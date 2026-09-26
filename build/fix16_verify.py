"""Actual-source regressions against pre-fix16. Explicit engine mocks, not runtime proof."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,json,math,re,hashlib,struct
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build'),str(ROOT)]
from papyrus_harness import Script,Array
from fix12_cost import Measured,scenario
from fix15_verify import setup
OLD=ROOT/'.codex/pre-fix16-snapshot/src'
NEW=ROOT/'src'

def corpse(folder):
 f=setup(folder);f.mark(10);f.v.hp=0;counts=[]
 f.c.overrides.update(PlayFormSound=lambda *a:None,SyncMult=lambda:1.,PushSyncStage=lambda:None,ClearSelfAll=lambda:None,
                     EndBothMarks=lambda *a:counts.append('end'))
 f.env['ESSBNodes'].overrides.update(CommonBurstMult=lambda *a:1.,HasPerpetual=lambda *a:False)
 f.env['ESSBNoForm']=NS(BurstMult=lambda *a:1.,BurstRadius=lambda *a:100.,OnBurstTarget=lambda *a:counts.append('reward'),OnBurst=lambda *a:counts.append(a[2]))
 f.v.GetDistance=lambda *a:1.
 f.c.OnFormClosed(10)
 assert counts==[0] and f.c.RegActor[0] is None,('corpse burst reward/slot',counts)
 assert f.v in f.c.DeadActor
 # All direct finish routes must detach without end XP, FX, or End.
 f=setup(folder);f.mark(9);f.v.hp=0;calls=[]
 f.c.Trees.overrides['OnEndXP']=lambda *a:calls.append('xp')
 f.c.overrides['PlaceFx']=lambda *a:calls.append('fx')
 f.env['ESSBReactions'].overrides['End']=lambda *a:calls.append('end')
 f.c.FinishMark(0,False,1,2.,True,False)
 assert not calls and f.c.RegElem[0]==0 and f.v in f.c.DeadActor
 f=setup(folder);f.v.hp=0
 f.c.overrides['ThePlayer']=lambda:(_ for _ in ()).throw(AssertionError('End reached corpse'))
 f.env['ESSBReactions'].End(f.c,10,f.v,1,2.)
 return 'dead burst: capture+clear, zero count/rewards; direct FinishMark/End guarded'

def divine(folder):
 f=setup(folder);calls=[];f.c.overrides['IsCurrentController']=lambda:False
 f.p.StartDeferredKill=lambda:calls.append('arm');f.p.EndDeferredKill=lambda:calls.append('end')
 f.c.CurrentElement.v=7;f.c.overrides['SyncStage']=lambda:3;f.owned.add((6,0,4,0))
 f.c.RefreshDivineProtection();assert not calls,('stale controller armed',calls)
 f.c.overrides['IsCurrentController']=lambda:True
 assert 'ReleaseDivineProtection' in f.c.functions,'missing maintenance release'
 f.c.overrides['ClearGuardWindows']=lambda:None
 f.c.fields['StateBroken']=True
 f.c.ReleaseDivineProtection();assert calls==['end'] and not f.c.DivineArmed and f.c.Enabled.v==0
 f.c.RefreshDivineProtection();assert calls==['end'],'tick rearmed after release'
 # Menu must work despite broken/disabled gameplay, resolve current controller after confirmation.
 accepted=[False];menu=[]
 vm=Script(folder/'ESSBMCM.psc',dict(ESSBState=NS(ControllerQuest=lambda:NS(GetAlias=lambda i:f.c)),
    ShowMessage=lambda *a:accepted[0],ForcePageReset=lambda:menu.append('reset'),
    Debug=NS(Notification=lambda *a:menu.append('notify')),__execute_logs__=True))
 vm.ReleaseDivineProtection();assert calls==['end']
 accepted[0]=True;vm.ReleaseDivineProtection();assert calls==['end','end'] and menu==['reset','notify']
 s=(folder/'ESSBTrees.psc').read_text(encoding='utf8')
 for m in re.finditer(r'Controller.RefreshAbilities\(\)',s):assert 'Controller.IsOperational()' in s[m.start()-110:m.start()]
 body='\n'.join(f.c.functions['Setup'][2]);assert body.index('player.EndDeferredKill()')<body.index('ValidateBindings()')
 return 'old generation cannot arm; broken-state confirmed MCM release disables rearm; Setup unconditional release retained'

def frozen(folder):
 f=setup(folder);s=Measured(folder/'ESSBStatus.psc',f.env);s.fields.update(Ctl=f.c,Holder=f.v,RingClock=100.)
 s.overrides.update(SyncFrozenFx=lambda:None,RegisterForSingleUpdate=lambda *a:None)
 f.clock[0]=101.;s.SetFrozen(0.,103.)
 assert s.FreezeSeconds==2. and s.FreezeTime==101.,('pending deadline doubled',s.FreezeSeconds,s.FreezeTime)
 s.fields.update(DeathCurseLeft=150.,AirLeft=140.)
 s.RebaseImportedClock();assert s.DeathCurseLeft==150. and s.AirLeft==140.,'host swap spuriously rebased'
 for now in [102.99,103.,134.]:
  f.clock[0]=now;assert (now-s.FreezeTime>=s.FreezeSeconds)==(now>=103.)
 f.clock[0]=110.;s.SetFrozen(0.,103.);assert s.FreezeTime<=103. and s.FreezeTime+s.FreezeSeconds==103.
 return 'pending bind at 101 preserves due 103; no future timestamp/rebase, late bind remains expired'

def domains(folder):
 f=setup(folder);old=f.actor();new=f.actor();pool=[old];present={id(old),id(f.p)};out=[]
 f.c.DomainElem[0]=10;f.c.DomainTickAt[0]=100.;f.c.DomainLeft[0]=140.
 f.c.overrides.update(InsideDomainSlot=lambda a,s:id(a) in present,ScanDomainTargets=lambda *a:Array(pool),
     SetGlobal=lambda *a:None,DomainFlag=lambda *a:0,ApplyUtil=lambda *a:None,ApplyDotDamage=lambda e,n,a:out.append((a,n)))
 f.env['PO3_SKSEFunctions']=NS(GetActorsByProcessingLevel=lambda *a:Array(pool))
 f.env['ESSBReactions'].overrides['ReactDamage']=lambda *a:1.
 # First sample establishes residents at domain start, both implementations have zero work.
 f.c.TickDomain();pool.append(new);present.add(id(new));f.clock[0]=134.
 f.c.TickDomain()
 assert all(a is not new for a,n in out),('newcomer received entire domain backlog',[(id(a),n) for a,n in out])
 assert out==[(old,34.)]
 f.clock[0]=135.;f.c.TickDomain();assert out[-2:]==[(old,1.),(new,1.)]
 # Leaving observed resets the resident's entry; reentry earns no prior time.
 pool.remove(new);present.remove(id(new));f.clock[0]=136.;f.c.TickDomain()
 pool.append(new);present.add(id(new));f.clock[0]=139.;before=len(out);f.c.TickDomain()
 assert not any(a is new for a,n in out[before:])
 # Poison and player recovery use their own same resident clock, not the domain clock.
 f.c.ClearDomainResidents(0);f.c.DomainElem[0]=8;f.c.DomainLeft[0]=200.;out.clear()
 f.c.overrides['AddStackTo']=lambda a,k,n:out.append((a,n))
 f.c.TickDomain();f.clock[0]=140.;f.c.TickDomain();assert out==[(old,1),(new,1)]
 f.c.ClearDomainResidents(0);f.c.DomainElem[0]=9;present.discard(id(f.p));f.c.TickDomain()
 present.add(id(f.p));f.clock[0]=174.;out.clear()
 f.c.overrides.update(GLevel=lambda *a:1.,ApplyUtil=lambda k,n,t,a:out.append((a,n)) if a is f.p else None)
 f.c.TickDomain();assert not out,'new player received recovery backlog'
 f.clock[0]=175.;f.c.TickDomain();assert out==[(f.p,15.),(f.p,15.)]
 return '34s late: resident 34/newcomer 0; next second 1 each; observed exit/reentry, poison and player recovery isolated'

def cost(folder):
 f=setup(folder);calls=[];f.c.overrides.update(MarkEngaged=lambda *a:None,ApplyNoFormBaseline=lambda *a:None,RecentCast=lambda *a:False)
 f.env['ESSBNoForm']=NS(IsCasting=lambda *a:calls.append('casting') or False,OnCombo=lambda *a:None,OnMartialHit=lambda *a:None,OnManaBreak=lambda *a:None,OnInterruptCast=lambda *a:None,EmberRatio=lambda *a:0)
 f.c.OnNoFormHit(f.v,None,False);assert not calls,'unowned casting natives'
 f.c.fields.update(CachedSync=30,SyncStageShown=3)
 f.c.overrides['RefreshDivineProtection']=lambda:calls.append('divine')
 f.c.AddSync(1);assert not calls,'unowned divine refresh at stage3'
 f.owned.add((6,0,4,0));f.c.AddSync(1)
 if 'CachedSyncStage' in f.c.fields:
  assert not calls,'round18 removed per-hit divine refresh'
  f.c.overrides['SendModEvent']=lambda *a:None
  f.c.OnSyncStage(3)
 assert calls==['divine']
 s=Measured(folder/'ESSBStatus.psc',f.env);s.fields.update(Ctl=f.c,Holder=f.v,RingClock=100.,Heat=3)
 checks=[];f.v.IsDead=lambda:checks.append('dead') or False
 s.overrides.update(InitRings=lambda:None,Tick=lambda:checks.append('tick'))
 f.clock[0]=100.2;s.GetStack(1);assert checks==[],'fast GetStack calls IsDead before clock check'
 f.clock[0]=101.;s.GetStack(1);assert checks==['dead','tick'],'elapsed path must still settle'
 result=scenario(folder);assert result['total']<=166
 return {'calls':result['total'],'scripted':result['scripted'],'native':result['native'],'guards':'casting, divine ownership + stack elapsed short-circuit'}

def streak(folder):
 f=setup(folder);f.owned.add((4,2,4,1));f.c.CurrentElement.v=5
 f.v.IsPlayerTeammate=lambda:False;f.v.IsCommandedActor=lambda:False
 f.c.overrides.update(ResolveHitWeaponType=lambda *a:5,SetSelf=lambda *a:None,TakeKillStreak=lambda:False)
 f.env['ESSBElem2'].overrides.update(WindThreshold=lambda *a:5,LethalAmbush=lambda *a:None)
 f.v.hp=0;f.c.OnWeaponHit(f.v,None,None,2048)
 assert f.c.KillElementFor(f.v)==0,'test must be a pure physical kill'
 f.c.CurrentElement.v=10;f.c.OnKillEvent(f.v,f.p)
 assert f.events==['streak'],('recorded wind form lost to killing element/current form',f.events)
 f.c.OnKillEvent(f.v,f.p);assert f.events==['streak']
 # Earlier non-sneak fact + kill-first delivery cannot consume the late fatal sneak fact.
 f=setup(folder);f.owned.add((4,2,4,1));f.c.CurrentElement.v=5
 f.c.HitActor[0]=f.v;f.c.HitSneak[0]=False;f.c.HitForm[0]=5
 f.v.hp=0;f.c.OnKillEvent(f.v,f.p);assert not f.c.HitKillDone[0]
 f.c.HitSneak[0]=True;f.c.SettleSneakKill(f.v,0);assert f.events==['streak']
 f=setup(folder);f.owned.add((4,2,4,1));f.c.HitActor[0]=f.v;f.c.HitSneak[0]=True;f.c.HitForm[0]=10
 f.c.CurrentElement.v=5;f.c.SettleSneakKill(f.v,5);assert not f.events
 return 'unmarked one-hit wind sneak counts after switching to dark; inverse current form rejected; kill-before-hit remains eligible'

def guards(folder):
 f=setup(folder);native={};spells={}
 for i in range(9):
  spells[i]=NS(index=i,seconds=0)
  spells[i].SetNthEffectDuration=lambda n,d,i=i:setattr(spells[i],'seconds',d)
 f.env['ESSBState'].overrides['GuardWindowSpell']=lambda i:spells[i]
 f.p.DispelSpell=lambda s:native.pop(s.index,None)
 f.p.DoCombatSpellApply=lambda s,a:native.__setitem__(s.index,f.clock[0]+s.seconds)
 names=['GuardSwitch','GuardBurst','GuardIce','GuardWind','GuardDivine','CloakGuard','GuardDark','GuardAstral','GuardStar']
 for i,name in enumerate(names):
  f.clock[0]=100.;getattr(f.c,'Set'+name)(2)
  # Emulate engine HasMagicEffect with native expiration, WITHOUT running script ticks.
  assert native.get(i)==102.,('missing native deadline for PERK read',name)
  f.clock[0]=102.;assert not (native[i]>f.clock[0])
 f.clock[0]=134.;assert not any(t>f.clock[0] for t in native.values())
 f.c.GetGuardWindLeft();f.c.GetGuardDarkLeft();assert f.c.GGuardWind.v==f.c.GGuardDark.v==0
 return 'all nine engine markers expire at 2s without a VM tick; late 34s PERK reads false; getter mirrors clear'

def killproc(folder):
 for kind in [1,10]:
  f=setup(folder);out=[]
  f.env['ESSBElem'].overrides['OnCremation']=lambda *a:out.append('fire')
  f.env['ESSBElem3'].overrides['OnDeathSoul']=lambda *a:out.append('soul')
  f.c.ArmKillProc(f.v,kind,20.);f.clock[0]+=2;f.v.hp=0;f.c.SettleKillProc(f.v)
  assert not out,'nonlethal application claimed unrelated weapon kill'
  for delay in [7.,34.]:
   f=setup(folder);f.mark(kind);out=[];f.v.hp=20.
   f.env['ESSBElem'].overrides['OnCremation']=lambda *a:out.append('fire')
   f.env['ESSBElem3'].overrides['OnDeathSoul']=lambda *a:out.append('soul')
   f.c.ArmKillProc(f.v,kind,20.);f.v.hp=0;f.clock[0]+=delay
   f.c.CaptureDeath(0);f.c.ClearSlot(0);f.c.OnKillEvent(f.v,f.p)
   assert out==['fire' if kind==1 else 'soul'],('late capture lost lethal prediction',kind,delay,out)
   f.c.OnKillEvent(f.v,f.p);assert len(out)==1
 # Prediction must compare the delivered (level/base/target-scaled) magnitude.
 f=setup(folder);f.v.hp=50.;amounts=[]
 f.c.BaseDamageMult.v=3.;f.c.overrides.update(GLevel=lambda *a:2.,ApplyDamageRaw=lambda e,n,a:amounts.append(n))
 f.env['ESSBElem2'].overrides['TargetDamageMult']=lambda *a:1.
 f.env['ESSBElem3'].overrides['TargetDamageMult']=lambda *a:1.
 f.c.ApplyDamage(1,10.,f.v,1)
 assert amounts==[60.] and f.c.KillProcUntil[0]==-1. and f.c.KillProcAmount[0]==10.
 return 'nonlethal 20/100 never claims weapon kill at 2s; lethal 20/20 survives 7/34s capture+clear once; prediction uses final magnitude, reward retains original amount'

def casting(folder):
 f=setup(folder);calls=[];casting=[True];facts=[]
 f.c.overrides.update(RecentCast=lambda *a:False,MarkEngaged=lambda *a:casting.__setitem__(0,False),ApplyNoFormBaseline=lambda *a:None)
 f.env['ESSBNoForm']=NS(IsCasting=lambda *a:calls.append('cast') or casting[0],OnCombo=lambda *a:None,OnMartialHit=lambda *a:None,
     OnManaBreak=lambda *a:facts.append(a[3]),OnInterruptCast=lambda *a:facts.append(a[2]),EmberRatio=lambda *a:0)
 f.c.OnNoFormHit(f.v,None,False);assert not calls and facts==[False],'unowned hit queried casting'
 f.owned.add((11,1,1,0));casting[0]=True;f.c.OnNoFormHit(f.v,None,False)
 assert calls==['cast'] and facts[-1] is True,'state was not captured before processing damage'
 # Arrival after casting ended is intentionally false: callback carries no original cast timestamp.
 f.clock[0]+=7;f.c.OnNoFormHit(f.v,None,False);assert facts[-1] is False
 return 'owned-only immutable pre-damage fact; 7s-late callback after cast end intentionally false'

TESTS=[('A1',corpse),('A2',divine),('A3',frozen),('A4',domains),('A5',cost),('B1.2',streak),('B1.6',guards),('B1.9',killproc),('B1.10',casting)]

def extra_costs(folder):
 f=setup(folder);m=f.m
 nf=Measured(folder/'ESSBNoForm.psc',f.env);f.env['ESSBNoForm']=nf
 nf.overrides.update(OnCombo=lambda *a:None,OnMartialHit=lambda *a:None,OnManaBreak=lambda *a:None,OnInterruptCast=lambda *a:None,EmberRatio=lambda *a:0.)
 f.c.overrides.update(MarkEngaged=lambda *a:None,ApplyNoFormBaseline=lambda *a:None,RecentCast=lambda *a:False)
 f.v.GetEquippedSpell=m.wrap('Actor.GetEquippedSpell',lambda i:object())
 f.v.GetEquippedShout=m.wrap('Actor.GetEquippedShout',lambda:object())
 f.env['PO3_SKSEFunctions']=NS(IsCasting=m.wrap('PO3.IsCasting',lambda *a:False))
 m.script.clear();m.native.clear();f.c.OnNoFormHit(f.v,None,False)
 noform=dict(scripted=sum(m.script.values()),native=sum(m.native.values()),casting_natives=sum(v for k,v in m.native.items() if k in ('Actor.GetEquippedSpell','Actor.GetEquippedShout','PO3.IsCasting')))
 s=Measured(folder/'ESSBStatus.psc',f.env);s.fields.update(Ctl=f.c,Holder=f.v,RingClock=100.,Heat=3)
 s.overrides['InitRings']=lambda:None
 f.v.IsDead=m.wrap('Actor.IsDead',lambda:False);f.clock[0]=100.2
 m.script.clear();m.native.clear()
 for _ in range(10):assert s.GetStack(1)==3
 reads=dict(scripted=sum(m.script.values()),native=sum(m.native.values()),is_dead=m.native['Actor.IsDead'])
 return dict(noform_unowned=noform,ten_same_second_stack_reads=reads)

def verify_records():
 import build_v03 as b,state_schema
 manifest=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
 old=json.loads((ROOT/'.codex/pre-fix16-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
 assert all(state_schema.stable_identity(k,manifest.get(k),v) for k,v in old.items())
 changed={k:[v['id'],manifest[k]['id']] for k,v in old.items() if v!=manifest[k]}
 assert set(changed)==set(state_schema.QUESTS) and manifest['ESSB_DebugLevel']['id']=='000811'
 assert set(manifest)-set(old)==b.GUARD_WINDOW_EDIDS | (b.hit18.new_edids(b) | b.hit19.NEW_EDIDS | set(b.tree_v04.NEW_PERK_EDIDS)) | {k for k in state_schema.stub_ids(b.STATE_SCHEMA_VERSION) if k not in state_schema.stub_ids(5)}
 records,meta=b.read_plugin(b.OUT/b.PLUGIN);by={r.edid:r for r in records}
 assert meta['masters']==['Skyrim.esm'] and len(records)==len(manifest)
 # Round 21: the window owners are v0.4 nodes, looked up by name in the identity table (build/plan-tree-nodes.json);
 # the windows whose v0.3 owners v0.4 removed (冰晶, 影甲, 星體, 星光) keep their records but no PERK uses them.
 owners={0:('common','順轉'),1:('common','安全閥'),3:('wind','殘影'),4:('divine','神佑'),5:('noform','破護')}
 plan=json.loads((ROOT/'build/plan-tree-nodes.json').read_text(encoding='utf8'))
 edid_of={(tr['id'],br['name']):f"ESSB_P_{tr['id']}_{ro['index']}_{ti['index']}_B{br['slot']+1}"
          for tr in plan['trees'] for ro in tr['routes'] for ti in ro['tiers'] for br in ti['branches']}
 perk_ctdas={r.edid:[v for t,v in r.ss if t=='CTDA'] for r in records if r.sig=='PERK'}
 for i,name in enumerate(b.GUARD_WINDOWS):
  eff=by['ESSB_WindowEffect_'+name];spell=by['ESSB_WindowSpell_'+name]
  assert 'VMAD' not in eff.d and not int.from_bytes(eff.d['DATA'][:4],'little')&0x200
  assert struct.unpack_from('<II',spell.d['SPIT'],16)==(1,0)
  assert spell.refs('EFID')==[eff.key]
  users=sorted(e for e,c in perk_ctdas.items() if b.guard_window(i) in c)
  assert users==([edid_of[owners[i]]] if i in owners else []),(name,users)
  # Exactly this effect, with comparison == true, on the PERK owner.
  assert struct.unpack_from('<H',b.guard_window(i),8)[0]==214
 return {'changed_existing':changed,'added':sorted(set(manifest)-set(old)),'records':len(records),'schema':state_schema.preflight()['state_schema_version']}

def run(records=True):
 negatives={};cases={}
 for key,test in TESTS:
  try:test(OLD)
  except AssertionError as e:negatives[key]=str(e)
  else:raise AssertionError(key+' pre-fix16 unexpectedly passed')
  cases[key]=test(NEW);print('FIX16',key,'ok',flush=True)
 cost_before=scenario(OLD);cost_after=scenario(NEW)
 assert cost_after['total']<cost_before['total'] and cost_after['total']<=166
 extra_before=extra_costs(OLD);extra_after=extra_costs(NEW)
 assert extra_before['noform_unowned']['casting_natives']==10 and extra_after['noform_unowned']['casting_natives']==0
 assert extra_before['ten_same_second_stack_reads']['is_dead']==10 and extra_after['ten_same_second_stack_reads']['is_dead']==0
 report=dict(negative_controls=negatives,cases=cases,cost_before=cost_before,cost_after=cost_after,extra_cost_before=extra_before,extra_cost_after=extra_after,runtime_tested=False)
 if records:report['records']=verify_records()
 before=json.loads((ROOT/'build/fix16-before.json').read_text(encoding='utf8'))
 for n,info in before.items():
  if n=='實作紀錄.md':
   baseline=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
   info=dict(sha256=hashlib.sha256(baseline).hexdigest(),length=len(baseline),bom=baseline.startswith(b'\xef\xbb\xbf'),crlf=baseline.count(b'\r\n'),lf=baseline.count(b'\n'))
  raw=(ROOT/n).read_bytes()
  assert raw.startswith(b'\xef\xbb\xbf')==info['bom'],n
  assert (raw.count(b'\r\n')==raw.count(b'\n'))==(info['crlf']==info['lf']),n
  if n=='實作紀錄.md':assert hashlib.sha256(raw[:info['length']]).hexdigest()==info['sha256']
 (ROOT/'build/fix16-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'FIX16 ok: 9/9 pre-fix16 failures -> 9/9 pass; hit calls {cost_before["total"]} -> {cost_after["total"]}; native runtime untested')
 return report

if __name__=='__main__':run('--sources-only' not in sys.argv)
