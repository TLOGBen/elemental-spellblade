"""Regression scenarios executing selected real Papyrus bodies with native mocks.
Run from campaign root: python build/fix_round_regression.py
This is deterministic source logic validation, not an in-game test.
"""
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace as NS
from papyrus_harness import Script, Array

ROOT = Path(__file__).resolve().parents[1]
results = []
clock = NS(now=100.0)
utility = NS(GetCurrentRealTime=lambda: clock.now, RandomFloat=lambda lo, hi: 0.99)
ranks, branches = {}, set()
nodes = NS(Rank=lambda ctl, t, r, k: ranks.get((t, r, k), 0),
           Br=lambda ctl, t, r, k, b: (t, r, k, b) in branches,
           OmniMult=lambda ctl: 1.0, TreeOf=lambda e: e - 1)
env = {'Utility': utility, 'ESSBNodes': nodes}
elem = Script(ROOT / 'src/ESSBElem.psc', env)
elem2 = Script(ROOT / 'src/ESSBElem2.psc', env)
elem3 = Script(ROOT / 'src/ESSBElem3.psc', env)
env.update(ESSBElem=elem, ESSBElem2=elem2, ESSBElem3=elem3,
           ESSBReactions=NS(BaseMax=lambda e: {1: 10, 2: 7, 5: 6, 6: 8, 10: 7, 11: 8}.get(e, 5),
                           ReactDamage=lambda ctl, e, k: k))


def check(name, run):
    run()
    results.append({'test': name, 'result': 'PASS'})
    print('PASS', name)


def equal(a, b):
    assert a == b, (a, b)


def close(a, b):
    assert math.isclose(a, b, abs_tol=1e-8), (a, b)


def formulas():
    ctl = NS(SyncStage=lambda: 3, GetOpenBoost=lambda e: 5)
    ranks.clear(); branches.clear()
    close(elem.IgniteMult(ctl, 10), 2.0)
    close(elem.IgniteMult(ctl, 15), 2.0)
    ranks[(0, 0, 4)] = 15
    ranks[(0, 2, 2)] = 15
    close(elem.IgniteMult(ctl, 10), 3.5)
    ranks[(4, 2, 4)] = 15
    close(elem2.LandingDamage(ctl), 1.25)
    branches.add((4, 2, 1, 0))
    close(elem2.LandingDamage(ctl), 1.75)
    ranks.clear(); branches.clear()
    ranks.update({(8, 0, 1): 15, (8, 0, 3): 15, (4, 1, 1): 15})
    close(elem3.WaterHitMult(ctl, None, False), 1.0)
    close(elem2.WindHitMult(ctl, None, False), 1.0)


def controller():
    vm = Script(ROOT / 'src/ESSBController.psc', env)
    vm.InitRegistry()
    return vm


def trio():
    vm = controller()
    for now, element, expected in [(100, 1, 1), (109, 2, 2), (118, 3, 2),
                                    (130, 1, 1), (134, 2, 2), (139, 3, 3)]:
        clock.now = now
        equal(vm.PushTrio(element), expected)
    for now in [150, 159, 168]:
        clock.now = now
        equal(vm.PushTrio(1), 1)
    clock.now = 177
    equal(vm.PushTrio(2), 2)
    clock.now = 186
    equal(vm.PushTrio(3), 2)


def blood_cost():
    ranks.clear(); branches.clear(); branches.add((5, 0, 4, 0))
    vm = controller()
    vm.overrides['ThePlayer'] = lambda: NS(GetActorValuePercentage=lambda av: 1.0)
    vm.overrides['SyncStage'] = lambda: 3
    vm.fields['FormActive'] = NS(GetValueInt=lambda: 1)
    vm.fields['CurrentElement'] = NS(GetValueInt=lambda: 6)
    close(vm.BloodDrainPerSecond(), 0.0)
    close(vm.BloodPowerCost(), 0.08)


