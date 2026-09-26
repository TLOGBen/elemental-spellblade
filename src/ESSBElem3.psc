Scriptname ESSBElem3 Hidden
{毒素（5.10）、水（5.11）、黑暗（5.12）、星界（5.13）四棵元素樹的節點效果。

樹索引 7 毒、8 水、9 暗、10 星（元素編號 8／9／10／11）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）／ESSBElem2（土風血聖）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

本輪的四個特殊機制：
  毒（2.3）毒層無上限、每層獨立 12 秒（ESSBStatus 的十二格環狀桶），終焉不結清只催毒，
      ≥門檻每 N 秒向 3 公尺內一名敵人傳 1 層；擴散間隔與門檻由節點改。
  水（5.11）長流是每秒百分比回復（規劃 8：自有效果，不動回復速率 AV），
      洗淨／淨化走「限定關鍵字的 Dispel 原型」，沖刷／洗滌走「對目標的 Dispel 原型」。
  暗（5.12）恐懼與瘋狂用自有 Demoralize（原型 7）／Frenzy（原型 8）效果，
      magnitude 就是等級上限（同原版幻術），首領、龍、亡靈魔族與機械免疫；
      亡者歸來（v0.4 的基礎死亡機制，DLL N5＋Papyrus）的六階表在這裡，復生本身等 N5 接上。
  星（v0.4 5.13）範圍與其他元素相同（星臨 2 公尺 +0.2 公尺／點）；v0.3 的「每點 +1 公尺、夜晚 ×1.5」已拿掉。

所有傷害都走 ESSBController.ApplyDamage，G(L) 由 ApplyDamage 統一乘上；
真實傷害（星斷）走 ApplyTrueDamage(amount, target, 樹)。}

; ================================================================== 狀態上限（規劃 2.3）

; 毒 毒層：無上限（0 代表無上限，見 ESSBController.StackCap）。
; 水 水壓：基礎 5；萬象再 +1／每 5 點。
Int Function PressureCap(ESSBController akCtl) Global
	Return 5 + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 暗 詛咒：基礎 5；傳奇主線「深淵」同調三段時 +1／每 3 點（最多 +5，共 10）；萬象再加。
Int Function CurseCap(ESSBController akCtl) Global
	Int cap = 5
	Int rank = ESSBNodes.Rank(akCtl, 9, 0, 4) ; @node 深淵
	If rank > 0 && akCtl.SyncStage() >= 3
		Int extra = rank / 3
		If extra > 5
			extra = 5
		EndIf
		cap = cap + extra
	EndIf
	Return cap + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; 星 星痕：基礎 3；持續專精主線 +1／每 5 點；萬象再加。
Int Function AstralCap(ESSBController akCtl) Global
	Return 3 + ESSBNodes.Rank(akCtl, 10, 0, 2) / 5 + ESSBNodes.StatusCapBonus(akCtl) ; @node 星痕層數上限
EndFunction

; ================================================================== 範圍

; 星臨（5.13 開啟大師主線）：與其他元素的「臨」相同，2 公尺 +0.2 公尺／點（星臨強化用同一個範圍）。
Float Function AdventRadius(ESSBController akCtl) Global
	Return (2.0 + 0.2 * ESSBNodes.Rank(akCtl, 10, 1, 3)) * 70.0 ; @node 星臨
EndFunction

; ================================================================== 附傷倍率

Float Function HitExtra(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 8
		Return PoisonHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 9
		Return WaterHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 10
		Return DarkHitExtra(akCtl, akTarget, abPower)
	ElseIf aiElement == 11
		Return AstralHitExtra(akCtl, akTarget, abPower)
	EndIf
	Return 0.0
EndFunction

; 5.10：開印後 5 秒內 +1%／點（毒附傷與同調每段由 DLL 算）。
Float Function PoisonHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	If akCtl.GetOpenBoost(8) > 0
		Return ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 1, 1), 0.01) ; @node 開印後 5 秒內毒附傷
	EndIf
	Return 0.0
EndFunction

; 5.11：開印後 5 秒內 +1%／點、水壓每層 +（10% + 1%／點）（「水壓」分支才會有層數）。
Float Function WaterHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = 0.0
	If akCtl.GetOpenBoost(9) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 8, 1, 1), 0.01) ; @node 開印後 5 秒內水附傷
	EndIf
	; 水壓層數只有「水壓」分支才會產生，沒投點就不查狀態容器（命中路徑）。
	If ESSBNodes.Br(akCtl, 8, 0, 1, 0) ; @node 水壓
		Int pressure = akCtl.GetStack(akTarget, 9)
		If pressure > 0
			Float perLayer = 0.1 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 8, 0, 2), 0.01) ; @node 水壓每層水附傷
			extra = extra + pressure * perLayer * ESSBNodes.OmniMult(akCtl)
		EndIf
	EndIf
	Return extra
EndFunction

; 5.12：開印後 5 秒內 +1%／點（暗附傷、同調每段、夜晚由 DLL 算）。
Float Function DarkHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	If akCtl.GetOpenBoost(10) > 0
		Return ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 1, 1), 0.01) ; @node 開印後 5 秒內暗附傷
	EndIf
	Return 0.0
EndFunction

