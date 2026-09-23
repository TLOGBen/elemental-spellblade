"""Review G source-path counter. Explicit natives; no timing claims or engine emulation."""
import ast, collections, json, re, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'build'))
sys.path.insert(0, str(ROOT))
import papyrus_harness as h

class Counter:
    def __init__(self): self.script=collections.Counter(); self.native=collections.Counter(); self.autoreads=collections.Counter(); self.cross=0; self.concat=0; self.stack=[]; self.logcalls=0
    def wrap(self,name,fn):
        def call(*args):
            self.native[name]+=1
            return fn(*args)
        return call

class Add(ast.NodeTransformer):
    def visit_BinOp(self,n):
        self.generic_visit(n)
        if isinstance(n.op,ast.Add): return ast.copy_location(ast.Call(ast.Name('padd',ast.Load()),[n.left,n.right],[]),n)
        return n

class Measured(h.Script):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.auto_props=set(re.findall(r'(?m)^\w+(?:\[\])? Property (\w+).* Auto(?:ReadOnly)?',self.path.read_text(encoding='utf8')))
    def __getattr__(self,name):
        m=self.env['meter']
        if name in self.fields and name in self.auto_props and m.stack and m.stack[-1] is not self:
            m.autoreads[self.path.stem+'.'+name]+=1
        return super().__getattr__(name)
    def call(self,name,*args):
        meter=self.env['meter']; key=self.path.stem+'.'+name
        meter.script[key]+=1
        if name in ('Log','LogThrottled','LogRejectedHit'): meter.logcalls+=1
        if meter.stack and meter.stack[-1] is not self and 'extends ' in self.path.read_text(encoding='utf8').splitlines()[0]: meter.cross+=1
        meter.stack.append(self)
        try:return super().call(name,*args)
        finally:meter.stack.pop()
    def evaluate(self,text,scope):
        text=re.sub(r'^(.*) as (Int|Float|Bool|Perk|GlobalVariable|ESSBTrees|Form|Message)$',lambda m:f'cast({m[1]}, "{m[2]}")',text)
        expr=h.expression(text)
        expr=re.sub(r'([\w.]+(?:\([^()]*\))?) as (Perk|GlobalVariable|ESSBTrees|Form|Message)',lambda m:f'cast({m[1]}, {m[2]!r})',expr)
        def padd(a,b):
            if isinstance(a,str) or isinstance(b,str):
                self.env['meter'].concat+=1
                return str(a)+str(b)
            return a+b
        scope['padd']=padd
        return eval(compile(ast.fix_missing_locations(Add().visit(ast.parse(expr,mode='eval'))),'<papyrus>','eval'),{'__builtins__':{}},scope)

