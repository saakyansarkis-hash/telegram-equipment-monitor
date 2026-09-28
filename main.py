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

client = TelegramClient(StringSession(session), api_id, api_hash)


# ============================================================
# ПРИОРИТЕТНЫЙ СПИСОК TELEGRAM-ИСТОЧНИКОВ
# ============================================================
#
# FILTER v7 обрабатывает ВСЕ группы/каналы, которые видит Telegram-аккаунт.
#
# Источники ниже — наш дополнительный приоритетный список.
# Если аккаунт уже состоит в них, сообщения оттуда обрабатываются как обычно.
# Если аккаунт в них не состоит, Telethon сам читать их не сможет до вступления.
# Для публичных групп используем username.
# Для инвайт-групп без username используем название чата.
# ============================================================

PRIORITY_SOURCE_USERNAMES = {
    "spetstekhnika_arenda",
    "spetctechnika_arenda_uslugi",
    "spetstekhnika_moskva",
    "arenda_spechtekhniki",
    "arendaspecteh_stroika",
    "arenda_spetstekhniki_msk",
    "spectehnikfree",
    "spectehnika_msk_pro",
    "spectehnix",
    "zakazspecteh",
    "spectehnika_5",
    "goryachie_zakazy",
    "spec_tech_bot",
    "kotelniki_24",
    "kotelniki_24chat",
    "lytkarinoonline",
    "lytkarino_chat",
    "vsem_podryad",
    "vsempodryad",
    "samosvalinfo",
    "samosvalam_rabota",
    "stroiteli_moskva",
    "samosvval",
    "stroitelimsk5",
    "stroitelimsk3",
    "stroiteli_moscow",
    "samosval2",
    "podryadru",
    "tehzakaz",
    "stroitelimsk4",
    "stroycamoskva",
    "spec_tehnika24",
    "moskva_spectehnika_arenda",
    "arenda_spehtekhniki",
    "spectehnika_1",
    "spectechnikarent",
    "stroiteli_msk_1",
    "gksamolet",
    "arenda_spetstekhniky",
    "arenda_spectehniki1",
    "stroymaterialy_moskva",
    "myluber",
    "ramenskoe_tv",
    "rx_machine",
    "samosvalrussia",
    "stroitelimoscow",
    "samolet2021all",
    "zhukovskiyonline",
    "zhukovskiy_ramenskoe",
    "grad_zhukovskiy",
    "ugorodok",
    "vm_volkov",
}

# Инвайт-группы без стабильного username.
# Сравниваем по названию, если оно совпадает.
PRIORITY_SOURCE_TITLES = {
    "спецтехника и самосвалы + нерудка мо и рф",
    "спецтехника // аренда",
    "чат жкх лыткарино",
}


def normalize_source_name(value):
    return (value or "").strip().lower().replace("ё", "е")


def source_is_priority(chat):
    username = normalize_source_name(getattr(chat, "username", None)).lstrip("@")
    title = normalize_source_name(getattr(chat, "title", None))

    if username and username in PRIORITY_SOURCE_USERNAMES:
        return True

    if title and title in {
        normalize_source_name(x)
        for x in PRIORITY_SOURCE_TITLES
    }:
        return True

    return False


# ============================================================
# ГЕОГРАФИЯ
# ============================================================
#
# 1. ЗАЯВКИ ТОЛЬКО НА СПЕЦТЕХНИКУ / МАТЕРИАЛ:
#    только ЮВАО + наша ближайшая зона МО.
#
# 2. ЗАЯВКИ НА РАБОТЫ / ПОДРЯДЫ:
#    вся Москва + вся Московская область.
#
# 3. Если адрес не указан:
#    заявку не теряем.
# ============================================================

