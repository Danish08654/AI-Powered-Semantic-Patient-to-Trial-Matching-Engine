import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Clinical Trial Matcher",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Clinical Trial Match Engine")

CONDITIONS = [
    "non-small cell lung cancer", "breast cancer", "type 2 diabetes",
    "lymphoma", "alzheimer disease", "rheumatoid arthritis",
    "chronic kidney disease", "ovarian cancer", "crohn disease",
    "sickle cell disease", "melanoma", "depression",
    "hypertension", "asthma", "heart failure"
]

MEDICATIONS = [
    "metformin", "methotrexate", "aspirin", "lisinopril",
    "atorvastatin", "omeprazole", "levothyroxine",
    "amlodipine", "prednisone", "insulin"
]

#  Sidebar 
st.sidebar.header("Patient Profile")

patient_id  = st.sidebar.text_input("Patient ID", "PT0001")
age         = st.sidebar.slider("Age", 12, 85, 58)
gender      = st.sidebar.selectbox("Gender", ["Male", "Female"])
conditions  = st.sidebar.multiselect("Diagnosed Conditions", CONDITIONS,
                                      default=["type 2 diabetes"])
medications = st.sidebar.multiselect("Current Medications", MEDICATIONS,
                                      default=["metformin"])

st.sidebar.markdown("** Clinical Parameters**")
ecog        = st.sidebar.selectbox("ECOG Status", [0,1,2,3,4])
egfr_val    = st.sidebar.slider("eGFR (mL/min)", 10.0, 100.0, 55.0, 1.0)
bmi         = st.sidebar.slider("BMI", 15.0, 55.0, 28.5, 0.5)
prior_tx    = st.sidebar.slider("Prior Therapies", 0, 5, 1)
is_pregnant = st.sidebar.checkbox("Pregnant", False)

st.sidebar.markdown("** Biomarkers**")
egfr_mut  = st.sidebar.checkbox("EGFR Mutation Positive", False)
brca_mut  = st.sidebar.checkbox("BRCA Mutation Positive", False)
pdl1_pos  = st.sidebar.checkbox("PD-L1 Positive", False)
amyloid   = st.sidebar.checkbox("Amyloid Positive", False)

st.sidebar.markdown("** Settings**")
top_k     = st.sidebar.slider("Top matches to show", 1, 10, 5)

match_btn = st.sidebar.button("Find Matching Trials", type="primary",
                               use_container_width=True)

# Main 
col_left, col_right = st.columns([2, 1])

with col_right:
    st.subheader("Available Trials")
    try:
        trials_resp = requests.get(f"{API_URL}/trials")
        trials_list = trials_resp.json()
        for t in trials_list:
            st.markdown(
                f"**{t['trial_id']}** — {t['condition']}  \n"
                f"*{t['phase']} · {t['location']}*"
            )
    except:
        st.info("API not connected")

with col_left:
    if match_btn:
        if not conditions:
            st.warning("Please select at least one condition.")
            st.stop()

        payload = {
            "patient_id":          patient_id,
            "age":                 age,
            "gender":              gender,
            "conditions":          conditions,
            "current_medications": medications,
            "ecog_status":         ecog,
            "egfr_value":          egfr_val,
            "bmi":                 bmi,
            "prior_therapies":     prior_tx,
            "is_pregnant":         is_pregnant,
            "egfr_mutation":       egfr_mut,
            "brca_mutation":       brca_mut,
            "pdl1_positive":       pdl1_pos,
            "amyloid_positive":    amyloid,
            "top_k":               top_k,
        }

        with st.spinner("Running semantic matching..."):
            try:
                resp   = requests.post(f"{API_URL}/match", json=payload)
                result = resp.json()
            except Exception as e:
                st.error(f"API connection failed: {e}")
                st.stop()

        st.subheader(f"Top {top_k} Trial Matches — Patient {result['patient_id']}")

        eligible_count = sum(1 for m in result['matches'] if m['hard_eligible'])
        c1, c2, c3 = st.columns(3)
        c1.metric("Trials Searched",    result['total_trials'])
        c2.metric("Hard Eligible",       eligible_count)
        c3.metric("Avg Match Score",
                  f"{sum(m['eligibility_score'] for m in result['matches'])/len(result['matches']):.1f}")

        st.divider()

        for i, match in enumerate(result['matches']):
            tier_color = "🟢" if match['hard_eligible'] else "🔴"
            score_color= "green" if match['eligibility_score'] > 70 else \
                         "orange" if match['eligibility_score'] > 40 else "red"

            with st.expander(
                f"{tier_color} #{i+1} — {match['trial_id']}: {match['condition']} "
                f"| Score: {match['eligibility_score']:.1f}/100",
                expanded=(i == 0)
            ):
                ca, cb, cc, cd = st.columns(4)
                ca.metric("Eligibility Score",  f"{match['eligibility_score']:.1f}")
                cb.metric("Semantic Score",     f"{match['semantic_score']:.1f}")
                cc.metric("Hard Eligible",      "✅ Yes" if match['hard_eligible'] else "❌ No")
                cd.metric("Phase",              match['phase'])

                st.markdown(f"**{match['title']}**")
                st.markdown(f"*{match['sponsor']} · {match['location']}*")

                # Eligibility checks
                st.markdown("**Eligibility Checks:**")
                check_cols = st.columns(len(match['eligibility_checks']))
                for col, check in zip(check_cols, match['eligibility_checks']):
                    icon = "✅" if check['status'] == 'PASS' else \
                           "❌" if check['status'] == 'FAIL' else "⚠️"
                    col.markdown(f"{icon} **{check['criterion']}**")
                    col.caption(check['detail'])

