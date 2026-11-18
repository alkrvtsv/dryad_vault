import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import database
import texts
import services
import keyboards
from config import ADMIN_ID

router = Router()
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)

class AdminUpload(StatesGroup):
    waiting_for_title = State()

class AdminDirectAssign(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_media = State()
    waiting_for_title = State()

class AdminRenameMedia(StatesGroup):
    waiting_for_title = State()

media_group_cache = {}

async def process_album_after_delay(media_group_id: str):
    await asyncio.sleep(1.5)
    if media_group_id not in media_group_cache:
        return
        
    data = media_group_cache.pop(media_group_id)
    messages = data["messages"]
    state = data["state"]
    bot = data["bot"]
    current_state = data["current_state"]
    target_user_id = data.get("target_user_id")
    
    file_ids = []
    media_types = []
    media_type = "album"
    title = None
    
    for msg in messages:
        try:
            f_id, m_type, _ = services.extract_media_info(msg)
            file_ids.append(f_id)
            media_types.append(m_type)
        except Exception:
            continue
            
        if not title and msg.caption and msg.caption.strip():
            title = msg.caption.strip()
            
    if not file_ids:
        return
        
    is_direct = (current_state == AdminDirectAssign.waiting_for_media.state)
    
    if title:
        if is_direct:
            saved_file_ids_str = await services.backup_and_get_album_file_ids(bot, file_ids, media_types, title)
            _, is_new = await database.create_direct_order(saved_file_ids_str, target_user_id, title, media_type)
            await state.clear()
            if is_new:
                await services.backup_database(bot, f"Альбом «{title}» напрямую привязан к заказчику ID: <code>{target_user_id}</code>")
                await messages[0].reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
        else:
            saved_file_ids_str = await services.backup_and_get_album_file_ids(bot, file_ids, media_types, title)
            code = await database.create_order(saved_file_ids_str, title, media_type)
            await services.backup_database(bot, f"Создана ссылка на альбом «{title}» ({len(file_ids)} фото, код: <code>{code}</code>)")
            bot_info = await bot.get_me()
            deep_link = f"https://t.me/{bot_info.username}?start={code}"
            reply_text = texts.admin_media_saved(code, deep_link, title, media_type)
            await messages[0].reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    else:
        if is_direct:
            await state.update_data(file_ids=file_ids, media_types=media_types, media_type=media_type)
            await state.set_state(AdminDirectAssign.waiting_for_title)
            await messages[0].answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())
        else:
            await state.update_data(file_ids=file_ids, media_types=media_types, media_type=media_type)
            await state.set_state(AdminUpload.waiting_for_title)
            await messages[0].answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())

@router.message(F.media_group_id, F.video|F.photo)
async def handle_media_group(message: types.Message, state: FSMContext, bot: Bot):
    current_state = await state.get_state()
    gid = message.media_group_id
    if gid not in media_group_cache:
        media_group_cache[gid] = {
            "messages": [], 
            "state": state, 
            "bot": bot,
            "current_state": current_state,
            "target_user_id": None
        }
        if current_state == AdminDirectAssign.waiting_for_media.state:
            data = await state.get_data()
            media_group_cache[gid]["target_user_id"] = data.get("target_user_id")
        asyncio.create_task(process_album_after_delay(gid))
    media_group_cache[gid]["messages"].append(message)

@router.message(CommandStart())
async def handle_admin_start(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await services.register_or_update_user(bot, message.from_user)
    await message.answer(texts.ADMIN_START, reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_CANCEL)
async def process_admin_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.ADMIN_ACTION_CANCELLED, reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_TEST)
async def handle_test_mode(message: types.Message, bot: Bot):
    """Обработчик кнопки тестового режима."""
    import config
    
    if not config.TEST_MODE:
        # Включаем тестовый режим
        success = await services.enable_test_mode(bot)
        if success:
            await message.answer(texts.TEST_MODE_ENABLED, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
        else:
            await message.answer("❌ Ошибка включения тестового режима", reply_markup=keyboards.get_admin_keyboard())
    else:
        # Отключаем тестовый режим
        success = await services.disable_test_mode(bot)
        if success:
            await message.answer(texts.TEST_MODE_DISABLED, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
        else:
            await message.answer("❌ Ошибка отключения тестового режима", reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_UPLOAD)
async def process_admin_upload_button(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.ADMIN_PROMPT_UPLOAD, reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_ASSIGN_DIRECT)
async def process_admin_assign_direct(message: types.Message, state: FSMContext):
    await state.set_state(AdminDirectAssign.waiting_for_user_id)
    await message.answer(texts.ADMIN_PROMPT_DIRECT_ID, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminDirectAssign.waiting_for_user_id)
async def process_admin_target_id(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(texts.ADMIN_ERR_INVALID_ID, reply_markup=keyboards.get_cancel_keyboard())
        return
    target_user_id = int(text)
    await services.sync_user_from_telegram(bot, target_user_id)
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminDirectAssign.waiting_for_media)
    await message.answer(texts.ADMIN_PROMPT_DIRECT_MEDIA, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminDirectAssign.waiting_for_media, F.video|F.photo)
async def process_admin_target_media(message: types.Message, state: FSMContext, bot: Bot):
    file_id, media_type, title = services.extract_media_info(message)
    data = await state.get_data()
    target_id = data["target_user_id"]
    if title:
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, media_type, title)
        _, is_new = await database.create_direct_order(saved_file_id, target_id, title, media_type)
        await state.clear()
        m_name = "Видео" if media_type == "video" else "Фото"
        if is_new:
            await services.backup_database(bot, f"{m_name} «{title}» напрямую привязано к заказчику ID: <code>{target_id}</code>")
            await message.reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
    else:
        await state.update_data(file_id=file_id, media_type=media_type)
        await state.set_state(AdminDirectAssign.waiting_for_title)
        await message.answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminDirectAssign.waiting_for_media)
