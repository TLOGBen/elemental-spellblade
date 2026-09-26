// Offline tests of the engine-free hit handler (HitPipeline.h, EngineFacts.h, HitMath.h, Selection.h and the
// generated ManifestData.h). Each group states what it proves; counts are printed and recorded in
// build/fix20-native-test.log by build/fix19_native.py.
//   A0 hand-computed anchors: a few hits worked out by hand from the v0.4 formulas (arithmetic in comments)
//   A  magnitude table: every scenario of build/fix20-magnitude-table.json (inputs, scripted random draws)
//      -> the ordered casts and magnitudes build/fix20_reference.py computes from the v0.4 text
//   B  wiring: engine answers -> planner inputs with a mocked engine: perk FormIDs and the 4-probe rank
//      search, the no-form route suppression, GLOB -> tuning field, hit flags -> attack, raw target facts,
//      cast -> spell record; expected FormIDs come from build/fix20-wiring.json (the generator's records,
//      checked against the built ESP), not from the code under test
//   C  filter: every hit-fact combination the engine can report -> verdict, vs a line-by-line
//      transliteration of the Papyrus OnWeaponHit gates (no-form hits included since round 20)
//   D  randomness: 100 000-draw distributions of the production generator (uniform B, 1..25 faces,
//      best-of-7, 5% chance) and 20 000 planned lightning hits (faces and crit rate), each within 5 sigma
#include "EngineFacts.h"
#include "HitPipeline.h"
#include "Selection.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

using json = nlohmann::json;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
}

bool Near(double actual, double expected)
{
    return std::abs(actual - expected) <= 1e-4 * std::max(1.0, std::abs(expected));
}

// ---------------------------------------------------------------- mocks shared by A0, A and D

struct MapNodes {
    std::map<std::tuple<int, int, int>, int> ranks;
    std::set<std::tuple<int, int, int, int>> branches;

    int Rank(const essb::NodeId& id) const
    {
        const auto it = ranks.find({ id.tree, id.route, id.tier });
        return it == ranks.end() ? 0 : it->second;
    }

    bool Has(const essb::BranchId& id) const
    {
        return branches.contains({ id.tree, id.route, id.tier, id.index });
    }
};

struct Draw {
    std::string kind;
    double lo = 0;
    double hi = 0;
    double value = 0;  // real: u in [0, 1]; int: the face; chance: probability
    bool hit = false;  // chance outcome
};

// Replays the scenario's draws in order and checks the planner asks for exactly those.
struct ScriptedRng {
    std::vector<Draw> draws;
    std::size_t next = 0;
    std::string scenario;

    const Draw& Take(const char* kind)
    {
        Check(next < draws.size(), scenario + ": planner drew more random values than scripted");
        const Draw& d = draws[next++];
        Check(d.kind == kind, scenario + ": planner drew " + kind + ", script has " + d.kind);
        return d;
    }

    int Int(int lo, int hi)
    {
        const Draw& d = Take("int");
        Check(d.lo == lo && d.hi == hi, scenario + ": integer range differs");
        return static_cast<int>(d.value);
    }

    float Real(float lo, float hi)
    {
        const Draw& d = Take("real");
        Check(Near(lo, d.lo) && Near(hi, d.hi), scenario + ": real range differs");
        return lo + (hi - lo) * static_cast<float>(d.value);
    }

    bool Chance(float probability)
    {
        const Draw& d = Take("chance");
        Check(Near(probability, d.value), scenario + ": crit probability differs");
        return d.hit;
    }
};

const std::map<std::string, essb::Cast> kCastNames = {
    { "kProc", essb::Cast::kProc },
    { "kDrainMagicka", essb::Cast::kDrainMagicka },
    { "kDrainStamina", essb::Cast::kDrainStamina },
    { "kTrueDamage", essb::Cast::kTrueDamage },
    { "kSoakSlow", essb::Cast::kSoakSlow },
    { "kDispelMark", essb::Cast::kDispelMark },
    { "kSilence", essb::Cast::kSilence },
    { "kHeal", essb::Cast::kHeal },
    { "kRestoreMagicka", essb::Cast::kRestoreMagicka },
    { "kRestoreStamina", essb::Cast::kRestoreStamina },
    { "kSpendMagicka", essb::Cast::kSpendMagicka },
    { "kBloodGuard", essb::Cast::kBloodGuard },
    { "kHushSpent", essb::Cast::kHushSpent },
};

// Map key of a node as the generated constants name it (tests never spell a slot themselves).
std::tuple<int, int, int> Key(const essb::NodeId& id)
{
    return { id.tree, id.route, id.tier };
}

std::tuple<int, int, int, int> Key(const essb::BranchId& id)
{
    return { id.tree, id.route, id.tier, id.index };
}

struct Inputs {
    essb::Attack attack;
    essb::Tuning tuning;
    essb::PlayerFacts player;
    essb::TargetFacts target;
    MapNodes nodes;
};

Inputs Bare(int element)
{
    Inputs in;
    in.attack.element = element;
    in.tuning.level.fill(1.0f);
    return in;
}

// ---------------------------------------------------------------- A0

