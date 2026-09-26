Scriptname ESSBController extends ReferenceAlias
{元素魔戰士 控制器：形態層、同調、融斷的觸發、環境、DLL 事件的 Papyrus 那一半
（規劃 v0.4 第 1、1.1、2.1～2.10、2.13、6.1 節）。

形態切換在同一個腳本幀內完成：移除舊形態能力、加上新形態能力、更新全域變數。
沒有 Utility.Wait、沒有忙等迴圈、沒有每幀輪詢。附傷與所有反應傷害都用
DoCombatSpellApply 套自有法術，不用 Spell.Cast，避免觸發施法事件被其他模組吃掉；
絕不直接 DamageActorValue 生命，讓 Ordinator 等天賦照常成立。

Round 22（N3）起沒有登記表、沒有狀態容器：目標身上的印記、層數、冰封、催毒、死咒、星痕，與你身上的熱度、
聖佑階梯，都是 DLL 掛的引擎效果（native/include/Status.h）。DLL 在命中那一幀決定開印／刷新／被切，做完開印與
終焉的狀態部分；round 24（N5）起反應本體、融斷、死亡處理與所有範圍掃描也在 DLL（native/include/Reactions.h）。
ModEvent 只剩 Papyrus 負責的那一半（裁定 R4）：ESSB_Open／ESSB_End（經驗、終焉特效）、ESSB_Hallucinate（恐懼／瘋狂的 AI）、
ESSB_Knock／ESSB_Push（推力）、ESSB_Ash（化灰崩解）、ESSB_Raise（復生 AI 與召喚上限）、ESSB_Sneak（不解除潛行）、
ESSB_Domain（領域開場特效）、ESSB_SyncUp、ESSB_Cleanse、ESSB_Lethal（神佑）；round 25（N6）起再加 ESSB_Switch（熱鍵與
形態力量的切換：DLL 已判定魔力門檻、寫好全域變數）與 ESSB_Close（魔力歸零 2 秒關閉）。每秒的維持費、長流、環境、雷雨電荷、
沉默扣魔與領域都在 DLL 的計時器（native/include/Timer.h），熱鍵在 DLL 的輸入事件 sink；ESSBFormRules、ESSBInput、
ESSBSilence 三個腳本刪除。
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
; round 25（N6）：環境偵測（天氣、室內、水中、時間）搬進 DLL 計時器，GameHour 屬性拿掉；這三個全域變數由 DLL 寫。

Spell Property SettingsPower Auto
Spell Property EngagedSpell Auto
Spell[] Property FormPowers Auto
Spell[] Property FormAbilities Auto
Spell[] Property HitNormalSpells Auto
Spell[] Property HitPowerSpells Auto
Spell[] Property UtilSpells Auto
Spell[] Property UtilTargetSpells Auto
; Contact variants: RestoreHealth, RestoreStamina, MeleeBuff (allies only).

Keyword Property EngagedKeyword Auto
Keyword Property UndeadKeyword Auto
Keyword Property DaedraKeyword Auto
Keyword[] Property MarkKeywords Auto
{11 個印記關鍵字，索引 0 = 火。判定「帶某元素印記」只讀本模組自己的 keyword（規劃 2.2）。}

; ---------------------------------------------------------------- 機制前線新增

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

GlobalVariable Property GRockArmor Auto
GlobalVariable Property GWind Auto
GlobalVariable Property GHolyShield Auto
GlobalVariable Property GBloodthirst Auto
GlobalVariable Property GGuardWind Auto
GlobalVariable Property GGuardDivine Auto
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
GlobalVariable Property GShockRecent Auto
GlobalVariable Property GGuardSwitch Auto
GlobalVariable Property GGuardBurst Auto
GlobalVariable Property GGuardIce Auto
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
Float[] TrioTimes
Int PerpetualKeep
Actor[] PendingServants
Float[] PendingServantDue
Bool ReanimateBusy




Bool DivineArmed
Actor[] CastActor
Float[] CastAt
Int CastNext

; 自身資源（電荷、岩甲、風勢、戰意、冰盾、同調……）round 23 起是 DLL 掛在你身上的效果（native/include/SelfLayer.h）；
; round 25 起雷雨天氣的 3 秒電荷也在 DLL（Timer.h PlanFormSecond）。
Bool LastHitPower
Int SyncStageShown

Bool Ready
Int Property CachedDebugLevel Auto
Bool Property RuntimeCacheReady Auto
Float Property CachedNodeScale Auto
Float CachedDuration
Int CachedT1
Int CachedT2
Int CachedT3
Bool LiftQueued
Bool Property StateBroken = False Auto
Bool FixInitialised
Bool TablesInitialised
Bool FirstSetupDone

; ---------------------------------------------------------------- 節點狀態（機制前線）

; 無元素樹（戰意與斷咒的冷卻 round 23 起在 DLL）

; 秒計時器（每秒 tick 減 1，歸零時把對應的全域變數寫回 0）
Float EmberLeft
Int EmberElem
Float QuenchLeft
Float ShockLeft
Float GuardSwitchLeft
Float GuardIceLeft
Float SyncKeepLeft
Int SyncKeep
Int PrevElement
Int TwinElement
Float TwinTime

; ---- 機制前線 round 2 的狀態
Int HolyShield
Float GuardWindLeft
Float GuardDivineLeft
Float CloakGuardLeft
Float NoBloodCostLeft
Float KeepSneakLeft
Bool DivineSaveUsed
Bool SneakingNow
Bool SilentOn
; 推力冷卻環（8 格）：kind 0 跌倒／吹飛 8 秒，kind 1 拉近 3 秒（規劃 2.6、8）
Actor[] KnockActor
Float[] KnockTime
Float[] PullTime
Float[] WashTime
Int KnockNext

; 領域 round 25（N6）起是引擎的 hazard（DLL 在融斷目標腳下放 Spawn Hazard 法術，引擎管壽命與數量；對你與對內部敵人的
; 每秒效果在 DLL 計時器，native/include/Timer.h）；這裡不再有三格表。

; ---- 機制前線 round 3 的狀態
Int WaterMirror
Float GuardDarkLeft
Float GuardAstralLeft
Float GuardStarLeft
Int AstralHits

; ---- 特效前線的狀態：爆炸預算（規劃 2.12「範圍事件最多播 5 個目標的特效」）
Int FxBudget
Float FxBudgetTime

; 切換／終焉的一次性旗標（協奏、三重奏、極致 round 23 起在 DLL）
Bool InSpread
Int TrioMask
Float TrioTime
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

; 推力冷卻環（round 22 起沒有目標登記表；round 25 起領域是引擎的 hazard）。
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
	; round 24（N5）：擊殺事件（ESSBGuard 的 OnActorKilled）整個刪除，死亡處理在 DLL 的死亡 sink（裁定 R4）。
	CachedDebugLevel = DebugLevel.GetValueInt()
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
	; 基礎規則天賦（血形態重擊改扣生命、岩甲物理減傷）：不是節點，開局加一次就不再動。
	If HitProcPerk && !player.HasPerk(HitProcPerk)
		player.AddPerk(HitProcPerk)
	EndIf
	If BaseRulesPerk && !player.HasPerk(BaseRulesPerk)
		player.AddPerk(BaseRulesPerk)
	EndIf
	RefreshTrees()
	RefreshAbilities()
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
	PO3_Events_Alias.RegisterForWeaponHit(Self)
	; DLL → Papyrus（round 22 起）。ModEvent 的登記不隨存檔保存，每次載入由這裡重登。
	; round 24（N5）：反應本體（冰封、聖裁、濺血、越線、碎冰、落地、放電、風刃、死亡）全在 DLL，這裡只剩經驗與特效
	;（開印、終焉）、推力、幻術 AI、化灰崩解、復生、不解除潛行、領域的開場特效、同調升段、洗淨、神佑（裁定 R4）；
	; round 25（N6）：熱鍵／形態力量的切換與魔力歸零的關閉。
	RegisterForModEvent("ESSB_Open", "OnESSBOpen")
	RegisterForModEvent("ESSB_End", "OnESSBEnd")
	RegisterForModEvent("ESSB_Hallucinate", "OnESSBHallucinate")
	RegisterForModEvent("ESSB_Knock", "OnESSBKnock")
	RegisterForModEvent("ESSB_Push", "OnESSBPush")
	RegisterForModEvent("ESSB_Ash", "OnESSBAsh")
	RegisterForModEvent("ESSB_Raise", "OnESSBRaise")
	RegisterForModEvent("ESSB_Sneak", "OnESSBSneak")
	RegisterForModEvent("ESSB_Domain", "OnESSBDomain")
	RegisterForModEvent("ESSB_SyncUp", "OnESSBSyncUp")
	RegisterForModEvent("ESSB_Cleanse", "OnESSBCleanse")
	RegisterForModEvent("ESSB_Lethal", "OnESSBLethal")
	RegisterForModEvent("ESSB_Switch", "OnESSBSwitch")
	RegisterForModEvent("ESSB_Close", "OnESSBClose")
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
	If (SyncKeepLeft > 0 && SyncKeepLeft > Now()) && SyncKeep > keep
		keep = SyncKeep
	EndIf
	If PerpetualKeep > keep
		keep = PerpetualKeep
	EndIf
	PerpetualKeep = 0
	SyncKeep = 0
	SyncKeepLeft = 0
	; round 23 (N4)：同調是 DLL 掛在你身上的效果（ESSB_N4_Sync，鏡射 ESSB_Sync）。保留的份交給 DLL，不算升段、不給回饋。
	ESSBNative.SetSync(keep)
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
	; 規劃 2.3：疊在你身上的狀態，離開形態時清空（你的資源由 DLL 在離開形態時清，見 FormLeave）。
	ClearSelfAll()
	; 規劃 2.12 第 1 列：開形態一次 FormActive 音（光環淡入由形態能力的 MGEF 自己播）。
	If FormSound && FormSound.GetValueInt() == 1
		PlayFormSound(FxSoundFormActive, aiIndex)
	EndIf
	FormOpenTime = Utility.GetCurrentRealTime()
	; round 23 (N4)：DLL 的開形態：專一的計時、雷臨強化（+5 電荷）、地臨強化（岩甲滿層）。
	; round 24 (N5)：同一個原生函式做各元素的「臨」（範圍內敵人開印）、臨強化、臨界、雙斷的再開印（Reactions.h PlanAdvent）。
	ESSBNative.FormEnter(aiIndex)
	RefreshAbilities()
	; 留在 Papyrus 的開形態附加效果：氣旋（推力）、聖臨強化（你與同伴的治療）。
	ESSBElem.OnFormOpenedExtra(Self, aiIndex)
EndFunction

Function OnFormSwitched(Int aiOldIndex, Int aiNewIndex)
	; DLL：離開舊形態的自身階梯（熱度洩壓、熔心、餘壓、聖佑清空、神聖領域）與你的資源（round 23：電荷的切換快照、
	; 過載終焉、墜星、星殘、協奏的「切換後首次終焉」、護血清空）。
	ESSBNative.FormLeave(aiOldIndex, False)
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
	; 5.2 關閉大師分支「協奏」與傳奇分支「大協奏」：切換後首次終焉由 DLL 記在你身上（ESSB_N4_Concert），終焉事件帶旗標。
	; 5.2 關閉傳奇分支「雙生」：雙持時左手武器攜帶前一個形態的元素 30 秒。
	If ESSBNodes.HasTwin(Self)
		TwinElement = aiOldIndex
		TwinTime = Now()
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
	; round 24（N5）：融斷整個在 DLL（Reactions.h PlanBurst）：一次掃描（15 公尺、收束 20 公尺 +0.3 公尺／點），範圍內每個
	; 帶印記的目標每個印記以自己的終焉本體 × K_sync × 融斷主線結清，寂、萬寂、斷界、回流、雙斷、安全閥、地斷、颶風、
	; 墜星的融斷那一半都在同一個計畫；推力與領域經 ESSB_Push／ESSB_Domain 回來。
	; 審查修正 1：原生函式只排進 DLL 的主執行緒 task 就回來（掃描與施放都在 task 裡）；目標數寫在 DLL 的 [burst] 行。
	ESSBNative.Burst(aiIndex)
	; DLL：離開形態的自身階梯（熱度洩壓、熔心、餘壓、聖佑清空、神聖領域）。
	ESSBNative.FormLeave(aiIndex, True)
	If CachedDebugLevel >= 1
		LogEvent(1, "burst", "queued stage=" + stage)
	EndIf

	; 5.2 持續傳奇分支「永續」：Z 關閉時若同調三段，融斷後保留一段同調到下一次開形態。
	If stage >= 3 && ESSBNodes.HasPerpetual(Self)
		Int t1 = 5
		If SyncT1
			t1 = SyncT1.GetValueInt()
		EndIf
		PerpetualKeep = t1
	EndIf
	; 5.2 安全閥（融斷時你受傷 -50% 2 秒）round 24 起是 DLL 掛在你身上的 ESSB_N5_SafetyValve，PERK 讀它。
	; 5.1 冷寂路線的收尾（免門檻、連斷；回流與雙斷 round 24 起在 DLL）。
	ESSBNoForm.OnBurst(Self, syncBefore)
	; 5.2 關閉專精分支「三重奏」：DLL 在第三種元素的終焉留下 60 秒的「下一次融斷保留全部同調」（碼 51）。
	Actor closer = ThePlayer()
	If closer && ESSBNative.GetStatus(closer, 51) > 0
		SetSyncKeep(syncBefore, 60)
		ESSBNative.ClearStatus(closer, 51)
	EndIf

	; round 23 (N4)：融斷後同調歸零（DLL 的效果）；保留的份在下一次開形態時由 SwitchForm 交給 DLL。
	ESSBNative.SetSync(0)
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
	Int hitElement = 0
	Bool hitActive = FormActive.GetValueInt() == 1
	If hitActive
		hitElement = CurrentElement.GetValueInt()
	EndIf
	If targetActor.IsDead()
		If CachedDebugLevel >= 3
			LogRejectedHit("invalid-actor", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)
		EndIf
		; Engine weapon damage already killed it: never send corpse damage/open marks. Round 24 (N5): the kill itself
		; (連殺 with the DLL's last-hit-sneak marker, and every other death effect) is the DLL's death sink; a dead
		; target never opens, so the round-16 lethal-ambush blades are gone (v0.4 奇襲 needs an open).
		If sneak && hitElement == 5
			SetSelf(3, ESSBElem2.WindThreshold(Self))
		EndIf
		Return
	EndIf
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
	If leftHand && TwinElement >= 1 && Now() - TwinTime <= DurationSeconds(30.0)
		element = TwinElement
	EndIf

	; Round 22 (N3): the DLL does the whole hit in the hit frame -- the proc with its magnitude and every target-side
	; multiplier read from the target's effects, and the mark: open / refresh / cut, layers and ladders (and the twin
	; element's proc and mark for a 雙生 left-hand hit). Open and end reactions come back as ModEvents (OnESSBOpen /
	; OnESSBEnd). Round 23 (N4): your resources too -- the self counters and sync, 極致, the blood power cost, 順勢,
	; 雷暴, 雷霆 (SelfLayer.h); their bodies come back as ESSB_Discharge / ESSB_Blade / ESSB_Knock.

	If CachedDebugLevel >= 2
		If CachedDebugLevel >= 2
			LogThrottled(2, "hit", targetActor.GetFormID() + " element=" + element + " weapon=" + weaponType \
				+ " power=" + power + " left=" + leftHand + " flags=" + aiHitFlagMask + " sync=" + Sync.GetValueInt())
		EndIf
	EndIf
	OnValidHitInternal(targetActor, element, power)
EndEvent

; 關形態的有效命中（規劃 5.1）。基準真傷、吸魔、小滅法、滅法與它們的節點（含反擊的吸魔 ×2）由 DLL 在命中
; 當下施放；round 23 起斷咒（讀目標的施法狀態、打斷、戰意）也在 DLL。這裡只剩已交戰標記。
; v0.3 純武藝路線（連段、節奏、疾攻、重擊碎甲、暴擊、終結、處決）與融斷路線的「餘燼」隨 v0.4 的法殺樹拿掉。
Function OnNoFormHit(Actor akTarget, Weapon akWeapon, Bool abPower)
	MarkEngaged(akTarget)
EndFunction

Bool Function LastHitWasPower()
	Return LastHitPower
EndFunction

; 只掛印記、不做開印反應（傳導、聖輝、暗染、星散、風襲、灼身、靜電……「附近 1 人也帶印記」）。
Function ApplyMark(Actor akTarget, Int aiElement)
	If akTarget && aiElement >= 1 && aiElement <= 11
		ESSBNative.ApplyMark(akTarget, aiElement)
	EndIf
EndFunction

; ---------------------------------------------------------------- 傷害與法術套用封裝

; 破魔印 8 秒（ESSBCounter）。
Function ApplyManaBreakMark(Actor akTarget)
	Actor player = ThePlayer()
	If player && ManaBreakSpell && akTarget
		ManaBreakSpell.SetNthEffectDuration(0, DurationInt(8))
		player.DoCombatSpellApply(ManaBreakSpell, akTarget)
	EndIf
EndFunction

; 反咒（v0.4 5.1）round 23 起由 DLL 的施法事件判定（施法者帶破魔印時受該次施法消耗的真實傷害，Hurt.h PlanSpellCast）；
; 施法動畫事件的登記（StartCounter／StopCounter／OnAnimationEvent）與斷咒用的最近施法紀錄一起刪除。

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
	player.DoCombatSpellApply(utilSpell, akTarget)
EndFunction

; ---------------------------------------------------------------- 公式掛勾

; 反應基準 B_max（settings.json element_damage 的上限欄 → QUST VMAD，規劃 2.7）。round 24：反應本體搬進 DLL、
; ESSBReactions 刪除後，Papyrus 還在用的只有領域的每秒傷害與聖臨強化的治療量。
Float Function BaseMax(Int aiElement)
	If aiElement < 1 || aiElement > 11
		Return 0.0
	EndIf
	Return ElementDamageMax[aiElement - 1]
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
	; round 23：v0.3 的岩甲常駐能力退役（岩甲的護甲是 DLL 的效果，不吃回復倍率）。
	If UtilSpells && UtilSpells[18]
		player.RemoveSpell(UtilSpells[18])
	EndIf
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

; 重擊一次的損血（占最大生命）。
Float Function BloodPowerCost()
	Actor player = ThePlayer()
	If !player
		Return 0.0
	EndIf
	Return BloodDrainCurve(player.GetActorValuePercentage("Health"), True)
EndFunction

; ---------------------------------------------------------------- 同調

; round 23 (N4)：同調是 DLL 掛在你身上的效果；命中 +1、開印的同調、門檻（同調門檻、專一）、升段的 ESSB_SyncUp 與
; 回饋都在 DLL（SelfLayer.h、Status.h res::SetSync）。這裡只剩 Papyrus 自己還要加的（目前沒有呼叫者時也保留入口）。
Function AddSync(Int aiAmount)
	Actor player = ThePlayer()
	If player && aiAmount > 0
		ESSBNative.AddStatus(player, 40, aiAmount)
	EndIf
EndFunction

; 同調升段：光暈與武器發光屬特效前線，這裡先送模組事件與紀錄。
Function OnSyncStage(Int aiStage)
	PushSyncStage()
	; 規劃 2.12「同調升段：Charge_X」。光暈與三段武器發光是引擎側的：三個
	; ESSB_SyncGlowEffect_n 與 ESSB_SyncWeaponEffect_<X> 掛在形態能力的效果層上，
	; 條件是 CTDA GetGlobalValue(ESSB_SyncStage) >= n，PushSyncStage 寫完就生效。
	PlayFormSound(FxSoundCharge, CurrentElement.GetValueInt())
	SendModEvent("ESSB_SyncStage", "stage", aiStage as Float)
	; 5.2 持續大師分支「回饋」（升段回生命與魔力各 B_max ×2）round 23 起由 DLL 在升段那一刻給。
	If CachedDebugLevel >= 1
		LogEvent(1, "sync", "stage=" + aiStage + " value=" + Sync.GetValueInt() \
			+ " element=" + CurrentElement.GetValueInt())
	EndIf
	RefreshSyncStage()
	RefreshDivineProtection()
EndFunction

; 樣式 C 的鏡射：同調段數（ESSB_SyncStage）round 23 起由 DLL 依同調效果寫；這裡只更新快取。
Function PushSyncStage()
	RefreshSyncStage()
EndFunction

; ---------------------------------------------------------------- 自身資源

; round 23 (N4)：電荷、岩甲、風勢是 DLL 掛在你身上的效果（計數＝效果強度，DLL 鏡射到 ESSB_Charge／ESSB_RockArmor／
; ESSB_Wind）。Papyrus 還要讀寫的地方（雷雨加電荷、先雷與雷殛讀電荷、致命潛行的風勢滿格）經 ESSBNative 的玩家碼
; 42／43／44。aiKind：1 電荷 2 岩甲 3 風勢。
Int Function SelfCode(Int aiKind)
	If aiKind == 1
		Return 42
	ElseIf aiKind == 2
		Return 43
	ElseIf aiKind == 3
		Return 44
	EndIf
	Return 0
EndFunction

; 樣式 C 的鏡射：v0.3 的聖盾層數（電荷、冰盾、戰意、岩甲、風勢的鏡射 round 23 起由 DLL 寫）。
Function PushSelf()
	SetGlobal(GHolyShield, HolyShield)
EndFunction

Int Function GetSelf(Int aiKind)
	Actor player = ThePlayer()
	Int code = SelfCode(aiKind)
	If !player || code <= 0
		Return 0
	EndIf
	Return ESSBNative.GetStatus(player, code)
EndFunction

Function ClearSelf(Int aiKind)
	SetSelf(aiKind, 0)
EndFunction

; 離開形態時 Papyrus 自己的部分（你的資源由 DLL 在 FormLeave 清）。
Function ClearSelfAll()
	HolyShield = 0
	; round 3：水鏡層與追擊的命中計數也是「疊在你身上」的資源，離開形態清空（規劃 2.3）。
	WaterMirror = 0
	AstralHits = 0
	SetGlobal(GWaterMirror, 0)
	PushSelf()
	RefreshSyncStage()
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

; round 23：岩甲的護甲是 DLL 掛的效果（ESSB_N4_RockArmorAVEffect）；v0.3 的岩甲常駐能力（UtilSpells[18]）退役，
; 載入時拿掉（ReconcileLoadedForm、RefreshRecovery）。

; 直接設定自身資源的絕對層數（致命潛行的風勢滿格）。
Function SetSelf(Int aiKind, Int aiValue)
	Actor player = ThePlayer()
	Int code = SelfCode(aiKind)
	If player && code > 0
		ESSBNative.SetStatus(player, code, aiValue)
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

; 2.9 必要角色（審查修正 2）：essential 的角色（參照或本體）。只有它們不會被跌倒、復生、化灰；有名字的（unique／protected）
; 敵人不豁免（首領的碎冰、沉默減半、血潮 3% 照舊讀 IsVIPTarget）。任務物件別名由 DLL 判定（Papyrus 讀不到）。
Bool Function IsEssentialTarget(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	If akTarget.IsEssential()
		Return True
	EndIf
	ActorBase base = akTarget.GetActorBase()
	Return base && base.IsEssential()
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
	; 自身資源的衰減（風勢 5 秒、電荷 10 秒未命中歸零、戰意 10 秒）是 DLL 效果的時長（round 23）。

	; 雷雨天氣的每 3 秒電荷（規劃 2.10）round 25 起在 DLL 計時器（Timer.h PlanFormSecond）。

	RefreshDivineProtection()
	TickTimers()
	; 印記與目標狀態的過期由 DLL 讀引擎效果的時長結算（ESSB_End 理由 2）；死亡處理 round 24 起在 DLL 的死亡 sink。

	; 5.2 持續傳奇主線「化身」是 DLL N4（冷卻後的下一次命中觸發該元素的持續傳奇；被動數值改為 10 秒視同已取得）。
	; v0.3「每 N 秒自動施放一次」的近似已拿掉。

	; 各元素樹的每秒掛勾（毒形態的以毒攻毒、百毒不侵；冰心與雷神 round 23 起、長流與長河 round 25 起在 DLL）。
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

	; 環境偵測（規劃 2.10，每 5 秒）round 25 起在 DLL 計時器，結果照舊寫進 ESSB_EnvWet／EnvStormy／EnvNight。

	Float delay = 5.0
	If FormActive.GetValueInt() == 1 || TimersActive()
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
	Float now = Now()
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
	If GuardIceLeft > 0
		If now >= GuardIceLeft
			GuardIceLeft = 0.0
		EndIf
		SetGlobal(GGuardIce, SecondsLeft(GuardIceLeft))
	EndIf
	; ---- round 2 的秒計時器
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
	RefreshSyncStage()
	If oldStage != CachedSyncStage
		PushSyncStage()
		RefreshDivineProtection()
	EndIf
EndFunction

Bool Function TimersActive()
	If (EmberLeft > 0 && EmberLeft > Now()) || (QuenchLeft > 0 && QuenchLeft > Now()) || (ShockLeft > 0 && ShockLeft > Now())
		Return True
	EndIf
	If (GuardDarkLeft > 0 && GuardDarkLeft > Now()) || (GuardAstralLeft > 0 && GuardAstralLeft > Now()) || (GuardStarLeft > 0 && GuardStarLeft > Now()) || WaterMirror > 0
		Return True
	EndIf
	If (GuardSwitchLeft > 0 && GuardSwitchLeft > Now()) || (GuardIceLeft > 0 && GuardIceLeft > Now()) || (SyncKeepLeft > 0 && SyncKeepLeft > Now())
		Return True
	EndIf
	If (GuardWindLeft > 0 && GuardWindLeft > Now()) || (GuardDivineLeft > 0 && GuardDivineLeft > Now()) || (CloakGuardLeft > 0 && CloakGuardLeft > Now())
		Return True
	EndIf
	Return (NoBloodCostLeft > 0 && NoBloodCostLeft > Now()) || (KeepSneakLeft > 0 && KeepSneakLeft > Now()) 		|| DivineSaveUsed
EndFunction

Function SetGlobal(GlobalVariable akGlobal, Int aiValue)
	If akGlobal && akGlobal.GetValueInt() != aiValue
		akGlobal.SetValueInt(aiValue)
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

; 戰意（無元素）與冰盾（冰）round 23 起是 DLL 掛在你身上的效果（玩家碼 45、46），這裡不再有存取器。

Function SetEmber(Int aiSeconds, Int aiElement)
	aiSeconds = DurationInt(aiSeconds)
	EmberLeft = Now() + aiSeconds
	EmberElem = aiElement
	SetGlobal(GEmber, SecondsLeft(EmberLeft))
EndFunction

Int Function GetEmberLeft()
	Return SecondsLeft(EmberLeft)
EndFunction

Function SetQuench(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	QuenchLeft = Now() + aiSeconds
	SetGlobal(GQuench, SecondsLeft(QuenchLeft))
EndFunction

Function SetShockRecent(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	ShockLeft = Now() + aiSeconds
	SetGlobal(GShockRecent, SecondsLeft(ShockLeft))
EndFunction

Function SetGuardSwitch(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardSwitchLeft = Now() + aiSeconds
	SetGlobal(GGuardSwitch, SecondsLeft(GuardSwitchLeft))
	ApplyGuardWindow(0, GuardSwitchLeft)
EndFunction

Function SetGuardIce(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardIceLeft = Now() + aiSeconds
	SetGlobal(GGuardIce, SecondsLeft(GuardIceLeft))
	ApplyGuardWindow(2, GuardIceLeft)
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

; ---- 同調保留（承接／連斷／永續／三重奏）
Function SetSyncKeep(Int aiValue, Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If aiValue > SyncKeep
		SyncKeep = aiValue
	EndIf
	SyncKeepLeft = Now() + aiSeconds
EndFunction

; 協奏／大協奏的「切換後首次終焉」與三重奏的逐元素標記 round 23 起是 DLL 掛在你身上的效果（終焉事件帶旗標、倍率已乘）。

; 斷咒、冰心、反震、洗淨的冷卻 round 23 起是 DLL 掛在你身上的效果（ESSB_N4_*Cooldown）。

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

; 殘影（5.7）與破護（5.1）的視窗 round 23 起是 DLL 在受擊時掛的效果（ESSB_N4_AfterimageEffect、ESSB_N4_CloakGuardEffect），
; PERK 直接讀它們；ESSB_GuardWind／ESSB_CloakGuard 視窗不再開。

Function SetGuardDivine(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardDivineLeft = Now() + aiSeconds
	SetGlobal(GGuardDivine, SecondsLeft(GuardDivineLeft))
	ApplyGuardWindow(4, GuardDivineLeft)
EndFunction

Function SetNoBloodCost(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	If Now() + aiSeconds > NoBloodCostLeft
		NoBloodCostLeft = Now() + aiSeconds
	EndIf
	SetGlobal(GNoBloodCost, SecondsLeft(NoBloodCostLeft))
EndFunction

; 順勢（5.7）的 5 秒與反擊（5.1）的格擋偵測、3 秒視窗 round 23 起都在 DLL。

; 5.7 關閉傳奇分支「連殺」：擊殺後 5 秒內不解除潛行；下一次潛行攻擊 ×2 是 DLL 讀的連殺效果（ESSBElem2.TryKillStreak）。
Function KeepSneak(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	KeepSneakLeft = Now() + aiSeconds
	Actor player = ThePlayer()
	If player
		; 規劃 8：用「壓低偵測值」實作，尊重原版偵測系統，不鎖 AI。
		PO3_SKSEFunctions.PreventActorDetection(player)
	EndIf
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
	GuardDarkLeft = Now() + aiSeconds
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
	If Now() + aiSeconds > GuardAstralLeft
		GuardAstralLeft = Now() + aiSeconds
	EndIf
	SetGlobal(GGuardAstral, SecondsLeft(GuardAstralLeft))
	ApplyGuardWindow(7, GuardAstralLeft)
EndFunction

Function SetGuardStar(Int aiSeconds)
	aiSeconds = DurationInt(aiSeconds)
	GuardStarLeft = Now() + aiSeconds
	SetGlobal(GGuardStar, SecondsLeft(GuardStarLeft))
	ApplyGuardWindow(8, GuardStarLeft)
EndFunction

; ---- 星界之門（5.13 關閉大師分支）：接管元素直接視為同調一段
; ---- 追擊（5.13 持續熟練分支）：每第 3 次命中。滿 3 就歸零並回傳 3。
Int Function BumpAstralHits()
	AstralHits += 1
	If AstralHits >= 3
		AstralHits = 0
		Return 3
	EndIf
	Return AstralHits
EndFunction

; ---- 洗淨／淨化（5.11）：DLL 在水的命中判定（每 3 秒一次）與潮身，送 ESSB_Cleanse 回來由這裡清。
; 規劃 8：不用原版 Dispel 對自己施放（會洗掉自己的增益），改用限定關鍵字的 Dispel。
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
	If IsEssentialTarget(akTarget)
		If CachedDebugLevel >= 2
			LogThrottled(2, "reanimate-reject", "reason=can-reanimate-essential")
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

Bool Function ApplyReanimate(Actor akTarget, Int aiLevelCap, Int aiSeconds, Float afAttack = 0.0)
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
	; 審查修正 3：僕從攻擊加成是同一個法術的第二個效果（AttackDamageMult 的 Peak Value Modifier）：跟復生一起結束，
	; 再復生一次是重新套用，不會疊加；0 就是沒有加成。
	ReanimateSpell.SetNthEffectMagnitude(1, afAttack)
	ReanimateSpell.SetNthEffectDuration(1, DurationInt(aiSeconds))
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

Bool Function ApplyAsh(Actor akTarget)
	Actor player = ThePlayer()
	If !player || !AshSpell || !akTarget
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-missing-player-spell-target")
		EndIf
		Return False
	EndIf
	; 規劃 8：龍不受崩解，原版即如此；必要角色也不化灰（規劃 2.9 的例外欄；有名字的敵人照樣化灰，審查修正 2）。
	If DragonKeyword && akTarget.HasKeyword(DragonKeyword)
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-dragon")
		EndIf
		Return False
	EndIf
	If IsEssentialTarget(akTarget)
		If CachedDebugLevel >= 2
			LogThrottled(2, "ash-reject", "reason=apply-essential")
		EndIf
		Return False
	EndIf
	AshSpell.SetNthEffectMagnitude(0, akTarget.GetActorValueMax("Health") + 100.0)
	player.DoCombatSpellApply(AshSpell, akTarget)
	Return True
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

; ESSB_Open：元素、開印倍率、這一擊切掉的元素（0 = 沒有）、1 = 命中開的印（強制開印是 0）。
; round 24（N5）：開印的本體與各樹開印分支在 DLL（Reactions.h Bodies::Open）；這裡只給經驗（規劃 4）。
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
	If CachedDebugLevel >= 1
		LogThrottled(1, "open", target.GetFormID() + " element=" + element + " mult=" + EventArg(args, 1) + " cut=" + (EventArg(args, 2) as Int))
	EndIf
EndEvent

; ESSB_End：元素、理由（0 被切 1 融斷 2 過期）、終焉倍率（round 23：已乘協奏、三重奏、過載終焉）、旗標（1 連鎖終焉、
; 2 切換後首次終焉）、三個 DLL 算好的值、雷終焉放電用的電荷（本體在 DLL 讀這些值，Papyrus 只讀元素、理由、倍率、旗標）。
; round 24（N5）：終焉的本體、各樹終焉分支、連鎖終焉、大協奏、反哺都在 DLL（Reactions.h Bodies::End）；這裡只給經驗
;（規劃 4）與放終焉的爆炸特效（規劃 2.12，每 0.5 秒 5 個的預算在 PlaceFx）。
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
	If Trees
		Trees.OnEndXP(element)
	EndIf
	PlaceFx(element, target)
	If CachedDebugLevel >= 1
		Int flags = (EventArg(args, 3) + 0.5) as Int
		LogThrottled(1, "end", target.GetFormID() + " element=" + element + " reason=" + (EventArg(args, 1) as Int) \
			+ " mult=" + EventArg(args, 2) + " chain=" + (Math.LogicalAnd(flags, 1) != 0))
	EndIf
EndEvent

; ---------------------------------------------------------------- round 23 (N4)：你的資源與受擊的本體

; ESSB_Knock：推力（碎岩、反震 3.0，地動 2.0）。跌倒的推力與每目標 8 秒冷卻在 Knockdown；推不倒（龍、騎乘、必要角色）的
; 反震改為減速 30% 3 秒（原本 OnEarthRetaliate 的做法）。
Event OnESSBKnock(String asEventName, String asArgs, Float afForce, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	If !Knockdown(target, afForce) && afForce >= 3.0
		ApplyUtil(0, 30.0, 3, target)
	EndIf
EndEvent

; ESSB_SyncUp：同調升到第 N 段（音效、ESSB_SyncStage 模組事件、神佑的資格；回饋已由 DLL 給）。
Event OnESSBSyncUp(String asEventName, String asArgs, Float afStage, Form akSender)
	If !IsOperational()
		Return
	EndIf
	Int stage = (afStage + 0.5) as Int
	If stage > SyncStageShown
		SyncStageShown = stage
		OnSyncStage(stage)
	EndIf
EndEvent

; ESSB_Cleanse：洗淨（1 = 淨化：清除全部負面效果；0 = 清一個）。DLL 已判定冷卻（洗淨 3 秒、潮身 30 秒）。
Event OnESSBCleanse(String asEventName, String asArgs, Float afPurge, Form akSender)
	If !IsOperational()
		Return
	EndIf
	ApplyCleanse(afPurge > 0.5)
EndEvent

; ESSB_Lethal：你這一擊被打到 0 以下（DLL 受擊 task 讀的生命）；神佑的延遲死亡在這裡結算。
Event OnESSBLethal(String asEventName, String asArgs, Float afUnused, Form akSender)
	If !IsCurrentController()
		Return
	EndIf
	OnLethalHitWhileArmed()
EndEvent

; ESSB_Hallucinate：1 恐懼 / 2 瘋狂、秒數（DLL 已比過詛咒門檻與冷卻、乘過持續時間）、1 = 群體（群魔、亡魂、暗臨強化）。
; 控不到的目標改為 3 秒幻視：攻擊 -20%（v0.4 5.12，只給詛咒階梯本身）；群體的那一份控不到就跳過。
; round 24（N5）：夢魘（恐懼時 3 公尺內詛咒 +1）與群魔（4 公尺內一起瘋狂）的範圍在 DLL（Reactions.h Bodies::Hallucinate）。
Event OnESSBHallucinate(String asEventName, String asArgs, Float afKind, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int kind = EventArg(args, 0) as Int
	Float seconds = EventArg(args, 1)
	If !CanCharm(target)
		If EventArg(args, 2) > 0.5
			Return
		EndIf
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
	Else
		ApplyFear(target, whole, True)
	EndIf
EndEvent

; ---------------------------------------------------------------- round 24 (N5)：DLL 的本體留給 Papyrus 的那一半（裁定 R4）

; ESSB_Push：種類（1 吹飛、2 拉近你、3 拉向中心、4 吹上天）、公尺、落地傷害（吹上天：B_max × 落地倍率，G 與目標倍率在
; 落地時由 DLL 乘）、中心的 FormID（風渦：被終焉的目標）、1 = 推不動時減速 30% 3 秒（吹飛、吹上天、颶風）。
; 推力的每目標冷卻與免疫名單照舊在 Knockdown／BlowBack／PullTo／LiftUp。
Event OnESSBPush(String asEventName, String asArgs, Float afKind, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target || target.IsDead()
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int kind = (EventArg(args, 0) + 0.5) as Int
	Float metres = EventArg(args, 1)
	Bool pushed = False
	If kind == 1
		pushed = BlowBack(target, metres)
	ElseIf kind == 2
		pushed = PullIn(target, metres)
	ElseIf kind == 3
		ObjectReference centre = None
		If args && args.Length > 3
			centre = Game.GetForm(args[3] as Int) as ObjectReference
		EndIf
		If centre
			pushed = PullTo(target, centre, metres)
		EndIf
	ElseIf kind == 4
		pushed = LiftUp(target, metres, EventArg(args, 2))
	EndIf
	If !pushed && EventArg(args, 4) > 0.5
		ApplyUtil(0, 30.0, 3, target)
	EndIf
EndEvent

; ESSB_Ash：化灰（DLL 的死亡 sink 判定：帶神聖印記死亡，或淨土）。崩解是 Papyrus 的法術（龍與必要角色 DLL 已排除，
; ApplyAsh 再擋一次）；聖灰、淨灰在 DLL。
Event OnESSBAsh(String asEventName, String asArgs, Float afUnused, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target
		Return
	EndIf
	If ApplyAsh(target) && CachedDebugLevel >= 1
		LogThrottled(1, "ash", target.GetFormID() + " turned to ash")
	EndIf
EndEvent

; ESSB_Raise：亡者歸來（DLL 判定：階、等級上限、秒數、僕從攻擊加成、1 = 死靈主的永久）。復生的 AI、召喚上限與
; 不可復生的名單在 ApplyReanimate／CanReanimate（裁定 R4）。
Event OnESSBRaise(String asEventName, String asArgs, Float afTier, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int levelCap = (EventArg(args, 1) + 0.5) as Int
	Int seconds = (EventArg(args, 2) + 0.5) as Int
	Float attack = EventArg(args, 3)
	If !CanReanimate(target)
		Return
	EndIf
	; 詛咒 5 層以上每層僕從攻擊 +10%（v0.4 5.12）：復生法術的第二個效果（審查修正 3，不改角色本身的數值）。
	ApplyReanimate(target, levelCap, seconds, attack)
EndEvent

; ESSB_Sneak：連殺（風印記目標被你的潛行攻擊殺死）：秒數內不解除潛行（DLL 已乘持續時間；下一次潛行攻擊 ×2 是 DLL 的視窗）。
Event OnESSBSneak(String asEventName, String asArgs, Float afSeconds, Form akSender)
	If !IsOperational()
		Return
	EndIf
	KeepSneak(UnscaledSeconds(afSeconds))
EndEvent

; ESSB_Domain：融斷（與聖域）留下的領域：元素、秒數（未乘持續時間）、半徑。round 25（N6，裁定 R4）：領域本身是引擎的
; hazard，DLL 已在目標腳下放好（Spawn Hazard，引擎管壽命與數量）；這裡只放一次該元素的開場爆炸特效（規劃 2.12）。
Event OnESSBDomain(String asEventName, String asArgs, Float afElement, Form akSender)
	Actor target = akSender as Actor
	If !IsOperational() || !target
		Return
	EndIf
	String[] args = StringUtil.Split(asArgs, "|")
	Int element = (EventArg(args, 0) + 0.5) as Int
	If element < 1 || element > 11
		Return
	EndIf
	PlaceFx(element, target)
	If CachedDebugLevel >= 1
		LogEvent(1, "domain", "placed element=" + element + " sec=" + ((EventArg(args, 1) + 0.5) as Int) + " target=" + target.GetFormID())
	EndIf
EndEvent

; ESSB_Switch（round 25，裁定 R6）：熱鍵或形態力量要切換（元素、1 = 從沒有形態開啟）。DLL 已判定魔力門檻（血形態、順轉、
; 免門檻例外）、寫好 ESSB_CurrentElement／ESSB_FormActive、用掉免門檻並顯示提示；這裡照規劃 1.1 換形態（能力、同調保留、
; 關閉時的融斷）。
Event OnESSBSwitch(String asEventName, String asArgs, Float afElement, Form akSender)
	If !IsOperational()
		Return
	EndIf
	SwitchForm((afElement + 0.5) as Int)
EndEvent

; ESSB_Close（round 25）：魔力歸零持續 2 秒（DLL 計時器判定，規劃 1.1），關閉形態。
Event OnESSBClose(String asEventName, String asArgs, Float afUnused, Form akSender)
	If !IsOperational() || FormActive.GetValueInt() != 1
		Return
	EndIf
	CloseForm()
	Debug.Notification("魔力耗盡，形態已關閉")
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
		+ " charge=" + GetSelf(1) + " rock=" + GetSelf(2) + " wind=" + GetSelf(3) \
		+ " resolve=" + ESSBNative.GetStatus(player, 45) + " ice=" + ESSBNative.GetStatus(player, 46) \
		+ " resonance=" + ESSBNative.GetStatus(player, 47) + " cosmos=" + ESSBNative.GetStatus(player, 48) \
		+ " overload=" + ESSBNative.GetStatusFloat(player, 49) + " force=" + ESSBNative.GetStatus(player, 50) \
		+ " guard=" + ESSBNative.GetStatusFloat(player, 58) \
		+ " heat=" + ESSBNative.GetStatus(player, 20) + " holy=" + ESSBNative.GetStatus(player, 21) \
		+ " molten=" + ESSBNative.GetStatus(player, 22) \
		+ " wet=" + IsEnvWet() + " stormy=" + IsEnvStormy() + " night=" + IsEnvNight())
	; 審查修正 1：帶印記目標的清單由 DLL 在主執行緒 task 裡掃描、寫進 DLL log（[ESSB][dump][L0] target=…）。
	ESSBNative.DumpTargets(3500.0)
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
	Debug.MessageBox("元素魔戰士：附近帶印記的目標列在 ElementsSpellblade.log\n最近的目標 " + shown)
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

; 雷終焉放電用的電荷（被切＝切換當下的快照、融斷／過期＝當下的）與它的消耗（蓄餘不消耗）round 23 起由 DLL 決定，
; 隨 ESSB_End 的第 8 個值帶來。

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
	If !SettingsPower
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
	Return True
EndFunction

Function ReconcileLoadedForm(Actor player)
	; A fresh schema has no combat state. Keep GLOB progression/settings and perks.
	FormActive.SetValueInt(0)
	CurrentElement.SetValueInt(0)
	Sync.SetValueInt(0)
	GWaterMirror.SetValueInt(0)
	GGuardDark.SetValueInt(0)
	GGuardAstral.SetValueInt(0)
	GGuardStar.SetValueInt(0)
	GRockArmor.SetValueInt(0)
	GWind.SetValueInt(0)
	GHolyShield.SetValueInt(0)
	GBloodthirst.SetValueInt(0)
	GGuardWind.SetValueInt(0)
	GGuardDivine.SetValueInt(0)
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
	GShockRecent.SetValueInt(0)
	GGuardSwitch.SetValueInt(0)
	GGuardBurst.SetValueInt(0)
	GGuardIce.SetValueInt(0)
	GFreeOpen.SetValueInt(0)
	Int i = 0
	While i < FormAbilities.Length
		player.RemoveSpell(FormAbilities[i])
		i += 1
	EndWhile
	; round 23：v0.3 的岩甲常駐能力退役（岩甲的護甲是 DLL 的效果）。
	player.RemoveSpell(UtilSpells[18])
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
	EmberLeft = 0.0
	QuenchLeft = 0.0
	ShockLeft = 0.0
	GuardSwitchLeft = 0.0
	GuardIceLeft = 0.0
	SyncKeepLeft = 0.0
	GuardWindLeft = 0.0
	GuardDivineLeft = 0.0
	CloakGuardLeft = 0.0
	NoBloodCostLeft = 0.0
	KeepSneakLeft = 0.0
	GuardDarkLeft = 0.0
	GuardAstralLeft = 0.0
	GuardStarLeft = 0.0
	FormOpenTime = now
	TwinTime = Now()
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
	LiftQueued = False
	Int i = 0
	While i < 8
		CastActor[i] = None
		KnockTime[i] = -1000000.0
		PullTime[i] = -1000000.0
		WashTime[i] = -1000000.0
		LiftActor[i] = None
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
; 印記與目標狀態在 DLL（見 OnWeaponHit）；開印那一擊的「開印 +2」由 DLL 在同一擊裡加（SelfLayer.h OpenGains）。
; Internal only: caller is an already guarded event/transaction. Never a saved authorization.
Function OnValidHitInternal(Actor akTarget, Int aiElement, Bool abPower)
	Actor player = ThePlayer()
	If !player
		Return
	EndIf
	MarkEngaged(akTarget)
	; 電荷／岩甲／風勢的命中 +1 與同調 +1 round 23 起在 DLL（SelfLayer.h PlanSelfHit）。
	; 5.3 持續專精主線：帶火印記目標火抗 -1%／點。
	If aiElement == 1
		ESSBElem.ApplyFireResistShred(Self, akTarget)
	EndIf
	; round 24（N5）：各樹命中當下的本體（震擊、護持、萎靡、侵蝕、詛咒的抗性侵蝕）在 DLL（Reactions.h PlanHitBodies）。
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

; round 25 審查修正：秒計時器（引燃、淬火、守勢、同調保留、雙生……）用 DLL 的遊戲時鐘（只算遊戲在跑的秒數，暫停、
; 讀檔不走），不再用 Utility.GetCurrentRealTime（暫停時照走）。讀檔時 ResetLoadClock 照舊把它們全部歸零。
Float Function Now()
	Return ESSBNative.RunningSeconds()
EndFunction

Int Function SecondsLeft(Float afDeadline)
	If afDeadline <= 0.0
		Return 0
	EndIf
	Float remaining = afDeadline - Now()
	If remaining <= 0.0
		Return 0
	EndIf
	Return Math.Ceiling(remaining) as Int
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

; round 23 (N4)：同調段數由 DLL 依同調效果與門檻（同調門檻、專一）算好，鏡射在 ESSB_SyncStage；這裡直接讀。
Int Function SyncStage()
	If !GSyncStage
		Return 0
	EndIf
	Return GSyncStage.GetValueInt()
EndFunction

; 只給「段數變了沒」的比較用（TickTimers 換段時刷新神佑）。
Function RefreshSyncStage()
	CachedSyncStage = SyncStage()
	SyncCacheReady = True
EndFunction

Function OnLethalHitWhileArmed()
	If IsOperational() && DivineArmed
		RefreshDivineProtection()
	EndIf
EndFunction

