Scriptname ESSBNoForm Hidden
{無元素樹「法殺」（規劃 v0.4 第 5.1 節）與真實傷害類別（2.8）。

三條路線：0 大師、1 滅法、2 冷寂。大師與滅法只在未開形態時生效；冷寂作用在元素形態的融斷。
弓弩的「重擊」由潛行射擊取代（控制器已在 OnWeaponHit 換算好 abPower）。

v0.4 的無元素命中（基準真傷、吸魔、小滅法、滅法、滅法印、沉默，以及吸魔量、奪魔、滅法倍率、燒魔倍數、枯竭、
靜寂、燒魔 +5%、低魔增傷、噬命、寂滅）由 DLL 在命中當下計算並施放（round 20 N2、round 21）；斷咒、反咒、戰意、
超載、法盾、化法為力、逼近、咒返、不屈、餘魔、破護、反擊 round 23（N4）起也在 DLL。
這裡只剩真傷倍率、施法判定與冷寂的免門檻／連斷（round 24 起冷寂的其餘節點在 DLL）。
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

; 融斷結束後：免門檻、連斷（開形態的代價與同調保留，Papyrus 負責）。
; round 24（N5）：冷寂路線的融斷倍率、範圍、寂（燒魔、上限、萬寂）、斷界、回流、雙斷都在 DLL（Reactions.h PlanBurst，
; 雙斷的再開印在 FormEnter 的 PlanAdvent）。
Function OnBurst(ESSBController akCtl, Int aiSyncBefore) Global
	; 新手分支「免門檻」：融斷後下一次開形態不需魔力。
	If ESSBNodes.Br(akCtl, 11, 2, 0, 0) ; @node 免門檻
		akCtl.SetFreeOpen(1)
	EndIf

	; 專精分支「連斷」：融斷後 5 秒內重開任一形態，保留一半同調。
	If ESSBNodes.Br(akCtl, 11, 2, 2, 0) ; @node 連斷
		akCtl.SetSyncKeep(aiSyncBefore / 2, 5)
	EndIf
EndFunction

