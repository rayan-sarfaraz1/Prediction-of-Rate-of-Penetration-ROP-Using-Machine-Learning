"""
ROP·AI — Rate of Penetration prediction studio (BS FYP, Petroleum & Gas Engineering, BUITEMS)

Guided workflow:  1 Data  →  2 Clean  →  3 Explore  →  4 Train  →  5 Results  →  Predict · Optimize · Batch

Run:   streamlit run app/streamlit_app.py
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import data_io as dio  # noqa: E402
import rop_pipeline as rp  # noqa: E402

RES, MOD, DATA, FIG = ROOT / "results", ROOT / "models", ROOT / "data", ROOT / "figures"
FEATURES, TARGET = rp.FEATURES, rp.TARGET
MODEL_NAMES = ["Linear Regression", "Decision Tree", "Random Forest", "SVR (RBF)", "ANN (MLP)"]
META = {  # label, unit, slider min, max, default, step
    "WOB": ("Weight on Bit", "klbf", 5.0, 45.0, 25.0, 0.5), "RPM": ("Rotary Speed", "rev/min", 40.0, 200.0, 120.0, 1.0),
    "Torque": ("Torque", "kft·lbf", 1.0, 30.0, 12.0, 0.5), "Q": ("Flow Rate", "gpm", 300.0, 1150.0, 700.0, 10.0),
    "MW": ("Mud Density ρ", "ppg", 8.8, 14.0, 11.0, 0.05), "SPP": ("Standpipe Pressure", "psi", 700.0, 5800.0, 3000.0, 50.0),
    "Bit_Dia": ("Bit Diameter", "in", 8.5, 17.5, 12.25, None), "Depth": ("Depth", "ft", 2000.0, 12000.0, 7000.0, 50.0),
}
BG, PANEL, LINE, INK, INK2, MUTED = "#070b14", "#0f1626", "#1e2a42", "#eef2f8", "#a3b0c6", "#6b7a93"
BLUE, ORANGE, AQUA, AMBER, VIOLET = "#4c8dff", "#ff7a45", "#22c998", "#f5b93d", "#9d8cff"

st.set_page_config(page_title="ROP·AI — ROP Prediction Studio", page_icon="🛢️", layout="wide",
                   initial_sidebar_state="expanded")

# ============================================================================ premium styling
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
html, body, .stApp, .stMarkdown, button, input, textarea, select {{ font-family: 'Inter', system-ui, sans-serif; }}
h1, h2, h3, h4, .ttl {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important; letter-spacing: -0.02em; color: {INK}; }}
.stApp {{ background:
   radial-gradient(900px 500px at 85% -10%, rgba(255,122,69,.13), transparent 60%),
   radial-gradient(900px 600px at 0% 0%, rgba(76,141,255,.16), transparent 55%), {BG}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stStatusWidget"], .stDeployButton, [data-testid="stToolbar"] {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px; }}
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #0b1120 0%, #080d18 100%); border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}

/* ---------- sidebar brand + stepper ---------- */
.brand {{ display:flex; align-items:center; gap:12px; padding: 6px 2px 18px 2px; }}
.brand .logo {{ width:42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:22px;
   background: linear-gradient(135deg, {ORANGE}, #ffb36b); box-shadow: 0 8px 24px rgba(255,122,69,.35); }}
.brand .n {{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.25rem; color:{INK}; line-height:1.1; }}
.brand .s {{ color:{MUTED}; font-size:.75rem; letter-spacing:.04em; }}
.navsec {{ color:{MUTED}; font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; margin: 22px 0 8px 4px; }}
section[data-testid="stSidebar"] .stButton button {{ width:100%; justify-content:flex-start; text-align:left; border-radius:12px;
   padding: .55rem .85rem; border:1px solid transparent; background: transparent; color:{INK2}; font-weight:500; transition: all .15s ease; }}
section[data-testid="stSidebar"] .stButton button:hover {{ background: rgba(76,141,255,.10); color:{INK}; border-color: rgba(76,141,255,.25); }}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {{ background: linear-gradient(90deg, rgba(255,122,69,.22), rgba(255,122,69,.04));
   color:#fff; border-color: rgba(255,122,69,.55); box-shadow: inset 3px 0 0 {ORANGE}; }}
section[data-testid="stSidebar"] .stButton button:disabled {{ opacity:.38; }}
section[data-testid="stSidebar"] .stButton button > div {{ justify-content:flex-start !important; width:100%; }}
section[data-testid="stSidebar"] .stButton button p {{ text-align:left; font-size:.92rem; }}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .3rem; }}
section[data-testid="stSidebar"] .stButton {{ margin: 0; }}
.progress-wrap {{ margin: 4px 2px 10px 2px; }}
.progress-bar {{ height:6px; border-radius:99px; background:{LINE}; overflow:hidden; }}
.progress-bar > div {{ height:100%; border-radius:99px; background: linear-gradient(90deg, {BLUE}, {ORANGE}); }}
.progress-lbl {{ display:flex; justify-content:space-between; color:{MUTED}; font-size:.72rem; margin-top:6px; }}

/* ---------- page header ---------- */
.eyebrow {{ display:inline-flex; gap:8px; align-items:center; padding: 5px 12px; border-radius:99px; font-size:.72rem; font-weight:700;
   letter-spacing:.08em; text-transform:uppercase; color:#ffc2a6; background: rgba(255,122,69,.12); border: 1px solid rgba(255,122,69,.35); }}
.ph h1 {{ font-size: 2.35rem; font-weight: 800; margin: 12px 0 6px 0; line-height:1.15;
   background: linear-gradient(90deg, #ffffff 0%, #c9d6ee 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.ph p {{ color:{INK2}; font-size:1.02rem; margin:0 0 22px 0; max-width: 820px; }}

/* ---------- cards ---------- */
.glass {{ background: linear-gradient(180deg, rgba(20,29,50,.85), rgba(13,20,36,.85)); border:1px solid {LINE}; border-radius:18px;
   padding: 20px 22px; box-shadow: 0 10px 30px rgba(0,0,0,.25); margin-bottom: 14px; }}
.glass h4 {{ margin: 0 0 6px 0; font-size: 1.05rem; }}
.glass p, .glass li {{ color:{INK2}; font-size:.92rem; }}
.kpi {{ background: linear-gradient(180deg, rgba(20,29,50,.9), rgba(13,20,36,.9)); border:1px solid {LINE}; border-radius:16px; padding:16px 18px; height:100%; position:relative; overflow:hidden; }}
.kpi:before {{ content:""; position:absolute; inset:0 auto 0 0; width:3px; background: linear-gradient(180deg, {BLUE}, {ORANGE}); }}
.kpi .lab {{ color:{MUTED}; font-size:.72rem; text-transform:uppercase; letter-spacing:.09em; font-weight:700; }}
.kpi .val {{ color:{INK}; font-family:'Plus Jakarta Sans'; font-size:1.7rem; font-weight:800; margin-top:6px; line-height:1.1; }}
.kpi .sub {{ color:{INK2}; font-size:.78rem; margin-top:4px; }}
.hero-rop {{ text-align:center; padding: 26px 18px; border-radius:22px; border:1px solid rgba(255,122,69,.45);
   background: radial-gradient(400px 200px at 50% 0%, rgba(255,122,69,.30), transparent 70%), linear-gradient(180deg, #161f35, #0d1424);
   box-shadow: 0 20px 50px rgba(255,122,69,.12); }}
.hero-rop .t {{ color:{INK2}; font-weight:600; font-size:.85rem; letter-spacing:.04em; }}
.hero-rop .n {{ font-family:'Plus Jakarta Sans'; font-size:3.6rem; font-weight:800; color:#fff; line-height:1.05; margin-top:6px; }}
.hero-rop .u {{ color:#ffc2a6; font-weight:600; }}
.badge {{ display:inline-block; padding:3px 10px; border-radius:99px; font-size:.75rem; font-weight:600; margin: 2px 4px 2px 0; }}
.b-ok {{ background: rgba(34,201,152,.12); color:#8ff0cf; border:1px solid rgba(34,201,152,.4); }}
.b-warn {{ background: rgba(245,185,61,.12); color:#ffd98a; border:1px solid rgba(245,185,61,.45); }}
.b-info {{ background: rgba(76,141,255,.12); color:#a9c8ff; border:1px solid rgba(76,141,255,.4); }}
.note-ok {{ padding:12px 16px; border-radius:14px; background: rgba(34,201,152,.08); border:1px solid rgba(34,201,152,.35); color:#9cefd3; font-size:.9rem; }}
.note-warn {{ padding:12px 16px; border-radius:14px; background: rgba(245,185,61,.08); border:1px solid rgba(245,185,61,.4); color:#ffdc93; font-size:.9rem; }}
.steps {{ display:grid; grid-template-columns: repeat(6, 1fr); gap:10px; margin: 6px 0 8px 0; }}
.steps div {{ background: rgba(15,22,38,.8); border:1px solid {LINE}; border-radius:14px; padding:12px; font-size:.8rem; color:{INK2}; }}
.steps b {{ display:block; color:{INK}; font-family:'Plus Jakarta Sans'; font-size:.95rem; margin-bottom:2px; }}
.foot {{ color:{MUTED}; font-size:.76rem; text-align:center; margin-top:40px; padding-top:16px; border-top:1px solid {LINE}; }}

/* ---------- widgets ---------- */
.stButton button[kind="primary"], .stDownloadButton button {{ background: linear-gradient(90deg, {ORANGE}, #ff9a5c); border:0; color:#fff; font-weight:600;
   border-radius:12px; box-shadow: 0 8px 22px rgba(255,122,69,.28); }}
.stButton button[kind="primary"]:hover {{ filter: brightness(1.08); }}
.stButton button[kind="secondary"] {{ border-radius:12px; }}
[data-testid="stFileUploaderDropzone"] {{ background: rgba(76,141,255,.05); border: 1.5px dashed rgba(76,141,255,.45); border-radius:16px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; padding: 10px 16px; color:{INK2}; }}
.stTabs [aria-selected="true"] {{ color:#fff; background: rgba(255,122,69,.10); }}
[data-testid="stDataFrame"] {{ border-radius: 14px; overflow:hidden; border:1px solid {LINE}; }}
[data-testid="stExpander"] {{ border:1px solid {LINE}; border-radius:14px; background: rgba(15,22,38,.6); }}
</style>""", unsafe_allow_html=True)


