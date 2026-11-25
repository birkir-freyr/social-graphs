"""Draw the Fandom and matched-source estimates with actor-clustered intervals."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

OUT = Path(__file__).resolve().parent / "results"


def main():
    report = json.loads((OUT / "comparison.json").read_text())
    samples = [("fandom", "Fandom · all scored roles", "#b8642a"),
               ("fandom_shared", "Fandom · shared roles", "#b8642a"),
               ("wikipedia_shared", "Wikipedia · shared roles", "#28708d")]
    panels = [("nolan_excess", "Excess departure from earlier roles"),
              ("nolan_own_minus_costar", "Own role minus a co-star’s role")]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.1), sharey=True)
    fig.subplots_adjust(left=.29, right=.985, bottom=.22, top=.78, wspace=.20)
    for ax, (test, title) in zip(axes, panels):
        ax.axvline(0, color="#666666", lw=1, ls="--")
        for index, (sample, _, color) in enumerate(samples):
            estimate = report[sample]["tests"][test]
            mean = estimate["mean"]
            low, high = estimate["ci95"]
            ax.errorbar(mean, 2-index, xerr=[[mean-low], [high-mean]], fmt="o",
                        color=color, markersize=6.5, capsize=3, linewidth=1.6)
        ax.set_title(title, fontsize=11, loc="left")
        ax.set_xlim(-.034, .070)
        ax.set_xticks([-.02, 0, .02, .04, .06])
        ax.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
        ax.set_ylim(-.5, 2.55)
        ax.grid(axis="x", alpha=.13)
        ax.spines[["top", "left", "right"]].set_visible(False)
        ax.spines["bottom"].set_color("#a1a1a1")
        ax.tick_params(axis="both", length=0, labelsize=9)
    axes[0].set_yticks([2, 1, 0], [f"{label}  ({report[k]['tests']['nolan_excess']['n']})"
                                    for k, label, _ in samples])
    fig.text(.29, .045, "Points are means. Bars show actor-clustered 95% bootstrap intervals.", fontsize=9)
    fig.savefig(OUT / "source_comparison.png", dpi=210, bbox_inches="tight", pad_inches=.18)
    plt.close(fig)


if __name__ == "__main__":
    main()
