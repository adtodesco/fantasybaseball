import logging
from datetime import datetime

from .model import StatType
from .modify import (
    add_mean_projections,
    add_points,
    add_points_above_replacement,
    order_and_rank_rows,
    order_columns,
)

logger = logging.getLogger(__name__)


def augment_projections(bat_projections, pit_projections, league=None):
    bat_projections = add_mean_projections(bat_projections)
    pit_projections = add_mean_projections(pit_projections)

    if league:
        if "scoring" in league:
            bat_projections = add_points(bat_projections, StatType.BATTING, league["scoring"], use_stat_proxies=True)
            pit_projections = add_points(pit_projections, StatType.PITCHING, league["scoring"], use_stat_proxies=True)

            bat_projections = order_and_rank_rows(bat_projections, order_by="Points", asc=False)
            pit_projections = order_and_rank_rows(pit_projections, order_by="Points", asc=False)
            if "roster" in league:
                bat_projections = add_points_above_replacement(bat_projections, StatType.BATTING, league["roster"])
                pit_projections = add_points_above_replacement(pit_projections, StatType.PITCHING, league["roster"])

    bat_projections = order_columns(
        bat_projections,
        [
            "ProjectionType",
            "Rank",
            "Position",
            "Name",
            "PlayerId",
            "League",
            "Team",
            "ShortName",
            "Points",
            "PAR",
            "Pts/G",
        ],
    )
    pit_projections = order_columns(
        pit_projections,
        ["ProjectionType", "Rank", "Name", "PlayerId", "League", "Team", "ShortName", "Points", "PAR", "Pts/IP"],
    )
    # TODO: Format stats

    return bat_projections, pit_projections


def write_projections_file(projections, stat_type, output_dir):
    current_time_string = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{stat_type.value}_{current_time_string}.csv"
    projections.to_csv(output_dir / filename, index=False)
