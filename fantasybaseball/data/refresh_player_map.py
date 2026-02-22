#!/usr/bin/env python3
"""Download the latest Smart Fantasy Baseball player ID mapping.

Usage:
    python fantasybaseball/data/refresh_player_map.py

This script downloads the CSV version of the SFBB Player ID Map directly
from their Google Sheets export URL and saves it to fantasybaseball/data/player_id_map.csv.
"""

import sys
import requests
import pandas as pd

# Direct CSV export URL from the Google Sheets document
# Smart Fantasy Baseball Tools publishes this at https://www.smartfantasybaseball.com/tools/
SFBB_PLAYER_MAP_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/1JgczhD5VDQ1EiXqVG-blttZcVwbZd5_Ne_mefUGwJnk/export?format=csv&gid=0"
)

OUTPUT_FILE = "fantasybaseball/data/player_id_map.csv"

# Expected columns to validate the download
EXPECTED_COLUMNS = ["MLBID", "IDFANGRAPHS", "FANTRAXID", "ESPNID", "YAHOOID", "PLAYERNAME"]


def download_player_map():
    """Download and validate the player ID mapping."""
    print(f"Downloading player ID map from {SFBB_PLAYER_MAP_CSV_URL}...")

    response = requests.get(SFBB_PLAYER_MAP_CSV_URL)
    response.raise_for_status()

    # Validate it's a valid CSV with expected columns
    df = pd.read_csv(pd.io.common.BytesIO(response.content))

    missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing_cols:
        print(f"ERROR: Downloaded file is missing expected columns: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    # Save to file
    with open(OUTPUT_FILE, "wb") as f:
        f.write(response.content)

    print(f"Successfully downloaded player ID map to {OUTPUT_FILE}")
    print(f"  Total players: {len(df):,}")
    print(f"  Players with MLBAM ID: {df['MLBID'].notna().sum():,}")
    print(f"  Players with Fangraphs ID: {df['IDFANGRAPHS'].notna().sum():,}")
    print(f"  Players with Fantrax ID: {df['FANTRAXID'].notna().sum():,}")


if __name__ == "__main__":
    download_player_map()
