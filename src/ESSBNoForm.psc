Scriptname ESSBNoForm Hidden
{無元素樹（規劃 v0.3 第 5.1 節）與真實傷害類別（2.8）。

三條路線：0 純武藝、1 破魔、2 融斷。適用未開啟任何形態時的近戰、拳腳、弓、弩；
弓弩的「重擊」由潛行射擊取代（控制器已在 OnWeaponHit 換算好 abPower）。

Round 20（N2）：v0.4 的無元素命中（基準真傷、吸魔、小滅法、滅法、滅法印、沉默，以及奪魔、枯竭、靜寂、
燒魔 +5%、低魔增傷、噬命這些節點）由 DLL 在命中當下計算並施放；v0.3 的「破魔」主線那一段隨之刪除。
這裡只剩 DLL 還沒接手的：純武藝（v0.3 節點）、斷咒（N4）、反咒（N4）、無魔、融斷路線。

真實傷害（2.8）：D_true = 基準 × G(L_無元素) × M_mod(無元素樹)。
走自有的 ESSB_TrueSpell（Resist Value = None、不掛學派、只掛 ESSB_TrueDamage keyword），
執行期 SetNthEffectMagnitude 後 DoCombatSpellApply，是本模組唯一允許扣生命的路徑。

破魔印是掛在目標身上的自有 MGEF（ESSBCounter），沉默與反咒以它為條件（2.3）。}

Int Function TREE() Global
	Return 11
EndFunction

; 武器基準傷害：拳腳讀玩家的 UnarmedDamage，其餘讀武器的基礎傷害。
; 暴擊、終結、處決都以它為基準，不讀任何外部模組的武器數值。
Float Function WeaponBase(ESSBController akCtl, Weapon akWeapon) Global
	If akWeapon
		Return akWeapon.GetBaseDamage()
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return 0.0
	EndIf
	Float unarmed = player.GetActorValue("UnarmedDamage")
	If unarmed < 4.0
		unarmed = 4.0
	EndIf
	Return unarmed
EndFunction

; ================================================================== 真實傷害（2.8）

; M_mod(無元素樹)：破魔傳奇主線（目標魔力 <25% 時 +3%／點）與靜寂分支在呼叫端另乘。
Float Function TrueMult(ESSBController akCtl, Actor akTarget) Global
	Float mult = 1.0
	If akTarget && akTarget.GetActorValuePercentage("Magicka") < 0.25
		mult = mult + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 1, 4), 0.03)
	EndIf
	Return mult
EndFunction

; ================================================================== 純武藝（route 0）

; 每次無形態有效命中。abPower 已含「潛行射擊視為重擊」。
Function OnMartialHit(ESSBController akCtl, Actor akTarget, Weapon akWeapon, Bool abPower, Float afRiposte = 1.0) Global
	Float base = WeaponBase(akCtl, akWeapon) * afRiposte

	; 熟練主線「重擊碎甲」：自有減防 1%／點，5 秒（破勢分支改 8 秒）。
	Int shred = ESSBNodes.Rank(akCtl, 11, 0, 1)
	If abPower && shred > 0
		Int duration = 5
		If ESSBNodes.Br(akCtl, 11, 0, 3, 0)
			duration = 8
		EndIf
		Float armorCut = akTarget.GetActorValue("DamageResist") * 0.01 * shred
		If armorCut > 0.0
			akCtl.ApplyUtil(1, armorCut, duration, akTarget)
		EndIf
	EndIf

	; 專精主線「暴擊率 +1%／點（自有判定）」：自有擲骰，命中就補一次武器基準的真實傷害。
	Int crit = ESSBNodes.Rank(akCtl, 11, 0, 2)
	If crit > 0 && Utility.RandomFloat(0.0, 1.0) < 0.01 * crit
		akCtl.ApplyTrueDamage(base, akTarget, 11, False)
		If akCtl.CachedDebugLevel >= 2
			akCtl.LogThrottled(2, "node", "noform crit base=" + base)
		EndIf
	EndIf

	Int resolve = akCtl.GetResolve()

	; 傳奇主線「終結」：戰意滿層重擊無視護甲 +3%／點。
	; 護甲穿透沒有可靠的原版進入點索引，改以等量的真實傷害表達「無視護甲」（見實作紀錄）。
	Int finisher = ESSBNodes.Rank(akCtl, 11, 0, 4)
	If abPower && resolve >= 5 && finisher > 0
		akCtl.ApplyTrueDamage(base * ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 0, 4), 0.03), akTarget, 11, False)
	EndIf

	; 傳奇分支「處決」：戰意滿層重擊對低於 25% 生命的目標傷害 ×3，消耗全部戰意。
	If abPower && resolve >= 5 && ESSBNodes.Br(akCtl, 11, 0, 4, 0)
		If akTarget.GetActorValuePercentage("Health") < 0.25
			akCtl.ApplyTrueDamage(base * 2.0, akTarget, 11, False)
			akCtl.ClearResolve()
			If akCtl.CachedDebugLevel >= 1
				akCtl.LogThrottled(1, "node", "noform execute " + akTarget.GetFormID())
			EndIf
		EndIf
	EndIf
