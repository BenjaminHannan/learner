"""Offline search corpus for the search() tool: Wikipedia summaries of ~150 puzzle/math/algorithm topics (fetched once by `python -m practice.library`,
saved to practice/data/library_wiki.json) plus pydoc text of a few stdlib modules (generated at job time, no payload cost). BM25, top 3 snippets,
at most 1,500 characters in total. No puzzle sites, no answer sites, no ARC or Project Euler pages."""
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
WIKI_PATH = DATA / "library_wiki.json"
MAX_CHARS = 1500
TOPK = 3
PYDOC_MODULES = ["builtins", "math", "itertools", "collections", "re", "fractions", "functools", "heapq"]

TITLES = """Breadth-first search;Depth-first search;Dynamic programming;Modular arithmetic;Flood fill;Symmetry;Prime number;Permutation;Graph coloring;Combination;Binomial coefficient;
Pigeonhole principle;Inclusion-exclusion principle;Greatest common divisor;Least common multiple;Euclidean algorithm;Sieve of Eratosthenes;Fibonacci sequence;Arithmetic progression;
Geometric progression;Triangular number;Square number;Cube (algebra);Factorial;Catalan number;Derangement;Stirling numbers of the second kind;Partition (number theory);
Pascal's triangle;Parity (mathematics);Divisibility rule;Prime factorization;Fundamental theorem of arithmetic;Modular multiplicative inverse;Chinese remainder theorem;Fermat's little theorem;
Euler's totient function;Perfect number;Palindrome;Binary number;Hexadecimal;Decimal;Positional notation;Digit sum;Digital root;Base (exponentiation);Exponentiation;Logarithm;Square root;
Quadratic equation;Linear equation;System of linear equations;Polynomial;Difference engine;Finite difference;Recurrence relation;Linear recurrence with constant coefficients;
Mathematical induction;Proof by contradiction;Boolean algebra;Truth table;Propositional calculus;Logical conjunction;Logical disjunction;Exclusive or;De Morgan's laws;Constraint satisfaction problem;
Backtracking;Brute-force search;Greedy algorithm;Divide-and-conquer algorithm;Recursion;Memoization;Binary search;Linear search;Sorting algorithm;Merge sort;Quicksort;Bubble sort;
Dijkstra's algorithm;A* search algorithm;Shortest path problem;Graph theory;Tree (graph theory);Connected component (graph theory);Adjacency matrix;Adjacency list;Bipartite graph;Eulerian path;
Hamiltonian path;Travelling salesman problem;Maze generation algorithm;Maze-solving algorithm;Flood fill algorithm;Queue (abstract data type);Stack (abstract data type);Priority queue;Hash table;
Set (mathematics);Multiset;Cartesian product;Matrix (mathematics);Transpose;Matrix multiplication;Rotation (mathematics);Reflection (mathematics);Translation (geometry);Scaling (geometry);
Tessellation;Tiling puzzle;Rotational symmetry;Reflection symmetry;Translational symmetry;Pattern;Connected space;Bounding box;Manhattan distance;Euclidean distance;Chebyshev distance;
Cellular automaton;Conway's Game of Life;Run-length encoding;Image segmentation;Mathematical morphology;Connected-component labeling;Pixel;Raster graphics;Color;RGB color model;
Caesar cipher;Substitution cipher;Vigenère cipher;Transposition cipher;ROT13;Atbash;Anagram;Cryptarithm;Sudoku;Magic square;Latin square;Knight's tour;Eight queens puzzle;Tower of Hanoi;
Logic puzzle;Knights and Knaves;Nonogram;Kakuro;KenKen;Lights Out (game);Sliding puzzle;Mastermind (board game);Probability;Expected value;Conditional probability;Combinatorics;
Enumerative combinatorics;Counting;Rule of sum;Rule of product;Stars and bars (combinatorics);Generating function;Sequence;Series (mathematics);Summation;Floor and ceiling functions;Modulo;
Integer;Rational number;Number line;Absolute value;Percentage;Ratio;Average;Median;Mode (statistics);Parity of a permutation;Cycle (graph theory);Path (graph theory);Grid graph;Lattice path;
Python (programming language);String (computer science);Array (data structure);List (abstract data type);Dictionary (data structure)""".replace("\n", "").split(";")
TITLES = [t.strip() for t in TITLES if t.strip()]


