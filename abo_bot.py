import os
import logging
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- تنظیمات اولیه ----------
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------- تنظیمات کانال اجباری ----------
# 👇 نام کاربری کانال خود را اینجا وارد کنید (با @ و بدون فاصله، مثال: "@my_channel")
REQUIRED_CHANNEL = "film01385"  # <--- این را به نام کانال خود تغییر دهید

# ---------- لاگینگ برای بررسی خطاها ----------
logging.basicConfig(level=logging.INFO)

# ---------- تابع بررسی عضویت در کانال ----------
def is_user_member(user_id, channel_username):
    try:
        member = bot.get_chat_member(channel_username, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"خطا در بررسی عضویت کاربر {user_id}: {e}")
        return False

# ---------- هندلر دستور start ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    # استخراج پارامتر (مثل film1)
    try:
        param = message.text.split()[1]
    except IndexError:
        param = None

    # اگر کاربر عضو کانال نباشد
    if not is_user_member(user_id, REQUIRED_CHANNEL):
        markup = InlineKeyboardMarkup(row_width=1)
        join_btn = InlineKeyboardButton(
            text="🔹 عضویت در کانال",
            url=f"https://t.me/{REQUIRED_CHANNEL[1:]}"
        )
        check_btn = InlineKeyboardButton(
            text="✅ عضویت را بررسی کردم",
            callback_data="check_membership"
        )
        markup.add(join_btn, check_btn)
        bot.reply_to(
            message,
            f"🚫 برای دریافت فیلم، ابتدا باید در کانال زیر عضو شوید:\n👉 {REQUIRED_CHANNEL}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return

    # اگر کاربر عضو است و پارامتر معتبر دارد
    # 👇 لطفاً File ID واقعی فیلم خود را اینجا قرار دهید
    if param == "abc":
        video_file_id = "BAACAgQAAxkBAAN6ah83R2alIdNXQwXLak9SK409wacAAv8yAAIxVvhQ2J09kYGhi4o7BA"
        bot.send_video(message.chat.id, video_file_id, caption="🎬 فیلم درخواستی شما")
    else:
        bot.reply_to(message, "سلام! برای دریافت محتوا، روی لینک‌های داخل کانال کلیک کن.")

# ---------- هندلر بررسی مجدد عضویت (Callback) ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_membership":
        user_id = call.from_user.id
        if is_user_member(user_id, REQUIRED_CHANNEL):
            bot.edit_message_text(
                "✅ عضویت شما تأیید شد! در حال ارسال فیلم...",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            # 👇 لطفاً File ID واقعی فیلم خود را اینجا نیز قرار دهید
            video_file_id = "BAACAgQAAxkBAAN6ah83R2alIdNXQwXLak9SK409wacAAv8yAAIxVvhQ2J09kYGhi4o7BA"
            bot.send_video(call.message.chat.id, video_file_id, caption="🎬 فیلم درخواستی شما")
        else:
            bot.answer_callback_query(call.id, "❗️ شما هنوز عضو کانال نشده‌اید. لطفاً ابتدا عضو شوید.", show_alert=True)

# ---------- مسیر Webhook (تلگرام درخواست‌ها را به اینجا می‌فرستد) ----------
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

# ---------- مسیر سلامت برای Health Check Render ----------
@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

# ---------- مسیر اصلی ----------
@app.route('/', methods=['GET'])
def index():
    return "ربات تلگرام با Webhook فعال است.", 200

# ---------- تابع تنظیم Webhook در تلگرام ----------
def set_webhook():
    external_url = os.environ.get('RENDER_EXTERNAL_URL')
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
    set_webhook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
