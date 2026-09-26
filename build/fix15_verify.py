"""Round 15 actual-source regressions. Native mocks are explicit; no game-runtime claim."""
from pathlib import Path
from types import SimpleNamespace as NS
import json,sys,math,re,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build'),str(ROOT)]
from papyrus_harness import Script,Array
from fix12_cost import Measured,scenario
from fix14_verify import fixture
OLD=ROOT/'.codex/pre-fix15-snapshot/src'
NEW=ROOT/'src'

def setup(folder):
 f=fixture(folder);f.env['Math'].Ceiling=math.ceil
 f.c.overrides.update(DurationInt=lambda x:int(x),DurationSeconds=lambda x:float(x),CooldownSeconds=lambda x:float(x))
 return f

def deathcurse(folder):
 f=setup(folder);f.mark(10);s=Measured(folder/'ESSBStatus.psc',f.env)
 s.fields.update(Ctl=f.c,Holder=f.v,DeathCurseLeft=103,DeathCurseAmount=20.,DeathCurseMult=1.5)
 f.c.RegStatus[0]=s;f.env['ESSBElem3'].overrides['AfterDeathCurse']=lambda *a:f.events.append(a[2])
 f.v.hp=0;f.c.CaptureDeath(0);f.c.ClearSlot(0)
 assert f.events==[30.],('death curse lost on death/clear',f.events)
 s.ResolveDeathCurse(True);assert f.events==[30.]
 f=setup(folder);f.mark(10);f.c.PendingCurse[0]=103;f.c.PendingCurseBase[0]=20;f.c.PendingCurseMult[0]=1.5
 f.env['ESSBElem3'].overrides['AfterDeathCurse']=lambda *a:f.events.append(a[2]);f.v.hp=0
 f.c.ClearSlot(0);assert f.events==[30.]
 return 'host and pending curses settle once on death; no corpse damage'

def terminal_hit(folder):
 f=setup(folder);f.mark(5);f.c.CurrentElement.v=5
 f.v.IsPlayerTeammate=lambda:False;f.v.IsCommandedActor=lambda:False
 f.c.overrides.update(ResolveHitWeaponType=lambda *a:5,SetSelf=lambda *a:f.events.append(('wind',a)),TakeKillStreak=lambda:False)
 f.env['ESSBElem2'].overrides.update(WindThreshold=lambda *a:5,LethalAmbush=lambda *a:f.events.append('ambush'))
 f.v.hp=0;f.c.OnWeaponHit(f.v,None,None,2048|65536)
 assert f.c.LastHitSneak and f.c.LastHitPower,'terminal hit facts rejected'
 assert ('wind',(3,5)) in f.events and 'ambush' in f.events,'terminal sneak effects missing'
 assert f.c.HitActor[0] is f.v and f.c.HitSneak[0] and f.c.HitWeapon[0]==5
 f.owned.add((4,2,4,1));f.c.OnKillEvent(f.v,f.p)
 assert f.events.count('streak')==1
 f.c.OnKillEvent(f.v,f.p);assert f.events.count('streak')==1
 # Inverse delivery order: preserve attribution through ClearSlot until hit facts arrive.
 f=setup(folder);f.mark(5);f.c.CurrentElement.v=5;f.owned.add((4,2,4,1))
 f.v.IsPlayerTeammate=lambda:False;f.v.IsCommandedActor=lambda:False
 f.c.overrides.update(ResolveHitWeaponType=lambda *a:5,SetSelf=lambda *a:None,TakeKillStreak=lambda:False)
 f.env['ESSBElem2'].overrides.update(WindThreshold=lambda *a:5,LethalAmbush=lambda *a:None)
 f.kill();assert 'streak' not in f.events
 f.clock[0]+=20;f.c.OnWeaponHit(f.v,None,None,2048)
 assert f.events.count('streak')==1,'kill-before-hit lost frozen wind attribution'
 return 'fatal sneak/power/weapon captured; target-owned streak once; wind+ambush; no dead proc'

