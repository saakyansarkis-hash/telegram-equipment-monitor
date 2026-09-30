import os
import re
import asyncio
import time
import hashlib
import csv
import json
from datetime import datetime
from pathlib import Path
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
# ТАБЛИЦА ЛИДОВ + ЭКОНОМИКА HOWO
# ============================================================

LEADS_CSV_PATH = os.getenv("LEADS_CSV_PATH", "leads.csv").strip()

DIESEL_RUB_PER_L = float(
    os.getenv("DIESEL_RUB_PER_L", "85")
)

HOWO_BODY_M3 = float(
    os.getenv("HOWO_BODY_M3", "20")
)

# Пока это расчетное значение. Если знаешь реальный расход,
# задай HOWO_FUEL_L_PER_100KM через переменную окружения.
HOWO_FUEL_L_PER_100KM = float(
    os.getenv("HOWO_FUEL_L_PER_100KM", "40")
)

# Полная экономика HOWO.
# Зарплату водителя и лизинг именно этого HOWO нужно задать отдельно.
HOWO_DRIVER_MONTHLY_RUB = float(
    os.getenv("HOWO_DRIVER_MONTHLY_RUB", "200000")
)

HOWO_LEASE_MONTHLY_RUB = float(
    os.getenv("HOWO_LEASE_MONTHLY_RUB", "60000")
)

HOWO_WORK_DAYS_MONTH = float(
    os.getenv("HOWO_WORK_DAYS_MONTH", "26")
)

HOWO_REPAIR_RESERVE_PCT = float(
    os.getenv("HOWO_REPAIR_RESERVE_PCT", "10")
)

HOWO_TIRE_RUB_PER_KM = float(
    os.getenv("HOWO_TIRE_RUB_PER_KM", "5")
)

HOWO_OTHER_RUB_PER_TRIP = float(
    os.getenv("HOWO_OTHER_RUB_PER_TRIP", "0")
)

# Пороговая оценка рентабельности HOWO.
# Можно менять через переменные окружения без правки файла.
HOWO_GOOD_MARGIN_PCT = float(
    os.getenv("HOWO_GOOD_MARGIN_PCT", "25")
)

HOWO_BORDER_MARGIN_PCT = float(
    os.getenv("HOWO_BORDER_MARGIN_PCT", "10")
)

HOWO_MIN_PROFIT_TRIP_RUB = float(
    os.getenv("HOWO_MIN_PROFIT_TRIP_RUB", "3000")
)

LEADS_CSV_HEADERS = [
    "Дата",
    "Категория",
    "Приоритет",
    "Балл",
    "Тип заявки",
    "География",
    "Группа",
    "Username группы",
    "Телефон",
    "Telegram контакт",
    "Техника",
    "Работы",
    "Подряд",
    "Материалы",
    "Площадь",
    "Объем",
    "Цена/ставка",
    "Плечо км",
    "Ставка руб/м3",
    "Ставка руб/рейс",
    "Рейсов/день",
    "Кузов HOWO м3",
    "Расход л/100км",
    "Дизель руб/л",
    "Выручка/рейс",
    "Топливо л/рейс",
    "Топливо руб/рейс",
    "Остаток после топлива/рейс",
    "Выручка/день",
    "Топливо руб/день",
    "Остаток после топлива/день",
    "Зарплата водителя/день",
    "Лизинг HOWO/день",
    "Ремонтный резерв/рейс",
    "Резина/рейс",
    "Прочее/рейс",
    "Полная себестоимость/рейс",
    "Прибыль/рейс",
    "Полная себестоимость/день",
    "Прибыль/день",
    "Маржа %",
    "Оценка HOWO",
    "Причина оценки HOWO",
    "ID лида",
    "Ссылка",
    "Текст заявки",
    "Статус",
]


# ============================================================
# ПРИОРИТЕТНЫЙ СПИСОК TELEGRAM-ИСТОЧНИКОВ
# ============================================================
#
# FILTER v11 обрабатывает ВСЕ группы/каналы, которые видит Telegram-аккаунт.
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
    "moskva_spetstekhnika",
    "spectehnika_2",
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


]


