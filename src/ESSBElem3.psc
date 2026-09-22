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
      亡者歸來是自有 Reanimate（原型 22）六階表，尊重召喚上限與化灰互斥。
  星（2.9／2.10）所有範圍的主線成長是每點 +1 公尺（其他元素 +0.2），夜晚再 ×1.5，
      一律走 Range() 一個函式，人數上限仍是 5。

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
	Int rank = ESSBNodes.Rank(akCtl, 9, 0, 4)
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
	Return 3 + ESSBNodes.Rank(akCtl, 10, 0, 2) / 5 + ESSBNodes.StatusCapBonus(akCtl)
EndFunction

; ================================================================== 範圍（規劃 2.9 例外表 + 2.10）

; 星界的所有範圍：基礎與其他元素相同，主線每點 +1 公尺（其他元素 +0.2），
; 夜晚再 ×1.5（規劃 2.10）。回傳遊戲單位（1 公尺 = 70 單位）。
Float Function Range(ESSBController akCtl, Float afBaseMetres, Float afPerPoint, Int aiRank) Global
	Float metres = afBaseMetres + afPerPoint * aiRank
	If akCtl.IsEnvNight()
		metres = metres * 1.5
	EndIf
	Return metres * 70.0
EndFunction

; 星臨（5.13 開啟大師主線）：2 公尺 +1 公尺／點。
Float Function AdventRadius(ESSBController akCtl) Global
	Return Range(akCtl, 2.0, 1.0, ESSBNodes.Rank(akCtl, 10, 1, 3))
EndFunction

; 星落與星域（5.13 關閉專精主線）：3 公尺 +0.8 公尺／點。
Float Function FallRadius(ESSBController akCtl) Global
	Return Range(akCtl, 3.0, 0.8, ESSBNodes.Rank(akCtl, 10, 2, 2))
EndFunction

; 群星（5.13 持續傳奇主線）：1 公尺 +1 公尺／點。
Float Function ConstellationRadius(ESSBController akCtl) Global
	Return Range(akCtl, 1.0, 1.0, ESSBNodes.Rank(akCtl, 10, 0, 4))
EndFunction

; 星散（5.13 開啟新手分支）：搜尋範圍 15 公尺，隨星臨主線每點 +1 公尺。
Float Function ScatterRadius(ESSBController akCtl) Global
	Return Range(akCtl, 15.0, 1.0, ESSBNodes.Rank(akCtl, 10, 1, 3))
EndFunction

; ================================================================== 附傷倍率

Float Function HitMult(ESSBController akCtl, Int aiElement, Actor akTarget, Bool abPower) Global
	If aiElement == 8
		Return PoisonHitMult(akCtl, akTarget, abPower)
	ElseIf aiElement == 9
		Return WaterHitMult(akCtl, akTarget, abPower)
	ElseIf aiElement == 10
		Return DarkHitMult(akCtl, akTarget, abPower)
	ElseIf aiElement == 11
		Return AstralHitMult(akCtl, akTarget, abPower)
	EndIf
	Return 1.0
EndFunction

; 5.10：毒附傷 +1%／點、同調每段 +1%／點、開印後 5 秒內 +1%／點。
Float Function PoisonHitMult(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 0, 1), 0.01)
	mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 0, 3), 0.01) * akCtl.SyncStage()
	If akCtl.GetOpenBoost(8) > 0
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 1, 1), 0.01)
	EndIf
	Return mult
EndFunction

; 5.11：水附傷 +1%／點、同調每段 +1%／點、開印後 5 秒內 +1%／點、
; 水壓每層 +（10% + 1%／點）（「水壓」分支才會有層數）。
Float Function WaterHitMult(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float mult = 1.0
	If akCtl.GetOpenBoost(9) > 0
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 8, 1, 1), 0.01)
	EndIf
	; 水壓層數只有「水壓」分支才會產生，沒投點就不查狀態容器（命中路徑）。
	If ESSBNodes.Br(akCtl, 8, 0, 1, 0)
		Int pressure = akCtl.GetStack(akTarget, 9)
		If pressure > 0
			Float perLayer = 0.1 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 8, 0, 2), 0.01)
			mult = mult + pressure * perLayer * ESSBNodes.OmniMult(akCtl)
		EndIf
	EndIf
	Return mult
EndFunction

; 5.12：暗附傷 +1%／點、同調每段 +1%／點、開印後 5 秒內 +1%／點、
; 虛空（對魔力低於 25% 的施法者 ×1.5）。
Float Function DarkHitMult(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 0, 1), 0.01)
	mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 0, 3), 0.01) * akCtl.SyncStage()
	If akCtl.GetOpenBoost(10) > 0
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 1, 1), 0.01)
	EndIf
	If ESSBNodes.Br(akCtl, 9, 0, 3, 0) && akTarget && ESSBNoForm.IsSpellUser(akCtl, akTarget) \
		&& akTarget.GetActorValuePercentage("Magicka") < 0.25
		mult = mult * 1.5
	EndIf
	Return mult
EndFunction

; 5.13：星附傷 +1%／點、同調每段 +1%／點、開印後 5 秒內 +1%／點、
; 星痕弱點（重擊時每層星痕 +8%）。
Float Function AstralHitMult(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 10, 0, 1), 0.01)
	mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 10, 0, 3), 0.01) * akCtl.SyncStage()
	If akCtl.GetOpenBoost(11) > 0
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 10, 1, 1), 0.01)
	EndIf
	If abPower && ESSBNodes.Br(akCtl, 10, 0, 2, 0)
		mult = mult + 0.08 * akCtl.GetStack(akTarget, 11) * ESSBNodes.OmniMult(akCtl)
	EndIf
	Return mult
