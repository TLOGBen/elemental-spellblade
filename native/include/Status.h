#pragma once
// Round 22 (slice N3): the target status layer and the fire / divine self ladders, kept in engine effects the DLL
// applies. Pure: no engine, no allocation, no global state. Plugin.cpp reads an actor's effect list into a Board, calls
// the planners here and executes the StatusOps they return (Dispel(true) the old instance, then CastSpellImmediate with
// magnitude override = layers and the effectiveness that sets the duration; build/fix22_records.py, ledger D1).
//
//   ProcTerms       what the statuses add to this hit's element proc (v0.4 2.7: M_mod additions and the T factor);
//                   replaces the Papyrus difference patch (ESSBController.ApplyProc), removed this round
//   PlanStatusHit   one accepted element hit: the mark (open / refresh / cut, 2.2), the element's status on the target
//                   (2.3), the fire and divine ladders on the player, and the STATE part of the open and end reactions.
//                   The reaction bodies (damage, pushes, heals, range scans) stay in Papyrus until N5; they get an
//                   event with the values the state part worked out (ruling R4)
//   PlanEnd         the state part of one mark's end (cut, burst, expiry; 2.6) and its event
//   On...           what happens when a status runs out (effect-removed event) or on the DLL timer (ladder decay, the
//                   white-hot fire source), and when you leave a form (洩壓, clearing your ladders)
//
// Every number is v0.4's; the comment names the section. Nothing here remembers anything between calls: whatever the
// next hit needs is written into an effect.
#include "HitMath.h"
#include "ManifestData.h"

#include <algorithm>
#include <array>
#include <cstdint>

namespace essb {

inline constexpr int kStatusKindCount = static_cast<int>(StatusKind::kCount);

// ================================================================ what the engine holds

// One of our effects on an actor: present or not, its magnitude (layers, a multiplier, a stored amount) and its clock.
struct Slot {
    bool has = false;
    float magnitude = 0.0f;
    float elapsed = 0.0f;
    float duration = 0.0f;

    constexpr float Remaining() const noexcept { return has ? std::max(0.0f, duration - elapsed) : 0.0f; }
    constexpr int Layers() const noexcept { return has ? static_cast<int>(magnitude + 0.5f) : 0; }
};

// Everything the DLL reads about one actor's statuses. Marks are indexed by element (1..11).
struct Board {
    std::array<Slot, kStatusKindCount> slot{};
    std::array<Slot, 12> mark{};
    Slot bleedDot{};          // blood DoT (2.7): magnitude = damage per second
    Slot poisonDot{};         // poison DoT (2.7): magnitude m = damage per second
    bool fearing = false;     // our fear is running (ESSB_FearEffect)
    bool frenzied = false;    // our frenzy is running (ESSB_FrenzyEffect)
    float maxSlowPct = 0.0f;  // strongest of our slows on it (they share one Peak Value Modifier: the strongest wins)

    constexpr const Slot& operator[](StatusKind kind) const noexcept { return slot[static_cast<int>(kind)]; }
    constexpr Slot& operator[](StatusKind kind) noexcept { return slot[static_cast<int>(kind)]; }
    constexpr bool Has(StatusKind kind) const noexcept { return (*this)[kind].has; }
    constexpr int Layers(StatusKind kind) const noexcept { return (*this)[kind].Layers(); }

    constexpr int MarkCount() const noexcept
    {
        int count = 0;
        for (int e = kFire; e <= kAstral; ++e) {
            count += mark[e].has ? 1 : 0;
        }
        return count;
    }
    // Of the marks other than `except`, the one that has been on longest (雙印 5.2: 被切掉時只結算較舊的那個).
    constexpr int OldestMark(int except) const noexcept
    {
        int oldest = 0;
        for (int e = kFire; e <= kAstral; ++e) {
            if (e != except && mark[e].has && (oldest == 0 || mark[e].elapsed > mark[oldest].elapsed)) {
                oldest = e;
            }
        }
        return oldest;
    }
};

// Target facts the status rules read besides its effects.
struct Body {
    float health = 100.0f;
    float healthMax = 100.0f;
    float stamina = 100.0f;
    float staminaMax = 100.0f;
    bool vip = false;               // essential / protected / unique: the smaller shatter and 聖裁 percentages
    bool undeadOrDaedra = false;
    float distanceToPlayer = 0.0f;  // game units (1 m = 70)
};

// The player's health, for the blood zone (越線), the cost path and the auto-vent.
struct Self {
    float health = 100.0f;
    float healthMax = 100.0f;
    float healthPermanent = 100.0f;

    constexpr float Fraction() const noexcept { return healthPermanent > 0.0f ? health / healthPermanent : 1.0f; }
};

// ================================================================ what the DLL does

enum class Op : std::uint8_t
{
    kApply,           // cast `kind` on `who`: magnitude override `magnitude`, lasting `seconds`
    kRemove,          // Dispel(true) every effect of `kind`'s spell on `who`
    kApplyMark,       // the mark of `element` on the target for `seconds`
    kRemoveMark,      // Dispel(true) the mark of `element`
    kBleedDot,        // blood DoT: `magnitude` per second for `seconds` (the whole-second spell); magnitude 0 removes it
    kPoisonDot,       // poison DoT, same
    kRemoveDots,      // both DoTs
    kSlow,            // our shared slow on the target: `magnitude` percent for `seconds` (whole-second spells)
    kDamage,          // ESSB_React_<element> on the target with this magnitude override; element 0 = true damage
    kHeal,            // player health + magnitude
    kRestoreMagicka,  // player magicka + magnitude
    kRestoreStamina,  // player stamina + magnitude
    kPayHealth,       // the cost path: player health - magnitude, never below 1 (5.3 火源代價)
    kWash,            // strip the target's hand-cast timed buffs (ruling R5); magnitude = 淨潮 heal per buff (0 none)
    kEvent,           // a ModEvent for the Papyrus reaction bodies
    kBleedDrain,      // 放血: ESSB_Util_BleedTick on the target (no resist, no G(L)) with this magnitude
};

enum class Who : std::uint8_t
{
    kTarget,
    kPlayer,
};

// ModEvents to Papyrus (ESSBController registers for each name, Plugin.cpp kEventNames). Arguments in order.
enum class Event : std::uint8_t
{
    kOpen,         // element, open multiplier, element cut by this same hit (0 none), 1 = opened by a hit (0 ForceOpen)
    kEnd,          // element, reason (EndReason), end multiplier, chain (1 = a chain end: no node multipliers, no
                   // further reactions), value1, value2, value3 (see PlanEndBody)
    kFrozen,       // seconds: the target froze (Papyrus puts the 50% frozen slow and 深寒 on it for that long)
    kHallucinate,  // 1 fear / 2 frenzy, seconds (Papyrus casts it, or 幻視 for targets it cannot charm)
    kJudgment,     // 聖佑 tier: 聖裁 went off (Papyrus puts the II / III armour break on the target)
    kSplash,       // (struck target's bleed remaining) you crossed 70% / 30% downwards: 濺血 -- Papyrus settles a ×0.5
                   // blood surge, no clear, on every bleeding target within 15 m (the scan is N5)
    kShatter,      // 1 in-hit, 2 by the frost end: the target shattered (Papyrus applies 碎甲)
    kLanding,      // landing damage: 浮空 ran out (Papyrus OnLanding)
    kRise,         // (no values) you crossed 70% / 30% upwards: 回湧 is N4; Papyrus runs 血約 (the scan is N5)
    kCount,
};

enum class EndReason : std::uint8_t
{
    kCut = 0,     // 被切 (a different element's hit)
    kBurst = 1,   // 融斷 (Z closes the form)
    kExpire = 2,  // 自然過期
};

struct StatusOp {
    Op op{};
    Who who = Who::kTarget;
    StatusKind kind = StatusKind::kCount;
    int element = 0;
    float magnitude = 0.0f;
    float seconds = 0.0f;
    Event event = Event::kCount;
    std::array<float, 8> arg{};
};

inline constexpr int kMaxStatusOps = 96;

struct StatusPlan {
    std::array<StatusOp, kMaxStatusOps> ops{};
    int count = 0;
    bool overflow = false;  // more ops than fit: the handler faults rather than silently dropping one
    bool consumeKillStreak = false;

