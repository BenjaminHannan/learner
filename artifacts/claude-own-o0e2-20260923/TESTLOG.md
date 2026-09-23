T1 audit count=61783680 expected=61783680 PASS
toy dialogues=200 ask_turns=600
T2 kill tiny_params=147776 identical_after_resume=True PASS
T3 smoke steps=30 loss_first=58.6267 loss_last=13.8225 falls=True elapsed=0.2s PASS
T3 roundtrip ok=1800/1800 PASS
T4 poison_unchanged=1800/1800 qline_leaks=0 PASS
T5 throughput tokens=129536 seconds=120.0 tok_per_s=1079.3 steps=506 (report only)
T6 rotary err_same_pos=2.861e-06 err_offset=0.000e+00 PASS
WALL total=121.5s
