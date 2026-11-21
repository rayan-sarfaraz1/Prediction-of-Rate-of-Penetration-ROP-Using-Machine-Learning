"""
Runs the automated test-suite and an independent re-computation of all reported metrics,
and writes results/verification.json (used by code/reports/build_verification.js).

Usage:  python code/verify.py
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
xml_path = RES / "pytest_report.xml"

proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/", f"--junitxml={xml_path}"],
                      cwd=ROOT, capture_output=True, text=True)
tests = []
for tc in ET.parse(xml_path).getroot().iter("testcase"):
    failed = tc.find("failure") is not None or tc.find("error") is not None
    tests.append({"name": tc.get("name"), "time": round(float(tc.get("time", 0)), 3),
                  "status": "FAIL" if failed else "PASS"})

# Independent re-computation of the reported test metrics from the saved predictions (plain NumPy)
pred = pd.read_csv(RES / "test_predictions.csv")
cmp_ = pd.read_csv(RES / "model_comparison.csv", index_col=0)
recompute = []
for m in cmp_.index:
    y, p = pred["ROP_actual"].values, pred[f"pred_{m}"].values
    e = y - p
    mine = {"MAE": np.abs(e).mean(), "RMSE": np.sqrt((e ** 2).mean()), "R2": 1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()}
    rep = {"MAE": cmp_.loc[m, "Test MAE"], "RMSE": cmp_.loc[m, "Test RMSE"], "R2": cmp_.loc[m, "Test R2"]}
    recompute.append({"model": m, **{f"{k}_reported": float(rep[k]) for k in mine},
                      **{f"{k}_recomputed": float(mine[k]) for k in mine},
                      "max_abs_diff": float(max(abs(rep[k] - mine[k]) for k in mine))})

out = {"date": date.today().isoformat(), "python": sys.version.split()[0], "n_tests": len(tests),
       "n_pass": sum(t["status"] == "PASS" for t in tests), "tests": tests, "recompute": recompute,
       "pytest_tail": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""}
(RES / "verification.json").write_text(json.dumps(out, indent=1))
print(f"{out['n_pass']}/{out['n_tests']} tests passed; max metric difference = "
      f"{max(r['max_abs_diff'] for r in recompute):.2e}")
sys.exit(0 if out["n_pass"] == out["n_tests"] else 1)
