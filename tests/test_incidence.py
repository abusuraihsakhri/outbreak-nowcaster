"""Boundary and CLI regression tests for illustrative delay-adjusted incidence."""
import csv
from pathlib import Path
import pytest
from incidence import main, nowcast_counts, parse_date, parse_delays

def test_exact_inverse_completeness_and_sorting():
    rows = [
        {"date": "2026-10-11", "reported": "90"},
        {"date": "2026-10-13", "reported": "5"},
        {"date": "2026-10-12", "reported": "15"},
        {"date": "2026-10-10", "reported": "100"},
    ]
    result = nowcast_counts(rows, "2026-10-13", parse_delays("0.5,0.3,0.2"))
    assert [r["nowcast"] for r in result] == [100, 90, 18.75, 10]
    assert [r["completeness"] for r in result] == [1, 1, .8, .5]
    assert [r["date"] for r in result] == sorted(r["date"] for r in result)

def test_weights_normalized():
    assert parse_delays("5,3,2") == pytest.approx([.5, .3, .2])

@pytest.mark.parametrize("weights", ["", "a,b", "0,1", "0,0", "-1,2", "NaN,1", "inf,1", ",,", "1," * 61])
def test_invalid_weights(weights):
    with pytest.raises(ValueError):
        parse_delays(weights)

@pytest.mark.parametrize("rows,asof", [
    ([{"date":"2026-10-14","reported":"1"}], "2026-10-13"),
    ([{"date":"2026-10-13","reported":"-1"}], "2026-10-13"),
    ([{"date":"2026-10-13","reported":"1.5"}], "2026-10-13"),
    ([{"date":"2026-10-13","reported":"NaN"}], "2026-10-13"),
    ([{"date":"2026-10-13","reported":"1"},{"date":"2026-10-13","reported":"2"}],"2026-10-13"),
    ([{"date":"2026-02-30","reported":"1"}], "2026-10-13"),
])
def test_invalid_rows(rows,asof):
    with pytest.raises(ValueError):
        nowcast_counts(rows,asof,parse_delays("0.5,0.5"))

def test_dates_strict():
    for val in ["20261013","2026-2-01","not-a-date"]:
        with pytest.raises(ValueError):
            parse_date(val)

def test_cli_csv_round_trip(tmp_path: Path):
    source=tmp_path/"source.csv";target=tmp_path/"result.csv"
    source.write_text("date,reported\n2026-10-13,5\n2026-10-12,15\n",encoding="utf-8")
    assert main(["--input",str(source),"--as-of","2026-10-13","--delays","0.5,0.5","--output",str(target)])==0
    with target.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==2
    assert rows[0]["nowcast"]=="15.0"
    assert rows[1]["nowcast"]=="10.0"
