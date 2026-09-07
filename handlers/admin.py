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
    waiting_for_video = State()
    waiting_for_title = State()

class AdminRenameVideo(StatesGroup):
    waiting_for_title = State()

@router.message(CommandStart())
async def handle_admin_start(message: types.Message, state: FSMContext):
    await state.clear()
    await database.save_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(texts.ADMIN_START, reply_markup=keyboards.get_admin_keyboard())

@router.message(F.text == texts.BUTTON_CANCEL)
async def process_admin_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.ADMIN_ACTION_CANCELLED, reply_markup=keyboards.get_admin_keyboard())

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
    await state.set_state(AdminDirectAssign.waiting_for_video)
    await message.answer(texts.ADMIN_PROMPT_DIRECT_VIDEO, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminDirectAssign.waiting_for_video, F.video)
async def process_admin_target_video(message: types.Message, state: FSMContext, bot: Bot):
    file_id = message.video.file_id
    title = services.extract_video_title(message)
    data = await state.get_data()
    
    if title:
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, title)
        await database.create_direct_order(saved_file_id, data["target_user_id"], title)
        await state.clear()
        await message.reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
    else:
        await state.update_data(file_id=file_id)
        await state.set_state(AdminDirectAssign.waiting_for_title)
        await message.answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminDirectAssign.waiting_for_title, F.text)
async def process_admin_target_title(message: types.Message, state: FSMContext, bot: Bot):
    title = message.text.strip()
    data = await state.get_data()
    saved_file_id = await services.backup_and_get_file_id(bot, data["file_id"], title)
    await database.create_direct_order(saved_file_id, data["target_user_id"], title)
    await state.clear()
    await message.reply(texts.ADMIN_DIRECT_SUCCESS, reply_markup=keyboards.get_admin_keyboard())

@router.message(AdminDirectAssign.waiting_for_video)
async def process_admin_target_not_video(message: types.Message):
    await message.answer(texts.ADMIN_ERR_NEED_VIDEO, reply_markup=keyboards.get_cancel_keyboard())

@router.message(F.video)
async def handle_video_upload(message: types.Message, state: FSMContext, bot: Bot):
    file_id = message.video.file_id
    title = services.extract_video_title(message)
    
    if title:
        saved_file_id = await services.backup_and_get_file_id(bot, file_id, title)
        code = await database.create_order(saved_file_id, title)
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={code}"
        reply_text = texts.admin_video_saved(code, deep_link, title)
        await message.reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await state.set_state(AdminUpload.waiting_for_title)
        await state.update_data(file_id=file_id)
        await message.answer(texts.ADMIN_PROMPT_TITLE, reply_markup=keyboards.get_cancel_keyboard())

@router.message(AdminUpload.waiting_for_title, F.text)
async def process_upload_title(message: types.Message, state: FSMContext, bot: Bot):
    title = message.text.strip()
    data = await state.get_data()
    file_id = data["file_id"]
    saved_file_id = await services.backup_and_get_file_id(bot, file_id, title)
    code = await database.create_order(saved_file_id, title)
    await state.clear()
    
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={code}"
    reply_text = texts.admin_video_saved(code, deep_link, title)
    await message.reply(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)

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
        await callback.message.edit_text(texts.CUSTOMER_NO_VIDEOS, reply_markup=markup)
        await callback.answer()
        return
    
    full_name, username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(full_name, username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    
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
        await callback.message.edit_text(texts.CUSTOMER_NO_VIDEOS, reply_markup=markup)
        await callback.answer()
        return
    
    full_name, username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(full_name, username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("vopt:"))
async def handle_video_options(callback: types.CallbackQuery):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    
    order = await database.get_order_by_code(code)
    if not order:
        await callback.answer("Видео не найдено", show_alert=True)
        return
    
    _, _, _, title = order
    video_title = title if title else "Без названия"
    full_name, _ = await database.get_user_info(user_id)
    
    markup = keyboards.build_video_actions_keyboard(code, user_id, page)
    text = texts.video_manage_text(video_title, code, full_name)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("newlink:"))
async def handle_create_new_link(callback: types.CallbackQuery, bot: Bot):
    _, code, _, _ = callback.data.split(":")
    order = await database.get_order_by_code(code)
    if not order:
        await callback.answer("Видео не найдено", show_alert=True)
        return
    
    _, file_id, _, title = order
    video_title = title if title else "Без названия"
    new_code = await database.create_order(file_id, video_title)
    
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={new_code}"
    
    reply_text = texts.admin_new_link_created(new_code, deep_link, video_title)
    await callback.message.answer(reply_text, reply_markup=keyboards.get_admin_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer(texts.NEW_LINK_SUCCESS)

@router.callback_query(F.data.startswith("ren:"))
async def handle_rename_video_start(callback: types.CallbackQuery, state: FSMContext):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    
    await state.set_state(AdminRenameVideo.waiting_for_title)
    await state.update_data(code=code, user_id=user_id, page=page)
    
    await callback.message.delete()
    await callback.message.answer(texts.ADMIN_PROMPT_RENAME, reply_markup=keyboards.get_cancel_keyboard())
    await callback.answer()

@router.message(AdminRenameVideo.waiting_for_title, F.text)
async def process_rename_video_title(message: types.Message, state: FSMContext):
    new_title = message.text.strip()
    data = await state.get_data()
    code = data["code"]
    user_id = data["user_id"]
    page = data.get("page", 1)
    
    await database.update_order_title(code, new_title)
    await state.clear()
    
    await message.answer(texts.ADMIN_RENAME_SUCCESS, reply_markup=keyboards.get_admin_keyboard())
    
    orders = await database.get_customer_orders(user_id)
    full_name, username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(full_name, username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("refresh:"))
async def handle_refresh_customer(callback: types.CallbackQuery, bot: Bot):
    _, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    
    full_name, username, success = await services.sync_user_from_telegram(bot, user_id)
    if not success:
        await callback.answer(texts.USER_UPDATE_FAILED, show_alert=True)
        return
        
    await callback.answer(texts.USER_UPDATED_SUCCESS)
    orders = await database.get_customer_orders(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(full_name, username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("del:"))
async def handle_delete_video_click(callback: types.CallbackQuery):
    _, code, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    
    await database.delete_order_by_code(code)
    await callback.answer(texts.VIDEO_DELETED_SUCCESS)
    
    orders = await database.get_customer_orders(user_id)
    if not orders:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=texts.BUTTON_BACK_CUSTOMERS, callback_data="back_customers:1")
        ]])
        await callback.message.edit_text(texts.CUSTOMER_NO_VIDEOS, reply_markup=markup)
        return
    
    full_name, username = await database.get_user_info(user_id)
    markup, current_items, total_pages, actual_page, start_idx = keyboards.build_customer_videos_keyboard(orders, user_id, page)
    text = texts.customer_details_title(full_name, username, user_id, current_items, len(orders), actual_page, total_pages, start_idx)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)