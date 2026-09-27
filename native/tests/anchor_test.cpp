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

#include <cmath>
#include <cstdio>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>

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
        std::printf("NATIVE ANCHORS ok: %d checks (G1 sums and percentage effects at level 100 / 節點倍率 5 / every line, G3 counts, "
                    "G4 the formless fuse, the 24-target burst)\n",
            checks);
        return 0;
    } catch (const std::exception& e) {
        std::printf("NATIVE ANCHORS FAILED: %s\n", e.what());
        return 1;
    }
}
