Scriptname ESSBElem2 Hidden
{大地（5.6）、風（5.7）、鮮血（5.8）、神聖（5.9）四棵元素樹的節點效果。

樹索引 3 土、4 風、5 血、6 聖（元素編號 4／5／6／7）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

物理推力（跌倒、拉近、吹飛、吹上天）一律走 ESSBController 的
Knockdown／PullIn／BlowBack／LiftUp，四者都在控制器裡做每目標冷卻與免疫名單，
本檔只決定「要不要推、推多遠」。浮空是自有的 1.5 秒狀態（ESSBStatus.AirLeft），
不讀物理狀態，落地傷害在狀態到期時結算（規劃 8 的空中追擊實作備註）。

所有傷害都走 ESSBController.ApplyDamage，G(L) 由 ApplyDamage 統一乘上。}

; ================================================================== 狀態上限（規劃 2.3）

; 土 岩甲（你）：基礎 5；厚土分支 10；萬象再 +1／每 5 點。
Int Function RockCap(ESSBController akCtl) Global
	Int cap = 5
	If ESSBNodes.Br(akCtl, 3, 0, 1, 1)
		cap = 10
	EndIf
	Return cap + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 土 岩甲每層護甲：15，磐石分支 25。
Float Function RockArmorPerLayer(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 0, 0, 0)
		Return 25.0 * akCtl.GLevel(3)
	EndIf
	Return 20.0 * akCtl.GLevel(3)
EndFunction

; 風 風勢門檻：4，亂舞分支 3（量表，不吃萬象）。
Int Function WindThreshold(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 4, 0, 1, 0)
		Return 3
	EndIf
	Return 4
EndFunction

; 血 血痕上限：8，深創分支 12；萬象再 +1／每 5 點。
Int Function BleedCap(ESSBController akCtl) Global
	Int cap = 8
	If ESSBNodes.Br(akCtl, 5, 0, 0, 1)
		cap = 12
	EndIf
	Return cap + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 聖 聖印上限：5；萬象再 +1／每 5 點。
Int Function HolyCap(ESSBController akCtl) Global
	Return 5 + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; ================================================================== 附傷倍率

Float Function HitExtra(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 4
		Return EarthHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 6
		Return BloodHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 7
		Return DivineHitExtra(akCtl, akTarget, abPower)
	EndIf
	; 5.7 風：開啟熟練主線是拉近距離，不是附傷；風附傷的節點與潛行 ×3 由 DLL 算。
	Return 0.0
EndFunction

; 5.6：開印後 5 秒內 +1%／點（土附傷與同調每段由 DLL 算）。
Float Function EarthHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	If akCtl.GetOpenBoost(4) > 0
		Return ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 3, 1, 1), 0.01)
	EndIf
	Return 0.0
EndFunction

; 5.8：開印後 5 秒內 +1%／點（血附傷、同調每段、血位曲線與血怒由 DLL 算）。
Float Function BloodHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	If akCtl.GetOpenBoost(6) > 0
		Return ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 5, 1, 1), 0.01)
	EndIf
	Return 0.0
EndFunction

; 5.9：開印後 5 秒內 +1%／點、聖印每層目標受聖傷 +1%／點、聖痕（聖附傷、同調每段、白天、亡靈魔族、驅魔由 DLL 算）。
Float Function DivineHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = HolyVulnerability(akCtl, akTarget)
	If akCtl.GetOpenBoost(7) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 6, 1, 1), 0.01)
	EndIf
	Return extra
EndFunction

; 聖印每層「目標受聖傷 +1%／點」＋聖痕的固定 +10%。裁決與聖光也吃同一個函式。
Float Function HolyVulnerability(ESSBController akCtl, Actor akTarget) Global
	Float bonus = 0.0
	Int stacks = akCtl.GetStack(akTarget, 6)
	If stacks > 0
		bonus = stacks * ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 6, 0, 0), 0.01) * ESSBNodes.OmniMult(akCtl)
		; 規劃 2.6 的基礎開印：聖印本身讓目標受聖傷 +20%。
		bonus = bonus + 0.2
	EndIf
	If ESSBNodes.Br(akCtl, 6, 1, 3, 0) && akCtl.HasElementMark(akTarget, 7)
		bonus = bonus + 0.1
	EndIf
	Return bonus
EndFunction

; ================================================================== 開印時的層數

