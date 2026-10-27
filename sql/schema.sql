-- ============================================================================
-- Pro Kabaddi League (PKL) Analytics Platform
-- Relational Database DDL Schema (SQLite Compatible)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. Dimension: Seasons & Tournaments
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_seasons;
CREATE TABLE dim_seasons (
    series_id INTEGER PRIMARY KEY,
    season_id INTEGER,
    season_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    is_official_pkl BOOLEAN NOT NULL CHECK (is_official_pkl IN (0, 1))
);

-- ----------------------------------------------------------------------------
-- 2. Dimension: Teams
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_teams;
CREATE TABLE dim_teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    is_pkl_franchise BOOLEAN NOT NULL CHECK (is_pkl_franchise IN (0, 1)),
    franchise_era TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. Dimension: Venues
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_venues;
CREATE TABLE dim_venues (
    venue_id INTEGER PRIMARY KEY,
    venue_name TEXT NOT NULL,
    city TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 4. Dimension: Players Master Profile
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_players;
CREATE TABLE dim_players (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_short_name TEXT,
    primary_role TEXT NOT NULL,
    primary_skill TEXT,
    total_career_appearances INTEGER NOT NULL DEFAULT 0,
    total_career_points INTEGER NOT NULL DEFAULT 0,
    total_career_raid_points INTEGER NOT NULL DEFAULT 0,
    total_career_tackle_points INTEGER NOT NULL DEFAULT 0
);

-- ----------------------------------------------------------------------------
-- 5. Fact: Matches
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_matches;
CREATE TABLE fact_matches (
    match_id INTEGER PRIMARY KEY,
    match_number TEXT NOT NULL,
    series_id INTEGER NOT NULL,
    season_id INTEGER,
    season_name TEXT NOT NULL,
    is_official_pkl BOOLEAN NOT NULL CHECK (is_official_pkl IN (0, 1)),
    match_date DATE NOT NULL,
    start_time TEXT,
    venue_id INTEGER NOT NULL,
    venue_name TEXT NOT NULL,
    home_team_id INTEGER,
    home_team_name TEXT,
    toss_winner_id INTEGER NOT NULL,
    toss_selection TEXT,
    team_a_id INTEGER NOT NULL,
    team_a_name TEXT NOT NULL,
    team_a_score INTEGER NOT NULL,
    team_b_id INTEGER NOT NULL,
    team_b_name TEXT NOT NULL,
    team_b_score INTEGER NOT NULL,
    total_match_points INTEGER NOT NULL,
    win_margin INTEGER,
    winner_team_id INTEGER,
    winner_team_name TEXT,
    is_tie BOOLEAN NOT NULL CHECK (is_tie IN (0, 1)),
    player_of_the_match_id INTEGER,
    player_of_the_match_name TEXT,
    status TEXT NOT NULL,
    is_completed BOOLEAN NOT NULL CHECK (is_completed IN (0, 1)),
    raw_result_text TEXT,
    FOREIGN KEY (series_id) REFERENCES dim_seasons(series_id),
    FOREIGN KEY (venue_id) REFERENCES dim_venues(venue_id),
    FOREIGN KEY (team_a_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (team_b_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (winner_team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (toss_winner_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (player_of_the_match_id) REFERENCES dim_players(player_id)
);

-- ----------------------------------------------------------------------------
-- 6. Fact: Team Match Performance (Box Scores)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_team_match;
CREATE TABLE fact_team_match (
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    raid_points_total INTEGER NOT NULL,
    raid_points_touch INTEGER NOT NULL,
    raid_points_bonus INTEGER NOT NULL,
    tackle_points_total INTEGER NOT NULL,
    tackle_points_capture INTEGER NOT NULL,
    tackle_points_bonus INTEGER NOT NULL,
    all_out_points INTEGER NOT NULL,
    extra_points INTEGER NOT NULL,
    raids_total INTEGER NOT NULL,
    raids_successful INTEGER NOT NULL,
    raids_unsuccessful INTEGER NOT NULL,
    raids_empty INTEGER NOT NULL,
    super_raids INTEGER NOT NULL DEFAULT 0,
    tackles_total INTEGER NOT NULL,
    tackles_successful INTEGER NOT NULL,
    tackles_unsuccessful INTEGER NOT NULL,
    super_tackles INTEGER NOT NULL DEFAULT 0,
    all_outs_inflicted INTEGER NOT NULL DEFAULT 0,
    raid_success_rate REAL NOT NULL DEFAULT 0.0,
    tackle_success_rate REAL NOT NULL DEFAULT 0.0,
    match_date DATE NOT NULL,
    season_id INTEGER,
    is_official_pkl BOOLEAN NOT NULL CHECK (is_official_pkl IN (0, 1)),
    status TEXT NOT NULL,
    opponent_team_id INTEGER NOT NULL,
    opponent_team_name TEXT NOT NULL,
    opponent_score INTEGER NOT NULL,
    score_difference INTEGER NOT NULL,
    result TEXT NOT NULL,
    is_winner BOOLEAN NOT NULL CHECK (is_winner IN (0, 1)),
    PRIMARY KEY (match_id, team_id),
    FOREIGN KEY (match_id) REFERENCES fact_matches(match_id),
    FOREIGN KEY (team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (opponent_team_id) REFERENCES dim_teams(team_id)
);

-- ----------------------------------------------------------------------------
-- 7. Fact: Player Match Performance
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_player_match;
CREATE TABLE fact_player_match (
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    player_short_name TEXT,
    player_role TEXT,
    player_skill TEXT,
    played BOOLEAN NOT NULL CHECK (played IN (0, 1)),
    starter BOOLEAN NOT NULL CHECK (starter IN (0, 1)),
    captain BOOLEAN NOT NULL CHECK (captain IN (0, 1)),
    total_points INTEGER NOT NULL DEFAULT 0,
    raid_points_total INTEGER NOT NULL DEFAULT 0,
    raid_points_touch INTEGER NOT NULL DEFAULT 0,
    raid_points_bonus INTEGER NOT NULL DEFAULT 0,
    tackle_points_total INTEGER NOT NULL DEFAULT 0,
    tackle_points_touch INTEGER NOT NULL DEFAULT 0,
    tackle_points_capture_bonus INTEGER NOT NULL DEFAULT 0,
    raids_total INTEGER NOT NULL DEFAULT 0,
    raids_successful INTEGER NOT NULL DEFAULT 0,
    raids_unsuccessful INTEGER NOT NULL DEFAULT 0,
    raids_empty INTEGER NOT NULL DEFAULT 0,
    tackles_total INTEGER NOT NULL DEFAULT 0,
    tackles_successful INTEGER NOT NULL DEFAULT 0,
    tackles_unsuccessful INTEGER NOT NULL DEFAULT 0,
    green_cards INTEGER NOT NULL DEFAULT 0,
    yellow_cards INTEGER NOT NULL DEFAULT 0,
    red_cards INTEGER NOT NULL DEFAULT 0,
    super_10 BOOLEAN NOT NULL CHECK (super_10 IN (0, 1)),
    high_5 BOOLEAN NOT NULL CHECK (high_5 IN (0, 1)),
    season_id INTEGER,
    is_official_pkl BOOLEAN NOT NULL CHECK (is_official_pkl IN (0, 1)),
    match_date DATE NOT NULL,
    PRIMARY KEY (match_id, player_id),
    FOREIGN KEY (match_id) REFERENCES fact_matches(match_id),
    FOREIGN KEY (team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (player_id) REFERENCES dim_players(player_id)
);

-- ----------------------------------------------------------------------------
-- 8. Fact: Play-by-Play Match Events
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_events;
CREATE TABLE fact_events (
    event_row_id INTEGER PRIMARY KEY,
    event_type_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    event_no INTEGER NOT NULL,
    clock TEXT,
    elapsed_seconds INTEGER,
    event_type TEXT NOT NULL,
    event_text TEXT,
    raiding_team_id INTEGER,
    defending_team_id INTEGER,
    raider_id INTEGER,
    defender_id INTEGER,
    raid_points INTEGER NOT NULL DEFAULT 0,
    defending_points INTEGER NOT NULL DEFAULT 0,
    score_team_a INTEGER NOT NULL DEFAULT 0,
    score_team_b INTEGER NOT NULL DEFAULT 0,
    score_difference INTEGER,
    is_super_raid BOOLEAN NOT NULL CHECK (is_super_raid IN (0, 1)),
    is_super_tackle BOOLEAN NOT NULL CHECK (is_super_tackle IN (0, 1)),
    is_do_or_die BOOLEAN NOT NULL CHECK (is_do_or_die IN (0, 1)),
    FOREIGN KEY (match_id) REFERENCES fact_matches(match_id),
    FOREIGN KEY (raiding_team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (defending_team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (raider_id) REFERENCES dim_players(player_id),
    FOREIGN KEY (defender_id) REFERENCES dim_players(player_id)
);

-- ----------------------------------------------------------------------------
-- Performance Indexes for Analytical Queries
-- ----------------------------------------------------------------------------
CREATE INDEX idx_matches_date ON fact_matches(match_date);
CREATE INDEX idx_matches_season ON fact_matches(season_id);
CREATE INDEX idx_matches_official ON fact_matches(is_official_pkl);
CREATE INDEX idx_matches_winner ON fact_matches(winner_team_id);
CREATE INDEX idx_matches_venue ON fact_matches(venue_id);

CREATE INDEX idx_tm_match ON fact_team_match(match_id);
CREATE INDEX idx_tm_team ON fact_team_match(team_id);
CREATE INDEX idx_tm_season ON fact_team_match(season_id);
CREATE INDEX idx_tm_date ON fact_team_match(match_date);
CREATE INDEX idx_tm_result ON fact_team_match(result);

CREATE INDEX idx_pm_match ON fact_player_match(match_id);
CREATE INDEX idx_pm_player ON fact_player_match(player_id);
CREATE INDEX idx_pm_team ON fact_player_match(team_id);
CREATE INDEX idx_pm_season ON fact_player_match(season_id);
CREATE INDEX idx_pm_played ON fact_player_match(played);

CREATE INDEX idx_events_match ON fact_events(match_id);
CREATE INDEX idx_events_event_no ON fact_events(match_id, event_no);
CREATE INDEX idx_events_raider ON fact_events(raider_id);
CREATE INDEX idx_events_defender ON fact_events(defender_id);
CREATE INDEX idx_events_type ON fact_events(event_type);
