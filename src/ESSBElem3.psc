Scriptname ESSBElem3 Hidden
{毒素（5.10）、水（5.11）、黑暗（5.12）、星界（5.13）四棵元素樹的節點效果。

樹索引 7 毒、8 水、9 暗、10 星（元素編號 8／9／10／11）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）／ESSBElem2（土風血聖）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

Round 22（N3）起，中毒（一顆成長的持續傷）、瘴氣、催毒、浸濕、水壓與沖刷、詛咒與幻覺階梯、死咒引信、星痕、共鳴、
星鎖都是 DLL 掛的引擎效果（native/include/Status.h）；round 24（N5）起開印與終焉的本體、各樹分支、臨強化、
星落、中毒死亡擴散、亡者歸來的判定都在 DLL（native/include/Reactions.h）；round 25（N6）起長流、長河與領域也在 DLL
的計時器（native/include/Timer.h）。這裡只剩毒形態的每秒效果（以毒攻毒、百毒不侵）、常駐能力的判定與幻術等級上限。
留在 Papyrus 的機制：
  水（5.11）洗淨／淨化走「限定關鍵字的 Dispel 原型」；長流（每秒百分比回復）與沖刷（開印沖刷、洗滌、潮池）在 DLL。
  暗（5.12）恐懼與瘋狂用自有 Demoralize（原型 7）／Frenzy（原型 8）效果，
      magnitude 就是等級上限（同原版幻術），首領、龍、亡靈魔族與機械免疫（DLL 送 ESSB_Hallucinate，這裡施放）。}



; ================================================================== 水
; 5.11 長流（每秒回復生命、耐力與維持費 80% 的魔力）與長河（同伴）round 25（N6）起在 DLL 計時器（Timer.h PlanFormSecond）。


; 導引的同調跳段（v0.4 2.6：同調立即跳到下一段門檻）round 23 起在 DLL（Status.h PlanEndSelf）。

; ================================================================== 暗：幻術


; 恐懼與瘋狂的等級上限（同原版幻術：magnitude 就是可影響的最高等級）。
; 基礎 10 級，暗樹每級 +1，所以 100 級的暗樹可影響 110 級以下的目標。
Int Function CharmCap(ESSBController akCtl) Global
	Int level = 1
	If akCtl.Trees
		level = akCtl.Trees.TreeLevel(9)
	EndIf
	Return 10 + level
EndFunction

; 亡者歸來（規劃 5.12 表 + 8）的判定（階、等級上限、秒數、殘魂、冥召、死靈主）round 24 起在 DLL 的死亡 sink；
; 復生的施放、召喚上限與不可復生名單在 ESSBController.OnESSBRaise → CanReanimate／ApplyReanimate。

; ================================================================== 每秒與擊殺

Function OnTick(ESSBController akCtl, Int aiElement) Global
	If aiElement == 8
		PoisonFormTick(akCtl)
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
		If nearby[index] && ESSBNative.GetStatus(nearby[index], 7) > 0
			heal = heal + 6.0
		EndIf
		index += 1
	EndWhile
	If heal > 0.0
		akCtl.ApplyUtil(4, heal, 0, player)
	EndIf
EndFunction


; ================================================================== 常駐能力與守衛
; 擊殺掛勾（蔓延、亡魂、亡衛、狂宴、亡者歸來）round 24 起是 DLL 的死亡處理；星的「星輝」、暗的「影身」已退役。

; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%（自有常駐能力，開形態才掛）。
Bool Function HasPoisonImmunity(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 7, 0, 0, 0) ; @node 免疫
EndFunction

; 5.10 持續熟練分支「毒皮」（被近戰命中時攻擊者中毒 +2 劑）round 23 起在 DLL 受擊（Hurt.h）。