int GroupA0()
{
    const essb::Config config = essb::MakeConfig();
    int cases = 0;
    auto run = [&](const Inputs& in, std::vector<Draw> draws) {
        ScriptedRng rng{ std::move(draws), 0, "A0" };
        const essb::Plan plan = essb::PlanHit(in.attack, config, in.tuning, in.player, in.target, in.nodes, rng);
        Check(rng.next == rng.draws.size(), "A0: scripted draws left over");
        ++cases;
        return plan;
    };
    // Fire, normal, level 1, no nodes, B = 11 (u = 0.5 of 10..12): 11 x R 1 x G 1.05 x 1 = 11.55.
    {
        const essb::Plan p = run(Bare(essb::kFire), { { "real", 10, 12, 0.5 } });
        Check(p.count == 1 && p.steps[0].cast == essb::Cast::kProc && Near(p.steps[0].magnitude, 11.55), "A0 fire");
    }
    // Lightning power attack, crit, face 25: 25 x 1.5 x 1.05 x 2.5 = 98.4375; drain 50% = 49.21875.
    {
        Inputs in = Bare(essb::kLightning);
        in.attack.power = true;
        const essb::Plan p = run(in, { { "int", 1, 25, 25 }, { "chance", 0, 0, 0.05, true } });
        Check(p.crit && p.count == 2 && Near(p.steps[0].magnitude, 98.4375), "A0 lightning crit");
        Check(p.steps[1].cast == essb::Cast::kDrainMagicka && Near(p.steps[1].magnitude, 49.21875), "A0 lightning drain");
    }
    // Blood at 50% health, blood mark, B = 9: curve 0.8 + (0.5 - 0.3) / 0.4 x 0.3 = 0.95 -> 9 x 1.05 x 0.95 = 8.9775;
    // leech ratio 0.35 + (0.5 - 0.3) / 0.4 x (0.15 - 0.35) = 0.25 -> heal 8.9775 x 0.25 = 2.244375.
    {
        Inputs in = Bare(essb::kBlood);
        in.player.health = 50.0f;
        in.target.bloodMark = true;
        const essb::Plan p = run(in, { { "real", 8, 10, 0.5 } });
        Check(p.count == 2 && Near(p.steps[0].magnitude, 8.9775), "A0 blood curve");
        Check(p.steps[1].cast == essb::Cast::kHeal && Near(p.steps[1].magnitude, 2.244375), "A0 blood leech");
    }
    // Divine against undead, daytime outdoors, B = 9: 9 x 1.05 x 1.2 (day) x 1.5 (undead) = 17.01.
    {
        Inputs in = Bare(essb::kDivine);
        in.target.undeadOrDaedra = true;
        const essb::Plan p = run(in, { { "real", 8, 10, 0.5 } });
        Check(p.count == 1 && Near(p.steps[0].magnitude, 17.01), "A0 divine undead");
    }
    // Fire, adept main 5 points, node scale 3: 1 + 5 x 1% x 3 = 1.15 -> B 10 x 1.05 x 1.15 = 12.075.
    {
        Inputs in = Bare(essb::kFire);
        in.nodes.ranks[Key(essb::node::kProcAdept[essb::kFire])] = 5;
        const essb::Plan p = run(in, { { "real", 10, 12, 0.0 } });
        Check(Near(p.steps[0].magnitude, 12.075), "A0 fire adept");
    }
    // No form, power, level 1, you 100/100 magicka, target 50/50:
    //   baseline 5 x 1.05 x 1.5 = 7.875; siphon 10 x 1.05 x 1.5 = 15.75 (target 34.25, you stay at 100);
    //   X = 15% x 100 = 15, Y = min(34.25, 15) = 15, true damage 30; dispel mark; target keeps 19.25: no silence.
    {
        Inputs in = Bare(essb::kNoElement);
        in.attack.power = true;
        in.target.magicka = 50.0f;
        in.target.magickaMax = 50.0f;
        const essb::Plan p = run(in, {});
        const std::vector<std::pair<essb::Cast, double>> expected = { { essb::Cast::kTrueDamage, 7.875 },
            { essb::Cast::kDrainMagicka, 15.75 }, { essb::Cast::kRestoreMagicka, 15.75 }, { essb::Cast::kSpendMagicka, 15.0 },
            { essb::Cast::kDrainMagicka, 15.0 }, { essb::Cast::kTrueDamage, 30.0 }, { essb::Cast::kDispelMark, 0.0 } };
        Check(p.count == static_cast<int>(expected.size()), "A0 dispel cast count");
        for (std::size_t i = 0; i < expected.size(); ++i) {
            Check(p.steps[i].cast == expected[i].first && Near(p.steps[i].magnitude, expected[i].second), "A0 dispel step " + std::to_string(i));
        }
    }
    // Round 21. No form, normal hit, level 1, 吸魔量 10 points and 滅法倍率 5 points, target 100/100, you 100/100:
    //   baseline 5 x 1.05 = 5.25; siphon 10 x 1.05 x (1 + 10 x 5%) = 15.75; small dispel burns 5 x 1.05 = 5.25,
    //   true damage 5.25 x (1 + 5 x 2%) = 5.775 (neither line takes the node scale).
    {
        Inputs in = Bare(essb::kNoElement);
        in.target.magicka = 100.0f;
        in.target.magickaMax = 100.0f;
        in.nodes.ranks[Key(essb::node::kNoFormSiphonAmount)] = 10;
        in.nodes.ranks[Key(essb::node::kNoFormDispelRate)] = 5;
        const essb::Plan p = run(in, {});
        const std::vector<std::pair<essb::Cast, double>> expected = { { essb::Cast::kTrueDamage, 5.25 },
            { essb::Cast::kDrainMagicka, 15.75 }, { essb::Cast::kRestoreMagicka, 15.75 }, { essb::Cast::kDrainMagicka, 5.25 },
            { essb::Cast::kTrueDamage, 5.775 } };
        Check(p.count == static_cast<int>(expected.size()), "A0 siphon amount / dispel rate cast count");
        for (std::size_t i = 0; i < expected.size(); ++i) {
            Check(p.steps[i].cast == expected[i].first && Near(p.steps[i].magnitude, expected[i].second), "A0 R5 step " + std::to_string(i));
        }
    }
    // Round 21. 反擊 window + 反擊 owned, same bare hit: siphon 10 x 1.05 x 2 = 21, and the window is used up.
    {
        Inputs in = Bare(essb::kNoElement);
        in.target.magicka = 100.0f;
        in.target.magickaMax = 100.0f;
        in.player.riposteWindow = true;
        in.nodes.branches.insert(Key(essb::node::kNoFormRiposte));
        const essb::Plan p = run(in, {});
        Check(p.consumeRiposte && p.steps[1].cast == essb::Cast::kDrainMagicka && Near(p.steps[1].magnitude, 21.0), "A0 riposte");
    }
    // Round 21. 寂滅: power hit, target 50/50 with 3 layers of 寂: X = 15, Y = 15, true damage (15 + 15) x (1.0 + 0.5) = 45,
    //   then the 10-second "spent" marker.
    {
        Inputs in = Bare(essb::kNoElement);
        in.attack.power = true;
        in.target.magicka = 50.0f;
        in.target.magickaMax = 50.0f;
        in.target.hushLayers = 3;
        in.nodes.branches.insert(Key(essb::node::kNoFormHushBreak));
        const essb::Plan p = run(in, {});
        Check(p.count == 8 && p.steps[5].cast == essb::Cast::kTrueDamage && Near(p.steps[5].magnitude, 45.0), "A0 hush break damage");
        Check(p.steps[6].cast == essb::Cast::kDispelMark && p.steps[7].cast == essb::Cast::kHushSpent, "A0 hush spent marker");
    }
    // Round 21. Fire in the rain, water sustain novice line 15 points: 10 + 15 x 0.3 = 14.5 -> 15 s soaked, slow 15%.
    {
        Inputs in = Bare(essb::kFire);
        in.tuning.envWet = true;
        in.nodes.ranks[Key(essb::node::kWaterSoakDuration)] = 15;
        const essb::Plan p = run(in, { { "real", 10, 12, 0.5 } });
        Check(p.count == 2 && p.steps[1].cast == essb::Cast::kSoakSlow && Near(p.steps[1].magnitude, 15.0) && p.steps[1].seconds == 15, "A0 soak duration");
    }
    return cases;
}

