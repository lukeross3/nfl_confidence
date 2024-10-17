import logging
from typing import Any, List

import gspread
import numpy as np
import yaml
from loguru import logger
from pydantic import BaseModel
from tenacity import after_log, before_sleep_log, retry, wait_exponential


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
