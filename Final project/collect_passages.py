#!/usr/bin/env python3
"""
Character passages for the Nolan project — the NLP half's input.

Reads the CSVs already in Final project/data/nolan/ and adds the one thing
missing: character-specific text.

For every role it takes the film's Wikipedia Plot section and keeps only the
sentences that name that character. Then it masks character and film names,
because otherwise similarity is driven by names rather than by what the
character does — idea.md asks for this explicitly.

    # pilot first, as idea.md plans: three actors, inspect by hand
    python3 collect_passages.py --pilot "Michael Caine,Cillian Murphy,Tom Hardy"

    # then the real run
    python3 collect_passages.py --max-billing 10

Writes passages.csv:
    actor, character, film, year, is_nolan, billing,
    n_sentences, n_words, role_text, role_text_masked, wiki_page, status

status says WHY a role has no text, which matters: "fetch_failed" is a
network problem, not a film without a plot. Re-run to retry those — only
failures are refetched, everything else is cached.

Everything is cached in ./cache_wiki/, so re-runs are free and it is safe
to interrupt.
"""

import argparse, csv, hashlib, json, os, re, sys, threading, time
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

WIKI = "https://en.wikipedia.org/w/api.php"
UA = "DTU-02805-student-project (course 02805, contact via DTU)"
CACHE = "cache_wiki"
DATA = "."                      # overridden by --data
PAUSE = 0.15                    # between live requests; Wikipedia asks for politeness

os.makedirs(CACHE, exist_ok=True)

_stats = Counter()


# ----------------------------------------------------------------- fetch
def cached(url, tries=4):
    """Return parsed JSON, or None if the request FAILED.

    None means 'we do not know', not 'nothing there'. Callers must keep
    the two apart — conflating them is how a network blip turns into a
    finding. Failures are not written to the cache, so a later run
    retries exactly those.
    """
    k = hashlib.sha1(url.encode()).hexdigest()[:20]
    p = os.path.join(CACHE, k + ".json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                _stats["cache_hit"] += 1
                return json.load(f)
        except json.JSONDecodeError:
            os.remove(p)
    for i in range(tries):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                d = json.load(r)
            # write via a unique temp name, then rename: a half-written
            # cache file read by another thread would poison the run
            tmp = f"{p}.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f)
            os.replace(tmp, p)
            _stats["fetched"] += 1
            time.sleep(PAUSE)
            return d
        except HTTPError as e:
            if e.code == 429:                      # rate limited: back off hard
                _stats["rate_limited"] += 1
                time.sleep(5 * (i + 1))
                continue
            if 400 <= e.code < 500 and e.code != 429:
                _stats["http_4xx"] += 1
                return None                        # a real "not available"
            time.sleep(2 * (i + 1))
        except (URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 * (i + 1))
    _stats["failed"] += 1
    return None


# ------------------------------------------------------- finding the page
BAD_TITLE = re.compile(
    r"^(List of|Index of)|filmography|on stage and screen|awards and nominations",
    re.I)


def find_page(title, year):
    """Return (page_title, status).

    status: 'ok' | 'fetch_failed' | 'no_page'

    Picks among five search hits instead of blindly taking the first,
    because the first is sometimes an actor's filmography page or the
    wrong year's remake.
    """
    s = cached(f"{WIKI}?action=query&list=search&srsearch="
               f"{quote(f'{title} {year} film')}&format=json&srlimit=5")
    if s is None:
        return "", "fetch_failed"
    hits = (s.get("query", {}) or {}).get("search", [])
    if not hits:
        return "", "no_page"

    def score(h):
        t = h.get("title", "")
        sn = re.sub(r"<[^>]+>", "", h.get("snippet", "") or "")
        sc = 0
        if re.search(r"\(.*\bfilm\b.*\)", t, re.I):          sc += 3
        if year and year in t:                               sc += 3
        if year and re.search(rf"\b{re.escape(year)}\b", sn): sc += 2
        if re.search(r"\bfilm\b", sn, re.I):                 sc += 1
        if t.lower().startswith(title.lower()):              sc += 2
        if BAD_TITLE.search(t):                              sc -= 8
        return sc

    hits.sort(key=score, reverse=True)
    return hits[0].get("title", ""), "ok"


# --------------------------------------------------- reading the sections
def split_sections(extract):
    """[(level, heading, body)] from a plaintext Wikipedia extract."""
    parts = re.split(r"\n(=+) ([^=\n]+?) \1\n", "\n" + extract)
    out = [(0, "", parts[0])]
    for i in range(1, len(parts) - 2, 3):
        out.append((len(parts[i]), parts[i + 1].strip(), parts[i + 2]))
    return out


PLOTISH = re.compile(r"^(plot|synopsis|premise|story|storyline)", re.I)


def plot_from_extract(extract):
    """The Plot section PLUS its subsections.

    The old version stopped at the next heading of any depth, so a plot
    broken into '=== Act one ===' lost everything after the first
    subheading. Here we keep going while the heading is deeper.
    """
    secs = split_sections(extract)
    for i, (lv, head, body) in enumerate(secs):
        if lv and PLOTISH.match(head):
            buf = [body]
            for lv2, _, b2 in secs[i + 1:]:
                if lv2 <= lv:
                    break
                buf.append(b2)
            return "\n".join(buf).strip()
    return ""


def plot_section(title, year, page_hint=""):
    """Return (plot_text, page_title, status).

    status: 'ok' | 'fetch_failed' | 'no_page' | 'no_plot_section'
    """
    page, st = (page_hint, "ok") if page_hint else find_page(title, year)
    if st != "ok" or not page:
        return "", page, st

    d = cached(f"{WIKI}?action=query&prop=extracts&explaintext=1&format=json"
               f"&redirects=1&titles={quote(page)}")
    if d is None:
        return "", page, "fetch_failed"
    pages = (d.get("query", {}) or {}).get("pages", {}) or {}
    extract = next(iter(pages.values()), {}).get("extract", "") or ""
    if not extract:
        return "", page, "no_page"

    plot = plot_from_extract(extract)
    return (plot, page, "ok" if plot else "no_plot_section")


def prefetch(films, workers):
    """Resolve every unique film concurrently, so the main loop is all
    cache hits. One request at a time was costing ~5s each; the wait is
    network latency, not work, so running several at once is the whole
    speed-up. Results are keyed by (title, year) and returned."""
    out, done, lock = {}, [0], threading.Lock()

    def one(job):
        title, year, hint = job
        r = plot_section(title, year, hint)
        with lock:
            out[(title, year)] = r
            done[0] += 1
            if done[0] % 25 == 0 or done[0] == len(films):
                ok = sum(1 for v in out.values() if v[2] == "ok")
                print(f"  fetched {done[0]}/{len(films)} films, "
                      f"{ok} with a plot", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, films))
    return out


