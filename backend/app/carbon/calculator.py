"""
Pure carbon footprint calculation functions.

No I/O, no side effects — deterministic and fully testable.
All inputs come from validated Pydantic models (passed as dict).
"""

from __future__ import annotations

from typing import Any, cast

from app.carbon.factors import (
    CONSUMPTION,
    DIET,
    GLOBAL_AVERAGE,
    HOME,
    PARIS_TARGET,
    TRANSPORT,
)


def calculate_footprint(inputs: dict[str, Any]) -> dict[str, Any]:
    """Calculate annual carbon footprint from user lifestyle inputs.

    Args:
        inputs: Dict matching CarbonInput model fields (already validated).

    Returns:
        Dict with total_kg, breakdown, vs_global_average_pct,
        vs_paris_target_pct, and ranked_categories.
    """
    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    transport_kg = (
        inputs.get("transport_km_car_petrol", 0.0) * TRANSPORT["car_petrol"]
        + inputs.get("transport_km_car_diesel", 0.0) * TRANSPORT["car_diesel"]
        + inputs.get("transport_km_car_electric", 0.0) * TRANSPORT["car_electric"]
        + inputs.get("transport_km_bus", 0.0) * TRANSPORT["bus"]
        + inputs.get("transport_km_train", 0.0) * TRANSPORT["train"]
        + inputs.get("flights_short_haul", 0) * TRANSPORT["flight_short_haul_per_flight"]
        + inputs.get("flights_long_haul", 0) * TRANSPORT["flight_long_haul_per_flight"]
    )

    # ------------------------------------------------------------------
    # Home Energy (divided equally among household members)
    # ------------------------------------------------------------------
    household_size = max(inputs.get("household_size", 1), 1)
    home_kg = (
        inputs.get("home_electricity_kwh", 0.0) * HOME["electricity_per_kwh"]
        + inputs.get("home_gas_kwh", 0.0) * HOME["gas_per_kwh"]
    ) / household_size

    # ------------------------------------------------------------------
    # Diet (annual, already per-person)
    # ------------------------------------------------------------------
    diet_type = inputs.get("diet_type", "meat_medium")
    diet_kg = DIET.get(diet_type, DIET["meat_medium"])

    # ------------------------------------------------------------------
    # Consumption / Shopping
    # ------------------------------------------------------------------
    consumption_level = inputs.get("consumption_level", "medium")
    consumption_kg = CONSUMPTION.get(consumption_level, CONSUMPTION["medium"])

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------
    breakdown: dict[str, float] = {
        "transport": round(transport_kg, 2),
        "home": round(home_kg, 2),
        "diet": round(diet_kg, 2),
        "consumption": round(consumption_kg, 2),
    }
    total_kg = round(sum(breakdown.values()), 2)

    # ------------------------------------------------------------------
    # Comparisons
    # ------------------------------------------------------------------
    vs_global_average_pct = round((total_kg / GLOBAL_AVERAGE) * 100, 1)
    vs_paris_target_pct = round((total_kg / PARIS_TARGET) * 100, 1)

    # ------------------------------------------------------------------
    # Rankings (highest emitting category first)
    # ------------------------------------------------------------------
    ranked_categories = sorted(
        [
            {
                "category": category,
                "kg": kg,
                "percentage": round((kg / total_kg) * 100, 1) if total_kg > 0 else 0.0,
            }
            for category, kg in breakdown.items()
        ],
        key=lambda x: cast(float, x["kg"]),
        reverse=True,
    )

    return {
        "total_kg": total_kg,
        "breakdown": breakdown,
        "vs_global_average_pct": vs_global_average_pct,
        "vs_paris_target_pct": vs_paris_target_pct,
        "ranked_categories": ranked_categories,
    }


# ---------------------------------------------------------------------------
# Rule-based insight tuning constants
# ---------------------------------------------------------------------------
# Emission thresholds (kg CO2e/year) above which a category warrants an action.
TRANSPORT_HIGH_THRESHOLD_KG = 2000.0
TRANSPORT_MODERATE_THRESHOLD_KG = 500.0
HOME_HIGH_THRESHOLD_KG = 1500.0
HOME_MODERATE_THRESHOLD_KG = 500.0

