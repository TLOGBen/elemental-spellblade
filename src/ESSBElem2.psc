Scriptname ESSBElem2 Hidden
{大地（5.6）、風（5.7）、鮮血（5.8）、神聖（5.9）四棵元素樹的節點效果。

Round 22（N3）起，裂痕、倒地、失衡、血痕、聖印、聖佑與聖裁計數是 DLL 掛的引擎效果（native/include/Status.h）；
這裡只剩開印與終焉的本體與範圍掃描（N5 前），狀態只經 ESSBNative 讀寫。

樹索引 3 土、4 風、5 血、6 聖（元素編號 4／5／6／7）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

物理推力（跌倒、拉近、吹飛、吹上天）一律走 ESSBController 的
Knockdown／PullIn／BlowBack／LiftUp，四者都在控制器裡做每目標冷卻與免疫名單，
本檔只決定「要不要推、推多遠」。浮空是 DLL 掛的 2 秒自有效果，不讀物理狀態，
到期時 DLL 送落地事件（ESSBController.OnLanding）結算落地傷害（規劃 8 的空中追擊實作備註）。

所有傷害都走 ESSBController.ApplyDamage，G(L) 由 ApplyDamage 統一乘上。}

; ================================================================== 狀態上限（規劃 2.3）

; 土 岩甲（你）：基礎 5；厚土分支 10；萬象再 +1／每 5 點。
Int Function RockCap(ESSBController akCtl) Global
	Int cap = 5
	If ESSBNodes.Br(akCtl, 3, 0, 1, 1) ; @node 厚土
		cap = 10
	EndIf
	Return cap + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 土 岩甲每層護甲（v0.4 5.6）：+25，磐石分支 +40（v0.4 沒有 G(L)）。
Float Function RockArmorPerLayer(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 0, 0, 0) ; @node 磐石
		Return 40.0
	EndIf
	Return 25.0
EndFunction

; 風 風勢門檻：4，亂舞分支 3（量表，不吃萬象）。
Int Function WindThreshold(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 4, 0, 1, 0) ; @node 亂舞
		Return 3
	EndIf
	Return 4
EndFunction







; 聖印（神聖印記本身）讓目標受聖傷 +20%（規劃 2.6 的基礎開印）＋聖痕的 +10%（非亡靈）。裁決吃同一個函式；
; 附傷的同一項由 DLL 讀（Status.h ProcTerms）。
Float Function HolyVulnerability(ESSBController akCtl, Actor akTarget) Global
	If !akCtl.HasElementMark(akTarget, 7)
		Return 0.0
	EndIf
	Float bonus = 0.2
	If ESSBNodes.Br(akCtl, 6, 1, 3, 0) && !akCtl.IsUndeadOrDaedra(akTarget) ; @node 聖痕
		bonus = bonus + 0.1
	EndIf
	Return bonus
EndFunction

; 聖佑各階的聖傷加成（v0.4 5.9：I +10%、II +20%、III +35%；持續新手主線 +1%／點 × 階數）：裁決與聖裁都吃。
Float Function HolyTierBonus(ESSBController akCtl, Int aiTier) Global
	Float bonus = 0.0
	If aiTier >= 3
		bonus = 0.35
	ElseIf aiTier == 2
		bonus = 0.2
	ElseIf aiTier == 1
		bonus = 0.1
	EndIf
	Return bonus + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 6, 0, 0), 0.01) * aiTier ; @node 聖佑各階武器傷害與聖傷加成
EndFunction

; 開印的岩甲（+2，岩膚 +4，開啟新手主線 +1／每 5 點）與風勢（+2，疾風痕直接滿）round 23 起在 DLL（SelfLayer.h）。


; ================================================================== 每次命中（元素專屬）

; 血的命中吸血（依血位占附傷）round 20 起由 DLL 與附傷同一刀結清，這裡沒有血的每擊工作。
Function OnHit(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 4
		OnEarthHit(akCtl, akTarget, abPower)
	ElseIf aiElement == 5
		OnWindHit(akCtl, akTarget, abPower)
	ElseIf aiElement == 7
		OnDivineHit(akCtl, akTarget, abPower)
	EndIf
EndFunction

Function OnEarthHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 5.6 持續專精主線（命中削減目標耐力）與分支「汲力」round 20 起由 DLL 在命中當下施放。
	If !abPower
		Return
	EndIf
	; 5.6 持續熟練分支「震擊」：重擊消耗裂痕標記，1.5× 地震爆傷並削減耐力。
	If ESSBNodes.Br(akCtl, 3, 0, 1, 0) && ESSBNative.GetStatus(akTarget, 3) > 0 ; @node 震擊
		akCtl.ApplyDamage(4, ESSBReactions.ReactDamage(akCtl, 4, 1.5), akTarget)
		akCtl.ApplyUtil(3, 50.0, 0, akTarget)
		ESSBNative.ClearStatus(akTarget, 3)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "node", "earth quakestrike " + akTarget.GetFormID())
		EndIf
	EndIf
	; 5.6 持續傳奇主線「地動」（同調三段重擊、目標耐力 <30%、5%／點跌倒）round 23 起由 DLL 擲，推力經 ESSB_Knock 回來。
EndFunction

