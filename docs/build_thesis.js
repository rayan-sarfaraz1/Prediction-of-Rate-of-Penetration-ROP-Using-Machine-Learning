/*
 * Builds two Word documents in BUITEMS P&G thesis format:
 *   1. ROP_FYP_Proposal_Ch1-3.docx        (Introduction, Literature Review, Methodology + work plan)
 *   2. ROP_FYP_Complete_Thesis_Draft.docx (all front matter + Chapters 1-5 + references + appendices)
 * Usage:  node docs/build_thesis.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType,
  HeadingLevel, PageBreak, Footer, PageNumber, NumberFormat, TableOfContents, StyleLevel,
  WidthType, ShadingType, BorderStyle, LevelFormat, TabStopType, VerticalAlign,
  PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "figures");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "doc_data.json"), "utf8"));
const BL = D.blind ? Object.fromEntries(D.blind.map((r) => [r[0], { MAE: r[1], MSE: r[2], RMSE: r[3], R2: r[4] }])) : null;
const TOP_TEST = D.models.reduce((a, r) => (r[7] > a[7] ? r : a))[0];

// ------------------------------------------------------------------ placeholders
const TITLE = "PREDICTION OF RATE OF PENETRATION (ROP) USING MACHINE LEARNING";
const TITLE_CASE = "Prediction of Rate of Penetration (ROP) Using Machine Learning";
const SUPERVISOR = "[Supervisor Name]";
const BATCH = "Batch: [Fall-20XX]";
const MEMBERS = [
  "[STUDENT NAME 1] (Group Leader) ([F2X-BS P&G-XXXXX])",
  "[STUDENT NAME 2] ([F2X-BS P&G-XXXXX])",
  "[STUDENT NAME 3] ([F2X-BS P&G-XXXXX])",
  "[STUDENT NAME 4] ([F2X-BS P&G-XXXXX])",
];
const DATE = "[DD/MM/YYYY]";

// ------------------------------------------------------------------ constants
const FONT = "Times New Roman";
const BODY = 24; // 12 pt
const TABLE_W = 8306; // A4 width 11906 - 2160 left - 1440 right
const LBLUE = "DBE8F8", LGREY = "F3F2EE", LORANGE = "FBE1D6";

// ------------------------------------------------------------------ inline markup
// **bold**  *italic*  ^{sup}  _{sub}
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\^\{[^}]+\}|_\{[^}]+\})/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    else if (t.startsWith("^")) out.push(new TextRun({ text: t.slice(2, -1), superScript: true, ...base }));
    else out.push(new TextRun({ text: t.slice(2, -1), subScript: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

// ------------------------------------------------------------------ builder state
class Builder {
  constructor() { this.ch = 0; this.fig = 0; this.tab = 0; this.eq = 0; this.numInst = 0; this.out = []; this.entries = []; }
  entry(kind, level, text) { this.entries.push({ kind, level, text: text.replace(/\*\*|\*|\^\{|_\{|\}/g, "") }); }
  push(...x) { this.out.push(...x); return this; }

  chapter(title) {
    this.ch += 1; this.fig = 0; this.tab = 0; this.eq = 0;
    this.entry("h", 1, `CHAPTER ${this.ch} ${title.toUpperCase()}`);
    return this.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true,
      children: [new TextRun(`CHAPTER ${this.ch} ${title.toUpperCase()}`)] }));
  }
  unnumbered(title, pageBreak = true, toc = true) {
    if (toc) this.entry("h", 1, title);
    return this.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pageBreak, children: [new TextRun(title)] }));
  }
  h2(t) { this.entry("h", 2, t); return this.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] })); }
  h3(t) { this.entry("h", 3, t); return this.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] })); }
  p(t, opts = {}) {
    return this.push(new Paragraph({ alignment: opts.align || AlignmentType.JUSTIFIED, children: runs(t, opts.run || {}),
      spacing: { after: 120, line: 360 } }));
  }
  bullets(items) {
    items.forEach((t) => this.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, alignment: AlignmentType.JUSTIFIED,
      spacing: { after: 60, line: 340 }, children: runs(t) })));
    return this;
  }
  numbered(items) {
    this.numInst += 1;
    items.forEach((t) => this.push(new Paragraph({ numbering: { reference: "numbers", level: 0, instance: this.numInst },
      alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 340 }, children: runs(t) })));
    return this;
  }
  figure(file, caption, widthIn = 6.0) {
    const buf = fs.readFileSync(path.join(FIG, file));
    const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
    const W = Math.round(widthIn * 96), H = Math.round(W * h / w);
    this.fig += 1;
    const label = `Figure ${this.ch}-${this.fig}`;
    this.entry("fig", 1, `${label} ${caption}`);
    this.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: W, height: H },
        altText: { title: label, description: caption, name: file } })] }));
    this.push(new Paragraph({ style: "FigCaption", children: runs(`${label} ${caption}`) }));
    return label;
  }
  nextFig() { return `Figure ${this.ch}-${this.fig + 1}`; }
  nextTab() { return `Table ${this.ch}-${this.tab + 1}`; }
  nextEq() { return `(${this.ch}-${this.eq + 1})`; }
  table(caption, headers, rows, widths, opts = {}) {
    let label;
    if (opts.label) label = opts.label; else { this.tab += 1; label = `Table ${this.ch}-${this.tab}`; }
    this.entry("tab", 1, `${label} ${caption}`);
    this.push(new Paragraph({ style: "TabCaption", keepNext: true, children: runs(`${label} ${caption}`) }));
    const total = widths.reduce((a, b) => a + b, 0);
    const scaled = widths.map((w) => Math.round(w * TABLE_W / total));
    scaled[scaled.length - 1] += TABLE_W - scaled.reduce((a, b) => a + b, 0);
    const border = { style: BorderStyle.SINGLE, size: 4, color: "8A8984" };
    const borders = { top: border, bottom: border, left: border, right: border };
    const cell = (t, i, head, shade) => new TableCell({
      width: { size: scaled[i], type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.CENTER,
      margins: { top: 50, bottom: 50, left: 90, right: 90 },
      shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: LBLUE } : shade ? { type: ShadingType.CLEAR, color: "auto", fill: shade } : undefined,
      children: [new Paragraph({ alignment: (i === 0 && !opts.centerFirst) || opts.leftAll ? AlignmentType.LEFT : AlignmentType.CENTER,
        spacing: { after: 0, line: 260 }, children: runs(String(t), { size: 20, bold: head || undefined }) })],
    });
    const trs = [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) })];
    rows.forEach((r, k) => trs.push(new TableRow({ cantSplit: true,
      children: r.map((c, i) => cell(c, i, false, opts.highlightRow === k ? LORANGE : undefined)) })));
    this.push(new Table({ width: { size: TABLE_W, type: WidthType.DXA }, columnWidths: scaled, rows: trs }));
    this.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    return label;
  }
  equation(eq) {
    this.eq += 1;
    this.push(new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: TABLE_W / 2 }, { type: TabStopType.RIGHT, position: TABLE_W }],
      spacing: { before: 80, after: 120 }, children: [new TextRun("\t"), ...runs(eq, { italics: false }), new TextRun(`\t(${this.ch}-${this.eq})`)] }));
    return `Equation (${this.ch}-${this.eq})`;
  }
  note(title, text) {
    const b = { style: BorderStyle.SINGLE, size: 12, color: "EB6834" };
    this.push(new Table({ width: { size: TABLE_W, type: WidthType.DXA }, columnWidths: [TABLE_W], rows: [new TableRow({ children: [
      new TableCell({ width: { size: TABLE_W, type: WidthType.DXA }, borders: { top: b, bottom: b, left: b, right: b },
        shading: { type: ShadingType.CLEAR, color: "auto", fill: "FDF1EB" }, margins: { top: 100, bottom: 100, left: 140, right: 140 },
        children: [new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, bold: true, size: 22 })] }),
          new Paragraph({ alignment: AlignmentType.JUSTIFIED, children: runs(text, { size: 22 }) })] })] })] }));
    this.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    return this;
  }
  center(t, opts = {}) {
    return this.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opts.after ?? 120, before: opts.before ?? 0 },
      children: runs(t, { size: opts.size || BODY, bold: opts.bold, color: opts.color }) }));
  }
  blank(n = 1) { for (let i = 0; i < n; i++) this.push(new Paragraph({ children: [] })); return this; }
  pageBreak() { return this.push(new Paragraph({ children: [new PageBreak()] })); }
}

// =================================================================== FRONT MATTER
function titlePage(b, kind) {
  b.center(TITLE, { size: 32, bold: true, before: 600, after: 360 });
  b.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [new ImageRun({ type: "png",
    data: fs.readFileSync(path.join(__dirname, "assets", "buitems_logo.png")), transformation: { width: 150, height: 150 },
    altText: { title: "BUITEMS logo", description: "BUITEMS logo", name: "logo" } })] }));
  if (kind === "proposal") b.center("FINAL YEAR PROJECT PROPOSAL (SYNOPSIS)", { bold: true, size: 26, after: 240 });
  b.center("DEPARTMENT OF PETROLEUM & GAS ENGINEERING", { bold: true, size: 26 });
  b.center(BATCH, { after: 300 });
  b.center("PROJECT SUPERVISOR", { bold: true });
  b.center(SUPERVISOR, { after: 300 });
  b.center("GROUP MEMBERS", { bold: true });
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  b.blank();
  b.center("FACULTY OF ENGINEERING AND ARCHITECTURE", { bold: true, before: 300 });
  b.center("BALOCHISTAN UNIVERSITY OF INFORMATION TECHNOLOGY, ENGINEERING AND MANAGEMENT SCIENCES (BUITEMS)", { bold: true });
}

function submittedPage(b) {
  b.pageBreak();
  b.center(TITLE, { size: 28, bold: true, before: 400, after: 400 });
  b.center("Thesis submitted to", { after: 200 });
  b.center("BALOCHISTAN UNIVERSITY OF INFORMATION TECHNOLOGY, ENGINEERING & MANAGEMENT SCIENCES", { bold: true, after: 300 });
  b.center("For the partial fulfillment of the requirements for the degree of", { after: 200 });
  b.center("BACHELOR OF SCIENCE", { bold: true, after: 60 });
  b.center("In", { after: 60 });
  b.center("PETROLEUM AND GAS ENGINEERING", { bold: true, after: 300 });
  b.center("By", { after: 120 });
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  b.center("Department of Petroleum & Gas Engineering", { before: 500, after: 40 });
  b.center("Faculty of Engineering and Architecture", { after: 40 });
  b.center(DATE);
}

function signatures(b) {
  b.p("**Students’ Names and Signatures:**");
  MEMBERS.forEach((m) => b.p(`${m.replace(/\s*\(.*$/, "")}  _____________________`, { align: AlignmentType.LEFT }));
  b.center("Department of Petroleum & Gas Engineering", { before: 300, after: 40 });
  b.center("Faculty of Engineering and Architecture", { after: 40 });
  b.center(DATE);
}

function declarationPages(b) {
  b.unnumbered("DECLARATION OF THE AUTHOR");
  b.p(`We hereby declare that the topic of our BS project/thesis “${TITLE_CASE}” is our own work, and it has not been presented for a degree at Balochistan University of Information Technology, Engineering & Management Sciences, Quetta, or elsewhere in the country. If this claim is found to be false at any time after our graduation, the University has the right to rescind our BS degree.`);
  signatures(b);

  b.unnumbered("PLAGIARISM ASSURANCE");
  b.p(`We hereby certify that the research presented in the thesis titled “${TITLE_CASE}” is our own study, with no key input from anyone else. Small contributions and assistance have been sincerely acknowledged, and the entire thesis has been written collectively by the group members.`);
  b.p("We are aware of the zero-tolerance policy of the HEC and of Balochistan University of Information Technology, Engineering & Management Sciences towards plagiarism. As authors of the above thesis/project, we declare that no portion of this thesis/project has been plagiarized and that all material used as reference has been properly cited.");
  b.p("We acknowledge that if we are found guilty of any formal copyright infringement in the above thesis after receiving our BS degree, the University reserves the right to withdraw or cancel our BS degree, and that the HEC and the University have the right to publish our names on the HEC/University website on which the names of students who submitted plagiarized work are listed.");
  signatures(b);

  b.unnumbered("CERTIFICATE OF APPROVAL");
  b.p(`The thesis entitled “${TITLE_CASE}” by;`);
  MEMBERS.forEach((m) => b.center(m, { after: 40 }));
  b.p("for BS (Petroleum and Gas Engineering) was evaluated and recommended by the Departmental Research Committee (DRC) in its meeting held on ______________.");
  b.blank(2);
  b.p("Supervisor: ______________________          Chairperson: ______________________", { align: AlignmentType.LEFT });
  b.blank();
  b.center("Balochistan University of Information Technology, Engineering and Management Sciences", { before: 400, after: 40 });
  b.center(DATE);

  b.unnumbered("ACKNOWLEDGEMENTS");
  b.p(`First of all, we thank Almighty Allah for giving us the strength and ability to complete this project. We are deeply grateful to our supervisor, ${SUPERVISOR}, for proposing this topic, for providing the research methodology and for continuous guidance throughout the project. We also thank the Chairperson and faculty members of the Department of Petroleum & Gas Engineering, BUITEMS, for their support. We acknowledge Equinor and the former Volve licence partners for making the Volve field data publicly available for research and education. Finally, we thank our families and friends for their encouragement.`);
}

function abstractPage(b, kind) {
  const best = D.summary.best_model;
  const m = Object.fromEntries(D.models.map((r) => [r[0], r]));
  const r2 = (n) => m[n][7].toFixed(3);
  b.unnumbered("ABSTRACT");
  b.p("Rate of Penetration (ROP) is one of the most important performance indicators in oil and gas well drilling because drilling time directly controls a large share of total well cost. ROP depends on many interacting operational, hydraulic, drilling-fluid and formation parameters, which makes it difficult to predict accurately with traditional empirical models such as the Bingham and Bourgoyne–Young equations. This project develops a data-driven workflow to predict ROP from commonly available surface drilling parameters using supervised machine learning.");
  b.p("The input vector consists of weight on bit (WOB), rotary speed (RPM), torque, mud flow rate (Q), mud density (ρ), standpipe pressure (SPP), bit diameter (D) and depth, with ROP as the target variable. The methodology covers data collection, data cleaning (duplicate removal, physical-limit checks, median imputation and IQR-based outlier treatment), exploratory data analysis, feature selection using Pearson correlation, mutual information and random-forest importance, standardization and an 80:20 train–test split. Five regression models — Linear Regression (baseline), Decision Tree, Random Forest, Support Vector Regression (RBF kernel) and an Artificial Neural Network (multilayer perceptron) — are trained with grid-search hyperparameter tuning and 5-fold cross-validation, and evaluated on unseen test data using MAE, MSE, RMSE and R².");
  if (kind === "complete") {
    b.p(`In this draft, the complete workflow was implemented in Python and demonstrated on a physics-based synthetic drilling dataset of ${D.cleaning[0][1]} records, generated so that every step could be developed and tested before the field data were available. On the random test set, the nonlinear models clearly outperformed the linear baseline (R² = ${r2("Linear Regression")}); ${TOP_TEST} (R² = ${r2(TOP_TEST)}) and the ANN (R² = ${r2("ANN (MLP)")}) were the most accurate. On a separate blind well that was never used in training, however, the tree-based models lost much of their accuracy (Random Forest R² = ${BL["Random Forest"].R2.toFixed(3)}) while the ANN remained robust (R² = ${BL["ANN (MLP)"].R2.toFixed(3)}). Using the mean of test and blind-well R² as the selection criterion, the ${best} was selected as the final model. Feature-importance analysis identified depth, WOB and RPM as the most influential parameters. **[These numbers must be replaced with the results obtained from the real field dataset before final submission.]**`);
  } else {
    b.p("The expected outcome is a validated and documented machine-learning model that can predict ROP for unseen drilling intervals, together with a quantitative comparison of the models and an analysis of which drilling parameters have the strongest influence on ROP.");
  }
  b.p("**Keywords:** Rate of penetration, drilling optimization, machine learning, random forest, artificial neural network, support vector regression, Python, scikit-learn", { align: AlignmentType.LEFT });
}

// Static table of contents. `toc` = [{kind, level, text, page}] from the previous build pass
// (page numbers are read back from the rendered PDF by docs/make_final.py). Without data, a
// Word TOC field is used instead.
function tocLine(text, page, level, kind) {
  const top = kind === "h" && level === 1;
  return new Paragraph({ indent: { left: kind === "h" ? (level - 1) * 360 : 0 }, keepLines: true,
    spacing: { before: top ? 120 : 0, after: top ? 60 : 30, line: 276 },
    tabStops: [{ type: TabStopType.RIGHT, position: TABLE_W, leader: "dot" }],
    children: [new TextRun({ text, bold: top, size: top ? 22 : 21 }), new TextRun({ text: `\t${page}`, size: 21, bold: top })] });
}
function tocPages(b, toc, lists = true) {
  const sect = (title, kind, fieldFn) => {
    b.unnumbered(title, true, false);
    if (toc) toc.filter((e) => e.kind === kind).forEach((e) => b.push(tocLine(e.text, e.page, e.level, e.kind)));
    else b.push(fieldFn());
  };
  sect(lists ? "TABLE OF CONTENTS" : "CONTENTS", "h", () => new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }));
  if (!lists) return;
  sect("LIST OF FIGURES", "fig", () => new TableOfContents("List of Figures", { hyperlink: true, stylesWithLevels: [new StyleLevel("FigCaption", 1)] }));
  sect("LIST OF TABLES", "tab", () => new TableOfContents("List of Tables", { hyperlink: true, stylesWithLevels: [new StyleLevel("TabCaption", 1)] }));
}

// Two-pass build: pass 1 collects the headings/captions, pass 2 renders the static TOC with
// page numbers from docs/.toc/<name>.json (or "00" placeholders of the same width).
async function buildOne(name, frontFn, mainFn) {
  const run = (toc) => { const f = new Builder(); frontFn(f, toc); const m = new Builder(); mainFn(m); return [f, m]; };
  const [f1, m1] = run(null);
  const entries = [...f1.entries, ...m1.entries];
  const dir = path.join(__dirname, ".toc"); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${name}.entries.json`), JSON.stringify(entries, null, 1));
  let pages = {};
  const pf = path.join(dir, `${name}.pages.json`);
  if (fs.existsSync(pf)) pages = JSON.parse(fs.readFileSync(pf, "utf8"));
  const toc = entries.map((e, i) => ({ ...e, page: pages[i] ?? "00" }));
  const [f, m] = run(toc);
  fs.writeFileSync(path.join(__dirname, `${name}.docx`), await Packer.toBuffer(makeDoc(f.out, m.out)));
}

function nomenclature(b) {
  b.unnumbered("LIST OF ABBREVIATIONS AND NOMENCLATURE");
  b.table("Abbreviations and symbols used in this thesis", ["Symbol / abbreviation", "Description", "Unit"], [
    ["ROP", "Rate of penetration", "ft/hr"], ["WOB", "Weight on bit", "klbf"], ["RPM, N", "Rotary speed of the bit", "rev/min"],
    ["T", "Surface torque", "kft·lbf"], ["Q", "Mud flow rate", "gpm"], ["ρ, MW", "Mud density (mud weight)", "ppg"],
    ["SPP", "Standpipe pressure", "psi"], ["D, d", "Bit diameter", "in"], ["BHA", "Bottom-hole assembly", "–"],
    ["ML", "Machine learning", "–"], ["LR", "Linear regression", "–"], ["DT", "Decision tree", "–"], ["RF", "Random forest", "–"],
    ["SVR", "Support vector regression", "–"], ["RBF", "Radial basis function", "–"], ["ANN / MLP", "Artificial neural network / multilayer perceptron", "–"],
    ["ReLU", "Rectified linear unit activation", "–"], ["EDA", "Exploratory data analysis", "–"], ["IQR", "Interquartile range", "–"],
    ["MI", "Mutual information", "nats"], ["RFE", "Recursive feature elimination", "–"], ["CV", "Cross-validation", "–"],
    ["MAE", "Mean absolute error", "ft/hr"], ["MSE", "Mean squared error", "(ft/hr)²"], ["RMSE", "Root mean squared error", "ft/hr"],
    ["R²", "Coefficient of determination", "–"], ["y_{i}, ŷ_{i}", "Measured and predicted ROP of sample i", "ft/hr"], ["n", "Number of samples", "–"],
  ], [2.2, 5, 1.4], { label: "Table i" });
}

// =================================================================== CHAPTER 1
function chapter1(b) {
  b.chapter("Introduction");
  b.h2("1.1 Background");
  b.p("Drilling is the most expensive single activity in the development of an oil or gas field. A large share of well cost is time-dependent (rig rate, services, fuel and personnel), so any reduction in drilling time directly lowers the cost of the well. The main indicator of how fast a well is being drilled is the **Rate of Penetration (ROP)** — the speed at which the drill bit advances through the rock, normally expressed in feet per hour (ft/hr) or metres per hour (m/hr) [1, 2].");
  b.h3("1.1.1 The Rotary Drilling Process");
  const fDrill = b.nextFig();
  b.p(`In rotary drilling (${fDrill}), a drill bit attached to the bottom of the drill string is rotated by a top drive or rotary table while part of the weight of the drill collars is applied to the bit as weight on bit (WOB). Drilling fluid (mud) is pumped down the drill pipe by the mud pumps, exits through the bit nozzles, cleans and cools the bit, and carries the rock cuttings up the annulus to the surface. The surface drilling parameters recorded continuously during this process — WOB, rotary speed (RPM), torque, mud flow rate (Q), standpipe pressure (SPP), mud density (ρ) and depth — form the basis of this study.`);
  b.figure("diagram_drilling_system.png", "Simplified rotary drilling system showing where the main drilling parameters are controlled and measured", 4.6);
  b.h3("1.1.2 Rate of Penetration and Its Controlling Factors");
  b.p("ROP is defined as the drilled depth per unit time:");
  b.equation("ROP = Δ*Depth* / Δ*t*");
  const fFac = b.nextFig();
  b.p(`ROP is controlled by a large number of interacting factors (${fFac}). These can be grouped into (i) mechanical/operational parameters such as WOB, RPM, torque, bit type and bit wear; (ii) hydraulic parameters such as flow rate, standpipe pressure and jet impact force, which control bottom-hole cleaning; (iii) drilling-fluid properties such as density and viscosity, which control the differential (overbalance) pressure acting on the rock; and (iv) formation and geometric factors such as rock strength, compaction, pore pressure, depth and hole size [2, 3]. Because these factors interact nonlinearly, ROP is difficult to describe with a simple equation.`);
  b.figure("diagram_rop_factors.png", "Main groups of factors affecting the rate of penetration", 5.6);
  b.h3("1.1.3 Machine Learning in Drilling Engineering");
  b.p("Traditional ROP models (for example those of Maurer, Bingham and Bourgoyne & Young) are physics-based or empirical equations with coefficients that must be calibrated for each field [4–6]. Modern rigs, however, record drilling parameters every few seconds, producing large datasets. Machine learning (ML) is a branch of artificial intelligence in which algorithms learn the relationship between inputs and an output directly from data, without an explicitly programmed equation. Supervised ML regression algorithms such as decision trees, random forests, support vector regression and artificial neural networks have been shown to capture the nonlinear relationship between drilling parameters and ROP more accurately than traditional models in several studies [9–12].");
  b.h2("1.2 Problem Statement");
  b.p("Accurate prediction of ROP is essential for planning drilling time, estimating well cost and selecting optimum drilling parameters. Traditional empirical ROP models rely on simplifying assumptions, need field-specific calibration coefficients and often fail to represent the complex, nonlinear interaction between operational, hydraulic, fluid and formation parameters. As a result, their predictions can deviate significantly from the measured ROP. At the same time, large volumes of recorded drilling data are often not used to their full potential. There is therefore a need for a systematic, data-driven approach that uses commonly available drilling parameters to predict ROP reliably, and for an objective comparison of different machine-learning algorithms for this purpose.");
  b.h2("1.3 Aim");
  b.p("The aim of this project is to develop, evaluate and compare machine-learning models that predict the Rate of Penetration (ROP) from commonly available drilling parameters, and to select the most suitable model for predicting ROP in unseen drilling data.");
  b.h2("1.4 Objectives");
  b.numbered([
    "To collect and prepare a drilling dataset containing WOB, RPM, torque, flow rate, mud density, standpipe pressure, bit diameter, depth and measured ROP.",
    "To clean the data and perform exploratory data analysis to understand the relationship of each drilling parameter with ROP.",
    "To select the most relevant input features using correlation analysis, mutual information and feature importance.",
    "To develop Linear Regression, Decision Tree, Random Forest, Support Vector Regression and Artificial Neural Network models for ROP prediction, and optimize their hyperparameters.",
    "To evaluate and compare the models using MAE, MSE, RMSE and R², together with graphical validation (actual vs predicted, residual and error plots).",
    "To identify the relative influence of each drilling parameter on ROP and to save and document the final ROP prediction model.",
  ]);
  b.h2("1.5 Scope of the Study");
  b.bullets([
    "The study uses historical drilling data (open-source/published datasets and, where available, field drilling records); no new wells are drilled.",
    "Eight input parameters are considered: WOB, RPM, torque, Q, ρ, SPP, bit diameter and depth. Bit type, bit wear and detailed lithology are outside the scope unless provided in the dataset.",
    "Five supervised regression algorithms are investigated, consistent with the BS-level scope recommended by the supervisor; Linear Regression serves as the baseline.",
    "The work is implemented in Python using open-source libraries (pandas, scikit-learn, matplotlib).",
    "The project focuses on ROP *prediction*; real-time optimization of drilling parameters is recommended as future work.",
  ]);
  b.h2("1.6 Significance of the Study");
  b.p("A reliable ROP prediction model helps drilling engineers to (i) estimate drilling time and cost more accurately during well planning, (ii) select drilling parameters that improve ROP and reduce non-productive time, (iii) identify which parameters have the strongest influence on drilling performance, and (iv) make better use of the large volumes of data recorded on modern rigs. For students and the department, the project provides a reproducible, open-source workflow that combines petroleum engineering knowledge with data science, which can be extended to other drilling problems such as torque-and-drag, stuck-pipe or bit-wear prediction.");
  b.h2("1.7 Thesis Structure");
  b.p("**Chapter 1** introduces the background, problem statement, aim, objectives, scope and significance of the study. **Chapter 2** reviews the fundamental concepts, previous research on ROP modelling, existing methods and the research gap. **Chapter 3** describes the methodology, including data collection, data preparation, the mathematical formulation of the machine-learning models, the software and tools, the computational procedure and the methodology flowchart. **Chapter 4** presents the results and discussion: data analysis, model performance, comparison tables and graphs. **Chapter 5** summarizes the major findings and conclusions and gives limitations, recommendations and future work.");
}

// =================================================================== CHAPTER 2
function chapter2(b) {
  b.chapter("Literature Review");
  b.p("This chapter reviews the fundamental concepts of ROP and machine learning, previous research on traditional and data-driven ROP models, the existing methods and the research gap addressed by this project.");
  b.h2("2.1 Fundamental Concepts");
  b.h3("2.1.1 Drilling Parameters Affecting ROP");
  const t = b.nextTab();
  b.p(`${t} summarizes the drilling parameters used in this study and their general effect on ROP as described in standard drilling engineering texts [2, 3].`);
  b.table("Drilling parameters used as model inputs and their general effect on ROP", ["Parameter", "Symbol / unit", "General effect on ROP"], [
    ["Weight on bit", "WOB, klbf", "ROP increases with WOB above the threshold needed to fail the rock, until bit floundering or poor cleaning occurs"],
    ["Rotary speed", "RPM, rev/min", "ROP increases with RPM, usually at a less-than-linear rate (exponent < 1) in harder rocks"],
    ["Torque", "T, kft·lbf", "Reflects bit–rock interaction; higher torque usually accompanies higher WOB and softer formations"],
    ["Flow rate", "Q, gpm", "Improves bottom-hole cleaning and removes cuttings, increasing ROP up to an optimum"],
    ["Mud density", "ρ, ppg", "Higher density increases overbalance (chip hold-down effect) and generally reduces ROP"],
    ["Standpipe pressure", "SPP, psi", "Indicates hydraulic energy delivered to the bit; related to Q, ρ and depth"],
    ["Bit diameter", "D, in", "Larger holes need more WOB for the same unit load (WOB/D); controls hole section"],
    ["Depth", "ft", "Rock strength and compaction increase with depth, so ROP generally decreases with depth"],
  ], [1.6, 1.5, 5]);
  b.h3("2.1.2 Machine Learning for Regression");
  b.p("Machine learning is commonly divided into supervised, unsupervised and reinforcement learning. ROP prediction is a **supervised regression** problem: the algorithm is trained on examples with known inputs *X* (drilling parameters) and a known continuous output *y* (measured ROP), and learns a function ŷ = f(X) that can be applied to new data. The available data are split into a training set, used to fit the model, and a testing set, kept unseen to measure how well the model generalizes. A model that fits the training data very closely but performs poorly on new data is said to **overfit**; a model that is too simple to capture the relationship **underfits**. Techniques such as cross-validation and hyperparameter tuning are used to balance this bias–variance trade-off [14, 17].");
  b.h2("2.2 Previous Research");
  b.h3("2.2.1 Traditional (Physics-Based and Empirical) ROP Models");
  b.p("Maurer (1962) derived the “perfect-cleaning” theory for roller-cone bits, in which ROP is proportional to the square of the excess unit weight on bit and to rotary speed, and inversely proportional to the square of rock strength [4]:");
  b.equation("ROP = (K / S^{2}) · [ (W/d) − (W/d)_{0} ]^{2} · N");
  b.p("where *K* is a constant, *S* is rock compressive strength, *W/d* is weight on bit per unit bit diameter, (*W/d*)_{0} is the threshold bit weight and *N* is rotary speed. Bingham (1964) proposed a simpler empirical relationship in which the exponent on unit bit weight is determined from field data [5]:");
  b.equation("ROP = K · (W/d)^{a} · N");
  b.p("Bourgoyne and Young (1974) developed the most widely used empirical model, expressing ROP as the product of eight functions representing formation strength, normal compaction, under-compaction, differential pressure, bit weight, rotary speed, tooth wear and bit hydraulics [6]. Its coefficients *a*_{1} to *a*_{8} are obtained by multiple regression on offset-well data:");
  b.equation("ROP = exp( a_{1} + Σ_{j=2}^{8} a_{j} x_{j} )");
  b.p("Warren (1987) extended these concepts to include the effect of imperfect cuttings removal for roller-cone bits [7], and Hareland and Rampersad (1994) developed a model for drag (PDC-type) bits that includes bit wear [8]. These models are physically meaningful, but they require field-specific coefficients, rock-strength data and assumptions that are often not fully satisfied in practice.");
  b.h3("2.2.2 Data-Driven (Machine-Learning) ROP Models");
  b.p("Bilgesu et al. (1997) were among the first to apply artificial neural networks to ROP prediction, showing that an ANN could learn ROP from drilling parameters and formation information [9]. Hegde et al. (2017) analysed ROP prediction with both physics-based and data-driven models and reported that data-driven models, such as random forests, produced more accurate predictions than traditional models on their field data [10]. Soares and Gray (2019) compared analytical ROP models with machine-learning models, including random forests, support vector machines and neural networks, for real-time prediction, and found that the machine-learning models generally provided better predictive capability once sufficient data were available [11]. Barbosa et al. (2019) reviewed the published literature on machine-learning methods for ROP prediction and optimization, and noted that neural networks and ensemble methods were the most frequently used approaches, while also highlighting the importance of data quality and of proper validation on unseen data [12].");
  b.h2("2.3 Existing Methods");
  b.table("Comparison of existing ROP prediction approaches", ["Approach", "Examples", "Strengths", "Limitations"], [
    ["Physics-based / analytical", "Maurer [4], Warren [7]", "Physically meaningful; few inputs", "Need rock strength and simplifying assumptions; limited accuracy"],
    ["Empirical / regression", "Bingham [5], Bourgoyne & Young [6]", "Simple; widely used in industry", "Field-specific coefficients; assume fixed functional form"],
    ["Linear ML regression", "Multiple linear regression", "Fast, interpretable baseline", "Cannot capture nonlinear interactions"],
    ["Tree-based ML", "Decision tree, random forest", "Nonlinear; robust to scaling; give feature importance", "Single trees overfit; forests are less interpretable"],
    ["Kernel methods", "Support vector regression", "Good with moderate data; nonlinear via kernels", "Sensitive to scaling and hyperparameters"],
    ["Neural networks", "ANN / MLP", "Learn complex nonlinear relationships", "Need more data and tuning; ‘black box’"],
  ], [1.6, 1.7, 2.3, 2.6]);
  b.h2("2.4 Research Gap");
  b.p("Although many studies have shown the potential of machine learning for ROP prediction, several gaps remain that are relevant for this project: (i) many studies use a single algorithm without a consistent comparison against a simple baseline on the same data; (ii) data-cleaning and pre-processing steps are often not reported in enough detail to be reproduced; (iii) evaluation is sometimes reported only on training data, without a separate unseen test set; and (iv) there are few open, reproducible student-level workflows in the Pakistani academic context that combine drilling-engineering knowledge with a transparent ML pipeline. This project addresses these gaps by applying a fully documented and reproducible workflow — from raw data cleaning to final model selection — and by comparing five algorithms of increasing complexity under identical conditions using standard statistical metrics and graphical validation.");
}

// =================================================================== CHAPTER 3
function chapter3(b, kind) {
  b.chapter("Methodology");
  b.h2("3.1 Research Design");
  const f = b.nextFig();
  b.p(`This study follows a quantitative, data-driven research design. Historical drilling data are collected, processed and used to train and test several supervised machine-learning algorithms. The overall workflow is: Data Collection → Data Cleaning → Exploratory Data Analysis → Feature Selection → Data Pre-processing → Model Development → Model Training → Model Testing → Performance Evaluation → ROP Prediction. The complete methodology is shown in the flowchart in ${f}.`);
  b.figure("diagram_methodology_flowchart.png", "Proposed methodology flowchart for ROP prediction", 4.9);

  b.h2("3.2 Data Collection");
  b.p("Historical drilling data are collected from the following sources, in order of preference:");
  b.bullets(["Field drilling records (daily drilling reports, mud-logging / real-time surface data), if made available by an operating company through the department.",
    "Open-source drilling datasets, in particular the **Equinor Volve field dataset** [13].", "Published research datasets.", "Well logs and drilling reports.", "Laboratory drilling experiments, if available."]);
  b.h3("3.2.1 Field / Laboratory Data");
  b.p("The primary open-source data source is the Volve field dataset released by Equinor in 2018 for research and education [13]. Volve is an oil field in the Norwegian North Sea, and the released data include real-time drilling data recorded while drilling its wells, containing surface parameters such as WOB, rotary speed, torque, flow rate, standpipe pressure, hook load, bit depth and ROP. Data from one or more wells will be exported to CSV format and the relevant channels will be mapped to the input and output variables in the table below. If field records from a Pakistani operator become available, they will be processed with the same workflow.");
  b.p("To develop and test every step of the pipeline before the real data are finalized, a **synthetic demonstration dataset** was also generated in Python using a Bourgoyne–Young-type multiplicative relationship with random formation layers, measurement noise and deliberately injected data-quality problems (duplicates, missing values, unrealistic values and spikes). This dataset is used only to verify the code and to illustrate the expected form of the results; it is not a substitute for field data.");
  b.table("Input and output variables of the ROP prediction model", ["Variable", "Symbol", "Unit", "Role"], [
    ["Weight on bit", "WOB", "klbf", "Input"], ["Rotary speed", "RPM", "rev/min", "Input"], ["Torque", "T", "kft·lbf", "Input"],
    ["Mud flow rate", "Q", "gpm", "Input"], ["Mud density", "ρ", "ppg", "Input"], ["Standpipe pressure", "SPP", "psi", "Input"],
    ["Bit diameter", "D", "in", "Input"], ["Measured depth", "Depth", "ft", "Input"], ["Rate of penetration", "ROP", "ft/hr", "Output (target)"],
  ], [2.4, 1.3, 1.3, 1.8]);
  b.p("The input vector and the target variable are therefore:");
  b.equation("X = [ WOB, RPM, T, Q, ρ, SPP, D, Depth ],     Y = ROP");

  b.h2("3.3 Data Cleaning and Preparation");
  b.p("Raw drilling data usually contain errors from sensors, data transmission and manual entry. The following steps are applied:");
  b.numbered(["Remove duplicate records.", "Identify missing values in every column.",
    "Handle missing values: rows with missing ROP (target) are removed; missing input values are replaced with the median, which is robust to outliers. To avoid information leakage, the median is calculated from the **training set only** and applied inside the model pipeline (Section 3.6).",
    "Identify physically unrealistic values (e.g. negative WOB, zero RPM while drilling, negative ROP) using the physical limits given in the table below, and treat them as missing.",
    "Detect and treat outliers in ROP using the interquartile-range (IQR) rule.",
    "Ensure all units are consistent (oilfield units are used throughout; metric data are converted, e.g. m/hr × 3.281 = ft/hr, tonnes × 2.2046 = klbf).",
    "Convert categorical variables (e.g. bit type or formation name, if present) to numerical form using one-hot encoding."]);
  b.table("Physical limits used to flag unrealistic values", ["Parameter", "Lower limit", "Upper limit", "Unit"], [
    ["WOB", "0.5", "80", "klbf"], ["RPM", "10", "400", "rev/min"], ["Torque", "0", "60", "kft·lbf"], ["Q", "100", "1500", "gpm"],
    ["ρ (MW)", "8.0", "20.0", "ppg"], ["SPP", "200", "7000", "psi"], ["Bit diameter", "3", "30", "in"], ["ROP", "0.5", "500", "ft/hr"],
  ], [2, 1.5, 1.5, 1.5]);
  b.p("Outliers are identified with the IQR rule, where Q_{1} and Q_{3} are the first and third quartiles. A conservative factor *k* = 3 is used because genuine ROP changes (e.g. drilling breaks) should not be removed:");
  b.equation("IQR = Q_{3} − Q_{1};   outlier if  ROP < Q_{1} − k·IQR  or  ROP > Q_{3} + k·IQR");

  b.h2("3.4 Exploratory Data Analysis (EDA)");
  b.p("EDA is performed to understand the distribution of each parameter and its relationship with ROP. The following graphs are generated: histograms, box plots, scatter plots, the correlation matrix and heatmap, and feature-versus-ROP plots — in particular ROP vs WOB, ROP vs RPM, ROP vs torque, ROP vs depth and ROP vs mud flow rate. A ROP-versus-depth log is also plotted to observe trends with depth and formation changes.");

  b.h2("3.5 Feature Selection");
  b.p("Feature selection identifies the most relevant drilling parameters and avoids unnecessary complexity. The following methods are used:");
  b.bullets(["**Pearson correlation coefficient** — measures the linear relationship between each input *x* and ROP *y*:"]);
  b.equation("r = Σ(x_{i} − x̄)(y_{i} − ȳ) / √[ Σ(x_{i} − x̄)^{2} · Σ(y_{i} − ȳ)^{2} ]");
  b.bullets(["**Mutual information (MI)** — measures any (linear or nonlinear) dependence between an input and ROP; MI = 0 means the variables are independent:"]);
  b.equation("I(X;Y) = Σ Σ p(x,y) · log[ p(x,y) / (p(x) p(y)) ]");
  b.bullets(["**Feature importance** from tree-based models (mean decrease in impurity), and",
    "**Recursive feature elimination with cross-validation (RFECV)**, in which the least important feature is removed repeatedly and the 5-fold cross-validated RMSE of a random forest is monitored for every number of features."]);
  b.p("All feature-selection calculations are performed on the **training set only**, so that the test set remains completely unseen. Highly correlated input pairs (|r| > 0.9) are examined; one of the pair may be removed if it does not improve model performance.");

  b.h2("3.6 Data Pre-processing");
  const fs_ = b.nextFig();
  b.p(`The cleaned dataset is randomly divided into **80% training data** and **20% testing data** (${fs_}). The training set is used to build and tune the models, while the testing set is kept completely separate for the final evaluation. Because the input parameters have very different ranges (e.g. RPM ≈ 100 while SPP ≈ 3000 psi), they are standardized to zero mean and unit standard deviation. The imputer (median) and the scaler are fitted on the training data only and then applied to the test data, inside a single scikit-learn Pipeline (imputer → scaler → model), to avoid information leakage:`);
  b.equation("z = (x − μ) / σ");
  b.figure("diagram_split_cv.png", "80:20 train–test split and 5-fold cross-validation used for hyperparameter tuning", 6.0);

  b.h2("3.7 Mathematical Models");
  b.p("Five supervised regression algorithms are developed, giving a clear progression from traditional regression to machine learning, ensemble learning and deep learning.");
  b.h3("3.7.1 Model 1: Linear Regression (Baseline)");
  b.p("Multiple linear regression assumes a linear relationship between the inputs and ROP. The coefficients β are found by ordinary least squares, i.e. by minimizing the sum of squared errors:");
  b.equation("ŷ = β_{0} + β_{1}x_{1} + β_{2}x_{2} + … + β_{p}x_{p}");
  b.h3("3.7.2 Model 2: Decision Tree Regression");
  b.p("A regression tree divides the input space into rectangular regions by recursive binary splits (e.g. “WOB ≤ 24 klbf?”). At each node, the split that most reduces the mean squared error of the two child nodes is selected, and the prediction for a region is the mean ROP of the training samples in it [15]. Tree depth and minimum samples per split/leaf control overfitting.");
  b.equation("ŷ(x) = (1/|R_{m}|) Σ_{i∈R_{m}} y_{i},   for x in region R_{m}");
  b.h3("3.7.3 Model 3: Random Forest Regression");
  const fRF = b.nextFig();
  b.p(`Random forest is an ensemble of *B* decision trees, each trained on a bootstrap sample of the training data and using a random subset of features at each split (${fRF}). Averaging many decorrelated trees reduces variance and overfitting, which makes random forest well suited to the complex, nonlinear relationship between drilling parameters and ROP [14]:`);
  b.equation("ŷ(x) = (1/B) Σ_{b=1}^{B} T_{b}(x)");
  b.figure("diagram_random_forest.png", "Concept of random forest regression", 5.6);
  b.h3("3.7.4 Model 4: Support Vector Regression (SVR)");
  b.p("SVR finds a function that deviates from the measured ROP by at most ε for as many samples as possible while remaining as flat as possible [16]. Nonlinear relationships are handled with a kernel; the radial basis function (RBF) kernel is used:");
  b.equation("min  ½‖w‖^{2} + C Σ (ξ_{i} + ξ_{i}^{*}),   K(x, x′) = exp(−γ ‖x − x′‖^{2})");
  b.p("where *C* controls the penalty on errors larger than ε, ξ are slack variables and γ controls the width of the RBF kernel.");
  b.h3("3.7.5 Model 5: Artificial Neural Network (ANN)");
  const fA = b.nextFig();
  b.p(`A feed-forward multilayer perceptron is used (${fA}). Each neuron computes a weighted sum of its inputs plus a bias and passes it through an activation function. Hidden layers use the ReLU activation and the output neuron is linear. The weights are learned by back-propagation [18] with the Adam optimizer [19], minimizing the mean squared error; L2 regularization (α) and early stopping are used to prevent overfitting. A network with sufficient hidden neurons can approximate any continuous function [20].`);
  b.equation("a_{j} = f( Σ_{i} w_{ij} x_{i} + b_{j} ),     f(z) = ReLU(z) = max(0, z)");
  b.figure("diagram_ann_architecture.png", "Architecture of the artificial neural network (multilayer perceptron) for ROP prediction", 5.4);

  b.h2("3.8 Model Training and Hyperparameter Tuning");
  b.p("Each model is trained on the training set by providing the input drilling parameters and the measured ROP as target, and allowing the algorithm to adjust its parameters to minimize prediction error. Hyperparameters are optimized with **grid search** combined with **5-fold cross-validation** on the training set, using RMSE as the scoring metric; random search can be used for larger grids. The search spaces are listed below.");
  b.table("Hyperparameter search space for each model", ["Model", "Hyperparameters and values searched"], [
    ["Linear Regression", "None (ordinary least squares)"],
    ["Decision Tree", "max_depth: 4, 6, 8, 10, 14; min_samples_split: 2, 10, 20; min_samples_leaf: 1, 5, 10"],
    ["Random Forest", "n_estimators (number of trees): 100, 300; max_depth: None, 12, 20; min_samples_split: 2, 5; min_samples_leaf: 1, 2"],
    ["SVR (RBF)", "C: 1, 10, 100; γ: scale, 0.05, 0.2; ε: 0.05, 0.1 (on standardized ROP)"],
    ["ANN (MLP)", "hidden layers: (32,16), (64,32), (64,32,16); α: 10^{−4}, 10^{−3}, 10^{−2}; learning rate: 0.001, 0.005; ReLU, Adam, early stopping"],
  ], [1.8, 6.2], { leftAll: true });

  b.h2("3.9 Model Testing and Performance Evaluation");
  b.p("After training, every model predicts ROP for the unseen testing dataset and the predicted values ŷ_{i} are compared with the measured values y_{i} using the following statistical measures:");
  b.p("**Mean Absolute Error (MAE):**"); b.equation("MAE = (1/n) Σ_{i=1}^{n} | y_{i} − ŷ_{i} |");
  b.p("**Mean Squared Error (MSE):**"); b.equation("MSE = (1/n) Σ_{i=1}^{n} ( y_{i} − ŷ_{i} )^{2}");
  b.p("**Root Mean Squared Error (RMSE):**"); b.equation("RMSE = √[ (1/n) Σ_{i=1}^{n} ( y_{i} − ŷ_{i} )^{2} ]");
  b.p("**Coefficient of Determination (R²):**"); b.equation("R^{2} = 1 − Σ( y_{i} − ŷ_{i} )^{2} / Σ( y_{i} − ȳ )^{2}");
  b.p("Lower MAE, MSE and RMSE and an R² closer to 1 indicate better performance. Training time is also recorded. A comparison table of all models is then prepared. The results are reported as measured, without deciding in advance which algorithm will perform best.");

  b.h2("3.10 Blind-Well Test and Final Model Selection");
  b.p("A random 80:20 split of depth-ordered drilling data can give optimistic results, because samples from neighbouring depths fall into both the training and testing sets. As required by the methodology, the selected model must also predict ROP for **previously unseen drilling data**. All trained models are therefore additionally applied to a completely separate well (the *blind well*), which is cleaned with the same procedure but never used for training, tuning or feature selection. The final model is selected with the following criterion, which rewards models that are accurate on the test set *and* generalize to a new well:");
  b.equation("Selection score = ½ ( R^{2}_{test} + R^{2}_{blind} )");
  b.p("The final model is saved (joblib) and documented in a model card together with its input parameters, algorithm and architecture, hyperparameters, performance metrics, training range of every input and prediction plots.");

  b.h2("3.11 Graphical Validation and Feature Importance");
  b.bullets(["**Actual vs predicted ROP** scatter plot with the 1:1 line.", "**Prediction error plot** — distribution of Error = ROP_{actual} − ROP_{predicted}.",
    "**Residual plot** — residuals against predicted ROP, to detect systematic errors.",
    "**Feature importance** bar charts for the Random Forest and Decision Tree models, showing the relative contribution of WOB, RPM, torque, depth, flow rate, mud density and SPP."]);

  b.h2("3.12 Software and Tools");
  b.table("Software and tools used in the project", ["Tool / library", "Purpose"], [
    ["Python 3.11+", "Programming language for the complete workflow"], ["Jupyter Notebook / VS Code / Google Colab", "Development environment"],
    ["pandas, NumPy", "Data loading, cleaning and numerical computation"], ["Matplotlib, Seaborn", "Graphs: histograms, box plots, heatmaps, validation plots"],
    ["scikit-learn", "Pre-processing, feature selection, LR, DT, RF, SVR, MLP, GridSearchCV, metrics"],
    ["TensorFlow / Keras (optional)", "Alternative deeper ANN implementation"], ["joblib", "Saving and loading the final trained model"],
    ["lasio (optional)", "Reading LAS-format well-log files"], ["Microsoft Excel", "Initial inspection of CSV/Excel drilling data"],
    ["Git / GitHub", "Version control and backup of code and results"], ["Mendeley / EndNote", "Reference management"], ["Microsoft Word", "Thesis writing"],
  ], [3, 5], { leftAll: true });

  b.h2("3.13 Experimental (Computational) Procedure");
  b.numbered([
    "Import the drilling data (CSV/Excel) into Python with pandas and rename columns to standard names (WOB, RPM, Torque, Q, MW, SPP, Bit_Dia, Depth, ROP).",
    "Apply the cleaning steps of Section 3.3 and record the number of records removed at each step.",
    "Generate descriptive statistics and the EDA graphs of Section 3.4.",
    "Compute Pearson correlation, mutual information and random-forest importance; finalize the input features.",
    "Split the data 80:20 (random_state = 42 for reproducibility); impute and standardize the inputs using training-set statistics only.",
    "For each of the five models, run grid search with 5-fold cross-validation, select the best hyperparameters and retrain on the full training set.",
    "Predict ROP on the test set; calculate MAE, MSE, RMSE, R² and training time.",
    "Produce the actual-vs-predicted, residual, error-distribution and feature-importance plots.",
    "Apply all models to the blind well (previously unseen drilling data) and calculate the same metrics.",
    "Select the final model with the selection score of Section 3.10 and save it (joblib) with its model card.",
    "Run the automated verification tests (pytest) to confirm the formulas, data split and saved results.",
  ]);

  if (kind === "proposal") {
    b.h2("3.14 Expected Outcomes");
    b.bullets(["A cleaned and documented drilling dataset suitable for ML.", "EDA graphs explaining how each drilling parameter affects ROP.",
      "Five trained and tuned ML models with a comparison table (MAE, RMSE, R², training time).",
      "Validation graphs and a ranking of the most influential drilling parameters.", "A saved final ROP prediction model and reproducible Python code."]);
    b.h2("3.15 Work Plan");
    b.figure("diagram_gantt.png", "Proposed project schedule (Gantt chart)", 6.2);
  }
}

// =================================================================== CHAPTER 4
function chapter4(b) {
  const M = Object.fromEntries(D.models.map((r) => [r[0], r]));
  const names = D.models.map((r) => r[0]);
  const best = D.summary.best_model;
  const f2 = (x) => Number(x).toFixed(2), f3 = (x) => Number(x).toFixed(3);
  // model row indexes: 0 name,1 TrainR2,2 TrainRMSE,3 CV RMSE,4 MAE,5 MSE,6 RMSE,7 R2,8 train time,9 tune time
  b.chapter("Results and Discussion");
  b.note("DRAFT NOTE — demonstration results",
    "All numbers, tables and graphs in this chapter were produced by running the project's Python code on the synthetic demonstration dataset described in Section 3.2.1. They show the expected format and the type of discussion required. Before submission, run the same code on the real field/Volve dataset (python code/rop_pipeline.py --data data/your_file.csv --blind data/second_well.csv); all figures and result files will be regenerated automatically, and the numbers and discussion in this chapter must then be updated.");

  b.h2("4.1 Data Cleaning Results");
  const tC = b.nextTab();
  b.p(`${tC} shows the number of records remaining after each cleaning step, and the following table lists the missing and unrealistic values found in each parameter. Of the ${D.cleaning[0][1]} raw records, ${D.cleaning[D.cleaning.length - 1][1]} (${(100 * D.cleaning[D.cleaning.length - 1][1] / D.cleaning[0][1]).toFixed(1)}%) were retained for modelling. Missing input values were kept and later imputed with the training-set median inside the model pipeline, and ${D.summary.n_outliers} ROP spikes above ${f2(D.summary.outlier_bounds[1])} ft/hr were removed by the 3×IQR rule.`);
  b.table("Records remaining after each data-cleaning step", ["Cleaning step", "Number of records"], D.cleaning, [5, 2]);
  b.table("Missing and physically unrealistic values detected in each parameter", ["Parameter", "Missing values", "Unrealistic values"], D.quality, [2.5, 2, 2]);

  b.h2("4.2 Descriptive Statistics");
  b.table("Descriptive statistics of the cleaned dataset", ["Parameter", "Mean", "Std. dev.", "Min", "Q1 (25%)", "Median", "Q3 (75%)", "Max"],
    D.desc.map((r) => [r[0] === "MW" ? "ρ (ppg)" : r[0] === "Bit_Dia" ? "D (in)" : r[0], ...r.slice(1).map(f2)]), [1.5, 1, 1, 1, 1, 1, 1, 1]);
  b.p("The cleaned data cover depths from about 2,000 ft to 12,000 ft and three hole sections (17½ in, 12¼ in and 8½ in). ROP ranges from about 7 to 134 ft/hr with a right-skewed distribution, which is typical of drilling data: most intervals are drilled at moderate ROP, with fewer fast intervals in soft formations.");

  b.h2("4.3 Exploratory Data Analysis");
  b.figure("eda_histograms.png", "Histograms of the drilling parameters and ROP", 6.2);
  b.figure("eda_boxplots.png", "Box plots of ROP before and after cleaning (left) and standardized input features (right)", 6.2);
  b.p("The box plot of raw ROP shows extreme values caused by spikes, which are removed after cleaning. The standardized feature box plots show that no input contains extreme residual outliers after the physical-limit checks.");
  const fH = b.nextFig();
  b.figure("eda_correlation_heatmap.png", "Correlation matrix heatmap of drilling parameters and ROP", 5.2);
  const c = D.corr_rop;
  b.p(`${fH} shows the Pearson correlation matrix. ROP has the strongest positive correlation with WOB (r = ${f2(c.WOB)}) and torque (r = ${f2(c.Torque)}), and the strongest negative correlation with mud density (r = ${f2(c.MW)}) and depth (r = ${f2(c.Depth)}). These signs agree with drilling theory: higher bit weight increases rock failure, while higher mud weight (overbalance) and the greater strength of deeper, more compacted rock reduce ROP. Strong correlations also exist between some inputs (e.g. depth with mud density and bit diameter, Q with SPP), because these parameters change together from one hole section to the next.`);
  b.figure("eda_feature_vs_rop.png", "ROP versus individual drilling parameters", 6.4);
  b.figure("eda_rop_depth_log.png", "ROP log versus depth", 2.8);
  b.p("The scatter plots show wide scatter for every single parameter, which means that no single parameter can explain ROP alone; the effect of one parameter depends on the others. The ROP–depth log shows cyclic changes caused by changing formation layers superimposed on a general decrease of ROP with depth. These observations justify the use of multivariate, nonlinear machine-learning models.");

  b.h2("4.4 Feature Selection Results");
  b.table("Feature relevance scores for ROP, computed on the training set (sorted by mutual information)", ["Feature", "Pearson r", "|r|", "Mutual information", "RF importance", "RFE rank"],
    D.fs.map((r) => [r[0] === "MW" ? "ρ (MW)" : r[0] === "Bit_Dia" ? "D (Bit_Dia)" : r[0], ...r.slice(1, 5).map(f3), String(r[5])]), [1.8, 1.2, 1, 1.6, 1.5, 1.1]);
  b.figure("feature_selection.png", "Absolute Pearson correlation and mutual information of each feature with ROP", 6.2);
  const nm = { MW: "mud density", Q: "flow rate", SPP: "SPP", Bit_Dia: "bit diameter", Depth: "depth", WOB: "WOB", RPM: "RPM", Torque: "torque" };
  const pairs = D.corr_pairs.map((q) => `${nm[q[0]]} and ${nm[q[1]]} (r = ${q[2].toFixed(2).replace("-", "−")})`).join(", ");
  b.p(`Depth has the highest mutual information with ROP, followed by mud density and WOB. RPM has a modest linear correlation but a high random-forest importance, showing that its effect is nonlinear and interacts with other parameters. The correlation matrix also shows that several input pairs are highly correlated — ${pairs} — because these parameters change together from one hole section to the next.`);
  const rfe = D.rfe, nOpt = D.summary.rfe_optimum_n_features, r8 = rfe[rfe.length - 1], rO = rfe[nOpt - 1];
  const fR = b.nextFig();
  b.figure("feature_rfe.png", "Recursive feature elimination: cross-validated RMSE versus number of features", 4.6);
  b.p(`${fR} shows the RFECV result. The cross-validated RMSE falls sharply up to about three to four features and is almost flat afterwards: the optimum (${nOpt} features, CV RMSE = ${rO[1].toFixed(2)} ft/hr) differs from using all eight features (CV RMSE = ${r8[1].toFixed(2)} ft/hr) by less than the standard deviation between folds (≈ ${r8[2].toFixed(2)} ft/hr). Since removing features gives no statistically meaningful improvement, all eight parameters show non-zero relevance, and tree-based models and the regularized ANN are not seriously affected by multicollinearity, all eight features were retained as model inputs, as proposed in the methodology. The individual coefficients of the linear regression model should, however, not be interpreted physically.`);

  b.h2("4.5 Model Training and Optimum Hyperparameters");
  const bp = D.summary.best_params;
  const fmt = (o) => Object.keys(o).length ? Object.entries(o).map(([k, v]) => `${k} = ${Array.isArray(v) ? "(" + v.join(", ") + ")" : v}`).join("; ") : "Not applicable";
  b.p(`The models were trained on ${D.summary.n_train} samples (80%) and tested on ${D.summary.n_test} samples (20%). The optimum hyperparameters selected by grid search with 5-fold cross-validation are listed below.`);
  b.table("Optimum hyperparameters selected by grid search (5-fold CV)", ["Model", "Optimum hyperparameters"], names.map((n) => [n, fmt(bp[n])]), [2, 6], { leftAll: true });

  b.h2("4.6 Model Performance and Comparison");
  const tP = b.nextTab();
  b.p(`${tP} compares the performance of all models on the unseen test data. The final model is highlighted.`);
  b.table("Performance comparison of the machine-learning models on the test set", ["Model", "MAE (ft/hr)", "MSE", "RMSE (ft/hr)", "R²", "CV RMSE", "Training time (s)"],
    names.map((n) => [n, f2(M[n][4]), f2(M[n][5]), f2(M[n][6]), f3(M[n][7]), f2(M[n][3]), f3(M[n][8])]), [2.2, 1.2, 1.2, 1.3, 1, 1.1, 1.3],
    { highlightRow: names.indexOf(best) });
  b.figure("eval_model_comparison.png", "Comparison of R², RMSE and MAE of the models on the test set (final model highlighted)", 6.4);
  const rank = [...names].sort((a, c2) => M[c2][7] - M[a][7]);
  b.p(`The linear regression baseline achieved R² = ${f3(M["Linear Regression"][7])} and RMSE = ${f2(M["Linear Regression"][6])} ft/hr, confirming that a linear equation cannot fully describe ROP. The single decision tree performed similarly to linear regression (R² = ${f3(M["Decision Tree"][7])}). The three advanced nonlinear models performed best: ${rank[0]} (R² = ${f3(M[rank[0]][7])}, RMSE = ${f2(M[rank[0]][6])} ft/hr), ${rank[1]} (R² = ${f3(M[rank[1]][7])}) and ${rank[2]} (R² = ${f3(M[rank[2]][7])}). Compared with the baseline, the best model reduced RMSE by ${(100 * (1 - M[best][6] / M["Linear Regression"][6])).toFixed(1)}%. The difference between the best models on the test set is small (ΔR² < 0.01), so they can be considered equally accurate on this split; the blind-well test in Section 4.8 is used to separate them. Training times are all below a few seconds, so computational cost is not a limiting factor for this data size.`);

  b.h2("4.7 Overfitting Analysis");
  b.table("Training versus testing performance (overfitting check)", ["Model", "Train R²", "Test R²", "Train RMSE", "Test RMSE", "Gap in R²"],
    names.map((n) => [n, f3(M[n][1]), f3(M[n][7]), f2(M[n][2]), f2(M[n][6]), f3(M[n][1] - M[n][7])]), [2.3, 1.2, 1.2, 1.3, 1.3, 1.1]);
  b.p(`The decision tree (${f3(M["Decision Tree"][1])} vs ${f3(M["Decision Tree"][7])}) and random forest (${f3(M["Random Forest"][1])} vs ${f3(M["Random Forest"][7])}) show the largest gaps between training and testing R², which is typical for deep trees that partly memorize the training data. The ANN, with L2 regularization and early stopping, shows a much smaller gap (${f3(M["ANN (MLP)"][1] - M["ANN (MLP)"][7])}), and linear regression shows almost none because it is too simple to overfit.`);

  b.h2("4.8 Blind-Well Test and Final Model Selection");
  const order = [...names].sort((a, c2) => D.score[c2] - D.score[a]);
  b.p(`All models were applied to the blind well (${D.summary.n_blind} records after cleaning), which was never used for training, tuning or feature selection. The results and the selection score of Section 3.10 are given below.`);
  b.table("Blind-well performance and final model selection score", ["Model", "Test R²", "Blind MAE", "Blind RMSE", "Blind R²", "Selection score"],
    order.map((n) => [n, f3(M[n][7]), f2(BL[n].MAE), f2(BL[n].RMSE), f3(BL[n].R2), f3(D.score[n])]), [2.3, 1.1, 1.2, 1.3, 1.1, 1.4],
    { highlightRow: order.indexOf(best) });
  b.figure("eval_blind_well.png", `Measured and predicted ROP for the blind well (${best})`, 6.0);
  const drop = (n) => f3(M[n][7] - BL[n].R2);
  b.p(`The blind-well test changes the picture considerably. The tree-based models, which were among the best on the random test set, lost most accuracy on the new well (Random Forest R² fell by ${drop("Random Forest")} and the decision tree by ${drop("Decision Tree")}). Because decision trees split on fixed depth thresholds, they partly memorize the depth–formation pattern of the training well, which does not transfer to a well with different formation layers. The smoother models — ANN, SVR and even linear regression — kept R² ≈ ${f2(BL["ANN (MLP)"].R2)} on the blind well, i.e. they generalize better. The ${best} obtained the highest selection score (${f3(D.score[best])}) and was therefore selected as the final ROP prediction model. Its blind-well RMSE of ${f2(BL[best].RMSE)} ft/hr is a more realistic estimate of the error to be expected on a new well than the random-split test RMSE of ${f2(M[best][6])} ft/hr.`);

  b.h2("4.9 Graphical Validation");
  const fAV = b.nextFig();
  b.figure("eval_actual_vs_predicted.png", "Actual versus predicted ROP for each model on the test set", 6.4);
  b.p(`In ${fAV}, points close to the dashed 1:1 line indicate accurate predictions. The linear model shows a curved pattern (under-prediction at high ROP and over-prediction at low ROP), while the random forest, SVR and ANN points are more tightly grouped around the line. All models tend to under-predict the highest ROP values (> 90 ft/hr), because few training samples exist in that range.`);
  b.figure("eval_residuals.png", "Residuals versus predicted ROP", 6.4);
  b.figure("eval_error_distribution.png", "Distribution of prediction errors (Error = ROP_actual − ROP_predicted)", 6.4);
  b.p("The residual plots of the nonlinear models are scattered randomly around zero, with no strong trend, indicating no major systematic bias. The spread of residuals increases with predicted ROP (heteroscedasticity), which is expected because measurement noise in ROP is proportional to its magnitude. The error histograms are approximately centred at zero, and the best models show the narrowest distributions.");
  b.figure("eval_depth_track.png", `Measured and predicted ROP (${best}) versus depth for the test samples`, 2.8);

  b.h2("4.10 Feature Importance Analysis");
  b.figure("eval_feature_importance.png", "Feature importance from the Random Forest and Decision Tree models", 6.2);
  b.p("Both tree-based models rank depth as the most important parameter, followed by WOB and RPM. Depth acts as a proxy for rock strength and compaction, which control how easily the rock is drilled. WOB and RPM are the two parameters that the driller directly controls, which shows that ROP can be improved by optimizing these settings. Mud density, flow rate and SPP have lower importance in this dataset, partly because their information is already contained in depth and hole size. These results agree with the Bourgoyne–Young model, in which formation strength, depth, bit weight and rotary speed are key terms [6].");

  b.h2("4.11 Sample Calculation");
  const W = D.worked;
  const err = W.map((r) => r[8] - r[9]);
  const mae = err.reduce((a, e) => a + Math.abs(e), 0) / err.length;
  const mse = err.reduce((a, e) => a + e * e, 0) / err.length;
  b.p(`To illustrate the calculation of the evaluation metrics, five samples from the test set and the ROP predicted by the ${best} model are shown below.`);
  b.table("Worked example: five test samples and predicted ROP", ["Depth (ft)", "WOB", "RPM", "T", "Q", "ρ", "SPP", "D", "Actual ROP", "Predicted ROP", "Error"],
    W.map((r, i) => [r[0].toFixed(0), f2(r[1]), r[2].toFixed(1), f2(r[3]), r[4].toFixed(0), f2(r[5]), r[6].toFixed(0), r[7], f2(r[8]), f2(r[9]), f2(err[i])]),
    [1.1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.9, 1, 1.1, 0.9], { centerFirst: true });
  b.p(`MAE = (1/5)(${err.map((e) => Math.abs(e).toFixed(2)).join(" + ")}) = **${mae.toFixed(2)} ft/hr**`);
  b.p(`MSE = (1/5)(${err.map((e) => (e * e).toFixed(2)).join(" + ")}) = **${mse.toFixed(2)} (ft/hr)²**,   RMSE = √${mse.toFixed(2)} = **${Math.sqrt(mse).toFixed(2)} ft/hr**`);
  b.p("The same calculations, applied to all test samples, give the values reported in the performance comparison table.");

  b.h2("4.12 Discussion of Findings");
  b.bullets([
    "Nonlinear ML models (ANN, random forest, SVR) predicted ROP considerably better than the linear baseline, confirming the nonlinear nature of ROP.",
    "Ensemble learning (random forest) greatly improved on a single decision tree by reducing variance.",
    "On the random test set the ANN and random forest gave comparable accuracy, but on the blind well the random forest dropped sharply while the ANN remained robust; a random split alone would therefore have led to the wrong model choice.",
    "On the blind well, ANN, SVR and linear regression performed almost equally, which shows that the remaining error is dominated by formation differences that the eight surface parameters cannot fully describe.",
    "Depth (formation strength), WOB and RPM were the most influential parameters, in agreement with classical drilling theory.",
    "Prediction errors increase at very high ROP, where data are scarce; more data from fast-drilling intervals would improve the models.",
  ]);
}

// =================================================================== CHAPTER 5
function chapter5(b) {
  const M = Object.fromEntries(D.models.map((r) => [r[0], r]));
  const best = D.summary.best_model;
  b.chapter("Conclusions and Recommendations");
  b.h2("5.1 Major Findings");
  b.bullets([
    `A complete, reproducible Python workflow for ROP prediction was developed, covering data cleaning, EDA, feature selection, model development, hyperparameter tuning, evaluation and model saving.`,
    `On the random test set, ${TOP_TEST} (R² = ${M[TOP_TEST][7].toFixed(3)}) and the ANN (R² = ${M["ANN (MLP)"][7].toFixed(3)}) were the most accurate models.`,
    `On a blind well never used in training, the ${best} remained robust (R² = ${BL[best].R2.toFixed(3)}, RMSE = ${BL[best].RMSE.toFixed(2)} ft/hr) whereas Random Forest dropped to R² = ${BL["Random Forest"].R2.toFixed(3)}; the ${best} was selected as the final model.`,
    `The linear regression baseline (R² = ${M["Linear Regression"][7].toFixed(3)}) and single decision tree (R² = ${M["Decision Tree"][7].toFixed(3)}) were clearly less accurate.`,
    "Depth, WOB and RPM were identified as the most influential parameters on ROP.",
  ]);
  b.h2("5.2 Conclusions");
  b.p("Machine-learning models can predict the rate of penetration from commonly available surface drilling parameters with good accuracy. The relationship between drilling parameters and ROP is strongly nonlinear, so nonlinear and ensemble models should be preferred over linear regression. A careful data-cleaning procedure, leakage-free pre-processing and evaluation on a separate, unseen well are essential for obtaining reliable and honest performance estimates: models that look best on a random split can generalize poorly to a new well. The selected final model has been saved together with its input parameters, hyperparameters and performance metrics, and can be used to predict ROP for new drilling data from similar wells. **[Update these conclusions with the final results from the real dataset.]**");
  b.h2("5.3 Limitations");
  b.bullets([
    "The results in this draft are based on a synthetic demonstration dataset; final conclusions depend on the real field dataset.",
    "Models trained on one field or well may not generalize to wells with different formations, bit types or drilling practices without retraining.",
    "Important factors such as bit type, bit wear, rock strength (UCS) and lithology were not included as inputs.",
    "A random train–test split gives optimistic results for depth-based data; only one blind well was available for the stricter well-based test.",
    "The ANN and random forest are less interpretable than empirical equations.",
  ]);
  b.h2("5.4 Recommendations");
  b.bullets([
    "Use data from several wells and validate the final model on a completely separate (blind) well.",
    "Add formation/lithology information, rock strength from logs, and bit type and wear as input features.",
    "Use the trained model together with an optimization algorithm to recommend optimum WOB, RPM and flow rate that maximize ROP within operational limits.",
    "Compare the ML models with a calibrated Bourgoyne–Young model on the same data.",
  ]);
  b.h2("5.5 Future Work");
  b.bullets([
    "Test advanced algorithms such as gradient boosting (XGBoost, LightGBM) and recurrent/LSTM neural networks for time-series drilling data.",
    "Use explainable-AI techniques (e.g. SHAP values) to interpret model predictions.",
    "Develop a simple user interface (e.g. a Streamlit web app) that allows engineers to enter drilling parameters and obtain predicted ROP.",
    "Extend the approach to real-time ROP prediction and drilling optimization during operations.",
  ]);
}

// =================================================================== REFERENCES & APPENDIX
function references(b) {
  b.unnumbered("REFERENCES");
  const refs = [
    "J. P. Mitchell and S. Z. Miska, *Fundamentals of Drilling Engineering*, SPE Textbook Series, vol. 12. Richardson, TX: Society of Petroleum Engineers, 2011.",
    "A. T. Bourgoyne Jr., K. K. Millheim, M. E. Chenevert, and F. S. Young Jr., *Applied Drilling Engineering*, SPE Textbook Series, vol. 2. Richardson, TX: Society of Petroleum Engineers, 1986.",
    "R. F. Mitchell, Ed., *Petroleum Engineering Handbook, Vol. II: Drilling Engineering*. Richardson, TX: Society of Petroleum Engineers, 2007.",
    "W. C. Maurer, “The ‘Perfect-Cleaning’ Theory of Rotary Drilling,” *J. Pet. Technol.*, vol. 14, no. 11, pp. 1270–1274, Nov. 1962. DOI: 10.2118/408-PA.",
    "M. G. Bingham, “A New Approach to Interpreting Rock Drillability,” *Oil & Gas Journal*, 1964 (series of articles).",
    "A. T. Bourgoyne Jr. and F. S. Young Jr., “A Multiple Regression Approach to Optimal Drilling and Abnormal Pressure Detection,” *SPE Journal*, vol. 14, no. 04, pp. 371–384, Aug. 1974. DOI: 10.2118/4238-PA.",
    "T. M. Warren, “Penetration-Rate Performance of Roller-Cone Bits,” *SPE Drilling Engineering*, vol. 2, no. 01, pp. 9–18, Mar. 1987. DOI: 10.2118/13259-PA.",
    "G. Hareland and P. R. Rampersad, “Drag-Bit Model Including Wear,” presented at the SPE Latin America/Caribbean Petroleum Engineering Conference, Buenos Aires, 1994. DOI: 10.2118/26957-MS.",
    "H. I. Bilgesu, L. T. Tetrick, U. Altmis, S. Mohaghegh, and S. Ameri, “A New Approach for the Prediction of Rate of Penetration (ROP) Values,” presented at the SPE Eastern Regional Meeting, Lexington, KY, 1997. DOI: 10.2118/39231-MS.",
    "C. Hegde, H. Daigle, H. Millwater, and K. Gray, “Analysis of rate of penetration (ROP) prediction in drilling using physics-based and data-driven models,” *J. Pet. Sci. Eng.*, vol. 159, pp. 295–306, 2017.",
    "C. Soares and K. Gray, “Real-time predictive capabilities of analytical and machine learning rate of penetration (ROP) models,” *J. Pet. Sci. Eng.*, vol. 172, pp. 934–959, 2019.",
    "L. F. F. M. Barbosa, A. Nascimento, M. H. Mathias, and J. A. de Carvalho Jr., “Machine learning methods applied to drilling rate of penetration prediction and optimization – A review,” *J. Pet. Sci. Eng.*, vol. 183, 106332, 2019.",
    "Equinor, “Volve field data set,” Equinor ASA, released 2018. [Online]. Available: https://www.equinor.com/energy/volve-data-sharing",
    "L. Breiman, “Random Forests,” *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001. DOI: 10.1023/A:1010933404324.",
    "L. Breiman, J. H. Friedman, R. A. Olshen, and C. J. Stone, *Classification and Regression Trees*. Belmont, CA: Wadsworth, 1984.",
    "H. Drucker, C. J. C. Burges, L. Kaufman, A. Smola, and V. Vapnik, “Support Vector Regression Machines,” in *Advances in Neural Information Processing Systems 9*, MIT Press, 1997, pp. 155–161.",
    "F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.",
    "D. E. Rumelhart, G. E. Hinton, and R. J. Williams, “Learning representations by back-propagating errors,” *Nature*, vol. 323, pp. 533–536, 1986. DOI: 10.1038/323533a0.",
    "D. P. Kingma and J. Ba, “Adam: A Method for Stochastic Optimization,” in *Proc. 3rd Int. Conf. Learning Representations (ICLR)*, 2015. arXiv:1412.6980.",
    "K. Hornik, M. Stinchcombe, and H. White, “Multilayer feedforward networks are universal approximators,” *Neural Networks*, vol. 2, no. 5, pp. 359–366, 1989.",
  ];
  refs.forEach((r, i) => b.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 300 },
    indent: { left: 567, hanging: 567 }, children: [new TextRun(`[${i + 1}]\t`), ...runs(r)], tabStops: [{ type: TabStopType.LEFT, position: 567 }] })));
  b.p("*Note: verify every reference against the original source and manage them in Mendeley or EndNote, as required by the department.*");
}

function appendix(b) {
  b.unnumbered("APPENDIX A — PROJECT CODE STRUCTURE");
  b.ch = "A"; b.tab = 0; b.fig = 0;
  b.p("The complete code is stored in the project GitHub repository. Running the two commands below regenerates all results and figures used in Chapter 4.");
  b.table("Project files", ["File / folder", "Content"], [
    ["code/generate_synthetic_data.py", "Generates the synthetic demonstration dataset (for testing only)"],
    ["code/rop_pipeline.py", "Complete workflow: cleaning, EDA, feature selection, 5 models, tuning, evaluation, plots, model saving"],
    ["code/make_diagrams.py", "Methodology flowchart and conceptual diagrams"], ["code/verify.py", "Runs all automated tests and re-computes every metric independently"],
    ["tests/test_pipeline.py", "44 automated tests: formulas, cleaning, split, leakage, models, saved model, app pages"],
    ["app/streamlit_app.py", "ROP·AI web application"], ["data/", "Raw, cleaned and blind-well datasets (CSV)"],
    ["figures/", "All graphs and diagrams (PNG)"], ["results/", "Tables of results (CSV/JSON)"], ["models/final_rop_model.joblib", "Saved final ROP prediction model"],
  ], [3, 5], { leftAll: true });
  b.p("**Commands:**  python code/rop_pipeline.py --data data/your_field_data.csv --blind data/your_blind_well.csv   then   python code/verify.py", { align: AlignmentType.LEFT });
  b.unnumbered("APPENDIX B — PROJECT SCHEDULE");
  b.ch = "B"; b.fig = 0;
  b.figure("diagram_gantt.png", "Project schedule (Gantt chart)", 6.2);
  b.unnumbered("APPENDIX C — ROP·AI WEB APPLICATION");
  b.ch = "C"; b.fig = 0;
  b.p("To make the final model usable by drilling engineers and to demonstrate the project, a web application named **ROP·AI** was developed with Streamlit. It loads the trained models and results produced by the pipeline and provides live single-point prediction, a WOB–RPM optimizer, interactive data exploration, model comparison and batch prediction from CSV files. Detailed instructions are given in the separate *ROP·AI User Guide*. The application is started with: streamlit run app/streamlit_app.py");
  b.figure("diagram_app_architecture.png", "Architecture of the ROP·AI system", 6.0);
  b.figure("../docs/screenshots/02_predict.png", "ROP·AI prediction page with live ROP prediction from drilling parameters", 6.2);
  b.figure("../docs/screenshots/03_optimizer.png", "ROP·AI optimizer page showing predicted ROP over WOB and RPM", 6.2);
}

// =================================================================== DOCUMENT
function makeDoc(front, main) {
  const footer = (fmt) => ({ default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) });
  const page = { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 2160, right: 1440 } };
  return new Document({
    features: { updateFields: true },
    creator: "FYP Group", title: TITLE_CASE,
    styles: {
      default: { document: { run: { font: FONT, size: BODY } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 32, bold: true, allCaps: false }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360 }, keepNext: true, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 28, bold: true }, paragraph: { spacing: { before: 300, after: 140 }, keepNext: true, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 220, after: 120 }, keepNext: true, outlineLevel: 2 } },
        { id: "FigCaption", name: "Figure Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 22, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 60, after: 240 } } },
        { id: "TabCaption", name: "Table Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 22, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 120, after: 100 }, keepNext: true } },
      ],
    },
    numbering: { config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 567, hanging: 340 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 567, hanging: 360 } } } }] },
    ] },
    sections: [
      { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } }, footers: footer(), children: front },
      { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } }, footers: footer(), children: main },
    ],
  });
}

async function build() {
  await buildOne("ROP_FYP_Proposal_Ch1-3",
    (f, toc) => { titlePage(f, "proposal"); abstractPage(f, "proposal"); tocPages(f, toc); nomenclature(f); },
    (m) => { chapter1(m); chapter2(m); chapter3(m, "proposal"); references(m); });
  await buildOne("ROP_FYP_Complete_Thesis_Draft",
    (f, toc) => { titlePage(f, "complete"); submittedPage(f); declarationPages(f); abstractPage(f, "complete"); tocPages(f, toc); nomenclature(f); },
    (m) => { chapter1(m); chapter2(m); chapter3(m, "complete"); chapter4(m); chapter5(m); references(m); appendix(m); });
  console.log("Documents written to", __dirname);
}
if (require.main === module) build().catch((e) => { console.error(e); process.exit(1); });
module.exports = { Builder, makeDoc, runs, buildOne, tocPages, TITLE, TITLE_CASE, SUPERVISOR, MEMBERS, BATCH, DATE, D };
