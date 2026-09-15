# Offline Transcriber

Local Python app that turns MP3 (and other audio) into `.txt` and `.srt` files using [faster-whisper](https://github.com/SYSTRAN/faster-whisper). After a one-time model download, it runs **fully offline** on this PC. No cloud APIs, no accounts, no telemetry.

Command line and a simple desktop window are both included.

## Requirements

- Windows, with [Python 3.10+](https://www.python.org/downloads/) (3.11 or 3.12 recommended)
- Disk space for a model (`small` is a few hundred MB; `large-v3` is a few GB)
- Optional: NVIDIA GPU + CUDA for faster / larger models

## One-time setup (internet)

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m transcriber download small
```

That stores weights in `models\small\`. Repeat `download` with another size if you want a second model.

After this, you can disconnect from the network. Transcription never contacts Hugging Face or any other service.

## Use it

Desktop window:

```powershell
python -m transcriber --gui
```

Command line:

```powershell
python -m transcriber path\to\audio.mp3
python -m transcriber path\to\audio.mp3 --model small --language en
python -m transcriber path\to\folder --model small
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

- Models load from `models\<name>\` with `local_files_only=True`.
- If a model is missing, the app tells you to run `python -m transcriber download <name>` instead of downloading during transcription.
- Silero VAD (silence skipping) is bundled with faster-whisper; it does not need a network.

## Licenses

| Piece | License |
| --- | --- |
| This app | For your local use; keep it as you like |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT |
| [OpenAI Whisper](https://github.com/openai/whisper) weights | MIT |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT |
| FFmpeg / PyAV (MP3 decode) | Typically LGPL |

All of the above are free to use locally. This project does **not** call the paid OpenAI transcription API.
