"""Analyze the cell geometry stored in a QCADesigner .qca file.

The parser intentionally uses only the standard library. It reports the
coordinates and geometry of every QCAD cell without modifying the input file.
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path


_NUMBER = r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?"


def _number(value: str) -> float:
    """Parse QCADesigner's decimal-comma or decimal-point number."""

    return float(value.strip().replace(",", "."))


def _value(block: str, key: str) -> float:
    match = re.search(rf"(?m)^{re.escape(key)}=({_NUMBER})\s*$", block)
    if match is None:
        raise ValueError(f"Missing numeric property {key!r}")
    return _number(match.group(1))


def _text_value(block: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}=(.*)$", block)
    if match is None:
        raise ValueError(f"Missing property {key!r}")
    return match.group(1).strip()


@dataclass(frozen=True)
class Dot:
    x: float
    y: float
    diameter: float
    charge: float
    spin: float
    potential: float


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Cell:
    cell_id: int
    label: str | None
    x: float
    y: float
    bounding_box: BoundingBox
    color: tuple[int, int, int]
    cell_width: float
    cell_height: float
    dot_diameter: float
    clock: int
    mode: str
    ignore_energy: bool
    function: str
    dots: tuple[Dot, ...]


def _parse_color(block: str) -> tuple[int, int, int]:
    return (
        int(_value(block, "clr.red")),
        int(_value(block, "clr.green")),
        int(_value(block, "clr.blue")),
    )


def _parse_dots(cell_block: str) -> tuple[Dot, ...]:
    dot_blocks = re.findall(
        r"\[TYPE:CELL_DOT\](.*?)(?=\[#TYPE:CELL_DOT\])",
        cell_block,
        flags=re.DOTALL,
    )
    return tuple(
        Dot(
            x=_value(block, "x"),
            y=_value(block, "y"),
            diameter=_value(block, "diameter"),
            charge=_number(_text_value(block, "charge")),
            spin=_number(_text_value(block, "spin")),
            potential=_number(_text_value(block, "potential")),
        )
        for block in dot_blocks
    )


def _parse_labels(text: str) -> list[tuple[str, float, float]]:
    labels = []
    label_pattern = re.compile(
        r"\[TYPE:QCADLabel\](.*?)(?=\[#TYPE:QCADLabel\])",
        flags=re.DOTALL,
    )
    for block in label_pattern.findall(text):
        labels.append((_text_value(block, "psz"), _value(block, "x"), _value(block, "y")))
    return labels


def _assign_labels(
    labels: list[tuple[str, float, float]], cells: list[tuple[float, float]]
) -> list[str | None]:
    """Associate each label with at most one cell using the closest pairs."""

    candidates = sorted(
        (
            (math.hypot(label[1] - cell[0], label[2] - cell[1]), label_index, cell_index)
            for label_index, label in enumerate(labels)
            for cell_index, cell in enumerate(cells)
        )
    )
    assigned: list[str | None] = [None] * len(cells)
    used_labels: set[int] = set()
    used_cells: set[int] = set()
    for _, label_index, cell_index in candidates:
        if label_index in used_labels or cell_index in used_cells:
            continue
        assigned[cell_index] = labels[label_index][0]
        used_labels.add(label_index)
        used_cells.add(cell_index)
    return assigned


def parse_qca(path: Path) -> tuple[list[Cell], float | None]:
    """Read cells and the optional grid spacing from a QCADesigner file."""

    text = path.read_text(encoding="utf-8")
    labels = _parse_labels(text)
    cell_blocks = re.findall(
        r"\[TYPE:QCADCell\](.*?)(?=\[#TYPE:QCADCell\])",
        text,
        flags=re.DOTALL,
    )
    positions = [(_value(block, "x"), _value(block, "y")) for block in cell_blocks]
    labels_by_cell = _assign_labels(labels, positions)
    cells: list[Cell] = []
    for cell_id, block in enumerate(cell_blocks, start=1):
        function = _text_value(block, "cell_function")
        dot_count = int(_value(block, "number_of_dots"))
        dots = _parse_dots(block)
        if dot_count != len(dots):
            raise ValueError(
                f"Cell {cell_id}: number_of_dots={dot_count}, parsed {len(dots)}"
            )

        cells.append(
            Cell(
                cell_id=cell_id,
                label=labels_by_cell[cell_id - 1],
                x=_value(block, "x"),
                y=_value(block, "y"),
                bounding_box=BoundingBox(
                    x=_value(block, "bounding_box.xWorld"),
                    y=_value(block, "bounding_box.yWorld"),
                    width=_value(block, "bounding_box.cxWorld"),
                    height=_value(block, "bounding_box.cyWorld"),
                ),
                color=_parse_color(block),
                cell_width=_value(block, "cell_options.cxCell"),
                cell_height=_value(block, "cell_options.cyCell"),
                dot_diameter=_value(block, "cell_options.dot_diameter"),
                clock=int(_value(block, "cell_options.clock")),
                mode=_text_value(block, "cell_options.mode"),
                ignore_energy=_text_value(block, "cell_options.ignore_energy") == "TRUE",
                function=function,
                dots=dots,
            )
        )

    grid_match = re.search(rf"(?m)^grid_spacing=({_NUMBER})\s*$", text)
    grid_spacing = _number(grid_match.group(1)) if grid_match else None
    return cells, grid_spacing


def _print_cells(cells: list[Cell], grid_spacing: float | None) -> None:
    print(f"Cells: {len(cells)}")
    print(
        "Coordinate unit: QCADesigner file unit "
        "(no nanometre conversion is declared in the file)"
    )
    if grid_spacing is not None:
        print(f"Grid spacing: {grid_spacing:g} file units")

    for cell in cells:
        box = cell.bounding_box
        print(f"\nCell {cell.cell_id} ({cell.label or 'unlabelled'})")
        print(f"  position: ({cell.x:g}, {cell.y:g})")
        print(
            f"  type: {cell.function.removeprefix('QCAD_CELL_').lower()}"
            f" | mode: {cell.mode}"
        )
        print(f"  color RGB: {cell.color}")
        print(
            f"  bounding box: origin=({box.x:g}, {box.y:g}), "
            f"size=({box.width:g}, {box.height:g})"
        )
        print(
            f"  cell options: size=({cell.cell_width:g}, {cell.cell_height:g}), "
            f"dot diameter={cell.dot_diameter:g}, clock={cell.clock}, "
            f"ignore energy={cell.ignore_energy}"
        )
        print(f"  dots: {len(cell.dots)}")
        for dot_number, dot in enumerate(cell.dots, start=1):
            print(
                f"    {dot_number}: position=({dot.x:g}, {dot.y:g}), "
                f"diameter={dot.diameter:g}, charge={dot.charge:g}, "
                f"spin={dot.spin:g}, potential={dot.potential:g}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qca_file", type=Path, help="path to a .qca file")
    args = parser.parse_args()
    if args.qca_file.suffix.lower() != ".qca":
        parser.error("input file must have the .qca extension")
    if not args.qca_file.is_file():
        parser.error(f"file does not exist: {args.qca_file}")

    cells, grid_spacing = parse_qca(args.qca_file)
    _print_cells(cells, grid_spacing)


if __name__ == "__main__":
    main()
