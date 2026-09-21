import os
import logging
from datetime import datetime
from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

import database
import texts
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID, DB_NAME

def extract_media_info(message: types.Message) -> tuple[str, str, str | None]:
    """Возвращает (file_id, media_type, title)."""
    if message.video:
        file_id = message.video.file_id
        media_type = "video"
        title = None
        if message.caption and message.caption.strip():
            title = message.caption.strip()
        elif message.video.file_name:
            name, _ = os.path.splitext(message.video.file_name)
            if name.strip():
                title = name.strip()
        return file_id, media_type, title
    elif message.photo:
        file_id = message.photo[-1].file_id  # наибольшее разрешение
        media_type = "photo"
        title = message.caption.strip() if message.caption and message.caption.strip() else None
        return file_id, media_type, title
    raise ValueError("Message contains neither video nor photo")

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

async def backup_and_get_file_id(bot: Bot, file_id: str, media_type: str, title: str | None = None) -> str:
    if not ARCHIVE_CHANNEL_ID:
        return file_id
    try:
        icon = "📦 🎬" if media_type == "video" else "📦 🖼"
        caption = f"{icon} <b>{title}</b>" if title else f"{icon} <b>Архив</b>"
        if media_type == "video":
            archived_msg = await bot.send_video(
                chat_id=ARCHIVE_CHANNEL_ID,
                video=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            return archived_msg.video.file_id
        else:
            archived_msg = await bot.send_photo(
                chat_id=ARCHIVE_CHANNEL_ID,
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            return archived_msg.photo[-1].file_id
    except Exception:
        return file_id

async def send_protected_media(
    bot: Bot,
    chat_id: int,
    file_id: str,
    media_type: str = "video",
    title: str | None = None,
    reply_markup=None
):
    if media_type == "video":
        await bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=texts.media_caption(title),
            protect_content=True,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await bot.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=texts.media_caption(title),
            protect_content=True,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

async def notify_admin(bot: Bot, code: str, user: types.User, title: str | None = None, media_type: str = "video"):
    msg = texts.admin_order_activated(
        code=code,
        username=user.username,
        user_id=user.id,
        title=title,
        media_type=media_type
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