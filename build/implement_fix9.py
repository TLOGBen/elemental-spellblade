from pathlib import Path
import re, json
R=Path.cwd()
def read(p):return Path(p).read_bytes().decode('utf-8-sig').replace('\r\n','\n')
def write(p,s):
 p=Path(p);b=p.read_bytes() if p.exists() else b'';bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n';p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+s.replace('\r\n','\n').replace('\n',nl).encode('utf8'))
def body(s,n):return re.search(r'(?m)^(?:\w+(?:\[\])? )?(?:Function|Event) '+n+r'\([^\n]*(?:\\\n[^\n]*)*\)[\s\S]*?^End(?:Function|Event)',s)[0]
def prepend(s,n,code):
 pat=r'(?m)^((?:\w+(?:\[\])? )?(?:Function|Event) '+n+r'\([^\n]*(?:\\\n[^\n]*)*\)\n)'
 s,k=re.subn(pat,lambda m:m[0]+code,s);assert k==1,(n,k);return s
# Backups are confined to the allowed generated build tree.
for p in list(Path('src').glob('*.psc'))+[Path('build_v03.py'),Path('settings.json')]:
 q=Path('build/fix9-before')/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes()) if not q.exists() else None
for p in Path('src').glob('*.psc'):
 s=read(p);arrays=set(re.findall(r'\b\w+\[\]\s+(?:Property\s+)?(\w+)',s,re.I))
 for a in arrays:
  s=re.sub(r'\b'+a+r'\s*==\s*None\b','!'+a,s,flags=re.I)
  s=re.sub(r'\b'+a+r'\s*!=\s*None\b',a,s,flags=re.I)
 write(p,s)
p='src/ESSBController.psc';s=read(p)
s=s.replace('Bool Ready\n','Bool Ready\nBool Property StateBroken = False Auto\nBool FixInitialised\nBool RegistryInitialised\nBool FirstSetupDone\n',1)
fail='\tIf StateBroken\n\t\tReturn\n\tEndIf\n'
for fn,flag in [('InitFixState','FixInitialised'),('InitRegistry','RegistryInitialised')]:
 old=body(s,fn);new=old.replace('\n','\n'+fail+'\tIf '+flag+'\n\t\tReturn\n\tEndIf\n',1)
 new=new.replace('; Independent None guards also repair partially initialized saved state.','; Allocate once on this schema; failure latches and never retries.')
 new=re.sub(r'(?m)^(\t\t(\w+) = new \w+\[\d+\])$',lambda m:m[0]+'\n\t\tIf !'+m[2]+'\n\t\t\tBreakState()\n\t\t\tReturn\n\t\tEndIf',new)
 if fn=='InitFixState':new=new.replace('\tInitBackupInts()\n','\tInitBackupInts()\n'+fail)
 else:new=new.replace('\tInitFixState()\n','\tInitFixState()\n'+fail)
 new=new.replace('EndFunction','\t'+flag+' = True\nEndFunction');s=s.replace(old,new)
# Helper-created backup arrays are validated before any legacy bank copy.
old=body(s,'InitBackupInts');new=old
new=re.sub(r'(?m)^(\s*(BackupInts[A-D]) = ESSBState.NewBackup\(\))$',lambda m:m[0]+'\n\t\tIf !'+m[2]+'\n\t\t\tBreakState()\n\t\t\tReturn\n\t\tEndIf',new)
s=s.replace(old,new)
# Entry points must not restart after the latch; queued callbacks also return before array reads.
for fn in ['OnInit','OnPlayerLoadGame','OnUpdate','Setup','ScheduleTick','ArmUpdate']:
 s=prepend(s,fn,fail)
for fn in ['OnWeaponHit','OnKillEvent','ToggleForm','SwitchForm','CloseForm','OnMarkStart','OnMarkFinish','OnStatusStart','OnStatusFinish','Tick','TickTimers','TickDomain','DumpRegistry']:
 s=prepend(s,fn,'\tIf !IsOperational()\n\t\tReturn\n\tEndIf\n')
for fn in ['InDomain','DomainFlag']:
 s=prepend(s,fn,'\tIf !IsOperational()\n\t\tReturn '+('False' if fn=='InDomain' else '0')+'\n\tEndIf\n')
