import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import websockets
except ImportError:
    print("Устанавливаю библиотеку websockets...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

SERVER_URL = "wss://notepad-server-gymw.onrender.com"

BG      = "#1c1c28"
PANEL   = "#14141f"
SIDE    = "#111119"
EDBG    = "#20202e"
BORDER  = "#2c2c42"
SEL     = "#28283c"
TXT     = "#d0d8f8"
MUTED   = "#52566e"
ACCENT  = "#6e9ef5"
PURPLE  = "#b08af0"
GREEN   = "#7ec86a"
RED     = "#f07070"
GOLD    = "#f0c060"
CARD    = "#1a1a28"

F_UI    = ("Segoe UI", 10)
F_BOLD  = ("Segoe UI", 10, "bold")
F_HEAD  = ("Segoe UI", 14, "bold")
F_MONO  = ("Consolas", 11)
F_SMALL = ("Segoe UI", 9)
F_BIG   = ("Segoe UI", 22, "bold")


def is_local_server_up():
    if "localhost" not in SERVER_URL and "127.0.0.1" not in SERVER_URL:
        return True
    try:
        port = int(SERVER_URL.split(":")[-1])
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False
    except Exception:
        return True


def start_local_server():
    if "localhost" not in SERVER_URL and "127.0.0.1" not in SERVER_URL:
        return
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    if not os.path.exists(path):
        return
    subprocess.Popen(
        [sys.executable, path],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )


class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, title="Введите пароль"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        self.geometry("340x160")
        parent.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()  // 2
        py = parent.winfo_y() + parent.winfo_height() // 2
        self.geometry(f"+{px - 170}+{py - 80}")

        tk.Label(self, text=title, font=F_BOLD, bg=BG, fg=TXT).pack(pady=(20, 8))

        self.entry = tk.Entry(self, show="●", font=F_UI, bg=EDBG, fg=TXT,
                              insertbackground=ACCENT, relief="flat", bd=0,
                              highlightthickness=1, highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        self.entry.pack(padx=30, fill="x", ipady=6)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda _: self._ok())

        bf = tk.Frame(self, bg=BG)
        bf.pack(pady=14)

        tk.Button(bf, text="Ок", font=F_UI, bg=ACCENT, fg=BG,
                  relief="flat", bd=0, padx=22, pady=5, cursor="hand2",
                  activebackground="#5580d0", activeforeground=BG,
                  command=self._ok).pack(side="left", padx=6)

        tk.Button(bf, text="Отмена", font=F_UI, bg=BORDER, fg=TXT,
                  relief="flat", bd=0, padx=16, pady=5, cursor="hand2",
                  activebackground=SEL, activeforeground=TXT,
                  command=self.destroy).pack(side="left", padx=6)

        self.wait_window()

    def _ok(self):
        self.result = self.entry.get()
        self.destroy()


class LoginScreen(tk.Frame):
    def __init__(self, master, on_action):
        super().__init__(master, bg=BG)
        self.on_action = on_action
        self._mode     = "login"
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.place(relx=.5, rely=.5, anchor="center")

        tk.Label(wrap, text="БЛОКНОТ", font=F_BIG,
                 bg=BG, fg=ACCENT).pack(pady=(0, 4))

        srv = SERVER_URL.replace("ws://", "").replace("wss://", "")
        tk.Label(wrap, text=f"Сервер: {srv}", font=F_SMALL,
                 bg=BG, fg=MUTED).pack(pady=(0, 16))

        self.lbl_sub = tk.Label(wrap, text="Войдите в аккаунт",
                                font=F_UI, bg=BG, fg=MUTED)
        self.lbl_sub.pack(pady=(0, 18))

        card = tk.Frame(wrap, bg=CARD, padx=36, pady=30)
        card.pack()

        tk.Label(card, text="Логин", font=F_SMALL, bg=CARD, fg=MUTED,
                 anchor="w").pack(fill="x")
        self.e_user = self._entry(card)

        tk.Label(card, text="Пароль", font=F_SMALL, bg=CARD, fg=MUTED,
                 anchor="w").pack(fill="x", pady=(10, 0))
        self.e_pass = self._entry(card, show="●")

        self.lbl_err = tk.Label(card, text="", font=F_SMALL, bg=CARD, fg=RED)
        self.lbl_err.pack(pady=(8, 0))

        self.btn_main = tk.Button(
            card, text="Войти", font=F_BOLD, bg=ACCENT, fg=BG,
            relief="flat", bd=0, pady=8, cursor="hand2",
            activebackground="#5580d0", activeforeground=BG,
            command=self._submit
        )
        self.btn_main.pack(fill="x", pady=(10, 0))

        self.btn_toggle = tk.Button(
            card, text="Нет аккаунта? Зарегистрироваться",
            font=F_SMALL, bg=CARD, fg=MUTED, relief="flat", bd=0,
            cursor="hand2", activebackground=CARD, activeforeground=ACCENT,
            command=self._toggle
        )
        self.btn_toggle.pack(pady=(8, 0))

        self.e_pass.bind("<Return>", lambda _: self._submit())

    def _entry(self, parent, show=""):
        e = tk.Entry(parent, font=F_UI, bg=EDBG, fg=TXT,
                     insertbackground=ACCENT, show=show,
                     relief="flat", bd=0, width=28,
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT)
        e.pack(ipady=7, pady=(2, 0))
        return e

    def _toggle(self):
        if self._mode == "login":
            self._mode = "register"
            self.lbl_sub.config(text="Создайте аккаунт")
            self.btn_main.config(text="Зарегистрироваться")
            self.btn_toggle.config(text="Уже есть аккаунт? Войти")
        else:
            self._mode = "login"
            self.lbl_sub.config(text="Войдите в аккаунт")
            self.btn_main.config(text="Войти")
            self.btn_toggle.config(text="Нет аккаунта? Зарегистрироваться")
        self.lbl_err.config(text="")

    def _submit(self):
        user = self.e_user.get().strip()
        pw   = self.e_pass.get()
        if not user or not pw:
            self.lbl_err.config(text="Заполните все поля")
            return
        self.btn_main.config(state="disabled")
        self.on_action(self._mode, user, pw, self._on_result)

    def _on_result(self, ok, error=""):
        self.btn_main.config(state="normal")
        if not ok:
            self.lbl_err.config(text=error or "Ошибка")

    def show_message(self, text, color=GREEN):
        self.lbl_err.config(text=text, fg=color)


class NoteScreen(tk.Frame):
    def __init__(self, master, username, is_admin, send_fn):
        super().__init__(master, bg=BG)
        self.username   = username
        self.is_admin   = is_admin
        self._send      = send_fn
        self.cur_id     = None
        self.meta       = {}
        self._ids       = []
        self._quiet     = False
        self._can_edit  = False
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=PANEL, height=46)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="БЛОКНОТ", font=("Segoe UI", 11, "bold"),
                 bg=PANEL, fg=ACCENT).pack(side="left", padx=18)

        name_color = GOLD if self.is_admin else PURPLE
        badge      = " 👑 ADMIN" if self.is_admin else ""
        tk.Label(bar, text=f"· {self.username}{badge}",
                 font=F_UI, bg=PANEL, fg=name_color).pack(side="left", padx=4)

        self.lbl_online = tk.Label(bar, text="", font=F_SMALL,
                                   bg=PANEL, fg=MUTED)
        self.lbl_online.pack(side="right", padx=18)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        side = tk.Frame(body, bg=SIDE, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="Заметки", font=F_BOLD,
                 bg=SIDE, fg=MUTED).pack(anchor="w", padx=14, pady=(14, 6))

        tk.Button(
            side, text="＋  Новая заметка", font=F_UI,
            bg=ACCENT, fg=BG,
            activebackground="#5580d0", activeforeground=BG,
            relief="flat", bd=0, pady=7, cursor="hand2",
            command=self._new_note
        ).pack(fill="x", padx=10, pady=(0, 10))

        lf = tk.Frame(side, bg=SIDE)
        lf.pack(fill="both", expand=True, padx=6)

        sb = tk.Scrollbar(lf, bg=BORDER, troughcolor=SIDE,
                          activebackground=MUTED, relief="flat", width=5)
        sb.pack(side="right", fill="y")

        self.lb = tk.Listbox(
            lf, bg=SIDE, fg=TXT,
            selectbackground=SEL, selectforeground=ACCENT,
            font=F_UI, relief="flat", bd=0,
            highlightthickness=0, activestyle="none",
            yscrollcommand=sb.set
        )
        self.lb.pack(fill="both", expand=True)
        sb.config(command=self.lb.yview)
        self.lb.bind("<<ListboxSelect>>", self._on_select)
        self.lb.bind("<Button-3>", self._ctx_menu)

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        right = tk.Frame(body, bg=BG)
        right.pack(fill="both", expand=True)

        info = tk.Frame(right, bg=BG)
        info.pack(fill="x", padx=20, pady=(16, 0))

        self.lbl_title = tk.Label(info, text="Выберите заметку",
                                  font=F_HEAD, bg=BG, fg=TXT, anchor="w")
        self.lbl_title.pack(fill="x")

        self.lbl_meta = tk.Label(info, text="", font=F_SMALL,
                                 bg=BG, fg=MUTED, anchor="w")
        self.lbl_meta.pack(fill="x", pady=(2, 10))

        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=14)

        ef = tk.Frame(right, bg=BG)
        ef.pack(fill="both", expand=True, padx=14, pady=12)

        esb = tk.Scrollbar(ef, bg=BORDER, troughcolor=EDBG,
                           activebackground=MUTED, relief="flat", width=5)
        esb.pack(side="right", fill="y")

        self.editor = tk.Text(
            ef, bg=EDBG, fg=TXT, insertbackground=ACCENT,
            font=F_MONO, relief="flat", bd=0,
            padx=18, pady=16, wrap="word", undo=True,
            yscrollcommand=esb.set, state="disabled"
        )
        self.editor.pack(fill="both", expand=True)
        esb.config(command=self.editor.yview)
        self.editor.bind("<<Modified>>", self._on_edit)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self.lbl_status = tk.Label(self, text="", font=F_SMALL,
                                   bg=PANEL, fg=MUTED, anchor="w")
        self.lbl_status.pack(fill="x", padx=14, pady=5)

    def set_notes(self, notes_data):
        self.meta = {n["id"]: n for n in notes_data}
        self._refresh_list()

    def _refresh_list(self):
        self._ids = list(self.meta.keys())
        self.lb.delete(0, "end")
        for nid in self._ids:
            n = self.meta[nid]
            lock = " 🔒" if n.get("locked") else ""
            mine = " ·" if n.get("is_mine") else ""
            self.lb.insert("end", f"  {n['title']}{lock}{mine}")

    def set_users(self, users):
        self.lbl_online.config(text=f"● {len(users)} онлайн")

    def status(self, text, color=MUTED):
        self.lbl_status.config(text=text, fg=color)

    def handle(self, m):
        a = m.get("action")

        if a == "notes_updated":
            self.set_notes(m["notes"])
            if self.cur_id and self.cur_id in self.meta:
                try:
                    idx = self._ids.index(self.cur_id)
                    self.lb.selection_set(idx)
                except ValueError:
                    pass

        elif a == "user_joined":
            self.set_users(m.get("users", []))
            self.status(f"{m['username']} вошёл")

        elif a == "user_left":
            self.set_users(m.get("users", []))
            self.status(f"{m['username']} вышел")

        elif a == "note_locked":
            self.status("Заметка защищена паролем", RED)
            dlg = PasswordDialog(self.master, "Пароль заметки")
            if dlg.result is not None:
                self._send({"action": "open_note", "id": m["id"],
                            "note_password": dlg.result})

        elif a == "note_content":
            self.cur_id    = m["id"]
            self._can_edit = m.get("can_edit", False)
            self.lbl_title.config(text=m["title"])
            lock_txt = "  🔒" if m.get("locked") else ""
            edit_txt = "  (только чтение)" if not self._can_edit else ""
            self.lbl_meta.config(text=f"Автор: {m['author']}{lock_txt}{edit_txt}")
            self._set_editor(m["content"])
            self.editor.config(state="normal" if self._can_edit else "disabled")

        elif a == "note_updated":
            if m["id"] in self.meta:
                self.meta[m["id"]]["updated_at"] = m["updated_at"]
            if m["id"] == self.cur_id and self._can_edit:
                self._set_editor(m["content"])
                self.status(f"{m['editor']} редактирует...", PURPLE)

        elif a == "note_deleted":
            self.meta.pop(m["id"], None)
            if self.cur_id == m["id"]:
                self.cur_id = None
                self._can_edit = False
                self.lbl_title.config(text="Заметка удалена")
                self.lbl_meta.config(text="")
                self._set_editor("")
                self.editor.config(state="disabled")

        elif a == "password_set_ok":
            nid = m["id"]
            if nid in self.meta:
                self.meta[nid]["locked"] = m.get("locked", False)
                self._refresh_list()
            txt = "Пароль установлен 🔒" if m.get("locked") else "Пароль снят"
            self.status(txt, GREEN)

        elif a == "error":
            self.status(m.get("text", "Ошибка"), RED)

    def _set_editor(self, text):
        self._quiet = True
        prev_state = self.editor.cget("state")
        self.editor.config(state="normal")
        if self.editor.get("1.0", "end-1c") != text:
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", text)
        self.editor.edit_modified(False)
        self.editor.config(state=prev_state)
        self._quiet = False

    def _on_select(self, _=None):
        sel = self.lb.curselection()
        if not sel or sel[0] >= len(self._ids):
            return
        nid  = self._ids[sel[0]]
        note = self.meta.get(nid, {})
        if note.get("locked") and not self.is_admin:
            dlg = PasswordDialog(self.master, "Пароль заметки")
            if dlg.result is None:
                return
            self._send({"action": "open_note", "id": nid,
                        "note_password": dlg.result})
        else:
            self._send({"action": "open_note", "id": nid})

    def _on_edit(self, _=None):
        if self._quiet or not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        if not self.cur_id or not self._can_edit:
            return
        self._send({"action": "edit_note", "id": self.cur_id,
                    "content": self.editor.get("1.0", "end-1c")})

    def _new_note(self):
        win = tk.Toplevel(self.master)
        win.title("Новая заметка")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.geometry("360x260")
        self.master.update_idletasks()
        wx = self.master.winfo_x() + self.master.winfo_width()  // 2 - 180
        wy = self.master.winfo_y() + self.master.winfo_height() // 2 - 130
        win.geometry(f"+{wx}+{wy}")

        tk.Label(win, text="Новая заметка", font=F_BOLD,
                 bg=BG, fg=TXT).pack(pady=(20, 4))

        card = tk.Frame(win, bg=CARD, padx=24, pady=20)
        card.pack(padx=20, fill="x")

        tk.Label(card, text="Название", font=F_SMALL,
                 bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
        e_title = tk.Entry(card, font=F_UI, bg=EDBG, fg=TXT,
                           insertbackground=ACCENT, relief="flat", bd=0,
                           highlightthickness=1, highlightbackground=BORDER,
                           highlightcolor=ACCENT)
        e_title.pack(fill="x", ipady=6, pady=(2, 10))
        e_title.focus_set()

        tk.Label(card, text="Пароль на заметку (необязательно)", font=F_SMALL,
                 bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
        e_pw = tk.Entry(card, font=F_UI, bg=EDBG, fg=TXT, show="●",
                        insertbackground=ACCENT, relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        highlightcolor=ACCENT)
        e_pw.pack(fill="x", ipady=6, pady=(2, 0))

        def submit():
            title = e_title.get().strip()
            if not title:
                return
            self._send({"action": "create_note", "title": title,
                        "note_password": e_pw.get()})
            win.destroy()

        e_pw.bind("<Return>", lambda _: submit())
        e_title.bind("<Return>", lambda _: e_pw.focus_set())

        tk.Button(win, text="Создать", font=F_BOLD,
                  bg=ACCENT, fg=BG, relief="flat", bd=0,
                  pady=7, cursor="hand2",
                  activebackground="#5580d0", activeforeground=BG,
                  command=submit).pack(fill="x", padx=20, pady=14)

    def _ctx_menu(self, event):
        idx = self.lb.nearest(event.y)
        if idx < 0 or idx >= len(self._ids):
            return
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(idx)
        nid     = self._ids[idx]
        note    = self.meta.get(nid, {})
        title   = note.get("title", "")
        is_mine = note.get("is_mine", False)

        menu = tk.Menu(self.master, tearoff=0, bg=SIDE, fg=TXT,
                       activebackground=SEL, activeforeground=TXT,
                       font=F_UI, bd=0, relief="flat")

        if is_mine or self.is_admin:
            menu.add_command(label="Установить/снять пароль",
                             command=lambda: self._set_note_pw(nid))
            menu.add_separator()
            menu.add_command(label=f"Удалить «{title}»", foreground=RED,
                             command=lambda: self._delete(nid, title))
        else:
            menu.add_command(label="Нет прав для управления", state="disabled")

        menu.tk_popup(event.x_root, event.y_root)

    def _set_note_pw(self, nid):
        dlg = PasswordDialog(self.master, "Новый пароль (или пусто — снять)")
        if dlg.result is not None:
            self._send({"action": "set_note_password", "id": nid,
                        "note_password": dlg.result})

    def _delete(self, nid, title):
        if messagebox.askyesno("Удалить", f"Удалить «{title}»?",
                               parent=self.master):
            self._send({"action": "delete_note", "id": nid})


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Блокнот")
        self.geometry("980x640")
        self.minsize(720, 480)
        self.configure(bg=BG)

        self._ws        = None
        self._loop      = asyncio.new_event_loop()
        self._cb        = None
        self._note_scr  = None
        self._connected = False

        threading.Thread(target=self._loop.run_forever, daemon=True).start()

        self._login_scr = LoginScreen(self, self._on_auth)
        self._login_scr.place(relx=0, rely=0, relwidth=1, relheight=1)

        if "localhost" in SERVER_URL or "127.0.0.1" in SERVER_URL:
            if not is_local_server_up():
                self._login_scr.show_message("Запуск локального сервера...", MUTED)
                start_local_server()
                self.after(1500, self._ws_connect)
            else:
                self.after(100, self._ws_connect)
        else:
            self._login_scr.show_message("Подключение к серверу...", MUTED)
            self.after(100, self._ws_connect)

    def _ws_connect(self):
        asyncio.run_coroutine_threadsafe(self._ws_run(), self._loop)

    async def _ws_run(self):
        try:
            self._ws = await websockets.connect(SERVER_URL, open_timeout=30)
            self._connected = True
            self.after(0, lambda: self._login_scr.show_message(
                "Подключено к серверу", GREEN))
            async for raw in self._ws:
                try:
                    m = json.loads(raw)
                except Exception:
                    continue
                self.after(0, lambda msg=m: self._handle(msg))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._login_scr.show_message(
                f"Не подключиться: {err[:50]}", RED))
            self.after(3000, self._ws_connect)
        finally:
            self._connected = False

    async def _async_send(self, data):
        if self._ws:
            try:
                await self._ws.send(json.dumps(data, ensure_ascii=False))
            except Exception:
                pass

    def _send(self, data):
        asyncio.run_coroutine_threadsafe(self._async_send(data), self._loop)

    def _on_auth(self, action, username, password, cb):
        if not self._connected:
            cb(False, "Нет соединения с сервером")
            return
        self._cb = cb
        self._send({"action": action, "username": username, "password": password})

    def _handle(self, m):
        a = m.get("action")

        if a == "register_result":
            if self._cb:
                if m["ok"]:
                    self._cb(True)
                    self._login_scr._toggle()
                    self._login_scr.show_message("Аккаунт создан! Войдите.", GREEN)
                else:
                    self._cb(False, m.get("error", "Ошибка"))

        elif a == "login_result":
            if self._cb:
                if m["ok"]:
                    self._cb(True)
                    self._open_notepad(m["username"], m["is_admin"],
                                       m["notes"], m["users"])
                else:
                    self._cb(False, m.get("error", "Ошибка"))

        else:
            if self._note_scr:
                self._note_scr.handle(m)

    def _open_notepad(self, username, is_admin, notes_data, users):
        self._login_scr.place_forget()
        self._note_scr = NoteScreen(self, username, is_admin, self._send)
        self._note_scr.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._note_scr.set_notes(notes_data)
        self._note_scr.set_users(users)
        self._note_scr.status("Подключено", GREEN)


if __name__ == "__main__":
    App().mainloop()