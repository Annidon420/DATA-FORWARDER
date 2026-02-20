# Telegram Video Bot - Production Ready

A professional Telegram access bot with force join, code verification, admin system, broadcast, video autosync, and Railway deployment support.

## Features

- **Force Join System**: Users must join required channels before accessing bot features
- **Code Access System**: Admin can add access codes for users
- **Admin System**: Multiple admin levels with secure key authentication
- **Broadcast System**: Send messages to all users
- **Video Autosync**: Auto-sync videos from private channels with serial numbers
- **Railway Deployment**: Ready for production deployment

## Project Structure

```
telegram-video-bot/
├── bot.py              # Main bot file
├── requirements.txt    # Python dependencies
├── Procfile           # Railway deployment
├── runtime.txt        # Python version
├── data/
│   ├── users.json      # User database
│   ├── codes.json      # Access codes
│   ├── force.json      # Force join channels
│   └── admins.json     # Admin list
└── README.md           # This file
```

## Installation

1. Clone the repository
2. Install dependencies:
   
```
   pip install -r requirements.txt
   
```

## Configuration

Set environment variables:
- `TOKEN`: Your Telegram Bot API token
- `ADMIN_ID`: Your Telegram user ID (owner)
- `ADMIN_KEY`: Secret key to add new admins

## Bot Commands

### User Commands
- `/start` - Start the bot and get access

### Admin Commands
- `/admin` - Open admin panel
- `/addcode <CODE>` - Add access code
- `/addforce @channel` - Add force join channel
- `/removeforce @channel` - Remove force join channel
- `/broadcast <MESSAGE>` - Broadcast message to all users
- `/adminkey <USER_ID>` - Add new admin (owner only)
- `/videosync` - Sync videos from private channel

## Force Join Setup

1. Add your bot to the channel as admin
2. Use `/addforce @channel_username` to add the channel
3. Users must join the channel before accessing bot features

## Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables:
   - `TOKEN`: Your Bot API token
   - `ADMIN_ID`: Your user ID
   - `ADMIN_KEY`: Your secret admin key
3. Deploy!

## License

MIT
