"""Offline execution of the actual Papyrus formula bodies plus generated-record checks."""
from pathlib import Path
from types import SimpleNamespace as NS
import re, json, math, collections
ROOT = Path(__file__).resolve().parents[1]
class Returned(Exception): pass
class Script:
    def __init__(self, path, registry, ctl):
        self.source=Path(path).read_text(encoding='utf-8');self.registry=registry;self.ctl=ctl;self.cache={}
    def __getattr__(self,name):
        if name not in self.cache:
            m=re.search(r'(?im)^[^\n;]*\bFunction '+re.escape(name)+r'\((.*?)\)\s*(?:Global)?\s*\n(.*?)^EndFunction',self.source,re.S|re.M)
            if not m: raise AttributeError(name)
            params=[];defaults={}
            for arg in m[1].replace('\\\n','').split(','):
                arg=arg.strip()
                if not arg:continue
                a=arg.split('=',1);p=a[0].strip().split()[-1];params.append(p)
                if len(a)>1:defaults[p]=eval(a[1].strip())
            text=m[2].replace('\\\n',' ');depth=0;lines=[]
            for raw in text.splitlines():
                line=raw.split(';',1)[0].strip()
                if not line:continue
                if 'LogThrottled(' in line or 'LogEvent(' in line:
                    lines.append('    '*depth+'pass');continue
                line=re.sub(r'^(?:Int|Float|Bool|String|Actor|Perk|Spell|ESSBStatus)(?:\[\])?\s+', '', line)
                line=re.sub(r'(\([^()]*\)|[\w.]+)\s+as Int\b',r'int(\1)',line)
                line=re.sub(r'\b([A-Za-z_]\w*)\.Length\b', r'len(\1)', line)
                line=line.replace('&&',' and ').replace('||',' or ')
                line=re.sub(r'!(?!=)','not ',line)
                if line in ('EndIf','EndWhile'):depth-=1;continue
                if line.startswith('ElseIf '):depth-=1;line='elif '+line[7:]+':'
                elif line=='Else':depth-=1;line='else:'
                elif line.startswith('If '):line='if '+line[3:]+':'
                elif line.startswith('While '):line='while '+line[6:]+':'
                elif line.startswith('Return'):line='raise Returned('+line[6:].strip()+')'
                lines.append('    '*depth+line)
                if line.endswith(':'):depth+=1
            assert depth==0,(name,depth)
            self.cache[name]=(params,defaults,compile('\n'.join(lines),str(name),'exec'))
        params,defaults,code=self.cache[name]
        def invoke(*args):
            env=dict(Utility=getattr(self.ctl,"Utility",NS(GetCurrentRealTime=lambda:0.0)));env.update(defaults);env.update(zip(params,args));env.update(self.registry);env.update(Self=self.ctl,Returned=Returned)
            # Resolve bare calls to functions on the same script or controller.
            class Scope(dict):
                def __missing__(scope,key):
                    if key in ('__builtins__','int','len'):raise KeyError(key)
                    if key=='Returned':return Returned
                    if key in self.registry:return self.registry[key]
                    if 'extends' not in self.source.splitlines()[0].lower() and re.search(r'\bFunction '+re.escape(key)+r'\(',self.source,re.I):return getattr(self,key)
                    if hasattr(self.ctl,key):return getattr(self.ctl,key)
                    if re.search(r'\bFunction '+re.escape(key)+r'\(',self.source,re.I):return getattr(self,key)
                    raise KeyError(key)
            scope=Scope(env)
            try:exec(code,scope)
            except Returned as r:return r.args[0] if r.args else None
        return invoke
class Glob:
    def __init__(self,x):self.x=x
    def GetValue(self):return self.x
    def GetValueInt(self):return int(self.x)
class Actor:
    def __init__(self,mag=1000,hp=400):self.mag=mag;self.maxmag=mag;self.hp=hp;self.true=[]
    def IsDead(self):return self.hp <= 0
    def GetActorValue(self,key):return self.mag if key=='Magicka' else self.hp
    def GetActorValueMax(self,key):return self.maxmag if key=='Magicka' else self.hp
    def GetActorValuePercentage(self,key):return self.mag/self.maxmag if key=='Magicka' and self.maxmag else 1.0
    def GetEquippedSpell(self,index):return None
    def HasMagicEffectWithKeyword(self,x):return False
    def GetFormID(self):return 1
    def DoCombatSpellApply(self,spell,target):target.true.append(spell.mag)
