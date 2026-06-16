"""AgriRisk Rwanda landing page — the full-screen app home, no sidebar.

Renders landing/index.html (the same file published to GitHub Pages) natively so
its links navigate in the same tab. The "Open the dashboard" buttons go to the
Dashboard hub (/Dashboard), which is where the tool sidebar lives.

Run: streamlit run dashboard/Home.py
"""
import re
from pathlib import Path

from _ui import ROOT
import streamlit as st

st.set_page_config(page_title="AgriRisk Rwanda", layout="wide",
                   initial_sidebar_state="collapsed")

raw = (Path(ROOT) / "landing" / "index.html").read_text(encoding="utf-8")
style = re.search(r"<style>.*?</style>", raw, re.S).group(0)
body = re.search(r"<body>(.*?)</body>", raw, re.S).group(1)
body = re.sub(r"<script>.*?</script>", "", body, flags=re.S)   # drop JS (Streamlit strips it anyway)
# in-app, the CTA opens the dashboard hub in the SAME tab. Streamlit only adds
# target="_blank" to markdown links that have no target, so we set _self.
body = body.replace(
    'href="https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd.streamlit.app/Dashboard"',
    'href="/Dashboard" target="_self"')

# fonts (the <link> in <head> is dropped) + overrides so Streamlit's chrome,
# background and link styling don't fight the landing design.
FONT = ("@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:"
        "opsz,wght@12..96,500;12..96,700;12..96,800&family=Inter:wght@400;500;600&"
        "family=JetBrains+Mono:wght@500;700&display=swap');")
OVERRIDE = """
.stApp{background:#F6F2E8 !important;}
header[data-testid="stHeader"],[data-testid="stToolbar"],#MainMenu,footer{display:none !important;}
section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none !important;}
.block-container,[data-testid="stMainBlockContainer"]{padding:0 !important;max-width:100% !important;}
[data-testid="stMarkdownContainer"] a{text-decoration:none !important;color:inherit !important;}
[data-testid="stMarkdownContainer"] .btn-go{color:#fff !important;}
[data-testid="stMarkdownContainer"] .band .btn-go{background:#fff !important;color:#C76E1B !important;}
[data-testid="stMarkdownContainer"] .btn-ghost{color:#1B4332 !important;}
[data-testid="stMarkdownContainer"] .brand{color:#1B4332 !important;}
.reveal{opacity:1 !important;transform:none !important;}
"""
style = style.replace("<style>", "<style>\n" + FONT + OVERRIDE)
st.markdown(style + body, unsafe_allow_html=True)