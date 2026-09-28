"""Round 29 (DLL 0.29.0) records: 灌注 (v0.4 5.2 common sustain legend branch; .codex/design-infuse-2026-09-28.md).

  ESSB_InfuseCostPct    MCM 平衡頁「灌注成本」: the share of your max magicka an infused power attack costs, 5..25 (default 10,
                        settings.json infuse_cost_pct); never scaled by the tree level, the node's points or 維持費.
  ESSB_InfuseFloorPct   MCM 平衡頁「灌注下限」: an infusion needs current magicka >= cost + this share of your max magicka,
                        0..60 (default 30, settings.json infuse_floor_pct); at 0 an infusion still leaves at least 1 point.

The perk itself is the plan's (tree_v04.NEW_SLOTS: ESSB_P_common_0_4_B2). The DLL reads both globals at hit time
(EngineFacts.h ReadTuning -> Tuning::infuseCostPct / infuseFloorPct). IDs 0x005F00-0x005FFF. Append-only.
"""
BASE = 0x5F00
COST_GLOBAL = 'ESSB_InfuseCostPct'
FLOOR_GLOBAL = 'ESSB_InfuseFloorPct'
COST_KEY = 'infuse_cost_pct'
FLOOR_KEY = 'infuse_floor_pct'
COST_RANGE = (5.0, 25.0, 1.0)     # MCM min, max, step (v0.4 6.2)
FLOOR_RANGE = (0.0, 60.0, 1.0)

_ids = {COST_GLOBAL: BASE, FLOOR_GLOBAL: BASE + 1}
LAST = BASE + 1
assert LAST <= 0x5FFF


def global_id(name):
    return _ids[name]


def add_records(b, add, settings):
    for name, key in ((COST_GLOBAL, COST_KEY), (FLOOR_GLOBAL, FLOOR_KEY)):
        add('GLOB', _ids[name], name, [('FNAM', b'f'), ('FLTV', b.F(settings[key]))])


def new_edids():
    return {COST_GLOBAL, FLOOR_GLOBAL}
