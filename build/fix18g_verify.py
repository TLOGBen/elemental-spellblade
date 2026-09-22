"""Execute shipped tie PSC with native mocks; engine winner is NOT mocked as evidence."""
from types import SimpleNamespace as NS
import itertools,json,sys,struct
def run(b):
 sys.path.insert(0,str(b.WORK/'build'))
 from papyrus_harness import Script
 names=['ProbeAB','ProbeHit','ProbeMultiply','CrossA','CrossB','CrossA2','CrossB2','TieA','TieB','TieA2','TieB2']
 class G:
  def __init__(self,v=0):self.v=v
  def GetValue(self):return self.v
  def SetValue(self,v):self.v=v
 logs=[];held=set();spells=set();addorder=[]
 av={'AttackDamageMult':1.25}
 player=NS(HasPerk=lambda p:p in held,RemovePerk=lambda p:held.discard(p),AddPerk=lambda p:(held.add(p),addorder.append(p)),AddSpell=lambda p,*a:spells.add(p),RemoveSpell=lambda p:spells.discard(p),GetActorValue=lambda n:av.get(n,0),ForceActorValue=lambda n,v:av.update({n:v}),UnequipAll=lambda:None,GetItemCount=lambda p:1,EquipItem=lambda *a:None)
 globals={n:G() for n in ['Gate','Session','TieVariant','TieResult1','TieResult2','TieResult3','TieResult4']}
 env=dict(__execute_logs__=True,__papyrus_concat__=True,Game=NS(GetPlayer=lambda:player),Debug=NS(Trace=logs.append,Notification=lambda s:None),Utility=NS(Wait=lambda t:None))
 s=Script(b.WORK/'src/ESSBProbeSetup.psc',env);s.fields.update({n:n for n in names},**globals)
 s.fields.update({n:n for n in ['PreparePower','SecondPower','ThirdPower','FourthPower','CleanupPower','Meter','Dagger']})
 target=NS(AddSpell=lambda *a:True,RemoveSpell=lambda *a:None)
 s.fields['Bandit']=target
 s.overrides.update(PrepareBandit=lambda *a:True,SetupReady=lambda:True,DeleteBandit=lambda p:s.fields.update(Bandit=None))
 m=Script(b.WORK/'src/ESSBProbeMeter.psc',env);m.fields.update({n:n for n in names},**globals,Player=player)
 s.GrantPowers();assert 'FourthPower' in spells
 cases=[]
 patterns=[([1,2,1,2],'lower FormID'),([2,1,2,1],'higher FormID'),([1,1,2,2],'added to player first'),([2,2,1,1],'added to player last'),([3,3,3,3],'additive'),([1,1,1,1],'unresolved'),([1,2,2,1],'inconsistent'),([0,2,1,2],'need four')]
 for pattern,expected in patterns:assert expected in m.TieDecision(*pattern)
 expectedorders=[['TieA','TieB'],['TieA2','TieB2'],['TieB','TieA'],['TieB2','TieA2']]
 for v in range(1,5):
  addorder.clear();s.RunProbe(5);assert addorder==expectedorders[v-1]
  assert m.CurrentMode()==v+4 and globals['TieVariant'].v==v
  assert any('PROBE=4 variant='+str(v) in x for x in logs)
  m.fields['Mode']=v+4
  for dmg,a,bb,c,winner in [(5,1,0,0,1),(7,0,1,0,2),(12,1,1,0,3),(12,1,0,0,0),(7,0,2,0,0),(20,0,0,1,0)]:
   assert m.TieWinner(dmg,a,bb,c,False)==winner
   assert m.TieWinner(dmg,a,bb,c,True)==0
   for offset in (-.15,.15):
    if winner:assert m.TieWinner(dmg+offset,a,bb,c,False)==winner
   for offset in (-.151,.151):assert m.TieWinner(dmg+offset,a,bb,c,False)==0
  m.RememberTie([1,2,1,2][v-1]);cases.append({'variant':v,'mode':m.Mode,'add_order':list(addorder),'logs':logs[-2:]})
 assert 'lower FormID' in logs[-1]
 # Every subset, every selected variant: reject partial / mixed sets.
 count=0
 expected={frozenset(['ProbeAB']):1,frozenset(['ProbeHit','ProbeMultiply']):2,frozenset(['CrossA','CrossB']):3,frozenset(['CrossA2','CrossB2']):4}
 for v in range(1,5):
  globals['TieVariant'].v=v
  for bits in itertools.product((0,1),repeat=len(names)):
   held.clear();held.update(n for n,on in zip(names,bits) if on)
   want=expected.get(frozenset(held),0)
   if held==set(expectedorders[v-1]):want=v+4
   assert m.CurrentMode()==want,(v,held,m.CurrentMode(),want)
   count+=1
 # Busy / failed preparation or meter attachment cannot advance variant.
 held.clear();s.fields['TieNext']=2;s.fields['Busy']=True;s.RunProbe(5);assert s.TieNext==2
 s.fields['Busy']=False;s.overrides['PrepareBandit']=lambda *a:False;s.RunProbe(5);assert s.TieNext==2
 s.overrides['PrepareBandit']=lambda *a:True;target.AddSpell=lambda *a:False;s.RunProbe(5);assert s.TieNext==2
 target.AddSpell=lambda *a:True
 s.RunProbe(3);assert not held and 'FourthPower' not in spells and s.TieNext==0 and av['AttackDamageMult']==1.25
 assert all(globals[n].v==0 for n in globals if n.startswith('Tie'))
 rr,meta=b.read_plugin(b.WORK/'build/fix18-probe-package/Elements Spellblade Round18 Probes.esp');by={r.edid:r for r in rr}
 assert meta['masters']==['Skyrim.esm'] and len(rr)==40
 wanted=[('A',0x860,0x810),('B',0x861,0x811),('A2',0x863,0x810),('B2',0x862,0x811)]
 conds=[]
 for name,fid,spell in wanted:
  r=by['ESSB_ProbeTie'+name];assert int(r.key.split('|')[1],16)==fid
  assert [v for k,v in r.ss if k=='PRKE']==[bytes([2,0,0])]
  assert [v for k,v in r.ss if k=='DATA'][1:]==[bytes([51,10,3])]
  assert r.d['EPFD']==b.I(b.own(spell));conds.append([v for k,v in r.ss if k in ('PRKC','CTDA')])
 assert all(c==conds[0] for c in conds)
 assert [r.edid for r in rr if r.edid.startswith('ESSB_ProbeTie')]==['ESSB_ProbeTieA','ESSB_ProbeTieB','ESSB_ProbeTieA2','ESSB_ProbeTieB2']
 report=dict(actual_psc_executed=True,subset_cases=count,patterns=patterns,variants=cases,records=40,master=meta['masters'],runtime_tested=False)
 (b.WORK/'build/fix18-probe-package/tie-offline-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('PROBE-TIE ok: 4 crossed variants, 8192 perk subsets, damage/count/invalid/tolerance guards, decision patterns, busy/failure/cleanup, priority-zero separate PERK and physical record order readback')
