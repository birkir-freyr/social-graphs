import csv
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import networkx as nx


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    data = Path(__file__).resolve().parent / "data" / "nolan"
    films = [row for row in read_rows(data / "nolan_films.csv") if row["included"] == "True"]
    actors = read_rows(data / "actors.csv")
    credits = read_rows(data / "nolan_cast.csv")
    graph = nx.Graph(name="Nolan actor-film network")

    for actor in actors:
        node_id = f"actor:{actor['actor_id']}"
        if node_id in graph:
            raise ValueError(f"Duplicate actor ID {actor['actor_id']}")
        graph.add_node(
            node_id, node_type="actor", bipartite=0,
            tmdb_id=int(actor["actor_id"]), label=actor["actor_name"],
        )
    for film in films:
        node_id = f"film:{film['film_id']}"
        if node_id in graph:
            raise ValueError(f"Duplicate film ID {film['film_id']}")
        graph.add_node(
            node_id, node_type="film", bipartite=1,
            tmdb_id=int(film["film_id"]), label=film["title"],
            year=int(film["wikipedia_year"]), release_date=film["release_date"],
            year_conflict=film["year_conflict"] == "True", genres=film["genres"],
            source_url=film["source_url"],
        )
    for credit in credits:
        actor_id = f"actor:{credit['actor_id']}"
        film_id = f"film:{credit['film_id']}"
        if actor_id not in graph or film_id not in graph:
            raise ValueError(f"Casting credit references an unknown node: {credit['credit_id']}")
        if graph.has_edge(actor_id, film_id):
            raise ValueError(f"Multiple casting rows for {actor_id} and {film_id}; review before combining")
        graph.add_edge(
            actor_id, film_id, relation="cast", character=credit["character"],
            credit_id=credit["credit_id"], cast_order=int(credit["cast_order"]),
            uncredited=credit["uncredited"] == "True",
            archive_footage=credit["archive_footage"] == "True",
            voice=credit["voice"] == "True", source_url=credit["source_url"],
        )

    actor_nodes = {node for node, attributes in graph.nodes(data=True) if attributes["node_type"] == "actor"}
    film_nodes = set(graph) - actor_nodes
    if not nx.is_bipartite(graph):
        raise ValueError("Casting graph is not bipartite")
    if graph.number_of_edges() != len(credits):
        raise ValueError("Casting edge count differs from source row count")
    if any(graph.degree(node) == 0 for node in graph):
        raise ValueError("Unexpected isolated source node")
    for film in films:
        if graph.degree(f"film:{film['film_id']}") != int(film["cast_count"]):
            raise ValueError(f"Cast count does not match graph degree for {film['title']}")
    for actor in actors:
        if graph.degree(f"actor:{actor['actor_id']}") != int(actor["nolan_film_count"]):
            raise ValueError(f"Actor degree differs from source count for {actor['actor_name']}")

    actor_degrees = Counter(graph.degree(node) for node in actor_nodes)
    top_actors = sorted(
        ({"actor_id": graph.nodes[node]["tmdb_id"], "name": graph.nodes[node]["label"], "films": graph.degree(node)} for node in actor_nodes),
        key=lambda row: (-row["films"], row["name"]),
    )[:15]
    summary = {
        "graph": {
            "nodes": graph.number_of_nodes(), "actors": len(actor_nodes), "films": len(film_nodes),
            "casting_edges": graph.number_of_edges(), "components": nx.number_connected_components(graph),
            "actors_with_multiple_nolan_films": sum(count for degree, count in actor_degrees.items() if degree >= 2),
            "actors_with_one_nolan_film": actor_degrees[1],
            "actor_film_count_distribution": dict(sorted(actor_degrees.items())),
            "top_recurring_actors": top_actors,
        },
    }

    output = data / "graphs"
    output.mkdir(parents=True, exist_ok=True)
    graph_path = output / "nolan_bipartite.graphml"
    audit_path = output / "graph_audit.json"
    with TemporaryDirectory(dir=output) as folder:
        staged_graph = Path(folder) / graph_path.name
        staged_audit = Path(folder) / audit_path.name
        nx.write_graphml(graph, staged_graph)
        staged_audit.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staged_graph.replace(graph_path)
        staged_audit.replace(audit_path)
    print(f"Built the graph with {len(films)} films, {len(actors)} actors, and {len(credits)} cast links.")


if __name__ == "__main__":
    main()
