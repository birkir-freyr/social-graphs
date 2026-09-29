"""Exercise 4.13: find the largest fracture along the disparity-filter sweep.

Run with Python 3.10+, networkx==3.4.2 and numpy==1.26.0.
No network requests: inputs are the frozen course TSVs bundled with the post.
"""
import csv
import hashlib
import json
import math
from itertools import groupby
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data"


def load_graph():
    def rows(filename):
        with (DATA / filename).open(encoding="utf-8") as stream:
            return list(csv.DictReader((s for s in stream if not s.startswith("#")),
                                       delimiter="\t", quoting=csv.QUOTE_NONE))
    graph = nx.Graph()
    graph.add_nodes_from((r["node_id"], r) for r in rows("week4_philosophers_nodes.tsv"))
    for row in rows("week4_philosophers_edges.tsv"):
        u, v, w = row["source"], row["target"], int(row["weight"])
        assert u in graph and v in graph and u != v
        graph.add_edge(u, v, weight=graph.get_edge_data(u, v, {}).get("weight", 0) + w)
    assert (len(graph), graph.number_of_edges()) == (1444, 9140)
    giant = graph.subgraph(max(nx.connected_components(graph), key=len)).copy()
    assert (len(giant), giant.number_of_edges()) == (1374, 9139)
    return graph, giant


def significance(graph):
    strength = dict(graph.degree(weight="weight"))
    edges = []
    for u, v, data in graph.edges(data=True):
        w = data["weight"]
        scores = [(1 - w / strength[n]) ** (graph.degree(n) - 1) for n in (u, v)]
        edges.append({"source": u, "target": v, "weight": w,
                      "score": min(scores), "ends": scores})
    return sorted(edges, key=lambda e: (e["score"], e["source"], e["target"]))


def backbone(graph, edges, alpha):
    out = nx.Graph()
    out.add_nodes_from(graph)
    out.add_edges_from((e["source"], e["target"]) for e in edges if e["score"] < alpha)
    return out


def counts(graph):
    components = sorted(nx.connected_components(graph), key=lambda c: (-len(c), min(c)))
    return {"links": graph.number_of_edges(), "active": len(graph) - nx.number_of_isolates(graph),
            "giant": len(components[0]), "components": len(components),
            "isolates": nx.number_of_isolates(graph)}


def stable_layout(graph, **kwargs):
    """Give seeded layouts stable node/edge order across Python hash seeds.

    NetworkX subgraph views can iterate their node-filter sets in hash order.
    A fixed random seed alone does not stabilize that input ordering.
    """
    ordered = nx.Graph()
    ordered.add_nodes_from(sorted(graph))
    ordered.add_edges_from(sorted((min(u, v), max(u, v)) for u, v in graph.edges()))
    return nx.spring_layout(ordered, seed=413, weight=None, **kwargs)


