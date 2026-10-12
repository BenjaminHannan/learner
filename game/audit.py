"""Post-run audit of a game-world run (GW5), from RUN_DIR/log.jsonl.

  python -m game.audit RUN_DIR      (prints the report and writes RUN_DIR/audit.json; exit 1 when a problem is found)

Checks every 'row' event. A game row (kind 'game'): world_seed is not sealed and not a quiz world of this run
(practice_seed(seed, 0, i)); day >= 1 and world_seed == practice_seed(seed, day, i) for some i < episodes_per_day;
unlock_step - credit_window < step <= unlock_step (rows with kept_by 'guess', 'pg' or 'distil' have no unlock and skip this one); steps == []; answer is one of the 17 words; source is own, explore
or invalid. A diary row has source 'diary'. Any other row is a problem. The constants sha256s in the start event must
equal the files' sha256 now. proved_wrong = a sealed or quiz world in a training row, or a changed constants file.
"""
import hashlib
import json
import os
import sys
from collections import Counter

from game import play

SOURCES = frozenset({'own', 'explore', 'invalid'})
DOMAIN_CONST = os.path.join(os.path.dirname(play.HERE), 'domain', 'constants.json')


def sha256_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def start_shas(start):
    """-> (domain sha, game sha) as the start event logged them. choice: names tried in turn, since the mode's log
    names are not fixed here: constants_sha256 / domain_constants_sha256, game_constants_sha256."""
    d = start.get('domain_constants_sha256', start.get('constants_sha256'))
    g = start.get('game_constants_sha256')
    return d, g


def audit_events(events, domain_sha=None, game_sha=None):
    start = [e for e in events if e['event'] == 'start']
    problems, sealed_quiz, const_changed = [], [], False
    if len(start) != 1:
        return dict(ok=False, proved_wrong=False, problems=[f'{len(start)} start events'], rows=0, by_source={})
    st = start[0]
    seed = int(st['seed'])
    cons = play.load_constants()[0]
    domain_sha = domain_sha or sha256_file(DOMAIN_CONST)
    game_sha = game_sha or sha256_file(play.CONST_PATH)
    logged_d, logged_g = start_shas(st)
    if logged_d != domain_sha:
        const_changed = True
        problems.append(f'domain constants sha256: log {logged_d} now {domain_sha}')
    if logged_g != game_sha:
        const_changed = True
        problems.append(f'game constants sha256: log {logged_g} now {game_sha}')
    epd = play.load_constants()[0]['episodes_per_day']
    quiz = {play.practice_seed(seed, 0, i) for i in range(100)}
    window = cons['credit_window']
    rows = [e for e in events if e['event'] == 'row']
    for r in rows:
        rid = r.get('id')
        if r.get('kind') == 'game':
            w = r.get('world_seed')
            if w is None:
                problems.append(f'{rid}: no world_seed')
                continue
            if play.is_sealed(w) or w in quiz:
                sealed_quiz.append(rid)
                problems.append(f'{rid}: world {w} is a {"sealed" if play.is_sealed(w) else "quiz"} world')
            day = r.get('day')
            if not isinstance(day, int) or day < 1 or not any(w == play.practice_seed(seed, day, i) for i in range(epd)
                                                              if day < 100):
                problems.append(f'{rid}: world {w} is not a practice world of day {day}')
            t, u = r.get('step'), r.get('unlock_step')
            if r.get('kept_by') in ('guess', 'pg', 'distil'):
                if t is None:
                    problems.append(f'{rid}: guess row has no step')
            elif t is None or u is None or not (u - window < t <= u):
                problems.append(f'{rid}: step {t} outside the credit window of unlock step {u}')
            if r.get('steps') != []:
                problems.append(f'{rid}: steps not empty')
            if r.get('answer') not in play.WORDS:
                problems.append(f'{rid}: answer {r.get("answer")!r} is not an action word')
            if r.get('source') not in SOURCES:
                problems.append(f'{rid}: source {r.get("source")!r}')
        elif r.get('source') == 'diary':
            pass
        else:
            problems.append(f'{rid}: kind {r.get("kind")!r} source {r.get("source")!r} is neither game nor diary')
    return dict(ok=not problems, proved_wrong=bool(sealed_quiz) or const_changed, problems=problems[:200],
                n_problems=len(problems), sealed_or_quiz_rows=sealed_quiz[:50], constants_changed=const_changed,
                rows=len(rows), by_source=dict(Counter(r.get('source') for r in rows)),
                by_kind=dict(Counter(r.get('kind') for r in rows)), seed=seed,
                constants=dict(domain_now=domain_sha, game_now=game_sha, domain_log=logged_d, game_log=logged_g))


def audit_run(run_dir):
    with open(os.path.join(run_dir, 'log.jsonl'), encoding='utf-8') as f:
        events = [json.loads(line) for line in f if line.strip()]
    return audit_events(events)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    assert len(args) == 1, 'usage: python -m game.audit RUN_DIR'
    rep = audit_run(args[0])
    print(json.dumps(rep, indent=1, sort_keys=True))
    with open(os.path.join(args[0], 'audit.json'), 'w') as f:
        json.dump(rep, f, indent=1, sort_keys=True)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
