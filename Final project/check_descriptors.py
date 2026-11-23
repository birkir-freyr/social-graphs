#!/usr/bin/env python3
"""
Does the result depend on roles with descriptive credits?

Some parts are credited as a description rather than a name -- "The Man",
"French Soldier", "Starbucks Angry Man". Those have no personal name to
match, and a name fragment taken from such a credit can match sentences
about someone else entirely. If the finding leaned on them it would be
an artefact of the extraction rather than a fact about casting.

This drops every role with a descriptor-style credit and reruns the
measure. It shells out to typecast.py rather than reimplementing the
scoring, so the comparison is against the real analysis and cannot
drift from it. The filtered dataset is written to a temporary file and
deleted, so no result file in the repo changes.

    python3 check_descriptors.py --roles passages.csv

Reproduces the sentence in Results: "Removing every role with a
descriptor-style credit (N roles) moves the estimate from X to Y and
leaves p unchanged."
"""

import argparse, csv, json, os, re, subprocess, sys, tempfile

# Words that mark a credit as a description of a part rather than a name.
# Deliberately broad: it over-flags real names such as "Lady Macduff",
# which is the safe direction -- the test asks whether the result
# survives dropping a superset of the suspect roles.
DESCRIPTOR = re.compile(
    r"\b(man|woman|boy|girl|guy|lady|guard|waitress|waiter|cop|officer|"
    r"nurse|doctor|clerk|driver|bartender|soldier|student|reporter|teacher|"
    r"judge|priest|guest|customer|patient|worker|assistant|secretary|angry|"
    r"young|old|first|second|third|#\d|no\.\s*\d|\bvoice\b|himself|herself)\b",
    re.I)

TITLES = {"the", "dr", "mr", "mrs", "ms"}


def is_descriptor(character):
    """True when a credit names no person."""
    c = re.sub(r"\(.*?\)", " ", character or "").strip()
    if not c:
        return True
    if DESCRIPTOR.search(c):
        return True
    # nothing in it looks like a personal name
    toks = [t for t in re.split(r"[\s,/]+", c) if t]
    return not any(len(t) > 2 and t[0].isupper() and t.lower() not in TITLES
                   for t in toks)


HERE = os.path.dirname(os.path.abspath(__file__))


def run_typecast(roles_path, text, min_results):
    """Call the real analysis and read its JSON back.

    Run from a scratch directory with absolute paths. typecast.py writes
    typecast_results.csv beside wherever it is run, and running it from
    the repo would overwrite the committed results with this check's
    filtered version -- which it silently did the first time.
    """
    work = tempfile.mkdtemp()
    out = os.path.join(work, "result.json")
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "typecast.py"),
             "--roles", os.path.abspath(roles_path),
             "--text", text, "--json", out,
             "--min-results", str(min_results)],
            capture_output=True, text=True, cwd=work)
        if not os.path.exists(out) or not os.path.getsize(out):
            sys.exit("typecast.py produced no JSON:\n" + r.stdout + r.stderr)
        with open(out, encoding="utf-8") as f:
            return json.load(f)
    finally:
        for n in os.listdir(work):
            os.unlink(os.path.join(work, n))
        os.rmdir(work)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default="passages.csv")
    ap.add_argument("--text", default="role_text_blind")
    ap.add_argument("--min-results", type=int, default=8)
    ap.add_argument("--show", type=int, default=12,
                    help="how many dropped credits to print")
    args = ap.parse_args()

    with open(args.roles, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        cols = rows[0].keys()

    keep = [r for r in rows if not is_descriptor(r["character"])]
    dropped = [r for r in rows if is_descriptor(r["character"])]
    usable_dropped = [r for r in dropped if int(r["n_words"] or 0) >= 25]

    print(f"{len(rows)} roles")
    print(f"  descriptor-style credits dropped : {len(dropped)}")
    print(f"  of those, usable (25+ words)     : {len(usable_dropped)}")
    print(f"  remaining                        : {len(keep)}")
    print("\nexamples of dropped credits:")
    for r in dropped[:args.show]:
        print(f"   {r['actor'][:20]:<22}{r['character'][:28]:<30}{r['film'][:26]}")

    full = run_typecast(args.roles, args.text, args.min_results)

    tmpdir = tempfile.mkdtemp()
    strict = os.path.join(tmpdir, "passages_strict.csv")
    try:
        with open(strict, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(cols))
            w.writeheader()
            w.writerows(keep)
        cut = run_typecast(strict, args.text, args.min_results)
    finally:
        if os.path.exists(strict):
            os.unlink(strict)
        os.rmdir(tmpdir)

    print("\n" + "=" * 62)
    print(f"{'':<22}{'all roles':>12}{'descriptors cut':>18}")
    print(f"{'mean difference':<22}{full['obs']:>+12.4f}{cut['obs']:>+18.4f}")
    print(f"{'z':<22}{full['z']:>+12.2f}{cut['z']:>+18.2f}")
    print(f"{'p':<22}{full['p']:>12.4f}{cut['p']:>18.4f}")
    print(f"{'actor-roles':<22}{full['n_roles']:>12}{cut['n_roles']:>18}")
    print(f"{'actors':<22}{full['n_actors']:>12}{cut['n_actors']:>18}")
    print("=" * 62)

    moved = abs(cut["obs"] - full["obs"])
    if moved < 0.002 and (cut["p"] < .05) == (full["p"] < .05):
        print("\nThe finding does not rest on descriptor-credited roles: the")
        print(f"estimate moves by {moved:.4f} and the conclusion is unchanged.")
    else:
        print("\nDropping these roles changes the result materially. The")
        print("finding may be an artefact of credits with no personal name;")
        print("report the cut version, not the full one.")


if __name__ == "__main__":
    main()
