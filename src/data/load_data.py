"""
src/data/load_data.py
---------------------
Robust data loading utilities for raw PKL tabular CSVs, JSON match timelines,
and seasonal summary statistics.
"""

import os
import glob
import json
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_raw_data_dir() -> str:
    """
    Locates the raw data directory.
    Checks `data/raw`, then falls back to current workspace root if raw files are present there.
    """
    candidates = [
        os.path.join(os.getcwd(), "data", "raw"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "raw"),
        os.getcwd()
    ]
    for candidate in candidates:
        if os.path.exists(os.path.join(candidate, "DS_match.csv")):
            return candidate
    return os.getcwd()


def get_match_json_dir() -> str:
    """
    Locates the Match_Data JSON directory.
    """
    candidates = [
        os.path.join(get_raw_data_dir(), "Data", "Data", "Match_Data"),
        os.path.join(get_raw_data_dir(), "Data", "Match_Data"),
        os.path.join(os.getcwd(), "Data", "Data", "Match_Data"),
        os.path.join(os.getcwd(), "Data", "Match_Data")
    ]
    for candidate in candidates:
        if os.path.exists(candidate) and len(glob.glob(os.path.join(candidate, "*.json"))) > 0:
            return candidate
    return os.path.join(os.getcwd(), "Data", "Data", "Match_Data")


def load_raw_matches() -> pd.DataFrame:
    """Loads DS_match.csv into a pandas DataFrame."""
    path = os.path.join(get_raw_data_dir(), "DS_match.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Matches CSV not found at {path}")
    logger.info(f"Loading raw matches from {path}")
    df = pd.read_csv(path)
    return df


def load_raw_teams() -> pd.DataFrame:
    """Loads DS_team.csv into a pandas DataFrame."""
    path = os.path.join(get_raw_data_dir(), "DS_team.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Teams CSV not found at {path}")
    logger.info(f"Loading raw teams from {path}")
    df = pd.read_csv(path)
    return df


def load_raw_players() -> pd.DataFrame:
    """Loads DS_players.csv into a pandas DataFrame."""
    path = os.path.join(get_raw_data_dir(), "DS_players.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Players CSV not found at {path}")
    logger.info(f"Loading raw players from {path}")
    df = pd.read_csv(path)
    return df


def load_raw_events() -> pd.DataFrame:
    """Loads DS_events.csv into a pandas DataFrame."""
    path = os.path.join(get_raw_data_dir(), "DS_events.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Events CSV not found at {path}")
    logger.info(f"Loading raw events from {path}")
    df = pd.read_csv(path, low_memory=False)
    return df


def load_match_json(match_id: int) -> Optional[Dict[str, Any]]:
    """Loads a single match JSON timeline by match_id."""
    json_dir = get_match_json_dir()
    path = os.path.join(json_dir, f"{match_id}.json")
    if not os.path.exists(path):
        logger.warning(f"Match JSON {path} does not exist.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_available_match_ids() -> List[int]:
    """Returns a sorted list of all match IDs available in Match_Data."""
    json_dir = get_match_json_dir()
    files = glob.glob(os.path.join(json_dir, "*.json"))
    match_ids = []
    for f in files:
        base = os.path.basename(f).replace(".json", "")
        if base.isdigit():
            match_ids.append(int(base))
    return sorted(match_ids)