def fetch(out=WIKI_PATH):
    import subprocess
    import urllib.parse
    from concurrent.futures import ThreadPoolExecutor

    def one(t):
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(t.replace(" ", "_"), safe="")
        for attempt in range(6):
            r = subprocess.run(["curl", "-sSL", "-f", "-A", "practice1-library/1.0 (research)", url], capture_output=True, text=True)
            if r.returncode == 0:
                break
            time.sleep(2 * (attempt + 1))
        else:
            print("failed:", t, file=sys.stderr)
            return None
        d = json.loads(r.stdout)
        if d.get("type") != "standard" or not d.get("extract"):
            return None
        return {"title": d["title"], "text": d["extract"]}
    with ThreadPoolExecutor(3) as ex:
        docs = [d for d in ex.map(one, TITLES) if d]
    seen, uniq = set(), []
    for d in docs:
        if d["title"] not in seen:
            seen.add(d["title"])
            uniq.append(d)
    Path(out).write_text(json.dumps(uniq, ensure_ascii=False))
    return uniq


def pydoc_docs(modules=PYDOC_MODULES):
    """Documentation of each public function/class of the modules, as one document per object (generated at run time with pydoc)."""
    import importlib
    import inspect
    import pydoc
    docs = []
    for m in modules:
        try:
            mod = importlib.import_module(m)
        except Exception:
            continue
        for name, obj in sorted(vars(mod).items()):
            if name.startswith("_") or not (callable(obj) or inspect.isclass(obj)):
                continue
            if m != "builtins" and getattr(obj, "__module__", m) not in (m, None, "_" + m) and not inspect.isbuiltin(obj):
                continue
            try:
                txt = pydoc.plain(pydoc.render_doc(obj, renderer=pydoc.plaintext))
            except Exception:
                continue
            txt = txt.split("Methods defined here")[0].split("Method resolution order")[0]
            txt = re.sub(r"^Python Library Documentation: ", "", txt)
            txt = re.sub(r"\n[ |]*\n+", "\n", txt).strip()[:900]
            docs.append({"title": f"python {m}.{name}" if m != "builtins" else f"python {name}", "text": txt})
    return docs


def tokenize(s):
    return re.findall(r"[a-z0-9_]+", s.lower())


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.tf = [Counter(tokenize(d["title"] + " " + d["title"] + " " + d["text"])) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(1, len(docs))
        df = Counter(t for c in self.tf for t in c)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - v + 0.5) / (v + 0.5)) for t, v in df.items()}

    def scores(self, query):
        q = tokenize(query)
        out = []
        for i, c in enumerate(self.tf):
            s = 0.0
            for t in q:
                if t in c:
                    f = c[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            out.append(s)
        return out

    def search(self, query, k=TOPK, max_chars=MAX_CHARS):
        sc = self.scores(query)
        order = [i for i in sorted(range(len(sc)), key=lambda i: -sc[i]) if sc[i] > 0][:k]
        if not order:
            return "No results."
        budget = max_chars // len(order)
        parts = []
        for i in order:
            d = self.docs[i]
            t = d["text"].strip()
            head = f"[{d['title']}] "
            t = t[: max(0, budget - len(head) - 4)] + ("..." if len(t) > budget - len(head) else "")
            parts.append(head + t)
        return "\n".join(parts)[:max_chars]


_LIB = {}


def get_library(with_pydoc=True):
    key = bool(with_pydoc)
    if key not in _LIB:
        docs = json.loads(WIKI_PATH.read_text()) if WIKI_PATH.exists() else []
        if with_pydoc:
            docs = docs + pydoc_docs()
        _LIB[key] = BM25(docs)
    return _LIB[key]


def search(query, with_pydoc=True):
    return get_library(with_pydoc).search(query)


if __name__ == "__main__":
    d = fetch()
    print(len(TITLES), "titles ->", len(d), "docs saved to", WIKI_PATH, WIKI_PATH.stat().st_size // 1024, "KB")
