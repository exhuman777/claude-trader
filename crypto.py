#!/usr/bin/env python3
"""
Encrypted Key Storage Module
============================
Secure private key management using PBKDF2-HMAC-SHA256 + Fernet encryption.

Security Features:
- 480,000 iterations for key derivation (OWASP 2024 recommendation)
- Unique random salt per encryption
- AES-128-CBC via Fernet (cryptography library)
- File permissions set to 0o600 (owner read/write only)

Usage:
    from crypto import KeyManager

    # Encrypt and save
    km = KeyManager()
    km.encrypt_and_save(private_key, password, "data/encrypted_key.json")

    # Load and decrypt
    private_key = km.load_and_decrypt(password, "data/encrypted_key.json")
"""

import os
import json
import base64
import secrets
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class CryptoError(Exception):
    """Base exception for crypto operations."""
    pass


class InvalidPasswordError(CryptoError):
    """Raised when password is incorrect."""
    pass


class CryptoNotAvailableError(CryptoError):
    """Raised when cryptography library is not installed."""
    pass


class KeyManager:
    """
    Manages encrypted storage of private keys.

    Uses PBKDF2-HMAC-SHA256 for key derivation and Fernet for encryption.
    Each encryption uses a unique random salt for security.

    Example:
        km = KeyManager()

        # Encrypt
        encrypted = km.encrypt(private_key, password)

        # Decrypt
        decrypted = km.decrypt(encrypted['ciphertext'], password, encrypted['salt'])

        # Or use file operations
        km.encrypt_and_save(private_key, password, "key.json")
        private_key = km.load_and_decrypt(password, "key.json")
    """

    # OWASP 2024 recommendation for PBKDF2-HMAC-SHA256
    DEFAULT_ITERATIONS = 480_000
    SALT_LENGTH = 32  # 256 bits

    def __init__(self, iterations: int = None):
        """
        Initialize KeyManager.

        Args:
            iterations: Number of PBKDF2 iterations (default: 480,000)
        """
        if not CRYPTO_AVAILABLE:
            raise CryptoNotAvailableError(
                "cryptography library not installed. "
                "Run: pip install cryptography"
            )
        self.iterations = iterations or self.DEFAULT_ITERATIONS

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: User password
            salt: Random salt bytes

        Returns:
            32-byte key suitable for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, plaintext: str, password: str) -> Dict[str, str]:
        """
        Encrypt plaintext with password.

        Args:
            plaintext: Data to encrypt (e.g., private key)
            password: Encryption password

        Returns:
            Dict with 'ciphertext', 'salt', 'iterations'
        """
        if not plaintext:
            raise CryptoError("Cannot encrypt empty plaintext")
        if not password:
            raise CryptoError("Password required for encryption")

        # Generate random salt
        salt = secrets.token_bytes(self.SALT_LENGTH)

        # Derive key and encrypt
        key = self._derive_key(password, salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(plaintext.encode())

        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'salt': base64.b64encode(salt).decode(),
            'iterations': self.iterations,
            'version': 1,  # For future format changes
        }

    def decrypt(self, ciphertext: str, password: str, salt: str,
                iterations: int = None) -> str:
        """
        Decrypt ciphertext with password.

        Args:
            ciphertext: Base64-encoded encrypted data
            password: Decryption password
            salt: Base64-encoded salt
            iterations: PBKDF2 iterations (uses stored value if None)

        Returns:
            Decrypted plaintext

        Raises:
            InvalidPasswordError: If password is incorrect
        """
        if not password:
            raise CryptoError("Password required for decryption")

        # Decode from base64
        salt_bytes = base64.b64decode(salt)
        ciphertext_bytes = base64.b64decode(ciphertext)

        # Use provided iterations or default
        iters = iterations or self.iterations

        # Derive key and decrypt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=iters,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        try:
            fernet = Fernet(key)
            plaintext = fernet.decrypt(ciphertext_bytes)
            return plaintext.decode()
        except InvalidToken:
            raise InvalidPasswordError("Invalid password or corrupted data")

    def encrypt_and_save(self, plaintext: str, password: str,
                         filepath: str) -> None:
        """
        Encrypt data and save to JSON file with restricted permissions.

        Args:
            plaintext: Data to encrypt
            password: Encryption password
            filepath: Output file path
        """
        encrypted = self.encrypt(plaintext, password)

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with restricted permissions (owner read/write only)
        with open(path, 'w') as f:
            json.dump(encrypted, f, indent=2)

        # Set file permissions to 0o600
        os.chmod(path, 0o600)

    def load_and_decrypt(self, password: str, filepath: str) -> str:
        """
        Load encrypted data from file and decrypt.

        Args:
            password: Decryption password
            filepath: Input file path

        Returns:
            Decrypted plaintext
        """
        path = Path(filepath)
        if not path.exists():
            raise CryptoError(f"File not found: {filepath}")

        with open(path, 'r') as f:
            data = json.load(f)

        return self.decrypt(
            ciphertext=data['ciphertext'],
            password=password,
            salt=data['salt'],
            iterations=data.get('iterations', self.DEFAULT_ITERATIONS)
        )

    def change_password(self, old_password: str, new_password: str,
                        filepath: str) -> None:
        """
        Re-encrypt file with new password.

        Args:
            old_password: Current password
            new_password: New password
            filepath: Encrypted file path
        """
        # Decrypt with old password
        plaintext = self.load_and_decrypt(old_password, filepath)

        # Re-encrypt with new password
        self.encrypt_and_save(plaintext, new_password, filepath)