def shadow_body():
    ranks.clear(); branches.clear(); branches.add((9, 0, 4, 0))
    windows = []
    ctl = NS(SetGuardDark=lambda n: windows.append(n), SyncStage=lambda: 3)
    elem3.OnShadowBody(ctl)
    equal(windows, [0])


def status():
    damage, stars = [], []
    ctl = NS(StackCap=lambda k: {5: 8, 11: 9}.get(k, 0),
             GetDamageMult=lambda e: 1.0, GetBloodHitMult=lambda: 1.0,
             IsVIPTarget=lambda a: False, ApplyBleedDrain=lambda *a: None,
             ApplyDamage=lambda e, amount, a: damage.append((e, amount)),
             LogThrottled=lambda *a: None, DebugLevel=NS(GetValueInt=lambda: 0),
             SpreadPoison=lambda *a: None, ThePlayer=lambda: None)
    holder = NS(GetActorValueMax=lambda av: 200.0, GetActorValue=lambda av: 100.0,
                GetFormID=lambda: 123, IsDead=lambda: False)
    local = dict(env)
    local['ESSBElem3'] = NS(AstralDelay=lambda c: 2, AstralForesee=lambda c: None,
        WetSeconds=lambda c: 10, PoisonTickMult=lambda c, b: 1.0,
        CatalyzeRate=lambda c: 2, SpreadInterval=lambda c: 2,
        SpreadThreshold=lambda c: 999, PoisonTickHook=lambda *a: None,
        DeathCurseLostRatio=lambda c: .15, AfterDeathCurse=lambda *a: None,
        DetonateAstral=lambda c, h, n, w, mult=1.0: stars.append((n, w, mult)))
    local['ESSBElem'] = NS(FrozenExtraSeconds=lambda c: 0,
        HasTinder=lambda c: False, FrozenResidual=lambda c, n: 0,
        OnFrozenTick=lambda *a: None)
    local['ESSBElem2'] = NS(BleedPerLayer=lambda c: 0.64,
                           BleedDrainPercent=lambda c, vip: .003)
    vm = Script(ROOT / 'src/ESSBStatus.psc', local)
    vm.fields.update(Ctl=ctl, Holder=holder)
    vm.InitRings()
    return vm, ctl, damage, stars


def poison_interleave():
    vm, ctl, damage, stars = status()
    vm.AddStack(7, 1)
    def apply(e, amount, target):
        damage.append((e, amount))
        if len(damage) == 1:
            vm.AddStack(7, 1)  # hit arrives during the cross-script damage call
    ctl.ApplyDamage = apply
    for _ in range(7):
        vm.Tick()
    equal([round(v / .25) for e, v in damage if e == 8], [1, 2, 2, 2, 2, 2, 1])
    equal(vm.GetStack(7), 0)


def bleed_interleave():
    vm, ctl, damage, stars = status()
    vm.AddStack(5, 1)
    def apply(e, amount, target):
        damage.append((e, amount))
        if len(damage) == 1:
            vm.AddStack(5, 1)  # bleed refreshes the existing stack as designed
    ctl.ApplyDamage = apply
    for _ in range(6):
        vm.Tick()
    equal([round(v / .64) for e, v in damage if e == 6], [1, 2, 2, 2, 2, 2])
    equal(vm.GetStack(5), 0)


def delayed_payloads():
    vm, ctl, damage, stars = status()
    vm.AddAstral(2, 1.45)
    vm.SetCatalyze(2, 3.0)
    vm.SetDeathCurse(3, 14.0, 2.0)
    vm.SetFrozen(2.0)
    ints, floats = vm.ExportInts(), vm.ExportFloats()
    equal((len(ints), len(floats)), (27, 17))
    clone, cc, cd, cs = status()
    clone.ImportState(ints, floats)
    equal(clone.ExportInts(), ints)
    equal(clone.ExportFloats(), floats)
    clone.AddStack(7, 1)
    for _ in range(3):
        clone.Tick()
    equal([n for n, w, m in cs], [2])
    close(cs[0][1], 2.9)
    equal([round(v, 2) for e, v in cd if e == 8], [1.5, 1.5, .25])
    close([v for e, v in cd if e == 10][0], 58.0)
    # Backward-compatible old host payload.
    clone.ImportState(ints, Array(floats[:12]))
    close(clone.CatalyzeMult, 1.0)
    close(clone.DeathCurseMult, 1.0)


