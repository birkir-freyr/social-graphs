"""Reproduce Week 1 measurements and website figures from the frozen TSVs."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"
ASSETS = ROOT / "site" / "assets"


def load_graph():
    with (DATA / "week1_nodes.tsv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"))
    with (DATA / "week1_edges.tsv").open(encoding="utf-8", newline="") as f:
        edges = list(csv.reader((l for l in f if not l.startswith("#")), delimiter="\t"))
    ids = {r["node_id"] for r in rows}
    assert len(ids) == len(rows) == 303
    assert all(len(e) == 2 and set(e) <= ids for e in edges)
    assert len(edges) == len(set(map(tuple, edges))) == 1784
    graph = nx.DiGraph()
    graph.add_nodes_from((r["node_id"], r) for r in rows)
    graph.add_edges_from(edges)
    assert nx.number_of_selfloops(graph) == 0
    return graph


def distribution(values):
    counts = np.bincount(values)
    raw = [{"u": int(k + 1), "count": int(c), "p": float(c / len(values))} for k, c in enumerate(counts)]
    intervals = [(u, u + 1) for u in range(1, 8)]
    left = 8
    while left <= len(counts):
        intervals.append((left, left * 2))
        left *= 2
    binned = []
    for lo, hi in intervals:
        count = int(counts[lo - 1:hi - 1].sum())
        binned.append({"u": float(np.sqrt(lo * (hi - 1))), "p": count / (len(values) * (hi - lo)),
                       "count": count, "lo": lo, "hi": hi})
    assert sum(b["count"] for b in binned) == len(values)
    assert np.isclose(sum(b["p"] * (b["hi"] - b["lo"]) for b in binned), 1)
    assert all(binned[i]["p"] == raw[i]["p"] for i in range(min(7, len(raw))))
    return {"raw": raw, "binned": binned}


def analyze(graph):
    undirected = graph.to_undirected()
    components = sorted((sorted(c) for c in nx.connected_components(undirected)), key=lambda c: (-len(c), c))
    island = components[1]
    giant = components[0]
    reciprocal = sum(graph.has_edge(v, u) for u, v in graph.edges) // 2
    after = undirected.subgraph([n for n in giant if n != "Spider-Man"])
    after_components = sorted(nx.connected_components(after), key=len, reverse=True)
    stranded = sorted(n for c in after_components[1:] for n in c)
    stats = {
        "nodes": len(graph), "directedEdges": graph.number_of_edges(),
        "undirectedEdges": undirected.number_of_edges(), "reciprocalPairs": reciprocal,
        "isolates": len(list(nx.isolates(graph))), "components": len(components),
        "giant": len(giant), "island": len(island),
        "averageDegree": sum(dict(undirected.degree()).values()) / len(graph),
        "density": nx.density(undirected), "afterSpiderMan": len(after_components[0]),
        "stranded": stranded,
        "zeroIn": sum(d == 0 for _, d in graph.in_degree()),
        "zeroOut": sum(d == 0 for _, d in graph.out_degree()),
    }
    assert (stats["nodes"], stats["directedEdges"], stats["undirectedEdges"], stats["isolates"]) == (303, 1784, 1434, 17)
    assert [len(c) for c in components] == [277, 9] + [1] * 17
    assert reciprocal == 350 and len(after_components[0]) == 271 and len(stranded) == 5

    # The main component is undirected only for layout; arrow direction remains in the data.
    positions = nx.spring_layout(undirected.subgraph(giant), seed=28, iterations=180, weight=None)
    nodes = []
    for node in graph:
        component = "main" if node in giant else "island" if node in island else "isolate"
        xy = positions.get(node, (0, 0))
        nodes.append({
            "id": node, "name": graph.nodes[node]["name"], "url": graph.nodes[node]["url"],
            "in": graph.in_degree(node), "out": graph.out_degree(node), "degree": undirected.degree(node),
            "component": component, "x": float(xy[0]), "y": float(xy[1]),
        })
    return {
        "snapshot": "2026-08-26", "stats": stats, "nodes": nodes,
        "edges": [list(e) for e in graph.edges],
        "distributions": {
            "in": distribution([d for _, d in graph.in_degree()]),
            "out": distribution([d for _, d in graph.out_degree()]),
        },
        "island": island,
    }


def make_figure(graph, result):
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    fig.patch.set_facecolor("#f4f5f1")
    for ax, mode, title in zip(axes, ["in", "out"], ["Who gets mentioned?", "Who links out?"]):
        ax.set_facecolor("#f4f5f1")
        data = result["distributions"][mode]
        raw = [r for r in data["raw"] if r["p"] > 0]
        bins = [b for b in data["binned"] if b["p"] > 0]
        ax.scatter([r["u"] for r in raw], [r["p"] for r in raw], color="#12685e", alpha=.55, label="Raw P(k)")
        ax.plot([b["u"] for b in bins], [b["p"] for b in bins], "o-", color="#d34a27", label="Mixed bins")
        ax.set(xscale="log", yscale="log", xlabel="k + 1 (degree zero included)",
               ylabel="Probability per unit degree", title=title)
        ax.grid(alpha=.18)
        ax.legend(frameon=False)
    fig.savefig(ASSETS / "week1-degrees.svg", metadata={"Date": None})
    plt.close(fig)


def main():
    graph = load_graph()
    result = analyze(graph)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "week1.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    make_figure(graph, result)
    print(json.dumps(result["stats"], indent=2))
    return graph, result


if __name__ == "__main__":
    main()

