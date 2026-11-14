import re
from datetime import date

from tests import harness as H

GIVEN_ON_REQUEST = {
    ("bank", "cancel_credit_card#3", "identification"),
    ("bank", "get_loan#0", "identification"),
    ("bank", "get_loan#5", "identification"),
    ("bank", "pay_bill#0", "identification"),
    ("bank", "pay_bill_with_credit_card#0", "identification"),
    ("bank", "pay_loan#0", "identification"),
    ("bank", "pay_loan#1", "identification"),
    ("bank", "set_safety_box#0", "identification"),
    ("bank", "set_safety_box#13", "identification"),
    ("bank", "transfer_funds#9", "identification"),
    ("library", "check_return_date#2", "password"),
}
SYNONYMS = {"dollars": ["$", "usd"], "drive": ["driving"]}
BOOLEAN_PHRASES = {
    ("key_returned", True): r"key has (already )?been returned",
    ("key_returned", False): r"hasn.t",
    ("passed", True): r"\bas passed\b",
    ("restricted", False): r"\bnot (be )?restricted\b",
}
ROOM_TYPES = r"\b(single|double|suite|penthouse)\b"
MONTHS = "January February March April May June July August September October November December".split()
WRITTEN_DATE = rf"\b({'|'.join(MONTHS)}) (\d{{1,2}})(?:st|nd|rd|th)?,? (\d{{4}})\b"
ISO_DATE = r"\b(\d{4})-(\d{2})-(\d{2})(?!\d)"
TIME = r"(?<!\d)\d{1,2}:\d\d(?!\d)"
NUMBER = r"(?<![\w\-:.,])-?\d[\d,]*(?:\.\d+)?(?![\w\-:])"


def leaves(value, key=None):
    if isinstance(value, dict):
        return [leaf for k, v in value.items() for leaf in leaves(v, k)]
    if isinstance(value, list):
        return [leaf for v in value for leaf in leaves(v, key)]
    return [(key, value)]


def dates(text):
    return ({date(int(y), int(m), int(d)) for y, m, d in re.findall(ISO_DATE, text)}
            | {date(int(y), MONTHS.index(m) + 1, int(d)) for m, d, y in re.findall(WRITTEN_DATE, text)})


def numbers(text):
    return {float(n.replace(",", "")) for n in re.findall(NUMBER, text)}


def plain(text):
    return text.lower().replace("_", " ")


def stated(prompt, key, value):
    if isinstance(value, bool):
        return bool(re.search(BOOLEAN_PHRASES[key, value], prompt, re.I))
    if isinstance(value, (int, float)):
        return float(value) in numbers(prompt)
    plural = "s?" if re.fullmatch(r"[a-z ]+", plain(value)) else ""
    if re.search(rf"(?<![a-z0-9]){re.escape(plain(value))}{plural}(?![a-z0-9])", plain(prompt)) or any(
            s in plain(prompt) for s in SYNONYMS.get(value, [])):
        return True
    if moment := re.fullmatch(ISO_DATE + r"(?:T(\d\d:\d\d):\d\d)?", value):
        y, m, d, clock = moment.groups()
        return date(int(y), int(m), int(d)) in dates(prompt) and (clock is None or clock in prompt)
    return False


def mismatches(domain, task):
    prompt, known = task["user_prompt"], task["user_known"]
    found = [("placeholder", "UNKNOWN_PLACEHOLDER")] if "UNKNOWN_PLACEHOLDER" in prompt else []
    found += [(key, value) for field, given in known.items() if (domain, task["id"], field) not in GIVEN_ON_REQUEST
              for key, value in leaves(given, field) if not stated(prompt, key, value)]
    known_dates = set().union(*[dates(v) for _, v in leaves(known) if isinstance(v, str)])
    found += [("unknown date", d.isoformat()) for d in sorted(dates(prompt) - known_dates)]
    known_numbers = {float(v) for _, v in leaves(known) if isinstance(v, (int, float))}
    known_numbers |= set().union(*[numbers(v) for _, v in leaves(known) if isinstance(v, str)])
    known_times = set().union(*[re.findall(TIME, v) for _, v in leaves(known) if isinstance(v, str)])
    found += [("unknown time", t) for t in sorted(set(re.findall(TIME, prompt)) - known_times)]
    found += [("unknown number", n) for n in sorted(numbers(re.sub(WRITTEN_DATE, "", prompt)) - known_numbers)]
    for key, value in known.items():
        if known.get(f"old_{key}", value) != value and prompt.find(known[f"old_{key}"]) > prompt.find(value):
            found += [("new value before old", key)]
    if domain == "hotel" and "room_type" in known:
        found += [("unknown room type", r) for r in sorted({r.lower() for r in re.findall(ROOM_TYPES, prompt, re.I)})
                  if r != known["room_type"]]
        if task["user_goal"] == "request_room_change" and not re.search(rf"\bto an? {known['room_type']}\b", prompt):
            found += [("room type not requested", known["room_type"])]
    if "slots" in known:
        found += [("slot range", r) for r in re.findall(r"from\W*\d{1,2}:\d\d\W*to\W*\d{1,2}:\d\d", prompt)]
    return found


def all_mismatches():
    return {(domain, task["id"]): found for domain in H.domains() for task in H.load_tasks(domain)
            if (found := mismatches(domain, task))}


def test_first_user_message_states_what_the_user_knows():
    assert all_mismatches() == {}
