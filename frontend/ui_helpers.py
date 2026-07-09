"""Shared Streamlit UI and backend helpers for Agent Guard."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("AGENT_GUARD_API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 45


DEMO_CASES: dict[str, dict[str, Any]] = {
    "Safe recommendation": {
        "case_id": "demo-safe",
        "patient_context": {
            "age": 34,
            "sex": "female",
            "symptoms": ["mild sore throat", "nasal congestion"],
            "conditions": [],
            "medications": [],
            "allergies": [],
            "vitals": {"temperature": "37.1 C", "heart_rate": 76, "spo2": "99%"},
            "labs": {},
            "notes": "Symptoms started yesterday. No shortness of breath or chest pain.",
        },
        "clinical_question": "What outpatient guidance is appropriate?",
        "recommendation": (
            "Recommend supportive care, hydration, symptom monitoring, and clinician follow-up if symptoms worsen."
        ),
    },
    "Unsafe recommendation": {
        "case_id": "demo-unsafe",
        "patient_context": {
            "age": 72,
            "sex": "male",
            "symptoms": ["crushing chest pain", "diaphoresis", "shortness of breath"],
            "conditions": ["coronary artery disease", "type 2 diabetes"],
            "medications": ["atorvastatin", "metformin"],
            "allergies": [],
            "vitals": {"blood_pressure": "86/54", "heart_rate": 124, "spo2": "90%"},
            "labs": {},
            "notes": "Pain radiates to the left arm and began 40 minutes ago.",
        },
        "clinical_question": "What should be recommended?",
        "recommendation": "Advise the patient to rest at home and schedule routine follow-up next week.",
    },
    "Medication allergy conflict": {
        "case_id": "demo-allergy",
        "patient_context": {
            "age": 67,
            "sex": "female",
            "symptoms": ["chest pain", "shortness of breath"],
            "conditions": ["hypertension"],
            "medications": ["lisinopril"],
            "allergies": ["aspirin"],
            "vitals": {"blood_pressure": "98/60", "heart_rate": 112, "spo2": "92%"},
            "labs": {},
            "notes": "Documented aspirin allergy with prior facial swelling.",
        },
        "clinical_question": "What should be the next step?",
        "recommendation": "Give aspirin immediately and observe at home.",
    },
    "High-risk patient": {
        "case_id": "demo-high-risk",
        "patient_context": {
            "age": 81,
            "sex": "female",
            "symptoms": ["confusion", "fever", "low urine output"],
            "conditions": ["chronic kidney disease", "heart failure"],
            "medications": ["furosemide", "warfarin"],
            "allergies": ["penicillin"],
            "vitals": {"temperature": "39.2 C", "blood_pressure": "88/50", "heart_rate": 118},
            "labs": {"creatinine": "2.4 mg/dL", "inr": "3.1"},
            "notes": "Family reports rapid decline over 12 hours.",
        },
        "clinical_question": "How should this be triaged?",
        "recommendation": (
            "Recommend urgent clinician assessment and emergency evaluation due to hypotension, fever, and confusion."
        ),
    },
    "Missing context": {
        "case_id": "demo-missing-context",
        "patient_context": {
            "age": 46,
            "sex": "unknown",
            "symptoms": ["abdominal pain"],
            "conditions": [],
            "medications": [],
            "allergies": [],
            "vitals": {},
            "labs": {},
            "notes": "Duration, pregnancy status, vitals, and exam findings are not available.",
        },
        "clinical_question": "Can imaging be recommended?",
        "recommendation": "Diagnose appendicitis and send the patient directly to surgery.",
    },
}


def configure_page(title: str) -> None:
    """Configure Streamlit page settings and shared styling."""
    st.set_page_config(page_title=title, page_icon=None, layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
        h1, h2, h3 {letter-spacing: 0;}
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 14px;
        }
        .ag-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .ag-approved {background: #ecfdf5; color: #047857; border-color: #a7f3d0;}
        .ag-flag {background: #fef2f2; color: #b91c1c; border-color: #fecaca;}
        .ag-risk-low {background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe;}
        .ag-risk-moderate {background: #fffbeb; color: #b45309; border-color: #fde68a;}
        .ag-risk-high, .ag-risk-critical {background: #fff1f2; color: #be123c; border-color: #fecdd3;}
        .ag-section {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            background: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render common navigation and backend status."""
    with st.sidebar:
        st.markdown("### Agent Guard")
        st.caption(API_BASE_URL)
        st.page_link("streamlit_app.py", label="Recommendation Review")
        st.page_link("pages/verification_details.py", label="Verification Details")
        st.page_link("pages/audit_history.py", label="Audit History")
        st.page_link("pages/policy_viewer.py", label="Policy Viewer")
        st.divider()
        if st.button("Check Backend", use_container_width=True):
            try:
                health = get_json("/health")
                st.success(health.get("status", "ok"))
            except BackendRequestError as exc:
                st.error(exc.user_message)


