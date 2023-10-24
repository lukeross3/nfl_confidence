import json
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

import requests
from pydantic import BaseModel, conlist, validator
from pytz import timezone


def get_valid_team_names() -> Set[str]:
    """Return a set containing all valid team names

    Returns:
        Set[str]: A set of all valid team names
    """
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    file_path = os.path.join(current_dir, "config", "name_maps.json")
    with open(file_path, "r") as f:
        name_map = json.load(f)
    return set(name_map.keys())


def convert_team_name(name: str) -> str:
    """Convert The Odds team name to standardized valid team name

    Args:
        name (str): The Odds formatted team name

    Returns:
        str: Standardized valid team name
    """
    return name.lower().replace(" ", "-")


def add_timezone(date_str: str) -> str:
    return date_str.replace("Z", "+00:00")


# Create an enum of valid team names
class StrEnum(str, Enum):
    pass


TeamNameEnum = StrEnum("TeamNameEnum", [(name, name) for name in get_valid_team_names()])
HeadToHeadEnum = StrEnum("HeadToHeadEnum", [("h2h", "h2h")])


class Outcome(BaseModel, extra="allow"):
    name: TeamNameEnum
    price: int

    @validator("name", pre=True)
    def convert_to_valid_team_name(cls, value):
        return convert_team_name(name=value)


class HeadToHeadOdds(BaseModel, extra="allow"):
    key: HeadToHeadEnum
    last_update: datetime
    outcomes: conlist(Outcome, min_length=2, max_length=2)


class BookMakerOdds(BaseModel, extra="allow"):
    title: str
    last_update: datetime
    markets: conlist(HeadToHeadOdds, min_length=1, max_length=1)


class GameOdds(BaseModel, extra="allow"):
    # Input fields
    home_team: TeamNameEnum
    away_team: TeamNameEnum
    commence_time: datetime
    bookmakers: List[BookMakerOdds]

    # Derived/Optional fields
    predicted_winner: Optional[TeamNameEnum] = None
    win_probability: Optional[float] = None

    @validator("home_team", pre=True)
    def convert_home_to_valid_team_name(cls, value):
        return convert_team_name(name=value)

    @validator("away_team", pre=True)
    def convert_away_to_valid_team_name(cls, value):
        return convert_team_name(name=value)

    @validator("commence_time", pre=True)
    def add_tz_to_commence_time(cls, value):
        return add_timezone(date_str=value)


def get_the_odds_json(api_key: str, odds_format: str = "american") -> List[Dict]:
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    params = {
        "regions": "us",
        "apiKey": api_key,
        "markets": "h2h",
        "oddsFormat": odds_format,
    }
    resp = requests.get(url, params)
    resp.raise_for_status()
    return resp.json()


def parse_the_odds_json(the_odds_json: List[Dict]) -> List[GameOdds]:
    return [GameOdds(**game) for game in the_odds_json]


def filter_games_by_date(
    games: List[GameOdds], after: datetime = datetime.min, before: datetime = datetime.max
) -> List[GameOdds]:
    """Filter the list of games down to only those with a commence_time between the given range.

    Args:
        games (List[GameOdds]): List of GameOdds objects
        after (datetime, optional): Keep only games with commence_time strictly greater than after.
            Defaults to datetime.min.
        before (datetime, optional): Keep only games with commence_time strictly less than after.
            Defaults to datetime.max.

    Returns:
        List[GameOdds]: Filter game list
    """
    return [game for game in games if after < game.commence_time < before]


def get_this_weeks_games(games: List[GameOdds]) -> List[GameOdds]:
    """Filter games list to only those between now and the coming Tuesday (since Monday Night
    Football is the last game of the week)

    Args:
        games (List[GameOdds]): List of games

    Returns:
        List[GameOdds]: Filtered list of games
    """
    # Compute the number of days until Tuesday
    now = datetime.now(tz=timezone("US/Eastern"))
    today = now.weekday()
    tuesday = 1  # Tuesday has int value 1 in datetime
    days_til_tuesday = (tuesday - today) % 7

    # If today is Tuesday, get a week from today
    if days_til_tuesday == 0:
        days_til_tuesday = 7

    # Keep only games between now and the coming Tuesday
    next_tuesday = now + timedelta(days=days_til_tuesday)
    return filter_games_by_date(
        games=games,
        after=now,
        before=next_tuesday,
    )


def convert_odds_to_probs(odds: float) -> float:
    """Convert american odds for moneyline into implied win probability. Calculation is taken from
    https://www.gamingtoday.com/tools/implied-probability/

    Args:
        odds (float): American moneyline odds (can be positive or negative)

    Returns:
        float: Implied win probability
    """
    if odds < 0:
        return (-1 * odds) / (-1 * odds + 100)
    else:
        return 100 / (odds + 100)


def compute_game_prob(game: GameOdds, weights: Optional[Dict] = None) -> GameOdds:
    """Adds the win_probability and predicted_winner fields to the input GameOdds object

    Args:
        game (GameOdds): Game to predict
        weights (Optional[Dict], optional): A dictionary mapping Oddsmaker titles to a weighting
        factor. Any oddsmaker not provided in the weights dict will default to
        1 / len(game.bookmakers) for a simple arithmetic average. Defaults to None.

    Returns:
        GameOdds: GameOdds object with the predicted_winner and win_probability fields set
    """
    # Empty dict by default
    if weights is None:
        weights = {}

    # Compute probs from odds for home and away team
    home_prob, away_prob = 0, 0
    for bookmaker in game.bookmakers:
        weight = weights.get(bookmaker.title, 1 / len(game.bookmakers))
        for outcome in bookmaker.markets[0].outcomes:
            if outcome.name == game.home_team:
                home_prob += weight * convert_odds_to_probs(odds=outcome.price)
            else:
                away_prob += weight * convert_odds_to_probs(odds=outcome.price)

    # Re-normalize since oddsmakers include a "vig" to give the house an edge
    home_prob /= home_prob + away_prob
    away_prob /= home_prob + away_prob

    # Add winner and prob to GameOdds object
    # NOTE: ties are possible, but not worth predicting. Default to home team in case of even odds
    if home_prob >= away_prob:
        game.predicted_winner = game.home_team
        game.win_probability = home_prob
    else:
        game.predicted_winner = game.away_team
        game.win_probability = away_prob
    return game
