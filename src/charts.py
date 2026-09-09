"""Plotly figure builders.

Encoding rules enforced here (see README for the measurements behind them):
  * colour carries fraud-status only - never merchant category
  * category identity is carried by the axis label on a sorted single-hue bar
  * no dual-axis charts: rate and volume are separate panels
  * every mark gets a hover tooltip
"""
import pandas as pd
import plotly.graph_objects as go

from . import theme as T


def _empty(msg: str = "NO DATA IN CURRENT SELECTION") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False,
                       font=dict(family=T.FONT, size=13, color=T.MUTED))
    fig.update_layout(**T.plotly_layout(height=260))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def hour_profile(df: pd.DataFrame) -> go.Figure:
    """Fraud rate by hour. Volume lives in a separate chart - never a second y-axis."""
    if df.empty:
        return _empty()
    g = df.groupby("transaction_hour", observed=True)["is_fraud"].agg(["count", "sum"])
    g = g.reindex(range(24), fill_value=0)
    rate = (g["sum"] / g["count"].replace(0, pd.NA) * 100).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=g.index, y=rate, mode="lines+markers", name="Fraud rate",
        line=dict(color=T.FRAUD, width=2),
        marker=dict(size=8, color=T.FRAUD, line=dict(width=2, color=T.SURFACE)),
        fill="tozeroy", fillcolor="rgba(255,77,77,0.13)",
        hovertemplate="<b>%{x:02d}:00</b><br>Fraud rate %{y:.2f}%"
                      "<br>%{customdata[0]} fraud / %{customdata[1]} txns<extra></extra>",
        customdata=list(zip(g["sum"], g["count"])),
    ))
    baseline = df["is_fraud"].mean() * 100
    fig.add_hline(y=baseline, line=dict(color=T.MUTED, width=1, dash="dot"),
                  annotation_text=f"selection avg {baseline:.2f}%",
                  annotation_font=dict(color=T.MUTED, size=10, family=T.FONT))
    fig.update_layout(**T.plotly_layout(height=310))
    fig.update_xaxes(title_text="Hour of day", dtick=2,
                     title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text="Fraud rate %", title_font=dict(size=11, color=T.MUTED))
    return fig


def hour_volume(df: pd.DataFrame) -> go.Figure:
    """Transaction volume by hour, split fraud vs clear. Two series -> legend."""
    if df.empty:
        return _empty()
    g = df.groupby(["transaction_hour", "is_fraud_label"], observed=True).size().unstack(
        fill_value=0).reindex(range(24), fill_value=0)
    fig = go.Figure()
    for label in ("CLEAR", "FRAUD"):
        if label in g.columns:
            fig.add_trace(go.Bar(
                x=g.index, y=g[label], name=label,
                marker=dict(color=T.STATUS_COLORS[label],
                            line=dict(width=2, color=T.SURFACE)),
                hovertemplate="<b>%{x:02d}:00</b><br>" + label + " %{y}<extra></extra>",
            ))
    fig.update_layout(**T.plotly_layout(height=310, showlegend=True), barmode="stack",
                      bargap=0.25)
    fig.update_xaxes(title_text="Hour of day", dtick=2,
                     title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text="Transactions", title_font=dict(size=11, color=T.MUTED))
    return fig


