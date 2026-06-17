"""Settings: appearance (light/dark theme), language, and account.

Open to any signed-in user. The theme choice is kept in session_state and
applied by _ui.setup() (which injects the dark CSS when theme == "dark").
"""
from _ui import setup
from _i18n import t
import streamlit as st

user = setup("Settings", "Your account and preferences")

# ---- Appearance: light / dark theme ----
st.subheader(t("Appearance"))
st.session_state.setdefault("theme", "light")
options = [t("Light"), t("Dark")]
idx = 0 if st.session_state["theme"] == "light" else 1
choice = st.radio(t("Theme"), options, index=idx, horizontal=True, key="_theme_radio")
new_theme = "light" if choice == options[0] else "dark"
if new_theme != st.session_state["theme"]:
    st.session_state["theme"] = new_theme
    st.rerun()

# ---- Language (also available in the sidebar) ----
st.subheader(t("Language"))
st.caption("Ururimi / Language: use the switch in the sidebar. It applies to every page.")

# ---- Account ----
st.subheader(t("Account"))
st.write(f"**{t('Name')}:** {user.get('name','')}")
st.write(f"**{t('Role')}:** {user.get('role','')}")
if user.get("district"):
    st.write(f"**{t('District')}:** {user['district']}")
