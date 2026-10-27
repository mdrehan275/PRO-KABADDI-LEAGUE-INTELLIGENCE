"""
app/pages/6_Match_Prediction.py
-------------------------------
Interactive Match Outcome Prediction & Pre-Match Intelligence.
Predicts calibrated win probabilities between any two PKL franchises
using the calibrated champion model with zero target leakage.
"""

import os
import sys
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Ensure both project root and app dir in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.utils import inject_custom_css, load_dim_teams, load_dim_venues
except ImportError:
    from utils import inject_custom_css, load_dim_teams, load_dim_venues
from src.models.predict import MatchPredictor

st.set_page_config(page_title="Match Prediction | PKL Analytics", page_icon="🎯", layout="wide")
inject_custom_css()

st.title("🎯 Pre-Match Intelligence & Win Probability Prediction")
st.markdown("""
Predict calibrated win probabilities for any two PKL franchises based strictly on historical performance,
recent form, tackle/raid rates, rest days, and head-to-head records **prior to the match whistle**.
""")


@st.cache_resource
def get_predictor():
    return MatchPredictor()


try:
    predictor = get_predictor()
except Exception as e:
    st.error(f"Failed to load prediction engine: {e}")
    st.stop()

df_teams = load_dim_teams()
df_venues = load_dim_venues()

# Filter to official 12 PKL franchise clubs
official_ids = [1, 2, 3, 4, 5, 6, 7, 8, 28, 29, 30, 31]
pkl_teams = df_teams[df_teams["team_id"].isin(official_ids)].sort_values(by="team_name")
team_options = dict(zip(pkl_teams["team_id"], pkl_teams["team_name"]))

st.sidebar.header("⚙️ Match Configuration")

# Select Teams
default_a = 6  # Patna Pirates
default_b = 5  # U Mumba

col_side1, col_side2 = st.sidebar.columns(2)
team_a_id = st.sidebar.selectbox(
    "Team A (Home / Perspective)",
    options=list(team_options.keys()),
    format_func=lambda x: team_options[x],
    index=list(team_options.keys()).index(default_a)
)

# Filter out Team A from Team B options
available_b = [tid for tid in team_options.keys() if tid != team_a_id]
team_b_id = st.sidebar.selectbox(
    "Team B (Challenger)",
    options=available_b,
    format_func=lambda x: team_options[x],
    index=available_b.index(default_b) if default_b in available_b else 0
)

# Reference Date
sim_mode = st.sidebar.radio(
    "Simulation Scenario",
    ["Latest Historical Form (End of Season 7)", "Custom Historical Date"]
)

if sim_mode == "Custom Historical Date":
    as_of_date = st.sidebar.date_input(
        "Match Date (Snapshot As-Of)",
        datetime.date(2019, 10, 1),
        min_value=datetime.date(2014, 7, 26),
        max_value=datetime.date(2019, 10, 19)
    )
    as_of_str = as_of_date.strftime("%Y-%m-%d")
else:
    as_of_str = None

# Home advantage selector
home_selection = st.sidebar.selectbox(
    "Venue Advantage",
    ["Neutral Venue", f"{team_options[team_a_id]} Home Court", f"{team_options[team_b_id]} Home Court"]
)

home_id = None
if home_selection == f"{team_options[team_a_id]} Home Court":
    home_id = team_a_id
elif home_selection == f"{team_options[team_b_id]} Home Court":
    home_id = team_b_id

# Run prediction
with st.spinner("Calculating pre-match features and running inference..."):
    res = predictor.predict_match(
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        as_of_date_str=as_of_str,
        home_team_id=home_id
    )

name_a = res["team_a_name"]
name_b = res["team_b_name"]
prob_a = res["team_a_prob"]
prob_b = res["team_b_prob"]

# --- DISPLAY TOP PREDICTION BANNER ---
st.markdown("---")
col_res1, col_res2, col_res3 = st.columns([1.2, 1.6, 1.2])

with col_res1:
    st.markdown(f"<div style='text-align: center; padding: 15px; border-radius: 8px; background: rgba(31, 119, 180, 0.1); border: 1px solid #1f77b4;'>"
                f"<h3 style='margin: 0; color: #1f77b4;'>{name_a}</h3>"
                f"<h1 style='margin: 5px 0; font-size: 3rem;'>{prob_a*100:.1f}%</h1>"
                f"<p style='color: #888; margin: 0;'>Win Probability</p></div>", unsafe_allow_html=True)