; 土 開印岩甲 +2（岩膚 +4），開啟新手主線再 +1／每 5 點。
; 風 開印風勢 +2（疾風痕直接滿），開啟新手主線 +1／每 5 點。
; 血 開印流血 2 層，開啟新手主線 +1／每 5 點。
; 聖 開印聖印 1 層，開啟新手主線不加層（改為回血），所以維持 1。
Int Function OpenStacks(ESSBController akCtl, Int aiElement) Global
	If aiElement == 4
		Int rock = 2
		If ESSBNodes.Br(akCtl, 3, 1, 1, 1)
			rock = 4
		EndIf
		Return rock + ESSBNodes.Rank(akCtl, 3, 1, 0) / 5
	ElseIf aiElement == 5
		If ESSBNodes.Br(akCtl, 4, 1, 1, 0)
			Return WindThreshold(akCtl)
		EndIf
		Return 2 + ESSBNodes.Rank(akCtl, 4, 1, 0) / 5
	ElseIf aiElement == 6
		Return 2 + ESSBNodes.Rank(akCtl, 5, 1, 0) / 5
	ElseIf aiElement == 7
		Return 1
	EndIf
	Return 0
EndFunction

; 命中時的層數（規劃 2.3 的「命中」欄）。土風是自身資源、血聖是敵方狀態，都各 +1。
Int Function HitStacks(ESSBController akCtl, Int aiElement, Bool abPower) Global
	Return 1
EndFunction

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
	; 5.6 持續熟練分支「震擊」：重擊消耗滿層裂痕，1.5× 爆傷並削減 50 耐力。
	If ESSBNodes.Br(akCtl, 3, 0, 1, 0) && akCtl.GetStack(akTarget, 3) > 0
		akCtl.ApplyDamage(4, ESSBReactions.ReactDamage(akCtl, 4, 1.5), akTarget)
		akCtl.ApplyUtil(3, 80.0 * akCtl.GLevel(3), 0, akTarget)
		akCtl.SetStack(akTarget, 3, 0)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "node", "earth quakestrike " + akTarget.GetFormID())
		EndIf
	EndIf
	; 5.6 持續傳奇主線「地動」：同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點。
	Int rank = ESSBNodes.Rank(akCtl, 3, 0, 4)
	If rank > 0 && akCtl.SyncStage() >= 3 && akTarget.GetActorValuePercentage("Stamina") < 0.3
		If Utility.RandomFloat(0.0, 1.0) < 0.05 * rank
			akCtl.Knockdown(akTarget, 2.0)
		EndIf
	EndIf
EndFunction

Function OnWindHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 5.7 持續熟練分支「順風」（命中回復耐力）round 20 起由 DLL 在命中當下施放。
	; 5.7 持續傳奇主線「千刃」：同調三段時每次命中附帶風刃，機率 5%／點。
	Int rank = ESSBNodes.Rank(akCtl, 4, 0, 4)
	If rank > 0 && akCtl.SyncStage() >= 3 && Utility.RandomFloat(0.0, 1.0) < 0.05 * rank
		WindBlade(akCtl, akTarget, 1.0)
	EndIf
	; 5.7 關閉大師分支「順勢」的視窗在接管元素身上，不在風形態，見 OnEnd。
EndFunction

Function OnDivineHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 5.9 持續專精主線：命中回血 +2%／點（以 B_max 為基準）。
	Int heal = ESSBNodes.Rank(akCtl, 6, 0, 2)
	If heal > 0
		akCtl.ApplyUtil(4, 1.0 * heal * akCtl.GLevel(6), 0, player)
	EndIf
	; 5.9 持續新手分支「護持」：命中獲得 10% 魔抗 3 秒。
	If ESSBNodes.Br(akCtl, 6, 0, 0, 0)
		akCtl.ApplyUtil(8, 10.0, 3, player)
	EndIf
	; 5.9 持續熟練分支「神罰」：聖印滿層時每次命中額外一次 50% 聖光。
	If ESSBNodes.Br(akCtl, 6, 0, 1, 0) && akCtl.GetStack(akTarget, 6) >= HolyCap(akCtl)
		akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 0.5) \
			* (1.0 + HolyVulnerability(akCtl, akTarget)), akTarget)
	EndIf
	; 5.9 持續熟練分支「聖盾」：每命中 +1 層（最多 5），抵消魔法傷害（PERK 進入點 0x29）。
	If ESSBNodes.Br(akCtl, 6, 0, 1, 1)
		akCtl.AddHolyShield(1)
	EndIf
	; 5.9 大師分支「祝福」：命中時小範圍治療同伴。
	If ESSBNodes.Br(akCtl, 6, 0, 3, 0)
		HealAllies(akCtl, 25.0 * akCtl.GLevel(6))
	EndIf
EndFunction