EndFunction

; 5.12 持續專精主線「詛咒滿層目標受所有傷害 +1%／點」與
; 5.13 開啟大師分支「星鎖」（開印目標 3 秒內受所有元素傷 +10%）。
; 決定 61：攻擊類進入點讀不到目標，所以這兩條只放大本模組造成的傷害。
Float Function TargetDamageMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If !akTarget
		Return mult
	EndIf
	; 三個查詢都先看節點有沒有投點，沒投就完全不碰狀態容器（這是命中路徑，見效能守則）。
	Int rank = ESSBNodes.Rank(akCtl, 9, 0, 2)
	If rank > 0 && akCtl.GetStack(akTarget, 10) >= CurseCap(akCtl)
		mult = mult * (1.0 + ESSBNodes.Pct(akCtl, rank, 0.01))
	EndIf
	If ESSBNodes.Br(akCtl, 10, 1, 3, 0) && akCtl.HasStarLock(akTarget)
		mult = mult * 1.1
	EndIf
	; 5.13 關閉傳奇分支「星域」：內部敵人受所有元素傷 +20%。
	If ESSBNodes.Br(akCtl, 10, 2, 4, 0) && akCtl.InDomain(akTarget, 11)
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
		Return 3 + ESSBNodes.Rank(akCtl, 7, 1, 0) / 3
	ElseIf aiElement == 9
		Return 1
	ElseIf aiElement == 10
		Return 2 + ESSBNodes.Rank(akCtl, 9, 1, 0) / 5
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
	ElseIf aiElement == 11
		OnAstralHit(akCtl, akTarget, abPower)
	EndIf
EndFunction

Function OnPoisonHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	; 兩個分支都沒投就不查狀態容器（命中路徑）。
	If !ESSBNodes.Br(akCtl, 7, 0, 1, 0) && !ESSBNodes.Br(akCtl, 7, 0, 2, 0)
		Return
	EndIf
	Int stacks = akCtl.GetStack(akTarget, 7)
	; 5.10 持續熟練分支「衰弱」：毒層 ≥5 時目標攻擊 -15%。
	If stacks >= 5 && ESSBNodes.Br(akCtl, 7, 0, 1, 0)
		akCtl.ApplyUtil(17, 15.0, 3, akTarget)
	EndIf
	; 5.10 持續專精分支「侵蝕」：毒層 ≥10 時目標毒抗 -20%。
	If stacks >= 10 && ESSBNodes.Br(akCtl, 7, 0, 2, 0)
		akCtl.ApplyUtil(24, 20.0, 6, akTarget)
	EndIf
EndFunction

Function OnWaterHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Actor player = akCtl.ThePlayer()
	; 5.11 持續新手分支「清流」：命中回復耐力 30。
	If ESSBNodes.Br(akCtl, 8, 0, 0, 0) && player
		akCtl.ApplyUtil(6, akCtl.WaterClearStamina.GetValue(), 0, player)
	EndIf
	Bool wet = akCtl.IsWet(akTarget) || akCtl.IsEnvWet()
	; 5.11 持續熟練分支「水壓」：命中浸濕目標 +1 水壓。
	If wet && ESSBNodes.Br(akCtl, 8, 0, 1, 0)
		akCtl.AddStackTo(akTarget, 9, 1)
	EndIf
	; 5.11 開啟大師分支「水牢」：浸濕目標移速 -20%。
	If wet && ESSBNodes.Br(akCtl, 8, 1, 3, 1)
		akCtl.ApplyUtil(0, 20.0, 3, akTarget)
	EndIf
	; 5.11 持續大師分支「水鏡」：每命中 +1 層（最多 3），被打消耗一層抵消 30% 傷害。
	If ESSBNodes.Br(akCtl, 8, 0, 3, 0)
		akCtl.AddWaterMirror(1)
	EndIf
	; 5.11 持續專精分支「洗淨」／大師分支「淨化」：命中時清除自身負面，每 3 秒一次。
	If ESSBNodes.Br(akCtl, 8, 0, 2, 0) && akCtl.TakeCleanse()
		akCtl.ApplyCleanse(ESSBNodes.Br(akCtl, 8, 0, 3, 1))
	EndIf
EndFunction

Function OnDarkHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Actor player = akCtl.ThePlayer()
	; 5.12 持續新手分支「蝕魔」：命中吸魔（基礎 B_max ×0.5，本分支 ×2 ＝ ×1.0）。
	If ESSBNodes.Br(akCtl, 9, 0, 0, 0) && player
		Float drain = 30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)
		akCtl.ApplyUtil(2, drain, 0, akTarget)
		akCtl.ApplyUtil(5, drain, 0, player)
	EndIf
	; 抗性侵蝕是詛咒狀態本身的效果（基礎 -2%／層，主線把它推到 -5%），
	; 所以不像其他分支可以先用投點擋掉；一次命中一次狀態查詢，同血樹的 OnBloodHit。
	Int curse = akCtl.GetStack(akTarget, 10)
	If curse <= 0
		Return
	EndIf
	; 5.12 持續新手主線：詛咒每層抗性侵蝕 -（2% + 0.2%／點）。
	ApplyCurseErosion(akCtl, akTarget, curse)
	; 5.12 持續熟練分支「衰弱」：詛咒目標攻擊 -10%。
	If ESSBNodes.Br(akCtl, 9, 0, 1, 0)
		akCtl.ApplyUtil(17, 10.0, 3, akTarget)
	EndIf
	; 5.12 持續專精分支「腐朽」：詛咒目標受治療 -50%（以 HealRateMult 表達，見實作紀錄）。
	If ESSBNodes.Br(akCtl, 9, 0, 2, 0)
		akCtl.ApplyUtil(20, 50.0, 8, akTarget)
	EndIf
