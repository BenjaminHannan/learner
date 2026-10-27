"""Generate raw synthetic assistant conversations with Sonnet 5.5.
usage: python3 generate.py --calls 4 --raw RAW.jsonl [--cap 37] [--workers 8]
Appends one JSON record per API call to RAW; cost is tracked in RAW.cost (resumable)."""
import argparse, json, os, random, re, sys, threading, time, pathlib
import anthropic
from concurrent.futures import ThreadPoolExecutor
HERE = pathlib.Path(__file__).parent
MODEL = "claude-sonnet-5-5"
PRICE_IN, PRICE_OUT = 3.0, 15.0   # $/M tokens (assumed; no docs lookup possible)
PER_CALL = 5

SCENARIOS = {
 "single_tool": (17, "ONE tool call then a short final answer. Request is clear and one tool suffices."),
 "multi_step": (22, "A chain of 2-6 dependent tool calls (each call uses info from the previous result; one call per assistant turn). Some tool results should be messy/partial/empty-but-not-fatal. Aim for 3-5 calls."),
 "clarify": (9, "The request is genuinely ambiguous or missing a required detail (which file? which Alex? what time?). The assistant asks ONE short clarifying question with NO tool call; the user answers; then the assistant proceeds (usually with a tool call) and finishes. May first do a harmless read-only lookup to narrow options."),
 "confirm_irreversible": (12, "The user asks for an irreversible/destructive action (send_email, or run_shell with rm / overwrite / mv over existing files / git push --force). The assistant first prepares (e.g. email_draft or ls/search to show what would be affected), shows the exact recipients/content/targets and asks for explicit confirmation WITHOUT calling the irreversible tool. The user then confirms (or in ~25% of cases changes something or cancels), and only then the assistant performs it."),
 "direct_answer": (9, "No tool is needed (general knowledge, coding concept, quick math, writing advice, rephrasing text the user pasted). The assistant answers directly and concisely with NO tool calls. 1-2 user turns."),
 "error_recovery": (11, "A tool call returns an error (file not found, permission denied, command not found, timeout, 404, invalid date, rate limit). The assistant recognizes the cause, adapts (different path, list_dir to find it, other tool, fixed args) and succeeds; or if it truly cannot, it says so honestly and offers the next step. Never pretend success."),
 "summarize_long": (6, "A tool returns a LONG output (40-120 lines of realistic log/file/email list/search results/page text, written out in full but kept tidy). The assistant gives a concise, accurate summary highlighting what matters to the user, citing specifics from the output."),
 "parallel": (14, "In ONE assistant turn the assistant emits 2-4 independent tool_calls (e.g. read several files, check calendar + search email + notes, search web two queries). Then one tool message per call, in the same order. Then a combined final answer; optionally a follow-up round."),
}
DOMAINS = ["school (homework, classes, college applications, AP exams, teachers)", "coding (the user's side projects, git, python, JS, debugging, builds)",
 "personal admin (bills, appointments, travel, errands, receipts, family)", "research (papers, web lookups, comparing options, citations)",
 "writing (essays, emails, blog posts, cover letters, notes)", "scheduling (calendar, reminders, study blocks, meetings, deadlines)"]
FIRST = ["Maya","Theo","Priya","Jonah","Lena","Omar","Sofia","Kenji","Ava","Darius","Nia","Felix","Ines","Caleb","Yara","Mateo","Hana","Rowan","Zara","Eli"]
LAST = ["Alder","Brightwater","Castellan","Dunmore","Everhart","Fairbanks","Greywood","Holloway","Ironside","Juniper","Kestrel","Lockridge","Marlowe","Northcott","Oakhurst","Pemberly","Quillfeather","Ravenscroft"]
FAKE_DOMAINS = ["example.com","example.org","mail.example.net","northfield-hs.example.edu","studymail.example.com"]
SYS_STYLES = [
 "You are a helpful personal assistant running locally on {user}'s MacBook. You can use tools to read and manage files, run shell commands, browse the web, and handle calendar, email, reminders and notes. Today is {today}. Current directory: {home}. Ask a short question if a request is ambiguous, and always get explicit confirmation before irreversible actions such as sending email or deleting files. Be concise.",
 "You are Mac Assistant, an on-device assistant for {user}. Use the provided tools when they help; answer directly when they don't. Do not guess missing details: ask. Confirm before anything irreversible (send_email, rm, overwriting files). Date: {today}. Home folder: {home}. Keep replies short and plain.",
 "Local assistant for {user} (high school senior and developer). Tools available: files, shell, web, calendar, email, reminders, notes. Date: {today}. Home: {home}. Rules: be brief; never invent tool results; if a tool fails, adapt or explain; confirm with the user before sending email or running destructive commands.",
]

def make_specs(rng, n):
    names = list(SCENARIOS); w = [SCENARIOS[k][0] for k in names]
    specs = []
    for _ in range(n):
        user = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        d = rng.randint(1, 28); m = rng.choice([9,10,11,12,1,2,3,4,5])
        y = 2026 if m >= 9 else 2027
        today = f"{y}-{m:02d}-{d:02d}"
        specs.append(dict(scenario=rng.choices(names, w)[0], domain=rng.choice(DOMAINS),
            user=user, today=today, home=f"/Users/{user.split()[0].lower()}",
            sys_style=rng.randrange(len(SYS_STYLES)), seed=rng.randrange(10**6)))
    return specs

