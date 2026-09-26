import os
import re
import html
import asyncio
import urllib.parse
import urllib.request

from telethon import TelegramClient, events
from telethon.sessions import StringSession


# ============================================================
# НАСТРОЙКИ RAILWAY
# ============================================================

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
session = os.getenv("TELEGRAM_SESSION", "").strip()

bot_token = os.getenv("BOT_TOKEN", "").strip()
bot_chat_id = os.getenv("BOT_CHAT_ID", "").strip()

if not session:
    raise RuntimeError("TELEGRAM_SESSION пустая")

if not bot_token:
    raise RuntimeError("BOT_TOKEN пустой")

if not bot_chat_id:
    raise RuntimeError("BOT_CHAT_ID пустой")


client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)


# ============================================================
# ГЕОГРАФИЯ
# ============================================================

locations = [
    # Москва
    "москва",
    "ювао",
    "юго-восточный административный округ",
    "лефортово",
    "нижегородский",
    "рязанский",
    "кузьминки",
    "выхино",
    "жулебино",
    "люблино",
    "марьино",
    "печатники",
    "южнопортовый",
    "капотня",
    "некрасовка",

    # Московская область
    "люберцы",
    "люберцах",
    "люберец",
    "котельники",
    "дзержинский",
    "лыткарино",
    "красково",
    "малаховка",
    "томилино",
    "октябрьский",
    "быково",
    "раменское",
    "раменский",
    "жуковский",
    "островцы",
    "софьино",
    "бронницы",
    "марусино",
]


# ============================================================
# СПЕЦТЕХНИКА И РАБОТЫ
# ============================================================

equipment_words = [
    # Экскаваторы / погрузчики
    "экскаватор-погрузчик",
    "экскаватор погрузчик",
    "экскаватор",
    "погрузчик",
    "мини-погрузчик",
    "мини погрузчик",
    "минипогрузчик",

    # Самосвалы
    "самосвал",
    "самосвалы",

    # Другая техника
    "бобкэт",
    "bobcat",
    "jcb",
    "джсб",
    "каток",
    "виброкаток",
    "бульдозер",
    "манипулятор",
    "автокран",
    "кран",
    "трактор",
    "грейдер",

    # Работы
    "копать",
    "копка",
    "котлован",
    "траншея",
    "планировка",
    "вывоз грунта",
    "вывоз земли",
    "земляные работы",
    "дорожные работы",
    "асфальтирование",

    # Снег
    "вывоз снега",
    "уборка снега",
    "убрать снег",
    "расчистка снега",
    "расчистить снег",
    "очистка снега",
    "погрузка снега",
    "загрузить снег",
    "снег вывоз",
    "уборка территории от снега",
    "очистка территории от снега",
]


# ============================================================
# МАТЕРИАЛЫ
# ============================================================

material_words = [
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
    "асфальтная крошка",
    "асфальтовая крошка",
    "асфальтный скол",
    "бой бетона",
    "бетонный бой",
]


# ============================================================
# СЛОВА, ПОКАЗЫВАЮЩИЕ ЧТО ЧЕЛОВЕК ИЩЕТ
# ============================================================

request_words = [
    "нужен",
    "нужна",
    "нужно",
    "нужны",
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
    "нужна техника",
    "нужен материал",
    "нужны материалы",
    "нужна доставка",
    "кто привезет",
    "кто привезёт",
    "кто привезти",
    "купим",
    "закупаем",
    "требуется техника",
    "требуется самосвал",
    "требуется экскаватор",
    "требуется погрузчик",
]


# ============================================================
# РЕКЛАМА / ВАКАНСИИ / ПРЕДЛОЖЕНИЯ
# ============================================================

ad_exclude_words = [
    "помощь диспетчера",
    "по размещению рекламы",
    "размещение рекламы",
    "услуги спецтехники",
    "предлагаемая спецтехника",
    "предлагаем спецтехнику",
    "сдам в аренду",
    "сдаю в аренду",
    "сдать в аренду",
    "наша техника",
    "наш автопарк",
    "техника в наличии",
    "свободная техника",
    "свободен экскаватор",
    "свободен погрузчик",
    "есть свободная техника",
    "работаем по москве",
    "работаем в области",
    "предоставление техники",
    "предоставляем технику",
    "оказываем услуги",
    "аренда спецтехники",
    "сдам спецтехнику",
    "сдается техника",
    "сдаётся техника",

    # вакансии
    "вакансия",
    "ищу работу",
    "ищет работу",
    "машинист ищет работу",
    "водитель ищет работу",
    "резюме",
    "требуется машинист",
    "требуется водитель",
    "требуются рабочие",
    "требуется рабочий",
    "требуются сотрудники",
    "требуется сотрудник",
    "ищется рабочий",
    "ищем сотрудника",
    "набор рабочих",
    "набор сотрудников",
    "гражданство:",
    "оплата:",
    "график:",
    "фото паспорта",
]


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def contains_word(text, word):
    """
    Для одиночных слов используем границы слова.
    Это предотвращает, например:
    'грунт' -> 'грунтовка'.
    """
    text = text.lower()
    word = word.lower()

    if " " in word or "-" in word:
        return word in text

    pattern = r"(?<!\w)" + re.escape(word) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def find_matches(text, words):
    found = []

    for word in words:
        if contains_word(text, word):
            found.append(word)

    return found


