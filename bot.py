import telebot
from telebot import types
import json
import os
import random
import string

# ==============================
# 🔑 CONFIG
# ==============================

BOT_TOKEN = "8406788191:AAGZVHQS0xWkNHMlfcoDIpj8yleeE3Y7m_k"
ADMIN_ID = 6313511983

VIDEOS_FILE = "videos.json"
CHANNELS_FILE = "channels.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 📂 CREATE FILES IF NOT EXIST
# ==============================

for file in [VIDEOS_FILE, CHANNELS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# ==============================
# 📂 LOAD / SAVE
# ==============================

def load_videos():
    with open(VIDEOS_FILE, "r") as f:
        return json.load(f)

def save_videos(data):
    with open(VIDEOS_FILE, "w") as f:
        json.dump(data, f)

def load_channels():
    with open(CHANNELS_FILE, "r") as f:
        return json.load(f)

def save_channels(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f)

# ==============================
# 🔐 FORCE JOIN CHECK
# ==============================

def is_joined(user_id):
    channels = load_channels()
    for channel in channels.values():
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def join_markup():
    markup = types.InlineKeyboardMarkup()
    channels = load_channels()
    for channel in channels.values():
        if channel.startswith("@"):
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

    data = load_videos()
    code = generate_code()

    while code in data:
        code = generate_code()

    data[code] = message.video.file_id
    save_videos(data)

    bot.reply_to(message, f"✅ Video Saved!\n🔑 Code: `{code}`", parse_mode="Markdown")

# ==============================
# 📤 SEND VIDEO
# ==============================

@bot.message_handler(func=lambda message: True)
def send_video(message):
    if message.from_user.id == ADMIN_ID:
        return

    if not is_joined(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Join channels first.", reply_markup=join_markup())
        return

    code = message.text.strip().upper()
    data = load_videos()

    if code in data:
        bot.send_video(message.chat.id, data[code])
    else:
        bot.send_message(message.chat.id, "❌ Invalid Code.")

# ==============================
# 🛠 ADMIN PANEL COMMANDS
# ==============================

@bot.message_handler(commands=['addchannel'])
def add_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        channel = message.text.split(" ")[1]
    except:
        bot.reply_to(message, "Usage:\n/addchannel @channelusername")
        return

    channels = load_channels()
    channels[str(len(channels)+1)] = channel
    save_channels(channels)

    bot.reply_to(message, f"✅ Channel Added:\n{channel}")

@bot.message_handler(commands=['removechannel'])
def remove_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        channel = message.text.split(" ")[1]
    except:
        bot.reply_to(message, "Usage:\n/removechannel @channelusername")
        return

    channels = load_channels()
    for key, value in list(channels.items()):
        if value == channel:
            del channels[key]
            save_channels(channels)
            bot.reply_to(message, f"❌ Channel Removed:\n{channel}")
            return

    bot.reply_to(message, "Channel not found.")

@bot.message_handler(commands=['listchannels'])
def list_channels(message):
    if message.from_user.id != ADMIN_ID:
        return

    channels = load_channels()
    if not channels:
        bot.reply_to(message, "No channels added.")
        return

    text = "📢 Force Join Channels:\n\n"
    for ch in channels.values():
        text += f"{ch}\n"

    bot.reply_to(message, text)

# ==============================
# ▶ RUN
# ==============================

print("Bot Running...")
bot.infinity_polling()
