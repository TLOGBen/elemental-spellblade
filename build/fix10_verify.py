"""FIX10 actual-source regressions; native Skyrim delivery is explicitly mocked.

Every defect is exercised against both the immutable pre-fix10 sources/ESP and
the generated result. This is not an in-game or Papyrus scheduling emulator.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import collections, hashlib, json, re, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'build'))
from papyrus_harness import Script, Array

class Glob:
    def __init__(self, v=0): self.v=v
    def GetValue(self): return self.v
    def GetValueInt(self): return int(self.v)
    def SetValueInt(self,v): self.v=v

class Actor:
    def __init__(self, hp=100): self.hp=hp; self.hits=[]
    def IsPlayerTeammate(self): return False
    def IsCommandedActor(self): return False
    def IsDead(self): return self.hp <= 0
    def GetActorValue(self, av): return self.hp if av=='Health' else 100
    def GetActorValueMax(self, av): return 100
    def GetActorValuePercentage(self, av): return self.GetActorValue(av)/100
    def GetFormID(self): return id(self)
    def DoCombatSpellApply(self, spell, target):
        target.hits.append(spell); target.hp -= spell.mag

class Spell:
    def __init__(self): self.mag=0
    def SetNthEffectMagnitude(self, i, value): self.mag=value
    def SetNthEffectDuration(self, i, value): pass

def controller(folder, current=None):
    player=Actor()
    helper=Script(ROOT/'src/ESSBState.psc')
    c=Script(folder/'ESSBController.psc',dict(ESSBState=helper,Utility=NS(GetCurrentRealTime=lambda:100.0)))
    helper.overrides['ControllerQuest']=lambda:NS(GetAlias=lambda i:current or c)
    # Init real arrays; Ready represents a serialized running instance.
    c.InitRegistry(); c.fields['Ready']=True
    c.fields.update(PlayerRef=player,CurrentElement=Glob(10),FormActive=Glob(1),
                    BaseDamageMult=Glob(1),MultDot=Glob(1),
                    HitNormalSpells=Array([Spell() for _ in range(11)]),
                    HitPowerSpells=Array([Spell() for _ in range(11)]),
                    ReactSpells=Array([Spell() for _ in range(11)]),TrueSpell=Spell(),
                    UtilSpells=Array([Spell() for _ in range(28)]),UtilTargetSpells=Array([]))
    c.overrides.update(GLevel=lambda t:1,GetHitMult=lambda *a:1,SyncStage=lambda:0)
    c.env['ESSBReactions']=NS(RollBase=lambda *a:150)
    c.env['ESSBNodes']=NS(TreeOf=lambda e:e-1,Br=lambda *a:False)
    if 'ApplyBakedProc' in c.functions:
        c.fields.update(ProcCacheReady=True,ProcVariants=Array([Spell()]),ProcElements=Array([10]),
                        ProcPowers=Array([0]),ProcSneaks=Array([0]),ProcBloodBands=Array([0]))
        c.ProcVariants[0].mag=150
    return c,player

def ash(c, killing):
    e=Script(c.path.parent/'ESSBElem2.psc',dict(ESSBNodes=NS(Br=lambda *a:False)))
    return e.ShouldAsh(c,killing)

def killing(c,target):
    return c.LastDamageFor(target) if 'LastDamageFor' in c.functions else c.LastDamageElement

def regression_a(folder):
    c,p=controller(folder)
    holy,dark=Actor(),Actor()
    c.ApplyDamageRaw(7,150,holy)
    assert ash(c,killing(c,holy)), 'divine lethal positive control'
    if 'ApplyBakedProc' in c.functions:
        c.NoteDamageElement(dark,10);c.ApplyBakedProc(dark,10,False,False)
    else:c.ApplyProc(dark,10,False,False,False)
    assert not ash(c,killing(c,dark)), 'another victim inherited divine damage'
    assert killing(c,dark)==10, 'darkness proc missing victim provenance'
    # A nonlethal holy hit must not tag a later physical kill of this same actor.
    physical=Actor(1000);c.ApplyDamageRaw(7,20,physical);physical.hp=0
    # Round 14 approved rule retains recent nonlethal damage for physical kills.
    if 'KillElementFor' in c.functions:
        assert ash(c,killing(c,physical)), 'recent holy damage lost on physical kill'
    else:
        assert not ash(c,killing(c,physical)), 'nonlethal holy hit tagged physical kill'
    # True and bleed damage replace the attribution. Already-dead targets cannot overwrite it.
    true=Actor(); c.ApplyDamageRaw(7,20,true);c.ApplyTrackedDamage(p,c.TrueSpell,true,0)
    c.TrueSpell.mag=150;c.ApplyTrackedDamage(p,c.TrueSpell,true,0)
    assert killing(c,true)==0 and not ash(c,killing(c,true))
    bleed=Actor();c.ApplyDamageRaw(7,20,bleed);c.ApplyUtil(7,150,0,bleed,True)
    assert killing(c,bleed)==6
    c.ApplyDamageRaw(7,150,bleed); assert killing(c,bleed)==6
    # 8 slotted victims plus unslotted targets, promotion, eviction, and status cleanup.
    for i in range(8):
        target=Actor();c.OccupySlot(i,target);c.ApplyDamageRaw(7 if i%2 else 10,150,target)
        assert killing(c,target)==(7 if i%2 else 10)
    slotted=c.RegActor[2]
    c.ClearSlot(2);assert killing(c,slotted)==10
    c.OccupySlot(2,slotted);assert killing(c,slotted)==10
    replacement=Actor();c.ClearSlot(2);c.OccupySlot(2,replacement)
    assert killing(c,replacement)==0 and killing(c,slotted)==10
    # No active-form substitution: close/switch the form after the lethal damage.
    c.CurrentElement.v=7;assert killing(c,dark)==10
    c.CurrentElement.v=10;assert killing(c,holy)==7
    received=[]
    c.env.update(ESSBElem=NS(OnKill=lambda *a:c.ApplyDamageRaw(7,150,Actor())),
                 ESSBElem2=NS(ShouldAsh=lambda *a:False,OnKill=lambda *a:received.append(a[4])),
                 ESSBElem3=NS(OnKill=lambda *a:received.append(a[4])),
                 ESSBNoForm=NS(OnKill=lambda *a:None,IsSpellUser=lambda *a:False))
    c.OnKillEvent(dark,p)
    assert received==[10,10], 'on-kill AoE changed frozen victim attribution'
    # Pure Land is the sole explicit exception; ownership + actual active divine form + stage 3.
    e=Script(folder/'ESSBElem2.psc',dict(ESSBNodes=NS(Br=lambda *a:True)))
    c.overrides['SyncStage']=lambda:3
    assert not e.ShouldAsh(c,10)
    c.CurrentElement.v=7;assert e.ShouldAsh(c,10)
    c.FormActive.v=0;assert not e.ShouldAsh(c,10)
    # Confirm all actual health delivery sites route through the wrapper.
    source=c.path.read_text(encoding='utf8')
    for fn in ('ApplyProc','ApplyDamageRaw','ApplyTrueDamage','Execute','ApplyUtil'):
        assert any('ApplyTrackedDamage(' in line for line in c.functions[fn][2]),fn
    assert 'Int LastDamageElement' not in source
    assert not re.search(r'NoteDamageElement\(\d', '\n'.join(p.read_text(encoding='utf8') for p in folder.glob('*.psc')))
    return 'cross-target, nonlethal, true, bleed, dead overwrite, slot reuse/eviction, form changes, Pure Land'

def regression_b(folder):
    current,p=controller(folder)
    # Both controllers have fully valid arrays, modeling old saved initialized state.
    old,_=controller(folder);old.env['ESSBState'].overrides['ControllerQuest']=lambda:NS(GetAlias=lambda i:current)
    old.fields['PlayerRef']=p
    effects=collections.Counter()
    def wire(c):
        c.env.update(ESSBElem=NS(OnKill=lambda *a:effects.update(['elem'])),
                     ESSBElem2=NS(ShouldAsh=lambda *a:False,OnKill=lambda *a:effects.update(['elem2'])),
                     ESSBElem3=NS(OnKill=lambda *a:effects.update(['elem3'])),
                     ESSBNoForm=NS(OnKill=lambda *a:effects.update(['noform']),IsSpellUser=lambda *a:False))
    wire(current);wire(old)
    victim=Actor(0)
    for c in (old,current,old,current):c.OnKillEvent(victim,p)
    assert effects==dict(elem=1,elem2=1,elem3=1,noform=1),dict(effects)
    # A nested duplicate arriving during on-kill AoE must see the pre-dispatch claim.
    current.env['ESSBElem'].OnKill=lambda *a:(effects.update(['elem']),current.OnKillEvent(a[2],p))
    for _ in range(12):
        v=Actor(0);current.OnKillEvent(v,p);current.OnKillEvent(v,p)
    assert all(n==13 for n in effects.values()),dict(effects)
    # Orphan controller callbacks must exit before native calls, allocation, globals or ticking.
    old.fields['FixInitialised']=False;old.fields['LiftActor']=None
    for fn,args in [('OnInit',()),('OnPlayerLoadGame',()),('OnUpdate',()),('Setup',()),
                    ('InitRegistry',()),('InitFixState',()),('ArmUpdate',()),('ScheduleTick',(1,)),
                    ('OnWeaponHit',(None,None,None,0)),('ToggleForm',(1,)),('CloseForm',())]:
        getattr(old,fn)(*args)
    assert old.LiftActor is None
    for name,field in [('ESSBGuard','Ctl'),('ESSBTrees','Controller')]:
        vm=Script(folder/(name+'.psc'));vm.fields[field]=old
        for fn in ('OnInit','OnPlayerLoadGame','Setup'):getattr(vm,fn)()
        if name=='ESSBGuard':vm.OnActorKilled(victim,p)
        else:vm.OnCustomSkillIncrease('ESSB_darkness');vm.OnUpdate()
    assert all(n==13 for n in effects.values())
    return 'two instances, repeated delivery, nested delivery, 13 victims, orphan lifecycle/XP/guard callbacks'

def regression_c(path):
    from tes import read_plugin
    records,_=read_plugin(path)
    families=('FormActive','Release','DrawSheathe','Charge','OnHit')
    found={f:[] for f in families}
    for r in records:
        if r.sig!='SNDR':continue
        for f in families:
            if re.fullmatch('ESSBFX_ZZSoundDescriptor_'+f+'_(Fire|Frost|Lightning|Earth|Wind|Blood|Divine|Poison|Water|Darkness|Astral)',r.edid):
                assert len(r.d['LNAM'])==4
                assert r.d['LNAM'][1]==0,(r.edid,r.d['LNAM'].hex())
                found[f].append(r.edid)
    assert all(len(v)==11 for v in found.values())
    return {f:len(v) for f,v in found.items()}

def regression_d(folder):
    owned=True
    c=NS(FormActive=Glob(1),Trees=NS(BranchInternal=lambda *a:owned,MainRankInternal=lambda *a:3))
    c.Trees.CachedBranch=c.Trees.BranchInternal;c.Trees.CachedMainRank=c.Trees.MainRankInternal
    nodes=Script(folder/'ESSBNodes.psc')
    if 'akCtl.Rank(' in (folder/'ESSBNodes.psc').read_text(encoding='utf8'):
        # Execute the relocated controller gate with real mirror arrays.
        gate=Script(folder/'ESSBController.psc')
        gate.fields.update(FormActive=c.FormActive,NodeMirrorReady=True,RankCacheA=Array([3]*120),RankCacheB=Array([3]*75),BranchCacheA=Array([15]*120),BranchCacheB=Array([15]*75))
        c.Rank=gate.Rank
        c.Br=lambda *a:owned and gate.Br(*a)

    assert not nodes.Br(c,11,1,1,1), 'backlash active while form is active'
    assert nodes.Rank(c,11,0,0)==0
    assert nodes.Br(c,11,2,4,1) and nodes.Rank(c,11,2,0)==3,'explicit burst transition effects preserved'
    c.FormActive.v=0
    assert nodes.Br(c,11,1,1,1) and nodes.Rank(c,11,0,0)==3
    owned=False
    assert not nodes.Br(c,11,1,1,1),'unowned branch'
    assert not nodes.Br(c,6,0,4,1),'unowned Pure Land'
    # Drive the actual incoming-spell event, including the branch ownership gate.
    ctl,p=controller(folder);ctl.fields.update(Trees=c.Trees,Enabled=Glob(1))
    ctl.overrides.update(GetSelf=lambda *a:0,GetIceShield=lambda:0,GetWaterMirror=lambda:0,
                         GetGuardWindLeft=lambda:0)
    effects=[]
    ctl.overrides['ApplyUtil']=lambda *a:effects.append(a)
    ctl.overrides['LogThrottled']=lambda *a:None
    guard=Script(folder/'ESSBGuard.psc',dict(ESSBNodes=nodes,ESSBReactions=NS(BaseMax=lambda *a:5)))
    guard.fields['Ctl']=ctl;guard.overrides['TakeAttacker']=lambda *a:True
    if 'NodeBits' in guard.fields:
        guard.fields.update(Ready=True,Enabled=ctl.Enabled,DivineArmed=Glob(0),NodeBits=True,
                            RockArmor=Glob(0),IceShield=Glob(0),WaterMirror=Glob(0),GuardWind=Glob(0))
        guard.overrides['GetActorReference']=lambda:p
        ctl.overrides['Br']=lambda *a:owned and not (a[0]==11 and a[1]<2 and ctl.FormActive.v==1)

    for active,have,expected in [(1,True,0),(0,False,0),(0,True,1)]:
        ctl.FormActive.v=active;owned=have;effects.clear()
        guard.OnHitEx(Actor(),Spell(),None,False,False,False,False)
        assert len(effects)==expected,(active,have,effects)
    return 'active/off + owned/unowned; martial/anti-magic gated; burst transition route preserved'

def evidence():
    lines=(ROOT/'.codex/smoke3-essb-events.log').read_text(encoding='utf-8-sig').splitlines()
    # First section is the event stream; the following error excerpts duplicate context.
    boundary=next(i for i,l in enumerate(lines) if l.startswith('\t'))
    events=lines[:boundary]
    tags=collections.Counter(re.search(r'\[ESSB\]\[(.*?)\]',l)[1].lower() for l in events if '[ESSB]' in l)
    kills=collections.Counter(re.search(r'\[L1\] (.*)',l)[1] for l in events if '[kill]' in l.lower())
    return dict(primary_events=len(events),tags=dict(tags),kill_multiplicity=dict(collections.Counter(kills.values())),
                orphan_stack_lines=sum('FC000800' in l for l in lines),
                orphan_examples=[dict(line=i+1,text=l) for i,l in enumerate(lines) if 'FC000800' in l][:6])

def run():
    baseline=ROOT/'.codex/pre-fix10-snapshot/src'
    assert baseline.is_dir()
    cases={};negatives={}
    oldesp=ROOT/'build/fix10-before/Elements Spellblade.esp'
    for name,fn,old,new in [('A',regression_a,baseline,ROOT/'src'),('B',regression_b,baseline,ROOT/'src'),
                            ('C',regression_c,oldesp,ROOT/'package/Elements Spellblade/Elements Spellblade.esp'),
                            ('D',regression_d,baseline,ROOT/'src')]:
        try:fn(old)
        except AssertionError as ex:negatives[name]=str(ex)
        else:raise AssertionError(name+' pre-fix incorrectly passed')
        cases[name]=fn(new)
    before=json.loads((ROOT/'.codex/pre-fix10-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    after=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    changed={k:dict(before=v,after=after.get(k)) for k,v in before.items() if after.get(k)!=v}
    assert set(changed)=={'ESSB_MainQuest','ESSB_MCMQuest'}
    import state_schema
    version=json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    assert all(after[k]['id']==f'{v:06X}' for k,v in state_schema.quest_ids(version).items())
    assert after['ESSB_DebugLevel']['id']=='000811'
    added={k:v for k,v in after.items() if k not in before}
    assert set(added)==(set(state_schema.stub_ids(version))-set(state_schema.stub_ids(2))) | __import__('build_v03').GUARD_WINDOW_EDIDS | (__import__('build_v03').hit18.new_edids(__import__('build_v03')) | __import__('build_v03').hit19.NEW_EDIDS)
    from tes import read_plugin
    oldrecords,_=read_plugin(oldesp)
    newrecords,_=read_plugin(ROOT/'package/Elements Spellblade/Elements Spellblade.esp')
    newby={r.edid:r for r in newrecords}
    import build_v03 as b
    # A pre-switch cloak-guard window must also be disabled by the engine perk gate.
    off=b.gv_eq(b.ID_GLOB['ESSB_FormActive'],0)
    assert off in [data for tag,data in b.branch_entries('noform',1,3,0) if tag=='CTDA']
    assert off in [data for tag,data in newby['ESSB_P_noform_1_3_B1'].ss if tag=='CTDA']
    sound_changes=[]
    for old in oldrecords:
        if old.sig not in ('SOUN','SNDR'):continue
        normalize=old.sig=='SNDR' and re.match('ESSBFX_ZZSoundDescriptor_(FormActive|DrawSheathe)_',old.edid)
        expected=[(tag,data[:1]+b'\0'+data[2:] if normalize and tag=='LNAM' else data) for tag,data in old.ss]
        assert newby[old.edid].ss==expected,old.edid
        if old.ss!=expected:sound_changes.append(old.edid)
    assert len(sound_changes)==20
    # Original file encodings, immutable design, and append-only implementation notes.
    for old in (ROOT/'build/fix10-before').rglob('*'):
        rel=old.relative_to(ROOT/'build/fix10-before')
        if not old.is_file() or old.suffix=='.esp':continue
        a=old.read_bytes();b=(ROOT/rel).read_bytes()
        if rel.as_posix()=='實作紀錄.md':
            prior=a
            a=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
            assert a.replace(b'\r\n',b'\n').startswith(prior.replace(b'\r\n',b'\n'))
        assert a.startswith(b'\xef\xbb\xbf')==b.startswith(b'\xef\xbb\xbf'),str(rel)
        assert bool(a.count(b'\r\n'))==bool(b.count(b'\r\n')),str(rel)
        if a.count(b'\r\n')==a.count(b'\n'):assert b.count(b'\r\n')==b.count(b'\n'),str(rel)
        if rel.as_posix()=='實作紀錄.md':assert b.startswith(a)
    report=dict(cases=cases,pre_fix_failures=negatives,changed=changed,added=added,
                sound_changes=sound_changes,evidence=evidence(),runtime_tested=False)
    (ROOT/'build/fix10-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('FIX10 ok: A/B/C/D regressions; all four fail pre-fix and pass current; current schema; only two quest IDs changed; 55 one-shot descriptors')
    return report

if __name__=='__main__':run()
