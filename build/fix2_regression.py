"""fix round 2: exercise real Papyrus bodies with explicit native mocks (not game runtime)."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy,json,re,sys,collections
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import papyrus_harness as harness
from papyrus_harness import Script,Array
# Quest.GetAlias() returns the controller mock; preserve the call when erasing this cast.
original_expression=harness.expression
harness.expression=lambda s:original_expression(s.replace(' as ESSBController',''))
import build_v03 as build
results=[]
def check(name,fn):
 fn();results.append(name);print('PASS',name)
def fail(*a): raise AssertionError('unexpected native call')
def controller():
 vm=Script(ROOT/'src/ESSBController.psc',{'Utility':NS(GetCurrentRealTime=lambda:100.0)})
 vm.InitRegistry();return vm

def status(start_action=None,tick_action=None):
 vm=Script(ROOT/'src/ESSBStatus.psc');calls=[]
 target=NS(IsDead=lambda:False)
 ctl=NS(OnStatusStart=lambda t,s:start_action(s) if start_action else None,
        OnStatusFinish=lambda t,s:calls.append('finish'))
 vm.fields.update(Holder=target,Ctl=ctl,Controller=NS(GetAlias=lambda _:ctl),Bound=True)
 vm.overrides.update(RegisterForSingleUpdate=lambda delay:calls.append(('schedule',delay)),
                     UnregisterForUpdate=fail,Dispel=lambda:calls.append('dispel'),
                     Tick=lambda:tick_action(vm) if tick_action else calls.append('tick'),
                     GetTimeElapsed=lambda:26.0)
 return vm,target,calls

def cancel_swap():
 vm=controller();vm.fields.update(SwapSlot=0,SwapActor=object(),SwapStarted=50)
 for slot in range(8):vm.SaveSwapData(slot,Array([slot]*27),Array([slot+.5]*17))
 vm.CancelSwap()
 assert vm.SwapSlot==-1 and vm.SwapActor is None and vm.SwapStarted==0
 for slot in range(8):
  assert vm.ReadSwapInts(slot)==[slot]*27 and vm.ReadSwapFloats(slot)==[slot+.5]*17
 body=vm.functions['CancelSwap'][2]
 assert not any(re.search(r'Swap(?:Ints|Floats)\s*=\s*None',l) for l in body)

def status_finish():
 vm,target,calls=status();vm.OnEffectFinish(target,None);vm.OnUpdate();vm.PrepareSwap();vm.DispelIfActive()
 assert calls==['finish'] and vm.Finished and vm.Migrating
 assert vm.IsStale(25.0)==False

def status_start_interleave():
 for action in [lambda s:s.OnEffectFinish(s.Holder,None),lambda s:s.PrepareSwap(),lambda s:s.DispelIfActive()]:
  vm,target,calls=status(start_action=action);vm.OnEffectStart(target,None)
  assert not any(isinstance(c,tuple) for c in calls),calls

def status_tick_interleave():
 for action in [lambda s:s.OnEffectFinish(s.Holder,None),lambda s:s.PrepareSwap(),lambda s:s.DispelIfActive()]:
  vm,target,calls=status(tick_action=action);vm.OnUpdate()
  assert not any(isinstance(c,tuple) for c in calls),calls

def live_status():
 vm,target,calls=status();vm.OnEffectStart(target,None);vm.OnUpdate()
 assert calls==[('schedule',1.0),'tick',('schedule',1.0)]
 assert vm.IsStale(25.0)
 vm.PrepareSwap();vm.OnUpdate();vm.DispelIfActive();vm.DispelIfActive();vm.OnEffectFinish(target,None)
 assert calls==[('schedule',1.0),'tick',('schedule',1.0),'dispel']

def mark_fixture(second=False):
 vm=controller();target=NS(DispelSpell=fail);vm.OccupySlot(0,target)
 events=[]
 vm.env.update(ESSBReactions=NS(End=lambda c,e,t,reason,mult,chain:events.append(('end',e,reason,mult,chain))),
               ESSBNodes=NS(HasResidualMark=lambda c:False))
 vm.overrides['PlaceFx']=lambda *a:events.append('fx')
 vm.fields['Trees']=NS(OnEndXP=lambda e:events.append(('xp',e)))
 mark=Script(ROOT/'src/ESSBMark.psc');mark.fields.update(Ctl=vm,Holder=target,ElementIndex=1)
 mark.overrides['Dispel']=lambda:events.append('dispel')
 if second:
  vm.fields['RegElem2'][0]=1;vm.fields['RegMark2'][0]=mark;vm.fields['RegSecondReal'][0]=True
 else:
  vm.fields['RegElem'][0]=1;vm.fields['RegMark'][0]=mark
 return vm,mark,target,events

def natural_marks():
 for second in [False,True]:
  vm,mark,target,events=mark_fixture(second)
  # A callback must skip even the scripted dispel wrapper, not only the native call.
  mark.overrides['DispelIfActive']=fail
  mark.OnEffectFinish(target,None);mark.OnEffectFinish(target,None)
  assert events==[('xp',1),('end',1,2,1.0,False),'fx'],events
  assert vm.RegElem[0]==0 and vm.RegElem2[0]==0

def explicit_mark_end():
 vm,mark,target,events=mark_fixture();vm.EndMark(0,1,2.0);mark.OnEffectFinish(target,None)
 assert events==['dispel',('xp',1),('end',1,1,2.0,False),'fx'],events
 mark.DispelIfActive();assert events.count('dispel')==1

def late_mark_start():
 for has_slot in [False,True]:
  vm,mark,target,events=mark_fixture()
  vm.fields['RegElem'][0]=0;vm.fields['RegMark'][0]=None
  if not has_slot:vm.fields['RegActor'][0]=None
  mark.OnEffectFinish(target,None);vm.OnMarkStart(1,target,mark)
  assert events==[]

def late_status_start():
 vm=controller();effect,target,calls=status();effect.OnEffectFinish(target,None)
 vm.OnStatusStart(target,effect)
 assert calls==['finish'] and effect.Migrating
 # A live duplicate is still suppressed and dispelled once.
 vm.OccupySlot(0,target);vm.fields['RegStatus'][0]=object()
 live,_,events=status();vm.OnStatusStart(target,live)
 assert events==['dispel'] and live.Migrating

def layout():
 plan=build.plan_trees.build();settings=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
 for tree in plan['trees']:
  config=build.csf_config(tree,settings);nodes=config['skills'][0]['nodes']
  build.validate_csf_layout(tree,nodes)
  # Coordinates are the ONLY changed skill config field.
  old_source=(ROOT/'build/fix2-before/build_v03.py').read_text(encoding='utf-8')
  old={'__name__':'fix2_layout_baseline'};exec(compile(old_source,'baseline','exec'),old)
  old_config=old['csf_config'](tree,settings)
  for c in [config,old_config]:
   for n in c['skills'][0]['nodes']:n.pop('x');n.pop('y')
  assert config==old_config
 tree=plan['trees'][0];original=build.csf_config(tree,settings)['skills'][0]['nodes']
 for kind in ['bounds','overlap','links','order']:
  nodes=copy.deepcopy(original)
  if kind=='bounds':nodes[0]['y']=4.6
  elif kind=='overlap':nodes[1]['x']=nodes[0]['x'];nodes[1]['y']=nodes[0]['y']
  elif kind=='links':nodes[0]['links']=[]
  else:
   for n in nodes:
    if n['id']=='m01':n['y']=0.0
  try:build.validate_csf_layout(tree,nodes)
  except AssertionError:pass
  else:raise AssertionError('layout assertion accepted '+kind)

def log_inventory():
 text=(ROOT/'.codex/smoke1-Papyrus.0.log').read_text(encoding='utf-8-sig',errors='replace')
 blocks=re.split(r'(?=^\[\d\d/\d\d/\d{4} - )',text,flags=re.M)
 groups={}
 for b in blocks:
  if not re.search(r'(?im)^\s+.*\.essb\w+\.',b) or not re.search('error:',b,re.I):continue
  message=b.splitlines()[0].split('] ',1)[-1]
  frames=re.findall(r'\.((?:essb)\w+\.\w+\(\))',b,re.I)
  key=(message,tuple(frames))
  row=groups.setdefault(key,{'message':message,'frames':frames,'count':0,'first_event':b})
  row['count']+=1
 assert sum(r['count'] for r in groups.values())==78 and len(groups)==9
 (ROOT/'build/fix2-log-errors.json').write_text(json.dumps({'total':78,'classes':list(groups.values())},ensure_ascii=False,indent=2),encoding='utf-8')

for name,fn in [
 ('CancelSwap preserves eight per-target backups without None array assignments',cancel_swap),
 ('finished status ignores finish-native, queued tick, swap and dispel calls',status_finish),
 ('OnEffectStart rechecks finish/migration after controller callback',status_start_interleave),
 ('OnUpdate rechecks finish/migration after Tick',status_tick_interleave),
 ('live status retains one-second ticks and migration suppresses queued update',live_status),
 ('primary and secondary natural marks settle once without self-dispel',natural_marks),
 ('explicit mark End preserves dispel, XP, End reason/multiplier and FX',explicit_mark_end),
 ('late mark rejection is safe with missing slot and wrong element',late_mark_start),
 ('late status rejection avoids both dead natives; live duplicate still dispels',late_status_start),
 ('13 layouts: only coordinates changed; invalid bounds/spacing/links/order rejected',layout),
 ('complete Papyrus log inventory: 78 errors in 9 stack classes',log_inventory),
]:check(name,fn)
(ROOT/'build/fix2-regression.json').write_text(json.dumps({'passed':len(results),'scope':'actual source bodies with native mocks; not Skyrim runtime','tests':results},indent=2),encoding='utf-8')
