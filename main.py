import os
import re
import asyncio
import urllib.parse
import urllib.request
import urllib.error

from telethon import TelegramClient, events
from telethon.sessions import StringSession


# ============================================================
# НАСТРОЙКИ
# ============================================================

api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
session = os.getenv("TELEGRAM_SESSION", "").strip()

bot_token = os.getenv("BOT_TOKEN", "").strip()
bot_chat_id = os.getenv("BOT_CHAT_ID", "").strip()


if not api_id:
    raise RuntimeError("TELEGRAM_API_ID не указан")

if not api_hash:
    raise RuntimeError("TELEGRAM_API_HASH не указан")

if not session:
    raise RuntimeError("TELEGRAM_SESSION не указана")

if not bot_token:
    raise RuntimeError("BOT_TOKEN не указан")

if not bot_chat_id:
    raise RuntimeError("BOT_CHAT_ID не указан")


client = TelegramClient(
    StringSession(session),
    api_id,
    api_hash
)


# ============================================================
# ГЕОГРАФИЯ
# ============================================================

locations = [

    # Москва / ЮВАО
    "москва",
    "ювао",
    "юго-восточный административный округ",

    "лефортово",
    "нижегородский",
    "рязанский",
    "текстильщики",
    "кузьминки",
    "выхино",
    "жулебино",
    "выхино-жулебино",
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
    "котельниках",

    "дзержинский",
    "дзержинском",

    "островцы",
    "островцах",

    "бронницы",
    "бронницах",

    "софьино",

    "лыткарино",

    "томилино",

    "красково",

    "марусино",

    "малаховка",

    "октябрьский",

    "быково",

    "раменское",
    "раменском",
    "раменский",

    "жуковский",
    "жуковском",
]


# ============================================================
# СПЕЦТЕХНИКА / РАБОТЫ
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

    "бобкэт",
    "бобкат",
    "bobcat",

    "jcb",
    "джсб",

    # Самосвалы
    "самосвал",
    "самосвалы",
    "самосвала",
    "самосвалов",

    # Другая техника
    "каток",
    "виброкаток",
    "бульдозер",
    "манипулятор",
    "автокран",
    "трактор",
    "грейдер",

    # Земляные работы
    "копать",
    "копка",
    "котлован",
    "траншея",
    "планировка",
    "вывоз грунта",
    "вывоз земли",
    "земляные работы",

    # Дороги / асфальт
    "дорожные работы",
    "асфальтирование",
    "укладка асфальта",
    "ямочный ремонт",

    # ========================================================
    # СНЕГ
    # ========================================================

    "вывоз снега",
    "вывезти снег",
    "вывезти снега",
    "вывести снег",

    "уборка снега",
    "убрать снег",
    "убрать снега",

    "очистка снега",
    "очистить снег",

    "очистка от снега",
    "очистить от снега",

    "очистка территории от снега",
    "очистка дорог от снега",
    "очистка парковки от снега",

    "расчистка снега",
    "расчистить снег",
    "расчистка от снега",

    "погрузка снега",
    "погрузить снег",

    "погрузка и вывоз снега",
    "уборка и вывоз снега",

    "механизированная уборка снега",
    "механизированная очистка снега",

    "снегоуборка",
    "снегоуборочные работы",

    "снег вывоз",
]


# ============================================================
# МАТЕРИАЛЫ
# ============================================================

material_words = [

    # Песок
    "песок",
    "песка",

    # Щебень
    "щебень",
    "щебня",

    # Грунт
    "грунт",
    "грунта",

    # Чернозём
    "чернозем",
    "чернозём",

    # ПГС
    "пгс",
    "опгс",

    # ========================================================
    # АСФАЛЬТНЫЙ СКОЛ / КРОШКА
    # ========================================================

    "асфальтный скол",
    "асфальтного скола",
    "асфальтовый скол",

    "асфальтная крошка",
    "асфальтовая крошка",
    "асфальтной крошки",
    "асфальтовой крошки",

    "асфальтовый лом",
    "лом асфальта",

    # Бетон
    "бой бетона",
    "бетонный бой",
    "бой бетонный",
]


# ============================================================
# СЛОВА, КОТОРЫЕ ПОКАЗЫВАЮТ, ЧТО ЧЕЛОВЕК ИЩЕТ / ПОКУПАЕТ
# ============================================================

