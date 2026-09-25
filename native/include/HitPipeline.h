#pragma once
// Stage 1 of the native hit handler: which hits count. Filter mirrors ESSBController.OnWeaponHit /
// ResolveHitWeaponType, so the DLL and the Papyrus difference patch accept the same hits.
// Round 20 (N2): a hit without an active form is accepted too (element 0) - the DLL now owns the
// no-form hit (baseline true damage, siphon, dispel). Pure/constexpr so tests drive it directly.
#include <cstdint>

namespace essb {

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
    kBadElement,
};

struct Verdict {
    Reject reason{ Reject::kAccepted };
    int weaponType{ kNoWeapon };
    int element{ 0 };  // accepted hits: 0 = no form, 1..11 = the active form's element
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
        return { Reject::kAccepted, weaponType, 0 };  // OnNoFormHit
    }
    if (!ValidElement(f.element)) {
        return { Reject::kBadElement, weaponType };
    }
    return { Reject::kAccepted, weaponType, static_cast<int>(f.element) };
}

}  // namespace essb
