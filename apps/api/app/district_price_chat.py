"""Ground district price comparisons in marketplace aggregates and the farmer's own offer."""
import re
import unicodedata
from decimal import Decimal

from .district_prices_catalog import (
    COMMODITY_ALIASES, COMMODITY_OPTIONS, DISTRICT_ALIASES, DISTRICT_OPTIONS,
    canonical_commodity, canonical_district,
)
from .services import calculate

DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
BENGALI_DIGITS = str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')
NUMBER = r'(?<![\d.,-])(\d{1,9}(?:\.\d{1,3})?)(?![\d.,]\d)'
CURRENCY = r'(?:৳|bdt|tk\.?|taka|টাকা)'
UNITS = {
    'kg': ('kg','kgs','kilogram','kilograms','kilo','kilos','কেজি','কিলোগ্রাম'),
    'g': ('g','gram','grams','গ্রাম'),
    'piece': ('piece','pieces','পিস','টি'),
    'bundle': ('bundle','bundles','আঁটি','আটি','বান্ডিল'),
    'crate': ('crate','crates','ক্রেট'),
}
UNIT_PATTERN = '|'.join(re.escape(u) for u in sorted((u for items in UNITS.values() for u in items),key=len,reverse=True))
UNIT = rf'({UNIT_PATTERN})(?![a-z])'
RATE_PATTERNS = (
    rf'(?:{CURRENCY}\s*)?{NUMBER}\s*(?:{CURRENCY}\s*)?(?:/|\bper\b|\ba\b|প্রতি)\s*{UNIT}',
    rf'(?:প্রতি|per)\s*{UNIT}\s*(?:দর|দাম|price|is|at|of)?\s*(?:{CURRENCY}\s*)?{NUMBER}\s*{CURRENCY}',
    rf'{UNIT}\s*(?:প্রতি|দরে|করে|তে)\s*(?:{CURRENCY}\s*)?{NUMBER}\s*{CURRENCY}',
)
# Remove freight from the buyer's offer before interpreting any currency rate.
FARE = re.compile(
    r'(?:transport(?:ation)?(?:\s+(?:cost|fare|fee))?s?|freight|fare|ভাড়া|ভাড়া|পরিবহন খরচ)\s*'
    r'(?:costs?|is|of|হলে|বাবদ)?\s*(?:' + CURRENCY + r'\s*)?' + NUMBER +
    r'(?:\s*' + CURRENCY + r')?(?:\s*(?:/|\bper\b|প্রতি)\s*([a-z]+|[ঀ-৿]+))?'
)
UNSUPPORTED_UNIT = re.compile(
    r'\b(?:maunds?|tons?|tonnes?)\b|(?:/|\bper\s+|প্রতি\s*)'
    r'(?:bags?|sacks?|boxes|box|baskets?|pounds?|lbs?|litres?|liters?|মণ|মন|বস্তা|ঝুড়ি|লিটার)'
)

BOARD_WORDS = re.compile(r'district (?:price|market)|price board|median|recent (?:local )?(?:sales|prices|orders|listings)|'
                        r'asking prices?|agreed prices?|local (?:sales|orders|listings|prices)|'
                        r'জেলার (?:বাজার)?দ[ারম]|জেলার .*দাম|দরপট্ট|মূল্যতালিকা|দাম বোর্ড|মধ্যমা|সাম্প্রতিক (?:অর্ডার|বিক্রি|দর|দাম)|'
                        r'জেলায় .*দাম|স্থানীয় (?:দর|বাজারদর|অর্ডার|দাম)|jelar (?:dam|dor)',re.I)
OFFICIAL = re.compile(r'\b(?:official|wholesale|retail|government|farm.gate)\b|সরকারি|পাইকারি|খুচরা',re.I)
TWO_BUYERS = re.compile(r'\b(?:nearer|farther|further|nearby market|buyer [ab]|first buyer|second buyer|two (?:buyers|markets))\b|'
                        r'দূরের বাজার|কাছের বাজার|দুই ক্রেতা|দুই বাজার',re.I)


def _name_in(text, aliases):
    for alias in sorted(aliases,key=len,reverse=True):
        key = unicodedata.normalize('NFC',alias).casefold()
        # Bengali attaches case endings directly to the noun (e.g. গাজীপুরে, টমেটোর).
        suffix = r'(?:ের|য়ের|য়ের|র|ে|য়|য়)?' if re.search('[ঀ-৿]',key) else r'(?:es|s)?'
        if re.search(r'(?<![\wঀ-৿])'+re.escape(key)+suffix+r'(?![\wঀ-৿])',text):
            return aliases[alias]
    return None


