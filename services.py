import os
import logging
import json
import shutil
from datetime import datetime
from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

import database
import texts
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID, DB_NAME, TEST_BACKUP_PATH
import config

def extract_media_info(message: types.Message) -> tuple[str, str, str|None]:
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
        file_id = message.photo[-1].file_id
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

async def backup_and_get_file_id(bot: Bot, file_id: str, media_type: str, title: str|None=None) -> tuple[str, int|None]:
    """Сохраняет файл в архив и возвращает (новый_file_id, archive_message_id)."""
    if not ARCHIVE_CHANNEL_ID:
        return file_id, None
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
            if config.TEST_MODE:
                config.TEST_ARCHIVED_MESSAGES.append((ARCHIVE_CHANNEL_ID, archived_msg.message_id))
            return archived_msg.video.file_id, archived_msg.message_id
        else:
            archived_msg = await bot.send_photo(
                chat_id=ARCHIVE_CHANNEL_ID,
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            if config.TEST_MODE:
                config.TEST_ARCHIVED_MESSAGES.append((ARCHIVE_CHANNEL_ID, archived_msg.message_id))
            return archived_msg.photo[-1].file_id, archived_msg.message_id
    except Exception:
        return file_id, None

async def backup_and_get_album_file_ids(bot: Bot, file_ids: list[str], media_types: list[str], title: str|None=None) -> tuple[str, list[int]]:
    """Сохраняет альбом в архив и возвращает (json_str, [archive_message_ids])."""
    if not ARCHIVE_CHANNEL_ID:
        return json.dumps([{"id": fid, "type": m_type} for fid, m_type in zip(file_ids, media_types)]), []
    try:
        from aiogram.types import InputMediaPhoto, InputMediaVideo
        media_group = []
        for i, fid in enumerate(file_ids):
            if media_types[i] == "video":
                media_group.append(InputMediaVideo(media=fid, caption=title or "Архив", parse_mode=ParseMode.HTML) if i == 0 else InputMediaVideo(media=fid))
            else:
                media_group.append(InputMediaPhoto(media=fid, caption=title or "Архив", parse_mode=ParseMode.HTML) if i == 0 else InputMediaPhoto(media=fid))
        
        archived_msgs = await bot.send_media_group(
            chat_id=ARCHIVE_CHANNEL_ID,
            media=media_group
        )
        
        archive_message_ids = []
        for msg in archived_msgs:
            archive_message_ids.append(msg.message_id)
            if config.TEST_MODE:
                config.TEST_ARCHIVED_MESSAGES.append((ARCHIVE_CHANNEL_ID, msg.message_id))
        
        new_media_list = []
        for i, m in enumerate(archived_msgs):
            if media_types[i] == "video":
                new_media_list.append({"id": m.video.file_id, "type": "video"})
            else:
                new_media_list.append({"id": m.photo[-1].file_id, "type": "photo"})
        return json.dumps(new_media_list), archive_message_ids
    except Exception as e:
        logging.error(f"Album backup failed: {e}")
        return json.dumps([{"id": fid, "type": m_type} for fid, m_type in zip(file_ids, media_types)]), []

async def delete_from_archive(bot: Bot, archive_message_id_str: str|None) -> int:
    """Удаляет сообщения из архива по списку ID (строка через запятую). Возвращает количество удаленных."""
    if not ARCHIVE_CHANNEL_ID or not archive_message_id_str:
        return 0
    deleted = 0
    try:
        ids = [int(x.strip()) for x in archive_message_id_str.split(",") if x.strip()]
        for msg_id in ids:
            try:
                await bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=msg_id)
                deleted += 1
            except Exception as e:
                logging.error(f"Не удалось удалить сообщение {msg_id} из архива: {e}")
    except Exception as e:
        logging.error(f"Ошибка парсинга archive_message_id: {e}")
    return deleted

