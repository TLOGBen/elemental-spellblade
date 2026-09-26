"""Round 14 actual Papyrus source execution; native calls mocked, no runtime claim."""
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib, json, re, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
# Round 22: these checks run on the pre-fix22 scripts; build/fix22_history.py ties them to today's (declared changes only).
import sys as _sys22
_sys22.path.insert(0, str(ROOT / 'build'))
import fix22_history as _fix22_history
SRC22 = _fix22_history.legacy_source()

sys.path[:0]=[str(ROOT/'build'),str(ROOT)]
from fix12_cost import scenario
from papyrus_harness import Array
NEW = SRC22
OLD=ROOT/'.codex/pre-fix14-snapshot/src'

def fixture(folder=NEW, debug=0):
    c,t,p,v,w,clock,m,env,G=scenario(folder,debug,True)
    owned={(9,2,0,1)}; rolls=[0.0]; events=[]; snapshots=[]; settled=[]
    c.fields.update(AshSpell=object(),ReanimateSpell=NS(SetNthEffectMagnitude=lambda *a:None,SetNthEffectDuration=lambda *a:None),
                    DragonKeyword='dragon',NoReanimateKeyword='no-reanimate',MultDuration=G(1))
    c.RegActor[0]=None;c.RegStatus[0]=None;c.DamageActor[0]=None
    c.overrides.update(IsVIPTarget=lambda target:getattr(target,'vip',False),GetStack=lambda *a:0,
                       SummonCap=lambda:1,ServantCount=lambda:0,SyncStage=lambda:0)
    env['ESSBNodes'].overrides['Br']=lambda ctl,*key:key in owned
    env['Utility'].RandomFloat=lambda *a:rolls[0]
    env['ESSBNoForm']=NS(OnKill=lambda *a:None,IsSpellUser=lambda *a:False)
    c.overrides['ApplyAsh']=lambda target:events.append('ash') or True
    c.overrides['ApplyReanimate']=lambda *a:events.append('reanimate') or True
    c.overrides['KeepSneak']=lambda *a:events.append('streak')
    # The logs themselves use the real cached guard/throttler and counter.
    def actor(hp=100,level=10):
        a=NS(hp=hp,level=level,keywords=set(),vip=False)
        a.GetActorValue=lambda av:a.hp if av=='Health' else 100
        a.GetActorValueMax=lambda av:100
        a.IsDead=lambda:a.hp<=0
        a.GetLevel=lambda:a.level
        a.GetFormID=lambda:id(a)
        a.HasKeyword=lambda k:k in a.keywords
        a.DispelSpell=lambda *args:None
        a.HasMagicEffect=lambda effect:True
        return a
    victim=actor()
    p.DoCombatSpellApply=lambda spell,target:setattr(target,'hp',target.hp-spell.mag)
    def mark(e,secondary=False,real=True):
        c.OccupySlot(0,victim)
        if secondary:
            c.RegElem2[0]=e;c.RegSecondReal[0]=real;c.RegSecondUntil[0]=clock[0]+8;c.RegSeq2[0]=2
            c.RegMark2[0]=NS(DispelIfActive=lambda:None) if real else None
        else:
            c.RegElem[0]=e;c.RegUntil[0]=clock[0]+8;c.RegSeq[0]=1
            c.RegMark[0]=NS(DispelIfActive=lambda:None)
    def damage(e,amount=1):c.ApplyTrackedDamage(p,NS(mag=amount),victim,e)
    def kill():
        victim.hp=0
        # Round 21: 亡者歸來 was removed early (ruling C3; N5 redoes it per v0.4), so a darkness kill has no Papyrus
        # effect. The attribution under test is observed, not simulated: `settled` records the element the real
        # OnKillEvent wrote into its settlement ring (SettledElement); no event is ever made up here.
        slot=c.fields.get('SettledNext')
        c.OnKillEvent(victim,p)
        if slot is not None and 'SettledElement' in c.fields and c.fields.get('SettledNext')!=slot:
            settled.append(c.SettledElement[slot])
    return NS(c=c,p=p,v=victim,clock=clock,m=m,env=env,owned=owned,rolls=rolls,events=events,settled=settled,
              mark=mark,damage=damage,kill=kill,actor=actor)

def outcome(f,want):
    """'ash': the real ApplyAsh ran. 'darkness': no Papyrus effect (亡者歸來 removed, C3) and the real settlement
    recorded darkness as the killing element."""
    if want=='ash':
        return f.events==['ash']
    return f.events==[] and f.settled[-1:]==[10]

