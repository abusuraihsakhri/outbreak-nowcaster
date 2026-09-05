"""
Comprehensive test suite for Outbreak Nowcaster core functions.
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import nowcaster as m


def test_smoke():
    """Basic smoke test for assess_row with generic input."""
    r = m.assess_row({'value': 10})
    assert isinstance(r, dict)


def test_calculate_score_basic():
    """Test calculate_score with numeric inputs."""
    result = m.calculate_score(a=10, b=20, c=30)
    assert "score" in result
    assert "inputs" in result
    assert result["inputs"] == 3
    assert isinstance(result["score"], float)


def test_calculate_score_with_string_numbers():
    """Test calculate_score with string numeric inputs."""
    result = m.calculate_score(x="10.5", y="20.3")
    assert result["inputs"] == 2
    assert result["score"] > 0


def test_calculate_score_empty():
    """Test calculate_score with no valid inputs."""
    result = m.calculate_score()
    assert result["inputs"] == 1
    assert "score" in result


def test_calculate_meld_na():
    """Test MELD-Na calculation with typical values."""
    result = m.calculate_meld_na(
        bilirubin=2.0, creatinine=1.2, inr=1.5,
        sodium=135, dialysis=False
    )
    assert result["score_type"] == "MELD-Na"
    assert "meld_na" in result
    assert 6 <= result["meld_na"] <= 40
    assert result["risk_tier"] in ["LOW", "MODERATE", "HIGH"]


def test_calculate_meld_na_dialysis():
    """Test MELD-Na with dialysis flag."""
    result = m.calculate_meld_na(
        bilirubin=3.0, creatinine=1.0, inr=1.8,
        sodium=130, dialysis=True
    )
    assert result["score_type"] == "MELD-Na"
    assert result["meld_na"] >= 6


def test_calculate_meld_na_high_values():
    """Test MELD-Na with very high values (ceiling at 40)."""
    result = m.calculate_meld_na(
        bilirubin=50.0, creatinine=15.0, inr=5.0,
        sodium=125, dialysis=True
    )
    assert result["meld_na"] == 40
    assert result["risk_tier"] == "HIGH"


def test_calculate_qtc():
    """Test QTc calculation with RR interval."""
    result = m.calculate_qtc(qt_ms=400, rr_ms=1000)
    assert result["score_type"] == "QTc"
    assert "qtc_ms" in result
    assert result["formula"] == "Bazett"
    assert result["risk_tier"] in ["NORMAL", "BORDERLINE", "PROLONGED"]


def test_calculate_qtc_with_hr():
    """Test QTc calculation with heart rate instead of RR."""
    result = m.calculate_qtc(qt_ms=420, hr_bpm=75)
    assert result["score_type"] == "QTc"
    assert result["qtc_ms"] > 0


def test_calculate_qtc_prolonged():
    """Test QTc with prolonged QT."""
    result = m.calculate_qtc(qt_ms=520, rr_ms=1000)
    assert result["risk_tier"] == "PROLONGED"


def test_calculate_bmi_z_adult():
    """Test BMI calculation for adult."""
    result = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=300, sex="M")
    assert result["score_type"] == "BMI-z"
    assert "bmi" in result
    assert "category" in result
    assert result["category"] in ["UNDERWEIGHT", "NORMAL", "OVERWEIGHT", "OBESE"]


def test_calculate_bmi_z_pediatric():
    """Test BMI calculation for pediatric patient."""
    result = m.calculate_bmi_z(weight_kg=15, height_cm=100, age_months=60, sex="F")
    assert result["score_type"] == "BMI-z"
    assert "z_score" in result


def test_convert_hba1c_from_percent():
    """Test HbA1c conversion from percentage."""
    result = m.convert_hba1c(hba1c_percent=7.0)
    assert result["score_type"] == "HbA1c"
    assert result["hba1c_percent"] == 7.0
    assert "eag_mgdl" in result
    assert result["classification"] == "DIABETES"


def test_convert_hba1c_from_eag():
    """Test HbA1c conversion from eAG."""
    result = m.convert_hba1c(eag_mgdl=154)
    assert result["score_type"] == "HbA1c"
    assert abs(result["hba1c_percent"] - 7.0) < 0.5


def test_convert_hba1c_normal():
    """Test HbA1c normal classification."""
    result = m.convert_hba1c(hba1c_percent=5.2)
    assert result["classification"] == "NORMAL"


def test_calculate_apri_fib4():
    """Test APRI and FIB-4 calculation."""
    result = m.calculate_apri_fib4(
        ast_u_l=80, alt_u_l=60, platelets_109=200, age_years=45
    )
    assert result["score_type"] == "APRI-FIB4"
    assert "apri" in result
    assert "fib4" in result
    assert "apri_stage" in result
    assert "fib4_stage" in result


def test_calculate_apri_fib4_cirrhosis():
    """Test APRI/FIB-4 with cirrhosis-range values."""
    result = m.calculate_apri_fib4(
        ast_u_l=150, alt_u_l=40, platelets_109=80, age_years=65
    )
    assert result["apri"] > 1.5
    assert result["fib4"] > 3.25


def test_assess_row_meld():
    """Test assess_row routes to MELD-Na correctly."""
    row = {"bilirubin": 2.5, "creatinine": 1.5, "inr": 1.3, "sodium": 136}
    result = m.assess_row(row)
    assert result["score_type"] == "MELD-Na"


def test_assess_row_qtc():
    """Test assess_row routes to QTc correctly."""
    row = {"qt_ms": 450, "rr_ms": 900}
    result = m.assess_row(row)
    assert result["score_type"] == "QTc"


def test_assess_row_bmi():
    """Test assess_row routes to BMI-z correctly."""
    row = {"weight_kg": 80, "height_cm": 180, "age": 360, "sex": "M"}
    result = m.assess_row(row)
    assert result["score_type"] == "BMI-z"


def test_assess_row_hba1c():
    """Test assess_row routes to HbA1c correctly."""
    row = {"hba1c_percent": 6.8}
    result = m.assess_row(row)
    assert result["score_type"] == "HbA1c"


def test_assess_row_apri():
    """Test assess_row routes to APRI-FIB4 correctly."""
    row = {"ast_u_l": 60, "alt_u_l": 45, "platelets_109": 180, "age_years": 50}
    result = m.assess_row(row)
    assert result["score_type"] == "APRI-FIB4"


def test_safe_float_none():
    """Test _safe_float with None."""
    assert m._safe_float(None) == 0.0
    assert m._safe_float(None, 5.0) == 5.0


def test_safe_float_invalid():
    """Test _safe_float with invalid input."""
    assert m._safe_float("not_a_number") == 0.0
    assert m._safe_float("abc", 10.0) == 10.0


def test_safe_float_valid():
    """Test _safe_float with valid input."""
    assert m._safe_float("3.14") == 3.14
    assert m._safe_float(42) == 42.0
    assert m._safe_float(2.5) == 2.5
