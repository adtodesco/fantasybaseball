import argparse
import pathlib
import time
import warnings

import pandas as pd
import progressbar
import requests
import yaml

from fantasybaseball.config import load_league_config
from fantasybaseball.fangraphs import get_projections
from fantasybaseball.model import ProjectionSource, ProjectionSourceName, StatCategory
from fantasybaseball.playerids import default_player_id_map_path
from fantasybaseball.projections import augment_projections, write_projections_file


def load_config_defaults():
    config_path = pathlib.Path("config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--projection-source", nargs="+", default=[p.value for p in ProjectionSourceName])
    parser.add_argument("-s", "--stat-category", nargs="+", default=[s.value for s in StatCategory])
    parser.add_argument("-x", "--exclude-bench", action="store_true", default=False)
    parser.add_argument("-r", "--rest-of-season", action="store_true")
    parser.add_argument("-l", "--league-file", default=None)
    parser.add_argument("-e", "--league-export", default=None)
    parser.add_argument("-o", "--output-dir", default="projections/")
    parser.add_argument("--player-id-map", default=default_player_id_map_path())
    parser.add_argument("--power-factor", type=float, default=None)

    config = load_config_defaults()
    if config:
        parser.set_defaults(**config)

    return parser.parse_args()


def create_projection_requests(stat_categories, projection_sources):
    jobs = list()
    for projection_source in projection_sources:
        for stat_category in stat_categories:
            jobs.append(
                {
                    "projection_source": projection_source,
                    "stat_category": stat_category,
                }
            )

    return jobs


def run_projection_requests(projection_requests, retries=3):
    bat_projections = list()
    pit_projections = list()
    bar = progressbar.ProgressBar(max_value=len(projection_requests)).start()
    for projection_request in projection_requests:
        while True:
            try:
                projections = get_projections(**projection_request)
                if projections.empty:
                    break
                if projection_request["stat_category"] == StatCategory.BATTING:
                    bat_projections.append(projections)
                else:
                    pit_projections.append(projections)

                break
            except requests.exceptions.ConnectionError:
                retries -= 1
                if retries >= 0:
                    time.sleep(5)
                else:
                    raise
        bar.update(bar.value + 1)
    bar.finish()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        return (
            pd.concat(bat_projections, ignore_index=True),
            pd.concat(pit_projections, ignore_index=True),
        )


def main():
    args = get_args()

    league, league_export = None, None
    if args.league_file:
        with open(pathlib.Path(args.league_file).resolve()) as f:
            league = load_league_config(yaml.safe_load(f))
    if args.league_export:
        league_export = pd.read_csv(args.league_export)

    stat_categories = [StatCategory(st) for st in args.stat_category]
    projection_sources = [ProjectionSource(pt, ros=args.rest_of_season) for pt in args.projection_source]
    include_bench = not args.exclude_bench
    output_dir = pathlib.Path(args.output_dir).resolve()

    projection_requests = create_projection_requests(stat_categories, projection_sources)
    bat_projections, pit_projections = run_projection_requests(projection_requests)
    bat_projections, pit_projections = augment_projections(
        bat_projections,
        pit_projections,
        league,
        league_export,
        include_bench,
        args.rest_of_season,
        player_id_map_path=args.player_id_map,
        power_factor=args.power_factor,
    )

    league_name = league.name if league else None
    bat_file_path = write_projections_file(bat_projections, StatCategory.BATTING, output_dir, league_name)
    pit_file_path = write_projections_file(pit_projections, StatCategory.PITCHING, output_dir, league_name)
    print("New projection files:")
    print(bat_file_path)
    print(pit_file_path)
