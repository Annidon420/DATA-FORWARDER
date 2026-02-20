import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_KEY = "8006902002"
DATA_DIR = "/data"

# ---------------- STORAGE ---------------- #

def file_path(name):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    return os.path.join(DATA_DIR, name)

def load_json(name):
    path = file_path(name)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
    with open(path, "r") as f:
        return json.load(f)

def save_json(name, data):
    with open(file_path(name), "w") as f:
        json.dump(data, f, indent=2)

# ---------------- DATABASE FILES ---------------- #

USERS_FILE = "users.json"
VIDEOS_FILE = "videos.json"
FORCE_FILE = "force.json"
ADMIN_FILE = "admin.json"

# ---------------- HELPERS ---------------- #

def add_user(user_id):
    users = load_json(USERS_FILE)
    users[str(user_id)] = True
    save_json(USERS_FILE, users)

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return str(user_id) in admins

# ---------------- COMMANDS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not await check_force_join(update, context):
        return

    await update.message.reply_text(
        "👋 Welcome!\n\nSend a number to get video.\nExample: 1"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send:\n/adminkey 8006902002")

async def adminkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) == 0:
        return await update.message.reply_text("Send key like:\n/adminkey 800*******")

    if context.args[0] == ADMIN_KEY:
        admins = load_json(ADMIN_FILE)
        admins[str(user_id)] = True
        save_json(ADMIN_FILE, admins)
        await update.message.reply_text("✅ Admin access granted.")
    else:
        await update.message.reply_text("❌ Wrong key.")

# ---------------- FORCE JOIN ---------------- #

async def check_force_join(update, context):
    channels = load_json(FORCE_FILE)
    if not channels:
        return True

    user_id = update.effective_user.id
    buttons = []

    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                buttons.append([InlineKeyboardButton("Join Channel", url=f"https://t.me/{ch.replace('@','')}")])
        except:
            continue

    if buttons:
        await update.message.reply_text(
            "🚫 Join required channels first.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return False

    return True

async def addforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) == 0:
        return await update.message.reply_text("Usage:\n/addforce @channelusername")

    channels = load_json(FORCE_FILE)
    channels[context.args[0]] = True
    save_json(FORCE_FILE, channels)
    await update.message.reply_text("✅ Force channel added.")

async def removeforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    channels = load_json(FORCE_FILE)
    if context.args[0] in channels:
        del channels[context.args[0]]
        save_json(FORCE_FILE, channels)
        await update.message.reply_text("❌ Force channel removed.")

# ---------------- AUTO SYNC ---------------- #

async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = load_json(VIDEOS_FILE)
    next_id = str(len(videos) + 1)

    videos[next_id] = {
        "chat_id": update.channel_post.chat_id,
        "message_id": update.channel_post.message_id,
    }

    save_json(VIDEOS_FILE, videos)

# ---------------- SEND VIDEO BY NUMBER ---------------- #

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return

    text = update.message.text.strip()

    if not text.isdigit():
        return

    videos = load_json(VIDEOS_FILE)

    if text not in videos:
        return await update.message.reply_text("❌ Video not found.")

    data = videos[text]

    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=data["chat_id"],
        message_id=data["message_id"],
    )

# ---------------- BROADCAST ---------------- #

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a message with /broadcast")

    users = load_json(USERS_FILE)

    for user_id in users:
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id,
            )
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent.")

# ---------------- MAIN ---------------- #

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("adminkey", adminkey))
app.add_handler(CommandHandler("addforce", addforce))
app.add_handler(CommandHandler("removeforce", removeforce))
app.add_handler(CommandHandler("broadcast", broadcast))

app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_number))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post))

app.run_polling()

