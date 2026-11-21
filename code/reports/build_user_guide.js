/*
 * Builds documents/ROP_AI_App_User_Guide.docx — guide to the ROP·AI web application.
 * Usage: node code/reports/build_user_guide.js   (run after app screenshots exist in documents/screenshots)
 */
const fs = require("fs");
const path = require("path");
const { AlignmentType, ImageRun, Paragraph } = require("docx");
const { Builder, buildOne, tocPages, TITLE, SUPERVISOR, MEMBERS, BATCH, D } = require("./build_thesis");

const SS = "../documents/screenshots/";
const best = D.summary.best_model;
const M = Object.fromEntries(D.models.map((r) => [r[0], r]));

function front(b, toc) {
  b.center("ROP·AI", { size: 56, bold: true, before: 900, after: 120, color: "EB6834" });
  b.center("Web Application for Rate of Penetration Prediction", { size: 30, bold: true, after: 120 });
  b.center("USER GUIDE & TECHNICAL DOCUMENTATION", { size: 24, after: 500 });
  b.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new ImageRun({ type: "png",
    data: fs.readFileSync(path.join(__dirname, "assets", "buitems_logo.png")), transformation: { width: 130, height: 130 },
    altText: { title: "BUITEMS logo", description: "BUITEMS logo", name: "logo" } })] }));
  b.center(`Final Year Project: ${TITLE}`, { bold: true, after: 300 });
  b.center("Department of Petroleum & Gas Engineering, BUITEMS", { after: 60 });
  b.center(BATCH, { after: 300 });
  b.center(`Supervisor: ${SUPERVISOR}`, { after: 120 });
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  tocPages(b, toc, false);
}

