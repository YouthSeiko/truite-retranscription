from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / ".models"

MODEL_SIZES = {
    "tiny": "tres rapide, moins precis (~75 Mo)",
    "base": "rapide (~145 Mo)",
    "small": "equilibre, recommande (~460 Mo)",
    "medium": "plus precis (~1,5 Go)",
    "large-v3": "tres precis (~3 Go)",
    "large-v3-turbo": "rapide et precis (~1,6 Go)",
}

LANGUAGES = {
    "Auto (detection)": None,
    "Francais": "fr",
    "English": "en",
    "Espanol": "es",
    "Deutsch": "de",
    "Italiano": "it",
    "Portugues": "pt",
    "Nederlands": "nl",
    "Polski": "pl",
    "Turkce": "tr",
    "Russky": "ru",
    "日本語": "ja",
    "中文": "zh",
    "한국어": "ko",
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".m4b", ".flac", ".ogg", ".opus",
    ".aac", ".wma", ".mp4", ".mkv", ".webm", ".aiff",
}


@dataclass
class Segment:
    start: float
    end: float
    text: str


def _pick_device() -> tuple[str, str]:
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def is_model_downloaded(size: str) -> bool:
    if not MODELS_DIR.exists():
        return False
    for model_bin in MODELS_DIR.rglob("model.bin"):
        if size in model_bin.parent.name:
            return True
    return False


def human_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


class Transcriber:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self._model: Optional[WhisperModel] = None
        self.device: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self, on_status: Optional[Callable[[str], None]] = None) -> None:
        if self._model is not None:
            return
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cached = is_model_downloaded(self.model_size)
        if on_status:
            if cached:
                on_status(f"Chargement du modele {self.model_size}...")
            else:
                on_status(f"Premiere utilisation : telechargement du modele {self.model_size} (une seule fois)...")
        device, compute = _pick_device()
        attempts = [(device, compute)]
        if device != "cpu":
            attempts.append(("cpu", "int8"))
        last_error: Optional[Exception] = None
        for dev, comp in attempts:
            try:
                model = WhisperModel(
                    self.model_size,
                    device=dev,
                    compute_type=comp,
                    download_root=str(MODELS_DIR),
                    local_files_only=cached,
                )
            except Exception as err:
                last_error = err
                continue
            self._model = model
            self.device = dev
            if on_status:
                on_status(f"Modele {self.model_size} pret ({dev}).")
            return
        raise RuntimeError(
            f"Impossible de charger le modele '{self.model_size}'. "
            f"La premiere utilisation demande une connexion Internet. "
            f"Details : {last_error}"
        )

    def transcribe_file(
        self,
        path: Path,
        language: Optional[str] = None,
        on_segment: Optional[Callable[[Segment], None]] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> tuple[list[Segment], object]:
        if self._model is None:
            self.load()
        try:
            segments_iter, info = self._model.transcribe(
                str(path),
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
                condition_on_previous_text=False,
            )
        except Exception:
            segments_iter, info = self._model.transcribe(
                str(path),
                language=language,
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=False,
            )
        duration = float(getattr(info, "duration", 0) or 0)
        results: list[Segment] = []
        for seg in segments_iter:
            if should_cancel and should_cancel():
                break
            item = Segment(
                start=float(seg.start),
                end=float(seg.end),
                text=(seg.text or "").strip(),
            )
            if item.text:
                results.append(item)
            if on_segment:
                on_segment(item)
            if on_progress and duration > 0:
                on_progress(min(item.end / duration, 1.0))
        if on_progress and duration > 0:
            on_progress(1.0)
        return results, info


def _fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_vtt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    idx = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({idx}){path.suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def export_segments(
    segments: list[Segment],
    source: Path,
    out_dir: Path,
    formats: list[str],
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fmts = [f for f in formats if f in ("txt", "srt", "vtt")] or ["txt"]
    written: list[Path] = []
    text = "\n".join(seg.text for seg in segments if seg.text).strip()
    for fmt in fmts:
        path = _unique_path(out_dir / f"{source.stem}.{fmt}")
        if fmt == "txt":
            content = text
        elif fmt == "srt":
            lines: list[str] = []
            index = 1
            for seg in segments:
                if not seg.text:
                    continue
                lines += [
                    str(index),
                    f"{_fmt_srt(seg.start)} --> {_fmt_srt(seg.end)}",
                    seg.text,
                    "",
                ]
                index += 1
            content = "\n".join(lines)
        else:
            lines = ["WEBVTT", ""]
            for seg in segments:
                if not seg.text:
                    continue
                lines += [
                    f"{_fmt_vtt(seg.start)} --> {_fmt_vtt(seg.end)}",
                    seg.text,
                    "",
                ]
            content = "\n".join(lines)
        path.write_text(content + ("\n" if content else ""), encoding="utf-8")
        written.append(path)
    return written
