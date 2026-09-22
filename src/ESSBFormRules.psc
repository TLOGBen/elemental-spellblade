Scriptname ESSBFormRules extends ActiveMagicEffect
{fix round 8：所有形態每秒付最大魔力百分比維持費，暗形態使用獨立基礎比例。
樹等級降低魔力維持費；血形態另保留血位曲線與留 1 HP 保護。
維持費倍率各套一次；不影響血重擊費。魔力歸零後有 2 秒寬限，再走正常 CloseForm。
只沿用形態啟用期間的 RegisterForSingleUpdate，不新增更新迴圈。}

GlobalVariable Property FormActive Auto
GlobalVariable Property CurrentElement Auto
Float Property UpkeepBasePct = 1.0 Auto
Float Property UpkeepDarkPct = 2.0 Auto
Float Property UpkeepLevelRelief = 0.7 Auto
Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Actor Holder
ESSBController Ctl
Float MagickaEmptySince = -1.0

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	Holder = akTarget
	If !Controller
		Return
	EndIf
	Ctl = Controller.GetAlias(0) as ESSBController
	RegisterForModEvent("ESSB_FormRulesReady", "OnRulesReady")
	RegisterForModEvent("ESSB_FormChanged", "OnESSBFormChanged")
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	RegisterForModEvent("ESSB_FormChanged", "OnESSBFormChanged")
	If FormActive.GetValueInt() == 1
		RegisterForSingleUpdate(1.0)
	EndIf
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	MagickaEmptySince = -1.0
	; The engine removes registrations after native AME teardown.
EndEvent

Event OnESSBFormChanged(String asEventName, String asStringArg, Float afNumArg, Form akSender)
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If FormActive.GetValueInt() == 1
		RegisterForSingleUpdate(1.0)
	Else
		MagickaEmptySince = -1.0
		UnregisterForUpdate()
	EndIf
EndEvent

Float Function MagickaUpkeep(Int aiElement)
	Int level = 1
	If Ctl.Trees
		level = Ctl.Trees.TreeLevel(aiElement - 1)
	EndIf
	If level > 100
		level = 100
	ElseIf level < 1
		level = 1
	EndIf
	Float pct = UpkeepBasePct
	If aiElement == 10
		pct = UpkeepDarkPct
	EndIf
	Return Holder.GetActorValueMax("Magicka") * pct * 0.01 * (1.0 - UpkeepLevelRelief * level / 100.0) * Ctl.MultUpkeep.GetValue()
EndFunction

Event OnUpdate()
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	If !Ctl && Controller
		Ctl = Controller.GetAlias(0) as ESSBController
	EndIf
	If !Ctl || Ctl.StateBroken
		Return
	EndIf
	If !Ctl.IsOperational()
		RegisterForSingleUpdate(1.0)
		Return
	EndIf
	If FormActive.GetValueInt() != 1 || !Holder
		MagickaEmptySince = -1.0
		Return
	EndIf
	If Ctl
		Int element = CurrentElement.GetValueInt()
		If Holder.GetActorValue("Magicka") > 0.0
			MagickaEmptySince = -1.0
		EndIf
		If element == 6
			Ctl.PayBloodCost(Ctl.BloodDrainPerSecond() * Ctl.MultUpkeep.GetValue())
		EndIf
		; 血形態只付血位扣血（使用者 2026-09-18 決定），不扣魔力，也不受魔力歸零自動關閉。
		Float cost = 0.0
		If element != 6
			cost = MagickaUpkeep(element)
		EndIf
		Float current = Holder.GetActorValue("Magicka")
		If cost > current
			cost = current
		EndIf
		If cost > 0.0
			Holder.DamageActorValue("Magicka", cost)
		EndIf
		If element != 6 && Holder.GetActorValue("Magicka") <= 0.0
			Float now = Utility.GetCurrentRealTime()
			If MagickaEmptySince < 0.0
				MagickaEmptySince = now
			ElseIf now - MagickaEmptySince >= 2.0
				MagickaEmptySince = -1.0
				Ctl.CloseForm()
				Debug.Notification("魔力耗盡，形態已關閉")
				Return
			EndIf
		EndIf
	EndIf
	If FormActive.GetValueInt() == 1
		RegisterForSingleUpdate(1.0)
	EndIf
EndEvent

Event OnRulesReady(String asEventName, String asStringArg, Float afNumArg, Form akSender)
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	Ctl = Controller.GetAlias(0) as ESSBController
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	MagickaEmptySince = -1.0
	UnregisterForUpdate()
	If FormActive.GetValueInt() == 1
		RegisterForSingleUpdate(1.0)
	EndIf
EndEvent