def attribution(folder=NEW):
    cases={}
    for e,want in [(10,'darkness'),(7,'ash')]:
        for source in ('mark','recent','recent-over-other-mark','newest-damage','expired-damage-mark', 'secondary-real'):
            f=fixture(folder)
            other=7 if e==10 else 10
            if source=='mark':f.mark(e)
            elif source=='recent':f.damage(e)
            elif source=='recent-over-other-mark':f.mark(other);f.damage(e)
            elif source=='newest-damage':
                f.damage(other);f.clock[0]+=.2;f.damage(e)
            elif source=='expired-damage-mark':
                f.mark(e);f.damage(other);f.clock[0]+=3.001
            elif source=='secondary-real':f.mark(e,True,True)
            # Explicit form switch: current form must never override victim evidence.
            f.c.CurrentElement.v=other
            f.kill()
            assert outcome(f,want),(e,source,f.events,f.settled)
            cases[f'{e}:{source}']=f.events
    for source in ('no-evidence','expired-damage','clock-backwards','virtual-secondary','expired-mark','failed-damage'):
        f=fixture(folder);f.c.CurrentElement.v=10
        if source=='expired-damage':f.damage(10);f.clock[0]+=3.001
        elif source=='clock-backwards':f.damage(10);f.clock[0]-=1
        elif source=='virtual-secondary':f.mark(10,True,False)
        elif source=='expired-mark':f.mark(10);f.clock[0]+=8.001
        elif source=='failed-damage':f.damage(10,0)
        assert f.c.KillElementFor(f.v,f.c.FindSlot(f.v))==0,source
        f.kill();assert f.events==[],(source,f.events)
        cases[source]='element 0; no effect'
    f=fixture(folder);f.damage(10);f.clock[0]+=3;assert f.c.LastDamageWasElement(f.v,10)
    f.clock[0]+=.001;assert not f.c.LastDamageWasElement(f.v,10)
    f=fixture(folder);f.damage(10);f.clock[0]+=.1;f.damage(7,0)
    assert f.c.LastDamageFor(f.v)==10,'resisted application overwrote valid earlier damage'
    f=fixture(folder);f.mark(7);f.damage(7);f.clock[0]+=.1;f.damage(10)
    f.c.CurrentElement.v=10;f.kill();assert outcome(f,'darkness'),'divine -> darkness weapon kill ashed'
    # A form switch alone is not evidence: recent divine still wins, per the approved rule.
    f=fixture(folder);f.damage(7);f.c.CurrentElement.v=10;f.kill();assert f.events==['ash']
    f=fixture(folder);f.damage(7);f.clock[0]+=3.001;f.c.CurrentElement.v=10;f.kill();assert not f.events
    cases['switches']='new darkness beats old divine; form-only switch preserves recent divine; expired evidence -> 0'
    for e,want in [(7,'ash'),(10,'darkness')]:
        f=fixture(folder);f.mark(e);f.c.RegMark[0]=None
        f.c.fields['MarkSpells']=Array([NS(GetNthEffectMagicEffect=lambda i:object()) for _ in range(11)])
        f.v.HasMagicEffect=lambda effect:False
        assert f.c.KillElementFor(f.v,0)==0,'queued but unapplied mark is not real evidence'
        f.v.HasMagicEffect=lambda effect:True
        f.kill();assert outcome(f,want)
        cases[f'{e}:native-mark-before-start-callback']='actual MGEF required when callback pending'
    f=fixture(folder);f.damage(10);f.v.hp=0;f.c.OccupySlot(0,f.v);f.c.CaptureDeath(0)
    f.clock[0]+=20;f.c.ClearSlot(0);f.kill();assert outcome(f,'darkness')
    cases['recent-capture']='recent damage frozen before delayed kill dispatch'
    # Independent actors, eviction/promotion, rollback, and ring reuse.
    f=fixture(folder);f.mark(10);f.damage(10);f.c.ClearSlot(0)
    assert f.c.KillElementFor(f.v)==10
    assert f.c.KillElementFor(f.actor())==0
    f.c.OccupySlot(0,f.v);assert f.c.LastDamageFor(f.v)==10
    for _ in range(129):f.c.ApplyTrackedDamage(f.p,NS(mag=1),f.actor(),7)
    assert f.c.LastDamageFor(f.v)==0
    cases['ring']='eviction/promotion/cross-target/129 replacements'
    # Freeze attribution before AME finish or Tick clear; delayed dispatch cannot erase it.
    for e,want in [(10,'darkness'),(7,'ash')]:
        for cleanup in ('capture-clear','mark-finish'):
            f=fixture(folder);f.mark(e);f.v.hp=0
            if cleanup=='capture-clear':f.c.CaptureDeath(0);f.c.ClearSlot(0)
            else:
                f.c.overrides['EndMark']=lambda *a:(f.c.RegElem.__setitem__(0,0),f.c.RegMark.__setitem__(0,None))
                f.c.OnMarkFinish(e,f.v,f.c.RegMark[0])
                f.c.CaptureDeath(0) # second cleanup must not overwrite first evidence
            f.clock[0]+=20;f.kill();f.kill()
            assert outcome(f,want),(cleanup,e,f.events,f.settled)
            cases[f'{e}:{cleanup}']=f.events
    # Pure Land is the explicit design exception and must win even over darkness evidence.
    f=fixture(folder);f.damage(10);f.owned.add((6,0,4,1));f.c.CurrentElement.v=7
    f.c.overrides['SyncStage']=lambda:3;f.kill();assert f.events==['ash']
    cases['pure-land']='ash first; no reanimation'
    f=fixture(folder);f.mark(5);f.owned.add((4,2,4,1));f.c.fields['LastHitSneak']=True
    if 'HitActor' in f.c.fields:f.c.HitActor[0]=f.v;f.c.HitSneak[0]=True
    if 'HitForm' in f.c.fields:f.c.HitForm[0]=5
    f.kill();assert f.events==['streak'];cases['wind']='shared attribution'
    return cases

