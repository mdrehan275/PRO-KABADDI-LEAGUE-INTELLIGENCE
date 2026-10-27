"""
src/analytics/metrics.py
------------------------
Core KPI and statistical metrics calculations for the PKL Analytics Platform.
Provides reusable functions for team performance, player profiling, match dynamics,
and head-to-head records.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def calculate_team_summary_metrics(df_team_match: pd.DataFrame, official_only: bool = True) -> pd.DataFrame:
    """
    Computes franchise performance summaries: win rate, points scored/conceded,
    raid/tackle contributions, and success rates.
    """
    df = df_team_match.copy()
    if official_only and 'is_official_pkl' in df.columns:
        df = df[df['is_official_pkl'] == True]
    if 'status' in df.columns:
        df = df[df['status'] == 'Full Time']

    grouped = df.groupby(['team_id', 'team_name']).agg(
        matches_played=('match_id', 'count'),
        wins=('is_winner', 'sum'),
        ties=('result', lambda r: (r == 'Tie').sum()),
        losses=('result', lambda r: (r == 'Loss').sum()),
        total_points_scored=('score', 'sum'),
        total_points_conceded=('opponent_score', 'sum'),
        avg_score=('score', 'mean'),
        avg_conceded=('opponent_score', 'mean'),
        total_raid_points=('raid_points_total', 'sum'),
        total_tackle_points=('tackle_points_total', 'sum'),
        total_all_out_points=('all_out_points', 'sum'),
        total_extra_points=('extra_points', 'sum'),
        total_raids=('raids_total', 'sum'),
        successful_raids=('raids_successful', 'sum'),
        empty_raids=('raids_empty', 'sum'),
        unsuccessful_raids=('raids_unsuccessful', 'sum'),
        total_tackles=('tackles_total', 'sum'),
        successful_tackles=('tackles_successful', 'sum'),
        super_raids=('super_raids', 'sum'),
        super_tackles=('super_tackles', 'sum'),
        all_outs_inflicted=('all_outs_inflicted', 'sum')
    ).reset_index()

    grouped['win_percentage'] = np.round(100.0 * grouped['wins'] / grouped['matches_played'], 2)
    grouped['point_differential'] = grouped['total_points_scored'] - grouped['total_points_conceded']
    grouped['raid_success_rate'] = np.round(100.0 * grouped['successful_raids'] / grouped['total_raids'].replace(0, np.nan), 2)
    grouped['empty_raid_rate'] = np.round(100.0 * grouped['empty_raids'] / grouped['total_raids'].replace(0, np.nan), 2)
    grouped['tackle_success_rate'] = np.round(100.0 * grouped['successful_tackles'] / grouped['total_tackles'].replace(0, np.nan), 2)

    return grouped.sort_values(by=['win_percentage', 'wins'], ascending=[False, False]).reset_index(drop=True)


def calculate_player_summary_metrics(df_player_match: pd.DataFrame, min_matches: int = 10) -> pd.DataFrame:
    """
    Computes individual player performance summaries: raid strike rate,
    tackle strike rate, Super 10s, High 5s, and relative volatility.
    """
    df = df_player_match[df_player_match['played'] == True].copy()
    if 'is_official_pkl' in df.columns:
        df = df[df['is_official_pkl'] == True]

    agg = df.groupby(['player_id', 'player_name', 'player_role']).agg(
        appearances=('match_id', 'count'),
        total_points=('total_points', 'sum'),
        avg_points=('total_points', 'mean'),
        std_points=('total_points', 'std'),
        max_points=('total_points', 'max'),
        total_raid_points=('raid_points_total', 'sum'),
        touch_points=('raid_points_touch', 'sum'),
        bonus_points=('raid_points_bonus', 'sum'),
        total_raids=('raids_total', 'sum'),
        successful_raids=('raids_successful', 'sum'),
        super_10s=('super_10', 'sum'),
        total_tackle_points=('tackle_points_total', 'sum'),
        total_tackles=('tackles_total', 'sum'),
        successful_tackles=('tackles_successful', 'sum'),
        high_5s=('high_5', 'sum')
    ).reset_index()

    agg = agg[agg['appearances'] >= min_matches].copy()
    agg['raid_strike_rate'] = np.round(100.0 * agg['successful_raids'] / agg['total_raids'].replace(0, np.nan), 2)
    agg['tackle_strike_rate'] = np.round(100.0 * agg['successful_tackles'] / agg['total_tackles'].replace(0, np.nan), 2)
    agg['relative_volatility'] = np.round(agg['std_points'] / agg['avg_points'].replace(0, np.nan), 3)

    return agg.sort_values(by='total_points', ascending=False).reset_index(drop=True)


def calculate_match_margin_metrics(df_matches: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes winning margin distribution and clutch finishing statistics.
    """
    df = df_matches[df_matches['is_completed'] == True].copy()
    if 'is_official_pkl' in df.columns:
        df = df[df['is_official_pkl'] == True]

    margins = df['win_margin'].dropna()
    total = len(df)
    ties = (df['is_tie'] == True).sum()
    clutch_1_3 = ((margins >= 1) & (margins <= 3)).sum()
    close_4_7 = ((margins >= 4) & (margins <= 7)).sum()
    moderate_8_14 = ((margins >= 8) & (margins <= 14)).sum()
    blowout_15_plus = (margins >= 15).sum()

    return {
        "total_completed_matches": total,
        "mean_margin": round(float(margins.mean()), 2),
        "median_margin": float(margins.median()),
        "std_margin": round(float(margins.std()), 2),
        "max_margin": int(margins.max()),
        "ties_count": int(ties),
        "ties_pct": round(100.0 * ties / total, 2),
        "clutch_1_3_count": int(clutch_1_3),
        "clutch_1_3_pct": round(100.0 * clutch_1_3 / total, 2),
        "close_4_7_count": int(close_4_7),
        "close_4_7_pct": round(100.0 * close_4_7 / total, 2),
        "moderate_8_14_count": int(moderate_8_14),
        "moderate_8_14_pct": round(100.0 * moderate_8_14 / total, 2),
        "blowout_15_plus_count": int(blowout_15_plus),
        "blowout_15_plus_pct": round(100.0 * blowout_15_plus / total, 2),
    }


