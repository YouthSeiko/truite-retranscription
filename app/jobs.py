from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from transcriber import PROJECT_ROOT, Transcriber, export_segments, human_duration

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