request_words = [

    # Нужно
    "нужен",
    "нужна",
    "нужно",
    "нужны",

    "необходим",
    "необходима",
    "необходимо",
    "необходимы",

    "требуется",
    "требуются",

    # Ищут
    "ищу",
    "ищем",
    "ищет",
    "ищут",

    "кто может",
    "кто сможет",
    "кто есть",
    "есть кто",

    # Аренда
    "возьму в аренду",
    "возьмем в аренду",
    "возьмём в аренду",
    "арендовать",
    "аренда",

    "нужна техника",
    "нужна спецтехника",

    # Материалы
    "нужен материал",
    "нужны материалы",
    "нужен материал",
    "нужна доставка",

    # ========================================================
    # ПОКУПКА
    # ========================================================

    "купить",
    "куплю",
    "купим",

    "хочу купить",
    "хотим купить",
    "хотят купить",

    "нужно купить",
    "надо купить",

    "приобрести",
    "хочу приобрести",
    "хотим приобрести",

    "закупаем",
    "закупаем материал",
    "закупаем материалы",

    "заказать",
    "хочу заказать",
    "хотим заказать",
    "нужно заказать",

    # Доставка
    "кто привезет",
    "кто привезёт",
    "кто доставит",
    "привезти",
    "доставить",
]


# ============================================================
# РЕКЛАМА / ПРЕДЛОЖЕНИЯ / ВАКАНСИИ
# ============================================================

ad_exclude_words = [

    # Реклама
    "помощь диспетчера",
    "по размещению рекламы",
    "размещение рекламы",

    # Предлагают технику
    "услуги спецтехники",
    "предлагаем спецтехнику",
    "предлагаю спецтехнику",

    "сдам в аренду",
    "сдаю в аренду",
    "сдаем в аренду",
    "сдаём в аренду",

    "сдам спецтехнику",
    "сдается техника",
    "сдаётся техника",

    "наша техника",
    "наш автопарк",

    "техника в наличии",
    "в наличии техника",

    "свободная техника",
    "свободна техника",

    "свободен экскаватор",
    "свободен погрузчик",
    "свободен самосвал",

    "есть свободная техника",

    "готовы выехать",

    "предоставим технику",
    "предоставляем технику",

    "оказываем услуги",

    "аренда спецтехники от",
    "предлагаем аренду",

    # Вакансии
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

    "гражданство:",
    "фото паспорта",
    "ежедневная оплата",
]


# ============================================================
# ДОПОЛНИТЕЛЬНЫЙ МУСОР
# ============================================================

exclude_words = [
    "продам",
    "продаю",
    "продается",
    "продаётся",

    "вакансия",
    "ищу работу",
    "ищет работу",
    "резюме",
]


# ============================================================
# ПОИСК СЛОВ БЕЗ ЛОЖНЫХ СОВПАДЕНИЙ
# ============================================================

def contains_word(text, word):

    text = text.lower()
    word = word.lower()

    # Фразы ищем обычным совпадением
    if " " in word or "-" in word:
        return word in text

    # Одиночные слова ищем по границам слова
    # Например:
    # грунт -> грунт
    # но НЕ грунтовка

    pattern = (
        r"(?<!\w)"
        + re.escape(word)
        + r"(?!\w)"
    )

    return (
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        is not None
    )


def find_matches(text, words):

    found = []

    for word in words:

        if contains_word(
            text,
            word
        ):
            found.append(
                word
            )

    return list(
        dict.fromkeys(found)
    )


# ============================================================
# ПОИСК ГЕОГРАФИИ
# ============================================================

def find_locations(text):

    text = text.lower()

    found = []

    for location in locations:

        if location in text:
            found.append(
                location
            )

    return list(
        dict.fromkeys(found)
    )


# ============================================================
# ПОИСК ТЕЛЕФОНА
# ============================================================

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

    match = phone_pattern.search(
        text
    )

    if not match:
        return None

    phone = match.group(0)

    digits = re.sub(
        r"\D",
        "",
        phone
    )

    # 8XXXXXXXXXX -> 7XXXXXXXXXX
    if (
        len(digits) == 11
        and digits.startswith("8")
    ):
        digits = (
            "7"
            + digits[1:]
        )

    if (
        len(digits) != 11
        or not digits.startswith("7")
    ):
        return None

    return "+" + digits


# ============================================================
# ОЦЕНКА ЗАЯВКИ
# ============================================================