def build_prompt(specs, tools):
    tdesc = "\n".join(f"- {t['function']['name']}({', '.join((k+('*' if k in t['function']['parameters'].get('required',[]) else '')) for k in t['function']['parameters']['properties'])}): {t['function']['description']}" for t in tools)
    tschema = json.dumps([t["function"] for t in tools], separators=(",", ":"))
    items = "\n".join(f"{i+1}. scenario={s['scenario']} | domain={s['domain']} | user={s['user']} | today={s['today']} | home={s['home']} | variety-seed={s['seed']}\n   scenario rule: {SCENARIOS[s['scenario']][1]}" for i, s in enumerate(specs))
    return f"""You are writing training data for a small local personal-assistant model that calls tools. Write {len(specs)} COMPLETE, realistic conversations between a user (a high-school senior who is also a developer) and the assistant on their MacBook.

TOOLS (* = required arg). Full JSON schemas follow; arguments you write MUST validate against them exactly (use only listed parameter names, correct types and enum values):
{tdesc}
SCHEMAS: {tschema}

SPECS (one conversation per spec, in order):
{items}

RULES
- All people, emails, files, schools, URLs are FICTIONAL. Use only example.com/.org/.net/.edu style domains; no real people, companies' private data, or real addresses. Names in the conversations can be invented freely (not just the user's name).
- User messages are natural, casual, sometimes terse or with typos; they vary a lot in length and style. Do not start every conversation the same way. Invent specific, concrete situations (use the variety-seed as inspiration) rather than generic ones.
- Assistant turns are concise, direct, contain NO hidden reasoning/thinking and no "Let me think". When calling tools, the assistant content is usually null or one very short sentence. The final assistant message reports the real result from the tool outputs, accurately, in a few sentences max (plain text, light formatting, no emoji).
- Tool results are realistic, specific and consistent with earlier results and with what the assistant says afterward. A tool message content is a string (usually compact JSON text, or plain stdout for run_shell/read_file). Include realistic errors and empty results where the scenario calls for it. Keep tool outputs short unless the scenario says long.
- BE COMPACT (cost matters): keep every tool result to at most ~6 short lines/items (except summarize_long), avoid padding fields, keep user and assistant messages short, at most 3-4 tool calls in multi_step chains unless truly needed, final answers 1-3 sentences.
- Paths use the user's home. Dates use today as reference; ISO 8601 for datetimes in args.
- The assistant must never call send_email or a destructive run_shell (rm, force push, overwrite) without the user having explicitly confirmed in an earlier user message after the assistant showed exactly what would happen.
- Each assistant tool-calling turn may have several tool_calls (parallel); then there must be exactly one tool message per call, in the same order, right after it.
- Conversation must END with an assistant message with text and no tool_calls.

OUTPUT: strictly a JSON array of {len(specs)} objects, nothing else (no markdown fences). Each object:
{{"scenario": "<spec scenario>", "messages": [
  {{"role":"user","content":"..."}},
  {{"role":"assistant","content":null,"tool_calls":[{{"name":"read_file","arguments":{{"path":"..."}}}}]}},
  {{"role":"tool","content":"..."}},
  {{"role":"assistant","content":"final text"}}
]}}
Do NOT include a system message or tool-call ids; they are added by code. "arguments" is a JSON object."""

class Cost:
    def __init__(s, path): s.p = pathlib.Path(path); s.l = threading.Lock(); s.v = json.loads(s.p.read_text()) if s.p.exists() else {"in":0,"out":0}
    def add(s, i, o):
        with s.l: s.v["in"]+=i; s.v["out"]+=o; s.p.write_text(json.dumps(s.v))
    @property
    def usd(s): return s.v["in"]*PRICE_IN/1e6 + s.v["out"]*PRICE_OUT/1e6

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", type=int, required=True); ap.add_argument("--raw", required=True)
    ap.add_argument("--cap", type=float, default=37.0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    client = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"], base_url="https://api.anthropic.com", max_retries=0)
    tools = json.loads((HERE/"tools.json").read_text())
    cost = Cost(a.raw + ".cost"); rng = random.Random(a.seed if a.seed is not None else time.time_ns())
    out_lock = threading.Lock(); stop = threading.Event(); done = [0]
    jobs = [make_specs(rng, PER_CALL) for _ in range(a.calls)]
    def run(specs):
        if stop.is_set(): return
        prompt = build_prompt(specs, tools)
        for attempt in range(8):
            # reserve: worst case ~ one in-flight call per worker beyond current spend
            if cost.usd + a.workers*0.12 >= a.cap: stop.set(); return
            try:
                r = client.messages.create(model=MODEL, max_tokens=12000,
                    messages=[{"role":"user","content":prompt}])
                cost.add(r.usage.input_tokens, r.usage.output_tokens)
                text = "".join(b.text for b in r.content if b.type == "text")
                with out_lock:
                    with open(a.raw, "a") as f:
                        f.write(json.dumps({"specs":specs,"text":text,"stop":r.stop_reason,"usage":[r.usage.input_tokens,r.usage.output_tokens]})+"\n")
                    done[0]+=1
                    if done[0]%10==0: print(f"calls {done[0]}  est ${cost.usd:.2f}", flush=True)
                return
            except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as e:
                time.sleep(min(60, 2**attempt + random.random()*2))
            except anthropic.APIStatusError as e:
                if e.status_code == 529: time.sleep(min(60, 2**attempt+random.random()*2)); continue
                print("API error", e.status_code, str(e)[:200], file=sys.stderr); return
    with ThreadPoolExecutor(a.workers) as ex: list(ex.map(run, jobs))
    print(f"finished calls={done[0]} est cost ${cost.usd:.2f} stopped_at_cap={stop.is_set()}")
if __name__ == "__main__": main()
