from __future__ import annotations

import os
import queue
import socket
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

import relay
from transcriber import PROJECT_ROOT, Transcriber, export_segments, human_duration


def _get_lan_ip():
    try:
        from server import get_lan_ip

        return get_lan_ip()
    except Exception:
        return None


def _get_tailscale_ip():
    try:
        from server import get_tailscale_ip

        return get_tailscale_ip()
    except Exception:
        return None
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False
        if host in ("127.0.0.1", "localhost", "::1", "[::1]"):
            return True
        local_ips = set()
        for getter in (_get_lan_ip, _get_tailscale_ip):
            try:
                ip = getter()
                if ip:
                    local_ips.add(str(ip).strip().lower())
            except Exception:
                continue
        if host in local_ips:
            return True
        try:
            resolved = socket.gethostbyname(host).lower()
            if resolved in local_ips or resolved in ("127.0.0.1", "::1"):
                return True
        except Exception:
            pass
    except Exception:
        pass
    return False


def _should_use_relay() -> bool:
    cfg = relay.load_relay()
    if cfg is None:
        return False
    url = str(cfg.get("url", ""))
    if _relay_is_local(url):
        try:
            relay.clear_relay()
        except Exception:
            pass
        return False
    return True

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
ERROR = "error"
CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    filename: str
    files: list[Path]
    model: str
    language: Optional[str]
    auto_save: bool
    origin: str
    status: str = QUEUED
    progress: float = 0.0
    text: str = ""
    error: str = ""
    out_files: dict[str, str] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    cancel_requested: bool = False
    owner: str = ""
    duration: float = 0.0

    @property
    def active(self) -> bool:
        return self.status in (QUEUED, RUNNING)

    def public(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "model": self.model,
            "origin": self.origin,
            "status": self.status,
            "progress": round(self.progress, 3),
            "text": self.text,
            "error": self.error,
            "count": len(self.files),
            "formats": sorted(self.out_files.keys()),
            "duration": round(self.duration, 1),
        }


class JobQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.events: queue.Queue = queue.Queue()
        self.listeners: list[Callable[[Job], None]] = []
        self._pending: list[Job] = []
        self._cond = threading.Condition()
        self._running_job: Optional[Job] = None
        self.transcriber: Optional[Transcriber] = None
        self.active_model: Optional[str] = None
        self._started = False
        self._thread = threading.Thread(target=self._loop, daemon=True, name="job-worker")
        self._last_progress_notify = 0.0

    def start(self) -> None:
        if not self._started:
            self._started = True
            self._thread.start()

    def submit(
        self,
        files: list[Path],
        model: str,
        language: Optional[str],
        auto_save: bool,
        origin: str = "local",
        owner: str = "",
    ) -> Job:
        files = [Path(f) for f in files]
        name = files[0].name if len(files) == 1 else f"{len(files)} fichiers"
        job = Job(
            id=uuid.uuid4().hex[:12],
            filename=name,
            files=files,
            model=model,
            language=language,
            auto_save=auto_save,
            origin=origin,
            owner=owner,
        )
        self.jobs[job.id] = job
        self._trim()
        with self._cond:
            self._pending.append(job)
            self._cond.notify()
        self._notify(job)
        return job

    def cancel(self, job_id: Optional[str] = None) -> None:
        running: Optional[Job] = None
        with self._cond:
            if job_id is None:
                for job in [j for j in self._pending if j.status == QUEUED]:
                    job.cancel_requested = True
                    job.status = CANCELLED
                    self._pending.remove(job)
                    self._notify(job)
                running = self._running_job
            else:
                job = self.jobs.get(job_id)
                if job and job.active:
                    if job.status == QUEUED and job in self._pending:
                        job.status = CANCELLED
                        self._pending.remove(job)
                        self._notify(job)
                    else:
                        job.cancel_requested = True
                        self._notify(job)
        if running is not None:
            running.cancel_requested = True
            self._notify(running)

    def subscribe(self, callback: Callable[[Job], None]) -> None:
        self.listeners.append(callback)

    def _notify(self, job: Job) -> None:
        if job.origin == "local":
            self.events.put(("job", job))
        for callback in list(self.listeners):
            try:
                callback(job)
            except Exception:
                pass

    def _emit(self, kind: str, payload, job: Job) -> None:
        if job.origin == "local":
            self.events.put((kind, payload))

    def _trim(self, limit: int = 60) -> None:
        if len(self.jobs) <= limit:
            return
        finished = [j for j in self.jobs.values() if not j.active]
        for job in finished[: len(self.jobs) - limit]:
            del self.jobs[job.id]

    def _loop(self) -> None:
        while True:
            with self._cond:
                while not self._pending:
                    self._cond.wait()
                job = self._pending.pop(0)
            if job.status == CANCELLED:
                continue
            self._running_job = job
            try:
                self._run(job)
            except Exception:
                job.status = ERROR
                job.error = traceback.format_exc()
                self._emit("error", job.error, job)
            finally:
                self._running_job = None
                self._notify(job)
                self._emit("finished", None, job)

    def _run(self, job: Job) -> None:
        if _should_use_relay():
            self._run_relay(job)
            return

        job.status = RUNNING
        self._notify(job)
        self._emit("status", f"Preparation ({job.filename})...", job)

        if self.transcriber is None or self.active_model != job.model:
            self._emit("status", f"Chargement du modele {job.model}...", job)
            self.transcriber = Transcriber(job.model)
            self.active_model = job.model
        self.transcriber.load(on_status=lambda msg: self._emit("status", msg, job))

        total = len(job.files)
        texts: list[str] = []
        for index, path in enumerate(job.files, 1):
            if job.cancel_requested:
                job.status = CANCELLED
                self._emit("log", "Transcription annulee.", job)
                return
            self._emit("status", f"Fichier {index}/{total} : {path.name}", job)
            self._emit("progress", (index - 1) / total, job)

            def on_progress(value: float, i: int = index) -> None:
                job.progress = (i - 1 + value) / total
                self._emit("progress", job.progress, job)
                now = time.time()
                if now - self._last_progress_notify >= 0.25:
                    self._last_progress_notify = now
                    self._notify(job)

            segments, info = self.transcriber.transcribe_file(
                path,
                language=job.language,
                on_progress=on_progress,
                should_cancel=lambda: job.cancel_requested,
            )
            text = "\n".join(seg.text for seg in segments if seg.text).strip()
            body = text if text else "(aucune parole detectee)"
            texts.append(f"===== {path.name} =====\n\n{body}")
            job.progress = index / total
            self._emit("progress", index / total, job)

            if job.auto_save:
                out_dir = self._out_dir(path)
                formats = ["txt", "srt", "vtt"] if job.origin == "remote" else ["txt"]
                written = export_segments(segments, path, out_dir, formats)
                for item in written:
                    job.out_files[item.suffix.lstrip(".").lower()] = str(item)
                    self._emit("log", f"Sauvegarde : {item}", job)

            duration = float(getattr(info, "duration", 0) or 0)
            job.duration += duration
            self._emit("log", f"Termine : {path.name} ({human_duration(duration)})", job)

        if job.cancel_requested:
            job.status = CANCELLED
            self._emit("status", "Annule", job)
            return
        job.text = "\n\n".join(texts)
        job.status = DONE
        job.progress = 1.0
        self._emit("result", job.text, job)
        self._emit("status", "Termine", job)
        self._emit("log", "Transcription terminee avec succes.", job)

    def _run_relay(self, job: Job) -> None:
        config = relay.load_relay()
        if config is None:
            raise RuntimeError("Relais non configure.")
        client = relay.RelayClient(config)
        host = client.host
        job.status = RUNNING
        self._notify(job)
        try:
            self._emit("status", f"Connexion au serveur {host}...", job)
            client.ping()
            total = len(job.files)
            texts: list[str] = []
            for index, path in enumerate(job.files, 1):
                if job.cancel_requested:
                    job.status = CANCELLED
                    self._emit("status", "Annule", job)
                    return
                self._emit("status", f"Envoi de {path.name} vers {host}...", job)
                self._emit("progress", (index - 1) / total, job)

                def on_upload(frac: float, i: int = index) -> None:
                    job.progress = (i - 1 + frac * 0.1) / total
                    self._emit("progress", job.progress, job)
                    self._throttle_notify(job)

                remote_id = client.upload(path, job.model, job.language or "", on_upload)
                body = self._follow_remote(job, client, remote_id, index, total)
                if body is None:
                    job.status = CANCELLED
                    return
                texts.append(f"===== {path.name} =====\n\n{body}")
                if job.auto_save:
                    out_dir = self._out_dir(path)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    target = self._unique(out_dir / f"{path.stem}.txt")
                    target.write_text(body + ("\n" if body else ""), encoding="utf-8")
                    job.out_files["txt"] = str(target)
                    self._emit("log", f"Sauvegarde : {target}", job)
                self._emit("progress", index / total, job)
                self._emit("log", f"Transcription terminee sur {host} : {path.name}", job)
            if job.cancel_requested:
                job.status = CANCELLED
                return
            job.text = "\n\n".join(texts)
            job.status = DONE
            job.progress = 1.0
            self._emit("result", job.text, job)
            self._emit("status", "Termine", job)
            self._emit("log", f"Transcription terminee via {host}.", job)
        except Exception as exc:
            job.status = ERROR
            job.error = relay.error_text(exc, host)
            self._emit("error", job.error, job)

    def _follow_remote(
        self, job: Job, client: "relay.RelayClient", remote_id: str, index: int, total: int
    ) -> Optional[str]:
        last_status = ""
        while True:
            if job.cancel_requested:
                client.cancel(remote_id)
                job.status = CANCELLED
                self._emit("status", "Annule (le serveur distant arrete la transcription).", job)
                return None
            state = client.state()
            remote = next(
                (item for item in state.get("jobs", []) if item.get("id") == remote_id),
                None,
            )
            if remote is None:
                raise RuntimeError("Le serveur distant n'a plus ce travail en memoire.")
            status = remote.get("status")
            frac = float(remote.get("progress") or 0.0)
            job.progress = (index - 1 + 0.1 + 0.9 * frac) / total
            self._emit("progress", job.progress, job)
            self._throttle_notify(job)
            message = f"Transcription sur le serveur... {int(frac * 100)} %"
            if status == RUNNING and message != last_status:
                last_status = message
                self._emit("status", message, job)
            if status == DONE:
                return self._relabel(client.download_text(remote_id))
            if status == ERROR:
                raise RuntimeError(remote.get("error") or "La transcription distant a echoue.")
            if status == CANCELLED:
                job.status = CANCELLED
                self._emit("status", "Annule", job)
                return None
            time.sleep(1.5)

    @staticmethod
    def _relabel(raw: str) -> str:
        body = raw
        if body.startswith("====="):
            _, _, rest = body.partition("\n")
            body = rest.lstrip("\n")
        return body.strip()

    def _throttle_notify(self, job: Job) -> None:
        now = time.time()
        if now - self._last_progress_notify >= 0.25:
            self._last_progress_notify = now
            self._notify(job)

    @staticmethod
    def _unique(target: Path) -> Path:
        if not target.exists():
            return target
        stem, suffix = target.stem, target.suffix
        for number in range(1, 1000):
            candidate = target.with_name(f"{stem} ({number}){suffix}")
            if not candidate.exists():
                return candidate
        return target

    @staticmethod
    def _out_dir(path: Path) -> Path:
        if path.parent.name == "remote_uploads":
            out = PROJECT_ROOT / "transcriptions" / "remote"
        else:
            out = path.parent / "transcriptions"
        out.mkdir(parents=True, exist_ok=True)
        return out


_queue: Optional[JobQueue] = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
        _queue.start()
    return _queue
