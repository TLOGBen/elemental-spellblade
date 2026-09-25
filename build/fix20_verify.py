"""Round 20 (slice N2): the Papyrus side of "the DLL computes the proc magnitude at hit time".

Executes the actual Papyrus sources with the source-level harness (natives mocked; not the game runtime):
  MIRROR     the difference patch's mirror of the DLL share (NativeProcUnit x NativeNodeSum) equals the mean of
             the DLL's proc in build/fix20_reference.py - the model the native tests use - for every element,
             attack kind, node profile, sync stage, level, damage multiplier, environment, blood health / 逆流 / 血怒
             and divine target kind;
  CARRIED    the target-side / script-state additions (HitExtra, HitExtraMult) are exactly what the pre-round-20
             HitMult added on top of the node percentages the DLL now owns, for every element and target state;
  PATCH      ApplyProc casts unit x ((S + X) x M - S) and nothing when that is <= 0, with unit / S from the
             reference and X / M from the pre-round-20 functions (not from the code under test);
  UNTOUCHED  every other script is byte-identical to the pre-round-20 snapshot and, in the six edited scripts,
             every function outside the declared N2 set is unchanged (the status layer is not touched);
  NO-WRITE   nothing pre-writes a proc spell magnitude any more;
  MARKERS    a switch applies the echo / twin markers the DLL reads; leaving a form clears the 護血 pool.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import itertools, json, math, re, runpy, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix20_reference as ref
from papyrus_harness import Script

NEW = ROOT / 'src'
BEFORE = ROOT / '.codex/pre-fix20-snapshot/src'
F18 = runpy.run_path(str(ROOT / 'build/fix18_verify.py'))
fixture, ranks = F18['fixture'], F18['ranks']
SETTINGS = json.loads((ROOT / 'settings.json').read_text(encoding='utf8'))
ref.load(SETTINGS)

# Functions round 20 changed, per script; everything else in these scripts must be byte-identical.
CHANGED = {
    'ESSBController.psc': {'OnWeaponHit', 'ApplyProc', 'ApplyBonusProc', 'ApplyExtraProc', 'DifferenceMult', 'NativeProcUnit',
                           'NativeNodeSum', 'NativeBloodCurve', 'LinearBloodCurve', 'DifferencePossible', 'OnNoFormHit',
                           'OnFormSwitched', 'CloseForm', 'ClearSelfAll', 'ApplySelfMarker', 'Leech', 'AddSelf', 'ClearSelf',
                           'TickTimers', 'EnvCheck', 'Setup', 'SwitchForm', 'RefreshTrees', 'RefreshAbilities', 'OnSyncStage',
                           'SetMolten', 'SetOpenBoost', 'SetEndBoost', 'SetBloodthirst', 'RefreshRuntimeValues',
                           'ValidateBindings', 'OnPlayerLoadGame'},
    'ESSBElem.psc': {'HitExtra', 'HitExtraMult', 'FireHitExtra', 'FrostHitExtra', 'ShockHitExtra'},
    'ESSBElem2.psc': {'HitExtra', 'EarthHitExtra', 'BloodHitExtra', 'DivineHitExtra', 'OnHit', 'OnEarthHit', 'OnWindHit'},
    'ESSBElem3.psc': {'HitExtra', 'PoisonHitExtra', 'WaterHitExtra', 'DarkHitExtra', 'AstralHitExtra', 'DarkHitExtraMult',
                      'OnWaterHit', 'OnDarkHit'},  # OnDarkHit: a comment that named the removed OnBloodHit
    'ESSBNoForm.psc': {'OnInterruptCast'},
    'ESSBTrees.psc': {'RefreshTree', 'RefreshActive'},
}
REMOVED = {
    'ESSBController.psc': {'RefreshProcMagnitudes', 'InitProcCache', 'PlayerElementMult', 'PlayerProcBase', 'ApplyBakedProc',
                           'TargetProcPossible', 'GetHitMult', 'ApplyNoFormBaseline'},
    'ESSBElem.psc': {'HitMult', 'FireHitMult', 'FrostHitMult', 'ShockHitMult'},
    'ESSBElem2.psc': {'HitMult', 'EarthHitMult', 'WindHitMult', 'BloodHitMult', 'DivineHitMult', 'OnBloodHit'},
    'ESSBElem3.psc': {'HitMult', 'PoisonHitMult', 'WaterHitMult', 'DarkHitMult', 'AstralHitMult'},
    'ESSBNoForm.psc': {'OnManaBreak', 'ApplySilence'},
    'ESSBTrees.psc': set(),
}


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-6)


def prepare(f, st):
    """Put a reference State into a harness controller."""
    c = f.c
    for tree in range(13):
        f.t.LevelCache[tree] = st.level.get(tree, 1)
        for route in range(3):
            for tier in range(5):
                bits = sum(1 << slot[3] for slot in st.branches if slot[:3] == (tree, route, tier))
                ranks(f, tree, route, tier, st.ranks.get((tree, route, tier), 0), bits)
    c.overrides['SyncStage'] = lambda: st.stage
    c.fields['CachedNodeScale'] = st.node_scale
    c.BaseDamageMult.v = st.base_damage_mult
    c.EnvNight.v = int(st.night)
    f.p.IsInInterior = lambda: st.interior
    f.p.GetActorValuePercentage = lambda av: st.hp / st.hp_perm if av == 'Health' else 1.0
    c.overrides['IsUndeadOrDaedra'] = lambda target: st.undead
    c.overrides['IsNecromancer'] = lambda target: st.necro


def mirror():
    cases = 0
    f = fixture()
    full = {(12, 1, 0): 4, (12, 1, 3): 2, (12, 0, 1): 6, (12, 0, 3): 5}
    for element, power, sneak, profile, stage, level, mult, scale in itertools.product(
            range(1, 12), (False, True), (False, True), ('none', 'element', 'all'), (0, 2, 3), (1, 40, 100), (1.0, 1.7), (3.0, 1.5)):
        if sneak and element != ref.WIND:
            continue
        r = {}
        if profile != 'none' and ref.adept(element):
            r[ref.adept(element)] = 7
            r[ref.master(element)] = 3
        if profile == 'all':
            r |= full
        st = ref.State(element=element, power=power, sneak=sneak, ranks=r, stage=stage, level={element - 1: level},
                       base_damage_mult=mult, node_scale=scale)
        prepare(f, st)
        got = f.c.NativeProcUnit(element, power, sneak, f.v) * f.c.NativeNodeSum(element, power)
        assert close(got, ref.expected_mean_proc(st, element)), (element, power, sneak, profile, stage, level, mult, scale, got)
        cases += 1
    # Environment, divine target kinds, blood health / 逆流 / 血怒.
    for element, night, interior, undead, necro, exorcism in itertools.product(
            (ref.DIVINE, ref.DARKNESS, ref.FIRE), (False, True), (False, True), (False, True), (False, True), (False, True)):
        st = ref.State(element=element, night=night, interior=interior, undead=undead, necro=necro,
                       branches={ref.NODES['kDivineExorcism']} if exorcism else set())
        prepare(f, st)
        got = f.c.NativeProcUnit(element, False, False, f.v) * f.c.NativeNodeSum(element, False)
        assert close(got, ref.expected_mean_proc(st, element)), (element, night, interior, undead, necro, exorcism, got)
        cases += 1
    for hp, reverse, rage, power in itertools.product((100, 99, 85, 70, 69.9, 55, 50, 30, 29.9, 20, 10, 5, 0), (False, True), (False, True), (False, True)):
        branches = ({ref.NODES['kBloodReverse']} if reverse else set()) | ({ref.NODES['kBloodRage']} if rage else set())
        st = ref.State(element=ref.BLOOD, power=power, hp=float(hp), branches=branches)
        prepare(f, st)
        got = f.c.NativeProcUnit(6, power, False, f.v) * f.c.NativeNodeSum(6, power)
        assert close(got, ref.expected_mean_proc(st, ref.BLOOD)), (hp, reverse, rage, power, got)
        cases += 1
    return cases


# ---------------------------------------------------------------- target-side terms carried over

class Target:
    def __init__(self, magicka):
        self.mag = magicka
        self.hits = []

    def GetActorValue(self, av):
        return self.mag if av == 'Magicka' else 1000.0

    def GetActorValuePercentage(self, av):
        return self.mag / 100.0 if av == 'Magicka' else 1.0

    def GetEquippedSpell(self, slot):
        return object()

    def HasMagicEffectWithKeyword(self, kw):
        return False

    def IsDead(self):
        return False

    def GetFormID(self):
        return 7


STATES = {  # name: (stacks per kind, open boost, overheat, molten, domain, target magicka, all branches, node ranks)
    'plain': ({}, 0, 0, 0, False, 50.0, False, False),   # nothing bought: only script timers can make a difference
    'bare': ({}, 0, 0, 0, False, 50.0, False, True),
    'overheat': ({1: 4}, 0, 1, 0, False, 50.0, False, True),   # overheat without 熔爐 (+50%)
    'hot': ({1: 6, 2: 5, 6: 3, 9: 4, 10: 5, 11: 3}, 1, 1, 1, True, 0.0, True, True),
    'mixed': ({1: 2, 2: 2, 6: 1, 9: 1, 10: 2, 11: 1}, 1, 0, 1, False, 10.0, True, True),
}


def rank_of(state, tree, route, tier):
    return 5 + (tree + route + tier) % 7 if state[7] else 0


def dress(f, state, element):
    stacks, boost, overheat, molten, domain, magicka, branches, _ = state
    c = f.c
    f.env['ESSBNoForm'] = F18['Measured'](c.path.parent / 'ESSBNoForm.psc', f.env)
    c.overrides.update(GetStack=lambda target, kind: stacks.get(kind, 0), GetOpenBoost=lambda e: boost,
                       GetSelf=lambda kind: overheat if kind == 4 else 0, GetMoltenLeft=lambda: molten,
                       InDomain=lambda target, e: domain, HasElementMark=lambda target, e: True,
                       GetAirborne=lambda target: 0, HasStarLock=lambda target: False)
    for tree in range(13):
        for route in range(3):
            for tier in range(5):
                ranks(f, tree, route, tier, rank_of(state, tree, route, tier), 15 if branches else 0)
    c.overrides['SyncStage'] = lambda: 2
    return Target(magicka)


def old_node_part(f, element):
    """The node percentages the pre-round-20 HitMult added that the DLL now owns (adept, master x stage, 驅魔)."""
    c = f.c
    if element == 9:
        return 0.0
    tree = element - 1
    nodes = f.env['ESSBNodes']
    part = nodes.Pct(c, c.Rank(tree, 0, 1), 0.01) + nodes.Pct(c, c.Rank(tree, 0, 3), 0.01) * c.SyncStage()
    return part


def carried():
    cases = 0
    for element, (name, state), power in itertools.product(range(1, 12), STATES.items(), (False, True)):
        old, new = fixture(BEFORE), fixture()
        targets = [dress(g, state, element) for g in (old, new)]
        for g in (old, new):
            g.c.overrides['IsNecromancer'] = lambda target: True
        before = old.env['ESSBElem'].HitMult(old.c, element, targets[0], power)
        extra = new.env['ESSBElem'].HitExtra(new.c, element, targets[1], power)
        mult = new.env['ESSBElem'].HitExtraMult(new.c, element, targets[1])
        exorcism = 0.5 if element == 7 and old.c.Br(6, 0, 0, 1) else 0.0   # additive in HitMult, now the DLL's x1.5
        expected = (before / mult) - 1 - old_node_part(old, element) - exorcism
        assert close(extra, expected), (element, name, power, before, extra, mult)
        cases += 1
    return cases


def patch_case(element, state, power, sneak, opening, thirst, endboost, only=None, streak=False):
    """One ApplyProc call against its expected value. `only` = (tree, route, tier, rank, bits) bought on top of `state`."""
    old, new = fixture(BEFORE), fixture()
    targets = [dress(g, state, element) for g in (old, new)]
    for g in (old, new):
        g.c.overrides.update(IsNecromancer=lambda target: False, IsUndeadOrDaedra=lambda target: False, TakeKillStreak=lambda: streak)
        g.c.fields.update(BloodthirstLeft=200.0 if thirst else 0.0, EndBoostLeft=200.0 if endboost else 0.0, EndBoostAmount=0.3)
        g.p.IsInInterior = lambda: True
        if only:
            ranks(g, *only)
    new.c.fields['NativeHit'] = new.G(1)
    new.c.MultDrain.v = 1.0
    # Reference share of the DLL: the same node ranks, stage 2, level 1, interior (no environment term).
    rank_map = {(t, r, k): rank_of(state, t, r, k) for t in range(13) for r in range(3) for k in range(5)}
    branch_set = {(t, r, k, n) for t in range(13) for r in range(3) for k in range(5) for n in range(4)} if state[6] else set()
    if only:
        rank_map[only[:3]] = only[3]
        branch_set |= {only[:3] + (n,) for n in range(4) if only[4] >> n & 1}
    st = ref.State(element=element, power=power, sneak=sneak, stage=2, interior=True, ranks=rank_map, branches=branch_set)
    st.hp = st.hp_perm * 1.0
    unit, s = ref.mean_unit(st, element), ref.node_sum(st, element)
    before = old.env['ESSBElem'].HitMult(old.c, element, targets[0], power)
    void = new.env['ESSBElem'].HitExtraMult(new.c, element, targets[1])
    x = before / void - 1 - old_node_part(old, element)
    m = void * old.env['ESSBElem2'].TargetDamageMult(old.c, targets[0]) * old.env['ESSBElem3'].TargetDamageMult(old.c, targets[0])
    m *= (1.2 if thirst else 1.0) * (1.3 if endboost else 1.0)
    if element == 5 and sneak:
        m *= old.env['ESSBElem2'].SneakMult(old.c) / 3.0 * old.env['ESSBElem2'].KillStreakMult(old.c)   # 連殺 x2 (pre-20: full *= sneak x streak)
    if opening:
        m *= old.env['ESSBNodes'].OpenStrikeMult(old.c) * old.env['ESSBElem'].OpenStrikeMult(old.c, element)
    expected = unit * ((s + x) * m - s)
    possible = new.c.DifferencePossible(element, power, sneak, opening)
    new.apps.clear()
    new.c.ApplyProc(targets[1], element, power, sneak, opening)
    got = new.apps[-1]['values'][0] if new.apps else 0.0
    if expected > 1e-6:
        assert len(new.apps) == 1 and close(got, expected), (element, state, power, sneak, opening, thirst, endboost, only, got, expected)
        if element == 3:
            assert close(new.apps[-1]['values'][1], expected * 0.5 * new.c.MultDrain.GetValue())
    else:
        assert not new.apps, (element, state, power, sneak, opening, only, got, expected)
    return expected, possible


def patch():
    """ApplyProc casts unit x ((S + X) x M - S), the terms taken from the reference and pre-round-20 code."""
    cases = 0
    for element, (name, state), power, sneak, opening, thirst, endboost in itertools.product(
            range(1, 12), STATES.items(), (False, True), (False, True), (False, True), (False, True), (False, True)):
        if sneak and element != 5:
            continue
        if name in ('mixed', 'overheat') and (thirst or endboost):
            continue
        patch_case(element, state, power, sneak, opening, thirst, endboost)
        cases += 1
    return cases


# DifferencePossible's per-element gates, each node bought alone on a target carrying every status stack
# (review round 20: in patch() an earlier shared gate always answered first, so these lines were never decisive).
GATE_TARGET = ({1: 6, 2: 5, 6: 3, 9: 4, 10: 5, 11: 3}, 0, 0, 0, False, 50.0, False, False)
DRAINED = GATE_TARGET[:5] + (0.0,) + GATE_TARGET[6:]   # lightning and 虛空 need a target with (almost) no magicka
GATES = [  # (element, power, sneak, opening, node = (tree, route, tier, rank, bits), options)
    (2, False, False, False, (1, 0, 2, 5, 0), {}),     # frost: Rank(1, 0, 2)
    (3, False, False, False, (2, 1, 3, 0, 4), dict(state=DRAINED)),   # lightning: Br(2, 1, 3, 2)
    (5, False, True, False, (4, 2, 4, 0, 2), dict(streak=True)),   # wind sneak kill streak: Br(4, 2, 4, 1)
    (5, False, True, False, (4, 0, 3, 0, 4), {}),      # wind sneak 暗風: Br(4, 0, 3, 2)
    (9, False, False, False, (8, 0, 1, 0, 1), {}),     # poison: Br(8, 0, 1, 0)
    (10, False, False, False, (9, 0, 3, 0, 1), dict(state=DRAINED)),   # dark 虛空 (caster below 25% magicka): Br(9, 0, 3, 0)
    (11, True, False, False, (10, 0, 2, 0, 1), {}),    # astral power: Br(10, 0, 2, 0)
]


def gates():
    cases = 0
    for element, power, sneak, opening, node, options in GATES:
        target, streak = options.get('state', GATE_TARGET), options.get('streak', False)
        expected, possible = patch_case(element, target, power, sneak, opening, False, False, node, streak)
        assert expected > 1e-6 and possible, ('gate node gives no difference, or the gate misses it', element, node, expected, possible)
        expected, possible = patch_case(element, target, power, sneak, opening, False, False, None, streak)
        assert expected <= 1e-6 and not possible, ('gate open without its node', element, node, expected, possible)
        cases += 2
    for element, node in ((5, (4, 2, 4, 0, 2)), (11, (10, 0, 2, 0, 1))):   # the same nodes do nothing off their condition
        expected, possible = patch_case(element, GATE_TARGET, False, False, False, False, False, node, True)
        assert expected <= 1e-6 and not possible, ('condition ignored', element, node, expected, possible)
        cases += 1
    return cases


# ---------------------------------------------------------------- structure

def functions(path):
    source = path.read_text(encoding='utf8')
    return {m[1]: m[0] for m in re.finditer(r'(?ms)^(?:\w+(?:\[\])? )?(?:Function|Event) (\w+)\(.*?^End(?:Function|Event)\b', source)}


def untouched():
    changed_files = set(CHANGED)
    identical = 0
    for old in sorted(BEFORE.glob('*.psc')):
        new = NEW / old.name
        assert new.exists(), old.name
        if old.name == 'ESSBState.psc':
            # Generated by build_v03.write_state_helpers from state_schema_version: only the main quest ID moves.
            import state_schema
            versions = [json.loads(p.read_text(encoding='utf8'))['state_schema_version'] for p in (BEFORE.parent / 'settings.json', ROOT / 'settings.json')]
            ids = [f"0x{state_schema.quest_ids(v)['ESSB_MainQuest']:06X}" for v in versions]
            assert old.read_bytes().replace(ids[0].encode(), ids[1].encode()) == new.read_bytes(), ('ESSBState.psc', ids)
            identical += 1
            continue
        if old.name not in changed_files:
            assert old.read_bytes() == new.read_bytes(), ('script outside the N2 set changed', old.name)
            identical += 1
            continue
        before, after = functions(old), functions(new)
        assert set(before) - set(after) == REMOVED[old.name], (old.name, set(before) - set(after))
        for name, text in after.items():
            if name in CHANGED[old.name]:
                continue
            assert before.get(name) == text, (old.name, name, 'changed outside the declared N2 set')
        for name in CHANGED[old.name]:  # the declared set is exact: each one really is new or different
            assert name in after and before.get(name) != after[name], (old.name, name, 'declared changed but unchanged')
    assert sorted(p.name for p in NEW.glob('*.psc')) == sorted(p.name for p in BEFORE.glob('*.psc'))
    return identical


def no_prewrite():
    source = '\n'.join(p.read_text(encoding='utf8') for p in NEW.glob('*.psc'))
    assert 'RefreshProcMagnitudes' not in source and 'ProcVariants' not in source
    writes = re.findall(r'(\w+)(?:\[[^\]]*\])?\.SetNthEffectMagnitude\(', source)
    assert not {'HitNormalSpells', 'HitPowerSpells'} & set(writes), writes
    ctl = functions(NEW / 'ESSBController.psc')
    assert [n for n, t in ctl.items() if 'procSpell.SetNthEffectMagnitude' in t] == ['ApplyBonusProc']
    return len(writes)


def markers():
    events = []
    f = fixture()
    c = f.c

    class Marker:
        def __init__(self, name):
            self.name = name

        def SetNthEffectDuration(self, i, seconds):
            events.append((self.name, 'duration', seconds))

    echo, twin, guard = Marker('echo'), Marker('twin'), Marker('guard')
    c.fields.update(EchoPendingSpell=echo, TwinWindowSpell=twin, BloodGuardSpell=guard)
    f.p.DoCombatSpellApply = lambda spell, target: events.append((spell.name, 'cast', target is f.p))
    f.p.DispelSpell = lambda spell: events.append((spell.name, 'dispel'))
    c.overrides.update(RefreshSyncStage=lambda: None, PushSelf=lambda: None, SyncRockArmor=lambda: None, SetGlobal=lambda *a: None)
    nodes = f.env['ESSBNodes']
    results = {}
    for echo_on, twin_on in itertools.product((False, True), repeat=2):
        events.clear()
        nodes.overrides.update(EchoRatio=lambda ctl, on=echo_on: 0.5 if on else 0.0, HasTwin=lambda ctl, on=twin_on: on)
        c.OnFormSwitched(2, 3)
        casts = [e for e in events if e[1] == 'cast']
        assert (('echo', 'cast', True) in casts) == echo_on and (('twin', 'cast', True) in casts) == twin_on, events
        if twin_on:
            assert ('twin', 'duration', c.DurationInt(30.0)) in events
        assert ('guard', 'dispel') in events, 'switching must clear the 護血 pool'
        results[(echo_on, twin_on)] = len(events)
    return len(results)


def run():
    report = dict(mirror=mirror(), carried=carried(), patch=patch(), gates=gates(), untouched_scripts=untouched(),
                  magnitude_writes=no_prewrite(), marker_cases=markers(), runtime_tested=False)
    (ROOT / 'build/fix20-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f"FIX20 PAPYRUS ok: mirror {report['mirror']} cases == reference DLL mean; carried target-side terms {report['carried']} "
          f"== pre-20 HitMult minus DLL nodes; ApplyProc {report['patch']} cases == unit x ((S+X) x M - S); "
          f"DifferencePossible {report['gates']} element-gate cases; "
          f"{report['untouched_scripts']} scripts byte-identical + declared N2 functions only; no proc magnitude pre-write; "
          f"{report['marker_cases']} switch-marker cases")
    return report


if __name__ == '__main__':
    run()
