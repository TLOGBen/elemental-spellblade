Scriptname ESSBController extends ReferenceAlias
{元素魔戰士 控制器：形態層、同調、融斷、環境、自身資源與反應本體的事件入口
（規劃 v0.4 第 1、1.1、2.1～2.10、2.13、6.1 節）。

形態切換在同一個腳本幀內完成：移除舊形態能力、加上新形態能力、更新全域變數。
沒有 Utility.Wait、沒有忙等迴圈、沒有每幀輪詢。附傷與所有反應傷害都用
DoCombatSpellApply 套自有法術，不用 Spell.Cast，避免觸發施法事件被其他模組吃掉；
絕不直接 DamageActorValue 生命，讓 Ordinator 等天賦照常成立。

Round 22（N3）起沒有登記表、沒有狀態容器：目標身上的印記、層數、冰封、催毒、死咒、星痕，與你身上的熱度、
聖佑階梯，都是 DLL 掛的引擎效果（native/include/Status.h）。DLL 在命中那一幀決定開印／刷新／被切，做完開印與
終焉的狀態部分，再用 ModEvent（ESSB_Open、ESSB_End、ESSB_Frozen、ESSB_Hallucinate、ESSB_Judgment、ESSB_Splash、
ESSB_Shatter、ESSB_Landing、ESSB_Death）叫這裡的處理函式跑反應本體（ESSBReactions，N5 前在 Papyrus）。
本腳本讀寫目標狀態一律經 ESSBNative（狀態代碼見 ESSBNative.psc）。

自身資源 aiKind（N4 前留在這裡）：1 電荷 2 岩甲 3 風勢
輔助法術 UtilSpells 索引：
  0 減速 1 減防 2 削魔 3 削耐 4 回血 5 回魔 6 回耐 7 放血（無抗性）}

GlobalVariable Property Enabled Auto
GlobalVariable Property DebugLevel Auto
GlobalVariable Property CurrentElement Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property Sync Auto
GlobalVariable Property SchoolXPMult Auto
; ESSB_NativeHit (DLL status, 1 = native base proc running). Read as a GLOB, never by calling into the DLL,
; so a missing DLL cannot cause unbound-native errors on the hit path.
GlobalVariable Property NativeHit Auto
; ESSB_NativeWanted (MCM preference for the DLL). Read once per load for the not-running notice.
GlobalVariable Property NativeWanted Auto
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
Spell Property EngagedSpell Auto
Spell[] Property FormPowers Auto
Spell[] Property FormAbilities Auto
Spell[] Property HitNormalSpells Auto
Spell[] Property HitPowerSpells Auto
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
Spell Property BloodGuardSpell Auto
{護血池：DLL 以強度＝池量灌入（血溢），離開形態時這裡清空。}
Spell Property EchoPendingSpell Auto
{餘響待發：切換時套上，DLL 在切換後第一擊結算前一元素附傷並移除它。}
Spell Property TwinWindowSpell Auto
{雙生視窗：切換時套上 30 秒，DLL 讀它決定左手命中是否另帶前一元素。}
Spell Property RiposteWindowSpell Auto
{反擊視窗（round 21）：格擋成功後套上 3 秒，DLL 讀它讓下一次無形態命中的吸魔 ×2 並移除它。}
Spell Property IceArmorAbility Auto
{冰甲（round 21）：冰形態的 3 公尺寒氣披風，只對敵對者減速 20%。}
Spell Property IceArmorWideAbility Auto
{冰甲＋霜膚（round 21）：寒氣半徑 5 公尺、減速 30%。}
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
Spell Property FrenzyBladeSpell Auto
{round 22「狂刃」：瘋狂中的目標傷害 +50%（ESSB_N3_FrenzyBlade，AttackDamageMult +0.5，跟瘋狂同秒數）。}
Spell Property VisionSpell Auto
{v0.4 5.12「幻視」：不能魅惑的目標 3 秒攻擊傷害 ×0.8（ESSB_N3_Vision，AttackDamageMult -0.2）。}
Spell Property ReanimateSpell Auto
{亡者歸來（原型 22 Reanimate，magnitude＝等級上限、duration 依階數）。}
Spell Property CleanseSpell Auto
{洗淨：限定關鍵字的 Dispel（中毒、元素持續傷、減速）＋ Cure Disease。}
Spell Property PurgeSpell Auto
{淨化／洗滌：關鍵字範圍更大的 Dispel ＋ Cure Disease ＋ Cure Poison。}
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
Int[] SettledElement
Actor[] SettledDead
Int SettledNext
Actor[] DeadActor
Int[] DeadElement
Int[] DeadFreeze
Int[] DeadBleed
Int DeadNext
Float[] TrioTimes
Int PerpetualKeep
Actor[] PendingServants
Float[] PendingServantDue
Bool ReanimateBusy


; 擊殺掛勾（round 22）：DLL 的死亡快照（ESSB_Death，屍體還帶著效果時送出）與 PO3 的擊殺回報誰先到都行；
; 回報了擊殺、快照卻沒來（目標身上沒有任何狀態）時，每秒 tick 在 1 秒後以空快照結算。
Int[] DeadMarks
Actor[] PendingKillActor
Float[] PendingKillAt
Int PendingKillNext
; FIX14: damage timestamps parallel to DamageActor[128].
Float[] DamageTime
; 融斷當下的電荷：ESSB_End 在融斷之後才回來，那時自身資源已清空（見 EndCharge）。
Int BurstCharge
Bool PlayerInFireDomain


; FIX15: target-owned facts and once-only death payloads.
Actor[] HitActor
Int[] HitForm
Bool[] HitSneak
Bool[] HitPower
Int[] HitWeapon
Bool[] HitKillDone
Int HitNext
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
Bool TablesInitialised
Bool FirstSetupDone

; ---------------------------------------------------------------- 節點狀態（機制前線）

; 無元素樹
Int Resolve
Float ResolveTime
Int ComboHits
Float ComboTime
Float InterruptTime

; 秒計時器（每秒 tick 減 1，歸零時把對應的全域變數寫回 0）
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
Int PrevElement
Int TwinElement
Float TwinTime
Float IceHeartTime

; ---- 機制前線 round 2 的狀態
Int HolyShield
Float BloodthirstLeft
Float GuardWindLeft
Float GuardDivineLeft
Float CloakGuardLeft
Float NoBloodCostLeft
Float WindFollowLeft
Float KeepSneakLeft
Bool DivineSaveUsed
; FIX10: provenance belongs to the victim, never to the active form.
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
Float CleanseTime
Int AstralHits

; ---- 特效前線的狀態：爆炸預算（規劃 2.12「範圍事件最多播 5 個目標的特效」）
Int FxBudget
Float FxBudgetTime

; 切換／終焉的一次性旗標
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
	; Allocate once on this schema; failure latches and never retries.
	If !DamageTime
		DamageTime = new Float[128]
		If !DamageTime
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
	If !DeadMarks
		DeadMarks = new Int[8]
		If !DeadMarks
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
	If !PendingKillActor
		PendingKillActor = new Actor[4]
		If !PendingKillActor
			BreakState()
			Return
		EndIf
	EndIf
	If !PendingKillAt
		PendingKillAt = new Float[4]
		If !PendingKillAt
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

