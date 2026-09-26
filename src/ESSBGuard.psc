Scriptname ESSBGuard extends ReferenceAlias
{玩家受擊與擊殺事件（機制前線 round 2）。

同一個 Player 別名上的第三個腳本（ESSBController 是第一個、ESSBTrees 是第二個）。
只做兩件事，兩件都是 PO3 的事件，不開任何每幀或每秒迴圈：

  1. RegisterForHitEventEx／OnHitEx：玩家是受害者。反擊（格擋偵測）、破護、灼身、寒反、靜電、
     土的岩甲「被打 -1」與山岳、風的殘影、土的反震、聖的神佑、毒的毒皮掛在這裡（v0.4 列為 DLL 受擊 N4，
     N4 前留在 Papyrus）。round 21：v0.3 的反噬、冰盾、水鏡、影身隨節點退役拿掉。
  2. RegisterForActorKilled／OnActorKilled：擊殺掛勾（飲血、血承、化灰、連殺；v0.3 的不死已退役）。
     只接受玩家為 akKiller；控制器以最近八名死者去重。
     Tick 只保留狀態快照，不從 IsDead() 推定擊殺歸屬。

每個攻擊者的反制效果都有 3 秒冷卻（規劃 5.3／5.4／5.5 的「每 3 秒一次」），
用 4 格環狀表記錄，不做全場掃描、不配置新陣列。}

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

; 每攻擊者 3 秒冷卻的 4 格環
Actor[] RecentActor
Float[] RecentTime
Int RecentNext
Bool Ready
Bool ArraysInitialised

Event OnInit()
	Setup()
EndEvent

Event OnPlayerLoadGame()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken
		Return
	EndIf
	If RecentTime
		Int i = 0
		While i < 4
			RecentTime[i] = -1000000.0
			i += 1
		EndWhile
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
	If !ArraysInitialised
		RecentActor = new Actor[4]
		RecentTime = new Float[4]
		If !RecentActor || !RecentTime
			Ctl.BreakState()
			Return
		EndIf
		ArraysInitialised = True
		RecentNext = 0
	EndIf
	PO3_Events_Alias.RegisterForHitEventEx(Self)
	PO3_Events_Alias.RegisterForActorKilled(Self)
	Ready = True
	If Ctl.CachedDebugLevel >= 1
		Ctl.LogEvent(1, "guard", "registered hit + kill events")
	EndIf
	RefreshNodeBits()
EndFunction

; ---------------------------------------------------------------- 受擊