def calculate_score(
    text,
    equipment_found,
    material_found,
    location_found
):

    score = 1

    # Срочность
    if any(
        word in text
        for word in [
            "срочно",
            "сегодня",
            "прямо сейчас",
            "на сейчас",
            "в течение часа",
        ]
    ):
        score += 3

    elif any(
        word in text
        for word in [
            "завтра",
            "на завтра",
            "утром",
        ]
    ):
        score += 2

    # Основная техника
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
            "bobcat",
            "бобкэт",
            "бобкат",
            "самосвал",
        ]
    ):
        score += 2

    # Снег
    if any(
        word in text
        for word in [
            "вывоз снега",
            "уборка снега",
            "очистка снега",
            "очистка от снега",
            "погрузка снега",
            "расчистка снега",
        ]
    ):
        score += 2

    # Материалы
    if any(
        word in text
        for word in [
            "асфальтный скол",
            "асфальтовый скол",
            "асфальтная крошка",
            "асфальтовая крошка",
            "бой бетона",
            "бетонный бой",
            "щебень",
            "песок",
        ]
    ):
        score += 2

    # Есть район
    if location_found:
        score += 1

    # Есть техника/работа
    if equipment_found:
        score += 1

    # Есть материал
    if material_found:
        score += 1

    return min(
        score,
        10
    )


# ============================================================
# ОТПРАВКА В TELEGRAM-БОТА
# ============================================================