; 推力冷卻環與三格領域（round 22 起沒有目標登記表）。
Function InitTables()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If TablesInitialised
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	; Allocate once on this schema; failure latches and never retries.
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
		If !DomainResident
			BreakState()
			Return
		EndIf
	EndIf
	If !DomainResidentAt
		DomainResidentAt = new Float[18]
		If !DomainResidentAt
			BreakState()
			Return
		EndIf
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
	TablesInitialised = True
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
	InitTables()
	If !IsCurrentController() || StateBroken
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
	; A DLL that is missing or refuses to start (game/SKSE version, Address Library) cannot show anything
	; itself, so the script says so once per load. A running DLL reports its own faults and the MCM switch.
	If Enabled.GetValueInt() == 1 && NativeWanted.GetValueInt() == 1 && NativeHit.GetValueInt() != 1
		Debug.Notification("元素魔戰士：DLL 命中附傷未運作（未安裝、遊戲／SKSE 版本或 Address Library 不符，或已故障）")
	EndIf
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
	If StateBroken
		Return
	EndIf
	Ready = True
	If InputLayer
		InputLayer.Setup()
	EndIf
	PO3_Events_Alias.RegisterForWeaponHit(Self)
	; DLL → 反應本體（round 22）。ModEvent 的登記不隨存檔保存，每次載入由這裡重登。
	RegisterForModEvent("ESSB_Open", "OnESSBOpen")
	RegisterForModEvent("ESSB_End", "OnESSBEnd")
	RegisterForModEvent("ESSB_Frozen", "OnESSBFrozen")
	RegisterForModEvent("ESSB_Hallucinate", "OnESSBHallucinate")
	RegisterForModEvent("ESSB_Judgment", "OnESSBJudgment")
	RegisterForModEvent("ESSB_Splash", "OnESSBSplash")
	RegisterForModEvent("ESSB_Shatter", "OnESSBShatter")
	RegisterForModEvent("ESSB_Landing", "OnESSBLanding")
	RegisterForModEvent("ESSB_Death", "OnESSBDeath")
	RegisterForModEvent("ESSB_Rise", "OnESSBRise")
	SendModEvent("ESSB_FormRulesReady")
	If CachedDebugLevel >= 1
		LogEvent(1, "init", "ready enabled=" + Enabled.GetValueInt() + " element=" + CurrentElement.GetValueInt() \
			+ " active=" + FormActive.GetValueInt() + " native=" + NativeHit.GetValueInt())
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
	If ESSBNodes.Br(Self, 12, 1, 1, 0) ; @node 順轉
		SetGuardSwitch(1)
	EndIf
	SendModEvent("ESSB_FormChanged", "open", aiIndex as Float)
	If CachedDebugLevel >= 1
		LogEvent(1, "form", "switch " + previous + " -> " + aiIndex + " syncKeep=" + keep)
	EndIf
	If previous >= 1 && previous != aiIndex
		OnFormSwitched(previous, aiIndex)
	EndIf
	OnFormOpened(aiIndex)
	ScheduleTick(1.0)
EndFunction

Function CloseForm()
	; 關閉形態是選單也會要求的動作（洗點前先關形態），總開關關著也要能關；DLL 那一半（融斷、洩壓）在總開關關著時本來就不做。
	If !IsReadyUI()
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
	; 關形態不是切換：沒有餘響；護血池隨形態清空。
	If player
		If EchoPendingSpell
			player.DispelSpell(EchoPendingSpell)
		EndIf
		If BloodGuardSpell
			player.DispelSpell(BloodGuardSpell)
		EndIf
	EndIf
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
	BurstCharge = 0
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
	; DLL：離開舊形態的自身階梯（熱度洩壓、熔心、餘壓、聖佑清空、神聖領域）。
	ESSBNative.FormLeave(aiOldIndex, False)
	ClearSelfAll()
	; 規劃 2.12 第 3 列：DrawSheathe_舊 接 FormActive_新（新的那一聲由 OnFormOpened 播，
	; SwitchForm 的呼叫順序就是先 OnFormSwitched 再 OnFormOpened）。
	; Round 18: switching has only the new form activation cue.
	PrevElement = aiOldIndex
	If GPrevElement
		GPrevElement.SetValueInt(aiOldIndex)
	EndIf
	; 5.2 關閉新手分支「餘響」與關閉專精主線：切換後首次命中附帶前一元素附傷。DLL 讀這顆標記結算並移除它。
	If ESSBNodes.EchoRatio(Self) > 0.0
		ApplySelfMarker(EchoPendingSpell, 0)
	EndIf
	; 5.2 關閉大師分支「協奏」與傳奇分支「大協奏」：切換後首次終焉。
	SwitchEndPending = True
	; 5.2 關閉傳奇分支「雙生」：雙持時左手武器攜帶前一個形態的元素 30 秒。
	If ESSBNodes.HasTwin(Self)
		TwinElement = aiOldIndex
		TwinTime = Utility.GetCurrentRealTime()
		If GTwinElement
			GTwinElement.SetValueInt(aiOldIndex)
		EndIf
		; DLL 以這顆 30 秒標記判斷雙生是否仍在時限內（左手另帶 GTwinElement 的元素附傷）。
		ApplySelfMarker(TwinWindowSpell, DurationInt(30.0))
		If CachedDebugLevel >= 1
			LogEvent(1, "node", "common twin element=" + aiOldIndex)
		EndIf
	EndIf
	RefreshSyncStage()
EndFunction

; 融斷（規劃 2.5）：關閉形態的瞬間，範圍內每個帶印記的目標一次結清為爆傷，
; 倍率 K_sync 隨同調段數 0／1／2／3 段 = ×1／×1.5／×2／×3。
Function OnFormClosed(Int aiIndex)
	; 規劃 2.12 第 2 列：關形態／融斷一次 Release 音。爆炸由 ESSB_End 的反應本體放，
	; 預算（每 0.5 秒 5 個）在 PlaceFx 裡，所以「範圍內每個印記目標一次爆炸」自動封頂 5 個。
	PlayFormSound(FxSoundRelease, aiIndex)
	Int syncBefore = Sync.GetValueInt()
	Int stage = SyncStage()
	; 融斷倍率：K_sync × 通用樹關閉路線 × 無元素樹融斷路線 × 該元素印記的融斷加成（各印記另乘，在 ESSBReactions.End）。
	Float k = SyncMult() * ESSBNodes.CommonBurstMult(Self) * ESSBNoForm.BurstMult(Self)
	Float radius = ESSBNoForm.BurstRadius(Self)
	; 雷終焉的放電用融斷當下的電荷；終焉事件在下面的 ClearSelfAll 之後才回來。
	BurstCharge = SelfCharge
	; DLL：範圍內每個帶印記的目標各結清一次（每目標一次終焉冷卻、融斷的狀態部分），反應本體由 ESSB_End 回來跑。
	; 5.1 融斷大師分支「斷界」（所有被結清元素的弱化 3 秒）是 DLL N5。
	Int burst = ESSBNative.BurstMarks(radius, k)
	; DLL：離開形態的自身階梯（熱度洩壓、熔心、餘壓、聖佑清空、神聖領域）。
	ESSBNative.FormLeave(aiIndex, True)
	If CachedDebugLevel >= 1
		LogEvent(1, "burst", "targets=" + burst + " stage=" + stage + " k=" + k + " radius=" + radius)
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
	If ESSBNodes.Br(Self, 12, 2, 3, 1) ; @node 安全閥
		SetGuardBurst(2)
	EndIf
	; 5.1 冷寂路線的收尾（免門檻、連斷、回流、雙斷）。
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
			ESSBElem2.LethalAmbush(Self, targetActor)
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

	Int nativeDamage = NoteDamageElement(targetActor, element)
	If nativeDamage >= 0
		DamageTime[nativeDamage] = Utility.GetCurrentRealTime()
	EndIf
	; Round 22 (N3): the DLL does the whole hit in the hit frame -- the proc with its magnitude and every target-side
	; multiplier read from the target's effects, and the mark: open / refresh / cut, layers and ladders (and the twin
	; element's proc and mark for a 雙生 left-hand hit). Open and end reactions come back as ModEvents (OnESSBOpen /
	; OnESSBEnd). Papyrus keeps only what is N4: the self counters, 極致, the blood power cost, 順勢, 雷暴, 雷霆.

	; 5.2 持續大師分支「極致」：同調三段時每 10 次命中額外一次全額附傷。
	If ESSBNodes.HasExtreme(Self) && SyncStage() >= 3
		ExtremeCount += 1
		If ExtremeCount >= 10
			ExtremeCount = 0
			; 額外一次全額附傷：DLL 以這一擊的旗標與目標當下的狀態算強度並施放（不消耗連殺）。
			ESSBNative.CastProc(targetActor, power)
			If CachedDebugLevel >= 2
				LogThrottled(2, "node", "common extreme extra proc element=" + element)
			EndIf
		EndIf
	EndIf

	; 5.2「餘響」與關閉專精主線：round 20 起由 DLL 在切換後第一擊結算（讀 ESSB_EchoPending，見 OnFormSwitched）。

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
		ESSBElem.Discharge(Self, targetActor, GetSelf(1), True, 1.0, 1.0, -1.0, False)
	EndIf
	If (ThunderLeft > 0 && ThunderLeft > Utility.GetCurrentRealTime()) && HasElementMark(targetActor, 3)
		ESSBElem.Discharge(Self, targetActor, GetSelf(1), False, 0.3, 1.0, -1.0, False)
	EndIf

	If CachedDebugLevel >= 2
		If CachedDebugLevel >= 2
			LogThrottled(2, "hit", targetActor.GetFormID() + " element=" + element + " weapon=" + weaponType \
				+ " power=" + power + " left=" + leftHand + " flags=" + aiHitFlagMask + " sync=" + Sync.GetValueInt())
		EndIf
	EndIf
	OnValidHitInternal(targetActor, element, power)
