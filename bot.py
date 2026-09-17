import os
import asyncio
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

POSTS = [
    "لا حَولَ و لا قُوّة إِلا بِالله.",
    "🌟 منشور ثاني - عدّلني",
    "💎 منشور ثالث - عدّلني",
]

async def main():
    bot = Bot(token=TOKEN)
    hour = datetime.now(timezone.utc).hour
    post = POSTS[hour % len(POSTS)]
    await bot.send_message(
        chat_id=CHAT_ID,
        text=post,
        parse_mode=ParseMode.HTML
    )
    print(f"✅ تم إرسال: {post[:30]}")

if __name__ == "__main__":
    asyncio.run(main())
