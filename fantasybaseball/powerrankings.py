import argparse
from pathlib import Path

import pandas as pd

NUM_BATTERS_PER_TEAM = 15
NUM_PITCHERS_PER_TEAM = 15


def parse_args():
    parser = argparse.ArgumentParser(description="Generate fantasy baseball power rankings from projections.")
    parser.add_argument("-b", "--bat-projections", required=True, help="Path to batters projection CSV")
    parser.add_argument("-p", "--pit-projections", required=True, help="Path to pitchers projection CSV")
    parser.add_argument("--projection-source", default="zobs", help="Projection type to use (default: zobs)")
    parser.add_argument("--num-batters", type=int, default=15, help="Number of top batters per team (default: 15)")
    parser.add_argument("--num-pitchers", type=int, default=15, help="Number of top pitchers per team (default: 15)")
    parser.add_argument(
        "--show",
        choices=["combined", "batter", "pitcher", "all"],
        default="combined",
        help="Type of rankings to show (default: combined)",
    )
    return parser.parse_args()


def get_top_n_by_team(df, n=None):
    """Get top N players per team, or all players if N is None."""
    filtered_df = df[df["Status"] != "FA"].sort_values("Points", ascending=False)
    if n is None:
        return filtered_df
    return filtered_df.groupby("Status").head(n)


def get_rankings_by_type(players_df: pd.DataFrame) -> pd.DataFrame:
    """Generate rankings for a specific set of players."""
    agg_dict = {
        "Points": ["sum", "mean"],
        "Salary": ["sum", "mean"],
        "AuctionValue": ["sum", "mean"],
        "ContractValue": ["sum", "mean"],
        "PlayerId": "count",
    }

    rankings = players_df.groupby("Status").agg(agg_dict).round(2)
    rankings.columns = [
        f"{col[0]}_{col[1]}".replace("_sum", " Total").replace("_mean", " Avg") for col in rankings.columns
    ]

    rankings = (
        rankings.rename(columns={"PlayerId_count": "Player Count"})
        .sort_values("Points Total", ascending=False)
        .reset_index()
        .rename(columns={"Status": "Team"})
    )

    rankings.index = rankings.index + 1
    return rankings


def generate_power_rankings(
    bat_proj_path: Path,
    pit_proj_path: Path,
    projection_source: str,
    num_batters=NUM_BATTERS_PER_TEAM,
    num_pitchers=NUM_PITCHERS_PER_TEAM,
) -> dict[str, pd.DataFrame]:
    """Generate power rankings for teams based on projections."""
    bat_proj = pd.read_csv(bat_proj_path)
    pit_proj = pd.read_csv(pit_proj_path)

    # Filter for specified projection type
    bat_proj = bat_proj[bat_proj["ProjectionSource"] == projection_source]
    pit_proj = pit_proj[pit_proj["ProjectionSource"] == projection_source]

    # Get top players per team for each category
    top_batters = get_top_n_by_team(bat_proj, num_batters)
    top_pitchers = get_top_n_by_team(pit_proj, num_pitchers)

    # Generate rankings for each type
    rankings = {
        "combined": get_rankings_by_type(pd.concat([top_batters, top_pitchers])),
        "batter": get_rankings_by_type(top_batters),
        "pitcher": get_rankings_by_type(top_pitchers),
    }

    return rankings


def main():
    args = parse_args()

    bat_path = Path(args.bat_projections)
    pit_path = Path(args.pit_projections)

    print(f"\nProjection Source: {args.projection_source}")
    print(f"Batters Projections: {bat_path}")
    print(f"Pitchers Projections: {pit_path}")
    print(f"Top Batters per Team: {args.num_batters}")
    print(f"Top Pitchers per Team: {args.num_pitchers}")

    rankings = generate_power_rankings(
        bat_path,
        pit_path,
        args.projection_source,
        args.num_batters,
        args.num_pitchers,
    )

    pd.set_option(
        "display.float_format",
        lambda x: "${:.2f}".format(x) if "Value" in str(x) or "Salary" in str(x) else "{:.2f}".format(x),
    )

    if args.show == "all":
        for ranking_type, df in rankings.items():
            print(f"\n{ranking_type.title()} rankings:")
            print(df)
    else:
        print(f"\n{args.show.title()} rankings:")
        print(rankings[args.show])
