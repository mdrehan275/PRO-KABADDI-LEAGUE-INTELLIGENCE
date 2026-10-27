-- ============================================================================
-- Pro Kabaddi League (PKL) Analytics Platform
-- Comprehensive Analytical SQL Queries Suite (22 Advanced Queries)
-- Demonstrating Joins, Window Functions, CTEs, Conditional Aggregation, and Rankings
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Total Matches and Completed Matches by Season and Tournament
-- Business Question: How has the PKL tournament expanded over time in match volume,
-- and what is the breakdown between official PKL seasons and external/testing tournaments?
-- ----------------------------------------------------------------------------
-- QUERY_1_START
SELECT 
    s.series_id,
    s.season_name,
    s.year,
    s.is_official_pkl,
    COUNT(m.match_id) AS total_fixtures,
    SUM(CASE WHEN m.is_completed = 1 THEN 1 ELSE 0 END) AS completed_matches,
    SUM(CASE WHEN m.is_tie = 1 THEN 1 ELSE 0 END) AS tied_matches,
    MIN(m.match_date) AS season_start_date,
    MAX(m.match_date) AS season_end_date,
    ROUND(AVG(CASE WHEN m.is_completed = 1 THEN m.total_match_points ELSE NULL END), 1) AS avg_match_total_points
FROM dim_seasons s
LEFT JOIN fact_matches m ON s.series_id = m.series_id
GROUP BY s.series_id, s.season_name, s.year, s.is_official_pkl
ORDER BY s.is_official_pkl DESC, s.year ASC, s.series_id ASC;
-- QUERY_1_END

-- ----------------------------------------------------------------------------
-- Query 2: Team Win Counts, Losses, Ties, and Win Percentages (Official PKL)
-- Business Question: What are the all-time win-loss-draw records and win percentages
-- of official PKL franchises across all completed league matches?
-- ----------------------------------------------------------------------------
-- QUERY_2_START
SELECT 
    t.team_id,
    t.team_name,
    t.short_name,
    t.franchise_era,
    COUNT(tm.match_id) AS matches_played,
    SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN tm.result = 'Loss' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN tm.result = 'Tie' THEN 1 ELSE 0 END) AS ties,
    ROUND(100.0 * SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) / COUNT(tm.match_id), 2) AS win_percentage,
    ROUND(AVG(tm.score), 1) AS avg_points_scored,
    ROUND(AVG(tm.opponent_score), 1) AS avg_points_conceded,
    SUM(tm.score_difference) AS cumulative_point_differential
FROM dim_teams t
JOIN fact_team_match tm ON t.team_id = tm.team_id
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY t.team_id, t.team_name, t.short_name, t.franchise_era
ORDER BY win_percentage DESC, wins DESC;
-- QUERY_2_END

-- ----------------------------------------------------------------------------
-- Query 3: Top 10 Highest-Scoring Matches in PKL History
-- Business Question: What are the highest aggregate scoring matches in PKL history,
-- which teams participated, and at which venues were they contested?
-- ----------------------------------------------------------------------------
-- QUERY_3_START
SELECT 
    m.match_id,
    m.season_name,
    m.match_date,
    m.venue_name,
    m.team_a_name,
    m.team_a_score,
    m.team_b_name,
    m.team_b_score,
    m.total_match_points,
    m.winner_team_name,
    m.win_margin
FROM fact_matches m
WHERE m.is_official_pkl = 1 AND m.is_completed = 1
ORDER BY m.total_match_points DESC
LIMIT 10;
-- QUERY_3_END

-- ----------------------------------------------------------------------------
-- Query 4: Average Team Score and Points Distribution by PKL Season
-- Business Question: How has scoring per match evolved across PKL Seasons 1 through 7?
-- Are modern matches higher scoring than inaugural seasons?
-- ----------------------------------------------------------------------------
-- QUERY_4_START
SELECT 
    tm.season_id,
    'Season ' || tm.season_id AS season_label,
    COUNT(DISTINCT tm.match_id) AS total_matches,
    ROUND(AVG(tm.score), 2) AS avg_team_score,
    MIN(tm.score) AS min_team_score,
    MAX(tm.score) AS max_team_score,
    ROUND(AVG(tm.raid_points_total), 2) AS avg_raid_points,
    ROUND(AVG(tm.tackle_points_total), 2) AS avg_tackle_points,
    ROUND(AVG(tm.all_out_points), 2) AS avg_all_out_points,
    ROUND(AVG(tm.extra_points), 2) AS avg_extra_points
