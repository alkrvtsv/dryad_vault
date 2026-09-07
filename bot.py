import asyncio
import logging
import os
import secrets
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DB_NAME = os.getenv("DB_NAME", "asmr_orders.db")

if not BOT_TOKEN or not ADMIN_ID_RAW:
    raise ValueError("BOT_TOKEN and ADMIN_ID must be set in .env")

ADMIN_ID = int(ADMIN_ID_RAW)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class OrderProcess(StatesGroup):
    waiting_for_code = State()

def get_client_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Получить видео")],
            [KeyboardButton(text="📜 История видео")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Загрузить видео")]
        ],
        resize_keyboard=True
    )

def get_user_keyboard(user_id: int):
    return get_admin_keyboard() if user_id == ADMIN_ID else get_client_keyboard()

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                is_used INTEGER DEFAULT 0,
                used_by INTEGER
            )
        """)
        await db.commit()

async def create_order(file_id: str) -> str:
    code = secrets.token_urlsafe(8)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO orders (code, file_id) VALUES (?, ?)", (code, file_id))
        await db.commit()
    return code

async def redeem_code(code: str, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id, is_used, used_by FROM orders WHERE code = ?", (code,))
        row = await cursor.fetchone()
        if not row:
            return None, "NOT_FOUND"
        file_id, is_used, used_by = row
        if is_used:
            if used_by == user_id:
                return file_id, "ALREADY_OWNED"
            return None, "USED_BY_OTHER"
        await db.execute("UPDATE orders SET is_used = 1, used_by = ? WHERE code = ?", (user_id, code))
        await db.commit()
        return file_id, "SUCCESS"

async def get_user_videos(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id FROM orders WHERE used_by = ?", (user_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def send_protected_video(chat_id: int, file_id: str):
    await bot.send_video(
        chat_id=chat_id,
        video=file_id,
        caption="Ваше персональное видео ✨\n\n<i>Сохранение и пересылка ограничены.</i>",
        protect_content=True,
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text == "📤 Загрузить видео", F.from_user.id == ADMIN_ID)
async def process_admin_upload_button(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправьте видеофайл для генерации ссылки и кода доступа.", reply_markup=get_admin_keyboard())

@dp.message(F.video, F.from_user.id == ADMIN_ID)
async def handle_video_upload(message: types.Message):
    file_id = message.video.file_id
    code = await create_order(file_id)
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={code}"
    
    text = (
        "✅ <b>Видео успешно сохранено!</b>\n\n"
        f"🔑 Код доступа: <code>{code}</code>\n\n"
        "🔗 Ссылка для клиента:\n"
        f"{deep_link}"
    )
    await message.reply(text, reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)

@dp.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    code = command.args.strip()
    keyboard = get_user_keyboard(message.from_user.id)
    file_id, status = await redeem_code(code, message.from_user.id)
    
    if status == "NOT_FOUND":
        await message.answer("❌ Код не найден.", reply_markup=keyboard)
        return
    if status == "USED_BY_OTHER":
        await message.answer("⚠️ Этот код уже был использован другим пользователем.", reply_markup=keyboard)
        return
        
    await message.answer("Загружаем ваше видео...", reply_markup=keyboard)
    await send_protected_video(message.chat.id, file_id)

@dp.message(CommandStart())
async def handle_regular_start(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Панель администратора. Нажмите «📤 Загрузить видео» или отправьте файл напрямую.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "Добро пожаловать! Воспользуйтесь кнопками меню ниже для работы с заказами.",
            reply_markup=get_client_keyboard()
        )

@dp.message(F.text == "🎬 Получить видео", F.from_user.id != ADMIN_ID)
async def process_get_video_button(message: types.Message, state: FSMContext):
    await state.set_state(OrderProcess.waiting_for_code)
    await message.answer("Пожалуйста, отправьте текстовый код доступа:")

@dp.message(F.text == "📜 История видео", F.from_user.id != ADMIN_ID)
async def process_history_button(message: types.Message, state: FSMContext):
    await state.clear()
    videos = await get_user_videos(message.from_user.id)
    
    if not videos:
        await message.answer("У вас пока нет доступных видео.", reply_markup=get_client_keyboard())
        return
    
    await message.answer(f"Найдено видео: {len(videos)}. Отправляю...", reply_markup=get_client_keyboard())
    for file_id in videos:
        await send_protected_video(message.chat.id, file_id)
        await asyncio.sleep(0.5)

@dp.message(OrderProcess.waiting_for_code, F.text, F.from_user.id != ADMIN_ID)
async def process_code_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    
    if text == "🎬 Получить видео":
        await message.answer("Отправьте текстовый код доступа:")
        return
        
    if text == "📜 История видео":
        await process_history_button(message, state)
        return

    file_id, status = await redeem_code(text, message.from_user.id)
    await state.clear()
    
    if status == "NOT_FOUND":
        await message.answer("❌ Код не найден или введен неверно. Нажмите «🎬 Получить видео», чтобы попробовать снова.", reply_markup=get_client_keyboard())
        return
        
    if status == "USED_BY_OTHER":
        await message.answer("⚠️ Этот код уже активирован другим пользователем.", reply_markup=get_client_keyboard())
        return
    
    await message.answer("Код принят! Загружаем видео...", reply_markup=get_client_keyboard())
    await send_protected_video(message.chat.id, file_id)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())