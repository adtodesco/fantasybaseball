from fantasybaseball import scoring
from fantasybaseball import utils
from fantasybaseball.glossary import ProjectionType, Stat, StatType
import numpy as np
import os
import pandas as pd
import yaml


PROJECTIONS_DIR = "../projections"
RANKINGS_DIR = "../rankings"
LEAGUES_DIR = "../leagues"

CUSTOM_BATTING_STATS = {
    Stat.TB.value: {Stat.H.value: 1, Stat.Dbl.value: 1, Stat.Trp.value: 2, Stat.HR.value: 3},
    Stat.Sng.value: {Stat.H.value: 1, Stat.Dbl.value: -1, Stat.Trp.value: -1, Stat.HR.value: -1},
    # Based on league average GDP per AB from 2019 season  (source: https://tinyurl.com/y66bqflr)
    Stat.GDP.value: {Stat.AB.value: 0.02},
}
CUSTOM_PITCHING_STATS = {
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

if __name__ == "__main__":
    # TODO: Gather variables from command line
    projection_types = [
        ProjectionType.ZIPS,
        ProjectionType.STEAMER,
        ProjectionType.DEPTH_CHARTS,
        ProjectionType.THE_BAT,
    ]
    stat_types = [StatType.BATTING, StatType.PITCHING]
    ros = False
    projections_dir = PROJECTIONS_DIR
    rankings_dir = RANKINGS_DIR
    leagues_dir = LEAGUES_DIR
    league_name = "beastmode"

    with open(os.path.join(leagues_dir, "{}.yaml".format(league_name))) as f:
        league = yaml.safe_load(f)

    projections = {StatType.BATTING.value: dict(), StatType.PITCHING.value: dict()}
    for metadata, projection in utils.read_projections(
        projections_dir=PROJECTIONS_DIR, projection_types=projection_types, stat_types=stat_types, ros=ros
    ):
        projection = projection.set_index("Id")
        projection.index = projection.index.map(np.str)
        projections[metadata["stat_type"]][metadata["projection_type"]] = projection

    for stat_type in StatType:
        projections[stat_type.value] = pd.concat(
            projections[stat_type.value].values(), keys=projections[stat_type.value].keys(), names=["Projection"]
        )
        stat_cols = list(projections[stat_type.value].select_dtypes(include=[np.number]))
        score_vector = scoring.calculate_score_vector(
            stat_type=stat_type,
            stat_cols=stat_cols,
            league=league,
            custom_stats=CUSTOM_BATTING_STATS if stat_type == StatType.BATTING else CUSTOM_PITCHING_STATS,
        )
        points = projections[stat_type.value].loc[:, stat_cols].fillna(0.0).dot(score_vector)
        points.name = "Points"
        projections[stat_type.value] = projections[stat_type.value].merge(points, left_index=True, right_index=True)
        decimals = {k: 0 if v == "int64" else 3 for k, v in projections[stat_type.value].dtypes.to_dict().items()}
        decimals.update({"Points": 0, "HBP": 0, "SV": 0, "HLD": 0, "IP": 0})
        mean_projections = (
            projections[stat_type.value]
            .groupby(by=["Id", "Name", "Position", "Team"])
            .mean(numeric_only=True)
            .round(decimals)
        )
        mean_projections["Projection"] = "mean"
        mean_projections = mean_projections.reset_index().set_index(["Projection", "Id"])
        projections[stat_type.value] = projections[stat_type.value].append(mean_projections)
        projections[stat_type.value].sort_values(["Projection", "Points"], ascending=[True, False], inplace=True)
        projections[stat_type.value].to_csv(os.path.join(RANKINGS_DIR, "{}-RANKINGS.csv".format(stat_type.name)))
