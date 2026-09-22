"""Execute probe diagnostic paths from shipped PSC; native boundaries are mocks."""
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib
import itertools
import json
import runpy
import sys


def run(b):
    sys.path.insert(0, str(b.WORK / 'build'))
    from papyrus_harness import Script, strip_comment
    assert strip_comment('Debug.Trace("reason; action") ; comment') == 'Debug.Trace("reason; action") '
    source = b.WORK / 'src'
    rows = []

    class Global:
        def __init__(self, value=0): self.value = value
        def GetValue(self): return self.value
        def SetValue(self, value): self.value = value

    def make(bits=(True, False, False), load=5):
        logs, calls = [], []
        perks = [NS(GetFormID=lambda i=i: ((load << 24) | (0x820+i)) - (0x100000000 if load >= 128 else 0)) for i in range(3)]
        weapon = NS(GetEnchantment=lambda: None)
        player = NS(HasPerk=lambda p: bits[next(i for i, x in enumerate(perks) if x is p)],
                    GetActorValue=lambda name: 0, GetEquippedWeapon=lambda: weapon)
        victim = NS(GetActorValue=lambda name: 1000 if name == 'Health' else 0, IsDead=lambda: False)
        def get_player():
            assert logs[0] == '[ESSB-PROBE] START meter', logs
            return player
        env = dict(__execute_logs__=True, __papyrus_concat__=True,
                   Debug=NS(Trace=logs.append), Game=NS(GetPlayer=get_player),
                   Utility=NS(GetCurrentRealTime=lambda: 0),
                   StringUtil=NS(GetNthChar=lambda text, index: text[index]),
                   Math=NS(RightShift=lambda v, n: (v & 0xffffffff) >> n, LogicalAnd=lambda a, c: a & c))
        meter = Script(source/'ESSBProbeMeter.psc', env)
        meter.fields.update(ProbeAB=perks[0], ProbeHit=perks[1], ProbeMultiply=perks[2],
                            Gate=Global(), Session=Global(), ReferenceSpell='reference')
        def dispel():
            calls.append('dispel')
            # Immediately dispatch Finish after native destruction, even for early refusals.
            meter.OnEffectFinish(victim, player)
        meter.overrides.update(Dispel=dispel, RegisterForModEvent=lambda *a: calls.append('register'),
                               RegisterForSingleUpdate=lambda *a: calls.append('update'))
        # No UnregisterForAllModEvents (or other native Self cleanup) mock:
        # any such call from OnEffectFinish fails closed as an unbound native.
        return meter, player, victim, logs, calls

    for load, bits, self_target in itertools.product((5, 0x81, 0xfd), itertools.product((False, True), repeat=3), (False, True)):
        meter, player, victim, logs, calls = make(bits, load)
        target = player if self_target else victim
        meter.OnEffectStart(target, player)
        valid = bits in ((True, False, False), (False, True, True))
        refused = [line for line in logs if line.startswith('[ESSB-PROBE] REFUSED')]
        assert logs[0] == '[ESSB-PROBE] START meter'
        if self_target or not valid:
            assert len(refused) == 1 and calls == ['dispel'], (bits, self_target, logs, calls)
            message = refused[0]
            if self_target:
                assert 'console target was the player' in message and 'click the bandit first' in message
                assert 'remove the meter spell from the player' in message
            if not valid:
                ids = [f'{load:02X}00082{i}' for i in range(3)]
                for fid, has in zip(ids, bits): assert f'{fid}={has}' in message, message
                assert f'probe 1 needs ONLY {ids[0]}' in message
                assert f'probe 2 needs BOTH {ids[1]} and {ids[2]} WITHOUT {ids[0]}' in message
                assert 'player.removeperk' in message and 'player.addperk' in message
            rows.append(dict(load_order=f'{load:02X}', perks=bits, self_target=self_target, message=message))
        else:
            assert not refused and calls == ['register', 'update']
            assert any('READY CONTROL' in line for line in logs)
            meter.OnEffectFinish(victim, player)
            assert meter.Gate.value == 0

    for event in ('segment-target', 'segment-session', 'hit-session', 'update-session', 'perks-changed', 'setup', 'wait'):
        meter, player, victim, logs, calls = make()
        if event == 'setup':
            player.GetEquippedWeapon = lambda: None
            meter.OnEffectStart(victim, player)
            assert calls == ['dispel'] and any('setup failed' in s for s in logs)
        else:
            meter.OnEffectStart(victim, player)
            logs.clear(); calls.clear()
            if event.endswith('session'): meter.Session.value += 1
            if event.startswith('segment'):
                meter.OnSegment(object() if event.endswith('target') else victim, 1, 5)
                assert meter.CountA == 0
            elif event == 'hit-session': meter.OnHit(player, meter.TestWeapon, None, False, False, False, False)
            elif event == 'perks-changed':
                player.HasPerk = lambda p: True
                meter.OnUpdate()
                assert all(f'0500082{i}=True' in logs[0] for i in range(3))
                assert meter.Gate.value == 0
            elif event == 'wait':
                meter.fields.update(Phase=1, LastActivity=-4)
                meter.OnUpdate()
                assert meter.Phase == 2 and calls == ['update']
            else: meter.OnUpdate()
            assert len(logs) == 1, (event, logs)
            assert any(word in logs[0] for word in ('remove', 'do not hit')), logs
        rows.append(dict(path=event, messages=logs))

    # Global cleanup retains its original session ownership rule without touching Self.
    for same_session in (False, True):
        meter, player, victim, logs, calls = make()
        meter.fields['Token'] = 4
        meter.Session.value = 4 if same_session else 5
        meter.Gate.value = 1
        meter.OnEffectFinish(victim, player)
        assert meter.Gate.value == (0 if same_session else 1) and not calls

    for handle, sent in ((0, False), (1, False), (1, True)):
        logs, pushed = [], []
        env = dict(__execute_logs__=True, __papyrus_concat__=True, Debug=NS(Trace=logs.append),
                   ModEvent=NS(Create=lambda *a: handle, Send=lambda *a: sent,
                               PushForm=lambda *a: pushed.append(a), PushInt=lambda *a: pushed.append(a),
                               PushFloat=lambda *a: pushed.append(a)))
        segment = Script(source/'ESSBProbeSegment.psc', env)
        segment.fields['Segment'] = 3
        def magnitude():
            assert logs == ['[ESSB-PROBE] START segment']
            return 10
        segment.overrides['GetMagnitude'] = magnitude
        segment.OnEffectStart('bandit', 'player')
        refused = [line for line in logs if 'REFUSED' in line]
        assert len(refused) == (0 if sent else 1)
        if refused:
            assert ('could not be created' if not handle else 'could not be sent') in refused[0]
            assert 'restart Skyrim through SKSE' in refused[0] and 'repeat the controls' in refused[0]
        assert len(pushed) == (3 if handle else 0)
        rows.append(dict(handle=handle, sent=sent, messages=logs))

    # Strip only the deliberately added diagnostics and prove the executable meter
    # unchanged verdict/tolerance/environment bodies match the round18c input bytes.
    # Round18d event changes are exercised by fix18d_verify, including invalid paths.
    baseline = b.WORK/'build/fix18-probe-package/round18c-validation/before/src/ESSBProbeMeter.psc'
    old = Script(baseline)
    new = Script(source/'ESSBProbeMeter.psc')
    def without_logs(lines):
        return [line for line in lines if not line.startswith(('Debug.Trace(', 'LogPerkRefusal('))]
    for name in old.functions:
        if name in ('OnEffectStart', 'OnSegment', 'OnEffectFinish', 'OnHit', 'OnUpdate', 'Verdict', 'CurrentMode', 'LogPerkRefusal'): continue
        assert without_logs(old.functions[name][2]) == without_logs(new.functions[name][2]), name
    finish = new.functions['OnEffectFinish'][2]
    assert finish == ['If Token == Session.GetValue()', 'Gate.SetValue(0.0)', 'EndIf']
    folder = b.WORK/'build/fix18-probe-package'
    # Setup adds records; preserve every original measurement record byte for byte.
    old_path = b.WORK/'build/round18e/before/probe.esp'
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == (folder/'round18c-validation/probe-esp-before.sha256').read_text()
    old_records, _ = b.read_plugin(old_path)
    new_records, _ = b.read_plugin(folder/'Elements Spellblade Round18 Probes.esp')
    by = {r.edid: r for r in new_records}
    assert len(old_records) == 16
    for old in old_records:
        new = by[old.edid]
        if old.edid in ('ESSB_ProbeMeterEffect', 'ESSB_ProbeMeter'): continue  # New cross-perk VMAD/OR gates checked in 18b/18f.
        assert (old.sig, old.flags, old.ss, old.key.split('|')[1]) == (new.sig, new.flags, new.ss, new.key.split('|')[1])
    parser = runpy.run_path(str(b.WORK/'build/fix5_read_bsa.py'))['Pex']
    for name, label in (('ESSBProbeMeter', 'meter'), ('ESSBProbeSegment', 'segment')):
        tree = parser((folder/'Scripts'/f'{name}.pex').read_bytes()).read()
        funcs = tree['objects'][0]['states']['']
        first = funcs['OnEffectStart']['code'][0]
        assert first[0] == 25 and first[1][:2] == ['debug', 'Trace']
        assert first[1][3][0] == '[ESSB-PROBE] START '+label
        if label == 'meter':
            for opcode, args in funcs['OnEffectFinish']['code']:
                if opcode == 23: assert args[1].lower() != 'self', args
    report = dict(start_combinations=48, diagnostic_cases=rows, cleanup_cases=2,
                  original_damage_records_unchanged=True, compiled_start_first=True,
                  compiled_finish_no_self_native=True, runtime_tested=False)
    (folder/'refusal-check.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('PROBE-REFUSALS ok: 48 starts; all perk combinations + load-order hex + player target; stale events; segment create/send failures; native-free Finish; unchanged 14 damage records/environment guards; expanded modes checked by 18f')
    return report
