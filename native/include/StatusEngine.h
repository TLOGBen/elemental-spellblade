// Round 22 review fix 6: the engine side of the status layer, written against an abstract engine so the native tests
// can run it on a fake effect list and a fake caster (native/tests/engine_test.cpp). Plugin.cpp supplies the real
// engine (RE::ActiveEffect lists, MagicCaster::CastSpellImmediate, ActiveEffect::Dispel, ModCallbackEvent).
//
//   ReadBoard     an actor's running effects -> Board (Status.h Read)
//   DispelWhere   collect first, then Dispel(true) each, with the self-dispel flag up (the removal sink skips those)
//   RunPlan       StatusPlan -> Lower -> dispel the old instances first (R3), then cast; pay / wash / event directly
//   Washes, Wash  ruling R5's predicate over the facts the engine reports, and the wash itself
//   OnRemoved     the effect-removed event, read-only: which of ours ended and why (expired / dispelled / death), with
//                 the target's crystal stacks read in the same frame (review fix 2)
//   PlanSettle    what an expiry does (Status.h's end-of-life rules), on the boards read in the settle task
//   CastSpells    every spell RunPlan can cast -- the adapter must resolve all of them (a missing one faults the DLL)
#pragma once

#include "Status.h"

#include <array>
#include <cstdint>
#include <vector>

