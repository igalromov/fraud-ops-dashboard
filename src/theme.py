"""Design tokens and theming for the FRAUD ops dashboard.

The "Hackers" aesthetic lives in the chrome (near-black surfaces, neon accents,
monospace type). It deliberately does NOT drive the data encoding: colour here
carries fraud-status only, because a five-hue categorical palette was measured
against this surface and failed CVD separation (worst pair dE 1.6). See README.
"""

# -- surfaces & ink ----------------------------------------------------------
PAGE = "#05080a"
SURFACE = "#0b1210"
SURFACE_2 = "#0f1a16"
BORDER = "rgba(43, 245, 160, 0.14)"
BORDER_SOLID = "#16241e"
INK = "#e8f5ef"
MUTED = "#7d9b8f"
GRID = "#16241e"

# -- semantic data colours ---------------------------------------------------
# Validated on surface #0b1210: CVD dE 17.5, normal-vision dE 41.6,
# contrast 13.2:1 / 5.8:1. Always paired with a text label, never colour alone.
ACCENT = "#2bf5a0"   # CLEAR / safe / primary accent
FRAUD = "#ff4d4d"    # FRAUD / alert
WARN = "#fab219"
INFO = "#22d3ee"

# Sequential one-hue ramp for magnitude (monotone L, min adjacent dL 0.089).
GREEN_RAMP = ["#0d3b2a", "#125a3f", "#178257", "#1faa70", "#2bd68d", "#5cf3ad"]
# Plotly colorscale form (position, colour).
SCALE = [[i / (len(GREEN_RAMP) - 1), c] for i, c in enumerate(GREEN_RAMP)]

FONT = '"JetBrains Mono", "Cascadia Code", "Consolas", ui-monospace, monospace'

STATUS_COLORS = {"FRAUD": FRAUD, "CLEAR": ACCENT}


def plotly_layout(height: int = 340, showlegend: bool = False) -> dict:
    """Shared plotly layout: dark surface, hairline recessive grid, no in-figure title."""
    return dict(
        height=height,
        showlegend=showlegend,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        margin=dict(l=10, r=16, t=28, b=10),
        hoverlabel=dict(
            bgcolor=SURFACE_2,
            bordercolor=ACCENT,
            font=dict(family=FONT, size=12, color=INK),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED, size=11),
        ),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER_SOLID,
                   tickfont=dict(color=MUTED, size=11)),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER_SOLID,
                   tickfont=dict(color=MUTED, size=11)),
    )


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');

.stApp {{
    background:
        radial-gradient(ellipse 900px 500px at 12% -8%, rgba(43,245,160,0.07), transparent 60%),
        radial-gradient(ellipse 700px 400px at 92% 4%, rgba(34,211,238,0.05), transparent 60%),
        {PAGE};
    font-family: {FONT};
}}
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: {FONT}; color: {INK}; }}

/* thin scanline texture - decorative chrome only, never over data */
.stApp::before {{
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: repeating-linear-gradient(
        to bottom, rgba(43,245,160,0.022) 0 1px, transparent 1px 3px);
}}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px; }}

h1, h2, h3, h4 {{ font-family: {FONT} !important; color: {INK}; letter-spacing: -0.01em; }}
h1 {{ font-weight: 700; }}

/* ---- masthead ---- */
.fx-head {{
    border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
    background: linear-gradient(90deg, rgba(43,245,160,0.06), rgba(11,18,16,0.4) 45%);
    border-radius: 4px; padding: 14px 20px; margin-bottom: 4px;
}}
.fx-head .t {{ font-size: clamp(0.95rem, 1.35vw, 1.4rem); font-weight: 700; color: {INK}; letter-spacing: 0.06em; }}
.fx-head .t span {{ color: {ACCENT}; text-shadow: 0 0 18px rgba(43,245,160,0.5); }}
.fx-head .s {{ font-size: 0.76rem; color: {MUTED}; letter-spacing: 0.14em; margin-top: 3px; }}

