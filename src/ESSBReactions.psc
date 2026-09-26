Scriptname ESSBReactions Hidden
{反應：開印與終焉（規劃 v0.3 第 2.6、2.7 節）。

不做元素配對。每個元素只有兩個反應：
  開印 = 目標從沒有印記變成有印記的那一下，效果由新印記的元素決定。
  終焉 = 目標身上的印記結束的那一下（被切掉／融斷／自然過期／第 9 目標逐出），
         效果由結束的那個印記的元素決定。

公式（2.7）：D_react = B_max × K_react × G(L) × M_mod × M_ext × (1 − Res)
  B_max 取自 settings.json element_damage 的上限欄（使用者核准偏離 2.1），不隨機、不吃重擊倍率 R。
  G(L) = 1 + 0.05 × L 由 ESSBController.ApplyDamage 統一乘上（讀 ESSBTrees.TreeG），
  所以本檔算出來的都是「還沒乘 G(L)」的值，不要在這裡再乘一次。
  M_mod 由 ESSBController.GetDamageMult() 提供（環境加成、血位倍率），
  節點加成由 ESSBNodes／ESSBElem 在 Open／End 的倍率上另乘。
  M_ext 與 (1 − Res) 由引擎結算：所有傷害都走本模組自有的 ESSB_React_<元素> 法術，
  執行期 SetNthEffectMagnitude 設值後 DoCombatSpellApply，絕不直接 DamageActorValue 生命。

終焉理由 aiReason：0 被切掉、1 融斷、2 自然過期、3 第 9 目標逐出（視同過期）。
「接管元素」類效果（水的導引、星的星落）只在被切掉時成立（2.6）。

狀態種類 aiKind（與 ESSBStatus／ESSBController 共用）：
  1 熱度 2 凍結 3 裂痕 4 失衡 5 血痕 6 聖印 7 毒層 8 浸濕 9 水壓 10 詛咒 11 星痕
自身資源 aiKind（AddSelf／GetSelf）：1 電荷 2 岩甲 3 風勢 4 過熱}

; fix round 4: settings.json element_damage -> QUST VMAD float arrays.
; User-approved deviation from design 2.1; no duplicated numeric defaults.
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

; 每擊隨機 B（規劃 2.1、8）：施放前設定 magnitude，不用三檔法術。
Float Function RollBase(ESSBController akCtl, Int aiElement) Global
	Float low = BaseMin(akCtl, aiElement)
	Float high = BaseMax(akCtl, aiElement)
	If high <= low
		Return low
	EndIf
	Return Utility.RandomFloat(low, high)
EndFunction

; D_react 的本模組部分：B_max × K_react × M_mod。G(L) 由 ApplyDamage 統一乘上，
; 所以這裡不重複乘（規劃 2.7）。
Float Function ReactDamage(ESSBController akCtl, Int aiElement, Float afK) Global
	Return BaseMax(akCtl, aiElement) * afK * akCtl.GetDamageMult(aiElement)
EndFunction

; ================================================================== 開印

