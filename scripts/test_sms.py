"""Send ONE AgriRisk alert to a single number so you can SEE it on the Africa's
Talking Simulator (sandbox) before going live to real phones.

    python scripts/test_sms.py +250790857019
    python scripts/test_sms.py +250790857019 "Custom message"

With no custom message it sends a representative weekly alert, the exact thing a
subscriber receives. It auto-loads a repo-root .env, so put your sandbox keys there:

    AT_USERNAME=sandbox
    AT_API_KEY=<your sandbox API key>

SAFE BY DEFAULT: with no credentials it runs in dry-run (prints only, nothing sent).
In SANDBOX mode the SMS appears in the AT SIMULATOR (Launch Simulator on the
dashboard and connect this number), NOT on a real handset. Real delivery needs a
LIVE (production) app.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_dotenv():
    """Load KEY=VALUE lines from a repo-root .env into os.environ (no dependency)."""
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from src.channels.sms_gateway import send_sms, is_live
from src.channels.sms_alerts import build_alert


def _mode():
    if not is_live():
        return "dry-run (printed only, nothing sent, no charge)"
    if os.getenv("AT_USERNAME", "").lower() == "sandbox":
        return "SANDBOX (free, appears in the AT simulator, not a real phone)"
    return "LIVE (real SMS to a real phone, you will be charged)"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_sms.py <phone> ["message"]\n'
              '  e.g. python scripts/test_sms.py +250790857019')
        raise SystemExit(1)

    phone = sys.argv[1].strip()
    message = sys.argv[2] if len(sys.argv) > 2 else build_alert(
        {"phone_number": phone, "district": "Musanze",
         "crops": "maize,beans,potatoes", "language": "rw"})

    print(f"Mode: {_mode()}")
    print(f"To:   {phone}")
    print(f"Text: {message}\n")
    result = send_sms(phone, message)
    print("Result:", result)

    status = result.get("status")
    sandbox = os.getenv("AT_USERNAME", "").lower() == "sandbox"
    if status == "dry-run":
        print("\nDry-run: no credentials detected. Put AT_USERNAME=sandbox and "
              "AT_API_KEY=<sandbox key> in .env (or the shell), then re-run.")
    elif status == "error":
        err = str(result.get("error", ""))
        if "WRONG_VERSION_NUMBER" in err or "SSLError" in err or "SSL" in err.upper():
            print("\nThe sandbox host failed TLS on THIS network (WRONG_VERSION_NUMBER), "
                  "the request never left your machine, so nothing reaches the simulator. "
                  "Try a different network/hotspot (mobile data), or go live.")
        elif "401" in err or "403" in err or "Unauthorized" in err:
            print("\nAuth rejected. Check that AT_USERNAME is exactly 'sandbox' and the key "
                  "is the SANDBOX API key (not the production one).")
        else:
            print("\nSend failed, see the error above.")
    elif status == "sent" and sandbox:
        print(f"\nSent to the SANDBOX. Now open the AT Simulator "
              "(developers.africastalking.com -> your sandbox app -> Launch Simulator), "
              f"connect {phone}, and the SMS shows up there, it will NOT arrive on a real phone.")