EndFunction

; 5.12 持續新手主線：詛咒每層抗性侵蝕。四種元素抗 + 魔抗 + 毒抗都吃同一個量，
; 用原型 34（Peak Value Modifier）所以會自己還原；「深淵」允許侵蝕到負值（AV 本來就可負）。
Function ApplyCurseErosion(ESSBController akCtl, Actor akTarget, Int aiCurse) Global
	Float per = 2.0 + 0.2 * ESSBNodes.Rank(akCtl, 9, 0, 0)
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

Function OnAstralHit(ESSBController akCtl, Actor akTarget, Bool abPower) Global
	Actor player = akCtl.ThePlayer()
	; 5.13 持續熟練分支「星軌」：命中回復魔力。
	If ESSBNodes.Br(akCtl, 10, 0, 1, 1) && player
		akCtl.ApplyUtil(5, 25.0 * akCtl.GLevel(10), 0, player)
	EndIf
	; 5.13 持續熟練分支「追擊」：每第 3 次命中額外 35% 星傷。
	If ESSBNodes.Br(akCtl, 10, 0, 1, 0) && akCtl.BumpAstralHits() >= 3
		akCtl.ApplyDamage(11, ESSBReactions.ReactDamage(akCtl, 11, 0.35), akTarget)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "node", "astral pursuit " + akTarget.GetFormID())
		EndIf
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
	; 5.10 開啟新手分支「毒濺」：開印時附近 1 人 +2 毒層。
	If ESSBNodes.Br(akCtl, 7, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 7, ESSBElem.RoundStochastic(2.0 * afMult))
		EndIf
	EndIf
	; 5.10 開啟熟練分支「毒膜」：開印時你毒抗 +50% 5 秒。
	If ESSBNodes.Br(akCtl, 7, 1, 1, 1) && player
		akCtl.ApplyUtil(23, 50.0, 5, player)
	EndIf
	; 5.10 開啟大師分支「腐蝕開印」：開印目標毒抗 -10%。
	If ESSBNodes.Br(akCtl, 7, 1, 3, 0)
		akCtl.ApplyUtil(24, 10.0, 8, akTarget)
	EndIf
	; 5.10 開啟大師分支「毒血」：開印時你回血 B_max ×0.5。
	If ESSBNodes.Br(akCtl, 7, 1, 3, 1) && player
		akCtl.ApplyUtil(4, 25.0 * akCtl.GLevel(7), 0, player)
	EndIf
	; 5.10 開啟傳奇分支「劇毒之始」：同調三段時開印毒層 ×2（再補一份等量）。
	If ESSBNodes.Br(akCtl, 7, 1, 4, 0) && akCtl.SyncStage() >= 3
		akCtl.AddStackTo(akTarget, 7, ESSBElem.RoundStochastic(OpenStacks(akCtl, 8) * afMult))
	EndIf
EndFunction

