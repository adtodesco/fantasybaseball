import copy
import functools
import math

import numpy as np
import pandas as pd

from .model import Position, ProjectionSource, ProjectionSourceName, StatCategory
from .scoring import calculate_score_vector


def standardize_name_format(name):
    """Converts 'Last, First' name format to 'First Last'."""
    if isinstance(name, str) and ", " in name:
        parts = name.split(", ")
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name

def add_mean_projection(projections, projection_sources=None, name="mean"):
    if projection_sources is None:
        projection_sources = projections["ProjectionSource"].unique()
    else:
        projection_sources = [p.value for p in projection_sources]

    group_by = ["Name", "MlbamId", "FangraphsId", "Position", "League", "Team", "ShortName"]
    if "Position" not in projections:
        group_by.remove("Position")

    # Fill missing values so free agents can be grouped
    # String columns get "--", integer ID columns get -1
    string_cols = ["Name", "Position", "League", "Team", "ShortName"]
    int_cols = ["MlbamId", "FangraphsId"]

    for col in string_cols:
        if col in group_by and col in projections.columns:
            projections[col] = projections[col].fillna("--")

    for col in int_cols:
        if col in group_by and col in projections.columns:
            projections[col] = projections[col].fillna(-1)

    mean_projections = (
        projections[projections["ProjectionSource"].isin(projection_sources)]
        .groupby(by=group_by)
        .mean(numeric_only=True)
    )
    mean_projections["ProjectionSource"] = name
    mean_projections.reset_index(inplace=True)

    return pd.concat([projections, mean_projections], ignore_index=True)


def add_points(projections, stat_category, league_scoring, use_stat_proxies=False):
    stat_cols = list(projections.select_dtypes(include=["number"]))
    score_vector = calculate_score_vector(
        stat_category=stat_category,
        stat_cols=stat_cols,
        league_scoring=league_scoring,
        use_stat_proxies=use_stat_proxies,
    )

    if stat_category == StatCategory.BATTING:
        count = projections["G"]
        points_per_count_label = "Pts/G"
    else:
        count = projections["IP"]
        points_per_count_label = "Pts/IP"

    points = projections.loc[:, stat_cols].fillna(0.0).dot(score_vector)
    points_per_count = points / count
    projections["Points"] = points
    projections[points_per_count_label] = points_per_count

    return projections


def add_pitcher_position(projections, league_roster):
    projections = projections.copy()
    if "SP" in league_roster["positions"] or "RP" in league_roster["positions"]:
        projections["Position"] = ["SP" if gs > 0.0 else "RP" for gs in projections["GS"]]
    else:
        projections["Position"] = "P"

    return projections


FLEX_POSITIONS = {
    Position.CI: [Position.FiB, Position.ThB],
    Position.MI: [Position.SeB, Position.SS],
    Position.UTIL: [Position.C, Position.FiB, Position.SeB, Position.SS, Position.ThB, Position.OF],
}


def _calculate_replacement_level_ranks(league_roster, include_bench=True):
    league_roster = copy.deepcopy(league_roster)
    team_count = league_roster["teams"]
    if not isinstance(team_count, int):
        team_count = len(team_count)
    positions = league_roster["positions"]
    bench_count = positions.pop("bench", None)
    positions = {Position(p): c for p, c in league_roster["positions"].items()}
    starter_count = sum(positions.values())

    if bench_count and include_bench:
        for position in positions.keys():
            bench_spots = positions[position] / starter_count * bench_count
            positions[position] += bench_spots

    for flex_position, eligible_positions in FLEX_POSITIONS.items():
        if flex_position in positions:
            for eligible_position in eligible_positions:
                if eligible_position in positions:
                    positions[eligible_position] += positions[flex_position] / len(eligible_positions)
            del positions[flex_position]

    return {p: c * team_count for p, c in positions.items()}


def _calculate_replacement_level_points(projections, replacement_level_ranks, replacement_players=5):
    replacement_level_points = dict()
    for projection_source in projections["ProjectionSource"].unique():
        replacement_level_points[projection_source] = dict()
        for position, rank in replacement_level_ranks.items():
            position_projections = projections.loc[
                (projections["ProjectionSource"] == projection_source)
                & projections["Position"].str.contains(position.value)
            ]
            if not position_projections.empty:
                points = (
                    position_projections.nlargest(math.ceil(rank + replacement_players - 1), "Points")
                    .nsmallest(replacement_players, "Points")["Points"]
                    .mean()
                )
                replacement_level_points[projection_source][position.value] = points

    return replacement_level_points


def _calculate_points_above_replacement(replacement_level_points, projection):
    projection_replacement_level_points = replacement_level_points[projection["ProjectionSource"]]
    positions = projection["Position"].split("/")
    replacement_position = None
    for position in positions:
        if position in projection_replacement_level_points:
            if (
                replacement_position is None
                or projection_replacement_level_points[position]
                < projection_replacement_level_points[replacement_position]
            ):
                replacement_position = position

    if replacement_position is None:
        replacement_position = max(projection_replacement_level_points, key=projection_replacement_level_points.get)

    return projection["Points"] - projection_replacement_level_points[replacement_position]


def add_points_above_replacement(projections, league_roster, include_bench=True):
    replacement_level_ranks = _calculate_replacement_level_ranks(league_roster, include_bench)
    replacement_level_points = _calculate_replacement_level_points(projections, replacement_level_ranks)
    calculate_points_above_replacement = functools.partial(
        _calculate_points_above_replacement, replacement_level_points
    )
    points_above_replacement = projections.apply(calculate_points_above_replacement, axis=1)
    projections["PAR"] = points_above_replacement

    return projections