# ============================================================================ helpers
def style(fig, h=380, legend=True):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,22,38,.75)", height=h,
                      margin=dict(l=10, r=10, t=36, b=10), font=dict(family="Inter", color=INK, size=12), showlegend=legend,
                      legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="#141d32", bordercolor=LINE, font_family="Inter"))
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE)
    return fig


def chart(fig, h=380, legend=True):
    st.plotly_chart(style(fig, h, legend), width="stretch", config={"displaylogo": False})


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="lab">{label}</div><div class="val">{value}</div>'
                 f'<div class="sub">{sub or "&nbsp;"}</div></div>', unsafe_allow_html=True)


def header(step, title, text):
    st.markdown(f'<div class="ph"><span class="eyebrow">{step}</span><h1>{title}</h1><p>{text}</p></div>', unsafe_allow_html=True)


def go_to(page):
    st.session_state.page = page


def nav_button(label, page, enabled=True):
    st.button(label, key=f"nav_{page}", on_click=go_to, args=(page,), disabled=not enabled,
              type="primary" if st.session_state.page == page else "secondary", width="stretch")


def gate(ok, msg, target, target_label):
    if not ok:
        st.markdown(f"<div class='glass'><h4>🔒 Not available yet</h4><p>{msg}</p></div>", unsafe_allow_html=True)
        st.button(target_label, type="primary", on_click=go_to, args=(target,))
        st.stop()


def S():
    return st.session_state


def model_ready():
    return S().get("models") is not None


def train_range():
    X = S()["split"][0]
    return {f: (float(X[f].min()), float(X[f].max())) for f in FEATURES}


# ============================================================================ state
st.session_state.setdefault("page", "data")
st.session_state.setdefault("unit", "ft/hr")
for k in ["flash", "raw", "raw_name", "std", "blind_std", "clean", "clean_log", "quality", "bounds", "split", "fs", "rfe",
          "models", "table", "preds", "params", "blind", "best", "score", "source", "raw_rop", "train_cfg"]:
    st.session_state.setdefault(k, None)

stages = [("data", S().std is not None), ("clean", S().clean is not None), ("explore", S().clean is not None),
          ("train", model_ready()), ("results", model_ready())]
done = sum(1 for _, ok in stages if ok)

# ============================================================================ sidebar
with st.sidebar:
    st.markdown("<div class='brand'><div class='logo'>🛢️</div><div><div class='n'>ROP·AI</div>"
                "<div class='s'>PREDICTION STUDIO</div></div></div>", unsafe_allow_html=True)
    pct = int(100 * done / len(stages))
    st.markdown(f"<div class='progress-wrap'><div class='progress-bar'><div style='width:{pct}%'></div></div>"
                f"<div class='progress-lbl'><span>Workflow progress</span><span>{done}/{len(stages)}</span></div></div>",
                unsafe_allow_html=True)
    tick = lambda ok: "✓ " if ok else ""
    st.markdown("<div class='navsec'>Workflow</div>", unsafe_allow_html=True)
    nav_button(f"{tick(S().std is not None)}1 · Load dataset", "data")
    nav_button(f"{tick(S().clean is not None)}2 · Pre-process & clean", "clean", S().std is not None)
    nav_button("3 · Explore data", "explore", S().clean is not None)
    nav_button(f"{tick(model_ready())}4 · Train models", "train", S().clean is not None)
    nav_button("5 · Results & selection", "results", model_ready())
    st.markdown("<div class='navsec'>Use the model</div>", unsafe_allow_html=True)
    nav_button("🎯  Predict ROP", "predict", model_ready())
    nav_button("⚙️  Optimizer", "optimizer", model_ready())
    nav_button("📁  Batch prediction", "batch", model_ready())
    st.markdown("<div class='navsec'>Project</div>", unsafe_allow_html=True)
    nav_button("ℹ️  About", "about")
    st.write("")
    if model_ready():
        b = S().best
        st.markdown(f"<div class='glass' style='padding:14px 16px'><div class='lab' style='color:{MUTED};font-size:.7rem;"
                    f"font-weight:700;letter-spacing:.1em'>ACTIVE MODEL</div><div style='font-family:Plus Jakarta Sans;font-weight:800;"
                    f"font-size:1.1rem;margin-top:4px'>{b}</div><div style='color:{INK2};font-size:.78rem'>Test R² "
                    f"{S().table.loc[b, 'Test R2']:.3f} · {S().source}</div></div>", unsafe_allow_html=True)
        st.segmented_control("ROP units", ["ft/hr", "m/hr"], key="unit")
    if S().source and "demo" in S().source:
        st.markdown("<div class='note-warn' style='font-size:.78rem'>Demo data in use — upload real field data for final results.</div>",
                    unsafe_allow_html=True)

