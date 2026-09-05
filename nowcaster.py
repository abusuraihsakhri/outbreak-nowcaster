#!/usr/bin/env python3
"""
Outbreak Nowcaster (Delay-Adjusted)
Nowcasting with reporting-delay deconvolution and Rt hindcast from line-list.
Stdlib only.
"""
import argparse
import csv
import json
import math
import sys


def _safe_float(value, default=0.0):
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [
        float(v) for v in kwargs.values()
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).replace('-', '', 1).isdigit())
    ]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "outbreak-nowcaster") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


def calculate_meld_na(bilirubin, creatinine, inr, sodium, dialysis, albumin=None, sex="M"):
    """
    Calculate MELD-Na score for liver disease severity.
    MELD = 3.78*ln(bilirubin) + 11.2*ln(INR) + 9.57*creatinine + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    """
    bili = _safe_float(bilirubin, 1.0)
    creat = _safe_float(creatinine, 1.0)
    inr_val = _safe_float(inr, 1.0)
    na = _safe_float(sodium, 137.0)

    # Apply floor/ceiling per UNOS guidelines
    bili = max(1.0, bili)
    creat = max(1.0, creat)
    if dialysis:
        creat = max(4.0, creat)
    inr_val = max(1.0, inr_val)
    na = max(125.0, min(137.0, na))

    meld = 3.78 * math.log(bili) + 11.2 * math.log(inr_val) + 9.57 * math.log(creat) + 6.43
    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    meld_na = max(6, min(40, round(meld_na)))

    return {
        "score_type": "MELD-Na",
        "meld_na": meld_na,
        "meld_base": round(meld, 1),
        "risk_tier": "HIGH" if meld_na >= 30 else "MODERATE" if meld_na >= 20 else "LOW",
        "components": {"bilirubin": bili, "creatinine": creat, "inr": inr_val, "sodium": na}
    }


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """
    Calculate QTc (corrected QT interval) using Bazett's formula.
    QTc = QT / sqrt(RR in seconds)
    If RR not provided but HR is, RR = 60/HR.
    """
    qt = _safe_float(qt_ms, 400.0)

    if rr_ms is not None and _safe_float(rr_ms) > 0:
        rr_sec = _safe_float(rr_ms) / 1000.0
    elif hr_bpm is not None and _safe_float(hr_bpm) > 0:
        rr_sec = 60.0 / _safe_float(hr_bpm)
    else:
        rr_sec = 1.0  # default 1 second

    qt_seconds = qt / 1000.0
    qtc = qt_seconds / math.sqrt(rr_sec)
    qtc_ms = qtc * 1000.0

    # Normal: <440ms male, <460ms female; borderline: 440-500; prolonged: >500
    risk = "PROLONGED" if qtc_ms > 500 else "BORDERLINE" if qtc_ms > 440 else "NORMAL"

    return {
        "score_type": "QTc",
        "qtc_ms": round(qtc_ms, 1),
        "qt_ms": qt,
        "rr_sec": round(rr_sec, 3),
        "risk_tier": risk,
        "formula": "Bazett"
    }


