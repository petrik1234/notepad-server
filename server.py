import asyncio
import json
import logging
import os
import hashlib
import http
import websockets
from datetime import datetime

logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

PORT      = int(os.environ.get("PORT", 8765))
HOST      = "0.0.0.0"
DATA_FILE = "data.json"


def _h(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


ACCOUNTS = {}
notes    = {}
_uid     = 0
sessions = {}

_save_lock = asyncio.Lock()


def load_data():
    global ACCOUNTS, notes, _uid

    if not os.path.exists(DATA_FILE):
        ACCOUNTS = {"admin": {"hash": _h("admin"), "is_admin": True}}
        notes = {}
        _uid = 0
        save_data_sync()
        print(f"  Создан новый {DATA_FILE} (админ: admin/admin)")
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ACCOUNTS = data.get("accounts", {})
        notes    = data.get("notes",    {})
        _uid     = data.get("uid",      0)

        if "admin" not in ACCOUNTS:
            ACCOUNTS["admin"] = {"hash": _h("admin"), "is_admin": True}
            save_data_sync()

        print(f"  Загружено: {len(ACCOUNTS)} аккаунтов, {len(notes)} заметок")
    except Exception as e:
        print(f"  Ошибка загрузки {DATA_FILE}: {e}")
        ACCOUNTS = {"admin": {"hash": _h("admin"), "is_admin": True}}
        notes = {}
        _uid = 0
        save_data_sync()


def save_data_sync():
    data = {"accounts": ACCOUNTS, "notes": notes, "uid": _uid}
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


async def save_data():
    async with _save_lock:
        try:
            await asyncio.to_thread(save_data_sync)
        except Exception as e:
            print(f"  ! Ошибка сохранения: {e}")


def new_id():
    global _uid
    _uid += 1
    return str(_uid)


def notes_list(requester):
    return [
        {
            "id":         k,
            "title":      v["title"],
            "author":     v["author"],
            "updated_at": v["updated_at"],
            "locked":     v["note_hash"] is not None,
            "is_mine":    v["author"] == requester
        }
        for k, v in notes.items()
    ]


async def broadcast(msg, skip=None):
    data = json.dumps(msg, ensure_ascii=False)
    for ws in list(sessions):
        if ws is not skip:
            try:
                await ws.send(data)
            except Exception:
                pass


async def send(ws, msg):
    try:
        await ws.send(json.dumps(msg, ensure_ascii=False))
    except Exception:
        pass


async def broadcast_note_list():
    for ws, sess in list(sessions.items()):
        try:
            await ws.send(json.dumps({
                "action": "notes_updated",
                "notes":  notes_list(sess["username"])
            }, ensure_ascii=False))
        except Exception:
            pass


async def process_request(connection, request):
    headers = request.headers
    if headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(http.HTTPStatus.OK, "OK\n")
    return None


async def handler(ws):
    username = None
    is_admin = False

    try:
        async for raw in ws:
            try:
                m = json.loads(raw)
            except Exception:
                continue

            a = m.get("action")

            if a == "ping":
                await send(ws, {"action": "pong"})
                continue

            if a == "register":
                uname = (m.get("username") or "").strip()
                pw    = m.get("password") or ""

                if not uname or not pw:
                    await send(ws, {"action": "register_result",
                                    "ok": False, "error": "Заполните все поля"})
                    continue
                if len(uname) < 2:
                    await send(ws, {"action": "register_result",
                                    "ok": False, "error": "Имя слишком короткое"})
                    continue
                if uname.lower() == "admin":
                    await send(ws, {"action": "register_result",
                                    "ok": False, "error": "Это имя зарезервировано"})
                    continue
                if uname in ACCOUNTS:
                    await send(ws, {"action": "register_result",
                                    "ok": False, "error": "Имя уже занято"})
                    continue

                ACCOUNTS[uname] = {"hash": _h(pw), "is_admin": False}
                await save_data()
                await send(ws, {"action": "register_result", "ok": True})
                print(f"  + Зарегистрирован: {uname}")

            elif a == "login":
                uname = (m.get("username") or "").strip()
                pw    = m.get("password") or ""

                acc = ACCOUNTS.get(uname)
                if not acc or acc["hash"] != _h(pw):
                    await send(ws, {"action": "login_result",
                                    "ok": False, "error": "Неверный логин или пароль"})
                    continue

                already_in = any(s["username"] == uname for s in sessions.values())
                if already_in:
                    await send(ws, {"action": "login_result", "ok": False,
                                    "error": "Аккаунт уже используется"})
                    continue

                username = uname
                is_admin = acc["is_admin"]
                sessions[ws] = {"username": username, "is_admin": is_admin}

                await send(ws, {
                    "action":   "login_result",
                    "ok":       True,
                    "username": username,
                    "is_admin": is_admin,
                    "notes":    notes_list(username),
                    "users":    [s["username"] for s in sessions.values()]
                })
                await broadcast({
                    "action":   "user_joined",
                    "username": username,
                    "users":    [s["username"] for s in sessions.values()]
                }, skip=ws)
                tag = "ADMIN" if is_admin else "user"
                print(f"  → Вход: {username} ({tag})")

            elif a == "create_note":
                if not username:
                    continue
                nid       = new_id()
                title     = (m.get("title") or "Без названия").strip()
                note_pw   = m.get("note_password") or ""
                note_hash = _h(note_pw) if note_pw else None

                notes[nid] = {
                    "title":      title,
                    "content":    "",
                    "author":     username,
                    "updated_at": datetime.now().strftime("%H:%M"),
                    "note_hash":  note_hash
                }
                await save_data()
                await broadcast_note_list()
                print(f"  📝 {username} → «{title}»{' 🔒' if note_hash else ''}")

            elif a == "open_note":
                if not username:
                    continue
                nid = m.get("id")
                if nid not in notes:
                    continue

                note = notes[nid]
                if note["note_hash"] is not None:
                    entered = m.get("note_password") or ""
                    if _h(entered) != note["note_hash"] and not is_admin:
                        await send(ws, {"action": "note_locked", "id": nid})
                        continue

                can_edit = (note["author"] == username) or is_admin

                await send(ws, {
                    "action":   "note_content",
                    "id":       nid,
                    "title":    note["title"],
                    "content":  note["content"],
                    "author":   note["author"],
                    "locked":   note["note_hash"] is not None,
                    "can_edit": can_edit
                })

            elif a == "edit_note":
                if not username:
                    continue
                nid = m.get("id")
                if nid not in notes:
                    continue
                note = notes[nid]
                if note["author"] != username and not is_admin:
                    await send(ws, {"action": "error",
                                    "text": "Нет прав для редактирования"})
                    continue

                notes[nid]["content"]    = m.get("content", "")
                notes[nid]["updated_at"] = datetime.now().strftime("%H:%M:%S")
                await save_data()

                await broadcast({
                    "action":     "note_updated",
                    "id":         nid,
                    "content":    notes[nid]["content"],
                    "updated_at": notes[nid]["updated_at"],
                    "editor":     username
                }, skip=ws)

            elif a == "delete_note":
                if not username:
                    continue
                nid = m.get("id")
                if nid not in notes:
                    continue
                if notes[nid]["author"] != username and not is_admin:
                    await send(ws, {"action": "error",
                                    "text": "Нет прав для удаления"})
                    continue

                title = notes[nid]["title"]
                del notes[nid]
                await save_data()
                await broadcast({"action": "note_deleted", "id": nid})
                await broadcast_note_list()
                print(f"  🗑  {username} удалил «{title}»")

            elif a == "set_note_password":
                if not username:
                    continue
                nid = m.get("id")
                if nid not in notes:
                    continue
                if notes[nid]["author"] != username and not is_admin:
                    await send(ws, {"action": "error", "text": "Нет прав"})
                    continue

                new_pw = m.get("note_password") or ""
                notes[nid]["note_hash"] = _h(new_pw) if new_pw else None
                await save_data()
                await send(ws, {"action": "password_set_ok", "id": nid,
                                "locked": notes[nid]["note_hash"] is not None})
                await broadcast_note_list()

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        sessions.pop(ws, None)
        if username:
            await broadcast({
                "action":   "user_left",
                "username": username,
                "users":    [s["username"] for s in sessions.values()]
            })
            print(f"  ← Выход: {username}")


async def main():
    print("=" * 50)
    print(f"  Блокнот-сервер запущен")
    print(f"  Слушает: {HOST}:{PORT}")
    print(f"  Файл данных: {os.path.abspath(DATA_FILE)}")
    print("=" * 50)
    load_data()
    print("=" * 50)
    async with websockets.serve(
        handler, HOST, PORT,
        process_request=process_request
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер остановлен")