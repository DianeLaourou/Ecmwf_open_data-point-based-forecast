"""
=============================================================================
dashboard.py — Dashboard Streamlit de Prévision Marine
Point Sème (6.22°N, 2.63°E) — Golfe de Guinée, Bénin

METEO-BENIN / DPROM / SPAM
Auteur : LAOUROU MAKONDJOU DIANE
=============================================================================
Usage :
    streamlit run dashboard.py
    streamlit run dashboard.py -- --swh ecmwf
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
import base64
import argparse
import sys
import os
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prévision Marine — Sème | METEO-BENIN",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS PERSONNALISÉ
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Palette océan profond ───────────────────────────── */
:root {
    --ocean-dark:   #0a1628;
    --ocean-mid:    #0d2240;
    --ocean-blue:   #0e3a6e;
    --ocean-teal:   #0b7285;
    --ocean-cyan:   #15aabf;
    --gold:         #f59f00;
    --alert-red:    #e03131;
    --alert-yellow: #f59f00;
    --alert-green:  #2f9e44;
    --text-light:   #e9ecef;
    --text-muted:   #adb5bd;
    --card-bg:      rgba(13, 34, 64, 0.85);
    --border:       rgba(21, 170, 191, 0.3);
}

/* ── Fond global ─────────────────────────────────────── */
.stApp {
    background: linear-gradient(160deg, #0a1628 0%, #0d2240 50%, #051020 100%);
}

/* ── Header principal ────────────────────────────────── */
.marine-header {
    background: linear-gradient(135deg, rgba(14,58,110,0.9) 0%, rgba(11,114,133,0.7) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.marine-header h1 {
    color: var(--text-light);
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.5px;
}
.marine-header .subtitle {
    color: var(--ocean-cyan);
    font-size: 0.85rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 600;
}

/* ── KPI Cards ────────────────────────────────────────── */
.kpi-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(21,170,191,0.2);
}
.kpi-card .kpi-label {
    font-size: 0.72rem;
    color: var(--ocean-cyan);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.kpi-card .kpi-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--text-light);
    line-height: 1.1;
}
.kpi-card .kpi-unit {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}

/* ── Warning Box ─────────────────────────────────────── */
.warning-box {
    border-radius: 10px;
    padding: 1rem 1.4rem;
    margin: 1rem 0;
    border-left: 5px solid;
    font-size: 0.9rem;
    font-weight: 500;
}
.warning-none {
    background: rgba(47, 158, 68, 0.12);
    border-color: var(--alert-green);
    color: #a9e34b;
}
.warning-yellow {
    background: rgba(245, 159, 0, 0.12);
    border-color: var(--alert-yellow);
    color: #ffd43b;
}
.warning-red {
    background: rgba(224, 49, 49, 0.14);
    border-color: var(--alert-red);
    color: #ff8787;
}

/* ── Section headers ─────────────────────────────────── */
.section-title {
    color: var(--ocean-cyan);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
}

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(10, 22, 40, 0.97) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stMarkdown h2 {
    color: var(--ocean-cyan);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

/* ── Metric overrides ────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 0.8rem !important;
}
[data-testid="stMetricLabel"] { color: var(--ocean-cyan) !important; font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { color: var(--text-light) !important; }

/* ── Plotly charts background ────────────────────────── */
.js-plotly-plot .plotly .modebar {
    background: rgba(13, 34, 64, 0.9) !important;
}

/* ── Tab styling ─────────────────────────────────────── */
[data-testid="stTabs"] button {
    color: var(--text-muted) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--ocean-cyan) !important;
    border-bottom-color: var(--ocean-cyan) !important;
}

/* ── Download buttons ────────────────────────────────── */
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--ocean-teal), var(--ocean-blue)) !important;
    color: white !important;
    border: 1px solid var(--ocean-cyan) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(135deg, var(--ocean-cyan), var(--ocean-teal)) !important;
    box-shadow: 0 4px 16px rgba(21,170,191,0.4) !important;
}

/* ── Selectbox, slider ───────────────────────────────── */
.stMultiSelect span[data-baseweb="tag"] {
    background-color: var(--ocean-teal) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — Configuration des variables
# ─────────────────────────────────────────────────────────────────────────────

ALERT_SWH_WARNING = 1.6   # m — seuil prudence
ALERT_SWH_DANGER  = 2.0   # m — seuil danger
ALERT_WIND_WARNING = 15   # kt — seuil vent prudence
ALERT_WIND_DANGER  = 20   # kt — seuil vent danger

# Métadonnées complètes de chaque variable
VAR_META = {
    "swh_m": {
        "label": "Hauteur significative des vagues (SWH)",
        "short": "SWH",
        "unit": "m",
        "color": "#15aabf",
        "group": "🌊 Vagues",
        "icon": "🌊",
        "thresholds": [
            {"value": ALERT_SWH_WARNING, "color": "rgba(245,159,0,0.3)",  "dash": "dash",  "name": "Prudence 1.6m"},
            {"value": ALERT_SWH_DANGER,  "color": "rgba(224,49,49,0.5)",  "dash": "dashdot","name": "Danger 2.0m"},
        ],
    },
    "sw1_ht_m": {
        "label": "Hauteur Swell 1",
        "short": "Swell 1",
        "unit": "m",
        "color": "#339af0",
        "group": "🌊 Vagues",
        "icon": "🌊",
        "thresholds": [],
    },
    "sw2_ht_m": {
        "label": "Hauteur Swell 2",
        "short": "Swell 2",
        "unit": "m",
        "color": "#74c0fc",
        "group": "🌊 Vagues",
        "icon": "🌊",
        "thresholds": [],
    },
    "sw1_period_s": {
        "label": "Période Swell 1",
        "short": "Période Sw1",
        "unit": "s",
        "color": "#a5d8ff",
        "group": "🌊 Vagues",
        "icon": "⏱️",
        "thresholds": [],
    },
    "sw2_period_s": {
        "label": "Période Swell 2",
        "short": "Période Sw2",
        "unit": "s",
        "color": "#d0ebff",
        "group": "🌊 Vagues",
        "icon": "⏱️",
        "thresholds": [],
    },
    "wind10_spd_kt": {
        "label": "Vitesse vent 10m",
        "short": "Vent 10m",
        "unit": "kt",
        "color": "#69db7c",
        "group": "💨 Vent",
        "icon": "💨",
        "thresholds": [
            {"value": ALERT_WIND_WARNING, "color": "rgba(245,159,0,0.3)", "dash": "dash",   "name": "15 kt"},
            {"value": ALERT_WIND_DANGER,  "color": "rgba(224,49,49,0.5)", "dash": "dashdot","name": "20 kt"},
        ],
    },
    "wind10_gust_kt": {
        "label": "Rafales 10m",
        "short": "Rafales",
        "unit": "kt",
        "color": "#b2f2bb",
        "group": "💨 Vent",
        "icon": "💨",
        "thresholds": [],
    },
    "wind100_spd_kt": {
        "label": "Vitesse vent 100m",
        "short": "Vent 100m",
        "unit": "kt",
        "color": "#40c057",
        "group": "💨 Vent",
        "icon": "💨",
        "thresholds": [],
    },
    "wind10_dir": {
        "label": "Direction vent 10m",
        "short": "Dir Vent 10m",
        "unit": "°",
        "color": "#a9e34b",
        "group": "💨 Vent",
        "icon": "🧭",
        "thresholds": [],
    },
    "mslp_hpa": {
        "label": "Pression mer (MSLP)",
        "short": "MSLP",
        "unit": "hPa",
        "color": "#ffa94d",
        "group": "🔴 Pression / Temp",
        "icon": "🔴",
        "thresholds": [
            {"value": 1010, "color": "rgba(21,170,191,0.2)", "dash": "dot", "name": "1010 hPa"},
        ],
    },
    "t2m_c": {
        "label": "Température 2m",
        "short": "T 2m",
        "unit": "°C",
        "color": "#ff6b6b",
        "group": "🔴 Pression / Temp",
        "icon": "🌡️",
        "thresholds": [],
    },
    "sst_c": {
        "label": "Température de surface mer (SST)",
        "short": "SST",
        "unit": "°C",
        "color": "#f06595",
        "group": "🔴 Pression / Temp",
        "icon": "🌡️",
        "thresholds": [],
    },
    "vis_km": {
        "label": "Visibilité",
        "short": "Visibilité",
        "unit": "km",
        "color": "#e599f7",
        "group": "🌫️ Autres",
        "icon": "👁️",
        "thresholds": [],
    },
    "rain_pct": {
        "label": "Probabilité de précipitation",
        "short": "Précip. (%)",
        "unit": "%",
        "color": "#4dabf7",
        "group": "🌫️ Autres",
        "icon": "🌧️",
        "thresholds": [
            {"value": 50, "color": "rgba(21,170,191,0.2)", "dash": "dot", "name": "50%"},
        ],
    },
    "cur_spd_kt": {
        "label": "Vitesse courant marin",
        "short": "Courant",
        "unit": "kt",
        "color": "#cc5de8",
        "group": "🌫️ Autres",
        "icon": "🔄",
        "thresholds": [],
    },
    "cur_dir": {
        "label": "Direction courant marin",
        "short": "Dir Courant",
        "unit": "°",
        "color": "#da77f2",
        "group": "🌫️ Autres",
        "icon": "🧭",
        "thresholds": [],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DONNÉES DÉMO (générées si pipeline non disponible)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def generate_demo_data() -> pd.DataFrame:
    """Génère des données de démo réalistes pour le Golfe de Guinée."""
    np.random.seed(42)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    # 5 jours × 6h = 20 pas de temps (+ 10 passés)
    times = [now - timedelta(hours=6*i) for i in range(9, -21, -1)]
    n = len(times)

    t = np.linspace(0, 2*np.pi, n)

    # SWH avec une houle réaliste Golfe de Guinée
    swh_base = 1.2 + 0.6*np.sin(t) + 0.3*np.sin(2.3*t) + np.random.normal(0, 0.08, n)
    swh_base = np.clip(swh_base, 0.3, 3.5)

    df = pd.DataFrame({
        "valid_local":    times,
        "swh_m":          swh_base,
        "sw1_ht_m":       np.clip(swh_base * 0.65 + np.random.normal(0, 0.05, n), 0, 2.5),
        "sw1_period_s":   11 + 3*np.sin(t*0.7) + np.random.normal(0, 0.3, n),
        "sw1_dir":        200 + 15*np.sin(t*0.4) + np.random.normal(0, 3, n),
        "sw2_ht_m":       np.clip(swh_base * 0.35 + np.random.normal(0, 0.04, n), 0, 1.5),
        "sw2_period_s":   7 + 2*np.sin(t*1.1) + np.random.normal(0, 0.3, n),
        "sw2_dir":        240 + 10*np.sin(t*0.6) + np.random.normal(0, 3, n),
        "wind10_spd_kt":  np.clip(8 + 6*np.sin(t*1.2) + np.random.normal(0, 0.5, n), 0, 30),
        "wind10_gust_kt": np.clip(12 + 8*np.sin(t*1.2) + np.random.normal(0, 0.7, n), 0, 38),
        "wind10_dir":     190 + 20*np.sin(t*0.5) + np.random.normal(0, 5, n),
        "wind100_spd_kt": np.clip(12 + 7*np.sin(t*1.1) + np.random.normal(0, 0.6, n), 0, 35),
        "wind100_dir":    195 + 18*np.sin(t*0.5) + np.random.normal(0, 4, n),
        "mslp_hpa":       1013 - 2*np.sin(t*0.8) + np.random.normal(0, 0.3, n),
        "t2m_c":          29 + 2*np.sin(t*0.3) + np.random.normal(0, 0.2, n),
        "sst_c":          28 + 1.5*np.sin(t*0.25) + np.random.normal(0, 0.15, n),
        "vis_km":         np.clip(15 - 3*np.sin(t*0.9) + np.random.normal(0, 0.5, n), 3, 20),
        "rain_pct":       np.clip(20 + 30*np.sin(t*0.8)**2 + np.random.normal(0, 3, n), 0, 100),
        "cur_spd_kt":     np.clip(0.5 + 0.4*np.sin(t*1.3) + np.random.normal(0, 0.05, n), 0, 2),
        "cur_dir":        150 + 30*np.sin(t*0.7) + np.random.normal(0, 5, n),
    })

    df["valid_local"] = pd.to_datetime(df["valid_local"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# CHARGEMENT DES DONNÉES RÉELLES (pipeline)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_pipeline_data(run_date: str, run_hour: int, swh_source: str) -> tuple[pd.DataFrame | None, str | None]:
    """Lance le pipeline et retourne (df, error_msg)."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from datetime import datetime as dt
        import config
        import extractor

        run_dt = dt.strptime(f"{run_date} {run_hour:02d}:00", "%Y-%m-%d %H:%M")
        if swh_source:
            config.SWH_SOURCE = swh_source

        df_ecmwf = extractor.extract_ecmwf(run_dt)
        df_cop   = extractor.extract_copernicus(run_dt)
        df       = extractor.merge_sources(df_ecmwf, df_cop)
        df["valid_local"] = pd.to_datetime(df["valid_local"])
        return df, None
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def deg_to_compass(deg: float) -> str:
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSO","SO","OSO","O","ONO","NO","NNO"]
    ix = round(deg / 22.5) % 16
    return dirs[ix]