async def process_admin_target_not_media(message: types.Message):
    await message.answer(texts.ADMIN_ERR_NEED_MEDIA, reply_markup=keyboards.get_cancel_keyboard())

@router.message(F.video|F.photo)
async def handle_media_upload(message: types.Message, state: FSMContext, bot: Bot):
    file_id, media_type, title = services.extract_media_info(message)
    if title:
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, media_type, title)
        code = await database.create_order(saved_file_id, title, media_type)
        m_name = "видео" if media_type == "video" else "фото"
        await services.backup_database(bot, f"Создана ссылка на {m_name} «{title}» (код: <code>{code}</code>)")
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={code}"
        reply_text = texts.admin_media_saved(code, deep_link, title, media_type)
        await message.reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await state.set_state(AdminUpload.waiting_for_title)
        await state.update_data(file_id=file_id, media_type=media_type)
        await message.answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminUpload.waiting_for_title, F.text)
async def process_upload_title(message: types.Message, state: FSMContext, bot: Bot):
    title = message.text.strip()
    data = await state.get_data()
    media_type = data["media_type"]
    
    await state.clear()
    
    if media_type == "album":
        file_ids = data["file_ids"]
        media_types = data["media_types"]
        saved_file_ids_str = await services.backup_and_get_album_file_ids(bot, file_ids, media_types, title)
        code = await database.create_order(saved_file_ids_str, title, media_type)
        m_name = "альбом"
        await services.backup_database(bot, f"Создана ссылка на {m_name} «{title}» (код: <code>{code}</code>)")
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={code}"
        reply_text = texts.admin_media_saved(code, deep_link, title, media_type)
        await message.reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    else:
        file_id = data["file_id"]
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, media_type, title)
        code = await database.create_order(saved_file_id, title, media_type)
        m_name = "видео" if media_type == "video" else "фото"
        await services.backup_database(bot, f"Создана ссылка на {m_name} «{title}» (код: <code>{code}</code>)")
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={code}"
        reply_text = texts.admin_media_saved(code, deep_link, title, media_type)
        await message.reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)

@router.message(AdminDirectAssign.waiting_for_title, F.text)
async def process_admin_target_title(message: types.Message, state: FSMContext, bot: Bot):
    title = message.text.strip()
    data = await state.get_data()
    target_id = data["target_user_id"]
    media_type = data["media_type"]
    
    await state.clear()
    
    if media_type == "album":
        file_ids = data["file_ids"]
        media_types = data["media_types"]
        saved_file_ids_str = await services.backup_and_get_album_file_ids(bot, file_ids, media_types, title)
        _, is_new = await database.create_direct_order(saved_file_ids_str, target_id, title, media_type)
        m_name = "Альбом"
        if is_new:
            await services.backup_database(bot, f"{m_name} «{title}» напрямую привязан к заказчику ID: <code>{target_id}</code>")
            await message.reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
    else:
        file_id = data["file_id"]
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, media_type, title)
        _, is_new = await database.create_direct_order(saved_file_id, target_id, title, media_type)
        m_name = "Видео" if media_type == "video" else "Фото"
        if is_new:
            await services.backup_database(bot, f"{m_name} «{title}» напрямую привязано к заказчику ID: <code>{target_id}</code>")
            await message.reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_CUSTOMERS_LIST)
async def process_admin_customers_list(message: types.Message, state: FSMContext):
    await state.clear()
    customers = await database.get_customers_summary()
    if not customers:
        await message.answer(texts.CUSTOMERS_EMPTY, reply_markup=keyboards.get_admin_keyboard())
        return
    markup = keyboards.build_customers_keyboard(customers, page=1)
    await message.answer(texts.CUSTOMERS_TITLE, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("cust_p:"))
async def handle_customers_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    customers = await database.get_customers_summary()
    if not customers:
        await callback.message.edit_text(texts.CUSTOMERS_EMPTY)
        await callback.answer()
        return
    markup = keyboards.build_customers_keyboard(customers, page=page)
    await callback.message.edit_text(texts.CUSTOMERS_TITLE, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("back_customers:"))
