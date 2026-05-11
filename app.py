from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.baseline import load_stops, nearest_stop_baseline, smart_stop_planner
from src.llm import llm_stop_planner
from src.policy import AMENITY_LABELS, ROUTE_DIRECTIONS, URGENCY_COPY


load_dotenv()

st.set_page_config(page_title="NextStop AI", page_icon=":material/map:", layout="wide")

st.title("NextStop AI")
st.caption("A focused GenAI workflow that helps long-distance drivers choose the next highway stop.")

sample = (
    "I need gas and coffee soon. I can go about 50 miles, "
    "and I would rather not stop somewhere without restrooms."
)

with st.sidebar:
    st.header("Mode")
    use_llm = st.toggle("Use OpenAI explanation", value=bool(os.getenv("OPENAI_API_KEY")))
    st.caption("Without an API key, the app uses the deterministic NextStop planner.")
    st.header("What It Optimizes")
    for urgency, copy in URGENCY_COPY.items():
        st.write(f"**{urgency.title()}:** {copy}")

st.subheader("Driver Context")
col1, col2, col3, col4 = st.columns(4)
route_options = sorted(ROUTE_DIRECTIONS.keys())
highway = col1.selectbox("Highway", route_options, index=route_options.index("I-94"))
direction = col2.selectbox("Direction", ROUTE_DIRECTIONS[highway])
current_mile = col3.number_input("Current mile marker", min_value=0.0, max_value=999.0, value=0.0, step=1.0)
fuel_range = col4.number_input("Fuel / battery range left", min_value=1.0, max_value=500.0, value=50.0, step=1.0)

selected = st.multiselect(
    "Must-have amenities",
    options=list(AMENITY_LABELS.keys()),
    format_func=lambda key: AMENITY_LABELS[key],
    default=[],
)

request = st.text_area("Natural language request", value=sample, height=120)

if st.button("Plan next stop", type="primary"):
    if not request.strip():
        st.warning("Describe what the driver needs first.")
    else:
        result = (
            llm_stop_planner(highway, direction, current_mile, fuel_range, request, selected)
            if use_llm
            else smart_stop_planner(highway, direction, current_mile, fuel_range, request, selected)
        )
        baseline = nearest_stop_baseline(highway, direction, current_mile, fuel_range, request)

        if result.recommendations:
            top = result.recommendations[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Recommended stop", top.name)
            col2.metric("Distance", f"{top.distance_miles:.1f} mi")
            col3.metric("Risk", top.risk_level)
            col4.metric("Urgency", result.urgency)

        st.subheader("Plan")
        st.write(result.driving_plan)
        st.info(result.caution)

        st.subheader("Why")
        st.write(result.request_summary)

        st.subheader("Top candidates")
        candidate_rows = [
            {
                "stop": rec.name,
                "distance_miles": rec.distance_miles,
                "type": rec.stop_type,
                "risk": rec.risk_level,
                "matched": ", ".join(rec.matched_amenities) or "none",
                "missing": ", ".join(rec.missing_amenities) or "none",
            }
            for rec in result.recommendations
        ]
        st.dataframe(pd.DataFrame(candidate_rows), hide_index=True, use_container_width=True)

        with st.expander("Compare with nearest-stop baseline"):
            base = baseline.recommendations[0]
            st.write(f"Baseline would stop at **{base.name}** in {base.distance_miles:.1f} miles.")
            st.write(baseline.caution)

with st.expander("Sample stop dataset"):
    st.dataframe(load_stops(), hide_index=True, use_container_width=True)