contract_words = [
    "требуется подрядчик",
    "требуются подрядчики",
    "ищем подрядчика",
    "ищу подрядчика",
    "нужен подрядчик",
    "нужны подрядчики",
    "требуется бригада",
    "ищем бригаду",
    "можно приступать",
    "начало работ",
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
    "нужен", "нужна", "нужно", "нужны", "надо",
    "необходим", "необходима", "необходимо", "необходимы",
    "требуется", "требуются",
    "ищу", "ищем", "ищет", "ищут",
    "кто может", "кто сможет", "кто есть", "есть кто",
    "возьму в аренду", "возьмем в аренду", "возьмём в аренду",
    "арендовать", "нужна техника", "нужна спецтехника",
    "нужен материал", "нужны материалы", "нужна доставка",
    "купить", "куплю", "купим", "приобрести",
    "заказать", "нужно заказать",
    "кто привезет", "кто привезёт", "кто доставит",
    "привезти", "доставить",
    "подрядчик", "подрядчики",
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
    "выполняем асфальтирование",
    "выполняем благоустройство",
    "выполняем земляные работы",
    "предлагаем услуги",
    "предлагаю услуги",
    "наши услуги",
    "наша компания выполняет",
    "работаем по москве",
    "работаем по московской области",
    "цена от",
    "стоимость от",
    "заказывайте",
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
# ЖЁСТКИЙ ФИЛЬТР МУСОРА / НЕ-КЛИЕНТСКИХ ПУБЛИКАЦИЙ
# ============================================================

# Тендеры, субподряды, закупки и конкурсные процедуры не присылаем.
blocked_procurement_patterns = [
    r"\bтендер\w*\b",
    r"\bаукцион\w*\b",
    r"\bгосзакуп\w*\b",
    r"\bзакупк\w*\b",
    r"\bконкурсн\w*\s+документац\w*\b",
    r"\bсубподряд\w*\b",
    r"\bгенподряд\w*\b",
    r"\bведомост\w*\s+об[ъь]ем\w*\b",
    r"(?<![а-яёa-z])вор(?![а-яёa-z])",
    r"\bзапрос\s+кп\b",
]

# Новости, отчеты и уже выполненные работы — не заявки.
news_completed_patterns = [
    r"\bадминистрац\w*\b.{0,120}\b(провел|провела|провели|сообщил|сообщила|сообщили)\w*\b",
    r"\b(отремонтировали|благоустроили|обустроили|построили|завершили|выполнили|провели)\b.{0,100}\b(работ|ремонт|дорог|двор|площадк|благоустрой)\w*\b",
    r"\bподвели\s+итоги\b",
    r"\bитоги\s+сезона\b",
    r"\bвстреч\w*\s+с\s+жител\w*\b",
]

# Явная реклама исполнителя/владельца техники.
provider_ad_patterns = [
    r"\b(выполняем|оказываем|предлагаем|предлагаю)\b.{0,80}\b(услуг|работ|асфальт|благоустрой|землян|спецтехник)\w*\b",
    r"\b(сдаю|сдаем|сдаём|сдам)\b.{0,60}\b(в\s+аренду|техник|экскаватор|самосвал|каток|погрузчик)\w*\b",
    r"\b(наш\w*\s+автопарк|техника\s+в\s+наличии|свободн\w*\s+техник)\b",
    r"\b(цена|стоимость)\s*[-—:]?\s*от\s+\d+",
]

# Демонтаж зданий сам по себе не наша заявка. Пропускаем его только при наличии
# земляных работ / вывоза / расчистки / последующего благоустройства.
demolition_building_patterns = [
    r"\bдемонтаж\w*\b.{0,80}\b(дом|здани|ангар|гараж|склад|сооружени)\w*\b",
    r"\bснос\w*\b.{0,80}\b(дом|здани|ангар|гараж|склад|сооружени)\w*\b",
]

demolition_allowed_context = [
    "земляные работы", "разработка грунта", "вывоз грунта", "вывоз земли",
    "вывоз строительного мусора", "погрузка", "расчистка территории",
    "подготовка участка", "благоустройство", "асфальтирование",
    "экскаватор-погрузчик", "экскаватор погрузчик",
]


def matches_any_regex(text, patterns):
    return any(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)

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
    r"\bавтовышк\w*\b",
    r"\bбашенн\w*\s+кран\w*\b",
    r"\bтрал\w*\b",
    r"\bдлинномер\w*\b",
    r"\bбуров\w*\b",
    r"\bассенизатор\w*\b",
    r"\bилосос\w*\b",
    r"\bбетононасос\w*\b",
    r"\bкомпрессор\w*\b",
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
# ДОПОЛНИТЕЛЬНАЯ ЛОГИКА FILTER v11
# ============================================================

BIG_LEAD_WORDS = [
    "комплексное благоустройство", "благоустройство под ключ",
    "строительство дороги", "строительство дорог", "асфальтирование",
]


AREA_PATTERN = re.compile(r"\b(\d[\d\s]{1,8})\s*(м2|м²|кв\.?\s*м)\b", re.IGNORECASE)
VOLUME_PATTERN = re.compile(r"\b(\d[\d\s]{1,8})\s*(м3|м³|куб(?:ов|а)?)\b", re.IGNORECASE)
MONEY_PATTERN = re.compile(r"\b(\d[\d\s]{2,12})\s*(₽|руб\.?|р\.)\b", re.IGNORECASE)
USERNAME_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_]{5,32})")

