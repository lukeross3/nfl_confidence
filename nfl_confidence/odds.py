import json
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Set

import requests
from pydantic import BaseModel, validator
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


class BookMakerOdds(BaseModel, extra="allow"):
    title: str
    last_update: datetime
    markets: List


class GameOdds(BaseModel, extra="allow"):
    home_team: TeamNameEnum
    away_team: TeamNameEnum
    commence_time: datetime
    bookmakers: List[BookMakerOdds]

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


def convert_odds_to_probs():
    pass
