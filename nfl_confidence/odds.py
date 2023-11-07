import json
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

import numpy as np
import requests
from pydantic import BaseModel, Field, computed_field, field_validator
from pytz import timezone
from typing_extensions import Annotated

from nfl_confidence.utils import dict_to_hash


def get_valid_team_names() -> Set[str]:
    """Return a set containing all valid team names

    Returns:
        Set[str]: A set of all valid team names
    """
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    file_path = os.path.join(current_dir, "assets", "team_names.json")
    with open(file_path, "r") as f:
        name_map = json.load(f)
    return set(name_map)


def convert_team_name(name: str) -> str:
    """Convert The Odds team name to standardized valid team name

    Args:
        name (str): The Odds formatted team name

    Returns:
        str: Standardized valid team name
    """
    return name.lower().replace(" ", "-")


def add_timezone(date_str: str) -> str:
    """Adds the timezone to a date string from the-odds API

    Args:
        date_str (str): Input date string from the-odds API

    Returns:
        str: Modified date string with time zone
    """
    return date_str.replace("Z", "+00:00")


# Create an enum of valid team names
class StrEnum(str, Enum):
    pass


TeamNameEnum = StrEnum("TeamNameEnum", [(name, name) for name in get_valid_team_names()])
HeadToHeadEnum = StrEnum("HeadToHeadEnum", [("h2h", "h2h")])


class Outcome(BaseModel, extra="allow"):
    # Input fields
    name: TeamNameEnum
    price: int

    # Derived fields
    raw_win_probability: Optional[float] = None

    @field_validator("name", mode="before")
    @classmethod
    def convert_to_valid_team_name(cls, value):
        return convert_team_name(name=value)


class HeadToHeadOdds(BaseModel, extra="allow"):
    key: HeadToHeadEnum
    last_update: datetime
    outcomes: Annotated[List[Outcome], Field(min_length=2, max_length=2)]


class BookMakerOdds(BaseModel, extra="allow"):
    # Input fields
    title: str
    last_update: datetime
    markets: Annotated[List[HeadToHeadOdds], Field(min_length=1, max_length=1)]

    # Derived Fields
    predicted_winner: Optional[TeamNameEnum] = None
    win_probability: Optional[float] = None


class GameOdds(BaseModel, extra="allow"):
    # Input fields
    home_team: TeamNameEnum
    away_team: TeamNameEnum
    commence_time: datetime
    bookmakers: List[BookMakerOdds]

    @computed_field
    @property
    def game_id(self) -> int:
        data_dict = {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "commence_time": str(self.commence_time),
        }
        return dict_to_hash(d=data_dict)

    # Derived/Optional fields
    predicted_winner: Optional[TeamNameEnum] = None
    win_probability: Optional[float] = None
    win_probability_variance: Optional[float] = None
    oddsmaker_agreement: Optional[float] = None

    @field_validator("home_team", mode="before")
    @classmethod
    def convert_home_to_valid_team_name(cls, value):
        return convert_team_name(name=value)

    @field_validator("away_team", mode="before")
    @classmethod
    def convert_away_to_valid_team_name(cls, value):
        return convert_team_name(name=value)

    @field_validator("commence_time", mode="before")
    @classmethod
    def add_tz_to_commence_time(cls, value):
        return add_timezone(date_str=value)


def get_the_odds_json(api_key: str, odds_format: str = "american") -> List[Dict]:
    """Make request to the-odds API for bookmaker odds

    Args:
        api_key (str): The-odds API key
        odds_format (str, optional): Format for odds, one of "american" or "decimal" All downstream
        functions require "american" format. Defaults to "american".

    Returns:
        List[Dict]: The-odds response JSON
    """
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
    """Parse the-odds JSON response into a list of GameOdds objects

    Args:
        the_odds_json (List[Dict]): the-odds API response

    Returns:
        List[GameOdds]: the-odds API response parsed into a list of GameOdds objects
    """
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


