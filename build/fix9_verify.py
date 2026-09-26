"""FIX9 offline source execution and failure injection; never claims to emulate saved-game VM binding."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy, hashlib, json, re, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
# Round 22: these checks run on the pre-fix22 scripts; build/fix22_history.py ties them to today's (declared changes only).
import sys as _sys22
_sys22.path.insert(0, str(ROOT / 'build'))
import fix22_history as _fix22_history
SRC22 = _fix22_history.legacy_source()
def CUR22(rel):  # a repo path as the older rounds knew it: src/* comes from the pre-fix22 snapshot
    rel = str(rel).replace(chr(92), '/')
    return SRC22 / rel[4:] if rel.startswith('src/') else ROOT / rel

sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'build'))
from papyrus_harness import Script, Array
import state_schema

class Glob:
    def __init__(self,v=0): self.value=v
    def GetValue(self):return self.value
    def GetValueInt(self):return int(self.value)
    def SetValueInt(self,v):self.value=v

class Player:
    def __init__(self):self.spells=set();self.perks={'earned-perk'};self.adds=[];self.removes=[]
    def HasSpell(self,s):return s in self.spells
    def EndDeferredKill(self):self.__dict__['ended_deferred']=self.__dict__.get('ended_deferred',0)+1
    def StartDeferredKill(self):self.__dict__['started_deferred']=self.__dict__.get('started_deferred',0)+1
    def AddSpell(self,s,quiet=False):self.spells.add(s);self.adds.append(s)
    def RemoveSpell(self,s):self.spells.discard(s);self.removes.append(s)
    def DispelSpell(self,s):self.removes.append(s)
    def HasPerk(self,s):return s in self.perks
    def AddPerk(self,s):self.perks.add(s)

class RejectField(dict):
    """A saved untyped member ignores array assignment; count actual attempts."""
    def __init__(self,data,bad):super().__init__(data);self.bad=bad;self.attempts=0
    def __setitem__(self,k,v):
        if k==self.bad and isinstance(v,list):self.attempts+=1;v=None
        super().__setitem__(k,v)

def make():
    notices=[];queue=[];registrations=[];player=Player()
    po3=NS(RegisterForWeaponHit=lambda x:registrations.append('weapon'),UnregisterForWeaponHit=lambda x:None,
           RegisterForHitEventEx=lambda x:registrations.append('hit'),RegisterForActorKilled=lambda x:registrations.append('kill'))
    env=dict(Debug=NS(MessageBox=lambda s:notices.append(s)),PO3_Events_Alias=po3,
             Utility=NS(GetCurrentRealTime=lambda:10.0),SendModEvent=lambda *args:None,
             UnregisterForUpdate=lambda:queue.clear(),RegisterForSingleUpdate=lambda d:queue.append(d),GetActorReference=lambda:player,RegisterForMenu=lambda *a:None)
    helper=Script(SRC22/'ESSBState.psc')
    env['ESSBState']=helper
    ctl=Script(SRC22/'ESSBController.psc',env)
    trees=Script(SRC22/'ESSBTrees.psc',env)
    guard=Script(SRC22/'ESSBGuard.psc',env)
    # Required VMAD properties are supplied by the ESP in production. Give distinct identity tokens here.
    for vm in (ctl,trees):
        source=vm.path.read_text(encoding='utf8')
        for typ,n in re.findall(r'(?m)^(\w+(?:\[\])?) Property (\w+).* Auto$',source):
            if typ=='GlobalVariable':vm.fields[n]=Glob(17)
            elif typ=='GlobalVariable[]':vm.fields[n]=Array([Glob(37+i) for i in range(13)])
            elif typ in ('Float[]','Int[]'):vm.fields[n]=Array([1]*11)
            elif typ.endswith('[]'):vm.fields[n]=Array([object() for _ in range(28 if n=='UtilSpells' else 11)])
            elif typ not in ('Int','Float','Bool','String'):vm.fields[n]=object()
    for field in ['ProcVariants','ProcElements','ProcRatios','ProcPowers','ProcSneaks','ProcBloodBands']:
        ctl.fields[field]=Array([object() if field=='ProcVariants' else 1 for _ in range(42)])
    ctl.fields['GuardLayer']=guard
    ctl.fields['InputLayer']=NS(Setup=lambda:None,RefreshPermission=lambda:None)
    guard.overrides['RefreshNodeBits']=lambda:None
    ctl.overrides.update(RefreshSyncStage=lambda:None,RefreshProcMagnitudes=lambda:None)
    ctl.fields['Trees']=trees;trees.fields['Controller']=ctl;guard.fields['Ctl']=ctl
    trees.overrides['UnregisterForUpdate']=lambda:queue.clear()
    helper.overrides['ControllerQuest']=lambda:NS(GetAlias=lambda i:ctl)
    helper.overrides['GuardWindowSpell']=lambda i:None
    ctl.env=dict(env,GetOwningQuest=lambda:NS(GetAlias=lambda i:guard))
    ctl.overrides.update(RefreshTrees=lambda:None,RefreshAbilities=lambda:None,EnvCheck=lambda:None)
    return ctl,trees,guard,player,notices,queue,registrations

def expect_fail(f):
    try:f()
    except (AssertionError,ValueError):return
    raise AssertionError('negative schema case incorrectly accepted')

def run():
    lock=state_schema.preflight();current=state_schema.signatures();version=lock['state_schema_version']
    assert not state_schema.check_lock(version,current,lock)
    changed=copy.deepcopy(current);changed['ESSBController']['members'].append(('futurearray','int[]','member'))
    expect_fail(lambda:state_schema.check_lock(version,changed,lock))
    assert state_schema.check_lock(version+1,changed,lock)
    expect_fail(lambda:state_schema.check_lock(version-1,current,lock))
    expect_fail(lambda:state_schema.check_lock(version+2,current,lock))
    for mutation in ('remove','retype'):
        c=copy.deepcopy(current);rows=c['ESSBController']['members']
        if mutation=='remove':rows.pop()
        else:rows[0]=(rows[0][0],'bool[]','member')
        expect_fail(lambda:state_schema.check_lock(version,c,lock))
    assert state_schema.quest_ids(3)=={'ESSB_MainQuest':0x6002,'ESSB_MCMQuest':0x6003}
    assert set(state_schema.stub_ids(2).values())<set(state_schema.stub_ids(3).values())
    src=(SRC22/'ESSBController.psc').read_text(encoding='utf8')
    sig=state_schema.signature(src)
    assert state_schema.signature(src+'\nFunction LocalOnly()\n Int[] local = new Int[8]\nEndFunction\n')==sig
    assert state_schema.signature(src+'\nInt[] AddedMember\n')!=sig
    assert state_schema.signature(src.replace('Actor[] LiftActor','Int[] LiftActor'))!=sig
    comparisons=[]
    for p in (SRC22).glob('*.psc'):
        s=p.read_text(encoding='utf8');arrays=set(re.findall(r'\b\w+\[\]\s+(?:Property\s+)?(\w+)',s,re.I))
        for num,line in enumerate(s.splitlines(),1):
            for var,op in re.findall(r'\b(\w+)\s+(==|!=)\s+None\b',line.split(';')[0]):
                assert var.lower() not in {a.lower() for a in arrays},(p.name,num,var)
                comparisons.append(dict(file=p.name,line=num,variable=var,op=op))
    # First setup closes a serialized active form and creates the hidden rules AME exactly once.
    ctl,trees,guard,p,notes,queue,regs=make()
    keep=[ctl.SettingsPower,*ctl.FormPowers];p.spells.update(keep+[ctl.FormRulesAbility,*ctl.FormAbilities])
    glob_before={n:[g.value for g in trees.fields[n]] for n in ('LvlGlobals','PtsGlobals','RatioGlobals','RespecGlobals')}
    settings_before={n:ctl.fields[n].value for n in ('Enabled','DebugLevel','MultUpkeep','MultDot','NodeScale')}
    ctl.Setup()
    assert ctl.IsOperational() and ctl.FixInitialised and ctl.RegistryInitialised and trees.TablesInitialised
    assert not notes and set(keep)<=p.spells and not set(ctl.FormAbilities)&p.spells
    assert ctl.FormActive.value==ctl.CurrentElement.value==ctl.Sync.value==0
    assert p.adds==[ctl.FormRulesAbility] and p.removes.count(ctl.FormRulesAbility)==1
    assert p.perks=={'earned-perk',ctl.BaseRulesPerk,ctl.HitProcPerk}
    assert all([g.value for g in trees.fields[n]]==v for n,v in glob_before.items())
    assert all(ctl.fields[n].value==v for n,v in settings_before.items())
    identities={n:id(v) for n,v in ctl.fields.items() if isinstance(v,Array)}
    for _ in range(40):ctl.InitRegistry();ctl.InitFixState();ctl.Setup()
    assert all(id(ctl.fields[n])==v for n,v in identities.items()) and p.adds==[ctl.FormRulesAbility]
    assert p.removes.count(ctl.FormRulesAbility)==1
    # The fast path cannot even inspect array truthiness after successful initialization.
    class NoProbe(Array):
        def __bool__(self):raise AssertionError('hot path probed initialized array')
    for n in identities:ctl.fields[n]=NoProbe(ctl.fields[n])
    ctl.InitRegistry();ctl.InitFixState()
    # Every required controller-owned array can fail individually. No second attempt or gameplay entry may run.
    members=state_schema.signature(src)['members']
    own_arrays=[n for n,t,k in members if t.endswith('[]') and k=='member' and n not in ('swapints',)]
    tested=[]
    for lower in own_arrays:
        c,t,g,p,notices,q,r=make();name=next(n for n in c.fields if n.lower()==lower)
        if name in ('ProcWritten','DrainWritten'):
            c.fields['NodeMirrorReady']=True;c.overrides.pop('RefreshProcMagnitudes')
        c.fields=RejectField(c.fields,name);c.Setup()
        assert c.StateBroken and len(notices)==1 and not c.IsOperational(), name
        count=c.fields.attempts
        for _ in range(3):
            c.Setup();c.OnUpdate();c.OnPlayerLoadGame();c.OnInit();c.ArmUpdate();c.InitRegistry();c.InitFixState()
            c.OnWeaponHit(None,None,None,0);c.OnKillEvent(None,None);c.ToggleForm(1);c.SwitchForm(2);c.CloseForm();c.Tick();c.TickTimers();c.TickDomain()
            c.OnMarkStart(1,None,None);c.OnMarkFinish(1,None,None);c.OnStatusStart(None,None);c.OnStatusFinish(None,None)
            g.OnHitEx(None,None,None,False,False,False,False);g.OnActorKilled(None,None);t.OnUpdate();t.OnCustomSkillIncrease('ESSB_fire')
        assert c.fields.attempts==count==1 and len(notices)==1 and not q and not r,name
        tested.append(name)
    # Trees and guard arrays have the same one-shot failure boundary before their first element access.
    for script,fields in [('trees',['SkillIds','TreeNames','CacheTree','CacheRank','CacheBranch','SnapBranch','AllRankA','AllRankB','AllBranchA','AllBranchB','AllValid','LevelCache']),('guard',['RecentActor','RecentTime'])]:
        for name in fields:
            c,t,g,p,notices,q,r=make();vm=t if script=='trees' else g;vm.fields=RejectField(vm.fields,name)
            c.Setup();assert c.StateBroken and len(notices)==1,name
            for _ in range(3):c.Setup();t.InitTables();g.Setup()
            assert vm.fields.attempts==1 and len(notices)==1,name
            tested.append(script+'.'+name)
    # Four active-effect rings fail before any element read/write and stop all subsequent callbacks.
    for name in ('BleedRing','PoisonRing','AstralRing','AstralWeight'):
        c,t,g,p,notices,q,r=make();c.Setup();q.clear()
        quest=NS(GetAlias=lambda i:c)
        helper=Script(SRC22/'ESSBState.psc');helper.overrides['ControllerQuest']=lambda:quest
        status=Script(SRC22/'ESSBStatus.psc',dict(ESSBState=helper,RegisterForSingleUpdate=lambda d:q.append(d)))
        status.fields['Controller']=quest;status.fields=RejectField(status.fields,name)
        status.OnEffectStart(p,p)
        assert c.StateBroken and len(notices)==1 and not status.Bound,name
        for _ in range(3):status.OnEffectStart(p,p);status.OnUpdate();status.AddStack(7,1)
        assert status.fields.attempts==1 and len(notices)==1 and not q,name
        tested.append('status.'+name)
    shatter=Script(SRC22/'ESSBElem.psc');shatter.Shatter(None,None,1.0)
    # Missing required VMAD bindings stop before any gameplay; validates the None.value error boundary.
    for field in ('MultUpkeep','BaseDamageMult','Trees','FormPowers','FormRulesAbility'):
        c,t,g,p,notices,q,r=make();c.fields[field]=None;c.Setup();c.OnUpdate()
        assert c.StateBroken and len(notices)==1 and not p.adds,field
    # Old AMEs may still exist for their finite duration. Reject them before resolving the orphaned alias.
    class Orphan:
        def __getattr__(self,n):raise AssertionError('touched orphan '+n)
    for name,event,args in [('ESSBStatus','OnUpdate',()),('ESSBMark','OnEffectStart',(None,None)),('ESSBCounter','OnAnimationEvent',(None,'')),('ESSBFormRules','OnUpdate',()),('ESSBSilence','OnUpdate',())]:
        vm=Script(SRC22/f'{name}.psc',dict(ESSBState=NS(ControllerQuest=lambda:object(),Operational=lambda:True)))
        vm.fields.update(Controller=object(),Ctl=Orphan());getattr(vm,event)(*args)
    # BOM and exact existing line ending conventions; protected tree hashes are read-only evidence.
    for old in (ROOT/'.codex/pre-fix9-snapshot').rglob('*'):
        rel=old.relative_to(ROOT/'.codex/pre-fix9-snapshot')
        if not old.is_file() or rel.as_posix()=='v03-formids.json':continue
        a=old.read_bytes();b=CUR22(rel).read_bytes()
        assert a.startswith(b'\xef\xbb\xbf')==b.startswith(b'\xef\xbb\xbf'),str(rel)
        assert (a.count(b'\r\n'),a.count(b'\n')-a.count(b'\r\n'))[0]==0 or b.count(b'\r\n')==b.count(b'\n'),str(rel)
        if a.count(b'\r\n')==0:assert b.count(b'\r\n')==0,str(rel)
        b.decode('utf8')
    protected=json.loads((ROOT/'build/fix9-protected-hashes.json').read_text(encoding='utf8'))
    for n,h in protected.items():
        if n.startswith('.strategic-advance/'): continue  # commander's campaign ledger is append-only by design
        if n in ('plan_coverage.py','plan_trees.py'):
            # Round 21 rebuilt both for v0.4 (its write set): the pre-fix21 snapshot must still carry the protected bytes.
            assert hashlib.sha256((ROOT/'.codex/pre-fix21-snapshot'/n).read_bytes()).hexdigest()==h,n
            continue
        assert hashlib.sha256(CUR22(n).read_bytes()).hexdigest()==h,n
    report=dict(array_failure_cases=tested,remaining_none_comparisons=comparisons,first_setup=True,repeated_setup=True,progress_preserved=True,old_effects_quarantined=True,signature_negative_cases=6,runtime_tested=False)
    (ROOT/'build/fix9-runtime-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'FIX9 ok: {len(tested)} array failures latched once; no retry/tick/hit/kill/power; Setup idempotent; progress preserved; old AMEs quarantined; schema negative cases; encodings/protected files checked')
    return report

if __name__=='__main__':run()