; 5.13：開印後 5 秒內 +1%／點、星痕弱點（重擊時每層星痕 +8%）（星附傷與同調每段由 DLL 算）。
Float Function AstralHitExtra(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float extra = 0.0
	If akCtl.GetOpenBoost(11) > 0
		extra = extra + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 10, 1, 1), 0.01) ; @node 開印後 5 秒內星附傷
	EndIf
	If abPower && ESSBNodes.Br(akCtl, 10, 0, 2, 0) ; @node 星痕弱點
		extra = extra + 0.08 * akCtl.GetStack(akTarget, 11) * ESSBNodes.OmniMult(akCtl)
	EndIf
	Return extra
EndFunction

; 5.13 開啟大師分支「星鎖」（開印目標 3 秒內受所有元素傷 +10%）與關閉傳奇分支「星域」（內部敵人受所有元素傷 +20%）。
; 決定 61：攻擊類進入點讀不到目標，所以這兩條只放大本模組造成的傷害。
; v0.4 暗的持續專精主線是「幻覺持續」（DLL N3），v0.3 的「詛咒滿層目標受所有傷害 +1%／點」已拿掉。
Float Function TargetDamageMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If !akTarget
		Return mult
	EndIf
	; 查詢都先看節點有沒有投點，沒投就完全不碰狀態（這是命中路徑，見效能守則）。
	If ESSBNodes.Br(akCtl, 10, 1, 3, 0) && akCtl.HasStarLock(akTarget) ; @node 星鎖
		mult = mult * 1.1
	EndIf
	If ESSBNodes.Br(akCtl, 10, 2, 4, 0) && akCtl.InDomain(akTarget, 11) ; @node 星域
		mult = mult * 1.2
	EndIf
	Return mult
EndFunction

; ================================================================== 開印時的層數

; 毒 開印 +3 毒層，開啟新手主線 +1／每 3 點；劇毒之始在 OpenPoison 再加一份。
; 水 浸濕是單層狀態，固定 1。
; 暗 開印 2 層詛咒，開啟新手主線 +1／每 5 點。
; 星 開印 1 層星痕，開啟新手主線不加層（改為縮短延遲），所以維持 1。
Int Function OpenStacks(ESSBController akCtl, Int aiElement) Global
	If aiElement == 8
		Return 3 + ESSBNodes.Rank(akCtl, 7, 1, 0) / 3 ; @node 開印劑數
	ElseIf aiElement == 9
		Return 1
	ElseIf aiElement == 10
		Return 2 + ESSBNodes.Rank(akCtl, 9, 1, 0) / 5 ; @node 開印詛咒
	ElseIf aiElement == 11
		Return 1
	EndIf
	Return 0
EndFunction

; 命中時的層數（規劃 2.3 的「命中」欄）：四個元素都各 +1。
Int Function HitStacks(ESSBController akCtl, Int aiElement, Bool abPower) Global
	Return 1
EndFunction

; ================================================================== 每次命中（元素專屬）

