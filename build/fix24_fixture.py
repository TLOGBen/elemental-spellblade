"""Round 24 (N5) native test fixtures for native/tests/reaction_test.cpp.

build/fix24-body-table.json   group R: body / burst / death / advent / echo scenarios -- the crowd (member 0 and the
                              others: boards, bodies, positions, flags), your board, the nodes owned (by v0.4 name,
                              resolved to slots through the identity table), the steps, and what build/fix24_reference.py
                              (the model written from the v0.4 text) says every member's board and every non-status op
                              (with the member it acts on) are afterwards
build/fix24-wiring.json       group W: the generator's identities for the round-24 records (build/fix24_records.py: the
                              kinds and the timed families) and the forms the crowd read resolves (engaged, reanimate)
"""
import json

import fix24_records as rec
import fix24_reference as ref

TABLE = 'build/fix24-body-table.json'
WIRING = 'build/fix24-wiring.json'
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


def _same(have, want):
    near = lambda a, b: abs(a - b) <= 2e-4 * max(1.0, abs(b))
    return len(have) == len(want) and all(a == b if isinstance(b, str) else near(a, b) for a, b in zip(have, want))


def _hand_check(name, expect):
    want = ref.HAND.get(name)
    if want is None:
        return 0
    for row in want.get('ops', []):
        assert any(_same(r, row) for r in expect['ops']), ('HAND', name, row, expect['ops'])
    for row in want.get('absent', []):
        assert not any(_same(r[:len(row)], row) for r in expect['ops']), ('HAND absent', name, row, expect['ops'])
    for (member, kind), pair in want.get('boards', {}).items():
        have = (expect['me'] if member == -1 else expect['members'][member]).get(kind)   # -1: your board
        assert have and _same(have, pair), ('HAND', name, member, kind, have, pair)
    return 1


def scenarios(damage):
    slots = _slots()
    rows, checked = [], []
    for spec in ref.scenario_specs():
        name = spec['name']
        for key in list(spec.get('ranks', {})) + list(spec.get('branches', set())):
            assert key in slots, (name, key)
        row = dict(
            name=name,
            ranks=[slots[k] + [v] for k, v in sorted(spec.get('ranks', {}).items())],
            branches=[slots[k] for k in sorted(spec.get('branches', set()))],
            tuning=spec.get('tuning', {}), levels=spec.get('levels', []), facts=spec.get('facts', {}),
            me=spec.get('me', {}), crowd=spec['crowd'], steps=spec['steps'],
            expect=ref.evaluate(damage, spec))
        rows.append(row)
        checked.append(_hand_check(name, row['expect']))
    assert sum(checked) == len(ref.HAND), ('HAND checks without a scenario', sum(checked), len(ref.HAND))
    return rows


def write(b, settings, write_if_changed, root):
    damage = {i + 1: tuple(settings['element_damage'][n]) for i, n in enumerate(ELEMENTS)}
    table = dict(source='build/fix24_reference.py (the v0.4 reaction bodies, 融斷, death handling and range scans)',
                 damage=[list(damage[e]) for e in range(1, 12)],
                 rng="per scenario facts.rng: 'mid' (default; a chance p succeeds when p >= 0.5, a real draw is the "
                     "midpoint), 'yes' (every chance succeeds, a real draw is its low end), 'no' (none, the high end)",
                 scenarios=scenarios(damage))
    write_if_changed(root / TABLE, json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    return len(table['scenarios'])


def wiring(b, globals_, write_if_changed, root):
    kinds = [dict(kind=k[0], suffix=k[1], effect=rec.effect_id(k[0]), spell=rec.spell_id(k[0]), seconds=k[4], on_player=k[3],
                  av=k[7]) for k in rec.KINDS]
    timed = [dict(name=name, util=util, self=util in rec.SELF_UTILS,
                  spells=[rec.timed_id(name, s) for s in range(1, rec.TIMED_MAX_SECONDS + 1)],
                  effect=b.util_effect_id(util)) for util, name in rec.TIMED]
    data = dict(kinds=kinds, timed=timed, timed_max=rec.TIMED_MAX_SECONDS, hush=b.hit21.HUSH, hush_effect=b.hit21.HUSH_EFFECT,
                heal_target=0x005151, drain_magicka=b.util_spell_id(2), engaged=b.ID_ENGAGED_EFFECT,
                reanimate=b.ID_REANIMATE_EFFECT,
                silence=[b.hit20.SILENCE + s - 1 for s in range(1, b.hit20.SILENCE_COUNT + 1)],
                tuning=dict(frostOpenSlowPct=globals_['ESSB_FrostOpenSlowPct'], waterOpenStamina=globals_['ESSB_WaterOpenStamina']))
    write_if_changed(root / WIRING, json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    return data