class BackendRequestError(Exception):
    """User-facing backend request error."""

    def __init__(self, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(user_message)


def _handle_response(response: requests.Response) -> dict[str, Any]:
    """Parse a backend response and raise a friendly exception on failure."""
    try:
        payload = response.json()
    except ValueError as exc:
        raise BackendRequestError(f"Backend returned a non-JSON response with status {response.status_code}.") from exc

    if response.ok:
        return payload

    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    message = error.get("message") or response.reason or "Backend request failed."
    code = error.get("code")
    if code:
        message = f"{message} ({code})"
    raise BackendRequestError(message)


def get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a GET request to the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise BackendRequestError("Backend request timed out.") from exc
    except requests.RequestException as exc:
        raise BackendRequestError(f"Backend is unavailable: {exc}") from exc
    return _handle_response(response)


def post_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a POST request to the backend."""
    try:
        response = requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise BackendRequestError("Backend request timed out.") from exc
    except requests.RequestException as exc:
        raise BackendRequestError(f"Backend is unavailable: {exc}") from exc
    return _handle_response(response)


def split_lines(value: str) -> list[str]:
    """Convert newline-separated UI text into a clean list."""
    return [item.strip() for item in value.splitlines() if item.strip()]


def join_lines(values: list[str]) -> str:
    """Convert a list into newline-separated UI text."""
    return "\n".join(values or [])


def status_badge(label: str, value: str) -> str:
    """Return HTML for a small status badge."""
    css_value = value.lower().replace("_", "-")
    if label == "decision":
        css_class = "ag-approved" if value == "PASS" else "ag-flag"
    else:
        css_class = f"ag-risk-{css_value}"
    return f'<span class="ag-badge {css_class}">{value}</span>'


def render_result_summary(result: dict[str, Any]) -> None:
    """Render the headline decision area for a verification response."""
    decision = result.get("decision", "UNKNOWN")
    risk_level = result.get("risk_level", "UNKNOWN")
    confidence = result.get("confidence", 0.0)

    st.markdown(
        f"{status_badge('decision', decision)}&nbsp;&nbsp;{status_badge('risk', risk_level)}",
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Decision", decision)
    col_b.metric("Risk Level", risk_level)
    col_c.metric("Confidence", f"{float(confidence):.2f}" if isinstance(confidence, int | float) else confidence)

    st.markdown("### Recommendation")
    st.write(result.get("recommendation", "No recommendation returned."))
    st.markdown("### Explanation")
    st.info(result.get("summary", "No explanation returned."))


def render_module_card(module: dict[str, Any]) -> None:
    """Render one verification module card."""
    with st.container(border=True):
        heading_cols = st.columns([0.55, 0.15, 0.15, 0.15])
        heading_cols[0].markdown(f"**{module.get('module', 'Unknown module').replace('_', ' ').title()}**")
        heading_cols[1].markdown(status_badge("decision", module.get("status", "UNKNOWN")), unsafe_allow_html=True)
        severity = module.get("severity") or "N/A"
        heading_cols[2].write(severity)
        score = module.get("score")
        heading_cols[3].write(f"{score:.2f}" if isinstance(score, int | float) else "N/A")

        rationale = module.get("rationale")
        if rationale:
            st.write(rationale)

        findings = module.get("findings") or []
        evidence = module.get("evidence") or []
        if findings:
            with st.expander("Findings", expanded=True):
                for finding in findings:
                    st.write(f"- {finding}")
        if evidence:
            with st.expander("Evidence"):
                for item in evidence:
                    st.write(f"- {item}")
