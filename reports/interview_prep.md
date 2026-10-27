# PKL Analytics Platform — Resume & Interview Preparation
**Pro Kabaddi League Analytics & Intelligence Platform**

---

## Part 1 — Resume Bullets (Data Analyst Role)

```
PKL Analytics & Intelligence Platform | Python, SQL, Streamlit, Pandas, Plotly
- Engineered an end-to-end sports analytics pipeline for 7 seasons of Pro Kabaddi League data
  (603 matches, 895 players, 66,568 match events) using Python and pandas.
- Designed a normalised 6-table SQLite relational schema and wrote 22+ advanced SQL queries
  using CTEs, RANK/DENSE_RANK window functions, LAG, rolling SUMs, and conditional aggregation
  to surface win rates, raid/tackle KPIs, venue performance, and season-over-season trends.
- Conducted 6 formal hypothesis tests using SciPy (Welch's t-test, Chi-Square, one-way ANOVA,
  Kruskal-Wallis) revealing that: (1) toss winners win only 45.7% of matches (χ²=7.74, p=0.005),
  (2) all-out frequency is the strongest single predictor of victory (r=0.536), and (3) scoring
  averages changed significantly across seasons (F=6.29, p<0.001).
- Produced a 9-page interactive Streamlit dashboard with Plotly charts covering team radar profiles,
  player scouting cards, live event timelines, SQL query runner, and match-momentum replay.
- Authored a data-quality report identifying and resolving 5 schema defects (numeric IDs stored as
  player names, missing role labels, event type codes misidentified as primary keys, etc.).
```

---

## Part 2 — Resume Bullets (Data Scientist / ML Engineer Role)

```
PKL Analytics & Intelligence Platform | Python, scikit-learn, Streamlit, SQLite, pytest
- Built a leakage-free pre-match binary outcome prediction system (target: win/loss) on 603 PKL
  fixtures using strict chronological walk-forward partitioning: Train S1–5 (344), Val S6 (124),
  Holdout Test S7 (79).
- Engineered 28 pre-match features from rolling historical averages — win rate, scoring differential,
  raid/tackle success rates, head-to-head record, rest days, venue familiarity — with automated
  leakage assertions enforced by pytest.
- Trained and benchmarked 4 classifiers (DummyClassifier, Logistic Regression L2, Random Forest,
  HistGradientBoosting); selected L2 Logistic Regression (Val AUC=0.654, Val Brier=0.233).
- Applied Platt Scaling probability calibration on the validation set, improving holdout test
  accuracy from 43% → 59.5%, F1 from 0.38 → 0.71, and Brier Score from 0.280 → 0.254.
- Computed permutation feature importance (25 shuffle repeats) on the unseen Season 7 test set,
  identifying rest-day differential as the single strongest win predictor (ΔAuC +0.068).
- Profiled 272 active PKL players into 4 archetypes (Elite Raider, Balanced All-Rounder,
  Defensive Anchor, Rotation Player) using KMeans clustering on 7 career rate features
  (silhouette score=0.39); validated cluster interpretability — top Raider cluster stars:
  Pardeep Narwal, Rahul Chaudhari, Ajay Thakur.
- Built an event-reconstructed match momentum engine from 66,568 chronological events, computing
  lead changes, possession percentages, and comeback indicators for any historic fixture.
- Wrote 32 automated pytest cases across data integrity, temporal leakage, model calibration,
  inference edge cases, and clustering validation; achieved 100% pass rate.
```

---

## Part 3 — Interview Question Bank

### 3A — Data Engineering & Cleaning

**Q: What data quality issues did you find and how did you resolve them?**
> Five critical defects: (1) `player_name_of_the_match` column in DS_match.csv stored numeric player IDs instead of names — resolved by joining with DS_players.csv to map all 575 POTM awards. (2) `player_role` and `player_skill` were 100% null — resolved with empirical classification: if ≥70% of a player's career actions are raids, classify as Raider; ≥70% tackles → Defender; otherwise All-Rounder. (3) `event_id` in DS_events.csv was a 1–10 event-type code, not a unique key — added synthetic `event_row_id` (1–66,568). (4) Season 1 scraper inverted tackle points against the opposing team squad — documented in data contracts with a conditional assertion that only requires 100% parity on Seasons 2–7. (5) 81 international/exhibition matches were mixed with 603 official PKL fixtures — separated using an `is_official_pkl` boolean flag based on `series_id`.

