"""
src/analytics/momentum.py
--------------------------
Event-reconstructed match momentum engine for PKL Analytics.
Builds rolling score differentials, lead-change timelines,
and momentum shift detection from fact_events data.
"""

import os
import sys
import logging
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# PKL event_id type codes → scoring impact
EVENT_SCORE_MAP = {
    1: 1,   # Touch point
    2: 1,   # Bonus point
    3: 2,   # Super raid (≥3 touchpoints)
    4: 2,   # All-out inflicted on opponent (+2 revival bonus)
    5: 1,   # Tackle success
    6: 0,   # Empty raid (no score)
    7: 0,   # Unsuccessful raid (tackled)
    8: 0,   # Unsuccessful tackle
    9: 1,   # Super tackle (defender outnumbered)
    10: 0,  # Other / review
}

def build_match_momentum(
    match_id: int,
    processed_dir: str = "data/processed",
) -> Optional[pd.DataFrame]:
    """
    Reconstructs the cumulative scoring timeline for a single match.
    Uses pre-computed score_team_a / score_team_b columns from fact_events
    (which already carry running totals from the event loader).
    Returns a DataFrame with columns:
        event_seq, event_type_id, team_a_id, team_b_id,
        team_a_name, team_b_name, score_a, score_b, score_diff, lead_holder
    """
    df_ev = pd.read_parquet(os.path.join(processed_dir, "fact_events.parquet"))
    df_fm = pd.read_parquet(os.path.join(processed_dir, "fact_matches.parquet"))

    match_meta = df_fm[df_fm["match_id"] == match_id]
    if match_meta.empty:
        logger.warning(f"Match ID {match_id} not found in fact_matches.")
        return None

    match_meta = match_meta.iloc[0]
    team_a_id   = int(match_meta["team_a_id"])
    team_b_id   = int(match_meta["team_b_id"])
    team_a_name = str(match_meta["team_a_name"])
    team_b_name = str(match_meta["team_b_name"])

    ev = df_ev[df_ev["match_id"] == match_id].copy()
    if ev.empty:
        logger.warning(f"No events found for match_id={match_id}.")
        return None

    # Sort chronologically by event_row_id (synthetic sequential key)
    ev = ev.sort_values("event_row_id").reset_index(drop=True)

    # Use pre-recorded running totals directly
    df_momentum = pd.DataFrame({
        "event_seq":      range(1, len(ev) + 1),
        "event_row_id":   ev["event_row_id"].values,
        "event_type_id":  ev["event_type_id"].values,
        "team_a_id":      team_a_id,
        "team_b_id":      team_b_id,
        "team_a_name":    team_a_name,
        "team_b_name":    team_b_name,
        "score_a":        ev["score_team_a"].ffill().fillna(0).astype(int).values,
        "score_b":        ev["score_team_b"].ffill().fillna(0).astype(int).values,
    })
    df_momentum["score_diff"] = df_momentum["score_a"] - df_momentum["score_b"]
    df_momentum["lead_holder"] = df_momentum["score_diff"].apply(
        lambda d: team_a_name if d > 0 else (team_b_name if d < 0 else "Tie")
    )

    return df_momentum


def count_lead_changes(df_momentum: pd.DataFrame) -> Dict:
    """Counts lead changes and determines final possession statistics."""
    leads = df_momentum["lead_holder"].values
    changes = sum(1 for i in range(1, len(leads)) if leads[i] != leads[i-1])

    team_a_name = df_momentum["team_a_name"].iloc[0]
    team_b_name = df_momentum["team_b_name"].iloc[0]

    t_a_lead = (df_momentum["score_diff"] > 0).sum()
    t_b_lead = (df_momentum["score_diff"] < 0).sum()
    tied     = (df_momentum["score_diff"] == 0).sum()
    total    = len(df_momentum)

    return {
        "lead_changes": int(changes),
        "team_a_lead_pct": round(t_a_lead / total * 100, 1) if total else 0,
        "team_b_lead_pct": round(t_b_lead / total * 100, 1) if total else 0,
        "tied_pct": round(tied / total * 100, 1) if total else 0,
        "max_team_a_lead": int(df_momentum["score_diff"].max()),
        "max_team_b_lead": int(df_momentum["score_diff"].min()),
        "comeback": abs(int(df_momentum["score_diff"].min())) >= 5 and df_momentum["score_diff"].iloc[-1] > 0
            if df_momentum["score_diff"].iloc[-1] > 0 else
            abs(int(df_momentum["score_diff"].max())) >= 5 and df_momentum["score_diff"].iloc[-1] < 0,
    }


