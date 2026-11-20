"""Prepare a QCADesigner file for the command-line simulator batch_sim.

Two changes are made:

1. Decimal commas are replaced with decimal points. QCADesigner on Windows
   with Slovenian settings writes "180,5", but batch_sim reads only up to the
   comma, so it would see 180.
2. A bus layout is added: one bus for every input cell and every output
   cell. batch_sim prints the values of these buses.
"""

import argparse
import re
from pathlib import Path

DECIMAL_COMMA = re.compile(r"(?m)^([A-Za-z_.]+=[-+]?\d+),(\d)")

INPUT_BUS = 1
OUTPUT_BUS = 2


def bus(name: str, function: int, index: int) -> list[str]:
    return [
        "[TYPE:BUS]",
        f"pszName={name}",
        f"bus_function={function}",
        "[BUS_DATA]",
        str(index),
        "[#BUS_DATA]",
        "[#TYPE:BUS]",
    ]


def prepare(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = DECIMAL_COMMA.sub(r"\1.\2", text)

    n_inputs = text.count("cell_function=QCAD_CELL_INPUT")
    n_outputs = text.count("cell_function=QCAD_CELL_OUTPUT")

    layout = ["[TYPE:BUS_LAYOUT]"]
    for i in range(n_inputs):
        layout += bus(f"IN{i}", INPUT_BUS, i)
    for i in range(n_outputs):
        layout += bus(f"OUT{i}", OUTPUT_BUS, i)
    layout.append("[#TYPE:BUS_LAYOUT]")

    # the bus layout belongs inside the design, just before its closing tag
    lines = text.rstrip("\n").split("\n")
    assert lines[-1] == "[#TYPE:DESIGN]", f"unexpected end of {source}"
    lines[-1:-1] = layout
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.destination)


if __name__ == "__main__":
    main()
