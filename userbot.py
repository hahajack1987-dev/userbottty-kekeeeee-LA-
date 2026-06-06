import asyncio
import os
import threading
from collections import deque
from datetime import datetime
from typing import List, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telethon import TelegramClient
from telethon.errors import RPCError

API_ID = int(os.getenv("34487343"))
API_HASH = os.getenv("a40ab178c6dafd889940afb1cbd5a0d8")
PHONE_NUMBER = os.getenv("905385592213")
SESSION_NAME = "userbot_session"
PORT = int(os.getenv("PORT", 5000))
LOG_LIMIT = 100

log_history = deque(maxlen=LOG_LIMIT)

class SpamConfig:
    def __init__(self):
        self.chat_ids: List[int] = []
        self.messages: List[str] = []
        self.delay_sec: float = 5.0
        self.loop: bool = False
        self.running: bool = False
        self.current_msg_idx: int = 0
        self.current_chat_idx: int = 0
        self.task: Optional[asyncio.Task] = None

config = SpamConfig()
client: Optional[TelegramClient] = None

def add_log(log_type: str, chat_id: Optional[int], message: Optional[str], error: Optional[str] = None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "chat_id": chat_id,
        "message": message,
        "error": error
    }
    log_history.appendleft(entry)
    print(f"[{entry['timestamp']}] {log_type.upper()}: {message or error}")

async def spam_loop():
    while config.running:
        if not config.chat_ids or not config.messages:
            add_log("error", None, "Chat veya mesaj listesi boş, durduruluyor.", None)
            await stop_spam()
            break

        chat_id = config.chat_ids[config.current_chat_idx]
        msg_text = config.messages[config.current_msg_idx]

        if msg_text and msg_text.strip():
            try:
                await client.send_message(chat_id, msg_text)
                add_log("sent", chat_id, msg_text)
            except RPCError as e:
                add_log("error", chat_id, msg_text, str(e))
        else:
            add_log("error", chat_id, "Boş mesaj atlandı", None)

        config.current_msg_idx += 1
        if config.current_msg_idx >= len(config.messages):
            config.current_msg_idx = 0
            config.current_chat_idx += 1
            if config.current_chat_idx >= len(config.chat_ids):
                if config.loop:
                    config.current_chat_idx = 0
                else:
                    await stop_spam()
                    break

        if config.running:
            await asyncio.sleep(config.delay_sec)

async def start_spam():
    if config.running:
        await stop_spam()
    if not config.chat_ids or not config.messages:
        add_log("error", None, "Chat listesi veya mesaj listesi boş.", None)
        return False
    config.running = True
    config.current_msg_idx = 0
    config.current_chat_idx = 0
    config.task = asyncio.create_task(spam_loop())
    add_log("info", None, f"Spam başlatıldı. {len(config.chat_ids)} chat, {len(config.messages)} mesaj, gecikme: {config.delay_sec}s, loop: {config.loop}")
    return True

async def stop_spam():
    if config.task and not config.task.done():
        config.task.cancel()
        try:
            await config.task
        except asyncio.CancelledError:
            pass
    config.running = False
    config.current_msg_idx = 0
    config.current_chat_idx = 0
    config.task = None
    add_log("info", None, "Spam döngüsü durduruldu.", None)

async def init_telegram():
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)
    me = await client.get_me()
    add_log("info", None, f"UserBot giriş başarılı: @{me.username} (ID: {me.id})")
    return True

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route("/config", methods=["POST"])
def set_config():
    data = request.json
    if "chatIds" in data:
        ids = data["chatIds"]
        if isinstance(ids, str):
            ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        config.chat_ids = ids
    if "messages" in data:
        msgs = data["messages"]
        if isinstance(msgs, str):
            msgs = [x.strip() for x in msgs.split(",") if x.strip()]
        config.messages = msgs
    if "delaySec" in data:
        config.delay_sec = float(data["delaySec"])
    if "loop" in data:
        config.loop = bool(data["loop"])
    return jsonify({"status": "configured", "chatIds": config.chat_ids, "messages": config.messages, "delaySec": config.delay_sec, "loop": config.loop})

@app.route("/start", methods=["GET"])
async def start_endpoint():
    success = await start_spam()
    if success:
        return jsonify({"status": "started"})
    return jsonify({"error": "Başlatılamadı. ChatIds veya messages boş olabilir."}), 400

@app.route("/stop", methods=["GET"])
async def stop_endpoint():
    await stop_spam()
    return jsonify({"status": "stopped"})

@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": list(log_history)})

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "running": config.running,
        "chatIds": config.chat_ids,
        "messages": config.messages,
        "delaySec": config.delay_sec,
        "loop": config.loop,
        "currentMsgIndex": config.current_msg_idx,
        "currentChatIndex": config.current_chat_idx
    })

def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

async def main():
    if not await init_telegram():
        add_log("error", None, "Telegram giriş başarısız!", None)
        return
    threading.Thread(target=run_flask, daemon=True).start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())