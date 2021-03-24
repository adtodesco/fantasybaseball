from fantasybaseball import fangraphs, utils
from fantasybaseball.glossary import League, Position, ProjectionType, StatType, Team
import pandas as pd
import progressbar
import ratelimiter

MAX_REQUESTS_PER_SECOND = 1.0
PROJECTIONS_DIR = "../projections"
REST_OF_SEASON = False

if __name__ == "__main__":
    projections = {StatType.BATTING: dict(), StatType.PITCHING: dict()}
    jobs = list()
    for projection_type in ProjectionType:
        projections[StatType.BATTING][projection_type] = list()
        projections[StatType.PITCHING][projection_type] = list()
        for team in Team:
            if team == Team.ALL:
                continue
            jobs.append(
                {
                    "projection_type": projection_type,
                    "stat_type": StatType.BATTING,
                    "team": team,
                    "ros": REST_OF_SEASON,
                }
            )
            jobs.append(
                {
                    "projection_type": projection_type,
                    "stat_type": StatType.PITCHING,
                    "team": team,
                    "ros": REST_OF_SEASON,
                }
            )

    rate_limiter = ratelimiter.RateLimiter(max_calls=MAX_REQUESTS_PER_SECOND, period=1)
    bar = progressbar.ProgressBar(max_value=len(jobs)).start()
    for job in jobs:
        with rate_limiter:
            result = fangraphs.get_projections(**job)
            projections[job["stat_type"]][job["projection_type"]].append(result)
            bar.update(bar.value + 1)
    bar.finish()

    for stat_type in StatType:
        for projection_type in ProjectionType:
            utils.write_projections(
                projections=pd.concat(
                    projections[stat_type][projection_type]
                ).drop_duplicates(),
                projections_dir=PROJECTIONS_DIR,
                projection_type=projection_type,
                stat_type=stat_type,
                ros=REST_OF_SEASON,
            )