namespace essb::engine {

// One running effect as the engine adapter reports it.
struct EffectView {
    std::uint32_t uid = 0;        // ActiveEffect::usUniqueID
    std::uint32_t effect = 0;     // local FormID of our base effect (status layer), 0 = not one of ours
    std::uint32_t spell = 0;      // local FormID of our spell, 0 = not one of ours
    float magnitude = 0.0f;
    float elapsed = 0.0f;
    float duration = 0.0f;
    // What the wash reads (native-verification-3 s15).
    bool hasSpell = false;        // the effect came from a spell item
    int spellType = 0;            // RE::MagicSystem::SpellType
    int castingSource = 0;        // RE::MagicSystem::CastingSource (0 left, 1 right, 2 voice, 3 instant)
    bool hostile = false;
    bool detrimental = false;
    bool ours = false;            // from Elements Spellblade.esp
    bool company = false;         // summon / bound weapon / reanimate / command summoned
};

// RE::MagicSystem::SpellType values the wash treats as cast by hand (spell, scroll, staff enchantment).
inline constexpr int kSpellTypeSpell = 0;
inline constexpr int kSpellTypeScroll = 13;
inline constexpr int kSpellTypeStaff = 12;
inline constexpr int kSourceLeft = 0;
inline constexpr int kSourceRight = 1;

template <class E>
Board ReadBoard(E& engine, Who who)
{
    Board board;
    engine.ForEach(who, [&](const EffectView& v, auto) {
        if (v.effect) {
            Read(board, RawEffect{ v.effect, v.magnitude, v.elapsed, v.duration });
        }
    });
    return board;
}

template <class E, class Match>
int DispelWhere(E& engine, Who who, Match&& match)
{
    std::vector<typename E::Handle> found;
    engine.ForEach(who, [&](const EffectView& v, typename E::Handle h) {
        if (match(v)) {
            found.push_back(h);
        }
    });
    const bool outer = engine.SelfDispel();
    engine.SetSelfDispel(true);
    for (const auto& h : found) {
        engine.Dispel(who, h);
    }
    engine.SetSelfDispel(outer);
    return static_cast<int>(found.size());
}

// Ruling R5: cast by hand (spell / scroll / staff from the left or right hand), still timed, beneficial -- not race
// powers, quest scripts (instant casts), abilities, diseases, potions, enchantments, summons / bound weapons, or ours.
constexpr bool Washes(const EffectView& v) noexcept
{
    const bool handCast = v.spellType == kSpellTypeSpell || v.spellType == kSpellTypeScroll || v.spellType == kSpellTypeStaff;
    const bool hand = v.castingSource == kSourceLeft || v.castingSource == kSourceRight;
    const bool timed = v.duration > 0.0f && v.elapsed < v.duration;
    const bool buff = !v.hostile && !v.detrimental;
    return v.hasSpell && handCast && hand && timed && buff && !v.ours && !v.company;
}

// Strips up to `limit` buffs; `log(view, washed)` sees every effect looked at (probe N3-3). Returns the count.
template <class E, class Log>
int Wash(E& engine, Who who, int limit, Log&& log)
{
    int taken = 0;
    return DispelWhere(engine, who, [&](const EffectView& v) {
        const bool wash = taken < limit && Washes(v);
        log(v, wash);
        if (wash) {
            ++taken;
        }
        return wash;
    });
}

// One op: Status.h Lower says which instances go first (native-verification-3 s5: always Dispel(true) before
// re-applying) and what is cast; pay, wash and the ModEvent are not casts.
template <class E>
void RunOp(E& engine, const StatusOp& op, const Tuning& tuning)
{
    const Lowered l = Lower(op, tuning.slowCapPct);
    const Who on = l.onPlayer ? Who::kPlayer : Who::kTarget;
    if (l.dispelSpell) {
        DispelWhere(engine, on, [&](const EffectView& v) { return v.spell == l.dispelSpell; });
    }
    if (l.dispelEffect) {
        const int dispelled = DispelWhere(engine, on, [&](const EffectView& v) { return v.effect == l.dispelEffect; });
        if (op.op == Op::kBleedDot || op.op == Op::kPoisonDot) {
            engine.LogReapply(op, dispelled);   // probe N3-2: how many old DoT instances one re-apply took off (expect 1)
        }
    }
    if (l.dispelEffect2) {
        DispelWhere(engine, on, [&](const EffectView& v) { return v.effect == l.dispelEffect2; });
    }
    if (l.spell && !(op.op == Op::kDamage && engine.Dead(on))) {
        engine.Cast(on, l.spell, l.magnitude, l.effectiveness);
    }
    switch (op.op) {
    case Op::kPayHealth:
        engine.PayHealth(op.magnitude);   // v0.4 5.3 代價：直接扣生命，永遠留 1 點（the engine clamps）
        break;
    case Op::kWash: {
        const int removed = Wash(engine, Who::kTarget, 999, [&](const EffectView& v, bool washed) { engine.LogWash(v, washed); });
        const float refund = op.magnitude * static_cast<float>(removed) * tuning.multRecovery;   // 淨潮
        if (removed > 0 && refund > 0.0f) {
            engine.Cast(Who::kPlayer, spell::kHeal, refund, 1.0f);
            engine.Cast(Who::kPlayer, spell::kRestoreMagicka, refund, 1.0f);
        }
        break;
    }
    case Op::kEvent:
        engine.Send(op);
        break;
    // Round 23 (N4): the engine-side ops (stamina, the resonance count, the interrupt task, 碎岩's ring, 冰心's scan).
    case Op::kPayStamina:
        engine.PayStamina(op.magnitude);
        break;
    case Op::kHurtHealth:
        engine.HurtHealth(op.magnitude);   // real damage, no clamp (it can kill)
        break;
    case Op::kResonance:
        engine.Resonance();
        break;
    case Op::kInterrupt:
        engine.Interrupt(on);
        break;
    case Op::kCrushArea:
        engine.CrushArea(op);
        break;
    case Op::kFreezeNearby:
        engine.FreezeNearby();
        break;
    default:
        break;
    }
}

template <class E>
void RunPlan(E& engine, const StatusPlan& plan, const Tuning& tuning)
{
    for (int i = 0; i < plan.count; ++i) {
        RunOp(engine, plan.ops[i], tuning);
    }
}

// ---------------------------------------------------------------- the effect-removed event

enum class Removal : std::uint8_t
{
    kIgnore,     // not ours, not one that settles, or not on the list any more
    kExpired,    // elapsed reached the duration and the actor lives: settle it
    kDispelled,  // taken off early (console, a dispel, a re-apply): nothing to settle
    kDeath,      // the actor died: death is N5's (the snapshot went to Papyrus)
};

struct Removed {
    Removal reason = Removal::kIgnore;
    Tag tag{};
    float magnitude = 0.0f;   // the effect's magnitude as it left (mark flags, fuse strength, landing damage)
    float elapsed = 0.0f;
    float duration = 0.0f;
    int crystals = 0;         // 冰晶 on the actor in the same frame (冰晶 lasts exactly as long as 冰封)
};

// Read-only: the event arrives while the effect is still on the list (native-verification-3 s2).
template <class E>
Removed OnRemoved(E& engine, Who who, std::uint32_t uid, bool dead)
{
    Removed out;
    bool found = false;
    Board board;
    engine.ForEachIncludingEnding(who, [&](const EffectView& v, auto) {
        if (v.effect) {
            Read(board, RawEffect{ v.effect, v.magnitude, v.elapsed, v.duration });
        }
        if (v.uid == uid && !found) {
            found = true;
            out.tag = TagOf(v.effect);
            out.magnitude = v.magnitude;
            out.elapsed = v.elapsed;
            out.duration = v.duration;
        }
    });
    if (!found || !Settles(out.tag)) {
        out.reason = Removal::kIgnore;
        return out;
    }
    out.crystals = board.Layers(StatusKind::kCrystal);
    const bool expired = out.duration > 0.0f && out.elapsed >= out.duration;
    out.reason = dead ? Removal::kDeath : expired ? Removal::kExpired : Removal::kDispelled;
    return out;
}

// ---------------------------------------------------------------- the settlement

struct Settled {
    bool jump = false;   // 跳印: a mark ended by time; the engine finds the nearest unmarked enemy and moves it there
};

// What one expiry does, on the boards read in the settle task. `x` comes from OnRemoved.
template <NodeReader Nodes, class Rng>
Settled PlanSettle(StatusPlan& plan, const Removed& x, Board& target, Board& self, const StatusInputs& in, const Nodes& nodes,
    Rng& rng)
{
    Settled out;
    using K = StatusKind;
    if (x.reason != Removal::kExpired) {
        return out;
    }
    if (x.tag.kind == TagKind::kMark) {
        if (!target.mark[x.tag.index].has) {   // not re-applied in the meantime
            const int flags = MarkFlags(x.magnitude);
            const bool ended = OnMarkExpired(plan, x.tag.index, flags, target, self, in, nodes, rng);
            out.jump = ended && nodes.Has(node::kCommonJump) && (flags & n3::kMarkJumped) == 0;
        }
    } else if (x.tag.kind == TagKind::kFear || x.tag.kind == TagKind::kFrenzy) {
        OnHallucinationEnd(plan, target, in, nodes);
    } else if (x.tag.kind == TagKind::kStatus) {
        const auto kind = static_cast<K>(x.tag.index);
        switch (kind) {
        case K::kFrozen:
            if (!target.Has(K::kFrozen)) {
                OnFrozenEnd(plan, target, self, in, nodes, x.crystals);
            }
            break;
        case K::kStarFuse:
            if (!target.Has(K::kStarFuse)) {
                OnStarFuseEnd(plan, target, self, in, nodes);
            }
            break;
        case K::kDeathCurse:
            OnDeathCurseEnd(plan, x.magnitude, target, self, in, nodes);
            break;
        case K::kAirborne:
            if (!target.Has(K::kAirborne)) {
                plan.Push(MakeEvent(Event::kLanding, x.magnitude));
            }
            break;
        case K::kHeat3:
        case K::kHeat4:
            if (!self.Has(kind)) {
                OnFuseEnd(plan, kind == K::kHeat3 ? 3 : 4, self, in, nodes);
            }
            break;
        default:
            break;   // 熔身結束後熱度歸零: the heat was already cleared when 熔身 began
        }
    }
    return out;
}

// ---------------------------------------------------------------- what the adapter must resolve

// Every spell (local FormID) Lower can name; Plugin.cpp resolves exactly these at load.
inline std::vector<std::uint32_t> CastSpells()
{
    std::vector<std::uint32_t> out;
    for (int k = 0; k < kStatusKindCount; ++k) {
        out.push_back(kStatusRecords[k].spell);
    }
    for (int e = kFire; e <= kAstral; ++e) {
        out.push_back(status::kMarkSpell[e]);
        out.push_back(status::kReactSpell[e]);
    }
    for (int i = 0; i < status::kDotMaxSeconds; ++i) {
        out.push_back(status::kBleedDot[i]);
        out.push_back(status::kPoisonDot[i]);
    }
    for (const std::uint32_t id : { spell::kTrueDamage, spell::kHeal, spell::kRestoreMagicka, spell::kRestoreStamina, spell::kBleedTick,
             spell::kSpendMagicka, spell::kDrainStamina, spell::kRiposte, spell::kDispelMark, spell::kBloodGuard }) {
        out.push_back(id);
    }
    for (const std::uint32_t id : spell::kSoak) {
        out.push_back(id);
    }
    return out;
}

// Every effect (local FormID) TagOf knows; Plugin.cpp resolves exactly these.
inline std::vector<std::uint32_t> TaggedEffects()
{
    std::vector<std::uint32_t> out;
    for (int k = 0; k < kStatusKindCount; ++k) {
        out.push_back(kStatusRecords[k].effect);
    }
    for (int e = kFire; e <= kAstral; ++e) {
        out.push_back(status::kMarkEffect[e]);
    }
    for (const std::uint32_t id : { status::kBleedDotEffect, status::kPoisonDotEffect, status::kFearEffect, status::kFrenzyEffect,
             status::kSlowEffect, effect::kBloodGuard }) {
        out.push_back(id);
    }
    return out;
}

}  // namespace essb::engine
