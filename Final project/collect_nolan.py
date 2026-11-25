import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
TMDB = "https://www.themoviedb.org"
NOLAN = 525
FILMOGRAPHY = "https://en.wikipedia.org/wiki/Christopher_Nolan_filmography"
USER_AGENT = "SocialGraphsCourseProject" 


def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{threading.get_ident()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def save_json(path, value):
    save_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def save_csv(path, fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    save_text(path, buffer.getvalue())


def tmdb_url(kind, item_id, suffix=""):
    return f"{TMDB}/{kind}/{item_id}{suffix}?language=en-US"


class PublicPages:
    def __init__(self, directory, offline, interval):
        self.directory = directory
        self.offline = offline
        self.interval = interval
        self.lock = threading.Lock()
        self.last_request = 0.0

    def get(self, url, content_format="html"):
        if content_format not in ("html", "json"):
            raise ValueError("Supported source formats are html and json")
        key = hashlib.sha256(url.encode()).hexdigest()
        folder = self.directory / "raw" / key[:2]
        payload_path = folder / f"{key}.{content_format}.gz"
        metadata_path = folder / f"{key}.json"
        if payload_path.exists() and metadata_path.exists():
            payload = gzip.decompress(payload_path.read_bytes())
            metadata = json.loads(metadata_path.read_text())
            if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
                raise ValueError(f"Cached source hash does not match for {url}")
            parsed = json.loads(payload) if content_format == "json" else BeautifulSoup(payload, "html.parser")
            return parsed, metadata
        if self.offline:
            raise FileNotFoundError(f"No cached source for {url}")

        for attempt in range(4):
            with self.lock:
                time.sleep(max(0, self.last_request + self.interval - time.monotonic()))
                self.last_request = time.monotonic()
            try:
                response = requests.get(
                    url, headers={"User-Agent": USER_AGENT}, timeout=(15, 45)
                )
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
                continue
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < 3:
                    retry_after = response.headers.get("Retry-After", "")
                    delay = int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1)
                    time.sleep(min(delay, 120))
                    continue
            response.raise_for_status()
            break

        payload = response.content
        parsed = json.loads(payload) if content_format == "json" else BeautifulSoup(payload, "html.parser")
        if content_format == "html":
            if not parsed.title or "just a moment" in parsed.title.get_text().lower():
                raise ValueError(f"Unexpected page or access challenge for {url}")
        metadata = {
            "url": url,
            "final_url": response.url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "raw_path": str(payload_path.relative_to(self.directory)),
        }
        folder.mkdir(parents=True, exist_ok=True)
        temporary = payload_path.with_suffix(".tmp")
        temporary.write_bytes(gzip.compress(payload, mtime=0))
        temporary.replace(payload_path)
        save_json(metadata_path, metadata)
        return parsed, metadata


def structured_object(soup, schema_type):
    for script in soup.select('script[type="application/ld+json"]'):
        value = json.loads(script.get_text())
        objects = value if isinstance(value, list) else [value]
        for item in objects:
            if item.get("@type") == schema_type:
                return item
    raise ValueError(f"Missing {schema_type} structured metadata")


def movie_rows(soup, department):
    table = soup.select_one(f'table.credits[data-department="{department}"]')
    if table is None:
        if department == "Acting" and soup.select_one("div.credits_list"):
            return []
        raise ValueError(f"Missing {department} credit table")
    result = []
    for row in table.select("table.credit_group > tr"):
        link = row.select_one('td.role > a[href^="/movie/"]')
        if link is None:
            continue
        movie_id = int(re.match(r"/movie/(\d+)", link["href"]).group(1))
        year_text = row.select_one("td.year").get_text(strip=True)
        year = int(year_text) if re.fullmatch(r"\d{4}", year_text) else None
        character = row.select_one("span.character")
        result.append({
            "film_id": movie_id,
            "title": link.get_text(" ", strip=True),
            "year": year,
            "character": character.get_text(" ", strip=True) if character else "",
            "credit_id": row.select_one("td.seperator > span").get("data-id", ""),
        })
    return result


def feature_inventory(pages):
    wiki, wiki_source = pages.get(FILMOGRAPHY)
    feature_table = wiki.select_one("table.wikitable")
    if feature_table is None:
        raise ValueError("Missing feature filmography table")
    features = []
    for row in feature_table.select("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) < 3 or cells[2].get_text(strip=True) != "Yes":
            continue
        title_link = cells[1].find("a", href=True)
        features.append({
            "title": title_link.get_text(" ", strip=True),
            "wikipedia_year": int(cells[0].get_text(strip=True)),
            "wikipedia_url": urljoin(FILMOGRAPHY, title_link["href"]),
        })
    director, director_source = pages.get(tmdb_url("person", NOLAN))
    directing = movie_rows(director, "Directing")
    by_title = {row["title"].casefold(): row for row in directing}
    for film in features:
        match = by_title.get(film["title"].casefold())
        if match is None:
            raise ValueError(f"No TMDB directing match for {film['title']}")
        film["film_id"] = match["film_id"]
    if not features:
        raise ValueError("Filmography yielded no directed features")
    save_json(pages.directory / "inventory_sources.json", {
        "feature_inventory_source": wiki_source,
        "director_credits_source": director_source,
        "all_tmdb_directing_movie_rows": directing,
        "matched_feature_films": features,
    })
    return features


def collect_film(pages, feature, as_of):
    film_id = feature["film_id"]
    soup, source = pages.get(tmdb_url("movie", film_id))
    movie = structured_object(soup, "Movie")
    release_date = movie.get("datePublished", "")
    status_node = soup.select_one("section.facts")
    status = ""
    if status_node:
        for paragraph in status_node.select("p"):
            label = paragraph.find("strong")
            if label and label.get_text(strip=True) == "Status":
                status = paragraph.get_text(" ", strip=True).removeprefix("Status").strip()
    released = bool(release_date and release_date <= as_of and status == "Released")
    film = {
        **feature,
        "release_date": release_date,
        "release_date_precision": "day" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", release_date) else "unknown",
        "year": int(release_date[:4]) if release_date else feature["wikipedia_year"],
        "genres": "|".join(movie.get("genre", [])),
        "runtime": movie.get("duration", ""),
        "status": status,
        "included": released,
        "overview": movie.get("description", ""),
        "external_ids": movie.get("sameAs", []),
        "source_url": source["url"],
        "source_sha256": source["sha256"],
        "year_conflict": bool(release_date and int(release_date[:4]) != feature["wikipedia_year"]),
    }
    if not released:
        return film, []
    cast_page, cast_source = pages.get(tmdb_url("movie", film_id, "/cast"))
    section = cast_page.select_one("section#cast")
    if section is None:
        raise ValueError(f"Missing cast section for {film['title']}")
    reported = section.select_one("h3 span")
    if reported is None:
        raise ValueError(f"Missing cast count for {film['title']}")
    credits = []
    for item in section.select("ol.people > li"):
        link = item.select_one('div.info p > a[href^="/person/"]')
        character_node = item.select_one("p.character")
        if link is None or character_node is None:
            raise ValueError(f"Unrecognized cast row for {film['title']}")
        actor_id = int(re.match(r"/person/(\d+)", link["href"]).group(1))
        character = character_node.get_text(" ", strip=True)
        credits.append({
            "film_id": film_id, "actor_id": actor_id,
            "actor_name": link.get_text(" ", strip=True), "character": character,
            "cast_order": int(item["data-order"]), "credit_id": item["data-credit-id"],
            "uncredited": "uncredited" in character.lower(),
            "archive_footage": "archive" in character.lower(),
            "voice": "(voice)" in character.lower(),
            "source_url": cast_source["url"],
        })
    if len(credits) != int(reported.get_text(strip=True)):
        raise ValueError(f"Cast count mismatch for {film['title']}")
    film["cast_count"] = len(credits)
    return film, credits


def collect_actor(pages, actor):
    soup, source = pages.get(tmdb_url("person", actor["actor_id"]))
    person = structured_object(soup, "Person")
    if int(re.search(r"/person/(\d+)", person["url"]).group(1)) != actor["actor_id"]:
        raise ValueError("Actor ID redirected to a different person")
    return [{
        **row, "actor_id": actor["actor_id"], "actor_name": actor["actor_name"],
        "source_url": source["url"], "source_sha256": source["sha256"],
        "format_status": "movie_type_unverified",
    } for row in movie_rows(soup, "Acting")]


def history_links(films, credits, histories):
    films_by_id = {film["film_id"]: film for film in films if film["included"]}
    by_actor = {}
    for role in histories:
        by_actor.setdefault(role["actor_id"], []).append(role)
    rows = []
    for target in credits:
        film = films_by_id[target["film_id"]]
        cutoff_year = min(film["year"], film["wikipedia_year"])
        for prior in by_actor.get(target["actor_id"], []):
            if prior["film_id"] == target["film_id"]:
                continue
            year = prior["year"]
            if year and year > cutoff_year:
                continue
            order = "missing_year" if year is None else "same_year_needs_date"
            if year is not None and year < cutoff_year:
                order = "earlier_year"
            rows.append({
                "actor_id": target["actor_id"], "target_film_id": target["film_id"],
                "prior_film_id": prior["film_id"], "prior_year": year,
                "prior_character": prior["character"], "release_order_status": order,
                "prior_nolan_film": prior["film_id"] in films_by_id,
                "format_status": prior["format_status"],
            })
    return rows


def plot_record(pages, film):
    soup, source = pages.get(film["wikipedia_url"])
    heading = soup.find(id="Plot") or soup.find(id="Synopsis")
    if heading is None:
        raise ValueError(f"No Plot or Synopsis section for {film['title']}")
    start = heading.parent if "mw-heading" in heading.parent.get("class", []) else heading
    paragraphs = []
    for node in start.next_siblings:
        if not getattr(node, "name", None):
            continue
        if node.name == "h2" or "mw-heading2" in node.get("class", []):
            break
        candidates = [node] if node.name == "p" else node.find_all("p")
        for paragraph in candidates:
            if paragraph.find_parent(class_="hatnote"):
                continue
            for reference in paragraph.select("sup.reference, .mw-editsection"):
                reference.decompose()
            text = paragraph.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)
    if not paragraphs:
        raise ValueError(f"Empty plot for {film['title']}")
    revision = re.search(r'"wgRevisionId"\s*:\s*(\d+)', str(soup))
    return {
        "film_id": film["film_id"], "title": film["title"],
        "source_url": source["url"], "source_sha256": source["sha256"],
        "revision_id": revision.group(1) if revision else None,
        "license": "CC BY-SA 4.0; Wikipedia contributors",
        "paragraphs": paragraphs, "word_count": len(" ".join(paragraphs).split()),
    }


def character_passages(plots, credits):
    by_film = {plot["film_id"]: plot for plot in plots}
    rows = []
    for credit in credits:
        plot = by_film.get(credit["film_id"])
        if plot is None:
            continue
        character = re.sub(r"\([^)]*\)", "", credit["character"]).strip()
        aliases = [name.strip() for name in character.split(" / ") if len(name.strip()) >= 3]
        matches = []
        for index, text in enumerate(plot["paragraphs"]):
            found = [alias for alias in aliases if re.search(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, flags=re.IGNORECASE
            )]
            if found:
                matches.append({"paragraph_index": index, "matched_aliases": found, "text": text})
        rows.append({
            "actor_id": credit["actor_id"], "film_id": credit["film_id"],
            "character": credit["character"], "aliases": aliases,
            "extraction_method": "literal_cast_name_in_plot_paragraph",
            "review_status": "needs_human_review", "matches": matches,
            "source_url": plot["source_url"], "source_sha256": plot["source_sha256"],
        })
    return rows


def write_dataset(directory, as_of, films, credits, histories, plots, errors, completed_actors):
    actors = {}
    for credit in credits:
        actors.setdefault(credit["actor_id"], {
            "actor_id": credit["actor_id"], "actor_name": credit["actor_name"],
            "nolan_film_count": 0, "filmography_collected": credit["actor_id"] in completed_actors,
        })["nolan_film_count"] += 1
    save_csv(directory / "actors.csv", ["actor_id", "actor_name", "nolan_film_count", "filmography_collected"], sorted(actors.values(), key=lambda row: row["actor_id"]))
    save_csv(directory / "nolan_films.csv", [
        "film_id", "title", "wikipedia_year", "year", "release_date", "release_date_precision",
        "year_conflict", "status", "included", "genres", "runtime", "cast_count", "wikipedia_url",
        "source_url",
    ], films)
    save_csv(directory / "nolan_cast.csv", [
        "film_id", "actor_id", "actor_name", "character", "cast_order", "credit_id", "uncredited",
        "archive_footage", "voice", "source_url",
    ], credits)
    histories = sorted(histories, key=lambda row: (row["actor_id"], row["film_id"], row["credit_id"]))
    save_csv(directory / "actor_movie_credits.csv", ["actor_id", "actor_name", "film_id", "title", "year", "character", "credit_id", "format_status", "source_url", "source_sha256"], histories)
    links = history_links(films, credits, histories)
    save_csv(directory / "historical_links.csv", ["actor_id", "target_film_id", "prior_film_id", "prior_year", "prior_character", "release_order_status", "prior_nolan_film", "format_status"], links)
    save_json(directory / "nolan_film_metadata.json", films)
    for name, rows in (("nolan_plots", plots), ("nolan_character_passages", character_passages(plots, credits))):
        save_text(directory / f"{name}.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    sources = [json.loads(path.read_text()) for path in sorted((directory / "raw").glob("*/*.json"))]
    save_json(directory / "sources.json", sources)
    summary = {
        "as_of": as_of, "nolan_features": sum(film["included"] for film in films),
        "nolan_cast_credits": len(credits), "actors": len(actors),
        "actor_filmographies_collected": len(completed_actors),
        "actor_movie_credits": len(histories),
        "distinct_movies_in_actor_filmographies": len({row["film_id"] for row in histories}),
        "historical_candidate_links": len(links),
        "historical_links_with_earlier_year": sum(row["release_order_status"] == "earlier_year" for row in links),
        "historical_links_needing_dates": sum(row["release_order_status"] != "earlier_year" for row in links),
        "nolan_plots": len(plots),
        "nolan_cast_credits_with_literal_plot_matches": sum(bool(row["matches"]) for row in character_passages(plots, credits)),
        "cached_public_pages": len(sources), "errors": errors,
        "coverage_notes": [
            "Cast counts match the counts displayed by TMDB; credited and uncredited entries are retained and flagged.",
            "Actor histories include all movie-type rows exposed on the public Acting table, including shorts, TV movies, documentaries and archive appearances pending classification.",
            "Historical links are candidates. Same-year and missing-year rows require dates before use; feature-film format is unverified.",
            "Raw filmographies retain later credits for audit; historical links use per-target year cutoffs.",
            "Prior Nolan films are retained and flagged so the baseline can select other directors.",
            "Repeated characters are preserved in raw credits and require character resolution before analysis.",
            "Character passages use literal cast names, preserve full paragraphs, and need human review for aliases, pronouns and unrelated characters.",
            "Earlier-film plots and metadata enrichment are subsequent collection steps.",
        ],
    }
    save_json(directory / "collection_summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("casts", "histories", "plots", "all"), default="all")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "nolan")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--interval", type=float, default=0.7)
    args = parser.parse_args()
    date.fromisoformat(args.as_of)
    if args.workers < 1 or args.interval < 0:
        parser.error("workers must be positive and interval nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    pages = PublicPages(args.output, args.offline, args.interval)
    films, credits, histories, plots, errors = [], [], [], [], []
    completed_actors = set()
    history_file = args.output / "actor_movie_credits.csv"
    if history_file.exists():
        with history_file.open(newline="") as handle:
            for row in csv.DictReader(handle):
                for key in ("actor_id", "film_id", "year"):
                    row[key] = int(row[key]) if row[key] else None
                histories.append(row)
    plots_file = args.output / "nolan_plots.jsonl"
    if plots_file.exists():
        plots = [json.loads(line) for line in plots_file.read_text().splitlines()]
    for feature in feature_inventory(pages):
        film, cast = collect_film(pages, feature, args.as_of)
        films.append(film)
        credits.extend(cast)
        print(f"Cast {film['title']}: {len(cast)} entries", flush=True)
    actors = {row["actor_id"]: row for row in credits}
    histories_by_actor = {}
    for row in histories:
        histories_by_actor.setdefault(row["actor_id"], []).append(row)
    # Successful empty filmographies also count as collected. The cache is the
    # source of truth, including on a resumed run.
    for index, actor in enumerate(actors.values(), 1):
        try:
            cached = PublicPages(args.output, True, 0)
            histories_by_actor[actor["actor_id"]] = collect_actor(cached, actor)
            completed_actors.add(actor["actor_id"])
        except FileNotFoundError:
            pass
        if index % 100 == 0:
            print(f"Cached filmographies checked {index}/{len(actors)}", flush=True)
    histories = [row for rows in histories_by_actor.values() for row in rows]
    write_dataset(args.output, args.as_of, films, credits, histories, plots, errors, completed_actors)
    if args.stage in ("histories", "all"):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(collect_actor, pages, actor): actor
                for actor in actors.values()
                if actor["actor_id"] not in completed_actors
            }
            for index, future in enumerate(as_completed(futures), 1):
                actor = futures[future]
                try:
                    histories_by_actor[actor["actor_id"]] = future.result()
                    completed_actors.add(actor["actor_id"])
                except Exception as error:
                    errors.append({"stage": "histories", "actor_id": actor["actor_id"], "name": actor["actor_name"], "error": str(error)})
                    print(f"Filmography failed {actor['actor_name']}: {error}", flush=True)
                if index % 25 == 0 or index == len(futures):
                    histories = [row for rows in histories_by_actor.values() for row in rows]
                    write_dataset(args.output, args.as_of, films, credits, histories, plots, errors, completed_actors)
                    print(f"Filmographies {index}/{len(futures)}; movie credits {len(histories)}; errors {len(errors)}", flush=True)
    if args.stage in ("plots", "all"):
        plots = []
        for film in films:
            if not film["included"]:
                continue
            try:
                record = plot_record(pages, film)
                plots.append(record)
                print(f"Plot {film['title']}: {record['word_count']} words", flush=True)
            except Exception as error:
                errors.append({"stage": "plots", "film_id": film["film_id"], "error": str(error)})
    summary = write_dataset(args.output, args.as_of, films, credits, histories, plots, errors, completed_actors)
    print(json.dumps({key: value for key, value in summary.items() if key != "coverage_notes"}, indent=2), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
