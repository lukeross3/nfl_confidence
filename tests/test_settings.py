import os

import pytest
from pydantic_core import ValidationError

from nfl_confidence.settings import Settings


def test_settings_raises_error_if_no_api_key():
    if "THE_ODDS_API_KEY" in os.environ:
        del os.environ["THE_ODDS_API_KEY"]
    with pytest.raises(ValidationError):
        Settings()
