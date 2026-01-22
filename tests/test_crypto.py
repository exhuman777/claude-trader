#!/usr/bin/env python3
"""
Tests for crypto.py - Encrypted Key Storage
"""

import os
import json
import tempfile
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto import (
    KeyManager,
    verify_private_key,
    generate_random_private_key,
    encrypt_key,
    decrypt_key,
    CryptoError,
    InvalidPasswordError,
    CRYPTO_AVAILABLE,
)


# Skip all tests if cryptography not installed
pytestmark = pytest.mark.skipif(
    not CRYPTO_AVAILABLE,
    reason="cryptography library not installed"
)


class TestKeyManager:
    """Tests for KeyManager class."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test basic encrypt/decrypt cycle."""
        km = KeyManager()
        plaintext = "test_secret_data_12345"
        password = "test_password"

        encrypted = km.encrypt(plaintext, password)

        assert "ciphertext" in encrypted
        assert "salt" in encrypted
        assert "iterations" in encrypted

        decrypted = km.decrypt(
            encrypted["ciphertext"],
            password,
            encrypted["salt"],
            encrypted["iterations"]
        )

        assert decrypted == plaintext

    def test_wrong_password_raises_error(self):
        """Test that wrong password raises InvalidPasswordError."""
        km = KeyManager()
        plaintext = "secret"
        password = "correct_password"
        wrong_password = "wrong_password"

        encrypted = km.encrypt(plaintext, password)

        with pytest.raises(InvalidPasswordError):
            km.decrypt(
                encrypted["ciphertext"],
                wrong_password,
                encrypted["salt"]
            )

    def test_empty_plaintext_raises_error(self):
        """Test that empty plaintext raises error."""
        km = KeyManager()

        with pytest.raises(CryptoError):
            km.encrypt("", "password")

    def test_empty_password_raises_error(self):
        """Test that empty password raises error."""
        km = KeyManager()

        with pytest.raises(CryptoError):
            km.encrypt("plaintext", "")

    def test_file_operations(self):
        """Test encrypt_and_save / load_and_decrypt."""
        km = KeyManager()
        plaintext = "0x" + "a" * 64  # Test private key
        password = "secure_password_123"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            # Save
            km.encrypt_and_save(plaintext, password, filepath)

            # Verify file exists and has restricted permissions
            assert Path(filepath).exists()
            mode = os.stat(filepath).st_mode & 0o777
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

            # Verify JSON structure
            with open(filepath) as f:
                data = json.load(f)
            assert "ciphertext" in data
            assert "salt" in data

            # Load and decrypt
            recovered = km.load_and_decrypt(password, filepath)
            assert recovered == plaintext

        finally:
            os.unlink(filepath)

    def test_change_password(self):
        """Test password change functionality."""
        km = KeyManager()
        plaintext = "original_secret"
        old_password = "old_pass"
        new_password = "new_pass"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            # Save with old password
            km.encrypt_and_save(plaintext, old_password, filepath)

            # Change password
            km.change_password(old_password, new_password, filepath)

            # Verify old password no longer works
            with pytest.raises(InvalidPasswordError):
                km.load_and_decrypt(old_password, filepath)

            # Verify new password works
            recovered = km.load_and_decrypt(new_password, filepath)
            assert recovered == plaintext

        finally:
            os.unlink(filepath)

    def test_custom_iterations(self):
        """Test with custom iteration count."""
        km = KeyManager(iterations=10000)  # Lower for test speed
        plaintext = "test_data"
        password = "password"

        encrypted = km.encrypt(plaintext, password)
        assert encrypted["iterations"] == 10000

        decrypted = km.decrypt(
            encrypted["ciphertext"],
            password,
            encrypted["salt"],
            encrypted["iterations"]
        )
        assert decrypted == plaintext


class TestVerifyPrivateKey:
    """Tests for verify_private_key function."""

    def test_valid_key_with_prefix(self):
        """Test valid key with 0x prefix."""
        key = "0x" + "a" * 64
        assert verify_private_key(key) is True

    def test_valid_key_without_prefix(self):
        """Test valid key without prefix."""
        key = "a" * 64
        assert verify_private_key(key) is True

    def test_valid_key_uppercase(self):
        """Test valid key with uppercase."""
        key = "0x" + "A" * 64
        assert verify_private_key(key) is True

    def test_invalid_key_too_short(self):
        """Test invalid key that's too short."""
        key = "0x" + "a" * 63
        assert verify_private_key(key) is False

    def test_invalid_key_too_long(self):
        """Test invalid key that's too long."""
        key = "0x" + "a" * 65
        assert verify_private_key(key) is False

    def test_invalid_key_non_hex(self):
        """Test invalid key with non-hex characters."""
        key = "0x" + "g" * 64
        assert verify_private_key(key) is False

    def test_empty_key(self):
        """Test empty key."""
        assert verify_private_key("") is False
        assert verify_private_key(None) is False


class TestGenerateRandomPrivateKey:
    """Tests for generate_random_private_key function."""

    def test_generates_valid_key(self):
        """Test that generated key is valid."""
        key = generate_random_private_key()
        assert verify_private_key(key) is True

    def test_generates_unique_keys(self):
        """Test that each call generates unique key."""
        keys = [generate_random_private_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_encrypt_decrypt_key(self):
        """Test encrypt_key and decrypt_key functions."""
        key = "0x" + "b" * 64
        password = "my_password"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            encrypt_key(key, password, filepath)
            recovered = decrypt_key(password, filepath)
            assert recovered == key
        finally:
            os.unlink(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
