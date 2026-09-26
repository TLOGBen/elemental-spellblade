Scriptname ESSBReactions Hidden
{反應本體：開印與終焉（規劃 v0.4 第 2.6、2.7 節）。

Round 22（N3）起，印記、層數、階梯都是 DLL 掛在目標與玩家身上的引擎效果：DLL 在命中那一幀決定開印／刷新／被切，
做完開印與終焉的「狀態部分」（加層、消耗、冰封、催毒、導引、死咒引信、星痕引爆……），再用 ModEvent 把這裡的
「本體」叫起來（傷害、削減、回復、推力、範圍掃描）。本體只經 ESSBNative 讀寫狀態，自己不存任何東西（裁定 R4：
反應本體到 N5 才搬進 DLL）。

公式（2.7）：D_react = B_max × K_react × G(L) × M_mod × M_ext × (1 − Res)
  B_max 取自 settings.json element_damage 的上限欄；G(L) 由 ESSBController.ApplyDamage 統一乘上，
  所以本檔算出來的都是「還沒乘 G(L)」的值。M_ext 與 (1 − Res) 由引擎結算。

終焉理由 aiReason：0 被切掉、1 融斷、2 自然過期（第 9 目標逐出隨登記表一起消失）。
Round 23（N4）起你的資源（電荷、岩甲、風勢、同調）也是 DLL 的效果：開印的 +2、導引的同調跳段、協奏／三重奏／
過載終焉的倍率、雷終焉放電用哪一份電荷與它的消耗都在 DLL，這裡只拿 ESSB_End 帶來的值。}

; fix round 4: settings.json element_damage -> QUST VMAD float arrays.
Float Function BaseMax(ESSBController akCtl, Int aiElement) Global
	If aiElement < 1 || aiElement > 11 || !akCtl
		Return 0.0
	EndIf
	Return akCtl.ElementDamageMax[aiElement - 1]
EndFunction

Float Function BaseMin(ESSBController akCtl, Int aiElement) Global
	If aiElement < 1 || aiElement > 11 || !akCtl
		Return 0.0
	EndIf
	Return akCtl.ElementDamageMin[aiElement - 1]
EndFunction

; D_react 的本模組部分：B_max × K_react × M_mod。G(L) 由 ApplyDamage 統一乘上（規劃 2.7）。
Float Function ReactDamage(ESSBController akCtl, Int aiElement, Float afK) Global
	Return BaseMax(akCtl, aiElement) * afK * akCtl.GetDamageMult(aiElement)
EndFunction

; ================================================================== 開印

