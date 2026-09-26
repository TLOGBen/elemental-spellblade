// Round 22 review fix 6: the engine side of the status layer (StatusEngine.h) against a fake effect list and a fake
// caster -- what Plugin.cpp's adapter does with them is only reading / dispelling / casting, so the order and the choice
// of instances is tested here:
//   read      ReadBoard picks up ours and ignores foreign effects
//   run       RunPlan dispels the old instance before re-applying (ruling R3) with the self-dispel flag up, casts with
//             the lowered magnitude / effectiveness, never casts damage on a dead target, pays, sends, washes + refunds
//   wash      ruling R5's predicate: only hand-cast, timed, beneficial buffs that are not ours and not company
//   removal   OnRemoved tells expiry / dispel / death apart and carries the crystal stacks of the same frame
//   settle    PlanSettle: 凍傷 on carried crystals when 冰晶 is already gone (review fix 2), 跳印 once, nothing for dispels
//   resolve   every spell Lower can name is in CastSpells() and every dispelled effect in TaggedEffects() (the adapter
//             resolves exactly those; ESSB_Util_BleedTick was missing before this test)
//   judged    聖痕: a target with the divine mark is judged undead / daedra (review fix 4)
//   crowd     round 24 (N5): SelectCrowd on a fake process list (2.9: the hostile, the hostile faction and the engaged;
//             never you, the dead, the unloaded, the commanded, a neutral you did not attack; teammates only as allies,
//             4 at most; nearest first, the limit), RunPlan selects each op's member before casting
//   death     round 24 (N5): fake death events -- DeathCounts (dead = false only, never you, something of ours / your
//             kill / your servant) and one death end to end: fake list -> crowd -> PlanDeath (the poison's death spread)
//             -> RunPlan: the follower and the neutral NPC are never cast on
#include "StatusEngine.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using essb::StatusKind;
using essb::Who;
using essb::engine::EffectView;

int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
}

bool Near(double a, double b)
{
    return std::abs(a - b) <= 2e-4 * std::max(1.0, std::abs(b));
}

struct FakeNodes {
    std::set<std::tuple<int, int, int, int>> branches;
    int Rank(const essb::NodeId&) const { return 0; }
    bool Has(const essb::BranchId& id) const { return branches.contains({ id.tree, id.route, id.tier, id.index }); }
    void Own(const essb::BranchId& id) { branches.insert({ id.tree, id.route, id.tier, id.index }); }
};

struct FixedRng {
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return lo + (hi - lo) * 0.5f; }
    bool Chance(float p) { return p >= 0.5f; }
};

struct FakeEffect {
    EffectView v;
    bool alive = true;
    bool ending = false;   // finishing: on the list, but ForEach (running effects) no longer reports it
};

struct Fake {
    using Handle = int;
    std::vector<FakeEffect> list[2];   // [0] target, [1] player
    bool self = false;
    bool deadTarget = false;
    std::vector<std::string> log;
    int washLooked = 0;

    static int Index(Who who) { return who == Who::kPlayer ? 1 : 0; }

    template <class Fn>
    void ForEach(Who who, Fn&& fn)
    {
        auto& l = list[Index(who)];
        for (int i = 0; i < static_cast<int>(l.size()); ++i) {
            if (l[i].alive && !l[i].ending) {
                fn(l[i].v, i);
            }
        }
    }

    template <class Fn>
    void ForEachIncludingEnding(Who who, Fn&& fn)
    {
        auto& l = list[Index(who)];
        for (int i = 0; i < static_cast<int>(l.size()); ++i) {
            if (l[i].alive) {
                fn(l[i].v, i);
            }
        }
    }