EndEvent

; 關形態的有效命中（規劃 5.1）。基準真傷、吸魔、小滅法、滅法與它們的節點（含反擊的吸魔 ×2）由 DLL 在命中
; 當下施放；這裡只剩斷咒（N4 前留在 Papyrus）。v0.3 純武藝路線（連段、節奏、疾攻、重擊碎甲、暴擊、終結、處決）
; 與融斷路線的「餘燼」隨 v0.4 的法殺樹拿掉。
Function OnNoFormHit(Actor akTarget, Weapon akWeapon, Bool abPower)
	; Capture before any spell/native damage can end the casting animation.
	Bool hitCasting = ESSBNodes.Br(Self, 11, 1, 1, 0) && (ESSBNoForm.IsCasting(akTarget) || RecentCast(akTarget)) ; @node 斷咒
	MarkEngaged(akTarget)
	ESSBNoForm.OnInterruptCast(Self, akTarget, hitCasting)
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

; 只掛印記、不做開印反應（傳導、聖輝、暗染、星散、風襲、灼身、靜電……「附近 1 人也帶印記」）。
Function ApplyMark(Actor akTarget, Int aiElement)
	If akTarget && aiElement >= 1 && aiElement <= 11
		ESSBNative.ApplyMark(akTarget, aiElement)
	EndIf
EndFunction

; ---------------------------------------------------------------- 開印之後（ESSB_Open 的通用樹部分）

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
		ESSBElem.Discharge(Self, akTarget, charge, False, 0.5, 1.0, -1.0, False)
	EndIf
	; v0.3 的通用樹「廣印」（開印擴散到附近 1 人）v0.4 已移除（同格改為「跳印」，DLL N3）。
EndFunction

; 對目標直接開印（火臨／冰臨／雷臨、雙斷）：DLL 做開印的狀態部分，反應本體由 ESSB_Open 回來跑。
Function ForceOpenOn(Actor akTarget, Int aiElement)
	If !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11
		Return
	EndIf
	MarkEngaged(akTarget)
	ESSBNative.ForceOpen(akTarget, aiElement)
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
	; 5.3 火域：內部敵人受火傷 +20%（附傷與 DLL 結算的火傷由 DLL 讀領域效果）。
	If aiElement == 1 && DomainActive() && InDomain(akTarget, 1)
		amount = amount * 1.2
	EndIf
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
	; 5.1 滅法傳奇分支「噬命」：真實傷害的 50% 轉為你的生命（命中的真傷由 DLL 算，這裡是反咒等 Papyrus 真傷）。
	If ESSBNodes.Br(Self, 11, 1, 4, 1) ; @node 噬命
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
	If !IsOperational() || !CounterEligible(akTarget) || !ESSBNodes.Br(Self, 11, 1, 1, 2) ; @node 反咒
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
EndFunction

; 回復倍率（MCM）變動時：重設自有常駐能力的強度（溫血、感應）並重掛。
; round 21：v0.3 在這裡改寫冰盾、電盾、水鏡、聖盾四個 PERK 進入點的數值；四個節點在 v0.4 都退役或改版，
; ESP 的進入點與這裡的改寫同一輪拿掉（合約成果 3）。
Function RefreshRecovery()
	Actor player = ThePlayer()
	If !player || !Trees
		Return
	EndIf
	Float mult = MultRecovery.GetValue()
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
	; 5.3 持續熟練分支「溫血」：火形態耐力回復 +20%。
	SyncAbility(player, WarmBloodAbility, element == 1 && ESSBNodes.Br(Self, 0, 0, 1, 1)) ; @node 溫血
	; 5.5 持續新手分支「感應」：雷形態魔力回復 +20%。
	SyncAbility(player, InductionAbility, element == 3 && ESSBNodes.Br(Self, 2, 0, 0, 0)) ; @node 感應
	; 5.10 持續新手分支「免疫」：毒形態毒抗 +50%。
	SyncAbility(player, PoisonResistAbility, element == 8 && ESSBElem3.HasPoisonImmunity(Self))
	; 5.4 開啟熟練分支「冰甲」：冰形態下身上一圈 3 公尺寒氣（披風，只對敵對者），範圍內敵人減速 20%；
	; 持續熟練分支「霜膚」：寒氣半徑 3 → 5 公尺，減速再 +10%。凍結量表 ≥1 的 35%（霜膚 45%）與
	; 「命中寒氣內的敵人凍結再 +1」要等凍結量表改成目標身上的效果（DLL N3）。
	; v0.3 的「抗咒」（無形態魔抗）與「星輝」（星形態魔力回復）分支已退役。
	Bool iceArmor = element == 2 && ESSBNodes.Br(Self, 1, 1, 1, 1) ; @node 冰甲
	Bool frostSkin = ESSBNodes.Br(Self, 1, 0, 1, 1) ; @node 霜膚
	SyncAbility(player, IceArmorAbility, iceArmor && !frostSkin)
	SyncAbility(player, IceArmorWideAbility, iceArmor && frostSkin)
	; 規劃 1.1／5.7：風形態的移速與潛行能力。
	RefreshWindAbilities()
	RefreshDivineProtection()
	RefreshSyncStage()
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
	If ESSBNodes.Br(Self, 5, 0, 2, 0) ; @node 逆流
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
	If ESSBNodes.Br(Self, 5, 0, 3, 1) && raw >= 0.3 && raw <= 0.7 ; @node 血怒
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
	ratio = ratio + 0.01 * ESSBNodes.Rank(Self, 5, 0, 2) ; @node 吸血比例各血位
	Float raw = player.GetActorValuePercentage("Health")
	If ESSBNodes.Br(Self, 5, 0, 3, 1) && raw >= 0.3 && raw <= 0.7 ; @node 血怒
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
; v0.4「代價（扣血）不會被任何節點取消，只會被換成別的東西」：v0.3 的「血氣」減半、「血臨強化」「血約」
; 「不死」的免扣血都已拿掉。
Float Function BloodDrainPerSecond()
	If FormActive.GetValueInt() != 1 || CurrentElement.GetValueInt() != 6
		Return 0.0
	EndIf
	Actor player = ThePlayer()
	If !player
		Return 0.0
	EndIf
	Return BloodDrainCurve(player.GetActorValuePercentage("Health"), False)
EndFunction

; 重擊一次的損血（占最大生命）。
Float Function BloodPowerCost()
	Actor player = ThePlayer()
	If !player
		Return 0.0
	EndIf
	Return BloodDrainCurve(player.GetActorValuePercentage("Health"), True)
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

; 反應的吸血回血（開印、血潮；命中吸血 round 20 起在 DLL）。
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
	; round 20：同一格的節點在 v0.4 是「血溢」（命中吸血的溢出灌進護血池，由 DLL 做）。反應的回血
	;（開印、血潮）到 N3 進 DLL 之前，溢出不灌池。
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
	EndIf
EndFunction

; 樣式 C 的鏡射：電荷、冰盾、戰意寫進全域變數給 PERK 進入點（v0.3 的過熱在 v0.4 是 DLL 的熱度階梯）。
Function PushSelf()
	If GCharge && GCharge.GetValueInt() != SelfCharge
		GCharge.SetValueInt(SelfCharge)
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
	EndIf
