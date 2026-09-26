#pragma once
// Stage 3 of the native hit handler (round 20, slice N2): for one accepted hit, decide which spells the
// DLL casts and with which magnitude override. Pure: no engine, no allocation, no global state.
//   * engine facts arrive already read (EngineFacts.h builds them from mocked or real engine answers);
//   * every random draw goes through the Rng passed in, so tests can script the draws;
//   * the result is a Plan: an ordered list of casts, one magnitude override each. The override is
//     applied by the engine to every effect of a spell (native-verification-2 section 10: NO), so a
//     spell that needs two different magnitudes is split into two single-effect spells.
//
// Round 21 (v0.4 trees): the no-form 吸魔量 / 滅法倍率 / 燒魔倍數 lines, 寂滅 and 反擊 (their N2 halves, ruling R5)
// and the soaked slow's duration node (fixed-duration spells, ruling R6); every node is looked up by v0.4 name.
// Formula (v0.4 2.7):  D_hit = B x R x G(L) x BaseDamageMult x M_mod x T x C   (M_ext and Res: engine)
//   M_mod = (1 + sum of node percentages) x blood curve x blood rage x environment x undead x exorcism x wind sneak
// Round 22 (N3): the target-side and status terms (heat, open boost, frozen, holy vulnerability, pressure, ...) come
// from Status.h ProcTerms as StatusTerms; the Papyrus difference patch (ESSBController.ApplyProc) is gone.
#include "ManifestData.h"
#include "NodeIds.h"

#include <algorithm>
#include <array>
#include <concepts>
#include <cstdint>

