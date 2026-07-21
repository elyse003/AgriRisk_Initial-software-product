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
        # Keep the signed token in the URL on EVERY authenticated render. Sidebar
        # page-links drop query params, so without this a full browser reload (F5)
        # would find no token, lose the session, and bounce to the login screen.
        # Re-asserting it here means a reload restores the session on the SAME page.
        tok = st.session_state.get("auth_token") or _make_token(user)
        st.session_state["auth_token"] = tok
        try:
            if st.query_params.get(_QP) != tok:
                st.query_params[_QP] = tok
        except Exception:
            pass
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


# ---------------------------------------------------------------------------
# Sign-in screen: a single centred card. The Google button is a real st.button
# (so it can call st.login) restyled via its .st-key-* container, because a
# Streamlit button cannot hold inline SVG. The G is a base64 data URI, so the
# logo needs no network request and no static asset.
# ---------------------------------------------------------------------------
_G_ICON = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0OCA0OCI+PHBhdGggZmlsbD0iI0VBNDMzNSIgZD0iTTI0IDkuNWMzLjU0IDAgNi43MSAxLjIyIDkuMjEgMy42bDYuODUtNi44NUMzNS45IDIuMzggMzAuNDcgMCAyNCAwIDE0LjYyIDAgNi41MSA1LjM4IDIuNTYgMTMuMjJsNy45OCA2LjE5QzEyLjQzIDEzLjcyIDE3Ljc0IDkuNSAyNCA5LjV6Ii8+PHBhdGggZmlsbD0iIzQyODVGNCIgZD0iTTQ2Ljk4IDI0LjU1YzAtMS41Ny0uMTUtMy4wOS0uMzgtNC41NUgyNHY5LjAyaDEyLjk0Yy0uNTggMi45Ni0yLjI2IDUuNDgtNC43OCA3LjE4bDcuNzMgNmM0LjUxLTQuMTggNy4wOS0xMC4zNiA3LjA5LTE3LjY1eiIvPjxwYXRoIGZpbGw9IiNGQkJDMDUiIGQ9Ik0xMC41MyAyOC41OWMtLjQ4LTEuNDUtLjc2LTIuOTktLjc2LTQuNTlzLjI3LTMuMTQuNzYtNC41OWwtNy45OC02LjE5Qy45MiAxNi40NiAwIDIwLjEyIDAgMjRjMCAzLjg4LjkyIDcuNTQgMi41NiAxMC43OGw3Ljk3LTYuMTl6Ii8+PHBhdGggZmlsbD0iIzM0QTg1MyIgZD0iTTI0IDQ4YzYuNDggMCAxMS45My0yLjEzIDE1Ljg5LTUuODFsLTcuNzMtNmMtMi4xNSAxLjQ1LTQuOTIgMi4zLTguMTYgMi4zLTYuMjYgMC0xMS41Ny00LjIyLTEzLjQ3LTkuOTFsLTcuOTggNi4xOUM2LjUxIDQyLjYyIDE0LjYyIDQ4IDI0IDQ4eiIvPjwvc3ZnPg=="

