import os
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

# ТОЛЬКО ЭТИ ГРУППЫ РАЗРЕШЕНЫ
allowed_group_ids = {
    -1003131421027,
    -1001809918387,
    -1001539684326,
    -1001441296814,
    -1001418585777,
    -1002490441950,
    -1001415675181,
    -1001685481181,
    -1001856584867,
    -1002350807807,
    -1001276185967,
    -1003724018857,
    -1001118491651,
    -1002061929686,
    -1001459409687,
    -1001306098132,
    -1003306039720,
    -1001301136511,
    -1001278195228,
    -1001222872680,
    -1001228954856,
    -1002375169218,
    -1001419440228,
    -1001882638967,
    -1003481966234,
    -1003627473505,
    -1001246232066,
}


async def main():
    await client.start()

    print("=== ПРОВЕРКА БЕЛОГО СПИСКА ===", flush=True)

    found = 0

    async for dialog in client.iter_dialogs():

        if not dialog.is_group:
            continue

        if dialog.id not in allowed_group_ids:
            continue

        found += 1

        print(
            f"OK | {dialog.name} | ID: {dialog.id}",
            flush=True
        )

    print(
        f"=== НАЙДЕНО: {found} ИЗ {len(allowed_group_ids)} ===",
        flush=True
    )

    # ВАЖНО:
    # Пока ничего автоматически не отправляем.
    print("=== СООБЩЕНИЯ НЕ ОТПРАВЛЯЛИСЬ ===", flush=True)


with client:
    client.loop.run_until_complete(main())
