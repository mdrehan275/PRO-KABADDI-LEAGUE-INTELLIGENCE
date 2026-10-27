"""
src/features/build_features.py
------------------------------
Leak-free, chronological feature engineering pipeline for PKL match outcome prediction.
Generates pre-match rolling historical features, head-to-head records, rest days,
and venue familiarity without look-ahead target leakage.
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_match_features(processed_dir: str = "data/processed") -> pd.DataFrame:
    """
    Constructs a leak-free feature matrix where each row represents a single official match
    from the canonical perspective of Team A (team_id_A < team_id_B).
    All features are derived exclusively from historical matches strictly prior to the match timestamp.
    """
    logger.info("Loading processed data for feature engineering...")
    df_matches = pd.read_parquet(os.path.join(processed_dir, "fact_matches.parquet"))
    df_team_match = pd.read_parquet(os.path.join(processed_dir, "fact_team_match.parquet"))

    # Filter to official completed matches and sort chronologically
    df_m = df_matches[(df_matches['is_official_pkl'] == True) & (df_matches['is_completed'] == True)].copy()
    df_m['match_date_dt'] = pd.to_datetime(df_m['match_date'])
    df_m = df_m.sort_values(by=['match_date_dt', 'match_id']).reset_index(drop=True)

    df_tm = df_team_match[(df_team_match['is_official_pkl'] == True) & (df_team_match['status'] == 'Full Time')].copy()
    df_tm['match_date_dt'] = pd.to_datetime(df_tm['match_date'])
    df_tm = df_tm.sort_values(by=['match_date_dt', 'match_id']).reset_index(drop=True)

    # Build chronological match features
    features_rows = []

    # Historical lookup structures (updated chronologically)
    team_history: Dict[int, List[Dict]] = {}
    h2h_history: Dict[Tuple[int, int], List[Dict]] = {}
    venue_history: Dict[Tuple[int, int], List[Dict]] = {}

    for idx, match in df_m.iterrows():
        mid = match['match_id']
        m_date = match['match_date_dt']
        season_id = int(match['season_id'])
        t_a_id = int(match['team_a_id'])
        t_b_id = int(match['team_b_id'])
        venue_id = int(match['venue_id'])
        home_id = match['home_team_id']

        # --- EXTRACT TEAM A PRIOR HISTORY ---
        a_hist = team_history.get(t_a_id, [])
        a_n = len(a_hist)
        if a_n > 0:
            a_prior_win_pct = sum(h['is_win'] for h in a_hist) / a_n
            a_prior_avg_pts = sum(h['score'] for h in a_hist) / a_n
            a_prior_avg_conceded = sum(h['opp_score'] for h in a_hist) / a_n
            a_prior_diff = a_prior_avg_pts - a_prior_avg_conceded
            a_total_raids = sum(h['raids_total'] for h in a_hist)
            a_succ_raids = sum(h['raids_succ'] for h in a_hist)
            a_raid_rate = a_succ_raids / a_total_raids if a_total_raids > 0 else 0.38
            a_total_tkls = sum(h['tackles_total'] for h in a_hist)
            a_succ_tkls = sum(h['tackles_succ'] for h in a_hist)
            a_tackle_rate = a_succ_tkls / a_total_tkls if a_total_tkls > 0 else 0.40
            a_avg_ao = sum(h['all_outs'] for h in a_hist) / a_n

            # Last 5 matches
            a_l5 = a_hist[-5:]
            a_l5_win_pct = sum(h['is_win'] for h in a_l5) / len(a_l5)
            a_l5_avg_pts = sum(h['score'] for h in a_l5) / len(a_l5)
            a_l5_avg_conceded = sum(h['opp_score'] for h in a_l5) / len(a_l5)
            a_l5_diff = a_l5_avg_pts - a_l5_avg_conceded

            # Rest days
            last_date = a_hist[-1]['date']
            a_rest_days = min(float((m_date - last_date).days), 14.0)
        else:
            # Debut baseline defaults
            a_prior_win_pct = 0.50
            a_prior_avg_pts = 32.0
            a_prior_avg_conceded = 32.0
            a_prior_diff = 0.0
            a_raid_rate = 0.38
            a_tackle_rate = 0.40
            a_avg_ao = 1.0
            a_l5_win_pct = 0.50
            a_l5_avg_pts = 32.0
            a_l5_avg_conceded = 32.0
            a_l5_diff = 0.0
            a_rest_days = 7.0

        # --- EXTRACT TEAM B PRIOR HISTORY ---
        b_hist = team_history.get(t_b_id, [])
        b_n = len(b_hist)
        if b_n > 0:
            b_prior_win_pct = sum(h['is_win'] for h in b_hist) / b_n
            b_prior_avg_pts = sum(h['score'] for h in b_hist) / b_n
            b_prior_avg_conceded = sum(h['opp_score'] for h in b_hist) / b_n
            b_prior_diff = b_prior_avg_pts - b_prior_avg_conceded
            b_total_raids = sum(h['raids_total'] for h in b_hist)
            b_succ_raids = sum(h['raids_succ'] for h in b_hist)
            b_raid_rate = b_succ_raids / b_total_raids if b_total_raids > 0 else 0.38
            b_total_tkls = sum(h['tackles_total'] for h in b_hist)
            b_succ_tkls = sum(h['tackles_succ'] for h in b_hist)
            b_tackle_rate = b_succ_tkls / b_total_tkls if b_total_tkls > 0 else 0.40
            b_avg_ao = sum(h['all_outs'] for h in b_hist) / b_n

            # Last 5 matches
            b_l5 = b_hist[-5:]
            b_l5_win_pct = sum(h['is_win'] for h in b_l5) / len(b_l5)
            b_l5_avg_pts = sum(h['score'] for h in b_l5) / len(b_l5)
            b_l5_avg_conceded = sum(h['opp_score'] for h in b_l5) / len(b_l5)
            b_l5_diff = b_l5_avg_pts - b_l5_avg_conceded

            # Rest days
            last_date = b_hist[-1]['date']
            b_rest_days = min(float((m_date - last_date).days), 14.0)
        else:
            b_prior_win_pct = 0.50
            b_prior_avg_pts = 32.0
            b_prior_avg_conceded = 32.0
            b_prior_diff = 0.0
            b_raid_rate = 0.38
            b_tackle_rate = 0.40
            b_avg_ao = 1.0
            b_l5_win_pct = 0.50
            b_l5_avg_pts = 32.0
            b_l5_avg_conceded = 32.0
            b_l5_diff = 0.0
            b_rest_days = 7.0

        # --- HEAD-TO-HEAD PRIOR HISTORY ---
        h2h_key = (min(t_a_id, t_b_id), max(t_a_id, t_b_id))
        h2h_list = h2h_history.get(h2h_key, [])
        h2h_n = len(h2h_list)
        if h2h_n > 0:
            h2h_a_wins = sum(1 for g in h2h_list if g['winner_id'] == t_a_id)
            h2h_a_win_pct = h2h_a_wins / h2h_n
            h2h_a_avg_margin = sum(g['team_a_score'] - g['team_b_score'] for g in h2h_list) / h2h_n
        else:
            h2h_a_win_pct = 0.50
            h2h_a_avg_margin = 0.0

        # --- VENUE FAMILIARITY ---
        a_venue_hist = venue_history.get((t_a_id, venue_id), [])
        b_venue_hist = venue_history.get((t_b_id, venue_id), [])
        a_v_matches = len(a_venue_hist)
        b_v_matches = len(b_venue_hist)
        a_v_win_pct = sum(g['is_win'] for g in a_venue_hist) / a_v_matches if a_v_matches > 0 else 0.50
        b_v_win_pct = sum(g['is_win'] for g in b_venue_hist) / b_v_matches if b_v_matches > 0 else 0.50

        # Home team status
        a_is_home = int(pd.notnull(home_id) and int(home_id) == t_a_id)
        b_is_home = int(pd.notnull(home_id) and int(home_id) == t_b_id)

        # --- TARGET VARIABLES ---
        # Binary target: 1 if Team A wins, 0 if Team B wins (or tie)
        # We also create an indicator for ties
        is_tie = int(match['is_tie'])
        team_a_score = int(match['team_a_score'])
        team_b_score = int(match['team_b_score'])
        point_margin = team_a_score - team_b_score
        team_a_won = 1 if team_a_score > team_b_score else 0

        # Record feature row
        row = {
            "match_id": mid,
            "match_date": match['match_date'],
            "season_id": season_id,
            "team_a_id": t_a_id,
            "team_a_name": match['team_a_name'],
            "team_b_id": t_b_id,
            "team_b_name": match['team_b_name'],
            "venue_id": venue_id,
            
            # Target labels
            "target_team_a_win": team_a_won,
            "target_margin": point_margin,
            "is_tie": is_tie,
            "team_a_score": team_a_score,
            "team_b_score": team_b_score,
            
            # Differential Features (Team A - Team B)
            "diff_prior_win_pct": a_prior_win_pct - b_prior_win_pct,
            "diff_prior_avg_pts": a_prior_avg_pts - b_prior_avg_pts,
            "diff_prior_avg_conceded": a_prior_avg_conceded - b_prior_avg_conceded,
            "diff_prior_diff": a_prior_diff - b_prior_diff,
            "diff_raid_rate": a_raid_rate - b_raid_rate,
            "diff_tackle_rate": a_tackle_rate - b_tackle_rate,
            "diff_avg_allouts": a_avg_ao - b_avg_ao,
            
            # Recent Form (Last 5 matches)
            "diff_l5_win_pct": a_l5_win_pct - b_l5_win_pct,
            "diff_l5_avg_pts": a_l5_avg_pts - b_l5_avg_pts,
            "diff_l5_avg_conceded": a_l5_avg_conceded - b_l5_avg_conceded,
            "diff_l5_differential": a_l5_diff - b_l5_diff,
            
            # Direct Team A Pre-Match Features
            "team_a_prior_matches": a_n,
            "team_a_prior_win_pct": a_prior_win_pct,
            "team_a_prior_avg_pts": a_prior_avg_pts,
            "team_a_prior_avg_conceded": a_prior_avg_conceded,
            "team_a_prior_raid_rate": a_raid_rate,
            "team_a_prior_tackle_rate": a_tackle_rate,
            "team_a_l5_win_pct": a_l5_win_pct,
            "team_a_l5_diff": a_l5_diff,
            "team_a_rest_days": a_rest_days,
            "team_a_venue_matches": a_v_matches,
            "team_a_venue_win_pct": a_v_win_pct,
            "team_a_is_home": a_is_home,
            
            # Direct Team B Pre-Match Features
            "team_b_prior_matches": b_n,
            "team_b_prior_win_pct": b_prior_win_pct,
            "team_b_prior_avg_pts": b_prior_avg_pts,
            "team_b_prior_avg_conceded": b_prior_avg_conceded,
            "team_b_prior_raid_rate": b_raid_rate,
            "team_b_prior_tackle_rate": b_tackle_rate,
            "team_b_l5_win_pct": b_l5_win_pct,
            "team_b_l5_diff": b_l5_diff,
            "team_b_rest_days": b_rest_days,
            "team_b_venue_matches": b_v_matches,
            "team_b_venue_win_pct": b_v_win_pct,
            "team_b_is_home": b_is_home,
            
            # Head-to-Head & Rest Differentials
            "h2h_matches_count": h2h_n,
            "h2h_team_a_win_pct": h2h_a_win_pct,
            "h2h_team_a_avg_margin": h2h_a_avg_margin,
            "diff_rest_days": a_rest_days - b_rest_days
        }
        features_rows.append(row)

        # --- UPDATE CHRONOLOGICAL HISTORICAL LOOKUPS POST-MATCH ---
        # Fetch team box score stats from df_tm
        tm_sub = df_tm[df_tm['match_id'] == mid].set_index('team_id')
        if t_a_id in tm_sub.index and t_b_id in tm_sub.index:
            r_a = tm_sub.loc[t_a_id]
            r_b = tm_sub.loc[t_b_id]

            # Update team A history
            team_history.setdefault(t_a_id, []).append({
                "date": m_date,
                "is_win": 1 if r_a['result'] == 'Win' else 0,
                "score": int(r_a['score']),
                "opp_score": int(r_a['opponent_score']),
                "raids_total": int(r_a['raids_total']),
                "raids_succ": int(r_a['raids_successful']),
                "tackles_total": int(r_a['tackles_total']),
                "tackles_succ": int(r_a['tackles_successful']),
                "all_outs": int(r_a['all_outs_inflicted'])
            })

            # Update team B history
            team_history.setdefault(t_b_id, []).append({
                "date": m_date,
                "is_win": 1 if r_b['result'] == 'Win' else 0,
                "score": int(r_b['score']),
                "opp_score": int(r_b['opponent_score']),
                "raids_total": int(r_b['raids_total']),
                "raids_succ": int(r_b['raids_successful']),
                "tackles_total": int(r_b['tackles_total']),
                "tackles_succ": int(r_b['tackles_successful']),
                "all_outs": int(r_b['all_outs_inflicted'])
            })

            # Update H2H history
            h2h_history.setdefault(h2h_key, []).append({
                "match_id": mid,
                "winner_id": match['winner_team_id'],
                "team_a_score": team_a_score,
                "team_b_score": team_b_score
            })

            # Update Venue history
            venue_history.setdefault((t_a_id, venue_id), []).append({"is_win": 1 if r_a['result'] == 'Win' else 0})
            venue_history.setdefault((t_b_id, venue_id), []).append({"is_win": 1 if r_b['result'] == 'Win' else 0})

    df_features = pd.DataFrame(features_rows)
    logger.info(f"Engineered {df_features.shape[1]} features across {len(df_features)} official matches.")
    
    out_parquet = os.path.join(processed_dir, "model_features.parquet")
    out_csv = os.path.join(processed_dir, "model_features.csv")
    df_features.to_parquet(out_parquet, index=False)
    df_features.to_csv(out_csv, index=False)
    logger.info(f"Saved feature dataset to {out_parquet} and {out_csv}")
    
    return df_features


def get_feature_columns() -> List[str]:
    """Returns the vetted list of leak-free predictive pre-match feature column names."""
    return [
        "diff_prior_win_pct",
        "diff_prior_avg_pts",
        "diff_prior_avg_conceded",
        "diff_prior_diff",
        "diff_raid_rate",
        "diff_tackle_rate",
        "diff_avg_allouts",
        "diff_l5_win_pct",
        "diff_l5_avg_pts",
        "diff_l5_avg_conceded",
        "diff_l5_differential",
        "team_a_prior_win_pct",
        "team_b_prior_win_pct",
        "team_a_prior_avg_pts",
        "team_b_prior_avg_pts",
        "team_a_prior_raid_rate",
        "team_b_prior_raid_rate",
        "team_a_prior_tackle_rate",
        "team_b_prior_tackle_rate",
        "team_a_l5_win_pct",
        "team_b_l5_win_pct",
        "team_a_l5_diff",
        "team_b_l5_diff",
        "h2h_team_a_win_pct",
        "h2h_team_a_avg_margin",
        "diff_rest_days",
        "team_a_is_home",
        "team_b_is_home"
    ]


def get_train_val_test_splits(
    df_features: pd.DataFrame,
    exclude_ties: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Chronological temporal partitioning:
      - Training Set:   Seasons 1 through 5 (2014 - 2017)
      - Validation Set: Season 6 (2018 - 2019)
      - Test Set:       Season 7 (2019)
    """
    df = df_features.copy()
    if exclude_ties:
        # Evaluate primary binary classifier on decided matches
        df = df[df['is_tie'] == 0].copy()

    train_df = df[df['season_id'] <= 5].copy()
    val_df = df[df['season_id'] == 6].copy()
    test_df = df[df['season_id'] == 7].copy()

    logger.info(f"Split sizes: Train={len(train_df)} (S1-5), Val={len(val_df)} (S6), Test={len(test_df)} (S7)")
    return train_df, val_df, test_df


if __name__ == "__main__":
    df_feats = build_match_features()
    feature_cols = get_feature_columns()
    print("\n--- Feature Engineering Summary ---")
    print(f"Total Rows: {len(df_feats)}")
    print(f"Total Columns: {df_feats.shape[1]}")
    print(f"Predictive Features ({len(feature_cols)}):", feature_cols[:8], "...")
    
    tr, va, te = get_train_val_test_splits(df_feats, exclude_ties=True)
    print(f"Decided Matches Split -> Train: {len(tr)}, Val: {len(va)}, Test: {len(te)}")
    print(f"Target Balance Train: {tr['target_team_a_win'].mean():.3f}")
    print(f"Target Balance Val:   {va['target_team_a_win'].mean():.3f}")
    print(f"Target Balance Test:  {te['target_team_a_win'].mean():.3f}")
