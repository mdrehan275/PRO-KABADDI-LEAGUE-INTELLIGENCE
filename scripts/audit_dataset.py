import os
import sys
import glob
import json
import pandas as pd
import numpy as np

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" {title.upper()} ")
    print("=" * 80)

# 1. Load data
print_separator("1. Loading Data")
df_match = pd.read_csv("DS_match.csv")
df_team = pd.read_csv("DS_team.csv")
df_players = pd.read_csv("DS_players.csv")
df_events = pd.read_csv("DS_events.csv", low_memory=False)

print(f"DS_match shape: {df_match.shape}")
print(f"DS_team shape: {df_team.shape}")
print(f"DS_players shape: {df_players.shape}")
print(f"DS_events shape: {df_events.shape}")

# 2. Detailed Series Analysis
print_separator("2. Series Breakdown and PKL Seasons")
series_summary = df_match.groupby(['series_id', 'series_name']).agg(
    match_count=('match_id', 'count'),
    min_date=('date', 'min'),
    max_date=('date', 'max'),
    distinct_teams=('match_id', lambda m: df_team[df_team['match_id'].isin(m)]['id'].nunique()),
    statuses=('status', lambda x: list(x.unique()))
).reset_index()
print(series_summary.to_string())

# 3. Team Names & Consistency
print_separator("3. Team Identifiers & Name Inconsistencies")
teams_per_id = df_team.groupby('id')['name'].unique().to_dict()
for tid, names in sorted(teams_per_id.items()):
    print(f"Team ID {tid:<3}: {list(names)}")

# 4. Team Score Components Reconciliation
print_separator("4. Team Score Components Breakdown")
# Let's check where score != raid + tackle + all_out + extras
calculated_pts = (
    df_team['stats.points.raid_points.total'] + 
    df_team['stats.points.tackle_points.total'] + 
    df_team['stats.points.all_out'] + 
    df_team['stats.points.extras']
)
discrepancies = df_team[df_team['score'] != calculated_pts]
print(f"Number of rows where score != raid + tackle + all_out + extras: {len(discrepancies)} out of {len(df_team)} ({len(discrepancies)/len(df_team)*100:.2f}%)")
if len(discrepancies) > 0:
    print("Sample discrepancies (diff = score - calc):")
    sample_disc = discrepancies[['match_id', 'id', 'name', 'score', 'stats.points.raid_points.total', 'stats.points.tackle_points.total', 'stats.points.all_out', 'stats.points.extras']].copy()
    sample_disc['calc'] = calculated_pts.loc[discrepancies.index]
    sample_disc['diff'] = sample_disc['score'] - sample_disc['calc']
    print(sample_disc.head(10).to_string())
    print("\nValue counts of diff:")
    print(sample_disc['diff'].value_counts())

# 5. Reconcile Player Points with Team Points
print_separator("5. Reconcile Player Points with Team Points")
# Player points aggregation
player_agg = df_players.groupby(['match_id', 'team_id']).agg(
    player_count=('player_id', 'count'),
    player_raid_total=('player_raid_points_total', 'sum'),
    player_tackle_total=('player_tackle_points_total', 'sum'),
    player_points_total=('player_total_points', 'sum')
).reset_index()

team_player_recon = pd.merge(df_team, player_agg, left_on=['match_id', 'id'], right_on=['match_id', 'team_id'], how='left')
print(f"Team rows with matching player records: {team_player_recon['player_count'].notnull().sum()} / {len(df_team)}")
missing_players = team_player_recon[team_player_recon['player_count'].isnull()]
print(f"Team rows with MISSING player records: {len(missing_players)}")
if len(missing_players) > 0:
    print("Matches with missing player records:", missing_players[['match_id', 'name', 'score']].head(10).to_string())

valid_recon = team_player_recon[team_player_recon['player_count'].notnull()].copy()
valid_recon['raid_diff'] = valid_recon['stats.points.raid_points.total'] - valid_recon['player_raid_total']
valid_recon['tackle_diff'] = valid_recon['stats.points.tackle_points.total'] - valid_recon['player_tackle_total']
print(f"\nRaid point differences between team stat and sum of players:")
print(f"  Exact matches: {(valid_recon['raid_diff'] == 0).sum()} / {len(valid_recon)} ({(valid_recon['raid_diff'] == 0).mean()*100:.1f}%)")
print(f"  Discrepant count: {(valid_recon['raid_diff'] != 0).sum()}")
if (valid_recon['raid_diff'] != 0).sum() > 0:
    print("  Raid diff value counts:\n", valid_recon['raid_diff'].value_counts().head(5))

