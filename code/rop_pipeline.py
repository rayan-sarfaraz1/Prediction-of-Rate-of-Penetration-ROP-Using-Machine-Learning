"""
ROP prediction pipeline (BS FYP - Petroleum & Gas Engineering).

Workflow (as per supervisor's methodology):
Data Collection -> Data Cleaning -> EDA -> Feature Selection -> Pre-processing
-> Model Development -> Training (GridSearch + CV) -> Testing -> Evaluation
-> Feature Importance -> Model Comparison -> Final ROP Prediction Model

Usage:
    python code/rop_pipeline.py                      # uses synthetic demo data
    python code/rop_pipeline.py --data data/real.csv # uses your real dataset

The CSV must contain the columns listed in FEATURES + TARGET (rename your
columns to match, or edit the COLUMN_MAP below).
"""
import argparse
import json
import time
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV, mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
RES = ROOT / "results"
MOD = ROOT / "models"

FEATURES = ["WOB", "RPM", "Torque", "Q", "MW", "SPP", "Bit_Dia", "Depth"]
TARGET = "ROP"
LABELS = {
    "WOB": "WOB (klbf)", "RPM": "RPM (rev/min)", "Torque": "Torque (kft·lbf)",
    "Q": "Flow rate Q (gpm)", "MW": "Mud density ρ (ppg)", "SPP": "SPP (psi)",
    "Bit_Dia": "Bit diameter D (in)", "Depth": "Depth (ft)", "ROP": "ROP (ft/hr)",
}
# Physical limits used to flag unrealistic values
LIMITS = {
    "WOB": (0.5, 80), "RPM": (10, 400), "Torque": (0, 60), "Q": (100, 1500),
    "MW": (8.0, 20.0), "SPP": (200, 7000), "Bit_Dia": (3, 30), "Depth": (0, 35000),
    "ROP": (0.5, 500),
}
SEED = 42

# ---- Plot style (validated categorical palette, single-hue where possible) ----
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "axes.edgecolor": "#b5b4ae", "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 110, "savefig.dpi": 220, "savefig.bbox": "tight",
})


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)


# ----------------------------------------------------------------------------
# 1. Data cleaning
# ----------------------------------------------------------------------------
def clean(df: pd.DataFrame, k: float = 3.0):
    log = [("Raw records", len(df))]
    df = df.drop_duplicates().copy()
    log.append(("After removing duplicates", len(df)))

    missing_before = df[FEATURES + [TARGET]].isna().sum()

    # Unrealistic values -> NaN
    unrealistic = {}
    for c, (lo, hi) in LIMITS.items():
        mask = (df[c] < lo) | (df[c] > hi)
        unrealistic[c] = int(mask.sum())
        df.loc[mask, c] = np.nan

    # Target cannot be imputed -> drop rows with missing ROP
    df = df.dropna(subset=[TARGET])
    log.append(("After removing rows with invalid/missing ROP", len(df)))

    # NOTE: missing input values are NOT filled here. They are imputed with the median
    # of the TRAINING set inside each model pipeline (SimpleImputer), so no information
    # from the test set leaks into training.

    # Outliers in ROP: IQR rule (3 x IQR, conservative for drilling data)
    q1, q3 = df[TARGET].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    out_mask = (df[TARGET] < lo) | (df[TARGET] > hi)
    n_out = int(out_mask.sum())
    df = df[~out_mask].reset_index(drop=True)
    log.append((f"After removing ROP outliers ({k:g}×IQR)", len(df)))

    quality = pd.DataFrame({
        "Missing values": missing_before,
        "Unrealistic values": pd.Series(unrealistic),
    }).fillna(0).astype(int)
    return df, log, quality, (lo, hi, n_out)


