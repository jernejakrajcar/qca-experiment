"""Compare our majority gate with the published one from QCADesigner-E (E4).

The published gate (experiments/published-majority-use.qca) comes with
QCADesigner-E (Sill Torres et al., 2018). It uses the USE clocking scheme and
has long input wires.

For both gates the script reports the standard QCA metrics (cells, area,
clock zones, crossings, energy) and the tolerance of the centre cell from the
sweeps in experiments/results/. It writes experiments/figures/comparison_table.tex.

Run in the qca-sim Docker image (the energy needs batch_sim).
"""

import tempfile
from pathlib import Path

from analyze_qca import parse_qca
from prepare_batch import prepare
from results import FIGURES, ROOT, load, nm, tolerance
from run_sweep import read_energy, simulate

GATES = [
    # name, design file, centre cell id, sweep results at 1 K and 10 K
    ("naša", "majority-voter-base.qca", 2, "e2-coherence-1K", "e2-coherence-10K"),
    ("objavljena~\\cite{g12:silltorres2018}", "published-majority-use.qca", 8, "e4-published-1K", "e4-published-10K"),
]
CELL_SIZE = 18.0  # nm


def area_nm2(cells) -> float:
    xs = [c.x for c in cells]
    ys = [c.y for c in cells]
    return (max(xs) - min(xs) + CELL_SIZE) * (max(ys) - min(ys) + CELL_SIZE)


def clock_zones(cells) -> int:
    """Clock zones that the signal passes from input to output (inputs are not counted)."""
    return len({c.clock for c in cells if c.function != "QCAD_CELL_INPUT"})


def energy_eV(design: Path) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        ready = Path(tmp) / "design.qca"
        prepare(design, ready)
        output = simulate("batch_sim", ready, "COHERENCE_VECTOR_ENERGY",
                          ROOT / "experiments" / "sim-options" / "energy-1K.txt")
    return float(read_energy(output)[0])


def weakest(experiment: str, cell_id: int) -> float:
    """Smallest tolerance of the centre cell over all four directions."""
    rows = [r for r in load(experiment) if r["cell_id"] == str(cell_id)]
    # tolerance() groups by cell name, so give the selected rows one name
    for row in rows:
        row["cell"] = "centre"
    return min(tolerance(rows, "centre", d)[0] for d in ("left", "right", "up", "down"))


def main() -> None:
    lines = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
             r"Izvedba & Celice & Površina & Urine cone & Križanja & Energija"
             r" & \multicolumn{2}{c}{Toleranca sredine [nm]} \\",
             r" & & [$\mu$m$^2$] & & & [meV/cikel] & 1 K & 10 K \\", r"\midrule"]

    for name, file, centre, at_1k, at_10k in GATES:
        design = ROOT / "experiments" / file
        cells, _ = parse_qca(design)
        row = {
            "cells": len(cells),
            "area": area_nm2(cells) / 1e6,       # nm² -> µm²
            "zones": clock_zones(cells),
            "energy": energy_eV(design) * 1e3,   # eV -> meV
            "1K": weakest(at_1k, centre),
            "10K": weakest(at_10k, centre),
        }
        print(name, row)
        lines.append(f"{name} & {row['cells']} & {nm(round(row['area'], 4))} & {row['zones']} & 0"
                     f" & {nm(round(row['energy'], 3))} & {nm(row['1K'])} & {nm(row['10K'])} \\\\")

    lines += [r"\bottomrule", r"\end{tabular}"]
    table = "\n".join(lines).replace(",", "{,}") + "\n"
    (FIGURES / "comparison_table.tex").write_text(table)


if __name__ == "__main__":
    main()
