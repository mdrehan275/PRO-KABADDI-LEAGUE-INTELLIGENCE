"""
app/pages/5_SQL_Insights.py
---------------------------
Interactive SQL Query Runner, Live Analytics Database Explorer,
KPI Mathematical Definitions, and Data Quality Auditing Contracts.
"""

import os
import sqlite3
import time
import streamlit as st
import pandas as pd

from utils import apply_custom_css

st.set_page_config(page_title="SQL Insights & Methodology | PKL Intelligence", page_icon="🔍", layout="wide")
apply_custom_css()

st.title("🔍 SQL Query Explorer & Methodology")
st.markdown("Execute advanced relational SQL queries directly against the production analytical warehouse, examine KPI formulas, and review data contracts.")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "pkl_analytics.db")
SQL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sql", "analysis_queries.sql")
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sql", "schema.sql")


@st.cache_resource(show_spinner="Initializing in-memory analytical warehouse...")
def get_database_connection():
    """
    Returns a connection to SQLite. If data/pkl_analytics.db doesn't exist on disk
    (e.g. freshly deployed to Streamlit Cloud), it automatically rebuilds it from the
    preprocessed Parquet tables so all 22 SQL queries work immediately with zero configuration.
    """
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Check if database file exists and contains tables
    needs_init = True
    if os.path.exists(DB_PATH):
        try:
            c = sqlite3.connect(DB_PATH)
            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", c)
            c.close()
            if "dim_seasons" in tables["name"].values:
                needs_init = False
        except Exception:
            needs_init = True

    if needs_init:
        # Load tables from parquet
        from app.utils import PROCESSED_DIR
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Apply schema if available
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
            conn.commit()

        # 2. Populate tables from parquet
        table_names = [
            "dim_seasons", "dim_teams", "dim_venues", "dim_players",
            "fact_matches", "fact_team_match", "fact_player_match", "fact_events"
        ]
        for tbl in table_names:
            pq_file = os.path.join(PROCESSED_DIR, f"{tbl}.parquet")
            if os.path.exists(pq_file):
                df_tbl = pd.read_parquet(pq_file)
                df_tbl.to_sql(tbl, conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()

    return DB_PATH

tab1, tab2, tab3 = st.tabs(["🚀 Interactive SQL Explorer", "📐 KPI Math Definitions", "🛡️ Data Quality & Contracts"])

# --- TAB 1: INTERACTIVE SQL RUNNER ---
with tab1:
    st.subheader("Interactive Warehouse Query Runner")
    st.markdown("Choose from 22 pre-authored advanced analytical queries or execute custom `SELECT` queries against `data/pkl_analytics.db`.")

    # Extract queries
    queries = {}
    if os.path.exists(SQL_FILE):
        with open(SQL_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        import re
        pattern = re.compile(r"-- QUERY_(\d+)_START\s+(.*?)\s+-- QUERY_\1_END", re.DOTALL)
        for m in pattern.finditer(content):
            q_num = int(m.group(1))
            queries[q_num] = m.group(2).strip()

    query_titles = {
        1: "Q01: Total Matches and Completed Matches by Season and Tournament",
        2: "Q02: Team Win Counts, Losses, Ties, and Win Percentages (Official PKL)",
        3: "Q03: Top 10 Highest-Scoring Matches in PKL History",
        4: "Q04: Average Team Score and Points Distribution by PKL Season",
        5: "Q05: All-Time Top 15 Highest-Performing Raiders",
        6: "Q06: All-Time Top 15 Highest-Performing Defenders",
        7: "Q07: Player Rankings using RANK() and DENSE_RANK() by Tactical Role",
        8: "Q08: Top Scorer in Each PKL Season (Season-Wise Leaders)",
        9: "Q09: Team Win Rates by Venue & Stadium Fortress Analysis",
        10: "Q10: Toss Outcome vs Match Outcome Analysis",
        11: "Q11: Leading Player Point Contribution to Team Total",
        12: "Q12: Team Successful Raid Percentages & Offensive Breakdown",
        13: "Q13: Team Defensive Tackle Success Rates & Super Tackle Production",
        14: "Q14: Super Raid and Super Tackle Frequency by Season",
        15: "Q15: Match Outcomes Segmented by Score Margin (Clutch vs Blowout)",
        16: "Q16: Season-over-Season Performance Evolution (LAG Window Function)",
        17: "Q17: Rolling 5-Match Player Performance (Pre-Match Form Feature)",
        18: "Q18: Team Cumulative Form & Running Goal Differential",
        19: "Q19: Player Consistency Analysis: Relative Volatility Index",
        20: "Q20: Match-Level Chronological Feature Aggregation from Events",
        21: "Q21: Team Performance in High-Pressure Do-or-Die Raids",
        22: "Q22: Captaincy Leadership Impact on Franchise Victory"
    }

    selected_query_label = st.selectbox(
        "Select Analytical Query:",
        [query_titles[i] for i in sorted(query_titles.keys())] + ["Custom SQL Query..."]
    )

    if selected_query_label != "Custom SQL Query...":
        q_idx = int(selected_query_label.split(":")[0].replace("Q", ""))
        default_sql = queries.get(q_idx, "SELECT 1;")
    else:
        default_sql = "SELECT team_name, franchise_era, is_pkl_franchise FROM dim_teams WHERE is_pkl_franchise = 1;"

    user_sql = st.text_area("SQL Statement (Read-Only SQLite):", value=default_sql, height=220)

    if st.button("▶️ Execute Query", type="primary"):
        # Security sanity check (read-only execution)
        forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "ATTACH"]
        if any(kw in user_sql.upper() for kw in forbidden_keywords):
            st.error("Only read-only SELECT queries are permitted on this analytical warehouse.")
        else:
            try:
                db_file = get_database_connection()
                conn = sqlite3.connect(db_file)
                t0 = time.time()
                result_df = pd.read_sql_query(user_sql, conn)
                elapsed_ms = (time.time() - t0) * 1000
                conn.close()

                st.success(f"Query returned **{len(result_df):,} rows** in **{elapsed_ms:.1f} ms**.")
                st.dataframe(result_df, use_container_width=True)

                # Download CSV
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Query Result as CSV",
                    data=csv,
                    file_name="pkl_sql_query_result.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"SQL Execution Error: {e}")

# --- TAB 2: KPI MATHEMATICAL DEFINITIONS ---
with tab2:
    st.subheader("📐 Standard KPI Mathematical Formulas")
    
    st.markdown("""
    #### 1. Official Team Score Decomposition
    Every team match score is mathematically guaranteed to equal:
    $$\\text{Score} = \\text{Raid Points Total} + \\text{Tackle Points Total} + \\text{All-Out Points} + \\text{Extra Points}$$
    - **Raid Points Total:** $\\text{Touch Points} + \\text{Bonus Points}$.
    - **Tackle Points Total:** $\\text{Capture Points} + \\text{Super Tackle Bonus Points}$.
    - **All-Out Points:** Exactly $2 \\times (\\text{All-Outs Inflicted})$.
    - **Extra Points:** Technical referee awards, line-out penalties, and technical bench violations.
    
    ---

    #### 2. Offensive Efficiency Metrics
    - **Raid Strike Rate (%):**
      $$\\text{Raid Strike Rate} = \\frac{\\text{Successful Raids}}{\\text{Total Raids Attempted}} \\times 100\\%$$
    - **Empty Raid Rate (%):**
      $$\\text{Empty Raid Rate} = \\frac{\\text{Empty Strategic Raids}}{\\text{Total Raids Attempted}} \\times 100\\%$$
    - **Super Raid Rate:** Raids yielding $\\ge 3$ points per attempt.

    ---

    #### 3. Defensive Efficiency Metrics
    - **Tackle Success Rate (%):**
      $$\\text{Tackle Success Rate} = \\frac{\\text{Successful Tackles}}{\\text{Total Tackles Attempted}} \\times 100\\%$$
    - **Super Tackle Rate:** Tackles successfully executed when $\\le 3$ active defenders remain on court (awards 2 points).

    ---

    #### 4. Player Consistency & Volatility Metrics
    - **Relative Volatility Index:**
      $$\\text{RVI} = \\frac{\\sigma_{\\text{points}}}{\\mu_{\\text{points}}}$$
      Measures scoring variance relative to output mean. Low RVI ($< 0.45$) indicates dependable anchors; high RVI ($> 0.80$) indicates high-risk swing performers.
    """)

# --- TAB 3: DATA QUALITY AUDIT CONTRACTS ---
with tab3:
    st.subheader("🛡️ Data Provenance & Quality Limitations")
    
    st.markdown("""
    1. **Player of the Match Defect Resolution:**
       - Raw `DS_match.csv` erroneously duplicated `player_id_of_the_match` into `player_name_of_the_match`.
       - Our pipeline joined the master player registry across `DS_players.csv` and successfully resolved all 575 POTM awards to verified player strings.
    
    2. **Tournament Filtering Scope:**
       - The raw archive contains 17 competitions (684 matches).
       - Official PKL franchise metrics and prediction targets are strictly filtered to `series_id IN (1, 2, 3, 4, 8, 26, 49)` (603 matches). Non-PKL tournaments (World Cup, Asian Games) are isolated in `dim_seasons`.
    
    3. **Season 1 Defensive Attribution Note:**
       - In Season 1 (2014), the original web API scraper recorded squad tackle points inverted against the opposing team.
       - Modern seasons (Seasons 6 & 7) reconcile with 100.0% exact parity between player and team totals.
    
    4. **Caravan Format & Home Advantage:**
       - PKL matches travel in caravan city legs. In neutral fixtures, `home_team_id` is null by design.
       - Home advantage is evaluated strictly where a franchise competes at its registered home stadium.
    """)
