from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name):return (ROOT/name).read_text(encoding='utf-8-sig')
def write(name,text):
 p=ROOT/name;raw=p.read_bytes() if p.exists() else b''
 bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
 nl='\r\n' if b'\r\n' in raw else '\n'
 p.write_bytes(bom+text.replace('\r\n','\n').replace('\n',nl).encode('utf8'))
def replace(name,old,new,count=1):
 s=read(name);assert s.count(old)==count,(name,old,s.count(old));write(name,s.replace(old,new))
def ledger(item,text):
 p='.codex/impl-fix-round16.html';s=read(p);s=s.replace(item+'：待處理',item+'：'+text);write(p,s)

if __name__=='__main__':
 c='src/ESSBController.psc'
 replace(c,'\t\t\tIf player && target.GetDistance(player) <= radius','\t\t\tIf target.IsDead()\n\t\t\t\tCaptureDeath(index)\n\t\t\t\tClearSlot(index)\n\t\t\tElseIf player && target.GetDistance(player) <= radius')
 replace(c,'\t; Detach and promote before any cross-script call can deliver an AME callback.','\tBool dead = target.IsDead()\n\tIf dead\n\t\tCaptureDeath(aiSlot)\n\tEndIf\n\t; Detach and promote before any cross-script call can deliver an AME callback.')
 replace(c,'\tIf !abAllowed\n\t\tReturn','\tIf dead || target.IsDead() || !abAllowed\n\t\tReturn')
 replace('src/ESSBReactions.psc','Function End(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Bool abChain = False) Global\n\tIf !akCtl || !akTarget || aiElement < 1 || aiElement > 11','Function End(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Bool abChain = False) Global\n\tIf !akCtl || !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11')
 ledger('A1 屍體融斷','已修正死亡捕獲、清格、終焉與 XP 守衛；待回歸')
 for fn in ['RefreshAbilities','RefreshDivineProtection']:
  replace(c,f'Function {fn}()\n',f'Function {fn}()\n\tIf !IsCurrentController()\n\t\tReturn\n\tEndIf\n')
 replace('src/ESSBTrees.psc','If Controller\n\t\tController.RefreshAbilities()','If Controller && Controller.IsOperational()\n\t\tController.RefreshAbilities()',2)
 replace('src/ESSBTrees.psc','If Controller && abRefreshAbilities','If Controller && abRefreshAbilities && Controller.IsOperational()')
 write(c,read(c)+'''\n; Explicit maintenance release: disabling prevents tick/combat/setup from rearming.
Function ReleaseDivineProtection()
	If !IsCurrentController()
		Return
	EndIf
	Enabled.SetValueInt(0)
	DivineArmed = False
	DivineSaveUsed = True
	Actor player = ThePlayer()
	If player
		player.EndDeferredKill()
	EndIf
EndFunction
''')
 write('src/ESSBMCM.psc',read('src/ESSBMCM.psc')+'''
Function ReleaseDivineProtection()
	If !ShowMessage("解除神佑保護並停用模組？解除後可正常死亡。卸載前請解除並存檔；一般頁重新啟用模組可恢復功能。", True, "解除保護", "取消")
		Return
	EndIf
	; Always resolve the current quest, even when gameplay is disabled/broken.
	Quest currentQuest = ESSBState.ControllerQuest()
	ESSBController ctl
	If currentQuest
		ctl = currentQuest.GetAlias(0) as ESSBController
	EndIf
	If ctl
		ctl.ReleaseDivineProtection()
	Else
		Game.GetPlayer().EndDeferredKill()
	EndIf
	ForcePageReset()
	Debug.Notification("元素魔戰士：已解除神佑保護並停用模組；卸載前請存檔。")
EndFunction
''')
 replace('build_v03.py',"assert functions == {'RespecCurrent', 'RespecAll', 'DumpRegistry', 'RestoreDefaults'}","assert functions == {'RespecCurrent', 'RespecAll', 'DumpRegistry', 'RestoreDefaults', 'ReleaseDivineProtection'}")
 replace('build_v03.py',"    balance.append(button('ESSB_RestoreDefaults'","    balance.append(button('ESSB_ReleaseDivineProtection', '解除神佑保護', 'ReleaseDivineProtection',\n                          '確認後解除延遲死亡並停用模組，避免重新上鎖；卸載前請先解除並存檔。'))\n    balance.append(button('ESSB_RestoreDefaults'")
 ledger('A2 神佑解除與世代守衛','已加世代守衛及 MCM 確認解除；停用避免再上鎖；保留 Setup 無條件 EndDeferredKill')
 replace('src/ESSBStatus.psc','\t\t; Encode the original due time even when host binding arrived late.\n\t\tFreezeTime = afDeadline - FreezeSeconds','\t\t; Deadline is already scaled. Never put a start timestamp in the future.\n\t\tFreezeSeconds = afDeadline - FreezeTime\n\t\tIf FreezeSeconds <= 0.0\n\t\t\tFreezeSeconds = 0.01\n\t\t\tFreezeTime = afDeadline - FreezeSeconds\n\t\tEndIf')
 ledger('A3 pending 冰封','已改以綁定時刻及剩餘秒數保存原期限，避免二次縮放／未來起點')
