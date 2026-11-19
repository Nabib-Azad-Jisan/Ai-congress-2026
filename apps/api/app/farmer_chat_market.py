"""Two-buyer comparison using confirmed farmer inputs, stored as JSON-safe decimals.

An extra amount is always the farther/second buyer minus the nearer/first buyer.
Trip expenses are whole-trip BDT unless a farmer explicitly gives a per-kg rate.
"""
import re
import unicodedata
from decimal import Decimal


_BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_EN_DIGITS = "0123456789"
_NUMBER = re.compile(r"(?<![\d.])[+-]?\d+(?:\.\d+)?(?![\d.])")
_SIDES = ("near", "far", "extra")

# Convert unit, role, and expense words to a small vocabulary. Names and other
# text survive, so unknown numbers aren't silently turned into money or weights.
_VOCAB = {
    "near": r"\b(?:first|local|nearby|nearer|nearest|near|kacher|kache|kachher|kaser)\b|"
            r"\b(?:buyer|market)\s*a\b|কাছের|কাছাকাছি|কাছে|নিকটস্থ|স্থানীয়|প্রথম",
    "far": r"\b(?:second|distant|farther|further|faraway|far|durer|dure|durerhaat)\b|"
           r"\b(?:buyer|market)\s*b\b|দূরের|দূরে|দুরের|দুরে|দ্বিতীয়",
    "transport": r"\b(?:transport(?:ation)?|freight|fare|delivery|trucking|trip|bhara|vara|bhada|poribohon)\b|"
                 r"পরিবহ[ণন](?:ের)?|ভাড়[াায়]*|ভারা|যাতায়াত|গাড়িখরচ",
    "handling": r"\b(?:handling|loading|unloading|labour|labor|packing|commission|fees?)\b|"
                r"হ্যান্ডলিং|লোডিং|আনলোডিং|মজুরি|কমিশন|প্যাকিং",
    "kg each": r"\b(?:proti|per)\s*(?:kg|kilo(?:gram)?s?)\b|প্রতি\s*কেজি(?:তে)?|"
               r"কেজি\s*(?:প্রতি|পিছু)|কেজিতে|কেজিদরে|\bkg\s*(?:te|proti|pichu)\b",
    "kg": r"\b(?:kilograms?|kilos?|keji)\b|কিলোগ্রাম|কেজি",
    "tk": r"[৳]|টাক(?:ায়|ার|া)|\b(?:BDT|taka|tk)\b",
    "more": r"\b(?:more|higher|extra|additional|difference|premium|beshi|besi|baroti)\b|বেশি|বেশী|অতিরিক্ত|বাড়তি|পার্থক্য|আরও|আরো",
    "less": r"\b(?:less|lower|cheaper|kom)\b|কম",
    "price": r"\b(?:prices?|quotes?|rates?|bid[s]?|pay[s]?|offer[s]?|dam|daam|dor)\b|দাম|দর|দেবে|দিচ্ছে",
    "market": r"\b(?:markets?|bazare?|bajare?|haat)\b|বাজার(?:ের|ে)?|হাটে?",
    "buyer": r"\b(?:buyers?|kreta)\b|ক্রেতা",
    "compare": r"\bcompar(?:e|ing|ison)\b|তুলনা",
    "cost": r"\b(?:expenses?|costs?|khoroch|khoroc)\b|খরচ",
    "equal": r"\b(?:same|equal|identical|soman)\b|সমান|একই",
    "zero": r"\b(?:none|zero|free|no)\b|নেই|নাই|লাগবে না",
}


def _normalize(message: str) -> str:
    text = unicodedata.normalize("NFKC", message.lower()).translate(str.maketrans(_BN_DIGITS, _EN_DIGITS))
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$)|\d{2},\d{2,3}\b)", "", text)
    for word, pattern in _VOCAB.items():
        text = re.sub(unicodedata.normalize("NFKC", pattern), f" {word} ", text, flags=re.I)
    text = re.sub(r"\b(?:transport\s*(?:and|ও|এবং|\+)\s*handling|handling\s*(?:and|ও|এবং|\+)\s*transport)\b",
                  " combined ", text)
    return re.sub(r"\s+", " ", text).strip()


