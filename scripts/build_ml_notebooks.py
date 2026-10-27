"""
scripts/build_ml_notebooks.py
-----------------------------
Generates publication-quality Jupyter notebooks for Feature Engineering (04)
and Model Evaluation & Explainability (05).
"""

import json
import os

def create_notebook(cells, output_path):
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.13.9"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"Created notebook: {output_path}")


def md_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.strip().split("\n")]}


def code_cell(code):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [line + "\n" for line in code.strip().split("\n")]}


def build_notebook_04():
    cells = [
        md_cell("""# 04. Feature Engineering & Leakage Prevention Pipeline
## PKL Analytics & Intelligence Platform
**Role:** Senior Data Scientist / ML Engineer  
**Dataset:** Pro Kabaddi League (Seasons 1–7)

---

### Objectives
1. **Target Formulation:** Frame the match outcome prediction as a canonical binary classification problem ($Y = 1$ if Team A wins, $0$ if Team B wins/ties).
2. **Leakage Prevention Contract:** Ensure all features are strictly derived from historical fixtures timestamped **before** the match start whistle.
3. **Domain Feature Construction:**
   - Pre-match rolling win percentages and point differentials.
   - Recent 5-match form indicators (momentum).
   - Raid and tackle efficiency rates.
   - Head-to-Head historical dominance.
   - Rest days and schedule fatigue.
   - Home venue familiarity.
4. **Temporal Partitioning:** Split data chronologically into:
   - **Training Set:** Seasons 1–5 (2014–2017)
   - **Validation Set:** Season 6 (2018–2019)
   - **Holdout Test Set:** Season 7 (2019)"""),

        code_cell("""import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(".."))

from src.features.build_features import build_match_features, get_feature_columns, get_train_val_test_splits"""),

        md_cell("""### 1. Build and Inspect the Chronological Feature Matrix"""),

        code_cell("""# Generate or load features from processed directory
df_feats = build_match_features(processed_dir="../data/processed")
feature_cols = get_feature_columns()

print(f"Total Matches Processed: {len(df_feats)}")
print(f"Total Engineered Columns: {df_feats.shape[1]}")
print(f"Vetted Predictive Feature Set ({len(feature_cols)} features):")
for i, col in enumerate(feature_cols, 1):
    print(f"  {i:02d}. {col}")"""),

        md_cell("""### 2. Verify Canonical Target Balance and Differential Distributions"""),

        code_cell("""# Display sample feature vectors
cols_to_preview = [
    "match_id", "match_date", "season_id", "team_a_name", "team_b_name",
    "diff_prior_win_pct", "diff_l5_differential", "diff_raid_rate", "diff_tackle_rate",
    "target_team_a_win"
]
df_feats[cols_to_preview].head(10)"""),

        md_cell("""### 3. Chronological Temporal Partitioning
We avoid random K-fold CV because random shuffling leaks future meta-strategies, tactical meta-shifts, and squad aging into past evaluations.  
We enforce a strict temporal walk-forward split:"""),

        code_cell("""train_df, val_df, test_df = get_train_val_test_splits(df_feats, exclude_ties=True)

print("=" * 60)
print(f"TRAIN SET (Seasons 1-5): {len(train_df)} matches | Target Mean: {train_df['target_team_a_win'].mean():.3f}")
print(f"VAL SET   (Season 6):    {len(val_df)} matches | Target Mean: {val_df['target_team_a_win'].mean():.3f}")
print(f"TEST SET  (Season 7):    {len(test_df)} matches | Target Mean: {test_df['target_team_a_win'].mean():.3f}")
print("=" * 60)"""),

        md_cell("""### 4. Correlation Analysis of Pre-Match Differential Features with Match Victory"""),

        code_cell("""# Compute Pearson correlation with binary outcome
diff_features = [c for c in feature_cols if c.startswith("diff_") or c.startswith("h2h_")]
corrs = train_df[diff_features + ["target_team_a_win"]].corr()["target_team_a_win"].drop("target_team_a_win").sort_values(ascending=False)

plt.figure(figsize=(10, 6), dpi=150)
sns.barplot(x=corrs.values, y=corrs.index, palette="vlag")
plt.title("Pre-Match Feature Correlation with Match Victory (Training Set: S1-S5)", fontsize=12, fontweight="bold")
plt.xlabel("Pearson Correlation Coefficient")
plt.axvline(0, color="black", linestyle="--", lw=1)
plt.tight_layout()
plt.show()""")
    ]
    create_notebook(cells, "notebooks/04_feature_engineering.ipynb")