def extract_first_number(pattern, text):
    match = pattern.search(text or "")
    return match.group(0) if match else None

def extract_telegram_contact(text):
    match = USERNAME_PATTERN.search(text or "")
    return "@" + match.group(1) if match else None

def detect_big_lead(text_lower):
    reasons = []
    for word in BIG_LEAD_WORDS:
        if word in text_lower:
            reasons.append(word)
    area = extract_first_number(AREA_PATTERN, text_lower)
    volume = extract_first_number(VOLUME_PATTERN, text_lower)
    if area:
        digits = re.sub(r"\D", "", area)
        if digits and int(digits) >= 1000:
            reasons.append(f"крупная площадь: {area}")
    if volume:
        digits = re.sub(r"\D", "", volume)
        if digits and int(digits) >= 500:
            reasons.append(f"крупный объем: {volume}")
    return bool(reasons), list(dict.fromkeys(reasons))

def categorize_lead(text_lower, classification):
    equipment_found = classification["equipment_found"]
    work_found = classification["work_found"]
    if any(x in text_lower for x in ["самосвал", "howo", "хово", "8x4", "8×4", "6x4", "6×4"]):
        return "🚛 HOWO / САМОСВАЛ"
    if any(x in text_lower for x in ["асфальт", "благоустройство", "бордюр", "дорог", "парков"]):
        return "🛣 АСФАЛЬТ / БЛАГОУСТРОЙСТВО"
    if any(x in text_lower for x in ["землян", "грунт", "котлован", "транше", "планиров", "отсып", "засып"]):
        return "🚜 ЗЕМЛЯНЫЕ РАБОТЫ"
    if equipment_found and not work_found:
        return "🚜 ТЕХНИКА"
    return "📋 ПОДХОДЯЩАЯ ЗАЯВКА"



# ============================================================
# HOWO: СТАВКА / ПЛЕЧО / РЕЙСЫ / ТАБЛИЦА
# ============================================================

SHOULDER_PATTERN = re.compile(
    r"\b(?:плечо|расстояние)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*км\b",
    re.IGNORECASE,
)

RATE_M3_PATTERN = re.compile(
    r"\b(\d[\d\s]*(?:[.,]\d+)?)\s*(?:₽|руб(?:\.|лей)?|р\.?)?\s*/?\s*(?:м3|м³|куб)\b",
    re.IGNORECASE,
)

RATE_TRIP_PATTERN = re.compile(
    r"\b(\d[\d\s]*(?:[.,]\d+)?)\s*(?:₽|руб(?:\.|лей)?|р\.?)?\s*/?\s*(?:рейс|рейса)\b",
    re.IGNORECASE,
)

TRIPS_PATTERN = re.compile(
    r"\b(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s*рейс(?:а|ов)?\b",
    re.IGNORECASE,
)