EndFunction

Function ClearSelfAll()
	SelfCharge = 0
	SelfRockArmor = 0
	SelfWind = 0
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
	; 護血池（DLL 灌入的血溢）也是疊在你身上的資源：離開形態清空（v0.4 2.3）。
	Actor player = ThePlayer()
	If player && BloodGuardSpell
		player.DispelSpell(BloodGuardSpell)
	EndIf
EndFunction

; DLL 讀的自身標記（餘響待發、雙生視窗）：套在玩家身上；aiSeconds > 0 時先寫時長。
Function ApplySelfMarker(Spell akMarker, Int aiSeconds)
	Actor player = ThePlayer()
	If !player || !akMarker
		Return
	EndIf
	If aiSeconds > 0
		akMarker.SetNthEffectDuration(0, aiSeconds)
	EndIf
	player.DoCombatSpellApply(akMarker, player)
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

; 毒的擴散：每個帶毒目標每次只找一個對象，不做全場掃描（規劃 2.7）。狀態碼 25＝擴散一劑：
; m' = m + 劑數、d' = max(d - t, 12)（審查修正 5；命中的 +3 秒規則是碼 7）。
Function SpreadPoison(Actor akFrom, Int aiAmount, Int aiTargets = 1)
	If !akFrom
		Return
	EndIf
	Actor[] nearby = ScanTargets(akFrom, 210.0, aiTargets, akFrom)
	Int index = 0
	While index < nearby.Length
		If nearby[index] && aiAmount > 0
			ESSBNative.AddStatus(nearby[index], 25, aiAmount)
		EndIf
		index += 1
	EndWhile
EndFunction

; ---------------------------------------------------------------- 每秒 tick 與環境

Function Tick()
	If !IsOperational()
		; 總開關關掉（IsOperational 不成立）時：仍要解除神佑的延遲死亡，否則角色會停在不會死的狀態（RefreshDivineProtection
		; 在 eligible 不成立時 EndDeferredKill）；並保持 5 秒一次的空 tick，重新打開總開關後每秒工作照常接上。
		If IsCurrentController() && !StateBroken && Ready
			If DivineArmed
				RefreshDivineProtection()
			EndIf
			NextTickAt = 0.0
			ScheduleTick(5.0)
		EndIf
		Return
	EndIf
	; 主控台 `set ESSB_DebugLevel to N` 不會觸發任何事件，快取只在載入／換形態／關 MCM 時刷新，
	; 玩家在遊戲中途開除錯會一直看不到紀錄。每個 tick 讀一次（不是每刀），成本可忽略。
	CachedDebugLevel = DebugLevel.GetValueInt()
	InitTables()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If MultRecovery && LastRecoveryScale != MultRecovery.GetValue()
		RefreshRecovery()
	EndIf
	Float now = Utility.GetCurrentRealTime()

	; 自身資源衰減（規劃 2.3）：風勢 5 秒未命中歸零；電荷 10 秒未命中後每秒 -1；
	; 岩甲不衰減。
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
	; 印記與目標狀態的過期由 DLL 讀引擎效果的時長結算（ESSB_End 理由 2）；這裡只剩擊殺掛勾的保底。
	SettleStaleKills(now)

	; 5.2 持續傳奇主線「化身」是 DLL N4（冷卻後的下一次命中觸發該元素的持續傳奇；被動數值改為 10 秒視同已取得）。
	; v0.3「每 N 秒自動施放一次」的近似已拿掉。

	; 各元素樹的每秒掛勾（冰心、雷神、毒形態、長流）。
	If FormActive.GetValueInt() == 1
		Int tickElement = CurrentElement.GetValueInt()
		ESSBElem.OnTick(Self, tickElement)
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

	If now - LastEnvCheck >= 5.0
		LastEnvCheck = now
		EnvCheck()
	EndIf

	Float delay = 5.0
	If FormActive.GetValueInt() == 1 || TimersActive() || KillPending()
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
	Int oldStage = CachedSyncStage
	Float now = Utility.GetCurrentRealTime()
	; v0.3 的熔身（過熱滿 10 秒、每秒回耐力）在 v0.4 是 DLL 的熔身效果與每秒 tick。
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
	If KeepSneakLeft > 0
		If now >= KeepSneakLeft
			KeepSneakLeft = 0.0
		EndIf
		If KeepSneakLeft <= 0
			Actor sneaker = ThePlayer()
			If sneaker
				PO3_SKSEFunctions.ResetActorDetection(sneaker)
			EndIf
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
	TickDomain()
	RefreshSyncStage()
	If oldStage != CachedSyncStage
		PushSyncStage()
		RefreshDivineProtection()
	EndIf
EndFunction

Bool Function TimersActive()
	If (EmberLeft > 0 && EmberLeft > Utility.GetCurrentRealTime()) || (QuenchLeft > 0 && QuenchLeft > Utility.GetCurrentRealTime()) || (ShockLeft > 0 && ShockLeft > Utility.GetCurrentRealTime()) || DomainActive()
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
	Return (NoBloodCostLeft > 0 && NoBloodCostLeft > Utility.GetCurrentRealTime()) || (WindFollowLeft > 0 && WindFollowLeft > Utility.GetCurrentRealTime()) || (KeepSneakLeft > 0 && KeepSneakLeft > Utility.GetCurrentRealTime()) 		|| DivineSaveUsed
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
; 節點腳本是無狀態的全域函式，這樣加新元素只要加函式。

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

; 對目標加層（代碼見 ESSBNative.psc）：狀態本身是 DLL 掛在目標身上的引擎效果，上限與萬象也在 DLL。
Function AddStackTo(Actor akTarget, Int aiKind, Int aiAmount)
	If akTarget && aiAmount > 0
		ESSBNative.AddStatus(akTarget, aiKind, aiAmount)
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

; 離玩家最近、帶指定元素印記的目標（雷神用）。
Actor Function NearestMarked(Int aiElement)
	Actor player = ThePlayer()
	If !player || aiElement < 1 || aiElement > 11
		Return None
	EndIf
	Actor[] found = ESSBNative.MarkedNear(player, 7000.0, 1, aiElement)
	If found && found.Length > 0
		Return found[0]
	EndIf
	Return None
EndFunction

