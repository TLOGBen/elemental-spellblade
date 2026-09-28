// Round 27: hand anchors for the damage sums (G1), the open's layer counts (G3), 熔斷's formless fuse (G4) and the burst's
// op list (B-small), on the real planners (Status.h, Reactions.h). Every expected number below is worked out by hand in its
// comment from v0.4's text -- tree level 100 (G = 1 + 0.05 × 100 = 6), 節點倍率 5 (the MCM's highest), every main line
// at its 15 points (a percentage line gives 15 × p × 5 = 75p), 同調 three stages.
//   G1  one M_mod = 1 + Σ; a percentage-of-health effect (碎冰, 聖裁 III, 死咒's lost-health part, 血潮's current-health
//       part) takes only its own lines -- the end lines, 導引, 協奏 and the burst's lines do not move it; 催毒 does not
//       compound
//   G3  an open's layer / dose / freeze counts take the 開印效果 line without 節點倍率
//   G4  熔斷 kept the heat past the form: the fuse running out with no fire form is a vent (no 過熱, no 10% cost)
//   B   a burst on 24 targets with two marks each and every fusion node fits the op list (it never faults the DLL)
#include "EngineFacts.h"
#include "Reactions.h"
#include "Status.h"
#include "StatusEngine.h"

#include <algorithm>
#include <cmath>
#include <iterator>
#include <cstdio>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

using essb::StatusKind;
int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
}

bool Near(double a, double b, double tol = 1e-3)
{
    return std::abs(a - b) <= tol * std::max(1.0, std::abs(b));
}

// Every main line at 15 points; the branches listed (or all of them).
struct MaxNodes {
    std::set<std::tuple<int, int, int, int>> branches;
    bool allBranches = false;
    int Rank(const essb::NodeId& id) const { return id.tree >= 0 ? essb::kMainMaxRank : 0; }
    bool Has(const essb::BranchId& id) const { return allBranches || branches.contains({ id.tree, id.route, id.tier, id.index }); }
    void Add(const essb::BranchId& id) { branches.insert({ id.tree, id.route, id.tier, id.index }); }
};

struct MidRng {
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return lo + (hi - lo) * 0.5f; }
    bool Chance(float) { return false; }
};

struct World {
    essb::Config config = essb::MakeConfig();
    essb::Tuning tuning;
    essb::StatusInputs in;
    MidRng rng;

    explicit World(float nodeScale = 5.0f)
    {
        tuning.level.fill(100.0f);
        tuning.nodeScale = nodeScale;
        tuning.syncStage = 3;
        in.config = &config;
        in.tuning = &tuning;
        in.n4 = true;
        in.body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
    }
};

float DamageOf(const essb::StatusPlan& plan, int element, int at = 0)
{
    float sum = 0.0f;
    for (int i = 0; i < plan.count; ++i) {
        const essb::StatusOp& op = plan.ops[i];
        if (op.op == essb::Op::kDamage && op.element == element && op.at == at) {
            sum += op.magnitude;
        }
    }
    return sum;
}

// ---------------------------------------------------------------- G1: 碎冰 at the frost end
void ShatterAnchors()
{
    for (const bool vip : { false, true }) {
        for (const bool extras : { false, true }) {
            World w;
            w.in.body.vip = vip;
            MaxNodes nodes;
            nodes.Add(essb::node::kFrostSharp);   // 銳碎
            essb::Board target;
            target.mark[essb::kFrost] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
            target[StatusKind::kFrozen] = essb::Slot{ true, 1.0f, 1.0f, 3.0f };
            target[StatusKind::kCrystal] = essb::Slot{ true, 3.0f, 1.0f, 4.0f };
            if (extras) {
                target[StatusKind::kGuided] = essb::Slot{ true, 1.5f, 0.0f, 30.0f };   // 導引 ×1.5 waits for this end
            }
            essb::Board me;
            auto plan = std::make_unique<essb::StatusPlan>();
            essb::PlanEnd(*plan, essb::kFrost, essb::EndReason::kCut, extras ? 2.0f : 1.0f, false, target, me, w.in, nodes, w.rng);
            // 銳碎 25% (首領 12%) × (1 + 碎冰 +3%／點 75 × 0.03 = 2.25) + 3 crystals × 5% (首領 2.5%), of 1000 max health:
            //   non-boss 0.25 × 3.25 + 0.15 = 0.9625 → 962.5; boss 0.12 × 3.25 + 0.075 = 0.465 → 465.
            // The end lines (all maxed), a K of 2 and 導引 ×1.5 change nothing: its own lines only.
            const float want = vip ? 465.0f : 962.5f;
            Check(Near(DamageOf(*plan, 0), want), std::string("G1 碎冰 ") + (vip ? "boss" : "non-boss") + (extras ? " with K 2 and 導引" : "") +
                ": " + std::to_string(DamageOf(*plan, 0)) + " != " + std::to_string(want));
        }
    }
}

