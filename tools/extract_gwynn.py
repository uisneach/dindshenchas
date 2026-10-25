"""Extract poems from Gwynn's Metrical Dindshenchas OCR (archive.org _djvu.txt).

Gwynn prints the Irish text on the left-hand page and the translation on the
right, each followed by a block of manuscript variants. Every page starts with
a running head naming the poem, which is how pages are split and assigned.

Usage: python -I tools/extract_gwynn.py out.json volume.txt "TITLE I" "TITLE II|ALIAS" ...
Output: {title: {"ga": [[line x4], ...], "en": [[line x4], ...], "pages": [first, last],
                 "line_counts": [ga, en]}}
"""
import difflib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio
from ocr_common import clean_spaces, english_ratio, fix_english_verse, fix_irish_verse

ROMAN = re.compile(r"\s+(I{1,3}|IV|V|11|1|Il|IL|lI)\s*$")
APPARATUS = re.compile(r"^\s*\d+[\.,]\s|^\s*[A-Z0-9]{4,}[\.,]?\s*(\d|$)|^\s*[A-Z]{2,}\s*;")
ATTRIBUTION = re.compile(r"\bcecinit\b|\bdixit\b", re.I)


def is_apparatus(line):
    # A variant reading is "lemma] reading"; a "]" closing an editorial "[...]" is text.
    if APPARATUS.search(line):
        return True
    return line.count("]") > line.count("[")



def norm(s):
    s = unicodedata.normalize("NFKD", s.upper())
    return re.sub(r"[^A-Z ]", "", s).strip()


def split_title(t):
    t = re.sub(r"[\d().,:;'’\-]", " ", t).strip()
    m = ROMAN.search(t)
    numeral = ""
    if m:
        numeral = {"11": "II", "1": "I", "Il": "II", "IL": "II", "lI": "II"}.get(m.group(1), m.group(1))
        t = t[: m.start()]
    return norm(t).replace(" ", ""), numeral


def header_of(line):
    """Return the running head text if this line looks like one, else None."""
    s = line.strip()
    if not (3 <= len(s) <= 45):
        return None
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3 or sum(c.isupper() for c in letters) / len(letters) < 0.8:
        return None
    return s


def best_poem(header, titles, threshold=0.8):
    """The target title this running head belongs to, allowing for OCR damage."""
    hb, hn = split_title(header)
    best, score = None, 0.0
    for t in titles:
        for alias in t.split("|"):  # English pages may carry a shortened head
            tb, tn = split_title(alias)
            if hn != tn:
                continue
            r = difflib.SequenceMatcher(None, hb, tb).ratio()
            if r > score:
                best, score = t, r
    return best if score >= threshold else None


def page_range(seen):
    """First and last page from (page index, printed number) pairs.

    Printed numbers are often misread or missing, but consecutive pages differ
    by one, so the most common (number - index) gives the true first page.
    """
    if not seen:
        return None
    offsets = [num - idx for idx, num in seen if num]
    if not offsets:
        return None
    # Ties go to the larger start: misreads usually drop a digit ("19" for "190")
    start = max(set(offsets), key=lambda o: (offsets.count(o), o))
    last_idx = max(idx for idx, _ in seen)
    return [start, start + last_idx]


def pages(lines):
    """Yield (header, page_number, body_lines) for each page."""
    head, num, body = None, None, []
    for line in lines:
        h = header_of(line)
        if h:
            if head is not None:
                yield head, num, body
            m = re.search(r"\d+", h)
            head, num, body = h, int(m.group()) if m else None, []
        elif head is not None:
            body.append(line)
    if head is not None:
        yield head, num, body


def verse_lines(body):
    out = []
    for line in body:
        s = line.strip()
        if not s:
            continue
        if is_apparatus(s):
            break  # variants run to the foot of the page
        if ATTRIBUTION.search(s):
            continue
        # Gwynn numbers every fifth line in the margin; keep it for resyncing.
        m = re.search(r"\s+(\d{1,3})[\-\.]?\s*$", s)
        num = int(m.group(1)) if m else None
        s = re.sub(r"\s+(\d{1,3}[\-\.]?|S\.|\d&)\s*$", "", s)
        out.append((clean_spaces(s), num))
    return out


def resync(lines):
    """Fix OCR line wraps and drops using the printed line numbers."""
    out = []
    for text, num in lines:
        out.append(text)
        if not num or num % 5 or abs(num - len(out)) > 3:
            continue  # absent or misread number
        while len(out) > num:
            # One printed line was split in two: rejoin the shortest fragment
            # (among the last five) with the line before it.
            tail = range(max(1, len(out) - 5), len(out))
            k = min(tail, key=lambda i: len(out[i]))
            out[k - 1] += " " + out.pop(k)
        while len(out) < num:
            out.insert(len(out) - 1, "")  # a dropped line, left blank
    return out


def stanzas(lines):
    return [lines[i:i + 4] for i in range(0, len(lines), 4)]


def extract(text, titles):
    lines = text.splitlines()
    result = {t: {"ga": [], "en": [], "pages": []} for t in titles}
    started = {t: False for t in titles}
    for head, num, body in pages(lines):
        if norm(head).startswith("NOTES"):
            # Commentary pages: stop collecting for any poem already seen
            started = {t: (None if v else v) for t, v in started.items()}
            continue
        t = best_poem(head, titles)
        if t is None or started[t] is None:
            continue
        vl = verse_lines(body)
        if not vl:
            continue
        started[t] = True
        lang = "en" if english_ratio(" ".join(text for text, _ in vl)) >= 0.12 else "ga"
        result[t][lang].extend(vl)
        result[t]["pages"].append((len(result[t]["pages"]), num))
    out = {}
    for t, r in result.items():
        ga, en = resync(r["ga"]), resync(r["en"])
        out[t] = {
            "ga": stanzas([fix_irish_verse(x) for x in ga]),
            "en": stanzas([fix_english_verse(x) for x in en]),
            "pages": page_range(r["pages"]),
            "line_counts": [len(ga), len(en)],
        }
    return out


def main(out_path, src, *titles):
    with open(src, encoding="utf-8") as f:
        text = f.read()
    data = extract(text, titles)
    existing = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
    existing.update(data)
    jsonio.write(out_path, existing)
    for t, r in data.items():
        print(f"{t}: lines ga={r['line_counts'][0]} en={r['line_counts'][1]} pages={r['pages']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
