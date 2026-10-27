"""
src/models/evaluate_model.py
----------------------------
Comprehensive model evaluation, probability calibration assessment,
feature importance profiling, and error analysis for PKL match prediction.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, brier_score_loss, log_loss, confusion_matrix,
    roc_curve, classification_report
)
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance

from src.features.build_features import get_feature_columns, get_train_val_test_splits

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
    """Computes a full suite of classification and calibration metrics."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 and len(np.unique(y_prob)) > 1 else 0.50,
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)) if len(np.unique(y_true)) > 1 and len(np.unique(y_prob)) > 1 else 1.0
    }


def evaluate_models(
    models_dir: str = "models",
    processed_dir: str = "data/processed",
    figures_dir: str = "reports/figures"
) -> Dict[str, Any]:
    """
    Evaluates all trained candidate models on both Validation (S6) and Holdout Test (S7) sets.
    Generates diagnostic figures and returns benchmark metrics.
    """
    os.makedirs(figures_dir, exist_ok=True)
    
    # 1. Load data and features
    feat_parquet = os.path.join(processed_dir, "model_features.parquet")
    df_feats = pd.read_parquet(feat_parquet)
    feature_cols = get_feature_columns()
    target_col = "target_team_a_win"
    
    train_df, val_df, test_df = get_train_val_test_splits(df_feats, exclude_ties=True)
    
    X_train = train_df[feature_cols].copy()
    y_train = train_df[target_col].values

    X_val = val_df[feature_cols].copy()
    y_val = val_df[target_col].values

    X_test = test_df[feature_cols].copy()
    y_test = test_df[target_col].values

    # 2. Load models
    model_names = [
        "baseline_dummy",
        "logistic_regression",
        "random_forest",
        "hist_gradient_boosting",
        "calibrated_best_model"
    ]
    loaded_models = {}
    for name in model_names:
        path = os.path.join(models_dir, f"{name}.joblib")
        if os.path.exists(path):
            loaded_models[name] = joblib.load(path)
            logger.info(f"Loaded {name} from {path}")

    # 3. Evaluate across splits
    results = {"val": {}, "test": {}}
    predictions = {"val": {}, "test": {}}

    for split_name, X_split, y_split in [("val", X_val, y_val), ("test", X_test, y_test)]:
        for name, model in loaded_models.items():
            y_pred = model.predict(X_split)
            if hasattr(model, "predict_proba"):
                y_prob = model.predict_proba(X_split)[:, 1]
            else:
                y_prob = y_pred.astype(float)
            
            metrics = compute_metrics(y_split, y_pred, y_prob)
            results[split_name][name] = metrics
            predictions[split_name][name] = {"y_pred": y_pred, "y_prob": y_prob}

    # 4. Generate Visualizations
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    
    # --- Figure 1: ROC Curves (Test Set) ---
    plt.figure(figsize=(8, 6), dpi=300)
    for name, model in loaded_models.items():
        if name == "baseline_dummy":
            continue
        prob = predictions["test"][name]["y_prob"]
        fpr, tpr, _ = roc_curve(y_test, prob)
        auc_val = results["test"][name]["roc_auc"]
        label_name = name.replace("_", " ").title()
        plt.plot(fpr, tpr, lw=2.2, label=f"{label_name} (AUC = {auc_val:.3f})")
    
    plt.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Random Chance (AUC = 0.500)")
    plt.title("Holdout Test Set (Season 7) ROC Curves", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    plt.ylabel("True Positive Rate (Sensitivity)", fontsize=11)
    plt.legend(loc="lower right", frameon=True, fontsize=10)
    plt.tight_layout()
    roc_path = os.path.join(figures_dir, "model_roc_curves.png")
    plt.savefig(roc_path)
    plt.close()
    logger.info(f"Saved ROC curve to {roc_path}")

    # --- Figure 2: Calibration Curves (Reliability Diagrams on Test Set) ---
    plt.figure(figsize=(8, 6), dpi=300)
    for name in ["logistic_regression", "random_forest", "calibrated_best_model"]:
        if name in loaded_models:
            prob = predictions["test"][name]["y_prob"]
            fraction_pos, mean_pred = calibration_curve(y_test, prob, n_bins=5, strategy="uniform")
            brier = results["test"][name]["brier_score"]
            label_name = name.replace("_", " ").title()
            plt.plot(mean_pred, fraction_pos, "s-", lw=2, label=f"{label_name} (Brier = {brier:.3f})")

    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.title("Probability Calibration Diagram (Holdout Test Set)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Mean Predicted Probability (Team A Win)", fontsize=11)
    plt.ylabel("Empirical Win Fraction", fontsize=11)
    plt.legend(loc="upper left", frameon=True, fontsize=10)
    plt.tight_layout()
    calib_path = os.path.join(figures_dir, "model_calibration_curves.png")
    plt.savefig(calib_path)
    plt.close()
    logger.info(f"Saved Calibration curve to {calib_path}")

    # --- Figure 3: Confusion Matrices (Test Set) ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
    plot_models = ["logistic_regression", "random_forest", "calibrated_best_model"]
    for idx, name in enumerate(plot_models):
        if name in loaded_models:
            cm = confusion_matrix(y_test, predictions["test"][name]["y_pred"])
            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[idx],
                        xticklabels=["Team B Win", "Team A Win"],
                        yticklabels=["Team B Win", "Team A Win"])
            acc = results["test"][name]["accuracy"]
            axes[idx].set_title(f"{name.replace('_', ' ').title()}\nAccuracy: {acc*100:.1f}%", fontsize=11, fontweight="bold")
            axes[idx].set_xlabel("Predicted Label", fontsize=10)
            axes[idx].set_ylabel("True Label", fontsize=10)
    plt.tight_layout()
    cm_path = os.path.join(figures_dir, "model_confusion_matrices.png")
    plt.savefig(cm_path)
    plt.close()
    logger.info(f"Saved Confusion matrices to {cm_path}")

    # --- Figure 4: Feature Importance (Permutation Importance on Test Set) ---
    best_name = "calibrated_best_model" if "calibrated_best_model" in loaded_models else "logistic_regression"
    eval_model = loaded_models[best_name]
    logger.info(f"Computing permutation feature importance for {best_name} on Test set...")
    perm_res = permutation_importance(eval_model, X_test, y_test, n_repeats=25, random_state=42, scoring="roc_auc")
    
    feat_imp_df = pd.DataFrame({
        "feature": feature_cols,
        "importance_mean": perm_res.importances_mean,
        "importance_std": perm_res.importances_std
    }).sort_values(by="importance_mean", ascending=False)

    plt.figure(figsize=(10, 6.5), dpi=300)
    top12 = feat_imp_df.head(12).sort_values(by="importance_mean", ascending=True)
    plt.barh(top12["feature"], top12["importance_mean"], xerr=top12["importance_std"], color="#1f77b4", alpha=0.85, capsize=4)
    plt.title("Top Predictive Features (Permutation Importance on Holdout Test Set)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Decrease in ROC-AUC Score when Permuted", fontsize=11)
    plt.tight_layout()
    fi_path = os.path.join(figures_dir, "model_feature_importance.png")
    plt.savefig(fi_path)
    plt.close()
    logger.info(f"Saved Feature Importance plot to {fi_path}")

    # 5. Error Analysis on Season 7 Holdout
    test_analysis_df = test_df.copy()
    test_analysis_df["predicted_win_prob"] = predictions["test"][best_name]["y_prob"]
    test_analysis_df["predicted_win"] = predictions["test"][best_name]["y_pred"]
    test_analysis_df["is_correct"] = (test_analysis_df["predicted_win"] == test_analysis_df[target_col]).astype(int)
    test_analysis_df["prediction_error"] = np.abs(test_analysis_df[target_col] - test_analysis_df["predicted_win_prob"])

    upsets = test_analysis_df[test_analysis_df["is_correct"] == 0].sort_values(by="prediction_error", ascending=False).head(5)
    upset_records = []
    for _, row in upsets.iterrows():
        upset_records.append({
            "match_id": int(row["match_id"]),
            "match_date": str(row["match_date"]),
            "team_a": row["team_a_name"],
            "team_b": row["team_b_name"],
            "score_a": int(row["team_a_score"]),
            "score_b": int(row["team_b_score"]),
            "predicted_team_a_prob": float(row["predicted_win_prob"]),
            "actual_winner": row["team_a_name"] if row["target_team_a_win"] == 1 else row["team_b_name"]
        })

    eval_summary = {
        "validation_metrics": results["val"],
        "test_metrics": results["test"],
        "top_features": feat_imp_df.head(10).to_dict(orient="records"),
        "top_upsets": upset_records
    }

    # Save evaluation summary to JSON
    summary_path = os.path.join(models_dir, "evaluation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(eval_summary, f, indent=2)
    logger.info(f"Saved evaluation summary to {summary_path}")

    return eval_summary


if __name__ == "__main__":
    summary = evaluate_models()
    print("\n================== HOLDOUT TEST SET (SEASON 7) BENCHMARK ==================")
    print(f"{'Model':26s} | {'Acc':6s} | {'Bal Acc':8s} | {'F1':6s} | {'ROC-AUC':8s} | {'Brier':6s}")
    print("-" * 72)
    for name, m in summary["test_metrics"].items():
        print(f"{name:26s} | {m['accuracy']:.3f}  | {m['balanced_accuracy']:.3f}    | {m['f1']:.3f}  | {m['roc_auc']:.3f}    | {m['brier_score']:.3f}")
    
    print("\n--- Top 5 Predictive Features ---")
    for f in summary["top_features"][:5]:
        print(f"  {f['feature']:28s} -> Importance: {f['importance_mean']:+.4f} (±{f['importance_std']:.4f})")
