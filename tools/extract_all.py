"""Download the archive.org OCR for every source volume and re-extract all texts.

Usage: python -I tools/extract_all.py <download-dir>
Writes sources/stokes_rennes.json and sources/gwynn_*.json. To add a poem,
add its running-head title (as printed, with "|ALIAS" for a variant head)
to the list for its volume and re-run.
"""
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

STOKES = ["revueceltique15pari", "revueceltiqu16pari"]

GWYNN = {
    # Part III (1913)
    "gwynn_part3": ("toddlectureserie10royauoft", [
        "BOAND I", "BOAND II", "CNOGBA", "NAS", "ATH CLIATH CUALANN|ATH CLIATH",
        "BEND ETAIR I", "BEND ETAIR II", "LOCH GARMAN", "PORT LAIRGE", "SLIAB MISS",
        "LOCH LEIN", "LUIMNECH", "SINANN I", "SINANN II", "RATH CRUACHAN", "ATH LUAIN",
        "LOCH ERNE|LOCH N-ERNE", "CARMUN"]),
    # Todd Lecture Series VII-IX: Poems from the Dindshenchas (1900), Parts I-II
    "gwynn_toronto_v7-9": ("toddlectureserie09royauoft", [
        "BRUG I|BRUG NA BOINDE I", "BRUG II|BRUG NA BOINDE II", "MIDE", "SLIAB BLADMA",
        "MAG LIFE", "AILECH I", "AILECH II",
        "TEMAIR I", "TEMAIR II", "TEMAIR III", "TEMAIR IV", "TEMAIR V"]),
    # A second scan of Parts I-III, used where its OCR is better
    "gwynn_google_v8-10": ("toddlectureseri02acadgoog", [
        "TEMAIR I", "TEMAIR II", "TEMAIR III", "TEMAIR IV", "TEMAIR V",
        "MIDE", "BRUG I", "BRUG II", "SLIAB BLADMA", "MAG LIFE"]),
}


def fetch(ident, dl):
    path = os.path.join(dl, f"{ident}.txt")
    if not os.path.exists(path):
        url = f"https://archive.org/download/{ident}/{ident}_djvu.txt"
        print("downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


def run(script, *args):
    subprocess.run([sys.executable, "-I", os.path.join(TOOLS, script), *args], check=True)


def main(dl):
    os.makedirs(dl, exist_ok=True)
    src = os.path.join(ROOT, "sources")
    run("extract_stokes.py", os.path.join(src, "stokes_rennes.json"), *(fetch(i, dl) for i in STOKES))
    for name, (ident, titles) in GWYNN.items():
        out = os.path.join(src, f"{name}.json")
        if os.path.exists(out):
            os.remove(out)
        run("extract_gwynn.py", out, fetch(ident, dl), *titles)


if __name__ == "__main__":
    main(sys.argv[1])
