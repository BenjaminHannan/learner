"""Build and submit Message Batches requests for the Practice-1 sealed test set and the Sonnet practice pool.
usage: python -m practice.testgen.gen {test|pool} N [--label L] [--kinds k1,k2] [--seed S]
Raw replies go to practice/data/raw_<label>.json (no key is ever written)."""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from sleep2.askonce.batches import req, run_batch  # noqa: E402
from sleep2.askonce.config import SONNET  # noqa: E402

DATA = ROOT / "practice" / "data"
KINDS = ["grid", "number", "word", "logic", "sequence", "cipher", "ascii_picture"]

THEMES = {
    "test": "lighthouse orchard glacier violin harbor compass saffron tundra lantern mosaic canyon falcon bakery "
            "telescope marsh clocktower velvet comet archive rivet monsoon quartz ferry thistle anvil mirage "
            "pottery sundial caravan ember prairie kayak loom nebula quarry regatta sparrow tapestry volcano "
            "windmill zeppelin almanac beacon cobalt dune estuary fjord gondola hammock igloo juniper kelp".split(),
    "pool": "museum robot bicycle jungle pancake submarine meadow pirate library desert chess rainstorm circus "
            "satellite carousel village tractor bonfire canoe dragon eclipse festival garden hockey island jigsaw "
            "kitchen lagoon market notebook ocean puppet rocket subway tulip umbrella vineyard whistle yacht "
            "zebra attic bridge candle domino engine forest glider harvest".split(),
}

HINTS = {
    "test": {
        "grid": ["gravity: cells fall down until blocked", "recolor each object by its size", "mirror the shape across a diagonal",
                 "draw a line from each dot to the wall", "fill enclosed regions", "keep only the largest object", "count colours and output a bar",
                 "shift each row by its index", "overlay the left half on the right half"],
        "number": ["digit sums and divisibility", "counting lattice paths with obstacles", "modular arithmetic of a big power", "coin or stamp combinations",
                   "age/ratio/work-rate word problem", "base conversion with a twist", "number of divisors or totients", "clock and calendar arithmetic"],
        "word": ["anagram with a constraint", "word ladder shortest length (give the lexicon in the prompt)", "hidden word across a list's initials",
                 "count words in a given passage satisfying a rule", "letter-pattern crossword fragment with a given word list", "spelling transformation rules applied in order"],
        "logic": ["knights and knaves with 4-5 speakers", "seating arrangement at a round table", "who-owns-what grid with 4 people and 3 attributes",
                  "scheduling with precedence clues", "truth-teller / liar / alternator", "ordering of race finishers from clues"],
        "sequence": ["next term of a recurrence with a twist", "n-th term of a self-referential sequence", "sum of a pattern after reindexing",
                     "interleaved two sequences", "differences of differences", "look-and-say variants"],
        "cipher": ["Caesar/shift with a keyword", "Vigenere with a short key given in the prompt", "rail fence", "substitution given by a table", "Atbash plus reversal", "numeric A1Z26 with an offset"],
        "ascii_picture": ["count rectangles made of # characters", "count separate islands of #", "identify which letter shape is drawn", "count triangles of a given orientation",
                          "find the row/column with the most marks", "count enclosed holes"],
    },
    "pool": {
        "grid": ["extend a pattern to the border", "swap two colours and flip", "crop the bounding box of the object", "replicate a small tile into a bigger grid",
                 "draw a frame around the grid", "connect same-coloured dots in a row/column", "count objects and output that many cells", "rotate by 90 degrees and recolour"],
        "number": ["sum of multiples with exclusion", "last digits of a product", "rounds of a tournament / handshakes", "digits of a repunit or factorial",
                   "min/max with constraints in a small optimisation", "gcd/lcm schedule problem", "perimeter-area integer puzzle", "binary operations on bits"],
        "word": ["letters that appear in every word of a list", "caesar-free scramble: unscramble given a list of candidates", "longest word chain", "palindromes in a passage",
                 "vowel/consonant pattern counting", "sort by custom rule and give the k-th"],
        "logic": ["four friends and four pets grid", "grid with 'exactly one statement is true'", "river-crossing minimal moves", "tournament standings from partial results",
                  "colored hats deduction", "floor-by-floor elevator or room-assignment clues"],
        "sequence": ["fibonacci-like with different seeds", "polygonal / triangular number patterns", "digit-wise rule sequences", "Collatz-style step counts",
                     "alternating add/multiply operations", "position of a value in a generated list"],
        "cipher": ["Playfair-free: simple columnar transposition", "ROT with a given shift plus digit mapping", "Morse-like code table given in prompt", "keyword substitution alphabet",
                   "reverse each word then shift", "base-26 style number encoding"],
        "ascii_picture": ["count plus-shaped marks", "count the squares of any size in a grid of #", "which row index has the longest run", "count diagonal lines",
                          "count figures that touch the border", "total filled cells inside a drawn outline"],
    },
}

