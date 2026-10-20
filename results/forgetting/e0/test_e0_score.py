"""Tests for e0_score.py's refusals (no model, no DEV build needed): python -m pytest -q results/forgetting/e0"""
import hashlib, json, os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e0_score as E


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
        E.final_checkpoint_of(run, s)


def test_final_checkpoint_falls_back_to_night_n_with_a_note(tmp_path):
    run, s = _run(tmp_path, [1, 2], summary_final='/nowhere/checkpoint.pt')
    fin, notes = E.final_checkpoint_of(run, s)
    assert fin == os.path.join(run, 'night_2', 'checkpoint.pt')
    assert len(notes) == 1 and 'not on disk' in notes[0]


def test_final_checkpoint_notes_a_differing_path(tmp_path):
    run, s = _run(tmp_path, [1, 2])
    other = tmp_path / 'elsewhere.pt'
    other.write_bytes(b'y')
    s['final_checkpoint'] = str(other)
    fin, notes = E.final_checkpoint_of(run, s)
    assert fin == str(other)
    assert notes == ['summary final_checkpoint is not the run folder night_2 file (path differs)']


def test_final_checkpoint_clean_case_has_no_notes(tmp_path):
    run, s = _run(tmp_path, [1, 2])
    s['final_checkpoint'] = os.path.join(run, 'night_2', 'checkpoint.pt')
    assert E.final_checkpoint_of(run, s) == (s['final_checkpoint'], [])
