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

def legacy_src():
    # Round 24 (N5): the reaction bodies these checks exercise (WetSlow, FlowPercent's neighbours, the burst lines) moved
    # into the DLL; they run on the scripts round 23 shipped, which build/fix24_history.py ties to today's (declared
    # changes only), as rounds 22 / 23 did for the older verifiers.
    import sys
    sys.path.insert(0,str(ROOT/'build'))
    import fix24_history
    return fix24_history.legacy_source()


def r24_src():
    # Round 25 (N6): 長流 (FlowPercent) moved into the DLL timer (Timer.h FlowFraction, tested by native/tests/timer_test.cpp
    # against build/fix25_reference.py); the Papyrus value checks run on the scripts round 24 shipped, which
    # build/fix25_history.py ties to today's (declared changes only).
    import sys
    sys.path.insert(0,str(ROOT/'build'))
    import fix25_history
    return fix25_history.legacy_source()


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
                rows.append(dict(tree=t['id'],tree_index=t['index'],route=r['index'],route_name=r['name'],tier=n['index'],tier_name=n['name'],old=n['main_original'],new=n['main'],status=n['balance_class'],reason=n['balance_reason'],status_v04=NODES[t['id'],n['main_label']][0],site=NODES[t['id'],n['main_label']][1]))
    assert len(rows)==195
    # Round 21 (v0.4): every ESSBNodes.Pct call is bound to the node it reads BY v0.4 NAME, through the identity
    # table (build/fix21_identity.py resolves each `; @node` read, element-skeleton reads expanded per tree), not by
    # a (tree, route, tier) literal: a Pct over a read of slot X counts for the node that sits at X in v0.4.
    import fix21_identity as ident
    idplan=ident.load_plan();by_pos,by_name=ident.index(idplan);table,_=ident.statuses(by_name)
    reads,errs=ident.check_papyrus(ident.scripts(),by_pos,by_name,table,[x['id'] for x in idplan['trees']])
    assert not errs,errs[:5]
    per_line=collections.defaultdict(list)
    for rd in reads:per_line[rd['file'],rd['line']].append(rd)
    tree_of={x['id']:x['index'] for x in idplan['trees']}
    def pos(node):
        n=by_name[node];return (tree_of[n['tree']],n['route'],n['tier'])
    mapped=collections.defaultdict(list)
    pct_sites=0
    for name,text in sorted(ident.scripts().items()):
        body=ident.strip_docs(text);fn='';assigned={}
        for number,line in ident.logical_lines(body):
            code,_=ident.split_comment(line)
            m=ident.FUNC_RE.match(code)
            if m:fn=m.group(1);assigned={}
            here=per_line.get((name,number),[])
            v=re.match(r'\s*(?:Int|Float)?\s*(\w+)\s*=.*\bRank\(',code)
            if v and here:assigned[v[1]]=here
            for pm in re.finditer(r'\bESSBNodes\.Pct\(',code):
                if fn=='Pct':continue
                args,_=ident.call_args(code,pm.end()-1)
                base=float(args[2]);first=args[1]
                if re.search(r'\bRank\(',first):
                    k=len(list(ident.CALL_RE.finditer(ident.strip_strings(code[:pm.end()]))))   # reads before this Pct's own Rank
                    src=[here[k]]
                else:
                    src=assigned.get(first.strip());assert src,(name,number,'Pct over an unknown rank',first)
                for rd in src:
                    for node in rd['nodes']:mapped[pos(node)].append((f'src/{name}:{fn}',number,base))
                pct_sites+=1
    papyrus_sites=pct_sites
    # Round 20 (N2): the sustain adept / master element lines are applied by the DLL at hit time
    # (native/include/HitMath.h NodeSum over the generated node::kProcAdept / kProcMaster tables). Round 22 deleted the
    # Papyrus mirror (ESSBController.NativeNodeSum, with the difference patch), so the DLL site is the only binding.
    hitmath=(ROOT/'native/include/HitMath.h').read_text(encoding='utf-8')
    nodesum=re.search(r'constexpr float NodeSum\(.*?\n\}',hitmath,re.S)[0]
    manifest=(ROOT/'native/include/ManifestData.h').read_text(encoding='utf-8')
    for table_name,tier in (('kProcAdept',1),('kProcMaster',3)):
        assert f'Pct(t, nodes.Rank(node::{table_name}[element]), 0.01f)' in nodesum,(table_name,'DLL site')
        cells=re.search(r'NodeId '+table_name+r'\[12\] = \{(.*?)\};',manifest)[1]
        for tr in range(11):
            if tr==8:
                continue  # water: its sustain adept / master lines are recovery, not proc damage
            assert '{'+f'{tr}, 0, {tier}'+'}' in cells,(table_name,tr)
            mapped[tr,0,tier].append((f'native/include/HitMath.h:NodeSum[{table_name}]',hitmath[:hitmath.index(nodesum)].count('\n')+1,.01))
            pct_sites+=1
    # Round 22 (N3): the status layer's percentage main lines are the DLL's too. Every Pct(t, nodes.Rank(node::X), base)
    # in native/include/Status.h and native/src/Plugin.cpp is bound, through fix19_native's NODE_IDENTITY (constants)
    # and ARRAY_IDENTITY (per-element tables, node::kX[kElement] or [element] = every tree that has the line), to the
    # v0.4 main line it reads, with its base coefficient (a literal, or an n3:: constant of Status.h).
    sys.path.insert(0,str(ROOT/'build'))
    import fix19_native
    status_h=(ROOT/'native/include/Status.h').read_text(encoding='utf-8')
    n3={m[1]:float(m[2]) for m in re.finditer(r'inline constexpr float (k\w+) = ([\d.]+)f;',status_h)}
    # Round 24 (N5): the reaction bodies' per-point constants (namespace n5) are coefficients too.
    reactions_h=(ROOT/'native/include/Reactions.h').read_text(encoding='utf-8')
    n3.update({m[1]:float(m[2]) for m in re.finditer(r'inline constexpr float (k\w+) = ([\d.]+)f;',reactions_h)})
    elements={n:i for i,n in enumerate(['kFire','kFrost','kLightning','kEarth','kWind','kBlood','kDivine','kPoison','kWater','kDarkness','kAstral'],1)}
    dll_sites=0
    # Round 24 (N5): the reaction bodies' percentage lines (the burst main lines) moved from Papyrus into Reactions.h; the
    # no-form true-damage line's Papyrus copy (ESSBNoForm.TrueMult) went with the Papyrus true damage, HitMath.h is its site.
    for rel in ('native/include/Status.h','native/src/Plugin.cpp','native/include/Reactions.h','native/include/HitMath.h'):
        text=(ROOT/rel).read_text(encoding='utf-8')
        if rel.endswith('Reactions.h'):
            text=text.replace('Pct(Rank(','Pct(t, nodes.Rank(')   # the Bodies member Pct(rank, perPoint) is essb::Pct(T(), rank, perPoint)
        for m in re.finditer(r'Pct\(\s*[\w.]+,\s*nodes\.Rank\(\s*(?:essb::)?node::(k\w+)(?:\[\s*(?:essb::)?(\w+)\s*\])?\s*\),\s*([^)]+?)\s*\)',text):
            name,index,expr=m[1],m[2],m[3].strip()
            base=float(expr[:-1]) if re.fullmatch(r'[\d.]+f',expr) else n3[expr.removeprefix('essb::').removeprefix('n3::').removeprefix('n5::')]
            if name in fix19_native.NODE_IDENTITY:
                cells=[fix19_native.NODE_IDENTITY[name]]
            else:
                table=fix19_native.ARRAY_IDENTITY[name]
                cells=[table[elements[index]]] if index in elements else [c for c in table if c]
            line=text[:m.start()].count('\n')+1
            for cell in cells:
                node=by_name[cell]
                if node['kind']!='main':
                    continue   # branch nodes carry no per-point coefficient
                mapped[pos(cell)].append((f'{rel}:{name}',line,base))
            dll_sites+=1
            pct_sites+=1
    # Round 24 (N5): the Papyrus sites left are the ones Papyrus still owns (the reaction bodies are the DLL's); the total
    # stays at 30 or more and the DLL must carry what moved.
    assert papyrus_sites>=5 and dll_sites>=20 and pct_sites>=30,(papyrus_sites,dll_sites,pct_sites)
    scaled={}
    for row in rows:
        k=row['tree_index'],row['route'],row['tier']
        if row['status']=='SCALED' and row['status_v04'].startswith('LATER'):
            # v0.4 node owned by a later slice: record only (ruling R4), so nothing may read it yet.
            assert k not in mapped,('LATER node has a Pct site',row,mapped[k]);continue
        if row['status']=='SCALED':
            expected=float(re.search(r'\+([\d.]+)%／點',row['old'])[1])/100
            assert k in mapped,('unbound',row)
            assert any(math.isclose(a[2],expected) for a in mapped[k]),('coefficient',row,mapped[k])
            row['code_sites']=mapped[k];scaled[k]=row
    assert set(mapped)==set(scaled),('extra Pct nodes',set(mapped)-set(scaled))
    # Round 24 review fix 4: the behaviour checks run on today's scripts wherever the function still exists (Pct,
    # FlowPercent, ApplyUtil's slow cap); only WetSlow, deleted with the Papyrus bodies (the soaked slow is the DLL's,
    # HitMath.h SoakSlowPct, tested natively), still runs on the round-23 scripts.
    ctl=Ctl(settings);reg=make_scripts(ROOT/'src',ctl)
    for scale in [1,1.5,3,5]:
        ctl.NodeScale.x=scale
        for rank in [0,1,15]:
            for base in [.002,.005,.01,.02,.03,.05]:assert math.isclose(reg['ESSBNodes'].Pct(ctl,rank,base),scale*rank*base)
    # Round 21 (outcome 3): ESSBNodes.RefreshWeaponPercent is gone with the v0.3 weapon-damage entry points
    # (純武藝新手／戰意／淬火); v0.4 has no main line that needs a script-scaled PERK entry point.
    assert not re.search(r'RefreshWeaponPercent\s*\(',''.join(ident.split_comment(l)[0] for s in ident.scripts().values() for l in s.splitlines()))
    # Round 20 (N2): the v0.3 破魔 main line (ESSBNoForm.OnManaBreak) was replaced by the DLL's v0.4 siphon /
    # small dispel / dispel; their formulas are tested natively (hit_pipeline_test groups A0/A), not here.
    cases='retired in round 20: no-form siphon and dispel moved to the DLL (native groups A0/A)'
    # Actual water helper, including same bonuses at all MCM scales.
    water=[]
    for scale in [1,3,5]:
        ctl=Ctl(settings);ctl.NodeScale.x=scale;reg=make_scripts(r24_src(),ctl)
        value=reg['ESSBElem3'].FlowPercent(ctl);assert math.isclose(value,.08)
        old=make_scripts(legacy_src(),Ctl(settings));assert old['ESSBElem3'].WetSlow(ctl)==settings['water_wet_slow_pct']
        water.append(dict(node_scale=scale,regen_pct=value*100,health_300=value*300,health_500=value*500))
    # Round 20 (N2): GetHitMult no longer exists. The proc multiplier is the DLL's (native group A) plus the
    # Papyrus difference patch for target-side terms, checked against the same reference by build/fix20_verify.py.
    multipliers=envelopes='retired in round 20: see build/fix20-check.json (difference patch vs reference)'
    # Ensure the scale applies to engine entry points too, without changing their conditions/count.
    by={(t['id'],r['index'],n['index']):n for t in plan['trees'] for r in t['routes'] for n in r['tiers']}
    # Identity and text independent ESP readback.
    records,meta=build_v03.read_plugin(build_v03.OUT/build_v03.PLUGIN);rec={r.edid:r for r in records}
    written=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf-8'));baseline=json.loads((ROOT/'.codex/pre-fix6-snapshot/v03-formids.json').read_text(encoding='utf-8'))['records']
    assert all(build_v03.state_schema.stable_identity(k,written['records'].get(k),v) for k,v in baseline.items())
    added={k:v for k,v in written['records'].items() if k not in baseline and k not in build_v03.SCHEMA_STUBS and k not in build_v03.GUARD_WINDOW_EDIDS and k not in (build_v03.hit18.new_edids(build_v03) | build_v03.hit19.NEW_EDIDS | set(build_v03.tree_v04.NEW_PERK_EDIDS)) and not k.startswith('ESSB_Mult')}
    assert len(added)==12 and all(v['type']=='GLOB' if 'type' in v else v['sig']=='GLOB' for v in added.values())
    assert all(int(v['id'],16)>max(int(o['id'],16) for o in baseline.values()) for v in added.values())
    for (tree,r,t),n in by.items():
        for rank in range(1,16):
            desc=rec[f'ESSB_P_{tree}_{r}_{t}_M{rank}'].d['DESC'].rstrip(b'\0').decode('utf-8')
            assert desc==f'第 {rank}/15 點：'+n['main']
        for b in n['branches']:
            desc=rec[f'ESSB_P_{tree}_{r}_{t}_B{b["slot"]+1}'].d['DESC'].rstrip(b'\0').decode('utf-8')
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
    print(f'FIX6 ok: {len(rows)} classified; {len(scaled)} scaled nodes bound; 12 appended GLOBs; existing non-quest IDs unchanged; baseline={len(baseline)}; Papyrus formulas / DLL NodeSum sites + PERK text + shared slow cap checked')
    return report
if __name__=='__main__':run()
