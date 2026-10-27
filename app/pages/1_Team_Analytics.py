"""
app/pages/1_Team_Analytics.py
-----------------------------
Franchise-level deep-dive analytics, season trends, benchmark comparisons,
and tactical strengths/weaknesses profiling.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils import load_all_data, apply_custom_css, format_plotly_chart, PKL_ORANGE, PKL_NAVY, PKL_TEAL, PKL_RED, PKL_GREEN

st.set_page_config(page_title="Team Analytics | PKL Intelligence", page_icon="🛡️", layout="wide")
apply_custom_css()

st.title("🛡️ Franchise & Team Analytics")
st.markdown("Analyze team performance, offensive/defensive balance, seasonal trajectories, and tactical strengths.")

try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

df_team_match = data["fact_team_match"]
dim_teams = data["dim_teams"]

# Filter official teams
official_teams = sorted(dim_teams[dim_teams['is_pkl_franchise']]['team_name'].tolist())

# --- SIDEBAR FILTERS ---
st.sidebar.header("Team & Season Filter")
selected_team = st.sidebar.selectbox("Select Franchise:", official_teams, index=official_teams.index("U Mumba") if "U Mumba" in official_teams else 0)

available_seasons = ["All Seasons"] + [f"Season {s}" for s in sorted(df_team_match[df_team_match['team_name'] == selected_team]['season_id'].dropna().unique())]
selected_season = st.sidebar.selectbox("Select Season:", available_seasons, index=0)

# Filter dataset
team_df = df_team_match[df_team_match['team_name'] == selected_team].copy()
league_df = df_team_match[df_team_match['is_official_pkl']].copy()

if selected_season != "All Seasons":
    season_num = int(selected_season.replace("Season ", ""))
    team_df = team_df[team_df['season_id'] == season_num]
    league_df = league_df[league_df['season_id'] == season_num]

if team_df.empty:
    st.warning(f"No match records found for {selected_team} in {selected_season}.")
    st.stop()

# --- TOP METRICS ---
matches_count = len(team_df)
wins = (team_df['result'] == 'Win').sum()
losses = (team_df['result'] == 'Loss').sum()
ties = (team_df['result'] == 'Tie').sum()
win_pct = 100.0 * wins / matches_count if matches_count > 0 else 0.0
avg_score = team_df['score'].mean()
avg_conceded = team_df['opponent_score'].mean()
diff = team_df['score_difference'].sum()

# League averages for benchmarks
lg_avg_score = league_df['score'].mean()
lg_avg_conceded = league_df['opponent_score'].mean()
lg_win_pct = 50.0  # Zero-sum baseline

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Matches Played", f"{matches_count}")
col2.metric("Win Percentage", f"{win_pct:.1f}%", delta=f"{win_pct - lg_win_pct:+.1f}% vs League")
col3.metric("Avg Pts Scored", f"{avg_score:.1f}", delta=f"{avg_score - lg_avg_score:+.1f} vs Avg")
col4.metric("Avg Pts Conceded", f"{avg_conceded:.1f}", delta=f"{-(avg_conceded - lg_avg_conceded):+.1f} vs Avg", delta_color="inverse")
col5.metric("Point Differential", f"{diff:+d}")

st.markdown("---")

# --- ROW 1: TACTICAL CONTRIBUTION & BENCHMARK RADAR ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader(f"📊 Point Contribution Breakdown: {selected_team}")
    
    total_raid_pts = team_df['raid_points_total'].sum()
    total_tackle_pts = team_df['tackle_points_total'].sum()
    total_allout_pts = team_df['all_out_points'].sum()
    total_extras_pts = team_df['extra_points'].sum()
    
    fig_donut = go.Figure(go.Pie(
        labels=['Raid Points', 'Tackle Points', 'All-Out Points', 'Extra Points'],
        values=[total_raid_pts, total_tackle_pts, total_allout_pts, total_extras_pts],
        hole=0.45,
        marker=dict(colors=[PKL_ORANGE, PKL_NAVY, PKL_TEAL, PKL_RED])
    ))
    format_plotly_chart(fig_donut, f"Total Points Scored ({team_df['score'].sum():,} pts)", height=380)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_right:
    st.subheader("🎯 Tactical Benchmark Comparison")
    
    # 5 KPI metrics normalized
    metrics_labels = ['Raid Strike Rate (%)', 'Tackle Strike Rate (%)', 'Avg Score', 'Super Tackles / Match', 'All-Outs / Match']
    
    t_raid_sr = 100.0 * team_df['raids_successful'].sum() / max(team_df['raids_total'].sum(), 1)
    t_tackle_sr = 100.0 * team_df['tackles_successful'].sum() / max(team_df['tackles_total'].sum(), 1)
    t_score = avg_score
    t_st = team_df['super_tackles'].sum() / matches_count
    t_ao = team_df['all_outs_inflicted'].sum() / matches_count

    l_raid_sr = 100.0 * league_df['raids_successful'].sum() / max(league_df['raids_total'].sum(), 1)
    l_tackle_sr = 100.0 * league_df['tackles_successful'].sum() / max(league_df['tackles_total'].sum(), 1)
    l_score = lg_avg_score
    l_st = league_df['super_tackles'].sum() / len(league_df)
    l_ao = league_df['all_outs_inflicted'].sum() / len(league_df)

    # Scale to index (100 = league avg)
    team_values = [
        t_raid_sr / l_raid_sr * 100,
        t_tackle_sr / l_tackle_sr * 100,
        t_score / l_score * 100,
        t_st / max(l_st, 0.01) * 100,
        t_ao / max(l_ao, 0.01) * 100
    ]
    benchmark_values = [100, 100, 100, 100, 100]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=team_values, theta=metrics_labels, fill='toself', name=selected_team, line=dict(color=PKL_ORANGE, width=2)
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=benchmark_values, theta=metrics_labels, fill='none', name='League Baseline (100)', line=dict(color='gray', dash='dash', width=1.5)
    ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[50, 150])))
    format_plotly_chart(fig_radar, f"{selected_team} vs League Baseline (Index = 100)", height=380)
    st.plotly_chart(fig_radar, use_container_width=True)

# --- ROW 2: MATCH-BY-MATCH FORM TRAJECTORY ---
st.subheader(f"📈 Match-by-Match Scoring & Form: {selected_team}")

team_chrono = team_df.sort_values(by='match_date').reset_index(drop=True)
team_chrono['match_num'] = np.arange(1, len(team_chrono) + 1)
team_chrono['rolling_3_avg'] = team_chrono['score'].rolling(3, min_periods=1).mean()

fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=team_chrono['match_num'],
    y=team_chrono['score'],
    name='Points Scored',
    marker_color=np.where(team_chrono['result'] == 'Win', PKL_GREEN, np.where(team_chrono['result'] == 'Tie', 'gray', PKL_RED)),
    hovertext=[f"vs {row['opponent_team_name']} ({row['score']}-{row['opponent_score']}) on {row['match_date']}" for _, row in team_chrono.iterrows()]
))
fig_trend.add_trace(go.Scatter(
    x=team_chrono['match_num'],
    y=team_chrono['rolling_3_avg'],
    name='3-Match Rolling Avg',
    line=dict(color='#0D47A1', width=3)
))
fig_trend.add_hline(y=avg_score, line_dash='dash', line_color='orange', annotation_text=f"Team Mean ({avg_score:.1f})")
format_plotly_chart(fig_trend, "Game-by-Game Points Scored (Green = Win, Red = Loss, Gray = Tie)", height=380)
st.plotly_chart(fig_trend, use_container_width=True)

# --- ROW 3: STRENGTHS, WEAKNESSES, AND EVIDENCE ---
st.subheader("💡 Tactical Strengths, Weaknesses & Evidence")

col_str, col_wk = st.columns(2)

with col_str:
    st.markdown("#### ✅ Primary Tactical Strengths")
    strengths = []
    if t_raid_sr > l_raid_sr:
        strengths.append(f"**High Offensive Efficiency:** Raid strike rate of **{t_raid_sr:.1f}%** outperforms the league baseline ({l_raid_sr:.1f}%).")
    if t_tackle_sr > l_tackle_sr:
        strengths.append(f"**Stingy Court Defense:** Defensive tackle conversion of **{t_tackle_sr:.1f}%** ranks above league average ({l_tackle_sr:.1f}%).")
    if t_ao > l_ao:
        strengths.append(f"**All-Out Infliction Power:** Averages **{t_ao:.2f} all-outs inflicted per match** (League: {l_ao:.2f}).")
    if t_st > l_st:
        strengths.append(f"**Super Tackle Threat:** High clutch defensive scoring with **{t_st:.2f} super tackles/game**.")
    if not strengths:
        strengths.append(f"Consistent roster rotation and disciplined court positioning across regulation fixtures.")
    for s in strengths:
        st.markdown(f"- {s}")

with col_wk:
    st.markdown("#### ⚠️ Tactical Vulnerabilities & Risks")
    weaknesses = []
    if t_raid_sr <= l_raid_sr:
        weaknesses.append(f"**Raid Conversion Deficit:** Offensive strike rate of **{t_raid_sr:.1f}%** trails the league average ({l_raid_sr:.1f}%).")
    if t_tackle_sr <= l_tackle_sr:
        weaknesses.append(f"**Tackle Leaks:** Defensive capture rate of **{t_tackle_sr:.1f}%** allows opposing raiders frequent escape points.")
    if avg_conceded > lg_avg_conceded:
        weaknesses.append(f"**High Points Conceded:** Allows an average of **{avg_conceded:.1f} pts/match** (League average: {lg_avg_conceded:.1f}).")
    if not weaknesses:
        weaknesses.append("Occasional third-raid (Do-or-Die) pressure stalls during high-intensity closing minutes.")
    for w in weaknesses:
        st.markdown(f"- {w}")
