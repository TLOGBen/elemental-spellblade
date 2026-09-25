#pragma once
// Stage 4a of the native hit handler: which spell record each planned cast uses (local FormIDs from
// the generated manifest). Round 20 (N2): the proc spell is chosen by element and normal / power only;
// the round-18 magnitude variants (lightning R1-R5, blood B1-B3, wind sneak) are gone - the magnitude
// is the per-hit override now.
#include "HitMath.h"
#include "ManifestData.h"

#include <cstdint>

namespace essb {

constexpr const ProcRow* FindProc(int element, bool power) noexcept
{
    for (const auto& row : procRows) {
        if (row.element == element && row.power == static_cast<int>(power)) {
            return &row;
        }
    }
    return nullptr;
}

// 0 when the plan asks for something the manifest does not have (the handler treats that as a fault).
constexpr std::uint32_t SpellFor(const CastStep& step) noexcept
{
    switch (step.cast) {
    case Cast::kProc: {
        const ProcRow* row = FindProc(step.element, step.power);
        return row ? row->id : 0;
    }
    case Cast::kDrainMagicka:
        return spell::kDrainMagicka;
    case Cast::kDrainStamina:
        return spell::kDrainStamina;
    case Cast::kTrueDamage:
        return spell::kTrueDamage;
    case Cast::kSoakSlow:
        return spell::kSoakSlow;
    case Cast::kDispelMark:
        return spell::kDispelMark;
    case Cast::kSilence:
        return step.seconds >= 1 && step.seconds <= kSilenceSpellCount ? spell::kSilence[step.seconds - 1] : 0;
    case Cast::kHeal:
        return spell::kHeal;
    case Cast::kRestoreMagicka:
        return spell::kRestoreMagicka;
    case Cast::kRestoreStamina:
        return spell::kRestoreStamina;
    case Cast::kSpendMagicka:
        return spell::kSpendMagicka;
    case Cast::kBloodGuard:
        return spell::kBloodGuard;
    }
    return 0;
}

// Casts whose spell must keep its record magnitudes (script markers, silence with its -100 regen part).
constexpr bool UsesOverride(Cast cast) noexcept
{
    return cast != Cast::kDispelMark && cast != Cast::kSilence;
}

}  // namespace essb