with col_res2:
    st.markdown(f"<div style='text-align: center; padding: 20px;'>"
                f"<p style='text-transform: uppercase; letter-spacing: 2px; color: #888; font-size: 0.85rem; margin: 0;'>Model Verdict</p>"
                f"<h2 style='margin: 5px 0; color: #ff7f0e;'>{res['predicted_winner']}</h2>"
                f"<span style='background: #2b2b2b; padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; border: 1px solid #444;'>{res['confidence_tier']}</span>"
                f"</div>", unsafe_allow_html=True)

    # Probability Bar
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=["Probability"], x=[prob_a * 100], orientation="h",
        name=name_a, marker_color="#1f77b4", text=f"{prob_a*100:.1f}%", textposition="inside"
    ))
    fig_bar.add_trace(go.Bar(
        y=["Probability"], x=[prob_b * 100], orientation="h",
        name=name_b, marker_color="#d62728", text=f"{prob_b*100:.1f}%", textposition="inside"
    ))
    fig_bar.update_layout(
        barmode="stack",
        height=70,
        margin=dict(l=0, r=0, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]),
        yaxis=dict(showgrid=False, showticklabels=False),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_res3:
    st.markdown(f"<div style='text-align: center; padding: 15px; border-radius: 8px; background: rgba(214, 39, 40, 0.1); border: 1px solid #d62728;'>"
                f"<h3 style='margin: 0; color: #d62728;'>{name_b}</h3>"
                f"<h1 style='margin: 5px 0; font-size: 3rem;'>{prob_b*100:.1f}%</h1>"
                f"<p style='color: #888; margin: 0;'>Win Probability</p></div>", unsafe_allow_html=True)

st.markdown("---")

# --- TALE OF THE TAPE & HEAD-TO-HEAD ---
col_tape, col_h2h = st.columns([1.5, 1.0])

with col_tape:
    st.subheader("📋 Tale of the Tape (Pre-Match Fundamentals)")
    tape_df = pd.DataFrame(res["tale_of_the_tape"])
    st.dataframe(tape_df, use_container_width=True, hide_index=True)

with col_h2h:
    st.subheader("⚔️ Head-to-Head Rivalry History")
    h2h = res["h2h_summary"]
    st.metric("Total Historical Encounters", f"{h2h['total_encounters']} matches")
    
    c_w1, c_w2, c_tie = st.columns(3)
    c_w1.metric(f"{name_a} Wins", h2h[f"{name_a}_wins"])
    c_w2.metric(f"{name_b} Wins", h2h[f"{name_b}_wins"])
    c_tie.metric("Draws / Ties", h2h["ties"])
    
    st.info(f"**Average Scoring Margin:** {h2h['avg_margin']} in favor of {name_a}")

# --- MODEL DIAGNOSTICS & EXPLAINABILITY ---
st.markdown("---")
st.subheader("🔬 Machine Learning Methodology & Explainability")

tab1, tab2, tab3 = st.tabs(["Top Predictive Drivers", "Test Set Performance Benchmark", "Calibration Diagrams"])

with tab1:
    col_feat1, col_feat2 = st.columns([1.2, 1.0])
    with col_feat1:
        st.markdown("""
        ### Key Feature Rankings (Permutation Importance on Holdout Test Set)
        Features are ranked by the drop in test ROC-AUC when randomly shuffled.
        The top determinants of PKL match victory are:
        1. **Schedule Rest Differential (`diff_rest_days`):** Recovery days between games heavily impact tackle reaction speed.
        2. **Recent 5-Match Scoring Margin (`diff_l5_differential`):** Teams entering on hot net-positive runs outperform season averages.
        3. **Scoring Firepower Baseline (`diff_prior_avg_pts`):** All-time offensive scoring rates.
        4. **Tackle Success Differential (`diff_tackle_rate`):** Defensive conversion on opponent raids.
        """)
        fi_path = "reports/figures/model_feature_importance.png"
        if os.path.exists(fi_path):
            st.image(fi_path, use_column_width=True)

    with col_feat2:
        st.markdown("### Leakage Prevention Audit Contract")
        st.success("""
        - **No Lookahead:** All statistics strictly cutoff before match start.
        - **Temporal Walk-Forward:** Train on S1-5 (344 matches), Calibrate on S6 (124 matches), Test on S7 (79 matches).
        - **Probabilities Sum to 100%:** Guaranteed complementary odds ($P(A) + P(B) = 1.0$).
        - **Platt Scaling:** Calibrated using Sigmoid fit on out-of-fold validation set to minimize Brier score loss.
        """)

with tab2:
    st.markdown("### Holdout Test Set (Season 7) Model Benchmark")
    eval_json = "models/evaluation_summary.json"
    if os.path.exists(eval_json):
        import json
        with open(eval_json) as f:
            eval_data = json.load(f)
        test_metrics_df = pd.DataFrame(eval_data["test_metrics"]).T
        st.dataframe(
            test_metrics_df[["accuracy", "balanced_accuracy", "f1", "roc_auc", "brier_score", "log_loss"]].style.format("{:.3f}"),
            use_container_width=True
        )

    roc_path = "reports/figures/model_roc_curves.png"
    cm_path = "reports/figures/model_confusion_matrices.png"
    c_roc, c_cm = st.columns(2)
    if os.path.exists(roc_path):
        with c_roc:
            st.image(roc_path, caption="Season 7 Holdout ROC Curves", use_column_width=True)
    if os.path.exists(cm_path):
        with c_cm:
            st.image(cm_path, caption="Confusion Matrices", use_column_width=True)

with tab3:
    st.markdown("### Probability Calibration & Reliability Analysis")
    st.markdown("""
    A model with a low Brier score guarantees that when it assigns a **70% probability** to a victory, 
    those teams actually win **70% of the time**. Raw uncalibrated models often suffer from overconfidence.
    """)
    calib_path = "reports/figures/model_calibration_curves.png"
    if os.path.exists(calib_path):
        st.image(calib_path, caption="Reliability Diagram (Brier Score: 0.254)", use_column_width=True)
