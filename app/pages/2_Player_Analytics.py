"""
app/pages/2_Player_Analytics.py
-------------------------------
Player Intelligence, Individual Scouting, Milestone Tracking, and Peer Comparison.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils import load_all_data, apply_custom_css, format_plotly_chart, PKL_ORANGE, PKL_NAVY, PKL_TEAL, PKL_GREEN

st.set_page_config(page_title="Player Analytics | PKL Intelligence", page_icon="🏃", layout="wide")
apply_custom_css()

st.title("🏃 Player Intelligence & Scouting")
st.markdown("Individual player career profiles, strike rates, Super 10s, High 5s, volatility index, and peer benchmarking.")

try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

df_player_match = data["fact_player_match"]
dim_players = data["dim_players"]
dim_teams = data["dim_teams"]

# Filter official PKL player appearances
pm_official = df_player_match[df_player_match['is_official_pkl'] & df_player_match['played']].copy()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Player Scouting Filter")

# Filter by Role
available_roles = ["All Roles"] + sorted(dim_players['primary_role'].unique().tolist())
selected_role = st.sidebar.selectbox("Filter by Role:", available_roles, index=0)

filtered_players = dim_players.copy()
if selected_role != "All Roles":
    filtered_players = filtered_players[filtered_players['primary_role'] == selected_role]

# Minimum matches cutoff
min_apps = st.sidebar.slider("Minimum Career Matches:", min_value=1, max_value=50, value=15)
qualified_players = filtered_players[filtered_players['total_career_appearances'] >= min_apps].sort_values(by='total_career_points', ascending=False)

if qualified_players.empty:
    st.warning("No players match the specified filters. Try lowering the minimum match threshold.")
    st.stop()

player_names = qualified_players['player_name'].tolist()
default_player = "Pardeep Narwal" if "Pardeep Narwal" in player_names else player_names[0]
selected_player_name = st.sidebar.selectbox("Select Player:", player_names, index=player_names.index(default_player))

# Active Player Profile
player_row = qualified_players[qualified_players['player_name'] == selected_player_name].iloc[0]
player_id = int(player_row['player_id'])
p_matches = pm_official[pm_official['player_id'] == player_id].sort_values(by='match_date').reset_index(drop=True)

if p_matches.empty:
    st.warning(f"No match box scores recorded for {selected_player_name}.")
    st.stop()

# --- TOP KPI TILES ---
total_points = p_matches['total_points'].sum()
appearances = len(p_matches)
ppm = total_points / appearances if appearances > 0 else 0
total_raid_pts = p_matches['raid_points_total'].sum()
total_tackle_pts = p_matches['tackle_points_total'].sum()
super_10s = int(p_matches['super_10'].sum())
high_5s = int(p_matches['high_5'].sum())
raid_sr = 100.0 * p_matches['raids_successful'].sum() / max(p_matches['raids_total'].sum(), 1)
tackle_sr = 100.0 * p_matches['tackles_successful'].sum() / max(p_matches['tackles_total'].sum(), 1)

# Overall ranking
rank_in_role = (qualified_players[qualified_players['primary_role'] == player_row['primary_role']]['total_career_points'] > total_points).sum() + 1

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Player Role", f"{player_row['primary_role']}", help="Empirically classified by career on-court actions")
col2.metric("Total Points", f"{total_points:,} pts", help=f"Rank #{rank_in_role} in role")
col3.metric("Points / Match", f"{ppm:.2f} pts")
col4.metric("Super 10s / High 5s", f"{super_10s} S10 | {high_5s} H5")
col5.metric("Strike Rates", f"{raid_sr:.1f}% Raid | {tackle_sr:.1f}% Tkl")

st.markdown("---")

# --- ROW 1: GAME-BY-GAME SCORING & FORM TRAJECTORY ---
col_left, col_right = st.columns([1.2, 0.8])

with col_left:
    st.subheader(f"📈 Game-by-Game Scoring Trajectory: {selected_player_name}")
    
    p_matches['game_seq'] = np.arange(1, len(p_matches) + 1)
    p_matches['rolling_5_avg'] = p_matches['total_points'].rolling(5, min_periods=1).mean()
    
    fig_pts = go.Figure()
    fig_pts.add_trace(go.Bar(
        x=p_matches['game_seq'],
        y=p_matches['raid_points_total'],
        name='Raid Points',
        marker_color=PKL_ORANGE
    ))
    fig_pts.add_trace(go.Bar(
        x=p_matches['game_seq'],
        y=p_matches['tackle_points_total'],
        name='Tackle Points',
        marker_color=PKL_NAVY
    ))
    fig_pts.add_trace(go.Scatter(
        x=p_matches['game_seq'],
        y=p_matches['rolling_5_avg'],
        name='5-Match Rolling Avg',
        line=dict(color='#D32F2F', width=2.5)
    ))
    fig_pts.update_layout(barmode='stack')
    format_plotly_chart(fig_pts, f"Points per Game ({appearances} appearances)", height=380)
    st.plotly_chart(fig_pts, use_container_width=True)

with col_right:
    st.subheader("🎯 Skill & Action Breakdown")
    
    touches = p_matches['raid_points_touch'].sum()
    bonuses = p_matches['raid_points_bonus'].sum()
    tackles_regular = p_matches['tackle_points_touch'].sum()
    super_tackle_bonuses = p_matches['tackle_points_capture_bonus'].sum()
    
    fig_donut = go.Figure(go.Pie(
        labels=['Raid Touch Pts', 'Raid Bonus Pts', 'Tackle Captures', 'Super Tackle Bonus'],
        values=[touches, bonuses, tackles_regular, super_tackle_bonuses],
        hole=0.45,
        marker=dict(colors=['#E65100', '#FFA726', '#1565C0', '#42A5F5'])
    ))
    format_plotly_chart(fig_donut, f"Scoring Method Composition ({total_points} pts)", height=380)
    st.plotly_chart(fig_donut, use_container_width=True)

# --- ROW 2: PEER BENCHMARK COMPARISON ---
st.subheader(f"👥 Peer Comparison: Top {player_row['primary_role']}s in PKL History")

# Peer group
peers = qualified_players[qualified_players['primary_role'] == player_row['primary_role']].head(10).copy()
peers['ppm'] = np.round(peers['total_career_points'] / peers['total_career_appearances'], 2)

fig_peers = px.scatter(
    peers,
    x='total_career_appearances',
    y='ppm',
    size='total_career_points',
    color='player_name',
    hover_name='player_name',
    labels={"total_career_appearances": "Career Appearances", "ppm": "Average Points Per Appearance"},
    title=f"Career Volume vs. Scoring Efficiency among {player_row['primary_role']}s"
)
format_plotly_chart(fig_peers, f"Peer Efficiency Benchmark ({player_row['primary_role']}s)", height=380)
st.plotly_chart(fig_peers, use_container_width=True)

# Peer Table
st.dataframe(
    peers[['player_name', 'total_career_appearances', 'total_career_points', 'total_career_raid_points', 'total_career_tackle_points', 'ppm']].rename(columns={
        "player_name": "Player",
        "total_career_appearances": "Matches Played",
        "total_career_points": "Total Points",
        "total_career_raid_points": "Raid Points",
        "total_career_tackle_points": "Tackle Points",
        "ppm": "Avg Pts/Match"
    }),
    use_container_width=True
)
