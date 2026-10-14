import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Iterable, List

import gspread
import numpy as np
import yaml
from loguru import logger
from pydantic import BaseModel
from pytz import timezone
from tenacity import after_log, before_sleep_log, retry, wait_exponential

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def load_asset(name: str) -> Any:
    """Load a JSON file from the package's assets folder

    Args:
        name (str): File name, e.g. "team_names.json"

    Returns:
        Any: The parsed JSON
    """
    with open(os.path.join(ASSETS_DIR, name), "r") as f:
        return json.load(f)


def confirm_system_time() -> None:
    """Ask the user to confirm the system time, which decides which games count as this
    week's and which have started. Exits with code 1 if they say it's wrong.
    """
    date_str = datetime.now(tz=timezone("US/Eastern")).strftime("%I:%M on %A, %b %d")
    if input(f"Is it currently {date_str}? (y/n) ").lower() != "y":
        logger.error("System time is wrong. Please restart")
        sys.exit(1)


def get_ranks(values: List[float], zero_indexed: bool = False) -> List[int]:
    """Generate a ranking of the input values. E.g. [3, 7, 9, 1] -> [2, 3, 4, 1]

    Args:
        values (List[float]): [description]
        zero_indexed (bool, optional): [description]. Defaults to False.

    Returns:
        List[int]: [description]
    """
    offset = 0
    if not zero_indexed:
        offset = 1
    return offset + np.argsort(np.argsort(values))


def get_unused_confidence(
    n_games: int, used: Iterable[int] = (), max_confidence: int = 16
) -> List[int]:
    """Get the confidence values still available for a week. A week with n_games games uses
    values (max_confidence - n_games + 1) through max_confidence.

    Args:
        n_games (int): Total number of games in the week, including ones already played
        used (Iterable[int], optional): Values already used on locked games. Defaults to ().
        max_confidence (int, optional): Highest confidence value. Defaults to 16.

    Returns:
        List[int]: Unused values, ascending
    """
    all_values = range(max_confidence - n_games + 1, max_confidence + 1)
    return sorted(set(all_values) - set(used))


def assign_confidence(win_probs: List[float], values: List[int]) -> List[int]:
    """Greedily assign confidence values to games, highest values to the most likely winners.
    If there are more values than games, the lowest values go unused.

    Args:
        win_probs (List[float]): Predicted winner's win probability for each game
        values (List[int]): Confidence values available to assign

    Raises:
        ValueError: If there are fewer values than games

    Returns:
        List[int]: Confidence value for each game, in the same order as win_probs
    """
    if len(values) < len(win_probs):
        raise ValueError(f"{len(win_probs)} games but only {len(values)} confidence values left")
    n_unused = len(values) - len(win_probs)
    top_values = sorted(values)[n_unused:]
    return [top_values[rank - 1] for rank in get_ranks(values=win_probs)]


def read_config(config_path: str, config_class: BaseModel) -> BaseModel:
    """Read the yaml config from the config_path and return an instance of the given config_class

    Args:
        config_path (str): Path to the config yaml file
        config_class (BaseModel): Config class to instantiate

    Returns:
        BaseModel: Instance of the config class with values from config path
    """
    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)
    return config_class(**config_dict)


@retry(
    wait=wait_exponential(max=90),
    before_sleep=before_sleep_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
)
def update_cell(ws: gspread.Worksheet, row: int, col: int, value: Any) -> None:
    """Update a cell value, with retries to avoid write rate limiting

    Args:
        ws (gspread.worksheet): gspread worksheet object
        row (int): Row index to update
        col (int): Column index to update
        value (Any): Value to insert
    """
    ws.update_cell(row, col, value)
