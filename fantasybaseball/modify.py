import copy
import functools
import math

import numpy as np
import pandas as pd

from .model import Position, StatType
from .scoring import calculate_score_vector


def add_mean_projection(projections, projection_types=None, name="mean"):
    if projection_types is None:
        projection_types = projections["ProjectionType"].unique()
    else:
        projection_types = [p.value for p in projection_types]

    group_by = ["Name", "PlayerId", "Position", "League", "Team", "ShortName"]
    if "Position" not in projections:
        group_by.remove("Position")

    # Fill missing values with "--" so free agents can be grouped
    projections[group_by] = projections[group_by].fillna("--")

    mean_projections = (
        projections[projections["ProjectionType"].isin(projection_types)].groupby(by=group_by).mean(numeric_only=True)
    )
    mean_projections["ProjectionType"] = name
    mean_projections.reset_index(inplace=True)

    return pd.concat([projections, mean_projections], ignore_index=True)


def add_points(projections, stat_type, league_scoring, use_stat_proxies=False):
    stat_cols = list(projections.select_dtypes(include=["number"]))
    score_vector = calculate_score_vector(
        stat_type=stat_type,
        stat_cols=stat_cols,
        league_scoring=league_scoring,
        use_stat_proxies=use_stat_proxies,
    )

    if stat_type == StatType.BATTING:
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


def _calculate_replacement_level_points(projections, replacement_level_ranks):
    replacement_level_points = dict()
    for projection_type in projections["ProjectionType"].unique():
        replacement_level_points[projection_type] = dict()
        for position, rank in replacement_level_ranks.items():
            position_projections = projections.loc[
                (projections["ProjectionType"] == projection_type)
                & projections["Position"].str.contains(position.value)
            ]
            if not position_projections.empty:
                points = position_projections.nlargest(math.ceil(rank), "Points").iloc[-1]["Points"]
                replacement_level_points[projection_type][position.value] = points

    return replacement_level_points


def _calculate_points_above_replacement(replacement_level_points, projection):
    projection_replacement_level_points = replacement_level_points[projection["ProjectionType"]]
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
        print(f"replacement position is None for player {projection['Name']} with positions {positions}")
        replacement_position = max(projection_replacement_level_points, key=projection_replacement_level_points.get)
        print(f"using {replacement_position} as replacement position")

    return projection["Points"] - projection_replacement_level_points[replacement_position]


def add_points_above_replacement(projections, league_roster):
    replacement_level_ranks = _calculate_replacement_level_ranks(league_roster)
    print(f"replacement_level_ranks: {replacement_level_ranks}")
    replacement_level_points = _calculate_replacement_level_points(projections, replacement_level_ranks)
    print(f"replacement_level_points: {replacement_level_points}")
    calculate_points_above_replacement = functools.partial(
        _calculate_points_above_replacement, replacement_level_points
    )
    points_above_replacement = projections.apply(calculate_points_above_replacement, axis=1)
    projections["PAR"] = points_above_replacement

    return projections


def _calculate_auction_value(par_value, minimum_salary, projection):
    if projection["ProjectionType"] in par_value:
        return projection["PAR"] * par_value[projection["ProjectionType"]] + minimum_salary

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
        rostered_players_ids = list()
    else:
        rostered_players_total_salary = rostered_players["Salary"].sum()
        rostered_players_ids = rostered_players["FangraphsPlayerId"]
    team_count = league_roster["teams"]
    roster_spots = sum(league_roster["positions"].values())
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    total_auction_value = (team_count * salary_cap - rostered_players_total_salary) - (
        team_count * roster_spots * minimum_salary - len(rostered_players_ids) * rostered_players_majors_perc
    )

    total_par = dict()
    bat_projection_types = bat_projections["ProjectionType"].unique()
    pit_projection_types = pit_projections["ProjectionType"].unique()
    projection_types = set(bat_projection_types).intersection(set(pit_projection_types))
    for projection_type in projection_types:
        bat_par = bat_projections.loc[
            (bat_projections["ProjectionType"] == projection_type)
            & (bat_projections["PAR"] > 0.0)
            & (~bat_projections["PlayerId"].isin(rostered_players_ids))
        ]["PAR"].sum()
        pit_par = pit_projections.loc[
            (pit_projections["ProjectionType"] == projection_type)
            & (pit_projections["PAR"] > 0.0)
            & (~pit_projections["PlayerId"].isin(rostered_players_ids))
        ]["PAR"].sum()
        total_par[projection_type] = bat_par + pit_par

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
    projections = projections.sort_values(["ProjectionType", order_by], ascending=[True, asc])
    rank = projections.groupby("ProjectionType")[order_by].rank(ascending=asc).astype(int)
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
    league_player = league_export[league_export["FangraphsPlayerId"] == projection["PlayerId"]]
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
    projections = projections.merge(
        league_export[["Status", "Salary", "Contract", "FangraphsPlayerId"]],
        left_on="PlayerId",
        right_on="FangraphsPlayerId",
    )
    del projections["FangraphsPlayerId"]

    return projections


def format_stats(projections, columns):
    for column, col_type, *decimals in columns:
        if col_type == "float" and decimals:
            projections[column] = projections[column].round(decimals[0])
        elif col_type == "int":
            projections[column] = projections[column].astype(int)
        elif col_type == "string":
            projections[column] = projections[column].astype(str)
        elif col_type == "currency" and decimals:
            projections[column] = projections[column].round(decimals[0]).apply(lambda x: f"${x:,.2f}")
    return projections