def _calculate_auction_value(par_value, minimum_salary, projection):
    if projection["ProjectionSource"] in par_value:
        return projection["PAR"] * par_value[projection["ProjectionSource"]] + minimum_salary

    return np.nan


def add_auction_values(
    bat_projections,
    pit_projections,
    league_roster,
    league_salary,
    rostered_players=None,
    rostered_players_majors_perc=0.7,
):
    if rostered_players is None:
        rostered_players_total_salary = 0.0
        rostered_mlbam_ids = list()
        rostered_fangraphs_ids = list()
    else:
        rostered_players_total_salary = rostered_players["Salary"].sum()
        rostered_mlbam_ids = rostered_players["MlbamId"].dropna().tolist()
        rostered_fangraphs_ids = rostered_players["FangraphsId"].dropna().tolist()
    team_count = league_roster["teams"]
    roster_spots = sum(league_roster["positions"].values())
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    rostered_count = max(len(rostered_mlbam_ids), len(rostered_fangraphs_ids))
    total_auction_value = (team_count * salary_cap - rostered_players_total_salary) - (
        team_count * roster_spots * minimum_salary - rostered_count * rostered_players_majors_perc
    )

    total_par = dict()
    bat_projection_sources = bat_projections["ProjectionSource"].unique()
    pit_projection_sources = pit_projections["ProjectionSource"].unique()
    projection_sources = set(bat_projection_sources).union(set(pit_projection_sources))
    for projection_source in projection_sources:
        bat_par = bat_projections.loc[
            (bat_projections["ProjectionSource"] == projection_source)
            & (bat_projections["PAR"] > 0.0)
            & (~bat_projections["MlbamId"].isin(rostered_mlbam_ids))
            & (~bat_projections["FangraphsId"].isin(rostered_fangraphs_ids))
        ]["PAR"].sum()

        # Hack around missing BAT X pitcher projections
        pit_projection_source = projection_source
        if projection_source == ProjectionSource(ProjectionSourceName.THE_BAT_X):
            pit_projection_source = ProjectionSource(ProjectionSourceName.THE_BAT).value
        elif projection_source == ProjectionSource(ProjectionSourceName.THE_BAT_X, ros=True):
            pit_projection_source = ProjectionSource(ProjectionSourceName.THE_BAT, ros=True).value

        pit_par = pit_projections.loc[
            (pit_projections["ProjectionSource"] == pit_projection_source)
            & (pit_projections["PAR"] > 0.0)
            & (~pit_projections["MlbamId"].isin(rostered_mlbam_ids))
            & (~pit_projections["FangraphsId"].isin(rostered_fangraphs_ids))
        ]["PAR"].sum()
        total_par[projection_source] = bat_par + pit_par

    par_value = {p: total_auction_value / t for p, t in total_par.items()}
    calculate_auction_value = functools.partial(_calculate_auction_value, par_value, minimum_salary)

    bat_auction_values = bat_projections.apply(calculate_auction_value, axis=1)
    bat_projections["AuctionValue"] = bat_auction_values
    bat_projections["ContractValue"] = bat_projections["AuctionValue"] - bat_projections["Salary"]

    pit_auction_values = pit_projections.apply(calculate_auction_value, axis=1)
    pit_projections["AuctionValue"] = pit_auction_values
    pit_projections["ContractValue"] = pit_projections["AuctionValue"] - pit_projections["Salary"]

    return bat_projections, pit_projections


def order_and_rank_rows(projections, order_by, asc=True):
    projections = projections.sort_values(["ProjectionSource", order_by], ascending=[True, asc])
    rank = projections.groupby("ProjectionSource")[order_by].rank(ascending=asc).astype(int)
    if "Rank" in projections:
        projections.pop("Rank")
    projections.insert(1, "Rank", rank)
    return projections


def order_columns(projections, columns, front=True):
    projections = projections.copy()
    insert_at = projections.shape[1] - 1
    if front:
        columns = reversed(columns)
        insert_at = 0
    for col_name in columns:
        try:
            col = projections.pop(col_name)
            projections.insert(insert_at, col.name, col)
        except KeyError:
            pass

    return projections


def _replace_position(league_export, projection):
    position = projection["Position"]

    # Try matching on MLBAM ID first
    if pd.notna(projection.get("MlbamId")):
        league_player = league_export[league_export["MlbamId"] == projection["MlbamId"]]
        if not league_player.empty:
            position = league_player.iloc[0]["Position"]
            position = position.replace(",", "/")
            return position

    # Fallback to Fangraphs ID
    if pd.notna(projection.get("FangraphsId")):
        league_player = league_export[league_export["FangraphsId"] == projection["FangraphsId"]]
        if not league_player.empty:
            position = league_player.iloc[0]["Position"]
            position = position.replace(",", "/")

    return position


def replace_positions(projections, league_export):
    replace_position = functools.partial(_replace_position, league_export)
    replaced_positions = projections.apply(replace_position, axis=1)
    projections["Position"] = replaced_positions
    return projections


def add_league_info(projections, league_export):
    # This function is deprecated - merging now happens in projections.py
    # via _merge_with_league_export(). Keeping this as a no-op for compatibility.
    return projections


def format_stats(projections, columns):
    for column, col_type, *decimals in columns:
        if column not in projections:
            continue

        if col_type == "float" and decimals:
            projections[column] = projections[column].round(decimals[0])
        elif col_type == "int":
            projections[column] = pd.to_numeric(projections[column], errors="coerce").fillna(0).astype(int)
        elif col_type == "string":
            projections[column] = projections[column].astype(str)
        elif col_type == "currency" and decimals:
            projections[column] = projections[column].round(decimals[0]).apply(lambda x: f"${x:,.2f}")
    return projections