// ---------------------------------------------------------------- G1: 聖裁 III on the third hit
void JudgeAnchors()
{
    for (const bool vip : { false, true }) {
        World w;
        w.in.body.vip = vip;
        MaxNodes nodes;
        essb::Board target;
        target.mark[essb::kDivine] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
        target[StatusKind::kJudge] = essb::Slot{ true, 2.0f, 0.5f, 4.0f };   // the third hit
        essb::Board me;
        me[StatusKind::kHoly3] = essb::Slot{ true, 1.0f, 3.0f, 8.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanStatusHit(*plan, essb::kDivine, false, target, me, w.in, nodes, w.rng);
        // 4% (首領 2%) of 1000 × T (聖佑 III +35% → 1.35) × (1 + 聖裁傷害 +2%／點 75 × 0.02 = 1.5 → 2.5) = 135 (首領 67.5);
        // 聖佑各階 (75 × 0.01 × 3 = 2.25) is not its line and does not enter.
        const float want = vip ? 67.5f : 135.0f;
        Check(Near(DamageOf(*plan, essb::kDivine), want), std::string("G1 聖裁 III ") + (vip ? "boss" : "non-boss") + ": " +
                                                               std::to_string(DamageOf(*plan, essb::kDivine)) + " != " + std::to_string(want));
    }
}

// ---------------------------------------------------------------- G1: 死咒 settles
void DeathCurseAnchors()
{
    for (const float fuse : { 1.0f, 5.0f }) {
        World w;
        w.in.body = essb::Body{ 200.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
        MaxNodes nodes;
        essb::Board target;
        target[StatusKind::kDeathCurse] = essb::Slot{ true, fuse, 3.0f, 3.0f };
        essb::Board me;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::OnDeathCurseEnd(*plan, fuse, target, me, w.in, nodes);
        // B_max(暗) 10 × 2.0 × G 6 = 120 × the fuse; lost 800 × (15% + 死咒係數 75 × 0.005 = 0.375) = 420 whatever the fuse:
        //   fuse 1 → 540; fuse 5 (K × M_mod of a big end) → 600 + 420 = 1020.
        const float want = 120.0f * fuse + 420.0f;
        Check(Near(DamageOf(*plan, essb::kDarkness), want), "G1 死咒 fuse " + std::to_string(fuse) + ": " +
                                                                std::to_string(DamageOf(*plan, essb::kDarkness)) + " != " + std::to_string(want));
        bool marked = false;
        for (int i = 0; i < plan->count; ++i) {
            if (plan->ops[i].op == essb::Op::kDamage) {
                Check(marked, "B-small: 冥召's marker is set before the death curse's damage");
            }
            marked = marked || (plan->ops[i].op == essb::Op::kApply && plan->ops[i].kind == StatusKind::kCurseKill);
        }
        Check(marked, "B-small: the death curse settlement sets kCurseKill");
    }
}

// ---------------------------------------------------------------- G1: 血潮 and the flat end sum
essb::Crowd OneTarget(const essb::Board& board, float health, bool vip)
{
    essb::Crowd c;
    c.m[0].has = true;
    c.m[0].board = board;
    c.m[0].body = essb::Body{ health, 1000.0f, 100.0f, 100.0f, vip, false, 100.0f };
    c.m[0].magickaMax = 100.0f;
    c.count = 1;
    return c;
}

void EndBodyAnchors()
{
    // 血潮's current-health part: no bleed left; 放血終焉 (10% → 20%, 首領 3% → 6%) × (1 + 血潮 +3%／點 2.25) of 1000 now:
    //   non-boss 0.2 × 3.25 × 1000 = 650, boss 0.06 × 3.25 × 1000 = 195 -- with 導引 ×1.5 on the target and every end
    //   line maxed, still 650 / 195.
    for (const bool vip : { false, true }) {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kBloodEndBleed);
        essb::Board target;
        target.mark[essb::kBlood] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
        target[StatusKind::kGuided] = essb::Slot{ true, 1.5f, 0.0f, 30.0f };
        essb::Board me;
        essb::Crowd crowd = OneTarget(target, 1000.0f, vip);
        w.in.body = crowd.m[0].body;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanEnd(*plan, essb::kBlood, essb::EndReason::kCut, 1.0f, false, crowd.m[0].board, me, w.in, nodes, w.rng);
        essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        essb::RunBodies(*plan, 0, crowd, me, bin, nodes, w.rng);
        const float want = vip ? 195.0f : 650.0f;
        Check(Near(DamageOf(*plan, essb::kBlood), want), std::string("G1 血潮 current-health part ") + (vip ? "boss" : "non-boss") + ": " +
                                                             std::to_string(DamageOf(*plan, essb::kBlood)) + " != " + std::to_string(want));
    }
    // A flat end is B_max × K × G × M_mod with ONE sum: the frost end on an unfrozen target (碎冰 ×1.0 of B_max 10):
    //   M_mod = 1 + common 終焉 0.75 + 終焉再 0.75 + 同調三段時終焉 0.75 + 冰 終焉 +2%／點 1.5 + 碎冰 +3%／點 2.25 = 7.0;
    //   10 × 1.0 × 7.0 × G 6 = 420 (the old product 3.25 × 2.5 × 3.25 gave 1584.375).
    World w;
    MaxNodes nodes;
    essb::Board target;
    target.mark[essb::kFrost] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
    essb::Board me;
    essb::Crowd crowd = OneTarget(target, 1000.0f, false);
    auto plan = std::make_unique<essb::StatusPlan>();
    essb::PlanEnd(*plan, essb::kFrost, essb::EndReason::kCut, 1.0f, false, crowd.m[0].board, me, w.in, nodes, w.rng);
    essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
    essb::RunBodies(*plan, 0, crowd, me, bin, nodes, w.rng);
    Check(Near(DamageOf(*plan, essb::kFrost), 420.0f), "G1 the frost end's one sum: " + std::to_string(DamageOf(*plan, essb::kFrost)) + " != 420");
}

// ---------------------------------------------------------------- G1: 催毒 does not compound
void CatalyseAnchors()
{
    World w;
    MaxNodes nodes;
    essb::Board target;
    target.poisonDot = essb::Slot{ true, 10.0f, 2.0f, 10.0f };   // 10 a second, 8 s left
    essb::Board me;
    float last = 0.0f;
    for (int end = 0; end < 3; ++end) {
        target.mark[essb::kPoison] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
        target[StatusKind::kEndCooldown] = essb::Slot{};
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanEnd(*plan, essb::kPoison, essb::EndReason::kCut, 1.0f, false, target, me, w.in, nodes, w.rng);
        for (int i = 0; i < plan->count; ++i) {
            if (plan->ops[i].op == essb::Op::kPoisonDot && plan->ops[i].magnitude > 0.0f) {
                last = plan->ops[i].magnitude;
            }
        }
        // Round 27b (review B N5): 催毒 ×2 exactly, its line joining the per-dose M_mod: the base 10 carries 1 + 每劑 +2%／點
        // (75 × 0.02 = 1.5) = 2.5; catalysed it reads 1 + 1.5 + 催毒期間中毒傷害 (75 × 0.03 = 2.25) = 4.75, so
        // 10 × 2 × 4.75 / 2.5 = 38, and it stays 38 at every further end (round 27 had × 2 × 3.25 = 65; the old code
        // multiplied again: 65, 422.5, 2746).
        Check(Near(last, 38.0f) && Near(target[StatusKind::kCatalyzed].magnitude, 3.8f),
            "G1 催毒 end " + std::to_string(end + 1) + ": " + std::to_string(last) + " != 38");
    }
}

// ---------------------------------------------------------------- G3: the open's counts
void OpenCountAnchors()
{
    for (const float scale : { 1.0f, 5.0f }) {
        World w(scale);
        w.tuning.syncStage = 0;
        MaxNodes nodes;   // 開印效果 at 15 points: counts × (1 + 15 × 0.03 = 1.45) whatever the 節點倍率
        essb::Board target;
        essb::Board me;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanStatusHit(*plan, essb::kDarkness, false, target, me, w.in, nodes, w.rng, false);
        // 開印詛咒: 2 + 15 / 5 = 5 layers × 1.45 = 7.25 → 7 (the mid draw rounds down 0.25) -- the same at 節點倍率 1 and 5
        // (was 5 × (1 + 15 × 0.03 × 5 = 3.25) = 16.25 → capped at the curse cap at 5).
        Check(target.Layers(StatusKind::kCurse) == 7,
            "G3 the open's curse count at 節點倍率 " + std::to_string(scale) + ": " + std::to_string(target.Layers(StatusKind::kCurse)) + " != 7");
    }
}

// ---------------------------------------------------------------- G4: 熔斷's fuse with no form
void MeltdownAnchors()
{
    for (const int form : { 0, static_cast<int>(essb::kFire) }) {
        World w;
        w.in.formElement = form;
        MaxNodes nodes;
        essb::Board me;
        me[StatusKind::kHeat3] = essb::Slot{ true, 0.0f, 10.0f, 10.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::OnFuseEnd(*plan, 3, me, w.in, nodes);
        bool overheat = false;
        bool paid = false;
        for (int i = 0; i < plan->count; ++i) {
            overheat = overheat || (plan->ops[i].op == essb::Op::kEvent && plan->ops[i].event == essb::Event::kOverheat);
            paid = paid || plan->ops[i].op == essb::Op::kPayHealth;
        }
        if (form == 0) {
            Check(!overheat && !paid && me.Has(StatusKind::kVentedHeat), "G4 the fuse ends with no form: a vent (no 過熱, no cost)");
        } else {
            Check(overheat || me.Has(StatusKind::kHeat4) || me.Has(StatusKind::kMoltenBody), "G4 in the fire form the fuse still overheats");
        }
    }
}

// ---------------------------------------------------------------- B-small: the burst's op list
void BurstCapacity()
{
    World w;
    MaxNodes nodes;
    nodes.allBranches = true;   // every fusion node (and every other branch)
    essb::Crowd crowd;
    crowd.count = 1 + essb::n5::kCrowdMax;
    for (int k = 1; k < crowd.count; ++k) {
        essb::Member& m = crowd.m[k];
        m.has = true;
        const int a = 1 + (k % 11);
        const int b = 1 + ((k + 4) % 11);
        m.board.mark[a] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
        m.board.mark[b] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
        m.board.bleedDot = essb::Slot{ true, 5.0f, 1.0f, 8.0f };
        m.board.poisonDot = essb::Slot{ true, 5.0f, 1.0f, 8.0f };
        m.board[StatusKind::kStar] = essb::Slot{ true, 2.0f, 0.0f, 30.0f };
        m.body = essb::Body{ 500.0f, 1000.0f, 20.0f, 100.0f, false, false, 200.0f };
        m.pos = { 50.0f * static_cast<float>(k), 0.0f, 0.0f };
        m.magicka = 50.0f;
        m.magickaMax = 100.0f;
    }
    essb::Board me;
    me[StatusKind::kCosmos] = essb::Slot{ true, 10.0f, 0.0f, 10.0f };
    essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
    auto plan = std::make_unique<essb::StatusPlan>();
    const essb::BurstResult r = essb::PlanBurst(*plan, crowd, me, bin, 3, essb::kWind, nodes, w.rng);
    std::printf("NATIVE ANCHORS burst: 24 targets x 2 marks, every node -> %d ops (%d targets, %d marks)\n", plan->count, r.targets, r.marks);
    Check(r.targets == essb::n5::kCrowdMax && r.marks == 2 * essb::n5::kCrowdMax, "B-small: the burst reached every target and mark");
    Check(!plan->overflow && plan->count < essb::kMaxStatusOps, "B-small: the burst's ops fit (" + std::to_string(plan->count) + ")");
    Check(plan->count > 512, "B-small: this burst needs more than the old 512 slots (" + std::to_string(plan->count) + ")");
}

}  // namespace

// ---------------------------------------------------------------- round 27b: review B
void Review27bAnchors()
{
    // N1: 焚天 -- the fire end on member 0 chains to member 1 (also fire-marked, no statuses on either): the chained end's
    // body is the primary's (K × M_mod) and its 爆燃 line joins the carried sum, so the chained end is at most the primary
    // (it was the primary × (1 + the line) again).
    {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kFireSkyfire);
        essb::Crowd crowd;
        crowd.count = 2;
        for (int k = 0; k < 2; ++k) {
            crowd.m[k].has = true;
            crowd.m[k].board.mark[essb::kFire] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
            crowd.m[k].body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
        }
        essb::Board me;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanEnd(*plan, essb::kFire, essb::EndReason::kCut, 1.0f, false, crowd.m[0].board, me, w.in, nodes, w.rng);
        essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        essb::RunBodies(*plan, 0, crowd, me, bin, nodes, w.rng);
        const float primary = DamageOf(*plan, essb::kFire, 0);
        const float chained = DamageOf(*plan, essb::kFire, 1);
        Check(primary > 0.0f && chained > 0.0f && chained <= primary * 1.0001f,
            "B-N1 焚天 on the other (" + std::to_string(chained) + ") must not exceed the primary end (" + std::to_string(primary) + ")");
    }
    // N2: 淬毒's transfer and 毒濺's doses read the open line without 節點倍率: the same at 節點倍率 1 and 5.
    {
        int doses[2] = {};
        int n = 0;
        for (const float scale : { 1.0f, 5.0f }) {
            World w(scale);
            MaxNodes nodes;
            nodes.Add(essb::node::kPoisonSplash);
            essb::Crowd crowd;
            crowd.count = 2;
            crowd.m[0].has = true;
            crowd.m[1].has = true;
            crowd.m[1].pos = { 50.0f, 0.0f, 0.0f };   // within 3 m and 15 m
            essb::Board me;
            auto plan = std::make_unique<essb::StatusPlan>();
            essb::PlanStatusHit(*plan, essb::kPoison, false, crowd.m[0].board, me, w.in, nodes, w.rng, false);
            essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
            essb::RunBodies(*plan, 0, crowd, me, bin, nodes, w.rng);
            doses[n++] = essb::Doses(crowd.m[1].board, essb::PerDose(*w.in.config, w.tuning, nodes));
        }
        Check(doses[0] > 0 && doses[0] == doses[1],
            "B-N2 the open's passed doses at 節點倍率 1 and 5: " + std::to_string(doses[0]) + " / " + std::to_string(doses[1]));
    }
    // N3: the fire source burns in the fire form or in 餘壓; it costs only in the fire form at 白熱.
    {
        essb::Board none;
        essb::Board linger;
        linger[StatusKind::kSourceLinger] = essb::Slot{ true, 1.0f, 0.0f, 2.0f };
        Check(essb::FireSourceBurns(true, none) && essb::FireSourceBurns(false, linger) && !essb::FireSourceBurns(false, none),
            "B-N3 the source burns in the fire form or in 餘壓");
        Check(essb::FireSourceCosts(true, 3) && !essb::FireSourceCosts(false, 4) && !essb::FireSourceCosts(true, 2),
            "B-N3 the source costs only in the fire form at 白熱");
    }
    // N6: a no-form killing blow spends nothing of yours.
    {
        essb::Plan p;
        p.overloadAfter = 3.0f;
        p.overloaded = p.silenced = p.breakUsed = p.consumeEcho = true;
        const essb::Plan c = essb::CorpseHitPlan(p);
        Check(c.overloadAfter < 0.0f && !c.overloaded && !c.silenced && !c.breakUsed && !c.consumeEcho,
            "B-N6 a killing blow's plan spends no overload, no 破式, no 滅法 resolve and keeps the echo");
    }
}

