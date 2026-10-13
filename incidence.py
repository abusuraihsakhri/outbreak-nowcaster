"""Illustrative inverse-completeness nowcasting of aggregated event-date surveillance reports.

This is not a fitted reporting-delay distribution, probabilistic forecast, or
validated clinical decision tool. Observed cases must be grouped by event date.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, date, timezone
import math
import re
import sys

DEFAULT_DELAYS = "0.50,0.25,0.15,0.10"  # illustrative only


def parse_delays(value: str) -> list[float]:
    """Normalize nonnegative reporting-delay probabilities for days 0..n-1."""
    try:
        weights = [float(part.strip()) for part in value.split(",")]
    except (AttributeError, ValueError) as exc:
        raise ValueError("Delay weights must be comma-separated numbers") from exc
    if not 1 <= len(weights) <= 60 or not all(math.isfinite(w) and w >= 0 for w in weights):
        raise ValueError("Provide 1–60 finite, nonnegative delay weights")
    total = math.fsum(weights)
    if not math.isfinite(total) or total <= 0 or weights[0] <= 0:
        raise ValueError("Weights must sum to a positive value and day-0 weight must be > 0")
    return [w / total for w in weights]


def parse_date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Dates must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date: {value}") from exc


def nowcast_counts(rows: list[dict], as_of: str, delays: list[float]) -> list[dict]:
    """Compute observed / P(delay <= event age); input is already aggregated."""
    reference = parse_date(as_of)
    if not delays or any(not math.isfinite(p) or p < 0 for p in delays):
        raise ValueError("Delay probabilities must be finite and nonnegative")
    total = math.fsum(delays)
    if not math.isfinite(total) or total <= 0 or delays[0] <= 0 or abs(total - 1) > 1e-9:
        raise ValueError("Delay probabilities must sum to 1 with positive day-0 probability")
    cumulative = []
    running = 0.0
    for probability in delays:
        running += probability
        cumulative.append(min(1.0, running))
    out = []
    seen = set()
    for row in rows:
        when = parse_date(row["date"])
        if when > reference:
            raise ValueError(f"Event date {when} is after the as-of date")
        if when in seen:
            raise ValueError(f"Duplicate event date: {when}")
        seen.add(when)
        raw = str(row["reported"]).strip()
        if not re.fullmatch(r"\d+", raw):
            raise ValueError(f"Reported cases must be a nonnegative integer on {when}")
        observed = int(raw)
        age = (reference - when).days
        completeness = cumulative[min(age, len(cumulative) - 1)]
        estimate = observed / completeness
        if not math.isfinite(estimate):
            raise ValueError(f"Nowcast overflow on {when}")
        out.append({
            "date": when.isoformat(),
            "reported": observed,
            "age_days": age,
            "completeness": round(completeness, 6),
            "nowcast": round(estimate, 2),
            "additional_estimated": round(estimate - observed, 2),
        })
    return sorted(out, key=lambda r: r["date"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Illustrative reporting-delay-adjusted incidence nowcast")
    parser.add_argument("--input", required=True, help="CSV with date,reported; counts by event date")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat(), help="YYYY-MM-DD surveillance snapshot date")
    parser.add_argument("--delays", default=DEFAULT_DELAYS, help="Day 0, day 1, ... delay weights (default illustrative)")
    parser.add_argument("--output", help="Output CSV path; defaults to stdout")
    args = parser.parse_args(argv)
    try:
        delays = parse_delays(args.delays)
        with open(args.input, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames or not {"date", "reported"}.issubset(reader.fieldnames):
                raise ValueError("CSV requires date,reported column headers")
            records = nowcast_counts(list(reader), args.as_of, delays)
        if not records:
            raise ValueError("CSV contains no rows")
        fields = ["date", "reported", "age_days", "completeness", "nowcast", "additional_estimated"]
        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                writer.writerows(records)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        return 0
    except (ValueError, KeyError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