# Fraction of a category's emissions each action is estimated to remove.
TRANSPORT_HIGH_REDUCTION = 0.40
TRANSPORT_MODERATE_REDUCTION = 0.20
HOME_HIGH_REDUCTION = 0.20
HOME_MODERATE_REDUCTION = 0.15
MONITORING_REDUCTION = 0.10  # generic track-and-reduce fallback

# Flight counts above which a flight-reduction action is offered.
SHORT_HAUL_FLIGHT_THRESHOLD = 2
LONG_HAUL_FLIGHT_THRESHOLD = 1

# Flat annual savings for lifestyle swaps that don't scale linearly with a
# single numeric input (diet and consumption patterns).
DIET_HEAVY_SAVING_KG = 800.0
DIET_MEDIUM_SAVING_KG = 400.0
CONSUMPTION_HIGH_SAVING_KG = 600.0
CONSUMPTION_MEDIUM_SAVING_KG = 500.0

# Response contract: callers always receive exactly this many insights.
TARGET_INSIGHT_COUNT = 3


def _transport_insight(transport_kg: float) -> dict[str, Any] | None:
    """Driving-reduction action sized to the user's road transport emissions."""
    if transport_kg > TRANSPORT_HIGH_THRESHOLD_KG:
        return {
            "category": "transport",
            "action": (
                "Switch to public transport or carpooling for your daily commute. "
                "Replacing a petrol car commute with bus or train "
                "cuts per-km emissions by ~75%."
            ),
            "estimated_saving_kg": round(transport_kg * TRANSPORT_HIGH_REDUCTION, 1),
            "timeframe": "Achievable within 30 days",
            "priority": 1,
        }
    if transport_kg > TRANSPORT_MODERATE_THRESHOLD_KG:
        return {
            "category": "transport",
            "action": (
                "Combine car trips and plan routes efficiently. "
                "Reducing driving by 20% through trip consolidation saves fuel and emissions."
            ),
            "estimated_saving_kg": round(transport_kg * TRANSPORT_MODERATE_REDUCTION, 1),
            "timeframe": "Achievable within 30 days",
            "priority": 2,
        }
    return None


def _flight_insight(flights_short_haul: int, flights_long_haul: int) -> dict[str, Any] | None:
    """Flight-reduction action for frequent flyers, using the published per-flight factors."""
    if (
        flights_short_haul > SHORT_HAUL_FLIGHT_THRESHOLD
        or flights_long_haul > LONG_HAUL_FLIGHT_THRESHOLD
    ):
        flight_saving = (
            min(flights_short_haul, 1) * TRANSPORT["flight_short_haul_per_flight"]
            + min(flights_long_haul, 1) * TRANSPORT["flight_long_haul_per_flight"]
        )
        return {
            "category": "transport",
            "action": (
                "Replace one flight with a train journey or video call. "
                "A single long-haul flight produces more CO2e than driving for 9,500 km."
            ),
            "estimated_saving_kg": round(flight_saving, 1),
            "timeframe": "Next planned trip",
            "priority": 1,
        }
    return None


def _home_insight(home_kg: float) -> dict[str, Any] | None:
    """Home-energy action sized to the user's household emissions."""
    if home_kg > HOME_HIGH_THRESHOLD_KG:
        return {
            "category": "home",
            "action": (
                "Install LED bulbs throughout your home and set a smart thermostat. "
                "LEDs use 75% less energy; a 1°C thermostat reduction "
                "saves ~3% on heating bills."
            ),
            "estimated_saving_kg": round(home_kg * HOME_HIGH_REDUCTION, 1),
            "timeframe": "Achievable within 30 days",
            "priority": 2,
        }
    if home_kg > HOME_MODERATE_THRESHOLD_KG:
        return {
            "category": "home",
            "action": (
                "Switch to a 100% renewable electricity tariff. "
                "Green energy tariffs are now competitively priced "
                "and eliminate electricity grid emissions."
            ),
            "estimated_saving_kg": round(home_kg * HOME_MODERATE_REDUCTION, 1),
            "timeframe": "Achievable within 7 days",
            "priority": 3,
        }
    return None