if S().get("flash"):                      # message queued before a rerun
    st.toast(S().flash[0], icon=S().flash[1]); S().flash = None

UF = 1.0 if (S().unit or "ft/hr") == "ft/hr" else 0.3048
RU = S().unit or "ft/hr"


# ============================================================================ mapping widget
def mapping_ui(df, prefix, require_rop=True):
    """Column + unit mapping. Returns (standardized dataframe or None, mapping, units, constants)."""
    guess = dio.guess_mapping(df.columns)
    none_opt = "— not in file —"
    cols = [none_opt] + list(df.columns)
    mapping, units, consts = {}, {}, {}
    st.markdown("<div class='glass'><h4>🧭 Map your columns</h4><p>Columns and units were detected automatically from the "
                "header names — please check them. All values are converted to oilfield units for the models.</p></div>",
                unsafe_allow_html=True)
    grid = st.columns(3)
    for i, f in enumerate(dio.FIELDS):
        with grid[i % 3]:
            with st.container(border=True):
                g = guess[f]
                c = st.selectbox(dio.LABEL[f], cols, index=cols.index(g) if g in cols else 0, key=f"{prefix}_col_{f}")
                mapping[f] = None if c == none_opt else c
                ulist = list(dio.UNITS[f])
                gu = dio.guess_unit(f, mapping[f])
                units[f] = st.selectbox("Unit", ulist, index=ulist.index(gu), key=f"{prefix}_unit_{f}", label_visibility="collapsed")
                if mapping[f] is None:
                    if f == "Bit_Dia":
                        consts[f] = st.number_input("Constant bit diameter", value=12.25, step=0.25, key=f"{prefix}_const_{f}")
                    elif f == "ROP" and not require_rop:
                        st.caption("Optional — only needed to compute accuracy.")
                    else:
                        st.markdown("<span class='badge b-warn'>required</span>", unsafe_allow_html=True)
    missing = [dio.LABEL[f] for f in dio.FIELDS if mapping[f] is None and f not in consts and not (f == "ROP" and not require_rop)]
    if missing:
        st.markdown(f"<div class='note-warn'>Please select a column for: <b>{', '.join(missing)}</b></div>", unsafe_allow_html=True)
        return None, mapping, units, consts
    if not require_rop and mapping["ROP"] is None:
        consts["ROP"] = np.nan
    try:
        std = dio.apply_mapping(df, mapping, units, consts)
    except ValueError as e:
        st.error(str(e)); return None, mapping, units, consts
    return std, mapping, units, consts


def reset_after_data():
    for k in ["clean", "clean_log", "quality", "bounds", "split", "fs", "rfe", "models", "table", "preds", "params",
              "blind", "best", "score", "raw_rop", "train_cfg"]:
        S()[k] = None


def load_demo():
    reset_after_data()
    S().raw = pd.read_csv(DATA / "synthetic_drilling_data_raw.csv"); S().raw_name = "synthetic_drilling_data_raw.csv (demo)"
    S().std = S().raw[dio.FIELDS].copy()
    b = DATA / "synthetic_blind_well.csv"
    S().blind_std = pd.read_csv(b)[dio.FIELDS] if b.exists() else None
    S().source = "demo dataset"
    S().page = "clean"


def load_saved_project():
    bundle = joblib.load(MOD / "all_models.joblib")
    reset_after_data()
    clean = pd.read_csv(DATA / "cleaned_drilling_data.csv")
    S().raw = clean; S().std = clean; S().clean = clean; S().raw_name = "saved project (cleaned_drilling_data.csv)"
    S().clean_log = pd.read_csv(RES / "cleaning_log.csv").values.tolist()
    S().split = rp.split(clean)
    S().models = bundle["models"]; S().best = bundle["best"]
    S().table = pd.read_csv(RES / "model_comparison.csv", index_col=0)
    tp = pd.read_csv(RES / "test_predictions.csv")
    S().preds = {n: tp[f"pred_{n}"].values for n in S().models}
    S().params = json.loads((RES / "summary.json").read_text()).get("best_params", {})
    if (RES / "blind_test.csv").exists():
        bt = pd.read_csv(RES / "blind_test.csv", index_col=0)
        S().blind = (bt, None, None, None)
        S().score = pd.read_csv(RES / "selection_score.csv", index_col=0).iloc[:, 0]
    S().source = "saved project model"
    S().page = "results"


