import pandas as pd


def replace_pitcher_position(projections, league_roster):
    projections = projections.copy()
    if "SP" in league_roster["positions"] or "RP" in league_roster["positions"]:
        projections["Position"] = ["SP" if gs > 0.0 else "RP" for gs in projections["GS"]]
    else:
        projections["Position"] = "P"

    return projections


def replace_positions(projections, league_export):
    """Replace projection positions with league export positions using ID matching."""
    # Build lookup dicts from league export
    mlbam_positions = {}
    fangraphs_positions = {}

    for _, row in league_export.iterrows():
        position = row.get("Position")
        if pd.isna(position):
            continue
        position = str(position).replace(",", "/")

        if pd.notna(row.get("MlbamId")):
            mlbam_positions[row["MlbamId"]] = position
        if pd.notna(row.get("FangraphsId")):
            fangraphs_positions[row["FangraphsId"]] = position

    # Map positions: try MlbamId first, then FangraphsId fallback
    mlbam_match = projections["MlbamId"].map(mlbam_positions)
    fangraphs_match = projections["FangraphsId"].map(fangraphs_positions)
    projections["Position"] = mlbam_match.fillna(fangraphs_match).fillna(projections["Position"])

    return projections
