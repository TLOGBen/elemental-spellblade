"""Writes build/fix27_native_history.py: the round-27 seal of the DLL sources, the native tests, the generator modules,
the verifiers and the probe judge.

Run after the round's native / generator / verifier code is final (python -B build/fix27_native_history_gen.py). Every
covered file is bound to its bytes by sha256: unchanged files must equal the pre-fix27 snapshot; changed and added files
carry the reason written here and their sha256. Any later edit, a new file in the covered folders or a missing file fails
the build until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix27-snapshot'
NOW = ROOT

R27 = 'Round 27（DLL 0.27.0）'
REASONS = {}   # filled by build/fix27_reasons.py (one table for this seal and the ledger)


def _load_reasons():
    import fix27_reasons
    REASONS.update(fix27_reasons.NATIVE)


VERIFIERS = ('fix6_verify.py', 'fix11_verify.py', 'fix16_verify.py', 'fix21_verify.py', 'fix22_verify.py', 'fix23_verify.py',
             'fix24_verify.py', 'fix25_verify.py', 'fix26_verify.py', 'fix21_identity.py',
             'fix22_history.py', 'fix22_history_gen.py', 'fix22_history_template.py', 'fix22_native_history.py',
             'fix22_native_history_gen.py', 'fix22_native_history_template.py', 'fix23_history.py', 'fix23_history_gen.py',
             'fix23_history_template.py', 'fix23_native_history.py', 'fix23_native_history_gen.py', 'fix23_native_history_template.py',
             'fix24_history.py', 'fix24_history_gen.py', 'fix24_history_template.py', 'fix24_native_history.py',
             'fix24_native_history_gen.py', 'fix24_native_history_template.py',
             'fix25_history.py', 'fix25_history_gen.py', 'fix25_history_template.py', 'fix25_native_history.py',
             'fix25_native_history_gen.py', 'fix25_native_history_template.py',
             'fix26_history.py', 'fix26_history_gen.py', 'fix26_history_template.py', 'fix26_native_history.py', 'fix26_native_history_gen.py',
             'fix26_native_history_template.py', 'fix27_verify.py', 'fix27_reasons.py', 'fix27_history.py', 'fix27_history_gen.py',
             'fix27_history_template.py', 'fix27_native_history_gen.py', 'fix27_native_history_template.py', 'fix28_verify.py',
             'fix29_verify.py')   # round 29


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((NOW / 'native' / part).glob('*.*'))
    files += [NOW / 'native/CMakeLists.txt', NOW / 'native/build.py']
    files += sorted(p for p in NOW.glob('*.py'))
    files += [NOW / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py', 'fix23_records.py', 'fix23_reference.py', 'fix23_fixture.py',
                                             'fix24_records.py', 'fix24_reference.py', 'fix24_fixture.py',
                                             'fix25_records.py', 'fix25_reference.py', 'fix25_fixture.py',
                                             'fix26_records.py', 'fix26_format.py', 'probe-judge.py', 'fix27_visuals.py',
                                             'fix27_records.py', 'fix28_records.py', 'papyrus_budget.py',
                                             'fix29_records.py')]   # round 29
    # The verifiers too (a weakened check would otherwise pass unseen). This seal cannot hold itself;
    # build/fix26_native_history.py is regenerated last.
    files += [NOW / f'build/{n}' for n in VERIFIERS]
    return [p.relative_to(NOW).as_posix() for p in files]


def before_sha(rel):
    snap = SNAP / rel
    return hashlib.sha256(snap.read_bytes()).hexdigest() if snap.is_file() else None


def main():
    _load_reasons()
    rows = []
    for rel in covered():
        now = hashlib.sha256((NOW / rel).read_bytes()).hexdigest()
        before = before_sha(rel)
        if before == now:
            rows.append((rel, 'unchanged', now, ''))
            continue
        why = REASONS.get(rel)
        assert why, (rel, 'changed in round 27 but no reason is written in build/fix27_reasons.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix27_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix27_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix27_native_history: {counts}')


if __name__ == '__main__':
    main()
