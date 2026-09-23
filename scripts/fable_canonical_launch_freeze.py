"""Freeze the launch manifest for Astra's canonical-operator screen (Fable, 2026-09-19 EDT).

Astra built the screen, ran the outcome-blind rehearsal and wrote the pre-launch amendment, then
was stopped by Ben before writing `astra_canonical_operator_launch.json`. This additive script
writes exactly the manifest Astra's runner/report expect; it changes no registered file and
runs no model.
"""
from __future__ import annotations
import datetime, json, sys
from pathlib import Path

import astra_canonical_operator_run as R  # imports the full source closure
P, C, OUT, ROOT = R.P, R.C, R.OUT, R.ROOT


def main():
    R.A.data.bootstrap()
    import premonition.toy_ladder  # noqa: F401  (closure)
    files = set()
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and Path(path).is_absolute() and Path(path).exists() and Path(path).resolve().is_relative_to(ROOT) and Path(path).suffix == '.py':
            files.add(Path(path).resolve())
    files |= {ROOT/'scripts/astra_canonical_operator_report.py', ROOT/'tests/test_astra_canonical_operator.py',
              ROOT/'scripts/fable_canonical_launch_freeze.py', ROOT/'runtime.local.json',
              ROOT/'design/v3/17-canonical-operator-screen.md'}
    for path in OUT.rglob('*'):
        if path.is_file() and path.name != 'astra_canonical_operator_launch.json':
            files.add(path.resolve())
    panels = json.loads((OUT/'astra_canonical_operator_panels.json').read_text())
    for row in panels.values():
        assert C.sha(row['path']) == row['sha256'], row['path']
        files.add(Path(row['path']).resolve())
    exclusion = OUT/'astra_canonical_operator_panels/forbidden-semantics.json'
    manifest = dict(
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        frozen_by='Fable (Claude) after Ben stopped Astra before launch; design, predictions, amendment, code, panels and rehearsal are Astra\'s and unchanged',
        schedule=dict(updates=6000, training_seconds=1200, work_seconds=1740, terminate_seconds=1770,
                      visits_per_update=16, parallel_seeds=[0, 1, 2]),
        exclusion_path=str(exclusion), panels=panels,
        torch=R.torch.__version__, python=sys.version,
        files={str(p.relative_to(ROOT)): C.sha(p) for p in sorted(files)})
    C.write_new(OUT/'astra_canonical_operator_launch.json', manifest)
    print(len(manifest['files']), 'files frozen;', C.sha(OUT/'astra_canonical_operator_launch.json'))


if __name__ == '__main__':
    main()