# Re-check after init calls; no continuation may touch unallocated arrays.
s=s.replace('\tInitFixState()\n\tFloat now','\tInitFixState()\n'+fail+'\tFloat now')
s=s.replace('\tInitRegistry()\n\tPO3_Events_Alias.RegisterForWeaponHit(Self)','\tIf !ValidateBindings()\n\t\tBreakState()\n\t\tReturn\n\tEndIf\n\tInitRegistry()\n'+fail+'\tTrees.InitTables()\n'+fail+'\tESSBGuard guard = Self as ESSBGuard\n\tIf !guard\n\t\tBreakState()\n\t\tReturn\n\tEndIf\n\tguard.Setup()\n'+fail+'\tIf !FirstSetupDone\n\t\tReconcileLoadedForm(player)\n\t\tFirstSetupDone = True\n\tEndIf\n\tPO3_Events_Alias.RegisterForWeaponHit(Self)')
s=s.replace('\tplayer.AddSpell(SettingsPower, False)','\tIf !player.HasSpell(SettingsPower)\n\t\tplayer.AddSpell(SettingsPower, False)\n\tEndIf',1)
s=s.replace('\t\tplayer.AddSpell(FormPowers[index], False)','\t\tIf !player.HasSpell(FormPowers[index])\n\t\t\tplayer.AddSpell(FormPowers[index], False)\n\t\tEndIf',1)
s=s.replace('\tplayer.AddSpell(FormRulesAbility, False)','\tIf !player.HasSpell(FormRulesAbility)\n\t\tplayer.AddSpell(FormRulesAbility, False)\n\tEndIf',1)
props=re.findall(r'(?m)^(\w+(?:\[\])?) Property (\w+).* Auto$',s)
required=[(t,n) for t,n in props if t.endswith('[]') or t in ['GlobalVariable','Spell','ESSBTrees']]
validation='Bool Function ValidateBindings()\n'
for t,n in required:
 validation+='\tIf !'+n+'\n\t\tReturn False\n\tEndIf\n'
 if t.endswith('[]') and t not in ('Int[]','Float[]','Bool[]','String[]'):
  validation+='\tInt check'+n+' = 0\n\tWhile check'+n+' < '+n+'.Length\n\t\tIf !'+n+'[check'+n+']\n\t\t\tReturn False\n\t\tEndIf\n\t\tcheck'+n+' += 1\n\tEndWhile\n'
validation+='\tReturn True\nEndFunction\n'
mirrors=[n for t,n in props if t=='GlobalVariable' and n.startswith('G') and n!='GameHour']
reconcile='Function ReconcileLoadedForm(Actor player)\n\t; A fresh schema has no combat state. Keep GLOB progression/settings and perks.\n\tFormActive.SetValueInt(0)\n\tCurrentElement.SetValueInt(0)\n\tSync.SetValueInt(0)\n'
reconcile+=''.join('\t'+n+'.SetValueInt(0)\n' for n in mirrors)
reconcile+='\tInt i = 0\n\tWhile i < FormAbilities.Length\n\t\tplayer.RemoveSpell(FormAbilities[i])\n\t\ti += 1\n\tEndWhile\n\t; Recreate the AME too: its saved Controller property belongs to the old quest.\n\tplayer.RemoveSpell(FormRulesAbility)\n\tSendModEvent("ESSB_FormChanged", "close", 0.0)\nEndFunction\n'
s+='\n; FIX9: the failure latch is persistent; there is no retry/reset path.\nBool Function IsOperational()\n\tReturn !StateBroken && Ready\nEndFunction\n\nFunction BreakState()\n\tIf StateBroken\n\t\tReturn\n\tEndIf\n\tStateBroken = True\n\tReady = False\n\tUnregisterForUpdate()\n\tPO3_Events_Alias.UnregisterForWeaponHit(Self)\n\tIf Trees\n\t\tTrees.UnregisterForUpdate()\n\tEndIf\n\tDebug.MessageBox("元素魔戰士：此存檔含不相容的舊腳本狀態，已停止運作。請退出遊戲，安裝已提升 state_schema_version 並重新建置的完整更新包，再載入此存檔。無需清存檔，技能樹等級、點數與設定保留。")\nEndFunction\n\n'+validation+'\n'+reconcile
write(p,s)
# Tables: allocate/validate BEFORE the first array element is written.
p='src/ESSBTrees.psc';s=read(p);s=s.replace('Bool Ready\n','Bool Ready\nBool TablesInitialised\n',1)
old=body(s,'InitTables');allocs=re.findall(r'(?m)^\t(\w+) = new (\w+)\[(\d+)\]$',old)
new=re.sub(r'(?m)^\t\w+ = new \w+\[\d+\]\n','',old)
new=new.replace('\tIf SkillIds\n','\tIf !Controller || Controller.StateBroken || TablesInitialised\n',1)
head=''
for n,t,size in allocs:
 head+='\tIf !'+n+'\n\t\t'+n+' = new '+t+'['+size+']\n\tEndIf\n\tIf !'+n+'\n\t\tController.BreakState()\n\t\tReturn\n\tEndIf\n'
