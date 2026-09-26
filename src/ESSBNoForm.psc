Scriptname ESSBNoForm Hidden
{無元素樹「法殺」（規劃 v0.4 第 5.1 節）與真實傷害類別（2.8）。

三條路線：0 大師、1 滅法、2 冷寂。大師與滅法只在未開形態時生效；冷寂作用在元素形態的融斷。
弓弩的「重擊」由潛行射擊取代（控制器已在 OnWeaponHit 換算好 abPower）。

v0.4 的無元素命中（基準真傷、吸魔、小滅法、滅法、滅法印、沉默，以及吸魔量、奪魔、滅法倍率、燒魔倍數、枯竭、
靜寂、燒魔 +5%、低魔增傷、噬命、寂滅）由 DLL 在命中當下計算並施放（round 20 N2、round 21）；斷咒、反咒、戰意、
超載、法盾、化法為力、逼近、咒返、不屈、餘魔、破護、反擊 round 23（N4）起也在 DLL。
這裡只剩 v0.3 融斷路線沿用下來的節點（冷寂 N5 前）與真傷倍率。
v0.3 的純武藝路線（重擊碎甲、暴擊率、戰意武器傷害、終結、節奏、處決……）在 v0.4 已整條換成大師路線（多為 N4），
其效果在 round 21 拿掉。

真實傷害（2.8）：D_true = 基準 × G(L_無元素) × M_mod(無元素樹)。
走自有的 ESSB_TrueSpell（Resist Value = None、不掛學派、只掛 ESSB_TrueDamage keyword），
執行期 SetNthEffectMagnitude 後 DoCombatSpellApply，是本模組唯一允許扣生命的路徑。

破魔印是掛在目標身上的自有 MGEF（ESSBCounter），沉默與反咒以它為條件（2.3）。}

Int Function TREE() Global
	Return 11
EndFunction

; ================================================================== 真實傷害（2.8）

; M_mod(無元素樹)：滅法傳奇主線（目標魔力 <25% 時命中傷害 +3%／點）。Papyrus 這一側只剩反咒等真傷在用；
; 命中的真傷由 DLL 算同一條主線。
Float Function TrueMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If akTarget && akTarget.GetActorValuePercentage("Magicka") < 0.25
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 1, 4), 0.03) ; @node 目標魔力低於 25% 時命中傷害
	EndIf
	Return mult
EndFunction

; ================================================================== 滅法（route 1）

; 熟練分支「斷咒」round 23 起在 DLL：命中當下讀目標的施法狀態、打斷、每 5 秒一次、戰意 +1（SelfLayer.h PlanSelfNoForm）。

; 施法者／帶魔法護盾或元素披風：只讀原版關鍵字與裝備欄，不讀其他模組的狀態。
Bool Function IsSpellUser(ESSBController akCtl, Actor akTarget) Global
	If akTarget.GetEquippedSpell(0) || akTarget.GetEquippedSpell(1)
		Return True
	EndIf
	If akCtl.ArmorSpellKeyword && akTarget.HasMagicEffectWithKeyword(akCtl.ArmorSpellKeyword)
		Return True
	EndIf
	If akCtl.CloakKeyword && akTarget.HasMagicEffectWithKeyword(akCtl.CloakKeyword)
		Return True
	EndIf
	Return False
EndFunction

Bool Function IsCasting(Actor akTarget) Global
	If !akTarget
		Return False
	EndIf
	; Actor.psc: 0 left, 1 right, 2 other, 3 instant (powers).
	Int source = 0
	While source < 4
		Spell magicItem = akTarget.GetEquippedSpell(source)
		If magicItem && PO3_SKSEFunctions.IsCasting(akTarget, magicItem)
			Return True
		EndIf
		source += 1
	EndWhile
	Form voice = akTarget.GetEquippedShout()
	Return voice && PO3_SKSEFunctions.IsCasting(akTarget, voice)
EndFunction

; 熟練分支「反咒」round 23 起在 DLL 的施法事件（施法者帶破魔印時，受該次施法消耗魔力 ×（100% +2%／無元素樹等級）的
; 真實傷害、戰意 +1；Hurt.h PlanSpellCast，裁定 R7）。

; ================================================================== 冷寂（route 2）

; 新手主線「融斷 +2%／點」、傳奇主線「融斷再 +3%／點」。與通用樹的融斷倍率相乘。
Float Function BurstMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 2, 0), 0.02) + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 2, 4), 0.03) ; @node 融斷, 融斷再
EndFunction

; 專精主線：融斷範圍 +0.3 公尺／點；熟練分支「收束」：15 → 20 公尺。
Float Function BurstRadius(ESSBController akCtl) Global
	Float metres = 15.0
	If ESSBNodes.Br(akCtl, 11, 2, 1, 0) ; @node 收束
		metres = 20.0
	EndIf
	metres = metres + 0.3 * ESSBNodes.Rank(akCtl, 11, 2, 2) ; @node 融斷範圍
	Return metres * 70.0
EndFunction

; 融斷結束後：免門檻、連斷、回流、雙斷。
; v0.4 冷寂路線的熟練主線是「寂每層燒魔」、大師主線是「寂上限」（寂是 DLL N5），v0.3 的「餘燼」「淬火」
; 與已退役的「餘燼延續」已拿掉。
Function OnBurst(ESSBController akCtl, Int aiElement, Int aiMarks, Int aiSyncBefore) Global
	; 新手分支「免門檻」：融斷後下一次開形態不需魔力。
	If ESSBNodes.Br(akCtl, 11, 2, 0, 0) ; @node 免門檻
		akCtl.SetFreeOpen(1)
	EndIf

	; 專精分支「連斷」：融斷後 5 秒內重開任一形態，保留一半同調。
	If ESSBNodes.Br(akCtl, 11, 2, 2, 0) ; @node 連斷
		akCtl.SetSyncKeep(aiSyncBefore / 2, 5)
	EndIf

	; 大師分支「回流」：融斷回復你魔力，每個印記 B_max ×0.5。
	If ESSBNodes.Br(akCtl, 11, 2, 3, 1) && aiMarks > 0 ; @node 回流
		Actor player = akCtl.ThePlayer()
		If player
			akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 0.5 * aiMarks, 0, player)
		EndIf
	EndIf

	; 傳奇分支「雙斷」：融斷後 3 秒內再次按 Z 開任一形態，對範圍內敵人立即開印一次。
	If ESSBNodes.Br(akCtl, 11, 2, 4, 0) ; @node 雙斷
		akCtl.SetDoubleBurst(3)
	EndIf
EndFunction

