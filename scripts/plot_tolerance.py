"""Bar chart and LaTeX table of the tolerance of every cell and direction (E1, E2).

Outputs in experiments/figures/:
    tolerance.pdf, tolerance.png   bar chart
    tolerance_table.tex            table for the report
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from results import CELL_LABEL, CELLS, DIRECTION_LABEL, DIRECTIONS, FIGURES, load, nm, tolerances

SERIES = [
    ("e2-coherence-1K", "koherentni vektor, 1 K (enako bistabilni)", "#2a78d6"),
    ("e2-coherence-10K", "koherentni vektor, 10 K", "#eb6834"),
]
TEXT, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"


def same_result(a: str, b: str) -> bool:
    """True if two experiments gave the same status at every displacement."""
    def key(rows):
        return [(r["cell"], r["direction"], r["displacement_nm"], r["status"]) for r in rows]
    return key(load(a)) == key(load(b))


def bar_chart(data: dict) -> None:
    rows = [(c, d) for c in CELLS for d in DIRECTIONS]
    fig, ax = plt.subplots(figsize=(7.0, 7.2))

    ticks, y = [], 0.0
    for i, (cell, direction) in enumerate(rows):
        if i > 0 and direction == DIRECTIONS[0]:
            y += 0.6  # gap between cells
        ticks.append(y)
        for s, (experiment, _, color) in enumerate(SERIES):
            value, reason = data[experiment][(cell, direction)]
            bar_y = y + (s - 0.5) * 0.4
            if reason == "overlap":
                ax.barh(bar_y, value, height=0.36, color="white", edgecolor=color,
                        hatch="////", linewidth=1.2)
            else:
                ax.barh(bar_y, value, height=0.36, color=color)
            label = ("≥ " if reason == "max" else "") + nm(value)
            ax.text(value + 0.08, bar_y, label, va="center", fontsize=7.5, color=MUTED)
        y += 1.0

    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{CELL_LABEL[c]}, {DIRECTION_LABEL[d]}" for c, d in rows],
                       fontsize=8.5, color=TEXT)
    ax.invert_yaxis()
    ax.set_xlim(0, 7)
    ax.set_xlabel("največji premik, pri katerem vrata še delujejo [nm]", color=TEXT)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)

    legend = [Patch(color=color, label=label) for _, label, color in SERIES]
    legend.append(Patch(facecolor="white", edgecolor=MUTED, hatch="////",
                        label="omejeno s prekrivanjem s sosednjo celico"))
    ax.legend(handles=legend, loc="upper right", fontsize=8, frameon=False)

    fig.tight_layout()
    fig.savefig(FIGURES / "tolerance.pdf")
    fig.savefig(FIGURES / "tolerance.png", dpi=200)
    plt.close(fig)


def latex_table(data: dict) -> None:
    def cell_text(value, reason):
        number = nm(value).replace(",", "{,}")
        if reason == "max":
            return f"$\\geq {number}$"
        if reason == "overlap":
            return number + "\\textsuperscript{p}"
        return number

    lines = [r"\begin{tabular}{llrr}", r"\toprule",
             r"Celica & Smer & 1 K [nm] & 10 K [nm] \\", r"\midrule"]
    for cell in CELLS:
        for direction in DIRECTIONS:
            values = [cell_text(*data[e][(cell, direction)]) for e, _, _ in SERIES]
            lines.append(f"{CELL_LABEL[cell]} & {DIRECTION_LABEL[direction]} & "
                         f"{values[0]} & {values[1]} \\\\")
        lines.append(r"\midrule" if cell != CELLS[-1] else r"\bottomrule")
    lines.append(r"\end{tabular}")
    (FIGURES / "tolerance_table.tex").write_text("\n".join(lines) + "\n")


def main() -> None:
    if not same_result("e1-bistable", "e2-coherence-1K"):
        print("Warning: bistable and coherence vector at 1 K differ, update the legend.")

    FIGURES.mkdir(parents=True, exist_ok=True)
    data = {experiment: tolerances(experiment) for experiment, _, _ in SERIES}
    bar_chart(data)
    latex_table(data)


if __name__ == "__main__":
    main()