def _diet_insight(diet_type: str) -> dict[str, Any] | None:
    """Diet-swap action matched to the user's dietary pattern."""
    if diet_type == "meat_heavy":
        return {
            "category": "diet",
            "action": (
                "Reduce red meat consumption to 3 times per week. "
                "Beef has 20x the carbon footprint of chicken and "
                "100x that of legumes per gram of protein."
            ),
            "estimated_saving_kg": DIET_HEAVY_SAVING_KG,
            "timeframe": "Achievable within 30 days",
            "priority": 1,
        }
    if diet_type == "meat_medium":
        return {
            "category": "diet",
            "action": (
                "Try 2 plant-based meals per day. "
                "Swapping one beef meal per week for plant protein saves ~350 kg CO2e per year."
            ),
            "estimated_saving_kg": DIET_MEDIUM_SAVING_KG,
            "timeframe": "Achievable within 30 days",
            "priority": 2,
        }
    return None


def _consumption_insight(consumption_level: str) -> dict[str, Any] | None:
    """Consumption-reduction action matched to the user's shopping pattern."""
    if consumption_level == "high":
        return {
            "category": "consumption",
            "action": (
                "Buy second-hand for your next clothing or electronics purchase. "
                "Extending a garment's life by 9 months reduces "
                "its carbon and water footprint by ~30%."
            ),
            "estimated_saving_kg": CONSUMPTION_HIGH_SAVING_KG,
            "timeframe": "Next purchase decision",
            "priority": 2,
        }
    if consumption_level == "medium":
        return {
            "category": "consumption",
            "action": (
                "Audit subscriptions and physical goods — "
                "cancel unused services and avoid impulse purchases. "
                "Reducing consumption by 20% saves both money "
                "and ~500 kg CO2e annually."
            ),
            "estimated_saving_kg": CONSUMPTION_MEDIUM_SAVING_KG,
            "timeframe": "Achievable within 30 days",
            "priority": 3,
        }
    return None


def _fallback_insight(breakdown: dict[str, float]) -> dict[str, Any]:
    """Generic track-and-reduce action, used to pad up to the contract count."""
    return {
        "category": "general",
        "action": (
            "Track your footprint monthly and set a 10% reduction target for next quarter. "
            "Consistent monitoring is the most effective habit to sustain long-term reductions."
        ),
        "estimated_saving_kg": round(sum(breakdown.values()) * MONITORING_REDUCTION, 1),
        "timeframe": "Ongoing",
        "priority": 3,
    }


def get_rule_based_insights(
    ranked_categories: list[dict[str, Any]],
    breakdown: dict[str, float],
    diet_type: str = "meat_medium",
    consumption_level: str = "medium",
    flights_short_haul: int = 0,
    flights_long_haul: int = 0,
) -> list[dict[str, Any]]:
    """Generate deterministic, rule-based carbon reduction insights.

    Each category contributes at most one candidate action (via the
    ``_*_insight`` helpers); candidates are then ranked by priority and
    estimated saving, trimmed to the contract count, and padded with a
    generic fallback when fewer than ``TARGET_INSIGHT_COUNT`` apply.

    Args:
        ranked_categories: Sorted list of category emission dicts.
        breakdown: Per-category kg CO2e dict.
        diet_type: User's diet type pattern.
        consumption_level: User's goods consumption pattern level.
        flights_short_haul: Number of annual short-haul flights.
        flights_long_haul: Number of annual long-haul flights.

    Returns:
        List of exactly ``TARGET_INSIGHT_COUNT`` insight dicts, each with a
        sequential priority (1..N) and an estimated carbon saving.
    """
    candidate_insights: list[dict[str, Any]] = [
        insight
        for insight in (
            _transport_insight(breakdown.get("transport", 0.0)),
            _flight_insight(flights_short_haul, flights_long_haul),
            _home_insight(breakdown.get("home", 0.0)),
            _diet_insight(diet_type),
            _consumption_insight(consumption_level),
        )
        if insight is not None
    ]

    # Highest priority (lowest number) first, then largest saving first.
    candidate_insights.sort(key=lambda x: (x["priority"], -x["estimated_saving_kg"]))

    insights = candidate_insights[:TARGET_INSIGHT_COUNT]
    while len(insights) < TARGET_INSIGHT_COUNT:
        # Fresh dict each time so the sequential re-numbering below is correct.
        insights.append(_fallback_insight(breakdown))

    # Re-number priorities sequentially to match final ordering.
    for idx, insight in enumerate(insights, start=1):
        insight["priority"] = idx

    return insights