def _decimal(value) -> Decimal | None:
    raw = str(value)
    if not re.fullmatch(r"[+-]?\d{1,12}(?:\.\d{1,4})?", raw):
        return None
    return Decimal(raw)


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def _field(side: str, kind: str, rate=False) -> str:
    return f"{side}_{kind}" + ("_per_kg" if rate or kind == "price" else "")


def _save(state: dict, side: str, kind: str, rate: bool, value: Decimal) -> None:
    # A new absolute quote cannot be combined with a past relative quote.
    # Replacing a trip total with a rate also removes the stale total.
    if kind == "total_cost":
        for key in tuple(state):
            if "_transport" in key or "_handling" in key or key == "require_handling":
                state.pop(key)
    elif kind in ("transport", "handling") and any("_total_cost" in key for key in state):
        # The previous combined bill did not break down its components.
        for key in tuple(state):
            if "_total_cost" in key:
                state.pop(key)
        state["require_handling"] = True
    excluded = ("near", "far") if side == "extra" else ("extra",)
    for other in (*excluded, side):
        for unit in (False, True):
            state.pop(_field(other, kind, unit), None)
    state[_field(side, kind, rate)] = _plain(value)
    if state.get("needs_unit") == kind:
        state.pop("needs_unit")
    if state.get("unassigned", {}).get("kind") == kind:
        state.pop("unassigned")


def _existing_side(state: dict, kind: str) -> str | None:
    sides = [s for s in _SIDES if any(_field(s, kind, rate) in state for rate in (False, True))]
    return sides[0] if len(sides) == 1 else None


def _pieces(text: str):
    """Keep a number with its units and separate a following labeled amount."""
    for clause in re.split(r"[,;:]|\b(?:and|but|with|also|ar|kintu)\b|"
                           r"কিন্তু|এবং|(?:^|\s)আর(?:\s|$)", text):
        start = 0
        numbers = list(_NUMBER.finditer(clause))
        for current, following in zip(numbers, numbers[1:]):
            middle = clause[current.end():following.start()]
            marker = re.search(r"\b(?:near|far|handling|transport|combined|cost|price|kg each)\b", middle)
            cut = current.end() + marker.start() if marker else following.start()
            # e.g. "5/kg more extra transport 600": retain the price sign and
            # attach the explicit cost qualifier to the following expense.
            if marker:
                qualifier = re.search(r"\b(more|less)\s+$", middle[:marker.start()])
                if qualifier and marker.group() in ("transport", "handling"):
                    cut = current.end() + qualifier.start()
            yield clause[start:cut].strip()
            start = cut
        yield clause[start:].strip()


def _slot_side(slots: dict, value: Decimal, kind: str, rate: bool) -> str | None:
    # The model may associate a named buyer with a role. The amount and its
    # monetary meaning/units must already be present in this clause.
    matches = [s for s in ("near", "far") if _decimal(slots.get(_field(s, kind, rate))) == value]
    return matches[0] if len(matches) == 1 else None


def _read_inputs(text: str, state: dict, slots: dict) -> bool:
    recognized = False
    pending = state.get("pending", "")
    if pending == "prices":
        pair = re.fullmatch(r"(?:tk\s*)?(\d+(?:\.\d+)?)\s*(?:tk)?\s*(?:and|আর|ও|,)\s*"
                            r"(?:tk\s*)?(\d+(?:\.\d+)?)\s*(?:tk)?[.।]?", text)
        if pair and all(_decimal(value) is not None for value in pair.groups()):
            for side, value in zip(("near", "far"), pair.groups()):
                _save(state, side, "price", True, Decimal(value))
            return True
    for sentence in re.split(r"[!?\n।]|(?<!\d)\.|\.(?!\d)", text):
        recognized |= _read_sentence(sentence, state, slots, pending)
    return recognized