def stars_immediate_and_foresee():
    vm, ctl, damage, stars = status()
    warnings = []
    vm.env['ESSBElem3'].AstralDelay = lambda c: 1
    vm.env['ESSBElem3'].AstralForesee = lambda c: warnings.append(True)
    vm.AddAstral(2, 1.45)
    equal(warnings, [True])
    vm.DetonateAstralNow(2.0)
    equal(stars[0][0], 2); close(stars[0][1], 2.9); close(stars[0][2], 2.0)
    equal(vm.GetStack(11), 0)
    equal(list(vm.AstralWeight), [0.0, 0.0])


def swap_backup():
    vm = controller()
    for slot in range(8):
        ints = Array([slot * 100 + k for k in range(27)])
        floats = Array([slot * 100.0 + k / 10 for k in range(17)])
        vm.SaveSwapData(slot, ints, floats)
    vm.CancelSwap()  # timeout releases the lock, not the per-target data
    for slot in range(8):
        equal(vm.ReadSwapInts(slot), [slot * 100 + k for k in range(27)])
        equal(vm.ReadSwapFloats(slot), [slot * 100.0 + k / 10 for k in range(17)])
    vm.ClearSlot(3)
    equal(vm.BackupValid[3], False)
    equal(vm.BackupValid[4], True)


def marks_and_cooldown():
    vm = controller()
    target = NS(DispelSpell=lambda spell: None)
    vm.OccupySlot(0, target)
    vm.fields['RegElem'][0] = 1
    vm.fields['RegElem2'][0] = 2
    vm.fields['RegSecondReal'][0] = True
    vm.fields['RegSeq2'][0] = 20
    vm.fields['RegSecondUntil'][0] = 200.0
    vm.fields['MarkSpells'] = Array([True] * 11)
    ended = []
    vm.env = dict(env)
    vm.env['ESSBReactions'] = NS(End=lambda c, e, *a: ended.append(e))
    vm.env['ESSBNodes'] = NS(HasResidualMark=lambda c: False, Br=lambda *a: False)
    vm.overrides['PlaceFx'] = lambda *a: None
    primary = NS(Dispel=lambda: None)
    secondary = NS(Dispel=lambda: None)
    vm.OnMarkStart(1, target, primary)
    vm.OnMarkStart(2, target, secondary)
    equal(vm.RegMark[0], primary); equal(vm.RegMark2[0], secondary)
    equal(vm.WillOpen(target, 2), False)
    clock.now = 200
    vm.EndMark(0, 0, 1.0)
    equal(ended, [1]); equal(vm.RegElem[0], 2); equal(vm.RegMark[0], secondary)
    # Chain cannot repeat a consumed mark, and shares the same one-second gate.
    vm.EndLinkedMark(target, 2, 0.5)
    equal(ended, [1]); equal(vm.RegElem[0], 0)
    vm.EndLinkedMark(target, 2, .5)
    equal(ended, [1])
    clock.now = 202
    vm.fields['RegElem'][0] = 3; vm.fields['RegElem2'][0] = 4
    vm.EndBothMarks(0, 3.0)
    equal(ended, [1, 4, 3])


def domain_filter():
    vm = controller()
    vm.fields['DomainX'][0] = 1000.0
    vm.fields['DomainR'][0] = 100.0
    vm.overrides['IsValidTarget'] = lambda a: a is not None
    def actor(x):
        return NS(GetPositionX=lambda: x, GetPositionY=lambda: 0, GetPositionZ=lambda: 0)
    outsiders = [actor(x) for x in range(5)]
    inside = actor(1001)
    selected = vm.ScanDomainTargets(Array(outsiders + [inside]), 0)
    equal(selected[0], inside)
    equal(len([x for x in selected if x]), 1)


