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

say('The author of Fasti is Ovid', 'm0.txt')
say('Ovid was born in the city of Sulmona', 'm1.txt')
say('forget Ovid place_of_birth', 'm2.txt')
say('Where was the author of Fasti born?', 'm3.txt')
# EXPECTED (sealed pre-run): flagged turns must abstain
# OBSERVED: BUG -- turn 3 leaks 'Sulmona'; turn 3 should abstain (got "Fasti's author's place of birth is Sulmona.\n")