# --------------------------------------------------- names and sentences
DROP = {"the","a","an","dr","dr.","mr","mr.","mrs","mrs.","ms","ms.","miss",
        "sir","lord","lady","young","old","elder","agent","officer","captain",
        "detective","professor","prof.","uncle","aunt","father","mother",
        "himself","herself","narrator","voice","man","woman","boy","girl"}


def name_keys(character):
    c = re.sub(r"\(.*?\)", " ", character or "")
    keys = []
    for a in [x.strip() for x in c.split("/") if x.strip()]:
        if len(a) > 2:
            keys.append(a)
        for p in re.split(r"[\s,]+", a):
            p = p.strip(".,'\"")
            if len(p) > 2 and p[0].isupper() and p.lower() not in DROP:
                keys.append(p)
    keys = [k for k in keys if k.lower() not in DROP]
    keys.sort(key=len, reverse=True)
    seen, out = set(), []
    for k in keys:
        if k.lower() not in seen:
            seen.add(k.lower()); out.append(k)
    return out


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]


def mask(text, char_keys, film_title):
    """Replace the character's own name with CHARACTER and the film title
    with FILM. idea.md asks for this so similarity reflects the role, not
    the name."""
    out = text
    for k in sorted(char_keys, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(k)}\b", "CHARACTER", out)
    for w in [w for w in re.split(r"\W+", film_title or "") if len(w) > 3]:
        out = re.sub(rf"\b{re.escape(w)}\b", "FILM", out, flags=re.I)
    return out


