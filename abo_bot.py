import os
import logging
from flask import Flask, request, jsonify
import telebot

# ---------- تنظیمات اولیه ----------
TOKEN = os.environ.get('BOT_TOKEN')  # توکن را از محیط می‌خوانیم (در Render تنظیم می‌شود)
if not TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------- لاگینگ برای بررسی خطاها ----------
logging.basicConfig(level=logging.INFO)

# ---------- مسیر Webhook (تلگرام درخواست‌ها را به این آدرس می‌فرستد) ----------
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"خطا در پردازش Webhook: {e}")
        return jsonify({"status": "error"}), 500

# ---------- مسیر سلامت (برای Health Check Render و cron-job) ----------
@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

# ---------- مسیر اصلی (فقط برای نمایش) ----------
@app.route('/', methods=['GET'])
def index():
    return "ربات تلگرام با Webhook فعال است.", 200

# ---------- دستورات ساده ربات (مثال) ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "سلام! این ربات با Webhook کار می‌کند. 🚀")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# ---------- تابع تنظیم Webhook در تلگرام (در زمان اجرا) ----------
def set_webhook():
    # آدرس ربات در Render: https://your-app-name.onrender.com
    # توجه: Render به شما آدرس می‌دهد. اینجا باید از متغیر محیطی یا آدرس ثابت استفاده کنید.
    # در Render، آدرس به صورت خودکار در دسترس است. ما از آدرس نسبی استفاده می‌کنیم.
    # اما برای تنظیم webhook، به آدرس کامل نیاز داریم. می‌توانید آن را از متغیر محیطی RENDER_EXTERNAL_URL بخوانید.
    external_url = os.environ.get('RENDER_EXTERNAL_URL')  # Render این متغیر را خودکار می‌سازد
    if not external_url:
        logging.warning("RENDER_EXTERNAL_URL تنظیم نشده. Webhook تنظیم نمی‌شود.")
        return
    
    webhook_url = f"{external_url}/webhook/{TOKEN}"
    result = bot.set_webhook(url=webhook_url)
    if result:
        logging.info(f"Webhook با موفقیت تنظیم شد: {webhook_url}")
    else:
        logging.error("تنظیم Webhook ناموفق بود")

# ---------- اجرای برنامه ----------
if __name__ == '__main__':
    # ابتدا webhook را تنظیم می‌کنیم
    set_webhook()
    # سپس سرور Flask را راه می‌اندازیم
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)