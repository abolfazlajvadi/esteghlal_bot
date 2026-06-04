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

# ---------- تنظیمات کانال‌ها ----------
REQUIRED_CHANNEL = "@film01385"           # کانال اجباری (کاربر باید عضو بشه)
STORAGE_CHANNEL = "@esteghlal01385" # 👈 کانال خصوصی برای ذخیره فیلم‌ها (یوزرنیم واقعی رو بذار)

# ---------- دیکشنری فیلم‌ها (شناسه -> message_id) ----------
# برای گرفتن message_id: فیلم رو در کانال خصوصی بفرست، سپس از ربات @get_id_bot استفاده کن
FILMS = {
    "film1": {
        "message_id": 3,                    # 👈 عدد message_id واقعی رو بذار
        "caption": "🎬 فیلم درخواستی شما"
    }
}

# ---------- لاگینگ ----------
logging.basicConfig(level=logging.INFO)

# ---------- تابع بررسی عضویت در کانال ----------
def is_user_member(user_id, channel_username):
    try:
        member = bot.get_chat_member(channel_username, user_id)
        logging.info(f"MEMBER STATUS: {member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"MEMBERSHIP ERROR: {e}")
        return False

# ---------- تابع ارسال فیلم از کانال ذخیره ----------
def send_film(chat_id, film_key):
    film = FILMS.get(film_key)
    if not film:
        return False
    try:
        bot.forward_message(
            chat_id=chat_id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=film["message_id"]
        )
        if film.get("caption"):
            bot.send_message(chat_id, film["caption"])
        return True
    except Exception as e:
        logging.error(f"خطا در ارسال فیلم: {e}")
        return False

# ---------- هندلر دستور start ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # استخراج پارامتر از لینک (مثل ?start=film1)
    try:
        param = message.text.split()[1]
        logging.info(f"PARAM received: {param}")
    except IndexError:
        param = None
        logging.info("No parameter received")

    # بررسی عضویت در کانال اجباری
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

    # اگر کاربر عضو است، فیلم را ارسال کن
    if param and param in FILMS:
        send_film(message.chat.id, param)
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
            # ارسال فیلم پیش‌فرض (اولین فیلم در دیکشنری)
            first_film = next(iter(FILMS.keys()))
            send_film(call.message.chat.id, first_film)
        else:
            bot.answer_callback_query(call.id, "❗️ شما هنوز عضو کانال نشده‌اید.", show_alert=True)

# ---------- مسیر Webhook ----------
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# ---------- مسیر سلامت برای Render ----------
@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

# ---------- مسیر اصلی ----------
@app.route('/', methods=['GET'])
def index():
    return "ربات تلگرام با Webhook فعال است.", 200

# ---------- تنظیم Webhook ----------
def set_webhook():
    external_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not external_url:
        logging.warning("RENDER_EXTERNAL_URL not set")
        return
    webhook_url = f"{external_url}/webhook/{TOKEN}"
    result = bot.set_webhook(url=webhook_url)
    if result:
        logging.info(f"Webhook set: {webhook_url}")
    else:
        logging.error("Failed to set webhook")

# ---------- اجرا ----------
if __name__ == '__main__':
    set_webhook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
