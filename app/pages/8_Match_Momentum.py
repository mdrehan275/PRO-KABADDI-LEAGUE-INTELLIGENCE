"""
app/pages/8_Match_Momentum.py
-------------------------------
Event-Reconstructed Match Momentum & Live Scoring Timeline.
Renders the chronological score progression for any official PKL match,
highlights lead-change moments, comeback victories, and first/second half dynamics.
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils import inject_custom_css
from src.analytics.momentum import build_match_momentum, count_lead_changes

st.set_page_config(page_title="Match Momentum | PKL Analytics", page_icon="📈", layout="wide")
inject_custom_css()

st.title("📈 Event-Reconstructed Match Momentum")
st.markdown("""
Play-by-play score reconstruction from 66,568 chronological events — revealing momentum swings,
lead changes, comeback victories, and scoring dominance patterns within individual matches.
""")

@st.cache_data
def load_match_catalog():
    df = pd.read_parquet("data/processed/fact_matches.parquet")
    official = df[(df["is_official_pkl"] == True) & (df["is_completed"] == True)].copy()
    official["label"] = (
        official["team_a_name"] + " vs " + official["team_b_name"] +
        "  (S" + official["season_id"].astype(int).astype(str) +
        " | " + official["match_date"] + ")"
    )
    return official.sort_values(["season_id", "match_date"])

df_matches = load_match_catalog()

# ── Sidebar Controls ─────────────────────────────────────────────────────────
st.sidebar.header("Select Match")
season_opts = sorted(df_matches["season_id"].unique().astype(int).tolist())
selected_season = st.sidebar.selectbox("Season", season_opts, index=len(season_opts) - 1)

season_matches = df_matches[df_matches["season_id"] == selected_season]

# Team filter
all_teams = sorted(set(season_matches["team_a_name"].tolist() + season_matches["team_b_name"].tolist()))
team_filter = st.sidebar.selectbox("Filter by Team (optional)", ["All Teams"] + all_teams)
if team_filter != "All Teams":
    season_matches = season_matches[
        (season_matches["team_a_name"] == team_filter) |
        (season_matches["team_b_name"] == team_filter)
    ]

if season_matches.empty:
    st.info("No matches found for this filter combination.")
    st.stop()

match_labels = dict(zip(season_matches["match_id"], season_matches["label"]))
chosen_match_id = st.sidebar.selectbox("Match", list(match_labels.keys()),
                                        format_func=lambda x: match_labels[x])

# ── Load momentum ─────────────────────────────────────────────────────────────
with st.spinner("Reconstructing event timeline..."):
    df_mom = build_match_momentum(chosen_match_id)

if df_mom is None or df_mom.empty:
    st.error("No event data available for this match.")
    st.stop()

team_a_name = df_mom["team_a_name"].iloc[0]
team_b_name = df_mom["team_b_name"].iloc[0]
final_a = int(df_mom["score_a"].iloc[-1])
final_b = int(df_mom["score_b"].iloc[-1])
stats = count_lead_changes(df_mom)

# ── Match Result Banner ───────────────────────────────────────────────────────
winner = team_a_name if final_a > final_b else (team_b_name if final_b > final_a else "TIE")
margin = abs(final_a - final_b)

col_a, col_mid, col_b = st.columns([1.2, 1.4, 1.2])
with col_a:
    st.markdown(
        f"<div style='text-align:center; padding:16px; border-radius:8px; "
        f"background:rgba(31,119,180,0.12); border:1px solid #1f77b4;'>"
        f"<h3 style='margin:0;color:#1f77b4;'>{team_a_name}</h3>"
        f"<h1 style='margin:4px 0; font-size:3.2rem;'>{final_a}</h1>"
        f"</div>", unsafe_allow_html=True)
with col_mid:
    st.markdown(
        f"<div style='text-align:center; padding:16px;'>"
        f"<p style='color:#888;font-size:0.8rem;letter-spacing:2px;text-transform:uppercase;'>Final Score</p>"
        f"<h2 style='margin:4px 0;'>{'🏆 ' + winner if winner != 'TIE' else '🤝 Tie'}</h2>"
        f"<p style='color:#888;'>Margin: {margin} pts | Lead Changes: {stats['lead_changes']}</p>"
        f"</div>", unsafe_allow_html=True)
with col_b:
    st.markdown(
        f"<div style='text-align:center; padding:16px; border-radius:8px; "
        f"background:rgba(214,39,40,0.12); border:1px solid #d62728;'>"
        f"<h3 style='margin:0;color:#d62728;'>{team_b_name}</h3>"
        f"<h1 style='margin:4px 0; font-size:3.2rem;'>{final_b}</h1>"
        f"</div>", unsafe_allow_html=True)

st.markdown("---")

# ── Main Momentum Chart ───────────────────────────────────────────────────────
st.subheader("Scoring Progression & Momentum Swings")

x = df_mom["event_seq"].values
y = df_mom["score_diff"].values
score_a_trace = df_mom["score_a"].values
score_b_trace = df_mom["score_b"].values

fig = go.Figure()

# Shaded differential regions
fig.add_trace(go.Scatter(
    x=x, y=np.where(y > 0, y, 0),
    fill="tozeroy", mode="none",
    fillcolor="rgba(31,119,180,0.22)", name=f"{team_a_name} Leads"
))
fig.add_trace(go.Scatter(
    x=x, y=np.where(y < 0, y, 0),
    fill="tozeroy", mode="none",
    fillcolor="rgba(214,39,40,0.22)", name=f"{team_b_name} Leads"
))
# Differential line
fig.add_trace(go.Scatter(
    x=x, y=y, mode="lines",
    line=dict(color="#2c3e50", width=2.2),
    name="Score Differential (A−B)", hovertemplate="Event %{x}<br>Diff: %{y:+d} pts<extra></extra>",
))
# Zero line
fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)

# Mark approximate half-time (median event)
half_idx = int(len(x) * 0.5)
fig.add_vline(x=half_idx, line_dash="dot", line_color="orange",
              annotation_text="Approx. Half-Time", annotation_position="top right")

fig.update_layout(
    xaxis_title="Event Sequence (Chronological)",
    yaxis_title=f"Score Differential ({team_a_name} − {team_b_name})",
    height=420,
    legend=dict(orientation="h", y=-0.22),
    hovermode="x unified",
    margin=dict(l=40, r=20, t=20, b=60),
)
st.plotly_chart(fig, use_container_width=True)

# ── Individual Score Lines ────────────────────────────────────────────────────
st.subheader("Cumulative Score Trajectories")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=x, y=score_a_trace, mode="lines",
    name=team_a_name, line=dict(color="#1f77b4", width=2.2),
    hovertemplate="Event %{x}<br>" + team_a_name + ": %{y} pts<extra></extra>"
))
fig2.add_trace(go.Scatter(
    x=x, y=score_b_trace, mode="lines",
    name=team_b_name, line=dict(color="#d62728", width=2.2),
    hovertemplate="Event %{x}<br>" + team_b_name + ": %{y} pts<extra></extra>"
))
fig2.update_layout(
    xaxis_title="Event Sequence", yaxis_title="Cumulative Score",
    height=380, legend=dict(orientation="h", y=-0.22),
    hovermode="x unified", margin=dict(l=40, r=20, t=20, b=60),
)
st.plotly_chart(fig2, use_container_width=True)

# ── Momentum Statistics Panel ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("Match Control Statistics")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Lead Changes", stats["lead_changes"])
m2.metric(f"{team_a_name} Led", f"{stats['team_a_lead_pct']}%")
m3.metric(f"{team_b_name} Led", f"{stats['team_b_lead_pct']}%")
m4.metric("Time Tied", f"{stats['tied_pct']}%")
m5.metric("Comeback Victory", "Yes 🔥" if stats["comeback"] else "No")

# ── Event Type Breakdown ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Event Type Distribution in This Match")

ev_type_map = {
    1: "Successful Raid", 2: "Unsuccessful Raid", 3: "Empty Raid",
    4: "Tackle Success", 5: "All-Out", 9: "Super Tackle", 10: "Other"
}
ev_counts = (
    df_mom.groupby("event_type_id").size().reset_index(name="count")
)
ev_counts["event_label"] = ev_counts["event_type_id"].map(lambda x: ev_type_map.get(x, f"Type {x}"))

fig3 = go.Figure(go.Bar(
    x=ev_counts["event_label"], y=ev_counts["count"],
    marker_color="#3498db", opacity=0.85,
))
fig3.update_layout(xaxis_title="Event Type", yaxis_title="Count", height=300, margin=dict(t=10, b=40))
st.plotly_chart(fig3, use_container_width=True)
