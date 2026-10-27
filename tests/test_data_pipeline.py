"""
tests/test_data_pipeline.py
---------------------------
Pytest automated validation suite for the PKL Analytics Platform data pipeline.
"""

import os
import pytest
import pandas as pd
import numpy as np


@pytest.fixture(scope="module")
def processed_data():
    """Fixture to load all processed parquet tables."""
    processed_dir = "data/processed"
    tables = {}
    table_names = [
        "dim_seasons", "dim_teams", "dim_venues", "dim_players",
        "fact_matches", "fact_team_match", "fact_player_match", "fact_events"
    ]
    for name in table_names:
        pq_path = os.path.join(processed_dir, f"{name}.parquet")
        assert os.path.exists(pq_path), f"Processed parquet {pq_path} missing!"
        tables[name] = pd.read_parquet(pq_path)
    return tables


def test_primary_key_uniqueness(processed_data):
    """Asserts that all primary keys are strictly unique and non-null."""
    dim_teams = processed_data["dim_teams"]
    dim_venues = processed_data["dim_venues"]
    dim_players = processed_data["dim_players"]
    fact_matches = processed_data["fact_matches"]
    fact_team_match = processed_data["fact_team_match"]
    fact_player_match = processed_data["fact_player_match"]

    # Dimension PKs
    assert dim_teams["team_id"].is_unique
    assert not dim_teams["team_id"].isnull().any()

    assert dim_venues["venue_id"].is_unique
    assert not dim_venues["venue_id"].isnull().any()

    assert dim_players["player_id"].is_unique
    assert not dim_players["player_id"].isnull().any()

    # Fact PKs
    assert fact_matches["match_id"].is_unique
    assert not fact_matches["match_id"].isnull().any()
    assert len(fact_matches) == 684

    # Composite PKs
    assert not fact_team_match.duplicated(subset=["match_id", "team_id"]).any()
    assert len(fact_team_match) == 1368

    assert not fact_player_match.duplicated(subset=["match_id", "player_id"]).any()
    assert len(fact_player_match) == 16892


def test_referential_integrity(processed_data):
    """Asserts that foreign key relationships between facts and dimensions hold."""
    dim_teams = processed_data["dim_teams"]
    dim_venues = processed_data["dim_venues"]
    dim_players = processed_data["dim_players"]
    fact_matches = processed_data["fact_matches"]
    fact_team_match = processed_data["fact_team_match"]
    fact_player_match = processed_data["fact_player_match"]

    valid_team_ids = set(dim_teams["team_id"])
    valid_venue_ids = set(dim_venues["venue_id"])
    valid_match_ids = set(fact_matches["match_id"])
    valid_player_ids = set(dim_players["player_id"])

    # fact_matches FKs
    assert set(fact_matches["venue_id"]).issubset(valid_venue_ids)
    assert set(fact_matches["team_a_id"]).issubset(valid_team_ids)
    assert set(fact_matches["team_b_id"]).issubset(valid_team_ids)

    # fact_team_match FKs
    assert set(fact_team_match["match_id"]).issubset(valid_match_ids)
    assert set(fact_team_match["team_id"]).issubset(valid_team_ids)
    assert set(fact_team_match["opponent_team_id"]).issubset(valid_team_ids)

    # fact_player_match FKs
    assert set(fact_player_match["match_id"]).issubset(valid_match_ids)
    assert set(fact_player_match["team_id"]).issubset(valid_team_ids)
    assert set(fact_player_match["player_id"]).issubset(valid_player_ids)


def test_team_score_reconciliation(processed_data):
    """Asserts that team score decomposition strictly equals the sum of its 4 components."""
    fact_team_match = processed_data["fact_team_match"]
    calculated_score = (
        fact_team_match["raid_points_total"] +
        fact_team_match["tackle_points_total"] +
        fact_team_match["all_out_points"] +
        fact_team_match["extra_points"]
    )
    score_discrepancies = (fact_team_match["score"] - calculated_score).abs().sum()
    assert score_discrepancies == 0, f"Score decomposition failed: {score_discrepancies}"


def test_player_of_the_match_resolution(processed_data):
    """Asserts that the raw data anomaly in player_name_of_the_match is resolved."""
    fact_matches = processed_data["fact_matches"]
    potm_matches = fact_matches[fact_matches["player_of_the_match_id"].notnull()]
    assert len(potm_matches) == 575
    # Every non-null POTM ID must map to a non-null string name
    assert potm_matches["player_of_the_match_name"].notnull().all()
    # Check that POTM names are not numeric strings
    for name in potm_matches["player_of_the_match_name"].head(20):
        assert not name.replace(".", "").isdigit(), f"Name appears to be numeric ID: {name}"


def test_date_and_chronology(processed_data):
    """Asserts that dates are ISO formatted and chronological."""
    fact_matches = processed_data["fact_matches"]
    # Check format YYYY-MM-DD
    assert fact_matches["match_date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    dates = pd.to_datetime(fact_matches["match_date"])
    assert dates.min() == pd.Timestamp("2014-07-26")
    assert dates.max() == pd.Timestamp("2019-09-12")


def test_event_timeline_integrity(processed_data):
    """Asserts that event timeline clock has been converted to valid elapsed seconds."""
    fact_events = processed_data["fact_events"]
    assert len(fact_events) == 66568
    assert fact_events["elapsed_seconds"].notnull().all()
    assert (fact_events["elapsed_seconds"] >= 0).all()
