"""Round 20 (N2) / round 21 native test fixtures, generated from the reference model and the generator's record table.

build/fix20-magnitude-table.json  group A: hit scenarios (inputs, scripted random draws, expected casts)
                                  computed by build/fix20_reference.py from the v0.4 formulas.
build/fix20-wiring.json           group B: what the engine-read layer must ask and derive - perk FormIDs
                                  per node slot, the GLOB behind every tuning field, spell FormIDs per cast -
                                  taken from build_v03's record identities (cross-checked against the built
                                  ESP by fix19_native.verify).
"""
import itertools
import json
from dataclasses import asdict, replace

import fix20_reference as ref

TABLE = 'build/fix20-magnitude-table.json'
WIRING = 'build/fix20-wiring.json'


def _draw_real(element, u):
    lo, hi = ref.DAMAGE[element]
    return ['real', lo, hi, u]


def _draw_proc(element, u=0.5, value=13, crit=False):
    """Draws one RollProc consumes: B, and the crit roll for lightning."""
    if element == ref.LIGHTNING:
        lo, hi = ref.DAMAGE[ref.LIGHTNING]
        return [['int', lo, hi, value], ['chance', 0.05, crit]]
    return [_draw_real(element, u)]


def _scenario(name, state, draws):
    out = ref.plan(state, [tuple(d) for d in draws])
    fields = asdict(state)
    ranks = [[*slot, v] for slot, v in sorted(state.ranks.items())]
    branches = [list(slot) for slot in sorted(state.branches)]
    levels = [[tree, v] for tree, v in sorted(state.level.items())]
    for key in ('ranks', 'branches', 'level'):
        fields.pop(key)
    return dict(name=name, state=fields, ranks=ranks, branches=branches, levels=levels, draws=draws,
                expect=dict(casts=[list(c) for c in out['casts']], consume_echo=out['consume_echo'],
                            consume_riposte=out['consume_riposte'], crit=out['crit'], magnitude=out['magnitude']))


def _rich_nodes(element):
    """Every N2 percentage node of this element and the common tree bought, with distinct ranks."""
    ranks = {(12, 1, 0): 4, (12, 1, 3): 2, (12, 0, 1): 6, (12, 0, 3): 5}
    if ref.adept(element):
        ranks[ref.adept(element)] = 7
    if ref.master(element):
        ranks[ref.master(element)] = 3
    return ranks