LOGIN_CSS = """
<style>
.st-key-ag_login{ max-width:430px; margin:26px auto 0; background:#fff;
  border:1px solid var(--line); border-radius:16px; padding:0 26px 22px;
  box-shadow:0 12px 34px rgba(27,67,50,.07); }
.ag-login-brand{ display:flex; align-items:center; justify-content:center; gap:10px;
  padding:22px 0 18px; margin:0 -26px 20px; border-bottom:1px solid var(--line); }
.ag-login-brand .seed{ width:22px; height:22px; border-radius:50% 50% 50% 0;
  background:var(--emerald); transform:rotate(-45deg); box-shadow:inset -3px -3px 0 rgba(0,0,0,.08); }
.ag-login-brand .nm{ font-style:italic; font-weight:700; font-size:23px; color:var(--forest);
  letter-spacing:-.01em; }
/* uppercase field labels, like the reference */
.st-key-ag_login [data-testid="stWidgetLabel"] p{ font-size:11px; font-weight:600;
  letter-spacing:.08em; text-transform:uppercase; color:var(--mut); }
.st-key-ag_login [data-testid="stForm"]{ border:none; padding:0; }
/* the inputs sit on a white card, so they need their own fill and border */
.st-key-ag_login .stTextInput div[data-baseweb="input"]{
  background:#FBF9F3 !important; border:1px solid var(--line) !important; border-radius:8px; }
/* the password field nests a second baseweb box for the reveal icon: no border on it */
.st-key-ag_login .stTextInput div[data-baseweb="base-input"]{
  background:transparent !important; border:none !important; }
.st-key-ag_login .stTextInput input{ background:transparent !important; }
.st-key-ag_login .stTextInput div[data-baseweb="input"]:focus-within{ border-color:var(--emerald) !important; }
/* primary: full-width AgriRisk green (Streamlit sizes buttons to their label) */
.st-key-ag_login [data-testid="stFormSubmitButton"]{ width:100%; }
.st-key-ag_login [data-testid="stFormSubmitButton"] button{ width:100% !important;
  background:var(--forest) !important; color:#fff !important; border:none !important;
  border-radius:8px; padding:11px 0; font-weight:700 !important; letter-spacing:.07em;
  text-transform:uppercase; font-size:13px; margin-top:4px; }
.st-key-ag_login [data-testid="stFormSubmitButton"] button:hover{ background:#15392a !important; }
/* the OR rule */
.ag-or{ display:flex; align-items:center; gap:14px; margin:18px 0 14px;
  color:var(--mut); font-size:11px; letter-spacing:.12em; }
.ag-or:before,.ag-or:after{ content:""; flex:1; height:1px; background:var(--line); }
/* Google: white, bordered, four-colour G before the label */
div[class*="st-key-google_login"] button{ background:#fff !important; color:var(--ink) !important;
  border:1px solid var(--line) !important; border-radius:8px; font-weight:600 !important; }
div[class*="st-key-google_login"] button:hover{ border-color:var(--emerald) !important;
  background:#fff !important; }
div[class*="st-key-google_login"] button p{ display:inline-flex; align-items:center; }
div[class*="st-key-google_login"] button p:before{ content:""; width:18px; height:18px;
  margin-right:10px; flex:0 0 18px;
  background:url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0OCA0OCI+PHBhdGggZmlsbD0iI0VBNDMzNSIgZD0iTTI0IDkuNWMzLjU0IDAgNi43MSAxLjIyIDkuMjEgMy42bDYuODUtNi44NUMzNS45IDIuMzggMzAuNDcgMCAyNCAwIDE0LjYyIDAgNi41MSA1LjM4IDIuNTYgMTMuMjJsNy45OCA2LjE5QzEyLjQzIDEzLjcyIDE3Ljc0IDkuNSAyNCA5LjV6Ii8+PHBhdGggZmlsbD0iIzQyODVGNCIgZD0iTTQ2Ljk4IDI0LjU1YzAtMS41Ny0uMTUtMy4wOS0uMzgtNC41NUgyNHY5LjAyaDEyLjk0Yy0uNTggMi45Ni0yLjI2IDUuNDgtNC43OCA3LjE4bDcuNzMgNmM0LjUxLTQuMTggNy4wOS0xMC4zNiA3LjA5LTE3LjY1eiIvPjxwYXRoIGZpbGw9IiNGQkJDMDUiIGQ9Ik0xMC41MyAyOC41OWMtLjQ4LTEuNDUtLjc2LTIuOTktLjc2LTQuNTlzLjI3LTMuMTQuNzYtNC41OWwtNy45OC02LjE5Qy45MiAxNi40NiAwIDIwLjEyIDAgMjRjMCAzLjg4LjkyIDcuNTQgMi41NiAxMC43OGw3Ljk3LTYuMTl6Ii8+PHBhdGggZmlsbD0iIzM0QTg1MyIgZD0iTTI0IDQ4YzYuNDggMCAxMS45My0yLjEzIDE1Ljg5LTUuODFsLTcuNzMtNmMtMi4xNSAxLjQ1LTQuOTIgMi4zLTguMTYgMi4zLTYuMjYgMC0xMS41Ny00LjIyLTEzLjQ3LTkuOTFsLTcuOTggNi4xOUM2LjUxIDQyLjYyIDE0LjYyIDQ4IDI0IDQ4eiIvPjwvc3ZnPg==") center/contain no-repeat; }
/* secondary row: forgot password / sign up */
div[class*="st-key-ag_alt"] button{ background:#fff !important; color:var(--mut) !important;
  border:1px solid var(--line) !important; border-radius:8px; font-weight:600 !important;
  font-size:11.5px; letter-spacing:.06em; text-transform:uppercase; }
div[class*="st-key-ag_alt"] button:hover{ color:var(--forest) !important;
  border-color:var(--emerald) !important; background:#fff !important; }
/* "FORGOT PASSWORD?" wrapped onto two lines in its half-width column */
div[class*="st-key-ag_alt"] button p{ white-space:nowrap; font-size:10.5px; letter-spacing:.04em; }
</style>
"""