EndFunction

; 專精分支「節奏」：4 秒內連續命中 3 次，回復耐力並 +1 戰意（最多 5）。
Function OnCombo(ESSBController akCtl, Int aiHits) Global
	If aiHits < 3 || !ESSBNodes.Br(akCtl, 11, 0, 2, 0)
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If player
		akCtl.ApplyUtil(6, 60.0 * akCtl.GLevel(11), 0, player)
	EndIf
	akCtl.AddResolve(1)
	If akCtl.CachedDebugLevel >= 2
		akCtl.LogThrottled(2, "node", "noform rhythm resolve=" + akCtl.GetResolve())
	EndIf
EndFunction

; ================================================================== 破魔（route 1）

; 熟練分支「斷咒」：命中施法中的敵人打斷其施法，每 5 秒一次（v0.4 列為 DLL N4，到那時才搬）。
; round 20 前它掛在破魔主線裡、要先有破魔點數才生效；破魔主線在 N2 由 DLL 的吸魔／滅法取代後，
; 斷咒只看自己的分支。
Function OnInterruptCast(ESSBController akCtl, Actor akTarget, Bool abHitCasting) Global
	If !abHitCasting || !ESSBNodes.Br(akCtl, 11, 1, 1, 0)
		Return
	EndIf
	If akCtl.TakeInterrupt()
		; 低衝突原則（6）：不用麻痺與硬直。把魔力清空並給 1 秒沉默，
		; NPC 沒有魔力就會中止並改用近戰，效果等同打斷。
		akCtl.ApplyUtil(2, akTarget.GetActorValue("Magicka") + 1.0, 0, akTarget)
		akCtl.ApplySilenceSpell(akTarget, 1)
		If akCtl.CachedDebugLevel >= 1
			akCtl.LogThrottled(1, "node", "noform interrupt " + akTarget.GetFormID())
		EndIf
	EndIf
EndFunction

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

; 反咒（熟練分支 B2，由 ESSBCounter 在目標施法的動畫事件上呼叫）：
; 受其該次施法消耗魔力 100% 的真實傷害，每無元素樹等級 +2%，100 級為 300%。
Function OnCounterSpell(ESSBController akCtl, Actor akTarget, Float afCost) Global
	If afCost <= 0.0 || !ESSBNodes.Br(akCtl, 11, 1, 1, 2)
		Return
	EndIf
	Int level = 1
	If akCtl.Trees
		level = akCtl.Trees.TreeLevel(11)
	EndIf
	Float ratio = 1.0 + 0.02 * level
	; Tree/branch queries yield too: expiry still wins immediately before damage.
	If !akCtl.IsOperational() || !akCtl.CounterEligible(akTarget)
		Return
	EndIf
	akCtl.ApplyTrueDamage(afCost * ratio, akTarget)
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "noform counter " + akTarget.GetFormID() + " cost=" + afCost + " ratio=" + ratio)
	EndIf
EndFunction

