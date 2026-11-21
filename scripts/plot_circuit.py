"""Drawing of the majority gate with an arrow for every cell and direction (E2).

The arrow length is the tolerance at 1 K, the label shows 1 K | 10 K.
Cells are drawn further apart than in reality so that the arrows fit:
only the arrows are to scale, not the distances between cells.

Outputs in experiments/figures/:
    circuit-tolerance.pdf, circuit-tolerance.png   for the report
    circuit-tolerance-slide.png                    16:9, for slides
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

from results import CELL_LABEL, FIGURES, nm, tolerances

# position of every cell on the drawing grid
POSITION = {"Input1": (0, 1), "Input2": (-1, 0), "Center": (0, 0), "Input3": (0, -1), "Output": (1, 0)}
ARROW = {"left": (-1, 0), "right": (1, 0), "up": (0, 1), "down": (0, -1)}
FILL = {"Input1": "#dbe8fb", "Input2": "#dbe8fb", "Input3": "#dbe8fb",
        "Center": "#d9f0e4", "Output": "#fdf0c8"}
# where the cell name goes, relative to the cell centre (in cell sizes)
NAME_AT = {"Input1": (-0.75, 0.75, "right"), "Input3": (-0.75, -0.75, "right"),
           "Input2": (0, -0.95, "center"), "Center": (0.75, 0.75, "left"),
           "Output": (0.75, -0.75, "left")}

SPACING = 6.0    # distance between cell centres in the drawing
CELL = 1.6       # size of a drawn cell
SCALE = 0.5      # drawing units per nm of displacement

TEXT = "#1f1f1e"
GREY = "#9b9a93"
# one blue, darker = more sensitive
CLASSES = [(2.0, "#104281", "občutljivo (< 2 nm)"),
           (4.5, "#2a78d6", "srednje (2–4,5 nm)"),
           (float("inf"), "#86b6ef", "robustno (≥ 4,5 nm)")]


def arrow_color(value: float, reason: str) -> str:
    if reason == "overlap":
        return GREY
    return next(color for limit, color, _ in CLASSES if value < limit)


def label(value: float, reason: str) -> str:
    return ("≥ " if reason == "max" else "") + nm(value)


def draw_cell(ax, cell: str, x: float, y: float, font: float) -> None:
    ax.add_patch(Rectangle((x - CELL / 2, y - CELL / 2), CELL, CELL,
                           facecolor=FILL[cell], edgecolor=TEXT, linewidth=1.2, zorder=3))
    for dx in (-0.32, 0.32):
        for dy in (-0.32, 0.32):
            ax.add_patch(Circle((x + dx * CELL, y + dy * CELL), CELL * 0.11,
                                facecolor="white", edgecolor=TEXT, linewidth=0.9, zorder=4))
    nx, ny, align = NAME_AT[cell]
    ax.text(x + nx * CELL, y + ny * CELL, CELL_LABEL[cell], ha=align, va="center",
            fontsize=font, fontweight="bold", color=TEXT)


def draw_arrow(ax, x, y, ux, uy, at_1k, at_10k, toward_cell: bool, font: float) -> None:
    value, reason = at_1k
    start = (x + ux * CELL / 2, y + uy * CELL / 2)
    end = (start[0] + ux * value * SCALE, start[1] + uy * value * SCALE)
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=font * 1.1,
                                 color=arrow_color(*at_1k), linewidth=2.4, zorder=2))

    if reason == "overlap" and at_10k[1] == "overlap":
        return  # always 1,75 nm, explained in the legend

    text = label(*at_1k)
    if label(*at_10k) != text:
        text += " | " + label(*at_10k)

    if toward_cell:
        # the arrow ends between two cells: put the text beside the arrow
        side = 1 if ux > 0 or uy > 0 else -1
        tx, ty = end[0] + ux * 0.6, end[1] + uy * 0.6
        if ux:
            ax.text(tx, ty + side * 0.7, text, ha="center", va="bottom" if side > 0 else "top",
                    fontsize=font * 0.8, color=TEXT)
        else:
            ax.text(tx + side * 0.7, ty, text, ha="left" if side > 0 else "right", va="center",
                    fontsize=font * 0.8, color=TEXT)
    else:
        # the arrow points outwards: put the text after its tip
        tx, ty = end[0] + ux * 0.3, end[1] + uy * 0.3
        ha = "left" if ux > 0 else "right" if ux < 0 else "center"
        va = "bottom" if uy > 0 else "top" if uy < 0 else "center"
        ax.text(tx, ty, text, ha=ha, va=va, fontsize=font * 0.8, color=TEXT)


def draw(ax, at_1k: dict, at_10k: dict, font: float) -> None:
    for cell, (gx, gy) in POSITION.items():
        x, y = gx * SPACING, gy * SPACING
        draw_cell(ax, cell, x, y, font)
        for direction, (ux, uy) in ARROW.items():
            toward_cell = (gx + ux, gy + uy) in POSITION.values()
            draw_arrow(ax, x, y, ux, uy, at_1k[(cell, direction)], at_10k[(cell, direction)],
                       toward_cell, font)
    ax.set_aspect("equal")
    ax.set_ylim(-SPACING - 4.0, SPACING + 3.6)
    ax.axis("off")


def add_legend(ax, font: float, **placement) -> None:
    handles = [Line2D([0], [0], color=color, lw=2.5, label=text) for _, color, text in CLASSES]
    handles.append(Line2D([0], [0], color=GREY, lw=2.5,
                          label="1,75 nm: vrata še delujejo, pri 2 nm\n"
                                "bi se celici dotaknili (razmik je 2 nm)"))
    ax.legend(handles=handles, frameon=False, fontsize=font * 0.75, handlelength=1.6,
              title="dovoljeni premik pri 1 K | 10 K [nm]", title_fontsize=font * 0.8,
              alignment="left", **placement)


def main() -> None:
    at_1k = tolerances("e2-coherence-1K")
    at_10k = tolerances("e2-coherence-10K")
    FIGURES.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.4, 7.6))
    draw(ax, at_1k, at_10k, font=10)
    ax.set_xlim(-SPACING - 4.6, SPACING + 5.2)
    add_legend(ax, 10, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "circuit-tolerance.pdf")
    fig.savefig(FIGURES / "circuit-tolerance.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    draw(ax, at_1k, at_10k, font=15)
    ax.set_xlim(-SPACING - 4.6, SPACING + 15)
    add_legend(ax, 15, loc="center right")
    fig.tight_layout()
    fig.savefig(FIGURES / "circuit-tolerance-slide.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