; DLL 已經掛好新印記並做完開印的狀態部分；afMult 是開印倍率（開印效果 +3%／點 × 餘燼），
; aiCutFrom 是這一擊切掉的元素（0 = 沒有切）；abFromHit：命中開的印（火臨、雙斷這類直接開印是 False）。
Function Open(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult, Int aiCutFrom, Bool abFromHit) Global
	If !akCtl || !akTarget || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float mult = afMult
	; 電荷／岩甲／風勢的「開印 +2」round 23 起由 DLL 在開印那一擊加（SelfLayer.h OpenGains）。
	If aiElement == 1
		; 點燃：你的熱度升一階（DLL），並立即一次 B_max ×0.5 火傷
		akCtl.ApplyDamage(1, ReactDamage(akCtl, 1, 0.5) * mult, akTarget)
	ElseIf aiElement == 2
		; 霜結：凍結 +3（DLL），減速 25% 3 秒
		akCtl.ApplyUtil(0, akCtl.FrostOpenSlowPct.GetValue() * mult, 3, akTarget)
	ElseIf aiElement == 3
		; 感電：你 +2 電荷（DLL），目標魔力 -B_max ×1.0
		akCtl.ApplyUtil(2, BaseMax(akCtl, 3) * mult, 0, akTarget)
	ElseIf aiElement == 4
		; 裂痕（DLL）：目標護甲 -30（持續新手主線 +2／點）、耐力 -10，你回復 10 耐力並 +2 岩甲
		akCtl.ApplyUtil(1, ESSBElem2.FissureArmor(akCtl) * mult, 8, akTarget)
		akCtl.ApplyUtil(3, 10.0 * mult, 0, akTarget)
		akCtl.ApplyUtil(6, 10.0 * mult, 0, player)
	ElseIf aiElement == 5
		; 風痕：你風勢 +2、失衡（DLL），並把目標拉近（拉近在 ESSBElem2.OpenWind，奇襲要在同一處決定不拉近）
	ElseIf aiElement == 6
		; 血痕：流血 2 層（DLL），並依血位吸血
		akCtl.Leech(50.0 * akCtl.GetBloodLeechRatio() * mult)   ; v0.4 沒寫量也沒寫 G(L)：沿用 50、拿掉 G
	ElseIf aiElement == 7
		; 聖印（DLL；你的聖佑升一階也是 DLL），你回血 B_max ×0.5
		akCtl.ApplyUtil(4, BaseMax(akCtl, 7) * 0.5 * mult, 0, player)
	ElseIf aiElement == 8
		; 淬毒：3 劑 12 秒（DLL），並立即向 3 公尺內一名敵人傳 1 劑（掃描 N5 前在這裡）
		akCtl.SpreadPoison(akTarget, ESSBElem.RoundStochastic(mult))
	ElseIf aiElement == 10
		; 詛咒 2 層（DLL），吸魔 B_max ×1.0
		Float drain = BaseMax(akCtl, 10) * mult
		akCtl.ApplyUtil(2, drain, 0, akTarget)
		akCtl.ApplyUtil(5, drain, 0, player)
	EndIf
	; 水的浸濕與減速、星的星痕與共鳴、星鎖、星耀都在 DLL。
	ESSBElem.OnOpen(akCtl, aiElement, akTarget, mult, aiCutFrom)
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "open", akTarget.GetFormID() + " element=" + aiElement + " mult=" + mult + " cut=" + aiCutFrom)
	EndIf
EndFunction

; ================================================================== 終焉

