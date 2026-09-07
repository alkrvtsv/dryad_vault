import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
import database
from handlers import admin, client

logging.basicConfig(level=logging.INFO)

async def main():
    await database.init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(admin.router)
    dp.include_router(client.router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())