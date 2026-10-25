# Habit spotting: what others do (Haiku search sweep, 2026-10-25 ~22:35Z; snippets only, verify before citing)

- Memory systems (Generative Agents reflection, Mem0, Zep/Graphiti bi-temporal graph, A-Mem, Letta): none has a dedicated habit detector. The closest are reflection (periodic higher-level conclusions) and Zep's "valid from / valid until" times (useful for habits that stop). Suggested.
- Periodic pattern mining (Kiran & Fournier-Viger, *Periodic Pattern Mining*, Springer 2021; xED routine mining in smart homes, HAL hal-01188640). It scores items by distinct-period support plus periodicity and variability. Our name-pair count is the 2-item special case. Suggested.
- Benchmarks: LongMemEval, LoCoMo(-Plus), PrefEval, PERSONAMEM, LifeAgentBench. None tests routine inference from scattered chat mentions, so a held-out week is still the realistic test.

Ideas for Habit-2 (untested):
1. Items beyond name pairs: a single name, a weekday or time bucket, or a recurring task type. Count support as distinct days and add a periodicity check. Test it on a new week with injected weekday-only, time-only and single-name routines plus 2-day coincidence distractors.
2. Stopped habits: a "last seen" window. A routine not seen for N days goes stale (the newest-wins rule should cover habit items too). Test: a routine that stops mid-run.
3. False habits: Habit-1 stage 1 already measures this with the F set (40 fact pairs). Add true coincidences (2 one-off meetings) as negatives in the next week.
