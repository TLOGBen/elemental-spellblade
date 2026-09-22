"""fix3: meaningful source lifecycle, schema, selection, and binary-preservation regressions."""
from pathlib import Path
from types import SimpleNamespace as NS
import json,struct,sys,re,copy
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from papyrus_harness import Script
import build_v03 as b
from tes import read_plugin
results=[]
def check(name,fn):
 fn();results.append(name);print('PASS',name)
clock=NS(now=100.0)
def status():
 calls=[];life=NS(dead=False)
 target=NS(IsDead=lambda:life.dead,GetFormID=lambda:'123')
 ctl=NS(DebugLevel=NS(GetValueInt=lambda:0),LogThrottled=lambda *a:None,OnStatusFinish=lambda *a:None)
 vm=Script(ROOT/'src/ESSBStatus.psc',{'Utility':NS(GetCurrentRealTime=lambda:clock.now),
    'ESSBElem':NS(FrozenExtraSeconds=lambda c:0,OnFrozenTick=lambda *a:None,FrozenResidual=lambda c,f:0),
    'ESSBElem3':NS(AstralDelay=lambda c:2)})
 vm.fields.update(Holder=target,Ctl=ctl,Bound=True,
    FrozenShader=NS(Play=lambda *a:calls.append('play'),Stop=lambda *a:calls.append('stop')))
 vm.overrides.update(Dispel=lambda:None,RegisterForSingleUpdate=lambda t:calls.append('schedule'))
 vm.InitRings();return vm,calls,life

def thresholds():
 clock.now=100;v,c,_=status()
 v.AddStack(2,4);assert c==[]
 v.AddStack(2,1);v.AddStack(2,1);v.SyncFrozenFx();assert c==['play']
 v.ClearStack(2);v.ClearStack(2);assert c==['play','stop']
 v.SetStack(2,5);v.SetStack(2,2);assert c==['play','stop','play','stop']
def expires():
 clock.now=100;v,c,_=status();v.SetFrozen(2)
 clock.now=101;v.Tick();assert c==['play'] and v.Freeze==5
 clock.now=102;v.Tick();assert c==['play','stop'] and v.Freeze==0
 clock.now=100;v,c,_=status();v.SetStack(2,5)
 clock.now=102;v.Tick();assert c==['play']
 clock.now=103;v.Tick();assert c==['play','stop']
def migration():
 clock.now=100;v,c,_=status();v.SetFrozen(5);ints=v.ExportInts();floats=v.ExportFloats()
 v.PrepareSwap();assert c==['play','stop'];v.OnEffectFinish(v.Holder,None);assert c==['play','stop']
 n,nc,_=status();n.ImportState(ints,floats);assert nc==['play'] and n.Freeze==5
 n.OnEffectFinish(n.Holder,None);assert nc==['play','stop']
def cleanup():
 for method in ('DispelIfActive','death','OnEffectFinish'):
  v,c,life=status();v.SetFrozen(3)
  if method=='death':life.dead=True;v.OnUpdate()
  elif method=='OnEffectFinish':v.OnEffectFinish(v.Holder,None)
  else:v.DispelIfActive()
  assert c==['play','stop'],(method,c)
  v.SyncFrozenFx();assert c==['play','stop']
def schema():
 text=(ROOT/'vendor/wbDefinitionsTES5.pas').read_text(encoding='utf-8-sig')
 body=text.split("wbRecord(EFSH, 'Effect Shader'")[1].split('], False, nil')[0].split("wbStruct(DATA, '', [")[1]
 names=re.findall(r"wb(?:Float|Integer|ByteColors|ByteArray|FormIDCk)\('([^']+)'",body)
 offsets={n:i*4 for i,n in enumerate(names)}
 for label,off in [('Fill/Texture Effect - Presistent Alpha Ratio',32),('Edge Effect - Persistent Alpha Ratio',72),
     ('Fill/Texture Effect - Full Alpha Ratio',84),('Edge Effect - Full Alpha Ratio',88),('Flags',384),
     ('Particle Shader - Persistant Particle Count',128),('Ambient Sound',308)]:assert offsets[label]==off
 assert len(names)*4==400

