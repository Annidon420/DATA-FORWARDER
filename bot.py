import os
import json
import logging
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    logger.error("TOKEN environment variable is missing")
    sys.exit(1)

ADMIN_ID_STR = os.environ.get("ADMIN_ID")
if not ADMIN_ID_STR:
    logger.error("ADMIN_ID environment variable is missing")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_ID_STR)
except ValueError:
    logger.error("ADMIN_ID must be an integer")
    sys.exit(1)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_file(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        logger.warning(f"Corrupted or missing file {filename}, initializing with default")
        return default if default is not None else []

def save_file(data, filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save {filename}: {e}")

def load_admins():
    admins = load_file("admins.json", [])
    if ADMIN_ID not in admins:
        admins.append(ADMIN_ID)
        save_file(admins, "admins.json")
    return set(admins)

async def check_joined(user_id: int, bot) -> bool:
    forces = load_file("force.json", [])
    for channel in forces:
        try:
            await bot.get_chat_member(channel, user_id)
        except BadRequest as e:
            if "user_not_participant" in e.message.lower():
                return False
            else:
                logger.error(f"Error checking membership in {channel}: {e}")
                return False
    return True

async def show_join_buttons(message):
    forces = load_file("force.json", [])
    buttons = [[InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel[1:]}")] for channel in forces]
    buttons.append([InlineKeyboardButton("I Joined", callback_data="check_join")])
    markup = InlineKeyboardMarkup(buttons)
    await message.reply_text("Please join the following channels to access the bot:", reply_markup=markup)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_file("users.json", [])
    if user_id not in users:
        users.append(user_id)
        save_file(users, "users.json")
    forces = load_file("force.json", [])
    if not forces:
        await update.message.reply_text("Welcome! Send your access code.")
        return
    if await check_joined(user_id, context.bot):
        await update.message.reply_text("Welcome! You have joined all channels. Send your access code.")
    else:
        await show_join_buttons(update.message)

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if await check_joined(user_id, context.bot):
        await query.edit_message_text("You have joined all channels successfully! Now send your access code.")
    else:
        await query.edit_message_text("You haven't joined all channels yet. Please join them.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admins = load_admins()
    if user_id not in admins and not await check_joined(user_id, context.bot):
        await show_join_buttons(update.message)
        return
    text = update.message.text.strip()
    codes = set(load_file("codes.json", []))
    if text in codes:
        await update.message.reply_text("Access Granted")
        videos = load_file("videos.json", {})
        if text in videos:
            file_id = videos[text]
            try:
                await context.bot.send_video(update.message.chat.id, file_id)
            except Exception as e:
                logger.error(f"Failed to send video for code {text}: {e}")
                await update.message.reply_text("Error sending content. Please contact admin.")
    else:
        await update.message.reply_text("Invalid Code")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_file("config.json", {"private_channel": None})
    private_channel = config.get("private_channel")
    if not private_channel or update.message.chat.id != private_channel:
        return
    if update.message.video:
        file_id = update.message.video.file_id
        videos = load_file("videos.json", {})
        serial = len(videos) + 1
        code = str(serial)
        videos[code] = file_id
        save_file(videos, "videos.json")
        codes = load_file("codes.json", [])
        if code not in codes:
            codes.append(code)
            save_file(codes, "codes.json")
        await update.message.reply_text(f"Video added with code: {code}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    text = """Admin Panel:

- /addcode <code> - Add an access code
- /addforce @channel - Add a force join channel
- /removeforce @channel - Remove a force join channel
- /broadcast <message> - Broadcast to all users
- /setprivate <channel_id> - Set private channel for auto-sync videos
- /adminkey <user_id> - Add new admin (owner only)"""
    await update.message.reply_text(text)

async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    if not context.args:
        await update.message.reply_text("Usage: /addcode <code>")
        return
    code = " ".join(context.args)
    codes = load_file("codes.json", [])
    if code not in codes:
        codes.append(code)
        save_file(codes, "codes.json")
        await update.message.reply_text("Code added successfully.")
    else:
        await update.message.reply_text("Code already exists.")

async def add_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    if not context.args:
        await update.message.reply_text("Usage: /addforce @channel")
        return
    channel = context.args[0]
    if not channel.startswith("@"):
        await update.message.reply_text("Channel must start with @")
        return
    try:
        me = await context.bot.get_chat_member(channel, context.bot.id)
        if me.status != "administrator":
            await update.message.reply_text("Please make me an administrator in the channel first.")
            return
    except BadRequest as e:
        await update.message.reply_text(f"Error: {e.message}")
        return
    forces = load_file("force.json", [])
    if channel not in forces:
        forces.append(channel)
        save_file(forces, "force.json")
        await update.message.reply_text("Force join channel added successfully.")
    else:
        await update.message.reply_text("Channel already added.")

async def remove_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    if not context.args:
        await update.message.reply_text("Usage: /removeforce @channel")
        return
    channel = context.args[0]
    forces = load_file("force.json", [])
    if channel in forces:
        forces.remove(channel)
        save_file(forces, "force.json")
        await update.message.reply_text("Force join channel removed successfully.")
    else:
        await update.message.reply_text("Channel not found.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message_text = " ".join(context.args)
    users = load_file("users.json", [])
    sent = 0
    failed = 0
    for user in users:
        try:
            await context.bot.send_message(user, message_text, disable_notification=True)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to broadcast to {user}: {e}")
    await update.message.reply_text(f"Broadcast complete: Sent to {sent} users, failed for {failed} users.")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /adminkey <user_id>")
        return
    try:
        new_admin = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    admins = load_file("admins.json", [])
    if new_admin not in admins:
        admins.append(new_admin)
        save_file(admins, "admins.json")
        await update.message.reply_text("New admin added successfully.")
    else:
        await update.message.reply_text("User is already an admin.")

async def set_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_admins():
        return
    if not context.args:
        await update.message.reply_text("Usage: /setprivate <channel_id>")
        return
    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid channel ID.")
        return
    config = load_file("config.json", {})
    config["private_channel"] = channel_id
    save_file(config, "config.json")
    await update.message.reply_text(f"Private channel set to {channel_id}.")

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("addcode", add_code))
    application.add_handler(CommandHandler("addforce", add_force))
    application.add_handler(CommandHandler("removeforce", remove_force))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("adminkey", add_admin))
    application.add_handler(CommandHandler("setprivate", set_private))
    application.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.run_polling()
