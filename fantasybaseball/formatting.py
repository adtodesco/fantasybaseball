import pandas as pd


def order_and_rank_rows(projections, order_by, asc=True):
    projections = projections.sort_values(["ProjectionSource", order_by], ascending=[True, asc])
    rank = projections.groupby("ProjectionSource")[order_by].rank(ascending=asc).astype(int)
    if "Rank" in projections:
        projections.pop("Rank")
    projections.insert(1, "Rank", rank)
    return projections


def order_columns(projections, columns, front=True):
    projections = projections.copy()
    insert_at = projections.shape[1] - 1
    if front:
        columns = reversed(columns)
        insert_at = 0
    for col_name in columns:
        try:
            col = projections.pop(col_name)
            projections.insert(insert_at, col.name, col)
        except KeyError:
            pass

    return projections


def format_stats(projections, columns):
    for column, col_type, *decimals in columns:
        if column not in projections:
            continue

        if col_type == "float" and decimals:
            projections[column] = projections[column].round(decimals[0])
        elif col_type == "int":
            projections[column] = pd.to_numeric(projections[column], errors="coerce").fillna(0).astype(int)
        elif col_type == "string":
            projections[column] = projections[column].astype(str)
        elif col_type == "currency" and decimals:
            projections[column] = pd.to_numeric(projections[column], errors="coerce").round(decimals[0])
    return projections


def format_currency_for_csv(projections, columns):
    """Format currency columns as strings for CSV output only."""
    projections = projections.copy()
    for column, col_type, *decimals in columns:
        if column not in projections:
            continue
        if col_type == "currency":
            projections[column] = projections[column].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
    return projections
