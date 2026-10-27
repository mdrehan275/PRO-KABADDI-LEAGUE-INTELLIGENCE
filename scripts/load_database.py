"""
scripts/load_database.py
------------------------
Creates SQLite analytical database `data/pkl_analytics.db` using `sql/schema.sql`,
loads all processed parquet/csv tables, builds indexes, and validates counts.
"""

import os
import sqlite3
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/pkl_analytics.db"
SCHEMA_PATH = "sql/schema.sql"
PROCESSED_DIR = "data/processed"


def load_database():
    """Initializes schema and populates SQLite database from processed tables."""
    logger.info(f"Connecting to SQLite database: {DB_PATH}")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"Removed previous database file at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Execute DDL Schema
    logger.info(f"Executing schema DDL from {SCHEMA_PATH}...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()

    # 2. Tables to load
    tables = [
        "dim_seasons",
        "dim_teams",
        "dim_venues",
        "dim_players",
        "fact_matches",
        "fact_team_match",
        "fact_player_match",
        "fact_events"
    ]

    counts = {}
    for table_name in tables:
        pq_path = os.path.join(PROCESSED_DIR, f"{table_name}.parquet")
        csv_path = os.path.join(PROCESSED_DIR, f"{table_name}.csv")

        if os.path.exists(pq_path):
            df = pd.read_parquet(pq_path)
        elif os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(f"Missing data file for table {table_name}")

        # Convert boolean columns to 0/1 for SQLite compatibility
        for col in df.select_dtypes(include=['bool']).columns:
            df[col] = df[col].astype(int)

        # Load into SQLite
        df.to_sql(table_name, conn, if_exists="append", index=False)
        
        # Verify count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        db_count = cursor.fetchone()[0]
        counts[table_name] = db_count
        logger.info(f"  Loaded {table_name:<18}: {db_count:>6} rows")
        assert db_count == len(df), f"Row count mismatch in {table_name}: {db_count} vs {len(df)}"

    conn.close()
    logger.info(f"Database successfully created and populated at {DB_PATH}!")
    return counts


if __name__ == "__main__":
    counts = load_database()
    print("\n" + "=" * 60)
    print(" PKL SQLITE DATABASE BUILD COMPLETED SUCCESSFULLY ")
    print("=" * 60)
    for tbl, cnt in counts.items():
        print(f"  {tbl:<22}: {cnt:>6} rows")