def frost_snapshot():
    ranks.clear(); branches.clear()
    branches.update({(1, 2, 4, 0), (1, 2, 3, 0)})
    state = {'freeze': 5, 'coffin': 0, 'area': 0}
    ctl = NS(GetStack=lambda a, k: state['freeze'],
             SetStack=lambda a, k, n: state.update(freeze=n),
             ApplyDamage=lambda *a: None, ApplyUtil=lambda *a: None,
             SetFrozen=lambda a, sec: state.update(freeze=5, coffin=sec))
    target = NS(GetActorValuePercentage=lambda av: .8,
                GetActorValue=lambda av: 100.0, IsDead=lambda: False)
    elem.Shatter(ctl, target, 1.0)
    equal(state['coffin'], 2.0)
    # No coffin branch: current freeze is zero, but glacier uses its entry snapshot.
    branches.remove((1, 2, 4, 0))
    elem.Shatter(ctl, target, 1.0)
    equal(state['freeze'], 0)
    elem.overrides['ShatterArea'] = lambda *a: state.update(area=state['area'] + 1)
    elem.EndFrostNodes(ctl, target, 2, 1.0, 5)
    equal(state['area'], 1)
    elem.overrides.pop('ShatterArea')


def shock_snapshot():
    ranks.clear(); branches.clear(); branches.add((2, 2, 3, 0))
    calls = []
    target, neighbour = object(), object()
    ctl = NS(GetSelf=lambda k: 0, ScanTargets=lambda *a: Array([neighbour]),
             HasElementMark=lambda a, e: True)
    elem.overrides['Discharge'] = lambda c, a, n, consume, mult: calls.append((n, consume))
    elem.EndShockNodes(ctl, target, 2, 1.0, 6)
    equal(calls, [(6, False)])
    elem.overrides.pop('Discharge')
    source = (ROOT / 'src/ESSBReactions.psc').read_text(encoding='utf8')
    body = re.search(r'Function End\(.*?\nEndFunction', source, re.S)[0]
    assert body.index('snapshot = akCtl.GetSelf(1)') < body.index('EndShock(akCtl')
    assert body.index('ESSBElem.OnEnd(') < body.rindex('ConsumeEndCharge(snapshot)')


def star_fall_feedback():
    ranks.clear(); branches.clear()
    branches.add((10, 2, 1, 1))
    hits, feedback = [], []
    ctl = NS(ApplyTrueDamage=lambda n, a, t: hits.append(('true', n, t)),
             ApplyDamage=lambda e, n, a: hits.append(('element', n, e)))
    for victim in ['centre', 'area']:
        elem3.FallHit(ctl, victim, 100.0, 1)
    equal(hits, [('true', 60.0, 10), ('true', 60.0, 10)])
    hits.clear(); ranks[(10, 0, 0)] = 15
    elem3.overrides['OnAstralDetonate'] = lambda c, a, n: feedback.append(n)
    elem3.DetonateAstral(ctl, 'victim', 2, 2.9, 2.0)
    close(hits[0][1], 2.9 * 2 * 1.3)
    equal(feedback, [2])
    elem3.overrides.pop('OnAstralDetonate')


