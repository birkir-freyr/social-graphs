"""Independent check of Fig. 1 (main-cast network): recompute the main cast from the raw CSV and compare with every line, dot and label drawn in figures/nolan_main_cast_network.pdf. Run with PyMuPDF installed: python investigations/verify_fig1.py"""
import csv, math, os, re, sys
from collections import defaultdict
import fitz

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
# ---------- 1. truth straight from the raw CSV ----------
films = {r["film_id"]: (r["title"], r["wikipedia_year"]) for r in csv.DictReader(open(D + "data/nolan/nolan_films.csv"))}
truth = defaultdict(set)
for r in csv.DictReader(open(D + "data/nolan/nolan_cast.csv")):
    if r["uncredited"] == "True" or r["voice"] == "True" or r["archive_footage"] == "True":
        continue
    if int(r["cast_order"]) >= 10:
        continue
    truth[r["actor_name"]].add(films[r["film_id"]][0])
returning = {a: fs for a, fs in truth.items() if len(fs) >= 2}
single = {a: fs for a, fs in truth.items() if len(fs) == 1}
per_film_single = defaultdict(int)
for a, fs in single.items():
    per_film_single[next(iter(fs))] += 1
print(f"TRUTH: {len(truth)} main-cast actors, {len(returning)} returning, {len(single)} one-film, "
      f"{sum(map(len, truth.values()))} links")

# ---------- 2. what the PDF actually draws ----------
page = fitz.open(D + "figures/nolan_main_cast_network.pdf")[0]
spans = []
for b in page.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            if s["text"].strip():
                spans.append((s["text"].strip(), fitz.Rect(s["bbox"]), s["color"], "Bold" in s["font"]))
def hexrgb(c):
    return tuple(round(x, 3) for x in c) if c else None

lines, squares, black, grey = [], [], [], []
for d in page.get_drawings():
    items = d["items"]
    fill, stroke = hexrgb(d.get("fill")), hexrgb(d.get("color"))
    r = d["rect"]; c = fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    kinds = {it[0] for it in items}
    if len(items) == 1 and items[0][0] == "l" and stroke and fill is None:
        lines.append((items[0][1], items[0][2], stroke))
    elif stroke == (1.0, 1.0, 1.0) and fill is not None:          # markers have a white outline
        if "c" in kinds:
            black.append((c, fill, r.width))
        else:
            squares.append((c, fill, r.width))
    elif fill is not None and abs(fill[0] - 0.71) < 0.01 and fill[0] == fill[1] == fill[2] and r.width < 4:
        grey.append((c, fill, r.width))
print(f"DRAWN: {len(lines)} line segments, {len(squares)} squares, {len(black)} black dots, {len(grey)} grey dots")

# film squares -> film name via the bold coloured title nearest to the square, colour must match
film_titles = [s for s in spans if s[3] and not re.fullmatch(r"\(\d{4}\)", s[0])]
year_spans = [s for s in spans if s[3] and re.fullmatch(r"\(\d{4}\)", s[0])]
sq_film = {}
cx = sum(c.x for c, _, _ in squares) / len(squares)
cy = sum(c.y for c, _, _ in squares) / len(squares)
def bearing(x, y):
    return math.atan2(y - cy, x - cx)
for c, col, w in squares:
    # the title sits straight outside its square: pick the title with the same bearing from the centre
    sb = bearing(c.x, c.y)
    def angdiff(s):
        tb = bearing((s[1].x0 + s[1].x1) / 2, (s[1].y0 + s[1].y1) / 2)
        d = abs(tb - sb)
        return min(d, 2 * math.pi - d)
    title = min(film_titles, key=angdiff)
    sq_film[(round(c.x, 1), round(c.y, 1))] = (title[0], col)
names_on_ring = sorted(v[0] for v in sq_film.values())
print("Films on ring:", names_on_ring)

def nearest(pt, pts):
    return min(pts, key=lambda p: abs(p[0] - pt))

# assign each line: one end at a square, other end at a dot
drawn_returning = defaultdict(set)
drawn_single_per_film = defaultdict(int)
colour_ok = 0
for p, q, col in lines:
    sp, sq_ = nearest(p, squares), nearest(q, squares)
    end_sq, other = (sp, q) if abs(sp[0] - p) < abs(sq_[0] - q) else (sq_, p)
    film, fcol = sq_film[(round(end_sq[0].x, 1), round(end_sq[0].y, 1))]
    if col == fcol:
        colour_ok += 1
    else:
        print("  COLOUR MISMATCH on a link to", film, col, fcol)
    dot = nearest(other, black + grey)
    if dot in black:
        drawn_returning[(round(dot[0].x, 1), round(dot[0].y, 1))].add(film)
    else:
        drawn_single_per_film[film] += 1
print(f"Links whose colour matches their film square: {colour_ok}/{len(lines)}")

# labels: each actor name -> nearest black dot
actor_spans = [s for s in spans if not s[3]]
problems = 0
used = {}
for name, rect, _, _ in actor_spans:
    centre = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
    # distance from the label box to each dot centre
    def box_dist(pt):
        dx = max(rect.x0 - pt.x, 0, pt.x - rect.x1)
        dy = max(rect.y0 - pt.y, 0, pt.y - rect.y1)
        return math.hypot(dx, dy)
    ranked = sorted(black, key=lambda d: box_dist(d[0]))
    dot = ranked[0]
    key = (round(dot[0].x, 1), round(dot[0].y, 1))
    gap = box_dist(dot[0]) - dot[2] / 2
    runner_up = box_dist(ranked[1][0]) - ranked[1][2] / 2
    drawn = drawn_returning.get(key, set())
    want = returning.get(name)
    ok = want == drawn
    used.setdefault(key, []).append(name)
    flag = "OK " if ok else "BAD"
    if not ok:
        problems += 1
    print(f"  {flag} {name:<22} drawn films={sorted(drawn)}  "
          f"label-to-own-dot gap={gap:5.1f}pt  next dot={runner_up:5.1f}pt")
    if want is None:
        print("      ^ name not in the truth list!"); problems += 1
dup = {k: v for k, v in used.items() if len(v) > 1}
missing = set(returning) - {s[0] for s in actor_spans}
print("Dots claimed by two labels:", dup or "none")
print("Returning actors with no label:", missing or "none")
print("Black dots:", len(black), "vs returning actors:", len(returning))
print("One-film actors per film (drawn vs truth):")
for f in sorted(per_film_single):
    d, t = drawn_single_per_film.get(f, 0), per_film_single[f]
    print(f"  {'OK ' if d == t else 'BAD'} {f:<24} drawn {d:>2}  truth {t:>2}")
    problems += d != t
print("Film years on the figure:", sorted(s[0] for s in year_spans))
print("PROBLEMS:", problems)
