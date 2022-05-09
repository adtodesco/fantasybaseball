from bs4 import BeautifulSoup, SoupStrainer
import pandas as pd
import requests

from .exceptions import InvalidRequest
from .model import League, Position, ProjectionType, StatType, Team

_PROJECTIONS_URL = "https://www.fangraphs.com/projections.aspx"
_PROJECTIONS_TABLE_ID = "ProjectionBoard1_dg1_ctl00"
_NO_RECORD_MESSAGE = "No records to display."
_SORT_COLUMN = {
    # ABs column indices
    StatType.BATTING: {
        ProjectionType.ZIPS: 5,
        ProjectionType.STEAMER: 5,
        ProjectionType.DEPTH_CHARTS: 5,
        ProjectionType.THE_BAT: 5,
        ProjectionType.THE_BAT_X: 5,
    },
    # IPs column indices
    StatType.PITCHING: {
        ProjectionType.ZIPS: 8,
        ProjectionType.STEAMER: 9,
        ProjectionType.DEPTH_CHARTS: 10,
        ProjectionType.THE_BAT: 9,
    },
}


def get_projections(
    projection_type,
    stat_type,
    league=League.ALL,
    team=Team.ALL,
    position=Position.ALL,
    ros=False,
):
    """Gets the requested projections from Fangraphs

    Args:
        projection_type: The `ProjectionType`.
        stat_type: The `StatType` to retrieve.
        league: The `League` to retrieve.
        team: The `Team` to retrieve (e.g. All, Red Sox, Dodgers, etc.). Teams are listed
            in glossary.py.
        position: The Position to retrieve (e.g. All, P, C, etc.). Positions are listed
            in glossary.py.
        ros: Retrieve projections for the rest of the season.  By default pre-season
            projections are retrieved.

    Returns: A DataFrame containing the requested projections of the "top 30" players
        where batters are ordered by at-bats and pitchers are ordered by innings
        pitched.

    Raises:
        InvalidRequest:
            1. If both `team` and `league` are set (at least one must be ALL).
            2. If `projection_type` is not a valid ProjectionType. ProjectionTypes are
                listed in glossary.py.
            3. If `stat_type` is not a valid StatType. StatTypes are listed in
                glossary.py.
        HTTPError: If one occurred.
    """
    if league != League.ALL and team != Team.ALL:
        raise InvalidRequest("'team' and 'league' cannot both be set in the same projections request")
    if not isinstance(projection_type, ProjectionType):
        raise InvalidRequest(f"{projection_type} is not a valid ProjectionType.")
    if not isinstance(stat_type, StatType):
        raise InvalidRequest(f"{stat_type} is not a valid StatType.")

    sort_column = _SORT_COLUMN[stat_type][projection_type]
    projection_type_value = projection_type.value
    if ros:
        if projection_type == ProjectionType.STEAMER:
            projection_type_value = f"{projection_type.value}r"
        else:
            projection_type_value = f"r{projection_type.value}"

    payload = {
        "pos": position.value,
        "stats": stat_type.value,
        "type": projection_type_value,
        "team": team.value,
        "lg": league.value,
        "sort": f"{sort_column},d",
    }
    response = requests.get(_PROJECTIONS_URL, params=payload)
    response.raise_for_status()
    return _parse_projections_table(response.text)


def _parse_projections_table(html):
    strainer = SoupStrainer(id=_PROJECTIONS_TABLE_ID)
    table_soup = BeautifulSoup(html, "lxml", parse_only=strainer)
    # TODO: Catch and raise table tag parsing errors
    columns = ["Id", "Position"]
    columns.extend([h.get_text() for h in table_soup.find_all("th")])
    data = []
    for row_soup in table_soup.find("tbody").find_all("tr"):
        href = row_soup.find("td").find("a").get("href")
        attributes = {attr.split("=")[0]: attr.split("=")[1] for attr in href.split("?")[1].split("&")}
        row = [attributes["playerid"], attributes["position"]]
        row.extend([r.get_text().strip() for r in row_soup.find_all("td")])
        data.append(row)
    if data[0][0] == _NO_RECORD_MESSAGE:
        data = []
    projections = pd.DataFrame(data=data, columns=columns)
    return projections
