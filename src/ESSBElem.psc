Scriptname ESSBElem Hidden
{火（5.3）、冰（5.4）、雷（5.5）三棵元素樹的節點效果。

樹索引 0 火、1 冰、2 雷（元素編號 1／2／3）。路線 0 持續、1 開啟、2 關閉。
其餘八棵元素樹照同一組函式名稱加進來：元素 4–7（土風血聖）在 ESSBElem2、
元素 8–11（毒水暗星）在 ESSBElem3。每個元素只要提供
HitMult／OpenStacks／HitStacks／OnOpen／OnEnd／OnFormOpened／OnAvatar／OnTick／OnKill，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限）不必再改。
本檔的分派點共八處：HitMult、OpenStacks、HitStacks、OnOpen、OnFormOpened（星界的範圍成長）、
OnFormOpenedExtra、OnEnd、OnAvatar；OnTick 與 OnKill 由 ESSBController 直接分派給三個檔案。

所有傷害都走 ESSBController.ApplyDamage（自有 ESSB_React_<元素> 法術，
執行期設 magnitude 後 DoCombatSpellApply），G(L) 由 ApplyDamage 統一乘上。}

; ================================================================== 狀態上限（規劃 2.3）

; 火 熱度：基礎 10（滿即自燃）；添薪分支 15；通用樹傳奇主線「萬象」欄再 +1／每 5 點。
Int Function HeatCap(ESSBController akCtl) Global
	Int cap = 10
	If ESSBNodes.Br(akCtl, 0, 0, 0, 0)
		cap = 15
	EndIf
	Return cap + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 火 過熱（你）：基礎 10；熔爐分支 20。
Int Function OverheatCap(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 0, 0, 4, 1)
		Return 20
	EndIf
	Return 10
EndFunction

; 雷 電荷（你）：基礎 6；持續專精主線 +1／每 3 點（蓄電）；萬象再 +1／每 5 點。
Int Function ChargeCap(ESSBController akCtl) Global
	Return 6 + ESSBNodes.Rank(akCtl, 2, 0, 2) / 3 + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 冰 凍結量表固定 5（量表不吃萬象，規劃 2.3）。
Int Function FreezeCap() Global
	Return 5
EndFunction

; ================================================================== 附傷倍率（M_mod 的元素樹部分）

Float Function HitExtra(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 1
		Return FireHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 2
		Return FrostHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 3
		Return ShockHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement >= 4 && aiElement <= 7
		Return ESSBElem2.HitExtra(akCtl, aiElement, akTarget, abPower)
	ElseIf aiElement >= 8 && aiElement <= 11
		Return ESSBElem3.HitExtra(akCtl, aiElement, akTarget, abPower)
	EndIf
	Return 0.0
EndFunction

; 差額補丁的乘法項裡屬於元素的部分（暗的虛空 ×1.5）；其餘元素 1。
Float Function HitExtraMult(ESSBController akCtl, Int aiElement, Actor akTarget) Global
	If aiElement == 10
		Return ESSBElem3.DarkHitExtraMult(akCtl, akTarget)
	EndIf
	Return 1.0
EndFunction

; 5.3：熱度每層 +（8% + 0.2%／點）、開印後 5 秒內 +1%／點、過熱中 +50%（熔爐 +80%）、熔身 +100%、火域內目標 +20%。
; （火附傷 +1%／點與同調每段 +1%／點由 DLL 算。）
Float Function FireHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = 0.0
	Int heat = akCtl.GetStack(akTarget, 1)
	If heat > 0
		Float perLayer = 0.08 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 0, 0, 0), 0.002)
		extra = extra + heat * perLayer * ESSBNodes.OmniMult(akCtl)
	EndIf
	If akCtl.GetOpenBoost(1) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 0, 1, 1), 0.01)
	EndIf
	If akCtl.GetSelf(4) > 0
		; 規劃 1.1：過熱期間火附傷 +50%；熔爐分支改為 +80%。
		If ESSBNodes.Br(akCtl, 0, 0, 4, 1)
			extra = extra + 0.8
		Else
			extra = extra + 0.5
		EndIf
	EndIf
	If akCtl.GetMoltenLeft() > 0
		extra = extra + 1.0
	EndIf
	If akCtl.InDomain(akTarget, 1)
		extra = extra + 0.2
	EndIf
	Return extra
EndFunction

; 5.4：冰封目標 +2%／點、開印後 5 秒內 +1%／點（冰附傷與同調每段由 DLL 算）。
Float Function FrostHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = 0.0
	If akCtl.GetStack(akTarget, 2) >= 5
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 1, 0, 2), 0.02)
	EndIf
	If akCtl.GetOpenBoost(2) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 1, 1, 1), 0.01)
	EndIf
	Return extra
EndFunction

