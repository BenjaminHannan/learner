"""Tests for e0_score.py's refusals (no model, no DEV build, no torch: night discovery is passed in as a plain glob):
python -m pytest -q results/forgetting/e0"""
import glob, hashlib, json, os, re, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e0_score as E


def NC(run):
    """night discovery for the tests, as domain/score.py night_checkpoints does it, without importing it (it pulls in torch)."""
    return sorted((int(re.search(r'night_(\d+)', p).group(1)), p) for p in glob.glob(os.path.join(run, 'night_*', 'checkpoint.pt')))


def _file(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    return str(p), hashlib.sha256(p.read_bytes()).hexdigest()


def test_check_devs_refuses_a_mismatched_big_dev(tmp_path):
    small, s_sha = _file(tmp_path, 'small.jsonl', [{'id': i} for i in range(4)])
    big, b_sha = _file(tmp_path, 'big.jsonl', [{'id': i} for i in range(20)])
    other, _ = _file(tmp_path, 'other.jsonl', [{'id': 100 + i} for i in range(20)])   # same length, different rows
    assert E.check_devs(small, big, s_sha, b_sha) == (s_sha, b_sha)
    with pytest.raises(SystemExit, match='big DEV'):
        E.check_devs(small, other, s_sha, b_sha)


def test_check_devs_refuses_a_mismatched_small_dev(tmp_path):
    small, s_sha = _file(tmp_path, 'small.jsonl', [{'id': i} for i in range(4)])
    big, b_sha = _file(tmp_path, 'big.jsonl', [{'id': i} for i in range(20)])
    with pytest.raises(SystemExit, match='small DEV'):
        E.check_devs(big, big, s_sha, b_sha)


def test_check_devs_default_shas_refuse_any_other_file(tmp_path):
    small, _ = _file(tmp_path, 'small.jsonl', [{'id': i} for i in range(4)])
    big, _ = _file(tmp_path, 'big.jsonl', [{'id': i} for i in range(6800)])   # a 6,800-row file is not enough: the content must be the ship DEV
    with pytest.raises(SystemExit):
        E.check_devs(small, big)


def _run(tmp_path, nights, summary_final=None, n=None):
    run = tmp_path / 'run'
    for k in nights:
        (run / f'night_{k}').mkdir(parents=True)
        (run / f'night_{k}' / 'checkpoint.pt').write_bytes(b'x')
    s = {'nights_run': n if n is not None else max(nights), 'parent': 'P'}
    if summary_final is not None:
        s['final_checkpoint'] = summary_final
    return str(run), s


def test_final_checkpoint_refuses_missing_nights(tmp_path):
    run, s = _run(tmp_path, [1, 3], n=3)
    with pytest.raises(SystemExit, match=r'missing night checkpoints \[2\]'):
        E.final_checkpoint_of(run, s, NC)


def test_final_checkpoint_falls_back_to_night_n_with_a_note(tmp_path):
    run, s = _run(tmp_path, [1, 2], summary_final='/nowhere/checkpoint.pt')
    fin, notes = E.final_checkpoint_of(run, s, NC)
    assert fin == os.path.join(run, 'night_2', 'checkpoint.pt')
    assert len(notes) == 1 and 'not on disk' in notes[0]


def test_final_checkpoint_notes_a_differing_path(tmp_path):
    run, s = _run(tmp_path, [1, 2])
    other = tmp_path / 'elsewhere.pt'
    other.write_bytes(b'y')
    s['final_checkpoint'] = str(other)
    fin, notes = E.final_checkpoint_of(run, s, NC)
    assert fin == str(other)
    assert notes == ['summary final_checkpoint is not the run folder night_2 file (path differs)']


def test_final_checkpoint_notes_ignored_extra_nights(tmp_path):
    run, s = _run(tmp_path, [1, 2, 3, 4], n=3)
    fin, notes = E.final_checkpoint_of(run, s, NC)
    assert fin == os.path.join(run, 'night_3', 'checkpoint.pt')
    assert notes[0] == 'night checkpoints after nights_run=3 were ignored: [4]', notes


def test_note_wording_matches_analyze():
    """Each note e0 writes is worded as domain/analyze.py words it: the same template appears in BOTH sources (analyze names N, e0 names n)."""
    here = os.path.dirname(os.path.abspath(__file__))
    src_a = open(os.path.join(here, '..', '..', '..', 'domain', 'analyze.py')).read()
    src_e = open(os.path.join(here, 'e0_score.py')).read()
    for t in ("missing night checkpoints {missing}", "night checkpoints after nights_run={N} were ignored: {extra}",
              "summary final_checkpoint not on disk ({fin}); used the night_{N} file in the run folder",
              "'summary final_checkpoint is not the run folder night_%d file (path differs)' % N"):
        assert t in src_a, ('analyze', t)
        assert t.replace('{N}', '{n}').replace('% N', '% n') in src_e, ('e0', t)


def test_nights_run_zero_or_missing_is_a_named_refusal(tmp_path):
    run, s = _run(tmp_path, [1])
    with pytest.raises(SystemExit, match='nights_run is 0'):
        E.final_checkpoint_of(run, dict(s, nights_run=0), NC)
    with pytest.raises(SystemExit, match='has no nights_run'):
        E.final_checkpoint_of(run, {k: v for k, v in s.items() if k != 'nights_run'}, NC)


def test_write_json_atomic_replaces_whole_file(tmp_path):
    p = str(tmp_path / 'e0.json')
    E.write_json_atomic({'runs': {'a': 1}}, p)
    E.write_json_atomic({'runs': {'b': 2}}, p)
    assert json.load(open(p)) == {'runs': {'b': 2}} and not os.path.exists(p + '.tmp')


def test_resolve_runs_checks_every_run_before_scoring(tmp_path):
    good, s = _run(tmp_path, [1, 2])
    par = tmp_path / 'parent.pt'
    par.write_bytes(b'p')
    s['parent'] = str(par)
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(s))
    plan = E.resolve_runs([good], NC)
    assert plan[0][0] == good and plan[0][2] == os.path.join(good, 'night_2', 'checkpoint.pt')
    with pytest.raises(SystemExit, match='no summary.json'):
        E.resolve_runs([good, str(tmp_path / 'absent')], NC)
    s2 = dict(s, parent=str(tmp_path / 'gone.pt'))
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(s2))
    with pytest.raises(SystemExit, match='not on disk'):
        E.resolve_runs([good], NC)