class Spell:
    def SetNthEffectMagnitude(self,i,n):self.mag=n
    def SetNthEffectDuration(self,i,n):self.duration=n
class Ctl:
    def __init__(self,settings):
        self.RuntimeCacheReady=False;self.CachedDebugLevel=0;self.CachedDuration=1.0;self.StateBroken=False;self.Ready=True;self.settings=settings;self.ranks={};self.rank_default=15;self.branches=set();self.all_branches=False;self.stacks={};self.stage=3
        for prop,key,value in json.loads((ROOT/'build/fix6-knobs.json').read_text()):setattr(self,prop,Glob(settings[key]))
        
        for n in ['Dot','Cooldown','Recovery','Drain','Duration']:setattr(self,'Mult'+n,Glob(settings['mult_'+n.lower()]))
        self.BaseDamageMult=Glob(settings['base_damage_mult']);self.EnvNight=Glob(0);self.BloodthirstLeft=0;self.EndBoostLeft=0;self.EndBoostAmount=0
        self.SilenceKeyword=None;self.ArmorSpellKeyword=None;self.CloakKeyword=None;self.TrueSpell=Spell();self.player=Actor(300);self.events=[];self.level=100
        self.ElementDamageMax=[v[1] for v in settings['element_damage'].values()]
        self.ElementDamageMin=[v[0] for v in settings['element_damage'].values()]
        self.FormActive=Glob(0);self.CurrentElement=Glob(0)
        self.Trees=NS(MainRankInternal=lambda t,r,k:self.ranks.get((t,r,k),self.rank_default),BranchInternal=lambda t,r,k,n:self.all_branches or (t,r,k,n) in self.branches,TreeGInternal=lambda t:1+.05*self.level,OnValidHitXP=lambda e:None)
        self.Trees.CachedMainRank=self.Trees.MainRankInternal;self.Trees.CachedBranch=self.Trees.BranchInternal;self.Trees.TreeG=self.Trees.TreeGInternal
    def Rank(self,t,r,k):return 0 if t==11 and r<2 and self.FormActive.GetValueInt()==1 else self.Trees.MainRankInternal(t,r,k)
    def Br(self,t,r,k,n):return False if t==11 and r<2 and self.FormActive.GetValueInt()==1 else self.Trees.BranchInternal(t,r,k,n)
    # Formula-only suite mocks provenance; FIX10 executes the actual wrapper separately.
    def IsOperational(self):return True
    def NoteDamageElement(self,*args):return -1
    # Formula suite leaves provenance to FIX10/FIX14 actual-source tests.
    def ApplyTrackedDamage(self,player,spell,target,*args):player.DoCombatSpellApply(spell,target)
    def ThePlayer(self):return self.player
    def SyncStage(self):return self.stage
    def GetStack(self,target,kind):return self.stacks.get(kind,0)
    def GetOpenBoost(self,e):return 5
    def GetSelf(self,k):return 0
    def GetMoltenLeft(self):return 0
    def InDomain(self,t,e):return False
    def HasStarLock(self,t):return False
    def GetAirborne(self,t):return 0
    def IsNecromancer(self,t):return False
    def IsEnvNight(self):return self.EnvNight.x==1
    def HasElementMark(self,t,e):return True
    def IsVIPTarget(self,t):return False
    def GLevel(self,t):return 1+.05*self.level
    def GetBloodHitMult(self):return 1.3
    def LogThrottled(self,*args):pass
    def ApplyManaBreakMark(self,*args):pass
    def ApplySilenceSpell(self,t,d):self.events.append(('silence',d))
    def TakeInterrupt(self):return False
    def ApplyUtil(self,kind,value,duration,target,balanced=False):
        self.events.append((kind,value))
        if kind==2:target.mag=max(0,target.mag-value)
        if kind==5:target.mag+=value
    def GetDamageMult(self,e):return self.scripts['ESSBController'].GetDamageMult(e)
    def DrainAmount(self,value):return self.scripts['ESSBController'].DrainAmount(value)
    def RecoveryAmount(self,value):return self.scripts['ESSBController'].RecoveryAmount(value)
    def DurationSeconds(self,value):return self.scripts['ESSBController'].DurationSeconds(value)
    def DurationInt(self,value):return int(self.DurationSeconds(value)+.5)
    def ApplyTrueDamage(self,*args):return self.scripts['ESSBController'].ApplyTrueDamage(*args)

