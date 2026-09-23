"""Round 18: actual record readback + source-body differential and cost gates."""
from pathlib import Path
from types import SimpleNamespace as NS
import json,math,struct,itertools,sys,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build'),str(ROOT)]
from fix12_cost import scenario,Measured
from papyrus_harness import Array
import build_v03 as b
import fix18_records as r18
OLD=ROOT/'.codex/pre-fix18-snapshot/src'
NEW=ROOT/'src'

def fixture(folder=NEW):
    c,t,p,v,w,clock,m,env,G=scenario(folder,prepare_only=True)
    env['Math'].Ceiling=math.ceil
    settings=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))
    c.fields['ElementDamageMin']=Array([settings['element_damage'][e][0] for e in b.ELEMENTS]);c.fields['ElementDamageMax']=Array([settings['element_damage'][e][1] for e in b.ELEMENTS])
    p.GetActorValuePercentage=lambda av:1.
    v.GetActorValuePercentage=lambda av:1.
    writes=[];applications=[]
    class Spell:
        def __init__(self,e,p=0):self.e=e;self.power=p;self.values={}
        def SetNthEffectMagnitude(self,i,x):self.values[i]=x;writes.append((self.e,self.power,i,x))
    if folder==NEW:
        c.fields['ProcVariants']=Array([Spell(x['e'],x['p']) for x in r18.variants(b)])
        c.fields['ProcCacheReady']=False
        c.fields['HitBonusSpells']=Array([Spell(e) for e in range(1,12)])
    c.fields['HitNormalSpells']=Array([Spell(e) for e in range(1,12)])
    c.fields['HitPowerSpells']=Array([Spell(e,1) for e in range(1,12)])
    # Only damage native boundary is mocked; full ApplyProc source executes.
    p.DoCombatSpellApply=lambda spell,target:applications.append(dict(spell=spell.e,values=dict(spell.values)))
    c.overrides.update(InDomain=lambda *a:False)
    return NS(c=c,t=t,p=p,v=v,w=w,clock=clock,m=m,env=env,G=G,writes=writes,apps=applications)

def ranks(f,tree,route,tier,value=0,bits=0):
    i=tree*15+route*5+tier;idx=i if i<120 else i-120
    (f.t.AllRankA if i<120 else f.t.AllRankB)[idx]=value
    (f.t.AllBranchA if i<120 else f.t.AllBranchB)[idx]=bits

def player_sequences():
    rows=[]
    for state in range(6):
        a=fixture(OLD);n=fixture()
        for f in (a,n):
            f.c.overrides.update(GetStack=lambda *x:0,GetAirborne=lambda *x:0,HasStarLock=lambda *x:False,HasElementMark=lambda *x:False)
            for tree in range(13):
                f.t.LevelCache[tree]=1+state*13
                for tier in range(5):
                    ranks(f,tree,0,tier,state)
                    ranks(f,tree,1,tier,state*2)
            f.c.fields['CachedSync']=state*9;f.c.Sync.v=state*9
            f.c.fields['BloodthirstLeft']=110 if state>=1 else 0
            f.c.fields['EndBoostLeft']=110 if state>=2 else 0;f.c.fields['EndBoostAmount']=.21
            for e in range(1,12):f.c.OpenBoost[e]=110 if state>=3 else 0
            f.c.fields['SelfOverheat']=1 if state>=4 else 0
            f.c.fields['MoltenLeft']=110 if state>=5 else 0
            f.c.EnvNight.v=state%2
        n.c.RefreshSyncStage();n.c.RefreshProcMagnitudes()
        for e,power in itertools.product(range(1,12),(False,True)):
            # Target-side multiplier explicitly one; blood's approved step is compared separately.
            if e==6:continue
            a.c.ApplyProc(a.v,e,power,False,False)
            old=a.apps[-1]['values'][0]
            current=next(s.values[0] for s,v in zip(n.c.ProcVariants,r18.variants(b)) if v['e']==e and v['p']==int(power) and v['s']==0 and v['band']==0 and v['existing'])
            assert math.isclose(current,old,abs_tol=1e-4),(state,e,power,current,old)
            rows.append([state,e,power,current])
        n.writes.clear();n.c.RefreshProcMagnitudes();assert n.writes==[],('repeat writes',state,n.writes)
    return {'sequences':6,'comparisons':len(rows),'repeat_writes':0,'rows':rows}

