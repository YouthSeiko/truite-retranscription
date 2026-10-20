from __future__ import annotations

import json
import os
import queue
import sys
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from jobs import get_queue
from transcriber import (
    AUDIO_EXTENSIONS,
    LANGUAGES,
    MODEL_SIZES,
    PROJECT_ROOT,
    Transcriber,
)

try:
    import tkinterdnd2

    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

APP_NAME = "Truite Retranscription"
CONFIG_PATH = PROJECT_ROOT / "config.json"

ACCENT = "#22B8CF"
ACCENT_DARK = "#1596AC"
BG = "#0A1929"
CARD = "#122A42"
CARD_ALT = "#1B3A58"
TEXT = "#EAF6FF"
MUTED = "#7FA8C9"
SUCCESS = "#2DD4A7"
ERROR = "#F87171"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


if DND_AVAILABLE:

    class _Root(ctk.CTk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                tkinterdnd2.TkinterDnD.require(self)
            except Exception:
                pass

else:
    _Root = ctk.CTk


class TruiteRetranscriptionApp(_Root):
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title(APP_NAME)
        self.geometry("880x760")
        self.minsize(760, 640)
        self.configure(fg_color=BG)
        try:
            self.iconbitmap(str(PROJECT_ROOT / "app" / "icon.ico"))
        except Exception:
            pass

        self.files: list[Path] = []
        self.job_queue = get_queue()
        self.messages: queue.Queue = self.job_queue.events
        self.current_job_id: str | None = None
        self.remote = None
        self.remote_win = None
        self.last_result: str = ""
        self.last_sources: list[Path] = []

        config = load_config()
        self.model_var = ctk.StringVar(value=config.get("model", "small"))
        self.lang_var = ctk.StringVar(value=config.get("language", "Auto (detection)"))
        self.auto_save_var = ctk.BooleanVar(value=config.get("auto_save", True))

        self._build_ui()
        self._bind_drop()
        self.after(100, self._poll_messages)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 6))
        header.grid_columnconfigure(1, weight=1)

        _bundle = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else Path("")
        logo_path = next(
            (p for p in (_bundle / "app" / "logo.png", PROJECT_ROOT / "app" / "logo.png") if p.exists()),
            None,
        )
        if logo_path:
            try:
                from PIL import Image as PILImage

                logo = ctk.CTkImage(
                    light_image=PILImage.open(logo_path),
                    dark_image=PILImage.open(logo_path),
                    size=(56, 56),
                )
                ctk.CTkLabel(header, image=logo, text="").grid(
                    row=0, column=0, rowspan=2, padx=(0, 14)
                )
            except Exception:
                pass

        ctk.CTkLabel(
            header,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            header,
            text="Transcription audio vers texte, entierement en local",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 4))

        self.remote_btn = ctk.CTkButton(
            header,
            text="Mode distant",
            width=124, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=CARD_ALT, hover_color="#2A4D70",
            text_color=TEXT, border_width=1, border_color="#2A4D70",
            corner_radius=10,
            command=self.toggle_remote,
        )
        self.remote_btn.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

        files_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        files_card.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        files_card.grid_columnconfigure(0, weight=1)

        files_head = ctk.CTkFrame(files_card, fg_color=CARD)
        files_head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        files_head.grid_columnconfigure(0, weight=1)

        self.files_label = ctk.CTkLabel(
            files_head,
            text="Fichiers audio (MP3, WAV, M4A, FLAC...)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        self.files_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            files_head, text="+ Ajouter", width=100, height=32,
            fg_color=ACCENT, hover_color=ACCENT_DARK, command=self.add_files,
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            files_head, text="Vider", width=70, height=32,
            fg_color=CARD_ALT, hover_color="#2A4D70", text_color=MUTED,
            border_width=1, border_color="#2A4D70", command=self.clear_files,
        ).grid(row=0, column=2, padx=(8, 0))

        self.drop_zone = ctk.CTkFrame(
            files_card, fg_color=CARD_ALT, corner_radius=10,
            border_width=1, border_color="#2A4D70",
        )
        self.drop_zone.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 6))
        self.drop_zone.grid_columnconfigure(0, weight=1)

        self.drop_label = ctk.CTkLabel(
            self.drop_zone,
            text="Deposez vos fichiers ici, ou cliquez sur Ajouter",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
        )
        self.drop_label.grid(row=0, column=0, padx=16, pady=16)

        self.file_list = ctk.CTkTextbox(
            files_card, height=96, fg_color=CARD_ALT,
            text_color=TEXT, font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=10, border_width=1, border_color="#2A4D70",
            state="disabled",
        )
        self.file_list.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        settings = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        settings.grid(row=2, column=0, sticky="ew", padx=24, pady=8)
        settings.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            settings, text="Modele", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))
        model_menu = ctk.CTkOptionMenu(
            settings, variable=self.model_var, values=list(MODEL_SIZES.keys()),
            width=180, fg_color=CARD_ALT, button_color=ACCENT,
            button_hover_color=ACCENT_DARK, command=self._on_model_change,
        )
        model_menu.grid(row=1, column=0, sticky="w", padx=16, pady=(4, 6))
        self.model_info = ctk.CTkLabel(
            settings, text=MODEL_SIZES[self.model_var.get()],
            font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w",
        )
        self.model_info.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            settings, text="Langue", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT, anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=16, pady=(14, 0))
        ctk.CTkOptionMenu(
            settings, variable=self.lang_var, values=list(LANGUAGES.keys()),
            width=180, fg_color=CARD_ALT, button_color=ACCENT,
            button_hover_color=ACCENT_DARK,
        ).grid(row=1, column=1, sticky="w", padx=16, pady=(4, 6))
        ctk.CTkLabel(
            settings, text="Auto = detection automatique",
            font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w",
        ).grid(row=2, column=1, sticky="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            settings, text="Sortie", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT, anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=16, pady=(14, 0))
        ctk.CTkCheckBox(
            settings, text="Sauvegarder en .txt automatiquement",
            variable=self.auto_save_var, fg_color=ACCENT,
            font=ctk.CTkFont(size=12), text_color=TEXT,
        ).grid(row=1, column=2, sticky="w", padx=16, pady=(4, 6))
        ctk.CTkLabel(
            settings, text="Dans un dossier transcriptions/",
            font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w",
        ).grid(row=2, column=2, sticky="w", padx=16, pady=(0, 14))

        action = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        action.grid(row=3, column=0, sticky="ew", padx=24, pady=4)
        action.grid_columnconfigure(1, weight=1)

        self.run_btn = ctk.CTkButton(
            action, text="Lancer la retranscription", height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_DARK, corner_radius=10,
            command=self.toggle_run,
        )
        self.run_btn.grid(row=0, column=0, padx=(0, 12))

        self.progress = ctk.CTkProgressBar(action, height=14, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.grid(row=0, column=1, sticky="ew")

        self.status_label = ctk.CTkLabel(
            action, text="Pret", font=ctk.CTkFont(size=12),
            text_color=MUTED, width=220, anchor="e",
        )
        self.status_label.grid(row=0, column=2, padx=(12, 0))

        result_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        result_card.grid(row=4, column=0, sticky="nsew", padx=24, pady=8)
        result_card.grid_columnconfigure(0, weight=1)
        result_card.grid_rowconfigure(1, weight=1)

        result_head = ctk.CTkFrame(result_card, fg_color=CARD)
        result_head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        result_head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            result_head, text="Resultat", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(result_head, fg_color=CARD)
        btns.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btns, text="Copier", width=76, height=30, fg_color=CARD_ALT,
            hover_color="#2A4D70", text_color=TEXT, border_width=1,
            border_color="#2A4D70", command=self.copy_result,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btns, text="Enregistrer", width=96, height=30, fg_color=CARD_ALT,
            hover_color="#2A4D70", text_color=TEXT, border_width=1,
            border_color="#2A4D70", command=self.save_result,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btns, text="Ouvrir le dossier", width=120, height=30, fg_color=CARD_ALT,
            hover_color="#2A4D70", text_color=TEXT, border_width=1,
            border_color="#2A4D70", command=self.open_output_folder,
        ).pack(side="left")

        self.result_box = ctk.CTkTextbox(
            result_card, fg_color=CARD_ALT, text_color=TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=10, border_width=1, border_color="#2A4D70",
            wrap="word",
        )
        self.result_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 6))

        self.log_box = ctk.CTkTextbox(
            result_card, height=76, fg_color="#0D2137",
            text_color=MUTED, font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8, border_width=1, border_color="#2A4D70",
            state="disabled",
        )
        self.log_box.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def _bind_drop(self) -> None:
        if not DND_AVAILABLE:
            return
        for widget in (self, self.drop_zone, self.drop_label, self.file_list):
            try:
                widget.drop_target_register(tkinterdnd2.DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event) -> None:
        for item in self._parse_drop(event.data.strip()):
            self._add_path(Path(item))

    @staticmethod
    def _parse_drop(data: str) -> list[str]:
        results: list[str] = []
        current = ""
        in_braces = False
        for char in data:
            if char == "{":
                in_braces = True
            elif char == "}":
                in_braces = False
                if current:
                    results.append(current)
                    current = ""
            elif char == " " and not in_braces:
                if current:
                    results.append(current)
                    current = ""
            else:
                current += char
        if current:
            results.append(current)
        return results

    def _add_path(self, path: Path) -> None:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.suffix.lower() in AUDIO_EXTENSIONS:
                    self._add_file(child)
        elif path.suffix.lower() in AUDIO_EXTENSIONS:
            self._add_file(path)
        self._refresh_file_list()

    def _add_file(self, path: Path) -> None:
        if path not in self.files:
            self.files.append(path)

    def add_files(self) -> None:
        initial = str(self.files[-1].parent) if self.files else str(Path.home())
        picked = filedialog.askopenfilenames(
            title="Choisir des fichiers audio",
            initialdir=initial,
            filetypes=[
                ("Fichiers audio", "*.mp3 *.wav *.m4a *.m4b *.flac *.ogg *.opus *.aac *.wma *.mp4 *.mkv *.webm *.aiff"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        for item in picked:
            self._add_file(Path(item))
        self._refresh_file_list()

    def clear_files(self) -> None:
        self.files.clear()
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        self.file_list.configure(state="normal")
        self.file_list.delete("1.0", "end")
        if not self.files:
            self.file_list.insert("end", "Aucun fichier pour le moment.")
            self.drop_label.configure(text="Deposez vos fichiers ici, ou cliquez sur Ajouter")
        else:
            for index, path in enumerate(self.files, 1):
                self.file_list.insert("end", f"{index:>3}. {path.name}   [{path.parent}]\n")
            self.drop_label.configure(
                text=f"{len(self.files)} fichier(s) en attente de retranscription"
            )
        self.file_list.configure(state="disabled")

    def _on_model_change(self, value: str) -> None:
        self.model_info.configure(text=MODEL_SIZES.get(value, ""))
        config = load_config()
        config["model"] = value
        save_config(config)

    def log(self, message: str) -> None:
        self.messages.put(("log", message))

    def toggle_run(self) -> None:
        current = self.job_queue.jobs.get(self.current_job_id) if self.current_job_id else None
        if current is not None and current.active:
            self.job_queue.cancel(current.id)
            self.run_btn.configure(state="disabled", text="Arret en cours...")
            return
        if not self.files:
            messagebox.showwarning(APP_NAME, "Ajoutez au moins un fichier audio.")
            return
        self.last_result = ""
        self.last_sources = list(self.files)
        self.result_box.delete("1.0", "end")
        self.run_btn.configure(text="Annuler", fg_color=ERROR, hover_color="#DA3633")
        self.progress.set(0)
        self.status_label.configure(text="Preparation...")
        config = load_config()
        config["model"] = self.model_var.get()
        config["language"] = self.lang_var.get()
        config["auto_save"] = self.auto_save_var.get()
        save_config(config)
        submitted = self.job_queue.submit(
            list(self.files),
            self.model_var.get(),
            LANGUAGES.get(self.lang_var.get()),
            self.auto_save_var.get(),
            origin="local",
        )
        self.current_job_id = submitted.id

    def toggle_remote(self) -> None:
        from server import DEFAULT_PORT, RemoteServer, password_defined, set_password

        if self.remote is not None:
            self.remote.stop()
            self.remote = None
            self.remote_btn.configure(
                text="Mode distant",
                fg_color=CARD_ALT, hover_color="#2A4D70",
                text_color=TEXT, border_width=1, border_color="#2A4D70",
            )
            if self.remote_win is not None:
                try:
                    self.remote_win.destroy()
                except Exception:
                    pass
                self.remote_win = None
            self._append_log("Mode distant desactive.")
            return

        if password_defined():
            dialog = ctk.CTkInputDialog(
                title=f"{APP_NAME} — Mode distant",
                text="Nouveau mot de passe (laisser vide pour garder l'actuel) :",
            )
            password = (dialog.get_input() or "").strip()
            if password and len(password) < 8:
                messagebox.showwarning(APP_NAME, "Le mot de passe doit faire au moins 8 caracteres.")
                return
            if password:
                set_password(password)
        else:
            dialog = ctk.CTkInputDialog(
                title=f"{APP_NAME} — Mode distant",
                text="Definition du mot de passe d'acces distant (8 caracteres minimum).\n"
                "Vos appareils devront le saisir pour utiliser ce PC.",
            )
            password = (dialog.get_input() or "").strip()
            if not password:
                return
            if len(password) < 8:
                messagebox.showwarning(APP_NAME, "Le mot de passe doit faire au moins 8 caracteres.")
                return
            set_password(password)

        server = RemoteServer(self.job_queue, DEFAULT_PORT)
        try:
            server.start()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Impossible de demarrer le serveur distant.\n{exc}")
            return
        self.remote = server
        self.remote_btn.configure(
            text="Distant : actif",
            fg_color=SUCCESS, hover_color="#25B491",
            text_color="#04212B", border_width=0,
        )
        urls = server.urls()
        self._append_log(f"Mode distant actif : {urls['lan']}")
        self._show_remote_window()

    def _show_remote_window(self) -> None:
        from server import open_firewall

        server = self.remote
        if server is None:
            return
        if self.remote_win is not None:
            try:
                self.remote_win.destroy()
            except Exception:
                pass

        win = ctk.CTkToplevel(self)
        win.title(f"{APP_NAME} — Mode distant")
        win.geometry("440x640")
        win.minsize(440, 560)
        win.configure(fg_color=BG)
        win.transient(self)
        self.remote_win = win
        win.grid_columnconfigure(0, weight=1)

        urls = server.urls()

        ctk.CTkLabel(
            win, text="Mode distant actif",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT,
        ).grid(row=0, column=0, pady=(22, 2), padx=24, sticky="w")
        ctk.CTkLabel(
            win,
            text="Scannez le QR code ou saisissez l'adresse dans un navigateur.",
            font=ctk.CTkFont(size=13), text_color=MUTED, wraplength=380, justify="left",
        ).grid(row=1, column=0, padx=24, sticky="w")

        qr_image = self._make_qr_image(urls["lan"])
        if qr_image:
            qr_frame = ctk.CTkFrame(win, fg_color=CARD, corner_radius=14)
            qr_frame.grid(row=2, column=0, padx=24, pady=16, sticky="ew")
            qr_label = ctk.CTkLabel(qr_frame, image=qr_image, text="")
            qr_label.image = qr_image
            qr_label.pack(padx=20, pady=16)
            ctk.CTkLabel(
                qr_frame, text="Sur le meme Wi-Fi, scannez avec l'appareil photo.",
                font=ctk.CTkFont(size=12), text_color=MUTED,
            ).pack(pady=(0, 14))

        links = ctk.CTkFrame(win, fg_color=CARD, corner_radius=14)
        links.grid(row=3, column=0, padx=24, sticky="ew")
        links.grid_columnconfigure(0, weight=1)

        row = 0
        for label_text, url in (("Reseau local", urls["lan"]), ("Tailscale", urls["tailscale"])):
            if url is None:
                continue
            ctk.CTkLabel(
                links, text=label_text, font=ctk.CTkFont(size=12, weight="bold"),
                text_color=MUTED, anchor="w",
            ).grid(row=row, column=0, padx=16, pady=(12 if row == 0 else 4, 0), sticky="w")
            entry_row = ctk.CTkFrame(links, fg_color=CARD)
            entry_row.grid(row=row + 1, column=0, padx=12, pady=4, sticky="ew")
            entry_row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                entry_row, text=url, font=ctk.CTkFont(family="Consolas", size=13),
                text_color=ACCENT, anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=4)
            ctk.CTkButton(
                entry_row, text="Copier", width=76, height=28, fg_color=CARD_ALT,
                hover_color="#2A4D70", text_color=TEXT, border_width=1,
                border_color="#2A4D70",
                command=lambda u=url: self._copy_text(u),
            ).grid(row=0, column=1, padx=(6, 0))
            row += 2

        if urls["tailscale"] is None:
            hint = ctk.CTkLabel(
                links,
                text="Hors de ce reseau ? Installez Tailscale (gratuit) sur ce PC\n"
                "et vos appareils : aucun port a ouvrir, tout reste chiffre.",
                font=ctk.CTkFont(size=11.5), text_color=MUTED, justify="left", wraplength=360,
            )
            hint.grid(row=row, column=0, padx=16, pady=(10, 4), sticky="w")

        ctk.CTkButton(
            win, text="Autoriser le port au pare-feu Windows", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_DARK, corner_radius=10,
            command=lambda: self._open_firewall(server.port),
        ).grid(row=4, column=0, padx=24, pady=(14, 4), sticky="ew")

        self.remote_status = ctk.CTkLabel(
            win,
            text=f"Serveur actif sur le port {server.port} — arretez-le depuis la fenetre principale.",
            font=ctk.CTkFont(size=11.5), text_color=MUTED, wraplength=380, justify="left",
        )
        self.remote_status.grid(row=5, column=0, padx=24, pady=(0, 18), sticky="w")

    @staticmethod
    def _make_qr_image(url: str, size: int = 176):
        try:
            import qrcode

            qr = qrcode.QRCode(border=2, box_size=8)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0A1929", back_color="white").convert("RGB")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except Exception:
            return None

    def _copy_text(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self._append_log(f"Adresse copiee : {text}")

    def _open_firewall(self, port: int) -> None:
        from server import open_firewall

        try:
            open_firewall(port)
            self._append_log("Demande d'autorisation du pare-feu (UAC)...")
            if self.remote_win is not None and hasattr(self, "remote_status"):
                self.remote_status.configure(
                    text="Autorisation demandee : validez la fenetre Windows (UAC)."
                )
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Impossible de modifier le pare-feu.\n{exc}")

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "status":
                    self.status_label.configure(text=payload)
                elif kind == "progress":
                    self.progress.set(float(payload))
                elif kind == "result":
                    self.result_box.delete("1.0", "end")
                    self.result_box.insert("end", payload)
                elif kind == "error":
                    self._append_log("ERREUR : " + payload.replace("\n", " | "))
                    messagebox.showerror(APP_NAME, "La transcription a echoue. Details dans le journal.")
                elif kind == "finished":
                    self.progress.set(1.0)
                    self.run_btn.configure(
                        text="Lancer la retranscription",
                        fg_color=ACCENT, hover_color=ACCENT_DARK, state="normal",
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _append_log(self, message: str) -> None:
        from datetime import datetime

        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{stamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def copy_result(self) -> None:
        text = self.result_box.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._append_log("Texte copie dans le presse-papiers.")

    def save_result(self) -> None:
        text = self.result_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP_NAME, "Aucun resultat a enregistrer.")
            return
        initial = str(self.last_sources[0].with_suffix(".txt")) if self.last_sources else str(Path.home() / "transcription.txt")
        target = filedialog.asksaveasfilename(
            title="Enregistrer la transcription",
            initialfile=Path(initial).name,
            defaultextension=".txt",
            filetypes=[("Texte", "*.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return
        Path(target).write_text(text + "\n", encoding="utf-8")
        self._append_log(f"Enregistre : {target}")

    def open_output_folder(self) -> None:
        folder: Path | None = None
        if self.last_sources:
            candidate = self.last_sources[0].parent / "transcriptions"
            if candidate.exists():
                folder = candidate
            else:
                folder = self.last_sources[0].parent
        if folder is None:
            folder = PROJECT_ROOT / "transcriptions"
            folder.mkdir(exist_ok=True)
        os.startfile(str(folder))


def _cli(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog=APP_NAME, add_help=True)
    sub = parser.add_subparsers(dest="command")
    warmup = sub.add_parser("warmup", help="telecharger le modele IA en local")
    warmup.add_argument("--model", default="small", choices=list(MODEL_SIZES.keys()))
    transcribe = sub.add_parser("transcribe", help="transcrire un fichier audio en ligne de commande")
    transcribe.add_argument("audio")
    transcribe.add_argument("--model", default="small", choices=list(MODEL_SIZES.keys()))
    transcribe.add_argument("--language", default=None)
    transcribe.add_argument("--output", default=None, help="fichier .txt de sortie")
    serve = sub.add_parser("serve", help="demarrer le serveur d'acces distant")
    serve.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)

    if args.command == "warmup":
        engine = Transcriber(args.model)
        engine.load()
        print(f"Modele {args.model} pret.")
        return 0

    if args.command == "transcribe":
        source = Path(args.audio).expanduser().resolve()
        if not source.exists():
            print(f"Fichier introuvable : {source}")
            return 1
        engine = Transcriber(args.model)
        engine.load()
        segments, info = engine.transcribe_file(source, language=args.language)
        text = "\n".join(seg.text for seg in segments if seg.text).strip()
        target = Path(args.output).expanduser().resolve() if args.output else source.with_suffix(".txt")
        target.write_text(text + "\n", encoding="utf-8")
        print(f"Ecrit : {target}")
        return 0

    if args.command == "serve":
        import time as _time

        from server import DEFAULT_PORT, RemoteServer, password_defined

        if not password_defined():
            print("Mode distant non active : definissez d'abord le mot de passe depuis la fenetre principale.")
            return 1
        server = RemoteServer(port=args.port or DEFAULT_PORT)
        server.start()
        urls = server.urls()
        print(f"Serveur actif : {urls['lan']}")
        if urls["tailscale"]:
            print(f"Tailscale    : {urls['tailscale']}")
        try:
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
        return 0

    parser.print_help()
    return 0


def main() -> None:
    if len(sys.argv) > 1:
        raise SystemExit(_cli(sys.argv[1:]))
    app = TruiteRetranscriptionApp()
    app.mainloop()


if __name__ == "__main__":
    main()
