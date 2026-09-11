import os
import urllib.parse
import urllib.request

from telethon import TelegramClient, events
from telethon.sessions import StringSession


api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
session = os.getenv("TELEGRAM_SESSION", "").strip()

bot_token = os.getenv("BOT_TOKEN")
bot_chat_id = os.getenv("BOT_CHAT_ID")


client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)


keywords = [
    "нужен экскаватор",
    "ищу экскаватор",
    "требуется экскаватор",
    "экскаватор-погрузчик",
    "экскаватор погрузчик",
    "нужен погрузчик",
    "ищу погрузчик",
    "нужен мини-погрузчик",
    "нужен мини погрузчик",
    "ищу мини-погрузчик",
    "ищу мини погрузчик",
    "нужен каток",
    "ищу каток",
    "требуется каток",
    "аренда экскаватора",
    "аренда погрузчика",
    "аренда спецтехники",
]

exclude_words = [
    "продам",
    "продаю",
    "вакансия",
    "ищу работу",
]


def send_to_bot(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": bot_chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


@client.on(events.NewMessage)
async def handler(event):
    text = (event.message.message or "").strip()

    if not text:
        return

    text_lower = text.lower()

    if any(word in text_lower for word in exclude_words):
        return

    matched = [word for word in keywords if word in text_lower]

    if not matched:
        return

    try:
        chat = await event.get_chat()
        sender = await event.get_sender()

        chat_name = getattr(chat, "title", None) or "Личный чат"

        username = getattr(sender, "username", None)
        sender_name = (
            f"@{username}"
            if username
            else getattr(sender, "first_name", None) or "Не указан"
        )

        chat_username = getattr(chat, "username", None)

        message_link = ""
        if chat_username:
            message_link = (
                f"\n\n🔗 Ссылка:\n"
                f"https://t.me/{chat_username}/{event.message.id}"
            )

        alert = (
            "🔥 НАЙДЕНА ЗАЯВКА НА СПЕЦТЕХНИКУ\n\n"
            f"📍 Группа: {chat_name}\n"
            f"👤 Автор: {sender_name}\n"
            f"🔎 Совпадение: {', '.join(matched)}\n\n"
            f"💬 Сообщение:\n{text}"
            f"{message_link}"
        )

        send_to_bot(alert)

        print("Заявка отправлена в Telegram-бот", flush=True)

    except Exception as error:
        print("Ошибка обработки сообщения:", error, flush=True)


print("Монитор Telegram запущен", flush=True)

client.start()
client.run_until_disconnected()


client.start()
client.run_until_disconnected()
