"""
Accura – Cryptographic Utilities
Fernet-based encryption for storing user API keys at rest.
"""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet

from config import settings


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = settings.get("security.encryption_key") or os.getenv("ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return the base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext string."""
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
