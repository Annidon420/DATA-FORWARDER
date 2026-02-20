import config
import database
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

admin_sessions = {}
waiting_for_video = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /get to receive video.")

async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor = database.cursor
    conn = database.conn

    cursor.execute("SELECT current_serial FROM pointer WHERE id=1")
    current_serial = cursor.fetchone()[0]

    cursor.execute("SELECT message_id FROM videos WHERE serial=?", (current_serial,))
    result = cursor.fetchone()

    if result is None:
        await update.message.reply_text("No videos available.")
        return

    message_id = result[0]

    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=config.STORAGE_CHANNEL_ID,
        message_id=message_id
    )

    cursor.execute("SELECT MAX(serial) FROM videos")
    max_serial = cursor.fetchone()[0]

    next_serial = current_serial + 1
    if next_serial > max_serial:
        next_serial = 1

    cursor.execute("UPDATE pointer SET current_serial=? WHERE id=1", (next_serial,))
    conn.commit()

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("Not allowed.")
        return

    admin_sessions[update.effective_user.id] = "waiting_password"
    await update.message.reply_text("Enter admin password:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in admin_sessions and admin_sessions[user_id] == "waiting_password":
        if update.message.text == config.ADMIN_PASSWORD:
            admin_sessions[user_id] = "logged_in"
            await update.message.reply_text("Admin logged in. Send /addvideo")
        else:
            await update.message.reply_text("Wrong password.")
            del admin_sessions[user_id]

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        return

    if admin_sessions[update.effective_user.id] != "logged_in":
        return

    waiting_for_video[update.effective_user.id] = True
    await update.message.reply_text("Send video from storage channel.")

async def save_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in waiting_for_video:
        return

    if not update.message.video:
        return

    cursor = database.cursor
    conn = database.conn

    cursor.execute("SELECT MAX(serial) FROM videos")
    result = cursor.fetchone()[0]
    next_serial = 1 if result is None else result + 1

    cursor.execute(
        "INSERT INTO videos (serial, message_id) VALUES (?, ?)",
        (next_serial, update.message.message_id)
    )
    conn.commit()

    await update.message.reply_text(f"Video added with serial {next_serial}")
    del waiting_for_video[user_id]

def main():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get_video))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addvideo", add_video))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, save_video))

    app.run_polling()

if __name__ == "__main__":
    main()
