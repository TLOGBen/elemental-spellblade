"""Fix4 source-body regression checks. Native calls mocked; not an in-game VM test."""
import json, math, re
from pathlib import Path
from types import SimpleNamespace as NS
from papyrus_harness import Script, Array
ROOT = Path(__file__).resolve().parent.parent
settings = json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
class G:
    def __init__(self,v): self.v=v
    def GetValue(self): return self.v
    def GetValueInt(self): return int(self.v)
class Spell:
    def SetNthEffectMagnitude(self,i,v): self.magnitude=v
class Actor:
    def __init__(self): self.hits=[]
    def DoCombatSpellApply(self,spell,target): self.hits.append((spell,spell.magnitude,target))
    def GetActorValue(self,av): return 100.0
    def GetActorValuePercentage(self,av): return 1.0
    def GetFormID(self): return 123

def source(name): return ROOT/'src'/f'{name}.psc'
def close(a,b): assert math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8),(a,b)
checks=[]
# Execute real init bodies with every combination of the four lift arrays.
for mask in range(16):
    c=Script(source('ESSBController'))
    keep={}
    for i,(name,default) in enumerate([('LiftActor',None),('LiftDue',7.0),('LiftForce',3.0),('LiftDamage',8.0)]):
        if mask & (1<<i):
            c.fields[name]=Array([default]*8); keep[name]=c.fields[name]
    c.InitFixState()
    for name in ['LiftActor','LiftDue','LiftForce','LiftDamage']: assert len(c.fields[name])==8
    c.InitFixState()
    for name,arr in keep.items(): assert c.fields[name] is arr
checks.append('init: 16/16 partial lift states repaired; repeated init preserves existing arrays')
c=Script(source('ESSBController')); c.InitRegistry()
arrays={n:v for n,v in c.fields.items() if isinstance(v,Array)}
for missing in arrays:
    c.fields[missing]=None; c.InitRegistry()
    assert len(c.fields[missing])==len(arrays[missing]),missing
before={n:v for n,v in c.fields.items() if isinstance(v,Array)}
c.InitRegistry(); assert all(c.fields[n] is arr for n,arr in before.items())
checks.append(f'init: all {len(arrays)} controller arrays independently repaired; registry reentry preserves identity')
old=Script(ROOT/'.codex/pre-fix4-snapshot/src/ESSBController.psc')
old.fields['LiftActor']=Array([Actor()]*8); old.InitFixState()
assert old.fields['LiftDue'] is None
old.env['Utility']=NS(GetCurrentRealTime=lambda:0)
try: old.ArmUpdate()
except TypeError: pass
else: raise AssertionError('old partial-init failure not reproduced')
checks.append('old source reproduces None sibling access in ArmUpdate; new independent guards repair it')
c=Script(source('ESSBController')); scheduled=[]
c.overrides['RegisterForSingleUpdate']=scheduled.append
c.OnInit(); c.OnInit(); assert scheduled==[2.0,2.0] and c.LiftActor is None
c.overrides['Setup']=lambda:scheduled.append('setup')
c.OnUpdate(); assert scheduled[-1]=='setup'
checks.append('OnInit (including duplicate delivery) only schedules; initial OnUpdate calls Setup before array access')
# Wire actual source formulas and damage sinks; replace only game/native and node/environment factors.
player=Actor(); target=Actor(); c=Script(source('ESSBController'))
reactions=Script(source('ESSBReactions')); elem2=Script(source('ESSBElem2')); status=Script(source('ESSBStatus'))
nodes=NS(TreeOf=lambda e:e-1,Br=lambda *a:False,Rank=lambda *a:0,OmniMult=lambda *a:1.0,
         OpenStrikeMult=lambda *a:1.0)
elem=NS(FrozenExtraSeconds=lambda *a:0.0,OpenStrikeMult=lambda *a:1.0)
elem3=NS(TargetDamageMult=lambda *a:1.0,AstralDelay=lambda *a:2,PoisonTickMult=lambda *a:1.0,
         SpreadInterval=lambda *a:100,SpreadThreshold=lambda *a:999,PoisonTickHook=lambda *a:None)
env={'ESSBNodes':nodes,'ESSBReactions':reactions,'ESSBElem2':elem2,'ESSBElem3':elem3,'ESSBElem':elem,
     'ESSBNoForm':NS(TrueMult=lambda *a:1.0),'Utility':NS(GetCurrentRealTime=lambda:1.0,RandomFloat=lambda lo,hi:(lo+hi)/2)}
for script in [c,reactions,elem2,status]: script.env.update(env)
elem2.overrides['TargetDamageMult']=lambda *a:1.0
for name,value in [('GLevel',1.05),('GetDamageMult',1.0),('GetHitMult',1.0),('GetBloodHitMult',1.0),('IsVIPTarget',False)]:
    c.overrides[name]=lambda *a,v=value:v
c.overrides.update(ThePlayer=lambda:player,LogThrottled=lambda *a:None)
c.fields.update(ElementDamageMin=Array([v[0] for v in settings['element_damage'].values()]),
                ElementDamageMax=Array([v[1] for v in settings['element_damage'].values()]),
                PoisonDotK=G(settings['poison_dot_k']),BleedDotK=G(settings['bleed_dot_k']),
                BaseDamageMult=G(1.0),DebugLevel=G(0),ReactSpells=Array([Spell() for _ in range(11)]),
                HitNormalSpells=Array([Spell() for _ in range(11)]),HitPowerSpells=Array([Spell() for _ in range(11)]),
                TrueSpell=Spell(),UtilSpells=Array([Spell() for _ in range(8)]))
