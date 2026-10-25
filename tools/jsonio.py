"""Write JSON the same readable way everywhere: four-space indents, one value
per line, accented letters kept as they are, a newline at the end.

GeoJSON keeps each [longitude, latitude] pair on one line; otherwise every
number of every outline would get a line of its own.
"""
import json
import re

PAIR = re.compile(r"\[\s+(-?[\d.eE+-]+),\s+(-?[\d.eE+-]+)\s+\]")


def dumps(data, geo=False):
    text = json.dumps(data, ensure_ascii=False, indent=4)
    if geo:
        text = PAIR.sub(r"[\1, \2]", text)
    return text + "\n"


def write(path, data, geo=False):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(data, geo))
