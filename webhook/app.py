"""Twilio webhook for the AgriRisk farmer assistant (WhatsApp + SMS).

Twilio POSTs an incoming message to /whatsapp (or /sms); we run the same bot
used by the dashboard's WhatsApp Preview and reply with TwiML. This is a small,
separate web service because Streamlit cannot receive webhooks.

Local run:   uvicorn webhook.app:app --reload
Deploy:      see render.yaml (free Render web service)
"""
import sys
import time
from pathlib import Path
from xml.sax.saxutils import escape

# make the repo root importable (src/, config/, data/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, Response

from src.channels.whatsapp_bot import converse
from src.channels.sms_alerts import handle_keyword

app = FastAPI(title="AgriRisk farmer assistant webhook")

# Per-sender conversation memory so SMS/WhatsApp match the in-app chat: a farmer can
# text "price" then "beans" then "Musanze" across messages. Kept in memory with a
# short TTL (a texting session is bursty). Note: this assumes a single worker; for
# multiple workers/instances move this to the DB or a shared cache.
_SESSIONS: dict[str, tuple] = {}
_SESSION_TTL = 20 * 60   # seconds


def _get_state(sender: str) -> dict:
    ent = _SESSIONS.get(sender)
    if ent and (time.time() - ent[1]) <= _SESSION_TTL:
        return ent[0]
    _SESSIONS.pop(sender, None)
    return {}


def _reply(body: str, sender: str) -> str:
    """YEGO/STOP opt-in-out first, otherwise the stateful bot answer (same as chat)."""
    kw = handle_keyword(body, sender)
    if kw is not None:
        return kw
    reply, state = converse(body, _get_state(sender))
    _SESSIONS[sender] = (state, time.time())
    return reply


def _twiml(message: str) -> Response:
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'
    return Response(content=body, media_type="application/xml")


@app.get("/")
def health():
    return JSONResponse({"status": "ok", "service": "agririsk-webhook"})


@app.post("/whatsapp")
async def whatsapp(Body: str = Form(default=""), From: str = Form(default="")):
    return _twiml(_reply(Body, From))


@app.post("/sms")
async def sms(Body: str = Form(default=""), From: str = Form(default="")):
    return _twiml(_reply(Body, From))