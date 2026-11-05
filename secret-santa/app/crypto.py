"""Envelope encryption for the pairings.

One random 256-bit *master key* encrypts every pairing row (AES-256-GCM).
The master key is never stored in clear: each admin holds their own copy,
wrapped with a key derived from their password (scrypt). Without an admin
password, the database file alone does not reveal who gives to whom.
"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SCRYPT = dict(n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


class WrongPassword(Exception):
    pass


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode())


def new_master_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _kek(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)


def wrap_key(master: bytes, password: str) -> tuple[str, str]:
    """Return (salt_b64, wrapped_b64)."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    ct = AESGCM(_kek(password, salt)).encrypt(nonce, master, b"santa-master-key")
    return _b64(salt), _b64(nonce + ct)


def unwrap_key(salt_b64: str, wrapped_b64: str, password: str) -> bytes:
    blob = _unb64(wrapped_b64)
    try:
        return AESGCM(_kek(password, _unb64(salt_b64))).decrypt(blob[:12], blob[12:], b"santa-master-key")
    except InvalidTag as exc:
        raise WrongPassword() from exc


def _aad(year: int, giver_id: int) -> bytes:
    # Binds the ciphertext to its row, so rows cannot be swapped around in the DB.
    return f"pairing:{year}:{giver_id}".encode()


def seal_receiver(master: bytes, year: int, giver_id: int, receiver_id: int) -> str:
    nonce = os.urandom(12)
    return _b64(nonce + AESGCM(master).encrypt(nonce, str(receiver_id).encode(), _aad(year, giver_id)))


def open_receiver(master: bytes, year: int, giver_id: int, sealed: str) -> int:
    blob = _unb64(sealed)
    return int(AESGCM(master).decrypt(blob[:12], blob[12:], _aad(year, giver_id)).decode())


def wrap_with_kek(master: bytes, kek: bytes) -> str:
    """Wrap the master key with a raw 256-bit key (used for SANTA_SERVER_KEY)."""
    nonce = os.urandom(12)
    return _b64(nonce + AESGCM(kek).encrypt(nonce, master, b"santa-server-key"))


def unwrap_with_kek(wrapped_b64: str, kek: bytes) -> bytes:
    blob = _unb64(wrapped_b64)
    try:
        return AESGCM(kek).decrypt(blob[:12], blob[12:], b"santa-server-key")
    except InvalidTag as exc:
        raise WrongPassword("SANTA_SERVER_KEY does not match this database") from exc