// ---------------------------------------------------------------- 27g: 傷害倍率 (ESSB_BaseDamageMult) covers every damage of ours
float TrueDamageOf(const essb::Plan& p)
{
    float sum = 0.0f;
    for (int i = 0; i < p.count; ++i) {
        if (p.steps[i].cast == essb::Cast::kTrueDamage) {
            sum += p.steps[i].magnitude;
        }
    }
    return sum;
}

void DamageMultAnchors()
{
    const float kMult = 0.8f;   // the 0.27.6 default
    float curse[2] = {};
    float source[2] = {};
    float blade[2] = {};
    float small[2] = {};
    float dispel[2] = {};
    int n = 0;
    for (const float mult : { 1.0f, kMult }) {
        // 死咒: B_max part and the lost-health part (0.27.5 left the lost part out).
        {
            World w;
            w.tuning.baseDamageMult = mult;
            w.in.body = essb::Body{ 200.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
            MaxNodes nodes;
            essb::Board target;
            target[StatusKind::kDeathCurse] = essb::Slot{ true, 1.0f, 3.0f, 3.0f };
            essb::Board me;
            auto plan = std::make_unique<essb::StatusPlan>();
            essb::OnDeathCurseEnd(*plan, 1.0f, target, me, w.in, nodes);
            curse[n] = DamageOf(*plan, essb::kDarkness);
        }
        // 火源: the B_max part and the cost × N part (0.27.5 left the cost part out).
        {
            World w;
            w.tuning.baseDamageMult = mult;
            w.in.self.healthMax = 500.0f;
            MaxNodes nodes;
            essb::Board self;
            self[StatusKind::kSourceLinger] = essb::Slot{ true, 1.0f, 0.0f, 2.0f };
            source[n] = essb::PlanFireSource(self, w.in, nodes).perEnemy;
        }
        // 血刃: the flat part of a blood proc (0.27.5 added it after the multiplier).
        {
            World w;
            w.tuning.baseDamageMult = mult;
            MaxNodes nodes;
            essb::StatusTerms terms;
            terms.flat[essb::kBlood] = 40.0f;
            essb::Attack a;
            a.element = essb::kBlood;
            a.power = true;
            blade[n] = essb::RollProc(essb::kBlood, a, w.config, w.tuning, essb::PlayerFacts{}, essb::TargetFacts{}, nodes, w.rng, terms).magnitude;
        }
        // 小滅法 and 滅法: the no-form true damage (0.27.5: no multiplier at all).
        for (const bool power : { false, true }) {
            World w;
            w.tuning.baseDamageMult = mult;
            MaxNodes nodes;
            essb::Attack a;
            a.power = power;
            essb::PlayerFacts p;
            essb::TargetFacts target;
            target.magicka = 200.0f;
            target.magickaMax = 200.0f;
            essb::Plan plan;
            essb::PlanNoFormHit(plan, a, w.config, w.tuning, p, target, nodes);
            (power ? dispel : small)[n] = TrueDamageOf(plan);
        }
        ++n;
    }
    const auto scaled = [&](const char* what, const float* v) {
        Check(v[0] > 0.0f && Near(v[1], v[0] * kMult, std::max(1e-3, v[0] * 1e-5)),
            std::string("27g 傷害倍率 0.8 scales ") + what + ": " + std::to_string(v[1]) + " vs " + std::to_string(v[0]) + " at 1.0");
    };
    scaled("死咒 (with the lost-health part)", curse);
    scaled("火源 (with the cost part)", source);
    scaled("血刃's flat part with the blood proc", blade);
    scaled("小滅法", small);
    scaled("滅法", dispel);
    essb::Tuning one;
    essb::Tuning low;
    low.baseDamageMult = kMult;
    const float drain[2] = { essb::BleedDrainDamage(3, 0.003f, 500.0f, one), essb::BleedDrainDamage(3, 0.003f, 500.0f, low) };
    Check(Near(drain[0], 4.5f), "27g 放血 3 layers × 0.3% × 500 = 4.5 at 1.0: " + std::to_string(drain[0]));
    scaled("放血", drain);
}

// ---------------------------------------------------------------- round 28: the user's decisions 2026-09-28
int CountOps(const essb::StatusPlan& plan, essb::Op op)
{
    int n = 0;
    for (int i = 0; i < plan.count; ++i) {
        n += plan.ops[i].op == op ? 1 : 0;
    }
    return n;
}

int CountEvents(const essb::StatusPlan& plan, essb::Event event)
{
    int n = 0;
    for (int i = 0; i < plan.count; ++i) {
        n += plan.ops[i].op == essb::Op::kEvent && plan.ops[i].event == event ? 1 : 0;
    }
    return n;
}

essb::Crowd Around5(int members)
{
    essb::Crowd crowd;
    crowd.count = members + 1;   // member 0 (the hit's target) is empty in an advent
    for (int k = 1; k <= members; ++k) {
        crowd.m[k].has = true;
        crowd.m[k].body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
        crowd.m[k].pos = { 30.0f * static_cast<float>(k), 0.0f, 0.0f };   // all within 2 m of you
    }
    return crowd;
}

// A hotkey rotation (every switch opens the 臨: the user's rule) around 5 hostiles, every node at 15 and every branch: after
// the first switch marked them all, no switch cuts a mark (D1) -- no end, no damage without a weapon hit -- and a switch's
// sync gain is the same with 1 target as with 5 (D2: your gains once per switch, not per target).
void RotationAnchors()
{
    const int order[] = { essb::kFire, essb::kFrost, essb::kLightning, essb::kEarth, essb::kWind, essb::kDivine, essb::kPoison,
        essb::kDarkness, essb::kAstral, essb::kFire, essb::kFrost, essb::kLightning };
    int syncGain[2] = {};
    int n = 0;
    for (const int members : { 1, 5 }) {
        World w;
        MaxNodes nodes;
        nodes.allBranches = true;
        essb::Crowd crowd = Around5(members);
        essb::Board me;
        const essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        int damage = 0;
        int ends = 0;
        int maxGain = 0;
        for (std::size_t i = 0; i < std::size(order); ++i) {
            const int before = me.Layers(StatusKind::kSync);
            auto plan = std::make_unique<essb::StatusPlan>();
            essb::PlanAdvent(*plan, crowd, me, bin, order[i], nodes, w.rng);
            maxGain = std::max(maxGain, me.Layers(StatusKind::kSync) - before);
            if (i > 0) {
                damage += CountOps(*plan, essb::Op::kDamage);
                ends += CountEvents(*plan, essb::Event::kEnd);
                Check(CountOps(*plan, essb::Op::kRemoveMark) == 0, "28 D1: switch " + std::to_string(i) + " cut a mark");
            }
            me = essb::Board{};   // the switch starts the sync count again (SwitchWork); the gain is what one switch gives
        }
        Check(damage == 0 && ends == 0, "28 D1: a rotation after the first switch deals no damage and ends nothing (" +
                                            std::to_string(damage) + " damage ops, " + std::to_string(ends) + " ends, " +
                                            std::to_string(members) + " targets)");
        syncGain[n++] = maxGain;
    }
    Check(syncGain[0] > 0 && syncGain[0] == syncGain[1], "28 D2: a switch's sync gain does not grow with the targets (" +
                                                            std::to_string(syncGain[0]) + " with 1, " + std::to_string(syncGain[1]) + " with 5)");
}

// D3: 水臨強化 -- 25% of max magicka × the recovery slider and a cleanse, only with a hostile in the advent's range.
void WaterAdventAnchors()
{
    for (const int members : { 0, 1 }) {
        World w;
        w.tuning.multRecovery = 2.0f;
        MaxNodes nodes;
        nodes.Add(essb::node::kWaterAdventPlus);
        essb::Crowd crowd = Around5(members);
        essb::Board me;
        const essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 10.0f, 200.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanAdvent(*plan, crowd, me, bin, essb::kWater, nodes, w.rng);
        float restored = 0.0f;
        for (int i = 0; i < plan->count; ++i) {
            if (plan->ops[i].op == essb::Op::kRestoreMagicka) {
                restored += plan->ops[i].magnitude;
            }
        }
        const bool cleansed = CountEvents(*plan, essb::Event::kCleanse) > 0;
        if (members == 0) {
            Check(restored == 0.0f && !cleansed, "28 D3: no hostile in range -- no magicka, no cleanse");
        } else {
            Check(Near(restored, 200.0f * 0.25f * 2.0f) && cleansed, "28 D3: 25% of 200 × recovery 2 = 100 and a cleanse (" +
                                                                    std::to_string(restored) + ")");
        }
    }
}

// D6: a burst settles a mark the fire source put on (flag n3::kMarkSourced) at half the fusion damage of a hit's mark.
void SourcedBurstAnchors()
{
    float fire[2] = {};
    int n = 0;
    for (const int flags : { 0, essb::n3::kMarkSourced }) {
        World w;
        MaxNodes nodes;
        essb::Crowd crowd;
        crowd.count = 2;
        crowd.m[1].has = true;
        crowd.m[1].body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
        crowd.m[1].pos = { 100.0f, 0.0f, 0.0f };
        crowd.m[1].board.mark[essb::kFire] = essb::Slot{ true, static_cast<float>(flags), 1.0f, 8.0f };
        essb::Board me;
        const essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        (void)essb::PlanBurst(*plan, crowd, me, bin, 0, essb::kFire, nodes, w.rng);
        fire[n++] = DamageOf(*plan, essb::kFire, 1);
    }
    Check(fire[0] > 0.0f && Near(fire[1], fire[0] * 0.5f, std::max(1e-3, fire[0] * 1e-4)),
        "28 D6: the source's mark bursts at half (" + std::to_string(fire[1]) + " vs " + std::to_string(fire[0]) + ")");
}

// Round 28 (the user's fixes): 死咒's lost-health part ×0.5 on a boss; the guide is itself (× nothing of the end); 三重奏
// rests 10 s after it fires.
void FixAnchors()
{
    {
        World w;
        w.in.body = essb::Body{ 200.0f, 1000.0f, 100.0f, 100.0f, true, false, 100.0f };   // a boss
        MaxNodes nodes;
        essb::Board target;
        target[StatusKind::kDeathCurse] = essb::Slot{ true, 1.0f, 3.0f, 3.0f };
        essb::Board me;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::OnDeathCurseEnd(*plan, 1.0f, target, me, w.in, nodes);
        // 120 (the B_max part) + 420 × 0.5 = 330
        Check(Near(DamageOf(*plan, essb::kDarkness), 330.0f), "28 死咒 on a boss: " + std::to_string(DamageOf(*plan, essb::kDarkness)) + " != 330");
    }
    {
        float guide[2] = {};
        int n = 0;
        for (const float mult : { 1.0f, 2.0f }) {
            World w;
            MaxNodes nodes;
            essb::Board target;
            target.mark[essb::kWater] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
            essb::Board me;
            auto plan = std::make_unique<essb::StatusPlan>();
            essb::PlanEnd(*plan, essb::kWater, essb::EndReason::kCut, mult, false, target, me, w.in, nodes, w.rng);
            guide[n++] = target[StatusKind::kGuided].magnitude;
        }
        Check(guide[0] > 1.0f && Near(guide[0], guide[1]), "28 the guide is itself: " + std::to_string(guide[0]) + " / " + std::to_string(guide[1]));
    }
    {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kCommonTrio);
        essb::Board me;
        me[StatusKind::kTrio1] = essb::Slot{ true, 1.0f, 1.0f, 10.0f };
        me[StatusKind::kTrio2] = essb::Slot{ true, 1.0f, 1.0f, 10.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        int flags = 0;
        const float first = essb::res::EndExtra(*plan, essb::kLightning, 0, me, w.in, nodes, flags);
        Check(Near(first, 3.0f) && me.Has(StatusKind::kTrioCooldown), "28 三重奏 fires and rests");
        me[StatusKind::kTrio4] = essb::Slot{ true, 1.0f, 1.0f, 10.0f };
        me[StatusKind::kTrio5] = essb::Slot{ true, 1.0f, 1.0f, 10.0f };
        const float second = essb::res::EndExtra(*plan, essb::kDivine, 0, me, w.in, nodes, flags);
        Check(Near(second, 1.0f), "28 三重奏 does not fire again inside its 10 s rest (" + std::to_string(second) + ")");
    }
}

// ---------------------------------------------------------------- round 28b: the user's rulings 2026-09-28
// F5 印潮: the first hit after a switch opened its mark (member 0) -- up to 2 other hostiles within 15 m of it carrying no
// mark of ours get the new element's mark, nearest first; a marked one is skipped (no switch), one at 16 m is out.
void SurgeAnchors()
{
    struct Row {
        const char* name;
        std::vector<std::pair<float, int>> others;   // (x in game units from member 0 at 0, the element of a mark it carries or 0)
        std::vector<int> want;                       // the members that must come out with the water mark
    };
    const float m16 = 16.0f * 70.0f;
    const Row rows[] = {
        { "0 unmarked -> 0", { { 200.0f, essb::kFire }, { 300.0f, essb::kFrost } }, {} },
        { "3 unmarked in range -> the 2 nearest", { { 300.0f, 0 }, { 100.0f, 0 }, { 200.0f, 0 } }, { 2, 3 } },
        { "unmarked at 16 m -> excluded", { { m16, 0 }, { 150.0f, 0 } }, { 2 } },
        { "already marked -> excluded (no switch)", { { 50.0f, essb::kFire }, { 120.0f, 0 }, { 60.0f, essb::kWater } }, { 2 } },
    };
    for (const Row& row : rows) {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kCommonSurge);
        essb::Crowd crowd;
        crowd.count = 1 + static_cast<int>(row.others.size());
        crowd.m[0].has = true;
        crowd.m[0].body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
        crowd.m[0].board.mark[essb::kWater] = essb::Slot{ true, 0.0f, 0.0f, 15.0f };   // the hit's own open
        for (std::size_t i = 0; i < row.others.size(); ++i) {
            essb::Member& m = crowd.m[i + 1];
            m.has = true;
            m.body = essb::Body{ 1000.0f, 1000.0f, 100.0f, 100.0f, false, false, 100.0f };
            m.pos = { row.others[i].first, 0.0f, 0.0f };
            if (row.others[i].second != 0) {
                m.board.mark[row.others[i].second] = essb::Slot{ true, 0.0f, 1.0f, 15.0f };
            }
        }
        const essb::Crowd before = crowd;
        essb::Board me;
        const essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanSurge(*plan, crowd, me, bin, essb::kWater, nodes, w.rng);
        for (int k = 1; k < crowd.count; ++k) {
            const bool wanted = std::find(row.want.begin(), row.want.end(), k) != row.want.end();
            const bool had = before.m[k].board.mark[essb::kWater].has;
            const bool opened = !had && crowd.m[k].board.mark[essb::kWater].has;
            Check(opened == wanted, std::string("28b F5 印潮 ") + row.name + ": member " + std::to_string(k) +
                                        (wanted ? " not marked" : " marked"));
            for (int e = essb::kFire; e <= essb::kAstral; ++e) {
                Check(!before.m[k].board.mark[e].has || crowd.m[k].board.mark[e].has,
                    std::string("28b F5 印潮 ") + row.name + ": member " + std::to_string(k) + " lost a mark (a switch)");
            }
        }
        Check(CountOps(*plan, essb::Op::kRemoveMark) == 0, std::string("28b F5 印潮 ") + row.name + ": a mark was removed");
        Check(CountEvents(*plan, essb::Event::kOpen) == static_cast<int>(row.want.size()),
            std::string("28b F5 印潮 ") + row.name + ": " + std::to_string(CountEvents(*plan, essb::Event::kOpen)) + " opens");
    }
    {   // without the branch nothing happens
        World w;
        MaxNodes nodes;
        essb::Crowd crowd = Around5(3);
        essb::Board me;
        const essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 100.0f, 100.0f };
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanSurge(*plan, crowd, me, bin, essb::kWater, nodes, w.rng);
        Check(plan->count == 0, "28b F5 印潮 without the branch plans nothing");
    }
}

