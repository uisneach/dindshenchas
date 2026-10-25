"""Build area shapes for large places (lakes, rivers, mountain ranges, plains).

Each place in data/places_src.json may have an "area" spec:
  {"lake": [names]}       lake outlines from OpenStreetMap, matched by name
  {"river": [names]}      the river's whole course, as lines
  {"upland": {"min_m": 250, "box": [w, s, e, n]}}
                          ground above min_m connected to the highest point near
                          the place, traced from elevation data (clipped to box)
  {"corridor": {"river": [names], "km": 4, "boxes": [[w, s, e, n], ...]}}
                          a band km either side of the river within the boxes:
                          an approximate extent for a plain with no defined edge

Inputs (in <osm-dir>): lakes_osm.geojson and rivers_osm.geojson, from OpenStreetMap
via Overpass; terrarium elevation tiles (Terrain Tiles on AWS Open Data) at zoom 10
in <elevation-cache>/10/x/y.png (downloaded if missing).

Build-only dependencies: numpy and Pillow. Run without -I so user-installed
packages load; -P keeps this folder off the import path:
    python -E -P tools/make_areas.py <osm-dir> <elevation-cache>
Writes data/areas.geojson
"""
import json
import math
import os
import sys
import urllib.request
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z = 10  # elevation and raster work happen in zoom-10 pixels (~95 m in Ireland)
SOURCE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
USER_AGENT = "dindshenchas-map/0.1 (build script)"
LAKE_TOLERANCE = 0.0004   # degrees, ~30 m
RIVER_TOLERANCE = 0.001   # degrees, ~80 m


# ---------- geometry helpers ----------

