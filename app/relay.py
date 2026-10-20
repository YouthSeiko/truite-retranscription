from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from transcriber import PROJECT_ROOT

RELAY_CONFIG_PATH = PROJECT_ROOT / "relay_config.json"
OFFER_PATH = PROJECT_ROOT / "offer.json"
BOUNDARY = "truite-relay-boundary"


def load_relay() -> Optional[dict]:
    try:
        data = json.loads(RELAY_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    url = str(data.get("url", "")).strip().rstrip("/")
    password = str(data.get("password", ""))
    if not url or not password:
        return None
    result = {"url": url, "password": password}
    username = str(data.get("username", "")).strip()
    if username:
        result["username"] = username
    label = str(data.get("label", "")).strip()
    if label:
        result["label"] = label
    return result


def save_relay(url: str, password: str, username: str = "", label: str = "") -> dict:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    data: dict = {"url": url, "password": password}
    username = username.strip()
    if username:
        data["username"] = username
    label = label.strip()
    if label:
        data["label"] = label
    RELAY_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def load_offer() -> Optional[dict]:
    try:
        data = json.loads(OFFER_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    url = str(data.get("url", "")).strip()
    password = str(data.get("password", ""))
    if not url or not password:
        return None
    offer = {"url": url, "password": password}
    username = str(data.get("username", "")).strip()
    if username:
        offer["username"] = username
    offer["label"] = str(data.get("label", "")).strip() or "Serveur"
    return offer


def accept_offer() -> Optional[dict]:
    offer = load_offer()
    if offer is None:
        return None
    return save_relay(
        offer["url"],
        offer["password"],
        username=offer.get("username", ""),
        label=offer.get("label", ""),
    )


def clear_relay() -> None:
    try:
        RELAY_CONFIG_PATH.unlink()
    except OSError:
        pass


def relay_active() -> bool:
    return load_relay() is not None


def error_text(exc: Exception, host: str) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace") or "{}")
            detail = str(payload.get("detail", ""))
        except Exception:
            detail = ""
        if "Session invalide" in detail or exc.code == 401:
            return "Session refusee par le serveur distant. Verifiez son mot de passe."
        return detail or f"Le serveur distant a repondu une erreur {exc.code}."
    if isinstance(exc, urllib.error.URLError):
        return (
            f"Serveur distant injoignable ({host}). "
            "Verifiez que l'application est ouverte sur ce PC et sur le meme reseau."
        )
    if isinstance(exc, TimeoutError):
        return f"Le serveur distant ({host}) ne repond pas (delai depasse)."
    return str(exc) or host


class _CountingBody:
    def __init__(self, path: Path, head: bytes, tail: bytes, on_progress: Callable[[float], None]):
        self._buffers: list = [io.BytesIO(head), path.open("rb"), io.BytesIO(tail)]
        self._index = 0
        self._total = len(head) + path.stat().st_size + len(tail)
        self._sent = 0
        self._on_progress = on_progress

    def read(self, size: int = -1) -> bytes:
        while self._index < len(self._buffers):
            chunk = self._buffers[self._index].read(size)
            if chunk:
                self._sent += len(chunk)
                try:
                    self._on_progress(min(self._sent / max(self._total, 1), 1.0))
                except Exception:
                    pass
                return chunk
            self._index += 1
        return b""

    def close(self) -> None:
        for buffer in self._buffers:
            try:
                buffer.close()
            except Exception:
                pass


class RelayClient:
    def __init__(self, config: dict) -> None:
        self.url = config["url"]
        self.password = config["password"]
        self.username = str(config.get("username", "")).strip()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    @property
    def host(self) -> str:
        return self.url.split("://", 1)[-1]

    def _open(self, request, timeout: int = 30):
        return self._opener.open(request, timeout=timeout)

    def _login(self) -> None:
        payload: dict = {"password": self.password}
        if self.username:
            payload["username"] = self.username
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/api/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self._open(request, timeout=15):
            pass

    def _request(self, request, timeout: int = 30, retry_auth: bool = True):
        try:
            return self._open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and retry_auth:
                exc.close()
                self._login()
                return self._open(request, timeout=timeout)
            raise

    def ping(self) -> None:
        self._login()
        request = urllib.request.Request(f"{self.url}/api/state")
        with self._request(request, timeout=15):
            pass

    def upload(
        self,
        path: Path,
        model: str,
        language: str,
        on_progress: Callable[[float], None],
    ) -> str:
        safe_name = path.name.replace('"', "'")
        head = b"".join(
            (
                f"--{BOUNDARY}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            ).encode("utf-8")
            for name, value in (("model", model), ("language", language))
        )
        head += (
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        tail = f"\r\n--{BOUNDARY}--\r\n".encode("utf-8")
        body = _CountingBody(path, head, tail, on_progress)
        request = urllib.request.Request(
            f"{self.url}/api/upload", data=body, method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
                "Content-Length": str(len(head) + path.stat().st_size + len(tail)),
            },
        )
        with self._request(request, timeout=600, retry_auth=False) as response:
            payload = json.loads(response.read().decode("utf-8"))
        remote_id = str(payload.get("id", ""))
        if not remote_id:
            raise RuntimeError("Le serveur distant n'a pas renvoye d'identifiant.")
        return remote_id

    def state(self) -> dict:
        request = urllib.request.Request(f"{self.url}/api/state")
        with self._request(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def download_text(self, job_id: str) -> str:
        request = urllib.request.Request(f"{self.url}/api/download/{job_id}/txt")
        with self._request(request, timeout=120) as response:
            return response.read().decode("utf-8", "replace")

    def cancel(self, job_id: str) -> None:
        try:
            request = urllib.request.Request(
                f"{self.url}/api/cancel/{job_id}", data=b"", method="POST"
            )
            with self._request(request, timeout=15):
                pass
        except Exception:
            pass