// F7 水臨強化's 10 s cooldown (running clock): fires at 0 s, not at 5 s (the L4 case), again at 10.5 s.
void WaterAdventCooldownAnchors()
{
    essb::AdventCooldown cooldown;
    const std::uint64_t at[] = { 0, 5000, 10500 };
    const bool fires[] = { true, false, true };
    for (int i = 0; i < 3; ++i) {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kWaterAdventPlus);
        essb::Crowd crowd = Around5(1);
        essb::Board me;
        essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 10.0f, 200.0f };
        bin.waterAdventReady = cooldown.Ready(at[i]);
        auto plan = std::make_unique<essb::StatusPlan>();
        const essb::AdventOutcome out = essb::PlanAdvent(*plan, crowd, me, bin, essb::kWater, nodes, w.rng);
        if (out.waterFired) {
            cooldown.Fired(at[i]);
        }
        const bool restored = CountOps(*plan, essb::Op::kRestoreMagicka) > 0;
        const bool cleansed = CountEvents(*plan, essb::Event::kCleanse) > 0;
        const std::string when = std::to_string(at[i]) + " ms";
        Check(out.waterFired == fires[i] && restored == fires[i] && cleansed == fires[i],
            "28b F7 水臨強化 at " + when + (fires[i] ? " did not fire" : " fired inside its 10 s"));
        Check(out.waterCooling == !fires[i], "28b F7 水臨強化 at " + when + ": the cooling flag (the L4 line)");
        if (!fires[i]) {
            Check(Near(cooldown.Left(at[i]), 5.0f), "28b F7 left at 5 s = 5 s: " + std::to_string(cooldown.Left(at[i])));
            // nothing of the branch: the same plan as without 水臨強化 (the water 臨's own open stays)
            World bare;
            MaxNodes none;
            essb::Crowd crowd2 = Around5(1);
            essb::Board me2;
            essb::BodyInputs bin2{ &bare.in, false, 100.0f, 100.0f, 10.0f, 200.0f };
            auto plan2 = std::make_unique<essb::StatusPlan>();
            (void)essb::PlanAdvent(*plan2, crowd2, me2, bin2, essb::kWater, none, bare.rng);
            Check(plan->count == plan2->count, "28b F7 水臨強化 cooling plans what no 水臨強化 plans (" + std::to_string(plan->count) +
                                                   " vs " + std::to_string(plan2->count) + " ops)");
        }
    }
    essb::AdventCooldown other;   // the other advents: no cooldown -- 冰臨強化 at 0 s and 5 s both slow
    for (const std::uint64_t now : { std::uint64_t{ 0 }, std::uint64_t{ 5000 } }) {
        World w;
        MaxNodes nodes;
        nodes.Add(essb::node::kFrostAdventPlus);
        essb::Crowd crowd = Around5(1);
        essb::Board me;
        essb::BodyInputs bin{ &w.in, false, 100.0f, 100.0f, 10.0f, 200.0f };
        bin.waterAdventReady = other.Ready(now);
        auto plan = std::make_unique<essb::StatusPlan>();
        const essb::AdventOutcome out = essb::PlanAdvent(*plan, crowd, me, bin, essb::kFrost, nodes, w.rng);
        Check(!out.waterFired && !out.waterCooling && CountOps(*plan, essb::Op::kSlow) > 0,
            "28b F7 冰臨強化 keeps no cooldown (" + std::to_string(now) + " ms)");
    }
}

int main()
{
    try {
        ShatterAnchors();
        JudgeAnchors();
        DeathCurseAnchors();
        EndBodyAnchors();
        CatalyseAnchors();
        OpenCountAnchors();
        MeltdownAnchors();
        BurstCapacity();
        Review27bAnchors();
        DamageMultAnchors();
        RotationAnchors();
        WaterAdventAnchors();
        SourcedBurstAnchors();
        FixAnchors();
        SurgeAnchors();
        WaterAdventCooldownAnchors();
        std::printf("NATIVE ANCHORS ok: %d checks (G1 sums and percentage effects at level 100 / 節點倍率 5 / every line, G3 counts, "
                    "G4 the formless fuse, the 24-target burst)\n",
            checks);
        return 0;
    } catch (const std::exception& e) {
        std::printf("NATIVE ANCHORS FAILED: %s\n", e.what());
        return 1;
    }
}