def get_alert_level(df: pd.DataFrame) -> tuple[str, str, str]:
    """Retourne (niveau, css_class, texte_warning)."""
    swh_max  = df["swh_m"].max()  if "swh_m"          in df.columns else 0
    wind_max = df["wind10_spd_kt"].max() if "wind10_spd_kt" in df.columns else 0

    if swh_max >= ALERT_SWH_DANGER or wind_max >= ALERT_WIND_DANGER:
        return "🔴 DANGER", "warning-red", (
            f"Warning: Conditions dangereuses attendues. "
            f"SWH max {swh_max:.1f} m — Vent max {wind_max:.0f} kt."
        )
    elif swh_max >= ALERT_SWH_WARNING or wind_max >= ALERT_WIND_WARNING:
        return "🟡 PRUDENCE", "warning-yellow", (
            f"Warning: Conditions modérées. Prudence recommandée. "
            f"SWH max {swh_max:.1f} m — Vent max {wind_max:.0f} kt."
        )
    else:
        return "🟢 NORMAL", "warning-none", (
            f"Warning: None. Conditions clémentes. "
            f"SWH max {swh_max:.1f} m — Vent max {wind_max:.0f} kt."
        )

def plotly_theme() -> dict:
    """Thème plotly commun dark-ocean."""
    return dict(
        paper_bgcolor="rgba(10,22,40,0)",
        plot_bgcolor="rgba(13,34,64,0.5)",
        font=dict(color="#e9ecef", family="monospace, sans-serif", size=12),
        xaxis=dict(
            gridcolor="rgba(21,170,191,0.12)",
            linecolor="rgba(21,170,191,0.3)",
            tickcolor="rgba(21,170,191,0.3)",
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="rgba(21,170,191,0.12)",
            linecolor="rgba(21,170,191,0.3)",
            tickcolor="rgba(21,170,191,0.3)",
            showgrid=True,
        ),
        legend=dict(
            bgcolor="rgba(10,22,40,0.7)",
            bordercolor="rgba(21,170,191,0.3)",
            borderwidth=1,
        ),
        margin=dict(l=60, r=30, t=40, b=50),
        hovermode="x unified",
    )