; 5.5：開印後 5 秒內 +1%／點、電蝕分支（目標魔力為 0 時 +25%）（雷附傷與同調每段由 DLL 算）。
Float Function ShockHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = 0.0
	If akCtl.GetOpenBoost(3) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 2, 1, 1), 0.01)
	EndIf
	If ESSBNodes.Br(akCtl, 2, 1, 3, 2) && akTarget.GetActorValue("Magicka") <= 0.0
		extra = extra + 0.25
	EndIf
	Return extra
EndFunction

; ================================================================== 開印與終焉倍率

; 各元素「開啟傳奇主線：開印效果 +3%／點」。
Float Function OpenMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 1, 4), 0.03)
EndFunction

; 各元素「關閉新手主線：終焉 +2%／點」。傳奇主線（爆燃／碎冰／放電 +3%／點）
; 只作用在該元素自己的終焉效果上，由各自的 End 函式另乘。
Float Function EndMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 0), 0.02)
EndFunction

; 各元素「關閉熟練／大師主線：該元素印記的融斷 +2%／點」（兩階各一次）。
Float Function BurstMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 1), 0.02) + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 3), 0.02)
EndFunction

; 傳奇主線的「該元素終焉招式本身」倍率：火 爆燃、冰 碎冰、雷 放電，各 +3%／點。
Float Function SignatureMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 4), 0.03)
EndFunction

; ================================================================== 開印時的額外層數

; 火 開印熱度 +2（引火分支 +5），開啟新手主線再 +1／每 5 點。
; 冰 開印凍結 +3，開啟新手主線 +1／每 3 點。
; 雷 開印電荷 +2，開啟新手主線 +1／每 5 點。
Int Function OpenStacks(ESSBController akCtl, Int aiElement) Global
	If aiElement == 1
		Int heat = 2
		If ESSBNodes.Br(akCtl, 0, 1, 0, 0)
			heat = 5
		EndIf
		Return heat + ESSBNodes.Rank(akCtl, 0, 1, 0) / 5
	ElseIf aiElement == 2
		Return 3 + ESSBNodes.Rank(akCtl, 1, 1, 0) / 3
	ElseIf aiElement == 3
		Return 2 + ESSBNodes.Rank(akCtl, 2, 1, 0) / 5
	ElseIf aiElement >= 4 && aiElement <= 7
		Return ESSBElem2.OpenStacks(akCtl, aiElement)
	ElseIf aiElement >= 8 && aiElement <= 11
		Return ESSBElem3.OpenStacks(akCtl, aiElement)
	EndIf
	Return 0
EndFunction

; 命中時的層數（規劃 2.3 的「命中」欄）加上節點修正。
Int Function HitStacks(ESSBController akCtl, Int aiElement, Bool abPower) Global
	If aiElement == 1
		Int heat = 1
		If abPower
			heat = 2
			; 5.3 持續熟練分支「烙印」：重擊熱度 +2 → +4。
			If ESSBNodes.Br(akCtl, 0, 0, 1, 0)
				heat = 4
			EndIf
		EndIf
		Return heat
	ElseIf aiElement == 2
		Int chill = 1
		If abPower
			chill = 2
			; 5.4 持續新手分支「寒蝕」：重擊凍結 +2。
			If ESSBNodes.Br(akCtl, 1, 0, 0, 0)
				chill = 4
			EndIf
		EndIf
		; 5.4 持續新手主線：每次命中凍結累積 +5%／點。量表是整數，以機率補足小數。
		Float scaled = chill * (1.0 + 0.05 * ESSBNodes.Rank(akCtl, 1, 0, 0))
		If akCtl.PlayerInDomain(2)
			scaled = scaled * 2.0
		EndIf
		Return RoundStochastic(scaled)
	ElseIf aiElement == 3
		Return 1
	ElseIf aiElement >= 4 && aiElement <= 7
		Return ESSBElem2.HitStacks(akCtl, aiElement, abPower)
	ElseIf aiElement >= 8 && aiElement <= 11
		Return ESSBElem3.HitStacks(akCtl, aiElement, abPower)
	EndIf
	Return 1
EndFunction

; 把小數層數變成整數：整數部分保證給，小數部分以機率決定。避免「+5%／點」永遠被截掉。
Int Function RoundStochastic(Float afValue) Global
	Int whole = afValue as Int
	Float remainder = afValue - whole
	If remainder > 0.0 && Utility.RandomFloat(0.0, 1.0) < remainder
		whole += 1
	EndIf
	Return whole
EndFunction

