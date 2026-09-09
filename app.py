"""FRAUD OPS // transaction intelligence console.

Streamlit dashboard for exploring a credit-card fraud dataset: filter down to a
segment, let the miner rank which feature combinations actually carry fraud, and
drill through to the underlying transactions.
"""
import pandas as pd
import streamlit as st

from src import charts, data as D, filters as F, patterns as P, theme as T

st.set_page_config(page_title="FRAUD OPS // Console", page_icon="🛡",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(T.CSS, unsafe_allow_html=True)

df_all = D.load_data()
BASELINE = df_all["is_fraud"].mean()
df = F.render_sidebar(df_all)
k = D.kpis(df, BASELINE)


# --------------------------------------------------------------------------- UI helpers
_TONES = {
    "accent": (T.ACCENT, "rgba(43,245,160,0.30)"),
    "fraud": (T.FRAUD, "rgba(255,77,77,0.32)"),
    "warn": (T.WARN, "rgba(250,178,25,0.28)"),
    "info": (T.INFO, "rgba(34,211,238,0.28)"),
}


def kpi_row(tiles: list[tuple[str, str, str, str]]) -> None:
    """Render KPI tiles in one wrapping grid.

    A fixed st.columns(5) crushes each tile to ~47px on a narrow viewport; a
    CSS grid reflows to 2-3 per row instead.
    """
    html = ['<div class="fx-grid">']
    for label, value, sub, tone in tiles:
        colour, glow = _TONES[tone]
        html.append(
            f'<div class="fx-kpi" style="--kpi-accent:{colour};--kpi-glow:{glow}">'
            f'<div class="k-label">{label}</div><div class="k-value">{value}</div>'
            f'<div class="k-sub">{sub}</div></div>')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="fx-sec">// {title}</div>', unsafe_allow_html=True)


def rate_table(frame: pd.DataFrame, height: int = 420) -> None:
    """Shared column formatting so every rate/lift table reads the same way.

    `Fraud rate` is carried as a 0-1 proportion; Streamlit's printf format appends
    a literal "%" without scaling, so it is converted to percentage points here
    rather than rendering 100% fraud as "1.00%".
    """
    frame = frame.assign(**{"Fraud rate": frame["Fraud rate"] * 100})
    st.dataframe(
        frame, width="stretch", hide_index=True, height=height,
        column_config={
            "Fraud rate": st.column_config.NumberColumn("Fraud rate", format="%.2f%%"),
            "Lift": st.column_config.NumberColumn("Lift", format="%.1fx",
                                                  help="Fraud rate vs the current selection baseline"),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence", min_value=0.0, max_value=1.0, format="%.3f",
                help="Wilson score lower bound - penalises small samples"),
            "Txns": st.column_config.NumberColumn("Txns", format="%d"),
            "Fraud": st.column_config.NumberColumn("Fraud", format="%d"),
        })


# --------------------------------------------------------------------------- masthead
st.markdown(
    '<div class="fx-head"><div class="t">FRAUD<span>_OPS</span> // TRANSACTION '
    'INTELLIGENCE CONSOLE</div><div class="s">CREDIT CARD FRAUD DETECTION &nbsp;·&nbsp; '
    '10,000 RECORDS &nbsp;·&nbsp; PATTERN &amp; ANOMALY ANALYSIS</div></div>',
    unsafe_allow_html=True)

tags = F.active_filter_tags()
share = len(df) / len(df_all) * 100
st.markdown(
    f'<div class="fx-note" style="margin:8px 0 14px">▸ <b style="color:{T.ACCENT}">'
    f'{len(df):,}</b> of {len(df_all):,} transactions selected '
    f'({share:.1f}%) &nbsp;·&nbsp; file baseline {BASELINE * 100:.2f}%'
    + ("<br>▸ filters: " + "".join(f'<span class="fx-tag">{t}</span>' for t in tags)
       if tags else "")
    + "</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown(
        '<div class="fx-alert">⚠ &nbsp;<b>NO TRANSACTIONS MATCH THE CURRENT FILTERS.</b>'
        '<br>Widen a range or hit <b>Reset all filters</b> in the sidebar.</div>',
        unsafe_allow_html=True)

