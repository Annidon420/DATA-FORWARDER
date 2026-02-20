import os
import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))  # example: -1001234567890

# ============================================

# Database setup
conn = sqlite3.connect("videos.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    serial INTEGER PRIMARY KEY,
    message_id INTEGER
)
""")
conn.commit()


# ================== AUTO SYNC ==================

async def auto_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post

    if message and message.video:
        cursor.execute("SELECT MAX(serial) FROM videos")
        result = cursor.fetchone()[0]

        next_serial = 1 if result is None else result + 1

        cursor.execute(
            "INSERT INTO videos (serial, message_id) VALUES (?, ?)",
            (next_serial, message.message_id),
        )
        conn.commit()

        print(f"New video saved with serial {next_serial}")


# ================== USER NUMBER HANDLER ==================

async def send_video_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit():
        return

    serial = int(text)

    cursor.execute("SELECT message_id FROM videos WHERE serial = ?", (serial,))
    result = cursor.fetchone()

    if result:
        message_id = result[0]

        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=STORAGE_CHANNEL_ID,
            message_id=message_id,
        )
    else:
        await update.message.reply_text("Video not found.")


# ================== START COMMAND ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a number to get a video.")


# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Listen to new channel posts
    app.add_handler(MessageHandler(filters.Chat(STORAGE_CHANNEL_ID) & filters.VIDEO, auto_sync))

    # Listen to user numbers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_video_by_number))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