Function OpenWater(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.11 開啟新手分支「廣佈」：開印時浸濕擴散到附近 1 人。
	If ESSBNodes.Br(akCtl, 8, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 8, 1)
			akCtl.ApplyUtil(0, WetSlow(akCtl), 10, nearby[0])
		EndIf
	EndIf
	; 5.11 開啟熟練分支「回流」：開印時回復耐力 80。
	If ESSBNodes.Br(akCtl, 8, 1, 1, 1) && player
		akCtl.ApplyUtil(6, akCtl.WaterOpenStamina.GetValue(), 0, player)
	EndIf
	; 5.11 開啟大師分支「沖刷」：開印驅散目標一個有時限的增益，每目標每 10 秒一次。
	If ESSBNodes.Br(akCtl, 8, 1, 3, 0)
		akCtl.ApplyStrip(akTarget)
	EndIf
	; 5.11 開啟傳奇分支「汪洋之始」：同調三段時開印的浸濕不會過期，直到被切掉。
	If ESSBNodes.Br(akCtl, 8, 1, 4, 0) && akCtl.SyncStage() >= 3
		akCtl.SetWetLock(akTarget)
	EndIf
EndFunction

Function OpenDark(ESSBController akCtl, Actor akTarget) Global
	; 5.12 開啟新手分支「夢魘」：開印施加恐懼 1.5 秒（整數秒 tick，取 2 秒，見實作紀錄）。
	If ESSBNodes.Br(akCtl, 9, 1, 0, 0)
		akCtl.ApplyFear(akTarget, 2)
	EndIf
	; 5.12 開啟熟練分支「瘋狂」：開印使目標 3 秒內攻擊最近的任何人。
	If ESSBNodes.Br(akCtl, 9, 1, 1, 0)
		akCtl.ApplyFrenzy(akTarget, 3)
		; 5.12 開啟傳奇分支「群魔」：同調三段時瘋狂改為範圍。
		If ESSBNodes.Br(akCtl, 9, 1, 4, 0) && akCtl.SyncStage() >= 3
			Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.ApplyFrenzy(nearby[index], 3)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
	; 5.12 開啟熟練分支「幻影」：開印後 3 秒目標對你的命中率 -30%
	; （引擎沒有命中率修正，以攻擊 -30% 表達，見實作紀錄）。
	If ESSBNodes.Br(akCtl, 9, 1, 1, 1)
		akCtl.ApplyUtil(17, 30.0, 3, akTarget)
	EndIf
	; 5.12 開啟大師分支「迷亂」：開印目標 3 秒內無法施法（沿用沉默的實作）。
	If ESSBNodes.Br(akCtl, 9, 1, 3, 0)
		akCtl.ApplySilenceSpell(akTarget, 3)
	EndIf
	; 5.12 開啟大師分支「暗染」：開印時附近 1 人也詛咒。
	If ESSBNodes.Br(akCtl, 9, 1, 3, 1)
		Actor[] spread = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If spread[0]
			akCtl.AddStackTo(spread[0], 10, 2)
			akCtl.ApplyMark(spread[0], 10)
		EndIf
	EndIf
EndFunction

Function OpenAstral(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.13 開啟新手分支「星散」：開印時附近 1 人也星痕，搜尋範圍隨星臨主線成長。
	If ESSBNodes.Br(akCtl, 10, 1, 0, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, ScatterRadius(akCtl), 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 11, 1)
			akCtl.ApplyMark(nearby[0], 11)
		EndIf
	EndIf
	; 5.13 開啟熟練分支「星引力」：開印時回復魔力。
	If ESSBNodes.Br(akCtl, 10, 1, 1, 1) && player
		akCtl.ApplyUtil(5, 40.0 * akCtl.GLevel(10), 0, player)
	EndIf
	; 5.13 開啟大師分支「星鎖」：開印目標 3 秒內受所有元素傷 +10%。
	If ESSBNodes.Br(akCtl, 10, 1, 3, 0)
		akCtl.SetStarLock(akTarget, 3)
	EndIf
	; 5.13 開啟大師分支「星光」：開印時你受傷 -10% 3 秒（PERK 進入點讀 ESSB_GuardStar）。
	If ESSBNodes.Br(akCtl, 10, 1, 3, 1)
		akCtl.SetGuardStar(3)
	EndIf
	; 5.13 開啟傳奇分支「星耀」：同調三段時開印的延遲星傷改為立即並 ×2。
	If ESSBNodes.Br(akCtl, 10, 1, 4, 0) && akCtl.SyncStage() >= 3
		akCtl.DetonateAstralNow(akTarget, 2.0)
	EndIf
EndFunction

; 5.11 開啟新手主線：浸濕減速 15% +1%／點（第六輪；原規劃 2.6 基礎為 10%）。
Float Function WetSlow(ESSBController akCtl) Global
	Return akCtl.WaterWetSlowPct.GetValue() + 1.0 * ESSBNodes.Rank(akCtl, 8, 1, 0)
EndFunction

; 5.11 持續新手主線：浸濕持續 10 秒 +0.3 秒／點。
Int Function WetSeconds(ESSBController akCtl) Global
	Float seconds = 10.0 + 0.3 * ESSBNodes.Rank(akCtl, 8, 0, 0)
	Return (seconds + 0.5) as Int
EndFunction

; ================================================================== 開形態（各元素的「臨」的附加效果）

Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	If aiElement == 8
		; 5.10 開啟專精分支「毒臨強化」：毒臨時範圍內敵人 +3 毒層。
		If ESSBNodes.Br(akCtl, 7, 1, 2, 0)
			Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 7, 3)
				EndIf
				index += 1
			EndWhile
		EndIf
	ElseIf aiElement == 9
		; 5.11 開啟專精分支「水臨強化」：水臨時範圍內敵人浸濕並減速 20%，你立即清除全部負面。
		If ESSBNodes.Br(akCtl, 8, 1, 2, 0)
			Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					akCtl.AddStackTo(nearby[index], 8, 1)
					akCtl.ApplyUtil(0, 20.0, 5, nearby[index])
				EndIf
				index += 1
			EndWhile
			akCtl.ApplyCleanse(True)
		EndIf
	ElseIf aiElement == 10
		; 5.12 開啟專精分支「暗臨強化」：暗臨時範圍內敵人恐懼 2 秒。
		If ESSBNodes.Br(akCtl, 9, 1, 2, 0)
			Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
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
		If ESSBNodes.Br(akCtl, 10, 1, 2, 0)
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

; 5.10 關閉熟練分支「延毒」：催毒 8 → 12 秒；關閉專精分支「毒斷」：融斷的催毒 ×2。
Int Function CatalyzeSeconds(ESSBController akCtl, Int aiReason) Global
	Int seconds = 8
	If ESSBNodes.Br(akCtl, 7, 2, 1, 0)
		seconds = 12
	EndIf
	If aiReason == 1 && ESSBNodes.Br(akCtl, 7, 2, 2, 0)
		seconds = seconds * 2
	EndIf
	Return seconds
EndFunction

; 催毒期間的每秒跳動倍率：基礎 2（每秒兩次），關閉新手分支「潰爛」改為 3。
Float Function CatalyzeRate(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 7, 2, 0, 0)
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 毒層每秒傷害的節點倍率：持續新手主線 +2%／點，催毒期間再 +3%／點（關閉傳奇主線）。
Float Function PoisonTickMult(ESSBController akCtl, Bool abCatalyzed) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 0, 0), 0.02)
	If abCatalyzed
		mult = mult * (1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 7, 2, 4), 0.03))
	EndIf
	Return mult
EndFunction

; 5.10 持續專精主線：基礎擴散間隔 2 秒 -0.1 秒／點。狀態容器是整數秒 tick，
; 所以分兩檔：10 點以下 2 秒、10 點以上 1 秒；點滿（15）的「0.5 秒」以「每秒傳兩個目標」表達。
Int Function SpreadInterval(ESSBController akCtl) Global
	If ESSBNodes.Rank(akCtl, 7, 0, 2) >= 10
		Return 1
	EndIf
	Return 2
