"""Round 22 (N3) native test fixtures for native/tests/status_test.cpp.

build/fix22-status-table.json   group S: status scenarios -- pre-hit boards, the nodes owned (by v0.4 name, resolved
                                to slots through the identity table), the steps (hits, ends, expiries, ...) and what
                                build/fix22_reference.py (the model written from the v0.4 text) says the boards and
                                the non-status ops are afterwards
build/fix22-wiring.json         group W: the generator's record identities (build/fix22_records.py and build_v03's
                                IDs): which local FormID is which status / mark / DoT spell, the record seconds, the
                                stub flags -- what TagOf, Read, Settles and Lower must agree with
"""
import json

import fix22_records as rec
import fix22_reference as ref

TABLE = 'build/fix22-status-table.json'
WIRING = 'build/fix22-wiring.json'
ELEMENTS = ['Fire', 'Frost', 'Lightning', 'Earth', 'Wind', 'Blood', 'Divine', 'Poison', 'Water', 'Darkness', 'Astral']
TUNING_FIELDS = dict(sync='syncStage', mult_duration='multDuration', mult_cooldown='multCooldown', node_scale='nodeScale',
                     base='baseDamageMult', recovery='multRecovery', mult_dot='multDot', poison_k='poisonDotK',
                     bleed_k='bleedDotK', wet='envWet', stormy='envStormy', night='envNight', slow_cap='slowCapPct',
                     wet_slow='wetSlowPct')


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


# Review fix 1 / 2 / 5, rulings (b)+(d): expectations computed by hand from the v0.4 text, NOT from the reference model.
# The fixture refuses to write the table unless the model agrees, so the native test (which compares the C++ against the
# table) is held to these numbers too. Per dose at tree level 1 = B_max 9 x k_dot 0.2116 x G(1) 1.05 = 1.99962.
#   catalyse (2.7 催毒): m' = 2m, d' = d - t  -> 4 doses 7.99848 x 2 = 15.99696 for 10 s, marker 2
#   re-open (淬毒 3 doses, 2.7 growth in base doses): base 4 + 3 = 7 -> 7 x 1.99962 x 2 = 27.99468; d' = min(10 + 3, 15) = 13
#   two power hits (+2 each): base 9 -> 35.99316 (15 s), then base 11 capped at 10 -> 39.9924 (15 s)
#   spread one dose (2.7 擴散一劑): 4 + 1 = 5 doses = 9.9981; d' = max(12 - 10, 12) = 12
#   spread 0.5 into a catalysed poison: 15.99696 / 2 = base 4, + 0.5 = 4.5 -> 4.5 x 1.99962 x 2 = 17.99658; d' = max(13, 12) = 13
#   miasma: 5 doses -> 0.5 / s; 4 doses -> 0; catalysed base 5 with 10 points x NodeScale 3 -> 1.0 + 0.05 x 30 = 2.5
#   plague: 4 points x 5% = 0.2 at sync 3
#   凍傷 (5.4): 3 carried crystals x B_max 10 x 0.5 x G 1.05 = 15.75 frost damage
#   深霜結 freeze: gauge 4 + 1 = 5 freezes for 3 s; the 2 stored crystals last 3 + 1 = 4 s
#   幻影 (5.12): the target carries Phantom for 3 s
HAND = {
    'catalyse then re-open: open +3 doses keeps ×2': dict(target={'PoisonDot': [27.99468, 13.0], 'Catalyzed': [2.0, 13.0]}),
    'catalyse then re-open, two power hits: base-dose cap 10 keeps ×2': dict(target={'PoisonDot': [39.9924, 15.0],
                                                                                        'Catalyzed': [2.0, 15.0]}),
    "spread one dose: d' = max(d - t, 12)": dict(target={'PoisonDot': [9.9981, 12.0]}),
    'spread 0.5 dose into a catalysed poison': dict(target={'PoisonDot': [17.99658, 13.0], 'Catalyzed': [2.0, 13.0]}),
    'miasma: 5 doses give 0.5 a second, 4 give none': dict(ops=[['miasmaDoses', 0.5]]),
    'miasma below the threshold': dict(ops=[['miasmaDoses', 0.0]]),
    'miasma catalysed + 瘴氣每秒傳遞劑量 10 points': dict(ops=[['miasmaDoses', 2.5]]),
    'plague: 5%/pt at sync 3': dict(ops=[['plagueChance', 0.2]]),
    '凍傷 with the crystals already gone: the removal sink carried 3 (review fix 2)': dict(ops=[['damage', 2, 15.75]]),
    'freezing keeps the stored crystals 1 s past the frozen end': dict(target={'Frozen': [1.0, 3.0], 'Crystal': [2.0, 4.0]}),
    '幻影: the dark open puts 幻影 on the target for 3 s': dict(target={'Phantom': [1.0, 3.0]}),
}


