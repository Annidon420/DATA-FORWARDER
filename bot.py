import os
import json
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

# ================= CONFIG ================= #

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = f"{DATA_DIR}/users.json"
CODES_FILE = f"{DATA_DIR}/codes.json"
FORCE_FILE = f"{DATA_DIR}/force.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

# ================= JSON HELPERS ================= #

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


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


# ================= FORCE JOIN SYSTEM ================= #

async def check_force_join(user_id, context):
    channels = load_json(FORCE_FILE)
    not_joined = []

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)

        except Exception as e:
            print(f"Force join error: {e}")
            not_joined.append(channel)

    return not_joined


async def send_force_message(update, context, channels):
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
        InlineKeyboardButton("✅ I Joined", callback_data="recheck_join")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🚫 To continue, please join required channels:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🚫 To continue, please join required channels:",
            reply_markup=reply_markup
        )


async def recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    not_joined = await check_force_join(user_id, context)

    if not not_joined:
        await query.edit_message_text(
            "✅ Verification Successful!\n\nNow send your access code."
        )
    else:
        await send_force_message(update, context, not_joined)


# ================= MESSAGE HANDLER ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Check force join first
    not_joined = await check_force_join(user_id, context)
    if not_joined:
        return await send_force_message(update, context, not_joined)

    codes = load_json(CODES_FILE)

    if text in codes:
        await update.message.reply_text("🎉 Access Granted!")
    else:
        await update.message.reply_text("❌ Invalid Code.")


# ================= ADMIN PANEL ================= #

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
        return await update.message.reply_text("❌ Only owner can add admins.")

    if not context.args:
        return await update.message.reply_text("Usage:\n/adminkey USER_ID")

    admins = load_json(ADMINS_FILE)
    admins[context.args[0]] = True
    save_json(ADMINS_FILE, admins)

    await update.message.reply_text("✅ Admin added successfully.")


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
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast Completed\n\nSent: {sent}\nFailed: {failed}"
    )


# ================= MAIN ================= #

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("adminkey", adminkey))
app.add_handler(CommandHandler("addcode", addcode))
app.add_handler(CommandHandler("addforce", addforce))
app.add_handler(CommandHandler("removeforce", removeforce))
app.add_handler(CommandHandler("broadcast", broadcast))

app.add_handler(CallbackQueryHandler(recheck_join, pattern="recheck_join"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
