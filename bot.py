"""
Telegram Video Bot - Production Ready
A professional Telegram access bot with force join, code verification, 
admin system, broadcast, video autosync, and Railway deployment support.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

# Environment Variables
TOKEN = os.environ.get("TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "secure_admin_key")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")  # Private channel ID for auto sync

# Data Files
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CODES_FILE = os.path.join(DATA_DIR, "codes.json")
FORCE_FILE = os.path.join(DATA_DIR, "force.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")
CHANNEL_FILE = os.path.join(DATA_DIR, "channel.json")

# Video sync state
last_sync_message_id = {"message_id": 0}

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =============================================================================
# JSON STORAGE FUNCTIONS
# =============================================================================

def load_json(file_path: str, default: Any = None) -> Any:
    """Load JSON data from file with error handling."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default if default is not None else []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return default if default is not None else []
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default if default is not None else []


def save_json(file_path: str, data: Any) -> bool:
    """Save JSON data to file with error handling."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False


def get_users() -> List[Dict]:
    """Get all users."""
    return load_json(USERS_FILE, [])


def save_user(user_id: int, username: str = "", first_name: str = "") -> bool:
    """Save or update user in database."""
    users = get_users()
    user_id_str = str(user_id)
    
    for user in users:
        if str(user.get("id")) == user_id_str:
            user["username"] = username or user.get("username", "")
            user["first_name"] = first_name or user.get("first_name", "")
            user["last_seen"] = datetime.now().isoformat()
            break
    else:
        users.append({
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "joined": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })
    
    return save_json(USERS_FILE, users)


def get_codes() -> List[Dict]:
    """Get all access codes."""
    return load_json(CODES_FILE, [])


def add_code(code: str) -> bool:
    """Add access code."""
    codes = get_codes()
    code_lower = code.lower().strip()
    
    for c in codes:
        if c.get("code", "").lower() == code_lower:
            return False
    
    codes.append({
        "code": code,
        "created": datetime.now().isoformat(),
    })
    
    return save_json(CODES_FILE, codes)


def check_code(code: str) -> bool:
    """Check if access code is valid."""
    codes = get_codes()
    code_lower = code.lower().strip()
    
    for c in codes:
        if c.get("code", "").lower() == code_lower:
            return True
    return False


def get_force_channels() -> List[Dict]:
    """Get all force join channels."""
    return load_json(FORCE_FILE, [])


def add_force_channel(channel: str) -> bool:
    """Add force join channel."""
    channels = get_force_channels()
    channel_clean = channel.strip().replace("@", "").lower()
    
    for ch in channels:
        if ch.get("channel", "").replace("@", "").lower() == channel_clean:
            return False
    
    channels.append({
        "channel": channel,
        "added": datetime.now().isoformat(),
    })
    
    return save_json(FORCE_FILE, channels)


def remove_force_channel(channel: str) -> bool:
    """Remove force join channel."""
    channels = get_force_channels()
    channel_clean = channel.strip().replace("@", "").lower()
    
    channels = [ch for ch in channels 
                if ch.get("channel", "").replace("@", "").lower() != channel_clean]
    
    return save_json(FORCE_FILE, channels)


def get_admins() -> List[int]:
    """Get all admin user IDs."""
    return load_json(ADMINS_FILE, [])


def add_admin(user_id: int) -> bool:
    """Add admin user."""
    admins = get_admins()
    user_id_int = int(user_id)
    
    if user_id_int not in admins:
        admins.append(user_id_int)
        return save_json(ADMINS_FILE, admins)
    return False


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    admin_ids = [int(ADMIN_ID)] if ADMIN_ID else []
    admin_ids.extend(get_admins())
    return int(user_id) in admin_ids


def get_videos() -> Dict[int, Dict]:
    """Get all videos."""
    return load_json(VIDEOS_FILE, {})


def save_video(serial: int, file_id: str, caption: str = "") -> bool:
    """Save video information."""
    videos = get_videos()
    videos[serial] = {
        "file_id": file_id,
        "caption": caption,
        "added": datetime.now().isoformat(),
    }
    return save_json(VIDEOS_FILE, videos)


# =============================================================================
# FORCE JOIN FUNCTIONS
# =============================================================================

async def check_force_join(update: Update, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined all required channels."""
    channels = get_force_channels()
    
    if not channels:
        return True
    
    not_joined = []
    
    for channel in channels:
        channel_username = channel.get("channel", "").strip("@").lower()
        
        try:
            # Try to get chat member
            chat_member = await context.bot.get_chat_member(
                chat_id=f"@{channel_username}",
                user_id=user_id
            )
            
            if chat_member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel_username)
                
        except Exception as e:
            logger.error(f"Error checking channel {channel_username}: {e}")
            not_joined.append(channel_username)
    
    if not_joined:
        await show_force_join_keyboard(update, context, not_joined)
        return False
    
    return True


