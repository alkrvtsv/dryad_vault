import os
from aiogram import Bot, types
from aiogram.enums import ParseMode
import database
import texts
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID

def extract_video_title(message: types.Message) -> str | None:
    if message.caption and message.caption.strip():
        return message.caption.strip()
    if message.video and message.video.file_name:
        name, _ = os.path.splitext(message.video.file_name)
        if name.strip():
            return name.strip()
    return None

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

async def send_protected_video(bot: Bot, chat_id: int, file_id: str, title: str | None = None):
    await bot.send_video(
        chat_id=chat_id,
        video=file_id,
        caption=texts.video_caption(title),
        protect_content=True,
        parse_mode=ParseMode.HTML
    )

async def notify_admin(bot: Bot, code: str, user: types.User, title: str | None = None):
    msg = texts.admin_order_activated(
        code=code,
        name=user.full_name,
        username=user.username,
        user_id=user.id,
        title=title
    )
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML)

async def sync_user_from_telegram(bot: Bot, user_id: int):
    try:
        chat = await bot.get_chat(user_id)
        name_parts = [chat.first_name, chat.last_name]
        full_name = " ".join([p for p in name_parts if p]) or "Пользователь"
        username = chat.username
        await database.save_user(user_id, full_name, username)
        return full_name, username, True
    except Exception:
        return None, None, False