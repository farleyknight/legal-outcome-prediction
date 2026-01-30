"""Pytest configuration and fixtures."""

import os
from pathlib import Path

from dotenv import load_dotenv


def pytest_configure(config):
    """Load .env file before tests run."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
