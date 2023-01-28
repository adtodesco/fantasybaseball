import argparse
import pathlib
import time

import pandas as pd
import progressbar
import requests
import yaml

from fantasybaseball.fangraphs import pull_projections
from fantasybaseball.model import ProjectionType, StatType
from fantasybaseball.projections import augment_projections, write_projections_file


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--projection-types", nargs="+", default=[p.value for p in ProjectionType])
    parser.add_argument("-s", "--stat-types", nargs="+", default=[s.value for s in StatType])
    parser.add_argument("-r", "--rest-of-season", default=False)
    parser.add_argument("-l", "--league-file", default=None)
    parser.add_argument("-o", "--output-dir", default="projections/")
    return parser.parse_args()


def create_jobs(stat_types, projection_types, ros=False):
    jobs = list()
    for projection_type in projection_types:
        for stat_type in stat_types:
            jobs.append(
                {
                    "projection_type": projection_type,
                    "stat_type": stat_type,
                    "ros": ros,
                }
            )

    return jobs


def run_jobs(jobs, retries=3):
    bat_projections = list()
    pit_projections = list()
    bar = progressbar.ProgressBar(max_value=len(jobs)).start()
    for job in jobs:
        while True:
            try:
                projections = pull_projections(**job)
                if projections.empty:
                    break
                if job["stat_type"] == StatType.BATTING:
                    bat_projections.append(projections)
                else:
                    pit_projections.append(projections)
                break
            except requests.exceptions.ConnectionError:
                if retries:
                    time.sleep(5)
                else:
                    raise
        bar.update(bar.value + 1)
    bar.finish()

    return pd.concat(bat_projections, ignore_index=True), pd.concat(pit_projections, ignore_index=True)


def main():
    args = get_args()
    stat_types = [StatType(st) for st in args.stat_types]
    projection_types = [ProjectionType(pt) for pt in args.projection_types]
    output_dir = pathlib.Path(args.output_dir).resolve()
    league = None
    if args.league_file:
        with open(pathlib.Path(args.league_file).resolve()) as f:
            league = yaml.safe_load(f)

    jobs = create_jobs(stat_types, projection_types)
    bat_projections, pit_projections = run_jobs(jobs)

    bat_projections, pit_projections = augment_projections(bat_projections, pit_projections, league)

    write_projections_file(bat_projections, StatType.BATTING, output_dir)
    write_projections_file(pit_projections, StatType.PITCHING, output_dir)


if __name__ == "__main__":
    main()
