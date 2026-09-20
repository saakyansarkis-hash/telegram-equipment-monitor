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


async def main():
    await client.start()

    print("=== TELEGRAM ADS: СПИСОК ГРУПП ===", flush=True)

    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            print(
                f"GROUP | {dialog.name} | ID: {dialog.id}",
                flush=True
            )

    print("=== КОНЕЦ СПИСКА ===", flush=True)


with client:
    client.loop.run_until_complete(main())
