"""Export the three-backbone comparison from the saved analysis (no recomputation)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#a44427', '#826ba4', '#196b61', '#85641b', '#356c9a', '#b35070', '#527332', '#a95315', '#66578c']


def build():
    data = json.loads((ROOT / "site/data/week4.json").read_text())
    nodes = {n["id"]: n for n in data["nodes"]}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="#e8ede5")
    for ax, alpha in zip(axes, [.1, .2, .3]):
        edges = [e for e in data["edges"] if e["score"] < alpha]
        active = {e[k] for e in edges for k in ("source", "target")}
        ordered = sorted((nodes[n] for n in active), key=lambda n: (n["strength"], n["id"]))
        segments = [[(nodes[e[k]]["x"], -nodes[e[k]]["y"]) for k in ("source", "target")] for e in edges]
        ax.add_collection(LineCollection(segments, colors="#17312d", linewidths=.3, alpha=.22))
        ax.scatter([n["x"] for n in ordered], [-n["y"] for n in ordered],
                   s=[n["strength"] * .15 for n in ordered], c=[COLORS[n["community"]] for n in ordered], linewidths=0)
        for n in sorted(ordered, key=lambda n: -n["strength"])[:3]:
            ax.annotate(n["name"], (n["x"], -n["y"]), xytext=(4, 4), textcoords="offset points", fontsize=7, color="#17312d")
        record = next(r for r in data["snapshots"] if r["alpha"] == alpha)
        ax.set_title(f'α = {alpha:.2f}  /  {record["giant"]:,} in largest component', fontsize=12, color="#17312d", loc="left", pad=12)
        ax.text(0, -.025, f'{len(edges):,} links · {len(active):,} people with a link', transform=ax.transAxes, fontsize=10, color="#596761")
        ax.set_xlim(-1.08, 1.08); ax.set_ylim(-1.08, 1.08); ax.set_aspect("equal"); ax.axis("off")
    fig.subplots_adjust(left=.025, right=.985, top=.90, bottom=.10, wspace=.08)
    out = ROOT / "site/assets/week4-backbones.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.hashsalt": "week4", "svg.fonttype": "none"}):
        fig.savefig(out, facecolor=fig.get_facecolor(), metadata={"Date": None})
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    build()