# ----------------------------------------------------------------------------
# 2. EDA
# ----------------------------------------------------------------------------
def eda(raw: pd.DataFrame, df: pd.DataFrame):
    cols = FEATURES + [TARGET]

    # Histograms
    fig, axes = plt.subplots(3, 3, figsize=(7.2, 6.2))
    for ax, c in zip(axes.flat, cols):
        ax.hist(df[c].dropna(), bins=30, color=BLUE, edgecolor="white", linewidth=0.5)
        ax.set_title(LABELS[c]); ax.set_ylabel("Count")
    fig.suptitle("Distribution of drilling parameters and ROP", fontsize=11, color=INK)
    fig.tight_layout(); save(fig, "eda_histograms.png")

    # Box plots: raw vs cleaned ROP + standardized features
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1, 2.4]})
    raw_rop = raw[TARGET].dropna()
    axes[0].boxplot([raw_rop, df[TARGET]], tick_labels=["Raw", "Cleaned"], widths=0.5,
                    patch_artist=True, boxprops=dict(facecolor="#d6e6f8", color=BLUE),
                    medianprops=dict(color=ORANGE, linewidth=1.6),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor=GREY, markeredgecolor="none"))
    axes[0].set_title("ROP before vs after cleaning"); axes[0].set_ylabel("ROP (ft/hr)")
    z = (df[FEATURES] - df[FEATURES].mean()) / df[FEATURES].std()
    axes[1].boxplot([z[c].dropna() for c in FEATURES], tick_labels=FEATURES, widths=0.55, patch_artist=True,
                    boxprops=dict(facecolor="#d6e6f8", color=BLUE),
                    medianprops=dict(color=ORANGE, linewidth=1.6),
                    flierprops=dict(marker="o", markersize=2.5, markerfacecolor=GREY, markeredgecolor="none"))
    axes[1].set_title("Input features (standardized z-scores)"); axes[1].set_ylabel("z-score")
    axes[1].tick_params(axis="x", rotation=30)
    fig.tight_layout(); save(fig, "eda_boxplots.png")

    # Correlation heatmap (diverging, grey midpoint)
    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    cmap = sns.diverging_palette(250, 20, s=75, l=50, center="light", as_cmap=True)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap=cmap, vmin=-1, vmax=1, square=True,
                linewidths=1.5, linecolor="white", cbar_kws={"shrink": 0.8, "label": "Pearson r"},
                annot_kws={"size": 7.5}, ax=ax)
    ax.set_title("Correlation matrix (Pearson)")
    fig.tight_layout(); save(fig, "eda_correlation_heatmap.png")

    # Feature vs ROP scatter (the 5 relationships named in the methodology + 3)
    fig, axes = plt.subplots(2, 4, figsize=(8.0, 4.4), sharey=True)
    for ax, c in zip(axes.flat, FEATURES):
        ax.scatter(df[c], df[TARGET], s=6, alpha=0.35, color=BLUE, edgecolors="none")
        ax.set_xlabel(LABELS[c])
        r = df[c].corr(df[TARGET])
        ax.text(0.03, 0.95, f"r = {r:.2f}", transform=ax.transAxes, va="top", fontsize=8, color=INK)
    for ax in axes[:, 0]:
        ax.set_ylabel("ROP (ft/hr)")
    fig.suptitle("ROP versus individual drilling parameters", fontsize=11, color=INK)
    fig.tight_layout(); save(fig, "eda_feature_vs_rop.png")

    # ROP vs depth log-style track
    fig, ax = plt.subplots(figsize=(3.2, 5.0))
    srt = df.sort_values("Depth")
    ax.plot(srt[TARGET], srt["Depth"], color=BLUE, linewidth=0.5)
    ax.invert_yaxis(); ax.set_xlabel("ROP (ft/hr)"); ax.set_ylabel("Depth (ft)")
    ax.set_title("ROP log vs depth")
    fig.tight_layout(); save(fig, "eda_rop_depth_log.png")

    desc = df[cols].describe().T[["mean", "std", "min", "25%", "50%", "75%", "max"]]
    return corr, desc


