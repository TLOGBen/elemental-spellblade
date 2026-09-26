Scriptname ESSBElem Hidden
{火（5.3）、冰（5.4）、雷（5.5）三棵元素樹的節點效果。

樹索引 0 火、1 冰、2 雷（元素編號 1／2／3）。路線 0 持續、1 開啟、2 關閉。
其餘八棵元素樹照同一組函式名稱：元素 4–7（土風血聖）在 ESSBElem2、元素 8–11（毒水暗星）在 ESSBElem3。

Round 22（N3）起，熱度（你身上的階）、凍結量表、冰晶、碎冰、印記時長、開印與命中的層數都是 DLL 的事
（native/include/Status.h）；這裡只剩開印與終焉的「本體」——傷害、削減、回復、範圍掃描（N5 前），
狀態只經 ESSBNative 讀寫。

所有傷害都走 ESSBController.ApplyDamage（自有 ESSB_React_<元素> 法術，執行期設 magnitude 後
DoCombatSpellApply），G(L) 由 ApplyDamage 統一乘上。}

; ================================================================== 自身資源上限（N4 前在 Papyrus）

; 雷 電荷（你）：基礎 6；持續專精主線 +1／每 3 點（蓄電）；萬象再 +1／每 5 點。
Int Function ChargeCap(ESSBController akCtl) Global
	Return 6 + ESSBNodes.Rank(akCtl, 2, 0, 2) / 3 + ESSBNodes.StatusCapBonus(akCtl) ; @node 電荷上限
EndFunction

; 冰 凍結量表固定 5（量表不吃萬象，規劃 2.3）。
Int Function FreezeCap() Global
	Return 5
EndFunction

; ================================================================== 開印與終焉倍率

; 各元素「關閉新手主線：終焉 +2%／點」。傳奇主線（爆燃／碎冰／放電 +3%／點）
; 只作用在該元素自己的終焉效果上，由各自的函式另乘。
Float Function EndMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 0), 0.02) ; @node 終焉{elements}
EndFunction

; 各元素「關閉熟練／大師主線：該元素印記的融斷 +2%／點」（兩階各一次）。
Float Function BurstMult(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 1), 0.02) + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 3), 0.02) ; @node *印記的融斷{elements}, *印記的融斷再{elements}
EndFunction

; 關閉傳奇主線「該元素終焉招式 +3%／點」：火 爆燃、冰 碎冰、雷 放電、土 地震、血 血潮、聖 裁決、水 導引、暗 死咒、星 星落。
; 風（落地傷害 +5%／點）與毒（催毒期間中毒傷害 +3%／點）的同一格是別的節點（落地在 ESSBElem2、催毒在 DLL）。
Float Function SignatureMult(ESSBController akCtl, Int aiElement) Global
	If aiElement == 5 || aiElement == 8
		Return 1.0
	EndIf
	Int tree = ESSBNodes.TreeOf(aiElement)
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 4), 0.03) ; @node 爆燃{fire} / 碎冰{frost} / 放電{lightning} / 地震{earth} / 血潮{blood} / 裁決{divine} / 導引{water} / 死咒{darkness} / 星落{astral}
EndFunction

; ================================================================== 開印時的自身資源（N4 前在 Papyrus）

; 雷 開印電荷 +2，開啟新手主線 +1／每 5 點；土、風的岩甲與風勢在 ESSBElem2。
; 目標身上的層數（凍結、血痕、中毒、詛咒、星痕…）與你的熱度、聖佑由 DLL 在開印當下加。
Int Function OpenStacks(ESSBController akCtl, Int aiElement) Global
	If aiElement == 3
		Return 2 + ESSBNodes.Rank(akCtl, 2, 1, 0) / 5 ; @node 開印電荷
	ElseIf aiElement == 4 || aiElement == 5
		Return ESSBElem2.OpenStacks(akCtl, aiElement)
	EndIf
	Return 0
EndFunction

; 把小數層數變成整數：整數部分保證給，小數部分以機率決定。
Int Function RoundStochastic(Float afValue) Global
	Int whole = afValue as Int
	Float remainder = afValue - whole
	If remainder > 0.0 && Utility.RandomFloat(0.0, 1.0) < remainder
		whole += 1
	EndIf
	Return whole
EndFunction

; ================================================================== 開印（分支）