def heat_case(heat,elapsed=0,rank=0):
    result=[]
    for folder in (OLD,NEW):
        f=fixture(folder);f.c.CurrentElement.v=1
        ranks(f,0,0,0,rank);ranks(f,0,0,1,rank)
        status=Measured(folder/'ESSBStatus.psc',f.env)
        status.fields.update(Ctl=f.c,Holder=f.v,Heat=heat,HeatTime=100-elapsed,RingClock=100-elapsed,
            BleedRing=Array([0]*10),PoisonRing=Array([0]*12),AstralRing=Array([0]*2),AstralWeight=Array([0.]*2))
        f.c.RegActor[0]=f.v;f.c.RegElem[0]=1;f.c.RegStatus[0]=status
        if folder==NEW:f.c.RefreshProcMagnitudes()
        f.m.script.clear();f.m.native.clear();f.apps.clear()
        f.c.ApplyProc(f.v,1,False,False,False,0,f.c.RegGeneration[0])
        base=f.c.ProcVariants[0].values[0] if folder==NEW else 0
        result.append(dict(base=base,script=f.apps[-1]['values'][0] if f.apps else 0,heat=status.Heat,
                           reads=f.m.script['ESSBController.GetStack'],ticks=f.m.script['ESSBStatus.Tick'],applications=len(f.apps)))
    old,new=result
    assert math.isclose(new['base']+new['script'],old['script'],abs_tol=1e-4),(heat,elapsed,rank,result)
    assert old['heat']==new['heat'] and old['reads']==new['reads'] and old['ticks']==new['ticks'],result
    if new['script']<=0:assert new['applications']==0
    return dict(heat=heat,elapsed=elapsed,rank=rank,old=old,engine_plus_script=new)

def differences():
    rows=[heat_case(0),heat_case(4),heat_case(4,6),heat_case(4,0,9),heat_case(10,0,15)]
    worked=rows[1]['engine_plus_script'];assert math.isclose(worked['base'],11.55,abs_tol=1e-4) and math.isclose(worked['script'],3.696,abs_tol=1e-4)
    fast=[]
    for e in range(2,12):
        if e==7:continue
        f=fixture();f.m.script.clear();f.m.native.clear();f.m.cross=0
        f.c.ApplyProc(f.v,e,False,False,False)
        assert not f.apps and f.m.cross==0 and f.m.script['ESSBController.GetStack']==0,(e,f.m.script,f.m.cross)
        fast.append(e)
    return dict(rows=rows,zero_cross_script_elements=fast,innate_exceptions=[1,7],GetStack_lazy_tick_preserved=True)

def sync_samples():
    a=fixture(OLD);n=fixture()
    for i in range(200):
        for f in (a,n):
            f.c.fields['CachedSync']=i%41;f.c.Sync.v=i%41
            ranks(f,12,0,0,i%16)
            ranks(f,12,0,1,0,2 if i%2 else 0)
            f.c.fields['FormOpenTime']=0 if i%3 else 99
        n.c.RefreshSyncStage();assert a.c.SyncStage()==n.c.SyncStage(),i
    return 200

def guard_fast():
    f=fixture();g=Measured(NEW/'ESSBGuard.psc',f.env)
    g.fields.update(Ctl=f.c,Ready=True,Enabled=f.G(1),FormActive=f.G(0),DivineArmed=f.G(0),RockArmor=f.G(0),IceShield=f.G(0),WaterMirror=f.G(0),GuardWind=f.G(0),NodeBits=False)
    g.overrides['GetActorReference']=lambda:f.p
    f.m.script.clear();f.m.native.clear();g.OnHitEx(f.v,None,None,False,False,False,False)
    assert not any(k.startswith('ESSBController.') for k in f.m.script),f.m.script
    return dict(controller_calls=0,natives=dict(f.m.native))