# ----------------------------------------------------------------------------
# 3. Feature selection
# ----------------------------------------------------------------------------
def feature_selection(X_tr, y_tr, plot=True, rfe=True):
    """Feature relevance computed on the TRAINING set only (after train-set median imputation)."""
    X = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(X_tr), columns=FEATURES)
    y = y_tr.reset_index(drop=True)
    pearson = X.corrwith(y)
    mi = pd.Series(mutual_info_regression(X, y, random_state=SEED), index=FEATURES)
    rf = RandomForestRegressor(n_estimators=200, random_state=SEED, n_jobs=-1).fit(X, y)
    rf_imp = pd.Series(rf.feature_importances_, index=FEATURES)

    if not rfe:
        table = pd.DataFrame({"Pearson r": pearson, "|r|": pearson.abs(), "Mutual information": mi,
                              "RF importance": rf_imp}).sort_values("Mutual information", ascending=False)
        return table, None, None
    # Recursive feature elimination with 5-fold CV (Random Forest as estimator)
    rfe = RFECV(RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=-1), step=1, min_features_to_select=1,
                cv=KFold(5, shuffle=True, random_state=SEED), scoring="neg_root_mean_squared_error", n_jobs=-1).fit(X, y)
    table = pd.DataFrame({"Pearson r": pearson, "|r|": pearson.abs(), "Mutual information": mi,
                          "RF importance": rf_imp, "RFE rank": pd.Series(rfe.ranking_, index=FEATURES)}
                         ).sort_values("Mutual information", ascending=False)
    n_feat = np.arange(1, len(FEATURES) + 1)
    rfe_curve = pd.DataFrame({"n_features": n_feat, "cv_rmse": -rfe.cv_results_["mean_test_score"],
                              "cv_rmse_std": rfe.cv_results_["std_test_score"]})
    if not plot:
        return table, rfe_curve, int(rfe.n_features_)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=False)
    s = table["|r|"].sort_values()
    axes[0].barh(s.index, s.values, color=BLUE, height=0.6)
    axes[0].set_title("|Pearson r| with ROP"); axes[0].set_xlabel("|r|")
    s = table["Mutual information"].sort_values()
    axes[1].barh(s.index, s.values, color=BLUE, height=0.6)
    axes[1].set_title("Mutual information with ROP"); axes[1].set_xlabel("MI (nats)")
    for ax in axes:
        ax.grid(axis="y", visible=False)
    fig.tight_layout(); save(fig, "feature_selection.png")

    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.errorbar(rfe_curve.n_features, rfe_curve.cv_rmse, yerr=rfe_curve.cv_rmse_std, color=BLUE, marker="o",
                markersize=5, linewidth=2, capsize=3)
    best_n = int(rfe.n_features_)
    ax.scatter([best_n], [rfe_curve.cv_rmse[best_n - 1]], s=90, color=ORANGE, zorder=5, label=f"Optimum: {best_n} features")
    ax.set_xlabel("Number of features retained"); ax.set_ylabel("5-fold CV RMSE (ft/hr)")
    ax.set_title("Recursive feature elimination (RFECV, Random Forest)"); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); save(fig, "feature_rfe.png")
    return table, rfe_curve, best_n


# ----------------------------------------------------------------------------
# 4. Models
# ----------------------------------------------------------------------------
FAST_GRIDS = {  # smaller search spaces for quick runs (e.g. inside the web app)
    "Decision Tree": {"model__max_depth": [6, 10], "model__min_samples_leaf": [5, 10]},
    "Random Forest": {"model__n_estimators": [150], "model__max_depth": [None, 15], "model__min_samples_leaf": [1, 2]},
    "SVR (RBF)": {"regressor__model__C": [10, 100], "regressor__model__gamma": ["scale", 0.2]},
    "ANN (MLP)": {"regressor__model__hidden_layer_sizes": [(64, 32), (64, 32, 16)], "regressor__model__alpha": [1e-3, 1e-2]},
}


def build_models(fast: bool = False):
    models = _build_models()
    if fast:
        models = {n: (est, FAST_GRIDS.get(n, grid)) for n, (est, grid) in models.items()}
    return models


