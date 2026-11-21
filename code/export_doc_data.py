"""Collect pipeline results into results/doc_data.json for docs/build_thesis.js."""
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
d = {}
d["cleaning"] = pd.read_csv(R / "cleaning_log.csv").values.tolist()
q = pd.read_csv(R / "data_quality.csv", index_col=0)
d["quality"] = [[i, int(r.iloc[0]), int(r.iloc[1])] for i, r in q.iterrows()]
s = pd.read_csv(R / "descriptive_statistics.csv", index_col=0).round(2)
d["desc"] = [[i] + r.tolist() for i, r in s.iterrows()]
f = pd.read_csv(R / "feature_selection.csv", index_col=0).round(3)
d["fs"] = [[i] + r.tolist() for i, r in f.iterrows()]
m = pd.read_csv(R / "model_comparison.csv", index_col=0)
d["models"] = [[i] + r.round(4).tolist() for i, r in m.iterrows()]
d["model_cols"] = m.columns.tolist()
d["corr_rop"] = pd.read_csv(R / "correlation_matrix.csv", index_col=0).round(2)["ROP"].to_dict()
d["summary"] = json.loads((R / "summary.json").read_text())

# Worked example: first five test samples
df = pd.read_csv(ROOT / "data" / "cleaned_drilling_data.csv")
mdl = joblib.load(ROOT / "models" / "final_rop_model.joblib")
X, y = df[mdl["features"]], df["ROP"]
_, X_te, _, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
pred = mdl["model"].predict(X_te.iloc[:5])
d["worked"] = [[float(r.Depth), float(r.WOB), float(r.RPM), float(r.Torque), float(r.Q), float(r.MW), float(r.SPP),
                float(r.Bit_Dia), round(float(a), 2), round(float(b), 2)]
               for (_, r), a, b in zip(X_te.iloc[:5].iterrows(), y_te.iloc[:5], pred)]
(R / "doc_data.json").write_text(json.dumps(d, indent=1))
print("wrote", R / "doc_data.json")
