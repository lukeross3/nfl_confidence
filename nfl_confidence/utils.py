import glob
import json
import os
from typing import List

import numpy as np


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


def get_secret_key_path(directory: str, username: str) -> str:
    """Find the user's secret key in the directory and return its path

    Args:
        directory (str): Secrets directory
        username (str): Username for secret

    Returns:
        str: Path to secret file
    """
    matching_paths = glob.glob(os.path.join(directory, f"{username}-*"))
    n_matches = len(matching_paths)
    if n_matches == 0:
        raise ValueError(f"No matching secrets for username {username} in directory {directory}")
    elif n_matches > 1:
        raise ValueError(
            f"Ambiguous: found {n_matches} > 1 matching secrets for username {username} in "
            f"directory {directory}"
        )
    return matching_paths[0]


def load_team_name_map():

    # Load original map
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, os.path.pardir, "config", "name_maps.json")
    with open(config_path, "r") as f:
        official_to_nicknames = json.load(f)

    # Reverse map direction
    nickname_to_official = {}
    for official, nicknames in official_to_nicknames.items():
        nicknames.append(official)  # Map the official name back to itself
        for nickname in nicknames:
            # assert nickname not in nickname_to_official, f"Repeated nickname: {nickname}"
            nickname_to_official[nickname] = official
    return nickname_to_official
