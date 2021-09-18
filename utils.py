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
