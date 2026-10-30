"""Scout: a second agent that runs beside the Practice-1M agents and hunts the web for NEW puzzles that come with an official answer.
  ~/learner-ops/.venv/bin/python -m practice.scout [--out ~/learner-ops/practice1m/scout] [--url http://127.0.0.1:8089] [--until 10:30Z] [--max-episodes 400]
It talks to the SAME already-running mlx_lm.server as mac_run (ONE extra stream, concurrency 1) and never starts or stops it. Server down -> sleep and retry;
~/learner-ops/PAUSE_OTHERS present -> wait. Tools: python, search, fetch (through practice/web.py: test100 shingle block + answer-site domain list), save, done.
`save` accepts a find only if it passes: JSON shape, no 12-word shingle shared with a sealed test100 puzzle, no near-duplicate (8-gram Jaccard > 0.5) of any
practice / test / sibling puzzle or earlier find, and the answer string appears in text FETCHED from answer_url (or source_url) in the same episode (the fetched text's
sha256 is logged). That text match is the only check the scout can make, so every find is written with status "unverified"; practice/scout_verify.py is the later check.
Output (append-only, resume-safe): finds.jsonl, scout.log, episodes.jsonl (transcripts), stats.json. These finds are NOT used in tonight's Practice-1M arms."""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import tools as T
from .gen import OpenAIBackend, _get_json, _post_json
from .grade import normalize
from .harness import cut_reply, render
from .web import PAGE_CHARS, Web, shingle_hashes, words

HERE = Path(__file__).resolve().parent
PDATA = HERE / "data"
OPS = Path(os.path.expanduser("~/learner-ops"))
MAX_TURNS = 8
MAX_NEW, MAX_CTX = 512, 4096
JACCARD_MAX = 0.5
MAXP, MINP, MAXA = 3000, 30, 200
DEFAULT_OUT = "~/learner-ops/practice1m/scout"

TOPICS = [
    "knights and knaves", "cryptarithm (letters stand for digits)", "nonogram (small, 5x5 or 10x10)", "kakuro (small)", "river crossing", "weighing coins on a balance",
    "number sequence (next term)", "word ladder", "anagram", "cipher or code to decode", "combinatorics counting", "probability", "geometry with an integer answer",
    "chess mate-in-one (written as text)", "magic square", "sudoku-style (small grid)", "logic grid puzzle (who owns what)", "age problem", "clock and calendar problem",
    "digit puzzle (find the number)", "number theory (remainders, divisors)", "pattern in a grid of digits", "path counting on a grid", "Tower of Hanoi or move counting",
    "hat puzzle", "truth-teller / liar riddle", "water jug puzzle", "sum of a series", "modular arithmetic", "prime numbers", "base conversion or binary puzzle",
    "matchstick puzzle", "tiling or domino counting", "round-robin tournament counting", "median / mean / average problem", "work-rate or speed problem",
    "Project Euler style problem (number 101 or higher)", "math competition problem with a short integer answer (AMC, AIME, olympiad)", "Rosetta-style programming riddle with a numeric result",
    "lateral thinking riddle with a one-word answer",
]

SYSTEM = """You are a scout. Your job: find puzzles on the web that come with an official answer or solution page, copy the puzzle and its answer, and save them.
You may use tools. Each turn, reply with exactly ONE tool call and nothing after it: the tool's name as a tag around its input.
Examples:
<search>logic puzzle with answer page</search>
<fetch>https://example.com/puzzle 3000</fetch>
Tools:
- search: web search (top 5 results: title, URL, snippet). Input is a short query. Pages that could reveal other puzzles' answers are withheld.
- fetch: download one web page as plain text (3000 characters at a time). Input is a full http(s) URL, optionally followed by a character offset to read further (example: https://example.com/p 3000).
- python: run Python 3 code (10 seconds, no internet). Use print() to see results.
- save: store one find. Input is JSON: {"title": "...", "prompt": "...", "answer": "...", "answer_type": "int", "source_url": "https://...", "answer_url": "https://..."}
  prompt = the puzzle statement copied from the page, complete enough to solve on its own. answer = only the final answer. answer_type is int (an integer), str (a short word or phrase)
  or grid (rows of digits, one per line). source_url = page with the puzzle; answer_url = page where the answer is shown (may be the same page). You must have fetched the page
  that shows the answer in this episode, and the answer must appear in its text, or the save is rejected.
- done: end the episode. Input is empty.
You have at most __N__ turns. Do not make up puzzles or answers. Copy them from the page."""
SYSTEM = SYSTEM.replace("__N__", str(MAX_TURNS))

