"""Gateway-agnostic SMS sender (CPaaS).

Sends one SMS through the configured Communications-Platform-as-a-Service. The
default provider is Africa's Talking (best Rwanda coverage, MTN/Airtel); Twilio
is also supported. It uses plain HTTP (`requests`) so there's no SDK dependency.

SAFE BY DEFAULT: with no API key set, or SMS_DRY_RUN=1, it does NOT send — it
just returns/logs the message it *would* send. So the whole alert pipeline runs
and demos with zero cost or telecom onboarding; set the credentials to go live.

Environment variables
  SMS_PROVIDER      "africastalking" (default) | "twilio"
  SMS_DRY_RUN       "1" to force dry-run even when credentials exist
  AT_USERNAME       Africa's Talking username ("sandbox" for the test account)
  AT_API_KEY        Africa's Talking API key
  AT_SENDER_ID      optional sender id / shortcode
  TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM   for the Twilio provider
"""
from __future__ import annotations

import os

import requests


def _truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def is_live() -> bool:
    """True only when a provider is fully configured AND dry-run isn't forced."""
    if _truthy(os.getenv("SMS_DRY_RUN", "")):
        return False
    provider = os.getenv("SMS_PROVIDER", "africastalking").lower()
    if provider == "twilio":
        return all(os.getenv(k) for k in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM"))
    return bool(os.getenv("AT_API_KEY") and os.getenv("AT_USERNAME"))


def _send_africastalking(to: str, message: str) -> dict:
    username = os.getenv("AT_USERNAME", "")
    url = ("https://api.sandbox.africastalking.com/version1/messaging"
           if username == "sandbox"
           else "https://api.africastalking.com/version1/messaging")
    data = {"username": username, "to": to, "message": message}
    sender = os.getenv("AT_SENDER_ID")
    if sender:
        data["from"] = sender
    r = requests.post(url, data=data, timeout=20, headers={
        "apiKey": os.getenv("AT_API_KEY", ""),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    r.raise_for_status()
    return {"provider": "africastalking", "status": "sent", "response": r.json()}


def _send_twilio(to: str, message: str) -> dict:
    sid = os.getenv("TWILIO_SID", "")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    r = requests.post(url, timeout=20, auth=(sid, os.getenv("TWILIO_TOKEN", "")),
                      data={"To": to, "From": os.getenv("TWILIO_FROM", ""), "Body": message})
    r.raise_for_status()
    return {"provider": "twilio", "status": "sent", "response": r.json()}


def send_sms(to: str, message: str, dry_run: bool | None = None) -> dict:
    """Send one SMS (or simulate it). Returns a small result dict; never raises
    on a provider error — it reports it, so a bad number can't stop a batch."""
    if dry_run is None:
        dry_run = not is_live()
    if dry_run:
        print(f"[SMS dry-run] -> {to}: {message}")
        return {"to": to, "status": "dry-run", "message": message}
    provider = os.getenv("SMS_PROVIDER", "africastalking").lower()
    try:
        res = _send_twilio(to, message) if provider == "twilio" else _send_africastalking(to, message)
        res["to"] = to
        return res
    except Exception as e:
        return {"to": to, "status": "error", "error": str(e)}