"""Step 4 (job 1, GPU): base K2 + slot memory + prompt rule over days 1-5, with the DETERMINISTIC sim-Ben in the loop.
Round 1 = first move for every request of the day; ASKs get a pre-written answer and the model moves again (round 2).
A wrong committed slot value triggers a pre-written correction. Writes diary/day{d}.jsonl (+ oracle/day{d}.jsonl, never read by the tagger).
`gen` is any callable gen(prompts, max_new, temperature, seed) -> list[str] so the same code runs on the GPU and on a tiny CPU model.
"""
import os
from pathlib import Path

from .config import ACT_MAX_NEW, DATA, DAYS_TRAIN, jdump, jl_write, jload, shrink
from .slot_memory import SlotMemory
from .tools_mock import MockWorld, check_action, parse_reply
from .user_sim import UserSim
from .world import Persona, act_text, first_messages, load_requests, render


def run_days(gen, persona, phr, bos="", days=None, out_dir=None, seed=7, temperature=0.7, requests=None, log=print):
    out_dir = Path(out_dir or "diary_out")
    sim = UserSim(persona, phr)
    mem = SlotMemory()
    known = set()
    world = MockWorld()
    allreq = requests if requests is not None else load_requests(split="train")
    facts = list(persona.facts.values())
    summary = {}
    for day in days or range(1, DAYS_TRAIN + 1):
        reqs = shrink([r for r in allreq if r["day"] == day])
        # --- round 1
        msgs, memlines = [], []
        for r in reqs:
            ml = mem.retrieve(r["text"] + " " + " ".join(persona.slot(s)["ref"] for s in r["slots"])) if r["underspecified"] or len(mem) else []
            memlines.append(ml)
            msgs.append(first_messages(persona, r, ml))
        out1 = gen([render(m, True, bos) for m in msgs], ACT_MAX_NEW, temperature, seed + day * 10)
        parsed1 = [parse_reply(o) for o in out1]
        # --- sim answers, round 2
        ask_idx = [i for i, (k, _) in enumerate(parsed1) if k == "ASK"]
        answers = {}
        for i in ask_idx:
            answers[i] = sim.answer_ask(reqs[i], parsed1[i][1], known)
        msgs2 = [msgs[i] + [{"role": "assistant", "content": "ASK " + parsed1[i][1]}, {"role": "user", "content": answers[i][0]}] for i in ask_idx]
        out2 = gen([render(m, True, bos) for m in msgs2], ACT_MAX_NEW, temperature, seed + day * 10 + 1) if msgs2 else []
        parsed2 = {i: parse_reply(o) for i, o in zip(ask_idx, out2)}
        out2d = dict(zip(ask_idx, out2))
        diary, oracle, new_mem = [], [], []
        for i, r in enumerate(reqs):
            ml = memlines[i]
            refs = [persona.slot(s)["ref"] for s in r["slots"]] if r["underspecified"] else []
            rows = [{"day": day, "req_id": r["req_id"], "turn": 0, "role": "user", "text": r["text"],
                     "meta": {"kind": "request", "lookup_refs": refs, "memory": ml, "prompt_user": msgs[i][1]["content"]}}]
            move1, payload1 = parsed1[i]
            rows.append({"day": day, "req_id": r["req_id"], "turn": 1, "role": "assistant", "text": out1[i].strip(), "meta": {"kind": "move", "move": move1}})
            final = (move1, payload1)
            orc = {"day": day, "req_id": r["req_id"], "first_move": move1, "slots": r["slots"], "underspecified": r["underspecified"],
                   "regret": False, "annoyance": False, "silent_wrong": False, "copy_error": False, "regret_slots": [], "annoy_slot": None}
            turn = 2
            if move1 == "ASK":
                ans, sid, annoyed = answers[i]
                rows.append({"day": day, "req_id": r["req_id"], "turn": turn, "role": "user", "text": ans, "meta": {"kind": "answer"}})
                turn += 1
                orc["annoyance"] = annoyed
                orc["annoy_slot"] = sid
                if sid and refs:
                    new_mem.append((day, "qa", persona.slot(sid)["ref"], f'{persona.slot(sid)["ref"]}: asked "{payload1}"; Ben answered: {ans}'))
                    known_add = sid
                    orc["answered_slot"] = known_add
                final = parsed2[i]
                rows.append({"day": day, "req_id": r["req_id"], "turn": turn, "role": "assistant", "text": out2d[i].strip(), "meta": {"kind": "move", "move": final[0]}})
                turn += 1
            if final[0] == "ACT":
                res = world.execute(final[1])
                ok, bad = check_action(final[1], r["gold"])
                rows.append({"day": day, "req_id": r["req_id"], "turn": turn, "role": "user", "text": "", "meta": {"kind": "tool_result", "result": res}})
                turn += 1
                if not ok:
                    bad_slots = [r["arg_slots"][a] for a in bad if a in r["arg_slots"]]
                    bad_slots = list(dict.fromkeys(bad_slots))
                    if bad_slots:
                        sid = bad_slots[0]
                        ctext = sim.correction(r, sid)
                        if ctext is None:
                            orc["silent_wrong"] = True
                        else:
                            rows.append({"day": day, "req_id": r["req_id"], "turn": turn, "role": "user", "text": ctext, "meta": {"kind": "correction"}})
                            new_mem.append((day, "corr", persona.slot(sid)["ref"], f'{persona.slot(sid)["ref"]}: Ben corrected me: {ctext}'))
                            if move1 == "ACT":
                                orc["regret"], orc["regret_slots"] = True, bad_slots
                            else:
                                orc["copy_error"] = True
                            orc["answered_slot"] = sid
                    else:
                        orc["copy_error"] = True
                orc["final_ok"] = ok
            else:
                orc["final_ok"] = False
                orc["no_action"] = True
            orc["final_move"] = final[0]
            diary += rows
            oracle.append(orc)
        # background facts told to the assistant today (8 per day, 40 over days 1-5)
        for fct in facts[(day - 1) * 8: day * 8]:
            diary.append({"day": day, "req_id": f"fact-{fct['fact_id']}", "turn": 0, "role": "user", "text": fct["statement"], "meta": {"kind": "fact", "fact_id": fct["fact_id"]}})
            diary.append({"day": day, "req_id": f"fact-{fct['fact_id']}", "turn": 1, "role": "assistant", "text": "Noted.", "meta": {"kind": "ack"}})
        for d_, k_, ref_, t_ in new_mem:  # memory and the 'known' set update only at day end (fixed during the day)
            mem.add(d_, k_, ref_, t_)
        for o in oracle:
            if o.get("answered_slot"):
                known.add(o["answered_slot"])
        jl_write(out_dir / "diary" / f"day{day}.jsonl", diary)
        jl_write(out_dir / "oracle" / f"day{day}.jsonl", oracle)
        summary[day] = {"n": len(reqs), "asks": sum(o["first_move"] == "ASK" for o in oracle), "regret": sum(o["regret"] for o in oracle),
                        "annoyance": sum(o["annoyance"] for o in oracle), "final_ok": sum(bool(o.get("final_ok")) for o in oracle),
                        "no_action": sum(bool(o.get("no_action")) for o in oracle), "silent_wrong": sum(o["silent_wrong"] for o in oracle)}
        log(f"day {day}: {summary[day]}")
    jdump(out_dir / "daylog_summary.json", summary)
    return summary
