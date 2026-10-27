# Pro Kabaddi League (PKL) Analytics Platform: Data Dictionary

## Overview
This document provides an exhaustive, authoritative schema specification and data dictionary for all raw and processed entities within the Pro Kabaddi League (PKL) dataset (spanning Seasons 1 through 7, 2014–2019).

---

## 1. Matches Entity (`DS_match.csv` / `matches`)

| Column Name | Physical Data Type | Logical Type | Nullable | Primary / Foreign Key | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `match_id` | `INTEGER` | Categorical ID | No | **PK** | Unique match identifier across all seasons and tournaments. |
| `match_number` | `VARCHAR(50)` | Categorical | No | None | Display match label (e.g., "Match 1", "Qualifier 1", "Final"). |
| `date` | `VARCHAR(20)` / `DATE` | Temporal | No | None | Date of the match. Raw contains mixed formats (`M/D/YYYY`, `MM/DD/YYYY`, `YYYY-MM-DD`). Converted to ISO `YYYY-MM-DD`. |
| `start_time` | `VARCHAR(10)` / `TIME` | Temporal | No | None | Scheduled start time in Indian Standard Time (IST, e.g., "20:00"). |
| `result` | `VARCHAR(255)` | Categorical Text | Yes | None | Narrative match outcome (e.g., "U Mumba beat Jaipur Pink Panthers (45-31)", "Match Tied (30-30)"). Null in 5 uncompleted/testing matches. |
| `player_id_of_the_match` | `FLOAT` / `INTEGER` | Categorical ID | Yes | **FK** -> `players(player_id)` | Numeric Player ID of the Player of the Match (Man of the Match). Null in 109 matches (ties or unrecorded). |
| `player_name_of_the_match` | `FLOAT` | Defective Field | Yes | None | **Data Quality Warning**: In raw data, this column erroneously duplicates `player_id_of_the_match` (floats). Resolved via join with `players(player_name)`. |
| `series_id` | `INTEGER` | Categorical ID | No | None | Unique competition identifier (e.g., 1 for Season 1, 2 for Season 2, ..., 49 for Season 7). |
| `series_name` | `VARCHAR(100)` | Categorical Text | No | None | Full competition name. Covers PKL Seasons 1–7 (603 matches), test fixtures (6 matches), and international/exhibition tournaments (75 matches). |
| `status` | `VARCHAR(50)` | Categorical | No | None | Match completion state: `'Full Time'` (679), `'1st Half'` (3), `'2nd Half'` (1), `'Yet to Begin'` (1). |
| `toss_winner` | `INTEGER` | Categorical ID | No | **FK** -> `teams(team_id)` | Team ID that won the pre-match coin toss. |
| `toss_selection` | `VARCHAR(50)` | Categorical | No | None | Decision made by toss winner (`'Choice of court : Left'`, `'Choice of court : Right'`, `'Choice of raid : Right'`). Contains minor spacing variances. |
| `venue_id` | `INTEGER` | Categorical ID | No | None | Identifier for the indoor stadium/arena. |
| `venue_name` | `VARCHAR(150)` | Categorical Text | No | None | Stadium name and city (e.g., "DOME@NSCI SVP Stadium, Mumbai", "The Arena by TransStadia, Ahmedabad"). |
| `home_team_id` | `FLOAT` / `INTEGER` | Categorical ID | Yes | **FK** -> `teams(team_id)` | Team ID of the hosting team. Missing (`NULL`) in 433 matches (neutral legs, early tournament formats, or exhibition games). |
| `home_team_name` | `VARCHAR(100)` | Categorical Text | Yes | None | Name of the hosting franchise when designated. |

---

## 2. Team Match Statistics Entity (`DS_team.csv` / `team_match_stats`)

