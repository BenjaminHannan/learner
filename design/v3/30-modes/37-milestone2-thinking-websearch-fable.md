# Milestone 2 — THINKING / LEARNING mode v1 with web search (Fable, 22 Sep 2026)

Script: `scripts/fable_thinking_m2.py` (plain software; the searcher is a plug-in tool).

Checked: `--selftest` 18/18, including hostile pages (missing url, value not in the quote, a claim about a
person Ben taught, an instruction-shaped claim, a non-object, a bad relation key). One REAL search
("the moons of Mars", GPT web helper): 8 findings quarantined with NASA urls and quotes; none answer
questions until approved. First real run returned 0 findings because the helper replies in escaped
Markdown; `parse_bridge_reply` now undoes that and a regression check covers it.

Rules enforced: only Ben-assigned (or Ben-approved) topics are searched; only the topic text leaves the
machine; topics naming someone Ben taught are refused; claims need url + quote containing subject and
value; rows are `web-quarantine`; only `approve` (actor ben -> promote) makes a taught row.

Known limits (not fixed): the quote is what the helper REPORTS, not re-fetched and verified against the
page; values are literals only (no entity links, so no multi-hop through web facts yet); relation keys are
whatever the helper chose (no normalisation: `discovered_by` vs `discoverer`); curiosity is only a
"suggested topic" list, no learned drive; one search takes minutes; Codex is not installed on the Mac, so
the helper is the search tool.

## v1.1 (same day) — Ben: "don't assume what it reads is true; if in doubt, look somewhere else; I won't approve 1,000 facts"

Per-fact approval is gone. New judge (`Thinking.judge`): a claim is BELIEVED only if (a) its quote is really on
the re-opened page, (b) >= 2 independent websites give the same value, (c) any rival value trails by >= 2
websites. Otherwise it looks elsewhere (one batched search per round, websites already seen are excluded,
at most 2 rounds per fact) and, if still in doubt, does not believe it. Believed rows are a new notebook
source `web-verified` (contract cases c31, c32): ranked below taught/inferred/sleep rows, needs evidence from
2 websites, and answers carry "(I read that online; you didn't tell me.)". Text naming anyone Ben taught
about is never sent out, even when it came from a web page. Self-test: 19 checks.

Known limits: values must match exactly after normalisation ("two" vs "2" do not agree); two websites can
copy the same wrong source (independence = different domain only); entities have no person/thing kind, so
anything Ben has taught facts about is treated as private and never updated from the web; pages that block
simple fetches or need JavaScript make quotes uncheckable, so those claims stay unbelieved.

## v1.2 (2026-09-21) — two fixes found by real runs
Real run 1 (topic "the moons of Mars"): 8 NASA claims found, **0 believed**. Cause: the web helper drops the backslash in `\"`, so one quote containing speech marks made the whole look-elsewhere reply unreadable. Fix: replies are now read item by item (`_salvage_objects`), and raw replies can be logged with `FABLE_BRIDGE_LOG=<dir>`.
Real run 2: 3 believed, each from 3 independent sites; the rest stuck because "11 km", "approximately 11 km" and "≈11.0 km" counted as three rival values. Fix: `_value_key` — a `<number> <unit>` value agrees when number and unit match to 2 significant figures; names, dates and bare years still need word-for-word agreement. Re-judging the same saved findings (no new web calls): **6 of 6 believed**, 2–4 sites each.
Means: the judge can read a topic and end up believing only things several independent sites say, with no approval from Ben. Doesn't mean: one topic, friendly facts; no adversarial/false-claim topic tried on the live web yet; the stored wording is the first site's ("more than 23 000 km"), not the most precise one.
Known gaps: Wikipedia quotes often fail the on-page check (footnote marks / fetch differences); unit conversion (6.9 miles vs 11 km) not attempted.
