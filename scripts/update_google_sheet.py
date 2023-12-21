import argparse
from datetime import datetime

import gspread as gs
import pandas as pd
from loguru import logger
from pytz import timezone

from nfl_confidence.odds import (
    get_the_odds_json,
    get_this_weeks_games,
    parse_the_odds_json,
)
from nfl_confidence.settings import Settings
from nfl_confidence.utils import get_ranks

parser = argparse.ArgumentParser(description="Args for computing confidence rankings")
parser.add_argument(
    "--secret_path",
    metavar="p",
    type=str,
    required=False,
    default=None,
    help="Directory containing google sheets secret",
)
parser.add_argument(
    "--username",
    metavar="u",
    type=str,
    default="lukeross",
    help="Username for google sheets account",
)
parser.add_argument(
    "--sheet",
    metavar="s",
    type=str,
    required=False,
    default="Luke NFL Confidence '23-'24",
    help="Sheet name under the account",
)
parser.add_argument(
    "--week",
    metavar="w",
    type=int,
    required=True,
    help="Week number to update",
)
parser.add_argument(
    "--max_confidence",
    metavar="m",
    type=int,
    required=False,
    default=16,
    help="Maximum confidence value for the week",
)
args = parser.parse_args()

# Constants
required_columns = [
    "id",
    "home_team",
    "away_team",
    "predicted_winner",
    "prob_variance",
    "oddsmaker_agreement",
    "confidence_prob",
    "confidence_rank",
]

# Get the google sheets secret
settings = Settings(_env_file=".env")
if args.secret_path is not None:
    secret_path = args.secret_path
elif settings.GOOGLE_SHEETS_SECRET_PATH is not None:
    secret_path = settings.GOOGLE_SHEETS_SECRET_PATH
else:
    logger.error(
        "No google sheets path provided. Must pass '--secret_path' arg, set "
        "'GOOGLE_SHEETS_SECRET_PATH' environment variable, or add to .env file"
    )
    exit()

# Check the current time
now = datetime.now(tz=timezone("US/Eastern"))
date_str = now.strftime("%I:%M on %A, %b %d")
correct_time = input(f"\n\nIs it curently {date_str}? (y/n) ")
if correct_time.lower() != "y":
    logger.error("System time is wrong. Please restart")
    exit()

# Get spreadsheet object
logger.info(f"Reading google sheet '{args.sheet}' using secret at {secret_path}")
gc = gs.service_account(filename=secret_path)
sh = gc.open(args.sheet)

# Decide whether to create new worksheet or update existing
worksheet_list = [worksheet.title for worksheet in sh.worksheets()]
worksheet_name = f"Week {args.week}"
if worksheet_name in worksheet_list:
    ws = sh.worksheet(worksheet_name)
    df = pd.DataFrame(ws.get_all_records())
    logger.debug(f"Found existing worksheet '{worksheet_name}':\n{df}")

    # Check that sheet has all required columns
    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Couldn't find required column '{column}' "
                f"among existing columns: {list(df.columns)}"
            )
else:
    logger.info(f"Could not find worksheet '{worksheet_name}' among existing: {worksheet_list}")
    proceed = input(f"\n\nWorksheet '{worksheet_name}' does not exist. Create it? (y/n) ")

    # Exit without creating a worksheet
    if proceed.lower() != "y":
        logger.info("Exiting without creating new worksheet")
        exit()

    # Create a new worksheet
    logger.info(f"Creating new worksheet {worksheet_name}")
    ws = sh.add_worksheet(title=worksheet_name, rows=20, cols=15)
    df = pd.DataFrame(columns=required_columns)


# Get Moneyline/Head2head odds
the_odds_json = get_the_odds_json(
    api_key=settings.THE_ODDS_API_KEY.get_secret_value(), odds_format="american"
)

# Parse the response json into GameOdds objects
games = parse_the_odds_json(the_odds_json=the_odds_json)

# Filter to only this week's games
games = get_this_weeks_games(games=games)

# Sort games by commence time
games = sorted(games, key=lambda x: x.commence_time)

# Check that union of existing and the-odds API games has a valid count
existing_game_ids = set(df.id)
logger.info(f"Got {len(existing_game_ids)} existing games")
api_game_ids = set(game.id for game in games)
logger.info(f"Got {len(api_game_ids)} games from the-odds API")
all_game_ids = existing_game_ids.union(api_game_ids)
logger.info(f"Got {len(all_game_ids)} total games for the week")
if not (9 <= len(all_game_ids) <= 16):
    proceed = input(
        f"\n\n{len(all_game_ids)} games is outside the normal range for regular season weeks."
        " Continue? (y/n) "
    )
    if proceed.lower() != "y":
        logger.info("Exiting without updating worksheet")
        exit()

# Filter for games that started in the past and whose confidence is already fixed
# TODO

# Compute confidence ranks
win_probs = [game.win_probability for game in games]
confidence_ranks = get_ranks(values=win_probs, zero_indexed=False)
max_conf = max(confidence_ranks)
confidence_ranks += args.max_confidence - max_conf

# Create new dataframe
new_df = pd.DataFrame(
    [
        {
            "id": game.id,
            "home_team": game.home_team.value,
            "away_team": game.away_team.value,
            "predicted_winner": game.predicted_winner.value,
            "prob_variance": game.win_probability_variance,
            "oddsmaker_agreement": game.oddsmaker_agreement,
            "confidence_prob": game.win_probability,
            "confidence_rank": confidence_rank,
        }
        for game, confidence_rank in zip(games, confidence_ranks)
    ]
)

# Get user approval to update sheet
logger.info(f"Ready to update sheet with new data:\n{new_df}")
proceed = input(f"\n\nReady to update sheet '{worksheet_name}' with the above data? (y/n) ")
if proceed.lower() != "y":
    logger.info("Exiting without updating worksheet")
    exit()

# Update the sheet
ws.update([new_df.columns.values.tolist()] + new_df.values.tolist())
logger.info(f"Successfully updated worksheet {worksheet_name}!")