def _read_sentence(sentence: str, state: dict, slots: dict, pending: str) -> bool:
    active_side = None
    recognized = False
    for piece in _pieces(sentence):
        if not piece:
            continue
        # A comparison's subject precedes "than". Ignore the other party here.
        subject = re.split(r"\bthan\b", piece, maxsplit=1)[0]
        roles = re.findall(r"\b(near|far)\b", subject)
        if roles:
            active_side = roles[-1]
        number = _NUMBER.search(piece)
        expenses = re.findall(r"\b(handling|transport)\b", piece)
        if "combined" in piece or ("cost" in piece and not expenses):
            expenses = ["total_cost"]
        if not number:
            uncertain = re.search(r"^(?:is|are|do|does|could|which|what|how)\b|\b(?:idea|unsure|unknown|know|not)\b|কি|জানি", piece)
            if re.search(r"\b(equal|zero)\b", piece) and expenses and not uncertain:
                for kind in expenses:
                    side = "extra" if "equal" in piece or not active_side else active_side
                    _save(state, side, kind, False, Decimal(0))
                recognized = True
            continue
        value = _decimal(number.group())
        if value is None:
            continue
        after = piece[number.end():]
        before = piece[:number.start()]
        if re.match(r"\s*(?:sacks?\b|bags?\b|maunds?\b|tonnes?\b|বস্তা|মণ)", after) and not expenses:
            state.pop("quantity_kg", None)
            recognized = True
            continue
        if re.match(r"\s*kg\b(?!\s*each)", after) and not re.search(r"\b(?:tk|per)\s*$", before):
            if value > 0:
                state["quantity_kg"] = _plain(value)
            else:
                state.pop("quantity_kg", None)
            recognized = True
            continue
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?\s*(?:tk)?", piece) and pending:
            if pending == "quantity_kg" and "tk" not in piece and value > 0:
                state[pending] = _plain(value)
                recognized = True
                continue
            if pending.startswith(("near_", "far_", "extra_")) and (value >= 0 or pending.startswith("extra_")):
                side, kind = pending.removesuffix("_per_kg").split("_", 1)
                _save(state, side, kind, kind == "price", value)
                recognized = True
                continue
        rate = bool(re.search(r"/\s*kg\b|\bkg\s+each\b|\bper\s+kg\b|\btk\s+kg\b", piece)
                    or re.search(r"\bkg\s*$", before) and re.match(r"\s*tk\b", after))
        relative = bool(re.search(r"\b(more|less)\b", piece))
        kind = expenses[-1] if expenses else "price"
        if re.search(r"[%$€£]|শতাংশ|per\s+(?!kg\b)|/\s*(?!\s*kg\b)[a-z\u0980-\u09ff]|"
                     r"\b(?:percent|usd|dollars?|yards?|maunds?|sacks?|tonnes?)\b", piece):
            state["needs_unit"] = kind
            recognized = True
            continue
        if not expenses and not rate:
            # Explicit updates can inherit the unit of a confirmed bid.
            asked_price = pending == "prices" or pending.endswith("_price_per_kg")
            known_quote = roles and _field(active_side, "price") in state
            known_delta = relative and "extra_price_per_kg" in state
            if re.search(r"\b(?:total|lot|entire|load)\b|মোট", piece) and ("tk" in piece or "price" in piece):
                state["needs_unit"] = "price"
                recognized = True
                continue
            if not (asked_price or known_quote or known_delta) or not re.search(r"\b(?:price|tk)\b", piece):
                continue
            rate = True
        if len(set(expenses)) > 1:
            continue
        if relative:
            side = "extra"
            if ("less" in piece) != ("near" in roles and roles[-1] == "near"):
                value = -value
        else:
            side = active_side or _slot_side(slots, value, kind, rate)
            if not side and pending in [_field(s, kind) for s in _SIDES]:
                side = pending.split("_")[0]
            if not side:
                side = _existing_side(state, kind)
            if not side:
                # An unlabeled trip expense may be a total or a difference.
                state["unassigned"] = {"kind": kind, "value": _plain(value), "rate": rate}
                recognized = True
                continue
        if value < 0 and side != "extra":
            continue
        _save(state, side, kind, rate, value)
        recognized = True
    return recognized