async def send_protected_media(
    bot: Bot,
    chat_id: int,
    file_id: str,
    media_type: str="video",
    title: str|None=None,
    reply_markup=None
):
    """Отправляет защищенный материал пользователю и отслеживает его в тестовом режиме."""
    if media_type == "album":
        try:
            media_list = json.loads(file_id)
        except Exception:
            media_list = [{"id": fid, "type": "photo"} for fid in file_id.split(",")]
            
        from aiogram.types import InputMediaPhoto, InputMediaVideo
        media_group = []
        for i, item in enumerate(media_list):
            fid = item["id"]
            m_type = item["type"]
            if m_type == "video":
                media_group.append(InputMediaVideo(
                    media=fid, 
                    caption=texts.media_caption(title) if i == 0 else None, 
                    parse_mode=ParseMode.HTML
                ))
            else:
                media_group.append(InputMediaPhoto(
                    media=fid, 
                    caption=texts.media_caption(title) if i == 0 else None, 
                    parse_mode=ParseMode.HTML
                ))
        
        sent_msgs = await bot.send_media_group(
            chat_id=chat_id,
            media=media_group,
            protect_content=True
        )
        
        if config.TEST_MODE:
            for msg in sent_msgs:
                config.TEST_SENT_MESSAGES.append((chat_id, msg.message_id))
        
        if reply_markup:
            menu_msg = await bot.send_message(
                chat_id=chat_id, 
                text="⬇️ Меню:", 
                reply_markup=reply_markup
            )
            if config.TEST_MODE:
                config.TEST_SENT_MESSAGES.append((chat_id, menu_msg.message_id))
            
    elif media_type == "video":
        sent_msg = await bot.send_video(
            chat_id=chat_id, video=file_id, caption=texts.media_caption(title),
            protect_content=True, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        if config.TEST_MODE:
            config.TEST_SENT_MESSAGES.append((chat_id, sent_msg.message_id))
    else:
        sent_msg = await bot.send_photo(
            chat_id=chat_id, photo=file_id, caption=texts.media_caption(title),
            protect_content=True, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        if config.TEST_MODE:
            config.TEST_SENT_MESSAGES.append((chat_id, sent_msg.message_id))

async def notify_admin(bot: Bot, code: str, user: types.User, title: str|None=None, media_type: str="video"):
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

async def enable_test_mode(bot: Bot) -> bool:
    """Включает режим тестирования. Возвращает True если успешно."""
    if config.TEST_MODE:
        return False
    
    try:
        if os.path.exists(DB_NAME):
            shutil.copy2(DB_NAME, TEST_BACKUP_PATH)
        
        config.TEST_ARCHIVED_MESSAGES.clear()
        config.TEST_SENT_MESSAGES.clear()
        config.TEST_MODE = True
        
        await backup_database(bot, "🧪 Включен режим тестирования")
        
        return True
    except Exception as e:
        logging.error(f"Ошибка включения тестового режима: {e}")
        return False

async def disable_test_mode(bot: Bot) -> bool:
    """Отключает режим тестирования, восстанавливает БД и удаляет тестовые материалы."""
    if not config.TEST_MODE:
        return False
    
    try:
        # 1. Удаляем материалы из архивного канала
        archive_deleted = 0
        for chat_id, message_id in config.TEST_ARCHIVED_MESSAGES:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                archive_deleted += 1
            except Exception as e:
                logging.error(f"Не удалось удалить сообщение {message_id} из архива: {e}")
        
        # 2. Удаляем материалы, отправленные пользователям
        user_deleted = 0
        for chat_id, message_id in config.TEST_SENT_MESSAGES:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                user_deleted += 1
            except Exception as e:
                logging.error(f"Не удалось удалить сообщение {message_id} у пользователя: {e}")
        
        # Восстанавливаем базу данных из бэкапа
        if os.path.exists(TEST_BACKUP_PATH):
            shutil.copy2(TEST_BACKUP_PATH, DB_NAME)
            os.remove(TEST_BACKUP_PATH)
        
        config.TEST_MODE = False
        config.TEST_ARCHIVED_MESSAGES.clear()
        config.TEST_SENT_MESSAGES.clear()
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"✅ Режим тестирования завершен.\n"
                f"🗑 Удалено из архива: {archive_deleted}\n"
                f"🗑 Удалено у пользователей: {user_deleted}"
            )
        )
        
        return True
    except Exception as e:
        logging.error(f"Ошибка отключения тестового режима: {e}")
        return False