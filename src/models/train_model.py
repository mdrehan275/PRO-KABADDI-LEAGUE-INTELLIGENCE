"""
src/models/train_model.py
-------------------------
Training pipeline for PKL match outcome prediction models.
Fits multiple candidate classifiers using strict temporal partitioning:
  - Training: Seasons 1-5 (2014-2017)
  - Validation: Season 6 (2018-2019)
  - Holdout Test: Season 7 (2019)

Produces trained models, calibrated probability wrappers, and metadata artifacts.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import numpy as np
import joblib

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss

from src.features.build_features import build_match_features, get_feature_columns, get_train_val_test_splits

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train_all_models(
    models_dir: str = "models",
    processed_dir: str = "data/processed"
) -> Dict[str, Any]:
    """
    Trains baseline, linear, and tree-based ensemble models on the chronological training set,
    evaluates on the validation set, calibrates the best model, and persists artifacts.
    """
    os.makedirs(models_dir, exist_ok=True)
    
    # 1. Load or build feature matrix
    feat_parquet = os.path.join(processed_dir, "model_features.parquet")
    if os.path.exists(feat_parquet):
        logger.info(f"Loading features from {feat_parquet}")
        df_feats = pd.read_parquet(feat_parquet)
    else:
        logger.info("Feature parquet not found, generating features...")
        df_feats = build_match_features(processed_dir=processed_dir)

    feature_cols = get_feature_columns()
    target_col = "target_team_a_win"

    # 2. Chronological splits
    train_df, val_df, test_df = get_train_val_test_splits(df_feats, exclude_ties=True)
    
    X_train = train_df[feature_cols].copy()
    y_train = train_df[target_col].values
    
    X_val = val_df[feature_cols].copy()
    y_val = val_df[target_col].values

    X_test = test_df[feature_cols].copy()
    y_test = test_df[target_col].values

    logger.info(f"Training shapes -> X_train: {X_train.shape}, X_val: {X_val.shape}, X_test: {X_test.shape}")
    logger.info(f"Class distributions -> Train 1s: {y_train.mean():.3f}, Val 1s: {y_val.mean():.3f}, Test 1s: {y_test.mean():.3f}")

    # 3. Define candidate model architectures
    models = {
        "baseline_dummy": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=0.08, penalty="l2", solver="lbfgs", max_iter=1000, random_state=42))
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=4,
            min_samples_split=6,
            min_samples_leaf=4,
            max_features="sqrt",
            random_state=42
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=80,
            max_depth=3,
            learning_rate=0.04,
            min_samples_leaf=8,
            l2_regularization=0.5,
            random_state=42
        )
    }

    # 4. Train candidates and score on validation set
    trained_artifacts = {}
    val_scores = {}

    for name, model in models.items():
        logger.info(f"Fitting {name}...")
        model.fit(X_train, y_train)
        
        # Validation predictions
        y_val_pred = model.predict(X_val)
        y_val_prob = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else y_val_pred
        
        acc = accuracy_score(y_val, y_val_pred)
        auc = roc_auc_score(y_val, y_val_prob) if len(np.unique(y_val_prob)) > 1 else 0.50
        brier = brier_score_loss(y_val, y_val_prob)
        loss = log_loss(y_val, y_val_prob) if len(np.unique(y_val_prob)) > 1 else 1.0

        val_scores[name] = {
            "val_accuracy": float(acc),
            "val_roc_auc": float(auc),
            "val_brier": float(brier),
            "val_log_loss": float(loss)
        }
        logger.info(f"--> {name}: Val Acc = {acc:.4f}, Val AUC = {auc:.4f}, Brier = {brier:.4f}")

        # Save candidate model
        model_path = os.path.join(models_dir, f"{name}.joblib")
        joblib.dump(model, model_path)
        trained_artifacts[name] = model

    # 5. Select best model based on validation ROC-AUC / Brier score
    # We choose the best model among non-baseline candidates
    candidate_names = [k for k in models.keys() if k != "baseline_dummy"]
    best_candidate_name = max(candidate_names, key=lambda k: val_scores[k]["val_roc_auc"])
    best_base_model = trained_artifacts[best_candidate_name]
    logger.info(f"Best candidate selected: {best_candidate_name} (Val AUC: {val_scores[best_candidate_name]['val_roc_auc']:.4f})")

    # 6. Fit Probability Calibrator on Validation Set
    logger.info(f"Fitting Calibrator (Platt Scaling) on validation set for {best_candidate_name}...")
    try:
        from sklearn.frozen import FrozenEstimator
        calibrator = CalibratedClassifierCV(estimator=FrozenEstimator(best_base_model), method="sigmoid")
    except ImportError:
        calibrator = CalibratedClassifierCV(estimator=best_base_model, cv="prefit", method="sigmoid")
    calibrator.fit(X_val, y_val)

    # Save calibrated model
    calibrated_path = os.path.join(models_dir, "calibrated_best_model.joblib")
    joblib.dump(calibrator, calibrated_path)
    trained_artifacts["calibrated_best_model"] = calibrator

    # 7. Persist feature column specification and metadata
    feat_meta_path = os.path.join(models_dir, "feature_columns.json")
    with open(feat_meta_path, "w") as f:
        json.dump(feature_cols, f, indent=2)

    metadata = {
        "best_candidate": best_candidate_name,
        "feature_count": len(feature_cols),
        "feature_names": feature_cols,
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "test_samples": int(len(X_test)),
        "validation_scores": val_scores,
        "train_target_mean": float(y_train.mean()),
        "val_target_mean": float(y_val.mean()),
        "test_target_mean": float(y_test.mean())
    }
    meta_path = os.path.join(models_dir, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model training pipeline completed successfully. Artifacts saved in {models_dir}/")
    return {
        "models": trained_artifacts,
        "val_scores": val_scores,
        "best_model_name": best_candidate_name,
        "metadata": metadata
    }


if __name__ == "__main__":
    results = train_all_models()
    print("\n--- Model Training Summary ---")
    print(f"Best Candidate: {results['best_model_name']}")
    for m, sc in results['val_scores'].items():
        print(f"  {m:25s} | Acc: {sc['val_accuracy']:.3f} | AUC: {sc['val_roc_auc']:.3f} | Brier: {sc['val_brier']:.3f}")