def _hand_check(name, expect):
    want = HAND.get(name)
    if want is None:
        return 0
    near = lambda a, b: abs(a - b) <= 2e-4 * max(1.0, abs(b))
    for kind, (mag, rest) in want.get('target', {}).items():
        have = expect['target'].get(kind)
        assert have and near(have[0], mag) and near(have[1], rest), ('HAND', name, kind, have, (mag, rest))
    for row in want.get('ops', []):
        assert any(len(r) == len(row) and r[0] == row[0] and all(near(a, b) for a, b in zip(r[1:], row[1:])) for r in expect['ops']), \
            ('HAND', name, row, expect['ops'])
    return 1


def _step(step):
    op, *args = step
    return [op] + [float(a) if isinstance(a, float) else a for a in args]


def scenarios(damage):
    slots = _slots()
    trees = {t: i for i, t in enumerate(ref.TREE[1:])}
    rows = []
    checked = []
    for spec in ref.scenario_specs():
        name, options, statuses, marks, steps = spec
        opts = dict(options)
        ranks = opts.pop('ranks', {})
        branches = opts.pop('branches', set())
        flags = opts.pop('target_flags', {})
        level = opts.pop('level', {})
        body = opts.pop('body', {})
        tuning = {TUNING_FIELDS[k]: v for k, v in opts.items() if k in TUNING_FIELDS}
        facts = {k: opts[k] for k in ('hp', 'hp_max', 'interior', 'ice_armor') if k in opts}
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
    table = dict(source='build/fix22_reference.py (the v0.4 status rules)',
                 damage=[list(damage[e]) for e in range(1, 12)],
                 rng='a chance p succeeds when p >= 0.5; a real draw in [lo, hi] is the midpoint',
                 scenarios=scenarios(damage))
    write_if_changed(root / TABLE, json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    return len(table['scenarios'])


def wiring(b, write_if_changed, root):
    kinds = [dict(kind=k[0], suffix=k[1], effect=rec.effect_id(k[0]), spell=rec.spell_id(k[0]), seconds=k[4],
                  on_player=k[3], stub=k[5]) for k in rec.KINDS]
    # Round 23 (N4): the StatusKind enum continues with build/fix23_records.py's kinds (no stubs), so the wiring the
    # status test checks TagOf / Read / Lower against is the whole table.
    import fix23_records as rec23
    kinds += [dict(kind=k[0], suffix=k[1], effect=rec23.effect_id(k[0]), spell=rec23.spell_id(k[0]), seconds=k[4],
                   on_player=k[3], stub=False) for k in rec23.KINDS]
    data = dict(
        kinds=kinds,
        marks=[dict(element=i + 1, effect=b.ID_MARK_EFFECT + i, spell=b.ID_MARK_SPELL + i) for i in range(11)],
        mark_record_seconds=8,
        react=[b.ID_REACT_SPELL + i for i in range(11)], true_spell=b.ID_TRUE_SPELL,
        bleed_dot=dict(effect=rec.dot_effect_id('bleed'), spells=[rec.dot_spell_id('bleed', s) for s in range(1, rec.DOT_MAX_SECONDS + 1)]),
        poison_dot=dict(effect=rec.dot_effect_id('poison'), spells=[rec.dot_spell_id('poison', s) for s in range(1, rec.DOT_MAX_SECONDS + 1)]),
        fear=b.ID_FEAR_EFFECT, frenzy=b.ID_FRENZY_EFFECT, slow_effect=b.util_effect_id(0),
        soak=[b.hit21.soak_id(s) for s in range(1, b.hit21.SOAK_MAX_SECONDS + 1)],
        heal=b.util_spell_id(4), magicka=b.util_spell_id(5), stamina=b.util_spell_id(6), bleed_tick=b.util_spell_id(7))
    write_if_changed(root / WIRING, json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    return data