/* ---- KPI tiles ---- */
.fx-grid {{
    display: grid; gap: 10px; margin-bottom: 6px;
    grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
}}
.fx-kpi {{
    border: 1px solid {BORDER}; background: {SURFACE};
    border-radius: 4px; padding: 12px 13px; height: 100%; min-width: 0;
    position: relative; overflow: hidden;
}}
.fx-kpi::after {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
    background: var(--kpi-accent, {ACCENT}); opacity: 0.85;
}}
.fx-kpi .k-label {{
    font-size: 0.6rem; color: {MUTED}; letter-spacing: 0.1em; text-transform: uppercase;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
/* Monospace is wide and these tiles sit five-across, so the value must scale with
   the viewport and never wrap - a wrapped "10,0 / 00" is unreadable. */
.fx-kpi .k-value {{
    font-size: clamp(1.05rem, 1.55vw, 1.8rem); font-weight: 700; line-height: 1.3;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: var(--kpi-accent, {ACCENT}); text-shadow: 0 0 22px var(--kpi-glow, rgba(43,245,160,0.30));
}}
.fx-kpi .k-sub {{
    font-size: 0.66rem; color: {MUTED};
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}

/* ---- panels & callouts ---- */
.fx-panel {{
    border: 1px solid {BORDER}; background: {SURFACE};
    border-radius: 4px; padding: 14px 18px; margin-bottom: 10px;
}}
.fx-alert {{
    border: 1px solid rgba(255,77,77,0.35); border-left: 3px solid {FRAUD};
    background: rgba(255,77,77,0.07); border-radius: 4px;
    padding: 11px 15px; margin-bottom: 9px; font-size: 0.85rem; color: {INK};
}}
.fx-ok {{
    border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
    background: rgba(43,245,160,0.06); border-radius: 4px;
    padding: 11px 15px; margin-bottom: 9px; font-size: 0.85rem; color: {INK};
}}
.fx-sec {{
    font-size: 0.72rem; color: {ACCENT}; letter-spacing: 0.18em;
    text-transform: uppercase; margin: 16px 0 6px; font-weight: 500;
}}
.fx-note {{ font-size: 0.76rem; color: {MUTED}; line-height: 1.55; }}
.fx-tag {{
    display: inline-block; border: 1px solid {BORDER}; border-radius: 3px;
    padding: 1px 7px; margin: 2px 4px 2px 0; font-size: 0.72rem; color: {ACCENT};
    background: rgba(43,245,160,0.07);
}}

/* ---- sidebar ---- */
section[data-testid="stSidebar"] {{
    background: {SURFACE}; border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] > div {{ width: 290px; }}
section[data-testid="stSidebar"] label p {{ font-size: 0.78rem; }}
section[data-testid="stSidebar"] * {{ font-family: {FONT}; }}
/* The blanket font rules above also hit Streamlit's Material Symbols glyphs,
   which then render as their literal ligature text ("keyboard_double_arrow_left").
   Restore the icon font wherever an icon actually lives. */
[data-testid="stIconMaterial"],
span[class*="material-symbols"],
.material-symbols-rounded, .material-symbols-outlined {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined" !important;
}}
section[data-testid="stSidebar"] .stButton button {{
    width: 100%; background: rgba(43,245,160,0.07); color: {ACCENT};
    border: 1px solid {BORDER}; border-radius: 3px;
    font-size: 0.74rem; letter-spacing: 0.05em; padding: 4px 8px;
}}
section[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(43,245,160,0.16); border-color: {ACCENT}; color: {ACCENT};
}}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px; border-bottom: 1px solid {BORDER}; background: transparent;
    flex-wrap: wrap;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent; color: {MUTED}; border-radius: 3px 3px 0 0;
    padding: 8px 14px; font-size: 0.74rem; letter-spacing: 0.12em; font-weight: 500;
}}
.stTabs [aria-selected="true"] {{
    background: rgba(43,245,160,0.09) !important; color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT};
}}

/* ---- widgets ---- */
.stDataFrame {{ border: 1px solid {BORDER}; border-radius: 4px; }}
div[data-testid="stMetricValue"] {{ color: {ACCENT}; font-family: {FONT}; }}
.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: {ACCENT}; }}
div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
    background: {SURFACE_2}; border-color: {BORDER}; font-size: 0.8rem;
}}
.stDownloadButton button {{
    background: rgba(43,245,160,0.09); color: {ACCENT};
    border: 1px solid {BORDER}; border-radius: 3px; font-size: 0.78rem;
}}
.stDownloadButton button:hover {{ background: rgba(43,245,160,0.18); border-color: {ACCENT}; }}
#MainMenu, footer {{ visibility: hidden; }}
</style>
"""
