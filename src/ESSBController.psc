Scriptname ESSBController extends ReferenceAlias
{元素魔戰士 控制器：形態層、附傷、印記登記表、同調、融斷、環境
（規劃 v0.3 第 1、1.1、1.1.1、2.1～2.10、2.13、6.1 節）。

形態切換在同一個腳本幀內完成：移除舊形態能力、加上新形態能力、更新全域變數。
沒有 Utility.Wait、沒有忙等迴圈、沒有每幀輪詢。附傷與所有反應傷害都用
DoCombatSpellApply 套自有法術，不用 Spell.Cast，避免觸發施法事件被其他模組吃掉；
絕不直接 DamageActorValue 生命，讓 Ordinator 等天賦照常成立。

登記表（規劃 2.2）：同時帶印記的目標上限 8 個，第 9 個目標被開印時最舊的印記
提前過期並觸發過期終焉（EXPIRE 終焉），再給新目標開印。每個目標的開印與終焉
各有 1 秒內部冷卻，過期終焉也受此限制。

狀態種類 aiKind（與 ESSBStatus／ESSBReactions 共用）：
  1 熱度 2 凍結 3 裂痕 4 失衡 5 血痕 6 聖印 7 毒層 8 浸濕 9 水壓 10 詛咒 11 星痕
自身資源 aiKind：1 電荷 2 岩甲 3 風勢 4 過熱
輔助法術 UtilSpells 索引：
  0 減速 1 減防 2 削魔 3 削耐 4 回血 5 回魔 6 回耐 7 放血（無抗性）}

GlobalVariable Property Enabled Auto
GlobalVariable Property DebugLevel Auto
GlobalVariable Property CurrentElement Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property Sync Auto
GlobalVariable Property SchoolXPMult Auto
; fix round 4: bound once by QUST VMAD; no runtime form lookup.
GlobalVariable Property PoisonDotK Auto
GlobalVariable Property BleedDotK Auto
GlobalVariable Property BaseDamageMult Auto
GlobalVariable Property NodeScale Auto
GlobalVariable Property MultDot Auto
GlobalVariable Property MultCooldown Auto
GlobalVariable Property MultRecovery Auto
GlobalVariable Property MultDrain Auto
GlobalVariable Property MultDuration Auto
GlobalVariable Property MultUpkeep Auto
Float Property NoformBaseTrue = 5.0 Auto
Float LastRecoveryScale = -1.0
GlobalVariable Property ManabreakBase Auto
GlobalVariable Property ManabreakPerRank Auto
GlobalVariable Property ManabreakMaxmagPct Auto
GlobalVariable Property ManabreakDryPct Auto
GlobalVariable Property WaterFlowBasePct Auto
GlobalVariable Property WaterFlowPerRankPct Auto
GlobalVariable Property WaterWetSlowPct Auto
GlobalVariable Property FrostOpenSlowPct Auto
GlobalVariable Property SlowCapPct Auto
GlobalVariable Property WaterClearStamina Auto
GlobalVariable Property WaterOpenStamina Auto
Float[] Property ElementDamageMin Auto
Float[] Property ElementDamageMax Auto
GlobalVariable Property SyncT1 Auto
GlobalVariable Property SyncT2 Auto
GlobalVariable Property SyncT3 Auto
GlobalVariable Property EnvWet Auto
GlobalVariable Property EnvStormy Auto
GlobalVariable Property EnvNight Auto
GlobalVariable Property GameHour Auto
{Skyrim.esm 0x38：夜晚判定 20:00–6:00}

Spell Property SettingsPower Auto
Spell Property FormRulesAbility Auto
Spell Property StatusHostSpell Auto
Spell Property EngagedSpell Auto
Spell[] Property FormPowers Auto
Spell[] Property FormAbilities Auto
Spell[] Property HitNormalSpells Auto
Spell[] Property HitPowerSpells Auto
Spell[] Property MarkSpells Auto
Spell[] Property ReactSpells Auto
Spell[] Property UtilSpells Auto
Spell[] Property UtilTargetSpells Auto
; Contact variants: RestoreHealth, RestoreStamina, MeleeBuff (allies only).

Keyword Property EngagedKeyword Auto
Keyword Property UndeadKeyword Auto
Keyword Property DaedraKeyword Auto
Keyword[] Property MarkKeywords Auto
{11 個印記關鍵字，索引 0 = 火。判定「帶某元素印記」只讀本模組自己的 keyword（規劃 2.2）。}

; ---------------------------------------------------------------- 機制前線新增

Spell Property OverheatSelfSpell Auto
Spell Property TrueSpell Auto
{真實傷害（規劃 2.8）：Resist Value = None、不掛學派、只掛 ESSB_TrueDamage。}
Spell Property ManaBreakSpell Auto
{破魔印 8 秒（ESSBCounter）。}
Spell Property SilenceSpell Auto
{沉默（ESSBSilence + MagickaRateMult -100）。}
Spell Property AntiMagicAbility Auto
{無元素樹「抗咒」：無形態時魔抗 +15% 的常駐能力，由腳本加掛與移除。}
Spell Property WarmBloodAbility Auto
{火樹「溫血」：火形態耐力回復 +20%。}
Spell Property InductionAbility Auto
{雷樹「感應」：雷形態魔力回復 +20%。}

Keyword Property SilenceKeyword Auto
Keyword Property ArmorSpellKeyword Auto
{原版 MagicArmorSpell：破魔大師主線的「帶魔法護盾」判定。}
Keyword Property CloakKeyword Auto
{原版 MagicCloak：破魔大師主線的「元素披風」判定。}

; ---------------------------------------------------------------- 機制前線 round 2

; Round 18: player-only proc cache and immutable-layout node mirrors.
Perk Property HitProcPerk Auto
Spell[] Property ProcVariants Auto
Int[] Property ProcElements Auto
Float[] Property ProcRatios Auto
Int[] Property ProcPowers Auto
Int[] Property ProcSneaks Auto
Int[] Property ProcBloodBands Auto
Spell[] Property HitBonusSpells Auto
GlobalVariable Property GDivineArmed Auto
GlobalVariable Property FormNotify Auto
GlobalVariable Property FormSound Auto
ESSBGuard Property GuardLayer Auto
ESSBInput Property InputLayer Auto
Int[] Property RankCacheA Auto
Int[] Property RankCacheB Auto
Int[] Property BranchCacheA Auto
Int[] Property BranchCacheB Auto
Int[] Property LevelMirror Auto
Bool Property NodeMirrorReady Auto
Float[] ProcWritten
Float[] DrainWritten
Bool ProcCacheReady
Int CachedSyncStage
Bool SyncCacheReady
Int AppliedElement

Perk Property BaseRulesPerk Auto
{ESSB_P_BaseRules：不依賴投點的引擎側規則（血形態重擊改扣生命、岩甲物理減傷）。
開局 AddPerk 一次，永不移除。}
Spell Property AshSpell Auto
{化灰（規劃 5.9、8）：DATA 照抄原版 PerkDisintegrateFFAimed。}
Spell Property InheritSpell Auto
{血承：七個 Peak Value Modifier，magnitude 在施放前設定。}
Spell Property WindSpeedAbility Auto
{風形態移速（AV 30 SpeedMult）。強度隨節點變動，AddSpell 前 SetNthEffectMagnitude。}
Spell Property WindMuffleAbility Auto
{風形態潛行：Muffle 0.5（規劃 1.1）。}
Spell Property SilentAbility Auto
{5.7「無聲」：Muffle 1.0 + 潛行移速 +20%，取代 WindMuffleAbility。}

Keyword Property DragonKeyword Auto
Race Property GiantRace Auto
Race Property MammothRace Auto
Class Property NecroClass Auto
Faction Property NecroFaction Auto

; ---------------------------------------------------------------- 機制前線 round 3

Spell Property FearSpell Auto
{恐懼（原型 7 Demoralize，magnitude＝可影響的最高等級，同原版幻術）。}
Spell Property FrenzySpell Auto
{瘋狂（原型 8 Frenzy，magnitude＝等級上限）。}
Spell Property ReanimateSpell Auto
{亡者歸來（原型 22 Reanimate，magnitude＝等級上限、duration 依階數）。}
Spell Property CleanseSpell Auto
{洗淨：限定關鍵字的 Dispel（中毒、元素持續傷、減速）＋ Cure Disease。}
Spell Property PurgeSpell Auto
{淨化／洗滌：關鍵字範圍更大的 Dispel ＋ Cure Disease ＋ Cure Poison。}
Spell Property StripSpell Auto
{沖刷：對目標的 Dispel 原型，只影響有時限的法術效果。}
Spell Property PoisonResistAbility Auto
{5.10「免疫」：毒形態毒抗 +50% 的常駐能力。}

Keyword Property NoReanimateKeyword Auto
{原版 MagicNoReanimate（0x06F6FB）：不可復生的屍體（含灰堆）。}
Keyword Property HarmfulKeyword Auto
{原版 MagicAlchHarmful（0x042509）：「你中毒時」的判定。}
Perk Property TwinSoulsPerk Auto
{原版雙魂（0x0D5F1C）：召喚上限 1 → 2。}

; ---------------------------------------------------------------- 特效前線（規劃 2.11、2.12）

Spell[] Property SelfCleanseSpells Auto
{洗淨／淨化的 SELF 路徑要逐項移除的「本模組自己的有時限減益」。
規劃 8 要求不能用無限定 Dispel 對自己施放；原型 2 與旗標 0x100（Dispel Keywords）
在機制前線只是推論值，所以這裡不依賴它們，改用明確清單 + PO3 掃現行效果。}

Form[] Property FxExplosions Auto
{11 個 ESSBFX_ZZExplosion_<元素>Hand1（EXPL）。只在終焉、融斷、領域開場放，
每 0.5 秒最多 5 個（規劃 2.12 的效能守則：普通命中禁止用爆炸）。}
Sound[] Property FxSoundFormActive Auto
{開形態（規劃 2.12 第 1 列）。}
Sound[] Property FxSoundRelease Auto
{關形態／融斷（規劃 2.12 第 2 列）。}
Sound[] Property FxSoundDrawSheathe Auto
{切換形態時舊元素的收刀聲（規劃 2.12 第 3 列：DrawSheathe_舊 接 FormActive_新）。}
Sound[] Property FxSoundCharge Auto
{同調升段（規劃 2.12「同調升段：Charge_X」）。開印的 Charge 音由印記 MGEF 的 SNDD 播，
不走腳本。}

GlobalVariable Property GWaterMirror Auto
GlobalVariable Property GGuardDark Auto
GlobalVariable Property GGuardAstral Auto
GlobalVariable Property GGuardStar Auto
GlobalVariable Property GDomainPoison Auto
GlobalVariable Property GDomainWater Auto
GlobalVariable Property GDomainDark Auto
GlobalVariable Property GDomainAstral Auto

GlobalVariable Property GRockArmor Auto
GlobalVariable Property GWind Auto
GlobalVariable Property GHolyShield Auto
GlobalVariable Property GBloodthirst Auto
GlobalVariable Property GGuardWind Auto
GlobalVariable Property GGuardDivine Auto
GlobalVariable Property GDomainEarth Auto
GlobalVariable Property GDomainBlood Auto
GlobalVariable Property GDomainDivine Auto
GlobalVariable Property GNoBloodCost Auto
GlobalVariable Property GCloakGuard Auto

; 腳本狀態 → 全域變數的鏡射（樣式 C）：PERK 進入點的 CTDA 只讀得到全域變數，
; 所以下面這些值一律在「變動的那一刻」寫一次，不在每秒 tick 裡盲寫。
GlobalVariable Property GSyncStage Auto
GlobalVariable Property GResolve Auto
GlobalVariable Property GOverheat Auto
GlobalVariable Property GCharge Auto
GlobalVariable Property GIceShield Auto
GlobalVariable Property GMolten Auto
GlobalVariable Property GEmber Auto
GlobalVariable Property GQuench Auto
GlobalVariable Property GPrevElement Auto
GlobalVariable Property GTwinElement Auto
GlobalVariable Property GDomainFire Auto
GlobalVariable Property GDomainFrost Auto
GlobalVariable Property GShockRecent Auto
GlobalVariable Property GGuardSwitch Auto
GlobalVariable Property GGuardBurst Auto
GlobalVariable Property GGuardIce Auto
GlobalVariable Property GCombo Auto
GlobalVariable Property GFreeOpen Auto

ESSBTrees Property Trees Auto
{技能樹腳本（同一個 Player 別名上的第二個腳本）：經驗發放與節點階數查詢。}

; ---------------------------------------------------------------- 內部狀態

Actor PlayerRef
Actor[] LiftActor
Float[] LiftDue
Float[] LiftForce
Float[] LiftDamage
Float NextTickAt
Int[] RegGeneration
Float[] RegUntil
Bool[] RegSecondReal
Float[] RegPendStarLock
Bool[] RegPendWetLock
Bool[] RegHostPending
Float[] RegHostRequest
Actor SwapActor
Int SwapGeneration
Float SwapDeadline
Float SwapStarted
Int[] SettledElement
Actor[] SettledDead
Int SettledNext
Actor[] DeadActor
Int[] DeadElement
Int[] DeadFreeze
Int[] DeadBleed
Int[] DeadPoison
Int DeadNext
Float[] TrioTimes
Int PerpetualKeep
Actor[] PendingServants
Float[] PendingServantDue
Bool ReanimateBusy
Int[] PendingStacks
Bool[] PendingSet
Int[] PendingAstral
Float[] PendingAstralWeight
Float[] PendingRadiance
Float[] PendingFrozen
Float[] PendingCatalyze
Float[] PendingCatalyzeMult
Float[] PendingCurse
Float[] PendingCurseBase
Float[] PendingCurseMult
Float[] PendingNextEnd
Float[] PendingNextOpen
Float[] PendingAir
Float[] PendingAirDamage
Int[] BackupIntsA
Int[] BackupIntsB
Int[] BackupIntsC
Int[] BackupIntsD
Float[] BackupFloatsA
Float[] BackupFloatsB
Bool[] BackupValid



; 登記表（8 格）
Actor[] RegActor
Int[] RegElem
Int[] RegSeq
Int[] RegPendElem
Int[] RegPendAmt
Float[] RegLastOpen
Float[] RegLastEnd
ESSBMark[] RegMark
ESSBStatus[] RegStatus
Int NextSeq = 1

; 換宿暫存（規劃 8 的 30 秒宿主問題：每目標約 25 秒搬一次家）
Int SwapSlot = -1
Int[] SwapInts
; FIX14: damage timestamps parallel to DamageActor[128]; no longer swap state.
Float[] SwapFloats


; FIX15: target-owned facts and once-only death payloads.
Actor[] HitActor
Int[] HitForm
Bool[] HitSneak
Bool[] HitPower
Int[] HitWeapon
Bool[] HitKillDone
Int HitNext
Int[] DeadCurse
Int[] DeadHeat
Int[] DeadHoly
Int SwitchCharge
Bool DivineArmed
Actor[] CastActor
Float[] CastAt
Int CastNext
Actor[] KillProcActor
Int[] KillProcKind
Float[] KillProcUntil
Float[] KillProcAmount
Int KillProcNext

; 自身資源（離開形態清空）
Int SelfCharge
Int SelfRockArmor
Int SelfWind
Int SelfOverheat
Float ChargeDecayAt
Float SelfLastHit
Float StormCharge
Bool LastHitPower
Bool LastHitSneak
Int SyncStageShown

Float LastEnvCheck
Bool Ready
Int Property CachedDebugLevel Auto
Bool Property RuntimeCacheReady Auto
Float Property CachedNodeScale Auto
Float CachedDuration
Int CachedT1
Int CachedT2
Int CachedT3
Int CachedSync
Bool LiftQueued
Bool Property StateBroken = False Auto
Bool FixInitialised
Bool RegistryInitialised
Bool FirstSetupDone

; ---------------------------------------------------------------- 節點狀態（機制前線）
; 副印記（通用樹「雙印」與「疊印」共用同一格；規劃 2.2 明寫雙印不占名額）
Int[] RegElem2
Int[] RegSeq2
Float[] RegSecondUntil
ESSBMark[] RegMark2

; 無元素樹
Int Resolve
Float ResolveTime
Int ComboHits
Float ComboTime
Float InterruptTime

; 秒計時器（每秒 tick 減 1，歸零時把對應的全域變數寫回 0）
Float MoltenTickAt
Float MoltenLeft
Float EmberLeft
Int EmberElem
Float QuenchLeft
Float ShockLeft
Float GuardSwitchLeft
Float GuardBurstLeft
Float GuardIceLeft
Float ThunderLeft
Float DoubleBurstLeft
Float SyncKeepLeft
Int SyncKeep
Int IceShield
Int PendingDischarge
Int NextMarkBonus
Int PrevElement
Int TwinElement
Float TwinTime
Float AvatarLeft
Float IceHeartTime

; ---- 機制前線 round 2 的狀態
Int HolyShield
Float BloodthirstLeft
Float GuardWindLeft
Float GuardDivineLeft
Float CloakGuardLeft
Float NoBloodCostLeft
Float WindFollowLeft
Float RiposteLeft
Float KeepSneakLeft
Int PendingBleed
Bool PendingHeal
Bool KillStreakReady
Bool DivineSaveUsed
; FIX10: provenance belongs to the victim, never to the active form.
Int[] RegLastDamage
Actor[] DamageActor
Int[] DamageElement
Int DamageNext
Float RetaliateTime
Float SanctuaryTime
Bool SneakingNow
Bool SilentOn
Float RockArmorShown
; 推力冷卻環（8 格）：kind 0 跌倒／吹飛 8 秒，kind 1 拉近 3 秒（規劃 2.6、8）
Actor[] KnockActor
Float[] KnockTime
Float[] PullTime
Float[] WashTime
Int KnockNext
Float EndBoostLeft
Float EndBoostAmount

; 開印後／終焉後的 5 秒視窗（各元素開啟熟練與關閉專精主線）
Float[] OpenBoost
Float[] EndBoost

; 領域（火域、冰原、地裂、血池、聖域、毒霧、潮池、死域、星域）：
; 不放任何 ObjectReference，只記中心座標、半徑與剩餘秒數，由既有的每秒 tick 做幾何判定
; （見實作紀錄的偏離說明）。round 3 把單一格擴充成固定 3 格，因為不同元素的領域
; 在正常玩法下會同時存在（融斷留下領域 → 切換形態 → 再融斷）。
Actor[] DomainResident
Float[] DomainResidentAt
Int[] DomainElem
Float[] DomainTickAt
Float[] DomainLeft
Float[] DomainX
Float[] DomainY
Float[] DomainZ
Float[] DomainR

; ---- 機制前線 round 3 的狀態
Int WaterMirror
Float GuardDarkLeft
Float GuardAstralLeft
Float GuardStarLeft
Bool PendingDrain
Float CleanseTime
Int AstralHits

; ---- 特效前線的狀態：爆炸預算（規劃 2.12「範圍事件最多播 5 個目標的特效」）
Int FxBudget
Float FxBudgetTime

; 切換／終焉的一次性旗標
Bool SwitchHitPending
Bool SwitchEndPending
Bool InSpread
Int TrioMask
Float TrioTime
Int ExtremeCount
Float FormOpenTime

; 節流狀態（規劃 6.1：等級 2 以上每秒最多 20 行；同一訊息 0.5 秒內不重複）
Float LogWindowStart = 0.0
Int LogCount = 0
Int LogDropped = 0
String LogLastKey
Float LogLastTime

; ---------------------------------------------------------------- 生命週期

Event OnInit()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	; Alias init can be delivered before quest startup/reset has settled.
	; Do not touch or scan arrays here; a single deferred update performs Setup.
	RegisterForSingleUpdate(2.0)
EndEvent

Float LastNodeScale = -1.0

Event OnPlayerLoadGame()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	LastNodeScale = -1.0
	LastRecoveryScale = -1.0
	Ready = False
	RuntimeCacheReady = False
	ProcCacheReady = False
	SyncCacheReady = False
	NextTickAt = 0.0
	RegisterForSingleUpdate(2.0)
EndEvent

Event OnUpdate()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !Ready
		Setup()
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int index = 0
	Bool hasLift = False
	While LiftQueued && index < 8
		If LiftActor[index] && now >= LiftDue[index]
			Actor target = LiftActor[index]
			Float force = LiftForce[index]
			Float damage = LiftDamage[index]
			LiftActor[index] = None
			; Only the ragdoll states, never normal/getting-up actors.
			Int knock = PO3_SKSEFunctions.GetActorKnockState(target)
			If CanRagdoll(target) && (knock == 1 || knock == 3)
				target.ApplyHavokImpulse(0.0, 0.0, 1.0, force)
				SetAirborne(target, 2, damage)
			EndIf
		EndIf
		If LiftActor[index]
			hasLift = True
		EndIf
		index += 1
	EndWhile
	LiftQueued = hasLift
	If !Ready
		Setup()
	ElseIf now >= NextTickAt
		Tick()
	Else
		ArmUpdate()
	EndIf
EndEvent

Function InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If FixInitialised
		Return
	EndIf
	If !SwapFloats || SwapFloats.Length != 128
		SwapFloats = new Float[128]
		If !SwapFloats
			BreakState()
			Return
		EndIf
	EndIf
	; Allocate once on this schema; failure latches and never retries.
	If !PendingAir
		PendingAir = new Float[8]
		If !PendingAir
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingAirDamage
		PendingAirDamage = new Float[8]
		If !PendingAirDamage
			BreakState()
			Return
		EndIf
	EndIf
	InitBackupInts()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !BackupFloatsA
		BackupFloatsA = new Float[96]
		If !BackupFloatsA
			BreakState()
			Return
		EndIf
	EndIf
	If !BackupFloatsB
		BackupFloatsB = new Float[96]
		If !BackupFloatsB
			BreakState()
			Return
		EndIf
	EndIf
	If !BackupValid
		BackupValid = new Bool[8]
		If !BackupValid
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingNextEnd
		PendingNextEnd = new Float[8]
		If !PendingNextEnd
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingNextOpen
		PendingNextOpen = new Float[8]
		If !PendingNextOpen
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingStacks
		PendingStacks = new Int[96]
		If !PendingStacks
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingSet
		PendingSet = new Bool[96]
		If !PendingSet
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingAstral
		PendingAstral = new Int[8]
		If !PendingAstral
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingAstralWeight
		PendingAstralWeight = new Float[8]
		If !PendingAstralWeight
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingRadiance
		PendingRadiance = new Float[8]
		If !PendingRadiance
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingFrozen
		PendingFrozen = new Float[8]
		If !PendingFrozen
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingCatalyze
		PendingCatalyze = new Float[8]
		If !PendingCatalyze
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingCatalyzeMult
		PendingCatalyzeMult = new Float[8]
		If !PendingCatalyzeMult
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingCurse
		PendingCurse = new Float[8]
		If !PendingCurse
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingCurseBase
		PendingCurseBase = new Float[8]
		If !PendingCurseBase
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingCurseMult
		PendingCurseMult = new Float[8]
		If !PendingCurseMult
			BreakState()
			Return
		EndIf
	EndIf
	If !RegGeneration
		RegGeneration = new Int[8]
		If !RegGeneration
			BreakState()
			Return
		EndIf
	EndIf
	If !RegUntil
		RegUntil = new Float[8]
		If !RegUntil
			BreakState()
			Return
		EndIf
	EndIf
	If !RegSecondReal
		RegSecondReal = new Bool[8]
		If !RegSecondReal
			BreakState()
			Return
		EndIf
	EndIf
	If !RegPendStarLock
		RegPendStarLock = new Float[8]
		If !RegPendStarLock
			BreakState()
			Return
		EndIf
	EndIf
	If !RegPendWetLock
		RegPendWetLock = new Bool[8]
		If !RegPendWetLock
			BreakState()
			Return
		EndIf
	EndIf
	If !RegHostPending
		RegHostPending = new Bool[8]
		If !RegHostPending
			BreakState()
			Return
		EndIf
	EndIf
	If !RegHostRequest
		RegHostRequest = new Float[8]
		If !RegHostRequest
			BreakState()
			Return
		EndIf
	EndIf
	If !SettledElement
		SettledElement = new Int[8]
		If !SettledElement
			BreakState()
			Return
		EndIf
	EndIf
	If !SettledDead
		SettledDead = new Actor[8]
		If !SettledDead
			BreakState()
			Return
		EndIf
	EndIf
	If !HitActor
		HitActor = new Actor[8]
		If !HitActor
			BreakState()
			Return
		EndIf
	EndIf
	If !HitForm
		HitForm = new Int[8]
		If !HitForm
			BreakState()
			Return
		EndIf
	EndIf
	If !HitSneak
		HitSneak = new Bool[8]
		If !HitSneak
			BreakState()
			Return
		EndIf
	EndIf
	If !HitPower
		HitPower = new Bool[8]
		If !HitPower
			BreakState()
			Return
		EndIf
	EndIf
	If !HitWeapon
		HitWeapon = new Int[8]
		If !HitWeapon
			BreakState()
			Return
		EndIf
	EndIf
	If !HitKillDone
		HitKillDone = new Bool[8]
		If !HitKillDone
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadCurse
		DeadCurse = new Int[8]
		If !DeadCurse
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadHeat
		DeadHeat = new Int[8]
		If !DeadHeat
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadHoly
		DeadHoly = new Int[8]
		If !DeadHoly
			BreakState()
			Return
		EndIf
	EndIf
	If !CastActor
		CastActor = new Actor[8]
		If !CastActor
			BreakState()
			Return
		EndIf
	EndIf
	If !CastAt
		CastAt = new Float[8]
		If !CastAt
			BreakState()
			Return
		EndIf
	EndIf
	If !KillProcActor
		KillProcActor = new Actor[8]
		If !KillProcActor
			BreakState()
			Return
		EndIf
	EndIf
	If !KillProcKind
		KillProcKind = new Int[8]
		If !KillProcKind
			BreakState()
			Return
		EndIf
	EndIf
	If !KillProcUntil
		KillProcUntil = new Float[8]
		If !KillProcUntil
			BreakState()
			Return
		EndIf
	EndIf
	If !KillProcAmount
		KillProcAmount = new Float[8]
		If !KillProcAmount
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadActor
		DeadActor = new Actor[8]
		If !DeadActor
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadElement
		DeadElement = new Int[8]
		If !DeadElement
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadFreeze
		DeadFreeze = new Int[8]
		If !DeadFreeze
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadBleed
		DeadBleed = new Int[8]
		If !DeadBleed
			BreakState()
			Return
		EndIf
	EndIf
	If !DeadPoison
		DeadPoison = new Int[8]
		If !DeadPoison
			BreakState()
			Return
		EndIf
	EndIf
	If !TrioTimes
		TrioTimes = new Float[12]
		If !TrioTimes
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingServants
		PendingServants = new Actor[2]
		If !PendingServants
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingServantDue
		PendingServantDue = new Float[2]
		If !PendingServantDue
			BreakState()
			Return
		EndIf
	EndIf
	If !LiftDue
		LiftDue = new Float[8]
		If !LiftDue
			BreakState()
			Return
		EndIf
	EndIf
	If !LiftForce
		LiftForce = new Float[8]
		If !LiftForce
			BreakState()
			Return
		EndIf
	EndIf
	If !LiftDamage
		LiftDamage = new Float[8]
		If !LiftDamage
			BreakState()
			Return
		EndIf
	EndIf
	If !LiftActor
		LiftActor = new Actor[8]
		If !LiftActor
			BreakState()
			Return
		EndIf
	EndIf
	If !RegLastDamage
		RegLastDamage = new Int[8]
		If !RegLastDamage
			BreakState()
			Return
		EndIf
	EndIf
	If !DamageActor
		DamageActor = new Actor[128]
		If !DamageActor
			BreakState()
			Return
		EndIf
	EndIf
	If !DamageElement
		DamageElement = new Int[128]
		If !DamageElement
			BreakState()
			Return
		EndIf
	EndIf
	FixInitialised = True
EndFunction

; One update queue serves both the regular tick and one-shot lift callbacks.
Function ScheduleTick(Float afDelay)
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Float requested = Utility.GetCurrentRealTime() + afDelay
	If NextTickAt <= 0.0 || requested < NextTickAt
		NextTickAt = requested
	EndIf
	ArmUpdate()
EndFunction

Function ArmUpdate()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Float due = NextTickAt
	Int index = 0
	While LiftQueued && index < 8
		If LiftActor[index] && LiftDue[index] < due
			due = LiftDue[index]
		EndIf
		index += 1
	EndWhile
	Float delay = due - now
	If delay < 0.01
		delay = 0.01
	EndIf
	RegisterForSingleUpdate(delay)
EndFunction

Function InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If RegistryInitialised
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	; Allocate once on this schema; failure latches and never retries.
	If !RegActor
		RegActor = new Actor[8]
		If !RegActor
			BreakState()
			Return
		EndIf
	EndIf
	If !RegElem
		RegElem = new Int[8]
		If !RegElem
			BreakState()
			Return
		EndIf
	EndIf
	If !RegSeq
		RegSeq = new Int[8]
		If !RegSeq
			BreakState()
			Return
		EndIf
	EndIf
	If !RegPendElem
		RegPendElem = new Int[8]
		If !RegPendElem
			BreakState()
			Return
		EndIf
	EndIf
	If !RegPendAmt
		RegPendAmt = new Int[8]
		If !RegPendAmt
			BreakState()
			Return
		EndIf
	EndIf
	If !RegLastOpen
		RegLastOpen = new Float[8]
		If !RegLastOpen
			BreakState()
			Return
		EndIf
	EndIf
	If !RegLastEnd
		RegLastEnd = new Float[8]
		If !RegLastEnd
			BreakState()
			Return
		EndIf
	EndIf
	If !RegMark
		RegMark = new ESSBMark[8]
		If !RegMark
			BreakState()
			Return
		EndIf
	EndIf
	If !RegStatus
		RegStatus = new ESSBStatus[8]
		If !RegStatus
			BreakState()
			Return
		EndIf
	EndIf
	If !RegElem2
		RegElem2 = new Int[8]
		If !RegElem2
			BreakState()
			Return
		EndIf
	EndIf
	If !RegSeq2
		RegSeq2 = new Int[8]
		If !RegSeq2
			BreakState()
			Return
		EndIf
	EndIf
	If !RegSecondUntil
		RegSecondUntil = new Float[8]
		If !RegSecondUntil
			BreakState()
			Return
		EndIf
	EndIf
	If !RegMark2
		RegMark2 = new ESSBMark[8]
		If !RegMark2
			BreakState()
			Return
		EndIf
	EndIf
	If !OpenBoost
		OpenBoost = new Float[12]
		If !OpenBoost
			BreakState()
			Return
		EndIf
	EndIf
	If !EndBoost
		EndBoost = new Float[12]
		If !EndBoost
			BreakState()
			Return
		EndIf
	EndIf
	If !KnockActor
		KnockActor = new Actor[8]
		If !KnockActor
			BreakState()
			Return
		EndIf
	EndIf
	If !KnockTime
		KnockTime = new Float[8]
		If !KnockTime
			BreakState()
			Return
		EndIf
	EndIf
	If !PullTime
		PullTime = new Float[8]
		If !PullTime
			BreakState()
			Return
		EndIf
	EndIf
	If !WashTime
		WashTime = new Float[8]
		If !WashTime
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainResident
		DomainResident = new Actor[18]
	EndIf
	If !DomainResidentAt
		DomainResidentAt = new Float[18]
	EndIf
	If !DomainResident || !DomainResidentAt
		BreakState()
		Return
	EndIf
	If !DomainElem
		DomainElem = new Int[3]
		If !DomainElem
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainTickAt
		DomainTickAt = new Float[3]
		If !DomainTickAt
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainLeft
		DomainLeft = new Float[3]
		If !DomainLeft
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainX
		DomainX = new Float[3]
		If !DomainX
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainY
		DomainY = new Float[3]
		If !DomainY
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainZ
		DomainZ = new Float[3]
		If !DomainZ
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainR
		DomainR = new Float[3]
		If !DomainR
			BreakState()
			Return
		EndIf
	EndIf
	RegistryInitialised = True
