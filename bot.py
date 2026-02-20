import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_KEY = "8006902002"

logging.basicConfig(level=logging.INFO)

# ---------------- JSON Helpers ---------------- #

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- User System ---------------- #

def add_user(user_id):
    users = load_json("users.json")
    if user_id not in users["users"]:
        users["users"].append(user_id)
        save_json("users.json", users)

def is_admin(user_id):
    admins = load_json("admins.json")
    return user_id in admins["admins"]

# ---------------- Force Join Check ---------------- #

async def check_force_join(user_id, context):
    force = load_json("forcejoin.json")

    if not force["enabled"] or not force["channels"]:
        return True

    for channel in force["channels"]:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status == "left":
                return False
        except:
            return False

    return True

# ---------------- Admin Key ---------------- #

async def adminkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    if context.args[0] == ADMIN_KEY:
        admins = load_json("admins.json")
        if update.effective_user.id not in admins["admins"]:
            admins["admins"].append(update.effective_user.id)
            save_json("admins.json", admins)

        await update.message.reply_text("✅ You are now admin.")
    else:
        await update.message.reply_text("❌ Invalid key.")

# ---------------- Force Join Commands ---------------- #

async def addforce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    force = load_json("forcejoin.json")
    force["channels"].append(context.args[0])
    save_json("forcejoin.json", force)

    await update.message.reply_text("✅ Channel added.")

async def forceon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    force = load_json("forcejoin.json")
    force["enabled"] = True
    save_json("forcejoin.json", force)

    await update.message.reply_text("🔥 Force join enabled.")

async def forceoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    force = load_json("forcejoin.json")
    force["enabled"] = False
    save_json("forcejoin.json", force)

    await update.message.reply_text("🛑 Force join disabled.")

# ---------------- Broadcast ---------------- #

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    text = " ".join(context.args)
    users = load_json("users.json")["users"]

    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=text)
        except:
            pass

    await update.message.reply_text("✅ Broadcast complete.")

async def broadcastphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not update.message.photo:
        return

    caption = update.message.caption.replace("/broadcastphoto", "").strip()
    photo = update.message.photo[-1].file_id
    users = load_json("users.json")["users"]

    for user in users:
        try:
            await context.bot.send_photo(chat_id=user, photo=photo, caption=caption)
        except:
            pass

    await update.message.reply_text("✅ Photo broadcast complete.")

# ---------------- Video Auto Sync ---------------- #

async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post.video:
        videos = load_json("videos.json")
        next_number = str(len(videos) + 1)
        videos[next_number] = update.channel_post.video.file_id
        save_json("videos.json", videos)

        print(f"Video synced as {next_number}")

# ---------------- Main Message ---------------- #

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if update.message.text and update.message.text.isdigit():

        allowed = await check_force_join(user_id, context)

        if not allowed:
            force = load_json("forcejoin.json")
            buttons = [
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{ch.replace('@','')}")]
                for ch in force["channels"]
            ]
            await update.message.reply_text(
                "⚠️ Please join required channel(s).",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return

        videos = load_json("videos.json")

        if update.message.text in videos:
            await update.message.reply_video(videos[update.message.text])

# ---------------- Start App ---------------- #

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("adminkey", adminkey))
app.add_handler(CommandHandler("addforce", addforce))
app.add_handler(CommandHandler("forceon", forceon))
app.add_handler(CommandHandler("forceoff", forceoff))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.PHOTO & filters.Caption("/broadcastphoto"), broadcastphoto))
app.add_handler(MessageHandler(filters.ALL & filters.ChatType.CHANNEL, channel_post))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Bot Running...")
app.run_polling()
