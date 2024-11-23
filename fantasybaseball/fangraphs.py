import pandas as pd
import requests

from .model import ProjectionType

PROJECTIONS_URL = "https://www.fangraphs.com/api/projections"


def get_projections(stat_type, projection_type, ros=False):
    projection_type_value = projection_type.value
    if ros:
        if projection_type == ProjectionType.STEAMER:
            projection_type_value = f"{projection_type.value}r"
        else:
            projection_type_value = f"r{projection_type.value}"

    payload = {
        "stats": stat_type.value,
        "type": projection_type_value,
    }
    response = requests.get(PROJECTIONS_URL, params=payload)
    response.raise_for_status()

    projections = pd.DataFrame(response.json())
    if not projections.empty:
        _sanitize_projections(projections, projection_type_value)

    return projections.infer_objects()


def _sanitize_projections(projections, projection_type):
    projections["ProjectionType"] = projection_type
    projections["Name"] = projections["PlayerName"]
    projections.drop(["PlayerName", "TeamId", "."], axis=1, inplace=True, errors="ignore")
    projections.rename(columns={"minpos": "Position", "teamid": "TeamId", "playerids": "PlayerId"}, inplace=True)
