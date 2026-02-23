"""
Telegram Access Control Bot - Production Ready
Version: 2.0.0
Python Telegram Bot v20+
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Python Telegram Bot imports
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Environment Variables
TOKEN = os.environ.get('TOKEN', '')
ADMIN_ID = os.environ.get('ADMIN_ID', '')

# File Paths
DATA_DIR = Path('data')
USERS_FILE = DATA_DIR / 'users.json'
CODES_FILE = DATA_DIR / 'codes.json'
FORCE_FILE = DATA_DIR / 'force.json'
ADMINS_FILE = DATA_DIR / 'admins.json'
VIDEOS_FILE = DATA_DIR / 'videos.json'

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# JSON STORAGE SYSTEM
# ============================================================================

class JSONStorage:
    """Safe JSON storage with corruption recovery and auto-creation"""
    
    @staticmethod
    def load(file_path: Path) -> Dict:
        """Load JSON file with error handling"""
        try:
            if not file_path.exists():
                JSONStorage.save(file_path, {})
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON corruption in {file_path}: {e}")
            # Backup corrupted file
            backup_path = file_path.with_suffix('.json.bak')
            if file_path.exists():
                file_path.rename(backup_path)
            JSONStorage.save(file_path, {})
            return {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    @staticmethod
    def save(file_path: Path, data: Dict) -> bool:
        """Save data to JSON file"""
        try:
            DATA_DIR.mkdir(exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
            return False

# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================

class Database:
    """Database manager for all JSON files"""
    
    def __init__(self):
        self.users = JSONStorage.load(USERS_FILE)
        self.codes = JSONStorage.load(CODES_FILE)
        self.force_channels = JSONStorage.load(FORCE_FILE)
        self.admins = JSONStorage.load(ADMINS_FILE)
        self.videos = JSONStorage.load(VIDEOS_FILE)
    
    def save_all(self):
        """Save all data to files"""
        JSONStorage.save(USERS_FILE, self.users)
        JSONStorage.save(CODES_FILE, self.codes)
        JSONStorage.save(FORCE_FILE, self.force_channels)
        JSONStorage.save(ADMINS_FILE, self.admins)
        JSONStorage.save(VIDEOS_FILE, self.videos)
    
    # User Methods
    def add_user(self, user_id: int, username: str = ''):
        """Add or update user"""
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                'id': user_id,
                'username': username,
                'joined_at': datetime.now().isoformat()
            }
            JSONStorage.save(USERS_FILE, self.users)
            return True
        else:
            # Update username
            self.users[str(user_id)]['username'] = username
            JSONStorage.save(USERS_FILE, self.users)
        return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        return list(self.users.values())
    
    # Code Methods
    def add_code(self, code: str, video_number: Optional[int] = None):
        """Add access code"""
        self.codes[code.upper()] = {
            'code': code.upper(),
            'video_number': video_number,
            'created_at': datetime.now().isoformat()
        }
        JSONStorage.save(CODES_FILE, self.codes)
    
    def get_code(self, code: str) -> Optional[Dict]:
        """Get code data"""
        return self.codes.get(code.upper())
    
    def get_all_codes(self) -> List[Dict]:
        """Get all codes"""
        return list(self.codes.values())
    
    # Force Channel Methods
    def add_force_channel(self, channel_id: str, channel_name: str = ''):
        """Add force join channel"""
        if channel_id not in self.force_channels:
            self.force_channels[channel_id] = {
                'id': channel_id,
                'name': channel_name,
                'added_at': datetime.now().isoformat()
            }
            JSONStorage.save(FORCE_FILE, self.force_channels)
            return True
        return False
    
    def remove_force_channel(self, channel_id: str):
        """Remove force join channel"""
        if channel_id in self.force_channels:
            del self.force_channels[channel_id]
            JSONStorage.save(FORCE_FILE, self.force_channels)
            return True
        return False
    
    def get_all_force_channels(self) -> List[Dict]:
        """Get all force channels"""
        return list(self.force_channels.values())
    
    # Admin Methods
    def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return str(user_id) == str(ADMIN_ID)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin or owner"""
        return self.is_owner(user_id) or str(user_id) in self.admins
    
    def add_admin(self, user_id: int):
        """Add admin"""
        self.admins[str(user_id)] = {
            'id': user_id,
            'added_at': datetime.now().isoformat()
        }
        JSONStorage.save(ADMINS_FILE, self.admins)
    
    def get_all_admins(self) -> List[Dict]:
        """Get all admins"""
        return list(self.admins.values())
    
    # Video Methods
    def add_video(self, serial: int, file_id: str, caption: str = ''):
        """Add video with serial number"""
        self.videos[str(serial)] = {
            'serial': serial,
            'file_id': file_id,
            'caption': caption,
            'added_at': datetime.now().isoformat()
        }
        JSONStorage.save(VIDEOS_FILE, self.videos)
    
    def get_video(self, serial: int) -> Optional[Dict]:
        """Get video by serial number"""
        return self.videos.get(str(serial))
    
    def get_all_videos(self) -> List[Dict]:
        """Get all videos"""
        return list(self.videos.values())

