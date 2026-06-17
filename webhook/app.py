"""Twilio webhook for the AgriRisk farmer assistant (WhatsApp + SMS).

Twilio POSTs an incoming message to /whatsapp (or /sms); we run the same bot
used by the dashboard's WhatsApp Preview and reply with TwiML. This is a small,
separate web service because Streamlit cannot receive webhooks.

Local run:   uvicorn webhook.app:app --reload
Deploy:      see render.yaml (free Render web service)
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# make the repo root importable (src/, config/, data/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, Response

from src.channels.whatsapp_bot import answer

app = FastAPI(title="AgriRisk farmer assistant webhook")


def _twiml(message: str) -> Response:
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'
    return Response(content=body, media_type="application/xml")


@app.get("/")
def health():
    return JSONResponse({"status": "ok", "service": "agririsk-webhook"})


@app.post("/whatsapp")
async def whatsapp(Body: str = Form(default=""), From: str = Form(default="")):
    return _twiml(answer(Body))


@app.post("/sms")
async def sms(Body: str = Form(default=""), From: str = Form(default="")):
    return _twiml(answer(Body))