    constexpr void Push(const StatusOp& op) noexcept
    {
        if (count < kMaxStatusOps) {
            ops[count++] = op;
        } else {
            overflow = true;
        }
    }
};

// ================================================================ v0.4 numbers

namespace n3 {
inline constexpr float kMarkSeconds = 8.0f;        // 2.2 印記 8 秒
inline constexpr float kWaterMarkSeconds = 10.0f;  // 2.2 水印記 10 秒
inline constexpr float kMarkPerPoint = 0.2f;       // 5.2 / 5.x：印記持續 +0.2 秒／點
inline constexpr float kJumpSeconds = 4.0f;         // 5.2 跳印：跳過去的印記剩 4 秒
inline constexpr float kJumpRadius = 420.0f;        // 5.2 跳印：6 公尺內最近一個沒有印記的敵人
inline constexpr int kMarkJumped = 2;              // 印記強度的旗標位元：跳印跳過來的（每個印記只跳一次）
inline constexpr int kMarkExtended = 4;            // 旗標位元：咒延續過的（每目標一次）；一般印記的強度是 0
inline constexpr float kCurseLinger = 4.0f;        // 5.12 咒延：詛咒 ≥3 層的目標，黑暗印記過期時續 4 秒
inline constexpr int kCurseLingerAt = 3;
inline constexpr float kLinger = 4.0f;             // 5.4 寒留：接管元素的印記持續 +4 秒
inline constexpr float kResidualSeconds = 4.0f;    // 5.2 疊印：舊印記保留 4 秒為副印記
inline constexpr float kReactionCooldown = 1.0f;   // 2.6 每個目標的開印與終焉各有 1 秒內部冷卻
inline constexpr float kOpenWindow = 5.0f;         // 5.x 開啟熟練主線：開印後 5 秒內
inline constexpr float kEndWindow = 5.0f;          // 5.x 關閉專精主線：終焉後 5 秒內

// Fire (1.1, 2.6, 2.7, 5.3)
inline constexpr std::array<float, 5> kHeatProc{ 0.0f, 0.15f, 0.35f, 0.60f, 0.90f };  // 火附傷依熱度 +15／35／60／90%
inline constexpr std::array<float, 5> kHeatBurst{ 1.0f, 1.6f, 2.4f, 3.2f, 4.0f };     // 爆燃 ×（無／微熱…熔燒）
inline constexpr float kHeatMature = 2.0f;          // 各階成熟 2 秒才能再升
inline constexpr float kHeatDecay = 6.0f;           // 微熱、灼熱 6 秒未命中退一階
inline constexpr float kFuse = 8.0f;                // 白熱 8 秒引信
inline constexpr float kKindlingFuse = 12.0f;       // 添薪 8 → 12 秒
inline constexpr float kForge = 6.0f;               // 熔爐：熔燒再燒 6 秒
inline constexpr float kFlareExtend = 2.0f;         // 烈火點燃：白熱中開印引信 +2 秒
inline constexpr float kFlareExtendMax = 4.0f;      // 每個引信最多 +4 秒
inline constexpr float kFireDomainExtend = 5.0f;    // 火域：進入時白熱引信一次性 +5 秒
inline constexpr float kBlazeStart = 0.8f;          // 烈火之始：目標生命高於 80%
inline constexpr float kMolten = 10.0f;             // 熔身 10 秒
inline constexpr float kMoltenProc = 1.0f;          // 熔身：火附傷 +100%
inline constexpr float kMoltenStamina = 5.0f;       // 熔身：每秒回耐力 5
inline constexpr float kOverheatCost = 0.10f;       // 過熱：付最大生命 10%
inline constexpr float kSourceCost = 0.005f;        // 白熱：每秒付最大生命 0.5%
inline constexpr float kAutoVent = 0.10f;           // 生命 <10% 自動洩壓
inline constexpr float kSourceBase = 0.25f;         // 基礎燃燒 = B_max × 0.25 × G
inline constexpr float kSourceRadius = 210.0f;      // 3 公尺
inline constexpr float kForgeSourceRadius = 315.0f; // 熔燒 4.5 公尺
inline constexpr float kSourceN = 2.0f;             // N 基礎 2
inline constexpr float kSourceNPerPoint = 0.2f;     // 持續新手主線 +0.2／點（最多 5）
inline constexpr float kSourceNMax = 5.0f;
inline constexpr float kForgeN = 2.0f;              // 熔燒 N +2
inline constexpr float kInfernoPerPoint = 0.1f;     // 業火（同調三段）+0.1／點
inline constexpr float kSourceLinger = 2.0f;        // 餘壓：火源多留 2 秒
inline constexpr float kFireBathHeal = 0.1f;        // 火浴：每秒回血 B_max × 0.1 × 人數
inline constexpr float kOpenQuick = 5.0f;           // 開啟新手主線：開印後 5 秒內熱度升階免等待
inline constexpr float kOpenQuickPerFive = 0.5f;    // +0.5 秒／每 5 點
inline constexpr float kConsumeUnit = 0.25f;        // 爆燃的消耗加成：25% × 3 × 層數 ÷ 上限；單層標記 +25%
inline constexpr float kConsumeCap = 0.75f;         // 單一狀態最高 +75%
inline constexpr float kConsumeDotShare = 0.5f;     // 血痕與中毒的剩餘傷害 50% 轉為即時火傷
inline constexpr float kBlaze = 1.5f;               // 熾焰：白熱以上的爆燃再 ×1.5
inline constexpr float kEmber = 1.5f;               // 餘燼：火終焉後接管元素的開印 ×1.5

// Frost (2.3, 2.6, 5.4)
inline constexpr int kFreezeCap = 5;
inline constexpr int kFreezeOpen = 3;
inline constexpr float kFreezeGauge = 6.0f;         // 6 秒未命中歸零
inline constexpr float kFreezePerPoint = 0.05f;     // 持續新手主線：每次命中凍結累積 +5%／點
inline constexpr float kErodeExtend = 2.0f;         // 寒蝕：該次重擊造成的凍結歸零時限延長 2 秒
inline constexpr float kFrozen = 3.0f;              // 冰封 3 秒
inline constexpr float kPermafrost = 2.0f;          // 永凍：冰封 +2 秒
inline constexpr int kCrystalCap = 3;
inline constexpr float kShatter = 0.20f;            // 碎冰：最大生命 20% 真傷（首領與必要角色 10%）
inline constexpr float kShatterVip = 0.10f;
inline constexpr float kSharp = 0.25f;              // 銳碎：20% → 25%（首領 10% → 12%）
inline constexpr float kSharpVip = 0.12f;
inline constexpr float kCrystal = 0.05f;            // 每顆冰晶 +5%（首領 +2.5%）
inline constexpr float kCrystalVip = 0.025f;
inline constexpr float kCrystalMargin = 1.0f;       // 冰封中的冰晶比冰封多留 1 秒，冰封結束時一定還在（審查修正 2）
inline constexpr float kCoffin = 2.0f;              // 冰棺：碎冰後目標再冰封 2 秒
inline constexpr float kCoffinShatter = 0.5f;       // 第二次碎冰 ×0.5
inline constexpr float kFrostbite = 0.5f;           // 凍傷：每顆冰晶 B_max ×0.5 冰傷
inline constexpr float kGaugeSlow = 25.0f;          // 凍結量表 ≥1 時減速 25%
inline constexpr float kFrostLockSlow = 30.0f;      // 霜鎖：開印目標 3 秒內移速 -30%
inline constexpr float kFrostLock = 3.0f;
inline constexpr float kIceArmor = 210.0f;          // 冰甲：3 公尺寒氣
inline constexpr float kFrostSkin = 350.0f;         // 霜膚：3 → 5 公尺

// Earth, wind (2.3, 5.6, 5.7)
inline constexpr float kFissure = 8.0f;
inline constexpr float kDowned = 3.0f;              // 倒地 3 秒
inline constexpr float kRiftDowned = 5.0f;          // 裂地：開印目標 8 秒內被土弄倒，倒地 3 → 5 秒
inline constexpr float kDeepFissure = 0.5f;         // 深裂痕：耐力低於 50%
inline constexpr float kUnbalance = 3.0f;           // 失衡 3 秒
inline constexpr float kRideWind = 1.3f;            // 御風：失衡目標受你所有傷害 +30%
inline constexpr float kAirChase = 1.5f;            // 空中追擊：浮空目標受你的所有傷害 ×1.5
inline constexpr float kDarkWind = 5.0f;            // 暗風：潛行攻擊的風附傷 ×3 → ×5
inline constexpr float kKillStreak = 2.0f;          // 連殺：下一次潛行攻擊附傷 ×2

// Blood (2.3, 2.7, 5.8)
inline constexpr float kBleedDrain = 0.003f;        // 放血：每層每秒另扣目標當下生命 0.3%（首領 0.1%）
inline constexpr float kBleedDrainVip = 0.001f;
inline constexpr float kBleedDrainPerPoint = 0.0001f;   // 流血每層傷害主線：放血係數 +0.01%／點（不吃節點倍率）
inline constexpr int kBleedCap = 8;
inline constexpr int kDeepWound = 12;               // 深創：血痕上限 8 → 12
inline constexpr int kBleedOpen = 2;
inline constexpr float kBleed = 10.0f;              // 10 秒，命中刷新全部
inline constexpr float kStanch = 1.5f;              // 止血：低血位（30% 以下）流血傷害 ×1.5
inline constexpr float kZoneHigh = 0.7f;            // 越線：70% 與 30% 兩條線
inline constexpr float kZoneLow = 0.3f;
inline constexpr float kCross = 10.0f;              // 越線：上下共用 10 秒冷卻
inline constexpr int kBloodLead = 2;                // 血引：接管元素的開印附帶流血 2 層

// Divine (2.3, 5.9)
inline constexpr int kJudgeHits = 3;                // 第三擊觸發聖裁（神罰：第二擊）
inline constexpr float kJudge = 4.0f;               // 聖裁計數 4 秒，命中刷新
inline constexpr float kHolyDecay = 8.0f;           // 聖佑各階 8 秒，只有命中帶印記目標才刷新
inline constexpr float kHolyMature = 2.0f;          // 各階成熟 2 秒
inline constexpr std::array<float, 4> kHolyProc{ 0.0f, 0.10f, 0.20f, 0.35f };  // 聖附傷與裁決 +10／20／35%
inline constexpr std::array<float, 4> kHolyHeal{ 0.0f, 0.0f, 0.25f, 0.5f };    // II／III 命中回血 B_max ×
inline constexpr float kHolyMark = 0.2f;            // 聖印：目標受聖傷 +20%
inline constexpr float kStigma = 0.1f;              // 聖痕：非亡靈也受 +10% 聖傷
inline constexpr float kJudgeBase = 1.0f;           // 聖裁：B_max ×1.0 聖傷（無／I／II）
inline constexpr float kJudgeTop = 0.04f;           // III：目標最大生命 4% 的聖傷（首領與必要角色 2%）
inline constexpr float kJudgeTopVip = 0.02f;
inline constexpr float kPrey = 3.0f;                // 聖裁對亡靈魔族 ×3
inline constexpr int kPunishCap = 5;                // 懲戒上限 5（天誅 8 在累積那一半，N4）
inline constexpr float kPunish = 8.0f;              // 懲戒 8 秒
inline constexpr float kPunishPerLayer = 0.2f;      // 下一次裁決或聖裁每層 +20% 後清空
inline constexpr int kMercy = 2;                    // 慈光：開印時懲戒 +2（不需要聖佑 II）

// Poison (2.3, 2.7, 5.10)
inline constexpr int kDoseCap = 10;
inline constexpr int kDoseOpen = 3;
inline constexpr float kPoisonOpen = 12.0f;         // 開印 3 劑 12 秒
inline constexpr float kPoisonAdd = 3.0f;           // 時長 = 剩餘 +3 秒
inline constexpr float kPoisonMax = 15.0f;          // 上限 15 秒
inline constexpr int kMiasmaDoses = 5;              // 中毒 ≥5 劑時瘴氣（傳染門檻：1 劑）
inline constexpr float kMiasmaRate = 0.5f;          // 瘴氣：每秒傳 0.5 劑給 3 公尺內的敵人（催毒時 1 劑）
inline constexpr float kMiasmaRateCatalysed = 1.0f;
inline constexpr float kMiasmaPerPoint = 0.05f;     // 持續專精主線：瘴氣每秒傳遞劑量 +0.05／點（×NodeScale）
inline constexpr float kMiasmaRadius = 210.0f;      // 3 公尺
inline constexpr float kSpreadFloor = 12.0f;        // 2.7 擴散一劑：d' = max(d - t, 12)
inline constexpr float kCatalyze = 2.0f;            // 催毒：剩餘期間強度 ×2（潰爛 ×3）
inline constexpr float kFester = 3.0f;
inline constexpr float kPoisonLinger = 4.0f;        // 延毒：催毒時剩餘時長 +4 秒

// Water (2.3, 5.11)
inline constexpr float kSoak = 10.0f;
inline constexpr float kSoakPerPoint = 0.3f;        // 持續新手主線：浸濕持續 +0.3 秒／點
inline constexpr float kOcean = 30.0f;              // 汪洋：水終焉時目標的浸濕延長到 30 秒
inline constexpr float kSoakLocked = 3600.0f;       // 汪洋之始：浸濕不過期，直到被切掉
inline constexpr int kPressureCap = 5;
inline constexpr float kPressure = 8.0f;            // 水壓 8 秒，命中刷新
inline constexpr float kPressurePerLayer = 0.10f;   // 水壓：每層水附傷 +10%
inline constexpr float kGuide = 1.5f;               // 導引：接管元素的下一次終焉 ×1.5（強引 ×2.0）
inline constexpr float kStrongGuide = 2.0f;
inline constexpr float kWashCooldown = 10.0f;       // 退潮：每目標 10 秒一次

// Darkness (2.3, 5.12)
inline constexpr int kCurseCap = 5;
inline constexpr int kCurseOpen = 2;
inline constexpr float kCurse = 8.0f;
inline constexpr int kFearAt = 3;                   // 3 層恐懼（懼咒 2）
inline constexpr int kFrenzyAt = 5;                 // 5 層瘋狂（狂咒 4）
inline constexpr float kFear = 2.0f;
inline constexpr float kFrenzy = 3.0f;
inline constexpr float kFearCooldown = 12.0f;
inline constexpr float kFrenzyCooldown = 20.0f;
inline constexpr float kIllusionPerPoint = 0.1f;    // 幻覺持續 +0.1 秒／點
inline constexpr float kPhantom = 3.0f;             // 幻影：開印後 3 秒，目標對你的命中 30% 落空（PERK 擲骰）
inline constexpr int kConfusion = 2;                // 迷亂：瘋狂中的目標被你命中時詛咒 +2 層
inline constexpr int kEchoCurse = 2;                // 回魘：恐懼或瘋狂結束時詛咒 +2 層
inline constexpr float kDeathCurse = 3.0f;          // 死咒 3 秒引信
inline constexpr float kDeathCurseBase = 2.0f;      // 到期暗傷 = B_max ×2.0 ＋已損失生命的 15%
inline constexpr float kDeathCurseLost = 0.15f;
inline constexpr float kDeathCurseLostPerPoint = 0.005f;   // 關閉專精主線 +0.5%／點（×NodeScale）
inline constexpr float kDevour = 0.03f;             // 噬咒：消耗的每層 +3% 係數
inline constexpr float kPlagueChance = 0.05f;       // 瘟疫：同調三段時中毒目標每秒 5%／點機率擴散 1 劑（指揮官裁定 (b)）
inline constexpr float kPlagueRadius = 210.0f;      // 擴散到 3 公尺內最近的一名敵人

// Astral (2.3, 5.13)
inline constexpr int kStarCap = 3;
inline constexpr float kStarDelay = 2.0f;           // 2 秒未被直接命中後全部一起引爆
inline constexpr float kStarDelayPerPoint = 0.1f;   // 開啟新手主線：星痕延遲 -0.1 秒／點（2 → 0.5）
inline constexpr float kStarDelayMin = 0.5f;
inline constexpr float kStarLife = 30.0f;           // 星痕層數本身的壽命（引信到期就引爆，這只是上限）
inline constexpr float kStarWeakness = 0.08f;       // 星痕弱點：重擊時每層星痕 +8%
inline constexpr float kStarLock = 3.0f;            // 星鎖 3 秒
inline constexpr float kStarLockMult = 1.1f;        // 受所有元素傷 +10%
inline constexpr float kDomain = 1.2f;              // 火域（火傷）、星域（所有元素傷）+20%
inline constexpr float kRadiance = 2.0f;            // 星耀：延遲星傷改為立即並 ×2

inline constexpr float kOmni = 1.25f;               // 5.2 萬象：所有元素狀態的層數效果 +25%
inline constexpr float kBloodthirst = 1.2f;         // 5.8 飲血的嗜血：命中效果 +20%
}  // namespace n3

// ================================================================ helpers

template <RandomSource Rng>
constexpr int RoundStochastic(float value, Rng& rng)
{
    const int whole = static_cast<int>(value);
    const float remainder = value - static_cast<float>(whole);
    return whole + ((remainder > 0.0f && rng.Chance(remainder)) ? 1 : 0);
}

constexpr float Scaled(const Tuning& t, float seconds) noexcept
{
    return seconds * t.multDuration;   // ESSB_MultDuration (Papyrus DurationSeconds)
}

constexpr float CooldownOf(const Tuning& t, float seconds) noexcept
{
    return seconds * t.multCooldown;   // ESSB_MultCooldown (Papyrus CooldownSeconds)
}

template <NodeReader Nodes>
constexpr int CapBonus(const Nodes& nodes)
{
    return std::min(3, nodes.Rank(node::kCommonCapBonus) / 5);   // 5.2 每種元素狀態上限 +1 層／每 5 點（最多 +3）
}

template <NodeReader Nodes>
constexpr float Omni(const Nodes& nodes)
{
    return nodes.Has(node::kCommonOmni) ? n3::kOmni : 1.0f;
}

template <NodeReader Nodes>
constexpr int BleedCap(const Nodes& nodes)
{
    return (nodes.Has(node::kBloodDeepWound) ? n3::kDeepWound : n3::kBleedCap) + CapBonus(nodes);
}

template <NodeReader Nodes>
constexpr int PressureCap(const Nodes& nodes)
{
    return n3::kPressureCap + CapBonus(nodes);
}

template <NodeReader Nodes>
constexpr int CurseCap(const Tuning& t, const Nodes& nodes)
{
    int cap = n3::kCurseCap;
    if (t.syncStage >= 3) {
        cap += std::min(5, nodes.Rank(node::kDarkAbyss) / 3);   // 5.12 深淵：同調三段時上限 +1／每 3 點（最多 10）
    }
    return cap + CapBonus(nodes);
}

template <NodeReader Nodes>
constexpr int StarCap(const Nodes& nodes)
{
    return n3::kStarCap + nodes.Rank(node::kAstralCap) / 5 + CapBonus(nodes);   // 5.13 星痕層數上限 +1／每 5 點
}

// 2.7: per dose = B_max × k_dot (ESSB_PoisonDotK, 0.2116) × G(L) × M_mod (每劑傷害 +2%／點 × NodeScale; 萬象 +25%)
// × the MCM DoT multiplier (ESSB_MultDot).
template <NodeReader Nodes>
constexpr float PerDose(const Config& c, const Tuning& t, const Nodes& nodes)
{
    return c.damage[kPoison][1] * t.poisonDotK * t.multDot * TreeG(t, TreeOf(kPoison)) * t.baseDamageMult *
           (1.0f + Pct(t, nodes.Rank(node::kPoisonDoseDamage), 0.02f)) * Omni(nodes);
}

// 2.7: per bleed layer and second = B_max × k_dot (ESSB_BleedDotK, 0.1143) × G(L) × M_mod (流血每層傷害 +2%／點;
// 止血 at low blood) × ESSB_MultDot.
template <NodeReader Nodes>
constexpr float PerBleedLayer(const Config& c, const Tuning& t, const Nodes& nodes, const Self& self)
{
    float per = c.damage[kBlood][1] * t.bleedDotK * t.multDot * TreeG(t, TreeOf(kBlood)) * t.baseDamageMult *
                (1.0f + Pct(t, nodes.Rank(node::kBloodLayerDamage), 0.02f)) * Omni(nodes);
    if (nodes.Has(node::kBloodStanch) && self.Fraction() < n3::kZoneLow) {
        per *= n3::kStanch;   // 止血：於套用血痕當下依你目前血位寫入強度
    }
    return per;
}

// Whole doses of the poison on `b`, counted in base doses: a catalysed poison's strength carries the 催毒 multiplier
// (its marker's magnitude), which is not more doses.
constexpr int Doses(const Board& b, float perDose) noexcept
{
    const Slot& marker = b[StatusKind::kCatalyzed];
    const float factor = marker.has && marker.magnitude > 0.0f ? marker.magnitude : 1.0f;
    return perDose > 0.0f ? static_cast<int>(b.poisonDot.magnitude / factor / perDose + 0.001f) : 0;
}

// The player's heat: 0 none, 1 微熱, 2 灼熱, 3 白熱 (and 熔身), 4 熔燒.
constexpr int HeatTier(const Board& self) noexcept
{
    if (self.Has(StatusKind::kHeat4)) {
        return 4;
    }
    if (self.Has(StatusKind::kHeat3) || self.Has(StatusKind::kMoltenBody)) {
        return 3;
    }
    return self.Has(StatusKind::kHeat2) ? 2 : self.Has(StatusKind::kHeat1) ? 1 : 0;
}

constexpr StatusKind HeatKind(int tier) noexcept
{
    constexpr StatusKind kinds[] = { StatusKind::kHeat1, StatusKind::kHeat1, StatusKind::kHeat2, StatusKind::kHeat3,
        StatusKind::kHeat4 };
    return kinds[std::clamp(tier, 1, 4)];
}

constexpr int HolyTier(const Board& self) noexcept
{
    return self.Has(StatusKind::kHoly3) ? 3 : self.Has(StatusKind::kHoly2) ? 2 : self.Has(StatusKind::kHoly1) ? 1 : 0;
}

constexpr StatusKind HolyKind(int tier) noexcept
{
    return tier <= 1 ? StatusKind::kHoly1 : tier == 2 ? StatusKind::kHoly2 : StatusKind::kHoly3;
}

// 5.8 越線: 1 high (>70%), 2 middle (30..70%), 3 low (<30%).
constexpr int BloodZone(const Self& self) noexcept
{
    const float fraction = self.Fraction();
    return fraction > n3::kZoneHigh ? 1 : fraction >= n3::kZoneLow ? 2 : 3;
}

// The part of M_mod a reaction takes besides its own node multipliers: blood's curve and 血怒, day / night, the
// damage multiplier (the same categorical terms as the proc, v0.4 2.7 D_react; no wind sneak, no undead ×1.5).
template <NodeReader Nodes>
constexpr float ReactionScale(int element, const Tuning& t, const PlayerFacts& p, const Nodes& nodes)
{
    float scale = TreeG(t, TreeOf(element)) * t.baseDamageMult;
    if (element == kBlood) {
        scale *= Interpolate(BloodCurveFraction(p, nodes), kBloodHitCurve) * (BloodRage(p, nodes) ? 1.15f : 1.0f);
    }
    if (!p.interior) {
        if ((element == kDarkness && t.envNight) || (element == kDivine && !t.envNight)) {
            scale *= 1.2f;
        }
    }
    return scale;
}

// What the target's statuses do to a reaction the DLL deals itself, like Papyrus ApplyDamage's TargetDamageMult and
// GetDamageMult's 嗜血: 御風 (unbalanced), 空中追擊 (airborne), 星鎖, 星域.
template <NodeReader Nodes>
constexpr float ReactionVulnerability(const Board& target, const Board& self, const Tuning& t, const Nodes& nodes)
{
    float mult = self.Has(StatusKind::kBloodthirst) ? n3::kBloodthirst : 1.0f;
    if (nodes.Has(node::kWindRideWind) && target.Has(StatusKind::kUnbalance)) {   // 御風：不看同調（只有免疫減速看）
        mult *= n3::kRideWind;
    }
    if (nodes.Has(node::kWindAirChase) && target.Has(StatusKind::kAirborne)) {
        mult *= n3::kAirChase;
    }
    if (target.Has(StatusKind::kStarLock)) {
        mult *= n3::kStarLockMult;
    }
    if (target.Has(StatusKind::kDomainAstral)) {
        mult *= n3::kDomain;
    }
    (void)t;
    return mult;
}

// 聖痕 (v0.4 5.9): a target carrying the divine mark is judged undead / daedra -- the ×1.5 of 2.1 on the hit (HitMath)
// as well as the end's ×3 (PlanEndBody `prey`); the +10% for a target that is not undead stays in ProcTerms (review
// fix 4).
template <NodeReader Nodes>
constexpr TargetFacts JudgedTarget(TargetFacts facts, const Board& target, const Nodes& nodes)
{
    if (nodes.Has(node::kDivineStigma) && target.mark[kDivine].has) {
        facts.undeadOrDaedra = true;
    }
    return facts;
}

// ================================================================ op builders

constexpr StatusOp MakeOp(Op kind, Who who = Who::kTarget) noexcept
{
    StatusOp op{};
    op.op = kind;
    op.who = who;
    return op;
}

constexpr StatusOp Amount(Op kind, float magnitude, int element = 0, float seconds = 0.0f) noexcept
{
    const bool self = kind == Op::kHeal || kind == Op::kRestoreMagicka || kind == Op::kRestoreStamina || kind == Op::kPayHealth;
    StatusOp op = MakeOp(kind, self ? Who::kPlayer : Who::kTarget);
    op.magnitude = magnitude;
    op.element = element;
    op.seconds = seconds;
    return op;
}

template <class... Args>
constexpr StatusOp MakeEvent(Event event, Args... args) noexcept
{
    StatusOp op = MakeOp(Op::kEvent);
    op.event = event;
    int i = 0;
    ((op.arg[i++] = static_cast<float>(args)), ...);
    return op;
}

// Writes one actor's statuses: pushes the op and updates the board the planner holds, so later rules of the same call
// see the new state (an open that freezes the target, then the power hit that shatters it, and so on).
struct Writer {
    StatusPlan& plan;
    Board& board;
    Who who;

