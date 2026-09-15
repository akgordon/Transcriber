# Contributing

Thanks for wanting to improve Offline Transcriber. This is a small local-first project; keep changes focused.

## Development setup

```bash
git clone https://github.com/akgordon/Transcriber.git
cd Transcriber
python -m venv .venv
```

Activate `.venv`, then:

```bash
pip install -r requirements.txt
python -m transcriber --help
python -m unittest discover -s tests -v
```

You do not need a Whisper model to run `--help` or the unit tests. Download one only when you want to transcribe audio:

```bash
python -m transcriber download small
```

Do not commit `.venv/`, downloaded files under `models/` (except `models/.gitkeep`), or transcript output.

## Pull requests

- Open an issue first for larger changes.
- Keep PRs small and describe why the change is needed.
- Match the existing code style (Python 3.10+, stdlib Tkinter GUI, no extra UI toolkit).
- Transcription must stay offline after models are on disk: do not add network calls to the transcribe path.

## What belongs here

In scope: local transcription quality, CLI/GUI usability, packaging/docs, tests.

Out of scope for now: speaker diarization, live microphone, cloud APIs, shipping model weights in git.
