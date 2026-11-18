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

# Список сообщений в архивном канале, отправленных во время теста: [(chat_id, message_id), ...]
TEST_ARCHIVED_MESSAGES = []

# Список сообщений с материалами, отправленных пользователям во время теста: [(chat_id, message_id), ...]
TEST_SENT_MESSAGES = []

# Настройки бэкапов базы данных
BACKUP_RETENTION_COUNT = 10          # сколько последних бэкапов хранить в архиве
BACKUP_INTERVAL_SECONDS = 3600       # как часто проверять необходимость бэкапа (раз в час)
BACKUP_META_PATH = DB_NAME.rsplit(".", 1)[0] + "_backup_meta.json"  # файл учёта бэкапов