namespace essb {

// ---------------------------------------------------------------- trees and the nodes N2 reads

inline constexpr int kTreeCount = 13;
inline constexpr int kElementCount = 11;
inline constexpr int kNoFormTree = 11;
inline constexpr int kCommonTree = 12;

enum Element : int
{
    kNoElement = 0,
    kFire = 1,
    kFrost = 2,
    kLightning = 3,
    kEarth = 4,
    kWind = 5,
    kBlood = 6,
    kDivine = 7,
    kPoison = 8,
    kWater = 9,
    kDarkness = 10,
    kAstral = 11,
};

constexpr bool IsElement(int element) noexcept
{
    return element >= kFire && element <= kAstral;
}

constexpr int TreeOf(int element) noexcept
{
    return element - 1;
}

// The nodes N2 reads (node::k..., node::kProcAdept / kProcMaster per element) are generated into
// ManifestData.h, each checked against the ESP's node names by build/fix19_native.py.

// ---------------------------------------------------------------- inputs

// Values from settings.json (compiled into ManifestData.h) and the tunable globals read at hit time.
struct Config {
    std::array<std::array<float, 2>, kElementCount + 1> damage{};  // [element] = {B_min, B_max}; [0] unused
    float noFormBaseTrue = 5.0f;                                  // settings noform_base_true
};

struct Tuning {
    float baseDamageMult = 1.0f;     // ESSB_BaseDamageMult
    float nodeScale = 3.0f;          // ESSB_NodeScale: percentage damage main lines take x3 (v0.4 3)
    float multDrain = 1.0f;          // ESSB_MultDrain
    float multRecovery = 1.0f;       // ESSB_MultRecovery
    float multDuration = 1.0f;       // ESSB_MultDuration
    float slowCapPct = 70.0f;        // ESSB_SlowCapPct (never above 70)
    float wetSlowPct = 15.0f;        // ESSB_WaterWetSlowPct
    float waterClearStamina = 30.0f; // ESSB_WaterClearStamina
    float seizeMaxPct = 10.0f;       // ESSB_ManabreakMaxmagPct
    std::array<float, kTreeCount> level{};  // ESSB_Lvl_<tree>
    int syncStage = 0;               // ESSB_SyncStage
    bool envWet = false;             // ESSB_EnvWet (rain/snow outdoors, or swimming)
    bool envNight = false;           // ESSB_EnvNight (20:00-6:00)
    int prevElement = 0;             // ESSB_PrevElement
    int twinElement = 0;             // ESSB_TwinElement
    float multCooldown = 1.0f;       // ESSB_MultCooldown (round 22: the per-target reaction cooldowns)
    bool envStormy = false;          // ESSB_EnvStormy (round 22: 暴風雪 doubles freeze)
    float multDot = 1.0f;            // ESSB_MultDot (round 22: the DoTs are the DLL's now)
    float poisonDotK = 0.2116f;      // ESSB_PoisonDotK (2.7 k_dot, MCM)
    float bleedDotK = 0.1143f;       // ESSB_BleedDotK
};

// Round 22 (N3): what the statuses on the target and the player do to each element's proc this hit (Status.h
// ProcTerms). `add` joins the node sum of M_mod, `mult` is v0.4 2.7's T; `windSneak` is 暗風 / 連殺 on top of the ×3.
// All neutral by default, so the N2 formula is unchanged when no status applies.
struct StatusTerms {
    std::array<float, kElementCount + 1> add{};
    std::array<float, kElementCount + 1> mult{ 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f };
    float windSneak = 1.0f;
};

struct Attack {
    int element = 0;          // 0 = no form; 1..11 = ESSB_CurrentElement with a form active
    bool power = false;       // R = 1.5: melee power attack flag, or a sneak shot for bows/crossbows
    bool sneakAttack = false; // TESHitEvent kSneakAttack (undetected)
    bool leftHand = false;    // the hit came from the left-hand weapon (and the right hand holds another)
};

struct PlayerFacts {
    float health = 100.0f;
    float healthPermanent = 100.0f;  // denominator of GetActorValuePercentage
    float healthMax = 100.0f;        // GetActorValueMax (permanent + temporary)
    float magicka = 100.0f;
    float magickaMax = 100.0f;
    bool interior = false;
    bool echoPending = false;  // ESSB_EchoPending effect on the player (applied by Papyrus on a switch)
    bool twinWindow = false;   // ESSB_TwinWindow effect on the player (30 s after a switch, 雙生 owned)
    bool riposteWindow = false;  // ESSB_RiposteWindow effect on the player (3 s after a block, 反擊 owned)
    float bloodGuard = 0.0f;   // magnitude of the ESSB_BloodGuard effect on the player (0 = none)
};

struct TargetFacts {
    bool undeadOrDaedra = false;  // ActorTypeUndead / ActorTypeDaedra
    bool necromancer = false;     // necromancer class, necromancer faction, or commanding thralls
    bool bloodMark = false;       // our blood mark effect: N2's reading of "bleeding" (see ledger D4)
    bool silenced = false;        // our silence effect
    bool spellUser = false;       // a spell in either hand, or a ward / armour spell / cloak effect
    bool vip = false;             // essential, protected or unique: silence is halved
    float magicka = 0.0f;
    float magickaMax = 0.0f;
    int hushLayers = 0;           // magnitude of our 寂 effect (ESSB_HushEffect; given by 冷寂 at 融斷, N5)
    bool hushSpent = false;       // our 寂滅 "used" marker (ESSB_HushSpent)
};

// Everything the planner reads about the player's nodes; EngineFacts.h answers it from HasPerk.
template <class T>
concept NodeReader = requires(const T& nodes, NodeId id, BranchId branch) {
    { nodes.Rank(id) } -> std::convertible_to<int>;
    { nodes.Has(branch) } -> std::convertible_to<bool>;
};

// Every draw of the hit goes through this; production is SplitMix64, tests script the values.
template <class T>
concept RandomSource = requires(T& rng, int lo, int hi, float a, float b) {
    { rng.Int(lo, hi) } -> std::convertible_to<int>;      // uniform integer in [lo, hi]
    { rng.Real(a, b) } -> std::convertible_to<float>;     // uniform real in [a, b]
    { rng.Chance(a) } -> std::convertible_to<bool>;       // true with probability a
};

// ---------------------------------------------------------------- output

enum class Cast : std::uint8_t
{
    kProc,            // the element damage spell (element, power variant)
    kDrainMagicka,    // target magicka - magnitude
    kDrainStamina,    // target stamina - magnitude
    kTrueDamage,      // target health - magnitude, no resistances
    kSoakSlow,        // target slowed by magnitude percent for `seconds` (fixed-duration spells, ruling R6)
    kDispelMark,      // 滅法印 on the target (8 s), no override
    kSilence,         // silence on the target for `seconds`, no override
    kHushSpent,       // 寂滅 paid out on this target (10 s marker), no override
    kHeal,            // player health + magnitude
    kRestoreMagicka,  // player magicka + magnitude
    kRestoreStamina,  // player stamina + magnitude
    kSpendMagicka,    // player magicka - magnitude
    kBloodGuard,      // player's 護血 pool effect, magnitude = the new pool total
};

constexpr bool CastsOnPlayer(Cast cast) noexcept
{
    return cast >= Cast::kHeal;
}

struct CastStep {
    Cast cast{};
    float magnitude = 0.0f;  // the override; 0 for kDispelMark / kSilence (the record's own magnitudes)
    int element = 0;         // kProc only
    bool power = false;      // kProc only
    int seconds = 0;         // kSilence and kSoakSlow
};

inline constexpr int kMaxCasts = 16;
inline constexpr int kSilenceSpellCount = 8;  // ESSB_Native_Silence_1 .. _8 (fixed durations)
inline constexpr int kSoakSpellCount = 30;    // soaked slow of 1..30 s (fixed durations; 10 s is ESSB_Native_SoakSlow)

struct Plan {
    std::array<CastStep, kMaxCasts> steps{};
    int count = 0;
    bool consumeEcho = false;  // dispel the player's ESSB_EchoPending effect
    bool consumeRiposte = false;  // dispel the player's ESSB_RiposteWindow effect (反擊 used on this hit)
    // For the log and the debug notice.
    int element = 0;
    float magnitude = 0.0f;    // main proc (element hits) or total true damage (no form)
    bool crit = false;
    float siphon = 0.0f;
    float burned = 0.0f;
    bool dispel = false;       // heavy no-form hit that spent magicka

