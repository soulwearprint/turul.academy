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


# ─── Personal links ────────────────────────────────────────────────────────
# Each postcard carries a random link token. The server stores only a hash
# of it (to look the link up) plus that person's match sealed with a key
# derived from the token. So the page behind the link can show "your giftee"
# without any admin being logged in, while the database alone still reveals
# nothing.

def new_link_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def link_id(token: str) -> str:
    return hashlib.sha256(b"santa-link-id:" + token.encode()).hexdigest()


def _link_key(token: str) -> bytes:
    return hashlib.sha256(b"santa-link-key:" + token.encode()).digest()


def seal_for_link(token: str, year: int, giver_id: int, receiver_id: int) -> str:
    return seal_receiver(_link_key(token), year, giver_id, receiver_id)


def open_for_link(token: str, year: int, giver_id: int, sealed: str) -> int:
    return open_receiver(_link_key(token), year, giver_id, sealed)


# Per-link key pair, so an admin action (draw / reshuffle) can seal "who is
# this person's Secret Santa" *to* the link without knowing the link token,
# and only a request carrying that token can open it. Used solely to address
# "new gift idea" e-mails; it is never shown to anyone.

def new_link_keypair(token: str, year: int, member_id: int) -> tuple[str, str]:
    """Return (public_b64, private_sealed_with_token)."""
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

    priv = X25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    nonce = os.urandom(12)
    sealed = AESGCM(_link_key(token)).encrypt(nonce, raw, f"link-priv:{year}:{member_id}".encode())
    return _b64(pub), _b64(nonce + sealed)


def _route_key(shared: bytes, eph_pub: bytes) -> bytes:
    return hashlib.sha256(b"santa-route:" + shared + eph_pub).digest()


def seal_to_link(public_b64: str, year: int, member_id: int, value: int) -> str:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    shared = eph.exchange(X25519PublicKey.from_public_bytes(_unb64(public_b64)))
    nonce = os.urandom(12)
    ct = AESGCM(_route_key(shared, eph_pub)).encrypt(nonce, str(value).encode(), f"route:{year}:{member_id}".encode())
    return _b64(eph_pub + nonce + ct)


def open_with_link(token: str, priv_sealed: str, year: int, member_id: int, sealed: str) -> int:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey

    pblob = _unb64(priv_sealed)
    raw = AESGCM(_link_key(token)).decrypt(pblob[:12], pblob[12:], f"link-priv:{year}:{member_id}".encode())
    blob = _unb64(sealed)
    eph_pub, nonce, ct = blob[:32], blob[32:44], blob[44:]
    shared = X25519PrivateKey.from_private_bytes(raw).exchange(X25519PublicKey.from_public_bytes(eph_pub))
    return int(AESGCM(_route_key(shared, eph_pub)).decrypt(nonce, ct, f"route:{year}:{member_id}".encode()).decode())


def server_key() -> bytes:
    """Key the server holds without any admin logged in (needed for the daily digest).

    SANTA_SERVER_KEY (env, base64 32 bytes) if set - recommended, keeps it out of
    the data folder. Otherwise generated once into data/server.key (mode 600)."""
    env = os.environ.get("SANTA_SERVER_KEY")
    if env:
        raw = base64.b64decode(env)
        if len(raw) != 32:
            raise ValueError("SANTA_SERVER_KEY must be 32 random bytes, base64-encoded.")
        return raw
    from pathlib import Path
    default_dir = Path(os.environ.get("SANTA_DB", Path(__file__).resolve().parent.parent / "data" / "santa.db")).parent
    path = Path(os.environ.get("SANTA_SERVER_KEY_FILE", default_dir / "server.key"))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(os.urandom(32))
    return path.read_bytes()