; aiCutFrom：這一擊切掉的元素（0 = 沒有切）；接管類效果（餘燼、血引、聖引）的狀態部分在 DLL，
; 這裡只剩要 Papyrus 做的（餘電的放電：電荷 N4 前在 Papyrus）。
Function OnOpen(ESSBController akCtl, Int aiElement, Actor akTarget, Float afMult, Int aiCutFrom) Global
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
	akCtl.AfterOpen(aiElement, akTarget)
EndFunction

Function OpenFire(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.3 開啟熟練分支「餘熱」：開印時回復 15 耐力。
	If ESSBNodes.Br(akCtl, 0, 1, 1, 1) && player ; @node 餘熱
		akCtl.ApplyUtil(6, 15.0, 0, player)
	EndIf
	; 5.3 開啟專精分支「焰起強化」：開印額外對範圍內敵人造成一次火附傷（範圍掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 0, 1, 2, 0) ; @node 焰起強化
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
	; 5.3 開啟傳奇分支「先燃」：同調三段時開印立即一次 ×0.5 爆燃（不消耗目標狀態），照你的熱度算。
	If ESSBNodes.Br(akCtl, 0, 1, 4, 0) && akCtl.SyncStage() >= 3 && player ; @node 先燃
		Detonate(akCtl, akTarget, 0.5, ESSBNative.GetStatus(player, 20), 0.0, 1.0)
	EndIf
	; 烈火之始、引火、烈火點燃（熱度）在 DLL。
EndFunction

; 霜鎖、絕霜、深霜結（凍結量表、冰晶）在 DLL；這裡只剩範圍版的寒潮。
Function OpenFrost(ESSBController akCtl, Actor akTarget) Global
	; 5.4 開啟新手分支「寒潮」：開印時附近 1 人凍結 +2（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 1, 1, 0, 0) ; @node 寒潮
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.AddStackTo(nearby[0], 2, 2)
		EndIf
	EndIf
EndFunction

Function OpenShock(ESSBController akCtl, Actor akTarget) Global
	Actor player = akCtl.ThePlayer()
	; 5.5 開啟新手分支「傳導」：開印時附近 1 人也感電（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 2, 1, 0, 0) ; @node 傳導
		Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0]
			akCtl.ApplyMark(nearby[0], 3)
		EndIf
	EndIf
	; 5.5 開啟熟練分支「充能開印」：開印時回復 B_max 魔力。
	If ESSBNodes.Br(akCtl, 2, 1, 1, 1) && player ; @node 充能開印
		akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3), 0, player)
	EndIf
	; 5.5 開啟大師分支「感電削弱」：感電目標魔抗 -10%。
	If ESSBNodes.Br(akCtl, 2, 1, 3, 0) ; @node 感電削弱
		akCtl.ApplyUtil(16, 10.0, 8, akTarget)
	EndIf
	; 5.5 開啟大師分支「雷閃」：開印後 2 秒移速 +15%。
	If ESSBNodes.Br(akCtl, 2, 1, 3, 1) && player ; @node 雷閃
		akCtl.ApplyUtil(9, 15.0, 2, player)
	EndIf
	; 5.5 開啟傳奇分支「先雷」：同調三段時開印立即放電一次，不消耗電荷。
	If ESSBNodes.Br(akCtl, 2, 1, 4, 0) && akCtl.SyncStage() >= 3 ; @node 先雷
		Discharge(akCtl, akTarget, akCtl.GetSelf(1), False, 1.0, 1.0, -1.0, False)
	EndIf
EndFunction

; ================================================================== 開形態：火臨／冰臨／雷臨

; 各元素開啟大師主線：開形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點（開印由 DLL 做，ForceOpenOn）。
Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Int rank = ESSBNodes.Rank(akCtl, tree, 1, 3) ; @node *臨{fire frost lightning wind blood divine poison water darkness astral} / 地臨{earth}
	If rank <= 0
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Float radius = (2.0 + 0.2 * rank) * 70.0
	Actor[] nearby = akCtl.ScanTargets(player, radius, 5, player)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			akCtl.ForceOpenOn(nearby[index], aiElement)
			; 5.4 開啟專精分支「冰臨強化」：冰臨附帶減速 30% 3 秒。
			If aiElement == 2 && ESSBNodes.Br(akCtl, 1, 1, 2, 0) ; @node 冰臨強化
				akCtl.ApplyUtil(0, 30.0, 3, nearby[index])
			EndIf
		EndIf
		index += 1
	EndWhile
	; 5.5 開啟專精分支「雷臨強化」：雷臨時立即獲得 5 電荷。
	If aiElement == 3 && ESSBNodes.Br(akCtl, 2, 1, 2, 0) ; @node 雷臨強化
		akCtl.AddSelf(1, 5)
	EndIf
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "advent element=" + aiElement + " radius=" + radius)
	EndIf
