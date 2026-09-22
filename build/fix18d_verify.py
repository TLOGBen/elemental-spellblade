"""Round18d: execute actual PSC events and diagnostics with mocked native damage."""
from types import SimpleNamespace as NS
import json
import sys


def run(b):
    sys.path.insert(0, str(b.WORK/'build'))
    from papyrus_harness import Script
    rows = []

    class Global:
        def __init__(self): self.value = 0.0
        def GetValue(self): return self.value
        def SetValue(self, value): self.value = value

    class Form:
        def __init__(self, fid): self.fid = fid
        def GetFormID(self): return self.fid
        def GetType(self): return 41 if self.fid == 0x1397e else 22
        def GetEnchantment(self): return None
        def __str__(self): return f'{self.fid:08X}'

    def make(probe, k, fault=''):
        logs, disposed = [], []
        state = NS(now=0.0, health=10000.0, perks={0x820} if probe == 1 else {0x821, 0x822}, av={})
        weapon = Form(0x1397e)
        player = NS(HasPerk=lambda p: p.fid in state.perks,
                    GetActorValue=lambda n: state.av.get(n, 0.0), GetEquippedWeapon=lambda: weapon)
        victim = NS(GetActorValue=lambda n: state.health if n == 'Health' else state.av.get(n, 0.0), IsDead=lambda: False)
        env = dict(__execute_logs__=True, __papyrus_concat__=True, Debug=NS(Trace=logs.append),
                   Game=NS(GetPlayer=lambda: player), Utility=NS(GetCurrentRealTime=lambda: state.now),
                   StringUtil=NS(GetNthChar=lambda s, i: s[i]),
                   Math=NS(RightShift=lambda v, n: (v & 0xffffffff) >> n, LogicalAnd=lambda a, c: a & c))
        m = Script(b.WORK/'src/ESSBProbeMeter.psc', env)
        m.fields.update(ProbeAB=Form(0x820), ProbeHit=Form(0x821), ProbeMultiply=Form(0x822),
                        Gate=Global(), Session=Global(), ReferenceSpell='reference')
        m.overrides.update(RegisterForModEvent=lambda *a: None, RegisterForSingleUpdate=lambda *a: None,
                           Dispel=lambda: disposed.append(True))
        def hit(source=weapon, **flags):
            m.OnHit(player, source, flags.get('projectile'), flags.get('power', False),
                    flags.get('sneak', False), flags.get('bash', False), flags.get('blocked', False))
        def reference(spell, target):
            assert spell == 'reference' and target is victim
            state.health -= 10*k
            if fault != 'missing-reference': m.OnSegment(victim, 4, 0.0)
            if fault == 'duplicate-reference': m.OnSegment(victim, 4, 0.0)
            if fault == 'reference-hit': hit(Form(0xfe38982d))
        player.DoCombatSpellApply = reference
        def update(time): state.now = time; m.OnUpdate()
        return m, state, player, victim, weapon, logs, disposed, hit, update

    verdicts = [(1, 5, [1], 'lightning_roll_mode = chain'),
                (1, 12, [2, 1], 'lightning_roll_mode = additive'),
                (2, 10, [3], 'tier_multiplier_mode = spell_variant'),
                (2, 20, [3], 'tier_multiplier_mode = entry')]
    for k in (0.475, 0.95, 1.0, 0.2, 2.0, 0.1, 2.1, 0.0, -0.1):
        for probe, damage, segments, expected in verdicts:
            m, state, player, victim, weapon, logs, disposed, hit, update = make(probe, k)
            m.OnEffectStart(victim, player); hit()
            for t in (4, 5, 9, 10): update(t)
            if not 0.2 <= k <= 2.0:
                assert disposed and not m.Calibrated and m.Gate.value == 0
                assert any('reference k out of band' in x for x in logs)
                assert not any('CALIBRATE k=' in x or expected in x for x in logs)
                rows.append(dict(k=k, probe=probe, expected=expected, rejected=True, messages=logs))
                continue
            assert not disposed and m.Calibrated and m.Gate.value == 1
            assert abs(m.CalibrationK-k) < 1e-6
            assert any('CALIBRATE k=' in x for x in logs)
            # Two trials prove state/source reset; reported magnitude is deliberately zero.
            for start in (14, 20):
                state.health -= damage*k
                for segment in segments: m.OnSegment(victim, segment, 0.0)
                hit(); update(start); update(start+1)
                assert not disposed and not m.Bad and m.Hits == 0 and m.HitSources == ''
                assert any(expected in x and 'basis=health_delta/k' in x for x in logs)
            rows.append(dict(k=k, probe=probe, normalized=damage, expected=expected, messages=logs))

    faults = {
        'extra-source': 'extra hit events: count=3 expected=1 sources=[1:0001397E][2:FE38982D][3:FE38982D]',
        'double-swing': 'extra hit events: count=2 expected=1 sources=[1:0001397E][2:0001397E]',
        'physical': 'non-zero physical control delta=1.0 expected=0',
        'unstable-control': 'unstable health:', 'unstable-reference': 'unstable health:',
        'unstable-probe': 'unstable health:', 'perks': 'probe perks changed during measurement',
        'missing-reference': 'reference segment counts: reference=0',
        'duplicate-reference': 'reference segment counts: reference=2',
        'reference-hit': 'extra hit events: count=1 expected=0 sources=[1:FE38982D]',
        'missing-hit': 'missing hit events: count=0 expected=1',
        'control-segment': 'control segment counts: A=1',
        'late-segment': 'segment arrived during stability check: segment=1',
        'unknown-segment': 'unexpected segment=99',
        'weapon-change': 'equipped weapon changed', 'enchanted': 'test weapon is enchanted',
        'power': 'power=True', 'sneak': 'sneak=True', 'bash': 'bash=True', 'blocked': 'blocked=True',
        'projectile': 'projectile=00000001', 'wrong-source': 'source=FE38982D',
        'wrong-aggressor': 'aggressor=None', 'late-hit': 'phase=2',
        'dead': 'target is dead', 'low-health': 'target health too low=',
        **{n: 'non-zero '+n+'=1.0' for n in ('AttackDamageMult', 'FireResist', 'MagicResist', 'AbsorbChance', 'HealRate', 'HealRateMult')},
    }
    for probe in (1, 2):
        for fault, expected in faults.items():
            m, state, player, victim, weapon, logs, disposed, hit, update = make(probe, 0.475, fault)
            m.OnEffectStart(victim, player)
            if fault == 'missing-hit': state.health -= 1
            elif fault == 'wrong-aggressor': m.OnHit(None, weapon, None, False, False, False, False)
            elif fault == 'wrong-source': hit(Form(0xfe38982d))
            elif fault in ('power', 'sneak', 'bash', 'blocked'): hit(**{fault: True})
            elif fault == 'projectile': hit(projectile=Form(1))
            else: hit()
            if fault == 'extra-source': hit(Form(0xfe38982d)); hit(Form(0xfe38982d))
            if fault == 'double-swing': hit()
            if fault == 'physical': state.health -= 1
            if fault == 'perks': state.perks = {0x820, 0x821, 0x822}
            if fault == 'weapon-change': player.GetEquippedWeapon = lambda: Form(1)
            if fault == 'enchanted': weapon.GetEnchantment = lambda: Form(1)
            if fault == 'dead': victim.IsDead = lambda: True
            if fault == 'low-health': state.health = 100
            if fault in state.av or fault in ('AttackDamageMult', 'FireResist', 'MagicResist', 'AbsorbChance', 'HealRate', 'HealRateMult'): state.av[fault] = 1.0
            if fault == 'control-segment': m.OnSegment(victim, 1, 0)
            if fault == 'unknown-segment': m.OnSegment(victim, 99, 0)
            update(4)
            if not disposed:
                if fault == 'unstable-control': state.health -= 1
                if fault == 'late-segment': m.OnSegment(victim, 1, 0)
                if fault == 'late-hit': hit(); update(8)
                update(9 if fault == 'late-hit' else 5)
            if not disposed:
                update(13)
                if fault == 'unstable-reference': state.health -= 1
                update(14)
            if fault == 'unstable-probe':
                assert m.Calibrated and not disposed
                state.health -= (5 if probe == 1 else 10)*0.475
                m.OnSegment(victim, 1 if probe == 1 else 3, 0); hit(); update(18)
                state.health -= 1; update(19)
            assert disposed and m.Gate.value == 0, (probe, fault, logs)
            assert any(expected in x for x in logs), (probe, fault, expected, logs)
            if fault in ('extra-source', 'double-swing'):
                assert any('health_delta=0.0' in x for x in logs)
                assert not any('non-zero physical' in x or 'CONTROL is not zero' in x for x in logs)
            assert not any('lightning_roll_mode =' in x or 'tier_multiplier_mode =' in x for x in logs)
            rows.append(dict(probe=probe, fault=fault, messages=logs))

    meter = Script(b.WORK/'src/ESSBProbeMeter.psc')
    for probe, damage, segments, expected in verdicts:
        counts = [segments.count(i) for i in (1, 2, 3)]
        for offset in (-0.15, 0.15): assert expected in meter.Verdict(probe, damage+offset, *counts, False)
        for offset in (-0.151, 0.151): assert 'unexpected' in meter.Verdict(probe, damage+offset, *counts, False)
    report = dict(calibration_flows=36, valid_trials=40, diagnostic_flows=2*len(faults),
                  tolerance_cases=16, actual_psc_executed=True, runtime_tested=False, cases=rows)
    (b.WORK/'build/fix18-probe-package/calibration-check.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(f'PROBE-CALIBRATION ok: 36 flows; k=0.475/0.95/1.0 and band boundaries; rejected k=0.1/2.1/0/-0.1; four verdicts; {2*len(faults)} diagnostic flows; 16 tolerance boundaries')
    return report


if __name__ == '__main__':
    from pathlib import Path
    run(NS(WORK=Path(__file__).resolve().parents[1]))
