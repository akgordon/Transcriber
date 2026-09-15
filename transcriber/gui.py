"""Simple Tkinter window for offline transcription."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from transcriber.engine import (
    AUDIO_EXTENSIONS,
    DEFAULT_MODEL,
    MODEL_NAMES,
    LocalTranscriber,
    ModelNotFoundError,
    collect_audio_files,
    is_model_ready,
    missing_model_message,
)

LANGUAGES = (
    "auto",
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "zh",
    "ja",
    "ko",
    "ar",
    "hi",
    "nl",
    "pl",
    "sv",
)
DEVICES = ("auto", "cpu", "cuda")


class TranscriberApp(tk.Tk):
    def __init__(
        self,
        initial_path: str | None = None,
        model: str = DEFAULT_MODEL,
        language: str = "auto",
        device: str = "auto",
    ):
        super().__init__()
        self.title("Offline Transcriber")
        self.geometry("820x580")
        self.minsize(640, 480)

        self._queue: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._worker: threading.Thread | None = None

        self.path_var = tk.StringVar(value=initial_path or "")
        self.model_var = tk.StringVar(value=model if model in MODEL_NAMES else DEFAULT_MODEL)
        self.language_var = tk.StringVar(value=language if language in LANGUAGES else "auto")
        self.device_var = tk.StringVar(value=device if device in DEVICES else "auto")
        self.status_var = tk.StringVar(value="Ready. Models are used from the local models/ folder.")

        self._build()
        self.after(100, self._drain_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        path_row = ttk.Frame(root)
        path_row.pack(fill=tk.X, **pad)
        ttk.Label(path_row, text="Audio").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(path_row, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(path_row, text="Browse file", command=self._browse_file).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(path_row, text="Browse folder", command=self._browse_folder).pack(side=tk.LEFT)

        opts = ttk.Frame(root)
        opts.pack(fill=tk.X, **pad)
        ttk.Label(opts, text="Model").pack(side=tk.LEFT)
        self.model_box = ttk.Combobox(
            opts, textvariable=self.model_var, values=MODEL_NAMES, state="readonly", width=12
        )
        self.model_box.pack(side=tk.LEFT, padx=(6, 16))
        ttk.Label(opts, text="Language").pack(side=tk.LEFT)
        ttk.Combobox(
            opts, textvariable=self.language_var, values=LANGUAGES, state="readonly", width=8
        ).pack(side=tk.LEFT, padx=(6, 16))
        ttk.Label(opts, text="Device").pack(side=tk.LEFT)
        ttk.Combobox(
            opts, textvariable=self.device_var, values=DEVICES, state="readonly", width=8
        ).pack(side=tk.LEFT, padx=(6, 0))

        buttons = ttk.Frame(root)
        buttons.pack(fill=tk.X, **pad)
        self.transcribe_btn = ttk.Button(buttons, text="Transcribe", command=self._start)
        self.transcribe_btn.pack(side=tk.LEFT)
        self.cancel_btn = ttk.Button(buttons, text="Cancel", command=self._request_cancel, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=8)

        ttk.Label(root, textvariable=self.status_var).pack(fill=tk.X, **pad)

        log_frame = ttk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)
        self.log = tk.Text(log_frame, wrap=tk.WORD, height=18, state=tk.DISABLED)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _browse_file(self) -> None:
        filetypes = [
            ("Audio files", " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS)),
            ("All files", "*.*"),
        ]
        chosen = filedialog.askopenfilename(title="Choose audio file", filetypes=filetypes)
        if chosen:
            self.path_var.set(chosen)

    def _browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose folder of audio files")
        if chosen:
            self.path_var.set(chosen)

    def _append_log(self, line: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_running(self, running: bool) -> None:
        self.transcribe_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.cancel_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.path_entry.configure(state=tk.DISABLED if running else tk.NORMAL)

    def _start(self) -> None:
        raw_path = self.path_var.get().strip()
        if not raw_path:
            messagebox.showwarning("No file", "Choose an audio file or a folder first.")
            return
        model = self.model_var.get()
        if not is_model_ready(model):
            messagebox.showerror("Model missing", missing_model_message(model))
            self.status_var.set("Download a model before transcribing.")
            return
        try:
            files = collect_audio_files(Path(raw_path))
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Cannot transcribe", str(exc))
            return

        self._cancel.clear()
        self._set_running(True)
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)
        self.status_var.set(f"Starting ({len(files)} file{'s' if len(files) != 1 else ''}) ...")
        self._worker = threading.Thread(
            target=self._run_job,
            args=(files, model, self.language_var.get(), self.device_var.get()),
            daemon=True,
        )
        self._worker.start()

    def _request_cancel(self) -> None:
        self._cancel.set()
        self.status_var.set("Cancel requested ...")

    def _run_job(self, files: list[Path], model: str, language: str, device: str) -> None:
        try:
            engine = LocalTranscriber(model_name=model, device=device)
            self._queue.put(("status", f"Loading model '{model}' ..."))
            engine.load()
            self._queue.put(
                (
                    "log",
                    f"Using {engine.device_used} ({engine.compute_type_used}), model '{model}'",
                )
            )
            written: list[str] = []
            for index, audio in enumerate(files, start=1):
                if self._cancel.is_set():
                    self._queue.put(("cancelled", None))
                    return
                self._queue.put(("status", f"Transcribing {index}/{len(files)}: {audio.name}"))
                self._queue.put(("log", f"\n[{index}/{len(files)}] {audio}"))
                result = engine.transcribe_file(
                    audio,
                    language=language,
                    on_segment=lambda seg: self._queue.put(
                        ("log", f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
                    ),
                    should_cancel=self._cancel.is_set,
                )
                if self._cancel.is_set():
                    self._queue.put(("cancelled", None))
                    return
                self._queue.put(
                    (
                        "log",
                        f"Language: {result.language} ({result.language_probability:.0%})",
                    )
                )
                self._queue.put(("log", f"Wrote {result.txt_path}"))
                self._queue.put(("log", f"Wrote {result.srt_path}"))
                written.append(str(result.txt_path))
            self._queue.put(("done", written))
        except ModelNotFoundError as exc:
            self._queue.put(("error", str(exc)))
        except Exception as exc:
            self._queue.put(("error", f"{type(exc).__name__}: {exc}"))

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(str(payload))
            elif kind == "status":
                self.status_var.set(str(payload))
            elif kind == "done":
                self._set_running(False)
                count = len(payload) if isinstance(payload, list) else 0
                self.status_var.set(f"Done. Wrote {count} transcript(s).")
            elif kind == "cancelled":
                self._set_running(False)
                self.status_var.set("Cancelled.")
                self._append_log("Cancelled.")
            elif kind == "error":
                self._set_running(False)
                self.status_var.set("Error.")
                self._append_log(str(payload))
                messagebox.showerror("Transcription failed", str(payload))
        self.after(100, self._drain_queue)

    def _on_close(self) -> None:
        self._cancel.set()
        self.destroy()


def launch_gui(
    initial_path: str | None = None,
    model: str = DEFAULT_MODEL,
    language: str = "auto",
    device: str = "auto",
) -> None:
    app = TranscriberApp(
        initial_path=initial_path,
        model=model,
        language=language,
        device=device,
    )
    app.mainloop()