def add_thresholds(fig, var_key: str, df: pd.DataFrame, row=1, col=1):
    """Ajoute les lignes de seuils d'alerte sur un subplot."""
    meta = VAR_META.get(var_key, {})
    for th in meta.get("thresholds", []):
        fig.add_hline(
            y=th["value"],
            line_dash=th["dash"],
            line_color=th["color"],
            annotation_text=th["name"],
            annotation_font_color=th["color"],
            annotation_bgcolor="rgba(10,22,40,0.7)",
            row=row, col=col,
        )

def fig_to_bytes(fig) -> bytes:
    """Exporte une figure plotly en PNG (bytes)."""
    try:
        return fig.to_image(format="png", scale=2, width=1400, height=600)
    except Exception:
        return fig.to_html().encode()

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Prévisions", index=False)
    return buf.getvalue()

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# ─────────────────────────────────────────────────────────────────────────────
# GRAPHIQUES
# ─────────────────────────────────────────────────────────────────────────────

def make_timeseries(df: pd.DataFrame, selected_vars: list[str], title: str = "") -> go.Figure:
    """Crée un graphique multi-variables en séries temporelles (subplots)."""
    n = len(selected_vars)
    if n == 0:
        return go.Figure()

    # Un subplot par variable
    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=[VAR_META.get(v, {}).get("label", v) for v in selected_vars],
    )

    for i, var in enumerate(selected_vars, 1):
        if var not in df.columns:
            continue
        meta = VAR_META.get(var, {})
        color = meta.get("color", "#15aabf")
        unit  = meta.get("unit", "")

        # Remplissage sous la courbe pour première var
        fill = "tozeroy" if i == 1 else "none"
        fillcolor = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)"

        fig.add_trace(
            go.Scatter(
                x=df["valid_local"],
                y=df[var],
                mode="lines+markers",
                name=meta.get("short", var),
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
                fill=fill,
                fillcolor=fillcolor,
                hovertemplate=f"<b>{meta.get('short', var)}</b>: %{{y:.2f}} {unit}<extra></extra>",
            ),
            row=i, col=1,
        )
        # Seuils
        for th in meta.get("thresholds", []):
            fig.add_hline(
                y=th["value"],
                line_dash=th["dash"],
                line_color=th["color"],
                line_width=1.5,
                annotation_text=th["name"],
                annotation_font=dict(color=th["color"], size=10),
                annotation_bgcolor="rgba(10,22,40,0.6)",
                row=i, col=1,
            )

        fig.update_yaxes(title_text=unit, row=i, col=1,
                         title_font=dict(size=10, color=color))

    th = plotly_theme()
    # Répliquer les axes sur chaque subplot
    for i in range(1, n+1):
        ax_y = "" if i == 1 else str(i)
        ax_x = "" if i == 1 else str(i)
        fig.update_layout(**{
            f"yaxis{ax_y}": dict(
                gridcolor="rgba(21,170,191,0.12)",
                linecolor="rgba(21,170,191,0.3)",
                showgrid=True,
            )
        })

    fig.update_layout(
        paper_bgcolor=th["paper_bgcolor"],
        plot_bgcolor=th["plot_bgcolor"],
        font=th["font"],
        legend=th["legend"],
        margin=th["margin"],
        hovermode="x unified",
        height=max(220 * n, 320),
        title=dict(text=title, font=dict(color="#15aabf", size=14)) if title else None,
        xaxis=th["xaxis"],
    )
    # Partager la config x sur tous
    for i in range(1, n+1):
        ax = f"xaxis{'' if i==1 else i}"
        fig.update_layout(**{ax: th["xaxis"]})

    return fig


