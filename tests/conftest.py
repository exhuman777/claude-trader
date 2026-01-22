#!/usr/bin/env python3
"""
Pytest configuration and fixtures
"""

import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary."""
    return {
        "private_key": "0x" + "a" * 64,
        "funder": "0x" + "b" * 40,
        "host": "https://clob.polymarket.com",
        "chain_id": 137,
        "signature_type": 2
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    def _mock_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(f"POLY_{key}", str(value))
    return _mock_env


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all POLY_ environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith("POLY_"):
            monkeypatch.delenv(key, raising=False)
