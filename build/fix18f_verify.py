"""Actual shipped PSC: cross-perk verdicts/modes, conservative hit sets and setup failures.

Native functions are mocked, not evidence of Skyrim entry-51 traversal/collision.
"""
from types import SimpleNamespace as NS
import itertools
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
        def __init__(self, fid, kind=0): self.fid, self.kind = fid, kind
        def GetFormID(self): return self.fid
        def GetType(self): return self.kind
        def GetEnchantment(self): return None
        def __str__(self): return f'{self.fid:08X}'

    def fixture(mode=3):
        perks = {name: Form(fid) for name, fid in [('ProbeAB',0x820),('ProbeHit',0x821),('ProbeMultiply',0x822),('CrossA',0x850),('CrossB',0x851),('CrossA2',0x852),('CrossB2',0x853)]}
        state = NS(health=10000.0, now=0.0, av={}, perks={1:{0x820},2:{0x821,0x822},3:{0x850,0x851},4:{0x852,0x853}}[mode])
        logs, disposed = [], []
        weapon = Form(0x1397e,41)
        player = NS(HasPerk=lambda p:p.fid in state.perks, GetActorValue=lambda n:state.av.get(n,0),GetEquippedWeapon=lambda:weapon)
        victim = NS(GetActorValue=lambda n:state.health if n=='Health' else state.av.get(n,0), IsDead=lambda:False)
        env = dict(__execute_logs__=True,__papyrus_concat__=True, Game=NS(GetPlayer=lambda:player),
                   Debug=NS(Trace=logs.append),Utility=NS(GetCurrentRealTime=lambda:state.now),
                   Math=NS(RightShift=lambda v,n:(v&0xffffffff)>>n,LogicalAnd=lambda a,c:a&c),
                   StringUtil=NS(GetNthChar=lambda s,i:s[i]))
        m = Script(b.WORK/'src/ESSBProbeMeter.psc',env)
        m.fields.update(perks,Player=player,Gate=Global(),Session=Global(),ReferenceSpell=Form(0x813,22))
        m.overrides.update(RegisterForModEvent=lambda *a:None,RegisterForSingleUpdate=lambda *a:None,Dispel=lambda:disposed.append(True))
        def reference(spell,target):
            assert target is victim and spell is m.ReferenceSpell
            state.health -= 9.5
            m.OnSegment(victim,4,0)
        player.DoCombatSpellApply = reference
        def hit(source=weapon, aggressor=player, power=False): m.OnHit(aggressor,source,None,power,False,False,False)
        def update(t): state.now=t; m.OnUpdate()
        return m,state,player,victim,weapon,logs,disposed,hit,update

    # All 128 perk subsets, including mixed/partial pairs, must fail closed.
    m,state,*_ = fixture()
    ids=[0x820,0x821,0x822,0x850,0x851,0x852,0x853]
    expected={frozenset([0x820]):1,frozenset([0x821,0x822]):2,frozenset([0x850,0x851]):3,frozenset([0x852,0x853]):4}
    for bits in itertools.product((False,True),repeat=7):
        state.perks={fid for fid,bit in zip(ids,bits) if bit}
        assert m.CurrentMode()==expected.get(frozenset(state.perks),0)

    cases=[(1,7,[2],'lightning_roll_mode = exclusive')]
    for mode in (3,4):
        cases += [(mode,12,[1,2],'cross-perk additive: coexistence OK'),(mode,5,[1],'single winner A (5)'),(mode,7,[2],'single winner B (7)'),
                  (mode,0,[],'unexpected'),(mode,12,[1],'unexpected'),(mode,7,[2,2],'unexpected'),(mode,20,[3],'unexpected')]
    for mode,damage,segments,wanted in cases:
        m,state,player,victim,weapon,logs,disposed,hit,update=fixture(mode)
        m.OnEffectStart(victim,player);hit()
        for t in (4,5,9,10):update(t)
        assert m.Calibrated and not disposed
        state.health-=damage*0.95
        for segment in segments:m.OnSegment(victim,segment,0)
        hit();update(14);update(15)
        assert any(wanted in line and 'basis=health_delta/k' in line for line in logs),logs
        counts=[segments.count(i) for i in (1,2,3)]
        assert 'unexpected' in m.Verdict(mode,damage,*counts,True)
        if wanted!='unexpected':
            for offset in (-0.15,0.15):assert wanted in m.Verdict(mode,damage+offset,*counts,False)
            for offset in (-0.151,0.151):assert 'unexpected' in m.Verdict(mode,damage+offset,*counts,False)
        rows.append(dict(case='verdict',mode=mode,damage=damage,segments=segments,logs=logs))

    # Source order arbitrary; count everything, zero damage EXACT (not tolerance).
    for order in ('EWE','WEE','EEW'):
        m,state,player,victim,weapon,logs,disposed,hit,update=fixture()
        m.OnEffectStart(victim,player)
        for token in order:hit(weapon if token=='W' else Form(0x63000e76,0))
        assert m.Hits==3 and m.WeaponHits==1 and m.ExtraHits==2
        for t in (4,5,9,10):update(t)
        assert m.Calibrated and not disposed
        assert any('IGNORED control extra events=2 total=3' in x for x in logs)
        assert m.Hits==m.WeaponHits==m.ExtraHits==0
        # The following clean probe still decides correctly.
        state.health-=11.4;m.OnSegment(victim,1,0);m.OnSegment(victim,2,0);hit();update(14);update(15)
        assert any('cross-perk additive:' in x for x in logs)
        rows.append(dict(case='ignored-control',order=order,logs=logs))

    faults=['no-weapon','double-weapon','nonzero','tiny-delta','healing','spell','our-spell','weapon','projectile','none','wrong-aggressor','power','late','segment','probe-extra','reference-extra','resistance']
    for fault in faults:
        m,state,player,victim,weapon,logs,disposed,hit,update=fixture()
        m.OnEffectStart(victim,player)
        if fault!='no-weapon':hit()
        if fault in ('probe-extra','reference-extra'):
            update(4);update(5)
            if fault=='probe-extra':
                update(9);update(10)
                state.health-=11.4;m.OnSegment(victim,1,0);m.OnSegment(victim,2,0);hit()
        source=Form(0xfe38982d,0)
        if fault=='spell':source=Form(0x123,22)
        if fault=='our-spell':source=m.ReferenceSpell
        if fault=='weapon':source=Form(0x123,41)
        if fault=='projectile':source=Form(0x123,50)
        if fault=='none':source=None
        if fault=='late':update(4)
        hit(source, None if fault=='wrong-aggressor' else player, fault=='power')
        if fault=='double-weapon':hit()
        if fault in ('nonzero','tiny-delta','healing'):state.health-= {'nonzero':1,'tiny-delta':0.001,'healing':-1}[fault]
        if fault=='resistance':state.av['FireResist']=33
        if fault=='segment':m.OnSegment(victim,1,0)
        for t in (20,21):update(t)
        assert disposed and m.Gate.value==0,(fault,logs)
        assert not any('cross_perk_mode =' in x for x in logs),(fault,logs)
        assert not any('IGNORED control extra' in x for x in logs),(fault,logs)
        rows.append(dict(case='reject-hit-set',fault=fault,logs=logs))

    records,meta=b.read_plugin(b.WORK/'build/fix18-probe-package/Elements Spellblade Round18 Probes.esp')
    by={r.edid:r for r in records}
    for suffix,fid,spell,priority in [('A',0x850,0x810,200),('B',0x851,0x811,199),('A2',0x852,0x810,199),('B2',0x853,0x811,200)]:
        r=by['ESSB_ProbeCross'+suffix]
        assert int(r.key.split('|')[1],16)==fid
        assert [v for k,v in r.ss if k=='PRKE']==[bytes([2,0,priority])]
        assert [v for k,v in r.ss if k=='DATA']==[b.perk_data(playable=0,hidden=1),bytes([51,10,3])]
        assert r.d['EPFD']==b.I(b.own(spell)) and r.d['EPFT']==bytes([5])
        assert [v for k,v in r.ss if k=='CTDA']==[v for k,v in by['ESSB_ProbeMagnitudeHit'].ss if k=='CTDA']
    assert len(records)==40 and meta['masters']==['Skyrim.esm']
    # Pure PSC setup loops: late additions/removals, timeout and final-check refusal.
    setup_cases=[]
    for fault in ('late-add-remove','never-stable','no-3d','dead','final-drift'):
        av={n:0.0 for n in ('FireResist','MagicResist','AbsorbChance','HealRate','HealRateMult')}
        av['Health']=10000.0
        state=NS(ticks=0,maxhealth=10000.0,loaded=fault!='no-3d')
        logs=[]
        target=NS(GetActorValue=lambda n:av[n],GetActorValueMax=lambda n:state.maxhealth,
                  Is3DLoaded=lambda:state.loaded,IsDead=lambda:fault=='dead',IsDisabled=lambda:False,IsDeleted=lambda:False)
        def mod(n,value):
            av[n]+=value
            if n=='Health':state.maxhealth+=value
        def restore(n,value):av[n]=min(state.maxhealth,av[n]+value)
        target.ModActorValue=mod;target.RestoreActorValue=restore
        def wait(duration):
            state.ticks+=1
            if fault=='never-stable':av['FireResist']+=33
            if fault=='late-add-remove' and state.ticks in (1,4):
                delta=33 if state.ticks==1 else -33
                av['FireResist']+=delta;av['Health']+=50;state.maxhealth+=50
        player=object()
        s=Script(b.WORK/'src/ESSBProbeSetup.psc',dict(__execute_logs__=True,__papyrus_concat__=True,Game=NS(GetPlayer=lambda:player),Utility=NS(Wait=wait),Debug=NS(Trace=logs.append)))
        s.fields['Bandit']=target
        result=s.SettleBandit()
        assert result==(fault in ('late-add-remove','final-drift')),(fault,logs)
        if result:
            assert av['FireResist']==0 and state.maxhealth==av['Health']==10000
        if fault=='final-drift':
            av['FireResist']=33
            assert not s.SetupReady()
        if fault=='never-stable':assert state.ticks==30
        setup_cases.append(dict(case=fault,result=result,ticks=state.ticks,logs=logs))

    source=(b.WORK/'src/ESSBProbeSetup.psc').read_text(encoding='utf8')
    assert 'EnableAI(False)' not in source and 'Bandit.ForceActorValue' not in source
    assert source.index('Bandit.Is3DLoaded()')<source.index('Bandit.SetRestrained(True)')
    assert source.index('If !SetupReady()')<source.index('Bandit.AddSpell(Meter, False)')
    report=dict(actual_psc_executed=True,mode_subsets=128,cases=rows,setup_cases=setup_cases,records=40,masters=meta['masters'],runtime_tested=False,
                boundary='Native collision, entry 51 winner and other-mod compatibility require in-game trials; no network/deployment')
    (b.WORK/'build/fix18-probe-package/round18f-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(f'PROBE-ROUND18F ok: 128 perk subsets; {len(cases)} verdict flows; 3 ignored controls; {len(faults)} rejected hit sets; 5 setup/AV failure cases; cross-perk ESP readback')
    return report
