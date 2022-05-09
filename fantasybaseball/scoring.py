import logging
import pandas as pd

from .model import StatType


logger = logging.getLogger(__name__)


def calculate_score_vector(stat_type, stat_cols, league, custom_stats=None):
    """

    Args:
        stat_type:
        stat_cols:
        league:
        custom_stats:

    Returns:

    """
    if isinstance(stat_type, str):
        stat_type = StatType(str)
    if stat_type not in [StatType.BATTING, StatType.PITCHING]:
        raise TypeError(f"stat_type must be a `StatType` object.")

    coefficients = {c: 0.0 for c in stat_cols}
    for stat, points in league[stat_type.name].items():
        if stat in stat_cols:
            coefficients[stat] += float(points)
        elif stat in custom_stats:
            for s, c in custom_stats[stat].items():
                if s in coefficients:
                    coefficients[s] += c * float(points)
                else:
                    logger.debug(f"Cannot find stat '{s}' (used to calculate custom stat '{stat}') in stat cols.")
        else:
            logger.debug(f"Cannot find stat '{stat}' in stat cols or custom stats.")

    return pd.Series(data=coefficients, index=stat_cols)
