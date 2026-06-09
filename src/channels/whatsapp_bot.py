"""Farmer WhatsApp chatbot logic.

parse_message() turns a natural-language Kinyarwanda/English query into a
structured intent. The web app (and, in production, the Twilio webhook) routes
that intent to the right module and formats a bilingual reply. Keeping parsing
here means the live Twilio integration is a thin wrapper around the same logic.
"""
from __future__ import annotations

import re

from config.settings import DISTRICTS

# crop vocabulary: Kinyarwanda + English -> canonical crop
CROP_WORDS = {
    "ibigori": "maize", "maize": "maize",
    "ibishyimbo": "beans", "beans": "beans",
    "ibirayi": "potatoes", "potato": "potatoes", "potatoes": "potatoes",
}
# intent keywords
INTENT_WORDS = {
    "price": ["igiciro", "price", "ibiciro"],
    "risk": ["risk", "ibyago", "ibyago"],
    "disease": ["indwara", "disease"],
    "input": ["input", "ifumbire", "inputs", "imbuto"],
    "help": ["help", "ubufasha"],
}


def detect_language(text: str) -> str:
    rw_markers = ("igiciro", "ibigori", "ibirayi", "ibishyimbo", "indwara",
                  "ibyago", "ifumbire", "ubufasha", "muraho")
    return "rw" if any(w in text for w in rw_markers) else "en"


def parse_message(text: str) -> dict:
    """Return {intent, crop, district, budget, lang} parsed from a message."""
    t = text.lower().strip()
    lang = detect_language(t)

    intent = None
    for name, words in INTENT_WORDS.items():
        if any(w in t for w in words):
            intent = name
            break

    crop = next((c for w, c in CROP_WORDS.items() if w in t), None)
    district = next((d for d in DISTRICTS if d.lower() in t), None)
    budget_match = re.search(r"\d{4,}", t.replace(",", ""))
    budget = int(budget_match.group()) if budget_match else None

    # infer intent when a crop/district is named without an explicit keyword
    if intent is None and crop and district:
        intent = "price"

    return {"intent": intent, "crop": crop, "district": district,
            "budget": budget, "lang": lang}
