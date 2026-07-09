"""Agent Guard Recommendation Review page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ui_helpers import (
    BackendRequestError,
    DEMO_CASES,
    configure_page,
    join_lines,
    post_json,
    render_result_summary,
    render_sidebar,
    split_lines,
)


def load_case(case_name: str) -> None:
    """Load a synthetic case into Streamlit widget state."""
    selected = DEMO_CASES[case_name]
    context = selected["patient_context"]
    st.session_state["case_id"] = selected["case_id"]
    st.session_state["age"] = context.get("age", 0)
    st.session_state["sex"] = context.get("sex", "unknown")
    st.session_state["symptoms"] = join_lines(context.get("symptoms", []))
    st.session_state["conditions"] = join_lines(context.get("conditions", []))
    st.session_state["medications"] = join_lines(context.get("medications", []))
    st.session_state["allergies"] = join_lines(context.get("allergies", []))
    st.session_state["vitals"] = "\n".join(f"{key}: {value}" for key, value in context.get("vitals", {}).items())
    st.session_state["labs"] = "\n".join(f"{key}: {value}" for key, value in context.get("labs", {}).items())
    st.session_state["notes"] = context.get("notes", "")
    st.session_state["clinical_question"] = selected["clinical_question"]
    st.session_state["supplied_recommendation"] = selected["recommendation"]
    st.session_state["workflow"] = "Verify existing recommendation"


def parse_key_value_lines(value: str) -> dict[str, str]:
    """Parse simple key-value text fields into dictionaries."""
    parsed: dict[str, str] = {}
    for line in split_lines(value):
        if ":" in line:
            key, raw_value = line.split(":", 1)
            parsed[key.strip()] = raw_value.strip()
    return parsed


def build_patient_context() -> dict[str, Any]:
    """Build the patient context payload from widget state."""
    return {
        "age": st.session_state["age"],
        "sex": st.session_state["sex"],
        "symptoms": split_lines(st.session_state["symptoms"]),
        "conditions": split_lines(st.session_state["conditions"]),
        "medications": split_lines(st.session_state["medications"]),
        "allergies": split_lines(st.session_state["allergies"]),
        "vitals": parse_key_value_lines(st.session_state["vitals"]),
        "labs": parse_key_value_lines(st.session_state["labs"]),
        "notes": st.session_state["notes"],
    }


def initialize_form_defaults() -> None:
    """Initialize form state once so widgets do not receive conflicting defaults."""
    defaults = {
        "case_id": "demo-case",
        "age": 67,
        "sex": "female",
        "symptoms": "chest pain\nshortness of breath",
        "conditions": "diabetes\nhypertension",
        "medications": "metformin\nlisinopril",
        "allergies": "aspirin",
        "vitals": "heart_rate: 112\nspo2: 91%",
        "labs": "",
        "notes": "Pain radiates to left arm.",
        "workflow": "Generate and verify",
        "clinical_question": "What should be the next step?",
        "supplied_recommendation": "Recommend urgent clinician evaluation.",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


configure_page("Agent Guard")
render_sidebar()
initialize_form_defaults()

st.title("Agent Guard")
st.caption("Real-time safety checkpoint for clinical AI agents")

with st.container(border=True):
    demo_cols = st.columns([0.72, 0.28])
    selected_case = demo_cols[0].selectbox("Synthetic Demo Case", list(DEMO_CASES.keys()))
    if demo_cols[1].button("Load Case", use_container_width=True):
        load_case(selected_case)
        st.rerun()

left, right = st.columns([0.43, 0.57], gap="large")

with left:
    st.markdown("### Patient Context")
    st.text_input("Case ID", key="case_id")
    st.number_input("Age", min_value=0, max_value=130, key="age")
    sex_options = ["female", "male", "other", "unknown"]
    if st.session_state.get("sex") not in sex_options:
        st.session_state["sex"] = "unknown"
    st.selectbox(
        "Sex",
        sex_options,
        index=sex_options.index(st.session_state["sex"]),
        key="sex",
    )
    st.text_area("Symptoms", key="symptoms")
    st.text_area("Conditions", key="conditions")
    st.text_area("Medications", key="medications")
    st.text_area("Allergies", key="allergies")
    subcols = st.columns(2)
    subcols[0].text_area("Vitals", key="vitals")
    subcols[1].text_area("Labs", key="labs")
    st.text_area("Clinical Notes", key="notes")

with right:
    st.markdown("### Review")
    st.radio(
        "Workflow",
        ["Generate and verify", "Verify existing recommendation"],
        horizontal=True,
        key="workflow",
    )
    st.text_area(
        "Clinical Question",
        key="clinical_question",
    )

    if st.session_state["workflow"] == "Verify existing recommendation":
        st.text_area(
            "Existing Recommendation",
            height=120,
            key="supplied_recommendation",
        )

    if st.button("Run Agent Guard", type="primary", use_container_width=True):
        payload: dict[str, Any] = {
            "patient_context": build_patient_context(),
            "clinical_question": st.session_state["clinical_question"],
            "metadata": {"case_id": st.session_state["case_id"], "clinician_id": "demo-user"},
        }
        endpoint = "/v1/recommendations/generate-and-verify"
        if st.session_state["workflow"] == "Verify existing recommendation":
            endpoint = "/v1/recommendations/verify"
            payload["recommendation"] = st.session_state["supplied_recommendation"]

        with st.spinner("Running clinical generation and Agent Guard verification..."):
            try:
                result = post_json(endpoint, payload)
                st.session_state["latest_verification_result"] = result
                st.session_state["latest_audit_id"] = result.get("audit_id")
                st.success("Verification complete.")
            except BackendRequestError as exc:
                st.error(exc.user_message)

    result = st.session_state.get("latest_verification_result")
    if result:
        st.divider()
        render_result_summary(result)
        with st.expander("Model Metadata"):
            st.json(result.get("model_metadata", {}))
        with st.expander("Raw API Response"):
            st.json(result)