; 同伴治療（祝福、聖臨強化、聖光）。ScanTargets 會排除同伴，所以另走 ScanAllies。
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
	; 5.6 開啟新手分支「震波」：開印時附近 1 人也裂痕。
	If ESSBNodes.Br(akCtl, 3, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 3, 1)
			akCtl.ApplyUtil(1, FissureArmor(akCtl), 8, nearby[0])
		EndIf
	EndIf
	; 5.6 開啟大師分支「地基」：開印目標 3 秒內移速 -30%。
	If ESSBNodes.Br(akCtl, 3, 1, 3, 0)
		akCtl.ApplyUtil(0, 30.0, 3, akTarget)
	EndIf
	; 5.6 開啟大師分支「裂地」：開印在目標腳下留 3 秒減速地帶（共用領域格）。
	If ESSBNodes.Br(akCtl, 3, 1, 3, 1)
		akCtl.StartDomain(4, akTarget, 3)
	EndIf
	; 5.6 開啟傳奇分支「先震」：同調三段時開印立即一次 ×0.5 地震，不含跌倒。
	If ESSBNodes.Br(akCtl, 3, 1, 4, 0) && akCtl.SyncStage() >= 3
		Quake(akCtl, akTarget, 0.5, False)
	EndIf
EndFunction

Function OpenWind(ESSBController akCtl, Actor akTarget, Float afMult = 1.0) Global
	Actor player = akCtl.ThePlayer()
	; 5.7 開啟專精分支「奇襲」：潛行攻擊的開印同時觸發終焉，且不拉近。
	Bool ambush = ESSBNodes.Br(akCtl, 4, 1, 2, 1) && akCtl.LastHitWasSneak()
	If !ambush
		; 規劃 2.6 基礎開印「風痕」：把目標拉近你 1.5 公尺；開啟熟練主線 +0.1 公尺／點。
		akCtl.PullIn(akTarget, PullDistance(akCtl) * afMult)
	EndIf
	; 5.7 開啟新手分支「風襲」：開印時附近 1 人也風痕。
	If ESSBNodes.Br(akCtl, 4, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 4, 1)
			akCtl.ApplyMark(nearby[0], 5)
		EndIf
	EndIf
	; 5.7 開啟熟練分支「輕躍」：開印後 3 秒移速 +10%。
	If ESSBNodes.Br(akCtl, 4, 1, 1, 1) && player
		akCtl.ApplyUtil(9, 10.0, 3, player)
	EndIf
	; 5.7 開啟大師分支「氣流」：開印時回復 10 耐力。
	If ESSBNodes.Br(akCtl, 4, 1, 3, 1) && player
		akCtl.ApplyUtil(6, 40.0 * akCtl.GLevel(4), 0, player)
	EndIf
	; 5.7 開啟傳奇分支「先風」：同調三段時開印附帶一段風刃。
	If ESSBNodes.Br(akCtl, 4, 1, 4, 0) && akCtl.SyncStage() >= 3
		WindBlade(akCtl, akTarget, afMult)
	EndIf
	If ambush
		; 一刀開印兼吹飛：立即結算一次風終焉（abChain = True，不再往外連鎖）。
		ESSBReactions.End(akCtl, 5, akTarget, 0, 1.0, True)
		BlowAway(akCtl, akTarget, 1.0)
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "wind ambush " + akTarget.GetFormID())
		EndIf
	EndIf
EndFunction