Function Open(ESSBController akCtl, Int aiElement, Actor akTarget) Global
	If !akCtl || !akTarget || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 星落的接管：接管元素的這次開印 ×1.5（只會在被切掉的終焉後被設定）。
	Float mult = akCtl.TakeNextOpenMultOn(akTarget)
	; 各元素開啟傳奇主線：開印效果 +3%／點（規劃 2.6「開啟路線放大該元素的開印」）。
	mult = mult * ESSBElem.OpenMult(akCtl, aiElement)

	If aiElement == 1
		; 點燃：熱度 +2（節點可加），並立即一次 B_max ×0.5 火傷
		akCtl.AddStack(akTarget, 1, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 1) * mult))
		akCtl.ApplyDamage(1, ReactDamage(akCtl, 1, 0.5) * mult, akTarget)
	ElseIf aiElement == 2
		; 霜結：凍結 +3，減速 25% 3 秒（暴風雪天氣凍結累積 ×2，見 2.10）
		Int chill = ESSBElem.OpenStacks(akCtl, 2)
		If akCtl.IsEnvStormy()
			chill = chill * 2
		EndIf
		akCtl.AddStack(akTarget, 2, ESSBElem.RoundStochastic(chill * mult))
		akCtl.ApplyUtil(0, akCtl.FrostOpenSlowPct.GetValue() * mult, 3, akTarget)
	ElseIf aiElement == 3
		; 感電：你 +2 電荷（節點可加），目標魔力 -B_max ×1.0
		akCtl.AddSelf(1, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 3) * mult))
		akCtl.ApplyUtil(2, BaseMax(akCtl, 3) * mult, 0, akTarget)
	ElseIf aiElement == 4
		; 裂痕：目標護甲 -30（持續新手主線 +2／點）、耐力 -10，你回復 10 耐力並 +2 岩甲
		akCtl.AddStack(akTarget, 3, 1)
		akCtl.ApplyUtil(1, ESSBElem2.FissureArmor(akCtl) * mult, 8, akTarget)
		akCtl.ApplyUtil(3, 10.0 * mult, 0, akTarget)
		akCtl.ApplyUtil(6, 10.0 * mult, 0, player)
		akCtl.AddSelf(2, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 4) * mult))
	ElseIf aiElement == 5
		; 風痕：你風勢 +2、施加失衡，並把目標拉近（拉近在 ESSBElem2.OpenWind，
		; 因為「奇襲」分支要在同一處決定不拉近）
		akCtl.AddSelf(3, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 5) * mult))
		akCtl.AddStack(akTarget, 4, 1)
	ElseIf aiElement == 6
		; 血痕：流血 2 層，並依血位吸血（溢出由「血盾」轉臨時護盾）
		akCtl.AddStack(akTarget, 5, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 6) * mult))
		akCtl.Leech(50.0 * akCtl.GetBloodLeechRatio() * mult)   ; v0.4 沒寫量也沒寫 G(L)：沿用 50、拿掉 G
	ElseIf aiElement == 7
		; 聖印：聖印 1 層（目標受聖傷 +20%，見 ESSBElem2.HolyVulnerability），
		; 你回血 B_max ×0.5
		akCtl.AddStack(akTarget, 6, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 7) * mult))
		akCtl.ApplyUtil(4, BaseMax(akCtl, 7) * 0.5 * mult, 0, player)
	ElseIf aiElement == 8
		; 淬毒：+3 毒層（開啟新手主線 +1／每 3 點），並立即向 3 公尺內一名敵人傳 1 層
		akCtl.AddStack(akTarget, 7, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 8) * mult))
		akCtl.SpreadPoison(akTarget, ESSBElem.RoundStochastic(mult))
	ElseIf aiElement == 9
		; 浸濕：減速 15%，浸濕 10 秒（持續新手主線 +0.3 秒／點），水印記 10 秒
		;（印記時長由控制器在套用前設定）
		akCtl.AddStack(akTarget, 8, 1)
		akCtl.ApplyUtil(0, ESSBElem3.WetSlow(akCtl) * mult, ESSBElem3.WetSeconds(akCtl), akTarget)
	ElseIf aiElement == 10
		; 詛咒：施加 2 層詛咒（開啟新手主線 +1／每 5 點），吸魔 B_max ×1.0
		akCtl.AddStack(akTarget, 10, ESSBElem.RoundStochastic(ESSBElem.OpenStacks(akCtl, 10) * mult))
		Float drain = BaseMax(akCtl, 10) * mult
		akCtl.ApplyUtil(2, drain, 0, akTarget)
		akCtl.ApplyUtil(5, drain, 0, player)
	ElseIf aiElement == 11
		; 星痕：2 秒後一次 B_max ×1.0 延遲星傷（由狀態容器的環狀桶引爆；
		; 開啟新手主線縮短延遲，傳奇分支「星耀」改為立即並 ×2）
		akCtl.AddAstral(akTarget, ESSBElem.OpenStacks(akCtl, 11), mult)
	EndIf
	; 各元素樹的開印分支（火冰雷已落地，其餘元素在之後的輪次加進 ESSBElem）。
	ESSBElem.OnOpen(akCtl, aiElement, akTarget, mult)
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "open", akTarget.GetFormID() + " element=" + aiElement + " mult=" + mult)
	EndIf
