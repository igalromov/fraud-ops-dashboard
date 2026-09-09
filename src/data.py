"""Loading and feature engineering for the fraud dataset.

Bin edges are not arbitrary: they were chosen after profiling the source file so
that each band isolates a genuine step-change in fraud rate (e.g. device trust
<=40 carries 123 of the 151 fraud cases; velocity >=5 runs at 10.4%).
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "credit_card_fraud_10k.csv"

# Ordered so charts and filters present buckets chronologically, not alphabetically.
TIME_BUCKETS = ["Night 00-03", "Dawn 04-07", "Morning 08-11",
                "Afternoon 12-15", "Evening 16-19", "Late 20-23"]
AMOUNT_BANDS = ["0-50", "50-120", "120-250", "250-500", "500+"]
TRUST_BANDS = ["25-40 (low)", "41-55", "56-70", "71-85", "86-99 (high)"]
VELOCITY_BANDS = ["0-1", "2", "3", "4", "5+"]
AGE_BANDS = ["18-25", "26-35", "36-45", "46-55", "56-69"]

# Dimensions the pattern miner and segment explorer are allowed to combine.
DIMENSIONS = {
    "time_bucket": "Time bucket",
    "merchant_category": "Merchant category",
    "amount_band": "Amount band",
    "trust_band": "Device trust",
    "velocity_band": "Velocity 24h",
    "age_band": "Cardholder age",
    "foreign_flag": "Foreign txn",
    "mismatch_flag": "Location mismatch",
}
NUMERIC_COLS = ["amount", "transaction_hour", "device_trust_score",
                "velocity_last_24h", "cardholder_age"]


def _banded(series: pd.Series, edges: list, labels: list) -> pd.Categorical:
    return pd.cut(series, bins=edges, labels=labels, ordered=True)


@st.cache_data(show_spinner=False)
def load_data(path: str | None = None) -> pd.DataFrame:
    """Read the CSV and attach the derived columns the dashboard filters on."""
    df = pd.read_csv(path or DATA_PATH)

    df["time_bucket"] = _banded(df["transaction_hour"],
                                [-1, 3, 7, 11, 15, 19, 23], TIME_BUCKETS)
    df["amount_band"] = _banded(df["amount"], [-1, 50, 120, 250, 500, 1e9], AMOUNT_BANDS)
    df["trust_band"] = _banded(df["device_trust_score"], [0, 40, 55, 70, 85, 100], TRUST_BANDS)
    df["velocity_band"] = _banded(df["velocity_last_24h"], [-1, 1, 2, 3, 4, 1e9], VELOCITY_BANDS)
    df["age_band"] = _banded(df["cardholder_age"], [17, 25, 35, 45, 55, 200], AGE_BANDS)

    df["foreign_flag"] = df["foreign_transaction"].map({0: "Domestic", 1: "Foreign"})
    df["mismatch_flag"] = df["location_mismatch"].map({0: "Location OK", 1: "Mismatch"})
    df["is_fraud_label"] = df["is_fraud"].map({0: "CLEAR", 1: "FRAUD"})

    # A transparent, auditable count of how many known risk conditions a row trips.
    df["risk_flag_count"] = (
        df["transaction_hour"].between(0, 3).astype(int)
        + df["foreign_transaction"]
        + df["location_mismatch"]
        + (df["device_trust_score"] <= 40).astype(int)
        + (df["velocity_last_24h"] >= 5).astype(int)
    )
    return df


def kpis(df: pd.DataFrame, baseline_rate: float) -> dict:
    """Headline figures for the current selection, compared against the full file."""
    n = len(df)
    fraud_n = int(df["is_fraud"].sum()) if n else 0
    rate = fraud_n / n if n else 0.0
    return {
        "transactions": n,
        "fraud_count": fraud_n,
        "fraud_rate": rate,
        "exposure": float(df.loc[df["is_fraud"] == 1, "amount"].sum()) if n else 0.0,
        "avg_fraud_amount": float(df.loc[df["is_fraud"] == 1, "amount"].mean()) if fraud_n else 0.0,
        "lift": (rate / baseline_rate) if baseline_rate and n else 0.0,
    }