def riposte(folder):
 f=setup(folder);amounts=[];ripostes=[]
 if 'RiposteWindowSpell' in (folder/'ESSBController.psc').read_text(encoding='utf-8'):
  # Round 21 (v0.4 5.1 反擊, ruling R5): the window is an effect on the player (ESSB_RiposteWindow, 3 s x the
  # duration slider) that the DLL reads on the next no-form hit (siphon x2) and dispels once used; the x2 and the
  # single use are tested natively (A0 riposte anchor, A7 scenarios). Papyrus only opens the window.
  applied=[];marker=NS(SetNthEffectDuration=lambda i,n:applied.append(('duration',i,n)))
  f.c.fields['RiposteWindowSpell']=marker
  f.p.DoCombatSpellApply=lambda spell,target:applied.append(('apply',spell is marker,target is f.p))
  f.c.SetRiposte(3)
  assert applied==[('duration',0,f.c.DurationInt(3)),('apply',True,True)],('riposte window not opened',applied)
  f.c.fields['RiposteWindowSpell']=None;applied.clear();f.c.SetRiposte(3)
  assert not applied,'missing window spell must be a no-op'
  return 'round 21: 反擊 opens ESSB_RiposteWindow on the player for DurationInt(3) s; the DLL consumes it'
 f.c.fields.update(NoformBaseTrue=5.,GCombo=None)
 f.c.overrides.update(MarkEngaged=lambda *a:None,ApplyTrueDamage=lambda amount,*a:amounts.append(amount),RecentCast=lambda *a:False)
 f.env['ESSBNoForm']=NS(IsCasting=lambda *a:False,OnCombo=lambda *a:None,OnMartialHit=lambda *a:ripostes.append(a[4] if len(a)>4 else 1.),
  OnManaBreak=lambda *a:None,OnInterruptCast=lambda *a:None,EmberRatio=lambda *a:0)
 f.c.SetRiposte(3);f.clock[0]=102;f.c.OnNoFormHit(f.v,None,False)
 if 'ApplyNoFormBaseline' not in f.c.functions:
  # Round 20 (N2): the baseline true damage is the DLL's (it cannot read this script-side window), so the
  # v0.3 反擊 x1.3 now reaches only the Papyrus 純武藝 base. The window rules themselves are unchanged.
  assert not amounts and ripostes==[1.3],('riposte not passed to the martial base',ripostes)
  f.c.OnNoFormHit(f.v,None,False);assert ripostes[-1]==1.
  f.c.SetRiposte(3);f.clock[0]+=4;f.c.OnNoFormHit(f.v,None,False);assert ripostes[-1]==1.
  return 'round 20: riposte x1.3 on the martial base, consumed once, expires by wall clock (baseline is the DLL\'s)'
 assert amounts==[6.5],('riposte not applied',amounts)
 f.c.OnNoFormHit(f.v,None,False);assert amounts[-1]==5.
 f.c.SetRiposte(3);f.clock[0]+=4;f.c.OnNoFormHit(f.v,None,False);assert amounts[-1]==5.
 return 'no-form baseline x1.3, consumed once, expires by wall clock'

def divine(folder):
 f=setup(folder);held=[False];hp=[100.];events=[]
 f.c.CurrentElement.v=7;f.owned.add((6,0,4,0));f.c.overrides['SyncStage']=lambda:3
 f.p.GetActorValue=lambda av:hp[0]
 f.p.RestoreActorValue=lambda av,n:hp.__setitem__(0,hp[0]+n)
 f.p.StartDeferredKill=lambda:(held.__setitem__(0,True),events.append('arm'))
 f.p.EndDeferredKill=lambda:(held.__setitem__(0,False),events.append('release'))
 f.c.overrides.update(ApplyCleanse=lambda *a:events.append('cleanse'),SetGuardDivine=lambda *a:events.append('grace'))
 if 'RefreshDivineProtection' in f.c.functions:f.c.RefreshDivineProtection()
 assert held[0],'lethal protection not armed before damage'
 hp[0]=-500.;f.c.RefreshDivineProtection()
 assert hp[0]==1. and not held[0] and f.c.DivineSaveUsed
 assert events==['arm','grace','cleanse','release']
 f.c.RefreshDivineProtection();assert events.count('arm')==1,'twice per combat'
 f.c.fields['DivineSaveUsed']=False;f.c.RefreshDivineProtection();assert held[0]
 f.c.Enabled.v=0;f.c.RefreshDivineProtection();assert not held[0]
 return 'native protection armed before 600 damage; restore exactly 1; cleanse; release; once/combat; disable releases'

