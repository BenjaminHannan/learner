"""BM25 slot memory: SQLite FTS5 over question/answer and correction diary entries; top-3, about 150 tokens, inserted after the system prompt."""
import re
import sqlite3

from .config import MEM_MAX_TOKENS, MEM_TOPK

STOP = set("the a an to of and or for my me i it is in on at with please this that can you your be do".split())


def toks(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def approx_tokens(s):
    return max(1, len(s) // 4)


class SlotMemory:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("create virtual table m using fts5(text, day unindexed, kind unindexed, ref unindexed)")

    def add(self, day, kind, ref, text):
        self.db.execute("insert into m(text, day, kind, ref) values (?,?,?,?)", (text, day, kind, ref))

    def __len__(self):
        return self.db.execute("select count(*) from m").fetchone()[0]

    def search(self, query, k=MEM_TOPK):
        q = " OR ".join(f'"{t}"' for t in dict.fromkeys(toks(query)))
        if not q:
            return []
        return self.db.execute("select text, day, kind, ref, bm25(m) from m where m match ? order by bm25(m) limit ?", (q, k)).fetchall()

    def retrieve(self, query, k=MEM_TOPK, max_tokens=MEM_MAX_TOKENS):
        """Formatted memory lines for the prompt, trimmed to the token budget."""
        lines, used = [], 0
        for text, day, kind, ref, _ in self.search(query, k):
            line = f"- (day {day}) {text}"
            n = approx_tokens(line)
            if used + n > max_tokens:
                line = line[: max(0, (max_tokens - used) * 4)]
                if len(line) < 20:
                    break
            lines.append(line)
            used += approx_tokens(line)
        return lines

    def hit_with_values(self, value_tokens, before_day):
        """Tagger's 'answer already known' check: does any entry from an earlier day contain one of these answer strings (BM25 hit)?"""
        for v in value_tokens:
            q = '"' + v.replace('"', "") + '"'
            try:
                rows = self.db.execute("select day from m where m match ? and day < ?", (q, before_day)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if rows:
                return True
        return False


def entries_from_diary_rows(rows):
    """Rebuild the slot-memory entries (day, kind, ref, text) from diary rows exactly as simulate_days writes them (Q/A and corrections only)."""
    from .tools_mock import parse_reply
    g = {}
    for r in rows:
        g.setdefault(r["req_id"], []).append(r)
    out = []
    for rid, rs in g.items():
        if rid.startswith("fact-"):
            continue
        rs = sorted(rs, key=lambda x: x["turn"])
        req = rs[0]
        refs = req["meta"].get("lookup_refs", [])
        if not refs:
            continue
        ref = refs[0]
        first = rs[1]
        if first["meta"].get("move") == "ASK":
            ans = next((x for x in rs if x["meta"].get("kind") == "answer"), None)
            if ans:
                out.append((req["day"], "qa", ref, f'{ref}: asked "{parse_reply(first["text"])[1]}"; Ben answered: {ans["text"]}'))
        cor = next((x for x in rs if x["meta"].get("kind") == "correction"), None)
        if cor:
            out.append((req["day"], "corr", ref, f"{ref}: Ben corrected me: {cor['text']}"))
    return out


def memory_from_diary(diary_dir, max_day=None):
    from pathlib import Path
    from .config import jl_read
    import re as _re
    mem = SlotMemory()
    files = sorted(Path(diary_dir).glob("day*.jsonl"), key=lambda p: int(_re.findall(r"\d+", p.name)[0]))
    for p in files:
        day = int(_re.findall(r"\d+", p.name)[0])
        if max_day is not None and day > max_day:
            continue
        for e in entries_from_diary_rows(jl_read(p)):
            mem.add(*e)
    return mem
