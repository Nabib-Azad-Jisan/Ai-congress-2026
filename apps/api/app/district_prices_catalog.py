"""Commodity vocabulary for market evidence and district names from the BAMIS directory."""
import re
import unicodedata

from .farmer_chat_sources import _DISTRICTS, _key


# IDs represent goods sold on the market. In particular, husked and unhusked rice
# have separate prices. Only declared aliases can classify an existing listing.
_CROPS = [
    ("tomato", "Tomato", "টমেটো", "tomatoes|cherry tomato|cherry tomatoes|টমাটো"),
    ("potato", "Potato", "আলু", "potatoes"),
    ("sweet_potato", "Sweet potato", "মিষ্টি আলু", "sweet potatoes|মিষ্টি আলু"),
    ("paddy", "Paddy (unhusked rice)", "ধান", "paddy|rough rice|unmilled rice|unhusked rice|paddy rice|boro paddy|aman paddy|aus paddy|বোরো ধান|আমন ধান|আউশ ধান"),
    ("rice", "Milled rice", "চাল", "rice|white rice|brown rice|parboiled rice|সিদ্ধ চাল|আতপ চাল"),
    ("maize", "Maize", "ভুট্টা", "corn|maize grain|corn grain|ভুট্টার দানা"),
    ("wheat", "Wheat", "গম", "wheat grain"),
    ("mustard", "Mustard seed", "সরিষা বীজ", "mustard|mustard seeds|সরিষা|সরিষার বীজ|সরষে"),
    ("lentil", "Lentil", "মসুর ডাল", "lentils|মসুর|মসুরের ডাল"),
    ("mung_bean", "Mung bean", "মুগ ডাল", "mung beans|green gram|মুগ"),
    ("chickpea", "Chickpea", "ছোলা", "chickpeas|bengal gram"),
    ("groundnut", "Groundnut", "চিনাবাদাম", "groundnuts|peanut|peanuts|চিনা বাদাম"),
    ("soybean", "Soybean", "সয়াবিন", "soybeans|soya bean|soya beans"),
    ("onion", "Onion", "পেঁয়াজ", "onions|পিঁয়াজ"),
    ("garlic", "Garlic", "রসুন", ""),
    ("ginger", "Ginger", "আদা", ""),
    ("turmeric", "Fresh turmeric", "কাঁচা হলুদ", "turmeric root|raw turmeric"),
    ("chilli", "Fresh chilli", "কাঁচা মরিচ", "chilli|chili|chilies|chillies|green chilli|green chillies|green chili|chili pepper|chilli pepper|chili peppers|chilli peppers|মরিচ|কাঁচামরিচ|লঙ্কা"),
    ("dry_chilli", "Dried chilli", "শুকনা মরিচ", "dried chillies|dry chilli|dry chili|dried chili|শুকনো মরিচ"),
    ("bell_pepper", "Bell pepper", "ক্যাপসিকাম", "bell peppers|sweet pepper|sweet peppers|capsicum"),
    ("brinjal", "Brinjal", "বেগুন", "brinjals|eggplant|eggplants|aubergine|aubergines"),
    ("cucumber", "Cucumber", "শসা", "cucumbers"),
    ("carrot", "Carrot", "গাজর", "carrots"),
    ("pumpkin", "Pumpkin", "মিষ্টি কুমড়া", "pumpkins|কুমড়া"),
    ("squash", "Squash", "স্কোয়াশ", "butternut squash"),
    ("bottle_gourd", "Bottle gourd", "লাউ", "bottle gourds"),
    ("ash_gourd", "Ash gourd", "চাল কুমড়া", "ash gourds|wax gourd|চালকুমড়া"),
    ("pointed_gourd", "Pointed gourd", "পটল", "pointed gourds"),
    ("bitter_gourd", "Bitter gourd", "করলা", "bitter gourds|bitter melon|উচ্ছে"),
    ("okra", "Okra", "ঢেঁড়স", "lady's finger|ladies' fingers|ঢ্যাঁড়স"),
    ("cabbage", "Cabbage", "বাঁধাকপি", "cabbages"),
    ("cauliflower", "Cauliflower", "ফুলকপি", "cauliflowers"),
    ("spinach", "Spinach", "পালং শাক", "পালংশাক"),
    ("radish", "Radish", "মুলা", "radishes|মূলা"),
    ("banana", "Banana", "কলা", "bananas"),
    ("mango", "Mango", "আম", "mangoes|mangos"),
    ("guava", "Guava", "পেয়ারা", "guavas"),
    ("jackfruit", "Jackfruit", "কাঁঠাল", "jackfruits"),
    ("papaya", "Papaya", "পেঁপে", "papayas"),
    ("pineapple", "Pineapple", "আনারস", "pineapples"),
    ("litchi", "Litchi", "লিচু", "litchis|lychee|lychees"),
    ("jujube", "Jujube", "বরই", "jujubes|কুল"),
    ("lemon", "Lemon", "লেবু", "lemons"),
    ("watermelon", "Watermelon", "তরমুজ", "watermelons"),
    ("apple", "Apple", "আপেল", "apples"),
    ("orange", "Orange", "কমলা", "oranges"),
    ("grape", "Grape", "আঙুর", "grapes|আঙ্গুর"),
    ("peach", "Peach", "পীচ", "peaches|পিচ"),
    ("cherry", "Cherry", "চেরি", "cherries"),
    ("strawberry", "Strawberry", "স্ট্রবেরি", "strawberries"),
    ("sugarcane", "Sugarcane", "আখ", "sugar cane"),
    ("cotton", "Cotton", "তুলা", ""),
    ("jute", "Jute", "পাট", ""),
]


def _commodity_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("_", " ").replace("-", " ").split())


COMMODITY_OPTIONS = [{"id": cid, "en": en, "bn": bn} for cid, en, bn, _ in _CROPS]
COMMODITY_ALIASES = {
    alias: cid for cid, en, bn, aliases in _CROPS
    for alias in (cid, en, bn, *aliases.split("|")) if alias
}
_COMMODITY_BY_KEY = {_commodity_key(alias): cid for alias, cid in COMMODITY_ALIASES.items()}
# Exact names and a few descriptive prefixes support old listings without
# classifying processed goods, mixed lots, or unrelated crops by substring.
_PREFIXES = {"fresh", "organic", "local", "ripe", "farm", "তাজা", "দেশি", "দেশী", "জৈব", "পাকা"}


def canonical_commodity(value: str | None) -> str | None:
    key = _commodity_key(value or "")
    while key:
        if key in _COMMODITY_BY_KEY:
            return _COMMODITY_BY_KEY[key]
        first, _, key = key.partition(" ")
        if first not in _PREFIXES:
            break
    return None


# Reuse the same bilingual 64-district mapping as the extension-service lookup.
DISTRICT_OPTIONS = [
    {"id": place.name, "en": place.name, "bn": place.bangla}
    for place in sorted(set(_DISTRICTS.values()), key=lambda place: place.name)
]
DISTRICT_ALIASES = {alias: place.name for alias, place in _DISTRICTS.items()}
for option in DISTRICT_OPTIONS:
    DISTRICT_ALIASES.update({option["en"]: option["id"], option["bn"]: option["id"]})


def canonical_district(value: str | None) -> str | None:
    place = re.sub(r"(?:\s+(?:district|জেলা))?(?:\s*,\s*(?:bangladesh|বাংলাদেশ))?$", "", (value or "").strip(), flags=re.I)
    return DISTRICT_ALIASES.get(_key(place))