NUDGE = "Reply with exactly one tool call: the tool name as a tag around its input, for example <search>logic puzzle with answer</search>. Tools: search, fetch, python, save or done."
SCOUT_TOOLS = ("python", "search", "fetch", "save", "done")


def user_prompt(topic):
    return (f"Topic for this episode: {topic}.\nFind a puzzle of this kind (or a close one) on a puzzle site, puzzle archive or problem set whose page, or a linked solution page, "
            f"gives the official answer. Suggested first search: \"{topic} puzzle with answer\". Then fetch the page, copy the puzzle and the answer, and call save.")


# ---------------------------------------------------------------- small io helpers
def jl(path):
    out = []
    if Path(path).exists():
        for l in open(path, encoding="utf-8"):
            if l.strip():
                try:
                    out.append(json.loads(l))
                except ValueError:
                    pass  # a torn last line from a killed run
    return out


def jl_append(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()


def jdump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    Path(tmp).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    os.replace(tmp, path)


def sha(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def parse_until(s, now=None):
    """'10:30Z' / '10:30' -> the next such UTC time after `now`; an ISO datetime ('2026-10-26T10:30Z') is taken as written. -> epoch seconds."""
    now = now or datetime.now(timezone.utc)
    s = s.strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*Z?", s, re.I)
    if m:
        t = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        return t.timestamp()
    d = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def canon_url(u):
    p = urllib.parse.urlparse(urllib.parse.urldefrag(u.strip())[0])
    return f"{p.scheme.lower()}://{(p.netloc or '').lower()}{p.path.rstrip('/')}" + (("?" + p.query) if p.query else "")


# ---------------------------------------------------------------- checks used by `save` (and re-used by scout_verify)
def ngram_set(text, n=8):
    w = words(text)
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


class Dedup:
    """8-gram Jaccard near-duplicate index over practice / test / sibling puzzles and earlier scout finds."""

    def __init__(self):
        self.items = []  # (id, set)

    def add(self, pid, prompt):
        self.items.append((pid, ngram_set(prompt)))

    def nearest(self, prompt):
        s = ngram_set(prompt)
        best = (0.0, None)
        for pid, t in self.items:
            j = jaccard(s, t)
            if j > best[0]:
                best = (j, pid)
        return best


def load_reference(data_dir=PDATA):
    """-> (test_rows, practice_rows, dedup). practice_rows = practice + sonnet + pe pools (for the web guard); dedup also holds test100 and sibling60."""
    d = Path(data_dir)
    test = jl(d / "test100.jsonl")
    practice = jl(d / "practice_pool.jsonl") + jl(d / "sonnet_pool.jsonl") + jl(d / "pe_pool.jsonl")
    sib = jl(d / "sibling60.jsonl")
    dd = Dedup()
    for r in test + practice + sib:
        dd.add(r.get("id", "?"), str(r.get("prompt", "")))
    return test, practice, dd


def answer_in_text(answer, answer_type, text):
    """Does the answer string appear in the page text? int: as a whole number (commas ignored); str: as whole words; grid: rows, whitespace ignored."""
    if answer_type == "int":
        n = normalize(answer, "int")
        if n is None:
            return False
        t = re.sub(r"(?<=\d)[,  ](?=\d{3}\b)", "", text.replace("−", "-"))
        return re.search(r"(?<![\d\w.])" + re.escape(str(n)) + r"(?![\d\w]|\.\d)", t) is not None
    if answer_type == "str":
        a = " ".join(words(str(answer)))
        return bool(a) and (" " + a + " ") in (" " + " ".join(words(text)) + " ")
    if answer_type == "grid":
        rows = normalize(answer, "grid")
        if not rows:
            return False
        return "".join(rows) in re.sub(r"[\s,\[\]]", "", text)
    return False


def check_shape(o):
    """-> (clean record or None, reason). Shape and form only (no web, no dedup)."""
    if not isinstance(o, dict):
        return None, "bad_json"
    for k in ("title", "prompt", "answer", "answer_type", "source_url", "answer_url"):
        if o.get(k) in (None, ""):
            if k == "answer_url" and o.get("source_url"):
                o["answer_url"] = o["source_url"]
                continue
            return None, "missing_" + k
    r = {k: str(o[k]).strip() for k in ("title", "prompt", "answer", "answer_type", "source_url", "answer_url")}
    at = r["answer_type"].lower()
    if at not in ("int", "str", "grid"):
        return None, "answer_type"
    r["answer_type"] = at
    if not (MINP <= len(r["prompt"]) <= MAXP):
        return None, "prompt_length"
    if not r["answer"] or len(r["answer"]) > MAXA:
        return None, "answer_length"
    if not all(re.match(r"https?://", r[k]) for k in ("source_url", "answer_url")):
        return None, "bad_url"
    if at == "int" and normalize(r["answer"], "int") is None:
        return None, "int_form"
    if at == "grid":
        rows = normalize(r["answer"], "grid")
        if not rows or len(rows) > 12 or any(not x.isdigit() or len(x) > 12 for x in rows) or len({len(x) for x in rows}) != 1:
            return None, "grid_form"
    if len(r["answer"]) > 2 and r["answer"].lower() in r["prompt"].lower():
        return None, "answer_in_prompt"
    return r, "ok"


def parse_save_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-z]*\n?|\n?```$", "", t).strip()
    try:
        return json.loads(t)
    except ValueError:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                return None
    return None


def parse_scout_call(text):
    c = T.raw_call(text, SCOUT_TOOLS + ("answer",))
    if c:
        name, inp = c
        name = "done" if name == "answer" else name
        if name == "python":
            f = T._FENCE_RE.search(inp)
            inp = f.group(1) if f else inp
        return name, inp
    f = T._FENCE_RE.search(text)
    return ("python", f.group(1)) if f else None


class StopScout(Exception):
    pass


class Scout:
    def __init__(self, a, post=None, get=None, probe=None, sleep=time.sleep, now=time.time, ops=OPS, data_dir=PDATA, bos="", strip_bos=False, model="default_model"):
        self.a, self.sleep, self.now, self.ops = a, sleep, now, Path(ops)
        self.out = Path(os.path.expanduser(a.out))
        self.out.mkdir(parents=True, exist_ok=True)
        self.f_finds, self.f_log, self.f_eps, self.f_stats = (self.out / n for n in ("finds.jsonl", "scout.log", "episodes.jsonl", "stats.json"))
        self.until = a.until_ts
        self.probe = probe or (lambda: _get_json(a.url.rstrip("/") + "/v1/models", 3))
        self.bos = bos
        test, practice, self.dedup = load_reference(data_dir)
        self.web = Web()
        self.web.configure(True, test, practice, get=get)
        self.finds = jl(self.f_finds)
        for r in self.finds:
            self.dedup.add(r.get("id", "?"), r.get("prompt", ""))
        self.stats = {"episodes": 0, "saves": 0, "save_attempts": 0, "rejects": {}, "tokens": {"completion": 0, "prompt": 0}, "searches": 0, "fetches": 0,
                      "blocked": 0, "turns": 0, "server_waits": 0, "pause_waits": 0}
        if self.f_stats.exists():
            try:
                old = json.loads(self.f_stats.read_text())
                for k, v in old.items():
                    self.stats[k] = v
            except ValueError:
                pass
        self.stats["saves"] = max(self.stats.get("saves", 0), len(self.finds))
        self.last_err = None
        self._waiting = None
        self.backend = OpenAIBackend(a.url, model, workers=1, strip_prefix=bos if strip_bos else "", retries=0, post=self._post_wrap(post or _post_json), log=self.log,
                                     gate=self.wait_ready)

    # ------------------------------------------------------------ plumbing
    def log(self, msg):
        line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
        try:
            with open(self.f_log, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        if not self.a.quiet:
            print(line, flush=True)

    def _post_wrap(self, post):
        def f(url, body, timeout):
            try:
                r = post(url, body, timeout)
            except Exception as e:  # noqa: BLE001
                self.last_err = e
                raise
            self.stats["tokens"]["prompt"] += int((r.get("usage") or {}).get("prompt_tokens") or 0)
            return r
        return f

    def dump_stats(self):
        self.stats["tokens"]["completion"] = self.stats["tokens"].get("completion", 0)
        jdump(self.f_stats, self.stats)

    def past_deadline(self):
        return self.now() >= self.until

    def paused(self):
        return (self.ops / "PAUSE_OTHERS").exists()

    def wait_ready(self):
        """Called before every request: block while PAUSE_OTHERS exists or the server does not answer. Raises StopScout at the deadline."""
        while True:
            if self.past_deadline():
                raise StopScout("deadline")
            if self.paused():
                if self._waiting != "pause":
                    self._waiting = "pause"
                    self.stats["pause_waits"] += 1
                    self.log("PAUSE_OTHERS present: waiting")
                self.sleep(self.a.poll_s)
                continue
            try:
                self.probe()
            except Exception as e:  # noqa: BLE001
                if self._waiting != "server":
                    self._waiting = "server"
                    self.stats["server_waits"] += 1
                    self.log(f"server not answering ({type(e).__name__}); waiting")
                self.sleep(self.a.poll_s)
                continue
            if self._waiting:
                self.log(f"resuming after {self._waiting} wait")
                self._waiting = None
            return

    def generate(self, prompt, seed):
        """-> (text, ok). ok False = the request failed (server error); the caller retries the turn."""
        self.last_err = None
        before = self.backend.completion_tokens
        out = self.backend.generate([prompt], MAX_NEW, self.a.temperature, seed)[0]
        self.stats["tokens"]["completion"] += self.backend.completion_tokens - before
        return out, self.last_err is None

    # ------------------------------------------------------------ tools
    def do_fetch(self, inp, cache):
        parts = inp.strip().split()
        if not parts:
            return "fetch: input must be a full http(s) URL."
        url, off = parts[0], 0
        if len(parts) > 1 and parts[1].isdigit():
            off = int(parts[1])
        ent = cache.get(canon_url(url))
        if ent is None:
            self.stats["fetches"] += 1
            text, final, msg = self.web.fetch_text(url)
            if text is None:
                self.stats["blocked"] += "blocked" in (msg or "")
                self.log(f"fetch {url[:120]} -> {msg}")
                return msg
            ent = {"text": text, "hash": sha(text), "final": final, "url": url}
            cache[canon_url(url)] = ent
            cache[canon_url(final)] = ent
            self.log(f"fetch {url[:120]} final={final[:120]} chars={len(text)} sha256={ent['hash']}")
        text = ent["text"]
        if not text.strip():
            return "[empty page]"
        if off >= len(text):
            return f"[end of page: it has {len(text)} characters]"
        chunk = text[off:off + PAGE_CHARS]
        tail = f"\n[characters {off}-{off + len(chunk)} of {len(text)}; to read on: {url} {off + len(chunk)}]" if off + len(chunk) < len(text) else "\n[end of page]"
        return chunk + tail

    def do_search(self, inp):
        self.stats["searches"] += 1
        obs = self.web.search(inp)
        self.stats["blocked"] += sum(1 for e in self.web.end() if e.get("status") == "blocked")
        self.web.begin()
        self.log(f"search {inp.strip()[:100]!r}")
        return obs

    def reject(self, reason, why=""):
        self.stats["rejects"][reason] = self.stats["rejects"].get(reason, 0) + 1
        self.log(f"REJECT {reason} {why}".strip())
        self.dump_stats()
        return f"save rejected: {reason}. {why}".strip()

    def do_save(self, inp, cache, ep, topic):
        self.stats["save_attempts"] += 1
        rec, why = check_shape(parse_save_json(inp) if inp.strip() else None)
        if rec is None:
            return self.reject(why, "Fix the JSON fields and try again." if why != "answer_in_prompt" else "The prompt must not contain the answer.")
        if self.web.guard.sh and shingle_hashes(rec["prompt"]) & self.web.guard.sh:
            return self.reject("test_overlap", "This puzzle cannot be used. Find a different one.")
        j, other = self.dedup.nearest(rec["prompt"])
        if j > JACCARD_MAX:
            return self.reject("duplicate", f"(near-duplicate of {other}, Jaccard {j:.2f}). Find a different puzzle.")
        pages = []
        for k in ("answer_url", "source_url"):
            ent = cache.get(canon_url(rec[k]))
            if ent is not None and ent not in pages:
                pages.append(ent)
        if not pages:
            return self.reject("page_not_fetched", "Fetch the page that shows the answer first (the answer_url), then save.")
        hit = next((p for p in pages if answer_in_text(rec["answer"], rec["answer_type"], p["text"])), None)
        if hit is None:
            return self.reject("answer_not_in_page", "The answer does not appear in the fetched text of answer_url/source_url. Copy the answer exactly as the page shows it.")
        pw = ngram_set(rec["prompt"], 4)
        src = cache.get(canon_url(rec["source_url"]))
        in_src = round(len(pw & ngram_set(src["text"], 4)) / max(1, len(pw)), 3) if src else None
        rec.update({"id": "scout-" + sha(rec["prompt"])[:10], "kind": "scout", "source": "scout", "topic": topic, "episode": ep, "status": "unverified", "text_match": True,
                    "weak_match": len(re.sub(r"\s", "", rec["answer"])) <= 2, "answer_page_sha256": hit["hash"], "source_page_sha256": src["hash"] if src else None,
                    "prompt_in_source": in_src, "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        jl_append(self.f_finds, rec)
        self.finds.append(rec)
        self.dedup.add(rec["id"], rec["prompt"])
        self.stats["saves"] += 1
        self.log(f"SAVED {rec['id']} [{topic}] {rec['title'][:60]!r} answer={rec['answer'][:40]!r} answer_sha256={hit['hash']} prompt_in_source={in_src}")
        self.dump_stats()
        return f"saved ({rec['id']}). You may look for another puzzle or call done."

    # ------------------------------------------------------------ episode
    @staticmethod
    def _squeeze(msgs):
        """Keep the context under the cap by cutting the oldest tool outputs to 200 characters."""
        limit = (MAX_CTX - MAX_NEW - 150) * 3
        for m in msgs[2:]:
            if sum(len(x["content"]) for x in msgs) <= limit:
                return True
            if m["role"] == "user" and m["content"].startswith("Tool output") and len(m["content"]) > 260:
                m["content"] = m["content"][:200] + "\n[cut to save space]"
        return sum(len(x["content"]) for x in msgs) <= limit

    def episode(self, ep):
        topic = TOPICS[ep % len(TOPICS)]
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_prompt(topic)}]
        cache, turns, errs, saves0, end = {}, 0, 0, self.stats["saves"], "max_turns"
        self.web.begin()
        self.log(f"episode {ep} topic={topic!r}")
        while turns < MAX_TURNS:
            if not self._squeeze(msgs):
                end = "context_cap"
                break
            out, ok = self.generate(render(msgs, True, self.bos), ep * 1000 + turns + errs * 17)
            if not ok:
                errs += 1
                if errs > 3:
                    end = "server_error"
                    break
                continue  # wait_ready (gate) blocks while the server is down, then the same turn is retried
            errs = 0
            turns += 1
            self.stats["turns"] += 1
            out = cut_reply(out.strip("\n") if out.strip() else out)
            msgs.append({"role": "assistant", "content": out})
            call = parse_scout_call(out)
            if call is None:
                msgs.append({"role": "user", "content": NUDGE})
                continue
            name, inp = call
            if name == "done":
                end = "done"
                break
            if name == "python":
                obs = T.run_python(inp)
            elif name == "search":
                obs = self.do_search(inp)
            elif name == "fetch":
                obs = self.do_fetch(inp, cache)
            else:
                obs = self.do_save(inp, cache, ep, topic)
            left = MAX_TURNS - turns
            msgs.append({"role": "user", "content": f"Tool output ({name}):\n{obs}" + (f"\n({left} turns left)" if left <= 2 else "")})
        self.web.end()
        self.stats["episodes"] = ep + 1
        jl_append(self.f_eps, {"episode": ep, "topic": topic, "end": end, "turns": turns, "saves": self.stats["saves"] - saves0, "messages": msgs,
                               "fetched": [{"url": e["url"], "sha256": e["hash"]} for e in {id(v): v for v in cache.values()}.values()]})
        self.log(f"episode {ep} end={end} turns={turns} saves={self.stats['saves'] - saves0} total_saves={self.stats['saves']}")
        self.dump_stats()

    def run(self):
        self.log(f"scout start: url={self.a.url} until={datetime.fromtimestamp(self.until, timezone.utc).isoformat()} max_episodes={self.a.max_episodes} "
                 f"resume episodes={self.stats['episodes']} finds={len(self.finds)}")
        try:
            while self.stats["episodes"] < self.a.max_episodes and not self.past_deadline():
                self.wait_ready()
                self.episode(self.stats["episodes"])
        except StopScout as e:
            self.log(f"stopping: {e}")
        self.log(f"scout end: episodes={self.stats['episodes']} saves={self.stats['saves']} rejects={self.stats['rejects']}")
        self.dump_stats()
        return 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--url", default="http://127.0.0.1:8089", help="the running mlx_lm.server (the same one mac_run uses)")
    ap.add_argument("--port", type=int, default=None, help="shortcut for --url http://127.0.0.1:PORT")
    ap.add_argument("--model", default=None, help="model path/name sent in requests (default: the K2 q4 under ~/learner-ops/models if present, else default_model)")
    ap.add_argument("--until", default="10:30Z", help="hard stop, UTC: HH:MM[Z] (next occurrence) or an ISO datetime")
    ap.add_argument("--max-episodes", type=int, default=400)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--poll-s", type=int, default=30)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if a.port:
        a.url = f"http://127.0.0.1:{a.port}"
    a.until_ts = parse_until(a.until)
    return a


def locate_model(a):
    if a.model:
        return str(Path(os.path.expanduser(a.model)))
    for d in sorted((OPS / "models").glob("*")):
        if (d / "config.json").exists() and re.search(r"k2", d.name, re.I) and re.search(r"4bit|q4", d.name, re.I):
            return str(d)
    return "default_model"


def bos_of(model):
    """(bos text, strip it from prompts?) exactly as mac_run.load_tok decides, or ('', False) when no tokenizer can be loaded."""
    if not os.path.isdir(model):
        return "", False
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        bos = tok.bos_token or ""
        ids = tok("a", add_special_tokens=True).input_ids
        return bos, bool(bos and tok.bos_token_id is not None and ids and ids[0] == tok.bos_token_id)
    except Exception:  # noqa: BLE001
        return "", False


def main(argv=None):
    a = parse_args(argv)
    model = locate_model(a)
    bos, strip = bos_of(model)
    random.seed(0)
    return Scout(a, bos=bos, strip_bos=strip, model=model).run()


if __name__ == "__main__":
    sys.exit(main())
