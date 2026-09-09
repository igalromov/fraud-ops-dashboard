"""Sidebar filter controls.

Every widget writes to `st.session_state` under a stable key so the preset
buttons and the pattern-miner drill-through can drive the same controls the user
operates by hand - one filter state, several ways to set it.
"""
import pandas as pd
import streamlit as st

from . import data as D

# Preset name -> the session_state the sidebar should be forced into.
# These encode the findings from profiling the file, so an analyst can jump
# straight to a known segment instead of rebuilding it from six widgets.
PRESETS = {
    "Night attacks": {"f_time": ["Night 00-03"]},
    "Foreign + mismatch": {"f_foreign": "Foreign", "f_mismatch": "Mismatch"},
    "Low device trust": {"f_trust": (25, 40)},
    "High velocity": {"f_velocity": (5, 9)},
    "Clean segment": {
        "f_time": ["Dawn 04-07", "Morning 08-11", "Afternoon 12-15",
                   "Evening 16-19", "Late 20-23"],
        "f_foreign": "Domestic", "f_mismatch": "Location OK",
    },
}

_DEFAULTS = {
    "f_merchant": [], "f_time": [], "f_hour": (0, 23), "f_amount": None,
    "f_trust": (25, 99), "f_velocity": (0, 9), "f_age": (18, 69),
    "f_foreign": "All", "f_mismatch": "All", "f_status": "All", "f_flags": 0,
}


def init_state(df: pd.DataFrame) -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = (
                (float(df["amount"].min()), float(df["amount"].max()))
                if key == "f_amount" else value
            )


def reset_state(df: pd.DataFrame) -> None:
    """Force every control back to its default value."""
    for key, value in _DEFAULTS.items():
        st.session_state[key] = (
            (float(df["amount"].min()), float(df["amount"].max()))
            if key == "f_amount" else value
        )


def _apply_preset(name: str, df: pd.DataFrame) -> None:
    """Reset first, so presets never stack onto each other silently."""
    reset_state(df)
    st.session_state.update(PRESETS[name])


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Draw the controls and return the filtered frame."""
    init_state(df)
    sb = st.sidebar

    sb.markdown(
        '<div class="fx-sec" style="margin-top:0">// query console</div>',
        unsafe_allow_html=True)

    sb.markdown('<div class="fx-note">Quick presets</div>', unsafe_allow_html=True)
    names = list(PRESETS)
    for i in range(0, len(names), 2):
        for col, name in zip(sb.columns(2), names[i:i + 2]):
            if col.button(name, key=f"p_{name}", width="stretch"):
                _apply_preset(name, df)
                st.rerun()
    if sb.button("↺  Reset all filters", key="p_reset", width="stretch"):
        reset_state(df)
        st.rerun()

    sb.markdown('<div class="fx-sec">// dimensions</div>', unsafe_allow_html=True)
    sb.multiselect("Merchant category", sorted(df["merchant_category"].unique()),
                   key="f_merchant", placeholder="All categories")
    sb.multiselect("Time bucket", D.TIME_BUCKETS, key="f_time",
                   placeholder="All time buckets")
    sb.slider("Hour of day", 0, 23, key="f_hour")

    sb.markdown('<div class="fx-sec">// risk signals</div>', unsafe_allow_html=True)
    sb.radio("Foreign transaction", ["All", "Domestic", "Foreign"],
             key="f_foreign", horizontal=True)
    sb.radio("Location mismatch", ["All", "Location OK", "Mismatch"],
             key="f_mismatch", horizontal=True)
    sb.slider("Device trust score", 25, 99, key="f_trust")
    sb.slider("Velocity (last 24h)", 0, 9, key="f_velocity")
    sb.slider("Minimum risk flags", 0, 5, key="f_flags",
              help="How many of the 5 known risk conditions a transaction must trip.")

    sb.markdown('<div class="fx-sec">// transaction</div>', unsafe_allow_html=True)
    sb.slider("Amount ($)", float(df["amount"].min()), float(df["amount"].max()),
              key="f_amount")
    sb.slider("Cardholder age", 18, 69, key="f_age")
    sb.radio("Fraud status", ["All", "FRAUD", "CLEAR"], key="f_status", horizontal=True)

    return apply_filters(df)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Translate session_state into a boolean mask over the frame."""
    s = st.session_state
    mask = pd.Series(True, index=df.index)

    if s["f_merchant"]:
        mask &= df["merchant_category"].isin(s["f_merchant"])
    if s["f_time"]:
        mask &= df["time_bucket"].astype(str).isin(s["f_time"])

    lo, hi = s["f_hour"]
    mask &= df["transaction_hour"].between(lo, hi)
    lo, hi = s["f_amount"]
    mask &= df["amount"].between(lo, hi)
    lo, hi = s["f_trust"]
    mask &= df["device_trust_score"].between(lo, hi)
    lo, hi = s["f_velocity"]
    mask &= df["velocity_last_24h"].between(lo, hi)
    lo, hi = s["f_age"]
    mask &= df["cardholder_age"].between(lo, hi)

    if s["f_foreign"] != "All":
        mask &= df["foreign_flag"] == s["f_foreign"]
    if s["f_mismatch"] != "All":
        mask &= df["mismatch_flag"] == s["f_mismatch"]
    if s["f_status"] != "All":
        mask &= df["is_fraud_label"] == s["f_status"]
    if s["f_flags"] > 0:
        mask &= df["risk_flag_count"] >= s["f_flags"]

    return df[mask]


def active_filter_tags() -> list[str]:
    """Human-readable list of what is currently narrowing the data."""
    s = st.session_state
    tags = []
    if s.get("f_merchant"):
        tags.append("merchant: " + ", ".join(s["f_merchant"]))
    if s.get("f_time"):
        tags.append("time: " + ", ".join(s["f_time"]))
    if s.get("f_hour") != (0, 23):
        tags.append("hour {}-{}".format(*s["f_hour"]))
    if s.get("f_trust") != (25, 99):
        tags.append("trust {}-{}".format(*s["f_trust"]))
    if s.get("f_velocity") != (0, 9):
        tags.append("velocity {}-{}".format(*s["f_velocity"]))
    if s.get("f_age") != (18, 69):
        tags.append("age {}-{}".format(*s["f_age"]))
    for key, label in (("f_foreign", ""), ("f_mismatch", ""), ("f_status", "status: ")):
        if s.get(key, "All") != "All":
            tags.append(label + str(s[key]))
    if s.get("f_flags", 0) > 0:
        tags.append(f"risk flags >= {s['f_flags']}")
    return tags
