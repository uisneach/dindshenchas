"""Extract a simplified outline of the island of Ireland from Natural Earth.

Source: ne_10m_admin_0_map_subunits.geojson (public domain), from
https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
Usage: python -I tools/make_outline.py <subunits.geojson> data/ireland.geojson
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio

KEEP = {"IRL": "Ireland", "NIR": "Northern Ireland"}  # SU_A3 codes
TOLERANCE = 0.004  # degrees, roughly 300 m
MIN_RING_POINTS = 4


def perp_dist(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def simplify(points, tol):
    # Iterative Douglas-Peucker
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = 0, None
        for k in range(i + 1, j):
            d = perp_dist(points[k], points[i], points[j])
            if d > best:
                best, idx = d, k
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [[round(x, 4), round(y, 4)] for (x, y), k in zip(points, keep) if k]


def main(src, dst):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    features = []
    for feat in data["features"]:
        code = feat["properties"].get("SU_A3")
        if code not in KEEP:
            continue
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        out = []
        for poly in polys:
            rings = [simplify(r, TOLERANCE) for r in poly]
            if len(rings[0]) >= MIN_RING_POINTS:
                out.append([r for r in rings if len(r) >= MIN_RING_POINTS])
        features.append({"type": "Feature", "properties": {"name": KEEP[code]},
                         "geometry": {"type": "MultiPolygon", "coordinates": out}})
    jsonio.write(dst, {"type": "FeatureCollection", "features": features}, geo=True)
    print(f"wrote {len(features)} features")


if __name__ == "__main__":
    main(*sys.argv[1:3])
