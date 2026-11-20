"""Move one cell of the majority gate step by step and check if the gate still works.

For every cell, direction and displacement the script
  1. moves the cell (move_cell.py),
  2. prepares the file for batch_sim (prepare_batch.py),
  3. simulates all input combinations with batch_sim,
  4. compares the output with the majority of the three inputs.

A sweep in one direction stops when the moved cell would touch its neighbour.
Every simulation is one row in the output CSV file.

Example (in the qca-sim Docker image, see tools/Dockerfile):
  python3 scripts/run_sweep.py --engine BISTABLE \\
      --options experiments/sim-options/bistable.txt \\
      --out experiments/results/e1-bistable.csv
"""

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path

from analyze_qca import parse_qca
from move_cell import move_cell
from prepare_batch import prepare

ENGINES = ["BISTABLE", "COHERENCE_VECTOR", "COHERENCE_VECTOR_ENERGY"]
DIRECTIONS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
CELL_SIZE = 18.0  # nm

COLUMNS = ["engine", "cell_id", "cell", "direction", "displacement_nm",
           "status", "output_bits", "followed_input", "energy_eV", "energy_error_eV"]

# printed by the energy engine: average dissipation per clock cycle
ENERGY = re.compile(r"Avg_Ebath\): (\S+) eV \(Error: \+/- (\S+) eV\)")


def name(cell) -> str:
    return cell.label or "Center"


def touched_cell(cells, cell, dx: float, dy: float) -> str | None:
    """Return the name of the cell that `cell` would touch after the move, if any."""
    x, y = cell.x + dx, cell.y + dy
    for other in cells:
        if other is not cell and abs(other.x - x) <= CELL_SIZE and abs(other.y - y) <= CELL_SIZE:
            return name(other)
    return None


def simulate(batch_sim: str, qca_file: Path, engine: str, options: Path) -> str:
    """Simulate all input combinations once, without random displacement."""
    result = subprocess.run(
        [batch_sim, "-f", str(qca_file), "-e", engine, "-o", str(options), "-n", "1", "-t", "0"],
        capture_output=True, text=True)
    return result.stdout + result.stderr


def read_traces(output: str) -> dict[str, list[int]]:
    """Logic values of every bus, for example {"Input1": [0, 1, 0, 1], ...}.

    batch_sim prints each bus as two lines:
        First trace in this bus is "Input1"
        0 1 0 1
    """
    lines = output.replace("\r", "\n").splitlines()
    traces = {}
    for line, values in zip(lines, lines[1:]):
        if line.startswith("First trace in this bus is"):
            traces[line.split('"')[1]] = [int(v) for v in values.split()]
    return traces


def stretch(values: list[int], n: int) -> list[int]:
    """Repeat values so the list has n entries.

    batch_sim prints a new value only when an input changes, so the slowest
    input has fewer values than the output.
    """
    return [values[k * len(values) // n] for k in range(n)]


def check_majority(traces, inputs: list[str], output: str) -> tuple[str, str, str]:
    """Return (status, output bits, input that the output follows)."""
    if output not in traces or any(i not in traces for i in inputs):
        return "no_result", "", ""

    out = traces[output]
    if not out:
        # no output value at all: the output polarization never reached 0.5
        return "fail", "undetermined", ""

    # the energy engine prints one extra value: the output before the first input
    if len(out) == max(len(traces[i]) for i in inputs) + 1:
        out = out[1:]

    columns = {i: stretch(traces[i], len(out)) for i in inputs}
    expected = [int(sum(columns[i][k] for i in inputs) >= 2) for k in range(len(out))]

    status = "ok" if out == expected else "fail"
    bits = "".join(map(str, out))
    followed = "+".join(i for i in inputs if columns[i] == out)
    return status, bits, followed


def read_energy(output: str) -> tuple[str, str]:
    match = ENERGY.search(output)
    if not match:
        return "", ""
    return match.group(1), str(abs(float(match.group(2))))


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=ENGINES, required=True)
    parser.add_argument("--options", type=Path, required=True, help="simulation options file")
    parser.add_argument("--out", type=Path, required=True, help="CSV file with results")
    parser.add_argument("--base", type=Path, default=root / "experiments" / "majority-voter-base.qca")
    parser.add_argument("--cells", type=int, nargs="*", help="cell ids to move (default: all)")
    parser.add_argument("--step", type=float, default=0.25, help="step in nm")
    parser.add_argument("--max", type=float, default=6.0, help="largest displacement in nm")
    parser.add_argument("--batch-sim", default="batch_sim")
    args = parser.parse_args()

    cells, _ = parse_qca(args.base)
    inputs = [name(c) for c in cells if c.function == "QCAD_CELL_INPUT"]
    output = next(name(c) for c in cells if c.function == "QCAD_CELL_OUTPUT")
    moved_cells = [c for c in cells if not args.cells or c.cell_id in args.cells]
    steps = [i * args.step for i in range(round(args.max / args.step) + 1)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as file, tempfile.TemporaryDirectory() as tmp:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()

        for cell in moved_cells:
            for direction, (ux, uy) in DIRECTIONS.items():
                for d in steps:
                    row = dict.fromkeys(COLUMNS, "")
                    row.update(engine=args.engine, cell_id=cell.cell_id, cell=name(cell),
                               direction=direction, displacement_nm=d)

                    neighbour = touched_cell(cells, cell, ux * d, uy * d)
                    if neighbour:
                        row["status"] = f"overlap:{neighbour}"
                        writer.writerow(row)
                        break

                    moved = Path(tmp) / f"{cell.cell_id}-{direction}-{d}.qca"
                    ready = Path(tmp) / f"{cell.cell_id}-{direction}-{d}.batch.qca"
                    move_cell(args.base, moved, cell.cell_id, direction, d, file_units_per_nm=1.0)
                    prepare(moved, ready)

                    sim_output = simulate(args.batch_sim, ready, args.engine, args.options)
                    row["status"], row["output_bits"], row["followed_input"] = check_majority(
                        read_traces(sim_output), inputs, output)
                    row["energy_eV"], row["energy_error_eV"] = read_energy(sim_output)
                    writer.writerow(row)

                print(f"{name(cell):>7} {direction:>5} done", flush=True)


if __name__ == "__main__":
    main()
