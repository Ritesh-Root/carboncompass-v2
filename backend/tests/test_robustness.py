"""
Robustness tests: rate-limit enforcement, server-error paths, and calculator
correctness / fallback branches.

These complement the happy-path route and calculator tests by pinning the
behaviour the API promises under load, failure, and malformed input.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.carbon.calculator import calculate_footprint, get_rule_based_insights
from app.main import app
from app.services import firestore_service


class TestRateLimitEnforcement:
    """The /api/insights limiter (10/minute) must return 429 once exceeded."""

    def test_insights_returns_429_after_limit(
        self, client: TestClient, sample_carbon_result: dict
    ):
        # A dedicated forwarded-for IP gives this test its own rate-limit bucket,
        # isolated from every other test that hits the shared session client.
        headers = {"X-Forwarded-For": "203.0.113.250"}
        body = {"carbon_result": sample_carbon_result, "device_id": "rate-limit-001"}

        statuses = [
            client.post("/api/insights", json=body, headers=headers).status_code
            for _ in range(11)
        ]

        assert statuses[:10] == [200] * 10, statuses
        assert statuses[10] == 429


class TestServerErrorPaths:
    """Unhandled service failures must surface as HTTP 500, not crash."""

    def test_save_entry_returns_500_on_storage_failure(self, sample_carbon_result: dict):
        body = {"carbon_result": sample_carbon_result, "insights": []}

        with patch.object(
            firestore_service,
            "save_entry_memory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("storage exploded"),
        ):
            # raise_server_exceptions=False so the ServerErrorMiddleware turns the
            # unhandled error into a 500 response instead of re-raising it here.
            local_client = TestClient(app, raise_server_exceptions=False)
            response = local_client.post(
                "/api/entries",
                json=body,
                headers={"X-Forwarded-For": "203.0.113.251"},
            )

        assert response.status_code == 500


class TestCalculatorCorrectness:
    """Pin exact comparison math and defensive fallbacks in the pure function."""

    def test_known_footprint_comparison_percentages_are_exact(self):
        result = calculate_footprint(
            {"diet_type": "meat_medium", "consumption_level": "medium", "household_size": 1}
        )
        # diet (2500) + consumption (2500) = 5000; transport/home default to 0.
        assert result["total_kg"] == 5000.0
        assert result["vs_global_average_pct"] == 125.0  # 5000 / 4000 * 100
        assert result["vs_paris_target_pct"] == 250.0  # 5000 / 2000 * 100

    def test_invalid_diet_type_falls_back_to_meat_medium(self):
        result = calculate_footprint(
            {"diet_type": "carnivore", "consumption_level": "medium", "household_size": 1}
        )
        assert result["breakdown"]["diet"] == 2500.0

    def test_invalid_consumption_level_falls_back_to_medium(self):
        result = calculate_footprint(
            {"diet_type": "vegan", "consumption_level": "extreme", "household_size": 1}
        )
        assert result["breakdown"]["consumption"] == 2500.0

    def test_household_size_zero_is_clamped_to_one(self):
        zeroed = calculate_footprint(
            {
                "home_electricity_kwh": 1000,
                "household_size": 0,
                "diet_type": "vegan",
                "consumption_level": "low",
            }
        )
        single = calculate_footprint(
            {
                "home_electricity_kwh": 1000,
                "household_size": 1,
                "diet_type": "vegan",
                "consumption_level": "low",
            }
        )
        # household_size 0 must clamp to 1, not divide by zero.
        assert zeroed["breakdown"]["home"] == single["breakdown"]["home"]


class TestInsightsFallbackPadding:
    """A minimal user (nothing above any threshold) gets 3 generic insights."""

    def test_minimal_user_gets_three_distinct_generic_insights(self):
        breakdown = {"transport": 100.0, "home": 100.0, "diet": 1100.0, "consumption": 1200.0}
        ranked = sorted(
            ({"category": c, "kg": kg, "percentage": 0.0} for c, kg in breakdown.items()),
            key=lambda x: x["kg"],
            reverse=True,
        )

        insights = get_rule_based_insights(
            ranked,
            breakdown,
            diet_type="vegan",
            consumption_level="low",
            flights_short_haul=0,
            flights_long_haul=0,
        )

        assert len(insights) == 3
        assert all(i["category"] == "general" for i in insights)
        # Each fallback is a fresh dict, so priorities re-number cleanly to 1, 2, 3.
        assert [i["priority"] for i in insights] == [1, 2, 3]
        assert all(i["estimated_saving_kg"] > 0 for i in insights)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
