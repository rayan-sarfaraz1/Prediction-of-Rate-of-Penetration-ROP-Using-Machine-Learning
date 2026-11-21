/*
 * Builds documents/ROP_AI_SRS.docx — Software Requirements Specification (IEEE 830 / ISO/IEC/IEEE 29148 structure)
 * for the ROP·AI system (ML pipeline + web application + report generator).
 * Usage: node code/reports/build_srs.js   (normally run through code/reports/make_final.py)
 */
const fs = require("fs");
const path = require("path");
const { AlignmentType, ImageRun, Paragraph } = require("docx");
const { Builder, buildOne, tocPages, TITLE, SUPERVISOR, MEMBERS, BATCH, D } = require("./build_thesis");

const SS = "../documents/screenshots/";
const M = Object.fromEntries(D.models.map((r) => [r[0], r]));
const best = D.summary.best_model;
const H = "High", MED = "Medium", L = "Low";

function front(b, toc) {
  b.center("SOFTWARE REQUIREMENTS SPECIFICATION", { size: 34, bold: true, before: 800, after: 160, color: "EB6834" });
  b.center("ROP·AI — Rate of Penetration Prediction System", { size: 28, bold: true, after: 120 });
  b.center(`Final Year Project: ${TITLE}`, { size: 22, after: 400 });
  b.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new ImageRun({ type: "png",
    data: fs.readFileSync(path.join(__dirname, "assets", "buitems_logo.png")), transformation: { width: 130, height: 130 },
    altText: { title: "BUITEMS logo", description: "BUITEMS logo", name: "logo" } })] }));
  b.center("Prepared according to IEEE Std 830-1998 / ISO/IEC/IEEE 29148:2018", { size: 22, after: 300 });
  b.center("Department of Petroleum & Gas Engineering, BUITEMS", { after: 60 });
  b.center(BATCH, { after: 300 });
  b.center(`Supervisor: ${SUPERVISOR}`, { after: 120 });
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  b.unnumbered("REVISION HISTORY", true, false);
  b.table("Revision history", ["Version", "Date", "Description", "Author"], [
    ["1.0", "[DD/MM/YYYY]", "Initial SRS covering the ML pipeline, ROP·AI web application, report generator and verification suite", "FYP group"],
    ["", "", "", ""],
  ], [1, 1.5, 4.5, 1.5], { label: "Table i" });
  tocPages(b, toc, false);
}