EndFunction

Function Setup()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Ready = False
	Actor player = GetActorReference()
	If !player
		ScheduleTick(5.0)
		Return
	EndIf
	PlayerRef = player
	; 神佑用的 StartDeferredKill 是存在「角色」上的狀態，不在腳本實體裡。若舊世代實體在 schema 升版時
	; 被丟棄而沒跑 BreakState，玩家會永遠卡在延遲死亡（生命可以 <= 0 卻不會死）。每次 Setup 先無條件
	; 解除一次；生命 > 0 時這是 no-op，<= 0 時就是本來就該死。之後再由 RefreshDivineProtection 依資格重新上鎖。
	player.EndDeferredKill()
	DivineArmed = False
	SetGlobal(GDivineArmed, 0)
	If !ValidateBindings()
		BreakState()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	InitProcCache()
	If StateBroken
		Return
	EndIf
	Trees.InitTables()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	ESSBGuard guard = GetOwningQuest().GetAlias(0) as ESSBGuard
	If !guard
		BreakState()
		Return
	EndIf
	CachedDebugLevel = DebugLevel.GetValueInt()
	guard.Setup()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Bool wasLoaded = FirstSetupDone
	If !FirstSetupDone
		ReconcileLoadedForm(player)
		FirstSetupDone = True
	EndIf
	RefreshRuntimeValues()
	RegisterForMenu("Journal Menu")
	If !player.HasSpell(SettingsPower)
		player.AddSpell(SettingsPower, False)
	EndIf
	Int index = 0
	While index < FormPowers.Length
		If !player.HasSpell(FormPowers[index])
			player.AddSpell(FormPowers[index], False)
		EndIf
		index += 1
	EndWhile
	If !player.HasSpell(FormRulesAbility)
		player.AddSpell(FormRulesAbility, False)
	EndIf
	; 基礎規則天賦（血形態重擊改扣生命、岩甲物理減傷）：不是節點，開局加一次就不再動。
	If HitProcPerk && !player.HasPerk(HitProcPerk)
		player.AddPerk(HitProcPerk)
	EndIf
	If BaseRulesPerk && !player.HasPerk(BaseRulesPerk)
		player.AddPerk(BaseRulesPerk)
	EndIf
	RefreshTrees()
	RefreshAbilities()
	EnvCheck()
	If wasLoaded
		ResetLoadClock()
	EndIf
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	; Publish readiness only after every initialization phase is complete.
	AppliedElement = CurrentElement.GetValueInt()
	RefreshSyncStage()
	RefreshProcMagnitudes()
	If StateBroken
		Return
	EndIf
	Ready = True
	If InputLayer
		InputLayer.Setup()
	EndIf
	PO3_Events_Alias.RegisterForWeaponHit(Self)
	SendModEvent("ESSB_FormRulesReady")
	If CachedDebugLevel >= 1
		LogEvent(1, "init", "ready enabled=" + Enabled.GetValueInt() + " element=" + CurrentElement.GetValueInt() \
			+ " active=" + FormActive.GetValueInt() + " slots=8")
	EndIf
	ScheduleTick(1.0)
EndFunction

Actor Function ThePlayer()
	If !PlayerRef
		PlayerRef = GetActorReference()
	EndIf
	Return PlayerRef
EndFunction

; ---------------------------------------------------------------- 形態層

Function ToggleForm(Int aiIndex)
	If IsOperational() && InputLayer
		InputLayer.RequestSwitch(aiIndex)
	EndIf
EndFunction

Function SwitchForm(Int aiIndex)
	If !IsOperational()
		Return
	EndIf
	aiIndex = CurrentElement.GetValueInt()
	If FormActive.GetValueInt() != 1
		CloseForm()
		Return
	EndIf
	Actor player = ThePlayer()
	If !player || aiIndex < 1 || aiIndex > 11
		Return
	EndIf
	RiposteLeft = 0
	Int previous = AppliedElement
	If previous == aiIndex
		Return
	EndIf
	AppliedElement = aiIndex
	If previous >= 1 && previous <= 11
		player.RemoveSpell(FormAbilities[previous - 1])
	EndIf
	player.AddSpell(FormAbilities[aiIndex - 1], False)
	Int syncBefore = Sync.GetValueInt()
	RefreshTrees()

	; 同調的保留來源（規劃 5.2）：承接（切換保留 1/3）、連斷（融斷後 5 秒內重開保留一半）、
	; 永續／三重奏（融斷後保留一段或全部）。三者取高，不疊乘。
	Int keep = 0
	If previous >= 1
		keep = ESSBNodes.CarryOverSync(Self, syncBefore)
	EndIf
	If (SyncKeepLeft > 0 && SyncKeepLeft > Utility.GetCurrentRealTime()) && SyncKeep > keep
		keep = SyncKeep
	EndIf
	If PerpetualKeep > keep
		keep = PerpetualKeep
	EndIf
	PerpetualKeep = 0
	SyncKeep = 0
	SyncKeepLeft = 0
	CachedSync = keep
	Sync.SetValueInt(keep)
	SyncStageShown = 0
	PushSyncStage()

	; 5.2 開啟熟練分支「順轉」：切換後 1 秒受傷 -50%（PERK 進入點讀 ESSB_GuardSwitch）。
	If ESSBNodes.Br(Self, 12, 1, 1, 0)
		SetGuardSwitch(2)
	EndIf
	SendModEvent("ESSB_FormChanged", "open", aiIndex as Float)
	If CachedDebugLevel >= 1
		LogEvent(1, "form", "switch " + previous + " -> " + aiIndex + " syncKeep=" + keep)
	EndIf
	If previous >= 1 && previous != aiIndex
		OnFormSwitched(previous, aiIndex)
	EndIf
	OnFormOpened(aiIndex)
	RefreshProcMagnitudes()
	ScheduleTick(1.0)
EndFunction

Function CloseForm()
	If !IsOperational()
		Return
	EndIf
	Actor player = ThePlayer()
	Int previous = AppliedElement
	If previous == 0
		previous = CurrentElement.GetValueInt()
	EndIf
	AppliedElement = 0
	If player && previous >= 1 && previous <= 11
		player.RemoveSpell(FormAbilities[previous - 1])
	EndIf
	FormActive.SetValueInt(0)
	CurrentElement.SetValueInt(0)
	PrevElement = previous
	If GPrevElement
		GPrevElement.SetValueInt(previous)
	EndIf
	SendModEvent("ESSB_FormChanged", "close", 0.0)
	If CachedDebugLevel >= 1
		LogEvent(1, "form", "close " + previous)
	EndIf
	OnFormClosed(previous)
	RefreshTrees()
	RefreshAbilities()
EndFunction

Function OnFormOpened(Int aiIndex)
	; 規劃 2.3：疊在你身上的狀態，離開形態時清空；換到新形態也從零開始。
	ClearSelfAll()
	; 規劃 2.12 第 1 列：開形態一次 FormActive 音（光環淡入由形態能力的 MGEF 自己播）。
	If FormSound && FormSound.GetValueInt() == 1
		PlayFormSound(FxSoundFormActive, aiIndex)
	EndIf
	FormOpenTime = Utility.GetCurrentRealTime()
	RefreshAbilities()
	; 5.2 開啟大師分支「臨界」。
	ESSBNodes.OnFormOpened(Self, aiIndex)
	; 各元素開啟大師主線「火臨／冰臨／雷臨／地臨／風臨／血臨／聖臨」。
	ESSBElem.OnFormOpened(Self, aiIndex)
	ESSBElem.OnFormOpenedExtra(Self, aiIndex)
	; 5.1 融斷傳奇分支「雙斷」：融斷後 3 秒內再開任一形態，對範圍內敵人立即開印一次。
	If (DoubleBurstLeft > 0 && DoubleBurstLeft > Utility.GetCurrentRealTime())
		DoubleBurstLeft = 0
		Actor player = ThePlayer()
		If player
			Actor[] nearby = ScanTargets(player, ESSBNoForm.BurstRadius(Self), 5, player)
			Int index = 0
			While index < nearby.Length
				If nearby[index]
					ForceOpenOn(nearby[index], aiIndex)
				EndIf
				index += 1
			EndWhile
			If CachedDebugLevel >= 1
				LogEvent(1, "burst", "doubleburst reopen element=" + aiIndex)
			EndIf
		EndIf
	EndIf
EndFunction

Function OnFormSwitched(Int aiOldIndex, Int aiNewIndex)
	If aiOldIndex == 3
		SwitchCharge = SelfCharge
	EndIf
	ClearSelfAll()
	; 規劃 2.12 第 3 列：DrawSheathe_舊 接 FormActive_新（新的那一聲由 OnFormOpened 播，
	; SwitchForm 的呼叫順序就是先 OnFormSwitched 再 OnFormOpened）。
	; Round 18: switching has only the new form activation cue.
	PrevElement = aiOldIndex
	If GPrevElement
		GPrevElement.SetValueInt(aiOldIndex)
	EndIf
	; 5.2 關閉新手分支「餘響」與關閉專精主線：切換後首次命中附帶前一元素附傷。
	SwitchHitPending = True
	; 5.2 關閉大師分支「協奏」與傳奇分支「大協奏」：切換後首次終焉。
	SwitchEndPending = True
	; 5.2 關閉傳奇分支「雙生」：雙持時左手武器攜帶前一個形態的元素 30 秒。
	If ESSBNodes.HasTwin(Self)
		TwinElement = aiOldIndex
		TwinTime = Utility.GetCurrentRealTime()
		If GTwinElement
			GTwinElement.SetValueInt(aiOldIndex)
		EndIf
		If CachedDebugLevel >= 1
			LogEvent(1, "node", "common twin element=" + aiOldIndex)
		EndIf
	EndIf
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

; 融斷（規劃 2.5）：關閉形態的瞬間，15 公尺內所有登記目標的印記一次結清為爆傷，
; 倍率 K_sync 隨同調段數 0／1／2／3 段 = ×1／×1.5／×2／×3。
Function OnFormClosed(Int aiIndex)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	; 規劃 2.12 第 2 列：關形態／融斷一次 Release 音。爆炸由每個印記目標的 EndMark 放，
	; 預算（每 0.5 秒 5 個）在 PlaceFx 裡，所以「範圍內每個印記目標一次爆炸」自動封頂 5 個。
	PlayFormSound(FxSoundRelease, aiIndex)
	Int syncBefore = Sync.GetValueInt()
	Int stage = SyncStage()
	; 融斷倍率：K_sync × 通用樹關閉路線 × 無元素樹融斷路線 × 該元素印記的融斷加成（各印記另乘）。
	Float k = SyncMult() * ESSBNodes.CommonBurstMult(Self) * ESSBNoForm.BurstMult(Self)
	Float radius = ESSBNoForm.BurstRadius(Self)
	Int burst = 0
	Int skipped = 0
	Int index = 0
	While index < 8
		Actor target = RegActor[index]
		If target && (RegElem[index] >= 1 || RegElem2[index] >= 1)
			If target.IsDead()
				CaptureDeath(index)
				ClearSlot(index)
			ElseIf player && target.GetDistance(player) <= radius
				; 5.1 融斷大師分支「斷界」：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒。
				ESSBNoForm.OnBurstTarget(Self, target)
				EndBothMarks(index, k)
				burst += 1
			Else
				skipped += 1
			EndIf
		EndIf
		index += 1
	EndWhile
	If CachedDebugLevel >= 1
		LogEvent(1, "burst", "targets=" + burst + " outofrange=" + skipped + " stage=" + stage \
			+ " k=" + k + " radius=" + radius)
	EndIf

	; 5.2 持續傳奇分支「永續」：Z 關閉時若同調三段，融斷後保留一段同調到下一次開形態。
	If stage >= 3 && ESSBNodes.HasPerpetual(Self)
		Int t1 = 5
		If SyncT1
			t1 = SyncT1.GetValueInt()
		EndIf
		PerpetualKeep = t1
	EndIf
	; 5.2 關閉大師分支「安全閥」：融斷時你受傷 -50% 持續 2 秒。
	If ESSBNodes.Br(Self, 12, 2, 3, 1)
		SetGuardBurst(2)
	EndIf
	; 5.1 融斷路線的收尾（免門檻、餘燼、連斷、淬火、回流、雙斷）。
	ESSBNoForm.OnBurst(Self, aiIndex, burst, syncBefore)

	CachedSync = 0

	Sync.SetValueInt(0)
	SyncStageShown = 0
	PushSyncStage()
	ClearSelfAll()
EndFunction

; ---------------------------------------------------------------- 附傷與命中

; PO3 的本機 PSC 只保證 Form，未說明箭擊的來源實際類別。
; Weapon 優先；Ammo / None / 同一 Projectile 只在有投射物且裝備弓弩時回退。
; Spell、Explosion 與其他 Form 不因玩家剛好拿弓就冒充武器命中。
Int Function ResolveHitWeaponType(Actor akAttacker, Form akSource, Projectile akProjectile)
	Weapon weaponSource = akSource as Weapon
	If weaponSource
		Return weaponSource.GetWeaponType()
	EndIf
	Ammo ammoSource = akSource as Ammo
	Projectile projectileSource = akSource as Projectile
	If akSource && !ammoSource && (!projectileSource || projectileSource != akProjectile)
		Return -1
	EndIf
	If !akAttacker
		Return -1
	EndIf
	Weapon equipped = akAttacker.GetEquippedWeapon(False)
	Weapon offhand = akAttacker.GetEquippedWeapon(True)
	If akProjectile
		If equipped && (equipped.GetWeaponType() == 7 || equipped.GetWeaponType() == 9)
			Return equipped.GetWeaponType()
		EndIf
		If offhand && (offhand.GetWeaponType() == 7 || offhand.GetWeaponType() == 9)
			Return offhand.GetWeaponType()
		EndIf
	ElseIf !akSource && akAttacker.GetEquippedItemType(0) == 0 && akAttacker.GetEquippedItemType(1) == 0
		Return 0
	EndIf
	Return -1
EndFunction

; 不增加存檔成員；使用原本的 6.1 節流狀態。關閉時不查 Form、不組字串。
Function LogRejectedHit(String asReason, ObjectReference akTarget, Form akSource, Projectile akProjectile, Int aiHitFlagMask, Int aiWeaponType = -2)
	If CachedDebugLevel < 3
		Return
	EndIf
	Int sourceType = 0
	Int sourceID = 0
	Int targetID = 0
	If akSource
		sourceType = akSource.GetType()
		sourceID = akSource.GetFormID()
	EndIf
	If akTarget
		targetID = akTarget.GetFormID()
	EndIf
	If aiWeaponType == -2
		aiWeaponType = ResolveHitWeaponType(PlayerRef, akSource, akProjectile)
	EndIf
	If CachedDebugLevel >= 3
		LogThrottled(3, "hit-reject", "target=" + targetID + " reason=" + asReason \
			+ " sourceType=" + sourceType + " sourceFormID=" + sourceID + " weapon=" + aiWeaponType \
			+ " projectile=" + (akProjectile != None) + " flags=" + aiHitFlagMask \
			+ " rejectedMask=" + Math.LogicalAnd(aiHitFlagMask, 1097731))
	EndIf
EndFunction

