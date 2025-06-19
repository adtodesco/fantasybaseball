import pandas as pd
import requests

PROJECTIONS_URL = "https://www.fangraphs.com/api/projections"


def get_projections(stat_category, projection_source):
    payload = {
        "stats": stat_category.value,
        "type": projection_source.value,
    }
    response = requests.get(PROJECTIONS_URL, params=payload)
    response.raise_for_status()

    projections = pd.DataFrame(response.json())
    if not projections.empty:
        _sanitize_projections(projections, projection_source)

    return projections.infer_objects()


def _sanitize_projections(projections, projection_source):
    projections["ProjectionSource"] = projection_source.value
    projections["Name"] = projections["PlayerName"]
    projections.drop(["PlayerName", "TeamId", "."], axis=1, inplace=True, errors="ignore")
    projections.rename(columns={"minpos": "Position", "teamid": "TeamId", "playerids": "PlayerId"}, inplace=True)
