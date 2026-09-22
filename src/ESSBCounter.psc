Scriptname ESSBCounter extends ActiveMagicEffect
{破魔印 AME 只通知穩定的 ESSBController alias 註冊／清理施法事件。
目標身上的自有破魔印效果決定有效期；刷新不會被舊 AME 的 finish 取消。
保留既有成員 layout，舊 AME 排隊的動畫事件不再造成反咒。}

Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Actor Holder
ESSBController Ctl
Bool Listening

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If Controller != ESSBState.ControllerQuest() || !akTarget
		Return
	EndIf
	Holder = akTarget
	Ctl = Controller.GetAlias(0) as ESSBController
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	Listening = True
	Ctl.StartCounter(akTarget)
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	Listening = False
	If Controller != ESSBState.ControllerQuest() || !Ctl
		Return
	EndIf
	; Only the persistent alias calls registration natives, including cleanup.
	Ctl.StopCounter(akTarget)
EndEvent

Event OnAnimationEvent(ObjectReference akSource, String asEventName)
	; Legacy queued AME events are deliberately inert, even across a same-schema upgrade.
	If !Listening
		Return
	EndIf
EndEvent
