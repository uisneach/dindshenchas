"""Copy only the files the website needs into a folder for publishing.

Everything else in the repository (tools/, sources/, the place list and other
build inputs, notes) stays out of the published site.
Usage: python -I tools/build_site.py [out-dir]     (default: _site)
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths relative to the repository root; folders are copied whole
PUBLIC = [
    "index.html",
    "app.js",
    "style.css",
    "favicon.svg",
    "favicon.ico",
    "apple-touch-icon.png",
    "icon-192.png",
    "icon-512.png",
    "site.webmanifest",
    "vendor",
    "img",
    "data/places.geojson",
    "data/areas.geojson",
    "data/ireland.geojson",
    "data/entries",
]
OPTIONAL = [
    "CNAME",      # custom domain, once there is one
    ".nojekyll",
]


def main(out="_site"):
    out = os.path.abspath(os.path.join(ROOT, out))
    if out == ROOT or not out.startswith(ROOT + os.sep):
        sys.exit(f"refusing to build into {out}: it must be a folder inside the repository")
    if os.path.exists(out):
        # Only replace a folder that looks like an earlier build: nothing in it
        # that this script would not have put there
        expected = {p.split("/")[0] for p in PUBLIC + OPTIONAL}
        unexpected = set(os.listdir(out)) - expected
        if unexpected:
            sys.exit(f"refusing to replace {out}: it holds {sorted(unexpected)}, "
                     "which this script did not make")
        shutil.rmtree(out)
    os.makedirs(out)

    count = size = 0
    for rel in PUBLIC + [p for p in OPTIONAL if os.path.exists(os.path.join(ROOT, p))]:
        src, dst = os.path.join(ROOT, rel), os.path.join(out, rel)
        if not os.path.exists(src):
            sys.exit(f"missing {rel}: run tools/build.py first")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"))
        else:
            shutil.copy2(src, dst)
    for base, _, files in os.walk(out):
        for f in files:
            count += 1
            size += os.path.getsize(os.path.join(base, f))
    print(f"built {os.path.relpath(out, ROOT)}: {count} files, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(*sys.argv[1:2])
