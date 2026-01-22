#!/usr/bin/env python3
"""
Claude Polymarket Trading Cockpit - Setup Wizard
=================================================
Guides new users through complete setup:
1. API credentials (Polymarket) with ENCRYPTED storage
2. Data storage configuration
3. Optional API connections
4. Trading settings
5. Verification

Security Features:
- Private keys encrypted with PBKDF2 + Fernet
- File permissions set to 0o600
- Password never stored
"""
import os
import sys
import json
import getpass
from pathlib import Path

# Colors for terminal
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

def c(text, color):
    return f"{color}{text}{Colors.END}"

def banner():
    print()
    print(c("┌─────────────────────────────────────────────────────────────┐", Colors.CYAN))
    print(c("│", Colors.CYAN) + c("     CLAUDE POLYMARKET TRADING COCKPIT                       ", Colors.BOLD) + c("│", Colors.CYAN))
    print(c("│", Colors.CYAN) + c("     Setup Wizard v2.0                                       ", Colors.DIM) + c("│", Colors.CYAN))
    print(c("└─────────────────────────────────────────────────────────────┘", Colors.CYAN))
    print()

def section(title):
    print()
    print(c(f"━━━ {title} ", Colors.CYAN) + c("━" * (50 - len(title)), Colors.DIM))
    print()

def success(msg):
    print(c("  ✓ ", Colors.GREEN) + msg)

def warning(msg):
    print(c("  ⚠ ", Colors.YELLOW) + msg)

def error(msg):
    print(c("  ✗ ", Colors.RED) + msg)

def info(msg):
    print(c("  → ", Colors.DIM) + msg)