def record_checks():
    records,meta=b.read_plugin(b.OUT/b.PLUGIN);by={r.edid:r for r in records};perk=by['ESSB_P_HitProc']
    assert not any(k=='PRKE' for k,v in perk.ss), 'round19 release perk must be empty'
    # Original serialized oracle remains immutable in the round19 snapshot.
    old_records,_=b.read_plugin(ROOT/'.codex/pre-fix19-snapshot/package/Elements Spellblade/Elements Spellblade.esp')
    perk=next(r for r in old_records if r.edid=='ESSB_P_HitProc')
    entries=[];x=None;tab=None
    for k,v in perk.ss:
        if k=='PRKE':x={'conds':[]}
        elif x is not None:
            if k=='DATA':assert list(v)==[51,10,3]
            elif k=='EPFT':assert v==bytes([5])
            elif k=='EPFD':x['spell']=struct.unpack('<I',v)[0]&0xffffff
            elif k=='PRKC':tab=v[0]
            elif k=='CTDA':x['conds'].append((tab,v))
            elif k=='PRKF':entries.append(x);x=None
    assert len(entries)==74
    expected=r18.entries(b,json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['lightning_roll_mode'])
    assert all(x['spell']==r['spell'] and x['conds']==r['conditions'] for x,r in zip(entries,expected))
    # Independent evaluator of serialized CTDA including OR groups. RNG chain uses first-success selection.
    def passes(conds,state):
        group=False
        for tab,v in conds:
            op=v[0];val=struct.unpack_from('<f',v,4)[0];fn=struct.unpack_from('<H',v,8)[0];param=struct.unpack_from('<I',v,12)[0]
            if fn==74:actual=state['globals'][param]
            elif fn==597:actual=state['weapon']
            elif fn==673:actual=state['power']
            elif fn==286:actual=state['sneak']
            elif fn==640:actual=state['hp']
            elif fn==77:actual=state['random']
            else:actual=state.get(fn,0)
            result={0:actual==val,0x20:actual!=val,0x60:actual>=val,0x80:actual<val,0xA0:actual<=val}[op&0xe0]
            group=group or result
            if not op&1:
                if not group:return False
                group=False
        return True
    cases=0
    for active,e,power,sneak,weapon,hp in itertools.product(range(2),range(12),range(2),range(2),[0,1,7,12],[.1,.35,.65,.95]):
        st=dict(globals={b.own(b.ID_GLOB['ESSB_Enabled']):1,b.own(b.ID_GLOB['ESSB_FormActive']):active,b.own(b.ID_GLOB['ESSB_CurrentElement']):e},power=power,sneak=sneak,weapon=weapon,hp=hp,random=99)
        selected=[x for x in entries if passes(x['conds'],st)]
        assert len(selected)==int(active==1 and e>=1),(st,selected)
        for fn in [453,700,46,569]:
            st[fn]=1;assert not any(passes(x['conds'],st) for x in entries);st[fn]=0
        cases+=1
    # N=1 first-success probabilities; integer 0..99 sampling introduces <=0.5% absolute error.
    remaining=1.;probs=[]
    for j in range(5,0,-1):
        q=math.ceil(100/j)/100 if j>1 else 1.
        probs.append(remaining*q);remaining*=1-q
    assert all(abs(x-.2)<.005 for x in probs),probs
    for row in r18.variants(b):
        spell=by[row['edid']];assert struct.unpack_from('<II',spell.d['SPIT'],16)==(1,1)
        assert any(k=='EFID' and struct.unpack('<I',v)[0]==b.own(b.ID_ENGAGED_EFFECT) for k,v in spell.ss)
    for e in b.ELEMENTS:
        eff=by['ESSB_HitBonusEffect_'+e];d=eff.d['DATA']
        assert struct.unpack_from('<I',d)[0]&0x10 and 'VMAD' not in eff.d
        assert all(struct.unpack_from('<I',d,off)[0]==0 for off in [32,36]) and 'SNDD' not in eff.d
        form=by['ESSB_FormAbilityEffect_'+e];assert all(struct.unpack_from('<I',form.d['DATA'],off)[0]==0 for off in [32,36])
        assert not any('SyncGlow' in byid.edid for byid in records if byid.key in by['ESSB_FormAbility_'+e].refs('EFID'))
    old=json.loads((ROOT/'.codex/pre-fix18-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    cur=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    import state_schema
    assert all(state_schema.stable_identity(k,cur.get(k),v) for k,v in old.items())
    assert cur['ESSB_DebugLevel']['id']=='000811'
    diff={'added':{k:v for k,v in cur.items() if k not in old},'removed':[k for k in old if k not in cur], 'changed':{k:[v,cur[k]] for k,v in old.items() if cur.get(k)!=v}}
    (ROOT/'build/fix18-formid-diff.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2),encoding='utf8')
    return dict(entries=0,oracle_entries=74,truth_table_states=cases,chain_probabilities=probs,identities=len(old),records=len(records))

def run():
    import fix18_extra_checks as extra
    report=dict(input=extra.input_checks(ROOT),target_combinations=extra.targets(NS(**globals())),blood=extra.blood(NS(**globals())),player=player_sequences(),difference=differences(),sync=sync_samples(),guard=guard_fast(),records=record_checks())
    before=scenario(OLD);after=scenario(NEW)
    assert before['total']==165 and after['total']<=165
    report.update(before=before,after=after,runtime_tested=False)
    for name in ['ESSBStatus.psc','ESSBMark.psc','ESSBElem.psc','ESSBElem2.psc','ESSBElem3.psc','ESSBReactions.psc']:
        assert (OLD/name).read_bytes()==(NEW/name).read_bytes(),('status layer changed',name)
    (ROOT/'build/fix18-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    # Label says only what this function checks; the DLL <-> manifest <-> ESP mapping is checked by NATIVE (fix19_native.verify).
    print('HITPROC ok: release hit perk has 0 entries; round-18 snapshot 74 entries == generator oracle; engine_base + script_bonus == old within 1e-4; no-eligible-target multiplier zero cross-script reads; <=0 no spell; lazy GetStack Tick preserved')
    print(f'FIX17 ok: Guard no-work zero Controller calls; mirror Rank/Br; SyncStage 200 samples; hit calls {before["total"]} -> {after["total"]}')
    print('FIX18 ok: 15 input gates; 88 target combinations; 88 blood cases; six player sequences; repeat magnitude writes 0; native base delivery only; status sources byte-identical')
    return report

if __name__=='__main__':run()
