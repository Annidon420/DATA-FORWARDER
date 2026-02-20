import os
import json
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==============================
# ENV VARIABLES
# ==============================
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("ADMIN_ID"))
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL"))  # Numeric ID of private channel

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==============================
# DATA DIRECTORY
# ==============================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
CODES_FILE = DATA_DIR / "codes.json"
FORCE_FILE = DATA_DIR / "force.json"
ADMINS_FILE = DATA_DIR / "admins.json"

# ==============================
# JSON HELPERS
# ==============================
def load_json(file_path, default):
    try:
        if not file_path.exists():
            with open(file_path, "w") as f:
                json.dump(default, f)
            return default
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception:
        with open(file_path, "w") as f:
            json.dump(default, f)
        return default

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_FILE, [])
codes = load_json(CODES_FILE, {})  # serial: file_id
force_channels = load_json(FORCE_FILE, [])
admins = load_json(ADMINS_FILE, [OWNER_ID])

# ==============================
# HELPERS
# ==============================
def is_admin(user_id: int) -> bool:
    return user_id in admins

async def verify_force_join(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in force_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def build_force_keyboard():
    buttons = [[InlineKeyboardButton("I Joined", callback_data="recheck_join")]]
    return InlineKeyboardMarkup(buttons)

# ==============================
# START COMMAND
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in users:
        users.append(user.id)
        save_json(USERS_FILE, users)

    if force_channels:
        joined = await verify_force_join(user.id, context)
        if not joined:
            await update.message.reply_text(
                "⚠️ You must join all required channels first.",
                reply_markup=build_force_keyboard()
            )
            return

    await update.message.reply_text("👋 Welcome! Send your access code.")

async def recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    joined = await verify_force_join(user_id, context)
    if joined:
        await query.edit_message_text("✅ Verification successful! Send your access code.")
    else:
        await query.answer("❌ You have not joined all channels.", show_alert=True)

# ==============================
# CODE ACCESS SYSTEM
# ==============================
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in codes:
        await update.message.reply_text(f"✅ Access Granted for video serial {text}!")
    else:
        await update.message.reply_text("❌ Invalid Code.")

async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /addcode CODE")
        return
    code = context.args[0]
    codes[code] = None
    save_json(CODES_FILE, codes)
    await update.message.reply_text(f"✅ Code added: {code}")

# ==============================
# FORCE MANAGEMENT
# ==============================
async def add_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    channel = context.args[0]
    if channel not in force_channels:
        force_channels.append(channel)
        save_json(FORCE_FILE, force_channels)
    await update.message.reply_text("✅ Force channel added.")

async def remove_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    channel = context.args[0]
    if channel in force_channels:
        force_channels.remove(channel)
        save_json(FORCE_FILE, force_channels)
    await update.message.reply_text("✅ Force channel removed.")

# ==============================
# ADMIN SYSTEM
# ==============================
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        return
    new_admin = int(context.args[0])
    if new_admin not in admins:
        admins.append(new_admin)
        save_json(ADMINS_FILE, admins)
    await update.message.reply_text("✅ Admin added.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "Admin Panel:\n/addcode CODE\n/addforce @channel\n/removeforce @channel\n/broadcast MESSAGE"
    )

# ==============================
# BROADCAST
# ==============================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    message = " ".join(context.args)
    success = 0
    for user_id in users:
        try:
            await context.bot.send_message(user_id, message)
            success += 1
        except:
            continue
    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")

# ==============================
# AUTO-SYNC FOR STORAGE CHANNEL
# ==============================
async def auto_video_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        return
    if update.message.chat_id != STORAGE_CHANNEL:
        return
    serial = str(len(codes) + 1)
    codes[serial] = update.message.video.file_id
    save_json(CODES_FILE, codes)
    logger.info(f"Auto-sync: Video in channel assigned serial {serial}")

# ==============================
# MAIN FUNCTION
# ==============================
def main():
    if not TOKEN or not OWNER_ID or not STORAGE_CHANNEL:
        raise ValueError("Please set TOKEN, ADMIN_ID, STORAGE_CHANNEL environment variables")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addcode", add_code))
    app.add_handler(CommandHandler("addforce", add_force))
    app.add_handler(CommandHandler("removeforce", remove_force))
    app.add_handler(CommandHandler("adminkey", add_admin))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(recheck_join, pattern="recheck_join"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(MessageHandler(filters.VIDEO, auto_video_serial))

    logger.info("Bot started successfully.")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