Function OnWindHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 5.7 持續熟練分支「順風」（命中回復耐力）round 20 起由 DLL 在命中當下施放；持續傳奇主線「千刃」與關閉大師分支
	; 「順勢」round 23 起由 DLL 判定，風刃經 ESSB_Blade 回來。
EndFunction

; v0.4 的神聖以聖佑三階與聖裁為核心：聖佑升階、II／III 命中回血、聖裁計數與聖裁本身（含聖裁傷害、神罰）都在 DLL；
; 聖盾（聖佑各階的法術減傷）是聖佑階上的引擎效果。這裡只剩護持。
Function OnDivineHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 5.9 持續新手分支「護持」：命中獲得 10% 魔抗 3 秒。
	If ESSBNodes.Br(akCtl, 6, 0, 0, 0) ; @node 護持
		akCtl.ApplyUtil(8, 10.0, 3, player)
	EndIf
EndFunction

; 同伴治療（聖臨強化、聖光）。ScanTargets 會排除同伴，所以另走 ScanAllies。
Function HealAllies(ESSBController akCtl, Float afAmount) Global
	Actor[] allies = akCtl.ScanAllies(420.0)
	Int index = 0
	While index < allies.Length
		If allies[index]
			akCtl.ApplyUtil(4, afAmount, 0, allies[index])
		EndIf
		index += 1
	EndWhile
EndFunction

; ================================================================== 開印

Function OnOpen(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult = 1.0) Global
	If aiElement == 4
		OpenEarth(akCtl, akTarget)
	ElseIf aiElement == 5
		OpenWind(akCtl, akTarget, afMult)
	ElseIf aiElement == 6
		OpenBlood(akCtl, akTarget)
	ElseIf aiElement == 7
		OpenDivine(akCtl, akTarget)
	EndIf
EndFunction

Function OpenEarth(ESSBController akCtl, Actor akTarget) Global
	; 5.6 開啟新手分支「震波」：開印時附近 1 人也裂痕（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 3, 1, 0, 0) ; @node 震波
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 3, 1)
			akCtl.ApplyUtil(1, FissureArmor(akCtl), 8, nearby[0])
		EndIf
	EndIf
	; 5.6 開啟熟練分支「深裂痕」：開印時目標耐力低於 50% 則立即跌倒（倒地標記 DLL 在開印當下已掛，這裡是推力）。
	If ESSBNodes.Br(akCtl, 3, 1, 1, 0) && akTarget.GetActorValuePercentage("Stamina") < 0.5 ; @node 深裂痕
		akCtl.Knockdown(akTarget, 3.0)
	EndIf
	; 5.6 開啟大師分支「地基」：開印目標 3 秒內耐力不回復（自有效果把耐力回復設 0）。
	If ESSBNodes.Br(akCtl, 3, 1, 3, 0) ; @node 地基
		akCtl.ApplyUtil(21, 100.0, 3, akTarget)
	EndIf
	; 「裂地」（開印目標 8 秒內被土弄倒，倒地 3 → 5 秒）由 DLL 在掛倒地時讀裂痕。
	; 5.6 開啟傳奇分支「先震」：同調三段時開印立即一次 ×0.5 地震，不含跌倒。
	If ESSBNodes.Br(akCtl, 3, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 先震
		Quake(akCtl, akTarget, 0.5, False)
	EndIf
EndFunction

Function OpenWind(ESSBController akCtl, Actor akTarget, Float afMult = 1.0) Global
	Actor player = akCtl.ThePlayer()
	; 5.7 開啟專精分支「奇襲」：潛行攻擊的開印同時觸發終焉，且不拉近。
	Bool ambush = ESSBNodes.Br(akCtl, 4, 1, 2, 1) && akCtl.LastHitWasSneak() ; @node 奇襲
	If !ambush
		; 規劃 2.6 基礎開印「風痕」：把目標拉近你 1.5 公尺；開啟熟練主線 +0.1 公尺／點。
		akCtl.PullIn(akTarget, PullDistance(akCtl) * afMult)
		; 5.7 開啟大師分支「牽引」：目標身後 1.5 公尺內的其他敵人也一起被拉近並失衡（最多 2 人，各自 3 秒推力冷卻；
		; 掃描 N5 前在這裡）。「身後」＝比目標離你更遠。
		If ESSBNodes.Br(akCtl, 4, 1, 3, 0) && player ; @node 牽引
			Float behind = player.GetDistance(akTarget)
			Actor[] dragged = akCtl.ScanTargets(akTarget, 105.0, 5, akTarget)
			Int pulled = 0
			Int index = 0
			While index < dragged.Length && pulled < 2
				If dragged[index] && player.GetDistance(dragged[index]) > behind
					akCtl.PullIn(dragged[index], PullDistance(akCtl) * afMult)
					akCtl.AddStackTo(dragged[index], 4, 1)
					pulled += 1
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
	; 5.7 開啟新手分支「風襲」：開印時附近 1 人也風痕（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 4, 1, 0, 0) ; @node 風襲
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 4, 1)
			akCtl.ApplyMark(nearby[0], 5)
		EndIf
	EndIf
	; 5.7 開啟熟練分支「輕躍」：開印後 3 秒移速 +10%。
	If ESSBNodes.Br(akCtl, 4, 1, 1, 1) && player ; @node 輕躍
		akCtl.ApplyUtil(9, 10.0, 3, player)
	EndIf
	; 5.7 開啟大師分支「氣流」：開印時回復 10 耐力。
	If ESSBNodes.Br(akCtl, 4, 1, 3, 1) && player ; @node 氣流
		akCtl.ApplyUtil(6, 10.0, 0, player)
	EndIf
	; 5.7 開啟傳奇分支「先風」（同調三段時開印附帶一段風刃）round 23 起由 DLL 在開印那一擊送出（ESSB_Blade）。
	If ambush
		; 一刀開印兼吹飛：立即結算一次風終焉的本體（不再往外連鎖），失衡照吹飛的規則吹掉。
		ESSBNative.ClearStatus(akTarget, 4)
		ESSBReactions.EndWind(akCtl, akTarget, 1.0)
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "wind ambush " + akTarget.GetFormID())
		EndIf
	EndIf
