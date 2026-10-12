from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_env: Literal["development", "test", "production"] = "development"
    log_format: Literal["auto", "console", "json"] = "auto"
    database_url: str = "postgresql+psycopg://app:local-demo-only@localhost:5432/ecommerce"
    postgres_bin: str = ""
    provider_mode: Literal["mock", "openai"] = "mock"
    openai_api_key: str = ""
    openai_model: str = ""
    frontend_origin: str = "http://localhost:3000"
    session_cookie_name: str = "ecommerce_session"
    session_ttl_seconds: int = 28800
    action_ttl_seconds: int = 300
    chat_timeout_seconds: int = 30
    provider_timeout_seconds: int = 10
    max_agent_model_calls: int = 4
    max_agent_tool_calls: int = 4
    chat_rate_limit: int = 10
    auth_rate_limit: int = 10

    @model_validator(mode="after")
    def validate_runtime(self):
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        if self.provider_mode == "openai" and (not self.openai_model or not self.openai_api_key):
            raise ValueError("OpenAI mode requires OPENAI_MODEL and OPENAI_API_KEY")
        if self.app_env == "production":
            if self.provider_mode == "mock" or not self.frontend_origin.startswith("https://"):
                raise ValueError("Production requires real provider and HTTPS origin")
            if "local-demo-only" in self.database_url:
                raise ValueError("Production requires runtime database credentials")
        for value in (
            self.session_ttl_seconds,
            self.action_ttl_seconds,
            self.chat_timeout_seconds,
            self.provider_timeout_seconds,
            self.max_agent_model_calls,
            self.max_agent_tool_calls,
            self.chat_rate_limit,
            self.auth_rate_limit,
        ):
            if value < 1:
                raise ValueError("Execution limits must be positive")
        return self


@lru_cache
def settings():
    return Settings()