LOCAL_GEO_PATTERNS = {
    # Москва / ЮВАО
    "ЮВАО": [
        r"\bювао\b",
        r"юго[- ]восточн\w*\s+административн\w*\s+округ\w*",
    ],
    "Лефортово": [r"\bлефортов\w*\b"],
    "Нижегородский": [r"\bнижегородск\w*\b"],
    "Рязанский": [
        r"\bрязанск\w*\s+проспект\w*\b",
        r"\bрязанск\w*\s+район\w*\b",
        r"\bм\.?\s*рязанский\s+проспект\b",
    ],
    "Текстильщики": [r"\bтекстильщик\w*\b"],
    "Кузьминки": [r"\bкузьминк\w*\b"],
    "Выхино": [r"\bвыхин\w*\b"],
    "Жулебино": [r"\bжулебин\w*\b"],
    "Люблино": [r"\bлюблин\w*\b"],
    "Марьино": [r"\bмарьин\w*\b"],
    "Печатники": [r"\bпечатник\w*\b"],
    "Южнопортовый": [r"\bюжнопортов\w*\b"],
    "Капотня": [r"\bкапотн\w*\b"],
    "Некрасовка": [r"\bнекрасовк\w*\b"],

    # МО / наша зона
    "Люберцы": [r"\bлюберц\w*\b"],
    "Котельники": [r"\bкотельник\w*\b"],
    "Дзержинский": [
        r"\bг\.?\s*дзержинск\w*\b",
        r"\bгород\w*\s+дзержинск\w*\b",
        r"\bг\.?\s*о\.?\s*дзержинск\w*\b",
        r"\bгородск\w*\s+округ\w*\s+дзержинск\w*\b",
        r"\bдзержинский,\s*московск\w*\s+област\w*\b",
    ],
    "Островцы": [r"\bостровц\w*\b"],
    "Бронницы": [r"\bбронниц\w*\b"],
    "Софьино": [r"\bсофьин\w*\b"],
    "Лыткарино": [r"\bлыткарин\w*\b"],
    "Томилино": [r"\bтомилин\w*\b"],
    "Красково": [r"\bкрасков\w*\b"],
    "Марусино": [r"\bмарусин\w*\b"],
    "Малаховка": [r"\bмалаховк\w*\b"],
    "Октябрьский МО": [
        r"\bоктябрьск\w*\b.{0,40}\bлюбер",
        r"\bлюбер.{0,40}\bоктябрьск\w*\b",
    ],
    "Быково": [r"\bбыков\w*\b"],
    "Раменское": [r"\bраменск\w*\b"],
    "Жуковский": [
        r"\bг\.?\s*жуковск\w*\b",
        r"\bгород\w*\s+жуковск\w*\b",
        r"\bг\.?\s*о\.?\s*жуковск\w*\b",
        r"\bгородск\w*\s+округ\w*\s+жуковск\w*\b",
        r"\bжуковский,\s*московск\w*\s+област\w*\b",
    ],
}

MOSCOW_MO_PATTERNS = [
    r"\bмосква\b",
    r"\bмск\b",
    r"\bмосковск\w*\s+област\w*\b",
    r"\bподмосков\w*\b",

    r"\bбалаших\w*\b",
    r"\бреутов\w*\b",
    r"\bмытищ\w*\b",
    r"\bкоролев\w*\b",
    r"\bкоролёв\w*\b",
    r"\bкрасногорск\w*\b",
    r"\bхимк\w*\b",
    r"\bодинцов\w*\b",
    r"\bподольск\w*\b",
    r"\bдомодедов\w*\b",
    r"\bвидно\w*\b",
    r"\bногинск\w*\b",
    r"\bбогородск\w*\b",
    r"\bэлектростал\w*\b",
    r"\bпушкино\w*\b",
    r"\bщелков\w*\b",
    r"\bщёлков\w*\b",
    r"\bдолгопрудн\w*\b",
    r"\bлобн\w*\b",
    r"\bсолнечногорск\w*\b",
    r"\bистр\w*\b",
    r"\bчехов\w*\b",
    r"\bсерпухов\w*\b",
    r"\bступин\w*\b",
    r"\bколомн\w*\b",
    r"\bвоскресенск\w*\b",
    r"\bшатур\w*\b",
    r"\bегорьевск\w*\b",
    r"\bорехово[- ]зуев\w*\b",
    r"\bпавловск\w*\s+посад\w*\b",
    r"\bфрязин\w*\b",
    r"\bжелезнодорожн\w*\b",

    r"\bлюберц\w*\b",
    r"\bкотельник\w*\b",
    r"\bдзержинск\w*\b",
    r"\bлыткарин\w*\b",
    r"\bжуковск\w*\b",
    r"\bраменск\w*\b",
    r"\bбронниц\w*\b",
]

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


