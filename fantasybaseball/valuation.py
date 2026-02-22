import numpy as np


def add_auction_values(
    bat_projections,
    pit_projections,
    league_roster,
    league_salary,
    rostered_players=None,
    rostered_players_majors_perc=0.7,
):
    if rostered_players is None:
        rostered_players_total_salary = 0.0
        rostered_mlbam_ids = list()
        rostered_fangraphs_ids = list()
    else:
        rostered_players_total_salary = rostered_players["Salary"].sum()
        rostered_mlbam_ids = rostered_players["MlbamId"].dropna().tolist()
        rostered_fangraphs_ids = rostered_players["FangraphsId"].dropna().tolist()
    team_count = league_roster["teams"]
    roster_spots = sum(league_roster["positions"].values())
    salary_cap = league_salary["cap"]
    minimum_salary = league_salary["minimum"]
    rostered_count = max(len(rostered_mlbam_ids), len(rostered_fangraphs_ids))
    total_budget = team_count * salary_cap
    total_roster_spots = team_count * roster_spots
    total_auction_value = (total_budget - rostered_players_total_salary) - (
        total_roster_spots * minimum_salary - rostered_count * rostered_players_majors_perc
    )

    total_par = dict()
    bat_projection_sources = bat_projections["ProjectionSource"].unique()
    pit_projection_sources = pit_projections["ProjectionSource"].unique()
    projection_sources = set(bat_projection_sources).union(set(pit_projection_sources))
    for projection_source in projection_sources:
        bat_par = bat_projections.loc[
            (bat_projections["ProjectionSource"] == projection_source)
            & (bat_projections["PAR"] > 0.0)
            & (~bat_projections["MlbamId"].isin(rostered_mlbam_ids))
            & (~bat_projections["FangraphsId"].isin(rostered_fangraphs_ids))
        ]["PAR"].sum()

        pit_par = pit_projections.loc[
            (pit_projections["ProjectionSource"] == projection_source)
            & (pit_projections["PAR"] > 0.0)
            & (~pit_projections["MlbamId"].isin(rostered_mlbam_ids))
            & (~pit_projections["FangraphsId"].isin(rostered_fangraphs_ids))
        ]["PAR"].sum()
        total_par[projection_source] = bat_par + pit_par

    par_value = {p: total_auction_value / t for p, t in total_par.items()}

    # Vectorized auction value calculation
    bat_projections["AuctionValue"] = (
        bat_projections["ProjectionSource"].map(par_value) * bat_projections["PAR"] + minimum_salary
    )
    bat_projections["ContractValue"] = bat_projections["AuctionValue"] - bat_projections["Salary"]

    pit_projections["AuctionValue"] = (
        pit_projections["ProjectionSource"].map(par_value) * pit_projections["PAR"] + minimum_salary
    )
    pit_projections["ContractValue"] = pit_projections["AuctionValue"] - pit_projections["Salary"]

    return bat_projections, pit_projections