EndFunction

Function OpenBlood(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.8 開啟新手分支「血濺」：開印時附近 1 人流血 1 層（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 5, 1, 0, 0) ; @node 血濺
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 5, 1)
		EndIf
	EndIf
	; 5.8 開啟熟練分支「開印回血」：開印時你回血 B_max ×0.5，低血位 ×2。
	If ESSBNodes.Br(akCtl, 5, 1, 1, 1) && player ; @node 開印回血
		Float heal = ESSBReactions.BaseMax(akCtl, 6) * 0.5
		If player.GetActorValuePercentage("Health") < 0.3
			heal = heal * 2.0
		EndIf
		akCtl.ApplyUtil(4, heal, 0, player)
	EndIf
	; 5.8 開啟大師分支「血咒」：開印目標 5 秒內生命回復速率 -50%。
	If ESSBNodes.Br(akCtl, 5, 1, 3, 0) ; @node 血咒
		akCtl.ApplyUtil(20, 50.0, 5, akTarget)
	EndIf
	; 5.8 開啟大師分支「血脈」（開印 +2 同調）round 23 起在 DLL。
	; 5.8 開啟熟練分支「深血痕」的吸血那一半（層數在 DLL）：中血區吸血一次、低血區吸血兩次。
	If ESSBNodes.Br(akCtl, 5, 1, 1, 0) && player ; @node 深血痕
		Float health = player.GetActorValuePercentage("Health")
		Int leeches = 0
		If health < 0.3
			leeches = 2
		ElseIf health <= 0.7
			leeches = 1
		EndIf
		While leeches > 0
			akCtl.Leech(50.0 * akCtl.GetBloodLeechRatio())
			leeches -= 1
		EndWhile
	EndIf
	; 血引（血終焉後接管元素的開印附帶流血 2 層）在 DLL 的同一擊裡做。
	; 5.8 開啟傳奇分支「血祭之始」：同調三段時開印立即結算一次 ×0.5 血潮。
	If ESSBNodes.Br(akCtl, 5, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 血祭之始
		ESSBReactions.SurgeOn(akCtl, akTarget, 0.5, True)
	EndIf
EndFunction

Function OpenDivine(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.9 開啟新手主線：開印回血 +5%／點（以 B_max 為基準，疊在聖印基礎的 ×0.5 上：×0.5 → ×1.25）。
	Int rank = ESSBNodes.Rank(akCtl, 6, 1, 0) ; @node 開印回血
	If rank > 0 && player
		akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7) * 0.05 * rank, 0, player)
	EndIf
	; 5.9 開啟新手分支「聖輝」：開印時附近 1 人也聖印（聖印就是神聖印記；掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 6, 1, 0, 0) ; @node 聖輝
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.ApplyMark(nearby[0], 7)
		EndIf
	EndIf
	; 5.9 開啟大師分支「聖光」：開印時附近同伴回血 B_max。
	If ESSBNodes.Br(akCtl, 6, 1, 3, 1) ; @node 聖光
		HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))
	EndIf
	; 聖引（聖終焉後接管元素的開印治療你 B_max）與聖啟（聖佑直接 II）在 DLL。
EndFunction

; 5.6 持續新手主線：裂痕護甲削減 -30 → -60（+2／點；v0.4 沒有 G(L)）。
Float Function FissureArmor(ESSBController akCtl) Global
	Return 30.0 + 2.0 * ESSBNodes.Rank(akCtl, 3, 0, 0) ; @node 裂痕護甲削減
EndFunction

; 5.7 開啟熟練主線：開印拉近距離 1.5 公尺 +0.1 公尺／點，上限 3 公尺。
Float Function PullDistance(ESSBController akCtl) Global
	Float metres = 1.5 + 0.1 * ESSBNodes.Rank(akCtl, 4, 1, 1) ; @node 開印拉近距離
	If metres > 3.0
		metres = 3.0
	EndIf
	Return metres
EndFunction