FROM fact_team_match tm
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY tm.season_id
ORDER BY tm.season_id ASC;
-- QUERY_4_END

-- ----------------------------------------------------------------------------
-- Query 5: All-Time Top 15 Highest-Performing Raiders
-- Business Question: Who are the most prolific raiders in PKL history by total raid
-- points, touch points, bonus points, Super 10s, and raid strike rate?
-- ----------------------------------------------------------------------------
-- QUERY_5_START
SELECT 
    p.player_id,
    p.player_name,
    p.primary_role,
    COUNT(DISTINCT pm.match_id) AS appearances,
    SUM(pm.raid_points_total) AS total_raid_points,
    SUM(pm.raid_points_touch) AS touch_points,
    SUM(pm.raid_points_bonus) AS bonus_points,
    SUM(pm.raids_total) AS raids_attempted,
    SUM(pm.raids_successful) AS successful_raids,
    ROUND(100.0 * SUM(pm.raids_successful) / NULLIF(SUM(pm.raids_total), 0), 2) AS raid_success_pct,
    ROUND(1.0 * SUM(pm.raid_points_total) / COUNT(DISTINCT pm.match_id), 2) AS raid_points_per_match,
    SUM(CASE WHEN pm.super_10 = 1 THEN 1 ELSE 0 END) AS total_super_10s
FROM dim_players p
JOIN fact_player_match pm ON p.player_id = pm.player_id
WHERE pm.is_official_pkl = 1 AND pm.played = 1
GROUP BY p.player_id, p.player_name, p.primary_role
HAVING COUNT(DISTINCT pm.match_id) >= 15
ORDER BY total_raid_points DESC
LIMIT 15;
-- QUERY_5_END

-- ----------------------------------------------------------------------------
-- Query 6: All-Time Top 15 Highest-Performing Defenders
-- Business Question: Who are the premier defensive anchors in PKL history by tackle
-- points, tackle success percentage, super tackles, and High 5s?
-- ----------------------------------------------------------------------------
-- QUERY_6_START
SELECT 
    p.player_id,
    p.player_name,
    p.primary_role,
    p.primary_skill,
    COUNT(DISTINCT pm.match_id) AS appearances,
    SUM(pm.tackle_points_total) AS total_tackle_points,
    SUM(pm.tackles_total) AS tackles_attempted,
    SUM(pm.tackles_successful) AS successful_tackles,
    ROUND(100.0 * SUM(pm.tackles_successful) / NULLIF(SUM(pm.tackles_total), 0), 2) AS tackle_success_pct,
    ROUND(1.0 * SUM(pm.tackle_points_total) / COUNT(DISTINCT pm.match_id), 2) AS tackle_points_per_match,
    SUM(CASE WHEN pm.high_5 = 1 THEN 1 ELSE 0 END) AS total_high_5s
FROM dim_players p
JOIN fact_player_match pm ON p.player_id = pm.player_id
WHERE pm.is_official_pkl = 1 AND pm.played = 1
GROUP BY p.player_id, p.player_name, p.primary_role, p.primary_skill
HAVING COUNT(DISTINCT pm.match_id) >= 15
ORDER BY total_tackle_points DESC
LIMIT 15;
-- QUERY_6_END

-- ----------------------------------------------------------------------------
-- Query 7: Player Rankings using RANK() and DENSE_RANK() by Tactical Role
-- Business Question: How do players rank within their primary role ('Raider' vs 'Defender')
-- when comparing total points scored using both RANK() and DENSE_RANK()?
-- ----------------------------------------------------------------------------
-- QUERY_7_START
WITH role_aggregates AS (
    SELECT 
        p.player_id,
        p.player_name,
        p.primary_role,
        COUNT(DISTINCT pm.match_id) AS appearances,
        SUM(pm.total_points) AS career_points
    FROM dim_players p
    JOIN fact_player_match pm ON p.player_id = pm.player_id
    WHERE pm.is_official_pkl = 1 AND pm.played = 1 AND p.primary_role IN ('Raider', 'Defender')
    GROUP BY p.player_id, p.player_name, p.primary_role
    HAVING COUNT(DISTINCT pm.match_id) >= 10
)
SELECT 
    primary_role,
    player_name,
    appearances,
    career_points,
    RANK() OVER (PARTITION BY primary_role ORDER BY career_points DESC) AS role_rank,
    DENSE_RANK() OVER (PARTITION BY primary_role ORDER BY career_points DESC) AS role_dense_rank