def ask(prompt, default=None, secret=False):
    if secret:
        return getpass.getpass(f"  {prompt}: ")
    if default:
        result = input(f"  {prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"  {prompt}: ").strip()

def ask_yes_no(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    result = input(f"  {prompt} {suffix}: ").strip().lower()
    if not result:
        return default
    return result in ['y', 'yes']

def check_dependencies():
    """Check required Python packages"""
    section("Checking Dependencies")

    required = [
        ('py_clob_client', 'py-clob-client'),
        ('cryptography', 'cryptography'),
    ]
    optional = [
        ('yaml', 'pyyaml'),
        ('dotenv', 'python-dotenv'),
    ]
    missing = []
    missing_optional = []

    for module, pkg in required:
        try:
            __import__(module)
            success(f"{pkg} installed")
        except ImportError:
            missing.append(pkg)
            error(f"{pkg} not found")

    for module, pkg in optional:
        try:
            __import__(module)
            success(f"{pkg} installed (optional)")
        except ImportError:
            missing_optional.append(pkg)
            info(f"{pkg} not found (optional)")

    if missing:
        print()
        if ask_yes_no("Install missing packages?"):
            import subprocess
            for pkg in missing:
                info(f"Installing {pkg}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', pkg],
                             capture_output=True)
                success(f"{pkg} installed")

    if missing_optional:
        print()
        if ask_yes_no("Install optional packages for enhanced features?", False):
            import subprocess
            for pkg in missing_optional:
                info(f"Installing {pkg}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', pkg],
                             capture_output=True)
                success(f"{pkg} installed")

    return len(missing) == 0

def setup_polymarket_api():
    """Configure Polymarket API credentials with optional encryption"""
    section("Polymarket API Configuration")

    print("  To trade on Polymarket, you need API credentials from your wallet.")
    print()
    print(c("  How to get credentials:", Colors.BOLD))
    print("  1. Go to polymarket.com and log in")
    print("  2. Go to Settings → Export Private Key")
    print("  3. Copy your wallet address from your profile")
    print()

    config = {
        "host": "https://clob.polymarket.com",
        "chain_id": 137,
        "signature_type": 2,
        "private_key": "",
        "funder": ""
    }

    # Check if encryption is available
    try:
        from crypto import KeyManager, verify_private_key
        crypto_available = True
    except ImportError:
        crypto_available = False

    use_encryption = False
    if crypto_available:
        print(c("  🔐 Encryption Available!", Colors.GREEN))
        print("  Your private key can be encrypted with a password.")
        print("  You'll need to enter the password each time you start Claude Code.")
        print()
        use_encryption = ask_yes_no("Enable encrypted key storage? (Recommended)", True)
    else:
        print(c("  ⚠ Encryption not available (cryptography library missing)", Colors.YELLOW))
        print("  Private key will be stored in plain text.")
        print()

    private_key = ask("Private Key (64 hex chars)", secret=True)
    funder = ask("Wallet Address (0x...)")

    # Validate private key format
    if crypto_available:
        if not verify_private_key(private_key):
            warning("Private key format may be invalid (should be 64 hex characters)")
            if not ask_yes_no("Continue anyway?", False):
                return setup_polymarket_api()  # Retry

    config["private_key"] = private_key
    config["funder"] = funder
    config["encrypted"] = use_encryption

    if use_encryption:
        print()
        print(c("  Set encryption password:", Colors.BOLD))
        while True:
            password = ask("Password", secret=True)
            password_confirm = ask("Confirm password", secret=True)
            if password == password_confirm:
                config["_password"] = password  # Temporary, not saved
                break
            error("Passwords don't match. Try again.")

    return config

def setup_trading_settings():
    """Configure trading defaults and risk limits"""
    section("Trading Settings")

    print("  Configure default trading parameters and safety limits.")
    print()

    settings = {
        "default_size": 10.0,
        "max_position_size": 1000.0,
        "max_daily_loss": 100.0,
        "spike_threshold": 0.05,
        "take_profit": 0.10,
        "stop_loss": 0.05,
    }

    print(c("  Position Sizing:", Colors.BOLD))
    settings["default_size"] = float(ask("Default order size (shares)", "10"))
    settings["max_position_size"] = float(ask("Maximum position size", "1000"))

    print()
    print(c("  Risk Management:", Colors.BOLD))
    settings["max_daily_loss"] = float(ask("Maximum daily loss ($)", "100"))

    print()
    print(c("  Spike Detection (for automated alerts):", Colors.BOLD))
    threshold_pct = float(ask("Spike threshold (%)", "5"))
    settings["spike_threshold"] = threshold_pct / 100

    print()
    print(c("  Take Profit / Stop Loss:", Colors.BOLD))
    tp_pct = float(ask("Take profit (%)", "10"))
    sl_pct = float(ask("Stop loss (%)", "5"))
    settings["take_profit"] = tp_pct / 100
    settings["stop_loss"] = sl_pct / 100

    return settings

def setup_data_storage():
    """Configure data storage options"""
    section("Data Storage Configuration")

    print("  This cockpit stores data locally for fast access:")
    print()
    print(c("  What gets stored:", Colors.BOLD))
    print("  • Market database (1,330+ markets indexed)")
    print("  • Trading history and patterns")
    print("  • API response cache")
    print("  • Your preferences and strategies")
    print()
    print(c("  Storage location:", Colors.DIM))
    print("  ./data/           - Configuration and cache")
    print("  ./data/markets.db - SQLite market database")
    print()

    storage_config = {
        "data_dir": "data",
        "cache_enabled": True,
        "cache_expiry_hours": 24,
        "store_trade_history": True,
        "store_patterns": True,
        "encrypted_keys": True,
    }

    if ask_yes_no("Enable local caching for faster lookups?", True):
        storage_config["cache_enabled"] = True
        storage_config["cache_expiry_hours"] = int(ask("Cache expiry (hours)", "24"))

    if ask_yes_no("Store trading history for pattern learning?", True):
        storage_config["store_trade_history"] = True

    return storage_config

def setup_additional_apis():
    """Configure additional API connections"""
    section("Additional API Connections (Optional)")

    print("  Connect additional APIs for enhanced research:")
    print()

    apis = {
        "polymarket": {"enabled": True, "configured": True},
    }

    available_apis = [
        ("news_api", "News API", "Real-time news for market research"),
        ("twitter_api", "Twitter/X API", "Social sentiment tracking"),
        ("coingecko", "CoinGecko", "Crypto price data"),
    ]

    for api_id, name, desc in available_apis:
        print(f"  {c(name, Colors.BOLD)}: {desc}")
        if ask_yes_no(f"  Configure {name}?", False):
            apis[api_id] = {
                "enabled": True,
                "api_key": ask(f"  {name} API Key", secret=True)
            }
            success(f"{name} configured")
        else:
            apis[api_id] = {"enabled": False}
        print()

    return apis

def save_configuration(poly_config, trading_config, storage_config, api_config):
    """Save all configuration with optional encryption"""
    section("Saving Configuration")

    data_dir = Path(storage_config.get("data_dir", "data"))
    data_dir.mkdir(exist_ok=True)

    # Handle encryption
    use_encryption = poly_config.get("encrypted", False)
    password = poly_config.pop("_password", None)

    if use_encryption and password:
        try:
            from crypto import KeyManager
            km = KeyManager()

            # Save encrypted private key
            km.encrypt_and_save(
                poly_config["private_key"],
                password,
                str(data_dir / "encrypted_key.json")
            )
            success("Private key encrypted and saved")

            # Save config without private key
            safe_config = {
                "host": poly_config["host"],
                "chain_id": poly_config["chain_id"],
                "signature_type": poly_config["signature_type"],
                "funder": poly_config["funder"],
                "encrypted": True,
            }
            with open(data_dir / ".trading_config.json", 'w') as f:
                json.dump(safe_config, f, indent=2)
            success("Trading config saved (key encrypted separately)")

        except Exception as e:
            error(f"Encryption failed: {e}")
            warning("Falling back to plain storage")
            use_encryption = False

    if not use_encryption:
        # Save plain config (not recommended)
        poly_config.pop("encrypted", None)
        config_file = data_dir / ".trading_config.json"
        with open(config_file, 'w') as f:
            json.dump(poly_config, f, indent=2)
        os.chmod(config_file, 0o600)
        warning("Private key saved (plain text, file restricted to owner)")

    # Trading settings
    with open(data_dir / ".trading_settings.json", 'w') as f:
        json.dump(trading_config, f, indent=2)
    success("Trading settings saved")

    # Storage config
    with open(data_dir / ".storage_config.json", 'w') as f:
        json.dump(storage_config, f, indent=2)
    success("Storage settings saved")

    # API config (encrypt API keys if possible)
    api_file = data_dir / ".api_connections.json"
    with open(api_file, 'w') as f:
        json.dump(api_config, f, indent=2)
    os.chmod(api_file, 0o600)
    success("API connections saved")

    # Create/update .gitignore
    gitignore_entries = [
        "data/.trading_config.json",
        "data/encrypted_key.json",
        "data/.api_connections.json",
        "data/.trading_settings.json",
        "__pycache__/",
        "*.pyc",
    ]
    gitignore = Path(".gitignore")
    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text().strip().split('\n'))

    new_entries = [e for e in gitignore_entries if e not in existing]
    if new_entries:
        with open(gitignore, 'a') as f:
            f.write('\n' + '\n'.join(new_entries) + '\n')
        success(".gitignore updated (credentials protected)")

def verify_setup(poly_config):
    """Verify the setup works"""
    section("Verifying Setup")

    info("Testing Polymarket connection...")

    try:
        # Temporarily save config for testing
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Create test config
        test_config = {
            "host": poly_config["host"],
            "chain_id": poly_config["chain_id"],
            "signature_type": poly_config["signature_type"],
            "funder": poly_config["funder"],
            "private_key": poly_config["private_key"],
        }

        config_file = data_dir / ".trading_config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)

        # Test connection
        from polymarket_api import get_balances
        balance = get_balances()

        if balance:
            success("Polymarket connection successful!")
            info(f"Balance: {balance}")
            return True
        else:
            warning("Connected but couldn't fetch balance")
            return True

    except Exception as e:
        error(f"Connection failed: {e}")
        return False

def show_next_steps(encrypted=False):
    """Show what to do next"""
    section("Setup Complete!")

    print(c("  You're ready to trade! Here's what to do next:", Colors.GREEN))
    print()

    if encrypted:
        print(c("  🔐 Your private key is encrypted.", Colors.CYAN))
        print("  You'll be prompted for your password when trading.")
        print()

    print("  1. Start Claude Code in this directory:")
    print(c("     $ claude", Colors.CYAN))
    print()
    print("  2. Try these commands:")
    print(c('     "search trump markets"', Colors.DIM) + " - Find markets")
    print(c('     "show me elon tweet markets"', Colors.DIM) + " - Load an event")
    print(c('     "buy 10 at 35c"', Colors.DIM) + " - Place an order")
    print()
    print("  3. Try the examples:")
    print(c("     python examples/quickstart.py", Colors.DIM))
    print(c("     python examples/basic_trading.py", Colors.DIM))
    print(c("     python examples/spike_detector.py", Colors.DIM))
    print()
    print("  4. Read the documentation:")
    print(c("     docs/METHODOLOGY.md", Colors.DIM) + " - Trading methodology")
    print(c("     docs/ARCHITECTURE.md", Colors.DIM) + " - System architecture")
    print(c("     TRADING_MEMORY.md", Colors.DIM) + " - Pattern learning")
    print()
    print(c("  Happy trading!", Colors.GREEN))
    print()

def main():
    banner()

    print("  Welcome! This wizard will help you set up your trading cockpit.")
    print()
    print(c("  Features:", Colors.BOLD))
    print("  • Encrypted private key storage (recommended)")
    print("  • Configurable risk limits")
    print("  • Spike detection for automated alerts")
    print("  • Pattern learning for Claude Code")
    print()

    if not ask_yes_no("Ready to begin?"):
        print("\n  Setup cancelled. Run again when ready.\n")
        return

    # Step 1: Dependencies
    check_dependencies()

    # Step 2: Polymarket API
    poly_config = setup_polymarket_api()

    # Step 3: Trading Settings
    trading_config = setup_trading_settings()

    # Step 4: Data Storage
    storage_config = setup_data_storage()

    # Step 5: Additional APIs
    api_config = setup_additional_apis()

    # Step 6: Verify
    if verify_setup(poly_config):
        save_configuration(poly_config, trading_config, storage_config, api_config)
        show_next_steps(encrypted=poly_config.get("encrypted", False))
    else:
        print()
        warning("Setup incomplete. Please check your credentials and try again.")
        if ask_yes_no("Save configuration anyway?", False):
            save_configuration(poly_config, trading_config, storage_config, api_config)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Setup cancelled.\n")
