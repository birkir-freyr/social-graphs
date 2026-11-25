"""Is an actor's betweenness unusual beyond the number of films they are in?

Null model (course Week 2-3): degree-preserving swaps on the bipartite actor-film graph.
Each swap picks two casting links (a1-f1, a2-f2) and rewires them to (a1-f2, a2-f1) if neither
new link exists. Every actor keeps their number of films and every film its cast size; only
WHO is in WHICH film is randomised. 10 x m successful swaps per realisation, 200 realisations,
each started from the observed graph. For the actors in Table 1 we report the observed
betweenness, the null mean and SD, z, and the corrected empirical p (1 + #null >= obs)/(B + 1).

Run with networkx available, from 'Final project':  python investigations/betweenness_null.py
"""
import csv, json, os, random, statistics as st
import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G_all = nx.read_graphml(os.path.join(ROOT, "data/nolan/graphs/nolan_bipartite.graphml"))
G = G_all.copy()
G.remove_edges_from([(a, b) for a, b, d in G_all.edges(data=True)
                     if d["uncredited"] or d["voice"] or d["archive_footage"]])
G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
actors = [n for n, d in G.nodes(data=True) if d["node_type"] == "actor"]
films = [n for n, d in G.nodes(data=True) if d["node_type"] == "film"]
print(f"observed: {len(actors)} actors, {len(films)} films, {G.number_of_edges()} links")

obs = nx.betweenness_centrality(G, normalized=True)
focus = sorted((a for a in actors if G.degree(a) >= 4), key=lambda a: -obs[a])


def rewire(g, n_swaps, rng):
    g = g.copy()
    edges = [(a, f) if g.nodes[a]["node_type"] == "actor" else (f, a) for a, f in g.edges()]
    done = 0
    while done < n_swaps:
        i, j = rng.randrange(len(edges)), rng.randrange(len(edges))
        (a1, f1), (a2, f2) = edges[i], edges[j]
        if a1 == a2 or f1 == f2 or g.has_edge(a1, f2) or g.has_edge(a2, f1):
            continue
        g.remove_edge(a1, f1); g.remove_edge(a2, f2)
        g.add_edge(a1, f2); g.add_edge(a2, f1)
        edges[i], edges[j] = (a1, f2), (a2, f1)
        done += 1
    return g


rng = random.Random(2805)
B = 200
null = {a: [] for a in focus}
connected = 0
for b in range(B):
    h = rewire(G, 10 * G.number_of_edges(), rng)
    assert all(h.degree(n) == G.degree(n) for n in G), "degree changed"
    connected += nx.is_connected(h)
    bc = nx.betweenness_centrality(h, normalized=True)
    for a in focus:
        null[a].append(bc[a])

rows = []
for a in focus:
    mu, sd = st.mean(null[a]), st.pstdev(null[a])
    p_hi = (1 + sum(x >= obs[a] for x in null[a])) / (B + 1)
    p_lo = (1 + sum(x <= obs[a] for x in null[a])) / (B + 1)
    rows.append(dict(actor=G.nodes[a]["label"], films=G.degree(a), observed=round(obs[a], 4),
                     null_mean=round(mu, 4), null_sd=round(sd, 4),
                     z=round((obs[a] - mu) / sd, 2) if sd else None,
                     p_two_sided=round(min(1, 2 * min(p_hi, p_lo)), 4)))
    print(f"{rows[-1]['actor']:<16} films {rows[-1]['films']}  observed {obs[a]:.4f}  null "
          f"{mu:.4f} ± {sd:.4f}  z {rows[-1]['z']:+.2f}  p {rows[-1]['p_two_sided']:.4f}")
print(f"null graphs connected: {connected}/{B}")
json.dump(dict(B=B, swaps_per_realisation=10 * G.number_of_edges(), rows=rows,
               null_connected=connected), open(os.path.join(ROOT, "investigations/betweenness_null.json"), "w"),
          indent=1)
