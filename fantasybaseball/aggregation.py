import pandas as pd


def standardize_name_format(name):
    """Converts 'Last, First' name format to 'First Last'."""
    if isinstance(name, str) and ", " in name:
        parts = name.split(", ")
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name


def add_mean_projection(projections, projection_sources=None, name="mean"):
    if projection_sources is None:
        projection_sources = projections["ProjectionSource"].unique()
    else:
        projection_sources = [p.value for p in projection_sources]

    group_by = ["Name", "MlbamId", "FangraphsId", "Position", "League", "Team", "ShortName"]
    if "Position" not in projections:
        group_by.remove("Position")

    # Fill missing values so free agents can be grouped
    # String columns get "--", integer ID columns get -1
    string_cols = ["Name", "Position", "League", "Team", "ShortName"]
    int_cols = ["MlbamId", "FangraphsId"]

    for col in string_cols:
        if col in group_by and col in projections.columns:
            projections[col] = projections[col].fillna("--")

    for col in int_cols:
        if col in group_by and col in projections.columns:
            projections[col] = projections[col].fillna(-1)

    mean_projections = (
        projections[projections["ProjectionSource"].isin(projection_sources)]
        .groupby(by=group_by)
        .mean(numeric_only=True)
    )
    mean_projections["ProjectionSource"] = name
    mean_projections.reset_index(inplace=True)

    return pd.concat([projections, mean_projections], ignore_index=True)