FROM role_aggregates
ORDER BY primary_role, role_rank ASC
LIMIT 30;
-- QUERY_7_END

-- ----------------------------------------------------------------------------
-- Query 8: Top Scorer in Each PKL Season (Using CTE and ROW_NUMBER)
-- Business Question: Who was the MVP individual points leader for each PKL season
-- from Season 1 to Season 7, and what was their scoring tally?
-- ----------------------------------------------------------------------------
-- QUERY_8_START
WITH season_player_points AS (
    SELECT 
        pm.season_id,
        'Season ' || pm.season_id AS season_name,
        p.player_id,
        p.player_name,
        p.primary_role,
        COUNT(DISTINCT pm.match_id) AS matches_played,
        SUM(pm.total_points) AS season_total_points,
        SUM(pm.raid_points_total) AS season_raid_points,
        SUM(pm.tackle_points_total) AS season_tackle_points,
        ROW_NUMBER() OVER (PARTITION BY pm.season_id ORDER BY SUM(pm.total_points) DESC) AS season_rank
    FROM fact_player_match pm
    JOIN dim_players p ON pm.player_id = p.player_id
    WHERE pm.is_official_pkl = 1 AND pm.season_id IS NOT NULL AND pm.played = 1
    GROUP BY pm.season_id, p.player_id, p.player_name, p.primary_role
)
SELECT 
    season_id,
    season_name,
    player_name,
    primary_role,
    matches_played,
    season_total_points,
    season_raid_points,
    season_tackle_points,
    ROUND(1.0 * season_total_points / matches_played, 2) AS points_per_match
FROM season_player_points
WHERE season_rank = 1
ORDER BY season_id ASC;
-- QUERY_8_END

-- ----------------------------------------------------------------------------
-- Query 9: Team Win Rates by Venue & Stadium Fortress Analysis
-- Business Question: What are the most dominant team-venue combinations in PKL history?
-- Which teams have established true home fortresses?
-- ----------------------------------------------------------------------------
-- QUERY_9_START
SELECT 
    t.team_name,
    v.venue_name,
    v.city,
    COUNT(tm.match_id) AS matches_at_venue,
    SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN tm.result = 'Loss' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN tm.result = 'Tie' THEN 1 ELSE 0 END) AS ties,
    ROUND(100.0 * SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) / COUNT(tm.match_id), 1) AS venue_win_pct,
    ROUND(AVG(tm.score), 1) AS avg_score_at_venue
FROM fact_team_match tm
JOIN dim_teams t ON tm.team_id = t.team_id
JOIN fact_matches m ON tm.match_id = m.match_id
JOIN dim_venues v ON m.venue_id = v.venue_id
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY t.team_name, v.venue_name, v.city
HAVING COUNT(tm.match_id) >= 8
ORDER BY venue_win_pct DESC, matches_at_venue DESC
LIMIT 15;
-- QUERY_9_END

-- ----------------------------------------------------------------------------
-- Query 10: Toss Outcome vs Match Outcome Analysis
-- Business Question: Does winning the pre-match coin toss provide a statistically
-- detectable advantage in match victory, and does choice of court vs raid matter?
-- ----------------------------------------------------------------------------
-- QUERY_10_START
SELECT 
    m.toss_selection,
    COUNT(m.match_id) AS total_matches,
    SUM(CASE WHEN m.toss_winner_id = m.winner_team_id THEN 1 ELSE 0 END) AS toss_winner_won_match,
    SUM(CASE WHEN m.winner_team_id IS NOT NULL AND m.toss_winner_id != m.winner_team_id THEN 1 ELSE 0 END) AS toss_winner_lost_match,
    SUM(CASE WHEN m.is_tie = 1 THEN 1 ELSE 0 END) AS tied_matches,
    ROUND(100.0 * SUM(CASE WHEN m.toss_winner_id = m.winner_team_id THEN 1 ELSE 0 END) / COUNT(m.match_id), 2) AS toss_winner_win_pct
FROM fact_matches m
WHERE m.is_official_pkl = 1 AND m.is_completed = 1 AND m.toss_selection IS NOT NULL
GROUP BY m.toss_selection
ORDER BY total_matches DESC;
-- QUERY_10_END