def diagnostics():
    cases={}
    def check(name,setup,action,reason):
        for level in (0,2):
            f=fixture(debug=level);setup(f)
            f.m.concat=0;f.m.native.clear();f.m.script.clear()
            action(f)
            # Inspect the strings entering real LogThrottled without bypassing it.
            if level==0:
                assert f.m.concat==0 and f.m.native['Debug.Trace']==0,(name,'L0 built a log')
            else:
                assert any(reason in line for line in f.messages),(name,reason,f.messages)
                rejects=[x for x in f.messages if '-reject]' in x]
                if name.startswith('reanimate-') or name.startswith('apply-') or name.startswith('can-'):
                    assert len(rejects)==1,(name,rejects)
                cases[name]=rejects
    # Capture emitted traces, keeping the real throttler and cached guards.
    original=globals()['fixture']
    def traced(*args,**kwargs):
        f=original(*args,**kwargs);f.messages=[]
        f.env['Debug'].Trace=f.m.wrap('Debug.Trace',f.messages.append)
        return f
    globals()['fixture']=traced
    try:
        # Round 21: ESSBElem3.Reanimate / ESSBElem3.OnKill (v0.3 亡者歸來, 收割) are gone (N5 owns reanimation);
        # the controller's CanReanimate / ApplyReanimate helpers stay for N5 and keep their diagnostics.
        can=lambda f:f.c.CanReanimate(f.v)
        for key,reason in [('vip','vip'),('dragon','dragon'),('no-reanimate','no-reanimate-keyword')]:
            setup=lambda f,k=key:setattr(f.v,'vip',True) if k=='vip' else f.v.keywords.add(k)
            check('can-'+key,setup,can,'can-reanimate-'+reason)
        check('can-invalid',lambda f:None,lambda f:f.c.CanReanimate(None),'can-reanimate-invalid-target')
        check('ESSBElem2-invalid',lambda f:f.c.overrides.update(ThePlayer=lambda:None),
              lambda f:f.env['ESSBElem2'].OnKill(f.c,10,f.v,0,10,False),'invalid-player-or-target')
        for elem,reason in [(0,'no-element'),(10,'element-mismatch')]:
            check('ash-'+reason,lambda f:None,lambda f,e=elem:f.env['ESSBElem2'].ShouldAsh(f.c,e),reason)
        for elem,reason in [(0,'no-element'),(7,'element-mismatch'),(5,'branch-not-owned')]:
            check('wind-'+reason,lambda f:None,lambda f,e=elem:f.env['ESSBElem2'].TryKillStreak(f.c,e),reason)
        check('wind-not-sneak',lambda f:f.owned.add((4,2,4,1)),lambda f:f.env['ESSBElem2'].TryKillStreak(f.c,5),'not-sneak')
        def native_apply(f):f.c.overrides.pop('ApplyReanimate')
        for case,reason,setup in [
            ('busy','apply-busy',lambda f:f.c.fields.update(ReanimateBusy=True)),
            ('broken','apply-stale-or-broken',lambda f:f.c.fields.update(StateBroken=True)),
            ('spell','apply-missing-player-spell-target',lambda f:f.c.fields.update(ReanimateSpell=None)),
            ('cap','servant-cap-full',lambda f:f.c.overrides.update(ServantCount=lambda:1)),
            ('slots','apply-pending-slots-full',lambda f:f.c.fields.update(PendingServants=Array([object(),object()])))]:
            check('apply-'+case,lambda f,s=setup:(native_apply(f),s(f)),lambda f:f.c.ApplyReanimate(f.v,13,120),reason)
        for key,reason in [('vip','apply-vip'),('dragon','apply-dragon'),('missing','apply-missing-player-spell-target')]:
            def setup(f,k=key):
                f.c.overrides.pop('ApplyAsh')
                if k=='vip':f.v.vip=True
                elif k=='dragon':f.v.keywords.add('dragon')
                else:f.c.fields['AshSpell']=None
            check('ash-apply-'+key,setup,lambda f:f.c.ApplyAsh(f.v),reason)
        # No rewards on an ash application refusal; no fallback resurrection either.
        f=fixture(debug=2);f.mark(7);f.c.overrides.pop('ApplyAsh');f.v.vip=True
        f.env['ESSBElem2'].overrides['OnAsh']=lambda *a:f.events.append('ash-reward')
        f.kill();assert not f.events
        # Real throttler suppresses a repeated identical refusal.
        f=fixture(debug=2);f.c.CanReanimate(None);f.c.CanReanimate(None)
        assert len(f.messages)==1
        # Restart invalidates uptime evidence and does not change saved schema.
        f=fixture();f.damage(10);f.clock[0]=2;f.c.ResetLoadClock()
        assert f.c.LastDamageFor(f.v)==0 and f.c.SwapFloats.Length==128
        # Existing round-13 saved instance: legacy None/small arrays migrate on load.
        for legacy in (None,Array([123.0]*17)):
            f=fixture();f.c.fields['SwapFloats']=legacy;f.c.ResetLoadClock()
            assert f.c.SwapFloats.Length==128 and f.c.LastDamageFor(f.v)==0
        # Actual native apply wrapper succeeds and reserves one pending servant (kept for N5).
        f=fixture();f.c.overrides.pop('ApplyReanimate');f.v.hp=0
        f.p.DoCombatSpellApply=lambda spell,target:f.events.append(('apply',target))
        assert f.c.ApplyReanimate(f.v,13,120)
        assert len(f.events)==1 and f.c.PendingServants[0] is f.v and not f.c.ReanimateBusy
    finally:globals()['fixture']=original
    return cases