EndFunction

Int Function SpreadTargets(ESSBController akCtl) Global
	If ESSBNodes.Rank(akCtl, 7, 0, 2) >= 15
		Return 2
	EndIf
	Return 1
EndFunction

; 5.10 持續專精分支「傳染門檻」：基礎擴散門檻 5 層 → 1 層。
Int Function SpreadThreshold(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 7, 0, 2, 1)
		Return 1
	EndIf
	Return 5
EndFunction

; 5.10 持續傳奇主線「瘟疫」：同調三段時毒層每秒自動擴散到附近敵人，機率 5%／點。
; 由 ESSBStatus 的每秒 tick 呼叫（每個帶毒目標一次，不做全場掃描）。
Function PoisonTickHook(ESSBController akCtl, Actor akTarget, Int aiPoison, Int aiKillingElement = 0) Global
	Int rank = ESSBNodes.Rank(akCtl, 7, 0, 4)
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
	If !ESSBNodes.Br(akCtl, 7, 2, 3, 0) || !akTarget
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
	Float percent = (akCtl.WaterFlowBasePct.GetValue() + akCtl.WaterFlowPerRankPct.GetValue() * ESSBNodes.Rank(akCtl, 8, 0, 1)) * 0.01
	percent = percent + 0.0005 * ESSBNodes.Rank(akCtl, 8, 0, 3) * akCtl.SyncStage()
	If akCtl.SyncStage() >= 3
		percent = percent + 0.0005 * ESSBNodes.Rank(akCtl, 8, 0, 4)
	EndIf
	Return percent
EndFunction

; 5.11 關閉新手分支「強引」：導引 ×1.5 → ×2.0；關閉傳奇主線：導引 +3%／點。
Float Function GuideMult(ESSBController akCtl) Global
	Float mult = 1.5
	If ESSBNodes.Br(akCtl, 8, 2, 0, 0)
		mult = 2.0
	EndIf
	Return mult * ESSBElem.SignatureMult(akCtl, 9)
EndFunction

; 5.11 關閉熟練分支「潮引」：水終焉時接管元素 +5 → +10 同調。
Int Function GuideSync(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 8, 2, 1, 0)
		Return 10
	EndIf
	Return 5
EndFunction

; ================================================================== 暗：死咒周邊

; 5.12 關閉專精主線：死咒的「已損失生命」係數 15% +0.5%／點。
Float Function DeathCurseLostRatio(ESSBController akCtl) Global
	Return 0.15 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 9, 2, 2), 0.005)
EndFunction

; 死咒期間目標無法被治療（規劃 2.6）：3 秒，關閉熟練分支「不治」延長到 6 秒。
; 引擎沒有「受到的治療」修正，以 HealRateMult -100% 表達（同血咒的偏離，見實作紀錄）。
Int Function DeathCurseSeconds(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 9, 2, 1, 0)
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
	If ESSBNodes.Br(akCtl, 9, 2, 0, 0)
		Float gain = 30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)
		akCtl.ApplyUtil(4, gain, 0, player)
		akCtl.ApplyUtil(5, gain, 0, player)
	EndIf
	; 5.12 關閉大師分支「處刑」：死咒結算時生命低於 15% 則直接死亡；
	; 首領與必要角色改為 ×3 傷害（處決對必要角色無效，規劃 2.9）。
	If !akTarget.IsDead() && ESSBNodes.Br(akCtl, 9, 2, 3, 0) && akTarget.GetActorValuePercentage("Health") < 0.15
		If akCtl.IsVIPTarget(akTarget)
			akCtl.ApplyDamage(10, afAmount * 2.0, akTarget)
		Else

			akCtl.Execute(akTarget, 10)
		EndIf
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "dark execution " + akTarget.GetFormID())
		EndIf
	EndIf

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

; 5.12 關閉新手分支「亡者歸來」：按 Round 14 歸因為黑暗的敵人 25% 機率立即復生為你的僕從；
; 傳奇分支「死靈主」在同調三段時機率 100%，且任何等級可改為永久（第六階，永久上限 1 名）。
Bool Function Reanimate(ESSBController akCtl, Actor akVictim, Int aiCurse) Global
	If !akVictim
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=invalid-target")
		EndIf
		Return False
	EndIf
	If !ESSBNodes.Br(akCtl, 9, 2, 0, 1)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=branch-not-owned")
		EndIf
		Return False
	EndIf
	Bool master = ESSBNodes.Br(akCtl, 9, 2, 4, 1) && akCtl.SyncStage() >= 3
	Float chance = 0.25
	If master
		chance = 1.0
	EndIf
	Float roll = Utility.RandomFloat(0.0, 1.0)
	If roll >= chance
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=roll-failed" + " roll=" + roll + " chance=" + chance)
		EndIf
		Return False
	EndIf
	; 規劃 5.12：必要角色、任務角色、被神聖化灰的屍體不復生（化灰先於復生判定）。
	If !akCtl.CanReanimate(akVictim)
		; CanReanimate logged its specific refusal at guarded L2.
		Return False
	EndIf
	Int tier = ReanimateTier(akVictim.GetLevel())
	If tier >= 6 && !master
		; 60 級以上的敵人只有死靈主能復生。
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=tier-refused level=" + akVictim.GetLevel())
		EndIf
		Return False
	EndIf
	Int servants = akCtl.ServantCount()
	Bool permanent = tier >= 6
	If master && servants <= 0
		; 死靈主：任何等級的僕從都可以改為永久（第六階），永久上限 1 名，
		; 所以只有在身邊一個僕從都沒有的時候才升成第六階。
		tier = 6
		permanent = True
	EndIf
	Int seconds = ReanimateSeconds(tier)
	; 5.12 關閉專精分支「亡者強化」：持續 ×2（永久的那一階不再加倍）。
	Bool empower = ESSBNodes.Br(akCtl, 9, 2, 2, 1)
	If empower && !permanent
		seconds = seconds * 2
	EndIf
	; 僕從計入原版召喚上限（含雙魂天賦）；第六階永久上限 1 名。
	Int cap = akCtl.SummonCap()
	If permanent
		cap = 1
	EndIf
	If servants >= cap
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=servant-cap-full cap=" + cap + " servants=" + servants)
		EndIf
		Return False
	EndIf
	If !akCtl.ApplyReanimate(akVictim, ReanimateCapOf(tier), seconds)
		; ApplyReanimate logged its specific refusal at guarded L2.
		Return False
	EndIf
	; 5.12 關閉專精分支「亡者強化」：繼承死前的詛咒層數作為攻擊加成，每層 +10%
	;（與「攻擊削弱」同樣以 AV 34 的定值表達，見實作紀錄）。
	If empower && aiCurse > 0
		akCtl.ApplyUtil(27, 10.0 * aiCurse, seconds, akVictim)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "reanimate " + akVictim.GetFormID() + " tier=" + tier \
			+ " sec=" + seconds + " curse=" + aiCurse)
	EndIf
	Return True
