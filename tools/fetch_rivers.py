"""Fetch the main rivers of Ireland from OpenStreetMap (Overpass API), simplified.

Used by tools/make_areas.py for river and plain shapes (OSM data is ODbL;
credited in the About box).
Usage: python -I tools/fetch_rivers.py downloads/osm/rivers_osm.geojson
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_outline import simplify

ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "dindshenchas-map/0.1 (build script)"
RIVERS = ("Boyne|Liffey|Shannon|Barrow|Nore|Suir|Slaney|Blackwater|Lee|Bann|Erne|Moy|Foyle|"
          "Bandon|Fergus|Inny|Suck|Brosna|Mourne|Finn|Lagan|Avoca|Dodder|Maigue|Feale|Laune|"
          "Corrib|Robe|Deel|Owenmore|Garavogue|Blackwater|Sligo|Clare|Camlin|Annalee|Woodford")
# Headwaters are often tagged as streams: the Boyne's first 3 km from Trinity Well are
QUERY = f"""
[out:json][timeout:180];
way["waterway"~"^(river|stream)$"]["name"~"^(River |An )?({RIVERS})( River)?$"](51.3,-10.8,55.5,-5.3);
out geom;
"""
TOLERANCE = 0.0003  # degrees, ~25 m: about one pixel at zoom 12


def main(out_path):
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):  # the public server is often busy: back off and retry
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                elements = json.load(resp)["elements"]
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 5:
                raise
            time.sleep(15 * 2 ** attempt)
    features = []
    for el in elements:
        line = [[p["lon"], p["lat"]] for p in el.get("geometry", [])]
        if len(line) >= 2:
            features.append({"type": "Feature", "properties": {"name": el["tags"].get("name")},
                             "geometry": {"type": "LineString", "coordinates": simplify(line, TOLERANCE)}})
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False,
                  separators=(",", ":"))
    names = sorted({f["properties"]["name"] for f in features})
    print(f"{len(features)} river segments: {', '.join(names)}")


if __name__ == "__main__":
    main(sys.argv[1])
