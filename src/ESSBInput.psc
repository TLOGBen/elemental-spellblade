Scriptname ESSBInput extends ReferenceAlias
{Lightweight input: native GLOB publication precedes the busy Controller call.}
ESSBController Property Ctl Auto
GlobalVariable Property Enabled Auto
GlobalVariable Property CurrentElement Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property HotkeysEnabled Auto
GlobalVariable[] Property Hotkeys Auto
GlobalVariable Property FormNotify Auto
GlobalVariable Property FreeOpen Auto
Bool Ready
Bool FreePass

Event OnInit()
	Setup()
EndEvent

Event OnPlayerLoadGame()
	Ready = False
	Setup()
EndEvent

Function Setup()
	Ready = False
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If !Enabled || !CurrentElement || !FormActive || !HotkeysEnabled || !FormNotify || !FreeOpen || !Hotkeys
		Ctl.BreakState()
		Return
	EndIf
	If Hotkeys.Length != 11
		Ctl.BreakState()
		Return
	EndIf
	Int checkKey = 0
	While checkKey < Hotkeys.Length
		If !Hotkeys[checkKey]
			Ctl.BreakState()
			Return
		EndIf
		checkKey += 1
	EndWhile
	UnregisterForAllKeys()
	RegisterForMenu("Journal Menu")
	RefreshPermission()
	If HotkeysEnabled.GetValueInt() == 1
		Int i = 0
		While i < 11
			Int keyCode = Hotkeys[i].GetValueInt()
			If keyCode > 0
				RegisterForKey(keyCode)
			EndIf
			i += 1
		EndWhile
	EndIf
	Ready = True
EndFunction

Function RefreshPermission()
	If Ctl && Ctl.IsCurrentController() && !Ctl.StateBroken
		FreePass = Ctl.Br(12, 1, 1, 0)
	EndIf
EndFunction

Event OnMenuClose(String asMenuName)
	If asMenuName == "Journal Menu"
		Setup()
	EndIf
EndEvent

Event OnKeyDown(Int keyCode)
	If !Ready || HotkeysEnabled.GetValueInt() != 1 || Utility.IsInMenuMode() || UI.IsTextInputEnabled()
		Return
	EndIf
	Int i = 0
	While i < 11
		If Hotkeys[i].GetValueInt() == keyCode
			RequestSwitch(i + 1)
			Return
		EndIf
		i += 1
	EndWhile
EndEvent

Function RequestSwitch(Int aiElement)
	If !Ready || !Ctl || Ctl.StateBroken || aiElement < 1 || aiElement > 11 || Enabled.GetValueInt() != 1
		Return
	EndIf
	; Native quest identity check does not acquire the Controller's script lock.
	If GetOwningQuest() != ESSBState.ControllerQuest()
		Return
	EndIf
	Actor player = GetActorReference()
	If !player || player.IsDead()
		Return
	EndIf
	Int active = FormActive.GetValueInt()
	Int previous = CurrentElement.GetValueInt()
	If active == 0 && !FreePass && FreeOpen.GetValueInt() <= 0 && player.GetActorValue("Magicka") < player.GetActorValueMax("Magicka") * 0.1
		Debug.Notification("魔力不足，無法開啟形態")
		Return
	EndIf
	If active == 1 && previous == aiElement
		FormActive.SetValueInt(0)
		CurrentElement.SetValueInt(0)
	Else
		CurrentElement.SetValueInt(aiElement)
		FormActive.SetValueInt(1)
	EndIf
	If FormNotify.GetValueInt() == 1
		If FormActive.GetValueInt() == 0
			Debug.Notification("元素魔戰士：關閉形態")
		Else
			Debug.Notification("元素魔戰士：" + FormLabel(aiElement))
		EndIf
	EndIf
	; Consume the existing one-use permission only after publishing the engine selection.
	If active == 0
		Ctl.SetFreeOpen(0)
	EndIf
	Ctl.SwitchForm(aiElement)
EndFunction

String Function FormLabel(Int aiElement)
	If aiElement == 1
		Return "火焰"
	ElseIf aiElement == 2
		Return "冰霜"
	ElseIf aiElement == 3
		Return "雷電"
	ElseIf aiElement == 4
		Return "大地"
	ElseIf aiElement == 5
		Return "風"
	ElseIf aiElement == 6
		Return "鮮血"
	ElseIf aiElement == 7
		Return "神聖"
	ElseIf aiElement == 8
		Return "毒素"
	ElseIf aiElement == 9
		Return "水"
	ElseIf aiElement == 10
		Return "黑暗"
	ElseIf aiElement == 11
		Return "星界"
	EndIf
	Return ""
EndFunction
