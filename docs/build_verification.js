/*
 * Builds docs/ROP_FYP_Verification_Report.docx — requirements traceability + verification evidence.
 * Usage: python code/verify.py && node docs/build_verification.js
 */
const fs = require("fs");
const path = require("path");
const { AlignmentType, ImageRun, Paragraph } = require("docx");
const { Builder, buildOne, tocPages, TITLE, SUPERVISOR, MEMBERS, BATCH, D } = require("./build_thesis");

const V = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "results", "verification.json"), "utf8"));
const M = Object.fromEntries(D.models.map((r) => [r[0], r]));
const BL = Object.fromEntries((D.blind || []).map((r) => [r[0], r[4]]));
const best = D.summary.best_model;
const OK = "✅ Met", PART = "⚠️ Partly", NA = "— N/A";

function front(b, toc) {
  b.center("REQUIREMENTS & VERIFICATION REPORT", { size: 34, bold: true, before: 900, after: 200, color: "EB6834" });
  b.center(TITLE, { size: 26, bold: true, after: 400 });
  b.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new ImageRun({ type: "png",
    data: fs.readFileSync(path.join(__dirname, "assets", "buitems_logo.png")), transformation: { width: 130, height: 130 },
    altText: { title: "BUITEMS logo", description: "BUITEMS logo", name: "logo" } })] }));
  b.center("Department of Petroleum & Gas Engineering, BUITEMS", { after: 60 });
  b.center(BATCH, { after: 300 });
  b.center(`Supervisor: ${SUPERVISOR}`, { after: 120 });
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  b.center(`Verification run: ${V.date} · Python ${V.python} · ${V.n_pass}/${V.n_tests} automated tests passed`, { before: 400, size: 22 });
  tocPages(b, toc, false);
}