; ================================================================== 開形態（各元素的「臨」的附加效果）

Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	If aiElement == 4
		; 5.6 開啟專精分支「地臨強化」：地臨時岩甲滿層（開場就能碎岩；round 23 起由 DLL 在開形態時補滿），範圍內敵人
		; 耐力 -50%（最大耐力的一半；範圍掃描 N5 前由這裡做）。
		If ESSBNodes.Br(akCtl, 3, 1, 2, 0) ; @node 地臨強化
			Actor[] nearby = akCtl.ScanTargets(player, ESSBElem.AdventRadiusOf(akCtl, 4), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.ApplyUtil(3, nearby[index].GetActorValueMax("Stamina") * 0.5, 0, nearby[index], True)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 5
		; 5.7 開啟專精分支「氣旋」：風臨時把範圍內敵人拉到你面前 2 公尺。
		If ESSBNodes.Br(akCtl, 4, 1, 2, 0) ; @node 氣旋
			Actor[] nearby = akCtl.ScanTargets(player, ESSBElem.AdventRadiusOf(akCtl, 5), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.PullIn(nearby[index], 2.0)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 6
		; 5.8 開啟專精分支「血臨強化」：血臨時你付最大生命 15%（代價路徑，留 1 點），並立即觸發一次濺血（不受越線冷卻；
		; 濺血的掃描 N5 前在 ESSBController.Splash）。v0.3 的「血臨後 10 秒不扣血」已拿掉。
		If ESSBNodes.Br(akCtl, 5, 1, 2, 0) ; @node 血臨強化
			akCtl.PayBloodCost(0.15)
			akCtl.Splash()
		EndIf
	ElseIf aiElement == 7
		; 5.9 開啟專精分支「聖臨強化」：聖臨時你與附近同伴回血 B_max ×2（聖 B_max 10 → 20；v0.4 這一格沒有 G(L)）。
		If ESSBNodes.Br(akCtl, 6, 1, 2, 0) ; @node 聖臨強化
			Float heal = ESSBReactions.BaseMax(akCtl, 7) * 2.0
			akCtl.ApplyUtil(4, heal, 0, player)
			HealAllies(akCtl, heal)
		EndIf
	EndIf
EndFunction

; ================================================================== 土：地震

; 5.6 關閉新手分支「崩裂」：地震 ×1.5 → ×2.0。
Float Function QuakeK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 2, 0, 0) ; @node 崩裂
		Return 2.0
	EndIf
	Return 1.5
EndFunction

; 5.6 關閉熟練分支「廣震」：地震範圍 3 → 5 公尺（1 公尺 = 70 單位）。
Float Function QuakeRadius(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 2, 1, 0) ; @node 廣震
		Return 350.0
	EndIf
	Return 210.0
EndFunction

; 5.6 關閉專精主線：地震耐力削減 +3%／點（基礎 B_max ×2.0）。
Float Function QuakeStamina(ESSBController akCtl) Global
	Return 2.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2)) * akCtl.GLevel(3) ; @node 地震耐力削減
EndFunction

; 地震本體（規劃 2.6）：範圍土傷 + 削耐；耐力被打到 0 的目標跌倒，其餘減速 30% 3 秒。
Function Quake(ESSBController akCtl, Actor akTarget, Float afMult, Bool abKnock) Global
	Float amount = ESSBReactions.ReactDamage(akCtl, 4, QuakeK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 4)
	Float stamina = ESSBReactions.ReactDamage(akCtl, 4, QuakeStamina(akCtl)) * afMult
	Bool dust = ESSBNodes.Br(akCtl, 3, 2, 3, 1) ; @node 塵暴
	QuakeOne(akCtl, akTarget, amount, stamina, abKnock, dust)
	Actor[] nearby = akCtl.ScanTargets(akTarget, QuakeRadius(akCtl), 5, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			QuakeOne(akCtl, nearby[index], amount, stamina, abKnock, dust)
		EndIf
		index += 1
	EndWhile
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "quake", akTarget.GetFormID() + " amount=" + amount + " stamina=" + stamina)
	EndIf
EndFunction

Function QuakeOne(ESSBController akCtl, Actor akTarget, Float afAmount, Float afStamina, \
	Bool abKnock, Bool abDust) Global
	akCtl.ApplyDamage(4, afAmount, akTarget)
	Bool floored = akTarget.GetActorValue("Stamina") <= akCtl.DrainAmount(afStamina)
	akCtl.ApplyUtil(3, afStamina, 0, akTarget)
	If abKnock && floored
		; 規劃 2.6：耐力被打到 0 的目標跌倒（ragdoll，每目標 8 秒一次），免疫者改為減速。
		If !akCtl.Knockdown(akTarget, 3.0)
			akCtl.ApplyUtil(0, 30.0, 3, akTarget)
		EndIf
	Else
		akCtl.ApplyUtil(0, 30.0, 3, akTarget)
	EndIf
	; 5.6 關閉大師分支「塵暴」：地震使範圍內敵人攻擊 -20% 3 秒。
	If abDust
		akCtl.ApplyUtil(17, 20.0, 3, akTarget)
	EndIf
EndFunction

; 5.6 持續大師分支「反震」round 23 起由 DLL 在受擊時結算（土傷、清空岩甲、10 秒冷卻；推力經 ESSB_Knock 回來）。

; ================================================================== 風：風刃、吹飛、吹上天

; 5.7 持續新手主線：風刃傷害 +2%／點。暗風（潛行送出的風刃 ×2）round 23 起由 DLL 乘在 ESSB_Blade 的倍率上；
; Papyrus 自己送的潛行風刃（致命潛行的奇襲）在 LethalAmbush 另乘。
Float Function WindBladeMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 4, 0, 0), 0.02) ; @node 風刃傷害
EndFunction