; 各元素印記持續的額外秒數（開啟專精主線 +0.2 秒／點）。
Int Function MarkDurationBonus(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Float extra = 0.2 * ESSBNodes.Rank(akCtl, tree, 1, 2)
	Return (extra + 0.5) as Int
EndFunction

; ================================================================== 開印（分支）

Function OnOpen(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult = 1.0) Global
	If aiElement == 1
		OpenFire(akCtl, akTarget)
	ElseIf aiElement == 2
		OpenFrost(akCtl, akTarget)
	ElseIf aiElement == 3
		OpenShock(akCtl, akTarget)
	ElseIf aiElement >= 4 && aiElement <= 7
		ESSBElem2.OnOpen(akCtl, aiElement, akTarget, afMult)
	ElseIf aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnOpen(akCtl, aiElement, akTarget, afMult)
	EndIf
	akCtl.SetOpenBoost(aiElement, 5)
EndFunction

Function OpenFire(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.3 開啟大師分支「烈火之始」：開印若目標生命高於 80%，熱度直接 8。
	If ESSBNodes.Br(akCtl, 0, 1, 3, 0) && akTarget.GetActorValuePercentage("Health") > 0.8
		akCtl.SetStack(akTarget, 1, 8)
	EndIf
	; 5.3 開啟熟練分支「餘熱」：開印時回復 15 耐力。
	If ESSBNodes.Br(akCtl, 0, 1, 1, 1) && player
		akCtl.ApplyUtil(6, 50.0 * akCtl.GLevel(0), 0, player)
	EndIf
	; 5.3 開啟專精分支「焰起強化」：焰起額外對範圍內敵人造成一次火附傷。
	If ESSBNodes.Br(akCtl, 0, 1, 2, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
		Float amount = ESSBReactions.BaseMax(akCtl, 1) * 0.5 * akCtl.GetDamageMult(1)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.ApplyDamage(1, amount, nearby[index])
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.3 開啟傳奇分支「先燃」：同調三段時開印立即一次 ×0.5 爆燃。
	If ESSBNodes.Br(akCtl, 0, 1, 4, 0) && akCtl.SyncStage() >= 3
		Detonate(akCtl, akTarget, 0.5, False)
	EndIf
EndFunction

Function OpenFrost(ESSBController akCtl, Actor akTarget) Global
	; 5.4 開啟新手分支「寒潮」：開印時附近 1 人凍結 +2。
	If ESSBNodes.Br(akCtl, 1, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 2, 2)
		EndIf
	EndIf
	; 5.4 開啟熟練分支「冰甲」：開印時獲得 1 層冰盾。
	If ESSBNodes.Br(akCtl, 1, 1, 1, 1)
		akCtl.AddIceShield(1)
	EndIf
	; 5.4 開啟大師分支「霜鎖」：開印目標 3 秒內移速 -30%。
	If ESSBNodes.Br(akCtl, 1, 1, 3, 0)
		akCtl.ApplyUtil(0, 30.0, 3, akTarget)
	EndIf
	; 5.4 開啟大師分支「冰晶」：開印時你受傷 -10% 3 秒（PERK 進入點讀 ESSB_GuardIce）。
	If ESSBNodes.Br(akCtl, 1, 1, 3, 1)
		akCtl.SetGuardIce(3)
	EndIf
	; 5.4 開啟傳奇分支「絕霜」：同調三段時開印直接冰封。
	If ESSBNodes.Br(akCtl, 1, 1, 4, 0) && akCtl.SyncStage() >= 3
		akCtl.SetStack(akTarget, 2, FreezeCap())
	EndIf
EndFunction

Function OpenShock(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.5 開啟新手分支「傳導」：開印時附近 1 人也感電。
	If ESSBNodes.Br(akCtl, 2, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.ApplyMark(nearby[0], 3)
		EndIf
	EndIf
	; 5.5 開啟熟練分支「充能開印」：開印時回復 B_max 魔力。
	If ESSBNodes.Br(akCtl, 2, 1, 1, 1) && player
		akCtl.ApplyUtil(5, 60.0 * akCtl.GLevel(2), 0, player)
	EndIf
	; 5.5 開啟大師分支「感電削弱」：感電目標魔抗 -10%。
	If ESSBNodes.Br(akCtl, 2, 1, 3, 0)
		akCtl.ApplyUtil(16, 10.0, 8, akTarget)
	EndIf
	; 5.5 開啟大師分支「雷閃」：開印後 2 秒移速 +15%。
	If ESSBNodes.Br(akCtl, 2, 1, 3, 1) && player
		akCtl.ApplyUtil(9, 15.0, 2, player)
	EndIf
	; 5.5 開啟傳奇分支「先雷」：同調三段時開印立即放電一次，不消耗電荷。
	If ESSBNodes.Br(akCtl, 2, 1, 4, 0) && akCtl.SyncStage() >= 3
		Discharge(akCtl, akTarget, akCtl.GetSelf(1), False, 1.0)
	EndIf
EndFunction

; 5.3／5.4／5.5 開啟熟練分支「烈火點燃／深霜結／強感電」：開印那一擊附傷 ×1.5。
Float Function OpenStrikeMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	If ESSBNodes.Br(akCtl, tree, 1, 1, 0)
		Return 1.5
	EndIf
	Return 1.0
EndFunction

; ================================================================== 開形態：火臨／冰臨／雷臨

; 各元素開啟大師主線：開形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點。
Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Int rank = ESSBNodes.Rank(akCtl, tree, 1, 3)
	If rank <= 0
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float radius = (2.0 + 0.2 * rank) * 70.0
	If aiElement == 11
		; 規劃 2.9 例外表：星界的所有範圍主線每點 +1 公尺（夜晚再 ×1.5）。
		radius = ESSBElem3.AdventRadius(akCtl)
	EndIf
	Actor[] nearby = akCtl.ScanTargets(player, radius, 5, player)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			akCtl.ForceOpenOn(nearby[index], aiElement)
			; 5.4 開啟專精分支「冰臨強化」：冰臨附帶減速 30% 3 秒。
			If aiElement == 2 && ESSBNodes.Br(akCtl, 1, 1, 2, 0)
				akCtl.ApplyUtil(0, 30.0, 3, nearby[index])
			EndIf
		EndIf
		index += 1
	EndWhile
	; 5.5 開啟專精分支「雷臨強化」：雷臨時立即獲得 5 電荷。
	If aiElement == 3 && ESSBNodes.Br(akCtl, 2, 1, 2, 0)
		akCtl.AddSelf(1, 5)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "advent element=" + aiElement + " radius=" + radius)
	EndIf
EndFunction

; 土風血聖的「臨」附加效果（地臨強化、氣旋、血臨強化、聖臨強化）。
; 與 OnFormOpened 分開，是因為這幾個分支即使沒投主線（沒有「臨」）也要生效。
Function OnFormOpenedExtra(ESSBController akCtl, Int aiElement) Global
	If aiElement >= 4 && aiElement <= 7
		ESSBElem2.OnFormOpened(akCtl, aiElement)
	ElseIf aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnFormOpened(akCtl, aiElement)
	EndIf
EndFunction

; ================================================================== 火：自燃與爆燃

; 自燃倍率（5.3 持續傳奇主線）：獨立基礎 ×2。業火主線在同調三段時 +0.1／點。
Float Function IgniteMult(ESSBController akCtl, Int aiHeat) Global
	Float mult = 2.0
	If akCtl.SyncStage() >= 3
		mult = mult + 0.1 * ESSBNodes.Rank(akCtl, 0, 0, 4)
	EndIf
	Return mult
EndFunction

; 5.3 關閉專精主線：爆燃每層熱度倍率 +0.01／點（0.2 → 0.35）。
Float Function DetonatePerLayer(ESSBController akCtl) Global
	Float per = 0.2 + 0.01 * ESSBNodes.Rank(akCtl, 0, 2, 2)
	Return per * ESSBNodes.OmniMult(akCtl)
EndFunction

; 自燃：熱度到上限時由 ESSBStatus 呼叫。
Function OnIgnite(ESSBController akCtl, Actor akTarget, Int aiHeat) Global
	Float amount = ESSBReactions.BaseMax(akCtl, 1) * IgniteMult(akCtl, aiHeat) * akCtl.GetDamageMult(1)
	akCtl.ApplyDamage(1, amount, akTarget)
	; 5.3 持續大師分支「火浴」：自燃時你回血 B_max ×2。
	If ESSBNodes.Br(akCtl, 0, 0, 3, 1)
		Actor player = akCtl.ThePlayer()
		If player
			akCtl.ApplyUtil(4, 60.0 * akCtl.GLevel(0), 0, player)
		EndIf
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "ignite", akTarget.GetFormID() + " heat=" + aiHeat + " amount=" + amount)
	EndIf
EndFunction

; 自燃後的殘留熱度（熔心分支保留一半）。
Int Function IgniteResidual(ESSBController akCtl, Int aiHeat) Global
	If ESSBNodes.Br(akCtl, 0, 0, 2, 0)
		Return aiHeat / 2
	EndIf
	Return 0
EndFunction

; 爆燃（火終焉）：B_max ×1.0 ×（1 + 熱度 × 每層倍率）。
; abConsume 為真時消耗熱度（猛爆分支不消耗；熔斷分支讓融斷保留）。
Function Detonate(ESSBController akCtl, Actor akTarget, Float afMult, Bool abConsume) Global
	Int heat = akCtl.GetStack(akTarget, 1)
	Float mult = 1.0 + heat * DetonatePerLayer(akCtl)
	; 5.3 關閉熟練分支「熾焰」：爆燃結算時若熱度 ≥8 則 ×1.5。
	If heat >= 8 && ESSBNodes.Br(akCtl, 0, 2, 1, 0)
		mult = mult * 1.5
	EndIf
	Float amount = ESSBReactions.BaseMax(akCtl, 1) * afMult * mult * akCtl.GetDamageMult(1) * SignatureMult(akCtl, 1)
	akCtl.ApplyDamage(1, amount, akTarget, 1)
	If abConsume && !ESSBNodes.Br(akCtl, 0, 2, 0, 0)
		akCtl.SetStack(akTarget, 1, 0)
	EndIf
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "detonate " + akTarget.GetFormID() + " heat=" + heat + " amount=" + amount)
	EndIf
EndFunction

; ================================================================== 冰：碎冰

; 5.4 關閉新手分支「銳碎」：處決門檻 20% → 30%。
Float Function ShatterThreshold(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 1, 2, 0, 0)
		Return 0.3
	EndIf
	Return 0.2
EndFunction

; 碎冰本體。abFrozenOnly 為真時只對冰封目標生效（冰崩／冰河的範圍版本）。
Function Shatter(ESSBController akCtl, Actor akTarget, Float afMult) Global
	If !akCtl || !akTarget
		Return
	EndIf
	Int freeze = akCtl.GetStack(akTarget, 2)
	Bool executed = False
	akCtl.SetStack(akTarget, 2, 0)
	Float signature = SignatureMult(akCtl, 2)
	If freeze >= 5
		If akTarget.GetActorValuePercentage("Health") < ShatterThreshold(akCtl)
			If akCtl.IsVIPTarget(akTarget)
				akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 5.0) * afMult * signature, akTarget)
			Else
				executed = True
				akCtl.Execute(akTarget, 2)
			EndIf
		Else
			akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 2.5) * afMult * signature, akTarget)
			; 碎甲 10%；5.4 關閉大師分支「碎甲加深」改為 20%。
			Float shred = 0.1
			If ESSBNodes.Br(akCtl, 1, 2, 3, 1)
				shred = 0.2
			EndIf
			akCtl.ApplyUtil(1, akTarget.GetActorValue("DamageResist") * shred, 5, akTarget)
		EndIf
	Else
		akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 1.0) * afMult * signature, akTarget)
	EndIf
	; Original freeze is consumed first. Ice coffin is a fresh, explicit two-second state.
	If !executed && akTarget && !akTarget.IsDead() && ESSBNodes.Br(akCtl, 1, 2, 4, 0)
		akCtl.SetFrozen(akTarget, 2.0)
	EndIf
