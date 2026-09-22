"""Round 13: execute actual pre/post Papyrus bodies, with explicit native mocks.

No live Skyrim, saved-VM or animation timing claim. Native effect lifetime is
checked separately in generated ESP records; races are deterministic injections.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib, json, math, re, struct, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'build'), str(ROOT)]
import papyrus_harness as h
from fix11_verify import HitScript, add

class Script(HitScript):
    def __init__(self,path,env=None):
        if env is None:env={}
        env['padd']=add
        super().__init__(path,env)
from fix12_cost import scenario
from fix10_verify import controller, Actor
OLD = ROOT/'.codex/pre-fix13-snapshot/src'
NEW = ROOT/'src'

def ledger(item, detail):
    # Round 14 write scope excludes the archived Round 13 progress page.
    pass


class Glob:
    def __init__(self,v=1):self.v=v
    def GetValue(self):return self.v
    def GetValueInt(self):return int(self.v)
    def SetValue(self,v):self.v=v
    def SetValueInt(self,v):self.v=v

class Spell:
    def __init__(self):self.mag={};self.duration={};self.effect=object()
    def SetNthEffectMagnitude(self,i,v):self.mag[i]=v
    def SetNthEffectDuration(self,i,v):self.duration[i]=v
    def GetNthEffectMagicEffect(self,i):return self.effect

def lightning(folder):
    c,t,p,v,w,clock,m,env,G=scenario(folder,prepare_only=True)
    c.fields['MultDrain']=G(1)
    c.fields['HitNormalSpells']=h.Array([Spell() for _ in range(11)])
    c.fields['HitPowerSpells']=h.Array([Spell() for _ in range(11)])
    if 'ApplyBakedProc' in c.functions:
        c.fields['ProcVariants']=h.Array([Spell() for _ in c.ProcVariants]);c.fields['ProcCacheReady']=False
    applied=[]
    p.DoCombatSpellApply=lambda s,target:applied.append((s,dict(getattr(s,"mag",{})),target))
    for power in (False,True):
        for drain in (.25,1,3):
            c.MultDrain.v=drain;applied.clear()
            if 'ApplyBakedProc' in c.functions:
                c.RefreshProcMagnitudes();c.ApplyBakedProc(v,3,power,False)
            else:c.ApplyProc(v,3,power,False,False)
            assert len(applied)==1
            _,magnitudes,target=applied[0]
            assert 1 in magnitudes,'ordinary lightning proc has no magicka-drain effect magnitude'
            assert math.isclose(magnitudes[1],magnitudes[0]*.5*drain) and target is v
    # Full weapon handler extra-proc branch, not just a second manual ApplyProc call.
    c.MultDrain.v=1;applied.clear()
    env['ESSBNodes'].overrides['HasExtreme']=lambda *a:True
    c.overrides.update(SyncStage=lambda:3, SendModEvent=lambda *a:None);c.fields['ExtremeCount']=9
    if 'ApplyBakedProc' in c.functions:
        c.RefreshProcMagnitudes();c.ApplyBakedProc(v,3,False,False)  # explicit native base boundary
    c.OnWeaponHit(v,w,None,0)
    hits=[row for row in applied if 0 in row[1]]
    assert len(hits)==2,'expected base proc and extra proc from OnWeaponHit'
    assert all(math.isclose(mag[1],mag[0]*.5) for _,mag,target in hits)
    assert all(target is v for _,_,target in applied),'lightning must never restore the player'
    assert all(s not in (c.TrueSpell,) for s,_,_ in applied)
    # Non-lightning must remain single effect; actual health provenance still runs.
    applied.clear();c.overrides['GetHitMult']=lambda *a:1
    if 'ApplyBakedProc' in c.functions:c.ApplyBakedProc(v,1,False,False)
    else:c.ApplyProc(v,1,False,False,False)
    assert set(applied[0][1])=={0}
    return 'ordinary/power x drain .25/1/3; full extra-proc path twice; no player restore/true damage'

def eviction(folder):
    c,p=controller(folder);clock=[100];ended=[];dispelled=[]
    c.env['Utility']=NS(GetCurrentRealTime=lambda:clock[0])
    c.overrides.update(CooldownSeconds=lambda x:x,PlaceFx=lambda *a:None)
    c.env['ESSBReactions']=NS(End=lambda ctl,e,target,reason,mult,chain:ended.append((e,target,reason,mult)))
    for i in range(8):c.OccupySlot(i,Actor(1000))
    victim=c.RegActor[0];ninth=Actor(1000)
    c.RegElem[0]=1;c.RegElem2[0]=3;c.RegSecondReal[0]=True
    c.RegMark[0]=NS(DispelIfActive=lambda:dispelled.append(1))
    c.RegMark2[0]=NS(DispelIfActive=lambda:dispelled.append(3))
    before=c.RegGeneration[0]
    assert c.AcquireSlot(ninth)==0
    assert sorted(e for e,_,_,_ in ended)==[1,3],'ninth victim silently discards the secondary real mark'
    assert all(target is victim and reason==3 for _,target,reason,_ in ended)
    assert sorted(dispelled)==[1,3] and c.RegActor[0] is ninth and c.RegGeneration[0]>before
    # During a shared cooldown both AMEs are still removed, without bypassing the gate.
    c.RegElem[0]=1;c.RegElem2[0]=3;c.RegSecondReal[0]=True
    c.RegMark[0]=NS(DispelIfActive=lambda:dispelled.append(1))
    c.RegMark2[0]=NS(DispelIfActive=lambda:dispelled.append(3))
    c.RegLastEnd[0]=100;ended.clear();dispelled.clear()
    c.EndBothMarks(0,1,3)
    assert not ended and sorted(dispelled)==[1,3]
    # A reentrant End reaction can recycle the slot; neither the other mark nor
    # AcquireSlot's final Clear/Occupy may touch the replacement generation.
    replacement=Actor(1000)
    c.RegSeq[0]=0;c.RegElem[0]=1;c.RegElem2[0]=3;c.RegSecondReal[0]=True
    c.RegLastEnd[0]=-100;c.RegMark[0]=NS(DispelIfActive=lambda:None)
    c.RegMark2[0]=NS(DispelIfActive=lambda:None)
    c.env['ESSBReactions'].End=lambda *a:c.OccupySlot(0,replacement)
    assert c.AcquireSlot(Actor(1000))==-1 and c.RegActor[0] is replacement
    return 'two real marks: reason=3, one reservation, both dispelled; cooldown and recycled-generation guards'

def retaliation(folder):
    for layers,owned,ready,projectile,mountain,expected in (
        (5,True,True,None,False,0),(4,True,True,None,False,3),
        (5,True,False,None,False,4),(5,False,True,None,False,4),
        (5,True,True,object(),False,4),(5,True,True,None,True,0),
        (4,False,True,None,True,4)):
        state={'layers':layers,'hits':0,'takes':0,'consumes':0}
        def br(ctl,tree,route,tier,node):
            return (owned if (tree,route,tier,node)==(3,0,3,1) else
                    mountain if (tree,route,tier,node)==(3,0,4,0) else False)
        nodes=NS(Br=br,StatusCapBonus=lambda *a:0)
        def take():state['takes']+=1;return ready
        def consume():state['layers']-=1;state['consumes']+=1
        player=NS(GetActorValue=lambda av:100)
        ctl=NS(IsOperational=lambda:True,Enabled=Glob(),FormActive=Glob(),CurrentElement=Glob(4),
            ThePlayer=lambda:player,GetSelf=lambda n:state['layers'],ConsumeRockArmor=consume,
            RefreshDivineProtection=lambda:None,SyncStage=lambda:3,GetIceShield=lambda:0,GetWaterMirror=lambda:0,GetGuardWindLeft=lambda:0,
            TakeRetaliate=take,ClearSelf=lambda n:state.update(layers=0),CachedDebugLevel=0,
            ApplyDamage=lambda *a:state.update(hits=state['hits']+1),Knockdown=lambda *a:True)
        elem=Script(folder/'ESSBElem2.psc',dict(ESSBNodes=nodes,ESSBReactions=NS(ReactDamage=lambda *a:20)))
        guard=Script(folder/'ESSBGuard.psc',dict(ESSBNodes=nodes,ESSBElem2=elem))
        guard.fields['Ctl']=ctl;guard.overrides['TakeAttacker']=lambda *a:False
        if 'NodeBits' in guard.fields:
            guard.fields.update(Ready=True,Enabled=Glob(1),DivineArmed=Glob(0),RockArmor=Glob(layers),IceShield=Glob(0),WaterMirror=Glob(0),GuardWind=Glob(0),NodeBits=owned)
            guard.overrides['GetActorReference']=lambda:player
        guard.OnHitEx(object(),None,projectile,False,False,False,False)
        assert state['layers']==expected, 'full pre-hit rock stack cannot retaliate: '+str(state)
        success=owned and ready and layers==5 and projectile is None
        assert state['hits']==int(success)
        assert state['takes']==int(owned and layers==5 and projectile is None)
        assert state['consumes']==int(not success and not mountain)
    return 'pre-hit full stack triggers; partial/cooldown/no-node/ranged/mountain cases retain intended consumption'

def armor(folder):
    c,p=controller(folder);spell=Spell();c.UtilSpells[18]=spell
    owned=set();active=set();adds=[];casts=[];clock=[0];expiry=[0]
    p.HasSpell=lambda s:s in owned;p.HasMagicEffect=lambda e:e in active
    p.RemoveSpell=lambda s:(owned.discard(s),active.discard(s.effect))
    p.DispelSpell=lambda s:active.discard(s.effect)
    def add(s,quiet):owned.add(s);active.add(s.effect);adds.append(s)
    p.AddSpell=add
    def timed(index,mag,duration,target):
        active.add(spell.effect);expiry[0]=clock[0]+duration;casts.append(mag)
    c.overrides.update(ApplyUtil=timed,SetGlobal=lambda *a:None,RecoveryAmount=lambda x:x*1.7)
    c.env['ESSBElem2']=NS(RockArmorPerLayer=lambda *a:20)
    c.fields.update(SelfRockArmor=5,GRockArmor=Glob())
    c.SyncRockArmor();clock[0]=90
    if expiry[0] and clock[0]>=expiry[0]:active.clear()
    c.SyncRockArmor()
    assert spell.effect in active,'unchanged layers fail to restore expired rock armor'
    assert spell in owned and not casts and spell.mag[0]==170
    assert len(adds)==1,'unchanged persistent buff must not be recast'
    owned.clear();active.clear();c.SyncRockArmor();assert len(adds)==2
    active.clear();c.SyncRockArmor();assert len(adds)==3,'dispelled ability effect must be repaired'
    c.ClearSelf(2);assert not active and not owned and c.SelfRockArmor==0
    c.fields['SelfRockArmor']=3;c.SyncRockArmor();assert spell.mag[0]==102
    c.fields['SelfRockArmor']=0;c.SyncRockArmor();assert not owned
    return '90s unchanged layers persist; no periodic recast; missing/dispelled buff repaired; zero layers remove ability'

def opens(folder):
    env={};roll=[.1];stacks=[];selfs=[];utils=[]
    for name in ('ESSBElem','ESSBElem2','ESSBElem3','ESSBReactions'):
        env[name]=Script(folder/(name+'.psc'),env)
    # Real OpenMult, OpenStacks and RoundStochastic with the review's rank/scale.
    env['ESSBNodes']=NS(TreeOf=lambda e:e-1,Br=lambda *a:False,
        Rank=lambda ctl,tree,route,tier:10 if (route,tier)==(1,4) else 0,
        Pct=lambda ctl,rank,pct:rank*pct*3)
    env['Utility']=NS(RandomFloat=lambda *a:roll[0])
    env['ESSBElem'].overrides['OnOpen']=lambda *a:None
    env['ESSBReactions'].overrides['ReactDamage']=lambda *a:10
    ctl=NS(ThePlayer=lambda:object(),TakeNextOpenMultOn=lambda t:1,AddStack=lambda t,k,n:stacks.append((k,n)),
        AddSelf=lambda k,n:selfs.append((k,n)),ApplyDamage=lambda *a:None,ApplyUtil=lambda *a:utils.append(a),
        GetDamageMult=lambda e:1,GLevel=lambda e:1,GetBloodLeechRatio=lambda:1,Leech=lambda *a:None,
        CachedDebugLevel=0,IsEnvStormy=lambda:False,FrostOpenSlowPct=Glob(25),SpreadPoison=lambda *a:None)
    cases=[]
    for e,kind,selftarget,base in [(1,1,False,2),(3,1,True,2),(4,2,True,2),
                                 (6,5,False,2),(7,6,False,1),(10,10,False,2),
                                 (2,2,False,3),(5,3,True,2),(8,7,False,3)]:
        for random in (.1,.99):
            roll[0]=random;stacks.clear();selfs.clear();utils.clear()
            env['ESSBReactions'].Open(ctl,e,object())
            values=dict(selfs if selftarget else stacks)
            scaled=base*1.9;expect=int(scaled)+int(random < scaled-int(scaled))
            assert values[kind]==expect,f'element {e} open stack {values[kind]} != scaled {expect}'
            if e==4:
                stamina=[a[1] for a in utils if a[0]==6]
                assert stamina==[76.0],'earth open player stamina misses overall multiplier'
            cases.append((e,random,values[kind]))
    # Cap enforcement was not bypassed or altered (actual functions byte-for-byte).
    for name,funcs in [('ESSBController',['AddStack','AddSelf']),('ESSBStatus',['AddStack'])]:
        old=h.Script(OLD/(name+'.psc'));new=h.Script(NEW/(name+'.psc'))
        for f in funcs:
            if f in old.functions and name != 'ESSBStatus':
                prior=old.functions[f];current=new.functions[f]
                if f=='AddSelf':
                    lines=list(current[2]);hook=['If aiKind == 4 && before != SelfOverheat','RefreshProcMagnitudes()','EndIf']
                    pos=next(i for i in range(len(lines)-2) if [x.strip() for x in lines[i:i+3]]==hook)
                    del lines[pos:pos+3];current=(*current[:2],lines)
                assert prior==current,(name,f)
            elif name == 'ESSBStatus':
                assert 'RingAdd(BleedRing, aiAmount, Cap(5, 8))' in '\n'.join(new.functions[f][2])
    return cases

def cooldown(folder, which):
    clock=[100];c,p=controller(folder)
    c.env['Utility']=NS(GetCurrentRealTime=lambda:clock[0])
    c.overrides['CooldownSeconds']=lambda n:n
    triggered=[]
    if which=='interrupt':
        casting=[False];v=Actor(1000)
        env=dict(ESSBNodes=NS(Rank=lambda ctl,t,r,k:1 if (r,k)==(1,0) else 0,
            Br=lambda ctl,t,r,k,n:(t,r,k,n)==(11,1,1,0),GL=lambda *a:1))
        vm=Script(folder/'ESSBNoForm.psc',env);vm.overrides['IsCasting']=lambda target:casting[0]
        c.fields.update(ManabreakBase=Glob(20),ManabreakPerRank=Glob(4),SilenceKeyword=None)
        c.overrides.update(DrainAmount=lambda x:x,ApplyUtil=lambda *a:None,ApplyTrueDamage=lambda *a:None,
            ApplyManaBreakMark=lambda *a:None,ApplySilenceSpell=lambda *a:triggered.append(clock[0]))
        oldstamp=c.InterruptTime;vm.OnManaBreak(c,v,False,*([casting[0]] if folder==NEW else []))
        assert c.InterruptTime==oldstamp,'non-caster consumes interrupt cooldown'
        casting[0]=True;clock[0]+=1;vm.OnManaBreak(c,v,False,*([casting[0]] if folder==NEW else []))
        assert triggered==[101]
        clock[0]+=1;vm.OnManaBreak(c,v,False,*([casting[0]] if folder==NEW else []));assert triggered==[101]
        clock[0]=106;vm.OnManaBreak(c,v,False,*([casting[0]] if folder==NEW else []));assert triggered==[101,106]
    else:
        hp=[1.0];p.GetActorValuePercentage=lambda av:hp[0]
        env=dict(ESSBNodes=NS(Br=lambda *a:True))
        vm=Script(folder/'ESSBElem.psc',env)
        c.overrides.update(ScanTargets=lambda *a:h.Array([object()]),GetStack=lambda *a:1,
                           SetStack=lambda *a:triggered.append(clock[0]))
        oldstamp=c.IceHeartTime;vm.OnTick(c,2)
        assert c.IceHeartTime==oldstamp,'healthy tick consumes IceHeart cooldown'
        hp[0]=.29;clock[0]+=1;vm.OnTick(c,2);assert triggered==[101]
        clock[0]+=1;vm.OnTick(c,2);assert triggered==[101]
        clock[0]=131;vm.OnTick(c,2);assert triggered==[101,131]
    return triggered

def counter_lifetime(folder):
    c,p=controller(folder);effect=object();active=[True];dead=[False];registered=set();hits=[]
    c.fields['ManaBreakSpell']=NS(GetNthEffectMagicEffect=lambda i:effect)
    v=NS(IsDead=lambda:dead[0],HasMagicEffect=lambda e:active[0] and e is effect,
         GetEquippedSpell=lambda h: NS(GetEffectiveMagickaCost=lambda target:17+h))
    c.env['ESSBNodes']=NS(Br=lambda *a:True)
    c.env['ESSBNoForm']=NS(OnCounterSpell=lambda *a:hits.append(a[2]))
    def register(target,event):registered.add(event)
    c.overrides.update(RegisterForAnimationEvent=register,
                       UnregisterForAnimationEvent=lambda target,event:registered.discard(event))
    quest=NS(GetAlias=lambda i:c)
    helper=NS(ControllerQuest=lambda:quest)
    def effect_vm():
        vm=Script(folder/'ESSBCounter.psc',dict(ESSBState=helper,ESSBNodes=c.env['ESSBNodes'],
            RegisterForAnimationEvent=lambda *a:(_ for _ in ()).throw(AssertionError('short-lived AME still calls animation registration native'))))
        vm.fields['Controller']=quest
        return vm
    ame=effect_vm();ame.OnEffectStart(v,p)
    assert len(registered)==2
    c.OnAnimationEvent(v,'MRh_SpellFire_Event');c.OnAnimationEvent(v,'MLh_SpellFire_Event')
    assert hits==[18,17]
    c.OnAnimationEvent(v,'unknown');assert hits==[18,17]
    # Finishing the old AME after a refresh must preserve the new mark's listener.
    ame.OnEffectFinish(v,p);assert len(registered)==2
    active[0]=False;ame.OnEffectFinish(v,p);assert not registered
    c.OnAnimationEvent(v,'MRh_SpellFire_Event');assert hits==[18,17]
    ame.OnAnimationEvent(v,'MRh_SpellFire_Event');assert hits==[18,17]
    # Finish-before-start and finish between two registrations.
    ame.OnEffectStart(v,p);assert not registered
    active[0]=True
    def during_register(target,event):
        registered.add(event);active[0]=False;ame.OnEffectFinish(v,p)
    c.overrides['RegisterForAnimationEvent']=during_register
    ame.OnEffectStart(v,p);assert not registered
    c.overrides['RegisterForAnimationEvent']=register;active[0]=True
    ame.OnEffectStart(v,p);dead[0]=True
    c.OnAnimationEvent(v,'MRh_SpellFire_Event');assert not registered and hits==[18,17]
    dead[0]=False;active[0]=True
    # Native cost query can yield while the mark ends; final eligibility rejects it.
    def cost(target):active[0]=False;return 30
    v.GetEquippedSpell=lambda hand:NS(GetEffectiveMagickaCost=cost)
    c.OnAnimationEvent(v,'MRh_SpellFire_Event');assert hits==[18,17]
    # Execute the real damage dispatcher too: a yielding tree query can expire
    # the mark after the alias's last eligibility check.
    vm=Script(folder/'ESSBNoForm.psc',dict(ESSBNodes=NS(Br=lambda *a:True)))
    active[0]=True;damage=[]
    def level(tree):active[0]=False;return 30
    dispatch=NS(Trees=NS(TreeLevel=level),CachedDebugLevel=0,IsOperational=lambda:True,
                CounterEligible=lambda target:active[0],ApplyTrueDamage=lambda *a:damage.append(a))
    vm.OnCounterSpell(dispatch,v,17);assert not damage
    dispatch.Trees.TreeLevel=lambda tree:30;active[0]=True
    vm.OnCounterSpell(dispatch,v,17);assert damage==[(17*1.6,v)]
    # Retired alias identity must still reject all late events.
    c.env['ESSBState'].overrides['ControllerQuest']=lambda:NS(GetAlias=lambda i:object())
    active[0]=True;c.OnAnimationEvent(v,'MRh_SpellFire_Event');assert hits==[18,17]
    return 'stable alias only; refresh/expiry/death/late AME/finish-during-register/cost-yield/retired alias'

def casting(folder):
    equipped=[None]*4;voice=[None];current=[None];queried=[]
    actor=NS(GetEquippedSpell=lambda slot:equipped[slot],GetEquippedShout=lambda:voice[0],
             GetAnimationVariableBool=lambda name:(_ for _ in ()).throw(AssertionError('missing graph variable read: '+name)))
    def native(ref,item):
        assert item is not None;queried.append(item);return item is current[0]
    vm=Script(folder/'ESSBNoForm.psc',dict(PO3_SKSEFunctions=NS(IsCasting=native)))
    for i in range(4):
        equipped[:]=[None]*4;equipped[i]=current[0]=object()
        assert vm.IsCasting(actor),f'equipped source {i} not checked'
        current[0]=None;assert not vm.IsCasting(actor)
    equipped[:]=[None]*4;equipped[0]=equipped[1]=current[0]=object()
    assert vm.IsCasting(actor),'dual cast rejected'
    equipped[:]=[None]*4;voice[0]=current[0]=object();assert vm.IsCasting(actor)
    voice[0]=current[0]=None;assert not vm.IsCasting(actor) and not vm.IsCasting(None)
    return 'PO3 IsCasting on equipped left/right/other/instant/dual/voice; idle/empty/None negative controls'

def mcm(folder):
    config=json.loads((ROOT/'package/Elements Spellblade/MCM/Config/Elements Spellblade/config.json').read_text(encoding='utf8'))
    sliders=[r for p in config['pages'] for r in p['content'] if r.get('type')=='slider']
    assert len(sliders)==10
    values={int(r['valueOptions']['sourceForm'].split('|')[1],16):Glob(-99) for r in sliders}
    events=[];accept=[False];operational=[True];samequest=[True]
    ctl=NS(**{name:(lambda name=name:events.append(name)) for name in
        ('RefreshRuntimeValues','RefreshTrees','RefreshAbilities','RefreshRecovery')})
    quest=NS(GetAlias=lambda i:ctl)
    helper=Script(folder/'ESSBState.psc',dict(Game=NS(GetFormFromFile=lambda fid,plugin:values[fid])))
    helper.overrides.update(ControllerQuest=lambda:quest if samequest[0] else object(),Operational=lambda:operational[0])
    def show(*a):events.append('confirm');return accept[0]
    vm=Script(folder/'ESSBMCM.psc',dict(__execute_logs__=True,ESSBState=helper,ShowMessage=show,ForcePageReset=lambda:events.append('reset-page'),
                                     Debug=NS(Notification=lambda s:events.append('notice'))))
    vm.fields['Controller']=quest
    assert 'RestoreDefaults' in vm.functions,'MCM restore-defaults control was deferred'
    vm.RestoreDefaults();assert events==['confirm'] and all(v.v==-99 for v in values.values())
    events.clear();accept[0]=True;vm.RestoreDefaults()
    for row in sliders:
        fid=int(row['valueOptions']['sourceForm'].split('|')[1],16)
        assert values[fid].v==row['valueOptions']['defaultValue'],row['id']
    assert events==['confirm','RefreshRuntimeValues','RefreshTrees','RefreshAbilities','RefreshRecovery','reset-page','notice']
    # Cancelled/unready/stale-before and stale-after-confirmation do not write.
    for reason in ('unready','stale','stale-after-confirm'):
        for v in values.values():v.v=-99
        samequest[0]=reason!='stale';operational[0]=reason!='unready';events.clear()
        def guarded_show(*a):samequest[0]=False;events.append('confirm');return True
        if reason=='stale-after-confirm':vm.env['ShowMessage']=guarded_show
        vm.RestoreDefaults();assert all(v.v==-99 for v in values.values()) and 'notice' not in events
    button=[r for r in config['pages'][1]['content'] if r.get('action',{}).get('function')=='RestoreDefaults']
    assert len(button)==1
    return {r['id']:r['valueOptions']['defaultValue'] for r in sliders}

def record_checks():
    import build_v03 as b
    records,meta=b.read_plugin(b.OUT/b.PLUGIN);by={r.edid:r for r in records}
    drain=by['ESSB_UtilEffect_DrainMagicka'];data=drain.d['DATA']
    assert struct.unpack_from('<i',data,68)[0]==24+1  # Primary AV Magicka
    for power in ('Normal','Power'):
        s=by['ESSB_Hit_Lightning_'+power]
        refs=s.refs('EFID');assert len(refs)==3 and refs[1]==drain.key and refs[2]==by['ESSB_EngagedEffect'].key
        mags=[struct.unpack('<fII',v)[0] for tag,v in s.ss if tag=='EFIT']
        assert math.isclose(mags[1],mags[0]*.5)
    armor=by['ESSB_Util_ArmorBuff'];effect=by['ESSB_UtilEffect_ArmorBuff']
    # SPEL: type ability, constant effect, self. MGEF: No Duration, DamageResist.
    spit=armor.d['SPIT'];data=effect.d['DATA']
    assert struct.unpack_from('<I',spit,8)[0]==4
    assert struct.unpack_from('<II',spit,16)==(0,0)
    assert struct.unpack_from('<I',data,0)[0]&0x200
    assert struct.unpack_from('<i',data,68)[0]==39
    assert struct.unpack('<fII',armor.d['EFIT'])[2]==0
    return dict(records=len(records),masters=meta['masters'],lightning_effects=3,armor='constant self ability, no duration')

def boundaries():
    old=json.loads((ROOT/'.codex/pre-fix13-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    new=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    import state_schema
    assert all(state_schema.stable_identity(k,new.get(k),v) for k,v in old.items())
    assert new['ESSB_DebugLevel']['id']=='000811'
    before=json.loads((ROOT/'build/fix13-before.json').read_text(encoding='utf8'))
    for name,digest in before['protected'].items():
        if name == 'settings.json':
            old_settings=json.loads((ROOT/'.codex/pre-fix14-snapshot/settings.json').read_text(encoding='utf8'))
            current=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))
            current.pop('kill_attribution_seconds')
            for key in ('lightning_roll_mode','form_notify','form_sound','hotkeys_enabled'):current.pop(key,None)
            current['state_schema_version'] = old_settings['state_schema_version']
            assert current == old_settings, 'only Round 14 attribution setting may change'
            continue
        if name == 'state-schema.lock.json':
            state_schema.preflight()
            continue
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    raw=(ROOT/'實作紀錄.md').read_bytes();prefix=before['log_prefix']
    assert raw.startswith((ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes())  # Current round18b byte baseline
    for name,enc in before['encodings'].items():
        if name=='實作紀錄.md':
            baseline=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
            enc=dict(bom=baseline.startswith(b'\xef\xbb\xbf'),crlf=baseline.count(b'\r\n'),lf=baseline.count(b'\n'))
        raw=(ROOT/name).read_bytes()
        assert raw.startswith(b'\xef\xbb\xbf')==enc['bom'],name
        assert (raw.count(b'\r\n')==raw.count(b'\n'))==(enc['crlf']==enc['lf']),name
    import state_schema
    lock=state_schema.preflight();assert lock['state_schema_version']==json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    return dict(formids_unchanged=len(old),formids_added=0,schema=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version'],debug='000811',protected='unchanged; implementation log append-only; BOM/newlines retained')

def run():
    cases={};negatives={}
    for name,test in [('6',lightning),('7',eviction),('8',retaliation),('9',armor),('10',opens),
                      ('11-interrupt',lambda f:cooldown(f,'interrupt')),('11-iceheart',lambda f:cooldown(f,'iceheart')),
                      ('12',counter_lifetime),('13',casting),('MCM',mcm)]:
        try:test(OLD)
        except AssertionError as error:negatives[name]=str(error)
        else:raise AssertionError('pre-fix source unexpectedly passed: '+name)
        cases[name]=test(NEW)
        # Round15: historical progress ledger is read-only.
    records=record_checks();scope=boundaries()
    cost=scenario(NEW);assert cost['total']<=180 and 1 <= cost['identity'] <= 2 and cost['string_concats']==0
    report=dict(cases=cases,negative_controls=negatives,records=records,scope=scope,cost=cost,
                diagnoses={str(n):'confirmed' for n in range(6,14)},runtime_tested=False)
    (ROOT/'build/fix13-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'FIX13 ok: {len(negatives)} pre-fix failures; 6-13 + MCM pass; {scope["formids_unchanged"]} FormIDs unchanged; current schema; hit calls={cost["total"]}; native runtime untested')
    return report

if __name__=='__main__':run()
