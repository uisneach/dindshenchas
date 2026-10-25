"""Look up coordinates, a Commons image and the Logainm ID for each place on Wikidata.

Offline build tool: runs on your machine, never deployed. Standard library only.
Usage: python -I tools/fetch_wikidata.py data/places_src.json data/wikidata_cache.json
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "dindshenchas-map/0.1 (build script)"

QUERY = """
SELECT ?title ?item ?coord ?image ?logainm ?gaTitle WHERE {
  VALUES ?title { %s }
  ?article schema:about ?item ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name ?title .
  OPTIONAL { ?item wdt:P625 ?coord }
  OPTIONAL { ?item wdt:P18 ?image }
  OPTIONAL { ?item wdt:P5097 ?logainm }
  OPTIONAL { ?gaArticle schema:about ?item ;
                        schema:isPartOf <https://ga.wikipedia.org/> ;
                        schema:name ?gaTitle . }
}
"""


def sparql(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["results"]["bindings"]


def parse_point(wkt):
    # Wikidata returns "Point(lon lat)"
    lon, lat = wkt.removeprefix("Point(").removesuffix(")").split()
    return [round(float(lon), 5), round(float(lat), 5)]


def main(src_path, out_path):
    with open(src_path, encoding="utf-8") as f:
        places = json.load(f)

    titles = " ".join(json.dumps(p["wikipedia"]) + "@en" for p in places if p.get("wikipedia"))
    rows = {}
    for b in sparql(QUERY % titles):
        rows.setdefault(b["title"]["value"], b)  # first match wins

    cache = {}
    for p in places:
        b = rows.get(p.get("wikipedia"))
        if not b:
            continue
        entry = {"wikidata": b["item"]["value"].rsplit("/", 1)[-1]}
        if "coord" in b:
            entry["coordinates"] = parse_point(b["coord"]["value"])
        if "image" in b:
            entry["image_commons"] = urllib.parse.unquote(b["image"]["value"].rsplit("/", 1)[-1])
        if "logainm" in b:
            entry["logainm"] = b["logainm"]["value"]
        if "gaTitle" in b:  # the Irish-language Wikipedia (Vicipéid) article, if any
            entry["wikipedia_ga"] = b["gaTitle"]["value"]
        cache[p["id"]] = entry

    jsonio.write(out_path, cache)
    missing = [p["id"] for p in places if p.get("wikipedia") and p["id"] not in cache]
    print(f"found {len(cache)} places on Wikidata; not found: {missing}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