for n in re.findall(r'^GlobalVariable\[\] Property (\w+)',s,re.M):
 head+='\tIf !'+n+' || '+n+'.Length != 13\n\t\tController.BreakState()\n\t\tReturn\n\tEndIf\n\tInt check'+n+' = 0\n\tWhile check'+n+' < 13\n\t\tIf !'+n+'[check'+n+']\n\t\t\tController.BreakState()\n\t\t\tReturn\n\t\tEndIf\n\t\tcheck'+n+' += 1\n\tEndWhile\n'
new=new.replace('\tSkillIds[0]',head+'\tSkillIds[0]',1).replace('EndFunction','\tTablesInitialised = True\nEndFunction');s=s.replace(old,new)
# All array consumers in Trees have a central latch, including public MCM calls.
for m in list(re.finditer(r'(?m)^(?:(\w+(?:\[\])?) )?(Function|Event) (\w+)\(',s)):
 rt,kind,n=m.groups()
 if n=='InitTables':continue
 default={'Bool':'False','Int':'0','Float':'0.0','String':'""'}.get(rt,'None') if rt else ''
 s=prepend(s,n,'\tIf !Controller || Controller.StateBroken\n\t\tReturn'+(' '+default if default else '')+'\n\tEndIf\n')
s=s.replace('\tInitTables()\n','\tInitTables()\n\tIf Controller.StateBroken\n\t\tReturn\n\tEndIf\n',1) # Setup only; other callers below get typed returns.
for n in ['SkillId','TreeName','TreeOfSkillId','RefreshTree','CachedMainRank','RefreshActive','CachedBranch','TakeSnapshot','Reconcile']:
 old=body(s,n)
 if '\tInitTables()\n' in old:
  rt=re.match(r'(\w+) Function',old);d={'String':'""','Int':'0','Bool':'False'}.get(rt[1],'None') if rt else ''
  new=old.replace('\tInitTables()\n','\tInitTables()\n\tIf Controller.StateBroken\n\t\tReturn'+(' '+d if d else '')+'\n\tEndIf\n');s=s.replace(old,new)
write(p,s)
p='src/ESSBGuard.psc';s=read(p);s=s.replace('Bool Ready\n','Bool Ready\nBool ArraysInitialised\n',1)
s=prepend(s,'Setup','\tIf !Ctl || Ctl.StateBroken\n\t\tReturn\n\tEndIf\n')
s=s.replace('\tRecentActor = new Actor[4]\n\tRecentTime = new Float[4]\n\tRecentNext = 0','\tIf !ArraysInitialised\n\t\tRecentActor = new Actor[4]\n\t\tRecentTime = new Float[4]\n\t\tIf !RecentActor || !RecentTime\n\t\t\tCtl.BreakState()\n\t\t\tReturn\n\t\tEndIf\n\t\tArraysInitialised = True\n\t\tRecentNext = 0\n\tEndIf',1)
for n in ['OnHitEx','OnActorKilled']:
 s=prepend(s,n,'\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf\n')