Event OnWeaponHit(ObjectReference akTarget, Form akSource, Projectile akProjectile, Int aiHitFlagMask)
	If !IsOperational()
		If CachedDebugLevel >= 3
			LogRejectedHit("not-operational", akTarget, akSource, akProjectile, aiHitFlagMask)
		EndIf
		Return
	EndIf
	If Enabled.GetValueInt() != 1
		If CachedDebugLevel >= 3
			LogRejectedHit("disabled", akTarget, akSource, akProjectile, aiHitFlagMask)
		EndIf
		Return
	EndIf
	Actor caster = ThePlayer()
	Int weaponType = ResolveHitWeaponType(caster, akSource, akProjectile)
	; RE::HitData：格擋 1/2、盾擊 16384/32768、爆炸 1048576。
	; 本機 PO3 PDB 的 HitData::Flag 列舉亦符合此遮罩；不移除任何拒絕位元。
	If Math.LogicalAnd(aiHitFlagMask, 1097731) != 0
		If CachedDebugLevel >= 3
			LogRejectedHit("blocked-bash-explosion", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		Return
	EndIf
	Actor targetActor = akTarget as Actor
	If !targetActor || !caster || targetActor == caster || caster.IsDead()
		If CachedDebugLevel >= 3
			LogRejectedHit("invalid-actor", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		Return
	EndIf
	If targetActor.IsPlayerTeammate() || targetActor.IsCommandedActor()
		Return
	EndIf
	; -1 是未知／非武器來源；0 只保留給武器拳腳或可確認的空手。
	If weaponType < 0 || weaponType > 9 || weaponType == 8
		If CachedDebugLevel >= 3
			LogRejectedHit("unsupported-source-or-weapon", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		Return
	EndIf
	Bool ranged = (weaponType == 7 || weaponType == 9)
	; PO3 的 OnWeaponHit 對箭矢命中不保證帶 Projectile（本機 log 實測 akProjectile 為 None），
	; Phenderix 的同名事件也完全不看 akProjectile，只認武器型別 7／9。要求投射物會讓弓弩全部被丟掉。
	If !ranged && akProjectile != None
		If CachedDebugLevel >= 3
			LogRejectedHit("melee-with-projectile", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		Return
	EndIf
	Weapon sourceWeapon = akSource as Weapon
	If ranged && !sourceWeapon
		sourceWeapon = caster.GetEquippedWeapon(False)
		If !sourceWeapon || sourceWeapon.GetWeaponType() != weaponType
			sourceWeapon = caster.GetEquippedWeapon(True)
		EndIf
	EndIf
	Bool sneak = Math.LogicalAnd(aiHitFlagMask, 2048) != 0
	Bool power = Math.LogicalAnd(aiHitFlagMask, 65536) != 0
	If ranged
		; 弓弩沒有一般重擊，只有潛行射擊取得重擊待遇（規劃 2.1）。
		power = sneak
	EndIf
	LastHitPower = power
	LastHitSneak = sneak
	Int fact = 0
	While fact < 8 && HitActor[fact] != targetActor
		fact += 1
	EndWhile
	If fact >= 8
		fact = HitNext
		HitNext = (HitNext + 1) % 8
		HitKillDone[fact] = False
	EndIf
	Int hitElement = 0
	Bool hitActive = FormActive.GetValueInt() == 1
	If hitActive
		hitElement = CurrentElement.GetValueInt()
	EndIf
	HitForm[fact] = hitElement
	HitActor[fact] = targetActor
	HitSneak[fact] = sneak
	HitPower[fact] = power
	HitWeapon[fact] = weaponType
	If targetActor.IsDead()
		If CachedDebugLevel >= 3
			LogRejectedHit("invalid-actor", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		; Engine weapon damage already killed it: never send corpse damage/open marks.
		If sneak && hitElement == 5
			SetSelf(3, ESSBElem2.WindThreshold(Self))
			TakeKillStreak()
			ESSBElem2.LethalAmbush(Self, targetActor)
		EndIf
		Int deadSlot = FindSlot(targetActor)
		If deadSlot >= 0
			CaptureDeath(deadSlot)
		EndIf
		; Kill callback may have arrived before the weapon callback.
		Int settled = 0
		While settled < 8
			If SettledDead[settled] == targetActor
				SettleSneakKill(targetActor, SettledElement[settled])
				Return
			EndIf
			settled += 1
		EndWhile
		Return
	EndIf
	HitKillDone[fact] = False
	; 5.2 關閉傳奇分支「雙生」：雙持時左手武器攜帶前一個形態的元素。
	; PO3 的 akSource 就是這一擊的武器，和玩家左手武器比對即可分辨是哪一手。
	Bool leftHand = False
	If sourceWeapon && caster.GetEquippedWeapon(True) == sourceWeapon \
		&& caster.GetEquippedWeapon(False) != sourceWeapon
		leftHand = True
	EndIf

	If !hitActive
		; 規劃 4：關形態的任何武器命中只給無元素樹經驗，不做元素附傷與印記。
		OnNoFormHit(targetActor, sourceWeapon, power)
		If Trees
			Trees.OnValidHitXP(0)
		EndIf
		Return
	EndIf

	Int element = hitElement
	If element < 1 || element > 11
		If CachedDebugLevel >= 3
			LogRejectedHit("invalid-element", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		Return
	EndIf
	; 雙生：左手命中改用前一個形態的元素（30 秒內有效）。
	If leftHand && TwinElement >= 1 && Utility.GetCurrentRealTime() - TwinTime <= DurationSeconds(30.0)
		element = TwinElement
	EndIf

	Int hitSlot = FindSlotInternal(targetActor)
	Int hitGeneration = -1
	If hitSlot >= 0
		hitGeneration = RegGeneration[hitSlot]
	EndIf
	Bool opening = WillOpenInternal(targetActor, element, hitSlot)
	Bool procSneak = caster.IsSneaking()
	Bool procPower = PO3_SKSEFunctions.IsPowerAttacking(caster)
	If ranged
		procPower = procSneak
	EndIf
	Int nativeDamage = NoteDamageElement(targetActor, element)
	If nativeDamage >= 0
		SwapFloats[nativeDamage] = Utility.GetCurrentRealTime()
	EndIf
	If element != hitElement
		ApplyBakedProc(targetActor, element, power, sneak)
	Else
		ApplyProc(targetActor, element, procPower, procSneak, opening, hitSlot, hitGeneration)
	EndIf

	; 5.2 持續大師分支「極致」：同調三段時每 10 次命中額外一次全額附傷。
	If ESSBNodes.HasExtreme(Self) && SyncStage() >= 3
		ExtremeCount += 1
		If ExtremeCount >= 10
			ExtremeCount = 0
			ApplyBakedProc(targetActor, element, power, sneak)
			If CachedDebugLevel >= 2
				LogThrottled(2, "node", "common extreme extra proc element=" + element)
			EndIf
		EndIf
	EndIf

	; 5.2 關閉新手分支「餘響」＋關閉專精主線：切換後首次命中附帶前一元素附傷。
	If SwitchHitPending && PrevElement >= 1 && PrevElement != element
		SwitchHitPending = False
		Float echo = ESSBNodes.EchoRatio(Self)
		If echo > 0.0
			ApplyDamage(PrevElement, ESSBReactions.BaseMax(Self, PrevElement) * echo \
				* GetDamageMult(PrevElement), targetActor)
			If CachedDebugLevel >= 2
				LogThrottled(2, "node", "common echo element=" + PrevElement + " ratio=" + echo)
			EndIf
		EndIf
	EndIf

	; 規劃 1.1 血形態：重擊不消耗耐力，改扣生命（耐力那一半由 ESSB_P_BaseRules 的進入點做）。
	If element == 6 && power
		PayBloodCost(BloodPowerCost())
	EndIf
	; 5.7 關閉大師分支「順勢」：風終焉後 5 秒內接管元素的命中皆附帶一段風刃。
	If (WindFollowLeft > 0 && WindFollowLeft > Utility.GetCurrentRealTime())
		ESSBElem2.WindBlade(Self, targetActor, 1.0)
	EndIf

	; 5.5 持續專精分支「雷暴」與關閉傳奇分支「雷霆」：命中時的額外放電。
	If element == 3 && ESSBElem.StormChance(Self)
		ESSBElem.Discharge(Self, targetActor, GetSelf(1), True, 1.0)
	EndIf
	If (ThunderLeft > 0 && ThunderLeft > Utility.GetCurrentRealTime()) && HasElementMark(targetActor, 3)
		ESSBElem.Discharge(Self, targetActor, GetSelf(1), False, 0.3)
	EndIf

	If CachedDebugLevel >= 2
		If CachedDebugLevel >= 2
			LogThrottled(2, "hit", targetActor.GetFormID() + " element=" + element + " weapon=" + weaponType \
				+ " power=" + power + " left=" + leftHand + " flags=" + aiHitFlagMask + " sync=" + Sync.GetValueInt())
		EndIf
	EndIf
	OnValidHitInternal(targetActor, element, power, hitSlot, hitGeneration)
EndEvent

; 附傷一次：D_hit = B × R × G(L) × M_mod，後兩項（M_ext、抗性）由引擎結算。
; magnitude 在套用前設定在自有法術上（規劃 2.7「G(L) 的實作」、規劃 8「每擊隨機 B」）。
Function ApplyProc(Actor akTarget, Int aiElement, Bool abPower, Bool abSneak, Bool abOpening, Int aiSlot = -1, Int aiGeneration = -1)
	If !TargetProcPossible(aiElement, abPower, abSneak, abOpening)
		Return
	EndIf
	If !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Float b = (ElementDamageMin[aiElement - 1] + ElementDamageMax[aiElement - 1]) * 0.5
	If aiElement == 3
		b = 13.0
	EndIf
	If abPower
		b *= 1.5
	EndIf
	Float full = b * BaseDamageMult.GetValue() * GLevel(aiElement - 1) * GetHitMult(aiElement, akTarget, abPower)
	Float base = PlayerProcBase(aiElement, abPower)
	If aiElement == 6
		base *= GetBloodHitMult()
	EndIf
	If aiElement == 5 && abSneak
		Float sneakMult = ESSBElem2.SneakMult(Self)
		base *= sneakMult
		full *= sneakMult * ESSBElem2.KillStreakMult(Self)
	EndIf
	If abOpening
		full *= ESSBNodes.OpenStrikeMult(Self) * ESSBElem.OpenStrikeMult(Self, aiElement)
	EndIf
	Float bonus = full - base
	If bonus <= 0.0
		Return
	EndIf
	Spell procSpell = HitBonusSpells[aiElement - 1]
	procSpell.SetNthEffectMagnitude(0, bonus)
	If aiElement == 3
		procSpell.SetNthEffectMagnitude(1, DrainAmount(bonus * 0.5))
	EndIf
	ApplyTrackedDamage(ThePlayer(), procSpell, akTarget, aiElement, aiSlot, aiGeneration)
EndFunction

; 這一擊會不會是開印（登記表裡還沒有這個元素）。附傷倍率要在套用前就知道。
Bool Function WillOpen(Actor akTarget, Int aiElement)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return False
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return True
	EndIf
	Return RegElem[slot] != aiElement && !(RegElem2[slot] == aiElement && RegSecondReal[slot])
EndFunction

; 關形態的有效命中（規劃 5.1）：純武藝、破魔、餘燼。
Function OnNoFormHit(Actor akTarget, Weapon akWeapon, Bool abPower)
	; Capture before any spell/native damage can end the casting animation.
	Bool hitCasting = ESSBNodes.Br(Self, 11, 1, 1, 0) && (ESSBNoForm.IsCasting(akTarget) || RecentCast(akTarget))
	Float riposte = 1.0
	If (RiposteLeft > 0 && RiposteLeft > Utility.GetCurrentRealTime()) && Utility.GetCurrentRealTime() < RiposteLeft
		riposte = 1.3
	EndIf
	RiposteLeft = 0
	MarkEngaged(akTarget)
	ApplyNoFormBaseline(akTarget, abPower, riposte)
	Float now = Utility.GetCurrentRealTime()
	; 5.1 純武藝專精分支「節奏」：4 秒內連續命中 3 次。
	If now - ComboTime > 4.0
		ComboHits = 0
	EndIf
	ComboTime = now
	ComboHits += 1
	If ComboHits > 5
		; 「疾攻」最多 -50%，所以連段只算到 5。
		ComboHits = 5
	EndIf
	SetGlobal(GCombo, ComboHits)
	If ComboHits == 3
		ESSBNoForm.OnCombo(Self, ComboHits)
	EndIf
	ESSBNoForm.OnMartialHit(Self, akTarget, akWeapon, abPower, riposte)
	ESSBNoForm.OnManaBreak(Self, akTarget, abPower, hitCasting)
	; 5.1 融斷熟練主線「餘燼」：關閉形態後 N 秒內無形態命中附帶前一元素附傷。
	Float ember = ESSBNoForm.EmberRatio(Self)
	If ember > 0.0 && EmberElem >= 1
		ApplyDamage(EmberElem, ESSBReactions.BaseMax(Self, EmberElem) * ember * GetDamageMult(EmberElem), akTarget)
	EndIf
EndFunction

; fix round 8 documented addition: exact baseline, independent of purchased nodes.
; G and BaseDamageMult are applied only in ApplyTrueDamage; hit dispatcher owns XP.
Function ApplyNoFormBaseline(Actor akTarget, Bool abPower, Float afRiposte = 1.0)
	Float amount = NoformBaseTrue * afRiposte
	If abPower
		amount = amount * 1.5
	EndIf
	ApplyTrueDamage(amount, akTarget, 11, False, False, True)
EndFunction

Bool Function LastHitWasPower()
	Return LastHitPower
EndFunction

Bool Function LastHitWasSneak()
	Return LastHitSneak
EndFunction

; 土風血聖與毒水暗星八棵樹的每次命中掛勾（火冰雷的在 ESSBElem 裡各自處理）。
Function ElementHitHook(Actor akTarget, Int aiElement, Bool abPower)
	If aiElement >= 8 && aiElement <= 11
		ESSBElem3.OnHit(Self, aiElement, akTarget, abPower)
		Return
	EndIf
	If aiElement < 4 || aiElement > 7
		Return
	EndIf
	ESSBElem2.OnHit(Self, aiElement, akTarget, abPower)
	If aiElement == 4
		SyncRockArmor()
	ElseIf aiElement == 5
		; 規劃 1.1：潛行攻擊時風勢直接滿。
		If LastHitSneak
			SetSelf(3, ESSBElem2.WindThreshold(Self))
		EndIf
		; 規劃 2.3：風勢到門檻就送出風刃並歸零。
		ESSBElem2.CheckWindGauge(Self, akTarget)
	EndIf
EndFunction

; 每次有效命中：登記目標、掛「已交戰」標記、開印或刷新、累積元素狀態與同調。
Function OnValidHit(Actor akTarget, Int aiElement, Bool abPower)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	SelfLastHit = Utility.GetCurrentRealTime()
	MarkEngaged(akTarget)
	Int slot = AcquireSlot(akTarget)
	If slot < 0
		Return
	EndIf
	EnsureStatus(slot, akTarget)
	If RegElem[slot] == aiElement || (RegElem2[slot] == aiElement && RegSecondReal[slot])
		ApplyMark(akTarget, aiElement)
		HitStacks(akTarget, aiElement, abPower)
	Else
		InstallMark(slot, aiElement, akTarget)
	EndIf
	; 5.3 持續專精主線：帶熱度目標火抗 -1%／點。
	If aiElement == 1
		ESSBElem.ApplyFireResistShred(Self, akTarget)
	EndIf
	ElementHitHook(akTarget, aiElement, abPower)
	AddSync(1)
	If Trees
		; 規劃 4：開形態的有效命中給當前元素樹 + 通用樹。
		Trees.OnValidHitXP(aiElement)
	EndIf
	If FormActive.GetValueInt() == 1
		ScheduleTick(1.0)
	EndIf
EndFunction

Function InstallMark(Int aiSlot, Int aiElement, Actor akTarget)
	If RegElem[aiSlot] >= 1
		If !ESSBNodes.HasDualMark(Self) || RegElem2[aiSlot] >= 1
			EndMark(aiSlot, 0, 1.0)
		EndIf
	EndIf
	If RegElem[aiSlot] >= 1
		; After promotion the surviving older mark stays primary; the new mark is secondary.
		RegElem2[aiSlot] = aiElement
		RegSeq2[aiSlot] = NextSeq
		NextSeq += 1
		RegSecondReal[aiSlot] = True
		ApplyMark(akTarget, aiElement)
		OpenSecond(aiSlot, aiElement, akTarget)
	Else
		RegElem[aiSlot] = aiElement
		RegSeq[aiSlot] = NextSeq
		NextSeq += 1
		ApplyMark(akTarget, aiElement)
		OpenMark(aiSlot, aiElement, akTarget)
	EndIf
EndFunction

; 規劃 2.2：印記 8 秒，浸濕 10 秒。時長在套用前以 SetNthEffectDuration 設定。
Function ApplyMark(Actor akTarget, Int aiElement, Int aiSlot = -1)
	Actor player = ThePlayer()
	If !player || !MarkSpells || aiElement < 1 || aiElement > MarkSpells.Length
		Return
	EndIf
	Spell markSpell = MarkSpells[aiElement - 1]
	If !markSpell
		Return
	EndIf
	Int slot = aiSlot
	If slot >= 0 && RegActor[slot] != akTarget
		slot = -1
	EndIf
	If slot < 0
		slot = FindSlot(akTarget)
	EndIf
	If slot < 0
		slot = AcquireSlot(akTarget)
	EndIf
	If slot < 0
		Return
	EndIf
	If RegElem[slot] != aiElement && !(RegElem2[slot] == aiElement && RegSecondReal[slot])
		If RegElem[slot] >= 1 && (!ESSBNodes.HasDualMark(Self) || RegElem2[slot] >= 1)
			EndMark(slot, 0, 1.0)
		EndIf
		If RegElem[slot] < 1
			RegElem[slot] = aiElement
			RegSeq[slot] = NextSeq
		Else
			RegElem2[slot] = aiElement
			RegSeq2[slot] = NextSeq
			RegSecondReal[slot] = True
		EndIf
		NextSeq += 1
	EndIf
	Int duration = 8
	If aiElement == 9
		duration = 10
	EndIf
	; 5.2 開啟熟練主線（印記持續 +0.2 秒／點）＋各元素開啟專精主線（同樣 +0.2 秒／點）
	; ＋冰的「寒留」（終焉後接管元素的印記持續 +4 秒，一次性）。
	duration = duration + ESSBNodes.MarkDurationBonus(Self) + ESSBElem.MarkDurationBonus(Self, aiElement)
	If NextMarkBonus > 0
		duration = duration + NextMarkBonus
		NextMarkBonus = 0
	EndIf
	duration = DurationInt(duration)
	If slot >= 0
		If RegElem[slot] == aiElement
			RegMark[slot] = None
			RegUntil[slot] = Utility.GetCurrentRealTime() + duration
		ElseIf RegElem2[slot] == aiElement && RegSecondReal[slot]
			RegMark2[slot] = None
			RegSecondUntil[slot] = Utility.GetCurrentRealTime() + duration
		EndIf
	EndIf
	markSpell.SetNthEffectDuration(0, duration)
	player.DoCombatSpellApply(markSpell, akTarget)
EndFunction

; 同元素再命中的層數（規劃 2.3 的「命中」欄）加上節點修正。
Function HitStacks(Actor akTarget, Int aiElement, Bool abPower)
	Int amount = 1
	If abPower && (aiElement == 1 || aiElement == 2)
		amount = 2
	EndIf
	If aiElement == 1
		AddStack(akTarget, 1, ESSBElem.HitStacks(Self, 1, abPower))
	ElseIf aiElement == 2
		amount = ESSBElem.HitStacks(Self, 2, abPower)
		If IsEnvStormy()
			amount = amount * 2
		EndIf
		AddStack(akTarget, 2, amount)
	ElseIf aiElement == 3
		AddSelf(1, 1)
	ElseIf aiElement == 4
		AddSelf(2, 1)
	ElseIf aiElement == 5
		AddSelf(3, 1)
	ElseIf aiElement == 6
		AddStack(akTarget, 5, 1)
	ElseIf aiElement == 7
		AddStack(akTarget, 6, 1)
	ElseIf aiElement == 8
		AddStack(akTarget, 7, ESSBElem.HitStacks(Self, 8, abPower))
	ElseIf aiElement == 9
		; 浸濕是單層狀態，命中只刷新時間（規劃 2.3）。
		AddStack(akTarget, 8, 1)
	ElseIf aiElement == 10
		AddStack(akTarget, 10, ESSBElem.HitStacks(Self, 10, abPower))
	ElseIf aiElement == 11
		AddStack(akTarget, 11, ESSBElem.HitStacks(Self, 11, abPower))
	EndIf
	; 火形態：同調三段後每次命中累積 1 過熱（規劃 1.1）。熔身期間過熱不累積（5.3）。
	If aiElement == 1 && SyncStage() >= 3 && MoltenLeft <= 0
		AddSelf(4, 1)
	EndIf
EndFunction

; 各狀態的層數上限（規劃 2.3：基礎 + 該樹分支 + 通用樹「萬象」欄的 +1／每 5 點）。
; 0 代表無上限（毒層）。量表類（凍結）不吃通用樹加成。
Int Function StackCap(Int aiKind)
	If aiKind == 1
		Return ESSBElem.HeatCap(Self)
	ElseIf aiKind == 2
		Return 5
	ElseIf aiKind == 5
		Return ESSBElem2.BleedCap(Self)
	ElseIf aiKind == 6
		Return ESSBElem2.HolyCap(Self)
	ElseIf aiKind == 7
		Return 0
	ElseIf aiKind == 9
		Return ESSBElem3.PressureCap(Self)
	ElseIf aiKind == 10
		Return ESSBElem3.CurseCap(Self)
	ElseIf aiKind == 11
		Return ESSBElem3.AstralCap(Self)
	EndIf
	Return 1
EndFunction

; ---------------------------------------------------------------- 登記表

Int Function FindSlot(Actor akTarget)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return -1
	EndIf
	Int index = 0
	While index < 8
		If RegActor[index] == akTarget
			Return index
		EndIf
		index += 1
	EndWhile
	Return -1
EndFunction

Int Function RegistryCount()
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return 0
	EndIf
	Int total = 0
	Int index = 0
	While index < 8
		If RegActor[index]
			total += 1
		EndIf
		index += 1
	EndWhile
	Return total
EndFunction

Int Function AcquireSlot(Actor akTarget)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return -1
	EndIf
	Int free = -1
	Int oldest = -1
	Int oldestSeq = 0
	Int index = 0
	While index < 8
		If RegActor[index] == akTarget
			Return index
		EndIf
		If !RegActor[index] && free < 0
			free = index
		EndIf
		If RegActor[index] && (oldest < 0 || RegSeq[index] < oldestSeq)
			oldest = index
			oldestSeq = RegSeq[index]
		EndIf
		index += 1
	EndWhile
	If free >= 0
		OccupySlot(free, akTarget)
		Return free
	EndIf
	If oldest < 0
		Return -1
	EndIf
	; 規劃 2.2：第 9 個目標被開印時，最舊的印記提前過期並觸發過期終焉。
	If CachedDebugLevel >= 1
		LogEvent(1, "evict", "slot=" + oldest + " target=" + RegActor[oldest].GetFormID() \
			+ " element=" + RegElem[oldest] + " for=" + akTarget.GetFormID())
	EndIf
	Actor victim = RegActor[oldest]
	Int generation = RegGeneration[oldest]
	EndBothMarks(oldest, 1.0, 3)
	If RegActor[oldest] != victim || RegGeneration[oldest] != generation
		Return -1
	EndIf
	ClearSlot(oldest)
	OccupySlot(oldest, akTarget)
	Return oldest
EndFunction

Function OccupySlot(Int aiSlot, Actor akTarget)
	RegGeneration[aiSlot] = RegGeneration[aiSlot] + 1
	RegLastDamage[aiSlot] = LastDamageFor(akTarget)
	RegActor[aiSlot] = akTarget
	RegElem[aiSlot] = 0
	RegSeq[aiSlot] = NextSeq
	NextSeq += 1
	RegLastOpen[aiSlot] = -100.0
	RegLastEnd[aiSlot] = -100.0
	RegPendElem[aiSlot] = 0
	RegPendAmt[aiSlot] = 0
EndFunction

Function ClearSlot(Int aiSlot)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If RegActor[aiSlot] && RegActor[aiSlot].IsDead()
		CaptureDeath(aiSlot)
	EndIf
	ClearPendingState(aiSlot)
	BackupValid[aiSlot] = False
	If SwapSlot == aiSlot
		CancelSwap()
	EndIf
	RegGeneration[aiSlot] = RegGeneration[aiSlot] + 1
	RegUntil[aiSlot] = 0.0
	RegPendStarLock[aiSlot] = 0
	RegPendWetLock[aiSlot] = False
	RegHostPending[aiSlot] = False
	RegLastDamage[aiSlot] = 0
	RegActor[aiSlot] = None
	RegElem[aiSlot] = 0
	RegSeq[aiSlot] = 0
	RegMark[aiSlot] = None
	RegStatus[aiSlot] = None
	RegPendElem[aiSlot] = 0
	RegPendAmt[aiSlot] = 0
	RegLastOpen[aiSlot] = -100.0
	RegLastEnd[aiSlot] = -100.0
	ClearSecond(aiSlot)
EndFunction

; 開印：每個目標 1 秒內部冷卻（規劃 2.6）。
Function OpenMark(Int aiSlot, Int aiElement, Actor akTarget)
	Float now = Utility.GetCurrentRealTime()
	If now - RegLastOpen[aiSlot] < CooldownSeconds(1.0)
		If CachedDebugLevel >= 3
			LogThrottled(3, "open", akTarget.GetFormID() + " refused cooldown element=" + aiElement)
		EndIf
		RegElem[aiSlot] = aiElement
		Return
	EndIf
	RegLastOpen[aiSlot] = now
	RegElem[aiSlot] = aiElement
	RegSeq[aiSlot] = NextSeq
	NextSeq += 1
	If Trees
		; 規劃 4：開印給新印記元素樹 + 通用樹。
		Trees.OnOpenXP(aiElement)
	EndIf
	ESSBReactions.Open(Self, aiElement, akTarget)
	AfterOpen(aiElement, akTarget)
EndFunction

; 副印記的開印（雙印）：不占登記名額、不做終焉，其餘與主印記相同。
Function OpenSecond(Int aiSlot, Int aiElement, Actor akTarget)
	Float now = Utility.GetCurrentRealTime()
	If now - RegLastOpen[aiSlot] < CooldownSeconds(1.0)
		Return
	EndIf
	RegLastOpen[aiSlot] = now
	If Trees
		Trees.OnOpenXP(aiElement)
	EndIf
	ESSBReactions.Open(Self, aiElement, akTarget)
	AfterOpen(aiElement, akTarget)
EndFunction

; 開印之後的通用樹節點：先制／開印同調、廣印、餘電。
Function AfterOpen(Int aiElement, Actor akTarget)
	Int bonus = ESSBNodes.OpenSyncBonus(Self)
	If bonus > 0
		AddSync(bonus)
	EndIf
	; 5.5 關閉專精分支「餘電」：雷終焉後接管元素的開印附帶一次 ×0.5 放電。
	If PendingDischarge > 0
		Int charge = PendingDischarge
		PendingDischarge = 0
		ESSBElem.Discharge(Self, akTarget, charge, False, 0.5)
	EndIf
	; 5.2 開啟新手分支「廣印」：開印時擴散到附近 1 人。
	; InSpread 擋住「擴散出去的開印又再擴散」的連鎖，一次命中最多多一個目標。
	If ESSBNodes.HasWideMark(Self) && !InSpread
		InSpread = True
		Actor[] nearby = ScanTargets(akTarget, 1050.0, 1, akTarget)
		If nearby[0] && !HasElementMark(nearby[0], aiElement)
			ForceOpenOn(nearby[0], aiElement)
		EndIf
		InSpread = False
	EndIf
EndFunction

; 對一個還沒登記的目標直接開印（火臨／冰臨／雷臨、廣印、雙斷共用）。
Function ForceOpenOn(Actor akTarget, Int aiElement)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !akTarget || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Int slot = AcquireSlot(akTarget)
	If slot < 0
		Return
	EndIf
	EnsureStatus(slot, akTarget)
	MarkEngaged(akTarget)
	If RegElem[slot] == aiElement || (RegElem2[slot] == aiElement && RegSecondReal[slot])
		ApplyMark(akTarget, aiElement)
		Return
	EndIf
	InstallMark(slot, aiElement, akTarget)
EndFunction

; 終焉：aiReason 0 被切掉、1 融斷、2 自然過期、3 第 9 目標逐出（視同過期）。
Function EndMark(Int aiSlot, Int aiReason, Float afMult, ESSBMark akFinishing = None)
	FinishMark(aiSlot, False, aiReason, afMult, TakeEndSlot(aiSlot), False, akFinishing)
EndFunction

Bool Function TakeEndSlot(Int aiSlot)
	Float now = Utility.GetCurrentRealTime()
	If now - RegLastEnd[aiSlot] < CooldownSeconds(1.0)
		Return False
	EndIf
	RegLastEnd[aiSlot] = now
	Return True
EndFunction

; Both marks in one Z burst share one cooldown reservation.
Function EndBothMarks(Int aiSlot, Float afMult, Int aiReason = 1)
	Actor target = RegActor[aiSlot]
	Int generation = RegGeneration[aiSlot]
	Bool allowed = TakeEndSlot(aiSlot)
	; Expiry settles real marks only; a residual echo has no independent expiry.
	If aiReason != 3 || RegSecondReal[aiSlot]
		FinishMark(aiSlot, True, aiReason, afMult, allowed, False)
	EndIf
	If RegActor[aiSlot] != target || RegGeneration[aiSlot] != generation
		Return
	EndIf
	FinishMark(aiSlot, False, aiReason, afMult, allowed, False)
EndFunction

; All chain ends consume the matching mark through this same cooldown gate.
Function EndLinkedMark(Actor akTarget, Int aiElement, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	If RegElem[slot] == aiElement
		FinishMark(slot, False, 2, afMult, TakeEndSlot(slot), True)
	ElseIf RegElem2[slot] == aiElement
		FinishMark(slot, True, 2, afMult, TakeEndSlot(slot), True)
	EndIf
EndFunction

Function FinishMark(Int aiSlot, Bool abSecond, Int aiReason, Float afMult, Bool abAllowed, Bool abChain, ESSBMark akFinishing = None)
	Actor target = RegActor[aiSlot]
	Int generation = RegGeneration[aiSlot]
	Int element = RegElem[aiSlot]
	Int sequence = RegSeq[aiSlot]
	ESSBMark mark = RegMark[aiSlot]
	Bool realMark = True
	If abSecond
		element = RegElem2[aiSlot]
		sequence = RegSeq2[aiSlot]
		mark = RegMark2[aiSlot]
		realMark = RegSecondReal[aiSlot]
	EndIf
	If !target || element < 1
		Return
	EndIf
	Bool dead = target.IsDead()
	If dead
		CaptureDeath(aiSlot)
	EndIf
	; Detach and promote before any cross-script call can deliver an AME callback.
	If abSecond
		ClearSecond(aiSlot)
	Else
		RegElem[aiSlot] = 0
		RegMark[aiSlot] = None
		RegUntil[aiSlot] = 0.0
		If RegElem2[aiSlot] >= 1 && RegSecondReal[aiSlot]
			RegElem[aiSlot] = RegElem2[aiSlot]
			RegSeq[aiSlot] = RegSeq2[aiSlot]
			RegMark[aiSlot] = RegMark2[aiSlot]
			RegUntil[aiSlot] = RegSecondUntil[aiSlot]
			ClearSecond(aiSlot)
		EndIf
	EndIf
	; A finish callback still settles End, but must never dispel its own dead AME.
	If !akFinishing || mark != akFinishing
		If mark
			mark.DispelIfActive()
		ElseIf realMark
			target.DispelSpell(MarkSpells[element - 1])
		EndIf
	EndIf
	If dead
		Return
	EndIf
	If element == 9
		Bool keepWet = aiReason == 0 && abAllowed && ESSBNodes.Br(Self, 8, 2, 2, 0)
		If RegPendWetLock[aiSlot] && !keepWet
			PendingStacks[aiSlot * 12 + 8] = 0
		EndIf
		RegPendWetLock[aiSlot] = False
		ESSBStatus waterStatus = GetStatus(target)
		If waterStatus
			waterStatus.ReleaseWetLock(keepWet)
		EndIf
	EndIf
	If dead || target.IsDead() || !abAllowed
		Return
	EndIf
	If Trees
		Trees.OnEndXP(element)
	EndIf
	ESSBReactions.End(Self, element, target, aiReason, afMult, abChain)
	PlaceFx(element, target)
	If RegActor[aiSlot] != target || RegGeneration[aiSlot] != generation
		Return
	EndIf
	If aiReason == 0 && !abChain && ESSBNodes.HasResidualMark(Self) && RegElem2[aiSlot] < 1
		RegElem2[aiSlot] = element
		RegSeq2[aiSlot] = sequence
		RegSecondUntil[aiSlot] = Utility.GetCurrentRealTime() + DurationSeconds(4.0)
		RegSecondReal[aiSlot] = False
	EndIf
EndFunction

; 副印記的終焉（融斷時、或副印記過期時）。
Function EndSecondMark(Int aiSlot, Int aiReason, Float afMult, ESSBMark akFinishing = None)
	FinishMark(aiSlot, True, aiReason, afMult, TakeEndSlot(aiSlot), False, akFinishing)
EndFunction

Function ClearSecond(Int aiSlot)
	RegSecondReal[aiSlot] = False
	RegElem2[aiSlot] = 0
	RegSeq2[aiSlot] = 0
	RegSecondUntil[aiSlot] = 0.0
	RegMark2[aiSlot] = None
EndFunction

; ---------------------------------------------------------------- 印記 AME 回報

Function OnMarkStart(Int aiElement, Actor akTarget, ESSBMark akMark)
	If !IsOperational()
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		akMark.DispelIfActive()
		Return
	EndIf
	If RegElem[slot] == aiElement
		RegMark[slot] = akMark
	ElseIf RegElem2[slot] == aiElement && RegSecondReal[slot]
		RegMark2[slot] = akMark
	Else
		akMark.DispelIfActive()
	EndIf
EndFunction

Function OnMarkFinish(Int aiElement, Actor akTarget, ESSBMark akMark)
	If !IsOperational()
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	If RegElem[slot] == aiElement && RegMark[slot] == akMark
		If akTarget.IsDead()
			CaptureDeath(slot)
			Return
		EndIf
		EndMark(slot, 2, 1.0, akMark)
	ElseIf RegElem2[slot] == aiElement && RegMark2[slot] == akMark
		If akTarget.IsDead()
			CaptureDeath(slot)
			Return
		EndIf
		EndSecondMark(slot, 2, 1.0, akMark)
	EndIf
	; Keep the status host registered: pending DoT/death curse must survive mark expiry.
EndFunction

; ---------------------------------------------------------------- 狀態容器

Function EnsureStatus(Int aiSlot, Actor akTarget)
	If RegStatus[aiSlot] || !StatusHostSpell || RegHostPending[aiSlot]
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	RegHostPending[aiSlot] = True
	RegHostRequest[aiSlot] = Utility.GetCurrentRealTime()
	player.DoCombatSpellApply(StatusHostSpell, akTarget)
EndFunction

Function OnStatusStart(Actor akTarget, ESSBStatus akStatus)
	If !IsOperational()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		If SwapActor == akTarget
			CancelSwap()
		EndIf
		akStatus.PrepareSwap()
		akStatus.DispelIfActive()
		Return
	EndIf
	If RegStatus[slot] && RegStatus[slot] != akStatus
		akStatus.PrepareSwap()
		akStatus.DispelIfActive()
		Return
	EndIf
	Int generation = RegGeneration[slot]
	If BackupValid[slot]
		Int[] savedInts = ReadSwapInts(slot)
		Float[] savedFloats = ReadSwapFloats(slot)
		akStatus.ImportState(savedInts, savedFloats)
		akStatus.RebaseImportedClock()
		If RegActor[slot] != akTarget || RegGeneration[slot] != generation
			akStatus.PrepareSwap()
			akStatus.DispelIfActive()
			Return
		EndIf
		BackupValid[slot] = False
	EndIf
	If SwapSlot == slot && SwapActor == akTarget && SwapGeneration == generation
		CancelSwap()
	EndIf
	RegStatus[slot] = akStatus
	RegHostPending[slot] = False
	Float starLock = RegPendStarLock[slot]
	Bool wetLock = RegPendWetLock[slot]
	RegPendStarLock[slot] = 0
	RegPendWetLock[slot] = False
	If starLock > 0
		akStatus.SetStarLock(0, starLock)
	EndIf
	If wetLock
		akStatus.SetWetLock()
	EndIf
	If RegActor[slot] == akTarget && RegGeneration[slot] == generation
		FlushPendingState(slot, akStatus)
	EndIf
EndFunction

Function OnStatusFinish(Actor akTarget, ESSBStatus akStatus)
	If !IsOperational()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	If RegStatus[slot] == akStatus
		If akTarget.IsDead()
			CaptureDeath(slot)
		EndIf
		RegStatus[slot] = None
	EndIf
EndFunction

ESSBStatus Function GetStatus(Actor akTarget)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return None
	EndIf
	Return RegStatus[slot]
EndFunction

Function AddStack(Actor akTarget, Int aiKind, Int aiAmount)
	Int slot = FindSlot(akTarget)
	If slot < 0 || aiKind < 1 || aiKind > 11
		Return
	EndIf
	If aiKind == 11
		AddAstral(akTarget, aiAmount, 1.0)
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.AddStack(aiKind, aiAmount)
	Else
		Int pos = slot * 12 + aiKind
		PendingStacks[pos] = PendingStacks[pos] + aiAmount
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Int Function GetStack(Actor akTarget, Int aiKind)
	Int slot = FindSlot(akTarget)
	If slot < 0 || aiKind < 1 || aiKind > 11
		Return 0
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		Return status.GetStack(aiKind)
	EndIf
	If aiKind == 11
		Return PendingAstral[slot]
	EndIf
	Return PendingStacks[slot * 12 + aiKind]
EndFunction

Bool Function IsWet(Actor akTarget)
	Return GetStack(akTarget, 8) > 0
EndFunction

; 宿主只有 30 秒：每目標約 25 秒搬一次家，不是每次命中都搬。
Function CancelSwap()
	SwapSlot = -1
	SwapActor = None
	; SwapInts is legacy; SwapFloats holds damage timestamps. Per-slot backups own swap state.
	SwapStarted = 0.0
EndFunction

Function SwapHosts()
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If SwapSlot >= 0
		If RegActor[SwapSlot] != SwapActor || RegGeneration[SwapSlot] != SwapGeneration
			CancelSwap()
		ElseIf now >= SwapDeadline
			CancelSwap()
		ElseIf now - SwapStarted >= 3.0
			; Missing start callback: retry while retaining the exported state and identity.
			RegHostPending[SwapSlot] = False
			EnsureStatus(SwapSlot, SwapActor)
			SwapStarted = now

		EndIf
		If SwapSlot >= 0
			Return
		EndIf
	EndIf
	Int index = 0
	While index < 8
		Actor target = RegActor[index]
		ESSBStatus status = RegStatus[index]
		If target && !status
			If RegHostPending[index] && now - RegHostRequest[index] >= 3.0
				RegHostPending[index] = False
			EndIf
			EnsureStatus(index, target)
		ElseIf status && target && SwapSlot < 0 && status.IsStale(25.0)
			SwapSlot = index
			SwapActor = target
			Int generation = RegGeneration[index]
			SwapGeneration = generation
			SwapStarted = now
			SwapDeadline = now + 9.0
			status.PrepareSwap()
			Int[] exportedInts = status.ExportInts()
			Float[] exportedFloats = status.ExportFloats()
			If RegActor[index] == target && RegGeneration[index] == generation \
				&& SwapSlot == index && SwapActor == target && SwapGeneration == generation
				SaveSwapData(index, exportedInts, exportedFloats)
				RegStatus[index] = None
				RegHostPending[index] = False
				status.DispelIfActive()
				EnsureStatus(index, target)
			ElseIf SwapSlot == index && SwapActor == target && SwapGeneration == generation
				CancelSwap()
			EndIf
		EndIf
		index += 1
	EndWhile
EndFunction

; ---------------------------------------------------------------- 傷害與法術套用封裝

; 所有反應傷害都走自有的 ESSB_React_<元素>：執行期設 magnitude 後 DoCombatSpellApply。
; G(L) 與 BaseDamageMult 在這裡各乘一次；呼叫端與延遲狀態只存未乘倍率的值。
Function ApplyDamage(Int aiElement, Float afAmount, Actor akTarget, Int aiKillProc = 0)
	; 5.7 傳奇分支「御風」與「空中追擊」：失衡／浮空目標受你所有傷害放大。
	; 5.12 持續專精主線、5.13「星鎖」與「星域」同樣只放大本模組造成的傷害（決定 61）。
	Float amount = afAmount * BaseDamageMult.GetValue() * GLevel(ESSBNodes.TreeOf(aiElement)) \
		* ESSBElem2.TargetDamageMult(Self, akTarget) \
		* ESSBElem3.TargetDamageMult(Self, akTarget)
	If aiKillProc > 0
		ArmKillProc(akTarget, aiKillProc, afAmount, amount)
	EndIf
	ApplyDamageRaw(aiElement, amount, akTarget)
EndFunction

; Raw delivery never adds G(L) or BaseDamageMult; overheat self damage is not B-derived.
Function ApplyDamageRaw(Int aiElement, Float afAmount, Actor akTarget)
	If aiElement < 1 || aiElement > 11 || !akTarget || afAmount <= 0.0
		Return
	EndIf
	If !ReactSpells || aiElement > ReactSpells.Length
		Return
	EndIf
	Spell reactSpell = ReactSpells[aiElement - 1]
	Actor player = ThePlayer()
	If aiElement == 1 && akTarget == player
		reactSpell = OverheatSelfSpell
	EndIf
	If !reactSpell || !player
		Return
	EndIf
	reactSpell.SetNthEffectMagnitude(0, afAmount)
	ApplyTrackedDamage(player, reactSpell, akTarget, aiElement)
	If CachedDebugLevel >= 3
		LogThrottled(3, "damage", akTarget.GetFormID() + " element=" + aiElement + " amount=" + afAmount)
	EndIf
EndFunction

; 真實傷害（規劃 2.8）：D_true = 基準 × G(L_無元素) × M_mod(無元素樹)。
; 沒有 M_ext、沒有 Res。走自有 ESSB_TrueSpell，是本模組唯一允許扣生命的路徑。
; aiTree 預設 11（無元素樹）；5.13「星斷」以星樹（10）的 G(L) 計，並且不吃無元素樹的
; 「目標魔力 <25%」加成，因為那是破魔路線的節點。
Function ApplyTrueDamage(Float afAmount, Actor akTarget, Int aiTree = 11, Bool abGrantXP = True, Bool abLevelScaled = False, Bool abBaseline = False)
	If !akTarget || afAmount <= 0.0 || !TrueSpell
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Float amount = afAmount
	; ManaBreak has already scaled its drain (and clamped to actual magicka).
	If !abLevelScaled
		amount = amount * GLevel(aiTree)
	EndIf
	; Baseline has its own exact formula; existing node damage retains TrueMult.
	If aiTree == 11 && !abBaseline
		amount = amount * ESSBNoForm.TrueMult(Self, akTarget)
	EndIf
	amount = amount * BaseDamageMult.GetValue()
	If amount <= 0.0
		Return
	EndIf
	TrueSpell.SetNthEffectMagnitude(0, amount)
	ApplyTrackedDamage(player, TrueSpell, akTarget, 0)
	; 規劃 4：造成真實傷害練無元素樹。
	If Trees && abGrantXP
		Trees.OnValidHitXP(0)
	EndIf
	; 5.1 破魔傳奇分支「逆流」：真實傷害的 50% 轉為你的生命。
	If ESSBNodes.Br(Self, 11, 1, 4, 1)
		ApplyUtil(4, amount * 0.5, 0, player)
	EndIf
	If CachedDebugLevel >= 2
		LogThrottled(2, "true", akTarget.GetFormID() + " amount=" + amount)
	EndIf
EndFunction

; 破魔印 8 秒（ESSBCounter）。
Function ApplyManaBreakMark(Actor akTarget)
	Actor player = ThePlayer()
	If player && ManaBreakSpell && akTarget
		ManaBreakSpell.SetNthEffectDuration(0, DurationInt(8))
		player.DoCombatSpellApply(ManaBreakSpell, akTarget)
	EndIf
EndFunction

; The native active mark is the per-target expiry authority (including duration scaling).
Bool Function CounterEligible(Actor akTarget)
	Return akTarget && !akTarget.IsDead() && ManaBreakSpell && akTarget.HasMagicEffect(ManaBreakSpell.GetNthEffectMagicEffect(0))
EndFunction

Function StartCounter(Actor akTarget)
	If !IsOperational() || !CounterEligible(akTarget) || !ESSBNodes.Br(Self, 11, 1, 1, 2)
		Return
	EndIf
	RegisterForAnimationEvent(akTarget, "MRh_SpellFire_Event")
	RegisterForAnimationEvent(akTarget, "MLh_SpellFire_Event")
	; Finish may have run while registration yielded; clean the just-created pair.
	StopCounter(akTarget)
EndFunction

Function StopCounter(Actor akTarget)
	If !IsCurrentController() || !akTarget
		Return
	EndIf
	; A refreshed mark remains eligible; an old AME finish must not unregister it.
	If !IsOperational() || !CounterEligible(akTarget)
		UnregisterForAnimationEvent(akTarget, "MRh_SpellFire_Event")
		UnregisterForAnimationEvent(akTarget, "MLh_SpellFire_Event")
	EndIf
EndFunction

Event OnAnimationEvent(ObjectReference akSource, String asEventName)
	If !IsOperational()
		Return
	EndIf
	If asEventName != "MRh_SpellFire_Event" && asEventName != "MLh_SpellFire_Event"
		Return
	EndIf
	Actor target = akSource as Actor
	RememberCast(target)
	If !CounterEligible(target)
		StopCounter(target)
		Return
	EndIf
	Int hand = 1
	If asEventName == "MLh_SpellFire_Event"
		hand = 0
	EndIf
	Spell castSpell = target.GetEquippedSpell(hand)
	If castSpell
		Float cost = castSpell.GetEffectiveMagickaCost(target) as Float
		; Recheck after native queries before dispatching damage.
		If IsOperational() && CounterEligible(target)
			ESSBNoForm.OnCounterSpell(Self, target, cost)
		EndIf
	EndIf
EndEvent

; 沉默 N 秒（ESSBSilence + MagickaRateMult -100）。首領減半（規劃 8）。
Function ApplySilenceSpell(Actor akTarget, Int aiSeconds)
	Actor player = ThePlayer()
	If !player || !SilenceSpell || !akTarget || aiSeconds < 1
		Return
	EndIf
	Int duration = aiSeconds
	If IsVIPTarget(akTarget)
		duration = duration / 2
		If duration < 1
			duration = 1
		EndIf
	EndIf
	duration = DurationInt(duration)
	SilenceSpell.SetNthEffectDuration(0, duration)
	SilenceSpell.SetNthEffectDuration(1, duration)
	player.DoCombatSpellApply(SilenceSpell, akTarget)
EndFunction

; fix round 7: category delivery helpers never apply G(L).
Float Function CooldownSeconds(Float afSeconds)
	Return afSeconds * MultCooldown.GetValue()
EndFunction

Float Function DurationSeconds(Float afSeconds)
	If afSeconds <= 0.0
		Return 0.0
	EndIf
	Float scale = CachedDuration
	If !RuntimeCacheReady
		scale = MultDuration.GetValue()
	EndIf
	Float seconds = afSeconds * scale
	If seconds < 1.0
		seconds = 1.0
	EndIf
	Return seconds
EndFunction

Int Function DurationInt(Float afSeconds)
	Float seconds = DurationSeconds(afSeconds)
	Return (seconds + 0.5) as Int
EndFunction

Float Function RecoveryAmount(Float afAmount)
	Return afAmount * MultRecovery.GetValue()
EndFunction

Float Function DrainAmount(Float afAmount)
	Return afAmount * MultDrain.GetValue()
EndFunction

Function ApplyDotDamage(Int aiElement, Float afAmount, Actor akTarget)
	ApplyDamage(aiElement, afAmount * MultDot.GetValue(), akTarget)
EndFunction

Function ApplyUtil(Int aiIndex, Float afMagnitude, Int aiDuration, Actor akTarget, Bool abBalanced = False)
	If !UtilSpells || aiIndex < 0 || aiIndex >= UtilSpells.Length || !akTarget || afMagnitude <= 0.0
		Return
	EndIf
	Spell utilSpell = UtilSpells[aiIndex]
	Actor player = ThePlayer()
	If akTarget != player && UtilTargetSpells
		If aiIndex == 4
			utilSpell = UtilTargetSpells[0]
		ElseIf aiIndex == 6
			utilSpell = UtilTargetSpells[1]
		ElseIf aiIndex == 27
			utilSpell = UtilTargetSpells[2]
		EndIf
	EndIf
	If !utilSpell || !player
		Return
	EndIf
	; All mod movement slows share this single Peak Value Modifier effect.
	; Same effect uses the strongest magnitude; it does not add across casts.
	If aiIndex == 0
		Float cap = SlowCapPct.GetValue()
		If cap > 70.0
			cap = 70.0
		ElseIf cap < 0.0
			cap = 0.0
		EndIf
		If afMagnitude > cap
			afMagnitude = cap
		EndIf
	EndIf
	If !abBalanced
		If aiIndex == 4 || aiIndex == 5 || aiIndex == 6 || aiIndex == 18 || aiIndex == 19 || aiIndex == 10 || aiIndex == 11 || aiIndex == 25
			afMagnitude = RecoveryAmount(afMagnitude)
		ElseIf aiIndex == 1 || aiIndex == 2 || aiIndex == 3
			afMagnitude = DrainAmount(afMagnitude)
		ElseIf aiIndex == 7
			afMagnitude = afMagnitude * MultDot.GetValue() * BaseDamageMult.GetValue()
		EndIf
	EndIf
	utilSpell.SetNthEffectMagnitude(0, afMagnitude)
	If aiDuration > 0
		utilSpell.SetNthEffectDuration(0, DurationInt(aiDuration))
	EndIf
	If aiIndex == 7
		ApplyTrackedDamage(player, utilSpell, akTarget, 6)
	Else
		player.DoCombatSpellApply(utilSpell, akTarget)
	EndIf
EndFunction

; 放血：不吃 G(L) 與抗性，走 resist = none 的自有法術，不直接 DamageActorValue。
Function ApplyBleedDrain(Actor akTarget, Float afAmount)
	ApplyUtil(7, afAmount, 0, akTarget)
EndFunction

; 碎冰處決（規劃 2.6）：首領與必要角色由呼叫端改走傷害，不會走到這裡。
; 用自有的高強度傷害法術殺，不用 Kill()：擊殺歸屬、死亡事件、化灰與復生的判定
; 都與一般擊殺一致，外部天賦（如擊殺回復）也照常成立。
Function Execute(Actor akTarget, Int aiElement)
	Actor player = ThePlayer()
	If !akTarget || !player
		Return
	EndIf
	Float lethal = akTarget.GetActorValue("Health") * 10.0 + 1000.0
	If CachedDebugLevel >= 1
		LogEvent(1, "execute", akTarget.GetFormID() + " element=" + aiElement + " magnitude=" + lethal)
	EndIf
	If TrueSpell
		TrueSpell.SetNthEffectMagnitude(0, lethal)
		ApplyTrackedDamage(player, TrueSpell, akTarget, aiElement)
	EndIf
EndFunction

; ---------------------------------------------------------------- 公式掛勾

; M_mod：本模組節點加成合計。技能樹屬機制前線，本前線只提供環境加成與血位倍率，
; 之後的節點加成接在同一個函式裡，公式其他項不必改（規劃 2.7）。
Float Function GetDamageMult(Int aiElement)
	Float mult = 1.0
	; 5.8 持續熟練分支「飲血」的 10 秒「嗜血」：命中效果 +20%，不受血位影響。
	If (BloodthirstLeft > 0 && BloodthirstLeft > Utility.GetCurrentRealTime())
		mult = mult * 1.2
	EndIf
	If aiElement == 6
		mult = mult * GetBloodHitMult()
	ElseIf aiElement == 7 && EnvNight.GetValueInt() == 0
		; 白天神聖附傷 +20%（規劃 2.10）
		mult = mult * 1.2
	ElseIf aiElement == 10 && EnvNight.GetValueInt() == 1
		; 夜晚黑暗附傷 +20%（規劃 2.10）
		mult = mult * 1.2
	EndIf
	Return mult
EndFunction

; 附傷專用的 M_mod：共通項 × 通用樹 × 該元素樹（規劃 2.7）。
; 一次乘完，不出現「A 加成再乘 B 加成再乘 A」的疊乘。
Float Function GetHitMult(Int aiElement, Actor akTarget, Bool abPower)
	Float mult = GetDamageMult(aiElement) * ESSBNodes.CommonHitMult(Self, aiElement, abPower) \
		* ESSBElem.HitMult(Self, aiElement, akTarget, abPower) \
		* ESSBElem2.TargetDamageMult(Self, akTarget) \
		* ESSBElem3.TargetDamageMult(Self, akTarget)
	; 各元素關閉專精主線「終焉後 5 秒內接管元素附傷 +1%／點」：加成隨終焉的元素結算好存起來，
	; 之後不管接管的是哪個元素都吃同一份（規劃 2.6 的「接管元素」語意）。
	If (EndBoostLeft > 0 && EndBoostLeft > Utility.GetCurrentRealTime())
		mult = mult * (1.0 + EndBoostAmount)
	EndIf
	Return mult
EndFunction

; ---------------------------------------------------------------- 節點框架的讀取入口

Int Function Rank(Int aiTree, Int aiRoute, Int aiTier)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12 || aiRoute < 0 || aiRoute > 2 || aiTier < 0 || aiTier > 4
		Return 0
	EndIf
	If aiTree == 11 && aiRoute < 2 && FormActive.GetValueInt() == 1
		Return 0
	EndIf
	Int i = aiTree * 15 + aiRoute * 5 + aiTier
	If i < 120
		Return RankCacheA[i]
	EndIf
	Return RankCacheB[i - 120]
EndFunction

Bool Function Br(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12 || aiRoute < 0 || aiRoute > 2 || aiTier < 0 || aiTier > 4 || aiIndex < 0 || aiIndex > 3
		Return False
	EndIf
	If aiTree == 11 && aiRoute < 2 && FormActive.GetValueInt() == 1
		Return False
	EndIf
	Int i = aiTree * 15 + aiRoute * 5 + aiTier
	Int bits = 0
	If i < 120
		bits = BranchCacheA[i]
	Else
		bits = BranchCacheB[i - 120]
	EndIf
	Int divisor = 1
	If aiIndex == 1
		divisor = 2
	ElseIf aiIndex == 2
		divisor = 4
	ElseIf aiIndex == 3
		divisor = 8
	EndIf
	Int quotient = bits / divisor
	Return quotient % 2 == 1
EndFunction

; G(L) = 1 + 0.05 × 樹等級（規劃 2.7）。
Float Function GLevel(Int aiTree)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12
		Return 1.0
	EndIf
	Return 1.0 + 0.05 * LevelMirror[aiTree]
EndFunction

; 形態開／切／關與技能樹選單關閉時各跑一次，不在命中路徑上（規劃 2.2 的負載守則）。
Function RefreshTrees()
	RefreshRuntimeValues()
	If !Trees
		Return
	EndIf
	Int element = CurrentElement.GetValueInt()
	Int tree = 11
	If FormActive.GetValueInt() == 1 && element >= 1 && element <= 11
		tree = element - 1
	EndIf
	Trees.RefreshActive(tree)
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

; 自有常駐能力（抗咒、溫血、感應）：條件變動時加掛或移除，不用條件式常駐能力，
; 避免規劃 1.1.1 說的「條件引擎每秒才重算一次」延遲。
Function RefreshRecovery()
	Actor player = ThePlayer()
	If !player || !Trees
		Return
	EndIf
	Float mult = MultRecovery.GetValue()
	Perk ice = Trees.GetBranch(1, 0, 3, 0)
	Perk shock = Trees.GetBranch(2, 0, 3, 0)
	Perk water = Trees.GetBranch(8, 0, 3, 0)
	Perk holy = Trees.GetBranch(6, 0, 1, 1)
	ice.SetNthEntryValue(0, 0, 1.0 - 0.3 * mult)
	shock.SetNthEntryValue(0, 0, 1.0 - 0.15 * mult)
	water.SetNthEntryValue(0, 0, 1.0 - 0.3 * mult)
	Int index = 0
	While index < 5
		holy.SetNthEntryValue(index, 0, 1.0 - 0.1 * mult)
		index += 1
	EndWhile
	player.RemoveSpell(WarmBloodAbility)
	player.RemoveSpell(InductionAbility)
	WarmBloodAbility.SetNthEffectMagnitude(0, RecoveryAmount(20.0))
	InductionAbility.SetNthEffectMagnitude(0, RecoveryAmount(20.0))
	RockArmorShown = -1.0
	SyncRockArmor()
	RefreshAbilities()
	LastRecoveryScale = mult
EndFunction

Function RefreshAbilities()
	If !IsCurrentController()
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Int element = 0
	If FormActive.GetValueInt() == 1
		element = CurrentElement.GetValueInt()
	EndIf
	; 5.1 破魔大師分支「抗咒」：無形態時魔抗 +15%。
	SyncAbility(player, AntiMagicAbility, element == 0 && ESSBNodes.Br(Self, 11, 1, 3, 1))
	; 5.3 持續熟練分支「溫血」：火形態耐力回復 +20%。
	SyncAbility(player, WarmBloodAbility, element == 1 && ESSBNodes.Br(Self, 0, 0, 1, 1))
	; 5.5 持續新手分支「感應」：雷形態魔力回復 +20%。
	; 5.13 持續新手分支「星輝」：星形態魔力回復 +20%，效果完全相同，沿用同一個能力記錄。
	SyncAbility(player, InductionAbility, (element == 3 && ESSBNodes.Br(Self, 2, 0, 0, 0)) \
		|| (element == 11 && ESSBElem3.HasStarlight(Self)))
	; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%。
	SyncAbility(player, PoisonResistAbility, element == 8 && ESSBElem3.HasPoisonImmunity(Self))
	; 規劃 1.1／5.7：風形態的移速與潛行能力。
	RefreshWindAbilities()
	RefreshDivineProtection()
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Function SyncAbility(Actor akPlayer, Spell akAbility, Bool abWanted)
	If !akAbility
		Return
	EndIf
	Bool has = akPlayer.HasSpell(akAbility)
	If abWanted && !has
		akPlayer.AddSpell(akAbility, False)
	ElseIf !abWanted && has
		akPlayer.RemoveSpell(akAbility)
	EndIf
EndFunction

Float Function FormHeldSeconds()
	If FormActive.GetValueInt() != 1 || FormOpenTime <= 0.0
		Return 0.0
	EndIf
	Return Utility.GetCurrentRealTime() - FormOpenTime
EndFunction

; 血位讀值（規劃 1.1）。5.8 持續專精分支「逆流」反轉曲線：低血位命中強、高血位吸血強，
; 只反轉查表用的百分比，損血曲線另走 BloodDrainPercentAt，不受影響。
Float Function BloodPercent()
	Actor player = ThePlayer()
	If !player
		Return 1.0
	EndIf
	Float percent = player.GetActorValuePercentage("Health")
	If ESSBNodes.Br(Self, 5, 0, 2, 0)
		percent = 1.0 - percent
	EndIf
	If percent > 1.0
		percent = 1.0
	ElseIf percent < 0.0
		percent = 0.0
	EndIf
	Return percent
EndFunction

; Phase 1 blood damage uses the approved four HP bands; leech retains its original curve.
Float Function GetBloodHitMult()
	Actor player = ThePlayer()
	If !player
		Return 1.0
	EndIf
	Float percent = BloodPercent()
	Float extra = 1.0
	; 5.8 持續大師分支「血怒」：中血位（30～70%）時命中效果與吸血同時 +15%。
	Float raw = player.GetActorValuePercentage("Health")
	If ESSBNodes.Br(Self, 5, 0, 3, 1) && raw >= 0.3 && raw <= 0.7
		extra = 1.15
	EndIf
	Return BloodBandMult(BloodBand(raw)) * extra
EndFunction

Float Function BloodHitCurve(Float percent)
	If percent >= 0.85
		Return 1.25
	ElseIf percent >= 0.5
		Return 1.1
	ElseIf percent >= 0.2
		Return 0.85
	EndIf
	Return 0.6
EndFunction

; 吸血比例（占附傷）：100% 5%、70% 15%、30% 35%、10% 50%，線性內插。
; 5.8 持續專精主線「吸血比例各血位 +1%／點」、大師分支「血怒」+15%、飲血的「嗜血」+10%。
Float Function GetBloodLeechRatio()
	Actor player = ThePlayer()
	If !player
		Return 0.05
	EndIf
	Float ratio = BloodLeechCurve(BloodPercent())
	ratio = ratio + 0.01 * ESSBNodes.Rank(Self, 5, 0, 2)
	Float raw = player.GetActorValuePercentage("Health")
	If ESSBNodes.Br(Self, 5, 0, 3, 1) && raw >= 0.3 && raw <= 0.7
		ratio = ratio + 0.15
	EndIf
	If (BloodthirstLeft > 0 && BloodthirstLeft > Utility.GetCurrentRealTime())
		ratio = ratio + 0.10
	EndIf
	If ratio > 1.0
		ratio = 1.0
	EndIf
	Return ratio
EndFunction

Float Function BloodLeechCurve(Float percent)
	If percent >= 1.0
		Return 0.05
	ElseIf percent >= 0.7
		Return 0.15 - (percent - 0.7) * 0.3333
	ElseIf percent >= 0.3
		Return 0.35 - (percent - 0.3) * 0.5
	ElseIf percent >= 0.1
		Return 0.50 - (percent - 0.1) * 0.75
	EndIf
	Return 0.5
EndFunction

; ---------------------------------------------------------------- 血形態的損血與吸血（規劃 1.1）

; 損血曲線（占最大生命）：維持每秒 100% 1.0%／70% 0.6%／30% 0.2%／10% 0，
; 重擊一次 8%／5%／2%／0。曲線不受「逆流」影響（規劃 5.8 明寫）。
Float Function BloodDrainCurve(Float percent, Bool abPower)
	Float value = 0.0
	If percent >= 1.0
		value = 1.0
	ElseIf percent >= 0.7
		value = 0.6 + (percent - 0.7) * 1.3333
	ElseIf percent >= 0.3
		value = 0.2 + (percent - 0.3) * 1.0
	ElseIf percent >= 0.1
		value = (percent - 0.1) * 1.0
	EndIf
	If abPower
		; 重擊那一欄是 8／5／2／0，比維持費高 8 倍左右，用同形狀的曲線放大。
		If percent >= 1.0
			value = 8.0
		ElseIf percent >= 0.7
			value = 5.0 + (percent - 0.7) * 10.0
		ElseIf percent >= 0.3
			value = 2.0 + (percent - 0.3) * 7.5
		ElseIf percent >= 0.1
			value = (percent - 0.1) * 10.0
		Else
			value = 0.0
		EndIf
	EndIf
	Return value / 100.0
EndFunction

; 維持每秒損血（給 ESSBFormRules 呼叫）。非血形態回 0。
Float Function BloodDrainPerSecond()
	; 5.8 持續傳奇分支「不死」：同調三段時維持扣血歸零。
	If ESSBNodes.Br(Self, 5, 0, 4, 0) && SyncStage() >= 3
		Return 0.0
	EndIf
	If FormActive.GetValueInt() != 1 || CurrentElement.GetValueInt() != 6
		Return 0.0
	EndIf
	Actor player = ThePlayer()
	If !player
		Return 0.0
	EndIf
	Return BloodDrainCurve(player.GetActorValuePercentage("Health"), False) * BloodCostScale()
EndFunction

; 重擊一次的損血（占最大生命）。
Float Function BloodPowerCost()
	Actor player = ThePlayer()
	If !player
		Return 0.0
	EndIf
	Return BloodDrainCurve(player.GetActorValuePercentage("Health"), True) * BloodCostScale()
EndFunction

; 損血的折扣：血氣分支減半；血臨強化／血約／不死在視窗內歸零。
Float Function BloodCostScale()
	If (NoBloodCostLeft > 0 && NoBloodCostLeft > Utility.GetCurrentRealTime())
		Return 0.0
	EndIf
	If ESSBNodes.Br(Self, 5, 0, 0, 0)
		Return 0.5
	EndIf
	Return 1.0
EndFunction

; 血形態的自身損血：這是規劃 1.1 明定的「維持費」，和真實傷害一樣是本模組少數
; 允許直接動生命的路徑（維持費原本就寫在 ESSBFormRules 裡）。永遠留 1 點生命，
; 不讓維持費自己把玩家打死。
Function PayBloodCost(Float afPercentOfMax)
	If afPercentOfMax <= 0.0
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Float cost = player.GetActorValueMax("Health") * afPercentOfMax
	Float current = player.GetActorValue("Health")
	If cost > current - 1.0
		cost = current - 1.0
	EndIf
	If cost <= 0.0
		Return
	EndIf
	player.DamageActorValue("Health", cost)
	If CachedDebugLevel >= 3
		LogThrottled(3, "blood", "cost=" + cost + " percent=" + afPercentOfMax)
	EndIf
EndFunction

; 吸血：溢出的部分由「血盾」轉為臨時護盾（上限 20% 生命）。
Function Leech(Float afAmount)
	Actor player = ThePlayer()
	If !player || afAmount <= 0.0
		Return
	EndIf
	afAmount = RecoveryAmount(afAmount)
	Float missing = player.GetActorValueMax("Health") - player.GetActorValue("Health")
	Float heal = afAmount
	If heal > missing
		heal = missing
	EndIf
	If heal > 0.0
		ApplyUtil(4, heal, 0, player, True)
	EndIf
	; 5.8 持續熟練分支「血盾」：吸血溢出轉為臨時護盾，上限 20% 生命。
	Float overflow = afAmount - heal
	If overflow > 0.0 && ESSBNodes.Br(Self, 5, 0, 1, 1)
		Float cap = player.GetActorValueMax("Health") * 0.2
		If overflow > cap
			overflow = cap
		EndIf
		ApplyUtil(19, overflow, 20, player, True)
		ApplyUtil(4, overflow, 0, player, True)
	EndIf
EndFunction

; ---------------------------------------------------------------- 同調

Function AddSync(Int aiAmount)
	Int before = CachedSync
	If !RuntimeCacheReady
		before = Sync.GetValueInt()
	EndIf
	Int after = before + aiAmount
	CachedSync = after
	Sync.SetValueInt(after)
	RefreshSyncStage()
	Int stage = SyncStage()
	If stage > SyncStageShown
		SyncStageShown = stage
		OnSyncStage(stage)
	EndIf

EndFunction

Int Function ComputeSyncStage()
	Int value = CachedSync
	If !RuntimeCacheReady
		value = Sync.GetValueInt()
	EndIf
	Int t1 = 5
	Int t2 = 15
	Int t3 = 30
	If SyncT1
		t1 = CachedT1
		If !RuntimeCacheReady
			t1 = SyncT1.GetValueInt()
		EndIf
	EndIf
	If SyncT2
		t2 = CachedT2
		If !RuntimeCacheReady
			t2 = SyncT2.GetValueInt()
		EndIf
	EndIf
	If SyncT3
		t3 = CachedT3
		If !RuntimeCacheReady
			t3 = SyncT3.GetValueInt()
		EndIf
	EndIf
	; 5.2 持續新手主線「同調門檻 -2%／點」與熟練分支「專一」。
	Float scale = ESSBNodes.SyncThresholdScale(Self)
	If scale < 1.0
		t1 = (t1 * scale) as Int
		t2 = (t2 * scale) as Int
		t3 = (t3 * scale) as Int
		If t1 < 1
			t1 = 1
		EndIf
		If t2 <= t1
			t2 = t1 + 1
		EndIf
		If t3 <= t2
			t3 = t2 + 1
		EndIf
	EndIf
	If value >= t3
		Return 3
	ElseIf value >= t2
		Return 2
	ElseIf value >= t1
		Return 1
	EndIf
	Return 0
EndFunction

Float Function SyncMult()
	Int stage = SyncStage()
	If stage == 3
		Return 3.0
	ElseIf stage == 2
		Return 2.0
	ElseIf stage == 1
		Return 1.5
	EndIf
	Return 1.0
EndFunction

; 同調升段：光暈與武器發光屬特效前線，這裡先送模組事件與紀錄。
Function OnSyncStage(Int aiStage)
	PushSyncStage()
	; 規劃 2.12「同調升段：Charge_X」。光暈與三段武器發光是引擎側的：三個
	; ESSB_SyncGlowEffect_n 與 ESSB_SyncWeaponEffect_<X> 掛在形態能力的效果層上，
	; 條件是 CTDA GetGlobalValue(ESSB_SyncStage) >= n，PushSyncStage 寫完就生效。
	PlayFormSound(FxSoundCharge, CurrentElement.GetValueInt())
	SendModEvent("ESSB_SyncStage", "stage", aiStage as Float)
	; 5.2 持續大師分支「回饋」：同調升段時回復生命與魔力各 B_max ×2。
	ESSBNodes.OnSyncStage(Self, aiStage)
	If CachedDebugLevel >= 1
		LogEvent(1, "sync", "stage=" + aiStage + " value=" + Sync.GetValueInt() \
			+ " element=" + CurrentElement.GetValueInt())
	EndIf
	RefreshSyncStage()
	RefreshProcMagnitudes()
	RefreshDivineProtection()
EndFunction

; 樣式 C 的鏡射：同調段數寫進全域變數，PERK 進入點的 CTDA 才讀得到。
Function PushSyncStage()
	RefreshSyncStage()
	If GSyncStage
		Int stage = SyncStage()
		If GSyncStage.GetValueInt() != stage
			GSyncStage.SetValueInt(stage)
		EndIf
	EndIf
EndFunction

; ---------------------------------------------------------------- 自身資源

Function AddSelf(Int aiKind, Int aiAmount)
	Int before = GetSelf(aiKind)
	If aiKind == 1
		SelfCharge += aiAmount
		Int chargeCap = ESSBElem.ChargeCap(Self)
		If SelfCharge > chargeCap
			SelfCharge = chargeCap
		EndIf
		If before != SelfCharge
			GCharge.SetValueInt(SelfCharge)
		EndIf
	ElseIf aiKind == 2
		SelfRockArmor += aiAmount
		Int rockCap = ESSBElem2.RockCap(Self)
		If SelfRockArmor > rockCap
			SelfRockArmor = rockCap
		EndIf
		If SelfRockArmor < 0
			SelfRockArmor = 0
		EndIf
		SyncRockArmor()
	ElseIf aiKind == 3
		SelfWind += aiAmount
		; 風勢是量表，封頂在門檻（亂舞分支 3）；到門檻的風刃在 ESSBElem2.CheckWindGauge。
		Int windCap = ESSBElem2.WindThreshold(Self)
		If SelfWind > windCap
			SelfWind = windCap
		EndIf
		If SelfWind < 0
			SelfWind = 0
		EndIf
		If before != SelfWind
			GWind.SetValueInt(SelfWind)
		EndIf
	ElseIf aiKind == 4
		SelfOverheat += aiAmount
		If SelfOverheat >= ESSBElem.OverheatCap(Self)
			If ESSBElem.HasMoltenBody(Self)
				; 5.3 持續專精分支「熔身」：不再對自己爆，改為進入 10 秒熔身。
				SetMolten(10)
				SelfOverheat = 0
				If CachedDebugLevel >= 1
					LogEvent(1, "overheat", "moltenbody")
				EndIf
			Else
				; 規劃 1.1：過熱滿對自己爆一次最大生命 10% 的火傷並歸零。
				Actor player = ThePlayer()
				If player
					ApplyDamageRaw(1, player.GetActorValueMax("Health") * 0.1, player)
				EndIf
				SelfOverheat = 0
				If CachedDebugLevel >= 1
					LogEvent(1, "overheat", "vent")
				EndIf
			EndIf
		EndIf
		If before != SelfOverheat
			GOverheat.SetValueInt(SelfOverheat)
		EndIf
	EndIf
	If aiKind == 4 && before != SelfOverheat
		RefreshProcMagnitudes()
	EndIf
EndFunction

; 樣式 C 的鏡射：電荷、過熱、冰盾、戰意寫進全域變數給 PERK 進入點。
Function PushSelf()
	If GCharge && GCharge.GetValueInt() != SelfCharge
		GCharge.SetValueInt(SelfCharge)
	EndIf
	If GOverheat && GOverheat.GetValueInt() != SelfOverheat
		GOverheat.SetValueInt(SelfOverheat)
	EndIf
	If GIceShield && GIceShield.GetValueInt() != IceShield
		GIceShield.SetValueInt(IceShield)
	EndIf
	If GResolve && GResolve.GetValueInt() != Resolve
		GResolve.SetValueInt(Resolve)
	EndIf
	SetGlobal(GRockArmor, SelfRockArmor)
	SetGlobal(GWind, SelfWind)
	SetGlobal(GHolyShield, HolyShield)
EndFunction

Int Function GetSelf(Int aiKind)
	If aiKind == 1
		Return SelfCharge
	ElseIf aiKind == 2
		Return SelfRockArmor
	ElseIf aiKind == 3
		Return SelfWind
	ElseIf aiKind == 4
		Return SelfOverheat
	EndIf
	Return 0
EndFunction

Function ClearSelf(Int aiKind)
	Int before = GetSelf(aiKind)
	If aiKind == 1
		SelfCharge = 0
		If before != 0
			GCharge.SetValueInt(0)
		EndIf
	ElseIf aiKind == 2
		SelfRockArmor = 0
		SyncRockArmor()
		If before != 0
			GRockArmor.SetValueInt(0)
		EndIf
	ElseIf aiKind == 3
		SelfWind = 0
		If before != 0
			GWind.SetValueInt(0)
		EndIf
	ElseIf aiKind == 4
		SelfOverheat = 0
		If before != 0
			GOverheat.SetValueInt(0)
		EndIf
	EndIf
	If aiKind == 4 && before != SelfOverheat
		RefreshProcMagnitudes()
	EndIf
EndFunction

Function ClearSelfAll()
	SelfCharge = 0
	SelfRockArmor = 0
	SelfWind = 0
	SelfOverheat = 0
	StormCharge = 0
	IceShield = 0
	HolyShield = 0
	; round 3：水鏡層與追擊的命中計數也是「疊在你身上」的資源，離開形態清空（規劃 2.3）。
	WaterMirror = 0
	AstralHits = 0
	SetGlobal(GWaterMirror, 0)
	PushSelf()
	SyncRockArmor()
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

; 岩甲是層數管理的持續能力；只在數值變化或能力遺失時重掛。
Function SyncRockArmor()
	SetGlobal(GRockArmor, SelfRockArmor)
	Actor player = ThePlayer()
	If !player || !UtilSpells
		Return
	EndIf
	Spell armorSpell = UtilSpells[18]
	If !armorSpell
		Return
	EndIf
	Float wanted = RecoveryAmount(SelfRockArmor * ESSBElem2.RockArmorPerLayer(Self))
	If wanted == RockArmorShown && wanted > 0.0 && player.HasSpell(armorSpell) && player.HasMagicEffect(armorSpell.GetNthEffectMagicEffect(0))
		Return
	EndIf
	RockArmorShown = wanted
	player.RemoveSpell(armorSpell)
	; Also remove an old timed cast when upgrading an existing schema-4 save.
	player.DispelSpell(armorSpell)
	If wanted > 0.0
		armorSpell.SetNthEffectMagnitude(0, wanted)
		player.AddSpell(armorSpell, False)
	EndIf
EndFunction

; ---- 岩甲被打 -1（規劃 2.3，ESSBGuard 呼叫）
Function ConsumeRockArmor()
	AddSelf(2, -1)
EndFunction

; ---- 冰盾逐層消耗（5.4 持續大師分支，round 2 補上受擊事件後才成立）
Function ConsumeIceShield()
	If IceShield > 0
		IceShield -= 1
		GIceShield.SetValueInt(IceShield)
	EndIf
EndFunction

; 直接設定自身資源的絕對層數（地臨強化、固土、疾風痕用）。
Function SetSelf(Int aiKind, Int aiValue)
	Int before = GetSelf(aiKind)
	If aiKind == 1
		SelfCharge = aiValue
		If before != SelfCharge
			GCharge.SetValueInt(SelfCharge)
		EndIf
	ElseIf aiKind == 2
		SelfRockArmor = aiValue
		SyncRockArmor()
		If before != SelfRockArmor
			GRockArmor.SetValueInt(SelfRockArmor)
		EndIf
	ElseIf aiKind == 3
		SelfWind = aiValue
		If before != SelfWind
			GWind.SetValueInt(SelfWind)
		EndIf
	ElseIf aiKind == 4
		SelfOverheat = aiValue
		If before != SelfOverheat
			GOverheat.SetValueInt(SelfOverheat)
		EndIf
	EndIf
EndFunction

; ---------------------------------------------------------------- 目標資格與範圍（規劃 2.9）

Function MarkEngaged(Actor akTarget)
	If !akTarget || !EngagedSpell
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	; 30 秒「已交戰」自有標記；重複套用只是刷新時間。
	player.DoCombatSpellApply(EngagedSpell, akTarget)
EndFunction

Bool Function IsValidTarget(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	Actor player = ThePlayer()
	If !player || akTarget == player
		Return False
	EndIf
	If akTarget.IsDead() || akTarget.IsPlayerTeammate() || akTarget.IsCommandedActor()
		Return False
	EndIf
	If akTarget.IsHostileToActor(player)
		Return True
	EndIf
	If akTarget.IsInCombat() && akTarget.GetCombatTarget() == player
		Return True
	EndIf
	If EngagedKeyword && akTarget.HasMagicEffectWithKeyword(EngagedKeyword)
		Return True
	EndIf
	Return False
EndFunction

Bool Function IsVIPTarget(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	If akTarget.IsEssential()
		Return True
	EndIf
	ActorBase base = akTarget.GetActorBase()
	If base && (base.IsEssential() || base.IsProtected() || base.IsUnique())
		Return True
	EndIf
	Return False
EndFunction

Bool Function IsUndeadOrDaedra(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	If UndeadKeyword && akTarget.HasKeyword(UndeadKeyword)
		Return True
	EndIf
	If DaedraKeyword && akTarget.HasKeyword(DaedraKeyword)
		Return True
	EndIf
	Return False
EndFunction

; 「附近」的基礎定義（2.9）：中心為被命中的目標，半徑 15 公尺＝1050 單位，
; 人數上限 5，距離近的優先，不要求視線。回傳固定 5 格陣列，未用到的格是 None。
Actor[] Function ScanTargets(ObjectReference akCenter, Float afRadius, Int aiMax, Actor akExclude)
	Actor[] result = new Actor[5]
	Float[] distance = new Float[5]
	Int limit = aiMax
	If limit > 5
		limit = 5
	EndIf
	If limit < 1 || !akCenter
		Return result
	EndIf
	Actor[] pool = PO3_SKSEFunctions.GetActorsByProcessingLevel(0)
	If !pool
		Return result
	EndIf
	Int found = 0
	Int index = 0
	While index < pool.Length
		Actor candidate = pool[index]
		If candidate && candidate != akExclude && IsValidTarget(candidate)
			Float d = akCenter.GetDistance(candidate)
			If d <= afRadius
				Int slot = 0
				Bool placed = False
				While slot < limit && !placed
					If !result[slot]
						result[slot] = candidate
						distance[slot] = d
						placed = True
						found += 1
					ElseIf d < distance[slot]
						Int shift = limit - 1
						While shift > slot
							result[shift] = result[shift - 1]
							distance[shift] = distance[shift - 1]
							shift -= 1
						EndWhile
						result[slot] = candidate
						distance[slot] = d
						placed = True
						If found < limit
							found += 1
						EndIf
					EndIf
					slot += 1
				EndWhile
			EndIf
		EndIf
		index += 1
	EndWhile
	If CachedDebugLevel >= 3
		LogThrottled(3, "scan", "radius=" + afRadius + " max=" + limit + " pool=" + pool.Length + " found=" + found)
	EndIf
	Return result
EndFunction

; 毒的擴散：每個帶毒目標每次只找一個對象，不做全場掃描（規劃 2.7）。
Function SpreadPoison(Actor akFrom, Int aiAmount, Int aiTargets = 1)
	If !akFrom
		Return
	EndIf
	Actor[] nearby = ScanTargets(akFrom, 210.0, aiTargets, akFrom)
	Int index = 0
	While index < nearby.Length
		If nearby[index]
			AddStackTo(nearby[index], 7, aiAmount)
		EndIf
		index += 1
	EndWhile
EndFunction

; ---------------------------------------------------------------- 每秒 tick 與環境

Function Tick()
	If !IsOperational()
		Return
	EndIf
	; 主控台 `set ESSB_DebugLevel to N` 不會觸發任何事件，快取只在載入／換形態／關 MCM 時刷新，
	; 玩家在遊戲中途開除錯會一直看不到紀錄。每個 tick 讀一次（不是每刀），成本可忽略。
	CachedDebugLevel = DebugLevel.GetValueInt()
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If NodeScale && Trees && LastNodeScale != NodeScale.GetValue()
		ESSBNodes.RefreshWeaponPercent(Self)
		LastNodeScale = NodeScale.GetValue()
	EndIf
	If MultRecovery && LastRecoveryScale != MultRecovery.GetValue()
		RefreshRecovery()
	EndIf
	Float now = Utility.GetCurrentRealTime()

	; 自身資源衰減（規劃 2.3）：風勢 5 秒未命中歸零；電荷 10 秒未命中後每秒 -1；
	; 岩甲與過熱不衰減。
	If SelfWind > 0 && now - SelfLastHit >= 5.0
		SelfWind = 0
		GWind.SetValueInt(SelfWind)
	EndIf
	If SelfCharge > 0 && now - SelfLastHit >= 10.0
		Float decayStart = SelfLastHit + 9.0
		If ChargeDecayAt > decayStart
			decayStart = ChargeDecayAt
		EndIf
		Int decay = (now - decayStart) as Int
		SelfCharge -= decay
		ChargeDecayAt = decayStart + decay
		If SelfCharge < 0
			SelfCharge = 0
		EndIf
		GCharge.SetValueInt(SelfCharge)
	EndIf

	; 雷雨天氣：雷形態每 3 秒自動 +1 電荷（規劃 2.10）。
	If FormActive.GetValueInt() == 1 && CurrentElement.GetValueInt() == 3 && EnvStormy.GetValueInt() == 1
		If StormCharge <= 0
			StormCharge = now + CooldownSeconds(3.0)
		EndIf
		If now >= StormCharge
			StormCharge = now + CooldownSeconds(3.0)
			AddSelf(1, 1)
		EndIf
	Else
		StormCharge = 0
	EndIf

	; 戰意 5 秒未命中歸零（規劃 2.3）。
	If Resolve > 0 && now - ResolveTime >= 5.0
		Resolve = 0
		GResolve.SetValueInt(Resolve)
	EndIf
	; 「節奏」「疾攻」的連段：4 秒沒有新命中就斷。
	If ComboHits > 0 && now - ComboTime >= 4.0
		ComboHits = 0
		SetGlobal(GCombo, 0)
	EndIf

	RefreshDivineProtection()
	TickTimers()

	; 清掉死亡或離線的登記格；死亡的目標先跑擊殺掛勾（連鎖冰封、無魔）。
	Int index = 0
	While index < 8
		Actor target = RegActor[index]
		Int generation = RegGeneration[index]
		If target && (target.IsDead() || target.IsDisabled())
			If target.IsDead()
				CaptureDeath(index)
			EndIf
			If RegActor[index] == target && RegGeneration[index] == generation
				ClearSlot(index)
			EndIf
		ElseIf target && RegElem[index] >= 1 && RegUntil[index] > 0.0 && now >= RegUntil[index]
			EndMark(index, 2, 1.0)
		ElseIf target && RegElem2[index] >= 1 && RegSecondUntil[index] > 0.0 && now >= RegSecondUntil[index]
			; 疊印的副印記過期：過期終焉，倍率 ×1（規劃 2.6）。
			EndSecondMark(index, 2, 1.0)
		EndIf
		index += 1
	EndWhile

	; 5.2 持續傳奇主線「化身」：同調三段時每 N 秒自動觸發當前元素的持續傳奇效果。
	Int avatarCd = (CooldownSeconds(ESSBNodes.AvatarCooldown(Self)) + 0.5) as Int
	If avatarCd > 0 && FormActive.GetValueInt() == 1 && SyncStage() >= 3
		If now >= AvatarLeft
			AvatarLeft = 0.0
		EndIf
		If AvatarLeft <= 0
			AvatarLeft = Utility.GetCurrentRealTime() + avatarCd
			ESSBElem.OnAvatar(Self, CurrentElement.GetValueInt())
		EndIf
	Else
		AvatarLeft = Utility.GetCurrentRealTime() + avatarCd
	EndIf

	; 各元素樹的每秒掛勾（冰心、雷神、庇護）。
	If FormActive.GetValueInt() == 1
		Int tickElement = CurrentElement.GetValueInt()
		ESSBElem.OnTick(Self, tickElement)
		ESSBElem2.OnTick(Self, tickElement)
		ESSBElem3.OnTick(Self, tickElement)
		; 風形態：每秒讀一次潛行狀態（不是每幀），變了才動能力。
		If tickElement == 5
			Actor player = ThePlayer()
			If player
				Bool sneaking = player.IsSneaking()
				If sneaking != SneakingNow
					SneakingNow = sneaking
					RefreshWindStealth(True)
				EndIf
			EndIf
		EndIf
	EndIf
	; 5.9 傳奇分支「神佑」：每場戰鬥一次，脫戰即重置。
	If DivineSaveUsed
		Actor guardPlayer = ThePlayer()
		If guardPlayer && !guardPlayer.IsInCombat()
			DivineSaveUsed = False
		EndIf
	EndIf

	SwapHosts()

	If now - LastEnvCheck >= 5.0
		LastEnvCheck = now
		EnvCheck()
	EndIf

	Float delay = 5.0
	If FormActive.GetValueInt() == 1 || RegistryCount() > 0 || TimersActive()
		delay = 1.0
	EndIf
	NextTickAt = 0.0
	ScheduleTick(delay)
EndFunction

; 每秒把所有「剩餘秒數」計時器減一，歸零時同步把鏡射的全域變數寫回 0。
Function TickTimers()
	If !IsOperational()
		Return
	EndIf
	Bool procDirty = False
	Int oldStage = CachedSyncStage
	Float now = Utility.GetCurrentRealTime()
	If MoltenLeft > 0
		Float stop = now
		If stop > MoltenLeft
			stop = MoltenLeft
		EndIf
		Int ticks = (stop - MoltenTickAt) as Int
		MoltenTickAt += ticks
		If now >= MoltenLeft
			MoltenLeft = 0.0
			procDirty = True
		EndIf
		Actor player = ThePlayer()
		If player && ticks > 0
			; 熔身：每秒回耐力 5（5.3 持續專精分支）。
			ApplyUtil(6, 20.0 * GLevel(0) * ticks, 0, player)
		EndIf
		If MoltenLeft <= 0
			; 結束後過熱歸零。
			SelfOverheat = 0
			GOverheat.SetValueInt(SelfOverheat)
		EndIf
		SetGlobal(GMolten, SecondsLeft(MoltenLeft))
	EndIf
	If EmberLeft > 0
		If now >= EmberLeft
			EmberLeft = 0.0
		EndIf
		SetGlobal(GEmber, SecondsLeft(EmberLeft))
		If EmberLeft <= 0
			EmberElem = 0
		EndIf
	EndIf
	If QuenchLeft > 0
		If now >= QuenchLeft
			QuenchLeft = 0.0
		EndIf
		SetGlobal(GQuench, SecondsLeft(QuenchLeft))
	EndIf
	If ShockLeft > 0
		If now >= ShockLeft
			ShockLeft = 0.0
		EndIf
		SetGlobal(GShockRecent, SecondsLeft(ShockLeft))
	EndIf
	If GuardSwitchLeft > 0
		If now >= GuardSwitchLeft
			GuardSwitchLeft = 0.0
		EndIf
		SetGlobal(GGuardSwitch, SecondsLeft(GuardSwitchLeft))
	EndIf
	If GuardBurstLeft > 0
		If now >= GuardBurstLeft
			GuardBurstLeft = 0.0
		EndIf
		SetGlobal(GGuardBurst, SecondsLeft(GuardBurstLeft))
	EndIf
	If GuardIceLeft > 0
		If now >= GuardIceLeft
			GuardIceLeft = 0.0
		EndIf
		SetGlobal(GGuardIce, SecondsLeft(GuardIceLeft))
	EndIf
	If ThunderLeft > 0
		If now >= ThunderLeft
			ThunderLeft = 0.0
		EndIf
	EndIf
	; ---- round 2 的秒計時器
	If BloodthirstLeft > 0
		If now >= BloodthirstLeft
			BloodthirstLeft = 0.0
			procDirty = True
		EndIf
		SetGlobal(GBloodthirst, SecondsLeft(BloodthirstLeft))
	EndIf
	If GuardWindLeft > 0
		If now >= GuardWindLeft
			GuardWindLeft = 0.0
		EndIf
		SetGlobal(GGuardWind, SecondsLeft(GuardWindLeft))
	EndIf
	If GuardDivineLeft > 0
		If now >= GuardDivineLeft
			GuardDivineLeft = 0.0
		EndIf
		SetGlobal(GGuardDivine, SecondsLeft(GuardDivineLeft))
	EndIf
	If CloakGuardLeft > 0
		If now >= CloakGuardLeft
			CloakGuardLeft = 0.0
		EndIf
		SetGlobal(GCloakGuard, SecondsLeft(CloakGuardLeft))
	EndIf
	If NoBloodCostLeft > 0
		If now >= NoBloodCostLeft
			NoBloodCostLeft = 0.0
		EndIf
		SetGlobal(GNoBloodCost, SecondsLeft(NoBloodCostLeft))
	EndIf
	If WindFollowLeft > 0
		If now >= WindFollowLeft
			WindFollowLeft = 0.0
		EndIf
	EndIf
	If RiposteLeft > 0
		If now >= RiposteLeft
			RiposteLeft = 0.0
		EndIf
	EndIf
	If EndBoostLeft > 0
		If now >= EndBoostLeft
			EndBoostLeft = 0.0
			procDirty = True
		EndIf
		If EndBoostLeft <= 0
			EndBoostAmount = 0.0
		EndIf
	EndIf
	If KeepSneakLeft > 0
		If now >= KeepSneakLeft
			KeepSneakLeft = 0.0
		EndIf
		If KeepSneakLeft <= 0
			Actor sneaker = ThePlayer()
			If sneaker
				PO3_SKSEFunctions.ResetActorDetection(sneaker)
			EndIf
			KillStreakReady = False
		EndIf
	EndIf
	If DoubleBurstLeft > 0
		If now >= DoubleBurstLeft
			DoubleBurstLeft = 0.0
		EndIf
	EndIf
	; ---- round 3 的秒計時器
	If GuardDarkLeft > 0
		If now >= GuardDarkLeft
			GuardDarkLeft = 0.0
		EndIf
		SetGlobal(GGuardDark, SecondsLeft(GuardDarkLeft))
	EndIf
	If GuardAstralLeft > 0
		If now >= GuardAstralLeft
			GuardAstralLeft = 0.0
		EndIf
		SetGlobal(GGuardAstral, SecondsLeft(GuardAstralLeft))
	EndIf
	If GuardStarLeft > 0
		If now >= GuardStarLeft
			GuardStarLeft = 0.0
		EndIf
		SetGlobal(GGuardStar, SecondsLeft(GuardStarLeft))
	EndIf
	If SyncKeepLeft > 0
		If now >= SyncKeepLeft
			SyncKeepLeft = 0.0
		EndIf
		If SyncKeepLeft <= 0
			SyncKeep = 0
		EndIf
	EndIf
	Int slot = 1
	While slot <= 11
		If OpenBoost[slot] > 0
			If Utility.GetCurrentRealTime() >= OpenBoost[slot]
				OpenBoost[slot] = 0.0
			procDirty = True
			EndIf
		EndIf
		If EndBoost[slot] > 0
			If Utility.GetCurrentRealTime() >= EndBoost[slot]
				EndBoost[slot] = 0.0
			EndIf
		EndIf
		slot += 1
	EndWhile
	TickDomain()
	RefreshSyncStage()
	If oldStage != CachedSyncStage
		PushSyncStage()
		RefreshDivineProtection()
	EndIf
	If procDirty || oldStage != CachedSyncStage
		RefreshProcMagnitudes()
	EndIf
EndFunction

Bool Function TimersActive()
	If (MoltenLeft > 0 && MoltenLeft > Utility.GetCurrentRealTime()) || (EmberLeft > 0 && EmberLeft > Utility.GetCurrentRealTime()) || (QuenchLeft > 0 && QuenchLeft > Utility.GetCurrentRealTime()) || (ShockLeft > 0 && ShockLeft > Utility.GetCurrentRealTime()) || DomainActive()
		Return True
	EndIf
	If (GuardDarkLeft > 0 && GuardDarkLeft > Utility.GetCurrentRealTime()) || (GuardAstralLeft > 0 && GuardAstralLeft > Utility.GetCurrentRealTime()) || (GuardStarLeft > 0 && GuardStarLeft > Utility.GetCurrentRealTime()) || WaterMirror > 0
		Return True
	EndIf
	If (GuardSwitchLeft > 0 && GuardSwitchLeft > Utility.GetCurrentRealTime()) || (GuardBurstLeft > 0 && GuardBurstLeft > Utility.GetCurrentRealTime()) || (GuardIceLeft > 0 && GuardIceLeft > Utility.GetCurrentRealTime()) || (SyncKeepLeft > 0 && SyncKeepLeft > Utility.GetCurrentRealTime()) 		|| Resolve > 0 || ComboHits > 0
		Return True
	EndIf
	If (BloodthirstLeft > 0 && BloodthirstLeft > Utility.GetCurrentRealTime()) || (GuardWindLeft > 0 && GuardWindLeft > Utility.GetCurrentRealTime()) || (GuardDivineLeft > 0 && GuardDivineLeft > Utility.GetCurrentRealTime()) || (CloakGuardLeft > 0 && CloakGuardLeft > Utility.GetCurrentRealTime())
		Return True
	EndIf
	Return (NoBloodCostLeft > 0 && NoBloodCostLeft > Utility.GetCurrentRealTime()) || (WindFollowLeft > 0 && WindFollowLeft > Utility.GetCurrentRealTime()) || (RiposteLeft > 0 && RiposteLeft > Utility.GetCurrentRealTime()) || (KeepSneakLeft > 0 && KeepSneakLeft > Utility.GetCurrentRealTime()) 		|| (EndBoostLeft > 0 && EndBoostLeft > Utility.GetCurrentRealTime()) || DivineSaveUsed
EndFunction

Function SetGlobal(GlobalVariable akGlobal, Int aiValue)
	If akGlobal && akGlobal.GetValueInt() != aiValue
		akGlobal.SetValueInt(aiValue)
	EndIf
EndFunction

; 規劃 2.10：只讀天氣分類、時間與是否在水中，成本極低。
Function EnvCheck()
	Int wet = 0
	Int stormy = 0
	Int night = 0
	Weather current = Weather.GetCurrentWeather()
	Int classification = -1
	If current
		classification = current.GetClassification()
	EndIf
	; 分類 2 = 雨、3 = 雪。雷雨與暴風雪都落在這兩類。
	If classification == 2 || classification == 3
		wet = 1
		stormy = 1
	EndIf
	Actor player = ThePlayer()
	If player
		; 規劃 2.10：室內、地城沒有環境加成。
		Cell here = player.GetParentCell()
		If here && here.IsInterior()
			wet = 0
			stormy = 0
		EndIf
		If player.IsSwimming() || PO3_SKSEFunctions.IsRefUnderwater(player)
			wet = 1
		EndIf
	EndIf
	Float hour = 12.0
	If GameHour
		hour = GameHour.GetValue()
	EndIf
	If hour >= 20.0 || hour < 6.0
		night = 1
	EndIf
	Bool changed = False
	If EnvWet && EnvWet.GetValueInt() != wet
		EnvWet.SetValueInt(wet)
		changed = True
	EndIf
	If EnvStormy && EnvStormy.GetValueInt() != stormy
		EnvStormy.SetValueInt(stormy)
		changed = True
	EndIf
	If EnvNight && EnvNight.GetValueInt() != night
		EnvNight.SetValueInt(night)
		changed = True
	EndIf
	If changed
		If CachedDebugLevel >= 1
			LogEvent(1, "env", "wet=" + wet + " stormy=" + stormy + " night=" + night \
				+ " classification=" + classification + " hour=" + hour)
		EndIf
	EndIf
	If CachedDebugLevel >= 3
		; PO3 GetWeatherType 的回傳值只在等級 3 紀錄，供進遊戲校準雷雨與暴風雪的細分。
		If CachedDebugLevel >= 3
			LogThrottled(3, "env", "po3WeatherType=" + PO3_SKSEFunctions.GetWeatherType() \
				+ " classification=" + classification)
		EndIf
	EndIf
	If changed
		RefreshProcMagnitudes()
	EndIf
EndFunction

Bool Function IsEnvWet()
	If !EnvWet
		Return False
	EndIf
	Return EnvWet.GetValueInt() == 1
EndFunction

Bool Function IsEnvStormy()
	If !EnvStormy
		Return False
	EndIf
	Return EnvStormy.GetValueInt() == 1
EndFunction

Bool Function IsEnvNight()
	If !EnvNight
		Return False
	EndIf
	Return EnvNight.GetValueInt() == 1
EndFunction

; ---------------------------------------------------------------- 節點狀態的對外入口
; 全部是給 ESSBNodes／ESSBNoForm／ESSBElem 呼叫的小存取器。狀態留在控制器，
; 節點腳本是無狀態的全域函式，這樣加新元素只要加函式，不必再動登記表。

; ---- 戰意（無元素樹「節奏」給、「處決」消耗；5 秒未命中歸零）
Int Function GetResolve()
	Return Resolve
EndFunction

Function AddResolve(Int aiAmount)
	Resolve += aiAmount
	If Resolve > 5
		Resolve = 5
	EndIf
	ResolveTime = Utility.GetCurrentRealTime()
	GResolve.SetValueInt(Resolve)
EndFunction

Function ClearResolve()
	Resolve = 0
	GResolve.SetValueInt(Resolve)
EndFunction

; ---- 冰盾（5.4 持續大師分支）
Int Function GetIceShield()
	Return IceShield
EndFunction

Function AddIceShield(Int aiAmount)
	IceShield += aiAmount
	If IceShield > 5
		IceShield = 5
	EndIf
	GIceShield.SetValueInt(IceShield)
EndFunction

; ---- 秒計時器
Function SetMolten(Int aiSeconds)
	MoltenTickAt = Utility.GetCurrentRealTime()
	aiSeconds = DurationInt(aiSeconds)
	MoltenLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GMolten, SecondsLeft(MoltenLeft))
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Int Function GetMoltenLeft()
	Return SecondsLeft(MoltenLeft)
EndFunction

Function SetEmber(Int aiSeconds, Int aiElement)
	aiSeconds = DurationInt(aiSeconds)
	EmberLeft = Utility.GetCurrentRealTime() + aiSeconds
	EmberElem = aiElement
	SetGlobal(GEmber, SecondsLeft(EmberLeft))
EndFunction

Int Function GetEmberLeft()
	Return SecondsLeft(EmberLeft)
EndFunction

Function SetQuench(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	QuenchLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GQuench, SecondsLeft(QuenchLeft))
EndFunction

Function SetShockRecent(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	ShockLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GShockRecent, SecondsLeft(ShockLeft))
EndFunction

Function SetGuardSwitch(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardSwitchLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardSwitch, SecondsLeft(GuardSwitchLeft))
	ApplyGuardWindow(0, GuardSwitchLeft)
EndFunction

Function SetGuardBurst(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardBurstLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardBurst, SecondsLeft(GuardBurstLeft))
	ApplyGuardWindow(1, GuardBurstLeft)
EndFunction

Function SetGuardIce(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardIceLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardIce, SecondsLeft(GuardIceLeft))
	ApplyGuardWindow(2, GuardIceLeft)
EndFunction

Function SetThunder(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	ThunderLeft = Utility.GetCurrentRealTime() + aiSeconds
EndFunction

Function SetDoubleBurst(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	DoubleBurstLeft = Utility.GetCurrentRealTime() + aiSeconds
EndFunction

Function SetFreeOpen(Int aiValue)
	SetGlobal(GFreeOpen, aiValue)
EndFunction

Int Function GetFreeOpen()
	If !GFreeOpen
		Return 0
	EndIf
	Return GFreeOpen.GetValueInt()
EndFunction

Function SetPendingDischarge(Int aiValue)
	PendingDischarge = aiValue
EndFunction

Function SetNextMarkBonus(Int aiSeconds)
	NextMarkBonus = aiSeconds
EndFunction

; ---- 同調保留（承接／連斷／永續／三重奏）
Function SetSyncKeep(Int aiValue, Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If aiValue > SyncKeep
		SyncKeep = aiValue
	EndIf
	SyncKeepLeft = Utility.GetCurrentRealTime() + aiSeconds
EndFunction

Function SetSyncKeepAll()
	SetSyncKeep(Sync.GetValueInt(), 60)
EndFunction

; ---- 開印後／終焉後的 5 秒視窗
Function SetOpenBoost(Int aiElement, Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If aiElement >= 1 && aiElement <= 11
		OpenBoost[aiElement] = Utility.GetCurrentRealTime() + aiSeconds
	EndIf
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Int Function GetOpenBoost(Int aiElement)
	If aiElement < 1 || aiElement > 11
		Return 0
	EndIf
	If OpenBoost[aiElement] <= 0.0
		Return 0
	EndIf
	Return SecondsLeft(OpenBoost[aiElement])
EndFunction

Function SetEndBoost(Int aiElement, Int aiSeconds, Float afBonus = 0.0)
	aiSeconds = DurationInt(aiSeconds)
	If aiElement >= 1 && aiElement <= 11
		EndBoost[aiElement] = Utility.GetCurrentRealTime() + aiSeconds
	EndIf
	; 接管元素吃的是「剛結束的那個元素的階數」算出來的加成，所以把值也存起來。
	If afBonus > 0.0
		EndBoostLeft = Utility.GetCurrentRealTime() + aiSeconds
		EndBoostAmount = afBonus
	EndIf
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Int Function GetEndBoost(Int aiElement)
	If aiElement < 1 || aiElement > 11
		Return 0
	EndIf
	If EndBoost[aiElement] <= 0.0
		Return 0
	EndIf
	Return SecondsLeft(EndBoost[aiElement])
EndFunction

; ---- 一次性旗標
Bool Function TakeSwitchEnd()
	If !SwitchEndPending
		Return False
	EndIf
	SwitchEndPending = False
	Return True
EndFunction

Bool Function TakeGrandConcert()
	; 大協奏與協奏共用「切換後首次終焉」這個旗標；協奏先取走時大協奏就不再觸發。
	Return TakeSwitchEnd()
EndFunction

; 三重奏：10 秒內不同元素的終焉次數。回傳目前累積的種類數。
Int Function PushTrio(Int aiElement)
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return 0
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If aiElement < 1 || aiElement > 11
		Return 0
	EndIf
	TrioTimes[aiElement] = now
	Int count = 0
	Int index = 1
	While index <= 11
		If TrioTimes[index] > 0.0 && now - TrioTimes[index] <= 10.0
			count += 1
		Else
			TrioTimes[index] = 0.0
		EndIf
		index += 1
	EndWhile
	If count >= 3
		index = 1
		While index <= 11
			TrioTimes[index] = 0.0
			index += 1
		EndWhile
	EndIf
	Return count
EndFunction

; 斷咒的 5 秒冷卻。
Bool Function TakeInterrupt()
	Float now = Utility.GetCurrentRealTime()
	If now - InterruptTime < CooldownSeconds(5.0)
		Return False
	EndIf
	InterruptTime = now
	Return True
EndFunction

; 冰心的 30 秒冷卻。
Bool Function TakeIceHeart()
	Float now = Utility.GetCurrentRealTime()
	If now - IceHeartTime < CooldownSeconds(30.0)
		Return False
	EndIf
	IceHeartTime = now
	Return True
EndFunction

; ---- 狀態容器的寫入補充（節點要設定絕對層數時用）
Function SetStack(Actor akTarget, Int aiKind, Int aiValue)
	Int slot = FindSlot(akTarget)
	If slot < 0 || aiKind < 1 || aiKind > 11
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetStack(aiKind, aiValue)
	ElseIf aiKind == 11
		PendingAstral[slot] = aiValue
		PendingAstralWeight[slot] = aiValue as Float
		EnsureStatus(slot, akTarget)
	Else
		Int pos = slot * 12 + aiKind
		PendingSet[pos] = True
		PendingStacks[pos] = aiValue
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

; 對還沒登記的目標疊層（寒潮、連鎖冰封這類範圍效果）。
Function AddStackTo(Actor akTarget, Int aiKind, Int aiAmount)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !akTarget
		Return
	EndIf
	Int slot = AcquireSlot(akTarget)
	If slot < 0
		Return
	EndIf
	EnsureStatus(slot, akTarget)
	AddStack(akTarget, aiKind, aiAmount)
EndFunction

Function SetNextOpenMult(Actor akTarget, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetNextOpenMult(afMult)
	Else
		PendingNextOpen[slot] = afMult
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

; 只讀本模組自己的印記關鍵字（規劃 2.2）。
Bool Function HasElementMark(Actor akTarget, Int aiElement)
	If !akTarget || aiElement < 1 || aiElement > 11 || !MarkKeywords
		Return False
	EndIf
	Keyword mark = MarkKeywords[aiElement - 1]
	If !mark
		Return False
	EndIf
	Return akTarget.HasMagicEffectWithKeyword(mark)
EndFunction

; 登記表裡帶指定元素印記、離玩家最近的一個（化身、雷神用）。
Actor Function NearestMarked(Int aiElement)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return None
	EndIf
	Actor player = ThePlayer()
	If !player
		Return None
	EndIf
	Actor best = None
	Float bestDistance = 100000.0
	Int index = 0
	While index < 8
		Actor target = RegActor[index]
		If target && RegElem[index] == aiElement && !target.IsDead()
			Float d = target.GetDistance(player)
			If d < bestDistance
				bestDistance = d
				best = target
			EndIf
		EndIf
		index += 1
	EndWhile
	Return best
EndFunction

; ---- 領域（火域、冰原）
; 規劃 2.9 的例外表：中心為目標、半徑 3 公尺、持續 5 秒。本模組不放任何
; ObjectReference，只記中心座標與剩餘秒數，判定在既有的每秒 tick 與命中路徑上做。
; 3 格：同元素的領域直接取代自己那一格，否則取空格，全滿就換掉剩餘秒數最少的那一格。
; 半徑預設 3 公尺（規劃 2.9 例外表），星域另外傳入隨主線成長的半徑。
Function StartDomain(Int aiElement, Actor akCenter, Int aiSeconds, Float afRadius = 210.0)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !akCenter
		Return
	EndIf
	Int slot = -1
	Int index = 0
	While index < 3
		If DomainLeft[index] > 0 && DomainElem[index] == aiElement
			slot = index
			index = 3
		EndIf
		index += 1
	EndWhile
	If slot < 0
		index = 0
		While index < 3
			If DomainLeft[index] <= 0
				slot = index
				index = 3
			EndIf
			index += 1
		EndWhile
	EndIf
	If slot < 0
		slot = 0
		index = 1
		While index < 3
			If DomainLeft[index] < DomainLeft[slot]
				slot = index
			EndIf
			index += 1
		EndWhile
	EndIf
	DomainElem[slot] = aiElement
	DomainTickAt[slot] = Utility.GetCurrentRealTime()
	DomainLeft[slot] = DomainTickAt[slot] + DurationSeconds(aiSeconds)
	DomainX[slot] = akCenter.GetPositionX()
	DomainY[slot] = akCenter.GetPositionY()
	DomainZ[slot] = akCenter.GetPositionZ()
	DomainR[slot] = afRadius
	ClearDomainResidents(slot)
	ObserveDomainResidents(slot, ScanDomainTargets(PO3_SKSEFunctions.GetActorsByProcessingLevel(0), slot), ThePlayer(), DomainTickAt[slot])
	; 特效前線：領域開場放一次該元素的爆炸（規劃 2.12 允許「大事」用爆炸記錄）。
	; 判定完全不變——三格、中心座標、半徑、剩餘秒數都還是腳本側的，沒有 ObjectReference。
	PlaceFx(aiElement, akCenter)
	If CachedDebugLevel >= 1
		LogEvent(1, "domain", "start element=" + aiElement + " sec=" + aiSeconds \
			+ " radius=" + afRadius + " slot=" + slot)
	EndIf
EndFunction

Bool Function InDomain(Actor akTarget, Int aiElement)
	If !IsOperational()
		Return False
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return False
	EndIf
	If !akTarget
		Return False
	EndIf
	Int index = 0
	While index < 3
		If DomainLeft[index] > Utility.GetCurrentRealTime() && DomainElem[index] == aiElement
			Float dx = akTarget.GetPositionX() - DomainX[index]
			Float dy = akTarget.GetPositionY() - DomainY[index]
			Float dz = akTarget.GetPositionZ() - DomainZ[index]
			Float r = DomainR[index]
			If dx * dx + dy * dy + dz * dz <= r * r
				Return True
			EndIf
		EndIf
		index += 1
	EndWhile
	Return False
EndFunction

Bool Function DomainActive()
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return False
	EndIf
	Int index = 0
	While index < 3
		If DomainLeft[index] > 0
			Return True
		EndIf
		index += 1
	EndWhile
	Return False
EndFunction

Bool Function PlayerInDomain(Int aiElement)
	Return InDomain(ThePlayer(), aiElement)
EndFunction

; 每秒：三格領域各自倒數並結算內部的持續效果（火域的熱度加倍由命中路徑讀 InDomain）。
; 共用一次候選池，逐領域先篩選再按距離取五人；最後一秒結算後才倒數。
Function TickDomain()
	If !IsOperational()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !DomainActive()
		Return
	EndIf
	Actor player = ThePlayer()
	Actor[] pool = PO3_SKSEFunctions.GetActorsByProcessingLevel(0)
	Int slot = 0
	While slot < 3
		If DomainLeft[slot] > 0
			Float stop = Utility.GetCurrentRealTime()
			If stop > DomainLeft[slot]
				stop = DomainLeft[slot]
			EndIf
			Actor[] nearby = ScanDomainTargets(pool, slot)
			ObserveDomainResidents(slot, nearby, player, Utility.GetCurrentRealTime())
			Int ticks = DomainTargetTicks(player, slot, stop)
			DomainTickAt[slot] = stop
			Int element = DomainElem[slot]
			If ticks > 0 && InsideDomainSlot(player, slot)
				If element == 6
					ApplyUtil(4, 20.0 * GLevel(5) * ticks, 0, player)
				ElseIf element == 7
					ApplyUtil(4, 25.0 * GLevel(6) * ticks, 0, player)
					ApplyUtil(5, 20.0 * GLevel(6) * ticks, 0, player)
				ElseIf element == 9
					ApplyUtil(4, 15.0 * GLevel(8) * ticks, 0, player)
					ApplyUtil(6, 15.0 * GLevel(8) * ticks, 0, player)
				EndIf
			EndIf
			Int index = 0
			While index < nearby.Length
				Actor victim = nearby[index]
				ticks = DomainTargetTicks(victim, slot, stop)
				If victim && ticks > 0
					If element == 2
						; 冰原：內部敵人減速 50%。
						ApplyUtil(0, 50.0, 2, victim)
					EndIf
					If element == 4
						; 5.6 傳奇分支「地裂」：減速 50%、耐力不回復；
						; 專精分支「地斷」的泥沼只有減速 40%（沒點地裂時）。
						If ESSBNodes.Br(Self, 3, 2, 4, 0)
							ApplyUtil(0, 50.0, 2, victim)
							ApplyUtil(21, 100.0, 2, victim)
						Else
							ApplyUtil(0, 40.0, 2, victim)
						EndIf
					EndIf
					If element == 8
						; 5.10 關閉傳奇分支「毒霧」：內部每秒 +1 毒層。
						AddStackTo(victim, 7, ticks)
					EndIf
					If element == 9
						; 5.11 關閉傳奇分支「潮池」：內部敵人減速 30%。
						ApplyUtil(0, 30.0, 2, victim)
					EndIf
					If element == 10
						; 5.12 關閉傳奇分支「死域」：內部敵人無法被治療、每秒受 B_max ×0.5 暗傷。
						ApplyUtil(20, 100.0, 2, victim)
						ApplyDotDamage(10, ESSBReactions.ReactDamage(Self, 10, 0.5) * ticks, victim)
					EndIf
				EndIf
				index += 1
			EndWhile
			; Resolve the final second before removing the domain.
			If Utility.GetCurrentRealTime() >= DomainLeft[slot]
				DomainLeft[slot] = 0.0
			EndIf
			If DomainLeft[slot] <= 0
				DomainElem[slot] = 0
				ClearDomainResidents(slot)
			EndIf
		EndIf
		slot += 1
	EndWhile
	; 鏡射給 PERK 進入點的是「玩家在不在領域裡」，不是「領域存不存在」。
	SetGlobal(GDomainFire, DomainFlag(1, False))
	SetGlobal(GDomainFrost, DomainFlag(2, False))
	SetGlobal(GDomainEarth, DomainFlag(4, False))
	SetGlobal(GDomainBlood, DomainFlag(6, True))
	SetGlobal(GDomainDivine, DomainFlag(7, True))
	SetGlobal(GDomainPoison, DomainFlag(8, False))
	SetGlobal(GDomainWater, DomainFlag(9, True))
	SetGlobal(GDomainDark, DomainFlag(10, False))
	SetGlobal(GDomainAstral, DomainFlag(11, False))
EndFunction

Actor[] Function ScanDomainTargets(Actor[] akPool, Int aiSlot)
	Actor[] result = new Actor[5]
	Float[] distances = new Float[5]
	If !akPool
		Return result
	EndIf
	Int index = 0
	While index < akPool.Length
		Actor candidate = akPool[index]
		If IsValidTarget(candidate)
			Float dx = candidate.GetPositionX() - DomainX[aiSlot]
			Float dy = candidate.GetPositionY() - DomainY[aiSlot]
			Float dz = candidate.GetPositionZ() - DomainZ[aiSlot]
			Float d = dx * dx + dy * dy + dz * dz
			If d <= DomainR[aiSlot] * DomainR[aiSlot]
				Int pos = 0
				Bool placed = False
				While pos < 5 && !placed
					If !result[pos] || d < distances[pos]
						Int shift = 4
						While shift > pos
							result[shift] = result[shift - 1]
							distances[shift] = distances[shift - 1]
							shift -= 1
						EndWhile
						result[pos] = candidate
						distances[pos] = d
						placed = True
					EndIf
					pos += 1
				EndWhile
			EndIf
		EndIf
		index += 1
	EndWhile
	Return result
EndFunction

; 領域鏡射：abPlayerOnly 為真時只有「玩家在裡面」才寫 1（聖域、血池、潮池是對玩家的條件）。
Int Function DomainFlag(Int aiElement, Bool abPlayerOnly)
	If !IsOperational()
		Return 0
	EndIf
	If abPlayerOnly
		If PlayerInDomain(aiElement)
			Return 1
		EndIf
		Return 0
	EndIf
	Int index = 0
	While index < 3
		If DomainLeft[index] > 0 && DomainElem[index] == aiElement
			Return 1
		EndIf
		index += 1
	EndWhile
	Return 0
EndFunction

; ---------------------------------------------------------------- 機制前線 round 2

; ---- 物理推力（規劃 2.6、2.9、8）
; 跌倒、吹飛、吹上天走 PushActorAway／ApplyHavokImpulse，每目標 8 秒一次；
; 拉近每目標 3 秒一次。免疫名單：龍、騎乘中、必要角色與首領、巨人與猛獁。
; 回傳 False 代表沒有推（冷卻中或免疫），呼叫端改上減速。

Bool Function CanRagdoll(Actor akTarget)
	If !akTarget || akTarget.IsDead()
		Return False
	EndIf
	If DragonKeyword && akTarget.HasKeyword(DragonKeyword)
		Return False
	EndIf
	If akTarget.IsOnMount()
		Return False
	EndIf
	If IsVIPTarget(akTarget)
		Return False
	EndIf
	Race theRace = akTarget.GetRace()
	If theRace && (theRace == GiantRace || theRace == MammothRace)
		Return False
	EndIf
	Return True
EndFunction

; aiKind 0 = 跌倒／吹飛／吹上天（8 秒），1 = 拉近（3 秒）。
Bool Function TakePush(Actor akTarget, Int aiKind)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return False
	EndIf
	If !akTarget
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Float window = 8.0
	If aiKind == 1
		window = 3.0
	ElseIf aiKind == 2
		; round 3 沖刷：每目標 10 秒一次（規劃 5.11）。
		window = 10.0
	EndIf
	Int index = 0
	While index < 8
		If KnockActor[index] == akTarget
			Float last = KnockTime[index]
			If aiKind == 1
				last = PullTime[index]
			ElseIf aiKind == 2
				last = WashTime[index]
			EndIf
			If now - last < CooldownSeconds(window)
				Return False
			EndIf
			If aiKind == 1
				PullTime[index] = now
			ElseIf aiKind == 2
				WashTime[index] = now
			Else
				KnockTime[index] = now
			EndIf
			Return True
		EndIf
		index += 1
	EndWhile
	KnockActor[KnockNext] = akTarget
	KnockTime[KnockNext] = 0.0
	PullTime[KnockNext] = 0.0
	WashTime[KnockNext] = 0.0
	If aiKind == 1
		PullTime[KnockNext] = now
	ElseIf aiKind == 2
		WashTime[KnockNext] = now
	Else
		KnockTime[KnockNext] = now
	EndIf
	KnockNext += 1
	If KnockNext >= 8
		KnockNext = 0
	EndIf
	Return True
EndFunction

; 跌倒：小力道的 PushActorAway（同吼聲的做法），不走硬直動畫。
Bool Function Knockdown(Actor akTarget, Float afForce)
	Actor player = ThePlayer()
	If !player || !CanRagdoll(akTarget) || !TakePush(akTarget, 0)
		Return False
	EndIf
	player.PushActorAway(akTarget, afForce)
	If CachedDebugLevel >= 2
		LogThrottled(2, "push", akTarget.GetFormID() + " knockdown force=" + afForce)
	EndIf
	Return True
EndFunction

; 吹飛：從玩家往外的水平衝量，距離以公尺計（1 公尺 = 70 單位）。
Bool Function BlowBack(Actor akTarget, Float afMetres)
	Actor player = ThePlayer()
	If !player || !CanRagdoll(akTarget) || !TakePush(akTarget, 0)
		Return False
	EndIf
	If afMetres <= 0.0
		Return False
	EndIf
	player.PushActorAway(akTarget, afMetres)
	If CachedDebugLevel >= 2
		LogThrottled(2, "push", akTarget.GetFormID() + " blowback m=" + afMetres)
	EndIf
	Return True
EndFunction

; 拉近：從目標往玩家的水平衝量。距離 1.5～3 公尺（規劃 2.9 的例外表）。
Bool Function PullIn(Actor akTarget, Float afMetres)
	Actor player = ThePlayer()
	If !player
		Return False
	EndIf
	Return PullTo(akTarget, player, afMetres)
EndFunction

; 把目標拉向另一個參照（風渦：拉向被終焉的目標；氣旋：拉向玩家）。
Bool Function PullTo(Actor akTarget, ObjectReference akCentre, Float afMetres)
	If !akTarget || !akCentre || !CanRagdoll(akTarget) || !TakePush(akTarget, 1)
		Return False
	EndIf
	If afMetres <= 0.0
		Return False
	EndIf
	akCentre.PushActorAway(akTarget, -afMetres)
	; 5.7 開啟大師分支「牽引」：拉近的目標 2 秒內無法後退（自有減速 80%）。
	If ESSBNodes.Br(Self, 4, 1, 3, 0)
		ApplyUtil(0, 80.0, 2, akTarget)
	EndIf
	If CachedDebugLevel >= 2
		LogThrottled(2, "push", akTarget.GetFormID() + " pull m=" + afMetres)
	EndIf
	Return True
EndFunction

; 吹上天：帶向上分量的衝量 + 1.5 秒「浮空」自有狀態（規劃 8：不讀物理狀態）。
Bool Function LiftUp(Actor akTarget, Float afMetres, Float afLandingDamage)
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return False
	EndIf
	Actor player = ThePlayer()
	If !player || !akTarget || afMetres <= 0.0 || !CanRagdoll(akTarget)
		Return False
	EndIf
	Int slot = 0
	While slot < 8 && LiftActor[slot]
		slot += 1
	EndWhile
	If slot >= 8 || !TakePush(akTarget, 0)
		Return False
	EndIf
	LiftDue[slot] = Utility.GetCurrentRealTime() + 0.15
	LiftForce[slot] = afMetres * 70.0
	LiftDamage[slot] = afLandingDamage
	LiftActor[slot] = akTarget
	LiftQueued = True
	; Ragdoll first; one delayed impulse, no polling or Wait loop.
	player.PushActorAway(akTarget, 0.1)
	LiftDue[slot] = Utility.GetCurrentRealTime() + 0.15
	ArmUpdate()
	If CachedDebugLevel >= 2
		LogThrottled(2, "push", akTarget.GetFormID() + " lift queued m=" + afMetres)
	EndIf
	Return True
EndFunction

; ---- 浮空（自有狀態，存在狀態容器裡，每秒 tick 倒數，到期結算落地傷害）
Function SetAirborne(Actor akTarget, Int aiSeconds, Float afDamage)
	AddStackTo(akTarget, 4, 1)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetAirborne(aiSeconds, afDamage)
	Else
		PendingAir[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)
		PendingAirDamage[slot] = afDamage
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Int Function GetAirborne(Actor akTarget)
	ESSBStatus status = GetStatus(akTarget)
	If !status
		Return 0
	EndIf
	Return status.GetAirborne()
EndFunction

; 由 ESSBStatus 在浮空到期時呼叫：落地傷害（5.7 關閉傳奇主線）。
Function OnLanding(Actor akTarget, Float afAmount)
	If afAmount > 0.0
		ApplyDamage(5, afAmount, akTarget)
		If CachedDebugLevel >= 1
			LogThrottled(1, "land", akTarget.GetFormID() + " amount=" + afAmount)
		EndIf
	EndIf
EndFunction

; ---- 聖盾、嗜血、各種視窗
Int Function GetHolyShield()
	Return HolyShield
EndFunction

Function AddHolyShield(Int aiAmount)
	HolyShield += aiAmount
	If HolyShield > 5
		HolyShield = 5
	EndIf
	GHolyShield.SetValueInt(HolyShield)
EndFunction

Function SetBloodthirst(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	BloodthirstLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GBloodthirst, SecondsLeft(BloodthirstLeft))
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Int Function GetBloodthirst()
	Return SecondsLeft(BloodthirstLeft)
EndFunction

Function SetGuardWind(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardWindLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardWind, SecondsLeft(GuardWindLeft))
	ApplyGuardWindow(3, GuardWindLeft)
EndFunction

Int Function GetGuardWindLeft()
	Int left = SecondsLeft(GuardWindLeft)
	SetGlobal(GGuardWind, left)
	Return left
EndFunction

Function SetGuardDivine(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardDivineLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardDivine, SecondsLeft(GuardDivineLeft))
	ApplyGuardWindow(4, GuardDivineLeft)
EndFunction

Function SetCloakGuard(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	CloakGuardLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GCloakGuard, SecondsLeft(CloakGuardLeft))
	ApplyGuardWindow(5, CloakGuardLeft)
EndFunction

Function SetNoBloodCost(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If Utility.GetCurrentRealTime() + aiSeconds > NoBloodCostLeft
		NoBloodCostLeft = Utility.GetCurrentRealTime() + aiSeconds
	EndIf
	SetGlobal(GNoBloodCost, SecondsLeft(NoBloodCostLeft))
EndFunction

Function SetWindFollow(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	WindFollowLeft = Utility.GetCurrentRealTime() + aiSeconds
EndFunction

Function SetRiposte(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	RiposteLeft = Utility.GetCurrentRealTime() + aiSeconds
EndFunction

Function SetPendingBleed(Int aiLayers)
	PendingBleed = aiLayers
EndFunction

Int Function TakePendingBleed()
	Int value = PendingBleed
	PendingBleed = 0
	Return value
EndFunction

Function SetPendingHeal()
	PendingHeal = True
EndFunction

Bool Function TakePendingHeal()
	Bool value = PendingHeal
	PendingHeal = False
	Return value
EndFunction

; 5.7 關閉傳奇分支「連殺」：擊殺後 5 秒內不解除潛行，下一次潛行攻擊 ×2。
Function KeepSneak(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	KeepSneakLeft = Utility.GetCurrentRealTime() + aiSeconds
	KillStreakReady = True
	Actor player = ThePlayer()
	If player
		; 規劃 8：用「壓低偵測值」實作，尊重原版偵測系統，不鎖 AI。
		PO3_SKSEFunctions.PreventActorDetection(player)
	EndIf
EndFunction

Bool Function TakeKillStreak()
	If !KillStreakReady || KeepSneakLeft <= Utility.GetCurrentRealTime()
		Return False
	EndIf
	KillStreakReady = False
	Return True
EndFunction

; 反震的 10 秒冷卻（5.6 持續大師分支）。
Bool Function TakeRetaliate()
	Float now = Utility.GetCurrentRealTime()
	If now - RetaliateTime < CooldownSeconds(10.0)
		Return False
	EndIf
	RetaliateTime = now
	Return True
EndFunction

; 庇護的 30 秒冷卻（5.9 大師分支）。
Bool Function TakeSanctuary()
	Float now = Utility.GetCurrentRealTime()
	If now - SanctuaryTime < CooldownSeconds(30.0)
		Return False
	EndIf
	SanctuaryTime = now
	Return True
EndFunction

; 神佑：每場戰鬥一次，脫戰時由每秒 tick 重置。
Bool Function TakeDivineSave()
	If DivineSaveUsed || !ESSBNodes.Br(Self, 6, 0, 4, 0) || SyncStage() < 3
		Return False
	EndIf
	DivineSaveUsed = True
	Return True
EndFunction

; ---------------------------------------------------------------- 機制前線 round 3

; ---- 水鏡（5.11 持續大師分支）：每命中 +1 層（最多 3），被打消耗一層抵消 30% 傷害。
Int Function GetWaterMirror()
	Return WaterMirror
EndFunction

Function AddWaterMirror(Int aiAmount)
	WaterMirror += aiAmount
	If WaterMirror > 3
		WaterMirror = 3
	EndIf
	SetGlobal(GWaterMirror, WaterMirror)
EndFunction

Function ConsumeWaterMirror()
	If WaterMirror > 0
		WaterMirror -= 1
		SetGlobal(GWaterMirror, WaterMirror)
	EndIf
EndFunction

; ---- round 3 的受傷視窗（PERK 進入點讀這三個鏡射全域變數）
Function SetGuardDark(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardDarkLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardDark, SecondsLeft(GuardDarkLeft))
	ApplyGuardWindow(6, GuardDarkLeft)
EndFunction

Int Function GetGuardDarkLeft()
	Int left = SecondsLeft(GuardDarkLeft)
	SetGlobal(GGuardDark, left)
	Return left
EndFunction

Function SetGuardAstral(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If Utility.GetCurrentRealTime() + aiSeconds > GuardAstralLeft
		GuardAstralLeft = Utility.GetCurrentRealTime() + aiSeconds
	EndIf
	SetGlobal(GGuardAstral, SecondsLeft(GuardAstralLeft))
	ApplyGuardWindow(7, GuardAstralLeft)
EndFunction

Function SetGuardStar(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardStarLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GGuardStar, SecondsLeft(GuardStarLeft))
	ApplyGuardWindow(8, GuardStarLeft)
EndFunction

; ---- 蝕魔終焉（5.12 關閉熟練分支）：下一次終焉附帶吸魔
Function SetPendingDrain()
	PendingDrain = True
EndFunction

Bool Function TakePendingDrain()
	Bool value = PendingDrain
	PendingDrain = False
	Return value
EndFunction

; ---- 星界之門（5.13 關閉大師分支）：接管元素直接視為同調一段
Function BoostSyncToStage1()
	Int threshold = 5
	If SyncT1
		threshold = SyncT1.GetValueInt()
	EndIf
	If Sync.GetValueInt() < threshold
		CachedSync = threshold
		Sync.SetValueInt(threshold)
		PushSyncStage()
		If CachedDebugLevel >= 1
			LogThrottled(1, "node", "astral gate sync=" + threshold)
		EndIf
	EndIf
EndFunction

; ---- 追擊（5.13 持續熟練分支）：每第 3 次命中。滿 3 就歸零並回傳 3。
Int Function BumpAstralHits()
	AstralHits += 1
	If AstralHits >= 3
		AstralHits = 0
		Return 3
	EndIf
	Return AstralHits
EndFunction

; ---- 洗淨／淨化（5.11）：每 3 秒一次，清除自身負面效果。
; 規劃 8：不用原版 Dispel 對自己施放（會洗掉自己的增益），改用限定關鍵字的 Dispel。
Bool Function TakeCleanse()
	Float now = Utility.GetCurrentRealTime()
	If now - CleanseTime < CooldownSeconds(3.0)
		Return False
	EndIf
	CleanseTime = now
	Return True
EndFunction

; 安全建構：**不**依賴原型 2（Dispel）與旗標 0x100（Dispel Keywords），兩者在機制前線
; 都只是推論值。三段做法，每一段都只可能少清、不可能誤清玩家自己的增益：
;   1. 明確清單：本模組自己的有時限減益（SelfCleanseSpells），逐個 DispelSpell。
;   2. 原版實測原型：法術本體只留治病（3）與解毒（29），兩個都在 Skyrim.esm 有對照。
;   3. 外來減益：PO3 GetActiveEffects 掃現行效果，只挑「敵對 0x1 或有害 0x4」的，
;      再用 GetMagicEffectSource 回推來源法術後 DispelSpell。
; 形態能力、血承、岩甲、抗咒這些自有增益都不帶敵對／有害旗標，所以第 3 段碰不到它們。
Function ApplyCleanse(Bool abPurge)
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Int removed = 0
	; 1. 自有減益。
	If SelfCleanseSpells
		Int index = 0
		While index < SelfCleanseSpells.Length
			Spell own = SelfCleanseSpells[index]
			If own && player.HasMagicEffect(own.GetNthEffectMagicEffect(0))
				player.DispelSpell(own)
				removed += 1
			EndIf
			index += 1
		EndWhile
	EndIf
	; 2. 治病（洗淨與淨化都有）＋解毒（只有淨化有），走法術本體的原版原型。
	Spell chosen = CleanseSpell
	If abPurge && PurgeSpell
		chosen = PurgeSpell
	EndIf
	If chosen
		player.DoCombatSpellApply(chosen, player)
	EndIf
	; 3. 外來的敵對／有害效果。淨化才做（洗淨只清自己那幾類，規劃 5.11 的分支差異）。
	If abPurge
		removed += DispelHostileEffects(player)
	EndIf
	If CachedDebugLevel >= 1
		LogThrottled(1, "cleanse", "self purge=" + abPurge + " removed=" + removed)
	EndIf
EndFunction

; PO3 GetActiveEffects → 只取帶敵對（0x1）或有害（0x4）旗標的 MagicEffect，
; 回推來源法術再 DispelSpell。找不到來源（例如附魔或藥水）就跳過，不做任何猜測。
Int Function DispelHostileEffects(Actor akActor)
	If !akActor
		Return 0
	EndIf
	MagicEffect[] active = PO3_SKSEFunctions.GetActiveEffects(akActor, False)
	If !active
		Return 0
	EndIf
	Int removed = 0
	Int index = 0
	While index < active.Length
		MagicEffect effect = active[index]
		If effect && (effect.IsEffectFlagSet(1) || effect.IsEffectFlagSet(4))
			Form[] sources = PO3_SKSEFunctions.GetMagicEffectSource(akActor, effect)
			Int s = 0
			While sources && s < sources.Length
				Spell source = sources[s] as Spell
				If source
					akActor.DispelSpell(source)
					removed += 1
				EndIf
				s += 1
			EndWhile
		EndIf
		index += 1
	EndWhile
	Return removed
EndFunction

; ---- 沖刷／洗滌（5.11）：對目標的 Dispel 原型，只影響有時限的法術效果。
; 每目標 10 秒一次（沿用推力的環狀表，kind 2）。
; TARGET 路徑才留無限定的 Dispel 原型，所以這裡硬性擋掉「對玩家自己施放」。
Function ApplyStrip(Actor akTarget)
	Actor player = ThePlayer()
	If !player || !StripSpell || !akTarget
		Return
	EndIf
	If akTarget == player
		If CachedDebugLevel >= 1
			LogEvent(1, "strip", "refused: never dispel the player with the target-path Dispel")
		EndIf
		Return
	EndIf
	If !IsValidTarget(akTarget)
		Return
	EndIf
	If !TakePush(akTarget, 2)
		Return
	EndIf
	player.DoCombatSpellApply(StripSpell, akTarget)
	If CachedDebugLevel >= 1
		LogThrottled(1, "strip", akTarget.GetFormID() + " dispel timed buff")
	EndIf
EndFunction

; ---------------------------------------------------------------- 特效（規劃 2.11、2.12）

; 一次性爆炸。規劃 2.12 的效能守則：爆炸只用在終焉、融斷、領域這種「大事」，
; 普通命中禁止用；範圍事件最多播 5 個目標。預算窗口 0.5 秒 5 個，
; 融斷一次最多 16 次 EndMark 也只會放出 5 個。
Function PlaceFx(Int aiElement, ObjectReference akWhere)
	If !akWhere || aiElement < 1 || aiElement > 11 || !FxExplosions
		Return
	EndIf
	If aiElement > FxExplosions.Length
		Return
	EndIf
	Form burst = FxExplosions[aiElement - 1]
	If !burst
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If now - FxBudgetTime >= 0.5
		FxBudgetTime = now
		FxBudget = 0
	EndIf
	If FxBudget >= 5
		Return
	EndIf
	FxBudget += 1
	akWhere.PlaceAtMe(burst, 1, False, False)
EndFunction

; 形態音效。SOUN 記錄是從 Phenderix 複製進本模組的（ESSBFX_ZZSound_*），
; FIX10: build_v03.py forces both FormActive and DrawSheathe descriptors to one-shot.
; Release / Charge are already one-shot; no persistent instance or StopInstance is needed.
Function PlayFormSound(Sound[] akBank, Int aiElement)
	If !akBank || aiElement < 1 || aiElement > 11 || aiElement > akBank.Length
		Return
	EndIf
	Sound chosen = akBank[aiElement - 1]
	Actor player = ThePlayer()
	If chosen && player
		chosen.Play(player)
	EndIf
EndFunction

; ---- 恐懼與瘋狂（5.12）：自有 Demoralize／Frenzy 效果，magnitude 就是等級上限
; （同原版幻術）。首領、龍、亡靈魔族與機械免疫；秒數由呼叫端給。
Bool Function CanCharm(Actor akTarget)
	If !akTarget || akTarget.IsDead()
		Return False
	EndIf
	If IsVIPTarget(akTarget)
		Return False
	EndIf
	If DragonKeyword && akTarget.HasKeyword(DragonKeyword)
		Return False
	EndIf
	If IsUndeadOrDaedra(akTarget)
		Return False
	EndIf
	Return akTarget.GetLevel() <= ESSBElem3.CharmCap(Self)
EndFunction

Function ApplyFear(Actor akTarget, Int aiSeconds)
	Actor player = ThePlayer()
	If !player || !FearSpell || !CanCharm(akTarget) || aiSeconds < 1
		Return
	EndIf
	FearSpell.SetNthEffectMagnitude(0, ESSBElem3.CharmCap(Self) as Float)
	FearSpell.SetNthEffectDuration(0, DurationInt(aiSeconds))
	player.DoCombatSpellApply(FearSpell, akTarget)
	If CachedDebugLevel >= 1
		LogThrottled(1, "fear", akTarget.GetFormID() + " sec=" + aiSeconds)
	EndIf
EndFunction

Function ApplyFrenzy(Actor akTarget, Int aiSeconds)
	Actor player = ThePlayer()
	If !player || !FrenzySpell || !CanCharm(akTarget) || aiSeconds < 1
		Return
	EndIf
	FrenzySpell.SetNthEffectMagnitude(0, ESSBElem3.CharmCap(Self) as Float)
	FrenzySpell.SetNthEffectDuration(0, DurationInt(aiSeconds))
	player.DoCombatSpellApply(FrenzySpell, akTarget)
	If CachedDebugLevel >= 1
		LogThrottled(1, "frenzy", akTarget.GetFormID() + " sec=" + aiSeconds)
	EndIf
EndFunction

; ---- 亡者歸來（5.12）：自有 Reanimate 原型。召喚上限含原版雙魂天賦。
Int Function SummonCap()
	Actor player = ThePlayer()
	Int cap = 1
	If player && TwinSoulsPerk && player.HasPerk(TwinSoulsPerk)
		cap = 2
	EndIf
	Return cap
EndFunction

Int Function ServantCount()
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return 0
	EndIf
	Actor player = ThePlayer()
	If !player
		Return 99
	EndIf
	Actor[] thralls = PO3_SKSEFunctions.GetCommandedActors(player)
	Int count = 0
	If thralls
		count = thralls.Length
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int index = 0
	While index < 2
		Actor pending = PendingServants[index]
		If pending
			Bool present = False
			Int t = 0
			While thralls && t < thralls.Length
				If thralls[t] == pending
					present = True
				EndIf
				t += 1
			EndWhile
			If present || now >= PendingServantDue[index]
				PendingServants[index] = None
			Else
				count += 1
			EndIf
		EndIf
		index += 1
	EndWhile
	Return count
EndFunction

; 必要角色、任務角色、已經化灰或被標記不可復生的屍體都不復生（規劃 5.12、2.9）。
Bool Function CanReanimate(Actor akTarget)
	If !akTarget
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=can-reanimate-invalid-target")
		EndIf
		Return False
	EndIf
	If IsVIPTarget(akTarget)
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=can-reanimate-vip")
		EndIf
		Return False
	EndIf
	If DragonKeyword && akTarget.HasKeyword(DragonKeyword)
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=can-reanimate-dragon")
		EndIf
		Return False
	EndIf
	If NoReanimateKeyword && akTarget.HasKeyword(NoReanimateKeyword)
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=can-reanimate-no-reanimate-keyword")
		EndIf
		Return False
	EndIf
	Return True
EndFunction

Bool Function ApplyReanimate(Actor akTarget, Int aiLevelCap, Int aiSeconds)
	; Claim the transaction before native/cross-script calls release our lock.
	If ReanimateBusy
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=apply-busy")
		EndIf
		Return False
	EndIf
	ReanimateBusy = True
	InitFixState()
	If !IsCurrentController() || StateBroken
		ReanimateBusy = False
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=apply-stale-or-broken")
		EndIf
		Return False
	EndIf
	Actor player = ThePlayer()
	If !player || !ReanimateSpell || !akTarget
		ReanimateBusy = False
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=apply-missing-player-spell-target")
		EndIf
		Return False
	EndIf
	Int cap = SummonCap()
	If aiSeconds >= 86313600
		cap = 1
	EndIf
	If ServantCount() >= cap
		ReanimateBusy = False
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=servant-cap-full")
		EndIf
		Return False
	EndIf
	Int slot = 0
	While slot < 2 && PendingServants[slot]
		slot += 1
	EndWhile
	If slot >= 2
		ReanimateBusy = False
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=apply-pending-slots-full")
		EndIf
		Return False
	EndIf
	PendingServants[slot] = akTarget
	PendingServantDue[slot] = Utility.GetCurrentRealTime() + 5.0
	ReanimateSpell.SetNthEffectMagnitude(0, aiLevelCap as Float)
	ReanimateSpell.SetNthEffectDuration(0, DurationInt(aiSeconds))
	player.DoCombatSpellApply(ReanimateSpell, akTarget)
	ReanimateBusy = False
	If CachedDebugLevel >= 1
		LogEvent(1, "reanimate", akTarget.GetFormID() + " levelCap=" + aiLevelCap + " sec=" + aiSeconds)
	EndIf
	Return True
EndFunction

; ---- 「你中毒時」的判定（5.10 持續大師分支「以毒攻毒」）
Bool Function IsPoisoned(Actor akTarget)
	If !akTarget || !HarmfulKeyword
		Return False
	EndIf
	Return akTarget.HasMagicEffectWithKeyword(HarmfulKeyword)
EndFunction

; ---- 汪洋（5.11 關閉專精分支）：終焉後把該元素保留成副印記，融斷時再結算一次。
Function KeepAsSecond(Actor akTarget, Int aiElement, Int aiSeconds)
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0 || RegElem2[slot] >= 1
		Return
	EndIf
	RegElem2[slot] = aiElement
	RegSeq2[slot] = RegSeq[slot]
	RegSecondUntil[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)
	If CachedDebugLevel >= 2
		LogThrottled(2, "node", "water ocean second mark element=" + aiElement)
	EndIf
EndFunction

; ---- 大潮（5.11 關閉大師分支）：對別的目標設定「接管元素的下一次終焉」倍率。
Function SetNextEndMultOn(Actor akTarget, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetNextEndMult(afMult)
	Else
		PendingNextEnd[slot] = afMult
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

; ---- 星鎖（5.13 開啟大師分支）：開印目標 3 秒內受所有元素傷 +10%。
Function SetStarLock(Actor akTarget, Int aiSeconds)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetStarLock(aiSeconds)
	Else
		If Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds) > RegPendStarLock[slot]
			RegPendStarLock[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)
		EndIf
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Bool Function HasStarLock(Actor akTarget)
	ESSBStatus status = GetStatus(akTarget)
	If !status
		Return False
	EndIf
	Return status.HasStarLock()
EndFunction

; ---- 汪洋之始（5.11 開啟傳奇分支）：浸濕不會過期，直到被切掉。
Function SetWetLock(Actor akTarget)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetWetLock()
	Else
		RegPendWetLock[slot] = True
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

; ---- 化灰與血承
; FIX14: bounded per-actor recent damage survives registry eviction; no current-form fallback.
Int Function LastDamageFor(Actor akTarget)
	If !akTarget || !DamageActor || !SwapFloats || SwapFloats.Length != 128
		Return 0
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int i = 0
	While i < 128
		If DamageActor[i] == akTarget
			Float age = now - SwapFloats[i]
			If DamageElement[i] >= 1 && age >= 0.0 && age <= ESSBState.KillAttributionSeconds()
				Return DamageElement[i]
			EndIf
			Return 0
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction

Bool Function LastDamageWasElement(Actor akTarget, Int aiElement)
	Return LastDamageFor(akTarget) == aiElement
EndFunction

Int Function NoteDamageElement(Actor akTarget, Int aiElement, Int aiSlot = -1, Int aiGeneration = -1, Int aiDamageSlot = -1)
	If !akTarget || !DamageActor
		Return -1
	EndIf
	Int slot = aiSlot
	If slot >= 0 && (RegActor[slot] != akTarget || RegGeneration[slot] != aiGeneration)
		slot = -1
	EndIf
	If slot < 0
		slot = FindSlotInternal(akTarget)
	EndIf
	If slot >= 0 && aiElement >= 0
		RegLastDamage[slot] = aiElement
	EndIf
	If aiDamageSlot >= 0 && DamageActor[aiDamageSlot] == akTarget
		If aiElement >= 0
			DamageElement[aiDamageSlot] = aiElement
		EndIf
		Return aiDamageSlot
	EndIf
	Int i = 0
	While i < 128
		If DamageActor[i] == akTarget
			If aiElement >= 0
				DamageElement[i] = aiElement
			EndIf
			Return i
		EndIf
		i += 1
	EndWhile
	Int assigned = DamageNext
	DamageActor[DamageNext] = akTarget
	DamageElement[DamageNext] = 0
	SwapFloats[DamageNext] = -1.0
	If aiElement >= 0
		DamageElement[DamageNext] = aiElement
	EndIf
	DamageNext = (DamageNext + 1) % 128
	Return assigned
EndFunction

; All damaging spells are instant contact/self delivery (DELIVERY build gate).
; FIX14: publish before native delivery for lethal callback ordering; keep nonlethal damage.
; No health loss rolls back the provisional record. Never infer an element from form.
Function ApplyTrackedDamage(Actor player, Spell akSpell, Actor akTarget, Int aiElement, Int aiSlot = -1, Int aiGeneration = -1)
	If StateBroken || !Ready || !player || !akSpell || !akTarget
		Return
	EndIf
	Float beforeHealth = akTarget.GetActorValue("Health")
	If akTarget.IsDead() || beforeHealth <= 0.0 || !IsOperational()
		Return
	EndIf
	Int damageSlot = NoteDamageElement(akTarget, -1, aiSlot, aiGeneration)
	If damageSlot < 0
		Return
	EndIf
	Int previous = DamageElement[damageSlot]
	Float previousTime = SwapFloats[damageSlot]
	Float now = Utility.GetCurrentRealTime()
	DamageElement[damageSlot] = aiElement
	SwapFloats[damageSlot] = now
	player.DoCombatSpellApply(akSpell, akTarget)
	If akTarget.GetActorValue("Health") >= beforeHealth && DamageActor[damageSlot] == akTarget && SwapFloats[damageSlot] == now && DamageElement[damageSlot] == aiElement
		DamageElement[damageSlot] = previous
		SwapFloats[damageSlot] = previousTime
	EndIf
EndFunction

Bool Function ApplyAsh(Actor akTarget)
	Actor player = ThePlayer()
	If !player || !AshSpell || !akTarget
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-missing-player-spell-target")
		EndIf
		Return False
	EndIf
	; 規劃 8：龍不受崩解，原版即如此；必要角色也不化灰（規劃 2.9 的例外欄）。
	If DragonKeyword && akTarget.HasKeyword(DragonKeyword)
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-dragon")
		EndIf
		Return False
	EndIf
	If IsVIPTarget(akTarget)
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-vip")
		EndIf
		Return False
	EndIf
	AshSpell.SetNthEffectMagnitude(0, akTarget.GetActorValueMax("Health") + 100.0)
	player.DoCombatSpellApply(AshSpell, akTarget)
	Return True
EndFunction

; 5.8 持續專精分支「血承」：擊殺流血目標時吸收其屬性 15 秒，只保留最近一個。
; 七個效果的 magnitude 在施放前一次設定完（火冰電毒魔抗各 50%、護甲 20%、最大生命 10%）。
Function ApplyInherit(Actor akVictim)
	Actor player = ThePlayer()
	If !player || !InheritSpell || !akVictim
		Return
	EndIf
	InheritSpell.SetNthEffectMagnitude(0, akVictim.GetActorValue("FireResist") * 0.5)
	InheritSpell.SetNthEffectMagnitude(1, akVictim.GetActorValue("FrostResist") * 0.5)
	InheritSpell.SetNthEffectMagnitude(2, akVictim.GetActorValue("ElectricResist") * 0.5)
	InheritSpell.SetNthEffectMagnitude(3, akVictim.GetActorValue("PoisonResist") * 0.5)
	InheritSpell.SetNthEffectMagnitude(4, akVictim.GetActorValue("MagicResist") * 0.5)
	InheritSpell.SetNthEffectMagnitude(5, RecoveryAmount(akVictim.GetActorValue("DamageResist") * 0.2))
	InheritSpell.SetNthEffectMagnitude(6, RecoveryAmount(akVictim.GetActorValueMax("Health") * 0.1))
	Int effect = 0
	While effect < 7
		InheritSpell.SetNthEffectDuration(effect, DurationInt(15))
		effect += 1
	EndWhile
	player.DoCombatSpellApply(InheritSpell, player)
	If CachedDebugLevel >= 1
		LogThrottled(1, "node", "blood inherit from " + akVictim.GetFormID())
	EndIf
EndFunction

; 規劃 8「死靈施法者」判定：原版沒有關鍵字，本模組取三個候選的聯集——
; 職業 CombatMageNecro（0x0C969F）、陣營 NecromancerFaction（0x034B74）、
; 以及身邊有復生僕從（PO3 GetCommandedActors）。三者都是本機 Skyrim.esm 掃出來的實測值。
Bool Function IsNecromancer(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	ActorBase base = akTarget.GetActorBase()
	If base && NecroClass && base.GetClass() == NecroClass
		Return True
	EndIf
	If NecroFaction && akTarget.IsInFaction(NecroFaction)
		Return True
	EndIf
	Actor[] thralls = PO3_SKSEFunctions.GetCommandedActors(akTarget)
	Return thralls && thralls.Length > 0
EndFunction

; ---- 擊殺事件（ESSBGuard 的 OnActorKilled）
; FIX14: called only at death/capture. Real marks exclude virtual residual/ocean marks.
Int Function KillElementFor(Actor akVictim, Int aiSlot = -1)
	Int recent = LastDamageFor(akVictim)
	If recent >= 1
		Return recent
	EndIf
	If aiSlot < 0 || RegActor[aiSlot] != akVictim
		Return 0
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int element = 0
	Int sequence = -1
	If RegElem[aiSlot] >= 1 && RegUntil[aiSlot] > now && (RegMark[aiSlot] || (MarkSpells && akVictim.HasMagicEffect(MarkSpells[RegElem[aiSlot] - 1].GetNthEffectMagicEffect(0))))
		element = RegElem[aiSlot]
		sequence = RegSeq[aiSlot]
	EndIf
	If RegElem2[aiSlot] >= 1 && RegSecondReal[aiSlot] && RegSecondUntil[aiSlot] > now && RegSeq2[aiSlot] > sequence && (RegMark2[aiSlot] || (MarkSpells && akVictim.HasMagicEffect(MarkSpells[RegElem2[aiSlot] - 1].GetNthEffectMagicEffect(0))))
		element = RegElem2[aiSlot]
	EndIf
	Return element
EndFunction

Function CaptureDeath(Int aiSlot)
	Actor victim = RegActor[aiSlot]
	Int index = 0
	While index < 8
		If DeadActor[index] == victim || SettledDead[index] == victim
			Return
		EndIf
		index += 1
	EndWhile
	Int element = KillElementFor(victim, aiSlot)
	Int freeze = GetStack(victim, 2)
	Int bleed = GetStack(victim, 5)
	Int poison = GetStack(victim, 7)
	Int curse = GetStack(victim, 10)
	Int heat = GetStack(victim, 1)
	Int holy = GetStack(victim, 6)
	DeadActor[DeadNext] = victim
	DeadElement[DeadNext] = element
	DeadFreeze[DeadNext] = freeze
	DeadBleed[DeadNext] = bleed
	DeadPoison[DeadNext] = poison
	DeadCurse[DeadNext] = curse
	DeadHeat[DeadNext] = heat
	DeadHoly[DeadNext] = holy
	DeadNext = (DeadNext + 1) % 8
	SettleDeadCurse(aiSlot)
EndFunction

Function OnKillEvent(Actor akVictim, Actor akKiller = None)
	If !IsOperational()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !akVictim || akKiller != ThePlayer()
		Return
	EndIf
	Int index = 0
	While index < 8
		If SettledDead[index] == akVictim
			Return
		EndIf
		index += 1
	EndWhile
	Int captureSlot = FindSlot(akVictim)
	If captureSlot >= 0
		CaptureDeath(captureSlot)
	EndIf
	; Claim before calling any other script: repeated events cannot grant twice.
	Int settlement = SettledNext
	SettledElement[settlement] = 0
	SettledDead[SettledNext] = akVictim
	SettledNext = (SettledNext + 1) % 8
	Int slot = FindSlot(akVictim)
	Int element = KillElementFor(akVictim, slot)
	Int freeze = 0
	Int bleed = 0
	Int poison = 0
	Int curse = 0
	If slot >= 0
		freeze = GetStack(akVictim, 2)
		bleed = GetStack(akVictim, 5)
		poison = GetStack(akVictim, 7)
		curse = GetStack(akVictim, 10)
	EndIf
	index = 0
	While index < 8
		If DeadActor[index] == akVictim
			element = DeadElement[index]
			freeze = DeadFreeze[index]
			bleed = DeadBleed[index]
			poison = DeadPoison[index]
			curse = DeadCurse[index]
			DeadActor[index] = None
		EndIf
		index += 1
	EndWhile
	Int killingElement = element
	SettledElement[settlement] = killingElement
	Bool ash = ESSBElem2.ShouldAsh(Self, killingElement)
	ESSBElem.OnKill(Self, element, akVictim, freeze)
	ESSBElem2.OnKill(Self, element, akVictim, bleed, killingElement, ash)
	ESSBElem3.OnKill(Self, element, akVictim, poison, killingElement, ash, curse)
	SettleSneakKill(akVictim, killingElement)
	SettleKillProc(akVictim)
	ESSBNoForm.OnKill(Self, akVictim, ESSBNoForm.IsSpellUser(Self, akVictim))
	If slot >= 0 && RegActor[slot] == akVictim
		ClearSlot(slot)
	EndIf
	If CachedDebugLevel >= 1
		LogThrottled(1, "kill", akVictim.GetFormID() + " element=" + element)
	EndIf
EndFunction

; ---- 同伴掃描（祝福、聖光、聖臨強化）。ScanTargets 刻意排除同伴，所以另走這一條。
Actor[] Function ScanAllies(Float afRadius)
	Actor[] result = new Actor[5]
	Actor player = ThePlayer()
	If !player
		Return result
	EndIf
	Actor[] pool = PO3_SKSEFunctions.GetActorsByProcessingLevel(0)
	If !pool
		Return result
	EndIf
	Int found = 0
	Int index = 0
	While index < pool.Length && found < 5
		Actor candidate = pool[index]
		If candidate && candidate != player && !candidate.IsDead() \
			&& (candidate.IsPlayerTeammate() || candidate.IsCommandedActor()) \
			&& player.GetDistance(candidate) <= afRadius
			result[found] = candidate
			found += 1
		EndIf
		index += 1
	EndWhile
	Return result
EndFunction

; ---- 風形態的移速與潛行能力（規劃 1.1、5.7）
; 移速強度隨節點變動，所以 AddSpell 之前先 SetNthEffectMagnitude。
; 規劃 8 的「SpeedMult 重新整理」：本模組所有移速修正都走 MGEF（與原版 FrostSlowFFContact
; 同款，AV 30 + 原型 34），引擎在效果掛上時就會重算移動速度；為保險，掛完再做一次
; 負重微調（+0.1／-0.1，淨值為零）強迫重算衍生數值。兩次原生呼叫，只在形態開／切／關時跑。
Function RefreshWindAbilities()
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Bool windForm = FormActive.GetValueInt() == 1 && CurrentElement.GetValueInt() == 5
	If WindSpeedAbility
		Bool has = player.HasSpell(WindSpeedAbility)
		If windForm
			Float bonus = ESSBElem2.WindSpeedBonus(Self)
			If has
				player.RemoveSpell(WindSpeedAbility)
			EndIf
			WindSpeedAbility.SetNthEffectMagnitude(0, bonus)
			player.AddSpell(WindSpeedAbility, False)
			RefreshSpeed()
		ElseIf has
			player.RemoveSpell(WindSpeedAbility)
			RefreshSpeed()
		EndIf
	EndIf
	RefreshWindStealth(windForm)
EndFunction

; 潛行狀態每秒讀一次（不是每幀）：潛行中掛「無聲」或基礎的 Muffle 0.5，站起來就拿掉。
Function RefreshWindStealth(Bool abWindForm)
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Bool wantSilent = abWindForm && SneakingNow && ESSBElem2.HasSilent(Self)
	Bool wantMuffle = abWindForm && SneakingNow && !wantSilent
	SyncAbility(player, SilentAbility, wantSilent)
	SyncAbility(player, WindMuffleAbility, wantMuffle)
	If wantSilent != SilentOn
		SilentOn = wantSilent
		RefreshSpeed()
	EndIf
EndFunction

Function RefreshSpeed()
	Actor player = ThePlayer()
	If player
		player.ModActorValue("CarryWeight", 0.1)
		player.ModActorValue("CarryWeight", -0.1)
	EndIf
EndFunction

; ---------------------------------------------------------------- 除錯：印出目標表

Function DumpRegistry()
	If !IsOperational()
		Return
	EndIf
	InitRegistry()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	Int live = 0
	Debug.Trace("[ESSB][dump][L0] registry element=" + CurrentElement.GetValueInt() \
		+ " active=" + FormActive.GetValueInt() + " sync=" + Sync.GetValueInt() + " stage=" + SyncStage() \
		+ " charge=" + SelfCharge + " rock=" + SelfRockArmor + " wind=" + SelfWind + " overheat=" + SelfOverheat \
		+ " wet=" + IsEnvWet() + " stormy=" + IsEnvStormy() + " night=" + IsEnvNight())
	Int index = 0
	While index < 8
		Actor target = RegActor[index]
		If target
			live += 1
			Float distance = -1.0
			If player
				distance = target.GetDistance(player)
			EndIf
			String line = "[ESSB][dump][L0] slot=" + index + " target=" + target.GetFormID() \
				+ " element=" + RegElem[index] + " seq=" + RegSeq[index] + " dist=" + distance \
				+ " pend=" + RegPendElem[index] + "/" + RegPendAmt[index]
			ESSBStatus status = RegStatus[index]
			If status
				line = line + " " + status.Describe()
			Else
				line = line + " status=none"
			EndIf
			Debug.Trace(line)
		EndIf
		index += 1
	EndWhile
	Debug.Trace("[ESSB][dump][L0] registry end live=" + live + "/8")
	Debug.Notification("元素魔戰士：目標表 " + live + "/8 已寫入 Papyrus 紀錄")
EndFunction

; ---------------------------------------------------------------- 節流紀錄

Function LogThrottled(Int aiLevel, String asMechanism, String asMessage)
	If CachedDebugLevel < aiLevel
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	String logKey = asMechanism + "|" + asMessage
	If logKey == LogLastKey && now - LogLastTime < 0.5
		; 同一目標同一訊息 0.5 秒內不重複（規劃 6.1）。
		Return
	EndIf
	LogLastKey = logKey
	LogLastTime = now
	If now - LogWindowStart >= 1.0
		LogWindowStart = now
		If LogDropped > 0
			Debug.Trace("[ESSB][log][L" + aiLevel + "] dropped=" + LogDropped)
			LogDropped = 0
		EndIf
		LogCount = 0
	EndIf
	If LogCount >= 20
		LogDropped += 1
		Return
	EndIf
	LogCount += 1
	Debug.Trace("[ESSB][" + asMechanism + "][L" + aiLevel + "] " + asMessage)
EndFunction

Function AddAstral(Actor akTarget, Int aiLayers, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.AddAstral(aiLayers, afMult)
		Return
	EndIf
	Int room = StackCap(11) - PendingAstral[slot]
	If aiLayers < room
		room = aiLayers
	EndIf
	If room > 0
		PendingAstral[slot] = PendingAstral[slot] + room
		PendingAstralWeight[slot] = PendingAstralWeight[slot] + room * afMult
	EndIf
	EnsureStatus(slot, akTarget)
EndFunction

Function DetonateAstralNow(Actor akTarget, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.DetonateAstralNow(afMult)
	Else
		PendingRadiance[slot] = afMult
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Function SetFrozen(Actor akTarget, Float afSeconds)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetFrozen(afSeconds)
	Else
		PendingFrozen[slot] = Utility.GetCurrentRealTime() + DurationSeconds(afSeconds)
		SetStack(akTarget, 2, 5)
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Function ConsumeEndCharge(Int aiCharge)
	If aiCharge > 0 && !ESSBNodes.Br(Self, 2, 2, 1, 0)
		SelfCharge -= aiCharge
		If SelfCharge < 0
			SelfCharge = 0
		EndIf
		GCharge.SetValueInt(SelfCharge)
	EndIf
EndFunction

Function SetCatalyzeOn(Actor akTarget, Int aiSeconds, Float afMult)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetCatalyze(aiSeconds, afMult)
	Else
		PendingCatalyze[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)
		PendingCatalyzeMult[slot] = afMult
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Function SetDeathCurseOn(Actor akTarget, Int aiSeconds, Float afBase, Float afMult)
	If akTarget && akTarget.IsDead()
		ESSBElem3.AfterDeathCurse(Self, akTarget, afBase * afMult)
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		status.SetDeathCurse(aiSeconds, afBase, afMult)
	Else
		PendingCurse[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)
		PendingCurseBase[slot] = afBase
		PendingCurseMult[slot] = afMult
		EnsureStatus(slot, akTarget)
	EndIf
EndFunction

Function ClearPendingState(Int aiSlot)
	Int kind = 0
	While kind < 12
		PendingStacks[aiSlot * 12 + kind] = 0
		PendingSet[aiSlot * 12 + kind] = False
		kind += 1
	EndWhile
	PendingAstral[aiSlot] = 0
	PendingAstralWeight[aiSlot] = 0.0
	PendingRadiance[aiSlot] = 0.0
	PendingFrozen[aiSlot] = 0.0
	PendingCatalyze[aiSlot] = 0
	PendingCurse[aiSlot] = 0
	PendingNextEnd[aiSlot] = 0.0
	PendingNextOpen[aiSlot] = 0.0
	PendingAir[aiSlot] = 0
	PendingAirDamage[aiSlot] = 0.0
EndFunction

Function FlushPendingState(Int aiSlot, ESSBStatus akStatus)
	; Claim all pending fields before invoking the new host.
	Int[] amounts = new Int[12]
	Bool[] absolute = new Bool[12]
	Int kind = 1
	While kind <= 11
		amounts[kind] = PendingStacks[aiSlot * 12 + kind]
		absolute[kind] = PendingSet[aiSlot * 12 + kind]
		kind += 1
	EndWhile
	Int stars = PendingAstral[aiSlot]
	Float weight = PendingAstralWeight[aiSlot]
	Float radiance = PendingRadiance[aiSlot]
	Float frozen = PendingFrozen[aiSlot]
	Float catalyst = PendingCatalyze[aiSlot]
	Float catalystMult = PendingCatalyzeMult[aiSlot]
	Float curse = PendingCurse[aiSlot]
	Float curseBase = PendingCurseBase[aiSlot]
	Float curseMult = PendingCurseMult[aiSlot]
	Float nextEnd = PendingNextEnd[aiSlot]
	Float nextOpen = PendingNextOpen[aiSlot]
	Float air = PendingAir[aiSlot]
	Float airDamage = PendingAirDamage[aiSlot]
	ClearPendingState(aiSlot)
	kind = 1
	While kind <= 10
		If absolute[kind]
			akStatus.SetStack(kind, amounts[kind])
		ElseIf amounts[kind] > 0
			akStatus.AddStack(kind, amounts[kind])
		EndIf
		kind += 1
	EndWhile
	If air > 0
		akStatus.SetAirborne(0, airDamage, air)
	EndIf
	If nextEnd > 0.0
		akStatus.SetNextEndMult(nextEnd)
	EndIf
	If nextOpen > 0.0
		akStatus.SetNextOpenMult(nextOpen)
	EndIf
	If stars > 0
		akStatus.AddAstral(stars, weight / stars)
	EndIf
	If radiance > 0.0
		akStatus.DetonateAstralNow(radiance)
	EndIf
	If frozen > 0.0
		akStatus.SetFrozen(0.0, frozen)
	EndIf
	If catalyst > 0
		akStatus.SetCatalyze(0, catalystMult, catalyst)
	EndIf
	If curse > 0
		akStatus.SetDeathCurse(0, curseBase, curseMult, curse)
	EndIf
EndFunction

; Per-slot backups survive a delayed callback after the global migration lock times out.
Function InitBackupInts()
	; Four banks of two slots: 2 * 38 = 76, below Papyrus' 128 limit.
	If BackupIntsA && BackupIntsA.Length == 108
		Int[] oldA = BackupIntsA
		Int[] oldB = BackupIntsB
		BackupIntsA = ESSBState.NewBackup()
		If !BackupIntsA
			BreakState()
			Return
		EndIf
		BackupIntsB = ESSBState.NewBackup()
		If !BackupIntsB
			BreakState()
			Return
		EndIf
		BackupIntsC = ESSBState.NewBackup()
		If !BackupIntsC
			BreakState()
			Return
		EndIf
		BackupIntsD = ESSBState.NewBackup()
		If !BackupIntsD
			BreakState()
			Return
		EndIf
		Int slot = 0
		While slot < 8
			Int[] oldBank = oldA
			If slot >= 4
				oldBank = oldB
			EndIf
			If oldBank
				Int[] oldState = new Int[27]
				Int i = 0
				While i < 27
					oldState[i] = oldBank[(slot % 4) * 27 + i]
					i += 1
				EndWhile
				StoreSwapInts(slot, ESSBState.UpgradeInts(oldState))
			EndIf
			slot += 1
		EndWhile
	EndIf
	If !BackupIntsA
		BackupIntsA = ESSBState.NewBackup()
		If !BackupIntsA
			BreakState()
			Return
		EndIf
	EndIf
	If !BackupIntsB
		BackupIntsB = ESSBState.NewBackup()
		If !BackupIntsB
			BreakState()
			Return
		EndIf
	EndIf
	If !BackupIntsC
		BackupIntsC = ESSBState.NewBackup()
		If !BackupIntsC
			BreakState()
			Return
		EndIf
	EndIf
	If !BackupIntsD
		BackupIntsD = ESSBState.NewBackup()
		If !BackupIntsD
			BreakState()
			Return
		EndIf
	EndIf
EndFunction

Int[] Function SwapIntBank(Int aiSlot)
	If aiSlot < 2
		Return BackupIntsA
	ElseIf aiSlot < 4
		Return BackupIntsB
	ElseIf aiSlot < 6
		Return BackupIntsC
	EndIf
	Return BackupIntsD
EndFunction

Function StoreSwapInts(Int aiSlot, Int[] aiInts)
	Int[] ints = SwapIntBank(aiSlot)
	Int count = ESSBState.IntCount()
	Int index = 0
	While index < count
		ints[(aiSlot % 2) * count + index] = aiInts[index]
		index += 1
	EndWhile
EndFunction

Function SaveSwapData(Int aiSlot, Int[] aiInts, Float[] afFloats)
	StoreSwapInts(aiSlot, ESSBState.UpgradeInts(aiInts))
	Float[] floats = BackupFloatsA
	If aiSlot >= 4
		floats = BackupFloatsB
	EndIf
	Int index = 0
	While index < 24
		floats[(aiSlot % 4) * 24 + index] = afFloats[index]
		index += 1
	EndWhile
	BackupValid[aiSlot] = True
EndFunction

Int[] Function ReadSwapInts(Int aiSlot)
	Int[] source = SwapIntBank(aiSlot)
	Int[] result = ESSBState.NewInts()
	Int index = 0
	While index < result.Length
		result[index] = source[(aiSlot % 2) * result.Length + index]
		index += 1
	EndWhile
	Return result
EndFunction

Float[] Function ReadSwapFloats(Int aiSlot)
	Float[] source = BackupFloatsA
	If aiSlot >= 4
		source = BackupFloatsB
	EndIf
	Float[] result = new Float[24]
	Int index = 0
	While index < 24
		result[index] = source[(aiSlot % 4) * 24 + index]
		index += 1
	EndWhile
	Return result
EndFunction

Float Function TakeNextEndMultOn(Actor akTarget)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return 1.0
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		Return status.TakeNextEndMult()
	EndIf
	Float value = PendingNextEnd[slot]
	PendingNextEnd[slot] = 0.0
	If value <= 0.0
		value = 1.0
	EndIf
	Return value
EndFunction

Float Function TakeNextOpenMultOn(Actor akTarget)
	Int slot = FindSlot(akTarget)
	If slot < 0
		Return 1.0
	EndIf
	ESSBStatus status = RegStatus[slot]
	If status
		Return status.TakeNextOpenMult()
	EndIf
	Float value = PendingNextOpen[slot]
	PendingNextOpen[slot] = 0.0
	If value <= 0.0
		value = 1.0
	EndIf
	Return value
EndFunction

; FIX10: compare with the current alias; never call a native on an orphan alias.
Bool Function IsCurrentController()
	Quest currentQuest = ESSBState.ControllerQuest()
	If !currentQuest
		Return False
	EndIf
	ESSBController current = currentQuest.GetAlias(0) as ESSBController
	Return current == Self
EndFunction

; FIX9: the failure latch is persistent; there is no retry/reset path.
Bool Function IsOperational()
	Return IsCurrentController() && !StateBroken && Ready
EndFunction

Function BreakState()
	If DivineArmed && PlayerRef
		DivineArmed = False
		SetGlobal(GDivineArmed, 0)
		PlayerRef.EndDeferredKill()
	EndIf
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	StateBroken = True
	Ready = False
	UnregisterForUpdate()
	PO3_Events_Alias.UnregisterForWeaponHit(Self)
	If Trees
		Trees.UnregisterForUpdate()
	EndIf
	Debug.MessageBox("元素魔戰士：此存檔含不相容的舊腳本狀態，已停止運作。請退出遊戲，安裝已提升 state_schema_version 並重新建置的完整更新包，再載入此存檔。無需清存檔，技能樹等級、點數與設定保留。")
EndFunction

Bool Function ValidateBindings()
	If !Enabled
		Return False
	EndIf
	If !DebugLevel
		Return False
	EndIf
	If !CurrentElement
		Return False
	EndIf
	If !FormActive
		Return False
	EndIf
	If !Sync
		Return False
	EndIf
	If !SchoolXPMult
		Return False
	EndIf
	If !PoisonDotK
		Return False
	EndIf
	If !BleedDotK
		Return False
	EndIf
	If !BaseDamageMult
		Return False
	EndIf
	If !NodeScale
		Return False
	EndIf
	If !MultDot
		Return False
	EndIf
	If !MultCooldown
		Return False
	EndIf
	If !MultRecovery
		Return False
	EndIf
	If !MultDrain
		Return False
	EndIf
	If !MultDuration
		Return False
	EndIf
	If !MultUpkeep
		Return False
	EndIf
	If !ManabreakBase
		Return False
	EndIf
	If !ManabreakPerRank
		Return False
	EndIf
	If !ManabreakMaxmagPct
		Return False
	EndIf
	If !ManabreakDryPct
		Return False
	EndIf
	If !WaterFlowBasePct
		Return False
	EndIf
	If !WaterFlowPerRankPct
		Return False
	EndIf
	If !WaterWetSlowPct
		Return False
	EndIf
	If !FrostOpenSlowPct
		Return False
	EndIf
	If !SlowCapPct
		Return False
	EndIf
	If !WaterClearStamina
		Return False
	EndIf
	If !WaterOpenStamina
		Return False
	EndIf
	If !ElementDamageMin
		Return False
	EndIf
	If !ElementDamageMax
		Return False
	EndIf
	If !SyncT1
		Return False
	EndIf
	If !SyncT2
		Return False
	EndIf
	If !SyncT3
		Return False
	EndIf
	If !EnvWet
		Return False
	EndIf
	If !EnvStormy
		Return False
	EndIf
	If !EnvNight
		Return False
	EndIf
	If !GameHour
		Return False
	EndIf
	If !SettingsPower
		Return False
	EndIf
	If !FormRulesAbility
		Return False
	EndIf
	If !StatusHostSpell
		Return False
	EndIf
	If !EngagedSpell
		Return False
	EndIf
	If !FormPowers
		Return False
	EndIf
	Int checkFormPowers = 0
	While checkFormPowers < FormPowers.Length
		If !FormPowers[checkFormPowers]
			Return False
		EndIf
		checkFormPowers += 1
	EndWhile
	If !FormAbilities
		Return False
	EndIf
	Int checkFormAbilities = 0
	While checkFormAbilities < FormAbilities.Length
		If !FormAbilities[checkFormAbilities]
			Return False
		EndIf
		checkFormAbilities += 1
	EndWhile
	If !HitNormalSpells
		Return False
	EndIf
	Int checkHitNormalSpells = 0
	While checkHitNormalSpells < HitNormalSpells.Length
		If !HitNormalSpells[checkHitNormalSpells]
			Return False
		EndIf
		checkHitNormalSpells += 1
	EndWhile
	If !HitPowerSpells
		Return False
	EndIf
	Int checkHitPowerSpells = 0
	While checkHitPowerSpells < HitPowerSpells.Length
		If !HitPowerSpells[checkHitPowerSpells]
			Return False
		EndIf
		checkHitPowerSpells += 1
	EndWhile
	If !MarkSpells
		Return False
	EndIf
	Int checkMarkSpells = 0
	While checkMarkSpells < MarkSpells.Length
		If !MarkSpells[checkMarkSpells]
			Return False
		EndIf
		checkMarkSpells += 1
	EndWhile
	If !ReactSpells
		Return False
	EndIf
	Int checkReactSpells = 0
	While checkReactSpells < ReactSpells.Length
		If !ReactSpells[checkReactSpells]
			Return False
		EndIf
		checkReactSpells += 1
	EndWhile
	If !UtilSpells
		Return False
	EndIf
	Int checkUtilSpells = 0
	While checkUtilSpells < UtilSpells.Length
		If !UtilSpells[checkUtilSpells]
			Return False
		EndIf
		checkUtilSpells += 1
	EndWhile
	If !UtilTargetSpells
		Return False
	EndIf
	Int checkUtilTargetSpells = 0
	While checkUtilTargetSpells < UtilTargetSpells.Length
		If !UtilTargetSpells[checkUtilTargetSpells]
			Return False
		EndIf
		checkUtilTargetSpells += 1
	EndWhile
	If !MarkKeywords
		Return False
	EndIf
	Int checkMarkKeywords = 0
	While checkMarkKeywords < MarkKeywords.Length
		If !MarkKeywords[checkMarkKeywords]
			Return False
		EndIf
		checkMarkKeywords += 1
	EndWhile
	If !OverheatSelfSpell
		Return False
	EndIf
	If !TrueSpell
		Return False
	EndIf
	If !ManaBreakSpell
		Return False
	EndIf
	If !SilenceSpell
		Return False
	EndIf
	If !AntiMagicAbility
		Return False
	EndIf
	If !WarmBloodAbility
		Return False
	EndIf
	If !InductionAbility
		Return False
	EndIf
	If !AshSpell
		Return False
	EndIf
	If !InheritSpell
		Return False
	EndIf
	If !WindSpeedAbility
		Return False
	EndIf
	If !WindMuffleAbility
		Return False
	EndIf
	If !SilentAbility
		Return False
	EndIf
	If !FearSpell
		Return False
	EndIf
	If !FrenzySpell
		Return False
	EndIf
	If !ReanimateSpell
		Return False
	EndIf
	If !CleanseSpell
		Return False
	EndIf
	If !PurgeSpell
		Return False
	EndIf
	If !StripSpell
		Return False
	EndIf
	If !PoisonResistAbility
		Return False
	EndIf
	If !SelfCleanseSpells
		Return False
	EndIf
	Int checkSelfCleanseSpells = 0
	While checkSelfCleanseSpells < SelfCleanseSpells.Length
		If !SelfCleanseSpells[checkSelfCleanseSpells]
			Return False
		EndIf
		checkSelfCleanseSpells += 1
	EndWhile
	If !FxExplosions
		Return False
	EndIf
	Int checkFxExplosions = 0
	While checkFxExplosions < FxExplosions.Length
		If !FxExplosions[checkFxExplosions]
			Return False
		EndIf
		checkFxExplosions += 1
	EndWhile
	If !FxSoundFormActive
		Return False
	EndIf
	Int checkFxSoundFormActive = 0
	While checkFxSoundFormActive < FxSoundFormActive.Length
		If !FxSoundFormActive[checkFxSoundFormActive]
			Return False
		EndIf
		checkFxSoundFormActive += 1
	EndWhile
	If !FxSoundRelease
		Return False
	EndIf
	Int checkFxSoundRelease = 0
	While checkFxSoundRelease < FxSoundRelease.Length
		If !FxSoundRelease[checkFxSoundRelease]
			Return False
		EndIf
		checkFxSoundRelease += 1
	EndWhile
	If !FxSoundDrawSheathe
		Return False
	EndIf
	Int checkFxSoundDrawSheathe = 0
	While checkFxSoundDrawSheathe < FxSoundDrawSheathe.Length
		If !FxSoundDrawSheathe[checkFxSoundDrawSheathe]
			Return False
		EndIf
		checkFxSoundDrawSheathe += 1
	EndWhile
	If !FxSoundCharge
		Return False
	EndIf
	Int checkFxSoundCharge = 0
	While checkFxSoundCharge < FxSoundCharge.Length
		If !FxSoundCharge[checkFxSoundCharge]
			Return False
		EndIf
		checkFxSoundCharge += 1
	EndWhile
	If !GWaterMirror
		Return False
	EndIf
	If !GGuardDark
		Return False
	EndIf
	If !GGuardAstral
		Return False
	EndIf
	If !GGuardStar
		Return False
	EndIf
	If !GDomainPoison
		Return False
	EndIf
	If !GDomainWater
		Return False
	EndIf
	If !GDomainDark
		Return False
	EndIf
	If !GDomainAstral
		Return False
	EndIf
	If !GRockArmor
		Return False
	EndIf
	If !GWind
		Return False
	EndIf
	If !GHolyShield
		Return False
	EndIf
	If !GBloodthirst
		Return False
	EndIf
	If !GGuardWind
		Return False
	EndIf
	If !GGuardDivine
		Return False
	EndIf
	If !GDomainEarth
		Return False
	EndIf
	If !GDomainBlood
		Return False
	EndIf
	If !GDomainDivine
		Return False
	EndIf
	If !GNoBloodCost
		Return False
	EndIf
	If !GCloakGuard
		Return False
	EndIf
	If !GSyncStage
		Return False
	EndIf
	If !GResolve
		Return False
	EndIf
	If !GOverheat
		Return False
	EndIf
	If !GCharge
		Return False
	EndIf
	If !GIceShield
		Return False
	EndIf
	If !GMolten
		Return False
	EndIf
	If !GEmber
		Return False
	EndIf
	If !GQuench
		Return False
	EndIf
	If !GPrevElement
		Return False
	EndIf
	If !GTwinElement
		Return False
	EndIf
	If !GDomainFire
		Return False
	EndIf
	If !GDomainFrost
		Return False
	EndIf
	If !GShockRecent
		Return False
	EndIf
	If !GGuardSwitch
		Return False
	EndIf
	If !GGuardBurst
		Return False
	EndIf
	If !GGuardIce
		Return False
	EndIf
	If !GCombo
		Return False
	EndIf
	If !GFreeOpen
		Return False
	EndIf
	If !Trees
		Return False
	EndIf
	If !HitProcPerk
		Return False
	EndIf
	If !ProcVariants
		Return False
	EndIf
	If !ProcElements
		Return False
	EndIf
	If !ProcRatios
		Return False
	EndIf
	If !ProcPowers
		Return False
	EndIf
	If !ProcSneaks
		Return False
	EndIf
	If !ProcBloodBands
		Return False
	EndIf
	If !HitBonusSpells
		Return False
	EndIf
	If !GDivineArmed
		Return False
	EndIf
	If !FormNotify
		Return False
	EndIf
	If !FormSound
		Return False
	EndIf
	If !GuardLayer
		Return False
	EndIf
	If !InputLayer
		Return False
	EndIf
	If ProcVariants.Length != 42 || ProcElements.Length != 42 || ProcRatios.Length != 42 || ProcPowers.Length != 42 || ProcSneaks.Length != 42 || ProcBloodBands.Length != 42 || HitBonusSpells.Length != 11
		Return False
	EndIf
	Int checkProc = 0
	While checkProc < ProcVariants.Length
		If !ProcVariants[checkProc] || ProcElements[checkProc] < 1 || ProcElements[checkProc] > 11 || ProcRatios[checkProc] <= 0.0
			Return False
		EndIf
		checkProc += 1
	EndWhile
	checkProc = 0
	While checkProc < HitBonusSpells.Length
		If !HitBonusSpells[checkProc]
			Return False
		EndIf
		checkProc += 1
	EndWhile
	Return True
EndFunction

Function ReconcileLoadedForm(Actor player)
	; A fresh schema has no combat state. Keep GLOB progression/settings and perks.
	FormActive.SetValueInt(0)
	CurrentElement.SetValueInt(0)
	CachedSync = 0
	Sync.SetValueInt(0)
	GWaterMirror.SetValueInt(0)
	GGuardDark.SetValueInt(0)
	GGuardAstral.SetValueInt(0)
	GGuardStar.SetValueInt(0)
	GDomainPoison.SetValueInt(0)
	GDomainWater.SetValueInt(0)
	GDomainDark.SetValueInt(0)
	GDomainAstral.SetValueInt(0)
	GRockArmor.SetValueInt(0)
	GWind.SetValueInt(0)
	GHolyShield.SetValueInt(0)
	GBloodthirst.SetValueInt(0)
	GGuardWind.SetValueInt(0)
	GGuardDivine.SetValueInt(0)
	GDomainEarth.SetValueInt(0)
	GDomainBlood.SetValueInt(0)
	GDomainDivine.SetValueInt(0)
	GNoBloodCost.SetValueInt(0)
	GCloakGuard.SetValueInt(0)
	GSyncStage.SetValueInt(0)
	GResolve.SetValueInt(0)
	GOverheat.SetValueInt(0)
	GCharge.SetValueInt(0)
	GIceShield.SetValueInt(0)
	GMolten.SetValueInt(0)
	GEmber.SetValueInt(0)
	GQuench.SetValueInt(0)
	GPrevElement.SetValueInt(0)
	GTwinElement.SetValueInt(0)
	GDomainFire.SetValueInt(0)
	GDomainFrost.SetValueInt(0)
	GShockRecent.SetValueInt(0)
	GGuardSwitch.SetValueInt(0)
	GGuardBurst.SetValueInt(0)
	GGuardIce.SetValueInt(0)
	GCombo.SetValueInt(0)
	GFreeOpen.SetValueInt(0)
	Int i = 0
	While i < FormAbilities.Length
		player.RemoveSpell(FormAbilities[i])
		i += 1
	EndWhile
	; Recreate the AME too: its saved Controller property belongs to the old quest.
	player.RemoveSpell(FormRulesAbility)
	player.DispelSpell(UtilSpells[18])
	SendModEvent("ESSB_FormChanged", "close", 0.0)
EndFunction

; FIX12: refreshed at init/load, every form/tree change, and MCM close.
Function RefreshRuntimeValues()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	CachedDebugLevel = DebugLevel.GetValueInt()
	CachedNodeScale = NodeScale.GetValue()
	CachedDuration = MultDuration.GetValue()
	CachedT1 = SyncT1.GetValueInt()
	CachedT2 = SyncT2.GetValueInt()
	CachedT3 = SyncT3.GetValueInt()
	CachedSync = Sync.GetValueInt()
	RuntimeCacheReady = True
	RefreshSyncStage()
	RefreshProcMagnitudes()
EndFunction

Event OnMenuClose(String asMenuName)
	If !IsOperational() || asMenuName != "Journal Menu"
		Return
	EndIf
	RefreshRuntimeValues()
	RefreshTrees()
	RefreshAbilities()
EndEvent

; Short combat clocks restart on load; skill globals/perks/points are never written.
Function ResetLoadClock()
	ClearGuardWindows()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	InitRegistry()
	ChargeDecayAt = now
	StormCharge = 0.0
	SwitchCharge = 0
	SetGlobal(GBloodthirst, 0)
	SetGlobal(GCloakGuard, 0)
	SetGlobal(GEmber, 0)
	SetGlobal(GGuardAstral, 0)
	SetGlobal(GGuardBurst, 0)
	SetGlobal(GGuardDark, 0)
	SetGlobal(GGuardDivine, 0)
	SetGlobal(GGuardIce, 0)
	SetGlobal(GGuardStar, 0)
	SetGlobal(GGuardSwitch, 0)
	SetGlobal(GGuardWind, 0)
	SetGlobal(GMolten, 0)
	SetGlobal(GNoBloodCost, 0)
	SetGlobal(GQuench, 0)
	SetGlobal(GShockRecent, 0)
	If KillStreakReady || KeepSneakLeft > 0
		PO3_SKSEFunctions.ResetActorDetection(ThePlayer())
	EndIf
	KillStreakReady = False
	SetGlobal(GDomainFire, 0)
	SetGlobal(GDomainFrost, 0)
	SetGlobal(GDomainEarth, 0)
	SetGlobal(GDomainBlood, 0)
	SetGlobal(GDomainDivine, 0)
	SetGlobal(GDomainPoison, 0)
	SetGlobal(GDomainWater, 0)
	SetGlobal(GDomainDark, 0)
	SetGlobal(GDomainAstral, 0)
	MoltenLeft = 0.0
	EmberLeft = 0.0
	QuenchLeft = 0.0
	ShockLeft = 0.0
	GuardSwitchLeft = 0.0
	GuardBurstLeft = 0.0
	GuardIceLeft = 0.0
	ThunderLeft = 0.0
	DoubleBurstLeft = 0.0
	SyncKeepLeft = 0.0
	AvatarLeft = 0.0
	BloodthirstLeft = 0.0
	GuardWindLeft = 0.0
	GuardDivineLeft = 0.0
	CloakGuardLeft = 0.0
	NoBloodCostLeft = 0.0
	WindFollowLeft = 0.0
	RiposteLeft = 0.0
	KeepSneakLeft = 0.0
	EndBoostLeft = 0.0
	GuardDarkLeft = 0.0
	GuardAstralLeft = 0.0
	GuardStarLeft = 0.0
	Int timerIndex = 0
	While timerIndex < 12
		OpenBoost[timerIndex] = 0.0
		EndBoost[timerIndex] = 0.0
		timerIndex += 1
	EndWhile
	timerIndex = 0
	While timerIndex < 3
		DomainLeft[timerIndex] = 0.0
		ClearDomainResidents(timerIndex)
		timerIndex += 1
	EndWhile
	SelfLastHit = now
	ResolveTime = now
	ComboTime = now
	FormOpenTime = now
	TwinTime = now
	LastEnvCheck = 0.0
	InterruptTime = -1000000.0
	IceHeartTime = -1000000.0
	RetaliateTime = -1000000.0
	SanctuaryTime = -1000000.0
	CleanseTime = -1000000.0
	TrioTime = now
	TrioMask = 0
	FxBudgetTime = now
	FxBudget = 0
	LogWindowStart = now
	LogLastTime = -1000000.0
	LogCount = 0
	LogDropped = 0
	LogLastKey = ""
	InitRegistry()
	If StateBroken
		Return
	EndIf
	If !SwapFloats || SwapFloats.Length != 128
		SwapFloats = new Float[128]
		If !SwapFloats
			BreakState()
			Return
		EndIf
	EndIf
	Int damageIndex = 0
	While damageIndex < 128
		DamageActor[damageIndex] = None
		DamageElement[damageIndex] = 0
		SwapFloats[damageIndex] = -1.0
		damageIndex += 1
	EndWhile
	LiftQueued = False
	Int i = 0
	While i < 8
		If PendingAir[i] > 0
			PendingAir[i] = now + 1.0
		EndIf
		If PendingCurse[i] > 0
			PendingCurse[i] = now + 1.0
		EndIf
		If PendingCatalyze[i] > 0
			PendingCatalyze[i] = now + 1.0
		EndIf
		If RegPendStarLock[i] > 0
			RegPendStarLock[i] = now + 1.0
		EndIf
		If PendingFrozen[i] > 0
			PendingFrozen[i] = now + 1.0
		EndIf
		HitActor[i] = None
		CastActor[i] = None
		KillProcActor[i] = None
		DeadActor[i] = None
		RegLastDamage[i] = 0
		RegLastOpen[i] = -1000000.0
		RegLastEnd[i] = -1000000.0
		RegUntil[i] = now + 1.0
		RegSecondUntil[i] = now + 1.0
		RegHostRequest[i] = now - 3.0
		KnockTime[i] = -1000000.0
		PullTime[i] = -1000000.0
		WashTime[i] = -1000000.0
		LiftActor[i] = None
		If RegStatus[i]
			RegStatus[i].ResetLoadClock()
		EndIf
		i += 1
	EndWhile
	CancelSwap()
	i = 0
	While i < PendingServantDue.Length
		PendingServantDue[i] = now + 5.0
		i += 1
	EndWhile
	i = 0
	While i < TrioTimes.Length
		TrioTimes[i] = -1000000.0
		i += 1
	EndWhile
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function InitRegistryInternal()
	If StateBroken || RegistryInitialised
		Return
	EndIf
	InitRegistry()
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function InitFixStateInternal()
	If StateBroken || FixInitialised
		Return
	EndIf
	InitFixState()
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function ArmUpdateInternal()
	If StateBroken
		Return
	EndIf
	InitFixStateInternal()
	If StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Float due = NextTickAt
	Int index = 0
	While LiftQueued && index < 8
		If LiftActor[index] && LiftDue[index] < due
			due = LiftDue[index]
		EndIf
		index += 1
	EndWhile
	Float delay = due - now
	If delay < 0.01
		delay = 0.01
	EndIf
	RegisterForSingleUpdate(delay)
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function ScheduleTickInternal(Float afDelay)
	If StateBroken
		Return
	EndIf
	Float requested = Utility.GetCurrentRealTime() + afDelay
	If NextTickAt <= 0.0 || requested < NextTickAt
		NextTickAt = requested
	EndIf
	ArmUpdateInternal()
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Int Function FindSlotInternal(Actor akTarget)
	InitRegistryInternal()
	If StateBroken
		Return -1
	EndIf
	Int index = 0
	While index < 8
		If RegActor[index] == akTarget
			Return index
		EndIf
		index += 1
	EndWhile
	Return -1
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Bool Function WillOpenInternal(Actor akTarget, Int aiElement, Int aiSlot = -1)
	InitRegistryInternal()
	If StateBroken
		Return False
	EndIf
	Int slot = aiSlot
	If slot < 0
		Return True
	EndIf
	Return RegElem[slot] != aiElement && !(RegElem2[slot] == aiElement && RegSecondReal[slot])
EndFunction

; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function OnValidHitInternal(Actor akTarget, Int aiElement, Bool abPower, Int aiSlot = -1, Int aiGeneration = -1)
	InitRegistryInternal()
	If StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	SelfLastHit = Utility.GetCurrentRealTime()
	MarkEngaged(akTarget)
	Int slot = aiSlot
	If slot < 0
		slot = AcquireSlot(akTarget)
	ElseIf RegActor[slot] != akTarget || RegGeneration[slot] != aiGeneration
		slot = AcquireSlot(akTarget)
	EndIf
	If slot < 0
		Return
	EndIf
	EnsureStatus(slot, akTarget)
	If RegElem[slot] == aiElement || (RegElem2[slot] == aiElement && RegSecondReal[slot])
		ApplyMark(akTarget, aiElement, slot)
		HitStacks(akTarget, aiElement, abPower)
	Else
		InstallMark(slot, aiElement, akTarget)
	EndIf
	; 5.3 持續專精主線：帶熱度目標火抗 -1%／點。
	If aiElement == 1
		ESSBElem.ApplyFireResistShred(Self, akTarget)
	EndIf
	ElementHitHook(akTarget, aiElement, abPower)
	AddSync(1)
	If Trees
		; 規劃 4：開形態的有效命中給當前元素樹 + 通用樹。
		Trees.AwardInternal(aiElement)
	EndIf
	If True
		ScheduleTickInternal(1.0)
	EndIf
EndFunction

; Same L1 output as ESSBLog, using the init/load/MCM cache; intentionally unthrottled.
Function LogEvent(Int aiLevel, String asMechanism, String asMessage)
	If CachedDebugLevel >= aiLevel
		Debug.Trace("[ESSB][" + asMechanism + "][L" + aiLevel + "] " + asMessage)
	EndIf
EndFunction

Int Function TakeSwitchCharge()
	Int value = SwitchCharge
	SwitchCharge = 0
	Return value
EndFunction

Function SettleDeadCurse(Int aiSlot)
	If RegStatus[aiSlot]
		RegStatus[aiSlot].ResolveDeathCurse(True)
	EndIf
	If PendingCurse[aiSlot] > 0
		Float amount = PendingCurseBase[aiSlot] * PendingCurseMult[aiSlot]
		PendingCurse[aiSlot] = 0
		ESSBElem3.AfterDeathCurse(Self, RegActor[aiSlot], amount)
		If CachedDebugLevel >= 1
			LogEvent(1, "deathcurse", "settled pending on death")
		EndIf
	EndIf
EndFunction

Function SettleSneakKill(Actor akVictim, Int aiElement)
	Int i = 0
	While i < 8
		If HitActor[i] == akVictim && !HitKillDone[i] && HitSneak[i] && HitForm[i] == 5
			HitKillDone[i] = True
			ESSBElem2.TryKillStreak(Self, HitForm[i], HitSneak[i])
			Return
		EndIf
		i += 1
	EndWhile
EndFunction

Function RememberCast(Actor akTarget)
	If !akTarget
		Return
	EndIf
	Int i = 0
	While i < 8 && CastActor[i] != akTarget
		i += 1
	EndWhile
	If i == 8
		i = CastNext
		CastNext = (CastNext + 1) % 8
	EndIf
	CastActor[i] = akTarget
	CastAt[i] = Utility.GetCurrentRealTime()
EndFunction

Bool Function RecentCast(Actor akTarget)
	Int i = 0
	Float now = Utility.GetCurrentRealTime()
	While i < 8
		If CastActor[i] == akTarget
			Return now >= CastAt[i] && now - CastAt[i] <= 1.5
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function ArmKillProc(Actor akTarget, Int aiKind, Float afAmount, Float afPredicted = -1.0)
	If !akTarget || akTarget.IsDead()
		Return
	EndIf
	Int i = 0
	While i < 8 && KillProcActor[i] != akTarget
		i += 1
	EndWhile
	If i == 8
		i = KillProcNext
		KillProcNext = (KillProcNext + 1) % 8
	EndIf
	KillProcActor[i] = akTarget
	KillProcKind[i] = aiKind
	KillProcAmount[i] = afAmount
	Float beforeHealth = akTarget.GetActorValue("Health")
	If afPredicted < 0.0
		afPredicted = afAmount
	EndIf
	If beforeHealth > 0.0 && afPredicted >= beforeHealth
		KillProcUntil[i] = -1.0
	Else
		KillProcActor[i] = None
		KillProcUntil[i] = 0.0
	EndIf
EndFunction

Function SettleKillProc(Actor akTarget)
	Int i = 0
	Float now = Utility.GetCurrentRealTime()
	While i < 8
		If KillProcActor[i] == akTarget
			Int kind = KillProcKind[i]
			Float amount = KillProcAmount[i]
			Float due = KillProcUntil[i]
			KillProcActor[i] = None
			If due == -1.0
				If kind == 1
					ESSBElem.OnCremation(Self, akTarget, amount)
				ElseIf kind == 10
					ESSBElem3.OnDeathSoul(Self, akTarget)
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

; Native deferred kill holds the death transition BEFORE lethal damage, including DOT.
; It is paired only when owned by this instance. Existing tick/OnHit service the latch.
Function RefreshDivineProtection()
	If !IsCurrentController()
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	If DivineArmed && player.GetActorValue("Health") <= 0.0
		DivineSaveUsed = True
		DivineArmed = False
		SetGlobal(GDivineArmed, 0)
		; Restore exactly one actual health point, bypass recovery multipliers.
		SetGuardDivine(2)
		ApplyCleanse(True)
		player.RestoreActorValue("Health", 1.0 - player.GetActorValue("Health"))
		player.EndDeferredKill()
		Return
	EndIf
	Bool eligible = Enabled.GetValueInt() == 1 && FormActive.GetValueInt() == 1 && !DivineSaveUsed && SyncStage() >= 3 && ESSBNodes.Br(Self, 6, 0, 4, 0)
	If eligible && !DivineArmed
		player.StartDeferredKill()
		DivineArmed = True
		SetGlobal(GDivineArmed, 1)
	ElseIf !eligible && DivineArmed
		DivineArmed = False
		SetGlobal(GDivineArmed, 0)
		player.EndDeferredKill()
	EndIf
EndFunction

Function CaptureStatusDeath(Actor akTarget)
	Int slot = FindSlot(akTarget)
	If slot >= 0
		CaptureDeath(slot)
	EndIf
EndFunction

Int Function SecondsLeft(Float afDeadline)
	If afDeadline <= 0.0
		Return 0
	EndIf
	Float remaining = afDeadline - Utility.GetCurrentRealTime()
	If remaining <= 0.0
		Return 0
	EndIf
	Return Math.Ceiling(remaining) as Int
EndFunction

Bool Function InsideDomainSlot(Actor akTarget, Int aiSlot)
	If !akTarget
		Return False
	EndIf
	Float dx = akTarget.GetPositionX() - DomainX[aiSlot]
	Float dy = akTarget.GetPositionY() - DomainY[aiSlot]
	Float dz = akTarget.GetPositionZ() - DomainZ[aiSlot]
	Return dx * dx + dy * dy + dz * dz <= DomainR[aiSlot] * DomainR[aiSlot]
EndFunction

; Explicit maintenance release: disabling prevents tick/combat/setup from rearming.
Function ReleaseDivineProtection()
	If !IsCurrentController()
		Return
	EndIf
	Enabled.SetValueInt(0)
	ClearGuardWindows()
	DivineArmed = False
	SetGlobal(GDivineArmed, 0)
	DivineSaveUsed = True
	Actor player = ThePlayer()
	If player
		player.EndDeferredKill()
	EndIf
EndFunction

; Six residents/domain: the existing nearest-five selection plus the player.
; First observed inside is a conservative entry time; no retroactive award to newcomers.
Function ClearDomainResidents(Int aiSlot)
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		DomainResident[i] = None
		DomainResidentAt[i] = 0.0
		i += 1
	EndWhile
EndFunction

Function ObserveDomainResidents(Int aiSlot, Actor[] akNearby, Actor akPlayer, Float afNow)
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		Actor resident = DomainResident[i]
		Bool present = resident && resident == akPlayer && InsideDomainSlot(akPlayer, aiSlot)
		Int n = 0
		While resident && !present && n < akNearby.Length
			present = akNearby[n] == resident
			n += 1
		EndWhile
		If !present
			DomainResident[i] = None
			DomainResidentAt[i] = 0.0
		EndIf
		i += 1
	EndWhile
	If InsideDomainSlot(akPlayer, aiSlot)
		RememberDomainResident(akPlayer, aiSlot, afNow)
	EndIf
	i = 0
	While i < akNearby.Length
		RememberDomainResident(akNearby[i], aiSlot, afNow)
		i += 1
	EndWhile
EndFunction

Function RememberDomainResident(Actor akTarget, Int aiSlot, Float afNow)
	If !akTarget
		Return
	EndIf
	Int i = aiSlot * 6
	Int empty = -1
	While i < aiSlot * 6 + 6
		If DomainResident[i] == akTarget
			Return
		ElseIf !DomainResident[i]
			empty = i
		EndIf
		i += 1
	EndWhile
	If empty >= 0
		DomainResident[empty] = akTarget
		DomainResidentAt[empty] = afNow
	EndIf
EndFunction

Int Function DomainTargetTicks(Actor akTarget, Int aiSlot, Float afStop)
	If !akTarget
		Return 0
	EndIf
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		If DomainResident[i] == akTarget
			Int ticks = (afStop - DomainResidentAt[i]) as Int
			If ticks > 0
				DomainResidentAt[i] = DomainResidentAt[i] + ticks
				Return ticks
			EndIf
			Return 0
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction

; PERK reads native active-effect lifetime. A stale mirror alone grants no protection.
Function ApplyGuardWindow(Int aiIndex, Float afDeadline)
	Actor player = ThePlayer()
	Spell window = ESSBState.GuardWindowSpell(aiIndex)
	If !player || !window
		Return
	EndIf
	player.DispelSpell(window)
	Int seconds = SecondsLeft(afDeadline)
	If seconds > 0
		window.SetNthEffectDuration(0, seconds)
		player.DoCombatSpellApply(window, player)
	EndIf
EndFunction

Function ClearGuardWindows()
	Int i = 0
	While i < 9
		ApplyGuardWindow(i, 0.0)
		i += 1
	EndWhile
EndFunction

Int Function SyncStage()
	If !SyncCacheReady
		Return ComputeSyncStage()
	EndIf
	Return CachedSyncStage
EndFunction

Function RefreshSyncStage()
	CachedSyncStage = ComputeSyncStage()
	SyncCacheReady = True
EndFunction

Float Function PlayerElementMult(Int aiElement)
	Int tree = aiElement - 1
	Float mult = 1.0
	If aiElement != 9
		mult += ESSBNodes.Pct(Self, Rank(tree, 0, 1), 0.01)
		mult += ESSBNodes.Pct(Self, Rank(tree, 0, 3), 0.01) * SyncStage()
	EndIf
	If aiElement != 5 && GetOpenBoost(aiElement) > 0
		mult += ESSBNodes.Pct(Self, Rank(tree, 1, 1), 0.01)
	EndIf
	If aiElement == 1
		If SelfOverheat > 0
			If Br(0, 0, 4, 1)
				mult += 0.8
			Else
				mult += 0.5
			EndIf
		EndIf
		If GetMoltenLeft() > 0
			mult += 1.0
		EndIf
	EndIf
	Return mult
EndFunction

Float Function PlayerProcBase(Int aiElement, Bool abPower)
	Float b = (ElementDamageMin[aiElement - 1] + ElementDamageMax[aiElement - 1]) * 0.5
	If aiElement == 3
		b = 13.0
	EndIf
	If abPower
		b *= 1.5
	EndIf
	Float common = 1.0
	If BloodthirstLeft > Utility.GetCurrentRealTime()
		common *= 1.2
	EndIf
	If (aiElement == 7 && EnvNight.GetValueInt() == 0) || (aiElement == 10 && EnvNight.GetValueInt() == 1)
		common *= 1.2
	EndIf
	If EndBoostLeft > Utility.GetCurrentRealTime()
		common *= 1.0 + EndBoostAmount
	EndIf
	Return b * BaseDamageMult.GetValue() * GLevel(aiElement - 1) * common * ESSBNodes.CommonHitMult(Self, aiElement, abPower) * PlayerElementMult(aiElement)
EndFunction

Float Function BloodBandMult(Int aiBand)
	Int band = aiBand
	If Br(5, 0, 2, 0)
		band = 3 - band
	EndIf
	If band == 0
		Return 1.25
	ElseIf band == 1
		Return 1.1
	ElseIf band == 2
		Return 0.85
	EndIf
	Return 0.6
EndFunction

Function RefreshProcMagnitudes()
	If StateBroken || !NodeMirrorReady || !ProcVariants
		Return
	EndIf
	InitProcCache()
	If StateBroken
		Return
	EndIf
	Int i = 0
	While i < ProcVariants.Length
		Int e = ProcElements[i]
		Float value = PlayerProcBase(e, ProcPowers[i] == 1) * ProcRatios[i]
		If ProcSneaks[i] == 1
			value *= ESSBElem2.SneakMult(Self)
		EndIf
		If e == 6
			value *= BloodBandMult(ProcBloodBands[i])
		EndIf
		If value != ProcWritten[i]
			ProcVariants[i].SetNthEffectMagnitude(0, value)
			ProcWritten[i] = value
			If e == 6
				ProcVariants[i].SetNthEffectMagnitude(1, value * 0.15)
			EndIf
		EndIf
		If e == 3
			Float drain = DrainAmount(value * 0.5)
			If drain != DrainWritten[i]
				ProcVariants[i].SetNthEffectMagnitude(1, drain)
				DrainWritten[i] = drain
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Bool Function TargetProcPossible(Int aiElement, Bool abPower, Bool abSneak, Bool abOpening)
	; Innate heat and holy vulnerability exist even with zero purchased nodes.
	If aiElement == 1 || aiElement == 7
		Return True
	EndIf
	If Br(4, 0, 4, 0) || Br(4, 2, 4, 0) || Rank(9, 0, 2) > 0 || Br(10, 1, 3, 0) || Br(10, 2, 4, 0)
		Return True
	EndIf
	If abOpening && (Br(12, 1, 3, 0) || Br(aiElement - 1, 1, 1, 0))
		Return True
	EndIf
	If aiElement == 2
		Return Rank(1, 0, 2) > 0
	ElseIf aiElement == 3
		Return Br(2, 1, 3, 2)
	ElseIf aiElement == 5
		Return abSneak && Br(4, 2, 4, 1)
	ElseIf aiElement == 9
		Return Br(8, 0, 1, 0)
	ElseIf aiElement == 10
		Return Br(9, 0, 3, 0)
	ElseIf aiElement == 11
		Return abPower && Br(10, 0, 2, 0)
	EndIf
	Return False
EndFunction

Function ApplyBakedProc(Actor akTarget, Int aiElement, Bool abPower, Bool abSneak)
	If !akTarget || akTarget.IsDead() || !ProcCacheReady
		Return
	EndIf
	Int wantedBand = 0
	If aiElement == 6
		wantedBand = BloodBand(ThePlayer().GetActorValuePercentage("Health"))
	EndIf
	Int i = 0
	While i < ProcVariants.Length
		If ProcElements[i] == aiElement && ProcPowers[i] == (abPower as Int) && ProcBloodBands[i] == wantedBand
			If aiElement != 5 || ProcSneaks[i] == (abSneak as Int)
				ApplyTrackedDamage(ThePlayer(), ProcVariants[i], akTarget, aiElement)
				Return
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Int Function BloodBand(Float percent)
	If percent >= 0.85
		Return 0
	ElseIf percent >= 0.5
		Return 1
	ElseIf percent >= 0.2
		Return 2
	EndIf
	Return 3
EndFunction

Function OnLethalHitWhileArmed()
	If IsOperational() && DivineArmed
		RefreshDivineProtection()
	EndIf
EndFunction

Function InitProcCache()
	If StateBroken
		Return
	EndIf
	If !ProcCacheReady
		ProcWritten = new Float[64]
		DrainWritten = new Float[64]
		If !ProcWritten || !DrainWritten
			BreakState()
			Return
		EndIf
		Int j = 0
		While j < 64
			ProcWritten[j] = -1.0
			DrainWritten[j] = -1.0
			j += 1
		EndWhile
		ProcCacheReady = True
	EndIf
EndFunction