; 風刃：單體一段 B_max ×1.0；迴旋分支改為對附近 2 人各一段。
; 失衡目標受風刃傷害 +30%（規劃 2.3）。
Function WindBlade(ESSBController akCtl, Actor akTarget, Float afMult) Global
	If !akTarget
		Return
	EndIf
	Float amount = ESSBReactions.ReactDamage(akCtl, 5, 1.0) * afMult * WindBladeMult(akCtl)
	WindBladeOne(akCtl, akTarget, amount)
	If ESSBNodes.Br(akCtl, 4, 0, 0, 0) ; @node 迴旋
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 2, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				WindBladeOne(akCtl, nearby[index], amount)
			EndIf
			index += 1
		EndWhile
	EndIf
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "wind blade " + akTarget.GetFormID() + " amount=" + amount)
	EndIf
EndFunction

Function WindBladeOne(ESSBController akCtl, Actor akTarget, Float afAmount) Global
	Float amount = afAmount
	If ESSBNative.GetStatus(akTarget, 4) > 0
		amount = amount * 1.3
	EndIf
	akCtl.ApplyDamage(5, amount, akTarget)
	Actor player = akCtl.ThePlayer()
	; 5.7 持續專精分支「追風」：風刃命中回復耐力 3，並讓目標失衡。
	If ESSBNodes.Br(akCtl, 4, 0, 2, 0) ; @node 追風
		If player
			akCtl.ApplyUtil(6, 3.0, 0, player)
		EndIf
		akCtl.AddStackTo(akTarget, 4, 1)
	EndIf
	; 5.7 關閉傳奇分支「空中追擊」：風刃命中空中目標再推高 1 公尺並延長滯空。
	If ESSBNodes.Br(akCtl, 4, 2, 4, 0) && akCtl.GetAirborne(akTarget) > 0 ; @node 空中追擊
		akCtl.LiftUp(akTarget, 1.0, LandingDamage(akCtl))
	EndIf
EndFunction

; 風勢到門檻送出風刃並歸零（規劃 2.3）round 23 起由 DLL 判定（ESSB_Blade）。

; 吹飛距離：v0.4 固定 3 公尺（5.7 定位）。關閉專精主線 v0.4 是「多段觸發」（DLL N4），
; v0.3 的「吹飛距離 +0.2 公尺／點」已拿掉。
Float Function BlowDistance(ESSBController akCtl) Global
	Return 3.0
EndFunction

; 5.7 關閉傳奇主線：落地傷害 B_max ×0.5 +5%／點（點滿 ×1.25）。
Float Function LandingDamage(ESSBController akCtl) Global
	Float k = 0.5 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 4, 2, 4), 0.05) ; @node 落地傷害
	; 5.7 關閉熟練分支「上天」把基礎落地傷害提到 B_max ×1.0。
	If ESSBNodes.Br(akCtl, 4, 2, 1, 0) ; @node 上天
		k = k + 0.5
	EndIf
	Return ESSBReactions.ReactDamage(akCtl, 5, k)
EndFunction

; 吹飛／吹上天：有「上天」分支就改為向上推並掛浮空，否則向後吹飛。
; 免疫者（首領、龍、騎乘、巨人猛獁）由控制器改為減速 30% 3 秒。
Function BlowAway(ESSBController akCtl, Actor akTarget, Float afMult) Global
	If !akTarget
		Return
	EndIf
	Bool lifted = ESSBNodes.Br(akCtl, 4, 2, 1, 0) ; @node 上天
	Bool pushed = False
	If lifted
		pushed = akCtl.LiftUp(akTarget, 1.0, LandingDamage(akCtl))
	Else
		pushed = akCtl.BlowBack(akTarget, BlowDistance(akCtl))
	EndIf
	If !pushed
		akCtl.ApplyUtil(0, 30.0, 3, akTarget)
	EndIf
EndFunction

; ================================================================== 血：血潮




; 5.8 關閉專精主線：血潮治療倍率 ×2，每點 +0.1。
Float Function SurgeHealMult(ESSBController akCtl) Global
	Return 2.0 + 0.1 * ESSBNodes.Rank(akCtl, 5, 2, 2) ; @node 血潮治療倍率 ×2
EndFunction

; 5.8 關閉大師分支「放血終焉」：血潮的當前生命項 10% → 20%（首領 3% → 6%）。
Float Function SurgePercent(ESSBController akCtl, Bool abVIP) Global
	Float percent = 0.10
	If abVIP
		percent = 0.03
	EndIf
	If ESSBNodes.Br(akCtl, 5, 2, 3, 1) ; @node 放血終焉
		percent = percent * 2.0
	EndIf
	Return percent
EndFunction

; ================================================================== 聖：裁決

