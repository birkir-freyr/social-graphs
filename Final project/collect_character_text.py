"""Collect character descriptions and named plot passages for the Nolan study.

Uses the saved Wikipedia pages for Nolan films and the CMU Movie Summary Corpus
for historical roles. Every output passage is an extract from a saved source.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

from collect_nolan import ROOT, save_csv, save_json, save_text


CORPUS_URL = "https://www.cs.cmu.edu/~ark/personas/data/MovieSummaries.tar.gz"
GENERIC_NAMES = {
    "the", "and", "young", "old", "older", "younger", "adult", "child",
    "boy", "girl", "unknown", "unnamed", "first", "second", "third",
    "man", "woman", "boy", "girl", "young", "old", "self", "himself", "herself",
    "soldier", "officer", "policeman", "police", "pilot", "guard", "doctor",
    "professor", "general", "captain", "lieutenant", "sergeant", "reporter",
    "driver", "nurse", "waiter", "waitress", "voice", "radio", "cop", "thug",
    "prisoner", "judge", "assistant", "agent", "scientist", "civilian",
}
ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "gen.", "lt.", "sgt.", "st.", "jr.", "sr."}


def normalized(text):
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sentences(text):
    start = 0
    for boundary in re.finditer(r'(?<=[.!?])\s+(?=[A-Z0-9"“])', text):
        token = text[:boundary.start()].split()[-1]
        if token.lower() in ABBREVIATIONS or re.fullmatch(r"(?:[A-Z]\.)+", token):
            continue
        yield start, boundary.start(), text[start:boundary.start()]
        start = boundary.end()
    if start < len(text):
        yield start, len(text), text[start:]


def name_variants(labels):
    variants = set()
    for label in labels:
        cleaned = re.sub(r"\([^)]*\)", "", label)
        for name in re.split(r"\s+/\s+", cleaned):
            name = name.strip().strip(".,:")
            name = re.sub(r",?\s+(?:Jr|Sr)\.?$", "", name).strip()
            if not name:
                continue
            variants.add(name)
            variants.update(re.findall(r'["“]([^"”]+)["”]', name))
            without_title = re.sub(
                r"^(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?|Professor|Gen\.?|General|Lt\.?)\s+",
                "", name, flags=re.IGNORECASE,
            )
            variants.add(without_title)
            words = without_title.split()
            if len(words) > 1:
                variants.update((words[0], words[-1]))
    return {
        name for name in variants
        if len(normalized(name)) >= 3
        and normalized(name) not in GENERIC_NAMES
        and not any(character.isdigit() for character in name)
    }


def unique_aliases(labels, roster, owner):
    owners = defaultdict(set)
    for identity, names in roster:
        for alias in name_variants(names):
            owners[normalized(alias)].add(identity)
    return sorted(
        (alias for alias in name_variants(labels) if owners[normalized(alias)] == {owner}),
        key=lambda alias: (-len(alias), alias),
    )


def extract_passages(text, aliases):
    patterns = [
        (alias, re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", re.IGNORECASE))
        for alias in aliases
    ]
    passages = []
    for start, end, sentence in sentences(text):
        matched = [alias for alias, pattern in patterns if pattern.search(sentence)]
        if matched:
            passages.append({
                "text": sentence, "start": start, "end": end,
                "matched_aliases": matched,
            })
    return passages


def load_roles(directory):
    actors = {row["actor_id"]: row["actor_name"] for row in read_csv(directory / "actors.csv")}
    films = {row["film_id"]: row for row in read_csv(directory / "nolan_films.csv")}
    histories = read_csv(directory / "actor_movie_credits.csv")
    history_by_pair = defaultdict(list)
    for row in histories:
        history_by_pair[(row["actor_id"], row["film_id"])].append(row)
    roles = {}
    for row in read_csv(directory / "nolan_cast.csv"):
        key = (row["actor_id"], row["film_id"])
        roles[key] = {
            "actor_id": row["actor_id"], "actor_name": row["actor_name"],
            "film_id": row["film_id"], "film_title": films[row["film_id"]]["title"],
            "year": films[row["film_id"]]["wikipedia_year"],
            "tmdb_character_names": [row["character"]] if row["character"] else [],
            "is_nolan_film": True, "historical_order_statuses": [],
        }
    for link in read_csv(directory / "historical_links.csv"):
        key = (link["actor_id"], link["prior_film_id"])
        credits = history_by_pair[key]
        role = roles.setdefault(key, {
            "actor_id": key[0], "actor_name": actors[key[0]], "film_id": key[1],
            "film_title": credits[0]["title"], "year": credits[0]["year"],
            "tmdb_character_names": sorted({row["character"] for row in credits if row["character"]}),
            "is_nolan_film": key[1] in films, "historical_order_statuses": [],
        })
        if link["release_order_status"] not in role["historical_order_statuses"]:
            role["historical_order_statuses"].append(link["release_order_status"])
    for role in roles.values():
        role["role_id"] = f"tmdb:{role['actor_id']}:{role['film_id']}"
        role["historical_order_statuses"].sort()
        role["evidence"] = []
    return roles, films


def wikipedia_cast(soup):
    heading = soup.find(id="Cast")
    if heading is None:
        return []
    start = heading.parent if "mw-heading" in heading.parent.get("class", []) else heading
    entries = []
    for node in start.next_siblings:
        if not getattr(node, "name", None):
            continue
        if node.name == "h2" or "mw-heading2" in node.get("class", []):
            break
        for item in node.find_all("li"):
            clean = BeautifulSoup(str(item), "html.parser")
            for extra in clean.select("ul, ol, sup.reference, .mw-editsection"):
                extra.decompose()
            text = clean.get_text(" ", strip=True)
            actor, separator, body = text.partition(" as ")
            if not separator:
                continue
            _, _, intro = next(sentences(body))
            label = re.split(r"[:,]\s+", intro, maxsplit=1)[0].strip(" .:")
            descriptive = re.search(r"[:,]\s+(.+)", intro)
            has_description = bool(descriptive and len(descriptive.group(1).split()) >= 5)
            entries.append({
                "actor_name": actor, "character_label": label,
                "excerpt": intro, "has_description": has_description,
                "locator": f"Cast list item {len(entries) + 1}",
            })
    return entries


def collect_nolan_descriptions(directory, roles):
    sources = {row["sha256"]: row for row in json.loads((directory / "sources.json").read_text())}
    plots = [json.loads(line) for line in (directory / "nolan_plots.jsonl").read_text().splitlines()]
    by_film = defaultdict(list)
    for role in roles.values():
        if role["is_nolan_film"]:
            by_film[role["film_id"]].append(role)
    for plot in plots:
        source = sources[plot["source_sha256"]]
        soup = BeautifulSoup(gzip.decompress((directory / source["raw_path"]).read_bytes()), "html.parser")
        cast = wikipedia_cast(soup)
        cast_by_actor = defaultdict(list)
        for entry in cast:
            cast_by_actor[normalized(entry["actor_name"])].append(entry)
        film_roles = by_film[str(plot["film_id"])]
        roster = []
        for role in film_roles:
            entries = cast_by_actor[normalized(role["actor_name"])]
            labels = role["tmdb_character_names"] + [entry["character_label"] for entry in entries]
            role["wikipedia_character_labels"] = [entry["character_label"] for entry in entries]
            roster.append((role["role_id"], labels))
            for entry in entries:
                if entry["has_description"]:
                    role["evidence"].append({
                        "kind": "cast_description", "text": entry["excerpt"],
                        "source_url": plot["source_url"], "revision_id": plot["revision_id"],
                        "source_sha256": plot["source_sha256"], "locator": entry["locator"],
                        "matching_method": "actor_name_in_film_cast_section",
                        "review_status": "needs_human_review",
                    })
        for role in film_roles:
            labels = role["tmdb_character_names"] + role["wikipedia_character_labels"]
            aliases = unique_aliases(labels, roster, role["role_id"])
            role["wikipedia_aliases"] = aliases
            for index, paragraph in enumerate(plot["paragraphs"]):
                for passage in extract_passages(paragraph, aliases):
                    role["evidence"].append({
                        **passage, "kind": "plot_passage", "paragraph_index": index,
                        "source_url": plot["source_url"], "revision_id": plot["revision_id"],
                        "source_sha256": plot["source_sha256"],
                        "matching_method": "name_unique_within_cast_roster",
                        "review_status": "needs_human_review",
                    })


def archive_rows(archive, name):
    handle = archive.extractfile(f"MovieSummaries/{name}")
    if handle is None:
        raise ValueError(f"Missing corpus member {name}")
    with io.TextIOWrapper(handle, encoding="utf-8") as stream:
        for line in stream:
            yield line.rstrip("\r\n").split("\t")


def collect_cmu_descriptions(directory, roles, archive_path):
    with tarfile.open(archive_path, "r:gz") as archive:
        movies = {}
        by_title = defaultdict(list)
        for row in archive_rows(archive, "movie.metadata.tsv"):
            if len(row) != 9:
                raise ValueError("Unexpected CMU movie metadata row")
            movies[row[0]] = {
                "wikipedia_id": row[0], "title": row[2], "release_date": row[3],
                "runtime_minutes": row[5], "genres": json.loads(row[8]),
            }
            by_title[normalized(row[2])].append(row[0])
        characters = defaultdict(list)
        for row in archive_rows(archive, "character.metadata.tsv"):
            if len(row) != 13:
                raise ValueError("Unexpected CMU character metadata row")
            characters[row[0]].append({
                "character_name": row[3], "actor_name": row[8],
                "character_map_id": row[10], "actor_id": row[12],
            })
        plots = {}
        for row in archive_rows(archive, "plot_summaries.txt"):
            if len(row) < 2:
                raise ValueError("Unexpected CMU plot row")
            plots[row[0]] = "\t".join(row[1:])
        readme_handle = archive.extractfile("MovieSummaries/README.txt")
        if readme_handle:
            save_text(directory / "external/cmu/README.txt", readme_handle.read().decode("utf-8"))

    matches = []
    used_plots = {}
    for role in roles.values():
        if role["is_nolan_film"]:
            continue
        candidates = []
        if role["year"]:
            year = int(role["year"])
            for wiki_id in by_title[normalized(role["film_title"])]:
                movie = movies[wiki_id]
                if wiki_id not in plots or not movie["release_date"]:
                    continue
                difference = abs(int(movie["release_date"][:4]) - year)
                actor_characters = [
                    character for character in characters[wiki_id]
                    if normalized(character["actor_name"]) == normalized(role["actor_name"])
                ]
                if difference <= 1 and actor_characters:
                    candidates.append((difference, wiki_id, actor_characters))
        if candidates:
            best_difference = min(candidate[0] for candidate in candidates)
            candidates = [candidate for candidate in candidates if candidate[0] == best_difference]
        if len(candidates) != 1:
            role["cmu_match_status"] = "ambiguous_film_match" if candidates else "no_film_actor_match"
            continue
        difference, wiki_id, actor_characters = candidates[0]
        role["cmu_match_status"] = "title_actor_year_match" if difference == 0 else "adjacent_year_needs_review"
        role["cmu_character_names"] = sorted({character["character_name"] for character in actor_characters if character["character_name"]})
        role["cmu_wikipedia_id"] = wiki_id
        roster = [
            ((character["actor_name"], character["character_name"]), [character["character_name"]])
            for character in characters[wiki_id] if character["character_name"]
        ]
        aliases = set()
        for character in actor_characters:
            identity = (character["actor_name"], character["character_name"])
            aliases.update(unique_aliases([character["character_name"]], roster, identity))
        role["cmu_aliases"] = sorted(aliases)
        plot = plots[wiki_id]
        source_url = f"https://en.wikipedia.org/?curid={wiki_id}"
        for passage in extract_passages(plot, role["cmu_aliases"]):
            role["evidence"].append({
                **passage, "kind": "plot_passage", "source_url": source_url,
                "source_dataset": "CMU Movie Summary Corpus",
                "source_snapshot": "2012-11-02",
                "plot_sha256": hashlib.sha256(plot.encode()).hexdigest(),
                "matching_method": role["cmu_match_status"],
                "review_status": "needs_human_review",
            })
        used_plots[wiki_id] = {**movies[wiki_id], "source_url": source_url, "text": plot}
        matches.append({
            "role_id": role["role_id"], "actor_name": role["actor_name"],
            "tmdb_film_id": role["film_id"], "tmdb_title": role["film_title"],
            "tmdb_year": role["year"], "cmu_wikipedia_id": wiki_id,
            "cmu_title": movies[wiki_id]["title"], "cmu_release_date": movies[wiki_id]["release_date"],
            "cmu_character_names": " | ".join(role["cmu_character_names"]),
            "match_status": role["cmu_match_status"],
        })
    return matches, sorted(used_plots.values(), key=lambda row: int(row["wikipedia_id"]))


def collect_saved_fandom_descriptions(directory, roles):
    source_path = directory / "fandom_character_pages.jsonl"
    if not source_path.exists():
        return
    by_id = {role["role_id"]: role for role in roles.values()}
    for line in source_path.read_text().splitlines():
        article = json.loads(line)
        if article["media_scope"] != "single_film":
            continue
        for role_id in article["matched_role_ids"]:
            if role_id not in by_id:
                raise ValueError(f"Fandom article links to an unknown role {role_id}")
            for paragraph in article["paragraphs"]:
                by_id[role_id]["evidence"].append({
                    "kind": "fandom_description", "text": paragraph["text"],
                    "section_path": paragraph["section_path"],
                    "paragraph_index": paragraph["paragraph_index"],
                    "source_url": article["source_url"], "source_wiki": article["wiki"],
                    "page_id": article["page_id"], "revision_id": article["revision_id"],
                    "source_sha256": article["source_sha256"], "media_scope": article["media_scope"],
                    "matching_method": "fandom_portrayal_actor_and_curated_film_context",
                    "review_status": "needs_human_review",
                })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/nolan")
    parser.add_argument("--corpus", type=Path)
    args = parser.parse_args()
    archive_path = args.corpus or args.data / "external/cmu/MovieSummaries.tar.gz"
    if not archive_path.exists():
        parser.error(f"Download {CORPUS_URL} to {archive_path} first")
    roles, _ = load_roles(args.data)
    collect_nolan_descriptions(args.data, roles)
    matches, historical_plots = collect_cmu_descriptions(args.data, roles, archive_path)
    collect_saved_fandom_descriptions(args.data, roles)
    records = sorted(roles.values(), key=lambda role: (int(role["actor_id"]), int(role["film_id"])))
    coverage = []
    for role in records:
        role["description_text"] = "\n".join(dict.fromkeys(item["text"] for item in role["evidence"]))
        role["review_status"] = "needs_human_review" if role["evidence"] else "missing_character_text"
        coverage.append({
            "role_id": role["role_id"], "actor_id": role["actor_id"], "actor_name": role["actor_name"],
            "film_id": role["film_id"], "film_title": role["film_title"], "year": role["year"],
            "is_nolan_film": role["is_nolan_film"],
            "character_names": " | ".join(role["tmdb_character_names"]),
            "cast_descriptions": sum(item["kind"] == "cast_description" for item in role["evidence"]),
            "plot_passages": sum(item["kind"] == "plot_passage" for item in role["evidence"]),
            "fandom_passages": sum(item["kind"] == "fandom_description" for item in role["evidence"]),
            "word_count": len(role["description_text"].split()), "status": role["review_status"],
            "cmu_match_status": role.get("cmu_match_status", "not_applicable"),
        })
    for name, rows in (("character_descriptions", records), ("historical_plot_sources", historical_plots)):
        save_text(args.data / f"{name}.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    save_csv(args.data / "character_text_coverage.csv", list(coverage[0]), coverage)
    save_csv(args.data / "cmu_role_matches.csv", [
        "role_id", "actor_name", "tmdb_film_id", "tmdb_title", "tmdb_year", "cmu_wikipedia_id",
        "cmu_title", "cmu_release_date", "cmu_character_names", "match_status",
    ], matches)
    save_json(args.data / "character_text_sources.json", {
        "cmu_archive_url": CORPUS_URL, "cmu_archive_path": os.path.relpath(archive_path, args.data),
        "cmu_archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "cmu_snapshot": "2012-11-02", "paper": "https://aclanthology.org/P13-1035/",
        "wikipedia_sources": "sources.json", "wikipedia_plots": "nolan_plots.jsonl",
        "fandom_sources": "fandom_sources.json" if (args.data / "fandom_sources.json").exists() else None,
    })
    summary = {
        "roles_in_scope": len(records), "nolan_roles": sum(role["is_nolan_film"] for role in records),
        "nolan_roles_with_text": sum(role["is_nolan_film"] and bool(role["evidence"]) for role in records),
        "historical_roles_with_text": sum(not role["is_nolan_film"] and bool(role["evidence"]) for role in records),
        "roles_with_cast_descriptions": sum(any(item["kind"] == "cast_description" for item in role["evidence"]) for role in records),
        "roles_with_fandom_text": sum(any(item["kind"] == "fandom_description" for item in role["evidence"]) for role in records),
        "historical_film_actor_matches": len(matches), "historical_plot_sources": len(historical_plots),
        "missing_character_text": sum(not role["evidence"] for role in records),
        "cmu_match_statuses": dict(Counter(role.get("cmu_match_status", "not_applicable") for role in records)),
        "limitations": [
            "All descriptions are source excerpts and require human validation of identity and role content.",
            "The CMU source snapshot is from 2012. Its coverage does not cover the full historical-film scope.",
            "Historical film matches require normalized title and actor name, plus release years differing by at most one.",
            "Adjacent-year matches and differing character names need identity review.",
            "Short aliases are used only when unique within the source character roster; that roster can be incomplete.",
            "Generic unnamed roles can lack character-specific evidence.",
            "Pronouns and unlisted aliases can leave valid passages uncollected.",
            "Feature-film and release-order eligibility still require the checks recorded in collection_summary.json.",
            "Source and snapshot differences require sensitivity checks when comparing role similarities.",
            "Fandom paragraphs are kept as a distinct evidence type. Articles spanning films or adaptations require film-scope review before integration.",
        ],
    }
    save_json(args.data / "character_text_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