def make_wind_rose(df_filtered: pd.DataFrame) -> go.Figure:
    """Rose des vents (Barpolar)."""
    if "wind10_dir" not in df_filtered.columns or "wind10_spd_kt" not in df_filtered.columns:
        return go.Figure()

    bins   = np.arange(0, 361, 22.5)
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSO","SO","OSO","O","ONO","NO","NNO"]
    dirs   = df_filtered["wind10_dir"].dropna().values
    speeds = df_filtered["wind10_spd_kt"].dropna().values
    min_len = min(len(dirs), len(speeds))
    dirs = dirs[:min_len]; speeds = speeds[:min_len]

    speed_bins  = [0, 5, 10, 15, 20, 100]
    speed_labels = ["0–5 kt", "5–10 kt", "10–15 kt", "15–20 kt", ">20 kt"]
    colors       = ["#74c0fc", "#15aabf", "#69db7c", "#ffa94d", "#ff6b6b"]

    fig = go.Figure()
    for j, (smin, smax) in enumerate(zip(speed_bins[:-1], speed_bins[1:])):
        mask = (speeds >= smin) & (speeds < smax)
        d    = dirs[mask]
        counts = []
        for k in range(16):
            lo = bins[k]; hi = bins[k+1] if k < 15 else 360
            counts.append(np.sum((d >= lo) & (d < hi)))
        fig.add_trace(go.Barpolar(
            r=counts, theta=labels,
            name=speed_labels[j],
            marker_color=colors[j],
            marker_line_color="rgba(10,22,40,0.5)",
            marker_line_width=0.5,
            opacity=0.85,
        ))

    th = plotly_theme()
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(13,34,64,0.6)",
            radialaxis=dict(showticklabels=True, ticks="", gridcolor="rgba(21,170,191,0.2)",
                            linecolor="rgba(21,170,191,0.2)", tickfont=dict(color="#adb5bd", size=9)),
            angularaxis=dict(direction="clockwise", gridcolor="rgba(21,170,191,0.15)",
                             tickfont=dict(color="#e9ecef", size=11)),
        ),
        paper_bgcolor=th["paper_bgcolor"],
        font=th["font"],
        legend=th["legend"],
        margin=dict(l=40, r=40, t=50, b=40),
        height=380,
        title=dict(text="Rose des Vents 10m", font=dict(color="#69db7c", size=13)),
    )
    return fig


