"""Write plain-text and SubRip (.srt) transcripts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from transcriber.engine import Segment


def format_srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")


def write_txt(path: Path, segments: Iterable[Segment]) -> Path:
    path = Path(path)
    text = "\n".join(seg.text for seg in segments if seg.text)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return path


def write_srt(path: Path, segments: Iterable[Segment]) -> Path:
    path = Path(path)
    blocks: list[str] = []
    for index, seg in enumerate(segments, start=1):
        if not seg.text:
            continue
        blocks.append(
            f"{index}\n"
            f"{format_srt_timestamp(seg.start)} --> {format_srt_timestamp(seg.end)}\n"
            f"{seg.text}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