    void Dispel(Who who, Handle h)
    {
        auto& e = list[Index(who)][h];
        e.alive = false;
        log.push_back("dispel " + std::to_string(e.v.effect ? e.v.effect : e.v.uid) + (self ? " self" : " OTHER"));
    }
    bool SelfDispel() const { return self; }
    void SetSelfDispel(bool on) { self = on; }
    void Cast(Who who, std::uint32_t spell, float magnitude, float effectiveness)
    {
        char buf[128];
        std::snprintf(buf, sizeof(buf), "cast %u on %s mag %.4f eff %.4f", spell, who == Who::kPlayer ? "player" : "target",
            magnitude, effectiveness);
        log.push_back(buf);
        if (who == Who::kTarget) {
            castAt.push_back({ current, spell });
        }
    }
    bool Dead(Who who) { return who == Who::kTarget && deadTarget; }
    void PayHealth(float amount) { log.push_back("pay " + std::to_string(static_cast<int>(amount))); }
    void Send(const essb::StatusOp& op) { log.push_back("event " + std::to_string(static_cast<int>(op.event))); }
    void LogWash(const EffectView&, bool) { ++washLooked; }
    void LogReapply(const essb::StatusOp&, int dispelled) { reapplied.push_back(dispelled); }
    std::vector<int> reapplied;
    // Round 23 (N4): the engine-side ops of the self layer and the hurt path.
    void PayStamina(float amount) { log.push_back("stamina " + std::to_string(static_cast<int>(amount))); }
    void HurtHealth(float amount) { log.push_back("hurt " + std::to_string(static_cast<int>(amount))); }
    void Resonance() { log.push_back("resonance"); }
    void Interrupt(Who who) { log.push_back(std::string("interrupt ") + (who == Who::kPlayer ? "player" : "target")); }
    void CrushArea(const essb::StatusOp& op) { log.push_back("crush " + std::to_string(static_cast<int>(op.magnitude))); }
    void FreezeNearby() { log.push_back("freeze nearby"); }

    void Select(std::uint8_t at) { selected.push_back(at); current = at; }   // round 24: the crowd member of each op
    std::vector<std::uint8_t> selected;
    std::uint8_t current = 0;
    std::vector<std::pair<int, std::uint32_t>> castAt;   // (member, spell) of every target cast

    void Add(Who who, EffectView v) { list[Index(who)].push_back(FakeEffect{ v }); }
};

EffectView Ours(std::uint32_t effect, std::uint32_t spell, float magnitude, float elapsed, float duration, std::uint32_t uid = 0)
{
    EffectView v;
    v.uid = uid;
    v.effect = effect;
    v.spell = spell;
    v.magnitude = magnitude;
    v.elapsed = elapsed;
    v.duration = duration;
    v.hasSpell = true;
    v.ours = true;
    v.castingSource = 3;
    return v;
}

EffectView Buff(int spellType, int source, float elapsed, float duration, std::uint32_t uid)
{
    EffectView v;
    v.uid = uid;
    v.hasSpell = true;
    v.spellType = spellType;
    v.castingSource = source;
    v.elapsed = elapsed;
    v.duration = duration;
    return v;
}

const essb::StatusRecord& Rec(StatusKind k)
{
    return essb::kStatusRecords[static_cast<int>(k)];
}

void Read()
{
    Fake f;
    f.Add(Who::kTarget, Ours(Rec(StatusKind::kCurse).effect, Rec(StatusKind::kCurse).spell, 3.0f, 1.0f, 8.0f));
    f.Add(Who::kTarget, Buff(0, 1, 1.0f, 60.0f, 77));   // someone else's buff: no effect id of ours
    f.Add(Who::kTarget, Ours(essb::status::kPoisonDotEffect, essb::status::kPoisonDot[11], 6.0f, 2.0f, 12.0f));
    const essb::Board b = essb::engine::ReadBoard(f, Who::kTarget);
    Check(b.Layers(StatusKind::kCurse) == 3 && Near(b[StatusKind::kCurse].Remaining(), 7.0), "read: curse 3 layers, 7 s left");
    Check(b.poisonDot.has && Near(b.poisonDot.magnitude, 6.0) && Near(b.poisonDot.Remaining(), 10.0), "read: the poison DoT");
    int count = 0;
    for (const auto& s : b.slot) {
        count += s.has ? 1 : 0;
    }
    Check(count == 1, "read: the foreign buff is not a status");
}