; DLL 已經做完終焉的狀態部分，afV1..afV3 是它算好的值（見 native/include/Status.h PlanEndBody）：
;   火 afV1 熱度階、afV2 消耗加成、afV3 熾焰倍率；冰 afV1 = 1 已碎冰；雷 afV1 重擊倍率 R、afV2 暴擊擲骰、afV3 = 1 切換的重擊；
;   血 afV1 血痕剩餘傷害；聖 afV1 聖佑階。abChain：連鎖來的終焉，不再乘節點、不再往外連鎖。
; round 23：afMult 已乘協奏、三重奏、過載終焉；aiCharge 是雷終焉放電用的電荷（被切＝切換當下的快照、融斷／過期＝當下的，
; 消耗與蓄餘都在 DLL）；abAfterSwitch＝切換後首次終焉（大協奏讀它）。
Function End(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Bool abChain, \
	Float afV1, Float afV2, Float afV3, Int aiCharge = 0, Bool abAfterSwitch = False) Global
	If !akCtl || !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float mult = afMult
	Int charge = -1
	If aiElement == 3
		charge = aiCharge
	EndIf
	If !abChain
		; 規劃 2.6：關閉路線放大終焉與融斷。通用樹關閉路線 × 該元素關閉新手主線；融斷時再乘該元素「印記的融斷」兩階與雷斷。
		mult = mult * ESSBNodes.CommonEndMult(akCtl) * ESSBElem.EndMult(akCtl, aiElement)
		If aiReason == 1
			mult = mult * ESSBElem.BurstMult(akCtl, aiElement) * ESSBElem.ShockBurstBonus(akCtl, aiElement, aiReason, aiCharge)
		EndIf
	EndIf
	If akCtl.Trees
		akCtl.Trees.OnEndXP(aiElement)
	EndIf

	If aiElement == 1
		ESSBElem.Detonate(akCtl, akTarget, mult, afV1 as Int, afV2, afV3)
	ElseIf aiElement == 2
		; 碎冰（冰封時，DLL 已結算真傷並結束冰封）；未冰封 → B_max ×1.0 冰傷。
		If afV1 < 0.5
			akCtl.ApplyDamage(2, ReactDamage(akCtl, 2, 1.0) * mult * ESSBElem.SignatureMult(akCtl, 2), akTarget)
		EndIf
	ElseIf aiElement == 3
		If charge > 0
			ESSBElem.DischargeAll(akCtl, akTarget, charge, mult, False, afV1, afV2, afV3 >= 0.5)
		EndIf
	ElseIf aiElement == 4
		; 地震：裂痕不消耗（規劃 2.6 明寫「地震不消耗」）。
		; 5.6 蓄能（round 23）：重擊把滿的蓄勁換成下一次地震／碎岩 +5%／點，DLL 記在你身上（玩家碼 53），這裡用掉。
		Float charged = ESSBNative.GetStatusFloat(player, 53)
		If charged > 0.0 && !abChain
			ESSBNative.ClearStatus(player, 53)
			mult = mult * (1.0 + charged)
		EndIf
		ESSBElem2.Quake(akCtl, akTarget, mult, True)
	ElseIf aiElement == 5
		EndWind(akCtl, akTarget, mult)
	ElseIf aiElement == 6
		Surge(akCtl, akTarget, afV1, mult, aiReason, abChain)
	ElseIf aiElement == 7
		ESSBElem2.JudgeArea(akCtl, akTarget, mult, afV1 as Int)
	ElseIf aiElement == 9
		; 導引：接管元素的下一次終焉 ×1.5 已由 DLL 掛在目標身上；同調跳段 round 23 起也在 DLL。
	ElseIf aiElement == 10
		; 死咒：3 秒引信（DLL），引信期間目標無法被治療（生命回復速率 -100%，不治延長到 6 秒）。
		akCtl.ApplyUtil(20, 100.0, ESSBElem3.DeathCurseSeconds(akCtl), akTarget)
	ElseIf aiElement == 11
		ESSBElem3.Fall(akCtl, akTarget, mult, aiReason)
	EndIf
	; 毒的催毒（強度 ×2、時長＝剩餘）整個在 DLL；這裡只有它的節點（ESSBElem3.OnEnd）。
	akCtl.PlaceFx(aiElement, akTarget)
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "end", akTarget.GetFormID() + " element=" + aiElement + " reason=" + aiReason + " mult=" + mult + " chain=" + abChain)
	EndIf
	If abChain
		Return
	EndIf
	; 各元素樹的終焉分支（範圍版本、領域）。
	ESSBElem.OnEnd(akCtl, aiElement, akTarget, aiReason, mult, charge)
	; 5.2 關閉熟練分支「反哺」：每次終焉回復你 B_max 魔力。
	ESSBNodes.OnEndReward(akCtl, aiElement)
	; 5.2 關閉專精分支「連鎖終焉」：附近帶同一印記的目標也終焉 ×0.5。
	If ESSBNodes.HasChainEnd(akCtl)
		ChainEnd(akCtl, aiElement, akTarget, mult * 0.5, 5)
	EndIf
	; 5.2 關閉傳奇分支「大協奏」：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次終焉。
	If ESSBNodes.HasGrandConcert(akCtl) && abAfterSwitch
		ChainEnd(akCtl, aiElement, akTarget, mult, 5)
	EndIf
EndFunction

; 連鎖用的終焉：DLL 做狀態部分，事件標 chain，不再往外連鎖，避免遞迴。
Function ChainEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult, Int aiMax) Global
	Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, aiMax, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.HasElementMark(nearby[index], aiElement)
			ESSBNative.EndMark(nearby[index], aiElement, 2, afMult)
		EndIf
		index += 1
	EndWhile
EndFunction

