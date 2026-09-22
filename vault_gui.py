#!/usr/bin/env python3
"""
vault_gui.py

A cross-platform (Linux + Windows) Tkinter GUI for creating and
recovering threshold-recoverable encrypted vaults. Uses only the
Python standard library for the UI (tkinter), so PyInstaller can
bundle it into a single executable with no extra GUI toolkit to
install on the target machine.

Calls the exact same vault_core.create_vault / match_codewords /
reconstruct_and_decrypt functions used by the CLI scripts -- this GUI
is a second frontend on the same crypto implementation, not a
reimplementation of it.
"""

import importlib.util
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkfont

if importlib.util.find_spec("cryptography") is None:
    # Tkinter may not even be usable yet if this is missing, but try to
    # show a dialog; fall back to stderr if Tk itself can't start.
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Missing dependency",
            "This program requires the 'cryptography' package, which isn't "
            "installed here.\n\nRun:\n    pip install cryptography\n\n"
            "then try again.",
        )
    except Exception:
        print(
            "error: this program requires the 'cryptography' package, which "
            "isn't installed here.\n  Run: pip install cryptography",
            file=sys.stderr,
        )
    sys.exit(1)

import kdf as kdfmod
import vault_core
import vault_core_prime

APP_TITLE = "VaultTool"


class LogQueueWriter:
    """Thread-safe log sink: worker threads push strings, the Tk main
    loop drains them periodically via root.after()."""

    def __init__(self):
        self.q = queue.Queue()

    def __call__(self, msg: str):
        self.q.put(msg)


def browse_file(entry: tk.Entry, filetypes=(("All files", "*.*"),), save=False):
    if save:
        path = filedialog.asksaveasfilename(filetypes=filetypes)
    else:
        path = filedialog.askopenfilename(filetypes=filetypes)
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def browse_dir(entry: tk.Entry):
    path = filedialog.askdirectory()
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


class CreateTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.columnconfigure(1, weight=1)
        self._build()
        self._log_writer = LogQueueWriter()
        self._running = False

    def _build(self):
        row = 0

        def add_row(label, widget_factory, help_text=None):
            nonlocal row
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=3)
            widget = widget_factory(row)
            row += 1
            if help_text:
                ttk.Label(self, text=help_text, foreground="#666", font=("", 8)).grid(
                    row=row, column=1, sticky="w", pady=(0, 6)
                )
                row += 1
            return widget

        # Input path (file or folder)
        input_frame = ttk.Frame(self)
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(input_frame, text="File...", width=8,
                   command=lambda: browse_file(self.input_entry)).pack(side="left", padx=2)
        ttk.Button(input_frame, text="Folder...", width=8,
                   command=lambda: browse_dir(self.input_entry)).pack(side="left")
        ttk.Label(self, text="Input (file or folder)").grid(row=row, column=0, sticky="w", pady=3)
        input_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # Trustees / threshold / word length / word count
        self.trustees_var = tk.IntVar(value=5)
        self.threshold_var = tk.IntVar(value=3)
        self.word_length_var = tk.IntVar(value=8)
        self.word_count_var = tk.IntVar(value=8)
        self.memorable_var = tk.BooleanVar(value=True)
        self.strong_words_var = tk.BooleanVar(value=False)
        self.word_length_spinbox = None
        self.strong_words_check = None

        add_row("Total trustees (T)", lambda r: ttk.Spinbox(
            self, from_=1, to=255, textvariable=self.trustees_var, width=8
        ).grid(row=r, column=1, sticky="w"))
        add_row("Threshold to recover (D)", lambda r: ttk.Spinbox(
            self, from_=1, to=255, textvariable=self.threshold_var, width=8
        ).grid(row=r, column=1, sticky="w"))

        add_row("Memorable codewords", lambda r: ttk.Checkbutton(
            self, variable=self.memorable_var, command=self._on_memorable_toggle
        ).grid(row=r, column=1, sticky="w"),
            help_text="Whole, real dictionary words (bundled EFF wordlist by default) instead "
                       "of random syllables -- easier to actually remember. Recommended "
                       "default; uncheck for fixed-length/denser codewords instead.")

        def _word_length_widget(r):
            sb = ttk.Spinbox(self, from_=3, to=30, textvariable=self.word_length_var, width=8)
            sb.grid(row=r, column=1, sticky="w")
            self.word_length_spinbox = sb
        add_row("Codeword length (characters)", _word_length_widget,
            help_text="Ignored in memorable mode -- real words keep their natural length.")

        add_row("Words per trustee codeword", lambda r: ttk.Spinbox(
            self, from_=1, to=10, textvariable=self.word_count_var, width=8
        ).grid(row=r, column=1, sticky="w"),
            help_text="More words = more entropy. 8+ recommended for memorable mode (this default), "
                       "2+ otherwise -- lower for easier recall, higher for more margin.")

        def _strong_words_widget(r):
            cb = ttk.Checkbutton(self, variable=self.strong_words_var, command=self._on_strong_words_toggle)
            cb.grid(row=r, column=1, sticky="w")
            self.strong_words_check = cb
        add_row("Strong words", _strong_words_widget,
            help_text="Randomizes letter case and appends a 3-digit suffix to each word for "
                       "more entropy at the same length. Only use this if codewords will be "
                       "typed/pasted rather than read aloud or handwritten. Mutually exclusive "
                       "with memorable mode (case/digit noise undermines memorability).")

        # Dictionary (optional)
        dict_frame = ttk.Frame(self)
        self.dict_entry = ttk.Entry(dict_frame)
        self.dict_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(dict_frame, text="Browse...", width=10,
                   command=lambda: browse_file(self.dict_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Dictionary file (optional)").grid(row=row, column=0, sticky="w", pady=3)
        dict_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
        ttk.Label(self, text="Leave blank: memorable mode uses the bundled EFF wordlist, "
                              "otherwise built-in synthetic pronounceable words.",
                  foreground="#666", font=("", 8), wraplength=440, justify="left").grid(
            row=row, column=1, sticky="w", pady=(0, 6))
        row += 1

        self._on_memorable_toggle()

        # Output dir
        out_frame = ttk.Frame(self)
        self.outdir_entry = ttk.Entry(out_frame)
        self.outdir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_frame, text="Browse...", width=10,
                   command=lambda: browse_dir(self.outdir_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Output folder").grid(row=row, column=0, sticky="w", pady=3)
        out_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # KDF choice
        ttk.Label(self, text="Key derivation").grid(row=row, column=0, sticky="w", pady=3)
        kdf_frame = ttk.Frame(self)
        kdf_frame.grid(row=row, column=1, sticky="w", pady=3)
        self.kdf_var = tk.StringVar(value="auto")
        ttk.Radiobutton(kdf_frame, text="Auto (Argon2id if available)", variable=self.kdf_var, value="auto").pack(anchor="w")
        argon2_label = "Argon2id (stronger)" + ("" if kdfmod.ARGON2_AVAILABLE else " -- unavailable, install argon2-cffi")
        argon2_radio = ttk.Radiobutton(kdf_frame, text=argon2_label, variable=self.kdf_var, value="argon2id")
        argon2_radio.pack(anchor="w")
        if not kdfmod.ARGON2_AVAILABLE:
            argon2_radio.state(["disabled"])
        ttk.Radiobutton(kdf_frame, text="PBKDF2 (no extra dependency)", variable=self.kdf_var, value="pbkdf2").pack(anchor="w")

        self.argon2_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            kdf_frame, text="Customize Argon2id cost (advanced)",
            variable=self.argon2_custom_var, command=self._on_argon2_custom_toggle,
        ).pack(anchor="w", pady=(6, 0))

        self.argon2_time_cost_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_TIME_COST)
        self.argon2_memory_cost_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_MEMORY_COST_KIB)
        self.argon2_parallelism_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_PARALLELISM)
        self.argon2_custom_frame = ttk.Frame(kdf_frame)
        for label_text, var, width in (
            ("Time cost", self.argon2_time_cost_var, 6),
            ("Memory cost (KiB)", self.argon2_memory_cost_var, 10),
            ("Parallelism", self.argon2_parallelism_var, 6),
        ):
            field_row = ttk.Frame(self.argon2_custom_frame)
            ttk.Label(field_row, text=label_text, width=16).pack(side="left")
            ttk.Spinbox(field_row, from_=1, to=10_000_000, textvariable=var, width=width).pack(side="left")
            field_row.pack(anchor="w", pady=1)
        ttk.Label(
            self.argon2_custom_frame,
            text=f"Defaults ({kdfmod.DEFAULT_ARGON2_TIME_COST} / {kdfmod.DEFAULT_ARGON2_MEMORY_COST_KIB} KiB / "
                 f"{kdfmod.DEFAULT_ARGON2_PARALLELISM}) are already raised for a high security margin -- "
                 "lower them for faster recovery, or raise further for even more margin.",
            foreground="#666", font=("", 8), wraplength=380, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        # self.argon2_custom_frame stays unpacked (hidden) until the checkbox above is checked
        row += 1

        # Action button
        self.create_button = ttk.Button(self, text="Create Vault", command=self.on_create)
        self.create_button.grid(row=row, column=0, columnspan=2, pady=(10, 6))
        row += 1

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        row += 1

        self.log_box = scrolledtext.ScrolledText(self, height=12, state="disabled", wrap="word")
        self.log_box.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(row, weight=1)

    def _append_log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _poll_log_queue(self):
        drained_any = False
        try:
            while True:
                msg = self._log_writer.q.get_nowait()
                self._append_log(msg)
                drained_any = True
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self._poll_log_queue)

    def _on_memorable_toggle(self):
        memorable = bool(self.memorable_var.get())
        if memorable:
            self.strong_words_var.set(False)
        if self.strong_words_check is not None:
            self.strong_words_check.state(["disabled" if memorable else "!disabled"])
        if self.word_length_spinbox is not None:
            self.word_length_spinbox.state(["disabled" if memorable else "!disabled"])

    def _on_strong_words_toggle(self):
        if bool(self.strong_words_var.get()):
            self.memorable_var.set(False)
            self._on_memorable_toggle()

    def _on_argon2_custom_toggle(self):
        if bool(self.argon2_custom_var.get()):
            self.argon2_custom_frame.pack(anchor="w", pady=(4, 2))
        else:
            self.argon2_custom_frame.pack_forget()

    def on_create(self):
        input_path = self.input_entry.get().strip()
        if not input_path:
            messagebox.showerror(APP_TITLE, "Choose a file or folder to encrypt first.")
            return
        if not os.path.exists(input_path):
            messagebox.showerror(APP_TITLE, f"Input path not found:\n{input_path}")
            return

        memorable = bool(self.memorable_var.get())
        try:
            trustees = int(self.trustees_var.get())
            threshold = int(self.threshold_var.get())
            word_count = int(self.word_count_var.get())
            word_length = None if memorable else int(self.word_length_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror(APP_TITLE, "Trustees, threshold, word length, and word count must be numbers.")
            return
        strong_words = bool(self.strong_words_var.get()) and not memorable

        if threshold > trustees:
            messagebox.showerror(APP_TITLE, "Threshold (D) cannot exceed total trustees (T).")
            return
        if not memorable and word_length < 3:
            messagebox.showerror(APP_TITLE, "Codeword length should be at least 3 characters.")
            return

        dictionary_path = self.dict_entry.get().strip() or None
        outdir = self.outdir_entry.get().strip() or None

        # Resolve KDF choice, with a confirmation dialog for the auto-fallback case
        choice = self.kdf_var.get()
        if choice == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
            messagebox.showerror(
                APP_TITLE,
                "Argon2id was selected, but 'argon2-cffi' isn't installed.\n\n"
                "Install it (pip install argon2-cffi) or choose a different "
                "KDF option.",
            )
            return
        if choice == "auto":
            if kdfmod.ARGON2_AVAILABLE:
                kdf_method = "argon2id"
            else:
                proceed = messagebox.askyesno(
                    APP_TITLE,
                    "'argon2-cffi' is not installed, so Argon2id (the stronger, "
                    "memory-hard key derivation function) isn't available.\n\n"
                    "Shard protection would fall back to PBKDF2-HMAC-SHA256, "
                    "which is weaker against GPU/ASIC-parallel offline guessing "
                    "of your codewords.\n\n"
                    "For stronger protection, install argon2-cffi and restart "
                    "this program.\n\n"
                    "Proceed with the PBKDF2 fallback anyway?",
                )
                if not proceed:
                    return
                kdf_method = "pbkdf2"
        else:
            kdf_method = choice

        if kdf_method == "argon2id" and bool(self.argon2_custom_var.get()):
            try:
                argon2_overrides = {
                    "time_cost": int(self.argon2_time_cost_var.get()),
                    "memory_cost_kib": int(self.argon2_memory_cost_var.get()),
                    "parallelism": int(self.argon2_parallelism_var.get()),
                }
            except (tk.TclError, ValueError):
                messagebox.showerror(APP_TITLE, "Argon2id time cost, memory cost, and parallelism must be numbers.")
                return
            kdf_params = vault_core.resolve_kdf_params(kdf_method, argon2_overrides)
        else:
            kdf_params = kdfmod.default_params(kdf_method)

        self._running = True
        self.create_button.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")
        self.progress.start(12)
        self.after(100, self._poll_log_queue)

        def worker():
            try:
                result = vault_core.create_vault(
                    input_path=input_path,
                    trustees=trustees,
                    threshold=threshold,
                    word_length=word_length,
                    word_count=word_count,
                    dictionary_path=dictionary_path,
                    outdir=outdir,
                    kdf_method=kdf_method,
                    kdf_params=kdf_params,
                    randomize_case=strong_words,
                    digit_suffix_len=3 if strong_words else 0,
                    log=self._log_writer,
                )
                self._log_writer(f"Wrote {len(result['trustee_files'])} trustee codeword files to: {result['words_dir']}")
                self.after(0, lambda: self._on_create_done(result))
            except (ValueError, vault_core.VaultError) as e:
                msg = str(e)
                self.after(0, lambda: self._on_create_error(msg))
            except Exception as e:  # noqa: BLE001 - surface anything unexpected to the user
                msg = f"Unexpected error: {e}"
                self.after(0, lambda: self._on_create_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self):
        self._running = False
        self.progress.stop()
        self.create_button.configure(state="normal")

    def _on_create_done(self, result):
        self._finish()
        messagebox.showinfo(
            APP_TITLE,
            "Vault created successfully.\n\n"
            f"Container file:\n{result['krypt_path']}\n\n"
            f"Trustee codewords:\n{result['words_dir']}\n\n"
            "Distribute each trustee_N.txt to one trustee out-of-band, then "
            "delete these files from this machine.",
        )

    def _on_create_error(self, message):
        self._finish()
        messagebox.showerror(APP_TITLE, f"Vault creation failed:\n\n{message}")


class RecoverTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.columnconfigure(1, weight=1)
        self.metadata = None
        self.ciphertext = None
        self.word_entries = []
        self._log_writer = LogQueueWriter()
        self._running = False
        self._build()

    def _build(self):
        row = 0

        krypt_frame = ttk.Frame(self)
        self.krypt_entry = ttk.Entry(krypt_frame)
        self.krypt_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(krypt_frame, text="Browse...", width=10,
                   command=self.on_browse_krypt).pack(side="left", padx=2)
        ttk.Label(self, text=".krypt file").grid(row=row, column=0, sticky="w", pady=3)
        krypt_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.load_button = ttk.Button(self, text="Load Vault Info", command=self.on_load)
        self.load_button.grid(row=row, column=0, columnspan=2, pady=(2, 8))
        row += 1

        self.info_label = ttk.Label(self, text="No vault loaded yet.", foreground="#444")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        self.words_container = ttk.LabelFrame(self, text="Codewords")
        self.words_container.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.columnconfigure(1, weight=1)
        row += 1

        out_frame = ttk.Frame(self)
        self.outdir_entry = ttk.Entry(out_frame)
        self.outdir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_frame, text="Browse...", width=10,
                   command=lambda: browse_dir(self.outdir_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Output folder").grid(row=row, column=0, sticky="w", pady=3)
        out_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.recover_button = ttk.Button(self, text="Recover Vault", command=self.on_recover, state="disabled")
        self.recover_button.grid(row=row, column=0, columnspan=2, pady=(10, 6))
        row += 1

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        row += 1

        self.log_box = scrolledtext.ScrolledText(self, height=8, state="disabled", wrap="word")
        self.log_box.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(row, weight=1)

    def on_browse_krypt(self):
        browse_file(self.krypt_entry, filetypes=(("VaultTool container", "*.krypt"), ("All files", "*.*")))

    def _append_log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _poll_log_queue(self):
        drained_any = False
        try:
            while True:
                msg = self._log_writer.q.get_nowait()
                self._append_log(msg)
                drained_any = True
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self._poll_log_queue)

    def on_load(self):
        path = self.krypt_entry.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror(APP_TITLE, "Choose a valid .krypt file first.")
            return
        try:
            metadata = vault_core.peek_metadata(path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Couldn't read this file as a vault:\n\n{e}")
            return

        self.metadata = metadata
        self.ciphertext = None  # loaded again (cheaply) at recovery time

        threshold = metadata["threshold"]
        total = metadata["trustees_total"]
        kdf_method = metadata.get("kdf", "pbkdf2")

        info_text = f"This vault needs {threshold} of {total} codewords. KDF: {kdf_method}."
        if kdf_method == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
            info_text += "\n\u26a0 argon2-cffi is not installed -- install it before recovering this vault."
        self.info_label.configure(text=info_text)

        for child in self.words_container.winfo_children():
            child.destroy()
        self.word_entries = []
        for i in range(threshold):
            ttk.Label(self.words_container, text=f"Codeword {i + 1}:").grid(row=i, column=0, sticky="w", padx=6, pady=2)
            entry = ttk.Entry(self.words_container, show="\u2022")
            entry.grid(row=i, column=1, sticky="ew", padx=6, pady=2)
            self.word_entries.append(entry)
        self.words_container.columnconfigure(1, weight=1)

        can_recover = not (kdf_method == "argon2id" and not kdfmod.ARGON2_AVAILABLE)
        self.recover_button.configure(state="normal" if can_recover else "disabled")

    def on_recover(self):
        if self.metadata is None:
            messagebox.showerror(APP_TITLE, "Load a vault first.")
            return
        path = self.krypt_entry.get().strip()

        codewords = [e.get() for e in self.word_entries]
        if all(not w.strip() for w in codewords):
            messagebox.showerror(APP_TITLE, "Enter at least the required number of codewords.")
            return

        outdir = self.outdir_entry.get().strip() or None

        self._running = True
        self.recover_button.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")
        self.progress.start(12)
        self.after(100, self._poll_log_queue)

        def worker():
            try:
                # Re-read the container fresh (cheap) so we have both
                # metadata and ciphertext together without holding large
                # ciphertext in memory between Load and Recover clicks.
                metadata, ciphertext = vault_core.krypt_container.read_krypt(path)
                recovered, unmatched = vault_core.match_codewords(codewords, metadata)
                if unmatched:
                    self._log_writer(
                        f"{len(unmatched)} entered codeword(s) didn't match any shard and were skipped."
                    )
                result = vault_core.reconstruct_and_decrypt(
                    metadata, ciphertext, recovered, outdir=outdir, log=self._log_writer
                )
                self.after(0, lambda: self._on_recover_done(result))
            except vault_core.VaultError as e:
                msg = str(e)
                self.after(0, lambda: self._on_recover_error(msg))
            except Exception as e:  # noqa: BLE001
                msg = f"Unexpected error: {e}"
                self.after(0, lambda: self._on_recover_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self):
        self._running = False
        self.progress.stop()
        self.recover_button.configure(state="normal")

    def _on_recover_done(self, result):
        self._finish()
        messagebox.showinfo(APP_TITLE, f"Recovery successful.\n\nExtracted to:\n{result['outdir']}")

    def _on_recover_error(self, message):
        self._finish()
        messagebox.showerror(APP_TITLE, f"Recovery failed:\n\n{message}")


class CreatePrimeTab(ttk.Frame):
    """Same flow as CreateTab, but drives vault_core_prime.create_vault_prime:
    one of the trustees is a mandatory PRIME trustee, the rest are an
    interchangeable pool. T/D here count the prime trustee."""

    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.columnconfigure(1, weight=1)
        self._build()
        self._log_writer = LogQueueWriter()
        self._running = False

    def _build(self):
        row = 0

        def add_row(label, widget_factory, help_text=None):
            nonlocal row
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=3)
            widget = widget_factory(row)
            row += 1
            if help_text:
                ttk.Label(self, text=help_text, foreground="#666", font=("", 8)).grid(
                    row=row, column=1, sticky="w", pady=(0, 6)
                )
                row += 1
            return widget

        ttk.Label(
            self,
            text="One trustee is the PRIME trustee: their codeword is required for "
                 "every recovery. The rest are a plain interchangeable pool.",
            foreground="#444", font=("", 8), wraplength=440, justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        # Input path (file or folder)
        input_frame = ttk.Frame(self)
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(input_frame, text="File...", width=8,
                   command=lambda: browse_file(self.input_entry)).pack(side="left", padx=2)
        ttk.Button(input_frame, text="Folder...", width=8,
                   command=lambda: browse_dir(self.input_entry)).pack(side="left")
        ttk.Label(self, text="Input (file or folder)").grid(row=row, column=0, sticky="w", pady=3)
        input_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # Trustees / threshold / word length / word count
        self.trustees_var = tk.IntVar(value=4)
        self.threshold_var = tk.IntVar(value=3)
        self.word_length_var = tk.IntVar(value=8)
        self.word_count_var = tk.IntVar(value=8)
        self.memorable_var = tk.BooleanVar(value=True)
        self.strong_words_var = tk.BooleanVar(value=False)
        self.word_length_spinbox = None
        self.strong_words_check = None

        add_row("Total trustees, incl. prime (T)", lambda r: ttk.Spinbox(
            self, from_=2, to=255, textvariable=self.trustees_var, width=8
        ).grid(row=r, column=1, sticky="w"),
            help_text="1 prime + (T-1) pool trustees.")
        add_row("Threshold to recover, incl. prime (D)", lambda r: ttk.Spinbox(
            self, from_=2, to=255, textvariable=self.threshold_var, width=8
        ).grid(row=r, column=1, sticky="w"),
            help_text="The prime codeword + (D-1) from the pool.")

        add_row("Memorable codewords", lambda r: ttk.Checkbutton(
            self, variable=self.memorable_var, command=self._on_memorable_toggle
        ).grid(row=r, column=1, sticky="w"),
            help_text="Whole, real dictionary words (bundled EFF wordlist by default) instead "
                       "of random syllables -- easier to actually remember. Recommended "
                       "default; uncheck for fixed-length/denser codewords instead.")

        def _word_length_widget(r):
            sb = ttk.Spinbox(self, from_=3, to=30, textvariable=self.word_length_var, width=8)
            sb.grid(row=r, column=1, sticky="w")
            self.word_length_spinbox = sb
        add_row("Codeword length (characters)", _word_length_widget,
            help_text="Ignored in memorable mode -- real words keep their natural length.")

        add_row("Words per trustee codeword", lambda r: ttk.Spinbox(
            self, from_=1, to=10, textvariable=self.word_count_var, width=8
        ).grid(row=r, column=1, sticky="w"),
            help_text="More words = more entropy. 8+ recommended for memorable mode (this default), "
                       "2+ otherwise -- lower for easier recall, higher for more margin.")

        def _strong_words_widget(r):
            cb = ttk.Checkbutton(self, variable=self.strong_words_var, command=self._on_strong_words_toggle)
            cb.grid(row=r, column=1, sticky="w")
            self.strong_words_check = cb
        add_row("Strong words", _strong_words_widget,
            help_text="Randomizes letter case and appends a 3-digit suffix to each word for "
                       "more entropy at the same length. Only use this if codewords will be "
                       "typed/pasted rather than read aloud or handwritten. Mutually exclusive "
                       "with memorable mode (case/digit noise undermines memorability).")

        # Dictionary (optional)
        dict_frame = ttk.Frame(self)
        self.dict_entry = ttk.Entry(dict_frame)
        self.dict_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(dict_frame, text="Browse...", width=10,
                   command=lambda: browse_file(self.dict_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Dictionary file (optional)").grid(row=row, column=0, sticky="w", pady=3)
        dict_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
        ttk.Label(self, text="Leave blank: memorable mode uses the bundled EFF wordlist, "
                              "otherwise built-in synthetic pronounceable words.",
                  foreground="#666", font=("", 8), wraplength=440, justify="left").grid(
            row=row, column=1, sticky="w", pady=(0, 6))
        row += 1

        self._on_memorable_toggle()

        # Output dir
        out_frame = ttk.Frame(self)
        self.outdir_entry = ttk.Entry(out_frame)
        self.outdir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_frame, text="Browse...", width=10,
                   command=lambda: browse_dir(self.outdir_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Output folder").grid(row=row, column=0, sticky="w", pady=3)
        out_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # KDF choice
        ttk.Label(self, text="Key derivation").grid(row=row, column=0, sticky="w", pady=3)
        kdf_frame = ttk.Frame(self)
        kdf_frame.grid(row=row, column=1, sticky="w", pady=3)
        self.kdf_var = tk.StringVar(value="auto")
        ttk.Radiobutton(kdf_frame, text="Auto (Argon2id if available)", variable=self.kdf_var, value="auto").pack(anchor="w")
        argon2_label = "Argon2id (stronger)" + ("" if kdfmod.ARGON2_AVAILABLE else " -- unavailable, install argon2-cffi")
        argon2_radio = ttk.Radiobutton(kdf_frame, text=argon2_label, variable=self.kdf_var, value="argon2id")
        argon2_radio.pack(anchor="w")
        if not kdfmod.ARGON2_AVAILABLE:
            argon2_radio.state(["disabled"])
        ttk.Radiobutton(kdf_frame, text="PBKDF2 (no extra dependency)", variable=self.kdf_var, value="pbkdf2").pack(anchor="w")

        self.argon2_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            kdf_frame, text="Customize Argon2id cost (advanced)",
            variable=self.argon2_custom_var, command=self._on_argon2_custom_toggle,
        ).pack(anchor="w", pady=(6, 0))

        self.argon2_time_cost_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_TIME_COST)
        self.argon2_memory_cost_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_MEMORY_COST_KIB)
        self.argon2_parallelism_var = tk.IntVar(value=kdfmod.DEFAULT_ARGON2_PARALLELISM)
        self.argon2_custom_frame = ttk.Frame(kdf_frame)
        for label_text, var, width in (
            ("Time cost", self.argon2_time_cost_var, 6),
            ("Memory cost (KiB)", self.argon2_memory_cost_var, 10),
            ("Parallelism", self.argon2_parallelism_var, 6),
        ):
            field_row = ttk.Frame(self.argon2_custom_frame)
            ttk.Label(field_row, text=label_text, width=16).pack(side="left")
            ttk.Spinbox(field_row, from_=1, to=10_000_000, textvariable=var, width=width).pack(side="left")
            field_row.pack(anchor="w", pady=1)
        ttk.Label(
            self.argon2_custom_frame,
            text=f"Defaults ({kdfmod.DEFAULT_ARGON2_TIME_COST} / {kdfmod.DEFAULT_ARGON2_MEMORY_COST_KIB} KiB / "
                 f"{kdfmod.DEFAULT_ARGON2_PARALLELISM}) are already raised for a high security margin -- "
                 "lower them for faster recovery, or raise further for even more margin.",
            foreground="#666", font=("", 8), wraplength=380, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        # self.argon2_custom_frame stays unpacked (hidden) until the checkbox above is checked
        row += 1

        # Action button
        self.create_button = ttk.Button(self, text="Create Prime Vault", command=self.on_create)
        self.create_button.grid(row=row, column=0, columnspan=2, pady=(10, 6))
        row += 1

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        row += 1

        self.log_box = scrolledtext.ScrolledText(self, height=10, state="disabled", wrap="word")
        self.log_box.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(row, weight=1)

    def _append_log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self._log_writer.q.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self._poll_log_queue)

    def _on_memorable_toggle(self):
        memorable = bool(self.memorable_var.get())
        if memorable:
            self.strong_words_var.set(False)
        if self.strong_words_check is not None:
            self.strong_words_check.state(["disabled" if memorable else "!disabled"])
        if self.word_length_spinbox is not None:
            self.word_length_spinbox.state(["disabled" if memorable else "!disabled"])

    def _on_strong_words_toggle(self):
        if bool(self.strong_words_var.get()):
            self.memorable_var.set(False)
            self._on_memorable_toggle()

    def _on_argon2_custom_toggle(self):
        if bool(self.argon2_custom_var.get()):
            self.argon2_custom_frame.pack(anchor="w", pady=(4, 2))
        else:
            self.argon2_custom_frame.pack_forget()

    def on_create(self):
        input_path = self.input_entry.get().strip()
        if not input_path:
            messagebox.showerror(APP_TITLE, "Choose a file or folder to encrypt first.")
            return
        if not os.path.exists(input_path):
            messagebox.showerror(APP_TITLE, f"Input path not found:\n{input_path}")
            return

        memorable = bool(self.memorable_var.get())
        try:
            trustees = int(self.trustees_var.get())
            threshold = int(self.threshold_var.get())
            word_count = int(self.word_count_var.get())
            word_length = None if memorable else int(self.word_length_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror(APP_TITLE, "Trustees, threshold, word length, and word count must be numbers.")
            return
        strong_words = bool(self.strong_words_var.get()) and not memorable

        if threshold < 2:
            messagebox.showerror(APP_TITLE, "Threshold (D) must be at least 2: the prime codeword plus >= 1 from the pool.")
            return
        if trustees < 2:
            messagebox.showerror(APP_TITLE, "Total trustees (T) must be at least 2: 1 prime + >= 1 pool trustee.")
            return
        if threshold > trustees:
            messagebox.showerror(APP_TITLE, "Threshold (D) cannot exceed total trustees (T).")
            return
        if not memorable and word_length < 3:
            messagebox.showerror(APP_TITLE, "Codeword length should be at least 3 characters.")
            return

        dictionary_path = self.dict_entry.get().strip() or None
        outdir = self.outdir_entry.get().strip() or None

        choice = self.kdf_var.get()
        if choice == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
            messagebox.showerror(
                APP_TITLE,
                "Argon2id was selected, but 'argon2-cffi' isn't installed.\n\n"
                "Install it (pip install argon2-cffi) or choose a different "
                "KDF option.",
            )
            return
        if choice == "auto":
            if kdfmod.ARGON2_AVAILABLE:
                kdf_method = "argon2id"
            else:
                proceed = messagebox.askyesno(
                    APP_TITLE,
                    "'argon2-cffi' is not installed, so Argon2id (the stronger, "
                    "memory-hard key derivation function) isn't available.\n\n"
                    "Shard protection would fall back to PBKDF2-HMAC-SHA256, "
                    "which is weaker against GPU/ASIC-parallel offline guessing "
                    "of your codewords.\n\n"
                    "For stronger protection, install argon2-cffi and restart "
                    "this program.\n\n"
                    "Proceed with the PBKDF2 fallback anyway?",
                )
                if not proceed:
                    return
                kdf_method = "pbkdf2"
        else:
            kdf_method = choice

        if kdf_method == "argon2id" and bool(self.argon2_custom_var.get()):
            try:
                argon2_overrides = {
                    "time_cost": int(self.argon2_time_cost_var.get()),
                    "memory_cost_kib": int(self.argon2_memory_cost_var.get()),
                    "parallelism": int(self.argon2_parallelism_var.get()),
                }
            except (tk.TclError, ValueError):
                messagebox.showerror(APP_TITLE, "Argon2id time cost, memory cost, and parallelism must be numbers.")
                return
            kdf_params = vault_core.resolve_kdf_params(kdf_method, argon2_overrides)
        else:
            kdf_params = kdfmod.default_params(kdf_method)

        self._running = True
        self.create_button.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")
        self.progress.start(12)
        self.after(100, self._poll_log_queue)

        def worker():
            try:
                result = vault_core_prime.create_vault_prime(
                    input_path=input_path,
                    trustees=trustees,
                    threshold=threshold,
                    word_length=word_length,
                    word_count=word_count,
                    dictionary_path=dictionary_path,
                    outdir=outdir,
                    kdf_method=kdf_method,
                    kdf_params=kdf_params,
                    randomize_case=strong_words,
                    digit_suffix_len=3 if strong_words else 0,
                    log=self._log_writer,
                )
                self._log_writer(f"Wrote {len(result['trustee_files'])} trustee codeword files to: {result['words_dir']}")
                self.after(0, lambda: self._on_create_done(result))
            except (ValueError, vault_core_prime.VaultError) as e:
                msg = str(e)
                self.after(0, lambda: self._on_create_error(msg))
            except Exception as e:  # noqa: BLE001 - surface anything unexpected to the user
                msg = f"Unexpected error: {e}"
                self.after(0, lambda: self._on_create_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self):
        self._running = False
        self.progress.stop()
        self.create_button.configure(state="normal")

    def _on_create_done(self, result):
        self._finish()
        messagebox.showinfo(
            APP_TITLE,
            "Prime vault created successfully.\n\n"
            f"Container file:\n{result['krypt_path']}\n\n"
            f"Trustee codewords:\n{result['words_dir']}\n\n"
            f"trustee_prime.txt is MANDATORY -- recovery always needs it.\n"
            "The remaining trustee_N.txt files are the interchangeable pool.\n\n"
            "Distribute each file to one trustee out-of-band, then delete "
            "these files from this machine.",
        )

    def _on_create_error(self, message):
        self._finish()
        messagebox.showerror(APP_TITLE, f"Vault creation failed:\n\n{message}")


class RecoverPrimeTab(ttk.Frame):
    """Same flow as RecoverTab, but drives vault_core_prime.match_codewords_prime
    / reconstruct_and_decrypt_prime. Codewords can be entered in any order --
    which one turns out to be the prime trustee's is detected automatically."""

    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.columnconfigure(1, weight=1)
        self.metadata = None
        self.word_entries = []
        self._log_writer = LogQueueWriter()
        self._running = False
        self._build()

    def _build(self):
        row = 0

        krypt_frame = ttk.Frame(self)
        self.krypt_entry = ttk.Entry(krypt_frame)
        self.krypt_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(krypt_frame, text="Browse...", width=10,
                   command=self.on_browse_krypt).pack(side="left", padx=2)
        ttk.Label(self, text=".krypt file").grid(row=row, column=0, sticky="w", pady=3)
        krypt_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.load_button = ttk.Button(self, text="Load Vault Info", command=self.on_load)
        self.load_button.grid(row=row, column=0, columnspan=2, pady=(2, 8))
        row += 1

        self.info_label = ttk.Label(self, text="No vault loaded yet.", foreground="#444",
                                     wraplength=440, justify="left")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        self.words_container = ttk.LabelFrame(self, text="Codewords (any order -- the prime one is detected automatically)")
        self.words_container.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.columnconfigure(1, weight=1)
        row += 1

        out_frame = ttk.Frame(self)
        self.outdir_entry = ttk.Entry(out_frame)
        self.outdir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_frame, text="Browse...", width=10,
                   command=lambda: browse_dir(self.outdir_entry)).pack(side="left", padx=2)
        ttk.Label(self, text="Output folder").grid(row=row, column=0, sticky="w", pady=3)
        out_frame.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.recover_button = ttk.Button(self, text="Recover Vault", command=self.on_recover, state="disabled")
        self.recover_button.grid(row=row, column=0, columnspan=2, pady=(10, 6))
        row += 1

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        row += 1

        self.log_box = scrolledtext.ScrolledText(self, height=8, state="disabled", wrap="word")
        self.log_box.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(row, weight=1)

    def on_browse_krypt(self):
        browse_file(self.krypt_entry, filetypes=(("VaultTool container", "*.krypt"), ("All files", "*.*")))

    def _append_log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self._log_writer.q.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self._poll_log_queue)

    def on_load(self):
        path = self.krypt_entry.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror(APP_TITLE, "Choose a valid .krypt file first.")
            return
        try:
            metadata = vault_core_prime.peek_metadata(path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Couldn't read this file as a shardic-prime vault:\n\n{e}")
            return

        self.metadata = metadata

        threshold = metadata["threshold"]
        pool_threshold = metadata["pool_threshold"]
        pool_size = metadata["pool_size"]
        total = metadata["trustees_total"]
        kdf_method = metadata.get("kdf", "pbkdf2")

        info_text = (
            f"This vault needs the prime trustee's codeword plus {pool_threshold} "
            f"of {pool_size} pool codewords ({threshold} total, of {total} trustees). "
            f"KDF: {kdf_method}."
        )
        if kdf_method == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
            info_text += "\n⚠ argon2-cffi is not installed -- install it before recovering this vault."
        self.info_label.configure(text=info_text)

        for child in self.words_container.winfo_children():
            child.destroy()
        self.word_entries = []
        for i in range(threshold):
            ttk.Label(self.words_container, text=f"Codeword {i + 1}:").grid(row=i, column=0, sticky="w", padx=6, pady=2)
            entry = ttk.Entry(self.words_container, show="•")
            entry.grid(row=i, column=1, sticky="ew", padx=6, pady=2)
            self.word_entries.append(entry)
        self.words_container.columnconfigure(1, weight=1)

        can_recover = not (kdf_method == "argon2id" and not kdfmod.ARGON2_AVAILABLE)
        self.recover_button.configure(state="normal" if can_recover else "disabled")

    def on_recover(self):
        if self.metadata is None:
            messagebox.showerror(APP_TITLE, "Load a vault first.")
            return
        path = self.krypt_entry.get().strip()

        codewords = [e.get() for e in self.word_entries]
        if all(not w.strip() for w in codewords):
            messagebox.showerror(APP_TITLE, "Enter at least the required number of codewords, including the prime trustee's.")
            return

        outdir = self.outdir_entry.get().strip() or None

        self._running = True
        self.recover_button.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")
        self.progress.start(12)
        self.after(100, self._poll_log_queue)

        def worker():
            try:
                metadata, ciphertext = vault_core_prime.krypt_container.read_krypt(path)
                mask, pool_shards, unmatched = vault_core_prime.match_codewords_prime(codewords, metadata)
                if unmatched:
                    self._log_writer(
                        f"{len(unmatched)} entered codeword(s) didn't match any shard and were skipped."
                    )
                result = vault_core_prime.reconstruct_and_decrypt_prime(
                    metadata, ciphertext, mask, pool_shards, outdir=outdir, log=self._log_writer
                )
                self.after(0, lambda: self._on_recover_done(result))
            except vault_core_prime.VaultError as e:
                msg = str(e)
                self.after(0, lambda: self._on_recover_error(msg))
            except Exception as e:  # noqa: BLE001
                msg = f"Unexpected error: {e}"
                self.after(0, lambda: self._on_recover_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self):
        self._running = False
        self.progress.stop()
        self.recover_button.configure(state="normal")

    def _on_recover_done(self, result):
        self._finish()
        messagebox.showinfo(APP_TITLE, f"Recovery successful.\n\nExtracted to:\n{result['outdir']}")

    def _on_recover_error(self, message):
        self._finish()
        messagebox.showerror(APP_TITLE, f"Recovery failed:\n\n{message}")


class ShardicPrimeTab(ttk.Frame):
    """Container tab holding Create/Recover sub-tabs for the shardic-prime
    (mandatory prime trustee) scheme -- kept as its own inner notebook so it
    reads as one distinct add-on alongside the base Create/Recover tabs."""

    def __init__(self, parent):
        super().__init__(parent, padding=4)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        notebook.add(CreatePrimeTab(notebook), text="Create")
        notebook.add(RecoverPrimeTab(notebook), text="Recover")


_TK_NAMED_FONTS = [
    "TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont",
    "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
    "TkIconFont", "TkTooltipFont",
]


def _apply_hidpi_scaling(root):
    """Tk on X11 reports a flat 96 DPI regardless of the desktop's actual
    scaling preference -- unlike GTK/Qt, it won't pick up a 2x HiDPI
    setting on its own, so fonts/widgets render tiny on a scaled desktop.
    Best-effort: match Tk's scaling to Xft.dpi if xrdb reports one;
    silently do nothing otherwise (e.g. on Windows, where Tk already
    queries the real system DPI correctly).

    Tk auto-shrinks its named fonts' point size whenever 'tk scaling'
    changes, to keep their on-screen pixel size constant -- so those
    named fonts (everything not given an explicit font=(...) override)
    need their original point sizes reasserted afterward, or the window
    just gets bigger padding around still-tiny text.
    """
    try:
        output = subprocess.run(
            ["xrdb", "-query"], capture_output=True, text=True, timeout=2
        ).stdout
        dpi = None
        for line in output.splitlines():
            if line.startswith("Xft.dpi:"):
                dpi = float(line.split(":", 1)[1].strip())
                break
        if not dpi:
            return
        original_sizes = {}
        for name in _TK_NAMED_FONTS:
            try:
                original_sizes[name] = tkfont.nametofont(name).actual()["size"]
            except tk.TclError:
                pass
        root.tk.call("tk", "scaling", dpi / 72.0)
        for name, size in original_sizes.items():
            tkfont.nametofont(name).configure(size=size)
    except Exception:
        pass


def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    _apply_hidpi_scaling(root)

    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    create_tab = CreateTab(notebook)
    recover_tab = RecoverTab(notebook)
    shardic_prime_tab = ShardicPrimeTab(notebook)
    notebook.add(create_tab, text="Create Vault")
    notebook.add(recover_tab, text="Recover Vault")
    notebook.add(shardic_prime_tab, text="Shardic-Prime")

    # Size to the actual rendered content rather than a guessed constant --
    # theme/font rendering (e.g. the AppImage's bundled Tk) can need more
    # room than a fixed default accounts for. Cap to the screen so it never
    # opens larger than the display.
    root.update_idletasks()
    width = min(root.winfo_reqwidth(), int(root.winfo_screenwidth() * 0.9))
    height = min(root.winfo_reqheight(), int(root.winfo_screenheight() * 0.9))
    root.geometry(f"{width}x{height}")
    root.minsize(width, height)

    root.mainloop()


if __name__ == "__main__":
    main()
