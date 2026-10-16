#!/bin/bash
# DRYRUN evidence: python3 -I import checks and --help on the assembled tree (the frozen copy the job runs from)
PY=/dev/shm/ptcdry/venv/bin/python
CODE=$(ls -d /dev/shm/ptcdry/J/work/code/8aPTC3S-pc-* | head -1)
echo "tree: $CODE"
cd /dev/shm/ptcdry || exit 1
echo "--- python -I imports (isolated: no cwd, no PYTHONPATH, no user site; the tree is added by sys.path.insert in the -c string)"
$PY -I -c "
import sys
sys.path.insert(0, '$CODE')
import importlib
for m in ('custom_io.local_runner', 'custom_io.g8a.job', 'custom_io.g8a.get_data', 'custom_io.g8a.configs', 'custom_io.g8a.caps', 'custom_io.g8a.pool', 'custom_io.capcount', 'custom_io.models.plain_tf_steps', 'custom_io.models.plain_lm', 'custom_io.models.eg', 'custom_io.train'):
    importlib.import_module(m)
    print('import ok', m)
import custom_io.g8a.configs as C
print('PTC_ARM in ALL_ARMS:', C.PTC_ARM in C.ALL_ARMS, '| MODEL_OF PTC:', C.MODEL_OF[C.PTC_ARM])
print('ptc_cfg calc_train:', C.ptc_cfg('3M', {'eg_embed': True}).get('calc_train'))
"
echo "rc=$?"
echo "--- python -m custom_io.g8a.job --help (cwd = the frozen tree, as the runner does)"
cd $CODE && $PY -m custom_io.g8a.job --help | head -12
echo "rc=${PIPESTATUS[0]}"
echo "--- python -m custom_io.g8a.get_data --help"
$PY -m custom_io.g8a.get_data --help | head -8
echo "rc=${PIPESTATUS[0]}"
