"""Verification Details Streamlit page."""

from __future__ import annotations

import streamlit as st

from ui_helpers import configure_page, render_module_card, render_result_summary, render_sidebar


configure_page("Verification Details")
render_sidebar()

st.title("Verification Details")
st.caption("Module-level Agent Guard findings")

result = st.session_state.get("latest_verification_result")

if not result:
    st.info("Run a recommendation review or select an audit record to view verification details.")
    st.stop()

render_result_summary(result)

st.divider()
st.markdown("### Verification Modules")
module_results = result.get("module_results", [])
if module_results:
    for module in module_results:
        render_module_card(module)
else:
    st.warning("No module results were returned. The recommendation was not fully verified.")

st.markdown("### Policy Findings")
policy_results = result.get("policy_results", [])
if policy_results:
    for policy in policy_results:
        with st.container(border=True):
            cols = st.columns([0.45, 0.2, 0.2, 0.15])
            cols[0].markdown(f"**{policy.get('policy_id', 'unknown')}**")
            cols[1].write(policy.get("status", "UNKNOWN"))
            cols[2].write(policy.get("severity", "N/A"))
            cols[3].write("Required")
            if policy.get("message"):
                st.write(policy["message"])
else:
    st.info("No policy findings were returned.")

with st.expander("Raw Verification Payload"):
    st.json(result)