def to_px(lon, lat):
    n = 256 * 2 ** Z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def to_lonlat(x, y):
    n = 256 * 2 ** Z
    return x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def simplify(points, tol):
    """Douglas-Peucker."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = points[i], points[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        best, idx = 0, None
        for k in range(i + 1, j):
            x, y = points[k]
            if norm == 0:  # a closed ring: measure from the shared end point
                d = math.hypot(x - x1, y - y1)
            else:
                d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
            if d > best:
                best, idx = d, k
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [p for p, k in zip(points, keep) if k]


def chaikin(ring, rounds=2):
    """Round off the stair-steps of a traced pixel outline."""
    for _ in range(rounds):
        out = []
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            out += [(0.75 * x1 + 0.25 * x2, 0.75 * y1 + 0.25 * y2),
                    (0.25 * x1 + 0.75 * x2, 0.25 * y1 + 0.75 * y2)]
        ring = out
    return ring


def rnd(points):
    return [[round(x, 4), round(y, 4)] for x, y in points]


# ---------- raster helpers ----------

def elevation(cache, x0, y0, x1, y1):
    """Elevation grid for zoom-10 pixel window [x0, x1) x [y0, y1)."""
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x1 - 1) // 256, (y1 - 1) // 256
    rows = []
    for ty in range(ty0, ty1 + 1):
        row = []
        for tx in range(tx0, tx1 + 1):
            path = os.path.join(cache, str(Z), str(tx), f"{ty}.png")
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                req = urllib.request.Request(SOURCE.format(z=Z, x=tx, y=ty), headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=60) as resp, open(path, "wb") as f:
                    f.write(resp.read())
            rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
            row.append(rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768)
        rows.append(np.hstack(row))
    grid = np.vstack(rows)
    return grid[y0 - ty0 * 256:y1 - ty0 * 256, x0 - tx0 * 256:x1 - tx0 * 256]


def component(mask, seed):
    """The 4-connected region of mask containing seed, with interior holes filled."""
    h, w = mask.shape
    out = np.zeros_like(mask)
    q = deque([seed])
    out[seed] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                q.append((ny, nx))
    # Fill holes: anything not reachable from the edge through non-region pixels
    outside = np.zeros_like(mask)
    q = deque((y, x) for y in range(h) for x in (0, w - 1) if not out[y, x])
    q.extend((y, x) for x in range(w) for y in (0, h - 1) if not out[y, x])
    for y, x in q:
        outside[y, x] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and not out[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    return ~outside


DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]  # E, SE, S, ... clockwise


def trace(mask):
    """Outer boundary of a single filled region, as pixel-centre (x, y) points (Moore tracing)."""
    m = np.pad(mask, 1)
    ys, xs = np.nonzero(m)
    start = (int(xs[np.argmin(ys * m.shape[1] + xs)]), int(ys.min()))
    ring, c, back = [start], start, 4  # entered from the west
    for _ in range(m.size):
        for i in range(1, 9):
            d = (back + i) % 8
            nx, ny = c[0] + DIRS[d][0], c[1] + DIRS[d][1]
            if m[ny, nx]:
                px, py = c[0] + DIRS[(d - 1) % 8][0], c[1] + DIRS[(d - 1) % 8][1]
                back = DIRS.index((px - nx, py - ny))
                c = (nx, ny)
                break
        else:
            break  # isolated pixel
        if c == start:
            break
        ring.append(c)
    return [(x - 1 + 0.5, y - 1 + 0.5) for x, y in ring]


def mask_to_polygon(mask, ox, oy):
    ring = simplify(chaikin(trace(mask)), 0.6)
    ring = [to_lonlat(ox + x, oy + y) for x, y in ring]
    return {"type": "Polygon", "coordinates": [rnd(ring + ring[:1])]}


# ---------- area kinds ----------

def lake(names, lakes):
    polys = []
    for f in lakes["features"]:
        if f["properties"]["name"] in names:
            rings = f["geometry"]["coordinates"]
            n = f["properties"]["outer"]
            for outer in rings[:n]:
                # Islands are kept with whichever outer ring contains them
                polys.append([rnd(simplify(outer, LAKE_TOLERANCE))] +
                             [rnd(simplify(r, LAKE_TOLERANCE)) for r in rings[n:]
                              if contains(outer, r[0])])
    return {"type": "MultiPolygon", "coordinates": polys} if polys else None


def contains(ring, pt):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def river(names, rivers):
    lines = [rnd(simplify(f["geometry"]["coordinates"], RIVER_TOLERANCE))
             for f in rivers["features"] if f["properties"]["name"] in names]
    return {"type": "MultiLineString", "coordinates": lines} if lines else None


def upland(spec, point, cache):
    w, s, e, n = spec["box"]
    x0, y0 = map(int, to_px(w, n))
    x1, y1 = map(int, map(math.ceil, to_px(e, s)))
    elev = elevation(cache, x0, y0, x1, y1)
    # Seed at the highest ground within ~8 km of the place's marker
    px, py = to_px(*point)
    r = 85
    cy, cx = int(py) - y0, int(px) - x0
    win = elev[max(0, cy - r):cy + r, max(0, cx - r):cx + r]
    sy, sx = np.unravel_index(np.argmax(win), win.shape)
    seed = (max(0, cy - r) + sy, max(0, cx - r) + sx)
    return mask_to_polygon(component(elev >= spec["min_m"], seed), x0, y0)


def corridor(spec, rivers):
    lines = []
    for f in rivers["features"]:
        if f["properties"]["name"] not in spec["river"]:
            continue
        run = []
        for lon, lat in f["geometry"]["coordinates"]:
            if any(b[0] <= lon <= b[2] and b[1] <= lat <= b[3] for b in spec["boxes"]):
                run.append(to_px(lon, lat))
            elif run:
                lines.append(run)
                run = []
        if run:
            lines.append(run)
    if not lines:
        return None
    xs = [x for l in lines for x, _ in l]
    ys = [y for l in lines for _, y in l]
    lat = sum(to_lonlat(0, y)[1] for y in ys) / len(ys)
    radius = spec["km"] * 1000 / (156543.03 * math.cos(math.radians(lat)) / 2 ** Z)
    pad = int(radius) + 4
    ox, oy = int(min(xs)) - pad, int(min(ys)) - pad
    img = Image.new("1", (int(max(xs)) - ox + pad, int(max(ys)) - oy + pad), 0)
    draw = ImageDraw.Draw(img)
    for l in lines:
        pts = [(x - ox, y - oy) for x, y in l]
        draw.line(pts, fill=1, width=int(2 * radius))
        for x, y in pts:  # round joins
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=1)
    mask = np.asarray(img, dtype=bool)
    ys_, xs_ = np.nonzero(mask)
    seed = (int(ys_[len(ys_) // 2]), int(xs_[len(xs_) // 2]))
    return mask_to_polygon(component(mask, seed), ox, oy)


def main(osm_dir, cache):
    places = json.load(open(os.path.join(ROOT, "data", "places_src.json"), encoding="utf-8"))
    wd = json.load(open(os.path.join(ROOT, "data", "wikidata_cache.json"), encoding="utf-8"))
    lakes = json.load(open(os.path.join(osm_dir, "lakes_osm.geojson"), encoding="utf-8"))
    rivers = json.load(open(os.path.join(osm_dir, "rivers_osm.geojson"), encoding="utf-8"))
    features = []
    for p in places:
        spec = p.get("area")
        if not spec:
            continue
        (kind, arg), = spec.items()
        point = p.get("coordinates") or wd.get(p["id"], {}).get("coordinates")
        if kind == "lake":
            geom = lake(arg, lakes)
        elif kind == "river":
            geom = river(arg, rivers)
        elif kind == "upland":
            geom = upland(arg, point, cache)
        else:
            geom = corridor(arg, rivers)
        if not geom:
            print(f"{p['id']}: no geometry found for {spec}")
            continue
        features.append({"type": "Feature", "id": p["id"],
                         "properties": {"kind": kind, "approximate": kind == "corridor"},
                         "geometry": geom})
        size = len(json.dumps(geom))
        print(f"{p['id']:15} {kind:9} {size // 1024} KB")
    jsonio.write(os.path.join(ROOT, "data", "areas.geojson"),
                 {"type": "FeatureCollection", "features": features}, geo=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
