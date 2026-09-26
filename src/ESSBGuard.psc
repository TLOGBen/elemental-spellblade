Scriptname ESSBGuard extends ReferenceAlias
{玩家的擊殺事件（機制前線 round 2；round 23 起只剩這一件）。

同一個 Player 別名上的第三個腳本（ESSBController 是第一個、ESSBTrees 是第二個）。

  RegisterForActorKilled／OnActorKilled：擊殺掛勾（飲血、血承、化灰、連殺；v0.3 的不死已退役）。
  只接受玩家為 akKiller；控制器以最近八名死者去重。死亡處理是 DLL N5，到那時才搬。

Round 23（N4，裁定 R6）：玩家受擊整條搬進 DLL（native/include/Hurt.h：TESHitEvent 目標是你的那一支）。
這裡的 OnHitEx（反擊、破護、灼身、寒反、靜電、岩甲被打 -1 與山岳、殘影、反震、毒皮、神佑的致命一擊）與
它的每攻擊者 3 秒環、節點位元一起刪除；Setup 每次載入都把舊存檔登記過的受擊事件解除。
屬性保留原本的 VMAD 版面（產生器照舊填），腳本不再讀它們。}

GlobalVariable Property Enabled Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property DivineArmed Auto
GlobalVariable Property RockArmor Auto
GlobalVariable Property IceShield Auto
GlobalVariable Property WaterMirror Auto
GlobalVariable Property GuardWind Auto
Bool Property NodeBits Auto
ESSBController Property Ctl Auto
{ESSB_MainQuest 的別名 0，就是 ESSBController 自己。}

Bool Ready

Event OnInit()
	Setup()
EndEvent

Event OnPlayerLoadGame()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken
		Return
	EndIf
	Ready = False
	Setup()
EndEvent

Function Setup()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken
		Return
	EndIf
	If Ready
		Return
	EndIf
	; round 23：受擊在 DLL；舊存檔的 OnHitEx 登記會跟著存檔走，載入時解除。
	PO3_Events_Alias.UnregisterForAllHitEventsEx(Self)
	PO3_Events_Alias.RegisterForActorKilled(Self)
	Ready = True
	If Ctl.CachedDebugLevel >= 1
		Ctl.LogEvent(1, "guard", "registered kill events (hits are native)")
	EndIf
EndFunction

; ---------------------------------------------------------------- 擊殺

Event OnActorKilled(Actor akVictim, Actor akKiller)
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If !Ctl || !akVictim
		Return
	EndIf
	Actor player = Ctl.ThePlayer()
	If !player || akKiller != player
		Return
	EndIf
	Ctl.OnKillEvent(akVictim, akKiller)
EndEvent
