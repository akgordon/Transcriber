"""Local-only Whisper transcription (no network after models are on disk)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

MODEL_NAMES = ("tiny", "base", "small", "medium", "large-v3", "turbo")
DEFAULT_MODEL = "small"
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".webm")


class ModelNotFoundError(FileNotFoundError):
    """Raised when a local model directory is missing."""


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    source: Path
    language: str
    language_probability: float
    segments: list[Segment]
    txt_path: Path
    srt_path: Path
    device: str
    compute_type: str


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def models_dir() -> Path:
    return project_root() / "models"


def model_path(name: str) -> Path:
    return models_dir() / name


def is_model_ready(name: str) -> bool:
    path = model_path(name)
    return (
        path.is_dir()
        and (path / "model.bin").is_file()
        and (path / "config.json").is_file()
    )


def missing_model_message(name: str) -> str:
    return (
        f"Model '{name}' is not installed at {model_path(name)}.\n"
        f"Download it once (internet required) with:\n"
        f"  python -m transcriber download {name}"
    )


def collect_audio_files(path: Path) -> list[Path]:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if path.is_file():
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{path.suffix}'. "
                f"Use one of: {', '.join(AUDIO_EXTENSIONS)}"
            )
        return [path]
    files = sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not files:
        raise FileNotFoundError(
            f"No audio files found in {path} "
            f"(looked for {', '.join(AUDIO_EXTENSIONS)})"
        )
    return files


def resolve_device(prefer: str = "auto") -> tuple[str, str]:
    """Return (device, compute_type)."""
    if prefer == "cpu":
        return "cpu", "int8"
    if prefer == "cuda":
        return "cuda", "float16"

    try:
        import ctranslate2

        if ctranslate2.get_supported_compute_types("cuda"):
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def download_whisper_model(name: str) -> Path:
    if name not in MODEL_NAMES:
        raise ValueError(
            f"Unknown model '{name}'. Choose one of: {', '.join(MODEL_NAMES)}"
        )
    dest = model_path(name)
    dest.mkdir(parents=True, exist_ok=True)
    from faster_whisper.utils import download_model

    download_model(name, output_dir=str(dest))
    return dest


class LocalTranscriber:
    """Loads a on-disk Whisper model and transcribes audio files."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "auto"):
        if model_name not in MODEL_NAMES:
            raise ValueError(
                f"Unknown model '{model_name}'. Choose one of: {', '.join(MODEL_NAMES)}"
            )
        self.model_name = model_name
        self.device_prefer = device
        self.device_used = ""
        self.compute_type_used = ""
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        if not is_model_ready(self.model_name):
            raise ModelNotFoundError(missing_model_message(self.model_name))

        from faster_whisper import WhisperModel

        path = str(model_path(self.model_name))
        device, compute_type = resolve_device(self.device_prefer)
        try:
            self._model = WhisperModel(
                path,
                device=device,
                compute_type=compute_type,
                local_files_only=True,
            )
            self.device_used = device
            self.compute_type_used = compute_type
        except Exception:
            if device != "cpu":
                self._model = WhisperModel(
                    path,
                    device="cpu",
                    compute_type="int8",
                    local_files_only=True,
                )
                self.device_used = "cpu"
                self.compute_type_used = "int8"
            else:
                raise

    def transcribe_file(
        self,
        audio_path: Path,
        language: str = "auto",
        on_segment: Optional[Callable[[Segment], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> TranscriptResult:
        from transcriber.output import write_srt, write_txt

        self.load()
        audio_path = audio_path.expanduser().resolve()
        lang = None if language in (None, "", "auto") else language

        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=lang,
            beam_size=5,
            vad_filter=True,
        )

        collected: list[Segment] = []
        for raw in segments_iter:
            if should_cancel and should_cancel():
                break
            segment = Segment(
                start=float(raw.start),
                end=float(raw.end),
                text=(raw.text or "").strip(),
            )
            if not segment.text:
                continue
            collected.append(segment)
            if on_segment:
                on_segment(segment)

        txt_path = write_txt(audio_path.with_suffix(".txt"), collected)
        srt_path = write_srt(audio_path.with_suffix(".srt"), collected)
        return TranscriptResult(
            source=audio_path,
            language=getattr(info, "language", language or "unknown"),
            language_probability=float(getattr(info, "language_probability", 0.0) or 0.0),
            segments=collected,
            txt_path=txt_path,
            srt_path=srt_path,
            device=self.device_used,
            compute_type=self.compute_type_used,
        )

    def transcribe_paths(
        self,
        paths: Iterable[Path],
        language: str = "auto",
        on_segment: Optional[Callable[[Path, Segment], None]] = None,
        on_file_start: Optional[Callable[[Path, int, int], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> Iterator[TranscriptResult]:
        files = list(paths)
        total = len(files)
        for index, audio_path in enumerate(files, start=1):
            if should_cancel and should_cancel():
                break
            if on_file_start:
                on_file_start(audio_path, index, total)

            def _on_segment(segment: Segment, current=audio_path) -> None:
                if on_segment:
                    on_segment(current, segment)

            yield self.transcribe_file(
                audio_path,
                language=language,
                on_segment=_on_segment if on_segment else None,
                should_cancel=should_cancel,
            )
