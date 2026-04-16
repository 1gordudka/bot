import asyncio
import aiohttp
import os
from aiohttp import web
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = "8754552598:AAGEQxAv7vlIZYou6q2sv7SC2geIMHcIyOY"
PORT = int(os.environ.get("PORT", 8080))

SITES = [
    "https://ru-print.ru/",
    "https://yareklama24.ru/",
    "https://shop-krasivo.ru/",
    "http://proffkupavna.ru/",
    "https://copybar.ru",
    "https://f1-print.ru/",
    "https://ss-kp.ru/",
]

TIMEOUT = 10
CHECK_TIME = time(9, 0)
TZ = ZoneInfo("Europe/Moscow")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
subscribers: set[int] = set()


async def check_site(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT), ssl=False) as r:
            return f"{url} — ✅ OK ({r.status})" if r.status < 400 else f"{url} — ⚠️ {r.status}"
    except asyncio.TimeoutError:
        return f"{url} — ❌ TIMEOUT"
    except Exception as e:
        return f"{url} — ❌ {type(e).__name__}"


async def check_all():
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as s:
        results = await asyncio.gather(*(check_site(s, u) for u in SITES))
    ts = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")
    return f"📊 Проверка сайтов {ts} МСК\n\n" + "\n".join(results)


@dp.message(CommandStart())
async def start(msg: Message):
    subscribers.add(msg.chat.id)
    await msg.answer("Готово, подписал ✅\nКаждый день в 9:00 МСК буду присылать пинг сайтов.\n\nСейчас проверю разок для теста...")
    await msg.answer(await check_all())


async def scheduler():
    while True:
        now = datetime.now(TZ)
        target = datetime.combine(now.date(), CHECK_TIME, tzinfo=TZ)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        report = await check_all()
        for chat_id in list(subscribers):
            try:
                await bot.send_message(chat_id, report)
            except Exception as e:
                print(f"Ошибка отправки в {chat_id}: {e}")


async def healthcheck(request):
    return web.Response(text="ok")


async def run_web():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Healthcheck на порту {PORT}")


async def main():
    await run_web()
    asyncio.create_task(scheduler())
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
