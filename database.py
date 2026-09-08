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
                title TEXT
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
        await db.commit()

async def save_user(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username
        """, (user_id, username))
        await db.commit()

async def create_order(file_id: str, title: str) -> str:
    code = secrets.token_urlsafe(8)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO orders (code, file_id, title) VALUES (?, ?, ?)", (code, file_id, title))
        await db.commit()
    return code

async def create_direct_order(file_id: str, user_id: int, title: str) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверка: если у пользователя уже привязано это видео, не создаем дубликат
        cursor = await db.execute(
            "SELECT code FROM orders WHERE used_by = ? AND file_id = ? LIMIT 1",
            (user_id, file_id)
        )
        existing = await cursor.fetchone()
        if existing:
            return existing[0]

        code = secrets.token_urlsafe(8)
        await db.execute(
            "INSERT INTO orders (code, file_id, is_used, used_by, title) VALUES (?, ?, 1, ?, ?)",
            (code, file_id, user_id, title)
        )
        await db.commit()
        return code

async def redeem_code(code: str, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id, is_used, used_by, title FROM orders WHERE code = ?", (code,))
        row = await cursor.fetchone()
        if not row:
            return None, None, "NOT_FOUND"

        file_id, is_used, used_by, title = row

        if is_used:
            if used_by == user_id:
                return file_id, title, "ALREADY_OWNED"
            return None, None, "USED_BY_OTHER"

        # Проверяем, есть ли уже у этого пользователя видео с таким file_id
        existing_cursor = await db.execute(
            "SELECT code, title FROM orders WHERE used_by = ? AND file_id = ? LIMIT 1",
            (user_id, file_id)
        )
        existing_order = await existing_cursor.fetchone()

        if existing_order:
            # Видео уже есть в коллекции клиента: удаляем дублирующую временную запись
            await db.execute("DELETE FROM orders WHERE code = ?", (code,))
            await db.commit()
            resolved_title = title or existing_order[1]
            return file_id, resolved_title, "ALREADY_OWNED"

        await db.execute("UPDATE orders SET is_used = 1, used_by = ? WHERE code = ?", (user_id, code))
        await db.commit()
        return file_id, title, "SUCCESS"

async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT code, file_id, title FROM orders WHERE used_by = ? ORDER BY rowid DESC", (user_id,))
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
        cursor = await db.execute("SELECT code, file_id, title FROM orders WHERE used_by = ? ORDER BY rowid DESC", (user_id,))
        return await cursor.fetchall()

async def get_order_by_code(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT code, file_id, used_by, title FROM orders WHERE code = ?", (code,))
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