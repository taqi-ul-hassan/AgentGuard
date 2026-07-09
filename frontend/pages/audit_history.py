"""Audit History Streamlit page."""

from __future__ import annotations

import streamlit as st

from ui_helpers import BackendRequestError, configure_page, get_json, render_result_summary, render_sidebar


configure_page("Audit History")
render_sidebar()

st.title("Audit History")
st.caption("Stored Agent Guard decisions")

with st.sidebar:
    st.divider()
    decision = st.selectbox("Decision Filter", ["", "PASS", "FLAG"])
    risk_level = st.selectbox("Risk Filter", ["", "LOW", "MODERATE", "HIGH", "CRITICAL"])
    limit = st.slider("Limit", min_value=1, max_value=100, value=25)

params = {"limit": limit, "offset": 0}
if decision:
    params["decision"] = decision
if risk_level:
    params["risk_level"] = risk_level

try:
    with st.spinner("Loading audit history..."):
        data = get_json("/v1/audits", params=params)
except BackendRequestError as exc:
    st.error(exc.user_message)
    st.stop()

items = data.get("items", [])
total = data.get("total", 0)
st.metric("Matching Audits", total)

if not items:
    st.info("No audit records found.")
    st.stop()

st.dataframe(items, use_container_width=True, hide_index=True)

selected_audit_id = st.selectbox("Audit Detail", [item["id"] for item in items])

if selected_audit_id:
    try:
        with st.spinner("Loading audit detail..."):
            detail = get_json(f"/v1/audits/{selected_audit_id}")
    except BackendRequestError as exc:
        st.error(exc.user_message)
        st.stop()

    st.session_state["latest_verification_result"] = detail
    st.session_state["latest_audit_id"] = selected_audit_id

    st.divider()
    render_result_summary(detail)

    tabs = st.tabs(["Patient Context", "Modules", "Policies"])
    with tabs[0]:
        st.json(detail.get("patient_context", {}))
        st.write(detail.get("clinical_question", ""))
    with tabs[1]:
        modules = detail.get("module_results", [])
        if modules:
            st.dataframe(modules, use_container_width=True, hide_index=True)
        else:
            st.info("No module results stored for this audit.")
    with tabs[2]:
        policies = detail.get("policy_results", [])
        if policies:
            st.dataframe(policies, use_container_width=True, hide_index=True)
        else:
            st.info("No policy findings stored for this audit.")
