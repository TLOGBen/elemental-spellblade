Scriptname ESSBMark extends ActiveMagicEffect
{印記（規劃 v0.3 第 2.2、2.6 節）。

每個元素一個自有 MGEF／SPEL，由控制器在 OnWeaponHit 的附傷之後以 DoCombatSpellApply 套上。
本腳本只做兩件事：把自己這個實體登記給控制器（OnEffectStart），以及回報結束（OnEffectFinish）。
「是被切掉、融斷、逐出，還是自然過期」由控制器的登記表判定，不在這裡猜，
因此不會重複觸發終焉（規劃 8：過期終焉需分辨 Dispel 與自然結束）。}

Int Property ElementIndex Auto
{1..11，對應 火焰 冰霜 雷電 大地 風 鮮血 神聖 毒素 水 黑暗 星界}

Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Actor Holder
ESSBController Ctl
Bool Finished = False

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	Holder = akTarget
	If !Controller
		Return
	EndIf
	Ctl = Controller.GetAlias(0) as ESSBController
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If !Finished && Ctl && akTarget
		Ctl.OnMarkStart(ElementIndex, akTarget, Self)
	EndIf
EndEvent

; Called instead of the native Dispel by delayed controller callbacks.
Function DispelIfActive()
	If !Finished
		Finished = True
		Dispel()
	EndIf
EndFunction

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	Finished = True
	If Ctl && Holder && Controller == ESSBState.ControllerQuest() && Ctl.IsOperational()
		Ctl.OnMarkFinish(ElementIndex, Holder, Self)
	EndIf
EndEvent
