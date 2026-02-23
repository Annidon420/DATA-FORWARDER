import telebot
from telebot import types
import json
import os
import random
import string

# ==============================
# 🔑 CONFIG
# ==============================

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # Replace with your Telegram ID

# Public channels only (easy version)
FORCE_CHANNELS = [
    "@yourchannel1",
    "@yourchannel2"
]

DATA_FILE = "videos.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 📂 LOAD / SAVE DATABASE
# ==============================

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==============================
# 🔐 FORCE JOIN CHECK
# ==============================

def is_joined(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def join_markup():
    markup = types.InlineKeyboardMarkup()
    for channel in FORCE_CHANNELS:
        link = f"https://t.me/{channel.replace('@','')}"
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=link))
    markup.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check"))
    return markup

# ==============================
# 🎲 AUTO CODE GENERATOR
# ==============================

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==============================
# 🚀 START
# ==============================

@bot.message_handler(commands=['start'])
def start(message):
    if not is_joined(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "⚠️ Please join required channels first.",
            reply_markup=join_markup()
        )
        return

    bot.send_message(message.chat.id, "✅ Send your video code.")

# ==============================
# 🔁 CHECK JOIN BUTTON
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "check")
def check(call):
    if is_joined(call.from_user.id):
        bot.edit_message_text(
            "✅ Verified!\nNow send your video code.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

# ==============================
# 🎥 ADMIN UPLOAD VIDEO
# ==============================

@bot.message_handler(content_types=['video'])
def upload_video(message):
    if message.from_user.id != ADMIN_ID:
        return

    data = load_data()
    code = generate_code()

    while code in data:
        code = generate_code()

    data[code] = message.video.file_id
    save_data(data)

    bot.reply_to(
        message,
        f"✅ Video Saved Successfully!\n\n🔑 Code: `{code}`",
        parse_mode="Markdown"
    )

# ==============================
# 📤 SEND VIDEO BY CODE
# ==============================

@bot.message_handler(func=lambda message: True)
def send_video(message):
    if not is_joined(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "⚠️ Join channels first.",
            reply_markup=join_markup()
        )
        return

    code = message.text.strip().upper()
    data = load_data()

    if code in data:
        bot.send_video(message.chat.id, data[code])
    else:
        bot.send_message(message.chat.id, "❌ Invalid Code.")

# ==============================
# 📢 BROADCAST
# ==============================

users = set()

@bot.message_handler(func=lambda message: True)
def save_user(message):
    users.add(message.from_user.id)

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = message.reply_to_message
    if not msg:
        bot.reply_to(message, "Reply to a message to broadcast.")
        return

    for user in users:
        try:
            bot.copy_message(user, msg.chat.id, msg.message_id)
        except:
            pass

    bot.reply_to(message, "✅ Broadcast Sent.")

# ==============================
# ▶ RUN
# ==============================

print("Bot Running...")
bot.infinity_polling()
