"""Fetch Ireland's lakes from OpenStreetMap (Overpass API), for area shapes.

Used by tools/make_areas.py for lake shapes (OSM data is ODbL; credited in the
About box). Lakes smaller than MIN_AREA_KM2 are dropped, and outlines are
simplified to about 15 m.
Usage: python -I tools/fetch_lakes.py downloads/osm/lakes_osm.geojson
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_outline import simplify

ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "dindshenchas-map/0.1 (build script)"
QUERY = """
[out:json][timeout:300][maxsize:1073741824];
(
  way["natural"="water"]["water"~"^(lake|reservoir|lagoon)$"](51.3,-10.8,55.5,-5.3);
  relation["natural"="water"]["water"~"^(lake|reservoir|lagoon)$"](51.3,-10.8,55.5,-5.3);
  way["natural"="water"][!"water"]["name"~"^Lough"](51.3,-10.8,55.5,-5.3);
  relation["natural"="water"][!"water"]["name"~"^Lough"](51.3,-10.8,55.5,-5.3);
);
out geom;
"""
MIN_AREA_KM2 = 0.15
TOLERANCE = 0.0002  # degrees, ~15 m


def area_km2(ring):
    """Approximate area of a lon/lat ring (shoelace on a local equirectangular plane)."""
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx, ky = 111.32 * math.cos(lat0), 110.57
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        s += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(s) / 2


def join_ways(parts):
    """Join way segments that share endpoints into closed rings."""
    parts = [p[:] for p in parts if len(p) >= 2]
    rings = []
    while parts:
        ring = parts.pop()
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, p in enumerate(parts):
                if p[0] == ring[-1]:
                    ring += p[1:]
                elif p[-1] == ring[-1]:
                    ring += p[::-1][1:]
                elif p[-1] == ring[0]:
                    ring = p[:-1] + ring
                elif p[0] == ring[0]:
                    ring = p[::-1][:-1] + ring
                else:
                    continue
                parts.pop(i)
                changed = True
                break
        if ring[0] == ring[-1] and len(ring) >= 4:
            rings.append(ring)
    return rings


def main(out_path):
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp:
        elements = json.load(resp)["elements"]

    features = []
    for el in elements:
        if el["type"] == "way":
            outers = join_ways([[[p["lon"], p["lat"]] for p in el.get("geometry", [])]])
            inners = []
        else:
            members = [m for m in el.get("members", []) if m["type"] == "way" and m.get("geometry")]
            line = lambda m: [[p["lon"], p["lat"]] for p in m["geometry"]]
            outers = join_ways([line(m) for m in members if m.get("role") != "inner"])
            inners = join_ways([line(m) for m in members if m.get("role") == "inner"])
        outers = [r for r in outers if area_km2(r) >= MIN_AREA_KM2]
        if not outers:
            continue
        # Islands (inner rings) are kept if big enough to see
        inners = [r for r in inners if area_km2(r) >= MIN_AREA_KM2 / 3]
        rings = [simplify(r, TOLERANCE) for r in outers + inners]
        features.append({"type": "Feature",
                         "properties": {"name": el.get("tags", {}).get("name"),
                                        "outer": len(outers)},
                         "geometry": {"type": "MultiLineString", "coordinates": rings}})

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False,
                  separators=(",", ":"))
    named = sorted({f["properties"]["name"] for f in features if f["properties"]["name"]})
    print(f"{len(features)} lakes kept ({len(named)} named), e.g. {', '.join(named[:12])}")


if __name__ == "__main__":
    main(sys.argv[1])