def find_location(text):
    text_lower = text.lower()

    found = []
    for place in locations:
        if place in text_lower:
            found.append(place)

    return found


def find_phone(text):
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

    match = phone_pattern.search(text)

    if not match:
        return None

    phone = match.group(0)
    digits = re.sub(r"\D", "", phone)

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) != 11 or not digits.startswith("7"):
        return None

    return "+" + digits


def calculate_score(text, equipment_found, location_found):
    score = 1

    urgent_words = [
        "срочно",
        "сегодня",
        "прямо сейчас",
        "в течение часов",
        "на сейчас",
    ]

    tomorrow_words = [
        "завтра",
        "на завтра",
        "утром",
    ]

    if any(word in text for word in urgent_words):
        score += 3

    elif any(word in text for word in tomorrow_words):
        score += 2

    if any(
        word in text
        for word in [
            "экскаватор-погрузчик",
            "экскаватор погрузчик",
            "jcb",
            "джсб",
        ]
    ):
        score += 3

    elif any(
        word in text
        for word in [
            "мини-погрузчик",
            "мини погрузчик",
            "минипогрузчик",
            "бобкэт",
            "bobcat",
            "каток",
            "самосвал",
        ]
    ):
        score += 2

    if any(
        word in text
        for word in [
            "асфальтная крошка",
            "асфальтовая крошка",
            "асфальтный скол",
            "бой бетона",
            "бетонный бой",
            "щебень",
            "песок",
        ]
    ):
        score += 2

    if location_found:
        score += 1

    if equipment_found:
        score += 1

    return min(score, 10)


# ============================================================
# ОТПРАВКА В TELEGRAM-БОТА
# ============================================================

