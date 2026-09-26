Scriptname ESSBMCM extends MCM_ConfigBase
{Optional MCM bridge. Gameplay never references this script.}

Quest Property Controller Auto
; A constant false group disables the read-only GlobalValue rows.
Bool Property AllowTreeEditing = False AutoReadOnly

Function RespecCurrent()
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return
	EndIf
	ESSBTrees trees = GetTrees()
	If !trees
		Return
	EndIf
	Int tree = trees.CurrentTree()
	If ShowMessage("確定洗點：" + trees.TreeName(tree) + "？確認後會關閉目前形態，再洗這棵樹。需脫離戰鬥且冷卻已結束。", True, "確定洗點", "取消")
		; Capture the tree before CloseForm resets CurrentElement to zero.
		; Never close a form when combat/cooldown would reject the request.
		If tree < 11 && !Game.GetPlayer().IsInCombat() && trees.RespecReady(tree)
			ESSBController ctl = Controller.GetAlias(0) as ESSBController
			If ctl
				ctl.CloseForm()
			EndIf
		EndIf
		trees.Respec(tree)
		ForcePageReset()
	EndIf
EndFunction

Function RespecAll()
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return
	EndIf
	ESSBTrees trees = GetTrees()
	If trees && ShowMessage("確定洗點全部技能樹？需脫離戰鬥並關閉形態；冷卻中的樹會略過。", True, "確定洗點", "取消")
		trees.RespecAll()
		ForcePageReset()
	EndIf
EndFunction

Function DumpRegistry()
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return
	EndIf
	If Controller
		ESSBController ctl = Controller.GetAlias(0) as ESSBController
		If ctl
			ctl.DumpStatus()
		EndIf
	EndIf
EndFunction

ESSBTrees Function GetTrees()
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return None
	EndIf
	If Controller
		Return Controller.GetAlias(0) as ESSBTrees
	EndIf
	Return None
EndFunction

Function RestoreDefaults()
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return
	EndIf
	If !ShowMessage("確定恢復全部平衡與一般頁毒層／流血係數的建置預設值？", True, "恢復預設", "取消")
		Return
	EndIf
	; Confirmation yields to the menu: revalidate this quest before any write.
	If Controller != ESSBState.ControllerQuest() || !ESSBState.ReadyUI()
		Return
	EndIf
	ESSBState.RestoreTunableDefaults()
	ESSBController ctl = Controller.GetAlias(0) as ESSBController
	ctl.RefreshRuntimeValues()
	ctl.RefreshTrees()
	ctl.RefreshAbilities()
	ctl.RefreshRecovery()
	ForcePageReset()
	Debug.Notification("元素魔戰士：全部平衡與毒層／流血係數已恢復建置預設值。")
EndFunction

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


Function ApplyNativeSetting()
	GlobalVariable wanted = Game.GetFormFromFile(0x0052D2, "Elements Spellblade.esp") as GlobalVariable
	If wanted
		ESSBNative.SetNativeHit(wanted.GetValueInt() == 1)
	EndIf
	ForcePageReset()
EndFunction

Function ShowNativeStatus()
	String version = ESSBNative.NativeVersion()
	Bool active = ESSBNative.IsNativeHitActive()
	If version == ""
		version = "未載入／版本拒絕"
	EndIf
	ShowMessage("ElementsSpellblade DLL：" + version + "\n命中附傷運作：" + active + "\n停用時不會退回 entry 51。", False, "確定", "")
EndFunction