def normalize_text(text):
    return (text or "").lower().replace("ё", "е")


def find_pattern_labels(text, mapping):
    lower = normalize_text(text)
    found = []

    for label, patterns in mapping.items():
        for pattern in patterns:
            if re.search(pattern, lower, flags=re.IGNORECASE | re.DOTALL):
                found.append(label)
                break

    return list(dict.fromkeys(found))


def has_any_pattern(text, patterns):
    lower = normalize_text(text)
    return any(
        re.search(pattern, lower, flags=re.IGNORECASE | re.DOTALL)
        for pattern in patterns
    )


def analyze_geo_for_equipment(text):
    local_found = find_pattern_labels(text, LOCAL_GEO_PATTERNS)

    if local_found:
        return "allowed", local_found

    if has_any_pattern(text, EXPLICIT_GEO_PATTERNS):
        return "outside", []

    return "unknown", []


def analyze_geo_for_work(text):
    local_found = find_pattern_labels(text, LOCAL_GEO_PATTERNS)

    if local_found:
        return "allowed", local_found

    if has_any_pattern(text, MOSCOW_MO_PATTERNS):
        return "allowed", ["Москва / Московская область"]

    if has_any_pattern(text, EXPLICIT_GEO_PATTERNS):
        return "outside", []

    return "unknown", []


# ============================================================
# НАША ТЕХНИКА
# ============================================================

equipment_words = [
    "экскаватор-погрузчик",
    "экскаватор погрузчик",
    "jcb",
    "джсб",

    "мини-погрузчик",
    "мини погрузчик",
    "минипогрузчик",
    "бобкэт",
    "бобкат",
    "bobcat",

    "самосвал",
    "самосвалы",
    "самосвала",
    "самосвалов",
    "howo",
    "хово",
    "8x4",
    "8×4",
    "6x4",
    "6×4",
    "20 м3",
    "20 м³",

    "каток",
    "виброкаток",
    "дорожный каток",
]


# ============================================================
# РАБОТЫ / ПОДРЯДЫ
# ============================================================

work_words = [
    "асфальтирование",
    "укладка асфальта",
    "асфальтобетон",
    "асфальтобетонное покрытие",
    "аб покрытие",
    "дорожные работы",
    "строительство дороги",
    "строительство дорог",
    "ремонт дороги",
    "ремонт дорог",
    "ямочный ремонт",
    "внутриплощадочные дороги",
    "внутридворовые дороги",
    "проезд",
    "проезды",
    "парковка",
    "парковки",
    "стоянка",
    "стоянки",
    "площадка",
    "площадки",
    "тротуар",
    "тротуары",

    "благоустройство",
    "комплексное благоустройство",
    "благоустройство территории",
    "дворовая территория",
    "дворовые территории",

    "бордюр",
    "бордюры",
    "бортовой камень",
    "дорожный борт",
    "тротуарный борт",
    "устройство основания",
    "дорожная одежда",
    "подстилающий слой",
    "щебеночное основание",
    "щебёночное основание",
    "песчаное основание",
    "послойное уплотнение",
    "уплотнение",

    "земляные работы",
    "разработка грунта",
    "выемка грунта",
    "котлован",
    "котлованы",
    "траншея",
    "траншеи",
    "планировка",
    "планировка территории",
    "вертикальная планировка",
    "отсыпка",
    "обратная засыпка",
    "замена грунта",
    "вывоз грунта",
    "вывоз земли",

    "демонтаж асфальта",
    "демонтаж покрытия",
    "демонтаж покрытий",
    "демонтаж",
    "строительный бой",
    "вывоз боя",
    "утилизация грунта",
    "прием грунта",
    "приём грунта",

    "дренаж",
    "ливневка",
    "ливнёвка",
    "водоотведение",
    "наружные сети",
    "наружные работы",

    "вывоз снега",
    "уборка снега",
    "погрузка снега",
    "расчистка снега",
    "очистка от снега",
    "снегоуборочные работы",
]


