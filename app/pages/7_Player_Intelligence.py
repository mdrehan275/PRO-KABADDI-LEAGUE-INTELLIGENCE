"""
app/pages/7_Player_Intelligence.py
------------------------------------
Player Clustering & Performance Intelligence Dashboard.
Reveals player archetypes via KMeans clustering on career rate statistics,
renders searchable scouting profiles, and shows comparative scatter plots.
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils import inject_custom_css

st.set_page_config(page_title="Player Intelligence | PKL Analytics", page_icon="🏹", layout="wide")
inject_custom_css()

st.title("🏹 Player Intelligence & Archetype Clustering")
st.markdown("""
272 active PKL players profiled using **unsupervised KMeans clustering** (k=4, Silhouette Score=0.39)
on 7 career rate features: raid/tackle points per match, raid/tackle success rates, action share,
touch-point share, and milestone rates.
""")

CLUSTER_LABELS = {
    0: ("Elite Raider / Raid Specialist",      "#e74c3c"),
    1: ("Balanced All-Rounder",                "#3498db"),
    2: ("Defensive Anchor / Tackle Specialist","#2ecc71"),
    3: ("Rotation / Support Player",           "#f39c12"),
}

@st.cache_data
def load_clusters():
    p = pd.read_parquet("data/processed/player_clusters.parquet")
    p["archetype_label"] = p["cluster_id"].map(lambda x: CLUSTER_LABELS.get(x, (f"Cluster {x}", "#888"))[0])
    p["archetype_color"] = p["cluster_id"].map(lambda x: CLUSTER_LABELS.get(x, (f"Cluster {x}", "#888"))[1])
    return p

try:
    df = load_clusters()
except FileNotFoundError:
    st.warning("Player cluster data not found. Run `python src/analytics/player_clustering.py` first.")
    st.stop()

# ── Sidebar Filters ──────────────────────────────────────────────────────────
st.sidebar.header("Filters")
archetype_options = sorted(df["archetype_label"].unique())
selected_archetypes = st.sidebar.multiselect(
    "Player Archetypes",
    options=archetype_options,
    default=archetype_options
)
min_matches = st.sidebar.slider("Minimum Career Matches", 10, 80, 15)
search_name = st.sidebar.text_input("Search Player Name")

df_filtered = df[
    (df["archetype_label"].isin(selected_archetypes)) &
    (df["matches"] >= min_matches)
].copy()
if search_name:
    df_filtered = df_filtered[df_filtered["player_name"].str.contains(search_name, case=False, na=False)]

# ── Top KPI Row ──────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
for c_id, (label, color) in CLUSTER_LABELS.items():
    cnt = len(df[df["cluster_id"] == c_id])
    emoji = ["⚡", "🤸", "🛡️", "🔄"][c_id]
    [col1, col2, col3, col4][c_id].metric(f"{emoji} {label.split('/')[0].strip()}", f"{cnt} players")

st.markdown("---")

# ── Tab Layout ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️  Archetype Map (PCA Scatter)",
    "📊  Cluster Profiles",
    "🔍  Player Scouting Card",
    "⚔️  Head-to-Head Comparison",
])

# ── Tab 1: PCA Scatter Plot ──────────────────────────────────────────────────
with tab1:
    st.subheader("Player Archetype Landscape (PCA 2D Projection)")
    st.caption("Each dot is a player. Axes are the top 2 principal components of their 7 career rate features.")

    color_map = {v[0]: v[1] for v in CLUSTER_LABELS.values()}
    fig_scatter = px.scatter(
        df_filtered,
        x="pca_x", y="pca_y",
        color="archetype_label",
        color_discrete_map=color_map,
        hover_name="player_name",
        hover_data={
            "matches": True,
            "raid_pt_per_match": ":.2f",
            "tackle_pt_per_match": ":.2f",
            "raid_succ_rate": ":.2%",
            "tackle_succ_rate": ":.2%",
            "pca_x": False,
            "pca_y": False,
        },
        labels={"pca_x": "PC1 (Raid Specialisation Axis)", "pca_y": "PC2 (Efficiency Axis)"},
        height=560,
    )
    fig_scatter.update_traces(marker=dict(size=9, opacity=0.82, line=dict(width=0.4, color="white")))
    fig_scatter.update_layout(legend_title_text="Player Archetype", legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Tab 2: Cluster Profile Heatmap ───────────────────────────────────────────
with tab2:
    st.subheader("Cluster Feature Profiles")
    feat_cols = ["raid_pt_per_match", "tackle_pt_per_match", "raid_succ_rate",
                 "tackle_succ_rate", "raid_action_share", "touch_share", "milestone_rate"]
    label_map = {
        "raid_pt_per_match":    "Raid Pts / Match",
        "tackle_pt_per_match":  "Tackle Pts / Match",
        "raid_succ_rate":       "Raid Success Rate",
        "tackle_succ_rate":     "Tackle Success Rate",
        "raid_action_share":    "Raid Action Share",
        "touch_share":          "Touch Point Share",
        "milestone_rate":       "Super-10 / High-5 Rate",
    }

    cluster_means = (
        df.groupby("archetype_label")[feat_cols].mean()
    ).rename(columns=label_map)

    fig_heat = px.imshow(
        cluster_means,
        color_continuous_scale="RdYlGn",
        text_auto=".2f",
        aspect="auto",
        height=340,
        title="Normalised Cluster Centroids (Raw Means)",
    )
    fig_heat.update_xaxes(side="bottom")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("**Cluster Interpretation**")
    for c_id, (label, color) in CLUSTER_LABELS.items():
        sub = df[df["cluster_id"] == c_id]
        top = sub.nlargest(5, "total_pts")["player_name"].tolist()
        st.markdown(
            f"<div style='border-left: 4px solid {color}; padding: 6px 12px; margin: 6px 0; border-radius: 4px;'>"
            f"<b>{label}</b> — {len(sub)} players<br>"
            f"<small>Top: {', '.join(top)}</small></div>",
            unsafe_allow_html=True,
        )

# ── Tab 3: Player Scouting Card ───────────────────────────────────────────────
with tab3:
    if df_filtered.empty:
        st.info("No players match the selected filters.")
    else:
        player_names = df_filtered.sort_values("total_pts", ascending=False)["player_name"].tolist()
        chosen = st.selectbox("Select Player", player_names)
        row = df_filtered[df_filtered["player_name"] == chosen].iloc[0]

        cA, cB = st.columns([1, 2])
        with cA:
            archetype_color = row["archetype_color"]
            st.markdown(
                f"<div style='border-radius:12px; padding:20px; background:{archetype_color}22; "
                f"border: 1px solid {archetype_color}; text-align:center;'>"
                f"<h2 style='margin:0;'>{row['player_name']}</h2>"
                f"<p style='margin:4px 0; color:{archetype_color}; font-weight:bold;'>{row['archetype_label']}</p>"
                f"<p style='margin:4px 0; color:#888;'>Career: {int(row['matches'])} matches | "
                f"{int(row['total_pts'])} total pts</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("#### Career Metrics")
            metrics = {
                "Raid Pts / Match": f"{row['raid_pt_per_match']:.2f}",
                "Tackle Pts / Match": f"{row['tackle_pt_per_match']:.2f}",
                "Raid Success Rate": f"{row['raid_succ_rate']*100:.1f}%",
                "Tackle Success Rate": f"{row['tackle_succ_rate']*100:.1f}%",
                "Raid Action Share": f"{row['raid_action_share']*100:.1f}%",
                "Super-10 Achievements": str(int(row.get("super_10s", 0))),
                "High-5 Achievements": str(int(row.get("high_5s", 0))),
            }
            for k, v in metrics.items():
                st.markdown(f"- **{k}:** {v}")

        with cB:
            st.markdown("#### Performance Radar vs Archetype Average")
            categories = ["Raid Pts/Match", "Tackle Pts/Match", "Raid Succ Rate",
                          "Tackle Succ Rate", "Milestone Rate"]
            feat_map = {
                "Raid Pts/Match": "raid_pt_per_match",
                "Tackle Pts/Match": "tackle_pt_per_match",
                "Raid Succ Rate": "raid_succ_rate",
                "Tackle Succ Rate": "tackle_succ_rate",
                "Milestone Rate": "milestone_rate",
            }
            archetype_group = df[df["cluster_id"] == row["cluster_id"]]
            maxvals = {k: df[v].quantile(0.95) + 1e-6 for k, v in feat_map.items()}

            player_vals = [min(row[feat_map[c]] / maxvals[c], 1.0) for c in categories]
            arch_vals   = [min(archetype_group[feat_map[c]].mean() / maxvals[c], 1.0) for c in categories]

            fig_radar = go.Figure()
            for vals, name, color in [(player_vals, row["player_name"], archetype_color),
                                       (arch_vals, f"{row['archetype_label']} Avg", "#888")]:
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=categories + [categories[0]],
                    fill="toself", name=name,
                    line=dict(color=color, width=2), opacity=0.7,
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True, height=400,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

# ── Tab 4: Head-to-Head Player Comparison ────────────────────────────────────
with tab4:
    st.subheader("Head-to-Head Player Benchmark Scatter")
    col_x, col_y = st.columns(2)
    with col_x:
        p1_name = st.selectbox("Player A", df_filtered.sort_values("total_pts", ascending=False)["player_name"].tolist(), key="p1")
    with col_y:
        p2_opts = df_filtered[df_filtered["player_name"] != p1_name]["player_name"].sort_values().tolist()
        p2_name = st.selectbox("Player B", p2_opts, key="p2")

    feat_x = st.selectbox("X-Axis Feature", ["raid_pt_per_match", "raid_succ_rate", "tackle_succ_rate", "total_pt_per_match"])
    feat_y = st.selectbox("Y-Axis Feature", ["tackle_pt_per_match", "milestone_rate", "raid_succ_rate", "tackle_succ_rate"], index=1)

    fig_comp = px.scatter(
        df_filtered, x=feat_x, y=feat_y,
        color="archetype_label", color_discrete_map=color_map,
        hover_name="player_name", opacity=0.55, height=500,
        labels={feat_x: feat_x.replace("_", " ").title(), feat_y: feat_y.replace("_", " ").title()},
    )
    for name, marker_symbol in [(p1_name, "star"), (p2_name, "diamond")]:
        row = df_filtered[df_filtered["player_name"] == name]
        if not row.empty:
            r = row.iloc[0]
            fig_comp.add_trace(go.Scatter(
                x=[r[feat_x]], y=[r[feat_y]], mode="markers+text",
                text=[name], textposition="top center",
                marker=dict(symbol=marker_symbol, size=16, color=r["archetype_color"],
                            line=dict(width=2, color="white")),
                name=name, showlegend=True,
            ))

    st.plotly_chart(fig_comp, use_container_width=True)