Function OnHit(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 8
		OnPoisonHit(akCtl, akTarget, abPower)
	ElseIf aiElement == 9
		OnWaterHit(akCtl, akTarget, abPower)
	ElseIf aiElement == 10
		OnDarkHit(akCtl, akTarget, abPower)
	EndIf
	; 星：v0.3 的「追擊」「星軌」（持續熟練分支）v0.4 已移除，命中沒有星的專屬工作。
EndFunction

Function OnPoisonHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 兩個分支都沒投就不查狀態容器（命中路徑）。
	If !ESSBNodes.Br(akCtl, 7, 0, 1, 0) && !ESSBNodes.Br(akCtl, 7, 0, 2, 0) ; @node 萎靡, 侵蝕
		Return
	EndIf
	Int stacks = akCtl.GetStack(akTarget, 7)
	; 5.10 持續熟練分支「萎靡」：目標中毒 ≥5 劑（v0.3 毒層，N3 改成劑）時攻擊 -15%。
	If stacks >= 5 && ESSBNodes.Br(akCtl, 7, 0, 1, 0) ; @node 萎靡
		akCtl.ApplyUtil(17, 15.0, 3, akTarget)
	EndIf
	; 5.10 持續專精分支「侵蝕」：目標中毒滿劑（10）時毒抗 -20%。
	If stacks >= 10 && ESSBNodes.Br(akCtl, 7, 0, 2, 0) ; @node 侵蝕
		akCtl.ApplyUtil(24, 20.0, 6, akTarget)
	EndIf
EndFunction

; v0.3 的「水牢」「水鏡」v0.4 已移除。
Function OnWaterHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 5.11 持續新手分支「清流」（命中回復耐力）round 20 起由 DLL 在命中當下施放。
	Bool wet = akCtl.IsWet(akTarget) || akCtl.IsEnvWet()
	; 5.11 持續熟練分支「水壓」：命中浸濕目標 +1 水壓。
	If wet && ESSBNodes.Br(akCtl, 8, 0, 1, 0) ; @node 水壓
		akCtl.AddStackTo(akTarget, 9, 1)
	EndIf
	; 5.11 持續專精分支「洗淨」／大師分支「淨化」：命中時清除自身負面，每 3 秒一次。
	If ESSBNodes.Br(akCtl, 8, 0, 2, 0) && akCtl.TakeCleanse() ; @node 洗淨
		akCtl.ApplyCleanse(ESSBNodes.Br(akCtl, 8, 0, 3, 1)) ; @node 淨化
	EndIf
EndFunction

; v0.3 的「蝕魔」「衰弱」「腐朽」（暗的持續分支）v0.4 已移除；命中只剩詛咒本身的抗性侵蝕。
Function OnDarkHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 抗性侵蝕是詛咒狀態本身的效果（基礎 -2%／層，主線把它推到 -5%），一次命中一次狀態查詢。
	Int curse = akCtl.GetStack(akTarget, 10)
	If curse <= 0
		Return
	EndIf
	; 5.12 持續新手主線：詛咒每層抗性侵蝕 -（2% + 0.2%／點）。
	ApplyCurseErosion(akCtl, akTarget, curse)
EndFunction

; 5.12 持續新手主線：詛咒每層抗性侵蝕。四種元素抗 + 魔抗 + 毒抗都吃同一個量，
; 用原型 34（Peak Value Modifier）所以會自己還原；「深淵」允許侵蝕到負值（AV 本來就可負）。
Function ApplyCurseErosion(ESSBController akCtl, Actor akTarget, Int aiCurse) Global
	Float per = 2.0 + 0.2 * ESSBNodes.Rank(akCtl, 9, 0, 0) ; @node 詛咒每層抗性侵蝕
	Float amount = aiCurse * per * ESSBNodes.OmniMult(akCtl)
	If amount <= 0.0
		Return
	EndIf
	akCtl.ApplyUtil(13, amount, 8, akTarget)
	akCtl.ApplyUtil(14, amount, 8, akTarget)
	akCtl.ApplyUtil(15, amount, 8, akTarget)
	akCtl.ApplyUtil(16, amount, 8, akTarget)
	akCtl.ApplyUtil(24, amount, 8, akTarget)
	If akCtl.CachedDebugLevel >= 3
		akCtl.LogThrottled(3, "node", "dark erosion " + akTarget.GetFormID() + " amount=" + amount)
	EndIf
EndFunction

; ================================================================== 開印

Function OnOpen(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult = 1.0) Global
	If aiElement == 8
		OpenPoison(akCtl, akTarget, afMult)
	ElseIf aiElement == 9
		OpenWater(akCtl, akTarget)
	ElseIf aiElement == 10
		OpenDark(akCtl, akTarget)
	ElseIf aiElement == 11
		OpenAstral(akCtl, akTarget)
	EndIf
EndFunction

Function OpenPoison(ESSBController akCtl, Actor akTarget, Float afMult = 1.0) Global
	Actor player = akCtl.ThePlayer()
	; 5.10 開啟新手分支「毒濺」：開印時附近 1 人中毒 2 劑（v0.3 毒層）。
	If ESSBNodes.Br(akCtl, 7, 1, 0, 0) ; @node 毒濺
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 7, ESSBElem.RoundStochastic(2.0 * afMult))
		EndIf
	EndIf
	; 5.10 開啟熟練分支「毒膜」：開印時你毒抗 +50% 5 秒。
	If ESSBNodes.Br(akCtl, 7, 1, 1, 1) && player ; @node 毒膜
		akCtl.ApplyUtil(23, 50.0, 5, player)
	EndIf
	; 5.10 開啟大師分支「腐蝕開印」：開印目標毒抗 -10%。
	If ESSBNodes.Br(akCtl, 7, 1, 3, 0) ; @node 腐蝕開印
		akCtl.ApplyUtil(24, 10.0, 8, akTarget)
	EndIf
	; 5.10 開啟大師分支「毒血」：開印時你回血 B_max ×0.5。
	If ESSBNodes.Br(akCtl, 7, 1, 3, 1) && player ; @node 毒血
		akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 8) * 0.5, 0, player)
	EndIf
	; 5.10 開啟傳奇分支「劇毒之始」：同調三段時開印劑數 ×2（再補一份等量）。
	If ESSBNodes.Br(akCtl, 7, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 劇毒之始
		akCtl.AddStackTo(akTarget, 7, ESSBElem.RoundStochastic(OpenStacks(akCtl, 8) * afMult))
	EndIf
EndFunction

Function OpenWater(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.11 開啟新手分支「廣佈」：開印時浸濕擴散到附近 1 人（浸濕的減速與時長同開印的浸濕）。
	If ESSBNodes.Br(akCtl, 8, 1, 0, 0) ; @node 廣佈
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 8, 1)
			akCtl.ApplyUtil(0, WetSlow(akCtl), WetSeconds(akCtl), nearby[0])
		EndIf
	EndIf
	; 5.11 開啟熟練分支「湧泉」：開印時回復耐力 80。
	If ESSBNodes.Br(akCtl, 8, 1, 1, 1) && player ; @node 湧泉
		akCtl.ApplyUtil(6, akCtl.WaterOpenStamina.GetValue(), 0, player)
	EndIf
	; 5.11 開啟大師分支「開印沖刷」：開印額外驅散目標一個有時限的增益，每目標每 10 秒一次。
	If ESSBNodes.Br(akCtl, 8, 1, 3, 0) ; @node 開印沖刷
		akCtl.ApplyStrip(akTarget)
	EndIf
	; 5.11 開啟傳奇分支「汪洋之始」：同調三段時開印的浸濕不會過期，直到被切掉。
	If ESSBNodes.Br(akCtl, 8, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 汪洋之始
		akCtl.SetWetLock(akTarget)
	EndIf
EndFunction

; v0.4 暗的開啟路線圍繞幻覺階梯（DLL N3）：「夢魘」（目標恐懼時附近詛咒 +1）、「迷亂」（瘋狂中被命中詛咒 +2）、
; 「群魔」（達瘋狂門檻時範圍瘋狂）都要等幻覺階梯；v0.3 的「開印恐懼」「開印沉默」與已退役的「瘋狂」已拿掉。
Function OpenDark(ESSBController akCtl, Actor akTarget) Global
	; 5.12 開啟熟練分支「幻影」：開印後 3 秒目標對你的命中率 -30%
	; （引擎沒有命中率修正，以攻擊 -30% 表達，見實作紀錄）。
	If ESSBNodes.Br(akCtl, 9, 1, 1, 1) ; @node 幻影
		akCtl.ApplyUtil(17, 30.0, 3, akTarget)
	EndIf
	; 5.12 開啟大師分支「暗染」：開印時附近 1 人也詛咒。
	If ESSBNodes.Br(akCtl, 9, 1, 3, 1) ; @node 暗染
		Actor[] spread = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If spread[0]
			akCtl.AddStackTo(spread[0], 10, 2)
			akCtl.ApplyMark(spread[0], 10)
		EndIf
	EndIf
EndFunction

Function OpenAstral(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.13 開啟新手分支「星散」：開印時附近 1 人（15 公尺內）也星痕。
	If ESSBNodes.Br(akCtl, 10, 1, 0, 0) ; @node 星散
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 11, 1)
			akCtl.ApplyMark(nearby[0], 11)
		EndIf
	EndIf
	; 5.13 開啟大師分支「星鎖」：開印目標 3 秒內受所有元素傷 +10%。
	If ESSBNodes.Br(akCtl, 10, 1, 3, 0) ; @node 星鎖
		akCtl.SetStarLock(akTarget, 3)
	EndIf
	; 5.13 開啟傳奇分支「星耀」：同調三段時開印的延遲星傷改為立即並 ×2。
	If ESSBNodes.Br(akCtl, 10, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 星耀
		akCtl.DetonateAstralNow(akTarget, 2.0)
	EndIf
	; v0.3 的「星引力」「星光」（開啟分支）v0.4 已移除。
EndFunction

; 浸濕的減速（v0.4 2.6 水的開印：減速 15%，ESSB_WaterWetSlowPct）。v0.3 的「開啟新手主線：浸濕減速 +1%／點」
; 在 v0.4 是「開印時回復生命與耐力」（DLL N3），已拿掉。
Float Function WetSlow(ESSBController akCtl) Global
	Return akCtl.WaterWetSlowPct.GetValue()
EndFunction

; 5.11 持續新手主線：浸濕持續 10 秒 +0.3 秒／點（只延長浸濕本身，不影響水印記時長）。
; 雨雪、站在水中時 DLL 對所有敵人施放的浸濕，時長用同一個公式（固定時長法術挑一顆，指揮官裁定 R6）。
Int Function WetSeconds(ESSBController akCtl) Global
	Float seconds = 10.0 + 0.3 * ESSBNodes.Rank(akCtl, 8, 0, 0) ; @node 浸濕持續
	Return (seconds + 0.5) as Int
EndFunction

; ================================================================== 開形態（各元素的「臨」的附加效果）

Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	If aiElement == 8
		; 5.10 開啟專精分支「毒臨強化」：毒臨時範圍內敵人中毒 3 劑（v0.3 毒層）。
		If ESSBNodes.Br(akCtl, 7, 1, 2, 0) ; @node 毒臨強化
			Actor[] nearby = akCtl.ScanTargets(player, ESSBElem.AdventRadiusOf(akCtl, 8), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 7, 3)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 9
		; 5.11 開啟專精分支「水臨強化」：水臨時範圍內敵人浸濕（浸濕的減速與時長），你立即清除全部負面效果
		; 並回滿魔力（開場就是滿的水幕）。範圍掃描 N5 前由這裡做。
		If ESSBNodes.Br(akCtl, 8, 1, 2, 0) ; @node 水臨強化
			Actor[] nearby = akCtl.ScanTargets(player, ESSBElem.AdventRadiusOf(akCtl, 9), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 8, 1)
					akCtl.ApplyUtil(0, WetSlow(akCtl), WetSeconds(akCtl), nearby[index])
				EndIf
				index += 1
			EndWhile
			akCtl.ApplyCleanse(True)
			akCtl.ApplyUtil(5, player.GetActorValueMax("Magicka"), 0, player, True)
		EndIf
	ElseIf aiElement == 10
		; 5.12 開啟專精分支「暗臨強化」：暗臨時範圍內敵人恐懼 2 秒。
		If ESSBNodes.Br(akCtl, 9, 1, 2, 0) ; @node 暗臨強化
			Actor[] nearby = akCtl.ScanTargets(player, ESSBElem.AdventRadiusOf(akCtl, 10), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.ApplyFear(nearby[index], 2)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 11
		; 5.13 開啟專精分支「星臨強化」：星臨時範圍內敵人星痕 2 層。
		If ESSBNodes.Br(akCtl, 10, 1, 2, 0) ; @node 星臨強化
			Actor[] nearby = akCtl.ScanTargets(player, AdventRadius(akCtl), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 11, 2)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
EndFunction

; ================================================================== 毒：催毒與擴散（規劃 2.3、2.6）

; 5.10 關閉熟練分支「延毒」：催毒時剩餘時長 +4 秒（v0.3 的催毒 8 → 12 秒）。
; v0.4 的「毒斷」是融斷的催毒改為強度 ×4（DLL N5），v0.3 的「融斷催毒時間 ×2」已拿掉。
Int Function CatalyzeSeconds(ESSBController akCtl, Int aiReason) Global
	If ESSBNodes.Br(akCtl, 7, 2, 1, 0) ; @node 延毒
		Return 12
	EndIf
	Return 8
EndFunction

; 催毒期間的每秒跳動倍率：基礎 2（每秒兩次），關閉新手分支「潰爛」改為 3。
Float Function CatalyzeRate(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 7, 2, 0, 0) ; @node 潰爛
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 毒層每秒傷害的節點倍率：持續新手主線「每劑傷害 +2%／點」，催毒期間再 +3%／點（關閉傳奇主線）。
Float Function PoisonTickMult(ESSBController akCtl, Bool abCatalyzed) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 0, 0), 0.02) ; @node 每劑傷害
	If abCatalyzed
		mult = mult * (1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 2, 4), 0.03)) ; @node 催毒期間中毒傷害
	EndIf
	Return mult
