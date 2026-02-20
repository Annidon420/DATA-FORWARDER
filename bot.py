import os
import json
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= LOGGING ================= #

logging.basicConfig(level=logging.INFO)

# ================= CONFIG ================= #

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = f"{DATA_DIR}/users.json"
CODES_FILE = f"{DATA_DIR}/codes.json"
FORCE_FILE = f"{DATA_DIR}/force.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

# ================= SAFE JSON ================= #

def load_json(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def is_admin(user_id):
    admins = load_json(ADMINS_FILE)
    return str(user_id) in admins or user_id == ADMIN_ID

# ================= START ================= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_json(USERS_FILE)

    users[str(user.id)] = user.first_name
    save_json(USERS_FILE, users)

    await update.message.reply_text(
        "👋 Welcome!\n\nSend your access code to continue."
    )

# ================= FORCE JOIN ================= #

async def check_force(user_id, context):
    channels = load_json(FORCE_FILE)
    not_joined = []

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)

        except Exception as e:
            logging.error(f"Force Join Error: {e}")
            not_joined.append(channel)

    return not_joined

async def send_force(update, context, channels):
    keyboard = []

    for channel in channels:
        username = channel.replace("@", "")
        keyboard.append([
            InlineKeyboardButton(
                f"📢 Join {channel}",
                url=f"https://t.me/{username}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("✅ I Joined", callback_data="force_check")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🚫 Please join required channels first:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🚫 Please join required channels first:",
            reply_markup=reply_markup
        )

async def force_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # VERY IMPORTANT

    user_id = query.from_user.id
    not_joined = await check_force(user_id, context)

    if not not_joined:
        await query.edit_message_text(
            "✅ Verification successful!\n\nNow send your code."
        )
    else:
        await send_force(update, context, not_joined)

# ================= MESSAGE ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    not_joined = await check_force(user_id, context)
    if not_joined:
        return await send_force(update, context, not_joined)

    codes = load_json(CODES_FILE)

    if text in codes:
        await update.message.reply_text("🎉 Access Granted!")
    else:
        await update.message.reply_text("❌ Invalid Code.")

# ================= ADMIN ================= #

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Access Denied.")

    await update.message.reply_text(
        "🔐 Admin Panel\n\n"
        "/addcode CODE\n"
        "/addforce @channel\n"
        "/removeforce @channel\n"
        "/broadcast MESSAGE\n"
        "/adminkey USER_ID"
    )

# ================= ADMIN COMMANDS ================= #

async def adminkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Only owner allowed.")

    if not context.args:
        return await update.message.reply_text("Usage:\n/adminkey USER_ID")

    admins = load_json(ADMINS_FILE)
    admins[context.args[0]] = True
    save_json(ADMINS_FILE, admins)

    await update.message.reply_text("✅ Admin added.")

async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Usage:\n/addcode CODE")

    codes = load_json(CODES_FILE)
    codes[context.args[0]] = True
    save_json(CODES_FILE, codes)

    await update.message.reply_text("✅ Code added.")

async def addforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Usage:\n/addforce @channel")

    channels = load_json(FORCE_FILE)
    channels[context.args[0]] = True
    save_json(FORCE_FILE, channels)

    await update.message.reply_text("✅ Force channel added.")

async def removeforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Usage:\n/removeforce @channel")

    channels = load_json(FORCE_FILE)

    if context.args[0] in channels:
        del channels[context.args[0]]
        save_json(FORCE_FILE, channels)
        await update.message.reply_text("❌ Force channel removed.")
    else:
        await update.message.reply_text("Channel not found.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Usage:\n/broadcast MESSAGE")

    message = " ".join(context.args)
    users = load_json(USERS_FILE)

    sent = 0
    failed = 0

    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=message
            )
            sent += 1
        except Exception as e:
            logging.error(f"Broadcast Error: {e}")
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast Finished\n\nSent: {sent}\nFailed: {failed}"
    )

# ================= MAIN ================= #

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("adminkey", adminkey))
    app.add_handler(CommandHandler("addcode", addcode))
    app.add_handler(CommandHandler("addforce", addforce))
    app.add_handler(CommandHandler("removeforce", removeforce))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(force_check_callback, pattern="force_check"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 🔥 AUTOSYNC COMMANDS
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