**Q: How did you handle missing values?**
> Context-aware — distinguished between true zeros, unavailable observations, and not-applicable fields. For example: `player_role` was null for all 895 players, so I derived it empirically rather than imputing it. `bonus_pts` being 0 is a legitimate zero (player didn't earn bonus points), not missing. `home_team_id` being null means it's a neutral-venue match, which is semantically different from missing data — it becomes a feature in itself (0 for both `team_a_is_home` and `team_b_is_home`).

---

### 3B — SQL

**Q: Can you describe a complex SQL query you wrote?**
> Q14 from the suite: "Top Raiders by Season with Rank". It uses a CTE to compute `raid_success_rate = successful_raids / total_raids` per player per season, then applies `DENSE_RANK() OVER (PARTITION BY season_id ORDER BY raid_pts DESC)` to rank within each season, and filters to rank ≤ 5. The outer query joins with `dim_teams` via a subquery to get the franchise name for the match-year the stats correspond to.

**Q: What's the difference between RANK and DENSE_RANK?**
> `RANK()` skips positions after ties — if two players share rank 3, the next is rank 5. `DENSE_RANK()` never skips — the next is rank 4. In sports contexts, I used `DENSE_RANK` for "Top N per season" queries to avoid missing players due to rank gaps.

---

### 3C — Machine Learning & Leakage Prevention

**Q: What is target leakage and how did you prevent it in your feature engineering?**
> Target leakage occurs when features are computed using information that only exists *after* the outcome being predicted. In match prediction, this means including match-day statistics (points scored, raids made, all-outs) in the prediction features — the model would trivially "predict" outcomes it already knows. I prevented this by:
> 1. Building features using strictly historical records (timestamped `< match_date`).
> 2. Using rolling historical averages (all-time win%, last-5 form, cumulative raid rates) updated *only after* each match concludes.
> 3. Writing 3 explicit pytest tests that scan feature column names for leaky patterns and verify season-by-season temporal ordering.

**Q: Why did Logistic Regression outperform Random Forest and Gradient Boosting here?**
> Three reasons: (1) **Dataset size** — with only 344 training matches, tree ensembles are prone to overfitting on the 28 feature dimensions. Logistic Regression with strong L2 regularisation (C=0.08) effectively shrinks noisy coefficients. (2) **Noise ceiling** — PKL outcomes have high inherent variance (one-point matches happen 12.3% of the time), meaning the "true signal" in pre-match historical features is moderate; a simple calibrated linear model captures it without inventing spurious interactions. (3) **Calibration advantage** — Platt Scaling on the validation set is particularly well-matched to Logistic Regression's linear probability output, whereas tree probabilities require isotonic regression to fix severe distribution skew.

**Q: What does a Brier Score of 0.254 mean?**
> The Brier Score is the mean squared error between predicted probabilities and actual binary outcomes, ranging from 0 (perfect) to 1 (worst). Our champion's Brier Score of 0.254 means on average the predicted probability is √0.254 ≈ 0.50 away from the true label — in a 50/50 scenario this is expected, but our model substantially beats the naive baseline of 0.671. More importantly, the calibration diagram shows the predicted probabilities track the actual win frequencies well — when we say 70%, teams win ~70% of the time.

---

### 3D — Statistical Analysis

**Q: Walk me through one of your hypothesis tests.**
> Test 2: Does the coin toss winner have an advantage? H₀: Toss outcome and match outcome are independent. I tabulated the 2×2 contingency table — toss winners won 45.7% of their matches, toss losers won 54.3%. Running `scipy.stats.chi2_contingency` on this table gave χ²=7.742, p=0.0054. Since p<0.05, we reject H₀. Interestingly, the direction is counter-intuitive: toss *losers* win more often. This likely reflects a selection bias — weaker captains may win the toss but still lose, or the standard defensive-court choice doesn't confer an advantage in modern PKL.

---

### 3D — Player Clustering

**Q: How did you determine k=4 was the optimal number of clusters?**
> I ran the silhouette analysis from k=3 to k=6. The silhouette score measures how cohesive clusters are vs. how separated they are — closer to 1 is better. Results: k=3→0.361, k=4→0.390, k=5→0.353, k=6→0.336. k=4 achieved the highest score. I also validated interpretability: the 4 resulting clusters mapped naturally to known kabaddi roles (Elite Raider, Balanced All-Rounder, Defensive Anchor, Support/Rotation), and the top players in each cluster — Pardeep Narwal for Raider, Manjeet Chhillar for Defender — match domain knowledge from PKL commentary.

---

### 3E — Dashboard & Deployment

**Q: How would you deploy this application?**
> For portfolio purposes, Streamlit Community Cloud is the path of least resistance — push to GitHub, connect the repo, set requirements.txt, and the app auto-deploys. For production at scale (real-time match-day predictions), I would: (1) containerise with Docker, (2) deploy the inference `MatchPredictor` as a FastAPI microservice, (3) move the SQLite warehouse to PostgreSQL with read replicas, (4) schedule the feature pipeline to run post-match using a cron job or Airflow DAG, and (5) serve the Streamlit app via Streamlit Cloud or a cloud PaaS.

---

## Part 4 — 30-Second Elevator Pitch

*"I built a full-stack sports analytics and machine learning platform on seven seasons of Pro Kabaddi League data — 603 matches, 895 players, and 66,000 chronological events. The core ML system predicts which team will win before the match starts, using only historical rolling statistics — no post-match data. The champion model achieves 59.5% accuracy on the Season 7 holdout set with a calibrated Brier score of 0.254, beating the naive baseline by 80%. The project also includes a 9-page Streamlit dashboard, 22 analytical SQL queries with window functions and CTEs, six formal statistical hypothesis tests, player archetype clustering into four roles, and a play-by-play event momentum engine — all backed by 32 automated tests. It demonstrates the full data science lifecycle: data auditing, cleaning, SQL design, EDA, ML engineering, deployment, and documentation."*