def binary():
 old,_=read_plugin(ROOT/'build/fix3-before/Elements Spellblade.esp');new,_=read_plugin(b.OUT/b.PLUGIN)
 by={r.edid:r for r in new}
 for r in old:
  now=by[r.edid];assert now.key==r.key
  if r.edid=='ESSB_StatusHostEffect':
   assert [(k,v) for k,v in now.ss if k!='VMAD']==[(k,v) for k,v in r.ss if k!='VMAD'];continue
  if r.edid.startswith(('ESSB_FormAbilityEffect_','ESSB_MarkEffect_')) or r.edid in ('ESSB_ManaBreakEffect','ESSB_SilenceEffect'):
   offsets=(32,36) if r.edid.startswith('ESSB_FormAbilityEffect_') else (32,)
   data=bytearray(now.d['DATA'])
   for off in offsets:data[off:off+4]=r.d['DATA'][off:off+4]
   assert bytes(data)==r.d['DATA'],r.edid
   assert [(k,v) for k,v in now.ss if k!='DATA']==[(k,v) for k,v in r.ss if k!='DATA']
  else:assert now.ss==r.ss,r.edid
 assert struct.unpack('<f',by['ESSB_ShowMenu'].d['FLTV'])[0]==0

def settings():
 for config in [{'fx_aura':[]},{'fx_mark':{'Ice':'x|y'}},{'fx_aura':{'Frost':None}}, {'fx_mark':{'Fire':'bad'}}]:
  try:b.fx_settings(config)
  except ValueError:pass
  else:raise AssertionError(config)
 assert b.fx_settings({})['fx_aura']==b.FX_AURA_DEFAULT
 for config in [{'fx_aura':{'Frost':'Icebloom.esl|missing'}},
    {'fx_aura':{'Fire':'Phenderix Elements.esp|ZZArt_Fire'}},
    {'fx_mark':{'Fire':'vulcano.esp|DAR_MoltenSpellLavaMistShader'}},
    {'fx_mark':{'Divine':'Lightpower.esl|_LIP_ConsecrateDeadFXSA'}},
    {'fx_mark':{'Earth':'Phenderix Elements.esp|ZZShader_Earth'}}]:
  try:b.fx_export(config)
  except ValueError:pass
  else:raise AssertionError(config)
 # Exercise a real external EFSH that was not in the original 238 copies.
 rr,_,_,idx=b.fx_export({'fx_mark':{'Poison':'Venomancy.esp|_VENOM_PoisonFlameFXShader'}})
 assert idx['Venomancy.esp|_VENOM_PoisonFlameFXShader']&0xffffff>0x30fa
 manifest=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf-8'))['records']
 for r in rr:
  if r['edid'] in manifest:assert r['fid']&0xffffff==int(manifest[r['edid']]['id'],16)
 b.fx_export(json.loads((ROOT/'settings.json').read_text(encoding='utf-8')))

for name,fn in [('EFSH offsets independently match vendor',schema),('only requested ESP bytes changed; all old FX/weapon/hit/gameplay identical',binary),
 ('frozen starts at threshold, plays once, clears immediately',thresholds),('frozen follows default and overridden duration',expires),
 ('host migration stops old instance and restores new instance',migration),('death, dispel, finish clean shader without AME native calls',cleanup),
 ('settings reject malformed, missing, wrong-type, invisible; custom import appends IDs',settings)]:check(name,fn)
(ROOT/'build/fix3-regression.json').write_text(json.dumps({'passed':len(results),'tests':results,'scope':'ESP bytes and real source bodies with native mocks; not game runtime'},indent=2),encoding='utf-8')
