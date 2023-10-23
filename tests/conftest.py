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
