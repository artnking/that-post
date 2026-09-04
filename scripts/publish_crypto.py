#!/usr/bin/env python3
"""AES-256-GCM lock for a published That Post index. Never print the password."""
from __future__ import annotations

import os

MAGIC = b"THATPOST1"
SALT_LEN = 16
NONCE_LEN = 12
KDF_ITERS = 210_000
KEY_LEN = 32


def encrypt_index(plain: bytes, password: str, *, iters: int = KDF_ITERS) -> bytes:
    if len(password) != 4 or not password.isdigit():
        raise ValueError("publish PIN must be exactly 4 digits")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=iters,
    ).derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(nonce, plain, None)
    return MAGIC + salt + nonce + ct


def decrypt_index(blob: bytes, password: str, *, iters: int = KDF_ITERS) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    if not blob.startswith(MAGIC):
        raise ValueError("not a That Post locked index")
    salt = blob[len(MAGIC) : len(MAGIC) + SALT_LEN]
    nonce_at = len(MAGIC) + SALT_LEN
    nonce = blob[nonce_at : nonce_at + NONCE_LEN]
    ct = blob[nonce_at + NONCE_LEN :]
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=iters,
    ).derive(password.encode("utf-8"))
    return AESGCM(key).decrypt(nonce, ct, None)