def dimension_breakdown(df: pd.DataFrame, column: str, label: str,
                        metric: str = "rate") -> go.Figure:
    """Sorted single-hue horizontal bars. Identity is the axis label, not the colour."""
    if df.empty:
        return _empty()
    g = df.groupby(column, observed=True)["is_fraud"].agg(["count", "sum"])
    g = g[g["count"] > 0]
    if g.empty:
        return _empty()
    g["rate"] = g["sum"] / g["count"] * 100
    value = g["rate"] if metric == "rate" else g["count"]
    g = g.assign(_v=value).sort_values("_v")

    suffix = "%" if metric == "rate" else ""
    fig = go.Figure(go.Bar(
        x=g["_v"], y=[str(i) for i in g.index], orientation="h",
        marker=dict(color=T.FRAUD if metric == "rate" else T.ACCENT,
                    line=dict(width=2, color=T.SURFACE)),
        text=[f"{v:,.2f}{suffix}" if metric == "rate" else f"{v:,.0f}" for v in g["_v"]],
        textposition="outside",
        textfont=dict(family=T.FONT, size=11, color=T.INK),
        customdata=list(zip(g["sum"], g["count"])),
        hovertemplate="<b>%{y}</b><br>%{customdata[0]} fraud / %{customdata[1]} txns<extra></extra>",
    ))
    fig.update_layout(**T.plotly_layout(height=max(240, 46 * len(g))))
    # Headroom so the outside value label is not clipped on the longest bar.
    top = float(g["_v"].max()) if len(g) else 1.0
    fig.update_xaxes(title_text="Fraud rate %" if metric == "rate" else "Transactions",
                     title_font=dict(size=11, color=T.MUTED),
                     range=[0, top * 1.22 if top > 0 else 1])
    fig.update_yaxes(title_text=label, title_font=dict(size=11, color=T.MUTED))
    return fig


def lift_heatmap(df: pd.DataFrame, row_col: str, col_col: str,
                 row_label: str, col_label: str, min_support: int = 10) -> go.Figure:
    """Fraud rate across two dimensions on the validated one-hue ramp.

    Cells below `min_support` are blanked rather than shown: a 1-of-2 cell would
    otherwise render as the hottest thing on screen.
    """
    if df.empty or row_col == col_col:
        return _empty("PICK TWO DIFFERENT DIMENSIONS")
    counts = df.pivot_table(index=row_col, columns=col_col, values="is_fraud",
                            aggfunc="count", observed=True)
    sums = df.pivot_table(index=row_col, columns=col_col, values="is_fraud",
                          aggfunc="sum", observed=True)
    if counts.empty:
        return _empty()
    rate = (sums / counts * 100).where(counts >= min_support)

    cd = [[[0 if pd.isna(sums.iloc[i, j]) else int(sums.iloc[i, j]),
            0 if pd.isna(counts.iloc[i, j]) else int(counts.iloc[i, j])]
           for j in range(rate.shape[1])] for i in range(rate.shape[0])]

    fig = go.Figure(go.Heatmap(
        z=rate.values, x=[str(c) for c in rate.columns], y=[str(i) for i in rate.index],
        colorscale=T.SCALE, hoverongaps=False,
        customdata=cd, xgap=2, ygap=2,
        hovertemplate="<b>%{y}</b> / <b>%{x}</b><br>Fraud rate %{z:.2f}%"
                      "<br>%{customdata[0]} fraud / %{customdata[1]} txns<extra></extra>",
        colorbar=dict(title=dict(text="Fraud %", font=dict(color=T.MUTED, size=11)),
                      tickfont=dict(color=T.MUTED, size=10), outlinewidth=0, thickness=12),
    ))
    # Cell values are drawn as annotations rather than `texttemplate` so each one
    # can pick its own ink: a single light colour vanishes on the bright end of the
    # ramp, and a single dark one vanishes on the dark end.
    hottest = pd.Series(rate.values.ravel()).max(skipna=True)
    for i, row_name in enumerate(rate.index):
        for j, col_name in enumerate(rate.columns):
            value = rate.iloc[i, j]
            if pd.isna(value):
                continue
            share = value / hottest if hottest and hottest > 0 else 0
            fig.add_annotation(
                x=str(col_name), y=str(row_name), text=f"{value:.1f}%", showarrow=False,
                font=dict(family=T.FONT, size=11,
                          color=T.PAGE if share >= 0.55 else T.INK))

    fig.update_layout(**T.plotly_layout(height=max(300, 56 * max(len(rate.index), 4))))
    fig.update_xaxes(title_text=col_label, title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text=row_label, title_font=dict(size=11, color=T.MUTED))
    return fig


