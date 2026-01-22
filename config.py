#!/usr/bin/env python3
"""
Configuration Management Module
===============================
Flexible config with precedence: ENV > YAML > JSON > defaults

Usage:
    from config import Config

    # Load with auto-detection
    config = Config.load()  # Tries config.yaml, then .env, then data/.trading_config.json

    # Explicit loading
    config = Config.from_env()
    config = Config.from_yaml("config.yaml")
    config = Config.load_with_env("config.yaml")  # YAML with ENV overrides
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


# Environment variable prefix
ENV_PREFIX = "POLY_"


def get_env(name: str, default: str = "") -> str:
    """Get environment variable with prefix."""
    return os.environ.get(f"{ENV_PREFIX}{name}", os.environ.get(name, default))


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    val = get_env(name, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def get_env_int(name: str, default: int = 0) -> int:
    """Get integer environment variable."""
    val = get_env(name, "")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def get_env_float(name: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    val = get_env(name, "")
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigNotFoundError(ConfigError):
    """Raised when config file is not found."""
    pass


@dataclass
class ClobConfig:
    """CLOB (Central Limit Order Book) configuration."""
    host: str = "https://clob.polymarket.com"
    chain_id: int = 137  # Polygon mainnet
    signature_type: int = 2  # Gnosis Safe

    def is_valid(self) -> bool:
        """Validate CLOB configuration."""
        return bool(self.host and self.host.startswith("http"))


@dataclass
class TradingConfig:
    """Trading defaults and limits."""
    default_size: float = 10.0
    default_slippage: float = 0.02  # 2%
    max_position_size: float = 1000.0
    max_daily_loss: float = 100.0
    cooldown_seconds: int = 5
    min_liquidity: float = 100.0  # Minimum orderbook depth

    # Spike detection settings
    spike_threshold: float = 0.05  # 5% price movement
    spike_lookback: int = 60  # seconds
    take_profit: float = 0.10  # 10%
    stop_loss: float = 0.05  # 5%


@dataclass
class StorageConfig:
    """Data storage configuration."""
    data_dir: str = "data"
    cache_enabled: bool = True
    cache_expiry_hours: int = 24
    store_trade_history: bool = True
    store_patterns: bool = True
    encrypted_keys: bool = True


@dataclass
class Config:
    """
    Main configuration class for Claude Polymarket Trading.

    Supports loading from:
    - Environment variables (POLY_* prefix)
    - YAML files (config.yaml)
    - JSON files (data/.trading_config.json)

    Precedence: ENV > YAML > JSON > defaults
    """

    # Core credentials
    private_key: str = ""
    funder: str = ""  # Wallet address

    # API endpoints
    clob: ClobConfig = field(default_factory=ClobConfig)

    # Trading settings
    trading: TradingConfig = field(default_factory=TradingConfig)

    # Storage settings
    storage: StorageConfig = field(default_factory=StorageConfig)

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    def __post_init__(self):
        """Normalize addresses."""
        if self.funder and not self.funder.startswith("0x"):
            self.funder = "0x" + self.funder
        if self.funder:
            self.funder = self.funder.lower()

    @classmethod
    def load(cls, config_path: str = None) -> "Config":
        """
        Auto-detect and load configuration.

        Tries in order:
        1. Provided config_path
        2. config.yaml in current directory
        3. Environment variables
        4. data/.trading_config.json

        Returns:
            Config instance
        """
        # Load .env if available
        if DOTENV_AVAILABLE:
            load_dotenv()

        # Try explicit path first
        if config_path:
            path = Path(config_path)
            if path.suffix in ('.yaml', '.yml'):
                return cls.load_with_env(config_path)
            elif path.suffix == '.json':
                return cls.from_json(config_path)

        # Try config.yaml
        if Path("config.yaml").exists():
            return cls.load_with_env("config.yaml")

        # Try config.yml
        if Path("config.yml").exists():
            return cls.load_with_env("config.yml")

        # Try environment
        config = cls.from_env()
        if config.is_configured():
            return config

        # Try JSON
        json_paths = [
            "data/.trading_config.json",
            ".trading_config.json",
        ]
        for json_path in json_paths:
            if Path(json_path).exists():
                return cls.from_json(json_path)

        # Return defaults
        return cls()

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Supported variables (with POLY_ prefix or without):
            PRIVATE_KEY: Ethereum private key
            FUNDER / SAFE_ADDRESS: Wallet address
            CLOB_HOST: CLOB API host
            CHAIN_ID: Chain ID (default: 137)
            DEFAULT_SIZE: Default order size
            MAX_POSITION: Max position size
            MAX_DAILY_LOSS: Maximum daily loss limit
            SPIKE_THRESHOLD: Spike detection threshold
            DATA_DIR: Data directory path
            LOG_LEVEL: Logging level
        """
        config = cls()

        # Credentials
        config.private_key = get_env("PRIVATE_KEY", "")
        config.funder = get_env("FUNDER", get_env("SAFE_ADDRESS", ""))

        # CLOB settings
        clob_host = get_env("CLOB_HOST", "")
        if clob_host:
            config.clob.host = clob_host
        config.clob.chain_id = get_env_int("CHAIN_ID", 137)

        # Trading settings
        default_size = get_env_float("DEFAULT_SIZE", 0)
        if default_size:
            config.trading.default_size = default_size

        max_position = get_env_float("MAX_POSITION", 0)
        if max_position:
            config.trading.max_position_size = max_position

        max_loss = get_env_float("MAX_DAILY_LOSS", 0)
        if max_loss:
            config.trading.max_daily_loss = max_loss

        spike_threshold = get_env_float("SPIKE_THRESHOLD", 0)
        if spike_threshold:
            config.trading.spike_threshold = spike_threshold

        # Storage
        data_dir = get_env("DATA_DIR", "")
        if data_dir:
            config.storage.data_dir = data_dir

        config.storage.encrypted_keys = get_env_bool("ENCRYPTED_KEYS", True)

        # Logging
        log_level = get_env("LOG_LEVEL", "")
        if log_level:
            config.log_level = log_level.upper()

        config.verbose = get_env_bool("VERBOSE", False)

        return config

    @classmethod
    def from_yaml(cls, filepath: str) -> "Config":
        """Load configuration from YAML file."""
        if not YAML_AVAILABLE:
            raise ConfigError("PyYAML not installed. Run: pip install pyyaml")

        path = Path(filepath)
        if not path.exists():
            raise ConfigNotFoundError(f"Config file not found: {filepath}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_json(cls, filepath: str) -> "Config":
        """Load configuration from JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise ConfigNotFoundError(f"Config file not found: {filepath}")

        with open(path, 'r') as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        # Core credentials
        config.private_key = data.get("private_key", "")
        config.funder = data.get("funder", data.get("safe_address", ""))

        # CLOB config
        if "clob" in data:
            clob = data["clob"]
            config.clob = ClobConfig(
                host=clob.get("host", config.clob.host),
                chain_id=clob.get("chain_id", config.clob.chain_id),
                signature_type=clob.get("signature_type", config.clob.signature_type),
            )
        # Legacy flat format
        elif "host" in data:
            config.clob.host = data["host"]
            config.clob.chain_id = data.get("chain_id", 137)
            config.clob.signature_type = data.get("signature_type", 2)

        # Trading config
        if "trading" in data:
            trading = data["trading"]
            config.trading = TradingConfig(
                default_size=trading.get("default_size", config.trading.default_size),
                default_slippage=trading.get("default_slippage", config.trading.default_slippage),
                max_position_size=trading.get("max_position_size", config.trading.max_position_size),
                max_daily_loss=trading.get("max_daily_loss", config.trading.max_daily_loss),
                cooldown_seconds=trading.get("cooldown_seconds", config.trading.cooldown_seconds),
                min_liquidity=trading.get("min_liquidity", config.trading.min_liquidity),
                spike_threshold=trading.get("spike_threshold", config.trading.spike_threshold),
                spike_lookback=trading.get("spike_lookback", config.trading.spike_lookback),
                take_profit=trading.get("take_profit", config.trading.take_profit),
                stop_loss=trading.get("stop_loss", config.trading.stop_loss),
            )

        # Storage config
        if "storage" in data:
            storage = data["storage"]
            config.storage = StorageConfig(
                data_dir=storage.get("data_dir", config.storage.data_dir),
                cache_enabled=storage.get("cache_enabled", config.storage.cache_enabled),
                cache_expiry_hours=storage.get("cache_expiry_hours", config.storage.cache_expiry_hours),
                store_trade_history=storage.get("store_trade_history", config.storage.store_trade_history),
                store_patterns=storage.get("store_patterns", config.storage.store_patterns),
                encrypted_keys=storage.get("encrypted_keys", config.storage.encrypted_keys),
            )

        # Logging
        config.log_level = data.get("log_level", config.log_level)
        config.verbose = data.get("verbose", config.verbose)

        return config

    @classmethod
    def load_with_env(cls, filepath: str) -> "Config":
        """
        Load from file with environment variable overrides.

        Precedence: ENV > File > defaults
        """
        # Load .env if available
        if DOTENV_AVAILABLE:
            load_dotenv()

        # Start with file config
        path = Path(filepath)
        if path.suffix in ('.yaml', '.yml'):
            config = cls.from_yaml(filepath)
        elif path.suffix == '.json':
            config = cls.from_json(filepath)
        else:
            config = cls()

        # Override with environment variables
        private_key = get_env("PRIVATE_KEY", "")
        if private_key:
            config.private_key = private_key

        funder = get_env("FUNDER", get_env("SAFE_ADDRESS", ""))
        if funder:
            config.funder = funder

        clob_host = get_env("CLOB_HOST", "")
        if clob_host:
            config.clob.host = clob_host

        chain_id = get_env_int("CHAIN_ID", 0)
        if chain_id:
            config.clob.chain_id = chain_id

        data_dir = get_env("DATA_DIR", "")
        if data_dir:
            config.storage.data_dir = data_dir

        log_level = get_env("LOG_LEVEL", "")
        if log_level:
            config.log_level = log_level.upper()

        return config

    def is_configured(self) -> bool:
        """Check if essential config is present."""
        return bool(self.private_key and self.funder)

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.private_key:
            errors.append("private_key is required")

        if not self.funder:
            errors.append("funder (wallet address) is required")

        if not self.clob.is_valid():
            errors.append("clob.host is invalid")

        if self.trading.max_daily_loss < 0:
            errors.append("max_daily_loss must be positive")

        if self.trading.spike_threshold <= 0 or self.trading.spike_threshold >= 1:
            errors.append("spike_threshold must be between 0 and 1")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excludes sensitive data)."""
        return {
            "funder": self.funder[:10] + "..." if self.funder else "",
            "clob": asdict(self.clob),
            "trading": asdict(self.trading),
            "storage": asdict(self.storage),
            "log_level": self.log_level,
        }

    def save_yaml(self, filepath: str) -> None:
        """Save configuration to YAML file (excludes private_key)."""
        if not YAML_AVAILABLE:
            raise ConfigError("PyYAML not installed")

        data = {
            "funder": self.funder,
            "clob": asdict(self.clob),
            "trading": asdict(self.trading),
            "storage": asdict(self.storage),
            "log_level": self.log_level,
        }

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)

    def save_json(self, filepath: str, include_private_key: bool = False) -> None:
        """Save configuration to JSON file."""
        data = {
            "funder": self.funder,
            "host": self.clob.host,
            "chain_id": self.clob.chain_id,
            "signature_type": self.clob.signature_type,
        }

        if include_private_key and self.private_key:
            data["private_key"] = self.private_key

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        # Restrict permissions if contains private key
        if include_private_key:
            os.chmod(path, 0o600)

    def get_data_path(self, filename: str) -> Path:
        """Get path within data directory."""
        return Path(self.storage.data_dir) / filename

    def __repr__(self) -> str:
        """String representation."""
        configured = "configured" if self.is_configured() else "not configured"
        return f"Config({configured}, funder={self.funder[:10] if self.funder else 'none'}...)"


# Convenience function
def load_config(path: str = None) -> Config:
    """Load config with auto-detection."""
    return Config.load(path)


if __name__ == "__main__":
    # Demo
    print("Config Demo")
    print("=" * 50)

    # Try loading
    config = Config.load()
    print(f"Loaded config: {config}")
    print(f"Is configured: {config.is_configured()}")

    # Show settings
    print(f"\nTrading settings:")
    print(f"  Default size: {config.trading.default_size}")
    print(f"  Spike threshold: {config.trading.spike_threshold * 100}%")
    print(f"  Take profit: {config.trading.take_profit * 100}%")
    print(f"  Stop loss: {config.trading.stop_loss * 100}%")

    # Validate
    errors = config.validate()
    if errors:
        print(f"\nValidation errors: {errors}")
    else:
        print("\n✓ Configuration valid!")
