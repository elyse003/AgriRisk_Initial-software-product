"""Send ONE test SMS to a single number (e.g. your own phone).

    python scripts/test_sms.py +250788123456
    python scripts/test_sms.py +250788123456 "Custom message"

With no custom message it sends a representative weekly alert so you can see
exactly what a subscriber would receive. SAFE BY DEFAULT: with no CPaaS
credentials set it runs in dry-run (prints only, no charge, nothing leaves the
machine). Set AT_USERNAME + AT_API_KEY (use "sandbox" first) to send for real.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.channels.sms_gateway import send_sms, is_live
from src.channels.sms_alerts import build_alert


def _mode():
    if not is_live():
        return "dry-run (printed only, nothing sent, no charge)"
    if os.getenv("AT_USERNAME", "").lower() == "sandbox":
        return "SANDBOX (free — appears in the AT simulator, not a real phone)"
    return "LIVE (real SMS to a real phone — you will be charged)"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_sms.py <phone> ["message"]\n'
              '  e.g. python scripts/test_sms.py +250788123456')
        raise SystemExit(1)

    phone = sys.argv[1].strip()
    message = sys.argv[2] if len(sys.argv) > 2 else build_alert(
        {"phone_number": phone, "district": "Musanze",
         "crops": "maize,beans,potatoes", "language": "en"})

    print(f"Mode: {_mode()}")
    result = send_sms(phone, message)
    print("Result:", result)