def distribution_split(df: pd.DataFrame, column: str) -> go.Figure:
    """Normalised histogram of a numeric column, FRAUD vs CLEAR. Two series -> legend."""
    if df.empty:
        return _empty()
    fig = go.Figure()
    for label in ("CLEAR", "FRAUD"):
        sub = df[df["is_fraud_label"] == label]
        if sub.empty:
            continue
        fig.add_trace(go.Histogram(
            x=sub[column], name=label, histnorm="probability density",
            marker=dict(color=T.STATUS_COLORS[label],
                        line=dict(width=1, color=T.SURFACE)),
            opacity=0.72, nbinsx=34,
            hovertemplate=label + "<br>%{x}<br>density %{y:.4f}<extra></extra>",
        ))
    fig.update_layout(**T.plotly_layout(height=300, showlegend=True), barmode="overlay")
    fig.update_xaxes(title_text=column.replace("_", " ").title(),
                     title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text="Density", title_font=dict(size=11, color=T.MUTED))
    return fig


def scatter_explorer(df: pd.DataFrame, x: str, y: str, sample: int = 4000) -> go.Figure:
    """Two numeric columns, coloured by fraud status only (a CVD-validated pair).

    Clear rows are sampled and drawn first so the 1.5% fraud minority stays on top
    and visible instead of being buried under the majority class.
    """
    if df.empty:
        return _empty()
    fraud = df[df["is_fraud"] == 1]
    clear = df[df["is_fraud"] == 0]
    if len(clear) > sample:
        clear = clear.sample(sample, random_state=0)

    fig = go.Figure()
    for sub, label, size, opacity in ((clear, "CLEAR", 5, 0.45), (fraud, "FRAUD", 9, 0.95)):
        if sub.empty:
            continue
        fig.add_trace(go.Scattergl(
            x=sub[x], y=sub[y], mode="markers", name=label,
            marker=dict(color=T.STATUS_COLORS[label], size=size, opacity=opacity,
                        line=dict(width=1 if label == "FRAUD" else 0, color=T.SURFACE)),
            hovertemplate=label + "<br>%{x}<br>%{y}<extra></extra>",
        ))
    fig.update_layout(**T.plotly_layout(height=440, showlegend=True))
    fig.update_xaxes(title_text=x.replace("_", " ").title(),
                     title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text=y.replace("_", " ").title(),
                     title_font=dict(size=11, color=T.MUTED))
    return fig


def risk_flag_chart(df: pd.DataFrame) -> go.Figure:
    """Fraud rate against the number of risk conditions a transaction trips."""
    if df.empty:
        return _empty()
    g = df.groupby("risk_flag_count", observed=True)["is_fraud"].agg(["count", "sum"])
    g = g[g["count"] > 0]
    if g.empty:
        return _empty()
    g["rate"] = g["sum"] / g["count"] * 100
    fig = go.Figure(go.Bar(
        x=[str(i) for i in g.index], y=g["rate"],
        marker=dict(color=g["rate"], colorscale=T.SCALE,
                    line=dict(width=2, color=T.SURFACE)),
        text=[f"{v:.1f}%" for v in g["rate"]], textposition="outside",
        textfont=dict(family=T.FONT, size=11, color=T.INK),
        customdata=list(zip(g["sum"], g["count"])),
        hovertemplate="<b>%{x} risk flags</b><br>Fraud rate %{y:.2f}%"
                      "<br>%{customdata[0]} fraud / %{customdata[1]} txns<extra></extra>",
    ))
    fig.update_layout(**T.plotly_layout(height=300))
    fig.update_xaxes(title_text="Risk flags tripped (0-5)",
                     title_font=dict(size=11, color=T.MUTED))
    fig.update_yaxes(title_text="Fraud rate %", title_font=dict(size=11, color=T.MUTED),
                     range=[0, max(float(g["rate"].max()) * 1.18, 1)])
    return fig
