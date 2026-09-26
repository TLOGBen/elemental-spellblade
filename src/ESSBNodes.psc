Scriptname ESSBNodes Hidden
{節點效果框架 + 全元素通用樹（規劃 v0.4 第 2.7、5.2 節）。

本檔是機制前線的「一種效果一個樣式」總表。三個樣式，別的樹只要照抄：

  樣式 A（主線數值）：在計算的地方讀 `Rank(ctl, tree, route, tier)`（0–15），
    乘進對應的公式項。所有 G(L) 都走 `GL(ctl, tree)` = 1 + 0.05 × 樹等級。
  樣式 B（分支旗標）：在對應的事件處理函式裡讀 `Br(ctl, tree, route, tier, n)`，
    成立才跑那一段。分支是 0/1，不是階數。
  樣式 C（引擎側）：武器傷害、護甲、抗性、移速、耐力消耗這種 Papyrus 改不動的，
    由 build_v03.py 在同一筆 PERK 記錄上加進入點（PRKE/DATA/EPFT/EPFD/PRKC/CTDA）。
    進入點的條件只能讀 CTDA 讀得到的東西，所以腳本狀態（戰意、電荷、同調段、
    各種護盾秒數）一律鏡射到 0x005000 段的全域變數，由控制器在值變動時寫一次。

每一個讀點數的呼叫都在同一行帶 `; @node v0.4 節點名稱`，建置時 build/fix21_identity.py 逐一跟
build/plan-tree-nodes.json 核對（round 21）：格位換了意思、讀到退役格或讀到後續切片的節點，建置就失敗。

樹索引：0–10 元素（火冰雷土風血聖毒水暗星），11 無元素，12 全元素通用。
路線 0 持續／1 開啟／2 關閉（無元素樹是 0 大師／1 滅法／2 冷寂）。
階 0 新手／1 熟練／2 專精／3 大師／4 傳奇。

每個效果處理函式都以等級 2 或 3 留紀錄（ESSBController.LogThrottled），
等級 1 留給既有的事件紀錄（開印、終焉、融斷、形態）。}

; fix round 6: one runtime scale for approved percentage damage mainlines.
Float Function Pct(ESSBController akCtl, Int aiRank, Float afBasePerPoint) Global
	If akCtl.RuntimeCacheReady
		Return aiRank * afBasePerPoint * akCtl.CachedNodeScale
	EndIf
	Return aiRank * afBasePerPoint * akCtl.NodeScale.GetValue()
EndFunction

; round 21：v0.3 的 RefreshWeaponPercent（依節點倍率改寫純武藝、戰意、淬火三條主線的武器傷害進入點）已刪除——
; 三條主線在 v0.4 是吸魔量、法盾分擔、寂上限，ESP 的武器傷害進入點同一輪拿掉（合約成果 3）。

Int Function COMMON() Global
	Return 12
EndFunction

Int Function NOFORM() Global
	Return 11
EndFunction

; ================================================================== 樣式 A／B 的讀取入口

; 主線階數 0–15。走 ESSBTrees 的快取（形態切換與選單關閉時 RefreshTree），命中即 O(1)。
Int Function Rank(ESSBController akCtl, Int aiTree, Int aiRoute, Int aiTier) Global
	If !akCtl
		Return 0
	EndIf
	Return akCtl.Rank(aiTree, aiRoute, aiTier)
EndFunction

; 分支是否已取得。
Bool Function Br(ESSBController akCtl, Int aiTree, Int aiRoute, Int aiTier, Int aiIndex) Global
	If !akCtl
		Return False
	EndIf
	Return akCtl.Br(aiTree, aiRoute, aiTier, aiIndex)
EndFunction

; 規劃 2.7：G(L) = 1 + 0.05 × L，100 級為 ×6。
Float Function GL(ESSBController akCtl, Int aiTree) Global
	If !akCtl
		Return 1.0
	EndIf
	Return akCtl.GLevel(aiTree)
EndFunction

; 元素 1–11 對應的樹索引 0–10；元素不合法時回無元素樹。
Int Function TreeOf(Int aiElement) Global
	If aiElement >= 1 && aiElement <= 11
		Return aiElement - 1
	EndIf
	Return 11
EndFunction

; ================================================================== 通用樹：同調

; 5.2 持續新手：同調門檻 -2%／點；持續熟練分支「專一」：同一形態超過 60 秒再降一半。
Float Function SyncThresholdScale(ESSBController akCtl) Global
	Float scale = 1.0 - 0.02 * Rank(akCtl, 12, 0, 0) ; @node 同調門檻
	If scale < 0.4
		scale = 0.4
	EndIf
	If Br(akCtl, 12, 0, 1, 1) && akCtl.FormHeldSeconds() >= 60.0 ; @node 專一
		scale = scale * 0.5
	EndIf
	Return scale
