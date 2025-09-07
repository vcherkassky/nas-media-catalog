"""Configuration management for NAS Media Catalog."""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # UPnP Media Server Settings
    upnp_discovery_timeout: int = Field(
        default=10, description="UPnP discovery timeout in seconds"
    )
    upnp_server_name: str = Field(
        default="",
        description="Specific UPnP server name to connect to (empty = auto-discover)",
    )

    # Server Settings
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")

    # Database Settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./media_catalog.db", description="Database URL"
    )

    # Scanning Settings
    max_scan_depth: int = Field(
        default=5, description="Maximum directory depth for scanning"
    )
    auto_scan_on_startup: bool = Field(
        default=True, description="Automatically scan NAS on startup"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


# Global settings instance
settings = Settings()


def setup_logging(level: str = None) -> None:
    """
    Configure logging with a consistent format across the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses the level from settings.
    """
    log_level = level or settings.log_level

    # Standard format for all logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        force=True,  # Override any existing configuration
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
