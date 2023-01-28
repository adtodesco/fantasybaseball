import logging

import pandas as pd

from .model import Stat, StatType

logger = logging.getLogger(__name__)


BAT_STAT_PROXIES = {
    Stat.TB.value: {
        Stat.H.value: 1,
        Stat.Dbl.value: 1,
        Stat.Trp.value: 2,
        Stat.HR.value: 3,
    },
    Stat.Sng.value: {
        Stat.H.value: 1,
        Stat.Dbl.value: -1,
        Stat.Trp.value: -1,
        Stat.HR.value: -1,
    },
    # Based on league average GDP per AB from 2019 season  (source: https://tinyurl.com/y66bqflr)
    Stat.GDP.value: {Stat.AB.value: 0.02},
}
PIT_STAT_PROXIES = {
    # Based on league average HB per IP from 2019 season (source: https://tinyurl.com/y5aazd8g)
    Stat.HB.value: {Stat.IP.value: 0.05},
    # Based on league average QS per GS from 2019 season (source: https://tinyurl.com/y4wuhl26)
    Stat.QS.value: {Stat.GS.value: 0.37},
    # Based on league average CG per GS from 2019 season (source: https://tinyurl.com/y5aazd8g)
    Stat.CG.value: {Stat.GS.value: 0.01},
    # Based on league average SO per GS from 2019 season (source: https://tinyurl.com/y5aazd8g)
    Stat.SHO.value: {Stat.GS.value: 0.01},
    # Based on league average BS per SV from 2019 season (source: https://tinyurl.com/y5aazd8g)
    Stat.BS.value: {Stat.SV.value: 0.58},
}


def calculate_score_vector(stat_type, stat_cols, league_scoring, use_stat_proxies=False):
    if isinstance(stat_type, str):
        stat_type = StatType(str)
    if stat_type not in [StatType.BATTING, StatType.PITCHING]:
        raise TypeError(f"stat_type must be a `StatType` object.")
    stat_proxies = dict()
    if use_stat_proxies:
        if stat_type == StatType.BATTING:
            stat_proxies = BAT_STAT_PROXIES
        else:
            stat_proxies = PIT_STAT_PROXIES

    coefficients = {c: 0.0 for c in stat_cols}
    for stat, points in league_scoring[stat_type.value].items():
        if stat in stat_cols:
            coefficients[stat] += float(points)
        elif stat in stat_proxies:
            for s, c in stat_proxies[stat].items():
                if s in coefficients:
                    coefficients[s] += c * float(points)
                else:
                    logger.debug(f"Cannot find stat '{s}' (used as a proxy to calculate '{stat}') in stat cols.")
        else:
            logger.debug(f"Cannot find stat '{stat}' in stat cols or stat proxies.")

    return pd.Series(data=coefficients, index=stat_cols)
