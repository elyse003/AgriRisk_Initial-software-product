"""Farmer SMS alerts (officer + admin): enrol subscribers and send the weekly
price + seasonal-risk alert over the SMS gateway (Africa's Talking by default).

This is the officer console for the low-bandwidth channels that reach farmers on
basic phones — the digital-literacy path: no smartphone, no internet, no data.

Safe by default: with no CPaaS credentials, or SMS_DRY_RUN=1, sending is
simulated (nothing leaves the server, no charge). The current mode is shown at
the top so an officer always knows whether a click will really send.
"""
from _ui import setup, insight_panel
from _i18n import t
import streamlit as st

from config.settings import DISTRICTS
from src.db.connection import list_subscribers, add_subscriber, remove_subscriber
from src.channels.sms_alerts import build_alert, send_weekly_alerts
from src.channels.sms_gateway import send_sms, is_live
import os

# Belt-and-suspenders: keys set in the Streamlit Cloud "Secrets" box populate
# st.secrets but do not always reach os.getenv (which the SMS gateway reads).
# Copy them across here, before is_live() is ever called, so a correctly-set
# key flips the page to SANDBOX/LIVE even if the startup bridge did not run.
for _k in ("AT_USERNAME", "AT_API_KEY", "AT_SENDER_ID", "SMS_PROVIDER", "SMS_DRY_RUN"):
    try:
        if _k in st.secrets and str(st.secrets[_k]).strip():
            os.environ[_k] = str(st.secrets[_k]).strip()
    except Exception:
        pass

user = setup("Farmer Alerts", "Enrol farmers and send SMS price & risk alerts",
             allowed_roles=("officer", "super_admin"))
if user.get("role") not in ("officer", "super_admin"):
    st.error(t("This page is for extension officers and administrators."))
    st.stop()

CROPS = ["maize", "beans", "potatoes"]


def _mode():
    """Human-readable send mode, so the officer knows what a click will do."""
    if not is_live():
        return ("dry-run", "var(--ag-slate)",
                t("Simulated — nothing is sent and nothing is charged. "
                  "Set the Africa's Talking keys to send for real."))
    if os.getenv("AT_USERNAME", "").lower() == "sandbox":
        return ("sandbox", "var(--ag-amber)",
                t("Sandbox — messages appear in the Africa's Talking simulator, not on a real phone."))
    return ("LIVE", "var(--ag-terra)",
            t("LIVE — messages go to real phones and your account is charged."))


mode, colour, mode_help = _mode()

# ---- current mode + subscriber count -------------------------------------
df = list_subscribers()
n = 0 if df is None else len(df)
insight_panel([
    (colour, t("Send mode"), mode),
    ("var(--ag-sage)", t("Subscribers"), str(n)),
], lead=t("Farmer SMS channel"), strong=mode, meta=mode_help)

# ---- diagnostics: why is it in this mode? --------------------------------
# Shows exactly what the app detects, so a stuck DRY-RUN is easy to explain
# (missing key, unparsed secrets, etc.). No secret values are ever printed.
if mode == "dry-run":
    with st.expander(t("Why is it in DRY-RUN? (diagnostics)")):
        def _seen(k):
            in_env = bool(os.getenv(k, "").strip())
            try:
                in_sec = k in st.secrets and bool(str(st.secrets[k]).strip())
            except Exception:
                in_sec = False
            return in_env, in_sec
        try:
            n_secrets = len(list(st.secrets.keys()))
            secrets_ok = True
        except Exception as e:  # secrets file failed to parse
            n_secrets, secrets_ok = 0, False
            st.error(t("Streamlit could not read your Secrets — usually a TOML "
                       "formatting error. Detail: {err}").format(err=str(e)))
        try:
            key_names = sorted(st.secrets.keys())  # names only, never values
        except Exception:
            key_names = []
        st.write({
            t("secrets loaded"): secrets_ok,
            t("# of secret keys"): n_secrets,
            t("secret key names"): key_names,
            "AT_USERNAME": {"env": _seen("AT_USERNAME")[0], "secret": _seen("AT_USERNAME")[1]},
            "AT_API_KEY": {"env": _seen("AT_API_KEY")[0], "secret": _seen("AT_API_KEY")[1]},
            "is_live()": is_live(),
        })
        st.caption(t("Both AT_USERNAME and AT_API_KEY must show True. If 'secrets "
                     "loaded' is False, fix the TOML. If a key shows secret=True "
                     "but env=False, reboot the app to pick up the latest code."))