Function OpenBlood(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.8 開啟新手分支「血濺」：開印時附近 1 人流血 1 層。
	If ESSBNodes.Br(akCtl, 5, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 5, 1)
		EndIf
	EndIf
	; 5.8 開啟熟練分支「開印回血」：開印時你回血 B_max ×0.5，低血位 ×2。
	If ESSBNodes.Br(akCtl, 5, 1, 1, 1) && player
		Float heal = 25.0 * akCtl.GLevel(5)
		If player.GetActorValuePercentage("Health") < 0.3
			heal = heal * 2.0
		EndIf
		akCtl.ApplyUtil(4, heal, 0, player)
	EndIf
	; 5.8 開啟大師分支「血咒」：開印目標 5 秒內受治療 -50%。
	If ESSBNodes.Br(akCtl, 5, 1, 3, 0)
		akCtl.ApplyUtil(20, 50.0, 5, akTarget)
	EndIf
	; 5.8 開啟大師分支「血脈」：開印時 +2 同調。
	If ESSBNodes.Br(akCtl, 5, 1, 3, 1)
		akCtl.AddSync(2)
	EndIf
	; 5.8 關閉大師分支「血引」：血終焉後接管元素的開印附帶流血 2 層（跨元素，所以在控制器）。
	Int pending = akCtl.TakePendingBleed()
	If pending > 0
		akCtl.AddStackTo(akTarget, 5, pending)
	EndIf
	; 5.8 開啟傳奇分支「血祭之始」：同調三段時開印立即結算一次 ×0.5 血潮。
	If ESSBNodes.Br(akCtl, 5, 1, 4, 0) && akCtl.SyncStage() >= 3
		ESSBReactions.End(akCtl, 6, akTarget, 0, 0.5, True)
	EndIf
EndFunction

Function OpenDivine(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.9 開啟新手主線：開印回血 +5%／點（以 B_max 為基準，疊在基礎的 ×0.5 上）。
	Int rank = ESSBNodes.Rank(akCtl, 6, 1, 0)
	If rank > 0 && player
		akCtl.ApplyUtil(4, 2.0 * rank * akCtl.GLevel(6), 0, player)
	EndIf
	; 5.9 開啟新手分支「聖輝」：開印時附近 1 人也聖印。
	If ESSBNodes.Br(akCtl, 6, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 6, 1)
			akCtl.ApplyMark(nearby[0], 7)
		EndIf
	EndIf
	; 5.9 開啟熟練分支「聖護」：開印時獲得 10% 魔抗 3 秒。
	If ESSBNodes.Br(akCtl, 6, 1, 1, 1) && player
		akCtl.ApplyUtil(8, 10.0, 3, player)
	EndIf
	; 5.9 開啟大師分支「聖光」：開印時附近同伴回血 B_max。
	If ESSBNodes.Br(akCtl, 6, 1, 3, 1)
		HealAllies(akCtl, 40.0 * akCtl.GLevel(6))
	EndIf
	; 5.9 關閉大師分支「聖引」：聖終焉後接管元素的開印治療你 B_max。
	If akCtl.TakePendingHeal() && player
		akCtl.ApplyUtil(4, 40.0 * akCtl.GLevel(6), 0, player)
	EndIf
	; 5.9 開啟傳奇分支「聖啟」：同調三段時開印對亡靈魔族立即一次 ×0.5 裁決。
	If ESSBNodes.Br(akCtl, 6, 1, 4, 0) && akCtl.SyncStage() >= 3 && akCtl.IsUndeadOrDaedra(akTarget)
		Judge(akCtl, akTarget, 0.5)
	EndIf
EndFunction

; 5.6 持續新手主線：裂痕護甲削減 -30 → -60（+2／點）。
Float Function FissureArmor(ESSBController akCtl) Global
	Return (60.0 + 4.0 * ESSBNodes.Rank(akCtl, 3, 0, 0)) * akCtl.GLevel(3)
EndFunction

; 5.7 開啟熟練主線：開印拉近距離 1.5 公尺 +0.1 公尺／點，上限 3 公尺。
Float Function PullDistance(ESSBController akCtl) Global
	Float metres = 1.5 + 0.1 * ESSBNodes.Rank(akCtl, 4, 1, 1)
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
		; 5.6 開啟專精分支「地臨強化」：地臨時岩甲滿層，範圍內敵人減速 30% 3 秒。
		If ESSBNodes.Br(akCtl, 3, 1, 2, 0)
			akCtl.SetSelf(2, RockCap(akCtl))
			Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.ApplyUtil(0, 30.0, 3, nearby[index])
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 5
		; 5.7 開啟專精分支「氣旋」：風臨時把範圍內敵人拉到你面前 2 公尺。
		If ESSBNodes.Br(akCtl, 4, 1, 2, 0)
			Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.PullIn(nearby[index], 2.0)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 6
		; 5.8 開啟專精分支「血臨強化」：血臨後 10 秒不扣血。
		If ESSBNodes.Br(akCtl, 5, 1, 2, 0)
			akCtl.SetNoBloodCost(10)
		EndIf
	ElseIf aiElement == 7
		; 5.9 開啟專精分支「聖臨強化」：聖臨時你與附近同伴回血 B_max ×2。
		If ESSBNodes.Br(akCtl, 6, 1, 2, 0)
			akCtl.ApplyUtil(4, 60.0 * akCtl.GLevel(6), 0, player)
			HealAllies(akCtl, 60.0 * akCtl.GLevel(6))
		EndIf
	EndIf
EndFunction

; ================================================================== 土：地震

; 5.6 關閉新手分支「崩裂」：地震 ×1.5 → ×2.0。
Float Function QuakeK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 2, 0, 0)
		Return 2.0
	EndIf
	Return 1.5
EndFunction

; 5.6 關閉熟練分支「廣震」：地震範圍 3 → 5 公尺（1 公尺 = 70 單位）。
Float Function QuakeRadius(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 3, 2, 1, 0)
		Return 350.0
	EndIf
	Return 210.0
EndFunction

; 5.6 關閉專精主線：地震耐力削減 +3%／點（基礎 B_max ×2.0）。
Float Function QuakeStamina(ESSBController akCtl) Global
	Return 4.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2)) * akCtl.GLevel(3)
EndFunction

; 地震本體（規劃 2.6）：範圍土傷 + 削耐；耐力被打到 0 的目標跌倒，其餘減速 30% 3 秒。
Function Quake(ESSBController akCtl, Actor akTarget, Float afMult, Bool abKnock) Global
	Float amount = ESSBReactions.ReactDamage(akCtl, 4, QuakeK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 4)
	Float stamina = ESSBReactions.ReactDamage(akCtl, 4, QuakeStamina(akCtl)) * afMult
	Bool dust = ESSBNodes.Br(akCtl, 3, 2, 3, 1)
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