-- ----------------------------------------------------------------------------
-- Query 11: Leading Player Point Contribution to Team Total (Granularity-Safe Join)
-- Business Question: In which matches did a single star player carry the highest
-- percentage burden of their team's entire score?
-- ----------------------------------------------------------------------------
-- QUERY_11_START
WITH top_match_scorers AS (
    SELECT 
        pm.match_id,
        pm.team_id,
        pm.player_id,
        pm.player_name,
        pm.total_points AS player_points,
        ROW_NUMBER() OVER (PARTITION BY pm.match_id, pm.team_id ORDER BY pm.total_points DESC) AS scorer_rank
    FROM fact_player_match pm
    WHERE pm.is_official_pkl = 1 AND pm.played = 1
)
SELECT 
    m.match_date,
    tm.team_name,
    tms.player_name AS star_player,
    tms.player_points,
    tm.score AS team_total_score,
    ROUND(100.0 * tms.player_points / NULLIF(tm.score, 0), 2) AS player_point_share_pct,
    tm.result AS match_result
FROM top_match_scorers tms
JOIN fact_team_match tm ON tms.match_id = tm.match_id AND tms.team_id = tm.team_id
JOIN fact_matches m ON tm.match_id = m.match_id
WHERE tms.scorer_rank = 1 AND tm.is_official_pkl = 1 AND tm.status = 'Full Time' AND tm.score >= 25
ORDER BY player_point_share_pct DESC
LIMIT 15;
-- QUERY_11_END

-- ----------------------------------------------------------------------------
-- Query 12: Team Successful Raid Percentages & Offensive Breakdown
-- Business Question: Which teams executed the most efficient offensive raiding strategies,
-- maintaining the highest successful raid % while minimizing empty raids?
-- ----------------------------------------------------------------------------
-- QUERY_12_START
SELECT 
    t.team_name,
    COUNT(tm.match_id) AS total_matches,
    SUM(tm.raids_total) AS total_raids,
    SUM(tm.raids_successful) AS successful_raids,
    SUM(tm.raids_unsuccessful) AS unsuccessful_raids,
    SUM(tm.raids_empty) AS empty_raids,
    ROUND(100.0 * SUM(tm.raids_successful) / SUM(tm.raids_total), 2) AS successful_raid_pct,
    ROUND(100.0 * SUM(tm.raids_empty) / SUM(tm.raids_total), 2) AS empty_raid_pct,
    ROUND(100.0 * SUM(tm.raids_unsuccessful) / SUM(tm.raids_total), 2) AS unsuccessful_raid_pct,
    ROUND(1.0 * SUM(tm.raid_points_total) / COUNT(tm.match_id), 2) AS avg_raid_points_per_match
FROM fact_team_match tm
JOIN dim_teams t ON tm.team_id = t.team_id
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY t.team_name
ORDER BY successful_raid_pct DESC;
-- QUERY_12_END

-- ----------------------------------------------------------------------------
-- Query 13: Team Defensive Tackle Success Rates & Super Tackle Production
-- Business Question: Which franchises fielded the stingiest defenses in terms of
-- tackle success percentage and super tackle generation?
-- ----------------------------------------------------------------------------
-- QUERY_13_START
SELECT 
    t.team_name,
    COUNT(tm.match_id) AS total_matches,
    SUM(tm.tackles_total) AS total_tackle_attempts,
    SUM(tm.tackles_successful) AS successful_tackles,
    SUM(tm.tackles_unsuccessful) AS failed_tackles,
    ROUND(100.0 * SUM(tm.tackles_successful) / SUM(tm.tackles_total), 2) AS tackle_success_pct,
    SUM(tm.super_tackles) AS total_super_tackles,
    ROUND(1.0 * SUM(tm.tackle_points_total) / COUNT(tm.match_id), 2) AS avg_tackle_points_per_match
FROM fact_team_match tm
JOIN dim_teams t ON tm.team_id = t.team_id
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY t.team_name
ORDER BY tackle_success_pct DESC;
-- QUERY_13_END

