from __future__ import annotations

import json
import os
from pathlib import Path

from src.baseline import PlanResult, StopRecommendation, smart_stop_planner


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "nextstop_prompt.md"


def llm_stop_planner(
    highway: str,
    direction: str,
    current_mile: float,
    fuel_range: float,
    request: str,
    selected_amenities: list[str] | None = None,
    stop_type_filter: str = "any",
    model: str = "gpt-4o-mini",
) -> PlanResult:
    """Use OpenAI to explain a stop recommendation, with deterministic fallback."""
    deterministic = smart_stop_planner(
        highway,
        direction,
        current_mile,
        fuel_range,
        request,
        selected_amenities,
        stop_type_filter,
    )
    if not os.getenv("OPENAI_API_KEY"):
        return deterministic

    from openai import OpenAI

    context = {
        "highway": highway,
        "direction": direction,
        "current_mile": current_mile,
        "fuel_range": fuel_range,
        "request": request,
        "required_amenities": deterministic.required_amenities,
        "urgency": deterministic.urgency,
        "stop_type_filter": stop_type_filter,
    }
    candidates = [
        {
            "stop_id": rec.stop_id,
            "name": rec.name,
            "distance_miles": rec.distance_miles,
            "stop_type": rec.stop_type,
            "matched_amenities": rec.matched_amenities,
            "missing_amenities": rec.missing_amenities,
            "risk_level": rec.risk_level,
            "reason": rec.reason,
        }
        for rec in deterministic.recommendations
    ]
    prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        .replace("{{context}}", json.dumps(context, indent=2))
        .replace("{{candidates}}", json.dumps(candidates, indent=2))
    )
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)

    top_id = data.get("top_stop_id")
    ordered = _move_top_candidate_first(deterministic.recommendations, top_id)
    return PlanResult(
        request_summary=data.get("request_summary", deterministic.request_summary),
        required_amenities=deterministic.required_amenities,
        urgency=deterministic.urgency,
        recommendations=ordered,
        driving_plan=data.get("driving_plan", deterministic.driving_plan),
        caution=data.get("caution", deterministic.caution),
    )


def _move_top_candidate_first(
    recommendations: tuple[StopRecommendation, ...],
    top_stop_id: str | None,
) -> tuple[StopRecommendation, ...]:
    if not top_stop_id:
        return recommendations
    matches = [rec for rec in recommendations if rec.stop_id == top_stop_id]
    if not matches:
        return recommendations
    rest = [rec for rec in recommendations if rec.stop_id != top_stop_id]
    return tuple(matches + rest)
