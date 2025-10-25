"""Pytest configuration and shared fixtures."""

import pytest
from nas_media_catalog.config import setup_logging


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for all tests with consistent format."""
    setup_logging("INFO")
