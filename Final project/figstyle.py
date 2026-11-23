"""Shared figure style for the Nolan paper.

Colours come from the casting-network figure so every plot in the paper
reads as one set:

    #c76b2a   burnt orange — Nolan (films, in the network figure)
    #1f7fa8   steel blue   — everything else (actors, in the network figure)
    #dde0e3   pale grey    — null bands
    #823e0c   dark orange  — emphasis text

The blue is one step more saturated than the network figure's #48819c,
which sits below the chroma floor and prints as grey. Side by side they
read as the same blue; this one survives on paper.

House rules, applied by apply():
  * one column wide, one height, so the figures read as a set
  * nothing inside the axes that belongs in a caption — no stats blocks,
    no "shaded region is..." notes. The caption says those things.
  * two spines, thin, grey. No box, no top/right rules.
  * grid only on the axis a reader actually reads values off.

    import figstyle as S
    S.apply()
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NOLAN = "#c76b2a"
OTHER = "#1f7fa8"
GREY = "#dde0e3"
DARK_ORANGE = "#823e0c"
INK = "#1a1a1a"
INK2 = "#5b5f63"
LINE = "#c3c8cc"
SURFACE = "#ffffff"

COL1, COL2 = 3.42, 7.0          # PNAS single / double column, inches
HEIGHT = 3.1                    # one height for every single-column figure


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.size": 7.5,
        "axes.titlesize": 9,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": LINE,
        "axes.linewidth": 0.6,
        "xtick.color": LINE,
        "ytick.color": LINE,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.pad": 3,
        "ytick.major.pad": 3,
        "legend.frameon": False,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.4,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 400,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    })


def frame(ax, title, xlabel=None, ylabel=None, grid=None, legend_cols=0):
    """One call for the furniture every figure shares.

    grid: None, "x" or "y" — only the axis values are read off.
    legend_cols: >0 puts the legend above the axes and leaves room for it.
    """
    if grid:
        ax.grid(axis=grid, color=GREY, lw=0.6, zorder=0)
        ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if legend_cols:
        handles, labels = ax.get_legend_handles_labels()
        rows = -(-len(labels) // legend_cols)      # ceiling division
        ax.set_title(title, loc="center", color=INK, pad=10 + 13 * rows)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01),
                  ncol=legend_cols, borderaxespad=0)
    else:
        ax.set_title(title, loc="center", color=INK, pad=8)
    return ax