EndFunction

; 冰封解除時的殘留（5.4 持續專精分支「永凍」：冰封 +2 秒、結束後凍結保留一半）。
Int Function FrozenExtraSeconds(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 1, 0, 2, 0)
		Return 2
	EndIf
	Return 0
EndFunction

Int Function FrozenResidual(ESSBController akCtl, Int aiFreeze) Global
	If ESSBNodes.Br(akCtl, 1, 0, 2, 0)
		Return aiFreeze / 2
	EndIf
	Return 0
EndFunction

; 冰封期間的效果：減速與「深寒」。每秒由 ESSBStatus 呼叫一次。
Function OnFrozenTick(ESSBController akCtl, Actor akTarget) Global
	Float slow = 50.0
	; 5.4 持續傳奇主線「絕對零度」：同調三段時冰封減速再 -2%／點，可影響首領。
	If akCtl.SyncStage() >= 3
		slow = slow + 2.0 * ESSBNodes.Rank(akCtl, 1, 0, 4)
	EndIf
	If slow > 90.0
		slow = 90.0
	EndIf
	akCtl.ApplyUtil(0, slow, 2, akTarget)
	; 5.4 持續熟練分支「深寒」：冰封中目標耐力不回復，攻擊 -20%。
	If ESSBNodes.Br(akCtl, 1, 0, 1, 0)
		akCtl.ApplyUtil(17, 20.0, 2, akTarget)
		akCtl.ApplyUtil(3, 25.0 * akCtl.GLevel(1), 0, akTarget)
	EndIf