def switch_charge(folder):
 f=setup(folder);f.c.fields['SelfCharge']=8
 f.c.overrides.update(ClearSelfAll=lambda:f.c.fields.__setitem__('SelfCharge',0),PlayFormSound=lambda *a:None)
 f.env['ESSBNodes'].overrides['HasTwin']=lambda *a:False
 f.c.OnFormSwitched(3,1)
 charge=f.c.TakeSwitchCharge() if 'TakeSwitchCharge' in f.c.functions else f.c.GetSelf(1)
 assert charge==8,'switch route erased charge'
 assert f.c.SelfCharge==0 and f.c.TakeSwitchCharge()==0
 f.owned.add((2,2,3,1));assert f.env['ESSBElem'].OverloadMult(f.c,3,charge)==2.
 f.c.SetPendingDischarge(charge);f.env['ESSBNodes'].overrides.update(OpenSyncBonus=lambda *a:0,HasWideMark=lambda *a:False)
 f.env['ESSBElem'].overrides['Discharge']=lambda *a:f.events.append(a[2])
 f.c.AfterOpen(1,f.v);assert f.events==[8] and f.c.PendingDischarge==0
 return 'switch 8 -> self 0, end snapshot 8 consumed once; overload and residual discharge use 8'

def clocks(folder):
 f=setup(folder);f.c.overrides.update(TickDomain=lambda:None,SetGlobal=lambda *a:None)
 f.c.SetRiposte(3);f.c.SetOpenBoost(3,5);f.c.SetEndBoost(3,5)
 f.clock[0]+=34;f.c.TickTimers()
 assert f.c.fields.get('RiposteLeft',0)==0 and f.c.GetOpenBoost(3)==0 and f.c.GetEndBoost(3)==0,'34-second stall stretched windows'
 # Execute the actual status Tick, including integrated layer-seconds, expiry and delayed actions.
 s=Measured(folder/'ESSBStatus.psc',f.env);f.env['ESSBStatus']=s
 s.fields.update(Ctl=f.c,Holder=f.v,RingClock=100.,BleedRing=Array([1]+[0]*9),PoisonRing=Array([2]+[0]*11),
   AstralRing=Array([1,0]),AstralWeight=Array([1.,0.]),DeathCurseLeft=103.,DeathCurseAmount=20.,DeathCurseMult=1.,AirLeft=102.,AirDamage=15.,Freeze=5,FreezeTime=100.,Heat=4,HeatTime=100.)
 s.overrides.update(InitRings=lambda:None,SyncFrozenFx=lambda:None)
 f.c.fields['PoisonDotK']=NS(GetValue=lambda:1.)
 dots=[];land=[];stars=[];frozen=[]
 f.c.overrides.update(ApplyDotDamage=lambda e,n,*a:dots.append((e,n)),OnLanding=lambda *a:land.append(a[1]),GetDamageMult=lambda *a:1.,ApplyBleedDrain=lambda *a:None,GetBloodHitMult=lambda:1.,ApplyDamage=lambda *a:None,ArmKillProc=lambda *a:None)
 f.env['ESSBReactions'].overrides['BaseMax']=lambda *a:1.
 f.env['ESSBNodes'].overrides['OmniMult']=lambda *a:1.
 f.env['ESSBElem'].overrides.update(HasTinder=lambda *a:False,FrozenExtraSeconds=lambda *a:0,OnFrozenTick=lambda *a:frozen.append(1),FrozenResidual=lambda *a:0)
 f.env['ESSBElem2'].overrides.update(BleedPerLayer=lambda *a:1.,BleedDrainPercent=lambda *a:0.)
 f.env['ESSBElem3'].overrides.update(AstralDelay=lambda *a:2,PoisonTickMult=lambda *a:1.,SpreadInterval=lambda *a:3,SpreadThreshold=lambda *a:999,PoisonTickHook=lambda *a:None,DetonateAstral=lambda *a:stars.append(a[2]),AfterDeathCurse=lambda *a:f.events.append(a[2]),DeathCurseLostRatio=lambda *a:0.)
 s.Tick();assert dots==[(6,10.),(8,24.)] and land==[15.] and stars==[1] and frozen==[1]
 assert s.DeathCurseLeft==0 and s.AirLeft==0 and s.Heat==0
 s.Tick();assert len(dots)==2 and len(f.events)==1,'repeat tick duplicated settlement'
 # Exact deadline roundtrip through the real host serializer.
 s.fields['DeathCurseLeft']=140.25
 packed=s.ExportFloats();ints=s.ExportInts()
 s2=Measured(folder/'ESSBStatus.psc',f.env);s2.fields.update(Ctl=f.c,Holder=f.v)
 s2.overrides.update(SyncFrozenFx=lambda:None,RegisterForSingleUpdate=lambda *a:None);s2.ImportState(ints,packed)
 assert s2.DeathCurseLeft==140.25 and s2.RingClock==134.
 s2.ResetLoadClock();assert s2.DeathCurseLeft==135. and s2.RingClock==134.
 return '34s late tick: all deadlines expire; 10 bleed/24 poison layer-seconds, landing/star/curse once; precise swap + load rebase'