; 吹飛：對目標與附近 2 人（亂流 5 人）各一段 B_max ×1.0 風刃，目標向後吹飛 3 公尺（上天分支改為吹上天）；
; 首領與大型由 ESSBController.CanRagdoll 擋下並改為減速 30% 3 秒。失衡由 DLL 在終焉時吹掉。
Function EndWind(ESSBController akCtl, Actor akTarget, Float afMult) Global
	Int count = 2
	; 5.7 關閉新手分支「亂流」：風刃附近目標 2 → 5 人。
	If ESSBNodes.Br(akCtl, 4, 2, 0, 0) ; @node 亂流
		count = 5
	EndIf
	ESSBElem2.WindBlade(akCtl, akTarget, afMult)
	ESSBElem2.BlowAway(akCtl, akTarget, afMult)
	Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, count, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			ESSBElem2.WindBlade(akCtl, nearby[index], afMult)
		EndIf
		index += 1
	EndWhile
EndFunction

; 血潮：立即結算血痕剩餘（afRemaining＝剩餘強度 × 剩餘秒數，DLL 讀好並已清掉血痕；乘血位命中倍率），
; 再加目標當前生命 10%（首領 3%）；治療你＝結算傷害 × 當前吸血比例 × 2。
Function Surge(ESSBController akCtl, Actor akTarget, Float afRemaining, Float afMult, Int aiReason, Bool abChain) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float remaining = afRemaining
	; 5.8 關閉新手分支「飽飲」：血潮結算的流血傷害 ×1.5。
	If ESSBNodes.Br(akCtl, 5, 2, 0, 0) ; @node 飽飲
		remaining = remaining * 1.5
	EndIf
	Float surge = afMult
	; 5.8 關閉大師分支「血契」：高血位（70% 以上）時損失 10% 生命，血潮 ×2。
	If ESSBNodes.Br(akCtl, 5, 2, 3, 0) && player.GetActorValuePercentage("Health") >= 0.7 ; @node 血契
		akCtl.PayBloodCost(0.10)
		surge = surge * 2.0
	EndIf
	Float percent = ESSBElem2.SurgePercent(akCtl, akCtl.IsVIPTarget(akTarget))
	; 剩餘量是 DoT 的每秒值 × 秒數，已含 G(L) 與傷害倍率；ApplyDamage 會再乘一次，所以先除回來。血位倍率照乘（v0.4 2.6）。
	Float scale = akCtl.GLevel(5) * akCtl.BaseDamageMult.GetValue()
	Float remainingPart = 0.0
	If scale > 0.0
		remainingPart = remaining * akCtl.MultDot.GetValue() * surge * akCtl.GetBloodHitMult() / scale
	EndIf
	Float amount = remainingPart + akTarget.GetActorValue("Health") * percent * surge
	amount = amount * ESSBElem.SignatureMult(akCtl, 6)
	akCtl.ApplyDamage(6, amount, akTarget)
	akCtl.Leech(amount * akCtl.GetBloodLeechRatio() * ESSBElem2.SurgeHealMult(akCtl))
	; 5.8 關閉熟練分支「血斷」：血印記融斷治療你該傷害的 50%。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 5, 2, 1, 1) ; @node 血斷
		akCtl.Leech(amount * 0.5)
	EndIf
	; 5.8 持續傳奇主線「血海」：同調三段時血潮改為範圍（掃描 N5 前在這裡）。
	Float radius = ESSBElem2.SurgeRadius(akCtl)
	If radius > 0.0 && !abChain
		Actor[] nearby = akCtl.ScanTargets(akTarget, radius, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && ESSBNative.GetStatus(nearby[index], 5) > 0
				SurgeOn(akCtl, nearby[index], afMult, True)
			EndIf
			index += 1
		EndWhile
	EndIf
EndFunction

; 對別的流血目標結算一次血潮（血海、血漫、血祭之始）：讀它的血痕剩餘、abClear 為真時清掉，再算本體。
Function SurgeOn(ESSBController akCtl, Actor akTarget, Float afMult, Bool abClear) Global
	If !akTarget || akTarget.IsDead()
		Return
	EndIf
	Float remaining = ESSBNative.DotRemaining(akTarget, False)
	If abClear
		ESSBNative.ClearStatus(akTarget, 5)
	EndIf
	Surge(akCtl, akTarget, remaining, afMult, 2, True)
EndFunction
