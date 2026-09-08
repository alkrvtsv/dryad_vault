import os
import logging
from datetime import datetime
from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

import database
import texts
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID, DB_NAME

def extract_video_title(message: types.Message) -> str | None:
    if message.caption and message.caption.strip():
        return message.caption.strip()
    if message.video and message.video.file_name:
        name, _ = os.path.splitext(message.video.file_name)
        if name.strip():
            return name.strip()
    return None

async def backup_database(bot: Bot, description: str):
    if not ARCHIVE_CHANNEL_ID or not os.path.exists(DB_NAME):
        return
        
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caption = (
        f"💾 <b>Резервная копия базы данных</b>\n\n"
        f"📌 <b>Действие:</b> {description}\n"
        f"🕒 <b>Время:</b> <code>{now_str}</code>"
    )
    try:
        doc = FSInputFile(DB_NAME, filename=f"asmr_orders_{file_timestamp}.db")
        await bot.send_document(
            chat_id=ARCHIVE_CHANNEL_ID,
            document=doc,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Не удалось отправить бэкап базы данных: {e}")

async def register_or_update_user(bot: Bot, user: types.User):
    status = await database.save_user(user.id, user.username)
    user_ref = f"@{user.username}" if user.username else f"ID: {user.id}"
    
    if status == "NEW":
        await backup_database(bot, f"Новый заказчик добавлен в базу: {user_ref} (ID: <code>{user.id}</code>)")
    elif status == "UPDATED":
        await backup_database(bot, f"Обновлен юзернейм заказчика: {user_ref} (ID: <code>{user.id}</code>)")

async def backup_and_get_file_id(bot: Bot, file_id: str, title: str | None = None) -> str:
    if not ARCHIVE_CHANNEL_ID:
        return file_id
    try:
        caption = f"📦 <b>{title}</b>" if title else "📦 <b>Видеоархив</b>"
        archived_msg = await bot.send_video(
            chat_id=ARCHIVE_CHANNEL_ID,
            video=file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        return archived_msg.video.file_id
    except Exception:
        return file_id

async def send_protected_video(
    bot: Bot,
    chat_id: int,
    file_id: str,
    title: str | None = None,
    reply_markup=None
):
    """Отправляет защищенное видео и прикрепляет актуальную клавиатуру."""
    await bot.send_video(
        chat_id=chat_id,
        video=file_id,
        caption=texts.video_caption(title),
        protect_content=True,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def notify_admin(bot: Bot, code: str, user: types.User, title: str | None = None):
    msg = texts.admin_order_activated(
        code=code,
        username=user.username,
        user_id=user.id,
        title=title
    )
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML)

async def sync_user_from_telegram(bot: Bot, user_id: int):
    try:
        chat = await bot.get_chat(user_id)
        username = chat.username
        status = await database.save_user(user_id, username)
        if status in ("NEW", "UPDATED"):
            user_ref = f"@{username}" if username else "нет"
            await backup_database(bot, f"Ручная синхронизация заказчика: {user_ref} (ID: <code>{user_id}</code>)")
        return username, True
    except Exception:
        return None, False