import copy
import math

import numpy as np
import pandas as pd

from .model import Position

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


def calculate_points_above_replacement(projections, league_roster, include_bench=True):
    replacement_level_ranks = _calculate_replacement_level_ranks(league_roster, include_bench)
    replacement_level_points = _calculate_replacement_level_points(projections, replacement_level_ranks)

    # Build a flat lookup: (projection_source, position) -> replacement_points
    repl_lookup = {}
    for source, pos_dict in replacement_level_points.items():
        for pos, pts in pos_dict.items():
            repl_lookup[(source, pos)] = pts

    # Compute fallback replacement points per source (max across positions)
    fallback = {}
    for source, pos_dict in replacement_level_points.items():
        fallback[source] = max(pos_dict.values())

    # Explode multi-position players into one row per position
    expanded = projections[["ProjectionSource", "Position", "Points"]].copy()
    expanded["_orig_idx"] = expanded.index
    expanded["_positions"] = expanded["Position"].str.split("/")
    expanded = expanded.explode("_positions")

    # Look up replacement points for each (source, position) pair
    expanded["_repl_pts"] = [
        repl_lookup.get((src, pos), np.nan) for src, pos in zip(expanded["ProjectionSource"], expanded["_positions"])
    ]

    # For each original row, pick the position with the lowest replacement points
    # (most favorable for the player -- maximizes PAR)
    best_repl = expanded.groupby("_orig_idx")["_repl_pts"].min()

    # Fill NaN (no matching position) with fallback
    fallback_series = projections["ProjectionSource"].map(fallback)
    replacement_pts = best_repl.reindex(projections.index).fillna(fallback_series)

    return projections["Points"] - replacement_pts