# ============================================================================ PAGE 1 — DATA
def page_data():
    header("Step 1 of 5 · Data", "Start with your drilling data",
           "Upload a drilling dataset (CSV or Excel). ROP·AI will recognise the columns, convert units, clean the data, "
           "train five machine-learning models and select the best one — step by step.")
    st.markdown("<div class='steps'>" + "".join(f"<div><b>{t}</b>{d}</div>" for t, d in [
        ("1 · Load", "CSV / Excel + column mapping"), ("2 · Clean", "duplicates, limits, outliers"), ("3 · Explore", "EDA & feature selection"),
        ("4 · Train", "5 models, grid search + CV"), ("5 · Select", "test set + blind well"), ("Use", "predict · optimize · batch")]) + "</div>",
        unsafe_allow_html=True)
    st.write("")
    a, b = st.columns([1.6, 1], gap="large")
    with a:
        st.markdown("#### 📤 Upload your dataset")
        up = st.file_uploader("Training data — one or more wells (CSV / XLSX)", type=["csv", "xlsx", "xls"], key="up_main")
        upb = st.file_uploader("Blind well — optional, a separate well for the final test", type=["csv", "xlsx", "xls"], key="up_blind")
    with b:
        st.markdown("#### ⚡ Quick start")
        st.markdown("<div class='glass'><h4>🧪 Demo dataset</h4><p>3,040 synthetic drilling records with realistic problems "
                    "(duplicates, gaps, sensor errors, spikes) + an 800-row blind well.</p></div>", unsafe_allow_html=True)
        st.button("Use demo dataset", key="btn_demo", on_click=load_demo, width="stretch")
        if (MOD / "all_models.joblib").exists() and (DATA / "cleaned_drilling_data.csv").exists():
            st.markdown("<div class='glass'><h4>💾 Saved project model</h4><p>Open the last saved, already-trained models and "
                        "go straight to the results and predictions.</p></div>", unsafe_allow_html=True)
            st.button("Open saved project", key="btn_saved", on_click=load_saved_project, width="stretch")

    if up is not None:
        try:
            raw = dio.read_any(up)
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not read the file: {e}"); return
        st.markdown(f"#### 📄 {up.name}")
        c = st.columns(4)
        kpi(c[0], "Rows", f"{len(raw):,}"); kpi(c[1], "Columns", f"{raw.shape[1]}")
        kpi(c[2], "Missing cells", f"{100 * raw.isna().mean().mean():.1f}%"); kpi(c[3], "Numeric columns", f"{raw.select_dtypes('number').shape[1]}")
        with st.expander("Preview first rows", expanded=False):
            st.dataframe(raw.head(20), width="stretch")
        std, mapping, units, consts = mapping_ui(raw, "main")
        if std is not None:
            st.markdown("<div class='note-ok'>✅ All required fields are mapped. Preview of the standardized data (oilfield units):</div>",
                        unsafe_allow_html=True)
            st.dataframe(std.head(8).round(2), width="stretch")
            blind_std = None
            if upb is not None:
                try:
                    braw = dio.read_any(upb)
                    blind_std = dio.apply_mapping(braw, mapping, units, consts)
                    st.markdown(f"<span class='badge b-ok'>Blind well ready · {len(blind_std):,} rows (same column mapping)</span>",
                                unsafe_allow_html=True)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Blind-well file does not have the same columns as the training file: {e}")
            if st.button("Confirm data & continue to cleaning  →", type="primary", key="btn_confirm"):
                reset_after_data()
                S().raw, S().raw_name, S().std, S().blind_std = raw, up.name, std, blind_std
                S().source = f"uploaded · {up.name}"
                S().page = "clean"; st.rerun()
    elif S().std is not None:
        st.markdown(f"<div class='note-ok'>✅ Loaded: <b>{S().raw_name}</b> · {len(S().std):,} rows"
                    f"{' · blind well ' + format(len(S().blind_std), ',') + ' rows' if S().blind_std is not None else ''}</div>",
                    unsafe_allow_html=True)
        st.button("Continue to cleaning  →", type="primary", on_click=go_to, args=("clean",), key="btn_cont1")

    with st.expander("📋 Required data format and supported units"):
        st.markdown("Your file needs one column for each of these fields (names can be different — you map them above). "
                    "If the bit diameter is not recorded, a constant value can be entered.")
        st.dataframe(pd.DataFrame({"Field": [dio.LABEL[f] for f in dio.FIELDS],
                                   "Model unit": [list(dio.UNITS[f])[0] for f in dio.FIELDS],
                                   "Other accepted units": [", ".join(list(dio.UNITS[f])[1:]) or "—" for f in dio.FIELDS]}),
                     hide_index=True, width="stretch")


# ============================================================================ PAGE 2 — CLEAN
def run_cleaning(k):
    with st.status("Pre-processing and cleaning the data…", expanded=True) as status:
        st.write("🔎 Removing duplicate records"); time.sleep(0.15)
        st.write("🧩 Counting missing values"); time.sleep(0.15)
        st.write("📏 Checking physical limits (unrealistic values → missing)"); time.sleep(0.15)
        clean, log, quality, bounds = rp.clean(S().std, k=k)
        st.write(f"📉 Removing ROP outliers with the {k:g}×IQR rule"); time.sleep(0.15)
        st.write("✂️ Splitting 80 % training / 20 % testing (seed 42)")
        S().split = rp.split(clean)
        status.update(label=f"Cleaning complete — {len(clean):,} of {log[0][1]:,} records kept", state="complete")
    S().clean, S().clean_log, S().quality, S().bounds = clean, log, quality, bounds
    S().raw_rop = S().std["ROP"].dropna()
    for kk in ["fs", "rfe", "models", "table", "preds", "params", "blind", "best", "score"]:
        S()[kk] = None
    S().flash = (f"Data cleaned — {len(clean):,} records ready", "✅")
    st.rerun()                             # refresh the sidebar so the next steps unlock


def page_clean():
    header("Step 2 of 5 · Pre-processing", "Clean and prepare the data",
           "Duplicates are removed, physically impossible sensor values are flagged, missing ROP rows are dropped and ROP spikes "
           "are removed. Missing inputs are later filled with the training-set median inside each model (no data leakage).")
    gate(S().std is not None, "Load a dataset first.", "data", "← Go to Step 1 · Load dataset")
    a, b = st.columns([1.3, 1], gap="large")
    with a:
        st.markdown("<div class='glass'><h4>⚙️ Cleaning settings</h4><p>The IQR factor controls how strict the ROP outlier filter is "
                    "(3 = conservative, keeps genuine drilling breaks).</p></div>", unsafe_allow_html=True)
        k = st.slider("ROP outlier factor k (× IQR)", 1.5, 5.0, 3.0, 0.5)
        if st.button("🧹  Run pre-processing & cleaning", type="primary", key="btn_clean"):
            run_cleaning(k)
    with b:
        with st.expander("Physical limits used to flag unrealistic values", expanded=False):
            units = {f: META[f][1] for f in META} | {"ROP": "ft/hr"}
            st.dataframe(pd.DataFrame([(f, lo, hi, units.get(f, "")) for f, (lo, hi) in rp.LIMITS.items()],
                                      columns=["Field", "Min", "Max", "Unit"]), hide_index=True, width="stretch")
    if S().clean is None:
        return
    log = S().clean_log
    c = st.columns(4)
    kpi(c[0], "Raw records", f"{log[0][1]:,}"); kpi(c[1], "Clean records", f"{log[-1][1]:,}", f"{100 * log[-1][1] / log[0][1]:.1f}% kept")
    kpi(c[2], "Training / test", f"{len(S().split[0]):,} / {len(S().split[1]):,}", "80 : 20 split")
    if S().bounds:
        lo, hi, nout = S().bounds
        kpi(c[3], "ROP outliers removed", f"{nout}", f"above {hi:.1f} ft/hr")
    st.write("")
    t1, t2, t3, t4 = st.tabs(["Cleaning funnel", "Data quality", "ROP before / after", "Cleaned data"])
    with t1:
        fig = go.Figure(go.Funnel(y=[s for s, _ in log], x=[n for _, n in log], textinfo="value+percent initial",
                                  marker=dict(color=[BLUE, "#5d7cf0", VIOLET, ORANGE][:len(log)])))
        chart(fig, 340, False)
    with t2:
        if S().quality is not None:
            q = S().quality
            fig = go.Figure()
            fig.add_trace(go.Bar(x=q.index, y=q["Missing values"], name="Missing", marker_color=BLUE))
            fig.add_trace(go.Bar(x=q.index, y=q["Unrealistic values"], name="Unrealistic (set to missing)", marker_color=ORANGE))
            fig.update_layout(barmode="group"); fig.update_yaxes(title="Count")
            chart(fig, 360)
    with t3:
        fig = go.Figure()
        if S().raw_rop is not None:
            fig.add_trace(go.Box(y=S().raw_rop, name="Raw ROP", marker_color=MUTED, boxpoints="outliers"))
        fig.add_trace(go.Box(y=S().clean["ROP"], name="Cleaned ROP", marker_color=ORANGE, boxpoints="outliers"))
        fig.update_yaxes(title="ROP (ft/hr)")
        chart(fig, 380, False)
    with t4:
        st.dataframe(S().clean.round(2), width="stretch", height=360)
        st.download_button("⬇️  Download cleaned data (CSV)", S().clean.to_csv(index=False), "cleaned_drilling_data.csv", "text/csv")
    st.button("Continue to data exploration  →", type="primary", on_click=go_to, args=("explore",), key="btn_cont2")


