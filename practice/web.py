"""Live web tools for Practice-1M (Mac only; off unless enabled): search(query) via DuckDuckGo HTML, fetch(url), and the fairness filters.
Every search result and page passes `Guard.check` before the model sees it:
  (a) a 12-word shingle (lowercased, punctuation stripped) shared with any sealed test100 prompt or answer blocks it. Only HASHED shingles are kept;
  (b) a domain block list (puzzle / answer / solution sites), and any page that contains a practice puzzle's stored answer (>= 3 chars) together with
      that puzzle's title, id, or the start of its prompt.
Every call is logged as an event {tool, query/url, status: allowed|blocked, why}; the harness stores the events on the try record."""
import hashlib
import html
import re
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SHINGLE_N = 12
PAGE_CHARS = 3000
FETCH_TIMEOUT = 10
MAX_BYTES = 1_500_000
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"

BLOCK_HOSTS = ("raw.githubusercontent.com", "arcprize.org", "kaggle.com", "huggingface.co", "mathblog.dk", "stephan-brumme.com")
OK_EULER_HOSTS = ("projecteuler.net",)  # the problem statements themselves carry no answers


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _h(ws):
    return int.from_bytes(hashlib.sha1(" ".join(ws).encode()).digest()[:8], "big")


def shingle_hashes(text, n=SHINGLE_N):
    ws = words(text)
    return {_h(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def host_blocked(url):
    p = urllib.parse.urlparse(url if "//" in url else "//" + url)
    host = (p.hostname or "").lower().rstrip(".")
    path = (p.path or "").lower()
    def on(d):
        return host == d or host.endswith("." + d)
    for d in BLOCK_HOSTS:
        if on(d):
            return f"domain {d}"
    if on("github.com") and (path.startswith("/fchollet") or "euler" in path or "arc-agi" in path or "/arc/" in path):
        return "github path"
    if "euler" in host and not any(on(d) for d in OK_EULER_HOSTS):
        return "euler site"
    if on("projecteuler.net") and ("solution" in path or "thread" in path):
        return "euler solutions"
    return None


class Guard:
    def __init__(self, test_rows=(), practice_rows=()):
        self.sh = set()
        for r in test_rows:
            self.sh |= shingle_hashes(str(r.get("prompt", "")))
            a = str(r.get("answer", ""))
            if len(a.strip()) > 3:
                self.sh |= shingle_hashes(a)
        self.leaks = []  # (answer, [needles]) ; answers only used here
        for r in practice_rows:
            a = str(r.get("answer", "")).strip()
            if len(a) < 3:
                continue
            nd = [x.lower() for x in (r.get("title"), r.get("id")) if x]
            pw = " ".join(words(r.get("prompt", ""))[:10])
            if pw:
                nd.append(pw)
            if str(r.get("id", "")).startswith("pe-"):
                n = str(r["id"])[3:]
                nd += [f"problem {n}", f"euler {n}", f"euler problem {n}"]
            self.leaks.append((a.lower(), [x.lower() for x in nd]))

    def check(self, text, url=""):
        """-> None if allowed, else the reason."""
        if url:
            r = host_blocked(url)
            if r:
                return r
        if self.sh and shingle_hashes(text) & self.sh:
            return "shares a 12-word passage with a sealed test puzzle"
        low = text.lower()
        norm = " ".join(words(text))
        for a, needles in self.leaks:
            if a in low and any(n in low or n in norm for n in needles):
                return "contains a practice puzzle's answer next to its title/id"
        return None


# ---------------------------------------------------------------- html -> text
class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form", "iframe"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "table", "section", "article", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def html_to_text(src):
    p = _Text()
    try:
        p.feed(src)
        p.close()
    except Exception:  # noqa: BLE001
        pass
    t = "".join(p.out)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


class _DDG(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.res, self.cur, self.mode = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        c = a.get("class") or ""
        if tag == "a" and "result__a" in c:
            self.cur = {"title": "", "url": _unwrap(a.get("href", "")), "snippet": ""}
            self.res.append(self.cur)
            self.mode = "title"
        elif tag in ("a", "div", "td") and "result__snippet" in c and self.cur is not None:
            self.mode = "snippet"

    def handle_endtag(self, tag):
        if tag == "a" and self.mode == "title":
            self.mode = None
        elif tag in ("a", "div", "td") and self.mode == "snippet":
            self.mode = None

    def handle_data(self, d):
        if self.cur is not None and self.mode:
            self.cur[self.mode] += d


def _unwrap(href):
    if href.startswith("//"):
        href = "https:" + href
    q = urllib.parse.urlparse(href)
    if "uddg" in q.query:
        return urllib.parse.parse_qs(q.query)["uddg"][0]
    return href


def parse_ddg(page, k=5):
    p = _DDG()
    p.feed(page)
    out = []
    for r in p.res:
        r = {x: re.sub(r"\s+", " ", html.unescape(v)).strip() for x, v in r.items()}
        if r["url"] and r["title"]:
            out.append(r)
    return out[:k]


# ---------------------------------------------------------------- network (replaceable in tests)
def http_get(url, timeout=FETCH_TIMEOUT):
    """-> (final_url, content_type, text). Raises on network errors."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.5", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_BYTES)
        ct = r.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ct)
        return r.geturl(), ct, raw.decode(m.group(1) if m else "utf-8", "replace")


class Web:
    """Per-process web state: the guard, an on/off flag, thread-local event log."""

    def __init__(self):
        self.enabled, self.guard, self.get = False, Guard(), http_get
        self.tl = threading.local()

    def configure(self, enabled, test_rows=(), practice_rows=(), get=None):
        self.enabled, self.guard = bool(enabled), Guard(test_rows, practice_rows)
        self.get = get or http_get

    def begin(self):
        self.tl.events = []

    def end(self):
        ev, self.tl.events = getattr(self.tl, "events", []), []
        return ev

    def _log(self, **kw):
        if not hasattr(self.tl, "events"):
            self.tl.events = []
        self.tl.events.append(kw)

    def search(self, query):
        query = query.strip()[:300]
        if not query:
            return "search: empty query."
        try:
            _, _, page = self.get("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query}))
        except Exception as e:  # noqa: BLE001
            self._log(tool="search", query=query, url=None, status="error", why=str(e)[:100])
            return f"search failed: {type(e).__name__}"
        keep, lines = [], []
        for r in parse_ddg(page, 8):
            why = self.guard.check(r["title"] + " " + r["snippet"], r["url"])
            self._log(tool="search", query=query, url=r["url"], status="blocked" if why else "allowed", why=why)
            if not why and len(keep) < 5:
                keep.append(r)
        for i, r in enumerate(keep, 1):
            lines.append(f"[{i}] {r['title']}\n{r['url']}\n{r['snippet']}")
        return ("\n\n".join(lines) if lines else "no results (some results may have been withheld).")[:PAGE_CHARS]

    def fetch_text(self, url):
        """-> (full_text, final_url, message). Exactly one of full_text / message is set: message is the text shown to the model when the page is
        unavailable (bad URL, blocked, error, unsupported type). Same filters and event log as `fetch`."""
        url = url.strip().split()[0] if url.strip() else ""
        if not re.match(r"https?://", url):
            return None, url, "fetch: input must be a full http(s) URL."
        why = self.guard.check("", url)
        if why:
            self._log(tool="fetch", url=url, status="blocked", why=why)
            return None, url, "[blocked: this page is not available in this experiment]"
        try:
            final, ct, body = self.get(url)
        except Exception as e:  # noqa: BLE001
            self._log(tool="fetch", url=url, status="error", why=str(e)[:100])
            return None, url, f"fetch failed: {type(e).__name__}"
        if "html" in ct.lower() or body.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
            text = html_to_text(body)
        elif ct.lower().startswith("text/") or "json" in ct.lower() or not ct:
            text = body
        else:
            self._log(tool="fetch", url=url, status="error", why="content type " + ct[:40])
            return None, url, f"fetch: unsupported content type {ct[:40]}"
        why = self.guard.check(text, final)
        if why:
            self._log(tool="fetch", url=url, final_url=final, status="blocked", why=why)
            return None, final, "[blocked: this page is not available in this experiment]"
        self._log(tool="fetch", url=url, final_url=final, status="allowed", why=None)
        return text, final, None

    def fetch(self, url):
        text, _, msg = self.fetch_text(url)
        if text is None:
            return msg
        return text[:PAGE_CHARS] + ("\n[page cut]" if len(text) > PAGE_CHARS else "") if text.strip() else "[empty page]"


WEB = Web()
