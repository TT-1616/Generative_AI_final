from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STOPS_PATH = ROOT / "data" / "highway_stops.csv"


@dataclass(frozen=True)
class StopRecommendation:
    stop_id: str
    name: str
    distance_miles: float
    stop_type: str
    matched_amenities: tuple[str, ...]
    missing_amenities: tuple[str, ...]
    risk_level: str
    reason: str


@dataclass(frozen=True)
class PlanResult:
    request_summary: str
    required_amenities: tuple[str, ...]
    urgency: str
    recommendations: tuple[StopRecommendation, ...]
    driving_plan: str
    caution: str


def load_stops() -> pd.DataFrame:
    stops = pd.read_csv(STOPS_PATH)
    bool_columns = [
        "restroom",
        "gas",
        "food",
        "coffee",
        "ev_charger",
        "truck_parking",
        "pet_area",
        "open_24h",
    ]
    for column in bool_columns:
        stops[column] = stops[column].astype(bool)
    return stops


def distance_ahead(current_mile: float, stop_mile: float, direction: str) -> float | None:
    if direction in {"northbound", "eastbound"}:
        distance = stop_mile - current_mile
    else:
        distance = current_mile - stop_mile
    return round(distance, 1) if distance >= 0 else None


def parse_needs(request: str, selected_amenities: list[str] | None = None) -> tuple[tuple[str, ...], str]:
    text = request.lower()
    needs = set(selected_amenities or [])
    keyword_map = {
        "restroom": ("restroom", "bathroom", "toilet", "kids", "child", "pee"),
        "gas": ("gas", "fuel", "tank", "range", "empty"),
        "food": ("food", "meal", "eat", "lunch", "dinner", "hungry"),
        "coffee": ("coffee", "caffeine", "espresso"),
        "ev_charger": ("ev", "charge", "charger", "tesla"),
        "truck_parking": ("truck", "box truck", "trailer", "semi", "parking"),
        "pet_area": ("dog", "pet", "puppy"),
        "open_24h": ("night", "late", "midnight", "safe", "24", "seasonal", "closed", "winter", "avoid"),
    }
    for amenity, terms in keyword_map.items():
        if any(term in text for term in terms):
            needs.add(amenity)

    if any(term in text for term in ("urgent", "asap", "now", "almost empty", "low fuel", "can't wait")):
        urgency = "urgent"
    elif any(term in text for term in ("soon", "next 20", "kids", "bathroom", "restroom")):
        urgency = "soon"
    else:
        urgency = "flexible"
    return tuple(sorted(needs)), urgency


def _candidate_stops(highway: str, direction: str, current_mile: float) -> list[dict]:
    stops = load_stops()
    route_stops = stops[(stops["highway"] == highway) & (stops["direction"] == direction)].copy()
    candidates: list[dict] = []
    for row in route_stops.to_dict("records"):
        distance = distance_ahead(current_mile, float(row["mile_marker"]), direction)
        if distance is None:
            continue
        row["distance_miles"] = distance
        candidates.append(row)
    return sorted(candidates, key=lambda row: row["distance_miles"])


def nearest_stop_baseline(highway: str, direction: str, current_mile: float, fuel_range: float, request: str) -> PlanResult:
    """Baseline: choose the nearest open stop ahead, ignoring nuanced needs."""
    candidates = _candidate_stops(highway, direction, current_mile)
    if not candidates:
        return PlanResult("No stops found ahead.", tuple(), "urgent", tuple(), "", "No route data is available.")
    first = candidates[0]
    recommendation = _make_recommendation(first, tuple(), fuel_range)
    return PlanResult(
        request_summary="Baseline chooses the nearest known stop ahead.",
        required_amenities=tuple(),
        urgency="flexible",
        recommendations=(recommendation,),
        driving_plan=f"Stop at {first['name']} in {first['distance_miles']:.1f} miles.",
        caution="This baseline does not check whether the stop has the requested amenities.",
    )