// ---------------------------------------------------------------- A

Inputs FromScenario(const json& row)
{
    const json& s = row.at("state");
    Inputs in;
    in.attack.element = s.at("element");
    in.attack.power = s.at("power");
    in.attack.sneakAttack = s.at("sneak");
    in.attack.leftHand = s.at("left");
    essb::Tuning& t = in.tuning;
    t.level.fill(1.0f);
    for (const auto& level : row.at("levels")) {
        t.level[level.at(0).get<int>()] = level.at(1).get<float>();
    }
    t.syncStage = s.at("stage");
    t.baseDamageMult = s.at("base_damage_mult");
    t.nodeScale = s.at("node_scale");
    t.multDrain = s.at("mult_drain");
    t.multRecovery = s.at("mult_recovery");
    t.multDuration = s.at("mult_duration");
    t.slowCapPct = s.at("slow_cap");
    t.wetSlowPct = s.at("wet_slow");
    t.waterClearStamina = s.at("water_clear");
    t.seizeMaxPct = s.at("seize_pct");
    t.envWet = s.at("wet");
    t.envNight = s.at("night");
    t.prevElement = s.at("prev");
    t.twinElement = s.at("twin");
    essb::PlayerFacts& p = in.player;
    p.health = s.at("hp");
    p.healthPermanent = s.at("hp_perm");
    p.healthMax = s.at("hp_max");
    p.magicka = s.at("mp");
    p.magickaMax = s.at("mp_max");
    p.interior = s.at("interior");
    p.echoPending = s.at("echo_pending");
    p.twinWindow = s.at("twin_window");
    p.bloodGuard = s.at("guard");
    p.riposteWindow = s.at("riposte");
    essb::TargetFacts& g = in.target;
    g.undeadOrDaedra = s.at("undead");
    g.necromancer = s.at("necro");
    g.bloodMark = s.at("blood_mark");
    g.silenced = s.at("silenced");
    g.spellUser = s.at("spell_user");
    g.vip = s.at("vip");
    g.magicka = s.at("t_mp");
    g.magickaMax = s.at("t_mp_max");
    g.hushLayers = s.at("hush");
    g.hushSpent = s.at("hush_spent");
    for (const auto& r : row.at("ranks")) {
        in.nodes.ranks[{ r.at(0).get<int>(), r.at(1).get<int>(), r.at(2).get<int>() }] = r.at(3).get<int>();
    }
    for (const auto& b : row.at("branches")) {
        in.nodes.branches.insert({ b.at(0).get<int>(), b.at(1).get<int>(), b.at(2).get<int>(), b.at(3).get<int>() });
    }
    return in;
}

std::vector<Draw> DrawsOf(const json& row)
{
    std::vector<Draw> draws;
    for (const auto& d : row.at("draws")) {
        Draw draw;
        draw.kind = d.at(0);
        if (draw.kind == "chance") {
            draw.value = d.at(1);
            draw.hit = d.at(2);
        } else {
            draw.lo = d.at(1);
            draw.hi = d.at(2);
            draw.value = d.at(3);
        }
        draws.push_back(draw);
    }
    return draws;
}

