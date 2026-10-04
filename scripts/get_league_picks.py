import argparse
import os
from datetime import datetime

from loguru import logger

from nfl_confidence.yahoo import add_yahoo_args, get_league_picks, get_session

# Setup and parse script args
now = datetime.now()
parser = argparse.ArgumentParser(
    description="Download every league member's picks from Yahoo Pick'em group picks pages"
)
add_yahoo_args(parser)
parser.add_argument(
    "--season",
    type=int,
    default=now.year if now.month >= 3 else now.year - 1,
    help="Season year, only used to name the output file",
)
parser.add_argument("--first_week", type=int, default=1)
parser.add_argument("--last_week", type=int, default=18)
parser.add_argument("--output_path", type=str, default=None)
args = parser.parse_args()
output_path = args.output_path or os.path.join("results", f"league_picks_{args.season}.csv")

# Fetch and parse each week's group picks page
session = get_session(args.state_path)
picks = get_league_picks(session, args.group_id, args.first_week, args.last_week)
picks.to_csv(output_path, index=False)
logger.info(f"Wrote {len(picks)} picks over {picks.week.nunique()} weeks to {output_path}")

# Summarize finished games: points and accuracy by member. Pending games have correct missing,
# which mean and count skip.
summary = picks.groupby("team_name").agg(
    points=("points", "sum"),
    accuracy=("correct", "mean"),
    games=("correct", "count"),
)
print(summary.sort_values("points", ascending=False).round(3).to_string())