def _unit(word):
    return next((kind for kind, aliases in UNITS.items() if word in aliases), None)


def _offer(text):
    if re.search(r'[$€£]|\b(?:usd|eur|rupees?|dollars?)\b',text):
        return None
    for index, pattern in enumerate(RATE_PATTERNS):
        matches = list(re.finditer(pattern,text))
        if len(matches)>1:
            return None
        if matches:
            first,second = matches[0].groups()
            number,unit = (first,second) if index==0 else (second,first)
            value = Decimal(number)
            if value>0:
                return value,_unit(unit)
    return None


def _display(options, value, bn):
    return next((item['bn' if bn else 'en'] for item in options if item['id']==value), value)


def _proceeds(text, rate, fare, bn):
    """Use one saleable weight and a total fare or a compatible freight rate."""
    quantities = re.findall(NUMBER + r'\s*(?:kg\b|কেজি)', text)
    if (len(quantities) != 1 or not fare or
            re.search(r'loss|spoilage|ক্ষতি|নষ্ট|handling|fees?', text)):
        return None
    weight = quantities[0]
    cost, basis = fare.groups()
    total_fare = Decimal(cost)
    if basis:
        if _unit(basis) != 'kg':
            return ('এই চালানের মোট পরিবহন খরচ কত টাকা?' if bn else
                    'What is the total transport cost for this shipment?')
        total_fare *= Decimal(weight)
    try:
        totals = calculate(str(rate), weight, 0, str(total_fare), 0, 0)
    except ValueError:
        return None
    net = totals['net_bdt']
    if bn:
        return f'বিক্রিযোগ্য ওজন {weight} কেজি ও পরিবহন খরচ ৳{total_fare} ধরলে হাতে থাকবে ৳{net}, অন্য খরচ বাদ দেওয়ার আগে।'
    return f'For {weight} saleable kg, you would receive ৳{net} after ৳{total_fare} transport, before other costs.'


