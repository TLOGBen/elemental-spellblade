"""Round 23 (N4, your resources and the hits you take): the declared changes the historical verifiers accept. GENERATED
by build/fix23_history_gen.py from this template -- edit the reasons there, never the digests here.

Round 23 deleted ESSBGuard.OnHitEx and the Papyrus self-counter paths (ruling R6) and moved your resources and the hits
you take into DLL-applied engine effects (native/include/SelfLayer.h, Hurt.h). The verifiers of rounds 6-22 exercise the
scripts as they were; the round-22 seal (build/fix22_history.py) now runs on the pre-fix23 snapshot
(.codex/pre-fix23-snapshot/src, taken before any round-23 edit), and this module proves that today's scripts differ from
that snapshot ONLY by the changes declared below, each bound to the code by digest (comment-stripped body, sha256[:16],
build/fix21_history.digest):

  CHANGED     (script, function) -> (why, before, after)
  REMOVED     (script, function) -> (why, before)
  ADDED       (script, function) -> (why, after)
  PROPERTIES  script -> (why, code lines added outside functions, code lines removed)
  FILES       whole scripts removed or added -> (why, sha256 of the file, 'removed' | 'added')

Anything else fails the build: an undeclared edit, a declared function edited after sealing, a removed script that
comes back. legacy_source() hands the older seals and verifiers the snapshot only after that proof; the chain is
fix21 (20 -> 21, "now" = pre-fix22) -> fix22 (21 -> 22, "now" = pre-fix23) -> this one (22 -> 23, "now" = src/).
The round-23 behaviour itself is checked by build/fix23_verify.py and the native self tests.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [p for p in (str(ROOT / 'build'),) if p not in sys.path]
SNAPSHOT = ROOT / '.codex/pre-fix23-snapshot'

import fix21_history as _h21

CHANGED = {
#CHANGED#}

REMOVED = {
#REMOVED#}

ADDED = {
#ADDED#}

PROPERTIES = {
#PROPERTIES#}

FILES = {
#FILES#}

digest = _h21.digest
code = _h21.code
functions = _h21.functions
body_of = _h21.body_of
outside_functions = _h21.outside_functions


def snapshot_text(script: str) -> str:
    return (SNAPSHOT / 'src' / script).read_text(encoding='utf-8-sig')


def current_dir() -> Path:
    """Today's scripts (a later round moves this to its own pre-round snapshot, as round 23 did for build/fix22_history.py)."""
    return ROOT / 'src'


def current_text(script: str) -> str:
    return (current_dir() / script).read_text(encoding='utf-8-sig')


def round23_diff(script: str, text: str | None = None) -> dict:
    """pre-fix23 snapshot -> now (or `text`) for one script: every function the same, comments only, or declared
    with matching digests; code outside functions the same apart from comments, or exactly the declared lines."""
    old_text = snapshot_text(script)
    new_text = current_text(script) if text is None else text
    old_fns, new_fns = functions(old_text), functions(new_text)
    out = {}
    for fn in sorted(set(old_fns) | set(new_fns)):
        before, now = old_fns.get(fn), new_fns.get(fn)
        if before is None:
            decl = ADDED.get((script, fn))
            assert decl is not None, (script, fn, 'added in round 23 but not declared in ADDED')
            assert digest(now) == decl[1], (script, fn, 'added body differs from the declared one')
            out[fn] = 'added'
        elif now is None:
            decl = REMOVED.get((script, fn))
            assert decl is not None, (script, fn, 'deleted in round 23 but not declared in REMOVED')
            assert digest(before) == decl[1], (script, fn, 'pre-fix23 body is not the one the removal was declared against')
            out[fn] = 'removed'
        elif before == now:
            continue
        elif code(before) == code(now):
            out[fn] = 'comments'
        else:
            decl = CHANGED.get((script, fn))
            assert decl is not None, (script, fn, 'changed in round 23 but not declared in CHANGED')
            assert digest(before) == decl[1], (script, fn, 'pre-fix23 body is not the one the declaration was made against')
            assert digest(now) == decl[2], (script, fn, 'body differs from the declared round-23 change (edited after sealing)')
            out[fn] = 'declared'
    old_lines, new_lines = outside_functions(old_text).splitlines(), outside_functions(new_text).splitlines()
    if old_lines != new_lines:
        decl = PROPERTIES.get(script)
        assert decl is not None, (script, 'code outside functions changed in round 23 but not declared')
        added = tuple(x for x in new_lines if x not in old_lines)
        removed = tuple(x for x in old_lines if x not in new_lines)
        assert (added, removed) == (decl[1], decl[2]), (script, 'lines outside functions differ from the declared ones',
                                                        added, removed)
        out['<properties>'] = 'declared'
    return out


