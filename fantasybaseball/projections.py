import logging
from datetime import datetime

import pandas as pd

from .model import ProjectionType, StatType
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
    ("ProjectionType", "string"),
    ("Rank", "int"),
    ("Position", "string"),
    ("Name", "string"),
    ("PlayerId", "string"),
    ("FantraxPlayerId", "string"),
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
    ("ProjectionType", "string"),
    ("Rank", "int"),
    ("Position", "string"),
    ("Name", "string"),
    ("PlayerId", "string"),
    ("FantraxPlayerId", "string"),
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

FANGRAPHS_TO_FANTRAX_FILE = "sitemaps/fangraphs_to_fantrax.csv"


def augment_projections(bat_projections, pit_projections, league=None, league_export=None):
    bat_projections = add_mean_projection(
        bat_projections,
        projection_types=[
            ProjectionType.OOPSY,
            ProjectionType.STEAMER,
            ProjectionType.THE_BAT_X,
            ProjectionType.ZIPSDC,
        ],
        name="zobs",
    )
    pit_projections = add_mean_projection(
        pit_projections,
        projection_types=[
            ProjectionType.OOPSY,
            ProjectionType.STEAMER,
            ProjectionType.THE_BAT,
            ProjectionType.ZIPSDC,
        ],
        name="zobs",
    )

    rostered_players = None
    if league_export is not None:
        fangraphs_to_fantrax_map = pd.read_csv(FANGRAPHS_TO_FANTRAX_FILE)
        league_export = league_export.merge(fangraphs_to_fantrax_map, left_on="ID", right_on="FantraxPlayerId")

        bat_projections = replace_positions(bat_projections, league_export)

        bat_projections = add_league_info(bat_projections, league_export)
        pit_projections = add_league_info(pit_projections, league_export)

    if league:
        if "scoring" in league:
            bat_projections = add_points(bat_projections, StatType.BATTING, league["scoring"], use_stat_proxies=True)
            pit_projections = add_points(pit_projections, StatType.PITCHING, league["scoring"], use_stat_proxies=True)

            if "roster" in league:
                bat_projections = add_points_above_replacement(bat_projections, league["roster"])
                pit_projections = add_pitcher_position(pit_projections, league["roster"])
                pit_projections = add_points_above_replacement(pit_projections, league["roster"])

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


def write_projections_file(projections, stat_type, output_dir, league_name=None, custom=None):
    current_time_string = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{stat_type.value}_{current_time_string}.csv"
    if custom:
        filename = f"{custom}_{filename}"
    if league_name:
        filename = f"{league_name}_{filename}"
    file_path = output_dir / filename
    projections.to_csv(file_path, index=False)
    return file_path