def _build_models():
    scaled = lambda est: Pipeline([("imputer", SimpleImputer(strategy="median")),
                                   ("scaler", StandardScaler()), ("model", est)])
    return {
        "Linear Regression": (scaled(LinearRegression()), {}),
        "Decision Tree": (scaled(DecisionTreeRegressor(random_state=SEED)), {
            "model__max_depth": [4, 6, 8, 10, 14],
            "model__min_samples_split": [2, 10, 20],
            "model__min_samples_leaf": [1, 5, 10],
        }),
        "Random Forest": (scaled(RandomForestRegressor(random_state=SEED, n_jobs=-1)), {
            "model__n_estimators": [100, 300],
            "model__max_depth": [None, 12, 20],
            "model__min_samples_split": [2, 5],
            "model__min_samples_leaf": [1, 2],
        }),
        "SVR (RBF)": (TransformedTargetRegressor(
            regressor=scaled(SVR(kernel="rbf")), transformer=StandardScaler()), {
            "regressor__model__C": [1, 10, 100],
            "regressor__model__gamma": ["scale", 0.05, 0.2],
            "regressor__model__epsilon": [0.05, 0.1],
        }),
        "ANN (MLP)": (TransformedTargetRegressor(
            regressor=scaled(MLPRegressor(max_iter=3000, early_stopping=True,
                                          n_iter_no_change=30, random_state=SEED)),
            transformer=StandardScaler()), {
            "regressor__model__hidden_layer_sizes": [(32, 16), (64, 32), (64, 32, 16)],
            "regressor__model__alpha": [1e-4, 1e-3, 1e-2],
            "regressor__model__learning_rate_init": [1e-3, 5e-3],
        }),
    }


def metrics(y, p):
    mse = mean_squared_error(y, p)
    return {"MAE": mean_absolute_error(y, p), "MSE": mse, "RMSE": float(np.sqrt(mse)),
            "R2": r2_score(y, p)}


def split(df):
    X, y = df[FEATURES], df[TARGET]
    return train_test_split(X, y, test_size=0.20, random_state=SEED)


def train_one(name, est, grid, X_tr, y_tr, X_te, y_te):
    """Grid search (5-fold CV) + refit + test evaluation for one model."""
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    t0 = time.perf_counter()
    gs = GridSearchCV(est, grid or {}, cv=cv, scoring="neg_root_mean_squared_error", n_jobs=-1)
    gs.fit(X_tr, y_tr)
    tune_time = time.perf_counter() - t0
    best = gs.best_estimator_
    t0 = time.perf_counter(); best.fit(X_tr, y_tr); fit_time = time.perf_counter() - t0
    m_tr, m_te = metrics(y_tr, best.predict(X_tr)), metrics(y_te, p_te := best.predict(X_te))
    row = {"Model": name, "Train R2": m_tr["R2"], "Train RMSE": m_tr["RMSE"], "CV RMSE": -gs.best_score_,
           **{f"Test {k}": v for k, v in m_te.items()}, "Training time (s)": fit_time, "Tuning time (s)": tune_time}
    params = {k.split("__")[-1]: (list(v) if isinstance(v, tuple) else v) for k, v in gs.best_params_.items()}
    return row, p_te, params, best


def train_and_evaluate(X_tr, X_te, y_tr, y_te, fast=False):
    rows, preds, best_params, fitted = [], {}, {}, {}
    for name, (est, grid) in build_models(fast).items():
        row, p_te, params, best = train_one(name, est, grid, X_tr, y_tr, X_te, y_te)
        rows.append(row); preds[name] = p_te; best_params[name] = params; fitted[name] = best
        print(f"{name:18s}  test R2={row['Test R2']:.3f}  RMSE={row['Test RMSE']:.2f}  fit={row['Training time (s)']:.2f}s")
    table = pd.DataFrame(rows).set_index("Model")
    return table, preds, best_params, fitted


