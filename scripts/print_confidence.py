import argparse
import sys
from datetime import datetime

import pandas as pd
from loguru import logger
from pytz import timezone

from nfl_confidence.odds import (
    get_the_odds_json,
    get_this_weeks_games,
    parse_the_odds_json,
)
from nfl_confidence.settings import Settings
from nfl_confidence.utils import assign_confidence, get_unused_confidence
from nfl_confidence.yahoo import (
    DEFAULT_STATE_PATH,
    get_current_week,
    get_league_picks,
    get_locked_picks,
    get_matchups,
    get_page,
    get_session,
    get_top_picks,
    parse_group_picks,
    parse_week_games,
    pickem_url,
)

# Setup and parse script args
parser = argparse.ArgumentParser(description="Args for computing confidence rankings")
parser.add_argument(
    "--max_confidence",
    metavar="m",
    type=int,
    required=False,
    default=16,
    help="Maximum confidence value for the week. With --yahoo, it's set to the week's number of "
    "games instead, since Yahoo uses values 1 through the number of games",
)
parser.add_argument(
    "--verbose",
    action="store_true",
    required=False,
    help="Whether to print the results column by column",
)
parser.add_argument("--skip_errors", dest="skip_errors", action="store_true")
parser.set_defaults(skip_errors=False)
parser.add_argument(
    "--yahoo",
    action="store_true",
    help="Pull this week's games and your picks on games already started from Yahoo, and only "
    "assign the confidence values those picks haven't used",
)
parser.add_argument("--group_id", type=int, default=39345, help="Yahoo Pick'em group ID")
parser.add_argument("--team_id", type=int, default=3, help="Your team ID in the Yahoo group")
parser.add_argument("--state_path", type=str, default=DEFAULT_STATE_PATH)
args = parser.parse_args()

# Load env and settings
settings = Settings(_env_file=".env")

# Check the current time
now = datetime.now(tz=timezone("US/Eastern"))
date_str = now.strftime("%I:%M on %A, %b %d")
correct_time = input(f"Is it curently {date_str}? (y/n) ")
if correct_time.lower() != "y":
    logger.error("System time is wrong. Please restart")
    exit()

# Get Moneyline/Head2head odds
the_odds_json = get_the_odds_json(
    api_key=settings.THE_ODDS_API_KEY.get_secret_value(), odds_format="american"
)

# Parse the response json into GameOdds objects
games = parse_the_odds_json(the_odds_json=the_odds_json)

# Filter to only this week's games
games = get_this_weeks_games(games=games)

# Sort games by commence time, then ID to keep order the same on subsequent runs
games = sorted(games, key=lambda x: (x.commence_time, x.id))
if not games:
    raise ValueError(
        "No open games left this week in the odds API (e.g. after Monday night's kickoff). "
        "Rerun once next week's games are listed"
    )

# Find which confidence values are still available
n_games = len(games)
max_confidence = args.max_confidence
used_confidence = []
past_top_picks = {}
if args.yahoo:
    session = get_session(args.state_path)
    group_picks_url = pickem_url(f"{args.group_id}/grouppicks")
    html = get_page(session, group_picks_url)
    week = get_current_week(html)
    week_games = parse_week_games(html, week)

    # Yahoo may still show last week until it rolls over
    open_matchups = {frozenset((game.home_team.value, game.away_team.value)) for game in games}
    if not open_matchups & set(get_matchups(week_games)):
        week += 1
        html = get_page(session, f"{group_picks_url}?week={week}")
        week_games = parse_week_games(html, week)

    # Games that already started have used up the confidence values picked on them
    locked = get_locked_picks(
        week_games=week_games,
        picks=parse_group_picks(html, week),
        team_id=args.team_id,
        open_matchups=open_matchups,
    )
    # Yahoo's values run 1 through the week's number of games, so bye weeks top out below 16
    n_games = len(week_games)
    max_confidence = n_games
    used_confidence = locked.confidence.dropna().astype(int).tolist()
    logger.info(f"Week {week}: {len(locked)} of {n_games} games already started")
    for game in locked.itertuples():
        if pd.isna(game.confidence):
            logger.warning(
                f"No visible pick on started game {game.favorite} vs {game.underdog}, "
                "treating its confidence value as unused"
            )
        else:
            result = {True: "won", False: "lost"}.get(game.correct, "pending")
            logger.info(f"  Picked {game.pick} at {int(game.confidence)} ({result})")

    # Teams you've already used as a week's top pick, which the league doesn't allow repeating
    past_picks = get_league_picks(session, args.group_id, last_week=week - 1)
    past_top_picks = get_top_picks(past_picks, args.team_id)

# Compute confidence ranks, using the highest values still available
available_confidence = get_unused_confidence(
    n_games=n_games, used=used_confidence, max_confidence=max_confidence
)
if args.yahoo:
    logger.info(f"Assigning confidence values {available_confidence}")
win_probs = [game.win_probability for game in games]
confidence_ranks = assign_confidence(win_probs=win_probs, values=available_confidence)

# Create pandas dataframe
df = pd.DataFrame(
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

# Display the data frame
print(df, "\n")
if args.verbose:
    for column in df.columns:
        print(column)
        for val in list(df[column]):
            print(val)
        print("\n")

# Warn loudly, last so it isn't missed, if the top pick repeats a team already used at the top
sys.stdout.flush()
top_picks = df.loc[df.confidence_rank == max_confidence, "predicted_winner"]
for team in top_picks:
    if team in past_top_picks:
        weeks_used = ", ".join(str(week) for week in past_top_picks[team])
        banner = "!" * 80
        logger.warning(
            f"\n{banner}\n"
            f"  REPEAT TOP PICK: recommended {max_confidence} is {team}, "
            f"already your top pick in week {weeks_used}\n"
            f"  Pick a different {max_confidence} before submitting\n"
            f"{banner}"
        )
