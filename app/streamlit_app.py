"""
ROP·AI — Rate of Penetration prediction web app (BS FYP, P&G Engineering, BUITEMS)

Run:   streamlit run app/streamlit_app.py
Needs: models/all_models.joblib + results/*.csv  (created by code/rop_pipeline.py)
"""
import io
import json
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RES, MOD, DATA, FIG, DOCS = ROOT / "results", ROOT / "models", ROOT / "data", ROOT / "figures", ROOT / "docs"

FEATURES = ["WOB", "RPM", "Torque", "Q", "MW", "SPP", "Bit_Dia", "Depth"]
META = {  # label, unit, min, max, default, step
    "WOB": ("Weight on Bit", "klbf", 5.0, 45.0, 25.0, 0.5),
    "RPM": ("Rotary Speed", "rev/min", 40.0, 200.0, 120.0, 1.0),
    "Torque": ("Torque", "kft·lbf", 1.0, 30.0, 12.0, 0.5),
    "Q": ("Flow Rate", "gpm", 300.0, 1150.0, 700.0, 10.0),
    "MW": ("Mud Density ρ", "ppg", 8.8, 14.0, 11.0, 0.05),
    "SPP": ("Standpipe Pressure", "psi", 700.0, 5800.0, 3000.0, 50.0),
    "Bit_Dia": ("Bit Diameter", "in", 8.5, 17.5, 12.25, None),
    "Depth": ("Depth", "ft", 2000.0, 12000.0, 7000.0, 50.0),
}
BG, CARD, LINE, INK, INK2 = "#0b1220", "#121b2e", "#24304a", "#eef2f8", "#9aa7bd"
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#eb6834", "#1fbf88", "#f0b429"

st.set_page_config(page_title="ROP·AI — ROP Prediction", page_icon="🛢️", layout="wide")