; 5.9 關閉新手分支「重裁」：裁決 ×2.0 → ×3.0。
Float Function JudgeK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 6, 2, 0, 0) ; @node 重裁
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 裁決本體（規劃 2.6）：B_max ×2.0 聖傷（乘聖佑階的聖傷加成），對亡靈魔族 ×3，治療你 B_max ×1.0。
Function Judge(ESSBController akCtl, Actor akTarget, Float afMult, Int aiHolyTier) Global
	Actor player = akCtl.ThePlayer()
	Float amount = ESSBReactions.ReactDamage(akCtl, 7, JudgeK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 7) * (1.0 + HolyVulnerability(akCtl, akTarget)) * (1.0 + HolyTierBonus(akCtl, aiHolyTier))
	If IsHolyPrey(akCtl, akTarget)
		amount = amount * 3.0
	EndIf
	akCtl.ApplyDamage(7, amount, akTarget)
	If player
		akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)
	EndIf

	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "divine judge " + akTarget.GetFormID() + " amount=" + amount)
	EndIf
EndFunction

; 亡靈魔族判定；5.9 開啟大師分支「聖痕」讓帶聖印記的目標也吃同一份判定。
Bool Function IsHolyPrey(ESSBController akCtl, Actor akTarget) Global
	If akCtl.IsUndeadOrDaedra(akTarget)
		Return True
	EndIf
	Return ESSBNodes.Br(akCtl, 6, 1, 3, 0) && akCtl.HasElementMark(akTarget, 7) ; @node 聖痕
EndFunction

; ================================================================== 終焉掛勾

Function OnEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult) Global
	If aiElement == 4
		EndEarthNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 5
		EndWindNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 6
		EndBloodNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 7
		EndDivineNodes(akCtl, akTarget, aiReason, afMult)
	EndIf
EndFunction

Function EndEarthNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.6 關閉熟練分支「固土」（土終焉後岩甲滿層）round 23 起由 DLL 在終焉時補滿。
	; 5.6 關閉大師分支「山崩」：土終焉對範圍內所有帶裂痕的目標各一次地震。
	If ESSBNodes.Br(akCtl, 3, 2, 3, 0) ; @node 山崩
		Actor[] nearby = akCtl.ScanTargets(akTarget, QuakeRadius(akCtl), 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && ESSBNative.GetStatus(nearby[index], 3) > 0
				Quake(akCtl, nearby[index], afMult, False)
			EndIf
			index += 1
		EndWhile
	EndIf
	If aiReason != 1
		Return
	EndIf
	; 5.6 關閉傳奇分支「地裂」：土印記融斷後留下 5 秒地裂帶（內部效果在 ESSBController.TickDomain）。
	; v0.4 的「地斷」是融斷時範圍內耐力低於 30% 的目標直接跌倒（DLL N5），v0.3 的「3 秒泥沼」已拿掉。
	If ESSBNodes.Br(akCtl, 3, 2, 4, 0) ; @node 地裂
		akCtl.StartDomain(4, akTarget, 5)
	EndIf
EndFunction

Function EndWindNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.7 關閉專精分支「風渦」：終焉時 5 公尺內敵人被拉向目標聚攏。
	If ESSBNodes.Br(akCtl, 4, 2, 2, 0) ; @node 風渦
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.PullTo(nearby[index], akTarget, 2.0)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.7 關閉大師分支「順勢」（風被切後 5 秒內接管元素的命中各附一段風刃）round 23 起由 DLL 記在你身上。
	If aiReason != 1
		Return
	EndIf
	; 5.7 關閉熟練分支「風斷」：風印記融斷時每個目標各兩段風刃。
	If ESSBNodes.Br(akCtl, 4, 2, 1, 1) ; @node 風斷
		WindBlade(akCtl, akTarget, 1.0)
		WindBlade(akCtl, akTarget, 1.0)
	EndIf
	; 5.7 關閉大師分支「颶風」：融斷的吹上天改為對範圍內所有敵人，不限帶風印記。
	If ESSBNodes.Br(akCtl, 4, 2, 3, 0) ; @node 颶風
		Actor player = akCtl.ThePlayer()
		If player
			Actor[] nearby = akCtl.ScanTargets(player, ESSBNoForm.BurstRadius(akCtl), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					BlowAway(akCtl, nearby[index], afMult)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
EndFunction

Function EndBloodNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.8 關閉熟練分支「血漫」：血潮結算時附近流血目標一起血潮（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 5, 2, 1, 0) ; @node 血漫
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && ESSBNative.GetStatus(nearby[index], 5) > 0
				ESSBReactions.SurgeOn(akCtl, nearby[index], afMult, True)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 血約（往上越線時 15 公尺內流血目標血痕 +2）是越線的回湧那一邊（N4）加範圍掃描（N5）。血引在 DLL。
	; 5.8 關閉傳奇分支「血池」：血印記融斷後留下 5 秒血池。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 5, 2, 4, 0) ; @node 血池
		akCtl.StartDomain(6, akTarget, 5)
	EndIf
EndFunction

; v0.4 的「光耀」（裁決後亡靈魔族受聖傷 +20%，DLL N5）與「天誅」（懲戒，N4／N5）要等後續切片；
; v0.3 的「光耀減速」與已退役的「處決」已拿掉。
Function EndDivineNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 聖引（接管元素的開印治療你 B_max）在 DLL 的同一擊裡做。
	; 5.9 關閉熟練分支「聖斷」：聖印記融斷每個目標治療你 B_max ×1.0。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 6, 2, 1, 1) && player ; @node 聖斷
		akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)
	EndIf
	; 5.9 關閉專精分支「聖域」：聖終焉後留下聖域 5 秒；傳奇分支「神聖領域」：聖印記融斷後留下 8 秒聖域
	;（「聖佑 III 時融斷不清空聖佑」在 DLL 的離開形態）。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 6, 2, 4, 0) ; @node 神聖領域
		akCtl.StartDomain(7, akTarget, 8)
	ElseIf ESSBNodes.Br(akCtl, 6, 2, 2, 0) ; @node 聖域
		akCtl.StartDomain(7, akTarget, 5)
	EndIf