Event OnHitEx(ObjectReference akAggressor, Form akSource, Projectile akProjectile, \
	Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked)
	If !Ready || !Enabled || Enabled.GetValueInt() != 1
		Return
	EndIf
	Actor localPlayer = GetActorReference()
	Bool lethal = DivineArmed.GetValueInt() == 1 && localPlayer && localPlayer.GetActorValue("Health") <= 0.0
	If !lethal && !NodeBits && RockArmor.GetValueInt() == 0 && IceShield.GetValueInt() == 0 && WaterMirror.GetValueInt() == 0 && GuardWind.GetValueInt() == 0
		Return
	EndIf
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If !Ctl || Ctl.Enabled.GetValueInt() != 1
		Return
	EndIf
	Actor attacker = akAggressor as Actor
	Actor player = Ctl.ThePlayer()
	If !player || attacker == player
		Return
	EndIf
	Spell sourceSpell = akSource as Spell
	Bool melee = sourceSpell == None && akProjectile == None

	If lethal
		Ctl.OnLethalHitWhileArmed()
	EndIf

	; 5.1 大師熟練分支「反擊」：格擋成功後 3 秒內下一次命中吸魔 ×2（格擋偵測 N4 前在這裡；吸魔 ×2 由 DLL 讀視窗）。
	If abHitBlocked && ESSBNodes.Br(Ctl, 11, 0, 1, 0) ; @node 反擊
		Ctl.SetRiposte(3)
	EndIf

	; 5.1 滅法大師分支「破護」：不受元素披風反傷（第一跳仍會吃到）。
	; 判定＝來源是法術、沒有投射物、攻擊者身上帶原版 MagicCloak 效果。v0.3 的「反噬」分支已退役。
	If sourceSpell && akProjectile == None && ESSBNodes.Br(Ctl, 11, 1, 3, 0) && attacker \
		&& Ctl.CloakKeyword && attacker.HasMagicEffectWithKeyword(Ctl.CloakKeyword) ; @node 破護
		Ctl.SetCloakGuard(2)
	EndIf

	If Ctl.FormActive.GetValueInt() != 1
		Return
	EndIf
	Int element = Ctl.CurrentElement.GetValueInt()

	; Resolve retaliation against the pre-hit layers; only a failed trigger loses one.
	Int rockBefore = Ctl.GetSelf(2)
	Bool retaliated = False
	If melee && attacker
		retaliated = ESSBElem2.OnEarthRetaliate(Ctl, attacker, rockBefore)
	EndIf
	; 5.6 持續傳奇分支「山岳」：同調三段時岩甲不因被打減少。
	If !retaliated && rockBefore > 0 && !(ESSBNodes.Br(Ctl, 3, 0, 4, 0) && Ctl.SyncStage() >= 3) ; @node 山岳
		Ctl.ConsumeRockArmor()
	EndIf

	; 5.7 持續大師分支「殘影」：風勢滿時被近戰命中 30% 機率讓下一次攻擊無效（消耗風勢）。
	; v0.3 的「冰盾」「水鏡」（被打消耗一層）與「影身」v0.4 已退役（冰盾改成冰的基礎機制，N4）。
	If melee && ESSBNodes.Br(Ctl, 4, 0, 3, 0) && Ctl.GetSelf(3) >= ESSBElem2.WindThreshold(Ctl) ; @node 殘影
		If Utility.RandomFloat(0.0, 1.0) < 0.3
			Ctl.ClearSelf(3)
			Ctl.SetGuardWind(2)
			If Ctl.CachedDebugLevel >= 1
				Ctl.LogThrottled(1, "node", "wind afterimage")
			EndIf
		EndIf
	ElseIf Ctl.GetGuardWindLeft() > 0
		; 視窗已經抵掉一次攻擊，立刻關掉，不讓它白吃第二次。
		Ctl.SetGuardWind(0)
	EndIf

	If !attacker || !melee || !TakeAttacker(attacker)
		Return
	EndIf
	; 5.10 持續熟練分支「毒皮」：被近戰命中時攻擊者中毒 +2 劑。
	If element == 8
		ESSBElem3.OnPoisonSkin(Ctl, attacker)
	EndIf
	; 5.3 持續大師分支「灼身」：被近戰命中時攻擊者掛你的火印記並受一次火傷，每個攻擊者 3 秒一次（TakeAttacker）。
	If element == 1 && ESSBNodes.Br(Ctl, 0, 0, 3, 0) ; @node 灼身
		Ctl.ApplyMark(attacker, 1)
		Ctl.ApplyDamage(1, ESSBReactions.ReactDamage(Ctl, 1, 1.0), attacker)
		If Ctl.CachedDebugLevel >= 2
			Ctl.LogThrottled(2, "node", "fire scorch " + attacker.GetFormID())
		EndIf
	EndIf
	; 5.4 持續大師分支「寒反」：攻擊你的敵人被減速，且凍結 +1（每個攻擊者 3 秒一次，TakeAttacker）。
	If element == 2 && ESSBNodes.Br(Ctl, 1, 0, 3, 1) ; @node 寒反
		Ctl.ApplyUtil(0, 30.0, 3, attacker)
		Ctl.AddStackTo(attacker, 2, 1)
	EndIf
	; 5.5 持續熟練分支「靜電」：被近戰命中時攻擊者感電＝掛上你的雷印記（每個攻擊者 3 秒一次，TakeAttacker）。
	If element == 3 && ESSBNodes.Br(Ctl, 2, 0, 1, 1) ; @node 靜電
		Ctl.ApplyMark(attacker, 3)
	EndIf
EndEvent

; 每個攻擊者 3 秒一次。4 格環狀表，滿了就覆蓋最舊的一格。
Bool Function TakeAttacker(Actor akAttacker)
	If !Ctl || !Ctl.IsOperational() || !ArraysInitialised
		Return False
	EndIf
	If !akAttacker
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int index = 0
	While index < 4
		If RecentActor[index] == akAttacker
			If now - RecentTime[index] < Ctl.CooldownSeconds(3.0)
				Return False
			EndIf
			RecentTime[index] = now
			Return True
		EndIf
		index += 1
	EndWhile
	RecentActor[RecentNext] = akAttacker
	RecentTime[RecentNext] = now
	RecentNext += 1
	If RecentNext >= 4
		RecentNext = 0
	EndIf
	Return True
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

Function RefreshNodeBits()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken
		Return
	EndIf
	; 受擊時要做事的節點（毒皮、反震、反擊、破護、灼身、寒反、靜電、山岳、殘影）；都沒投就走快速路徑。
	NodeBits = ESSBNodes.Br(Ctl, 7, 0, 1, 1) || ESSBNodes.Br(Ctl, 3, 0, 3, 1) || ESSBNodes.Br(Ctl, 11, 0, 1, 0) || ESSBNodes.Br(Ctl, 11, 1, 3, 0) \
		|| ESSBNodes.Br(Ctl, 0, 0, 3, 0) || ESSBNodes.Br(Ctl, 1, 0, 3, 1) || ESSBNodes.Br(Ctl, 2, 0, 1, 1) \
		|| ESSBNodes.Br(Ctl, 3, 0, 4, 0) || ESSBNodes.Br(Ctl, 4, 0, 3, 0) ; @node 毒皮, 反震, 反擊, 破護, 灼身, 寒反, 靜電, 山岳, 殘影
EndFunction
