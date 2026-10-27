"""
tests/test_models.py
--------------------
Automated validation tests for feature engineering, model training,
probability calibration, and inference pipeline integrity.
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.build_features import get_feature_columns, get_train_val_test_splits


PROCESSED_DIR = "data/processed"
MODELS_DIR    = "models"


# ─── Feature Engineering Tests ────────────────────────────────────────────────

class TestFeatureEngineering:

    @pytest.fixture(scope="class")
    def df_feats(self):
        parquet_path = os.path.join(PROCESSED_DIR, "model_features.parquet")
        assert os.path.exists(parquet_path), "model_features.parquet must exist. Run build_features.py first."
        return pd.read_parquet(parquet_path)

    def test_feature_matrix_non_empty(self, df_feats):
        assert len(df_feats) > 500, f"Expected >500 rows, got {len(df_feats)}"

    def test_all_feature_columns_present(self, df_feats):
        feat_cols = get_feature_columns()
        missing = [c for c in feat_cols if c not in df_feats.columns]
        assert len(missing) == 0, f"Missing feature columns: {missing}"

    def test_no_target_leakage_columns(self, df_feats):
        """Score columns must be in targets only, not in predictive features."""
        feat_cols = get_feature_columns()
        leaky_patterns = ["score", "points_scored", "raid_pts", "tackle_pts", "all_outs_inflicted"]
        for col in feat_cols:
            for pattern in leaky_patterns:
                assert pattern not in col.lower(), (
                    f"Potential leakage: feature '{col}' contains '{pattern}'. "
                    f"Only rolling/pre-match averages should appear in feature set."
                )

    def test_temporal_split_no_overlap(self, df_feats):
        """Train/Val/Test sets must use non-overlapping season partitions."""
        train, val, test = get_train_val_test_splits(df_feats)
        assert len(train) > 0, "Training set is empty."
        assert len(val) > 0,   "Validation set is empty."
        assert len(test) > 0,  "Test set is empty."
        assert set(train["season_id"]).isdisjoint(set(test["season_id"])), \
            "Training and test seasons overlap — temporal leakage detected!"
        assert set(val["season_id"]).isdisjoint(set(test["season_id"])), \
            "Validation and test seasons overlap."

    def test_train_max_season_less_than_test_min(self, df_feats):
        """All training seasons must be strictly earlier than test seasons."""
        train, val, test = get_train_val_test_splits(df_feats)
        assert train["season_id"].max() < test["season_id"].min(), \
            f"Training max season ({train['season_id'].max()}) >= Test min season ({test['season_id'].min()}) — leakage!"

    def test_feature_values_bounded(self, df_feats):
        """Win percentage features must lie in [0, 1]."""
        feat_cols = get_feature_columns()
        win_pct_cols = [c for c in feat_cols if "win_pct" in c]
        for col in win_pct_cols:
            col_vals = df_feats[col]
            if col.startswith("diff_"):
                assert col_vals.between(-1, 1).all(), f"Differential win pct {col} out of [-1,1] range."
            else:
                assert col_vals.between(0, 1).all(), f"Win pct column {col} out of [0,1] range."

    def test_no_nan_in_features(self, df_feats):
        """Feature matrix must have no NaN values."""
        feat_cols = get_feature_columns()
        nan_cols = [c for c in feat_cols if df_feats[c].isna().any()]
        assert len(nan_cols) == 0, f"NaN values in feature columns: {nan_cols}"

    def test_no_inf_in_features(self, df_feats):
        """Feature matrix must have no infinite values."""
        feat_cols = get_feature_columns()
        inf_cols = [c for c in feat_cols if np.isinf(df_feats[c]).any()]
        assert len(inf_cols) == 0, f"Infinite values in feature columns: {inf_cols}"

    def test_target_binary(self, df_feats):
        """Target must be strictly binary {0, 1}."""
        vals = df_feats["target_team_a_win"].unique()
        assert set(vals).issubset({0, 1}), f"Target has non-binary values: {vals}"

    def test_rest_days_capped(self, df_feats):
        """Rest days must be capped at 14 per design."""
        for col in ["team_a_rest_days", "team_b_rest_days"]:
            if col in df_feats.columns:
                assert df_feats[col].max() <= 14.0, f"{col} exceeds cap of 14: max={df_feats[col].max()}"


# ─── Saved Model Tests ─────────────────────────────────────────────────────────

class TestSavedModels:

    REQUIRED_MODELS = [
        "baseline_dummy.joblib",
        "logistic_regression.joblib",
        "random_forest.joblib",
        "hist_gradient_boosting.joblib",
        "calibrated_best_model.joblib",
        "feature_columns.json",
        "model_metadata.json",
        "evaluation_summary.json",
    ]

    def test_all_model_files_exist(self):
        for fname in self.REQUIRED_MODELS:
            path = os.path.join(MODELS_DIR, fname)
            assert os.path.exists(path), f"Missing model artifact: {path}"

    def test_feature_columns_consistent(self):
        with open(os.path.join(MODELS_DIR, "feature_columns.json")) as f:
            saved_cols = json.load(f)
        expected_cols = get_feature_columns()
        assert saved_cols == expected_cols, "Saved feature columns don't match get_feature_columns()!"

    def test_best_candidate_is_non_dummy(self):
        with open(os.path.join(MODELS_DIR, "model_metadata.json")) as f:
            meta = json.load(f)
        assert meta["best_candidate"] != "baseline_dummy", \
            "Best candidate should not be the baseline dummy."

    def test_validation_auc_beats_random(self):
        with open(os.path.join(MODELS_DIR, "model_metadata.json")) as f:
            meta = json.load(f)
        best = meta["best_candidate"]
        best_auc = meta["validation_scores"][best]["val_roc_auc"]
        assert best_auc > 0.55, (
            f"Best model ({best}) val AUC ({best_auc:.3f}) must exceed 0.55 to show signal beyond random."
        )

    def test_calibrated_model_probability_bounds(self):
        """Calibrated model must produce probabilities strictly in (0, 1)."""
        df_feats = pd.read_parquet(os.path.join(PROCESSED_DIR, "model_features.parquet"))
        feat_cols = get_feature_columns()
        _, val_df, _ = get_train_val_test_splits(df_feats)
        X_val = val_df[feat_cols].head(30)

        model = joblib.load(os.path.join(MODELS_DIR, "calibrated_best_model.joblib"))
        probs = model.predict_proba(X_val)[:, 1]

        assert (probs >= 0.0).all() and (probs <= 1.0).all(), \
            "Calibrated model probabilities out of [0, 1] range."

    def test_complementary_probabilities(self):
        """Both class probabilities must sum to 1.0 for every prediction."""
        df_feats = pd.read_parquet(os.path.join(PROCESSED_DIR, "model_features.parquet"))
        feat_cols = get_feature_columns()
        _, _, test_df = get_train_val_test_splits(df_feats)
        X_test = test_df[feat_cols].head(20)

        model = joblib.load(os.path.join(MODELS_DIR, "calibrated_best_model.joblib"))
        probs = model.predict_proba(X_test)
        sums = probs.sum(axis=1)
        assert np.allclose(sums, 1.0, atol=1e-6), \
            f"Class probabilities don't sum to 1.0: min={sums.min():.6f}, max={sums.max():.6f}"


# ─── Inference Engine Tests ────────────────────────────────────────────────────

class TestMatchPredictor:

    @pytest.fixture(scope="class")
    def predictor(self):
        from src.models.predict import MatchPredictor
        return MatchPredictor()

    def test_predict_returns_required_keys(self, predictor):
        result = predictor.predict_match(team_a_id=1, team_b_id=2, as_of_date_str="2019-01-01")
        required = ["team_a_prob", "team_b_prob", "predicted_winner",
                    "confidence_tier", "tale_of_the_tape", "h2h_summary"]
        for key in required:
            assert key in result, f"Missing key '{key}' in prediction output."

    def test_probabilities_sum_to_one(self, predictor):
        result = predictor.predict_match(team_a_id=1, team_b_id=6, as_of_date_str="2019-06-01")
        total = result["team_a_prob"] + result["team_b_prob"]
        assert abs(total - 1.0) < 1e-6, f"Probabilities don't sum to 1.0: {total}"

    def test_probabilities_in_valid_range(self, predictor):
        result = predictor.predict_match(team_a_id=3, team_b_id=7, as_of_date_str="2018-06-01")
        assert 0.05 <= result["team_a_prob"] <= 0.95, "team_a_prob out of [0.05, 0.95] clip range."
        assert 0.05 <= result["team_b_prob"] <= 0.95, "team_b_prob out of [0.05, 0.95] clip range."

    def test_different_team_order_complements(self, predictor):
        """Swapping team A and team B must produce complementary probabilities."""
        r1 = predictor.predict_match(team_a_id=1, team_b_id=2, as_of_date_str="2019-01-01")
        r2 = predictor.predict_match(team_a_id=2, team_b_id=1, as_of_date_str="2019-01-01")
        # r1 team_a_prob + r2 team_a_prob should ≈ 1.0
        assert abs(r1["team_a_prob"] - r2["team_b_prob"]) < 1e-4, \
            "Flipping team order did not produce complementary probabilities."

    def test_same_team_raises_error(self, predictor):
        with pytest.raises(ValueError, match="distinct"):
            predictor.predict_match(team_a_id=1, team_b_id=1)

    def test_confidence_tier_populated(self, predictor):
        result = predictor.predict_match(team_a_id=5, team_b_id=6, as_of_date_str="2019-08-01")
        assert result["confidence_tier"] in [
            "Toss-Up / Competitive Deadlock",
            "Moderate Advantage",
            "High Probability Favorite",
        ], f"Unknown confidence_tier: {result['confidence_tier']}"


# ─── Clustering Tests ─────────────────────────────────────────────────────────

class TestPlayerClustering:

    @pytest.fixture(scope="class")
    def df_clusters(self):
        path = os.path.join(PROCESSED_DIR, "player_clusters.parquet")
        assert os.path.exists(path), "player_clusters.parquet missing. Run player_clustering.py first."
        return pd.read_parquet(path)

    def test_cluster_ids_in_range(self, df_clusters):
        assert df_clusters["cluster_id"].between(0, 3).all(), "Cluster IDs out of [0,3] range."

    def test_all_four_archetypes_present(self, df_clusters):
        expected = {0, 1, 2, 3}
        found = set(df_clusters["cluster_id"].unique())
        assert found == expected, f"Missing archetypes: {expected - found}"

    def test_minimum_cluster_size(self, df_clusters):
        for c_id in range(4):
            cnt = (df_clusters["cluster_id"] == c_id).sum()
            assert cnt >= 10, f"Cluster {c_id} has only {cnt} players — too sparse."

    def test_raid_specialists_have_high_raid_rate(self, df_clusters):
        """Elite Raiders (cluster_id=0) must have higher avg raid success than Defenders (cluster_id=2)."""
        raider_rate  = df_clusters[df_clusters["cluster_id"] == 0]["raid_succ_rate"].mean()
        defender_rate = df_clusters[df_clusters["cluster_id"] == 2]["raid_succ_rate"].mean()
        assert raider_rate > defender_rate, (
            f"Cluster 0 (Raiders) avg raid_succ_rate ({raider_rate:.3f}) should exceed "
            f"Cluster 2 (Defenders) ({defender_rate:.3f})."
        )