def _to_float(value):
    if value is None:
        return None

    cleaned = str(value).replace(" ", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_howo_inputs(text):
    lower = normalize_text(text)

    shoulder_match = SHOULDER_PATTERN.search(lower)
    rate_m3_match = RATE_M3_PATTERN.search(lower)
    rate_trip_match = RATE_TRIP_PATTERN.search(lower)
    trips_match = TRIPS_PATTERN.search(lower)

    shoulder_km = (
        _to_float(shoulder_match.group(1))
        if shoulder_match
        else None
    )

    rate_m3 = (
        _to_float(rate_m3_match.group(1))
        if rate_m3_match
        else None
    )

    rate_trip = (
        _to_float(rate_trip_match.group(1))
        if rate_trip_match
        else None
    )

    trips_per_day = None

    if trips_match:
        first = _to_float(trips_match.group(1))
        second = _to_float(trips_match.group(2))

        if first is not None and second is not None:
            trips_per_day = (first + second) / 2
        else:
            trips_per_day = first

    return {
        "shoulder_km": shoulder_km,
        "rate_m3": rate_m3,
        "rate_trip": rate_trip,
        "trips_per_day": trips_per_day,
    }


def calculate_howo_economy(text):
    data = extract_howo_inputs(text)

    shoulder_km = data["shoulder_km"]
    rate_m3 = data["rate_m3"]
    rate_trip = data["rate_trip"]
    trips_per_day = data["trips_per_day"]

    revenue_trip = None

    if rate_m3 is not None:
        revenue_trip = rate_m3 * HOWO_BODY_M3
    elif rate_trip is not None:
        revenue_trip = rate_trip

    fuel_l_trip = None
    fuel_cost_trip = None
    after_fuel_trip = None

    if shoulder_km is not None:
        round_trip_km = shoulder_km * 2

        fuel_l_trip = (
            round_trip_km
            * HOWO_FUEL_L_PER_100KM
            / 100
        )

        fuel_cost_trip = fuel_l_trip * DIESEL_RUB_PER_L

        if revenue_trip is not None:
            after_fuel_trip = revenue_trip - fuel_cost_trip

    revenue_day = None
    fuel_cost_day = None
    after_fuel_day = None

    if trips_per_day is not None:
        if revenue_trip is not None:
            revenue_day = revenue_trip * trips_per_day

        if fuel_cost_trip is not None:
            fuel_cost_day = fuel_cost_trip * trips_per_day

        if after_fuel_trip is not None:
            after_fuel_day = after_fuel_trip * trips_per_day

    driver_day = (
        HOWO_DRIVER_MONTHLY_RUB / HOWO_WORK_DAYS_MONTH
        if HOWO_WORK_DAYS_MONTH > 0
        else 0
    )

    lease_day = (
        HOWO_LEASE_MONTHLY_RUB / HOWO_WORK_DAYS_MONTH
        if HOWO_WORK_DAYS_MONTH > 0
        else 0
    )

    repair_reserve_trip = None
    tire_cost_trip = None
    full_cost_trip = None
    profit_trip = None
    full_cost_day = None
    profit_day = None
    margin_pct = None

    if revenue_trip is not None:
        repair_reserve_trip = (
            revenue_trip * HOWO_REPAIR_RESERVE_PCT / 100
        )

    if shoulder_km is not None:
        round_trip_km = shoulder_km * 2
        tire_cost_trip = round_trip_km * HOWO_TIRE_RUB_PER_KM

    if trips_per_day and trips_per_day > 0:
        driver_per_trip = driver_day / trips_per_day
        lease_per_trip = lease_day / trips_per_day
    else:
        driver_per_trip = 0
        lease_per_trip = 0

    if (
        fuel_cost_trip is not None
        and repair_reserve_trip is not None
        and tire_cost_trip is not None
    ):
        full_cost_trip = (
            fuel_cost_trip
            + repair_reserve_trip
            + tire_cost_trip
            + HOWO_OTHER_RUB_PER_TRIP
            + driver_per_trip
            + lease_per_trip
        )

        if revenue_trip is not None:
            profit_trip = revenue_trip - full_cost_trip

            if revenue_trip > 0:
                margin_pct = profit_trip / revenue_trip * 100

    if trips_per_day and trips_per_day > 0 and full_cost_trip is not None:
        full_cost_day = full_cost_trip * trips_per_day

        if revenue_day is not None:
            profit_day = revenue_day - full_cost_day

    return {
        **data,
        "revenue_trip": revenue_trip,
        "fuel_l_trip": fuel_l_trip,
        "fuel_cost_trip": fuel_cost_trip,
        "after_fuel_trip": after_fuel_trip,
        "revenue_day": revenue_day,
        "fuel_cost_day": fuel_cost_day,
        "after_fuel_day": after_fuel_day,
        "driver_day": driver_day,
        "lease_day": lease_day,
        "repair_reserve_trip": repair_reserve_trip,
        "tire_cost_trip": tire_cost_trip,
        "other_cost_trip": HOWO_OTHER_RUB_PER_TRIP,
        "full_cost_trip": full_cost_trip,
        "profit_trip": profit_trip,
        "full_cost_day": full_cost_day,
        "profit_day": profit_day,
        "margin_pct": margin_pct,
    }


def format_money(value):
    if value is None:
        return "не рассчитано"

    return f"{value:,.0f}".replace(",", " ") + " ₽"


def format_number(value, suffix=""):
    if value is None:
        return "не указано"

    if float(value).is_integer():
        value_text = str(int(value))
    else:
        value_text = f"{value:.1f}"

    return value_text + suffix



def make_short_lead_id(text, phone, chat_name):
    raw = (
        (phone or "")
        + "|"
        + (chat_name or "")
        + "|"
        + normalize_lead_text(text)[:500]
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:8].upper()


def build_auto_reply(category):
    if category == "🚛 HOWO / САМОСВАЛ":
        return (
            "Добрый день. По вашей заявке есть свой самосвал HOWO 20 м³. "
            "Готовы обсудить маршрут, плечо, материал, ставку, количество рейсов "
            "и график работы. Напишите адрес погрузки/выгрузки и условия оплаты."
        )

    if category == "🚜 ТЕХНИКА РЯДОМ":
        return (
            "Добрый день. По вашей заявке есть своя техника: "
            "экскаватор-погрузчик, мини-погрузчик, самосвал HOWO 20 м³ и каток 4 т. "
            "Подскажите точный адрес, объём работ, дату начала и количество смен."
        )

    if category in {
        "🛣 АСФАЛЬТ / БЛАГОУСТРОЙСТВО",
        "🏗 КРУПНЫЙ ПОДРЯД",
    }:
        return (
            "Добрый день. Готовы рассмотреть ваш объект по асфальтированию, "
            "благоустройству и земляным работам. Есть своя техника и бригада. "
            "Пришлите адрес, ВОР/объёмы, сроки, условия по материалам и оплате — "
            "подготовим расчёт и КП."
        )

    return (
        "Добрый день. Увидел вашу заявку. Есть своя техника и бригада. "
        "Подскажите адрес, объём, сроки и условия оплаты."
    )



def assess_howo_profitability(howo):
    """
    Оценка только по тем данным, которые удалось извлечь из заявки.
    Если не хватает плеча/ставки — просим уточнить, а не выдумываем.
    """
    profit_trip = howo.get("profit_trip")
    margin_pct = howo.get("margin_pct")

    if profit_trip is None or margin_pct is None:
        return {
            "label": "⚪ НУЖНО УТОЧНИТЬ",
            "reason": "не хватает ставки, плеча или количества рейсов для полного расчёта",
        }

    if (
        margin_pct >= HOWO_GOOD_MARGIN_PCT
        and profit_trip >= HOWO_MIN_PROFIT_TRIP_RUB
    ):
        return {
            "label": "🟢 ВЫГОДНО",
            "reason": (
                f"маржа {margin_pct:.1f}% и прибыль "
                f"{format_money(profit_trip)} за рейс"
            ),
        }

    if (
        margin_pct >= HOWO_BORDER_MARGIN_PCT
        and profit_trip > 0
    ):
        return {
            "label": "🟡 НА ГРАНИ",
            "reason": (
                f"маржа {margin_pct:.1f}% и прибыль "
                f"{format_money(profit_trip)} за рейс"
            ),
        }

    return {
        "label": "🔴 НЕВЫГОДНО",
        "reason": (
            f"маржа {margin_pct:.1f}% и прибыль "
            f"{format_money(profit_trip)} за рейс"
        ),
    }


def ensure_leads_csv():
    path = Path(LEADS_CSV_PATH)

    if path.parent != Path("."):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    if path.exists() and path.stat().st_size > 0:
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=LEADS_CSV_HEADERS,
            delimiter=";",
        )
        writer.writeheader()


