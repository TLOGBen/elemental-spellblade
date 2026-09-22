"""Round 18 resumption: zero-difference gate preflight, NOT acceptance.

Execute unchanged baseline Papyrus bodies with the existing native fixture.
Demonstrates why node eligibility and a numerically zero target bonus are
not equivalent. No product source, schema, baseline or game writes.
"""
import sys
sys.dont_write_bytecode = True
import json
import math
from pathlib import Path
from fix12_cost import scenario, Measured
from papyrus_harness import Array

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / '.codex/pre-fix18-snapshot/src'


def case(heat, elapsed=0):
    c, trees, player, target, weapon, clock, meter, env, Glob = scenario(OLD, prepare_only=True)
    c.CurrentElement.v = 1
    c.ElementDamageMin[0], c.ElementDamageMax[0] = 10, 12
    written = []
    class Proc:
        def SetNthEffectMagnitude(self, index, value):
            written.append(value)
    c.HitNormalSpells[0] = Proc()
    status = Measured(OLD / 'ESSBStatus.psc', env)
    status.fields.update(Ctl=c, Holder=target, Heat=heat,
        HeatTime=clock[0]-elapsed, RingClock=clock[0]-elapsed,
        BleedRing=Array([0]*10), PoisonRing=Array([0]*12),
        AstralRing=Array([0]*2), AstralWeight=Array([0.0]*2))
    c.RegActor[0] = target
    c.RegElem[0] = 1
    c.RegStatus[0] = status
    # Existing public alternative does not settle elapsed state.
    exported_heat = status.ExportInts()[0]
    meter.script.clear()
    meter.native.clear()
    c.ApplyProc(target, 1, False, False, False, 0, c.RegGeneration[0])
    base = 11 * 1.05
    old = written[-1]
    bonus = old - base
    assert math.isclose(base+bonus, old, abs_tol=1e-4)
    return dict(initial_heat=heat, seconds_since_heat=elapsed,
        export_ints_heat=exported_heat, final_heat=status.Heat,
        engine_base_reference=base, old_magnitude=old,
        arithmetic_difference=bonus,
        controller_getstack=meter.script['ESSBController.GetStack'],
        status_getstack=meter.script['ESSBStatus.GetStack'],
        status_tick=meter.script['ESSBStatus.Tick'])


def run():
    rows = [case(0), case(4), case(4, 6)]
    assert [r['final_heat'] for r in rows] == [0, 4, 0]
    assert all(math.isclose(r['old_magnitude'], expected, abs_tol=1e-4)
               for r, expected in zip(rows, [11.55, 15.246, 11.55]))
    assert rows[0]['arithmetic_difference'] == rows[2]['arithmetic_difference'] == 0
    assert all(r['controller_getstack'] == r['status_getstack'] == 1 for r in rows)
    assert rows[2]['export_ints_heat'] == 4 and rows[2]['status_tick'] == 1
    result = dict(kind='zero_difference_gate_preflight', round18_complete=False,
        source='immutable pre-fix18 snapshot; actual ApplyProc/GetHitMult/FireHitMult/GetStack/Tick/ExportInts',
        native_boundary='fix12_cost fixture; RandomFloat midpoint; no game execution',
        conditions='same target slot, live host, zero nodes, tree level 1, no opening or domain; only host heat/time differ',
        rows=rows,
        conclusion='Rank/Br eligibility cannot distinguish Heat=0 from Heat=4; ExportInts does not preserve GetStack overdue Tick semantics. A zero-difference result is not a proof available before reading target state.',
        request='Clarify zero-GetStack acceptance as statically ineligible fast path, or stop for a new status-layer ruling.')
    (ROOT/'build/fix18-zero-difference-preflight.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    run()
