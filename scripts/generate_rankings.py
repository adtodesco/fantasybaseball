import os
from datetime import datetime

import numpy as np
import pandas as pd
import yaml

from fantasybaseball import scoring
from fantasybaseball import utils
from fantasybaseball.model import ProjectionType, Stat, StatType

# LEAGUE_NAME = "beastmode"
LEAGUE_NAME = "dynasty"
PROJECTIONS_DIR = "../projections"
RANKINGS_DIR = "../rankings"
LEAGUES_DIR = "../leagues"
DT_FORMAT = "%Y-%m-%d"

CUSTOM_BATTING_STATS = {
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
        ProjectionType.THE_BAT_X,
    ]
    stat_types = [StatType.BATTING, StatType.PITCHING]
    ros = True
    projections_dir = PROJECTIONS_DIR
    rankings_dir = RANKINGS_DIR
    leagues_dir = LEAGUES_DIR
    league_name = LEAGUE_NAME
    date_string = datetime.today().strftime(DT_FORMAT)

    with open(os.path.join(leagues_dir, "{}.yaml".format(league_name))) as f:
        league = yaml.safe_load(f)

    projections = {StatType.BATTING.value: dict(), StatType.PITCHING.value: dict()}
    projection_files = utils.read_projections(
        projections_dir=PROJECTIONS_DIR,
        projection_types=projection_types,
        stat_types=stat_types,
        ros=ros,
    )
    for metadata, projection in projection_files:
        projection = projection.set_index("Id")
        projection.index = projection.index.map(np.str)
        projections[metadata["stat_type"]][metadata["projection_type"]] = projection

    for stat_type in StatType:
        # Merge projections for batters or pitchers
        df = pd.concat(
            projections[stat_type.value].values(),
            keys=projections[stat_type.value].keys(),
            names=["Projection"],
        )

        # Calculate and add points column
        stat_cols = list(df.select_dtypes(include=[np.number]))
        score_vector = scoring.calculate_score_vector(
            stat_type=stat_type,
            stat_cols=stat_cols,
            league=league,
            custom_stats=CUSTOM_BATTING_STATS if stat_type == StatType.BATTING else CUSTOM_PITCHING_STATS,
        )
        print("score vector:")
        print(score_vector)
        points = np.round(df.loc[:, stat_cols].fillna(0.0).dot(score_vector), 2)
        points.name = "Points"
        df = df.merge(points, left_index=True, right_index=True)

        ordered_columns = ["Rank", "Position", "Name", "Team", "Points"]

        # Add columns for Pts/G or Pts/IP
        if stat_type == StatType.BATTING:
            df["Pts/G"] = np.round(df["Points"] / df["G"], 2)
            ordered_columns.append("Pts/G")
        elif stat_type == StatType.PITCHING:
            df["Pts/IP"] = np.round(df["Points"] / df["IP"], 2)
            ordered_columns.append("Pts/IP")

        # Round mean projections integers to 0 decimals and floats to 3 decimals
        decimals = {k: 0 if v == "int64" else 3 for k, v in df.dtypes.to_dict().items()}
        decimals.update({"Points": 0, "HBP": 0, "SV": 0, "HLD": 0, "IP": 0})

        # Calculate and add mean projetions
        mean_projections = df.groupby(by=["Id", "Name", "Position", "Team"]).mean(numeric_only=True).round(decimals)
        mean_projections["Projection"] = "mean"
        mean_projections = mean_projections.reset_index().set_index(["Projection", "Id"])
        df = df.append(mean_projections)

        # Sort rows by projections then points (descending)
        df.sort_values(["Projection", "Points"], ascending=[True, False], inplace=True)

        # Add rank from 1 to N per projection type
        df["Rank"] = df.groupby("Projection")["Points"].rank(ascending=False).astype(int)

        # Order columns for easy reading
        for i, ordered_column in enumerate(ordered_columns):
            df.insert(i, ordered_column, df.pop(ordered_column))

        # Write rankings out to csv file
        rankings_file = os.path.join(
            RANKINGS_DIR,
            f"{stat_type.name}-RANKINGS-{league_name}-{date_string}.csv",
        )
        df.to_csv(rankings_file)
        print(f"Wrote rankings to {rankings_file}")