EndFunction

; ================================================================== 雷：放電

; 放電：以電荷數 × 30% B_max 對目標放電，削減魔力 = 傷害的 50%（電蝕分支 100%），
; 並跳到附近 2 人（連鎖分支 5 人）各 40%（電弧分支 80%）。
; 電荷滿格時 ×2，且放電是全系統唯一吃重擊倍率的終焉（規劃 2.6）。
Function Discharge(ESSBController akCtl, Actor akTarget, Int aiCharge, Bool abConsume, Float afMult) Global
	If aiCharge <= 0 || !akTarget
		Return
	EndIf
	Float perCharge = 0.3 * (1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 2, 0, 0), 0.01))
	Float amount = ESSBReactions.ReactDamage(akCtl, 3, perCharge * aiCharge) * afMult * SignatureMult(akCtl, 3)
	If aiCharge >= ChargeCap(akCtl)
		amount = amount * 2.0
	EndIf
	If akCtl.LastHitWasPower()
		amount = amount * 1.5
	EndIf
	Float drainRatio = 0.5
	If ESSBNodes.Br(akCtl, 2, 1, 3, 2)
		drainRatio = 1.0
	EndIf
	akCtl.ApplyDamage(3, amount, akTarget)
	akCtl.ApplyUtil(2, amount * drainRatio * akCtl.GLevel(2), 0, akTarget)

	Int jumpCount = 2
	If ESSBNodes.Br(akCtl, 2, 2, 0, 0)
		jumpCount = 5
	EndIf
	Float jumpRatio = 0.4
	If ESSBNodes.Br(akCtl, 2, 0, 1, 0)
		jumpRatio = 0.8
	EndIf
	Actor[] jump = akCtl.ScanTargets(akTarget, 1050.0, jumpCount, akTarget)
	Int index = 0
	While index < jump.Length
		If jump[index]
			akCtl.ApplyDamage(3, amount * jumpRatio, jump[index])
			akCtl.ApplyUtil(2, amount * jumpRatio * drainRatio * akCtl.GLevel(2), 0, jump[index])
		EndIf
		index += 1
	EndWhile

	If abConsume && !ESSBNodes.Br(akCtl, 2, 2, 1, 0)
		akCtl.ClearSelf(1)
	EndIf
	; 5.5 持續大師分支「疾電」：放電後 3 秒受傷 -15%（PERK 進入點讀 ESSB_ShockRecent）。
	If ESSBNodes.Br(akCtl, 2, 0, 3, 1)
		akCtl.SetShockRecent(3)
	EndIf
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "discharge " + akTarget.GetFormID() + " charge=" + aiCharge + " amount=" + amount)
	EndIf