| Column Name | Physical Data Type | Logical Type | Nullable | Primary / Foreign Key | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` / `team_id` | `INTEGER` | Categorical ID | No | **Composite PK**, **FK** -> `teams(team_id)` | Unique team identifier. Exactly 2 records per match (1,368 rows across 684 matches). |
| `match_id` | `INTEGER` | Categorical ID | No | **Composite PK**, **FK** -> `matches(match_id)` | Match reference identifier. |
| `name` / `team_name` | `VARCHAR(100)` | Categorical Text | No | None | Team franchise name. Normalizes variations (e.g., "Dabang Delhi" -> "Dabang Delhi K.C."). |
| `short_name` | `VARCHAR(10)` | Categorical | No | None | Official 3-letter team acronym (e.g., `MUM`, `DEL`, `BLR`, `PUN`, `JAI`, `PAT`, `TEL`, `BEN`). |
| `score` | `INTEGER` | Discrete Numeric | No | None | Final official match points scored by the team. Reconciles with components: `score = raid_pts + tackle_pts + all_out_pts + extras` (0 discrepancies). |
| `squad` | `TEXT` (JSON) | Structured Text | No | None | JSON array containing match squad roster, player IDs, and court statuses. |
| `stats.all_outs` | `INTEGER` | Discrete Numeric | No | None | Number of all-outs inflicted on opponent team during regulation play. |
| `stats.points.all_out` | `INTEGER` | Discrete Numeric | No | None | Points earned from all-outs (strictly 2 points per all-out inflicted). |
| `stats.points.extras` | `INTEGER` | Discrete Numeric | No | None | Technical and penalty points awarded to team by match referees. |
| `stats.points.declare` | `INTEGER` | Discrete Numeric | No | None | Points awarded via declaration (always 0 in regulation PKL). |
| `stats.points.raid_points.total` | `INTEGER` | Discrete Numeric | No | None | Total offensive raid points scored (`touch + bonus`). |
| `stats.points.raid_points.touch` | `INTEGER` | Discrete Numeric | No | None | Points gained by raider physically tagging defenders before safely returning across the mid-line. |
| `stats.points.raid_points.raid_bonus` | `INTEGER` | Discrete Numeric | No | None | Points gained by crossing the bonus line when 6 or 7 defenders are active on court. |
| `stats.points.tackle_points.total` | `INTEGER` | Discrete Numeric | No | None | Total defensive tackle points scored (`capture + super_tackle_bonus`). |
| `stats.points.tackle_points.capture` | `INTEGER` | Discrete Numeric | No | None | Base points from capturing opposing raiders (1 pt per standard capture). |
| `stats.points.tackle_points.capture_bonus`| `INTEGER`| Discrete Numeric | No | None | Bonus points from Super Tackles (1 extra point awarded when <=3 defenders pin raider). |
| `stats.points.total` | `INTEGER` | Discrete Numeric | No | None | Total points calculated by system. 100% identical to `score`. |
| `stats.raids.total` | `INTEGER` | Discrete Numeric | No | None | Total raids conducted by the team during the match (`successful + unsuccessful + Empty`). |
| `stats.raids.successful` | `INTEGER` | Discrete Numeric | No | None | Raids resulting in at least 1 point (touch or bonus). |
| `stats.raids.unsuccessful` | `INTEGER` | Discrete Numeric | No | None | Raids where raider was caught or ruled out. |
| `stats.raids.Empty` | `INTEGER` | Discrete Numeric | No | None | Raids resulting in 0 points where raider returned safely. |
| `stats.raids.super_raids` | `FLOAT` / `INTEGER` | Discrete Numeric | Yes (40.6% null) | None | Raids where 3 or more points were earned. Null represents 0 super raids. |
| `stats.tackles.total` | `INTEGER` | Discrete Numeric | No | None | Total defensive tackles initiated by the team. |
| `stats.tackles.successful` | `INTEGER` | Discrete Numeric | No | None | Tackles that prevented the raider from returning across mid-line. |
| `stats.tackles.unsuccessful`| `INTEGER` | Discrete Numeric | No | None | Tackles that failed, allowing raider to score touch points. |
| `stats.tackles.super_tackles`| `FLOAT` / `INTEGER`| Discrete Numeric | Yes (40.6% null)| None | Successful tackles executed with 3 or fewer defenders active. Null represents 0 super tackles. |

---

## 3. Player Match Statistics Entity (`DS_players.csv` / `player_match_stats`)

| Column Name | Physical Data Type | Logical Type | Nullable | Primary / Foreign Key | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `match_id` | `INTEGER` | Categorical ID | No | **Composite PK**, **FK** -> `matches(match_id)` | Match reference identifier. |
| `team_id` | `INTEGER` | Categorical ID | No | **Composite PK**, **FK** -> `teams(team_id)` | Team the player represented in this match. |
| `player_id` | `INTEGER` | Categorical ID | No | **Composite PK**, **FK** -> `players(player_id)` | Unique individual player identifier. |
| `player_name` | `VARCHAR(100)` | Categorical Text | No | None | Full legal player name. |
| `player_short_name` | `VARCHAR(50)` | Categorical Text | No | None | Abbreviated name (e.g., "A. Kumar", "P. Narwal"). |
| `player_skill` | `VARCHAR(50)` | Categorical | Yes (1.1% null) | None | Specific positional assignment: 'Raider', 'Defender, right cover', 'Defender, left corner', etc. |
| `player_role` | `VARCHAR(30)` | Categorical | Yes (1.1% null) | None | High-level tactical role: 'Raider', 'Defender', 'All-Rounder'. |
| `player_played` | `BOOLEAN` | Binary Indicator | No | None | `True` if player participated on court (starter or subbed in); `False` if bench reserve only. |
| `player_captain` | `BOOLEAN` | Binary Indicator | No | None | `True` if designated team captain for the fixture. |
| `player_on_starter` | `BOOLEAN` | Binary Indicator | No | None | `True` if in the starting 7 lineup. |
| `player_on_court` | `BOOLEAN` | Binary Indicator | No | None | Status indicator for court presence at whistle. |
| `player_jersey` | `FLOAT` / `INTEGER`| Discrete Numeric | Yes (5.2% null) | None | Player squad jersey number. |
| `player_total_points` | `INTEGER` | Discrete Numeric | No | None | Total match points scored by the player (`raid_points_total + tackle_points_total`). |
| `player_raid_points_total` | `INTEGER` | Discrete Numeric | No | None | Total raid points scored by player in this match. Reconciles with team total. |
| `player_raid_points_touch` | `INTEGER` | Discrete Numeric | No | None | Touch points scored during raids. |
| `player_raid_points_raid_bonus` | `INTEGER`| Discrete Numeric | No | None | Bonus points scored during raids. |
| `player_tackle_points_total` | `INTEGER` | Discrete Numeric | No | None | Total tackle points scored by player in this match. Reconciles with team total. |
| `player_tackle_points_touch` | `INTEGER` | Discrete Numeric | No | None | Tackle points from captures. |
| `player_tackle_points_capture_bonus`| `INTEGER`| Discrete Numeric | No | None | Tackle bonus points from participating in super tackles. |
| `player_raids_total` | `INTEGER` | Discrete Numeric | No | None | Total raid attempts made by the player. |
| `player_raids_successful` | `INTEGER` | Discrete Numeric | No | None | Raids resulting in at least 1 point. |
| `player_raids_unsuccessful` | `INTEGER` | Discrete Numeric | No | None | Raids ending in raider being tackled out. |
| `player_raids_Empty` | `INTEGER` | Discrete Numeric | No | None | Raids resulting in 0 points where raider returned safely. |
| `player_tackles_total` | `INTEGER` | Discrete Numeric | No | None | Defensive tackle attempts initiated. |
| `player_tackles_successful` | `INTEGER` | Discrete Numeric | No | None | Successful tackles completed. |
| `player_tackles_unsuccessful`| `INTEGER` | Discrete Numeric | No | None | Failed tackle attempts. |
| `player_green_card` | `INTEGER` | Discrete Numeric | No | None | Disciplinary warning cards received. |
| `player_yellow_card`| `INTEGER` | Discrete Numeric | No | None | Disciplinary 2-minute suspension cards received. |
| `player_red_card` | `INTEGER` | Discrete Numeric | No | None | Ejection cards received. |

---

## 4. Match Events Entity (`DS_events.csv` / `match_events`)

| Column Name | Physical Data Type | Logical Type | Nullable | Primary / Foreign Key | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | `INTEGER` | Categorical ID | No | None | Event record identifier. |
| `event_no` | `INTEGER` | Discrete Sequence | No | None | Chronological event index within the match (1, 2, ..., N). |
| `match_id` | `INTEGER` | Categorical ID | No | **FK** -> `matches(match_id)` | Associated match identifier. |
| `clock` | `VARCHAR(10)` | Temporal Interval | Yes | None | Elapsed game clock in `MM:SS` (ascending from 00:00 to 40:00+). |
| `event` | `VARCHAR(50)` | Categorical | No | None | Primary event type: `'Successful Raid'`, `'Empty Raid'`, `'Unsuccessful Raid'`, `'Substitution'`, `'TimeOut'`, `'Green Card'`, `'Yellow Card'`, `'Red Card'`, `'Non Raid Technical Points'`, `'Raider and Anti Out'`. |
| `event_text` | `VARCHAR(255)` | Descriptive Text | No | None | Action string (e.g., "Pardeep Narwal Successful Raid", "Mohit Chhillar Super Tackle"). |
| `raiding_team_id` | `FLOAT` / `INTEGER` | Categorical ID | Yes (12.4% null) | **FK** -> `teams(team_id)` | Team conducting offensive raid. Null on administrative timeouts. |
| `defending_team_id` | `FLOAT` / `INTEGER`| Categorical ID | Yes (12.4% null) | **FK** -> `teams(team_id)` | Team defending court. |
| `raider_id` | `FLOAT` / `INTEGER` | Categorical ID | Yes (12.4% null) | **FK** -> `players(player_id)` | Player initiating raid. |
| `defender_id` | `FLOAT` / `INTEGER` | Categorical ID | Yes (70.3% null) | **FK** -> `players(player_id)` | Primary defender credited with tackle/capture. |
| `raid_points` | `FLOAT` / `INTEGER` | Discrete Numeric | Yes | None | Points scored by raider on this raid event (0, 1, 2, 3, 4, 5). |
| `defending_points` | `FLOAT` / `INTEGER`| Discrete Numeric | Yes | None | Points scored by defending team on this event (0, 1, 2). |
| `score` | `VARCHAR(20)` | Structured Tuple | Yes (11.0% null) | None | Running score string array `[TeamA, TeamB]` at event completion. |
| `super_raid` | `BOOLEAN` / `FLOAT` | Binary Indicator | Yes (70.3% null) | None | `True` if raid resulted in >= 3 points. |
| `super_tackle` | `BOOLEAN` / `FLOAT`| Binary Indicator | Yes (70.3% null) | None | `True` if defense pinned raider with <= 3 defenders on court. |
| `do_or_die` | `BOOLEAN` / `FLOAT` | Binary Indicator | Yes (69.5% null) | None | `True` if raid was a mandatory scoring Do-or-Die raid. |
| `review.*` | Various | Complex Sub-schema | Yes (>95% null) | None | Video review metadata: review caller team, review outcome, and umpire challenge resolution. |

---

## 5. Entity Relationships & Granularity

```
[matches] 1 ──── 2 [team_match_stats]
   │
   ├──── 14-28 ───── [player_match_stats]
   │
   └──── 80-120 ──── [match_events]
```

- **Matches -> Team Match Stats**: 1-to-2 relationship. Every match has exactly two team statistics rows.
- **Matches -> Player Match Stats**: 1-to-many relationship (avg ~24.7 player records per match, 10–14 per squad).
- **Matches -> Match Events**: 1-to-many chronological sequence (avg ~97 event records per match).
- **Score Consistency**: Team score equals sum of points (`score = raid_pts + tackle_pts + all_out_pts + extras`). Sum of player raid and tackle points equals team raid and tackle points with 100% precision.
