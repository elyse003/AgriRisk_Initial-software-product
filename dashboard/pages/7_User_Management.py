"""User management (super_admin only): view, add, edit, reset, and remove users."""
from _ui import setup
from _i18n import t
from src.db.connection import (list_users, add_user, update_user, set_password,
                               delete_user, role_counts)
from config.settings import DISTRICTS, LANGUAGES
import streamlit as st

user = setup("User Management", "Manage accounts and roles")
if user.get("role") != "super_admin":
    st.error(t("This page is for administrators only."))
    st.stop()

ROLES = ["farmer", "officer", "super_admin"]
DISTRICT_OPTS = ["Nationwide"] + DISTRICTS

def _idx(options, value, default=0):
    return options.index(value) if value in options else default

# ---- role counts ----
rc = role_counts()
c1, c2, c3 = st.columns(3)
c1.metric("Administrators", rc.get("super_admin", 0))
c2.metric("Officers", rc.get("officer", 0))
c3.metric("Farmers", rc.get("farmer", 0))

# ---- all users ----
df = list_users()
st.dataframe(df.set_index("user_id"), use_container_width=True)

# ---- add a user ----
with st.expander("➕ Add a user"):
    with st.form("add_user", clear_on_submit=True):
        name = st.text_input("Full name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        a1, a2, a3 = st.columns(3)
        role = a1.selectbox("Role", ROLES, key="add_role")
        district = a2.selectbox("District", DISTRICT_OPTS, key="add_dist")
        lang = a3.selectbox("Language", LANGUAGES, key="add_lang")
        phone = st.text_input("Phone (optional)")
        if st.form_submit_button("Create user", type="primary"):
            if not (name.strip() and username.strip() and password):
                st.error("Fill in name, username and password.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif add_user(name.strip(), role, district=district, phone=(phone.strip() or None),
                          language=lang, username=username.strip(), password=password):
                st.success(f"Created user '{username.strip()}'.")
                st.rerun()
            else:
                st.error("That username or phone is already taken.")

# ---- edit / remove a user ----
st.subheader("Edit or remove a user")
if df.empty:
    st.info("No users yet.")
else:
    labels = {f"{r.username}  ·  {r['name']} ({r.role})": int(r.user_id) for _, r in df.iterrows()}
    pick = st.selectbox("Select a user", list(labels))
    uid = labels[pick]
    sel = df[df.user_id == uid].iloc[0]

    e1, e2 = st.columns(2)
    new_role = e1.selectbox("Role", ROLES, index=_idx(ROLES, sel.role), key="edit_role")
    new_district = e2.selectbox("District", DISTRICT_OPTS,
                                index=_idx(DISTRICT_OPTS, sel.district), key="edit_dist")
    if st.button("Save changes", type="primary"):
        update_user(uid, role=new_role, district=new_district)
        st.success("Saved.")
        st.rerun()

    np1, np2 = st.columns([2, 1])
    new_pw = np1.text_input("Reset password (new password)", type="password", key="reset_pw")
    if np2.button("Reset", use_container_width=True):
        if new_pw and len(new_pw) >= 6:
            set_password(uid, new_pw)
            st.success(f"Password reset for '{sel.username}'.")
        else:
            st.error("New password must be at least 6 characters.")

    st.divider()
    if uid == user.get("user_id"):
        st.caption("You can't delete the account you are signed in with.")
    else:
        if st.button(f"🗑 Delete '{sel.username}'", type="secondary"):
            delete_user(uid)
            st.success(f"Deleted '{sel.username}'.")
            st.rerun()