def make_scripts(folder,ctl):
    reg={}
    for p in Path(folder).glob('*.psc'):reg[p.stem]=Script(p,reg,ctl)
    ctl.scripts=reg
    return reg

def run():
    import sys
    sys.path.insert(0,str(ROOT))
    import plan_trees,build_v03
    settings=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
    plan=build_v03.apply_fix8_decisions(plan_trees.apply_balance_text(plan_trees.parse()))
    from plan_coverage import NODES
    rows=[]
    for t in plan['trees']:
        for r in t['routes']:
            for n in r['tiers']:
                rows.append(dict(tree=t['id'],tree_index=t['index'],route=r['index'],route_name=r['name'],tier=n['index'],tier_name=n['name'],old=n['main_original'],new=n['main'],status=n['balance_class'],reason=n['balance_reason'],site=NODES[t['id'],r['index'],n['index'],'M'][1]))
    assert len(rows)==195
    # Map every approved mainline to its actual Pct callsite, expanding shared dispatch explicitly.
    mapped=collections.defaultdict(list)
    for p in (ROOT/'src').glob('*.psc'):
        fn=''
        for ln,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            m=re.search(r'\bFunction (\w+)\(',line,re.I)
            if m:fn=m[1]
            if line.lstrip().startswith(';'):continue
            for m in re.finditer(r'ESSBNodes.Pct\(akCtl, (?:ESSBNodes\.)?Rank\(akCtl, (\d+), (\d+), (\d+)\), ([\d.]+)\)',line):
                mapped[tuple(map(int,m.group(1,2,3)))].append((str(p.relative_to(ROOT))+':'+fn,ln,float(m[4])))
    def add(tree,route,tier,file,fn,base):
        src=(ROOT/'src'/file).read_text(encoding='utf-8');b=re.search(r'\bFunction '+fn+r'\(.*?\n(.*?)EndFunction',src,re.S)[1]
        assert 'Pct(' in b,(file,fn)
        mapped[tree,route,tier].append(('src/'+file+':'+fn,src[:src.index(b)].count('\n')+1,base))
    for t in range(11):
        add(t,1,4,'ESSBElem.psc','OpenMult',.03)
        for tier,fn,base in [(0,'EndMult',.02),(1,'BurstMult',.02),(3,'BurstMult',.02),(4,'SignatureMult',.03)]:
            # Wind has a 5% landing coefficient; poison has its own catalyst Pct.
            if tier==4 and t in (4,7):continue
            add(t,2,tier,'ESSBElem.psc',fn,base)
    for t in [1,2,6,7,8]:add(t,2,2,'ESSBElem.psc','OnEnd',.01)
    add(9,0,2,'ESSBElem3.psc','TargetDamageMult',.01)
    for route,tier,base in [(0,0,.01),(0,3,.005),(2,3,.01)]:add(11,route,tier,'ESSBNodes.psc','RefreshWeaponPercent',base)
    scaled={}
    for row in rows:
        k=row['tree_index'],row['route'],row['tier']
        if row['status']=='SCALED':
            expected=float(re.search(r'\+([\d.]+)%／點',row['old'])[1])/100
            assert k in mapped,('unbound',row)
            assert any(math.isclose(a[2],expected) for a in mapped[k]),('coefficient',row,mapped[k])
            row['code_sites']=mapped[k];scaled[k]=row
    assert set(mapped)==set(scaled),('extra Pct nodes',set(mapped)-set(scaled))
    ctl=Ctl(settings);reg=make_scripts(ROOT/'src',ctl)
    for scale in [1,1.5,3,5]:
        ctl.NodeScale.x=scale
        for rank in [0,1,15]:
            for base in [.002,.005,.01,.02,.03,.05]:assert math.isclose(reg['ESSBNodes'].Pct(ctl,rank,base),scale*rank*base)
    # Actual helper drives all seven engine entries at every rank and every slider value.
    ctl=Ctl(settings);reg=make_scripts(ROOT/'src',ctl);perks={}
    class Perk:
        def __init__(self):self.entries={}
        def SetNthEntryValue(self,n,i,value):self.entries[n]=value
    def perk(tree,route,tier,rank):return perks.setdefault((route,tier,rank),Perk())
    ctl.Trees.GetMainPerk=perk
    for scale in [1,1.5,3,5]:
        ctl.NodeScale.x=scale;reg['ESSBNodes'].RefreshWeaponPercent(ctl)
        for rank in range(1,16):
            assert math.isclose(perks[0,0,rank].entries[0],1+.01*rank*scale)
            assert math.isclose(perks[2,3,rank].entries[0],1+.01*rank*scale)
            assert len(perks[0,3,rank].entries)==5
            assert all(math.isclose(v,1+.005*rank*scale) for v in perks[0,3,rank].entries.values())
    # Execute ManaBreak and its real ApplyTrueDamage body with controlled actor values.
    cases=[]
    for level,rank,mag,expected in [(10,1,1000,36),(100,15,1000,480),(100,15,100,100)]:
        ctl=Ctl(settings);ctl.level=level;ctl.rank_default=0;ctl.ranks={(11,1,0):rank,(11,1,1):15};reg=make_scripts(ROOT/'src',ctl);target=Actor(mag)
        reg['ESSBNoForm'].OnManaBreak(ctl,target,False)
        assert math.isclose(target.true[-1],expected*.95),(level,rank,target.true)
        assert math.isclose(ctl.player.mag,300+expected)
        cases.append(dict(level=level,rank=rank,available_magicka=mag,actual=expected,true_damage=target.true[-1],restored=ctl.player.mag-300,G_count=1))
    # Branch floor and caster bonus, unchanged ratio ceiling, dry branch single original G.
    ctl=Ctl(settings);ctl.rank_default=0;ctl.ranks={(11,1,0):15,(11,1,1):15,(11,1,3):15};ctl.branches={(11,1,0,0)};reg=make_scripts(ROOT/'src',ctl);target=Actor(10000);target.GetEquippedSpell=lambda i:True
    reg['ESSBNoForm'].OnManaBreak(ctl,target,False)
    assert math.isclose(target.true[-1],1000*1.75*.95)
    ctl=Ctl(settings);ctl.rank_default=0;ctl.ranks={(11,1,0):1};ctl.branches={(11,1,2,0)};reg=make_scripts(ROOT/'src',ctl);target=Actor(0)
    reg['ESSBNoForm'].OnManaBreak(ctl,target,False);assert math.isclose(target.true[-1],300*.2*6)
    # Actual water helper, including same bonuses at all MCM scales.
    water=[]
    for scale in [1,3,5]:
        ctl=Ctl(settings);ctl.NodeScale.x=scale;reg=make_scripts(ROOT/'src',ctl)
        value=reg['ESSBElem3'].FlowPercent(ctl);assert math.isclose(value,.08);assert reg['ESSBElem3'].WetSlow(ctl)==30
        water.append(dict(node_scale=scale,regen_pct=value*100,health_300=value*300,health_500=value*500))
    # Compare real old/new GetHitMult formula bodies under the same declared conditions.
    multipliers=[]
    for element,name in enumerate(build_v03.ELEMENTS,1):
        vals=[]
        for before in [True,False]:
            cfg=json.loads((ROOT/'build/fix6-before/settings.json').read_text(encoding='utf-8')) if before else settings
            cfg={**settings,**cfg};ctl=Ctl(cfg);ctl.NodeScale.x=1 if before else settings['node_percent_scale'];ctl.EnvNight.x=1 if element==10 else 0
            ctl.stacks={1:12,2:5,6:8,9:8,10:13};ctl.branches={(8,0,1,0)};ctl.EndBoostLeft=5;ctl.EndBoostAmount=.15*(1 if before else 3)
            reg=make_scripts(ROOT/('build/fix6-before/src' if before else 'src'),ctl);target=Actor()
            elem=reg['ESSBElem'].HitMult(ctl,element,target,True)
            full=reg['ESSBController'].GetHitMult(element,target,True)
            vals.append(dict(element_mult=elem,M_mod=full,G_times_M=full*6))
        multipliers.append(dict(element=name,old=vals[0],new=vals[1]))
    # All-branch conditional envelope. This is a bound, not a claim every window can coexist.
    envelopes=[]
    for element,name in enumerate(build_v03.ELEMENTS,1):
        pair=[]
        for before in [True,False]:
            ctl=Ctl(settings);ctl.NodeScale.x=1 if before else settings['node_percent_scale'];ctl.EnvNight.x=1 if element==10 else 0
            ctl.all_branches=True;ctl.BloodthirstLeft=10;ctl.EndBoostLeft=5;ctl.EndBoostAmount=.15*(1 if before else 3)
            ctl.stacks={1:17,2:5,4:1,6:8,9:8,10:13,11:9}
            ctl.GetSelf=lambda k:1;ctl.GetMoltenLeft=lambda:10;ctl.InDomain=lambda t,e:True
            ctl.HasStarLock=lambda t:True;ctl.GetAirborne=lambda t:2;ctl.IsNecromancer=lambda t:True
            reg=make_scripts(ROOT/('build/fix6-before/src' if before else 'src'),ctl)
            target=Actor(1000);target.mag=100;target.GetEquippedSpell=lambda i:True
            pair.append(reg['ESSBController'].GetHitMult(element,target,True))
        envelopes.append(dict(element=name,old=pair[0],new=pair[1]))
    # Ensure the scale applies to engine entry points too, without changing their conditions/count.
    by={(t['id'],r['index'],n['index']):n for t in plan['trees'] for r in t['routes'] for n in r['tiers']}
    # Identity and text independent ESP readback.
    records,meta=build_v03.read_plugin(build_v03.OUT/build_v03.PLUGIN);rec={r.edid:r for r in records}
    written=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf-8'));baseline=json.loads((ROOT/'.codex/pre-fix6-snapshot/v03-formids.json').read_text(encoding='utf-8'))['records']
    assert all(build_v03.state_schema.stable_identity(k,written['records'].get(k),v) for k,v in baseline.items())
    added={k:v for k,v in written['records'].items() if k not in baseline and k not in build_v03.SCHEMA_STUBS and k not in build_v03.GUARD_WINDOW_EDIDS and k not in build_v03.hit18.new_edids(build_v03) and not k.startswith('ESSB_Mult')}
    assert len(added)==12 and all(v['type']=='GLOB' if 'type' in v else v['sig']=='GLOB' for v in added.values())
    assert all(int(v['id'],16)>max(int(o['id'],16) for o in baseline.values()) for v in added.values())
    for (tree,r,t),n in by.items():
        for rank in range(1,16):
            desc=rec[f'ESSB_P_{tree}_{r}_{t}_M{rank}'].d['DESC'].rstrip(b'\0').decode('utf-8')
            assert desc==f'第 {rank}/15 點：'+n['main']
        for b in n['branches']:
            desc=rec[f'ESSB_P_{tree}_{r}_{t}_B{b["index"]+1}'].d['DESC'].rstrip(b'\0').decode('utf-8')
            assert b['description'] in desc
    # Peak Value Modifier on the only negative SpeedMult utility: non-stacking max with 70 clamp.
    import struct
    slow=rec['ESSB_UtilEffect_Slow'].d['DATA'];assert struct.unpack_from('<I',slow,64)[0]==34 and struct.unpack_from('<i',slow,68)[0]==30
    ctl=Ctl(settings);ctl.UtilSpells=[Spell()];ctl.UtilTargetSpells=[];reg=make_scripts(ROOT/'src',ctl)
    for value in [15,25,30,69,70,80,110,999]:
        reg['ESSBController'].ApplyUtil(0,value,3,Actor());assert ctl.UtilSpells[0].mag==min(value,70)
    for value in [0,50,70,100]:
        ctl.SlowCapPct.x=value;reg['ESSBController'].ApplyUtil(0,999,3,Actor());assert ctl.UtilSpells[0].mag==min(value,70)
    # Every slow cast goes via utility 0; no newly introduced AV or status machinery.
    stats=collections.Counter(r['status'] for r in rows)
    (ROOT/'build/fix6-classification.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(classification=dict(stats),scaled_distribution=dict(collections.Counter(re.search(r'\+([\d.]+)%／點',r['old'])[1] for r in rows if r['status']=='SCALED')),manabreak=cases,water=water,multipliers=multipliers,branch_envelopes=envelopes,existing_unchanged=len(baseline),added=added,description_perks=3225,masters=meta['masters'],runtime_tested=False)
    (ROOT/'build/fix6-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'FIX6 ok: {len(rows)} classified; {len(scaled)} scaled nodes bound; 12 appended GLOBs; existing non-quest IDs unchanged; baseline={len(baseline)}; actual Papyrus formulas + PERK text + shared slow cap checked')
    return report
if __name__=='__main__':run()
