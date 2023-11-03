import argparse

import dotenv
import pandas as pd

from nfl_confidence.odds import (
    compute_game_prob,
    get_the_odds_json,
    get_this_weeks_games,
    parse_the_odds_json,
)
from nfl_confidence.settings import Settings
from nfl_confidence.utils import get_ranks

# Setup and parse script args
parser = argparse.ArgumentParser(description="Args for computing confidence rankings")
parser.add_argument(
    "--max_confidence",
    metavar="m",
    type=int,
    required=False,
    default=16,
    help="Maximum confidence value for the week",
)
parser.add_argument(
    "--verbose",
    action="store_true",
    required=False,
    help="Whether to print the results column by column",
)
parser.add_argument("--skip_errors", dest="skip_errors", action="store_true")
parser.set_defaults(skip_errors=False)
args = parser.parse_args()

# Load env and settings
dotenv.load_dotenv()
settings = Settings()

# Get Moneyline/Head2head odds
the_odds_json = get_the_odds_json(
    api_key=settings.THE_ODDS_API_KEY.get_secret_value(), odds_format="american"
)

# Parse the response json into GameOdds objects
games = parse_the_odds_json(the_odds_json=the_odds_json)

# Filter to only this week's games
games = get_this_weeks_games(games=games)

# Compute winners and probabilities for each game
games = [compute_game_prob(game=game) for game in games]

# Sort games by commence time
games = sorted(games, key=lambda x: x.commence_time)

# Compute confidence ranks
win_probs = [game.win_probability for game in games]
confidence_ranks = get_ranks(values=win_probs, zero_indexed=False)
max_conf = max(confidence_ranks)
confidence_ranks += args.max_confidence - max_conf

# Create pandas dataframe
df = pd.DataFrame(
    [
        {
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

# Display the data frame
print(df, "\n")
if args.verbose:
    for column in df.columns:
        print(column)
        for val in list(df[column]):
            print(val)
        print("\n")
