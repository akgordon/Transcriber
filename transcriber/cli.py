"""Command-line interface for the offline transcriber."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from transcriber import __version__
from transcriber.engine import (
    DEFAULT_MODEL,
    MODEL_NAMES,
    ModelNotFoundError,
    collect_audio_files,
    download_whisper_model,
    is_model_ready,
)


def _download_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m transcriber download",
        description="Download a Whisper model into the local models/ folder (internet required once).",
    )
    parser.add_argument(
        "model",
        nargs="?",
        default=DEFAULT_MODEL,
        choices=MODEL_NAMES,
        help=f"Model size to download (default: {DEFAULT_MODEL})",
    )
    return parser


def _main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m transcriber",
        description="Transcribe audio to text locally with faster-whisper. Runs fully offline after models are downloaded.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Audio file or folder of audio files (non-recursive)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the desktop window",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=MODEL_NAMES,
        help=f"Local model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--language",
        default="auto",
        help="Language code (e.g. en) or 'auto' (default: auto)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "cpu", "cuda"),
        help="Inference device (default: auto)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"transcriber {__version__}",
    )
    return parser


def _run_download(argv: list[str]) -> int:
    args = _download_parser().parse_args(argv)
    print(f"Downloading '{args.model}' into models/{args.model} ...")
    dest = download_whisper_model(args.model)
    print(f"Saved model to {dest}")
    print("You can now transcribe offline.")
    return 0


def _run_transcribe(path: str, model: str, language: str, device: str) -> int:
    from transcriber.engine import LocalTranscriber

    if not is_model_ready(model):
        print(f"Model '{model}' is not installed at models/{model}.", file=sys.stderr)
        print(f"Download it once (internet required) with:", file=sys.stderr)
        print(f"  python -m transcriber download {model}", file=sys.stderr)
        return 1

    try:
        files = collect_audio_files(Path(path))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = LocalTranscriber(model_name=model, device=device)
    print(f"Loading model '{model}' ...")
    try:
        engine.load()
    except ModelNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Using {engine.device_used} ({engine.compute_type_used})")
    errors = 0
    for index, audio in enumerate(files, start=1):
        print(f"\n[{index}/{len(files)}] {audio}")
        try:
            result = engine.transcribe_file(
                audio,
                language=language,
                on_segment=lambda seg: print(
                    f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}"
                ),
            )
        except Exception as exc:
            print(f"Failed: {exc}", file=sys.stderr)
            errors += 1
            continue
        print(
            f"Detected language: {result.language} "
            f"({result.language_probability:.0%})"
        )
        print(f"Wrote {result.txt_path}")
        print(f"Wrote {result.srt_path}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "download":
        return _run_download(argv[1:])

    parser = _main_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from transcriber.gui import launch_gui

        launch_gui(
            initial_path=args.path,
            model=args.model,
            language=args.language,
            device=args.device,
        )
        return 0

    if not args.path:
        parser.print_help()
        return 2

    return _run_transcribe(args.path, args.model, args.language, args.device)


if __name__ == "__main__":
    raise SystemExit(main())
