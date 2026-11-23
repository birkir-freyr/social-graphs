#!/usr/bin/env python3
"""Integrity checks on the inputs, not the method.

The statistics have been tested against synthetic data. These are the
checks on whether the data going in is what we think it is.
"""
import csv, hashlib, json, os, re, sys
from collections import Counter, defaultdict
from urllib.parse import quote

rows = list(csv.DictReader(open("passages.csv", encoding="utf-8")))
us = [r for r in rows if int(r["n_words"] or 0) >= 25]
films = {r["film_id"]: r for r in csv.DictReader(
    open("data/nolan/nolan_films.csv", encoding="utf-8"))}
prior = list(csv.DictReader(
    open("data/nolan/roles_before_nolan_film.csv", encoding="utf-8")))

print("=" * 64)
print("1. Are the 'Nolan roles' actually from Nolan films?")
nol_titles = {f["title"] for f in films.values()}
bad = {r["film"] for r in rows if r["is_nolan"] == "1"} - nol_titles
print(f"   Nolan films in nolan_films.csv : {len(nol_titles)}")
print(f"   is_nolan rows citing a film not in that list: {len(bad)} {sorted(bad)[:4]}")

print("\n2. Are 'prior' roles actually earlier than the Nolan film?")
nolan_year = {}
for r in rows:
    if r["is_nolan"] == "1" and r["year"].isdigit():
        nolan_year.setdefault(r["actor"], []).append(int(r["year"]))
late = 0
for r in rows:
    if r["is_nolan"] != "1" and r["year"].isdigit() and r["actor"] in nolan_year:
        if int(r["year"]) > max(nolan_year[r["actor"]]):
            late += 1
print(f"   non-Nolan roles dated AFTER that actor's last Nolan film: {late}")
print("   (typecast.py filters on year itself, so these cannot leak into a")
print("    centroid — but they show the CSV is not purely 'before')")

print("\n3. Duplicate rows?")
key = Counter((r["actor"], r["film"], r["character"]) for r in rows)
dups = [k for k, n in key.items() if n > 1]
print(f"   repeated (actor, film, character): {len(dups)}  {dups[:3]}")

print("\n4. Do two roles share identical text? (same character, two actors)")
txt = defaultdict(list)
for r in us:
    if r["role_text"]:
        txt[hashlib.md5(r["role_text"].encode()).hexdigest()].append(
            f"{r['actor']}/{r['character'][:14]}/{r['film'][:16]}")
shared = {h: v for h, v in txt.items() if len(v) > 1}
print(f"   passages shared by 2+ roles: {len(shared)} groups, "
      f"{sum(len(v) for v in shared.values())} roles")
for v in list(shared.values())[:4]:
    print(f"     {v}")

print("\n5. Missing or impossible years")
noyear = sum(1 for r in us if not r["year"].isdigit())
odd = [r["year"] for r in us if r["year"].isdigit()
       and not (1900 <= int(r["year"]) <= 2027)]
print(f"   usable roles with no year: {noyear}   out-of-range years: {len(odd)}")

print("\n6. Nolan film list and release years")
for f in sorted(films.values(), key=lambda f: f.get("year", "")):
    print(f"     {f.get('year',''):<6}{f.get('title','')[:34]:<36}"
          f"status={f.get('status','?')}  included={f.get('included','?')}")