EndFunction

; ================================================================== 星：星落與引爆

; 5.13 關閉新手分支「隕星」：星落 ×2.0 → ×3.0。
Float Function FallK(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 10, 2, 0, 0)
		Return 3.0
	EndIf
	Return 2.0
EndFunction

; 5.13 關閉熟練分支「流星雨」：星落改為範圍。
Bool Function HasMeteorShower(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 10, 2, 1, 0)
EndFunction

; 5.13 關閉熟練分支「星斷」：星印記融斷改為真實傷害，倍率 ×0.6。
Bool Function HasTrueBurst(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 10, 2, 1, 1)
EndFunction

; 星痕引爆的延遲：環狀桶是 2 格（2 秒）。開啟新手主線「星痕延遲 -0.1 秒／點」
; 在 10 點以上縮成 1 秒（整數秒 tick 只有這兩檔）。
Int Function AstralDelay(ESSBController akCtl) Global
	If ESSBNodes.Rank(akCtl, 10, 1, 0) >= 10
		Return 1
	EndIf
	Return 2
EndFunction

; 星痕引爆傷害的節點倍率：持續新手主線 +2%／點。
Float Function AstralTickMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 10, 0, 0), 0.02)
EndFunction

; 5.13 持續大師分支「預知」：星痕引爆前 1 秒你受傷 -20%（PERK 進入點讀 ESSB_GuardAstral）。
Function AstralForesee(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 10, 0, 3, 0)
		akCtl.SetGuardAstral(2)
	EndIf
EndFunction

; 星痕引爆之後（由 ESSBStatus 呼叫）：星盾與星體。
Function OnAstralDetonate(ESSBController akCtl, Actor akTarget, Int aiLayers) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 5.13 持續大師分支「星盾」：星痕引爆時你獲得小護盾（臨時生命）。
	If ESSBNodes.Br(akCtl, 10, 0, 3, 1)
		akCtl.ApplyUtil(19, 25.0 * aiLayers * akCtl.GLevel(10), 10, player)
	EndIf
	; 5.13 持續傳奇分支「星體」：同調三段時星痕引爆治療你。
	If ESSBNodes.Br(akCtl, 10, 0, 4, 0) && akCtl.SyncStage() >= 3
		akCtl.ApplyUtil(4, 20.0 * aiLayers * akCtl.GLevel(10), 0, player)
	EndIf
EndFunction

; 星落本體（規劃 2.6 的終焉）：B_max ×2.0 星傷；星斷改為真實傷害 ×0.6；
; 流星雨改為範圍；群星（同調三段）再連鎖到範圍內的星痕目標。
Function Fall(ESSBController akCtl, Actor akTarget, Float afMult, Int aiReason) Global
	Float amount = ESSBReactions.ReactDamage(akCtl, 11, FallK(akCtl)) * afMult \
		* ESSBElem.SignatureMult(akCtl, 11)
	FallHit(akCtl, akTarget, amount, aiReason)
	If HasMeteorShower(akCtl)
		Actor[] nearby = akCtl.ScanTargets(akTarget, FallRadius(akCtl), 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				FallHit(akCtl, nearby[index], amount, aiReason)
			EndIf
			index += 1
		EndWhile
	EndIf
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

; Both delayed astral stacks and radiance retain weighted opening damage and feedback.
Function DetonateAstral(ESSBController akCtl, Actor akTarget, Int aiLayers, Float afWeight, Float afMult = 1.0) Global
	If aiLayers <= 0 || afWeight <= 0.0
		Return
	EndIf
	Float amount = ESSBReactions.ReactDamage(akCtl, 11, 1.0) * afWeight * afMult \
		* ESSBNodes.OmniMult(akCtl) * AstralTickMult(akCtl)
	akCtl.ApplyDamage(11, amount, akTarget)
	OnAstralDetonate(akCtl, akTarget, aiLayers)
EndFunction

; 5.13 持續傳奇主線「群星」：同調三段時星落連鎖附近星痕目標。
Function FallChain(ESSBController akCtl, Actor akTarget, Float afMult) Global
	Int rank = ESSBNodes.Rank(akCtl, 10, 0, 4)
	If rank <= 0 || akCtl.SyncStage() < 3
		Return
	EndIf
	Actor[] nearby = akCtl.ScanTargets(akTarget, ConstellationRadius(akCtl), 5, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.GetStack(nearby[index], 11) > 0
			Fall(akCtl, nearby[index], afMult * 0.5, 2)
		EndIf
		index += 1
	EndWhile
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "astral constellation " + akTarget.GetFormID())
	EndIf
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
	If ESSBNodes.Br(akCtl, 7, 2, 3, 1)
		akCtl.ApplyUtil(16, 20.0, 8, akTarget)
	EndIf
	; 5.10 關閉熟練分支「瘴氣」：毒終焉時毒層以原層數複製到 6 公尺內敵人（規劃 2.9 例外表：5 人）。
	If ESSBNodes.Br(akCtl, 7, 2, 1, 1)
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
	; 5.10 關閉傳奇分支「毒霧」：毒印記融斷後留下 5 秒毒霧，內部每秒 +1 毒層。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 7, 2, 4, 0)
		akCtl.StartDomain(8, akTarget, 5)
	EndIf
