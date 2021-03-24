import logging
import pandas as pd

from .glossary import Stat, StatType


logger = logging.getLogger(__name__)


def calculate_points(stat_type, stats, league):
    """

    Args:
        stat_type:
        stats:
        league:

    Returns:

    """
    if isinstance(stat_type, str):
        stat_type = StatType(str)
    if stat_type not in [StatType.BATTING, StatType.PITCHING]:
        raise ValueError("Unrecognized stat_type: {}".format(stat_type))
    total_points = 0
    for stat, points in league[stat_type.name].items():
        if stat in _POINT_FUNCS:
            total_points += _POINT_FUNCS[stat](stats=stats, points=points, stat=stat)

    return total_points


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
        raise ValueError("Unrecognized stat_type: {}".format(stat_type))

    coefficients = {c: 0.0 for c in stat_cols}
    for stat, points in league[stat_type.name].items():
        if stat in custom_stats:
            for s, c in custom_stats[stat].items():
                if s in coefficients:
                    coefficients[s] += c * float(points)
                else:
                    logger.debug(
                        "Cannot find stat '{}' (used to calculate custom stat '{}') in stat cols.".format(
                            s, stat
                        )
                    )
        elif stat in stat_cols:
            coefficients[stat] += float(points)
        else:
            logger.debug(
                "Cannot find stat '{}' in stat cols or custom stats.".format(stat)
            )

    return pd.Series(data=coefficients, index=stat_cols)


def _default(**kwargs):
    assert kwargs["stat"] in kwargs["stats"]
    return int(kwargs["stats"][kwargs["stat"]]) * int(kwargs["points"])


def _total_bases(**kwargs):
    assert all(
        stat in kwargs["stats"]
        for stat in [Stat.H.value, Stat.Dbl.value, Stat.Trp.value, Stat.HR.value]
    )
    total_bases = (
        int(kwargs["stats"][Stat.H.value])
        + int(kwargs["stats"][Stat.Dbl.value])
        + int(kwargs["stats"][Stat.Trp.value]) * 2
        + int(kwargs["stats"][Stat.HR.value]) * 3
    )
    return total_bases * int(kwargs["points"])


def _singles(**kwargs):
    assert all(
        stat in kwargs["stats"]
        for stat in [Stat.H.value, Stat.Dbl.value, Stat.Trp.value, Stat.HR.value]
    )
    singles = (
        int(kwargs["stats"][Stat.H.value])
        - int(kwargs["stats"][Stat.Dbl.value])
        - int(kwargs["stats"][Stat.Trp.value])
        - int(kwargs["stats"][Stat.HR.value])
    )
    return singles * int(kwargs["points"])


def _double_plays(**kwargs):
    assert Stat.AB.value in kwargs["stats"]
    # Based on league average GDP per AB from 2019 season (source: https://tinyurl.com/y66bqflr)
    average_gdp_per_ab = 0.02
    return round(average_gdp_per_ab * int(kwargs["stats"][Stat.AB.value])) * int(
        kwargs["points"]
    )


def _hit_by_pitch(**kwargs):
    if Stat.HBP.value in kwargs["stats"]:
        _default(**kwargs)
    return 0


def _cycles(**kwargs):
    # Ignoring cycles
    return 0


def _innings_pitched(**kwargs):
    assert Stat.IP.value in kwargs["stats"]
    return round(float(kwargs["stats"][Stat.IP.value]) * int(kwargs["points"]))


def _hit_batters(**kwargs):
    assert Stat.IP.value in kwargs["stats"]
    # Based on league average HB per IP from 2019 season (source: https://tinyurl.com/y5aazd8g)
    average_hb_per_ip = 0.05
    return round(average_hb_per_ip * int(kwargs["stats"][Stat.AB.value])) * int(
        kwargs["points"]
    )


def _quality_starts(**kwargs):
    assert Stat.GS.value in kwargs["stats"]
    # Based on league average QS per GS from 2019 season (source: https://tinyurl.com/y4wuhl26)
    average_qs_per_gs = 0.37
    return round(average_qs_per_gs * int(kwargs["stats"][Stat.AB.value])) * int(
        kwargs["points"]
    )


def _complete_games(**kwargs):
    assert Stat.GS.value in kwargs["stats"]
    # Based on league average CG per GS from 2019 season (source: https://tinyurl.com/y5aazd8g)
    average_cg_per_gs = 0.01
    return round(average_cg_per_gs * int(kwargs["stats"][Stat.GS.value])) * int(
        kwargs["points"]
    )


def _shut_outs(**kwargs):
    assert Stat.GS.value in kwargs["stats"]
    # Based on league average SO per GS from 2019 season (source: https://tinyurl.com/y5aazd8g)
    average_so_per_gs = 0.01
    return round(average_so_per_gs * int(kwargs["stats"][Stat.AB.value])) * int(
        kwargs["points"]
    )


def _blown_saves(**kwargs):
    assert Stat.SV.value in kwargs["stats"]
    # Based on league average BS per SV from 2019 season (source: https://tinyurl.com/y5aazd8g)
    average_bs_per_sv = 0.58
    return round(average_bs_per_sv * int(kwargs["stats"][Stat.SV.value])) * int(
        kwargs["points"]
    )


def _perfect_games(**kwargs):
    # Ignore perfect games
    return 0


_POINT_FUNCS = {
    Stat.TB.value: _total_bases,
    Stat.Sng.value: _singles,
    Stat.Dbl.value: _default,
    Stat.Trp.value: _default,
    Stat.HR.value: _default,
    Stat.R.value: _default,
    Stat.RBI.value: _default,
    Stat.BB.value: _default,
    Stat.SO.value: _default,
    Stat.SB.value: _default,
    Stat.CS.value: _default,
    Stat.GDP.value: _double_plays,
    Stat.HBP.value: _hit_by_pitch,
    Stat.CYC.value: _cycles,
    Stat.IP.value: _innings_pitched,
    Stat.ER.value: _default,
    Stat.H.value: _default,
    Stat.HB.value: _hit_batters,
    Stat.W.value: _default,
    Stat.L.value: _default,
    Stat.QS.value: _quality_starts,
    Stat.CG.value: _complete_games,
    Stat.SHO.value: _shut_outs,
    Stat.SV.value: _default,
    Stat.BS.value: _blown_saves,
    Stat.PG.value: _perfect_games,
}
