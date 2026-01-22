#!/usr/bin/env python3
"""
Tests for config.py - Configuration Management
"""

import os
import json
import tempfile
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    Config,
    ClobConfig,
    TradingConfig,
    StorageConfig,
    ConfigError,
    ConfigNotFoundError,
    get_env,
    get_env_bool,
    get_env_int,
    get_env_float,
)


class TestEnvHelpers:
    """Tests for environment variable helper functions."""

    def test_get_env_with_prefix(self, monkeypatch):
        """Test get_env with POLY_ prefix."""
        monkeypatch.setenv("POLY_TEST_VAR", "prefixed_value")
        assert get_env("TEST_VAR") == "prefixed_value"

    def test_get_env_without_prefix(self, monkeypatch):
        """Test get_env fallback to non-prefixed."""
        monkeypatch.setenv("TEST_VAR2", "unprefixed_value")
        assert get_env("TEST_VAR2") == "unprefixed_value"

    def test_get_env_default(self):
        """Test get_env returns default when not set."""
        assert get_env("NONEXISTENT_VAR", "default") == "default"

    def test_get_env_bool_true(self, monkeypatch):
        """Test get_env_bool with truthy values."""
        for val in ["1", "true", "yes", "on", "TRUE", "Yes"]:
            monkeypatch.setenv("POLY_BOOL_TEST", val)
            assert get_env_bool("BOOL_TEST") is True

    def test_get_env_bool_false(self, monkeypatch):
        """Test get_env_bool with falsy values."""
        for val in ["0", "false", "no", "off", "FALSE", "No"]:
            monkeypatch.setenv("POLY_BOOL_TEST", val)
            assert get_env_bool("BOOL_TEST") is False

    def test_get_env_int(self, monkeypatch):
        """Test get_env_int conversion."""
        monkeypatch.setenv("POLY_INT_TEST", "42")
        assert get_env_int("INT_TEST") == 42

    def test_get_env_int_invalid(self, monkeypatch):
        """Test get_env_int with invalid value."""
        monkeypatch.setenv("POLY_INT_TEST", "not_an_int")
        assert get_env_int("INT_TEST", 99) == 99

    def test_get_env_float(self, monkeypatch):
        """Test get_env_float conversion."""
        monkeypatch.setenv("POLY_FLOAT_TEST", "3.14")
        assert get_env_float("FLOAT_TEST") == 3.14