EndFunction

; 5.5 持續傳奇主線「天雷」：同調三段時放電改為對範圍內所有感電目標。
Function DischargeAll(ESSBController akCtl, Actor akTarget, Int aiCharge, Float afMult, Bool abConsume = True) Global
	Int rank = ESSBNodes.Rank(akCtl, 2, 0, 4)
	If rank <= 0 || akCtl.SyncStage() < 3
		Discharge(akCtl, akTarget, aiCharge, abConsume, afMult)
		Return
	EndIf
	Float radius = (2.0 + 0.2 * rank) * 70.0
	Actor player = akCtl.ThePlayer()
	Discharge(akCtl, akTarget, aiCharge, False, afMult)
	If player
		Actor[] nearby = akCtl.ScanTargets(player, radius, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.HasElementMark(nearby[index], 3)
				Discharge(akCtl, nearby[index], aiCharge, False, afMult)
			EndIf
			index += 1
		EndWhile
	EndIf
	If abConsume && !ESSBNodes.Br(akCtl, 2, 2, 1, 0)
		akCtl.ClearSelf(1)
	EndIf
EndFunction

; ================================================================== 終焉掛勾

; 由 ESSBReactions.End 在各元素的終焉函式之後呼叫（分支的範圍與追加效果）。
Function OnEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Int aiSnapshot = -1) Global
	If aiElement == 1
		EndFireNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 2
		EndFrostNodes(akCtl, akTarget, aiReason, afMult, aiSnapshot)
	ElseIf aiElement == 3
		EndShockNodes(akCtl, akTarget, aiReason, afMult, aiSnapshot)
	ElseIf aiElement >= 4 && aiElement <= 7
		ESSBElem2.OnEnd(akCtl, aiElement, akTarget, aiReason, afMult)
	ElseIf aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnEnd(akCtl, aiElement, akTarget, aiReason, afMult)
	EndIf
	; 各元素關閉專精主線：終焉後 5 秒內接管元素附傷 +1%／點（冰、雷、聖有這一階）。
	Int tree = ESSBNodes.TreeOf(aiElement)
	Int rank = ESSBNodes.Rank(akCtl, tree, 2, 2)
	If rank > 0
		; Only these five trees describe this damage bonus; preserve other existing paths.
		Float bonus = 0.01 * rank
		If aiElement == 2 || aiElement == 3 || aiElement == 7 || aiElement == 8 || aiElement == 9
			bonus = ESSBNodes.Pct(akCtl, rank, 0.01)
		EndIf
		akCtl.SetEndBoost(aiElement, 5, bonus)
	EndIf
EndFunction

Function EndFireNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.3 關閉專精分支「餘燼」：火終焉後接管元素的開印 ×1.5（只在被切掉時有接管元素）。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 0, 2, 2, 0)
		akCtl.SetNextOpenMult(akTarget, 1.5)
	EndIf
	; 5.3 關閉大師分支「焚天」：火終焉觸發時範圍內所有帶熱度目標一起爆燃。
	If ESSBNodes.Br(akCtl, 0, 2, 3, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.GetStack(nearby[index], 1) > 0
				Detonate(akCtl, nearby[index], afMult, True)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.3 關閉傳奇分支「火域」：火印記融斷後留下 5 秒火域。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 0, 2, 4, 0)
		akCtl.StartDomain(1, akTarget, 5)
	EndIf
EndFunction