void Run()
{
    essb::Tuning t;
    // Re-applying curse: the old instance goes first, flagged as ours, then the cast with effectiveness seconds / record.
    Fake f;
    f.Add(Who::kTarget, Ours(Rec(StatusKind::kCurse).effect, Rec(StatusKind::kCurse).spell, 2.0f, 5.0f, 8.0f));
    essb::StatusPlan plan;
    essb::Board target;
    essb::Writer{ plan, target, Who::kTarget }.Set(StatusKind::kCurse, 3.0f, Rec(StatusKind::kCurse).seconds * 1.5f);
    essb::engine::RunPlan(f, plan, t);
    Check(f.log.size() == 2 && f.log[0] == "dispel " + std::to_string(Rec(StatusKind::kCurse).effect) + " self", "run: dispel first, as ours");
    char want[128];
    std::snprintf(want, sizeof(want), "cast %u on target mag 3.0000 eff 1.5000", Rec(StatusKind::kCurse).spell);
    Check(f.log[1] == want, "run: then cast with magnitude 3, effectiveness 1.5 (" + f.log[1] + ")");
    Check(!f.self, "run: the self-dispel flag is restored");
    // Damage on a dead target is not cast; the removal of both DoTs dispels both; pay and events go to the engine.
    Fake g;
    g.deadTarget = true;
    g.Add(Who::kTarget, Ours(essb::status::kBleedDotEffect, essb::status::kBleedDot[4], 3.0f, 0.0f, 5.0f));
    g.Add(Who::kTarget, Ours(essb::status::kPoisonDotEffect, essb::status::kPoisonDot[4], 3.0f, 0.0f, 5.0f));
    essb::StatusPlan p2;
    p2.Push(essb::Amount(essb::Op::kDamage, 40.0f, essb::kFire));
    p2.Push(essb::MakeOp(essb::Op::kRemoveDots));
    p2.Push(essb::Amount(essb::Op::kPayHealth, 12.0f));
    p2.Push(essb::MakeEvent(essb::Event::kKnock, 3.0f));
    p2.Push(essb::MakeEvent(essb::Event::kFrozen, 3.0f));   // round 24: a body-only event never reaches Papyrus
    essb::engine::RunPlan(g, p2, t);
    Check(std::none_of(g.log.begin(), g.log.end(), [](const std::string& s) { return s.starts_with("cast"); }), "run: no damage cast on the dead");
    Check(std::count_if(g.log.begin(), g.log.end(), [](const std::string& s) { return s.starts_with("dispel"); }) == 2, "run: both DoTs dispelled");
    Check(std::find(g.log.begin(), g.log.end(), "pay 12") != g.log.end(), "run: the cost path pays");
    Check(std::find(g.log.begin(), g.log.end(), "event " + std::to_string(static_cast<int>(essb::Event::kKnock))) != g.log.end(),
        "run: the ModEvent goes to the engine");
    Check(std::find(g.log.begin(), g.log.end(), "event " + std::to_string(static_cast<int>(essb::Event::kFrozen))) == g.log.end(),
        "run: a body-only event (冰封) stays in the DLL");
    // Probe N3-2's count: re-applying the poison DoT over one running instance takes exactly that one off first.
    Fake h;
    h.Add(Who::kTarget, Ours(essb::status::kPoisonDotEffect, essb::status::kPoisonDot[9], 4.0f, 2.0f, 10.0f));
    essb::StatusPlan p3;
    p3.Push(essb::Amount(essb::Op::kPoisonDot, 6.0f, 0, 12.0f));
    essb::engine::RunPlan(h, p3, t);
    Check(h.reapplied.size() == 1 && h.reapplied[0] == 1 && !h.list[0][0].alive, "run: a DoT re-apply dispels the one old instance (N3-2)");
}

