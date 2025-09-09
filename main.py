from pyrogram import Client as TgClient
from pyrubi import Client as RbClient
from flask import Flask
import threading
import requests
import json
import os
import time

# ------------------ HTTP server ساده برای Render ------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------ تنظیمات ربات ------------------
api_id = 2040
api_hash = "b18441a1ff607e10a989891a5462e627"
source_channel = -1001092196973  # آیدی عددی کانال تلگرام
target_channel = "c0ByOFi0bc53d8706298ebf89d6604ba"

rb = RbClient("rubika_session")
tg = TgClient("telegram_session", api_id=api_id, api_hash=api_hash)

STATE_FILE = "last_tg_msg.json"
REQUIRED_STRING = "🤩 @ADAK_IR"
MY_TAG = "📲 @League_epror"
FILTER_WORDS = ["بت", "Https", "بانو", "همسر", "اختصاصی", "رایگان"]

SELF_URL = os.environ.get("SELF_URL", "https://your-app.onrender.com")

# ------------------ مدیریت وضعیت ------------------
def load_last_id():
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE, "r") as f:
            return int(json.load(f).get("last_id", 0))
    except:
        return 0

def save_last_id(msg_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_id": int(msg_id)}, f)

# ------------------ پردازش متن ------------------
def process_text(text: str) -> str:
    if not text:
        return None
    if REQUIRED_STRING not in text:
        return None
    for word in FILTER_WORDS:
        if word in text:
            return None
    lines = text.split("\n")
    new_lines = []
    for i in range(len(lines)-1):
        if lines[i].strip():
            new_lines.append(f"**{lines[i]}**")
        else:
            new_lines.append(lines[i])
    new_lines.append(MY_TAG)
    return "\n".join(new_lines)

# ------------------ Reconnect روبیکا ------------------
def reconnect_rb():
    global rb
    try:
        rb.disconnect()
    except:
        pass
    rb = RbClient("rubika_session")
    print("🔄 روبیکا دوباره وصل شد")

# ------------------ Keep Alive ------------------
def keep_alive():
    while True:
        try:
            requests.get(SELF_URL)
            print("🌐 keep-alive ارسال شد")
        except:
            print("⚠️ keep-alive شکست خورد")
        time.sleep(300)

# ------------------ ربات اصلی ------------------
def run_bot():
    global rb
    with tg:
        print("🚀 ربات شروع شد")
        if load_last_id() == 0:
            last_msg = list(tg.get_chat_history(source_channel, limit=1))
            if last_msg:
                save_last_id(last_msg[0].id)

        while True:
            try:
                last_id = load_last_id()
                msgs = list(tg.get_chat_history(source_channel, limit=1))
                msg = msgs[0] if msgs else None
                if not msg:
                    time.sleep(15)
                    continue
                if msg.id <= last_id:
                    time.sleep(15)
                    continue
                if msg.forward_from or msg.forward_from_chat:
                    save_last_id(msg.id)
                    continue

                caption = msg.caption or msg.text or ""
                processed_text = process_text(caption)
                if not processed_text:
                    save_last_id(msg.id)
                    continue

                if msg.photo:
                    file_path = f"/tmp/{msg.id}.jpg"
                    tg.download_media(msg.photo, file_path)
                    try:
                        rb.send_image(target_channel, file=file_path, text=processed_text)
                    except:
                        reconnect_rb()
                        rb.send_image(target_channel, file=file_path, text=processed_text)
                    os.remove(file_path)
                elif msg.video:
                    file_path = f"/tmp/{msg.id}.mp4"
                    tg.download_media(msg.video, file_path)
                    try:
                        rb.send_video(target_channel, file=file_path, text=processed_text)
                    except:
                        reconnect_rb()
                        rb.send_video(target_channel, file=file_path, text=processed_text)
                    os.remove(file_path)
                else:
                    try:
                        rb.send_text(target_channel, processed_text)
                    except:
                        reconnect_rb()
                        rb.send_text(target_channel, processed_text)

                save_last_id(msg.id)
                print(f"✅ پیام {msg.id} ارسال شد")

                time.sleep(15)
            except Exception as e:
                print("❌ خطای کلی:", e)
                reconnect_rb()
                time.sleep(20)

# ------------------ اجرای سرور و ربات ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=keep_alive).start()
    run_bot()
