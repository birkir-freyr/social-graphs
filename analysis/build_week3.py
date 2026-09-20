"""Build the Week 3 targeted-removal story from the frozen Marvel TSVs.

Run: python analysis/build_week3.py

The analysis uses the undirected giant component. Degree and betweenness are
recomputed after every removal; the random envelope contains 500 independent
removal orders. The Week 1 JSON contributes layout coordinates only.
"""

import csv
import hashlib
import json
from pathlib import Path
import random
import statistics

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data"
SEED = 31209
RANDOM_TRIALS = 500
MAX_REMOVALS = 100


def load_graph():
    with (DATA / "week1_nodes.tsv").open() as handle:
        rows = list(
            csv.DictReader(
                (line for line in handle if not line.startswith("#")),
                delimiter="\t",
            )
        )
    with (DATA / "week1_edges.tsv").open() as handle:
        edges = list(
            csv.reader(
                (line for line in handle if not line.startswith("#")),
                delimiter="\t",
            )
        )

    graph = nx.Graph()
    graph.add_nodes_from((row["node_id"], row) for row in rows)
    graph.add_edges_from(edges)
    assert len(graph) == 303
    assert graph.number_of_edges() == 1434
    assert nx.number_of_isolates(graph) == 17

    giant_nodes = max(nx.connected_components(graph), key=len)
    giant = graph.subgraph(giant_nodes).copy()
    assert len(giant) == 277 and giant.number_of_edges() == 1421
    return giant


def largest_component_size(graph):
    return max((len(component) for component in nx.connected_components(graph)), default=0)


def attack(graph, names, measure):
    working = graph.copy()
    order = []
    curve = [len(working)]
    for _ in range(MAX_REMOVALS):
        if measure == "degree":
            scores = dict(working.degree())
        elif measure == "betweenness":
            scores = nx.betweenness_centrality(working)
        else:
            raise ValueError(f"Unknown measure: {measure}")
        target = min(working, key=lambda node: (-scores[node], names[node]))
        order.append(target)
        working.remove_node(target)
        curve.append(largest_component_size(working))
    return {"order": order, "curve": curve}


def single_removal_table(graph, names, betweenness):
    rows = []
    for node in graph:
        working = graph.copy()
        working.remove_node(node)
        components = sorted(nx.connected_components(working), key=len, reverse=True)
        largest = components[0]
        detached = sorted(
            (member for component in components[1:] for member in component),
            key=lambda member: names[member],
        )
        rows.append(
            {
                "id": node,
                "name": names[node],
                "degree": graph.degree(node),
                "betweenness": betweenness[node],
                "largestComponent": len(largest),
                "detachedCount": len(detached),
                "componentCount": len(components),
                "detached": [{"id": member, "name": names[member]} for member in detached],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -row["detachedCount"],
            -row["componentCount"],
            -row["betweenness"],
            row["name"],
        ),
    )


def percentile(values, probability):
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def random_envelope(graph):
    rng = random.Random(SEED)
    nodes = list(graph)
    curves = []
    for _ in range(RANDOM_TRIALS):
        order = nodes.copy()
        rng.shuffle(order)
        working = graph.copy()
        curve = [len(working)]
        for node in order[:MAX_REMOVALS]:
            working.remove_node(node)
            curve.append(largest_component_size(working))
        curves.append(curve)

    summaries = []
    for removed in range(MAX_REMOVALS + 1):
        values = [curve[removed] for curve in curves]
        summaries.append(
            {
                "removed": removed,
                "mean": statistics.mean(values),
                "q05": percentile(values, 0.05),
                "median": percentile(values, 0.50),
                "q95": percentile(values, 0.95),
            }
        )
    return curves, summaries


def first_below(curve, threshold):
    return next(index for index, value in enumerate(curve) if value < threshold)


def build():
    graph = load_graph()
    layout = {
        node["id"]: node
        for node in json.loads((DATA / "week1.json").read_text())["nodes"]
    }
    names = {node: graph.nodes[node]["name"] for node in graph}
    betweenness = nx.betweenness_centrality(graph)
    single = single_removal_table(graph, names, betweenness)
    degree_attack = attack(graph, names, "degree")
    betweenness_attack = attack(graph, names, "betweenness")
    random_curves, random_summary = random_envelope(graph)

    assert single[0]["id"] == "Spider-Man"
    assert single[0]["largestComponent"] == 271
    assert single[0]["detachedCount"] == 5
    assert degree_attack["curve"][80] == 107
    assert betweenness_attack["curve"][80] == 42
    assert first_below(degree_attack["curve"], len(graph) / 2) == 74
    assert first_below(betweenness_attack["curve"], len(graph) / 2) == 63

    nodes = []
    for node in graph:
        source = layout[node]
        nodes.append(
            {
                "id": node,
                "name": names[node],
                "url": source["url"],
                "degree": graph.degree(node),
                "betweenness": betweenness[node],
                "x": source["x"],
                "y": source["y"],
            }
        )

    result = {
        "snapshot": "2026-08-26",
        "seed": SEED,
        "randomTrials": RANDOM_TRIALS,
        "maxRemovals": MAX_REMOVALS,
        "networkxVersion": nx.__version__,
        "sourceSHA256": {
            filename: hashlib.sha256((DATA / filename).read_bytes()).hexdigest()
            for filename in ["week1_nodes.tsv", "week1_edges.tsv"]
        },
        "graph": {
            "nodes": nodes,
            "edges": [list(edge) for edge in graph.edges()],
            "stats": {"nodes": len(graph), "edges": graph.number_of_edges()},
        },
        "singleRemoval": single,
        "strategies": {
            "degree": {
                **degree_attack,
                "label": "Adaptive degree",
                "description": "Recompute degree after every removal, then remove the current hub.",
            },
            "betweenness": {
                **betweenness_attack,
                "label": "Adaptive betweenness",
                "description": "Recompute betweenness after every removal, then remove the current broker.",
            },
        },
        "random": {"summary": random_summary},
        "findings": {
            "articulationPoints": len(list(nx.articulation_points(graph))),
            "degreeFirstBelowHalf": first_below(degree_attack["curve"], len(graph) / 2),
            "betweennessFirstBelowHalf": first_below(
                betweenness_attack["curve"], len(graph) / 2
            ),
            "degreeAt80": degree_attack["curve"][80],
            "betweennessAt80": betweenness_attack["curve"][80],
            "randomMedianAt80": random_summary[80]["median"],
        },
        "notes": {
            "network": "Undirected giant component only; an edge exists when either page links to the other.",
            "strategy": "Adaptive scores are recomputed on the entire remaining graph after each removal.",
            "random": "Each trial is a fresh uniform permutation of the 277 giant-component nodes.",
            "layout": "Week 1 seeded coordinates are reused; position is not a measurement.",
        },
    }
    assert result["findings"]["articulationPoints"] == 13

    (DATA / "week3.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    with (DATA / "week3-random-trials.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["trial", "removed", "largest_component"])
        for trial, curve in enumerate(random_curves):
            writer.writerows(
                (trial, removed, size) for removed, size in enumerate(curve)
            )

    print(
        json.dumps(
            {
                "singleRemoval": single[:5],
                "findings": result["findings"],
                "randomAt80": random_summary[80],
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    build()
