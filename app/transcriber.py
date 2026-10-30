from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Optional

from faster_whisper import WhisperModel

if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).resolve().parent
    if (_exe_dir / "_internal").is_dir():
        PROJECT_ROOT = _exe_dir.parent
    else:
        PROJECT_ROOT = _exe_dir
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

SAMPLE_RATE = 16000
CHUNK_SECONDS = 600
MIN_SPLIT_SECONDS = 60
MAX_SPLIT_DEPTH = 4


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


def probe_duration(path: Path) -> float:
    try:
        import av

        with av.open(str(path)) as container:
            if container.duration:
                return float(container.duration) / 1_000_000.0
            if container.streams.audio:
                stream = container.streams.audio[0]
                if stream.duration and stream.time_base:
                    return float(stream.duration * stream.time_base)
    except Exception:
        pass
    return 0.0


def _slice_to_wav(
    source: Path,
    start: float,
    length: float,
    target: Path,
    sequential: bool = False,
) -> tuple[float, int]:
    import av
    import wave

    resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    blocks: list[bytes] = []
    total = 0
    skipped = 0
    stop = start + length
    fallback = 0.0 if sequential else start
    try:
        container = av.open(str(source), options={"fflags": "+discardcorrupt"})
    except Exception:
        container = av.open(str(source))
    try:
        stream = container.streams.audio[0]
        if start > 0 and not sequential:
            warmup = max(0.0, start - 2.0)
            container.seek(int(warmup / float(stream.time_base)), stream=stream, backward=True)
        done = False
        for packet in container.demux(stream):
            if done:
                break
            if packet.dts is None:
                continue
            try:
                frames = packet.decode()
            except Exception:
                skipped += 1
                continue
            for frame in frames:
                rate = float(frame.sample_rate or SAMPLE_RATE)
                if frame.pts is not None:
                    frame_start = float(frame.pts * stream.time_base)
                else:
                    frame_start = fallback
                if rate > 0 and frame.samples:
                    fallback = frame_start + frame.samples / rate
                for converted in resampler.resample(frame):
                    data = converted.to_ndarray().reshape(-1)
                    size = int(data.shape[0])
                    if size <= 0:
                        continue
                    if frame_start + size / SAMPLE_RATE <= start:
                        continue
                    if frame_start >= stop:
                        done = True
                        break
                    if frame_start < start:
                        data = data[int(round((start - frame_start) * SAMPLE_RATE)) :]
                    room = int(round((stop - max(frame_start, start)) * SAMPLE_RATE))
                    if room <= 0:
                        done = True
                        break
                    if data.shape[0] > room:
                        data = data[:room]
                    if data.shape[0]:
                        blocks.append(data.tobytes())
                        total += int(data.shape[0])
                if done:
                    break
    finally:
        container.close()
    with wave.open(str(target), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        for item in blocks:
            out.writeframes(item)
    return total / SAMPLE_RATE, skipped


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

    def _transcribe_window(
        self,
        source: Path,
        language: Optional[str],
        on_segment: Optional[Callable[[Segment], None]],
        on_progress: Optional[Callable[[float], None]],
        should_cancel: Optional[Callable[[], bool]],
        offset: float,
        total: float,
    ) -> tuple[list[Segment], object]:
        try:
            segments_iter, info = self._model.transcribe(
                str(source),
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
                condition_on_previous_text=False,
            )
        except Exception:
            segments_iter, info = self._model.transcribe(
                str(source),
                language=language,
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=False,
            )
        results: list[Segment] = []
        for seg in segments_iter:
            if should_cancel and should_cancel():
                break
            item = Segment(
                start=offset + float(seg.start),
                end=offset + float(seg.end),
                text=(seg.text or "").strip(),
            )
            if item.text:
                results.append(item)
            if on_segment:
                on_segment(item)
            if on_progress and total > 0:
                on_progress(min(item.end / total, 1.0))
        return results, info

    def _transcribe_part(
        self,
        source: Path,
        temp_dir: Path,
        start: float,
        end: float,
        language: Optional[str],
        on_segment: Optional[Callable[[Segment], None]],
        on_progress: Optional[Callable[[float], None]],
        should_cancel: Optional[Callable[[], bool]],
        total: float,
        on_status: Optional[Callable[[str], None]],
        depth: int = 0,
    ) -> list[Segment]:
        length = end - start
        if length <= 0.5:
            return []
        chunk = temp_dir / f"passage_{int(start * 10):08d}_{int(length * 10):08d}.wav"
        last_error = "erreur inconnue"
        for sequential in (False, True):
            if should_cancel and should_cancel():
                return []
            try:
                written, skipped = _slice_to_wav(
                    source, start, length, chunk, sequential=sequential
                )
                if skipped and on_status:
                    on_status(
                        f"Passage {human_duration(start)} - {human_duration(end)} : "
                        f"{skipped} paquets audio illisibles ignores."
                    )
                if written <= 0.2:
                    raise RuntimeError("aucun echantillon audio lisible")
                part, _ = self._transcribe_window(
                    chunk, language, on_segment, on_progress, should_cancel, start, total
                )
                return part
            except Exception as exc:
                last_error = str(exc) or "erreur inconnue"
            finally:
                try:
                    chunk.unlink()
                except OSError:
                    pass
        if length > MIN_SPLIT_SECONDS and depth < MAX_SPLIT_DEPTH:
            middle = start + length / 2.0
            return self._transcribe_part(
                source, temp_dir, start, middle, language, on_segment, on_progress,
                should_cancel, total, on_status, depth + 1,
            ) + self._transcribe_part(
                source, temp_dir, middle, end, language, on_segment, on_progress,
                should_cancel, total, on_status, depth + 1,
            )
        if on_status:
            on_status(
                f"Passage {human_duration(start)} - {human_duration(end)} non transcrit : {last_error}"
            )
        return [
            Segment(
                start=start,
                end=end,
                text=(
                    f"[Partie non transcrite - {human_duration(start)} a {human_duration(end)} : "
                    "audio illisible]"
                ),
            )
        ]

    def transcribe_file(
        self,
        path: Path,
        language: Optional[str] = None,
        on_segment: Optional[Callable[[Segment], None]] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> tuple[list[Segment], object]:
        if self._model is None:
            self.load()
        duration = probe_duration(path)
        if duration <= CHUNK_SECONDS:
            try:
                results, info = self._transcribe_window(
                    path, language, on_segment, on_progress, should_cancel, 0.0, duration
                )
                if on_progress and duration > 0:
                    on_progress(1.0)
                return results, info
            except Exception:
                if on_status:
                    on_status("Fichier audio partiellement illisible : nouvelle tentative...")
                temp_dir = Path(tempfile.mkdtemp(prefix="truite_audio_"))
                chunk = temp_dir / "passage.wav"
                try:
                    written, skipped = _slice_to_wav(
                        path, 0.0, max(duration, 86400.0), chunk, sequential=True
                    )
                    if skipped and on_status:
                        on_status(f"{skipped} paquets audio illisibles ignores.")
                    if written <= 0.2:
                        raise RuntimeError("aucun echantillon audio lisible")
                    results, info = self._transcribe_window(
                        chunk, language, on_segment, on_progress, should_cancel, 0.0, written
                    )
                    if on_progress:
                        on_progress(1.0)
                    return results, SimpleNamespace(
                        duration=written, language=language, language_probability=0.0
                    )
                finally:
                    try:
                        chunk.unlink()
                    except OSError:
                        pass
                    try:
                        temp_dir.rmdir()
                    except OSError:
                        pass

        results: list[Segment] = []
        info = SimpleNamespace(duration=duration, language=language, language_probability=0.0)
        temp_dir = Path(tempfile.mkdtemp(prefix="truite_audio_"))
        start = 0.0
        try:
            while start < duration:
                if should_cancel and should_cancel():
                    break
                end = min(start + float(CHUNK_SECONDS), duration)
                if on_status:
                    on_status(
                        f"Passage {human_duration(start)} - {human_duration(end)} "
                        f"sur {human_duration(duration)}..."
                    )
                part = self._transcribe_part(
                    path, temp_dir, start, end, language, on_segment, on_progress,
                    should_cancel, duration, on_status,
                )
                results.extend(part)
                start = end
                if on_progress:
                    on_progress(min(start / duration, 1.0))
        finally:
            try:
                temp_dir.rmdir()
            except OSError:
                pass

        if on_progress:
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
