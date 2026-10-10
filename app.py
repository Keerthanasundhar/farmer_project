from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from farmer_advisor.agents import FarmerAdvisorGraph

st.set_page_config(page_title="Farmer Crop & Weather Advisor", layout="wide")

st.title("Farmer Crop & Weather Advisor")
st.caption("AI-assisted weather, crop, and alert advisory for small and marginal farmers")

sample_questions = [
    "I grow paddy near Thanjavur. Should I irrigate this week?",
    "Is it safe to spray pesticide on my cotton crop tomorrow?",
    "There is a cyclone warning. What should I do to protect my banana plantation?",
    "What is the best time to harvest groundnut given this week's forecast?",
]

user_question = st.text_area(
    "Enter your farming question",
    value=sample_questions[0],
    height=130,
)

if st.button("Get advice"):
    with st.spinner("Reviewing the weather, alerts and agronomy guidance..."):
        adviser = FarmerAdvisorGraph()
        result = adviser.run(user_question)

    st.subheader("Advisory")
    st.write(result["final_advice"])

    st.subheader("Sources")
    for source in result.get("sources", []):
        st.markdown(f"- {source}")

st.subheader("Sample queries")
for q in sample_questions:
    st.markdown(f"- {q}")