-- ----------------------------------------------------------------------------
-- Query 14: Super Raid and Super Tackle Frequency by Season
-- Business Question: How has the frequency of explosive match plays (Super Raids and
-- Super Tackles) evolved across PKL seasons?
-- ----------------------------------------------------------------------------
-- QUERY_14_START
SELECT 
    tm.season_id,
    'Season ' || tm.season_id AS season_name,
    COUNT(DISTINCT tm.match_id) AS total_matches,
    SUM(tm.super_raids) AS total_super_raids,
    ROUND(1.0 * SUM(tm.super_raids) / COUNT(DISTINCT tm.match_id), 2) AS super_raids_per_match,
    SUM(tm.super_tackles) AS total_super_tackles,
    ROUND(1.0 * SUM(tm.super_tackles) / COUNT(DISTINCT tm.match_id), 2) AS super_tackles_per_match,
    SUM(tm.all_outs_inflicted) AS total_all_outs,
    ROUND(1.0 * SUM(tm.all_outs_inflicted) / COUNT(DISTINCT tm.match_id), 2) AS all_outs_per_match
FROM fact_team_match tm
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY tm.season_id
ORDER BY tm.season_id ASC;
-- QUERY_14_END

-- ----------------------------------------------------------------------------
-- Query 15: Match Outcomes Segmented by Score Margin (Clutch vs Blowout)
-- Business Question: What proportion of PKL matches are decided in nail-biting clutch
-- scenarios (1-3 pts) versus comfortable or blowout margins (15+ pts)?
-- ----------------------------------------------------------------------------
-- QUERY_15_START
WITH margin_binned AS (
    SELECT 
        match_id,
        season_id,
        win_margin,
        is_tie,
        CASE 
            WHEN is_tie = 1 THEN 'Tie (0 pts)'
            WHEN win_margin BETWEEN 1 AND 3 THEN 'Clutch (1-3 pts)'
            WHEN win_margin BETWEEN 4 AND 7 THEN 'Close (4-7 pts)'
            WHEN win_margin BETWEEN 8 AND 14 THEN 'Moderate (8-14 pts)'
            ELSE 'Blowout (15+ pts)'
        END AS margin_category
    FROM fact_matches
    WHERE is_official_pkl = 1 AND is_completed = 1
)
SELECT 
    margin_category,
    COUNT(match_id) AS match_count,
    ROUND(100.0 * COUNT(match_id) / (SELECT COUNT(*) FROM margin_binned), 2) AS pct_of_total_matches,
    ROUND(AVG(win_margin), 1) AS avg_margin_in_bracket
FROM margin_binned
GROUP BY margin_category
ORDER BY 
    CASE margin_category
        WHEN 'Tie (0 pts)' THEN 1
        WHEN 'Clutch (1-3 pts)' THEN 2
        WHEN 'Close (4-7 pts)' THEN 3
        WHEN 'Moderate (8-14 pts)' THEN 4
        ELSE 5
    END;
-- QUERY_15_END

-- ----------------------------------------------------------------------------
-- Query 16: Season-over-Season Performance Evolution (LAG Window Function)
-- Business Question: How did each franchise's win percentage change year-over-year
-- between consecutive seasons?
-- ----------------------------------------------------------------------------
-- QUERY_16_START
WITH team_season_perf AS (
    SELECT 
        tm.team_id,
        tm.team_name,
        tm.season_id,
        COUNT(tm.match_id) AS matches_played,
        SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) AS wins,
        ROUND(100.0 * SUM(CASE WHEN tm.result = 'Win' THEN 1 ELSE 0 END) / COUNT(tm.match_id), 2) AS win_pct,
        ROUND(AVG(tm.score), 1) AS avg_score
    FROM fact_team_match tm
    WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time' AND tm.season_id IS NOT NULL
    GROUP BY tm.team_id, tm.team_name, tm.season_id
)
SELECT 
    team_name,
    season_id,
    matches_played,
    wins,
    win_pct,
    LAG(win_pct) OVER (PARTITION BY team_id ORDER BY season_id) AS prev_season_win_pct,
    ROUND(win_pct - LAG(win_pct) OVER (PARTITION BY team_id ORDER BY season_id), 2) AS yoy_win_pct_change,
    avg_score,
    ROUND(avg_score - LAG(avg_score) OVER (PARTITION BY team_id ORDER BY season_id), 2) AS yoy_avg_score_change
FROM team_season_perf
ORDER BY team_name, season_id ASC;
-- QUERY_16_END