    constexpr void Set(StatusKind kind, float magnitude, float seconds) const noexcept
    {
        StatusOp op = MakeOp(Op::kApply, who);
        op.kind = kind;
        op.magnitude = magnitude;
        op.seconds = seconds;
        plan.Push(op);
        board[kind] = Slot{ true, magnitude, 0.0f, seconds };
    }
    constexpr void Clear(StatusKind kind) const noexcept
    {
        if (board.Has(kind)) {
            StatusOp op = MakeOp(Op::kRemove, who);
            op.kind = kind;
            plan.Push(op);
        }
        board[kind] = Slot{};
    }
    constexpr void Mark(int element, float seconds) const noexcept
    {
        StatusOp op = MakeOp(Op::kApplyMark);
        op.element = element;
        op.seconds = seconds;
        plan.Push(op);
        board.mark[element] = Slot{ true, 0.0f, 0.0f, seconds };   // cast without an override: the record's 0
    }
    // A mark with flag bits in its magnitude (跳印 n3::kMarkJumped, 咒延 n3::kMarkExtended). No open reaction.
    constexpr void FlaggedMark(int element, float seconds, int flags) const noexcept
    {
        StatusOp op = MakeOp(Op::kApplyMark);
        op.element = element;
        op.seconds = seconds;
        op.magnitude = static_cast<float>(flags);
        plan.Push(op);
        board.mark[element] = Slot{ true, static_cast<float>(flags), 0.0f, seconds };
    }
    constexpr void Unmark(int element) const noexcept
    {
        if (board.mark[element].has) {
            StatusOp op = MakeOp(Op::kRemoveMark);
            op.element = element;
            plan.Push(op);
        }
        board.mark[element] = Slot{};
    }
};

// ================================================================ everything a rule reads

// Inputs besides the two boards. Pointers because this is built once per call by the handler.
struct StatusInputs {
    const Config* config = nullptr;
    const Tuning* tuning = nullptr;
    PlayerFacts player{};     // blood curve, interior (reaction scale)
    Self self{};
    Body body{};
    bool iceArmor = false;    // frost form with 冰甲: the 3 m chill cloak is on you (霜膚: 5 m)
};

// ================================================================ single-status rules

namespace rule {

// ---- durations

template <NodeReader Nodes>
constexpr float MarkSeconds(int element, const Tuning& t, const Nodes& nodes, bool linger)
{
    float seconds = element == kWater ? n3::kWaterMarkSeconds : n3::kMarkSeconds;
    seconds += n3::kMarkPerPoint * static_cast<float>(nodes.Rank(node::kCommonMarkDuration));
    if (IsNode(node::kMarkDuration[element])) {
        seconds += n3::kMarkPerPoint * static_cast<float>(nodes.Rank(node::kMarkDuration[element]));
    }
    return Scaled(t, seconds + (linger ? n3::kLinger : 0.0f));
}

template <NodeReader Nodes>
constexpr float SoakSeconds(const Tuning& t, const Nodes& nodes)
{
    return Scaled(t, n3::kSoak + n3::kSoakPerPoint * static_cast<float>(nodes.Rank(node::kWaterSoakDuration)));
}

template <NodeReader Nodes>
constexpr float StarDelay(const Tuning& t, const Nodes& nodes)
{
    const float delay = n3::kStarDelay - n3::kStarDelayPerPoint * static_cast<float>(nodes.Rank(node::kAstralDelay));
    return Scaled(t, std::max(n3::kStarDelayMin, delay));
}

template <NodeReader Nodes>
constexpr float FrozenSeconds(const Tuning& t, const Nodes& nodes)
{
    return Scaled(t, n3::kFrozen + (nodes.Has(node::kFrostPermafrost) ? n3::kPermafrost : 0.0f));
}

template <NodeReader Nodes>
constexpr float FuseSeconds(const Tuning& t, const Nodes& nodes)
{
    return Scaled(t, nodes.Has(node::kFireKindling) ? n3::kKindlingFuse : n3::kFuse);
}

// ---- frost

// The target freezes: gauge full, the freeze effect (magnitude = the shatter multiplier: 1, or 0.5 after 冰棺), crystals
// stored earlier (深霜結) last with it, and Papyrus gets the frozen event for the 50% slow and 深寒.
template <NodeReader Nodes>
constexpr void Freeze(StatusPlan& plan, Board& target, float seconds, float shatterMult, const Nodes& nodes)
{
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kFrozen, shatterMult, seconds);
    w.Set(StatusKind::kFreeze, static_cast<float>(n3::kFreezeCap), seconds);
    if (target.Has(StatusKind::kCrystal)) {
        // 冰晶 outlive 冰封 by a second, so the frozen end still sees them (凍傷; review fix 2); OnFrozenEnd clears them.
        w.Set(StatusKind::kCrystal, target[StatusKind::kCrystal].magnitude, seconds + n3::kCrystalMargin);
    }
    plan.Push(MakeEvent(Event::kFrozen, seconds));
    (void)nodes;
}

// 碎冰 (2.6, 5.4): max health 20% true damage (bosses 10%; 銳碎 25% / 12%; legend main +3%/point on the 20%), each
// crystal +5% (2.5%), the freeze ends; a second freeze from 冰棺 shatters for ×0.5. `source` 1 in-hit, 2 frost end.
template <NodeReader Nodes>
constexpr void Shatter(StatusPlan& plan, Board& target, const StatusInputs& in, const Nodes& nodes, int source, float mult = 1.0f)
{
    const Tuning& t = *in.tuning;
    const bool vip = in.body.vip;
    const bool sharp = nodes.Has(node::kFrostSharp);
    float pct = vip ? (sharp ? n3::kSharpVip : n3::kShatterVip) : (sharp ? n3::kSharp : n3::kShatter);
    pct *= 1.0f + Pct(t, nodes.Rank(node::kSignature[kFrost]), 0.03f);
    pct += static_cast<float>(target.Layers(StatusKind::kCrystal)) * (vip ? n3::kCrystalVip : n3::kCrystal);
    const float shatterMult = target[StatusKind::kFrozen].has ? target[StatusKind::kFrozen].magnitude : 1.0f;
    plan.Push(Amount(Op::kDamage, in.body.healthMax * pct * shatterMult * mult * t.baseDamageMult, 0));
    const Writer w{ plan, target, Who::kTarget };
    w.Clear(StatusKind::kFrozen);
    w.Clear(StatusKind::kCrystal);
    w.Clear(StatusKind::kFreeze);
    plan.Push(MakeEvent(Event::kShatter, source));
    if (nodes.Has(node::kFrostCoffin) && shatterMult >= 1.0f) {
        Freeze(plan, target, Scaled(t, n3::kCoffin), n3::kCoffinShatter, nodes);   // 冰棺
    }
}

// Adds freeze (2.3: 暴風雪 ×2; 冰原 ×2). Reaching 5 freezes. The gauge and any stored crystals run 6 s from this hit
// (寒蝕's power hit 8 s), with the 25% gauge slow for as long.
template <NodeReader Nodes, RandomSource Rng>
constexpr void AddFreeze(StatusPlan& plan, Board& target, float amount, bool erodePower, const StatusInputs& in,
    const Nodes& nodes, Rng& rng)
{
    const Tuning& t = *in.tuning;
    if (target.Has(StatusKind::kFrozen)) {
        return;
    }
    if (in.tuning->envStormy) {
        amount *= 2.0f;
    }
    if (target.Has(StatusKind::kDomainFrost)) {
        amount *= 2.0f;
    }
    const int after = std::min(n3::kFreezeCap, target.Layers(StatusKind::kFreeze) + RoundStochastic(amount, rng));
    if (after <= 0) {
        return;
    }
    if (after >= n3::kFreezeCap) {
        Freeze(plan, target, FrozenSeconds(t, nodes), 1.0f, nodes);
        return;
    }
    float seconds = Scaled(t, n3::kFreezeGauge);
    if (erodePower) {
        seconds += Scaled(t, n3::kErodeExtend);
    }
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kFreeze, static_cast<float>(after), seconds);
    if (target.Has(StatusKind::kCrystal)) {
        w.Set(StatusKind::kCrystal, target[StatusKind::kCrystal].magnitude, seconds);
    }
    plan.Push(Amount(Op::kSlow, std::min(n3::kGaugeSlow, std::clamp(t.slowCapPct, 0.0f, 70.0f)), 0, seconds));
}

