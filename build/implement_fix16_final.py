from implement_fix16 import *
import re
c='src/ESSBController.psc';b='build_v03.py'
windows=[('GuardSwitch','GGuardSwitch'),('GuardBurst','GGuardBurst'),('GuardIce','GGuardIce'),('GuardWind','GGuardWind'),('GuardDivine','GGuardDivine'),('CloakGuard','GCloakGuard'),('GuardDark','GGuardDark'),('GuardAstral','GGuardAstral'),('GuardStar','GGuardStar')]
for i,(name,glob) in enumerate(windows):
 s=read(c);start=s.index('Function Set'+name+'(');end=s.index('EndFunction',start)
 part=s[start:end];part+=f'\tApplyGuardWindow({i}, {name}Left)\n';write(c,s[:start]+part+s[end:])
for name,glob in [('GuardWind','GGuardWind'),('GuardDark','GGuardDark')]:
 replace(c,f'\tReturn SecondsLeft({name}Left)',f'\tInt left = SecondsLeft({name}Left)\n\tSetGlobal({glob}, left)\n\tReturn left')
write(c,read(c)+'''
; PERK reads native active-effect lifetime. A stale mirror alone grants no protection.
Function ApplyGuardWindow(Int aiIndex, Float afDeadline)
	Actor player = ThePlayer()
	Spell window = ESSBState.GuardWindowSpell(aiIndex)
	If !player || !window
		Return
	EndIf
	player.DispelSpell(window)
	Int seconds = SecondsLeft(afDeadline)
	If seconds > 0
		window.SetNthEffectDuration(0, seconds)
		player.DoCombatSpellApply(window, player)
	EndIf
EndFunction

Function ClearGuardWindows()
	Int i = 0
	While i < 9
		ApplyGuardWindow(i, 0.0)
		i += 1
	EndWhile
EndFunction
''')
replace(c,'Function ResetLoadClock()\n','Function ResetLoadClock()\n\tClearGuardWindows()\n')
replace(c,'\tEnabled.SetValueInt(0)\n\tDivineArmed = False','\tEnabled.SetValueInt(0)\n\tClearGuardWindows()\n\tDivineArmed = False')
# New native marker records are appended in the next free non-quest range.
replace(b,'def gv_ge(fid, value):',"GUARD_WINDOWS = "+repr([n for n,g in windows])+"\nID_GUARD_WINDOW = 0x005170\nGUARD_WINDOW_EDIDS = {f'ESSB_{kind}_{name}' for name in GUARD_WINDOWS for kind in ('WindowEffect', 'WindowSpell')}\n\ndef guard_window(index):\n    # HasMagicEffect (214) is evaluated by the engine at the PERK read.\n    return ctda(CTDA_EQ, 1.0, 214, param1=own(ID_GUARD_WINDOW + index * 2))\n\n\ndef gv_ge(fid, value):")
conds=['ID_MECH_GLOB + 13','ID_MECH_GLOB + 14','ID_MECH_GLOB + 15','mech2(4)','mech2(5)','mech2(10)','mech3(1)','mech3(2)','mech3(3)']
for i,cond in enumerate(conds):replace(b,f'gv_ge({cond}, 1)',f'guard_window({i})')
replace(b,'    # -------------------------------------------------------------- 輔助效果（減速、碎甲、削魔耐、回復、放血）', '''    # FIX16: native-duration markers; no Papyrus AME, no update polling.
    for index, name in enumerate(GUARD_WINDOWS):
        effect = ID_GUARD_WINDOW + index * 2
        add('MGEF', effect, f'ESSB_WindowEffect_{name}', [
            ('FULL', Z(name)), ('DATA', mgef_data(MGEF_MARKER_FLAGS, 1, casting=1, delivery=0)),
        ])
        add('SPEL', effect + 1, f'ESSB_WindowSpell_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(name)),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(0, 1, 0)), ('EFID', I(own(effect))),
            ('EFIT', struct.pack('<fII', 0.0, 0, 2)),
        ])

    # -------------------------------------------------------------- 輔助效果（減速、碎甲、削魔耐、回復、放血）''')
replace(b,"    for name, value in funcs:",'''    lines += ['Spell Function GuardWindowSpell(Int aiIndex) Global',
              '\\tIf aiIndex < 0 || aiIndex >= 9', '\\t\\tReturn None', '\\tEndIf',
              f'\\tReturn Game.GetFormFromFile(0x{ID_GUARD_WINDOW + 1:06X} + aiIndex * 2, "Elements Spellblade.esp") as Spell',
              'EndFunction', '']
    for name, value in funcs:''')
replace(b,"assert set(added) == FIX5_NEW_EDIDS | {e for e, (fid, _) in ID_BALANCE_GLOB.items() if fid >= 0x00515C}","assert set(added) == FIX5_NEW_EDIDS | GUARD_WINDOW_EDIDS | {e for e, (fid, _) in ID_BALANCE_GLOB.items() if fid >= 0x00515C}")
replace('build/state_schema.py','assert set(added)==set(stub_ids(version))','assert set(added)==set(stub_ids(version)) | b.GUARD_WINDOW_EDIDS')
# Preserve the lock file's existing CRLF when the approved migration is generated.
replace('build/state_schema.py',"        path.write_text(json.dumps(lock, ensure_ascii=False, indent=2)+'\\n', encoding='utf8')","        raw=path.read_bytes();nl='\\r\\n' if b'\\r\\n' in raw else '\\n'\n        path.write_bytes((json.dumps(lock, ensure_ascii=False, indent=2)+'\\n').replace('\\n',nl).encode('utf8'))")
ledger('B1.6 PERK 視窗','九種防護 PERK 已改讀原生限時 MGEF；不再以延遲鏡射值作減傷條件；讀取 getter 亦同步清鏡射')
# Predict once from health before dispatch. Non-lethal applications carry NO claim.
replace(c,'\tKillProcUntil[i] = Utility.GetCurrentRealTime() + ESSBState.KillAttributionSeconds()', '''\tFloat beforeHealth = akTarget.GetActorValue("Health")
	If beforeHealth > 0.0 && afAmount >= beforeHealth
		KillProcUntil[i] = -1.0
	Else
		KillProcActor[i] = None
		KillProcUntil[i] = 0.0
	EndIf''')
s=read(c);start=s.index('\tInt proc = 0\n',s.index('Function CaptureDeath'));end=s.index('\tSettleDeadCurse(aiSlot)',start);write(c,s[:start]+s[end:])
replace(c,'\t\t\tIf due == -1.0 || due >= now','\t\t\tIf due == -1.0')
# Actual pre-damage scaled spell magnitude is available in ApplyDamage; move arming there.
# Callers keep ownership of kind/amount and remain ordered before native application.
ledger('B1.9 預測致死','已以傷害前生命比較預測致死；未致死不武裝，移除三秒兌現視窗；待延遲捕獲回歸')
ledger('B1.10 斷咒延遲','斷咒僅持有節點時在命中回呼入口讀施法狀態；接受事件處理延遲，不宣稱原生碰撞時刻')
# Historical progress ledgers are outside this round's write set.
replace('build/fix15_verify.py','  ledger(cases)','  # FIX16: historical ledger is read-only.')
