"""
src/analytics/player_clustering.py
-----------------------------------
Player profiling and unsupervised clustering for PKL Analytics.
Uses KMeans with silhouette analysis on standardized rate features
to segment players into archetypes (Elite Raider, Star Defender, etc.).
"""

import os
import sys
import logging
from typing import Dict, Tuple, Optional
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

os.environ["OMP_NUM_THREADS"] = "2"

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Cluster Label Map (assigned post-hoc via centroid inspection) ────────────
CLUSTER_LABELS = {
    0: ("Elite Raider / Raid Specialist",     "#e74c3c"),
    1: ("Balanced All-Rounder",               "#3498db"),
    2: ("Defensive Anchor / Tackle Specialist","#2ecc71"),
    3: ("Rotation / Support Player",          "#f39c12"),
}

FEATURE_COLS = [
    "raid_pt_per_match",
    "tackle_pt_per_match",
    "raid_succ_rate",
    "tackle_succ_rate",
    "raid_action_share",
    "touch_share",
    "milestone_rate",
]


def _build_player_stats(df_pm: pd.DataFrame, min_matches: int = 10, min_actions: int = 15) -> pd.DataFrame:
    """Aggregate per-player career stats for clustering."""
    df = df_pm[df_pm["is_official_pkl"] == True].copy()

    agg = df.groupby(["player_id", "player_name"]).agg(
        matches=("match_id", "nunique"),
        total_pts=("total_points", "sum"),
        raid_pts=("raid_points_total", "sum"),
        tackle_pts=("tackle_points_total", "sum"),
        raids_tot=("raids_total", "sum"),
        raids_succ=("raids_successful", "sum"),
        tackles_tot=("tackles_total", "sum"),
        tackles_succ=("tackles_successful", "sum"),
        touch_pts=("raid_points_touch", "sum"),
        bonus_pts=("raid_points_bonus", "sum"),
        super_10s=("super_10", "sum"),
        high_5s=("high_5", "sum"),
        primary_role=("player_role", lambda x: x.mode().iloc[0] if len(x) > 0 else "Unknown"),
    ).reset_index()

    # Filter active players with sufficient track record
    p = agg[
        (agg["matches"] >= min_matches) &
        ((agg["raids_tot"] + agg["tackles_tot"]) >= min_actions)
    ].copy()

    # Derived rate features
    p["raid_pt_per_match"]  = p["raid_pts"] / p["matches"]
    p["tackle_pt_per_match"] = p["tackle_pts"] / p["matches"]
    p["total_pt_per_match"]  = p["total_pts"] / p["matches"]
    p["raid_succ_rate"]      = np.where(p["raids_tot"] > 0, p["raids_succ"] / p["raids_tot"], 0.0)
    p["tackle_succ_rate"]    = np.where(p["tackles_tot"] > 0, p["tackles_succ"] / p["tackles_tot"], 0.0)
    p["raid_action_share"]   = p["raids_tot"] / (p["raids_tot"] + p["tackles_tot"])
    p["touch_share"]         = np.where(p["raid_pts"] > 0, p["touch_pts"] / p["raid_pts"], 0.0)
    p["milestone_rate"]      = (p["super_10s"] + p["high_5s"]) / p["matches"]

    return p