def make_swell_compass(df_filtered: pd.DataFrame) -> go.Figure:
    """Graphique polaire direction/hauteur swell."""
    fig = go.Figure()
    for sw, col, label in [
        ("sw1_dir", "#339af0", "Swell 1"),
        ("sw2_dir", "#74c0fc", "Swell 2"),
    ]:
        ht_col = sw.replace("_dir", "_ht_m")
        if sw not in df_filtered.columns or ht_col not in df_filtered.columns:
            continue
        fig.add_trace(go.Scatterpolar(
            r=df_filtered[ht_col].fillna(0),
            theta=df_filtered[sw].fillna(0),
            mode="markers",
            name=label,
            marker=dict(color=col, size=8, opacity=0.8,
                        line=dict(color="white", width=0.5)),
            hovertemplate="Dir: %{theta:.0f}°<br>Ht: %{r:.2f} m<extra></extra>",
        ))

    th = plotly_theme()
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(13,34,64,0.6)",
            radialaxis=dict(showticklabels=True, ticks="", gridcolor="rgba(21,170,191,0.2)",
                            linecolor="rgba(21,170,191,0.2)", tickfont=dict(color="#adb5bd", size=9)),
            angularaxis=dict(direction="clockwise", rotation=90,
                             gridcolor="rgba(21,170,191,0.15)",
                             tickfont=dict(color="#e9ecef", size=10)),
        ),
        paper_bgcolor=th["paper_bgcolor"],
        font=th["font"],
        legend=th["legend"],
        margin=dict(l=40, r=40, t=50, b=40),
        height=380,
        title=dict(text="Direction & Hauteur Swell", font=dict(color="#339af0", size=13)),
    )
    return fig


