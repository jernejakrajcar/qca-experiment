"""Read sweep results and compute the tolerance of every cell and direction.

Tolerance is the largest displacement at which the gate still works.
A sweep ends for one of three reasons:
    fail     the gate gives a wrong output,
    overlap  the next step would make the cell touch its neighbour,
    max      the largest tested displacement was reached.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "experiments" / "results"
FIGURES = ROOT / "experiments" / "figures"

CELLS = ["Center", "Input1", "Input2", "Input3", "Output"]
DIRECTIONS = ["left", "right", "up", "down"]

# labels for figures and tables (in Slovenian)
CELL_LABEL = {"Center": "sredina", "Input1": "Input1", "Input2": "Input2",
              "Input3": "Input3", "Output": "izhod"}
DIRECTION_LABEL = {"left": "levo", "right": "desno", "up": "gor", "down": "dol"}


def load(experiment: str) -> list[dict]:
    with open(RESULTS / f"{experiment}.csv", newline="") as file:
        return list(csv.DictReader(file))


def tolerance(rows: list[dict], cell: str, direction: str) -> tuple[float, str]:
    """Return (tolerance in nm, reason the sweep ended)."""
    sweep = [r for r in rows if r["cell"] == cell and r["direction"] == direction]
    sweep.sort(key=lambda r: float(r["displacement_nm"]))

    last_ok = 0.0
    for row in sweep:
        if row["status"] != "ok":
            reason = "overlap" if row["status"].startswith("overlap") else "fail"
            return last_ok, reason
        last_ok = float(row["displacement_nm"])
    return last_ok, "max"


def tolerances(experiment: str) -> dict[tuple[str, str], tuple[float, str]]:
    rows = load(experiment)
    return {(c, d): tolerance(rows, c, d) for c in CELLS for d in DIRECTIONS}


def nm(value: float) -> str:
    """Number with a decimal comma, as used in Slovenian text: 1.25 -> "1,25"."""
    return f"{value:g}".replace(".", ",")
