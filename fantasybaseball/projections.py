import logging
from datetime import datetime

import pandas as pd

from .model import ProjectionSource, ProjectionSourceName, StatCategory
from .modify import (
    add_auction_values,
    add_league_info,
    add_mean_projection,
    add_pitcher_position,
    add_points,
    add_points_above_replacement,
    format_stats,
    order_and_rank_rows,
    order_columns,
    replace_positions,
)

logger = logging.getLogger(__name__)

BAT_START_COLUMNS = [
    ("ProjectionSource", "string"),
    ("Rank", "int"),
    ("Position", "string"),
    ("Name", "string"),
    ("MlbamId", "int"),
    ("FangraphsId", "int"),
    ("FantraxId", "string"),
    ("Age", "int"),
    ("League", "string"),
    ("Team", "string"),
    ("ShortName", "string"),
    ("Status", "string"),
    ("Salary", "currency", 2),
    ("Contract", "int"),
    ("Points", "float", 2),
    ("Pts/G", "float", 2),
    ("PAR", "float", 2),
    ("AuctionValue", "currency", 2),
    ("ContractValue", "currency", 2),
    ("ADP", "float", 2),
    ("G", "int"),
    ("AB", "int"),
    ("PA", "int"),
    ("H", "int"),
    ("1B", "int"),
    ("2B", "int"),
    ("3B", "int"),
    ("HR", "int"),
    ("R", "int"),
    ("RBI", "int"),
    ("BB", "int"),
    ("IBB", "int"),
    ("SO", "int"),
    ("HBP", "int"),
    ("SF", "int"),
    ("SH", "int"),
    ("SB", "int"),
    ("CS", "int"),
    ("AVG", "float", 3),
    ("OBP", "float", 3),
    ("SLG", "float", 3),
    ("OPS", "float", 3),
    ("wOBA", "float", 3),
    ("BB%", "float", 2),
    ("K%", "float", 2),
    ("BB/K", "float", 2),
    ("ISO", "float", 3),
    ("Spd", "float", 2),
    ("BABIP", "float", 3),
    ("wRC", "float", 2),
    ("wRAA", "float", 2),
    ("UZR", "float", 2),
    ("wBsR", "float", 2),
    ("BaseRunning", "float", 2),
    ("WAR", "float", 2),
    ("Off", "float", 2),
    ("Def", "float", 2),
    ("wRC+", "float", 2),
]

PIT_START_COLUMNS = [
    ("ProjectionSource", "string"),
    ("Rank", "int"),
    ("Position", "string"),
    ("Name", "string"),
    ("MlbamId", "int"),
    ("FangraphsId", "int"),
    ("FantraxId", "string"),
    ("Age", "int"),
    ("League", "string"),
    ("Team", "string"),
    ("ShortName", "string"),
    ("Status", "string"),
    ("Salary", "currency", 2),
    ("Contract", "int"),
    ("Points", "float", 2),
    ("Pts/IP", "float", 2),
    ("PAR", "float", 2),
    ("AuctionValue", "currency", 2),
    ("ContractValue", "currency", 2),
    ("ADP", "float", 2),
    ("W", "int"),
    ("L", "int"),
    ("GS", "int"),
    ("G", "int"),
    ("SV", "int"),
    ("HLD", "int"),
    ("IP", "float", 2),
    ("TBF", "int"),
    ("H", "int"),
    ("R", "int"),
    ("ER", "int"),
    ("HR", "int"),
    ("SO", "int"),
    ("BB", "int"),
    ("HBP", "int"),
    ("ERA", "float", 2),
    ("WHIP", "float", 2),
    ("K/9", "float", 2),
    ("BB/9", "float", 2),
    ("K/BB", "float", 2),
    ("HR/9", "float", 2),
    ("K%", "float", 2),
    ("BB%", "float", 2),
    ("K-BB%", "float", 2),
    ("GB%", "float", 2),
    ("AVG", "float", 2),
    ("BABIP", "float", 2),
    ("LOB%", "float", 2),
    ("FIP", "float", 2),
]