EndFunction

; 毒的基礎擴散（v0.3 毒層，N3 前）：每 2 秒向附近一名敵人傳 1 層。v0.4 的持續專精主線是瘴氣披風的每秒劑量
; （劑數併入待決，見規劃 10.4），v0.3 的「擴散間隔 -0.1 秒／點」已拿掉。
Int Function SpreadInterval(ESSBController akCtl) Global
	Return 2
EndFunction

Int Function SpreadTargets(ESSBController akCtl) Global
	Return 1
EndFunction

; 5.10 持續專精分支「傳染門檻」：擴散門檻 5 劑 → 1 劑（v0.3 毒層）。
Int Function SpreadThreshold(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 7, 0, 2, 1) ; @node 傳染門檻
		Return 1
	EndIf
	Return 5
EndFunction

; 5.10 持續傳奇主線「瘟疫」：同調三段時毒層每秒自動擴散到附近敵人，機率 5%／點。
; 由 ESSBStatus 的每秒 tick 呼叫（每個帶毒目標一次，不做全場掃描）。
Function PoisonTickHook(ESSBController akCtl, Actor akTarget, Int aiPoison, Int aiKillingElement = 0) Global
	Int rank = ESSBNodes.Rank(akCtl, 7, 0, 4) ; @node 瘟疫
	If rank <= 0 || akCtl.SyncStage() < 3
		Return
	EndIf
	If Utility.RandomFloat(0.0, 1.0) < 0.05 * rank
		akCtl.SpreadPoison(akTarget, 1)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "node", "poison plague " + akTarget.GetFormID())
		EndIf
	EndIf