def append_lead_to_csv(
    *,
    category,
    priority,
    score,
    lead_type,
    geo_line,
    chat_name,
    chat_username,
    phone,
    tg_contact,
    equipment_found,
    work_found,
    contract_found,
    material_found,
    text,
    message_link,
    howo,
    howo_assessment,
    lead_id,
):
    ensure_leads_csv()

    normalized = normalize_text(text)

    area = extract_first_number(
        AREA_PATTERN,
        normalized,
    )

    volume = extract_first_number(
        VOLUME_PATTERN,
        normalized,
    )

    price = extract_first_number(
        MONEY_PATTERN,
        normalized,
    )

    row = {
        "Дата": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Категория": category,
        "Приоритет": priority,
        "Балл": score,
        "Тип заявки": lead_type,
        "География": geo_line,
        "Группа": chat_name,
        "Username группы": chat_username or "",
        "Телефон": phone or "",
        "Telegram контакт": tg_contact or "",
        "Техника": ", ".join(equipment_found),
        "Работы": ", ".join(work_found),
        "Подряд": ", ".join(contract_found),
        "Материалы": ", ".join(material_found),
        "Площадь": area or "",
        "Объем": volume or "",
        "Цена/ставка": price or "",
        "Плечо км": howo["shoulder_km"] or "",
        "Ставка руб/м3": howo["rate_m3"] or "",
        "Ставка руб/рейс": howo["rate_trip"] or "",
        "Рейсов/день": howo["trips_per_day"] or "",
        "Кузов HOWO м3": HOWO_BODY_M3,
        "Расход л/100км": HOWO_FUEL_L_PER_100KM,
        "Дизель руб/л": DIESEL_RUB_PER_L,
        "Выручка/рейс": howo["revenue_trip"] or "",
        "Топливо л/рейс": howo["fuel_l_trip"] or "",
        "Топливо руб/рейс": howo["fuel_cost_trip"] or "",
        "Остаток после топлива/рейс": howo["after_fuel_trip"] or "",
        "Выручка/день": howo["revenue_day"] or "",
        "Топливо руб/день": howo["fuel_cost_day"] or "",
        "Остаток после топлива/день": howo["after_fuel_day"] or "",
        "Зарплата водителя/день": howo["driver_day"] or "",
        "Лизинг HOWO/день": howo["lease_day"] or "",
        "Ремонтный резерв/рейс": howo["repair_reserve_trip"] or "",
        "Резина/рейс": howo["tire_cost_trip"] or "",
        "Прочее/рейс": howo["other_cost_trip"] or "",
        "Полная себестоимость/рейс": howo["full_cost_trip"] or "",
        "Прибыль/рейс": howo["profit_trip"] or "",
        "Полная себестоимость/день": howo["full_cost_day"] or "",
        "Прибыль/день": howo["profit_day"] or "",
        "Маржа %": howo["margin_pct"] or "",
        "Оценка HOWO": howo_assessment["label"],
        "Причина оценки HOWO": howo_assessment["reason"],
        "ID лида": lead_id,
        "Ссылка": message_link or "",
        "Текст заявки": text,
        "Статус": "Новый",
    }

    with Path(LEADS_CSV_PATH).open(
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=LEADS_CSV_HEADERS,
            delimiter=";",
        )
        writer.writerow(row)


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
    material_found = classification["material_found"]

    # Явное намерение заказать / найти исполнителя — главный сигнал.
    if find_matches(text, request_words):
        score += 2

    if any(word in text for word in ["срочно", "сегодня", "прямо сейчас", "на сейчас", "в течение часа"]):
        score += 3
    elif any(word in text for word in ["завтра", "на завтра", "утром"]):
        score += 2

    if len(work_found) >= 3:
        score += 3
    elif work_found:
        score += 3

    if any(word in text for word in ["экскаватор-погрузчик", "экскаватор погрузчик", "jcb", "джсб"]):
        score += 4
    elif any(word in text for word in ["мини-погрузчик", "мини погрузчик", "минипогрузчик", "bobcat", "бобкэт", "бобкат", "самосвал", "каток"]):
        score += 3

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
# MINI CRM: СТАТУСЫ ЛИДОВ ЧЕРЕЗ КОМАНДЫ БОТУ
# ============================================================

