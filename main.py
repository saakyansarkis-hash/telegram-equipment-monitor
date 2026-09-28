import os
import re
import asyncio
import time
import hashlib
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
#
# Москва:
# только ЮВАО.
#
# Московская область:
# только наша ближайшая зона.
#
# Просто "Москва" НЕ считается подходящей географией.
#
# Если адрес явно указан и он чужой -> REJECT.
#
# Если адрес вообще не указан -> заявку НЕ теряем.
# ============================================================

TARGET_GEO_PATTERNS = {

    # --------------------------------------------------------
    # МОСКВА / ЮВАО
    # --------------------------------------------------------

    "ЮВАО": [
        r"\bювао\b",
        r"юго[- ]восточн\w*\s+административн\w*\s+округ\w*",
    ],

    "Лефортово": [
        r"\bлефортов\w*\b",
    ],

    "Нижегородский": [
        r"\bнижегородск\w*\b",
    ],

    "Рязанский": [
        r"\bрязанск\w*\s+проспект\w*\b",
        r"\bрязанск\w*\s+район\w*\b",
        r"\bм\.?\s*рязанский\s+проспект\b",
    ],

    "Текстильщики": [
        r"\bтекстильщик\w*\b",
    ],

    "Кузьминки": [
        r"\bкузьминк\w*\b",
    ],

    "Выхино": [
        r"\bвыхин\w*\b",
    ],

    "Жулебино": [
        r"\bжулебин\w*\b",
    ],

    "Люблино": [
        r"\bлюблин\w*\b",
    ],

    "Марьино": [
        r"\bмарьин\w*\b",
    ],

    "Печатники": [
        r"\bпечатник\w*\b",
    ],

    "Южнопортовый": [
        r"\bюжнопортов\w*\b",
    ],

    "Капотня": [
        r"\bкапотн\w*\b",
    ],

    "Некрасовка": [
        r"\bнекрасовк\w*\b",
    ],


    # --------------------------------------------------------
    # МОСКОВСКАЯ ОБЛАСТЬ
    # --------------------------------------------------------

    "Люберцы": [
        r"\bлюберц\w*\b",
    ],

    "Котельники": [
        r"\bкотельник\w*\b",
    ],

    "Дзержинский": [
        r"\bг\.?\s*дзержинск\w*\b",
        r"\bгород\w*\s+дзержинск\w*\b",
        r"\bг\.?\s*о\.?\s*дзержинск\w*\b",
        r"\bгородск\w*\s+округ\w*\s+дзержинск\w*\b",
        r"\bдзержинский,\s*московск\w*\s+област\w*\b",
    ],

    "Островцы": [
        r"\bостровц\w*\b",
    ],

    "Бронницы": [
        r"\bбронниц\w*\b",
    ],

    "Софьино": [
        r"\bсофьин\w*\b",
    ],

    "Лыткарино": [
        r"\bлыткарин\w*\b",
    ],

    "Томилино": [
        r"\bтомилин\w*\b",
    ],

    "Красково": [
        r"\bкрасков\w*\b",
    ],

    "Марусино": [
        r"\bмарусин\w*\b",
    ],

    "Малаховка": [
        r"\bмалаховк\w*\b",
    ],

    "Октябрьский МО": [
        r"\bоктябрьск\w*\b.{0,40}\bлюбер",
        r"\bлюбер.{0,40}\bоктябрьск\w*\b",
    ],

    "Быково": [
        r"\bбыков\w*\b",
    ],

    "Раменское": [
        r"\bраменск\w*\b",
    ],

    "Жуковский": [
        r"\bг\.?\s*жуковск\w*\b",
        r"\bгород\w*\s+жуковск\w*\b",
        r"\bг\.?\s*о\.?\s*жуковск\w*\b",
        r"\bгородск\w*\s+округ\w*\s+жуковск\w*\b",
        r"\bжуковский,\s*московск\w*\s+област\w*\b",
    ],
}


EXPLICIT_GEO_PATTERNS = [

    r"\bмосква\b",

    r"\bмосковск\w*\s+област\w*\b",

    r"\bг\.?\s*[а-яё-]{3,}",

    r"\bгород\w*\s+[а-яё-]{3,}",

    r"\bобласт\w*\b",

    r"\bрайон\w*\b",

    r"\bр-н\b",

    r"\bметро\s+[а-яё-]{3,}",

    r"\bм\.?\s+[а-яё-]{4,}",

    r"\bул\.?\s+[а-яё-]{3,}",

    r"\bулиц\w*\s+[а-яё-]{3,}",

    r"\bпроспект\w*\b",

    r"\bпр-т\b",

    r"\bшоссе\b",

    r"\bпос\.?\s*[а-яё-]{3,}",

    r"\bпос[её]лок\w*\s+[а-яё-]{3,}",

    r"\bдеревн\w*\s+[а-яё-]{3,}",
]


