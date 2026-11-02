"""Probe-5 analysis = Probe-4's analyze_e2e.py (same pickers, metric, pass marks E1-E3, tie-breaks) run on the LFM3 outputs; only the report title changes.
Usage: analyze_p5.py --tries DIR/tries/results.jsonl --self DIR/self_scores.jsonl --test-b DIR/tests_b/probes_lfm3base.jsonl --test-t DIR/tests_t/probes_lfm3.jsonl --out DIR [--tasks tasks_new.jsonl]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common  # noqa: F401  (sets sys.path for probe4 / probe1)
import analyze_e2e as E

_report_md = E.report_md
E.report_md = lambda *a, **k: _report_md(*a, **k).replace("# Probe-4 report", "# Probe-5 report (LFM3-1.7B, llama.cpp)", 1)

if __name__ == "__main__":
    E.main()