def test_check_devs_names_a_missing_file(tmp_path):
    small, s_sha = _file(tmp_path, 'small.jsonl', [{'id': 1}])
    with pytest.raises(SystemExit, match='big DEV .* does not exist'):
        E.check_devs(small, str(tmp_path / 'nope.jsonl'), s_sha, s_sha)
    with pytest.raises(SystemExit, match='CUSTOM_IO_DATA'):
        E.check_devs(str(tmp_path / 'nope.jsonl'), small, s_sha, s_sha)


def test_resolve_runs_parent_per_run_and_per_tool_refusal(tmp_path):
    good, s = _run(tmp_path, [1, 2])
    (tmp_path / 'run' / 'p.pt').write_bytes(b'p')   # parent recorded relative to the run folder
    s['parent'] = 'p.pt'
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(s))
    run, ss, fin, notes = E.resolve_runs([good], NC)[0]
    assert ss['parent'] == os.path.join(good, 'p.pt') and ss['parent_as_recorded'] == 'p.pt' and 'resolved against the run folder' in notes[-1]
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(dict(s, parent='nowhere/x.pt')))
    with pytest.raises(SystemExit, match='not on disk'):
        E.resolve_runs([good], NC)
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(dict(s, addon='per_tool')))
    with pytest.raises(SystemExit, match='per_tool'):
        E.resolve_runs([good], NC)


def test_relative_parent_resolves_against_base_and_smoke_is_refused(tmp_path):
    good, s = _run(tmp_path, [1, 2])
    launch = tmp_path / 'mainbrain'
    (launch / 'art').mkdir(parents=True)
    (launch / 'art' / 'parent.pt').write_bytes(b'p')
    s['parent'] = 'art/parent.pt'   # relative to Main brain's launch folder: not under cwd, not under the run folder
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(s))
    with pytest.raises(SystemExit, match='not on disk'):
        E.resolve_runs([good], NC)
    run, ss, fin, notes = E.resolve_runs([good], NC, base=str(launch))[0]
    assert ss['parent'] == str(launch / 'art' / 'parent.pt') and 'resolved against --base' in notes[-1]
    (tmp_path / 'run' / 'summary.json').write_text(json.dumps(dict(s, smoke=True)))
    with pytest.raises(SystemExit, match='smoke'):
        E.resolve_runs([good], NC, base=str(launch))


def test_check_devs_accepts_a_crlf_copy_with_a_note(tmp_path):
    small, s_sha = _file(tmp_path, 'small.jsonl', [{'id': i} for i in range(3)])
    crlf = tmp_path / 'crlf.jsonl'
    crlf.write_bytes(open(small, 'rb').read().replace(b'\n', b'\r\n'))
    notes = []
    assert E.check_devs(str(crlf), small, s_sha, s_sha, notes=notes) == (s_sha, s_sha)
    assert len(notes) == 1 and 'CRLF' in notes[0]


def test_pinned_small_sha_read_from_source_matches():
    repo = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    assert E.pinned_small_sha(repo) == E.SMALL_SHA


def test_main_refuses_a_bad_repo_and_an_existing_out(tmp_path):
    out = tmp_path / 'e0.json'
    out.write_text('{}')
    with pytest.raises(SystemExit, match='no custom_io/ and domain/'):
        E.main(['RUN', '--repo', str(tmp_path), '--big', 'b', '--out', str(out)])
    repo = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    with pytest.raises(SystemExit, match='exists; pass --overwrite'):
        E.main(['RUN', '--repo', repo, '--big', 'b', '--out', str(out)])


def test_final_checkpoint_clean_case_has_no_notes(tmp_path):
    run, s = _run(tmp_path, [1, 2])
    s['final_checkpoint'] = os.path.join(run, 'night_2', 'checkpoint.pt')
    assert E.final_checkpoint_of(run, s, NC) == (s['final_checkpoint'], [])
