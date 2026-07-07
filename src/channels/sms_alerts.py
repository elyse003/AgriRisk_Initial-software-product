"""Automated weekly farmer SMS alerts over a CPaaS (default Africa's Talking).

Composes a short, bilingual price + seasonal-risk alert for each subscriber from
their district and crops, reusing the SAME model-backed advice as the chat /
USSD / WhatsApp bot (src.channels.whatsapp_bot.answer), and sends it through the
gateway-agnostic sender (src.channels.sms_gateway). Runs in dry-run with no
credentials, so it's fully testable/demoable; set the CPaaS keys to go live.

Also handles inbound opt-in / opt-out keywords (YEGO / STOP) from the webhook.

    send_weekly_alerts(dry_run=None, limit=None) -> list[dict]
    handle_keyword(text, sender)  -> reply str, or None if it's not a keyword
"""
from __future__ import annotations

from src.channels.whatsapp_bot import answer
from src.channels.sms_gateway import send_sms, is_live
from src.db.connection import (list_subscribers, add_subscriber, remove_subscriber,
                               user_district)

# crop value -> Kinyarwanda keyword, so answer() replies in the right language
_RW_CROP = {"maize": "ibigori", "beans": "ibishyimbo", "potatoes": "ibirayi"}
_OPT_IN = {"yego", "start", "subscribe", "join"}
_OPT_OUT = {"stop", "hagarika", "end", "unsubscribe"}


def build_alert(sub: dict) -> str:
    """Compose one subscriber's weekly alert (kept short for SMS)."""
    rw = (sub.get("language") or "rw") == "rw"
    district = (sub.get("district") or "").strip()
    crops = [c.strip() for c in (sub.get("crops") or "").split(",") if c.strip()]
    lines = []
    if district and crops:
        c = crops[0]                                   # headline price = first crop
        q = f"{_RW_CROP.get(c, c)} igiciro {district}" if rw else f"{c} price {district}"
        lines.append(answer(q))
    if district:
        lines.append(answer(f"ibyago {district}" if rw else f"risk {district}"))
    body = " ".join(lines) if lines else (
        "Iyandikishe n'akarere n'ibihingwa." if rw else "Register your district and crops.")
    tail = " Andika STOP guhagarika." if rw else " Reply STOP to opt out."
    return "AgriRisk: " + body + tail


def send_weekly_alerts(dry_run: bool | None = None, limit: int | None = None) -> list[dict]:
    """Send the weekly alert to every subscriber. Returns a result per send."""
    df = list_subscribers()
    if df is None or len(df) == 0:
        print("No subscribers."); return []
    rows = df.to_dict("records")
    if limit:
        rows = rows[:limit]
    results = []
    for s in rows:
        msg = build_alert(s)
        results.append(send_sms(s["phone_number"], msg, dry_run=dry_run))
    sent = sum(r["status"] in ("sent", "dry-run") for r in results)
    mode = "LIVE" if is_live() and dry_run is not True else "dry-run"
    print(f"Weekly alerts [{mode}]: {sent}/{len(results)} ok")
    return results


def handle_keyword(text: str, sender: str):
    """Process a YEGO/STOP keyword from an inbound SMS. Returns the reply to send,
    or None if `text` isn't an opt-in/out keyword (so the bot handles it normally)."""
    t = (text or "").strip().lower()
    if t in _OPT_OUT:
        remove_subscriber(sender)
        return ("Wahagaritse imiburo ya AgriRisk. Andika YEGO kongera kwiyandikisha."
                if _looks_rw(sender) else
                "You've stopped AgriRisk alerts. Reply YEGO to rejoin.")
    if t in _OPT_IN:
        district = user_district(sender)               # seed district from the user record if known
        add_subscriber(sender, district, "maize,beans,potatoes", "rw")
        return ("Wiyandikishije! Uzajya wakira imiburo y'igiciro n'ibyago buri cyumweru. "
                "Andika STOP guhagarika.")
    return None


def _looks_rw(_sender) -> bool:
    return True   # default replies in Kinyarwanda; refine per-subscriber later