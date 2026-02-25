import telebot
import json
import random
import string

BOT_TOKEN = "8406788191:AAGZVHQS0xWkNHMlfcoDIpj8yleeE3Y7m_k"
ADMIN_ID = 6313511983

bot = telebot.TeleBot(BOT_TOKEN)

VIDEOS_FILE = "data/videos.json"
USERS_FILE = "data/users.json"
CHANNELS_FILE = "data/channels.json"


# ================= SAFE JSON =================

def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    users = load_json(USERS_FILE, [])

    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_json(USERS_FILE, users)

    bot.reply_to(message, "Welcome!\nSend video code & Get Code From @data277.")


# ================= ADMIN PANEL =================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return

    text = """
🔧 ADMIN PANEL

/addchannel @channel
/removechannel @channel
/listchannels
/listvideos
/deletevideo CODE
/broadcast MESSAGE
"""
    bot.reply_to(message, text)


# ================= ADD CHANNEL =================

@bot.message_handler(commands=['addchannel'])
def add_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        channel = message.text.split()[1]
        channels = load_json(CHANNELS_FILE, [])

        if channel not in channels:
            channels.append(channel)
            save_json(CHANNELS_FILE, channels)

        bot.reply_to(message, "✅ Channel Added")
    except:
        bot.reply_to(message, "Usage: /addchannel @channelusername")


# ================= REMOVE CHANNEL =================

@bot.message_handler(commands=['removechannel'])
def remove_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        channel = message.text.split()[1]
        channels = load_json(CHANNELS_FILE, [])

        if channel in channels:
            channels.remove(channel)
            save_json(CHANNELS_FILE, channels)

        bot.reply_to(message, "✅ Channel Removed")
    except:
        bot.reply_to(message, "Usage: /removechannel @channelusername")


# ================= LIST CHANNELS =================

@bot.message_handler(commands=['listchannels'])
def list_channels(message):
    if message.from_user.id != ADMIN_ID:
        return

    channels = load_json(CHANNELS_FILE, [])

    if not channels:
        bot.reply_to(message, "No channels added.")
    else:
        bot.reply_to(message, "\n".join(channels))


# ================= SAVE VIDEO =================

@bot.message_handler(content_types=['video'])
def save_video(message):
    if message.from_user.id != ADMIN_ID:
        return

    data = load_json(VIDEOS_FILE, {})
    code = generate_code()

    data[code] = message.video.file_id
    save_json(VIDEOS_FILE, data)

    bot.reply_to(message, f"✅ Video Saved\n📌 Code: {code}")


# ================= LIST VIDEOS =================

@bot.message_handler(commands=['listvideos'])
def list_videos(message):
    if message.from_user.id != ADMIN_ID:
        return

    data = load_json(VIDEOS_FILE, {})

    if not data:
        bot.reply_to(message, "No videos saved.")
        return

    text = "🎬 Video Codes:\n\n"
    for code in data:
        text += code + "\n"

    bot.reply_to(message, text)


# ================= DELETE VIDEO =================

@bot.message_handler(commands=['deletevideo'])
def delete_video(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        code = message.text.split()[1]
        data = load_json(VIDEOS_FILE, {})

        if code in data:
            del data[code]
            save_json(VIDEOS_FILE, data)
            bot.reply_to(message, "✅ Video Deleted")
        else:
            bot.reply_to(message, "Code not found")

    except:
        bot.reply_to(message, "Usage: /deletevideo CODE")


# ================= BROADCAST =================

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        text = message.text.replace("/broadcast ", "")
        users = load_json(USERS_FILE, [])
        sent = 0

        for user in users:
            try:
                bot.send_message(user, text)
                sent += 1
            except:
                pass

        bot.reply_to(message, f"✅ Broadcast sent to {sent} users")

    except:
        bot.reply_to(message, "Usage: /broadcast Your message")


# ================= FORCE JOIN CHECK =================

def check_force_join(user_id):
    channels = load_json(CHANNELS_FILE, [])

    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True


# ================= VIDEO CODE HANDLER (KEEP LAST!) =================

@bot.message_handler(func=lambda message: True)
def handle_code(message):

    if not check_force_join(message.from_user.id):
        channels = load_json(CHANNELS_FILE, [])
        text = "⚠️ Join Channels First:\n\n"
        for ch in channels:
            text += ch + "\n"
        bot.reply_to(message, text)
        return

    data = load_json(VIDEOS_FILE, {})

    if message.text in data:
        bot.send_video(message.chat.id, data[message.text])
    else:
        bot.reply_to(message, "❌ Invalid Code")


print("Bot Running...")
bot.infinity_polling()


