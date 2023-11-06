import numpy as np

from nfl_confidence.utils import dict_to_hash, get_ranks


def test_get_ranks():
    assert np.allclose(get_ranks([3, 7, 9, 1]), [2, 3, 4, 1])


def test_dict_to_hash_order():
    d1 = {
        "a": 1,
        "b": 2,
    }
    d2 = {
        "b": 2,
        "a": 1,
    }

    assert dict_to_hash(d1) == dict_to_hash(d2) == "YI3kmkYA27Wxc0knWXkuSg=="
