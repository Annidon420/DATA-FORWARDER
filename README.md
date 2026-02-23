# Telegram Access Control Bot

A professional production-ready Telegram bot with force join, access codes, auto video sync, admin management, and broadcast system.

## Features

✅ **Force Join System** - Require users to join channels before access  
✅ **Access Code System** - Verify users with codes, auto-send linked videos  
✅ **Auto Video Sync** - Automatically sync videos from private channel  
✅ **Admin Management** - Owner + admin system with commands  
✅ **Broadcast System** - Send messages to all users  
✅ **JSON Storage** - Safe storage with corruption recovery  
✅ **Railway Ready** - Production deployment ready  

## Project Structure

```
telegram-access-bot/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── Procfile            # Railway deployment
├── runtime.txt         # Python version
├── Railway.toml        # Railway config
└── data/
    ├── users.json      # User storage
    ├── codes.json     # Access codes
    ├── force.json     # Force join channels
    ├── admins.json    # Admin list
    └── videos.json    # Video storage
```

## Commands

### User Commands
- `/start` - Start the bot & register
- `/help` - Get help information

### Admin Commands
- `/admin` - Open admin panel
- `/addcode CODE [video_number]` - Add access code
- `/addforce @channel` - Add force join channel
- `/removeforce @channel` - Remove channel
- `/broadcast MESSAGE` - Broadcast to all users
- `/adminkey USER_ID` - Add new admin (Owner only)

## Setup Instructions

### 1. Create Telegram Bot
1. Open Telegram → @BotFather
2. Send `/newbot`
3. Follow instructions, get token
4. Save token (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your User ID
1. Open Telegram → @userinfobot
2. Send `/start`
3. Note your ID (e.g., `123456789`)

### 3. Configure Force Join Channels (Optional)
1. Add bot to your channel as admin
2. Get channel username or ID
3. Use `/addforce @channelusername`

### 4. Auto Video Sync Setup
1. Add bot to your private channel as admin
2. Upload videos with caption = serial number (1, 2, 3...)
3. Bot automatically syncs them!

## Railway Deployment

### Quick Deploy
1. Push code to GitHub
2. Go to [Railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Add environment variables:

| Variable | Value |
|----------|-------|
| TOKEN | Your bot token |
| ADMIN_ID | Your user ID |

5. Deploy!

### Environment Variables
```
TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
```

## How to Use

### Adding Access Codes
```
/addcode MYCODE 5
```
This creates code "MYCODE" that sends video #5 when used

### Force Join Channels
```
/addforce @mychannel
```
Users must join @mychannel before using the bot

### Auto Video Sync
1. Add bot to your private channel as admin
2. Upload video with caption "1"
3. Bot syncs video with serial #1
4. Users can get it by sending code or video number

## Bot Behavior

### Force Join Flow
1. User sends `/start`
2. Bot checks if user joined all required channels
3. If not joined → shows inline buttons to join
4. After joining → click "I Joined" button
5. Access granted!

### Access Code Flow
1. Admin adds code: `/addcode VIP123 5`
2. User sends "VIP123" to bot
3. Bot verifies code is valid
4. If linked to video → sends video automatically
5. Shows "Access Granted!"

### Video Sync Flow
1. Admin uploads video to private channel
2. Caption: "1" (serial number)
3. Bot detects and saves: serial # → file_id
4. User sends "1" or code
5. Bot sends the video

## Tech Stack

- Python 3.11+
- python-telegram-bot v20+
- Railway (Deployment)

## Local Development

```
bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (Linux/Mac)
export TOKEN="your_bot_token"
export ADMIN_ID="your_user_id"

# Set environment variables (Windows CMD)
set TOKEN=your_bot_token
set ADMIN_ID=your_user_id

# Run the bot
python bot.py
