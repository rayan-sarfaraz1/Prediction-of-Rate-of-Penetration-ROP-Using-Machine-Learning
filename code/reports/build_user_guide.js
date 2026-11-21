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

  b.chapter("Introduction");
  b.h2("1.1 What is ROP·AI?");
  b.p("**ROP·AI** is the web-based front end of the final year project *Prediction of Rate of Penetration (ROP) Using Machine Learning*. It turns the trained machine-learning models into an easy-to-use tool: a drilling engineer moves sliders for the drilling parameters and immediately sees the predicted ROP, how ROP responds to each parameter, and which combination of WOB and RPM gives the highest predicted ROP. It also shows all the data analysis and model-comparison results of the project in an interactive form, which makes it ideal for the project presentation and viva.");
  b.h2("1.2 Main features");
  b.table("Features of ROP·AI", ["Page", "What it does"], [
    ["🏠 Overview", "Project summary, key numbers (records, features, best model, best R²), workflow steps and model leaderboard"],
    ["🎯 Predict ROP", "Live ROP prediction from 8 sliders with ± test-RMSE, gauge, time to drill 1,000 ft, training-range check, predictions of all 5 models, sensitivity curve"],
    ["⚙️ Optimizer", "Searches WOB × RPM combinations within limits and marks the setting with the highest predicted ROP"],
    ["📊 Data Explorer", "Interactive scatter plots, histograms, correlation heatmap, ROP–depth log and data table; accepts your own CSV"],
    ["📈 Model Results", "Comparison table (MAE, MSE, RMSE, R², CV RMSE, training time), actual-vs-predicted, residuals, feature importance, blind-well test and final model selection"],
    ["📁 Batch Prediction", "Upload a CSV of drilling data, get ROP predictions for every row, accuracy metrics and a downloadable result file"],
    ["📄 Reports", "Downloads of the thesis, proposal, user guide, verification report and SRS (Word + PDF), all figures, result tables, final model and model card; figure gallery"],
    ["ℹ️ About", "Aim, models, team, tech stack, inputs/outputs and the methodology flowchart"],
  ], [2, 6], { leftAll: true });
  b.h2("1.3 Inputs and output");
  b.table("Model inputs and output", ["Parameter", "Symbol / column", "Unit", "Slider range in app"], [
    ["Weight on bit", "WOB", "klbf", "5 – 45"], ["Rotary speed", "RPM", "rev/min", "40 – 200"], ["Torque", "Torque", "kft·lbf", "1 – 30"],
    ["Flow rate", "Q", "gpm", "300 – 1150"], ["Mud density", "MW (ρ)", "ppg", "8.8 – 14.0"], ["Standpipe pressure", "SPP", "psi", "700 – 5800"],
    ["Bit diameter", "Bit_Dia", "in", "8.5, 12.25, 17.5"], ["Depth", "Depth", "ft", "2,000 – 12,000"], ["Rate of penetration (output)", "ROP", "ft/hr", "—"],
  ], [2.4, 1.8, 1.2, 2]);

  b.chapter("System Architecture");
  b.p("The system has two parts. The **training pipeline** (code/rop_pipeline.py) reads the drilling CSV, cleans it, performs EDA and feature selection, trains and tunes the five models and saves the models, result tables and figures. The **web app** (app/streamlit_app.py) loads these saved files and lets the user interact with them. Because the app only reads saved files, retraining on new data automatically updates the app.");
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
    "(Only the first time, or after changing data) train the models:  **python code/rop_pipeline.py**",
    "Start the app:  **streamlit run app/streamlit_app.py**",
    "The browser opens automatically at **http://localhost:8501**. If not, open that address manually.",
    "To stop the app, press **Ctrl + C** in the terminal.",
    "(Optional) Verify everything with the automated tests:  **python -m pytest -q tests/**  — all tests should pass.",
  ]);
  b.note("Tip for the viva", "Start the app before the presentation and keep the browser tab open. Press F11 for full-screen mode. Everything runs offline on the laptop once the libraries are installed.");

  b.chapter("Using the Application");
  b.h2("4.1 Sidebar");
  b.p("The sidebar on the left contains the page menu and the **Prediction model** selector. By default the best model (highest test R²) is selected. Changing the model changes the predictions on the Predict, Optimizer and Batch pages. The card below it shows the selected model's test R² and RMSE. The **ROP units** switch shows all predicted ROP values in ft/hr or m/hr. The yellow notice reminds the user that the current models are trained on demonstration data.");
  b.h2("4.2 Overview page");
  b.figure(SS + "01_overview.png", "Overview page", 6.3);
  b.p(`The Overview page introduces the project. The four cards show the number of records used, the eight input features, the best model (${best}) and its test R² (${M[best][7].toFixed(3)}). The left column lists the eight steps of the methodology and the right column shows the model leaderboard, where the best model is highlighted in orange.`);
  b.h2("4.3 Predict ROP page");
  b.figure(SS + "02_predict.png", "Predict ROP page", 6.3);
  b.numbered(["Move the eight sliders to the drilling conditions you want to test (bit diameter has three positions: 8½, 12¼ and 17½ in).",
    "The large orange card shows the predicted ROP in ft/hr and m/hr; the gauge shows it on a 0–150 ft/hr scale.",
    "The card below estimates the on-bottom time needed to drill 1,000 ft at this ROP.",
    "“What do all five models say?” compares the predictions of all models for the same input — useful to explain model differences in the viva.",
    "In “Sensitivity”, choose a parameter (e.g. WOB); the curve shows how predicted ROP changes when only that parameter changes, the green band marks the training range and the orange dot marks the current setting."]);
  b.p("**Training-range check.** Machine-learning models are only reliable inside the range of the data they were trained on. Below the prediction, a green message confirms that all inputs are inside the training range. If any input is outside it, a yellow warning lists the parameter and its training range, as shown below — the prediction is then an extrapolation and must be treated with caution.");
  b.figure(SS + "02b_range_warning.png", "Training-range warning when WOB is set above the range of the training data", 6.3);
  b.h2("4.4 Optimizer page");
  b.figure(SS + "03_optimizer.png", "Drilling parameter optimizer", 6.3);
  b.p("The optimizer fixes depth, mud density, flow rate, bit diameter and SPP at the chosen values and evaluates the model on a 40 × 40 grid of WOB and RPM values up to the maximum allowable limits. Torque is estimated from WOB using the Torque/WOB ratio. The contour map shows predicted ROP (blue = slow, orange = fast) and the white star marks the optimum. The optimum WOB, RPM and the maximum predicted ROP are shown on the right. The result is a data-driven recommendation and must always be checked against bit ratings, vibration, hole cleaning and torque limits.");
  b.h2("4.5 Data Explorer page");
  b.figure(SS + "04_data_explorer.png", "Data Explorer page", 6.3);
  b.p("The Data Explorer shows the cleaned project data, or any CSV that you upload with the same columns. The tabs provide: **Scatter vs ROP** (coloured by hole size, with Pearson r), **Distributions** (histogram and descriptive statistics), **Correlation** (interactive heatmap), **Depth log** (ROP against depth) and **Table** (first 500 rows). All charts can be zoomed by dragging and reset by double-clicking.");
  b.h2("4.6 Model Results page");
  b.figure(SS + "05_model_results.png", "Model Results page", 6.3);
  b.p("The table compares all five models on the unseen test set; the best R² and RMSE are highlighted. The tabs show actual-vs-predicted scatter with the 1:1 line, residual plot and error histogram, bar charts of R², RMSE and MAE, and the feature importance of the Random Forest and Decision Tree models.");
  b.p(`The last tab, **Blind well & final selection**, shows how every model performed on a completely separate well that was never used for training. It explains why the final model is the ${best}: Random Forest has the highest test R² (${M["Random Forest"][7].toFixed(3)}) but drops to ${(BLD["Random Forest"] ?? 0).toFixed(3)} on the new well, while the ${best} keeps ${(BLD[best] ?? 0).toFixed(3)}. The selection score is the mean of the test and blind-well R².`);
  b.figure(SS + "05b_blind_well.png", "Blind-well test and final model selection", 6.3);
  b.h2("4.7 Batch Prediction page");
  b.figure(SS + "06_batch.png", "Batch Prediction page", 6.3);
  b.numbered(["Click **Download CSV template** to get a file with the correct column names.",
    "Fill it with your drilling data (one row per depth/time step) and upload it. Alternatively, tick “use the demo test set”.",
    "The app predicts ROP for every row. If the file also contains a measured ROP column, MAE, RMSE and R² are calculated and actual and predicted ROP are plotted against depth.",
    "Click **Download predictions** to save the results as CSV (opens in Excel)."]);
  b.h2("4.8 Reports page");
  b.figure(SS + "08_reports.png", "Reports & Downloads page", 6.3);
  b.p("The Reports page collects every deliverable: the thesis, proposal, user guide, verification report and SRS (Word and PDF), a ZIP of all figures, a ZIP of all result tables, the final trained model (.joblib) and its model card (.json). The model card shows the algorithm, pipeline, hyperparameters, ANN architecture, inputs and output, test and blind-well metrics and the training range of every input. A figure gallery at the bottom lets you browse all graphs and diagrams for the presentation.");
  b.h2("4.9 About page");
  b.figure(SS + "07_about.png", "About page", 6.3);
  b.p("The About page summarizes the aim, models, team, technology stack, inputs and output, and contains the methodology flowchart. Replace the placeholders [Supervisor Name] and [Student 1–4] in app/streamlit_app.py with your real names.");

  b.chapter("Using Real Field Data");
  b.p("The app currently runs in **demo mode** with models trained on a synthetic dataset. To switch to real data:");
  b.numbered([
    "Export the drilling data (e.g. Volve real-time drilling data or field records) to CSV.",
    "Rename the columns exactly to: Depth, WOB, RPM, Torque, Q, MW, SPP, Bit_Dia, ROP and convert units to ft, klbf, rev/min, kft·lbf, gpm, ppg, psi, in and ft/hr.",
    "Save the file in the data folder, e.g. data/volve_well1.csv.",
    "Run:  **python code/rop_pipeline.py --data data/volve_well1.csv**  (takes 1–3 minutes).",
    "Restart the app. All pages now show the real-data results. Remove the demo notice from the sidebar in app/streamlit_app.py.",
    "Rebuild the thesis with the new results:  **python code/export_doc_data.py**  then  **python code/reports/make_final.py**.",
  ]);
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
    ["0:00", "Overview", "Problem: ROP controls drilling cost. Our solution: ML predicts ROP from 8 surface parameters. Show the leaderboard."],
    ["0:45", "Data Explorer", "Show ROP vs WOB and ROP vs depth; explain cleaning and correlations."],
    ["1:45", "Model Results", `Compare models: baseline LR (R² ${M["Linear Regression"][7].toFixed(2)}) vs ${best} (R² ${M[best][7].toFixed(2)}); show actual-vs-predicted and feature importance.`],
    ["2:45", "Predict ROP", "Increase WOB and RPM live — ROP rises; increase mud density or depth — ROP falls (agrees with drilling theory)."],
    ["3:45", "Optimizer", "Show how the model recommends the best WOB/RPM within limits — the practical value for the drilling engineer."],
    ["4:30", "Batch", "Upload a CSV and download predictions — shows the tool is usable on new wells."],
  ], [0.8, 1.5, 5.7], { leftAll: true });

  b.chapter("Troubleshooting");
  b.table("Common problems and solutions", ["Problem", "Solution"], [
    ["‘python’ or ‘pip’ is not recognized", "Reinstall Python and tick “Add Python to PATH”, or use py -m pip install -r requirements.txt"],
    ["‘streamlit’ is not recognized", "Run python -m streamlit run app/streamlit_app.py"],
    ["“Model/result files not found”", "Run python code/rop_pipeline.py first to create the models and results"],
    ["CSV upload error: missing columns", "Rename the CSV columns exactly as in the template (case-sensitive)"],
    ["Predictions look unrealistic", "Check units; keep inputs within the range of the training data (models do not extrapolate well)"],
    ["Port 8501 already in use", "Run streamlit run app/streamlit_app.py --server.port 8502"],
  ], [3, 5], { leftAll: true });

  b.chapter("FYP Completion Checklist");
  b.table("Remaining tasks to complete the FYP", ["#", "Task", "Status"], [
    ["1", "Methodology, proposal (Ch. 1–3) and complete thesis draft (Ch. 1–5)", "✅ Done (draft)"],
    ["2", "Python pipeline: cleaning, EDA, 5 models, tuning, evaluation, plots", "✅ Done"],
    ["3", "ROP·AI web app and this user guide", "✅ Done"],
    ["3a", "Leakage-free pipeline, RFE, blind-well test, model card and 44 automated tests", "✅ Done (all tests pass)"],
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