# --------------------------------------------------------------------------- KPI row
kpi_row([
    ("Transactions", f"{k['transactions']:,}", f"{share:.1f}% of file", "accent"),
    ("Fraud detected", f"{k['fraud_count']:,}",
     f"of {int(df_all['is_fraud'].sum())} in file", "fraud"),
    ("Fraud rate", f"{k['fraud_rate'] * 100:.2f}%",
     f"baseline {BASELINE * 100:.2f}%", "fraud"),
    ("Lift vs baseline", f"{k['lift']:.1f}x", "segment concentration",
     "warn" if k["lift"] >= 2 else "info"),
    ("Fraud exposure", f"${k['exposure']:,.0f}",
     f"avg ${k['avg_fraud_amount']:,.0f}/case", "warn"),
])

st.write("")
tab_overview, tab_segments, tab_miner, tab_anomaly, tab_txn = st.tabs(
    ["OVERVIEW", "SEGMENTS", "PATTERN MINER", "ANOMALIES", "TRANSACTIONS"])


# --------------------------------------------------------------------------- OVERVIEW
with tab_overview:
    left, right = st.columns([1.15, 1])
    with left:
        section("fraud rate by hour of day")
        st.plotly_chart(charts.hour_profile(df), width="stretch",
                        config={"displayModeBar": False}, key="ov_hour")
    with right:
        section("volume by hour · fraud vs clear")
        st.plotly_chart(charts.hour_volume(df), width="stretch",
                        config={"displayModeBar": False}, key="ov_vol")

    left, right = st.columns([1, 1])
    with left:
        section("risk-flag stacking")
        st.plotly_chart(charts.risk_flag_chart(df), width="stretch",
                        config={"displayModeBar": False}, key="ov_flags")
        st.markdown(
            '<div class="fx-note">Each transaction is scored against 5 known risk '
            'conditions: night hours, foreign, location mismatch, device trust ≤ 40, '
            'and velocity ≥ 5. Fraud rate climbs steeply as conditions stack.</div>',
            unsafe_allow_html=True)
    with right:
        section("how fraud differs from clear")
        profile = P.contrast_profile(df, D.NUMERIC_COLS)
        if profile.empty:
            st.markdown('<div class="fx-note">Needs both fraud and clear rows in the '
                        'selection to compare.</div>', unsafe_allow_html=True)
        else:
            st.dataframe(profile, width="stretch", hide_index=True, height=250,
                         column_config={"Delta %": st.column_config.NumberColumn(
                             "Delta %", format="%.1f%%",
                             help="Fraud average vs clear average")})

    section("top single-feature drivers")
    lift = P.column_lift(df, D.DIMENSIONS)
    if lift.empty:
        st.markdown('<div class="fx-note">No data in the current selection.</div>',
                    unsafe_allow_html=True)
    else:
        rate_table(lift.head(14), height=520)