EndFunction

; 「臨」的範圍：2 公尺 +0.2 公尺／點（該元素開啟大師主線；沒投點就是 2 公尺）。臨強化類分支的「範圍內」用同一個範圍。
Float Function AdventRadiusOf(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Int rank = ESSBNodes.Rank(akCtl, tree, 1, 3) ; @node *臨{fire frost lightning wind blood divine poison water darkness astral} / 地臨{earth}
	Return (2.0 + 0.2 * rank) * 70.0
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

; ================================================================== 火：爆燃

; v0.4 2.6 爆燃：B_max × 熱度倍率（無／微熱／灼熱／白熱／熔燒 ×1.0／1.6／2.4／3.2／4.0）× (1＋消耗加成) × 熾焰，單體。
; 熱度階、消耗加成（DLL 吃掉目標身上其他元素的狀態算出來的，含爆燃的消耗加成主線）與熾焰倍率都由 DLL 給。
Float Function HeatBurstMult(Int aiHeat) Global
	If aiHeat >= 4
		Return 4.0
	ElseIf aiHeat == 3
		Return 3.2
	ElseIf aiHeat == 2
		Return 2.4
	ElseIf aiHeat == 1
		Return 1.6
	EndIf
	Return 1.0
EndFunction

Function Detonate(ESSBController akCtl, Actor akTarget, Float afMult, Int aiHeat, Float afBonus, Float afBlaze) Global
	Float amount = ESSBReactions.ReactDamage(akCtl, 1, HeatBurstMult(aiHeat)) * (1.0 + afBonus) * afBlaze * afMult \
		* SignatureMult(akCtl, 1)
	akCtl.ApplyDamage(1, amount, akTarget, 1)
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "detonate " + akTarget.GetFormID() + " heat=" + aiHeat + " bonus=" + afBonus + " amount=" + amount)
	EndIf
EndFunction

; ================================================================== 冰：冰封與碎冰的本體

; 冰封開始（DLL 送 ESSB_Frozen）：冰封期間的強減速 50%（絕對零度：同調三段時再 -2%／點）與「深寒」，時長＝冰封秒數。
; 凍結量表、冰晶、碎冰的真傷由 DLL 管。
Function OnFrozen(ESSBController akCtl, Actor akTarget, Int aiSeconds) Global
	Float slow = 50.0
	If akCtl.SyncStage() >= 3
		slow = slow + 2.0 * ESSBNodes.Rank(akCtl, 1, 0, 4) ; @node 絕對零度
	EndIf
	; 總減速上限 70%（v0.4 5.4）：ApplyUtil 的減速一律壓在 ESSB_SlowCapPct（≤ 70）以下。
	akCtl.ApplyUtil(0, slow, aiSeconds, akTarget)
	; 5.4 持續熟練分支「深寒」：冰封中目標耐力不回復（耐力凝滯），攻擊 -20%。
	If ESSBNodes.Br(akCtl, 1, 0, 1, 0) ; @node 深寒
		akCtl.ApplyUtil(17, 20.0, aiSeconds, akTarget)
		akCtl.ApplyUtil(21, 100.0, aiSeconds, akTarget)
	EndIf
EndFunction

; 碎冰之後（DLL 送 ESSB_Shatter）：碎甲 10%（碎甲加深 20%），5 秒。
Function OnShatter(ESSBController akCtl, Actor akTarget) Global
	Float shred = 0.1
	If ESSBNodes.Br(akCtl, 1, 2, 3, 1) ; @node 碎甲加深
		shred = 0.2
	EndIf
	akCtl.ApplyUtil(1, akTarget.GetActorValue("DamageResist") * shred, 5, akTarget)
EndFunction

; ================================================================== 雷：放電

