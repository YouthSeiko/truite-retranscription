from __future__ import annotations

import json
import secrets
import time
from hashlib import scrypt
from pathlib import Path
from typing import Optional

from transcriber import PROJECT_ROOT

ACCOUNTS_PATH = PROJECT_ROOT / "accounts.json"
MAX_CREDIT = 300.0
REGEN_SECONDS_PER_MINUTE = 360.0


def _load() -> dict:
    try:
        return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    ACCOUNTS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _hash(password: str, salt: bytes) -> bytes:
    return scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)


def valid_username(user: str) -> bool:
    user = user.strip()
    if not 2 <= len(user) <= 24:
        return False
    return all(c.isalnum() or c in " -_." for c in user)


def create(user: str, password: str) -> str:
    user = user.strip()
    if not valid_username(user):
        return "Pseudo invalide : 2 a 24 caracteres (lettres, chiffres, - _ .)."
    if len(password) < 8:
        return "Mot de passe : 8 caracteres minimum."
    data = _load()
    if user.lower() in {key.lower() for key in data}:
        return "Ce pseudo existe deja."
    salt = secrets.token_bytes(16)
    data[user] = {
        "salt": salt.hex(),
        "hash": _hash(password, salt).hex(),
        "credit": MAX_CREDIT,
        "updated": time.time(),
        "created": time.time(),
    }
    _save(data)
    return ""


def authenticate(user: str, password: str) -> Optional[str]:
    data = _load()
    wanted = user.strip().lower()
    for key, record in data.items():
        if key.lower() != wanted:
            continue
        try:
            digest = _hash(password, bytes.fromhex(record["salt"]))
        except Exception:
            return None
        if secrets.compare_digest(digest.hex(), record["hash"]):
            return key
        return None
    return None


def _regen(record: dict) -> float:
    now = time.time()
    elapsed = max(0.0, now - float(record.get("updated", now)))
    credit = min(
        MAX_CREDIT,
        float(record.get("credit", MAX_CREDIT)) + elapsed / REGEN_SECONDS_PER_MINUTE,
    )
    record["credit"] = credit
    record["updated"] = now
    return credit


def get_credit(user: str) -> Optional[float]:
    data = _load()
    wanted = user.strip().lower()
    for key, record in data.items():
        if key.lower() == wanted:
            return _regen(record)
    return None


def debit(user: str, minutes: float) -> None:
    if minutes <= 0:
        return
    data = _load()
    wanted = user.strip().lower()
    for key, record in data.items():
        if key.lower() == wanted:
            _regen(record)
            record["credit"] = float(record["credit"]) - minutes
            _save(data)
            return


def list_accounts() -> list[dict]:
    data = _load()
    items = []
    for key, record in sorted(data.items()):
        credit = _regen(record)
        items.append(
            {
                "user": key,
                "credit": round(credit, 1),
                "max": MAX_CREDIT,
                "created": record.get("created", 0),
            }
        )
    if data:
        _save(data)
    return items
