"""
Automated verification of the ROP project.
Run:  python -m pytest -q tests/
(Run code/rop_pipeline.py first so that results/ and models/ exist.)
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import rop_pipeline as rp  # noqa: E402

RES, MOD, FIG = ROOT / "results", ROOT / "models", ROOT / "figures"
CLEAN = pd.read_csv(ROOT / "data" / "cleaned_drilling_data.csv")
CMP = pd.read_csv(RES / "model_comparison.csv", index_col=0)
PRED = pd.read_csv(RES / "test_predictions.csv")
SUMMARY = json.loads((RES / "summary.json").read_text())
BUNDLE = joblib.load(MOD / "all_models.joblib")
MODELS = ["Linear Regression", "Decision Tree", "Random Forest", "SVR (RBF)", "ANN (MLP)"]


# ---------------------------------------------------------------- formulas
def test_metric_formulas_match_definitions():
    rng = np.random.default_rng(0)
    y, p = rng.uniform(5, 150, 500), rng.uniform(5, 150, 500)
    m = rp.metrics(y, p)
    assert m["MAE"] == pytest.approx(np.mean(np.abs(y - p)))
    assert m["MSE"] == pytest.approx(np.mean((y - p) ** 2))
    assert m["RMSE"] == pytest.approx(np.sqrt(np.mean((y - p) ** 2)))
    assert m["R2"] == pytest.approx(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def test_perfect_prediction_gives_zero_error_and_r2_one():
    y = np.array([10.0, 20.0, 30.0])
    m = rp.metrics(y, y)
    assert m["MAE"] == 0 and m["RMSE"] == 0 and m["R2"] == 1


@pytest.mark.parametrize("model", MODELS)
def test_reported_metrics_recomputed_from_saved_predictions(model):
    y, p = PRED["ROP_actual"].values, PRED[f"pred_{model}"].values
    assert CMP.loc[model, "Test MAE"] == pytest.approx(np.mean(np.abs(y - p)), rel=1e-9)
    assert CMP.loc[model, "Test RMSE"] == pytest.approx(np.sqrt(np.mean((y - p) ** 2)), rel=1e-9)
    assert CMP.loc[model, "Test R2"] == pytest.approx(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2), rel=1e-9)
    assert CMP.loc[model, "Test MSE"] == pytest.approx(CMP.loc[model, "Test RMSE"] ** 2, rel=1e-9)


# ---------------------------------------------------------------- cleaning
def test_cleaned_data_has_no_duplicates_or_missing_target():
    assert not CLEAN.duplicated().any()
    assert CLEAN["ROP"].notna().all()


def test_cleaned_values_are_within_physical_limits():
    for col, (lo, hi) in rp.LIMITS.items():
        v = CLEAN[col].dropna()
        assert v.between(lo, hi).all(), col


def test_rop_outliers_removed_with_iqr_rule():
    lo, hi = SUMMARY["outlier_bounds"]
    assert CLEAN["ROP"].between(lo, hi).all()


def test_cleaning_function_removes_bad_rows():
    bad = pd.DataFrame([{f: 10.0 for f in rp.FEATURES} | {"ROP": -1.0, "Depth": 5000.0, "Bit_Dia": 8.5, "MW": 10.0,
                                                           "Q": 500.0, "SPP": 2000.0, "RPM": 100.0}] * 2)
    good = pd.DataFrame([{"WOB": 20.0, "RPM": 120.0, "Torque": 10.0, "Q": 600.0, "MW": 10.0, "SPP": 2500.0,
                          "Bit_Dia": 12.25, "Depth": 6000.0 + i, "ROP": 40.0 + i} for i in range(20)])
    out, *_ = rp.clean(pd.concat([bad, good], ignore_index=True))
    assert len(out) == 20 and (out["ROP"] > 0).all()


# ---------------------------------------------------------------- split / leakage
def _split():
    return rp.split(CLEAN)


def test_split_is_80_20_and_disjoint():
    X_tr, X_te, y_tr, y_te = _split()
    n = len(CLEAN)
    assert len(X_te) == pytest.approx(0.2 * n, abs=1)
    assert len(X_tr) + len(X_te) == n
    assert set(X_tr.index).isdisjoint(X_te.index)
    assert SUMMARY["n_train"] == len(X_tr) and SUMMARY["n_test"] == len(X_te)


def test_saved_test_set_matches_split():
    _, X_te, _, y_te = _split()
    assert np.allclose(PRED["ROP_actual"].values, y_te.values)


@pytest.mark.parametrize("model", ["Linear Regression", "Random Forest"])
def test_imputer_and_scaler_fitted_on_training_data_only(model):
    X_tr, _, _, _ = _split()
    pipe = BUNDLE["models"][model]
    imp, sc = pipe.named_steps["imputer"], pipe.named_steps["scaler"]
    assert np.allclose(imp.statistics_, X_tr.median().values)
    assert np.allclose(sc.mean_, X_tr.fillna(X_tr.median()).mean().values)


def test_blind_well_not_used_in_training():
    blind = pd.read_csv(ROOT / "data" / "synthetic_blind_well.csv")
    key = lambda d: set(map(tuple, d[rp.FEATURES + ["ROP"]].round(3).dropna().values))
    assert key(blind).isdisjoint(key(CLEAN))


# ---------------------------------------------------------------- models
def test_all_five_models_trained_and_compared():
    assert set(MODELS) == set(CMP.index) == set(BUNDLE["models"])
    for col in ["Test MAE", "Test MSE", "Test RMSE", "Test R2", "Training time (s)"]:
        assert CMP[col].notna().all()


def test_random_forest_tuned_on_required_hyperparameters():
    grid = rp.build_models()["Random Forest"][1]
    for hp in ["n_estimators", "max_depth", "min_samples_split", "min_samples_leaf"]:
        assert f"model__{hp}" in grid


def test_saved_final_model_reproduces_predictions():
    final = joblib.load(MOD / "final_rop_model.joblib")
    _, X_te, _, _ = _split()
    p = final["model"].predict(X_te)
    assert np.allclose(p, PRED[f"pred_{SUMMARY['best_model']}"].values)


def test_final_model_follows_selection_rule():
    score = pd.read_csv(RES / "selection_score.csv", index_col=0).iloc[:, 0]
    assert SUMMARY["best_model"] == score.idxmax()


def test_nonlinear_models_beat_linear_baseline():
    assert CMP.loc[SUMMARY["best_model"], "Test RMSE"] < CMP.loc["Linear Regression", "Test RMSE"]


def test_predictions_are_physically_sensible():
    model = BUNDLE["models"][SUMMARY["best_model"]]
    base = pd.DataFrame([{"WOB": 20.0, "RPM": 120.0, "Torque": 10.0, "Q": 700.0, "MW": 11.0, "SPP": 3000.0,
                          "Bit_Dia": 12.25, "Depth": 7000.0}])
    p = model.predict(base)[0]
    assert 0 < p < 300
    hi_wob = base.assign(WOB=35.0, Torque=17.5)
    assert model.predict(hi_wob)[0] > p          # more WOB -> faster drilling
    heavy = base.assign(MW=13.0)
    assert model.predict(heavy)[0] < p           # heavier mud -> slower drilling


def test_model_card_documents_required_items():
    card = json.loads((RES / "model_card.json").read_text())
    for k in ["input_parameters", "algorithm", "hyperparameters", "test_metrics", "training_range"]:
        assert k in card
    assert card["final_model"] == SUMMARY["best_model"]


# ---------------------------------------------------------------- outputs required by the methodology
@pytest.mark.parametrize("fig", [
    "eda_histograms.png", "eda_boxplots.png", "eda_correlation_heatmap.png", "eda_feature_vs_rop.png",
    "feature_selection.png", "feature_rfe.png", "eval_actual_vs_predicted.png", "eval_error_distribution.png",
    "eval_residuals.png", "eval_feature_importance.png", "eval_model_comparison.png", "eval_blind_well.png",
    "diagram_methodology_flowchart.png"])
def test_required_figures_exist(fig):
    assert (FIG / fig).exists() and (FIG / fig).stat().st_size > 10_000


# ---------------------------------------------------------------- web app
APP_PAGES = ["🏠 Overview", "🎯 Predict ROP", "⚙️ Optimizer", "📊 Data Explorer", "📈 Model Results",
             "📁 Batch Prediction", "📄 Reports", "ℹ️ About"]


@pytest.mark.parametrize("page", APP_PAGES)
def test_every_app_page_runs_without_error(page):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]
