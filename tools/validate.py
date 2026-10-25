"""Check the built site data before committing.

Fails (exit 1) on: places outside Ireland, missing entry files, broken image
paths, images without a licence or author, or a place with no text at all.
Usage: python -I tools/validate.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBOX = (-10.8, 51.3, -5.3, 55.5)  # lon/lat bounds of the island of Ireland


def main():
    errors, warnings = [], []
    with open(os.path.join(ROOT, "data", "places.geojson"), encoding="utf-8") as f:
        features = json.load(f)["features"]
    ids = [f["id"] for f in features]
    if len(ids) != len(set(ids)):
        errors.append("duplicate place ids")

    for feat in features:
        pid = feat["id"]
        if feat["geometry"]:
            lon, lat = feat["geometry"]["coordinates"]
            if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                errors.append(f"{pid}: coordinates {lon}, {lat} are outside Ireland")
        elif feat["properties"]["confidence"] != "unlocated":
            errors.append(f"{pid}: no coordinates but not marked unlocated")

        path = os.path.join(ROOT, "data", "entries", f"{pid}.json")
        if not os.path.exists(path):
            errors.append(f"{pid}: missing entry file")
            continue
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if not entry["sections"]:
            errors.append(f"{pid}: no dindshenchas text")
        for s in entry["sections"]:
            if not s.get("en") and not s.get("ga"):
                errors.append(f"{pid}: {s['title']} has no text")
            if s.get("incomplete"):
                ga, en = s["incomplete"]
                warnings.append(f"{pid}: {s['title']}: OCR incomplete ({ga} Irish / {en} English lines)")
        for img in entry["images"]:
            if not os.path.exists(os.path.join(ROOT, img["file"])):
                errors.append(f"{pid}: image file {img['file']} missing")
            if not img.get("licence") or not img.get("author"):
                errors.append(f"{pid}: image {img['file']} lacks licence or author")
        if not entry.get("note_ga") and entry.get("note"):
            warnings.append(f"{pid}: note has no Irish version (note_ga)")
        if not entry["reviewed"]:
            warnings.append(f"{pid}: identification not yet reviewed")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(features)} places, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
