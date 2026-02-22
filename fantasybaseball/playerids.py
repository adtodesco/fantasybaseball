from importlib import resources

import pandas as pd


def default_player_id_map_path():
    """Locate bundled player_id_map.csv using importlib.resources."""
    ref = resources.files("fantasybaseball").joinpath("data/player_id_map.csv")
    return str(ref)


def load_player_id_map(path=None):
    """Load Smart Fantasy Baseball player ID mapping."""
    player_map = pd.read_csv(path or default_player_id_map_path())

    # Standardize column names from SFBB format
    player_map.rename(
        columns={
            "MLBID": "MlbamId",
            "IDFANGRAPHS": "FangraphsId",
            "FANTRAXID": "FantraxId",
            "ESPNID": "EspnId",
            "YAHOOID": "YahooId",
        },
        inplace=True,
    )

    # Convert to appropriate types
    player_map["MlbamId"] = pd.to_numeric(player_map["MlbamId"], errors="coerce").astype("Int64")
    player_map["FangraphsId"] = pd.to_numeric(player_map["FangraphsId"], errors="coerce").astype("Int64")

    return player_map


def merge_with_league_export(projections, league_export):
    """Merge projections with league export using MLBAM ID with Fangraphs fallback."""

    # Ensure consistent types for FangraphsId
    league_export = league_export.copy()
    league_export["FangraphsId"] = pd.to_numeric(league_export["FangraphsId"], errors="coerce").astype("Int64")

    # Select league data columns, filtering out rows with null IDs to avoid cartesian products
    league_data = league_export[["Status", "Age", "Salary", "Contract", "MlbamId", "FangraphsId", "FantraxId"]].copy()

    # Primary join on MLBAM ID (only for non-null MlbamIds)
    league_data_mlbam = league_data[league_data["MlbamId"].notna()]
    merged = projections.merge(league_data_mlbam, on="MlbamId", how="left", suffixes=("_proj", "_league"))

    # For rows without MLBAM match, try Fangraphs ID
    unmatched_mask = merged["Status"].isna()
    if unmatched_mask.any():
        # Get unmatched projections
        unmatched_projections = projections[projections.index.isin(merged[unmatched_mask].index)]

        # Try to match on Fangraphs ID (only for non-null FangraphsIds)
        league_data_fangraphs = league_data[league_data["FangraphsId"].notna()]
        fangraphs_matches = unmatched_projections.merge(
            league_data_fangraphs[["Status", "Age", "Salary", "Contract", "FangraphsId", "FantraxId"]],
            on="FangraphsId",
            how="inner",
            suffixes=("", "_fg"),
        )

        # Update merged dataframe with Fangraphs matches
        if not fangraphs_matches.empty:
            for idx in fangraphs_matches.index:
                if idx in merged.index:
                    merged.loc[idx, "Status"] = fangraphs_matches.loc[idx, "Status"]
                    merged.loc[idx, "Age"] = fangraphs_matches.loc[idx, "Age"]
                    merged.loc[idx, "Salary"] = fangraphs_matches.loc[idx, "Salary"]
                    merged.loc[idx, "Contract"] = fangraphs_matches.loc[idx, "Contract"]
                    merged.loc[idx, "FantraxId"] = fangraphs_matches.loc[idx, "FantraxId"]
                    # Keep the FangraphsId from league export if they differ
                    if "FangraphsId_league" in merged.columns:
                        merged.loc[idx, "FangraphsId_league"] = fangraphs_matches.loc[idx, "FangraphsId"]

    # Consolidate FangraphsId columns - prefer projection's FangraphsId, then league's
    if "FangraphsId_proj" in merged.columns and "FangraphsId_league" in merged.columns:
        merged["FangraphsId"] = merged["FangraphsId_proj"].fillna(merged["FangraphsId_league"])
        merged.drop(["FangraphsId_proj", "FangraphsId_league"], axis=1, inplace=True)
    elif "FangraphsId_league" in merged.columns:
        merged.rename(columns={"FangraphsId_league": "FangraphsId"}, inplace=True)

    # Clean up any remaining duplicate columns
    merged.drop(
        [col for col in merged.columns if col.endswith("_league") or col.endswith("_proj")],
        axis=1,
        inplace=True,
        errors="ignore",
    )

    return merged
