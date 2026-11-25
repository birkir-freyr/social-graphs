"""Discover candidate Fandom articles for the paper's complete role roster."""
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collect_fandom import api_get, character_paragraphs, portrayal_text
from collect_nolan import PublicPages, save_json

DATA = ROOT / "data/nolan"
WORK = DATA / "raw/fandom-study"
ACTOR_ALIASES = {"Elliot Page": ["Ellen Page"], "Alon Aboutboul": ["Alon Abutbul"]}
GENERIC = set("the and young old adult voice uncredited self himself herself man woman agent officer detective general doctor dr mr mrs captain jr police guard soldier boy girl".split())


def norm(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key(row):
    return (row["actor"], row["film"], row["year"], row["character"])


def article(pages, wiki, **locator):
    parsed, source = api_get(pages, wiki, action="parse", prop="text|revid|categories", **locator)
    page = parsed["parse"]
    soup = BeautifulSoup(page["text"]["*"], "html.parser")
    cast = portrayal_text(soup)
    for tag in soup.select("script, style, .quote, .quotebox, .thumb, dl, .navbox, .notice, .messagebox"):
        tag.decompose()
    return dict(wiki=wiki, title=page["title"], rev=page["revid"], pageid=page["pageid"],
                categories=[s["*"] for s in page["categories"]], cast=cast,
                paragraphs=character_paragraphs(soup), fetched=source["retrieved_at"])


def discover():
    pages = PublicPages(DATA, False, 0.30)
    roles = read_csv(ROOT / "passages.csv")
    by_actor = defaultdict(list)
    aliases = defaultdict(list)
    archive = DATA / "character_descriptions.jsonl"
    if archive.exists():
        for line in archive.read_text().splitlines():
            r = json.loads(line)
            aliases[r["actor_name"], r["film_title"]].extend(
                r.get("cmu_character_names", []) + r.get("wikipedia_character_labels", []))
    for role in roles:
        names = [role["character"], *aliases[role["actor"], role["film"]]]
        role["tokens"] = set(norm(" ".join(names)).split()) - GENERIC
        by_actor[role["actor"]].append(role)

    def search(args):
        wiki, actor = args
        titles = {}
        for spelling in [actor, *ACTOR_ALIASES.get(actor, [])]:
            cursor = {}
            while True:
                data, _ = api_get(pages, wiki, action="query", list="search", srnamespace=0,
                                  srsearch=f'"{spelling}"', srlimit=500, srprop="", **cursor)
                for hit in data["query"]["search"]:
                    title = hit["title"]
                    if "/" in title and title.split("/")[-1].lower() in {"gallery", "quotes", "synopsis", "history"}:
                        continue
                    words = set(norm(title).split())
                    matched = [key(r) for r in by_actor[actor] if
                               (wiki != "chrisnolan" or r["is_nolan"] == "1") and
                               (words & r["tokens"] or norm(r["film"]) in norm(title))]
                    if matched:
                        titles[title] = matched
                cursor = data.get("continue")
                if not cursor:
                    break
        return wiki, titles

    candidates = defaultdict(set)
    with ThreadPoolExecutor(5) as pool:
        for wiki, hits in pool.map(search, [(w, a) for a in by_actor for w in ("hero", "villains", "chrisnolan")]):
            for title, matches in hits.items():
                candidates[wiki, title].update(matches)
    # Include the project's specialist wiki pages, including aliases missed by the general searches.
    source = DATA / "fandom_character_pages.jsonl"
    if source.exists() and archive.exists():
        credit = {r["role_id"]: (r["actor_name"], r["film_title"]) for r in
                  (json.loads(line) for line in archive.read_text().splitlines())}
        for line in source.read_text().splitlines():
            p = json.loads(line)
            for role_id in p["matched_role_ids"]:
                actor, film = credit[role_id]
                for r in by_actor[actor]:
                    if film == r["film"]:
                        candidates[p["wiki"], p["page_title"]].add(key(r))
    data, _ = api_get(pages, "ww2-movie-characters", action="query", list="categorymembers",
                      cmtitle="Category:Dunkirk (2017)", cmnamespace=0, cmlimit=500)
    for member in data["query"]["categorymembers"]:
        title = member["title"]
        for r in roles:
            if r["film"] == "Dunkirk" and set(norm(title).split()) & set(norm(r["character"]).split()):
                candidates["ww2-movie-characters", title].add(key(r))
    save_json(WORK / "candidates.json", [[w, t, sorted(rs)] for (w, t), rs in sorted(candidates.items())])
    print(f"{len(candidates)} candidate pages", flush=True)

    def fetch(args):
        (wiki, title), matches = args
        page = article(pages, wiki, page=title, redirects=1)
        page["matches"] = sorted(matches)
        return page

    with ThreadPoolExecutor(5) as pool:
        result = []
        for i, p in enumerate(pool.map(fetch, sorted(candidates.items())), 1):
            result.append(p)
            if i % 100 == 0:
                print(f"Read {i}/{len(candidates)}", flush=True)
    save_json(WORK / "pages.json", result)


if __name__ == "__main__":
    discover()