PLAYER_ID_MAP_FILE = "sitemaps/player_id_map.csv"


def _load_player_id_map():
    """Load Smart Fantasy Baseball player ID mapping."""
    player_map = pd.read_csv(PLAYER_ID_MAP_FILE)

    # Standardize column names from SFBB format
    player_map.rename(columns={
        "MLBID": "MlbamId",
        "IDFANGRAPHS": "FangraphsId",
        "FANTRAXID": "FantraxId",
        "ESPNID": "EspnId",
        "YAHOOID": "YahooId"
    }, inplace=True)

    # Convert to appropriate types
    player_map["MlbamId"] = pd.to_numeric(player_map["MlbamId"], errors='coerce').astype('Int64')
    player_map["FangraphsId"] = pd.to_numeric(player_map["FangraphsId"], errors='coerce').astype('Int64')

    return player_map


def _merge_with_league_export(projections, league_export):
    """Merge projections with league export using MLBAM ID with Fangraphs fallback."""

    # Ensure consistent types for FangraphsId
    league_export = league_export.copy()
    league_export["FangraphsId"] = pd.to_numeric(league_export["FangraphsId"], errors='coerce').astype('Int64')

    # Select league data columns, filtering out rows with null IDs to avoid cartesian products
    league_data = league_export[["Status", "Age", "Salary", "Contract", "MlbamId", "FangraphsId", "FantraxId"]].copy()

    # Primary join on MLBAM ID (only for non-null MlbamIds)
    league_data_mlbam = league_data[league_data["MlbamId"].notna()]
    merged = projections.merge(
        league_data_mlbam,
        on="MlbamId",
        how="left",
        suffixes=("_proj", "_league")
    )

    # For rows without MLBAM match, try Fangraphs ID
    unmatched_mask = merged["Status"].isna()
    if unmatched_mask.any():
        # Get unmatched projections
        unmatched_projections = projections[projections.index.isin(merged[unmatched_mask].index)]

        # Try to match on Fangraphs ID (only for non-null FangraphsIds)
        league_data_fangraphs = league_data[league_data["FangraphsId"].notna()]
        fangraphs_matches = unmatched_projections.merge(
            league_data_fangraphs[["Status", "Age", "Salary", "Contract", "FangraphsId", "FantraxId"]],
            on="FangraphsId",
            how="inner",
            suffixes=("", "_fg")
        )

        # Update merged dataframe with Fangraphs matches
        if not fangraphs_matches.empty:
            for idx in fangraphs_matches.index:
                if idx in merged.index:
                    merged.loc[idx, "Status"] = fangraphs_matches.loc[idx, "Status"]
                    merged.loc[idx, "Age"] = fangraphs_matches.loc[idx, "Age"]
                    merged.loc[idx, "Salary"] = fangraphs_matches.loc[idx, "Salary"]
                    merged.loc[idx, "Contract"] = fangraphs_matches.loc[idx, "Contract"]
                    merged.loc[idx, "FantraxId"] = fangraphs_matches.loc[idx, "FantraxId"]
                    # Keep the FangraphsId from league export if they differ
                    if "FangraphsId_league" in merged.columns:
                        merged.loc[idx, "FangraphsId_league"] = fangraphs_matches.loc[idx, "FangraphsId"]

    # Consolidate FangraphsId columns - prefer projection's FangraphsId, then league's
    if "FangraphsId_proj" in merged.columns and "FangraphsId_league" in merged.columns:
        merged["FangraphsId"] = merged["FangraphsId_proj"].fillna(merged["FangraphsId_league"])
        merged.drop(["FangraphsId_proj", "FangraphsId_league"], axis=1, inplace=True)
    elif "FangraphsId_league" in merged.columns:
        merged.rename(columns={"FangraphsId_league": "FangraphsId"}, inplace=True)

    # Clean up any remaining duplicate columns
    merged.drop([col for col in merged.columns if col.endswith("_league") or col.endswith("_proj")], axis=1, inplace=True, errors="ignore")

    return merged