# ----------------------------------------------------------------------------
# 5. Evaluation plots
# ----------------------------------------------------------------------------
def evaluation_plots(table, preds, y_te, fitted, X_te, best):
    names = list(preds)
    y = y_te.values
    lim = (0, max(y.max(), max(p.max() for p in preds.values())) * 1.05)

    # Actual vs predicted
    fig, axes = plt.subplots(2, 3, figsize=(8.0, 5.4))
    for ax, n in zip(axes.flat, names):
        ax.scatter(y, preds[n], s=7, alpha=0.45, color=BLUE, edgecolors="none")
        ax.plot(lim, lim, color=INK2, linewidth=1, linestyle="--")
        ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
        ax.set_title(n); ax.set_xlabel("Actual ROP (ft/hr)"); ax.set_ylabel("Predicted ROP (ft/hr)")
        ax.text(0.04, 0.95, f"R² = {table.loc[n, 'Test R2']:.3f}\nRMSE = {table.loc[n, 'Test RMSE']:.2f}",
                transform=ax.transAxes, va="top", fontsize=8, color=INK)
    axes.flat[-1].axis("off")
    fig.suptitle("Actual vs predicted ROP on the unseen test set (20%)", fontsize=11, color=INK)
    fig.tight_layout(); save(fig, "eval_actual_vs_predicted.png")

    # Residual plots
    fig, axes = plt.subplots(2, 3, figsize=(8.0, 5.0), sharey=True)
    for ax, n in zip(axes.flat, names):
        res = y - preds[n]
        ax.scatter(preds[n], res, s=7, alpha=0.45, color=BLUE, edgecolors="none")
        ax.axhline(0, color=INK2, linewidth=1, linestyle="--")
        ax.set_title(n); ax.set_xlabel("Predicted ROP (ft/hr)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Residual (ft/hr)")
    axes.flat[-1].axis("off")
    fig.suptitle("Residuals vs predicted ROP", fontsize=11, color=INK)
    fig.tight_layout(); save(fig, "eval_residuals.png")

    # Error distribution
    fig, axes = plt.subplots(2, 3, figsize=(8.0, 4.8), sharex=True)
    bins = np.linspace(-40, 40, 41)
    for ax, n in zip(axes.flat, names):
        err = y - preds[n]
        ax.hist(np.clip(err, -40, 40), bins=bins, color=BLUE, edgecolor="white", linewidth=0.5)
        ax.axvline(0, color=INK2, linewidth=1, linestyle="--")
        ax.set_title(f"{n}\nmean = {err.mean():.2f}, sd = {err.std():.2f}", fontsize=8.5)
        ax.set_xlabel("Error = Actual − Predicted (ft/hr)")
    axes.flat[-1].axis("off")
    fig.tight_layout(); save(fig, "eval_error_distribution.png")

    # Model comparison (two separate panels - never a dual axis)
    order = table.sort_values("Test R2").index
    colors = [ORANGE if n == best else BLUE for n in order]
    fig, axes = plt.subplots(1, 3, figsize=(8.2, 3.0), sharey=True)
    for ax, col, title in zip(axes, ["Test R2", "Test RMSE", "Test MAE"],
                              ["R² (higher is better)", "RMSE, ft/hr (lower is better)", "MAE, ft/hr (lower is better)"]):
        vals = table.loc[order, col]
        ax.barh(order, vals, color=colors, height=0.6)
        for i, v in enumerate(vals):
            ax.text(v, i, f" {v:.3f}" if col == "Test R2" else f" {v:.2f}", va="center", fontsize=7.5, color=INK)
        ax.set_title(title); ax.grid(axis="y", visible=False)
        ax.set_xlim(0, vals.max() * 1.25)
    fig.tight_layout(); save(fig, "eval_model_comparison.png")

    # Feature importance (Random Forest + Decision Tree)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for ax, n in zip(axes, ["Random Forest", "Decision Tree"]):
        imp = pd.Series(fitted[n].named_steps["model"].feature_importances_, index=FEATURES).sort_values()
        ax.barh(imp.index, imp.values, color=BLUE, height=0.6)
        for i, v in enumerate(imp.values):
            ax.text(v, i, f" {v:.2f}", va="center", fontsize=7.5, color=INK)
        ax.set_title(f"{n} feature importance"); ax.set_xlabel("Importance (impurity decrease)")
        ax.set_xlim(0, imp.max() * 1.25); ax.grid(axis="y", visible=False)
    fig.tight_layout(); save(fig, "eval_feature_importance.png")

    # Prediction along depth for best model (test points)
    idx = np.argsort(X_te["Depth"].values)
    fig, ax = plt.subplots(figsize=(3.4, 5.0))
    ax.plot(y[idx], X_te["Depth"].values[idx], color=GREY, linewidth=0.8, label="Actual")
    ax.plot(preds[best][idx], X_te["Depth"].values[idx], color=ORANGE, linewidth=0.8, label=f"Predicted ({best})")
    ax.invert_yaxis(); ax.set_xlabel("ROP (ft/hr)"); ax.set_ylabel("Depth (ft)")
    ax.legend(fontsize=7, frameon=False, loc="lower right"); ax.set_title("Test-set ROP vs depth")
    fig.tight_layout(); save(fig, "eval_depth_track.png")


