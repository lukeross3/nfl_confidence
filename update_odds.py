import os
import json
import time
import statistics
import argparse
from collections import OrderedDict

import requests
from diskcache import Cache


def main(args):
    # Initlialize cache
    config = json.load(open(args.config_path, "r"))
    cache_dir = config["cache_dir"]
    cache = Cache(cache_dir)

    # Get odds json from cache or make request of expired
    if "odds" in cache:
        odds = cache["odds"]
    else:
        url = "https://api.the-odds-api.com/v3/odds/"
        params = {
            "sport": "americanfootball_nfl",
            "region": "us",
            "apiKey": config["odds_api_key"],
            "mkt": "spreads"
        }
        resp = requests.get(url, params)
        resp.raise_for_status()
        odds = resp.json()
        cache.set("odds", odds, expire=60*60)

    # Get aggregator from args
    if args.aggregator == "mean":
        aggregator = statistics.mean
    elif args.aggregator == "mode":
        aggregator = statistics.mode
    elif args.aggregator == "median":
        aggregator = statistics.median

    # Write relevant fields to odds.json
    output = []
    for game in odds["data"]:
        team_a_spreads = [float(s["odds"]["spreads"]["points"][0]) for s in game["sites"]]
        output_game = OrderedDict()
        output_game["team_a"] = game["teams"][0]
        output_game["team_b"] = game["teams"][1]
        output_game["team_a_spread"] = aggregator(team_a_spreads)
        output.append(output_game)
    with open(args.output_path, "w") as f:
        json.dump(output, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config_path', metavar='c', type=str, default="config.json", help='config file path'
    )
    parser.add_argument(
        '--output_path', metavar='o', type=str, default="odds.json", help='output file path'
    )
    parser.add_argument(
        '--aggregator', metavar='a', type=str, default="median", help='aggregator for multiple spreads (default: median)'
    )
    args = parser.parse_args()
    main(args)