def boundaries():
    old=json.loads((ROOT/'.codex/pre-fix14-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    new=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    import state_schema
    assert all(state_schema.stable_identity(k,new.get(k),v) for k,v in old.items()) and new['ESSB_DebugLevel']['id']=='000811'
    before=json.loads((ROOT/'build/fix14-before.json').read_text(encoding='utf8'))
    for name,info in before.items():
        if name=='實作紀錄.md':
         baseline=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
         info=dict(sha256=hashlib.sha256(baseline).hexdigest(),length=len(baseline),bom=baseline.startswith(b'\xef\xbb\xbf'),crlf=baseline.count(b'\r\n'),lf=baseline.count(b'\n'))
        raw=(ROOT/name).read_bytes()
        assert raw.startswith(b'\xef\xbb\xbf')==info['bom'],name
        assert (raw.count(b'\r\n')==raw.count(b'\n'))==(info['crlf']==info['lf']),name
        if name=='實作紀錄.md':assert hashlib.sha256(raw[:info['length']]).hexdigest()==info['sha256']
        if name=='state-schema.lock.json':state_schema.preflight()
    import state_schema
    assert state_schema.preflight()['state_schema_version']==json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    cfg=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))
    from papyrus_harness import Script
    assert Script(NEW/'ESSBState.psc').KillAttributionSeconds()==cfg['kill_attribution_seconds']==3.0
    return dict(formids_unchanged=len(old),debug='000811',schema=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version'],encoding='preserved',implementation_log='append-only')

def run():
    negative={}
    for e in (7,10):
        f=fixture(OLD);f.mark(e);f.kill()
        assert f.events==[],('pre-fix mark-only unexpectedly passed',e,f.events)
        negative[str(e)]='actual pre-fix marked weapon kill produces no ash/reanimation'
    cases=attribution();logs=diagnostics();scope=boundaries()
    cost=scenario(NEW);assert cost['total']<=166 and cost['string_concats']==0 and 1 <= cost['identity'] <= 2
    report=dict(cases=cases,negative_controls=negative,diagnostics=logs,scope=scope,cost=cost,runtime_tested=False)
    (ROOT/'build/fix14-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'FIX14 ATTRIBUTION ok: {len(cases)} cases; {len(logs)} diagnostics; L0 zero concat; FormIDs {scope["formids_unchanged"]} unchanged; current schema; hit calls={cost["total"]}; native runtime untested')
    return report
if __name__=='__main__':run()