EndFunction

; 5.10 關閉大師分支「劇毒」：催毒期間目標毒抗視為 0。
; 引擎沒有「視為 0」，所以下一個等量於目標當前毒抗的削減（同碎冰的碎甲做法）。
Function ApplyVirulence(ESSBController akCtl, Actor akTarget, Int aiSeconds) Global
	If !ESSBNodes.Br(akCtl, 7, 2, 3, 0) || !akTarget ; @node 劇毒
		Return
	EndIf
	Float resist = akTarget.GetActorValue("PoisonResist")
	If resist > 0.0
		akCtl.ApplyUtil(24, resist, aiSeconds, akTarget)
	EndIf
EndFunction

; ================================================================== 水：長流與導引

; 5.11 持續熟練主線：長流每秒回復 2.0% +0.2%／點；
; 持續大師主線：同調每段 +0.05%／點；傳奇主線「長河」：同調三段時再 +0.05%／點。
Float Function FlowPercent(ESSBController akCtl) Global
	Float percent = (akCtl.WaterFlowBasePct.GetValue() + akCtl.WaterFlowPerRankPct.GetValue() * ESSBNodes.Rank(akCtl, 8, 0, 1)) * 0.01 ; @node 長流每秒回復
	percent = percent + 0.0005 * ESSBNodes.Rank(akCtl, 8, 0, 3) * akCtl.SyncStage() ; @node 同調每段長流回復
	If akCtl.SyncStage() >= 3
		percent = percent + 0.0005 * ESSBNodes.Rank(akCtl, 8, 0, 4) ; @node 長河
	EndIf
	Return percent
EndFunction

; 5.11 關閉新手分支「強引」：導引 ×1.5 → ×2.0；關閉傳奇主線：導引 +3%／點。
Float Function GuideMult(ESSBController akCtl) Global
	Float mult = 1.5
	If ESSBNodes.Br(akCtl, 8, 2, 0, 0) ; @node 強引
		mult = 2.0
	EndIf
	Return mult * ESSBElem.SignatureMult(akCtl, 9)
EndFunction

; 導引給接管元素的同調（v0.3 基礎 +5）。v0.3 的「潮引」（+10）v0.4 已移除。
Int Function GuideSync(ESSBController akCtl) Global
	Return 5
EndFunction

; ================================================================== 暗：死咒周邊

