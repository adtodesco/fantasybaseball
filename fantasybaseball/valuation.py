def calculate_auction_values(
    bat_projections,
    pit_projections,
    league_roster,
    league_salary,
    power_factor=1.0,
    total_auction_value=None,
    bat_pool_mask=None,
    pit_pool_mask=None,
):
    team_count = league_roster["teams"]
    roster_spots = sum(league_roster["positions"].values())
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    minors_pct = league_salary.get("minors_pct", 0.0) if hasattr(league_salary, "get") else league_salary["minors_pct"]
    effective_cap = salary_cap * (1 - minors_pct)
    total_budget = team_count * effective_cap
    total_roster_spots = team_count * roster_spots

    if total_auction_value is None:
        total_auction_value = total_budget - (total_roster_spots * minimum_salary)

    if bat_pool_mask is None:
        bat_pool_mask = bat_projections.index.to_series().map(lambda _: True)
    if pit_pool_mask is None:
        pit_pool_mask = pit_projections.index.to_series().map(lambda _: True)

    total_par = dict()
    bat_projection_sources = bat_projections["ProjectionSource"].unique()
    pit_projection_sources = pit_projections["ProjectionSource"].unique()
    projection_sources = set(bat_projection_sources).union(set(pit_projection_sources))
    for projection_source in projection_sources:
        bat_par = (
            bat_projections.loc[
                (bat_projections["ProjectionSource"] == projection_source)
                & (bat_projections["PAR"] > 0.0)
                & bat_pool_mask
            ]["PAR"]
            .pow(power_factor)
            .sum()
        )

        pit_par = (
            pit_projections.loc[
                (pit_projections["ProjectionSource"] == projection_source)
                & (pit_projections["PAR"] > 0.0)
                & pit_pool_mask
            ]["PAR"]
            .pow(power_factor)
            .sum()
        )
        total_par[projection_source] = bat_par + pit_par

    par_value = {p: total_auction_value / t for p, t in total_par.items()}

    bat_values = (
        bat_projections["ProjectionSource"].map(par_value) * bat_projections["PAR"].clip(lower=0).pow(power_factor)
        + minimum_salary
    )
    pit_values = (
        pit_projections["ProjectionSource"].map(par_value) * pit_projections["PAR"].clip(lower=0).pow(power_factor)
        + minimum_salary
    )

    return bat_values, pit_values


def calculate_available_budget(
    league_roster,
    league_salary,
    league_export,
):
    team_count = league_roster["teams"]
    minors_spots = league_roster.get("minors", 0) if hasattr(league_roster, "get") else league_roster["minors"]
    roster_spots = sum(league_roster["positions"].values()) + minors_spots
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    total_budget = team_count * salary_cap
    total_roster_spots = team_count * roster_spots

    signed = league_export[league_export["Status"].notna() & (league_export["Status"] != "FA")]
    signed_salary = signed["Salary"].sum()
    signed_count = len(signed)
    remaining_spots = total_roster_spots - signed_count

    return total_budget - signed_salary - (remaining_spots * minimum_salary)