def pending_status_start():
    vm = controller()
    target = object()
    vm.OccupySlot(0, target)
    vm.overrides['EnsureStatus'] = lambda *a: None
    vm.overrides['StackCap'] = lambda k: 9
    vm.SetStarLock(target, 3)
    vm.SetWetLock(target)
    vm.AddAstral(target, 2, 1.45)
    vm.SetDeathCurseOn(target, 3, 14, 2.0)
    vm.SetAirborne(target, 2, 7.5)
    status_vm, ctl, damage, stars = status()
    vm.OnStatusStart(target, status_vm)
    equal(status_vm.StarLockLeft, 3); equal(status_vm.WetLock, 1)
    equal(status_vm.GetStack(11), 2); close(status_vm.AstralWeight[0], 2.9)
    close(status_vm.DeathCurseMult, 2)
    equal(status_vm.AirLeft, 2); close(status_vm.AirDamage, 7.5)
    status_vm.ReleaseWetLock()
    equal(status_vm.GetStack(8), 0); equal(status_vm.WetLock, 0)
    status_vm.SetWetLock(); status_vm.ReleaseWetLock(True)
    equal(status_vm.GetStack(8), 1); equal(status_vm.WetLock, 0)


def summon_reservation():
    vm = controller()
    commanded, attempts = Array(), []
    player = NS(HasPerk=lambda p: True)
    vm.overrides['ThePlayer'] = lambda: player
    vm.fields['TwinSoulsPerk'] = True
    vm.env = dict(env)
    vm.env['PO3_SKSEFunctions'] = NS(GetCommandedActors=lambda p: commanded)
    vm.fields['ReanimateSpell'] = NS(SetNthEffectMagnitude=lambda *a: None,
                                    SetNthEffectDuration=lambda *a: None)
    a, b = NS(GetFormID=lambda: 1), NS(GetFormID=lambda: 2)
    def apply(spell, victim):
        attempts.append(victim)
        equal(vm.ApplyReanimate(b, 999, 86313600), False)  # reentrant kill event
    player.DoCombatSpellApply = apply
    clock.now = 300
    equal(vm.ApplyReanimate(a, 999, 86313600), True)
    equal(vm.ApplyReanimate(b, 999, 86313600), False)
    equal(vm.ServantCount(), 1)
    commanded.append(a)
    equal(vm.ServantCount(), 1)  # actual servant + reservation are not double counted
    equal(attempts, [a])


def kill_attribution_dedupe():
    vm = controller()
    player = object(); companion = object(); victim = NS(GetFormID=lambda: 1)
    vm.overrides['ThePlayer'] = lambda: player
    vm.fields['CurrentElement'] = NS(GetValueInt=lambda: 6)
    rewards = []
    vm.env = dict(env)
    for name in ('ESSBElem', 'ESSBElem2', 'ESSBElem3'):
        vm.env[name] = NS(OnKill=lambda *a: rewards.append(1))
    vm.env['ESSBNoForm'] = NS(IsSpellUser=lambda *a: False, OnKill=lambda *a: rewards.append(1))
    vm.OnKillEvent(victim, companion)
    equal(rewards, [])
    vm.OnKillEvent(victim, player)
    vm.OnKillEvent(victim, player)
    equal(len(rewards), 4)


def domain_last_second():
    vm = controller()
    victim, player = object(), object()
    calls = []
    vm.overrides.update(ThePlayer=lambda: player, PlayerInDomain=lambda e: False,
                        ScanDomainTargets=lambda pool, slot: Array([victim]),
                        AddStackTo=lambda a, k, n: calls.append((k, n)),
                        SetGlobal=lambda *a: None)
    vm.env = dict(env)
    vm.env['PO3_SKSEFunctions'] = NS(GetActorsByProcessingLevel=lambda n: Array([victim]))
    vm.fields['DomainElem'][0] = 8
    vm.fields['DomainLeft'][0] = 5
    for _ in range(6):
        vm.TickDomain()
    equal(calls, [(7, 1)] * 5)
    equal(vm.DomainLeft[0], 0)


