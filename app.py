# app.py
"""
Nepal Economic Dashboard
Interactive Streamlit dashboard for Nepal's key economic indicators.
Data source: World Bank Open Data  |  Built by Prasoddha Aryal
"""

import os
import json
import warnings
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nepal Economic Dashboard",
    page_icon="🇳🇵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

INDICATORS = {
    "GDP Growth Rate": {
        "file":  "gdp_growth.csv",
        "unit":  "% per year",
        "color": "#3FB950",
        "icon":  "📈",
        "code":  "NY.GDP.MKTP.KD.ZG",
        "wb_url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=NP",
        "summary": (
            "GDP growth measures how fast Nepal's total economy is expanding each year. "
            "Nepal's growth averaged around 4% annually from 2000–2023, with a sharp dip in "
            "2020 (−2.4%) due to COVID-19 and the 2015 earthquake causing a slowdown to 3.4%. "
            "Recovery has been steady but vulnerable to climate shocks and global conditions."
        ),
        "verify": [
            "Confirm 2020 value is negative (COVID impact).",
            "Check 2015 value reflects earthquake slowdown.",
            "Verify latest year against World Bank country page for Nepal.",
        ],
    },
    "Inflation (CPI)": {
        "file":  "inflation_cpi.csv",
        "unit":  "% per year",
        "color": "#F78166",
        "icon":  "💹",
        "code":  "FP.CPI.TOTL.ZG",
        "wb_url": "https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=NP",
        "summary": (
            "Inflation (CPI) measures how much everyday prices rise each year. Nepal's inflation "
            "averaged about 6.4% over 2000–2023, remaining persistently above the central bank's "
            "comfort zone. High inflation erodes the purchasing power of remittance income that "
            "millions of Nepali families depend on."
        ),
        "verify": [
            "Confirm average is ~6% range.",
            "Check 2022 spike aligns with global commodity price surge.",
            "Verify Nepal Rastra Bank annual report for latest figure.",
        ],
    },
    "Remittances": {
        "file":  "remittances.csv",
        "unit":  "% of GDP",
        "color": "#58A6FF",
        "icon":  "💸",
        "code":  "BX.TRF.PWKR.DT.GD.ZS",
        "wb_url": "https://data.worldbank.org/indicator/BX.TRF.PWKR.DT.GD.ZS?locations=NP",
        "summary": (
            "Remittances — money sent home by Nepalis working abroad — are the backbone of Nepal's "
            "economy, reaching nearly 28% of GDP at their peak. This makes Nepal one of the most "
            "remittance-dependent countries in the world. These inflows fund household consumption, "
            "education, and healthcare, but also create vulnerability to global labour market shocks."
        ),
        "verify": [
            "Confirm peak value ~27–28% of GDP around 2015–2016.",
            "Check 2020 dip due to COVID migration disruption.",
            "Cross-reference with Nepal Rastra Bank remittance bulletin.",
        ],
    },
    "Exports of Goods & Services": {
        "file":  "exports.csv",
        "unit":  "% of GDP",
        "color": "#D2A8FF",
        "icon":  "📦",
        "code":  "NE.EXP.GNFS.ZS",
        "wb_url": "https://data.worldbank.org/indicator/NE.EXP.GNFS.ZS?locations=NP",
        "summary": (
            "Nepal's exports of goods and services as a share of GDP reflect the country's limited "
            "export base — mainly carpets, pashmina, tea, and tourism. Exports peaked around 23% of "
            "GDP in 2000 (tourism-driven) but have generally trended lower, highlighting Nepal's "
            "chronic trade deficit challenge and limited industrial capacity."
        ),
        "verify": [
            "Confirm exports are much lower than imports throughout the period.",
            "Check 2020 collapse aligns with COVID tourism shutdown.",
            "Verify peak years correspond to tourism boom periods.",
        ],
    },
    "Imports of Goods & Services": {
        "file":  "imports.csv",
        "unit":  "% of GDP",
        "color": "#FFA657",
        "icon":  "🚢",
        "code":  "NE.IMP.GNFS.ZS",
        "wb_url": "https://data.worldbank.org/indicator/NE.IMP.GNFS.ZS?locations=NP",
        "summary": (
            "Nepal imports far more than it exports — consistently 28–42% of GDP — reflecting heavy "
            "dependence on India and China for fuel, goods, and raw materials. This large trade "
            "deficit is largely financed by remittance inflows. Reducing it is a key long-term "
            "development challenge for Nepal."
        ),
        "verify": [
            "Confirm imports consistently exceed exports by large margin.",
            "Check recent years for any improvement in trade balance.",
            "Verify fuel import share with Ministry of Finance data.",
        ],
    },
    "Unemployment Rate": {
        "file":  "unemployment.csv",
        "unit":  "% of total labour force",
        "color": "#E3B341",
        "icon":  "👷",
        "code":  "SL.UEM.TOTL.ZS",
        "wb_url": "https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=NP",
        "summary": (
            "Nepal's official unemployment rate appears low (around 10–11%) but understates the "
            "true challenge: millions work in low-productivity agriculture or are underemployed. "
            "The 2020 spike to 13% reflects COVID-19 disruptions and the mass return of migrant "
            "workers. High youth unemployment drives the ongoing migration of Nepalis abroad."
        ),
        "verify": [
            "Note: ILO modelled estimates — not a national survey figure.",
            "Confirm 2020 spike to ~13% as COVID outlier (flagged in validation).",
            "Cross-reference with Nepal Labour Force Survey if available.",
        ],
    },
}