def compute_raw_outcome_probs(game: GameOdds) -> GameOdds:
    """Computes raw_win_probability for each Outcome object in the GameOdds object. Values are raw
    in that they include the house "vig" and may not sum to 1.

    Args:
        game (GameOdds): Game to predict

    Returns:
        GameOdds: Game with raw_win_probability set for every Outcome object
    """
    for bookmaker in game.bookmakers:
        for outcome in bookmaker.markets[0].outcomes:
            outcome.raw_win_probability = convert_odds_to_probs(odds=outcome.price)
    return game


def compute_bookmaker_probs(game: GameOdds) -> GameOdds:
    """Computes predicted_winner and win_probability for each bookmaker in the game. Also computes
    raw_win_probability for each Outcome object in the game

    Args:
        game (GameOdds): Game to predict

    Returns:
        GameOdds: Game with bookmaker fields set
    """
    # First pass: compute raw, un-normalized win probs for every outcome
    game = compute_raw_outcome_probs(game=game)

    # Second pass: normalize probs to sum to 1 (removing "vig") and compute winner
    for bookmaker in game.bookmakers:
        # Get the index of the home team
        home_index = 0
        if bookmaker.markets[0].outcomes[home_index].name != game.home_team:
            home_index = 1
        assert bookmaker.markets[0].outcomes[home_index].name == game.home_team
        away_index = 1 - home_index

        # Normalize
        home_prob = bookmaker.markets[0].outcomes[home_index].raw_win_probability
        away_prob = bookmaker.markets[0].outcomes[away_index].raw_win_probability
        prob_sum = home_prob + away_prob
        home_prob = home_prob / prob_sum
        away_prob = away_prob / prob_sum
        bookmaker.markets[0].outcomes[home_index].win_probability = home_prob
        bookmaker.markets[0].outcomes[away_index].win_probability = away_prob

        # Compute bookmaker winner
        # NOTE: ties are possible, but not worth predicting. Default to home team
        if home_prob >= away_prob:
            bookmaker.predicted_winner = game.home_team
            bookmaker.win_probability = home_prob
        else:
            bookmaker.predicted_winner = game.away_team
            bookmaker.win_probability = away_prob

    return game


def compute_game_prob(game: GameOdds, weights: Optional[Dict] = None) -> GameOdds:
    """Adds the win_probability, predicted_winner, oddsmaker_agreement, and win_probability_variance
    fields to the input GameOdds object. Also adds predicted_winner and win_probability to each
    bookmaker and raw_win_probability to each Outcome

    Args:
        game (GameOdds): Game to predict
        weights (Optional[Dict], optional): A dictionary mapping Oddsmaker titles to a weighting
        factor. Any oddsmaker not provided in the weights dict will default to
        1 / len(game.bookmakers) for a simple arithmetic average. Defaults to None.

    Returns:
        GameOdds: GameOdds object with the additional fields set
    """
    # Empty dict by default
    if weights is None:
        weights = {}

    # First compute win probs for each bookmaker
    game = compute_bookmaker_probs(game=game)

    # Compute average win prob over each bookmaker
    home_prob, away_prob = 0, 0
    for bookmaker in game.bookmakers:
        weight = weights.get(bookmaker.title, 1 / len(game.bookmakers))
        if bookmaker.predicted_winner == game.home_team:
            home_prob += weight * bookmaker.win_probability
            away_prob += weight * (1.0 - bookmaker.win_probability)
        else:
            away_prob += weight * bookmaker.win_probability
            home_prob += weight * (1.0 - bookmaker.win_probability)

    # Add winner and prob to GameOdds object
    # NOTE: ties are possible, but not worth predicting. Default to home team in case of even odds
    if home_prob >= away_prob:
        game.predicted_winner = game.home_team
        game.win_probability = home_prob
    else:
        game.predicted_winner = game.away_team
        game.win_probability = away_prob

    # Compute agreement rate among betmakers
    agree = [bookmaker.predicted_winner == game.predicted_winner for bookmaker in game.bookmakers]
    game.oddsmaker_agreement = np.mean(agree)

    # Compute variance among bookmakers
    bookmaker_probs = []
    for bookmaker in game.bookmakers:
        if bookmaker.predicted_winner == game.predicted_winner:
            prob = bookmaker.win_probability
        else:
            prob = 1 - bookmaker.win_probability
        bookmaker_probs.append(prob)
    game.win_probability_variance = np.var(bookmaker_probs)

    return game
