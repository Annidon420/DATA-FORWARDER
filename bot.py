import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_KEY = "8006902002"
DATA_DIR = "/data"

USERS_FILE = "users.json"
VIDEOS_FILE = "videos.json"
FORCE_FILE = "force.json"
ADMIN_FILE = "admin.json"

# ---------------- STORAGE ---------------- #

def ensure_data_folder():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_path(filename):
    ensure_data_folder()
    return os.path.join(DATA_DIR, filename)

def load_json(filename):
    path = get_path(filename)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
    with open(path, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(get_path(filename), "w") as f:
        json.dump(data, f, indent=2)

# ---------------- HELPERS ---------------- #

def add_user(user_id):
    users = load_json(USERS_FILE)
    users[str(user_id)] = True
    save_json(USERS_FILE, users)

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return str(user_id) in admins

# ---------------- FORCE JOIN ---------------- #

async def check_force_join(update, context):
    channels = load_json(FORCE_FILE)

    if not channels:
        return True

    user_id = update.effective_user.id
    buttons = []
    not_joined = False

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                not_joined = True
                buttons.append([
                    InlineKeyboardButton(
                        "Join Channel",
                        url=f"https://t.me/{channel.replace('@','')}"
                    )
                ])
        except:
            not_joined = True

    if not_joined:
        buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="recheck")])
        await update.message.reply_text(
            "🚫 You must join required channel(s) first.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return False

    return True

async def recheck_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channels = load_json(FORCE_FILE)
    user_id = query.from_user.id

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return await query.edit_message_text("❌ Still not joined.")
        except:
            return await query.edit_message_text("❌ Error checking join.")

    await query.edit_message_text("✅ Join confirmed! Now send video number.")

# ---------------- COMMANDS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not await check_force_join(update, context):
        return

    await update.message.reply_text(
        "👋 Welcome!\n\nSend video number to receive video."
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Access Denied.")

    await update.message.reply_text(
        "👑 Admin Panel:\n\n"
        "/broadcast (reply to message)\n"
        "/addforce @channel\n"
        "/removeforce @channel"
    )

async def adminkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        return

    if context.args[0] == ADMIN_KEY:
        admins = load_json(ADMIN_FILE)
        admins[str(update.effective_user.id)] = True
        save_json(ADMIN_FILE, admins)
        await update.message.reply_text("✅ Admin access granted.")
    else:
        await update.message.reply_text("❌ Invalid key.")

async def addforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Access Denied.")

    if len(context.args) == 0:
        return await update.message.reply_text("Usage:\n/addforce @channelusername")

    channel = context.args[0]
    channels = load_json(FORCE_FILE)
    channels[channel] = True
    save_json(FORCE_FILE, channels)

    await update.message.reply_text(f"✅ {channel} added to force join.")

async def removeforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Access Denied.")

    if len(context.args) == 0:
        return await update.message.reply_text("Usage:\n/removeforce @channelusername")

    channel = context.args[0]
    channels = load_json(FORCE_FILE)

    if channel in channels:
        del channels[channel]
        save_json(FORCE_FILE, channels)
        await update.message.reply_text(f"❌ {channel} removed.")
    else:
        await update.message.reply_text("Channel not found.")

# ---------------- AUTO SYNC ---------------- #

async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post.video:
        return

    videos = load_json(VIDEOS_FILE)
    next_id = str(len(videos) + 1)

    videos[next_id] = {
        "chat_id": update.channel_post.chat_id,
        "message_id": update.channel_post.message_id,
    }

    save_json(VIDEOS_FILE, videos)

# ---------------- SEND VIDEO ---------------- #

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
        return await update.message.reply_text("Reply to message with /broadcast")

    users = load_json(USERS_FILE)
    success = 0

    for user_id in users:
        try:
            await context.bot.copy_message(
                chat_id=int(user_id),
                from_chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id,
            )
            success += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")

# ---------------- MAIN ---------------- #

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("adminkey", adminkey))
app.add_handler(CommandHandler("addforce", addforce))
app.add_handler(CommandHandler("removeforce", removeforce))
app.add_handler(CommandHandler("broadcast", broadcast))

app.add_handler(CallbackQueryHandler(recheck_callback, pattern="recheck"))

app.add_handler(
    MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_number)
)

app.add_handler(
    MessageHandler(filters.ChatType.CHANNEL, channel_post)
)

app.run_polling()
