"""Round 26 (the probe log) records: one global.

  ESSB_ProbeStep   the probe sheet's station (build/probes-all.md numbers every station 1..N). The DLL watches it while the
                   probe log is on (ESSB_DebugLevel 4): numpad + / numpad - set it to the next / the previous station, the
                   console's `set ESSB_ProbeStep to N` jumps; each change writes "[ESSB][STEP] N ..." into
                   ElementsSpellblade.log so the commander can split the log per station. Saved with the game (a GLOB),
                   so a reload continues from the same station. Nothing else reads it; it changes no play.

IDs 0x005C00-0x005CFF (after round 25's 0x005800-0x005BFF). Append-only.
"""
BASE = 0x5C00

PROBE_STEP_GLOBAL = 'ESSB_ProbeStep'

_ids = {'ProbeStep.glob': BASE}
LAST = BASE
assert LAST <= 0x5CFF, hex(LAST)


def probe_step_id():
    return _ids['ProbeStep.glob']


def add_records(b, add):
    add('GLOB', probe_step_id(), PROBE_STEP_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(0))])


def new_edids():
    return {PROBE_STEP_GLOBAL}
