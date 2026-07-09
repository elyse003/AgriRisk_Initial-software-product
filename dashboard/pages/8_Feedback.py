"""TAM pilot questionnaire (RQ4).

Collects the Technology Acceptance Model constructs the proposal promised to
measure, perceived usefulness, perceived ease of use, satisfaction, and the
officer's confidence in delivering data-driven advisories, and stores them
anonymously in the feedback table.

Ethics (per the proposal): no names or phone numbers are stored. Each participant
is identified only by an anonymous code (EO-01..EO-20 for extension officers,
FM-01..FM-20 for farmers), and responses can be exported with
scripts/export_feedback.py for the pilot analysis.
"""
from _ui import setup, page_header, insight_panel
from _i18n import t
import streamlit as st
from src.db.connection import submit_tam_feedback

user = setup("Feedback", "Help us evaluate AgriRisk",
             allowed_roles=("farmer", "officer", "super_admin"), header=False)

page_header(
    t("FEEDBACK"),
    f"<em>{t('Your experience')}</em> · {t('AgriRisk pilot')}",
    t("Four short questions about how useful and easy to use AgriRisk is. Your answers "
      "are anonymous, we store only your participant code, never your name or phone."),
    meta_strong="1-5", meta_sub=t("strongly disagree to strongly agree"))

MODULES = ["Overall platform", "Price Forecast", "Seasonal Risk",
           "Disease Alert", "Input Recommender"]
LIKERT = {1: t("Strongly disagree"), 2: t("Disagree"), 3: t("Neutral"),
          4: t("Agree"), 5: t("Strongly agree")}


def likert(label, help_text, key):
    v = st.select_slider(label, options=[1, 2, 3, 4, 5], value=3,
                         format_func=lambda x: f"{x} · {LIKERT[x]}", key=key)
    st.caption(help_text)
    return v


with st.form("tam_form", border=False):
    c1, c2 = st.columns(2)
    code = c1.text_input(t("Participant code"), placeholder="EO-01 / FM-01",
                         help=t("Anonymous code given to you by the researcher."))
    role_label = c2.radio(t("You are a"), [t("Extension officer"), t("Farmer")], horizontal=True)
    module = st.selectbox(t("Which part are you rating?"), MODULES)

    st.markdown("---")
    pu = likert(t("AgriRisk helps me make better farming decisions."),
                t("Perceived usefulness"), "pu")
    peou = likert(t("AgriRisk is easy to use."), t("Perceived ease of use"), "peou")
    sat = likert(t("Overall, I am satisfied with AgriRisk."), t("Satisfaction"), "sat")
    conf = likert(t("I feel more confident giving advice based on data."),
                  t("Confidence in data-driven advisories"), "conf")
    comments = st.text_area(t("Anything else? (optional)"), placeholder=t("Your comments…"))

    submitted = st.form_submit_button(t("Submit feedback"), type="primary")

if submitted:
    if not code.strip():
        st.error(t("Please enter your participant code (for example EO-01)."))
    else:
        role = "extension_officer" if role_label == t("Extension officer") else "farmer"
        ok = submit_tam_feedback(code, role, module, pu, peou, sat, conf,
                                 comments or None)
        if ok:
            st.success(t("Thank you! Your response was recorded anonymously."))
            insight_panel([
                ("var(--ag-sage)", t("Usefulness"), f"{pu}/5 · {LIKERT[pu]}"),
                ("var(--ag-slate)", t("Ease of use"), f"{peou}/5 · {LIKERT[peou]}"),
                ("var(--ag-terra)", t("Satisfaction"), f"{sat}/5 · {LIKERT[sat]}"),
                ("var(--ag-soil)", t("Confidence"), f"{conf}/5 · {LIKERT[conf]}"),
            ], lead=t("What you told us"), strong=t("Recorded"), meta=f"{code.upper()} · {module}")
        else:
            st.error(t("Could not save your response. Please try again."))

st.markdown(f"""<div class="ag-foot">
  <div><span class="label">{t('Privacy')}:</span> {t('Anonymous. No names or phone numbers are stored.')}</div>
  <div><span class="label">{t('Purpose')}:</span> {t('Academic evaluation of the AgriRisk pilot.')}</div>
</div>""", unsafe_allow_html=True)