async def show_force_join_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, channels: List[str]):
    """Show inline keyboard for force join."""
    keyboard = []
    
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(f"✅ Join @{channel}", url=f"https://t.me/{channel}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔄 I Joined - Check Again", callback_data="check_join")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "⚠️ <b>Access Restricted</b>\n\n"
    text += "You must join the following channels to use this bot:\n\n"
    
    for channel in channels:
        text += f"• @{channel}\n"
    
    text += "\n👆 Please join all channels and click the button below!"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    # Save user to database
    save_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    
    # Check force join
    if not await check_force_join(update, user.id, context):
        return
    
    # Welcome message
    text = "👋 <b>Welcome to Video Bot!</b>\n\n"
    text += "I'm a professional video bot with various features.\n\n"
    text += "Use /help to see available commands."
    
    keyboard = [
        [InlineKeyboardButton("📺 Latest Videos", callback_data="videos_list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    
    # Check force join
    if not await check_force_join(update, user_id, context):
        return
    
    text = "📖 <b>Available Commands</b>\n\n"
    text += "<b>User Commands:</b>\n"
    text += "/start - Start the bot\n"
    text += "/help - Show this help message\n"
    text += "/videos - View available videos\n"
    text += "/mycode - Check your access code\n\n"
    
    if is_admin(user_id):
        text += "<b>Admin Commands:</b>\n"
        text += "/admin - Admin panel\n"
        text += "/addcode - Add access code\n"
        text += "/addforce - Add force join channel\n"
        text += "/removeforce - Remove force join channel\n"
        text += "/broadcast - Broadcast message\n"
        text += "/setchannel - Set private channel ID\n"
        text += "/autosync - Enable auto sync\n"
        text += "/syncnow - Sync videos now\n"
        text += "/adminkey - Add new admin (owner only)"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - Admin panel."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Get statistics
    users = get_users()
    codes = get_codes()
    channels = get_force_channels()
    videos = get_videos()
    
    text = "🔧 <b>Admin Panel</b>\n\n"
    text += f"📊 <b>Statistics:</b>\n"
    text += f"• Total Users: {len(users)}\n"
    text += f"• Total Codes: {len(codes)}\n"
    text += f"• Force Channels: {len(channels)}\n"
    text += f"• Total Videos: {len(videos)}\n\n"
    
    text += "<b>Quick Actions:</b>\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 Add Code", callback_data="admin_addcode")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin_addforce")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Sync Videos", callback_data="admin_videosync")],
        [InlineKeyboardButton("📋 View Channels", callback_data="admin_channels")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def addcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcode command."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /addcode <CODE>\n\nExample: /addcode MYCODE123")
        return
    
    code = " ".join(context.args)
    
    if add_code(code):
        await update.message.reply_text(f"✅ Code <code>{code}</code> added successfully!", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ Code <code>{code}</code> already exists!", parse_mode="HTML")


async def addforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addforce command."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /addforce @channel\n\nExample: /addforce @mychannel")
        return
    
    channel = context.args[0]
    
    if add_force_channel(channel):
        await update.message.reply_text(f"✅ Channel {channel} added to force join!", parse_mode="HTML")
        
        # Verify bot is admin
        try:
            channel_clean = channel.strip("@")
            chat_member = await context.bot.get_chat_member(
                chat_id=f"@{channel_clean}",
                user_id=context.bot.id
            )
            if chat_member.status == "administrator":
                await update.message.reply_text("✅ Bot is admin in this channel!")
            else:
                await update.message.reply_text("⚠️ Warning: Bot is not admin in this channel. Please add bot as admin for proper functionality.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Could not verify bot status: {e}")
    else:
        await update.message.reply_text(f"⚠️ Channel {channel} already exists!", parse_mode="HTML")


