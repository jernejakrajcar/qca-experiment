"""Validate geometry and compare measured QCA outputs with majority truth."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_qca import parse_qca


def read_results(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_geometry(root: Path) -> dict[int, bool]:
    source = root / "qca-test-majority-voter.qca"
    baseline, _ = parse_qca(source)
    validity: dict[int, bool] = {0: True}

    for displacement in range(1, 7):
        variant = root / "test" / f"center-right-{displacement}.qca"
        cells, _ = parse_qca(variant)
        center = cells[1]
        baseline_center = baseline[1]

        unchanged = all(
            (cell.x, cell.y) == (baseline_cell.x, baseline_cell.y)
            for cell, baseline_cell in zip(cells, baseline)
            if cell.cell_id != 2
        )
        dx = center.x - baseline_center.x
        four_dots = len(center.dots) == 4
        dots_shifted = four_dots and all(
            abs(dot.x - baseline_dot.x - displacement) < 1e-9
            and dot.y == baseline_dot.y
            for dot, baseline_dot in zip(center.dots, baseline_center.dots)
        )
        validity[displacement] = unchanged and dx == float(displacement) and dots_shifted

    return validity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "test" / "results-template.csv",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    geometry = validate_geometry(root)

    rows = read_results(args.results)
    if len(rows) != 56:
        raise SystemExit(f"Expected 56 result rows, found {len(rows)}")

    seen: set[tuple[int, int, int, int]] = set()
    failures: list[str] = []
    pending = 0
    passed = 0

    for row in rows:
        key = (
            int(row["displacement_nm"]),
            int(row["A"]),
            int(row["B"]),
            int(row["C"]),
        )
        if key in seen:
            raise SystemExit(f"Duplicate result row: {key}")
        seen.add(key)

        expected = int(row["expected_output"])
        measured_text = row["measured_output"].strip()
        if measured_text == "":
            pending += 1
            continue
        if measured_text not in {"0", "1"}:
            failures.append(f"{key}: invalid measured_output={measured_text!r}")
            continue

        measured = int(measured_text)
        if measured == expected:
            passed += 1
        else:
            failures.append(f"{key}: expected {expected}, measured {measured}")

    print("Geometry verification:")
    for displacement, valid in geometry.items():
        print(f"  {displacement} nm/right: {'PASS' if valid else 'FAIL'}")

    print(f"\nResults: {passed} passed, {pending} pending, {len(failures)} mismatches")
    for failure in failures:
        print(f"  FAIL {failure}")

    if not all(geometry.values()):
        raise SystemExit(2)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