CRM_STATUS_MAP = {
    "called": "Позвонил",
    "wait": "Жду ответ",
    "calc": "Считаю",
    "kp": "Отправил КП",
    "work": "В работе",
    "refuse": "Отказ",
}


def update_lead_status(lead_id, new_status):
    path = Path(LEADS_CSV_PATH)

    if not path.exists():
        return False, "Таблица лидов ещё не создана."

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter=";",
        )
        rows = list(reader)
        fieldnames = reader.fieldnames or LEADS_CSV_HEADERS

    found = False

    for row in rows:
        if (
            row.get("ID лида", "")
            .strip()
            .upper()
            == lead_id.strip().upper()
        ):
            row["Статус"] = new_status
            found = True
            break

    if not found:
        return False, f"Лид {lead_id} не найден."

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    return True, f"{lead_id}: статус → {new_status}"


def get_bot_updates(offset=None):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    params = {
        "timeout": 20,
        "allowed_updates": '["message"]',
    }

    if offset is not None:
        params["offset"] = offset

    full_url = url + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(
            full_url,
            timeout=30,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        if not data.get("ok"):
            return []

        return data.get("result", [])

    except Exception as error:
        print(
            "⚠️ CRM getUpdates:",
            repr(error),
            flush=True,
        )
        return []


async def crm_bot_loop():
    offset = None

    while True:
        updates = await asyncio.to_thread(
            get_bot_updates,
            offset,
        )

        for update in updates:
            offset = update["update_id"] + 1

            message = update.get("message") or {}
            chat = message.get("chat") or {}
            text = (message.get("text") or "").strip()

            if str(chat.get("id")) != str(bot_chat_id):
                continue

            if not text.startswith("/status "):
                continue

            parts = text.split()

            if len(parts) != 3:
                await asyncio.to_thread(
                    send_bot_part,
                    "Формат: /status ID called|wait|calc|kp|work|refuse",
                )
                continue

            _, lead_id, status_code = parts

            status_name = CRM_STATUS_MAP.get(
                status_code.lower()
            )

            if not status_name:
                await asyncio.to_thread(
                    send_bot_part,
                    "Статусы: called, wait, calc, kp, work, refuse",
                )
                continue

            ok, result_text = await asyncio.to_thread(
                update_lead_status,
                lead_id,
                status_name,
            )

            await asyncio.to_thread(
                send_bot_part,
                ("✅ " if ok else "❌ ") + result_text,
            )

        await asyncio.sleep(2)


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

        # Жёстко отсекаем тендеры/субподряд/закупки.
        if matches_any_regex(text_lower, blocked_procurement_patterns):
            print("REJECT: тендер/субподряд/закупка", flush=True)
            return

        # Отсекаем новости, отчёты и публикации о уже выполненных работах.
        if matches_any_regex(text_lower, news_completed_patterns):
            print("REJECT: новость/отчёт/выполненные работы", flush=True)
            return

        # Отсекаем рекламу чужих услуг и предложение своей техники.
        if matches_any_regex(text_lower, provider_ad_patterns):
            print("REJECT: реклама исполнителя/техники", flush=True)
            return

        # Демонтаж зданий пропускаем только если есть смежные наши работы.
        if matches_any_regex(text_lower, demolition_building_patterns):
            if not any(word in text_lower for word in demolition_allowed_context):
                print("REJECT: демонтаж зданий без наших смежных работ", flush=True)
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
            lead_type = "🏗 РАБОТЫ"
            geo_status, location_found = analyze_geo_for_work(
                text_lower
            )

            if geo_status == "outside":
                print(
                    "REJECT: работы явно вне Москвы/МО",
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
        # КОНТАКТЫ / ДВА ПОТОКА
        # ----------------------------------------------------
        phone = find_phone(text)
        tg_contact = extract_telegram_contact(text)
        big_lead, big_reasons = detect_big_lead(text_lower)

        # Для качества оставляем заявки, где есть прямой контакт:
        # телефон или Telegram пользователя в тексте.
        if not phone and not tg_contact:
            print("REJECT: нет телефона или Telegram-контакта", flush=True)
            return

        print("Телефон:", phone or "нет", flush=True)
        print("Telegram-контакт:", tg_contact or "нет", flush=True)
        print("Крупный лид:", big_lead, big_reasons, flush=True)

        # ----------------------------------------------------
        # АНТИДУБЛЬ
        # ----------------------------------------------------
        contact_key = phone or tg_contact or f"{chat_username or chat_name}:{event.id}"

        duplicate, lead_key = is_duplicate_lead(
            text,
            contact_key,
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

        # В Telegram отправляем только сильные заявки 7/10 и выше.
        if score < 7:
            print(f"REJECT: низкий приоритет {score}/10", flush=True)
            return

        if score >= 9:
            priority = "🔥🔥🔥 СРОЧНАЯ ЗАЯВКА"
        elif score >= 8:
            priority = "🔥🔥 ХОРОШАЯ ЗАЯВКА"
        else:
            priority = "🔥 ПОДХОДИТ"

        category = categorize_lead(text_lower, classification)

        howo = calculate_howo_economy(text)

        howo_assessment = assess_howo_profitability(
            howo
        )

        lead_id = make_short_lead_id(
            text,
            phone,
            chat_name,
        )

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

        area_or_volume = (
            extract_first_number(AREA_PATTERN, text_lower)
            or extract_first_number(VOLUME_PATTERN, text_lower)
            or "не указан"
        )
        price_line = extract_first_number(MONEY_PATTERN, text_lower) or "не указана"

        # Причина приоритета — одна короткая строка.
        reason_parts = []
        if equipment_found:
            reason_parts.append("нужна наша техника")
        if work_found:
            reason_parts.append("наши работы")
        if location_found:
            reason_parts.append("подходящая география")
        if phone or tg_contact:
            reason_parts.append("есть контакт")
        priority_reason = ", ".join(reason_parts[:3]) or "подходящая заявка"

        alert = (
            f"{priority}\n"
            f"⭐ Приоритет: {score}/10\n\n"
            f"🚧 Вид работ: {category}\n"
            f"📍 Район: {geo_line}\n"
            f"📐 Объём/площадь: {area_or_volume}\n"
            f"💰 Бюджет/ставка: {price_line}\n"
            f"📞 Телефон: {phone or 'нет'}\n"
            f"💬 Telegram: {tg_contact or 'нет'}\n\n"
            f"📝 Текст заявки:\n{text}\n\n"
            f"Причина: {priority_reason}"
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

            try:
                append_lead_to_csv(
                    category=category,
                    priority=priority,
                    score=score,
                    lead_type=lead_type,
                    geo_line=geo_line,
                    chat_name=chat_name,
                    chat_username=chat_username,
                    phone=phone,
                    tg_contact=tg_contact,
                    equipment_found=equipment_found,
                    work_found=work_found,
                    contract_found=contract_found,
                    material_found=material_found,
                    text=text,
                    message_link=message_link,
                    howo=howo,
                    howo_assessment=howo_assessment,
                    lead_id=lead_id,
                )

                print(
                    f"📊 ЗАЯВКА ЗАПИСАНА В ТАБЛИЦУ: {LEADS_CSV_PATH}",
                    flush=True,
                )

            except Exception as table_error:
                print(
                    "⚠️ НЕ УДАЛОСЬ ЗАПИСАТЬ В ТАБЛИЦУ:",
                    repr(table_error),
                    flush=True,
                )

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
        "🚀 МОНИТОР ЗАЯВОК ЗАПУСКАЕТСЯ — FILTER v11",
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
        "✅ МОНИТОР ЗАЯВОК ЗАПУЩЕН — СТРОГИЙ ФИЛЬТР\n\n"
        f"Всего видно групп/каналов: {group_count}\n"
        f"Из нашей собранной базы видно: {priority_visible}\n\n"
        "📌 Отправляются только заявки 7/10 и выше.\n"
        "🚫 Тендеры, субподряды, реклама услуг, вакансии, новости и отчёты блокируются.\n"
        "🚫 Заявки на чужую технику блокируются.\n\n"
        "🚜 Наша техника: экскаватор-погрузчик, мини-погрузчик, HOWO/самосвал, каток.\n"
        "🏗 Наши работы: асфальтирование, благоустройство, основания, бордюры, земляные работы, вывоз/погрузка грунта.\n\n"
        "📍 Техника/материал: локальная зона. Работы: Москва и Московская область.\n"
        "📞 Для отправки нужен телефон или Telegram-контакт.\n"
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

    asyncio.create_task(
        crm_bot_loop()
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
