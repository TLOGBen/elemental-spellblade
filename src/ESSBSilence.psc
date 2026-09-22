Scriptname ESSBSilence extends ActiveMagicEffect
{沉默（規劃 v0.3 第 5.1 破魔專精主線；規劃 8 的沉默實作備註）。

Skyrim 沒有原生沉默。做法是自有效果把目標魔力鎖在 0 並暫停回復：
  - 本腳本每秒把目標當前魔力扣到 0（DamageActorValue，只動魔力，不動生命）。
  - 同一個法術的第二個效果是 MagickaRateMult 的有害值修正 -100，負責「不回復魔力」。
NPC 沒有魔力就不會施法，等同沉默；尊重免疫，對首領由呼叫端縮短秒數。
只動目標的魔力值，不碰 AI、不上硬直，與其他戰鬥模組不衝突。

本效果掛 ESSB_Silence keyword，「靜寂」分支以它為條件。}

Quest Property Controller Auto

Actor Holder

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If !Controller || Controller != ESSBState.ControllerQuest() || !ESSBState.Operational()
		Return
	EndIf
	Holder = akTarget
	Drain()
	RegisterForSingleUpdate(1.0)
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	; The engine removes registrations after native AME teardown.
EndEvent

Event OnUpdate()
	If !Controller || Controller != ESSBState.ControllerQuest() || !ESSBState.Operational()
		Return
	EndIf
	If !Holder || Holder.IsDead()
		Return
	EndIf
	Drain()
	RegisterForSingleUpdate(1.0)
EndEvent

Function Drain()
	If !Controller || Controller != ESSBState.ControllerQuest() || !ESSBState.Operational()
		Return
	EndIf
	If !Holder
		Return
	EndIf
	Float current = Holder.GetActorValue("Magicka")
	If current > 0.0
		Holder.DamageActorValue("Magicka", current)
	EndIf
EndFunction