EndFunction

; ================================================================== 終焉

Function End(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Bool abChain = False) Global
	If !akCtl || !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 水的導引：接管元素的下一次終焉 ×1.5。
	Float mult = afMult * akCtl.TakeNextEndMultOn(akTarget)
	ESSBStatus st = akCtl.GetStatus(akTarget)
	Int snapshot = -1
	If aiElement == 2
		snapshot = akCtl.GetStack(akTarget, 2)
	ElseIf aiElement == 3
		snapshot = akCtl.GetSelf(1)
		If aiReason == 0
			snapshot = akCtl.TakeSwitchCharge()
		EndIf
	EndIf
	If !abChain
		; 規劃 2.6：關閉路線放大終焉與融斷。通用樹關閉路線 × 該元素關閉新手主線；
		; 融斷時再乘該元素「印記的融斷」兩階與雷斷。（round 21：v0.3 的「洩壓」分支已退役。）
		mult = mult * ESSBNodes.CommonEndMult(akCtl) * ESSBElem.EndMult(akCtl, aiElement)
		mult = mult * ESSBElem.OverloadMult(akCtl, aiElement, snapshot)
		If aiReason == 1
			mult = mult * ESSBElem.BurstMult(akCtl, aiElement) \
				* ESSBElem.ShockBurstBonus(akCtl, aiElement, aiReason)
		EndIf
		mult = mult * ESSBNodes.TrioMult(akCtl, aiElement) * ESSBNodes.ConcertMult(akCtl)
	EndIf
	; （round 21：v0.3 暗的「蝕魔終焉」在這裡兌現的吸魔已隨分支退役拿掉。）

	If aiElement == 1
		EndFire(akCtl, akTarget, st, mult, aiReason)
	ElseIf aiElement == 2
		EndFrost(akCtl, akTarget, st, mult)
	ElseIf aiElement == 3
		EndShock(akCtl, akTarget, st, mult, snapshot)
	ElseIf aiElement == 4
		EndEarth(akCtl, akTarget, st, mult)
	ElseIf aiElement == 5
		EndWind(akCtl, akTarget, st, mult)
	ElseIf aiElement == 6
		EndBlood(akCtl, akTarget, st, mult, player, aiReason, abChain)
	ElseIf aiElement == 7
		EndDivine(akCtl, akTarget, st, mult, player)
	ElseIf aiElement == 8
		EndPoison(akCtl, akTarget, st, mult, aiReason)
	ElseIf aiElement == 9
		EndWater(akCtl, akTarget, st, mult, aiReason)
	ElseIf aiElement == 10
		EndDark(akCtl, akTarget, st, mult)
	ElseIf aiElement == 11
		EndAstral(akCtl, akTarget, st, mult, aiReason)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "end", akTarget.GetFormID() + " element=" + aiElement + " reason=" + aiReason + " mult=" + mult)
	EndIf
	If abChain
		If aiElement == 3 && aiReason != 0
			akCtl.ConsumeEndCharge(snapshot)
		EndIf
		Return
	EndIf
	; 各元素樹的終焉分支（範圍版本、領域、接管加成）。
	ESSBElem.OnEnd(akCtl, aiElement, akTarget, aiReason, mult, snapshot)
	If aiElement == 3 && aiReason != 0
		akCtl.ConsumeEndCharge(snapshot)
	EndIf
	; 5.2 關閉熟練分支「反哺」：每次終焉回復你 B_max 魔力。
	ESSBNodes.OnEndReward(akCtl, aiElement)
	; 5.2 關閉專精分支「連鎖終焉」：附近帶同一印記的目標也終焉 ×0.5。
	If ESSBNodes.HasChainEnd(akCtl)
		ChainEnd(akCtl, aiElement, akTarget, mult * 0.5, 5)
	EndIf
	; 5.2 關閉傳奇分支「大協奏」：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次終焉。
	If ESSBNodes.HasGrandConcert(akCtl) && akCtl.TakeGrandConcert()
		ChainEnd(akCtl, aiElement, akTarget, mult, 5)
	EndIf