print(f"\nTackle point differences between team stat and sum of players:")
print(f"  Exact matches: {(valid_recon['tackle_diff'] == 0).sum()} / {len(valid_recon)} ({(valid_recon['tackle_diff'] == 0).mean()*100:.1f}%)")
print(f"  Discrepant count: {(valid_recon['tackle_diff'] != 0).sum()}")
if (valid_recon['tackle_diff'] != 0).sum() > 0:
    print("  Tackle diff value counts:\n", valid_recon['tackle_diff'].value_counts().head(5))

# 6. Player Name Resolution for player_of_the_match
print_separator("6. Player of the Match Name Resolution")
# Create player_id -> player_name lookup table
player_lookup = df_players.dropna(subset=['player_id', 'player_name']).groupby('player_id')['player_name'].unique().to_dict()
print(f"Total unique players with names in DS_players: {len(player_lookup)}")

# Check if player_id_of_the_match can be mapped
potm_ids = df_match['player_id_of_the_match'].dropna().unique()
mapped_potm = [pid for pid in potm_ids if pid in player_lookup]
print(f"POTM unique IDs in DS_match: {len(potm_ids)}")
print(f"POTM IDs successfully mapped to DS_players: {len(mapped_potm)} / {len(potm_ids)}")
unmapped_potm = [pid for pid in potm_ids if pid not in player_lookup]
if unmapped_potm:
    print(f"Unmapped POTM IDs ({len(unmapped_potm)}):", unmapped_potm[:10])

# 7. Venue and Date Format Audit
print_separator("7. Venue and Date Formats")
print("Unique venues in DS_match:")
venues = df_match.groupby(['venue_id', 'venue_name']).size().reset_index(name='match_count')
print(venues.to_string())

print("\nDate format inspection (sample 10 dates):")
print(df_match['date'].head(10).tolist())
# Check parseability of dates
dates_parsed = pd.to_datetime(df_match['date'], errors='coerce')
print(f"Null dates after pd.to_datetime: {dates_parsed.isnull().sum()}")

# 8. Inspect Match JSON Structure
print_separator("8. Deep Inspection of Match JSON Files")
for mid in [1, 100, 1050]:
    json_path = f"Data/Data/Match_Data/{mid}.json"
    if os.path.exists(json_path):
        print(f"\n--- Reading JSON: {json_path} ---")
        with open(json_path, 'r', encoding='utf-8') as f:
            jdata = json.load(f)
        print("Root keys:", list(jdata.keys()))
        for k in jdata:
            val = jdata[k]
            if isinstance(val, dict):
                print(f"  ['{k}'] is dict with {len(val)} keys: {list(val.keys())[:10]}")
            elif isinstance(val, list):
                print(f"  ['{k}'] is list with {len(val)} items. First item type: {type(val[0]).__name__ if val else 'empty'}")
                if val and isinstance(val[0], dict):
                    print(f"    first item keys: {list(val[0].keys())[:10]}")
            else:
                print(f"  ['{k}'] is {type(val).__name__}: {str(val)[:50]}")
        
        # Check teams in JSON
        if 'teams' in jdata:
            teams_obj = jdata['teams']
            if isinstance(teams_obj, dict):
                print("  teams keys:", list(teams_obj.keys()))
                for tk, tv in teams_obj.items():
                    if isinstance(tv, dict):
                        print(f"    team '{tk}': id={tv.get('id')}, name={tv.get('name')}, score={tv.get('score')}")
            elif isinstance(teams_obj, list):
                for t in teams_obj:
                    if isinstance(t, dict):
                        print(f"    team list item: id={t.get('id')}, name={t.get('name')}, score={t.get('score')}")

# 9. Events Table Analysis
print_separator("9. Event Outcomes and Clock Semantics")
print("Top event values in DS_events:")
print(df_events['event'].value_counts(dropna=False).head(15))

print("\nSample clocks:")
print(df_events['clock'].dropna().head(10).tolist())

print("\nDo-or-die column values:")
print(df_events['do_or_die'].value_counts(dropna=False))

print("\nSuper raid values:")
print(df_events['super_raid'].value_counts(dropna=False))

print("\nSuper tackle values:")
print(df_events['super_tackle'].value_counts(dropna=False))

print("\nScore column format in DS_events (sample 10):")
print(df_events['score'].dropna().head(10).tolist())

print_separator("10. Toss Analysis in DS_match")
print("Toss selection values:")
print(df_match['toss_selection'].value_counts(dropna=False))
print("Toss winner match to home_team_id:")
print((df_match['toss_winner'] == df_match['home_team_id']).value_counts(dropna=False))

print("\nAudit script 2 execution finished.")
