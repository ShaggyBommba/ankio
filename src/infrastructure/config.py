from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_output: bool = False
    file_handler_enabled: bool = True
    file_path_pattern: str = ".logs/{date}.log"
    stream_handler_enabled: bool = True
    stream_format: str = "[%(asctime)s] %(levelname)-8s [%(threadName)s] %(message)s"
    stream_date_format: str = "%H:%M:%S"


class DatabaseSettings(BaseModel):
    """Configuration for the database used by repositories."""

    provider: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    user: str = "app"
    password: SecretStr = SecretStr("app")
    database: str = "app"
    ssl_mode: str | None = None

    @property
    def dsn(self) -> str:
        match self.provider:
            case "sqlite":
                return (
                    f"sqlite:///{PACKAGE_ROOT / self.database}.db"
                )
            case "postgresql":
                return (
                    f"postgresql://{self.user}:{self.password.get_secret_value()}"
                    f"@{self.host}:{self.port}/{self.database}"
                )
            case _:
                raise ValueError(f"Unsupported database provider: {self.provider}")

class OutboxSettings(BaseModel):
    """Configuration for durable outbox processing policy."""

    default_max_attempts: int = Field(default=3, ge=1)
    claim_timeout_seconds: int = Field(default=300, ge=1)


class Settings(BaseSettings):
    env: str = "development"
    name: str = "app"
    version: str = "0.1.0"
    debug: bool = False
    api_host: str = "localhost"
    api_port: int = 8002
    htmx_host: str = "localhost"
    htmx_port: int = 8034
    mcp_host: str = "localhost"
    mcp_port: int = 8035
    worker_poll_interval: int = Field(default=3, ge=1)
    worker_batch_limit: int = Field(default=100, ge=1)

    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    outbox: OutboxSettings = Field(default_factory=OutboxSettings)

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
