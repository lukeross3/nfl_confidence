import json
import os

import pytest


@pytest.fixture
def the_odds_file_path():
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    return os.path.join(current_dir, "assets", "the_odds_american.json")


@pytest.fixture
def the_odds_resp_json(the_odds_file_path):
    with open(the_odds_file_path, "r") as f:
        return json.load(f)


def _read_asset(name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "assets", name), "r") as f:
        return f.read()


@pytest.fixture
def group_picks_week1_html():
    """A finished week: every game has a winner"""
    return _read_asset("yahoo_group_picks_week1.html")


@pytest.fixture
def group_picks_week4_html():
    """An in-progress week: only the first game has been played"""
    return _read_asset("yahoo_group_picks_week4.html")