# ============================================================================ PAGE 3 — EXPLORE
def page_explore():
    header("Step 3 of 5 · Exploratory data analysis", "Understand the data",
           "How does each drilling parameter relate to ROP? Distributions, correlations, the ROP log and feature relevance "
           "(computed on the training set only).")
    gate(S().clean is not None, "Clean the data first.", "clean", "← Go to Step 2 · Clean")
    df = S().clean
    c = st.columns(4)
    kpi(c[0], "Records", f"{len(df):,}"); kpi(c[1], "Mean ROP", f"{df.ROP.mean():.1f}", "ft/hr")
    kpi(c[2], "Depth range", f"{df.Depth.min():,.0f}–{df.Depth.max():,.0f}", "ft"); kpi(c[3], "Max ROP", f"{df.ROP.max():.1f}", "ft/hr")
    st.write("")
    t1, t2, t3, t4, t5 = st.tabs(["ROP vs parameters", "Distributions", "Correlation", "Depth log", "Feature selection"])
    with t1:
        f = st.selectbox("Parameter", FEATURES, format_func=lambda v: f"{META[v][0]} ({META[v][1]})")
        fig = go.Figure()
        sizes = sorted(df.Bit_Dia.dropna().unique())
        palette = [BLUE, AQUA, ORANGE, VIOLET, AMBER]
        for i, bd in enumerate(sizes[:5]):
            s = df[df.Bit_Dia == bd]
            fig.add_trace(go.Scattergl(x=s[f], y=s.ROP, mode="markers", name=f'{bd:g}" hole', marker=dict(size=5, color=palette[i], opacity=.55)))
        fig.update_xaxes(title=f"{META[f][0]} ({META[f][1]})"); fig.update_yaxes(title="ROP (ft/hr)")
        chart(fig, 460)
        st.caption(f"Pearson r with ROP = {df[f].corr(df.ROP):.2f}")
    with t2:
        f = st.selectbox("Histogram of", FEATURES + [TARGET], key="hist")
        fig = go.Figure(go.Histogram(x=df[f], nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title=f); fig.update_yaxes(title="Count")
        chart(fig, 380, False)
        st.dataframe(df[FEATURES + [TARGET]].describe().T.round(2), width="stretch")
    with t3:
        cm = df[FEATURES + [TARGET]].corr().round(2)
        fig = go.Figure(go.Heatmap(z=cm.values, x=cm.columns, y=cm.index, zmin=-1, zmax=1, text=cm.values, texttemplate="%{text}",
                                   colorscale=[[0, BLUE], [0.5, "#222c44"], [1, ORANGE]]))
        chart(fig, 520, False)
    with t4:
        s = df.sort_values("Depth")
        fig = go.Figure(go.Scatter(x=s.ROP, y=s.Depth, mode="lines", line=dict(color=BLUE, width=1)))
        fig.update_yaxes(autorange="reversed", title="Depth (ft)"); fig.update_xaxes(title="ROP (ft/hr)")
        chart(fig, 620, False)
    with t5:
        if S().fs is None:
            with st.spinner("Computing Pearson r, mutual information and random-forest importance on the training set…"):
                X_tr, _, y_tr, _ = S().split
                S().fs = rp.feature_selection(X_tr, y_tr, plot=False, rfe=False)[0]
        fs = S().fs
        cols = st.columns(3)
        for col, (m, lab) in zip(cols, [("|r|", "|Pearson r|"), ("Mutual information", "Mutual information"), ("RF importance", "Random-forest importance")]):
            s = fs[m].sort_values()
            fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color=BLUE, text=[f"{v:.2f}" for v in s.values], textposition="outside"))
            fig.update_layout(title=lab); fig.update_xaxes(range=[0, s.max() * 1.3])
            with col:
                chart(fig, 330, False)
        if st.button("Run recursive feature elimination (RFECV, ≈30 s)", key="btn_rfe"):
            with st.spinner("Running RFECV with 5-fold cross-validation…"):
                X_tr, _, y_tr, _ = S().split
                _, curve, nbest = rp.feature_selection(X_tr, y_tr, plot=False, rfe=True)
                S().rfe = (curve, nbest)
        if S().rfe is not None:
            curve, nbest = S().rfe
            fig = go.Figure(go.Scatter(x=curve.n_features, y=curve.cv_rmse, mode="lines+markers", line=dict(color=BLUE, width=3),
                                       error_y=dict(type="data", array=curve.cv_rmse_std, color=MUTED)))
            fig.add_trace(go.Scatter(x=[nbest], y=[curve.cv_rmse[nbest - 1]], mode="markers", marker=dict(size=16, color=ORANGE), name="optimum"))
            fig.update_xaxes(title="Number of features"); fig.update_yaxes(title="CV RMSE (ft/hr)")
            chart(fig, 330, False)
            st.caption(f"Optimum: {nbest} features. If the gain is smaller than the fold-to-fold spread, all 8 features are kept.")
    st.button("Continue to model training  →", type="primary", on_click=go_to, args=("train",), key="btn_cont3")


# ============================================================================ PAGE 4 — TRAIN
def page_train():
    header("Step 4 of 5 · Machine learning", "Train and tune the models",
           "Each selected model is tuned with grid search and 5-fold cross-validation on the training set, then evaluated on "
           "the unseen 20 % test set — and on the blind well if one was uploaded.")
    gate(S().clean is not None, "Clean the data first.", "clean", "← Go to Step 2 · Clean")
    a, b = st.columns([1.3, 1], gap="large")
    with a:
        chosen = st.multiselect("Models", MODEL_NAMES, default=MODEL_NAMES)
        mode = st.radio("Hyperparameter search", ["⚡ Fast (≈20–40 s)", "🎯 Full thesis grid (≈2 min)"], horizontal=True)
    with b:
        X_tr, X_te, _, _ = S().split
        blind_txt = f"{len(S().blind_std):,} rows" if S().blind_std is not None else "not supplied"
        st.markdown(f"<div class='glass'><h4>Training set-up</h4><p>Training: <b>{len(X_tr):,}</b> rows · Test: <b>{len(X_te):,}</b> rows<br>"
                    f"Blind well: <b>{blind_txt}</b><br>Pipeline: median imputer → standard scaler → model<br>"
                    f"Metrics: MAE · MSE · RMSE · R²</p></div>", unsafe_allow_html=True)
    if st.button("🚀  Train models", type="primary", key="btn_train", disabled=not chosen):
        fast = mode.startswith("⚡")
        X_tr, X_te, y_tr, y_te = S().split
        models = rp.build_models(fast)
        rows, preds, params, fitted = [], {}, {}, {}
        bar = st.progress(0.0, text="Starting…")
        with st.status("Training models…", expanded=True) as status:
            for i, n in enumerate(chosen):
                bar.progress(i / len(chosen), text=f"Tuning {n} ({i + 1}/{len(chosen)})…")
                est, grid = models[n]
                t0 = time.perf_counter()
                row, p_te, prm, best = rp.train_one(n, est, grid, X_tr, y_tr, X_te, y_te)
                rows.append(row); preds[n] = p_te; params[n] = prm; fitted[n] = best
                st.write(f"✅ **{n}** — test R² {row['Test R2']:.3f}, RMSE {row['Test RMSE']:.2f} ft/hr ({time.perf_counter() - t0:.1f} s)")
            table = pd.DataFrame(rows).set_index("Model")
            blind = None
            if S().blind_std is not None:
                st.write("🧪 Testing all models on the blind well")
                blind = rp.blind_test(S().blind_std, fitted)
            best, score = rp.select_final_model(table, None if blind is None else blind[0])
            status.update(label=f"Training complete — final model: {best}", state="complete")
        bar.progress(1.0, text="Done")
        S().models, S().table, S().preds, S().params, S().blind, S().best, S().score = fitted, table, preds, params, blind, best, score
        S().train_cfg = {"mode": "fast" if fast else "full"}
        if "saved" in (S().source or ""):
            S().source = "retrained in app"
        S().flash = (f"Training complete — final model: {best}", "🏆")
        st.rerun()
    if model_ready():
        st.markdown(f"<div class='note-ok'>🏆 Final model: <b>{S().best}</b> — see the full comparison on the Results page.</div>",
                    unsafe_allow_html=True)
        st.write("")
        st.button("View results & model selection  →", type="primary", on_click=go_to, args=("results",), key="btn_cont4")