def dark_pending_order():
    pending, drains = {'value': False}, []
    def take():
        value = pending['value']; pending['value'] = False
        return value
    ctl = NS(ThePlayer=lambda: object(), TakeNextEndMultOn=lambda a: 1.0,
             GetStatus=lambda a: None, TakePendingDrain=take,
             ApplyUtil=lambda *a: drains.append(a))
    local = dict(env)
    local['ESSBNodes'] = NS(CommonEndMult=lambda c: 1.0, TrioMult=lambda *a: 1.0,
        ConcertMult=lambda c: 1.0, OnEndReward=lambda *a: None,
        HasChainEnd=lambda c: False, HasGrandConcert=lambda c: False)
    local['ESSBElem'] = NS(EndMult=lambda *a: 1.0, OverloadMult=lambda *a: 1.0,
        OnEnd=lambda c, e, *a: pending.update(value=True) if e == 10 else None)
    react = Script(ROOT / 'src/ESSBReactions.psc', local)
    react.overrides.update(EndDark=lambda *a: None, EndFire=lambda *a: None)
    react.End(ctl, 10, object(), 0, 1.0)
    equal(pending['value'], True); equal(drains, [])
    react.End(ctl, 1, object(), 0, 1.0)
    equal(pending['value'], False); equal(len(drains), 2)


def blood_chain_and_reason():
    ranks.clear(); branches.clear(); branches.add((5, 2, 1, 1))
    hits, heals = [], []
    a = NS(GetActorValue=lambda av: 100.0)
    b = NS(GetActorValue=lambda av: 100.0)
    c = NS(GetActorValue=lambda av: 100.0)
    ctl = NS(IsVIPTarget=lambda t: False, ApplyDamage=lambda e, n, t: hits.append(t),
             Leech=lambda n: heals.append(n), GetBloodLeechRatio=lambda: .1,
             GetStack=lambda t, k: 1,
             ScanTargets=lambda t, *args: Array([b if t is a else c]))
    local = dict(env)
    local['ESSBElem2'] = NS(SurgePercent=lambda *a: .1, SurgeHealMult=lambda c: 2.0,
        SurgeRadius=lambda c: 100.0, BleedPerLayer=lambda c: .64)
    local['ESSBElem'] = NS(SignatureMult=lambda *a: 1.0)
    react = Script(ROOT / 'src/ESSBReactions.psc', local)
    react.overrides['End'] = lambda ctl, e, target, reason, mult, chain: react.EndBlood(
        ctl, target, None, mult, object(), reason, chain)
    react.EndBlood(ctl, a, None, 1.0, object(), 0, False)
    equal(hits, [a, b])  # C is in B's radius but not A's: no relay expansion
    for reason in (0, 1, 2, 3):
        heals.clear()
        react.EndBlood(ctl, a, None, 1.0, object(), reason, True)
        equal(len(heals), 2 if reason == 1 else 1)
        if reason == 1:
            close(heals[1], 5.0)


def push_queue():
    ranks.clear(); branches.clear()
    vm = controller()
    actions, knock = [], {'state': 0}
    target = NS(GetFormID=lambda: 1,
        ApplyHavokImpulse=lambda *args: actions.append(('impulse', args)))
    player = NS(PushActorAway=lambda a, force: actions.append(('push', force)))
    vm.overrides.update(ThePlayer=lambda: player, CanRagdoll=lambda a: True,
        TakePush=lambda *a: True, ArmUpdate=lambda: None,
        SetAirborne=lambda *a: actions.append(('airborne', a[1:])))
    vm.env = dict(env)
    vm.env['PO3_SKSEFunctions'] = NS(GetActorKnockState=lambda a: knock['state'])
    vm.fields.update(Ready=True, NextTickAt=1000.0)
    clock.now = 400
    equal(vm.BlowBack(target, 3.0), True)
    equal(vm.PullTo(target, player, 1.5), True)
    equal(actions[:2], [('push', 3.0), ('push', -1.5)])
    equal(vm.LiftUp(target, 1.0, 10.0), True)
    equal(actions[-1], ('push', .1))
    clock.now = 400.2
    vm.OnUpdate()
    equal(len([a for a in actions if a[0] == 'impulse']), 0)
    knock['state'] = 1
    equal(vm.LiftUp(target, 1.0, 10.0), True)
    clock.now = 400.4
    vm.OnUpdate(); vm.OnUpdate()
    equal(len([a for a in actions if a[0] == 'impulse']), 1)
    equal(actions[-1][0], 'airborne')


