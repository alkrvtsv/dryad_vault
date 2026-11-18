import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, ErrorEvent
from aiogram.exceptions import TelegramBadRequest
from config import BOT_TOKEN, ADMIN_ID
import database
from handlers import admin, client

logging.basicConfig(level=logging.INFO)

async def setup_bot_commands(bot: Bot):
    await bot.set_my_commands(
        [BotCommand(command="start", description="Главное меню")],
        scope=BotCommandScopeDefault()
    )
    if ADMIN_ID:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Панель управления")],
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )

async def errors_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок. Глушит безвредные 'не модифицированные' правки."""
    exc = event.exception
    if isinstance(exc, TelegramBadRequest) and "message is not modified" in str(exc):
        # Ничего страшного: контент сообщения не изменился
        return
    # Остальные ошибки логируем
    logging.error(f"Ошибка при обработке апдейта: {exc}", exc_info=exc)

async def main():
    await database.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.errors.register(errors_handler)
    await setup_bot_commands(bot)
    dp.include_router(admin.router)
    dp.include_router(client.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())