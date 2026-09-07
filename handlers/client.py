from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

import database
import texts
import services
import keyboards
from config import ADMIN_ID

router = Router()

class OrderProcess(StatesGroup):
    waiting_for_code = State()

@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    await callback.answer()

@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message, command: CommandObject, state: FSMContext, bot: Bot):
    await state.clear()
    await database.save_user(message.from_user.id, message.from_user.username)
    
    code = command.args.strip()
    keyboard = keyboards.get_user_keyboard(message.from_user.id)
    file_id, title, status = await database.redeem_code(code, message.from_user.id)
    
    if status == "NOT_FOUND":
        await message.answer(texts.ERR_CODE_NOT_FOUND_LINK, reply_markup=keyboard)
        return
    if status == "USED_BY_OTHER":
        await message.answer(texts.ERR_USED_BY_OTHER, reply_markup=keyboard)
        return
        
    await message.answer(texts.VIDEO_LOADING, reply_markup=keyboard)
    await services.send_protected_video(bot, message.chat.id, file_id, title)

    if status == "SUCCESS":
        await services.notify_admin(bot, code, message.from_user, title)

@router.message(CommandStart(), F.from_user.id != ADMIN_ID)
async def handle_regular_start(message: types.Message, state: FSMContext):
    await state.clear()
    await database.save_user(message.from_user.id, message.from_user.username)
    await message.answer(texts.CLIENT_START, reply_markup=keyboards.get_client_keyboard(), parse_mode=ParseMode.HTML)

@router.message(F.text == texts.BUTTON_GET_VIDEO, F.from_user.id != ADMIN_ID)
async def process_get_video_button(message: types.Message, state: FSMContext):
    await state.set_state(OrderProcess.waiting_for_code)
    await message.answer(texts.CLIENT_ASK_CODE)

@router.message(F.text == texts.BUTTON_HISTORY, F.from_user.id != ADMIN_ID)
async def process_history_button(message: types.Message, state: FSMContext):
    await state.clear()
    await database.save_user(message.from_user.id, message.from_user.username)
    
    orders = await database.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer(texts.HISTORY_EMPTY, reply_markup=keyboards.get_client_keyboard())
        return
    
    markup = keyboards.build_client_history_keyboard(orders, page=1)
    await message.answer(texts.CLIENT_HISTORY_TITLE, reply_markup=markup, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("my_p:"), F.from_user.id != ADMIN_ID)
async def handle_client_history_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    orders = await database.get_user_orders(callback.from_user.id)
    if not orders:
        await callback.message.edit_text(texts.HISTORY_EMPTY)
        await callback.answer()
        return
    
    markup = keyboards.build_client_history_keyboard(orders, page=page)
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()

@router.callback_query(F.data.startswith("my_v:"), F.from_user.id != ADMIN_ID)
async def handle_client_video_click(callback: types.CallbackQuery, bot: Bot):
    code = callback.data.split(":")[1]
    order = await database.get_order_by_code(code)
    if not order or order[2] != callback.from_user.id:
        await callback.answer("Видео не найдено или недоступно", show_alert=True)
        return
    
    _, file_id, _, title = order
    await callback.answer()
    await services.send_protected_video(bot, callback.message.chat.id, file_id, title)

@router.message(OrderProcess.waiting_for_code, F.text, F.from_user.id != ADMIN_ID)
async def process_code_input(message: types.Message, state: FSMContext, bot: Bot):
    await database.save_user(message.from_user.id, message.from_user.username)
    text = message.text.strip()
    
    if text == texts.BUTTON_GET_VIDEO:
        await message.answer(texts.CLIENT_ASK_CODE)
        return
        
    if text == texts.BUTTON_HISTORY:
        await process_history_button(message, state)
        return

    file_id, title, status = await database.redeem_code(text, message.from_user.id)
    await state.clear()
    
    if status == "NOT_FOUND":
        await message.answer(texts.ERR_CODE_NOT_FOUND, reply_markup=keyboards.get_client_keyboard())
        return
        
    if status == "USED_BY_OTHER":
        await message.answer(texts.ERR_USED_BY_OTHER, reply_markup=keyboards.get_client_keyboard())
        return
    
    await message.answer(texts.VIDEO_LOADING, reply_markup=keyboards.get_client_keyboard())
    await services.send_protected_video(bot, message.chat.id, file_id, title)

    if status == "SUCCESS":
        await services.notify_admin(bot, text, message.from_user, title)