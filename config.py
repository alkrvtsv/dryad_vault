import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DB_NAME = os.getenv("DB_NAME", "asmr_orders.db")
ARCHIVE_CHANNEL_ID_RAW = os.getenv("ARCHIVE_CHANNEL_ID")

if not BOT_TOKEN or not ADMIN_ID_RAW:
    raise ValueError("BOT_TOKEN and ADMIN_ID must be set in .env")

ADMIN_ID = int(ADMIN_ID_RAW)
ARCHIVE_CHANNEL_ID = int(ARCHIVE_CHANNEL_ID_RAW) if ARCHIVE_CHANNEL_ID_RAW else None

PAGE_SIZE = 5

# Настройки режима тестирования
TEST_MODE = False
TEST_BACKUP_PATH = DB_NAME + ".test_backup"
TEST_ALLOWED_USER_ID = 7896647014