def select_final_model(table, blind_table=None):
    """Final-model rule: highest test R2; if a blind well is available, highest mean of
    test R2 and blind-well R2 (rewards models that also generalise to an unseen well)."""
    score = table["Test R2"].copy()
    if blind_table is not None:
        score = (table["Test R2"] + blind_table["R2"]) / 2
    return score.idxmax(), score


def blind_test(path, fitted):
    """Apply the trained models to a completely separate, previously unseen well (CSV path or DataFrame)."""
    raw = path if isinstance(path, pd.DataFrame) else pd.read_csv(path)
    df, *_ = clean(raw)
    X, y = df[FEATURES], df[TARGET]
    rows, preds = [], {}
    for n, m in fitted.items():
        p = m.predict(X); preds[n] = p
        rows.append({"Model": n, **metrics(y, p)})
    table = pd.DataFrame(rows).set_index("Model")
    return table, len(df), df, preds


def blind_plot(df, preds, table, best):
    y = df[TARGET]
    o = np.argsort(df["Depth"].values)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    axes[0].plot(y.values[o], df["Depth"].values[o], color=GREY, linewidth=0.8, label="Measured")
    axes[0].plot(preds[best][o], df["Depth"].values[o], color=ORANGE, linewidth=0.8, label=f"Predicted ({best})")
    axes[0].invert_yaxis(); axes[0].set_xlabel("ROP (ft/hr)"); axes[0].set_ylabel("Depth (ft)")
    axes[0].legend(frameon=False, fontsize=7, loc="lower right"); axes[0].set_title("Blind well: ROP vs depth")
    lim = (0, max(y.max(), preds[best].max()) * 1.05)
    axes[1].scatter(y, preds[best], s=7, alpha=0.45, color=BLUE, edgecolors="none")
    axes[1].plot(lim, lim, color=INK2, linestyle="--", linewidth=1); axes[1].set_xlim(lim); axes[1].set_ylim(lim)
    axes[1].set_aspect("equal"); axes[1].set_xlabel("Measured ROP (ft/hr)"); axes[1].set_ylabel("Predicted ROP (ft/hr)")
    axes[1].set_title(f"Blind well ({best}): R² = {table.loc[best, 'R2']:.3f}")
    fig.tight_layout(); save(fig, "eval_blind_well.png")