def _amount(state: dict, side: str, kind: str, quantity: Decimal) -> Decimal | None:
    base = _field(side, kind)
    if base in state:
        return Decimal(state[base])
    if _field(side, kind, True) in state:
        return quantity * Decimal(state[_field(side, kind, True)])
    return None


def _difference(state: dict, kind: str, quantity: Decimal) -> Decimal | None:
    extra = _amount(state, "extra", kind, quantity)
    if extra is not None:
        return extra
    near = _amount(state, "near", kind, quantity)
    far = _amount(state, "far", kind, quantity)
    return far - near if near is not None and far is not None else None


def _reply(state: dict, bn: bool) -> str:
    def local(en, bangla):
        return bangla if bn else en

    def digits(value):
        text = _plain(value)
        return text.translate(str.maketrans(_EN_DIGITS, _BN_DIGITS)) if bn else text

    def taka(value):
        return ("−" if value < 0 else "") + "৳" + digits(abs(value))

    def ask(key, en, bangla):
        state["pending"] = key
        return local(en, bangla)

    def cost_name(kind):
        return {"handling": local("handling", "মাল ওঠানো-নামানোর খরচ"),
                "transport": local("transport", "ভাড়া"),
                "total_cost": local("combined expenses", "সব খরচ মিলিয়ে")}[kind]

    first, second = (("ক্রেতা এ", "ক্রেতা বি") if bn else ("buyer A", "buyer B")) if state.get("buyers") else (
        ("কাছের বাজার", "দূরের বাজার") if bn else ("the nearer market", "the farther market"))
    state.pop("pending", None)
    if "needs_unit" in state:
        kind = state["needs_unit"]
        if kind == "price":
            return ask("prices", "What are the buyers’ prices per kg in BDT?", "দুই ক্রেতার দাম কেজিতে কত টাকা?")
        cost = cost_name(kind)
        return ask("units", f"What is the {cost} in BDT for the whole load or per kg, and which buyer is it for?",
                   f"কোন ক্রেতার জন্য এই {cost}, আর পুরো চালান বা প্রতি কেজিতে তা কত টাকা?")
    if "unassigned" in state:
        item = state["unassigned"]
        amount = "৳" + digits(Decimal(item["value"])) + (local("/kg", "/কেজি") if item["rate"] else "")
        if item["kind"] == "price":
            return ask("assign", f"Which buyer offers {amount}, {first} or {second}?",
                       f"{amount} কোন পক্ষের দর, {first} নাকি {second}?")
        return ask("assign", f"Is {amount} the extra expense for {second}, or the expense for just one buyer? Which one?",
                   f"{amount} কি {second} বেছে নিলে বাড়তি খরচ, নাকি কোনো এক পক্ষের খরচ? কোন পক্ষের?")
    if "quantity_kg" not in state:
        return ask("quantity_kg", "How many kg will you sell to the buyer you choose?", "একজন ক্রেতার কাছে মোট কত কেজি বিক্রি করবেন?")
    qty = Decimal(state["quantity_kg"])
    price = _difference(state, "price", qty)
    if price is None:
        known = _existing_side(state, "price")
        if known in ("near", "far"):
            missing = "far" if known == "near" else "near"
            label = second if missing == "far" else first
            return ask(_field(missing, "price"), f"What price in BDT/kg does {label} offer?",
                       f"{label} কত টাকা/কেজি দেবে?")
        return ask("prices", f"What are the prices in BDT/kg for {first} and {second}, in that order? You can also give the difference per kg.",
                   f"{first} ও {second} কত টাকা/কেজি দেবে? এই ক্রমে দুই দাম বা কেজিতে দামের পার্থক্য বলতে পারেন।")
    costs = {}
    kinds = ("total_cost",) if any("_total_cost" in key for key in state) else ("transport", "handling")
    for kind in kinds:
        difference = _difference(state, kind, qty)
        if difference is not None:
            costs[kind] = difference
            continue
        known = _existing_side(state, kind)
        if kind == "handling" and not known and not state.get("require_handling"):
            continue
        label = cost_name(kind)
        if known in ("near", "far"):
            missing = "far" if known == "near" else "near"
            party = second if missing == "far" else first
            return ask(_field(missing, kind), f"What is the total {label} in BDT for {party}?",
                       f"{party} বেছে নিলে মোট {label} কত টাকা?")
        return ask("extra_" + kind, f"How much extra {label} in BDT would {second} cost for the whole load? Enter 0 if the costs are equal.",
                   f"পুরো চালান {second} বেছে নিলে বাড়তি {label} কত টাকা? সমান হলে ০ বলুন।")
    net = qty * price - sum(costs.values())
    winner = second if net > 0 else first
    money = "৳" + digits(abs(net))
    if net == 0:
        result = local("Both buyers leave you the same amount.", "দুই জায়গায় হাতে সমান টাকা থাকবে।")
    else:
        result = local(f"{winner[0].upper() + winner[1:]} leaves you {money} more.", f"{winner} বেছে নিলে {money} বেশি হাতে থাকবে।")
    unit = local("kg", "কেজি")
    expense = " + ".join(taka(n) for n in costs.values())
    if len(costs) > 1 or expense.startswith("−"):
        expense = f"({expense})"
    math = f"{digits(qty)} {unit} × {taka(price)}/{unit} − {expense} = {taka(net)}"
    result += local(f" The difference for {second} compared with {first} is {math}.",
                    f" {first} থেকে {second} বেছে নিলে পার্থক্য {math}।")
    balances = []
    for side in ("near", "far"):
        bid = _amount(state, side, "price", qty)
        expenses = [_amount(state, side, kind, qty) for kind in costs]
        if bid is not None and all(n is not None for n in expenses):
            balances.append(digits(qty * bid - sum(expenses)))
    if len(balances) == 2:
        result += local(f" After your listed expenses, {first} pays ৳{balances[0]} and {second} pays ৳{balances[1]}.",
                        f" আপনার জানানো খরচ বাদে {first} থেকে ৳{balances[0]} এবং {second} থেকে ৳{balances[1]} পাবেন।")
    return result + local(" This assumes other costs are equal.", " অন্য খরচ দুই দিকে সমান ধরা হয়েছে।")


