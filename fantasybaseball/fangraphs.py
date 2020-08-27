from bs4 import BeautifulSoup, SoupStrainer
import pandas as pd
import requests

from .glossary import League, Position, ProjectionType, StatType, Team

_PROJECTIONS_URL = "https://www.fangraphs.com/projections.aspx?pos={}&stats={}&type={}&team={}&lg={}&sort={},d"
_PROJECTIONS_TABLE_ID = "ProjectionBoard1_dg1_ctl00"
_NO_RECORD_MESSAGE = "No records to display."
_SORT_COLUMN = {
    # ABs column indices
    StatType.BATTING.value: {
        ProjectionType.ZIPS.value: 5,
        ProjectionType.STEAMER.value: 5,
        ProjectionType.DEPTH_CHARTS.value: 5,
        ProjectionType.THE_BAT.value: 5,
    },
    # IPs column indices
    StatType.PITCHING.value: {
        ProjectionType.ZIPS.value: 8,
        ProjectionType.STEAMER.value: 9,
        ProjectionType.DEPTH_CHARTS.value: 10,
        ProjectionType.THE_BAT.value: 9,
    },
}


def get_projections(
    projection_type, stat_type, league=League.ALL.value, team=Team.ALL.value, position=Position.ALL.value, ros=False
):
    sort_column = _SORT_COLUMN[stat_type][projection_type]
    # TODO: Log warning if team and league is specified
    if ros:
        projection_type = (
            "{}r".format(projection_type)
            if projection_type == ProjectionType.STEAMER.value
            else "r{}".format(projection_type)
        )
    # TODO: Assert valid stat_type & projection for _SORT_COLUMN map
    url = _PROJECTIONS_URL.format(position, stat_type, projection_type, team, league, sort_column)
    response = requests.get(url)
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
        row.extend([r.get_text() for r in row_soup.find_all("td")])
        data.append(row)
    if data[0][0] == _NO_RECORD_MESSAGE:
        data = []
    projections = pd.DataFrame(data=data, columns=columns)
    # Drop "recent news" column from fangraph projections tables
    projections.drop(columns=[projections.columns[3]], inplace=True)
    return projections