void Wash()
{
    using namespace essb::engine;
    Check(Washes(Buff(kSpellTypeSpell, kSourceRight, 1.0f, 60.0f, 1)), "wash: a hand-cast timed buff");
    Check(Washes(Buff(kSpellTypeStaff, kSourceLeft, 1.0f, 60.0f, 1)), "wash: a staff buff from the left hand");
    Check(!Washes(Buff(kSpellTypeSpell, 3, 1.0f, 60.0f, 1)), "wash: an instant cast (console / quest script) stays");
    Check(!Washes(Buff(7, kSourceRight, 1.0f, 60.0f, 1)), "wash: a potion stays");
    Check(!Washes(Buff(4, kSourceRight, 1.0f, 60.0f, 1)), "wash: an ability stays");
    Check(!Washes(Buff(kSpellTypeSpell, kSourceRight, 60.0f, 60.0f, 1)), "wash: an ended buff stays");
    Check(!Washes(Buff(kSpellTypeSpell, kSourceRight, 1.0f, 0.0f, 1)), "wash: a buff without a duration stays");
    EffectView hostile = Buff(kSpellTypeSpell, kSourceRight, 1.0f, 60.0f, 1);
    hostile.hostile = true;
    Check(!Washes(hostile), "wash: a hostile effect stays");
    EffectView ours = Buff(kSpellTypeSpell, kSourceRight, 1.0f, 60.0f, 1);
    ours.ours = true;
    Check(!Washes(ours), "wash: ours stays");
    EffectView summon = Buff(kSpellTypeSpell, kSourceRight, 1.0f, 60.0f, 1);
    summon.company = true;
    Check(!Washes(summon), "wash: a summon stays");
    // The op: two buffs washed, one potion kept, 淨潮 refunds B_max x 2 per buff (recovery multiplier 1).
    Fake f;
    f.Add(Who::kTarget, Buff(kSpellTypeSpell, kSourceRight, 1.0f, 60.0f, 1));
    f.Add(Who::kTarget, Buff(kSpellTypeSpell, kSourceLeft, 1.0f, 60.0f, 2));
    f.Add(Who::kTarget, Buff(7, kSourceRight, 1.0f, 60.0f, 3));
    essb::StatusPlan plan;
    plan.Push(essb::Amount(essb::Op::kWash, 20.0f));
    essb::Tuning t;
    essb::engine::RunPlan(f, plan, t);
    Check(!f.list[0][0].alive && !f.list[0][1].alive && f.list[0][2].alive, "wash: the two hand-cast buffs go, the potion stays");
    Check(f.washLooked == 3, "wash: every effect is logged (probe N3-3)");
    char heal[96];
    std::snprintf(heal, sizeof(heal), "cast %u on player mag 40.0000 eff 1.0000", essb::spell::kHeal);
    Check(std::find(f.log.begin(), f.log.end(), heal) != f.log.end(), "wash: 淨潮 heals 2 x 20");
}

void Removal()
{
    using essb::engine::Removal;
    const auto& frozen = Rec(StatusKind::kFrozen);
    const auto& crystal = Rec(StatusKind::kCrystal);
    const auto make = [&](float elapsed) {
        Fake f;
        FakeEffect e{ Ours(frozen.effect, frozen.spell, 1.0f, elapsed, 3.0f, 42) };
        e.ending = true;   // the event's own effect: still on the list, no longer running
        f.list[0].push_back(e);
        f.Add(Who::kTarget, Ours(crystal.effect, crystal.spell, 3.0f, 3.0f, 4.0f, 43));
        return f;
    };
    Fake a = make(3.0f);
    essb::engine::Removed r = essb::engine::OnRemoved(a, Who::kTarget, 42, false);
    Check(r.reason == Removal::kExpired && r.tag.kind == essb::TagKind::kStatus && r.crystals == 3, "removal: expired, 3 crystals carried");
    Fake b = make(2.0f);
    Check(essb::engine::OnRemoved(b, Who::kTarget, 42, false).reason == Removal::kDispelled, "removal: early = dispel");
    Fake c = make(1.0f);
    Check(essb::engine::OnRemoved(c, Who::kTarget, 42, true).reason == Removal::kDeath, "removal: dead = death");
    Check(essb::engine::OnRemoved(c, Who::kTarget, 99, false).reason == Removal::kIgnore, "removal: not on the list = ignore");
    Fake d;
    d.Add(Who::kTarget, Ours(Rec(StatusKind::kFissure).effect, Rec(StatusKind::kFissure).spell, 1.0f, 8.0f, 8.0f, 7));
    Check(essb::engine::OnRemoved(d, Who::kTarget, 7, false).reason == Removal::kIgnore, "removal: a status that does not settle");
    Fake e;
    e.Add(Who::kTarget, Buff(0, 1, 60.0f, 60.0f, 8));
    Check(essb::engine::OnRemoved(e, Who::kTarget, 8, false).reason == Removal::kIgnore, "removal: a foreign effect");
}