def calculate_event_summary_metrics(df_events: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes event distribution, clock timeline metrics, and playmaking frequency.
    """
    total_events = len(df_events)
    event_counts = df_events['event_type'].value_counts().to_dict()
    super_raids = int(df_events['is_super_raid'].sum())
    super_tackles = int(df_events['is_super_tackle'].sum())
    dod_raids = int(df_events['is_do_or_die'].sum())

    return {
        "total_recorded_events": total_events,
        "event_type_distribution": event_counts,
        "super_raids_total": super_raids,
        "super_tackles_total": super_tackles,
        "do_or_die_raids_total": dod_raids
    }


def calculate_head_to_head(df_team_match: pd.DataFrame, team1_id: int, team2_id: int) -> Dict[str, Any]:
    """
    Computes head-to-head match summary between two teams.
    """
    h2h = df_team_match[(df_team_match['team_id'] == team1_id) & (df_team_match['opponent_team_id'] == team2_id)].copy()
    if h2h.empty:
        return {"matches": 0, "team1_wins": 0, "team2_wins": 0, "ties": 0}

    t1_name = h2h['team_name'].iloc[0]
    t2_name = h2h['opponent_team_name'].iloc[0]
    t1_wins = (h2h['result'] == 'Win').sum()
    t2_wins = (h2h['result'] == 'Loss').sum()
    ties = (h2h['result'] == 'Tie').sum()

    return {
        "matches": len(h2h),
        "team1_id": team1_id,
        "team1_name": t1_name,
        "team2_id": team2_id,
        "team2_name": t2_name,
        "team1_wins": int(t1_wins),
        "team2_wins": int(t2_wins),
        "ties": int(ties),
        "team1_avg_score": round(float(h2h['score'].mean()), 1),
        "team2_avg_score": round(float(h2h['opponent_score'].mean()), 1),
        "recent_meetings": h2h[['match_date', 'score', 'opponent_score', 'result']].sort_values(by='match_date', ascending=False).to_dict('records')
    }
