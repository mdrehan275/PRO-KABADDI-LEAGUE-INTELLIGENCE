"""
src/data/preprocess.py
----------------------
Reproducible data engineering and preprocessing pipeline for the Pro Kabaddi League (PKL) dataset.
Transforms raw CSV and JSON files into clean, validated, analytical dimension and fact tables.
Saves both Parquet and CSV formats in `data/processed/`.
"""

import os
import json
import logging
import re
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from .load_data import (
    load_raw_matches,
    load_raw_teams,
    load_raw_players,
    load_raw_events,
    load_match_json,
    get_available_match_ids
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- CANONICAL MAPPINGS & CONFIGURATION ---

# 12 Official PKL Franchises
PKL_FRANCHISE_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 28, 29, 30, 31}

# Official PKL Series IDs
PKL_SERIES_MAP = {
    1: {"season_id": 1, "season_name": "Season 1 (2014)", "year": 2014, "is_official_pkl": True},
    2: {"season_id": 2, "season_name": "Season 2 (2015)", "year": 2015, "is_official_pkl": True},
    3: {"season_id": 3, "season_name": "Season 3 (2016)", "year": 2016, "is_official_pkl": True},
    4: {"season_id": 4, "season_name": "Season 4 (2016)", "year": 2016, "is_official_pkl": True},
    8: {"season_id": 5, "season_name": "Season 5 (2017)", "year": 2017, "is_official_pkl": True},
    26: {"season_id": 6, "season_name": "Season 6 (2018)", "year": 2018, "is_official_pkl": True},
    49: {"season_id": 7, "season_name": "Season 7 (2019)", "year": 2019, "is_official_pkl": True},
}

# Team Name Normalization Map
TEAM_NAME_MAP = {
    1: "Bengaluru Bulls",
    2: "Dabang Delhi K.C.",
    3: "Jaipur Pink Panthers",
    4: "Bengal Warriors",
    5: "U Mumba",
    6: "Patna Pirates",
    7: "Puneri Paltan",
    8: "Telugu Titans",
    9: "Fire Birds",
    10: "Storm Queens",
    11: "Ice Divas",
    12: "India",
    13: "Republic of Korea",
    14: "Bangladesh",
    15: "Australia",
    16: "England",
    17: "Argentina",
    18: "Iran",
    19: "Thailand",
    20: "Japan",
    21: "USA",
    22: "Kenya",
    23: "Poland",
    24: "Indian Railways",
    25: "Haryana",
    26: "Services SSCB",
    27: "Maharashtra",
    28: "Haryana Steelers",
    29: "Tamil Thalaivas",
    30: "U.P. Yoddha",
    31: "Gujarat Fortunegiants",
    167: "Pakistan",
    172: "Sri Lanka",
    173: "India Women",
    174: "Indonesia Women",
    176: "Iran Women",
    181: "Chinese Taipei Women",
    236: "Pune Pride",
    237: "Pondicherry Predators",
    238: "Diler Delhi",
    239: "Chennai Challengers",
    240: "Bangalore Rhinos",
    241: "Telugu Bulls",
    242: "Mumbai Che Raje",
    243: "Haryana Heros"
}

# Team Short Names
TEAM_SHORT_NAMES = {
    1: "BLR", 2: "DEL", 3: "JAI", 4: "BEN", 5: "MUM", 6: "PAT",
    7: "PUN", 8: "TEL", 9: "FBD", 10: "STQ", 11: "ICD", 12: "IND",
    28: "HAR", 29: "CHE", 30: "UP", 31: "GUJ"
}

