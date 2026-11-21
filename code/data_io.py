"""
Reading user datasets: automatic column detection and unit conversion.

Any drilling CSV/Excel file (field records, Volve real-time data, ...) can be used. Each required
field is mapped to one column of the file (guessed automatically from the column names), and its unit
is converted to the oilfield units used by the models:

    Depth ft · WOB klbf · RPM rev/min · Torque kft·lbf · Q gpm · MW ppg · SPP psi · Bit_Dia in · ROP ft/hr
"""
import io
import re

import pandas as pd

FIELDS = ["Depth", "WOB", "RPM", "Torque", "Q", "MW", "SPP", "Bit_Dia", "ROP"]

LABEL = {"Depth": "Depth", "WOB": "Weight on bit (WOB)", "RPM": "Rotary speed (RPM)", "Torque": "Torque",
         "Q": "Flow rate (Q)", "MW": "Mud density (ρ / MW)", "SPP": "Standpipe pressure (SPP)",
         "Bit_Dia": "Bit diameter (D)", "ROP": "Rate of penetration (ROP)"}

# unit -> multiplication factor to the model unit (first entry = model unit)
UNITS = {
    "Depth": {"ft": 1.0, "m": 3.28084},
    "WOB": {"klbf": 1.0, "lbf": 0.001, "tonne (t) / kkgf": 2.20462, "kN": 0.224809},
    "RPM": {"rev/min": 1.0},
    "Torque": {"kft·lbf": 1.0, "ft·lbf": 0.001, "kN·m": 0.737562, "N·m": 0.000737562, "kkgf·m": 7.23301},
    "Q": {"gpm": 1.0, "L/min": 0.264172, "m³/min": 264.172, "m³/s": 15850.3, "bbl/min": 42.0},
    "MW": {"ppg": 1.0, "g/cm³ (SG)": 8.34540, "kg/m³": 0.00834540, "lb/ft³": 0.133681},
    "SPP": {"psi": 1.0, "bar": 14.5038, "kPa": 0.145038, "MPa": 145.038},
    "Bit_Dia": {"in": 1.0, "mm": 0.0393701},
    "ROP": {"ft/hr": 1.0, "m/hr": 3.28084, "ft/min": 60.0, "m/min": 196.850},
}

# keywords used to recognise columns (checked in this order; more specific first)
KEYWORDS = {
    "ROP": ["rop", "rate of penetration", "penetration rate"],
    "WOB": ["wob", "weight on bit", "bit weight"],
    "RPM": ["rpm", "rotary speed", "rotation", "surface rot"],
    "Torque": ["torque", "trq", "tqa"],
    "SPP": ["spp", "standpipe", "stand pipe", "pump pressure"],
    "Q": ["flow", "gpm", "mfi", "pump rate", "l/min", "q"],
    "MW": ["mud weight", "mud density", "density", "mw", "mdi", "ppg"],
    "Bit_Dia": ["bit size", "bit diameter", "bit_dia", "bitdia", "hole size", "diameter"],
    "Depth": ["bit depth", "hole depth", "measured depth", "depth", "md", "dmea", "dbtm"],
}

# unit hints found in column names
UNIT_HINTS = {
    "Depth": [(r"\(m\)|\[m\]|_m\b| m$|metre|meter", "m")],
    "WOB": [(r"kkgf|tonne|\bt\b|\(t\)", "tonne (t) / kkgf"), (r"\bkn\b", "kN"), (r"\blbf\b(?!.*k)", "lbf")],
    "Torque": [(r"kn\.?m|kn·m|knm", "kN·m"), (r"\bn\.?m\b", "N·m"), (r"kkgf", "kkgf·m"), (r"\bft\.?lbf\b(?<!k)", "ft·lbf")],
    "Q": [(r"l/min|lpm", "L/min"), (r"m3/min|m³/min", "m³/min"), (r"m3/s", "m³/s"), (r"bbl", "bbl/min")],
    "MW": [(r"g/cm3|g/cc|sg|g/cm³", "g/cm³ (SG)"), (r"kg/m3|kg/m³", "kg/m³"), (r"lb/ft3", "lb/ft³")],
    "SPP": [(r"\bbar\b", "bar"), (r"kpa", "kPa"), (r"mpa", "MPa")],
    "Bit_Dia": [(r"\bmm\b", "mm")],
    "ROP": [(r"m/h|m/hr|mph", "m/hr"), (r"ft/min", "ft/min"), (r"m/min", "m/min")],
}


def read_any(uploaded) -> pd.DataFrame:
    """Read a CSV / Excel file (path, bytes or Streamlit UploadedFile)."""
    name = getattr(uploaded, "name", str(uploaded)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    data = uploaded.getvalue() if hasattr(uploaded, "getvalue") else None
    if data is not None:
        text = data.decode("utf-8", errors="replace")
        sep = ";" if text.count(";") > text.count(",") else ","
        return pd.read_csv(io.StringIO(text), sep=sep)
    return pd.read_csv(uploaded)


def _norm(c: str) -> str:
    return re.sub(r"\s+", " ", str(c).strip().lower())


def guess_mapping(columns) -> dict:
    """Return {field: column or None}; exact standard names win, then keywords."""
    cols = list(columns)
    mapping, used = {}, set()
    for f in FIELDS:                                   # 1) exact standard names
        hit = next((c for c in cols if _norm(c) == f.lower()), None)
        if hit is not None:
            mapping[f] = hit; used.add(hit)
    for f in KEYWORDS:                                 # 2) keyword search
        if f in mapping:
            continue
        hit = None
        for kw in KEYWORDS[f]:
            for c in cols:
                if c in used:
                    continue
                n = _norm(c)
                ok = (re.search(rf"(^|[^a-z]){re.escape(kw)}([^a-z]|$)", n) if len(kw) <= 3 else kw in n)
                if ok:
                    hit = c; break
            if hit is not None:
                break
        mapping[f] = hit
        if hit is not None:
            used.add(hit)
    return {f: mapping.get(f) for f in FIELDS}


def guess_unit(field: str, column) -> str:
    units = list(UNITS[field])
    if column is None:
        return units[0]
    n = _norm(column)
    for pat, unit in UNIT_HINTS.get(field, []):
        if re.search(pat, n):
            return unit
    return units[0]


def apply_mapping(df: pd.DataFrame, mapping: dict, units: dict, constants: dict | None = None) -> pd.DataFrame:
    """Build a standard dataframe (FIELDS, model units). `constants` gives a fixed value for unmapped fields."""
    constants = constants or {}
    out = pd.DataFrame(index=df.index)
    for f in FIELDS:
        col = mapping.get(f)
        factor = UNITS[f][units.get(f, list(UNITS[f])[0])]
        if col is not None:
            out[f] = pd.to_numeric(df[col], errors="coerce") * factor
        elif f in constants and constants[f] is not None:
            out[f] = float(constants[f]) * factor
        else:
            raise ValueError(f"No column selected for {LABEL[f]}")
    return out.reset_index(drop=True)