; 放電（v0.4 2.6、5.5）：電荷數 × 30% B_max（每格 +1%／點）× R，削減魔力＝傷害的 50%，並跳到附近 2 人各 40%
;（電弧 3 人 55%、連鎖 5 人）。暴擊：與附傷同一個暴擊率（5% + 每格電荷 2%），一般 ×1.5，切換那一擊是重擊時 ×2.5；
; 電荷滿格的重擊放電必定暴擊（×2.5）。afCritDraw 是 DLL 在終焉當下擲的 [0,1)；Papyrus 自己觸發的放電（先雷、餘電、
; 雷殛、雷暴、雷霆、雷神）傳 -1，由這裡擲（電荷在 N4 前還在 Papyrus，所以暴擊率在這裡算）。
Function Discharge(ESSBController akCtl, Actor akTarget, Int aiCharge, Bool abConsume, Float afMult, Float afPower, Float afCritDraw, Bool abCutPower) Global
	If aiCharge <= 0 || !akTarget
		Return
	EndIf
	Float perCharge = 0.3 * (1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 2, 0, 0), 0.01)) ; @node 放電每格電荷傷害
	Float amount = ESSBReactions.ReactDamage(akCtl, 3, perCharge * aiCharge) * afMult * SignatureMult(akCtl, 3) * afPower
	Float draw = afCritDraw
	If draw < 0.0
		draw = Utility.RandomFloat(0.0, 1.0)
	EndIf
	Bool crit = draw < 0.05 + 0.02 * aiCharge
	If abCutPower && aiCharge >= ChargeCap(akCtl)
		crit = True
	EndIf
	If crit
		If abCutPower
			amount = amount * 2.5
		Else
			amount = amount * 1.5
		EndIf
	EndIf
	Float drainRatio = 0.5
	akCtl.ApplyDamage(3, amount, akTarget)
	akCtl.ApplyUtil(2, amount * drainRatio * akCtl.GLevel(2), 0, akTarget)

	Int jumpCount = 2
	Float jumpRatio = 0.4
	; 5.5 持續熟練分支「電弧」：跳躍人數 2 → 3、跳躍傷害 40% → 55%。
	If ESSBNodes.Br(akCtl, 2, 0, 1, 0) ; @node 電弧
		jumpCount = 3
		jumpRatio = 0.55
	EndIf
	; 5.5 關閉新手分支「連鎖」：跳躍 2 → 5 人。
	If ESSBNodes.Br(akCtl, 2, 2, 0, 0) ; @node 連鎖
		jumpCount = 5
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

	If abConsume && !ESSBNodes.Br(akCtl, 2, 2, 1, 0) ; @node 蓄餘
		akCtl.ClearSelf(1)
	EndIf
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "discharge " + akTarget.GetFormID() + " charge=" + aiCharge + " crit=" + crit + " amount=" + amount)
	EndIf
EndFunction

; 5.5 持續傳奇主線「天雷」：同調三段時放電改為對範圍內所有感電目標（掃描 N5 前在這裡）。
Function DischargeAll(ESSBController akCtl, Actor akTarget, Int aiCharge, Float afMult, Bool abConsume, Float afPower, Float afCritDraw, Bool abCutPower) Global
	Int rank = ESSBNodes.Rank(akCtl, 2, 0, 4) ; @node 天雷
	If rank <= 0 || akCtl.SyncStage() < 3
		Discharge(akCtl, akTarget, aiCharge, abConsume, afMult, afPower, afCritDraw, abCutPower)
		Return
	EndIf
	Float radius = (2.0 + 0.2 * rank) * 70.0
	Actor player = akCtl.ThePlayer()
	Discharge(akCtl, akTarget, aiCharge, False, afMult, afPower, afCritDraw, abCutPower)
	If player
		Actor[] nearby = akCtl.ScanTargets(player, radius, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.HasElementMark(nearby[index], 3)
				Discharge(akCtl, nearby[index], aiCharge, False, afMult, 1.0, -1.0, False)
			EndIf
			index += 1
		EndWhile
	EndIf
	If abConsume && !ESSBNodes.Br(akCtl, 2, 2, 1, 0) ; @node 蓄餘
		akCtl.ClearSelf(1)
	EndIf
EndFunction

; ================================================================== 終焉掛勾

; 由 ESSBReactions.End 在各元素的終焉本體之後呼叫（分支的範圍與追加效果）。
; 關閉專精主線「終焉後 5 秒內接管元素附傷」（R2：冰雷聖毒水星）的視窗由 DLL 在被切時掛上。
Function OnEnd(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiReason, Float afMult, Int aiSnapshot = -1) Global
	If aiElement == 1
		EndFireNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 2
		EndFrostNodes(akCtl, akTarget, aiReason, afMult)
	ElseIf aiElement == 3
		EndShockNodes(akCtl, akTarget, aiReason, afMult, aiSnapshot)
	ElseIf aiElement >= 4 && aiElement <= 7
		ESSBElem2.OnEnd(akCtl, aiElement, akTarget, aiReason, afMult)
	ElseIf aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnEnd(akCtl, aiElement, akTarget, aiReason, afMult)
	EndIf
EndFunction

Function EndFireNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.3 關閉大師分支「焚天」：火終焉觸發時範圍內所有帶火印記的目標一起爆燃（各自吃自己身上的狀態；掃描 N5 前在這裡，
	; 每一個都是 DLL 的連鎖終焉）。
	If ESSBNodes.Br(akCtl, 0, 2, 3, 0) ; @node 焚天
		Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 5, akTarget)
		Int index = 0
		While index < nearby.Length
			If nearby[index] && akCtl.HasElementMark(nearby[index], 1)
				ESSBNative.EndMark(nearby[index], 1, 2, afMult)
			EndIf
			index += 1
		EndWhile
	EndIf
	; 5.3 關閉傳奇分支「火域」：火印記融斷後留下 5 秒火域（內部敵人受火傷 +20%、你在其中升階免等待，TickDomain 掛標記）。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 0, 2, 4, 0) ; @node 火域
		akCtl.StartDomain(1, akTarget, 5)
	EndIf
