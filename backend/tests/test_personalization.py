"""
Regression tests for the personalisation & robustness fixes.

Each test here pins behaviour that was previously broken:

  * The rule-based fallback now reflects the user's ACTUAL diet/flights
    (previously hard-coded to meat_medium / no flights).
  * BigQuery analytics log the real diet_type (previously always "unknown").
  * The Gemini path guarantees exactly 3 insights or falls back.
  * Rate limiting keys on the real client IP behind a proxy.
  * Firestore documents serialise ranked_categories to plain dicts.

Several of these assertions FAIL against the pre-fix code, which is the point:
they lock in the corrected, context-aware behaviour.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.rate_limit import client_ip_key
from app.core.security import validate_device_id
from app.models.carbon import CarbonResult, RankedCategory
from app.models.insights import InsightItem
from app.routes.insights import _analytics_payload
from app.services import gemini_service
from app.services.firestore_service import _build_document
from app.services.gemini_service import GeminiUnavailableError

DEVICE_ID = "valid-device-001"


def _calc(client: TestClient, **overrides) -> dict:
    """POST /api/calculate and return the result dict."""
    payload = {
        "transport_km_car_petrol": 0,
        "transport_km_bus": 0,
        "transport_km_train": 0,
        "flights_short_haul": 0,
        "flights_long_haul": 0,
        "home_electricity_kwh": 0,
        "home_gas_kwh": 0,
        "household_size": 1,
        "diet_type": "meat_medium",
        "consumption_level": "medium",
        "device_id": DEVICE_ID,
    }
    payload.update(overrides)
    res = client.post("/api/calculate", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


def _insights(client: TestClient, result: dict) -> dict:
    res = client.post(
        "/api/insights",
        json={"carbon_result": result, "device_id": DEVICE_ID},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _result_model(**overrides) -> CarbonResult:
    base = {
        "total_kg": 5000.0,
        "breakdown": {"transport": 850.0, "home": 0.0, "diet": 1100.0, "consumption": 4000.0},
        "vs_global_average_pct": 125.0,
        "vs_paris_target_pct": 250.0,
        "ranked_categories": [
            RankedCategory(category="consumption", kg=4000.0, percentage=68.0),
            RankedCategory(category="transport", kg=850.0, percentage=14.0),
        ],
        "device_id": DEVICE_ID,
        "diet_type": "vegan",
        "consumption_level": "low",
        "flights_short_haul": 0,
        "flights_long_haul": 0,
    }
    base.update(overrides)
    return CarbonResult(**base)


class TestResultCarriesContext:
    """/api/calculate must echo lifestyle context onto the result."""

    def test_calculate_echoes_lifestyle_context(self, client: TestClient):
        result = _calc(
            client,
            diet_type="vegan",
            consumption_level="high",
            flights_short_haul=3,
            flights_long_haul=2,
        )
        assert result["diet_type"] == "vegan"
        assert result["consumption_level"] == "high"
        assert result["flights_short_haul"] == 3
        assert result["flights_long_haul"] == 2


class TestContextAwareFallback:
    """The rule-based fallback must reflect the user's real lifestyle."""

    def test_meat_heavy_gets_diet_insight_vegan_does_not(self, client: TestClient):
        """Only the meat-heavy user should receive a diet insight.

        Pre-fix, the fallback hard-coded diet_type='meat_medium', so a vegan
        user wrongly received a meat-reduction insight — this test failed.
        """
        heavy = _calc(
            client, transport_km_car_petrol=5000, consumption_level="high", diet_type="meat_heavy"
        )
        vegan = _calc(
            client, transport_km_car_petrol=5000, consumption_level="high", diet_type="vegan"
        )

        heavy_ins = _insights(client, heavy)
        vegan_ins = _insights(client, vegan)

        assert heavy_ins["source"] == "rules"
        assert vegan_ins["source"] == "rules"

        heavy_cats = [i["category"] for i in heavy_ins["insights"]]
        vegan_cats = [i["category"] for i in vegan_ins["insights"]]

        assert "diet" in heavy_cats
        assert "diet" not in vegan_cats

    def test_flights_flow_into_fallback_insights(self, client: TestClient):
        """A frequent flyer should get a flight-specific action.

        Pre-fix, flights were hard-coded to 0, so the flight insight never
        appeared regardless of input.
        """
        flyer = _calc(client, flights_long_haul=2, diet_type="vegan", consumption_level="low")
        flyer_ins = _insights(client, flyer)
        actions = " ".join(i["action"].lower() for i in flyer_ins["insights"])
        assert "flight" in actions


class TestAnalyticsPayload:
    """BigQuery events must log the real diet_type, never 'unknown'."""

    def test_payload_uses_real_diet_type(self):
        result = _result_model(diet_type="vegan")
        payload = _analytics_payload(result, source="rules", top_category="consumption")
        assert payload["diet_type"] == "vegan"
        assert payload["diet_type"] != "unknown"
        assert payload["insight_source"] == "rules"
        assert payload["top_category"] == "consumption"


class TestGeminiThreeInsightContract:
    """Gemini must yield exactly 3 valid insights or signal unavailable."""

    @pytest.mark.asyncio
    async def test_fewer_than_three_raises_unavailable(self):
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {
                    "category": "diet",
                    "action": "Swap beef.",
                    "estimated_saving_kg": 400.0,
                    "timeframe": "30 days",
                    "priority": 1,
                },
                {
                    "category": "transport",
                    "action": "Carpool.",
                    "estimated_saving_kg": 300.0,
                    "timeframe": "30 days",
                    "priority": 2,
                },
            ]
        )
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        with (
            patch("app.services.gemini_service.vertexai.init"),
            patch("app.services.gemini_service.GenerativeModel", return_value=mock_model),
        ):
            with pytest.raises(GeminiUnavailableError):
                await gemini_service.generate_insights_gemini(
                    ranked_categories=[{"category": "diet", "kg": 1100.0, "percentage": 100.0}],
                    total_kg=1100.0,
                )


class TestRateLimitKey:
    """Rate limiting must key on the originating client IP."""

    @staticmethod
    def _request(headers: dict[str, str], client_host: str = "10.0.0.1") -> Request:
        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw,
            "client": (client_host, 12345),
        }
        return Request(scope)

    def test_uses_first_forwarded_for_hop(self):
        req = self._request({"x-forwarded-for": "203.0.113.7, 10.0.0.1"})
        assert client_ip_key(req) == "203.0.113.7"

    def test_falls_back_to_peer_when_no_header(self):
        req = self._request({}, client_host="198.51.100.9")
        assert client_ip_key(req) == "198.51.100.9"


class TestFirestoreSerialisation:
    """Firestore documents must contain JSON-safe primitives only."""

    def test_ranked_categories_serialised_to_dicts(self):
        result = _result_model()
        insight = InsightItem(
            category="diet",
            action="Swap beef.",
            estimated_saving_kg=400.0,
            timeframe="30 days",
            priority=1,
        )
        doc = _build_document(DEVICE_ID, result, [insight])
        assert doc["ranked_categories"], "expected ranked categories in document"
        assert all(isinstance(rc, dict) for rc in doc["ranked_categories"])
        assert all(isinstance(i, dict) for i in doc["insights"])


class TestDeviceIdValidator:
    """validate_device_id stays consistent with the shared DeviceId rules."""

    def test_accepts_valid_and_rejects_invalid(self):
        assert validate_device_id("valid-device-001")
        assert not validate_device_id("short")  # < 8 chars
        assert not validate_device_id("bad id!")  # illegal chars
        assert not validate_device_id("a" * 65)  # > 64 chars
