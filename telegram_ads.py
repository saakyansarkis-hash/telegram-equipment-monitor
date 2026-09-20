import os
import asyncio
import random

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    SlowModeWaitError,
    ChatWriteForbiddenError,
)

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session = os.environ["TELEGRAM_SESSION"]

client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)

GROUP_IDS = [
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
]

MESSAGE = """🚜 СВОБОДНА СПЕЦТЕХНИКА

Экскаватор-погрузчик • Мини-погрузчик • Самосвал • Комбинированный каток 4 т

✅ Земляные и погрузочные работы
✅ Копка траншей и котлованов
✅ Планировка территории
✅ Вывоз грунта и строительного мусора
✅ Перевозка песка, щебня и асфальтной крошки
✅ Уплотнение асфальта и щебёночного основания

📍 Москва, ЮВАО и Московская область
⚡ Оперативная подача

📞 8 (969) 031-55-08
💬 WhatsApp / Telegram

Техника свободна — звоните!"""


async def main():
    await client.start()

    print("=== ЗАПУСК РАССЫЛКИ ===", flush=True)

    sent = 0
    skipped = 0

    for group_id in GROUP_IDS:
        try:
            entity = await client.get_entity(group_id)
            group_name = getattr(entity, "title", str(group_id))

            print(
                f"ПРОБУЕМ: {group_name} | {group_id}",
                flush=True
            )

            await client.send_message(entity, MESSAGE)

            sent += 1
            print(f"OK: {group_name}", flush=True)

            # Пауза 3–5 минут между группами
            wait_seconds = random.randint(180, 300)
            print(f"Пауза {wait_seconds} сек.", flush=True)

            await asyncio.sleep(wait_seconds)

        except SlowModeWaitError as e:
            skipped += 1
            print(
                f"ПРОПУСК: медленный режим, ждать {e.seconds} сек. | {group_id}",
                flush=True
            )
            continue

        except FloodWaitError as e:
            print(
                f"FLOOD WAIT: Telegram требует ждать {e.seconds} сек. Рассылка остановлена.",
                flush=True
            )
            break

        except ChatWriteForbiddenError:
            skipped += 1
            print(
                f"ПРОПУСК: отправка запрещена | {group_id}",
                flush=True
            )
            continue

        except Exception as e:
            skipped += 1
            print(
                f"ПРОПУСК {group_id}: {type(e).__name__}: {e}",
                flush=True
            )
            continue

    print("", flush=True)
    print("=== РАССЫЛКА ЗАВЕРШЕНА ===", flush=True)
    print(f"Отправлено: {sent}", flush=True)
    print(f"Пропущено: {skipped}", flush=True)


with client:
    client.loop.run_until_complete(main())
