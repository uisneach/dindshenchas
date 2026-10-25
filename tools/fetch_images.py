"""Download a resized copy of each place's Wikimedia Commons photo, with its credit.

Uses the image Wikidata lists for the place (data/wikidata_cache.json), plus any
extra files named in data/images_src.json ({"place-id": [{"file": "X.jpg",
"era": "historical"}]}). Licence and author come from the Commons API, and
images without a free licence are skipped.

Usage: python -I tools/fetch_images.py
Writes img/<id>-<n>.jpg and data/images.json
"""
import json
import os
import sys
import re
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "dindshenchas-map/0.1 (build script)"
WIDTH = 800
FREE = re.compile(r"^(CC0|CC BY|CC-BY|Public domain|PD|No restrictions|GFDL)", re.I)


def get(url, tries=5):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(tries):
        time.sleep(1.5)  # stay well inside Wikimedia's rate limits
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def image_info(filename):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo",
        "titles": "File:" + filename, "iiprop": "url|extmetadata", "iiurlwidth": WIDTH,
    })
    pages = json.loads(get(f"{API}?{q}"))["query"]["pages"]
    info = next(iter(pages.values()))["imageinfo"][0]
    meta = info["extmetadata"]
    return {
        "thumb": info["thumburl"],
        "source_url": info["descriptionurl"],
        "author": strip_html(meta.get("Artist", {}).get("value")) or "Unknown",
        "licence": strip_html(meta.get("LicenseShortName", {}).get("value")),
        "licence_url": meta.get("LicenseUrl", {}).get("value"),
        "caption": strip_html(meta.get("ImageDescription", {}).get("value"))[:200],
        "date": re.sub(r"^(\d{4}-\d\d-\d\d) .*", r"\1",
                       strip_html(meta.get("DateTimeOriginal", {}).get("value")))[:40],
    }


def main():
    with open(os.path.join(ROOT, "data", "wikidata_cache.json"), encoding="utf-8") as f:
        wd = json.load(f)
    extra_path = os.path.join(ROOT, "data", "images_src.json")
    extra = {}
    if os.path.exists(extra_path):
        with open(extra_path, encoding="utf-8") as f:
            extra = json.load(f)

    wanted = {}
    for pid, info in wd.items():
        if info.get("image_commons"):
            wanted.setdefault(pid, []).append({"file": info["image_commons"], "era": "today"})
    for pid, files in extra.items():
        wanted.setdefault(pid, []).extend(files)

    os.makedirs(os.path.join(ROOT, "img"), exist_ok=True)
    out = {}
    for pid, files in wanted.items():
        for n, spec in enumerate(files, 1):
            try:
                meta = image_info(spec["file"])
            except Exception as e:  # missing or renamed file
                print(f"{pid}: {spec['file']}: {e}")
                continue
            if not FREE.match(meta["licence"]):
                print(f"{pid}: skipped, licence {meta['licence']!r}")
                continue
            local = f"img/{pid}-{n}.jpg"
            path = os.path.join(ROOT, local)
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(get(meta.pop("thumb")))
            else:
                meta.pop("thumb")
            out.setdefault(pid, []).append({"file": local, "era": spec.get("era", "today"), **meta})
            print(f"{pid}: {local} ({meta['licence']}, {meta['author'][:40]})")

    jsonio.write(os.path.join(ROOT, "data", "images.json"), out)


if __name__ == "__main__":
    main()
