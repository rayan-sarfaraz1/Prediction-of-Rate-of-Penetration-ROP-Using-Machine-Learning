"""Conceptual diagrams for the thesis (flowchart, system schematic, ANN, RF, CV, Gantt)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, Circle, FancyArrowPatch

FIG = Path(__file__).resolve().parents[1] / "figures"
FIG.mkdir(exist_ok=True)
BLUE, LBLUE, ORANGE, LORANGE, AQUA, LAQUA = "#2a78d6", "#dbe8f8", "#eb6834", "#fbe1d6", "#1baf7a", "#d4f1e5"
INK, INK2, GREY, LGREY = "#0b0b0b", "#52514e", "#8a8984", "#efeeea"
plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.dpi": 220, "savefig.bbox": "tight"})


def box(ax, x, y, w, h, text, fc=LBLUE, ec=BLUE, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK, weight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, color=INK2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color=color, lw=1.1))


def flowchart():
    steps = [
        ("Collection of drilling data\n(field records, well logs, open datasets e.g. Volve)", LBLUE, BLUE),
        ("Data cleaning & quality checking\n(duplicates, unit consistency)", LBLUE, BLUE),
        ("Missing-value & outlier treatment\n(median imputation, physical limits, IQR)", LBLUE, BLUE),
        ("Exploratory data analysis\n(histograms, box plots, scatter, heatmap)", LBLUE, BLUE),
        ("Correlation & feature selection\n(Pearson r, mutual information, RF importance)", LBLUE, BLUE),
        ("Train–test split (80 : 20)\n+ standardization (fit on training set only)", LBLUE, BLUE),
        ("MODELS", None, None),
        ("Training & hyperparameter tuning\n(Grid search + 5-fold cross-validation)", LBLUE, BLUE),
        ("Model testing on unseen 20% data\nMAE, MSE, RMSE, R²", LAQUA, AQUA),
        ("Actual vs predicted, residual & error analysis\nFeature importance analysis", LAQUA, AQUA),
        ("Model comparison → Final ROP prediction model\n(saved with inputs, hyperparameters, metrics)", LORANGE, ORANGE),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 10.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, len(steps) * 1.0 + 0.4); ax.axis("off")
    y = len(steps) - 0.1
    prev, model_xs = None, None
    for text, fc, ec in steps:
        if text == "MODELS":
            names = ["Linear\nRegression", "Decision\nTree", "Random\nForest", "SVR\n(RBF)", "ANN\n(MLP)"]
            model_xs = [1.3, 3.15, 5.0, 6.85, 8.7]
            for xx, n in zip(model_xs, names):
                box(ax, xx, y, 1.65, 0.62, n, fc=LORANGE, ec=ORANGE, fs=7.5)
                arrow(ax, 5, prev - 0.33, xx, y + 0.33)
            prev = y; y -= 1.0
            continue
        box(ax, 5, y, 7.6, 0.66, text, fc=fc, ec=ec, fs=7.8)
        if model_xs is not None:
            for xx in model_xs:
                arrow(ax, xx, prev - 0.31, 5, y + 0.34)
            model_xs = None
        elif prev is not None:
            arrow(ax, 5, prev - 0.33, 5, y + 0.34)
        prev = y; y -= 1.0
    fig.savefig(FIG / "diagram_methodology_flowchart.png"); plt.close(fig)


def rop_factors():
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis("off")
    box(ax, 6, 3.5, 2.4, 1.1, "Rate of\nPenetration\n(ROP)", fc=LORANGE, ec=ORANGE, fs=10, bold=True)
    groups = [
        (2.0, 6.0, "Mechanical / operational", "WOB, RPM, Torque,\nbit type & bit wear"),
        (10.0, 6.0, "Hydraulic", "Flow rate Q, SPP,\njet impact, hole cleaning"),
        (2.0, 1.0, "Drilling fluid", "Mud density ρ, viscosity,\nsolids, overbalance"),
        (10.0, 1.0, "Formation / geometric", "Rock strength, depth,\npore pressure, bit diameter D"),
    ]
    for x, y, t, d in groups:
        box(ax, x, y, 3.6, 1.4, f"{t}\n\n{d}", fc=LBLUE, ec=BLUE, fs=8)
        arrow(ax, x + (1.8 if x < 6 else -1.8) * 0.9, y + (-0.7 if y > 3.5 else 0.7) * 0.9,
              6 + (-1.2 if x < 6 else 1.2), 3.5 + (0.55 if y > 3.5 else -0.55))
    fig.savefig(FIG / "diagram_rop_factors.png"); plt.close(fig)


def drilling_system():
    fig, ax = plt.subplots(figsize=(6.6, 6.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    # ground
    ax.add_patch(Rectangle((0, 0), 10, 7.0, fc="#f3eee4", ec="none"))
    for yy, c, lab in [(5.6, "#e9dfcc", "Shale"), (3.8, "#efe6d2", "Sandstone"), (2.0, "#e3d7bf", "Limestone")]:
        ax.add_patch(Rectangle((0, yy - 1.6), 10, 1.6, fc=c, ec="none"))
        ax.text(9.8, yy - 0.8, lab, ha="right", va="center", fontsize=7.5, color=INK2, style="italic")
    ax.plot([0, 10], [7.0, 7.0], color=INK2, lw=1)
    # rig
    ax.add_patch(Polygon([[3.9, 7.0], [4.6, 9.6], [5.4, 9.6], [6.1, 7.0]], closed=True, fc="none", ec=INK2, lw=1.2))
    ax.add_patch(Rectangle((4.5, 9.5), 1.0, 0.25, fc=GREY, ec=INK2))
    ax.text(6.3, 9.3, "Derrick / hoisting\n(controls WOB)", fontsize=7.5, color=INK)
    ax.add_patch(Rectangle((4.7, 7.6), 0.6, 0.35, fc=LBLUE, ec=BLUE))
    ax.text(5.55, 7.75, "Top drive (RPM, torque)", fontsize=7.5, ha="left", va="center", color=INK)
    # wellbore + drill string
    ax.add_patch(Rectangle((4.55, 0.9), 0.9, 6.1, fc="white", ec=INK2, lw=0.8))
    ax.add_patch(Rectangle((4.88, 1.25), 0.24, 6.6, fc=GREY, ec=INK2, lw=0.6))
    ax.add_patch(Rectangle((4.8, 1.25), 0.4, 1.3, fc="#6f6e69", ec=INK2, lw=0.6))
    ax.text(5.65, 1.9, "BHA / drill collars", fontsize=7.5, color=INK)
    ax.add_patch(Polygon([[4.6, 1.25], [5.4, 1.25], [5.0, 0.85]], closed=True, fc=ORANGE, ec=INK2))
    ax.text(5.65, 0.95, "Bit (diameter D) → ROP", fontsize=7.5, color=INK, weight="bold")
    # mud circulation
    ax.add_patch(Rectangle((0.6, 7.0), 1.6, 0.8, fc=LBLUE, ec=BLUE)); ax.text(1.4, 7.4, "Mud pits", ha="center", fontsize=7.5)
    ax.add_patch(Circle((2.9, 8.5), 0.35, fc=LBLUE, ec=BLUE)); ax.text(2.9, 9.05, "Mud pump\n(Q, SPP)", ha="center", fontsize=7.5)
    arrow(ax, 1.6, 7.8, 2.6, 8.35, BLUE); arrow(ax, 3.25, 8.5, 4.7, 7.85, BLUE)
    arrow(ax, 5.0, 6.6, 5.0, 2.8, BLUE)
    ax.text(3.9, 4.6, "Mud down\ndrill pipe", fontsize=7, color=BLUE, ha="center")
    arrow(ax, 4.7, 1.4, 4.7, 6.8, ORANGE); arrow(ax, 5.3, 1.4, 5.3, 6.8, ORANGE)
    ax.text(6.0, 4.6, "Mud + cuttings\nup annulus\n(density ρ)", fontsize=7, color=ORANGE)
    arrow(ax, 4.5, 7.05, 2.2, 7.3, ORANGE)
    ax.text(0.2, 6.5, "Depth increases ↓", fontsize=7.5, color=INK2)
    fig.savefig(FIG / "diagram_drilling_system.png"); plt.close(fig)


def ann():
    layers = [("Input layer\n8 features\n", ["WOB", "RPM", "Torque", "Q", "ρ", "SPP", "D", "Depth"]),
              ("Hidden layer 1\n64 neurons\nReLU", [""] * 7),
              ("Hidden layer 2\n32 neurons\nReLU", [""] * 6),
              ("Hidden layer 3\n16 neurons\nReLU", [""] * 4),
              ("Output layer\n1 neuron\nlinear", ["ROP"])]
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    ax.set_xlim(-1.2, 8.4); ax.set_ylim(-0.9, 8.6); ax.set_aspect("equal"); ax.axis("off")
    S = 1.8
    pos = []
    for i, (title, nodes) in enumerate(layers):
        n = len(nodes); ys = [4 + (n - 1) / 2 - k for k in range(n)]
        pos.append([(i * S, y) for y in ys])
        ax.text(i * S, 8.45, title, ha="center", va="center", fontsize=7.8, color=INK)
    for a, b in zip(pos[:-1], pos[1:]):
        for (x1, y1) in a:
            for (x2, y2) in b:
                ax.plot([x1, x2], [y1, y2], color="#c9c8c2", lw=0.4, zorder=1)
    for i, (title, nodes) in enumerate(layers):
        fc, ec = (LBLUE, BLUE) if i == 0 else (LORANGE, ORANGE) if i == len(layers) - 1 else (LAQUA, AQUA)
        for (x, y), lab in zip(pos[i], nodes):
            ax.add_patch(Circle((x, y), 0.2, fc=fc, ec=ec, lw=1.1, zorder=3))
            if lab:
                ax.text(x - 0.3 if i == 0 else x + 0.3, y, lab, ha="right" if i == 0 else "left", va="center", fontsize=7.5)
        if 0 < i < len(layers) - 1:
            ax.text(i * S, pos[i][-1][1] - 0.55, "⋮", ha="center", fontsize=11, color=INK2)
    ax.text(2 * S, -0.7, "Weights updated by back-propagation (Adam optimizer) to minimize mean squared error",
            ha="center", fontsize=7.5, color=INK2)
    fig.savefig(FIG / "diagram_ann_architecture.png"); plt.close(fig)


def random_forest():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
    box(ax, 6, 5.4, 4.4, 0.7, "Training data (n samples × 8 features)", fs=8)
    for k, x in enumerate([2, 6, 10]):
        arrow(ax, 6, 5.03, x, 4.45)
        # tree
        nodes = [(x, 3.9), (x - 0.8, 3.0), (x + 0.8, 3.0), (x - 1.2, 2.1), (x - 0.4, 2.1), (x + 0.4, 2.1), (x + 1.2, 2.1)]
        for (a, b) in [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]:
            ax.plot([nodes[a][0], nodes[b][0]], [nodes[a][1], nodes[b][1]], color=INK2, lw=0.8)
        for j, (nx, ny) in enumerate(nodes):
            ax.add_patch(Circle((nx, ny), 0.18, fc=LAQUA if j < 3 else LORANGE, ec=AQUA if j < 3 else ORANGE, zorder=3))
        ax.text(x, 1.55, f"Tree {k + 1 if k < 2 else 'B'} → ŷ{k + 1 if k < 2 else '_B'}", ha="center", fontsize=7.5)
        arrow(ax, x, 1.35, 6, 0.85)
    ax.text(6.2, 4.7, "random bootstrap samples", fontsize=6.8, color=INK2, ha="left")
    ax.text(8.0, 3.0, "…", fontsize=16, color=INK2, ha="center")
    box(ax, 6, 0.5, 5.6, 0.6, "Final ROP = average of all tree predictions  ŷ = (1/B) Σ ŷb", fc=LORANGE, ec=ORANGE, fs=8)
    fig.savefig(FIG / "diagram_random_forest.png"); plt.close(fig)


def split_cv():
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.6); ax.axis("off")
    ax.add_patch(Rectangle((0.5, 5.6), 7.2, 0.6, fc=LBLUE, ec=BLUE)); ax.text(4.1, 5.9, "Training set (80%)", ha="center", va="center", fontsize=8)
    ax.add_patch(Rectangle((7.7, 5.6), 1.8, 0.6, fc=LORANGE, ec=ORANGE)); ax.text(8.6, 5.9, "Test (20%)", ha="center", va="center", fontsize=8)
    ax.text(8.6, 5.2, "kept unseen until\nfinal evaluation", ha="center", va="top", fontsize=6.8, color=INK2)
    w = 7.2 / 5
    for f in range(5):
        y = 4.4 - f * 0.85
        for k in range(5):
            val = k == f
            ax.add_patch(Rectangle((0.5 + k * w, y), w, 0.6, fc=LAQUA if val else "white", ec=AQUA if val else BLUE, lw=0.9))
        ax.text(0.4, y + 0.3, f"Fold {f + 1}", ha="right", va="center", fontsize=7.5)
    ax.text(4.1, 0.25, "5-fold cross-validation on the training set (green = validation fold) for hyperparameter tuning",
            ha="center", fontsize=7.3, color=INK2)
    fig.savefig(FIG / "diagram_split_cv.png"); plt.close(fig)


def gantt():
    tasks = [("Literature review", 0, 6), ("Data collection & understanding", 3, 6),
             ("Data cleaning & EDA", 7, 5), ("Feature selection & pre-processing", 11, 3),
             ("Model development & tuning", 13, 7), ("Testing, evaluation & comparison", 19, 4),
             ("Thesis writing (Ch. 1–5)", 6, 22), ("Presentation / viva preparation", 26, 4)]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for i, (t, s, d) in enumerate(tasks):
        ax.barh(i, d, left=s, height=0.55, color=ORANGE if "Thesis" in t or "viva" in t else BLUE)
    ax.set_yticks(range(len(tasks))); ax.set_yticklabels([t[0] for t in tasks], fontsize=8)
    ax.invert_yaxis(); ax.set_xlabel("Week", fontsize=8.5); ax.set_xlim(0, 30)
    ax.set_xticks(range(0, 31, 2)); ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(axis="x", color="#e6e5e1", lw=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Proposed project schedule (≈ 30 weeks)", fontsize=10)
    fig.savefig(FIG / "diagram_gantt.png"); plt.close(fig)


def app_architecture():
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.set_xlim(0, 15); ax.set_ylim(0, 7); ax.axis("off")
    box(ax, 1.6, 5.2, 2.8, 1.2, "Drilling data\n(CSV: field / Volve)", fs=8)
    box(ax, 5.4, 5.2, 3.2, 1.2, "rop_pipeline.py\nclean · EDA\ntrain · tune", fc=LAQUA, ec=AQUA, fs=7.5)
    box(ax, 9.6, 6.0, 3.4, 0.8, "models/*.joblib\n(5 trained models)", fc=LGREY, ec=GREY, fs=7.5)
    box(ax, 9.6, 4.6, 3.4, 0.8, "results/*.csv\nfigures/*.png", fc=LGREY, ec=GREY, fs=7.5)
    box(ax, 13.2, 5.3, 2.8, 1.4, "Thesis builder\n(Word documents)", fc=LGREY, ec=GREY, fs=7.5)
    box(ax, 7.5, 2.0, 5.6, 1.5, "ROP·AI web app (Streamlit)\nPredict · Optimizer · Explorer\nResults · Batch · About",
        fc=LORANGE, ec=ORANGE, fs=8)
    box(ax, 13.2, 2.0, 2.8, 1.2, "User / examiner\n(web browser)", fs=8)
    box(ax, 1.6, 2.0, 2.8, 1.2, "New CSV upload\n(batch prediction)", fs=8)
    arrow(ax, 3.0, 5.2, 3.8, 5.2); arrow(ax, 7.0, 5.4, 7.9, 5.9); arrow(ax, 7.0, 5.0, 7.9, 4.7)
    arrow(ax, 11.3, 5.0, 11.8, 5.2); arrow(ax, 9.0, 5.6, 8.2, 2.75); arrow(ax, 9.6, 4.2, 9.0, 2.75)
    arrow(ax, 10.3, 2.0, 11.8, 2.0); arrow(ax, 11.8, 1.7, 10.3, 1.7); arrow(ax, 3.0, 2.0, 4.7, 2.0)
    fig.savefig(FIG / "diagram_app_architecture.png"); plt.close(fig)


def actor(ax, x, y, label):
    ax.add_patch(Circle((x, y + 0.55), 0.18, fc="white", ec=INK2, lw=1.2))
    ax.plot([x, x], [y + 0.37, y - 0.1], color=INK2, lw=1.2)
    ax.plot([x - 0.3, x + 0.3], [y + 0.2, y + 0.2], color=INK2, lw=1.2)
    ax.plot([x, x - 0.25], [y - 0.1, y - 0.5], color=INK2, lw=1.2); ax.plot([x, x + 0.25], [y - 0.1, y - 0.5], color=INK2, lw=1.2)
    ax.text(x, y - 0.75, label, ha="center", va="top", fontsize=7.5, color=INK)


def use_case_diagram():
    from matplotlib.patches import Ellipse
    fig, ax = plt.subplots(figsize=(7.4, 5.6))
    ax.set_xlim(0, 15); ax.set_ylim(0, 11.5); ax.axis("off")
    ax.add_patch(FancyBboxPatch((3.2, 0.3), 8.6, 10.8, boxstyle="round,pad=0.02,rounding_size=0.2", fc="#fafaf8", ec=INK2, lw=1))
    ax.text(7.5, 10.75, "ROP·AI system", ha="center", fontsize=9, weight="bold", color=INK)
    ucs = [(5.4, 9.7, "UC-1 Load / upload\ndrilling data"), (9.6, 9.7, "UC-2 Train, tune &\nevaluate models"),
           (5.4, 8.1, "UC-3 Explore data\n(EDA)"), (9.6, 8.1, "UC-4 Run blind-well test\n& select final model"),
           (5.4, 6.5, "UC-5 Predict ROP\n(single point)"), (9.6, 6.5, "UC-6 Optimize\nWOB & RPM"),
           (5.4, 4.9, "UC-7 Batch prediction\nfrom CSV"), (9.6, 4.9, "UC-8 View model\nresults"),
           (5.4, 3.3, "UC-9 Download reports,\nmodel & figures"), (9.6, 3.3, "UC-10 Generate thesis\n& reports"),
           (7.5, 1.5, "UC-11 Run verification tests")]
    for x, y, t in ucs:
        ax.add_patch(Ellipse((x, y), 3.7, 1.15, fc=LBLUE, ec=BLUE, lw=1.1)); ax.text(x, y, t, ha="center", va="center", fontsize=6.8)
    actor(ax, 1.3, 8.2, "Drilling engineer\n/ end user"); actor(ax, 1.3, 3.6, "Examiner /\nsupervisor")
    actor(ax, 13.7, 8.2, "Student /\nresearcher"); actor(ax, 13.7, 3.6, "LibreOffice /\nfile system")
    L = lambda a, b: ax.plot([a[0], b[0]], [a[1], b[1]], color=GREY, lw=0.8, zorder=0)
    for uc in [(3.55, 8.1), (3.55, 6.5), (3.55, 4.9), (3.55, 9.7)]: L((1.6, 8.3), uc)
    for uc in [(3.55, 3.3), (3.55, 4.9), (5.4, 0.95 + 0.0)]: pass
    for uc in [(3.55, 3.3), (7.8, 4.9), (3.55, 6.5)]: L((1.6, 3.7), uc)
    for uc in [(11.45, 9.7), (11.45, 8.1), (11.45, 3.3), (9.3, 1.5)]: L((13.4, 8.3), uc)
    L((13.4, 3.7), (11.45, 3.3))
    fig.savefig(FIG / "diagram_use_case.png"); plt.close(fig)


def dfd():
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
    proc = lambda x, y, t: (ax.add_patch(Circle((x, y), 0.95, fc=LAQUA, ec=AQUA, lw=1.2)), ax.text(x, y, t, ha="center", va="center", fontsize=6.8))
    store = lambda x, y, t: (ax.plot([x - 1.4, x + 1.4], [y + 0.42, y + 0.42], color=INK2, lw=1), ax.plot([x - 1.4, x + 1.4], [y - 0.42, y - 0.42], color=INK2, lw=1),
                             ax.plot([x - 1.4, x - 1.4], [y - 0.42, y + 0.42], color=INK2, lw=1), ax.text(x, y, t, ha="center", va="center", fontsize=6.8))
    box(ax, 1.3, 6.8, 2.2, 1.0, "Drilling data\nsource (CSV)", fs=7)
    proc(4.4, 6.8, "1.0\nClean &\nvalidate"); proc(7.6, 6.8, "2.0\nEDA &\nfeature sel."); proc(10.8, 6.8, "3.0\nTrain &\ntune")
    proc(14.0, 6.8, "4.0\nEvaluate &\nselect")
    store(7.6, 4.5, "D1 data/\n(cleaned CSV)"); store(10.8, 4.5, "D2 models/\n(.joblib)"); store(14.0, 4.5, "D3 results/\n+ figures/")
    proc(10.8, 1.9, "5.0\nROP·AI\nweb app"); proc(14.0, 1.9, "6.0\nBuild\nreports")
    box(ax, 6.0, 1.9, 2.6, 1.0, "User (browser)", fs=7); box(ax, 1.6, 1.9, 2.6, 1.0, "Documents\n(Word + PDF)", fs=7, fc=LORANGE, ec=ORANGE)
    for a, b in [((2.4, 6.8), (3.45, 6.8)), ((5.35, 6.8), (6.65, 6.8)), ((8.55, 6.8), (9.85, 6.8)), ((11.75, 6.8), (13.05, 6.8)),
                 ((4.6, 5.9), (6.6, 4.75)), ((10.8, 5.85), (10.8, 4.85)), ((14.0, 5.85), (14.0, 4.85)), ((10.8, 4.15), (10.8, 2.85)),
                 ((12.9, 4.3), (11.6, 2.6)), ((14.0, 4.15), (14.0, 2.85)), ((9.85, 1.75), (7.3, 1.75)), ((7.3, 2.05), (9.85, 2.05)),
                 ((13.05, 1.4), (2.9, 1.4))]:
        arrow(ax, *a, *b)
    ax.text(8.55, 2.35, "inputs / CSV", fontsize=6.3, color=INK2, ha="center"); ax.text(8.55, 1.35, "predictions, charts", fontsize=6.3, color=INK2, ha="center", va="top")
    fig.savefig(FIG / "diagram_dfd.png"); plt.close(fig)


if __name__ == "__main__":
    flowchart(); rop_factors(); drilling_system(); ann(); random_forest(); split_cv(); gantt(); app_architecture(); use_case_diagram(); dfd()
    print("diagrams saved to", FIG)
