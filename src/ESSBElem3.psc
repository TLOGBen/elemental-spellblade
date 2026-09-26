Scriptname ESSBElem3 Hidden
{毒素（5.10）、水（5.11）、黑暗（5.12）、星界（5.13）四棵元素樹的節點效果。

樹索引 7 毒、8 水、9 暗、10 星（元素編號 8／9／10／11）。路線 0 持續、1 開啟、2 關閉。
函式名與 ESSBElem（火冰雷）／ESSBElem2（土風血聖）一一對應，由 ESSBElem 依元素分派過來，
共通框架（G(L)、M_mod、開印／終焉倍率、狀態上限、印記時長）完全不必改。

Round 22（N3）起，中毒（一顆成長的持續傷）、瘴氣、催毒、浸濕、水壓與沖刷、詛咒與幻覺階梯、死咒引信、星痕、共鳴、
星鎖都是 DLL 掛的引擎效果（native/include/Status.h）；round 24（N5）起開印與終焉的本體、各樹分支、臨強化、
星落、中毒死亡擴散、亡者歸來的判定都在 DLL（native/include/Reactions.h）。這裡只剩每秒的形態效果（以毒攻毒、
百毒不侵、長流、長河）、常駐能力的判定、幻術等級上限與 Papyrus 自己的傷害（領域）用的目標倍率。
留在 Papyrus 的機制：
  水（5.11）長流是每秒百分比回復（規劃 8：自有效果，不動回復速率 AV），
      洗淨／淨化走「限定關鍵字的 Dispel 原型」，沖刷（開印沖刷、洗滌、潮池）走 DLL 的精確判定（ESSBNative.WashBuffs，裁定 R5）。
  暗（5.12）恐懼與瘋狂用自有 Demoralize（原型 7）／Frenzy（原型 8）效果，
      magnitude 就是等級上限（同原版幻術），首領、龍、亡靈魔族與機械免疫（DLL 送 ESSB_Hallucinate，這裡施放）。}


; ================================================================== Papyrus 自己的傷害（領域）的目標倍率

; 5.13 開啟大師分支「星鎖」（開印目標 3 秒內受所有元素傷 +10%）與關閉傳奇分支「星域」（內部敵人受所有元素傷 +20%）。
; 決定 61：攻擊類進入點讀不到目標，所以這兩條只放大本模組造成的傷害。
; v0.4 暗的持續專精主線是「幻覺持續」（DLL N3），v0.3 的「詛咒滿層目標受所有傷害 +1%／點」已拿掉。
Float Function TargetDamageMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If !akTarget
		Return mult
	EndIf
	; 只給 Papyrus 反應本體的傷害（ApplyDamage）；附傷的同一項由 DLL 讀。
	If ESSBNodes.Br(akCtl, 10, 1, 3, 0) && ESSBNative.GetStatus(akTarget, 15) > 0 ; @node 星鎖
		mult = mult * 1.1
	EndIf
	If ESSBNodes.Br(akCtl, 10, 2, 4, 0) && akCtl.InDomain(akTarget, 11) ; @node 星域
		mult = mult * 1.2
	EndIf
	Return mult
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
		If nearby[index] && ESSBNative.GetStatus(nearby[index], 7) > 0
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
; 擊殺掛勾（蔓延、亡魂、亡衛、狂宴、亡者歸來）round 24 起是 DLL 的死亡處理；星的「星輝」、暗的「影身」已退役。

; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%（自有常駐能力，開形態才掛）。
Bool Function HasPoisonImmunity(ESSBController akCtl) Global
	Return ESSBNodes.Br(akCtl, 7, 0, 0, 0) ; @node 免疫
EndFunction

; 5.10 持續熟練分支「毒皮」（被近戰命中時攻擊者中毒 +2 劑）round 23 起在 DLL 受擊（Hurt.h）。