contract_words = [
    "требуется подрядчик",
    "требуются подрядчики",
    "ищем подрядчика",
    "ищу подрядчика",
    "нужен подрядчик",
    "нужны подрядчики",
    "субподряд",
    "субподрядчик",
    "генподряд",
    "генподрядчик",
    "объем работ",
    "объём работ",
    "объемы работ",
    "объёмы работ",
    "вор",
    "ведомость объемов",
    "ведомость объёмов",
    "запрос кп",
    "коммерческое предложение",
    "тендер",
    "требуется бригада",
    "ищем бригаду",
    "можно приступать",
    "начало работ",
    "давальческий материал",
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
    "щпс",
    "асфальт",
    "асфальтный скол",
    "асфальтовый скол",
    "асфальтная крошка",
    "асфальтовая крошка",
    "асфальтовый лом",
    "лом асфальта",
    "асфальтный срез",
    "асфальтовый срез",
    "бой бетона",
    "бетонный бой",
    "бой бетонный",
    "нерудка",
]


# ============================================================
# ПРИЗНАК ЗАЯВКИ
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
    "приобрести",
    "закупаем",
    "закупаем материал",
    "закупаем материалы",
    "заказать",
    "нужно заказать",
    "кто привезет",
    "кто привезёт",
    "кто доставит",
    "привезти",
    "доставить",
    "подрядчик",
    "подрядчики",
    "субподряд",
    "объем работ",
    "объём работ",
    "объемы работ",
    "объёмы работ",
    "запрос кп",
    "тендер",
]


# ============================================================
# РЕКЛАМА / ВАКАНСИИ
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
]


# ============================================================
# НЕНУЖНАЯ ТЕХНИКА
# ============================================================

unwanted_equipment_patterns = [
    r"\bмини[\s-]*экскаватор\w*\b",
    r"\bминиэкскаватор\w*\b",
    r"\bманипулятор\w*\b",
    r"\bавтокран\w*\b",
    r"\bбульдозер\w*\b",
    r"\bтрактор\w*\b",
    r"\bгрейдер\w*\b",
]


# ============================================================
# ПОИСК СЛОВ
# ============================================================

def contains_word(text, word):
    text = text.lower()
    word = word.lower()

    if " " in word or "-" in word or "×" in word:
        return word in text

    pattern = r"(?<!\w)" + re.escape(word) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def find_matches(text, words):
    found = []

    for word in words:
        if contains_word(text, word):
            found.append(word)

    return list(dict.fromkeys(found))


# ============================================================
# ТЕЛЕФОН — ОБЯЗАТЕЛЕН
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
    match = phone_pattern.search(text)

    if not match:
        return None

    digits = re.sub(r"\D", "", match.group(0))

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) != 11 or not digits.startswith("7"):
        return None

    return "+" + digits


# ============================================================
# АНТИДУБЛЬ
# ============================================================

DUPLICATE_TTL = 24 * 60 * 60
seen_leads = {}


