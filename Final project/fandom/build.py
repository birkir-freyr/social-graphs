"""Rebuild the Fandom-only corpus from the reviewed page revisions and paragraph indices."""
import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from collect import DATA, ROOT, WORK, PublicPages, article, key, read_csv
from collect_nolan import save_csv
from collect_passages import blind, mask, name_keys

HERE = Path(__file__).resolve().parent
CREDIT = re.compile(r"\b(?:portray(?:ed|al)|voiced|played by|play by|portayed by|actors?|actress(?:es)?|also portrays?|performance by|cast as|also plays|also voices|also known for|directed by|screenplay|novelization|deleted scene|real.life counterpart|in (?:the )?original script)\b", re.I)
BOILERPLATE = re.compile(r"\b(?:protagonist|antagonist|character|villain|hero|deuteragonist|tritagonist)\b.*?\b(?:film|movie|thriller|drama|comedy|franchise|series|novel|adaptation|remake)\b", re.I)


@lru_cache(maxsize=1)
def cast_parentheses():
    names = {r["actor"] for r in read_csv(ROOT / "passages.csv")}
    return re.compile(r"\s*\(\s*(?:" + "|".join(re.escape(n) for n in sorted(names)) + r")\s*\)")


def clean(text):
    text = cast_parentheses().sub("", text)
    if "{{{" in text or re.search(r"(?m)^\s*(?:Information|Name:|Gender:|Full name:)\s*$", text):
        return ""
    if re.match(r'^\s*[“"]', text) and re.search(r'["”]\s*(?:$|[-–—~])', text):
        return ""
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    text = re.sub(r"\s+([,.;:!?%)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    text = re.sub(r"(\w)\s+(['’]s)\b", r"\1\2", text)
    # Keep periods in personal initials, abbreviations and decimal numbers intact.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“‘'])", text)
    sentences = []
    for part in parts:
        if sentences and re.search(r"(?:\b[A-Z]|\bMr|\bMrs|\bDr|\bJr|\bSr|\bProf)\.$", sentences[-1]):
            sentences[-1] += " " + part
        else:
            sentences.append(part)
    kept = []
    for s in sentences:
        if CREDIT.search(s):
            # Other credits often continue across punctuation in an actor's filmography.
            break
        if not BOILERPLATE.search(s):
            kept.append(s.strip())
    return " ".join(kept)


def indices(spec):
    result = []
    for item in spec.split(","):
        a, _, b = item.partition("-")
        result.extend(range(int(a), int(b or a) + 1))
    if len(set(result)) != len(result):
        raise ValueError(f"Overlapping source paragraphs: {spec}")
    return result


def selection(page, spec):
    return " ".join(t for i in indices(spec) if (t := clean(page["paragraphs"][i]["text"])))


def build(refresh=False, offline=False):
    reviews = read_csv(HERE / "sources.csv")
    cached = {}
    if (WORK / "pages.json").exists() and not refresh:
        cached = {(p["wiki"], str(p["rev"])): p for p in json.loads((WORK / "pages.json").read_text())}
    pages = PublicPages(DATA, offline, 0.4)
    unique = {(r["wiki"], r["revision"]) for r in reviews}

    def fetch(k):
        wiki, rev = k
        return k, article(pages, wiki, oldid=rev)
    with ThreadPoolExecutor(4) as pool:
        cached.update(pool.map(fetch, sorted(unique - cached.keys())))

    roster = read_csv(ROOT / "passages.csv")
    primary = [r for r in reviews if r["usage"] == "primary"]
    alternative = [r for r in reviews if r["usage"] == "general_wiki_alternative"]
    for sources, name in ((primary, "passages.csv"), (alternative, "general_wiki_alternatives.csv")):
        mapping = {key(r): r for r in sources}
        if len(mapping) != len(sources) or not set(mapping) <= {key(r) for r in roster}:
            raise ValueError(f"{name} must map to unique credits on the original roster")
        chosen = roster if sources is primary else [r for r in roster if key(r) in mapping]
        write_passages(chosen, mapping, cached, name)


def write_passages(roster, mapping, cached, name):
    out = []
    attributed = set()
    for r in roster:
        row = {k: r[k] for k in ("actor", "character", "film", "year", "is_nolan", "billing", "wiki_page")}
        row.update(status="no_verified_description", role_text="", role_text_masked="", role_text_blind="",
                   n_words=0, source_url="", revision_url="", source_sections="", selection="")
        if key(r) in mapping:
            s = mapping[key(r)]
            p = cached[s["wiki"], s["revision"]]
            if p["title"] != s["title"] or str(p["rev"]) != s["revision"]:
                raise ValueError(f"Page identity differs from reviewed revision: {key(r)}")
            selected = indices(s["paragraphs"])
            source_indices = {(s["wiki"], s["revision"], i) for i in selected}
            if attributed & source_indices:
                raise ValueError(f"Source paragraphs reused across roles: {key(r)}")
            attributed.update(source_indices)
            raw = selection(p, s["paragraphs"])
            if hashlib.sha256(raw.encode()).hexdigest() != s["sha256"]:
                raise ValueError(f"Extract differs from reviewed revision: {key(r)}")
            url = f'https://{s["wiki"]}.fandom.com/wiki/' + quote(s["title"].replace(" ", "_"), safe="()")
            keys = name_keys(r["character"])
            raw_masked = blind(raw, keys, r["film"])
            row.update(status="usable" if len(raw_masked.split()) >= 25 else "below_25_words",
                       role_text=raw, role_text_masked=mask(raw, keys, r["film"]), role_text_blind=raw_masked,
                       n_words=len(raw.split()), source_url=url, revision_url=url + "?oldid=" + s["revision"],
                       source_sections=" | ".join(dict.fromkeys(" > ".join(p["paragraphs"][i]["section_path"]) for i in selected)),
                       selection=s["selection"])
        out.append(row)
    save_csv(HERE / name, list(out[0]), out)
    print(f'{sum(r["status"] == "usable" for r in out)} usable Fandom passages among {len(out)} roles')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="read pinned revision responses instead of discovery snapshots")
    parser.add_argument("--offline", action="store_true", help="require locally cached API responses")
    args = parser.parse_args()
    build(args.refresh, args.offline)
