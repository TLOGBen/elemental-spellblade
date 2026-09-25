#pragma once
// Stage 2 of the native hit handler: turn the engine's raw answers into the planner's inputs.
// Plugin.cpp does the engine calls (HasPerk, TESGlobal::value, actor values, effect lists, keywords) and
// fills the Raw* structs; everything here is pure so the wiring can be tested with a mocked engine:
//   * perk ranks: the same 4-probe binary search over the 15-rank chain as ESSBTrees.GetMainRank, on the
//     same FormIDs (MAIN_BASE + node x 15 + rank - 1, BRANCH_BASE + node x 4 + index), and the same
//     "no-form tree routes 0/1 read as 0 while a form is active" rule as ESSBController.Rank/Br;
//   * globals: which GLOB feeds which Tuning field;
//   * attack: R from the hit flags (a sneak shot is the ranged power attack), left hand as Papyrus decides it;
//   * target: undead/daedra, necromancer, spell user and VIP as the Papyrus helpers decide them.
#include "HitMath.h"
#include "ManifestData.h"
#include "NodeIds.h"

#include <array>
#include <cstdint>

namespace essb {

// ---------------------------------------------------------------- perks

constexpr int NodeIndex(int tree, int route, int tier) noexcept
{
    return (tree * 3 + route) * 5 + tier;
}

inline constexpr int kNodeCount = NodeIndex(kTreeCount - 1, 2, 4) + 1;  // 195

// Local FormID of rank `rank` (1..15) of a main line.
constexpr std::uint32_t MainPerkId(const NodeId& id, int rank) noexcept
{
    return kMainPerkBase + static_cast<std::uint32_t>(NodeIndex(id.tree, id.route, id.tier) * kMainMaxRank + rank - 1);
}

constexpr std::uint32_t BranchPerkId(const BranchId& id) noexcept
{
    return kBranchPerkBase + static_cast<std::uint32_t>(NodeIndex(id.tree, id.route, id.tier) * kBranchSlots + id.index);
}

// The no-form tree's first two routes only apply without a form (ESSBController.Rank / Br).
constexpr bool SuppressedWhileFormActive(int tree, int route, bool formActive) noexcept
{
    return formActive && tree == kNoFormTree && route < 2;
}

// NodeReader over the player's perks. hasPerk(localFormID) -> bool is the engine (Actor::HasPerk) or a mock.
// Answers are cached for the lifetime of this object (one hit).
template <class HasPerk>
class PerkNodes
{
public:
    constexpr PerkNodes(HasPerk hasPerk, bool formActive) : hasPerk_(hasPerk), formActive_(formActive)
    {
        ranks_.fill(-1);
        branches_.fill(-1);
    }

    constexpr int Rank(const NodeId& id) const
    {
        if (!IsNode(id) || SuppressedWhileFormActive(id.tree, id.route, formActive_)) {
            return 0;
        }
        auto& cached = ranks_[NodeIndex(id.tree, id.route, id.tier)];
        if (cached < 0) {
            cached = static_cast<std::int8_t>(SearchRank(id));
        }
        return cached;
    }

    constexpr bool Has(const BranchId& id) const
    {
        if (SuppressedWhileFormActive(id.tree, id.route, formActive_)) {
            return false;
        }
        auto& cached = branches_[NodeIndex(id.tree, id.route, id.tier) * kBranchSlots + id.index];
        if (cached < 0) {
            cached = hasPerk_(BranchPerkId(id)) ? 1 : 0;
        }
        return cached == 1;
    }

private:
    // ESSBTrees.GetMainRank: 16 candidate values (0..15), four HasPerk probes.
    constexpr int SearchRank(const NodeId& id) const
    {
        int low = 0;
        int high = kMainMaxRank;
        while (low < high) {
            const int mid = (low + high + 1) / 2;
            if (hasPerk_(MainPerkId(id, mid))) {
                low = mid;
            } else {
                high = mid - 1;
            }
        }
        return low;
    }