EndFunction

Function EndFrostNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult) Global
	; 5.4 關閉熟練分支「冰崩」：碎冰改為 3 公尺範圍，命中所有冰封目標；關閉大師分支「冰河」：冰終焉時目標若冰封，
	; 範圍內所有冰封目標一起碎冰（掃描 N5 前在這裡；每一個的碎冰由 DLL 結算，各吃自己的冰晶）。
	If ESSBNodes.Br(akCtl, 1, 2, 1, 0) || ESSBNodes.Br(akCtl, 1, 2, 3, 0) ; @node 冰崩, 冰河
		ShatterArea(akCtl, akTarget, afMult)
	EndIf
	; 5.4 關閉傳奇分支「冰原」：冰印記融斷後留下 5 秒冰原。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 1, 2, 4, 1) ; @node 冰原
		akCtl.StartDomain(2, akTarget, 5)
	EndIf
EndFunction

Function ShatterArea(ESSBController akCtl, Actor akTarget, Float afMult) Global
	Actor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 5, akTarget)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && ESSBNative.GetStatus(nearby[index], 19) > 0
			ESSBNative.Shatter(nearby[index])
		EndIf
		index += 1
	EndWhile
EndFunction

Function EndShockNodes(ESSBController akCtl, Actor akTarget, Int aiReason, Float afMult, Int aiCharge = -1) Global
	; 5.5 關閉專精分支「餘電」：雷終焉後接管元素的開印附帶一次 ×0.5 放電。
	If aiReason == 0 && ESSBNodes.Br(akCtl, 2, 2, 2, 0) ; @node 餘電
		akCtl.SetPendingDischarge(aiCharge)
	EndIf
	; 5.5 關閉大師分支「雷殛」：雷終焉對範圍內所有感電目標各一次全額放電（掃描 N5 前在這裡）。
	If ESSBNodes.Br(akCtl, 2, 2, 3, 0) ; @node 雷殛
		Int charge = aiCharge
		If charge < 0
			charge = akCtl.GetSelf(1)
		EndIf
		If charge > 0
			Actor[] nearby = akCtl.ScanTargets(akTarget, 1050.0, 5, akTarget)
			Int index = 0
			While index < nearby.Length
				If nearby[index] && akCtl.HasElementMark(nearby[index], 3)
					Discharge(akCtl, nearby[index], charge, False, afMult, 1.0, -1.0, False)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
	; 5.5 關閉傳奇分支「雷霆」：雷印記融斷後 5 秒內你每次命中都放電 ×0.3。
	If aiReason == 1 && ESSBNodes.Br(akCtl, 2, 2, 4, 0) ; @node 雷霆
		akCtl.SetThunder(5)
	EndIf
EndFunction

