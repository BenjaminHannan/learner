"""Wrapper: regenerate the far-join chain into a scratch dir without editing tracked code.
usage: python3 regen.py BASE STAGE [--stub-missing]
STAGE: panel-v1 panel-v2 panel-v3 probe build build-mode build-l3 build-l4 build-l5
--stub-missing (NON-FAITHFUL diagnostic only): create empty files for MODE_ROWS / L4_ROWS / L4R1_ROWS so build-l3/build-l5 can run
without the parent checkpoint. Output is NOT the recorded data."""
import hashlib, os, sys
sys.path.insert(0, '/home/user/wtfar')
base, stage = sys.argv[1], sys.argv[2]
stub = '--stub-missing' in sys.argv
PANEL, DIAG, LEARN = (os.path.join(base, d) for d in ('panel', 'diag', 'learn'))
for d in (PANEL, DIAG, LEARN):
    os.makedirs(d, exist_ok=True)

from domain import panel as P
from domain.far import sheet_probe as SP
from domain.far import learn_probe as LP
import domain.far.panel_v3 as PV3

P.OUT_DIR = PANEL
SP.DIAG = DIAG
SP.PROBE = os.path.join(DIAG, 'sheet-probe.jsonl')
SP.FACTORS_JSON = os.path.join(DIAG, 'sheet-factors.json')
SP.FACTORS_MD = os.path.join(DIAG, 'sheet-factors.md')
SP.PANEL_FILES = (os.path.join(PANEL, 'sheet.jsonl'), os.path.join(PANEL, 'sheet.v2.jsonl'))
LP.LEARN = LEARN
j = lambda n: os.path.join(LEARN, n)
LP.TRAIN_ROWS = j('train-rows.jsonl'); LP.MODE_ROWS = j('train-rows-mode.jsonl')
LP.L3_TRAIN_ROWS = j('train-rows-l3.jsonl'); LP.L3_EVAL_ROWS = j('eval-rows-l3.jsonl'); LP.L3_SPLIT = j('pair-split-l3.json')
LP.L5_TRAIN_ROWS = j('train-rows-l5.jsonl'); LP.L5_EVAL_ROWS = j('eval-rows-l5.jsonl')
LP.L4_ROWS = j('train-rows-l4.jsonl'); LP.L4R1_ROWS = j('train-rows-l4r1.jsonl'); LP.L9_ROWS = j('train-rows-l9.jsonl')
LP.V3_PANEL = os.path.join(PANEL, 'sheet.v3.jsonl')
LP.EXCLUDE_FILES = (SP.PROBE, os.path.join(PANEL, 'sheet.jsonl'), os.path.join(PANEL, 'sheet.v2.jsonl'), LP.V3_PANEL)
# build_mode / build_l4 take their default paths at def time, so pass them explicitly
if stub:
    for p in (LP.MODE_ROWS, LP.L4_ROWS, LP.L4R1_ROWS):
        if not os.path.exists(p):
            open(p, 'w').close()
    print('NON-FAITHFUL: stubbed (empty) MODE_ROWS, L4_ROWS, L4R1_ROWS')

def sha_all():
    for root in (PANEL, DIAG, LEARN):
        for n in sorted(os.listdir(root)):
            p = os.path.join(root, n)
            print('  sha256', hashlib.sha256(open(p, 'rb').read()).hexdigest(), os.path.relpath(p, base))

if stage == 'panel-v1': P.main(v2=False)
elif stage == 'panel-v2': P.main(v2=True)
elif stage == 'panel-v3': PV3.main()
elif stage == 'probe': SP.build()
elif stage == 'build': LP.build()
elif stage == 'build-mode': LP.build_mode(LP.MODE_ROWS)
elif stage == 'build-l3': LP.build_l3()
elif stage == 'build-l4': LP.build_l4(LP.L4R1_ROWS)
elif stage == 'build-l5': LP.build_l5()
else: raise SystemExit('unknown stage')
print('--- files in', base)
sha_all()
