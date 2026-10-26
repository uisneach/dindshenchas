"""Draw the site icon: Ireland in ink with Uisneach marked in red.

The outline comes from data/ireland.geojson, so the icon matches the site's map.
Two versions:
  favicon     no background; a fine white outline keeps the island visible on
              dark tab bars, so the island can be drawn larger
  home screen the island on a paper tile, because phones fill transparent
              areas of home-screen icons with black or white anyway
Writes, at the repository root:
  favicon.svg            the main favicon (modern browsers)
  favicon.ico            16, 32 and 48 px, for browsers that ask for /favicon.ico
  apple-touch-icon.png   180 px, for iPhone and iPad home screens
  icon-192.png, icon-512.png   for site.webmanifest (Android home screens)

Build-only dependency: Pillow. Run without -I so user-installed packages load:
    python -E -P tools/make_icons.py
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_outline import simplify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER, INK, RED, WHITE = "#f4f3ef", "#1c1b19", "#a51d1d", "#ffffff"
UISNEACH = (-7.562, 53.49)  # the navel of Ireland, near the middle of the island
BOX = 32                    # the icon is designed on a 32-unit square
DOT, DOT_EDGE, CORNER = 2.3, 1.0, 4

# The island's longer side in those units, and its edge, for each version
FAVICON = {"island": 29, "outline": 1.2, "edge": WHITE, "tile": None}  # half the outline shows
HOME = {"island": 26, "outline": 0, "edge": PAPER, "tile": PAPER}


def outline(island):
    """The two mainland rings (island outline), projected into the 32-unit square."""
    with open(os.path.join(ROOT, "data", "ireland.geojson"), encoding="utf-8") as f:
        geo = json.load(f)
    rings = sorted((poly[0] for ft in geo["features"] for poly in ft["geometry"]["coordinates"]),
                   key=len, reverse=True)[:2]  # Ireland and Northern Ireland; offshore islands drop out
    k = math.cos(math.radians(53.4))
    pts = [(x * k, -y) for r in rings for x, y in r]
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    s = island / max(maxx - minx, maxy - miny)
    ox, oy = (BOX - (maxx - minx) * s) / 2, (BOX - (maxy - miny) * s) / 2

    def project(lon, lat):
        return ((lon * k - minx) * s + ox, (-lat - miny) * s + oy)

    return [[project(*p) for p in r] for r in rings], project(*UISNEACH)


def svg(style):
    rings, dot = outline(style["island"])
    path = " ".join("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in simplify(r, 0.35)) + "Z"
                    for r in rings)
    tile = (f'<rect width="{BOX}" height="{BOX}" rx="{CORNER}" fill="{style["tile"]}"/>'
            if style["tile"] else "")
    # paint-order puts the stroke behind the fill, so only its outer half shows
    edge = (f' stroke="{style["edge"]}" stroke-width="{style["outline"]}" '
            f'stroke-linejoin="round" paint-order="stroke"' if style["outline"] else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BOX} {BOX}">{tile}'
            f'<path d="{path}" fill="{INK}"{edge}/>'
            f'<circle cx="{dot[0]:.1f}" cy="{dot[1]:.1f}" r="{DOT}" fill="{RED}" '
            f'stroke="{style["edge"]}" stroke-width="{DOT_EDGE}"/></svg>\n')


def png(style, size, rounded=True):
    """Draw large and scale down, which smooths the edges."""
    rings, dot = outline(style["island"])
    big = size * 8
    u = big / BOX
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if style["tile"] and rounded:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=CORNER * u, fill=style["tile"])
    elif style["tile"]:  # iOS rounds home-screen icons itself, and wants them square
        d.rectangle((0, 0, big - 1, big - 1), fill=style["tile"])
    polys = [[(x * u, y * u) for x, y in simplify(r, 0.08)] for r in rings]
    if style["outline"]:
        for p in polys:  # the outline first, then the island over it
            d.line(p + p[:1], fill=style["edge"], width=round(style["outline"] * u), joint="curve")
    for p in polys:
        d.polygon(p, fill=INK)
    x, y = dot[0] * u, dot[1] * u
    rr = (DOT + DOT_EDGE / 2) * u
    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=style["edge"])
    rr = (DOT - DOT_EDGE / 2) * u
    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=RED)
    return img.resize((size, size), Image.LANCZOS)


def main():
    with open(os.path.join(ROOT, "favicon.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg(FAVICON))
    # Each .ico size drawn separately, so the small ones are not just shrunk copies
    ico = [png(FAVICON, s) for s in (16, 32, 48)]
    ico[-1].save(os.path.join(ROOT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)],
                 append_images=ico[:-1])
    png(HOME, 180, rounded=False).convert("RGB").save(os.path.join(ROOT, "apple-touch-icon.png"),
                                                      optimize=True)
    for size in (192, 512):
        png(HOME, size).save(os.path.join(ROOT, f"icon-{size}.png"), optimize=True)
    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        print(f"{name:22} {os.path.getsize(os.path.join(ROOT, name)) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
