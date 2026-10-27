import pandas as pd

df_tm = pd.read_parquet('data/processed/fact_team_match.parquet')
df_pm = pd.read_parquet('data/processed/fact_player_match.parquet')
pm_agg = df_pm.groupby(['match_id', 'team_id']).agg(sum_tackle=('tackle_points_total', 'sum')).reset_index()
merged = pd.merge(df_tm, pm_agg, on=['match_id', 'team_id'])
diffs = merged[merged['tackle_points_total'] != merged['sum_tackle']]
print("Divergent tackle rows by season:")
print(diffs['season_id'].value_counts(dropna=False))
