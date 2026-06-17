"""Session-based login for the dashboard.

Authenticates against the users table (src/db/connection.authenticate) and gates
the tool pages by role. Auth lives in st.session_state, so it lasts for the
session and clears on a hard refresh. This is capstone-grade auth (hashed
passwords, role checks), not a hardened production identity system.
"""
import streamlit as st

from _i18n import t
from src.db.connection import authenticate

OFFICERS = ("officer", "super_admin")


def current_user():
    return st.session_state.get("auth_user")


def logout():
    st.session_state.pop("auth_user", None)


def _login_form():
    st.markdown(f"<div class='ar-head'>{t('Sign in')}</div>"
                f"<div class='ar-sub'>{t('For extension officers and administrators')}</div>",
                unsafe_allow_html=True)
    c, _ = st.columns([1, 1])
    with c:
        with st.form("login"):
            username = st.text_input(t("Username"))
            password = st.text_input(t("Password"), type="password")
            submitted = st.form_submit_button(t("Sign in"), type="primary")
        if submitted:
            user = authenticate((username or "").strip(), password or "")
            if user:
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error(t("Wrong username or password."))
        st.caption("Demo: **admin / admin123** (admin), **musanze / officer123** "
                   "(officer), **jean / farmer123** (farmer)")


def require_login():
    """Return the logged-in user, or render the login form and stop the page."""
    user = current_user()
    if user:
        return user
    _login_form()
    st.stop()


def require_role(allowed):
    """Require login and one of `allowed` roles, else show a notice and stop."""
    user = require_login()
    if user.get("role") not in allowed:
        st.warning(t("This screen is for extension officers. As a farmer, you get "
                     "the same advice by SMS and WhatsApp."))
        st.stop()
    return user


def sidebar_account(user):
    """Show who is signed in, plus a logout button, in the sidebar."""
    st.sidebar.markdown(
        f"<div style='font-size:12px;color:#74A98C'>{t('Signed in as')}</div>"
        f"<div style='font-weight:600;color:#D8F3DC'>{user.get('name','')}</div>"
        f"<div style='font-size:12px;color:#74A98C'>{user.get('role','')}</div>",
        unsafe_allow_html=True)
    if st.sidebar.button(t("Log out"), use_container_width=True):
        logout()
        st.rerun()