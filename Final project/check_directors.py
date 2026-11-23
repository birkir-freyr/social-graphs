#!/usr/bin/env python3
"""Audit the director parse against the text it came from.

Two things can go wrong and they need separating:
  1. the regex grabs the wrong span of text  -> visible by reading
  2. Wikipedia itself is wrong               -> not checkable here

This prints a random sample with the sentence each name came from, so
(1) can be measured, and flags the systematic smells that a sample of
30 would miss.
"""
import argparse, csv, hashlib, json, os, random, re, sys
from collections import Counter, defaultdict
from urllib.parse import quote

import director_test as D

random.seed(2805)
WIKI = "https://en.wikipedia.org/w/api.php"


def lead(page, n=240):
    t = D.cached_extract(page)
    return re.sub(r"\s+", " ", t[:n]).strip()


ap = argparse.ArgumentParser()
ap.add_argument("--roles", default="passages.csv")
ap.add_argument("--sample", type=int, default=30)
args = ap.parse_args()

rows = [r for r in csv.DictReader(open(args.roles, encoding="utf-8"))
        if r["wiki_page"] and int(r["n_words"] or 0) >= 25]
pages = {}
for r in rows:
    pages.setdefault(r["wiki_page"], r["film"])

parsed = {p: D.director_of(p) for p in pages}
got = {p: d for p, d in parsed.items() if d}
print(f"film articles with a usable passage : {len(pages)}")
print(f"  director parsed                   : {len(got)}  "
      f"({len(got)/len(pages):.0%})\n")

# ---- systematic smells, which a sample of 30 would not catch ----------
print("=" * 70)
print("SMELL TESTS")
counts = Counter(got.values())
print(f"\ndistinct directors parsed: {len(counts)}")
print("most prolific (a wrong parse often repeats):")
for name, n in counts.most_common(8):
    print(f"   {n:>4}  {name}")

actors = {r["actor"] for r in rows}
clash = sorted({d for d in counts if d in actors})
print(f"\nparsed names that are also actor names in our data: {len(clash)}")
for c in clash[:10]:
    print(f"   {c}")

odd = sorted({d for d in counts
              if not re.fullmatch(r"[A-Z][\w.'-]+(?: [A-Z][\w.'-]+){1,3}", d)})
print(f"\nnames not shaped like a person's name: {len(odd)}")
for o in odd[:10]:
    print(f"   {o!r}")

# ---- the readable sample ---------------------------------------------
print("\n" + "=" * 70)
print(f"RANDOM SAMPLE OF {args.sample} — mark each ok / wrong")
print("=" * 70)
for p in random.sample(sorted(got), min(args.sample, len(got))):
    print(f"\n  PARSED : {got[p]}")
    print(f"  page   : {p}")
    print(f"  lead   : {lead(p)}")
