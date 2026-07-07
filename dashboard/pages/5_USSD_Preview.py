"""USSD Preview: a feature-phone *384#-style simulator for the AgriRisk menu.

Demonstrates how a farmer reaches AgriRisk on ANY phone, with no internet, via a
numbered menu, without needing a live USSD code (which requires an operator
agreement). Powered by src.channels.ussd_menu, which reuses the same advisory
logic as the chat/WhatsApp/SMS bot.
"""
import html

from _ui import setup, page_header
from _i18n import t
import streamlit as st
from src.channels.ussd_menu import ussd_session

setup("USSD Preview", "Feature-phone menu demo",
      allowed_roles=("farmer", "officer", "super_admin"), header=False)

page_header(
    "USSD PREVIEW",
    f"Feature-phone <em>{t('menu')}</em> demo",
    t("How a farmer reaches AgriRisk on any phone, no internet, no app, through a "
      "*384#-style menu. This is a working simulator; going live needs a short code from "
      "an operator, but the menu itself is ready."),
    meta_strong="*384#", meta_sub=t("simulator"))

st.markdown("""<style>
.ussd-wrap{ max-width:300px; margin:6px auto 14px; }
.ussd-phone{ background:#15181a; border-radius:30px; padding:16px 14px 20px;
  box-shadow:0 16px 44px rgba(0,0,0,.26); border:1px solid #2a2f31; }
.ussd-brandbar{ text-align:center; color:#7f8a85; font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; margin-bottom:8px; font-family:'Geist',sans-serif; }
.ussd-screen{ background:#bfe3c2; color:#0e2218;
  font-family:ui-monospace,"Cascadia Code","Consolas",monospace; font-size:13.5px; line-height:1.55;
  border-radius:7px; padding:14px 13px; min-height:210px; white-space:pre-line;
  border:2px solid #0c1812; box-shadow:inset 0 0 0 2px rgba(255,255,255,.22); }
.ussd-note{ text-align:center; font-size:11px; color:var(--ag-mute); margin-top:6px; }
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("ussd_chain", None)   # None = not dialed yet


def _phone(screen_text, footer=""):
    st.markdown(
        f"<div class='ussd-wrap'><div class='ussd-phone'>"
        f"<div class='ussd-brandbar'>MTN RW · *384#</div>"
        f"<div class='ussd-screen'>{html.escape(screen_text)}</div></div>"
        f"<div class='ussd-note'>{footer}</div></div>",
        unsafe_allow_html=True)


left, mid, right = st.columns([1, 1.1, 1])
with mid:
    if ss.ussd_chain is None:
        _phone("AgriRisk\n\nDial *384# to start.",
               t("Dial the code to open the menu."))
        if st.button(t("Dial *384#"), type="primary", use_container_width=True):
            ss.ussd_chain = ""
            st.rerun()
    else:
        screen, ended = ussd_session(ss.ussd_chain)
        _phone(screen, t("Session ended.") if ended else t("Reply with a number."))

        if ended:
            if st.button(t("Dial again"), type="primary", use_container_width=True):
                ss.ussd_chain = None
                st.rerun()
        else:
            with st.form("ussd_reply", clear_on_submit=True):
                reply = st.text_input(t("Your reply"), placeholder=t("Enter a number"),
                                      label_visibility="collapsed")
                c1, c2 = st.columns(2)
                send = c1.form_submit_button(t("Send"), type="primary", use_container_width=True)
                cancel = c2.form_submit_button(t("Cancel"), use_container_width=True)
            if send and reply.strip():
                ss.ussd_chain = f"{ss.ussd_chain}*{reply.strip()}" if ss.ussd_chain else reply.strip()
                st.rerun()
            if cancel:
                ss.ussd_chain = None
                st.rerun()

st.caption(t("Try: 1 (price) → 2 (Northern) → 4 (Musanze). The menu uses the same data "
             "and advice as the chat assistant."))