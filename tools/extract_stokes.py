"""Extract items from Stokes' Rennes Dindshenchas (Revue Celtique 15-16) OCR.

Input: archive.org _djvu.txt files for revueceltique15pari and revueceltiqu16pari.
Output: JSON {number: {title, page, item, ga: [...], en: [...], notes: [...]}}
Usage: python -I tools/extract_stokes.py out.json rc15.txt rc16.txt
"""
import difflib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio
from ocr_common import fix_english, fix_irish, is_english, join_lines

HEADING = re.compile(r"^\s*(\d{1,3})\s*\.\s{1,}([A-ZÀ-Ýa-zà-ÿ\[][^.]{1,40})\.\s*$")
# Looser form for OCR-garbled numbers ("GG." for 66, "So." for 80) or none at all
LOOSE_HEADING = re.compile(r"^\s*(?:\S{1,4}\s*[.,]\s+)?([^.]{3,40}?)\.?\]?\s*$")
CONTENTS_LINE = re.compile(r"^\s*\[?[\dilIoOCS ]{1,6}\s+([A-ZÀ-Ý][^,]{2,40}),")
RUNNING_HEAD = re.compile(r"(Rennes\s+Dind|Whitley\s+Stok|Revue\s+Celtique,\s+X)", re.I)
FOOTNOTE = re.compile(r"^\s*\d\s?\.\s")
ITEM_LIKE = re.compile(r"^[\dilIoO ]{2,5}\.\s+[A-ZÀ-Ý][^.]{2,40}\.$")
NOTES_START = re.compile(r"^(Also in|Versified|Edited|Translated|Printed|Cf\.|See )")


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z]", "", s)


def paragraphs(lines):
    buf = []
    for line in lines:
        if line.strip():
            buf.append(line)
        elif buf:
            yield buf
            buf = []
    if buf:
        yield buf


def page_number(line):
    m = re.search(r"(\d[\d ]{0,4})\s*$", line) or re.search(r"^\s*(\d[\d ]{0,4})", line)
    return int(m.group(1).replace(" ", "")) if m else None


def read_contents(lines):
    """Stokes' table of contents (items 1-130, in order) from Revue Celtique 15."""
    start = next(i for i, l in enumerate(lines) if l.strip() == "CONTENTS.")
    titles = {}
    for line in lines[start:]:
        if "SR.  fo.  90" in line:
            break
        m = CONTENTS_LINE.match(line)
        if m and not RUNNING_HEAD.search(line):
            titles[len(titles) + 1] = m.group(1)
    return titles


def heading_number(line, titles, expect):
    """Return the item number if this line is the heading of one of the next items."""
    if len(line.strip()) > 50:
        return None
    m = HEADING.match(line)
    if m and expect <= int(m.group(1)) <= expect + 3 and int(m.group(1)) not in titles:
        return int(m.group(1))
    m = LOOSE_HEADING.match(line)
    if not m:
        return None
    got = norm(m.group(1))
    for n in range(expect, expect + 4):
        want = norm(titles.get(n, ""))
        if want and difflib.SequenceMatcher(None, got, want).ratio() >= 0.75:
            return n
    return None


def split_items(text, start_marker, titles, expect):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if start_marker in l)
    items, cur, page = {}, None, None
    for line in lines[start:]:
        # An instalment ends with "(A suivre.)" and the article with Stokes' signature;
        # other articles follow, so stop collecting until the next heading.
        if "suivre" in line or re.fullmatch(r"\s*Whit\w{2,3}\s+Stok\w{2}\.\s*", line):
            cur = None
            continue
        if RUNNING_HEAD.search(line) and len(line) < 60:
            page = page_number(line) or page
            continue
        n = heading_number(line, titles, expect)
        if n:
            cur = {"n": n, "title": titles.get(n) or HEADING.match(line).group(2).strip(),
                   "page": page, "lines": []}
            items[n] = cur
            expect = n + 1
            continue
        if cur:
            cur["lines"].append(line)
    return items


def classify(item):
    ga, en, notes = [], [], []
    stage = "ga"
    for para in paragraphs(item["lines"]):
        text = join_lines(para)
        if not text or FOOTNOTE.match(text) and len(text) < 200 or text.isdigit():
            continue
        if ITEM_LIKE.match(text):
            break  # the next item's heading, missed because of OCR damage
        # Most items are Irish then English, but the Tara items alternate blocks,
        # so classify each paragraph; short ones keep the language before them.
        if NOTES_START.match(text) and (en or stage == "en"):
            stage = "notes"
        elif stage != "notes" and len(text) >= 60:
            stage = "en" if is_english(text) else "ga"
        target = {"ga": ga, "en": en, "notes": notes}[stage]
        # Re-join a paragraph broken by a page turn
        if target and not target[-1].endswith((".", "!", "?", "’", ":")) and text[:1].islower():
            target[-1] += " " + text
        else:
            target.append(text)
    return {
        "title": fix_irish(item["title"]), "page": item["page"],
        "ga": [fix_irish(p) for p in ga],
        "en": [fix_english(p) for p in en],
        "notes": [fix_english(p) for p in notes],
    }


def main(out, rc15, rc16):
    result, titles, expect = {}, {}, 1
    for path, vol in ((rc15, 15), (rc16, 16)):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if vol == 15:
            titles = read_contents(text.splitlines())
            marker = "SR.  fo.  90"
        else:
            marker = "RENNES    DINDSENCHAS"
            expect = 81  # Revue Celtique 16 resumes at no. 81
        items = split_items(text, marker, titles, expect)
        for n, item in items.items():
            entry = classify(item)
            entry["volume"] = vol
            result.setdefault(str(n), entry)
    jsonio.write(out, result)
    missing = [n for n in range(1, max(map(int, result)) + 1) if str(n) not in result]
    print(f"{len(result)} items; missing: {missing}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