# Venue Normalization Map
VENUE_NORMALIZATION = {
    1: ("Sree Kanteerava Stadium", "Bengaluru"),
    2: ("Thyagaraj Sports Complex", "New Delhi"),
    3: ("Sawai Mansingh Stadium", "Jaipur"),
    4: ("Netaji Subhash Chandra Bose Indoor Stadium", "Kolkata"),
    5: ("DOME@NSCI SVP Stadium", "Mumbai"),
    6: ("Patliputra Sports Complex", "Patna"),
    7: ("Shree Shiv Chhatrapati Sports Complex", "Pune"),
    8: ("Gachibowli Indoor Stadium", "Hyderabad"),
    10: ("Indira Gandhi Indoor Stadium", "New Delhi"),
    11: ("The Arena by TransStadia", "Ahmedabad"),
    12: ("Umaid Stadium", "Jodhpur"),
    13: ("Babu Banarasi Das Indoor Stadium", "Lucknow"),
    14: ("Motilal Nehru School of Sports", "Sonepat"),
    15: ("Harivansh Tana Bhagat Indoor Stadium", "Ranchi"),
    16: ("Jawaharlal Nehru Indoor Stadium", "Chennai"),
    17: ("Mankapur Indoor Stadium", "Nagpur"),
    20: ("Al Wasl Sports Club", "Dubai"),
    21: ("Theatre Garuda", "Jakarta"),
    23: ("Shaheed Vijay Singh Pathik Sports Complex", "Greater Noida"),
    24: ("Rajiv Gandhi Indoor Stadium", "Kochi"),
    25: ("Tau Devilal Sports Complex", "Panchkula"),
}


def parse_clock_to_seconds(clock_str: Any) -> Optional[int]:
    """Converts MM:SS clock string to integer elapsed seconds."""
    if pd.isnull(clock_str) or not isinstance(clock_str, str):
        return None
    try:
        parts = clock_str.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        return None
    return None


def parse_score_tuple(score_str: Any) -> Tuple[Optional[int], Optional[int]]:
    """Converts score string e.g. '[14, 20]' to discrete tuple (14, 20)."""
    if pd.isnull(score_str) or not isinstance(score_str, str):
        return None, None
    try:
        nums = re.findall(r"\d+", score_str)
        if len(nums) >= 2:
            return int(nums[0]), int(nums[1])
    except Exception:
        return None, None
    return None, None


def normalize_toss_selection(sel_str: Any) -> Optional[str]:
    """Standardizes toss selection string."""
    if pd.isnull(sel_str) or not isinstance(sel_str, str):
        return None
    s = sel_str.strip()
    s = re.sub(r"\s*:\s*", ": ", s)
    if "court" in s.lower() and "left" in s.lower():
        return "Court - Left"
    elif "court" in s.lower() and "right" in s.lower():
        return "Court - Right"
    elif "raid" in s.lower() and "right" in s.lower():
        return "Raid - Right"
    elif "raid" in s.lower() and "left" in s.lower():
        return "Raid - Left"
    return s


