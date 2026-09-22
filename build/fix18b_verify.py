"""Execute shipped Papyrus verdict bodies, plus native ESP/VMAD readback."""
from pathlib import Path
from types import SimpleNamespace as NS
import json, struct, sys

def run(b):
    sys.path.insert(0, str(b.WORK/'build'))
    from papyrus_harness import Script
    meter = Script(b.WORK/'src/ESSBProbeMeter.psc')
    cases = [
        (1,5,1,0,0,False,'lightning_roll_mode = chain'),
        (1,12,1,1,0,False,'lightning_roll_mode = additive'),
        (2,10,0,0,1,False,'tier_multiplier_mode = spell_variant'),
        (2,20,0,0,1,False,'tier_multiplier_mode = entry'),
        (1,7,0,1,0,False,'lightning_roll_mode = exclusive'),
        (1,12,1,0,0,False,'unexpected, report'),
        (1,5,1,1,0,False,'unexpected, report'),
        (2,0,0,0,0,False,'unexpected, report'),
        (2,15,0,0,1,False,'unexpected, report'),
        (2,20,0,0,2,False,'unexpected, report'),
        (2,20,0,0,1,True,'unexpected, report'),
        (1,12,1,1,0,True,'unexpected, report'),
    ]
    results=[]
    for *args, expected in cases:
        answer=meter.Verdict(*args)
        assert expected in answer, (args,answer)
        results.append(dict(input=args,verdict=answer))
    # Environment gates execute actual Clean(), with explicit native-boundary mocks.
    av=dict(FireResist=0,MagicResist=0,AbsorbChance=0,HealRate=0,HealRateMult=0,Health=1000)
    weapon=NS(GetEnchantment=lambda:None)
    player=NS(GetActorValue=lambda name:0,GetEquippedWeapon=lambda:weapon)
    victim=NS(GetActorValue=lambda name:av[name],IsDead=lambda:False)
    meter.fields.update(Player=player,Victim=victim,TestWeapon=weapon,Mode=2)
    meter.overrides['CurrentMode']=lambda:2
    assert meter.Clean()
    for name in ('FireResist','MagicResist','AbsorbChance','HealRate','HealRateMult'):
        for value in (-50,1,50,100):
            av[name]=value
            assert not meter.Clean(), (name,value)
        av[name]=0
    assert meter.Clean()
    # Drive the actual event state machine, including both controls. Native
    # damage/events are explicit mocks, never claimed as engine evidence.
    flows=[]
    class Global:
        def __init__(self):self.value=0.0
        def GetValue(self):return self.value
        def SetValue(self,v):self.value=v
    for probe,damage,segments,expected,control,reference in [(1,5,[(1,5)],'chain',0,10),(1,12,[(2,7),(1,5)],'additive',0,10),(2,10,[(3,20)],'spell_variant',0,10),(2,20,[(3,10)],'entry',0,10),(2,15,[(3,10)],'unexpected, report',0,10),(2,20,[(3,20)],'control rejected',1,10),(2,20,[(3,20)],'reference rejected',0,1),(2,10,[(3,10)],'reference rejected',0,21)]:
        clock=NS(now=0.0); gate=Global(); session=Global(); health=NS(value=1000.0)
        weapon=NS(GetEnchantment=lambda:None)
        victim=NS(GetActorValue=lambda name:health.value if name=='Health' else 0.0,IsDead=lambda:False)
        player=NS(GetActorValue=lambda name:0.0,GetEquippedWeapon=lambda:weapon)
        player.HasPerk=lambda perk: perk in ({'AB'} if probe==1 else {'Hit','Multiply'})
        observed=[];disposed=[]
        def verdict(*args):
            answer=meter.Verdict(*args);observed.append((args,answer));return answer
        env=dict(__papyrus_concat__=True,Game=NS(GetPlayer=lambda:player),Utility=NS(GetCurrentRealTime=lambda:clock.now),Verdict=verdict)
        flow=Script(b.WORK/'src/ESSBProbeMeter.psc',env)
        flow.fields.update(ProbeAB='AB',ProbeHit='Hit',ProbeMultiply='Multiply',Gate=gate,Session=session,ReferenceSpell='reference')
        flow.overrides.update(RegisterForModEvent=lambda *x:None,RegisterForSingleUpdate=lambda *x:None,Dispel=lambda:disposed.append(True))
        def cast_reference(spell,target):
            assert spell=='reference' and target is victim
            health.value-=reference;flow.OnSegment(victim,4,10)
        player.DoCombatSpellApply=cast_reference
        flow.OnEffectStart(victim,player)
        assert gate.value==0 and not disposed
        health.value-=control
        flow.OnHit(player,weapon,None,False,False,False,False)
        for t in (4,5,9,10):
            clock.now=t;flow.OnUpdate()
            if disposed:break
        if control!=0 or reference!=10:
            assert gate.value==0 and disposed and not observed
            flows.append(dict(control_damage=control,reference_damage=reference,rejected=True))
            continue
        assert gate.value==1 and flow.Calibrated and flow.Phase==0 and not observed and not disposed
        health.value-=damage
        # Segment callbacks may precede OnHit; reversed A/B order is allowed.
        for segment,reported in segments:flow.OnSegment(victim,segment,reported)
        flow.OnHit(player,weapon,None,False,False,False,False)
        for t in (14,15):clock.now=t;flow.OnUpdate()
        assert len(observed)==1 and expected in observed[0][1], observed
        assert observed[0][0][1]==damage
        # Reported magnitude deliberately contradicts health for BOTH tier cases.
        flows.append(dict(probe=probe,health_delta=damage,reported=segments,verdict=observed[0][1]))
    folder=b.WORK/'build/fix18-probe-package'
    records,meta=b.read_plugin(folder/'Elements Spellblade Round18 Probes.esp')
    by={r.edid:r for r in records}
    assert meta['masters']==['Skyrim.esm'] and not meta['flags'] & 0x200
    assert set(r.sig for r in records)=={'KYWD','MGEF','SPEL','GLOB','PERK','QUST'}
    assert len(records)==40 and len({r.key for r in records})==40
    for i in range(1,5):
        effect=by[f'ESSB_ProbeEffect{i}']
        assert effect.d['VMAD']==b.vmad('ESSBProbeSegment',{'Segment':(3,i)})
        data=effect.d['DATA']
        assert struct.unpack_from('<I',data,0)[0]==b.MGEF_HIT_FLAGS
        assert struct.unpack_from('<i',data,16)[0]==41
        assert struct.unpack_from('<II',data,64)==(0,24)
        assert struct.unpack_from('<II',data,80)==(1,1)
    for name,mag,effect in [('ESSB_ProbeA',5,0x801),('ESSB_ProbeB',7,0x802),('ESSB_ProbeMagnitude',10,0x803),('ESSB_ProbeReference',10,0x804)]:
        spell=by[name]
        assert spell.d['EFIT']==struct.pack('<fII',mag,0,0)
        assert spell.d['EFID']==b.I(b.own(effect))
    assert 'KWDA' not in by['ESSB_ProbeReference'].d
    assert 'KWDA' not in by['ESSB_ProbeEffect4'].d
    assert by['ESSB_ProbeMultiply'].d['EPFD']==b.F(2.0)
    assert by['ESSB_ProbeMultiply'].d['DATA']==bytes([29,3,3])
    props={name:(1,b.own(fid)) for name,fid in [('ProbeAB',0x820),('ProbeHit',0x821),('ProbeMultiply',0x822),('Gate',0x832),('Session',0x833),('ReferenceSpell',0x813),('CrossA',0x850),('CrossB',0x851),('CrossA2',0x852),('CrossB2',0x853),('TieA', 2144), ('TieB', 2145), ('TieA2', 2147), ('TieB2', 2146), ('TieVariant', 2160), ('TieResult1', 2161), ('TieResult2', 2162), ('TieResult3', 2163), ('TieResult4', 2164)]}
    assert by['ESSB_ProbeMeterEffect'].d['VMAD']==b.vmad('ESSBProbeMeter',props)
    assert struct.unpack_from('<II',by['ESSB_ProbeMeterEffect'].d['DATA'],80)==(0,0)
    assert by['ESSB_ProbeMeter'].d['SPIT']==b.spit(1,0,0)
    assert [v for k,v in by['ESSB_ProbeMeter'].ss if k=='CTDA']==[
        b.ctda(1,1,448,b.own(0x820),run_on=2,reference=0x14),
        b.ctda(1,1,448,b.own(0x821),run_on=2,reference=0x14),
        b.ctda(1,1,448,b.own(0x850),run_on=2,reference=0x14),
        b.ctda(1,1,448,b.own(0x852),run_on=2,reference=0x14),
        b.ctda(1,1,448,b.own(0x860),run_on=2,reference=0x14),
        b.ctda(0,1,448,b.own(0x863),run_on=2,reference=0x14)]
    assert by['ESSB_ProbeGate'].d['FLTV']==b.F(0)
    assert by['ESSB_ProbeSession'].d['FLTV']==b.F(0)
    for name,priorities in [('ESSB_ProbeAB',[200,199]),('ESSB_ProbeMagnitudeHit',[0])]:
        record=by[name]
        assert [v for k,v in record.ss if k=='PRKE']==[bytes([2,0,p]) for p in priorities]
        assert [v for k,v in record.ss if k=='DATA'][1:]==[bytes([51,10,3])]*len(priorities)
        assert [v for k,v in record.ss if k=='CTDA'].count(b.ctda(0,1,74,b.own(0x832)))==len(priorities)
        assert [v for k,v in record.ss if k=='CTDA'].count(b.ctda(0,1,214,b.own(0x830)))==len(priorities)
    for name in ('ESSBProbeMeter','ESSBProbeSegment'):
        assert (folder/'Source/Scripts'/f'{name}.psc').read_bytes()==(b.WORK/'src'/f'{name}.psc').read_bytes()
        assert (folder/'Scripts'/f'{name}.pex').read_bytes()[:4]==bytes.fromhex('FA57C0DE')
        assert name not in b.SCRIPTS
    report=dict(cases=results,event_flows=flows,resistance_guard_cases=20,records=40,runtime_tested=False)
    (folder/'offline-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('PROBE-LOGIC ok: actual Papyrus 5/12/10/20 + unexpected/duplicate/invalid cases; 20 resistance guards; native ESP and compiled PEX readback')
    return report