_VERIFIED = None


def verify() -> dict:
    """Every script: whole-file removals / additions by sha256, everything else through round23_diff."""
    global _VERIFIED
    if _VERIFIED is not None:
        return _VERIFIED
    old = {p.name for p in (SNAPSHOT / 'src').glob('*.psc')}
    new = {p.name for p in current_dir().glob('*.psc')}
    report = {}
    for name in sorted(old | new):
        if name not in old or name not in new:
            decl = FILES.get(name)
            assert decl is not None, (name, 'script added or removed in round 23 but not declared in FILES')
            path = SNAPSHOT / 'src' / name if name in old else current_dir() / name
            assert decl[2] == ('removed' if name in old else 'added'), (name, 'declared the other way round')
            assert hashlib.sha256(path.read_bytes()).hexdigest() == decl[1], (name, 'file differs from the declared one')
            report[name] = decl[2]
            continue
        changes = round23_diff(name)
        if changes:
            report[name] = changes
    for (script, fn) in list(CHANGED) + list(REMOVED) + list(ADDED):
        assert script in report and fn in report[script], (script, fn, 'declared but not a round-23 change')
    _VERIFIED = report
    return report


def legacy_source() -> Path:
    """The scripts round 22 shipped: the pre-fix23 snapshot, once verify() tied it to today (build/fix22_history.py reads it)."""
    verify()
    return SNAPSHOT / 'src'


# Silent edits (a number or a call changed inside a declared, an added or an untouched function): each must fail.
SILENT_EDITS = [
    ('ESSBController.psc', 'OnFormClosed', 'SetSyncKeep(syncBefore, 60)', 'SetSyncKeep(syncBefore, 30)'),
    ('ESSBController.psc', 'OnESSBKnock', 'ApplyUtil(0, 30.0, 3, target)', 'ApplyUtil(0, 45.0, 3, target)'),
    ('ESSBReactions.psc', 'End', 'mult * (1.0 + charged)', 'mult * (1.5 + charged)'),
    ('ESSBElem.psc', 'Discharge', 'amount = amount * afCritMult', 'amount = amount * 2.5'),
    ('ESSBGuard.psc', 'Setup', 'PO3_Events_Alias.UnregisterForAllHitEventsEx(Self)', 'PO3_Events_Alias.RegisterForHitEventEx(Self)'),
]


def self_check() -> dict:
    """Every declaration is true now, and the silent edits are caught."""
    verify()
    faults = []
    for script, fn, old, new in SILENT_EDITS:
        text = current_text(script)
        body = body_of(text, fn)
        assert body is not None and old in body, (script, fn, old)
        mutated = text.replace(body, body.replace(old, new, 1), 1)
        try:
            round23_diff(script, mutated)
        except AssertionError:
            faults.append(f'{script}:{fn}')
            continue
        raise AssertionError(('silent edit not caught', script, fn, old, new))
    return dict(changed=len(CHANGED), removed=len(REMOVED), added=len(ADDED), properties=len(PROPERTIES),
                files=len(FILES), silent_edits_caught=faults)
