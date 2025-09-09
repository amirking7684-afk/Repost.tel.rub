from flask import Flask
from pyrogram import Client as TgClient
from pyrubi import Client as RbClient
import threading
import json
import os
import time

# ------------------ تنظیمات ------------------
TELEGRAM_SESSION = "telegram_session"
RUBIKA_SESSION = "rubika_session"
SOURCE_CHANNEL = -1001092196973  # آیدی کانال تلگرام
TARGET_CHANNEL = "c0ByOFi0bc53d8706298ebf89d6604ba"

REQUIRED_STRING = "🤩 @ADAK_IR"
MY_TAG = "📲 @League_epror"
FILTER_WORDS = ["بت", "Https", "بانو", "همسر", "اختصاصی", "رایگان"]

STATE_FILE = "last_tg_msg.json"

tg = TgClient(TELEGRAM_SESSION, api_id=2040, api_hash="b18441a1ff607e10a989891a5462e627")
rb = RbClient(RUBIKA_SESSION)

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

# ------------------ ربات اصلی ------------------
def run_bot():
    global tg, rb
    while True:
        try:
            with tg:
                print("🚀 ربات شروع شد")
                chat = tg.get_chat(SOURCE_CHANNEL)
                print(f"📡 به کانال وصل شدم: {chat.title}")

                # بار اول، آخرین پیام کانال رو ذخیره کن
                if load_last_id() == 0:
                    last_msg = list(tg.get_chat_history(SOURCE_CHANNEL, limit=1))
                    if last_msg:
                        save_last_id(last_msg[0].id)

                while True:
                    try:
                        last_id = load_last_id()
                        msgs = list(tg.get_chat_history(SOURCE_CHANNEL, limit=5))
                        msgs.reverse()  # از قدیمی به جدید

                        for msg in msgs:
                            if msg.id <= last_id:
                                continue

                            if msg.forward_from or msg.forward_from_chat:
                                print(f"⛔ پیام {msg.id} فورواردی بود")
                                save_last_id(msg.id)
                                continue

                            caption = msg.caption or msg.text or ""
                            processed_text = process_text(caption)
                            if not processed_text:
                                print(f"⛔ پیام {msg.id} شرایط ارسال نداشت")
                                save_last_id(msg.id)
                                continue

                            # ارسال محتوا
                            if msg.photo:
                                file_path = f"/tmp/{msg.id}.jpg"
                                tg.download_media(msg.photo, file_path)
                                rb.send_image(TARGET_CHANNEL, file=file_path, text=processed_text)
                                os.remove(file_path)
                                print(f"✅ عکس + کپشن {msg.id} ارسال شد")
                            elif msg.video:
                                file_path = f"/tmp/{msg.id}.mp4"
                                tg.download_media(msg.video, file_path)
                                rb.send_video(TARGET_CHANNEL, file=file_path, text=processed_text)
                                os.remove(file_path)
                                print(f"✅ ویدیو + کپشن {msg.id} ارسال شد")
                            else:
                                rb.send_text(TARGET_CHANNEL, processed_text)
                                print(f"✅ متن {msg.id} ارسال شد")

                            save_last_id(msg.id)

                        time.sleep(15)

                    except Exception as e:
                        print("❌ خطا در پردازش پیام:", e)
                        time.sleep(10)

        except Exception as e:
            print("❌ خطای کلی در run_bot:", e)
            print("🔄 تلاش برای راه‌اندازی دوباره در 30 ثانیه...")
            time.sleep(30)

# ------------------ Flask وب‌سرور ------------------
app = Flask(__name__)
@app.route("/")
def home():
    return "🚀 ربات روی Render فعال است!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------ استارت همزمان ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