st.divider()

# ---- enrol a farmer ------------------------------------------------------
st.markdown(f"#### {t('Enrol a farmer')}")
with st.form("add_sub", border=False):
    c1, c2 = st.columns(2)
    phone = c1.text_input(t("Phone number"), placeholder="+2507...")
    district = c2.selectbox(t("District"), DISTRICTS)
    c3, c4 = st.columns(2)
    crops = c3.multiselect(t("Crops"), CROPS, default=["maize", "beans"])
    lang = c4.selectbox(t("Language"), ["rw", "en"],
                        format_func=lambda x: "Kinyarwanda" if x == "rw" else "English")
    if st.form_submit_button(t("Add subscriber"), type="primary"):
        p = (phone or "").strip()
        if not p or not crops:
            st.error(t("Enter a phone number and at least one crop."))
        elif add_subscriber(p, district, ",".join(crops), lang):
            st.success(t("Added {phone} ({district}).").format(phone=p, district=district))
            st.rerun()
        else:
            st.error(t("That phone number is already subscribed."))

# ---- current subscribers + remove ----------------------------------------
if n:
    st.markdown(f"#### {t('Subscribers')} ({n})")
    st.dataframe(df, use_container_width=True, hide_index=True)
    rm = st.selectbox(t("Remove a subscriber"), [""] + list(df["phone_number"]))
    if rm and st.button(t("Remove {phone}").format(phone=rm), icon=":material/delete:"):
        remove_subscriber(rm)
        st.rerun()
else:
    st.info(t("No subscribers yet. Enrol a farmer above, or they can text YEGO to opt in."))

st.divider()

# ---- preview + send one ---------------------------------------------------
st.markdown(f"#### {t('Preview & send a test')}")
pc1, pc2, pc3 = st.columns(3)
tphone = pc1.text_input(t("Test phone"), placeholder="+2507...")
tdist = pc2.selectbox(t("District "), DISTRICTS, key="tdist")
tcrop = pc3.selectbox(t("Crop"), CROPS, key="tcrop")
preview = build_alert({"phone_number": tphone or "+250...", "district": tdist,
                       "crops": tcrop, "language": "rw"})
st.markdown(f"<div class='ag-note'><strong>{t('Message preview')}:</strong><br>{preview}</div>",
            unsafe_allow_html=True)
st.caption(f"{len(preview)} {t('characters')}")

if st.button(t("Send test to this number"), type="primary", disabled=not (tphone or "").strip()):
    msg = build_alert({"phone_number": tphone.strip(), "district": tdist,
                       "crops": tcrop, "language": "rw"})
    res = send_sms(tphone.strip(), msg)
    if res["status"] in ("sent", "dry-run"):
        st.success(t("{mode}: message to {phone} — {status}.").format(
            mode=mode, phone=tphone.strip(), status=res["status"]))
    else:
        st.error(t("Send failed: {err}").format(err=res.get("error", "unknown")))

st.divider()

# ---- send to all ----------------------------------------------------------
st.markdown(f"#### {t('Send the weekly alert to all subscribers')}")
if mode == "LIVE":
    st.warning(t("This will send a real SMS to every subscriber and charge your account."))
if n == 0:
    st.button(t("Send weekly alerts"), disabled=True)
elif st.button(t("Send weekly alerts to {n} subscribers").format(n=n), type="primary"):
    results = send_weekly_alerts()
    ok = sum(r["status"] in ("sent", "dry-run") for r in results)
    err = [r for r in results if r["status"] == "error"]
    st.success(t("{mode}: {ok}/{total} alerts processed.").format(mode=mode, ok=ok, total=len(results)))
    if err:
        st.error(t("{n} failed (e.g. {err})").format(n=len(err), err=err[0].get("error", "")[:80]))

st.markdown(f"""<div class="ag-foot">
  <div><span class="label">{t('Channel')}:</span> {t("SMS via Africa's Talking (basic phones, no internet)")}</div>
  <div><span class="label">{t('Opt-out')}:</span> {t('Farmers reply STOP any time.')}</div>
</div>""", unsafe_allow_html=True)