void Settle()
{
    essb::Config c;
    c.damage[essb::kFrost] = { 8.0f, 10.0f };
    essb::Tuning t;
    essb::StatusInputs in;
    in.config = &c;
    in.tuning = &t;
    FakeNodes nodes;
    nodes.Own(essb::node::kFrostFrostbite);
    FixedRng rng;
    // 冰晶 expired in the same frame as 冰封: the board read in the task has none, the removal carried 3.
    essb::engine::Removed x;
    x.reason = essb::engine::Removal::kExpired;
    x.tag = essb::TagOf(Rec(StatusKind::kFrozen).effect);
    x.crystals = 3;
    essb::Board target;
    essb::Board self;
    essb::StatusPlan plan;
    essb::engine::PlanSettle(plan, x, target, self, in, nodes, rng);
    bool found = false;
    for (int i = 0; i < plan.count; ++i) {
        found = found || (plan.ops[i].op == essb::Op::kDamage && plan.ops[i].element == essb::kFrost && Near(plan.ops[i].magnitude, 15.75));
    }
    Check(found, "settle: 凍傷 3 carried crystals x B_max 10 x 0.5 x G 1.05 = 15.75");
    // A dispel settles nothing.
    x.reason = essb::engine::Removal::kDispelled;
    essb::StatusPlan none;
    essb::engine::PlanSettle(none, x, target, self, in, nodes, rng);
    Check(none.count == 0, "settle: a dispel settles nothing");
    // 跳印: a mark ended by time asks for the jump once; a mark that already jumped does not.
    FakeNodes jump;
    jump.Own(essb::node::kCommonJump);
    essb::engine::Removed m;
    m.reason = essb::engine::Removal::kExpired;
    m.tag = essb::TagOf(essb::status::kMarkEffect[essb::kFire]);
    essb::Board t2;
    essb::StatusPlan p2;
    Check(essb::engine::PlanSettle(p2, m, t2, self, in, jump, rng).jump, "settle: 跳印 asks for the jump");
    m.magnitude = static_cast<float>(essb::n3::kMarkJumped);
    essb::Board t3;
    essb::StatusPlan p3;
    Check(!essb::engine::PlanSettle(p3, m, t3, self, in, jump, rng).jump, "settle: a jumped mark does not jump again");
}

