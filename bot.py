import telebot
from telebot import types

BOT_TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 🔒 FORCE JOIN CHANNELS
# ==============================
# Public channel -> "@username"
# Private channel -> -100xxxxxxxxxx (chat ID)

FORCE_CHANNELS = [
    "@yourpublicchannel",
    -1001234567890  # replace with your private channel ID
]

# ==============================
# 🎬 VIDEO CODE SYSTEM
# ==============================

VIDEOS = {
    "1": "FILE_ID_HERE",
    "2": "FILE_ID_HERE_2"
}

# ==============================
# ✅ CHECK USER JOINED
# ==============================

def is_user_joined(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            print("Join Check Error:", e)
            return False
    return True


# ==============================
# 🚀 START COMMAND
# ==============================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if not is_user_joined(user_id):
        markup = types.InlineKeyboardMarkup()

        for channel in FORCE_CHANNELS:
            if isinstance(channel, str) and channel.startswith("@"):
                url = f"https://t.me/{channel.replace('@','')}"
                markup.add(types.InlineKeyboardButton("📢 Join Channel", url=url))

        markup.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_join"))

        bot.send_message(
            message.chat.id,
            "⚠️ Please join all required channels to use this bot.",
            reply_markup=markup
        )
        return

    bot.send_message(message.chat.id, "✅ Welcome! Send your video code.")


# ==============================
# 🔁 CALLBACK CHECK JOIN
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    user_id = call.from_user.id

    if is_user_joined(user_id):
        bot.edit_message_text(
            "✅ Verification Successful!\n\nNow send your video code.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ You have not joined all channels!",
            show_alert=True
        )


# ==============================
# 🎥 VIDEO CODE HANDLER
# ==============================

@bot.message_handler(func=lambda message: True)
def send_video_by_code(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not is_user_joined(user_id):
        bot.send_message(message.chat.id, "⚠️ Please join required channels first. Type /start")
        return

    if text in VIDEOS:
        bot.send_video(message.chat.id, VIDEOS[text])
    else:
        bot.send_message(message.chat.id, "❌ Invalid Code.")


# ==============================
# ▶️ RUN BOT
# ==============================

print("Bot is running...")
bot.infinity_polling()
