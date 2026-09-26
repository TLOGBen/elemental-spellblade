Scriptname ESSBElem2 Hidden
{大地（5.6）、風（5.7）、鮮血（5.8）、神聖（5.9）四棵元素樹的節點效果。

Round 22（N3）起，裂痕、倒地、失衡、血痕、聖印、聖佑與聖裁計數是 DLL 掛的引擎效果（native/include/Status.h）；
round 24（N5）起開印與終焉的本體、地震、風刃、吹飛、血潮、裁決、化灰的回饋、擊殺掛勾都在 DLL
（native/include/Reactions.h）。這裡只剩上限與門檻的讀值、氣旋與聖臨強化（開形態）、同伴治療、風形態的移速與潛行、
Papyrus 自己的傷害（領域）用的目標倍率。

樹索引 3 土、4 風、5 血、6 聖（元素編號 4／5／6／7）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

物理推力（跌倒、拉近、吹飛、吹上天）一律走 ESSBController 的 Knockdown／PullIn／BlowBack／LiftUp（DLL 決定推誰、推多遠，
經 ESSB_Push／ESSB_Knock 送來；裁定 R4：推力留 Papyrus），四者都在控制器裡做每目標冷卻與免疫名單。}

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


; 開印的岩甲（+2，岩膚 +4，開啟新手主線 +1／每 5 點）與風勢（+2，疾風痕直接滿）round 23 起在 DLL（SelfLayer.h）。


; ================================================================== 每次命中（元素專屬）

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

; ================================================================== 開形態（各元素的「臨」的附加效果）

Function OnFormOpened(ESSBController akCtl, Int aiElement) Global
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	; 5.6 地臨強化（岩甲滿層與範圍內敵人耐力 -50%）round 24 起都在 DLL（FormEnter：PlanSelfEnter、PlanAdvent）。
	If aiElement == 5
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
	; 5.8 血臨強化（付最大生命 15% 並濺血一次）round 24 起在 DLL（PlanAdvent）。
	ElseIf aiElement == 7
		; 5.9 開啟專精分支「聖臨強化」：聖臨時你與附近同伴回血 B_max ×2（聖 B_max 10 → 20；v0.4 這一格沒有 G(L)）。
		If ESSBNodes.Br(akCtl, 6, 1, 2, 0) ; @node 聖臨強化
			Float heal = akCtl.BaseMax(7) * 2.0
			akCtl.ApplyUtil(4, heal, 0, player)
			HealAllies(akCtl, heal)
		EndIf
	EndIf
EndFunction

; ================================================================== 土：地震

; 5.6 持續大師分支「反震」round 23 起由 DLL 在受擊時結算（土傷、清空岩甲、10 秒冷卻；推力經 ESSB_Knock 回來）。

; ================================================================== 風：風刃、吹飛、吹上天

; 風勢到門檻送出風刃並歸零（規劃 2.3）round 23 起由 DLL 判定（ESSB_Blade）。

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


