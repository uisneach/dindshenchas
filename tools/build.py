"""Assemble the site data from the place list and the extracted source texts.

Reads:  data/places_src.json, data/wikidata_cache.json, data/images.json (optional),
        sources/stokes_rennes.json, sources/gwynn_*.json
Writes: data/places.geojson, data/entries/<id>.json
Usage:  python -I tools/build.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STOKES_ITEMS = {15: "revueceltique15pari", 16: "revueceltiqu16pari"}
# Page ranges where the Rennes Dindshenchas is printed; OCR'd page numbers
# outside these are misreads and are dropped.
STOKES_PAGES = {15: [(272, 336), (418, 484)], 16: [(31, 83), (135, 175), (270, 290)]}

GWYNN_SOURCES = {
    "gwynn_part3": "toddlectureserie10royauoft",   # Part III only, so page links are safe
    "gwynn_toronto_v7-9": "toddlectureserie09royauoft",
    "gwynn_google_v8-10": "toddlectureseri02acadgoog",
}
SINGLE_VOLUME = {"gwynn_part3"}

PART_I = "The Metrical Dindshenchas, Part I (Todd Lecture Series VIII, 1903)"
PART_II = "The Metrical Dindshenchas, Part II (Todd Lecture Series IX, 1906)"
PART_III = "The Metrical Dindshenchas, Part III (Todd Lecture Series X, 1913)"
POEMS_1900 = "Poems from the Dindshenchas (Todd Lecture Series VII, 1900)"


def gwynn_edition(poem):
    base = poem.rsplit(" ", 1)[0] if poem.endswith((" I", " II", " III", " IV", " V")) else poem
    if base == "TEMAIR":
        return PART_I
    if base in ("BRUG", "MIDE", "SLIAB BLADMA", "MAG LIFE"):
        return PART_II
    if base == "AILECH":
        return POEMS_1900
    return PART_III


def display_title(poem):
    words = poem.split()
    return " ".join(w if w in ("I", "II", "III", "IV", "V") else w.capitalize() for w in words)


def load(path, default=None):
    full = os.path.join(ROOT, path)
    if default is not None and not os.path.exists(full):
        return default
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def stokes_section(stokes, n):
    item = stokes.get(str(n))
    if not item:
        return None
    vol, page = item["volume"], item["page"]
    if page and not any(a <= page <= b for a, b in STOKES_PAGES[vol]):
        page = None
    ident = STOKES_ITEMS[vol]
    year = 1894 if vol == 15 else 1895
    # Labels such as "no." and "p." are added by the page in the reader's language.
    return {
        "type": "prose",
        "number": n,
        "title": " ".join(item["title"].split()),
        "citation": f"Whitley Stokes, ‘The Prose Tales in the Rennes Dindshenchas’, "
                    f"Revue Celtique {vol} ({year})",
        "pages": [page] if page else None,
        "scan": f"https://archive.org/details/{ident}" + (f"/page/{page}/mode/1up" if page else ""),
        "ga": item["ga"],
        "en": item["en"],
        "notes": item["notes"],
    }


def gwynn_section(gwynn_sources, poem):
    # Several scans contain the same poem; prefer the one whose Irish and English agree.
    best = None
    for name, data in gwynn_sources.items():
        for key, r in data.items():
            if key.split("|")[0] != poem or not (r["ga"] and r["en"]):
                continue
            ga, en = r["line_counts"]
            score = (round(abs(ga - en) / max(ga, en), 2), -(ga + en))
            if best is None or score < best[0]:
                best = (score, name, r)
    if not best:
        return None
    _, name, r = best
    ga_lines, en_lines = r["line_counts"]
    pages = r["pages"]
    page_link = name in SINGLE_VOLUME and pages
    section = {
        "type": "verse",
        "title": display_title(poem),
        "citation": f"Edward Gwynn, {gwynn_edition(poem)}",
        "pages": pages if page_link else None,
        "scan": f"https://archive.org/details/{GWYNN_SOURCES[name]}"
                + (f"/page/{pages[0]}/mode/2up" if page_link else ""),
        "ga": r["ga"],
        "en": r["en"],
    }
    if abs(ga_lines - en_lines) > 2:
        section["incomplete"] = [ga_lines, en_lines]  # the page explains the mismatch
    return section


def main():
    places = load("data/places_src.json")
    wd = load("data/wikidata_cache.json", {})
    images = load("data/images.json", {})
    stokes = load("sources/stokes_rennes.json")
    gwynn = {name: load(f"sources/{name}.json") for name in GWYNN_SOURCES}

    os.makedirs(os.path.join(ROOT, "data", "entries"), exist_ok=True)
    features = []
    for p in places:
        info = wd.get(p["id"], {})
        coords = p.get("coordinates") or info.get("coordinates")
        if p["confidence"] == "unlocated":
            coords = None

        sections = [s for s in (stokes_section(stokes, n) for n in p.get("stokes", [])) if s]
        sections += [s for s in (gwynn_section(gwynn, poem) for poem in p.get("gwynn", [])) if s]

        entry = {k: p.get(k) for k in ("id", "name_mir", "name_ga", "name_en", "county", "county_ga",
                                       "kind", "confidence", "precision", "reviewed", "note", "note_ga")}
        entry["wikipedia"] = p.get("wikipedia")
        entry["wikipedia_ga"] = info.get("wikipedia_ga")
        entry["logainm"] = info.get("logainm")
        entry["images"] = images.get(p["id"], [])
        entry["sections"] = sections
        jsonio.write(os.path.join(ROOT, "data", "entries", f"{p['id']}.json"), entry)

        props = {k: p.get(k) for k in ("name_mir", "name_ga", "name_en", "county", "kind", "confidence")}
        props["prose"] = sum(s["type"] == "prose" for s in sections)
        props["verse"] = sum(s["type"] == "verse" for s in sections)
        features.append({"type": "Feature", "id": p["id"], "properties": props,
                         "geometry": {"type": "Point", "coordinates": coords} if coords else None})
        print(f"{p['id']:15} {'located' if coords else 'UNLOCATED':10} "
              f"prose={props['prose']} verse={props['verse']} images={len(entry['images'])}")

    jsonio.write(os.path.join(ROOT, "data", "places.geojson"),
                 {"type": "FeatureCollection", "features": features}, geo=True)


if __name__ == "__main__":
    main()
