"""TAM pilot questionnaire (RQ4).

The 12-item Technology Acceptance Model instrument the proposal specifies,
adapted from Davis (1989) and Venkatesh & Davis (2000): four items each for
perceived usefulness, perceived ease of use and satisfaction, on a 5-point
Likert scale. Four items per construct is what makes Cronbach's alpha (internal
consistency) computable, so the items are stored individually.

Extension officers answer in two phases, per the proposal: a confidence
*baseline* before they use the platform, and the full questionnaire afterwards.
RQ4 asks whether platform access produces a measurable *improvement* in
confidence, which a post-only rating cannot show. Farmers answer once.

Ethics (per the proposal): no names or phone numbers are stored, and the row
carries no account id either. Each participant is identified only by an anonymous
code (EO-01..EO-20 for extension officers, FM-01..FM-20 for farmers). Export the
responses with scripts/export_feedback.py for the pilot analysis.
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
    t("A short questionnaire about how useful and easy to use AgriRisk is. Your answers "
      "are anonymous, we store only your participant code, never your name or phone."),
    meta_strong="1-5", meta_sub=t("strongly disagree to strongly agree"))

MODULES = ["Overall platform", "Price Forecast", "Seasonal Risk",
           "Disease Alert", "Input Recommender"]
LIKERT = {1: t("Strongly disagree"), 2: t("Disagree"), 3: t("Neutral"),
          4: t("Agree"), 5: t("Strongly agree")}

# The 12 items, 4 per construct (Davis 1989; Venkatesh & Davis 2000).
PU_ITEMS = [
    "Using AgriRisk improves the farming decisions I make.",
    "Using AgriRisk saves me time when I need crop or market information.",
    "Using AgriRisk makes it easier to plan the season.",
    "Overall, I find AgriRisk useful in my work.",
]
PEOU_ITEMS = [
    "Learning to use AgriRisk was easy for me.",
    "I can get AgriRisk to show me what I want without difficulty.",
    "The information AgriRisk gives me is clear and understandable.",
    "Overall, I find AgriRisk easy to use.",
]
SAT_ITEMS = [
    "I am satisfied with the advice AgriRisk gives.",
    "AgriRisk meets my needs for crop and market information.",
    "I would recommend AgriRisk to other farmers or officers.",
    "Overall, I am satisfied with AgriRisk.",
]
# identical wording in both phases, so the two scores are comparable
CONFIDENCE_ITEM = "I feel confident giving advice based on data."


def likert(label, key):
    return st.select_slider(label, options=[1, 2, 3, 4, 5], value=3,
                            format_func=lambda x: f"{x} · {LIKERT[x]}", key=key)


def block(title, help_text, items, prefix):
    st.markdown(f"**{title}**")
    st.caption(help_text)
    scores = [likert(t(item), f"{prefix}{i}") for i, item in enumerate(items, start=1)]
    st.markdown("---")
    return scores


c1, c2 = st.columns(2)
role_label = c1.radio(t("You are a"), [t("Extension officer"), t("Farmer")], horizontal=True)
is_officer = role_label == t("Extension officer")

# Officers alone do the pre-post confidence assessment the proposal asks for.
if is_officer:
    phase_label = c2.radio(
        t("Which stage?"),
        [t("Before using AgriRisk (baseline)"), t("After using AgriRisk")],
        help=t("Answer the baseline once before you start, then the full questionnaire "
               "after you have used the platform. Use the same participant code both times."))
    is_pre = phase_label == t("Before using AgriRisk (baseline)")
else:
    is_pre = False

with st.form("tam_form", border=False):
    code = st.text_input(t("Participant code"), placeholder="EO-01 / FM-01",
                         help=t("Anonymous code given to you by the researcher. "
                                "Use the same code every time you answer."))

    pu = peou = sat = []
    module = None

    if is_pre:
        st.info(t("Baseline: answer this one question before you start using AgriRisk."))
        conf = likert(t(CONFIDENCE_ITEM), "conf")
        comments = None
    else:
        module = st.selectbox(t("Which part are you rating?"), MODULES)
        st.markdown("---")
        pu = block(t("Perceived usefulness"),
                   t("Does AgriRisk help you do your work?"), PU_ITEMS, "pu")
        peou = block(t("Perceived ease of use"),
                     t("Is AgriRisk easy to work with?"), PEOU_ITEMS, "peou")
        sat = block(t("Satisfaction"),
                    t("How do you feel about AgriRisk overall?"), SAT_ITEMS, "sat")
        st.markdown(f"**{t('Confidence in data-driven advisories')}**")
        conf = likert(t(CONFIDENCE_ITEM), "conf")
        comments = st.text_area(t("Anything else? (optional)"), placeholder=t("Your comments…"))

    submitted = st.form_submit_button(t("Submit feedback"), type="primary")

if submitted:
    if not code.strip():
        st.error(t("Please enter your participant code (for example EO-01)."))
    else:
        role = "extension_officer" if is_officer else "farmer"
        ok = submit_tam_feedback(code, role, "pre" if is_pre else "post",
                                 pu_items=pu, peou_items=peou, sat_items=sat,
                                 confidence=conf, module_name=module, comments=comments)
        if not ok:
            st.error(t("Could not save your response. Please try again."))
        elif is_pre:
            st.success(t("Baseline recorded. Come back after using AgriRisk to finish."))
            insight_panel([("var(--ag-soil)", t("Confidence"), f"{conf}/5 · {LIKERT[conf]}")],
                          lead=t("Your baseline"), strong=t("Recorded"),
                          meta=f"{code.upper()} · {t('before use')}")
        else:
            def _mean(xs):
                return round(sum(xs) / len(xs), 1)
            st.success(t("Thank you! Your response was recorded anonymously."))
            insight_panel([
                ("var(--ag-sage)", t("Usefulness"), f"{_mean(pu)}/5"),
                ("var(--ag-slate)", t("Ease of use"), f"{_mean(peou)}/5"),
                ("var(--ag-terra)", t("Satisfaction"), f"{_mean(sat)}/5"),
                ("var(--ag-soil)", t("Confidence"), f"{conf}/5 · {LIKERT[conf]}"),
            ], lead=t("What you told us"), strong=t("Recorded"),
                meta=f"{code.upper()} · {module}")

st.markdown(f"""<div class="ag-foot">
  <div><span class="label">{t('Privacy')}:</span> {t('Anonymous. No names or phone numbers are stored.')}</div>
  <div><span class="label">{t('Purpose')}:</span> {t('Academic evaluation of the AgriRisk pilot.')}</div>
</div>""", unsafe_allow_html=True)