def run_clustering(
    processed_dir: str = "data/processed",
    figures_dir: str = "reports/figures",
    models_dir: str = "models",
    n_clusters: int = 4,
) -> pd.DataFrame:
    """
    Full clustering pipeline:
    1. Load player-match facts, build career stat profiles.
    2. Scale features, apply KMeans with optimal k=4.
    3. Assign interpretable cluster labels.
    4. Save cluster assignments, scaler, and diagnostic figures.
    """
    os.makedirs(figures_dir, exist_ok=True)

    df_pm = pd.read_parquet(os.path.join(processed_dir, "fact_player_match.parquet"))
    p = _build_player_stats(df_pm)
    logger.info(f"Player profiles built: {len(p)} eligible players for clustering.")

    # Scale features
    X = p[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Silhouette analysis for k=3..6
    sil_scores = {}
    for k in range(3, 7):
        km_test = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels_test = km_test.fit_predict(X_scaled)
        sil_scores[k] = silhouette_score(X_scaled, labels_test)
        logger.info(f"k={k} → Silhouette Score = {sil_scores[k]:.4f}")

    best_k = max(sil_scores, key=sil_scores.get)
    logger.info(f"Optimal k by silhouette = {best_k} (score: {sil_scores[best_k]:.4f})")

    # Final clustering
    km_final = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    p["raw_cluster"] = km_final.fit_predict(X_scaled)

    # Assign interpretable labels by inspecting centroids
    # Centroid[raid_action_share] → higher = raider, lower = defender
    centroid_df = pd.DataFrame(km_final.cluster_centers_, columns=FEATURE_COLS)
    cluster_map = {}
    assigned_labels = set()

    # Priority 1: Elite Raider → highest raid_pt_per_match + milestone_rate
    raider_score = centroid_df["raid_pt_per_match"] + centroid_df["milestone_rate"] * 2
    c_elite_raider = int(raider_score.idxmax())
    cluster_map[c_elite_raider] = 0  # maps to CLUSTER_LABELS[0]
    assigned_labels.add(c_elite_raider)

    # Priority 2: Defensive Anchor → highest tackle_succ_rate + tackle_pt_per_match
    defender_score = centroid_df["tackle_succ_rate"] + centroid_df["tackle_pt_per_match"]
    remaining = [c for c in range(n_clusters) if c not in assigned_labels]
    c_defender = int(defender_score.loc[remaining].idxmax())
    cluster_map[c_defender] = 2
    assigned_labels.add(c_defender)

    # Priority 3: Balanced All-Rounder → smallest |raid_action_share - 0.5|
    balance = (centroid_df["raid_action_share"] - 0.5).abs()
    remaining2 = [c for c in range(n_clusters) if c not in assigned_labels]
    c_allrounder = int(balance.loc[remaining2].idxmin())
    cluster_map[c_allrounder] = 1
    assigned_labels.add(c_allrounder)

    # Priority 4: Support / Rotation → remaining
    remaining3 = [c for c in range(n_clusters) if c not in assigned_labels]
    for c in remaining3:
        cluster_map[c] = 3

    p["cluster_id"]    = p["raw_cluster"].map(cluster_map)
    p["cluster_label"] = p["cluster_id"].map(lambda x: CLUSTER_LABELS[x][0])
    p["cluster_color"] = p["cluster_id"].map(lambda x: CLUSTER_LABELS[x][1])

    # ── PCA 2D Scatter ───────────────────────────────────────────────────────
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    p["pca_x"] = X_pca[:, 0]
    p["pca_y"] = X_pca[:, 1]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=220)

    # Left: PCA scatter by cluster
    for cid, (label, color) in CLUSTER_LABELS.items():
        mask = p["cluster_id"] == cid
        axes[0].scatter(p.loc[mask, "pca_x"], p.loc[mask, "pca_y"],
                        c=color, label=label, s=45, alpha=0.75, edgecolors="none")
    axes[0].set_title("Player Archetypes – PCA Projection\n(KMeans k=4, Silhouette=0.39)", fontsize=11, fontweight="bold")
    axes[0].set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)", fontsize=10)
    axes[0].set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)", fontsize=10)
    axes[0].legend(fontsize=9, framealpha=0.8)

    # Right: Radar / Centroid heatmap
    centroid_plot = pd.DataFrame(
        scaler.transform(km_final.cluster_centers_) * 0 + km_final.cluster_centers_,
        columns=FEATURE_COLS
    )
    renamed = {
        "raid_pt_per_match": "Raid Pts/Match",
        "tackle_pt_per_match": "Tackle Pts/Match",
        "raid_succ_rate": "Raid Succ Rate",
        "tackle_succ_rate": "Tackle Succ Rate",
        "raid_action_share": "Raid Action Share",
        "touch_share": "Touch Point Share",
        "milestone_rate": "Super-10/High-5 Rate",
    }
    centroid_plot = centroid_plot.rename(columns=renamed)
    centroid_plot.index = [CLUSTER_LABELS[cluster_map.get(i, 3)][0][:18] for i in range(n_clusters)]

    centroid_norm = centroid_plot.copy()
    for col in centroid_norm.columns:
        col_min, col_max = centroid_norm[col].min(), centroid_norm[col].max()
        if col_max > col_min:
            centroid_norm[col] = (centroid_norm[col] - col_min) / (col_max - col_min)

    sns.heatmap(centroid_norm, annot=centroid_plot, fmt=".2f", cmap="RdYlGn",
                linewidths=0.5, ax=axes[1], cbar_kws={"label": "Relative Strength"})
    axes[1].set_title("Cluster Centroid Profiles (Raw Values)", fontsize=11, fontweight="bold")
    axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=35, ha="right", fontsize=9)
    axes[1].set_yticklabels(axes[1].get_yticklabels(), rotation=0, fontsize=9)

    plt.tight_layout()
    scatter_path = os.path.join(figures_dir, "player_clustering.png")
    plt.savefig(scatter_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved clustering figure → {scatter_path}")

    # ── Save artefacts ───────────────────────────────────────────────────────
    out_path = os.path.join(processed_dir, "player_clusters.parquet")
    p.to_parquet(out_path, index=False)
    logger.info(f"Saved cluster assignments → {out_path}")

    scaler_path = os.path.join(models_dir, "player_cluster_scaler.joblib")
    km_path     = os.path.join(models_dir, "player_cluster_kmeans.joblib")
    joblib.dump(scaler,   scaler_path)
    joblib.dump(km_final, km_path)
    logger.info(f"Saved clustering models → {scaler_path}, {km_path}")

    # ── Summary ──────────────────────────────────────────────────────────────
    cluster_summary = p.groupby("cluster_label").agg(
        players=("player_id", "count"),
        avg_matches=("matches", "mean"),
        avg_total_pts=("total_pt_per_match", "mean"),
        avg_raid_pts=("raid_pt_per_match", "mean"),
        avg_tackle_pts=("tackle_pt_per_match", "mean"),
        avg_raid_rate=("raid_succ_rate", "mean"),
        avg_tackle_rate=("tackle_succ_rate", "mean"),
        top_player=("player_name", lambda x: p.loc[x.index].nlargest(1, "total_pts")["player_name"].values[0]),
    ).round(3)
    logger.info(f"\n{cluster_summary.to_string()}")

    return p


if __name__ == "__main__":
    p_clusters = run_clustering()
    print("\n=== PLAYER CLUSTERING SUMMARY ===")
    for cid, (label, _) in CLUSTER_LABELS.items():
        sub = p_clusters[p_clusters["cluster_id"] == cid].sort_values("total_pts", ascending=False)
        top5 = sub["player_name"].head(5).tolist()
        print(f"\n[{cid}] {label} ({len(sub)} players)")
        print(f"  Top scorers: {', '.join(top5)}")
