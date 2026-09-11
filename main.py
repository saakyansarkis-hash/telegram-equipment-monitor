import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")

session = os.getenv("TELEGRAM_SESSION", "").strip().strip('"').strip("'")

print("SESSION LENGTH:", len(session))
print("SESSION FIRST CHAR:", session[:1])

client = TelegramClient(StringSession(session), api_id, api_hash)

keywords = [
    "нужен экскаватор-погрузчик",
    "ищу экскаватор-погрузчик",
    "экскаватор-погрузчик",
    "нужен каток",
    "нужен самосвал",
    "нужны самосвалы",
    "ищу самосвал",
    "требуется самосвал",
    "нужен мини-погрузчик",
    "нужен мини погрузчик",
    "ищу мини-погрузчик",
    "ищу мини погрузчик",
    "требуется мини-погрузчик",
]


@client.on(events.NewMessage)
async def handler(event):
    text = (event.message.message or "").lower()

    for word in keywords:
        if word in text:
            print("Найдена заявка:")
            print(event.message.message)
            break


client.start()
client.run_until_disconnected()
