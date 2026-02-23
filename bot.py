import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

# =========================
# ENVIRONMENT VARIABLES
# =========================

TOKEN = os.getenv("TOKEN")
OWNER_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("TOKEN environment variable not set")

if not OWNER_ID:
    raise ValueError("ADMIN_ID environment variable not set")

OWNER_ID = int(OWNER_ID)

# =========================
# LOGGING CONFIG
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# =========================
# DATA DIRECTORY SETUP
# =========================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
CODES_FILE = DATA_DIR / "codes.json"
FORCE_FILE = DATA_DIR / "force.json"
ADMINS_FILE = DATA_DIR / "admins.json"
VIDEOS_FILE = DATA_DIR / "videos.json"

# =========================
# SAFE JSON HANDLER
# =========================

def safe_load_json(file_path: Path, default: Any):
    try:
        if not file_path.exists():
            file_path.write_text(json.dumps(default, indent=4))
            return default

        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        logger.error(f"Corrupted JSON detected: {file_path.name}. Resetting.")
        file_path.write_text(json.dumps(default, indent=4))
        return default

    except Exception as e:
        logger.error(f"Error loading {file_path.name}: {e}")
        return default


def safe_save_json(file_path: Path, data: Any):
    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving {file_path.name}: {e}")

# =========================
# LOAD DATA
# =========================

users: Dict[str, Dict] = safe_load_json(USERS_FILE, {})
codes: Dict[str, bool] = safe_load_json(CODES_FILE, {})
force_channels = safe_load_json(FORCE_FILE, [])
admins = safe_load_json(ADMINS_FILE, [])
videos: Dict[str, str] = safe_load_json(VIDEOS_FILE, {})

# Ensure OWNER always admin
if OWNER_ID not in admins:
    admins.append(OWNER_ID)
    safe_save_json(ADMINS_FILE, admins)

# =========================
# SERIAL NUMBER HELPER
# =========================

def get_next_serial() -> str:
    if not videos:
        return "1"

    try:
        max_serial = max(int(k) for k in videos.keys())
        return str(max_serial + 1)
    except Exception:
        return "1"

# =========================
# BOT STARTUP
# =========================

def main():
    application = Application.builder().token(TOKEN).build()

    logger.info("Bot foundation loaded successfully.")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info(f"Total Admins: {len(admins)}")
    logger.info(f"Loaded Videos: {len(videos)}")

    application.run_polling()

if __name__ == "__main__":
    main()