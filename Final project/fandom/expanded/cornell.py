"""Index character dialogue for the paper's credits from the three original Cornell tables."""
import argparse
import csv
import hashlib
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLES = {
    "movie_titles_metadata": "da1c5f3fbf66caf50d6fa1b2d88d1e77389e84de4bb2a77793c6db79e17efb1a",
    "movie_characters_metadata": "332f1c58198ed1a6fef3c1b13bc54b46730a401a11ae979b7601e1f1564aaf23",
    "movie_lines": "59b9a78482829bc083d69cc9c164fc058eb4d0431712e09a4b08059663d0de56",
}
# Reviewed ambiguous speaker labels, dual roles, and exclusions for ambiguous attribution.
REVIEW = {
    ("Memento", "Leonard"): ["u6563", "u6564"],
    ("Memento", "Leonard's Wife"): ["u6565"],
    ("The Godfather", "Michael Corleone"): ["u3105"],
    ("The Godfather Part II", "Don Michael Corleone"): ["u5545"],
    ("The Insider", "Lowell Bergman"): ["u1499", "u1500"],
    ("The Man in the Iron Mask", "King Louis XIV / Philippe"): ["u6459", "u6462"],
    ("Basquiat", "Albert Milo"): ["u3887"],
    ("The Majestic", "Luke Trimble"): [],
    ("The Messenger", "Returning Soldier's Wife"): [],
    ("Get Carter", "Cliff Brumby"): [],
    ("Drop Dead Gorgeous", "Documentarian"): [],
}


def normalize(s):
    plain = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return " ".join(re.findall("[a-z0-9]+", plain))


def table(directory, name):
    raw = (directory / (name + ".txt")).read_bytes()
    if hashlib.sha256(raw).hexdigest() != TABLES[name]:
        raise ValueError(f"{name} differs from the reviewed Cornell release")
    for line in raw.split(b"\n"):
        if line.strip():
            yield line.rstrip(b"\r").decode("latin-1").split(" +++$+++ ")


def write(path, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main(directory, output_text):
    with (HERE / "passages.csv").open(newline="", encoding="utf-8") as file:
        roster = list(csv.DictReader(file))
    films = defaultdict(list)
    for mid, title, year, *_ in table(directory, "movie_titles_metadata"):
        films[normalize(title), year[:4]].append(mid)
    cast = defaultdict(dict)
    for cid, name, mid, *_ in table(directory, "movie_characters_metadata"):
        cast[mid][cid] = name
    utterances = defaultdict(list)
    for uid, cid, mid, _, line in table(directory, "movie_lines"):
        utterances[mid, cid].append((int(uid[1:]), line))

    occupied = set()
    index, text_rows = [], []
    for r in roster:
        movie_ids = films[normalize(r["film"]), r["year"]]
        if len(movie_ids) != 1:
            continue
        mid = movie_ids[0]
        credit_words = set(normalize(r["character"]).split())
        ids = REVIEW.get((r["film"], r["character"]))
        if ids is None:
            ids = [cid for cid, name in cast[mid].items() if normalize(name)
                   and set(normalize(name).split()) <= credit_words]
            if len(ids) != 1:
                continue
        if not ids:
            continue
        if occupied.intersection(ids):
            raise ValueError(f"Speaker ID already assigned for {r['film']}")
        occupied.update(ids)
        lines = sorted(line for cid in ids for line in utterances[mid, cid])
        record = {k: r[k] for k in ("actor", "film", "year", "character", "is_nolan")}
        record.update(movie_id=mid, speaker_ids="|".join(ids),
                      speaker_labels="|".join(" ".join(cast[mid][cid].split()) for cid in ids),
                      lines=len(lines), words=sum(len(t.split()) for _, t in lines),
                      has_fandom_description=int(r["status"] == "usable"))
        index.append(record)
        if output_text:
            text_rows.append(dict(record, dialogue="\n".join(t for _, t in lines)))
    write(HERE / "cornell_speakers.csv", index)
    if output_text:
        write(output_text, text_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory with the three Cornell .txt tables")
    parser.add_argument("--output-text", type=Path, help="also export joined script lines for local analysis")
    args = parser.parse_args()
    main(args.directory, args.output_text)
