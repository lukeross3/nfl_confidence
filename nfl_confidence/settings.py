from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Settings values
    THE_ODDS_API_KEY: SecretStr
    GOOGLE_SHEETS_SECRET_PATH: str | None

    # Settings config
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")
