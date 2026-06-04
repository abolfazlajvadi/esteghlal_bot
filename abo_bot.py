import os
import logging
import threading
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- تنظیمات اولیه ----------
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------- دیکشنری برای نگهداری فیلم درخواستی هر کاربر ----------
user_requested_film = {}

# ---------- تنظیمات کانال‌ها ----------
REQUIRED_CHANNEL = "@film01385"           # کانال اجباری
STORAGE_CHANNEL = "@esteghlal01385"       # کانال خصوصی برای ذخیره فیلم‌ها

# ---------- دیکشنری فیلم‌ها ----------
FILMS = {
    "film1": {
        "message_id": 3,                    # message_id واقعی فیلم
        "caption": "🎬 فیلم درخواستی شما"
    }
}

# ---------- لاگینگ ----------
logging.basicConfig(level=logging.INFO)

# ========== تابع حذف پیام بعد از ۲۰ ثانیه ==========
def delete_message_after_delay(chat_id, message_id, delay=20):
    """پیام رو بعد از delay ثانیه حذف می‌کنه"""
    def delete():
        try:
            bot.delete_message(chat_id, message_id)
            logging.info(f"Message {message_id} deleted after {delay} seconds")
        except Exception as e:
            logging.error(f"Failed to delete message: {e}")
    timer = threading.Timer(delay, delete)
    timer.daemon = True
    timer.start()

# ---------- تابع ارسال فیلم با تایمر حذف ----------
def send_film_with_timer(chat_id, film_key):
    film = FILMS.get(film_key)
    if not film:
        bot.send_message(chat_id, "❌ فیلم مورد نظر یافت نشد.")
        return False
    
    try:
        # فوروارد کردن فیلم از کانال ذخیره
        forwarded = bot.forward_message(
            chat_id=chat_id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=film["message_id"]
        )
        
        # پیام هشدار با تایمر
        warning_msg = bot.send_message(
            chat_id,
            f"⚠️ این فیلم تا {20} ثانیه دیگر حذف می‌شود.\n"
            "لطفاً برای نگهداری، آن را **سیو** یا **فوروارد** کنید، سپس دانلود کنید."
        )
        
        # حذف فیلم و پیام هشدار بعد از ۲۰ ثانیه
        delete_message_after_delay(chat_id, forwarded.message_id, delay=20)
        delete_message_after_delay(chat_id, warning_msg.message_id, delay=20)
        
        return True
    except Exception as e:
        logging.error(f"Error sending film: {e}")
        bot.send_message(chat_id, "❌ خطا در ارسال فیلم.")
        return False

# ---------- تابع بررسی عضویت ----------
def is_user_member(user_id, channel_username):
    try:
        member = bot.get_chat_member(channel_username, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Membership error: {e}")
        return False

# ---------- هندلر دستور start ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # استخراج پارامتر از لینک
    try:
        param = message.text.split()[1]
        logging.info(f"Param received: {param}")
    except IndexError:
        param = None
    
    # ذخیره کردن فیلم درخواستی کاربر (اگه پارامتر داشته باشه)
    if param:
        user_requested_film[chat_id] = param
        logging.info(f"Saved requested film for user {chat_id}: {param}")
    
    # بررسی عضویت در کانال اجباری
    if not is_user_member(user_id, REQUIRED_CHANNEL):
        markup = InlineKeyboardMarkup(row_width=1)
        join_btn = InlineKeyboardButton(
            "🔹 عضویت در کانال",
            url=f"https://t.me/{REQUIRED_CHANNEL[1:]}"
        )
        check_btn = InlineKeyboardButton(
            "✅ عضویت را بررسی کردم",
            callback_data="check_membership"
        )
        markup.add(join_btn, check_btn)
        bot.reply_to(
            message,
            f"🚫 برای دریافت فیلم، ابتدا در کانال {REQUIRED_CHANNEL} عضو شوید.",
            reply_markup=markup
        )
        return
    
    # اگر کاربر قبلاً عضو کانال بود، مستقیم فیلم درخواستی رو بفرست
    if param and param in FILMS:
        send_film_with_timer(chat_id, param)
    else:
        bot.reply_to(message, "سلام! برای دریافت فیلم، روی لینک‌های داخل کانال کلیک کن.")

# ---------- هندلر دکمه بررسی عضویت (نسخه جدید - بدون ارسال خودکار فیلم) ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_membership":
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        
        if is_user_member(user_id, REQUIRED_CHANNEL):
            # دریافت فیلم درخواستی کاربر از دیکشنری
            requested_film = user_requested_film.get(chat_id, "film1")
            
            # فقط پیام تأیید عضویت رو ویرایش می‌کنیم، فیلم نمی‌فرستیم
            bot.edit_message_text(
                f"✅ عضویت شما تأیید شد!\n\n"
                chat_id,
                call.message.message_id
            )
            # پاک کردن دیکشنری برای این کاربر
            if chat_id in user_requested_film:
                del user_requested_film[chat_id]
        else:
            bot.answer_callback_query(call.id, "❗️ شما هنوز عضو کانال نشده‌اید.", show_alert=True)

# ---------- Webhook و بقیه قسمت‌ها ----------
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

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "ربات تلگرام فعال است.", 200

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

if __name__ == '__main__':
    set_webhook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