    constexpr void Add(const CastStep& step) noexcept
    {
        if (count < kMaxCasts) {
            steps[count++] = step;
        }
    }
};

// ---------------------------------------------------------------- building blocks (each tested on its own)

constexpr float TreeG(const Tuning& t, int tree) noexcept
{
    return 1.0f + 0.05f * std::max(1.0f, t.level[tree]);
}

constexpr float Pct(const Tuning& t, int rank, float perPoint) noexcept
{
    return static_cast<float>(rank) * perPoint * t.nodeScale;
}

constexpr float Clamp01(float x) noexcept
{
    return x < 0.0f ? 0.0f : (x > 1.0f ? 1.0f : x);
}

// GetActorValuePercentage: current / permanent, 1.0 when the permanent value is 0.
constexpr float HealthFraction(const PlayerFacts& p) noexcept
{
    return p.healthPermanent > 0.0f ? p.health / p.healthPermanent : 1.0f;
}

// Linear interpolation over (fraction, value) points sorted by descending fraction; flat outside.
constexpr float Interpolate(float x, const std::array<std::array<float, 2>, 4>& points) noexcept
{
    if (x >= points[0][0]) {
        return points[0][1];
    }
    for (std::size_t i = 1; i < points.size(); ++i) {
        if (x >= points[i][0]) {
            const float span = points[i - 1][0] - points[i][0];
            const float along = (x - points[i][0]) / span;
            return points[i][1] + along * (points[i - 1][1] - points[i][1]);
        }
    }
    return points.back()[1];
}

// v0.4 1.1 blood curves: hit multiplier and leech ratio at 100% / 70% / 30% / 10% health.
inline constexpr std::array<std::array<float, 2>, 4> kBloodHitCurve{ { { 1.0f, 1.3f }, { 0.7f, 1.1f }, { 0.3f, 0.8f }, { 0.1f, 0.6f } } };
inline constexpr std::array<std::array<float, 2>, 4> kBloodLeechCurve{ { { 1.0f, 0.05f }, { 0.7f, 0.15f }, { 0.3f, 0.35f }, { 0.1f, 0.50f } } };

// The fraction the curves read: 逆流 mirrors it (low health hits hard, high health leeches).
template <NodeReader Nodes>
constexpr float BloodCurveFraction(const PlayerFacts& p, const Nodes& nodes)
{
    const float fraction = Clamp01(HealthFraction(p));
    return nodes.Has(node::kBloodReverse) ? 1.0f - fraction : fraction;
}

// 血怒: 30%..70% health (unclamped GetActorValuePercentage, as the Papyrus version read it).
template <NodeReader Nodes>
constexpr bool BloodRage(const PlayerFacts& p, const Nodes& nodes)
{
    const float fraction = HealthFraction(p);
    return nodes.Has(node::kBloodRage) && fraction >= 0.3f && fraction <= 0.7f;
}

// 1 + sum of the node percentages that scale this element's proc (v0.4 5.2 common tree + the element skeleton).
template <NodeReader Nodes>
constexpr float NodeSum(int element, bool power, const Tuning& t, const Nodes& nodes)
{
    float sum = 1.0f;
    // The element skeleton: sustain adept "X proc +1%/point" and sustain master "+1%/point per sync stage".
    // Water has neither (its sustain adept / master lines are recovery), so its entries are kNoNode.
    if (IsNode(node::kProcAdept[element])) {
        sum += Pct(t, nodes.Rank(node::kProcAdept[element]), 0.01f);
    }
    if (IsNode(node::kProcMaster[element])) {
        sum += Pct(t, nodes.Rank(node::kProcMaster[element]), 0.01f) * static_cast<float>(t.syncStage);
    }
    sum += Pct(t, nodes.Rank(node::kCommonAll1), 0.01f);
    sum += Pct(t, nodes.Rank(node::kCommonAll2), 0.01f);
    if (t.syncStage >= 2) {
        sum += Pct(t, nodes.Rank(node::kCommonStage2), 0.01f);
    }
    if (t.syncStage >= 3 && power) {
        sum += Pct(t, nodes.Rank(node::kCommonStage3Power), 0.02f);
    }
    return sum;
}

// Categorical multipliers the DLL knows at hit time (each x1 when it does not apply).
template <NodeReader Nodes>
constexpr float ElementMultiplier(int element, const Attack& a, const Tuning& t, const PlayerFacts& p,
    const TargetFacts& target, const Nodes& nodes, const StatusTerms& terms)
{
    float mult = 1.0f;
    if (element == kBlood) {
        mult *= Interpolate(BloodCurveFraction(p, nodes), kBloodHitCurve);
        if (BloodRage(p, nodes)) {
            mult *= 1.15f;
        }
    }
    if (!p.interior) {  // v0.4 2.10: indoors and dungeons have no environment bonus
        if (element == kDarkness && t.envNight) {
            mult *= 1.2f;
        }
        if (element == kDivine && !t.envNight) {
            mult *= 1.2f;
        }
    }
    if (element == kDivine && target.undeadOrDaedra) {
        mult *= 1.5f;
    }
    if (element == kDivine && target.necromancer && nodes.Has(node::kDivineExorcism)) {
        mult *= 1.5f;
    }
    if (element == kWind && a.sneakAttack) {
        mult *= 3.0f * terms.windSneak;
    }
    return mult * terms.mult[element];
}

// v0.4 2.1: lightning rolls its range (settings 1..25) N times and keeps the highest (N = 1 + charges;
// charges are N4, so 1). Integer faces: only they give the design's expected values 13.0 / 22.35 / 23.38.
template <RandomSource Rng>
constexpr int RollLightning(Rng& rng, int lowest, int highest, int rolls)
{
    int best = lowest;
    for (int i = 0; i < rolls; ++i) {
        best = std::max(best, static_cast<int>(rng.Int(lowest, highest)));
    }
    return best;
}

// Charges live in Papyrus until N4 (ESSB_Charge is a v0.3 mirror, not an engine effect): read as 0.
inline constexpr int kChargesUntilN4 = 0;

constexpr int LightningRolls(int charges) noexcept
{
    return 1 + charges;
}

constexpr float LightningCritChance(int charges) noexcept
{
    return 0.05f + 0.02f * static_cast<float>(charges);
}

// C of 2.7: only lightning crits; x1.5, or x2.5 on a power attack.
constexpr float CritMultiplier(bool power) noexcept
{
    return power ? 2.5f : 1.5f;
}

struct Proc {
    float magnitude = 0.0f;
    bool crit = false;
};

// One element proc: rolls B (and the crit for lightning) and returns D_hit before M_ext / Res.
template <NodeReader Nodes, RandomSource Rng>
constexpr Proc RollProc(int element, const Attack& a, const Config& c, const Tuning& t, const PlayerFacts& p,
    const TargetFacts& target, const Nodes& nodes, Rng& rng, const StatusTerms& terms)
{
    float b = 0.0f;
    if (element == kLightning) {
        const auto& faces = c.damage[kLightning];
        b = static_cast<float>(RollLightning(rng, static_cast<int>(faces[0]), static_cast<int>(faces[1]), LightningRolls(kChargesUntilN4)));
    } else {
        b = rng.Real(c.damage[element][0], c.damage[element][1]);
    }
    const float r = a.power ? 1.5f : 1.0f;
    Proc proc;
    proc.magnitude = b * r * TreeG(t, TreeOf(element)) * t.baseDamageMult * (NodeSum(element, a.power, t, nodes) + terms.add[element]) *
                     ElementMultiplier(element, a, t, p, target, nodes, terms);
    if (element == kLightning && rng.Chance(LightningCritChance(kChargesUntilN4))) {
        proc.crit = true;
        proc.magnitude *= CritMultiplier(a.power);
    }
    return proc;
}

// Leech ratio of the blood curve plus the expert main line (+1%/point, not node-scaled) and 血怒 (+15%).
// At most 50% + 15% + 15% = 80%, so no cap is needed.
template <NodeReader Nodes>
constexpr float LeechRatio(const PlayerFacts& p, const Nodes& nodes)
{
    float ratio = Interpolate(BloodCurveFraction(p, nodes), kBloodLeechCurve);
    ratio += 0.01f * static_cast<float>(nodes.Rank(node::kBloodLeechRatio));
    if (BloodRage(p, nodes)) {
        ratio += 0.15f;
    }
    return ratio;
}

inline constexpr float kBloodGuardCapOfMaxHealth = 0.2f;

// ---------------------------------------------------------------- element hits

template <NodeReader Nodes>
constexpr void AddBloodLeech(Plan& plan, float procMagnitude, const Tuning& t, const PlayerFacts& p, const Nodes& nodes)
{
    const float heal = procMagnitude * LeechRatio(p, nodes) * t.multRecovery;
    if (heal <= 0.0f) {
        return;
    }
    const float missing = std::max(0.0f, p.healthMax - p.health);
    const float healed = std::min(heal, missing);
    if (healed > 0.0f) {
        plan.Add({ Cast::kHeal, healed });
    }
    // 血溢: the overflow goes into the 護血 pool (the magnitude of our effect on the player), capped at 20% of max
    // health. The pool is clamped on read, so a pool above the cap (max health dropped since it filled) comes back
    // down on the next leech; a full pool is not recast. Known N4 item: two hits in one frame both read the pool
    // before either recast lands, so the second hit's overflow is lost (keeping it would need DLL state).
    const float cap = kBloodGuardCapOfMaxHealth * p.healthMax;
    float pool = std::min(p.bloodGuard, cap);
    const float overflow = heal - healed;
    if (overflow > 0.0f && nodes.Has(node::kBloodOverflow)) {
        pool = std::min(pool + overflow, cap);
    }
    if (pool > 0.0f && pool != p.bloodGuard) {
        plan.Add({ Cast::kBloodGuard, pool });
    }
}

template <NodeReader Nodes>
constexpr void AddFlatHitNodes(Plan& plan, int element, const Tuning& t, const Nodes& nodes)
{
    if (element == kEarth) {
        const float cut = 3.0f * static_cast<float>(nodes.Rank(node::kEarthStaminaCut)) * TreeG(t, TreeOf(kEarth));
        if (cut > 0.0f) {
            plan.Add({ Cast::kDrainStamina, cut * t.multDrain });
            if (nodes.Has(node::kEarthDrainStrength)) {
                plan.Add({ Cast::kRestoreStamina, cut * 0.5f * t.multRecovery });
            }
        }
    }
    if (element == kWind && nodes.Has(node::kWindTailwind)) {
        plan.Add({ Cast::kRestoreStamina, 25.0f * TreeG(t, TreeOf(kWind)) * t.multRecovery });
    }
    if (element == kWater && nodes.Has(node::kWaterClearStream)) {
        plan.Add({ Cast::kRestoreStamina, t.waterClearStamina * t.multRecovery });
    }
}

// v0.4 2.6: 浸濕 slows 15% (ESSB_WaterWetSlowPct), under the mod's shared cap (never above 70%).
constexpr float SoakSlowPct(const Tuning& t) noexcept
{
    const float cap = std::clamp(t.slowCapPct, 0.0f, 70.0f);
    return std::min(t.wetSlowPct, cap);
}

// 5.11 water sustain novice line: 浸濕 lasts 10 s +0.3 s per point (rounded to whole seconds like
// ESSBElem3.WetSeconds), then x the MCM duration multiplier; the spell of that many seconds is cast (1..30).
template <NodeReader Nodes>
constexpr int SoakSeconds(const Tuning& t, const Nodes& nodes)
{
    const int base = static_cast<int>(10.0f + 0.3f * static_cast<float>(nodes.Rank(node::kWaterSoakDuration)) + 0.5f);
    const int scaled = static_cast<int>(static_cast<float>(base) * t.multDuration + 0.5f);
    return std::clamp(scaled, 1, kSoakSpellCount);
}

// 餘響 + closing expert main line: share of the previous element's proc on the first hit after a switch.
template <NodeReader Nodes>
constexpr float EchoRatio(const Tuning& t, const Nodes& nodes)
{
    const float base = nodes.Has(node::kCommonEcho) ? 0.5f : 0.0f;
    return base + Pct(t, nodes.Rank(node::kCommonEchoRatio), 0.03f);
}

template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanElementHit(Plan& plan, const Attack& a, const Config& c, const Tuning& t, const PlayerFacts& p,
    const TargetFacts& target, const Nodes& nodes, Rng& rng, const StatusTerms& terms)
{
    const int element = a.element;
    const Proc proc = RollProc(element, a, c, t, p, target, nodes, rng, terms);
    plan.element = element;
    plan.magnitude = proc.magnitude;
    plan.crit = proc.crit;
    plan.Add({ Cast::kProc, proc.magnitude, element, a.power });
    if (element == kLightning) {
        // v0.4 2.1: drain = 50% of the damage override, as its own single-effect spell.
        plan.Add({ Cast::kDrainMagicka, proc.magnitude * 0.5f * t.multDrain });
    }
    if (element == kBlood && target.bloodMark) {
        AddBloodLeech(plan, proc.magnitude, t, p, nodes);
    }
    if (t.envWet) {
        // v0.4 2.10: rain, snow or standing in water: every enemy counts as soaked (slow only here).
        CastStep soak{ Cast::kSoakSlow, SoakSlowPct(t) };
        soak.seconds = SoakSeconds(t, nodes);
        plan.Add(soak);
    }
    AddFlatHitNodes(plan, element, t, nodes);

    // 雙生: the left-hand weapon also carries the previous form's element for 30 s.
    if (a.leftHand && p.twinWindow && IsElement(t.twinElement) && t.twinElement != element) {
        const Proc twin = RollProc(t.twinElement, a, c, t, p, target, nodes, rng, terms);
        plan.Add({ Cast::kProc, twin.magnitude, t.twinElement, a.power });
        if (t.twinElement == kLightning) {
            plan.Add({ Cast::kDrainMagicka, twin.magnitude * 0.5f * t.multDrain });
        }
    }
    // 餘響: the first hit after a switch also carries a share of the previous element's proc.
    if (p.echoPending && IsElement(t.prevElement) && t.prevElement != element) {
        plan.consumeEcho = true;
        const float ratio = EchoRatio(t, nodes);
        if (ratio > 0.0f) {
            const Proc echo = RollProc(t.prevElement, a, c, t, p, target, nodes, rng, terms);
            plan.Add({ Cast::kProc, echo.magnitude * ratio, t.prevElement, a.power });
        }
    }
}

// ---------------------------------------------------------------- no-form hits (v0.4 2.8, 5.1)

inline constexpr float kSiphonBase = 10.0f;        // 吸魔 10 x G
inline constexpr float kSmallBurnBase = 5.0f;      // 小滅法 5 x G
inline constexpr float kDispelSpendOfMax = 0.15f;  // 滅法 X = 15% of your max magicka
inline constexpr float kDispelMultiplier = 1.0f;   // base; x1.5 while overloaded: overload is N4
inline constexpr float kBurnMultiple = 1.0f;       // base: Y <= X x 1.0
inline constexpr int kMaxSilenceSeconds = 4;
inline constexpr int kHushBreakLayers = 3;         // 寂滅: the target carries at least 3 layers of 寂
inline constexpr float kHushBreakBonus = 0.5f;     // 寂滅: +0.5 to the next dispel's multiplier

// 5.1 滅法 novice line: the dispel multiplier +2% per point (not node-scaled: x1.0 -> x1.3); the small dispel
// uses the same multiplier (v0.4 5.1: its true damage is "燒掉的量 x 滅法倍率").
template <NodeReader Nodes>
constexpr float DispelRate(const Nodes& nodes)
{
    return kDispelMultiplier + 0.02f * static_cast<float>(nodes.Rank(node::kNoFormDispelRate));
}

// 5.1 滅法 adept line: Y may reach X x (1.0 + 7% per point) (x2.05 at 15).
template <NodeReader Nodes>
constexpr float BurnMultiple(const Nodes& nodes)
{
    return kBurnMultiple + 0.07f * static_cast<float>(nodes.Rank(node::kNoFormBurnMultiple));
}

// 5.1 冷寂 adept branch 寂滅 (the N2 half): a target with >= 3 layers of 寂 takes +0.5 on your next dispel.
template <NodeReader Nodes>
constexpr bool HushBreak(const TargetFacts& target, const Nodes& nodes)
{
    return nodes.Has(node::kNoFormHushBreak) && target.hushLayers >= kHushBreakLayers && !target.hushSpent;
}

template <NodeReader Nodes>
constexpr float TrueDamageMultiplier(const TargetFacts& target, const Tuning& t, const Nodes& nodes)
{
    float mult = 1.0f;
    if (target.silenced && nodes.Has(node::kNoFormStillness)) {
        mult *= 1.5f;
    }
    const bool lowMagicka = target.magickaMax > 0.0f && target.magicka < 0.25f * target.magickaMax;
    if (lowMagicka) {
        mult *= 1.0f + Pct(t, nodes.Rank(node::kNoFormLowMagicka), 0.03f);
    }
    return mult;
}

template <NodeReader Nodes>
constexpr float BurnBonus(const TargetFacts& target, const Nodes& nodes)
{
    return target.spellUser ? 1.0f + 0.05f * static_cast<float>(nodes.Rank(node::kNoFormBurnCasters)) : 1.0f;
}

// Silence seconds as ESSBController.ApplySilenceSpell rounds them: 1 + 0.2/point (max 4), halved for
// essential / protected / unique targets, then scaled by the duration multiplier; 1..8 spells exist.
template <NodeReader Nodes>
constexpr int SilenceSeconds(const TargetFacts& target, const Tuning& t, const Nodes& nodes)
{
    const float wanted = std::min(1.0f + 0.2f * static_cast<float>(nodes.Rank(node::kNoFormSilence)), static_cast<float>(kMaxSilenceSeconds));
    int seconds = static_cast<int>(wanted + 0.5f);
    if (target.vip) {
        seconds = std::max(1, seconds / 2);
    }
    const int scaled = static_cast<int>(static_cast<float>(seconds) * t.multDuration + 0.5f);
    return std::clamp(scaled, 1, kSilenceSpellCount);
}

template <NodeReader Nodes>
constexpr void PlanNoFormHit(Plan& plan, const Attack& a, const Config& c, const Tuning& t, const PlayerFacts& p,
    const TargetFacts& target, const Nodes& nodes)
{
    const float g = TreeG(t, kNoFormTree);
    const float r = a.power ? 1.5f : 1.0f;
    const float trueMult = TrueDamageMultiplier(target, t, nodes);
    float trueTotal = 0.0f;

    // 2.8 baseline: 5 x G x damage multiplier, power x1.5; no node multipliers.
    const float baseline = c.noFormBaseTrue * g * t.baseDamageMult * r;
    plan.Add({ Cast::kTrueDamage, baseline });
    trueTotal += baseline;

    // 吸魔: take the target's magicka, give it to you (nothing to take from a target with none).
    float siphon = kSiphonBase * g * r;
    if (nodes.Has(node::kNoFormSeize)) {
        siphon = std::max(siphon, target.magickaMax * t.seizeMaxPct * 0.01f);
    }
    // 大師 novice line: siphon amount +5% per point (not node-scaled: x1.0 -> x1.75).
    siphon *= 1.0f + 0.05f * static_cast<float>(nodes.Rank(node::kNoFormSiphonAmount));
    // 反擊: within 3 s of a successful block (the window effect Papyrus opens) this hit siphons x2 and uses it up.
    if (p.riposteWindow && nodes.Has(node::kNoFormRiposte)) {
        siphon *= 2.0f;
        plan.consumeRiposte = true;
    }
    siphon = std::min(siphon * t.multDrain, std::max(0.0f, target.magicka));
    float targetMagicka = std::max(0.0f, target.magicka);
    float playerMagicka = std::max(0.0f, p.magicka);
    if (siphon > 0.0f) {
        const float gained = siphon * t.multRecovery;
        plan.Add({ Cast::kDrainMagicka, siphon });
        plan.Add({ Cast::kRestoreMagicka, gained });
        targetMagicka -= siphon;
        playerMagicka = std::min(p.magickaMax, playerMagicka + gained);
    }
    plan.siphon = siphon;

    // No magicka, no dispel of either size (v0.4 5.1: the limit is deliberate).
    const float rate = DispelRate(nodes);
    if (playerMagicka > 0.0f && !a.power) {
        // 小滅法: burn 5 x G more of the target's magicka; true damage = burned x dispel multiplier.
        const float burn = std::min(kSmallBurnBase * g * BurnBonus(target, nodes) * t.multDrain, targetMagicka);
        if (burn > 0.0f) {
            const float damage = burn * rate * trueMult;
            plan.Add({ Cast::kDrainMagicka, burn });
            plan.Add({ Cast::kTrueDamage, damage });
            trueTotal += damage;
            plan.burned = burn;
        }
    } else if (playerMagicka > 0.0f && a.power) {
        // 滅法: spend X of your magicka, burn Y of theirs, true damage (X + Y) x multiplier; no G(L).
        const float x = std::min(kDispelSpendOfMax * p.magickaMax, playerMagicka);
        float spend = x;
        float y = 0.0f;
        if (targetMagicka <= 0.0f && nodes.Has(node::kNoFormDepletion)) {
            spend = std::min(2.0f * x, playerMagicka);  // 枯竭: burn twice X of your own instead
        } else {
            y = std::min(targetMagicka, x * BurnMultiple(nodes) * BurnBonus(target, nodes) * t.multDrain);
        }
        const bool hushBreak = HushBreak(target, nodes);
        const float damage = (spend + y) * (rate + (hushBreak ? kHushBreakBonus : 0.0f)) * trueMult;
        plan.Add({ Cast::kSpendMagicka, spend });
        if (y > 0.0f) {
            plan.Add({ Cast::kDrainMagicka, y });
        }
        plan.Add({ Cast::kTrueDamage, damage });
        plan.Add({ Cast::kDispelMark, 0.0f });
        if (hushBreak) {
            plan.Add({ Cast::kHushSpent, 0.0f });  // only the next dispel: the target is marked for 10 s
        }
        if (targetMagicka - y <= 0.0f) {
            CastStep silence{ Cast::kSilence, 0.0f };
            silence.seconds = SilenceSeconds(target, t, nodes);
            plan.Add(silence);
        }
        trueTotal += damage;
        plan.burned = y;
        plan.dispel = true;
    }

    // 噬命: half of every true damage of this hit heals you.
    if (nodes.Has(node::kNoFormDevour)) {
        plan.Add({ Cast::kHeal, trueTotal * 0.5f * t.multRecovery });
    }
    plan.element = kNoElement;
    plan.magnitude = trueTotal;
}

// The whole hit. Element hits need a form; no-form hits are element 0.
template <NodeReader Nodes, RandomSource Rng>
constexpr Plan PlanHit(const Attack& a, const Config& c, const Tuning& t, const PlayerFacts& p,
    const TargetFacts& target, const Nodes& nodes, Rng& rng, const StatusTerms& terms = StatusTerms{})
{
    Plan plan;
    if (IsElement(a.element)) {
        PlanElementHit(plan, a, c, t, p, target, nodes, rng, terms);
    } else if (a.element == kNoElement) {
        PlanNoFormHit(plan, a, c, t, p, target, nodes);
    }
    return plan;
}

// ---------------------------------------------------------------- production randomness

// SplitMix64: small, fast, good enough for damage rolls; seeded once per game process.
class SplitMix64
{
public:
    explicit constexpr SplitMix64(std::uint64_t seed) noexcept : state_(seed) {}

    constexpr std::uint64_t Next() noexcept
    {
        std::uint64_t z = (state_ += 0x9E3779B97F4A7C15ull);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
        return z ^ (z >> 31);
    }

    // Uniform in [0, 1) with 24 bits, exactly representable as float.
    constexpr float Unit() noexcept
    {
        return static_cast<float>(Next() >> 40) * (1.0f / 16777216.0f);
    }

    // Uniform integer in [lo, hi] without modulo bias (rejection sampling).
    constexpr int Int(int lo, int hi) noexcept
    {
        const std::uint64_t span = static_cast<std::uint64_t>(hi - lo) + 1;
        const std::uint64_t limit = ~0ull - (~0ull % span);
        std::uint64_t x = Next();
        while (x >= limit) {
            x = Next();
        }
        return lo + static_cast<int>(x % span);
    }

    constexpr float Real(float lo, float hi) noexcept
    {
        return lo + (hi - lo) * Unit();
    }

    constexpr bool Chance(float probability) noexcept
    {
        return Unit() < probability;
    }

private:
    std::uint64_t state_;
};

}  // namespace essb
