"""Application settings, validated from the environment at startup.

Optional variables ship as ``None`` and are validated when their dependent
code runs, so the package can be imported without a fully configured
environment.
"""

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO")

    aws_region: str | None = Field(default=None)
    aws_access_key_id: str | None = Field(default=None)
    aws_secret_access_key: str | None = Field(default=None)
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0")
    bedrock_embedding_model_id: str = Field(default="amazon.titan-embed-text-v2:0")
    bedrock_max_retries: int = Field(default=3)

    database_url: str | None = Field(default=None)

    checkpoint_path: str = Field(
        default=".data/checkpoints.db",
        validation_alias=AliasChoices("LEXAGENT_CHECKPOINT_PATH", "CHECKPOINT_PATH"),
    )

    eval_mode: str = Field(
        default="auto",
        validation_alias=AliasChoices("LEXAGENT_EVAL_MODE", "EVAL_MODE"),
    )

    checkpoint_backend: Literal["sqlite", "postgres"] = Field(
        default="sqlite",
        validation_alias=AliasChoices("CHECKPOINT_BACKEND", "LEXAGENT_CHECKPOINT_BACKEND"),
    )

    s3_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_BUCKET", "LEXAGENT_S3_BUCKET"),
    )

    require_api_key: bool = Field(
        default=False,
        validation_alias=AliasChoices("REQUIRE_API_KEY", "LEXAGENT_REQUIRE_API_KEY"),
    )

    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LEXAGENT_API_KEY", "API_KEY"),
    )


settings = Settings()
