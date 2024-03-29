import logging
from datetime import datetime

import pandas as pd

from .model import StatType
from .modify import (
    add_auction_values,
    add_league_info,
    add_mean_projections,
    add_pitcher_position,
    add_points,
    add_points_above_replacement,
    order_and_rank_rows,
    order_columns,
    replace_positions,
)

logger = logging.getLogger(__name__)

BAT_START_COLUMNS = [
    "ProjectionType",
    "Rank",
    "Position",
    "Name",
    "PlayerId",
    "League",
    "Team",
    "ShortName",
    "Status",
    "Salary",
    "Contract",
    "Points",
    "Pts/G",
    "PAR",
    "AuctionValue",
    "ADP",
]
PIT_START_COLUMNS = [
    "ProjectionType",
    "Rank",
    "Position",
    "Name",
    "PlayerId",
    "League",
    "Team",
    "ShortName",
    "Status",
    "Salary",
    "Contract",
    "Points",
    "Pts/IP",
    "PAR",
    "AuctionValue",
    "ADP",
]

FANGRAPHS_TO_FANTRAX_FILE = "sitemaps/fangraphs_to_fantrax.csv"


def augment_projections(
    bat_projections, pit_projections, league=None, league_export=None, exclude_rostered_players_from_value_calc=False
):
    bat_projections = add_mean_projections(bat_projections)
    pit_projections = add_mean_projections(pit_projections)

    rostered_players = None
    if league_export is not None:
        fangraphs_to_fantrax_map = pd.read_csv(FANGRAPHS_TO_FANTRAX_FILE)
        league_export = league_export.merge(fangraphs_to_fantrax_map, left_on="ID", right_on="FantraxPlayerId")

        bat_projections = replace_positions(bat_projections, league_export)

        bat_projections = add_league_info(bat_projections, league_export)
        pit_projections = add_league_info(pit_projections, league_export)

        if exclude_rostered_players_from_value_calc:
            rostered_players = league_export[league_export["Status"] != "FA"]

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

    bat_projections = order_columns(bat_projections, BAT_START_COLUMNS)
    pit_projections = order_columns(pit_projections, PIT_START_COLUMNS)
    # TODO: Format stats

    return bat_projections, pit_projections


def write_projections_file(projections, stat_type, output_dir, league_name=None, custom=None):
    current_time_string = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{stat_type.value}_{current_time_string}.csv"
    if custom:
        filename = f"{custom}_{filename}"
    if league_name:
        filename = f"{league_name}_{filename}"
    projections.to_csv(output_dir / filename, index=False)
