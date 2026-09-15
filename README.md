# Offline Transcriber

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/akgordon/Transcriber/actions/workflows/ci.yml/badge.svg)](https://github.com/akgordon/Transcriber/actions/workflows/ci.yml)

Local Python app that turns MP3 (and other audio) into `.txt` and `.srt` files using [faster-whisper](https://github.com/SYSTRAN/faster-whisper). After a one-time model download, it runs **fully offline**. No cloud APIs, no accounts, no telemetry.

Command line and a simple desktop window are both included.

## Requirements

- Python 3.10+ (3.11–3.13 recommended)
- Disk space for a model (`small` is a few hundred MB; `large-v3` is a few GB)
- Optional: NVIDIA GPU + CUDA for faster / larger models

Works on Windows, macOS, and Linux.

## One-time setup (internet)

```bash
git clone https://github.com/akgordon/Transcriber.git
cd Transcriber
python -m venv .venv
```

Activate the virtual environment:

- Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

If PowerShell blocks the activate script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Then:

```bash
pip install -r requirements.txt
python -m transcriber download small
```

That stores weights in `models/small/`. Repeat `download` with another size if you want a second model.

After this, you can disconnect from the network. Transcription never contacts Hugging Face or any other service.

## Use it

Desktop window:

```bash
python -m transcriber --gui
```

Command line:

```bash
python -m transcriber path/to/audio.mp3
python -m transcriber path/to/audio.mp3 --model small --language en
python -m transcriber path/to/folder --model small
python -m transcriber download small
```

Outputs are written next to the source file:

- `audio.txt` — plain transcript
- `audio.srt` — timestamped subtitles

Supported files: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.opus`, `.webm`. Folder mode is non-recursive.

### Options

| Flag | Meaning |
| --- | --- |
| `--model` | `tiny`, `base`, `small` (default), `medium`, `large-v3`, `turbo` |
| `--language` | `auto` (default) or a code such as `en` |
| `--device` | `auto` (default), `cpu`, or `cuda` |
| `--gui` | Open the desktop window |

On CPU, start with `small`. Use `large-v3` or `turbo` if you have an NVIDIA GPU.

## Offline rules

- Models load from `models/<name>/` with `local_files_only=True`.
- If a model is missing, the app tells you to run `python -m transcriber download <name>` instead of downloading during transcription.
- Silero VAD (silence skipping) is bundled with faster-whisper; it does not need a network.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please report security issues as described in [SECURITY.md](SECURITY.md).

## License

This project is licensed under the [MIT License](LICENSE). Copyright (c) 2026 Alan Gordon.

Third-party components:

| Piece | License |
| --- | --- |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT |
| [OpenAI Whisper](https://github.com/openai/whisper) weights | MIT |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT |
| FFmpeg / PyAV (MP3 decode, installed via pip) | Typically LGPL |

This project does **not** call the paid OpenAI transcription API. Model weights are not shipped in the repository; each user downloads them locally.
