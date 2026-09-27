"""Round 26 seal of the DLL sources, the native tests, the generator modules, the verifiers and the probe judge. GENERATED
by build/fix26_native_history_gen.py from this template -- write reasons there, never edit the digests here.

FILES  path -> (state, sha256 now, why): 'unchanged' files equal the pre-fix26 snapshot (.codex/pre-fix26-snapshot, taken
       before any round-26 edit); 'changed' / 'added' ones carry the declared reason. verify() fails on any byte that
       differs, on a covered file that is missing and on a file in native/include, native/src or native/tests that is not
       listed. build/fix25_native_history.py checks the snapshot (round 25 as shipped) only after this proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix26-snapshot'

FILES = {
#FILES#}

FOLDERS = ('native/include', 'native/src', 'native/tests')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(rel: str, data: bytes) -> None:
    state, sha, why = FILES[rel]
    assert _sha(data) == sha, (rel, state, 'differs from the sealed bytes (edited after sealing; regenerate with a reason)')


def verify() -> dict:
    root = ROOT
    for rel in FILES:
        path = root / rel
        assert path.is_file(), (rel, 'sealed file is missing')
        check(rel, path.read_bytes())
    for folder in FOLDERS:
        for path in (root / folder).glob('*.*'):
            rel = path.relative_to(root).as_posix()
            assert rel in FILES, (rel, 'new file in a sealed folder, not in the seal')
    return {s: sum(1 for v in FILES.values() if v[0] == s) for s in ('unchanged', 'changed', 'added')}


# Silent edits (a constant or a condition changed without resealing): each must fail check().
SILENT_EDITS = [
    ('native/include/Trace.h', 'inline constexpr std::size_t kMaxLine = 480;', 'inline constexpr std::size_t kMaxLine = 481;'),
    ('native/include/Trace.h', 'inline constexpr float kLevel = 4.0f;', 'inline constexpr float kLevel = 3.0f;'),
    ('native/src/Plugin.cpp', 'LogThreadOnce(Probe::kHurtTask, "hurt task");', 'LogThreadOnce(Probe::kHurt, "hurt task");'),
    ('native/include/StatusEngine.h', 'why(i, Pick::kNeutral);', 'why(i, Pick::kFar);'),
    ('build/fix26_format.py', "B = r'[01]'", "B = r'[012]'"),
    ('build/probe-judge.py', "if not 0.88 <= r <= 0.99:", "if not 0.80 <= r <= 0.99:"),
    ('build/fix26_records.py', 'BASE = 0x5C00', 'BASE = 0x5C01'),
]


def self_check() -> dict:
    counts = verify()
    caught = []
    for rel, old, new in SILENT_EDITS:
        data = (ROOT / rel).read_bytes()
        assert old.encode('utf-8') in data, (rel, old)
        try:
            check(rel, data.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
        except AssertionError:
            caught.append(rel)
            continue
        raise AssertionError(('silent edit not caught', rel, old))
    return dict(counts, silent_edits_caught=caught)
