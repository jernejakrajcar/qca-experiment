"""Open the majority-gate baseline and displacement tests in QCADesigner."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


QCADESIGNER = Path(r"C:\Program Files (x86)\QCADesignerE\bin\QCADesignerE.exe")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-baseline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="also open qca-test-majority-voter.qca",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    files: list[Path] = []
    if args.include_baseline:
        files.append(root / "qca-test-majority-voter.qca")
    files.extend(root / "test" / f"center-right-{displacement}.qca" for displacement in range(1, 7))

    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        parser.error("missing test files:\n" + "\n".join(missing))
    if not QCADESIGNER.is_file():
        parser.error(f"QCADesigner not found: {QCADESIGNER}")

    subprocess.Popen(
        [str(QCADESIGNER), *(str(path) for path in files)],
        cwd=root,
    )

    print("Opened:")
    for path in files:
        print(f"  {path}")
    print()
    print("In any QCADesigner window:")
    print("  Simulation -> Simulation Type Setup")
    print("  select Exhaustive Verification")
    print("  click OK")
    print("  use Ctrl+M to start each simulation")


if __name__ == "__main__":
    main()
