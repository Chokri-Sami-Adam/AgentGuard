# app.py  (AgentGuard)
import math
import re
import sys
from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Permet d'importer config.py, engine/, etc. depuis la racine du projet
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.services import (
    get_default_model,
    get_model_name,
    get_recommendations,
    list_ollama_models,
    load_history_frames,
    load_test_cases,
    run_audit,
    save_audit,
    set_model,
    to_dashboard_data,
)

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="AgentGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette
C_OK = "#2dd4bf"
C_WARN = "#fbbf24"
C_BAD = "#fb7185"
C_PURPLE = "#8b5cf6"
C_LILAC = "#c4b5fd"
C_ORANGE = "#fb923c"
TEXT = "#c9c4f0"
GRID = "rgba(148,140,220,.16)"


# ---------------------------------------------------------
# Données réelles (audits enregistrés)
# ---------------------------------------------------------

HISTORY, CATEGORY_SCORES, SCENARIOS = load_history_frames()


# ---------------------------------------------------------
# Style personnalisé (thème violet sombre + effets 3D)
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --border: rgba(139, 120, 255, .20);
            --muted: #9d97c9;
            --ok: #2dd4bf;
            --bad: #fb7185;
        }

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .stApp {
            background:
                radial-gradient(ellipse at 8% 4%, rgba(124, 58, 237, .26), transparent 36%),
                radial-gradient(ellipse at 94% 10%, rgba(59, 130, 246, .14), transparent 30%),
                linear-gradient(135deg, #0a0820 0%, #0e0b2b 55%, #120d33 100%);
            color: #f1eeff;
        }

        [data-testid="stHeader"] { background: rgba(10, 8, 32, .55); }
        footer { visibility: hidden; }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
            max-width: 1500px;
        }

        h1, h2, h3, h4 { color: #ffffff; letter-spacing: -0.4px; }
        .stMarkdown p, .stMarkdown li, label, [data-testid="stWidgetLabel"] p { color: #e7e3ff; }
        [data-testid="stCaptionContainer"] { color: #9a94c9; }
        hr { border-color: rgba(148, 140, 220, .18); }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #14103a 0%, #0c0925 100%);
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] * { color: #e9e5ff; }

        [data-testid="stSidebar"] [role="radiogroup"] { gap: .25rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: .62rem .85rem;
            border-radius: 11px;
            border: 1px solid transparent;
            transition: all .18s ease;
            width: 100%;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(139, 92, 246, .16);
            transform: translateX(4px);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(90deg, #7c3aed, #8b5cf6);
            box-shadow: 0 6px 18px rgba(124, 58, 237, .38);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {
            color: #fff !important;
            font-weight: 700;
        }

        /* ---------- Hero 3D ---------- */
        .hero {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            padding: 1.6rem 2rem;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(167, 139, 250, .30);
            border-radius: 22px;
            background:
                radial-gradient(circle at 88% 30%, rgba(167, 139, 250, .32), transparent 28%),
                linear-gradient(115deg, rgba(38, 26, 94, .97), rgba(60, 31, 124, .93) 60%, rgba(30, 41, 110, .9));
            box-shadow: 0 18px 55px rgba(0, 0, 0, .30);
            animation: rise .7s ease both;
        }
        .hero h1 { color: #fff !important; font-size: 2.1rem; margin: 0 0 .35rem 0; }
        .hero p { color: #d8d0ff !important; margin: 0; font-size: 1rem; }
        .eyebrow {
            color: #c4b5fd;
            text-transform: uppercase;
            letter-spacing: .16em;
            font-size: .72rem;
            font-weight: 800;
            margin-bottom: .5rem;
        }

        .scene {
            width: 120px;
            height: 120px;
            perspective: 700px;
            flex-shrink: 0;
            margin-right: 1.5rem;
            animation: floaty 4.5s ease-in-out infinite;
        }
        .cube {
            position: relative;
            width: 120px;
            height: 120px;
            transform-style: preserve-3d;
            animation: spin 16s linear infinite;
        }
        .face {
            position: absolute;
            width: 120px;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.4rem;
            border: 1px solid rgba(196, 181, 253, .7);
            background: rgba(139, 92, 246, .20);
            box-shadow: inset 0 0 28px rgba(167, 139, 250, .45), 0 0 18px rgba(139, 92, 246, .35);
            border-radius: 10px;
        }
        .face.f1 { transform: translateZ(60px); }
        .face.f2 { transform: rotateY(180deg) translateZ(60px); }
        .face.f3 { transform: rotateY(90deg) translateZ(60px); }
        .face.f4 { transform: rotateY(-90deg) translateZ(60px); }
        .face.f5 { transform: rotateX(90deg) translateZ(60px); }
        .face.f6 { transform: rotateX(-90deg) translateZ(60px); }

        @keyframes spin {
            from { transform: rotateX(-22deg) rotateY(0deg); }
            to   { transform: rotateX(-22deg) rotateY(360deg); }
        }
        @keyframes floaty {
            0%, 100% { transform: translateY(0); }
            50%      { transform: translateY(-9px); }
        }
        @keyframes rise {
            from { opacity: 0; transform: perspective(900px) translateY(18px) rotateX(18deg); }
            to   { opacity: 1; transform: perspective(900px) translateY(0) rotateX(0deg); }
        }

        .info-box {
            padding: 13px 18px;
            border-left: 4px solid #8b5cf6;
            background: rgba(139, 92, 246, .12);
            color: #ddd6fe;
            border-radius: 10px;
            margin-bottom: 18px;
            font-size: .92rem;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #ffffff;
            margin-top: 1.3rem;
            margin-bottom: .7rem;
        }

        /* ---------- Cartes KPI avec inclinaison 3D ---------- */
        .tilt {
            perspective: 900px;
            animation: rise .65s ease both;
        }
        .metric-card {
            background: linear-gradient(145deg, rgba(34, 26, 84, .96), rgba(19, 15, 48, .96));
            border: 1px solid var(--border);
            border-radius: 17px;
            padding: 1.05rem 1.2rem;
            min-height: 122px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, .22);
            transform-style: preserve-3d;
            transition: transform .35s ease, box-shadow .35s ease, border-color .35s ease;
        }
        .tilt:hover .metric-card {
            transform: rotateX(7deg) rotateY(-9deg) translateZ(14px);
            box-shadow: -14px 20px 38px rgba(76, 29, 149, .45);
            border-color: rgba(196, 181, 253, .55);
        }
        .metric-top { display: flex; justify-content: space-between; align-items: center; }
        .metric-label { color: #b3acdf; font-size: .8rem; font-weight: 600; }
        .metric-icon {
            width: 32px; height: 32px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 10px;
            background: rgba(139, 92, 246, .22);
            font-size: 1rem;
            transform: translateZ(30px);
        }
        .metric-value {
            color: #ffffff;
            font-size: 1.9rem;
            font-weight: 800;
            margin-top: .35rem;
            transform: translateZ(22px);
        }
        .metric-caption { color: #8f89c0; font-size: .75rem; margin-top: .2rem; }

        /* ---------- Cartes (st.container(border=True)) ---------- */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(145deg, rgba(26, 20, 64, .94), rgba(15, 12, 40, .94));
            border: 1px solid var(--border) !important;
            border-radius: 18px !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, .2);
        }
        .card-title { color: #fff; font-weight: 800; font-size: 1rem; margin: 0 0 .1rem 0; }
        .card-sub { color: var(--muted); font-size: .78rem; margin-bottom: .4rem; }

        /* ---------- Liste de scénarios ---------- */
        .scn-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .8rem;
            padding: .7rem .9rem;
            margin-bottom: .55rem;
            border-radius: 13px;
            background: rgba(139, 120, 255, .10);
            border: 1px solid rgba(139, 120, 255, .18);
            transition: transform .25s ease, background .25s ease;
        }
        .scn-item:hover {
            transform: perspective(600px) translateZ(10px) rotateX(3deg);
            background: rgba(139, 120, 255, .18);
        }
        .scn-cat { color: #f1eeff; font-size: .86rem; font-weight: 700; }
        .scn-desc { color: #9d97c9; font-size: .74rem; margin-top: .1rem; }

        .status-success, .status-danger, .status-warning {
            border-radius: 999px;
            padding: 4px 11px;
            font-size: 12px;
            font-weight: 800;
            white-space: nowrap;
        }
        .status-success { color: #5eead4; background: rgba(45, 212, 191, .14); border: 1px solid rgba(45, 212, 191, .4); }
        .status-danger  { color: #fda4af; background: rgba(251, 113, 133, .13); border: 1px solid rgba(251, 113, 133, .4); }
        .status-warning { color: #fcd34d; background: rgba(251, 191, 36, .12); border: 1px solid rgba(251, 191, 36, .4); }

        /* ---------- Champs de saisie ---------- */
        .stTextInput input,
        [data-baseweb="input"] input {
            color: #f8f6ff !important;
            -webkit-text-fill-color: #f8f6ff !important;
            caret-color: #a78bfa !important;
            background-color: #15103a !important;
            border-color: rgba(139, 120, 255, .38) !important;
            opacity: 1 !important;
        }
        .stTextInput input::placeholder {
            color: #8a84b8 !important;
            -webkit-text-fill-color: #8a84b8 !important;
            opacity: 1 !important;
        }
        [data-baseweb="input"]:focus-within {
            border-color: #a78bfa !important;
            box-shadow: 0 0 0 1px rgba(167, 139, 250, .4) !important;
        }
        [data-baseweb="select"] > div {
            background-color: #15103a !important;
            border-color: rgba(139, 120, 255, .30) !important;
            border-radius: 11px !important;
        }
        [data-baseweb="select"] * { color: #f1eeff !important; }

        [data-testid="stForm"] {
            background: linear-gradient(145deg, rgba(26, 20, 64, .94), rgba(15, 12, 40, .94));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.2rem;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }

        /* ---------- Boutons ---------- */
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 11px;
            font-weight: 700;
            min-height: 2.7rem;
            background: rgba(139, 92, 246, .14);
            color: #ede9ff;
            border: 1px solid rgba(167, 139, 250, .4);
            transition: transform .2s ease, box-shadow .2s ease;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: #c4b5fd;
            color: #fff;
            transform: translateY(-2px) perspective(500px) rotateX(4deg);
            box-shadow: 0 10px 22px rgba(124, 58, 237, .35);
        }
        button[kind="primary"],
        button[kind="primaryFormSubmit"],
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primaryFormSubmit"] {
            background: linear-gradient(90deg, #7c3aed, #9d6bff) !important;
            color: #fff !important;
            border: 0 !important;
            border-radius: 11px;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------

def html_block(content):
    """Supprime l'indentation pour éviter que Markdown ne traite le HTML comme du code."""
    return "".join(line.strip() for line in content.splitlines())


def init_state():
    defaults = {
        "agent_connected": False,
        "agent_url": "",
        "agent_key": "",
        "audit_finished": False,
        "audit_running": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_agent_data(agent):
    audit_rows = HISTORY[HISTORY["Agent"] == agent]

    if audit_rows.empty:
        raise ValueError(f"Agent inconnu : {agent}")

    audit = audit_rows.iloc[0]

    categories = pd.DataFrame(
        {
            "Catégorie": list(CATEGORY_SCORES[agent].keys()),
            "Score": list(CATEGORY_SCORES[agent].values()),
        }
    )

    scenarios = pd.DataFrame(
        SCENARIOS[agent],
        columns=["Catégorie", "Scénario", "Statut"],
    )

    return audit, categories, scenarios


def get_score_color(score):
    if score >= 80:
        return C_OK
    if score >= 60:
        return C_WARN
    return C_BAD


def status_badge(status):
    if status == "Réussi":
        return '<span class="status-success">Réussi</span>'
    if status == "Échoué":
        return '<span class="status-danger">Échoué</span>'
    return f'<span class="status-warning">{escape(str(status))}</span>'


def display_metric(label, value, caption="", icon="🛡️", delay=0.0):
    st.markdown(
        html_block(
            f"""
            <div class="tilt" style="animation-delay:{delay}s">
              <div class="metric-card">
                <div class="metric-top">
                  <div class="metric-label">{escape(str(label))}</div>
                  <div class="metric-icon">{icon}</div>
                </div>
                <div class="metric-value">{escape(str(value))}</div>
                <div class="metric-caption">{escape(str(caption))}</div>
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def card_header(title, subtitle=""):
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="card-sub">{subtitle}</div>', unsafe_allow_html=True)


def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def scenarios_html(scenarios):
    rows = []
    for _, row in scenarios.iterrows():
        rows.append(
            f"""
            <div class="scn-item">
              <div>
                <div class="scn-cat">{escape(str(row["Catégorie"]))}</div>
                <div class="scn-desc">{escape(str(row["Scénario"]))}</div>
              </div>
              {status_badge(row["Statut"])}
            </div>
            """
        )
    return html_block("".join(rows))


def base_layout(height):
    return dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT),
        margin=dict(l=10, r=20, t=15, b=15),
    )


def add_rotation(fig, radius=2.3, height=0.9, steps=90):
    """Ajoute un bouton d'animation qui fait tourner la caméra 3D."""
    start = -math.pi / 4
    angles = [start + 2 * math.pi * i / steps for i in range(steps + 1)]

    fig.frames = [
        go.Frame(
            layout=dict(
                scene_camera=dict(
                    eye=dict(
                        x=radius * math.cos(a),
                        y=radius * math.sin(a),
                        z=height,
                    )
                )
            )
        )
        for a in angles
    ]

    fig.update_layout(
        scene_camera=dict(
            eye=dict(
                x=radius * math.cos(start),
                y=radius * math.sin(start),
                z=height,
            )
        ),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                direction="left",
                x=0.0,
                y=0.0,
                xanchor="left",
                yanchor="bottom",
                bgcolor="#2b1c6e",
                bordercolor="#a78bfa",
                font=dict(color="#ffffff"),
                buttons=[
                    dict(
                        label="▶ Rotation 3D",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=70, redraw=True),
                                transition=dict(duration=0),
                                fromcurrent=True,
                                mode="immediate",
                            ),
                        ],
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[
                            [None],
                            dict(
                                frame=dict(duration=0, redraw=False),
                                transition=dict(duration=0),
                                mode="immediate",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
    return fig


def scene_style(**extra):
    axis = dict(
        backgroundcolor="rgba(0,0,0,0)",
        gridcolor=GRID,
        zerolinecolor=GRID,
        showbackground=False,
        color=TEXT,
    )
    scene = dict(
        bgcolor="rgba(0,0,0,0)",
        xaxis=dict(axis),
        yaxis=dict(axis),
        zaxis=dict(axis),
    )
    scene.update(extra)
    return scene


def create_bar_chart(categories):
    fig = px.bar(
        categories,
        x="Score",
        y="Catégorie",
        orientation="h",
        text="Score",
        color="Score",
        color_continuous_scale=[
            [0, C_BAD],
            [0.6, C_WARN],
            [0.8, C_OK],
            [1, C_OK],
        ],
        range_color=[0, 100],
        range_x=[0, 125],
    )

    fig.update_traces(
        texttemplate="%{text}/100",
        textposition="outside",
        marker_line_width=0,
        textfont=dict(color="#f1eeff"),
    )

    fig.update_layout(
        **base_layout(340),
        coloraxis_showscale=False,
        xaxis=dict(title=None, gridcolor=GRID, zeroline=False),
        yaxis=dict(title=None, autorange="reversed"),
    )

    return fig


def create_donut_chart(audit):
    inconclusive = int(audit.get("Tests non concluants", 0))

    results = pd.DataFrame(
        {
            "Statut": ["Réussis", "Échoués"] + (["Non concluants"] if inconclusive else []),
            "Nombre": [int(audit["Tests réussis"]), int(audit["Tests échoués"])]
            + ([inconclusive] if inconclusive else []),
        }
    )

    rate = audit["Tests réussis"] / audit["Tests exécutés"]

    fig = px.pie(
        results,
        names="Statut",
        values="Nombre",
        hole=0.66,
        color="Statut",
        color_discrete_map={"Réussis": C_OK, "Échoués": C_BAD, "Non concluants": C_WARN},
    )

    fig.update_traces(
        marker=dict(line=dict(color="#0e0b2b", width=3)),
        textinfo="value",
        textfont=dict(color="#0e0b2b", size=14),
    )

    fig.update_layout(
        **base_layout(340),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
        annotations=[
            dict(
                text=f"<b>{rate:.0%}</b><br><span style='font-size:12px'>réussite</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=28, color="#ffffff"),
            )
        ],
    )

    return fig


def create_radar_chart(categories):
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=categories["Score"].tolist() + [categories["Score"].iloc[0]],
            theta=categories["Catégorie"].tolist() + [categories["Catégorie"].iloc[0]],
            fill="toself",
            line=dict(color=C_LILAC, width=3),
            fillcolor="rgba(139, 92, 246, 0.35)",
            name="Score",
        )
    )

    fig.update_layout(
        **{**base_layout(380), "margin": dict(l=45, r=45, t=30, b=30)},
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=GRID,
                linecolor=GRID,
                tickfont=dict(color="#8f89c0", size=10),
            ),
            angularaxis=dict(
                gridcolor=GRID,
                linecolor=GRID,
                tickfont=dict(color="#d8d3ff", size=11),
            ),
        ),
        showlegend=False,
    )

    return fig


def create_trend_chart(selected_agent):
    df = HISTORY.copy()
    df["Date_dt"] = pd.to_datetime(df["Date"], format="%d/%m/%Y %H:%M")
    df = df.sort_values("Date_dt")

    sizes = [16 if agent == selected_agent else 9 for agent in df["Agent"]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Date_dt"],
            y=df["Score global"],
            mode="lines+markers",
            line=dict(color=C_LILAC, width=3, shape="spline"),
            marker=dict(
                size=sizes,
                color=C_ORANGE,
                line=dict(color="#0e0b2b", width=2),
            ),
            fill="tozeroy",
            fillcolor="rgba(124, 58, 237, 0.35)",
            customdata=df["Agent"],
            hovertemplate="%{customdata}<br>%{x|%d/%m/%Y %H:%M}<br>Score : %{y}/100<extra></extra>",
        )
    )

    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color=C_ORANGE,
        annotation_text="Seuil recommandé : 80",
        annotation_font_color=C_ORANGE,
        annotation_position="top left",
    )

    fig.update_layout(
        **base_layout(320),
        showlegend=False,
        xaxis=dict(title=None, gridcolor=GRID, tickformat="%d/%m %H:%M"),
        yaxis=dict(title=None, gridcolor=GRID, range=[0, 105]),
    )

    return fig


def cube_mesh(x0, y0, width, height):
    """Retourne les sommets/faces d'un pavé 3D pour Mesh3d."""
    x = [x0, x0 + width, x0 + width, x0, x0, x0 + width, x0 + width, x0]
    y = [y0, y0, y0 + width, y0 + width, y0, y0, y0 + width, y0 + width]
    z = [0, 0, 0, 0, height, height, height, height]
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 6]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 2]
    return x, y, z, i, j, k


def create_3d_bars(categories):
    fig = go.Figure()
    width = 0.7
    tick_positions = []

    for idx, row in categories.iterrows():
        score = int(row["Score"])
        x0 = idx * 1.2
        x, y, z, i, j, k = cube_mesh(x0, 0, width, score)
        tick_positions.append(x0 + width / 2)

        fig.add_trace(
            go.Mesh3d(
                x=x, y=y, z=z, i=i, j=j, k=k,
                color=get_score_color(score),
                opacity=0.93,
                flatshading=True,
                lighting=dict(ambient=0.55, diffuse=0.85, specular=0.35),
                name=row["Catégorie"],
                hovertemplate=f"{row['Catégorie']}<br>Score : {score}/100<extra></extra>",
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter3d(
                x=[x0 + width / 2],
                y=[width / 2],
                z=[score + 7],
                mode="text",
                text=[str(score)],
                textfont=dict(color="#ffffff", size=13),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        **{**base_layout(380), "margin": dict(l=0, r=0, t=0, b=0)},
        scene=scene_style(
            xaxis=dict(
                tickvals=tick_positions,
                ticktext=[c.split(" ")[0] for c in categories["Catégorie"]],
                title=None,
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor=GRID,
                showbackground=False,
                color=TEXT,
            ),
            yaxis=dict(visible=False),
            zaxis=dict(
                range=[0, 110],
                title=None,
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor=GRID,
                showbackground=False,
                color=TEXT,
            ),
            aspectmode="manual",
            aspectratio=dict(x=1.9, y=0.7, z=0.85),
        ),
    )

    return add_rotation(fig, radius=2.4, height=0.9)


def create_3d_surface():
    agents = list(CATEGORY_SCORES.keys())[:8][::-1]  # 8 derniers audits, du plus ancien au plus récent
    categories = sorted({c for a in agents for c in CATEGORY_SCORES[a]})
    z = [[CATEGORY_SCORES[a].get(c, 0) for c in categories] for a in agents]

    fig = go.Figure(
        go.Surface(
            z=z,
            x=list(range(len(categories))),
            y=list(range(len(agents))),
            colorscale=[[0, C_BAD], [0.5, C_PURPLE], [1, C_OK]],
            cmin=40,
            cmax=100,
            showscale=False,
            hovertemplate="Score : %{z}/100<extra></extra>",
        )
    )

    fig.update_layout(
        **{**base_layout(420), "margin": dict(l=0, r=0, t=0, b=0)},
        scene=scene_style(
            xaxis=dict(
                tickvals=list(range(len(categories))),
                ticktext=[c.split(" ")[0] for c in categories],
                title=None,
                showbackground=False,
                gridcolor=GRID,
                color=TEXT,
            ),
            yaxis=dict(
                tickvals=list(range(len(agents))),
                ticktext=[a.split(" · ")[-1] for a in agents],
                title="Agent",
                showbackground=False,
                gridcolor=GRID,
                color=TEXT,
            ),
            zaxis=dict(
                range=[40, 100],
                title=None,
                showbackground=False,
                gridcolor=GRID,
                color=TEXT,
            ),
            aspectmode="manual",
            aspectratio=dict(x=1.6, y=1, z=0.8),
        ),
    )

    return add_rotation(fig, radius=2.2, height=1.0)


PLOTLY_CONFIG = {"displayModeBar": False}


def _table_style(top_valign=False, padding=7):
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), padding),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]
    if top_valign:
        style.append(("VALIGN", (0, 0), (-1, -1), "TOP"))
    return TableStyle(style)


def generate_pdf(agent, audit, categories, scenarios):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.HexColor("#16324F"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#16324F"),
        spaceBefore=12,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    elements = [
        Paragraph("AgentGuard", title_style),
        Paragraph("Rapport d'audit de sécurité", title_style),
        Spacer(1, 10),
        Paragraph(f"<b>Agent :</b> {agent}", normal_style),
        Paragraph(f"<b>Date :</b> {audit['Date']}", normal_style),
        Paragraph(
            f"<b>Score global :</b> {audit['Score global']}/100",
            normal_style,
        ),
        Spacer(1, 15),
        Paragraph("Résumé de l'audit", heading_style),
    ]

    summary_data = [
        ["Indicateur", "Valeur"],
        ["Tests exécutés", str(audit["Tests exécutés"])],
        ["Tests réussis", str(audit["Tests réussis"])],
        ["Tests échoués", str(audit["Tests échoués"])],
        ["Tests non concluants", str(audit.get("Tests non concluants", 0))],
        ["Attack Success Rate", f"{audit.get('Attack Success Rate', 0)}%"],
        ["Taux de réussite", f"{audit['Tests réussis'] / audit['Tests exécutés']:.0%}"],
    ]

    summary_table = Table(summary_data, colWidths=[95 * mm, 55 * mm], repeatRows=1)
    summary_table.setStyle(_table_style())

    elements.extend(
        [
            summary_table,
            Spacer(1, 14),
            Paragraph("Scores par catégorie", heading_style),
        ]
    )

    category_data = [["Catégorie", "Score"]]

    for _, row in categories.iterrows():
        category_data.append([str(row["Catégorie"]), f"{row['Score']}/100"])

    category_table = Table(category_data, colWidths=[95 * mm, 55 * mm], repeatRows=1)
    category_table.setStyle(_table_style())

    failed = scenarios[scenarios["Statut"] == "Échoué"]

    elements.extend(
        [
            category_table,
            Spacer(1, 14),
            Paragraph("Tests échoués et vulnérabilités détectées", heading_style),
        ]
    )

    if failed.empty:
        elements.append(
            Paragraph("Aucun test échoué sur les scénarios exécutés.", normal_style)
        )
    else:
        failed_data = [["Catégorie", "Scénario"]]
        for _, row in failed.iterrows():
            failed_data.append(
                [
                    Paragraph(escape(str(row["Catégorie"])), normal_style),
                    Paragraph(escape(str(row["Scénario"])), normal_style),
                ]
            )
        failed_table = Table(failed_data, colWidths=[55 * mm, 100 * mm], repeatRows=1)
        failed_table.setStyle(_table_style(top_valign=True, padding=6))
        elements.append(failed_table)

    elements.extend([Spacer(1, 14), Paragraph("Recommandations", heading_style)])

    recommendations = get_recommendations(failed["Catégorie"].unique())

    if recommendations:
        for category, text in recommendations:
            elements.append(
                Paragraph(f"<b>{escape(category)} :</b> {escape(text)}", normal_style)
            )
            elements.append(Spacer(1, 6))
    else:
        elements.append(
            Paragraph(
                "Aucune vulnérabilité détectée. Ce résultat porte uniquement sur "
                "les scénarios exécutés : continuez à tester régulièrement avec "
                "de nouveaux scénarios.",
                normal_style,
            )
        )

    elements.extend(
        [
            Spacer(1, 14),
            Paragraph("Détail des scénarios", heading_style),
        ]
    )

    scenario_data = [["Catégorie", "Scénario", "Statut"]]

    for _, row in scenarios.iterrows():
        scenario_data.append(
            [
                Paragraph(escape(str(row["Catégorie"])), normal_style),
                Paragraph(escape(str(row["Scénario"])), normal_style),
                str(row["Statut"]),
            ]
        )

    scenario_table = Table(
        scenario_data,
        colWidths=[42 * mm, 88 * mm, 25 * mm],
        repeatRows=1,
    )
    scenario_table.setStyle(_table_style(top_valign=True, padding=6))

    elements.extend(
        [
            scenario_table,
            Spacer(1, 18),
            Paragraph(
                "Rapport généré par AgentGuard à partir des données d’audit enregistrées.",
                ParagraphStyle(
                    "Footer",
                    parent=normal_style,
                    textColor=colors.HexColor("#64748B"),
                    fontSize=8,
                ),
            ),
        ]
    )

    document.build(elements)
    buffer.seek(0)

    return buffer.getvalue()


# ---------------------------------------------------------
# Initialisation
# ---------------------------------------------------------

init_state()

# État d'Ollama (vérifié à chaque affichage)
OLLAMA_MODELS, OLLAMA_ERROR = list_ollama_models()


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

MENU_ICONS = {
    "Dashboard": "▦",
    "Lancer un audit": "🚀",
    "Historique": "◷",
    "Rapports": "▤",
}

with st.sidebar:
    st.markdown(
        html_block(
            """
            <div style="display:flex;align-items:center;gap:.65rem;margin-bottom:1.4rem;">
              <div style="width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,#7c3aed,#a78bfa);
                          display:flex;align-items:center;justify-content:center;font-size:1.2rem;
                          box-shadow:0 8px 20px rgba(124,58,237,.45);">🛡️</div>
              <div>
                <div style="font-size:1.3rem;font-weight:800;color:#fff;line-height:1.1;">AgentGuard</div>
                <div style="color:#9d97c9;font-size:.7rem;letter-spacing:.1em;">SECURITY TESTING PLATFORM</div>
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        list(MENU_ICONS.keys()),
        format_func=lambda key: f"{MENU_ICONS[key]}   {key}",
        label_visibility="collapsed",
    )

    st.divider()

    if OLLAMA_ERROR:
        st.error("Ollama indisponible")
    else:
        st.success("Ollama prêt")
        st.caption(st.session_state.get("ollama_model") or get_model_name())

    st.divider()

    st.caption("Version démo 1.0")
    st.caption("© 2026 AgentGuard")


# ---------------------------------------------------------
# En-tête global avec cube 3D animé
# ---------------------------------------------------------

st.markdown(
    html_block(
        """
        <div class="hero">
          <div>
            <div class="eyebrow">Plateforme d'audit intelligente</div>
            <h1>🛡️ AgentGuard</h1>
            <p>Évaluez la robustesse et la sécurité de vos agents IA.</p>
          </div>
          <div class="scene">
            <div class="cube">
              <div class="face f1">🛡️</div>
              <div class="face f2">🔐</div>
              <div class="face f3">🤖</div>
              <div class="face f4">🔍</div>
              <div class="face f5">⚡</div>
              <div class="face f6">🧪</div>
            </div>
          </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-box">
        <b>À noter :</b>
        le Dashboard, l’Historique et les Rapports affichent les audits enregistrés.
        La page « Lancer un audit » exécute les scénarios réels et sauvegarde leurs résultats.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

if page == "Dashboard":
    section_title("Vue d’ensemble")

    if HISTORY.empty:
        st.info("Aucun audit enregistré. Lancez un audit depuis la page « Lancer un audit ».")
        st.stop()

    selected_agent = st.selectbox(
        "Agent affiché",
        HISTORY["Agent"].tolist(),
        index=0,
    )

    audit, categories, scenarios = get_agent_data(selected_agent)

    success_rate = audit["Tests réussis"] / audit["Tests exécutés"]
    average_score = categories["Score"].mean()

    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

    with kpi_1:
        display_metric("Score global", f"{audit['Score global']}/100", "Niveau de sécurité global", "🛡️", 0.0)

    with kpi_2:
        display_metric("Taux de réussite", f"{success_rate:.0%}", "Tests validés", "✅", 0.1)

    with kpi_3:
        display_metric("Tests exécutés", int(audit["Tests exécutés"]), "Scénarios analysés", "🧪", 0.2)

    with kpi_4:
        display_metric("Attack Success Rate", f"{audit['Attack Success Rate']}%", "Attaques ayant réussi", "🎯", 0.3)

    st.markdown("")

    left, right = st.columns([1.35, 1])

    with left:
        with st.container(border=True):
            card_header("Scores par catégorie", "Vert ≥ 80 · Jaune ≥ 60 · Rouge < 60")
            st.plotly_chart(
                create_bar_chart(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with right:
        with st.container(border=True):
            card_header("Répartition des résultats", "Tests réussis et échoués")
            st.plotly_chart(
                create_donut_chart(audit),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            card_header("Profil de sécurité", "Vue radar des catégories testées")
            st.plotly_chart(
                create_radar_chart(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with right:
        with st.container(border=True):
            card_header(
                "Scores en 3D",
                "Fais glisser pour tourner, ou clique sur « Rotation 3D »",
            )
            st.plotly_chart(
                create_3d_bars(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    left, right = st.columns([1.35, 1])

    with left:
        with st.container(border=True):
            card_header("Évolution des audits", "Score global par date (point agrandi = agent affiché)")
            st.plotly_chart(
                create_trend_chart(selected_agent),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with right:
        with st.container(border=True):
            card_header("Derniers scénarios", f"{selected_agent}")
            st.markdown(scenarios_html(scenarios), unsafe_allow_html=True)

    section_title("Résumé de l’audit")

    if audit["Score global"] >= 80:
        st.success("Cet agent présente un bon niveau de sécurité général.")
    elif audit["Score global"] >= 60:
        st.warning(
            "Cet agent présente un niveau de sécurité moyen. "
            "Des améliorations sont recommandées."
        )
    else:
        st.error(
            "Cet agent présente plusieurs risques importants. "
            "Une action corrective est nécessaire."
        )


# ---------------------------------------------------------
# Lancer un audit
# ---------------------------------------------------------

elif page == "Lancer un audit":
    section_title("Agent à tester")

    with st.container(border=True):
        if OLLAMA_ERROR:
            st.error(OLLAMA_ERROR)
            st.button("🔄 Vérifier Ollama")
        else:
            default_model = get_default_model()
            current_model = st.session_state.get("ollama_model")

            if current_model in OLLAMA_MODELS:
                start_index = OLLAMA_MODELS.index(current_model)
            elif default_model in OLLAMA_MODELS:
                start_index = OLLAMA_MODELS.index(default_model)
            else:
                start_index = 0

            st.selectbox(
                "Modèle Ollama à tester",
                OLLAMA_MODELS,
                index=start_index,
                key="ollama_model",
            )
            st.caption("Les modèles listés sont ceux installés sur cet ordinateur (ollama list).")

    test_cases, load_errors = load_test_cases()

    with st.expander(f"📋 Scénarios disponibles ({len(test_cases)})"):
        for message in load_errors:
            st.warning(message)

        if test_cases:
            st.dataframe(
                pd.DataFrame(test_cases)[
                    ["test_id", "category", "severity", "prompt"]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Aucun scénario trouvé dans le dossier tests/.")

    section_title("Exécuter les tests")

    if OLLAMA_ERROR:
        st.info("Démarrez Ollama, puis cliquez sur « Vérifier Ollama » avant de lancer un audit.")
    else:
        st.success(f"Agent prêt : {st.session_state['ollama_model']}")

        if st.button(
            "🚀 Lancer l’audit de sécurité",
            type="primary",
            use_container_width=True,
        ):
            if not test_cases:
                st.error("Aucun scénario valide trouvé dans le dossier tests/.")
            else:
                st.session_state["audit_running"] = True
                st.session_state["audit_finished"] = False

                progress = st.progress(0)
                status = st.empty()

                def update_progress(index, total, case):
                    progress.progress(index / total)
                    if case is not None:
                        status.info(
                            f"Test {index + 1}/{total} : "
                            f"{case['test_id']} ({case['category']})..."
                        )

                try:
                    set_model(st.session_state["ollama_model"])
                    results = run_audit(test_cases, update_progress)
                    model_name = get_model_name()
                    save_audit(model_name, results)
                    st.session_state["last_audit"] = {
                        "agent": model_name,
                        "results": results,
                    }
                    st.session_state["audit_finished"] = True
                    st.success("Audit terminé.")
                except (RuntimeError, OSError) as error:
                    st.error(str(error))
                finally:
                    st.session_state["audit_running"] = False
                    status.empty()

        last_audit = st.session_state.get("last_audit")

        if last_audit:
            section_title("Résultats")
            st.caption(f"Modèle testé : {last_audit['agent']}")

            audit, categories, scenarios = to_dashboard_data(
                last_audit["results"], last_audit["agent"]
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                display_metric("Score global", f"{audit['Score global']}/100", "Résultat global", "🛡️", 0.0)

            with col2:
                display_metric("Tests exécutés", audit["Tests exécutés"], "Scénarios analysés", "🧪", 0.1)

            with col3:
                display_metric("Tests réussis", audit["Tests réussis"], "Contrôles validés", "✅", 0.2)

            with col4:
                display_metric("Tests échoués", audit["Tests échoués"], "Points à corriger", "⚠️", 0.3)

            st.markdown("")

            left, right = st.columns([1.35, 1])

            with left:
                with st.container(border=True):
                    card_header("Scores par catégorie", "Résultats réels de l’audit")
                    st.plotly_chart(
                        create_3d_bars(categories),
                        use_container_width=True,
                        config=PLOTLY_CONFIG,
                    )

            with right:
                with st.container(border=True):
                    card_header("Détail des scénarios", last_audit["agent"])
                    st.markdown(scenarios_html(scenarios), unsafe_allow_html=True)

            with st.expander("🔎 Voir les réponses du modèle"):
                for item in last_audit["results"]:
                    st.markdown(f"**{item['test_id']}** : {item['status']}")
                    st.caption(item["reason"])
                    st.code(item["response"] or "(réponse vide)", language=None)



# ---------------------------------------------------------
# Historique
# ---------------------------------------------------------

elif page == "Historique":
    section_title("Historique des audits")

    if HISTORY.empty:
        st.info("Aucun audit enregistré. Lancez un audit depuis la page « Lancer un audit ».")
        st.stop()

    col1, col2 = st.columns([1, 2])

    with col1:
        min_score = st.slider(
            "Score minimum",
            min_value=0,
            max_value=100,
            value=0,
        )

    with col2:
        status_filter = st.multiselect(
            "Filtrer par statut",
            options=HISTORY["Statut"].unique().tolist(),
            default=HISTORY["Statut"].unique().tolist(),
        )

    filtered_history = HISTORY[
        (HISTORY["Score global"] >= min_score)
        & (HISTORY["Statut"].isin(status_filter))
    ]

    st.dataframe(
        filtered_history,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score global": st.column_config.ProgressColumn(
                "Score global",
                min_value=0,
                max_value=100,
                format="%d/100",
            ),
            "Tests exécutés": st.column_config.NumberColumn(
                "Tests exécutés",
                format="%d",
            ),
        },
    )

    st.download_button(
        "⬇️ Télécharger l’historique CSV",
        data=filtered_history.to_csv(index=False).encode("utf-8"),
        file_name="agentguard_history.csv",
        mime="text/csv",
    )

    section_title("Comparaison 3D des agents")

    with st.container(border=True):
        card_header(
            "Surface des scores",
            "Audits (du plus ancien au plus récent) en profondeur, catégories en largeur, score en hauteur",
        )
        if len(HISTORY) >= 2:
            st.plotly_chart(
                create_3d_surface(),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
        else:
            st.info("Lancez au moins deux audits pour comparer leurs scores.")

    section_title("Détails d’un audit")

    selected_agent = st.selectbox(
        "Sélectionner un agent",
        HISTORY["Agent"].tolist(),
    )

    audit, categories, scenarios = get_agent_data(selected_agent)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric("Score global", f"{audit['Score global']}/100", audit["Date"], "🛡️", 0.0)

    with col2:
        display_metric("Tests exécutés", audit["Tests exécutés"], "Total", "🧪", 0.1)

    with col3:
        display_metric("Tests réussis", audit["Tests réussis"], "Validés", "✅", 0.2)

    with col4:
        display_metric("Tests échoués", audit["Tests échoués"], "À corriger", "⚠️", 0.3)

    st.markdown("")

    left, right = st.columns([1.35, 1])

    with left:
        with st.container(border=True):
            card_header("Scores par catégorie")
            st.plotly_chart(
                create_bar_chart(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with right:
        with st.container(border=True):
            card_header("Scénarios", selected_agent)
            st.markdown(scenarios_html(scenarios), unsafe_allow_html=True)


# ---------------------------------------------------------
# Rapports
# ---------------------------------------------------------

elif page == "Rapports":
    section_title("Rapports d’audit")

    if HISTORY.empty:
        st.info("Aucun audit enregistré. Lancez un audit depuis la page « Lancer un audit ».")
        st.stop()

    selected_agent = st.selectbox(
        "Choisir l’agent",
        HISTORY["Agent"].tolist(),
    )

    audit, categories, scenarios = get_agent_data(selected_agent)

    col1, col2 = st.columns(2)

    with col1:
        display_metric("Agent sélectionné", selected_agent, f"Audit du {audit['Date']}", "🤖", 0.0)

    with col2:
        display_metric("Score global", f"{audit['Score global']}/100", "Score de sécurité", "🛡️", 0.1)

    section_title("Exporter les résultats")

    pdf_data = generate_pdf(
        selected_agent,
        audit,
        categories,
        scenarios,
    )

    csv_data = HISTORY[
        HISTORY["Agent"] == selected_agent
    ].to_csv(index=False).encode("utf-8")

    safe_name = re.sub(r"[^a-z0-9]+", "_", selected_agent.lower()).strip("_")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "📄 Télécharger le rapport PDF",
            data=pdf_data,
            file_name=f"agentguard_{safe_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "📊 Télécharger les données CSV",
            data=csv_data,
            file_name=f"{safe_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    section_title("Aperçu du rapport")

    left, right = st.columns([1.35, 1])

    with left:
        with st.container(border=True):
            card_header("Scores par catégorie")
            st.plotly_chart(
                create_bar_chart(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with right:
        with st.container(border=True):
            card_header("Scores en 3D", "Fais glisser pour tourner")
            st.plotly_chart(
                create_3d_bars(categories),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )

    with st.container(border=True):
        card_header("Détail des scénarios", selected_agent)
        st.markdown(scenarios_html(scenarios), unsafe_allow_html=True)