def model_card(best, fitted, table, best_params, X_tr, n_feat_rfe, blind):
    """Documentation of the final model, as required by the methodology (Section 13)."""
    model = fitted[best].regressor_ if hasattr(fitted[best], "regressor_") else fitted[best]
    est = model.named_steps["model"]
    card = {
        "final_model": best,
        "algorithm": type(est).__name__,
        "pipeline": [type(step).__name__ for _, step in model.steps] + (["StandardScaler (target)"] if hasattr(fitted[best], "regressor_") else []),
        "input_parameters": {f: LABELS[f] for f in FEATURES},
        "target": LABELS[TARGET],
        "hyperparameters": best_params[best],
        "test_metrics": {k.replace("Test ", ""): round(float(table.loc[best, k]), 4)
                         for k in ["Test MAE", "Test MSE", "Test RMSE", "Test R2"]},
        "cv_rmse": round(float(table.loc[best, "CV RMSE"]), 4),
        "training_time_s": round(float(table.loc[best, "Training time (s)"]), 4),
        "rfe_optimum_n_features": n_feat_rfe,
        "training_range": {f: [round(float(X_tr[f].min()), 3), round(float(X_tr[f].max()), 3)] for f in FEATURES},
        "blind_well_metrics": None if blind is None else {k: round(float(v), 4) for k, v in blind[0].loc[best].items()},
        "files": {"model": "models/final_rop_model.joblib", "all_models": "models/all_models.joblib"},
    }
    if hasattr(est, "hidden_layer_sizes"):
        card["architecture"] = {"input_neurons": len(FEATURES), "hidden_layers": list(est.hidden_layer_sizes),
                                "activation": est.activation, "output_neurons": 1, "solver": est.solver,
                                "iterations_trained": int(est.n_iter_)}
    (RES / "model_card.json").write_text(json.dumps(card, indent=2))
    return card


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_drilling_data_raw.csv"))
    ap.add_argument("--blind", default=str(ROOT / "data" / "synthetic_blind_well.csv"),
                    help="CSV of a separate, unseen well for the final blind test ('' to skip)")
    args = ap.parse_args()
    for d in (FIG, RES, MOD):
        d.mkdir(exist_ok=True)

    # 1. Cleaning
    raw = pd.read_csv(args.data)
    df, log, quality, (lo, hi, n_out) = clean(raw)
    pd.DataFrame(log, columns=["Step", "Records"]).to_csv(RES / "cleaning_log.csv", index=False)
    quality.to_csv(RES / "data_quality.csv")
    df.to_csv(ROOT / "data" / "cleaned_drilling_data.csv", index=False)

    # 2. EDA (descriptive, on the cleaned dataset)
    corr, desc = eda(raw, df)
    desc.to_csv(RES / "descriptive_statistics.csv")
    corr.to_csv(RES / "correlation_matrix.csv")

    # 3. Split FIRST, then everything that learns from data uses the training set only
    X_tr, X_te, y_tr, y_te = split(df)
    fs, rfe_curve, n_feat_rfe = feature_selection(X_tr, y_tr)
    fs.to_csv(RES / "feature_selection.csv"); rfe_curve.to_csv(RES / "rfe_curve.csv", index=False)

    # 4-5. Models, tuning, testing
    table, preds, best_params, fitted = train_and_evaluate(X_tr, X_te, y_tr, y_te)
    table.to_csv(RES / "model_comparison.csv")

    # 6. Blind test on a separate, previously unseen well
    blind = None
    if args.blind and Path(args.blind).exists():
        blind = blind_test(args.blind, fitted)
        blind[0].to_csv(RES / "blind_test.csv")

    # 7. Final model selection + evaluation graphs
    best, score = select_final_model(table, None if blind is None else blind[0])
    score.rename("Selection score").to_csv(RES / "selection_score.csv")
    evaluation_plots(table, preds, y_te, fitted, X_te, best)
    if blind is not None:
        blind_plot(blind[2], blind[3], blind[0], best)
        print(f"Blind well ({blind[1]} rows): R2={blind[0].loc[best, 'R2']:.3f}")

    # 8. Save + document final model
    joblib.dump({"model": fitted[best], "features": FEATURES, "target": TARGET},
                MOD / "final_rop_model.joblib")
    joblib.dump({"models": fitted, "best": best, "features": FEATURES, "target": TARGET},
                MOD / "all_models.joblib", compress=3)
    tp = X_te.copy(); tp["ROP_actual"] = y_te.values
    for n, p in preds.items():
        tp[f"pred_{n}"] = p
    tp.to_csv(RES / "test_predictions.csv", index=False)
    imp = pd.DataFrame({n: fitted[n].named_steps["model"].feature_importances_
                        for n in ["Random Forest", "Decision Tree"]}, index=FEATURES)
    imp.to_csv(RES / "feature_importance.csv")
    model_card(best, fitted, table, best_params, X_tr, n_feat_rfe, blind)
    summary = {"best_model": best, "best_params": best_params, "n_train": len(X_tr),
               "n_test": len(X_te), "outlier_bounds": [lo, hi], "n_outliers": n_out,
               "rfe_optimum_n_features": n_feat_rfe, "n_blind": None if blind is None else blind[1],
               "selection_rule": "mean of test R2 and blind-well R2" if blind is not None else "test R2"}
    (RES / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("Best model:", best)


if __name__ == "__main__":
    main()
