"""Automated pattern discovery and anomaly scoring.

The dataset's signal lives in feature *interactions*, not single columns
(night + foreign + mismatch runs at 100% fraud while each alone sits near 8%).
Scanning combinations automatically is therefore the point of the dashboard,
not a nicety.

With only 151 fraud rows in 10,000, deep slices hit tiny samples fast, so every
rate is reported with its support and ranked by a Wilson score lower bound -
a 2-of-2 fluke must not outrank a 46-of-153 real pattern.
"""
from itertools import combinations

import numpy as np
import pandas as pd

Z = 1.96  # 95% two-sided


def wilson_lower_bound(successes: int, n: int, z: float = Z) -> float:
    """Lower bound of the Wilson score interval for a binomial proportion.

    Penalises small samples: 2/2 yields ~0.34 while 46/153 yields ~0.23 - so
    ranking by this bound rewards evidence, not luck.
    """
    if n == 0:
        return 0.0
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def column_lift(df: pd.DataFrame, dimensions: dict) -> pd.DataFrame:
    """Single-feature breakdown: every value of every dimension, ranked by lift."""
    if df.empty:
        return pd.DataFrame(columns=["Feature", "Value", "Txns", "Fraud",
                                     "Fraud rate", "Lift", "Confidence"])
    baseline = df["is_fraud"].mean()
    rows = []
    for col, label in dimensions.items():
        grp = df.groupby(col, observed=True)["is_fraud"].agg(["count", "sum"])
        for value, (count, fraud) in grp.iterrows():
            if count == 0:
                continue
            rate = fraud / count
            rows.append({
                "Feature": label,
                "Value": str(value),
                "Txns": int(count),
                "Fraud": int(fraud),
                "Fraud rate": rate,
                "Lift": rate / baseline if baseline else 0.0,
                "Confidence": wilson_lower_bound(int(fraud), int(count)),
            })
    out = pd.DataFrame(rows)
    return out.sort_values("Lift", ascending=False, ignore_index=True)


def mine_combinations(df: pd.DataFrame, dims: list[str], labels: dict,
                      max_depth: int = 3, min_support: int = 25,
                      min_lift: float = 1.0) -> pd.DataFrame:
    """Scan every combination of `dims` up to `max_depth` and rank by fraud lift.

    Returns one row per surviving segment with its defining conditions, support,
    fraud rate, lift over the current baseline, and Wilson confidence.
    """
    empty = pd.DataFrame(columns=["Depth", "Pattern", "Txns", "Fraud",
                                  "Fraud rate", "Lift", "Confidence", "_keys"])
    if df.empty or not dims:
        return empty
    baseline = df["is_fraud"].mean()
    if baseline == 0:
        return empty

    rows = []
    for depth in range(1, max_depth + 1):
        for combo in combinations(dims, depth):
            grp = df.groupby(list(combo), observed=True)["is_fraud"].agg(["count", "sum"])
            grp = grp[grp["count"] >= min_support]
            for values, (count, fraud) in grp.iterrows():
                values = values if isinstance(values, tuple) else (values,)
                rate = fraud / count
                lift = rate / baseline
                if lift < min_lift:
                    continue
                rows.append({
                    "Depth": depth,
                    "Pattern": "  +  ".join(
                        f"{labels.get(c, c)} = {v}" for c, v in zip(combo, values)),
                    "Txns": int(count),
                    "Fraud": int(fraud),
                    "Fraud rate": rate,
                    "Lift": lift,
                    "Confidence": wilson_lower_bound(int(fraud), int(count)),
                    "_keys": tuple(zip(combo, [str(v) for v in values])),
                })
    if not rows:
        return empty
    out = pd.DataFrame(rows)
    return out.sort_values(["Confidence", "Lift"], ascending=False, ignore_index=True)


def anomaly_scores(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """Robust (median/MAD) z-scores computed *within the current selection*.

    MAD rather than standard deviation so a handful of extreme values cannot
    inflate the spread and hide the outliers they are part of. Scored relative
    to what is on screen, so filtering to a segment re-bases the scan onto that
    segment's own normal.
    """
    if df.empty:
        return df.assign(anomaly_score=pd.Series(dtype=float))
    scored = df.copy()
    parts = []
    for col in numeric_cols:
        values = scored[col].astype(float)
        median = values.median()
        mad = (values - median).abs().median()
        scale = mad * 1.4826 if mad > 0 else values.std(ddof=0)
        z = (values - median).abs() / scale if scale and scale > 0 else pd.Series(
            0.0, index=values.index)
        scored[f"z_{col}"] = z
        parts.append(z)
    scored["anomaly_score"] = pd.concat(parts, axis=1).max(axis=1)
    return scored


def contrast_profile(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """How fraud rows differ from clear rows on each numeric column, in the selection."""
    fraud = df[df["is_fraud"] == 1]
    clear = df[df["is_fraud"] == 0]
    if fraud.empty or clear.empty:
        return pd.DataFrame(columns=["Metric", "Fraud avg", "Clear avg", "Delta %"])
    rows = []
    for col in numeric_cols:
        f_avg, c_avg = fraud[col].mean(), clear[col].mean()
        rows.append({
            "Metric": col.replace("_", " ").title(),
            "Fraud avg": round(f_avg, 2),
            "Clear avg": round(c_avg, 2),
            "Delta %": round((f_avg - c_avg) / c_avg * 100, 1) if c_avg else 0.0,
        })
    return pd.DataFrame(rows).sort_values(
        "Delta %", key=lambda s: s.abs(), ascending=False, ignore_index=True)
