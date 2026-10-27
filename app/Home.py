"""
app/Home.py
-----------
PKL Analytics & Intelligence Platform - Main Landing Page & League Overview.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils import load_all_data, apply_custom_css, format_plotly_chart, PKL_ORANGE, PKL_NAVY, PKL_TEAL

st.set_page_config(
    page_title="PKL Analytics & Intelligence Platform",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_css()

# Header Banner
st.markdown('<span class="badge-pkl">PRO KABADDI LEAGUE INTELLIGENCE</span>', unsafe_allow_html=True)
st.title("🏆 PKL Analytics & Intelligence Platform")
st.markdown("""
*Historical Performance Analysis, Player Intelligence, Tactical Dynamics, and Match Outcome Prediction across PKL Seasons 1 to 7.*
""")

# Load Cached Data
try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.stop()

df_matches = data["fact_matches"]
df_team_match = data["fact_team_match"]
df_player_match = data["fact_player_match"]
dim_seasons = data["dim_seasons"]
dim_teams = data["dim_teams"]

# Official PKL filtered slice
df_m_official = df_matches[df_matches['is_official_pkl'] & df_matches['is_completed']].copy()
df_tm_official = df_team_match[df_team_match['is_official_pkl'] & (df_team_match['status'] == 'Full Time')].copy()

# Sidebar Filters & Scope Selector
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/0/01/Pro_Kabaddi_League_logo.svg/330px-Pro_Kabaddi_League_logo.svg.png", width=160)
st.sidebar.header("Platform Navigation & Filters")
scope_filter = st.sidebar.radio(
    "Competition Scope:",
    ["Official PKL League (Seasons 1–7)", "All Available Competitions (Including World Cup & Masters)"],
    index=0
)

if scope_filter == "Official PKL League (Seasons 1–7)":
    active_matches = df_m_official
    active_tm = df_tm_official
else:
    active_matches = df_matches[df_matches['is_completed']]
    active_tm = df_team_match[df_team_match['status'] == 'Full Time']

# --- TOP KPI METRIC TILES ---
st.markdown("### 📊 Executive League Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

total_matches = len(active_matches)
total_teams = active_tm['team_name'].nunique()
total_seasons = active_matches['season_name'].nunique()
total_player_appearances = len(df_player_match[df_player_match['played']])
avg_match_score = active_matches['total_match_points'].mean()

# Highest scoring match
highest_match = active_matches.loc[active_matches['total_match_points'].idxmax()]

col1.metric("Total Matches", f"{total_matches:,}")
col2.metric("Franchises / Teams", f"{total_teams}")
col3.metric("Seasons Covered", f"{total_seasons}")
col4.metric("Player Appearances", f"{total_player_appearances:,}", help="Total recorded individual on-court match appearances")
col5.metric("Avg Match Points", f"{avg_match_score:.1f} pts")

st.markdown(f"""
> **Highest-Scoring Match:** **{highest_match['team_a_name']} ({highest_match['team_a_score']})** vs **{highest_match['team_b_name']} ({highest_match['team_b_score']})** — **{highest_match['total_match_points']} aggregate points** on *{highest_match['match_date']}* at *{highest_match['venue_name']}*.
""")

st.markdown("---")

# --- SECTION 2: CHARTS ROW 1 ---
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    st.subheader("📈 Season-by-Season Scoring Trajectory")
    season_agg = df_tm_official.groupby('season_id').agg(
        avg_score=('score', 'mean'),
        avg_raid=('raid_points_total', 'mean'),
        avg_tackle=('tackle_points_total', 'mean'),
        avg_allout=('all_out_points', 'mean')
    ).reset_index()
    season_agg['season_label'] = "Season " + season_agg['season_id'].astype(str)

    fig_season = go.Figure()
    fig_season.add_trace(go.Bar(
        x=season_agg['season_label'], y=season_agg['avg_raid'],
        name='Raid Points', marker_color=PKL_ORANGE
    ))
    fig_season.add_trace(go.Bar(
        x=season_agg['season_label'], y=season_agg['avg_tackle'],
        name='Tackle Points', marker_color=PKL_NAVY
    ))
    fig_season.add_trace(go.Bar(
        x=season_agg['season_label'], y=season_agg['avg_allout'],
        name='All-Out Points', marker_color=PKL_TEAL
    ))
    fig_season.update_layout(barmode='stack')
    format_plotly_chart(fig_season, "Average Team Score Breakdown by Season", height=380)
    st.plotly_chart(fig_season, use_container_width=True)

with col_right:
    st.subheader("🎯 Match Outcome Distributions")
    
    # Margin bins
    margin_labels = ['Tie (0 pts)', 'Clutch (1-3 pts)', 'Close (4-7 pts)', 'Moderate (8-14 pts)', 'Blowout (15+ pts)']
    def get_margin_bin(row):
        if row['is_tie']:
            return 'Tie (0 pts)'
        m = row['win_margin']
        if m <= 3:
            return 'Clutch (1-3 pts)'
        elif m <= 7:
            return 'Close (4-7 pts)'
        elif m <= 14:
            return 'Moderate (8-14 pts)'
        else:
            return 'Blowout (15+ pts)'

    margin_series = active_matches.apply(get_margin_bin, axis=1).value_counts()[margin_labels]
    
    fig_pie = go.Figure(go.Pie(
        labels=margin_series.index,
        values=margin_series.values,
        hole=0.45,
        marker=dict(colors=['#9E9E9E', '#E65100', '#FB8C00', '#1976D2', '#0D47A1'])
    ))
    format_plotly_chart(fig_pie, "Victory Margin Breakdown (% of Fixtures)", height=380)
    st.plotly_chart(fig_pie, use_container_width=True)

# --- SECTION 3: ALL-TIME TEAM RANKINGS TABLE ---
st.subheader("🏅 Franchise All-Time Leaderboard")

team_rankings = df_tm_official.groupby('team_name').agg(
    matches=('match_id', 'count'),
    wins=('is_winner', 'sum'),
    ties=('result', lambda r: (r == 'Tie').sum()),
    losses=('result', lambda r: (r == 'Loss').sum()),
    points_for=('score', 'sum'),
    points_against=('opponent_score', 'sum'),
    avg_score=('score', 'mean'),
    diff=('score_difference', 'sum')
).reset_index()

team_rankings['win_pct'] = np.round(100.0 * team_rankings['wins'] / team_rankings['matches'], 2)
team_rankings['avg_score'] = np.round(team_rankings['avg_score'], 1)
team_rankings = team_rankings.sort_values(by=['win_pct', 'wins'], ascending=[False, False]).reset_index(drop=True)
team_rankings.index = team_rankings.index + 1

st.dataframe(
    team_rankings.rename(columns={
        "team_name": "Franchise",
        "matches": "Played",
        "wins": "Won",
        "ties": "Tied",
        "losses": "Lost",
        "win_pct": "Win %",
        "points_for": "Pts Scored",
        "points_against": "Pts Conceded",
        "avg_score": "Avg Pts/Match",
        "diff": "Score Differential"
    }),
    use_container_width=True,
    height=420
)

# --- SECTION 4: PLATFORM NAVIGATION GUIDE ---
st.markdown("---")
st.markdown("### 🧭 Platform Explorer Modules")
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

with col_m1:
    st.markdown("#### 🛡️ Team Analytics")
    st.caption("Deep-dive franchise win rates, scoring efficiency, raid vs tackle tactical quadrants, and seasonal momentum.")

with col_m2:
    st.markdown("#### 🏃 Player Analytics")
    st.caption("Individual player profiles, radar charts, strike rates, Super 10s, High 5s, and performance volatility.")

with col_m3:
    st.markdown("#### ⚔️ Match Explorer")
    st.caption("Single fixture deep-dive, official box scores, starting 7 lineups, player of the match, and venue details.")

with col_m4:
    st.markdown("#### ⏱️ Event Analytics")
    st.caption("Granular play-by-play timelines, Do-or-Die raid conversion, super raid/tackle dynamics, and lead progression.")

with col_m5:
    st.markdown("#### 🔍 SQL & Methodology")
    st.caption("Interactive query runner executing 22 advanced SQL queries, KPI math definitions, and data-quality contracts.")