def build_notebook_05():
    cells = [
        md_cell("""# 05. Model Training, Calibration, Evaluation & Explainability
## PKL Analytics & Intelligence Platform
**Role:** Senior Data Scientist / Machine Learning Engineer  
**Dataset:** Pro Kabaddi League (Seasons 1–7)

---

### Objectives
1. **Model Suite:** Train and compare Baseline (Dummy), Logistic Regression (L2 regularized), Random Forest, and HistGradientBoosting classifiers.
2. **Probability Calibration:** Apply Platt Scaling (Sigmoid Calibrated Classifier CV) on the validation set to produce reliable win probabilities.
3. **Comprehensive Evaluation:** Score all models on the unseen holdout test set (Season 7) across Accuracy, Balanced Accuracy, F1-Score, ROC-AUC, and Brier Score Loss.
4. **Interpretability:** Extract global feature importances via permutation importance and explain individual match upset drivers.
5. **Pre-Match Inference Demo:** Demonstrate real-time match forecasting with `MatchPredictor`."""),

        code_cell("""import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(".."))

from src.models.train_model import train_all_models
from src.models.evaluate_model import evaluate_models
from src.models.predict import MatchPredictor"""),

        md_cell("""### 1. Execute Training Pipeline and Model Selection"""),

        code_cell("""# Train all models and calibrate best candidate
train_results = train_all_models(models_dir="../models", processed_dir="../data/processed")
print("Selected Best Model Candidate:", train_results["best_model_name"])
print("Validation Performance:")
for name, sc in train_results["val_scores"].items():
    print(f"  {name:25s} | Val Acc: {sc['val_accuracy']:.3f} | Val AUC: {sc['val_roc_auc']:.3f} | Brier: {sc['val_brier']:.3f}")"""),

        md_cell("""### 2. Comprehensive Evaluation on Holdout Test Set (Season 7)"""),

        code_cell("""eval_results = evaluate_models(models_dir="../models", processed_dir="../data/processed", figures_dir="../reports/figures")

test_df_metrics = pd.DataFrame(eval_results["test_metrics"]).T
cols_display = ["accuracy", "balanced_accuracy", "f1", "roc_auc", "brier_score", "log_loss"]
test_df_metrics[cols_display].sort_values(by="roc_auc", ascending=False)"""),

        md_cell("""### 3. Diagnostic Figures: ROC Curves & Calibration Diagrams"""),

        code_cell("""from IPython.display import Image, display

print("--- ROC Curves (Holdout Test Set) ---")
display(Image(filename="../reports/figures/model_roc_curves.png"))

print("--- Probability Calibration Diagram ---")
display(Image(filename="../reports/figures/model_calibration_curves.png"))

print("--- Confusion Matrices ---")
display(Image(filename="../reports/figures/model_confusion_matrices.png"))"""),

        md_cell("""### 4. Permutation Feature Importance"""),

        code_cell("""top_feats = pd.DataFrame(eval_results["top_features"])
print("Top 10 Features by Permutation Importance:")
display(top_feats)

display(Image(filename="../reports/figures/model_feature_importance.png"))"""),

        md_cell("""### 5. Error & Upset Analysis: Why Did Underdogs Win?
Analyzing matches where the model assigned highest win probability to the losing team:"""),

        code_cell("""upsets_df = pd.DataFrame(eval_results["top_upsets"])
print("Top Season 7 Surprises / Upsets:")
display(upsets_df)"""),

        md_cell("""### 6. Interactive Pre-Match Prediction Demonstration"""),

        code_cell("""predictor = MatchPredictor(models_dir="../models", processed_dir="../data/processed")

# Predict marquee clash: Bengaluru Bulls (1) vs Dabang Delhi K.C. (2)
prediction = predictor.predict_match(team_a_id=1, team_b_id=2, as_of_date_str="2019-10-15")

print("=" * 60)
print(f"PREDICTED OUTCOME: {prediction['team_a_name']} ({prediction['team_a_prob']*100:.1f}%) vs {prediction['team_b_name']} ({prediction['team_b_prob']*100:.1f}%)")
print(f"FAVORITE: {prediction['predicted_winner']} [{prediction['confidence_tier']}]")
print("=" * 60)

print("\n--- Tale of the Tape ---")
display(pd.DataFrame(prediction['tale_of_the_tape']))

print("\n--- Head to Head Record ---")
print(prediction['h2h_summary'])""")
    ]
    create_notebook(cells, "notebooks/05_model_evaluation.ipynb")

if __name__ == "__main__":
    build_notebook_04()
    build_notebook_05()
