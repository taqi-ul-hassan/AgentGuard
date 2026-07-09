"""Policy Viewer Streamlit page."""

from __future__ import annotations

import streamlit as st

from ui_helpers import BackendRequestError, configure_page, get_json, post_json, render_sidebar


configure_page("Policy Viewer")
render_sidebar()

st.title("Policy Viewer")
st.caption("Active clinical governance policies")

toolbar = st.columns([0.75, 0.25])
with toolbar[1]:
    if st.button("Reload Policies", use_container_width=True):
        try:
            reload_response = post_json("/v1/policies/reload")
            st.success(f"Loaded {reload_response.get('loaded_count', 0)} policies.")
        except BackendRequestError as exc:
            st.error(exc.user_message)

try:
    with st.spinner("Loading policies..."):
        data = get_json("/v1/policies")
except BackendRequestError as exc:
    st.error(exc.user_message)
    st.stop()

with toolbar[0]:
    st.metric("Policy Version", data.get("version", "unknown"))

policies = data.get("policies", [])
if not policies:
    st.warning("No active policies returned.")
    st.stop()

for policy in policies:
    with st.container(border=True):
        cols = st.columns([0.52, 0.16, 0.16, 0.16])
        cols[0].markdown(f"**{policy.get('policy_id', 'unknown')}**")
        cols[1].write(policy.get("severity", "N/A"))
        cols[2].write("Required" if policy.get("required") else "Optional")
        cols[3].write(data.get("version", "unknown"))
        st.write(policy.get("description", ""))
        with st.expander("Evaluation Prompt"):
            st.write(policy.get("evaluation_prompt", ""))
