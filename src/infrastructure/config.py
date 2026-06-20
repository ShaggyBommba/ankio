from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_output: bool = False
    file_handler_enabled: bool = True
    file_path_pattern: str = ".logs/{date}.log"
    stream_handler_enabled: bool = True
    stream_format: str = "[%(asctime)s] %(levelname)-8s [%(threadName)s] %(message)s"
    stream_date_format: str = "%H:%M:%S"

class Settings(BaseSettings):
    env: str = "development"
    name: str = "app"
    version: str = "0.1.0"
    debug: bool = False
    api_host: str = "localhost"
    api_port: int = 8002
    htmx_host: str = "localhost"
    htmx_port: int = 8003
    worker_poll_interval: int = Field(default=3, ge=1)
    worker_batch_limit: int = Field(default=100, ge=1)

    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


@lru_cache()
def get_settings(env_file: str | Path = ".env") -> Settings:
    load_dotenv(env_file, override=False)
    settings = Settings()
    return settings