// ---- blood

// Bleed layers (2.3): up to 8 (深創 12, + 萬象 cap); every hit refreshes all of them for 10 s; the DoT's per-second
// strength is re-written with the new layer count (layers × per layer, 2.7).
template <NodeReader Nodes>
constexpr void AddBleed(StatusPlan& plan, Board& target, int layers, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    const int after = std::min(BleedCap(nodes), target.Layers(StatusKind::kBleed) + layers);
    if (after <= 0) {
        return;
    }
    const float seconds = Scaled(t, n3::kBleed);
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kBleed, static_cast<float>(after), seconds);
    const float perSecond = static_cast<float>(after) * PerBleedLayer(*in.config, t, nodes, in.self);
    plan.Push(Amount(Op::kBleedDot, perSecond, 0, seconds));
    target.bleedDot = Slot{ true, perSecond, 0.0f, seconds };
}

// ---- poison

struct Poison {
    float magnitude = 0.0f;   // damage per second (m)
    float remaining = 0.0f;   // seconds (d - t)
};

// A catalysed poison (催毒, 潰爛; the end multiplier included) carries its whole multiplier as the 催毒 marker's magnitude:
// m = base × factor. Growth is counted in base doses so a later dose never halves a catalysed poison (review fix 1).
constexpr float PoisonFactor(const Board& target) noexcept
{
    const Slot& marker = target[StatusKind::kCatalyzed];
    return marker.has && marker.magnitude > 0.0f ? marker.magnitude : 1.0f;
}

// 2.7 growth: base' = min(base + doses × per dose, 10 doses), m' = base' × factor; d' = min(d - t + 3 s, 15 s); doses on a
// clean target start at 12 s (the open's 3 doses). Doses may be fractional (瘴氣 0.5 a second).
constexpr Poison Grow(Poison now, float doses, float perDose, float factor, float add, float maximum, float openSeconds) noexcept
{
    const float base = now.magnitude / factor;
    Poison next;
    next.magnitude = std::min(base + doses * perDose, static_cast<float>(n3::kDoseCap) * perDose) * factor;
    next.remaining = now.magnitude <= 0.0f ? openSeconds : std::min(now.remaining + add, maximum);
    return next;
}

// 2.7 擴散一劑 (淬毒's transfer, 瘴氣, 瘟疫, 濃毒): the same base-dose growth, d' = max(d - t, 12 s).
constexpr Poison Spread(Poison now, float doses, float perDose, float factor, float floor) noexcept
{
    const float base = now.magnitude / factor;
    Poison next;
    next.magnitude = std::min(base + doses * perDose, static_cast<float>(n3::kDoseCap) * perDose) * factor;
    next.remaining = std::max(now.remaining, floor);
    return next;
}

constexpr float BaseDoses(const Board& target, float perDose) noexcept
{
    return perDose > 0.0f ? target.poisonDot.magnitude / PoisonFactor(target) / perDose : 0.0f;
}

// Re-applies the one poison effect (Dispel(true) first, native-verification-3 s5); a catalysed poison's marker follows its
// time. The 瘴氣 cloak is gone (commander ruling (b)+(d)): the per-second spread is TargetSecond's (MiasmaDoses below).
template <NodeReader Nodes>
constexpr void SetPoison(StatusPlan& plan, Board& target, Poison next, const StatusInputs& in, const Nodes& nodes)
{
    plan.Push(Amount(Op::kPoisonDot, next.magnitude, 0, next.remaining));
    target.poisonDot = Slot{ true, next.magnitude, 0.0f, next.remaining };
    if (target.Has(StatusKind::kCatalyzed)) {
        Writer{ plan, target, Who::kTarget }.Set(StatusKind::kCatalyzed, target[StatusKind::kCatalyzed].magnitude, next.remaining);
    }
    (void)in;
    (void)nodes;
}

template <NodeReader Nodes>
constexpr void AddDoses(StatusPlan& plan, Board& target, float doses, const StatusInputs& in, const Nodes& nodes)
{
    if (doses <= 0.0f) {
        return;
    }
    const Tuning& t = *in.tuning;
    const Poison now{ target.poisonDot.magnitude, target.poisonDot.Remaining() };
    SetPoison(plan, target, Grow(now, doses, PerDose(*in.config, t, nodes), PoisonFactor(target), Scaled(t, n3::kPoisonAdd),
        Scaled(t, n3::kPoisonMax), Scaled(t, n3::kPoisonOpen)), in, nodes);
}

template <NodeReader Nodes>
constexpr void SpreadDoses(StatusPlan& plan, Board& target, float doses, const StatusInputs& in, const Nodes& nodes)
{
    if (doses <= 0.0f) {
        return;
    }
    const Tuning& t = *in.tuning;
    const Poison now{ target.poisonDot.magnitude, target.poisonDot.Remaining() };
    SetPoison(plan, target, Spread(now, doses, PerDose(*in.config, t, nodes), PoisonFactor(target), Scaled(t, n3::kSpreadFloor)),
        in, nodes);
}

// 瘴氣 (2.3, 5.10): a target with at least 5 base doses (傳染門檻 1) gives every enemy within 3 m 0.5 doses a second
// (1 while catalysed), + 0.05 per point of the 持續 adept main line. 0 below the threshold.
template <NodeReader Nodes>
constexpr float MiasmaDoses(const Board& source, const StatusInputs& in, const Nodes& nodes)
{
    if (!source.poisonDot.has) {
        return 0.0f;
    }
    const float perDose = PerDose(*in.config, *in.tuning, nodes);
    const int threshold = nodes.Has(node::kPoisonThreshold) ? 1 : n3::kMiasmaDoses;
    if (BaseDoses(source, perDose) + 0.001f < static_cast<float>(threshold)) {
        return 0.0f;
    }
    const float rate = source.Has(StatusKind::kCatalyzed) ? n3::kMiasmaRateCatalysed : n3::kMiasmaRate;
    return rate + Pct(*in.tuning, nodes.Rank(node::kPoisonMiasmaRate), n3::kMiasmaPerPoint);
}

// 瘟疫 (5.10 持續傳奇主線): at sync stage 3 a poisoned target spreads 1 dose to the nearest enemy within 3 m, 5% a
// point each second.
template <NodeReader Nodes>
constexpr float PlagueChance(const Board& source, const Tuning& t, const Nodes& nodes)
{
    return source.poisonDot.has && t.syncStage >= 3 ? n3::kPlagueChance * static_cast<float>(nodes.Rank(node::kPoisonPlague)) : 0.0f;
}

// ---- water

// Pressure (5.11): up to 5 (+ 萬象 cap), 8 s. Newly reaching the cap washes the target once (ruling R5); it has to fall
// below the cap (expire) before it can wash again, so a hit that keeps it at the cap does nothing more.
template <NodeReader Nodes>
constexpr void SetPressure(StatusPlan& plan, Board& target, int layers, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    const int cap = PressureCap(nodes);
    const int before = target.Layers(StatusKind::kPressure);
    const int after = std::min(cap, layers);
    if (after <= 0) {
        return;
    }
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kPressure, static_cast<float>(after), Scaled(t, n3::kPressure));
    if (after >= cap && before < cap) {
        // 淨潮：任何沖刷每清掉目標一個增益，你回復生命與魔力各 B_max ×2.
        const float refund = nodes.Has(node::kWaterPurgeTide) ? 2.0f * in.config->damage[kWater][1] : 0.0f;
        plan.Push(Amount(Op::kWash, refund));
    }
}

// ---- darkness

// Curse (2.3, 5.12): up to 5 (深淵, 萬象), 8 s; after adding, the illusion ladder compares the layers: crossing 3 fears
// (懼咒 2), crossing 5 frenzies (狂咒 4), frenzy first when one hit crosses both; each has its own cooldown on the target.
template <NodeReader Nodes>
constexpr void AddCurse(StatusPlan& plan, Board& target, int layers, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    const int before = target.Layers(StatusKind::kCurse);
    const int after = std::min(CurseCap(t, nodes), before + layers);
    if (after <= 0 || layers <= 0) {
        return;
    }
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kCurse, static_cast<float>(after), Scaled(t, n3::kCurse));
    const int fearAt = nodes.Has(node::kDarkFearCurse) ? 2 : n3::kFearAt;
    const int frenzyAt = nodes.Has(node::kDarkFrenzyCurse) ? 4 : n3::kFrenzyAt;
    const float longer = n3::kIllusionPerPoint * static_cast<float>(nodes.Rank(node::kDarkIllusionTime));
    if (before < frenzyAt && after >= frenzyAt && !target.Has(StatusKind::kFrenzyCooldown)) {
        w.Set(StatusKind::kFrenzyCooldown, 1.0f, CooldownOf(t, n3::kFrenzyCooldown));
        plan.Push(MakeEvent(Event::kHallucinate, 2, Scaled(t, n3::kFrenzy + longer)));
    } else if (before < fearAt && after >= fearAt && !target.Has(StatusKind::kFearCooldown)) {
        w.Set(StatusKind::kFearCooldown, 1.0f, CooldownOf(t, n3::kFearCooldown));
        plan.Push(MakeEvent(Event::kHallucinate, 1, Scaled(t, n3::kFear + longer)));
    }
}

// ---- astral

// Star marks (5.13): up to 3 (+1 per 5 points, 萬象 cap); a direct hit re-times the fuse, which detonates all of them
// when it runs out (OnStarFuseEnd). A target with star marks is in resonance.
template <NodeReader Nodes>
constexpr void AddStars(StatusPlan& plan, Board& target, int layers, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    const int after = std::min(StarCap(nodes), target.Layers(StatusKind::kStar) + layers);
    if (after <= 0) {
        return;
    }
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kStar, static_cast<float>(after), Scaled(t, n3::kStarLife));
    w.Set(StatusKind::kStarFuse, 1.0f, StarDelay(t, nodes));
}

// Detonation: layers × B_max × 1.0 × G × the reaction scale × 萬象, and the target leaves resonance.
template <NodeReader Nodes>
constexpr void DetonateStars(StatusPlan& plan, Board& target, const Board& self, const StatusInputs& in,
    const Nodes& nodes, float mult)
{
    const int layers = target.Layers(StatusKind::kStar);
    const float vulnerability = ReactionVulnerability(target, self, *in.tuning, nodes);
    const Writer w{ plan, target, Who::kTarget };
    w.Clear(StatusKind::kStarFuse);
    w.Clear(StatusKind::kStar);
    if (layers <= 0) {
        return;
    }
    const float amount = static_cast<float>(layers) * in.config->damage[kAstral][1] *
                         ReactionScale(kAstral, *in.tuning, in.player, nodes) * Omni(nodes) * mult * vulnerability;
    plan.Push(Amount(Op::kDamage, amount, kAstral));
}

// ---- earth

// 倒地 (2.3, 5.6): 3 s, 5 s with 裂地 while the earth open's fissure is still on the target.
template <NodeReader Nodes>
constexpr void Down(StatusPlan& plan, Board& target, const StatusInputs& in, const Nodes& nodes)
{
    const bool rift = nodes.Has(node::kEarthRift) && target.Has(StatusKind::kFissure);
    const Writer w{ plan, target, Who::kTarget };
    w.Set(StatusKind::kDowned, 1.0f, Scaled(*in.tuning, rift ? n3::kRiftDowned : n3::kDowned));
}

// ---- the fire ladder (on the player)

// Moves the heat to `tier` (0 clears it). Tiers 1-2 carry the 6 s decay timer; tier 3 is the white-hot fuse.
template <NodeReader Nodes>
constexpr void SetHeat(StatusPlan& plan, Board& self, int tier, const StatusInputs& in, const Nodes& nodes, float fuse = 0.0f)
{
    const Writer w{ plan, self, Who::kPlayer };
    for (int k = 1; k <= 4; ++k) {
        if (k != tier) {
            w.Clear(HeatKind(k));
        }
    }
    if (tier <= 0) {
        w.Clear(StatusKind::kHeatDecay);
        return;
    }
    const Tuning& t = *in.tuning;
    if (tier == 3) {
        w.Set(StatusKind::kHeat3, 0.0f, fuse > 0.0f ? fuse : FuseSeconds(t, nodes));   // magnitude = seconds 烈火點燃 added
        w.Clear(StatusKind::kHeatDecay);
    } else if (tier == 4) {
        w.Set(StatusKind::kHeat4, 0.0f, Scaled(t, n3::kForge));
        w.Clear(StatusKind::kHeatDecay);
    } else {
        w.Set(HeatKind(tier), 1.0f, 3600.0f);
        w.Set(StatusKind::kHeatDecay, 1.0f, Scaled(t, n3::kHeatDecay));
    }
}

