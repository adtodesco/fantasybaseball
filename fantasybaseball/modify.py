import copy
import functools
import math

import pandas as pd

from .model import Position, StatType
from .scoring import calculate_score_vector


def add_mean_projections(projections):
    projection_types = projections["ProjectionType"].unique()

    group_by = ["Name", "PlayerId", "Position", "League", "Team", "ShortName"]
    if "Position" not in projections:
        group_by.remove("Position")

    mean_projections = (
        projections[projections["ProjectionType"].isin(projection_types)].groupby(by=group_by).mean(numeric_only=True)
    )
    mean_projections["ProjectionType"] = "mean"
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


FLEX_POSITIONS = {
    Position.CI: [Position.FiB, Position.ThB],
    Position.MI: [Position.SeB, Position.SS],
    Position.UTIL: [Position.C, Position.FiB, Position.SeB, Position.SS, Position.ThB, Position.OF],
}


def _calculate_replacement_level_ranks(league_roster):
    league_roster = copy.deepcopy(league_roster)
    team_count = league_roster["teams"]
    positions = league_roster["positions"]
    bench_count = positions.pop("bench", None)
    positions = {Position(p): c for p, c in league_roster["positions"].items()}
    starter_count = sum(positions.values())

    if bench_count:
        for position in positions.keys():
            bench_spots = (positions[position] / starter_count) * bench_count
            positions[position] += bench_spots

    for flex_position, eligible_positions in FLEX_POSITIONS.items():
        if flex_position in positions:
            for eligible_position in eligible_positions:
                if eligible_position in positions:
                    positions[eligible_position] += positions[flex_position] / len(eligible_positions)
            del positions[flex_position]

    return {p: c * team_count for p, c in positions.items()}


def _calculate_replacement_level_points(projections, stat_type, replacement_level_ranks):
    replacement_level_points = dict()
    for projection_type in projections["ProjectionType"].unique():
        replacement_level_points[projection_type] = dict()
        for position, rank in replacement_level_ranks.items():
            if stat_type == StatType.BATTING:
                position_projections = projections.loc[
                    (projections["ProjectionType"] == projection_type)
                    & projections["Position"].str.contains(position.value)
                ]
            else:
                position_projections = projections.loc[projections["ProjectionType"] == projection_type].nlargest(
                    math.ceil(rank), "Points"
                )
            points = position_projections.nlargest(math.ceil(rank), "Points").iloc[-1]["Points"]
            replacement_level_points[projection_type][position.value] = points

    return replacement_level_points


def _calculate_points_above_replacement(replacement_level_points, projection):
    projection_replacement_level_points = replacement_level_points[projection["ProjectionType"]]
    positions = projection["Position"].split("/") if "Position" in projection else [Position.P.value]
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


def add_points_above_replacement(projections, stat_type, league_roster):
    replacement_level_ranks = _calculate_replacement_level_ranks(league_roster)
    if stat_type == StatType.BATTING:
        replacement_level_ranks.pop(Position.P)
    else:
        replacement_level_ranks = {Position.P: replacement_level_ranks[Position.P]}

    replacement_level_points = _calculate_replacement_level_points(projections, stat_type, replacement_level_ranks)
    calculate_points_above_replacement = functools.partial(
        _calculate_points_above_replacement, replacement_level_points
    )
    points_above_replacement = projections.apply(calculate_points_above_replacement, axis=1)
    projections["PAR"] = points_above_replacement

    return projections


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
