"""
src/models/predict.py
---------------------
Real-time, leak-free pre-match outcome prediction engine for PKL fixtures.
Dynamically constructs pre-match features up to the fixture timestamp,
runs inference using the calibrated champion classifier, and outputs calibrated
win probabilities that strictly sum to 100%.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
import pandas as pd
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class MatchPredictor:
    """
    Inference class for Pro Kabaddi League match outcome forecasting.
    """
    def __init__(self, models_dir: str = "models", processed_dir: str = "data/processed"):
        self.models_dir = models_dir
        self.processed_dir = processed_dir
        
        # Load model and metadata
        meta_path = os.path.join(models_dir, "model_metadata.json")
        with open(meta_path, "r") as f:
            self.metadata = json.load(f)
            
        feat_path = os.path.join(models_dir, "feature_columns.json")
        with open(feat_path, "r") as f:
            self.feature_columns = json.load(f)

        model_file = os.path.join(models_dir, "calibrated_best_model.joblib")
        if not os.path.exists(model_file):
            model_file = os.path.join(models_dir, f"{self.metadata['best_candidate']}.joblib")
            
        self.model = joblib.load(model_file)
        logger.info(f"Loaded predictor model from {model_file}")

        # Load reference dimensional & historical data
        self.df_teams = pd.read_parquet(os.path.join(processed_dir, "dim_teams.parquet")).set_index("team_id")
        self.df_matches = pd.read_parquet(os.path.join(processed_dir, "fact_matches.parquet"))
        self.df_team_match = pd.read_parquet(os.path.join(processed_dir, "fact_team_match.parquet"))
        
        # Ensure datetimes are parsed
        self.df_matches["match_date_dt"] = pd.to_datetime(self.df_matches["match_date"])
        self.df_team_match["match_date_dt"] = pd.to_datetime(self.df_team_match["match_date"])

    def get_team_name(self, team_id: int) -> str:
        """Returns standard team name for a team_id."""
        if team_id in self.df_teams.index:
            return str(self.df_teams.loc[team_id, "team_name"])
        return f"Team {team_id}"

    def compute_pre_match_profile(self, team_id: int, as_of_date: pd.Timestamp) -> Dict[str, Any]:
        """Calculates team performance metrics strictly prior to as_of_date."""
        hist = self.df_team_match[
            (self.df_team_match["team_id"] == team_id) &
            (self.df_team_match["is_official_pkl"] == True) &
            (self.df_team_match["status"] == "Full Time") &
            (self.df_team_match["match_date_dt"] < as_of_date)
        ].sort_values(by="match_date_dt")

        n = len(hist)
        if n == 0:
            return {
                "matches": 0,
                "win_pct": 0.50,
                "avg_pts": 32.0,
                "avg_conceded": 32.0,
                "diff": 0.0,
                "raid_rate": 0.38,
                "tackle_rate": 0.40,
                "avg_ao": 1.0,
                "l5_win_pct": 0.50,
                "l5_avg_pts": 32.0,
                "l5_avg_conceded": 32.0,
                "l5_diff": 0.0,
                "rest_days": 7.0
            }

        wins = (hist["result"] == "Win").sum()
        win_pct = wins / n
        avg_pts = hist["score"].mean()
        avg_conceded = hist["opponent_score"].mean()
        diff = avg_pts - avg_conceded

        tot_raids = hist["raids_total"].sum()
        succ_raids = hist["raids_successful"].sum()
        raid_rate = succ_raids / tot_raids if tot_raids > 0 else 0.38

        tot_tkls = hist["tackles_total"].sum()
        succ_tkls = hist["tackles_successful"].sum()
        tackle_rate = succ_tkls / tot_tkls if tot_tkls > 0 else 0.40

        avg_ao = hist["all_outs_inflicted"].mean()

        l5 = hist.tail(5)
        l5_win_pct = (l5["result"] == "Win").sum() / len(l5)
        l5_avg_pts = l5["score"].mean()
        l5_avg_conceded = l5["opponent_score"].mean()
        l5_diff = l5_avg_pts - l5_avg_conceded

        last_date = hist["match_date_dt"].iloc[-1]
        rest_days = min(float((as_of_date - last_date).days), 14.0)

        return {
            "matches": n,
            "win_pct": float(win_pct),
            "avg_pts": float(avg_pts),
            "avg_conceded": float(avg_conceded),
            "diff": float(diff),
            "raid_rate": float(raid_rate),
            "tackle_rate": float(tackle_rate),
            "avg_ao": float(avg_ao),
            "l5_win_pct": float(l5_win_pct),
            "l5_avg_pts": float(l5_avg_pts),
            "l5_avg_conceded": float(l5_avg_conceded),
            "l5_diff": float(l5_diff),
            "rest_days": float(rest_days)
        }

    def compute_h2h_profile(self, team_a_id: int, team_b_id: int, as_of_date: pd.Timestamp) -> Dict[str, Any]:
        """Calculates head-to-head metrics between team A and team B strictly prior to as_of_date."""
        m_h2h = self.df_matches[
            (self.df_matches["is_official_pkl"] == True) &
            (self.df_matches["is_completed"] == True) &
            (self.df_matches["match_date_dt"] < as_of_date) &
            (
                ((self.df_matches["team_a_id"] == team_a_id) & (self.df_matches["team_b_id"] == team_b_id)) |
                ((self.df_matches["team_a_id"] == team_b_id) & (self.df_matches["team_b_id"] == team_a_id))
            )
        ]
        n = len(m_h2h)
        if n == 0:
            return {"matches": 0, "a_wins": 0, "b_wins": 0, "ties": 0, "a_win_pct": 0.50, "a_avg_margin": 0.0}

        a_wins = (m_h2h["winner_team_id"] == team_a_id).sum()
        b_wins = (m_h2h["winner_team_id"] == team_b_id).sum()
        ties = (m_h2h["is_tie"] == 1).sum()
        a_win_pct = a_wins / n

        margins = []
        for _, row in m_h2h.iterrows():
            if row["team_a_id"] == team_a_id:
                margins.append(row["team_a_score"] - row["team_b_score"])
            else:
                margins.append(row["team_b_score"] - row["team_a_score"])

        return {
            "matches": n,
            "a_wins": int(a_wins),
            "b_wins": int(b_wins),
            "ties": int(ties),
            "a_win_pct": float(a_win_pct),
            "a_avg_margin": float(np.mean(margins))
        }

    def predict_match(
        self,
        team_a_id: int,
        team_b_id: int,
        as_of_date_str: Optional[str] = None,
        venue_id: Optional[int] = None,
        home_team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates calibrated win probabilities for Team A vs Team B.
        Probabilities strictly sum to 100%.
        """
        if team_a_id == team_b_id:
            raise ValueError("Team A and Team B must be distinct teams.")

        # Determine reference date
        if as_of_date_str:
            as_of_date = pd.to_datetime(as_of_date_str)
        else:
            # Future fixture: use all historical matches
            as_of_date = pd.Timestamp.now() + pd.Timedelta(days=1)

        # Standardize canonical representation: canonical team 1 has lower ID
        c_t1 = min(team_a_id, team_b_id)
        c_t2 = max(team_a_id, team_b_id)

        p1 = self.compute_pre_match_profile(c_t1, as_of_date)
        p2 = self.compute_pre_match_profile(c_t2, as_of_date)
        h2h_c1 = self.compute_h2h_profile(c_t1, c_t2, as_of_date)

        c1_is_home = 1 if home_team_id and home_team_id == c_t1 else 0
        c2_is_home = 1 if home_team_id and home_team_id == c_t2 else 0

        # Construct feature dictionary in exact feature column order
        feat_dict = {
            "diff_prior_win_pct": p1["win_pct"] - p2["win_pct"],
            "diff_prior_avg_pts": p1["avg_pts"] - p2["avg_pts"],
            "diff_prior_avg_conceded": p1["avg_conceded"] - p2["avg_conceded"],
            "diff_prior_diff": p1["diff"] - p2["diff"],
            "diff_raid_rate": p1["raid_rate"] - p2["raid_rate"],
            "diff_tackle_rate": p1["tackle_rate"] - p2["tackle_rate"],
            "diff_avg_allouts": p1["avg_ao"] - p2["avg_ao"],
            "diff_l5_win_pct": p1["l5_win_pct"] - p2["l5_win_pct"],
            "diff_l5_avg_pts": p1["l5_avg_pts"] - p2["l5_avg_pts"],
            "diff_l5_avg_conceded": p1["l5_avg_conceded"] - p2["l5_avg_conceded"],
            "diff_l5_differential": p1["l5_diff"] - p2["l5_diff"],
            "team_a_prior_win_pct": p1["win_pct"],
            "team_b_prior_win_pct": p2["win_pct"],
            "team_a_prior_avg_pts": p1["avg_pts"],
            "team_b_prior_avg_pts": p2["avg_pts"],
            "team_a_prior_raid_rate": p1["raid_rate"],
            "team_b_prior_raid_rate": p2["raid_rate"],
            "team_a_prior_tackle_rate": p1["tackle_rate"],
            "team_b_prior_tackle_rate": p2["tackle_rate"],
            "team_a_l5_win_pct": p1["l5_win_pct"],
            "team_b_l5_win_pct": p2["l5_win_pct"],
            "team_a_l5_diff": p1["l5_diff"],
            "team_b_l5_diff": p2["l5_diff"],
            "h2h_team_a_win_pct": h2h_c1["a_win_pct"],
            "h2h_team_a_avg_margin": h2h_c1["a_avg_margin"],
            "diff_rest_days": p1["rest_days"] - p2["rest_days"],
            "team_a_is_home": c1_is_home,
            "team_b_is_home": c2_is_home
        }

        # Vectorize
        X_infer = pd.DataFrame([feat_dict])[self.feature_columns]

        # Model predict
        prob_c1 = float(self.model.predict_proba(X_infer)[0, 1])
        prob_c2 = 1.0 - prob_c1

        # Map back to requested team_a and team_b order
        if team_a_id == c_t1:
            prob_a = prob_c1
            prob_b = prob_c2
        else:
            prob_a = prob_c2
            prob_b = prob_c1

        # Clip slightly to avoid extreme uncalibrated 0 or 1 edge cases
        prob_a = float(np.clip(prob_a, 0.05, 0.95))
        prob_b = 1.0 - prob_a

        name_a = self.get_team_name(team_a_id)
        name_b = self.get_team_name(team_b_id)

        # Confidence categorization
        prob_diff = abs(prob_a - prob_b)
        if prob_diff < 0.10:
            confidence = "Toss-Up / Competitive Deadlock"
        elif prob_diff < 0.25:
            confidence = "Moderate Advantage"
        else:
            confidence = "High Probability Favorite"

        pred_winner = name_a if prob_a >= prob_b else name_b

        # Head to head stats from perspective of requested team_a
        h2h_stats = self.compute_h2h_profile(team_a_id, team_b_id, as_of_date)
        profile_a = self.compute_pre_match_profile(team_a_id, as_of_date)
        profile_b = self.compute_pre_match_profile(team_b_id, as_of_date)

        return {
            "team_a_id": team_a_id,
            "team_a_name": name_a,
            "team_a_prob": prob_a,
            "team_b_id": team_b_id,
            "team_b_name": name_b,
            "team_b_prob": prob_b,
            "predicted_winner": pred_winner,
            "confidence_tier": confidence,
            "tale_of_the_tape": {
                "metric": [
                    "Historical Win Rate",
                    "Recent Form (Last 5 Matches)",
                    "Average Points Scored",
                    "Average Points Conceded",
                    "Raid Success Rate",
                    "Tackle Success Rate",
                    "Average All-Outs Inflicted",
                    "Rest Days Before Match"
                ],
                name_a: [
                    f"{profile_a['win_pct']*100:.1f}% ({profile_a['matches']} matches)",
                    f"{profile_a['l5_win_pct']*100:.1f}% (Net: {profile_a['l5_diff']:+.1f})",
                    f"{profile_a['avg_pts']:.1f}",
                    f"{profile_a['avg_conceded']:.1f}",
                    f"{profile_a['raid_rate']*100:.1f}%",
                    f"{profile_a['tackle_rate']*100:.1f}%",
                    f"{profile_a['avg_ao']:.2f}",
                    f"{profile_a['rest_days']:.0f} days"
                ],
                name_b: [
                    f"{profile_b['win_pct']*100:.1f}% ({profile_b['matches']} matches)",
                    f"{profile_b['l5_win_pct']*100:.1f}% (Net: {profile_b['l5_diff']:+.1f})",
                    f"{profile_b['avg_pts']:.1f}",
                    f"{profile_b['avg_conceded']:.1f}",
                    f"{profile_b['raid_rate']*100:.1f}%",
                    f"{profile_b['tackle_rate']*100:.1f}%",
                    f"{profile_b['avg_ao']:.2f}",
                    f"{profile_b['rest_days']:.0f} days"
                ]
            },
            "h2h_summary": {
                "total_encounters": h2h_stats["matches"],
                f"{name_a}_wins": h2h_stats["a_wins"],
                f"{name_b}_wins": h2h_stats["b_wins"],
                "ties": h2h_stats["ties"],
                "avg_margin": f"{h2h_stats['a_avg_margin']:+.1f} pts"
            }
        }


if __name__ == "__main__":
    predictor = MatchPredictor()
    # Test sample fixture: Patna Pirates (3) vs U Mumba (5)
    preview = predictor.predict_match(team_a_id=3, team_b_id=5, as_of_date_str="2019-10-01")
    print(f"\n================ PRE-MATCH PREDICTION ================")
    print(f"{preview['team_a_name']} ({preview['team_a_prob']*100:.1f}%) vs {preview['team_b_name']} ({preview['team_b_prob']*100:.1f}%)")
    print(f"Predicted Winner: {preview['predicted_winner']} [{preview['confidence_tier']}]")
    print("\n--- Tale of the Tape ---")
    tape_df = pd.DataFrame(preview['tale_of_the_tape'])
    print(tape_df.to_string(index=False))
    print("\n--- Head to Head Record ---")
    print(preview['h2h_summary'])
