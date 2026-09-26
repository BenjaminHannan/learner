"""rt-02g reader variants on dev + practice data only (Plain-English puzzles thread, 2026-09-26). Never reads a TEST panel.
Results: artifacts/claude-rt02g-20260926/dev (see WITHDRAWN-rt02g.md there). Run from the repo root:
  OMP_NUM_THREADS=4 python -B scripts/claude_rt02g_margins.py V0|V1|V2 OUT.jsonl BASE
V0 = rt-02g's registered prompt; V1 = a stricter instruction with 12 examples; V2 = a yes/no question (V1's examples).
For each gated message: margin = logit(first token of "numbers") - logit(first token of "none") at the answer's first
position, and the reading continued greedily after a forced "numbers:" (so any threshold can be scored offline).
Prefix KV cache over the shared few-shot part (CPU speed only)."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import torch
import claude_rt02g as G
import claude_sleep02c as SL
from transformers import DynamicCache

V1_ASK = ("Message: {text}\n\nIs this person asking you to find a way to combine the numbers they give, using + - * /, "
          "so that the result equals a target number? Most messages that contain numbers are not: ages, times, prices, "
          "scores, codes, lists and totals, checking a sum, or sharing an answer they already found. If it is a request "
          "to solve such a puzzle, reply exactly \"numbers: <the numbers to combine>; target: <the target>\". "
          "Otherwise reply exactly \"none\".")
V1_SHOT = [
    ("Can you get 10 out of 2, 3 and 4? Each one used once.", "numbers: 2, 3, 4; target: 10"),
    ("My sister has 3 cats, 2 dogs and 1 rabbit, 6 pets in all.", "none"),
    ("We need 4 chairs, 6 plates and 2 tables for 11 guests. Can you write the shopping list?", "none"),
    ("24 using 1 5 5 6 please", "numbers: 1, 5, 5, 6; target: 24"),
    ("Is 5 * 4 + 2 equal to 22?", "none"),
    ("Flight 12 boards at gate 7 from row 3 to row 9. Can you remind me in a text?", "none"),
    ("My numbers are 3 7 8 12. How do I make 20 from them?", "numbers: 3, 7, 8, 12; target: 20"),
    ("I solved it myself: (9 - 3) * 2 = 12!", "none"),
    ("I finally made 18 from 2, 6 and 9 by myself, so happy!", "none"),
    ("What is 7 + 8 + 2 + 1?", "none"),
    ("The swim times were 11, 13, 12 and 10 seconds, and the record is 9. Who should race?", "none"),
    ("Find a way to reach 15 with 9, 2 and 5 using + - * /.", "numbers: 9, 2, 5; target: 15"),
]
V2_ASK = ("Message: {text}\n\nQuestion: is this person asking you to solve a number puzzle, that is, to find a way to "
          "combine the numbers they give with + - * / so that the result is a target number they name? Answer yes or no.")
V2_SHOT = [(q, "no" if a == "none" else "yes") for q, a in V1_SHOT]
VARIANTS = {"V0": (G.READ_ASK, G.FEW_SHOT), "V1": (V1_ASK, V1_SHOT), "V2": (V2_ASK, V2_SHOT)}


def msgs(ask, shot, text):
    m = []
    for q, a in shot:
        m += [{"role": "user", "content": ask.format(text=q)}, {"role": "assistant", "content": a}]
    return m + [{"role": "user", "content": ask.format(text=text)}]


def main(variant, out_path, floor=-6.0):
    ask, shot = VARIANTS[variant]
    yn = variant == "V2"
    for q, a in (V1_SHOT if yn else shot):
        assert (G.accept(q, a) is not None) == (a != "none"), q
    one_b = G.load_one_b(sys.argv[3])
    tok, model = one_b.tok, one_b.model
    for x in SL.lora_mods(model):
        x.scale = 0.0
    render = lambda t: tok.apply_chat_template(msgs(ask, shot, t), tokenize=False, add_generation_prompt=True,
                                              enable_thinking=False)
    a_ids, b_ids = tok(render("AAAA")).input_ids, tok(render("BBBB")).input_ids
    P = next(i for i, (x, y) in enumerate(zip(a_ids, b_ids)) if x != y)
    prefix = a_ids[:P]
    gp = render("AAAA")
    forced = tok(gp + ("yes" if yn else "numbers:")).input_ids[len(a_ids):]
    none_id = tok(gp + ("no" if yn else "none")).input_ids[len(a_ids)]
    num_id = forced[0]
    assert tok(gp + ("yes" if yn else "numbers:")).input_ids[:len(a_ids)] == a_ids
    cache = DynamicCache()
    with torch.no_grad():
        model(input_ids=torch.tensor([prefix]), past_key_values=cache, use_cache=True)
    eos = {tok.eos_token_id} | set(tok.convert_tokens_to_ids([t for t in ["<|im_end|>", "<|endoftext|>"] if t in tok.get_vocab()]))
    nl = set(i for t, i in tok.get_vocab().items() if "\n" in tok.convert_tokens_to_string([t]))
    rows, t0 = [], time.time()
    for k, (src, text, want) in enumerate(G.dev_sets()):
        if not G.pre_gate(text):
            continue
        ids = tok(render(text)).input_ids
        assert ids[:P] == prefix
        cache.crop(P)
        with torch.no_grad():
            lg = model(input_ids=torch.tensor([ids[P:]]), past_key_values=cache, use_cache=True).logits[0, -1]
        margin = float(lg[num_id] - lg[none_id])
        top = tok.decode([int(lg.argmax())])
        reading = None
        if margin >= floor and not yn:
            gen, nxt = [], list(forced)
            with torch.no_grad():
                for _ in range(G.READ_MAX_NEW):
                    lg2 = model(input_ids=torch.tensor([nxt]), past_key_values=cache, use_cache=True).logits[0, -1]
                    t = int(lg2.argmax())
                    if t in eos or t in nl:
                        break
                    gen.append(t)
                    nxt = [t]
            reading = "numbers:" + tok.decode(gen)
        got = G.accept(text, reading) if reading else None
        rows.append({"k": k, "src": src, "kind": "puzzle" if want else "negative", "margin": round(margin, 3),
                     "top": top, "reading": reading, "got": got, "want": want})
        if len(rows) % 20 == 0:
            print(len(rows), round(time.time() - t0), flush=True)
    Path(out_path).write_text("".join(json.dumps(r) + "\n" for r in rows))
    print("done", variant, len(rows), round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