def smart_stop_planner(
    highway: str,
    direction: str,
    current_mile: float,
    fuel_range: float,
    request: str,
    selected_amenities: list[str] | None = None,
) -> PlanResult:
    required, urgency = parse_needs(request, selected_amenities)
    candidates = _candidate_stops(highway, direction, current_mile)
    scored = []
    for row in candidates:
        missing = tuple(amenity for amenity in required if not row[amenity])
        matched = tuple(amenity for amenity in required if row[amenity])
        distance = float(row["distance_miles"])
        reachable = distance <= fuel_range
        fuel_buffer = fuel_range - distance
        score = distance
        score += 50 * len(missing)
        if not reachable:
            score += 1000
        if "gas" in required and row["gas"] and fuel_buffer >= 5:
            score -= 20
        if urgency == "urgent" and distance > 25:
            score += 30
        if urgency == "soon" and distance > 30:
            score += 18
        if row["open_24h"]:
            score -= 3
        scored.append((score, row, matched, missing))

    scored.sort(key=lambda item: item[0])
    recommendations = tuple(_make_recommendation(row, missing, fuel_range, matched) for _, row, matched, missing in scored[:3])

    if not recommendations:
        return PlanResult(
            request_summary="No stops are available ahead in the sample dataset.",
            required_amenities=required,
            urgency=urgency,
            recommendations=tuple(),
            driving_plan="No recommendation available.",
            caution="Use a real navigation app or DOT source before driving.",
        )

    top = recommendations[0]
    request_summary = _summarize_request(required, urgency)
    driving_plan = _make_driving_plan(top, recommendations, fuel_range)
    caution = _make_caution(top, fuel_range)
    return PlanResult(request_summary, required, urgency, recommendations, driving_plan, caution)


def _make_recommendation(
    row: dict,
    missing_amenities: tuple[str, ...],
    fuel_range: float,
    matched_amenities: tuple[str, ...] = tuple(),
) -> StopRecommendation:
    distance = float(row["distance_miles"])
    if distance > fuel_range:
        risk_level = "not reachable on stated fuel range"
    elif fuel_range - distance < 8:
        risk_level = "tight fuel buffer"
    elif missing_amenities:
        risk_level = "amenity tradeoff"
    else:
        risk_level = "good match"

    reason_parts = [f"{distance:.1f} miles ahead"]
    if matched_amenities:
        reason_parts.append("matches " + ", ".join(matched_amenities))
    if missing_amenities:
        reason_parts.append("missing " + ", ".join(missing_amenities))
    if row["open_24h"]:
        reason_parts.append("open 24h")
    reason = "; ".join(reason_parts)
    return StopRecommendation(
        stop_id=str(row["stop_id"]),
        name=str(row["name"]),
        distance_miles=distance,
        stop_type=str(row["stop_type"]),
        matched_amenities=matched_amenities,
        missing_amenities=missing_amenities,
        risk_level=risk_level,
        reason=reason,
    )


def _summarize_request(required: tuple[str, ...], urgency: str) -> str:
    if required:
        needs = ", ".join(required).replace("_", " ")
    else:
        needs = "a reasonable rest stop"
    return f"Driver needs {needs}; urgency is {urgency}."


def _make_driving_plan(top: StopRecommendation, recommendations: tuple[StopRecommendation, ...], fuel_range: float) -> str:
    plan = f"Recommended next stop: {top.name}, about {top.distance_miles:.1f} miles ahead."
    if top.distance_miles > fuel_range:
        return plan + " This is beyond the stated fuel range, so the driver should not rely on this plan."
    if len(recommendations) > 1:
        backup = recommendations[1]
        plan += f" Backup option: {backup.name} at {backup.distance_miles:.1f} miles."
    return plan


def _make_caution(top: StopRecommendation, fuel_range: float) -> str:
    if top.distance_miles > fuel_range:
        return "Fuel range is not enough for the recommended stop. Use live navigation and stop sooner if possible."
    if fuel_range - top.distance_miles < 8:
        return "Fuel buffer is tight. Do not skip this stop unless live navigation shows a closer fuel option."
    if top.missing_amenities:
        return "This recommendation has a tradeoff. Review the missing amenities before deciding."
    return "Check live navigation before driving because hours, closures, and services can change."
