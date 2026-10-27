"""
app/pages/3_Match_Explorer.py
-----------------------------
Deep-dive match explorer: box scores, official squad rosters, player of the match,
and chronological event timelines.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils import load_all_data, apply_custom_css, format_plotly_chart, PKL_ORANGE, PKL_NAVY, PKL_TEAL, PKL_GREEN, PKL_RED

st.set_page_config(page_title="Match Explorer | PKL Intelligence", page_icon="⚔️", layout="wide")
apply_custom_css()

st.title("⚔️ Match Explorer & Box Scores")
st.markdown("Examine full game statistics, official team box scores, player of the match, and chronological event timelines.")

try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

df_matches = data["fact_matches"]
df_team_match = data["fact_team_match"]
df_player_match = data["fact_player_match"]
df_events = data["fact_events"]

# --- SIDEBAR MATCH SELECTOR ---
st.sidebar.header("Match Selection")

# Filter by season first
seasons = ["All Official Seasons"] + [f"Season {s}" for s in sorted(df_matches[df_matches['season_id'].notnull()]['season_id'].unique().astype(int))]
sel_season = st.sidebar.selectbox("Filter by Season:", seasons, index=0)

m_pool = df_matches[df_matches['is_completed']].copy()
if sel_season != "All Official Seasons":
    s_num = int(sel_season.replace("Season ", ""))
    m_pool = m_pool[m_pool['season_id'] == s_num]

# Formatted match dropdown label: "Match ID - Team A vs Team B (Date)"
m_pool['dropdown_label'] = (
    "Match " + m_pool['match_id'].astype(str) + ": " +
    m_pool['team_a_name'] + " vs " + m_pool['team_b_name'] + " (" +
    m_pool['match_date'] + ")"
)

dropdown_options = m_pool['dropdown_label'].tolist()
default_match_label = dropdown_options[0] if dropdown_options else None
selected_label = st.sidebar.selectbox("Select Match:", dropdown_options, index=0)

match_id = int(selected_label.split(":")[0].replace("Match ", ""))
match_row = df_matches[df_matches['match_id'] == match_id].iloc[0]

# --- SCOREBOARD HEADER CARD ---
st.markdown("---")
score_col1, score_col2, score_col3 = st.columns([1.2, 0.6, 1.2])

with score_col1:
    is_a_win = match_row['winner_team_id'] == match_row['team_a_id']
    st.markdown(f"### {'🏆 ' if is_a_win else ''}{match_row['team_a_name']}")
    st.markdown(f"<h1 style='color: {'#2E7D32' if is_a_win else '#424242'}; font-size: 3.5rem; margin-top: -10px;'>{match_row['team_a_score']}</h1>", unsafe_allow_html=True)

with score_col2:
    st.markdown("<p style='text-align: center; color: gray; font-size: 1.2rem; font-weight: bold; margin-top: 15px;'>FINAL</p>", unsafe_allow_html=True)
    if match_row['is_tie']:
        st.markdown("<p style='text-align: center; color: orange; font-weight: bold;'>MATCH TIED</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='text-align: center; color: #1565C0; font-weight: 600;'>Margin: {match_row['win_margin']} pts</p>", unsafe_allow_html=True)

with score_col3:
    is_b_win = match_row['winner_team_id'] == match_row['team_b_id']
    st.markdown(f"### {'🏆 ' if is_b_win else ''}{match_row['team_b_name']}")
    st.markdown(f"<h1 style='color: {'#2E7D32' if is_b_win else '#424242'}; font-size: 3.5rem; margin-top: -10px;'>{match_row['team_b_score']}</h1>", unsafe_allow_html=True)

# Metadata pills
meta1, meta2, meta3, meta4 = st.columns(4)
meta1.markdown(f"**📅 Date:** {match_row['match_date']}")
meta2.markdown(f"**🏟️ Venue:** {match_row['venue_name']}")
meta3.markdown(f"**🪙 Toss Winner:** {match_row['team_a_name'] if match_row['toss_winner_id'] == match_row['team_a_id'] else match_row['team_b_name']} ({match_row['toss_selection']})")
potm_text = match_row['player_of_the_match_name'] if pd.notnull(match_row['player_of_the_match_name']) else "Not Awarded / Tied"
meta4.markdown(f"**🌟 Player of the Match:** **{potm_text}**")

st.markdown("---")

# --- TEAM STATISTICS COMPARISON TABLE ---
st.subheader("📊 Team Performance Comparison")

tm_match = df_team_match[df_team_match['match_id'] == match_id].set_index('team_name')
if len(tm_match) >= 2:
    t_a_stats = tm_match.loc[match_row['team_a_name']]
    t_b_stats = tm_match.loc[match_row['team_b_name']]

    comparison_data = {
        "Metric": [
            "Total Score",
            "Raid Points (Touch + Bonus)",
            "Tackle Points (Captures + Super Tackles)",
            "All-Out Points Inflicted",
            "Extra Points Awarded",
            "Total Raids Attempted",
            "Successful Raids",
            "Empty Raids",
            "Super Raids (3+ pts)",
            "Total Tackles Attempted",
            "Successful Tackles",
            "Super Tackles (<=3 defenders)",
            "Raid Success Rate (%)",
            "Tackle Success Rate (%)"
        ],
        match_row['team_a_name']: [
            t_a_stats['score'],
            f"{t_a_stats['raid_points_total']} ({t_a_stats['raid_points_touch']} touch, {t_a_stats['raid_points_bonus']} bonus)",
            f"{t_a_stats['tackle_points_total']} ({t_a_stats['tackle_points_capture']} capture, {t_a_stats['tackle_points_bonus']} bonus)",
            t_a_stats['all_out_points'],
            t_a_stats['extra_points'],
            t_a_stats['raids_total'],
            t_a_stats['raids_successful'],
            t_a_stats['raids_empty'],
            t_a_stats['super_raids'],
            t_a_stats['tackles_total'],
            t_a_stats['tackles_successful'],
            t_a_stats['super_tackles'],
            f"{t_a_stats['raid_success_rate']*100:.1f}%",
            f"{t_a_stats['tackle_success_rate']*100:.1f}%"
        ],
        match_row['team_b_name']: [
            t_b_stats['score'],
            f"{t_b_stats['raid_points_total']} ({t_b_stats['raid_points_touch']} touch, {t_b_stats['raid_points_bonus']} bonus)",
            f"{t_b_stats['tackle_points_total']} ({t_b_stats['tackle_points_capture']} capture, {t_b_stats['tackle_points_bonus']} bonus)",
            t_b_stats['all_out_points'],
            t_b_stats['extra_points'],
            t_b_stats['raids_total'],
            t_b_stats['raids_successful'],
            t_b_stats['raids_empty'],
            t_b_stats['super_raids'],
            t_b_stats['tackles_total'],
            t_b_stats['tackles_successful'],
            t_b_stats['super_tackles'],
            f"{t_b_stats['raid_success_rate']*100:.1f}%",
            f"{t_b_stats['tackle_success_rate']*100:.1f}%"
        ]
    }
    st.table(pd.DataFrame(comparison_data).set_index("Metric"))

# --- PLAYER BOX SCORES ---
st.subheader("🏃 Individual Player Box Scores")

pm_match = df_player_match[df_player_match['match_id'] == match_id].copy()

tab_a, tab_b = st.tabs([match_row['team_a_name'], match_row['team_b_name']])

with tab_a:
    pm_a = pm_match[pm_match['team_id'] == match_row['team_a_id']].sort_values(by=['starter', 'total_points'], ascending=[False, False])
    st.dataframe(
        pm_a[['player_name', 'player_role', 'starter', 'captain', 'total_points', 'raid_points_total', 'raid_points_touch', 'raid_points_bonus', 'tackle_points_total', 'super_10', 'high_5']].rename(columns={
            "player_name": "Player Name",
            "player_role": "Role",
            "starter": "Starter",
            "captain": "Captain",
            "total_points": "Total Pts",
            "raid_points_total": "Raid Pts",
            "raid_points_touch": "Touch Pts",
            "raid_points_bonus": "Bonus Pts",
            "tackle_points_total": "Tackle Pts",
            "super_10": "Super 10",
            "high_5": "High 5"
        }),
        use_container_width=True
    )

with tab_b:
    pm_b = pm_match[pm_match['team_id'] == match_row['team_b_id']].sort_values(by=['starter', 'total_points'], ascending=[False, False])
    st.dataframe(
        pm_b[['player_name', 'player_role', 'starter', 'captain', 'total_points', 'raid_points_total', 'raid_points_touch', 'raid_points_bonus', 'tackle_points_total', 'super_10', 'high_5']].rename(columns={
            "player_name": "Player Name",
            "player_role": "Role",
            "starter": "Starter",
            "captain": "Captain",
            "total_points": "Total Pts",
            "raid_points_total": "Raid Pts",
            "raid_points_touch": "Touch Pts",
            "raid_points_bonus": "Bonus Pts",
            "tackle_points_total": "Tackle Pts",
            "super_10": "Super 10",
            "high_5": "High 5"
        }),
        use_container_width=True
    )

# --- CHRONOLOGICAL PLAY-BY-PLAY EVENT TIMELINE ---
st.subheader("⏱️ Play-by-Play Event Timeline")

ev_match = df_events[df_events['match_id'] == match_id].sort_values(by='event_no').copy()

if not ev_match.empty:
    ev_match['time_min'] = ev_match['elapsed_seconds'] / 60.0
    
    # Timeline score chart
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=ev_match['time_min'], y=ev_match['score_team_a'],
        name=match_row['team_a_name'], line=dict(color=PKL_ORANGE, width=2.5)
    ))
    fig_line.add_trace(go.Scatter(
        x=ev_match['time_min'], y=ev_match['score_team_b'],
        name=match_row['team_b_name'], line=dict(color=PKL_NAVY, width=2.5)
    ))
    fig_line.add_vline(x=20.0, line_dash="dash", line_color="gray", annotation_text="Half Time")
    format_plotly_chart(fig_line, "Score Progression over Regulation Match Clock (Minutes)", height=350)
    st.plotly_chart(fig_line, use_container_width=True)

    # Key highlight events
    st.markdown("#### ⚡ Highlight Plays (Super Raids, Super Tackles & Multi-Point Raids)")
    highlights = ev_match[(ev_match['is_super_raid'] == True) | (ev_match['is_super_tackle'] == True) | (ev_match['raid_points'] >= 2)]
    if not highlights.empty:
        st.dataframe(
            highlights[['event_no', 'clock', 'event_type', 'event_text', 'raid_points', 'defending_points', 'score_team_a', 'score_team_b', 'is_do_or_die']].rename(columns={
                "event_no": "Play #",
                "clock": "Game Clock",
                "event_type": "Play Type",
                "event_text": "Action Description",
                "raid_points": "Raid Pts",
                "defending_points": "Def Pts",
                "score_team_a": f"{match_row['team_a_name']} Score",
                "score_team_b": f"{match_row['team_b_name']} Score",
                "is_do_or_die": "Do-or-Die"
            }),
            use_container_width=True
        )
    else:
        st.info("No super raids or super tackles occurred in this fixture.")
else:
    st.info("Play-by-play event timeline records are not available for this match.")