void Resolve()
{
    const auto spells = essb::engine::CastSpells();
    const auto effects = essb::engine::TaggedEffects();
    auto has = [](const std::vector<std::uint32_t>& v, std::uint32_t id) { return std::find(v.begin(), v.end(), id) != v.end(); };
    auto lowered = [&](const essb::StatusOp& op, const std::string& what) {
        const essb::Lowered l = essb::Lower(op, 70.0f);
        Check(!l.spell || has(spells, l.spell), what + ": the cast spell is resolved");
        Check(!l.dispelSpell || has(spells, l.dispelSpell), what + ": the dispelled spell is resolved");
        Check(!l.dispelEffect || has(effects, l.dispelEffect), what + ": the dispelled effect is resolved");
        Check(!l.dispelEffect2 || has(effects, l.dispelEffect2), what + ": the second dispelled effect is resolved");
    };
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        essb::StatusOp op = essb::MakeOp(essb::Op::kApply, essb::kStatusRecords[k].onPlayer ? Who::kPlayer : Who::kTarget);
        op.kind = static_cast<StatusKind>(k);
        op.magnitude = 1.0f;
        op.seconds = 5.0f;
        lowered(op, "apply " + std::to_string(k));
        op.op = essb::Op::kRemove;
        lowered(op, "remove " + std::to_string(k));
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        essb::StatusOp op = essb::MakeOp(essb::Op::kApplyMark);
        op.element = e;
        op.seconds = 8.0f;
        lowered(op, "mark");
        lowered(essb::Amount(essb::Op::kDamage, 5.0f, e), "reaction damage");
    }
    for (int s = 1; s <= 45; ++s) {
        lowered(essb::Amount(essb::Op::kBleedDot, 3.0f, 0, static_cast<float>(s)), "bleed DoT");
        lowered(essb::Amount(essb::Op::kPoisonDot, 3.0f, 0, static_cast<float>(s)), "poison DoT");
    }
    for (int s = 1; s <= 30; ++s) {
        lowered(essb::Amount(essb::Op::kSlow, 20.0f, 0, static_cast<float>(s)), "slow");
    }
    for (const essb::Op op : { essb::Op::kHeal, essb::Op::kRestoreMagicka, essb::Op::kRestoreStamina, essb::Op::kBleedDrain }) {
        lowered(essb::Amount(op, 5.0f), "restore / 放血");
    }
    lowered(essb::Amount(essb::Op::kDamage, 5.0f, 0), "true damage");
    lowered(essb::MakeOp(essb::Op::kRemoveDots), "remove DoTs");
    Check(has(spells, essb::spell::kBleedTick), "resolve: ESSB_Util_BleedTick (放血) is resolved");
    // Round 23 (N4): every op the self layer and the hurt path can push.
    for (const essb::Op op : { essb::Op::kSpendMagicka, essb::Op::kDrainStamina, essb::Op::kBloodGuardPool, essb::Op::kPayStamina,
             essb::Op::kResonance, essb::Op::kInterrupt, essb::Op::kCrushArea, essb::Op::kFreezeNearby }) {
        lowered(essb::Amount(op, 5.0f), "round 23 op " + std::to_string(static_cast<int>(op)));
    }
    lowered(essb::Amount(essb::Op::kBloodGuardPool, 0.0f), "護血 pool removed");
    lowered(essb::MakeOp(essb::Op::kRiposte, Who::kPlayer), "反擊 window");
    lowered(essb::MakeOp(essb::Op::kDispelMarkOn), "咒返 滅法印");
    Check(has(effects, essb::effect::kBloodGuard), "resolve: the 護血 pool effect is tagged (it is dispelled before a re-apply)");
}

void Judged()
{
    FakeNodes stigma;
    stigma.Own(essb::node::kDivineStigma);
    essb::Board marked;
    marked.mark[essb::kDivine] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
    essb::TargetFacts living;
    Check(essb::JudgedTarget(living, marked, stigma).undeadOrDaedra, "聖痕: the marked target is judged undead / daedra");
    Check(!essb::JudgedTarget(living, essb::Board{}, stigma).undeadOrDaedra, "聖痕: without the mark it is not");
    Check(!essb::JudgedTarget(living, marked, FakeNodes{}).undeadOrDaedra, "聖痕: without the node it is not");
}

essb::engine::ActorView Actor(float x, bool hostile, float y = 0.0f)
{
    essb::engine::ActorView a;
    a.hostile = hostile;
    a.pos = { x, y, 0.0f };
    return a;
}