def calculate_market_turn(message: str, previous: dict, locale: str, slots: dict | None = None) -> tuple[dict, str] | None:
    text = _normalize(message)
    fresh = bool(re.search(r"\bnew (?:market )?(?:compare|scenario|case)\b|নতুন (?:compare|হিসাব)", text))
    if fresh:
        previous = {}
    state = dict(previous)
    if re.search(r"\b(?:buyer|market)\s+[ab]\b|\b(?:first|second)\s+buyer\b", message, re.I) or (
            "buyer" in text and not re.search(r"\b(near|far)\b", text)):
        state["buyers"] = True
    subject = re.search(r"\b(?:market|buyer|price|handling|transport|combined|sell|tk)\b", text)
    comparing = re.search(r"\b(?:compare|better|net|more profitable)\b|লাভ|তুলনা", text)
    amount = _NUMBER.search(text)
    roles = re.search(r"\b(?:near|far|more|less)\b", text)
    comparison = fresh or bool((subject or previous) and (comparing or (roles and amount)))
    if not previous and not comparison and not (slots and re.search(r"\b(?:buyer|market)\b", text)):
        return None
    unassigned = state.get("unassigned")
    if unassigned and not _NUMBER.search(text):
        roles = re.findall(r"\b(near|far|more)\b", text)
        if roles:
            side = "extra" if "more" in roles else roles[-1]
            _save(state, side, unassigned["kind"], unassigned["rate"], Decimal(unassigned["value"]))
            return state, _reply(state, locale.startswith("bn"))
    recognized = _read_inputs(text, state, slots or {})
    if not recognized and not comparison:
        return None
    return state, _reply(state, locale.startswith("bn"))