function body(b) {
  const BLD = Object.fromEntries((D.blind || []).map((r) => [r[0], r[4]]));
  const N_TESTS = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "results", "verification.json"), "utf8")).n_tests;

  b.chapter("Introduction");
  b.h2("1.1 What is ROP·AI?");
  b.p("**ROP·AI** is the web-based front end of the final year project *Prediction of Rate of Penetration (ROP) Using Machine Learning*. It is a guided **prediction studio**: when it opens it asks for a drilling dataset, recognises the columns and units, pre-processes and cleans the data, explores it, trains and tunes five machine-learning models, selects the best one using a test set and a blind well, and then lets the user predict ROP, optimize WOB and RPM and run batch predictions — all inside the browser, without writing any code. This makes it ideal for the project presentation and viva.");
  b.h2("1.2 Guided workflow and main features");
  b.table("Workflow steps and pages of ROP·AI", ["Step / page", "What it does"], [
    ["1 · Load dataset", "Upload a CSV or Excel file (plus an optional blind well), or use the demo dataset or the saved project model. Columns and units are detected automatically and converted to oilfield units"],
    ["2 · Pre-process & clean", "Removes duplicates, flags physically impossible values, drops missing ROP, removes ROP outliers (k×IQR, adjustable) and splits 80 : 20; shows a cleaning funnel, data-quality chart and before/after box plots"],
    ["3 · Explore data", "ROP vs each parameter, distributions, correlation heatmap, ROP–depth log, feature selection (Pearson r, mutual information, RF importance, optional RFECV)"],
    ["4 · Train models", "Linear Regression, Decision Tree, Random Forest, SVR and ANN with grid search + 5-fold CV (fast or full thesis grid), live progress, blind-well test"],
    ["5 · Results & selection", "Leaderboard (test and blind-well metrics, selection score), actual vs predicted, residuals, feature importance, hyperparameters; save as project model"],
    ["🎯 Predict ROP", "Live prediction from 8 sliders with ± test RMSE, gauge, time to drill 1,000 ft, training-range check, all five models, sensitivity curve"],
    ["⚙️ Optimizer", "WOB × RPM contour map within limits with the optimum setting for maximum predicted ROP"],
    ["📁 Batch prediction", "Upload any drilling file (same automatic column mapping), predict ROP for every row, accuracy if ROP is present, download results"],
    ["ℹ️ About", "Aim, workflow, team, tech stack and methodology flowchart"],
  ], [2.1, 5.9], { leftAll: true });
  b.h2("1.3 Inputs and output");
  b.table("Model inputs and output", ["Parameter", "Symbol / column", "Unit", "Slider range in app"], [
    ["Weight on bit", "WOB", "klbf", "5 – 45"], ["Rotary speed", "RPM", "rev/min", "40 – 200"], ["Torque", "Torque", "kft·lbf", "1 – 30"],
    ["Flow rate", "Q", "gpm", "300 – 1150"], ["Mud density", "MW (ρ)", "ppg", "8.8 – 14.0"], ["Standpipe pressure", "SPP", "psi", "700 – 5800"],
    ["Bit diameter", "Bit_Dia", "in", "8.5, 12.25, 17.5"], ["Depth", "Depth", "ft", "2,000 – 12,000"], ["Rate of penetration (output)", "ROP", "ft/hr", "—"],
  ], [2.4, 1.8, 1.2, 2]);

  b.chapter("System Architecture");
  b.p("The system has two parts. The **training pipeline** (code/rop_pipeline.py) reads the drilling CSV, cleans it, performs EDA and feature selection, trains and tunes the five models and saves the models, result tables and figures. The **web app** (app/streamlit_app.py) runs the same pipeline functions interactively: data loaded in the browser is mapped, cleaned, explored and used to train the models inside the app (module code/data_io.py handles column recognition and unit conversion). A trained model can be saved as the *project model* and opened again later. The command-line pipeline is used to produce the thesis figures and tables.");
  b.figure("diagram_app_architecture.png", "Architecture of the ROP·AI system", 6.2);
  b.table("Technology stack", ["Layer", "Technology", "Why"], [
    ["Language", "Python 3.11+", "Standard for data science; free; huge community"],
    ["Machine learning", "scikit-learn", "LR, DT, RF, SVR, MLP, GridSearchCV and metrics in one library"],
    ["Data handling", "pandas, NumPy", "Reading CSV/Excel, cleaning and calculations"],
    ["Web front end", "Streamlit", "Builds a web app in pure Python — no HTML/JavaScript needed"],
    ["Interactive charts", "Plotly", "Zoom, hover and pan on every chart"],
    ["Static figures", "Matplotlib, Seaborn", "High-resolution figures for the thesis"],
    ["Model storage", "joblib", "Saves and loads trained models"],
    ["Hosting (optional)", "Streamlit Community Cloud", "Free public link from the GitHub repository"],
  ], [1.8, 2.2, 4], { leftAll: true });
  b.table("Project folder structure", ["Path", "Content"], [
    ["app/streamlit_app.py", "The ROP·AI web application"], [".streamlit/config.toml", "Dark theme and server settings"],
    ["code/rop_pipeline.py", "Training pipeline (cleaning → models → results)"], ["code/generate_synthetic_data.py", "Demo dataset generator (testing only)"],
    ["code/make_diagrams.py, code/export_doc_data.py", "Diagrams and data for the documents"], ["data/", "Raw and cleaned CSV data"],
    ["models/all_models.joblib", "All five trained models"], ["models/final_rop_model.joblib", "Best (final) model"],
    ["results/", "Result tables (CSV/JSON)"], ["figures/", "Graphs and diagrams (PNG)"], ["documents/", "Thesis, proposal, user guide, verification report (Word + PDF), screenshots, reference files"], ["code/reports/", "Scripts that build all documents"],
  ], [3.2, 4.8], { leftAll: true });

  b.chapter("Installation and Running");
  b.h2("3.1 Requirements");
  b.bullets(["Windows 10/11, macOS or Linux; 4 GB RAM or more.", "Python 3.11 or newer (from python.org — tick “Add Python to PATH” during installation).",
    "VS Code (recommended) or any terminal.", "Internet connection only for the first installation of libraries."]);
  b.h2("3.2 Step-by-step installation");
  b.numbered([
    "Download the project from GitHub (Code → Download ZIP) and extract it, or clone it with Git.",
    "Open a terminal (Command Prompt / PowerShell / VS Code terminal) in the project folder.",
    "Install the libraries:  **pip install -r requirements.txt**",
    "Start the app:  **streamlit run app/streamlit_app.py**",
    "The browser opens automatically at **http://localhost:8501**. If not, open that address manually.",
    "To stop the app, press **Ctrl + C** in the terminal.",
    "(Optional) Verify everything with the automated tests:  **python -m pytest -q tests/**  — all tests should pass.",
  ]);
  b.note("Tip for the viva", "Start the app before the presentation and keep the browser tab open. Press F11 for full-screen mode. Everything runs offline on the laptop once the libraries are installed.");

  b.chapter("Using the Application");
  b.h2("4.1 Navigation");
  b.p("The sidebar shows the five workflow steps, a progress bar and the ‘Use the model’ pages. Steps unlock one after the other: cleaning is available after a dataset is loaded, exploration and training after cleaning, and results and the prediction pages after training. Completed steps are marked with ✓. Once a model exists, the sidebar shows the active model and a switch for ROP units (ft/hr or m/hr).");
  b.h2("4.2 Step 1 — Load dataset");
  b.figure(SS + "01_load_data.png", "Step 1: the app opens by asking for a drilling dataset", 6.3);
  b.p("When the application opens, it asks for data. There are three ways to start:");
  b.bullets(["**Upload your dataset** — drag a CSV or Excel file into ‘Training data’. Optionally upload a second, separate well into ‘Blind well’ for the final generalization test.",
    "**Use demo dataset** — loads the 3,040-row synthetic dataset and its 800-row blind well (for learning and testing).",
    "**Open saved project** — opens the last model saved with ‘Save as project model’ and goes straight to the results."]);
  b.figure(SS + "02_column_mapping.png", "Automatic column and unit mapping for a file with metric, Volve-style headers", 6.3);
  b.p("After an upload, ROP·AI shows the number of rows, columns and missing cells and then the **column mapping**. For every required field it selects the matching column and its unit automatically from the header names (for example ‘Weight on Bit (kkgf)’ → WOB in tonnes, ‘Rate of Penetration (m/h)’ → ROP in m/hr). Check the selections, correct them if needed, and enter a constant bit diameter if the file has no bit-size column. Click **Confirm data & continue to cleaning**; all values are converted to oilfield units.");
  b.h2("4.3 Step 2 — Pre-process & clean");
  b.figure(SS + "03_clean.png", "Step 2: pre-processing and cleaning results", 6.3);
  b.p("Choose the ROP outlier factor k (default 3) and click **Run pre-processing & cleaning**. The app removes duplicates, sets physically impossible values to missing, drops rows without ROP, removes ROP spikes with the k×IQR rule and splits the data 80 : 20. The cards and tabs show the records kept, the cleaning funnel, missing/unrealistic values per column, ROP before and after cleaning and the cleaned table (downloadable as CSV).");
  b.h2("4.4 Step 3 — Explore data");
  b.figure(SS + "04_explore.png", "Step 3: exploratory data analysis", 6.3);
  b.p("The tabs show ROP against each parameter (coloured by hole size, with Pearson r), histograms with descriptive statistics, the correlation heatmap, the ROP–depth log and the feature-selection results calculated on the training set. Recursive feature elimination can be run with one click.");
  b.h2("4.5 Step 4 — Train models");
  b.figure(SS + "05_train.png", "Step 4: training and tuning the models", 6.3);
  b.p("Select the models and the search mode — **Fast** (smaller grids, about 20–40 s) or **Full thesis grid** (the grids of the methodology, about 2 minutes) — and click **Train models**. A progress bar and a live log show the test R² and RMSE of every model. If a blind well was uploaded, all models are also tested on it and the final model is selected automatically.");
  b.h2("4.6 Step 5 — Results & selection");
  b.figure(SS + "06_results.png", "Step 5: model comparison and final selection", 6.3);
  b.p(`The leaderboard lists test metrics, cross-validation RMSE, training time, blind-well R² and RMSE and the selection score (mean of test and blind-well R²); the final model is highlighted. In the demonstration the ${best} is selected: Random Forest reaches a similar test R² but drops to about ${(BLD["Random Forest"] ?? 0).toFixed(2)} on the blind well. Further tabs show actual vs predicted, residuals and errors, feature importance and the optimum hyperparameters. **Save as project model** stores the models and results so that the next session can start with ‘Open saved project’.`);
  b.h2("4.7 Predict ROP");
  b.figure(SS + "07_predict.png", "Predict ROP page", 6.3);
  b.numbered(["Choose the model (the final model is selected by default) and move the eight sliders.",
    "The result card shows the predicted ROP with its test RMSE; the gauge and the time to drill 1,000 ft are updated instantly.",
    "A green message confirms that all inputs are inside the training range; a yellow warning lists any input outside it (the prediction is then an extrapolation).",
    "‘All models’ compares the five models; ‘Sensitivity’ shows how ROP changes with one parameter, with the training range shaded."]);
  b.h2("4.8 Optimizer");
  b.figure(SS + "08_optimizer.png", "Drilling-parameter optimizer", 6.3);
  b.p("Set depth, mud density, flow rate, bit size and SPP and the maximum allowable WOB and RPM. The model is evaluated on a 40 × 40 grid; the contour map shows predicted ROP and the star marks the optimum WOB and RPM. This is a data-driven recommendation — always check bit ratings, vibration, hole cleaning and torque limits.");
  b.h2("4.9 Batch prediction");
  b.figure(SS + "09_batch.png", "Batch prediction for an uploaded file with metric units", 6.3);
  b.p("Upload any drilling file; the same automatic column and unit mapping is used (measured ROP is optional). ROP is predicted for every row and added as the first column. If measured ROP is present, MAE, RMSE and R² are calculated and measured and predicted ROP are plotted against depth. Click **Download predictions** to save the results as CSV.");
  b.h2("4.10 About");
  b.figure(SS + "10_about.png", "About page", 6.3);
  b.p("Aim, workflow, team, technology stack and the methodology flowchart. Replace the placeholders [Supervisor Name] and [Student 1–4] in app/streamlit_app.py with your names.");

  b.chapter("Using Real Field Data");
  b.h2("5.1 Where to put the data");
  b.p("No code changes and no renaming are needed. Real field data can be used in two ways:");
  b.bullets(["**In the app (recommended):** start the app and upload the file in Step 1. Columns and units are mapped automatically; then follow Steps 2–5 and click **Save as project model**.",
    "**From the command line (for the thesis figures):** copy the file into the **data/** folder, rename the columns to Depth, WOB, RPM, Torque, Q, MW, SPP, Bit_Dia and ROP in oilfield units, and run  **python code/rop_pipeline.py --data data/well1.csv --blind data/well2.csv**, then  **python code/export_doc_data.py**, **python code/verify.py** and  **python code/reports/make_final.py**."]);
  b.h2("5.2 Recommended data");
  b.bullets(["At least two wells: one (or more) for training and a separate one as the blind well.",
    "Real-time drilling data with WOB, RPM, torque, flow rate, standpipe pressure, mud density, bit depth and ROP — for example the Equinor Volve dataset.",
    "One row per depth or time step; the file can be CSV (comma or semicolon separated) or Excel."]);
  b.p("The project includes data/example_metric_format.csv, a file with Volve-style metric headers, to try the automatic mapping. The app converts the following units automatically:");
  b.table("Common unit conversions", ["From", "To", "Multiply by"], [
    ["m/hr", "ft/hr", "3.281"], ["m", "ft", "3.281"], ["tonnes (t)", "klbf", "2.2046"], ["kN", "klbf", "0.2248"],
    ["kN·m", "kft·lbf", "0.7376"], ["L/min", "gpm", "0.2642"], ["m³/s", "gpm", "15,850"], ["g/cm³ (SG)", "ppg", "8.345"],
    ["bar", "psi", "14.504"], ["kPa", "psi", "0.1450"], ["mm", "in", "0.03937"],
  ], [2.5, 2.5, 2.5]);

  b.chapter("Online Deployment (Optional)");
  b.p("The app can be published on the internet for free with Streamlit Community Cloud, so that the supervisor and examiners can open it from a link:");
  b.numbered(["Push the complete project (including the models folder) to a GitHub repository.",
    "Go to share.streamlit.io and sign in with GitHub.",
    "Click **Create app**, select the repository and branch, and set the main file path to app/streamlit_app.py.",
    "Click **Deploy**. After a few minutes the app is available at a public link that can be shared and added to the thesis and slides."]);

  b.chapter("Viva Demonstration Script");
  b.p("A suggested 5-minute live demonstration:");
  b.table("Suggested live demo flow", ["Time", "Page", "What to show and say"], [
    ["0:00", "1 · Load", "Problem: ROP controls drilling cost. Upload the field file — show the automatic column and unit mapping."],
    ["0:45", "2 · Clean", "Run cleaning — explain duplicates, physical limits, outliers (funnel and before/after box plot)."],
    ["1:30", "3 · Explore", "Show ROP vs WOB and ROP vs depth, the correlation heatmap and feature relevance."],
    ["2:15", "4–5 · Train & results", `Train (fast mode) live; compare baseline LR (R² ${M["Linear Regression"][7].toFixed(2)}) with ${best} (R² ${M[best][7].toFixed(2)}) and explain the blind-well selection.`],
    ["2:45", "Predict ROP", "Increase WOB and RPM live — ROP rises; increase mud density or depth — ROP falls (agrees with drilling theory)."],
    ["3:45", "Optimizer", "Show how the model recommends the best WOB/RPM within limits — the practical value for the drilling engineer."],
    ["4:30", "Batch", "Upload a CSV and download predictions — shows the tool is usable on new wells."],
  ], [0.8, 1.5, 5.7], { leftAll: true });

  b.chapter("Troubleshooting");
  b.table("Common problems and solutions", ["Problem", "Solution"], [
    ["‘python’ or ‘pip’ is not recognized", "Reinstall Python and tick “Add Python to PATH”, or use py -m pip install -r requirements.txt"],
    ["‘streamlit’ is not recognized", "Run python -m streamlit run app/streamlit_app.py"],
    ["‘Open saved project’ is not shown", "No project model has been saved yet — load data, train, then click Save as project model"],
    ["A field shows ‘required’ in the column mapping", "Select the matching column of your file, or enter a constant (bit diameter)"],
    ["Strange values after upload", "Check the unit chosen for each column in the mapping step"],
    ["Predictions look unrealistic", "Check units; keep inputs within the range of the training data (models do not extrapolate well)"],
    ["Port 8501 already in use", "Run streamlit run app/streamlit_app.py --server.port 8502"],
  ], [3, 5], { leftAll: true });

  b.chapter("FYP Completion Checklist");
  b.table("Remaining tasks to complete the FYP", ["#", "Task", "Status"], [
    ["1", "Methodology, proposal (Ch. 1–3) and complete thesis draft (Ch. 1–5)", "✅ Done (draft)"],
    ["2", "Python pipeline: cleaning, EDA, 5 models, tuning, evaluation, plots", "✅ Done"],
    ["3", "ROP·AI web app and this user guide", "✅ Done"],
    ["3a", `Leakage-free pipeline, RFE, blind-well test, model card and ${N_TESTS} automated tests`, "✅ Done (all tests pass)"],
    ["3b", "Requirements & verification report", "✅ Done"],
    ["4", "Obtain real drilling data (Volve or field) and convert to CSV", "⏳ Pending"],
    ["5", "Re-run pipeline on real data; update Chapter 4 and 5 numbers and discussion", "⏳ Pending"],
    ["6", "Fill names, roll numbers, supervisor and dates; update Word fields (TOC)", "⏳ Pending"],
    ["7", "Verify references in Mendeley/EndNote; plagiarism check", "⏳ Pending"],
    ["8", "Supervisor review and corrections", "⏳ Pending"],
    ["9", "Presentation slides and viva rehearsal with the live app", "⏳ Pending"],
    ["10", "(Optional) Deploy the app online on Streamlit Community Cloud", "⏳ Optional"],
  ], [0.5, 5.8, 1.7], { leftAll: true });
  return b.out;
}

buildOne("ROP_AI_App_User_Guide", front, body).then(() => console.log("User guide written"));