int GroupA(const json& table)
{
    // The table must describe the production settings (compiled into ManifestData.h).
    const essb::Config config = essb::MakeConfig();
    const auto& damage = table.at("config").at("damage");
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        Check(Near(config.damage[e][0], damage.at(e - 1).at(0)) && Near(config.damage[e][1], damage.at(e - 1).at(1)), "A: damage ranges differ from settings");
    }
    Check(Near(config.noFormBaseTrue, table.at("config").at("noform_base_true")), "A: noform_base_true differs");
    int cases = 0;
    std::set<essb::Cast> seen;
    for (const auto& row : table.at("scenarios")) {
        const std::string name = row.at("name");
        const Inputs in = FromScenario(row);
        ScriptedRng rng{ DrawsOf(row), 0, name };
        const essb::Plan plan = essb::PlanHit(in.attack, config, in.tuning, in.player, in.target, in.nodes, rng);
        Check(rng.next == rng.draws.size(), name + ": scripted draws left over");
        const json& expect = row.at("expect");
        const auto& casts = expect.at("casts");
        Check(plan.count == static_cast<int>(casts.size()), name + ": cast count " + std::to_string(plan.count) + " != " + std::to_string(casts.size()));
        for (int i = 0; i < plan.count; ++i) {
            const essb::CastStep& step = plan.steps[i];
            const json& c = casts.at(i);
            const std::string label = name + " step " + std::to_string(i);
            Check(step.cast == kCastNames.at(c.at(0).get<std::string>()), label + ": cast kind");
            Check(Near(step.magnitude, c.at(1).get<double>()), label + ": magnitude " + std::to_string(step.magnitude) + " != " + std::to_string(c.at(1).get<double>()));
            if (step.cast == essb::Cast::kProc) {
                Check(step.element == c.at(2).get<int>() && step.power == c.at(3).get<bool>(), label + ": proc spell");
            }
            if (step.cast == essb::Cast::kSilence || step.cast == essb::Cast::kSoakSlow) {
                Check(step.seconds == c.at(4).get<int>(), label + ": seconds");
            }
            seen.insert(step.cast);
        }
        Check(plan.consumeEcho == expect.at("consume_echo").get<bool>(), name + ": echo consumption");
        Check(plan.consumeRiposte == expect.at("consume_riposte").get<bool>(), name + ": riposte consumption");
        Check(plan.crit == expect.at("crit").get<bool>(), name + ": crit");
        Check(Near(plan.magnitude, expect.at("magnitude").get<double>()), name + ": reported magnitude");
        ++cases;
    }
    Check(seen.size() == kCastNames.size(), "A: the table does not exercise every cast kind");
    return cases;
}

// ---------------------------------------------------------------- B

struct PerkEngine {
    std::set<std::uint32_t> owned;
    mutable std::vector<std::uint32_t> asked;

    bool operator()(std::uint32_t id) const
    {
        asked.push_back(id);
        return owned.contains(id);
    }
};

essb::NodeId NodeOf(const json& slot)
{
    return { slot.at(0).get<int>(), slot.at(1).get<int>(), slot.at(2).get<int>() };
}

essb::BranchId BranchOf(const json& slot)
{
    return { slot.at(0).get<int>(), slot.at(1).get<int>(), slot.at(2).get<int>(), slot.at(3).get<int>() };
}