def stacks(folder):
 f=setup(folder);f.mark(10);f.v.hp=0
 vals={1:8,2:5,5:4,6:3,7:7,10:5};f.c.overrides['GetStack']=lambda a,k:vals.get(k,0)
 f.c.CaptureDeath(0);f.c.ClearSlot(0);f.c.overrides['GetStack']=lambda *a:0
 if 'Function OnKill(' not in (folder/'ESSBElem3.psc').read_text(encoding='utf-8'):
  # Round 21: the v0.3 darkness on-kill consumer (ESSBElem3.OnKill: 收割／亡者歸來) is gone (N5 owns death
  # handling); the frozen snapshot it read is still taken, so check the snapshot itself.
  assert f.c.DeadCurse[0]==5,('curse lost between capture and kill',f.c.DeadCurse[0])
  f.c.OnKillEvent(f.v,f.p)
  assert f.c.DeadHeat[0]==8 and f.c.DeadHoly[0]==3
  return 'round 21: curse 5 / heat 8 / holy 3 frozen before clear (no darkness on-kill consumer until N5)'
 got=[];f.env['ESSBElem3'].overrides['OnKill']=lambda *a:got.append(a[6] if len(a)>6 else 0)
 f.c.OnKillEvent(f.v,f.p)
 assert got==[5],('curse lost between capture and kill',got)
 assert f.c.DeadHeat[0]==8 and f.c.DeadHoly[0]==3
 return 'curse 5 / heat 8 / holy 3 frozen before clear; kill reads snapshot even with no host'

def heat(folder):
 out=[];r=Script(folder/'ESSBReactions.psc',dict(ESSBElem=NS(KeepHeatOnBurst=lambda *a:True,Detonate=lambda *a:out.append(a[3]))))
 args=[object(),object(),None,1.]
 r.EndFire(*args,*([1] if len(r.functions['EndFire'][1])==5 else []))
 assert out==[False],'KeepHeatOnBurst has no reachable caller'
 r.EndFire(*args,0);assert out[-1] is True
 return 'burst with node preserves heat; switch still consumes'

def killproc(folder):
 f=setup(folder);v=f.v;f.c.overrides.update(GetStack=lambda *a:2,GetDamageMult=lambda *a:1.,ApplyDamage=lambda *a:f.c.ArmKillProc(a[2],a[3],a[1]) if len(a)>3 else None,SetStack=lambda *a:None)
 e=f.env['ESSBElem'];e.overrides.update(DetonatePerLayer=lambda *a:.1,SignatureMult=lambda *a:1.)
 f.env['ESSBReactions'].overrides['BaseMax']=lambda *a:10.
 f.owned.add((0,2,3,1));out=[]
 e.overrides['OnCremation']=lambda *a:out.append(('fire',a[2]))
 v.hp=10;e.Detonate(f.c,v,1.,True);assert not out and v.hp==10
 v.hp=0;f.c.OnKillEvent(v,f.p)
 assert out==[('fire',12.)],('async detonation kill ignored',out)
 f.c.OnKillEvent(v,f.p);assert len(out)==1
 f=setup(folder);out=[];f.env['ESSBElem3'].overrides['OnDeathSoul']=lambda *a:out.append('soul')
 f.v.hp=10;f.c.ArmKillProc(f.v,10,20.);f.v.hp=0;f.c.OnKillEvent(f.v,f.p);assert out==['soul']
 f=setup(folder);f.c.ArmKillProc(f.v,10,20.);f.clock[0]+=4;f.v.hp=0
 f.env['ESSBElem3'].overrides['OnDeathSoul']=lambda *a:out.append('stale');f.c.OnKillEvent(f.v,f.p);assert 'stale' not in out
 return 'native damage delayed beyond apply return: fire/soul resolved by kill event once; stale cause rejected'