EndFunction

; 連鎖用的終焉：abChain = True，不再往外連鎖，避免遞迴。
Function ChainEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult, Int aiMax) Global
	Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, aiMax, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.HasElementMark(nearby[index], aiElement)
			akCtl.EndLinkedMark(nearby[index], aiElement, afMult)
		EndIf
		index += 1
	EndWhile
EndFunction

; 爆燃：B_max ×1.0 × (1 + 熱度 × 每層倍率) 的瞬間火傷，消耗熱度；單體。
; 每層倍率、熾焰、猛爆、火葬全在 ESSBElem.Detonate 裡（5.3 關閉路線）。
Function EndFire(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiReason = 2) Global
	ESSBElem.Detonate(akCtl, akTarget, afMult, !(aiReason == 1 && ESSBElem.KeepHeatOnBurst(akCtl)))
EndFunction

; 碎冰：冰封（凍結 ≥5）且生命低於門檻 → 處決；首領與必要角色改為 B_max ×5.0。
; 冰封但生命較高 → B_max ×2.5 並碎甲；未冰封 → ×1.0。門檻與碎甲深度見 5.4。
Function EndFrost(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult) Global
	ESSBElem.Shatter(akCtl, akTarget, afMult)
EndFunction

; 放電：電荷數 × 30% B_max（每格 +1%／點），削減目標魔力，並跳到附近數人；
; 電荷滿格時 ×2，且放電是全系統唯一吃重擊倍率的終焉。天雷在同調三段時改為範圍版本。
Function EndShock(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiCharge = -1) Global
	Int charge = aiCharge
	If charge < 0
		charge = akCtl.GetSelf(1)
	EndIf
	If charge <= 0
		Return
	EndIf
	ESSBElem.DischargeAll(akCtl, akTarget, charge, afMult, False)
EndFunction

; 地震：3 公尺範圍（廣震 5 公尺）土傷 ×1.5（崩裂 ×2.0），削減耐力 B_max ×2；
; 耐力被打到 0 的目標跌倒（PushActorAway，每目標 8 秒一次），其餘減速 30% 3 秒。
; 裂痕不消耗（規劃 2.6 明寫「地震不消耗」）。
Function EndEarth(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult) Global
	ESSBElem2.Quake(akCtl, akTarget, afMult, True)
EndFunction

; 吹飛：對目標與附近 2 人（亂流 5 人）各一段 B_max ×1.0 風刃，目標向後吹飛 3 公尺
;（上天分支改為吹上天）；首領與大型由 ESSBController.CanRagdoll 擋下並改為減速 30% 3 秒。
Function EndWind(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult) Global
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
	If akStatus
		akStatus.ClearStack(4)
	EndIf
EndFunction