# Initialize Database
db = Database()

# ============================================================================
# KEYBOARDS
# ============================================================================

def get_force_join_keyboard(force_channels: List[Dict]) -> InlineKeyboardMarkup:
    """Create force join keyboard"""
    keyboard = []
    for channel in force_channels:
        channel_name = channel.get('name', channel['id'])
        keyboard.append([
            InlineKeyboardButton(
                f"🔗 Join {channel_name}", 
                url=f"https://t.me/{channel_name.replace('@', '')}"
            )
        ])
    keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_join")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Add Code", callback_data="admin_addcode")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin_addforce")],
        [InlineKeyboardButton("➖ Remove Channel", callback_data="admin_removeforce")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔧 Manage Admins", callback_data="admin_manage")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================================
# FORCE JOIN SYSTEM
# ============================================================================

async def check_user_membership(user_id: int, channel_id: str, bot) -> bool:
    """Check if user joined channel using get_chat_member"""
    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership for {channel_id}: {e}")
        return False

async def verify_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verify user has joined all required channels"""
    user_id = update.effective_user.id
    force_channels = db.get_all_force_channels()
    
    if not force_channels:
        return True
    
    not_joined = []
    for channel in force_channels:
        channel_id = channel['id']
        is_member = await check_user_membership(user_id, channel_id, context.bot)
        if not is_member:
            not_joined.append(channel)
    
    if not_joined:
        keyboard = get_force_join_keyboard(not_joined)
        text = "🔒 <b>Access Restricted</b>\n\n"
        text += "You must join the following channels to use this bot:\n\n"
        
        for channel in not_joined:
            text += f"• {channel.get('name', channel['id'])}\n"
        
        text += "\n⏳ After joining, click '✅ I Joined'"
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='HTML')
        return False
    
    return True

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    db.add_user(user.id, user.username or '')
    
    # Check force join
    if not await verify_force_join(update, context):
        return
    
    text = "👋 <b>Welcome!</b>\n\n"
    text += "This is your Access Control Bot.\n\n"
    text += "Available features:\n"
    text += "• Access codes for video content\n"
    text += "• Automatic video sync from channel\n\n"
    text += "Send me an access code to get started!"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    text = "📖 <b>Help</b>\n\n"
    text += "Send an access code to get the content.\n\n"
    text += "<b>Admin Commands:</b>\n"
    text += "/admin - Admin panel\n"
    text += "/addcode CODE - Add access code\n"
    text += "/addforce @channel - Add force join channel\n"
    text += "/removeforce @channel - Remove channel\n"
    text += "/broadcast MESSAGE - Broadcast to all users"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    text = "⚙️ <b>Admin Panel</b>\n\n"
    text += f"👥 Users: {len(db.get_all_users())}\n"
    text += f"🔑 Codes: {len(db.get_all_codes())}\n"
    text += f"📺 Videos: {len(db.get_all_videos())}\n"
    text += f"🔗 Force Channels: {len(db.get_all_force_channels())}"
    
    await update.message.reply_text(text, reply_markup=get_admin_keyboard(), parse_mode='HTML')

# ============================================================================
# ACCESS CODE SYSTEM
# ============================================================================

async def addcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add access code - /addcode CODE [video_number]"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /addcode CODE [video_number]\nExample: /addcode VIDEO123 5")
        return
    
    code = args[0].upper()
    video_number = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    db.add_code(code, video_number)
    
    text = f"✅ Code <code>{code}</code> added successfully!"
    if video_number:
        text += f"\n📺 Linked to video #{video_number}"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ============================================================================
# FORCE JOIN SYSTEM COMMANDS
# ============================================================================

async def addforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add force join channel - /addforce @channel"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /addforce @channelusername")
        return
    
    channel_username = args[0].replace('@', '')
    channel_id = f"@{channel_username}"
    
    # Try to get channel info
    try:
        chat = await context.bot.get_chat(channel_id)
        channel_name = chat.title or channel_username
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        channel_name = channel_username
    
    if db.add_force_channel(channel_id, channel_name):
        await update.message.reply_text(f"✅ Force channel @{channel_username} added!\n\n⚠️ Make sure to add the bot as admin in the channel for membership check to work.")
    else:
        await update.message.reply_text(f"ℹ️ Channel @{channel_username} already exists!")

async def removeforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove force join channel - /removeforce @channel"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /removeforce @channelusername")
        return
    
    channel_username = args[0].replace('@', '')
    channel_id = f"@{channel_username}"
    
    if db.remove_force_channel(channel_id):
        await update.message.reply_text(f"✅ Channel @{channel_username} removed!")
    else:
        await update.message.reply_text(f"❌ Channel @{channel_username} not found!")

# ============================================================================
# ADMIN MANAGEMENT
# ============================================================================

async def adminkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add admin - /adminkey USER_ID (Owner only)"""
    user_id = update.effective_user.id
    
    if not db.is_owner(user_id):
        await update.message.reply_text("❌ Only owner can add admins!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /adminkey USER_ID")
        return
    
    try:
        new_admin_id = int(args[0])
        db.add_admin(new_admin_id)
        await update.message.reply_text(f"✅ Admin added: {new_admin_id}")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

# ============================================================================
# BROADCAST SYSTEM
# ============================================================================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message - /broadcast MESSAGE"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    # Get message text (everything after /broadcast)
    message_text = update.message.text.replace('/broadcast', '').strip()
    
    if not message_text:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return
    
    users = db.get_all_users()
    success = 0
    failed = 0
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['id'],
                text=message_text,
                parse_mode='HTML'
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['id']}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Broadcast complete!\n\n"
        f"📊 Success: {success}\n"
        f"❌ Failed: {failed}"
    )

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    # Check force join first
    if not await verify_force_join(update, context):
        return
    
    text = update.message.text.strip().upper()
    
    # Check if it's an access code
    code_data = db.get_code(text)
    
    if code_data:
        video_number = code_data.get('video_number')
        
        if video_number:
            # Send linked video
            video_data = db.get_video(video_number)
            if video_data:
                try:
                    await update.message.reply_video(
                        video=video_data['file_id'],
                        caption=f"📺 Video #{video_number}"
                    )
                    await update.message.reply_text("✅ Access Granted!")
                except Exception as e:
                    logger.error(f"Error sending video: {e}")
                    await update.message.reply_text("❌ Error sending video. Please contact admin.")
            else:
                await update.message.reply_text(
                    f"✅ Access Granted!\n\n⚠️ Video #{video_number} not found!",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text("✅ Access Granted!")
    else:
        # Not a code - show help
        await update.message.reply_text(
            "❌ Invalid code or unknown command.\n\n"
            "Send a valid access code to get content."
        )

# ============================================================================
# CALLBACK QUERY HANDLERS
# ============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "check_join":
        # Recheck membership
        if await verify_force_join(update, context):
            await query.edit_message_text("✅ Access Granted! Welcome!")
    
    elif data == "admin_stats":
        if not db.is_admin(user_id):
            await query.answer("❌ Unauthorized!", show_alert=True)
            return
        
        text = "📊 <b>Statistics</b>\n\n"
        text += f"👥 Total Users: {len(db.get_all_users())}\n"
        text += f"🔑 Total Codes: {len(db.get_all_codes())}\n"
        text += f"📺 Total Videos: {len(db.get_all_videos())}\n"
        text += f"🔗 Force Channels: {len(db.get_all_force_channels())}"
        
        await query.edit_message_text(text, reply_markup=get_admin_keyboard(), parse_mode='HTML')
    
    elif data == "admin_close":
        await query.delete_message()
    
    elif data in ["admin_addcode", "admin_addforce", "admin_removeforce", "admin_broadcast", "admin_manage"]:
        if not db.is_admin(user_id):
            await query.answer("❌ Unauthorized!", show_alert=True)
            return
        
        if data == "admin_addcode":
            await query.edit_message_text(
                "➕ <b>Add Access Code</b>\n\n"
                "Use command:\n<code>/addcode CODE [video_number]</code>\n\n"
                "Example:\n<code>/addcode VIDEO123 5</code>",
                reply_markup=get_admin_keyboard(),
                parse_mode='HTML'
            )
        elif data == "admin_addforce":
            await query.edit_message_text(
                "➕ <b>Add Force Channel</b>\n\n"
                "Use command:\n<code>/addforce @username</code>",
                reply_markup=get_admin_keyboard(),
                parse_mode='HTML'
            )
        elif data == "admin_removeforce":
            await query.edit_message_text(
                "➖ <b>Remove Force Channel</b>\n\n"
                "Use command:\n<code>/removeforce @username</code>",
                reply_markup=get_admin_keyboard(),
                parse_mode='HTML'
            )
        elif data == "admin_broadcast":
            await query.edit_message_text(
                "📢 <b>Broadcast</b>\n\n"
                "Use command:\n<code>/broadcast Your message</code>",
                reply_markup=get_admin_keyboard(),
                parse_mode='HTML'
            )
        elif data == "admin_manage":
            text = "🔧 <b>Admin Management</b>\n\n"
            text += f"👤 Owner ID: <code>{ADMIN_ID}</code>\n\n"
            text += "<b>Admins:</b>\n"
            for admin in db.get_all_admins():
                text += f"• <code>{admin['id']}</code>\n"
            text += "\nUse <code>/adminkey USER_ID</code> to add admins (Owner only)"
            
            await query.edit_message_text(text, reply_markup=get_admin_keyboard(), parse_mode='HTML')

# ============================================================================
# AUTO VIDEO SYNC SYSTEM
# ============================================================================

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle posts in the private channel"""
    if not update.channel_post:
        return
    
    message = update.channel_post
    
    # Check if it's a video
    if not message.video:
        return
    
    # Check caption for number
    caption = message.caption.strip() if message.caption else ""
    
    if caption.isdigit():
        serial = int(caption)
        file_id = message.video.file_id
        
        db.add_video(serial, file_id, caption)
        
        logger.info(f"Video {serial} synced from channel")
        
        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"📺 New video synced!\n📊 Serial: #{serial}"
            )
        except:
            pass

# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to run the bot"""
    # Validate configuration
    if not TOKEN:
        logger.error("TOKEN not set! Set TOKEN environment variable.")
        sys.exit(1)
    
    if not ADMIN_ID:
        logger.error("ADMIN_ID not set! Set ADMIN_ID environment variable.")
        sys.exit(1)
    
    logger.info("Starting Telegram Access Bot...")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Force Channels: {len(db.get_all_force_channels())}")
    logger.info(f"Codes: {len(db.get_all_codes())}")
    logger.info(f"Videos: {len(db.get_all_videos())}")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addcode", addcode_command))
    application.add_handler(CommandHandler("addforce", addforce_command))
    application.add_handler(CommandHandler("removeforce", removeforce_command))
    application.add_handler(CommandHandler("adminkey", adminkey_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Message handler (must be after commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Channel post handler for video sync
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=['message', 'callback_query', 'channel_post'])

if __name__ == '__main__':
    main()
