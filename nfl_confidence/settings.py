from pydantic import SecretStr, extra
from pydantic_settings import BaseSettings


class Settings(BaseSettings, Extra=extra.forbid):
    THE_ODDS_API_KEY: SecretStr