; 5.6 持續大師分支「反震」：岩甲滿層時被近戰命中反震一次土傷並使攻擊者跌倒，
; 每 10 秒一次，清空岩甲。由 ESSBGuard 在玩家受擊時呼叫。
Bool Function OnEarthRetaliate(ESSBController akCtl, Actor akAttacker, Int aiRockBefore) Global
	If !ESSBNodes.Br(akCtl, 3, 0, 3, 1) || !akAttacker
		Return False
	EndIf
	If aiRockBefore < RockCap(akCtl) || !akCtl.TakeRetaliate()
		Return False
	EndIf
	akCtl.ClearSelf(2)
	akCtl.ApplyDamage(4, ESSBReactions.ReactDamage(akCtl, 4, 2.0), akAttacker)
	If !akCtl.Knockdown(akAttacker, 3.0)
		akCtl.ApplyUtil(0, 30.0, 3, akAttacker)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "earth retaliate " + akAttacker.GetFormID())
	EndIf
	Return True
EndFunction

; ================================================================== 風：風刃、吹飛、吹上天

; 5.7 持續新手主線：風刃傷害 +2%／點；暗風讓潛行送出的風刃 ×2。
Float Function WindBladeMult(ESSBController akCtl) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 4, 0, 0), 0.02)
	If ESSBNodes.Br(akCtl, 4, 0, 3, 2) && akCtl.LastHitWasSneak()
		mult = mult * 2.0
	EndIf
	Return mult
EndFunction

; 風刃：單體一段 B_max ×1.0；迴旋分支改為對附近 2 人各一段。
; 失衡目標受風刃傷害 +30%（規劃 2.3）。
Function WindBlade(ESSBController akCtl, Actor akTarget, Float afMult) Global
	If !akTarget
		Return
	EndIf
	Float amount = ESSBReactions.ReactDamage(akCtl, 5, 1.0) * afMult * WindBladeMult(akCtl)
	WindBladeOne(akCtl, akTarget, amount)
	If ESSBNodes.Br(akCtl, 4, 0, 0, 0)
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
	If akCtl.GetStack(akTarget, 4) > 0
		amount = amount * 1.3
	EndIf
	akCtl.ApplyDamage(5, amount, akTarget)
	Actor player = akCtl.ThePlayer()
	; 5.7 持續專精分支「追風」：風刃命中回復耐力 3，並讓目標失衡。
	If ESSBNodes.Br(akCtl, 4, 0, 2, 0)
		If player
			akCtl.ApplyUtil(6, 15.0 * akCtl.GLevel(4), 0, player)
		EndIf
		akCtl.AddStackTo(akTarget, 4, 1)
	EndIf
	; 5.7 關閉傳奇分支「空中追擊」：風刃命中空中目標再推高 1 公尺並延長滯空。
	If ESSBNodes.Br(akCtl, 4, 2, 4, 0) && akCtl.GetAirborne(akTarget) > 0
		akCtl.LiftUp(akTarget, 1.0, LandingDamage(akCtl))
	EndIf
EndFunction

; 風勢到門檻就送出風刃並歸零（規劃 2.3）。由控制器在命中後呼叫。
Function CheckWindGauge(ESSBController akCtl, Actor akTarget) Global
	If akCtl.GetSelf(3) < WindThreshold(akCtl)
		Return
	EndIf
	akCtl.ClearSelf(3)
	WindBlade(akCtl, akTarget, 1.0)
EndFunction

; 5.7 關閉專精主線：吹飛距離 3 公尺 +0.2 公尺／點，上限 6 公尺。
Float Function BlowDistance(ESSBController akCtl) Global
	Float metres = 3.0 + 0.2 * ESSBNodes.Rank(akCtl, 4, 2, 2)
	If metres > 6.0
		metres = 6.0
	EndIf
	Return metres
EndFunction

; 5.7 關閉傳奇主線：落地傷害 B_max ×0.5 +5%／點（點滿 ×1.25）。
Float Function LandingDamage(ESSBController akCtl) Global
	Float k = 0.5 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 4, 2, 4), 0.05)
	; 5.7 關閉熟練分支「上天」把基礎落地傷害提到 B_max ×1.0。
	If ESSBNodes.Br(akCtl, 4, 2, 1, 0)
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
	Bool lifted = ESSBNodes.Br(akCtl, 4, 2, 1, 0)
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

; 5.8 持續新手主線：流血每層傷害 +2%／點。
Float Function BleedPerLayer(ESSBController akCtl) Global
	Return ESSBReactions.BaseMax(akCtl, 6) * akCtl.BleedDotK.GetValue() * akCtl.GetDamageMult(6) \
		* ESSBNodes.OmniMult(akCtl) * BleedTickMult(akCtl)
EndFunction

Float Function BleedTickMult(ESSBController akCtl) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 5, 0, 0), 0.02)
	; 5.8 持續大師分支「止血」：低血位（30% 以下）時流血傷害 ×1.5。
	Actor player = akCtl.ThePlayer()
	If ESSBNodes.Br(akCtl, 5, 0, 3, 0) && player && player.GetActorValuePercentage("Health") < 0.3
		mult = mult * 1.5
	EndIf
	Return mult
