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

# -------------------- CONFIG --------------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
ADMINS_FILE = DATA_DIR / "admins.json"
FORCE_FILE = DATA_DIR / "force.json"
CODES_FILE = DATA_DIR / "codes.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -------------------- JSON SAFE LOAD --------------------
def load_json(file, default):
    try:
        if file.exists():
            with open(file, "r") as f:
                return json.load(f)
        else:
            return default
    except:
        return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# Initialize files
for file in [USERS_FILE, ADMINS_FILE, FORCE_FILE, CODES_FILE]:
    if not file.exists():
        save_json(file, {})

admins = load_json(ADMINS_FILE, {})
admins[str(ADMIN_ID)] = True
save_json(ADMINS_FILE, admins)

# -------------------- UTIL --------------------
def is_admin(user_id):
    admins = load_json(ADMINS_FILE, {})
    return str(user_id) in admins


# -------------------- FORCE JOIN CHECK --------------------
async def check_force_join(user_id, context):
    force_channels = load_json(FORCE_FILE, {})
    not_joined = []

    for channel in force_channels.values():
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)

    return not_joined


# -------------------- START --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    users = load_json(USERS_FILE, {})
    users[str(user_id)] = True
    save_json(USERS_FILE, users)

    not_joined = await check_force_join(user_id, context)

    if not_joined:
        buttons = []
        for channel in not_joined:
            chat = await context.bot.get_chat(channel)
            buttons.append(
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{chat.username}")]
            )

        buttons.append(
            [InlineKeyboardButton("I Joined", callback_data="recheck")]
        )

        await update.message.reply_text(
            "Please join all required channels.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    await update.message.reply_text(
        "Send the serial number to receive your video."
    )


# -------------------- RECHECK --------------------
async def recheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    not_joined = await check_force_join(user_id, context)

    if not not_joined:
        await query.edit_message_text(
            "Access granted! Send the serial number."
        )
    else:
        await query.answer("You still have not joined all channels.", show_alert=True)


# -------------------- AUTO VIDEO SYNC --------------------
async def auto_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != STORAGE_CHANNEL_ID:
        return

    if update.message.video:
        codes = load_json(CODES_FILE, {})
        serial = str(len(codes) + 1)
        codes[serial] = {
            "file_id": update.message.video.file_id
        }
        save_json(CODES_FILE, codes)

        logging.info(f"Video synced with serial {serial}")


# -------------------- USER REQUEST VIDEO --------------------
async def send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text.isdigit():
        return

    not_joined = await check_force_join(user_id, context)
    if not_joined:
        await update.message.reply_text("Join required channels first.")
        return

    codes = load_json(CODES_FILE, {})

    if text in codes:
        file_id = codes[text]["file_id"]
        await update.message.reply_video(file_id)
    else:
        await update.message.reply_text("Invalid Code")


# -------------------- ADMIN --------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "/addforce @channel\n"
        "/removeforce @channel\n"
        "/broadcast message"
    )


async def add_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    channel = context.args[0].replace("@", "")
    force = load_json(FORCE_FILE, {})
    force[channel] = channel
    save_json(FORCE_FILE, force)

    await update.message.reply_text("Channel added.")


async def remove_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    channel = context.args[0].replace("@", "")
    force = load_json(FORCE_FILE, {})
    if channel in force:
        del force[channel]
        save_json(FORCE_FILE, force)

    await update.message.reply_text("Channel removed.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    message = " ".join(context.args)
    users = load_json(USERS_FILE, {})

    success = 0
    for user_id in users:
        try:
            await context.bot.send_message(user_id, message)
            success += 1
        except:
            pass

    await update.message.reply_text(f"Sent to {success} users.")


# -------------------- MAIN --------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addforce", add_force))
    app.add_handler(CommandHandler("removeforce", remove_force))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(recheck, pattern="recheck"))

    app.add_handler(MessageHandler(filters.Chat(STORAGE_CHANNEL_ID) & filters.VIDEO, auto_sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_video))

    logging.info("Bot Started")
    app.run_polling()


if __name__ == "__main__":
    main()