def normalize_lead_text(text):
    value = normalize_text(text)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"@\w+", " ", value)
    value = re.sub(r"[^a-zа-я0-9]+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def make_lead_key(text, phone):
    normalized = normalize_lead_text(text)
    raw_key = phone + "|" + normalized[:1000]
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def cleanup_seen_leads():
    now = time.time()

    expired = [
        key
        for key, created_at in seen_leads.items()
        if now - created_at > DUPLICATE_TTL
    ]

    for key in expired:
        seen_leads.pop(key, None)


def is_duplicate_lead(text, phone):
    cleanup_seen_leads()
    key = make_lead_key(text, phone)

    if key in seen_leads:
        return True, key

    return False, key


def remember_lead(key):
    seen_leads[key] = time.time()


# ============================================================
# КЛАССИФИКАЦИЯ
# ============================================================

def classify_lead(text_lower):
    equipment_found = find_matches(text_lower, equipment_words)
    work_found = find_matches(text_lower, work_words)
    contract_found = find_matches(text_lower, contract_words)
    material_found = find_matches(text_lower, material_words)

    is_work_lead = bool(work_found or contract_found)

    return {
        "equipment_found": equipment_found,
        "work_found": work_found,
        "contract_found": contract_found,
        "material_found": material_found,
        "is_work_lead": is_work_lead,
    }


def is_only_unwanted_equipment(text_lower, classification):
    if classification["equipment_found"]:
        return False

    if classification["work_found"] or classification["contract_found"]:
        return False

    if classification["material_found"]:
        return False

    return any(
        re.search(pattern, text_lower, flags=re.IGNORECASE)
        for pattern in unwanted_equipment_patterns
    )


# ============================================================
# ОЦЕНКА
# ============================================================

def calculate_score(text, classification, location_found, priority_source=False):
    score = 1

    equipment_found = classification["equipment_found"]
    work_found = classification["work_found"]
    contract_found = classification["contract_found"]
    material_found = classification["material_found"]

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

    if contract_found:
        score += 3

    if len(work_found) >= 3:
        score += 3
    elif work_found:
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
            "каток",
        ]
    ):
        score += 2

    if material_found:
        score += 1

    if location_found:
        score += 1

    if priority_source:
        score += 1

    return min(score, 10)


# ============================================================
# ОТПРАВКА В БОТА
# ============================================================