def scenarios():
    rows = []
    base = ref.State()
    # A1: every element x normal/power x three node profiles x three B draws (lightning: 1 / 13 / 25, crit or not).
    profiles = {
        'bare': dict(),
        'rich': dict(stage=3, base_damage_mult=1.2, level={t: 40 for t in range(13)}),
        'stage2': dict(stage=2, level={t: 100 for t in range(13)}, node_scale=5.0),
    }
    for element, power, (pname, prof) in itertools.product(range(1, 12), (False, True), profiles.items()):
        ranks = _rich_nodes(element) if pname != 'bare' else {}
        state = replace(base, element=element, power=power, ranks=ranks, **prof)
        for i, u in enumerate((0.0, 0.37, 1.0)):
            value, crit = (1, 13, 25)[i], i == 2
            rows.append(_scenario(f'A1 e{element} p{int(power)} {pname} draw{i}', state, _draw_proc(element, u, value, crit)))
    # A2: blood curve and leech: health points x 逆流 x 血怒, leech with a blood mark, overflow into 護血.
    for hp, reverse, rage in itertools.product((100, 95, 85, 70, 55, 50, 30, 20, 10, 5, 0), (False, True), (False, True)):
        branches = set()
        if reverse:
            branches.add(ref.NODES['kBloodReverse'])
        if rage:
            branches.add(ref.NODES['kBloodRage'])
        state = replace(base, element=ref.BLOOD, hp=float(hp), hp_perm=100.0, hp_max=100.0, blood_mark=True,
                        branches=branches, ranks={ref.NODES['kBloodLeechRatio']: 4})
        rows.append(_scenario(f'A2 blood hp{hp} rev{int(reverse)} rage{int(rage)}', state, _draw_proc(ref.BLOOD, 0.25)))
    for guard, hp, overflow in itertools.product((0.0, 15.0, 39.9, 40.0, 60.0), (200.0, 195.0), (False, True)):
        # 40 = exactly the cap (no recast); 60 = above the cap after max health dropped (clamped to 40)
        branches = {ref.NODES['kBloodOverflow']} if overflow else set()
        state = replace(base, element=ref.BLOOD, hp=hp, hp_perm=200.0, hp_max=200.0, blood_mark=True, guard=guard,
                        branches=branches, level={5: 100}, power=True)
        rows.append(_scenario(f'A2 overflow guard{guard} hp{hp} br{int(overflow)}', state, _draw_proc(ref.BLOOD, 1.0)))
    rows.append(_scenario('A2 blood without mark: no leech', replace(base, element=ref.BLOOD, hp=40.0), _draw_proc(ref.BLOOD, 0.5)))
    rows.append(_scenario('A2 blood temp health: max above permanent', replace(base, element=ref.BLOOD, hp=90.0, hp_perm=80.0, hp_max=120.0, blood_mark=True), _draw_proc(ref.BLOOD, 0.5)))
    # A3: divine and darkness environment, undead, exorcism, interior.
    for element, night, interior, undead, necro, exorcism in itertools.product(
            (ref.DIVINE, ref.DARKNESS), (False, True), (False, True), (False, True), (False, True), (False, True)):
        branches = {ref.NODES['kDivineExorcism']} if exorcism else set()
        state = replace(base, element=element, night=night, interior=interior, undead=undead, necro=necro, branches=branches)
        rows.append(_scenario(f'A3 e{element} night{int(night)} in{int(interior)} und{int(undead)} nec{int(necro)} exo{int(exorcism)}', state, _draw_proc(element, 0.6)))
    # A4: wind sneak attack (melee power, ranged sneak shot counted as power by MakeAttack), wet slow, flat nodes.
    for power, sneak in itertools.product((False, True), (False, True)):
        rows.append(_scenario(f'A4 wind p{int(power)} s{int(sneak)}', replace(base, element=ref.WIND, power=power, sneak=sneak), _draw_proc(ref.WIND, 0.8)))
    for element, cap in itertools.product((ref.FIRE, ref.WATER), (70.0, 20.0, 90.0)):
        state = replace(base, element=element, wet=True, slow_cap=cap)
        rows.append(_scenario(f'A4 wet e{element} cap{cap}', state, _draw_proc(element, 0.1)))
    for points, drain_back, recov, drain in itertools.product((0, 1, 15), (False, True), (1.0, 1.5), (1.0, 0.5)):
        branches = {ref.NODES['kEarthDrainStrength']} if drain_back else set()
        state = replace(base, element=ref.EARTH, ranks={ref.NODES['kEarthStaminaCut']: points} if points else {},
                        branches=branches, level={3: 60}, mult_recovery=recov, mult_drain=drain)
        rows.append(_scenario(f'A4 earth cut{points} back{int(drain_back)} rec{recov} dr{drain}', state, _draw_proc(ref.EARTH, 0.5)))
    for drain, power, crit in itertools.product((0.25, 3.0), (False, True), (False, True)):
        # lightning's 50% magicka drain follows the damage override and ESSB_MultDrain (round-13 regression, now DLL)
        rows.append(_scenario(f'A4 lightning drain{drain} p{int(power)} c{int(crit)}', replace(base, element=ref.LIGHTNING, mult_drain=drain, power=power),
                              _draw_proc(ref.LIGHTNING, 0.0, 17, crit)))
    for owned in (False, True):
        rows.append(_scenario(f'A4 wind tailwind{int(owned)}', replace(base, element=ref.WIND, level={4: 20}, mult_recovery=2.0,
                              branches={ref.NODES['kWindTailwind']} if owned else set()), _draw_proc(ref.WIND, 0.5)))
        rows.append(_scenario(f'A4 water clear{int(owned)}', replace(base, element=ref.WATER, water_clear=45.0,
                              branches={ref.NODES['kWaterClearStream']} if owned else set()), _draw_proc(ref.WATER, 0.5)))
    # A5: twin (left hand, window, twin element) and echo (pending, previous element, ratio).
    for left, window, twin in itertools.product((False, True), (False, True), (0, ref.FIRE, ref.LIGHTNING, ref.FROST)):
        state = replace(base, element=ref.FROST, left=left, twin_window=window, twin=twin, ranks=_rich_nodes(ref.LIGHTNING) | _rich_nodes(ref.FIRE), stage=1)
        draws = _draw_proc(ref.FROST, 0.3)
        if left and window and twin not in (0, ref.FROST):
            draws += _draw_proc(twin, 0.9, 20, True)
        rows.append(_scenario(f'A5 twin left{int(left)} win{int(window)} twin{twin}', state, draws))
    for pending, prev, echo, points in itertools.product((False, True), (0, ref.WATER, ref.ASTRAL), (False, True), (0, 5)):
        state = replace(base, element=ref.ASTRAL, echo_pending=pending, prev=prev, power=True,
                        branches={ref.NODES['kCommonEcho']} if echo else set(),
                        ranks={ref.NODES['kCommonEchoRatio']: points} if points else {})
        draws = _draw_proc(ref.ASTRAL, 0.2)
        ratio = (0.5 if echo else 0) + points * 0.03 * 3
        if pending and prev not in (0, ref.ASTRAL) and ratio > 0:
            draws += _draw_proc(prev, 0.7)
        rows.append(_scenario(f'A5 echo pend{int(pending)} prev{prev} br{int(echo)} pts{points}', state, draws))
    # A6: no-form hits.
    nf = replace(base, element=0, level={11: 20})
    for power, (t_mp, t_max), (mp, mp_max) in itertools.product(
            (False, True), ((0.0, 0.0), (5.0, 100.0), (40.0, 200.0), (1000.0, 1000.0)), ((0.0, 150.0), (10.0, 150.0), (200.0, 200.0))):
        rows.append(_scenario(f'A6 nf p{int(power)} t{t_mp}/{t_max} me{mp}/{mp_max}', replace(nf, power=power, t_mp=t_mp, t_mp_max=t_max, mp=mp, mp_max=mp_max), []))
    for seize, depletion, still, low, devour, caster in itertools.product((False, True), repeat=6):
        branches = set()
        for flag, key in ((seize, 'kNoFormSeize'), (depletion, 'kNoFormDepletion'), (still, 'kNoFormStillness'), (devour, 'kNoFormDevour')):
            if flag:
                branches.add(ref.NODES[key])
        ranks = {}
        if low:
            ranks[ref.NODES['kNoFormLowMagicka']] = 8
        if caster:
            ranks[ref.NODES['kNoFormBurnCasters']] = 12
        for power, t_mp in ((False, 20.0), (True, 0.0), (True, 400.0)):
            state = replace(nf, power=power, branches=branches, ranks=ranks, silenced=still, spell_user=caster,
                            t_mp=t_mp, t_mp_max=500.0, mp=120.0, mp_max=300.0, seize_pct=12.0)
            rows.append(_scenario(f'A6 nodes sz{int(seize)} dp{int(depletion)} st{int(still)} lo{int(low)} dv{int(devour)} ca{int(caster)} p{int(power)} t{t_mp}', state, []))
    for still, t_mp, low_points in itertools.product((False, True), (60.0, 200.0), (0, 8)):
        # Small dispel with magicka left after the siphon (60/500 is below 25%, 200/500 is not), so its true
        # damage carries the 靜寂 x1.5 and low-magicka multipliers (review round 20: the cases above burn nothing).
        state = replace(nf, power=False, branches={ref.NODES['kNoFormStillness']} if still else set(), silenced=still,
                        ranks={ref.NODES['kNoFormLowMagicka']: low_points} if low_points else {},
                        t_mp=t_mp, t_mp_max=500.0, mp=120.0, mp_max=300.0)
        rows.append(_scenario(f'A6 small dispel st{int(still)} t{t_mp} lo{low_points}', state, []))
    for level, mult, power in itertools.product((1, 25, 50, 75, 100), (0.25, 1.0, 1.7, 3.0), (False, True)):
        # 2.8 baseline across tree level x damage multiplier x power (the round-8 Papyrus cases, now the DLL's)
        rows.append(_scenario(f'A6 baseline L{level} m{mult} p{int(power)}', replace(nf, level={11: level}, base_damage_mult=mult, power=power), []))
    for power in (False, True):   # MultRecovery 0: the siphon gives nothing, so an empty pool stays empty (no dispel)
        rows.append(_scenario(f'A6 no recovery p{int(power)}', replace(nf, power=power, mult_recovery=0.0, t_mp=500.0, t_mp_max=500.0, mp=0.0, mp_max=100.0), []))
    for points, vip, duration in itertools.product((0, 5, 15), (False, True), (0.5, 1.0, 2.0, 3.0)):
        state = replace(nf, power=True, ranks={ref.NODES['kNoFormSilence']: points} if points else {}, vip=vip,
                        mult_duration=duration, t_mp=10.0, t_mp_max=50.0, mp=100.0, mp_max=100.0)
        rows.append(_scenario(f'A6 silence pts{points} vip{int(vip)} dur{duration}', state, []))
    # A7 (round 21): the v0.4 nodes the DLL now reads - 吸魔量, 反擊, 滅法倍率, 燒魔倍數, 寂滅 (R5) and the
    # soaked slow's duration (R6).
    for points, window, owned, power in itertools.product((0, 5, 15), (False, True), (False, True), (False, True)):
        state = replace(nf, power=power, riposte=window, t_mp=400.0, t_mp_max=400.0, mp=150.0, mp_max=300.0,
                        ranks={ref.NODES['kNoFormSiphonAmount']: points} if points else {},
                        branches={ref.NODES['kNoFormRiposte']} if owned else set())
        rows.append(_scenario(f'A7 siphon pts{points} win{int(window)} own{int(owned)} p{int(power)}', state, []))
    for rate, multiple, power, t_mp in itertools.product((0, 7, 15), (0, 15), (False, True), (30.0, 900.0)):
        ranks = {}
        if rate:
            ranks[ref.NODES['kNoFormDispelRate']] = rate
        if multiple:
            ranks[ref.NODES['kNoFormBurnMultiple']] = multiple
        state = replace(nf, power=power, ranks=ranks, t_mp=t_mp, t_mp_max=900.0, mp=200.0, mp_max=400.0)
        rows.append(_scenario(f'A7 dispel rate{rate} mult{multiple} p{int(power)} t{t_mp}', state, []))
    for layers, spent, owned, power in itertools.product((0, 2, 3, 5), (False, True), (False, True), (False, True)):
        state = replace(nf, power=power, hush=layers, hush_spent=spent, t_mp=300.0, t_mp_max=300.0, mp=200.0, mp_max=200.0,
                        branches={ref.NODES['kNoFormHushBreak']} if owned else set())
        rows.append(_scenario(f'A7 hush {layers} spent{int(spent)} own{int(owned)} p{int(power)}', state, []))
    for points, duration in itertools.product((0, 1, 5, 14, 15), (0.25, 0.5, 1.0, 1.4, 2.0, 3.0)):
        state = replace(base, element=ref.EARTH, wet=True, mult_duration=duration,
                        ranks={ref.NODES['kWaterSoakDuration']: points} if points else {})
        rows.append(_scenario(f'A7 soak pts{points} dur{duration}', state, _draw_proc(ref.EARTH, 0.4)))
    return rows


