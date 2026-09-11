import os
import re
import urllib.parse
import urllib.request

from telethon import TelegramClient, events
from telethon.sessions import StringSession


# =========================
# НАСТРОЙКИ
# =========================

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


# =========================
# ГЕОГРАФИЯ
# =========================

locations = [
    "люберцы",
    "люберцах",
    "люберец",
    "лыткарино",
    "жуковский",
    "жуковском",

    "котельники",
    "дзержинский",
    "дзержинском",
    "томилино",
    "красково",
    "малаховка",
    "октябрьский",
    "быково",
    "раменское",
    "раменском",
]


# =========================
# СПЕЦТЕХНИКА
# =========================

equipment_words = [
        "асфальтный скол",
    "асфальтовый скол",
    "скол асфальта",
    "бой бетона",
    "бетонный бой",
    "бой бетонный",
    "асфальтная крошка",
    "асфальтовая крошка",
    "крошка асфальта",
    "песок",
    "песка",
    "щебень",
    "щебня",
    "грунт",
    "грунта",
    "чернозем",
    "чернозём",
    "пгс",
    "опгс",    
    "куплю",
    "купим",
    "закупаем",
    "закупим",
    "нужен материал",
    "нужны материалы",
    "нужна доставка",
    "нужно с доставкой",
    "с доставкой",
    "требуется материал",
    "требуются материалы",
    "кто возит",
    "кто привезет",
    "кто привезёт",
    "кто продает",
    "кто продаёт",   
    "продам",
    "продаю",
    "продаем",
    "продаём",
    "продажа",
    "предлагаем",
    "в наличии",
    "наша техника",
    "услуги спецтехники",
    "оказываем услуги",
    "вакансия",
    "ищу работу",
    "ищет работу",
]


# Слова, которые обычно показывают, что технику ИЩУТ
request_words = [
    "нужен",
    "нужна",
    "нужно",
    "нужны",
    "требуется",
    "требуются",
    "ищу",
    "ищем",
    "кто может",
    "кто сможет",
    "кто есть",
    "есть кто",
    "необходим",
    "необходима",
    "необходимы",
    "возьму в аренду",
    "арендовать",
    "аренда",
    "дайте контакт",
    "подскажите кто",
    "куплю",
    "купим",
    "закупаем",
    "закупим",
    "нужен материал",
    "нужны материалы",
    "нужна доставка",
    "нужно с доставкой",
    "с доставкой",
    "требуется материал",
    "требуются материалы",
    "кто возит",
    "кто привезет",
    "кто привезёт",
    "кто продает",
    "кто продаёт",
]


def calculate_score(text, equipment_found, location_found):
    score = 1

    if any(word in text for word in [
        "срочно",
        "сегодня",
        "прямо сейчас",
        "в течение часа"
    ]):
        score += 3

    elif any(word in text for word in [
        "завтра",
        "на завтра",
        "утром"
    ]):
        score += 2

    if any(word in text for word in [
        "экскаватор-погрузчик",
        "экскаватор погрузчик",
        "jcb",
        "джсб"
    ]):
        score += 3

    elif "каток" in text:
        score += 3

    elif any(word in text for word in [
        "мини-погрузчик",
        "мини погрузчик",
        "минипогрузчик",
        "bobcat",
        "бобкат"
    ]):
        score += 2

    if any(word in text for word in [
        "асфальтная крошка",
        "асфальтовая крошка",
        "асфальтный скол",
        "бой бетона",
        "бой бетонный",
        "щебень",
        "песок"
    ]):
        score += 2

    if any(city in text for city in [
        "люберцы",
        "люберцах",
        "лыткарино"
    ]):
        score += 1

    
    return min(score, 10)
    


# Явный мусор / объявления
exclude_words = [
    "продам",
    "продаю",
    "продается",
    "продаётся",
    "вакансия",
    "ищу работу",
    "ищет работу",
    "машинист ищет работу",
    "водитель ищет работу",
    "резюме",
]


# =========================
# ПОИСК ТЕЛЕФОНА
# =========================

phone_pattern = re.compile(
    r"""
    (?:
        (?:\+7|8)
        [\s\-\(\)]*
        \d{3}
        [\s\-\(\)]*
        \d{3}
        [\s\-]*
        \d{2}
        [\s\-]*
        \d{2}
    )
    """,
    re.VERBOSE
)


def find_phone(text):
    match = phone_pattern.search(text)

    if not match:
        return None

    phone = match.group(0)

    # Оставляем только цифры
    digits = re.sub(r"\D", "", phone)

    # 8XXXXXXXXXX -> 7XXXXXXXXXX
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) != 11 or not digits.startswith("7"):
        return None

    return "+" + digits


# =========================
# ОТПРАВКА В БОТА
# =========================

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


# =========================
# МОНИТОРИНГ TELEGRAM
# =========================

@client.on(events.NewMessage)
async def handler(event):

    text = (event.message.message or "").strip()

    if not text:
        return

    text_lower = text.lower()


    # 1. Отсекаем рекламу и вакансии
    if any(word in text_lower for word in exclude_words):
        return


    # 2. В сообщении обязательно должна быть спецтехника
    equipment_found = [
        word for word in equipment_words
        if word in text_lower
    ]

    if not equipment_found:
        return


    # 3. Должен быть признак заявки
    request_found = [
        word for word in request_words
        if word in text_lower
    ]

    if not request_found:
        return
    score = calculate_score(
        text_lower,
        equipment_found,
        location_found
)


    # 4. Обязательно наша география
    location_found = [
        location for location in locations
        if location in text_lower
    ]

    if not location_found:
        return
    score = calculate_score(
        text_lower,
        equipment_found,
        location_found
    )

    # 5. ОБЯЗАТЕЛЬНО телефон
    phone = find_phone(text)

    if not phone:
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


        # Ссылка на оригинальное сообщение
        message_link = ""

        chat_username = getattr(chat, "username", None)

        if chat_username:
            message_link = (
                f"\n\n🔗 Открыть заявку:\n"
                f"https://t.me/{chat_username}/{event.message.id}"
            )


        alert = (
                    f"🔥 ПРИОРИТЕТ: {score}/10\n\n"
            "🔥 ГОРЯЧАЯ ЗАЯВКА\n\n"

            f"📍 Район: {', '.join(location_found)}\n"
            f"🚜 Техника: {', '.join(equipment_found)}\n\n"

            f"📞 ТЕЛЕФОН:\n"
            f"{phone}\n\n"

            f"💬 Заявка:\n"
            f"{text}\n\n"

            f"👤 Автор: {sender_name}\n"
            f"📢 Группа: {chat_name}"

            f"{message_link}"
        )


        send_to_bot(alert)

        print(
            f"Отправлена заявка: {phone} / {location_found}",
            flush=True
        )


    except Exception as error:

        print(
            "Ошибка обработки сообщения:",
            error,
            flush=True
        )


print("Монитор заявок запущен", flush=True)

client.start()
client.run_until_disconnected()
