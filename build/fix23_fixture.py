"""Round 23 (N4) native test fixtures for native/tests/self_test.cpp.

build/fix23-self-table.json   group S: self-layer and hurt scenarios -- your board and the target's (or the attacker's)
                              before, the nodes owned (by v0.4 name, resolved to slots through the identity table), the
                              steps (element hits, no-form hits, opens, ends, form leave / enter, hurts, spell casts, the
                              per-second decay) and what build/fix23_reference.py (the model written from the v0.4 text)
                              says the boards and the non-status ops are afterwards
build/fix23-wiring.json       group W: the generator's record identities for the round-23 records (build/fix23_records.py)
                              and the mirror globals the DLL writes
"""
import json

import fix23_records as rec
import fix23_reference as ref

TABLE = 'build/fix23-self-table.json'
WIRING = 'build/fix23-wiring.json'
ELEMENTS = ['Fire', 'Frost', 'Lightning', 'Earth', 'Wind', 'Blood', 'Divine', 'Poison', 'Water', 'Darkness', 'Astral']


def _slots():
    """(tree, v0.4 name) -> [tree, route, tier] or [tree, route, tier, slot], from the identity table."""
    import plan_trees
    found = {}
    for tree in plan_trees.parse()['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                found[(tree['id'], tier['main_label'])] = [tree['index'], route['index'], tier['index']]
                for b in tier['branches']:
                    found[(tree['id'], b['name'])] = [tree['index'], route['index'], tier['index'], b['slot']]
    return found


TUNING_FIELDS = dict(sync='syncStage', mult_duration='multDuration', mult_cooldown='multCooldown', node_scale='nodeScale',
                     base='baseDamageMult', recovery='multRecovery')


# Hand anchors (computed from the v0.4 text by hand, NOT by the model; the fixture refuses to write the table unless the
# model agrees, so the C++ is held to them too). Tree level 1: G = 1.05. B_max: fire 12, earth 10, astral 10.
#   同調 (2.4): 4 + 1 = 5 = stage 1 -> ESSB_SyncUp 1; 回饋 = B_max(fire) 12 x 2 = 24 health and 24 magicka
#   碎岩 (5.6): 5 layers x B_max 10 x 0.3 x G 1.05 = 15.75 earth; stamina 5 x 10 x 0.5 x 1.05 = 26.25; knock 3
#   反震 (5.6): B_max 10 x 2.0 x 1.05 = 21 earth, knock 3, 10 s cooldown
#   滿格重擊放電 (2.1): 6 charges, x1 (the Papyrus body: x30% B_max per charge), R 1.5, crit x2.5
#   冰盾 (5.4): 2 + 1 = 3 layers -> armour 60, magic resist 12 for 8 s
#   法盾 (5.1): lost 21 at share 0.30 -> blocked 21 x 0.3 / 0.7 = 9, x1.0 magicka = 9
#   水幕 (5.11): lost 16 at 0.20 -> blocked 4, x1.5 = 6 magicka
#   護血 (5.8, share 0.50 by commander ruling): lost 1 -> blocked 1, pool 5 -> 4; lost 80 through a 5 pool -> blocked 80,
#       pool 0, 75 real damage: 20 - 75 < 0 -> ESSB_Lethal (no keep-1); lost 10 through a 6 pool -> 4 real damage
#   法盾 out of magicka: lost 21 -> blocked 9, 5 magicka paid, 4 real damage; 水幕: lost 16 -> blocked 4 = 6 magicka owed,
#       3 paid, (6 - 3) / 1.5 = 2 real damage
#   DoT (review ruling): a destruction spell's DoT with 30 left after the cut, 法盾 30%: 30 x 0.3 / 0.7 = 12.857143 dealt
#       back; its direct 10 -> blocked 4.285714 magicka
#   雷神: 6 charges x B_max(lightning) 25 x 0.5 = 75 magicka
#   蓄能 (≥1 converts): a power hit with 3 蓄勁 -> quake +15%, 蓄勁 0 + 3; a block with 4 -> bracing 4 for 3 s, 蓄勁 2
#   SyncT 3 / 8 / 12: 2 + 1 = 3 = stage 1
#   化法為力 (5.1): a 20-point spell x30% = 6; 3 fit under max magicka, 3 go to the overload (3 s wait)
#   超載 decay (5.1): 不竭 5 points -> 5% - 1% = 4% of 200 = 8 a second: 30 -> 22
#   懲戒 (5.9): 7 + 2 (誓約's attacker) = 9, 天誅 cap 8, 8 s
#   三重奏 (5.2): fire's end after frost's and lightning's inside 10 s: x3 (End mult 3), keep-all 60 s
#   闇星一擊 (5.13): star cap 3 x B_max 10 x G 1.05 x (1 + 2 points x 3% x NodeScale 3) = 37.17 astral; 闇宙 3 -> 2
#   反咒 (5.1): cost 40 x (1 + 2% x level 1) = 40.8 true damage; 噬命 half = 20.4
HAND = {
    'sync: 4 + a hit = stage 1, ESSB_SyncUp, 回饋 heals B_max x2': dict(
        me={'Sync': [5.0, 86400.0]}, ops=[['event', 'SyncUp', 1.0], ['heal', 24.0], ['magicka', 24.0]]),
    '碎岩: a full power hit smashes the armour out, 蓄勁 +3': dict(
        me={'StoredForce': [3.0, 86400.0]}, ops=[['damage', 4, 15.75], ['drainStamina', 26.25], ['event', 'Knock', 3.0]]),
    '反震: full armour, melee, B_max x2 back and a knock, armour gone': dict(
        me={'RetaliateCooldown': [1.0, 10.0]}, ops=[['damage', 4, 21.0], ['event', 'Knock', 3.0]]),
    'lightning: a full power hit discharges (crit x2.5), the mark stays': dict(ops=[['event', 'Discharge', 6.0, 1.0, 1.5, 2.5]]),
    '冰盾: a frost hit +1 layer (armour 20, resist 4%)': dict(
        me={'IceShield': [3.0, 8.0], 'IceShieldArmorAV': [60.0, 8.0], 'IceShieldMagicAV': [12.0, 8.0]}),
    '法盾: 30% by magicka at 1.0': dict(ops=[['spendMagicka', 9.0]]),
    '水幕: 20% by magicka at 1.5 a point': dict(ops=[['spendMagicka', 6.0]]),
    '護血: the pool takes 50% of a small hit and holds': dict(ops=[['guardPool', 4.0]]),
    '護血: a huge hit through a tiny pool kills (no keep-1)': dict(ops=[['guardPool', 0.0], ['hurtHealth', 75.0], ['event', 'Lethal']]),
    '護血: the pool partially holds, the rest is real damage': dict(ops=[['guardPool', 0.0], ['hurtHealth', 4.0]]),
    '法盾: magicka runs out, the rest is damage': dict(ops=[['spendMagicka', 5.0], ['hurtHealth', 4.0]]),
    '水幕: magicka runs out, the rest is damage': dict(ops=[['spendMagicka', 3.0], ['hurtHealth', 2.0]]),
    '法盾 does not share a DoT: the cut part of a burning spell is dealt back': dict(ops=[['hurtHealth', 12.857143],
                                                                                    ['spendMagicka', 4.285714]]),
    'lightning: 雷神 at sync 3 discharges when the charges fill, magicka back, 疾電': dict(ops=[['magicka', 75.0]]),
    '蓄能: any 蓄勁 converts on a power hit (3 points -> +15% quake)': dict(me={'ChargedQuake': [0.15, 3600.0],
                                                                              'StoredForce': [3.0, 86400.0]}),
    '蓄能: a block converts 4 points into 4% bracing': dict(me={'Bracing': [4.0, 3.0], 'StoredForce': [2.0, 86400.0]}),
    'sync: ESSB_SyncT1..3 at 3 / 8 / 12 move the stages': dict(me={'Sync': [3.0, 86400.0]}, ops=[['event', 'SyncUp', 1.0]]),
    '化法為力: 30% of a spell back as magicka, the rest into the overload': dict(
        me={'Overload': [3.0, 86400.0], 'OverloadWait': [1.0, 3.0]}, ops=[['magicka', 3.0]]),
    '超載 decays 5% a second after the wait; 不竭 5 points 4%': dict(me={'Overload': [22.0, 86400.0]}),
    '懲戒: 誓約 attacker +2, 天誅 cap 8': dict(me={'Punish': [8.0, 8.0]}),
    '三重奏: the third element end in 10 s x3, keep-all': dict(
        me={'SyncKeepAll': [1.0, 60.0]}, ops=[['event', 'End', 3.0, 0.0, 3.0, 0.0, 1.0, 0.5, 0.0, 0.0]]),
    '闇星: a hit strikes a full detonation, 闇宙 -1': dict(me={'Cosmos': [2.0, 10.0]}, ops=[['damage', 11, 37.17]]),
    '反咒: the marked caster takes its cost x(1 + 2%/level) true damage, 噬命 half back': dict(
        ops=[['damage', 0, 40.8], ['heal', 20.4]]),
}


def _same(have, want):
    near = lambda a, b: abs(a - b) <= 2e-4 * max(1.0, abs(b))
    return len(have) == len(want) and all(a == b if isinstance(b, str) else near(a, b) for a, b in zip(have, want))


def _hand_check(name, expect):
    want = HAND.get(name)
    if want is None:
        return 0
    for side in ('target', 'me'):
        for kind, pair in want.get(side, {}).items():
            have = expect[side].get(kind)
            assert have and _same(have, pair), ('HAND', name, kind, have, pair)
    for row in want.get('ops', []):
        assert any(_same(r, row) for r in expect['ops']), ('HAND', name, row, expect['ops'])
    return 1


def _step(step):
    op, *args = step
    out = [op]
    for a in args:
        out.append({k: float(v) if isinstance(v, float) else v for k, v in a.items()} if isinstance(a, dict) else a)
    return out


def scenarios(damage):
    slots = _slots()
    trees = {t: i for i, t in enumerate(ref.TREE[1:])}
    rows, checked = [], []
    for spec in ref.scenario_specs():
        name, options, statuses, marks, steps = spec
        opts = dict(options)
        ranks = opts.pop('ranks', {})
        branches = opts.pop('branches', set())
        flags = opts.pop('target_flags', {})
        level = opts.pop('level', {})
        body = opts.pop('body', {})
        tuning = {TUNING_FIELDS[k]: v for k, v in opts.items() if k in TUNING_FIELDS}
        if 'sync_t' in opts:   # ESSB_SyncT1..3 (round 23 review)
            tuning.update(syncT1=opts['sync_t'][0], syncT2=opts['sync_t'][1], syncT3=opts['sync_t'][2])
            opts.pop('sync_t')
        facts = {k: opts[k] for k in ('hp', 'hp_max', 'form', 'rng', 'magicka_max') if k in opts}
        unknown = set(opts) - set(TUNING_FIELDS) - set(facts)
        assert not unknown, (name, unknown)
        for key in list(ranks) + list(branches):
            assert key in slots, (name, key)
        rows.append(dict(
            name=name,
            ranks=[slots[k] + [v] for k, v in sorted(ranks.items())],
            branches=[slots[k] for k in sorted(branches)],
            tuning=tuning, levels=[[trees[t], v] for t, v in sorted(level.items())],
            facts=facts, body=body, flags=flags,
            statuses=[list(s) for s in statuses], marks=[list(m) for m in marks],
            steps=[_step(s) for s in steps],
            expect=ref.evaluate(damage, spec)))
        checked.append(_hand_check(name, rows[-1]['expect']))
    assert sum(checked) == len(HAND), ('HAND checks without a scenario', sum(checked), len(HAND))
    return rows


def write(b, settings, write_if_changed, root):
    damage = {i + 1: tuple(settings['element_damage'][n]) for i, n in enumerate(ELEMENTS)}
    table = dict(source='build/fix23_reference.py (the v0.4 self-resource and hurt rules)',
                 damage=[list(damage[e]) for e in range(1, 12)],
                 rng="per scenario facts.rng: 'mid' (default; a chance p succeeds when p >= 0.5, a real draw is the "
                     "midpoint), 'yes' (every chance succeeds, a real draw is its low end), 'no' (none, the high end)",
                 scenarios=scenarios(damage))
    write_if_changed(root / TABLE, json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    return len(table['scenarios'])


def wiring(b, globals_, write_if_changed, root):
    kinds = [dict(kind=k[0], suffix=k[1], effect=rec.effect_id(k[0]), spell=rec.spell_id(k[0]), seconds=k[4], on_player=k[3],
                  av=k[7]) for k in rec.KINDS]
    mirrors = {name: globals_[name] for name in ('ESSB_Sync', 'ESSB_SyncStage', 'ESSB_Charge', 'ESSB_Resolve', 'ESSB_IceShield',
                                                  'ESSB_RockArmor', 'ESSB_Wind', 'ESSB_Bracing')}
    data = dict(kinds=kinds, mirrors=mirrors, riposte=b.hit21.RIPOSTE, spend_magicka=b.hit20.SPEND,
                drain_stamina=b.util_spell_id(3), dispel_mark=b.ID_MANABREAK_SPELL, guard_spell=b.hit20.GUARD,
                guard_effect=b.hit20.GUARD_EFFECT)
    write_if_changed(root / WIRING, json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    return data
