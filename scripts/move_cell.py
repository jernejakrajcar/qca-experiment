"""Create a translated copy of one cell in a QCADesigner .qca file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from analyze_qca import parse_qca


_NUMBER = r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?"
_DIRECTIONS = {"left": (-1.0, 0.0), "right": (1.0, 0.0), "up": (0.0, -1.0), "down": (0.0, 1.0)}


def _format_number(value: float, original: str) -> str:
    decimal_separator = "," if "," in original else "."
    formatted = f"{value:.6f}"
    return formatted.replace(".", decimal_separator)


def _replace_property(block: str, key: str, delta: float) -> str:
    pattern = re.compile(rf"(?m)^(?P<prefix>{re.escape(key)}=)(?P<value>{_NUMBER})(?P<suffix>\s*)$")

    def replace(match: re.Match[str]) -> str:
        value = float(match.group("value").replace(",", "."))
        return (
            f"{match.group('prefix')}"
            f"{_format_number(value + delta, match.group('value'))}"
            f"{match.group('suffix')}"
        )

    updated, count = pattern.subn(replace, block, count=1)
    if count != 1:
        raise ValueError(f"Expected exactly one property {key!r}, found {count}")
    return updated


def _translate_cell_block(block: str, dx: float, dy: float) -> str:
    for key in ("x", "bounding_box.xWorld"):
        block = _replace_property(block, key, dx)
    for key in ("y", "bounding_box.yWorld"):
        block = _replace_property(block, key, dy)

    dot_pattern = re.compile(
        r"(\[TYPE:CELL_DOT\].*?)(?=\[#TYPE:CELL_DOT\])", flags=re.DOTALL
    )
    dot_blocks = dot_pattern.findall(block)
    for dot_block in dot_blocks:
        translated = _replace_property(dot_block, "x", dx)
        translated = _replace_property(translated, "y", dy)
        block = block.replace(dot_block, translated, 1)
    return block


def _translate_label_block(block: str, dx: float, dy: float) -> str:
    for key in ("x", "bounding_box.xWorld"):
        block = _replace_property(block, key, dx)
    for key in ("y", "bounding_box.yWorld"):
        block = _replace_property(block, key, dy)
    return block


def move_cell(
    source: Path,
    destination: Path,
    cell_id: int,
    direction: str,
    displacement_nm: float,
    file_units_per_nm: float,
) -> None:
    """Translate one cell from the original source into a new QCA file.

    ``file_units_per_nm`` is explicit because the input file does not declare
    how its world coordinates map to physical nanometres.
    """

    if source.resolve() == destination.resolve():
        raise ValueError("destination must differ from the original source")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {destination}")
    if direction not in _DIRECTIONS:
        raise ValueError(f"unknown direction {direction!r}")
    if displacement_nm < 0:
        raise ValueError("displacement_nm must not be negative")
    if file_units_per_nm <= 0:
        raise ValueError("file_units_per_nm must be positive")

    cells, _ = parse_qca(source)
    if not 1 <= cell_id <= len(cells):
        raise ValueError(f"cell_id must be between 1 and {len(cells)}")

    direction_x, direction_y = _DIRECTIONS[direction]
    dx = direction_x * displacement_nm * file_units_per_nm
    dy = direction_y * displacement_nm * file_units_per_nm
    text = source.read_text(encoding="utf-8")

    cell_pattern = re.compile(
        r"(\[TYPE:QCADCell\])(.*?)(\[#TYPE:QCADCell\])", flags=re.DOTALL
    )
    cell_matches = list(cell_pattern.finditer(text))
    target_match = cell_matches[cell_id - 1]
    target_block = _translate_cell_block(target_match.group(2), dx, dy)
    text = (
        text[: target_match.start(2)]
        + target_block
        + text[target_match.end(2) :]
    )

    # Labels are separate QCAD objects. Only move a label when the source
    # analysis associated that label with the selected cell.
    target_cell = cells[cell_id - 1]
    if target_cell.label is not None:
        labels = re.compile(
            r"(\[TYPE:QCADLabel\])(.*?)(\[#TYPE:QCADLabel\])", flags=re.DOTALL
        )
        for label_match in labels.finditer(text):
            label_block = label_match.group(2)
            label_match_text = re.search(
                r"(?m)^psz=(.*)$", label_block
            )
            if label_match_text and label_match_text.group(1).strip() == target_cell.label:
                updated_label = _translate_label_block(label_block, dx, dy)
                text = (
                    text[: label_match.start(2)]
                    + updated_label
                    + text[label_match.end(2) :]
                )
                break

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def batch_move_cell(
    source: Path,
    destination_dir: Path,
    cell_id: int,
    directions: tuple[str, ...],
    displacements_nm: tuple[float, ...],
    file_units_per_nm: float,
) -> list[Path]:
    """Generate independent copies for all direction/displacement combinations."""

    created: list[Path] = []
    source = source.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)

    for direction in directions:
        for displacement_nm in displacements_nm:
            displacement_text = f"{displacement_nm:g}".replace(".", "_")
            destination = (
                destination_dir
                / f"cell{cell_id}-{direction}-{displacement_text}nm.qca"
            )
            move_cell(
                source,
                destination,
                cell_id,
                direction,
                displacement_nm,
                file_units_per_nm,
            )
            created.append(destination)

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--cell-id", type=int, required=True)
    parser.add_argument("--direction", choices=sorted(_DIRECTIONS), required=True)
    parser.add_argument("--displacement-nm", type=float, required=True)
    parser.add_argument(
        "--file-units-per-nm",
        type=float,
        required=True,
        help="verified conversion from nanometres to QCAD world units",
    )
    args = parser.parse_args()
    move_cell(
        args.source,
        args.destination,
        args.cell_id,
        args.direction,
        args.displacement_nm,
        args.file_units_per_nm,
    )
    print(f"Created {args.destination}")


if __name__ == "__main__":
    main()
