"""Collect Fandom character articles through the public MediaWiki API.

Discovers Nolan character pages from relevant film categories and reads a small,
editable seed list for historical roles. Multi-film or adaptation-mixed articles
remain separate review candidates instead of entering a single-film profile.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup

from collect_character_text import name_variants, normalized, read_csv
from collect_nolan import ROOT, PublicPages, save_csv, save_json, save_text


COMMUNITIES = {
    "inception": {"films": ["Inception"], "categories": ["Characters"], "scope": "single_film"},
    "interstellarfilm": {"films": ["Interstellar"], "categories": ["Characters"], "scope": "single_film"},
    "batman": {
        "films": ["Batman Begins", "The Dark Knight", "The Dark Knight Rises"],
        "categories": ["Batman Begins Characters", "The Dark Knight Characters", "The Dark Knight Rises Characters"],
        "scope": "multiple_films_and_tie_ins",
    },
}
EXCLUDED_SECTIONS = {
    "contents", "quotes", "trivia", "references", "external links", "navigation",
    "gallery", "behind the scenes", "appearances", "portrayals", "casting",
    "2008 script", "original script", "development", "film production",
}


def api_url(wiki, **parameters):
    return f"https://{wiki}.fandom.com/api.php?" + urlencode({"format": "json", **parameters})


def api_get(pages, wiki, **parameters):
    result, source = pages.get(api_url(wiki, **parameters), content_format="json")
    if "error" in result:
        raise ValueError(f"{wiki}: {result['error'].get('code')}: {result['error'].get('info')}")
    return result, source


def character_paragraphs(soup):
    body = soup.select_one(".mw-parser-output") or soup
    for extra in body.select("table, aside, .portable-infobox, .toc, .navbox, .gallery, figure, blockquote, sup.reference, .mw-editsection"):
        extra.decompose()
    sections = {}
    paragraphs = []
    for node in body.find_all(["h2", "h3", "h4", "p"]):
        if node.name != "p":
            level = int(node.name[1])
            sections = {depth: title for depth, title in sections.items() if depth < level}
            sections[level] = node.get_text(" ", strip=True).replace("[ ]", "").strip()
            continue
        path = [sections[depth] for depth in sorted(sections)]
        if any(normalized(section) in EXCLUDED_SECTIONS for section in path):
            continue
        text = node.get_text(" ", strip=True)
        if len(text.split()) < 8:
            continue
        paragraphs.append({
            "paragraph_index": len(paragraphs), "section_path": path or ["Introduction"],
            "text": text,
        })
    return paragraphs


def portrayal_text(soup):
    values = []
    for item in soup.select(".pi-data"):
        label = item.select_one(".pi-data-label")
        value = item.select_one(".pi-data-value")
        if label and value and any(word in normalized(label.get_text()) for word in ("actor", "portray", "played by", "voiced by")):
            values.append(value.get_text(" ", strip=True))
    for row in soup.select("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) >= 2 and any(word in normalized(cells[0].get_text()) for word in ("actor", "portray", "played by", "voiced by")):
            values.append(" ".join(cell.get_text(" ", strip=True) for cell in cells[1:]))
    for paragraph in soup.select("p, li"):
        text = paragraph.get_text(" ", strip=True)
        for match in re.finditer(
            r"\b(?:portrayed|played|voiced)\s+by\s+([^.;!?]+)", text, re.IGNORECASE
        ):
            values.append(re.split(r",?\s+who\b", match.group(1), maxsplit=1)[0])
    return values


def actor_is_portrayed(actor_name, values):
    actor = normalized(actor_name)
    for value in values:
        text = normalized(value)
        if re.search(r"(?<!\w)" + re.escape(actor) + r"(?!\w)", text):
            return True
    return False


def discover(pages, seeds):
    candidates = {}
    source_records = []
    for wiki, community in COMMUNITIES.items():
        for category in community["categories"]:
            continuation = {}
            while True:
                result, source = api_get(
                    pages, wiki, action="query", list="categorymembers",
                    cmtitle=f"Category:{category}", cmlimit=500, **continuation,
                )
                source_records.append(source)
                for member in result["query"]["categorymembers"]:
                    if member["ns"] == 0:
                        candidates[(wiki, member["title"])] = {
                            "wiki": wiki, "page": member["title"],
                            "films": community["films"], "media_scope": community["scope"],
                            "actor_name": "", "discovery": f"Category:{category}",
                        }
                continuation = result.get("continue")
                if not continuation:
                    break
    for seed in read_csv(seeds):
        candidates[(seed["wiki"], seed["page"])] = {
            **seed, "films": [seed["film_title"]], "discovery": "fandom_seed_pages.csv",
        }
    return sorted(candidates.values(), key=lambda row: (row["wiki"], row["page"])), source_records


def collect_page(pages, candidate, roles):
    wiki = candidate["wiki"]
    result, source = api_get(
        pages, wiki, action="parse", page=candidate["page"], prop="text|revid|categories",
        redirects=1,
    )
    article = result["parse"]
    soup = BeautifulSoup(article["text"]["*"], "html.parser")
    portrayals = portrayal_text(soup)
    paragraphs = character_paragraphs(soup)
    permitted_films = {normalized(title) for title in candidate["films"]}
    page_names = {normalized(name) for name in name_variants([article["title"]])}
    matched_roles = []
    for role in roles:
        if normalized(role["film_title"]) not in permitted_films:
            continue
        if candidate["actor_name"] and normalized(role["actor_name"]) != normalized(candidate["actor_name"]):
            continue
        role_labels = (
            role["tmdb_character_names"]
            + role.get("wikipedia_character_labels", [])
            + role.get("cmu_character_names", [])
        )
        role_names = {normalized(name) for name in name_variants(role_labels)}
        if not page_names.intersection(role_names):
            continue
        if actor_is_portrayed(role["actor_name"], portrayals):
            matched_roles.append(role["role_id"])
    return {
        "wiki": wiki, "page_id": article["pageid"], "page_title": article["title"],
        "revision_id": article["revid"],
        "source_url": f"https://{wiki}.fandom.com/wiki/" + quote(article["title"].replace(" ", "_"), safe="()"),
        "api_url": source["url"], "source_sha256": source["sha256"],
        "raw_path": source["raw_path"], "retrieved_at": source["retrieved_at"],
        "media_scope": candidate["media_scope"], "film_context": candidate["films"],
        "portrayal_evidence": portrayals, "matched_role_ids": sorted(matched_roles),
        "review_status": "needs_human_review" if candidate["media_scope"] == "single_film" else "film_scope_review_required",
        "paragraphs": paragraphs,
        "word_count": sum(len(paragraph["text"].split()) for paragraph in paragraphs),
        "text_sha256": hashlib.sha256("\n".join(p["text"] for p in paragraphs).encode()).hexdigest(),
        "categories": [category["*"] for category in article.get("categories", [])],
        "matching_method": "curated_film_context_portrayal_actor_and_character_name",
    }, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/nolan")
    parser.add_argument("--seeds", type=Path, default=ROOT / "fandom_seed_pages.csv")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--interval", type=float, default=0.7)
    args = parser.parse_args()
    if args.workers < 1 or args.interval < 0:
        parser.error("workers must be positive and interval nonnegative")
    pages = PublicPages(args.data, args.offline, args.interval)
    roles = [json.loads(line) for line in (args.data / "character_descriptions.jsonl").read_text().splitlines()]
    candidates, sources = discover(pages, args.seeds)
    print(f"Discovered {len(candidates)} Fandom character-page candidates", flush=True)
    rights = {}
    for wiki in sorted({candidate["wiki"] for candidate in candidates}):
        result, source = api_get(pages, wiki, action="query", meta="siteinfo", siprop="rightsinfo|general")
        rights[wiki] = result["query"]
        sources.append(source)
    records, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(collect_page, pages, candidate, roles): candidate for candidate in candidates}
        for index, future in enumerate(as_completed(futures), 1):
            candidate = futures[future]
            try:
                record, source = future.result()
                records.append(record)
                sources.append(source)
            except Exception as error:
                errors.append({"wiki": candidate["wiki"], "page": candidate["page"], "error": str(error)})
            if index % 25 == 0 or index == len(futures):
                print(f"Fandom pages {index}/{len(futures)}; source errors {len(errors)}", flush=True)
    records.sort(key=lambda row: (row["wiki"], row["page_title"]))
    for record in records:
        record["license"] = rights[record["wiki"]].get("rightsinfo", {})
    save_text(args.data / "fandom_character_pages.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    coverage = [{
        "wiki": row["wiki"], "page_title": row["page_title"], "page_id": row["page_id"],
        "revision_id": row["revision_id"], "source_url": row["source_url"],
        "media_scope": row["media_scope"], "word_count": row["word_count"],
        "matched_role_ids": "|".join(row["matched_role_ids"]), "review_status": row["review_status"],
    } for row in records]
    save_csv(args.data / "fandom_coverage.csv", [
        "wiki", "page_title", "page_id", "revision_id", "source_url", "media_scope", "word_count", "matched_role_ids", "review_status",
    ], coverage)
    save_json(args.data / "fandom_sources.json", {"api_sources": sorted(sources, key=lambda row: row["url"]), "wiki_rights": rights})
    summary = {
        "candidate_pages": len(candidates), "collected_pages": len(records),
        "pages_with_text": sum(bool(row["paragraphs"]) for row in records),
        "pages_matched_to_roles": sum(bool(row["matched_role_ids"]) for row in records),
        "matched_roles": len({role_id for row in records for role_id in row["matched_role_ids"]}),
        "single_film_roles_with_text": len({role_id for row in records if row["media_scope"] == "single_film" and row["paragraphs"] for role_id in row["matched_role_ids"]}),
        "pages_by_wiki": dict(Counter(row["wiki"] for row in records)), "errors": errors,
        "scope_notes": [
            "Category discovery covers the Inception, Interstellar, and Dark Knight trilogy communities.",
            "Historical character pages come from the editable seed list; coverage remains incomplete.",
            "Role matching requires a character-name overlap, actor portrayal evidence, and the curated film context.",
            "Film scope and fan-written traits require human review before analysis.",
            "Trilogy, tie-in, and adaptation-mixed articles require section-level review before use in an individual film profile.",
        ],
    }
    save_json(args.data / "fandom_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
