def calculate_auction_values(
    bat_projections,
    pit_projections,
    league_roster,
    league_salary,
    power_factor=1.0,
):
    team_count = league_roster["teams"]
    roster_spots = sum(league_roster["positions"].values())
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    total_budget = team_count * salary_cap
    total_roster_spots = team_count * roster_spots
    total_auction_value = total_budget - (total_roster_spots * minimum_salary)

    total_par = dict()
    bat_projection_sources = bat_projections["ProjectionSource"].unique()
    pit_projection_sources = pit_projections["ProjectionSource"].unique()
    projection_sources = set(bat_projection_sources).union(set(pit_projection_sources))
    for projection_source in projection_sources:
        bat_par = bat_projections.loc[
            (bat_projections["ProjectionSource"] == projection_source)
            & (bat_projections["PAR"] > 0.0)
        ]["PAR"].pow(power_factor).sum()

        pit_par = pit_projections.loc[
            (pit_projections["ProjectionSource"] == projection_source)
            & (pit_projections["PAR"] > 0.0)
        ]["PAR"].pow(power_factor).sum()
        total_par[projection_source] = bat_par + pit_par

    par_value = {p: total_auction_value / t for p, t in total_par.items()}

    bat_values = (
        bat_projections["ProjectionSource"].map(par_value)
        * bat_projections["PAR"].clip(lower=0).pow(power_factor)
        + minimum_salary
    )
    pit_values = (
        pit_projections["ProjectionSource"].map(par_value)
        * pit_projections["PAR"].clip(lower=0).pow(power_factor)
        + minimum_salary
    )

    return bat_values, pit_values
