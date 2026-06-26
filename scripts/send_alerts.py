"""Scheduled entry point for the weekly farmer SMS alerts.

Run on a schedule (cron, or a cloud scheduled job), e.g. weekly:
    python scripts/send_alerts.py

SAFE BY DEFAULT: with no CPaaS credentials it runs in **dry-run** and just prints
the messages it would send. To send for real, set the Africa's Talking variables
(AT_USERNAME, AT_API_KEY[, AT_SENDER_ID]); SMS_DRY_RUN=1 forces dry-run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.channels.sms_alerts import send_weekly_alerts

if __name__ == "__main__":
    send_weekly_alerts()