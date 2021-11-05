import glob
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