-- ----------------------------------------------------------------------------
-- Query 17: Rolling 5-Match Player Performance (Pre-Match Form Feature)
-- Business Question: How can we compute rolling 5-match form for raiders chronologically
-- to build leak-free pre-match predictive features?
-- ----------------------------------------------------------------------------
-- QUERY_17_START
WITH player_chronological AS (
    SELECT 
        pm.player_id,
        pm.player_name,
        pm.match_id,
        pm.match_date,
        pm.total_points,
        pm.raid_points_total,
        pm.tackle_points_total,
        ROW_NUMBER() OVER (PARTITION BY pm.player_id ORDER BY pm.match_date, pm.match_id) AS appearance_seq
    FROM fact_player_match pm
    WHERE pm.is_official_pkl = 1 AND pm.played = 1
)
SELECT 
    player_id,
    player_name,
    match_id,
    match_date,
    appearance_seq,
    total_points,
    ROUND(AVG(total_points) OVER (
        PARTITION BY player_id 
        ORDER BY match_date, match_id 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_5_match_avg_points,
    ROUND(AVG(raid_points_total) OVER (
        PARTITION BY player_id 
        ORDER BY match_date, match_id 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_5_match_avg_raid_pts
FROM player_chronological
WHERE player_id IN (12, 29, 58)  -- Sample showcase: Anup Kumar, Jang Kun Lee, Kashiling Adake
ORDER BY player_id, appearance_seq ASC
LIMIT 30;
-- QUERY_17_END

-- ----------------------------------------------------------------------------
-- Query 18: Team Cumulative Form & Running Goal Differential via Window Functions
-- Business Question: What was each team's progressive cumulative points scored and
-- running score differential within each season?
-- ----------------------------------------------------------------------------
-- QUERY_18_START
SELECT 
    tm.match_id,
    tm.season_id,
    tm.match_date,
    tm.team_name,
    tm.score,
    tm.opponent_score,
    tm.score_difference,
    tm.result,
    SUM(tm.score) OVER (
        PARTITION BY tm.team_id, tm.season_id 
        ORDER BY tm.match_date, tm.match_id
    ) AS cumulative_points_scored,
    SUM(tm.score_difference) OVER (
        PARTITION BY tm.team_id, tm.season_id 
        ORDER BY tm.match_date, tm.match_id
    ) AS cumulative_differential,
    ROW_NUMBER() OVER (
        PARTITION BY tm.team_id, tm.season_id 
        ORDER BY tm.match_date, tm.match_id
    ) AS match_number_in_season
FROM fact_team_match tm
WHERE tm.is_official_pkl = 1 AND tm.season_id = 1 AND tm.team_id IN (3, 5) -- Jaipur vs U Mumba in S1
ORDER BY tm.team_id, match_number_in_season ASC;
-- QUERY_18_END

-- ----------------------------------------------------------------------------
-- Query 19: Player Consistency Analysis: Standard Deviation & Low Variance Anchors
-- Business Question: Which players deliver the most reliable, low-variance scoring
-- across multiple matches (identifying dependable anchors vs volatile swing players)?
-- ----------------------------------------------------------------------------
-- QUERY_19_START
WITH player_stats AS (
    SELECT 
        p.player_id,
        p.player_name,
        p.primary_role,
        COUNT(pm.match_id) AS matches_played,
        ROUND(AVG(pm.total_points), 2) AS avg_points,
        MIN(pm.total_points) AS min_points,
        MAX(pm.total_points) AS max_points
    FROM fact_player_match pm
    JOIN dim_players p ON pm.player_id = p.player_id
    WHERE pm.is_official_pkl = 1 AND pm.played = 1
    GROUP BY p.player_id, p.player_name, p.primary_role
    HAVING COUNT(pm.match_id) >= 25 AND AVG(pm.total_points) >= 5.0
)
SELECT 
    player_id,
    player_name,
    primary_role,
    matches_played,
    avg_points,
    min_points,
    max_points,
    ROUND(max_points - min_points, 1) AS scoring_range,
    ROUND(1.0 * (max_points - min_points) / avg_points, 2) AS relative_volatility_index
FROM player_stats
ORDER BY avg_points DESC, relative_volatility_index ASC
LIMIT 15;
-- QUERY_19_END

-- ----------------------------------------------------------------------------
-- Query 20: Match-Level Chronological Feature Aggregation from Events
-- Business Question: Reconstruct match dynamics from granular event streams:
-- score at 10-minute mark, score at 20-minute half-time mark, and total cards.
-- ----------------------------------------------------------------------------
-- QUERY_20_START
WITH event_halves AS (
    SELECT 
        e.match_id,
        SUM(CASE WHEN e.elapsed_seconds <= 1200 THEN e.raid_points + e.defending_points ELSE 0 END) AS first_half_points,
        SUM(CASE WHEN e.elapsed_seconds > 1200 THEN e.raid_points + e.defending_points ELSE 0 END) AS second_half_points,
        SUM(CASE WHEN e.event_type = 'Green Card' THEN 1 ELSE 0 END) AS green_cards,
        SUM(CASE WHEN e.event_type = 'Yellow Card' THEN 1 ELSE 0 END) AS yellow_cards,
        SUM(CASE WHEN e.is_do_or_die = 1 THEN 1 ELSE 0 END) AS do_or_die_raids,
        COUNT(e.event_row_id) AS total_plays
    FROM fact_events e
    GROUP BY e.match_id
)
SELECT 
    m.match_id,
    m.season_name,
    m.match_date,
    m.team_a_name,
    m.team_a_score,
    m.team_b_name,
    m.team_b_score,
    eh.first_half_points,
    eh.second_half_points,
    eh.do_or_die_raids,
    eh.green_cards,
    eh.yellow_cards,
    eh.total_plays
FROM fact_matches m
JOIN event_halves eh ON m.match_id = eh.match_id
WHERE m.is_official_pkl = 1 AND m.is_completed = 1
ORDER BY m.match_id ASC
LIMIT 15;
-- QUERY_20_END

-- ----------------------------------------------------------------------------
-- Query 21: Team Performance in High-Pressure Do-or-Die Raids
-- Business Question: Which teams convert the highest percentage of high-pressure
-- Do-or-Die raids into successful points according to play-by-play event records?
-- ----------------------------------------------------------------------------
-- QUERY_21_START
SELECT 
    t.team_name,
    COUNT(e.event_row_id) AS total_dod_raids,
    SUM(CASE WHEN e.event_type = 'Successful Raid' THEN 1 ELSE 0 END) AS successful_dod_raids,
    SUM(CASE WHEN e.event_type = 'Unsuccessful Raid' THEN 1 ELSE 0 END) AS failed_dod_raids,
    ROUND(100.0 * SUM(CASE WHEN e.event_type = 'Successful Raid' THEN 1 ELSE 0 END) / COUNT(e.event_row_id), 2) AS dod_conversion_pct,
    SUM(e.raid_points) AS total_dod_points_scored
FROM fact_events e
JOIN dim_teams t ON e.raiding_team_id = t.team_id
JOIN fact_matches m ON e.match_id = m.match_id
WHERE m.is_official_pkl = 1 AND e.is_do_or_die = 1 AND e.raiding_team_id IS NOT NULL
GROUP BY t.team_name
HAVING COUNT(e.event_row_id) >= 50
ORDER BY dod_conversion_pct DESC;
-- QUERY_21_END

-- ----------------------------------------------------------------------------
-- Query 22: Captaincy Leadership Impact on Franchise Victory
-- Business Question: What is the win rate and scoring differential of teams when their
-- appointed team captain plays on court compared to when captain is benched?
-- ----------------------------------------------------------------------------
-- QUERY_22_START
WITH match_captains AS (
    SELECT 
        pm.match_id,
        pm.team_id,
        pm.player_name AS captain_name,
        pm.total_points AS captain_points,
        pm.played AS captain_played
    FROM fact_player_match pm
    WHERE pm.captain = 1 AND pm.is_official_pkl = 1
)
SELECT 
    tm.team_name,
    COUNT(tm.match_id) AS total_matches,
    SUM(CASE WHEN mc.captain_played = 1 THEN 1 ELSE 0 END) AS matches_with_captain_on_court,
    ROUND(100.0 * SUM(CASE WHEN mc.captain_played = 1 AND tm.result = 'Win' THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN mc.captain_played = 1 THEN 1 ELSE 0 END), 0), 2) AS win_pct_with_captain,
    ROUND(AVG(CASE WHEN mc.captain_played = 1 THEN tm.score ELSE NULL END), 1) AS avg_team_score_with_captain,
    ROUND(AVG(CASE WHEN mc.captain_played = 1 THEN mc.captain_points ELSE NULL END), 1) AS avg_captain_personal_score
FROM fact_team_match tm
JOIN match_captains mc ON tm.match_id = mc.match_id AND tm.team_id = mc.team_id
WHERE tm.is_official_pkl = 1 AND tm.status = 'Full Time'
GROUP BY tm.team_name
ORDER BY win_pct_with_captain DESC;
-- QUERY_22_END