; ---- 領域（火域、冰原）
; 規劃 2.9 的例外表：中心為目標、半徑 3 公尺、持續 5 秒。本模組不放任何
; ObjectReference，只記中心座標與剩餘秒數，判定在既有的每秒 tick 與命中路徑上做。
; 3 格：同元素的領域直接取代自己那一格，否則取空格，全滿就換掉剩餘秒數最少的那一格。
; 半徑預設 3 公尺（規劃 2.9 例外表），星域另外傳入隨主線成長的半徑。
Function StartDomain(Int aiElement, Actor akCenter, Int aiSeconds, Float afRadius = 210.0)
	InitTables()
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
	InitTables()
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
	InitTables()
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
	InitTables()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !DomainActive()
		PlayerInFireDomain = False
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
					ApplyUtil(4, 20.0 * ticks, 0, player)
				ElseIf element == 7
					ApplyUtil(4, 25.0 * ticks, 0, player)
					ApplyUtil(5, 20.0 * ticks, 0, player)
				ElseIf element == 9
					; 潮池：你在其中回血回耐力並每秒洗淨一次。
					ApplyUtil(4, 15.0 * ticks, 0, player)
					ApplyUtil(6, 15.0 * ticks, 0, player)
					ApplyCleanse(False)
				EndIf
			EndIf
			Int index = 0
			While index < nearby.Length
				Actor victim = nearby[index]
				; 火域（受火附傷 +20%）、冰原（凍結累積 ×2）、星域（受所有元素傷 +20%）：DLL 讀內部敵人身上的領域效果
				;（2 秒，每秒續；離開或領域結束後最多殘留 2 秒）。
				If victim && element == 1
					ESSBNative.SetWindow(victim, 32, 2.0, 0.0)
				ElseIf victim && element == 2
					ESSBNative.SetWindow(victim, 33, 2.0, 0.0)
				ElseIf victim && element == 11
					ESSBNative.SetWindow(victim, 34, 2.0, 0.0)
				EndIf
				ticks = DomainTargetTicks(victim, slot, stop)
				If victim && ticks > 0
					If element == 2
						; 冰原：內部敵人減速 50%。
						ApplyUtil(0, 50.0, 2, victim)
					EndIf
					If element == 4
						; 5.6 關閉傳奇分支「地裂」：內部敵人耐力不回復，耐力歸 0 的敵人在其中跌倒
						; （Knockdown 本身是每目標 8 秒一次）。「掛倒地」要等倒地標記（DLL N3）。
						ApplyUtil(21, 100.0, 2, victim)
						If victim.GetActorValue("Stamina") <= 0.0
							Knockdown(victim, 3.0)
						EndIf
					EndIf
					If element == 8
						; 5.10 關閉傳奇分支「毒霧」：內部每秒 +1 毒層。
						AddStackTo(victim, 7, ticks)
					EndIf
					If element == 9
						; 5.11 關閉傳奇分支「潮池」：內部敵人每秒被沖刷一個增益（沖刷法術；v0.4 寫的 DLL 原生沖刷函式尚未有）。
						ApplyStrip(victim, True)
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
	; 火域：你在其中熱度升階免等待（DLL 讀你身上的效果），進入火域時白熱引信一次性 +5 秒（v0.4 5.3）。
	Bool inFire = player && PlayerInDomain(1)
	If inFire
		ESSBNative.SetWindow(player, 35, 2.0, 0.0)
		If !PlayerInFireDomain
			ESSBNative.ExtendFuse(5.0)
		EndIf
	EndIf
	PlayerInFireDomain = inFire
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
	InitTables()
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
	; v0.4 2.3：土造成的跌倒掛上「倒地」（3 秒），倒地的目標被你打的每一刀都算重擊（DLL）。
	ESSBNative.AddStatus(akTarget, 13, 1)
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
	; v0.4 的「牽引」是開印拉近時連身後 1.5 公尺內的敵人一起拉（掃描 N5），v0.3 的「拉近後減速 80%」已拿掉。
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

; ---- 浮空（DLL 掛在目標身上的效果；到期時 DLL 以 ESSB_Landing 送回落地傷害，見 OnLanding）
Function SetAirborne(Actor akTarget, Int aiSeconds, Float afDamage)
	If !akTarget
		Return
	EndIf
	; 浮空期間同時失衡（v0.4 5.7）。
	ESSBNative.AddStatus(akTarget, 4, 1)
	ESSBNative.SetWindow(akTarget, 36, aiSeconds as Float, afDamage)
EndFunction

Int Function GetAirborne(Actor akTarget)
	If !akTarget
		Return 0
	EndIf
	Return ESSBNative.GetStatus(akTarget, 14)
EndFunction

; 浮空到期（ESSB_Landing）：落地傷害（5.7 關閉傳奇主線）。
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
	; DLL 讀你身上的嗜血效果（命中效果 +20%）；Papyrus 的反應本體讀這裡的計時（GetDamageMult）。
	Actor player = ThePlayer()
	If player
		ESSBNative.SetWindow(player, 30, aiSeconds as Float, 0.0)
	EndIf
	aiSeconds = DurationInt(aiSeconds)
	BloodthirstLeft = Utility.GetCurrentRealTime() + aiSeconds
	SetGlobal(GBloodthirst, SecondsLeft(BloodthirstLeft))
	RefreshSyncStage()
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

; 5.1 大師熟練分支「反擊」：格擋成功後 3 秒內下一次命中吸魔 ×2。格擋偵測在 ESSBGuard（N4 前）；
; 這裡在你身上掛 3 秒反擊視窗，DLL 在下一次無形態命中讀它、吸魔 ×2 後移除（N2 那一半）。
Function SetRiposte(Int aiSeconds)
	ApplySelfMarker(RiposteWindowSpell, DurationInt(aiSeconds))
EndFunction