def cast_capture(folder):
 f=setup(folder);f.owned.add((11,1,1,0));casting=[True];observed=[]
 f.c.overrides.update(RecentCast=lambda *a:False,MarkEngaged=lambda *a:casting.__setitem__(0,False),ApplyNoFormBaseline=lambda *a:None)
 f.env['ESSBNoForm']=NS(IsCasting=lambda *a:casting[0],OnCombo=lambda *a:None,OnMartialHit=lambda *a:None,
  OnManaBreak=lambda *a:observed.append(a[3] if len(a)>3 else casting[0]),OnInterruptCast=lambda *a:observed.append(a[2]),EmberRatio=lambda *a:0)
 f.c.OnNoFormHit(f.v,None,False)
 assert observed==[True],'processing-time casting check lost hit-time fact'
 if 'RecentCast' in f.c.overrides:del f.c.overrides['RecentCast']
 f.c.RememberCast(f.v);f.clock[0]+=1.5;assert f.c.RecentCast(f.v)
 f.clock[0]+=.01;assert not f.c.RecentCast(f.v)
 return 'casting captured before damage; passed immutably; recent spell-fire window 1.5s'

TESTS=[deathcurse,terminal_hit,riposte,divine,switch_charge,clocks,stacks,heat,killproc,cast_capture]
def run():
 negatives={};cases={}
 for i,test in enumerate(TESTS,1):
  try:test(OLD)
  except AssertionError as e:negatives[i]=str(e)
  else:raise AssertionError(f'finding {i}: pre-fix15 passed unexpectedly')
  cases[i]=test(NEW)
  print('FIX15 finding',i,'ok',flush=True)
  # FIX16: historical ledger is read-only.
 cost=scenario(NEW);assert cost['total']<=166 and 1 <= cost['identity'] <= 2 and cost['string_concats']==0
 import state_schema
 old=json.loads((ROOT/'.codex/pre-fix15-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
 new=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
 assert all(state_schema.stable_identity(k,new.get(k),v) for k,v in old.items())
 assert new['ESSB_DebugLevel']['id']=='000811'
 lock=state_schema.preflight();assert lock['state_schema_version']==json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
 import build_v03 as b
 records,meta=b.read_plugin(b.OUT/b.PLUGIN);by={r.edid:r for r in records}
 assert meta['masters']==['Skyrim.esm'] and len(records)==len(new)
 persistent=[r for r in records if r.edid=='ESSB_StatusHostEffect' or r.edid.startswith('ESSB_MarkEffect_')]
 assert len(persistent)==12 and all(int.from_bytes(r.d['DATA'][:4],'little')&0x00200000 for r in persistent)
 # Generated marker persistence is deliberately limited to the reviewed effects.
 assert not int.from_bytes(by['ESSB_EngagedEffect'].d['DATA'][:4],'little')&0x00200000
 before=json.loads((ROOT/'build/fix15-before.json').read_text(encoding='utf8'))
 for n,info in before.items():
  if n=='實作紀錄.md':
   baseline=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
   info=dict(sha256=hashlib.sha256(baseline).hexdigest(),length=len(baseline),bom=baseline.startswith(b'\xef\xbb\xbf'),crlf=baseline.count(b'\r\n'),lf=baseline.count(b'\n'))
  raw=(ROOT/n).read_bytes();assert raw.startswith(b'\xef\xbb\xbf')==info['bom'],n
  assert (raw.count(b'\r\n')==raw.count(b'\n'))==(info['crlf']==info['lf']),n
  if n=='實作紀錄.md':assert hashlib.sha256(raw[:info['length']]).hexdigest()==info['sha256']
 report=dict(negative_controls=negatives,cases=cases,cost=cost,schema=lock['state_schema_version'],identity_changes={k:[v,new.get(k)] for k,v in old.items() if new.get(k)!=v},runtime_tested=False)
 (ROOT/'build/fix15-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'FIX15 ok: 10/10 pre-fix15 failures -> 10/10 pass; current schema; non-quest FormIDs unchanged; DebugLevel 000811; hit calls={cost["total"]}')
 return report

def ledger(cases):
 coverage={i:('部分涵蓋' if i in (2,7,9) else '未涵蓋') for i in range(1,11)}
 rows=''.join(f'<tr><td>{i}</td><td>{coverage[i]}</td><td>{cases.get(i,"待驗證")}</td></tr>' for i in range(1,11))
 (ROOT/'.codex/impl-fix-round15.html').write_text('<!doctype html><meta charset="utf-8"><title>Round 15</title><style>body{font:16px system-ui;margin:3em;max-width:1000px}td,th{padding:12px;border-bottom:1px solid #ccc;text-align:left}</style><h1>第 15 輪修正與離線驗證</h1><p>以 review-fable-2026-09-19.md 為工作清單。未寫 MO2／SkyrimSE；未連網；未實機驗證。</p><table><tr><th>發現</th><th>第 14 輪</th><th>回歸結果</th></tr>'+rows+'</table>',encoding='utf8')

if __name__=='__main__':run()