// A fire hit or open pushes the heat `steps` tiers, if the current tier has matured (2 s); inside the open window of
// 開啟新手主線 or a 火域 you are standing in, there is no wait. Never past white-hot; 熔身 does not advance.
template <NodeReader Nodes>
constexpr void RaiseHeat(StatusPlan& plan, Board& self, int steps, const StatusInputs& in, const Nodes& nodes, bool direct = false)
{
    if (self.Has(StatusKind::kMoltenBody)) {
        return;
    }
    const int tier = HeatTier(self);
    const Writer w{ plan, self, Who::kPlayer };
    if (tier >= 3) {
        return;   // white-hot and above only change by the fuse
    }
    bool mature = tier == 0 || self[HeatKind(tier)].elapsed >= n3::kHeatMature || direct;
    const Slot& open = self[StatusKind::kOpenBoost];
    if (open.has && open.Layers() == kFire && nodes.Rank(node::kFireOpenQuick) > 0 && open.Remaining() > 0.0f) {
        mature = true;   // 開印後 5 秒內（+0.5 秒／每 5 點）熱度升階免等待
    }
    if (self.Has(StatusKind::kFireDomainPlayer)) {
        mature = true;   // 火域：你在其中熱度升階免等待
    }
    if (!mature) {
        if (tier > 0) {
            w.Set(StatusKind::kHeatDecay, 1.0f, Scaled(*in.tuning, n3::kHeatDecay));   // the hit still resets the decay
        }
        return;
    }
    SetHeat(plan, self, std::min(3, tier + steps), in, nodes);
}

// ---- the divine ladder (on the player)

template <NodeReader Nodes>
constexpr void SetHoly(StatusPlan& plan, Board& self, int tier, const StatusInputs& in, const Nodes& nodes)
{
    const Writer w{ plan, self, Who::kPlayer };
    for (int k = 1; k <= 3; ++k) {
        if (k != tier) {
            w.Clear(HolyKind(k));
        }
    }
    if (tier <= 0) {
        w.Clear(StatusKind::kHolyDecay);
        return;
    }
    if (!self.Has(HolyKind(tier))) {
        // Magnitude override 0: an override would be written into the tier spell's weapon and armour effects too.
        w.Set(HolyKind(tier), 0.0f, 3600.0f);
    }
    w.Set(StatusKind::kHolyDecay, 1.0f, Scaled(*in.tuning, n3::kHolyDecay));
    (void)nodes;
}

// Hitting a target with the divine mark raises 聖佑 one tier once the current tier has matured (2 s), else refreshes it.
template <NodeReader Nodes>
constexpr void RaiseHoly(StatusPlan& plan, Board& self, int steps, const StatusInputs& in, const Nodes& nodes)
{
    const int tier = HolyTier(self);
    const bool mature = tier == 0 || self[HolyKind(tier)].elapsed >= n3::kHolyMature;
    SetHoly(plan, self, mature ? std::min(3, tier + steps) : tier, in, nodes);
}

}  // namespace rule

// ================================================================ proc terms (replaces the difference patch)

// What the statuses do to one element's proc, read BEFORE this hit changes anything (like the Papyrus patch): `add`
// joins the node sum of M_mod (bonuses like the nodes: the open / end windows, 熔身, 冰封目標受冰附傷, the 聖佑 holy
// bonus); `mult` is 2.7's T and the target's vulnerabilities (heat tier, pressure, star weakness, 聖印, domains, 星鎖,
// 御風, 空中追擊, 嗜血). Ledger decision: which side each term sits on.
struct ProcTerm {
    float add = 0.0f;
    float mult = 1.0f;
};

template <NodeReader Nodes>
constexpr ProcTerm ProcTerms(int element, bool power, const Tuning& t, const Board& target, const Board& self,
    const Body& body, const Nodes& nodes)
{
    ProcTerm term;
    const Slot& open = self[StatusKind::kOpenBoost];
    if (open.has && open.Layers() == element && open.Remaining() > 0.0f && IsNode(node::kOpenProc[element])) {
        term.add += Pct(t, nodes.Rank(node::kOpenProc[element]), 0.01f);   // 開印後 5 秒內 X 附傷 +1%／點
    }
    if (self.Has(StatusKind::kEndBoost)) {
        term.add += self[StatusKind::kEndBoost].magnitude;   // 終焉後 5 秒內接管元素附傷（終焉時算好）
    }
    if (self.Has(StatusKind::kBloodthirst)) {
        term.mult *= n3::kBloodthirst;
    }
    switch (element) {
    case kFire:
        term.mult *= 1.0f + n3::kHeatProc[HeatTier(self)];
        if (self.Has(StatusKind::kMoltenBody)) {
            term.add += n3::kMoltenProc;
        }
        if (target.Has(StatusKind::kDomainFire)) {
            term.mult *= n3::kDomain;
        }
        break;
    case kFrost:
        if (target.Has(StatusKind::kFrozen)) {
            term.add += Pct(t, nodes.Rank(node::kFrostFrozenProc), 0.02f);   // 冰封目標受冰附傷 +2%／點
        }
        break;
    case kDivine: {
        const int holy = HolyTier(self);
        term.add += n3::kHolyProc[holy];
        term.add += Pct(t, nodes.Rank(node::kDivineHolyBonus), 0.01f) * static_cast<float>(holy);   // +1%／點 × 階數
        if (target.mark[kDivine].has) {
            float vulnerability = 1.0f + n3::kHolyMark;
            if (nodes.Has(node::kDivineStigma) && !body.undeadOrDaedra) {
                vulnerability += n3::kStigma;
            }
            term.mult *= vulnerability;
        }
        break;
    }
    case kWater:
        if (nodes.Has(node::kWaterPressure) && target.Has(StatusKind::kPressure)) {
            const float perLayer = n3::kPressurePerLayer + Pct(t, nodes.Rank(node::kWaterPressureDamage), 0.01f);
            term.mult *= 1.0f + static_cast<float>(target.Layers(StatusKind::kPressure)) * perLayer * Omni(nodes);
        }
        break;
    case kAstral:
        if (power && nodes.Has(node::kAstralWeakness)) {
            term.mult *= 1.0f + n3::kStarWeakness * static_cast<float>(target.Layers(StatusKind::kStar)) * Omni(nodes);
        }
        break;
    default:
        break;
    }
    if (nodes.Has(node::kWindRideWind) && target.Has(StatusKind::kUnbalance)) {   // 御風：不看同調（只有免疫減速看）
        term.mult *= n3::kRideWind;
    }
    if (nodes.Has(node::kWindAirChase) && target.Has(StatusKind::kAirborne)) {
        term.mult *= n3::kAirChase;
    }
    if (target.Has(StatusKind::kStarLock)) {
        term.mult *= n3::kStarLockMult;
    }
    if (target.Has(StatusKind::kDomainAstral)) {
        term.mult *= n3::kDomain;
    }
    return term;
}

// 暗風 (the wind sneak attack ×5 instead of HitMath's ×3) and 連殺 (×2, used up by this hit).
template <NodeReader Nodes>
constexpr float WindSneakExtra(bool sneak, const Board& self, const Nodes& nodes, bool& consumeStreak)
{
    consumeStreak = false;
    if (!sneak) {
        return 1.0f;
    }
    float mult = nodes.Has(node::kWindDarkWind) ? n3::kDarkWind / 3.0f : 1.0f;
    if (self.Has(StatusKind::kKillStreak) && nodes.Has(node::kWindKillStreak)) {
        mult *= n3::kKillStreak;
        consumeStreak = true;
    }
    return mult;
}

// ================================================================ open and end (the state part)

// The open reaction's state (2.6 開印) for `element`, times `mult` (開印效果 +3%／點 × 餘燼). `cutFrom` = the element this
// same hit cut (0 none): 血引 and 聖引 act on the open that follows their end.
template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanOpenState(StatusPlan& plan, int element, float mult, int cutFrom, Board& target, Board& self,
    const StatusInputs& in, const Nodes& nodes, Rng& rng)
{
    const Tuning& t = *in.tuning;
    const Config& c = *in.config;
    const Writer tw{ plan, target, Who::kTarget };
    const Writer pw{ plan, self, Who::kPlayer };
    // The open windows first: the fire ladder reads its own (開印後熱度升階免等待).
    float window = n3::kOpenWindow;
    if (element == kFire) {
        window += n3::kOpenQuickPerFive * static_cast<float>(nodes.Rank(node::kFireOpenQuick) / 5);
    }
    pw.Set(StatusKind::kOpenBoost, static_cast<float>(element), Scaled(t, window));   // the effect's life is the window
    switch (element) {
    case kFire: {
        const int tier = HeatTier(self);
        if (tier == 3 && self.Has(StatusKind::kHeat3) && nodes.Has(node::kFireFlareOpen)) {
            // 烈火點燃：白熱中開印引信 +2 秒（每個引信最多 +4 秒；火源掛的印記不算開印，那條路不走這裡）。
            const Slot& fuse = self[StatusKind::kHeat3];
            const float extra = std::min(n3::kFlareExtend, n3::kFlareExtendMax - fuse.magnitude);
            if (extra > 0.0f) {
                pw.Set(StatusKind::kHeat3, fuse.magnitude + extra, fuse.Remaining() + extra);
            }
        } else if (nodes.Has(node::kFireBlazeStart) && in.body.healthMax > 0.0f &&
                   in.body.health / in.body.healthMax > n3::kBlazeStart && tier < 3) {
            rule::SetHeat(plan, self, 3, in, nodes);   // 烈火之始：開印若目標生命高於 80%，熱度直接白熱
        } else {
            rule::RaiseHeat(plan, self, nodes.Has(node::kFireIgnite) ? 2 : 1, in, nodes);   // 點燃（引火：兩階）
        }
        break;
    }
    case kFrost: {
        if (nodes.Has(node::kFrostDeepRime) && !target.Has(StatusKind::kFrozen)) {
            const int crystals = std::min(n3::kCrystalCap, target.Layers(StatusKind::kCrystal) + 1);   // 深霜結
            tw.Set(StatusKind::kCrystal, static_cast<float>(crystals), Scaled(t, n3::kFreezeGauge));
        }
        if (nodes.Has(node::kFrostAbsolute) && t.syncStage >= 3) {
            if (!target.Has(StatusKind::kFrozen)) {
                rule::Freeze(plan, target, rule::FrozenSeconds(t, nodes), 1.0f, nodes);   // 絕霜
            }
        } else {
            const float amount = static_cast<float>(n3::kFreezeOpen + nodes.Rank(node::kFrostOpenFreeze) / 3) * mult;
            rule::AddFreeze(plan, target, amount, false, in, nodes, rng);   // 霜結：凍結 +3（開印凍結 +1／每 3 點）
        }
        // 霜結的減速 25% 3 秒 is the open body in Papyrus. 霜鎖：開印目標 3 秒內移速 -30%；已在減速上限時改為凍結 +1.
        if (nodes.Has(node::kFrostLock)) {
            if (target.maxSlowPct >= std::clamp(t.slowCapPct, 0.0f, 70.0f)) {
                rule::AddFreeze(plan, target, 1.0f, false, in, nodes, rng);
            } else {
                plan.Push(Amount(Op::kSlow, n3::kFrostLockSlow, 0, Scaled(t, n3::kFrostLock)));
            }
        }
        break;
    }
    case kEarth:
        tw.Set(StatusKind::kFissure, 1.0f, Scaled(t, n3::kFissure));   // 裂痕（護甲與耐力的削減是 Papyrus 開印本體）
        if (nodes.Has(node::kEarthDeepFissure) && in.body.staminaMax > 0.0f &&
            in.body.stamina / in.body.staminaMax < n3::kDeepFissure) {
            rule::Down(plan, target, in, nodes);   // 深裂痕：耐力低於 50% 立即跌倒（掛倒地；推力在 Papyrus）
        }
        break;
    case kWind:
        tw.Set(StatusKind::kUnbalance, 1.0f, Scaled(t, n3::kUnbalance));   // 風痕：施加失衡（拉近的推力在 Papyrus）
        break;
    case kBlood: {
        int layers = n3::kBleedOpen + nodes.Rank(node::kBloodOpenLayers) / 5;   // 開印 2 層（+1 層／每 5 點）
        if (nodes.Has(node::kBloodDeepMark)) {
            const int zone = BloodZone(in.self);   // 深血痕：高血區 +2、中血區 +1（吸血在 Papyrus 開印本體）
            layers += zone == 1 ? 2 : zone == 2 ? 1 : 0;
        }
        rule::AddBleed(plan, target, RoundStochastic(static_cast<float>(layers) * mult, rng), in, nodes);
        break;
    }
    case kDivine: {
        // 聖印就是神聖印記本身；你的聖佑升一階（各階成熟 2 秒，同命中）；聖啟：同調三段時直接到 II。
        rule::RaiseHoly(plan, self, 1, in, nodes);
        if (nodes.Has(node::kDivineDawn) && t.syncStage >= 3 && HolyTier(self) < 2) {
            rule::SetHoly(plan, self, 2, in, nodes);
        }
        if (nodes.Has(node::kDivineMercy)) {   // 慈光：開印時懲戒 +2（不需要聖佑 II）
            const int layers = std::min(n3::kPunishCap, self.Layers(StatusKind::kPunish) + n3::kMercy);
            Writer{ plan, self, Who::kPlayer }.Set(StatusKind::kPunish, static_cast<float>(layers), Scaled(t, n3::kPunish));
        }
        break;
    }
    case kPoison: {
        int doses = n3::kDoseOpen + nodes.Rank(node::kPoisonOpenDoses) / 3;   // 淬毒：3 劑（+1／每 3 點）
        if (nodes.Has(node::kPoisonToxicStart) && t.syncStage >= 3) {
            doses *= 2;   // 劇毒之始
        }
        rule::AddDoses(plan, target, static_cast<float>(RoundStochastic(static_cast<float>(doses) * mult, rng)), in, nodes);
        break;
    }
    case kWater: {
        const bool lock = nodes.Has(node::kWaterOceanStart) && t.syncStage >= 3;   // 汪洋之始
        tw.Set(StatusKind::kSoak, lock ? 2.0f : 1.0f, lock ? n3::kSoakLocked : rule::SoakSeconds(t, nodes));
        plan.Push(Amount(Op::kSlow, SoakSlowPct(t) * mult, 0, rule::SoakSeconds(t, nodes)));   // 浸濕：減速 15%
        if (nodes.Has(node::kWaterDeepSoak) && nodes.Has(node::kWaterPressure) && t.envWet) {
            rule::SetPressure(plan, target, PressureCap(nodes), in, nodes);   // 深濕：水壓直接滿格（立即沖刷）
        }
        break;
    }
    case kDarkness:
        rule::AddCurse(plan, target, RoundStochastic(static_cast<float>(n3::kCurseOpen + nodes.Rank(node::kDarkOpenCurse) / 5) * mult, rng), in, nodes);
        if (nodes.Has(node::kDarkPhantom)) {
            // 幻影：開印後 3 秒目標對你的命中 30% 落空——目標帶幻影效果，你的 PERK（受到的傷害 ×0，條件：攻擊者帶幻影
            // 且 GetRandomPercent < 30）每一擊各擲一次（指揮官裁定 (c)）。
            tw.Set(StatusKind::kPhantom, 1.0f, Scaled(t, n3::kPhantom));
        }
        break;
    case kAstral:
        rule::AddStars(plan, target, 1, in, nodes);   // 星痕 1 層並進入共鳴
        if (nodes.Has(node::kAstralLock)) {
            tw.Set(StatusKind::kStarLock, 1.0f, Scaled(t, n3::kStarLock));   // 星鎖
        }
        if (nodes.Has(node::kAstralRadiance) && t.syncStage >= 3) {
            rule::DetonateStars(plan, target, self, in, nodes, n3::kRadiance);   // 星耀：延遲星傷改為立即並 ×2
        }
        break;
    default:
        break;
    }
    if (cutFrom == kBlood && nodes.Has(node::kBloodLead)) {
        rule::AddBleed(plan, target, n3::kBloodLead, in, nodes);   // 血引：血終焉後接管元素的開印附帶流血 2 層
    }
    if (cutFrom == kDivine && nodes.Has(node::kDivineLead)) {
        plan.Push(Amount(Op::kHeal, c.damage[kDivine][1] * t.multRecovery));   // 聖引：接管元素的開印治療你 B_max
    }
}

