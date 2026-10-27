# PKL Analytics & Intelligence Platform

<p align="center">
  <strong>Pro Kabaddi League · Historical Performance Analysis · Player Intelligence · Match Outcome Prediction</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python" />
  <img src="https://img.shields.io/badge/Streamlit-Multipage-red?logo=streamlit" />
  <img src="https://img.shields.io/badge/scikit--learn-1.x-orange?logo=scikit-learn" />
  <img src="https://img.shields.io/badge/SQLite-Analytics-lightgrey?logo=sqlite" />
  <img src="https://img.shields.io/badge/Tests-32%20Passed-brightgreen" />
</p>

---

## Project Overview

An **end-to-end sports analytics and ML platform** built on 7 seasons of official Pro Kabaddi League data (Seasons 1–7, 2014–2019). The platform demonstrates the full data science lifecycle — from raw data ingestion and schema design, through exploratory analysis and statistical testing, to machine learning model deployment — in a publicly interactive Streamlit dashboard.

**Why PKL?** Kabaddi is a 7-player contact sport where every raid, tackle, and all-out creates a measurable event. With 602 official matches, 16,892 player-match records, and 66,568 chronological events, it provides a rich, underexplored dataset ideal for sports analytics.

---

## Architecture

```
PKL_PREDICTION/
├── Data/                        ← 684 raw match JSONs (Seasons 1–7 + Int'l)
├── DS_match.csv                 ← 684 match-level records
├── DS_team.csv                  ← 1,368 team-match records
├── DS_players.csv               ← 16,892 player-match records
├── DS_events.csv                ← 66,568 event-level records
│
├── src/
│   ├── data/
│   │   ├── load_data.py         ← CSV + JSON loaders
│   │   ├── preprocess.py        ← Cleaning & normalisation pipeline
│   │   └── validate_data.py     ← Data contract assertions
│   ├── features/
│   │   └── build_features.py    ← Leak-free chronological feature engineering
│   ├── models/
│   │   ├── train_model.py       ← Multi-model training + calibration
│   │   ├── evaluate_model.py    ← Benchmarks, ROC, Brier, permutation importance
│   │   └── predict.py          ← MatchPredictor inference engine
│   └── analytics/
│       ├── metrics.py           ← Domain KPI calculations
│       ├── insights.py          ← EDA helper functions
│       ├── player_clustering.py ← KMeans archetype profiling
│       └── momentum.py          ← Event-reconstructed match momentum
│
├── app/
│   ├── Home.py                  ← League Overview & KPI cards
│   ├── utils.py                 ← Shared cache, CSS, Plotly helpers
│   └── pages/
│       ├── 1_Team_Analytics.py
│       ├── 2_Player_Analytics.py
│       ├── 3_Match_Explorer.py
│       ├── 4_Event_Analytics.py
│       ├── 5_SQL_Insights.py
│       ├── 6_Match_Prediction.py  ← ML win probability engine
│       ├── 7_Player_Intelligence.py ← Clustering & scouting cards
│       └── 8_Match_Momentum.py    ← Event timeline & momentum swings
│
├── sql/
│   ├── schema.sql               ← Relational DDL (6 tables, FKs, indexes)
│   └── analysis_queries.sql     ← 22 analytical SQL queries
│
├── notebooks/
│   ├── 01_data_quality_audit.ipynb
│   ├── 02_exploratory_data_analysis.ipynb
│   ├── 03_statistical_analysis.ipynb
│   ├── 04_feature_engineering.ipynb
│   └── 05_model_evaluation.ipynb
│
├── data/
│   ├── raw/                     ← Original CSVs (unchanged)
│   ├── processed/               ← 9 clean Parquet tables
│   └── pkl_analytics.db         ← SQLite analytical warehouse
│
├── models/                      ← Trained joblib artifacts
├── reports/
│   ├── data_quality_report.md
│   ├── data_dictionary.md
│   ├── statistical_analysis_report.md
│   ├── sql_analysis_report.md
│   ├── model_evaluation_report.md
│   └── figures/                 ← 12 publication-grade charts
│
├── scripts/                     ← Reproducible run scripts
├── tests/                       ← 32 automated pytest cases
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/pkl-analytics-platform.git
cd pkl-analytics-platform

pip install -r requirements.txt
```

### 2. Run the Data Pipeline

```bash
# Step 1: Clean & process all data → data/processed/*.parquet
python src/data/preprocess.py

# Step 2: Load SQLite warehouse → data/pkl_analytics.db
python scripts/load_database.py

# Step 3: Build feature matrix → data/processed/model_features.parquet
python src/features/build_features.py

# Step 4: Train all models → models/*.joblib
python src/models/train_model.py

# Step 5: Evaluate models → reports/model_evaluation_report.md + figures
python src/models/evaluate_model.py

# Step 6: Cluster players → data/processed/player_clusters.parquet
python src/analytics/player_clustering.py
```

### 3. Run the Test Suite

```bash
pytest tests/ -v
# Expected: 32 passed
```

### 4. Launch the Dashboard

```bash
streamlit run app/Home.py
```

---

## Dashboard Pages

| Page | Description |
|---|---|
| 🏠 **Home** | League KPI cards, season-wise match counts, team win-rate leaderboard |
| 📊 **Team Analytics** | Radar charts, game-by-game form, tactical diagnosis (raid vs tackle ratio) |
| 🏹 **Player Analytics** | Scouting profiles, scoring methods, peer benchmark scatter plots |
| 🔍 **Match Explorer** | Scoreboard, box scores, head-to-head record, play-by-play progression |
| ⚡ **Event Analytics** | Raid outcome distributions, do-or-die conversion, 1st vs 2nd half dynamics |
| 🔬 **SQL Insights** | Interactive runner for all 22 analytical SQL queries with business context |
| 🎯 **Match Prediction** | Pre-match win probability engine with tale-of-the-tape, model diagnostics |
| 🏹 **Player Intelligence** | KMeans archetype clustering, PCA landscape, radar scouting cards |
| 📈 **Match Momentum** | Event-reconstructed score timelines, lead-change analysis, comeback detection |

