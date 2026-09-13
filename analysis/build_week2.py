"""Reproduce the Week 2 friendship-paradox story from the frozen public TSVs.

Run: python analysis/build_week2.py
Only NetworkX is needed. All sampling expectations are exact sums; the null
ensembles use 100 independent starts, each with 10m successful edge swaps.
"""
import csv
import hashlib
import json
from pathlib import Path
import statistics

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data"
SEED = 21109
REPLICATES = 100


def load_graph():
    with (DATA / "week1_nodes.tsv").open() as f:
        rows = list(csv.DictReader((s for s in f if not s.startswith("#")), delimiter="\t"))
    with (DATA / "week1_edges.tsv").open() as f:
        edges = list(csv.reader((s for s in f if not s.startswith("#")), delimiter="\t"))
    g = nx.Graph()
    g.add_nodes_from((r["node_id"], r) for r in rows)
    assert len(rows) == len(g) == 303
    assert len(edges) == len(set(map(tuple, edges))) == 1784
    assert all(u in g and v in g and u != v for u, v in edges)
    g.add_edges_from(edges)
    assert g.number_of_edges() == 1434 and nx.number_of_isolates(g) == 17
    return g


def metrics(g):
    degrees = dict(g.degree())
    eligible = [v for v in g if degrees[v]]
    mean = sum(degrees.values()) / len(g)
    variance = statistics.pvariance(degrees.values())
    person = sum(degrees.values()) / len(eligible)
    friend = sum(sum(degrees[w] for w in g[v]) / degrees[v] for v in eligible) / len(eligible)
    fraction = sum(sum(degrees[w] >= degrees[v] for w in g[v]) / degrees[v] for v in eligible) / len(eligible)
    endpoint = sum(k*k for k in degrees.values()) / sum(degrees.values())
    gap = sum(degrees[u]/degrees[v] + degrees[v]/degrees[u] - 2 for u, v in g.edges()) / len(eligible)
    assert abs(endpoint - (mean + variance / mean)) < 1e-10
    assert abs(friend - person - gap) < 1e-10 and gap >= 0
    return {"n": len(g), "m": g.number_of_edges(), "eligible": len(eligible),
            "isolates": len(g)-len(eligible), "allMean": mean, "variance": variance,
            "personMean": person, "friendMean": friend, "fractionGE": fraction,
            "endpointMean": endpoint, "gap": gap}


def graph_payload(g, source_nodes):
    ids = list(g)
    indices = {v: i for i, v in enumerate(ids)}
    d = dict(g.degree())
    eligible = [v for v in ids if d[v]]
    nodes = []
    for v in ids:
        attr = source_nodes.get(v, {})
        probability = sum(1/d[w] for w in g[v]) / len(eligible)
        nodes.append({"id": v, "name": attr.get("name", f"Node {v}"), "degree": d[v],
                      "friendProbability": probability,
                      "neighborMean": sum(d[w] for w in g[v])/d[v] if d[v] else None,
                      "higherNeighbors": sum(d[w] > d[v] for w in g[v]),
                      "x": attr.get("x", 0), "y": attr.get("y", 0)})
    assert abs(sum(n["friendProbability"] for n in nodes)-1) < 1e-10
    assert abs(sum(n["friendProbability"]*n["degree"] for n in nodes)-metrics(g)["friendMean"]) < 1e-10
    return {"stats": metrics(g), "nodes": nodes, "edges": [[indices[u], indices[v]] for u, v in g.edges()]}


def build():
    g = load_graph()
    original = metrics(g)
    # Reuse Week 1's seeded layout to keep the same characters in the same places.
    layout = {n["id"]: n for n in json.loads((DATA / "week1.json").read_text())["nodes"]}
    trials = []
    representative = {}
    for i in range(REPLICATES):
        shuffled = g.copy()
        nx.double_edge_swap(shuffled, nswap=10*g.number_of_edges(), max_tries=1000*g.number_of_edges(), seed=SEED+i)
        assert dict(shuffled.degree()) == dict(g.degree())
        assert nx.number_of_selfloops(shuffled) == 0
        er = nx.gnm_random_graph(len(g), g.number_of_edges(), seed=SEED+1000+i)
        er = nx.relabel_nodes(er, dict(enumerate(g.nodes())))
        for label, h, seed in [("shuffle", shuffled, SEED+i), ("random", er, SEED+1000+i)]:
            values = metrics(h)
            trials.append({"model": label, "trial": i, "seed": seed, **values})
            if label == "shuffle":
                assert abs(values["endpointMean"]-original["endpointMean"]) < 1e-10
            if i == 0:
                representative[label] = graph_payload(h, layout)
    ensembles = {}
    for label in ["shuffle", "random"]:
        block = [t for t in trials if t["model"] == label]
        values = [t["friendMean"] for t in block]
        upper = (1+sum(x >= original["friendMean"] for x in values))/(REPLICATES+1)
        lower = (1+sum(x <= original["friendMean"] for x in values))/(REPLICATES+1)
        ensembles[label] = {"mean": statistics.mean(values), "sd": statistics.stdev(values),
                            "min": min(values), "max": max(values), "values": values,
                            "pTwoSided": min(1, 2*min(upper, lower)),
                            "gapMean": statistics.mean(t["gap"] for t in block)}
    real = graph_payload(g, layout)
    leaders = sorted(real["nodes"], key=lambda n: (-n["friendProbability"], n["name"]))[:5]
    local_peaks = sorted((n for n in real["nodes"] if n["degree"] and not n["higherNeighbors"]),
                         key=lambda n: (-n["degree"], n["name"]))
    sources = {name: hashlib.sha256((DATA/name).read_bytes()).hexdigest()
               for name in ["week1_nodes.tsv", "week1_edges.tsv"]}
    result = {"snapshot": "2026-08-26", "seed": SEED, "replicates": REPLICATES,
              "networkxVersion": nx.__version__, "sourceSHA256": sources,
              "graphs": {"real": real, **representative}, "ensembles": ensembles,
              "leaders": leaders, "localPeaks": local_peaks,
              "notes": {"edgeMeaning": "An undirected pair exists if either Wikipedia page links to the other.",
                        "sampling": "Uniform nonisolated person, then uniform neighbor; ties included in friend >= person.",
                        "null": "Fresh copy of observed simple graph for every shuffle; 10m successful swaps; connectivity unconstrained.",
                        "test": "Two-sided equal-tail corrected Monte Carlo test of exact person-first friend mean; minimum p=2/101.",
                        "layout": "Week 1 coordinates reused across models; placement is not a measurement."}}
    (DATA/"week2.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n")
    with (DATA/"week2-null-trials.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trials[0])); w.writeheader(); w.writerows(trials)
    print(json.dumps({"real": original, "ensembles": {k: {a:b for a,b in v.items() if a != "values"} for k,v in ensembles.items()},
                      "leaders": [{k:n[k] for k in ["name", "degree", "friendProbability"]} for n in leaders],
                      "localPeaks": [{k:n[k] for k in ["name", "degree"]} for n in local_peaks]}, indent=2))
    return result


if __name__ == "__main__":
    star = metrics(nx.star_graph(3))
    assert (star["allMean"], star["friendMean"], star["endpointMean"]) == (1.5, 2.5, 2.0)
    regular = metrics(nx.cycle_graph(8))
    assert regular["gap"] == 0 and regular["endpointMean"] == 2
    build()