EndFunction

; ================================================================== 擊殺


; 5.9 持續傳奇主線「天啟」：同調三段時裁決改為範圍，1 公尺 +0.2 公尺／點（掃描 N5 前在這裡）。
; 懲戒（v0.4 2.3）：這一次裁決每層 +20%，然後清空（範圍裁決的每個目標吃同一份；聖裁那一份在 DLL）。
Function JudgeArea(ESSBController akCtl, Actor akTarget, Float afMult, Int aiHolyTier) Global
	Actor player = akCtl.ThePlayer()
	Int punish = 0
	If player
		punish = ESSBNative.GetStatus(player, 23)
		If punish > 0
			ESSBNative.ClearStatus(player, 23)
		EndIf
	EndIf
	afMult = afMult * (1.0 + 0.2 * punish)
	Judge(akCtl, akTarget, afMult, aiHolyTier)
	Int rank = ESSBNodes.Rank(akCtl, 6, 0, 4) ; @node 天啟
	Bool wide = ESSBNodes.Br(akCtl, 6, 2, 1, 0) ; @node 廣裁
	If rank <= 0 && !wide
		Return
	EndIf
	Float radius = 210.0
	If rank > 0 && akCtl.SyncStage() >= 3
		radius = (1.0 + 0.2 * rank) * 70.0
		If radius < 210.0 && wide
			radius = 210.0
		EndIf
	ElseIf !wide
		Return
	EndIf
	Actor[] nearby = akCtl.ScanTargets(akTarget, radius, 5, akTarget)
	; v0.4：每一次裁決各治療你 B_max ×1.0（round 7 的「單次累計上限」不在 v0.4，拿掉）。
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			Judge(akCtl, nearby[index], afMult, aiHolyTier)
		EndIf
		index += 1
	EndWhile
EndFunction

; 5.8 持續傳奇主線「血海」：同調三段時血潮改為範圍，1 公尺 +0.2 公尺／點。
Float Function SurgeRadius(ESSBController akCtl) Global
	Int rank = ESSBNodes.Rank(akCtl, 5, 0, 4) ; @node 血海
	If rank <= 0 || akCtl.SyncStage() < 3
		Return 0.0
	EndIf
	Return (1.0 + 0.2 * rank) * 70.0
EndFunction

; 擊殺掛勾：由 ESSBGuard 的 OnActorKilled 轉進來（akVictim 已死）。
Function OnKill(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiBleed, Int aiKillingElement = 0, Bool abAsh = False) Global
	Actor player = akCtl.ThePlayer()
	If !player || !akTarget
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "ash-reject", "reason=invalid-player-or-target")
		EndIf
		Return
	EndIf
	If aiBleed > 0
		; 5.8 持續熟練分支「飲血」：擊殺流血目標回血 20%，並獲得 10 秒嗜血（命中效果 +20%，差額補丁讀）。
		; 「吸血 +10%」要等嗜血改成你身上的效果、DLL 讀得到（N5）。
		If ESSBNodes.Br(akCtl, 5, 0, 1, 0) ; @node 飲血
			akCtl.ApplyUtil(4, player.GetActorValueMax("Health") * 0.2, 0, player)
			akCtl.SetBloodthirst(10)
		EndIf
		; 5.8 持續專精分支「血承」：吸收死者屬性 15 秒，只保留最近一個。
		If ESSBNodes.Br(akCtl, 5, 0, 2, 1) ; @node 血承
			akCtl.ApplyInherit(akTarget)
		EndIf
		; v0.4 的「不死」（回滿耐力並回血到越過上方的線、觸發回湧）是死亡處理（DLL N5），v0.3 的版本已拿掉。
	EndIf
	; 5.7 關閉傳奇分支「連殺」：潛行攻擊擊殺後 5 秒內不解除潛行。
	; FIX15: controller dispatches streak with victim-owned attack facts.
	; 5.9 化灰：按 Round 14 擊殺歸因為神聖的目標化為灰燼（龍不受崩解，原版即如此）。
	If abAsh
		If akCtl.ApplyAsh(akTarget)
			OnAsh(akCtl, akTarget)
		EndIf
	EndIf
EndFunction

; 化灰的觸發條件：本次目標按 Round 14 歸因為神聖（使用者核准偏離規劃 8），或傳奇分支「淨土」。
Bool Function ShouldAsh(ESSBController akCtl, Int aiElement) Global
	If aiElement == 7
		Return True
	EndIf
	; Explicit design exception: Pure Land is a form-based talent, not provenance.
	If ESSBNodes.Br(akCtl, 6, 0, 4, 1) && akCtl.FormActive.GetValueInt() == 1 && akCtl.CurrentElement.GetValueInt() == 7 && akCtl.SyncStage() >= 3 ; @node 淨土
		Return True
	EndIf
	If aiElement == 0
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "ash-reject", "reason=no-element")
		EndIf
	Else
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "ash-reject", "reason=element-mismatch" + " element=" + aiElement)
		EndIf
	EndIf
	Return False