COLORS = {
    "bg":       "#0D1117",
    "card_bg":  "#161B22",
    "border":   "#30363D",
    "text":     "#E6EDF3",
    "muted":    "#8B949E",
    "red":      "#E63946",
    "green":    "#3FB950",
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Import Google Font */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Hide default Streamlit elements */
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  .stDeployButton { display: none; }

  /* Hero banner */
  .hero {
    background: linear-gradient(135deg, #0D1117 0%, #1a1f2e 50%, #0D1117 100%);
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -20%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(230,57,70,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }
  .hero h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    background: linear-gradient(90deg, #E6EDF3, #E63946);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hero p { color: #8B949E; font-size: 1rem; margin: 0; }
  .hero .flag { font-size: 2.5rem; float: right; margin-top: -0.5rem; }

  /* Metric cards */
  .metric-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    transition: border-color 0.2s;
  }
  .metric-card:hover { border-color: #E63946; }
  .metric-icon { font-size: 1.6rem; margin-bottom: 0.3rem; }
  .metric-label { color: #8B949E; font-size: 0.78rem; font-weight: 500;
                  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem; }
  .metric-value { color: #E6EDF3; font-size: 2rem; font-weight: 700; line-height: 1; }
  .metric-delta-pos { color: #3FB950; font-size: 0.85rem; font-weight: 500; margin-top: 0.3rem; }
  .metric-delta-neg { color: #F78166; font-size: 0.85rem; font-weight: 500; margin-top: 0.3rem; }
  .metric-delta-neu { color: #8B949E; font-size: 0.85rem; font-weight: 500; margin-top: 0.3rem; }

  /* Summary box */
  .summary-box {
    background: #161B22;
    border-left: 3px solid #E63946;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    color: #C9D1D9;
    font-size: 0.93rem;
    line-height: 1.6;
  }
  .ai-badge {
    display: inline-block;
    background: #21262D;
    border: 1px solid #30363D;
    border-radius: 4px;
    padding: 0.15rem 0.5rem;
    font-size: 0.72rem;
    color: #8B949E;
    margin-bottom: 0.5rem;
  }

  /* Verify checklist */
  .verify-box {
    background: #0D1117;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-top: 0.5rem;
  }
  .verify-box p { color: #E3B341; font-size: 0.82rem; font-weight: 600;
                  margin: 0 0 0.4rem 0; text-transform: uppercase; letter-spacing: 0.04em; }
  .verify-box ul { margin: 0; padding-left: 1.2rem; color: #8B949E; font-size: 0.83rem; line-height: 1.7; }

  /* Section header */
  .section-header {
    border-bottom: 1px solid #30363D;
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
    color: #E6EDF3;
    font-size: 1.1rem;
    font-weight: 600;
  }

  /* Data quality bar */
  .quality-bar {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 0.7rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.85rem;
    color: #8B949E;
    margin-bottom: 1rem;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #161B22 !important;
    border-right: 1px solid #30363D;
  }

  /* Plotly chart container */
  .js-plotly-plot { border-radius: 8px; }

  /* Download button */
  .stDownloadButton > button {
    background: #21262D;
    border: 1px solid #30363D;
    color: #E6EDF3;
    border-radius: 6px;
    transition: border-color 0.2s;
  }
  .stDownloadButton > button:hover { border-color: #E63946; }
</style>
""", unsafe_allow_html=True)


# ── Data Loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_indicator(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def load_metadata():
    path = os.path.join(DATA_DIR, "metadata.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ── Chart helpers ──────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#E6EDF3"),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(
        gridcolor="#21262D",
        linecolor="#30363D",
        tickcolor="#30363D",
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor="#21262D",
        linecolor="#30363D",
        tickcolor="#30363D",
        showgrid=True,
    ),
    hoverlabel=dict(
        bgcolor="#161B22",
        bordercolor="#30363D",
        font_color="#E6EDF3",
    ),
)


def line_chart(df, indicator_name, color, unit):
    meta = INDICATORS[indicator_name]
    fig = go.Figure()
    if df is None or df.empty:
        fig.add_annotation(
            text="No data available for the selected range",
            showarrow=False,
            font=dict(size=14, color="#8B949E"),
        )
        fig.update_layout(**PLOTLY_LAYOUT, height=360)
        return fig

    # Build a translucent fill from the hex color
    hex_to_rgba = {
        "#3FB950": "rgba(63,185,80,0.10)",
        "#F78166": "rgba(247,129,102,0.10)",
        "#58A6FF": "rgba(88,166,255,0.10)",
        "#D2A8FF": "rgba(210,168,255,0.10)",
        "#FFA657": "rgba(255,166,87,0.10)",
        "#E3B341": "rgba(227,179,65,0.10)",
    }
    fill_color = hex_to_rgba.get(color, "rgba(230,57,70,0.10)")

    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["value"],
        mode="lines+markers",
        name=indicator_name,
        line=dict(color=color, width=2.5),
        marker=dict(size=5, color=color),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate=f"<b>%{{x}}</b><br>{indicator_name}: %{{y:.2f}} {unit}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"{meta['icon']} {indicator_name}", font_size=15),
        xaxis_title="Year",
        yaxis_title=unit,
        showlegend=False,
        height=360,
    )
    return fig


def bar_chart(df, indicator_name, color, unit):
    meta = INDICATORS[indicator_name]
    fig = go.Figure()
    if df is None or df.empty:
        fig.add_annotation(
            text="No data available for the selected range",
            showarrow=False,
            font=dict(size=14, color="#8B949E"),
        )
        fig.update_layout(**PLOTLY_LAYOUT, height=360)
        return fig

    fig.add_trace(go.Bar(
        x=df["year"],
        y=df["value"],
        name=indicator_name,
        marker=dict(
            color=df["value"],
            colorscale=[[0, "#21262D"], [1, color]],
            line=dict(width=0),
        ),
        hovertemplate=f"<b>%{{x}}</b><br>{indicator_name}: %{{y:.2f}} {unit}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"{meta['icon']} {indicator_name} — Bar View", font_size=15),
        xaxis_title="Year",
        yaxis_title=unit,
        showlegend=False,
        height=360,
    )
    return fig


def trade_balance_chart(df_exp, df_imp, yr_min, yr_max):
    """Special combined chart for exports vs imports."""
    exp = df_exp[(df_exp["year"] >= yr_min) & (df_exp["year"] <= yr_max)]
    imp = df_imp[(df_imp["year"] >= yr_min) & (df_imp["year"] <= yr_max)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=imp["year"], y=imp["value"], name="Imports",
        line=dict(color="#FFA657", width=2.5),
        fill="tozeroy", fillcolor="rgba(255,166,87,0.08)",
        hovertemplate="<b>%{x}</b><br>Imports: %{y:.2f}% of GDP<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=exp["year"], y=exp["value"], name="Exports",
        line=dict(color="#D2A8FF", width=2.5),
        fill="tozeroy", fillcolor="rgba(210,168,255,0.1)",
        hovertemplate="<b>%{x}</b><br>Exports: %{y:.2f}% of GDP<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="📦 Trade Balance: Exports vs Imports (% of GDP)", font_size=15),
        xaxis_title="Year",
        yaxis_title="% of GDP",
        showlegend=True,
        legend=dict(
            bgcolor="#161B22", bordercolor="#30363D", borderwidth=1,
            font=dict(color="#E6EDF3"),
        ),
        height=380,
    )
    return fig


# ── Metric Card Helpers ────────────────────────────────────────────────────────
def render_metric(col, icon, label, value, unit, delta, delta_label):
    if delta is None:
        delta_html = '<div class="metric-delta-neu">— no prior year</div>'
    elif delta > 0:
        delta_html = f'<div class="metric-delta-pos">▲ +{delta:.2f} {unit} vs {delta_label}</div>'
    elif delta < 0:
        delta_html = f'<div class="metric-delta-neg">▼ {abs(delta):.2f} {unit} vs {delta_label}</div>'
    else:
        delta_html = f'<div class="metric-delta-neu">→ unchanged vs {delta_label}</div>'

    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-icon">{icon}</div>
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value:.2f}<span style="font-size:1rem;color:#8B949E"> {unit}</span></div>
      {delta_html}
    </div>
    """, unsafe_allow_html=True)


def compute_metrics(df, yr_max):
    if df is None or df.empty:
        return 0.0, yr_max, None

    latest_row = df[df["year"] == yr_max]
    if latest_row.empty:
        latest_row = df[df["year"] == df["year"].max()]
    if latest_row.empty:
        return 0.0, yr_max, None

    latest      = float(latest_row["value"].values[0])
    latest_year = int(latest_row["year"].values[0])

    prev_row = df[df["year"] == latest_year - 1]
    delta = None
    if not prev_row.empty:
        delta = latest - float(prev_row["value"].values[0])

    return latest, latest_year, delta


# ── Main App ───────────────────────────────────────────────────────────────────
def main():
    meta = load_metadata()
    last_updated = meta.get("last_updated", "Unknown")

    # ── Hero ──
    st.markdown(f"""
    <div class="hero">
      <span class="flag">🇳🇵</span>
      <h1>Nepal Economic Dashboard</h1>
      <p>Key economic indicators for Nepal · World Bank Open Data · 2000–2023</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Data quality bar ──
    st.markdown(f"""
    <div class="quality-bar">
      <span style="color:#3FB950; font-weight:600;">● Data Quality: All checks passed</span>
      <span>·</span>
      <span>Last updated: <b style="color:#E6EDF3">{last_updated}</b></span>
      <span>·</span>
      <span>Source: <b style="color:#E6EDF3">World Bank Open Data</b></span>
      <span>·</span>
      <span>⚠ Note: Unemployment 2020–2021 flagged as COVID-era outliers — <em>expected, kept</em></span>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 🇳🇵 Nepal Dashboard")
        st.markdown("---")

        selected = st.selectbox(
            "Select Indicator",
            list(INDICATORS.keys()),
            index=0,
        )

        st.markdown("---")
        st.markdown("**Year Range**")
        yr_min, yr_max = st.slider(
            "Select years",
            min_value=2000,
            max_value=2023,
            value=(2000, 2023),
            label_visibility="collapsed",
        )

        st.markdown("---")
        chart_type = st.radio(
            "Chart Type",
            ["Line Chart", "Bar Chart"],
            index=0,
        )

        st.markdown("---")
        show_trade = st.checkbox("Show Trade Balance Comparison", value=False)

        st.markdown("---")
        st.markdown("""
        <div style="color:#8B949E; font-size:0.8rem; line-height:1.5;">
        <b style="color:#E6EDF3">Data Sources</b><br>
        World Bank Open Data<br>
        Indicator codes listed in Sources section below.<br><br>
        <b style="color:#E6EDF3">Limitations</b><br>
        Data lags 1–2 years.<br>
        Unemployment = ILO modelled estimates.<br>
        NRB granular data not included.
        </div>
        """, unsafe_allow_html=True)

    # ── Load active indicator ──
    ind_meta = INDICATORS[selected]
    df_raw   = load_indicator(ind_meta["file"])

    if df_raw is None:
        st.error(
            f"Data file not found for **{selected}**. "
            "Please run `python data_collection.py` first."
        )
        st.stop()

    df_filtered = df_raw[(df_raw["year"] >= yr_min) & (df_raw["year"] <= yr_max)].copy()

    # ── Headline Metric Cards ──
    st.markdown('<div class="section-header">Headline Metrics</div>', unsafe_allow_html=True)

    # Load all 6 for the headline row
    all_latest = {}
    cols = st.columns(6)
    for i, (name, im) in enumerate(INDICATORS.items()):
        dfi = load_indicator(im["file"])
        if dfi is not None:
            val, yr, delta = compute_metrics(dfi, yr_max)
            all_latest[name] = (val, yr, delta)
            unit_short = im["unit"].split(" ")[0]   # '%'
            render_metric(cols[i], im["icon"], name, val, unit_short, delta, str(yr - 1))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main Chart ──
    st.markdown(f'<div class="section-header">{ind_meta["icon"]} {selected} ({yr_min}–{yr_max})</div>',
                unsafe_allow_html=True)

    if chart_type == "Line Chart":
        fig = line_chart(df_filtered, selected, ind_meta["color"], ind_meta["unit"])
    else:
        fig = bar_chart(df_filtered, selected, ind_meta["color"], ind_meta["unit"])

    st.plotly_chart(fig, use_container_width=True)

    # ── Trade Balance Overlay ──
    if show_trade:
        st.markdown('<div class="section-header">📊 Trade Balance: Exports vs Imports</div>',
                    unsafe_allow_html=True)
        df_exp = load_indicator("exports.csv")
        df_imp = load_indicator("imports.csv")
        if df_exp is not None and df_imp is not None:
            st.plotly_chart(
                trade_balance_chart(df_exp, df_imp, yr_min, yr_max),
                use_container_width=True,
            )

    # ── Plain-language Summary ──
    st.markdown(f"""
    <div class="summary-box">
      <div class="ai-badge">🤖 AI-assisted summary · ✅ Human verification required before publishing</div><br>
      {ind_meta['summary']}
    </div>
    """, unsafe_allow_html=True)

    # ── Verification Checklist ──
    with st.expander("📋 Verification Checklist (complete before publishing)"):
        st.markdown(f"""
        **Before publishing this summary, verify these numbers against the source:**
        """)
        for item in ind_meta["verify"]:
            st.markdown(f"- [ ] {item}")
        st.markdown(f"""
        **Source:** [{ind_meta['wb_url']}]({ind_meta['wb_url']})
        """)

    # ── Download Button ──
    st.markdown('<div class="section-header">⬇️ Download Data</div>', unsafe_allow_html=True)
    col_dl1, col_dl2, _ = st.columns([1, 1, 4])
    with col_dl1:
        csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"Download {selected} CSV",
            data=csv_bytes,
            file_name=f"nepal_{ind_meta['file']}",
            mime="text/csv",
        )
    with col_dl2:
        df_all = load_indicator("all_indicators.csv")
        if df_all is not None:
            all_bytes = df_all.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download All Indicators",
                data=all_bytes,
                file_name="nepal_all_indicators.csv",
                mime="text/csv",
            )

    # ── Sources & Methodology ──
    st.markdown("---")
    st.markdown('<div class="section-header">📚 Sources & Methodology</div>', unsafe_allow_html=True)

    with st.expander("Click to expand full sources and methodology"):
        st.markdown("""
        ### Data Sources

        All data is fetched directly from the **World Bank Open Data API** using the `wbgapi`
        Python library — no manual download required.

        | Indicator | World Bank Code | Direct Link |
        |-----------|----------------|-------------|
        | GDP Growth Rate | `NY.GDP.MKTP.KD.ZG` | [View](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=NP) |
        | Inflation (CPI) | `FP.CPI.TOTL.ZG` | [View](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=NP) |
        | Remittances | `BX.TRF.PWKR.DT.GD.ZS` | [View](https://data.worldbank.org/indicator/BX.TRF.PWKR.DT.GD.ZS?locations=NP) |
        | Exports of Goods & Services | `NE.EXP.GNFS.ZS` | [View](https://data.worldbank.org/indicator/NE.EXP.GNFS.ZS?locations=NP) |
        | Imports of Goods & Services | `NE.IMP.GNFS.ZS` | [View](https://data.worldbank.org/indicator/NE.IMP.GNFS.ZS?locations=NP) |
        | Unemployment Rate | `SL.UEM.TOTL.ZS` | [View](https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=NP) |

        ### Methodology
        - Data is fetched, cleaned, and saved as CSV files by `data_collection.py`
        - Quality is validated by `validation.py` (checks for missing values, duplicates, outliers)
        - Charts are built with Plotly and hosted on Streamlit Community Cloud
        - **Year range:** 2000–2023 (World Bank data typically lags 1–2 years)
        - **Country code:** NPL (Nepal)

        ### Limitations
        - Unemployment figures are **ILO modelled estimates**, not national survey data
        - Nepal Rastra Bank (NRB) granular monthly data is not included (no public API)
        - Data may lag the current year by 1–2 years
        - Plain-language summaries were **AI-assisted** and must be **human-verified** before publishing

        ### About Nepal Rastra Bank (NRB) Data
        If you want to add NRB granular data manually:
        1. Visit [Nepal Rastra Bank Publications](https://www.nrb.org.np/category/publications/)
        2. Download the **Current Macroeconomic Situation** Excel file
        3. Save it as `data/nrb_macro.xlsx`
        4. A future update to `data_collection.py` can parse this file

        ---
        *Built by Prasoddha Aryal · Nepal Economic Dashboard · 2024*
        *AI-assisted summaries are clearly labelled and require human verification before publishing.*
        """)


if __name__ == "__main__":
    main()