def district_market_turn(question, plan, previous, plot_crop, farm_district, lang, lookup):
    """Return (reply, scope, source detail) for board requests; leave other market tools in charge."""
    if lookup is None:
        return None
    text = unicodedata.normalize('NFC',question).translate(DIGITS).casefold()
    bn = lang=='bn'
    def t(en, bengali):
        return bengali if bn else en

    # Wholesale and retail reference queries stay with the authenticated quote/DAM lookup.
    if OFFICIAL.search(text) or re.search(r'\bDAM\b',question) or TWO_BUYERS.search(text):
        return None
    explicit_crop = _name_in(text,COMMODITY_ALIASES)
    explicit_district = _name_in(text,DISTRICT_ALIASES)
    fares = list(FARE.finditer(text))
    sale_text = FARE.sub(' ', text)
    offer = _offer(sale_text)
    contextual = bool(previous) and (
        explicit_crop or explicit_district or offer or previous.get('awaiting') or
        re.search(r'what about|how about|instead|take home|transport|sell|\bper\b|প্রতি|তাহলে|পরিবহন|ভাড়া|ভাড়া|হাতে|বিক্রি',text))
    explicit_board = BOARD_WORDS.search(text)
    inferred_trade = plan.get('trade_type') in ('retail', 'wholesale', 'farm-gate')
    if inferred_trade and not (explicit_board or contextual or plan.get('district_board') is True):
        return None
    board_question = plan.get('district_board') is True or explicit_board or (
        explicit_district and (offer or re.search(r'price|\b(?:dam|daam|dor)\b|দাম|বাজারদর|কত দরে',text)))
    if not board_question and not contextual:
        return None
    named_crop = plan.get('crop') if isinstance(plan.get('crop'),str) else None
    named_place = plan.get('district') if isinstance(plan.get('district'),str) else None
    crop = canonical_commodity(explicit_crop or named_crop or previous.get('crop',plot_crop) or '')
    district = canonical_district(explicit_district or named_place or previous.get('district',farm_district) or '')
    unit_word = re.search(r'(?:/|\bper\s+|প্রতি\s*)'+UNIT,sale_text)
    planned_unit = plan.get('board_unit') if isinstance(plan.get('board_unit'),str) else None
    unit = offer[1] if offer else (_unit(unit_word[1]) if unit_word else planned_unit)
    unit = unit or (previous.get('unit') if previous.get('crop')==crop else None) or 'kg'
    scope = {'crop':crop,'district':district,'unit':'kg' if unit=='g' else unit}
    if plot_crop=='rice' and not (explicit_crop or named_crop or previous.get('crop')) and crop=='rice':
        scope.update(crop=None,awaiting=True)
        return t('Are you selling unhusked paddy or milled rice?', 'আপনি ধান বিক্রি করছেন, নাকি চাল?'),scope,None
    if not crop or not district or unit not in UNITS or UNSUPPORTED_UNIT.search(sale_text):
        scope['awaiting'] = True
        if not crop:
            question = t('Which crop would you like to look up?', 'কোন ফসলের বাজারদর দেখতে চান?')
        elif not district:
            question = t('Which Bangladesh district should I check?', 'বাংলাদেশের কোন জেলার বাজারদর দেখতে চান?')
        else:
            scope['unit'] = None
            question = t('What is the comparable price per kg, piece, bundle, or crate?', 'প্রতি কেজি, পিস, আঁটি বা ক্রেটের দর কত?')
        return question,scope,None

    board = lookup(crop,district,scope['unit'])
    dates = f"{board['window_start']} – {board['window_end']}"
    product, place = _display(COMMODITY_OPTIONS,crop,bn), _display(DISTRICT_OPTIONS,district,bn)
    price_unit = {'kg':'কেজি','piece':'পিস','bundle':'আঁটি','crate':'ক্রেট'}[scope['unit']] if bn else scope['unit']
    source = f"KrishiMarket · {place} · {product} · {dates} · BDT/{scope['unit']}"
    lines = [t(f'{product} in {place}, {dates} (KrishiMarket).',f'{place} জেলায় {product} · {dates} (কৃষিমার্কেট)।')]
    for kind in ('asking','agreed'):
        row = board[kind]
        n, median = row['count'],row['median_bdt']
        if median is None:
            notice = (t('Not enough local listings yet.','এখনও পর্যাপ্ত স্থানীয় বিজ্ঞাপন নেই।') if kind=='asking' else
                      t('Not enough local orders yet.','এখনও পর্যাপ্ত স্থানীয় অর্ডার নেই।'))
            lines.append(notice+' '+t(f"{n} of {board['min_samples']} needed.",f"প্রয়োজন {board['min_samples']}টি, পাওয়া গেছে {n}টি।"))
        elif kind=='asking':
            lines.append(t(f'Median asking price: ৳{median}/{price_unit} from {n} listings.',
                           f'{n}টি বিজ্ঞাপনে চাওয়া দামের মধ্যমা ৳{median}/{price_unit}।'))
        else:
            lines.append(t(f'Median agreed price: ৳{median}/{price_unit} from {n} confirmed orders.',
                           f'{n}টি নিশ্চিত অর্ডারে সম্মত দামের মধ্যমা ৳{median}/{price_unit}।'))
    rate = None
    if offer:
        rate = offer[0] * (1000 if offer[1]=='g' else 1)
    elif all(previous.get(key)==scope[key] for key in ('crop','district','unit')) and previous.get('offer'):
        rate = Decimal(previous['offer'])
    if rate is not None:
        scope['offer'] = str(rate)
        if offer and board['agreed']['median_bdt'] is not None:
            delta = rate - Decimal(board['agreed']['median_bdt'])
            if delta:
                relation = t('above','বেশি') if delta>0 else t('below','কম')
                lines.append(t(f'Your offer is ৳{abs(delta):.2f}/{price_unit} {relation} the agreed median.',
                               f'আপনার প্রস্তাব সম্মত দামের মধ্যমা থেকে প্রতি {price_unit} ৳{abs(delta):.2f} {relation}।'))
            else:
                lines.append(t('Your offer matches the agreed median.','আপনার প্রস্তাব সম্মত দামের মধ্যমার সমান।'))
        if scope['unit']=='kg' and len(fares) == 1:
            net = _proceeds(sale_text, rate, fares[0], bn)
            if net:
                lines.append(net)
    reply = '\n'.join(lines)
    return reply.translate(BENGALI_DIGITS) if bn else reply,scope,source