// 5.x 關閉專精主線 "終焉後 5 秒內接管元素附傷": only the trees whose own table has it there (ruling R2 of round 21).
constexpr bool HasTakeoverLine(int element) noexcept
{
    return element == kFrost || element == kLightning || element == kDivine || element == kPoison ||
           element == kWater || element == kAstral;
}

// The state part of one mark's end (2.6) on `target`, and the end event with what the Papyrus body needs:
//   fire       value1 heat tier the detonation uses, value2 consumption bonus (incl. 爆燃的消耗加成), value3 熾焰 ×1.5
//   frost      value1 1 when the target was frozen (the DLL shattered it; Papyrus does 碎甲 / 冰崩 / 冰河), else 0
//   lightning  value1 R (1.5 for a power hit that cut), value2 the crit draw in [0, 1), value3 1 for a cutting power hit
//   blood      value1 bleed remaining (strength × seconds) the surge settles; the bleed is removed here
//   divine     value1 聖佑 tier (judgment's holy bonus)
// `allowed` is false inside the target's 1 s end cooldown: the mark still goes, nothing reacts.
// 2.7 M_mod of an end: (1 + common 終焉 +1%／點 + 終焉再 +1%／點 [+ 同調三段時終焉 +1%／點 at sync 3]) × (1 + the
// tree's 關閉新手主線 終焉 +2%／點), each ×NodeScale -- the same factors ESSBNodes.CommonEndMult × ESSBElem.EndMult use.
template <NodeReader Nodes>
constexpr float EndNodeMult(int element, const Tuning& t, const Nodes& nodes)
{
    float common = 1.0f + Pct(t, nodes.Rank(node::kCommonEnd), 0.01f) + Pct(t, nodes.Rank(node::kCommonEndAgain), 0.01f);
    if (t.syncStage >= 3) {
        common += Pct(t, nodes.Rank(node::kCommonSyncEnd), 0.01f);
    }
    return common * (1.0f + Pct(t, nodes.Rank(node::kEndMain[element]), 0.02f));
}

template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanEndBody(StatusPlan& plan, int element, EndReason reason, float mult, bool power, Board& target,
    Board& self, const StatusInputs& in, const Nodes& nodes, Rng& rng, bool chain = false)
{
    const Tuning& t = *in.tuning;
    const Writer tw{ plan, target, Who::kTarget };
    const Writer pw{ plan, self, Who::kPlayer };
    tw.Set(StatusKind::kEndCooldown, 1.0f, CooldownOf(t, n3::kReactionCooldown));
    const bool cut = reason == EndReason::kCut;
    if (target.Has(StatusKind::kGuided)) {
        mult *= target[StatusKind::kGuided].magnitude;   // 導引：接管元素的下一次終焉 ×1.5
        tw.Clear(StatusKind::kGuided);
    }
    // The end's own damage the DLL settles (the end shatter, the fire end's DoT conversion, catalysis, the death curse)
    // takes the end node multipliers of 2.7 (common 終焉 / 終焉再 / 同調三段時終焉 × the tree's 終焉 main line), like the
    // Papyrus bodies do (ESSBReactions.End); a chain end takes none. 協奏、三重奏、過載終焉 read Papyrus state (N4).
    const float settle = chain ? mult : mult * EndNodeMult(element, t, nodes);
    std::array<float, 3> value{};
    switch (element) {
    case kFire: {
        const int heat = std::max(HeatTier(self), self.Layers(StatusKind::kVentedHeat));
        pw.Clear(StatusKind::kVentedHeat);
        const bool keep = nodes.Has(node::kFireFierce);   // 猛爆：吃了加成但東西還在
        float bonus = 0.0f;
        int consumed = 0;
        auto ladder = [&](StatusKind kind, int cap) {
            const int layers = target.Layers(kind);
            if (layers > 0 && cap > 0) {
                bonus += std::min(n3::kConsumeCap, n3::kConsumeUnit * 3.0f * static_cast<float>(layers) / static_cast<float>(cap));
                ++consumed;
                if (!keep) {
                    tw.Clear(kind);
                }
            }
        };
        auto single = [&](StatusKind kind) {
            if (target.Has(kind)) {
                bonus += n3::kConsumeUnit;
                ++consumed;
                if (!keep) {
                    tw.Clear(kind);
                }
            }
        };
        ladder(StatusKind::kFreeze, n3::kFreezeCap);
        ladder(StatusKind::kCurse, CurseCap(t, nodes));
        ladder(StatusKind::kPressure, PressureCap(nodes));
        single(StatusKind::kFissure);
        single(StatusKind::kSoak);
        single(StatusKind::kUnbalance);
        if (!keep && target.Has(StatusKind::kFrozen)) {
            tw.Clear(StatusKind::kFrozen);
            tw.Clear(StatusKind::kCrystal);
        }
        // 血痕與中毒的剩餘傷害 50% 轉為即時火傷並移除（猛爆：照算、不移除）。
        const float dots = target.bleedDot.magnitude * target.bleedDot.Remaining() + target.poisonDot.magnitude * target.poisonDot.Remaining();
        if (dots > 0.0f) {
            const float domain = target.Has(StatusKind::kDomainFire) ? n3::kDomain : 1.0f;   // 火域：受火傷 +20%
            plan.Push(Amount(Op::kDamage, dots * n3::kConsumeDotShare * settle * domain, kFire));
            consumed += (target.bleedDot.has ? 1 : 0) + (target.poisonDot.has ? 1 : 0);
            if (!keep) {
                plan.Push(MakeOp(Op::kRemoveDots));
                tw.Clear(StatusKind::kBleed);
                tw.Clear(StatusKind::kCatalyzed);
                target.bleedDot = Slot{};
                target.poisonDot = Slot{};
            }
        }
        if (target.Has(StatusKind::kStar)) {
            ++consumed;
            rule::DetonateStars(plan, target, self, in, nodes, 1.0f);   // 星痕立即引爆
        }
        bonus += Pct(t, nodes.Rank(node::kFireConsume), 0.01f) * static_cast<float>(consumed);   // +1%／點 × 被消耗的狀態數
        value = { static_cast<float>(heat), bonus, heat >= 3 && nodes.Has(node::kFireBlaze) ? n3::kBlaze : 1.0f };
        break;
    }
    case kFrost:
        if (target.Has(StatusKind::kFrozen)) {
            rule::Shatter(plan, target, in, nodes, 2, settle);
            value[0] = 1.0f;
        }
        break;
    case kLightning: {
        const bool hitCut = cut && power;
        value = { hitCut ? 1.5f : 1.0f, rng.Real(0.0f, 1.0f), hitCut ? 1.0f : 0.0f };
        break;
    }
    case kWind:
        tw.Clear(StatusKind::kUnbalance);   // 吹飛：失衡被吹掉
        break;
    case kBlood:
        value[0] = target.bleedDot.magnitude * target.bleedDot.Remaining();   // 剩餘強度 × 剩餘秒數
        if (target.bleedDot.has) {
            plan.Push(Amount(Op::kBleedDot, 0.0f, 0, 0.0f));   // 0 strength = remove the bleed DoT
            target.bleedDot = Slot{};
        }
        tw.Clear(StatusKind::kBleed);
        break;
    case kDivine:
        value[0] = static_cast<float>(HolyTier(self));
        break;
    case kPoison:
        if (target.poisonDot.has) {
            // 催毒：同一顆效果重套，強度 ×2（潰爛 ×3；催毒期間中毒傷害 +3%／點）、時長＝剩餘（延毒 +4 秒）。
            float factor = nodes.Has(node::kPoisonFester) ? n3::kFester : n3::kCatalyze;
            factor *= 1.0f + Pct(t, nodes.Rank(node::kSignature[kPoison]), 0.03f);
            const float remaining = target.poisonDot.Remaining() + (nodes.Has(node::kPoisonLinger) ? Scaled(t, n3::kPoisonLinger) : 0.0f);
            // The marker keeps the whole multiplier on the base doses (a second catalysis multiplies it again).
            const float whole = rule::PoisonFactor(target) * factor * settle;
            tw.Set(StatusKind::kCatalyzed, whole, remaining);
            const rule::Poison next{ target.poisonDot.magnitude * factor * settle, remaining };
            rule::SetPoison(plan, target, next, in, nodes);
        }
        break;
    case kWater:
        if (cut) {
            // 導引（強引 ×2.0；關閉傳奇主線 +3%／點）掛在目標身上，接管元素的下一次終焉讀它。
            const float guide = (nodes.Has(node::kWaterStrongGuide) ? n3::kStrongGuide : n3::kGuide) *
                                (1.0f + Pct(t, nodes.Rank(node::kSignature[kWater]), 0.03f));
            tw.Set(StatusKind::kGuided, guide * mult, Scaled(t, 30.0f));
        }
        if (target.Has(StatusKind::kSoak) && target[StatusKind::kSoak].magnitude > 1.5f) {
            tw.Set(StatusKind::kSoak, 1.0f, rule::SoakSeconds(t, nodes));   // 汪洋之始的鎖在被切／結束時解開
        }
        if (nodes.Has(node::kWaterOcean)) {
            tw.Set(StatusKind::kSoak, 1.0f, Scaled(t, n3::kOcean));   // 汪洋：浸濕延長到 30 秒
        }
        if (nodes.Has(node::kWaterEbb) && reason != EndReason::kExpire && !target.Has(StatusKind::kWashCooldown)) {
            tw.Set(StatusKind::kWashCooldown, 1.0f, CooldownOf(t, n3::kWashCooldown));   // 退潮：被切或融斷時沖刷一次
            plan.Push(Amount(Op::kWash, nodes.Has(node::kWaterPurgeTide) ? 2.0f * in.config->damage[kWater][1] : 0.0f));
        }
        break;
    case kDarkness: {
        // 死咒：3 秒引信（強度＝本次終焉倍率 × 死咒 +3%／點），到期結算（OnDeathCurseEnd）；冥印：暗印記被切時留 8 秒。
        const float fuse = settle * (1.0f + Pct(t, nodes.Rank(node::kSignature[kDarkness]), 0.03f));
        tw.Set(StatusKind::kDeathCurse, fuse, Scaled(t, n3::kDeathCurse));
        if (cut && nodes.Has(node::kDarkNether)) {
            tw.Set(StatusKind::kNether, 1.0f, Scaled(t, 8.0f));
        }
        break;
    }
    case kAstral:
        if (target.Has(StatusKind::kStar)) {
            rule::DetonateStars(plan, target, self, in, nodes, 1.0f);   // 星落：本人的星痕立即引爆（其他共鳴目標的掃描 N5）
        }
        break;
    default:
        break;
    }
    if (cut && !chain && HasTakeoverLine(element)) {
        const float boost = Pct(t, nodes.Rank(node::kTakeover[element]), 0.01f);   // 終焉後 5 秒內接管元素附傷 +1%／點
        if (boost > 0.0f) {
            pw.Set(StatusKind::kEndBoost, boost, Scaled(t, n3::kEndWindow));
        }
    }
    if (cut && !chain && nodes.Has(node::kCommonResidual) && !target.Has(StatusKind::kResidual)) {
        tw.Set(StatusKind::kResidual, static_cast<float>(element), Scaled(t, n3::kResidualSeconds));   // 疊印
    }
    plan.Push(MakeEvent(Event::kEnd, element, static_cast<int>(reason), mult, chain ? 1 : 0, value[0], value[1], value[2]));
}

// One mark's end by a cut or a burst: the mark goes; inside the target's 1 s end cooldown nothing else happens.
template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanEnd(StatusPlan& plan, int element, EndReason reason, float mult, bool power, Board& target,
    Board& self, const StatusInputs& in, const Nodes& nodes, Rng& rng)
{
    Writer{ plan, target, Who::kTarget }.Unmark(element);
    if (!target.Has(StatusKind::kEndCooldown)) {
        PlanEndBody(plan, element, reason, mult, power, target, self, in, nodes, rng);
    }
}

// ================================================================ one element hit

struct HitStatus {
    int cutFrom = 0;       // the element this hit cut (0 none)
    bool opened = false;   // this hit opened its mark (the open reaction ran)
};