function body(b) {
  // ------------------------------------------------------------------ 1
  b.chapter("Introduction");
  b.h2("1.1 Purpose");
  b.p("This Software Requirements Specification (SRS) defines the functional and non-functional requirements of **ROP·AI**, the software developed in the final year project *Prediction of Rate of Penetration (ROP) Using Machine Learning*. It is intended for the project supervisor and examiners (to evaluate what the software does and how it is verified), for the project group (as the reference for development, testing and the thesis), and for future students or engineers who extend the system.");
  b.h2("1.2 Scope");
  b.p("ROP·AI predicts the drilling rate of penetration (ft/hr) from eight surface drilling parameters. The product consists of four parts:");
  b.numbered(["**ML pipeline** — cleans historical drilling data, performs exploratory data analysis and feature selection, trains and tunes five regression models, evaluates them on a test set and a blind well, selects and saves the final model.",
    "**ROP·AI web application** — an interactive browser application for single-point prediction, drilling-parameter optimization, data exploration, model results, batch prediction and downloads.",
    "**Report generator** — builds the thesis, proposal, user guide, verification report and this SRS in Word and PDF format from the latest results.",
    "**Verification suite** — automated tests that check formulas, data handling, models and every page of the application."]);
  b.p("The software is a decision-support and academic tool. It does **not** control drilling equipment, is not connected to rig systems in real time and does not replace engineering judgement.");
  b.h2("1.3 Definitions, Acronyms and Abbreviations");
  b.table("Definitions and abbreviations", ["Term", "Definition"], [
    ["ROP", "Rate of penetration — drilled depth per unit time (ft/hr)"], ["WOB", "Weight on bit (klbf)"], ["RPM", "Rotary speed (rev/min)"],
    ["T", "Surface torque (kft·lbf)"], ["Q", "Mud flow rate (gpm)"], ["ρ, MW", "Mud density / mud weight (ppg)"], ["SPP", "Standpipe pressure (psi)"],
    ["D, Bit_Dia", "Bit diameter (in)"], ["ML", "Machine learning"], ["LR, DT, RF, SVR, ANN", "Linear regression, decision tree, random forest, support vector regression, artificial neural network"],
    ["MAE, MSE, RMSE, R²", "Mean absolute error, mean squared error, root mean squared error, coefficient of determination"],
    ["CV, RFECV", "Cross-validation; recursive feature elimination with cross-validation"],
    ["Blind well", "A complete well that is never used for training, tuning or feature selection; used to test generalization"],
    ["Model card", "Machine-readable documentation of the final model (inputs, algorithm, hyperparameters, metrics, training range)"],
    ["Training range", "Minimum and maximum of each input in the training set; predictions outside it are extrapolations"],
    ["FR / NFR", "Functional requirement / non-functional requirement"], ["UC", "Use case"],
  ], [2.2, 5.8], { leftAll: true });
  b.h2("1.4 References");
  b.numbered(["IEEE Std 830-1998, *IEEE Recommended Practice for Software Requirements Specifications*.",
    "ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*.",
    "Supervisor's methodology document: *Prediction of Rate of Penetration (ROP) Using Machine Learning — Methodology* (documents/reference/Supervisor_Methodology_ROP_ML.pdf).",
    "Project thesis draft, user guide and verification report (documents/ folder).",
    "F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011."]);
  b.h2("1.5 Overview of this Document");
  b.p("Chapter 2 gives the overall description of the product. Chapter 3 specifies external interfaces. Chapter 4 lists the functional requirements by feature, Chapter 5 the non-functional requirements and Chapter 6 the data requirements. Chapter 7 describes the use cases and Chapter 8 the verification of every requirement (acceptance criteria and traceability to tests).");

  // ------------------------------------------------------------------ 2
  b.chapter("Overall Description");
  b.h2("2.1 Product Perspective");
  const fA = b.nextFig();
  b.p(`ROP·AI is a self-contained, locally installed Python system (${fA}). The ML pipeline reads drilling data from CSV files and writes trained models, result tables and figures to the project folders. The web application and the report generator only read these saved artefacts, so retraining on new data automatically updates the application and all documents.`);
  b.figure("diagram_app_architecture.png", "System architecture of ROP·AI", 6.0);
  const fD = b.nextFig();
  b.p(`${fD} shows the data flow between the processes and data stores.`);
  b.figure("diagram_dfd.png", "Data flow diagram (level 1)", 6.2);
  b.h2("2.2 Product Functions");
  b.bullets(["Import and validate drilling data; clean duplicates, missing, unrealistic and outlier values.",
    "Produce exploratory graphs and feature-relevance statistics.",
    "Train, tune (grid search + 5-fold CV) and evaluate five regression models.",
    "Test all models on a blind well and select the final model automatically.",
    "Save the final model with a model card.",
    "Predict ROP for one set of parameters or for a whole CSV file, with a training-range check.",
    "Recommend the WOB–RPM combination giving the highest predicted ROP.",
    "Display all results interactively and provide downloads of reports, figures, tables and the model.",
    "Generate all project documents in Word and PDF, and verify the system with automated tests."]);
  b.h2("2.3 User Classes and Characteristics");
  b.table("User classes", ["User class", "Description", "Main functions used", "Technical skill"], [
    ["Drilling engineer / end user", "Uses the trained model to estimate ROP and choose drilling parameters", "Predict, Optimizer, Batch prediction", "Basic computer skills"],
    ["Student / researcher (FYP group)", "Runs the pipeline on new data, maintains code and documents", "Pipeline, report generator, tests", "Python basics"],
    ["Supervisor / examiner", "Evaluates the project, methodology and results", "Overview, Model results, Reports, Verification report", "Basic computer skills"],
  ], [2, 2.6, 2.2, 1.4], { leftAll: true });
  b.h2("2.4 Operating Environment");
  b.table("Operating environment", ["Item", "Requirement"], [
    ["Operating system", "Windows 10/11, macOS or Linux (64-bit)"], ["Hardware (minimum)", "Dual-core CPU, 4 GB RAM, 1 GB free disk space"],
    ["Python", "3.11 or newer with packages from requirements.txt (pandas, NumPy, scikit-learn, Matplotlib, Seaborn, joblib, Streamlit, Plotly)"],
    ["Browser", "Any current Chrome, Edge, Firefox or Safari"],
    ["Report generator (optional)", "Node.js with the ‘docx’ package, LibreOffice and poppler (pdftotext)"],
    ["Network", "Not required after installation (the application runs on localhost)"],
  ], [2.2, 5.8], { leftAll: true });
  b.h2("2.5 Design and Implementation Constraints");
  b.bullets(["The methodology prescribed by the supervisor must be followed: 80:20 split, the listed models and metrics, grid search with cross-validation.",
    "Only open-source software may be used (no paid licences).",
    "The thesis documents must follow the BUITEMS P&G thesis template and the suggested five-chapter scheme.",
    "Input data must be in CSV format with the column names and units of Chapter 6.",
    "Results must be reproducible: a fixed random seed (42) is used for splitting and model training."]);
  b.h2("2.6 User Documentation");
  b.p("The following documentation is delivered in the documents/ folder: ROP·AI User Guide (installation, every page, viva demo script, troubleshooting), the complete thesis, the proposal, the Requirements & Verification Report and this SRS. The README.md file on GitHub gives a quick start.");
  b.h2("2.7 Assumptions and Dependencies");
  b.bullets(["The drilling data are representative of the wells to which the model is applied; predictions for different fields require retraining.",
    "The current demonstration models are trained on a synthetic dataset; final engineering use requires real field data (e.g. Equinor Volve).",
    "Recorded sensor values are in, or can be converted to, the specified units.",
    "Third-party libraries behave as documented; versions are pinned to minimum versions in requirements.txt."]);

  // ------------------------------------------------------------------ 3
  b.chapter("External Interface Requirements");
  b.h2("3.1 User Interfaces");
  b.p("The web application uses a dark theme with a sidebar for navigation, model selection and the ROP unit switch, and is designed for desktop and laptop screens. Charts are interactive (zoom, hover, pan). The pages are listed below; screenshots are included in the User Guide.");
  b.table("User-interface pages", ["Page", "Main UI elements"], [
    ["🏠 Overview", "Hero banner, five KPI cards, workflow steps, leaderboard (test vs blind-well R²)"],
    ["🎯 Predict ROP", "Eight sliders, ROP result card with ± RMSE, gauge, time-to-drill card, range check message, five-model comparison, sensitivity curve"],
    ["⚙️ Optimizer", "Fixed-parameter sliders, limits, WOB × RPM contour map with optimum marker, optimum cards"],
    ["📊 Data Explorer", "CSV uploader, KPI cards, tabs: scatter, distributions, correlation, depth log, table"],
    ["📈 Model Results", "Metrics table, tabs: actual vs predicted, residuals, metric comparison, feature importance, blind well & final selection"],
    ["📁 Batch Prediction", "Template download, CSV uploader, metrics cards, depth plot, results table, download button"],
    ["📄 Reports", "Download buttons for all documents (Word/PDF), figures ZIP, results ZIP, model, model card; model card view; figure gallery"],
    ["ℹ️ About", "Aim, models, team, tech stack, inputs/outputs, methodology flowchart"],
  ], [1.8, 6.2], { leftAll: true });
  b.figure(SS + "02_predict.png", "Example user interface: Predict ROP page", 6.0);
  b.h2("3.2 Hardware Interfaces");
  b.p("No special hardware interfaces. The system does not connect to rig sensors, PLCs or WITSML servers; drilling data are supplied as files.");
  b.h2("3.3 Software Interfaces");
  b.table("Software interfaces", ["Interface", "Direction", "Format / protocol"], [
    ["Drilling data", "Input", "CSV (UTF-8, comma-separated, header row)"], ["Trained models", "Output / input", "joblib (scikit-learn Pipeline objects)"],
    ["Result tables", "Output", "CSV and JSON (results/)"], ["Model card", "Output", "JSON (results/model_card.json)"],
    ["Figures", "Output", "PNG, 220 dpi (figures/)"], ["Documents", "Output", "DOCX and PDF (documents/)"],
    ["Batch predictions", "Output", "CSV download from the web app"], ["Test report", "Output", "JUnit XML + JSON (results/)"],
  ], [2.4, 1.6, 4], { leftAll: true });
  b.h2("3.4 Communication Interfaces");
  b.p("The web application is served by Streamlit over HTTP on http://localhost:8501 (port configurable). Usage-statistics collection is disabled. Uploaded files are processed in memory on the local computer and are not sent to any external service. Optional public hosting (Streamlit Community Cloud) uses HTTPS.");

  // ------------------------------------------------------------------ 4
  b.chapter("Functional Requirements");
  b.p("Each requirement has a unique identifier, a priority (High = essential for the FYP, Medium = important, Low = desirable) and is verified as described in Chapter 8.");
  const fr = (id, title, rows) => { b.h2(`${id} ${title}`); b.table(`${title} requirements`, ["ID", "Requirement", "Priority"], rows, [1.0, 6.0, 1.0], { leftAll: true }); };
  fr("4.1", "Data Input and Validation", [
    ["FR-1.1", "The system shall read drilling data from a CSV file given on the command line (--data) and from files uploaded in the web application.", H],
    ["FR-1.2", "The system shall require the columns Depth, WOB, RPM, Torque, Q, MW, SPP, Bit_Dia and ROP (ROP optional for batch prediction) and shall show an error message naming any missing column.", H],
    ["FR-1.3", "The system shall accept a separate blind-well CSV file (--blind) for final testing.", H],
  ]);
  fr("4.2", "Data Cleaning", [
    ["FR-2.1", "The system shall remove duplicate records.", H],
    ["FR-2.2", "The system shall count missing values per column and report them.", H],
    ["FR-2.3", "The system shall flag values outside the physical limits of Table 6-2 as unrealistic and treat them as missing.", H],
    ["FR-2.4", "The system shall remove records with missing or invalid ROP.", H],
    ["FR-2.5", "The system shall remove ROP outliers using the 3 × IQR rule.", H],
    ["FR-2.6", "The system shall impute missing input values with the median of the training set only.", H],
    ["FR-2.7", "The system shall save a cleaning log with the number of records after each step.", MED],
  ]);
  fr("4.3", "Exploratory Data Analysis", [
    ["FR-3.1", "The system shall produce histograms, box plots, a correlation heatmap, ROP-versus-parameter scatter plots and a ROP–depth log.", H],
    ["FR-3.2", "The system shall save descriptive statistics and the correlation matrix as tables.", MED],
  ]);
  fr("4.4", "Feature Selection", [
    ["FR-4.1", "The system shall compute Pearson correlation, mutual information and random-forest importance of every input with ROP on the training set.", H],
    ["FR-4.2", "The system shall perform recursive feature elimination with 5-fold cross-validation and plot CV RMSE against the number of features.", MED],
  ]);
  fr("4.5", "Model Development and Training", [
    ["FR-5.1", "The system shall split the cleaned data randomly into 80 % training and 20 % testing data with a fixed seed.", H],
    ["FR-5.2", "The system shall standardize inputs with statistics fitted on the training data only.", H],
    ["FR-5.3", "The system shall train Linear Regression, Decision Tree, Random Forest, SVR (RBF kernel) and ANN (MLP) models.", H],
    ["FR-5.4", "The system shall tune the hyperparameters of each model by grid search with 5-fold cross-validation; for Random Forest at least the number of trees, maximum depth, minimum samples per split and minimum samples per leaf.", H],
    ["FR-5.5", "The system shall record the training time of each model.", MED],
  ]);
  fr("4.6", "Model Evaluation", [
    ["FR-6.1", "The system shall compute MAE, MSE, RMSE and R² of every model on the unseen test set.", H],
    ["FR-6.2", "The system shall produce a model-comparison table and chart.", H],
    ["FR-6.3", "The system shall produce actual-vs-predicted, residual and error-distribution plots for every model.", H],
    ["FR-6.4", "The system shall produce feature-importance bar charts for the Random Forest and Decision Tree models.", H],
    ["FR-6.5", "The system shall produce a training-versus-testing comparison to detect overfitting.", MED],
  ]);
  fr("4.7", "Blind-Well Test and Final Model Selection", [
    ["FR-7.1", "The system shall evaluate all trained models on the blind well with the same metrics.", H],
    ["FR-7.2", "The system shall select the final model as the model with the highest mean of test R² and blind-well R² (test R² only if no blind well is supplied).", H],
  ]);
  fr("4.8", "Model Persistence and Documentation", [
    ["FR-8.1", "The system shall save the final model and all five models as joblib files.", H],
    ["FR-8.2", "The system shall write a model card containing input parameters, algorithm, pipeline, ANN architecture (if applicable), hyperparameters, test and blind-well metrics and the training range of every input.", H],
  ]);
  fr("4.9", "ROP Prediction (Web Application)", [
    ["FR-9.1", "The application shall predict ROP from eight user-controlled inputs and update the result immediately when an input changes.", H],
    ["FR-9.2", "The application shall allow the user to choose any of the five models; the final model shall be selected by default.", H],
    ["FR-9.3", "The application shall display the prediction with its test RMSE, on a gauge, and as the time to drill 1,000 ft.", MED],
    ["FR-9.4", "The application shall warn the user when any input is outside the training range and list the affected inputs.", H],
    ["FR-9.5", "The application shall show the predictions of all five models for the same inputs.", MED],
    ["FR-9.6", "The application shall plot the sensitivity of ROP to a selected input, marking the training range.", MED],
    ["FR-9.7", "The application shall display ROP in ft/hr or m/hr as selected by the user.", L],
    ["FR-9.8", "Predicted ROP shall never be negative.", H],
  ]);
  fr("4.10", "Drilling-Parameter Optimizer", [
    ["FR-10.1", "The application shall evaluate a 40 × 40 grid of WOB and RPM values within user-defined maximum limits, with the other parameters held constant.", MED],
    ["FR-10.2", "The application shall display the predicted ROP as a contour map and mark and report the optimum WOB, RPM and ROP.", MED],
  ]);
  fr("4.11", "Data Exploration and Model Results", [
    ["FR-11.1", "The application shall show interactive scatter plots (coloured by hole size), histograms with statistics, a correlation heatmap, a depth log and a data table for the project data or an uploaded CSV.", MED],
    ["FR-11.2", "The application shall show the model-comparison table and, for a selected model, actual-vs-predicted and residual plots, metric bar charts and feature importance.", H],
    ["FR-11.3", "The application shall show the blind-well results and the selection score used to choose the final model.", H],
  ]);
  fr("4.12", "Batch Prediction", [
    ["FR-12.1", "The application shall provide a CSV input template for download.", MED],
    ["FR-12.2", "The application shall predict ROP for every row of an uploaded CSV file.", H],
    ["FR-12.3", "If measured ROP is present, the application shall compute MAE, RMSE and R² and plot measured and predicted ROP against depth.", MED],
    ["FR-12.4", "The application shall allow the results to be downloaded as CSV.", H],
  ]);
  fr("4.13", "Reports and Downloads", [
    ["FR-13.1", "The application shall offer downloads of the thesis, proposal, user guide, verification report and SRS in Word and PDF format when available.", MED],
    ["FR-13.2", "The application shall offer downloads of all figures (ZIP), all result tables (ZIP), the final model and the model card.", MED],
    ["FR-13.3", "The report generator shall rebuild all documents from the latest results, including a page-numbered table of contents and lists of figures and tables.", MED],
  ]);
  fr("4.14", "Verification", [
    ["FR-14.1", "The system shall provide an automated test-suite covering formulas, cleaning, split, leakage, models, saved model, selection rule and every application page.", H],
    ["FR-14.2", "The system shall independently re-compute the reported test metrics from the saved predictions and report the maximum difference.", MED],
  ]);

  // ------------------------------------------------------------------ 5
  b.chapter("Non-Functional Requirements");
  b.table("Non-functional requirements", ["ID", "Category", "Requirement", "Measured value (current system)"], [
    ["NFR-1", "Performance", "A single prediction shall be returned in less than 1 s.", "≈ 2 ms (ANN), ≈ 87 ms (Random Forest)"],
    ["NFR-2", "Performance", "Batch prediction of 10,000 rows shall complete in less than 5 s.", "≈ 0.01 s (ANN)"],
    ["NFR-3", "Performance", "The optimizer grid (1,600 points) shall be computed in less than 2 s.", "≈ 5 ms (ANN)"],
    ["NFR-4", "Performance", "The complete pipeline for ≈ 3,000 records shall finish in less than 10 min on a 4-core computer.", "≈ 1.7 min"],
    ["NFR-5", "Accuracy", "The final model shall have a lower test RMSE than the linear-regression baseline, and its blind-well metrics shall be reported.", `RMSE ${M[best][6].toFixed(2)} vs ${M["Linear Regression"][6].toFixed(2)} ft/hr (demo data)`],
    ["NFR-6", "Correctness", "No information from the test set or blind well shall be used for training, imputation, scaling or feature selection.", "Verified by tests"],
    ["NFR-7", "Reproducibility", "Re-running the pipeline on the same data shall give the same split, models and selection (fixed seed 42).", "Verified"],
    ["NFR-8", "Usability", "A new user shall be able to obtain a prediction within 1 minute of opening the application, without training.", "Default values give an immediate prediction"],
    ["NFR-9", "Usability", "All charts shall have axis titles with units, and colour shall not be the only means of identification.", "Inspection"],
    ["NFR-10", "Reliability", "Invalid uploads (missing columns) shall produce an error message, not a crash.", "Verified"],
    ["NFR-11", "Maintainability", "Code shall be modular (cleaning, EDA, feature selection, models, evaluation as separate functions) and documented.", "Inspection"],
    ["NFR-12", "Portability", "The system shall run on Windows, macOS and Linux with Python 3.11+.", "Pure-Python dependencies"],
    ["NFR-13", "Security & privacy", "Uploaded data shall be processed locally and not transmitted to external services; usage statistics are disabled.", "Configuration"],
    ["NFR-14", "Traceability", "Every functional requirement shall be traceable to a test, demonstration or inspection.", "Chapter 8"],
  ], [0.9, 1.4, 3.6, 2.1], { leftAll: true });

  // ------------------------------------------------------------------ 6
  b.chapter("Data Requirements");
  b.h2("6.1 Data Dictionary");
  b.table("Input and output data dictionary", ["Column", "Description", "Unit", "Type", "Role"], [
    ["Depth", "Measured depth", "ft", "float", "Input"], ["WOB", "Weight on bit", "klbf", "float", "Input"], ["RPM", "Rotary speed", "rev/min", "float", "Input"],
    ["Torque", "Surface torque", "kft·lbf", "float", "Input"], ["Q", "Mud flow rate", "gpm", "float", "Input"], ["MW", "Mud density (ρ)", "ppg", "float", "Input"],
    ["SPP", "Standpipe pressure", "psi", "float", "Input"], ["Bit_Dia", "Bit diameter", "in", "float", "Input"], ["ROP", "Rate of penetration", "ft/hr", "float", "Target (output)"],
  ], [1.3, 2.6, 1.2, 1.1, 1.8]);
  b.h2("6.2 Validation Rules");
  b.table("Physical limits used to validate data", ["Column", "Minimum", "Maximum", "Unit"], [
    ["WOB", "0.5", "80", "klbf"], ["RPM", "10", "400", "rev/min"], ["Torque", "0", "60", "kft·lbf"], ["Q", "100", "1500", "gpm"],
    ["MW", "8.0", "20.0", "ppg"], ["SPP", "200", "7000", "psi"], ["Bit_Dia", "3", "30", "in"], ["Depth", "0", "35000", "ft"], ["ROP", "0.5", "500", "ft/hr"],
  ], [2, 1.5, 1.5, 1.5]);
  b.h2("6.3 Data Stores and Retention");
  b.table("Data stores", ["Store", "Content", "Created by"], [
    ["data/", "Raw, cleaned and blind-well CSV files", "User / pipeline"], ["models/", "final_rop_model.joblib, all_models.joblib", "Pipeline"],
    ["results/", "Cleaning log, statistics, feature selection, model comparison, blind test, selection score, model card, test predictions, verification", "Pipeline / verify.py"],
    ["figures/", "All graphs and diagrams", "Pipeline / make_diagrams.py"], ["documents/", "Word and PDF documents, screenshots, reference files", "Report generator"],
  ], [1.6, 4.6, 1.8], { leftAll: true });

  // ------------------------------------------------------------------ 7
  b.chapter("Use Cases");
  const fU = b.nextFig();
  b.p(`${fU} shows the actors and use cases of ROP·AI. The main use cases are described below.`);
  b.figure("diagram_use_case.png", "Use-case diagram of ROP·AI", 6.0);
  const uc = (id, name, actor, pre, flow, post) => b.table(`${id}: ${name}`, ["Field", "Description"], [
    ["Primary actor", actor], ["Preconditions", pre], ["Main flow", flow], ["Postconditions", post]], [1.8, 6.2], { leftAll: true });
  uc("UC-2", "Train, tune and evaluate models", "Student / researcher", "Python environment installed; training CSV (and optional blind-well CSV) available",
    "1. User runs python code/rop_pipeline.py --data <file> --blind <file>. 2. System cleans data and saves the cleaning log. 3. System produces EDA graphs. 4. System splits data 80:20 and performs feature selection on the training set. 5. System tunes and trains the five models. 6. System evaluates them on the test set and the blind well. 7. System selects and saves the final model and model card.",
    "Models, result tables, figures and model card are updated; the web app and documents use the new results.");
  uc("UC-5", "Predict ROP (single point)", "Drilling engineer / end user", "Trained models exist; web app is running",
    "1. User opens Predict ROP. 2. User sets the eight drilling parameters. 3. System checks the training range and shows a confirmation or warning. 4. System displays predicted ROP with ± RMSE, gauge and drilling time, and the predictions of all five models. 5. User optionally inspects the sensitivity curve.",
    "Predicted ROP is shown; no data are stored.");
  uc("UC-6", "Optimize WOB and RPM", "Drilling engineer / end user", "Trained models exist; web app is running",
    "1. User opens Optimizer. 2. User sets depth, mud density, flow rate, bit size, SPP and the WOB/RPM limits. 3. System evaluates the 40 × 40 grid. 4. System shows the contour map and the optimum WOB, RPM and ROP.",
    "Recommended parameters are displayed with a caution note.");
  uc("UC-7", "Batch prediction from CSV", "Drilling engineer / end user", "CSV file with the eight input columns",
    "1. User downloads the template (optional). 2. User uploads the CSV. 3. System validates the columns. 4. System predicts ROP for every row and, if ROP is present, computes metrics and plots. 5. User downloads the results.",
    "A CSV with predicted ROP is downloaded. Alternative flow: missing columns → error message listing them.");
  uc("UC-10", "Generate thesis and reports", "Student / researcher", "Pipeline results exist; Node.js, LibreOffice and poppler installed",
    "1. User runs python code/export_doc_data.py, python code/verify.py and python code/reports/make_final.py. 2. System builds every document, converts it to PDF, reads the page numbers back and rebuilds it with a static table of contents.",
    "Updated Word and PDF documents are stored in documents/.");

  // ------------------------------------------------------------------ 8
  b.chapter("Verification and Acceptance");
  b.p("Each requirement is verified by an automated **Test**, a **Demonstration** in the running application, or an **Inspection** of code or outputs. All automated tests are run with python code/verify.py; the results are reported in the Requirements & Verification Report.");
  b.table("Requirements verification matrix", ["Requirement(s)", "Method", "Evidence / test"], [
    ["FR-1.1, FR-1.3", "Test", "Pipeline run with --data/--blind; test_blind_well_not_used_in_training"],
    ["FR-1.2, NFR-10", "Demonstration", "Upload of a CSV with a missing column shows an error message (Data Explorer, Batch)"],
    ["FR-2.1, FR-2.4", "Test", "test_cleaned_data_has_no_duplicates_or_missing_target; test_cleaning_function_removes_bad_rows"],
    ["FR-2.3", "Test", "test_cleaned_values_are_within_physical_limits"], ["FR-2.5", "Test", "test_rop_outliers_removed_with_iqr_rule"],
    ["FR-2.6, FR-5.2, NFR-6", "Test", "test_imputer_and_scaler_fitted_on_training_data_only"],
    ["FR-2.2, FR-2.7, FR-3.x, FR-4.x", "Test / Inspection", "test_required_figures_exist; results/*.csv"],
    ["FR-5.1, NFR-7", "Test", "test_split_is_80_20_and_disjoint; test_saved_test_set_matches_split"],
    ["FR-5.3", "Test", "test_all_five_models_trained_and_compared"], ["FR-5.4", "Test", "test_random_forest_tuned_on_required_hyperparameters"],
    ["FR-6.1", "Test", "test_metric_formulas_match_definitions; test_reported_metrics_recomputed_from_saved_predictions"],
    ["FR-6.2 – FR-6.5", "Test / Inspection", "test_required_figures_exist; thesis Tables 4-6, 4-7"],
    ["FR-7.1, FR-7.2", "Test", "test_final_model_follows_selection_rule; results/blind_test.csv"],
    ["FR-8.1, FR-8.2", "Test", "test_saved_final_model_reproduces_predictions; test_model_card_documents_required_items"],
    ["FR-9.x, FR-10.x, FR-11.x, FR-12.x, FR-13.1–13.2", "Test + Demonstration", "test_every_app_page_runs_without_error (8 pages); User Guide screenshots"],
    ["FR-9.8", "Inspection / Test", "Predictions clipped at zero; test_predictions_are_physically_sensible"],
    ["FR-13.3", "Demonstration", "make_final.py: all TOC entries resolved"],
    ["FR-14.1, FR-14.2", "Test", "code/verify.py: 44/44 tests pass; max metric difference ≈ 10⁻¹⁵"],
    ["NFR-1 – NFR-4", "Test (timing)", "Measured values in Table 5-1"], ["NFR-5", "Test", "test_nonlinear_models_beat_linear_baseline"],
    ["NFR-9, NFR-11 – NFR-13", "Inspection", "Code review, configuration (.streamlit/config.toml)"],
  ], [2.4, 1.6, 4.0], { leftAll: true });
  b.h2("8.1 Acceptance Criteria");
  b.bullets(["All automated tests pass (python code/verify.py exits without error).",
    "The pipeline completes on the real field dataset and the final model has a lower test RMSE than the baseline.",
    "Blind-well metrics of the final model are reported in the thesis.",
    "All eight pages of the web application open without errors, and the documents build with a complete table of contents.",
    "The supervisor confirms that the methodology requirements are met (see the Requirements & Verification Report)."]);

  // ------------------------------------------------------------------ 9
  b.chapter("Future Enhancements");
  b.bullets(["Real-time data input from rig systems (WITSML) for live ROP prediction.",
    "Additional inputs: lithology, rock strength (UCS), bit type and bit wear.",
    "Additional models (gradient boosting, LSTM) and explainability (SHAP values).",
    "Multi-well training with well-based cross-validation.",
    "User accounts and saved scenarios for public deployment."]);
}

buildOne("ROP_AI_SRS", front, body).then(() => console.log("SRS written"));
