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
source_channel = -1003095739251  # آیدی عددی کانال تلگرام
target_channel = "c0CusS702bf9f47324f1db408daa6a74"

rb = RbClient("rubika_session")
tg = TgClient("telegram_session", api_id=api_id, api_hash=api_hash)

STATE_FILE = "last_tg_msg.json"
REQUIRED_STRING = "@Bad_ss"
MY_TAG = "@League_epror"
FILTER_WORDS = ["فیلتر", "ممنوع", "بد"]

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
        print("❌ پیام خالی است")
        return None

    if REQUIRED_STRING not in text:
        print(f"❌ پیام رشته اجباری '{REQUIRED_STRING}' ندارد")
        return None

    for word in FILTER_WORDS:
        if word in text:
            print(f"❌ پیام شامل کلمه فیلتر شده است: {word}")
            return None

    lines = text.split("\n")
    new_lines = []
    for i in range(len(lines)-1):
        if lines[i].strip():
            new_lines.append(f"**{lines[i]}**")
        else:
            new_lines.append(lines[i])

    # آخرین خط با تگ شما جایگزین میشه
    new_lines.append(MY_TAG)
    return "\n".join(new_lines)

# ------------------ ربات اصلی ------------------
def run_bot():
    with tg:
        print("🚀 ربات شروع شد")
        try:
            chat = tg.get_chat(source_channel)
            print(f"📡 به کانال وصل شدم: {chat.title}")
        except Exception as e:
            print("❌ خطا در اتصال به کانال:", e)

        # فقط بار اول: آخرین پیام کانال رو به عنوان نقطه شروع ذخیره می‌کنیم
        if load_last_id() == 0:
            last_msg = next(tg.get_chat_history(source_channel, limit=1), None)
            if last_msg:
                save_last_id(last_msg.id)
                print(f"⏳ شروع از پیام {last_msg.id} (فقط پیام‌های جدید ارسال خواهند شد)")

        while True:
            try:
                last_id = load_last_id()
                msg = next(tg.get_chat_history(source_channel, limit=1), None)

                if not msg:
                    print("⚠️ پیامی پیدا نشد")
                    time.sleep(15)
                    continue

                print(f"📥 پیام {msg.id} بررسی شد (آخرین ذخیره‌شده: {last_id})")

                # پیام قبلا پردازش شده
                if msg.id <= last_id:
                    print("⏭ پیام قبلا پردازش شده بود")
                    save_last_id(msg.id)
                    time.sleep(15)
                    continue

                # پیام فورواردی
                if msg.forward_from or msg.forward_from_chat:
                    print("⛔ پیام فورواردی بود")
                    save_last_id(msg.id)
                    continue

                caption = msg.caption or msg.text or ""
                processed_text = process_text(caption)

                if not processed_text:
                    print("⛔ پیام شرایط ارسال را نداشت")
                    save_last_id(msg.id)
                    continue

                # ارسال عکس
                if msg.photo:
                    file_path = os.path.join(os.getcwd(), f"{msg.id}.jpg")
                    tg.download_media(msg.photo, file_path)
                    rb.send_image(target_channel, file=file_path, text=processed_text)
                    os.remove(file_path)
                    print("✅ عکس + کپشن ارسال شد")
                # ارسال ویدیو
                elif msg.video:
                    file_path = os.path.join(os.getcwd(), f"{msg.id}.mp4")
                    tg.download_media(msg.video, file_path)
                    rb.send_video(target_channel, file=file_path, text=processed_text)
                    os.remove(file_path)
                    print("✅ ویدیو + کپشن ارسال شد")
                # فقط متن
                else:
                    rb.send_text(target_channel, processed_text)
                    print("✅ متن ارسال شد")

                # ذخیره پیام بعد از ارسال
                save_last_id(msg.id)
                print(f"💾 پیام {msg.id} ذخیره شد")

                time.sleep(15)

            except Exception as e:
                print("❌ خطای کلی:", e)
                time.sleep(20)

# ------------------ اجرای همزمان Flask و ربات ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()  # HTTP server برای Render
    run_bot()  # اجرای ربات اصلی
