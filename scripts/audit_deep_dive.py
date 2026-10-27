import os
import json
import pandas as pd
import numpy as np

print("=" * 80)
print("DEEP DIVE AUDIT: SCORE DISCREPANCIES, DATES, CLOCK, AND VENUES")
print("=" * 80)

# 1. Team Score Discrepancies
df_team = pd.read_csv("DS_team.csv")
calc_pts = (
    df_team['stats.points.raid_points.total'] + 
    df_team['stats.points.tackle_points.total'] + 
    df_team['stats.points.all_out'] + 
    df_team['stats.points.extras']
)
diff = df_team['score'] - calc_pts
discrepant_teams = df_team[diff != 0].copy()
print(f"Total rows with score difference: {len(discrepant_teams)} / {len(df_team)}")

# 2. Date format issues in DS_match.csv
df_match = pd.read_csv("DS_match.csv")
print("\n" + "=" * 80)
print("DATE FORMAT ISSUES IN DS_match.csv")
# Check how pd.to_datetime handles dates with format='mixed'
parsed_dates_mixed = pd.to_datetime(df_match['date'], format='mixed', errors='coerce')
print(f"Unparsed dates with format='mixed': {parsed_dates_mixed.isnull().sum()}")
if parsed_dates_mixed.isnull().sum() > 0:
    print(df_match.loc[parsed_dates_mixed.isnull(), ['match_id', 'date', 'series_id', 'series_name']])
else:
    print(f"All {len(df_match)} dates successfully parsed with format='mixed'!")
    print(f"Date range: {parsed_dates_mixed.min().strftime('%Y-%m-%d')} to {parsed_dates_mixed.max().strftime('%Y-%m-%d')}")

# 3. Clock format & direction in DS_events.csv
print("\n" + "=" * 80)
print("EVENT CLOCK DIRECTION AND ORDERING IN DS_events.csv")
df_events = pd.read_csv("DS_events.csv", low_memory=False)
sample_events_m1 = df_events[df_events['match_id'] == 1].head(10)[['event_no', 'clock', 'event', 'score', 'raid_points', 'defending_points']]
print("First 10 events of Match 1:")
print(sample_events_m1.to_string())
sample_events_m1_tail = df_events[df_events['match_id'] == 1].tail(10)[['event_no', 'clock', 'event', 'score', 'raid_points', 'defending_points']]
print("\nLast 10 events of Match 1:")
print(sample_events_m1_tail.to_string())

# 4. Status breakdown in DS_match
print("\n" + "=" * 80)
print("STATUS BREAKDOWN IN DS_match.csv")
print(df_match['status'].value_counts())
non_full_time = df_match[df_match['status'] != 'Full Time']
print(f"Non-full-time matches ({len(non_full_time)}):")
print(non_full_time[['match_id', 'date', 'series_id', 'series_name', 'status', 'result']].to_string())

# 5. Result field parsing in DS_match
print("\n" + "=" * 80)
print("RESULT FIELD STRUCTURE IN DS_match.csv")
print("Null results count:", df_match['result'].isnull().sum())
print("Null result matches:")
print(df_match[df_match['result'].isnull()][['match_id', 'series_name', 'status', 'date']])

# 6. Team Name Normalization Mapping
print("\n" + "=" * 80)
print("TEAM NAME NORMALIZATION CHECK")
team_names_map = df_team.groupby(['id', 'name']).size().reset_index(name='n_matches')
print(team_names_map.to_string())

# 7. Summary Stats Directory contents
print("\n" + "=" * 80)
print("SUMMARY STATS DIRECTORY AUDIT")
import glob
summary_folders = sorted(glob.glob("Data/Data/Summary Stats/*"))
for sf in summary_folders:
    s_files = os.listdir(sf)
    sample_file_path = os.path.join(sf, s_files[0]) if s_files else None
    first_few_chars = ""
    if sample_file_path and os.path.isfile(sample_file_path):
        with open(sample_file_path, 'r', encoding='utf-8') as f:
            first_few_chars = f.read(100).replace('\n', ' ')
    print(f"Folder: {os.path.basename(sf):<30} Files ({len(s_files)}): {s_files[:3]} | sample content: {first_few_chars[:40]}")

print("\nAudit Deep Dive completed successfully.")