# --------------------------------------------------------------------------- SEGMENTS
with tab_segments:
    dim_labels = list(D.DIMENSIONS.values())
    dim_by_label = {v: kk for kk, v in D.DIMENSIONS.items()}

    c1, c2, c3 = st.columns([1, 1, 1])
    pick = c1.selectbox("Breakdown dimension", dim_labels, index=0)
    metric = c2.radio("Measure", ["Fraud rate", "Volume"], horizontal=True)
    numeric_pick = c3.selectbox("Distribution column", D.NUMERIC_COLS, index=2)

    left, right = st.columns([1, 1])
    with left:
        section(f"{pick.lower()} · {metric.lower()}")
        st.plotly_chart(
            charts.dimension_breakdown(df, dim_by_label[pick], pick,
                                       "rate" if metric == "Fraud rate" else "count"),
            width="stretch", config={"displayModeBar": False}, key="sg_break")
    with right:
        section(f"{numeric_pick.replace('_', ' ')} · fraud vs clear")
        st.plotly_chart(charts.distribution_split(df, numeric_pick),
                        width="stretch", config={"displayModeBar": False},
                        key="sg_dist")

    section("two-dimension fraud-rate matrix")
    c1, c2, c3 = st.columns([1, 1, 1])
    row_pick = c1.selectbox("Rows", dim_labels, index=0, key="hm_row")
    col_pick = c2.selectbox("Columns", dim_labels, index=6, key="hm_col")
    min_sup = c3.slider("Min transactions per cell", 1, 100, 10, key="hm_sup",
                        help="Cells with less support are left blank rather than "
                             "rendered as the hottest colour on a 1-of-2 sample.")
    st.plotly_chart(
        charts.lift_heatmap(df, dim_by_label[row_pick], dim_by_label[col_pick],
                            row_pick, col_pick, min_sup),
        width="stretch", config={"displayModeBar": False}, key="sg_heat")

    section("free scatter explorer")
    c1, c2 = st.columns(2)
    x_pick = c1.selectbox("X axis", D.NUMERIC_COLS, index=2, key="sc_x")
    y_pick = c2.selectbox("Y axis", D.NUMERIC_COLS, index=0, key="sc_y")
    st.plotly_chart(charts.scatter_explorer(df, x_pick, y_pick),
                    width="stretch", config={"displayModeBar": False},
                    key="sg_scatter")


# --------------------------------------------------------------------------- MINER
with tab_miner:
    st.markdown(
        '<div class="fx-ok">▸ <b>Automated pattern discovery.</b> Every combination of '
        'the selected dimensions is scanned and ranked by how much it concentrates '
        'fraud. Ranking uses a <b>Wilson score lower bound</b>, so a 2-of-2 fluke '
        'cannot outrank a well-evidenced segment.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    dims_pick = c1.multiselect(
        "Dimensions to combine", list(D.DIMENSIONS.values()),
        default=list(D.DIMENSIONS.values()), key="mn_dims")
    depth = c2.slider("Max combination depth", 1, 3, 3, key="mn_depth")
    support = c3.slider("Min transactions", 5, 200, 25, step=5, key="mn_sup",
                        help="Lower this to surface small but extreme cells.")

    dim_by_label = {v: kk for kk, v in D.DIMENSIONS.items()}
    dims = [dim_by_label[label] for label in dims_pick]
    mined = P.mine_combinations(df, dims, D.DIMENSIONS, depth, support)

    if mined.empty:
        st.markdown(
            '<div class="fx-note">No pattern clears the current support threshold. '
            'Lower <b>Min transactions</b> or widen the filters.</div>',
            unsafe_allow_html=True)
    else:
        top = mined.iloc[0]
        st.markdown(
            f'<div class="fx-alert">⚑ <b>STRONGEST PATTERN:</b> {top["Pattern"]}'
            f'<br>&nbsp;&nbsp;&nbsp;<b style="color:{T.FRAUD}">'
            f'{top["Fraud rate"] * 100:.1f}% fraud</b> '
            f'({int(top["Fraud"])} of {int(top["Txns"])} transactions) '
            f'· <b>{top["Lift"]:.0f}x</b> the selection baseline</div>',
            unsafe_allow_html=True)

        section(f"{len(mined):,} patterns found · ranked by confidence")
        rate_table(mined.drop(columns=["_keys"]).head(60), height=560)
        st.markdown(
            '<div class="fx-note">▸ <b>Lift</b> is the fraud rate divided by the current '
            'selection baseline. <b>Confidence</b> is the lower bound of the 95% Wilson '
            'interval — sort by it to see patterns backed by real evidence, and raise '
            '<b>Max combination depth</b> to find interactions single columns hide.</div>',
            unsafe_allow_html=True)

        csv = mined.drop(columns=["_keys"]).to_csv(index=False).encode("utf-8")
        st.download_button("⤓  Export patterns (CSV)", csv,
                           "fraud_patterns.csv", "text/csv")