EndFunction

; 5.2 持續新手分支「承接」：切換時保留前一形態三分之一同調。
Int Function CarryOverSync(ESSBController akCtl, Int aiBefore) Global
	If !Br(akCtl, 12, 0, 0, 0) ; @node 承接
		Return 0
	EndIf
	Return aiBefore / 3
EndFunction

; 5.2 持續大師分支「回饋」：同調升段時回復生命與魔力各 B_max ×2。
Function OnSyncStage(ESSBController akCtl, Int aiStage) Global
	If Br(akCtl, 12, 0, 3, 1) ; @node 回饋
		Actor player = akCtl.ThePlayer()
		Float amount = ESSBReactions.BaseMax(akCtl, akCtl.CurrentElement.GetValueInt()) * 2.0
		If player && amount > 0.0
			akCtl.ApplyUtil(4, amount, 0, player)
			akCtl.ApplyUtil(5, amount, 0, player)
			If akCtl.CachedDebugLevel >= 2
				akCtl.LogThrottled(2, "node", "common feedback stage=" + aiStage + " amount=" + amount)
			EndIf
		EndIf
	EndIf
EndFunction

; ================================================================== 通用樹：附傷倍率

; 5.2 開啟新手／開啟大師（所有元素附傷 +1%／點 ×2 階）、
; 持續熟練（二段 +1%／點）、持續大師（三段重擊 +2%／點）。
Float Function CommonHitMult(ESSBController akCtl, Int aiElement, Bool abPower) Global
	Float mult = 1.0 + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 1, 0), 0.01) + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 1, 3), 0.01) ; @node 所有元素附傷, 所有元素附傷再
	Int stage = akCtl.SyncStage()
	If stage >= 2
		mult = mult + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 0, 1), 0.01) ; @node 同調二段時附傷
	EndIf
	If stage >= 3 && abPower
		mult = mult + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 0, 3), 0.02) ; @node 同調三段時重擊附傷
	EndIf
	Return mult
EndFunction

; 5.2 關閉新手 +1%／點、關閉大師再 +1%／點。終焉與融斷都吃。
; （持續專精主線「同調三段時終焉 +1%／點」是 DLL N3，v0.3 的「同調三段時受傷 -0.5%／點」已拿掉。）
Float Function CommonEndMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 2, 0), 0.01) + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 2, 3), 0.01) ; @node 終焉, 終焉再
EndFunction

; 5.2 關閉熟練 融斷 +1%／點、關閉傳奇 再 +2%／點。
Float Function CommonBurstMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 2, 1), 0.01) + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 2, 4), 0.02) ; @node 融斷, 融斷再
EndFunction

; ================================================================== 通用樹：狀態上限與萬象

; 5.2 開啟傳奇主線：每種元素狀態上限 +1 層／每 5 點，最多 +3（規劃 2.3）。
Int Function StatusCapBonus(ESSBController akCtl) Global
	Int bonus = Rank(akCtl, 12, 1, 4) / 5 ; @node 每種元素狀態上限
	If bonus > 3
		bonus = 3
	EndIf
	Return bonus
EndFunction

; 5.2 開啟傳奇分支「萬象」：所有元素狀態的層數效果 +25%。
Float Function OmniMult(ESSBController akCtl) Global
	If Br(akCtl, 12, 1, 4, 0) ; @node 萬象
		Return 1.25
	EndIf
	Return 1.0
EndFunction

; ================================================================== 通用樹：印記與開印

; 5.2 開啟熟練主線：印記持續 +0.2 秒／點。回傳「額外秒數」（四捨五入到整數秒，
; SetNthEffectDuration 只吃整數）。
Int Function MarkDurationBonus(ESSBController akCtl) Global
	Float extra = 0.2 * Rank(akCtl, 12, 1, 1) ; @node 印記持續
	Return (extra + 0.5) as Int
EndFunction

; 5.2 開啟熟練分支「先制」（開印 +2 同調）與開啟專精主線（+1 同調／每 5 點）。
Int Function OpenSyncBonus(ESSBController akCtl) Global
	Int gain = Rank(akCtl, 12, 1, 2) / 5 ; @node 開印時
	If Br(akCtl, 12, 1, 1, 1) ; @node 先制
		gain += 2
	EndIf
	Return gain
EndFunction

; v0.3 的開啟新手分支「廣印」與開啟大師分支「深印」（開印那一擊 ×1.5）v0.4 已移除
; （同格改為「跳印」「印潮」，DLL N3／N5）。

; 5.2 開啟專精分支「雙印」：目標可同時帶兩種元素印記。
Bool Function HasDualMark(ESSBController akCtl) Global
	Return Br(akCtl, 12, 1, 2, 0) ; @node 雙印