def send_bot_part(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": bot_chat_id,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()

        print("✅ Telegram: сообщение отправлено", flush=True)
        return True

    except urllib.error.HTTPError as error:
        try:
            body = error.read().decode("utf-8")
        except Exception:
            body = ""

        print(
            "❌ TELEGRAM HTTP ERROR:",
            error.code,
            body,
            flush=True,
        )

        return False

    except Exception as error:
        print(
            "❌ TELEGRAM ERROR:",
            repr(error),
            flush=True,
        )

        return False


def split_message(text, max_length=3800):
    if len(text) <= max_length:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            parts.append(remaining)
            break

        cut = remaining.rfind("\n", 0, max_length)

        if cut < 1000:
            cut = max_length

        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()

    return parts


def send_to_bot(message):
    parts = split_message(message)

    for index, part in enumerate(parts, start=1):
        if len(parts) > 1:
            part = f"Часть {index}/{len(parts)}\n\n" + part

        if not send_bot_part(part):
            return False

    return True


# ============================================================
# ОБРАБОТЧИК
# ============================================================

@client.on(events.NewMessage)
async def handler(event):
    try:
        text = (event.raw_text or "").strip()

        if not text:
            print("REJECT: пустое сообщение", flush=True)
            return

        text_lower = normalize_text(text)

        # ----------------------------------------------------
        # ЧАТ
        # ----------------------------------------------------
        try:
            chat = await event.get_chat()
        except Exception:
            chat = None

        if not chat:
            print("REJECT: не удалось определить чат", flush=True)
            return

        chat_name = (
            getattr(chat, "title", None)
            or getattr(chat, "username", None)
            or "Личный чат"
        )

        chat_username = getattr(chat, "username", None)

        # ----------------------------------------------------
        # ИСТОЧНИК
        # ----------------------------------------------------
        # Читаем ВСЕ группы/каналы, которые видит аккаунт.
        # Наш собранный список только помечаем как приоритетный.
        priority_source = source_is_priority(chat)

        print(
            f"ИСТОЧНИК: {'⭐ из нашей базы' if priority_source else 'обычная группа аккаунта'}",
            flush=True,
        )

        # ----------------------------------------------------
        # АВТОР
        # ----------------------------------------------------
        try:
            sender = await event.get_sender()
        except Exception:
            sender = None

        username = getattr(sender, "username", None)
        first_name = getattr(sender, "first_name", None)
        last_name = getattr(sender, "last_name", None)

        if username and username.lower() == "spec_clients_bot":
            print("REJECT: собственный бот", flush=True)
            return

        # ----------------------------------------------------
        # ЛОГ
        # ----------------------------------------------------
        short_text = text.replace("\n", " ")[:500]

        print("\n" + "=" * 70, flush=True)
        print(f"RECEIVED | {chat_name} | {short_text}", flush=True)

        # ----------------------------------------------------
        # РЕКЛАМА / ВАКАНСИЯ
        # ----------------------------------------------------
        ad_found = find_matches(
            text_lower,
            ad_exclude_words + exclude_words,
        )

        if ad_found:
            print(
                "REJECT: реклама/вакансия:",
                ad_found,
                flush=True,
            )
            return

        for pattern in job_patterns:
            if re.search(
                pattern,
                text_lower,
                flags=re.IGNORECASE,
            ):
                print("REJECT: job", flush=True)
                return

        # ----------------------------------------------------
        # КЛАССИФИКАЦИЯ
        # ----------------------------------------------------
        classification = classify_lead(text_lower)

        equipment_found = classification["equipment_found"]
        work_found = classification["work_found"]
        contract_found = classification["contract_found"]
        material_found = classification["material_found"]

        print("Наша техника:", equipment_found, flush=True)
        print("Работы:", work_found, flush=True)
        print("Подряд:", contract_found, flush=True)
        print("Материалы:", material_found, flush=True)

        if (
            not equipment_found
            and not work_found
            and not contract_found
            and not material_found
        ):
            if is_only_unwanted_equipment(
                text_lower,
                classification,
            ):
                print(
                    "REJECT: только ненужная техника",
                    flush=True,
                )
            else:
                print(
                    "REJECT: нет нашей техники/работ/материалов",
                    flush=True,
                )

            return

        # ----------------------------------------------------
        # ПРИЗНАК ЗАЯВКИ
        # ----------------------------------------------------
        request_found = find_matches(
            text_lower,
            request_words,
        )

        print(
            "Признак заявки:",
            request_found,
            flush=True,
        )

        if not request_found and not contract_found:
            print(
                "REJECT: нет признака заявки",
                flush=True,
            )
            return

        # ----------------------------------------------------
        # ГЕОГРАФИЯ
        # ----------------------------------------------------
        if classification["is_work_lead"]:
            lead_type = "🏗 РАБОТЫ / ПОДРЯД"
            geo_status, location_found = analyze_geo_for_work(
                text_lower
            )

            if geo_status == "outside":
                print(
                    "REJECT: подряд явно вне Москвы/МО",
                    flush=True,
                )
                return

        else:
            lead_type = "🚜 ТЕХНИКА / МАТЕРИАЛ"
            geo_status, location_found = analyze_geo_for_equipment(
                text_lower
            )

            if geo_status == "outside":
                print(
                    "REJECT: техника/материал вне нашей зоны",
                    flush=True,
                )
                return

        print("Тип:", lead_type, flush=True)
        print(
            "География:",
            geo_status,
            location_found,
            flush=True,
        )

        # ----------------------------------------------------
        # ТЕЛЕФОН — ОБЯЗАТЕЛЕН
        # ----------------------------------------------------
        phone = find_phone(text)

        if not phone:
            print(
                "REJECT: НЕТ ТЕЛЕФОНА",
                flush=True,
            )
            return

        print("Телефон:", phone, flush=True)

        # ----------------------------------------------------
        # АНТИДУБЛЬ
        # ----------------------------------------------------
        duplicate, lead_key = is_duplicate_lead(
            text,
            phone,
        )

        if duplicate:
            print(
                "REJECT: такая заявка уже приходила "
                "за последние 24 часа",
                flush=True,
            )
            return

        # ----------------------------------------------------
        # ОЦЕНКА
        # ----------------------------------------------------
        score = calculate_score(
            text_lower,
            classification,
            location_found,
            priority_source=priority_source,
        )

        if score >= 8:
            priority = "🔥🔥🔥 ВЫСОКИЙ ПРИОРИТЕТ"
        elif score >= 6:
            priority = "🔥🔥 ХОРОШАЯ ЗАЯВКА"
        elif score >= 4:
            priority = "🔥 ПОДХОДИТ"
        else:
            priority = "🟡 НОВАЯ ЗАЯВКА"

        # ----------------------------------------------------
        # АВТОР
        # ----------------------------------------------------
        if username:
            sender_name = "@" + username
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
                sender_name = "Не указан"

        # ----------------------------------------------------
        # ССЫЛКА
        # ----------------------------------------------------
        message_link = ""

        if chat_username:
            message_link = (
                "https://t.me/"
                f"{chat_username}/"
                f"{event.id}"
            )

        # ----------------------------------------------------
        # СТРОКИ
        # ----------------------------------------------------
        geo_line = (
            ", ".join(location_found)
            if location_found
            else "не указан"
        )

        equipment_line = ""
        if equipment_found:
            equipment_line = (
                "🚜 Наша техника: "
                + ", ".join(equipment_found)
                + "\n"
            )

        work_line = ""
        if work_found:
            work_line = (
                "🏗 Работы: "
                + ", ".join(work_found)
                + "\n"
            )

        contract_line = ""
        if contract_found:
            contract_line = (
                "📋 Подряд: "
                + ", ".join(contract_found)
                + "\n"
            )

        material_line = ""
        if material_found:
            material_line = (
                "🧱 Материалы: "
                + ", ".join(material_found)
                + "\n"
            )

        # ----------------------------------------------------
        # СООБЩЕНИЕ
        # ----------------------------------------------------
        source_line = (
            "⭐ Источник: из нашей собранной базы"
            if priority_source
            else "📢 Источник: одна из ваших текущих групп"
        )

        alert = (
            f"{priority}\n"
            f"{lead_type}\n"
            f"⭐ Приоритет: {score}/10\n"
            f"{source_line}\n\n"

            f"{equipment_line}"
            f"{work_line}"
            f"{contract_line}"
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
            flush=True,
        )

        sent = send_to_bot(alert)

        if sent:
            remember_lead(lead_key)

            print(
                "✅ ЗАЯВКА УШЛА В TELEGRAM-БОТА",
                flush=True,
            )
        else:
            print(
                "❌ TELEGRAM НЕ ПРИНЯЛ СООБЩЕНИЕ",
                flush=True,
            )

    except Exception as error:
        print(
            "❌ ОШИБКА ОБРАБОТКИ:",
            repr(error),
            flush=True,
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    print("\n" + "=" * 70, flush=True)
    print(
        "🚀 МОНИТОР ЗАЯВОК ЗАПУСКАЕТСЯ — FILTER v7",
        flush=True,
    )
    print("=" * 70, flush=True)

    await client.start()

    me = await client.get_me()

    if getattr(me, "bot", False):
        raise RuntimeError(
            "TELEGRAM_SESSION авторизована как БОТ. "
            "Для мониторинга нужен обычный Telegram-аккаунт."
        )

    print(
        "✅ TELEGRAM АККАУНТ АВТОРИЗОВАН",
        flush=True,
    )

    # --------------------------------------------------------
    # СЧИТАЕМ ВСЕ ГРУППЫ И НАШ ПРИОРИТЕТНЫЙ СПИСОК
    # --------------------------------------------------------
    group_count = 0
    priority_visible = 0

    print(
        "\n📋 ГРУППЫ / КАНАЛЫ:",
        flush=True,
    )

    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            group_count += 1
            entity = dialog.entity

            priority_source = source_is_priority(entity)

            if priority_source:
                priority_visible += 1

            username = (
                getattr(entity, "username", None)
                or "-"
            )

            marker = "⭐" if priority_source else "  "

            print(
                f"{marker} GROUP {group_count}: "
                f"{dialog.name} | "
                f"@{username} | "
                f"ID: {dialog.id}",
                flush=True,
            )

    print(
        "\n📊 ВСЕГО ВИДНО ГРУПП/КАНАЛОВ:",
        group_count,
        flush=True,
    )

    print(
        "⭐ ИЗ НАШЕЙ СОБРАННОЙ БАЗЫ ВИДНО:",
        priority_visible,
        flush=True,
    )

    print(
        "👂 ЖДУ НОВЫЕ СООБЩЕНИЯ...",
        flush=True,
    )

    # --------------------------------------------------------
    # ТЕСТ
    # --------------------------------------------------------
    test_message = (
        "✅ МОНИТОР ЗАЯВОК ЗАПУЩЕН — FILTER v7\n\n"

        f"Всего видно групп/каналов: {group_count}\n"
        f"Из нашей собранной базы видно: {priority_visible}\n\n"

        "📢 ОБРАБАТЫВАЮТСЯ ВСЕ ГРУППЫ И КАНАЛЫ, "
        "КОТОРЫЕ ВИДИТ ВАШ TELEGRAM-АККАУНТ.\n"
        "⭐ Наш собранный список используется как дополнительный приоритет.\n\n"

        "🚜 ЗАЯВКИ ТОЛЬКО НА ТЕХНИКУ:\n"
        "ЮВАО + Люберцы / Котельники / Дзержинский / "
        "Лыткарино / Жуковский / Раменское и ближайшая зона.\n\n"

        "🏗 ЗАЯВКИ НА РАБОТЫ / ПОДРЯДЫ:\n"
        "ВСЯ Москва + ВСЯ Московская область.\n\n"

        "📞 ТЕЛЕФОН В ТЕКСТЕ ЗАЯВКИ ОБЯЗАТЕЛЕН.\n"
        "Без телефона заявка НЕ отправляется.\n\n"

        "🚜 Наша техника:\n"
        "• Экскаватор-погрузчик\n"
        "• Мини-погрузчик\n"
        "• HOWO / самосвал 20 м³\n"
        "• Каток 4 т\n\n"

        "🏗 Наши работы:\n"
        "• Асфальтирование\n"
        "• Благоустройство\n"
        "• Дороги / парковки / площадки\n"
        "• Бордюры / основания\n"
        "• Земляные работы\n"
        "• Демонтаж / вывоз грунта\n"
        "• Дренаж / наружные сети\n"
        "• Подряд / субподряд / ВОР / тендер\n\n"

        "🔁 Дубли: не чаще 1 раза за 24 часа."
    )

    if send_to_bot(test_message):
        print(
            "✅ ТЕСТОВОЕ СООБЩЕНИЕ В БОТА ОТПРАВЛЕНО",
            flush=True,
        )
    else:
        print(
            "❌ ТЕСТОВОЕ СООБЩЕНИЕ В БОТА НЕ УШЛО",
            flush=True,
        )

    await client.run_until_disconnected()


# ============================================================
# СТАРТ
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "Монитор остановлен.",
            flush=True,
        )

    except Exception as error:
        print(
            "❌ КРИТИЧЕСКАЯ ОШИБКА:",
            repr(error),
            flush=True,
        )
        raise
