"""Additional actual-body input and target multiplier regression scenarios."""
import itertools,math
from types import SimpleNamespace as NS
from papyrus_harness import Script,Array

def input_checks(root):
    # Round 25 (N6): ESSBInput is gone -- the hotkeys are the DLL's input sink and switch (native/include/Timer.h
    # InputOpen / PlanSwitch, tested in native/tests/timer_test.cpp); these round-18 gates run on the script round 24
    # shipped, which build/fix25_history.py ties to today's (declared changes only).
    import sys
    sys.path.insert(0,str(root/'build'))
    import fix25_history
    legacy=fix25_history.legacy_source()
    class G:
        def __init__(self,v):self.v=v
        def GetValueInt(self):return int(self.v)
        def SetValueInt(self,v):self.v=v
    checks=[]
    for reason in ['open','switch','close','low','free','branch','disabled','stale','broken','unready','dead','invalid','menu','text','keys-off']:
        notices=[];events=[];quest=object();menu=reason=='menu';text=reason=='text'
        vm=Script(legacy/'ESSBInput.psc',dict(ESSBState=NS(ControllerQuest=lambda:quest),Debug=NS(Notification=lambda x:notices.append(x)),Utility=NS(IsInMenuMode=lambda:menu),UI=NS(IsTextInputEnabled=lambda:text)))
        active=reason in ['switch','close'];current=1 if active else 0
        ctl=NS(StateBroken=reason=='broken')
        ctl.SetFreeOpen=lambda x:events.append(('consume',vm.CurrentElement.v,vm.FormActive.v))
        ctl.SwitchForm=lambda x:events.append(('switch',vm.CurrentElement.v,vm.FormActive.v))
        player=NS(IsDead=lambda:reason=='dead',GetActorValue=lambda x:0 if reason in ['low','free','branch'] else 100,GetActorValueMax=lambda x:100)
        vm.fields.update(Ctl=ctl,Ready=reason!='unready',Enabled=G(reason!='disabled'),CurrentElement=G(current),FormActive=G(active),FreeOpen=G(reason=='free'),FreePass=reason=='branch',FormNotify=G(1),HotkeysEnabled=G(reason!='keys-off'),Hotkeys=Array([G(20+i) for i in range(11)]))
        vm.overrides.update(GetOwningQuest=lambda:object() if reason=='stale' else quest,GetActorReference=lambda:player)
        wanted=1 if reason=='close' else 2
        if reason in ['menu','text','keys-off']:vm.OnKeyDown(21)
        else:vm.RequestSwitch(0 if reason=='invalid' else wanted)
        ok=reason in ['open','switch','close','free','branch']
        assert bool(events)==ok,(reason,events)
        if ok:
            assert events[-1]==('switch',0 if reason=='close' else wanted,0 if reason=='close' else 1),(reason,events)
            assert len(events)==(1 if active else 2)
        else:assert vm.FormActive.v==active and vm.CurrentElement.v==current,reason
        checks.append(reason)
    return checks

def targets(api):
    rows=[];cache={}
    for e,power,sneak,opening in itertools.product(range(1,12),(False,True),(False,True),(False,True)):
        fresh=e not in cache
        if fresh:cache[e]=[api.fixture(api.OLD),api.fixture()]
        fs=cache[e]
        for f in fs:
            f.apps.clear()
            f.env['ESSBNoForm']=api.Measured(f.c.path.parent/'ESSBNoForm.psc',f.env)
            f.v.GetActorValuePercentage=lambda av:0 if av=='Magicka' else 1
            f.v.GetEquippedSpell=lambda slot:object()
            for tree in range(13):
                for route in range(3):
                    for tier in range(5):api.ranks(f,tree,route,tier,3,7)
            f.c.fields.update(CachedSync=40,KillStreakReady=True,KeepSneakLeft=110)
            f.c.Sync.v=40
            f.c.overrides.update(GetStack=lambda *x:12,GetAirborne=lambda *x:3,HasStarLock=lambda *x:True,InDomain=lambda *x:True,HasElementMark=lambda *x:True)
            f.v.GetActorValue=lambda av:0 if av=='Magicka' else 1000
            f.v.HasKeyword=lambda kw:True
            f.v.IsInFaction=lambda x:True
            f.c.fields['NecroFaction']=object()
            f.v.GetActorBase=lambda:NS(GetClass=lambda:object())
            f.p.GetActorValuePercentage=lambda x:.95
        a,n=fs
        if fresh:n.c.RefreshSyncStage();n.c.RefreshProcMagnitudes()
        if e==6:
            # Approved phase-1 blood steps replace old continuous curve only.
            a.c.overrides['GetBloodHitMult']=lambda:n.c.GetBloodHitMult()
        a.c.ApplyProc(a.v,e,power,sneak,opening)
        n.c.ApplyProc(n.v,e,power,sneak,opening)
        idx=next(i for i,v in enumerate(api.r18.variants(api.b)) if v['e']==e and v['p']==int(power) and v['s']==(int(sneak) if e==5 else 0) and v['band']==0 and (v['existing'] or e==5 and sneak))
        base=n.c.ProcVariants[idx].values[0]
        if e==6 and n.c.GetBloodHitMult()!=n.c.BloodBandMult(0):base*=1.15
        bonus=n.apps[-1]['values'][0] if n.apps else 0
        old=a.apps[-1]['values'][0]
        assert math.isclose(base+bonus,old,abs_tol=1e-4),(e,power,sneak,opening,base,bonus,old)
        assert a.c.KillStreakReady==n.c.KillStreakReady
        rows.append([e,power,sneak,opening,base,bonus,old])
    return rows

def blood(api):
    rows=[]
    for reverse,rage,hp,power in itertools.product((False,True),(False,True),[0,.1999,.2,.2999,.3,.5,.7,.7001,.8499,.85,1],(False,True)):
        f=api.fixture();api.ranks(f,5,0,2,0,int(reverse));api.ranks(f,5,0,3,0,2 if rage else 0)
        f.p.GetActorValuePercentage=lambda x:hp
        f.c.RefreshProcMagnitudes()
        band=f.c.BloodBand(hp);i=next(i for i,v in enumerate(api.r18.variants(api.b)) if v['e']==6 and v['p']==int(power) and v['band']==band)
        expected=f.c.PlayerProcBase(6,power)*f.c.GetBloodHitMult()
        v=f.c.ProcVariants[i].values;actual=v[0]+(v[1] if rage and .3<=hp<=.7 else 0)
        assert math.isclose(actual,expected,abs_tol=1e-4),(reverse,rage,hp,power,actual,expected)
        rows.append([reverse,rage,hp,power,actual])
    return rows