; 5.5 關閉大師分支「過載終焉」：任一元素終焉時，若你電荷 ≥8，該次終焉傷害 ×2（v0.4；電荷跨形態攜帶是 N4）。
Float Function OverloadMult(ESSBController akCtl, Int aiElement, Int aiCharge = -1) Global
	If aiCharge < 0
		aiCharge = akCtl.GetSelf(1)
	EndIf
	If aiCharge >= 8 && ESSBNodes.Br(akCtl, 2, 2, 3, 1) ; @node 過載終焉
		Return 2.0
	EndIf
	Return 1.0
EndFunction

; 5.5 關閉熟練分支「雷斷」：雷印記融斷時附加你全部電荷的放電加成。
Float Function ShockBurstBonus(ESSBController akCtl, Int aiElement, Int aiReason) Global
	If aiElement == 3 && aiReason == 1 && ESSBNodes.Br(akCtl, 2, 2, 1, 1) ; @node 雷斷
		Return 1.0 + 0.3 * akCtl.GetSelf(1)
	EndIf
	Return 1.0
EndFunction

; 5.4 關閉熟練分支「冰封融斷」：冰印記融斷時目標若冰封，視同碎冰。
Bool Function FrostBurstShatter(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 1, 2, 1, 1) ; @node 冰封融斷
EndFunction

; ================================================================== 每秒與擊殺掛勾

Function OnTick(ESSBController akCtl, Int aiElement) Global
	If aiElement == 2
		; 5.4 持續傳奇分支「冰心」：生命低於 30% 時自動冰封附近所有凍結量表 ≥1 的敵人，每 30 秒一次。
		If ESSBNodes.Br(akCtl, 1, 0, 4, 0) ; @node 冰心
			Actor player = akCtl.ThePlayer()
			If player && player.GetActorValuePercentage("Health") < 0.3 && akCtl.TakeIceHeart()
				Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
				Int index = 0
				While index < nearby.Length
					If nearby[index] && ESSBNative.GetStatus(nearby[index], 2) > 0
						ESSBNative.SetStatus(nearby[index], 2, FreezeCap())
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
		If ESSBNodes.Br(akCtl, 2, 0, 4, 0) && akCtl.SyncStage() >= 3 ; @node 雷神
			Int charge = akCtl.GetSelf(1)
			If charge >= ChargeCap(akCtl)
				Actor victim = akCtl.NearestMarked(3)
				If victim
					DischargeAll(akCtl, victim, charge, 1.0, True, 1.0, -1.0, False)
					Actor player = akCtl.ThePlayer()
					If player
						akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3) * charge, 0, player)
					EndIf
				EndIf
			EndIf
		EndIf
	EndIf
EndFunction

Function OnKill(ESSBController akCtl, Int aiElement, Actor akTarget, Int aiFreeze) Global
	; 5.4 持續專精分支「連鎖冰封」：冰封目標死亡時附近敵人凍結 +3 並減速 30% 3 秒（死亡處理 N5 前在這裡；
	; 屍體的凍結量表由 DLL 的死亡快照給）。
	If aiFreeze >= 5 && ESSBNodes.Br(akCtl, 1, 0, 2, 1) ; @node 連鎖冰封
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

; 5.5 持續專精分支「雷暴」：電荷滿時普攻也有 30% 機率放電（N4 前在 Papyrus）。
Bool Function StormChance(ESSBController akCtl) Global
	If !ESSBNodes.Br(akCtl, 2, 0, 2, 0) ; @node 雷暴
		Return False
	EndIf
	If akCtl.GetSelf(1) < ChargeCap(akCtl)
		Return False
	EndIf
	Return Utility.RandomFloat(0.0, 1.0) < 0.3
EndFunction

; 5.3 持續專精主線：帶火印記目標火抗 -1%／點（命中火印記目標時）。
Function ApplyFireResistShred(ESSBController akCtl, Actor akTarget) Global
	Int rank = ESSBNodes.Rank(akCtl, 0, 0, 2) ; @node 帶火印記目標火抗
	If rank <= 0 || !akCtl.HasElementMark(akTarget, 1)
		Return
	EndIf
	akCtl.ApplyUtil(13, rank as Float, 6, akTarget)
EndFunction

Function OnCremation(ESSBController akCtl, Actor akTarget, Float afAmount) Global
	; 5.3 關閉大師分支「火葬」：爆燃擊殺的目標對附近敵人再爆一次 ×0.5。
	If ESSBNodes.Br(akCtl, 0, 2, 3, 1) ; @node 火葬
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
