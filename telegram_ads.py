import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session = os.environ["TELEGRAM_SESSION"]

client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)

keywords = [
    "спецтех",
    "экскават",
    "погруз",
    "аренд",
    "строй",
    "строител",
    "дорож",
    "щеб",
    "песок",
    "грунт",
    "асфальт",
    "любер",
    "котельник",
    "лыткар",
    "москва"
]


async def main():
    await client.start()

    print("=== ПОДХОДЯЩИЕ ГРУППЫ ДЛЯ ОБЪЯВЛЕНИЯ ===", flush=True)

    count = 0

    async for dialog in client.iter_dialogs():
        if not dialog.is_group:
            continue

        name = dialog.name or ""
        name_lower = name.lower()

        if any(word in name_lower for word in keywords):
            count += 1
            print(
                f"GROUP | {name} | ID: {dialog.id}",
                flush=True
            )

    print(f"=== НАЙДЕНО ГРУПП: {count} ===", flush=True)
    print("=== НИ ОДНО СООБЩЕНИЕ НЕ ОТПРАВЛЕНО ===", flush=True)


with client:
    client.loop.run_until_complete(main())