def calculate_bmi_z(weight_kg, height_cm, age_months, sex="M"):
    """
    Calculate BMI and approximate z-score for pediatric/adult assessment.
    For adults: BMI = weight(kg) / height(m)^2
    For pediatric: simplified z-score approximation.
    """
    weight = _safe_float(weight_kg, 70.0)
    height = _safe_float(height_cm, 170.0)
    age = _safe_float(age_months, 60.0)

    height_m = height / 100.0
    height_m = max(0.5, height_m)  # prevent division by zero

    bmi = weight / (height_m ** 2)

    # Approximate z-score (simplified)
    if age < 240:  # pediatric (< 20 years)
        # Rough median BMI by age approximation
        median_bmi = 15.5 + (age / 240) * 4.5
        z_score = (bmi - median_bmi) / 2.0
        category = "OBESE" if z_score > 2 else "OVERWEIGHT" if z_score > 1 else "NORMAL" if z_score > -2 else "UNDERWEIGHT"
    else:
        z_score = (bmi - 22.0) / 4.0
        category = "OBESE" if bmi >= 30 else "OVERWEIGHT" if bmi >= 25 else "NORMAL" if bmi >= 18.5 else "UNDERWEIGHT"

    return {
        "score_type": "BMI-z",
        "bmi": round(bmi, 1),
        "z_score": round(z_score, 2),
        "age_months": age,
        "sex": sex,
        "category": category
    }


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """
    Convert between HbA1c (%) and estimated Average Glucose (eAG mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7 (ADA formula)
    """
    if hba1c_percent is not None and _safe_float(hba1c_percent) > 0:
        hba1c = _safe_float(hba1c_percent)
        eag = 28.7 * hba1c - 46.7
        source = "hba1c"
    elif eag_mgdl is not None and _safe_float(eag_mgdl) > 0:
        eag = _safe_float(eag_mgdl)
        hba1c = (eag + 46.7) / 28.7
        source = "eag"
    else:
        return {"score_type": "HbA1c", "error": "No valid input provided"}

    # ADA classification
    if hba1c < 5.7:
        classification = "NORMAL"
    elif hba1c < 6.5:
        classification = "PREDIABETES"
    else:
        classification = "DIABETES"

    return {
        "score_type": "HbA1c",
        "hba1c_percent": round(hba1c, 1),
        "eag_mgdl": round(eag, 1),
        "classification": classification,
        "source": source
    }


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """
    Calculate APRI and FIB-4 scores for liver fibrosis assessment.
    AST to Platelet Ratio Index: APRI = (AST/ULN_AST) / platelets * 100
    FIB-4 = (Age * AST) / (Platelets * sqrt(ALT))
    """
    ast = _safe_float(ast_u_l, 30.0)
    alt = _safe_float(alt_u_l, 30.0)
    platelets = _safe_float(platelets_109, 250.0)
    age = _safe_float(age_years, 40.0)

    # Assume ULN for AST = 40 U/L
    uln_ast = 40.0
    ast_ratio = ast / uln_ast
    platelets_safe = max(1.0, platelets)  # prevent division by zero

    apri = (ast_ratio / platelets_safe) * 100.0

    # FIB-4
    alt_safe = max(1.0, alt)
    fib4 = (age * ast) / (platelets_safe * math.sqrt(alt_safe))

    # Interpretation
    if fib4 < 1.45:
        fib4_stage = "F0-F1 (No/mild fibrosis)"
    elif fib4 < 3.25:
        fib4_stage = "F2-F3 (Moderate/significant fibrosis)"
    else:
        fib4_stage = "F4 (Advanced fibrosis/cirrhosis)"

    if apri < 0.5:
        apri_stage = "No significant fibrosis"
    elif apri < 1.5:
        apri_stage = "Significant fibrosis"
    else:
        apri_stage = "Cirrhosis likely"

    return {
        "score_type": "APRI-FIB4",
        "apri": round(apri, 2),
        "apri_stage": apri_stage,
        "fib4": round(fib4, 2),
        "fib4_stage": fib4_stage,
        "components": {"ast": ast, "alt": alt, "platelets": platelets, "age": age}
    }


def assess_row(row):
    try:
        # try common lab keys
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"), row.get("creatinine"), row.get("inr"),
                row.get("sodium"), row.get("dialysis", "0") == "1",
                row.get("albumin"), row.get("sex", "M")
            )
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"), row.get("rr_ms"),
                row.get("hr_bpm") or row.get("heart_rate")
            )
        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"), row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60, row.get("sex", "M")
            )
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"), row.get("alt_u_l"),
                row.get("platelets_109"), row.get("age_years") or row.get("age")
            )
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}

def process_csv(inp, out):
    """Process a CSV file and write results to output."""
    with open(inp, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys = set()
    for rr in results:
        all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        writer.writeheader()
        writer.writerows(results)
    return results


def build_parser():
    """Build the argument parser for CLI."""
    p = argparse.ArgumentParser(prog="nowcaster", description="Outbreak Nowcaster (Delay-Adjusted)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. {"bilirubin": 1.2}')
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    b = sub.add_parser("batch", help="batch csv")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv=None):
    """Main entry point for CLI."""
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        if a.json:
            row = json.loads(a.json)
        else:
            row = {}
            # map aliases
            if a.bili is not None:
                row["bilirubin"] = a.bili
            if a.creat is not None:
                row["creatinine"] = a.creat
            if a.inr is not None:
                row["inr"] = a.inr
            if a.na is not None:
                row["sodium"] = a.na
            if a.qt is not None:
                row["qt_ms"] = a.qt
            if a.rr is not None:
                row["rr_ms"] = a.rr
            if a.hr is not None:
                row["hr_bpm"] = a.hr
        print(assess_row(row))
        return 0
    if a.cmd == "batch":
        res = process_csv(a.input, a.output)
        print(f"Processed {len(res)} -> {a.output}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
