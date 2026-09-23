#pragma once
// Stage 3 of the hit pipeline: pure selection of the proc spell key.
// No engine, allocation, global state or RNG. Vetoes (disabled, allies, dead targets, ...)
// are handled earlier by Filter() in HitPipeline.h; select() only sees accepted hits.
#include <cstdint>

namespace essb {

// Values of CTDA 597 GetEquippedItemType for the right hand, as the old entry-51 segments tested them.
inline constexpr int kItemBow = 7;
inline constexpr int kItemCrossbow = 12;

struct Input {
    int element{};    // 1..11 (ESSB_CurrentElement)
    int rightItem{};  // CTDA 597 right hand: kItemBow, kItemCrossbow, or 0 for anything else
    bool power{};     // CTDA 673 IsPowerAttacking
    bool sneak{};     // CTDA 286 IsSneaking
    int blood{-1};    // element 6 only: health band 0..3 (>=85%, >=50%, >=20%, >=0%); -1 = no band matched
    int lightning{};  // element 3 only: band 1..5 chosen by the GetRandomPercent chain
};

struct Key {
    int element{};
    int power{};
    int sneak{};
    int blood{};
    int lightning{};

    constexpr bool operator==(const Key&) const = default;

    constexpr int index() const noexcept
    {
        return (((element * 2 + power) * 2 + sneak) * 4 + blood) * 6 + lightning;
    }
};

// Upper bound of Key::index() for element 11, power 1, sneak 1, blood 3, lightning 5.
inline constexpr int kKeyCount = Key{ 11, 1, 1, 3, 5 }.index() + 1;

constexpr Key select(const Input& x) noexcept
{
    if (x.element < 1 || x.element > 11) {
        return {};
    }
    const bool ranged = x.rightItem == kItemBow || x.rightItem == kItemCrossbow;
    Key key{};
    key.element = x.element;
    // Bows and crossbows have no power attack: a sneak shot takes the power variant (round 18).
    key.power = ranged ? int(x.sneak) : int(x.power);
    key.sneak = x.element == 5 ? int(x.sneak) : 0;
    if (x.element == 6) {
        if (x.blood < 0 || x.blood > 3) {
            return {};
        }
        key.blood = x.blood;
    }
    if (x.element == 3) {
        if (x.lightning < 1 || x.lightning > 5) {
            return {};
        }
        key.lightning = x.lightning;
    }
    return key;
}

}  // namespace essb
