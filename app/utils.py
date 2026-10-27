"""
app/utils.py
------------
Shared data loading, caching, UI styling, and helper routines for the Streamlit application.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Fallback search paths for Streamlit Cloud and local execution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATE_DIRS = [
    os.path.join(BASE_DIR, "data", "processed"),
    os.path.join(BASE_DIR, "Data", "processed"),
    os.path.abspath("data/processed"),
    os.path.abspath("Data/processed"),
]

PROCESSED_DIR = next((d for d in CANDIDATE_DIRS if os.path.isdir(d)), CANDIDATE_DIRS[0])

# Canonical Color Palette
PKL_ORANGE = "#FF6F00"
PKL_NAVY = "#0D47A1"
PKL_TEAL = "#00897B"
PKL_RED = "#D32F2F"
PKL_GREEN = "#388E3C"
PKL_GOLD = "#FBC02D"
PKL_SLATE = "#37474F"


@st.cache_data(show_spinner=False)
def load_all_data():
    """
    Cached data loader reading all preprocessed Parquet tables.
    Returns a dictionary of DataFrames.
    """
    tables = [
        "dim_seasons", "dim_teams", "dim_venues", "dim_players",
        "fact_matches", "fact_team_match", "fact_player_match", "fact_events"
    ]
    data = {}
    for tbl in tables:
        pq_path = os.path.join(PROCESSED_DIR, f"{tbl}.parquet")
        csv_path = os.path.join(PROCESSED_DIR, f"{tbl}.csv")
        if os.path.exists(pq_path):
            data[tbl] = pd.read_parquet(pq_path)
        elif os.path.exists(csv_path):
            data[tbl] = pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(f"Table {tbl} not found in {PROCESSED_DIR}")
    return data


def apply_custom_css():
    """Injects custom sports-analytics CSS styling for polished visual appeal."""
    st.markdown("""
        <style>
            /* Main container adjustments */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                max-width: 1280px;
            }
            
            /* Metric KPI card container styling */
            div[data-testid="metric-container"] {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border: 1px solid #dee2e6;
                padding: 1rem 1.25rem;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            div[data-testid="metric-container"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
            }
            div[data-testid="metric-container"] label {
                font-weight: 600;
                color: #495057;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
                color: #0D47A1;
                font-size: 1.8rem;
                font-weight: 700;
            }

            /* Section headers */
            h1, h2, h3 {
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: #1A237E;
            }
            
            /* Sidebar banner */
            .css-1d391kg {
                padding-top: 1.5rem;
            }
            
            /* Callout badge */
            .badge-pkl {
                background-color: #FF6F00;
                color: white;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
                display: inline-block;
                margin-bottom: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)


def format_plotly_chart(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    """Applies unified sports-analytics theme to Plotly figures."""
    fig.update_layout(
        title={
            'text': f"<b>{title}</b>",
            'y': 0.95,
            'x': 0.02,
            'xanchor': 'left',
            'yanchor': 'top',
            'font': {'size': 16, 'color': '#1A237E'}
        },
        template='plotly_white',
        height=height,
        margin=dict(l=40, r=40, t=60, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Segoe UI"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    return fig