int GroupB(const json& wiring)
{
    int cases = 0;
    // B1: main lines - owning ranks 1..k of the chain reads as rank k, with at most four probes, all inside the chain.
    for (const auto& [name, ids] : wiring.at("main_perks").items()) {
        const essb::NodeId id = NodeOf(wiring.at("slots").at(name));
        const std::vector<std::uint32_t> chain = ids.get<std::vector<std::uint32_t>>();
        Check(chain.size() == static_cast<std::size_t>(essb::kMainMaxRank), name + ": chain length");
        for (int k = 0; k <= essb::kMainMaxRank; ++k) {
            PerkEngine engine;
            engine.owned.insert(chain.begin(), chain.begin() + k);
            const essb::PerkNodes nodes(std::cref(engine), false);
            Check(nodes.Rank(id) == k, name + ": rank " + std::to_string(k));
            Check(engine.asked.size() <= 4, name + ": more than four HasPerk probes");
            for (const auto asked : engine.asked) {
                Check(std::find(chain.begin(), chain.end(), asked) != chain.end(), name + ": probed a FormID outside its chain");
            }
            const std::size_t before = engine.asked.size();
            Check(nodes.Rank(id) == k && engine.asked.size() == before, name + ": rank not cached within the hit");
            ++cases;
        }
    }
    // B2: branches - one probe of the branch's own FormID.
    for (const auto& [name, fid] : wiring.at("branch_perks").items()) {
        const essb::BranchId id = BranchOf(wiring.at("slots").at(name));
        for (const bool owned : { false, true }) {
            PerkEngine engine;
            if (owned) {
                engine.owned.insert(fid.get<std::uint32_t>());
            }
            const essb::PerkNodes nodes(std::cref(engine), false);
            Check(nodes.Has(id) == owned && engine.asked == std::vector<std::uint32_t>{ fid.get<std::uint32_t>() }, name + ": branch probe");
            ++cases;
        }
    }
    // B3: the no-form tree's routes 0/1 read as nothing while a form is active (ESSBController.Rank / Br), without probing;
    // without a form the same slots are read. The mock owns every FormID the wiring lists.
    {
        PerkEngine all;
        for (const auto& [name, ids] : wiring.at("main_perks").items()) {
            for (const auto fid : ids) {
                all.owned.insert(fid.get<std::uint32_t>());
            }
        }
        for (const auto& [name, fid] : wiring.at("branch_perks").items()) {
            all.owned.insert(fid.get<std::uint32_t>());
        }
        for (const auto& [name, slot] : wiring.at("slots").items()) {
            if (slot.at(0).get<int>() != essb::kNoFormTree) {
                continue;
            }
            const bool branch = slot.size() == 4;
            const bool suppressed = slot.at(1).get<int>() < 2;
            all.asked.clear();
            const essb::PerkNodes active(std::cref(all), true);
            const int value = branch ? int(active.Has(BranchOf(slot))) : active.Rank(NodeOf(slot));
            Check(suppressed ? value == 0 && all.asked.empty() : value > 0, name + ": no-form suppression while a form is active");
            const essb::PerkNodes inactive(std::cref(all), false);
            const int free = branch ? int(inactive.Has(BranchOf(slot))) : inactive.Rank(NodeOf(slot));
            Check(free > 0, name + ": readable without a form");
            ++cases;
        }
    }
    // B4: every tuning field reads the GLOB the generator says; nothing else is asked.
    {
        const json& g = wiring.at("globals");
        std::map<std::uint32_t, float> values;
        float next = 3.0f;
        for (const auto& [field, fid] : g.at("tuning").items()) {
            values[fid.get<std::uint32_t>()] = next;
            next += 1.0f;
        }
        const auto levels = g.at("levels").get<std::vector<std::uint32_t>>();
        Check(levels.size() == static_cast<std::size_t>(essb::kTreeCount), "B4: level globals");
        for (const auto fid : levels) {
            values[fid] = next;
            next += 1.0f;
        }
        const std::uint32_t wet = g.at("tuning").at("envWet");
        const std::uint32_t night = g.at("tuning").at("envNight");
        values[wet] = 1.0f;
        values[night] = 0.0f;
        std::set<std::uint32_t> asked;
        const essb::Tuning t = essb::ReadTuning([&](std::uint32_t id) {
            Check(values.contains(id), "B4: ReadTuning asked a GLOB the wiring does not list");
            asked.insert(id);
            return values.at(id);
        });
        Check(asked.size() == values.size(), "B4: a listed GLOB was never read");
        auto at = [&](const char* field) {
            return values.at(g.at("tuning").at(field).get<std::uint32_t>());
        };
        const std::vector<std::pair<const char*, float>> fields = { { "baseDamageMult", t.baseDamageMult }, { "nodeScale", t.nodeScale },
            { "multDrain", t.multDrain }, { "multRecovery", t.multRecovery }, { "multDuration", t.multDuration },
            { "slowCapPct", t.slowCapPct }, { "wetSlowPct", t.wetSlowPct }, { "waterClearStamina", t.waterClearStamina },
            { "seizeMaxPct", t.seizeMaxPct }, { "syncStage", float(t.syncStage) }, { "prevElement", float(t.prevElement) },
            { "twinElement", float(t.twinElement) } };
        for (const auto& [field, value] : fields) {
            Check(value == at(field), std::string("B4: ") + field);
            ++cases;
        }
        Check(t.envWet && !t.envNight, "B4: environment flags");
        for (int tree = 0; tree < essb::kTreeCount; ++tree) {
            Check(t.level[tree] == values.at(levels[tree]), "B4: tree level " + std::to_string(tree));
            ++cases;
        }
    }
    // B5: hit flags -> attack. Ranged: the sneak shot is the power attack; the left hand needs a different right.
    {
        struct Row {
            bool power, sneak, ranged;
            std::uint32_t source, left, right;
            bool wantPower, wantLeft;
        };
        const Row rows[] = {
            { true, false, false, 7, 5, 7, true, false },    // melee power attack, right hand
            { false, true, false, 5, 5, 7, false, true },    // melee sneak attack from the left hand: no power
            { true, false, true, 9, 9, 9, false, false },    // bow: the power flag does not count
            { false, true, true, 9, 9, 9, true, false },     // bow sneak shot counts as power; bow in both hands is not "left"
            { false, false, false, 5, 5, 5, false, false },  // identical weapons in both hands read as right
            { false, false, false, 0, 0, 7, false, false },  // no source weapon (fists): never left
        };
        for (const Row& r : rows) {
            const essb::RawAttack raw{ r.power, r.sneak, r.ranged, r.source, r.left, r.right };
            const essb::Attack a = essb::MakeAttack(essb::kFrost, raw);
            Check(a.element == essb::kFrost && a.power == r.wantPower && a.sneakAttack == r.sneak && a.leftHand == r.wantLeft, "B5 attack row");
            ++cases;
        }
    }
    // B6: raw target facts -> planner facts, one flag at a time.
    {
        using Field = bool essb::RawTarget::*;
        struct Row {
            Field raw;
            bool essb::TargetFacts::*fact;
        };
        const Row rows[] = {
            { &essb::RawTarget::undeadKeyword, &essb::TargetFacts::undeadOrDaedra },
            { &essb::RawTarget::daedraKeyword, &essb::TargetFacts::undeadOrDaedra },
            { &essb::RawTarget::necromancerClass, &essb::TargetFacts::necromancer },
            { &essb::RawTarget::necromancerFaction, &essb::TargetFacts::necromancer },
            { &essb::RawTarget::bloodMark, &essb::TargetFacts::bloodMark },
            { &essb::RawTarget::silenced, &essb::TargetFacts::silenced },
            { &essb::RawTarget::spellInLeftHand, &essb::TargetFacts::spellUser },
            { &essb::RawTarget::spellInRightHand, &essb::TargetFacts::spellUser },
            { &essb::RawTarget::armorSpellEffect, &essb::TargetFacts::spellUser },
            { &essb::RawTarget::cloakEffect, &essb::TargetFacts::spellUser },
            { &essb::RawTarget::essential, &essb::TargetFacts::vip },
            { &essb::RawTarget::baseEssential, &essb::TargetFacts::vip },
            { &essb::RawTarget::baseProtected, &essb::TargetFacts::vip },
            { &essb::RawTarget::baseUnique, &essb::TargetFacts::vip },
        };
        const essb::TargetFacts none = essb::MakeTarget(essb::RawTarget{});
        for (const Row& r : rows) {
            essb::RawTarget raw;
            raw.*(r.raw) = true;
            const essb::TargetFacts facts = essb::MakeTarget(raw);
            Check(facts.*(r.fact) && !(none.*(r.fact)), "B6 target flag");
            ++cases;
        }
        essb::RawTarget thralls;
        thralls.commandedActors = 1;
        thralls.magicka = 12.0f;
        thralls.magickaMax = 40.0f;
        const essb::TargetFacts t = essb::MakeTarget(thralls);
        Check(t.necromancer && t.magicka == 12.0f && t.magickaMax == 40.0f, "B6 thralls and magicka");
        ++cases;
        // 寂 layers ride on the effect's magnitude (whole numbers); the spent marker is a flag.
        for (const float magnitude : { 0.0f, 1.0f, 2.9999f, 3.0f, 5.0f }) {
            essb::RawTarget hush;
            hush.hushMagnitude = magnitude;
            hush.hushSpent = magnitude >= 3.0f;
            const essb::TargetFacts h = essb::MakeTarget(hush);
            Check(h.hushLayers == static_cast<int>(magnitude + 0.5f) && h.hushSpent == (magnitude >= 3.0f) && none.hushLayers == 0 && !none.hushSpent,
                "B6 hush layers");
            ++cases;
        }
    }
    // B7: each planned cast uses the spell record the generator assigned to it.
    {
        const json& spells = wiring.at("spells");
        for (const auto& [name, cast] : kCastNames) {
            if (cast == essb::Cast::kProc) {
                continue;
            }
            essb::CastStep step{ cast };
            if (cast == essb::Cast::kSilence || cast == essb::Cast::kSoakSlow) {
                const std::string prefix = cast == essb::Cast::kSilence ? "kSilence" : "kSoak";
                for (int s = 1; s <= essb::DurationVariants(cast); ++s) {
                    step.seconds = s;
                    Check(essb::SpellFor(step) == spells.at(prefix + std::to_string(s)).get<std::uint32_t>(), "B7 " + prefix + " " + std::to_string(s));
                    ++cases;
                }
                step.seconds = 0;
                Check(essb::SpellFor(step) == 0, "B7 " + prefix + " 0 must not resolve");
                step.seconds = essb::DurationVariants(cast) + 1;
                Check(essb::SpellFor(step) == 0, "B7 " + prefix + " past the last spell must not resolve");
                continue;
            }
            Check(essb::SpellFor(step) == spells.at(name).get<std::uint32_t>(), "B7 " + name);
            ++cases;
        }
        std::set<std::uint32_t> procIds;
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            for (const bool power : { false, true }) {
                const essb::ProcRow* row = essb::FindProc(e, power);
                Check(row && row->element == e && row->power == int(power), "B7 proc row");
                procIds.insert(row->id);
                ++cases;
            }
        }
        Check(procIds.size() == 22, "B7 proc spells distinct");
    }
    // B8: GetActorValuePercentage semantics (0 permanent health reads as full).
    {
        essb::PlayerFacts p;
        p.health = 30.0f;
        p.healthPermanent = 0.0f;
        Check(essb::HealthFraction(p) == 1.0f, "B8 zero permanent health");
        p.healthPermanent = 120.0f;
        Check(Near(essb::HealthFraction(p), 0.25), "B8 fraction");
        cases += 2;
    }
    return cases;
}