def write(b, settings, write_if_changed, root):
    ref.load(settings)
    table = dict(
        source='build/fix20_reference.py (v0.4 formulas)',
        config=dict(damage=[list(ref.DAMAGE[e]) for e in range(1, 12)], noform_base_true=ref.NOFORM_BASE),
        scenarios=scenarios())
    write_if_changed(root / TABLE, json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    return len(table['scenarios'])


def wiring(b, nodes, spells, globals_, write_if_changed, root):
    """Group B expectations from the generator's record identities (checked against the built ESP later)."""
    main = {}
    for name, slot in nodes.items():
        if len(slot) == 3:
            t, r, k = slot
            node = (t * 3 + r) * 5 + k
            main[name] = [b.ID_MAIN_PERK + node * b.plan_trees.MAIN_MAX_RANK + rank for rank in range(b.plan_trees.MAIN_MAX_RANK)]
    branch = {}
    for name, slot in nodes.items():
        if len(slot) == 4:
            t, r, k, n = slot
            branch[name] = b.ID_BRANCH_PERK + ((t * 3 + r) * 5 + k) * b.plan_trees.MAX_BRANCH + n
    data = dict(main_perks=main, branch_perks=branch, slots={k: list(v) for k, v in nodes.items()},
                globals=globals_, spells=spells)
    write_if_changed(root / WIRING, json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    return data