EndFunction

; 5.8 持續新手主線：放血係數 0.3% +0.01%／點（首領 0.1%，同樣按比例成長）。
Float Function BleedDrainPercent(ESSBController akCtl, Bool abVIP) Global
	Float percent = 0.003 + 0.0001 * ESSBNodes.Rank(akCtl, 5, 0, 0)
	If abVIP
		percent = percent / 3.0
	EndIf
	Return percent
EndFunction

; 5.8 關閉專精主線：血潮治療倍率 ×2 → 每點 +0.1。
Float Function SurgeHealMult(ESSBController akCtl) Global
	Return 2.0 + 0.1 * ESSBNodes.Rank(akCtl, 5, 2, 2)
EndFunction

; 5.8 關閉大師分支「放血終焉」：血潮的當前生命項 10% → 20%（首領 3% → 6%）。
Float Function SurgePercent(ESSBController akCtl, Bool abVIP) Global
	Float percent = 0.10
	If abVIP
		percent = 0.03
	EndIf
	If ESSBNodes.Br(akCtl, 5, 2, 3, 1)
		percent = percent * 2.0
	EndIf
	Return percent
EndFunction

; ================================================================== 聖：裁決

; 5.9 關閉新手分支「重裁」：裁決 ×2.0 → ×3.0。
Float Function JudgeK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 6, 2, 0, 0)
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 裁決本體（規劃 2.6）：B_max ×2.0 聖傷，對亡靈魔族 ×3，治療你 B_max ×1.0。
Function Judge(ESSBController akCtl, Actor akTarget, Float afMult, Float afHealBase = 25.0) Global
	Actor player = akCtl.ThePlayer()
	Float amount = ESSBReactions.ReactDamage(akCtl, 7, JudgeK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 7) * (1.0 + HolyVulnerability(akCtl, akTarget))
	If IsHolyPrey(akCtl, akTarget)
		amount = amount * 3.0
	EndIf
	akCtl.ApplyDamage(7, amount, akTarget)
	If player
		akCtl.ApplyUtil(4, afHealBase * akCtl.GetDamageMult(7) * akCtl.GLevel(6), 0, player)
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
	Return ESSBNodes.Br(akCtl, 6, 1, 3, 0) && akCtl.HasElementMark(akTarget, 7)
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
	; 5.6 關閉熟練分支「固土」：土終焉後你岩甲滿層。
	If ESSBNodes.Br(akCtl, 3, 2, 1, 1)
		akCtl.SetSelf(2, RockCap(akCtl))
	EndIf
	; 5.6 關閉大師分支「山崩」：土終焉對範圍內所有帶裂痕的目標各一次地震。
	If ESSBNodes.Br(akCtl, 3, 2, 3, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, QuakeRadius(akCtl), 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.GetStack(nearby[index], 3) > 0
				Quake(akCtl, nearby[index], afMult, False)
			EndIf
			index += 1
		EndWhile
	EndIf
	If aiReason != 1
		Return
	EndIf
	; 5.6 關閉傳奇分支「地裂」：融斷後留下 5 秒地裂帶；
	; 關閉專精分支「地斷」：融斷附帶 3 秒泥沼。兩者共用同一格領域，地裂優先。
	If ESSBNodes.Br(akCtl, 3, 2, 4, 0)
		akCtl.StartDomain(4, akTarget, 5)
	ElseIf ESSBNodes.Br(akCtl, 3, 2, 2, 0)
		akCtl.StartDomain(4, akTarget, 3)
	EndIf
EndFunction

Function EndWindNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.7 關閉專精分支「風渦」：終焉時 5 公尺內敵人被拉向目標聚攏。
	If ESSBNodes.Br(akCtl, 4, 2, 2, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.PullTo(nearby[index], akTarget, 2.0)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.7 關閉大師分支「順勢」：風終焉後 5 秒內接管元素的命中皆附帶一段風刃。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 4, 2, 3, 1)
		akCtl.SetWindFollow(5)
	EndIf
	If aiReason != 1
		Return
	EndIf
	; 5.7 關閉熟練分支「風斷」：風印記融斷時每個目標各兩段風刃。
	If ESSBNodes.Br(akCtl, 4, 2, 1, 1)
		WindBlade(akCtl, akTarget, 1.0)
		WindBlade(akCtl, akTarget, 1.0)
	EndIf
	; 5.7 關閉大師分支「颶風」：融斷的吹上天改為對範圍內所有敵人，不限帶風印記。
	If ESSBNodes.Br(akCtl, 4, 2, 3, 0)
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
	; 5.8 關閉熟練分支「血漫」：血潮結算時附近流血目標一起血潮。
	If ESSBNodes.Br(akCtl, 5, 2, 1, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.GetStack(nearby[index], 5) > 0
				ESSBReactions.End(akCtl, 6, nearby[index], 2, afMult, True)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.8 關閉專精分支「血約」：血終焉後 8 秒不扣血。
	If ESSBNodes.Br(akCtl, 5, 2, 2, 0)
		akCtl.SetNoBloodCost(8)
	EndIf
	; 5.8 關閉大師分支「血引」：血終焉後接管元素的開印附帶流血 2 層。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 5, 2, 3, 2)
		akCtl.SetPendingBleed(2)
	EndIf
	; 5.8 關閉傳奇分支「血池」：血印記融斷後留下 5 秒血池。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 5, 2, 4, 0)
		akCtl.StartDomain(6, akTarget, 5)
	EndIf
