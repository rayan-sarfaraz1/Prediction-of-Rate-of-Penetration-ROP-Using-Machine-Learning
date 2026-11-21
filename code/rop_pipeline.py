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
from sklearn.feature_selection import mutual_info_regression
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
def clean(df: pd.DataFrame):
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

    # Median imputation of features
    medians = df[FEATURES].median()
    df[FEATURES] = df[FEATURES].fillna(medians)

    # Outliers in ROP: IQR rule (3 x IQR, conservative for drilling data)
    q1, q3 = df[TARGET].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 3 * iqr, q3 + 3 * iqr
    out_mask = (df[TARGET] < lo) | (df[TARGET] > hi)
    n_out = int(out_mask.sum())
    df = df[~out_mask].reset_index(drop=True)
    log.append(("After removing ROP outliers (3×IQR)", len(df)))

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
        ax.hist(df[c], bins=30, color=BLUE, edgecolor="white", linewidth=0.5)
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
    axes[1].boxplot([z[c] for c in FEATURES], tick_labels=FEATURES, widths=0.55, patch_artist=True,
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
def feature_selection(df):
    X, y = df[FEATURES], df[TARGET]
    pearson = X.corrwith(y)
    mi = pd.Series(mutual_info_regression(X, y, random_state=SEED), index=FEATURES)
    rf = RandomForestRegressor(n_estimators=200, random_state=SEED, n_jobs=-1).fit(X, y)
    rf_imp = pd.Series(rf.feature_importances_, index=FEATURES)
    table = pd.DataFrame({"Pearson r": pearson, "|r|": pearson.abs(),
                          "Mutual information": mi, "RF importance": rf_imp}).sort_values("Mutual information", ascending=False)

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
    return table


# ----------------------------------------------------------------------------
# 4. Models
# ----------------------------------------------------------------------------
def build_models():
    scaled = lambda est: Pipeline([("scaler", StandardScaler()), ("model", est)])
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


def train_and_evaluate(df):
    X, y = df[FEATURES], df[TARGET]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20, random_state=SEED)
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    rows, preds, best_params, fitted = [], {}, {}, {}
    for name, (est, grid) in build_models().items():
        t0 = time.perf_counter()
        gs = GridSearchCV(est, grid or {}, cv=cv, scoring="neg_root_mean_squared_error", n_jobs=-1)
        gs.fit(X_tr, y_tr)
        tune_time = time.perf_counter() - t0
        best = gs.best_estimator_
        t0 = time.perf_counter(); best.fit(X_tr, y_tr); fit_time = time.perf_counter() - t0
        p_tr, p_te = best.predict(X_tr), best.predict(X_te)
        m_tr, m_te = metrics(y_tr, p_tr), metrics(y_te, p_te)
        rows.append({"Model": name, "Train R2": m_tr["R2"], "Train RMSE": m_tr["RMSE"],
                     "CV RMSE": -gs.best_score_, **{f"Test {k}": v for k, v in m_te.items()},
                     "Training time (s)": fit_time, "Tuning time (s)": tune_time})
        preds[name] = p_te
        best_params[name] = {k.split("__")[-1]: (list(v) if isinstance(v, tuple) else v)
                             for k, v in gs.best_params_.items()}
        fitted[name] = best
        print(f"{name:18s}  test R2={m_te['R2']:.3f}  RMSE={m_te['RMSE']:.2f}  fit={fit_time:.2f}s")
    table = pd.DataFrame(rows).set_index("Model")
    return table, preds, best_params, fitted, (X_tr, X_te, y_tr, y_te)


# ----------------------------------------------------------------------------
# 5. Evaluation plots
# ----------------------------------------------------------------------------
def evaluation_plots(table, preds, y_te, fitted, X_te):
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
    best = table["Test R2"].idxmax()
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
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_drilling_data_raw.csv"))
    args = ap.parse_args()
    for d in (FIG, RES, MOD):
        d.mkdir(exist_ok=True)

    raw = pd.read_csv(args.data)
    df, log, quality, (lo, hi, n_out) = clean(raw)
    pd.DataFrame(log, columns=["Step", "Records"]).to_csv(RES / "cleaning_log.csv", index=False)
    quality.to_csv(RES / "data_quality.csv")
    df.to_csv(ROOT / "data" / "cleaned_drilling_data.csv", index=False)

    corr, desc = eda(raw, df)
    desc.to_csv(RES / "descriptive_statistics.csv")
    corr.to_csv(RES / "correlation_matrix.csv")

    fs = feature_selection(df)
    fs.to_csv(RES / "feature_selection.csv")

    table, preds, best_params, fitted, (X_tr, X_te, y_tr, y_te) = train_and_evaluate(df)
    table.to_csv(RES / "model_comparison.csv")
    best = evaluation_plots(table, preds, y_te, fitted, X_te)

    joblib.dump({"model": fitted[best], "features": FEATURES, "target": TARGET},
                MOD / "final_rop_model.joblib")
    summary = {"best_model": best, "best_params": best_params, "n_train": len(X_tr),
               "n_test": len(X_te), "outlier_bounds": [lo, hi], "n_outliers": n_out}
    (RES / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("Best model:", best)


if __name__ == "__main__":
    main()
