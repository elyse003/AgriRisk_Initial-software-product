"""USSD-style menu engine for AgriRisk (gateway-agnostic).

Drives a *384#-style numbered-menu session over the SAME advisory logic as the
WhatsApp/SMS bot (src.channels.whatsapp_bot.answer). It is stateless in the
Africa's Talking sense: the whole chain of the farmer's inputs, joined by '*',
is passed in on every call, e.g. "1*2*3".

    ussd_session(text) -> (screen, ended)
        screen  the text to show on the phone
        ended   True when the session is over (AT 'END'), False to continue ('CON')

The same engine powers the in-app USSD simulator and can back a real Africa's
Talking /ussd endpoint later (just prefix the screen with 'CON ' / 'END ').
No telecom or regulatory onboarding is needed to build or demo this.
"""
from __future__ import annotations

from src.channels.whatsapp_bot import answer

CROP_BY_NUM = {"1": "maize", "2": "beans", "3": "potatoes"}

# Rwanda's five provinces and their districts (for the drill-down menus).
PROVINCES = {
    "1": ("Kigali City", ["Nyarugenge", "Gasabo", "Kicukiro"]),
    "2": ("Northern", ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"]),
    "3": ("Southern", ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe",
                       "Nyanza", "Nyaruguru", "Ruhango"]),
    "4": ("Eastern", ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma",
                      "Nyagatare", "Rwamagana"]),
    "5": ("Western", ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu",
                      "Rusizi", "Rutsiro"]),
}

CROP_MENU = "Choose crop:\n1. Maize\n2. Beans\n3. Potatoes"


def _menu(title, rows):
    return "\n".join([title] + [f"{k}. {v}" for k, v in rows])


def _province_menu():
    return _menu("Choose province:", [(k, v[0]) for k, v in PROVINCES.items()])


def _district_menu(prov_key):
    name, dists = PROVINCES[prov_key]
    return _menu(f"{name} - district:", [(str(i + 1), d) for i, d in enumerate(dists)])


def _district_from(prov_key, sel):
    _, dists = PROVINCES[prov_key]
    try:
        d = dists[int(sel) - 1]
        return d if int(sel) >= 1 else None
    except (ValueError, IndexError):
        return None


def ussd_session(text: str):
    """Return (screen, ended) for the accumulated USSD input chain `text`."""
    parts = text.split("*") if text else []

    if not parts:
        return _menu("AgriRisk", [
            ("1", "Crop price"),
            ("2", "Seasonal risk"),
            ("3", "Disease alert"),
            ("4", "Fertilizer plan"),
        ]), False

    choice = parts[0]

    # 1) PRICE: crop -> province -> district -> result
    if choice == "1":
        if len(parts) == 1:
            return CROP_MENU, False
        crop = CROP_BY_NUM.get(parts[1])
        if not crop:
            return "Invalid choice. Dial again.", True
        if len(parts) == 2:
            return _province_menu(), False
        if parts[2] not in PROVINCES:
            return "Invalid choice. Dial again.", True
        if len(parts) == 3:
            return _district_menu(parts[2]), False
        district = _district_from(parts[2], parts[3])
        if not district:
            return "Invalid choice. Dial again.", True
        return answer(f"{crop} price {district}"), True

    # 2) SEASONAL RISK: province -> district -> result
    if choice == "2":
        if len(parts) == 1:
            return _province_menu(), False
        if parts[1] not in PROVINCES:
            return "Invalid choice. Dial again.", True
        if len(parts) == 2:
            return _district_menu(parts[1]), False
        district = _district_from(parts[1], parts[2])
        if not district:
            return "Invalid choice. Dial again.", True
        return answer(f"risk {district}"), True

    # 3) DISEASE ALERT: province -> district -> result (all crops)
    if choice == "3":
        if len(parts) == 1:
            return _province_menu(), False
        if parts[1] not in PROVINCES:
            return "Invalid choice. Dial again.", True
        if len(parts) == 2:
            return _district_menu(parts[1]), False
        district = _district_from(parts[1], parts[2])
        if not district:
            return "Invalid choice. Dial again.", True
        return answer(f"disease {district}"), True

    # 4) FERTILIZER PLAN: crop -> land size -> result
    if choice == "4":
        if len(parts) == 1:
            return CROP_MENU, False
        crop = CROP_BY_NUM.get(parts[1])
        if not crop:
            return "Invalid choice. Dial again.", True
        if len(parts) == 2:
            return "Enter land size in hectares\n(e.g. 0.5):", False
        land = parts[2].replace(",", ".").strip()
        try:
            float(land)
        except ValueError:
            return "Invalid land size. Dial again.", True
        return answer(f"fertilizer {crop} {land} ha"), True

    return "Invalid choice. Dial again.", True