def make_correlation_heatmap(df_filtered: pd.DataFrame, num_vars: list[str]) -> go.Figure:
    """Matrice de corrélation des variables numériques."""
    available = [v for v in num_vars if v in df_filtered.columns]
    if len(available) < 2:
        return go.Figure()

    corr = df_filtered[available].corr().round(2)
    labels = [VAR_META.get(v, {}).get("short", v) for v in available]

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=labels, y=labels,
        colorscale=[[0,"#e03131"],[0.5,"rgba(13,34,64,0.5)"],[1,"#15aabf"]],
        zmin=-1, zmax=1,
        text=corr.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=10),
        hovertemplate="%{x} vs %{y}: %{z}<extra></extra>",
        colorbar=dict(tickfont=dict(color="#e9ecef")),
    ))

    th = plotly_theme()
    fig.update_layout(
        paper_bgcolor=th["paper_bgcolor"],
        plot_bgcolor=th["plot_bgcolor"],
        font=th["font"],
        margin=dict(l=80, r=30, t=40, b=80),
        height=420,
        title=dict(text="Matrice de Corrélation", font=dict(color="#15aabf", size=13)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding:0.5rem 0 1rem 0;'>
            <div style='font-size:2.5rem;'>🌊</div>
            <div style='color:#15aabf; font-size:0.7rem; letter-spacing:2px;
                        text-transform:uppercase; font-weight:700;'>METEO-BENIN</div>
            <div style='color:#adb5bd; font-size:0.65rem; margin-top:0.2rem;'>DPROM / SPAM</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("## ⚙️ Paramètres")

        # ── Source de données ─────────────────────────────────
        data_source = st.radio(
            "Source de données",
            ["🎲 Données démo", "🔗 Pipeline en direct"],
            index=0,
            help="'Démo' = données synthétiques réalistes. 'Pipeline' = lance le vrai pipeline ECMWF/Copernicus."
        )

        run_date, run_hour, swh_source = None, 0, "ecmwf"
        if data_source == "🔗 Pipeline en direct":
            st.markdown("### 📅 Date du run ECMWF")
            run_date = st.date_input("Date", value=datetime.utcnow().date())
            run_hour = st.selectbox("Heure UTC", [0, 6, 12, 18], index=2)
            swh_source = st.selectbox("Source SWH", ["ecmwf", "copernicus"], index=0)

        st.divider()

        # ── Sélection de variables ────────────────────────────
        st.markdown("## 📊 Variables à visualiser")

        groups = {}
        for k, m in VAR_META.items():
            g = m["group"]
            groups.setdefault(g, []).append(k)

        selected_vars = []
        for group_name, vars_in_group in groups.items():
            with st.expander(group_name, expanded=group_name.startswith("🌊")):
                for v in vars_in_group:
                    meta = VAR_META[v]
                    checked = v in ["swh_m", "wind10_spd_kt", "mslp_hpa"]
                    if st.checkbox(
                        f"{meta['icon']} {meta['short']} ({meta['unit']})",
                        value=checked,
                        key=f"chk_{v}",
                    ):
                        selected_vars.append(v)

        st.divider()

        # ── Filtre temporel ───────────────────────────────────
        st.markdown("## 🗓️ Période")

        # Générer les données démo pour connaître les bornes disponibles
        _df_bounds = generate_demo_data()
        _dt_min = _df_bounds["valid_local"].min().to_pydatetime()
        _dt_max = _df_bounds["valid_local"].max().to_pydatetime()

        # Toutes les heures disponibles dans les données
        _all_times = sorted(_df_bounds["valid_local"].dt.to_pydatetime().tolist())
        _all_dates = sorted(set(t.date() for t in _all_times))

        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input(
                "📅 Du",
                value=_dt_min.date(),
                min_value=_dt_min.date(),
                max_value=_dt_max.date(),
                key="start_date",
            )
            _hours_start = sorted(set(
                t.hour for t in _all_times if t.date() == start_date
            )) or list(range(0, 24, 6))
            start_hour = st.selectbox(
                "🕐 Heure début",
                options=_hours_start,
                format_func=lambda h: f"{h:02d}:00",
                index=0,
                key="start_hour",
            )
        with col_b:
            end_date = st.date_input(
                "📅 Au",
                value=_dt_max.date(),
                min_value=_dt_min.date(),
                max_value=_dt_max.date(),
                key="end_date",
            )
            _hours_end = sorted(set(
                t.hour for t in _all_times if t.date() == end_date
            )) or list(range(0, 24, 6))
            end_hour = st.selectbox(
                "🕐 Heure fin",
                options=_hours_end,
                format_func=lambda h: f"{h:02d}:00",
                index=len(_hours_end) - 1,
                key="end_hour",
            )

        from datetime import datetime as _dt
        time_start = _dt.combine(start_date, _dt.min.time()).replace(hour=start_hour)
        time_end   = _dt.combine(end_date,   _dt.min.time()).replace(hour=end_hour)

        # Sécurité : inverser si start > end
        if time_start > time_end:
            time_start, time_end = time_end, time_start

        st.divider()

        # ── Options graphique ─────────────────────────────────
        st.markdown("## 🎨 Options d'affichage")
        show_markers = st.checkbox("Marqueurs sur courbes", value=True)
        show_thresholds = st.checkbox("Seuils d'alerte", value=True)
        chart_type = st.selectbox("Type principal", ["Séries temporelles", "Aire empilée"], index=0)

        st.divider()
        st.markdown("""
        <div style='color:#adb5bd; font-size:0.65rem; text-align:center; line-height:1.6;'>
            Sème — 6.22°N, 2.63°E<br>
            Golfe de Guinée, Bénin<br>
            Sources : ECMWF · Copernicus<br>
            © 2026 LAOUROU M. DIANE
        </div>
        """, unsafe_allow_html=True)

    return {
        "data_source": data_source,
        "run_date": str(run_date) if run_date else None,
        "run_hour": run_hour,
        "swh_source": swh_source,
        "selected_vars": selected_vars,
        "time_start": time_start,
        "time_end":   time_end,
        "show_markers": show_markers,
        "show_thresholds": show_thresholds,
        "chart_type": chart_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────

def render_kpi_row(df: pd.DataFrame):
    """Affiche les KPI principaux en 1 ligne."""
    cols = st.columns(6)
    kpis = [
        ("swh_m",          "SWH Max",        "m",    lambda s: f"{s.max():.2f}"),
        ("wind10_spd_kt",  "Vent Max",        "kt",   lambda s: f"{s.max():.1f}"),
        ("wind10_gust_kt", "Rafale Max",      "kt",   lambda s: f"{s.max():.1f}"),
        ("mslp_hpa",       "MSLP Min",        "hPa",  lambda s: f"{s.min():.1f}"),
        ("sst_c",          "SST Moy",         "°C",   lambda s: f"{s.mean():.1f}"),
        ("rain_pct",       "Précip Max",      "%",    lambda s: f"{s.max():.0f}"),
    ]
    for col, (var, label, unit, fmt) in zip(cols, kpis):
        with col:
            if var in df.columns:
                val = fmt(df[var].dropna())
            else:
                val = "—"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{val}</div>
                <div class="kpi-unit">{unit}</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ONGLETS PRINCIPAUX
# ─────────────────────────────────────────────────────────────────────────────

def render_main_tabs(df: pd.DataFrame, df_filtered: pd.DataFrame, params: dict):
    """Affiche les onglets du dashboard."""
    selected = params["selected_vars"]

    tab_ts, tab_vent, tab_swell, tab_corr, tab_data, tab_export = st.tabs([
        "📈 Séries temporelles",
        "💨 Vent & Rose",
        "🌊 Swell & Courants",
        "🔗 Corrélations",
        "📋 Données brutes",
        "💾 Exports",
    ])

    # ────────── Onglet 1 : Séries temporelles ────────────────
    with tab_ts:
        if not selected:
            st.info("👈 Sélectionnez au moins une variable dans la barre latérale.")
        else:
            fig = make_timeseries(df_filtered, selected,
                                  title=f"Prévisions — Sème ({df_filtered['valid_local'].min().strftime('%d/%m')} → {df_filtered['valid_local'].max().strftime('%d/%m %H:%M')})")
            st.plotly_chart(fig, use_container_width=True)

            # Bouton export PNG
            col_exp, _ = st.columns([1, 5])
            with col_exp:
                try:
                    img = fig_to_bytes(fig)
                    ext = "png" if isinstance(img, bytes) and img[:4] == b'\x89PNG' else "html"
                    st.download_button(
                        f"⬇️ Export PNG",
                        data=img,
                        file_name=f"seme_timeseries_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
                        mime=f"image/{ext}" if ext == "png" else "text/html",
                        key="dl_ts",
                    )
                except Exception:
                    pass

    # ────────── Onglet 2 : Vent & Rose ───────────────────────
    with tab_vent:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig_w = make_timeseries(
                df_filtered,
                [v for v in ["wind10_spd_kt","wind10_gust_kt","wind100_spd_kt"] if v in df_filtered.columns],
                title="Vitesses de vent"
            )
            st.plotly_chart(fig_w, use_container_width=True)
        with c2:
            fig_r = make_wind_rose(df_filtered)
            st.plotly_chart(fig_r, use_container_width=True)

        # Direction vent
        if "wind10_dir" in df_filtered.columns:
            st.markdown('<div class="section-title">Direction du vent 10m (°)</div>', unsafe_allow_html=True)
            fig_dir = make_timeseries(df_filtered, ["wind10_dir"], title="Direction vent 10m")
            st.plotly_chart(fig_dir, use_container_width=True)

    # ────────── Onglet 3 : Swell & Courants ──────────────────
    with tab_swell:
        c1, c2 = st.columns([1, 1])
        with c1:
            swell_vars = [v for v in ["swh_m","sw1_ht_m","sw2_ht_m"] if v in df_filtered.columns]
            fig_s = make_timeseries(df_filtered, swell_vars, title="Hauteurs de houle")
            st.plotly_chart(fig_s, use_container_width=True)

        with c2:
            fig_sc = make_swell_compass(df_filtered)
            st.plotly_chart(fig_sc, use_container_width=True)

        c3, c4 = st.columns([1, 1])
        with c3:
            period_vars = [v for v in ["sw1_period_s","sw2_period_s"] if v in df_filtered.columns]
            if period_vars:
                fig_p = make_timeseries(df_filtered, period_vars, title="Périodes de swell")
                st.plotly_chart(fig_p, use_container_width=True)
        with c4:
            cur_vars = [v for v in ["cur_spd_kt","cur_dir"] if v in df_filtered.columns]
            if cur_vars:
                fig_c = make_timeseries(df_filtered, cur_vars, title="Courants marins")
                st.plotly_chart(fig_c, use_container_width=True)

    # ────────── Onglet 4 : Corrélations ──────────────────────
    with tab_corr:
        numeric_vars = [k for k in VAR_META if k in df_filtered.columns and
                        df_filtered[k].dtype in [float, int, np.float64, np.int64]]
        if len(numeric_vars) >= 2:
            fig_hm = make_correlation_heatmap(df_filtered, numeric_vars)
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Pas assez de variables numériques pour calculer les corrélations.")

        # Scatter personnalisé
        st.markdown('<div class="section-title">Nuage de points personnalisé</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            var_x = st.selectbox("Axe X", options=numeric_vars,
                                 index=numeric_vars.index("wind10_spd_kt") if "wind10_spd_kt" in numeric_vars else 0,
                                 key="scatter_x")
        with c2:
            var_y = st.selectbox("Axe Y", options=numeric_vars,
                                 index=numeric_vars.index("swh_m") if "swh_m" in numeric_vars else 0,
                                 key="scatter_y")

        if var_x and var_y:
            mx = VAR_META.get(var_x, {}); my = VAR_META.get(var_y, {})
            fig_sc = go.Figure(go.Scatter(
                x=df_filtered[var_x], y=df_filtered[var_y],
                mode="markers",
                marker=dict(
                    color=df_filtered["valid_local"].astype(np.int64) // 10**9,
                    colorscale="Viridis",
                    size=7, opacity=0.8,
                    colorbar=dict(title="Temps", tickfont=dict(color="#e9ecef")),
                    showscale=True,
                ),
                hovertemplate=f"{mx.get('short',var_x)}: %{{x:.2f}} {mx.get('unit','')}<br>"
                              f"{my.get('short',var_y)}: %{{y:.2f}} {my.get('unit','')}<extra></extra>",
            ))
            th = plotly_theme()
            fig_sc.update_layout(
                **th,
                height=380,
                xaxis_title=f"{mx.get('short',var_x)} ({mx.get('unit','')})",
                yaxis_title=f"{my.get('short',var_y)} ({my.get('unit','')})",
                title=dict(text=f"{mx.get('short',var_x)} vs {my.get('short',var_y)}",
                           font=dict(color="#15aabf", size=13)),
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    # ────────── Onglet 5 : Données brutes ────────────────────
    with tab_data:
        st.markdown(f"**{len(df_filtered)} lignes** × **{len(df_filtered.columns)} colonnes**")

        # Formatage
        display_df = df_filtered.copy()
        display_df["valid_local"] = display_df["valid_local"].dt.strftime("%d/%m/%Y %H:%M")

        # Coloration SWH
        def color_swh(val):
            try:
                v = float(val)
                if v >= ALERT_SWH_DANGER:
                    return "background-color: rgba(224,49,49,0.25); color: #ff8787"
                elif v >= ALERT_SWH_WARNING:
                    return "background-color: rgba(245,159,0,0.2); color: #ffd43b"
            except Exception:
                pass
            return ""

        styled = display_df.style
        if "swh_m" in display_df.columns:
            styled = styled.map(color_swh, subset=["swh_m"])

        # Arrondi pour affichage
        numeric_cols = display_df.select_dtypes(include=[np.number]).columns
        styled = styled.format({c: "{:.2f}" for c in numeric_cols}, na_rep="—")

        st.dataframe(styled, use_container_width=True, height=450)

    # ────────── Onglet 6 : Exports ───────────────────────────
    with tab_export:
        st.markdown('<div class="section-title">Exporter les données filtrées</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)

        with c1:
            csv_bytes = df_to_csv_bytes(df_filtered)
            st.download_button(
                "⬇️ Export CSV (;)",
                data=csv_bytes,
                file_name=f"seme_previsions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with c2:
            xl_bytes = df_to_excel_bytes(df_filtered)
            st.download_button(
                "⬇️ Export Excel (.xlsx)",
                data=xl_bytes,
                file_name=f"seme_previsions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with c3:
            json_str = df_filtered.assign(
                valid_local=df_filtered["valid_local"].dt.strftime("%Y-%m-%dT%H:%M:%S")
            ).to_json(orient="records", indent=2, force_ascii=False)
            st.download_button(
                "⬇️ Export JSON",
                data=json_str.encode("utf-8"),
                file_name=f"seme_previsions_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown('<div class="section-title">Exporter les graphiques (PNG)</div>', unsafe_allow_html=True)
        if params["selected_vars"]:
            fig_export = make_timeseries(df_filtered, params["selected_vars"])
            try:
                img = fig_to_bytes(fig_export)
                ext = "png"
                st.download_button(
                    "⬇️ Graphique série temp. (PNG)",
                    data=img,
                    file_name=f"seme_graphique_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
                    mime=f"image/{ext}",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"Export PNG non disponible (kaleido manquant) : {e}")

        st.divider()
        st.markdown("### 📋 Bulletin de synthèse")
        level, css, warning_txt = get_alert_level(df_filtered)
        swh_m = df_filtered["swh_m"].max() if "swh_m" in df_filtered.columns else 0
        wind_m = df_filtered["wind10_spd_kt"].max() if "wind10_spd_kt" in df_filtered.columns else 0

        bulletin = f"""BULLETIN DE PRÉVISION MARINE — SÈME (6.22°N, 2.63°E)
METEO-BENIN / DPROM / SPAM
Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')} (UTC+1)
Période : {df_filtered['valid_local'].min().strftime('%d/%m/%Y %H:%M')} → {df_filtered['valid_local'].max().strftime('%d/%m/%Y %H:%M')}

═══════════════════════════════════════════════════════
NIVEAU D'ALERTE : {level}
{warning_txt}
═══════════════════════════════════════════════════════

STATISTIQUES CLÉS
─────────────────
SWH    max : {f'{swh_m:.2f} m' if "swh_m" in df_filtered.columns else 'N/A'}
Vent   max : {f'{wind_m:.1f} kt' if "wind10_spd_kt" in df_filtered.columns else 'N/A'}
Rafale max : {f'{df_filtered["wind10_gust_kt"].max():.1f} kt' if "wind10_gust_kt" in df_filtered.columns else 'N/A'}
MSLP   min : {f'{df_filtered["mslp_hpa"].min():.1f} hPa' if "mslp_hpa" in df_filtered.columns else 'N/A'}
SST  moy   : {f'{df_filtered["sst_c"].mean():.1f} °C' if "sst_c" in df_filtered.columns else 'N/A'}

═══════════════════════════════════════════════════════
Source : ECMWF Open Data + Copernicus Marine Service
Auteur : LAOUROU MAKONDJOU DIANE
"""
        st.text_area("Bulletin texte", value=bulletin, height=340)
        st.download_button(
            "⬇️ Télécharger le bulletin (.txt)",
            data=bulletin.encode("utf-8"),
            file_name=f"bulletin_seme_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    params = render_sidebar()

    # ── Chargement des données ────────────────────────────────
    if params["data_source"] == "🔗 Pipeline en direct":
        with st.spinner("⏳ Lancement du pipeline ECMWF/Copernicus..."):
            df, err = load_pipeline_data(
                params["run_date"], params["run_hour"], params["swh_source"]
            )
        if err:
            st.error(f"❌ Erreur pipeline : {err}")
            st.info("💡 Passage aux données de démonstration.")
            df = generate_demo_data()
            is_demo = True
        else:
            is_demo = False
    else:
        df = generate_demo_data()
        is_demo = True

    # ── Filtre temporel ───────────────────────────────────────
    now_local = datetime.now()
    df_filtered = df[
        (df["valid_local"] >= pd.Timestamp(params["time_start"])) &
        (df["valid_local"] <= pd.Timestamp(params["time_end"]))
    ].copy()

    if df_filtered.empty:
        # Fallback : toute la période si filtre trop restrictif
        df_filtered = df.copy()

    # ── Header ───────────────────────────────────────────────
    demo_badge = " · <span style='color:#ffa94d; font-size:0.7rem;'>🎲 DONNÉES DÉMO</span>" if is_demo else ""
    st.markdown(f"""
    <div class="marine-header">
        <div style="font-size:3rem;">🌊</div>
        <div>
            <div class="subtitle">METEO-BENIN · DPROM / SPAM</div>
            <h1>Prévision Marine — Sème{demo_badge}</h1>
            <div style="color:#adb5bd; font-size:0.78rem; margin-top:0.2rem;">
                📍 6.22°N, 2.63°E · Golfe de Guinée, Bénin &nbsp;|&nbsp;
                Source : ECMWF Open Data + Copernicus Marine &nbsp;|&nbsp;
                Mise à jour : {now_local.strftime('%d/%m/%Y %H:%M')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Warning Banner ────────────────────────────────────────
    level, css, warning_txt = get_alert_level(df_filtered)
    st.markdown(
        f'<div class="warning-box {css}"><b>{level}</b> — {warning_txt}</div>',
        unsafe_allow_html=True,
    )

    # ── KPI Row ───────────────────────────────────────────────
    render_kpi_row(df_filtered)
    st.markdown("---")

    # ── Onglets ───────────────────────────────────────────────
    render_main_tabs(df, df_filtered, params)

    # ── Pied de page ─────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; color:#4a6480; font-size:0.68rem; margin-top:2rem; padding:1rem 0;
                border-top:1px solid rgba(21,170,191,0.15);'>
        © 2026 · LAOUROU MAKONDJOU DIANE · Météorologiste & Data Scientist · METEO-BENIN / DPROM / SPAM<br>
        Données : ECMWF Open Data (CC BY 4.0) · Copernicus Marine Service
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