; 傳奇分支「無魔」：擊殺施法者回滿耐力與魔力。由控制器在登記格清除時判定。
Function OnKill(ESSBController akCtl, Actor akTarget, Bool abWasSpellUser) Global
	If !abWasSpellUser || !ESSBNodes.Br(akCtl, 11, 1, 4, 0)
		Return
	EndIf
	Actor player = akCtl.ThePlayer()
	If !player
		Return
	EndIf
	akCtl.ApplyUtil(5, player.GetActorValueMax("Magicka"), 0, player)
	akCtl.ApplyUtil(6, player.GetActorValueMax("Stamina"), 0, player)
	If akCtl.CachedDebugLevel >= 1
		akCtl.LogThrottled(1, "node", "noform nomagic refill")
	EndIf
EndFunction

; ================================================================== 融斷（route 2）

; 新手 +2%／點、傳奇再 +3%／點。與通用樹的融斷倍率相乘。
Float Function BurstMult(ESSBController akCtl) Global
	Return 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 2, 0), 0.02) + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 2, 4), 0.03)
EndFunction

; 專精主線：融斷範圍 +0.3 公尺／點；熟練分支「收束」：15 → 20 公尺。
Float Function BurstRadius(ESSBController akCtl) Global
	Float metres = 15.0
	If ESSBNodes.Br(akCtl, 11, 2, 1, 0)
		metres = 20.0
	EndIf
	metres = metres + 0.3 * ESSBNodes.Rank(akCtl, 11, 2, 2)
	Return metres * 70.0
EndFunction

; 融斷結束後：免門檻、連斷、淬火、餘燼、回流、斷界、雙斷。
Function OnBurst(ESSBController akCtl, Int aiElement, Int aiMarks, Int aiSyncBefore) Global
	; 新手分支「免門檻」：融斷後下一次開形態不需魔力。
	If ESSBNodes.Br(akCtl, 11, 2, 0, 0)
		akCtl.SetFreeOpen(1)
	EndIf

	; 熟練主線「餘燼」：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +2%／點；
	; 熟練分支「餘燼延續」改為 20 秒。
	If ESSBNodes.Rank(akCtl, 11, 2, 1) > 0
		Int seconds = 10
		If ESSBNodes.Br(akCtl, 11, 2, 1, 1)
			seconds = 20
		EndIf
		akCtl.SetEmber(seconds, aiElement)
	EndIf

	; 專精分支「連斷」：融斷後 5 秒內重開任一形態，保留一半同調。
	If ESSBNodes.Br(akCtl, 11, 2, 2, 0)
		akCtl.SetSyncKeep(aiSyncBefore / 2, 5)
	EndIf

	; 大師主線「淬火」：融斷後 10 秒內武器傷害 +1%／點（PERK 進入點讀 ESSB_Quench）。
	If ESSBNodes.Rank(akCtl, 11, 2, 3) > 0
		akCtl.SetQuench(10)
	EndIf

	; 大師分支「回流」：融斷回復你魔力，每個印記 B_max ×0.5。
	If ESSBNodes.Br(akCtl, 11, 2, 3, 1) && aiMarks > 0
		Actor player = akCtl.ThePlayer()
		If player
			akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 2.0 * aiMarks * akCtl.GLevel(11), 0, player)
		EndIf
	EndIf

	; 傳奇分支「雙斷」：融斷後 3 秒內再次按 Z 開任一形態，對範圍內敵人立即開印一次。
	If ESSBNodes.Br(akCtl, 11, 2, 4, 0)
		akCtl.SetDoubleBurst(3)
	EndIf
EndFunction

; 大師分支「斷界」：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒。
; 本模組的通用弱化＝減速 30% + 碎甲 10%，不引用其他模組的減益。
Function OnBurstTarget(ESSBController akCtl, Actor akTarget) Global
	If !ESSBNodes.Br(akCtl, 11, 2, 3, 0) || !akTarget
		Return
	EndIf
	akCtl.ApplyUtil(0, 30.0, 3, akTarget)
	akCtl.ApplyUtil(1, akTarget.GetActorValue("DamageResist") * 0.1, 3, akTarget)
EndFunction

; 餘燼：關閉形態後 N 秒內的無形態命中，附帶前一元素附傷 +2%／點。
; 回傳這一擊要附帶的比例（0 代表不附帶）。
Float Function EmberRatio(ESSBController akCtl) Global
	If akCtl.GetEmberLeft() <= 0
		Return 0.0
	EndIf
	Return ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, 11, 2, 1), 0.02)
EndFunction
