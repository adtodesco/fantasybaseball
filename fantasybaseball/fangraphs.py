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

    # Preserve both Fangraphs and MLBAM IDs
    projections.rename(columns={
        "minpos": "Position",
        "teamid": "TeamId",
        "playerids": "FangraphsId",  # Explicit: this is Fangraphs ID
        "xMLBAMID": "MlbamId"         # Universal identifier
    }, inplace=True)

    # Convert IDs to nullable integers (handles nulls for recent call-ups)
    projections["MlbamId"] = pd.to_numeric(projections["MlbamId"], errors='coerce').astype('Int64')
    projections["FangraphsId"] = pd.to_numeric(projections["FangraphsId"], errors='coerce').astype('Int64')

    projections.drop(["PlayerName", "TeamId", "."], axis=1, inplace=True, errors="ignore")