// v0.4 2.2 + 2.3 for one accepted hit of the form's `element` (or 雙生's left-hand element). The target's board and
// the player's board are the pre-hit reads; they are updated in place as the plan grows. hitWork = false is a forced
// open without a hit (Papyrus 臨 / 雙斷): the mark (cut, open) only.
template <NodeReader Nodes, RandomSource Rng>
constexpr HitStatus PlanStatusHit(StatusPlan& plan, int element, bool power, Board& target, Board& self,
    const StatusInputs& in, const Nodes& nodes, Rng& rng, bool hitWork = true)
{
    const Tuning& t = *in.tuning;
    const Config& c = *in.config;
    HitStatus result;
    const Writer tw{ plan, target, Who::kTarget };
    const Writer pw{ plan, self, Who::kPlayer };

    // ---- the mark
    const bool refresh = target.mark[element].has;
    bool linger = false;
    float openMult = 1.0f + Pct(t, nodes.Rank(node::kOpenEffect[element]), 0.03f);   // 開啟傳奇主線：開印效果 +3%／點
    if (!refresh) {
        const int others = target.MarkCount();
        const bool dual = nodes.Has(node::kCommonDualMark);
        if (others > 0 && !(dual && others < 2)) {
            // 被切：先舊終焉、再驅散、再新開印（雙印：切掉較舊的那個）。
            const int old = target.OldestMark(element);
            PlanEnd(plan, old, EndReason::kCut, 1.0f, power, target, self, in, nodes, rng);
            result.cutFrom = old;
            linger = old == kFrost && nodes.Has(node::kFrostLinger);           // 寒留
            if (old == kFire && nodes.Has(node::kFireEmber)) {
                openMult *= n3::kEmber;                                        // 餘燼
            }
            if (old == kWater && target.Has(StatusKind::kSoak) && target[StatusKind::kSoak].magnitude > 1.5f) {
                tw.Set(StatusKind::kSoak, 1.0f, rule::SoakSeconds(t, nodes));
            }
        }
    }
    tw.Mark(element, rule::MarkSeconds(element, t, nodes, linger));
    if (!refresh && !target.Has(StatusKind::kOpenCooldown)) {
        tw.Set(StatusKind::kOpenCooldown, 1.0f, CooldownOf(t, n3::kReactionCooldown));
        PlanOpenState(plan, element, openMult, result.cutFrom, target, self, in, nodes, rng);
        plan.Push(MakeEvent(Event::kOpen, element, openMult, result.cutFrom, hitWork ? 1 : 0));
        result.opened = true;
    }

    if (!hitWork) {
        return result;   // a forced open (臨, 雙斷): the mark and its open only, no hit
    }

    // ---- the element's status on a refreshing hit (2.3 命中欄)
    if (refresh) {
        switch (element) {
        case kFire:
            rule::RaiseHeat(plan, self, power && nodes.Has(node::kFireBrand) ? 2 : 1, in, nodes);   // 烙印：重擊兩階
            break;
        case kFrost:
            if (target.Has(StatusKind::kFrozen)) {
                if (power) {
                    rule::Shatter(plan, target, in, nodes, 1);   // 冰封中的重擊（含倒地目標的每一擊）碎冰
                } else if (target.Layers(StatusKind::kCrystal) < n3::kCrystalCap) {
                    // 冰封中的普攻：冰晶 +1（上限 3，不刷新冰封時間）。
                    tw.Set(StatusKind::kCrystal, static_cast<float>(target.Layers(StatusKind::kCrystal) + 1),
                        target[StatusKind::kFrozen].Remaining() + n3::kCrystalMargin);   // 冰封結束後多留 1 秒（凍傷讀得到）
                }
            } else {
                float amount = power ? (nodes.Has(node::kFrostErode) ? 3.0f : 2.0f) : 1.0f;   // 命中 +1、重擊 +2（寒蝕 +3）
                amount *= 1.0f + n3::kFreezePerPoint * static_cast<float>(nodes.Rank(node::kFrostAccumulate));
                rule::AddFreeze(plan, target, amount, power && nodes.Has(node::kFrostErode), in, nodes, rng);
            }
            break;
        case kBlood:
            rule::AddBleed(plan, target, 1, in, nodes);
            break;
        case kPoison:
            rule::AddDoses(plan, target, power ? 2.0f : 1.0f, in, nodes);   // 命中 +1、重擊 +2
            break;
        case kWater:
            if (target.Has(StatusKind::kSoak)) {
                const bool locked = target[StatusKind::kSoak].magnitude > 1.5f;
                tw.Set(StatusKind::kSoak, locked ? 2.0f : 1.0f, locked ? n3::kSoakLocked : rule::SoakSeconds(t, nodes));
            }
            break;
        case kDarkness:
            rule::AddCurse(plan, target, 1 + (target.frenzied && nodes.Has(node::kDarkConfusion) ? n3::kConfusion : 0), in, nodes);
            break;
        case kAstral:
            rule::AddStars(plan, target, 1, in, nodes);
            break;
        default:
            break;
        }
    }

    // ---- every hit of the element, open or not
    if (element == kFrost && in.iceArmor && !target.Has(StatusKind::kFrozen)) {
        // 冰甲：你命中寒氣內的敵人時凍結再 +1（霜膚：寒氣 5 公尺）。
        const float radius = nodes.Has(node::kFrostSkin) ? n3::kFrostSkin : n3::kIceArmor;
        if (in.body.distanceToPlayer <= radius) {
            rule::AddFreeze(plan, target, 1.0f, false, in, nodes, rng);
        }
    }
    if (element == kWater && nodes.Has(node::kWaterPressure) && (target.Has(StatusKind::kSoak) || t.envWet)) {
        rule::SetPressure(plan, target, target.Layers(StatusKind::kPressure) + 1, in, nodes);   // 水壓：命中浸濕目標 +1
    }
    if (element == kDivine) {
        if (refresh) {
            rule::RaiseHoly(plan, self, 1, in, nodes);   // 命中帶神聖印記的目標升一階（成熟 2 秒）
        }
        const int holy = HolyTier(self);
        if (n3::kHolyHeal[holy] > 0.0f) {
            plan.Push(Amount(Op::kHeal, c.damage[kDivine][1] * n3::kHolyHeal[holy] * t.multRecovery));   // II／III 命中回血
        }
        // 聖裁計數：聖形態命中 +1（4 秒），第三擊觸發（神罰：第二擊）。
        const int needed = nodes.Has(node::kDivineRetribution) ? 2 : n3::kJudgeHits;
        const int count = target.Layers(StatusKind::kJudge) + 1;
        if (count >= needed) {
            tw.Clear(StatusKind::kJudge);
            float damage = 0.0f;
            if (holy >= 3) {
                damage = in.body.healthMax * (in.body.vip ? n3::kJudgeTopVip : n3::kJudgeTop) * t.baseDamageMult;
            } else {
                damage = c.damage[kDivine][1] * n3::kJudgeBase * ReactionScale(kDivine, t, in.player, nodes);
            }
            damage *= 1.0f + n3::kHolyProc[holy] + Pct(t, nodes.Rank(node::kDivineHolyBonus), 0.01f) * static_cast<float>(holy);
            damage *= 1.0f + Pct(t, nodes.Rank(node::kDivineJudgeDamage), 0.02f);   // 聖裁傷害 +2%／點
            const bool prey = in.body.undeadOrDaedra || (nodes.Has(node::kDivineStigma) && target.mark[kDivine].has);
            if (prey) {
                damage *= n3::kPrey;
            }
            damage *= ReactionVulnerability(target, self, t, nodes);
            const int punish = self.Layers(StatusKind::kPunish);   // 懲戒：每層 +20%，用過清空
            if (punish > 0) {
                damage *= 1.0f + n3::kPunishPerLayer * static_cast<float>(punish);
                Writer{ plan, self, Who::kPlayer }.Clear(StatusKind::kPunish);
            }
            plan.Push(Amount(Op::kDamage, damage, kDivine));
            if (holy >= 2) {
                plan.Push(MakeEvent(Event::kJudgment, holy));
            }
        } else {
            tw.Set(StatusKind::kJudge, static_cast<float>(count), Scaled(t, n3::kJudge));
        }
    }
    if (element == kBlood) {
        // 越線（5.8）：你身上的血區標記與現在的生命比對；換區就換標記，冷卻外觸發（往下＝濺血，往上＝回湧 N4）。
        const int zone = BloodZone(in.self);
        const int marked = self.Layers(StatusKind::kBloodZone);
        if (marked != zone) {
            pw.Set(StatusKind::kBloodZone, static_cast<float>(zone), 86400.0f);
            if (marked != 0 && zone > marked && !self.Has(StatusKind::kCrossCooldown)) {
                pw.Set(StatusKind::kCrossCooldown, 1.0f, CooldownOf(t, n3::kCross));
                // 濺血：15 公尺內所有流血目標（最多 5）一次 ×0.5 血潮、不清除血痕（掃描 N5 前在 Papyrus）。
                plan.Push(MakeEvent(Event::kSplash, target.bleedDot.magnitude * target.bleedDot.Remaining()));
            } else if (marked != 0 && zone < marked && !self.Has(StatusKind::kCrossCooldown)) {
                pw.Set(StatusKind::kCrossCooldown, 1.0f, CooldownOf(t, n3::kCross));   // 回湧的效果是 N4
                plan.Push(MakeEvent(Event::kRise));   // 血約（往上越線時 15 公尺內流血目標 +2 層）的掃描在 Papyrus
            }
        }
    }
    return result;
}

// ================================================================ when a status runs out

// The flag bits a mark carries in its magnitude (n3::kMarkJumped, n3::kMarkExtended); a plain mark is 0.
constexpr int MarkFlags(float magnitude) noexcept
{
    return magnitude > 0.0f ? static_cast<int>(magnitude + 0.5f) : 0;
}

// A mark ran out on its own (the effect-removed event said "expired"; `flags` = MarkFlags of the gone effect): the
// expiry end, ×1, no takeover (2.6). 咒延 (5.12): a darkness mark on a target with >= 3 curse layers is instead re-applied
// for 4 s, once per mark, and ends then -- returns false in that case (no end now, nothing to jump).
template <NodeReader Nodes, RandomSource Rng>
constexpr bool OnMarkExpired(StatusPlan& plan, int element, int flags, Board& target, Board& self, const StatusInputs& in,
    const Nodes& nodes, Rng& rng)
{
    if (element == kDarkness && nodes.Has(node::kDarkLinger) && (flags & n3::kMarkExtended) == 0 &&
        target.Layers(StatusKind::kCurse) >= n3::kCurseLingerAt) {
        Writer{ plan, target, Who::kTarget }.FlaggedMark(element, Scaled(*in.tuning, n3::kCurseLinger), flags | n3::kMarkExtended);
        return false;
    }
    target.mark[element] = Slot{};   // already gone from the engine: nothing to dispel
    if (!target.Has(StatusKind::kEndCooldown)) {
        PlanEndBody(plan, element, EndReason::kExpire, 1.0f, false, target, self, in, nodes, rng);
    }
    return true;
}

// 冰封 ended by time (not by a shatter): the gauge empties (永凍 keeps half), unshattered crystals are lost — 凍傷 turns
// each into a B_max ×0.5 frost hit first.
template <NodeReader Nodes>
constexpr void OnFrozenEnd(StatusPlan& plan, Board& target, const Board& self, const StatusInputs& in, const Nodes& nodes,
    int carriedCrystals = 0)
{
    const Writer tw{ plan, target, Who::kTarget };
    const int crystals = std::max(target.Layers(StatusKind::kCrystal), carriedCrystals);
    if (crystals > 0 && nodes.Has(node::kFrostFrostbite)) {
        const float each = in.config->damage[kFrost][1] * n3::kFrostbite * ReactionScale(kFrost, *in.tuning, in.player, nodes) *
                           ReactionVulnerability(target, self, *in.tuning, nodes);
        plan.Push(Amount(Op::kDamage, each * static_cast<float>(crystals), kFrost));
    }
    tw.Clear(StatusKind::kCrystal);
    if (nodes.Has(node::kFrostPermafrost)) {
        tw.Set(StatusKind::kFreeze, static_cast<float>(n3::kFreezeCap / 2), Scaled(*in.tuning, n3::kFreezeGauge));
    } else {
        tw.Clear(StatusKind::kFreeze);
    }
}

// 星痕 fuse ran out (2 s without a direct hit): every layer detonates together.
template <NodeReader Nodes>
constexpr void OnStarFuseEnd(StatusPlan& plan, Board& target, const Board& self, const StatusInputs& in, const Nodes& nodes)
{
    target[StatusKind::kStarFuse] = Slot{};
    rule::DetonateStars(plan, target, self, in, nodes, 1.0f);
}

// 死咒 fuse ran out (not dispelled): B_max ×2.0 + lost health × (15% + 0.5%/point; 噬咒 +3% per curse layer it eats),
// × the fuse strength; 饕餮 leeches health and magicka B_max each.
template <NodeReader Nodes>
constexpr void OnDeathCurseEnd(StatusPlan& plan, float fuseMult, Board& target, const Board& self, const StatusInputs& in,
    const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    fuseMult *= ReactionVulnerability(target, self, t, nodes);
    const float bMax = in.config->damage[kDarkness][1];
    float ratio = n3::kDeathCurseLost + Pct(t, nodes.Rank(node::kDarkCurseLost), n3::kDeathCurseLostPerPoint);
    if (nodes.Has(node::kDarkDevour)) {
        ratio += n3::kDevour * static_cast<float>(target.Layers(StatusKind::kCurse));
        const Writer tw{ plan, target, Who::kTarget };
        tw.Clear(StatusKind::kCurse);
    }
    const float lost = std::max(0.0f, in.body.healthMax - in.body.health);
    const float damage = (bMax * n3::kDeathCurseBase * ReactionScale(kDarkness, t, in.player, nodes) + lost * ratio) * fuseMult;
    plan.Push(Amount(Op::kDamage, damage, kDarkness));
    if (nodes.Has(node::kDarkGlutton)) {
        plan.Push(Amount(Op::kHeal, bMax * t.multRecovery));
        plan.Push(Amount(Op::kRestoreMagicka, bMax * t.multRecovery));
    }
}

// 恐懼 or 瘋狂 ended: 回魘 deepens the curse by 2 layers.
template <NodeReader Nodes>
constexpr void OnHallucinationEnd(StatusPlan& plan, Board& target, const StatusInputs& in, const Nodes& nodes)
{
    if (nodes.Has(node::kDarkEcho)) {
        rule::AddCurse(plan, target, n3::kEchoCurse, in, nodes);
    }
}

