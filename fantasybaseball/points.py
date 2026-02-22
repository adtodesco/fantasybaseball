from .model import StatCategory
from .scoring import calculate_score_vector


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