EndFunction

Function EndWaterNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 5.11 關閉大師分支「大潮」：水終焉時範圍內所有浸濕目標都給接管元素導引。
	If ESSBNodes.Br(akCtl, 8, 2, 3, 0)
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
	If ESSBNodes.Br(akCtl, 8, 2, 3, 1)
		akCtl.ApplyCleanse(True)
		akCtl.ApplyStrip(akTarget)
	EndIf
	; 5.11 關閉專精分支「汪洋」：水終焉不移除浸濕，保留為副印記 10 秒，融斷時再結算。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 8, 2, 2, 0)
		akCtl.KeepAsSecond(akTarget, 9, 10)
	EndIf
	If aiReason != 1
		Return
	EndIf
	; 5.11 關閉熟練分支「水斷」：水印記融斷改為治療你並回復耐力。
	If ESSBNodes.Br(akCtl, 8, 2, 1, 1) && player
		Float amount = ESSBReactions.ReactDamage(akCtl, 9, 2.0) * afMult * akCtl.GLevel(8)
		akCtl.ApplyUtil(4, amount, 0, player)
		akCtl.ApplyUtil(6, amount, 0, player)
	EndIf
	; 5.11 關閉傳奇分支「潮池」：水印記融斷後留下 5 秒水域。
	If ESSBNodes.Br(akCtl, 8, 2, 4, 0)
		akCtl.StartDomain(9, akTarget, 5)
	EndIf
EndFunction

Function EndDarkNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	Actor player = akCtl.ThePlayer()
	; 5.12 關閉熟練分支「蝕魔終焉」：暗終焉後接管元素的下一次終焉附帶吸魔。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 9, 2, 1, 1)
		akCtl.SetPendingDrain()
	EndIf
	; 5.12 關閉大師分支「深淵回響」：暗終焉回滿你的魔力。
	If ESSBNodes.Br(akCtl, 9, 2, 3, 1) && player
		akCtl.ApplyUtil(5, player.GetActorValueMax("Magicka"), 0, player)
	EndIf
	; 5.12 關閉傳奇分支「死域」：暗印記融斷後留下 5 秒死域。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 9, 2, 4, 0)
		akCtl.StartDomain(10, akTarget, 5)
	EndIf
EndFunction

Function EndAstralNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.13 關閉專精分支「星引」：星終焉後接管元素 +10 同調。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 10, 2, 2, 0)
		akCtl.AddSync(10)
	EndIf
	; 5.13 關閉大師分支「星界之門」：星終焉後接管元素直接視為同調一段。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 10, 2, 3, 0)
		akCtl.BoostSyncToStage1()
	EndIf
	; 5.13 持續傳奇主線「群星」：同調三段時星落連鎖附近星痕目標。
	FallChain(akCtl, akTarget, afMult)
	; 5.13 關閉傳奇分支「星域」：星印記融斷後留下 5 秒星域，範圍同星落。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 10, 2, 4, 0)
		akCtl.StartDomain(11, akTarget, 5, FallRadius(akCtl))
	EndIf
EndFunction

; 5.13 關閉大師分支「星軌終焉」：星終焉後接管元素的開印 ×1.5 → ×2.0
;（規劃 2.6 的基礎星落本來就給 ×1.5，分支再加深，見實作紀錄的解讀）。
Float Function TakeoverOpenMult(ESSBController akCtl) Global
	If ESSBNodes.Br(akCtl, 10, 2, 3, 1)
		Return 2.0
	EndIf
	Return 1.5
EndFunction

; 任何元素的終焉之後（由 ESSBReactions.End 呼叫一次）：暗的「蝕魔終焉」在這裡兌現。
Function OnAnyEnd(ESSBController akCtl, Int aiElement, Actor akTarget) Global
	If !akCtl.TakePendingDrain() || !akTarget
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	Float drain = 40.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)
	akCtl.ApplyUtil(2, drain, 0, akTarget)
	If player
		akCtl.ApplyUtil(5, drain, 0, player)
	EndIf
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "dark drain end " + akTarget.GetFormID())
	EndIf
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
	If ESSBNodes.Br(akCtl, 7, 0, 3, 1) && akCtl.IsPoisoned(player)
		akCtl.ApplyUtil(25, 20.0, 3, player)
	EndIf
	; 5.10 持續傳奇分支「百毒不侵」：同調三段時免疫中毒與疾病，
	; 且附近中毒敵人每秒替你回血。
	If !ESSBNodes.Br(akCtl, 7, 0, 4, 0) || akCtl.SyncStage() < 3
		Return
	EndIf
	akCtl.ApplyUtil(23, 100.0, 3, player)
	akCtl.ApplyUtil(26, 100.0, 3, player)
	Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
	Float heal = 0.0
	Int index = 0
	While index < nearby.Length
		If nearby[index] && akCtl.GetStack(nearby[index], 7) > 0
			heal = heal + 6.0 * akCtl.GLevel(7)
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
	If ESSBNodes.Rank(akCtl, 8, 0, 4) <= 0 || akCtl.SyncStage() < 3
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

