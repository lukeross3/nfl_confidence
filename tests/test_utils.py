import numpy as np
import pytest

from nfl_confidence.utils import (
    assign_confidence,
    confirm_system_time,
    get_ranks,
    get_unused_confidence,
)


def test_confirm_system_time(monkeypatch):
    # Confirmed: carry on
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    confirm_system_time()

    # Wrong time: exit with an error code
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    with pytest.raises(SystemExit) as exit_info:
        confirm_system_time()
    assert exit_info.value.code == 1


def test_get_ranks():
    assert np.allclose(get_ranks([3, 7, 9, 1]), [2, 3, 4, 1])


def test_get_unused_confidence():
    assert get_unused_confidence(n_games=16) == list(range(1, 17))
    assert get_unused_confidence(n_games=14) == list(range(3, 17))
    assert get_unused_confidence(n_games=16, used=[16, 5]) == [
        v for v in range(1, 17) if v not in (5, 16)
    ]


def test_assign_confidence():
    # Highest values go to the most likely winners
    assert assign_confidence([0.6, 0.9, 0.7], [14, 15, 16]) == [14, 16, 15]
    assert assign_confidence([0.6, 0.9, 0.7], [1, 5, 16]) == [1, 16, 5]

    # Extra values: the lowest go unused
    assert assign_confidence([0.6, 0.9], [1, 5, 16]) == [5, 16]

    with pytest.raises(ValueError):
        assign_confidence([0.6, 0.9, 0.7], [15, 16])