EndFunction

Function EndDivineNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 5.9 持續專精分支「光耀」：裁決後附近亡靈魔族減速。
	If ESSBNodes.Br(akCtl, 6, 0, 2, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.IsUndeadOrDaedra(nearby[index])
				akCtl.ApplyUtil(0, 40.0, 4, nearby[index])
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.9 大師分支「處決」：裁決處決範圍內低於 20% 生命的亡靈魔族。
	If ESSBNodes.Br(akCtl, 6, 2, 3, 0)
		Actor[] prey = akCtl.ScanTargets(akTarget, 350.0, 5, None)
		Int index = 0
		While index < prey.Length
			If prey[index] && IsHolyPrey(akCtl, prey[index]) \
				&& prey[index].GetActorValuePercentage("Health") < 0.2
				If akCtl.IsVIPTarget(prey[index])
					akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 5.0), prey[index])
				Else

					akCtl.Execute(prey[index], 7)
				EndIf
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.9 關閉大師分支「聖引」：聖終焉後接管元素的開印治療你 B_max。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 6, 2, 3, 1)
		akCtl.SetPendingHeal()
	EndIf
	; 5.9 關閉熟練分支「聖斷」：聖印記融斷每個目標治療你 B_max ×1.0。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 6, 2, 1, 1) && player
		akCtl.ApplyUtil(4, 25.0 * akCtl.GetDamageMult(7) * akCtl.GLevel(6), 0, player)
	EndIf
	; 5.9 關閉專精分支「聖域」5 秒／傳奇分支「神聖領域」8 秒（融斷後）。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 6, 2, 4, 0)
		akCtl.StartDomain(7, akTarget, 8)
	ElseIf ESSBNodes.Br(akCtl, 6, 2, 2, 0)
		akCtl.StartDomain(7, akTarget, 5)
	EndIf
EndFunction

; ================================================================== 每秒與擊殺

Function OnTick(ESSBController akCtl, Int aiElement) Global
	If aiElement != 7
		Return
	EndIf
	; 5.9 大師分支「庇護」：生命低於 30% 時自動聖盾滿層，每 30 秒一次。
	If !ESSBNodes.Br(akCtl, 6, 0, 3, 1)
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If player && player.GetActorValuePercentage("Health") < 0.3 && akCtl.TakeSanctuary()
		akCtl.AddHolyShield(5)
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "divine sanctuary")
		EndIf
	EndIf
EndFunction

; 化身（通用樹持續傳奇主線）觸發的「當前元素持續傳奇效果」。
Function OnAvatar(ESSBController akCtl, Int aiElement) Global
	Actor player = akCtl.ThePlayer()
	If aiElement == 4
		; 地動：對最近的帶裂痕目標直接跌倒並補一次地震。
		Actor victim = akCtl.NearestMarked(4)
		If victim
			Quake(akCtl, victim, 1.0, True)
		EndIf
	ElseIf aiElement == 5
		; 千刃：對最近的風印記目標連送三段風刃。
		Actor victim = akCtl.NearestMarked(5)
		If victim
			WindBlade(akCtl, victim, 1.0)
			WindBlade(akCtl, victim, 1.0)
			WindBlade(akCtl, victim, 1.0)
		EndIf
	ElseIf aiElement == 6
		; 血海：對最近的流血目標結算一次範圍血潮。
		Actor victim = akCtl.NearestMarked(6)
		If victim
			ESSBReactions.End(akCtl, 6, victim, 2, 1.0, True)
		EndIf
	ElseIf aiElement == 7
		; 天啟：對最近的聖印記目標結算一次範圍裁決。
		Actor victim = akCtl.NearestMarked(7)
		If victim
			JudgeArea(akCtl, victim, 1.0)
		EndIf
	EndIf
EndFunction