s=prepend(s,'TakeAttacker','\tIf !Ctl || !Ctl.IsOperational() || !ArraysInitialised\n\t\tReturn False\n\tEndIf\n')
s=s.replace('\tIf !RecentActor\n\t\tRecentActor = new Actor[4]\n\t\tRecentTime = new Float[4]\n\tEndIf\n','')
write(p,s)
# AME generations: no access to old untyped state; the quest ref is an existing member.
for name in ['ESSBStatus','ESSBMark','ESSBCounter','ESSBFormRules']:
 p='src/'+name+'.psc';s=read(p)
 gate='\tIf Controller != ESSBState.ControllerQuest()\n\t\tReturn\n\tEndIf\n'
 for n in re.findall(r'(?m)^Event (\w+)\(',s):
  if n=='OnEffectFinish':continue
  s=prepend(s,n,gate)
  if n!='OnEffectStart':s=prepend(s,n,'\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf\n')
 # Startup gate follows Ctl resolution, before registration or array initialisation.
 s=s.replace('\tCtl = Controller.GetAlias(0) as ESSBController\n','\tCtl = Controller.GetAlias(0) as ESSBController\n\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf\n')
 if name=='ESSBStatus':
  s=s.replace('\tInitRings()\n','',1).replace('\tBound = True','\tInitRings()\n\tIf Ctl.StateBroken\n\t\tReturn\n\tEndIf\n\tBound = True',1)
  s=s.replace('If Finished || Migrating || Freeze < 5 || Holder.IsDead()','If Finished || Migrating || !Holder || Freeze < 5 || Holder.IsDead()')
  # Validate helper results before copies and any element access.
  for var in ['BleedRing','PoisonRing','AstralRing','AstralWeight']:
   s=re.sub(r'(?m)^(\t\t'+var+r' = (?:ESSBState\.\w+\(\)|new \w+\[\d+\]))$',lambda m:m[0]+'\n\t\tIf !'+var+'\n\t\t\tCtl.BreakState()\n\t\t\tReturn\n\t\tEndIf',s)
  s=prepend(s,'InitRings','\tIf Ctl && Ctl.StateBroken\n\t\tReturn\n\tEndIf\n')
  s=prepend(s,'Tick','\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf\n')
  s=s.replace('\tInitRings()\n\tFloat now','\tInitRings()\n\tIf Ctl.StateBroken\n\t\tReturn\n\tEndIf\n\tFloat now')
  s=s.replace('If !Finished && !Migrating','If !Finished && !Migrating && !Ctl.StateBroken')
  s=s.replace('If Migrating || !Bound || !Ctl || !Holder','If Migrating || !Bound || !Ctl || !Holder || Controller != ESSBState.ControllerQuest() || !Ctl.IsOperational()')
 if name=='ESSBMark':s=s.replace('If Ctl && Holder','If Ctl && Holder && Controller == ESSBState.ControllerQuest() && Ctl.IsOperational()')
 if name=='ESSBCounter':
  old=body(s,'OnEffectFinish');s=s.replace(old,'Event OnEffectFinish(Actor akTarget, Actor akCaster)\n\t; Native AME binding is already gone; the engine removes registrations.\n\tListening = False\nEndEvent')
 write(p,s)
# Ephemeral power casts resolve current generated quest, even from a previously known SPEL.
p='src/ESSBFormPowerEffect.psc';s=read(p);s=prepend(s,'OnEffectStart','\tController = ESSBState.ControllerQuest()\n');s=s.replace('If controllerAlias\n','If controllerAlias && controllerAlias.IsOperational()\n');write(p,s)
p='src/ESSBSettingsEffect.psc';s=read(p);s=prepend(s,'OnEffectStart','\tESSBController ctl = GetController()\n\tIf !ctl || !ctl.IsOperational()\n\t\tReturn\n\tEndIf\n');s=prepend(s,'GetController','\tController = ESSBState.ControllerQuest()\n');s=prepend(s,'GetTrees','\tESSBController ctl = GetController()\n\tIf !ctl || !ctl.IsOperational()\n\t\tReturn None\n\tEndIf\n');write(p,s)
p='src/ESSBSilence.psc';s=read(p)
for n in ['OnEffectStart','OnUpdate','Drain']:
 s=prepend(s,n,'\tIf !ESSBState.Operational()\n\t\tReturn\n\tEndIf\n')
write(p,s)
p='src/ESSBMCM.psc';s=read(p)
for n in ['RespecCurrent','RespecAll','DumpRegistry','GetTrees']:
 s=prepend(s,n,'\tIf !ESSBState.Operational()\n\t\tReturn'+(' None' if n=='GetTrees' else '')+'\n\tEndIf\n')
write(p,s)
p='settings.json';s=read(p);s=s.replace('  "version": 4,','  "version": 4,\n  "state_schema_version": 2,',1);write(p,s)
print('FIX9 runtime edits written with original BOM/newlines')
