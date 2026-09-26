Scriptname ESSBElem Hidden
{火（5.3）、冰（5.4）、雷（5.5）三棵元素樹的節點效果。

樹索引 0 火、1 冰、2 雷（元素編號 1／2／3）。路線 0 持續、1 開啟、2 關閉。
其餘八棵元素樹照同一組函式名稱：元素 4–7（土風血聖）在 ESSBElem2、元素 8–11（毒水暗星）在 ESSBElem3。

Round 22（N3）起，熱度（你身上的階）、凍結量表、冰晶、碎冰、印記時長、開印與命中的層數都是 DLL 的事
（native/include/Status.h）；round 24（N5）起開印與終焉的本體、節點、範圍掃描、爆燃、放電、冰封與碎冰之後、
火臨／冰臨／雷臨也都在 DLL（native/include/Reactions.h，裁定 R4），這裡只剩火命中的火抗削減（Papyrus 負責）
與開形態的附加效果分派（氣旋、聖臨強化留在 Papyrus）。}

; ================================================================== 自身資源上限

; 冰 凍結量表固定 5（量表不吃萬象，規劃 2.3）。
Int Function FreezeCap() Global
	Return 5
EndFunction

; 開印時你的資源（電荷、岩甲、風勢、同調、共鳴層）round 23 起由 DLL 在開印那一擊加（SelfLayer.h OpenGains）。

; ================================================================== 開形態

; 火臨／冰臨／雷臨（與所有元素的「臨」、臨強化、臨界、雙斷的再開印）round 24 起在 DLL（FormEnter：PlanAdvent）。

; 「臨」的範圍：2 公尺 +0.2 公尺／點（該元素開啟大師主線；沒投點就是 2 公尺）。臨強化類分支的「範圍內」用同一個範圍。
Float Function AdventRadiusOf(ESSBController akCtl, Int aiElement) Global
	Int tree = ESSBNodes.TreeOf(aiElement)
	Int rank = ESSBNodes.Rank(akCtl, tree, 1, 3) ; @node *臨{fire frost lightning wind blood divine poison water darkness astral} / 地臨{earth}
	Return (2.0 + 0.2 * rank) * 70.0
EndFunction

; 開形態留在 Papyrus 的附加效果：氣旋（推力）、聖臨強化（你與同伴的治療）。即使沒投主線（沒有「臨」）也生效。
Function OnFormOpenedExtra(ESSBController akCtl, Int aiElement) Global
	If aiElement == 5 || aiElement == 7
		ESSBElem2.OnFormOpened(akCtl, aiElement)
	EndIf
EndFunction

; 爆燃、冰封與碎冰之後、放電與跳躍、各終焉分支、擊殺掛勾（連鎖冰封、火葬）round 24 起在 DLL（Reactions.h）。

; ================================================================== 每秒與擊殺掛勾

; 冰（冰心：受擊後生命低於 30%）與雷（雷神：電荷滿層的那一擊）的每秒掛勾 round 23 起在 DLL（Hurt.h、SelfLayer.h）。
Function OnTick(ESSBController akCtl, Int aiElement) Global
EndFunction

; 5.3 持續專精主線：帶火印記目標火抗 -1%／點（命中火印記目標時）。
Function ApplyFireResistShred(ESSBController akCtl, Actor akTarget) Global
	Int rank = ESSBNodes.Rank(akCtl, 0, 0, 2) ; @node 帶火印記目標火抗
	If rank <= 0 || !akCtl.HasElementMark(akTarget, 1)
		Return
	EndIf
	akCtl.ApplyUtil(13, rank as Float, 6, akTarget)
EndFunction
