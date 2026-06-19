"""Session-based login for the dashboard.

Authenticates against the users table (src/db/connection.authenticate) and gates
the tool pages by role. Auth lives in st.session_state, so it lasts for the
session and clears on a hard refresh. This is capstone-grade auth (hashed
passwords, role checks), not a hardened production identity system.
"""
import streamlit as st

from _i18n import t
from config.settings import DISTRICTS
from src.db.connection import authenticate, add_user

OFFICERS = ("officer", "super_admin")


def current_user():
    return st.session_state.get("auth_user")


def logout():
    st.session_state.pop("auth_user", None)


def _login_form():
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


def _signup_form():
    with st.form("signup"):
        name = st.text_input(t("Full name"))
        username = st.text_input(t("Username"))
        c1, c2 = st.columns(2)
        pw = c1.text_input(t("Password"), type="password")
        pw2 = c2.text_input(t("Confirm password"), type="password")
        district = st.selectbox(t("District"), ["Nationwide"] + DISTRICTS)
        phone = st.text_input(t("Phone (optional)"))
        submitted = st.form_submit_button(t("Create account"), type="primary")
    # New accounts are farmers; an administrator promotes trusted users to officer.
    role = "farmer"
    st.caption(t("New accounts are farmers. An administrator can upgrade you to "
                 "extension officer."))
    if submitted:
        name, username = (name or "").strip(), (username or "").strip()
        if not (name and username and pw):
            st.error(t("Please fill in name, username and password."))
            return
        if pw != pw2:
            st.error(t("Passwords do not match."))
            return
        if len(pw) < 6:
            st.error(t("Password must be at least 6 characters."))
            return
        ok = add_user(name, role, district=district, phone=(phone.strip() or None),
                      language=st.session_state.get("lang", "en"),
                      username=username, password=pw)
        if not ok:
            st.error(t("That username or phone is already taken."))
            return
        st.session_state["auth_user"] = authenticate(username, pw)
        st.rerun()


def require_login():
    """Return the logged-in user, or render the sign-in / sign-up screen and stop."""
    user = current_user()
    if user:
        return user
    st.markdown(f"<div class='ar-head'>{t('Sign in')}</div>"
                f"<div class='ar-sub'>{t('For extension officers and administrators')}</div>",
                unsafe_allow_html=True)
    tab_in, tab_up = st.tabs([t("Sign in"), t("Create account")])
    with tab_in:
        _login_form()
    with tab_up:
        _signup_form()
    st.stop()


def require_role(allowed):
    """Require login and one of `allowed` roles, else show a notice and stop."""
    user = require_login()
    if user.get("role") not in allowed:
        st.warning(t("This screen is for extension officers. As a farmer, you get "
                     "the same advice by SMS and WhatsApp."))
        st.stop()
    return user


def sidebar_account(user, dg=None):
    """Show who is signed in, plus a logout button. `dg` is the target container
    (defaults to the sidebar) so placement in the pinned bottom group is reliable."""
    dg = dg or st.sidebar
    dg.markdown(
        f"<div style='font-size:11px;color:#5E7065;margin-top:4px;letter-spacing:.04em;"
        f"text-transform:uppercase'>{t('Signed in as')}</div>"
        f"<div style='font-weight:600;color:#1B4332;font-size:15px'>{user.get('name','')}</div>"
        f"<div style='font-size:12.5px;color:#5E7065;margin-bottom:8px;text-transform:capitalize'>{user.get('role','')}</div>",
        unsafe_allow_html=True)
    if dg.button(t("Log out"), use_container_width=True, icon=":material/logout:"):
        logout()
        st.rerun()