; 5.7 關閉傳奇分支「連殺」：擊殺後 5 秒內不解除潛行；下一次潛行攻擊 ×2 是 DLL 讀的連殺效果（ESSBElem2.TryKillStreak）。
Function KeepSneak(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	KeepSneakLeft = Utility.GetCurrentRealTime() + aiSeconds
	Actor player = ThePlayer()
	If player
		; 規劃 8：用「壓低偵測值」實作，尊重原版偵測系統，不鎖 AI。
		PO3_SKSEFunctions.PreventActorDetection(player)
	EndIf
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
	If DivineSaveUsed || !ESSBNodes.Br(Self, 6, 0, 4, 0) || SyncStage() < 3 ; @node 神佑
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

; ---- 沖刷（5.11）：沖掉目標一個「手施、有時限、有益」的增益，判定同浸濕／水壓的全數沖刷（DLL WashBuffs：
; 排除種族能力、任務腳本、常駐能力、疾病、藥水與本模組自己的效果）。每目標 10 秒一次（沿用推力的環狀表，
; kind 2）；潮池的「每秒沖刷一個」走 abEverySecond，不吃這個冷卻。
Function ApplyStrip(Actor akTarget, Bool abEverySecond = False)
	Actor player = ThePlayer()
	If !player || !akTarget || akTarget == player || !IsValidTarget(akTarget)
		Return
	EndIf
	If !abEverySecond && !TakePush(akTarget, 2)
		Return
	EndIf
	Int washed = ESSBNative.WashBuffs(akTarget, 1)
	If CachedDebugLevel >= 1
		LogThrottled(1, "strip", akTarget.GetFormID() + " washed=" + washed)
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

; abScaled：秒數已經乘過 MultDuration（DLL 的幻覺階梯送來的秒數），不再乘一次。
Function ApplyFear(Actor akTarget, Int aiSeconds, Bool abScaled = False)
	Actor player = ThePlayer()
	If !player || !FearSpell || !CanCharm(akTarget) || aiSeconds < 1
		Return
	EndIf
	Int seconds = aiSeconds
	If !abScaled
		seconds = DurationInt(aiSeconds)
	EndIf
	FearSpell.SetNthEffectMagnitude(0, ESSBElem3.CharmCap(Self) as Float)
	FearSpell.SetNthEffectDuration(0, seconds)
	player.DoCombatSpellApply(FearSpell, akTarget)
	If CachedDebugLevel >= 1
		LogThrottled(1, "fear", akTarget.GetFormID() + " sec=" + aiSeconds)
	EndIf
EndFunction

Function ApplyFrenzy(Actor akTarget, Int aiSeconds, Bool abScaled = False)
	Actor player = ThePlayer()
	If !player || !FrenzySpell || !CanCharm(akTarget) || aiSeconds < 1
		Return
	EndIf
	Int seconds = aiSeconds
	If !abScaled
		seconds = DurationInt(aiSeconds)
	EndIf
	FrenzySpell.SetNthEffectMagnitude(0, ESSBElem3.CharmCap(Self) as Float)
	FrenzySpell.SetNthEffectDuration(0, seconds)
	player.DoCombatSpellApply(FrenzySpell, akTarget)
	; 5.12 開啟熟練分支「狂刃」：瘋狂中的目標造成的傷害 +50%（同樣秒數的引擎效果，AttackDamageMult +0.5）。
	If ESSBNodes.Br(Self, 9, 1, 1, 2) && FrenzyBladeSpell ; @node 狂刃
		FrenzyBladeSpell.SetNthEffectDuration(0, seconds)
		player.DoCombatSpellApply(FrenzyBladeSpell, akTarget)
	EndIf
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

; ---- 化灰與血承
; FIX14: bounded per-actor recent damage survives registry eviction; no current-form fallback.
Int Function LastDamageFor(Actor akTarget)
	If !akTarget || !DamageActor || !DamageTime
		Return 0
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Int i = 0
	While i < 128
		If DamageActor[i] == akTarget
			Float age = now - DamageTime[i]
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

Int Function NoteDamageElement(Actor akTarget, Int aiElement, Int aiDamageSlot = -1)
	If !akTarget || !DamageActor
		Return -1
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
	DamageTime[DamageNext] = -1.0
	If aiElement >= 0
		DamageElement[DamageNext] = aiElement
	EndIf
	DamageNext = (DamageNext + 1) % 128
	Return assigned
EndFunction

; All damaging spells are instant contact/self delivery (DELIVERY build gate).
; FIX14: publish before native delivery for lethal callback ordering; keep nonlethal damage.
; No health loss rolls back the provisional record. Never infer an element from form.
Function ApplyTrackedDamage(Actor player, Spell akSpell, Actor akTarget, Int aiElement)
	If StateBroken || !Ready || !player || !akSpell || !akTarget
		Return
	EndIf
	Float beforeHealth = akTarget.GetActorValue("Health")
	If akTarget.IsDead() || beforeHealth <= 0.0 || !IsOperational()
		Return
	EndIf
	Int damageSlot = NoteDamageElement(akTarget, -1)
	If damageSlot < 0
		Return
	EndIf
	Int previous = DamageElement[damageSlot]
	Float previousTime = DamageTime[damageSlot]
	Float now = Utility.GetCurrentRealTime()
	DamageElement[damageSlot] = aiElement
	DamageTime[damageSlot] = now
	player.DoCombatSpellApply(akSpell, akTarget)
	If akTarget.GetActorValue("Health") >= beforeHealth && DamageActor[damageSlot] == akTarget && DamageTime[damageSlot] == now && DamageElement[damageSlot] == aiElement
		DamageElement[damageSlot] = previous
		DamageTime[damageSlot] = previousTime
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

; ---- 擊殺事件
; 致死元素：最近 3 秒內的本模組傷害優先；沒有時取死亡快照裡的印記（形態元素的印記優先，其次元素序最小的）。
Int Function KillElementFor(Actor akVictim, Int aiMarks)
	Int recent = LastDamageFor(akVictim)
	If recent >= 1
		Return recent
	EndIf
	If aiMarks == 0
		Return 0
	EndIf
	Int current = CurrentElement.GetValueInt()
	If FormActive.GetValueInt() == 1 && HasMarkBit(aiMarks, current)
		Return current
	EndIf
	Int element = 1
	While element <= 11
		If HasMarkBit(aiMarks, element)
			Return element
		EndIf
		element += 1
	EndWhile
	Return 0
EndFunction

Bool Function HasMarkBit(Int aiMarks, Int aiElement)
	Return aiElement >= 1 && aiElement <= 11 && Math.LogicalAnd(aiMarks, Math.LeftShift(1, aiElement)) != 0
EndFunction

; PO3 的擊殺回報（ESSBGuard 的 OnActorKilled）。DLL 的死亡快照已經到了就立刻結算，否則等快照（OnESSBDeath），
; 1 秒內都沒來就以空快照結算（SettleStaleKills）。
Function OnKillEvent(Actor akVictim, Actor akKiller = None)
	If !IsOperational()
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	If !akVictim || akKiller != ThePlayer()
		Return
	EndIf
	If NativeHit.GetValueInt() != 1 || HasDeathSnapshot(akVictim)
		SettleKill(akVictim)
		Return
	EndIf
	Int i = 0
	While i < 4
		If PendingKillActor[i] == akVictim
			Return
		EndIf
		i += 1
	EndWhile
	PendingKillActor[PendingKillNext] = akVictim
	PendingKillAt[PendingKillNext] = Utility.GetCurrentRealTime()
	PendingKillNext = (PendingKillNext + 1) % 4
	ScheduleTick(1.0)
EndFunction

Bool Function HasDeathSnapshot(Actor akVictim)
	Int i = 0
	While i < 8
		If DeadActor[i] == akVictim
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; 擊殺掛勾（連鎖冰封、飲血、血承、化灰、連殺、焚化、噬魂）：每個死者只結算一次。
Function SettleKill(Actor akVictim)
	Int index = 0
	While index < 8
		If SettledDead[index] == akVictim
			Return
		EndIf
		index += 1
	EndWhile
	; Claim before calling any other script: repeated events cannot grant twice.
	Int settlement = SettledNext
	SettledElement[settlement] = 0
	SettledDead[settlement] = akVictim
	SettledNext = (SettledNext + 1) % 8
	index = 0
	While index < 4
		If PendingKillActor[index] == akVictim
			PendingKillActor[index] = None
		EndIf
		index += 1
	EndWhile
	Int element = LastDamageFor(akVictim)
	Int marks = 0
	Int freeze = 0
	Int bleed = 0
	index = 0
	While index < 8
		If DeadActor[index] == akVictim
			element = DeadElement[index]
			marks = DeadMarks[index]
			freeze = DeadFreeze[index]
			bleed = DeadBleed[index]
			DeadActor[index] = None
		EndIf
		index += 1
	EndWhile
	SettledElement[settlement] = element
	; v0.4 5.9：帶神聖印記死亡即化灰，不看致死元素；其餘照致死元素（ShouldAsh，含淨土）。
	Bool ash = ESSBElem2.ShouldAsh(Self, element) || HasMarkBit(marks, 7)
	ESSBElem.OnKill(Self, element, akVictim, freeze)
	ESSBElem2.OnKill(Self, element, akVictim, bleed, element, ash)
	; v0.3 的毒「蔓延」、暗「收割」「亡者歸來」、無元素「無魔」擊殺掛勾在 v0.4 是死亡處理（DLL N5）或已移除。
	SettleSneakKill(akVictim, element)
	SettleKillProc(akVictim)
	If CachedDebugLevel >= 1
		LogThrottled(1, "kill", akVictim.GetFormID() + " element=" + element + " marks=" + marks)
	EndIf
EndFunction

; PO3 回報了擊殺、DLL 的快照 1 秒內沒來（目標身上沒有任何本模組狀態）：以空快照結算。
Function SettleStaleKills(Float afNow)
	Int i = 0
	While i < 4
		Actor victim = PendingKillActor[i]
		If victim && afNow - PendingKillAt[i] >= 1.0
			PendingKillActor[i] = None
			SettleKill(victim)
		EndIf
		i += 1
	EndWhile
EndFunction

Bool Function KillPending()
	Int i = 0
	While i < 4
		If PendingKillActor[i]
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; ================================================================ DLL → 反應本體（ModEvent）
; strArg 是 DLL 把各值以 "|" 串起來的字串（Plugin.cpp SendEvent，順序見 native/include/Status.h 的 enum Event），
; sender 是目標。每個處理函式先驗控制器，再把值交給反應本體；目標狀態已由 DLL 在送出前改好。

Float Function EventArg(String[] akArgs, Int aiIndex)
	If !akArgs || aiIndex < 0 || aiIndex >= akArgs.Length
		Return 0.0
	EndIf
	Return akArgs[aiIndex] as Float
EndFunction

; DLL 送來的秒數已乘過 MultDuration；ApplyUtil 會再乘一次，先換回未乘的秒數。
Int Function UnscaledSeconds(Float afSeconds)
	Float scale = CachedDuration
	If !RuntimeCacheReady
		scale = MultDuration.GetValue()
	EndIf
	If scale <= 0.0
		scale = 1.0
	EndIf
	Int seconds = (afSeconds / scale + 0.5) as Int
	If seconds < 1
		seconds = 1
	EndIf
	Return seconds
EndFunction

; ESSB_Open：元素、開印倍率、這一擊切掉的元素（0 = 沒有）、1 = 命中開的印（ForceOpen 是 0）。
Event OnESSBOpen(String asEventName, String asArgs, Float afElement, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int element = EventArg(args, 0) as Int
	If element < 1 || element > 11
		Return
	EndIf
	If Trees
		; 規劃 4：開印給新印記元素樹 + 通用樹。
		Trees.OnOpenXP(element)
	EndIf
	ESSBReactions.Open(Self, element, target, EventArg(args, 1), EventArg(args, 2) as Int, EventArg(args, 3) > 0.5)
EndEvent

; ESSB_End：元素、理由（0 被切 1 融斷 2 過期）、終焉倍率、1 = 連鎖終焉、三個 DLL 算好的值（ESSBReactions.End）。
Event OnESSBEnd(String asEventName, String asArgs, Float afElement, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int element = EventArg(args, 0) as Int
	If element < 1 || element > 11
		Return
	EndIf
	ESSBReactions.End(Self, element, target, EventArg(args, 1) as Int, EventArg(args, 2), EventArg(args, 3) > 0.5, \
		EventArg(args, 4), EventArg(args, 5), EventArg(args, 6))
EndEvent

; ESSB_Frozen：冰封秒數（冰封期間的強減速與深寒）。
Event OnESSBFrozen(String asEventName, String asArgs, Float afSeconds, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	ESSBElem.OnFrozen(Self, target, UnscaledSeconds(afSeconds))
	; 5.4 開啟大師分支「霜爆」：目標進入冰封的那一刻，3 公尺內其他凍結量表 ≥1 的敵人凍結 +2（掃描 N5 前在這裡）。
	If ESSBNodes.Br(Self, 1, 1, 3, 2) ; @node 霜爆
		Actor[] near = ScanTargets(target, 210.0, 5, target)
		Int index = 0
		While index < near.Length
			If near[index] && ESSBNative.GetStatus(near[index], 2) >= 1
				AddStackTo(near[index], 2, 2)
			EndIf
			index += 1
		EndWhile
	EndIf
EndEvent

; ESSB_Hallucinate：1 恐懼 / 2 瘋狂、秒數（DLL 已比過詛咒門檻與冷卻）。控不到的目標改為 3 秒幻視：攻擊 -20%（v0.4 5.12）。
Event OnESSBHallucinate(String asEventName, String asArgs, Float afKind, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int kind = EventArg(args, 0) as Int
	Float seconds = EventArg(args, 1)
	If !CanCharm(target)
		; v0.4 第 1380 行：幻視 3 秒、攻擊 -20%＝攻擊傷害倍率 ×0.8（AttackDamageMult -0.2），不是平減 MeleeDamage。
		Actor visionCaster = ThePlayer()
		If VisionSpell && visionCaster
			visionCaster.DoCombatSpellApply(VisionSpell, target)
		EndIf
		If CachedDebugLevel >= 1
			LogThrottled(1, "illusion", target.GetFormID() + " vision kind=" + kind)
		EndIf
		Return
	EndIf
	Int whole = (seconds + 0.5) as Int
	If whole < 1
		whole = 1
	EndIf
	If kind == 2
		ApplyFrenzy(target, whole, True)
		; 5.12 開啟傳奇分支「群魔」：同調三段時，目標達到瘋狂門檻那一刻，4 公尺內所有詛咒 ≥3 層的敵人一起瘋狂 3 秒
		;（各自的瘋狂冷卻照算；掃描 N5 前在這裡）。
		If ESSBNodes.Br(Self, 9, 1, 4, 0) && SyncStage() >= 3 ; @node 群魔
			Actor[] crowd = ScanTargets(target, 280.0, 5, target)
			Int index = 0
			While index < crowd.Length
				Actor other = crowd[index]
				If other && ESSBNative.GetStatus(other, 10) >= 3 && ESSBNative.GetStatus(other, 24) == 0 && CanCharm(other)
					ApplyFrenzy(other, 3)
					ESSBNative.SetWindow(other, 37, 20.0, 0.0)
				EndIf
				index += 1
			EndWhile
		EndIf
	Else
		ApplyFear(target, whole, True)
		; 5.12 開啟新手分支「夢魘」：目標恐懼時，3 公尺內其他敵人詛咒 +1（每次恐懼一次；掃描 N5 前在這裡）。
		If ESSBNodes.Br(Self, 9, 1, 0, 0) ; @node 夢魘
			Actor[] near = ScanTargets(target, 210.0, 5, target)
			Int index = 0
			While index < near.Length
				If near[index]
					AddStackTo(near[index], 10, 1)
				EndIf
				index += 1
			EndWhile
		EndIf
	EndIf
EndEvent

; ESSB_Judgment：聖裁在聖佑 II／III 時的破防：目標護甲 -60、魔抗 -10%，5 秒（v0.4 5.9；III 的 3 公尺聖光爆是範圍掃描，N5）。
Event OnESSBJudgment(String asEventName, String asArgs, Float afTier, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	ApplyUtil(1, 60.0, 5, target)
	ApplyUtil(16, 10.0, 5, target)
	If CachedDebugLevel >= 1
		LogThrottled(1, "judgment", target.GetFormID() + " tier=" + (afTier as Int))
	EndIf
EndEvent

; ESSB_Splash：往下越線的濺血（v0.4 5.8）：15 公尺內所有流血目標（最多 5）立即結算一次 ×0.5 血潮，不清除血痕
;（掃描 N5 前在這裡）。
Event OnESSBSplash(String asEventName, String asArgs, Float afRemaining, Form akSender)
	If !IsOperational()
		Return
	EndIf
	Splash()
EndEvent

Function Splash()
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Actor[] bleeding = ScanTargets(player, 1050.0, 5, None)
	Int index = 0
	While index < bleeding.Length
		If bleeding[index] && ESSBNative.GetStatus(bleeding[index], 5) > 0
			ESSBReactions.SurgeOn(Self, bleeding[index], 0.5, False)
		EndIf
		index += 1
	EndWhile
EndFunction

; ESSB_Rise：往上越線（回湧本身是 N4）。5.8 關閉專精分支「血約」：15 公尺內所有流血目標血痕 +2 層（掃描 N5 前在這裡）。
Event OnESSBRise(String asEventName, String asArgs, Float afUnused, Form akSender)
	Actor player = ThePlayer()
	If !IsOperational() || !player || !ESSBNodes.Br(Self, 5, 2, 2, 0) ; @node 血約
		Return
	EndIf
	Actor[] bleeding = ScanTargets(player, 1050.0, 5, None)
	Int index = 0
	While index < bleeding.Length
		If bleeding[index] && ESSBNative.GetStatus(bleeding[index], 5) > 0
			AddStackTo(bleeding[index], 5, 2)
		EndIf
		index += 1
	EndWhile
EndEvent

; ESSB_Shatter：碎冰之後的碎甲（1 命中碎冰、2 冰終焉碎冰；DLL 已結算真傷並結束冰封）。
Event OnESSBShatter(String asEventName, String asArgs, Float afSource, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	ESSBElem.OnShatter(Self, target)
EndEvent

; ESSB_Landing：浮空到期，落地傷害。
Event OnESSBLanding(String asEventName, String asArgs, Float afDamage, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	OnLanding(target, afDamage)
EndEvent

; ESSB_Death：DLL 在目標死亡、屍體還帶著效果時送出的快照：印記位元、凍結、血痕層、毒劑、詛咒、1 = 冰封中、
; 1 = 冥蝕、1 = 玩家擊殺。玩家擊殺就結算擊殺掛勾；否則留給稍後到的 PO3 擊殺回報（OnKillEvent）。
Event OnESSBDeath(String asEventName, String asArgs, Float afMarks, Form akSender)
	Actor victim = akSender as Actor
	If !IsOperational() || !victim
		Return
	EndIf
	InitFixState()
	If !IsCurrentController() || StateBroken
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int marks = EventArg(args, 0) as Int
	Int freeze = EventArg(args, 1) as Int
	If EventArg(args, 5) > 0.5
		; 冰封中死亡＝量表滿（連鎖冰封讀 5）。
		freeze = 5
	EndIf
	Int slot = DeadNext
	DeadActor[slot] = victim
	DeadMarks[slot] = marks
	DeadElement[slot] = KillElementFor(victim, marks)
	DeadFreeze[slot] = freeze
	DeadBleed[slot] = EventArg(args, 2) as Int
	DeadNext = (DeadNext + 1) % 8
	Bool pending = False
	Int i = 0
	While i < 4
		If PendingKillActor[i] == victim
			pending = True
		EndIf
		i += 1
	EndWhile
	If pending || EventArg(args, 7) > 0.5
		SettleKill(victim)
	EndIf
EndEvent

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

; ---------------------------------------------------------------- 除錯：印出附近目標的狀態（DLL 的引擎效果）

Function DumpStatus()
	If !IsReadyUI()
		Return
	EndIf
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	Debug.Trace("[ESSB][dump][L0] status element=" + CurrentElement.GetValueInt() \
		+ " active=" + FormActive.GetValueInt() + " sync=" + Sync.GetValueInt() + " stage=" + SyncStage() \
		+ " charge=" + SelfCharge + " rock=" + SelfRockArmor + " wind=" + SelfWind \
		+ " heat=" + ESSBNative.GetStatus(player, 20) + " holy=" + ESSBNative.GetStatus(player, 21) \
		+ " molten=" + ESSBNative.GetStatus(player, 22) \
		+ " wet=" + IsEnvWet() + " stormy=" + IsEnvStormy() + " night=" + IsEnvNight())
	Actor[] marked = ESSBNative.MarkedNear(player, 3500.0, 16, 0)
	Int count = 0
	Int index = 0
	While marked && index < marked.Length
		Actor target = marked[index]
		If target
			count += 1
			String line = "[ESSB][dump][L0] target=" + target.GetFormID() + " marks=" + ESSBNative.MarksOn(target) \
				+ " dist=" + target.GetDistance(player)
			Int code = 2
			While code <= 19
				Int value = ESSBNative.GetStatus(target, code)
				If value != 0
					line = line + " s" + code + "=" + value
				EndIf
				code += 1
			EndWhile
			Debug.Trace(line)
		EndIf
		index += 1
	EndWhile
	Debug.Trace("[ESSB][dump][L0] status end marked=" + count)
	; 探針卡「新來的 NPC 沒有殘留狀態」（審查修正 7）：最近一個可打的目標，狀態碼 2～19 全部列在畫面上。
	Actor nearest = ScanTargets(player, 2100.0, 1, player)[0]
	String shown = "（附近沒有目標）"
	If nearest
		shown = nearest.GetDisplayName() + "：印記 " + ESSBNative.MarksOn(nearest)
		Int c = 2
		While c <= 19
			shown = shown + " s" + c + "=" + ESSBNative.GetStatus(nearest, c)
			c += 1
		EndWhile
	EndIf
	Debug.MessageBox("元素魔戰士：附近帶印記的目標 " + count + " 個\n最近的目標 " + shown)
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

; 雷終焉用哪一份電荷：被切＝切換當下存起來的（TakeSwitchCharge）、融斷＝融斷當下的（BurstCharge）、過期＝現在的。
Int Function EndCharge(Int aiReason)
	If aiReason == 0
		Return TakeSwitchCharge()
	ElseIf aiReason == 1
		Return BurstCharge
	EndIf
	Return SelfCharge
EndFunction

Function ConsumeEndCharge(Int aiCharge, Int aiReason = 2)
	If aiCharge <= 0 || ESSBNodes.Br(Self, 2, 2, 1, 0) ; @node 蓄餘
		Return
	EndIf
	If aiReason == 1
		BurstCharge -= aiCharge
		If BurstCharge < 0
			BurstCharge = 0
		EndIf
		Return
	EndIf
	SelfCharge -= aiCharge
	If SelfCharge < 0
		SelfCharge = 0
	EndIf
	GCharge.SetValueInt(SelfCharge)
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
; 審查修正 3：總開關（ESSB_Enabled）關掉時，所有遊戲路徑（命中、狀態、每秒、結算、ModEvent 反應）都不做事。
Bool Function IsOperational()
	Return IsReadyUI() && Enabled && Enabled.GetValueInt() == 1
EndFunction

; 指揮官裁定（審查修正後）：MCM 與選單動作（狀態按鈕、技能樹選單、洗點、恢復預設、設定、關閉形態）不看總開關，
; 只要控制器就緒就能用；遊戲效果另看 IsOperational。
Bool Function IsReadyUI()
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
	If !NativeHit || !NativeWanted
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
	If !BloodGuardSpell || !EchoPendingSpell || !TwinWindowSpell
		Return False
	EndIf
	If !RiposteWindowSpell
		Return False
	EndIf
	If !IceArmorAbility
		Return False
	EndIf
	If !IceArmorWideAbility
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
EndFunction

Event OnMenuClose(String asMenuName)
	If !IsReadyUI() || asMenuName != "Journal Menu"
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
	InitTables()
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
	If KeepSneakLeft > 0
		PO3_SKSEFunctions.ResetActorDetection(ThePlayer())
	EndIf
	SetGlobal(GDomainFire, 0)
	SetGlobal(GDomainFrost, 0)
	SetGlobal(GDomainEarth, 0)
	SetGlobal(GDomainBlood, 0)
	SetGlobal(GDomainDivine, 0)
	SetGlobal(GDomainPoison, 0)
	SetGlobal(GDomainWater, 0)
	SetGlobal(GDomainDark, 0)
	SetGlobal(GDomainAstral, 0)
	EmberLeft = 0.0
	QuenchLeft = 0.0
	ShockLeft = 0.0
	GuardSwitchLeft = 0.0
	GuardBurstLeft = 0.0
	GuardIceLeft = 0.0
	ThunderLeft = 0.0
	DoubleBurstLeft = 0.0
	SyncKeepLeft = 0.0
	BloodthirstLeft = 0.0
	GuardWindLeft = 0.0
	GuardDivineLeft = 0.0
	CloakGuardLeft = 0.0
	NoBloodCostLeft = 0.0
	WindFollowLeft = 0.0
	KeepSneakLeft = 0.0
	GuardDarkLeft = 0.0
	GuardAstralLeft = 0.0
	GuardStarLeft = 0.0
	Int timerIndex = 0
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
	If StateBroken
		Return
	EndIf
	Int damageIndex = 0
	While damageIndex < 128
		DamageActor[damageIndex] = None
		DamageElement[damageIndex] = 0
		DamageTime[damageIndex] = -1.0
		damageIndex += 1
	EndWhile
	LiftQueued = False
	Int i = 0
	While i < 8
		HitActor[i] = None
		CastActor[i] = None
		KillProcActor[i] = None
		DeadActor[i] = None
		KnockTime[i] = -1000000.0
		PullTime[i] = -1000000.0
		WashTime[i] = -1000000.0
		LiftActor[i] = None
		i += 1
	EndWhile
	i = 0
	While i < 4
		PendingKillActor[i] = None
		i += 1
	EndWhile
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

; 每次有效命中（Papyrus 那一半）：已交戰標記、自身資源的「命中 +1」、各樹命中掛勾、同調與經驗。
; 印記與目標狀態在 DLL（見 OnWeaponHit）；開印那一擊的「開印 +2」由 ESSB_Open 補足（ESSBReactions.Open）。
; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function OnValidHitInternal(Actor akTarget, Int aiElement, Bool abPower)
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	SelfLastHit = Utility.GetCurrentRealTime()
	MarkEngaged(akTarget)
	; 電荷／岩甲／風勢：命中 +1（v0.4 2.3；N4 前在 Papyrus）。
	If aiElement == 3
		AddSelf(1, 1)
	ElseIf aiElement == 4
		AddSelf(2, 1)
	ElseIf aiElement == 5
		AddSelf(3, 1)
	EndIf
	; 5.3 持續專精主線：帶火印記目標火抗 -1%／點。
	If aiElement == 1
		ESSBElem.ApplyFireResistShred(Self, akTarget)
	EndIf
	ElementHitHook(akTarget, aiElement, abPower)
	AddSync(1)
	If Trees
		; 規劃 4：開形態的有效命中給當前元素樹 + 通用樹。
		Trees.AwardInternal(aiElement)
	EndIf
	ScheduleTickInternal(1.0)
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
	Bool eligible = Enabled.GetValueInt() == 1 && FormActive.GetValueInt() == 1 && !DivineSaveUsed && SyncStage() >= 3 && ESSBNodes.Br(Self, 6, 0, 4, 0) ; @node 神佑
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

Float Function BloodBandMult(Int aiBand)
	Int band = aiBand
	If Br(5, 0, 2, 0) ; @node 逆流
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

