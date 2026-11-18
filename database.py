import secrets
import aiosqlite
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                is_used INTEGER DEFAULT 0,
                used_by INTEGER,
                title TEXT,
                media_type TEXT DEFAULT 'video',
                archive_message_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN title TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN media_type TEXT DEFAULT 'video'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN archive_message_id TEXT")
        except Exception:
            pass
        await db.commit()

async def save_user(user_id: int, username: str|None) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            await db.commit()
            return "NEW"
        elif row[0] != username:
            await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            await db.commit()
            return "UPDATED"
        return "UNCHANGED"

async def create_order(file_id: str, title: str, media_type: str="video", archive_message_id: str|None=None) -> str:
    code = secrets.token_urlsafe(8)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO orders (code, file_id, title, media_type, archive_message_id) VALUES (?, ?, ?, ?, ?)",
            (code, file_id, title, media_type, archive_message_id)
        )
        await db.commit()
    return code

async def create_direct_order(file_id: str, user_id: int, title: str, media_type: str="video", archive_message_id: str|None=None) -> tuple[str, bool]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code FROM orders WHERE used_by = ? AND file_id = ? LIMIT 1",
            (user_id, file_id)
        )
        existing = await cursor.fetchone()
        if existing:
            return existing[0], False
        code = secrets.token_urlsafe(8)
        await db.execute(
            "INSERT INTO orders (code, file_id, is_used, used_by, title, media_type, archive_message_id) VALUES (?, ?, 1, ?, ?, ?, ?)",
            (code, file_id, user_id, title, media_type, archive_message_id)
        )
        await db.commit()
        return code, True

async def redeem_code(code: str, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id, is_used, used_by, title, media_type FROM orders WHERE code = ?", (code,))
        row = await cursor.fetchone()
        if not row:
            return None, None, None, "NOT_FOUND"
        file_id, is_used, used_by, title, media_type = row
        media_type = media_type or "video"
        if is_used:
            if used_by == user_id:
                return file_id, title, media_type, "ALREADY_OWNED"
            return None, None, None, "USED_BY_OTHER"
        existing_cursor = await db.execute(
            "SELECT code, title FROM orders WHERE used_by = ? AND file_id = ? LIMIT 1",
            (user_id, file_id)
        )
        existing_order = await existing_cursor.fetchone()
        if existing_order:
            await db.execute("DELETE FROM orders WHERE code = ?", (code,))
            await db.commit()
            resolved_title = title or existing_order[1]
            return file_id, resolved_title, media_type, "DUPLICATE_REMOVED"
        await db.execute("UPDATE orders SET is_used = 1, used_by = ? WHERE code = ?", (user_id, code))
        await db.commit()
        return file_id, title, media_type, "SUCCESS"

async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, file_id, title, COALESCE(media_type, 'video') FROM orders WHERE used_by = ? ORDER BY rowid DESC",
            (user_id,)
        )
        return await cursor.fetchall()

async def get_customers_summary():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT o.used_by, u.username, COUNT(o.code)
            FROM orders o
            LEFT JOIN users u ON o.used_by = u.user_id
            WHERE o.used_by IS NOT NULL
            GROUP BY o.used_by
            ORDER BY o.rowid DESC
        """)
        return await cursor.fetchall()

async def get_customer_orders(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, file_id, title, COALESCE(media_type, 'video') FROM orders WHERE used_by = ? ORDER BY rowid DESC",
            (user_id,)
        )
        return await cursor.fetchall()

async def get_order_by_code(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, file_id, used_by, title, COALESCE(media_type, 'video'), archive_message_id FROM orders WHERE code = ?",
            (code,)
        )
        return await cursor.fetchone()

async def update_order_title(code: str, title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE orders SET title = ? WHERE code = ?", (title, code))
        await db.commit()

async def get_user_info(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0]:
            return row[0]
        return None

async def delete_order_by_code(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM orders WHERE code = ?", (code,))
        await db.commit()

async def unlink_order(code: str) -> str:
    """Отвязывает материал. Если он ещё у кого-то есть — удаляет запись,
    иначе помечает как 'без привязки'. Возвращает 'UNLINKED' или 'DELETED'."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id FROM orders WHERE code = ?", (code,))
        row = await cursor.fetchone()
        if not row:
            return "NOT_FOUND"
        file_id = row[0]
        cursor = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE file_id = ? AND used_by IS NOT NULL AND code != ?",
            (file_id, code)
        )
        others_count = (await cursor.fetchone())[0]
        if others_count > 0:
            await db.execute("DELETE FROM orders WHERE code = ?", (code,))
            await db.commit()
            return "DELETED"
        else:
            await db.execute("UPDATE orders SET is_used = 0, used_by = NULL WHERE code = ?", (code,))
            await db.commit()
            return "UNLINKED"

async def get_unlinked_orders():
    """Материалы без привязки. Показываем только те, у которых НЕТ ни одной
    активной привязки к пользователю по тому же file_id."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT o.code, o.file_id, o.title, COALESCE(o.media_type, 'video'), o.archive_message_id
            FROM orders o
            WHERE o.used_by IS NULL AND o.is_used = 0
            AND NOT EXISTS (
                SELECT 1 FROM orders o2
                WHERE o2.file_id = o.file_id AND o2.used_by IS NOT NULL
            )
            ORDER BY o.rowid DESC
        """)
        return await cursor.fetchall()

async def get_all_unique_media():
    """Все уникальные медиа, сгруппированные по file_id."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT MIN(code) as code, file_id, MIN(title) as title, COALESCE(MIN(media_type), 'video') as media_type, COUNT(*) as order_count
            FROM orders
            GROUP BY file_id
            ORDER BY MAX(rowid) DESC
        """)
        return await cursor.fetchall()

async def get_material_owners(file_id: str):
    """Возвращает список пользователей, у которых есть данный материал."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT o.used_by, u.username
            FROM orders o
            LEFT JOIN users u ON o.used_by = u.user_id
            WHERE o.file_id = ? AND o.used_by IS NOT NULL
            ORDER BY o.rowid DESC
        """, (file_id,))
        return await cursor.fetchall()

async def delete_all_orders_by_file_id(file_id: str) -> list[str]:
    """Удаляет все записи с данным file_id и возвращает список archive_message_id."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT archive_message_id FROM orders WHERE file_id = ?", (file_id,))
        rows = await cursor.fetchall()
        archive_ids = []
        for row in rows:
            if row[0]:
                archive_ids.append(row[0])
        await db.execute("DELETE FROM orders WHERE file_id = ?", (file_id,))
        await db.commit()
    return archive_ids