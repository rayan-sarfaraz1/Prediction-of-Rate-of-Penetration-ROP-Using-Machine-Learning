"""
ROP·AI — Rate of Penetration prediction web app (BS FYP, P&G Engineering, BUITEMS)

Run:   streamlit run app/streamlit_app.py
Needs: models/all_models.joblib + results/*.csv  (created by code/rop_pipeline.py)
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RES, MOD, DATA, FIG = ROOT / "results", ROOT / "models", ROOT / "data", ROOT / "figures"

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
    }
    return out


try:
    BUNDLE, R = load_models(), load_results()
except FileNotFoundError:
    st.error("Model/result files not found. Run `python code/rop_pipeline.py` first.")
    st.stop()
MODELS, BEST = BUNDLE["models"], BUNDLE["best"]
CMP = R["cmp"]

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<h2 style='margin-bottom:0'>🛢️ ROP·AI</h2><div style='color:{INK2};font-size:.85rem'>"
                "Rate of Penetration Prediction</div>", unsafe_allow_html=True)
    st.write("")
    page = st.radio("Navigate", ["🏠 Overview", "🎯 Predict ROP", "⚙️ Optimizer", "📊 Data Explorer",
                                 "📈 Model Results", "📁 Batch Prediction", "ℹ️ About"], label_visibility="collapsed")
    st.divider()
    model_name = st.selectbox("Prediction model", list(MODELS), index=list(MODELS).index(BEST),
                              help="The best model (by test R²) is selected by default.")
    r2 = CMP.loc[model_name, "Test R2"]
    st.markdown(f"<div class='kpi'><div class='lab'>Selected model</div><div class='val' style='font-size:1.2rem'>"
                f"{model_name}</div><div class='sub'>Test R² {r2:.3f} · RMSE {CMP.loc[model_name, 'Test RMSE']:.2f} ft/hr</div></div>",
                unsafe_allow_html=True)
    st.write("")
    st.markdown("<div class='warn'>⚠️ Demo mode: models are trained on synthetic data. Re-run the pipeline with real "
                "field/Volve data before final use.</div>", unsafe_allow_html=True)
    st.caption("BS FYP · Dept. of Petroleum & Gas Engineering · BUITEMS")

MODEL = MODELS[model_name]


def predict(df):
    return np.clip(MODEL.predict(df[FEATURES]), 0, None)


# ============================================================================= pages
if page == "🏠 Overview":
    st.markdown("""<div class="hero"><span class="tag">BS Final Year Project · Petroleum & Gas Engineering</span>
    <h1>Prediction of Rate of Penetration using Machine Learning</h1>
    <p>Predict how fast the bit will drill — from eight everyday surface drilling parameters — using five
    machine-learning models trained, tuned and compared on drilling data.</p></div>""", unsafe_allow_html=True)
    c = st.columns(4)
    kpi(c[0], "Records used", f"{len(R['data']):,}", f"from {int(R['clean_log'].iloc[0, 1]):,} raw records")
    kpi(c[1], "Input features", "8", "WOB · RPM · T · Q · ρ · SPP · D · Depth")
    kpi(c[2], "Best model", BEST, "selected by test R²")
    kpi(c[3], "Best test R²", f"{CMP.loc[BEST, 'Test R2']:.3f}", f"RMSE {CMP.loc[BEST, 'Test RMSE']:.2f} ft/hr")
    st.write("")
    a, b = st.columns([1.15, 1])
    with a:
        st.markdown("#### How it works")
        steps = ["Collect drilling data (field records / Volve dataset)", "Clean: duplicates, missing values, unrealistic values, outliers",
                 "Explore: histograms, correlations, ROP vs each parameter", "Select features: Pearson r, mutual information, RF importance",
                 "Split 80 : 20 and standardize", "Train 5 models with Grid Search + 5-fold CV",
                 "Evaluate on unseen data: MAE, MSE, RMSE, R²", "Pick the best model → predict ROP"]
        st.markdown("".join(f"<div class='step'><div class='d'>{i + 1}</div><div>{s}</div></div>" for i, s in enumerate(steps)),
                    unsafe_allow_html=True)
    with b:
        st.markdown("#### Model leaderboard")
        lb = CMP.sort_values("Test R2", ascending=True)
        fig = go.Figure(go.Bar(x=lb["Test R2"], y=lb.index, orientation="h", text=[f"{v:.3f}" for v in lb["Test R2"]],
                               textposition="outside", marker_color=[ORANGE if n == BEST else BLUE for n in lb.index]))
        fig.update_xaxes(range=[0, 1.05], title="Test R² (higher is better)")
        st.plotly_chart(plot_style(fig, 330, False), use_container_width=True)

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
    preds_all = {n: float(np.clip(m.predict(x[FEATURES]), 0, None)[0]) for n, m in MODELS.items()}
    with right:
        st.markdown(f"<div class='big-rop'><div style='color:{INK2};font-weight:600;margin-bottom:8px'>Predicted ROP · {model_name}</div>"
                    f"<div class='n'>{rop:.1f}</div><div class='u'>ft/hr · {rop * 0.3048:.1f} m/hr</div></div>", unsafe_allow_html=True)
        gauge = go.Figure(go.Indicator(mode="gauge", value=rop, gauge=dict(
            axis=dict(range=[0, 150], tickcolor=INK2), bar=dict(color=ORANGE, thickness=0.3), bgcolor=CARD, borderwidth=0,
            steps=[dict(range=[0, 30], color="#1a2540"), dict(range=[30, 70], color="#1e2c4d"), dict(range=[70, 150], color="#22345c")])))
        st.plotly_chart(plot_style(gauge, 210, False), use_container_width=True)
        hours = 1000 / rop if rop > 0 else float("inf")
        st.markdown(f"<div class='card'>⏱️ Time to drill <b>1,000 ft</b> at this ROP: <b>{hours:.1f} hours</b> "
                    f"({hours / 24:.1f} days on bottom)</div>", unsafe_allow_html=True)
    st.markdown("#### What do all five models say?")
    comp = pd.Series(preds_all).sort_values()
    fig = go.Figure(go.Bar(x=comp.values, y=comp.index, orientation="h", text=[f"{v:.1f}" for v in comp.values],
                           textposition="outside", marker_color=[ORANGE if n == model_name else BLUE for n in comp.index]))
    fig.update_xaxes(title="Predicted ROP (ft/hr)", range=[0, comp.max() * 1.2])
    st.plotly_chart(plot_style(fig, 260, False), use_container_width=True)

    st.markdown("#### Sensitivity — how ROP responds to one parameter")
    p = st.selectbox("Vary parameter", [f for f in FEATURES if f != "Bit_Dia"], format_func=lambda f: META[f][0])
    lo, hi = META[p][2], META[p][3]
    grid = pd.DataFrame([vals] * 60); grid[p] = np.linspace(lo, hi, 60)
    yv = predict(grid)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid[p], y=yv, mode="lines", line=dict(color=BLUE, width=3), name="Predicted ROP"))
    fig.add_trace(go.Scatter(x=[vals[p]], y=[rop], mode="markers", marker=dict(color=ORANGE, size=14, line=dict(color="white", width=2)),
                             name="Current setting"))
    fig.update_xaxes(title=f"{META[p][0]} ({META[p][1]})"); fig.update_yaxes(title="ROP (ft/hr)")
    st.plotly_chart(plot_style(fig, 340), use_container_width=True)

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
    Z = predict(g).reshape(WW.shape)
    k = np.unravel_index(np.argmax(Z), Z.shape)
    a, b = st.columns([1.6, 1])
    with a:
        fig = go.Figure(go.Contour(x=W, y=N, z=Z, colorscale=[[0, "#13203b"], [0.5, BLUE], [1, ORANGE]],
                                   colorbar=dict(title="ROP<br>ft/hr"), contours=dict(showlabels=True, labelfont=dict(color="white"))))
        fig.add_trace(go.Scatter(x=[W[k[1]]], y=[N[k[0]]], mode="markers+text", text=["OPTIMUM"], textposition="bottom left", textfont=dict(color="white", size=13),
                                 marker=dict(symbol="star", size=20, color="white", line=dict(color=ORANGE, width=2)), showlegend=False))
        fig.update_xaxes(title="WOB (klbf)", range=[W[0], W[-1] + 1.5]); fig.update_yaxes(title="RPM (rev/min)", range=[N[0], N[-1] + 8])
        st.plotly_chart(plot_style(fig, 470, False), use_container_width=True)
    with b:
        st.markdown(f"<div class='big-rop'><div style='color:{INK2};font-weight:600;margin-bottom:8px'>Maximum predicted ROP</div>"
                    f"<div class='n'>{Z[k]:.1f}</div><div class='u'>ft/hr</div></div>", unsafe_allow_html=True)
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
        st.plotly_chart(plot_style(fig, 440), use_container_width=True)
        st.caption(f"Pearson r with ROP = {df[f].corr(df.ROP):.2f}")
    with t2:
        f = st.selectbox("Histogram of", FEATURES + ["ROP"], key="h")
        fig = go.Figure(go.Histogram(x=df[f], nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title=f); fig.update_yaxes(title="Count")
        st.plotly_chart(plot_style(fig, 400, False), use_container_width=True)
        st.dataframe(df[FEATURES + ["ROP"]].describe().T.round(2), use_container_width=True)
    with t3:
        cm = df[FEATURES + ["ROP"]].corr().round(2)
        fig = go.Figure(go.Heatmap(z=cm.values, x=cm.columns, y=cm.index, zmin=-1, zmax=1, text=cm.values, texttemplate="%{text}",
                                   colorscale=[[0, BLUE], [0.5, "#2a3348"], [1, ORANGE]]))
        st.plotly_chart(plot_style(fig, 520, False), use_container_width=True)
    with t4:
        s = df.sort_values("Depth")
        fig = go.Figure(go.Scatter(x=s.ROP, y=s.Depth, mode="lines", line=dict(color=BLUE, width=1)))
        fig.update_yaxes(autorange="reversed", title="Depth (ft)"); fig.update_xaxes(title="ROP (ft/hr)")
        st.plotly_chart(plot_style(fig, 620, False), use_container_width=True)
    with t5:
        st.dataframe(df.head(500), use_container_width=True, height=420)

elif page == "📈 Model Results":
    st.markdown("## 🤖 Model Results")
    show = CMP[["Test MAE", "Test MSE", "Test RMSE", "Test R2", "CV RMSE", "Train R2", "Training time (s)"]].rename(
        columns={"Test R2": "Test R²", "Train R2": "Train R²"})
    st.dataframe(show.style.format("{:.3f}").highlight_max("Test R²", color="#5a2a17").highlight_min("Test RMSE", color="#5a2a17"),
                 use_container_width=True)
    t1, t2, t3, t4 = st.tabs(["Actual vs Predicted", "Residuals", "Metric comparison", "Feature importance"])
    pr = R["pred"]
    with t1:
        m = st.selectbox("Model", list(MODELS), index=list(MODELS).index(BEST), key="avp")
        mx = max(pr.ROP_actual.max(), pr[f"pred_{m}"].max()) * 1.05
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=pr.ROP_actual, y=pr[f"pred_{m}"], mode="markers", name="Test samples",
                                   marker=dict(size=6, color=BLUE, opacity=0.6)))
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Perfect prediction (1:1)", line=dict(color=ORANGE, dash="dash")))
        fig.update_xaxes(title="Actual ROP (ft/hr)", range=[0, mx]); fig.update_yaxes(title="Predicted ROP (ft/hr)", range=[0, mx])
        st.plotly_chart(plot_style(fig, 520), use_container_width=True)
        st.caption(f"R² = {CMP.loc[m, 'Test R2']:.3f} · RMSE = {CMP.loc[m, 'Test RMSE']:.2f} ft/hr · MAE = {CMP.loc[m, 'Test MAE']:.2f} ft/hr")
    with t2:
        m = st.selectbox("Model", list(MODELS), index=list(MODELS).index(BEST), key="res")
        res = pr.ROP_actual - pr[f"pred_{m}"]
        a, b = st.columns(2)
        fig = go.Figure(go.Scattergl(x=pr[f"pred_{m}"], y=res, mode="markers", marker=dict(size=6, color=BLUE, opacity=0.6)))
        fig.add_hline(y=0, line=dict(color=ORANGE, dash="dash"))
        fig.update_xaxes(title="Predicted ROP (ft/hr)"); fig.update_yaxes(title="Residual (ft/hr)")
        a.plotly_chart(plot_style(fig, 400, False), use_container_width=True)
        fig = go.Figure(go.Histogram(x=res, nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title="Error = Actual − Predicted (ft/hr)")
        b.plotly_chart(plot_style(fig, 400, False), use_container_width=True)
    with t3:
        cols = st.columns(3)
        for col, (met, lab) in zip(cols, [("Test R2", "R² ↑"), ("Test RMSE", "RMSE ↓ (ft/hr)"), ("Test MAE", "MAE ↓ (ft/hr)")]):
            s = CMP[met].sort_values(ascending=met != "Test R2")
            fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", text=[f"{v:.3f}" if met == "Test R2" else f"{v:.2f}" for v in s],
                                   textposition="outside", marker_color=[ORANGE if n == BEST else BLUE for n in s.index]))
            fig.update_layout(title=lab); fig.update_xaxes(range=[0, s.max() * 1.3])
            col.plotly_chart(plot_style(fig, 330, False), use_container_width=True)
    with t4:
        m = st.radio("Model", ["Random Forest", "Decision Tree"], horizontal=True)
        s = R["imp"][m].sort_values()
        fig = go.Figure(go.Bar(x=s.values, y=[META[i][0] for i in s.index], orientation="h", marker_color=BLUE,
                               text=[f"{v:.2f}" for v in s.values], textposition="outside"))
        fig.update_xaxes(title="Importance", range=[0, s.max() * 1.25])
        st.plotly_chart(plot_style(fig, 400, False), use_container_width=True)

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
            st.plotly_chart(plot_style(fig, 520), use_container_width=True)
        st.dataframe(df, use_container_width=True, height=320)
        st.download_button("⬇️ Download predictions", df.to_csv(index=False), "rop_predictions.csv", "text/csv")

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
