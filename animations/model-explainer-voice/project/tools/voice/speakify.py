"""Turn caption-style text into text a speech engine says correctly.
Digits become words, code names get their spoken form, symbols become words.
    python3 tools/voice/speakify.py "In T1SDR, 73.01 beat 6,040 questions."
The same function is used by tts.py. Anything left over (digits, odd symbols) is reported by check_text()."""
import re, sys

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
        "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")]


def int_words(n):
    if n < 0:
        return "minus " + int_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (" " + int_words(n % 100) if n % 100 else "")
    for val, name in SCALES:
        if n >= val:
            rest = n % val
            return int_words(n // val) + " " + name + ((", " if val >= 10 ** 6 else " ") + int_words(rest) if rest else "")
    return str(n)


def ordinal_words(n):
    w = int_words(n)
    irregular = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
    parts = re.split(r"([ -])", w)
    last = parts[-1]
    if last in irregular:
        parts[-1] = irregular[last]
    elif last.endswith("y"):
        parts[-1] = last[:-1] + "ieth"
    else:
        parts[-1] = last + "th"
    return "".join(parts)


def digits_words(s):
    return " ".join(ONES[int(c)] for c in s)


def num_words(tok):
    """'6,040' -> six thousand, forty ; '73.01' -> seventy-three point zero one"""
    t = tok.replace(",", "")
    if "." in t:
        a, b = t.split(".", 1)
        return int_words(int(a or "0")) + " point " + digits_words(b)
    return int_words(int(t))


MONTHS = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
          "Sep": "September", "Sept": "September", "Oct": "October", "Nov": "November", "Dec": "December"}

# fixed spoken forms for names and code words (whole-word, case-sensitive)
LEXICON = [
    (r"SmolLM2-360M", "Smol L L M two, three hundred sixty million"),
    (r"EmbeddingGemma 2", "Embedding Gemma two"),
    (r"EmbeddingGemma", "Embedding Gemma"),
    (r"FineWeb-Edu", "Fine Web Ed"),
    (r"T1SDR", "T one S D R"),
    (r"H1R", "H one R"),
    (r"H1", "H one"),
    (r"G1", "G one"),
    (r"B2V", "B two V"),
    (r"B2", "B two"),
    (r"B3", "B three"),
    (r"TKN", "T K N"),
    (r"TK", "T K"),
    (r"GX", "G X"),
    (r"EGE", "E G E"),
    (r"GPT-2", "G P T two"),
    (r"bAbI", "babby"),
    (r"AdamW", "Adam W"),
    (r"bf16", "B F sixteen"),
    (r"TEACH", "teach"),
    (r"PC", "P C"),
    (r"AI", "A I"),
    (r"GB", "gigabytes"),
    (r"8a-G", "eight A G"),
    (r"8a", "eight A"),
    (r"LoRA", "Laura"),
    (r"RPN", "R P N"),
    (r"in-distribution", "in distribution"),
    (r"GitHub", "GitHub"),
    (r"Gemma", "Gemma"),
]


def speakify(text):
    s = text
    s = s.replace(" ", " ").replace("’", "'").replace("“", "").replace("”", "").replace('"', "")
    s = s.replace("‑", "-").replace("‐", "-").replace("−", "-")  # non-breaking hyphen, minus sign
    # parentheses become commas
    s = re.sub(r"\s*\(([^)]*)\)", r", \1,", s)
    s = re.sub(r",\s*,", ",", s)
    s = re.sub(r",\s*([.;:!?])", r"\1", s)
    # months
    s = re.sub(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.? (\d{1,2})\b", lambda m: f"{MONTHS[m.group(1)]} {ordinal_words(int(m.group(2)))}", s)
    # exponent forms like 1e-3
    s = re.sub(r"\b(\d+(?:\.\d+)?)e-(\d+)\b", lambda m: f"{num_words(m.group(1))} e minus {num_words(m.group(2))}", s)
    # code names and fixed phrases
    for pat, rep in LEXICON:
        s = re.sub(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z])", rep, s)
    # things like 3M, 100M, 373.1M, 25M ; 1.2-billion-number ; 350-million-number ; 3-million-number ; 100M-thinker
    s = re.sub(r"(?<![\w.])(\d+(?:\.\d+)?)M(?![A-Za-z0-9])", lambda m: num_words(m.group(1)) + " million", s)
    s = re.sub(r"(\d+(?:\.\d+)?)-(million|billion|thousand)\b", lambda m: num_words(m.group(1)) + " " + m.group(2), s)
    # signs
    s = re.sub(r"(?<![\w])\+(?=\d)", "plus ", s)
    s = re.sub(r"(?<![\w])-(?=\d)", "minus ", s)
    s = s.replace("×", " times ").replace("÷", " divided by ").replace("→", ", ").replace("—", ", ").replace("–", " to ")
    s = re.sub(r"\s=\s", " equals ", s)
    s = s.replace("%", " percent")
    s = re.sub(r"(\d)\s*x\s*(\d)", r"\1 times \2", s)
    # numbers (with thousands commas and decimals)
    s = re.sub(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", lambda m: num_words(m.group(0)), s)
    # word-number hyphen forms: pooled-5 -> pooled five handled by number rule ("pooled-five"); make it a space
    s = re.sub(r"\b(pooled|chain|Pooled|Chain|always|Always)-(\w)", r"\1 \2", s)
    s = s.replace(" vs ", " versus ").replace(" vs. ", " versus ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    return s


def check_text(s):
    """Problems left after speakify: digits or odd characters the engine may mangle."""
    probs = []
    if re.search(r"\d", s):
        probs.append("digit left: " + ", ".join(re.findall(r"\S*\d\S*", s)[:5]))
    odd = set(re.findall(r"[^A-Za-z0-9\s.,;:!?'\-]", s))
    if odd:
        probs.append("odd characters: " + "".join(sorted(odd)))
    caps = re.findall(r"\b[A-Z]{2,}\b", s)
    if caps:
        probs.append("all-caps word(s): " + ", ".join(sorted(set(caps))))
    return probs


if __name__ == "__main__":
    for a in sys.argv[1:] or ["In T1SDR, 73.01 beat 6,040 questions (called parameters) on Oct 9, +0.49 for 3M at 1e-3: 24,000 × 256 = 6,144,000."]:
        print(speakify(a))
        print(check_text(speakify(a)))
