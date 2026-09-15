"""Tests that do not require downloaded Whisper weights."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from transcriber.engine import Segment, collect_audio_files
from transcriber.output import format_srt_timestamp, write_srt, write_txt


class FormatSrtTimestampTests(unittest.TestCase):
    def test_zero(self) -> None:
        self.assertEqual(format_srt_timestamp(0), "00:00:00,000")

    def test_hours_minutes_seconds(self) -> None:
        self.assertEqual(format_srt_timestamp(3661.5), "01:01:01,500")

    def test_negative_clamps_to_zero(self) -> None:
        self.assertEqual(format_srt_timestamp(-1), "00:00:00,000")


class WriteTranscriptTests(unittest.TestCase):
    def test_txt_and_srt(self) -> None:
        segments = [
            Segment(start=0.0, end=1.5, text="Hello"),
            Segment(start=1.5, end=3.0, text="world"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            txt = write_txt(Path(tmp) / "out.txt", segments)
            srt = write_srt(Path(tmp) / "out.srt", segments)
            self.assertEqual(txt.read_text(encoding="utf-8"), "Hello\nworld\n")
            self.assertIn("00:00:00,000 --> 00:00:01,500", srt.read_text(encoding="utf-8"))
            self.assertIn("Hello", srt.read_text(encoding="utf-8"))


class CollectAudioFilesTests(unittest.TestCase):
    def test_missing_path(self) -> None:
        with self.assertRaises(FileNotFoundError):
            collect_audio_files(Path("this-file-does-not-exist.mp3"))

    def test_folder_finds_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "track.mp3").write_bytes(b"")
            (folder / "notes.txt").write_text("skip", encoding="utf-8")
            files = collect_audio_files(folder)
            self.assertEqual([p.name for p in files], ["track.mp3"])


if __name__ == "__main__":
    unittest.main()