# Capitalised words that are ordinary English starting a sentence, not names.
NOT_A_NAME = set("""The A An And But Or So Then Now Later Finally Eventually
Meanwhile However Although Though Despite After Before During While When As If
Because Since Until Unless Upon With Without By For From In On At To Into Over
Under Between Through Against About He She It They We You His Her Its Their Our
This That These Those There Here One Two Three Four Five Both All Each Some Many
Most Having Using Realizing Believing Learning Knowing Seeing Taking Leaving
Returning Arriving Unable Unbeknownst Instead Meanwhile Soon Once Years Months
Days Night Day Morning Later Next Last First Second Third Final Another Other
Only Still Even Just Although Yet Nevertheless Afterwards Afterward Back
Together Suddenly Shortly Eventually Later""".split())


def blind(text, char_keys, film_title):
    """Everything mask() does, plus every OTHER name in the passage.

    Without this, two roles in the same film share 'Gotham', 'Bruce',
    'Falcone' and so look alike for reasons that have nothing to do with
    the kind of role being played — and franchise actors get an inflated
    within-actor similarity, which is the very quantity we test. A name
    is taken to be any capitalised word that occurs somewhere other than
    the start of a sentence.
    """
    out = mask(text, char_keys, film_title)
    # tokens with their positions, so we can tell sentence-initial apart
    names = set()
    for mt in re.finditer(r"\b[A-Z][a-z]{2,}\b", out):
        w = mt.group(0)
        if w in NOT_A_NAME or w in ("CHARACTER", "FILM"):
            continue
        before = out[:mt.start()].rstrip()
        if before and not before.endswith((".", "!", "?")):
            names.add(w)          # seen mid-sentence -> a name
    for w in sorted(names, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(w)}\b", "NAME", out)
    return out