# ----------------------------------------------------------------------------- style
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, #1a2a4a 0%, {BG} 55%); }}
section[data-testid="stSidebar"] {{ background: #0a1020; border-right: 1px solid {LINE}; }}
.block-container {{ padding-top: 3rem; max-width: 1250px; }}
h1, h2, h3, h4 {{ color: {INK}; letter-spacing: -0.02em; }}
.hero {{ padding: 28px 32px; border-radius: 20px; border: 1px solid {LINE};
        background: linear-gradient(135deg, rgba(57,135,229,.18), rgba(235,104,52,.14)); margin-bottom: 18px; }}
.hero h1 {{ font-size: 2.3rem; font-weight: 800; margin: 0 0 6px 0; }}
.hero p {{ color: {INK2}; font-size: 1.02rem; margin: 0; }}
.tag {{ display:inline-block; padding: 4px 11px; border-radius: 999px; font-size: .75rem; font-weight: 600;
       background: rgba(235,104,52,.16); color: #ffb08f; border: 1px solid rgba(235,104,52,.4); margin-bottom: 12px; }}
.kpi {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 16px; padding: 16px 18px; height: 100%; }}
.kpi .lab {{ color: {INK2}; font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }}
.kpi .val {{ color: {INK}; font-size: 1.75rem; font-weight: 800; margin-top: 4px; }}
.kpi .sub {{ color: {INK2}; font-size: .8rem; }}
.card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; }}
.big-rop {{ text-align:center; padding: 22px; border-radius: 20px; border: 1px solid rgba(235,104,52,.5);
           background: linear-gradient(160deg, rgba(235,104,52,.22), rgba(18,27,46,1)); }}
.big-rop .n {{ font-size: 3.4rem; font-weight: 800; color: #fff; line-height: 1; }}
.big-rop .u {{ color: #ffc3aa; font-weight: 600; }}
.step {{ display:flex; gap:12px; align-items:flex-start; margin: 8px 0; color: {INK}; }}
.step .d {{ min-width: 28px; height: 28px; border-radius: 50%; background: {BLUE}; color: #fff; font-weight: 700;
           display:flex; align-items:center; justify-content:center; font-size: .85rem; }}
.warn {{ padding: 10px 14px; border-radius: 12px; background: rgba(240,180,41,.1); border: 1px solid rgba(240,180,41,.45);
        color: #f6d58a; font-size: .85rem; }}
div[data-testid="stMetricValue"] {{ color: {INK}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 2px; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{ padding: 9px 14px; border-radius: 12px; width: 100% !important; box-sizing: border-box;
   border: 1px solid transparent; transition: all .15s ease; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: rgba(57,135,229,.12); }}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
   background: linear-gradient(90deg, rgba(235,104,52,.28), rgba(235,104,52,.06)); border-color: rgba(235,104,52,.5); }}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none !important; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label p {{ font-size: .95rem; font-weight: 500; }}
.chip {{ display:inline-block; padding: 3px 10px; margin: 3px 4px 0 0; border-radius: 999px; font-size: .78rem;
        background: rgba(240,180,41,.12); border: 1px solid rgba(240,180,41,.5); color: #f6d58a; }}
.ok {{ padding: 10px 14px; border-radius: 12px; background: rgba(31,191,136,.1); border: 1px solid rgba(31,191,136,.45);
      color: #9be7c8; font-size: .88rem; }}
.foot {{ color: {INK2}; font-size: .78rem; text-align: center; margin-top: 36px; padding-top: 14px; border-top: 1px solid {LINE}; }}
.dl {{ display:flex; justify-content: space-between; align-items:center; }}
.stTabs [data-baseweb="tab"] {{ background: {CARD}; border-radius: 10px 10px 0 0; padding: 8px 16px; }}
</style>""", unsafe_allow_html=True)


def plot_style(fig, h=380, legend=True):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=CARD, height=h,
                      margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Inter", color=INK, size=12),
                      showlegend=legend, legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE)
    return fig


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="lab">{label}</div><div class="val">{value}</div>'
                 f'<div class="sub">{sub or "&nbsp;"}</div></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------- data
@st.cache_resource
def load_models():
    return joblib.load(MOD / "all_models.joblib")


@st.cache_data
def load_results():
    out = {
        "cmp": pd.read_csv(RES / "model_comparison.csv", index_col=0),
        "pred": pd.read_csv(RES / "test_predictions.csv"),
        "imp": pd.read_csv(RES / "feature_importance.csv", index_col=0),
        "fs": pd.read_csv(RES / "feature_selection.csv", index_col=0),
        "clean_log": pd.read_csv(RES / "cleaning_log.csv"),
        "summary": json.loads((RES / "summary.json").read_text()),
        "data": pd.read_csv(DATA / "cleaned_drilling_data.csv"),
        "card": json.loads((RES / "model_card.json").read_text()),
    }
    out["blind"] = pd.read_csv(RES / "blind_test.csv", index_col=0) if (RES / "blind_test.csv").exists() else None
    out["score"] = pd.read_csv(RES / "selection_score.csv", index_col=0).iloc[:, 0] if (RES / "selection_score.csv").exists() else None
    return out


try:
    BUNDLE, R = load_models(), load_results()
except FileNotFoundError:
    st.error("Model/result files not found. Run `python code/rop_pipeline.py` first.")
    st.stop()
MODELS, BEST = BUNDLE["models"], BUNDLE["best"]
CMP, BLIND, MCARD = R["cmp"], R["blind"], R["card"]
TRAIN_RANGE = MCARD["training_range"]

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<h2 style='margin-bottom:0'>🛢️ ROP·AI</h2><div style='color:{INK2};font-size:.85rem'>"
                "Rate of Penetration Prediction</div>", unsafe_allow_html=True)
    st.write("")
    page = st.radio("Navigate", ["🏠 Overview", "🎯 Predict ROP", "⚙️ Optimizer", "📊 Data Explorer",
                                 "📈 Model Results", "📁 Batch Prediction", "📄 Reports", "ℹ️ About"],
                    label_visibility="collapsed")
    st.divider()
    model_name = st.selectbox("Prediction model", list(MODELS), index=list(MODELS).index(BEST),
                              help="The final model (best combined accuracy on the test set and the blind well) is selected by default.")
    RU = st.segmented_control("ROP units", ["ft/hr", "m/hr"], default="ft/hr") or "ft/hr"
    r2 = CMP.loc[model_name, "Test R2"]
    st.markdown(f"<div class='kpi'><div class='lab'>Selected model</div><div class='val' style='font-size:1.2rem'>"
                f"{model_name}</div><div class='sub'>Test R² {r2:.3f} · RMSE {CMP.loc[model_name, 'Test RMSE']:.2f} ft/hr</div></div>",
                unsafe_allow_html=True)
    st.write("")
    st.markdown("<div class='warn'>⚠️ Demo mode: models are trained on synthetic data. Re-run the pipeline with real "
                "field/Volve data before final use.</div>", unsafe_allow_html=True)
    st.caption("BS FYP · Dept. of Petroleum & Gas Engineering · BUITEMS")

MODEL = MODELS[model_name]
UF = 1.0 if RU == "ft/hr" else 0.3048   # unit factor for displaying ROP


def predict(df):
    return np.clip(MODEL.predict(df[FEATURES]), 0, None)


# ============================================================================= pages
if page == "🏠 Overview":
    st.markdown("""<div class="hero"><span class="tag">BS Final Year Project · Petroleum & Gas Engineering</span>
    <h1>Prediction of Rate of Penetration using Machine Learning</h1>
    <p>Predict how fast the bit will drill — from eight everyday surface drilling parameters — using five
    machine-learning models trained, tuned and compared on drilling data.</p></div>""", unsafe_allow_html=True)
    c = st.columns(5)
    kpi(c[0], "Records used", f"{len(R['data']):,}", f"from {int(R['clean_log'].iloc[0, 1]):,} raw records")
    kpi(c[1], "Input features", "8", "WOB · RPM · T · Q · ρ · SPP · D · Depth")
    kpi(c[2], "Final model", BEST, "best on test set + blind well")
    kpi(c[3], "Test R²", f"{CMP.loc[BEST, 'Test R2']:.3f}", f"RMSE {CMP.loc[BEST, 'Test RMSE']:.2f} ft/hr")
    if BLIND is not None:
        kpi(c[4], "Blind-well R²", f"{BLIND.loc[BEST, 'R2']:.3f}", f"RMSE {BLIND.loc[BEST, 'RMSE']:.2f} ft/hr")
    else:
        kpi(c[4], "Train / test", f"{R['summary']['n_train']} / {R['summary']['n_test']}", "80 : 20 split")
    st.write("")
    a, b = st.columns([1.15, 1])
    with a:
        st.markdown("#### How it works")
        steps = ["Collect drilling data (field records / Volve dataset)", "Clean: duplicates, missing values, unrealistic values, outliers",
                 "Explore: histograms, correlations, ROP vs each parameter", "Select features: Pearson r, mutual information, RF importance",
                 "Split 80 : 20 and standardize", "Train 5 models with Grid Search + 5-fold CV",
                 "Evaluate on unseen test data + a blind well: MAE, MSE, RMSE, R²", "Select the final model → predict ROP"]
        st.markdown("".join(f"<div class='step'><div class='d'>{i + 1}</div><div>{s}</div></div>" for i, s in enumerate(steps)),
                    unsafe_allow_html=True)
    with b:
        st.markdown("#### Model leaderboard")
        order = (R["score"] if R["score"] is not None else CMP["Test R2"]).sort_values().index
        fig = go.Figure()
        fig.add_trace(go.Bar(x=CMP.loc[order, "Test R2"], y=order, orientation="h", name="Test set (20%)", marker_color=BLUE,
                             text=[f"{v:.3f}" for v in CMP.loc[order, "Test R2"]], textposition="outside"))
        if BLIND is not None:
            fig.add_trace(go.Bar(x=BLIND.loc[order, "R2"], y=order, orientation="h", name="Blind well", marker_color=ORANGE,
                                 text=[f"{v:.3f}" for v in BLIND.loc[order, "R2"]], textposition="outside"))
        fig.update_layout(barmode="group", bargap=0.25)
        fig.update_xaxes(range=[0, 1.1], title="R² (higher is better)")
        st.plotly_chart(plot_style(fig, 380), width="stretch")
        st.caption(f"Final model: **{BEST}** — highest mean R² over the test set and the blind well.")

elif page == "🎯 Predict ROP":
    st.markdown("## 🎯 Predict ROP")
    st.caption("Set the drilling parameters — prediction updates instantly.")
    left, right = st.columns([1.35, 1])
    vals = {}
    with left:
        g = st.columns(2)
        for i, f in enumerate(FEATURES):
            lab, unit, lo, hi, dv, step = META[f]
            with g[i % 2]:
                if f == "Bit_Dia":
                    vals[f] = st.select_slider(f"{lab} ({unit})", options=[8.5, 12.25, 17.5], value=12.25)
                else:
                    vals[f] = st.slider(f"{lab} ({unit})", lo, hi, dv, step)
    x = pd.DataFrame([vals])
    rop = float(predict(x)[0])
    outside = [f for f in FEATURES if not (TRAIN_RANGE[f][0] <= vals[f] <= TRAIN_RANGE[f][1])]
    if outside:
        st.markdown("<div class='warn'>⚠️ <b>Outside the training range</b> — the model is extrapolating, so treat this prediction "
                    "with caution:<br>" + "".join(f"<span class='chip'>{META[f][0]}: trained on {TRAIN_RANGE[f][0]:g}–{TRAIN_RANGE[f][1]:g} {META[f][1]}</span>"
                                                     for f in outside) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='ok'>✅ All inputs are inside the range of the training data — prediction is within the model's validated domain.</div>",
                    unsafe_allow_html=True)
    st.write("")
    preds_all = {n: float(np.clip(m.predict(x[FEATURES]), 0, None)[0]) for n, m in MODELS.items()}
    with right:
        st.markdown(f"<div class='big-rop'><div style='color:{INK2};font-weight:600;margin-bottom:8px'>Predicted ROP · {model_name}</div>"
                    f"<div class='n'>{rop * UF:.1f}</div><div class='u'>{RU} · ± {CMP.loc[model_name, 'Test RMSE'] * UF:.1f} (test RMSE)</div></div>", unsafe_allow_html=True)
        gauge = go.Figure(go.Indicator(mode="gauge", value=rop * UF, gauge=dict(
            axis=dict(range=[0, 150 * UF], tickcolor=INK2), bar=dict(color=ORANGE, thickness=0.3), bgcolor=CARD, borderwidth=0,
            steps=[dict(range=[0, 30 * UF], color="#1a2540"), dict(range=[30 * UF, 70 * UF], color="#1e2c4d"),
                   dict(range=[70 * UF, 150 * UF], color="#22345c")])))
        st.plotly_chart(plot_style(gauge, 210, False), width="stretch")
        hours = 1000 / rop if rop > 0 else float("inf")
        st.markdown(f"<div class='card'>⏱️ Time to drill <b>1,000 ft</b> at this ROP: <b>{hours:.1f} hours</b> "
                    f"({hours / 24:.1f} days on bottom)</div>", unsafe_allow_html=True)
    st.markdown("#### What do all five models say?")
    comp = pd.Series(preds_all).sort_values() * UF
    fig = go.Figure(go.Bar(x=comp.values, y=comp.index, orientation="h", text=[f"{v:.1f}" for v in comp.values],
                           textposition="outside", marker_color=[ORANGE if n == model_name else BLUE for n in comp.index]))
    fig.update_xaxes(title=f"Predicted ROP ({RU})", range=[0, comp.max() * 1.2])
    st.plotly_chart(plot_style(fig, 260, False), width="stretch")

    st.markdown("#### Sensitivity — how ROP responds to one parameter")
    p = st.selectbox("Vary parameter", [f for f in FEATURES if f != "Bit_Dia"], format_func=lambda f: META[f][0])
    lo, hi = META[p][2], META[p][3]
    grid = pd.DataFrame([vals] * 60); grid[p] = np.linspace(lo, hi, 60)
    yv = predict(grid)
    fig = go.Figure()
    lo_t, hi_t = TRAIN_RANGE[p]
    fig.add_vrect(x0=lo_t, x1=hi_t, fillcolor="rgba(31,191,136,.08)", line_width=0, annotation_text="training range",
                  annotation_position="top left", annotation_font_color="#9be7c8")
    fig.add_trace(go.Scatter(x=grid[p], y=yv * UF, mode="lines", line=dict(color=BLUE, width=3), name="Predicted ROP"))
    fig.add_trace(go.Scatter(x=[vals[p]], y=[rop * UF], mode="markers", marker=dict(color=ORANGE, size=14, line=dict(color="white", width=2)),
                             name="Current setting"))
    fig.update_xaxes(title=f"{META[p][0]} ({META[p][1]})"); fig.update_yaxes(title=f"ROP ({RU})")
    st.plotly_chart(plot_style(fig, 340), width="stretch")

elif page == "⚙️ Optimizer":
    st.markdown("## ⚙️ Drilling Parameter Optimizer")
    st.caption("Searches WOB × RPM combinations for the highest predicted ROP while other parameters are held at the values below.")
    c = st.columns(4)
    base = {}
    for i, f in enumerate(["Depth", "MW", "Q", "Bit_Dia"]):
        lab, unit, lo, hi, dv, step = META[f]
        with c[i]:
            base[f] = (st.select_slider(f"{lab} ({unit})", [8.5, 12.25, 17.5], 12.25) if f == "Bit_Dia"
                       else st.slider(f"{lab} ({unit})", lo, hi, dv, step))
    c2 = st.columns(4)
    wob_max = c2[0].slider("Max allowable WOB (klbf)", 10.0, 45.0, 35.0, 0.5)
    rpm_max = c2[1].slider("Max allowable RPM", 60.0, 200.0, 170.0, 5.0)
    torque_per_wob = c2[2].slider("Torque / WOB ratio", 0.2, 0.9, 0.5, 0.05, help="Torque is estimated from WOB with this ratio")
    spp = c2[3].slider("SPP (psi)", 700.0, 5800.0, 3000.0, 50.0)
    W = np.linspace(5, wob_max, 40); N = np.linspace(40, rpm_max, 40)
    WW, NN = np.meshgrid(W, N)
    g = pd.DataFrame({"WOB": WW.ravel(), "RPM": NN.ravel(), "Torque": WW.ravel() * torque_per_wob, "SPP": spp, **base})
    Z = predict(g).reshape(WW.shape) * UF
    k = np.unravel_index(np.argmax(Z), Z.shape)
    a, b = st.columns([1.6, 1])
    with a:
        fig = go.Figure(go.Contour(x=W, y=N, z=Z, colorscale=[[0, "#13203b"], [0.5, BLUE], [1, ORANGE]],
                                   colorbar=dict(title=f"ROP<br>{RU}"), contours=dict(showlabels=True, labelfont=dict(color="white"))))
        fig.add_trace(go.Scatter(x=[W[k[1]]], y=[N[k[0]]], mode="markers+text", text=["OPTIMUM"], textposition="bottom left", textfont=dict(color="white", size=13),
                                 marker=dict(symbol="star", size=20, color="white", line=dict(color=ORANGE, width=2)), showlegend=False))
        fig.update_xaxes(title="WOB (klbf)", range=[W[0], W[-1] + 1.5]); fig.update_yaxes(title="RPM (rev/min)", range=[N[0], N[-1] + 8])
        st.plotly_chart(plot_style(fig, 470, False), width="stretch")
    with b:
        st.markdown(f"<div class='big-rop'><div style='color:{INK2};font-weight:600;margin-bottom:8px'>Maximum predicted ROP</div>"
                    f"<div class='n'>{Z[k]:.1f}</div><div class='u'>{RU}</div></div>", unsafe_allow_html=True)
        st.write("")
        kp = st.columns(2)
        kpi(kp[0], "Optimum WOB", f"{W[k[1]]:.1f}", "klbf")
        kpi(kp[1], "Optimum RPM", f"{N[k[0]]:.0f}", "rev/min")
        st.write("")
        st.markdown(f"<div class='card' style='font-size:.9rem;color:{INK2}'>The model suggests drilling at the starred point. "
                    "Always check against bit manufacturer limits, vibration, hole cleaning and torque limits before applying in the field. "
                    "This is a data-driven recommendation, not a guarantee.</div>", unsafe_allow_html=True)

elif page == "📊 Data Explorer":
    st.markdown("## 📊 Data Explorer")
    up = st.file_uploader("Use your own CSV (optional) — columns: " + ", ".join(FEATURES + ["ROP"]), type="csv")
    df = pd.read_csv(up) if up else R["data"]
    if up is not None and not set(FEATURES + ["ROP"]).issubset(df.columns):
        st.error("CSV must contain columns: " + ", ".join(FEATURES + ["ROP"])); st.stop()
    c = st.columns(4)
    kpi(c[0], "Rows", f"{len(df):,}"); kpi(c[1], "Mean ROP", f"{df.ROP.mean():.1f}", "ft/hr")
    kpi(c[2], "Depth range", f"{df.Depth.min():,.0f}–{df.Depth.max():,.0f}", "ft"); kpi(c[3], "Max ROP", f"{df.ROP.max():.1f}", "ft/hr")
    st.write("")
    t1, t2, t3, t4, t5 = st.tabs(["Scatter vs ROP", "Distributions", "Correlation", "Depth log", "Table"])
    with t1:
        f = st.selectbox("Parameter", [x for x in FEATURES], format_func=lambda v: f"{META[v][0]} ({META[v][1]})")
        fig = go.Figure()
        for bd, col in zip([17.5, 12.25, 8.5], [BLUE, AQUA, ORANGE]):
            s = df[df.Bit_Dia == bd]
            fig.add_trace(go.Scattergl(x=s[f], y=s.ROP, mode="markers", name=f'{bd}" hole', marker=dict(size=5, color=col, opacity=0.55)))
        fig.update_xaxes(title=f"{META[f][0]} ({META[f][1]})"); fig.update_yaxes(title="ROP (ft/hr)")
        st.plotly_chart(plot_style(fig, 440), width="stretch")
        st.caption(f"Pearson r with ROP = {df[f].corr(df.ROP):.2f}")
    with t2:
        f = st.selectbox("Histogram of", FEATURES + ["ROP"], key="h")
        fig = go.Figure(go.Histogram(x=df[f], nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title=f); fig.update_yaxes(title="Count")
        st.plotly_chart(plot_style(fig, 400, False), width="stretch")
        st.dataframe(df[FEATURES + ["ROP"]].describe().T.round(2), width="stretch")
    with t3:
        cm = df[FEATURES + ["ROP"]].corr().round(2)
        fig = go.Figure(go.Heatmap(z=cm.values, x=cm.columns, y=cm.index, zmin=-1, zmax=1, text=cm.values, texttemplate="%{text}",
                                   colorscale=[[0, BLUE], [0.5, "#2a3348"], [1, ORANGE]]))
        st.plotly_chart(plot_style(fig, 520, False), width="stretch")
    with t4:
        s = df.sort_values("Depth")
        fig = go.Figure(go.Scatter(x=s.ROP, y=s.Depth, mode="lines", line=dict(color=BLUE, width=1)))
        fig.update_yaxes(autorange="reversed", title="Depth (ft)"); fig.update_xaxes(title="ROP (ft/hr)")
        st.plotly_chart(plot_style(fig, 620, False), width="stretch")
    with t5:
        st.dataframe(df.head(500), width="stretch", height=420)

elif page == "📈 Model Results":
    st.markdown("## 📈 Model Results")
    show = CMP[["Test MAE", "Test MSE", "Test RMSE", "Test R2", "CV RMSE", "Train R2", "Training time (s)"]].rename(
        columns={"Test R2": "Test R²", "Train R2": "Train R²"})
    st.dataframe(show.style.format("{:.3f}").highlight_max("Test R²", color="#5a2a17").highlight_min("Test RMSE", color="#5a2a17"),
                 width="stretch")
    t1, t2, t3, t4, t5 = st.tabs(["Actual vs Predicted", "Residuals", "Metric comparison", "Feature importance",
                                  "Blind well & final selection"])
    pr = R["pred"]
    with t1:
        m = st.selectbox("Model", list(MODELS), index=list(MODELS).index(BEST), key="avp")
        mx = max(pr.ROP_actual.max(), pr[f"pred_{m}"].max()) * 1.05
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=pr.ROP_actual, y=pr[f"pred_{m}"], mode="markers", name="Test samples",
                                   marker=dict(size=6, color=BLUE, opacity=0.6)))
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Perfect prediction (1:1)", line=dict(color=ORANGE, dash="dash")))
        fig.update_xaxes(title="Actual ROP (ft/hr)", range=[0, mx]); fig.update_yaxes(title="Predicted ROP (ft/hr)", range=[0, mx])
        st.plotly_chart(plot_style(fig, 520), width="stretch")
        st.caption(f"R² = {CMP.loc[m, 'Test R2']:.3f} · RMSE = {CMP.loc[m, 'Test RMSE']:.2f} ft/hr · MAE = {CMP.loc[m, 'Test MAE']:.2f} ft/hr")
    with t2:
        m = st.selectbox("Model", list(MODELS), index=list(MODELS).index(BEST), key="res")
        res = pr.ROP_actual - pr[f"pred_{m}"]
        a, b = st.columns(2)
        fig = go.Figure(go.Scattergl(x=pr[f"pred_{m}"], y=res, mode="markers", marker=dict(size=6, color=BLUE, opacity=0.6)))
        fig.add_hline(y=0, line=dict(color=ORANGE, dash="dash"))
        fig.update_xaxes(title="Predicted ROP (ft/hr)"); fig.update_yaxes(title="Residual (ft/hr)")
        a.plotly_chart(plot_style(fig, 400, False), width="stretch")
        fig = go.Figure(go.Histogram(x=res, nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title="Error = Actual − Predicted (ft/hr)")
        b.plotly_chart(plot_style(fig, 400, False), width="stretch")
    with t3:
        cols = st.columns(3)
        for col, (met, lab) in zip(cols, [("Test R2", "R² ↑"), ("Test RMSE", "RMSE ↓ (ft/hr)"), ("Test MAE", "MAE ↓ (ft/hr)")]):
            s = CMP[met].sort_values(ascending=met != "Test R2")
            fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", text=[f"{v:.3f}" if met == "Test R2" else f"{v:.2f}" for v in s],
                                   textposition="outside", marker_color=[ORANGE if n == BEST else BLUE for n in s.index]))
            fig.update_layout(title=lab); fig.update_xaxes(range=[0, s.max() * 1.3])
            col.plotly_chart(plot_style(fig, 330, False), width="stretch")
    with t4:
        m = st.radio("Model", ["Random Forest", "Decision Tree"], horizontal=True)
        s = R["imp"][m].sort_values()
        fig = go.Figure(go.Bar(x=s.values, y=[META[i][0] for i in s.index], orientation="h", marker_color=BLUE,
                               text=[f"{v:.2f}" for v in s.values], textposition="outside"))
        fig.update_xaxes(title="Importance", range=[0, s.max() * 1.25])
        st.plotly_chart(plot_style(fig, 400, False), width="stretch")
    with t5:
        if BLIND is None:
            st.info("No blind-well file was supplied to the pipeline.")
        else:
            st.markdown("A random 80 : 20 split can be optimistic because neighbouring depths end up in both sets. The models were "
                        "therefore also tested on a **completely separate well** that was never used for training or tuning.")
            sel = pd.DataFrame({"Test R²": CMP["Test R2"], "Blind-well R²": BLIND["R2"], "Blind-well RMSE": BLIND["RMSE"],
                                "Selection score": R["score"]}).sort_values("Selection score", ascending=False)
            st.dataframe(sel.style.format("{:.3f}").highlight_max("Selection score", color="#5a2a17"), width="stretch")
            order = sel.index[::-1]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sel.loc[order, "Test R²"], y=order, orientation="h", name="Test set", marker_color=BLUE))
            fig.add_trace(go.Bar(x=sel.loc[order, "Blind-well R²"], y=order, orientation="h", name="Blind well", marker_color=ORANGE))
            fig.update_layout(barmode="group"); fig.update_xaxes(range=[0, 1], title="R²")
            st.plotly_chart(plot_style(fig, 360), width="stretch")
            st.markdown(f"<div class='ok'>✅ Final model: <b>{BEST}</b> — selection score = mean of test R² and blind-well R². "
                        "Tree models score well on the random test set but drop on the new well, showing that they memorise "
                        "field-specific depth patterns; the ANN generalises best.</div>", unsafe_allow_html=True)

elif page == "📁 Batch Prediction":
    st.markdown("## 📁 Batch Prediction")
    st.caption("Upload a CSV with the 8 input columns. If it also contains ROP, accuracy metrics are calculated.")
    tmpl = pd.DataFrame([{f: META[f][4] for f in FEATURES}])
    st.download_button("⬇️ Download CSV template", tmpl.to_csv(index=False), "rop_input_template.csv", "text/csv")
    up = st.file_uploader("Upload drilling data CSV", type="csv", key="batch")
    use_demo = st.checkbox("…or use the demo test set", value=up is None)
    df = pd.read_csv(up) if up is not None else (R["pred"][FEATURES + ["ROP_actual"]].rename(columns={"ROP_actual": "ROP"}) if use_demo else None)
    if df is not None:
        miss = [f for f in FEATURES if f not in df.columns]
        if miss:
            st.error(f"Missing columns: {miss}"); st.stop()
        df = df.copy(); df["ROP_predicted"] = predict(df).round(2)
        if "ROP" in df.columns:
            e = df.ROP - df.ROP_predicted
            c = st.columns(4)
            kpi(c[0], "Samples", f"{len(df):,}"); kpi(c[1], "MAE", f"{e.abs().mean():.2f}", "ft/hr")
            kpi(c[2], "RMSE", f"{np.sqrt((e ** 2).mean()):.2f}", "ft/hr")
            kpi(c[3], "R²", f"{1 - (e ** 2).sum() / ((df.ROP - df.ROP.mean()) ** 2).sum():.3f}")
            st.write("")
            s = df.sort_values("Depth")
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=s.ROP, y=s.Depth, mode="markers", name="Actual", marker=dict(color=INK2, size=5, opacity=0.7)))
            fig.add_trace(go.Scattergl(x=s.ROP_predicted, y=s.Depth, mode="markers", name="Predicted", marker=dict(color=ORANGE, size=5, opacity=0.8)))
            fig.update_yaxes(autorange="reversed", title="Depth (ft)"); fig.update_xaxes(title="ROP (ft/hr)")
            st.plotly_chart(plot_style(fig, 520), width="stretch")
        st.dataframe(df, width="stretch", height=320)
        st.download_button("⬇️ Download predictions", df.to_csv(index=False), "rop_predictions.csv", "text/csv")

elif page == "📄 Reports":
    st.markdown("## 📄 Reports & Downloads")
    st.caption("Every deliverable of the project in one place — ready for submission, presentation and viva.")
    docs = [("ROP_FYP_Complete_Thesis_Draft", "Complete thesis (Chapters 1–5)", "📘"),
            ("ROP_FYP_Proposal_Ch1-3", "Proposal / synopsis (Chapters 1–3)", "📗"),
            ("ROP_AI_App_User_Guide", "ROP·AI user guide", "📙"),
            ("ROP_FYP_Verification_Report", "Requirements & verification report", "📕")]
    cols = st.columns(2)
    for i, (stem, title, icon) in enumerate(docs):
        with cols[i % 2]:
            st.markdown(f"<div class='card'><h4 style='margin:0 0 6px 0'>{icon} {title}</h4>"
                        f"<div style='color:{INK2};font-size:.85rem'>{stem}</div></div>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            for col, ext, mime in [(b1, "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                                   (b2, "pdf", "application/pdf")]:
                f = DOCS / f"{stem}.{ext}"
                if f.exists():
                    col.download_button(f"⬇️ {ext.upper()}", f.read_bytes(), f.name, mime, key=f"{stem}{ext}", width="stretch")
                else:
                    col.button(f"{ext.upper()} not built", disabled=True, key=f"{stem}{ext}", width="stretch")
    st.markdown("#### Data, results and model")

    def zip_of(folder, pattern):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.glob(pattern)):
                z.write(f, f.name)
        return buf.getvalue()
    c = st.columns(4)
    c[0].download_button("🖼️ All figures (ZIP)", zip_of(FIG, "*.png"), "rop_figures.zip", "application/zip", width="stretch")
    c[1].download_button("📊 All result tables (ZIP)", zip_of(RES, "*.*"), "rop_results.zip", "application/zip", width="stretch")
    c[2].download_button("🧠 Final model (.joblib)", (MOD / "final_rop_model.joblib").read_bytes(), "final_rop_model.joblib",
                         width="stretch")
    c[3].download_button("🧾 Model card (.json)", json.dumps(MCARD, indent=2), "model_card.json", "application/json",
                         width="stretch")
    st.markdown("#### Final model card")
    a, b = st.columns([1, 1])
    with a:
        hp = " · ".join(f"{k} = {v}" for k, v in MCARD["hyperparameters"].items()) or "—"
        arch = MCARD.get("architecture")
        st.markdown(f"<div class='card'><b>Model:</b> {MCARD['final_model']} ({MCARD['algorithm']})<br>"
                    f"<b>Pipeline:</b> {' → '.join(MCARD['pipeline'])}<br><b>Hyperparameters:</b> {hp}<br>"
                    + (f"<b>Architecture:</b> {arch['input_neurons']} → {' → '.join(map(str, arch['hidden_layers']))} → 1 "
                       f"({arch['activation']}, {arch['solver']}, {arch['iterations_trained']} iterations)<br>" if arch else "")
                    + f"<b>Inputs:</b> {', '.join(MCARD['input_parameters'].values())}<br><b>Output:</b> {MCARD['target']}</div>",
                    unsafe_allow_html=True)
    with b:
        tm, bm = MCARD["test_metrics"], MCARD.get("blind_well_metrics") or {}
        mt = pd.DataFrame({"Test set": tm, "Blind well": {k: bm.get(k) for k in tm}}).T
        st.dataframe(mt.style.format("{:.3f}", na_rep="—"), width="stretch")
        rng = pd.DataFrame(MCARD["training_range"], index=["min", "max"]).T
        rng.index = [META[i][0] for i in rng.index]
        st.dataframe(rng, width="stretch", height=318)
    st.markdown("#### Figure gallery")
    figs = sorted(FIG.glob("*.png"))
    pick = st.select_slider("Browse figures", options=[f.stem for f in figs], value=figs[0].stem if figs else None)
    if pick:
        st.image(str(FIG / f"{pick}.png"), width="stretch")

else:
    st.markdown("## ℹ️ About the project")
    a, b = st.columns([1.3, 1])
    with a:
        st.markdown("""<div class="card"><h4>Aim</h4>Develop, evaluate and compare machine-learning models that predict the
        Rate of Penetration (ROP) from commonly available drilling parameters, and select the most suitable model for unseen data.</div>
        <div class="card"><h4>Models</h4>Linear Regression (baseline) · Decision Tree · Random Forest · Support Vector Regression (RBF) ·
        Artificial Neural Network (MLP) — tuned with Grid Search + 5-fold cross-validation.</div>
        <div class="card"><h4>Team</h4>Supervisor: [Supervisor Name]<br>Group: [Student 1] · [Student 2] · [Student 3] · [Student 4]<br>
        Department of Petroleum & Gas Engineering, BUITEMS, Quetta</div>""", unsafe_allow_html=True)
    with b:
        st.markdown("""<div class="card"><h4>Tech stack</h4>Python · pandas · NumPy · scikit-learn · Plotly · Matplotlib · Streamlit · joblib</div>
        <div class="card"><h4>Inputs</h4>WOB (klbf) · RPM · Torque (kft·lbf) · Flow rate Q (gpm) · Mud density ρ (ppg) ·
        SPP (psi) · Bit diameter D (in) · Depth (ft)</div><div class="card"><h4>Output</h4>ROP (ft/hr)</div>""", unsafe_allow_html=True)
        if (FIG / "diagram_methodology_flowchart.png").exists():
            with st.expander("Methodology flowchart"):
                st.image(str(FIG / "diagram_methodology_flowchart.png"))

st.markdown("<div class='foot'>ROP·AI · Prediction of Rate of Penetration using Machine Learning · BS FYP, Department of "
            "Petroleum & Gas Engineering, BUITEMS · Python · scikit-learn · Streamlit</div>", unsafe_allow_html=True)