void Crowd()
{
    using essb::engine::ActorView;
    using essb::engine::SelectCrowd;
    std::vector<ActorView> list;
    ActorView you = Actor(0, false);
    you.you = true;
    list.push_back(you);                          // 0 you
    list.push_back(Actor(300, true));             // 1 the primary (read separately)
    list.push_back(Actor(500, true));             // 2 hostile: in
    ActorView dead = Actor(400, true);
    dead.dead = true;
    list.push_back(dead);                         // 3 dead
    ActorView far = Actor(450, true);
    far.loaded = false;
    list.push_back(far);                          // 4 not loaded
    ActorView summon = Actor(350, true);
    summon.commanded = true;
    list.push_back(summon);                       // 5 commanded (summon, raised servant)
    ActorView follower = Actor(600, false);
    follower.teammate = true;
    list.push_back(follower);                     // 6 follower: an ally
    ActorView away = Actor(2000, false);
    away.teammate = true;
    list.push_back(away);                         // 7 follower beyond 15 m of you
    list.push_back(Actor(200, false));            // 8 neutral, not attacked: never
    ActorView engaged = Actor(700, false);
    engaged.engaged = true;
    list.push_back(engaged);                      // 9 neutral you attacked (30 s marker): in
    list.push_back(Actor(1400, true));            // 10 hostile, 15.7 m from the centre, 20 m from you: out
    list.push_back(Actor(1300, true));            // 11 hostile, 14.3 m from the centre: in
    const std::array<float, 3> centre{ 300, 0, 0 };
    const std::array<float, 3> origin{ 0, 0, 0 };
    auto picks = SelectCrowd(list, 1, centre, 1050.0f, origin, 1050.0f, essb::n5::kCrowdMax);
    Check(picks.size() == 4 && picks[0].index == 2 && picks[1].index == 9 && picks[2].index == 11 && picks[3].index == 6 &&
          !picks[0].ally && !picks[2].ally && picks[3].ally, "crowd: 2.9 eligibility, nearest first, the ally last");
    for (const auto& p : picks) {
        Check(p.index != 8 && p.index != 3 && p.index != 4 && p.index != 5 && p.index != 0 && p.index != 1 && p.index != 7 &&
              p.index != 10, "crowd: never the neutral, the dead, the unloaded, the commanded, you, the primary, a far one");
    }
    picks = SelectCrowd(list, 1, centre, 1050.0f, origin, 1050.0f, 2);
    Check(picks.size() == 3 && picks[0].index == 2 && picks[1].index == 9 && picks[2].ally, "crowd: the hostile limit (allies apart)");
    std::vector<ActorView> many;
    for (int i = 0; i < 6; ++i) {
        ActorView a = Actor(100.0f + 10.0f * static_cast<float>(i), false);
        a.teammate = true;
        many.push_back(a);
    }
    picks = SelectCrowd(many, -1, origin, 1050.0f, origin, 1050.0f, essb::n5::kCrowdMax);
    Check(picks.size() == 4 && picks[0].index == 0 && picks[3].index == 3, "crowd: 4 allies at most, nearest first");
    // RunPlan selects the member of every op before running it; a cast goes to that member.
    Fake f;
    essb::StatusPlan plan;
    essb::StatusOp a = essb::Amount(essb::Op::kDamage, 10.0f, essb::kFire);
    a.at = 2;
    plan.Push(a);
    plan.Push(essb::Amount(essb::Op::kDamage, 5.0f, essb::kFrost));
    essb::StatusOp h = essb::Amount(essb::Op::kHeal, 7.0f);
    h.at = 3;
    plan.Push(h);
    essb::Tuning t;
    essb::engine::RunPlan(f, plan, t);
    Check(f.selected.size() == 3 && f.selected[0] == 2 && f.selected[1] == 0 && f.selected[2] == 3, "run: each op selects its member");
    Check(f.castAt.size() == 2 && f.castAt[0].first == 2 && f.castAt[1].first == 0, "run: the damage goes to the selected member");
}