// ---------------------------------------------------------------- C

// Transliteration of ESSBController.ResolveHitWeaponType + the OnWeaponHit gates, kept deliberately
// close to the Papyrus text (not to HitPipeline.h) so the two implementations are independent.
int PapyrusResolve(const essb::HitFacts& f)
{
    const bool isWeapon = f.source == essb::SourceKind::kWeapon;
    if (isWeapon) {
        return f.sourceWeaponType;  // Return weaponSource.GetWeaponType()
    }
    const bool hasSource = f.source != essb::SourceKind::kNone;
    const bool ammo = f.source == essb::SourceKind::kAmmo;
    const bool sameProjectile = f.source == essb::SourceKind::kSameProjectile;
    if (hasSource && !ammo && !sameProjectile) {
        return -1;
    }
    const int equipped = f.right.weaponType;  // GetEquippedWeapon(False)
    const int offhand = f.left.weaponType;    // GetEquippedWeapon(True)
    if (f.projectile) {
        if (equipped != -1 && (equipped == 7 || equipped == 9)) {
            return equipped;
        }
        if (offhand != -1 && (offhand == 7 || offhand == 9)) {
            return offhand;
        }
    } else if (!hasSource && f.left.nothing && f.right.nothing) {  // GetEquippedItemType(0) == 0 && (1) == 0
        return 0;
    }
    return -1;
}

// -1 rejected, 0 OnNoFormHit, 1..11 element hit.
int PapyrusAccepts(const essb::HitFacts& f)
{
    if (!f.causeIsPlayer || f.enabled != 1.0f) {
        return -1;
    }
    if (f.bash || f.blocked) {  // Math.LogicalAnd(aiHitFlagMask, 1097731) != 0
        return -1;
    }
    if (!f.targetIsActor || f.targetIsPlayer || f.teammate || f.commanded) {
        return -1;
    }
    const int weaponType = PapyrusResolve(f);
    if (weaponType < 0 || weaponType > 9 || weaponType == 8) {
        return -1;
    }
    const bool ranged = weaponType == 7 || weaponType == 9;
    if (!ranged && f.projectile) {
        return -1;
    }
    if (f.targetDead) {
        return -1;
    }
    const bool hitActive = f.formActive == 1.0f;  // FormActive.GetValueInt() == 1
    if (!hitActive) {
        return 0;  // OnNoFormHit
    }
    const int element = int(f.element);  // CurrentElement.GetValueInt()
    return element >= 1 && element <= 11 ? element : -1;
}

