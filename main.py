from pyrogram import Client as TgClient
from pyrubi import Client as RbClient
from flask import Flask
import threading
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
source_channel = -1001092196973
target_channel = "c0ByOFi0bc53d8706298ebf89d6604ba"

STATE_FILE = "last_tg_msg.json"
REQUIRED_STRING = "🤩 @ADAK_IR"
MY_TAG = "📲 @League_epror"
FILTER_WORDS = ["بت", "Https", "بانو", "همسر", "اختصاصی", "رایگان"]

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
    new_lines = [f"**{line}**" if line.strip() else line for line in lines[:-1]]
    new_lines.append(MY_TAG)
    return "\n".join(new_lines)

# ------------------ ایجاد سشن‌ها ------------------
def create_sessions():
    tg_client = TgClient("telegram_session", api_id=api_id, api_hash=api_hash)
    rb_client = RbClient("rubika_session")
    return tg_client, rb_client

# ------------------ ارسال پایدار به روبیکا ------------------
def safe_send(rb_client, msg_type, file=None, text=None):
    for attempt in range(2):
        try:
            if msg_type == "text":
                rb_client.send_text(target_channel, text)
            elif msg_type == "image":
                rb_client.send_image(target_channel, file=file, text=text)
            elif msg_type == "video":
                rb_client.send_video(target_channel, file=file, text=text)
            return True
        except Exception as e:
            print(f"⚠️ خطا در ارسال به روبیکا (تلاش {attempt+1}):", e)
            time.sleep(5)
            rb_client = RbClient("rubika_session")  # reconnect
    print("❌ ارسال پیام به روبیکا ناموفق بود.")
    return False

# ------------------ ربات اصلی ------------------
def run_bot():
    tg, rb = create_sessions()
    with tg:
        print("🚀 ربات شروع شد")
        if load_last_id() == 0:
            last_msg = list(tg.get_chat_history(source_channel, limit=1))
            if last_msg:
                save_last_id(last_msg[0].id)

        while True:
            try:
                last_id = load_last_id()
                msgs = list(tg.get_chat_history(source_channel, limit=5))  # بررسی چند پیام آخر
                for msg in reversed(msgs):  # از قدیمی به جدید
                    if msg.id <= last_id:
                        continue
                    if msg.forward_from or msg.forward_from_chat:
                        save_last_id(msg.id)
                        continue

                    caption = msg.caption or msg.text or ""
                    processed_text = process_text(caption)
                    if not processed_text:
                        save_last_id(msg.id)
                        continue

                    success = False
                    if msg.photo:
                        file_path = f"/tmp/{msg.id}.jpg"
                        tg.download_media(msg.photo, file_path)
                        success = safe_send(rb, "image", file=file_path, text=processed_text)
                        if success:
                            os.remove(file_path)
                    elif msg.video:
                        file_path = f"/tmp/{msg.id}.mp4"
                        tg.download_media(msg.video, file_path)
                        success = safe_send(rb, "video", file=file_path, text=processed_text)
                        if success:
                            os.remove(file_path)
                    else:
                        success = safe_send(rb, "text", text=processed_text)

                    if success:
                        save_last_id(msg.id)

                time.sleep(10)
            except Exception as e:
                print("❌ خطای کلی:", e)
                time.sleep(20)

# ------------------ اجرای سرور و ربات ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