# ------------------------------------------------------------------ main
def rd(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        sys.exit(f"missing {p} — point --data at Final project/data/nolan")
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    global DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".")
    ap.add_argument("--out", default="passages.csv")
    ap.add_argument("--pilot", default="", help="comma-separated actor names")
    ap.add_argument("--max-billing", type=int, default=10)
    ap.add_argument("--min-prior", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6,
                    help="concurrent Wikipedia fetches (6 is polite and fast)")
    args = ap.parse_args()
    DATA = args.data

    films = {r["film_id"]: r for r in rd("nolan_films.csv")}
    cast = rd("nolan_cast.csv")
    prior = rd("roles_before_nolan_film.csv")

    # --- which actors are we doing? ---
    cast = [c for c in cast
            if c["uncredited"] == "False" and c["archive_footage"] == "False"]
    if args.pilot:
        want = {a.strip() for a in args.pilot.split(",") if a.strip()}
        cast = [c for c in cast if c["actor_name"] in want]
        missing = want - {c["actor_name"] for c in cast}
        if missing:
            print(f"not in nolan_cast.csv: {sorted(missing)}")
    else:
        cast = [c for c in cast
                if c["cast_order"].isdigit()
                and int(c["cast_order"]) < args.max_billing]

    actors = {c["actor_name"] for c in cast}
    prior_by = defaultdict(list)
    for r in prior:
        if r["actor"] in actors:
            prior_by[r["actor"]].append(r)
    actors = {a for a in actors if len(prior_by[a]) >= args.min_prior}
    cast = [c for c in cast if c["actor_name"] in actors]

    # roles_before_nolan_film.csv lists a Nolan film as a "prior role"
    # whenever the actor was in an EARLIER Nolan film. Those rows are
    # correct for the casting graph but must not be labelled non-Nolan
    # here: that would put an actor's other Nolan roles into the control
    # set and into the centroid defining their prior type, which is the
    # very thing being compared against.
    nolan_titles = {f.get("title", "") for f in films.values()
                    if f.get("title")}
    nolan_hint = {f.get("title", ""):
                  (f.get("wikipedia_url", "") or "").rsplit("/", 1)[-1].replace("_", " ")
                  for f in films.values()}

    jobs = {}           # (actor, film, character) -> job tuple, Nolan wins
    for c in cast:
        f = films.get(c["film_id"], {})
        t = f.get("title", "")
        jobs[(c["actor_name"], t, c["character"])] = (
            t, f.get("year", ""), nolan_hint.get(t, ""),
            c["actor_name"], c["character"], 1, c["cast_order"])
    for a in sorted(actors):
        for r in prior_by[a]:
            k = (a, r["film"], r["character"])
            if k in jobs:
                continue                      # already have it, as a Nolan role
            is_nolan = 1 if r["film"] in nolan_titles else 0
            jobs[k] = (r["film"], r["year"], nolan_hint.get(r["film"], ""),
                       a, r["character"], is_nolan, "")
    jobs = list(jobs.values())

    # one entry per unique film, keeping the page hint when we have one
    film_jobs = {}
    for title, year, hint, *_ in jobs:
        if (title, year) not in film_jobs or hint:
            film_jobs[(title, year)] = (title, year, hint)
    film_jobs = list(film_jobs.values())

    print(f"actors        {len(actors)}")
    print(f"roles         {len(jobs)}  ({sum(1 for j in jobs if j[5])} Nolan)")
    print(f"unique films  {len(film_jobs)}   "
          f"{args.workers} at a time (cached after)\n")

    t0 = time.time()
    plots = prefetch(film_jobs, args.workers)
    print(f"  fetching took {time.time()-t0:.0f}s\n")

    rows = []
    for n, (title, year, hint, actor, char, isn, billing) in enumerate(jobs, 1):
        plot, page, status = plots[(title, year)]
        sents = sentences(plot)
        keys = name_keys(char)
        hit = [s for s in sents
               if any(re.search(rf"\b{re.escape(k)}\b", s) for k in keys)]
        txt = " ".join(hit)
        rows.append({
            "actor": actor, "character": char, "film": title, "year": year,
            "is_nolan": isn, "billing": billing,
            "n_sentences": len(hit), "n_words": len(txt.split()),
            "role_text": txt,
            "role_text_masked": mask(txt, keys, title),
            "role_text_blind": blind(txt, keys, title),
            "wiki_page": page,
            "status": status if status != "ok" else
                      ("ok" if len(txt.split()) >= 25 else "not_named_enough"),
        })
        if n % 100 == 0:
            ok = sum(1 for r in rows if r["n_words"] >= 25)
            print(f"  {n}/{len(jobs)}   usable so far {ok} ({ok/n:.0%})")

    cols = ["actor", "character", "film", "year", "is_nolan", "billing",
            "n_sentences", "n_words", "role_text", "role_text_masked",
            "role_text_blind", "wiki_page", "status"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)

    usable = [r for r in rows if r["n_words"] >= 25]
    fstat = Counter(st for _, (_, _, st) in plots.items())
    byactor = Counter(r["actor"] for r in usable)
    ready = [a for a in actors
             if byactor[a] >= args.min_prior + 1
             and any(r["is_nolan"] and r["n_words"] >= 25
                     for r in usable if r["actor"] == a)]

    print("\n" + "=" * 58)
    print(f"roles written          {len(rows)}")
    print(f"  25+ words of text    {len(usable)}  "
          f"({len(usable)/max(len(rows),1):.0%})")
    print(f"films                  {len(plots)}")
    print(f"  plot found           {fstat['ok']}")
    print(f"  FETCH FAILED         {fstat['fetch_failed']}   <-- re-run to retry")
    print(f"  no page found        {fstat['no_page']}")
    print(f"  no plot section      {fstat['no_plot_section']}")
    print(f"actors ready to test   {len(ready)}   <-- THE NUMBER")
    print("=" * 58)
    print(f"requests: {_stats['fetched']} fetched, {_stats['cache_hit']} cached, "
          f"{_stats['rate_limited']} rate-limited, {_stats['failed']} gave up")
    print(f"\nwrote {args.out}")
    if fstat["fetch_failed"]:
        print(f"\n{fstat['fetch_failed']} films failed to fetch. That is a network")
        print("problem, NOT films without plots. Run the same command again —")
        print("successes are cached, so only the failures are retried.")
    print("\nREAD SOME PASSAGES BEFORE TRUSTING ANY SCORE. Sort by n_words,")
    print("open five rows, check the text is about that character and that")
    print("the masking did not eat something it should have kept.")


if __name__ == "__main__":
    main()