def sweep(graph, edges):
    """Add equal-score batches together; reverse this sequence to tighten alpha.

    A score t is excluded at alpha=t, included just above t. Union-find yields
    every component-size event without repeatedly traversing the full graph.
    """
    parent = {n: n for n in graph}
    sizes = {n: 1 for n in graph}
    active = set()
    largest, links, components = 1, 0, len(graph)
    def root(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    events = []
    for score, batch in groupby(edges, key=lambda e: e["score"]):
        batch = list(batch)
        before = largest
        for e in batch:
            u, v = e["source"], e["target"]
            active.update((u, v))
            a, b = root(u), root(v)
            if a != b:
                if sizes[a] < sizes[b]:
                    a, b = b, a
                parent[b] = a
                sizes[a] += sizes[b]
                largest = max(largest, sizes[a])
                components -= 1
        links += len(batch)
        events.append({"score": score, "below": before, "above": largest,
                       "drop": largest - before, "links_above": links,
                       "active_above": len(active), "components_above": components,
                       "removed": batch})
    assert largest == len(graph) and links == graph.number_of_edges()
    return events


def build():
    full, graph = load_graph()
    edges = significance(graph)
    events = sweep(graph, edges)
    critical = max(events, key=lambda e: e["drop"])
    threshold = critical["score"]
    before = backbone(graph, edges, math.nextafter(threshold, math.inf))
    after = backbone(graph, edges, threshold)
    assert counts(before)["giant"] - counts(after)["giant"] == critical["drop"]
    old_giant = max(nx.connected_components(before), key=len)
    fragments = sorted(nx.connected_components(after.subgraph(old_giant)), key=lambda c: (-len(c), min(c)))
    strength = dict(graph.degree(weight="weight"))
    communities = sorted(nx.community.louvain_communities(graph, weight=None, seed=0),
                         key=lambda c: (-len(c), min(c)))
    membership = {n: i for i, community in enumerate(communities) for n in community}
    def leaders(group, limit=5):
        return sorted(group, key=lambda n: (-strength[n], n))[:limit]
    critical["fragments"] = [{"size": len(c), "leaders": leaders(c), "nodes": sorted(c)} for c in fragments]
    critical["before"] = counts(before)
    critical["after"] = counts(after)
    detail_positions = stable_layout(before.subgraph(old_giant), iterations=250)
    # A fixed 90-degree rotation fits the wide close-up; it changes no distances.
    critical["positions"] = {n: [round(float(p[1]), 6), round(float(-p[0]), 6)]
                             for n, p in detail_positions.items()}
    critical["single_link_removals"] = []
    for e in critical["removed"]:
        trial = before.copy()
        trial.remove_edge(e["source"], e["target"])
        critical["single_link_removals"].append({"source": e["source"], "target": e["target"], **counts(trial)})
    communities_out = [{"size": len(c), "leaders": leaders(c), "id": i} for i, c in enumerate(communities)]
    # The baseline is a backbone layout. All views share it so motion cannot
    # create apparent splits. Isolates at alpha=.3 are placed in an outer ring.
    reference = backbone(graph, edges, .3)
    visible = reference.subgraph([n for n, d in reference.degree() if d])
    # Lay out disconnected components separately: unconstrained spring repulsion
    # otherwise sends the small pieces far away and shrinks the main group.
    pieces = sorted(nx.connected_components(visible), key=lambda c: (-len(c), min(c)))
    positions = {}
    for i, piece in enumerate(pieces):
        local = stable_layout(visible.subgraph(piece), iterations=200, k=.15)
        bound = max(math.hypot(*p) for p in local.values()) or 1
        angle = 2 * math.pi * (i - 1) / max(1, len(pieces) - 1)
        cx, cy = (0, 0) if i == 0 else (math.cos(angle), math.sin(angle))
        scale = .83 if i == 0 else min(.08, .014 * math.sqrt(len(piece)))
        for n, p in local.items():
            rho = math.hypot(*p) / bound
            # Expand the dense center without moving nodes between components.
            # This is a display transform only; distances are not measurements.
            expand = rho ** (-.6) if i == 0 and rho else 1
            positions[n] = (cx + scale * float(p[0]) / bound * expand,
                            cy + scale * float(p[1]) / bound * expand)
    radius = 1.2
    isolates = sorted(set(graph) - set(visible))
    for i, n in enumerate(isolates):
        angle = 2 * math.pi * i / len(isolates)
        positions[n] = (radius * math.cos(angle), radius * math.sin(angle))
    extent = max(max(abs(float(x)), abs(float(y))) for x, y in positions.values())
    nodes = [{"id": n, "name": graph.nodes[n]["name"], "url": graph.nodes[n]["url"],
              "degree": graph.degree(n), "strength": strength[n], "community": membership[n],
              "x": round(float(positions[n][0]) / extent, 6), "y": round(float(positions[n][1]) / extent, 6),
              "ring": n in isolates} for n in graph]
    alphas = [.05, .1, .2, .3, .5]
    snapshots = [{"alpha": a, **counts(backbone(graph, edges, a))} for a in alphas]
    assert [(r["links"], r["active"], r["giant"]) for r in snapshots] == [
        (292, 348, 116), (649, 607, 419), (1540, 950, 816), (2549, 1111, 1052), (5641, 1284, 1270)]
    result = {"meta": {"exercise": "4.13", "snapshot": "2026-09-15", "networkx": nx.__version__,
                        "roster_nodes": len(full), "roster_links": full.number_of_edges(),
                        "nodes": len(graph), "links": graph.number_of_edges(),
                        "louvain_seed": 0, "layout_seed": 413, "layout_alpha": .3,
                        "community_q": nx.community.modularity(graph, communities, weight=None),
                        "hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(DATA.glob("week4_philosophers_*.tsv"))}},
              "nodes": nodes, "edges": edges, "communities": communities_out,
              "snapshots": snapshots, "critical": critical,
              "curve": [{k: e[k] for k in ("score", "below", "above", "drop")} for e in events]}
    (DATA / "week4.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    with (DATA / "week4-sweep.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=["score", "giant_at_score", "giant_just_above", "drop_when_tightening"])
        writer.writeheader()
        writer.writerows({"score": e["score"], "giant_at_score": e["below"],
                          "giant_just_above": e["above"], "drop_when_tightening": e["drop"]} for e in events)
    print(json.dumps({"critical": {k: v for k, v in critical.items() if k not in ("fragments", "positions")},
                      "fragments": [{"size": f["size"], "leaders": f["leaders"]} for f in critical["fragments"]],
                      "communities": communities_out, "snapshots": snapshots}, indent=2))


if __name__ == "__main__":
    build()