def scenario(folder, debug=0, prepare_only=False):
    m=Counter(); wrap=m.wrap
    class Glob:
        def __init__(self,v=0): self.v=v
        def GetValue(self):m.native['GlobalVariable.GetValue']+=1;return self.v
        def GetValueInt(self):m.native['GlobalVariable.GetValueInt']+=1;return int(self.v)
        def SetValueInt(self,v):m.native['GlobalVariable.SetValueInt']+=1;self.v=v
    class Actor:
        def IsDead(self):m.native['Actor.IsDead']+=1;return False
        def IsPlayerTeammate(self):m.native['Actor.IsPlayerTeammate']+=1;return False
        def IsCommandedActor(self):m.native['Actor.IsCommandedActor']+=1;return False
        def GetActorValue(self,av):m.native['Actor.GetActorValue']+=1;return 1000.0
        def GetEquippedWeapon(self,left):m.native['Actor.GetEquippedWeapon']+=1;return None if left else weapon
        def GetFormID(self):m.native['Actor.GetFormID']+=1;return 42
        def HasPerk(self,p):m.native['Actor.HasPerk']+=1;return False
        def DoCombatSpellApply(self,s,t):m.native['Actor.DoCombatSpellApply']+=1
        def DispelSpell(self,s):m.native['Actor.DispelSpell']+=1
    class Spell:
        def SetNthEffectMagnitude(self,i,x):m.native['Spell.SetNthEffectMagnitude']+=1
        def SetNthEffectDuration(self,i,x):m.native['Spell.SetNthEffectDuration']+=1
    weapon=NS(GetWeaponType=wrap('Weapon.GetWeaponType',lambda:5))
    player=Actor();target=Actor();clock=[100.0];traces=[]
    env=dict(meter=m,__execute_logs__=True)
    for name in ('ESSBController','ESSBTrees','ESSBNodes','ESSBElem','ESSBElem2','ESSBElem3','ESSBReactions','ESSBState','ESSBLog'):
        env[name]=Measured(folder/(name+'.psc'),env)
    c=env['ESSBController'];t=env['ESSBTrees']
    quest=NS(GetAlias=wrap('Quest.GetAlias',lambda i:c))
    env.update(Utility=NS(GetCurrentRealTime=wrap('Utility.GetCurrentRealTime',lambda:clock[0]),RandomFloat=wrap('Utility.RandomFloat',lambda a,b:(a+b)/2)),
               Math=NS(LogicalAnd=wrap('Math.LogicalAnd',lambda a,b:a&b)),
               Game=NS(GetFormFromFile=wrap('Game.GetFormFromFile',lambda fid,p:quest if fid>=0x6000 else Spell() if 0x5170 <= fid <= 0x5181 else object())),
               CustomSkills=NS(AdvanceSkill=wrap('CustomSkills.AdvanceSkill',lambda *a:None)),
               Debug=NS(Trace=wrap('Debug.Trace',traces.append)))
    for vm in (c,t):
        for k,typ in vm.types.items():
            if typ=='GlobalVariable':vm.fields[k]=Glob()
    if 'NativeHit' in c.fields:c.fields['NativeHit']=Glob(1)  # DLL running; ApplyProc reads this GLOB
    c.InitRegistry()
    c.fields.update(Ready=True,PlayerRef=player,Trees=t,Enabled=Glob(1),FormActive=Glob(1),CurrentElement=Glob(3),
                    Sync=Glob(0),SyncT1=Glob(5),SyncT2=Glob(15),SyncT3=Glob(30),NodeScale=Glob(3),BaseDamageMult=Glob(1),
                    MultDuration=Glob(1),DebugLevel=Glob(debug),HitNormalSpells=h.Array([Spell() for _ in range(11)]),
                    MarkSpells=h.Array([Spell() for _ in range(11)]),EngagedSpell=Spell(),ElementDamageMin=h.Array([1]*11),ElementDamageMax=h.Array([25]*11))
    c.RegActor[0]=target;c.RegElem[0]=3;c.RegStatus[0]=object();c.DamageActor[0]=target
    c.overrides['RegisterForSingleUpdate']=wrap('RegisterForSingleUpdate',lambda *a:None)
    t.fields.update(Controller=c,PlayerRef=player,Ready=True,TablesInitialised=True,CacheTree=h.Array([2,11,12]),CacheRank=h.Array([0]*45),
                    CacheBranch=h.Array([0]*45),LvlGlobals=h.Array([Glob(1) for _ in range(13)]),XPPerHit=Glob(1),
                    SkillIds=h.Array(['ESSB_'+str(i) for i in range(13)]))
    if 'CachedDebugLevel' in c.fields:
        c.RefreshRuntimeValues()
        # Equivalent cold cache preparation: every perk absent, all tree levels 1.
        t.fields.update(AllRankA=h.Array([0]*120),AllRankB=h.Array([0]*75),AllBranchA=h.Array([0]*120),AllBranchB=h.Array([0]*75),
                        AllValid=h.Array([True]*13),LevelCache=h.Array([1]*13))
        c.fields['LiftQueued']=False
    if 'ProcVariants' in c.fields:
        import fix18_records as hit18
        import build_v03 as b
        c.fields.update(RankCacheA=t.AllRankA, RankCacheB=t.AllRankB,
            BranchCacheA=t.AllBranchA, BranchCacheB=t.AllBranchB,
            LevelMirror=t.LevelCache, NodeMirrorReady=True,
            HitBonusSpells=h.Array([Spell() for _ in range(11)]))
        rows=hit18.variants(b)
        for field,key in [('ProcElements','e'),('ProcPowers','p'),('ProcSneaks','s'),('ProcBloodBands','band'),('ProcRatios','ratio')]:
            c.fields[field]=h.Array([v[key] for v in rows])
        c.fields['ProcVariants']=h.Array([Spell() for _ in rows])
        player.IsSneaking=wrap('Actor.IsSneaking',lambda:False)
        player.GetActorValuePercentage=wrap('Actor.GetActorValuePercentage',lambda av:1.0)
        env['PO3_SKSEFunctions']=NS(IsPowerAttacking=wrap('PO3.IsPowerAttacking',lambda a:False))
        c.RefreshSyncStage()
        c.RefreshProcMagnitudes()
    m.script.clear();m.native.clear();m.autoreads.clear();m.cross=m.concat=m.logcalls=0
    if prepare_only:return c,t,player,target,weapon,clock,m,env,Glob
    c.OnWeaponHit(target,weapon,None,0)
    result=dict(scripted=sum(m.script.values()),native=sum(m.native.values()),cross_instance=m.cross,string_concats=m.concat,
                logging_calls=m.logcalls,identity=m.script['ESSBController.IsCurrentController'],glob_reads=sum(v for k,v in m.native.items() if k.startswith('GlobalVariable.Get')),
                scripts=dict(m.script),natives=dict(m.native),external_auto_reads=sum(m.autoreads.values()),auto_reads=dict(m.autoreads),log_messages=traces,runtime_tested=False)
    result['total']=result['scripted']+result['native']
    return result

if __name__=='__main__':
    folder=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'src'
    result=scenario(folder)
    print(json.dumps(result,indent=2))
