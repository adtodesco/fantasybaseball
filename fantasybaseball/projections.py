import logging
from datetime import datetime

from .model import ProjectionSource, ProjectionSourceName, StatCategory
from .columns import BAT_START_COLUMNS, PIT_START_COLUMNS
from .playerids import load_player_id_map, merge_with_league_export
from .aggregation import add_mean_projection
from .formatting import format_currency_for_csv, format_stats, order_and_rank_rows, order_columns
from .points import calculate_points
from .positions import replace_pitcher_position, replace_positions
from .replacement import calculate_points_above_replacement
from .valuation import calculate_auction_values

logger = logging.getLogger(__name__)


def augment_projections(
    bat_projections, pit_projections, league_config=None, league_export=None, include_bench=True, ros=False,
    player_id_map_path=None, power_factor=None,
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

    if league_export is not None:
        player_id_map = load_player_id_map(player_id_map_path)

        # Add MLBAM IDs to league export via Fantrax ID
        league_export = league_export.merge(
            player_id_map[["MlbamId", "FangraphsId", "FantraxId"]],
            left_on="ID",        # Fantrax ID from export (e.g., "*02yc4*")
            right_on="FantraxId",
            how="left"
        )

        # Join projections with league export on MLBAM ID (primary)
        # with fallback to Fangraphs ID for players without MLBAM
        bat_projections = merge_with_league_export(bat_projections, league_export)
        pit_projections = merge_with_league_export(pit_projections, league_export)

        bat_projections = replace_positions(bat_projections, league_export)

    # Strip pitcher positions from batting projections (fixes two-way players like Ohtani)
    if "Position" in bat_projections.columns:
        bat_projections["Position"] = bat_projections["Position"].str.replace(r"[,/]?P", "", regex=True).str.strip("/,")

    if league_config:
        if "scoring" in league_config:
            bat_projections["Points"] = calculate_points(
                bat_projections, StatCategory.BATTING, league_config["scoring"], use_stat_proxies=True
            )
            bat_projections["Pts/G"] = bat_projections["Points"] / bat_projections["G"]

            pit_projections["Points"] = calculate_points(
                pit_projections, StatCategory.PITCHING, league_config["scoring"], use_stat_proxies=True
            )
            pit_projections["Pts/IP"] = pit_projections["Points"] / pit_projections["IP"]

            if "roster" in league_config:
                bat_projections["PAR"] = calculate_points_above_replacement(
                    bat_projections, league_config["roster"], include_bench
                )
                pit_projections = replace_pitcher_position(pit_projections, league_config["roster"])
                pit_projections["PAR"] = calculate_points_above_replacement(
                    pit_projections, league_config["roster"], include_bench
                )

                if "salary" in league_config:
                    roster, salary = league_config["roster"], league_config["salary"]
                    bat_projections["AuctionValue"], pit_projections["AuctionValue"] = \
                        calculate_auction_values(bat_projections, pit_projections, roster, salary)
                    bat_projections["ContractValue"] = bat_projections["AuctionValue"] - bat_projections["Salary"]
                    pit_projections["ContractValue"] = pit_projections["AuctionValue"] - pit_projections["Salary"]

                    if power_factor:
                        bat_projections["CurvedValue"], pit_projections["CurvedValue"] = \
                            calculate_auction_values(bat_projections, pit_projections, roster, salary, power_factor)

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

    columns = BAT_START_COLUMNS if stat_category == StatCategory.BATTING else PIT_START_COLUMNS
    output = format_currency_for_csv(projections, columns)
    output.to_csv(file_path, index=False)
    return file_path
