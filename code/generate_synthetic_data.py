"""
Generate a SYNTHETIC drilling dataset for demonstrating the ROP workflow.

IMPORTANT: This data is NOT real field data. It is generated from a
physics-inspired relationship (loosely following Bourgoyne & Young, 1974)
so that the full pipeline (cleaning -> EDA -> ML -> evaluation) can be built
and tested before the real dataset (e.g. Equinor Volve or field records) is
available. All thesis results produced from this file must be replaced with
results from the real dataset.

Units (oilfield):
    Depth  ft        WOB   klbf       RPM   rev/min
    Torque kft.lbf   Q     gpm        MW    ppg (mud density, rho)
    SPP    psi       Bit_Dia in       ROP   ft/hr
"""
import numpy as np
import pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "synthetic_drilling_data_raw.csv"
OUT_BLIND = DATA / "synthetic_blind_well.csv"


def generate(n: int = 3000, seed: int = 42, inject: bool = True) -> pd.DataFrame:
    RNG = np.random.default_rng(seed)
    depth = np.sort(RNG.uniform(2000, 12000, n))

    # Hole sections / bit sizes
    bit = np.where(depth < 4000, 17.5, np.where(depth < 9000, 12.25, 8.5))

    # Lithology layers -> formation drillability (hardness) factor
    layer_tops = np.arange(2000, 12001, 750)
    layer_drill = RNG.uniform(0.6, 1.4, len(layer_tops))
    idx = np.clip(np.searchsorted(layer_tops, depth, side="right") - 1, 0, len(layer_tops) - 1)
    drillability = layer_drill[idx]

    wob = np.select(
        [bit == 17.5, bit == 12.25],
        [RNG.uniform(15, 35, n), RNG.uniform(15, 40, n)],
        RNG.uniform(10, 30, n),
    )
    rpm = RNG.uniform(60, 180, n)
    q = np.select(
        [bit == 17.5, bit == 12.25],
        [RNG.uniform(800, 1100, n), RNG.uniform(600, 900, n)],
        RNG.uniform(350, 600, n),
    )
    mw = 8.8 + 0.00035 * depth + RNG.normal(0, 0.25, n)
    pore_ppg = 8.6 + 0.0003 * depth
    spp = 0.015 * q ** 1.8 * (mw / 10) * (1 + depth / 20000) + RNG.normal(0, 120, n)
    torque = 0.035 * wob * bit * (1 + depth / 30000) * (1 / drillability) ** 0.3 + RNG.normal(0, 0.8, n)

    # Physics-inspired ROP model (multiplicative, Bourgoyne-Young style)
    rop = (
        80
        * drillability
        * ((wob / bit) / 2.0) ** 0.9
        * (rpm / 100) ** 0.6
        * np.exp(-1.2e-4 * (depth - 2000))
        * np.exp(-0.35 * (mw - pore_ppg))
        * (q / (bit * 60)) ** 0.3
        * RNG.lognormal(0, 0.12, n)
    )

    df = pd.DataFrame({
        "Depth": depth.round(1),
        "WOB": wob.round(2),
        "RPM": rpm.round(1),
        "Torque": torque.round(2),
        "Q": q.round(1),
        "MW": mw.round(2),
        "SPP": spp.round(0),
        "Bit_Dia": bit,
        "ROP": rop.round(2),
    })

    if not inject:
        return df
    # ---- Inject realistic data-quality problems (to demonstrate cleaning) ----
    # 1) Duplicate records
    dup = df.sample(40, random_state=1)
    df = pd.concat([df, dup], ignore_index=True)
    # 2) Missing values (~2% in selected columns)
    for col in ["WOB", "RPM", "Torque", "Q", "SPP"]:
        miss = RNG.choice(len(df), int(0.02 * len(df)), replace=False)
        df.loc[miss, col] = np.nan
    # 3) Physically unrealistic values (sensor errors)
    bad = RNG.choice(len(df), 25, replace=False)
    df.loc[bad[:10], "WOB"] = -5.0
    df.loc[bad[10:18], "RPM"] = 0.0
    df.loc[bad[18:], "ROP"] = -1.0
    # 4) Spikes / outliers in ROP
    spikes = RNG.choice(len(df), 30, replace=False)
    df.loc[spikes, "ROP"] = df.loc[spikes, "ROP"] * RNG.uniform(4, 7, 30)

    return df.sample(frac=1, random_state=7).reset_index(drop=True)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    data.to_csv(OUT, index=False)
    print(f"Saved {len(data)} rows -> {OUT}")
    # A separate "blind" well (different random formation layers), never used in training:
    blind = generate(n=800, seed=2026, inject=False)
    blind.to_csv(OUT_BLIND, index=False)
    print(f"Saved {len(blind)} rows -> {OUT_BLIND}")
