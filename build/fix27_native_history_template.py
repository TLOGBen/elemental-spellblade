"""Round 27 seal of the DLL sources, the native tests, the generator modules, the verifiers and the probe judge. GENERATED
by build/fix27_native_history_gen.py from this template -- write reasons there, never edit the digests here.

FILES  path -> (state, sha256 now, why): 'unchanged' files equal the pre-fix27 snapshot (.codex/pre-fix27-snapshot, taken
       before any round-27 edit); 'changed' / 'added' ones carry the declared reason. verify() fails on any byte that
       differs, on a covered file that is missing and on a file in native/include, native/src or native/tests that is not
       listed. build/fix26_native_history.py checks the snapshot (round 26 as shipped) only after this proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix27-snapshot'

FILES = {
#FILES#}

FOLDERS = ('native/include', 'native/src', 'native/tests')


def base() -> Path:
    """Today's bytes (a later round moves this to its own pre-round snapshot, as round 27 did for build/fix26_native_history.py)."""
    return ROOT


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(rel: str, data: bytes) -> None:
    state, sha, why = FILES[rel]
    assert _sha(data) == sha, (rel, state, 'differs from the sealed bytes (edited after sealing; regenerate with a reason)')


def verify() -> dict:
    root = base()
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
    ('native/include/Registry.h', 'inline constexpr float kExpirySlack = 0.35f;', 'inline constexpr float kExpirySlack = 0.5f;'),
    ('native/include/Runtime.h', 'inline constexpr std::uint64_t kHurtMaxWaitMs = 150;', 'inline constexpr std::uint64_t kHurtMaxWaitMs = 1500;'),
    ('native/src/Plugin.cpp', 'SwitchWork(*player, p.kind, facts.active ? facts.current : 0, p.element, 0);', 'SwitchWork(*player, p.kind, 0, p.element, 0);'),
]


def self_check() -> dict:
    counts = verify()
    caught = []
    for rel, old, new in SILENT_EDITS:
        data = (base() / rel).read_bytes()
        assert old.encode('utf-8') in data, (rel, old)
        try:
            check(rel, data.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
        except AssertionError:
            caught.append(rel)
            continue
        raise AssertionError(('silent edit not caught', rel, old))
    return dict(counts, silent_edits_caught=caught)