EndFunction

; 化灰之後的回饋（聖灰、淨灰）。
Function OnAsh(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.9 持續專精分支「聖灰」：敵人化為灰燼時你回復魔力 B_max ×2。
	If ESSBNodes.Br(akCtl, 6, 0, 2, 1) && player ; @node 聖灰
		akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 7) * 2.0, 0, player)
	EndIf
	; 5.9 關閉專精分支「淨灰」：化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷。
	If ESSBNodes.Br(akCtl, 6, 2, 2, 1) ; @node 淨灰
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.IsUndeadOrDaedra(nearby[index])
				akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 1.0), nearby[index])
			EndIf
			index += 1
		EndWhile
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "ash", akTarget.GetFormID() + " turned to ash")
	EndIf
EndFunction

; ================================================================== 風形態的移速與潛行（規劃 1.1、5.7）

; 風形態移速 +10%；持續專精主線再 +0.5%／點；大師分支「疾風」再 +10%。
; 疾風的「衝刺時每秒回補耐力再加倍」要先有 1.1 的風形態衝刺回補（基礎機制，本輪不在技能樹範圍，尚未實作）。
Float Function WindSpeedBonus(ESSBController akCtl) Global
	Float bonus = 10.0 + 0.5 * ESSBNodes.Rank(akCtl, 4, 0, 2) ; @node 風形態移速再
	If ESSBNodes.Br(akCtl, 4, 0, 3, 1) ; @node 疾風
		bonus = bonus + 10.0
	EndIf
	Return bonus
EndFunction

; 潛行中是否要換成「無聲」（Muffle 1.0 + 潛行移速 +20%）。
Bool Function HasSilent(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 4, 0, 2, 1) ; @node 無聲
EndFunction

; 5.7 持續傳奇分支「御風」：同調三段時免疫減速。
Bool Function WindSlowImmune(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 4, 0, 4, 0) && akCtl.SyncStage() >= 3 ; @node 御風
EndFunction

; 5.7 持續傳奇分支「御風」：失衡目標受你所有傷害 +30%（不看同調；v0.4 只有免疫減速看同調三段）；
; 5.7 關閉傳奇分支「空中追擊」：浮空目標受你所有傷害 ×1.5。只給 Papyrus 反應本體的傷害（ApplyDamage）；
; 附傷的同一項由 DLL 讀（Status.h ProcTerms），武器傷害那一半是 PERK 讀失衡效果。
Float Function TargetDamageMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If !akTarget
		Return mult
	EndIf
	If ESSBNodes.Br(akCtl, 4, 0, 4, 0) && ESSBNative.GetStatus(akTarget, 4) > 0 ; @node 御風
		mult = mult * 1.3
	EndIf
	If ESSBNodes.Br(akCtl, 4, 2, 4, 0) && ESSBNative.GetStatusFloat(akTarget, 14) > 0.0 ; @node 空中追擊
		mult = mult * 1.5
	EndIf
	Return mult
EndFunction



; FIX16 deviation: wind-form branch consumes recorded hit-time form, not killing element.
Function TryKillStreak(ESSBController akCtl, Int aiHitForm, Bool abSneak = False) Global
	If aiHitForm == 0
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "kill-streak-reject", "reason=no-element")
		EndIf
		Return
	EndIf
	If aiHitForm != 5
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "kill-streak-reject", "reason=element-mismatch" + " element=" + aiHitForm)
		EndIf
		Return
	EndIf
	If !ESSBNodes.Br(akCtl, 4, 2, 4, 1) ; @node 連殺
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "kill-streak-reject", "reason=branch-not-owned")
		EndIf
		Return
	EndIf
	If !abSneak
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "kill-streak-reject", "reason=not-sneak")
		EndIf
		Return
	EndIf
	akCtl.KeepSneak(5)
	; 下一次潛行攻擊附傷 ×2：DLL 讀你身上的連殺視窗、用掉就移除（死亡處理 N5 前由這裡掛）。
	ESSBNative.SetWindow(akCtl.ThePlayer(), 31, akCtl.DurationSeconds(5.0), 0.0)
EndFunction

; Terminal physical sneak attack: the victim is already dead, but the ambush's
; nearby-target effect remains meaningful. Never open marks or damage the corpse.
Function LethalAmbush(ESSBController akCtl, Actor akTarget) Global
	If !ESSBNodes.Br(akCtl, 4, 1, 2, 1) ; @node 奇襲
		Return
	EndIf
	Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 2, akTarget)
	; 5.7 持續大師分支「暗風」：潛行攻擊送出的風刃 ×2（DLL 的風刃已自己乘；這是 Papyrus 送的那一段）。
	Float bladeMult = 1.0
	If ESSBNodes.Br(akCtl, 4, 0, 3, 2) ; @node 暗風
		bladeMult = 2.0
	EndIf
	Int i = 0
	While i < nearby.Length
		If nearby[i]
			WindBlade(akCtl, nearby[i], bladeMult)
			BlowAway(akCtl, nearby[i], 1.0)
		EndIf
		i += 1
	EndWhile
EndFunction