def send_bot_part(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{bot_token}/sendMessage"
    )

    data = urllib.parse.urlencode({
        "chat_id": bot_chat_id,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            result = (
                response
                .read()
                .decode("utf-8")
            )

        print(
            "✅ Telegram: сообщение отправлено",
            flush=True
        )

        return True

    except urllib.error.HTTPError as error:

        try:
            body = (
                error
                .read()
                .decode("utf-8")
            )
        except Exception:
            body = ""

        print(
            "❌ TELEGRAM HTTP ERROR:",
            error.code,
            body,
            flush=True
        )

        return False

    except Exception as error:

        print(
            "❌ TELEGRAM ERROR:",
            repr(error),
            flush=True
        )

        return False


def split_message(text, max_length=3800):

    if len(text) <= max_length:
        return [text]

    parts = []

    remaining = text

    while remaining:

        if len(remaining) <= max_length:

            parts.append(
                remaining
            )

            break

        cut = remaining.rfind(
            "\n",
            0,
            max_length
        )

        if cut < 1000:
            cut = max_length

        parts.append(
            remaining[:cut]
        )

        remaining = (
            remaining[cut:]
            .lstrip()
        )

    return parts


def send_to_bot(message):

    parts = split_message(
        message
    )

    for index, part in enumerate(
        parts,
        start=1
    ):

        if len(parts) > 1:

            part = (
                f"Часть {index}/{len(parts)}\n\n"
                + part
            )

        success = send_bot_part(
            part
        )

        if not success:
            return False

    return True


# ============================================================
# УЖЕ ОБРАБОТАННЫЕ СООБЩЕНИЯ
# ============================================================

seen_messages = set()


# ============================================================
# ОБРАБОТЧИК TELEGRAM
# ============================================================

@client.on(events.NewMessage)
async def handler(event):

    try:

        text = (
            event.raw_text
            or ""
        ).strip()

        # ====================================================
        # ПЕЧАТАЕМ ПОЛНОСТЬЮ В RAILWAY
        # ====================================================

        print(
            "\n"
            + "=" * 70,
            flush=True
        )

        print(
            "📩 НОВОЕ СООБЩЕНИЕ",
            flush=True
        )

        print(
            "CHAT ID:",
            event.chat_id,
            flush=True
        )

        print(
            "MESSAGE ID:",
            event.id,
            flush=True
        )

        print(
            "ПОЛНЫЙ ТЕКСТ:",
            text,
            flush=True
        )

        print(
            "=" * 70,
            flush=True
        )

        if not text:

            print(
                "REJECT: пустое сообщение",
                flush=True
            )

            return

        text_lower = (
            text
            .lower()
        )

        # ====================================================
        # ЧАТ / ГРУППА
        # ====================================================

        try:

            chat = await event.get_chat()

        except Exception:

            chat = None

        chat_name = (
            getattr(
                chat,
                "title",
                None
            )
            or getattr(
                chat,
                "username",
                None
            )
            or "Личный чат"
        )

        chat_name_lower = (
            str(chat_name)
            .lower()
        )

        print(
            "ГРУППА:",
            chat_name,
            flush=True
        )

        # ====================================================
        # ОТПРАВИТЕЛЬ
        # ====================================================

        try:

            sender = await event.get_sender()

        except Exception:

            sender = None

        username = getattr(
            sender,
            "username",
            None
        )

        first_name = getattr(
            sender,
            "first_name",
            None
        )

        last_name = getattr(
            sender,
            "last_name",
            None
        )

        # Наш бот не анализируем
        if (
            username
            and username.lower()
            == "spec_clients_bot"
        ):

            print(
                "REJECT: собственный бот",
                flush=True
            )

            return

        # ====================================================
        # ДУБЛИКАТ ПО MESSAGE ID
        # ====================================================

        message_key = (
            event.chat_id,
            event.id
        )

        if message_key in seen_messages:

            print(
                "REJECT: duplicate",
                flush=True
            )

            return

        # ====================================================
        # РЕКЛАМА / ВАКАНСИЯ
        # ====================================================

        ad_found = find_matches(
            text_lower,
            ad_exclude_words
            + exclude_words
        )

        if ad_found:

            print(
                "REJECT: реклама/вакансия:",
                ad_found,
                flush=True
            )

            return

        # ====================================================
        # ТЕХНИКА / РАБОТЫ
        # ====================================================

        equipment_found = find_matches(
            text_lower,
            equipment_words
        )

        # Если нашли точное название,
        # убираем более общие дубли

        if (
            "экскаватор-погрузчик"
            in equipment_found
        ):

            equipment_found = [
                item
                for item
                in equipment_found
                if item not in [
                    "экскаватор",
                    "погрузчик",
                    "экскаватор погрузчик",
                ]
            ]

        elif (
            "экскаватор погрузчик"
            in equipment_found
        ):

            equipment_found = [
                item
                for item
                in equipment_found
                if item not in [
                    "экскаватор",
                    "погрузчик",
                ]
            ]

        if (
            "мини-погрузчик"
            in equipment_found
        ):

            equipment_found = [
                item
                for item
                in equipment_found
                if item not in [
                    "погрузчик",
                    "мини погрузчик",
                    "минипогрузчик",
                ]
            ]

        # ====================================================
        # МАТЕРИАЛЫ
        # ====================================================

        material_found = find_matches(
            text_lower,
            material_words
        )

        print(
            "Техника/работы:",
            equipment_found,
            flush=True
        )

        print(
            "Материалы:",
            material_found,
            flush=True
        )

        if (
            not equipment_found
            and not material_found
        ):

            print(
                "REJECT: нет нашей техники/работ/материала",
                flush=True
            )

            return

        # ====================================================
        # ПРИЗНАК ЗАЯВКИ
        # ====================================================

        request_found = find_matches(
            text_lower,
            request_words
        )

        print(
            "Признак заявки:",
            request_found,
            flush=True
        )

        if not request_found:

            print(
                "REJECT: нет признака заявки",
                flush=True
            )

            return

        # ====================================================
        # ГЕОГРАФИЯ
        #
        # ИЩЕМ И В ТЕКСТЕ, И В НАЗВАНИИ ГРУППЫ
        # ====================================================

        geo_text = (
            text_lower
            + " "
            + chat_name_lower
        )

        location_found = find_locations(
            geo_text
        )

        print(
            "География:",
            location_found,
            flush=True
        )

        if not location_found:

            print(
                "REJECT: не наша география",
                flush=True
            )

            return

        # ====================================================
        # ТЕЛЕФОН ОБЯЗАТЕЛЕН
        # ====================================================

        phone = find_phone(
            text
        )

        if not phone:

            print(
                "REJECT: НЕТ ТЕЛЕФОНА",
                flush=True
            )

            return

        print(
            "Телефон:",
            phone,
            flush=True
        )

        # ====================================================
        # ОЦЕНКА
        # ====================================================

        score = calculate_score(
            text_lower,
            equipment_found,
            material_found,
            location_found
        )

        if score >= 7:

            priority = (
                "🔥 ГОРЯЧАЯ ЗАЯВКА"
            )

        elif score >= 4:

            priority = (
                "🟠 ХОРОШАЯ ЗАЯВКА"
            )

        else:

            priority = (
                "🟡 НОВАЯ ЗАЯВКА"
            )

        # ====================================================
        # АВТОР
        # ====================================================

        if username:

            sender_name = (
                "@"
                + username
            )

        else:

            sender_name = " ".join(
                part
                for part in [
                    first_name,
                    last_name,
                ]
                if part
            ).strip()

            if not sender_name:
                sender_name = (
                    "Не указан"
                )

        # ====================================================
        # ССЫЛКА НА ОРИГИНАЛЬНОЕ СООБЩЕНИЕ
        # ====================================================

        message_link = ""

        chat_username = getattr(
            chat,
            "username",
            None
        )

        if chat_username:

            message_link = (
                "https://t.me/"
                f"{chat_username}/"
                f"{event.id}"
            )

        # ====================================================
        # ФОРМИРУЕМ БОТА
        # ====================================================

        equipment_line = ""

        if equipment_found:

            equipment_line = (
                "🚜 Техника / работы: "
                + ", ".join(
                    equipment_found
                )
                + "\n"
            )

        material_line = ""

        if material_found:

            material_line = (
                "🧱 Материал: "
                + ", ".join(
                    material_found
                )
                + "\n"
            )

        geo_line = ", ".join(
            location_found
        )

        alert = (
            f"{priority}\n"
            f"⭐ Приоритет: {score}/10\n\n"

            f"{equipment_line}"
            f"{material_line}"

            f"📍 Район: {geo_line}\n"
            f"📞 ТЕЛЕФОН: {phone}\n\n"

            f"💬 ПОЛНЫЙ ТЕКСТ ЗАЯВКИ:\n"
            f"{text}\n\n"

            f"👤 Автор: {sender_name}\n"
            f"📢 Группа: {chat_name}"
        )

        if message_link:

            alert += (
                "\n\n"
                "🔗 Открыть оригинал:\n"
                f"{message_link}"
            )

        # ====================================================
        # ОТПРАВКА
        # ====================================================

        print(
            "✅ ЗАЯВКА ПРОШЛА ВСЕ ФИЛЬТРЫ",
            flush=True
        )

        sent = send_to_bot(
            alert
        )

        if sent:

            seen_messages.add(
                message_key
            )

            print(
                "✅ ЗАЯВКА УШЛА В TELEGRAM-БОТА",
                flush=True
            )

        else:

            print(
                "❌ ЗАЯВКА НАЙДЕНА, НО TELEGRAM НЕ ПРИНЯЛ СООБЩЕНИЕ",
                flush=True
            )

    except Exception as error:

        print(
            "❌ ОШИБКА ОБРАБОТКИ:",
            repr(error),
            flush=True
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    print(
        "\n"
        + "=" * 70,
        flush=True
    )

    print(
        "🚀 МОНИТОР ЗАЯВОК ЗАПУСКАЕТСЯ",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    await client.start()

    me = await client.get_me()

    if getattr(
        me,
        "bot",
        False
    ):

        raise RuntimeError(
            "TELEGRAM_SESSION авторизована как БОТ. "
            "Для мониторинга нужен обычный Telegram-аккаунт."
        )

    print(
        "✅ TELEGRAM АККАУНТ АВТОРИЗОВАН",
        flush=True
    )

    print(
        "Имя:",
        getattr(
            me,
            "first_name",
            ""
        ),
        flush=True
    )

    print(
        "Username:",
        getattr(
            me,
            "username",
            ""
        ),
        flush=True
    )

    # ========================================================
    # ПОКАЗЫВАЕМ ГРУППЫ
    # ========================================================

    group_count = 0

    print(
        "\n📋 ГРУППЫ / КАНАЛЫ:",
        flush=True
    )

    async for dialog in client.iter_dialogs():

        if (
            dialog.is_group
            or dialog.is_channel
        ):

            group_count += 1

            print(
                f"GROUP {group_count}: "
                f"{dialog.name} | "
                f"ID: {dialog.id}",
                flush=True
            )

    print(
        "\n✅ ВСЕГО ВИДНО ГРУПП/КАНАЛОВ:",
        group_count,
        flush=True
    )

    print(
        "👂 ЖДУ НОВЫЕ СООБЩЕНИЯ...",
        flush=True
    )

    # ========================================================
    # ТЕСТ БОТА ПРИ КАЖДОМ ЗАПУСКЕ
    # ========================================================

    test_message = (
        "✅ МОНИТОР ЗАЯВОК ЗАПУЩЕН\n\n"
        f"Видно групп/каналов: {group_count}\n\n"
        "Фильтр активен:\n"
        "🚜 Спецтехника\n"
        "🧱 Материалы\n"
        "🛣 Асфальтирование\n"
        "❄️ Очистка / уборка / вывоз снега\n\n"
        "📞 Заявки без телефона НЕ отправляются."
    )

    test_sent = send_to_bot(
        test_message
    )

    if test_sent:

        print(
            "✅ ТЕСТОВОЕ СООБЩЕНИЕ В БОТА ОТПРАВЛЕНО",
            flush=True
        )

    else:

        print(
            "❌ ТЕСТОВОЕ СООБЩЕНИЕ В БОТА НЕ УШЛО",
            flush=True
        )

    await client.run_until_disconnected()


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Монитор остановлен.",
            flush=True
        )

    except Exception as error:

        print(
            "❌ КРИТИЧЕСКАЯ ОШИБКА:",
            repr(error),
            flush=True
        )

        raise