Function EndFrostNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult, Int aiFreeze = -1) Global
	If aiFreeze < 0
		aiFreeze = akCtl.GetStack(akTarget, 2)
	EndIf
	; 5.4 關閉熟練分支「冰崩」：碎冰改為 3 公尺範圍，命中所有冰封目標。
	If ESSBNodes.Br(akCtl, 1, 2, 1, 0)
		ShatterArea(akCtl, akTarget, afMult)
	ElseIf ESSBNodes.Br(akCtl, 1, 2, 3, 0) && aiFreeze >= 5
		; 5.4 關閉大師分支「冰河」：冰終焉時目標若冰封，範圍內所有冰封目標一起碎冰。
		ShatterArea(akCtl, akTarget, afMult)
	EndIf
	; 5.4 關閉專精分支「寒留」：冰終焉後接管元素的印記持續 +4 秒。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 1, 2, 2, 0)
		akCtl.SetNextMarkBonus(4)
	EndIf
	; 5.4 關閉傳奇分支「冰原」：冰印記融斷後留下 5 秒冰原。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 1, 2, 4, 1)
		akCtl.StartDomain(2, akTarget, 5)
	EndIf
EndFunction

Function ShatterArea(ESSBController akCtl, Actor akTarget, Float afMult) Global
	Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 5, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.GetStack(nearby[index], 2) >= 5
			Shatter(akCtl, nearby[index], afMult)
		EndIf
		index += 1
	EndWhile
EndFunction

Function EndShockNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult, Int aiCharge = -1) Global
	; 5.5 關閉專精分支「餘電」：雷終焉後接管元素的開印附帶一次 ×0.5 放電。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 2, 2, 2, 0)
		akCtl.SetPendingDischarge(aiCharge)
	EndIf
	; 5.5 關閉大師分支「雷殛」：雷終焉對範圍內所有感電目標各一次全額放電。
	If ESSBNodes.Br(akCtl, 2, 2, 3, 0)
		Int charge = aiCharge
		If charge < 0
			charge = akCtl.GetSelf(1)
		EndIf
		If charge > 0
			Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
			Int index = 0
			While index < nearby.Length
				If nearby[index] && akCtl.HasElementMark(nearby[index], 3)
					Discharge(akCtl, nearby[index], charge, False, afMult)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
	; 5.5 關閉傳奇分支「雷霆」：雷印記融斷後 5 秒內你每次命中都放電 ×0.3。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 2, 2, 4, 0)
		akCtl.SetThunder(5)
	EndIf
EndFunction

; 5.5 關閉大師分支「過載終焉」：終焉時電荷 ≥8 則傷害 ×2。
Float Function OverloadMult(ESSBController akCtl, Int aiElement, Int aiCharge = -1) Global
	If aiCharge < 0
		aiCharge = akCtl.GetSelf(1)
	EndIf
	If aiElement == 3 && ESSBNodes.Br(akCtl, 2, 2, 3, 1) && aiCharge >= 8
		Return 2.0
	EndIf
	Return 1.0
EndFunction

; 5.5 關閉熟練分支「雷斷」：雷印記融斷時附加你全部電荷的放電加成。
Float Function ShockBurstBonus(ESSBController akCtl, Int aiElement, Int aiReason) Global
	If aiElement == 3 && aiReason == 1 && ESSBNodes.Br(akCtl, 2, 2, 1, 1)
		Return 1.0 + 0.3 * akCtl.GetSelf(1)
	EndIf
	Return 1.0
EndFunction

; 5.3 關閉新手分支「洩壓」：融斷時把過熱轉為額外爆燃傷害，每點過熱 +10%。
Float Function VentMult(ESSBController akCtl, Int aiElement, Int aiReason) Global
	If aiElement != 1 || aiReason != 1 || !ESSBNodes.Br(akCtl, 0, 2, 0, 1)
		Return 1.0
	EndIf
	Int overheat = akCtl.GetSelf(4)
	; 熔身中融斷仍可洩壓，以熔身剩餘秒數 ×2 計為過熱點數（5.3 持續專精分支「熔身」）。
	If akCtl.GetMoltenLeft() > 0
		overheat = akCtl.GetMoltenLeft() * 2
	EndIf
	Return 1.0 + 0.1 * overheat
EndFunction

; 5.3 關閉熟練分支「熔斷」：融斷後目標熱度保留。
Bool Function KeepHeatOnBurst(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 0, 2, 1, 1)
EndFunction

; 5.4 關閉熟練分支「冰封融斷」：冰印記融斷時目標若冰封，視同碎冰，含處決判定。
Bool Function FrostBurstShatter(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 1, 2, 1, 1)
EndFunction

; ================================================================== 每秒與擊殺掛勾

