"""
scripts/generate_eda_visualizations.py
--------------------------------------
Generates publication-quality charts and plots for the PKL Exploratory Data Analysis
and Statistical Analysis Report.
Saves figure files in `reports/figures/`.
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set consistent styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

OUTPUT_DIR = "reports/figures"
PROCESSED_DIR = "data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load data
df_matches = pd.read_parquet(os.path.join(PROCESSED_DIR, "fact_matches.parquet"))
df_team_match = pd.read_parquet(os.path.join(PROCESSED_DIR, "fact_team_match.parquet"))
df_player_match = pd.read_parquet(os.path.join(PROCESSED_DIR, "fact_player_match.parquet"))
df_events = pd.read_parquet(os.path.join(PROCESSED_DIR, "fact_events.parquet"))

df_m_official = df_matches[(df_matches['is_official_pkl'] == True) & (df_matches['is_completed'] == True)].copy()
df_tm_official = df_team_match[(df_team_match['is_official_pkl'] == True) & (df_team_match['status'] == 'Full Time')].copy()

# -------------------------------------------------------------
# Figure 1: Scoring Distributions across PKL Seasons
# -------------------------------------------------------------
print("Generating Fig 1: Scoring by Season...")
plt.figure(figsize=(10, 6))
palette = sns.color_palette("mako", n_colors=7)
ax = sns.boxplot(
    data=df_tm_official,
    x='season_id',
    y='score',
    palette=palette,
    boxprops=dict(alpha=0.8),
    showmeans=True,
    meanprops={"marker": "o", "markerfacecolor": "red", "markeredgecolor": "black", "markersize": "7"}
)
sns.stripplot(
    data=df_tm_official,
    x='season_id',
    y='score',
    color='black',
    alpha=0.15,
    jitter=0.2,
    size=3
)
plt.title("PKL Team Scoring Distribution Across Seasons 1 to 7", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("PKL Season", fontsize=12, labelpad=10)
plt.ylabel("Team Points Scored in Match", fontsize=12, labelpad=10)
plt.axhline(df_tm_official['score'].mean(), color='crimson', linestyle='--', linewidth=1.5, label=f"League Mean: {df_tm_official['score'].mean():.1f} pts")
plt.legend(frameon=True, facecolor='white', loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig1_scoring_by_season.png"))
plt.close()

# -------------------------------------------------------------
# Figure 2: Winning Margins & Clutch Scenario Distribution
# -------------------------------------------------------------
print("Generating Fig 2: Winning Margins...")
plt.figure(figsize=(10, 6))
margins = df_m_official['win_margin'].dropna()
sns.histplot(margins, bins=25, kde=True, color='#2b5c8f', edgecolor='white', alpha=0.7)
plt.axvline(margins.median(), color='darkorange', linestyle='--', linewidth=2, label=f"Median Margin: {margins.median():.0f} pts")
plt.axvline(3.5, color='crimson', linestyle=':', linewidth=2, label="Clutch Threshold (<= 3 pts, 28.6% of matches)")
plt.title("Distribution of Match Winning Margins in PKL History", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Winning Margin (Points Difference)", fontsize=12, labelpad=10)
plt.ylabel("Number of Matches", fontsize=12, labelpad=10)
plt.legend(frameon=True, facecolor='white', loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig2_winning_margins.png"))
plt.close()

# -------------------------------------------------------------
# Figure 3: All-Time Team Win Rates & Point Differentials
# -------------------------------------------------------------
print("Generating Fig 3: Team Win Rates...")
team_summary = df_tm_official.groupby('team_name').agg(
    matches=('match_id', 'count'),
    wins=('is_winner', 'sum'),
    differential=('score_difference', 'sum')
).reset_index()
team_summary['win_pct'] = 100.0 * team_summary['wins'] / team_summary['matches']
team_summary = team_summary.sort_values(by='win_pct', ascending=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), sharey=True)

colors1 = ['#2ca02c' if w >= 50 else '#1f77b4' for w in team_summary['win_pct']]
ax1.barh(team_summary['team_name'], team_summary['win_pct'], color=colors1, alpha=0.85)
ax1.axvline(50, color='gray', linestyle='--', linewidth=1)
ax1.set_xlabel("Win Percentage (%)", fontsize=12)
ax1.set_title("All-Time Win Percentage", fontsize=13, fontweight='bold')
for i, v in enumerate(team_summary['win_pct']):
    ax1.text(v + 1, i, f"{v:.1f}%", va='center', fontsize=9)

colors2 = ['#2ca02c' if d >= 0 else '#d62728' for d in team_summary['differential']]
ax2.barh(team_summary['team_name'], team_summary['differential'], color=colors2, alpha=0.85)
ax2.axvline(0, color='gray', linestyle='-', linewidth=1)
ax2.set_xlabel("Cumulative Point Differential", fontsize=12)
ax2.set_title("Cumulative Score Differential", fontsize=13, fontweight='bold')
for i, v in enumerate(team_summary['differential']):
    ax2.text(v + (15 if v >= 0 else -60), i, f"{v:+d}", va='center', fontsize=9)

plt.suptitle("Pro Kabaddi League: Franchise Historical Records (Seasons 1-7)", fontsize=15, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig3_team_win_loss_records.png"))
plt.close()

# -------------------------------------------------------------
# Figure 4: Raid Points vs. Tackle Points Scatter
# -------------------------------------------------------------
print("Generating Fig 4: Raid vs. Tackle Points...")
plt.figure(figsize=(9, 7))
team_perf = df_tm_official.groupby('team_name').agg(
    avg_raid=('raid_points_total', 'mean'),
    avg_tackle=('tackle_points_total', 'mean'),
    win_pct=('is_winner', lambda x: 100.0 * x.mean()),
    matches=('match_id', 'count')
).reset_index()

scatter = plt.scatter(
    team_perf['avg_raid'],
    team_perf['avg_tackle'],
    s=team_perf['matches'] * 3.5,
    c=team_perf['win_pct'],
    cmap='viridis',
    edgecolors='black',
    alpha=0.9,
    linewidth=1.2
)
cbar = plt.colorbar(scatter)
cbar.set_label('Win Percentage (%)', fontsize=11)

# Annotate team names
for _, r in team_perf.iterrows():
    plt.annotate(
        r['team_name'].replace("Jaipur Pink Panthers", "Jaipur").replace("Bengaluru Bulls", "Bengaluru").replace("Gujarat Fortunegiants", "Gujarat"),
        (r['avg_raid'] + 0.1, r['avg_tackle'] + 0.05),
        fontsize=9,
        fontweight='semibold'
    )

plt.axvline(team_perf['avg_raid'].mean(), color='gray', linestyle='--', linewidth=1, label="League Avg Raid Pts")
plt.axhline(team_perf['avg_tackle'].mean(), color='gray', linestyle=':', linewidth=1, label="League Avg Tackle Pts")
plt.title("Team Tactical Archetypes: Offensive Raid Pts vs. Defensive Tackle Pts (Per Match)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Average Raid Points Per Match", fontsize=12)
plt.ylabel("Average Tackle Points Per Match", fontsize=12)
plt.legend(frameon=True, loc='lower left')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig4_raid_vs_tackle_scatter.png"))
plt.close()

# -------------------------------------------------------------
# Figure 5: Top 10 All-Time Raiders & Defenders
# -------------------------------------------------------------
print("Generating Fig 5: Top Raiders and Defenders...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))

# Raiders
pm_played = df_player_match[df_player_match['played'] == True]
top_raiders = pm_played.groupby('player_name').agg(
    raid_pts=('raid_points_total', 'sum'),
    super_10s=('super_10', 'sum')
).sort_values(by='raid_pts', ascending=True).tail(10)

ax1.barh(top_raiders.index, top_raiders['raid_pts'], color='#e6550d', alpha=0.85)
ax1.set_xlabel("Total Career Raid Points", fontsize=12)
ax1.set_title("All-Time Top 10 Raiders", fontsize=13, fontweight='bold')
for i, (pname, v) in enumerate(zip(top_raiders.index, top_raiders['raid_pts'])):
    ax1.text(v + 10, i, f"{v} pts ({top_raiders.loc[pname, 'super_10s']} S10)", va='center', fontsize=9)

# Defenders
top_defenders = pm_played.groupby('player_name').agg(
    tackle_pts=('tackle_points_total', 'sum'),
    high_5s=('high_5', 'sum')
).sort_values(by='tackle_pts', ascending=True).tail(10)

ax2.barh(top_defenders.index, top_defenders['tackle_pts'], color='#3182bd', alpha=0.85)
ax2.set_xlabel("Total Career Tackle Points", fontsize=12)
ax2.set_title("All-Time Top 10 Defenders", fontsize=13, fontweight='bold')
for i, (pname, v) in enumerate(zip(top_defenders.index, top_defenders['tackle_pts'])):
    ax2.text(v + 5, i, f"{v} pts ({top_defenders.loc[pname, 'high_5s']} H5)", va='center', fontsize=9)

plt.suptitle("Pro Kabaddi League Legends: All-Time Elite Scorers & Defenders", fontsize=15, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig5_top_raiders_defenders.png"))
plt.close()

# -------------------------------------------------------------
# Figure 6: Raid Outcomes and Playmaking Frequency
# -------------------------------------------------------------
print("Generating Fig 6: Raid Outcomes Breakdown...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

# Raid outcome pie
raid_events = df_events[df_events['event_type'].str.contains('Raid', na=False)]['event_type'].value_counts()
colors_pie = ['#31a354', '#74c476', '#de2d26']
ax1.pie(
    raid_events.values[:3],
    labels=raid_events.index[:3],
    autopct='%1.1f%%',
    startangle=140,
    colors=colors_pie,
    wedgeprops=dict(edgecolor='white', linewidth=2, width=0.6)
)
ax1.set_title("Distribution of Raid Outcomes\n(66,000+ Actions)", fontsize=13, fontweight='bold')

# Explosive play per match by season
s_explosive = df_tm_official.groupby('season_id').agg(
    super_raids_per_match=('super_raids', lambda x: x.sum() / len(x.unique())),
    super_tackles_per_match=('super_tackles', lambda x: x.sum() / len(x.unique()))
)
x = np.arange(len(s_explosive))
width = 0.35
ax2.bar(x - width/2, s_explosive['super_raids_per_match'], width, label='Super Raids (3+ pts)', color='#fd8d3c', alpha=0.85)
ax2.bar(x + width/2, s_explosive['super_tackles_per_match'], width, label='Super Tackles (<=3 def)', color='#6baed6', alpha=0.85)
ax2.set_xticks(x)
ax2.set_xticklabels([f"Season {i}" for i in s_explosive.index])
ax2.set_ylabel("Frequency per Team-Match", fontsize=12)
ax2.set_title("Explosive Plays per Match by Season", fontsize=13, fontweight='bold')
ax2.legend(frameon=True, loc='upper right')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig6_event_outcomes_breakdown.png"))
plt.close()

# -------------------------------------------------------------
# Figure 7: Correlation Heatmap with Match Victory
# -------------------------------------------------------------
print("Generating Fig 7: Correlation Heatmap...")
corr_cols = [
    'score', 'score_difference', 'raid_points_total', 'raid_points_touch', 'raid_points_bonus',
    'tackle_points_total', 'all_out_points', 'extra_points',
    'raid_success_rate', 'tackle_success_rate', 'super_raids', 'super_tackles'
]
corr_df = df_tm_official[corr_cols].corr()

plt.figure(figsize=(11, 9))
sns.heatmap(
    corr_df,
    annot=True,
    fmt=".2f",
    cmap="vlag",
    center=0,
    linewidths=0.5,
    cbar_kws={"shrink": 0.8}
)
plt.title("Correlation Matrix of PKL Team Performance Attributes", fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig7_correlation_matrix.png"))
plt.close()

# -------------------------------------------------------------
# Figure 8: Match Momentum & Score Progression (Match 1 Showcase)
# -------------------------------------------------------------
print("Generating Fig 8: Match Momentum Timeline...")
m1_events = df_events[df_events['match_id'] == 1].sort_values(by='event_no').copy()
m1_events['time_minutes'] = m1_events['elapsed_seconds'] / 60.0

plt.figure(figsize=(11, 6))
plt.plot(m1_events['time_minutes'], m1_events['score_team_a'], label='Jaipur Pink Panthers', color='#e377c2', linewidth=2.5)
plt.plot(m1_events['time_minutes'], m1_events['score_team_b'], label='U Mumba', color='#ff7f0e', linewidth=2.5)
plt.axvline(20.0, color='gray', linestyle='--', linewidth=1.5, label='Half Time (20 min)')
plt.fill_between(m1_events['time_minutes'], m1_events['score_team_a'], m1_events['score_team_b'], color='gray', alpha=0.15)
plt.title("Chronological Score Progression: Match 1 (U Mumba vs Jaipur Pink Panthers)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Elapsed Match Time (Minutes)", fontsize=12)
plt.ylabel("Points", fontsize=12)
plt.xlim(0, 41)
plt.legend(frameon=True, facecolor='white', loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig8_score_progression_momentum.png"))
plt.close()

print("All 8 figures successfully generated and saved to reports/figures/!")