def analyze_geo(text):

    lower = (
        text
        or ""
    ).lower()

    lower = lower.replace(
        "ё",
        "е"
    )

    found = []

    for label, patterns in TARGET_GEO_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                lower,
                flags=re.IGNORECASE | re.DOTALL
            ):

                found.append(label)

                break

    found = list(
        dict.fromkeys(found)
    )

    if found:

        return (
            "allowed",
            found
        )

    for pattern in EXPLICIT_GEO_PATTERNS:

        if re.search(
            pattern,
            lower,
            flags=re.IGNORECASE
        ):

            return (
                "outside",
                []
            )

    return (
        "unknown",
        []
    )


# ============================================================
# НУЖНАЯ СПЕЦТЕХНИКА / РАБОТЫ
# ============================================================
#
# ОСТАВЛЯЕМ:
#
# Экскаватор-погрузчик
# Мини-погрузчик
# Самосвал
# Каток
#
# УБРАЛИ:
#
# Мини-экскаватор
# Обычный экскаватор
# Манипулятор
# Автокран
# Бульдозер
# Трактор
# Грейдер
# ============================================================

equipment_words = [

    # --------------------------------------------------------
    # ЭКСКАВАТОР-ПОГРУЗЧИК
    # --------------------------------------------------------

    "экскаватор-погрузчик",

    "экскаватор погрузчик",

    "jcb",

    "джсб",


    # --------------------------------------------------------
    # МИНИ-ПОГРУЗЧИК
    # --------------------------------------------------------

    "мини-погрузчик",

    "мини погрузчик",

    "минипогрузчик",

    "бобкэт",

    "бобкат",

    "bobcat",


    # --------------------------------------------------------
    # САМОСВАЛ
    # --------------------------------------------------------

    "самосвал",

    "самосвалы",

    "самосвала",

    "самосвалов",


    # --------------------------------------------------------
    # КАТОК
    # --------------------------------------------------------

    "каток",

    "виброкаток",


    # --------------------------------------------------------
    # ЗЕМЛЯНЫЕ РАБОТЫ
    # --------------------------------------------------------

    "копать",

    "копка",

    "котлован",

    "траншея",

    "планировка",

    "вывоз грунта",

    "вывоз земли",

    "земляные работы",


    # --------------------------------------------------------
    # ДОРОГИ / АСФАЛЬТ
    # --------------------------------------------------------

    "дорожные работы",

    "асфальтирование",

    "укладка асфальта",

    "ямочный ремонт",


    # --------------------------------------------------------
    # СНЕГ
    # --------------------------------------------------------

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
# ЗАПРЕЩЁННАЯ / НЕНУЖНАЯ ТЕХНИКА
# ============================================================
#
# Если такая техника явно указана в заявке,
# сообщение сразу отбрасываем.
# ============================================================

unwanted_equipment_patterns = [

    # Мини-экскаватор

    r"\bмини[\s-]*экскаватор\w*\b",

    r"\bминиэкскаватор\w*\b",


    # Манипулятор

    r"\bманипулятор\w*\b",


    # Автокран

    r"\bавтокран\w*\b",


    # Бульдозер

    r"\bбульдозер\w*\b",


    # Трактор

    r"\bтрактор\w*\b",


    # Грейдер

    r"\bгрейдер\w*\b",
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

    "асфальтный скол",

    "асфальтного скола",

    "асфальтовый скол",

    "асфальтная крошка",

    "асфальтовая крошка",

    "асфальтной крошки",

    "асфальтовой крошки",

    "асфальтовый лом",

    "лом асфальта",

    "асфальтный срез",

    "асфальтовый срез",

    "бой бетона",

    "бетонный бой",

    "бой бетонный",
]


# ============================================================
# ПРИЗНАК ЗАЯВКИ — ОБЯЗАТЕЛЕН
# ============================================================

request_words = [

    "нужен",

    "нужна",

    "нужно",

    "нужны",

    "надо",

    "необходим",

    "необходима",

    "необходимо",

    "необходимы",

    "требуется",

    "требуются",

    "ищу",

    "ищем",

    "ищет",

    "ищут",

    "кто может",

    "кто сможет",

    "кто есть",

    "есть кто",

    "возьму в аренду",

    "возьмем в аренду",

    "возьмём в аренду",

    "арендовать",

    "аренда",

    "нужна техника",

    "нужна спецтехника",

    "нужен материал",

    "нужны материалы",

    "нужна доставка",

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

    "помощь диспетчера",

    "по размещению рекламы",

    "размещение рекламы",

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


job_patterns = [

    r"\bтребует(?:ся|ются)\s+(?:\d+\s+)?рабоч",

    r"\bищем\s+(?:\d+\s+)?рабоч",

    r"\bнужн(?:ы|о|а|ен)\s+(?:\d+\s+)?рабоч",

    r"\bваканси",

    r"\bгражданство\s*:",

    r"\bфото\s+паспорта",

    r"\bежедневная\s+оплата",
]


# ============================================================
# ПОИСК СЛОВ БЕЗ ЛОЖНЫХ СОВПАДЕНИЙ
# ============================================================

def contains_word(text, word):

    text = text.lower()

    word = word.lower()

    if " " in word or "-" in word:

        return word in text

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
# ПОИСК ТЕЛЕФОНА
# ============================================================

phone_pattern = re.compile(
    r"""
    (?:
        (?:\+7|8)
        [\s\-\(\)\.]*
        \d{3}
        [\s\-\(\)\.]*
        \d{3}
        [\s\-\(\)\.]*
        \d{2}
        [\s\-\(\)\.]*
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

    return (
        "+"
        + digits
    )


# ============================================================
# АНТИДУБЛЬ
# ============================================================
#
# Одна и та же заявка часто копируется в разные группы.
#
# Старый вариант:
# chat_id + message_id
#
# не помогал, потому что в каждой группе ID разные.
#
# Теперь создаём отпечаток:
#
# телефон + нормализованный текст.
#
# Повтор в течение 24 часов НЕ отправляется.
# ============================================================

DUPLICATE_TTL = 24 * 60 * 60

seen_leads = {}


def normalize_lead_text(text):

    value = (
        text
        or ""
    ).lower()

    value = value.replace(
        "ё",
        "е"
    )

    # Убираем ссылки.
    value = re.sub(
        r"https?://\S+",
        " ",
        value
    )

    # Убираем @username.
    value = re.sub(
        r"@\w+",
        " ",
        value
    )

    # Оставляем буквы и цифры.
    value = re.sub(
        r"[^a-zа-я0-9]+",
        " ",
        value,
        flags=re.IGNORECASE
    )

    # Нормализуем пробелы.
    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


def make_lead_key(
    text,
    phone
):

    normalized = normalize_lead_text(
        text
    )

    raw_key = (
        phone
        + "|"
        + normalized
    )

    return hashlib.sha256(
        raw_key.encode(
            "utf-8"
        )
    ).hexdigest()


def cleanup_seen_leads():

    now = time.time()

    expired = [
        key
        for key, created_at in seen_leads.items()
        if now - created_at > DUPLICATE_TTL
    ]

    for key in expired:

        seen_leads.pop(
            key,
            None
        )


def is_duplicate_lead(
    text,
    phone
):

    cleanup_seen_leads()

    key = make_lead_key(
        text,
        phone
    )

    if key in seen_leads:

        return (
            True,
            key
        )

    return (
        False,
        key
    )


def remember_lead(key):

    seen_leads[key] = time.time()


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


    if any(
        word in text
        for word in [
            "асфальтный скол",
            "асфальтовый скол",
            "асфальтная крошка",
            "асфальтовая крошка",
            "асфальтный срез",
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
    }).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=data
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            response.read()

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


def split_message(
    text,
    max_length=3800
):

    if len(text) <= max_length:

        return [
            text
        ]

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
# ОБРАБОТЧИК TELEGRAM
# ============================================================

@client.on(events.NewMessage)
async def handler(event):

    try:

        text = (
            event.raw_text
            or ""
        ).strip()

        if not text:

            print(
                "REJECT: пустое сообщение",
                flush=True
            )

            return


        text_lower = (
            text.lower()
        )


        # ----------------------------------------------------
        # ЧАТ / ГРУППА
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # АВТОР
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ЛОГ
        # ----------------------------------------------------

        short_text = (
            text
            .replace("\n", " ")
            [:500]
        )


        print(
            "\n"
            + "=" * 70,
            flush=True
        )

        print(
            f"RECEIVED | {chat_name} | {short_text}",
            flush=True
        )


        # ----------------------------------------------------
        # РЕКЛАМА / ВАКАНСИЯ
        # ----------------------------------------------------

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


        for pattern in job_patterns:

            if re.search(
                pattern,
                text_lower,
                flags=re.IGNORECASE
            ):

                print(
                    "REJECT: job",
                    flush=True
                )

                return


        # ----------------------------------------------------
        # НЕНУЖНАЯ ТЕХНИКА
        # ----------------------------------------------------

        for pattern in unwanted_equipment_patterns:

            if re.search(
                pattern,
                text_lower,
                flags=re.IGNORECASE
            ):

                print(
                    "REJECT: ненужная техника:",
                    pattern,
                    flush=True
                )

                return


        # ----------------------------------------------------
        # НУЖНАЯ ТЕХНИКА / РАБОТЫ
        # ----------------------------------------------------

        equipment_found = find_matches(
            text_lower,
            equipment_words
        )


        # ----------------------------------------------------
        # МАТЕРИАЛЫ
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ПРИЗНАК ЗАЯВКИ
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ГЕОГРАФИЯ
        # ----------------------------------------------------

        geo_status, location_found = analyze_geo(
            text_lower
        )


        print(
            "География:",
            geo_status,
            location_found,
            flush=True
        )


        if geo_status == "outside":

            print(
                "REJECT: явно указано местоположение "
                "вне нашей зоны",
                flush=True
            )

            return


        if geo_status == "unknown":

            print(
                "INFO: район не указан",
                flush=True
            )


        # ----------------------------------------------------
        # ТЕЛЕФОН
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # АНТИДУБЛЬ 24 ЧАСА
        # ----------------------------------------------------

        duplicate, lead_key = is_duplicate_lead(
            text,
            phone
        )


        if duplicate:

            print(
                "REJECT: такая заявка уже приходила "
                "за последние 24 часа",
                flush=True
            )

            return


        # ----------------------------------------------------
        # ОЦЕНКА
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ИМЯ АВТОРА
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ССЫЛКА НА ОРИГИНАЛ
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ГЕОГРАФИЯ ДЛЯ БОТА
        # ----------------------------------------------------

        if location_found:

            geo_line = ", ".join(
                location_found
            )

        else:

            geo_line = (
                "не указан"
            )


        # ----------------------------------------------------
        # ТЕХНИКА
        # ----------------------------------------------------

        equipment_line = ""

        if equipment_found:

            equipment_line = (
                "🚜 Техника / работы: "
                + ", ".join(
                    equipment_found
                )
                + "\n"
            )


        # ----------------------------------------------------
        # МАТЕРИАЛ
        # ----------------------------------------------------

        material_line = ""

        if material_found:

            material_line = (
                "🧱 Материал: "
                + ", ".join(
                    material_found
                )
                + "\n"
            )


        # ----------------------------------------------------
        # СООБЩЕНИЕ
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ОТПРАВКА
        # ----------------------------------------------------

        print(
            "SEND: заявка прошла фильтры",
            flush=True
        )


        sent = send_to_bot(
            alert
        )


        if sent:

            # Запоминаем заявку ТОЛЬКО после успешной отправки.
            remember_lead(
                lead_key
            )

            print(
                "✅ ЗАЯВКА УШЛА В TELEGRAM-БОТА",
                flush=True
            )

        else:

            print(
                "❌ TELEGRAM НЕ ПРИНЯЛ СООБЩЕНИЕ",
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
        "🚀 МОНИТОР ЗАЯВОК ЗАПУСКАЕТСЯ — FILTER v4",
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


    # --------------------------------------------------------
    # СЧИТАЕМ ГРУППЫ
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # ТЕСТ ПРИ ЗАПУСКЕ
    # --------------------------------------------------------

    test_message = (
        "✅ МОНИТОР ЗАЯВОК ЗАПУЩЕН — FILTER v4\n\n"

        f"Видно групп/каналов: {group_count}\n\n"

        "🚜 Экскаватор-погрузчик\n"

        "🚜 Мини-погрузчик\n"

        "🚚 Самосвал\n"

        "🛣 Каток\n"

        "🧱 Материалы\n"

        "🛣 Асфальтирование / дорожные работы\n"

        "❄️ Уборка / погрузка / вывоз снега\n\n"

        "❌ Мини-экскаватор НЕ принимается\n"

        "❌ Манипулятор НЕ принимается\n"

        "❌ Автокран / трактор / бульдозер / грейдер "
        "НЕ принимаются\n\n"

        "🔎 Признак заявки ОБЯЗАТЕЛЕН\n"

        "📞 Телефон ОБЯЗАТЕЛЕН\n"

        "📍 Москва: только ЮВАО\n"

        "📍 Наша зона МО включена\n"

        "📍 Если адрес вообще не указан — "
        "заявка не теряется\n\n"

        "🔁 Повтор одинаковой заявки: "
        "не чаще 1 раза за 24 часа"
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


# ============================================================
# СТАРТ
# ============================================================

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
