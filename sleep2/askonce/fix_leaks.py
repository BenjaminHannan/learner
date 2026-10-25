"""One-off, deterministic repair of the frozen text so the new-ambiguity words no longer appear in days 1-5 text (see DEVIATIONS.md, 'Leakage scan').
Only NON-held-out slots, the 40 background facts and one anchor prompt are edited; no value that gold actions use is changed.
Re-freezes persona.json / phrasings.json hashes. Safe to re-run (a second run finds nothing to replace).
  python -m sleep2.askonce.fix_leaks"""
import json
import re

from .config import DATA, jdump, jload, sha256_file

# slot id -> ordered [(regex, replacement)] applied to labels, refs, values-as-text and all of the slot's phrasings
SLOT_FIXES = {
    "contact_21": [(r"sam\.rivera\.mom@", "theo.rivera.aunt@"), (r"Sam's mom", "Theo's aunt"), (r"\bSam\b", "Theo"), (r"\bmom\b", "aunt")],
    "meeting_09": [(r"\bSam\b", "Theo")],
    "meeting_02": [(r"\bMom\b", "Aunt Rae"), (r"\bmom\b", "Aunt Rae"), (r"Orthodontist adjustment", "Braces adjustment"), (r"\borthodontist\b", "braces place")],
    "contact_16": [(r"\borthodontist\b", "braces place")],
    "contact_19": [(r"\bstudy group\b", "book club"), (r"lab class", "chem section")],
    "contact_03": [(r"debate coach", "forensics coach"), (r"driving instructor", "road-test examiner")],
    "file_07": [(r"Debate club", "Forensics club"), (r"/clubs/debate/", "/clubs/forensics/"), (r"\bdebate\b", "forensics")],
    "meeting_01": [(r"fundraiser planning", "fundraiser prep")],
    "meeting_03": [(r"Chemistry lab report due", "Chemistry write-up due"), (r"the lab report", "the write-up"), (r"\blab report\b", "write-up")],
    "file_08": [(r"Band concert travel permission", "Band trip travel permission"), (r"permission_concert_travel", "permission_band_travel"), (r"\bconcert\b", "trip")],
    "meeting_04": [(r"Garcia's Pizza", "Garcia's Grill"), (r"\bpizza\b", "grill"), (r"\bPizza\b", "Grill")],
    "contact_20": [(r"Grandma's landlord", "Nana's landlord"), (r"\b[Gg]randma\b", "nana")],
}
FACT_FIXES = {
    "fact_18": [(r"\b[Gg]randmother\b", "nana"), (r"\b[Gg]randma\b", "nana")],
    "fact_27": [(r"\bbirthday\b", "date of birth")],
    "fact_32": [(r"\b[Oo]rthodontist\b", "braces doctor")],
    "fact_39": [(r"\bdriving\b", "behind-the-wheel")],
}
ANCHOR_FIXES = [(r"how to study for", "how to prepare for")]


def sub(text, fixes):
    for rx, rep in fixes:
        text = re.sub(rx, rep, text)
    return text


def walk(o, fixes):
    if isinstance(o, str):
        return sub(o, fixes)
    if isinstance(o, list):
        return [walk(x, fixes) for x in o]
    if isinstance(o, dict):
        return {k: walk(v, fixes) for k, v in o.items()}
    return o


def main():
    P, phr = jload(DATA / "persona.json"), jload(DATA / "phrasings.json")
    for s in P["slots"]:
        if s["slot_id"] in SLOT_FIXES:
            assert s["split"] != "new"
            fx = SLOT_FIXES[s["slot_id"]]
            for k in ("candidates",):
                s[k] = walk(s[k], fx)  # labels and wrong-candidate values only; the true value is checked below
    for f in P["facts"]:
        if f["fact_id"] in FACT_FIXES:
            for k in ("statement", "recall_q"):
                f[k] = sub(f[k], FACT_FIXES[f["fact_id"]])
    for sid, fx in SLOT_FIXES.items():
        phr["slots"][sid] = walk(phr["slots"][sid], fx)
    for fid, fx in FACT_FIXES.items():
        phr["facts"][fid] = walk(phr["facts"][fid], fx)
    phr["general"] = walk(phr["general"], ANCHOR_FIXES)
    for s in P["slots"]:
        assert s["value"] in [c["value"] for c in s["candidates"]], f"{s['slot_id']}: true value was renamed"
    reqs = (DATA / "requests.jsonl").read_text()
    jdump(DATA / "persona.json", P)
    jdump(DATA / "phrasings.json", phr)
    for f in ("persona", "phrasings"):
        name = f"{f}.json"
        (DATA / f"{f}.sha256").write_text(sha256_file(DATA / name) + f"  {name}\n")
    assert not re.search(r"Theo's aunt|theo\.rivera|forensics|Braces adjustment|chem section|book club|Garcia's Grill|Nana's|road-test", reqs), "requests.jsonl would need regenerating"
    print("fixed; persona/phrasings re-frozen")


if __name__ == "__main__":
    main()
