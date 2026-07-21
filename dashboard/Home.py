"""AgriRisk Rwanda landing page, the full-screen app home, no sidebar.

Renders landing/index.html (the same file published to GitHub Pages) natively so
its links navigate in the same tab. The "Open the dashboard" buttons go to the
Dashboard hub (/Dashboard), which is where the tool sidebar lives.

Kept deliberately light: importing _ui here would pull in pandas and the model
loaders (~1.3s) before the first paint, which is long enough to show Streamlit's
empty default page while the landing is still being built. We only needed ROOT.

Run: streamlit run dashboard/Home.py
"""
import base64
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:          # _auth imports config.settings from the repo root
    sys.path.insert(0, ROOT)

st.set_page_config(page_title="AgriRisk Rwanda", layout="wide",
                   initial_sidebar_state="collapsed")

# fonts (the <link> in <head> is dropped) + overrides so Streamlit's chrome,
# background and link styling don't fight the landing design.
FONT = "@import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600;1,700&display=swap');"
OVERRIDE = """
.stApp{background:#F6F2E8 !important;}
/* force the landing typeface (Poppins) over Streamlit's default Source Sans */
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *{font-family:'Poppins',sans-serif !important;}
header[data-testid="stHeader"],[data-testid="stToolbar"],#MainMenu{display:none !important;}
section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNav"]{display:none !important;}
.block-container,[data-testid="stMainBlockContainer"]{padding:0 !important;max-width:100% !important;}
[data-testid="stMarkdownContainer"] a{text-decoration:none !important;color:inherit !important;}
[data-testid="stMarkdownContainer"] .btn-go{color:#fff !important;}
[data-testid="stMarkdownContainer"] .band .btn-go{background:#fff !important;color:#2D6A4F !important;}
[data-testid="stMarkdownContainer"] .hero .btn-ghost{color:#fff !important;}
[data-testid="stMarkdownContainer"] .brand{color:#1B4332 !important;}
/* Scroll-driven reveal in-app: the landing's IntersectionObserver <script> is
   stripped by Streamlit, so drive the .reveal pop-in with pure CSS (no JS).
   Supported in Chromium/Edge; browsers without it just show the content. */
@keyframes agReveal{from{opacity:0;transform:translateY(30px) scale(.985)}to{opacity:1;transform:none}}
@supports (animation-timeline:view()){
  .reveal{animation:agReveal linear both;animation-timeline:view();animation-range:entry 5% cover 34%;}
}
@supports not (animation-timeline:view()){
  .reveal{opacity:1 !important;transform:none !important;}
}
"""

DEPLOYED_HREF = ('href="https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd'
                 '.streamlit.app/Dashboard"')


@st.cache_data(show_spinner=False)
def _landing_html():
    """Read the landing page and inline its images once, not on every rerun.

    The four photos are ~440 KB, so base64-encoding them per run was pure latency.
    """
    raw = (Path(ROOT) / "landing" / "index.html").read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", raw, re.S).group(0)
    body = re.search(r"<body>(.*?)</body>", raw, re.S).group(1)
    body = re.sub(r"<script>.*?</script>", "", body, flags=re.S)   # drop JS (Streamlit strips it anyway)

    # in-app, the CTA opens the dashboard hub in the SAME tab. Streamlit only adds
    # target="_blank" to markdown links that have no target, so we set _self.
    body = body.replace(DEPLOYED_HREF, 'href="/Dashboard" target="_self"')

    # Streamlit serves raw HTML from a virtual path, so the landing's relative
    # ../assets/<file> paths won't resolve. Inline the hero background and crop
    # photos as base64 data URIs. The background lives in <style>, photos in <body>.
    for name in ("background.jpg", "maize.jpg", "beans.jpg", "potatoes.jpg"):
        path = Path(ROOT) / "assets" / name
        if path.exists():
            uri = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
            style = style.replace(f"../assets/{name}", uri)
            body = body.replace(f"../assets/{name}", uri)

    return style.replace("<style>", "<style>\n" + FONT + OVERRIDE), body


style, body = _landing_html()

st.markdown(style + body, unsafe_allow_html=True)