; 化身（通用樹持續傳奇主線）觸發的「當前元素持續傳奇效果」。
Function OnAvatar(ESSBController akCtl, Int aiElement) Global
	If aiElement == 8
		; 瘟疫：對最近的帶毒目標強制擴散一次，並自己再加 3 層。
		Actor victim = akCtl.NearestMarked(8)
		If victim
			akCtl.AddStackTo(victim, 7, 3)
			akCtl.SpreadPoison(victim, 2)
		EndIf
	ElseIf aiElement == 9
		; 長河：立即結算一次長流（你與同伴各回一份）。
		WaterFormTick(akCtl)
	ElseIf aiElement == 10
		; 深淵：對最近的詛咒目標補滿詛咒層並重下一次抗性侵蝕。
		Actor victim = akCtl.NearestMarked(10)
		If victim
			akCtl.SetStack(victim, 10, CurseCap(akCtl))
			ApplyCurseErosion(akCtl, victim, CurseCap(akCtl))
		EndIf
	ElseIf aiElement == 11
		; 群星：對最近的星痕目標結算一次星落並連鎖。
		Actor victim = akCtl.NearestMarked(11)
		If victim
			Fall(akCtl, victim, 1.0, 2)
			FallChain(akCtl, victim, 1.0)
		EndIf
	EndIf
EndFunction

; 擊殺掛勾：由 ESSBController.OnKillEvent（PO3 OnActorKilled）與每秒 tick 的後援路徑轉進來。
Function OnKill(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiPoison, Int aiKillingElement = 0, Bool abAsh = False, Int aiCurse = 0) Global
	Actor player = akCtl.ThePlayer()
	If !player || !akTarget
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=invalid-player-or-target")
		EndIf
		Return
	EndIf
	; 5.10 持續大師分支「蔓延」：中毒目標死亡時毒層傳給附近敵人。
	If aiPoison > 0 && ESSBNodes.Br(akCtl, 7, 0, 3, 0)
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index]
				akCtl.AddStackTo(nearby[index], 7, aiPoison)
			EndIf
			index += 1
		EndWhile
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "poison creep " + akTarget.GetFormID() + " layers=" + aiPoison)
		EndIf
	EndIf
	Int curse = aiCurse
	; 5.12 持續大師分支「收割」：詛咒目標死亡回魔。
	If curse > 0 && ESSBNodes.Br(akCtl, 9, 0, 3, 1)
		akCtl.ApplyUtil(5, 15.0 * curse * akCtl.GLevel(9), 0, player)
	EndIf
	; 5.12 關閉新手分支「亡者歸來」：按 Round 14 歸因為黑暗的敵人有機率復生為僕從。
	; 與神聖化灰互斥（化灰先於復生判定，規劃 5.12），使用控制器預先凍結的化灰決策。
	If abAsh
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=ash-priority")
		EndIf
		Return
	EndIf
	If aiKillingElement == 0
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=no-element")
		EndIf
		Return
	EndIf
	If aiKillingElement != 10
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "reanimate-reject", "reason=element-mismatch" + " element=" + aiKillingElement)
		EndIf
		Return
	EndIf
	Reanimate(akCtl, akTarget, curse)
EndFunction

; ================================================================== 常駐能力與守衛

; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%（自有常駐能力，開形態才掛）。
Bool Function HasPoisonImmunity(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 7, 0, 0, 0)
EndFunction

; 5.13 持續新手分支「星輝」：星形態魔力回復 +20%（沿用雷樹「感應」的同款能力）。
Bool Function HasStarlight(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 10, 0, 0, 0)
EndFunction

; 5.10 持續熟練分支「毒皮」：被近戰命中時攻擊者 +2 毒層。由 ESSBGuard 呼叫。
Function OnPoisonSkin(ESSBController akCtl, Actor akAttacker) Global
	If !ESSBNodes.Br(akCtl, 7, 0, 1, 1) || !akAttacker
		Return
	EndIf
	akCtl.AddStackTo(akAttacker, 7, 2)
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "poison skin " + akAttacker.GetFormID())
	EndIf
EndFunction

; 5.12 持續傳奇分支「影身」：同調三段時被近戰命中 30% 機率無效並回魔。由 ESSBGuard 呼叫。
Function OnShadowBody(ESSBController akCtl) Global
	akCtl.SetGuardDark(0)
	If !ESSBNodes.Br(akCtl, 9, 0, 4, 0) || akCtl.SyncStage() < 3
		Return
	EndIf
	If Utility.RandomFloat(0.0, 1.0) >= 0.3
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	akCtl.SetGuardDark(2)
	If player
		akCtl.ApplyUtil(5, 50.0 * akCtl.GLevel(9), 0, player)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "dark shadowbody")
	EndIf
EndFunction

Function OnDeathSoul(ESSBController akCtl, Actor akTarget) Global
	; 5.12 關閉專精分支「亡魂」：死咒殺死目標時附近敵人恐懼 2 秒。
	If ESSBNodes.Br(akCtl, 9, 2, 2, 0)
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