EndFunction

; 5.2 關閉熟練分支「疊印」：終焉後舊印記保留 4 秒為副印記。
Bool Function HasResidualMark(ESSBController akCtl) Global
	Return Br(akCtl, 12, 2, 1, 1) ; @node 疊印
EndFunction

; 5.2 開啟大師分支「臨界」：開形態那一刻附近敵人減速 30% 2 秒。
Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	If !Br(akCtl, 12, 1, 3, 1) ; @node 臨界
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			akCtl.ApplyUtil(0, 30.0, 2, nearby[index])
		EndIf
		index += 1
	EndWhile
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "common threshold slow element=" + aiElement)
	EndIf
EndFunction

; ================================================================== 通用樹：終焉週邊

; 5.2 關閉熟練分支「反哺」：每次終焉回復你 B_max 魔力。
Function OnEndReward(ESSBController akCtl, Int aiElement) Global
	If !Br(akCtl, 12, 2, 1, 0) ; @node 反哺
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If player
		akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement), 0, player)
	EndIf
EndFunction

; 5.2 關閉專精分支「三重奏」：10 秒內觸發三種不同元素的終焉，第三次 ×3，
; 且下一次融斷後保留全部同調。回傳這一次的額外倍率。
Float Function TrioMult(ESSBController akCtl, Int aiElement) Global
	If !Br(akCtl, 12, 2, 2, 1) ; @node 三重奏
		Return 1.0
	EndIf
	Int count = akCtl.PushTrio(aiElement)
	If count >= 3
		akCtl.SetSyncKeepAll()
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "common trio element=" + aiElement + " x3")
		EndIf
		Return 3.0
	EndIf
	Return 1.0
EndFunction

; 5.2 關閉大師分支「協奏」：切換後首次終焉傷害 ×1.5。
Float Function ConcertMult(ESSBController akCtl) Global
	If Br(akCtl, 12, 2, 3, 0) && akCtl.TakeSwitchEnd() ; @node 協奏
		Return 1.5
	EndIf
	Return 1.0
EndFunction

; 5.2 關閉專精分支「連鎖終焉」：終焉時附近帶同一印記的目標也終焉 ×0.5。
Bool Function HasChainEnd(ESSBController akCtl) Global
	Return Br(akCtl, 12, 2, 2, 0) ; @node 連鎖終焉
EndFunction

; 5.2 關閉傳奇分支「大協奏」：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次終焉。
Bool Function HasGrandConcert(ESSBController akCtl) Global
	Return Br(akCtl, 12, 2, 4, 0) ; @node 大協奏
EndFunction

; 5.2 關閉新手分支「餘響」：切換後首次命中附帶前一元素 50% 附傷；
; 關閉專精主線：切換後首次命中附帶前一元素附傷 +3%／點。
; 回傳這一次附帶的比例（0 代表不附帶）。
Float Function EchoRatio(ESSBController akCtl) Global
	Float ratio = 0.0
	If Br(akCtl, 12, 2, 0, 0) ; @node 餘響
		ratio = 0.5
	EndIf
	ratio = ratio + ESSBNodes.Pct(akCtl, Rank(akCtl, 12, 2, 2), 0.03) ; @node 切換後首次命中附帶前一元素附傷
	Return ratio
EndFunction

; 5.2 持續大師分支「極致」：同調三段時每 10 次命中額外一次全額附傷。
Bool Function HasExtreme(ESSBController akCtl) Global
	Return Br(akCtl, 12, 0, 3, 0) ; @node 極致
EndFunction


; 5.2 持續傳奇分支「永續」：Z 關閉時若同調三段，融斷後保留一段同調。
Bool Function HasPerpetual(ESSBController akCtl) Global
	Return Br(akCtl, 12, 0, 4, 0) ; @node 永續
EndFunction

; 5.2 持續專精分支「定神」：同調三段時免疫減速（自有）。
; 冰原「你在其中免疫減速」走同一個守衛函式（5.4 關閉傳奇分支）。
Bool Function SelfSlowImmune(ESSBController akCtl) Global
	If Br(akCtl, 12, 0, 2, 0) && akCtl.SyncStage() >= 3 ; @node 定神
		Return True
	EndIf
	; 5.7 風持續傳奇分支「御風」：同調三段時免疫減速（自有）。
	If ESSBElem2.WindSlowImmune(akCtl)
		Return True
	EndIf
	Return akCtl.PlayerInDomain(2)
EndFunction

; 5.2 關閉傳奇分支「雙生」：雙持時左手武器攜帶你前一個形態的元素 30 秒。
Bool Function HasTwin(ESSBController akCtl) Global
	Return Br(akCtl, 12, 2, 4, 1) ; @node 雙生
EndFunction