Function OnTick(ESSBController akCtl, Int aiElement) Global
	If aiElement == 2
		; 5.4 持續傳奇分支「冰心」：生命低於 30% 時自動冰封附近所有帶寒意的敵人，每 30 秒一次。
		If ESSBNodes.Br(akCtl, 1, 0, 4, 0)
			Actor player = akCtl.ThePlayer()
			If player && player.GetActorValuePercentage("Health") < 0.3 && akCtl.TakeIceHeart()
				Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
				Int index = 0
				While index < nearby.Length
					If nearby[index] && akCtl.GetStack(nearby[index], 2) > 0
						akCtl.SetStack(nearby[index], 2, FreezeCap())
					EndIf
					index += 1
				EndWhile
				If akCtl.CachedDebugLevel >= 1
					akCtl.LogThrottled(1, "node", "frost iceheart")
				EndIf
			EndIf
		EndIf
	ElseIf aiElement == 3
		; 5.5 持續傳奇分支「雷神」：同調三段時電荷滿層自動放電並回復魔力。
		If ESSBNodes.Br(akCtl, 2, 0, 4, 0) && akCtl.SyncStage() >= 3
			Int charge = akCtl.GetSelf(1)
			If charge >= ChargeCap(akCtl)
				Actor victim = akCtl.NearestMarked(3)
				If victim
					DischargeAll(akCtl, victim, charge, 1.0)
					Actor player = akCtl.ThePlayer()
					If player
						akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3) * charge * akCtl.GLevel(2), 0, player)
					EndIf
				EndIf
			EndIf
		EndIf
	EndIf
EndFunction

; 化身（通用樹持續傳奇主線）：自動觸發當前元素的持續傳奇效果。
Function OnAvatar(ESSBController akCtl, Int aiElement) Global
	If aiElement == 1
		; 業火：對最近的帶熱度目標立即自燃一次。
		Actor victim = akCtl.NearestMarked(1)
		If victim
			Int heat = akCtl.GetStack(victim, 1)
			If heat > 0
				OnIgnite(akCtl, victim, heat)
				akCtl.SetStack(victim, 1, IgniteResidual(akCtl, heat))
			EndIf
		EndIf
	ElseIf aiElement == 2
		; 絕對零度：對最近的帶冰印記目標直接冰封並上強減速。
		Actor victim = akCtl.NearestMarked(2)
		If victim
			akCtl.SetStack(victim, 2, FreezeCap())
			OnFrozenTick(akCtl, victim)
		EndIf
	ElseIf aiElement == 3
		; 天雷：對最近的感電目標做一次範圍放電。
		Actor victim = akCtl.NearestMarked(3)
		If victim
			DischargeAll(akCtl, victim, akCtl.GetSelf(1), 1.0)
		EndIf
	ElseIf aiElement >= 4 && aiElement <= 7
		ESSBElem2.OnAvatar(akCtl, aiElement)
	ElseIf aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnAvatar(akCtl, aiElement)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "avatar element=" + aiElement)
	EndIf
EndFunction

Function OnKill(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiFreeze) Global
	; 5.4 持續專精分支「連鎖冰封」：冰封目標死亡時附近敵人凍結 +3 並減速 30% 3 秒。
	If aiFreeze >= 5 && ESSBNodes.Br(akCtl, 1, 0, 2, 1)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.AddStackTo(nearby[index], 2, 3)
				akCtl.ApplyUtil(0, 30.0, 3, nearby[index])
			EndIf
			index += 1
		EndWhile
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "frost chainfreeze " + akTarget.GetFormID())
		EndIf
	EndIf
EndFunction

; 5.5 持續專精分支「雷暴」：電荷滿時普攻也有 30% 機率放電。
Bool Function StormChance(ESSBController akCtl) Global
	If !ESSBNodes.Br(akCtl, 2, 0, 2, 0)
		Return False
	EndIf
	If akCtl.GetSelf(1) < ChargeCap(akCtl)
		Return False
	EndIf
	Return Utility.RandomFloat(0.0, 1.0) < 0.3
EndFunction

; 5.3 持續專精分支「熔身」：過熱滿了不再對自己爆，改為 10 秒熔身。
Bool Function HasMoltenBody(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 0, 0, 2, 1)
EndFunction

; 5.3 大師分支「火種」：熱度不因未命中歸零。
Bool Function HasTinder(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 0, 1, 3, 1)
EndFunction

; 5.3 持續專精主線：帶熱度目標火抗 -1%／點。
Function ApplyFireResistShred(ESSBController akCtl, Actor akTarget) Global
	Int rank = ESSBNodes.Rank(akCtl, 0, 0, 2)
	If rank <= 0 || akCtl.GetStack(akTarget, 1) <= 0
		Return
	EndIf
	akCtl.ApplyUtil(13, rank as Float, 6, akTarget)
EndFunction

Function OnCremation(ESSBController akCtl, Actor akTarget, Float afAmount) Global
	; 5.3 關閉大師分支「火葬」：爆燃擊殺的目標對附近敵人再爆一次 ×0.5。
	If ESSBNodes.Br(akCtl, 0, 2, 3, 1)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.ApplyDamage(1, afAmount * 0.5, nearby[index])
			EndIf
			index += 1
		EndWhile
	EndIf
EndFunction
