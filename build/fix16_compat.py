from implement_fix16 import *
import re
c='src/ESSBController.psc'
for kind in ('Open','End'):
 replace(c,f'\tReturn SecondsLeft({kind}Boost[aiElement])',f'\tIf {kind}Boost[aiElement] <= 0.0\n\t\tReturn 0\n\tEndIf\n\tReturn SecondsLeft({kind}Boost[aiElement])')
# Previous gates still verify their exact additions, excluding only the 18 new records
# verified independently by FIX16. No previous identity check is removed.
replace('build/fix6_verify.py',"k not in build_v03.SCHEMA_STUBS and not k.startswith", "k not in build_v03.SCHEMA_STUBS and k not in build_v03.GUARD_WINDOW_EDIDS and not k.startswith")
for file in ('build/fix7_verify.py','build/fix8_verify.py'):
 replace(file,'k not in b.SCHEMA_STUBS}', 'k not in b.SCHEMA_STUBS and k not in b.GUARD_WINDOW_EDIDS}')
replace('build/fix10_verify.py','assert set(added)==set(state_schema.stub_ids(version))-set(state_schema.stub_ids(2))',"assert set(added)==(set(state_schema.stub_ids(version))-set(state_schema.stub_ids(2))) | __import__('build_v03').GUARD_WINDOW_EDIDS")
replace('build/fix12_verify.py',"assert set(ids)-set(oldids)==set(state_schema.stub_ids(json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']))-set(state_schema.stub_ids(3))", "assert set(ids)-set(oldids)==(set(state_schema.stub_ids(json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']))-set(state_schema.stub_ids(3))) | __import__('build_v03').GUARD_WINDOW_EDIDS")
replace('build/fix15_verify.py',"lock=state_schema.preflight();assert lock['state_schema_version']==5","lock=state_schema.preflight();assert lock['state_schema_version']==json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']")
replace('build/fix15_verify.py','cost=cost,schema=5,','cost=cost,schema=lock[\'state_schema_version\'],')
replace('build/fix15_verify.py','pass; schema 5;', 'pass; current schema;')
replace('build/fix15_verify.py','f=setup(folder);casting=[True];observed=[]','f=setup(folder);f.owned.add((11,1,1,0));casting=[True];observed=[]')
# R15's old tests demanded a nonlethal 12 damage application award a later weapon kill.
# Keep asynchronous lethal settlement coverage, correct the trigger to actual lethal HP.
replace('build/fix15_verify.py','e.Detonate(f.c,v,1.,True);assert not out and v.hp==100','v.hp=10;e.Detonate(f.c,v,1.,True);assert not out and v.hp==10')
replace('build/fix15_verify.py','f.c.ArmKillProc(f.v,10,20.);f.v.hp=0;','f.v.hp=10;f.c.ArmKillProc(f.v,10,20.);f.v.hp=0;')
replace('build/fix14_verify.py',"if 'HitActor' in f.c.fields:f.c.HitActor[0]=f.v;f.c.HitSneak[0]=True", "if 'HitActor' in f.c.fields:f.c.HitActor[0]=f.v;f.c.HitSneak[0]=True\n    if 'HitForm' in f.c.fields:f.c.HitForm[0]=5")
# Native marker access for historical source fixtures. New source tests exercise expiry.
replace('build/fix12_cost.py',"        def DoCombatSpellApply(self,s,t):m.native['Actor.DoCombatSpellApply']+=1", "        def DoCombatSpellApply(self,s,t):m.native['Actor.DoCombatSpellApply']+=1\n        def DispelSpell(self,s):m.native['Actor.DispelSpell']+=1")
replace('build/fix12_cost.py','quest if fid>=0x6000 else object()', 'quest if fid>=0x6000 else Spell() if 0x5170 <= fid <= 0x5181 else object()')