def run_preprocessing_pipeline(output_dir: str = "data/processed") -> Dict[str, Any]:
    """
    Executes the end-to-end data engineering pipeline.
    Creates and validates:
      - dim_seasons
      - dim_teams
      - dim_players
      - dim_venues
      - fact_matches
      - fact_team_match
      - fact_player_match
      - fact_events
    Saves outputs in Parquet and CSV in `output_dir`.
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Starting PKL Preprocessing Pipeline...")

    # 1. Load Raw Data
    df_raw_match = load_raw_matches()
    df_raw_team = load_raw_teams()
    df_raw_players = load_raw_players()
    df_raw_events = load_raw_events()

    audit_stats = {
        "raw_matches_count": len(df_raw_match),
        "raw_team_records_count": len(df_raw_team),
        "raw_players_count": len(df_raw_players),
        "raw_events_count": len(df_raw_events),
    }

    # -------------------------------------------------------------
    # 2. Build Dimensions
    # -------------------------------------------------------------
    logger.info("Building dimension tables...")

    # A. dim_seasons
    all_series = df_raw_match[['series_id', 'series_name']].drop_duplicates().copy()
    seasons_records = []
    for _, row in all_series.iterrows():
        sid = row['series_id']
        sname = row['series_name']
        if sid in PKL_SERIES_MAP:
            info = PKL_SERIES_MAP[sid]
            seasons_records.append({
                "series_id": sid,
                "season_id": info["season_id"],
                "season_name": info["season_name"],
                "year": info["year"],
                "is_official_pkl": True
            })
        else:
            # External or testing tournament
            year_match = re.search(r"20\d\d", sname)
            year_val = int(year_match.group(0)) if year_match else 2016
            seasons_records.append({
                "series_id": sid,
                "season_id": None,
                "season_name": sname,
                "year": year_val,
                "is_official_pkl": False
            })
    dim_seasons = pd.DataFrame(seasons_records).sort_values(by=["is_official_pkl", "series_id"], ascending=[False, True])

    # B. dim_teams
    team_ids = df_raw_team['id'].unique()
    teams_records = []
    for tid in sorted(team_ids):
        canonical_name = TEAM_NAME_MAP.get(tid, df_raw_team[df_raw_team['id'] == tid]['name'].iloc[0])
        short_name = TEAM_SHORT_NAMES.get(tid, df_raw_team[df_raw_team['id'] == tid]['short_name'].iloc[0])
        is_pkl = tid in PKL_FRANCHISE_IDS
        era = "Inaugural 8" if tid in range(1, 9) else ("Expansion 4" if tid in [28, 29, 30, 31] else "Non-PKL")
        teams_records.append({
            "team_id": int(tid),
            "team_name": canonical_name,
            "short_name": short_name,
            "is_pkl_franchise": is_pkl,
            "franchise_era": era
        })
    dim_teams = pd.DataFrame(teams_records)

    # C. dim_venues
    venue_records = []
    for vid in sorted(df_raw_match['venue_id'].unique()):
        if vid in VENUE_NORMALIZATION:
            vname, city = VENUE_NORMALIZATION[vid]
        else:
            raw_vname = df_raw_match[df_raw_match['venue_id'] == vid]['venue_name'].iloc[0]
            vname = raw_vname
            city = raw_vname.split(",")[-1].strip() if "," in raw_vname else "Unknown"
        venue_records.append({
            "venue_id": int(vid),
            "venue_name": vname,
            "city": city
        })
    dim_venues = pd.DataFrame(venue_records)

    # D. dim_players (Player Master Dimension)
    # Note: In raw data, player_role is 100% unpopulated (empty strings/nulls).
    # We empirically derive the player's tactical role based on career raid vs tackle action ratios:
    # - Raider: >= 70% of actions are raids
    # - Defender: <= 30% of actions are raids (>= 70% tackles)
    # - All-Rounder: balanced raid & tackle actions
    # - Bench/Reserve: 0 on-court actions
    p_actions = df_raw_players.groupby('player_id').agg(
        total_raids=('player_raids_total', 'sum'),
        total_tackles=('player_tackles_total', 'sum'),
        raid_pts=('player_raid_points_total', 'sum'),
        tackle_pts=('player_tackle_points_total', 'sum')
    ).reset_index()

    def classify_player_role(r):
        total_actions = r['total_raids'] + r['total_tackles']
        if total_actions == 0:
            return 'Bench/Reserve'
        raid_share = r['total_raids'] / total_actions
        if raid_share >= 0.70:
            return 'Raider'
        elif raid_share <= 0.30:
            return 'Defender'
        else:
            return 'All-Rounder'

    p_actions['empirical_role'] = p_actions.apply(classify_player_role, axis=1)
    player_id_to_role = p_actions.set_index('player_id')['empirical_role'].to_dict()

    player_agg = df_raw_players.groupby('player_id').agg(
        player_name=('player_name', lambda x: x.dropna().iloc[0] if not x.dropna().empty else f"Player_{x.name}"),
        player_short_name=('player_short_name', lambda x: x.dropna().iloc[0] if not x.dropna().empty else ""),
        primary_skill=('player_skill', lambda x: x.dropna().mode().iloc[0] if not x.dropna().empty else "Unspecified"),
        total_career_appearances=('player_played', 'count'),
        total_career_points=('player_total_points', 'sum'),
        total_career_raid_points=('player_raid_points_total', 'sum'),
        total_career_tackle_points=('player_tackle_points_total', 'sum')
    ).reset_index()
    player_agg['primary_role'] = player_agg['player_id'].map(player_id_to_role)
    dim_players = player_agg[['player_id', 'player_name', 'player_short_name', 'primary_role', 'primary_skill',
                              'total_career_appearances', 'total_career_points', 'total_career_raid_points', 'total_career_tackle_points']]

    # Player Name Lookup for fast mapping
    player_id_to_name = dim_players.set_index('player_id')['player_name'].to_dict()

    # -------------------------------------------------------------
    # 3. Clean fact_team_match
    # -------------------------------------------------------------
    logger.info("Building fact_team_match...")
    # Standardize column naming and drop scraper artifact columns
    df_tm = pd.DataFrame()
    df_tm['match_id'] = df_raw_team['match_id'].astype(int)
    df_tm['team_id'] = df_raw_team['id'].astype(int)
    df_tm['team_name'] = df_tm['team_id'].map(dim_teams.set_index('team_id')['team_name'])
    df_tm['short_name'] = df_tm['team_id'].map(dim_teams.set_index('team_id')['short_name'])
    df_tm['score'] = df_raw_team['score'].astype(int)

    # Points breakdown
    df_tm['raid_points_total'] = df_raw_team['stats.points.raid_points.total'].astype(int)
    df_tm['raid_points_touch'] = df_raw_team['stats.points.raid_points.touch'].astype(int)
    df_tm['raid_points_bonus'] = df_raw_team['stats.points.raid_points.raid_bonus'].astype(int)
    df_tm['tackle_points_total'] = df_raw_team['stats.points.tackle_points.total'].astype(int)
    df_tm['tackle_points_capture'] = df_raw_team['stats.points.tackle_points.capture'].astype(int)
    df_tm['tackle_points_bonus'] = df_raw_team['stats.points.tackle_points.capture_bonus'].astype(int)
    df_tm['all_out_points'] = df_raw_team['stats.points.all_out'].astype(int)
    df_tm['extra_points'] = df_raw_team['stats.points.extras'].astype(int)

    # Count statistics
    df_tm['raids_total'] = df_raw_team['stats.raids.total'].astype(int)
    df_tm['raids_successful'] = df_raw_team['stats.raids.successful'].astype(int)
    df_tm['raids_unsuccessful'] = df_raw_team['stats.raids.unsuccessful'].astype(int)
    df_tm['raids_empty'] = df_raw_team['stats.raids.Empty'].astype(int)
    df_tm['super_raids'] = df_raw_team['stats.raids.super_raids'].fillna(0).astype(int)

    df_tm['tackles_total'] = df_raw_team['stats.tackles.total'].astype(int)
    df_tm['tackles_successful'] = df_raw_team['stats.tackles.successful'].astype(int)
    df_tm['tackles_unsuccessful'] = df_raw_team['stats.tackles.unsuccessful'].astype(int)
    df_tm['super_tackles'] = df_raw_team['stats.tackles.super_tackles'].fillna(0).astype(int)
    df_tm['all_outs_inflicted'] = df_raw_team['stats.all_outs'].astype(int)

    # Rates
    df_tm['raid_success_rate'] = np.where(df_tm['raids_total'] > 0, df_tm['raids_successful'] / df_tm['raids_total'], 0.0)
    df_tm['tackle_success_rate'] = np.where(df_tm['tackles_total'] > 0, df_tm['tackles_successful'] / df_tm['tackles_total'], 0.0)

    # Attach match date and series details
    match_meta = df_raw_match[['match_id', 'series_id', 'date', 'status']].copy()
    match_meta['match_date'] = pd.to_datetime(match_meta['date'], format='mixed').dt.strftime('%Y-%m-%d')
    match_meta['season_id'] = match_meta['series_id'].map(lambda s: PKL_SERIES_MAP[s]['season_id'] if s in PKL_SERIES_MAP else None)
    match_meta['is_official_pkl'] = match_meta['series_id'].isin(PKL_SERIES_MAP)
    df_tm = pd.merge(df_tm, match_meta[['match_id', 'match_date', 'season_id', 'is_official_pkl', 'status']], on='match_id', how='left')

    # Opponent linking (pairing the 2 records per match)
    opponents = []
    for mid, group in df_tm.groupby('match_id'):
        if len(group) == 2:
            r0 = group.iloc[0]
            r1 = group.iloc[1]
            opponents.append({
                "match_id": mid,
                "team_id": r0['team_id'],
                "opponent_team_id": r1['team_id'],
                "opponent_team_name": r1['team_name'],
                "opponent_score": r1['score']
            })
            opponents.append({
                "match_id": mid,
                "team_id": r1['team_id'],
                "opponent_team_id": r0['team_id'],
                "opponent_team_name": r0['team_name'],
                "opponent_score": r0['score']
            })
    df_opp = pd.DataFrame(opponents)
    df_tm = pd.merge(df_tm, df_opp, on=['match_id', 'team_id'], how='left')

    df_tm['score_difference'] = df_tm['score'] - df_tm['opponent_score']
    df_tm['result'] = np.where(
        df_tm['status'] != 'Full Time', 'Incomplete',
        np.where(df_tm['score_difference'] > 0, 'Win',
                 np.where(df_tm['score_difference'] < 0, 'Loss', 'Tie'))
    )
    df_tm['is_winner'] = df_tm['result'] == 'Win'

    fact_team_match = df_tm.sort_values(by=['match_date', 'match_id', 'team_id']).reset_index(drop=True)

    # -------------------------------------------------------------
    # 4. Clean fact_matches
    # -------------------------------------------------------------
    logger.info("Building fact_matches...")
    matches_list = []
    for mid, group in fact_team_match.groupby('match_id'):
        m_raw = df_raw_match[df_raw_match['match_id'] == mid].iloc[0]
        
        # Determine canonical Team A and Team B (sorted by team_id)
        group_sorted = group.sort_values(by='team_id')
        t_a = group_sorted.iloc[0]
        t_b = group_sorted.iloc[1]

        # Resolution for player of the match
        potm_id = m_raw['player_id_of_the_match']
        potm_id_int = int(potm_id) if pd.notnull(potm_id) else None
        potm_name = player_id_to_name.get(potm_id_int, None) if potm_id_int else None

        # Winner resolution
        if m_raw['status'] != 'Full Time':
            winner_id = None
            winner_name = None
            is_tie = False
            margin = None
        elif t_a['score'] > t_b['score']:
            winner_id = t_a['team_id']
            winner_name = t_a['team_name']
            is_tie = False
            margin = t_a['score'] - t_b['score']
        elif t_b['score'] > t_a['score']:
            winner_id = t_b['team_id']
            winner_name = t_b['team_name']
            is_tie = False
            margin = t_b['score'] - t_a['score']
        else:
            winner_id = None
            winner_name = "Tied"
            is_tie = True
            margin = 0

        # Venue canonical
        vid = int(m_raw['venue_id'])
        v_name = dim_venues[dim_venues['venue_id'] == vid]['venue_name'].iloc[0] if vid in dim_venues['venue_id'].values else m_raw['venue_name']

        # Home team
        ht_id = int(m_raw['home_team_id']) if pd.notnull(m_raw['home_team_id']) else None
        ht_name = TEAM_NAME_MAP.get(ht_id, None) if ht_id else None

        # Normalized toss
        toss_sel = normalize_toss_selection(m_raw['toss_selection'])

        matches_list.append({
            "match_id": int(mid),
            "match_number": str(m_raw['match_number']),
            "series_id": int(m_raw['series_id']),
            "season_id": PKL_SERIES_MAP[m_raw['series_id']]['season_id'] if m_raw['series_id'] in PKL_SERIES_MAP else None,
            "season_name": PKL_SERIES_MAP[m_raw['series_id']]['season_name'] if m_raw['series_id'] in PKL_SERIES_MAP else m_raw['series_name'],
            "is_official_pkl": m_raw['series_id'] in PKL_SERIES_MAP,
            "match_date": pd.to_datetime(m_raw['date'], format='mixed').strftime('%Y-%m-%d'),
            "start_time": str(m_raw['start_time']),
            "venue_id": vid,
            "venue_name": v_name,
            "home_team_id": ht_id,
            "home_team_name": ht_name,
            "toss_winner_id": int(m_raw['toss_winner']),
            "toss_selection": toss_sel,
            "team_a_id": t_a['team_id'],
            "team_a_name": t_a['team_name'],
            "team_a_score": t_a['score'],
            "team_b_id": t_b['team_id'],
            "team_b_name": t_b['team_name'],
            "team_b_score": t_b['score'],
            "total_match_points": t_a['score'] + t_b['score'],
            "win_margin": margin,
            "winner_team_id": winner_id,
            "winner_team_name": winner_name,
            "is_tie": is_tie,
            "player_of_the_match_id": potm_id_int,
            "player_of_the_match_name": potm_name,
            "status": str(m_raw['status']),
            "is_completed": (m_raw['status'] == 'Full Time'),
            "raw_result_text": str(m_raw['result']) if pd.notnull(m_raw['result']) else None
        })

    fact_matches = pd.DataFrame(matches_list).sort_values(by=['match_date', 'match_id']).reset_index(drop=True)

    # -------------------------------------------------------------
    # 5. Clean fact_player_match
    # -------------------------------------------------------------
    logger.info("Building fact_player_match...")
    df_pm = pd.DataFrame()
    df_pm['match_id'] = df_raw_players['match_id'].astype(int)
    df_pm['team_id'] = df_raw_players['team_id'].astype(int)
    df_pm['player_id'] = df_raw_players['player_id'].astype(int)
    df_pm['player_name'] = df_pm['player_id'].map(player_id_to_name)
    df_pm['player_short_name'] = df_raw_players['player_short_name'].fillna('')
    df_pm['player_role'] = df_pm['player_id'].map(player_id_to_role)
    df_pm['player_skill'] = df_raw_players['player_skill'].fillna('Unspecified')

    # Status flags
    df_pm['played'] = df_raw_players['player_played'].astype(bool)
    df_pm['starter'] = df_raw_players['player_on_starter'].astype(bool)
    df_pm['captain'] = df_raw_players['player_captain'].astype(bool)

    # Scoring metrics
    df_pm['total_points'] = df_raw_players['player_total_points'].astype(int)
    df_pm['raid_points_total'] = df_raw_players['player_raid_points_total'].astype(int)
    df_pm['raid_points_touch'] = df_raw_players['player_raid_points_touch'].astype(int)
    df_pm['raid_points_bonus'] = df_raw_players['player_raid_points_raid_bonus'].astype(int)
    df_pm['tackle_points_total'] = df_raw_players['player_tackle_points_total'].astype(int)
    df_pm['tackle_points_touch'] = df_raw_players['player_tackle_points_touch'].astype(int)
    df_pm['tackle_points_capture_bonus'] = df_raw_players['player_tackle_points_capture_bonus'].astype(int)

    # Raid counts
    df_pm['raids_total'] = df_raw_players['player_raids_total'].astype(int)
    df_pm['raids_successful'] = df_raw_players['player_raids_successful'].astype(int)
    df_pm['raids_unsuccessful'] = df_raw_players['player_raids_unsuccessful'].astype(int)
    df_pm['raids_empty'] = df_raw_players['player_raids_Empty'].astype(int)

    # Tackle counts
    df_pm['tackles_total'] = df_raw_players['player_tackles_total'].astype(int)
    df_pm['tackles_successful'] = df_raw_players['player_tackles_successful'].astype(int)
    df_pm['tackles_unsuccessful'] = df_raw_players['player_tackles_unsuccessful'].astype(int)

    # Cards
    df_pm['green_cards'] = df_raw_players['player_green_card'].fillna(0).astype(int)
    df_pm['yellow_cards'] = df_raw_players['player_yellow_card'].fillna(0).astype(int)
    df_pm['red_cards'] = df_raw_players['player_red_card'].fillna(0).astype(int)

    # Milestones
    df_pm['super_10'] = df_pm['raid_points_total'] >= 10
    df_pm['high_5'] = df_pm['tackle_points_total'] >= 5

    # Merge match metadata
    df_pm = pd.merge(df_pm, fact_matches[['match_id', 'season_id', 'is_official_pkl', 'match_date']], on='match_id', how='left')
    fact_player_match = df_pm.sort_values(by=['match_date', 'match_id', 'team_id', 'total_points'], ascending=[True, True, True, False]).reset_index(drop=True)

    # -------------------------------------------------------------
    # 6. Clean fact_events
    # -------------------------------------------------------------
    logger.info("Building fact_events...")
    df_ev = pd.DataFrame()
    df_ev['event_row_id'] = range(1, len(df_raw_events) + 1)
    df_ev['event_type_id'] = df_raw_events['event_id'].astype(int)
    df_ev['match_id'] = df_raw_events['match_id'].astype(int)
    df_ev['event_no'] = df_raw_events['event_no'].astype(int)
    df_ev['clock'] = df_raw_events['clock'].astype(str)
    df_ev['elapsed_seconds'] = df_raw_events['clock'].apply(parse_clock_to_seconds)
    df_ev['event_type'] = df_raw_events['event'].fillna('Other')
    df_ev['event_text'] = df_raw_events['event_text'].fillna('')

    df_ev['raiding_team_id'] = df_raw_events['raiding_team_id'].apply(lambda x: int(x) if pd.notnull(x) else None)
    df_ev['defending_team_id'] = df_raw_events['defending_team_id'].apply(lambda x: int(x) if pd.notnull(x) else None)
    df_ev['raider_id'] = df_raw_events['raider_id'].apply(lambda x: int(x) if pd.notnull(x) else None)
    df_ev['defender_id'] = df_raw_events['defender_id'].apply(lambda x: int(x) if pd.notnull(x) else None)

    df_ev['raid_points'] = df_raw_events['raid_points'].fillna(0).astype(int)
    df_ev['defending_points'] = df_raw_events['defending_points'].fillna(0).astype(int)

    # Parse running score string e.g. '[0, 1]'
    score_tuples = df_raw_events['score'].apply(parse_score_tuple)
    df_ev['score_team_a'] = [t[0] for t in score_tuples]
    df_ev['score_team_b'] = [t[1] for t in score_tuples]
    df_ev['score_difference'] = np.where(df_ev['score_team_a'].notnull() & df_ev['score_team_b'].notnull(),
                                         df_ev['score_team_a'] - df_ev['score_team_b'], None)

    # Sparse flags
    df_ev['is_super_raid'] = df_raw_events['super_raid'].fillna(False).astype(bool)
    df_ev['is_super_tackle'] = df_raw_events['super_tackle'].fillna(False).astype(bool)
    df_ev['is_do_or_die'] = df_raw_events['do_or_die'].fillna(False).astype(bool)

    # Forward-fill running scores if occasional event rows lack running score
    df_ev['score_team_a'] = df_ev.groupby('match_id')['score_team_a'].ffill().bfill().fillna(0).astype(int)
    df_ev['score_team_b'] = df_ev.groupby('match_id')['score_team_b'].ffill().bfill().fillna(0).astype(int)
    df_ev['score_difference'] = df_ev['score_team_a'] - df_ev['score_team_b']

    fact_events = df_ev.sort_values(by=['match_id', 'event_no']).reset_index(drop=True)

    # -------------------------------------------------------------
    # 7. Save Clean Outputs to Parquet and CSV
    # -------------------------------------------------------------
    logger.info(f"Writing clean artifacts to {output_dir}...")
    tables = {
        "dim_seasons": dim_seasons,
        "dim_teams": dim_teams,
        "dim_venues": dim_venues,
        "dim_players": dim_players,
        "fact_matches": fact_matches,
        "fact_team_match": fact_team_match,
        "fact_player_match": fact_player_match,
        "fact_events": fact_events
    }

    for name, df in tables.items():
        parquet_path = os.path.join(output_dir, f"{name}.parquet")
        csv_path = os.path.join(output_dir, f"{name}.csv")
        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False)
        logger.info(f"  {name:<18}: {len(df):>6} rows saved -> {parquet_path} and {csv_path}")

    logger.info("Preprocessing Pipeline Completed Successfully!")
    return {
        "tables_written": list(tables.keys()),
        "record_counts": {k: len(v) for k, v in tables.items()},
        "audit_stats": audit_stats
    }


if __name__ == "__main__":
    results = run_preprocessing_pipeline()
    print("\n--- Pipeline Execution Summary ---")
    for tbl, count in results["record_counts"].items():
        print(f"  {tbl:<20}: {count} records")