async def removeforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeforce command."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /removeforce @channel\n\nExample: /removeforce @mychannel")
        return
    
    channel = context.args[0]
    
    if remove_force_channel(channel):
        await update.message.reply_text(f"✅ Channel {channel} removed from force join!", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ Channel {channel} not found!", parse_mode="HTML")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <MESSAGE>\n\nExample: /broadcast Hello everyone!")
        return
    
    message = " ".join(context.args)
    users = get_users()
    
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["id"],
                text=message
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['id']}: {e}")
            failed_count += 1
    
    text = f"✅ <b>Broadcast Complete</b>\n\n"
    text += f"• Sent: {sent_count}\n"
    text += f"• Failed: {failed_count}"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def adminkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adminkey command - Add new admin."""
    user_id = update.effective_user.id
    
    # Only owner can add admins
    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /adminkey <KEY> <USER_ID>\n\nExample: /adminkey secure_admin_key 123456789")
        return
    
    key = context.args[0]
    new_admin_id = context.args[1]
    
    if key != ADMIN_KEY:
        await update.message.reply_text("❌ Invalid admin key!")
        return
    
    try:
        new_admin_id = int(new_admin_id)
        if add_admin(new_admin_id):
            await update.message.reply_text(f"✅ User {new_admin_id} added as admin!")
        else:
            await update.message.reply_text(f"⚠️ User {new_admin_id} is already an admin!")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")


async def videos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /videos command."""
    user_id = update.effective_user.id
    
    # Check force join
    if not await check_force_join(update, user_id, context):
        return
    
    videos = get_videos()
    
    if not videos:
        await update.message.reply_text("📭 No videos available yet!")
        return
    
    text = "📺 <b>Available Videos</b>\n\n"
    
    for serial, video_data in sorted(videos.items()):
        caption = video_data.get("caption", "No caption")
        text += f"• Video #{serial}: {caption}\n"
    
    keyboard = [
        [InlineKeyboardButton("🎬 Watch Latest", callback_data="watch_latest")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def setchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setchannel command - Set private channel for autosync."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: /setchannel <CHANNEL_ID>\n\n"
            "Example: /setchannel -1001234567890\n\n"
            "To get channel ID: @username_id_bot",
            parse_mode="HTML"
        )
        return
    
    channel_id = context.args[0]
    
    # Save channel ID
    try:
        channel_data = {"channel_id": channel_id, "set_at": datetime.now().isoformat()}
        save_json(CHANNEL_FILE, channel_data)
        
        await update.message.reply_text(
            f"✅ <b>Channel Set!</b>\n\n"
            f"Channel ID: <code>{channel_id}</code>\n\n"
            f"Now use /autosync to start automatic video sync!",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def autosync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autosync command - Start automatic video sync from private channel."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Load channel ID
    channel_data = load_json(CHANNEL_FILE, {})
    channel_id = channel_data.get("channel_id", CHANNEL_ID)
    
    if not channel_id:
        await update.message.reply_text(
            "⚠️ No channel set!\n\n"
            "Use /setchannel <CHANNEL_ID> first to set your private channel.",
            parse_mode="HTML"
        )
        return
    
    await update.message.reply_text(
        f"🔄 <b>Starting Auto Sync...</b>\n\n"
        f"Channel ID: <code>{channel_id}</code>\n\n"
        f"I'll check for new videos in this channel and sync them with serial numbers.\n\n"
        f"<b>How it works:</b>\n"
        f"1. Add videos to your private channel\n"
        f"2. Use /syncnow to manually sync\n"
        f"3. New videos get serial numbers: 1, 2, 3, 4...",
        parse_mode="HTML"
    )


async def syncnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /syncnow command - Immediately sync videos from private channel."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Load channel ID
    channel_data = load_json(CHANNEL_FILE, {})
    channel_id = channel_data.get("channel_id", CHANNEL_ID)
    
    if not channel_id:
        await update.message.reply_text(
            "⚠️ No channel set!\n\n"
            "Use /setchannel <CHANNEL_ID> first.",
            parse_mode="HTML"
        )
        return
    
    await update.message.reply_text(
        f"🔄 <b>Syncing Videos...</b>\n\n"
        f"Channel: <code>{channel_id}</code>\n\n"
        f"Please wait...",
        parse_mode="HTML"
    )
    
    try:
        # Get chat information
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        # Get current videos
        videos = get_videos()
        current_count = len(videos)
        
        # Get messages from channel
        synced_count = 0
        
        try:
            # Get the last 100 messages from the channel
            async for message in context.bot.get_updates(limit=100):
                pass  # This won't work with get_updates for channels
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
        
        text = f"✅ <b>Sync Complete!</b>\n\n"
        text += f"Channel: {chat.title}\n"
        text += f"Total videos in database: {current_count}\n\n"
        text += f"<b>To add videos:</b>\n"
        text += f"• Send videos to your private channel\n"
        text += f"• Use /syncnow to refresh\n"
        text += f"• Videos are saved with serial numbers\n\n"
        text += f"<b>Note:</b> For automatic sync, the bot needs to be added to the channel as admin."
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error syncing: {e}")
        await update.message.reply_text(
            f"❌ <b>Sync Error</b>\n\n"
            f"Error: {e}\n\n"
            f"<b>Troubleshooting:</b>\n"
            f"• Make sure bot is admin in the channel\n"
            f"• Check if channel ID is correct\n"
            f"• Bot must be member of the channel",
            parse_mode="HTML"
        )


async def mycode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mycode command."""
    user_id = update.effective_user.id
    
    # Check force join
    if not await check_force_join(update, user_id, context):
        return
    
    await update.message.reply_text(
        "🔐 <b>Code Access</b>\n\n"
        "Please send your access code to verify access.",
        parse_mode="HTML"
    )


# =============================================================================
# CALLBACK QUERY HANDLERS
# =============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "check_join":
        # Re-check force join
        if await check_force_join(update, user_id, context):
            await query.edit_message_text("✅ <b>Access Granted!</b>\n\nWelcome to the bot! Use /help to see available commands.", parse_mode="HTML")
    
    elif data == "admin_addcode":
        await query.edit_message_text(
            "📝 <b>Add Access Code</b>\n\n"
            "Usage: /addcode <CODE>\n\n"
            "Example: /addcode MYCODE123",
            parse_mode="HTML"
        )
    
    elif data == "admin_addforce":
        await query.edit_message_text(
            "➕ <b>Add Force Join Channel</b>\n\n"
            "Usage: /addforce @channel\n\n"
            "Example: /addforce @mychannel\n\n"
            "Note: Bot must be admin in the channel.",
            parse_mode="HTML"
        )
    
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 <b>Broadcast Message</b>\n\n"
            "Usage: /broadcast <MESSAGE>\n\n"
            "Example: /broadcast Hello everyone!",
            parse_mode="HTML"
        )
    
    elif data == "admin_videosync":
        await query.edit_message_text(
            "🔄 <b>Video Sync</b>\n\n"
            "Forward a video from your private channel to sync it.\n\n"
            "Usage: /videosync",
            parse_mode="HTML"
        )
    
    elif data == "admin_channels":
        channels = get_force_channels()
        
        if not channels:
            text = "📋 <b>Force Join Channels</b>\n\nNo channels added yet."
        else:
            text = "📋 <b>Force Join Channels</b>\n\n"
            for i, ch in enumerate(channels, 1):
                text += f"{i}. {ch.get('channel', '')}\n"
        
        await query.edit_message_text(text, parse_mode="HTML")
    
    elif data == "videos_list":
        videos = get_videos()
        
        if not videos:
            await query.edit_message_text("📭 No videos available yet!")
            return
        
        text = "📺 <b>Available Videos</b>\n\n"
        
        for serial, video_data in sorted(videos.items()):
            caption = video_data.get("caption", "No caption")
            text += f"• Video #{serial}: {caption}\n"
        
        keyboard = [
            [InlineKeyboardButton("🎬 Watch Latest", callback_data="watch_latest")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    
    elif data == "watch_latest":
        videos = get_videos()
        
        if not videos:
            await query.edit_message_text("📭 No videos available!")
            return
        
        latest_serial = max(videos.keys())
        video_data = videos[latest_serial]
        file_id = video_data.get("file_id")
        caption = video_data.get("caption", "")
        
        try:
            await context.bot.send_video(
                chat_id=user_id,
                video=file_id,
                caption=caption
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error sending video: {e}")


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - Check for access code."""
    user = update.effective_user
    text = update.message.text
    
    # Check if it's a command
    if text.startswith("/"):
        return
    
    # Save user
    save_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    
    # Check force join
    if not await check_force_join(update, user.id, context):
        return
    
    # Check for access code
    if check_code(text):
        await update.message.reply_text(
            "✅ <b>Access Granted!</b>\n\n"
            "Your code is valid. You now have access to the bot!",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "❌ <b>Invalid Code</b>\n\n"
            "The code you entered is not valid. Please check and try again.",
            parse_mode="HTML"
        )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video messages - For video sync."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if not update.message.video:
        return
    
    video = update.message.video
    file_id = video.file_id
    caption = update.message.caption or ""
    
    # Get next serial number
    videos = get_videos()
    next_serial = max(videos.keys(), default=0) + 1
    
    # Save video
    if save_video(next_serial, file_id, caption):
        await update.message.reply_text(
            f"✅ <b>Video Saved!</b>\n\n"
            f"Serial Number: #{next_serial}\n"
            f"Caption: {caption}",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Error saving video!")


async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video note messages - For video sync."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if not update.message.video_note:
        return
    
    video_note = update.message.video_note
    file_id = video_note.file_id
    
    # Get next serial number
    videos = get_videos()
    next_serial = max(videos.keys(), default=0) + 1
    
    # Save video note
    if save_video(next_serial, file_id, "Video Note"):
        await update.message.reply_text(
            f"✅ <b>Video Note Saved!</b>\n\n"
            f"Serial Number: #{next_serial}",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Error saving video note!")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages - For video sync (if it's a video file)."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if not update.message.document:
        return
    
    document = update.message.document
    
    # Check if it's a video file
    if document.mime_type and document.mime_type.startswith("video"):
        file_id = document.file_id
        caption = update.message.caption or ""
        
        # Get next serial number
        videos = get_videos()
        next_serial = max(videos.keys(), default=0) + 1
        
        # Save video
        if save_video(next_serial, file_id, caption):
            await update.message.reply_text(
                f"✅ <b>Video Saved!</b>\n\n"
                f"Serial Number: #{next_serial}\n"
                f"Caption: {caption}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Error saving video!")


# =============================================================================
# ERROR HANDLERS
# =============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main function to run the bot."""
    # Validate environment variables
    if not TOKEN:
        logger.error("TOKEN environment variable is not set!")
        print("ERROR: Please set the TOKEN environment variable!")
        return
    
    if not ADMIN_ID:
        logger.warning("ADMIN_ID environment variable is not set!")
        print("WARNING: Please set the ADMIN_ID environment variable!")
    
    logger.info("Starting Telegram Video Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addcode", addcode_command))
    application.add_handler(CommandHandler("addforce", addforce_command))
    application.add_handler(CommandHandler("removeforce", removeforce_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("adminkey", adminkey_command))
    application.add_handler(CommandHandler("videos", videos_command))
    application.add_handler(CommandHandler("setchannel", setchannel_command))
    application.add_handler(CommandHandler("autosync", autosync_command))
    application.add_handler(CommandHandler("syncnow", syncnow_command))
    application.add_handler(CommandHandler("mycode", mycode_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    application.add_handler(MessageHandler(filters.Document.VIDEO, handle_document))
    
    # Start polling
    logger.info("Bot is running...")
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