int Verdict(const essb::HitFacts& f)
{
    const essb::Verdict v = essb::Filter(f);
    return v.reason == essb::Reject::kAccepted ? v.element : -1;
}

// Hand states the engine can report: empty, a non-weapon (spell/shield/torch), a hand-to-hand
// weapon, or a weapon of type 1..9.
std::vector<essb::HandFacts> Hands()
{
    std::vector<essb::HandFacts> hands = { { essb::kNoWeapon, true }, { essb::kNoWeapon, false }, { 0, true } };
    for (int type = 1; type <= 9; ++type) {
        hands.push_back({ type, false });
    }
    return hands;
}

int GroupC()
{
    struct SourceState {
        essb::SourceKind kind;
        int weaponType;
    };
    std::vector<SourceState> sources = { { essb::SourceKind::kNone, -1 }, { essb::SourceKind::kAmmo, -1 },
        { essb::SourceKind::kSameProjectile, -1 }, { essb::SourceKind::kOther, -1 } };
    for (int type = 0; type <= 9; ++type) {
        sources.push_back({ essb::SourceKind::kWeapon, type });
    }
    const auto hands = Hands();
    int cases = 0;
    // C1: weapon resolution over every reportable source/projectile/hand combination, with and without a form.
    for (const auto& source : sources) {
        for (int projectile = 0; projectile < 2; ++projectile) {
            for (const auto& right : hands) {
                for (const auto& left : hands) {
                    for (const float active : { 0.0f, 1.0f }) {
                        essb::HitFacts f;
                        f.causeIsPlayer = true;
                        f.targetIsActor = true;
                        f.enabled = 1.0f;
                        f.formActive = active;
                        f.element = 1.0f;
                        f.source = source.kind;
                        f.sourceWeaponType = source.weaponType;
                        f.projectile = projectile != 0;
                        f.right = right;
                        f.left = left;
                        Check(essb::ResolveWeaponType(f) == PapyrusResolve(f), "C1 weapon resolution differs from Papyrus");
                        Check(Verdict(f) == PapyrusAccepts(f), "C1 filter differs from Papyrus");
                        ++cases;
                    }
                }
            }
        }
    }
    // C2: every other gate, each boolean fact and each global value, on melee, ranged and fist baselines.
    // The GLOBs are only ever written with SetValueInt / MCM toggles, so only integer values can occur.
    const float globals[] = { 0.0f, 1.0f, 2.0f, -1.0f, 3.0f, 11.0f, 12.0f };
    for (int baseline = 0; baseline < 3; ++baseline) {
        for (int gate = 0; gate < 9; ++gate) {
            for (int on = 0; on < 2; ++on) {
                for (float value : globals) {
                    essb::HitFacts f;
                    f.causeIsPlayer = true;
                    f.targetIsActor = true;
                    f.enabled = 1.0f;
                    f.formActive = 1.0f;
                    f.element = 3.0f;
                    if (baseline == 0) {
                        f.source = essb::SourceKind::kWeapon;
                        f.sourceWeaponType = 1;
                    } else if (baseline == 1) {
                        f.source = essb::SourceKind::kWeapon;
                        f.sourceWeaponType = 7;
                        f.projectile = true;
                    }
                    const bool flag = on != 0;
                    switch (gate) {
                    case 0: f.causeIsPlayer = flag; break;
                    case 1: f.targetIsActor = flag; break;
                    case 2: f.targetIsPlayer = flag; break;
                    case 3: f.targetDead = flag; break;
                    case 4: f.teammate = flag; f.commanded = !flag; break;
                    case 5: f.bash = flag; f.blocked = !flag; break;
                    case 6: f.enabled = value; f.formActive = flag ? 1.0f : value; break;
                    case 7: f.element = value; break;
                    case 8: f.formActive = value; f.element = flag ? value : 5.0f; break;
                    }
                    Check(Verdict(f) == PapyrusAccepts(f), "C2 gate differs from Papyrus");
                    ++cases;
                }
            }
        }
    }
    return cases;
}

// ---------------------------------------------------------------- D

// Binomial / mean tolerance: 5 standard errors; the seeds are fixed, so the result is deterministic.
void CheckShare(int count, int trials, double expected, const std::string& what)
{
    const double share = double(count) / trials;
    const double sigma = std::sqrt(expected * (1 - expected) / trials);
    Check(std::abs(share - expected) <= 5.0 * sigma, what + ": share " + std::to_string(share) + " vs " + std::to_string(expected));
}