---

## Machine Learning — Key Results

### Pre-Match Match Outcome Prediction

**Problem:** Binary classification — predict the winning team before the match whistle using only historical statistics (zero leakage).

**Partitioning:** Strict temporal walk-forward split:
- Train: Seasons 1–5 (344 matches)
- Validation: Season 6 (124 matches)
- **Holdout Test: Season 7 (79 matches)**

| Model | Validation AUC | Test Accuracy | Test F1 | Test Brier |
|---|---|---|---|---|
| Baseline (Majority Class) | 0.500 | 32.9% | 0.000 | 0.671 |
| Logistic Regression (L2) | **0.654** | 43.0% | 0.384 | 0.280 |
| Random Forest | 0.651 | 35.4% | 0.215 | 0.302 |
| HistGradientBoosting | 0.621 | 48.1% | 0.453 | 0.296 |
| **Calibrated LR (Champion)** | **0.654** | **59.5%** | **0.714** | **0.254** |

**Champion:** L2 Logistic Regression + Platt Scaling calibration on validation set → probability-calibrated, interpretable win forecasts.

### Top Predictive Features (Permutation Importance on Holdout)

1. **`diff_rest_days`** (+0.068): Recovery time differential — paramount in PKL's congested fixture calendar.
2. **`diff_l5_differential`** (+0.023): Recent 5-match net scoring momentum.
3. **`team_a_l5_diff`** (+0.021): Team A's own recent form trajectory.
4. **`diff_prior_avg_pts`** (+0.017): Offensive firepower baseline difference.
5. **`team_b_is_home`** (+0.013): Opponent home court advantage.

### Player Clustering

272 active players (≥10 matches) profiled into 4 archetypes via KMeans (k=4, Silhouette=0.39):

| Archetype | Players | Top Representatives |
|---|---|---|
| ⚡ Elite Raider | 17 | Pardeep Narwal, Rahul Chaudhari, Ajay Thakur |
| 🤸 Balanced All-Rounder | 150 | Rishank Devadiga, Jang Kun Lee, Jasvir Singh |
| 🛡️ Defensive Anchor | 38 | Manjeet Chhillar, Fazel Atrachali, Ravinder Pahal |
| 🔄 Rotation / Support | 67 | Vishal Mane, C. Arun, Sachin Shingade |

---

## Statistical Analysis — Key Findings

| Finding | Test Used | Result |
|---|---|---|
| Score Separation (Winner vs Loser) | Welch's t-test + Mann-Whitney | t=23.23, p<10⁻⁹⁰, Cohen's d=1.42 |
| Toss Winner ≠ Match Winner | Chi-Square | χ²=7.74, p=0.005, toss win rate=45.7% |
| Toss Choice (Court/Raid) doesn't matter | Chi-Square | χ²=0.00, p=1.00 (Fail to reject H₀) |
| Significant season-over-season score changes | One-way ANOVA | F=6.29, p<0.001, η²=0.03 |
| Raid success rates differ across franchises | One-way ANOVA | F=2.26, p=0.010 |
| All-Outs best predict victory | Point-biserial | r=0.536 (strongest single predictor) |

---

## Data Engineering Highlights

- **603 official PKL fixtures** isolated from 81 international/test matches across 17 series.
- **Zero score discrepancies** in team financial reconciliation: `score = raid_pts + tackle_pts + all_out + extras` (verified for all 1,368 team-match records).
- **Player-of-Match fix:** Raw CSV stored numeric IDs in the name column — all 575 POTM awards remapped to actual player names.
- **Player role inference:** Empirical classification (≥70% raid actions → Raider; ≥70% tackle actions → Defender) applied since raw data lacked role labels.
- **Event ID fix:** `event_id` in DS_events.csv was an event-type category code (1–10), not a primary key. Added synthetic `event_row_id` (1–66,568).

---

## Tech Stack

| Domain | Tools |
|---|---|
| **Data Processing** | Python 3.13, pandas, NumPy |
| **Database** | SQLite, 22 analytical SQL queries (CTEs, window functions, RANK/DENSE_RANK, LAG) |
| **Statistical Analysis** | SciPy (t-test, Mann-Whitney, Chi-Square, ANOVA, Kruskal-Wallis) |
| **Machine Learning** | scikit-learn (Logistic Regression, Random Forest, HistGradientBoosting, CalibratedClassifierCV) |
| **Clustering** | KMeans, PCA, StandardScaler, silhouette analysis |
| **Explainability** | Permutation Importance, probability calibration curves (Brier score) |
| **Visualisation** | Matplotlib, Seaborn, Plotly |
| **Dashboard** | Streamlit (9-page multi-app) |
| **Persistence** | Parquet, joblib, SQLite |
| **Testing** | pytest (32 cases across data quality, feature engineering, ML, inference, clustering) |

---

## Requirements

```
streamlit>=1.32.0
pandas>=2.0.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
plotly>=5.18.0
scikit-learn>=1.4.0
scipy>=1.11.0
pyarrow>=14.0.0
joblib>=1.3.0
pytest>=8.0.0
```

---

## License

This project uses publicly available Pro Kabaddi League data for educational and portfolio purposes.
