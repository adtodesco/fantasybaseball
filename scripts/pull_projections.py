import pandas as pd
import progressbar
import ratelimiter
import requests
import time

from fantasybaseball import fangraphs, utils
from fantasybaseball.model import ProjectionType, StatType, Team


MAX_REQUESTS_PER_SECOND = 0.5
PROJECTIONS_DIR = "../projections"
REST_OF_SEASON = True


def create_jobs(stat_type, projection_type):
    jobs = list()
    for team in Team:
        if team == Team.ALL:
            continue
        jobs.append(
            {
                "projection_type": projection_type,
                "stat_type": stat_type,
                "team": team,
                "ros": REST_OF_SEASON,
            }
        )

    return jobs


def main():
    projections = {StatType.BATTING: dict(), StatType.PITCHING: dict()}
    jobs = list()
    for projection_type in ProjectionType:
        projections[StatType.BATTING][projection_type] = list()
        jobs.extend(create_jobs(StatType.BATTING, projection_type))
        if projection_type == ProjectionType.THE_BAT_X:
            continue
        projections[StatType.PITCHING][projection_type] = list()
        jobs.extend(create_jobs(StatType.PITCHING, projection_type))

    rate_limiter = ratelimiter.RateLimiter(max_calls=MAX_REQUESTS_PER_SECOND, period=1)
    bar = progressbar.ProgressBar(max_value=len(jobs)).start()
    for job in jobs:
        with rate_limiter:
            retries = 3
            while True:
                try:
                    result = fangraphs.get_projections(**job)
                    break
                except requests.exceptions.ConnectionError:
                    if retries:
                        time.sleep(5)
                    else:
                        raise
            projections[job["stat_type"]][job["projection_type"]].append(result)
            bar.update(bar.value + 1)
    bar.finish()

    for stat_type in StatType:
        for projection_type in ProjectionType:
            if projection_type in projections[stat_type]:
                utils.write_projections(
                    projections=pd.concat(projections[stat_type][projection_type]).drop_duplicates(),
                    projections_dir=PROJECTIONS_DIR,
                    projection_type=projection_type,
                    stat_type=stat_type,
                    ros=REST_OF_SEASON,
                )


if __name__ == "__main__":
    main()
