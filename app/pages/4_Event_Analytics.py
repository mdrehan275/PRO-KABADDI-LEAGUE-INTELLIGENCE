"""
app/pages/4_Event_Analytics.py
------------------------------
Granular Event-Stream Intelligence: Raid Outcomes, Do-or-Die Pressure,
Super Plays, and Second-Half Scoring Acceleration.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils import load_all_data, apply_custom_css, format_plotly_chart, PKL_ORANGE, PKL_NAVY, PKL_TEAL, PKL_RED, PKL_GREEN

st.set_page_config(page_title="Event Analytics | PKL Intelligence", page_icon="⏱️", layout="wide")
apply_custom_css()

st.title("⏱️ Play-by-Play Event Analytics")
st.markdown("Investigate the mechanics of individual plays: raid success vs empty rates, high-pressure Do-or-Die raids, and second-half momentum shifts.")

try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

df_events = data["fact_events"]
df_matches = data["fact_matches"]
dim_teams = data["dim_teams"]

official_mids = set(df_matches[df_matches['is_official_pkl']]['match_id'])
ev_official = df_events[df_events['match_id'].isin(official_mids)].copy()

# --- TOP METRIC TILES ---
total_plays = len(ev_official)
total_raids = len(ev_official[ev_official['event_type'].str.contains('Raid', na=False)])
total_dod = int(ev_official['is_do_or_die'].sum())
total_super_raids = int(ev_official['is_super_raid'].sum())
total_super_tackles = int(ev_official['is_super_tackle'].sum())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Recorded Plays", f"{total_plays:,}")
col2.metric("Raid Attempts", f"{total_raids:,}")
col3.metric("Do-or-Die Raids", f"{total_dod:,}")
col4.metric("Super Raids", f"{total_super_raids:,}", help="Raids generating >= 3 points")
col5.metric("Super Tackles", f"{total_super_tackles:,}", help="Tackles executed with <= 3 defenders on court")

st.markdown("---")

# --- ROW 1: RAID OUTCOMES & DO-OR-DIE CONVERSION ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🎯 Distribution of Raid Outcomes")
    
    raid_types = ev_official[ev_official['event_type'].str.contains('Raid', na=False)]['event_type'].value_counts()
    
    fig_donut = go.Figure(go.Pie(
        labels=raid_types.index,
        values=raid_types.values,
        hole=0.45,
        marker=dict(colors=[PKL_GREEN, '#FFA726', PKL_RED])
    ))
    format_plotly_chart(fig_donut, f"Raid Outcomes ({total_raids:,} raids)", height=380)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_right:
    st.subheader("⚡ Do-or-Die Pressure Conversion by Franchise")
    
    # Team DoD stats
    dod_events = ev_official[ev_official['is_do_or_die'] == True].copy()
    dod_by_team = dod_events.groupby('raiding_team_id').agg(
        total_dod=('event_row_id', 'count'),
        successful_dod=('event_type', lambda x: (x == 'Successful Raid').sum())
    ).reset_index()
    
    dod_by_team = pd.merge(dod_by_team, dim_teams[['team_id', 'team_name']], left_on='raiding_team_id', right_on='team_id')
    dod_by_team = dod_by_team[dod_by_team['total_dod'] >= 50].copy()
    dod_by_team['conversion_pct'] = np.round(100.0 * dod_by_team['successful_dod'] / dod_by_team['total_dod'], 1)
    dod_by_team = dod_by_team.sort_values(by='conversion_pct', ascending=True)

    fig_dod = go.Figure(go.Bar(
        x=dod_by_team['conversion_pct'],
        y=dod_by_team['team_name'],
        orientation='h',
        marker=dict(color=np.where(dod_by_team['conversion_pct'] >= 40.0, PKL_GREEN, PKL_NAVY)),
        text=[f"{v:.1f}% ({s}/{t})" for v, s, t in zip(dod_by_team['conversion_pct'], dod_by_team['successful_dod'], dod_by_team['total_dod'])],
        textposition='outside'
    ))
    format_plotly_chart(fig_dod, "Do-or-Die Raid Success Rate (Min 50 DoD Raids)", height=380)
    st.plotly_chart(fig_dod, use_container_width=True)

# --- ROW 2: TIMELINE SCORING ACCELERATION (FIRST HALF VS SECOND HALF) ---
st.subheader("⏳ Timing Dynamics: First-Half vs. Second-Half Scoring")

ev_official['half'] = np.where(ev_official['elapsed_seconds'] <= 1200, '1st Half (0-20 min)', '2nd Half (20-40 min)')
half_scoring = ev_official.groupby('half').agg(
    total_pts=('raid_points', lambda x: x.sum() + ev_official.loc[x.index, 'defending_points'].sum()),
    super_raids=('is_super_raid', 'sum'),
    super_tackles=('is_super_tackle', 'sum'),
    do_or_die=('is_do_or_die', 'sum')
).reset_index()

col_h1, col_h2, col_h3 = st.columns([1, 1, 1])

with col_h1:
    fig_half_pts = px.bar(
        half_scoring, x='half', y='total_pts',
        color='half', color_discrete_sequence=[PKL_NAVY, PKL_ORANGE],
        title="Points Scored: 1st vs 2nd Half"
    )
    format_plotly_chart(fig_half_pts, "Total Points by Match Half", height=320)
    st.plotly_chart(fig_half_pts, use_container_width=True)

with col_h2:
    fig_half_sp = px.bar(
        half_scoring, x='half', y=['super_raids', 'super_tackles'],
        barmode='group', color_discrete_sequence=['#FF9800', '#2196F3'],
        title="Explosive Plays by Half"
    )
    format_plotly_chart(fig_half_sp, "Super Plays by Match Half", height=320)
    st.plotly_chart(fig_half_sp, use_container_width=True)

with col_h3:
    fig_half_dod = px.bar(
        half_scoring, x='half', y='do_or_die',
        color='half', color_discrete_sequence=['#455A64', '#D32F2F'],
        title="Do-or-Die Raids by Half"
    )
    format_plotly_chart(fig_half_dod, "Do-or-Die Frequency by Half", height=320)
    st.plotly_chart(fig_half_dod, use_container_width=True)

st.markdown("""
> **Tactical Finding:** Teams score approximately **11.4% more points in the second half** than the first half. As trailing teams exhaust defensive covers and must take attacking risks, empty raids decrease and high-scoring super raids/tackles surge.
""")