; 5.9 持續傳奇主線「天啟」：同調三段時裁決改為範圍，1 公尺 +0.2 公尺／點。
Function JudgeArea(ESSBController akCtl, Actor akTarget, Float afMult) Global
	Judge(akCtl, akTarget, afMult)
	Int rank = ESSBNodes.Rank(akCtl, 6, 0, 4)
	Bool wide = ESSBNodes.Br(akCtl, 6, 2, 1, 0)
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
	Float healLeft = 75.0
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			Float healBase = 25.0
			If healBase > healLeft
				healBase = healLeft
			EndIf
			Judge(akCtl, nearby[index], afMult, healBase)
			healLeft = healLeft - healBase
		EndIf
		index += 1
	EndWhile
EndFunction

; 5.8 持續傳奇主線「血海」：同調三段時血潮改為範圍，1 公尺 +0.2 公尺／點。
Float Function SurgeRadius(ESSBController akCtl) Global
	Int rank = ESSBNodes.Rank(akCtl, 5, 0, 4)
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
		; 5.8 持續熟練分支「飲血」：擊殺流血目標回血 20%，並獲得 10 秒嗜血。
		If ESSBNodes.Br(akCtl, 5, 0, 1, 0)
			akCtl.ApplyUtil(4, player.GetActorValueMax("Health") * 0.2, 0, player)
			akCtl.SetBloodthirst(10)
		EndIf
		; 5.8 持續專精分支「血承」：吸收死者屬性 15 秒，只保留最近一個。
		If ESSBNodes.Br(akCtl, 5, 0, 2, 1)
			akCtl.ApplyInherit(akTarget)
		EndIf
		; 5.8 持續傳奇分支「不死」：同調三段時流血目標死亡回滿耐力。
		If ESSBNodes.Br(akCtl, 5, 0, 4, 0) && akCtl.SyncStage() >= 3
			akCtl.ApplyUtil(6, player.GetActorValueMax("Stamina"), 0, player)
		EndIf
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
	If ESSBNodes.Br(akCtl, 6, 0, 4, 1) && akCtl.FormActive.GetValueInt() == 1 && akCtl.CurrentElement.GetValueInt() == 7 && akCtl.SyncStage() >= 3
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
	If ESSBNodes.Br(akCtl, 6, 0, 2, 1) && player
		akCtl.ApplyUtil(5, 60.0 * akCtl.GLevel(6), 0, player)
	EndIf
	; 5.9 關閉專精分支「淨灰」：化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷。
	If ESSBNodes.Br(akCtl, 6, 2, 2, 1)
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
Float Function WindSpeedBonus(ESSBController akCtl) Global
	Float bonus = 10.0 + 0.5 * ESSBNodes.Rank(akCtl, 4, 0, 2)
	If ESSBNodes.Br(akCtl, 4, 0, 3, 1)
		bonus = bonus + 10.0
	EndIf
	Return bonus
EndFunction

; 潛行中是否要換成「無聲」（Muffle 1.0 + 潛行移速 +20%）。
Bool Function HasSilent(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 4, 0, 2, 1)
EndFunction

; 5.7 持續傳奇分支「御風」：同調三段時免疫減速。
Bool Function WindSlowImmune(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 4, 0, 4, 0) && akCtl.SyncStage() >= 3
EndFunction

; 5.7 持續傳奇分支「御風」：失衡目標受你所有傷害 +30%；
; 5.7 關閉傳奇分支「空中追擊」：浮空目標受你所有傷害 ×1.5。
Float Function TargetDamageMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If !akTarget
		Return mult
	EndIf
	If ESSBNodes.Br(akCtl, 4, 0, 4, 0) && akCtl.SyncStage() >= 3 && akCtl.GetStack(akTarget, 4) > 0
		mult = mult * 1.3
	EndIf
	If ESSBNodes.Br(akCtl, 4, 2, 4, 0) && akCtl.GetAirborne(akTarget) > 0
		mult = mult * 1.5
	EndIf
	Return mult
EndFunction

; 5.7 關閉傳奇分支「連殺」：下一次潛行攻擊附傷 ×2。
Float Function KillStreakMult(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 4, 2, 4, 1) && akCtl.TakeKillStreak()
		Return 2.0
	EndIf
	Return 1.0
EndFunction

; 5.7 持續大師分支「暗風」：潛行攻擊的風附傷 ×3 → ×5。
Float Function SneakMult(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 4, 0, 3, 2)
		Return 5.0
	EndIf
	Return 3.0
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
	If !ESSBNodes.Br(akCtl, 4, 2, 4, 1)
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
EndFunction

; Terminal physical sneak attack: the victim is already dead, but the ambush's
; nearby-target effect remains meaningful. Never open marks or damage the corpse.
Function LethalAmbush(ESSBController akCtl, Actor akTarget) Global
	If !ESSBNodes.Br(akCtl, 4, 1, 2, 1)
		Return
	EndIf
	Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 2, akTarget)
	Int i = 0
	While i < nearby.Length
		If nearby[i]
			WindBlade(akCtl, nearby[i], 1.0)
			BlowAway(akCtl, nearby[i], 1.0)
		EndIf
		i += 1
	EndWhile
EndFunction