def stale_host_identity():
    vm = controller()
    old, new = object(), object()
    vm.OccupySlot(0, old)
    vm.SaveSwapData(0, Array([1] * 27), Array([1.0] * 17))
    rejected = []
    def imported(*args):
        # Clear/reuse occurs while the controller is in another script's ImportState.
        vm.ClearSlot(0)
        vm.OccupySlot(0, new)
    host = NS(ImportState=imported, PrepareSwap=lambda: rejected.append('stop'),
              Dispel=lambda: rejected.append('dispel'))
    vm.OnStatusStart(old, host)
    equal(vm.RegActor[0], new)
    equal(vm.RegStatus[0], None)
    equal(rejected, ['stop', 'dispel'])
    # Completely late old callback also cannot import into the reused slot.
    rejected.clear(); vm.OnStatusStart(old, host)
    equal(vm.RegStatus[0], None)
    equal(rejected, ['stop', 'dispel'])


def execute_unscaled_true():
    vm = controller()
    magnitude, applied = [], []
    spell = NS(SetNthEffectMagnitude=lambda ix, n: magnitude.append(n))
    target = NS(GetActorValue=lambda av: 100.0, GetFormID=lambda: 1)
    player = NS(DoCombatSpellApply=lambda s, t: applied.append((s, t)))
    vm.fields['TrueSpell'] = spell
    vm.overrides['ThePlayer'] = lambda: player
    # No GLevel or TrueMult mock: calling them accidentally would fail this test.
    vm.Execute(target, 2)
    equal(magnitude, [2000.0]); equal(applied, [(spell, target)])


if __name__ == '__main__':
    for name, test in [
        ('A12/A13/A14/R1 node formula endpoints', formulas),
        ('B9 sliding ten-second trio window', trio),
        ('B5 undead maintenance versus power cost', blood_cost),
        ('R3 shadow window consumed before failed proc', shadow_body),
        ('A9 poison insertion during damage keeps six ticks', poison_interleave),
        ('A9 bleed insertion during damage keeps five ticks', bleed_interleave),
        ('A4/A5/A7/B4 weighted delayed payload and host roundtrip', delayed_payloads),
        ('A15/advisory radiance and one-second foresee', stars_immediate_and_foresee),
        ('B3 eight identity-separated backups survive timeout', swap_backup),
        ('B1/B2 primary-secondary routing, promotion and cooldown transaction', marks_and_cooldown),
        ('B7 domain membership precedes nearest-five cap', domain_filter),
        ('A1 glacier entry snapshot and independent two-second coffin', frost_snapshot),
        ('A2 shock execution receives pre-consumption charge', shock_snapshot),
        ('A6/A15 meteor true damage and shared astral feedback', star_fall_feedback),
        ('R2/R6 delayed host lock and weighted payload handoff', pending_status_start),
        ('R7 reentrant kills reserve summon slot before native apply', summon_reservation),
        ('P1-4/B supplement player attribution and repeated event dedupe', kill_attribution_dedupe),
        ('R5 five-second domain produces five effect ticks', domain_last_second),
        ('A3 drain is consumed by the next end, not the producing end', dark_pending_order),
        ('A8/A10/B8 blood sea cannot relay and extra heal is burst-only', blood_chain_and_reason),
        ('P0-1 signed pushes and single delayed ragdoll-only impulse', push_queue),
        ('B3 slot reuse during import rejects the old host', stale_host_identity),
        ('P1-3 execution uses unscaled true spell without elemental resist', execute_unscaled_true),
    ]:
        check(name, test)
    (ROOT / 'build/fix-round-regression.json').write_text(json.dumps({
        'scope': 'Actual selected Papyrus function bodies; mocked native/external calls; not game runtime',
        'passed': len(results), 'results': results}, indent=2), encoding='utf8')
