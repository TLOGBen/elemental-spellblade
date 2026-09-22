from pathlib import Path
import shutil
p=Path('src/ESSBStatus.psc'); shutil.copyfile(p,Path('build/fix3-before/ESSBStatus.psc'))
s=p.read_bytes().decode('utf-8').replace('\r\n','\n')
def replace(a,b,count=1):
 global s
 assert s.count(a)==count,(a[:100],s.count(a),count)
 s=s.replace(a,b)
replace('Quest Property Controller Auto\n','EffectShader Property FrozenShader Auto\nBool FrozenFxShown = False\n\nQuest Property Controller Auto\n')
replace('Event OnEffectFinish(Actor akTarget, Actor akCaster)\n','Event OnEffectFinish(Actor akTarget, Actor akCaster)\n\tStopFrozenFx()\n')
replace('\tMigrating = True\nEndFunction','\tMigrating = True\n\tStopFrozenFx()\nEndFunction')
replace('Function DispelIfActive()\n\tIf !Finished\n\t\tFinished = True','Function DispelIfActive()\n\tIf !Finished\n\t\tFinished = True\n\t\tStopFrozenFx()')
replace('\t\tFreezeTime = now\n\tElseIf aiKind == 3','\t\tFreezeTime = now\n\t\tSyncFrozenFx()\n\tElseIf aiKind == 3')
replace('\t\tFreezeSeconds = 0.0\n\tElseIf aiKind == 5','\t\tFreezeSeconds = 0.0\n\t\tSyncFrozenFx()\n\tElseIf aiKind == 5')
replace('\t\tFreezeSeconds = 0.0\n\tElseIf aiKind == 3','\t\tFreezeSeconds = 0.0\n\t\tSyncFrozenFx()\n\tElseIf aiKind == 3')
replace('\tFreezeSeconds = afSeconds\nEndFunction','\tFreezeSeconds = afSeconds\n\tSyncFrozenFx()\nEndFunction')
replace('\t\tAstralWeight[1] = afFloats[16]\n\tEndIf\nEndFunction','\t\tAstralWeight[1] = afFloats[16]\n\tEndIf\n\tSyncFrozenFx()\nEndFunction')
replace('\tIf Holder.IsDead()\n\t\t;','\tIf Holder.IsDead()\n\t\tStopFrozenFx()\n\t\t;')
replace('\tElseIf Freeze > 0 && now - FreezeTime >= 6.0\n\t\tFreeze = 0\n\tEndIf','\tElseIf Freeze > 0 && now - FreezeTime >= 6.0\n\t\tFreeze = 0\n\tEndIf\n\tSyncFrozenFx()')
pos=s.index('; ---------------------------------------------------------------- 環狀桶')
s=s[:pos]+''' ; fix round 3: visual transitions only; no extra timer and no gameplay spell.
Function SyncFrozenFx()
	If !FrozenShader || !Holder
		Return
	EndIf
	If Finished || Migrating || Freeze < 5 || Holder.IsDead()
		StopFrozenFx()
	ElseIf !FrozenFxShown
		FrozenFxShown = True
		FrozenShader.Play(Holder)
	EndIf
EndFunction

Function StopFrozenFx()
	If FrozenFxShown
		FrozenFxShown = False
		If FrozenShader && Holder
			FrozenShader.Stop(Holder)
		EndIf
	EndIf
EndFunction

'''.lstrip()+s[pos:]
p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
print('ESSBStatus visual transitions edited; CRLF preserved')