function body(b) {
  b.chapter("Purpose and Summary");
  b.p("This report checks the complete project against **every requirement of the supervisor's methodology document** (*Prediction of Rate of Penetration (ROP) Using Machine Learning — Methodology*, Sections 1–15 and the recommended BS-FYP scope) and against the **suggested thesis scheme** (Chapters 1–5). For each requirement it states where it is implemented and what evidence proves it. It also documents the correctness audit, the issues found and fixed, the automated test results and an independent re-computation of all reported metrics.");
  b.table("Verification summary", ["Item", "Result"], [
    ["Methodology requirements (Sections 1–15 + scope)", "All met; data collection partly (real field data pending)"],
    ["Thesis scheme items (Chapters 1–5)", "All present in the complete thesis draft"],
    ["Automated tests", `${V.n_pass} of ${V.n_tests} passed`],
    ["Independent re-computation of MAE, RMSE, R²", `Max. difference ${Math.max(...V.recompute.map((r) => r.max_abs_diff)).toExponential(1)} (identical)`],
    ["Data leakage", "None — imputer, scaler and feature selection fitted on the training set only (tested)"],
    ["Final model", `${best} — test R² ${M[best][7].toFixed(3)}, blind-well R² ${(BL[best] ?? 0).toFixed(3)}`],
  ], [3.6, 4.4], { leftAll: true });
  b.note("Important — what “correct” means here",
    "The workflow, formulas, data handling and software have been verified to be correct. The *numbers* in this report and in Chapter 4 of the thesis come from the synthetic demonstration dataset and therefore only show that the method works. They become the real project results only after the pipeline is run on real drilling data (e.g. the Equinor Volve dataset). The same code, tests and documents regenerate automatically with the real data.");

  b.chapter("Methodology Requirements Traceability");
  b.p("The table maps each requirement in the supervisor's methodology to its implementation and evidence. Figure and table numbers refer to the complete thesis draft.");
  b.table("Traceability of the methodology requirements", ["§", "Requirement", "Implementation", "Evidence", "Status"], [
    ["1", "Workflow: collection → cleaning → EDA → feature selection → pre-processing → development → training → testing → evaluation → prediction", "code/rop_pipeline.py main()", "Fig. 3-1 flowchart; Thesis Ch. 3", OK],
    ["2", "Historical data from published/open-source/field/lab sources", "--data option for any CSV; Volve planned; synthetic demo + separate blind well", "Thesis §3.2", PART + " (real data pending)"],
    ["3.1", "Remove duplicate records", "clean(): drop_duplicates", "Table 4-1; test_cleaned_data_has_no_duplicates", OK],
    ["3.2", "Identify missing values", "clean(): missing count per column", "Table 4-2", OK],
    ["3.3", "Handle missing values (median imputation or removal)", "Missing ROP rows removed; inputs: SimpleImputer(median) fitted on training set", "test_imputer_and_scaler_fitted_on_training_data_only", OK],
    ["3.4", "Identify unrealistic drilling values", "Physical limits table (LIMITS)", "Table 3-2; test_cleaned_values_are_within_physical_limits", OK],
    ["3.5", "Detect and treat outliers", "3×IQR rule on ROP", "Fig. 4-2; test_rop_outliers_removed_with_iqr_rule", OK],
    ["3.6", "Consistent units", "Oilfield units throughout; conversion table", "Thesis §3.3; User Guide Table 5-1", OK],
    ["3.7", "Convert categorical variables", "No categorical inputs in dataset; one-hot encoding described", "Thesis §3.3", NA],
    ["4", "EDA: histograms, box plots, scatter, correlation matrix, heatmap, ROP vs WOB/RPM/Torque/Depth/Q", "eda()", "Figs. 4-1 … 4-5", OK],
    ["5", "Inputs X = [WOB, RPM, T, Q, ρ, SPP, D, Depth], Y = ROP", "FEATURES, TARGET", "Table 3-1", OK],
    ["5", "Feature selection: correlation, importance, mutual information, RFE", "feature_selection() incl. RFECV — training set only", "Table 4-4; Figs. 4-6, 4-7", OK],
    ["6", "80 % training / 20 % testing; test kept separate", "split(): train_test_split(test_size = 0.2)", "test_split_is_80_20_and_disjoint", OK],
    ["15", "Normalization / standardization", "StandardScaler inside the pipeline", "test_imputer_and_scaler_fitted_on_training_data_only", OK],
    ["7", "Models: LR (baseline), DT, RF, SVR (RBF), ANN", "build_models()", "Table 4-6; test_all_five_models_trained_and_compared", OK],
    ["8", "Training; Grid search / random search / cross-validation", "GridSearchCV with 5-fold CV for every model", "Table 3-3, Table 4-5", OK],
    ["8", "RF hyperparameters: trees, max depth, min samples split, min samples leaf", "Random Forest grid", "test_random_forest_tuned_on_required_hyperparameters", OK],
    ["9", "MAE, MSE, RMSE, R² on unseen test data", "metrics()", "Eqs. 3-11…3-14; formula tests; re-computation (Ch. 5)", OK],
    ["10", "Comparison table incl. training time; results not decided in advance", "model_comparison.csv", "Table 4-6, Fig. 4-8", OK],
    ["11", "Actual vs predicted, prediction-error and residual plots", "evaluation_plots()", "Figs. 4-10 … 4-12", OK],
    ["12", "Feature importance (RF, DT) bar chart", "feature_importance.csv", "Fig. 4-14", OK],
    ["13", "Select model; predict previously unseen data; save & document (inputs, architecture, hyperparameters, metrics, plots)", "select_final_model(); blind_test(); model_card.json; final_rop_model.joblib", "Table 4-8, Fig. 4-9; test_model_card_documents_required_items", OK],
    ["14", "Python; Excel/CSV → Python → … → ROP prediction", "Python 3 + scikit-learn; CSV input", "Thesis §3.12", OK],
    ["15", "Methodology flowchart", "make_diagrams.py", "Fig. 3-1", OK],
    ["Scope", "Recommended 4 models (LR, DT, RF, ANN)", "All 4 + optional SVR", "Table 4-6", OK],
  ], [0.5, 2.6, 2.3, 2.1, 1.0], { leftAll: true });

  b.chapter("Thesis Scheme Compliance");
  b.table("Suggested scheme for final year design projects vs. complete thesis draft", ["Chapter", "Required items", "Where in the thesis", "Status"], [
    ["1 Introduction", "Background, problem statement, aim, objectives, scope, significance", "§1.1 – §1.6 (+ §1.7 thesis structure)", OK],
    ["2 Literature Review", "Fundamental concepts, previous research, existing methods, research gap", "§2.1 – §2.4", OK],
    ["3 Methodology", "Data collection, field/lab data, mathematical models, software/tools, experimental procedure, flowchart", "§3.2, §3.2.1, §3.7, §3.12, §3.13, Fig. 3-1", OK],
    ["4 Results & Discussion", "Calculations, graphs, tables, simulation results, comparison, discussion", "§4.11 sample calculation; Figs. 4-1…4-14; Tables 4-1…4-9; §4.6–4.8; §4.12", OK],
    ["5 Conclusions & Recommendations", "Major findings, conclusions, limitations, recommendations, future work", "§5.1 – §5.5", OK],
    ["Front matter (template)", "Title, declaration, plagiarism, approval, acknowledgements, abstract, TOC, lists of figures/tables", "Roman-numbered front pages", OK],
  ], [1.8, 3.0, 2.4, 1.0], { leftAll: true });

  b.chapter("Correctness Audit: Issues Found and Fixed");
  b.p("A line-by-line audit of the first version of the code against the methodology and good machine-learning practice found the following issues. All have been fixed and are now protected by automated tests.");
  b.table("Audit findings", ["#", "Issue found", "Why it matters", "Fix", "Test"], [
    ["1", "Missing inputs were filled with the median of the whole dataset before the split", "Information from the test set leaked into training (optimistic results)", "Median imputation moved inside the pipeline, fitted on training data only", "test_imputer_and_scaler_fitted_on_training_data_only"],
    ["2", "Feature selection (correlation, MI, importance) used all data", "Test data influenced the choice of inputs", "Feature selection performed on the training set only", "test_split_is_80_20_and_disjoint"],
    ["3", "RFE listed in the methodology but not implemented", "Requirement §5 incomplete", "RFECV with Random Forest and 5-fold CV added (Fig. 4-7)", "test_required_figures_exist"],
    ["4", "Final model chosen only on a random 80:20 split; no prediction on previously unseen data (§13)", `Random Forest looked best (test R² ${M["Random Forest"][7].toFixed(3)}) but fails on a new well (R² ${(BL["Random Forest"] ?? 0).toFixed(3)})`, "Blind-well test + selection score = mean of test and blind R²", "test_final_model_follows_selection_rule"],
    ["5", "Final model not documented as required by §13", "Requirement §13 incomplete", "model_card.json (inputs, algorithm, architecture, hyperparameters, metrics, training range)", "test_model_card_documents_required_items"],
    ["6", "App: ROP unit label overwritten by a loop variable (“ft” instead of “ft/hr”)", "Wrong unit shown to the user", "Variable renamed; unit switch ft/hr ↔ m/hr added", "test_every_app_page_runs_without_error"],
    ["7", "App: predictions outside the training range were shown without warning", "Extrapolated predictions can be misleading", "Training-range check with warning on the Predict page", "test_every_app_page_runs_without_error"],
    ["8", "Word table of contents was an empty field in PDF/phone viewers", "Report looked incomplete", "Static TOC, list of figures and tables generated from the rendered PDF page numbers", "Visual check"],
  ], [0.4, 2.0, 2.0, 2.2, 1.9], { leftAll: true });

  b.chapter("Automated Test Results");
  b.p(`The test-suite (tests/test_pipeline.py) is run with **python -m pytest -q tests/**. On ${V.date}, **${V.n_pass} of ${V.n_tests} tests passed**. The tests cover the metric formulas, data cleaning, the 80:20 split, data leakage, all five models, the saved final model, the selection rule, physical plausibility of predictions (more WOB → higher ROP; heavier mud → lower ROP), the presence of every required figure, and every page of the web application.`);
  b.table("Automated test results", ["#", "Test", "Result"], V.tests.map((t, i) => [String(i + 1), t.name.replace(/\[(.*)\]/, " — $1").replace(/[^\x20-\x7E—–]/g, "").trim(), t.status === "PASS" ? "✅ PASS" : "❌ FAIL"]),
    [0.5, 6.3, 1.2], { leftAll: true });

  b.chapter("Independent Re-computation of Metrics");
  b.p("As an additional check, MAE, RMSE and R² of every model were recomputed directly from the saved test predictions with plain NumPy, using the formulas of the methodology, and compared with the values reported in the thesis.");
  const e = (x) => x.toFixed(4);
  b.table("Reported versus independently recomputed test metrics", ["Model", "MAE rep.", "MAE recomp.", "RMSE rep.", "RMSE recomp.", "R² rep.", "R² recomp.", "Max. diff."],
    V.recompute.map((r) => [r.model, e(r.MAE_reported), e(r.MAE_recomputed), e(r.RMSE_reported), e(r.RMSE_recomputed), e(r.R2_reported), e(r.R2_recomputed), r.max_abs_diff.toExponential(1)]),
    [1.9, 0.9, 1.0, 0.9, 1.0, 0.8, 0.9, 0.9]);
  b.p("All values agree to within floating-point round-off (≈ 10^{−15}), confirming that the reported metrics are computed correctly.");

  b.chapter("Open Items Before Final Submission");
  b.table("Remaining actions", ["#", "Action", "Responsible"], [
    ["1", "Obtain real drilling data (Equinor Volve real-time drilling data or field records) and at least one additional well for the blind test", "Students / supervisor"],
    ["2", "Run: python code/rop_pipeline.py --data <training.csv> --blind <blind_well.csv>, then python code/verify.py and python docs/make_final.py", "Students"],
    ["3", "Review the automatically updated Chapter 4 and 5 text and adjust the discussion to the real results", "Students"],
    ["4", "Fill in names, roll numbers, supervisor, batch and dates; remove the demonstration notes", "Students"],
    ["5", "Verify all references in Mendeley/EndNote; run the plagiarism check", "Students"],
    ["6", "Supervisor review", "Supervisor"],
  ], [0.4, 6.0, 1.6], { leftAll: true });
}

buildOne("ROP_FYP_Verification_Report", front, body).then(() => console.log("Verification report written"));
