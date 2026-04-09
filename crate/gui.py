"""
Crate — GUI frontend built with customtkinter.

Layout
──────
┌──────────────────────────────────────────────────────────┐
│  CRATE                                  [dark/light btn] │
├──────────────────────────────────────────────────────────┤
│  Folder: [______________________________] [Browse]       │
│  Mode:   [both ▼]   Device: [cpu ▼]   Model: [4stems ▼] │
├──────────────────────────────────────────────────────────┤
│  [Analyse]   [Stems]   [Full Pipeline]   [☐ Dry run]     │
├──────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐    │
│  │ File │ BPM │ Key │ Camelot │ Confidence │ Status │    │
│  │ ...  │     │     │         │            │        │    │
│  └──────────────────────────────────────────────────┘    │
│  ████████████████░░░░░░  12 / 30  Analysing track.mp3    │
├──────────────────────────────────────────────────────────┤
│  [log output]                                            │
└──────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Optional

import customtkinter as ctk

from .analyzer import analyze
from .scanner import scan_folder
from .stems import MODELS, extract_stems
from .tagger import write_tags

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── colours ────────────────────────────────────────────────────────────────
_BG        = "#1a1a2e"
_PANEL     = "#16213e"
_ACCENT    = "#0f3460"
_GREEN     = "#4caf50"
_RED       = "#f44336"
_YELLOW    = "#ffc107"
_FG        = "#e0e0e0"
_FG_DIM    = "#888"
_ROW_ALT   = "#1e2a45"


class CrateApp(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()
        self.title("Crate")
        self.geometry("960x720")
        self.minsize(800, 600)
        self.configure(fg_color=_BG)

        self._folder: Optional[Path] = None
        self._output: Optional[Path] = None
        self._running = False
        self._q: queue.Queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_controls()
        self._build_table()
        self._build_progress()
        self._build_log()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=_PANEL, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="CRATE", font=ctk.CTkFont(size=26, weight="bold"),
            text_color=_FG,
        ).grid(row=0, column=0, padx=20, pady=14, sticky="w")

        ctk.CTkLabel(
            hdr, text="DJ-ready audio analysis",
            font=ctk.CTkFont(size=12), text_color=_FG_DIM,
        ).grid(row=0, column=1, padx=4, pady=14, sticky="w")

        self._theme_btn = ctk.CTkButton(
            hdr, text="☀ Light", width=80, height=28,
            fg_color=_ACCENT, hover_color="#1a4a80",
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=20, pady=14)

    def _build_controls(self) -> None:
        ctrl = ctk.CTkFrame(self, fg_color=_PANEL, corner_radius=8)
        ctrl.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
        ctrl.grid_columnconfigure(1, weight=1)

        # row 0 — source folder
        ctk.CTkLabel(ctrl, text="Source", text_color=_FG_DIM, width=60, anchor="e").grid(
            row=0, column=0, padx=(16, 8), pady=(14, 4), sticky="e"
        )
        self._folder_var = tk.StringVar(value="No folder selected")
        ctk.CTkEntry(
            ctrl, textvariable=self._folder_var,
            fg_color="#0d1b2a", border_color=_ACCENT,
            text_color=_FG, state="readonly",
        ).grid(row=0, column=1, padx=4, pady=(14, 4), sticky="ew")
        ctk.CTkButton(
            ctrl, text="Browse", width=90,
            fg_color=_ACCENT, hover_color="#1a4a80",
            command=self._browse_source,
        ).grid(row=0, column=2, padx=(4, 16), pady=(14, 4))

        # row 1 — output folder
        ctk.CTkLabel(ctrl, text="Output", text_color=_FG_DIM, width=60, anchor="e").grid(
            row=1, column=0, padx=(16, 8), pady=(2, 4), sticky="e"
        )
        self._output_var = tk.StringVar(value="Same as source (tag in place)")
        ctk.CTkEntry(
            ctrl, textvariable=self._output_var,
            fg_color="#0d1b2a", border_color="#1a3a5c",
            text_color=_FG_DIM, state="readonly",
        ).grid(row=1, column=1, padx=4, pady=(2, 4), sticky="ew")

        out_btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        out_btn_frame.grid(row=1, column=2, padx=(4, 16), pady=(2, 4))
        ctk.CTkButton(
            out_btn_frame, text="Browse", width=90,
            fg_color=_ACCENT, hover_color="#1a4a80",
            command=self._browse_output,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            out_btn_frame, text="✕", width=28,
            fg_color="#3a1a1a", hover_color="#5a2020",
            command=self._clear_output,
        ).pack(side="left")

        # row 2 — options
        opts = ctk.CTkFrame(ctrl, fg_color="transparent")
        opts.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=(4, 10))

        def _lbl(parent: ctk.CTkFrame, text: str) -> None:
            ctk.CTkLabel(parent, text=text, text_color=_FG_DIM, width=50, anchor="e").pack(
                side="left", padx=(0, 4)
            )

        _lbl(opts, "Mode")
        self._mode_var = tk.StringVar(value="both")
        ctk.CTkOptionMenu(
            opts, variable=self._mode_var,
            values=["both", "serato", "rekordbox"],
            width=110, fg_color=_ACCENT, button_color=_ACCENT,
        ).pack(side="left", padx=(0, 16))

        _lbl(opts, "Device")
        self._device_var = tk.StringVar(value="cpu")
        ctk.CTkOptionMenu(
            opts, variable=self._device_var,
            values=["cpu", "mps", "cuda"],
            width=80, fg_color=_ACCENT, button_color=_ACCENT,
        ).pack(side="left", padx=(0, 16))

        _lbl(opts, "Model")
        self._model_var = tk.StringVar(value="4stems")
        ctk.CTkOptionMenu(
            opts, variable=self._model_var,
            values=list(MODELS.keys()),
            width=110, fg_color=_ACCENT, button_color=_ACCENT,
        ).pack(side="left", padx=(0, 20))

        self._dry_run_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts, text="Dry run", variable=self._dry_run_var,
            text_color=_FG, fg_color=_ACCENT, hover_color="#1a4a80",
        ).pack(side="left", padx=(0, 20))

        self._recursive_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts, text="Recursive", variable=self._recursive_var,
            text_color=_FG, fg_color=_ACCENT, hover_color="#1a4a80",
        ).pack(side="left")

        # row 2 — action buttons
        btns = ctk.CTkFrame(ctrl, fg_color="transparent")
        btns.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

        btn_cfg = dict(height=36, corner_radius=6)
        self._btn_analyse = ctk.CTkButton(
            btns, text="Analyse (BPM + Key)", width=170,
            fg_color="#1b5e20", hover_color="#2e7d32",
            command=lambda: self._start("analyze"), **btn_cfg,
        )
        self._btn_analyse.pack(side="left", padx=(0, 8))

        self._btn_stems = ctk.CTkButton(
            btns, text="Extract Stems", width=140,
            fg_color="#0d47a1", hover_color="#1565c0",
            command=lambda: self._start("stems"), **btn_cfg,
        )
        self._btn_stems.pack(side="left", padx=(0, 8))

        self._btn_full = ctk.CTkButton(
            btns, text="Full Pipeline", width=130,
            fg_color="#4a148c", hover_color="#6a1fb0",
            command=lambda: self._start("full"), **btn_cfg,
        )
        self._btn_full.pack(side="left", padx=(0, 24))

        self._btn_stop = ctk.CTkButton(
            btns, text="Stop", width=80,
            fg_color=_RED, hover_color="#c62828", state="disabled",
            command=self._stop, **btn_cfg,
        )
        self._btn_stop.pack(side="left")

    def _build_table(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=_PANEL, corner_radius=8)
        frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Crate.Treeview",
            background="#0d1b2a", fieldbackground="#0d1b2a",
            foreground=_FG, rowheight=24,
            font=("Helvetica", 11),
        )
        style.configure(
            "Crate.Treeview.Heading",
            background=_ACCENT, foreground=_FG,
            font=("Helvetica", 11, "bold"),
        )
        style.map("Crate.Treeview", background=[("selected", "#1a4a80")])

        cols = ("file", "bpm", "key", "camelot", "confidence", "status")
        self._tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            style="Crate.Treeview", selectmode="extended",
        )

        col_cfg = [
            ("file",       "File",       350, "w"),
            ("bpm",        "BPM",         60, "center"),
            ("key",        "Key",        120, "center"),
            ("camelot",    "Camelot",     70, "center"),
            ("confidence", "Confidence",  90, "center"),
            ("status",     "Status",      90, "center"),
        ]
        for cid, heading, width, anchor in col_cfg:
            self._tree.heading(cid, text=heading)
            self._tree.column(cid, width=width, anchor=anchor, stretch=cid == "file")

        self._tree.tag_configure("ok",    foreground=_GREEN)
        self._tree.tag_configure("error", foreground=_RED)
        self._tree.tag_configure("dry",   foreground=_YELLOW)
        self._tree.tag_configure("alt",   background=_ROW_ALT)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        vsb.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 4))

    def _build_progress(self) -> None:
        prog = ctk.CTkFrame(self, fg_color=_PANEL, corner_radius=8)
        prog.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
        prog.grid_columnconfigure(0, weight=1)

        self._progress_bar = ctk.CTkProgressBar(
            prog, mode="determinate", height=12,
            fg_color="#0d1b2a", progress_color=_ACCENT,
        )
        self._progress_bar.set(0)
        self._progress_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))

        self._progress_label = ctk.CTkLabel(
            prog, text="Ready", text_color=_FG_DIM,
            font=ctk.CTkFont(size=11),
        )
        self._progress_label.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

    def _build_log(self) -> None:
        log_frame = ctk.CTkFrame(self, fg_color=_PANEL, corner_radius=8)
        log_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 10))
        log_frame.grid_columnconfigure(0, weight=1)

        self._log = ctk.CTkTextbox(
            log_frame, height=110, fg_color="#0d1b2a",
            text_color=_FG_DIM, font=ctk.CTkFont(family="Courier", size=11),
            state="disabled",
        )
        self._log.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    # ── actions ─────────────────────────────────────────────────────────────

    def _browse_source(self) -> None:
        path = filedialog.askdirectory(title="Select source music folder")
        if path:
            self._folder = Path(path)
            self._folder_var.set(str(self._folder))
            self._log_msg(f"Source: {path}")

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder for tagged copies")
        if path:
            self._output = Path(path)
            self._output_var.set(str(self._output))
            self._log_msg(f"Output: {path}")

    def _clear_output(self) -> None:
        self._output = None
        self._output_var.set("Same as source (tag in place)")

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("light")
            self._theme_btn.configure(text="🌙 Dark")
        else:
            ctk.set_appearance_mode("dark")
            self._theme_btn.configure(text="☀ Light")

    def _start(self, mode: str) -> None:
        if not self._folder or not self._folder.exists():
            self._log_msg("Please select a valid folder first.", level="warn")
            return
        if self._running:
            return

        self._running = True
        self._set_buttons_state("disabled")
        self._btn_stop.configure(state="normal")

        for item in self._tree.get_children():
            self._tree.delete(item)
        self._progress_bar.set(0)
        self._progress_label.configure(text="Starting…")

        thread = threading.Thread(
            target=self._worker,
            args=(mode,),
            daemon=True,
        )
        thread.start()

    def _stop(self) -> None:
        self._running = False
        self._log_msg("Stopping after current file…", level="warn")

    # ── background worker ────────────────────────────────────────────────────

    def _worker(self, pipeline: str) -> None:
        folder      = self._folder
        output      = self._output
        mode        = self._mode_var.get()
        device      = self._device_var.get()
        model       = self._model_var.get()
        dry_run     = self._dry_run_var.get()
        recursive   = self._recursive_var.get()

        files = scan_folder(folder, recursive=recursive)
        if not files:
            self._q.put(("log", "No audio files found in the selected folder.", "warn"))
            self._q.put(("done", None))
            return

        dest_note = f" → {output}" if output else " (in place)"
        self._q.put(("log", f"Found {len(files)} file(s) — running '{pipeline}' pipeline{dest_note}", "info"))
        total = len(files)

        stems_out = (output / "stems") if output else None

        for idx, path in enumerate(files):
            if not self._running:
                self._q.put(("log", "Stopped by user.", "warn"))
                break

            row_id = str(idx)

            if pipeline in ("analyze", "full"):
                self._q.put(("progress", idx, total, f"Analysing  {path.name}"))
                try:
                    result = analyze(path)
                    if not dry_run:
                        write_tags(path, result, mode=mode, output_root=output, source_root=folder)
                    status = "Dry run" if dry_run else ("Copied & tagged" if output else "Tagged")
                    self._q.put(("row_analyze", row_id, path.name, result, status, idx))
                    self._q.put(("log", f"[{idx+1}/{total}] {path.name}  BPM={result.bpm}  {result.key}  {result.camelot}", "ok"))
                except Exception as exc:
                    self._q.put(("row_error", row_id, path.name, str(exc), idx))
                    self._q.put(("log", f"[{idx+1}/{total}] ERROR {path.name}: {exc}", "error"))

            if pipeline in ("stems", "full"):
                self._q.put(("progress", idx, total, f"Extracting stems  {path.name}"))
                try:
                    stem_dir = extract_stems(path, output_dir=stems_out, model=model, device=device)
                    self._q.put(("log", f"[{idx+1}/{total}] Stems → {stem_dir}", "ok"))
                except Exception as exc:
                    self._q.put(("log", f"[{idx+1}/{total}] STEMS ERROR {path.name}: {exc}", "error"))

        self._q.put(("progress", total, total, "Done"))
        self._q.put(("done", None))

    # ── queue polling ────────────────────────────────────────────────────────

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._q.get_nowait()
                self._handle_msg(msg)
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _handle_msg(self, msg: tuple) -> None:
        kind = msg[0]

        if kind == "progress":
            _, done, total, label = msg
            frac = done / total if total else 0
            self._progress_bar.set(frac)
            self._progress_label.configure(text=f"{label}  ({done}/{total})")

        elif kind == "row_analyze":
            _, row_id, name, result, status, idx = msg
            tag = "dry" if status == "Dry run" else "ok"
            alt = "alt" if idx % 2 else ""
            self._tree.insert(
                "", "end", iid=row_id,
                values=(
                    name,
                    f"{result.bpm:.1f}",
                    result.key,
                    result.camelot,
                    f"{result.confidence:.3f}",
                    status,
                ),
                tags=(tag, alt),
            )
            self._tree.see(row_id)

        elif kind == "row_error":
            _, row_id, name, error, idx = msg
            alt = "alt" if idx % 2 else ""
            self._tree.insert(
                "", "end", iid=row_id,
                values=(name, "-", "-", "-", "-", "Error"),
                tags=("error", alt),
            )
            self._tree.see(row_id)

        elif kind == "log":
            _, text, level = msg
            self._log_msg(text, level=level)

        elif kind == "done":
            self._running = False
            self._set_buttons_state("normal")
            self._btn_stop.configure(state="disabled")

    def _log_msg(self, text: str, level: str = "info") -> None:
        prefix = {"info": "→", "ok": "✓", "warn": "⚠", "error": "✗"}.get(level, "→")
        self._log.configure(state="normal")
        self._log.insert("end", f"{prefix}  {text}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_buttons_state(self, state: str) -> None:
        for btn in (self._btn_analyse, self._btn_stems, self._btn_full):
            btn.configure(state=state)


def launch() -> None:
    app = CrateApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
