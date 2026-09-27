"""Round 26 (the probe log) records: one global.

  ESSB_ProbeStep   the probe sheet's station (build/probes-all.md numbers every station 1..N). The DLL watches it while the
                   probe log is on (ESSB_DebugLevel 4): numpad + / numpad - set it to the next / the previous station, the
                   console's `set ESSB_ProbeStep to N` jumps; each change writes "[ESSB][STEP] N ..." into
                   ElementsSpellblade.log so the commander can split the log per station. Saved with the game (a GLOB),
                   so a reload continues from the same station. Nothing else reads it; it changes no play.

  ESSB_TrueHudBars round 26c: the MCM switch 「TrueHUD 資源條」 (default 1). 0 = the DLL does no TrueHUD widget work at
                   all (no load, no add; the bars already added are removed), for an A/B without uninstalling TrueHUD.

IDs 0x005C00-0x005CFF (after round 25's 0x005800-0x005BFF). Append-only.
"""
BASE = 0x5C00

PROBE_STEP_GLOBAL = 'ESSB_ProbeStep'
TRUEHUD_GLOBAL = 'ESSB_TrueHudBars'

_ids = {'ProbeStep.glob': BASE, 'TrueHudBars.glob': BASE + 1}
LAST = BASE + 1
assert LAST <= 0x5CFF, hex(LAST)


def probe_step_id():
    return _ids['ProbeStep.glob']


def truehud_id():
    return _ids['TrueHudBars.glob']


def add_records(b, add):
    add('GLOB', probe_step_id(), PROBE_STEP_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(0))])
    add('GLOB', truehud_id(), TRUEHUD_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(1))])   # round 26c: default on


def new_edids():
    return {PROBE_STEP_GLOBAL, TRUEHUD_GLOBAL}
