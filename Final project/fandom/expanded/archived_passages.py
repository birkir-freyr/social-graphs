"""Export supplemental plot and cast passages for credits missing from both text corpora."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from collect_character_text import GENERIC_NAMES, normalized, read_csv
from collect_nolan import save_csv
from collect_passages import blind, name_keys
from typecast import MIN_WORDS

TITLES = GENERIC_NAMES | set("mr mrs dr det maj lt sir specialist president warden pastor uncle "
                             "crew chief taxi sailor cinema fight chairman hitman".split())
FIELDS = ("actor", "film", "year", "character", "is_nolan", "role_id", "source", "source_url",
          "source_version", "source_sha256", "source_locations", "review_status", "n_words_blind",
          "role_text", "role_text_blind")


def credit_key(actor, film, year):
    return normalized(actor), normalized(film), year


def selected_evidence(role, character):
    is_nolan = role["is_nolan_film"]
    if not is_nolan and role.get("cmu_match_status") != "title_actor_year_match":
        return []
    labels = role.get("wikipedia_character_labels" if is_nolan else "cmu_character_names", [])
    names = (set(normalized(character).split()) - TITLES) & set(normalized(" ".join(labels)).split())
    if not names:
        return []
    selected = {}
    for item in role["evidence"]:
        if item["kind"] == "cast_description" and is_nolan:
            selected.setdefault(item["text"], item)
        elif item["kind"] == "plot_passage":
            # Reject hits supported only by a title or a lowercase word such as "will".
            if any(names.intersection(normalized(alias).split())
                   and re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", item["text"])
                   for alias in item["matched_aliases"]):
                selected.setdefault(item["text"], item)
    return list(selected.values())


def location(item):
    if item["kind"] == "cast_description":
        return item["locator"]
    paragraph = f"paragraph {item['paragraph_index']}, " if "paragraph_index" in item else ""
    return f"{paragraph}characters {item['start']}-{item['end']}"


def main(archive):
    fandom = read_csv(HERE / "passages.csv")
    original = {(r["actor"], r["film"], r["year"], r["character"]): r
                for r in read_csv(ROOT / "passages.csv")}
    missing = {}
    for r in fandom:
        old = original[r["actor"], r["film"], r["year"], r["character"]]
        if r["status"] != "usable" and len(old["role_text_blind"].split()) < MIN_WORDS:
            key = credit_key(r["actor"], r["film"], r["year"])
            if key in missing:
                raise ValueError(f"Ambiguous roster credit: {key}")
            missing[key] = r

    records = {}
    with archive.open(encoding="utf-8") as file:
        for line in file:
            role = json.loads(line)
            key = credit_key(role["actor_name"], role["film_title"], role["year"])
            if key not in missing:
                continue
            r = missing[key]
            items = selected_evidence(role, r["character"])
            raw = "\n".join(item["text"] for item in items)
            masked = blind(raw, name_keys(r["character"]), r["film"])
            if len(masked.split()) < MIN_WORDS:
                continue
            is_nolan = role["is_nolan_film"]
            signature = {(i["source_url"], str(i["revision_id"]) if is_nolan else i["source_snapshot"],
                          i["source_sha256"] if is_nolan else i["plot_sha256"]) for i in items}
            if key in records or len(signature) != 1 or is_nolan != (r["is_nolan"] == "1"):
                raise ValueError(f"Conflicting source or credit: {key}")
            url, version, digest = signature.pop()
            records[key] = {**r, "role_id": role["role_id"],
                            "source": "Wikipedia" if is_nolan else "CMU Movie Summary Corpus",
                            "source_url": url + "?oldid=" + version if is_nolan else url,
                            "source_version": version, "source_sha256": digest,
                            "source_locations": " | ".join(location(i) for i in items),
                            "review_status": "needs_human_review", "n_words_blind": len(masked.split()),
                            "role_text": raw, "role_text_blind": masked}
    save_csv(HERE / "archived_passages.csv", FIELDS, [records[k] for k in sorted(records)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path,
                        default=ROOT / "data/nolan/character_descriptions.jsonl")
    main(parser.parse_args().archive)
