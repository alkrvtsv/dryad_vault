import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import BOT_TOKEN, ADMIN_ID
import database
from handlers import admin, client

logging.basicConfig(level=logging.INFO)

async def setup_bot_commands(bot: Bot):
    client_commands = [
        BotCommand(command="start", description="Главное меню / Меню"),
        BotCommand(command="history", description="Мои видео"),
        BotCommand(command="get", description="Ввести код доступа"),
    ]
    await bot.set_my_commands(client_commands, scope=BotCommandScopeDefault())

    if ADMIN_ID:
        admin_commands = [
            BotCommand(command="start", description="Панель управления"),
            BotCommand(command="customers", description="Список заказчиков"),
            BotCommand(command="cancel", description="Отмена действия"),
        ]
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

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