def verify_private_key(key: str) -> bool:
    """
    Validate Ethereum private key format.

    Args:
        key: Private key string

    Returns:
        True if valid format, False otherwise
    """
    if not key:
        return False

    # Remove 0x prefix if present
    if key.startswith('0x') or key.startswith('0X'):
        key = key[2:]

    # Must be 64 hex characters
    if len(key) != 64:
        return False

    try:
        int(key, 16)
        return True
    except ValueError:
        return False


def generate_random_private_key() -> str:
    """
    Generate random private key for testing.

    WARNING: For testing only! Use proper key generation for real funds.

    Returns:
        Random 32-byte hex string with 0x prefix
    """
    return '0x' + secrets.token_hex(32)


def hash_password(password: str) -> str:
    """
    Create password hash for verification (not encryption).

    Args:
        password: Password to hash

    Returns:
        SHA-256 hash hex string
    """
    return hashlib.sha256(password.encode()).hexdigest()


# Convenience functions for non-OOP usage
def encrypt_key(private_key: str, password: str, filepath: str) -> None:
    """Encrypt and save private key to file."""
    km = KeyManager()
    km.encrypt_and_save(private_key, password, filepath)


def decrypt_key(password: str, filepath: str) -> str:
    """Load and decrypt private key from file."""
    km = KeyManager()
    return km.load_and_decrypt(password, filepath)


if __name__ == "__main__":
    # Demo
    print("KeyManager Demo")
    print("=" * 50)

    if not CRYPTO_AVAILABLE:
        print("Install cryptography: pip install cryptography")
        exit(1)

    # Generate test key
    test_key = generate_random_private_key()
    test_password = "demo_password_123"
    test_file = "/tmp/test_encrypted_key.json"

    print(f"Original key: {test_key[:10]}...{test_key[-6:]}")

    # Encrypt
    km = KeyManager()
    km.encrypt_and_save(test_key, test_password, test_file)
    print(f"Encrypted and saved to: {test_file}")

    # Decrypt
    recovered = km.load_and_decrypt(test_password, test_file)
    print(f"Recovered key: {recovered[:10]}...{recovered[-6:]}")

    # Verify
    assert test_key == recovered, "Keys don't match!"
    print("\n✓ Encryption/decryption successful!")

    # Cleanup
    os.remove(test_file)