async def handle_back_to_customers(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    customers = await database.get_customers_summary()
    if not customers:
        await callback.message.edit_text(texts.CUSTOMERS_EMPTY)
        await callback.answer()
        return
    markup = keyboards.build_customers_keyboard(customers, page=page)
    await callback.message.edit_text(texts.CUSTOMERS_TITLE, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("cust:"))
async def handle_customer_click(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    user_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    orders = await database.get_customer_orders(user_id)
    if not orders:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=texts.BUTTON_BACK_CUSTOMERS, callback_data="back_customers:1")
        ]])
        await callback.message.edit_text(texts.CUSTOMER_NO_MEDIA, reply_markup=markup)
        await callback.answer()
        return
    username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("cvid_p:"))
async def handle_customer_videos_pagination(callback: types.CallbackQuery):
    _, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    orders = await database.get_customer_orders(user_id)
    if not orders:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=texts.BUTTON_BACK_CUSTOMERS, callback_data="back_customers:1")
        ]])
        await callback.message.edit_text(texts.CUSTOMER_NO_MEDIA, reply_markup=markup)
        await callback.answer()
        return
    username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("vopt:"))
async def handle_video_options(callback: types.CallbackQuery):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    order = await database.get_order_by_code(code)
    if not order:
        await callback.answer("Материал не найден", show_alert=True)
        return
    _, _, _, title, media_type = order
    media_title = title if title else "Без названия"
    username = await database.get_user_info(user_id)
    markup = keyboards.build_video_actions_keyboard(code, user_id, page)
    text = texts.media_manage_text(media_title, code, user_id, username, media_type)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("view:"))
async def handle_admin_view_media(callback: types.CallbackQuery, bot: Bot):
    code = callback.data.split(":")[1]
    order = await database.get_order_by_code(code)
    if not order:
        await callback.answer("Материал не найден", show_alert=True)
        return
    _, file_id, _, title, media_type = order
    await callback.answer()
    await services.send_protected_media(
        bot,
        chat_id=callback.message.chat.id,
        file_id=file_id,
        media_type=media_type,
        title=title,
        reply_markup=keyboards.get_admin_keyboard()
    )

@router.callback_query(F.data.startswith("newlink:"))
async def handle_create_new_link(callback: types.CallbackQuery, bot: Bot):
    _, code, _, _ = callback.data.split(":")
    order = await database.get_order_by_code(code)
    if not order:
        await callback.answer("Материал не найден", show_alert=True)
        return
    _, file_id, _, title, media_type = order
    media_title = title if title else "Без названия"
    new_code = await database.create_order(file_id, media_title, media_type)
    m_name = "видео" if media_type == "video" else "фото"
    await services.backup_database(bot, f"Создана новая ссылка для {m_name} «{media_title}» (код: <code>{new_code}</code>)")
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={new_code}"
    reply_text = texts.admin_new_link_created(new_code, deep_link, media_title, media_type)
    await callback.message.answer(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer(texts.NEW_LINK_SUCCESS)

@router.callback_query(F.data.startswith("ren:"))
async def handle_rename_media_start(callback: types.CallbackQuery, state: FSMContext):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    await state.set_state(AdminRenameMedia.waiting_for_title)
    await state.update_data(code=code, user_id=user_id, page=page)
    await callback.message.delete()
    await callback.message.answer(texts.ADMIN_PROMPT_RENAME, reply_markup=keyboards.get_cancel_keyboard())
    await callback.answer()

@router.message(AdminRenameMedia.waiting_for_title, F.text)
async def process_rename_media_title(message: types.Message, state: FSMContext, bot: Bot):
    new_title = message.text.strip()
    data = await state.get_data()
    code = data["code"]
    user_id = data["user_id"]
    page = data.get("page", 1)
    await database.update_order_title(code, new_title)
    await state.clear()
    await services.backup_database(bot, f"Переименован материал (код: <code>{code}</code>) ➔ «{new_title}»")
    await message.answer(texts.ADMIN_RENAME_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
    orders = await database.get_customer_orders(user_id)
    username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("refresh:"))
async def handle_refresh_customer(callback: types.CallbackQuery, bot: Bot):
    _, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    username, success = await services.sync_user_from_telegram(bot, user_id)
    if not success:
        await callback.answer(texts.USER_UPDATE_FAILED, show_alert=True)
        return
    await callback.answer(texts.USER_UPDATED_SUCCESS)
    orders = await database.get_customer_orders(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("del:"))
async def handle_delete_media_click(callback: types.CallbackQuery, bot: Bot):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    await database.delete_order_by_code(code)
    await services.backup_database(bot, f"Удален материал (код: <code>{code}</code>) у заказчика ID: <code>{user_id}</code>")
    await callback.answer(texts.MEDIA_DELETED_SUCCESS)
    orders = await database.get_customer_orders(user_id)
    if not orders:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=texts.BUTTON_BACK_CUSTOMERS, callback_data="back_customers:1")
        ]])
        await callback.message.edit_text(texts.CUSTOMER_NO_MEDIA, reply_markup=markup)
        return
    username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)