# ============================================================================ PAGE 5 — RESULTS
def save_project():
    X_tr, X_te, y_tr, y_te = S().split
    fitted, table, best = S().models, S().table, S().best
    for d in (MOD, RES, DATA):
        d.mkdir(exist_ok=True)
    joblib.dump({"model": fitted[best], "features": FEATURES, "target": TARGET}, MOD / "final_rop_model.joblib")
    joblib.dump({"models": fitted, "best": best, "features": FEATURES, "target": TARGET}, MOD / "all_models.joblib", compress=3)
    table.to_csv(RES / "model_comparison.csv")
    tp = X_te.copy(); tp["ROP_actual"] = y_te.values
    for n, p in S().preds.items():
        tp[f"pred_{n}"] = p
    tp.to_csv(RES / "test_predictions.csv", index=False)
    S().clean.to_csv(DATA / "cleaned_drilling_data.csv", index=False)
    pd.DataFrame(S().clean_log, columns=["Step", "Records"]).to_csv(RES / "cleaning_log.csv", index=False)
    if S().blind is not None:
        S().blind[0].to_csv(RES / "blind_test.csv")
    S().score.rename("Selection score").to_csv(RES / "selection_score.csv")
    rp.model_card(best, fitted, table, S().params, X_tr, None, S().blind)
    summ = json.loads((RES / "summary.json").read_text()) if (RES / "summary.json").exists() else {}
    summ.update({"best_model": best, "best_params": S().params, "n_train": len(X_tr), "n_test": len(X_te)})
    (RES / "summary.json").write_text(json.dumps(summ, indent=2, default=str))
    st.toast("Project model saved — open it next time with ‘Open saved project’", icon="💾")


def page_results():
    header("Step 5 of 5 · Results", "Model comparison & final selection",
           "All models compared on the unseen test set and on the blind well. The final model has the highest mean of test R² "
           "and blind-well R² (or test R² if no blind well was supplied).")
    gate(model_ready(), "Train the models first.", "train", "← Go to Step 4 · Train")
    T, best = S().table, S().best
    blind = S().blind[0] if S().blind is not None else None
    c = st.columns(5)
    kpi(c[0], "Final model", best, "selected automatically")
    kpi(c[1], "Test R²", f"{T.loc[best, 'Test R2']:.3f}"); kpi(c[2], "Test RMSE", f"{T.loc[best, 'Test RMSE']:.2f}", "ft/hr")
    kpi(c[3], "Test MAE", f"{T.loc[best, 'Test MAE']:.2f}", "ft/hr")
    kpi(c[4], "Blind-well R²", f"{blind.loc[best, 'R2']:.3f}" if blind is not None else "—", "separate well" if blind is not None else "no blind well")
    st.write("")
    tabs = st.tabs(["Leaderboard", "Actual vs predicted", "Residuals & errors", "Feature importance", "Hyperparameters"])
    with tabs[0]:
        show = T[["Test MAE", "Test MSE", "Test RMSE", "Test R2", "CV RMSE", "Train R2", "Training time (s)"]].rename(
            columns={"Test R2": "Test R²", "Train R2": "Train R²"})
        if blind is not None:
            show["Blind R²"] = blind["R2"]; show["Blind RMSE"] = blind["RMSE"]
        if S().score is not None:
            show["Selection score"] = S().score
        key = "Selection score" if "Selection score" in show else "Test R²"
        show = show.sort_values(key, ascending=False)
        st.dataframe(show.style.format("{:.3f}").highlight_max(key, color="#5a2a17"), width="stretch")
        order = show.index[::-1]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=T.loc[order, "Test R2"], y=order, orientation="h", name="Test set", marker_color=BLUE,
                             text=[f"{v:.3f}" for v in T.loc[order, "Test R2"]], textposition="outside"))
        if blind is not None:
            fig.add_trace(go.Bar(x=blind.loc[order, "R2"], y=order, orientation="h", name="Blind well", marker_color=ORANGE,
                                 text=[f"{v:.3f}" for v in blind.loc[order, "R2"]], textposition="outside"))
        fig.update_layout(barmode="group"); fig.update_xaxes(range=[0, 1.1], title="R²")
        chart(fig, 400)
        if blind is not None:
            st.markdown("<div class='note-ok'>A random split can be optimistic; the blind well shows how each model generalises to a new well. "
                        "Models that drop strongly on the blind well have memorised field-specific patterns.</div>", unsafe_allow_html=True)
    y_te = S().split[3]
    with tabs[1]:
        m = st.selectbox("Model", list(S().models), index=list(S().models).index(best), key="avp")
        p = S().preds[m]; mx = max(y_te.max(), p.max()) * 1.05
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=y_te, y=p, mode="markers", name="Test samples", marker=dict(size=6, color=BLUE, opacity=.6)))
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="1 : 1", line=dict(color=ORANGE, dash="dash")))
        fig.update_xaxes(title="Actual ROP (ft/hr)", range=[0, mx]); fig.update_yaxes(title="Predicted ROP (ft/hr)", range=[0, mx])
        chart(fig, 500)
    with tabs[2]:
        m = st.selectbox("Model", list(S().models), index=list(S().models).index(best), key="res")
        r = y_te.values - S().preds[m]
        a, b = st.columns(2)
        fig = go.Figure(go.Scattergl(x=S().preds[m], y=r, mode="markers", marker=dict(size=6, color=BLUE, opacity=.6)))
        fig.add_hline(y=0, line=dict(color=ORANGE, dash="dash"))
        fig.update_xaxes(title="Predicted ROP (ft/hr)"); fig.update_yaxes(title="Residual (ft/hr)")
        with a:
            chart(fig, 380, False)
        fig = go.Figure(go.Histogram(x=r, nbinsx=40, marker_color=BLUE, marker_line=dict(color=BG, width=1)))
        fig.update_xaxes(title="Error = Actual − Predicted (ft/hr)")
        with b:
            chart(fig, 380, False)
    with tabs[3]:
        trees = [n for n in ["Random Forest", "Decision Tree"] if n in S().models]
        if trees:
            m = st.radio("Model", trees, horizontal=True)
            imp = pd.Series(S().models[m].named_steps["model"].feature_importances_, index=FEATURES).sort_values()
            fig = go.Figure(go.Bar(x=imp.values, y=[META[i][0] for i in imp.index], orientation="h", marker_color=BLUE,
                                   text=[f"{v:.2f}" for v in imp.values], textposition="outside"))
            fig.update_xaxes(title="Importance", range=[0, imp.max() * 1.25])
            chart(fig, 400, False)
        else:
            st.info("Feature importance is available for the tree-based models.")
    with tabs[4]:
        st.dataframe(pd.DataFrame([(n, " · ".join(f"{k} = {v}" for k, v in (S().params.get(n) or {}).items()) or "—")
                                   for n in S().models], columns=["Model", "Optimum hyperparameters"]), hide_index=True, width="stretch")
    st.write("")
    a, b = st.columns([1, 1])
    with a:
        st.button("💾  Save as project model", key="btn_save", on_click=save_project,
                  help="Stores the models and results so that they can be opened next time with ‘Open saved project’.")
    with b:
        st.button("Use the model: predict ROP  →", type="primary", on_click=go_to, args=("predict",), key="btn_cont5")


