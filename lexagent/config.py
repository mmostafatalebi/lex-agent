"""Application settings, validated from the environment at startup.

Optional variables ship as ``None`` and are validated when their dependent
code runs, so the package can be imported without a fully configured
environment.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO")


settings = Settings()
