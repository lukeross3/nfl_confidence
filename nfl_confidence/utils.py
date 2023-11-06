import base64
import hashlib
import json
from typing import Dict, List

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


def dict_to_hash(d: Dict) -> str:
    # Convert dict to string. Need to sort to make sure we are insensitive to insertion order
    dict_str = json.dumps(
        d,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        indent=None,
        skipkeys=False,
    )

    # Convert string to hash digest
    digest = hashlib.md5(dict_str.encode("utf-8")).digest()

    # Convert hash digest into base64 string
    return base64.b64encode(digest).decode("utf-8")