def send_to_bot(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": bot_chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = response.read().decode("utf-8")

        print("✅ УВЕДОМЛЕНИЕ ОТПРАВЛЕНО В БОТА", flush=True)
        return result

    except Exception as e:
        print(
            f"❌ ОШИБКА ОТПРАВКИ В БОТА: {repr(e)}",
            flush=True
        )
        return None


# ============================================================
# МОНИТОРИНГ TELEGRAM
# ============================================================

seen_leads = set()


@client.on(events.NewMessage)
async def handler(event):

    # --------------------------------------------------------
    # ВАЖНО: диагностический вывод ДО ВСЕХ фильтров
    # --------------------------------------------------------

    text = event.raw_text or ""

    try:
        chat = await event.get_chat()
        chat_name = (
            getattr(chat, "title", None)
            or getattr(chat, "username", None)
            or str(event.chat_id)
        )
    except Exception:
        chat = None
        chat_name = str(event.chat_id)

    print("", flush=True)
    print("=" * 70, flush=True)
    print("📩 ПОЛУЧЕНО НОВОЕ СООБЩЕНИЕ TELEGRAM", flush=True)
    print(f"ГРУППА: {chat_name}", flush=True)
    print(f"CHAT_ID: {event.chat_id}", flush=True)
    print(f"ТЕКСТ: {text[:1000]}", flush=True)
    print("=" * 70, flush=True)

    if not text.strip():
        print("REJECT: пустое сообщение", flush=True)
        return

    text_lower = text.lower().strip()

    # --------------------------------------------------------
    # Получаем отправителя
    # --------------------------------------------------------

    try:
        sender = await event.get_sender()
    except Exception:
        sender = None

    sender_username = getattr(sender, "username", None)
    sender_first_name = getattr(sender, "first_name", None)
    sender_last_name = getattr(sender, "last_name", None)

    sender_name = " ".join(
        part
        for part in [sender_first_name, sender_last_name]
        if part
    ).strip()

    # --------------------------------------------------------
    # Игнорируем собственного бота
    # --------------------------------------------------------

    if sender_username and sender_username.lower() == "spec_clients_bot":
        print(
            "REJECT: сообщение собственного бота",
            flush=True
        )
        return

    # --------------------------------------------------------
    # Отсеиваем вакансии и рекламу
    # --------------------------------------------------------

    found_ad_words = find_matches(
        text_lower,
        ad_exclude_words
    )

    if found_ad_words:
        print(
            "REJECT: реклама/вакансия:",
            found_ad_words,
            flush=True
        )
        return

    # --------------------------------------------------------
    # Ищем технику / работы / материалы
    # --------------------------------------------------------

    equipment_found = find_matches(
        text_lower,
        equipment_words
    )

    material_found = find_matches(
        text_lower,
        material_words
    )

    if not equipment_found and not material_found:
        print(
            "REJECT: нет нашей техники/работ/материалов",
            flush=True
        )
        return

    # --------------------------------------------------------
    # Проверяем намерение заказать
    # --------------------------------------------------------

    request_found = find_matches(
        text_lower,
        request_words
    )

    if not request_found:
        print(
            "REJECT: нет признака запроса клиента",
            flush=True
        )
        return

    # --------------------------------------------------------
    # География
    # --------------------------------------------------------

    location_found = find_location(text_lower)

    if not location_found:
        print(
            "REJECT: не найден наш район",
            flush=True
        )
        return

    # --------------------------------------------------------
    # Телефон
    # --------------------------------------------------------

    phone = find_phone(text)

    # --------------------------------------------------------
    # Защита от повторов
    # --------------------------------------------------------

    lead_key = (
        event.chat_id,
        event.id
    )

    if lead_key in seen_leads:
        print(
            "REJECT: сообщение уже обработано",
            flush=True
        )
        return

    seen_leads.add(lead_key)

    # --------------------------------------------------------
    # Оценка
    # --------------------------------------------------------

    score = calculate_score(
        text_lower,
        equipment_found,
        location_found
    )

    if score >= 7:
        temperature = "🔥 ГОРЯЧАЯ ЗАЯВКА"
    elif score >= 4:
        temperature = "🟠 ХОРОШАЯ ЗАЯВКА"
    else:
        temperature = "🟡 НОВАЯ ЗАЯВКА"

    # --------------------------------------------------------
    # Ссылка на сообщение
    # --------------------------------------------------------

    message_link = None

    chat_username = getattr(
        chat,
        "username",
        None
    ) if chat else None

    if chat_username:
        message_link = (
            f"https://t.me/{chat_username}/{event.id}"
        )

    # --------------------------------------------------------
    # Контакт отправителя
    # --------------------------------------------------------

    sender_contact = ""

    if sender_username:
        sender_contact = (
            f"\n👤 Telegram: @{html.escape(sender_username)}"
        )

    elif sender_name:
        sender_contact = (
            f"\n👤 Отправитель: {html.escape(sender_name)}"
        )

    # --------------------------------------------------------
    # Формируем сообщение
    # --------------------------------------------------------

    categories = equipment_found + material_found

    categories_text = ", ".join(
        dict.fromkeys(categories)
    )

    location_text = ", ".join(
        dict.fromkeys(location_found)
    )

    phone_text = (
        html.escape(phone)
        if phone
        else "в сообщении не указан"
    )

    safe_text = html.escape(text[:2500])
    safe_chat = html.escape(str(chat_name))

    notification = (
        f"{temperature}\n\n"
        f"⭐ Оценка: <b>{score}/10</b>\n"
        f"📍 Район: <b>{html.escape(location_text)}</b>\n"
        f"🚜 Найдено: <b>{html.escape(categories_text)}</b>\n"
        f"📞 Телефон: <b>{phone_text}</b>\n"
        f"💬 Группа: <b>{safe_chat}</b>"
        f"{sender_contact}\n\n"
        f"📝 <b>Сообщение:</b>\n"
        f"{safe_text}"
    )

    if message_link:
        notification += (
            f'\n\n🔗 <a href="{message_link}">'
            f"Открыть сообщение"
            f"</a>"
        )

    print(
        "✅ ПОДХОДЯЩАЯ ЗАЯВКА",
        flush=True
    )
    print(
        f"Оценка: {score}/10",
        flush=True
    )

    send_to_bot(notification)


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    print("", flush=True)
    print("=" * 70, flush=True)
    print("🚀 МОНИТОР ЗАЯВОК ЗАПУСКАЕТСЯ", flush=True)
    print("=" * 70, flush=True)

    await client.start()

    me = await client.get_me()

    print(
        f"✅ TELEGRAM АВТОРИЗОВАН: "
        f"{getattr(me, 'first_name', '')} "
        f"@{getattr(me, 'username', '')}",
        flush=True
    )

    # --------------------------------------------------------
    # Показываем, какие группы реально видит аккаунт
    # --------------------------------------------------------

    print("", flush=True)
    print(
        "📋 ПРОВЕРЯЕМ ДОСТУПНЫЕ TELEGRAM-ДИАЛОГИ...",
        flush=True
    )

    group_count = 0

    async for dialog in client.iter_dialogs():

        if dialog.is_group or dialog.is_channel:
            group_count += 1

            print(
                f"GROUP {group_count}: "
                f"{dialog.name} | "
                f"ID: {dialog.id}",
                flush=True
            )

    print("", flush=True)
    print(
        f"✅ ВСЕГО ВИДНО ГРУПП/КАНАЛОВ: {group_count}",
        flush=True
    )

    print(
        "👂 ЖДУ НОВЫЕ СООБЩЕНИЯ...",
        flush=True
    )
    print("=" * 70, flush=True)

    # Тестируем отправку в нашего бота
    send_to_bot(
        "✅ <b>Монитор спецтехники запущен</b>\n\n"
        f"Telegram подключён.\n"
        f"Видно групп/каналов: <b>{group_count}</b>\n"
        f"Монитор ждёт новые сообщения."
    )

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "Монитор остановлен пользователем",
            flush=True
        )

    except Exception as e:
        print(
            f"❌ КРИТИЧЕСКАЯ ОШИБКА: {repr(e)}",
            flush=True
        )
        raise
