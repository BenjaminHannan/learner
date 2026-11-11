#!/usr/bin/env python3
"""Weekly Field monitor: scans new AI/model research for what matters to this project and writes an ELI5 brief.

Paid from the API credit (LEARNER_ANTHROPIC_API_KEY). One Sonnet request with web search, capped searches.
Usage: python3 ops/field-monitor/scan.py [--days 7] [--out-dir /mnt/project-files/field-monitor]
"""
import argparse, datetime, os, sys, zoneinfo

TOPICS = """- small models that reason and learn from few examples
- looped / recurrent thinkers (same layers reused many times) and learned stopping
- continual learning without forgetting (sleep / replay, anti-forgetting guards)
- scaling: getting more out of size than a plain transformer
- self-play and game agents (Minecraft especially)
- intrinsic motivation / curiosity / learned reward
- tool use by small models"""

SYSTEM = f"""You are the Field monitor for Ben's model-training project (Ben is a high-school senior).
The project builds a small model (hundreds of millions of parameters) that thinks in loops, learns new skills from a few examples without forgetting old ones (sleep/replay), uses outside tools, and aims to beat Minecraft like a person.

Scan arXiv and lab/research blogs (Anthropic, OpenAI, Google DeepMind, Meta FAIR, AI2, Hugging Face, Mistral, Qwen, etc.) for NEW items from the last {{days}} days on:
{TOPICS}

Rules:
- Use web search. Only report items you actually found; give the real title, date and link for each. Never invent papers.
- Pick at most 6 items, ranked by how much they could matter to the project. Skip hype and incremental noise.
- For each item: one plain-language line on what it is (ELI5, no jargon), one line on why it might matter to us (or "probably not"), and a label: SHOWN (paper reports it with evidence), CLAIMED (blog/PR claim only) or UNCLEAR.
- If nothing relevant is new, say so in two lines; do not pad.
- Format: markdown. Start with a 2-sentence "This week in short" for Ben, then the items, then "Worth a deeper look" listing 0-2 item titles.
- Under 600 words. Times in US Eastern (ET)."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out-dir", default="/mnt/project-files/field-monitor" if os.path.isdir("/mnt/project-files") else "ops/field-monitor/briefs")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--max-searches", type=int, default=15)
    a = ap.parse_args()
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        sys.exit("LEARNER_ANTHROPIC_API_KEY is not set")
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    import anthropic
    c = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")
    now = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    msgs = [{"role": "user", "content": f"Today is {now:%Y-%m-%d}. Run the scan for the last {a.days} days and write the brief."}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": a.max_searches}]
    usage_in = usage_out = 0
    for _ in range(6):  # continue if the server pauses a long turn
        r = c.messages.create(model=a.model, max_tokens=8000, system=SYSTEM.replace("{days}", str(a.days)),
                              tools=tools, messages=msgs)
        usage_in += r.usage.input_tokens
        usage_out += r.usage.output_tokens
        if r.stop_reason != "pause_turn":
            break
        msgs.append({"role": "assistant", "content": r.content})
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    if not text:
        sys.exit("empty brief")
    os.makedirs(a.out_dir, exist_ok=True)
    path = os.path.join(a.out_dir, f"brief-{now:%Y-%m-%d}.md")
    with open(path, "w") as f:
        f.write(f"# Field monitor brief, {now:%b %d, %Y} ET\n\n{text}\n\n_Tokens: {usage_in} in, {usage_out} out._\n")
    print(path)
    print(f"tokens in={usage_in} out={usage_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
