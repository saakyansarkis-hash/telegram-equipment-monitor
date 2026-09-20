import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session = os.environ["TELEGRAM_SESSION"]

client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)

# ТЕСТ: отправляем только в ОДНУ группу
TEST_GROUP_ID = -1003131421027

message = """🚜 СВОБОДЕН ЭКСКАВАТОР-ПОГРУЗЧИК

Аренда экскаватора-погрузчика с машинистом.

✅ Копка траншей и котлованов
✅ Планировка территории
✅ Погрузка грунта, щебня, песка
✅ Земляные и погрузочные работы
✅ Работа по сменам

📍 Москва, ЮВАО и Московская область
⚡ Оперативная подача

📞 8 (969) 031-55-08
💬 WhatsApp / Telegram

Техника свободна — звоните!"""


async def main():
    await client.start()

    print("=== ТЕСТ ОТПРАВКИ ===", flush=True)
    print(f"Группа: {TEST_GROUP_ID}", flush=True)

    try:
        await client.send_message(
            TEST_GROUP_ID,
            message
        )

        print(
            "=== УСПЕШНО: ТЕСТОВОЕ ОБЪЯВЛЕНИЕ ОТПРАВЛЕНО ===",
            flush=True
        )

    except FloodWaitError as e:
        print(
            f"FLOOD WAIT: Telegram просит подождать {e.seconds} сек.",
            flush=True
        )

    except Exception as e:
        print(
            f"ОШИБКА ОТПРАВКИ: {type(e).__name__}: {e}",
            flush=True
        )


with client:
    client.loop.run_until_complete(main())
