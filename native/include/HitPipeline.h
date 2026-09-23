#pragma once
// Engine-free stages of the native hit handler (Plugin.cpp does the engine reads and the cast):
//   1. Filter(HitFacts)        which hits count - mirrors ESSBController.OnWeaponHit/ResolveHitWeaponType,
//                              so the DLL base proc and the Papyrus difference bonus accept the same hits
//   2. BuildInput(element, q)  asks the engine the same CTDA predicates the old entry-51 segments used
//   3. select(Input)           Selection.h
// Everything here is constexpr/pure so tests can drive it with mocked engine answers.
#include "Selection.h"

#include <cstdint>

namespace essb {

// ---------------------------------------------------------------- stage 1: filter

inline constexpr int kNoWeapon = -1;  // "not a TESObjectWEAP" for weapon-type fields
inline constexpr int kStaff = 8;      // RE::WEAPON_TYPE::kStaff
inline constexpr int kBow = 7;        // RE::WEAPON_TYPE::kBow
inline constexpr int kCrossbow = 9;   // RE::WEAPON_TYPE::kCrossbow

// What TESHitEvent::source resolves to.
enum class SourceKind : std::uint8_t
{
    kNone,            // source FormID 0
    kWeapon,          // TESObjectWEAP; sourceWeaponType holds its type
    kAmmo,            // TESAmmo
    kSameProjectile,  // BGSProjectile equal to TESHitEvent::projectile
    kOther,           // spell, enchantment, explosion, other projectile, unknown
};

struct HandFacts {
    int weaponType{ kNoWeapon };  // RE::WEAPON_TYPE of a TESObjectWEAP in this hand, else kNoWeapon
    bool nothing{ true };         // GetEquippedItemType(hand) == 0: empty or a hand-to-hand weapon
};

struct HitFacts {
    bool causeIsPlayer{};
    bool targetIsActor{};
    bool targetIsPlayer{};
    bool targetDead{};
    bool teammate{};
    bool commanded{};
    bool bash{};     // TESHitEvent kBashAttack
    bool blocked{};  // TESHitEvent kHitBlocked
    SourceKind source{ SourceKind::kNone };
    int sourceWeaponType{ kNoWeapon };
    bool projectile{};  // TESHitEvent::projectile != 0
    HandFacts right{};
    HandFacts left{};
    float enabled{};     // ESSB_Enabled
    float formActive{};  // ESSB_FormActive
    float element{};     // ESSB_CurrentElement
};

enum class Reject : std::uint8_t
{
    kAccepted,
    kNotPlayer,
    kDisabled,
    kBashOrBlocked,
    kBadTarget,
    kAlly,
    kUnsupportedWeapon,
    kMeleeProjectile,
    kDeadTarget,
    kFormInactive,
    kBadElement,
};

struct Verdict {
    Reject reason{ Reject::kAccepted };
    int weaponType{ kNoWeapon };
};

constexpr bool IsRangedType(int weaponType) noexcept
{
    return weaponType == kBow || weaponType == kCrossbow;
}

// Same range the Papyrus hit path accepts: 0..9 without staves (staff hits are magic, not weapon hits).
constexpr bool SupportedWeapon(int weaponType) noexcept
{
    return weaponType >= 0 && weaponType <= 9 && weaponType != kStaff;
}

// Port of ESSBController.ResolveHitWeaponType (Papyrus). Right hand is GetEquippedWeapon(False).
constexpr int ResolveWeaponType(const HitFacts& f) noexcept
{
    if (f.source == SourceKind::kWeapon) {
        return f.sourceWeaponType;
    }
    if (f.source == SourceKind::kOther) {
        return kNoWeapon;
    }
    if (f.projectile) {
        if (IsRangedType(f.right.weaponType)) {
            return f.right.weaponType;
        }
        if (IsRangedType(f.left.weaponType)) {
            return f.left.weaponType;
        }
        return kNoWeapon;
    }
    if (f.source == SourceKind::kNone && f.right.nothing && f.left.nothing) {
        return 0;
    }
    return kNoWeapon;
}

constexpr bool ValidElement(float element) noexcept
{
    // NaN fails every comparison, so it is rejected too.
    return element >= 1.0f && element <= 11.0f && element == static_cast<float>(static_cast<int>(element));
}

// Gate order follows ESSBController.OnWeaponHit; only the verdict matters, the order only picks the reason.
constexpr Verdict Filter(const HitFacts& f) noexcept
{
    if (!f.causeIsPlayer) {
        return { Reject::kNotPlayer };
    }
    if (f.enabled != 1.0f) {
        return { Reject::kDisabled };
    }
    if (f.bash || f.blocked) {
        return { Reject::kBashOrBlocked };
    }
    if (!f.targetIsActor || f.targetIsPlayer) {
        return { Reject::kBadTarget };
    }
    if (f.teammate || f.commanded) {
        return { Reject::kAlly };
    }
    const int weaponType = ResolveWeaponType(f);
    if (!SupportedWeapon(weaponType)) {
        return { Reject::kUnsupportedWeapon, weaponType };
    }
    if (!IsRangedType(weaponType) && f.projectile) {
        return { Reject::kMeleeProjectile, weaponType };
    }
    if (f.targetDead) {
        return { Reject::kDeadTarget, weaponType };
    }
    if (f.formActive != 1.0f) {
        return { Reject::kFormInactive, weaponType };
    }
    if (!ValidElement(f.element)) {
        return { Reject::kBadElement, weaponType };
    }
    return { Reject::kAccepted, weaponType };
}

// ---------------------------------------------------------------- stage 2: read the selection state

// CTDA function indices, identical to RE::FUNCTION_DATA::FunctionID (static_assert in Plugin.cpp).
enum class Fn : std::uint16_t
{
    kGetRandomPercent = 77,
    kIsSneaking = 286,
    kGetEquippedItemType = 597,
    kGetActorValuePercent = 640,
    kIsPowerAttacking = 673,
};

enum class Op : std::uint8_t
{
    kEqual,
    kGreaterOrEqual,
    kLess,
};

// One condition the engine evaluates on the player (subject and target = player).
struct Query {
    Fn fn{};
    float value{};
    Op op{ Op::kEqual };
    std::uint32_t param{};
};

inline constexpr std::uint32_t kRightHand = 1;  // CTDA 597 parameter
inline constexpr std::uint32_t kLeftHand = 0;
inline constexpr std::uint32_t kHealth = 24;  // ActorValue Health, the CTDA 640 parameter

// Health bands of the blood element, highest first: CTDA 640 >= threshold.
inline constexpr float kBloodThresholds[4] = { 0.85f, 0.5f, 0.2f, 0.0f };

// Lightning chain: R5 first, each GetRandomPercent < 100/(5-i); the first success wins, otherwise R1.
// Evaluation stops at the first success, so the engine RNG is only drawn as often as the chain needs.
inline constexpr float kLightningChance[4] = { 100.0f / 5, 100.0f / 4, 100.0f / 3, 100.0f / 2 };

// ask(Query) -> bool is the engine (Plugin.cpp) or a mock (tests).
template <class Ask>
constexpr Input BuildInput(int element, Ask&& ask)
{
    Input x{};
    x.element = element;
    if (ask(Query{ Fn::kGetEquippedItemType, float(kItemBow), Op::kEqual, kRightHand })) {
        x.rightItem = kItemBow;
    } else if (ask(Query{ Fn::kGetEquippedItemType, float(kItemCrossbow), Op::kEqual, kRightHand })) {
        x.rightItem = kItemCrossbow;
    }
    x.power = ask(Query{ Fn::kIsPowerAttacking, 1.0f, Op::kEqual, 0 });
    x.sneak = ask(Query{ Fn::kIsSneaking, 1.0f, Op::kEqual, 0 });
    if (element == 6) {
        for (int band = 0; band < 4; ++band) {
            if (ask(Query{ Fn::kGetActorValuePercent, kBloodThresholds[band], Op::kGreaterOrEqual, kHealth })) {
                x.blood = band;
                break;
            }
        }
    }
    if (element == 3) {
        x.lightning = 1;
        for (int i = 0; i < 4; ++i) {
            if (ask(Query{ Fn::kGetRandomPercent, kLightningChance[i], Op::kLess, 0 })) {
                x.lightning = 5 - i;
                break;
            }
        }
    }
    return x;
}

}  // namespace essb