int GroupD()
{
    constexpr int trials = 100000;
    int draws = 0;
    essb::SplitMix64 rng(0x5EED2020ull);
    // D1: B for fire is uniform on [10, 12]: mean 11 and four equal quarters.
    {
        std::array<int, 4> quarter{};
        double sum = 0;
        for (int i = 0; i < trials; ++i) {
            const float b = rng.Real(10.0f, 12.0f);
            Check(b >= 10.0f && b <= 12.0f, "D1 B out of range");
            sum += b;
            ++quarter[std::min(3, int((b - 10.0f) * 2.0f))];
        }
        const double sigmaMean = (2.0 / std::sqrt(12.0)) / std::sqrt(double(trials));
        Check(std::abs(sum / trials - 11.0) <= 5.0 * sigmaMean, "D1 mean of B");
        for (int q = 0; q < 4; ++q) {
            CheckShare(quarter[q], trials, 0.25, "D1 quarter " + std::to_string(q));
        }
        draws += trials;
    }
    // D2: lightning with N = 1 (production until N4): each face 1..25 has 4%.
    {
        std::array<int, 26> face{};
        for (int i = 0; i < trials; ++i) {
            ++face[essb::RollLightning(rng, 1, 25, essb::LightningRolls(essb::kChargesUntilN4))];
        }
        Check(face[0] == 0, "D2 face 0");
        for (int f = 1; f <= 25; ++f) {
            CheckShare(face[f], trials, 0.04, "D2 face " + std::to_string(f));
        }
        draws += trials;
    }
    // D3: best of 7 (six charges, v0.4 2.1 example): mean 22.35 and P(max <= 12) = (12/25)^7.
    {
        double sum = 0;
        double sumSq = 0;
        int low = 0;
        for (int i = 0; i < trials; ++i) {
            const int best = essb::RollLightning(rng, 1, 25, 7);
            sum += best;
            sumSq += double(best) * best;
            low += best <= 12;
        }
        double expected = 0;
        for (int k = 1; k <= 25; ++k) {
            expected += 1.0 - std::pow((k - 1) / 25.0, 7);
        }
        const double mean = sum / trials;
        const double sigmaMean = std::sqrt(sumSq / trials - mean * mean) / std::sqrt(double(trials));
        Check(std::abs(expected - 22.3517) < 1e-3, "D3 expected value of best-of-7 (v0.4 says 22.35)");
        Check(std::abs(mean - expected) <= 5.0 * sigmaMean, "D3 best-of-7 mean");
        CheckShare(low, trials, std::pow(12.0 / 25.0, 7), "D3 best-of-7 low tail");
        draws += 7 * trials;
    }
    // D4: the 5% crit roll.
    {
        int hits = 0;
        for (int i = 0; i < trials; ++i) {
            hits += rng.Chance(essb::LightningCritChance(essb::kChargesUntilN4));
        }
        CheckShare(hits, trials, 0.05, "D4 chance 5%");
        draws += trials;
    }
    // D5: 20 000 planned lightning hits, bare profile (magnitude = face x 1.05, x1.5 on a crit):
    // faces uniform, crit rate 5%, a crit is exactly x1.5.
    {
        constexpr int hits = 20000;
        const essb::Config config = essb::MakeConfig();
        const Inputs in = Bare(essb::kLightning);
        std::array<int, 26> face{};
        int crits = 0;
        for (int i = 0; i < hits; ++i) {
            const essb::Plan p = essb::PlanHit(in.attack, config, in.tuning, in.player, in.target, in.nodes, rng);
            const double raw = p.steps[0].magnitude / 1.05 / (p.crit ? 1.5 : 1.0);
            const int f = int(std::lround(raw));
            Check(std::abs(raw - f) < 1e-3 && f >= 1 && f <= 25, "D5 magnitude is not face x 1.05 (x1.5)");
            ++face[f];
            crits += p.crit;
        }
        for (int f = 1; f <= 25; ++f) {
            CheckShare(face[f], hits, 0.04, "D5 planned face " + std::to_string(f));
        }
        CheckShare(crits, hits, 0.05, "D5 planned crit rate");
        draws += 2 * hits;
    }
    // D6: integer draws have no modulo bias on an awkward span.
    {
        std::array<int, 3> bucket{};
        for (int i = 0; i < trials; ++i) {
            ++bucket[rng.Int(10, 12) - 10];
        }
        for (int b = 0; b < 3; ++b) {
            CheckShare(bucket[b], trials, 1.0 / 3.0, "D6 bucket " + std::to_string(b));
        }
        draws += trials;
    }
    return draws;
}

// Manifest identity at compile time: every proc row is a distinct element x power.
constexpr bool ProcRowsDistinct()
{
    for (std::size_t i = 0; i < std::size(essb::procRows); ++i) {
        for (std::size_t j = i + 1; j < std::size(essb::procRows); ++j) {
            if (essb::procRows[i].element == essb::procRows[j].element && essb::procRows[i].power == essb::procRows[j].power) {
                return false;
            }
        }
    }
    return true;
}
static_assert(ProcRowsDistinct());

json Load(const char* path)
{
    std::ifstream file(path);
    Check(bool(file), std::string("missing fixture ") + path);
    json data;
    file >> data;
    return data;
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        Check(argc == 3, "usage: hit_pipeline_test <build/fix20-magnitude-table.json> <build/fix20-wiring.json>");
        const json table = Load(argv[1]);
        const json wiring = Load(argv[2]);
        const int a0 = GroupA0();
        const int a = GroupA(table);
        const int b = GroupB(wiring);
        const int c = GroupC();
        const int d = GroupD();
        std::printf("NATIVE ANCHORS ok: A0 %d hand-computed hits (fire, lightning power crit + drain, blood curve + leech, divine undead, adept node, no-form dispel; round 21: siphon amount + dispel rate, riposte, hush break, soak duration)\n", a0);
        std::printf("NATIVE MAGNITUDE ok: A %d scenarios == build/fix20_reference.py (casts, order, magnitudes, seconds, draws, echo, riposte, crit)\n", a);
        std::printf("NATIVE WIRING ok: B %d mocked engine reads -> inputs (perk FormIDs + 4-probe ranks, no-form suppression, GLOB fields, attack, target, spells)\n", b);
        std::printf("NATIVE FILTER ok: C %d hit-fact combinations == Papyrus OnWeaponHit gates (element and no-form)\n", c);
        std::printf("NATIVE RANDOM ok: D %d production draws (uniform B, 1..25 faces, best-of-7, 5%% crit, planned lightning faces and crits) within 5 sigma\n", d);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "FAILED: %s\n", e.what());
        return 1;
    }
}