def plot_momentum(
    df_momentum: pd.DataFrame,
    figures_dir: str = "reports/figures",
    save: bool = True,
) -> plt.Figure:
    """Renders a publication-quality match momentum chart."""
    team_a_name = df_momentum["team_a_name"].iloc[0]
    team_b_name = df_momentum["team_b_name"].iloc[0]
    match_id    = df_momentum["event_row_id"].iloc[0]

    fig, ax = plt.subplots(figsize=(12, 5), dpi=200)

    x = df_momentum["event_seq"].values
    y = df_momentum["score_diff"].values

    # Shade regions
    ax.fill_between(x, y, 0, where=(y > 0), alpha=0.25, color="#1f77b4", label=f"{team_a_name} Leading")
    ax.fill_between(x, y, 0, where=(y < 0), alpha=0.25, color="#d62728", label=f"{team_b_name} Leading")

    ax.plot(x, y, color="#2c3e50", lw=1.8, zorder=3)
    ax.axhline(0, color="gray", linestyle="--", lw=1, alpha=0.7)

    # Annotate lead changes
    lcdata = count_lead_changes(df_momentum)
    stats_text = (
        f"Lead Changes: {lcdata['lead_changes']}  |  "
        f"{team_a_name} Led {lcdata['team_a_lead_pct']}%  |  "
        f"{team_b_name} Led {lcdata['team_b_lead_pct']}%"
    )
    ax.set_title(f"Match Momentum: {team_a_name} vs {team_b_name}\n{stats_text}",
                 fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Event Sequence (Chronological)", fontsize=10)
    ax.set_ylabel("Scoring Differential (Team A − Team B)", fontsize=10)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.legend(loc="upper left", frameon=True, fontsize=9)
    plt.tight_layout()

    if save:
        os.makedirs(figures_dir, exist_ok=True)
        path = os.path.join(figures_dir, f"momentum_match_{df_momentum['team_a_id'].iloc[0]}_{df_momentum['team_b_id'].iloc[0]}.png")
        plt.savefig(path, bbox_inches="tight")
        logger.info(f"Saved momentum chart → {path}")

    return fig


def generate_momentum_summary_stats(
    processed_dir: str = "data/processed",
    sample_n: int = 30,
    figures_dir: str = "reports/figures",
) -> pd.DataFrame:
    """
    Generates momentum summaries for a sample of official PKL matches.
    Saves aggregate figures for lead-change distribution.
    """
    df_fm = pd.read_parquet(os.path.join(processed_dir, "fact_matches.parquet"))
    official_matches = df_fm[
        (df_fm["is_official_pkl"] == True) & (df_fm["is_completed"] == True)
    ]["match_id"].sample(n=min(sample_n, len(df_fm)), random_state=42).tolist()

    summaries = []
    for mid in official_matches:
        df_mom = build_match_momentum(mid, processed_dir=processed_dir)
        if df_mom is None or df_mom.empty:
            continue
        stats = count_lead_changes(df_mom)
        final_diff = int(df_mom["score_diff"].iloc[-1])
        summaries.append({
            "match_id": mid,
            "lead_changes": stats["lead_changes"],
            "team_a_lead_pct": stats["team_a_lead_pct"],
            "team_b_lead_pct": stats["team_b_lead_pct"],
            "tied_pct": stats["tied_pct"],
            "max_lead_a": stats["max_team_a_lead"],
            "max_lead_b": stats["max_team_b_lead"],
            "comeback_victory": stats["comeback"],
            "final_diff": final_diff,
        })

    df_summary = pd.DataFrame(summaries)
    logger.info(f"Momentum stats computed for {len(df_summary)} matches.")

    # Plot lead-change distribution
    if not df_summary.empty:
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), dpi=200)

        axes[0].hist(df_summary["lead_changes"], bins=15, color="#3498db", edgecolor="white", alpha=0.85)
        axes[0].set_title("Distribution of Lead Changes per Match", fontsize=11, fontweight="bold")
        axes[0].set_xlabel("Number of Lead Changes")
        axes[0].set_ylabel("Match Count")

        axes[1].hist(df_summary["final_diff"], bins=15, color="#e74c3c", edgecolor="white", alpha=0.85)
        axes[1].axvline(0, color="black", linestyle="--", lw=1.5)
        axes[1].set_title("Distribution of Final Score Differentials\n(Team A − Team B)", fontsize=11, fontweight="bold")
        axes[1].set_xlabel("Final Margin (points)")
        axes[1].set_ylabel("Match Count")

        plt.tight_layout()
        summary_path = os.path.join(figures_dir, "momentum_summary.png")
        plt.savefig(summary_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved momentum summary figure → {summary_path}")

    return df_summary


if __name__ == "__main__":
    # Test with a known match
    df_mom = build_match_momentum(match_id=1)
    if df_mom is not None:
        stats = count_lead_changes(df_mom)
        print(f"Match 1 -> Events: {len(df_mom)}, Lead Changes: {stats['lead_changes']}")
        print(f"  {df_mom['team_a_name'].iloc[0]}: led {stats['team_a_lead_pct']}% | "
              f"{df_mom['team_b_name'].iloc[0]}: led {stats['team_b_lead_pct']}%")
        print(f"  Final Diff: {df_mom['score_diff'].iloc[-1]:+d}")
        plot_momentum(df_mom)

    print("\nGenerating momentum summary across 30 random matches...")
    df_sum = generate_momentum_summary_stats(sample_n=30)
    if not df_sum.empty:
        print(df_sum[["match_id", "lead_changes", "comeback_victory", "final_diff"]].head(10).to_string(index=False))