    HasPerk hasPerk_;
    bool formActive_;
    mutable std::array<std::int8_t, kNodeCount> ranks_{};
    mutable std::array<std::int8_t, kNodeCount * kBranchSlots> branches_{};
};

// ---------------------------------------------------------------- globals

// global(localFormID) -> float is the engine (TESGlobal::value) or a mock.
template <class Global>
constexpr Tuning ReadTuning(Global&& global)
{
    Tuning t;
    t.baseDamageMult = global(glob::kBaseDamageMult);
    t.nodeScale = global(glob::kNodeScale);
    t.multDrain = global(glob::kMultDrain);
    t.multRecovery = global(glob::kMultRecovery);
    t.multDuration = global(glob::kMultDuration);
    t.slowCapPct = global(glob::kSlowCapPct);
    t.wetSlowPct = global(glob::kWaterWetSlowPct);
    t.waterClearStamina = global(glob::kWaterClearStamina);
    t.seizeMaxPct = global(glob::kManabreakMaxmagPct);
    for (int tree = 0; tree < kTreeCount; ++tree) {
        t.level[tree] = global(glob::kTreeLevel[tree]);
    }
    t.syncStage = static_cast<int>(global(glob::kSyncStage));
    t.envWet = global(glob::kEnvWet) == 1.0f;
    t.envNight = global(glob::kEnvNight) == 1.0f;
    t.prevElement = static_cast<int>(global(glob::kPrevElement));
    t.twinElement = static_cast<int>(global(glob::kTwinElement));
    return t;
}

// ---------------------------------------------------------------- the attack

struct RawAttack {
    bool powerFlag = false;         // TESHitEvent kPowerAttack
    bool sneakFlag = false;         // TESHitEvent kSneakAttack
    bool ranged = false;            // resolved weapon type is a bow or crossbow (Filter)
    std::uint32_t sourceWeapon = 0; // FormID of the hit's source weapon form (0 = none / not a weapon)
    std::uint32_t leftWeapon = 0;   // FormID of the weapon equipped in the left hand (0 = none)
    std::uint32_t rightWeapon = 0;  // FormID of the weapon equipped in the right hand (0 = none)
};

// ESSBController.OnWeaponHit: bows and crossbows have no power attack; a sneak shot takes its place.
// The left hand is the source only when the right hand holds something else (identical twins read as right).
constexpr Attack MakeAttack(int element, const RawAttack& raw) noexcept
{
    Attack a;
    a.element = element;
    a.power = raw.ranged ? raw.sneakFlag : raw.powerFlag;
    a.sneakAttack = raw.sneakFlag;
    a.leftHand = raw.sourceWeapon != 0 && raw.sourceWeapon == raw.leftWeapon && raw.rightWeapon != raw.sourceWeapon;
    return a;
}

// ---------------------------------------------------------------- the target

struct RawTarget {
    bool undeadKeyword = false;       // ActorTypeUndead
    bool daedraKeyword = false;       // ActorTypeDaedra
    bool necromancerClass = false;    // base class == Skyrim.esm necromancer class
    bool necromancerFaction = false;  // in the Skyrim.esm necromancer faction
    int commandedActors = 0;          // thralls it commands
    bool bloodMark = false;           // has our blood mark effect
    bool silenced = false;            // has our silence effect
    bool spellInLeftHand = false;
    bool spellInRightHand = false;
    bool armorSpellEffect = false;    // an active effect with MagicArmorSpell
    bool cloakEffect = false;         // an active effect with MagicCloak
    bool essential = false;           // the reference is essential
    bool baseEssential = false;
    bool baseProtected = false;
    bool baseUnique = false;
    float magicka = 0.0f;
    float magickaMax = 0.0f;
};

constexpr TargetFacts MakeTarget(const RawTarget& raw) noexcept
{
    TargetFacts t;
    t.undeadOrDaedra = raw.undeadKeyword || raw.daedraKeyword;
    // ESSBController.IsNecromancer
    t.necromancer = raw.necromancerClass || raw.necromancerFaction || raw.commandedActors > 0;
    t.bloodMark = raw.bloodMark;
    t.silenced = raw.silenced;
    // ESSBNoForm.IsSpellUser
    t.spellUser = raw.spellInLeftHand || raw.spellInRightHand || raw.armorSpellEffect || raw.cloakEffect;
    // ESSBController.IsVIPTarget
    t.vip = raw.essential || raw.baseEssential || raw.baseProtected || raw.baseUnique;
    t.magicka = raw.magicka;
    t.magickaMax = raw.magickaMax;
    return t;
}

// ---------------------------------------------------------------- settings

constexpr Config MakeConfig() noexcept
{
    Config c;
    for (int element = kFire; element <= kAstral; ++element) {
        c.damage[element] = { kElementDamage[element][0], kElementDamage[element][1] };
    }
    c.noFormBaseTrue = kNoFormBaseTrue;
    return c;
}

}  // namespace essb