// The white-hot fuse (or 熔燒) ran out without a vent: 熔爐 turns white-hot into 熔燒 for 6 s more; otherwise overheat:
// pay 10% of max health on the cost path (熔身: pay nothing, 10 s of 熔身 instead), heat to zero (熔心: 微熱). The
// 15 m detonation of fire-marked targets is a range scan (N5).
template <NodeReader Nodes>
constexpr void OnFuseEnd(StatusPlan& plan, int tier, Board& self, const StatusInputs& in, const Nodes& nodes)
{
    const Writer pw{ plan, self, Who::kPlayer };
    self[HeatKind(tier)] = Slot{};
    if (tier == 3 && nodes.Has(node::kFireForge)) {
        rule::SetHeat(plan, self, 4, in, nodes);
        return;
    }
    pw.Clear(StatusKind::kFireBath);
    if (nodes.Has(node::kFireMoltenBody)) {
        rule::SetHeat(plan, self, 0, in, nodes);
        pw.Set(StatusKind::kMoltenBody, 1.0f, Scaled(*in.tuning, n3::kMolten));
        return;
    }
    plan.Push(Amount(Op::kPayHealth, in.self.healthMax * n3::kOverheatCost));
    rule::SetHeat(plan, self, nodes.Has(node::kFireMoltenCore) ? 1 : 0, in, nodes);
}

// Leaving a form (switch or Z). Your fire heat vents: white-hot or higher records the tier the next detonation uses
// (洩壓: 爆燃照熱度算), then heat → 0, 熔心 keeps 微熱, 餘壓 keeps 灼熱 and the fire source for 2 s more. 聖佑 clears
// (神聖領域: a burst at III keeps it). Other self resources are Papyrus' until N4.
template <NodeReader Nodes>
constexpr void OnFormLeave(StatusPlan& plan, int element, bool burst, Board& self, const StatusInputs& in, const Nodes& nodes)
{
    const Writer pw{ plan, self, Who::kPlayer };
    if (element == kFire && burst && nodes.Has(node::kFireMeltdown)) {
        // 熔斷（5.3，v0.4 標 DLL N5）：融斷後熱度保留——熱度本來就是你身上的階，什麼都不動即可。
    } else if (element == kFire) {
        const int tier = HeatTier(self);
        if (tier >= 3) {
            pw.Set(StatusKind::kVentedHeat, static_cast<float>(tier), Scaled(*in.tuning, 30.0f));
            pw.Clear(StatusKind::kMoltenBody);
            pw.Clear(StatusKind::kFireBath);
            if (nodes.Has(node::kFireResidualPressure)) {
                rule::SetHeat(plan, self, 2, in, nodes);
                pw.Set(StatusKind::kSourceLinger, 1.0f, Scaled(*in.tuning, n3::kSourceLinger));
            } else {
                rule::SetHeat(plan, self, nodes.Has(node::kFireMoltenCore) ? 1 : 0, in, nodes);
            }
        } else {
            rule::SetHeat(plan, self, 0, in, nodes);
        }
    }
    if (element == kDivine) {
        const bool keep = burst && HolyTier(self) == 3 && nodes.Has(node::kDivineHolyDomain);
        if (!keep) {
            rule::SetHoly(plan, self, 0, in, nodes);
        }
        pw.Clear(StatusKind::kPunish);   // 懲戒：離開形態清空
    }
}

// ================================================================ the DLL timer (per tick)

// Ladder decay, polled each tick: 微熱／灼熱 step down when their 6 s decay timer is gone (火種: never), 聖佑 steps down
// when its 8 s timer is gone. A step down starts the lower tier with a fresh timer.
template <NodeReader Nodes>
constexpr void PlanDecay(StatusPlan& plan, Board& self, const StatusInputs& in, const Nodes& nodes)
{
    const int heat = HeatTier(self);
    if ((heat == 1 || heat == 2) && !self.Has(StatusKind::kHeatDecay) && !nodes.Has(node::kFireTinder)) {
        rule::SetHeat(plan, self, heat - 1, in, nodes);
    }
    const int holy = HolyTier(self);
    if (holy > 0 && !self.Has(StatusKind::kHolyDecay)) {
        rule::SetHoly(plan, self, holy - 1, in, nodes);
    }
}

// White-hot: you are the fire source. Per second, each hostile within 3 m (熔燒 4.5 m) takes
// (B_max × 0.25 × G + cost × N) × M_mod(火附傷純百分比主線) fire damage and gets the fire mark (no open).
struct FireSource {
    bool active = false;
    float radius = 0.0f;
    float perEnemy = 0.0f;   // damage override per enemy
    float cost = 0.0f;       // your health paid this second (the cost path)
};

template <NodeReader Nodes>
constexpr FireSource PlanFireSource(const Board& self, const StatusInputs& in, const Nodes& nodes)
{
    FireSource source;
    const int tier = HeatTier(self);
    source.active = tier >= 3 || self.Has(StatusKind::kSourceLinger);
    if (!source.active) {
        return source;
    }
    const Tuning& t = *in.tuning;
    const bool forge = tier == 4;
    source.radius = forge ? n3::kForgeSourceRadius : n3::kSourceRadius;
    source.cost = in.self.healthMax * n3::kSourceCost;   // 熔身 waives the overheat's 10%, not the source's 0.5%/s
    float n = n3::kSourceN + std::min(n3::kSourceNMax - n3::kSourceN, n3::kSourceNPerPoint * static_cast<float>(nodes.Rank(node::kFireSourceN)));
    if (forge) {
        n += n3::kForgeN;
    }
    if (t.syncStage >= 3) {
        n += n3::kInfernoPerPoint * static_cast<float>(nodes.Rank(node::kFireInferno));
    }
    const float base = in.config->damage[kFire][1] * n3::kSourceBase * TreeG(t, TreeOf(kFire)) * t.baseDamageMult;
    source.perEnemy = (base + source.cost * n) * NodeSum(kFire, false, t, nodes);
    return source;
}

// ================================================================ records (pure: local FormIDs, the engine resolves them)

// What one of our effect records stands for on an actor's effect list.
enum class TagKind : std::uint8_t
{
    kNone,
    kStatus,     // index = StatusKind
    kMark,       // index = element
    kBleedDot,
    kPoisonDot,
    kFear,
    kFrenzy,
    kSlow,       // our shared slow (the strongest of them is Board::maxSlowPct)
};

struct Tag {
    TagKind kind = TagKind::kNone;
    int index = 0;
};

// The effect record (local FormID) -> what it is. Plugin.cpp builds its pointer table from this, so the engine read and
// the tests use one mapping.
constexpr Tag TagOf(std::uint32_t effect) noexcept
{
    for (int k = 0; k < kStatusKindCount; ++k) {
        if (kStatusRecords[k].effect == effect) {
            return { TagKind::kStatus, k };
        }
    }
    for (int e = kFire; e <= kAstral; ++e) {
        if (status::kMarkEffect[e] == effect) {
            return { TagKind::kMark, e };
        }
    }
    if (effect == status::kBleedDotEffect) {
        return { TagKind::kBleedDot, 0 };
    }
    if (effect == status::kPoisonDotEffect) {
        return { TagKind::kPoisonDot, 0 };
    }
    if (effect == status::kFearEffect) {
        return { TagKind::kFear, 0 };
    }
    if (effect == status::kFrenzyEffect) {
        return { TagKind::kFrenzy, 0 };
    }
    if (effect == status::kSlowEffect) {
        return { TagKind::kSlow, 0 };
    }
    return {};
}

// Which of our effects settle when they run out (their records carry the stub script; build/fix22_records.py).
constexpr bool Settles(const Tag& tag) noexcept
{
    if (tag.kind == TagKind::kMark || tag.kind == TagKind::kFear || tag.kind == TagKind::kFrenzy) {
        return true;
    }
    return tag.kind == TagKind::kStatus && kStatusRecords[tag.index].stub &&
           static_cast<StatusKind>(tag.index) != StatusKind::kMoltenBody;
}

// One running effect as the engine reports it (Plugin.cpp: base form -> local id, ActiveEffect fields).
struct RawEffect {
    std::uint32_t effect = 0;  // local FormID of the base effect
    float magnitude = 0.0f;
    float elapsed = 0.0f;
    float duration = 0.0f;
};

constexpr void Keep(Slot& slot, const RawEffect& effect) noexcept
{
    const float remaining = effect.duration - effect.elapsed;
    if (slot.has && slot.Remaining() >= remaining) {
        return;   // two instances (never ours on purpose): the longer-lasting one counts
    }
    slot = Slot{ true, effect.magnitude, effect.elapsed, effect.duration };
}

constexpr void Read(Board& board, const RawEffect& effect) noexcept
{
    const Tag tag = TagOf(effect.effect);
    switch (tag.kind) {
    case TagKind::kStatus:
        Keep(board.slot[tag.index], effect);
        break;
    case TagKind::kMark:
        Keep(board.mark[tag.index], effect);
        break;
    case TagKind::kBleedDot:
        Keep(board.bleedDot, effect);
        break;
    case TagKind::kPoisonDot:
        Keep(board.poisonDot, effect);
        break;
    case TagKind::kFear:
        board.fearing = true;
        break;
    case TagKind::kFrenzy:
        board.frenzied = true;
        break;
    case TagKind::kSlow:
        board.maxSlowPct = std::max(board.maxSlowPct, effect.magnitude);
        break;
    case TagKind::kNone:
        break;
    }
}

// effectiveness = wanted / record seconds scales the duration of a No Magnitude effect (ledger D1); exactly 1 when the
// record length is wanted, so a spell that also carries magnitude effects (聖佑's tier) is never scaled.
constexpr float EffectivenessFor(float seconds, float recordSeconds) noexcept
{
    const float gap = seconds - recordSeconds;
    if (recordSeconds <= 0.0f || seconds <= 0.0f || (gap < 0.001f && gap > -0.001f)) {
        return 1.0f;
    }
    return seconds / recordSeconds;
}

constexpr int WholeSeconds(float seconds, int maximum) noexcept
{
    return std::clamp(static_cast<int>(seconds + 0.5f), 1, maximum);
}

// The cast an op turns into: spell (local FormID), magnitude override, effectiveness, and the running instances that
// are dispelled first (0 = none). Remove ops have spell 0 and only the dispel.
struct Lowered {
    std::uint32_t spell = 0;
    float magnitude = 0.0f;
    float effectiveness = 1.0f;
    std::uint32_t dispelSpell = 0;    // every effect of this spell
    std::uint32_t dispelEffect = 0;   // every instance of this effect
    std::uint32_t dispelEffect2 = 0;  // a second effect (the other DoT)
    bool onPlayer = false;
};

constexpr Lowered Lower(const StatusOp& op, float slowCapPct) noexcept
{
    Lowered out;
    out.onPlayer = op.who == Who::kPlayer;
    switch (op.op) {
    case Op::kApply: {
        const StatusRecord& r = kStatusRecords[static_cast<int>(op.kind)];
        out.dispelSpell = r.spell;
        if (op.seconds > 0.0f) {
            out.spell = r.spell;
            out.magnitude = op.magnitude;
            out.effectiveness = EffectivenessFor(op.seconds, r.seconds);
        }
        break;
    }
    case Op::kRemove:
        out.dispelSpell = kStatusRecords[static_cast<int>(op.kind)].spell;
        break;
    case Op::kApplyMark:
        out.dispelEffect = status::kMarkEffect[op.element];
        out.spell = status::kMarkSpell[op.element];
        out.magnitude = op.magnitude;   // 0, or the flag bits of a 跳印 / 咒延 mark (MarkFlags)
        out.effectiveness = EffectivenessFor(op.seconds, status::kMarkRecordSeconds);
        break;
    case Op::kRemoveMark:
        out.dispelEffect = status::kMarkEffect[op.element];
        break;
    case Op::kBleedDot:
    case Op::kPoisonDot: {
        const bool bleed = op.op == Op::kBleedDot;
        out.dispelEffect = bleed ? status::kBleedDotEffect : status::kPoisonDotEffect;
        if (op.magnitude > 0.0f && op.seconds > 0.0f) {
            const int s = WholeSeconds(op.seconds, status::kDotMaxSeconds);
            out.spell = bleed ? status::kBleedDot[s - 1] : status::kPoisonDot[s - 1];
            out.magnitude = op.magnitude;   // Value Modifier: effectiveness stays 1 (it would scale the damage)
        }
        break;
    }
    case Op::kSlow: {
        const float pct = std::min(op.magnitude, std::clamp(slowCapPct, 0.0f, 70.0f));
        if (pct > 0.0f) {
            out.spell = spell::kSoak[WholeSeconds(op.seconds, kSoakSpellCount) - 1];   // the shared slow, one spell per second
            out.magnitude = pct;
        }
        break;
    }
    case Op::kDamage:
        if (op.magnitude > 0.0f) {
            out.spell = op.element == 0 ? spell::kTrueDamage : status::kReactSpell[op.element];
            out.magnitude = op.magnitude;
        }
        break;
    case Op::kBleedDrain:
        if (op.magnitude > 0.0f) {
            out.spell = spell::kBleedTick;
            out.magnitude = op.magnitude;
        }
        break;
    case Op::kHeal:
    case Op::kRestoreMagicka:
    case Op::kRestoreStamina:
        if (op.magnitude > 0.0f) {
            out.spell = op.op == Op::kHeal ? spell::kHeal : op.op == Op::kRestoreMagicka ? spell::kRestoreMagicka : spell::kRestoreStamina;
            out.magnitude = op.magnitude;
        }
        break;
    case Op::kRemoveDots:
        out.dispelEffect = status::kBleedDotEffect;
        out.dispelEffect2 = status::kPoisonDotEffect;
        break;
    case Op::kPayHealth:
    case Op::kWash:
    case Op::kEvent:
        break;   // not a cast (Plugin.cpp does these directly)
    }
    return out;
}

}  // namespace essb
