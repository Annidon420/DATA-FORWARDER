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
# SAFE JSON HANDLING
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
        logger.warning(f"Corrupted JSON detected in {file_path}, resetting.")
        with open(file_path, "w") as f:
            json.dump(default, f)
        return default

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")

users = load_json(USERS_FILE, [])
codes = load_json(CODES_FILE, {})
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
        except Exception as e:
            logger.error(f"Force check failed for {channel}: {e}")
            return False
    return True

def build_force_keyboard():
    buttons = []
    for channel in force_channels:
        username = channel.replace("@", "")
        buttons.append([InlineKeyboardButton("Join Channel", url=f"https://t.me/{username}")])
    buttons.append([InlineKeyboardButton("I Joined", callback_data="recheck_join")])
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

    await update.message.reply_text(
        "👋 Welcome!\n\nSend your access code to continue."
    )

# ==============================
# FORCE RECHECK CALLBACK
# ==============================

async def recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    joined = await verify_force_join(user_id, context)

    if joined:
        await query.edit_message_text(
            "✅ Verification successful!\nNow send your access code."
        )
    else:
        await query.answer("❌ You have not joined all channels.", show_alert=True)

# ==============================
# CODE SYSTEM
# ==============================

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text in codes:
        await update.message.reply_text("✅ Access Granted!")
    else:
        await update.message.reply_text("❌ Invalid Code.")

async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /addcode CODE")
        return

    code = context.args[0]
    codes[code] = True
    save_json(CODES_FILE, codes)

    await update.message.reply_text(f"✅ Code added: {code}")

# ==============================
# FORCE MANAGEMENT
# ==============================

async def add_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /addforce @channel")
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
        "Admin Panel:\n\n"
        "/addcode CODE\n"
        "/addforce @channel\n"
        "/removeforce @channel\n"
        "/broadcast MESSAGE"
    )

# ==============================
# BROADCAST
# ==============================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast MESSAGE")
        return

    message = " ".join(context.args)
    success = 0

    for user_id in users:
        try:
            await context.bot.send_message(user_id, message)
            success += 1
        except Exception:
            continue

    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")

# ==============================
# AUTO VIDEO SYNC (STORAGE_CHANNEL)
# ==============================

async def auto_video_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        return

    chat_id = update.message.chat_id
    if chat_id != STORAGE_CHANNEL:
        return  # Only process videos from STORAGE_CHANNEL

    # Generate next serial code
    serial = str(len(codes) + 1)
    codes[serial] = True
    save_json(CODES_FILE, codes)

    # DM owner
    try:
        await context.bot.send_message(
            OWNER_ID,
            f"🎬 New video uploaded.\nAccess Code: {serial}"
        )
    except Exception as e:
        logger.error(f"Failed to DM OWNER_ID: {e}")

    logger.info(f"Auto-sync code {serial} created successfully.")

# ==============================
# MAIN FUNCTION
# ==============================

def main():
    if not TOKEN:
        raise ValueError("TOKEN environment variable not set")
    if not OWNER_ID:
        raise ValueError("ADMIN_ID environment variable not set")
    if not STORAGE_CHANNEL:
        raise ValueError("STORAGE_CHANNEL environment variable not set")

    app = ApplicationBuilder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addcode", add_code))
    app.add_handler(CommandHandler("addforce", add_force))
    app.add_handler(CommandHandler("removeforce", remove_force))
    app.add_handler(CommandHandler("adminkey", add_admin))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Callback query for "I Joined"
    app.add_handler(CallbackQueryHandler(recheck_join, pattern="recheck_join"))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(MessageHandler(filters.VIDEO, auto_video_serial))

    logger.info("Bot started successfully.")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