def _brand():
    st.markdown("<div class='ag-login-brand'><span class='seed'></span>"
                "<span class='nm'>AgriRisk</span></div>", unsafe_allow_html=True)


def _login_form():
    with st.form("login", border=False):
        username = st.text_input(t("Username"))
        password = st.text_input(t("Password"), type="password")
        submitted = st.form_submit_button(t("Log in"), type="primary", use_container_width=True)
    if submitted:
        user = authenticate((username or "").strip(), password or "")
        if user:
            _start_session(user)
            st.rerun()
        else:
            st.error(t("Wrong username or password."))

    _google_button("signin")

    c1, c2 = st.columns(2)
    if c1.button(t("Forgot password?"), key="ag_alt_forgot", use_container_width=True):
        st.info(t("Ask an administrator to reset it for you in User Management."))
    if c2.button(t("Sign up"), key="ag_alt_signup", use_container_width=True):
        st.session_state["auth_view"] = "signup"
        st.rerun()


def _google_button(key):
    """"Continue with Google", shown only when OIDC is configured.

    `key` must differ per call site: the button renders on the sign-in and the
    sign-up view, and Streamlit rejects two widgets sharing an id.
    """
    if not google_enabled():
        return
    st.markdown(f"<div class='ag-or'>{t('OR')}</div>", unsafe_allow_html=True)
    if st.button(t("Log in with Google"), use_container_width=True,
                 key=f"google_login_{key}"):
        st.login("google")


def _signup_form():
    with st.form("signup", border=False):
        name = st.text_input(t("Full name"))
        username = st.text_input(t("Username"))
        c1, c2 = st.columns(2)
        pw = c1.text_input(t("Password"), type="password")
        pw2 = c2.text_input(t("Confirm password"), type="password")
        district = st.selectbox(t("District"), ["Nationwide"] + DISTRICTS)
        phone = st.text_input(t("Phone (optional)"))
        submitted = st.form_submit_button(t("Create account"), type="primary", use_container_width=True)
    # New accounts are farmers; an administrator promotes trusted users to officer.
    st.caption(t("New accounts are farmers. An administrator can upgrade you to "
                 "extension officer."))
    if submitted:
        name, username = (name or "").strip(), (username or "").strip()
        if not (name and username and pw):
            st.error(t("Please fill in name, username and password."))
        elif pw != pw2:
            st.error(t("Passwords do not match."))
        elif len(pw) < 6:
            st.error(t("Password must be at least 6 characters."))
        else:
            ok = add_user(name, "farmer", district=district, phone=(phone.strip() or None),
                          language=st.session_state.get("lang", "en"),
                          username=username, password=pw)
            if not ok:
                st.error(t("That username or phone is already taken."))
            else:
                _start_session(authenticate(username, pw))
                st.rerun()

    _google_button("signup")

    if st.button(t("Back to sign in"), key="ag_alt_back", use_container_width=True):
        st.session_state["auth_view"] = "signin"
        st.rerun()


def require_login():
    """Return the logged-in user, or render the sign-in card and stop."""
    user = current_user()
    if user:
        return user
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.container(key="ag_login"):
        _brand()
        if st.session_state.get("auth_view") == "signup":
            _signup_form()
        else:
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