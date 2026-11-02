import os
import asyncio
from telegram import Bot

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

POST = "لا حَولَ و لا قُوّة إِلا بِالله."

async def main():
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=POST)
    print("✅ تم إرسال المنشور")

if __name__ == "__main__":
    asyncio.run(main())