for i,(name,(lo,hi)) in enumerate(settings['element_damage'].items(),1):
    close(reactions.BaseMin(c,i),lo);close(reactions.BaseMax(c,i),hi)
    for mult in [1.0,2.5]:
        c.BaseDamageMult.v=mult
        for power in [False,True]:
            c.ApplyProc(target,i,power,False,False)
            close(player.hits[-1][1],(lo+hi)/2*(1.5 if power else 1)*1.05*mult)
        c.ApplyDamage(i,reactions.ReactDamage(c,i,2.0),target)
        close(player.hits[-1][1],hi*2*1.05*mult)
checks.append('11/11 elements: real ApplyProc normal/power and ReactDamage -> ApplyDamage -> Raw scale once at M=1 and 2.5')
for mult in [1.0,2.5]:
    c.BaseDamageMult.v=mult
    c.ApplyDamageRaw(1,10.0,target);close(player.hits[-1][1],10.0)
    c.ApplyTrueDamage(10.0,target,11,False);close(player.hits[-1][1],10.5)
    c.ApplyTrueDamage(10.0,target,10,False);close(player.hits[-1][1],10.5*mult)
    c.ApplyBleedDrain(target,0.3);close(player.hits[-1][1],0.3)
    s=Script(source('ESSBStatus'),env);s.fields.update(Ctl=c,Holder=target)
    s.InitRings();s.BleedRing[0]=1;s.PoisonRing[0]=1
    start=len(player.hits)
    for _ in range(7):s.Tick()
    hits=player.hits[start:]
    bleed=[v for sp,v,t in hits if sp is c.ReactSpells[5]]
    poison=[v for sp,v,t in hits if sp is c.ReactSpells[7]]
    assert len(bleed)==5 and len(poison)==6,(bleed,poison)
    for v in bleed:close(v,1.2*mult)
    for v in poison:close(v,2.0*mult)
checks.append('real Status.Tick: bleed 1.2 x 5 ticks, poison 2.0 x 6 ticks; M=2.5 scales once; durations unchanged')
checks.append('raw overheat / noform true / current-health bleed drain unscaled; B-derived astral true scales once')
# EndBlood must settle unscaled remaining bleed, then enter the choke point once.
elem.SignatureMult=lambda *a:1.0
c.overrides.update(Leech=lambda *a:None,GetBloodLeechRatio=lambda:0.05)
for mult in [1.0,2.5]:
    c.BaseDamageMult.v=mult
    s=Script(source('ESSBStatus'),env);s.fields.update(Ctl=c,Holder=target);s.InitRings();s.BleedRing[0]=1
    remaining=s.BleedRemaining(elem2.BleedPerLayer(c))
    close(remaining,1.2/1.05*5)
    reactions.EndBlood(c,target,s,1.0,player)
    close(player.hits[-1][1],(remaining+100*0.10)*1.05*mult)
checks.append('real EndBlood: remaining-bleed uses the same BleedDotK, no stored multiplier, one final application')
# Grep-level complete list of active source producers and native delivery functions.
build=(ROOT/'build_v03.py').read_text(encoding='utf-8')
active=re.search(r'SCRIPTS = (\[.*?\])',build,re.S)[1]
import ast
active=ast.literal_eval(active)
rows=[]; reads=[]
for name in active:
    scope=''
    for line_no,line in enumerate(source(name).read_text(encoding='utf-8').splitlines(),1):
        decl=re.match(r'^(?:\w+(?:\[\])? )?(Function|Event) (\w+)\(',line)
        if decl:scope=decl[2];continue
        code=line.split(';')[0].strip()
        if not code:continue
        if 'BaseDamageMult.GetValue()' in code:reads.append((name,scope,line_no))
        if re.search(r'\b(BaseMax|BaseMin|RollBase|BleedPerLayer|ApplyProc|ApplyDamage|ApplyDamageRaw|ApplyTrueDamage|DoCombatSpellApply)\(',code) or re.search(r'(PoisonDotK|BleedDotK)\.GetValue',code):
            rows.append({'file':f'src/{name}.psc','function':scope,'line':line_no,'code':code})
assert {(n,f) for n,f,_ in reads}=={('ESSBController',f) for f in ['ApplyProc','ApplyDamage','ApplyTrueDamage']}
assert len(reads)==3
raw=[r for r in rows if re.search(r'\bApplyDamageRaw\(',r['code'])]
assert {r['function'] for r in raw}=={'ApplyDamage','AddSelf'}
assert all(r['file']=='src/ESSBController.psc' for r in rows if 'DoCombatSpellApply(' in r['code'])
checks.append('static: exactly 3 multiplier reads, Raw callers limited to ApplyDamage and overheat AddSelf; native spell delivery centralized')
result={'checks':checks,'multiplier_reads':reads,'callsites':rows,'runtime_validation':False}
(ROOT/'build/fix4-offline-proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for check in checks:print('OK:',check)
print(f'PROOF ok: {len(checks)} groups; {len(rows)} call sites inventoried; no in-game validation claimed')