; 5.12 關閉專精主線：死咒的「已損失生命」係數 15% +0.5%／點。
Float Function DeathCurseLostRatio(ESSBController akCtl) Global
	Return 0.15 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 2, 2), 0.005) ; @node 死咒的「已損失生命」係數
EndFunction

; 死咒期間目標無法被治療（規劃 2.6）：3 秒，關閉熟練分支「不治」延長到 6 秒。
; 引擎沒有「受到的治療」修正，以 HealRateMult -100% 表達（同血咒的偏離，見實作紀錄）。
Int Function DeathCurseSeconds(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 9, 2, 1, 0) ; @node 不治
		Return 6
	EndIf
	Return 3
EndFunction

; 死咒結算之後（由 ESSBStatus 在傷害套用完的那一秒呼叫）。
Function AfterDeathCurse(ESSBController akCtl, Actor akTarget, Float afAmount) Global
	Actor player = akCtl.ThePlayer()
	If !akTarget || !player
		Return
	EndIf
	; 5.12 關閉新手分支「饕餮」：死咒結算時吸血吸魔各 B_max ×1.0。
	If ESSBNodes.Br(akCtl, 9, 2, 0, 0) ; @node 饕餮
		Float gain = ESSBReactions.BaseMax(akCtl, 10)
		akCtl.ApplyUtil(4, gain, 0, player)
		akCtl.ApplyUtil(5, gain, 0, player)
	EndIf
	; v0.3 的「處刑」（死咒結算時低血直接死亡）v0.4 已移除：處決只有冰一家（v0.4 相對 v0.3 的差異）。
EndFunction

; 恐懼與瘋狂的等級上限（同原版幻術：magnitude 就是可影響的最高等級）。
; 基礎 10 級，暗樹每級 +1，所以 100 級的暗樹可影響 110 級以下的目標。
Int Function CharmCap(ESSBController akCtl) Global
	Int level = 1
	If akCtl.Trees
		level = akCtl.Trees.TreeLevel(9)
	EndIf
	Return 10 + level
EndFunction

; ================================================================== 暗：亡者歸來（規劃 5.12 表 + 8）
; v0.4 的亡者歸來是基礎死亡機制（死時帶黑暗印記且詛咒 ≥3 就復生，DLL N5＋Papyrus）；v0.3 的「亡者歸來」
; 「亡者強化」分支已退役、「死靈主」改版（N5）。復生本身等 N5 接上，下面三個函式是 v0.4 的等級對照表，
; 與 ESSBController.ApplyReanimate／CanReanimate 一起留給 N5。

; 六階的等級上限：≤6／≤13／≤21／≤30／≤60／任意（第六階只有「死靈主」才有）。
Int Function ReanimateTier(Int aiLevel) Global
	If aiLevel <= 6
		Return 1
	ElseIf aiLevel <= 13
		Return 2
	ElseIf aiLevel <= 21
		Return 3
	ElseIf aiLevel <= 30
		Return 4
	ElseIf aiLevel <= 60
		Return 5
	EndIf
	Return 6
EndFunction

Int Function ReanimateCapOf(Int aiTier) Global
	If aiTier == 1
		Return 6
	ElseIf aiTier == 2
		Return 13
	ElseIf aiTier == 3
		Return 21
	ElseIf aiTier == 4
		Return 30
	ElseIf aiTier == 5
		Return 60
	EndIf
	; 第六階：同原版亡魂奴僕（200 級）＝等於無上限。
	Return 999
EndFunction

Int Function ReanimateSeconds(Int aiTier) Global
	If aiTier <= 3
		Return 120
	ElseIf aiTier <= 5
		Return 180
	EndIf
	; 第六階永久：同原版 DeathThrall 的 86313600 秒。
	Return 86313600
EndFunction

; ================================================================== 星：星落與引爆

; 5.13 關閉新手分支「隕星」：星落 ×2.0 → ×3.0。
Float Function FallK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 10, 2, 0, 0) ; @node 隕星
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 5.13 關閉熟練分支「星斷」：星印記融斷改為真實傷害，倍率 ×0.6。
Bool Function HasTrueBurst(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 10, 2, 1, 1) ; @node 星斷
EndFunction

; 星痕引爆的延遲：環狀桶是 2 格（2 秒）。開啟新手主線「星痕延遲 -0.1 秒／點」
; 在 10 點以上縮成 1 秒（整數秒 tick 只有這兩檔）。
Int Function AstralDelay(ESSBController akCtl) Global
	If ESSBNodes.Rank(akCtl, 10, 1, 0) >= 10 ; @node 星痕延遲
		Return 1
	EndIf
	Return 2
EndFunction

; 星落本體（規劃 2.6 的終焉）：B_max ×2.0 星傷；星斷改為真實傷害 ×0.6。
; v0.3 的「流星雨」（星落改範圍）與「群星」（星落連鎖）v0.4 已移除／改版（持續傳奇主線是永夜，DLL N4）。
Function Fall(ESSBController akCtl, Actor akTarget, Float afMult, Int aiReason) Global
	Float amount = ESSBReactions.ReactDamage(akCtl, 11, FallK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 11)
	FallHit(akCtl, akTarget, amount, aiReason)
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "astral fall " + akTarget.GetFormID() + " amount=" + amount)
	EndIf
EndFunction

