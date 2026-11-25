"""Reproduce the expanded corpus from the original CSV and reviewed Fandom revisions."""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build import indices, write_passages
from collect import DATA, PublicPages, article, key, read_csv
from collect_nolan import save_csv


def build(offline):
    roster = read_csv(HERE.parent / "passages.csv")
    additions = read_csv(HERE / "sources.csv")
    mapping = {key(r): r for r in additions}
    old = {key(r): r for r in roster}
    if len(mapping) != len(additions) or any(old[k]["status"] == "usable" for k in mapping):
        raise ValueError("Each addition must cover one previously unusable credit")
    reviewed = [r for r in read_csv(HERE.parent / "sources.csv")
                if r["usage"] == "primary" and key(r) not in mapping] + additions
    paragraphs = set()
    for r in reviewed:
        selected = {(r["wiki"], r["revision"], i) for i in indices(r["paragraphs"])}
        if paragraphs & selected:
            raise ValueError(f"Overlapping source paragraphs for {key(r)}")
        paragraphs.update(selected)

    client = PublicPages(DATA, offline, 0.4)
    def fetch(k):
        wiki, rev = k
        return k, article(client, wiki, oldid=rev)

    with ThreadPoolExecutor(4) as pool:
        pages = dict(pool.map(fetch, sorted({(r["wiki"], r["revision"]) for r in additions})))
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "additional.csv"
        write_passages([old[k] for k in mapping], mapping, pages, path)
        new = {key(r): r for r in read_csv(path)}
    if any(r["status"] != "usable" for r in new.values()):
        raise ValueError("New passages must pass the original word threshold")
    save_csv(HERE / "passages.csv", list(roster[0]), [new.get(key(r), r) for r in roster])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use cached pinned responses")
    build(parser.parse_args().offline)
