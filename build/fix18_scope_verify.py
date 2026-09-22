"""Read-only actual-source proof of the phase-1 target-state dependency.

This is a preflight counterexample, NOT a HITPROC or round-18 acceptance test.
Native boundaries use the existing representative-hit fixture. Production
ApplyProc/GetHitMult/GetStack/FireHitMult/Status.GetStack bodies are unmodified.
"""
import sys
sys.dont_write_bytecode = True
import json
import math
from pathlib import Path
from fix12_cost import scenario, Measured
from papyrus_harness import Array

ROOT = Path(__file__).resolve().parents[1]


def run():
    folder = ROOT / 'src'
    c, trees, player, target, weapon, clock, meter, env, Glob = scenario(folder, prepare_only=True)
    settings = json.loads((ROOT / 'settings.json').read_text(encoding='utf8'))
    c.CurrentElement.v = 1
    c.ElementDamageMin[0], c.ElementDamageMax[0] = settings['element_damage']['Fire']
    target_b = type(target)()
    written = []

    class Proc:
        def SetNthEffectMagnitude(self, index, value):
            written.append((index, value))

    c.HitNormalSpells[0] = Proc()
    rows = []
    for slot, actor, heat in ((0, target, 0), (1, target_b, 4)):
        status = Measured(folder / 'ESSBStatus.psc', env)
        status.fields.update(Ctl=c, Holder=actor, Heat=heat, HeatTime=clock[0], RingClock=clock[0],
                             BleedRing=Array([0]*10), PoisonRing=Array([0]*12),
                             AstralRing=Array([0]*2), AstralWeight=Array([0.0]*2))
        c.RegActor[slot] = actor
        c.RegElem[slot] = 1
        c.RegStatus[slot] = status
        assert c.GetStack(actor, 1) == heat
        c.ApplyProc(actor, 1, False, False, False, slot, c.RegGeneration[slot])
        rows.append(dict(target=f'target_{slot}', heat=heat, magnitude=written[-1][1]))
    assert math.isclose(rows[1]['magnitude'] / rows[0]['magnitude'], 1.32)
    cost = scenario(folder)
    report = dict(kind='phase1_scope_preflight_only', round18_complete=False,
                  source_bodies_executed=['ESSBController.ApplyProc', 'ESSBController.GetHitMult',
                    'ESSBController.GetStack', 'ESSBElem.FireHitMult', 'ESSBStatus.GetStack'],
                  conditions='same player, ranks=0, tree level=1, normal attack, not opening, same native actor values',
                  native_boundary='existing fix12_cost fixture; RandomFloat returns midpoint; no Skyrim runtime',
                  results=rows, representative_hit=cost,
                  dependency='native phase-1 shared proc cannot distinguish script-only Heat=0 from Heat=4; '
                             'target effect representation is scheduled for phase 2; extra scripted target bonus '
                             'would require extending the prescribed three-purpose ApplyProc fallback')
    (ROOT / 'build/fix18-scope-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(results=rows, scripted=cost['scripted'], native=cost['native'], total=cost['total']), indent=2))


if __name__ == '__main__':
    run()
