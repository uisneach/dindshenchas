"""Helpers shared by the OCR extractors."""
import re

# Words common in English but (almost) never in Middle Irish text
EN_WORDS = set("""the of was to his her from which that he she by with were who had son
daughter there this they them their for were when then thence name named called
river hill king queen whence hence it its into after said""".split())

PUNCT_END = tuple('.!?;:»"\')]')


def english_ratio(text):
    words = re.findall(r"[A-Za-z]+", text.lower())
    if not words:
        return 0.0
    return sum(w in EN_WORDS for w in words) / len(words)


def is_english(text, threshold=0.12):
    return english_ratio(text) >= threshold


def clean_spaces(s):
    s = s.replace("—", "—")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ([,;:.!?])", r"\1", s)
    return s.strip()


def join_lines(lines):
    """Join OCR lines into one paragraph, undoing end-of-line hyphenation."""
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if out.endswith("-") and not out.endswith(" -"):
            out = out[:-1] + line
        else:
            out = (out + " " + line) if out else line
    return clean_spaces(out)


# Systematic OCR confusions seen in these scans (English side only)
EN_FIXES = [
    (r"\blier\b", "her"), (r"\bLier\b", "Her"), (r"\bIiands\b", "hands"),
    (r"\bhâve\b", "have"), (r"\bhère\b", "here"), (r"\bwâs\b", "was"),
    (r"\bhiver\b", "inver"), (r"\bcvery\b", "every"), (r"\bevcr\b", "ever"),
    (r"\bnamc\b", "name"), (r"\bthc\b", "the"), (r"\btlie\b", "the"), (r"\bTlie\b", "The"),
    (r"\bwhcn\b", "when"), (r"\bfeU\b", "fell"), (r"\bont\b", "out"), (r"\beves\b", "eyes"),
    (r"\bshewas\b", "she was"), (r"\bthemother\b", "the mother"), (r"\bwhiçh\b", "which"),
    (r"\bAcd\b", "Aed"), (r"\bflecing\b", "fleeing"), (r"«\s*", "‘"), (r"\s*»", "’"),
]


# Revue Celtique was OCR'd as French, which reads Stokes' acute accents on
# Irish vowels as circumflexes; Irish never uses the circumflex.
CIRCUMFLEX = str.maketrans("âêîôûÂÊÎÔÛ", "áéíóúÁÉÍÓÚ")


def fix_english(s):
    for pat, rep in EN_FIXES:
        s = re.sub(pat, rep, s)
    return s.translate(CIRCUMFLEX)


def fix_irish(s):
    # Strip characters that never occur in the printed Irish and are OCR noise
    # from italicised expansions of manuscript contractions.
    s = re.sub(r"[\^\\|]", "", s)
    s = re.sub(r"«\s*", "‘", s)
    s = re.sub(r"\s*»", "’", s)
    return clean_spaces(s).translate(CIRCUMFLEX)


def fix_digits_in_words(s):
    # "B6inde" -> "Bóinde": this OCR reads ó as 6 inside words
    return re.sub(r"(?<=[A-Za-zÀ-ÿ])6|6(?=[a-zà-ÿ])", "ó", s)


def fix_irish_verse(s):
    # Gwynn's Irish text has no numerals once line numbers are stripped,
    # so a lone 6 is the preposition ó and 0 is the vocative O.
    s = fix_digits_in_words(s)
    s = re.sub(r"\b6\b", "ó", s)
    s = re.sub(r"\b0\b", "O", s)
    return s


def fix_english_verse(s):
    s = fix_english(fix_digits_in_words(s))
    s = re.sub(r"\b0\b", "O", s)          # vocative "O prince"
    s = re.sub(r"^1(?=\s|')", "I", s)      # "1 will tell thee"
    return s
