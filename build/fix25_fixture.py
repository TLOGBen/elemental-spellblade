"""Round 25 (N6) native test fixtures for native/tests/timer_test.cpp.

build/fix25-timer-table.json   the scenarios of build/fix25_reference.py (the clock, the forms' second, the environment,
                               the domains, the slows, the hotkeys) with the nodes resolved to slots through the identity
                               table and what the model says (ops with the member they act on, outputs, your board after)
build/fix25-wiring.json        the generator's identities for the round-25 records (build/fix25_records.py: the kinds, the
                               domains' HAZDs / Spawn Hazard effects / spawn spells, the hazard spells' effects), the globals
                               the timer and the hotkeys read, the ally stamina spell, the upkeep settings
"""
import json

import fix25_records as rec
import fix25_reference as ref

TABLE = 'build/fix25-timer-table.json'
WIRING = 'build/fix25-wiring.json'
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


def scenarios(damage):
    slots = _slots()
    rows, checked = [], []
    for spec in ref.scenario_specs():
        ranks = dict(spec.get('ranks', {}))
        branches = set(tuple(b) for b in spec.get('branches', ()))
        for key in list(ranks) + list(branches):
            assert key in slots, (spec['name'], key)
        row = ref.fixture_row(damage, spec)
        row['ranks'] = [slots[k] + [v] for k, v in sorted(ranks.items())]
        row['branches'] = [slots[k] for k in sorted(branches)]
        row['expect'] = ref.evaluate(damage, dict(spec, ranks=ranks, branches=branches))
        rows.append(row)
        checked.append(ref.check_hand(spec['name'], row['expect']))
    assert sum(checked) == len(ref.HAND), ('HAND checks without a scenario', sum(checked), len(ref.HAND))
    return rows


def write(b, settings, write_if_changed, root):
    damage = {i + 1: tuple(settings['element_damage'][n]) for i, n in enumerate(ELEMENTS)}
    # The model's upkeep numbers are v0.4 1.1's; the build reads them from settings.json -- they must agree.
    assert (settings['upkeep_base_pct'], settings['upkeep_dark_pct'], settings['upkeep_level_relief']) == \
        (ref.UPKEEP_BASE, ref.UPKEEP_DARK, ref.UPKEEP_RELIEF), 'settings.json upkeep_* differ from v0.4 1.1'
    table = dict(source='build/fix25_reference.py (v0.4 1.1, 2.9, 2.10, 5.x domains, 6.2 hotkeys)',
                 damage=[list(damage[e]) for e in range(1, 12)], scenarios=scenarios(damage))
    write_if_changed(root / TABLE, json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    return len(table['scenarios'])


def wiring(b, globals_, write_if_changed, root):
    kinds = [dict(kind=k[0], suffix=k[1], effect=rec.effect_id(k[0]), spell=rec.spell_id(k[0]), seconds=k[4], on_player=k[3])
             for k in rec.KINDS]
    domains = []
    for e in rec.DOMAIN_ELEMENTS:
        domains.append(dict(element=e, hazard=rec.hazard_id(e), hazard_spell=rec.hazard_spell_id(e), spawn_effect=rec.spawn_effect_id(e),
                            spawn=[rec.spawn_id(e, s) for s in range(1, rec.DOMAIN_MAX_SECONDS + 1)],
                            effects=[list(x) for x in rec.hazard_effects(b, e)]))
    data = dict(kinds=kinds, domains=domains, domain_max=rec.DOMAIN_MAX_SECONDS, stamina_target=0x005153,
                radius_feet=rec.DOMAIN_RADIUS_FEET, radius_units=rec.DOMAIN_RADIUS_UNITS,
                globals=dict(multUpkeep=globals_['ESSB_MultUpkeep'], flowBase=globals_['ESSB_WaterFlowBasePct'],
                             flowPerRank=globals_['ESSB_WaterFlowPerRankPct'], thunder=globals_['ESSB_EnvThunder'],
                             freeOpen=globals_['ESSB_FreeOpen'], hotkeysEnabled=globals_['ESSB_HotkeysEnabled'],
                             formNotify=globals_['ESSB_FormNotify'],
                             hotkeys=[globals_[f'ESSB_Hotkey_{e}'] for e in ELEMENTS]),
                upkeep=[ref.UPKEEP_BASE, ref.UPKEEP_DARK, ref.UPKEEP_RELIEF])
    write_if_changed(root / WIRING, json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    return data