; 血潮：立即結算剩餘流血總傷一次（乘血位命中倍率），再加目標當前生命 10%（首領 3%）；
; 治療你 = 結算傷害 × 當前吸血比例 × 2。
Function EndBlood(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Actor akPlayer, Int aiReason = 0, Bool abChain = False) Global
	Float remaining = 0.0
	If akStatus
		; 每層每秒 = B_max × BleedDotK × M_mod；剩餘總量以環狀桶各格剩餘秒數計。
		remaining = akStatus.BleedRemaining(ESSBElem2.BleedPerLayer(akCtl))
	EndIf
	; 5.8 關閉新手分支「飽飲」：血潮結算的流血傷害 ×1.5。
	If ESSBNodes.Br(akCtl, 5, 2, 0, 0) ; @node 飽飲
		remaining = remaining * 1.5
	EndIf
	Float surge = afMult
	; 5.8 關閉大師分支「血契」：高血位（70% 以上）時損失 10% 生命，血潮 ×2。
	If ESSBNodes.Br(akCtl, 5, 2, 3, 0) && akPlayer.GetActorValuePercentage("Health") >= 0.7 ; @node 血契
		akCtl.PayBloodCost(0.10)
		surge = surge * 2.0
	EndIf
	Float percent = ESSBElem2.SurgePercent(akCtl, akCtl.IsVIPTarget(akTarget))
	Float amount = remaining * akCtl.MultDot.GetValue() * surge + akTarget.GetActorValue("Health") * percent * surge
	amount = amount * ESSBElem.SignatureMult(akCtl, 6)
	akCtl.ApplyDamage(6, amount, akTarget)
	akCtl.Leech(amount * akCtl.GetBloodLeechRatio() * ESSBElem2.SurgeHealMult(akCtl))
	; 5.8 關閉熟練分支「血斷」：血印記融斷治療你該傷害的 50%。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 5, 2, 1, 1) ; @node 血斷
		akCtl.Leech(amount * 0.5)
	EndIf
	If akStatus
		akStatus.ClearStack(5)
	EndIf
	; 5.8 持續傳奇主線「血海」：同調三段時血潮改為範圍。
	Float radius = ESSBElem2.SurgeRadius(akCtl)
	If radius > 0.0 && !abChain
		Actor[] nearby = akCtl.ScanTargets(akTarget, radius, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.GetStack(nearby[index], 5) > 0
				End(akCtl, 6, nearby[index], 2, afMult, True)
			EndIf
			index += 1
		EndWhile
	EndIf
EndFunction

; 裁決：B_max ×2.0 聖傷（重裁 ×3.0），對亡靈魔族 ×3，治療你 B_max ×1.0。
; 天啟（同調三段）與廣裁把它變成範圍版本。
Function EndDivine(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Actor akPlayer) Global
	ESSBElem2.JudgeArea(akCtl, akTarget, afMult)
	If akStatus
		akStatus.ClearStack(6)
	EndIf
EndFunction

; 催毒：毒層不結清，8 秒內每秒跳兩次，擴散改為每秒一次（融斷同樣催毒，關閉形態後仍工作）。
; 秒數由 5.10 關閉路線的「延毒」與「毒斷」改（見 ESSBElem3.CatalyzeSeconds）。
Function EndPoison(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiReason) Global
	akCtl.SetCatalyzeOn(akTarget, ESSBElem3.CatalyzeSeconds(akCtl, aiReason), afMult)
EndFunction

; 導引：接管元素的下一次終焉 ×1.5（強引 ×2.0，傳奇主線再 +3%／點），
; 並讓你立刻 +5 同調。只在被切掉時有接管元素。
Function EndWater(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiReason) Global
	If aiReason == 0
		akCtl.SetNextEndMultOn(akTarget, ESSBElem3.GuideMult(akCtl) * afMult)
	EndIf
	akCtl.AddSync(ESSBElem3.GuideSync(akCtl))
EndFunction

; 死咒：3 秒後對目標一次暗傷 = B_max ×2.0 + 目標已損失生命的 15%（係數由關閉專精主線成長），
; 死咒期間目標無法被治療（以 HealRateMult -100% 表達，關閉熟練分支「不治」延長到 6 秒）。
Function EndDark(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult) Global
	Int seconds = ESSBElem3.DeathCurseSeconds(akCtl)
	Float amount = ReactDamage(akCtl, 10, 2.0)
	Float curseMult = afMult * ESSBElem.SignatureMult(akCtl, 10)
	akCtl.ApplyUtil(20, 100.0, seconds, akTarget)
	If akStatus
		akStatus.SetDeathCurse(3, amount, curseMult)
	Else
		akCtl.SetDeathCurseOn(akTarget, 3, amount, curseMult)
	EndIf
EndFunction

; 星落：B_max ×2.0 星傷（隕星 ×3.0、星斷改真傷 ×0.6），且接管元素的這次開印 ×1.5。
; 只在被切掉時有接管元素。
Function EndAstral(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiReason) Global
	ESSBElem3.Fall(akCtl, akTarget, afMult, aiReason)
	If akStatus
		akStatus.ClearStack(11)
	EndIf
	If aiReason == 0
		akCtl.SetNextOpenMult(akTarget, ESSBElem3.TakeoverOpenMult(akCtl))
	EndIf
EndFunction