def augment_projections(
    bat_projections, pit_projections, league=None, league_export=None, include_bench=True, ros=False
):
    bat_projections = add_mean_projection(
        bat_projections,
        projection_sources=[
            ProjectionSource(ProjectionSourceName.OOPSY, ros),
            ProjectionSource(ProjectionSourceName.STEAMER, ros),
            ProjectionSource(ProjectionSourceName.THE_BAT_X, ros),
            ProjectionSource(ProjectionSourceName.ZIPSDC, ros),
        ],
        name="rzobs" if ros else "zobs",
    )
    pit_projections = add_mean_projection(
        pit_projections,
        projection_sources=[
            ProjectionSource(ProjectionSourceName.OOPSY, ros),
            ProjectionSource(ProjectionSourceName.STEAMER, ros),
            ProjectionSource(ProjectionSourceName.THE_BAT, ros),
            ProjectionSource(ProjectionSourceName.ZIPSDC, ros),
        ],
        name="rzobs" if ros else "zobs",
    )

    rostered_players = None
    if league_export is not None:
        player_id_map = _load_player_id_map()

        # Add MLBAM IDs to league export via Fantrax ID
        league_export = league_export.merge(
            player_id_map[["MlbamId", "FangraphsId", "FantraxId"]],
            left_on="ID",        # Fantrax ID from export (e.g., "*02yc4*")
            right_on="FantraxId",
            how="left"
        )

        # Join projections with league export on MLBAM ID (primary)
        # with fallback to Fangraphs ID for players without MLBAM
        bat_projections = _merge_with_league_export(bat_projections, league_export)
        pit_projections = _merge_with_league_export(pit_projections, league_export)

        bat_projections = replace_positions(bat_projections, league_export)

    # Strip pitcher positions from batting projections (fixes two-way players like Ohtani)
    if "Position" in bat_projections.columns:
        bat_projections["Position"] = bat_projections["Position"].str.replace(r"[,/]?P", "", regex=True).str.strip("/,")

    if league:
        if "scoring" in league:
            bat_projections = add_points(
                bat_projections, StatCategory.BATTING, league["scoring"], use_stat_proxies=True
            )
            pit_projections = add_points(
                pit_projections, StatCategory.PITCHING, league["scoring"], use_stat_proxies=True
            )

            if "roster" in league:
                bat_projections = add_points_above_replacement(bat_projections, league["roster"], include_bench)
                pit_projections = add_pitcher_position(pit_projections, league["roster"])
                pit_projections = add_points_above_replacement(pit_projections, league["roster"], include_bench)

                if "salary" in league:
                    bat_projections, pit_projections = add_auction_values(
                        bat_projections, pit_projections, league["roster"], league["salary"], rostered_players
                    )

            bat_projections = order_and_rank_rows(bat_projections, order_by="Points", asc=False)
            pit_projections = order_and_rank_rows(pit_projections, order_by="Points", asc=False)

    bat_projections = order_columns(bat_projections, [c[0] for c in BAT_START_COLUMNS])
    pit_projections = order_columns(pit_projections, [c[0] for c in PIT_START_COLUMNS])

    bat_projections = bat_projections[[c[0] for c in BAT_START_COLUMNS if c[0] in bat_projections.columns]]
    pit_projections = pit_projections[[c[0] for c in PIT_START_COLUMNS if c[0] in pit_projections.columns]]

    bat_projections = format_stats(bat_projections, BAT_START_COLUMNS)
    pit_projections = format_stats(pit_projections, PIT_START_COLUMNS)

    return bat_projections, pit_projections


def write_projections_file(projections, stat_category, output_dir, league_name=None, custom=None):
    current_time_string = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{stat_category.value}_{current_time_string}.csv"
    if custom:
        filename = f"{custom}_{filename}"
    if league_name:
        filename = f"{league_name}_{filename}"
    file_path = output_dir / filename
    projections.to_csv(file_path, index=False)
    return file_path
