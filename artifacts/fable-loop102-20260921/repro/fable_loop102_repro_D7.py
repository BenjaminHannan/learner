import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from fable_loop102_agent import Loop102Daemon as Loop90Daemon

root = Path(tempfile.mkdtemp())
(root / 'inbox').mkdir()
d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)
def say(text, name):
    (root / 'inbox' / name).write_text(text)
    for p in sorted((root / 'inbox').glob('*.txt')):
        d.process_file(p)
    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])

say('The capital of Poland is Warsaw since 1596.', 'm0.txt')
say("Who is Poland's capital?", 'm1.txt')
# EXPECTED (sealed pre-run): final must contain 'Warsaw'
# OBSERVED: BUG -- turn 1 leaks 'since 1596'
