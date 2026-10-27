# v1 withdrawn before any run (2026-09-20)

This experiment was frozen (manifest 42ccdf15…) and queued, but NO stage-A or stage-B run was ever started. Astra's audit (design/v3/18-audit-before-fable-continues.md, §7)
found two launch blockers: (1) stage B loads stage A with no competence gate, which would repeat marg-staged's missing premise; (2) the `frozen-terminal-6` arm changes two
things at once (drops absent candidates AND renormalises away non-entity mass), so it is not a clean absent-candidate test; and the diagnostics score only the
single-model system, not LINK + the frozen terminal used in training. The queued launcher was cancelled. Successor: v2 built to
design/v3/18-link-isolation-v2-preregistration-draft.md. Fable's predictions P21–P25 in this folder are void (never scoreable).
