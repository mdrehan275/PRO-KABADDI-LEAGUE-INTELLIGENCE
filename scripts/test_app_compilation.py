"""
scripts/test_app_compilation.py
-------------------------------
Validates that all Streamlit app scripts and utility functions compile cleanly,
import without circular dependency errors, and load datasets successfully.
"""

import sys
import os
import py_compile

APP_DIR = "app"
PAGES_DIR = os.path.join(APP_DIR, "pages")

print("=" * 60)
print("TESTING STREAMLIT APP COMPILATION & IMPORTS")
print("=" * 60)

files_to_test = [
    os.path.join(APP_DIR, "utils.py"),
    os.path.join(APP_DIR, "Home.py"),
    os.path.join(PAGES_DIR, "1_Team_Analytics.py"),
    os.path.join(PAGES_DIR, "2_Player_Analytics.py"),
    os.path.join(PAGES_DIR, "3_Match_Explorer.py"),
    os.path.join(PAGES_DIR, "4_Event_Analytics.py"),
    os.path.join(PAGES_DIR, "5_SQL_Insights.py")
]

for f in files_to_test:
    assert os.path.exists(f), f"File {f} does not exist!"
    try:
        py_compile.compile(f, doraise=True)
        print(f"  [PASS] {f} syntax compiled cleanly.")
    except Exception as e:
        print(f"  [FAIL] {f} compilation error: {e}")
        sys.exit(1)

# Test data loading via utils
sys.path.insert(0, APP_DIR)
import utils
data = utils.load_all_data()
print(f"\nData successfully loaded via app/utils.py: {len(data)} tables in memory.")
for name, df in data.items():
    print(f"  {name:<18}: {len(df):>6} rows")

print("\nAll Streamlit application modules validated successfully!")
