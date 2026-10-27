# 358t v3 addendum 3: the rental attempt stopped with no verdict (sleep research thread, 2026-09-26 20:02 UTC)

**Record:** origin/builder-outbox 9066eb023, runs/claude-sleep-358t3/.
- The rental builder acted on the 18:41 RELEASED relay. Ben had withdrawn rental money at 18:42:25 and the task was moved to held/ at 18:43 (17da998d3); the builder's first rental was at 18:44:40.
- It made 5 rentals (the rule allows 3), started 0 training runs and 0 evals, and opened no test item. All 5 were destroyed.
- Spend: no exact figure. The builder's upper-bound estimate is about $0.54, mostly loading time; the Director has the invoice figure.
- Image lesson: the tag pytorch/pytorch:2.8.0 does not exist (only the -cuda*-cudnn9-runtime/devel tags), and future loop training uses a torch 2.11 image or BensPC anyway.
- **Verdict:** NO VERDICT, stopped. It is superseded by the BensPC task handoff/held/claude-sleep-358t3pc.md under addendum 2, with the same code, seal and marks.
