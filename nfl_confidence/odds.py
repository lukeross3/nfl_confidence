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
    name: TeamNameEnum
    price: int

    @computed_field
    @property
    def raw_win_probability(self) -> float:
        return convert_odds_to_probs(odds=self.price)

    @field_validator("name", mode="before")
    @classmethod
    def convert_to_valid_team_name(cls, value):
        return convert_team_name(name=value)


class HeadToHeadOdds(BaseModel, extra="allow"):
    key: HeadToHeadEnum
    last_update: datetime
    outcomes: Annotated[List[Outcome], Field(min_length=2, max_length=2)]


class BookMakerOdds(BaseModel, extra="allow"):
    title: str
    last_update: datetime
    markets: Annotated[List[HeadToHeadOdds], Field(min_length=1, max_length=1)]

    @computed_field
    @property
    def win_probability(self) -> float:
        raw_probs = np.array([outcome.raw_win_probability for outcome in self.markets[0].outcomes])
        normalized_probs = raw_probs / np.sum(raw_probs)
        return np.max(normalized_probs)

    @computed_field
    @property
    def predicted_winner(self) -> Optional[TeamNameEnum]:
        raw_probs = [outcome.raw_win_probability for outcome in self.markets[0].outcomes]

        # In case of tie, return None
        if raw_probs[0] == raw_probs[1]:
            return None

        max_idx = np.argmax(raw_probs)
        return self.markets[0].outcomes[max_idx].name


class GameOdds(BaseModel, extra="allow"):
    # Input fields
    id: str
    home_team: TeamNameEnum
    away_team: TeamNameEnum
    commence_time: datetime
    bookmakers: List[BookMakerOdds]

    @computed_field
    @property
    def home_team_win_prob(self) -> float:
        home_prob = 0.0
        for bookmaker in self.bookmakers:
            if bookmaker.predicted_winner == self.home_team:
                home_prob += bookmaker.win_probability
            elif bookmaker.predicted_winner == self.away_team:
                home_prob += 1.0 - bookmaker.win_probability
            else:
                home_prob += 0.5
        return home_prob / len(self.bookmakers)

    @computed_field
    @property
    def away_team_win_prob(self) -> float:
        return 1.0 - self.home_team_win_prob

    @computed_field
    @property
    def predicted_winner(self) -> TeamNameEnum:
        if self.home_team_win_prob >= self.away_team_win_prob:
            return self.home_team
        else:
            return self.away_team

    @computed_field
    @property
    def win_probability(self) -> float:
        return max(self.home_team_win_prob, self.away_team_win_prob)

    @computed_field
    @property
    def win_probability_variance(self) -> float:
        bookmaker_probs = []
        for bookmaker in self.bookmakers:
            if bookmaker.predicted_winner == self.predicted_winner:
                prob = bookmaker.win_probability
            elif bookmaker.predicted_winner == self.away_team:
                prob = 1.0 - bookmaker.win_probability
            else:
                prob = 0.5
            bookmaker_probs.append(prob)
        return np.var(bookmaker_probs)

    @computed_field
    @property
    def oddsmaker_agreement(self) -> float:
        agree = [
            bookmaker.predicted_winner == self.predicted_winner for bookmaker in self.bookmakers
        ]
        return np.mean(agree)

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
