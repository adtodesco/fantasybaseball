from fantasybaseball import fangraphs, utils
from fantasybaseball.glossary import *
import pandas as pd
import progressbar
import ratelimiter

MAX_REQUESTS_PER_SECOND = 1.0
PROJECTIONS_DIR = "../projections"


if __name__ == "__main__":
    projections = {StatType.BATTING.value: dict(), StatType.PITCHING.value: dict()}
    jobs = list()
    for projection_type in ProjectionType:
        projections[StatType.BATTING.value][projection_type.value] = list()
        projections[StatType.PITCHING.value][projection_type.value] = list()
        for position in Position:
            if position == Position.ALL:
                continue
            for league in League:
                if league == League.ALL:
                    continue
                jobs.append(
                    {
                        "projection_type": projection_type.value,
                        "stat_type": StatType.BATTING.value,
                        "league": league.value,
                        "position": position.value,
                        "ros": True,
                    }
                )
        for team in Team:
            if team == Team.ALL:
                continue
            jobs.append(
                {
                    "projection_type": projection_type.value,
                    "stat_type": StatType.PITCHING.value,
                    "team": team.value,
                    "ros": True,
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
                projections=pd.concat(projections[stat_type.value][projection_type.value]).drop_duplicates(),
                projections_dir=PROJECTIONS_DIR,
                projection_type=projection_type,
                stat_type=stat_type,
                ros=True,
            )
