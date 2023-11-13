import numpy as np

from nfl_confidence.utils import get_ranks


def test_get_ranks():
    assert np.allclose(get_ranks([3, 7, 9, 1]), [2, 3, 4, 1])