# --------------------------------------------------------------------------- ANOMALIES
with tab_anomaly:
    st.markdown(
        '<div class="fx-ok">▸ <b>Outlier scan.</b> Robust z-scores (median / MAD) are '
        'computed <b>within the current selection</b>, so filtering to a segment '
        're-bases the scan onto that segment\'s own normal rather than the whole file.</div>',
        unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="fx-note">No data in the current selection.</div>',
                    unsafe_allow_html=True)
    else:
        scored = P.anomaly_scores(df, D.NUMERIC_COLS)
        threshold = st.slider("Anomaly score threshold (robust z)", 1.0, 10.0, 3.0, 0.5,
                              key="an_thr")
        outliers = scored[scored["anomaly_score"] >= threshold]

        out_rate = outliers["is_fraud"].mean() if len(outliers) else 0.0
        norm = scored[scored["anomaly_score"] < threshold]
        norm_rate = norm["is_fraud"].mean() if len(norm) else 0.0
        kpi_row([
            ("Outliers flagged", f"{len(outliers):,}",
             f"{len(outliers) / len(scored) * 100:.1f}% of selection", "warn"),
            ("Fraud in outliers", f"{out_rate * 100:.2f}%",
             f"{int(outliers['is_fraud'].sum())} cases", "fraud"),
            ("Fraud in the rest", f"{norm_rate * 100:.2f}%",
             f"{int(norm['is_fraud'].sum())} cases", "accent"),
            ("Outlier lift", f"{(out_rate / norm_rate):.1f}x" if norm_rate else "n/a",
             "outlier vs rest", "info"),
        ])

        st.write("")
        left, right = st.columns([1, 1])
        with left:
            section("anomaly score distribution")
            st.plotly_chart(charts.distribution_split(scored, "anomaly_score"),
                            width="stretch",
                            config={"displayModeBar": False}, key="an_dist")
        with right:
            section("risk flags vs fraud rate")
            st.plotly_chart(charts.risk_flag_chart(df), width="stretch",
                            config={"displayModeBar": False}, key="an_flags")

        section("highest-scoring transactions")
        cols = (["transaction_id", "anomaly_score", "risk_flag_count", "is_fraud_label",
                 "amount", "transaction_hour", "merchant_category",
                 "device_trust_score", "velocity_last_24h"])
        worst = outliers.nlargest(40, "anomaly_score")[cols] if len(outliers) else \
            scored.nlargest(40, "anomaly_score")[cols]
        st.dataframe(
            worst, width="stretch", hide_index=True, height=420,
            column_config={
                "anomaly_score": st.column_config.NumberColumn("Anomaly", format="%.2f"),
                "risk_flag_count": st.column_config.NumberColumn("Flags", format="%d"),
                "is_fraud_label": st.column_config.TextColumn("Status"),
                "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            })


# --------------------------------------------------------------------------- TXN TABLE
with tab_txn:
    section("transaction drill-down")
    base_cols = ["transaction_id", "is_fraud_label", "risk_flag_count", "amount",
                 "transaction_hour", "time_bucket", "merchant_category",
                 "foreign_flag", "mismatch_flag", "device_trust_score",
                 "velocity_last_24h", "cardholder_age"]
    chosen = st.multiselect("Columns", base_cols, default=base_cols, key="tx_cols")
    sort_by = st.selectbox("Sort by", chosen or base_cols, index=0, key="tx_sort")
    ascending = st.radio("Order", ["Descending", "Ascending"], horizontal=True,
                         key="tx_order") == "Ascending"

    view = df[chosen] if chosen else df[base_cols]
    view = view.sort_values(sort_by, ascending=ascending)
    st.markdown(f'<div class="fx-note">Showing up to 1,000 of {len(view):,} rows.</div>',
                unsafe_allow_html=True)
    st.dataframe(
        view.head(1000), width="stretch", hide_index=True, height=560,
        column_config={
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "is_fraud_label": st.column_config.TextColumn("Status"),
            "risk_flag_count": st.column_config.NumberColumn("Flags", format="%d"),
        })
    st.download_button("⤓  Export current selection (CSV)",
                       view.to_csv(index=False).encode("utf-8"),
                       "fraud_selection.csv", "text/csv")