# ============================================================================ USE: PREDICT
def predict(model, df):
    return np.clip(model.predict(df[FEATURES]), 0, None)


def model_picker(key):
    names = list(S().models)
    return st.selectbox("Model", names, index=names.index(S().best), key=key,
                        help="The final (selected) model is used by default.")


def page_predict():
    header("Use the model", "Predict ROP", "Set the drilling parameters — the prediction updates instantly.")
    gate(model_ready(), "Train the models first.", "train", "← Go to Step 4 · Train")
    name = model_picker("pm"); model = S().models[name]; TR = train_range()
    left, right = st.columns([1.35, 1], gap="large")
    vals = {}
    with left:
        g = st.columns(2)
        for i, f in enumerate(FEATURES):
            lab, unit, lo, hi, dv, step = META[f]
            with g[i % 2]:
                if f == "Bit_Dia":
                    opts = sorted(set([8.5, 12.25, 17.5] + [round(float(v), 3) for v in S().clean.Bit_Dia.dropna().unique()[:6]]))
                    vals[f] = st.select_slider(f"{lab} ({unit})", options=opts, value=12.25 if 12.25 in opts else opts[0])
                else:
                    vals[f] = st.slider(f"{lab} ({unit})", lo, hi, dv, step)
    x = pd.DataFrame([vals]); rop = float(predict(model, x)[0])
    rmse = S().table.loc[name, "Test RMSE"]
    with right:
        st.markdown(f"<div class='hero-rop'><div class='t'>PREDICTED ROP · {name.upper()}</div><div class='n'>{rop * UF:.1f}</div>"
                    f"<div class='u'>{RU} · ± {rmse * UF:.1f} (test RMSE)</div></div>", unsafe_allow_html=True)
        gauge = go.Figure(go.Indicator(mode="gauge", value=rop * UF, gauge=dict(
            axis=dict(range=[0, 150 * UF], tickcolor=MUTED), bar=dict(color=ORANGE, thickness=.28), bgcolor=PANEL, borderwidth=0,
            steps=[dict(range=[0, 30 * UF], color="#141d33"), dict(range=[30 * UF, 70 * UF], color="#18233d"), dict(range=[70 * UF, 150 * UF], color="#1c2a49")])))
        chart(gauge, 200, False)
        hrs = 1000 / rop if rop > 0 else float("inf")
        st.markdown(f"<div class='glass'>⏱️ Drilling <b>1,000 ft</b> at this ROP takes <b>{hrs:.1f} h</b> on bottom ({hrs / 24:.1f} days).</div>",
                    unsafe_allow_html=True)
    outside = [f for f in FEATURES if not (TR[f][0] - 1e-9 <= vals[f] <= TR[f][1] + 1e-9)]
    if outside:
        st.markdown("<div class='note-warn'>⚠️ <b>Outside the training range</b> — the model is extrapolating; treat this prediction with caution: "
                    + " ".join(f"<span class='badge b-warn'>{META[f][0]}: trained on {TR[f][0]:g}–{TR[f][1]:g} {META[f][1]}</span>" for f in outside)
                    + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='note-ok'>✅ All inputs are inside the training range — prediction is within the model's validated domain.</div>",
                    unsafe_allow_html=True)
    st.write("")
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### All models")
        comp = pd.Series({n: float(predict(m, x)[0]) for n, m in S().models.items()}).sort_values() * UF
        fig = go.Figure(go.Bar(x=comp.values, y=comp.index, orientation="h", text=[f"{v:.1f}" for v in comp.values], textposition="outside",
                               marker_color=[ORANGE if n == name else BLUE for n in comp.index]))
        fig.update_xaxes(title=f"Predicted ROP ({RU})", range=[0, comp.max() * 1.25])
        chart(fig, 300, False)
    with b:
        st.markdown("#### Sensitivity")
        p = st.selectbox("Vary", [f for f in FEATURES if f != "Bit_Dia"], format_func=lambda f: META[f][0])
        grid = pd.DataFrame([vals] * 60); grid[p] = np.linspace(META[p][2], META[p][3], 60)
        fig = go.Figure()
        fig.add_vrect(x0=TR[p][0], x1=TR[p][1], fillcolor="rgba(34,201,152,.07)", line_width=0, annotation_text="training range",
                      annotation_position="top left", annotation_font_color="#8ff0cf")
        fig.add_trace(go.Scatter(x=grid[p], y=predict(model, grid) * UF, mode="lines", line=dict(color=BLUE, width=3), name="ROP"))
        fig.add_trace(go.Scatter(x=[vals[p]], y=[rop * UF], mode="markers", marker=dict(color=ORANGE, size=14, line=dict(color="white", width=2)), name="current"))
        fig.update_xaxes(title=f"{META[p][0]} ({META[p][1]})"); fig.update_yaxes(title=f"ROP ({RU})")
        chart(fig, 300, False)


