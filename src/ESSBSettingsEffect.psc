Scriptname ESSBSettingsEffect extends ActiveMagicEffect
{技能樹力量。設定、洗點與除錯控制已移至 MCM。
選項順序與 ESSB_SettingsMenu 一致：0 元素樹、1 通用樹、2 關閉。}

Message Property SettingsMenu Auto
GlobalVariable Property Enabled Auto
GlobalVariable Property DebugLevel Auto
Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0，上面掛 ESSBController 與 ESSBTrees}

Bool Handled

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If Handled
		Return
	EndIf
	Handled = True
	; Retired spell instances cannot redirect into the new controller generation.
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	ESSBController ctl = GetController()
	If !ctl || !ctl.IsReadyUI()
		Debug.Notification("元素魔戰士：尚未就緒")
		Return
	EndIf
	ESSBTrees trees = GetTrees()
	If !trees || !trees.BeginSettings()
		Return
	EndIf
	Int choice = SettingsMenu.Show()
	trees.FinishSettings(choice)
EndEvent

; Retained callable controls; the lesser-power menu no longer invokes them.
Function ToggleEnabled()
	Enabled.SetValueInt(1 - Enabled.GetValueInt())
	ESSBLog.Log(1, "settings", "enabled=" + Enabled.GetValueInt())
EndFunction

Function CycleDebugLevel()
	DebugLevel.SetValueInt((DebugLevel.GetValueInt() + 1) % 4)
	ESSBController ctl = GetController()
	If ctl
		ctl.RefreshRuntimeValues()
	EndIf
	ESSBLog.Log(1, "settings", "debug level=" + DebugLevel.GetValueInt())
EndFunction

ESSBController Function GetController()
	Controller = ESSBState.ControllerQuest()
	If !Controller
		Debug.Notification("元素魔戰士：控制器未就緒")
		Return None
	EndIf
	ESSBController controllerAlias = Controller.GetAlias(0) as ESSBController
	If !controllerAlias
		Debug.Notification("元素魔戰士：控制器未就緒")
	EndIf
	Return controllerAlias
EndFunction

ESSBTrees Function GetTrees()
	ESSBController ctl = GetController()
	If !ctl || !ctl.IsReadyUI()
		Return None
	EndIf
	If !Controller
		Debug.Notification("元素魔戰士：技能樹未就緒")
		Return None
	EndIf
	ESSBTrees trees = Controller.GetAlias(0) as ESSBTrees
	If !trees
		Debug.Notification("元素魔戰士：技能樹未就緒")
	EndIf
	Return trees
EndFunction