Function FallHit(ESSBController akCtl, Actor akTarget, Float amount, Int aiReason) Global
	If aiReason == 1 && HasTrueBurst(akCtl)
		; 星斷：融斷改為真實傷害（不吃護甲與抗性），倍率 ×0.6。
		akCtl.ApplyTrueDamage(amount * 0.6, akTarget, 10)
	Else
		akCtl.ApplyDamage(11, amount, akTarget)
	EndIf
EndFunction

; Both delayed astral stacks and radiance retain weighted opening damage.
; v0.4 的持續新手主線是「回聲比例」（DLL N5），v0.3 的「星痕延遲傷害 +2%／點」已拿掉；
; v0.3 引爆時的「星盾」「星體」分支 v0.4 已移除。
Function DetonateAstral(ESSBController akCtl, Actor akTarget, Int aiLayers, Float afWeight, Float afMult = 1.0) Global
	If aiLayers <= 0 || afWeight <= 0.0
		Return
	EndIf
	Float amount = ESSBReactions.ReactDamage(akCtl, 11, 1.0) * afWeight * afMult * ESSBNodes.OmniMult(akCtl)
	akCtl.ApplyDamage(11, amount, akTarget)
EndFunction

; ================================================================== 終焉掛勾

Function OnEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult) Global
	If aiElement == 8
		EndPoisonNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 9
		EndWaterNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 10
		EndDarkNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 11
		EndAstralNodes(akCtl, akTarget, aiReason, afMult)
	EndIf
EndFunction

Function EndPoisonNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.10 關閉大師分支「劇毒」：催毒期間目標毒抗視為 0。
	ApplyVirulence(akCtl, akTarget, CatalyzeSeconds(akCtl, aiReason))
	; 5.10 關閉大師分支「腐蝕終焉」：毒終焉後目標魔抗 -20% 8 秒。
	If ESSBNodes.Br(akCtl, 7, 2, 3, 1) ; @node 腐蝕終焉
		akCtl.ApplyUtil(16, 20.0, 8, akTarget)
	EndIf
	; 5.10 關閉熟練分支「疫染」：毒終焉時把目標的中毒（v0.3 毒層，同層數）複製到 6 公尺內敵人（規劃 2.9 例外表：5 人）。
	If ESSBNodes.Br(akCtl, 7, 2, 1, 1) ; @node 疫染
		Int layers = akCtl.GetStack(akTarget, 7)
		If layers > 0
			Actor[] nearby = akCtl.ScanTargets(akTarget, 420.0, 5, akTarget)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 7, layers)
				EndIf
				index += 1
			EndWhile
			If akCtl.CachedDebugLevel >= 1
				akCtl.LogThrottled(1, "node", "poison miasma " + akTarget.GetFormID() + " layers=" + layers)
			EndIf
		EndIf
	EndIf
	; 5.10 關閉傳奇分支「毒霧」：毒印記融斷後留下 5 秒毒霧，內部每秒 +1 毒層（劑數併入待決，見規劃 10.4）。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 7, 2, 4, 0) ; @node 毒霧
		akCtl.StartDomain(8, akTarget, 5)
	EndIf
EndFunction

Function EndWaterNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 5.11 關閉大師分支「大潮」：水終焉時範圍內所有浸濕目標都給接管元素導引。
	If ESSBNodes.Br(akCtl, 8, 2, 3, 0) ; @node 大潮
		Actor[] nearby = akCtl.ScanTargets(akTarget, 350.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.IsWet(nearby[index])
				akCtl.SetNextEndMultOn(nearby[index], GuideMult(akCtl) * afMult)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.11 關閉大師分支「洗滌」：水終焉清除你所有負面效果，並驅散目標一個有時限的增益。
	If ESSBNodes.Br(akCtl, 8, 2, 3, 1) ; @node 洗滌
		akCtl.ApplyCleanse(True)
		akCtl.ApplyStrip(akTarget)
	EndIf
	; v0.4 的「汪洋」是水終焉時目標浸濕延長到 30 秒（浸濕是 DLL N3），v0.3 的「保留為副印記 10 秒」已拿掉。
	If aiReason != 1
		Return
	EndIf
	; 5.11 關閉熟練分支「水斷」：水印記融斷改為治療你並回復耐力。
	If ESSBNodes.Br(akCtl, 8, 2, 1, 1) && player ; @node 水斷
		; 治療量＝這個水印記原本的融斷量：v0.4 2.7 D_burst = B_max × K_sync × G(L_水) × M_mod（afMult 帶 K_sync；
		; ReactDamage 不含 G，G 由 ApplyDamage 乘，這裡不走 ApplyDamage，所以自己乘一次）。v0.3 的額外 ×2.0 沒有 v0.4 依據，拿掉。
		Float amount = ESSBReactions.ReactDamage(akCtl, 9, 1.0) * afMult * akCtl.GLevel(8)
		akCtl.ApplyUtil(4, amount, 0, player)
		akCtl.ApplyUtil(6, amount, 0, player)
	EndIf
	; 5.11 關閉傳奇分支「潮池」：水印記融斷後留下 5 秒水域（內部效果在 ESSBController.TickDomain）。
	If ESSBNodes.Br(akCtl, 8, 2, 4, 0) ; @node 潮池
		akCtl.StartDomain(9, akTarget, 5)
	EndIf
EndFunction

; v0.3 的「蝕魔終焉」分支 v0.4 已移除。
Function EndDarkNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 5.12 關閉大師分支「深淵回響」：暗終焉回滿你的魔力。
	If ESSBNodes.Br(akCtl, 9, 2, 3, 1) && player ; @node 深淵回響
		akCtl.ApplyUtil(5, player.GetActorValueMax("Magicka"), 0, player)
	EndIf
	; 5.12 關閉傳奇分支「死域」：暗印記融斷後留下 5 秒死域。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 9, 2, 4, 0) ; @node 死域
		akCtl.StartDomain(10, akTarget, 5)
	EndIf
