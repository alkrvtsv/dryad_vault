import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import BOT_TOKEN, ADMIN_ID
import database
from handlers import admin, client

logging.basicConfig(level=logging.INFO)

async def setup_bot_commands(bot: Bot):
    # Оставляем только /start для обычных пользователей
    await bot.set_my_commands(
        [BotCommand(command="start", description="Главное меню")],
        scope=BotCommandScopeDefault()
    )

    # Оставляем только /start для администратора
    if ADMIN_ID:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Панель управления")],
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )

async def main():
    await database.init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    await setup_bot_commands(bot)
    
    dp.include_router(admin.router)
    dp.include_router(client.router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())