DIFFS = ["easy", "medium", "hard"]

TEMPLATE = """You are writing ONE puzzle for a benchmark that tests a small language model that can run short Python programs. Another system will verify your answer by running your solver program, so correctness and uniqueness matter more than cleverness.

Kind: {kind}  ({kind_desc})
Difficulty: {difficulty}  (easy = a careful person solves it in under a minute; medium = a few minutes of work or a short program; hard = needs real multi-step reasoning or a short program, but still has one exact answer)
Theme word for flavour (use it in names or setting, loosely): {theme}
Idea hint (optional starting point, you may adapt it): {hint}
Random seed word to vary your choices: {seed}

Requirements:
- The puzzle text in "prompt" must be fully self-contained (include all data, all example grids/lists/pictures, any word lists) and must state the EXACT answer format (for example "Answer with a single integer", "Answer with one lowercase word", or "Answer with the output grid as rows of digits, one row per line, no spaces").
- The answer must be unique and verifiable. Short: an integer, a short string (at most 60 characters), or a grid (at most 10x10, digits 0-9, rows separated by newlines).
- Do not reveal the answer in the prompt. Keep the prompt under 2,000 characters.
- For kind grid: give 2 or 3 input/output example grids that follow one hidden rule (do not state the rule), then a test input; the answer is the test output grid. Write grids as rows of digits with spaces between cells, one row per line.
- For kind ascii_picture: draw the picture in the prompt using plain ASCII characters.
- "solver" is a complete, self-contained Python 3 program using only the standard library that computes the answer from scratch (embed the puzzle data in it) and prints exactly the answer, in the same format as "answer" (grid: rows of digits without spaces, one per line). It must run in under 5 seconds and use no network or files.
- "answer_type" is one of int, str, grid.

Reply with ONLY one JSON object (no code fence, no commentary) with these keys:
{{"kind": "{kind}", "title": "...", "difficulty": "{difficulty}", "prompt": "...", "answer": "...", "answer_type": "int|str|grid", "solver": "..."}}
Think briefly; do not draft the puzzle at length before answering."""

KIND_DESC = {
    "grid": "ARC-style grid transformation puzzle with example pairs and a hidden rule",
    "number": "arithmetic / number theory / counting problem with an integer answer",
    "word": "word puzzle (anagram, word list reasoning, letter patterns) with a short string or integer answer",
    "logic": "deduction puzzle (knights and knaves, grids of clues, ordering) with a short answer",
    "sequence": "find-the-pattern / compute-the-term sequence puzzle",
    "cipher": "decode (or encode) a message with a described cipher; answer is the plaintext or a number",
    "ascii_picture": "count or identify shapes in an ASCII picture",
}


def build(which, n, label, kinds=None, seed=0):
    rng = random.Random(f"{which}-{label}-{seed}")
    kinds = kinds or KINDS
    reqs = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        difficulty = DIFFS[(i // len(kinds)) % 3] if rng.random() < 0.5 else rng.choice(DIFFS)
        theme = rng.choice(THEMES[which])
        hint = rng.choice(HINTS[which][kind])
        sd = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6)) + str(rng.randrange(1000))
        p = TEMPLATE.format(kind=kind, kind_desc=KIND_DESC[kind], difficulty=difficulty, theme=theme, hint=hint, seed=sd)
        reqs.append(req(f"{which}-{label}-{i:03d}-{kind}", SONNET, p, max_tokens=6000))
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["test", "pool"])
    ap.add_argument("n", type=int)
    ap.add_argument("--label", default="b1")
    ap.add_argument("--kinds", default="")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    kinds = [k for k in a.kinds.split(",") if k] or None
    reqs = build(a.which, a.n, a.label, kinds, a.seed)
    out, usage = run_batch(reqs, f"{a.which}-{a.label}", spend_file=DATA / "spend.json")
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"raw_{a.which}_{a.label}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"saved {len(out)} replies")


if __name__ == "__main__":
    main()