EndFunction

; v0.3 的「星引」「星界之門」（關閉分支）與「群星」（持續傳奇主線）v0.4 已移除／改版。
Function EndAstralNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.13 關閉傳奇分支「星域」：星印記融斷後留下 5 秒星域（3 公尺），內部敵人受所有元素傷 +20%。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 10, 2, 4, 0) ; @node 星域
		akCtl.StartDomain(11, akTarget, 5, 210.0)
	EndIf
EndFunction

; 星終焉後接管元素的開印倍率（規劃 2.6 的基礎星落 ×1.5）。v0.3 的「星軌終焉」（×2.0）v0.4 已移除。
Float Function TakeoverOpenMult(ESSBController akCtl) Global
	Return 1.5
EndFunction

; ================================================================== 每秒與擊殺

Function OnTick(ESSBController akCtl, Int aiElement) Global
	If aiElement == 8
		PoisonFormTick(akCtl)
	ElseIf aiElement == 9
		WaterFormTick(akCtl)
	EndIf
EndFunction

Function PoisonFormTick(ESSBController akCtl) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 5.10 持續大師分支「以毒攻毒」：你中毒時生命回復 +20%。
	If ESSBNodes.Br(akCtl, 7, 0, 3, 1) && akCtl.IsPoisoned(player) ; @node 以毒攻毒
		akCtl.ApplyUtil(25, 20.0, 3, player)
	EndIf
	; 5.10 持續傳奇分支「百毒不侵」：同調三段時免疫中毒與疾病，
	; 且附近中毒敵人每秒替你回血。
	If !ESSBNodes.Br(akCtl, 7, 0, 4, 0) || akCtl.SyncStage() < 3 ; @node 百毒不侵
		Return
	EndIf
	akCtl.ApplyUtil(23, 100.0, 3, player)
	akCtl.ApplyUtil(26, 100.0, 3, player)
	Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
	Float heal = 0.0
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.GetStack(nearby[index], 7) > 0
			heal = heal + 6.0
		EndIf
		index += 1
	EndWhile
	If heal > 0.0
		akCtl.ApplyUtil(4, heal, 0, player)
	EndIf
EndFunction

; 5.11 持續熟練／大師／傳奇主線「長流」：每秒回復最大生命與最大耐力的百分比。
; 規劃 8：自有效果的每秒回復，不動回復速率 AV，所以不受戰鬥中回復減半影響。
Function WaterFormTick(ESSBController akCtl) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float percent = FlowPercent(akCtl)
	If percent <= 0.0
		Return
	EndIf
	Float health = player.GetActorValueMax("Health") * percent
	Float stamina = player.GetActorValueMax("Stamina") * percent
	akCtl.ApplyUtil(4, health, 0, player)
	akCtl.ApplyUtil(6, stamina, 0, player)
	; 5.11 持續傳奇主線「長河」：同調三段時長流同時作用於附近同伴。
	If ESSBNodes.Rank(akCtl, 8, 0, 4) <= 0 || akCtl.SyncStage() < 3 ; @node 長河
		Return
	EndIf
	Actor[] allies = akCtl.ScanAllies(420.0)
	Int index = 0
	While index < allies.Length
		If allies[index]
			akCtl.ApplyUtil(4, allies[index].GetActorValueMax("Health") * percent, 0, allies[index])
			akCtl.ApplyUtil(6, allies[index].GetActorValueMax("Stamina") * percent, 0, allies[index])
		EndIf
		index += 1
	EndWhile
EndFunction


; ================================================================== 常駐能力與守衛
; v0.3 的擊殺掛勾（蔓延、收割、亡者歸來）v0.4 都改成死亡處理（DLL N5）或已移除；星的「星輝」、暗的「影身」已退役。

; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%（自有常駐能力，開形態才掛）。
Bool Function HasPoisonImmunity(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 7, 0, 0, 0) ; @node 免疫
EndFunction

; 5.10 持續熟練分支「毒皮」：被近戰命中時攻擊者中毒 +2 劑（v0.3 毒層）。由 ESSBGuard 呼叫。
Function OnPoisonSkin(ESSBController akCtl, Actor akAttacker) Global
	If !ESSBNodes.Br(akCtl, 7, 0, 1, 1) || !akAttacker ; @node 毒皮
		Return
	EndIf
	akCtl.AddStackTo(akAttacker, 7, 2)
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "poison skin " + akAttacker.GetFormID())
	EndIf
EndFunction

Function OnDeathSoul(ESSBController akCtl, Actor akTarget) Global
	; 5.12 關閉專精分支「亡魂」：死咒殺死目標時附近敵人恐懼 2 秒。
	If ESSBNodes.Br(akCtl, 9, 2, 2, 0) ; @node 亡魂
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.ApplyFear(nearby[index], 2)
			EndIf
			index += 1
		EndWhile
	EndIf
EndFunction
