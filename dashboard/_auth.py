"""Session-based login for the dashboard.

Authenticates against the users table (src/db/connection.authenticate) and gates
the tool pages by role. Auth lives in st.session_state, so it lasts for the
session and clears on a hard refresh. This is capstone-grade auth (hashed
passwords, role checks), not a hardened production identity system.
"""
import base64
import hashlib
import hmac
import os
import time

import streamlit as st

from _i18n import t
from config.settings import DISTRICTS
from src.db.connection import (authenticate, add_user, get_user_by_username,
                               get_user_by_email, add_oauth_user)

OFFICERS = ("officer", "super_admin")

# ---------------------------------------------------------------------------
# Session persistence across full page reloads.
# Login lives in st.session_state, which a full browser reload wipes. Some
# in-app links (the dashboard tool cards, the footer) are plain <a href> anchors
# that DO reload, which used to drop the user back to the sign-in screen. To
# avoid that, we mint a short signed token on login and carry it in those links
# (auth_qs()); current_user() restores the session from it after a reload.
# ---------------------------------------------------------------------------
_TOKEN_TTL = 14 * 24 * 3600          # 14 days
_QP = "t"                            # query-param name that carries the token


def _secret() -> bytes:
    s = (os.getenv("AGRIRISK_SECRET") or "").strip()
    if not s:
        try:
            s = str(st.secrets.get("AGRIRISK_SECRET", "")).strip()
        except Exception:
            s = ""
    return (s or "agririsk-dev-secret").encode()


def _make_token(user: dict) -> str:
    """Signed, expiring token: base64('username.expiry.hmac')."""
    payload = f"{user.get('username', '')}.{int(time.time()) + _TOKEN_TTL}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{payload}.{sig}".encode()).decode()


def _user_from_token(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, exp, sig = raw.rsplit(".", 2)
        expect = hmac.new(_secret(), f"{username}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expect) or int(exp) < time.time():
            return None
        return get_user_by_username(username)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Google sign-in (OpenID Connect), via Streamlit's built-in st.login().
# Requires [auth] + [auth.google] in .streamlit/secrets.toml, and Authlib.
# When it isn't configured the button is hidden and password login is unaffected,
# so a fresh clone still runs with no OAuth setup.
# ---------------------------------------------------------------------------
GOOGLE_DEFAULT_ROLE = "farmer"     # least privilege; an admin promotes to officer


def google_enabled() -> bool:
    try:
        auth = st.secrets.get("auth", {})
        return bool(auth.get("google", {}).get("client_id"))
    except Exception:
        return False


def _oidc_identity():
    """(email, name) of the Google user, or (None, None) if not signed in."""
    try:
        u = st.user
        if not getattr(u, "is_logged_in", False):
            return None, None
        return (u.get("email") or "").strip().lower(), (u.get("name") or "").strip()
    except Exception:
        return None, None


def _user_from_google():
    """Map a verified Google identity to an app account, creating one if new."""
    email, name = _oidc_identity()
    if not email:
        return None
    user = get_user_by_email(email)
    if user:
        return user
    return add_oauth_user(name, email, role=GOOGLE_DEFAULT_ROLE,
                          language=st.session_state.get("lang", "en"))


def current_user():
    user = st.session_state.get("auth_user")
    if user:
        return user
    # restore from a token in the URL (survives the full reload some links cause)
    try:
        token = st.query_params.get(_QP)
    except Exception:
        token = None
    if token:
        user = _user_from_token(token)
        if user:
            st.session_state["auth_user"] = user
            st.session_state["auth_token"] = token
            return user
    # signed in with Google but no app session yet (e.g. straight after the redirect)
    if google_enabled():
        user = _user_from_google()
        if user:
            _start_session(user)
            return user
    return None


def auth_token() -> str:
    """The current user's token (for embedding in reload-style links), or ''.
    Calls current_user() first so a token in the URL (e.g. on the landing page,
    reached via the logo) restores the session before we hand it back out."""
    user = current_user()
    if not user:
        return ""
    tok = st.session_state.get("auth_token")
    if not tok:
        tok = _make_token(user)
        st.session_state["auth_token"] = tok
    return tok


def auth_qs() -> str:
    """'?t=<token>' to append to a plain-anchor link so a reload keeps the login."""
    tok = auth_token()
    return f"?{_QP}={tok}" if tok else ""


def _start_session(user):
    st.session_state["auth_user"] = user
    st.session_state["auth_token"] = _make_token(user)
    st.query_params[_QP] = st.session_state["auth_token"]   # so a refresh restores it


def logout():
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_token", None)
    try:
        if _QP in st.query_params:
            del st.query_params[_QP]
    except Exception:
        pass
    # end the Google session too, else current_user() would silently sign back in
    try:
        if google_enabled() and getattr(st.user, "is_logged_in", False):
            st.logout()
    except Exception:
        pass


def _login_form():
    with st.form("login"):
        username = st.text_input(t("Username"))
        password = st.text_input(t("Password"), type="password")
        submitted = st.form_submit_button(t("Sign in"), type="primary")
    if submitted:
        user = authenticate((username or "").strip(), password or "")
        if user:
            _start_session(user)
            st.rerun()
        else:
            st.error(t("Wrong username or password."))
    _google_button("signin")


def _google_button(key):
    """"Continue with Google", shown only when OIDC is configured.

    `key` must differ per call site: the button renders on both the sign-in and
    the sign-up tab, and Streamlit rejects two widgets sharing an id.
    """
    if not google_enabled():
        return
    st.markdown(
        "<div style='display:flex;align-items:center;gap:12px;margin:14px 0 10px;"
        "color:#5E7065;font-size:12px'>"
        "<div style='flex:1;height:1px;background:#DED7C4'></div>"
        f"{t('or')}"
        "<div style='flex:1;height:1px;background:#DED7C4'></div></div>",
        unsafe_allow_html=True)
    if st.button(t("Continue with Google"), use_container_width=True,
                 icon=":material/account_circle:", key=f"google_login_{key}"):
        st.login("google")


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
        _start_session(authenticate(username, pw))
        st.rerun()
    _google_button("signup")


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