void Death()
{
    using essb::engine::DeathCounts;
    using essb::engine::DeathEvent;
    essb::Board empty;
    essb::Board poisoned;
    poisoned.poisonDot = essb::Slot{ true, 2.0f, 0.0f, 5.0f };
    Check(!DeathCounts(DeathEvent{ true, false, true, false }, poisoned), "death: the dead = true event is not ours (s10)");
    Check(!DeathCounts(DeathEvent{ false, true, false, false }, poisoned), "death: your own death is never handled");
    Check(!DeathCounts(DeathEvent{ false, false, false, false }, empty), "death: nothing of ours, not your kill: skipped");
    Check(DeathCounts(DeathEvent{ false, false, false, false }, poisoned), "death: our poison on the corpse counts");
    Check(DeathCounts(DeathEvent{ false, false, true, false }, empty), "death: your kill counts (無魔, 飲血, 淨土)");
    Check(DeathCounts(DeathEvent{ false, false, false, true }, empty), "death: your servant's death counts (亡衛)");
    essb::Board hushed;
    hushed.hush = essb::Slot{ true, 2.0f, 0.0f, 10.0f };
    Check(DeathCounts(DeathEvent{ false, false, false, false }, hushed), "death: 寂 counts as ours");
    // One death end to end: the corpse carries poison; the process list has a hostile, a follower and a neutral NPC
    // within 15 m -- only the hostile takes the spread (2.9), and the executor casts on that member only.
    using essb::engine::ActorView;
    std::vector<ActorView> list;
    ActorView you = Actor(0, false);
    you.you = true;
    list.push_back(you);
    list.push_back(Actor(100, true));             // the corpse (member 0; read separately)
    list.push_back(Actor(300, true));             // a hostile
    ActorView follower = Actor(150, false);
    follower.teammate = true;
    list.push_back(follower);
    list.push_back(Actor(250, false));            // a neutral NPC
    const auto picks = essb::engine::SelectCrowd(list, 1, { 100, 0, 0 }, 1050.0f, { 0, 0, 0 }, 1050.0f, essb::n5::kCrowdMax);
    auto crowd = std::make_unique<essb::Crowd>();
    crowd->you = { 0, 0, 0 };
    crowd->m[0].has = true;
    crowd->m[0].pos = { 100, 0, 0 };
    crowd->m[0].board = poisoned;
    crowd->m[0].body.healthMax = 100.0f;
    crowd->count = 1;
    for (const auto& p : picks) {
        essb::Member& m = crowd->m[crowd->count++];
        m.has = true;
        m.ally = p.ally;
        m.pos = list[p.index].pos;
    }
    Check(crowd->count == 3 && !crowd->m[1].ally && crowd->m[2].ally, "death: the crowd is the hostile and the follower (ally)");
    essb::Config c;
    for (int e = 1; e <= 11; ++e) {
        c.damage[e] = { 8.0f, 10.0f };
    }
    essb::Tuning t;
    essb::StatusInputs in;
    in.config = &c;
    in.tuning = &t;
    in.n4 = true;
    essb::BodyInputs bin;
    bin.in = &in;
    bin.stamina = bin.staminaMax = 100.0f;
    bin.magicka = bin.magickaMax = 100.0f;
    essb::Board self;
    auto plan = std::make_unique<essb::StatusPlan>();
    FakeNodes nodes;
    FixedRng rng;
    essb::DeathFacts facts;
    Check(DeathCounts(DeathEvent{ false, false, false, false }, crowd->m[0].board), "death: this one counts");
    essb::PlanDeath(*plan, *crowd, self, bin, facts, nodes, rng);
    Check(crowd->m[1].board.poisonDot.has && !crowd->m[2].board.poisonDot.has, "death: the spread reaches the hostile, never the follower");
    Fake f;
    essb::engine::RunPlan(f, *plan, t);
    Check(!f.castAt.empty(), "death: the spread is cast");
    for (const auto& [member, spell] : f.castAt) {
        Check(member == 1, "death: every cast goes to the hostile member (never the follower, never the neutral)");
    }
}

}  // namespace

int main()
{
    try {
        Read();
        Run();
        Wash();
        Removal();
        Settle();
        Resolve();
        Judged();
        Crowd();
        Death();
        std::printf("NATIVE ENGINE E ok: %d checks (read, run order, wash R5, removal reasons + carried crystals, settle, "
                    "resolve every lowered spell, 聖痕, the crowd from a fake process list, fake death events)\n", checks);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "ENGINE TEST FAILED: %s\n", e.what());
        return 1;
    }
}
