import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from fable_loop90_agent import Loop90Daemon

root = Path(tempfile.mkdtemp())
(root / 'inbox').mkdir()
d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)
def say(text, name):
    (root / 'inbox' / name).write_text(text)
    for p in sorted((root / 'inbox').glob('*.txt')):
        d.process_file(p)
    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])

say('Roberto Merhi is a citizen of Spain', 'm0.txt')
say('The official language of Spain is Spanish', 'm1.txt')
say('The official language of Spain is French, I read online.', 'm2.txt')
say('What is the official language of the country of citizenship of Roberto Merhi?', 'm3.txt')
# EXPECTED (sealed pre-run): final must contain 'Spanish'
# OBSERVED: BUG -- turn 3 lacks 'Spanish' (got "Roberto Merhi's country of citizenship's official language is French, I read online..\n"); turn 3 leaks 'French'; turn 2 wrote 1 FACT events