class TestClobConfig:
    """Tests for ClobConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        clob = ClobConfig()
        assert clob.host == "https://clob.polymarket.com"
        assert clob.chain_id == 137
        assert clob.signature_type == 2

    def test_is_valid(self):
        """Test is_valid method."""
        clob = ClobConfig()
        assert clob.is_valid() is True

        clob.host = ""
        assert clob.is_valid() is False

        clob.host = "not_a_url"
        assert clob.is_valid() is False


class TestTradingConfig:
    """Tests for TradingConfig dataclass."""

    def test_default_values(self):
        """Test default trading configuration."""
        trading = TradingConfig()
        assert trading.default_size == 10.0
        assert trading.spike_threshold == 0.05
        assert trading.take_profit == 0.10
        assert trading.stop_loss == 0.05


class TestConfig:
    """Tests for main Config class."""

    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        assert config.private_key == ""
        assert config.funder == ""
        assert config.log_level == "INFO"

    def test_is_configured(self):
        """Test is_configured method."""
        config = Config()
        assert config.is_configured() is False

        config.private_key = "0x" + "a" * 64
        config.funder = "0x" + "b" * 40
        assert config.is_configured() is True

    def test_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "private_key": "0x" + "a" * 64,
            "funder": "0x" + "b" * 40,
            "clob": {
                "host": "https://test.api.com",
                "chain_id": 80001,
            },
            "trading": {
                "default_size": 25.0,
                "spike_threshold": 0.10,
            }
        }

        config = Config.from_dict(data)

        assert config.private_key == "0x" + "a" * 64
        assert config.funder == "0x" + "b" * 40
        assert config.clob.host == "https://test.api.com"
        assert config.clob.chain_id == 80001
        assert config.trading.default_size == 25.0
        assert config.trading.spike_threshold == 0.10

    def test_from_json(self):
        """Test loading from JSON file."""
        data = {
            "private_key": "0x" + "c" * 64,
            "funder": "0x" + "d" * 40,
            "host": "https://clob.polymarket.com",
            "chain_id": 137,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            config = Config.from_json(filepath)
            assert config.private_key == "0x" + "c" * 64
            assert config.funder == "0x" + "d" * 40
        finally:
            os.unlink(filepath)

    def test_from_json_not_found(self):
        """Test error when JSON file not found."""
        with pytest.raises(ConfigNotFoundError):
            Config.from_json("nonexistent_file.json")

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("POLY_PRIVATE_KEY", "0x" + "e" * 64)
        monkeypatch.setenv("POLY_FUNDER", "0x" + "f" * 40)
        monkeypatch.setenv("POLY_CHAIN_ID", "80001")
        monkeypatch.setenv("POLY_DEFAULT_SIZE", "50.0")

        config = Config.from_env()

        assert config.private_key == "0x" + "e" * 64
        assert config.funder == "0x" + "f" * 40
        assert config.clob.chain_id == 80001
        assert config.trading.default_size == 50.0

    def test_address_normalization(self):
        """Test that addresses are normalized to lowercase."""
        config = Config(funder="0xABCDEF1234567890" + "a" * 24)
        assert config.funder.islower()

    def test_validate_missing_private_key(self):
        """Test validation catches missing private key."""
        config = Config(funder="0x" + "a" * 40)
        errors = config.validate()
        assert any("private_key" in e for e in errors)

    def test_validate_missing_funder(self):
        """Test validation catches missing funder."""
        config = Config(private_key="0x" + "a" * 64)
        errors = config.validate()
        assert any("funder" in e for e in errors)

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = Config(
            private_key="0x" + "a" * 64,
            funder="0x" + "b" * 40
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_to_dict_excludes_private_key(self):
        """Test to_dict doesn't expose full private key."""
        config = Config(
            private_key="0x" + "a" * 64,
            funder="0x" + "b" * 40
        )
        data = config.to_dict()
        assert "private_key" not in data
        # Funder should be truncated
        assert "..." in data["funder"]

    def test_save_json(self):
        """Test saving to JSON file."""
        config = Config(
            private_key="0x" + "a" * 64,
            funder="0x" + "b" * 40
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            config.save_json(filepath)

            with open(filepath) as f:
                data = json.load(f)

            assert data["funder"] == "0x" + "b" * 40
            # Private key should NOT be included by default
            assert "private_key" not in data

        finally:
            os.unlink(filepath)

    def test_save_json_with_private_key(self):
        """Test saving JSON with private key included."""
        config = Config(
            private_key="0x" + "a" * 64,
            funder="0x" + "b" * 40
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            config.save_json(filepath, include_private_key=True)

            # Check file permissions
            mode = os.stat(filepath).st_mode & 0o777
            assert mode == 0o600

            with open(filepath) as f:
                data = json.load(f)

            assert data["private_key"] == "0x" + "a" * 64

        finally:
            os.unlink(filepath)

    def test_get_data_path(self):
        """Test get_data_path method."""
        config = Config()
        config.storage.data_dir = "my_data"

        path = config.get_data_path("test.json")
        assert path == Path("my_data/test.json")


class TestConfigLoadPrecedence:
    """Test configuration load precedence: ENV > YAML > JSON > defaults."""

    def test_env_overrides_json(self, monkeypatch):
        """Test that environment variables override JSON config."""
        # Create JSON config
        json_data = {
            "private_key": "0x" + "a" * 64,
            "funder": "0x" + "a" * 40,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            filepath = f.name

        try:
            # Set env var to different value
            monkeypatch.setenv("POLY_FUNDER", "0x" + "b" * 40)

            # load_with_env should use env value
            # Note: This requires YAML support, so we test from_dict + from_env
            config = Config.from_json(filepath)
            assert config.funder == "0x" + "a" * 40  # From JSON

            # Now load with env override
            monkeypatch.setenv("POLY_FUNDER", "0x" + "c" * 40)
            env_config = Config.from_env()
            assert env_config.funder == "0x" + "c" * 40  # From ENV

        finally:
            os.unlink(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
