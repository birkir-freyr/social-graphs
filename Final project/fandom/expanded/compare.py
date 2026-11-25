"""Re-run the same-film comparison on the expanded Fandom corpus."""
import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyze import role_key
from common import load_rows, vectorise
from film_confound import placebo, scored_roles
from semantic_pilot import MODEL, REVISION, encode, paired_estimate


def compare(rows):
    pairs = placebo(rows, [r for r in scored_roles(rows) if r["is_nolan"]])
    return paired_estimate(pairs), sorted([list(role_key(r)) for r in pairs])


def main(model_dir):
    corpus = HERE / "passages.csv"
    rows = load_rows(path=str(corpus))
    with corpus.open(encoding="utf-8", newline="") as stream:
        urls = {(r["actor"], r["film"], r["character"]): r["source_url"] for r in csv.DictReader(stream)}
    by_article = {}
    for r in sorted(rows, key=lambda x: (x["year"], x["film"], x["character"])):
        if not r["is_nolan"]:
            url = urls[r["actor"], r["film"], r["character"]]
            by_article.setdefault((r["actor"], url), role_key(r))
    keep = set(by_article.values())
    dense, _ = encode([r["text"] for r in rows], model_dir)
    lexical = vectorise([dict(r) for r in rows])
    semantic = [dict(r, v=dict(enumerate(dense[r["text"]].tolist()))) for r in rows]
    with (HERE.parent / "results/fandom_scores.csv").open(newline="", encoding="utf-8") as stream:
        old_roles = {(r["actor"], r["film"], int(r["year"]), r["character"])
                     for r in csv.DictReader(stream) if r["group"] == "nolan" and int(r["n_costars"])}
    report = {"model": MODEL, "revision": REVISION}
    for name, scored in (("tfidf", lexical), ("minilm", semantic)):
        full, roles = compare(scored)
        sensitivity, _ = compare([r for r in scored if r["is_nolan"] or role_key(r) in keep])
        report[name] = {"all": full, "one_earlier_role_per_article": sensitivity}
        new_roles = [r for r in roles if tuple(r) not in old_roles]
        if name == "tfidf":
            report["newly_eligible_nolan_roles"] = new_roles
        elif new_roles != report["newly_eligible_nolan_roles"]:
            raise ValueError("The two methods disagree on which roles are eligible")
    (HERE / "comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path)
    main(parser.parse_args().model_dir)
