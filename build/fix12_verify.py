"""Round 12 actual-source regression + exact review-G counter (natives mocked).
No engine UI/VM timing claim. Both source and packaged record acceptance are checked.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import collections, hashlib, json, re, sys, struct
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build'),str(ROOT)]
import papyrus_harness as h
from fix12_cost import scenario, Measured, Counter
import state_schema
OLD=ROOT/'.codex/pre-fix12-snapshot/src'
NEW=ROOT/'src'

def fixture(folder=NEW):return scenario(folder,prepare_only=True)

def clock_regression(folder):
    c,t,p,v,w,clock,m,env,Glob=fixture(folder)
    scheduled=[];c.overrides['RegisterForSingleUpdate']=scheduled.append
    arm=c.ScheduleTickInternal if 'ScheduleTickInternal' in c.functions else c.ScheduleTick
    c.fields['NextTickAt']=0
    arm(1.0);first=c.NextTickAt
    for dt in [.1,.5,.9]:clock[0]=100+dt;arm(1.0)
    assert c.NextTickAt==first,'continuous hits postpone tick'
    clock[0]=100.95;arm(.01);assert c.NextTickAt<first
    # The completed tick can move the regular deadline forward; lift wins if earlier.
    c.fields.update(NextTickAt=100.96,LastNodeScale=3,LastRecoveryScale=0,SelfCharge=0)
    c.FormActive.v=0;c.RegActor[0]=None
    counts=collections.Counter()
    c.overrides.update(TickTimers=lambda:counts.update(['timers']),SwapHosts=lambda:counts.update(['hosts']),
                       TimersActive=lambda:True,EnvCheck=lambda:None)
    env['ESSBNodes'].overrides['AvatarCooldown']=lambda *a:0
    clock[0]=101;c.Tick()
    assert counts==dict(timers=1,hosts=1) and c.NextTickAt==102
    c.fields['LiftQueued']=True;c.LiftActor[0]=v;c.LiftDue[0]=101.15;c.ArmUpdate()
    assert abs(scheduled[-1]-.15)<1e-8
    # Drive 35 seconds of 0.5s hits through real scheduler and real OnUpdate dispatch.
    c.LiftActor[0]=None;c.fields['LiftQueued']=False
    c.FormActive.v=1
    c.overrides['Tick']=lambda:(counts.update(['tick']),c.fields.update(NextTickAt=0),arm(1.0))
    for n in range(1,71):
        clock[0]=101+n*.5;arm(1.0)
        if clock[0]>=c.NextTickAt:c.OnUpdate()
    assert counts['tick']==35
    return '0.5s hits for 35s: 35 ticks; completed tick re-arms; lift deadline preserved'

def rules_regression(folder):
    now=[60.0];ready=[True];scheduled=[];events={};notices=[];closed=[]
    class Player:
        mag=100.0
        def GetActorValue(self,av):return self.mag
        def GetActorValueMax(self,av):return 100.0
        def EndDeferredKill(self):self.__dict__['ended_deferred']=self.__dict__.get('ended_deferred',0)+1
        def StartDeferredKill(self):self.__dict__['started_deferred']=self.__dict__.get('started_deferred',0)+1
        def DamageActorValue(self,av,value):self.mag-=value
    class Glob:
        def __init__(self,v):self.v=v
        def GetValue(self):return self.v
        def GetValueInt(self):return int(self.v)
    player=Player();active=Glob(1)
    c=NS(StateBroken=False,IsOperational=lambda:ready[0],Trees=NS(TreeLevel=lambda e:1),MultUpkeep=Glob(1),
         CloseForm=lambda:(closed.append(True),setattr(active,'v',0)))
    quest=NS(GetAlias=lambda i:c)
    vm=h.Script(folder/'ESSBFormRules.psc',dict(__execute_logs__=True,ESSBState=NS(ControllerQuest=lambda:quest),
        Utility=NS(GetCurrentRealTime=lambda:now[0]),RegisterForSingleUpdate=scheduled.append,
        UnregisterForUpdate=lambda:scheduled.clear(),RegisterForModEvent=lambda name,cb:events.update({name:cb}),
        Debug=NS(Notification=notices.append)))
    vm.fields.update(Controller=quest,FormActive=active,CurrentElement=Glob(1))
    vm.OnEffectStart(player,player);scheduled.clear();ready[0]=False;vm.OnUpdate()
    assert scheduled,'temporary NotReady consumes the only update forever'
    ready[0]=True;vm.fields['MagickaEmptySince']=7200
    vm.OnRulesReady('ESSB_FormRulesReady','',0,None)
    assert vm.MagickaEmptySince==-1 and scheduled==[1.0]
    vm.OnUpdate();assert player.mag<100
    player.mag=0
    for seconds in (60,61,62):now[0]=seconds;vm.OnUpdate()
    assert len(closed)==1 and '魔力耗盡' in notices[0]
    # Old generation must never rearm. Same-generation StateBroken must not retry.
    scheduled.clear();vm.env['ESSBState'].ControllerQuest=lambda:object();vm.OnUpdate()
    assert not scheduled
    vm.env['ESSBState'].ControllerQuest=lambda:quest;c.StateBroken=True;vm.OnUpdate();assert not scheduled
    # Start while not ready still registers the explicit Setup wake-up.
    c.StateBroken=False;ready[0]=False;events.clear();vm.OnEffectStart(player,player)
    assert events['ESSB_FormRulesReady']=='OnRulesReady'
    setup=h.Script(NEW/'ESSBController.psc').functions['Setup'][2]
    assert 'SendModEvent("ESSB_FormRulesReady")' in setup
    return 'update-before-Setup, existing AME wake-up, 2s empty grace, not-ready start, stale/broken exclusion'

def uptime_regression(folder):
    c,t,p,v,w,clock,m,env,Glob=fixture(folder)
    t.fields.update(XPWindowStart=7200,XPCount=10)
    clock[0]=60
    assert t.XPBudget(),'restart uptime leaves XP frozen until 7200s'
    if 'ResetLoadClock' not in c.functions:raise AssertionError('missing load clock reset')
    for key in ['InterruptTime','IceHeartTime','RetaliateTime','SanctuaryTime','CleanseTime','NextTickAt']:
        c.fields[key]=7200
    c.RegLastOpen[0]=c.RegLastEnd[0]=7200;c.RegStatus[0]=None
    levels=[g.v for g in t.LvlGlobals];points=[17+i for i in range(13)];t.fields['PtsGlobals']=h.Array([Glob(v) for v in points])
    c.MultCooldown.v=1;c.ResetLoadClock()
    assert c.TakeInterrupt() and c.TakeIceHeart() and c.TakeRetaliate() and c.TakeSanctuary()
    assert c.RegLastOpen[0]<0 and c.RegLastEnd[0]<0 and c.RegUntil[0]==61
    assert [g.v for g in t.LvlGlobals]==levels and [g.v for g in t.PtsGlobals]==points
    t.fields.update(XPWindowStart=7200,XPCount=10)
    t.overrides.update(ClearShowMenu=lambda:None,RegisterForSingleUpdate=lambda *a:None)
    t.OnPlayerLoadGame();assert t.XPCount==0 and t.XPWindowStart==60
    # Serialized swap backups have application-time fields too: rebase only backward uptime.
    queued=[];status=h.Script(NEW/'ESSBStatus.psc',dict(Utility=env['Utility'],RegisterForSingleUpdate=queued.append))
    status.fields['Ctl']=c
    for stamp in ('HeatTime','FreezeTime','FissureTime','UnbalanceTime','HolyTime','WetTime','PressureTime','CurseTime'):
        status.fields[stamp]=7200
    status.RebaseImportedClock();assert status.HeatTime==60 and queued==[1.0]
    status.fields['HeatTime']=59;queued.clear();status.RebaseImportedClock()
    assert status.HeatTime==59 and not queued
    return '7200s -> 60s: XP + all five short cooldowns reset; levels/points unchanged; mark deadlines finite'

def friendly_regression(folder):
    for kind in ('teammate','summon','reanimated'):
        c,t,p,v,w,clock,m,env,Glob=fixture(folder)
        v.IsPlayerTeammate=lambda:kind=='teammate'
        v.IsCommandedActor=lambda:kind!='teammate'
        for form in (0,1):
            c.FormActive.v=form
            calls=[];c.overrides['OnNoFormHit']=lambda *a:calls.append('noform')
            c.OnWeaponHit(v,w,None,0)
            assert not calls and not m.native['Actor.DoCombatSpellApply'] and not m.native['CustomSkills.AdvanceSkill'],kind
    c,t,p,v,w,clock,m,env,Glob=fixture(folder);c.OnWeaponHit(v,w,None,0)
    assert m.native['Actor.DoCombatSpellApply']==(2 if 'ApplyBakedProc' in c.functions else 3) and m.native['CustomSkills.AdvanceSkill']==2
    return 'teammate/summon/reanimated, form on/off rejected before damage/mark/XP; neutral direct hit accepted'

def menus(folder=NEW):
    c,t,p,v,w,clock,m,env,Glob=fixture(folder)
    clock[0]=100;shown=[];opened=[];refreshed=[];notices=[];scheduled=[];registered=[]
    visible=set();owned=set();fakeplayer=NS(HasPerk=lambda perk:perk in owned,RemovePerk=owned.discard)
    t.fields.update(PlayerRef=fakeplayer,SnapBranch=h.Array([0]*15),PtsGlobals=h.Array([Glob(20) for _ in range(13)]))
    t.overrides.update(InitTables=lambda:None,RegisterForSingleUpdate=scheduled.append,
        RegisterForMenu=registered.append,UnregisterForMenu=lambda *a:None,
        GetBranch=lambda tree,r,tier,n:(tree,r,tier,n),RefreshTree=refreshed.append)
    c.overrides['RefreshAbilities']=lambda:None
    env['Math'].LogicalOr=lambda a,b:a|b
    env['UI']=NS(IsMenuOpen=lambda n:n in visible)
    env['Debug'].Notification=notices.append
    env['ESSBLog']=NS(Log=lambda *a:None)
    env['CustomSkills'].OpenCustomSkillMenu=lambda skill:opened.append((skill,'MessageBoxMenu' in visible))
    quest=NS(GetAlias=lambda i:c);helper=NS(ControllerQuest=lambda:quest)
    effect_env=dict(__execute_logs__=True,ESSBState=helper,cast=lambda obj,typ:t if typ=='ESSBTrees' else h.cast(obj,typ),Debug=env['Debug'],ESSBLog=NS(Log=lambda *a:None))
    def effect():
        e=h.Script(folder/'ESSBSettingsEffect.psc',effect_env)
        e.fields.update(Controller=quest,SettingsMenu=NS(Show=show))
        return e
    def show():
        shown.append(True);visible.add('MessageBoxMenu')
        if len(shown)==1:effect().OnEffectStart(p,p)  # duplicate AME delivery while picker waits
        return 1
    e=effect();e.OnEffectStart(p,p)
    assert len(shown)==1,'one cast dispatches two picker stacks'
    assert not opened,'CSF opens in Message.Show continuation while MessageBox is tearing down'
    e.OnEffectStart(p,p);assert len(shown)==1
    assert not t.BeginSettings(),'second press accepted during queued open'
    # Slow teardown: first deferred event must wait for MessageBox close, without polling.
    before=len(scheduled);clock[0]+=.2;t.OnUpdate()
    assert not opened and t.QueuedTree==12 and len(scheduled)==before
    visible.clear();t.OnMenuClose('MessageBoxMenu');clock[0]+=.2;t.OnUpdate()
    assert opened==[('ESSB_12',False)] and registered==['MessageBoxMenu','StatsMenu'] and t.PendingTree==12
    visible.add('StatsMenu');t.OnMenuOpen('StatsMenu')
    assert not t.BeginSettings();t.OpenTree(11);assert len(opened)==1
    # CSF already spent 1 point; same-tree close spends the remaining 4 for a new branch.
    owned.add((12,0,0,0));t.PtsGlobals[12].v=19
    t.OnMenuClose('Other Menu');assert t.PendingTree==12
    visible.clear();t.OnMenuClose('StatsMenu')
    assert t.PendingTree==-1 and t.PtsGlobals[12].v==15 and refreshed==[12]
    t.OnMenuClose('StatsMenu');assert t.PtsGlobals[12].v==15
    # Lost native close retains the old snapshot, and the next genuine request reconciles it once.
    t.TakeSnapshot(11);t.fields.update(PendingTree=11,OpeningMenu=False)
    assert t.BeginSettings();t.FinishSettings(1);clock[0]+=1;t.OnUpdate()
    assert refreshed==[12,11] and t.PendingTree==12 and len(opened)==2
    # Before Ready, neither picker nor native menu opens and a short notice is visible.
    c.fields['Ready']=False;effect().OnEffectStart(p,p)
    assert '尚未就緒' in notices[-1] and len(shown)==1
    # Retired effect must not redirect to the canonical new alias (round-10 class safeguard).
    stale=effect();stale.fields['Controller']=object();n=len(notices);stale.OnEffectStart(p,p)
    assert len(shown)==1 and len(notices)==n
    return 'duplicate AMEs + repeat callback + queued/visible presses; deferred native open; same-tree branch charge once; stale fallback; pre-ready notice; retired effect rejection'

def caches():
    c,t,p,v,w,clock,m,env,Glob=fixture()
    for tree in range(13):
        pos=tree*15+7;arr=t.AllRankA if pos<120 else t.AllRankB;idx=pos if pos<120 else pos-120
        arr[idx]=tree+1
        assert t.MainRankInternal(tree,1,2)==tree+1
    t.AllBranchB[12*15+7-120]=4
    assert t.BranchInternal(12,1,2,2) and not t.BranchInternal(12,1,2,1)
    t.AllValid[2]=False;t.overrides['GetMainRank']=lambda *a:9;t.overrides['HasBranch']=lambda *a:True
    assert t.MainRankInternal(2,0,0)==9 and t.BranchInternal(2,0,0,0)
    # Execute the cold refresh and verify both banks, rank changes, branch changes and levels.
    env['Math'].LogicalOr=lambda a,b:a|b
    t.LvlGlobals[12].v=33;t.RefreshTree(12)
    assert t.AllValid[12] and t.MainRankInternal(12,0,0)==9 and abs(t.TreeGInternal(12)-2.65)<1e-8
    c.NodeScale.v=1.7;c.DebugLevel.v=3;c.MultDuration.v=.5;c.Sync.v=7;c.RefreshRuntimeValues()
    assert c.CachedNodeScale==1.7 and c.CachedDebugLevel==3 and c.CachedSync==7
    assert c.DurationSeconds(8)==4
    calls=[];c.overrides.update(RefreshTrees=lambda:calls.append('trees'),RefreshAbilities=lambda:calls.append('abilities'))
    c.NodeScale.v=2;c.DebugLevel.v=0;c.OnMenuClose('Journal Menu')
    assert c.CachedNodeScale==2 and c.CachedDebugLevel==0 and calls==['trees','abilities']
    # Every tree mutation refreshes the affected cache; form/load/MCM entry refreshes runtime values.
    for name in ('Reconcile','RespecTree','OnCustomSkillIncrease'):
        assert any('RefreshTree(' in line for line in t.functions[name][2]),name
    return '13 direct-index trees, two <=128 banks, cold fallback, level/rank/branch refresh, MCM close cache invalidation'

def log_gates():
    names=[]
    for p in NEW.glob('*.psc'):
        if p.stem in ('ESSBLog','ESSBSettingsEffect','ESSBFormPowerEffect','ESSBMCM','ESSBPlayerAlias'):continue
        src=p.read_text(encoding='utf8').replace('\\\n','')
        stack=[]
        for line in src.splitlines():
            text=line.strip()
            if text.startswith('If '):stack.append(text)
            elif text=='EndIf':stack.pop()
            if re.match(r'(?:(?:\w+)\.)?(?:LogThrottled|LogEvent|LogRejectedHit)\(',text):
                assert any('CachedDebugLevel >=' in g for g in stack),(p.name,text)
                names.append((p.name,text.split('(')[0]))
    # Existing FIX11 diagnostics exercises high-level text, 0.5s duplicate/20 per second/dropped.
    from fix11_verify import diagnostics
    diagnostics()
    return dict(gated_calls=len(names),cold_legacy=['ESSBSettingsEffect.ToggleEnabled/CycleDebugLevel','ESSBFormPowerEffect startup notices'],throttle='0.5s dedup,20/s,dropped unchanged')

def setup_readiness(folder=NEW):
    from fix9_verify import make
    c,t,g,p,notes,queue,registrations=make()
    c.functions['Setup']=h.Script(folder/'ESSBController.psc').functions['Setup']
    notifications=[];observed=[]
    quest=NS(GetAlias=lambda i:c)
    c.env['ESSBState'].overrides['ControllerQuest']=lambda:quest
    def during_setup():
        observed.append(c.IsOperational())
        assert not c.IsOperational(), 'Setup publishes Ready before tree/ability/environment initialization'
        e=h.Script(NEW/'ESSBSettingsEffect.psc',dict(__execute_logs__=True,ESSBState=c.env['ESSBState'],Debug=NS(Notification=notifications.append)))
        e.fields.update(Controller=quest,SettingsMenu=NS(Show=lambda:(_ for _ in ()).throw(AssertionError('picker before Setup completed'))))
        e.OnEffectStart(p,p)
    c.overrides.update(RefreshTrees=during_setup,RefreshAbilities=during_setup,EnvCheck=during_setup)
    c.Setup()
    assert observed==[False,False,False] and c.IsOperational()
    assert len(notifications)==3 and all('尚未就緒' in n for n in notifications)
    # Existing status updates must survive this legitimate temporary not-ready phase too.
    c.fields['Ready']=False;queue.clear()
    st=h.Script(NEW/'ESSBStatus.psc',dict(ESSBState=c.env['ESSBState'],RegisterForSingleUpdate=queue.append))
    st.fields.update(Controller=quest,Ctl=c,Holder=p);st.OnUpdate();assert queue==[1.0]
    return 'Ready stays false through tree/ability/environment initialization; three early casts notice; live status retries NotReady'

def run():
    cases={};negatives={}
    for name,test in [('tick',clock_regression),('upkeep',rules_regression),('uptime',uptime_regression),('friendly',friendly_regression),('menu',menus)]:
        try:test(OLD)
        except AssertionError as e:negatives[name]=str(e)
        else:raise AssertionError('pre-fix unexpectedly passed '+name)
        cases[name]=test(NEW)
    cases['cache']=caches();cases['logging']=log_gates()
    try:setup_readiness(OLD)
    except AssertionError as e:negatives['early_ready']=str(e)
    else:raise AssertionError('pre-fix early Ready unexpectedly passed')
    cases['setup_readiness']=setup_readiness()
    before=scenario(OLD);after=scenario(NEW)
    assert (before['scripted'],before['native'],before['identity'],before['cross_instance'],before['string_concats'])==(532,388,152,159,8)
    assert after['total']<=320 and 1 <= after['identity'] <= 2 and after['string_concats']==after['logging_calls']==0
    # Both debug levels still execute the same gameplay paths; high-level logs retain content.
    old3=scenario(OLD,3);new3=scenario(NEW,3)
    assert (old3['scripted'],old3['native'])==(533,395)
    assert old3['natives']['Debug.Trace']==2 and new3['natives']['Debug.Trace']==1
    assert [s for s in old3['log_messages'] if '[proc]' not in s]==new3['log_messages'], 'enabled logging content changed'
    oldids=json.loads((ROOT/'.codex/pre-fix12-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    ids=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    changed={k:dict(before=v,after=ids.get(k)) for k,v in oldids.items() if ids.get(k)!=v}
    assert set(changed)==set(state_schema.QUESTS)
    assert all(state_schema.stable_identity(k,ids.get(k),v) for k,v in oldids.items())
    assert ids['ESSB_DebugLevel']['id']=='000811'
    assert set(ids)-set(oldids)==(set(state_schema.stub_ids(json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']))-set(state_schema.stub_ids(3))) | __import__('build_v03').GUARD_WINDOW_EDIDS | (__import__('build_v03').hit18.new_edids(__import__('build_v03')) | __import__('build_v03').hit19.NEW_EDIDS)
    config=json.loads((ROOT/'package/Elements Spellblade/MCM/Config/Elements Spellblade/config.json').read_text(encoding='utf8'))
    sliders=[r for p in config['pages'] for r in p['content'] if r.get('type')=='slider']
    assert len(sliders)==10 and all('預設' in r['text'] for r in sliders)
    assert any(r.get('action', {}).get('function') == 'RestoreDefaults' for r in config['pages'][1]['content'])
    import build_v03 as b
    records,_=b.read_plugin(b.OUT/b.PLUGIN);by={r.edid:r for r in records}
    for r in sliders:assert by[r['id']].d['FLTV']==struct.pack('<f',r['valueOptions']['defaultValue'])
    # Existing authored encodings and exact CRLF patterns are retained.
    for old in OLD.glob('*.psc'):
        a=old.read_bytes();z=(NEW/old.name).read_bytes()
        assert a.startswith(b'\xef\xbb\xbf')==z.startswith(b'\xef\xbb\xbf'),old.name
        if a.count(b'\r\n')==a.count(b'\n'):assert z.count(b'\r\n')==z.count(b'\n'),old.name
        if not a.count(b'\r\n'):assert not z.count(b'\r\n'),old.name
    raw=(ROOT/'build_v03.py').read_bytes();assert raw.count(b'\r\n')==raw.count(b'\n')
    report=dict(cases=cases,negative_controls=negatives,before=before,after=after,debug3_before=old3,debug3_after=new3,
                identity_changes=changed,defaults={r['id']:r['valueOptions']['defaultValue'] for r in sliders},
                runtime_tested=False,menu_root_cause='Source confirms Ready published before Setup completes, immediate Show->CSF continuation and missing cast/alias lock; native teardown hypothesis remains unverified without Skyrim.')
    (ROOT/'build/fix12-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f"FIX12 ok: {len(negatives)} pre-fix reproductions; menu/upkeep/load/friendly/tick/cache/log regressions; {before['scripted']}+{before['native']} -> {after['scripted']}+{after['native']}; L0 concat 8->0; current schema; defaults 10/10; native runtime untested")
    return report

if __name__=='__main__':run()
