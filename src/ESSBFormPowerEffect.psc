Scriptname ESSBFormPowerEffect extends ActiveMagicEffect
{形態力量（規劃 v0.3 第 1 節）：按 Z 施放「形態：火焰」等 11 個 Lesser Power，
交給控制器決定開啟、切換或關閉。腳本本身不做任何等待。}

Int Property ElementIndex Auto
{1..11，對應 火焰 冰霜 雷電 大地 風 鮮血 神聖 毒素 水 黑暗 星界}

Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Event OnEffectStart(Actor akTarget, Actor akCaster)
	Controller = ESSBState.ControllerQuest()
	If !Controller
		Return
	EndIf
	; round 25（N6，裁定 R6）：Z 路線與熱鍵呼叫同一個切換函式（DLL：魔力門檻、全域變數、提示，再 ESSB_Switch 回控制器）。
	ESSBNative.RequestSwitch(ElementIndex)
EndEvent