# ============================================================================ USE: OPTIMIZER
def page_optimizer():
    header("Use the model", "Drilling-parameter optimizer",
           "Searches WOB × RPM combinations for the highest predicted ROP while the other parameters are held constant.")
    gate(model_ready(), "Train the models first.", "train", "← Go to Step 4 · Train")
    name = model_picker("om"); model = S().models[name]
    c = st.columns(4); base = {}
    for i, f in enumerate(["Depth", "MW", "Q", "Bit_Dia"]):
        lab, unit, lo, hi, dv, step = META[f]
        with c[i]:
            base[f] = (st.select_slider(f"{lab} ({unit})", [8.5, 12.25, 17.5], 12.25) if f == "Bit_Dia" else st.slider(f"{lab} ({unit})", lo, hi, dv, step))
    c2 = st.columns(4)
    wmax = c2[0].slider("Max allowable WOB (klbf)", 10.0, 45.0, 35.0, 0.5)
    nmax = c2[1].slider("Max allowable RPM", 60.0, 200.0, 170.0, 5.0)
    tr = c2[2].slider("Torque / WOB ratio", 0.2, 0.9, 0.5, 0.05, help="Torque is estimated from WOB with this ratio")
    spp = c2[3].slider("SPP (psi)", 700.0, 5800.0, 3000.0, 50.0)
    W = np.linspace(5, wmax, 40); N = np.linspace(40, nmax, 40); WW, NN = np.meshgrid(W, N)
    g = pd.DataFrame({"WOB": WW.ravel(), "RPM": NN.ravel(), "Torque": WW.ravel() * tr, "SPP": spp, **base})
    Z = predict(model, g).reshape(WW.shape) * UF
    k = np.unravel_index(np.argmax(Z), Z.shape)
    a, b = st.columns([1.6, 1], gap="large")
    with a:
        fig = go.Figure(go.Contour(x=W, y=N, z=Z, colorscale=[[0, "#111a30"], [0.5, BLUE], [1, ORANGE]], colorbar=dict(title=f"ROP<br>{RU}"),
                                   contours=dict(showlabels=True, labelfont=dict(color="white"))))
        fig.add_trace(go.Scatter(x=[W[k[1]]], y=[N[k[0]]], mode="markers+text", text=["OPTIMUM"], textposition="bottom left",
                                 textfont=dict(color="white", size=13), marker=dict(symbol="star", size=20, color="white", line=dict(color=ORANGE, width=2))))
        fig.update_xaxes(title="WOB (klbf)", range=[W[0], W[-1] + 1.5]); fig.update_yaxes(title="RPM (rev/min)", range=[N[0], N[-1] + 8])
        chart(fig, 470, False)
    with b:
        st.markdown(f"<div class='hero-rop'><div class='t'>MAXIMUM PREDICTED ROP</div><div class='n'>{Z[k]:.1f}</div><div class='u'>{RU}</div></div>",
                    unsafe_allow_html=True)
        st.write("")
        kp = st.columns(2)
        kpi(kp[0], "Optimum WOB", f"{W[k[1]]:.1f}", "klbf"); kpi(kp[1], "Optimum RPM", f"{N[k[0]]:.0f}", "rev/min")
        st.write("")
        st.markdown("<div class='glass'><p>Data-driven recommendation — always check bit ratings, vibration, hole cleaning and torque "
                    "limits before applying it in the field.</p></div>", unsafe_allow_html=True)


# ============================================================================ USE: BATCH
def page_batch():
    header("Use the model", "Batch prediction",
           "Upload a CSV or Excel file of drilling data — ROP is predicted for every row. If measured ROP is included, accuracy is calculated.")
    gate(model_ready(), "Train the models first.", "train", "← Go to Step 4 · Train")
    name = model_picker("bm"); model = S().models[name]
    up = st.file_uploader("Drilling data to predict (CSV / XLSX)", type=["csv", "xlsx", "xls"], key="up_batch")
    if up is None:
        st.markdown("<div class='glass'><p>Columns are mapped the same way as in Step 1 — any column names and units are accepted.</p></div>",
                    unsafe_allow_html=True)
        return
    raw = dio.read_any(up)
    std, *_ = mapping_ui(raw, "batch", require_rop=False)
    if std is None:
        return
    out = raw.copy(); out.insert(0, "ROP_predicted_ft_hr", predict(model, std).round(2))
    if std["ROP"].notna().any():
        m = std["ROP"].notna()
        e = std.loc[m, "ROP"] - out.loc[m, "ROP_predicted_ft_hr"]
        y = std.loc[m, "ROP"]
        c = st.columns(4)
        kpi(c[0], "Rows", f"{len(out):,}"); kpi(c[1], "MAE", f"{e.abs().mean():.2f}", "ft/hr")
        kpi(c[2], "RMSE", f"{np.sqrt((e ** 2).mean()):.2f}", "ft/hr"); kpi(c[3], "R²", f"{1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum():.3f}")
        st.write("")
        s = pd.DataFrame({"Depth": std.Depth, "ROP": std.ROP, "P": out.ROP_predicted_ft_hr}).sort_values("Depth")
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=s.ROP, y=s.Depth, mode="markers", name="Measured", marker=dict(color=MUTED, size=4)))
        fig.add_trace(go.Scattergl(x=s.P, y=s.Depth, mode="markers", name="Predicted", marker=dict(color=ORANGE, size=4)))
        fig.update_yaxes(autorange="reversed", title="Depth (ft)"); fig.update_xaxes(title="ROP (ft/hr)")
        chart(fig, 520)
    else:
        kpi(st.columns(4)[0], "Rows predicted", f"{len(out):,}")
    st.dataframe(out.head(500), width="stretch", height=320)
    st.download_button("⬇️  Download predictions (CSV)", out.to_csv(index=False), "rop_predictions.csv", "text/csv")


# ============================================================================ ABOUT
def page_about():
    header("Project", "About ROP·AI", "BS Final Year Project — Department of Petroleum & Gas Engineering, BUITEMS, Quetta.")
    a, b = st.columns([1.3, 1], gap="large")
    with a:
        st.markdown("""<div class="glass"><h4>Aim</h4><p>Develop, evaluate and compare machine-learning models that predict the Rate of
        Penetration (ROP) from commonly available drilling parameters, and select the most suitable model for unseen data.</p></div>
        <div class="glass"><h4>Workflow</h4><p>Load data → column &amp; unit mapping → cleaning (duplicates, physical limits, missing values,
        3×IQR outliers) → EDA &amp; feature selection → 80 : 20 split → Linear Regression, Decision Tree, Random Forest, SVR, ANN with
        grid search + 5-fold CV → test-set and blind-well evaluation → final model → prediction, optimization and batch prediction.</p></div>
        <div class="glass"><h4>Team</h4><p>Supervisor: [Supervisor Name]<br>Group: [Student 1] · [Student 2] · [Student 3] · [Student 4]</p></div>""",
                    unsafe_allow_html=True)
    with b:
        st.markdown("""<div class="glass"><h4>Tech stack</h4><p>Python · pandas · NumPy · scikit-learn · Plotly · Streamlit · joblib</p></div>
        <div class="glass"><h4>Inputs → output</h4><p>WOB · RPM · Torque · Flow rate Q · Mud density ρ · SPP · Bit diameter D · Depth
        → <b>ROP (ft/hr)</b></p></div>""", unsafe_allow_html=True)
        if (FIG / "diagram_methodology_flowchart.png").exists():
            with st.expander("Methodology flowchart"):
                st.image(str(FIG / "diagram_methodology_flowchart.png"))


PAGES = {"data": page_data, "clean": page_clean, "explore": page_explore, "train": page_train, "results": page_results,
         "predict": page_predict, "optimizer": page_optimizer, "batch": page_batch, "about": page_about}
PAGES.get(S().page, page_data)()
st.markdown("<div class='foot'>ROP·AI · Prediction of Rate of Penetration using Machine Learning · BS FYP, Petroleum &amp; Gas Engineering, "
            "BUITEMS</div>", unsafe_allow_html=True)
