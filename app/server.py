from __future__ import annotations

import asyncio
import json
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from hashlib import scrypt
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from jobs import DONE, Job, JobQueue, get_queue
from transcriber import AUDIO_EXTENSIONS, LANGUAGES, MODEL_SIZES, PROJECT_ROOT

COOKIE = "truite_session"
SESSION_LIFETIME = 7 * 24 * 3600
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
REMOTE_CONFIG_PATH = PROJECT_ROOT / "remote_config.json"
UPLOAD_DIR = PROJECT_ROOT / "remote_uploads"
DEFAULT_PORT = 8722

_sessions: dict[str, float] = {}
_login_fails: dict[str, list[float]] = {}


def _load_remote_config() -> dict:
    try:
        return json.loads(REMOTE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_remote_config(data: dict) -> None:
    try:
        REMOTE_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def password_defined() -> bool:
    return bool(_load_remote_config().get("password"))


def set_password(password: str) -> None:
    salt = secrets.token_bytes(16)
    digest = scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    config = _load_remote_config()
    config["password"] = f"{salt.hex()}${digest.hex()}"
    _save_remote_config(config)


def verify_password(password: str) -> bool:
    stored = _load_remote_config().get("password")
    if not stored or "$" not in stored:
        return False
    salt_hex, digest_hex = stored.split("$", 1)
    try:
        digest = scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def _session_valid(token: str | None) -> bool:
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None or expiry < time.time():
        _sessions.pop(token, None)
        return False
    return True


def _login_allowed(ip: str) -> bool:
    now = time.time()
    recent = [t for t in _login_fails.get(ip, []) if now - t < 300]
    _login_fails[ip] = recent
    return len(recent) < 8


def _record_login_fail(ip: str) -> None:
    _login_fails.setdefault(ip, []).append(time.time())


def get_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def get_tailscale_ip() -> str | None:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            first = result.stdout.strip().splitlines()[0].strip()
            if first.startswith("100."):
                return first
    except Exception:
        pass
    return None


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def open_firewall(port: int) -> None:
    script = Path(tempfile.gettempdir()) / "truite-parefeu.ps1"
    script.write_text(
        "try { netsh advfirewall firewall delete rule name=\"Truite Retranscription\" | Out-Null } catch {}\n"
        f"netsh advfirewall firewall add rule name=\"Truite Retranscription\" dir=in action=allow protocol=TCP localport={port}\n"
        "Write-Host \"Pare-feu : port {port} autorise.\"\n"
        "Start-Sleep -Seconds 3\n",
        encoding="utf-8",
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-StartHidden", "-File", str(script)]
    )


def _resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", "")
        if bundle:
            return Path(bundle) / "app"
    return PROJECT_ROOT / "app"


class RemoteServer:
    def __init__(self, queue: JobQueue | None = None, port: int = DEFAULT_PORT) -> None:
        self.queue = queue or get_queue()
        self.port = port
        self.running = False
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clients: set[WebSocket] = set()
        self._subscribed = False
        self._html = ""
        self._app = self._build_app()

    def start(self) -> None:
        if self.running:
            return
        if not port_is_free(self.port):
            raise RuntimeError(f"Le port {self.port} est deja utilise.")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        web_path = _resource_dir() / "web" / "index.html"
        self._html = web_path.read_text(encoding="utf-8") if web_path.exists() else "<h1>Page introuvable</h1>"
        if not self._subscribed:
            self.queue.subscribe(self._on_job_change)
            self._subscribed = True
        config = uvicorn.Config(
            self._app, host="0.0.0.0", port=self.port, log_level="warning", access_log=False
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="remote-server")
        self._thread.start()
        self.running = True

    def stop(self) -> None:
        if not self.running:
            return
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.running = False
        self._server = None
        self._loop = None
        self._clients.clear()

    def urls(self) -> dict:
        lan = get_lan_ip()
        info = {"lan": f"http://{lan}:{self.port}", "tailscale": None}
        tailscale = get_tailscale_ip()
        if tailscale:
            info["tailscale"] = f"http://{tailscale}:{self.port}"
        return info

    def _state_payload(self) -> dict:
        jobs = sorted(self.queue.jobs.values(), key=lambda j: j.created, reverse=True)[:50]
        return {"type": "state", "jobs": [job.public() for job in jobs]}

    def _on_job_change(self, job: Job) -> None:
        if job.origin == "remote" and not job.active:
            for path in job.files:
                try:
                    if path.parent.name == "remote_uploads":
                        path.unlink()
                except OSError:
                    pass
        loop = self._loop
        if loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(), loop)
        except RuntimeError:
            pass

    async def _broadcast(self) -> None:
        payload = self._state_payload()
        for client in list(self._clients):
            try:
                await client.send_json(payload)
            except Exception:
                self._clients.discard(client)

    def _build_app(self) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self._loop = asyncio.get_running_loop()
            yield
            self._loop = None

        app = FastAPI(title="Truite Retranscription", lifespan=lifespan, docs_url=None, redoc_url=None)

        public_paths = {"/api/info", "/api/login"}

        @app.middleware("http")
        async def auth_guard(request: Request, call_next):
            path = request.url.path
            if path.startswith("/api/") and path not in public_paths:
                if not _session_valid(request.cookies.get(COOKIE)):
                    return JSONResponse({"detail": "Session invalide"}, status_code=401)
            return await call_next(request)

        async def require_session(request: Request) -> str:
            token = request.cookies.get(COOKIE)
            if not _session_valid(token):
                raise HTTPException(status_code=401, detail="Session invalide")
            return token or ""

        @app.get("/", response_class=HTMLResponse)
        async def index() -> HTMLResponse:
            return HTMLResponse(self._html)

        @app.get("/logo.png", response_model=None)
        async def logo():
            path = _resource_dir() / "logo.png"
            if path.exists():
                return FileResponse(path, media_type="image/png")
            return Response(status_code=404)

        @app.get("/api/info")
        async def info() -> dict:
            return {
                "ready": password_defined(),
                "app": "Truite Retranscription",
                "models": MODEL_SIZES,
                "languages": list(LANGUAGES.keys()),
            }

        @app.post("/api/login")
        async def login(request: Request, response: Response) -> dict:
            ip = request.client.host if request.client else "?"
            if not _login_allowed(ip):
                raise HTTPException(status_code=429, detail="Trop de tentatives. Reessayez dans 5 minutes.")
            body = await request.json()
            password = str(body.get("password", ""))
            if not password_defined() or not verify_password(password):
                _record_login_fail(ip)
                raise HTTPException(status_code=401, detail="Mot de passe incorrect")
            token = secrets.token_urlsafe(32)
            _sessions[token] = time.time() + SESSION_LIFETIME
            response.set_cookie(
                COOKIE, token, max_age=SESSION_LIFETIME, httponly=True, samesite="lax"
            )
            return {"ok": True}

        @app.post("/api/logout")
        async def logout(request: Request, response: Response, token: str = Depends(require_session)) -> dict:
            _sessions.pop(token, None)
            response.delete_cookie(COOKIE)
            return {"ok": True}

        @app.get("/api/state")
        async def state(token: str = Depends(require_session)) -> dict:
            return self._state_payload()

        @app.post("/api/upload")
        async def upload(
            request: Request,
            file: UploadFile = File(...),
            model: str = Form(""),
            language: str = Form(""),
            token: str = Depends(require_session),
        ) -> dict:
            raw_name = Path(file.filename or "audio.mp3").name
            safe = "".join(c if c.isalnum() or c in " -_()." else "_" for c in raw_name).strip() or "audio.mp3"
            if Path(safe).suffix.lower() not in AUDIO_EXTENSIONS:
                raise HTTPException(status_code=415, detail="Format audio non pris en charge")
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOAD_DIR / f"{secrets.token_hex(4)}_{safe}"
            size = 0
            with dest.open("wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        out.close()
                        dest.unlink(missing_ok=True)
                        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 500 Mo)")
                    out.write(chunk)
            config = _load_app_config()
            model_name = model if model in MODEL_SIZES else config.get("model", "small")
            valid_codes = {value for value in LANGUAGES.values() if value}
            if language in LANGUAGES:
                lang_key = LANGUAGES[language]
            elif language in valid_codes:
                lang_key = language
            else:
                lang_key = None
            job = self.queue.submit([dest], model_name, lang_key, True, origin="remote")
            return job.public()

        @app.get("/api/download/{job_id}/{fmt}")
        async def download(job_id: str, fmt: str, token: str = Depends(require_session)) -> Response:
            job = self.queue.jobs.get(job_id)
            if job is None or job.status != DONE:
                raise HTTPException(status_code=409, detail="Resultat non disponible")
            if fmt not in ("txt", "srt", "vtt"):
                raise HTTPException(status_code=400, detail="Format inconnu")
            stored = job.out_files.get(fmt)
            if stored and Path(stored).exists():
                return FileResponse(stored, filename=Path(stored).name)
            if fmt == "txt" and job.text:
                name = Path(job.filename).stem
                return Response(
                    job.text,
                    media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}.txt"'},
                )
            raise HTTPException(status_code=404, detail="Fichier de sortie introuvable")

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket) -> None:
            token = ws.cookies.get(COOKIE)
            if not _session_valid(token):
                await ws.close(code=4401)
                return
            await ws.accept()
            self._clients.add(ws)
            try:
                await ws.send_json(self._state_payload())
                while True:
                    await ws.receive_text()
            except Exception:
                pass
            finally:
                self._clients.discard(ws)

        return app


def _load_app_config() -> dict:
    try:
        return json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
