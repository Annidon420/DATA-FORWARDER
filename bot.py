import os
import json
import logging
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("ADMIN_ID"))

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
CODES_FILE = f"{DATA_DIR}/codes.json"
FORCE_FILE = f"{DATA_DIR}/force.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"
VIDEOS_FILE = f"{DATA_DIR}/videos.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================== JSON SAFE HANDLING ==================

def load_json(file: str, default):
    try:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump(default, f)
        with open(file, "r") as f:
            return json.load(f)
    except Exception:
        logger.error(f"Corrupted JSON detected in {file}, resetting.")
        with open(file, "w") as f:
            json.dump(default, f)
        return default


def save_json(file: str, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# ================== LOAD DATA ==================

users = load_json(USERS_FILE, {})
codes = load_json(CODES_FILE, {})
force_channels = load_json(FORCE_FILE, [])
admins = load_json(ADMINS_FILE, [OWNER_ID])
videos = load_json(VIDEOS_FILE, {})


# ================== UTILITIES ==================

def is_admin(user_id: int) -> bool:
    return user_id in admins


async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    not_joined = []

    for channel in force_channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(channel)
        except Exception:
            not_joined.append(channel)

    if not_joined:
        buttons = [
            [InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{c.replace('@','')}")]
            for c in not_joined
        ]
        buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="recheck")])

        await update.effective_message.reply_text(
            "⚠️ You must join all required channels to use this bot.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return False

    return True


# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[str(user.id)] = {"username": user.username}
    save_json(USERS_FILE, users)

    if not await check_force_join(update, context):
        return

    await update.message.reply_text(
        "👋 Welcome!\n\nSend your access code to unlock content."
    )


# ================== FORCE JOIN CALLBACK ==================

async def recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await check_force_join(update, context):
        await query.edit_message_text("✅ Verified! Now send your access code.")


# ================== ACCESS CODE SYSTEM ==================

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return

    user_code = update.message.text.strip()

    if user_code in codes:
        await update.message.reply_text("✅ Access Granted!")
        if user_code in videos:
            await update.message.reply_video(videos[user_code])
    else:
        await update.message.reply_text("❌ Invalid Code.")


# ================== ADMIN COMMANDS ==================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "👮 Admin Panel\n\n"
        "/addcode CODE\n"
        "/addforce @channel\n"
        "/removeforce @channel\n"
        "/broadcast MESSAGE\n"
        "/adminkey USER_ID"
    )


async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /addcode CODE")

    code = context.args[0]
    codes[code] = True
    save_json(CODES_FILE, codes)
    await update.message.reply_text(f"✅ Code {code} added.")


async def addforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /addforce @channel")

    channel = context.args[0]
    if channel not in force_channels:
        force_channels.append(channel)
        save_json(FORCE_FILE, force_channels)
        await update.message.reply_text("✅ Channel added to force join.")


async def removeforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return

    channel = context.args[0]
    if channel in force_channels:
        force_channels.remove(channel)
        save_json(FORCE_FILE, force_channels)
        await update.message.reply_text("❌ Channel removed.")


async def adminkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        return

    new_admin = int(context.args[0])
    if new_admin not in admins:
        admins.append(new_admin)
        save_json(ADMINS_FILE, admins)
        await update.message.reply_text("✅ New admin added.")


# ================== BROADCAST ==================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return

    message = " ".join(context.args)
    sent = 0

    for user_id in users:
        try:
            await context.bot.send_message(int(user_id), message)
            sent += 1
        except Exception:
            continue

    await update.message.reply_text(f"📢 Broadcast sent to {sent} users.")


# ================== AUTO VIDEO SYNC ==================

async def auto_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.video:
        chat_id = str(update.channel_post.chat_id)
        caption = update.channel_post.caption

        if caption and caption.strip().isdigit():
            serial = caption.strip()
            videos[serial] = update.channel_post.video.file_id
            save_json(VIDEOS_FILE, videos)
            logger.info(f"Video synced with code {serial}")


# ================== MAIN ==================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addcode", addcode))
    app.add_handler(CommandHandler("addforce", addforce))
    app.add_handler(CommandHandler("removeforce", removeforce))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("adminkey", adminkey))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CallbackQueryHandler(recheck_join, pattern="recheck"))

    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, auto_sync))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
