// Round 22 (N3) offline tests of the status layer (Status.h and the generated ManifestData.h).
//   S  scenarios: every row of build/fix22-status-table.json -- pre-hit boards, owned nodes, a list of steps (hits,
//      forced opens, ends, expiries, the ladders' timers, form leave, ProcTerms) -- run through the planners here; the
//      boards afterwards and every non-status op (damage, heals, washes, slows, DoTs, ModEvents) must equal what
//      build/fix22_reference.py (written from the v0.4 text) computed. Random draws are fixed: a chance p succeeds when
//      p >= 0.5, a real draw is the midpoint (the table says the same)
//   W  wiring: the record identities build/fix22-wiring.json takes from the generator (build/fix22_records.py and
//      build_v03's IDs) -> TagOf / Settles / Read (a fake engine's effect list) / Lower (what is cast and dispelled)
// Injected faults (build/fix22_verify.py) mutate the table and require this binary to fail.
#include "Status.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

using json = nlohmann::json;
using essb::StatusKind;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
}

bool Near(double actual, double expected)
{
    return std::abs(actual - expected) <= 2e-4 * std::max(1.0, std::abs(expected));
}

json Load(const char* path)
{
    std::ifstream in(path);
    Check(in.good(), std::string("cannot open ") + path);
    json data;
    in >> data;
    return data;
}

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

struct FixedRng {
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return lo + (hi - lo) * 0.5f; }
    bool Chance(float probability) { return probability >= 0.5f; }
};

std::string SuffixOf(int kind)
{
    const std::string_view id = essb::kStatusRecords[kind].editorId;
    // Round 22's kinds are ESSB_N3_*, round 23's (build/fix23_records.py, appended) ESSB_N4_*.
    constexpr std::string_view n3 = "ESSB_N3_";
    constexpr std::string_view n4 = "ESSB_N4_";
    constexpr std::string_view n5 = "ESSB_N5_";   // round 24's kinds follow (same prefix length)
    constexpr std::string_view n6 = "ESSB_N6_";   // round 25's too
    Check(id.starts_with(n3) || id.starts_with(n4) || id.starts_with(n5) || id.starts_with(n6),
        "status record without the ESSB_N3_ .. N6_ prefix");
    return std::string(id.substr(n3.size()));
}

StatusKind KindOf(const std::string& suffix)
{
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        if (SuffixOf(k) == suffix) {
            return static_cast<StatusKind>(k);
        }
    }
    throw std::runtime_error("unknown status kind " + suffix);
}

const char* kEventNames[] = { "Open", "End", "Frozen", "Hallucinate", "Judgment", "Splash", "Shatter", "Landing", "Rise",
    "Discharge", "Blade", "Knock", "SyncUp", "Cleanse", "Lethal", "Push", "Ash", "Raise", "Sneak", "Domain", "Overheat",
    "Switch", "Close" };
// round 23 added six (N4), round 24 six more (N5; build/fix24_reference.py checks those)
const int kEventArgs[] = { 4, 7, 1, 2, 1, 1, 1, 1, 0, 4, 2, 1, 1, 1, 0, 5, 0, 5, 1, 3, 0, 2, 0 };
static_assert(std::size(kEventNames) == static_cast<int>(essb::Event::kCount));

// ---------------------------------------------------------------- group S

struct Row {
    std::string name;
    std::vector<double> values;
};

std::optional<Row> RowOf(const essb::StatusOp& op)
{
    using essb::Op;
    switch (op.op) {
    case Op::kDamage: return Row{ "damage", { static_cast<double>(op.element), op.magnitude } };
    case Op::kHeal: return Row{ "heal", { op.magnitude } };
    case Op::kRestoreMagicka: return Row{ "magicka", { op.magnitude } };
    case Op::kRestoreStamina: return Row{ "stamina", { op.magnitude } };
    case Op::kPayHealth: return Row{ "pay", { op.magnitude } };
    case Op::kWash: return Row{ "wash", { op.magnitude } };
    case Op::kSlow: return Row{ "slow", { op.magnitude, op.seconds } };
    case Op::kBleedDot: return Row{ "bleedDot", { op.magnitude, op.seconds } };
    case Op::kPoisonDot: return Row{ "poisonDot", { op.magnitude, op.seconds } };
    case Op::kRemoveDots: return Row{ "removeDots", {} };
    case Op::kBleedDrain: return Row{ "bleedDrain", { op.magnitude } };
    case Op::kEvent: {
        if (op.event == essb::Event::kOverheat) {
            return std::nullopt;   // round 24: a body-only marker the body pass consumes (reaction_test covers it)
        }
        const int e = static_cast<int>(op.event);
        Row row{ std::string("event:") + kEventNames[e], {} };
        for (int i = 0; i < kEventArgs[e]; ++i) {
            row.values.push_back(op.arg[i]);
        }
        return row;
    }
    default:
        return std::nullopt;   // status writes: the boards afterwards are compared instead
    }
}

Row RowOf(const json& expected)
{
    Row row;
    row.name = expected.at(0).get<std::string>();
    std::size_t i = 1;
    if (row.name == "event") {
        row.name += ":" + expected.at(1).get<std::string>();
        i = 2;
    }
    for (; i < expected.size(); ++i) {
        row.values.push_back(expected.at(i).get<double>());
    }
    return row;
}

std::map<std::string, std::pair<double, double>> Summary(const essb::Board& b)
{
    std::map<std::string, std::pair<double, double>> out;
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        if (b.slot[k].has) {
            out[SuffixOf(k)] = { b.slot[k].magnitude, b.slot[k].Remaining() };
        }
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        if (b.mark[e].has) {
            out["Mark" + std::to_string(e)] = { b.mark[e].magnitude, b.mark[e].Remaining() };
        }
    }
    if (b.bleedDot.has) {
        out["BleedDot"] = { b.bleedDot.magnitude, b.bleedDot.Remaining() };
    }
    if (b.poisonDot.has) {
        out["PoisonDot"] = { b.poisonDot.magnitude, b.poisonDot.Remaining() };
    }
    return out;
}

void CompareBoard(const std::string& where, const essb::Board& actual, const json& expected)
{
    const auto have = Summary(actual);
    std::set<std::string> want;
    for (const auto& [name, v] : expected.items()) {
        want.insert(name);
        const auto it = have.find(name);
        Check(it != have.end(), where + ": expected " + name + " is missing");
        Check(Near(it->second.first, v.at(0).get<double>()), where + ": " + name + " magnitude " +
              std::to_string(it->second.first) + " != " + std::to_string(v.at(0).get<double>()));
        Check(Near(it->second.second, v.at(1).get<double>()), where + ": " + name + " remaining " +
              std::to_string(it->second.second) + " != " + std::to_string(v.at(1).get<double>()));
    }
    for (const auto& [name, v] : have) {
        Check(want.contains(name), where + ": unexpected " + name);
    }
}

bool Same(const Row& a, const Row& b)
{
    if (a.name != b.name || a.values.size() != b.values.size()) {
        return false;
    }
    for (std::size_t i = 0; i < a.values.size(); ++i) {
        if (!Near(a.values[i], b.values[i])) {
            return false;
        }
    }
    return true;
}

std::string Text(const Row& r)
{
    std::string s = r.name;
    for (double v : r.values) {
        char buf[48];
        std::snprintf(buf, sizeof(buf), " %.5f", v);
        s += buf;
    }
    return s;
}

void Age(essb::Board& b, float seconds)
{
    auto step = [&](essb::Slot& s) {
        if (s.has) {
            s.elapsed += seconds;
            if (s.elapsed >= s.duration) {
                s = essb::Slot{};
            }
        }
    };
    for (auto& s : b.slot) {
        step(s);
    }
    for (auto& s : b.mark) {
        step(s);
    }
    step(b.bleedDot);
    step(b.poisonDot);
}

void Seed(essb::Board& target, essb::Board& self, const json& row)
{
    for (const auto& s : row.at("statuses")) {
        essb::Board& board = s.at(0).get<std::string>() == "target" ? target : self;
        const std::string kind = s.at(1).get<std::string>();
        const essb::Slot slot{ true, s.at(2).get<float>(), s.at(3).get<float>(), s.at(4).get<float>() };
        if (kind == "PoisonDot") {
            board.poisonDot = slot;
        } else if (kind == "BleedDot") {
            board.bleedDot = slot;
        } else {
            board[KindOf(kind)] = slot;
        }
    }
    for (const auto& m : row.at("marks")) {
        target.mark[m.at(0).get<int>()] = essb::Slot{ true, m.at(1).get<float>(), m.at(2).get<float>(), m.at(3).get<float>() };
    }
    const json& flags = row.at("flags");
    target.maxSlowPct = flags.value("max_slow", 0.0f);
    target.frenzied = flags.value("frenzied", false);
}

void ApplyTuning(essb::Tuning& t, const json& row)
{
    const json& tu = row.at("tuning");
    t.syncStage = tu.value("syncStage", 0);
    t.multDuration = tu.value("multDuration", 1.0f);
    t.multCooldown = tu.value("multCooldown", 1.0f);
    t.nodeScale = tu.value("nodeScale", 3.0f);
    t.baseDamageMult = tu.value("baseDamageMult", 1.0f);
    t.multRecovery = tu.value("multRecovery", 1.0f);
    t.multDot = tu.value("multDot", 1.0f);
    t.poisonDotK = tu.value("poisonDotK", 0.2116f);
    t.bleedDotK = tu.value("bleedDotK", 0.1143f);
    t.envWet = tu.value("envWet", false);
    t.envStormy = tu.value("envStormy", false);
    t.envNight = tu.value("envNight", false);
    t.slowCapPct = tu.value("slowCapPct", 70.0f);
    t.wetSlowPct = tu.value("wetSlowPct", 15.0f);
    t.level.fill(1.0f);
    for (const auto& lv : row.at("levels")) {
        t.level[lv.at(0).get<int>()] = lv.at(1).get<float>();
    }
}

std::pair<int, int> GroupS(const json& table)
{
    essb::Config c;
    for (int e = 1; e <= 11; ++e) {
        c.damage[e] = { table.at("damage").at(e - 1).at(0).get<float>(), table.at("damage").at(e - 1).at(1).get<float>() };
    }
    int scenarios = 0;
    int compared = 0;
    for (const json& row : table.at("scenarios")) {
        const std::string name = row.at("name").get<std::string>();
        MapNodes nodes;
        for (const auto& r : row.at("ranks")) {
            nodes.ranks[{ r.at(0).get<int>(), r.at(1).get<int>(), r.at(2).get<int>() }] = r.at(3).get<int>();
        }
        for (const auto& b : row.at("branches")) {
            nodes.branches.insert({ b.at(0).get<int>(), b.at(1).get<int>(), b.at(2).get<int>(), b.at(3).get<int>() });
        }
        essb::Tuning t;
        ApplyTuning(t, row);
        const json& facts = row.at("facts");
        const json& body = row.at("body");
        essb::StatusInputs in;
        in.config = &c;
        in.tuning = &t;
        const float hp = facts.value("hp", 100.0f);
        const float hpMax = facts.value("hp_max", 100.0f);
        in.player.health = hp;
        in.player.healthPermanent = hpMax;
        in.player.healthMax = hpMax;
        in.player.interior = facts.value("interior", false);
        in.self = essb::Self{ hp, hpMax, hpMax };
        in.body.health = body.value("health", 100.0f);
        in.body.healthMax = body.value("health_max", 100.0f);
        in.body.stamina = body.value("stamina", 100.0f);
        in.body.staminaMax = body.value("stamina_max", 100.0f);
        in.body.vip = body.value("vip", false);
        in.body.undeadOrDaedra = body.value("undead", false);
        in.body.distanceToPlayer = body.value("distance", 0.0f);
        in.iceArmor = facts.value("ice_armor", false);
        essb::Board target;
        essb::Board self;
        Seed(target, self, row);
        FixedRng rng;
        std::vector<Row> ops;
        for (const json& step : row.at("steps")) {
            const std::string op = step.at(0).get<std::string>();
            essb::StatusPlan plan;
            if (op == "hit") {
                essb::PlanStatusHit(plan, step.at(1).get<int>(), step.at(2).get<bool>(), target, self, in, nodes, rng);
            } else if (op == "force") {
                essb::PlanStatusHit(plan, step.at(1).get<int>(), false, target, self, in, nodes, rng, false);
            } else if (op == "end") {
                essb::PlanEnd(plan, step.at(1).get<int>(), static_cast<essb::EndReason>(step.at(2).get<int>()),
                    step.at(3).get<float>(), false, target, self, in, nodes, rng);
            } else if (op == "expireMark") {
                essb::OnMarkExpired(plan, step.at(1).get<int>(), step.at(2).get<int>(), target, self, in, nodes, rng);
            } else if (op == "frozenEnd") {
                target[StatusKind::kFrozen] = essb::Slot{};
                essb::OnFrozenEnd(plan, target, self, in, nodes, step.size() > 1 ? step.at(1).get<int>() : 0);
            } else if (op == "spread") {
                essb::rule::SpreadDoses(plan, target, step.at(1).get<float>(), in, nodes);
            } else if (op == "miasma") {
                ops.push_back(Row{ "miasmaDoses", { essb::rule::MiasmaDoses(target, in, nodes) } });
            } else if (op == "plague") {
                ops.push_back(Row{ "plagueChance", { essb::rule::PlagueChance(target, t, nodes) } });
            } else if (op == "starFuseEnd") {
                essb::OnStarFuseEnd(plan, target, self, in, nodes);
            } else if (op == "deathCurseEnd") {
                target[StatusKind::kDeathCurse] = essb::Slot{};
                essb::OnDeathCurseEnd(plan, step.at(1).get<float>(), target, self, in, nodes);
            } else if (op == "hallucinationEnd") {
                essb::OnHallucinationEnd(plan, target, in, nodes);
            } else if (op == "fuseEnd") {
                essb::OnFuseEnd(plan, step.at(1).get<int>(), self, in, nodes);
            } else if (op == "leave") {
                essb::OnFormLeave(plan, step.at(1).get<int>(), step.at(2).get<bool>(), self, in, nodes);
            } else if (op == "decay") {
                essb::PlanDecay(plan, self, in, nodes);
            } else if (op == "age") {
                Age(target, step.at(1).get<float>());
                Age(self, step.at(1).get<float>());
            } else if (op == "terms") {
                const essb::ProcTerm term = essb::ProcTerms(step.at(1).get<int>(), step.at(2).get<bool>(), t, target, self, in.body, nodes);
                ops.push_back(Row{ "terms", { step.at(1).get<double>(), term.add, term.mult } });
            } else {
                throw std::runtime_error(name + ": unknown step " + op);
            }
            Check(!plan.overflow, name + ": plan overflow");
            for (int i = 0; i < plan.count; ++i) {
                if (auto r = RowOf(plan.ops[i])) {
                    ops.push_back(*r);
                }
            }
        }
        const json& expect = row.at("expect");
        CompareBoard(name + " (target)", target, expect.at("target"));
        CompareBoard(name + " (you)", self, expect.at("me"));
        std::vector<bool> used(ops.size(), false);
        for (const json& e : expect.at("ops")) {
            const Row want = RowOf(e);
            bool found = false;
            for (std::size_t i = 0; i < ops.size() && !found; ++i) {
                if (!used[i] && Same(ops[i], want)) {
                    used[i] = true;
                    found = true;
                }
            }
            if (!found) {
                std::string have;
                for (const auto& r : ops) {
                    have += "\n    " + Text(r);
                }
                throw std::runtime_error(name + ": expected op " + Text(want) + " not produced; ops were:" + have);
            }
            ++compared;
        }
        for (std::size_t i = 0; i < ops.size(); ++i) {
            Check(used[i], name + ": unexpected op " + Text(ops[i]));
        }
        ++scenarios;
    }
    return { scenarios, compared };
}

// ---------------------------------------------------------------- group W

int GroupW(const json& w)
{
    using essb::Op;
    using essb::TagKind;
    int checks = 0;
    const json& kinds = w.at("kinds");
    Check(static_cast<int>(kinds.size()) == essb::kStatusKindCount, "status kind count differs from the generator");
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        const json& row = kinds.at(k);
        const essb::StatusRecord& r = essb::kStatusRecords[k];
        const std::string label = row.at("suffix").get<std::string>();
        Check(SuffixOf(k) == label, "kind order differs at " + label);
        Check(r.effect == row.at("effect").get<std::uint32_t>() && r.spell == row.at("spell").get<std::uint32_t>(), label + ": record ids");
        Check(Near(r.seconds, row.at("seconds").get<double>()) && r.onPlayer == row.at("on_player").get<bool>() &&
              r.stub == row.at("stub").get<bool>(), label + ": record facts");
        const essb::Tag tag = essb::TagOf(r.effect);
        Check(tag.kind == TagKind::kStatus && tag.index == k, label + ": TagOf");
        // A stub script is what makes the engine report the end; the DLL settles exactly those (熔身 needs no settlement).
        Check(essb::Settles(tag) == (r.stub && label != "MoltenBody"), label + ": Settles");
        // Apply with the record's seconds: effectiveness 1; with 1.5x: 1.5; remove: dispel the spell only.
        essb::StatusOp op = essb::MakeOp(Op::kApply, r.onPlayer ? essb::Who::kPlayer : essb::Who::kTarget);
        op.kind = static_cast<StatusKind>(k);
        op.magnitude = 3.0f;
        op.seconds = r.seconds;
        essb::Lowered l = essb::Lower(op, 70.0f);
        Check(l.spell == r.spell && l.dispelSpell == r.spell && Near(l.effectiveness, 1.0) && Near(l.magnitude, 3.0) &&
              l.onPlayer == r.onPlayer, label + ": Lower apply");
        op.seconds = r.seconds * 1.5f;
        l = essb::Lower(op, 70.0f);
        Check(Near(l.effectiveness, 1.5), label + ": Lower apply effectiveness");
        op.op = Op::kRemove;
        l = essb::Lower(op, 70.0f);
        Check(l.spell == 0 && l.dispelSpell == r.spell, label + ": Lower remove");
        // A fake engine list: the effect with magnitude 2, 1 s gone of 4 s; a shorter duplicate does not win.
        essb::Board b;
        essb::Read(b, essb::RawEffect{ r.effect, 2.0f, 1.0f, 4.0f });
        essb::Read(b, essb::RawEffect{ r.effect, 5.0f, 1.0f, 2.0f });
        Check(b.slot[k].has && Near(b.slot[k].magnitude, 2.0) && Near(b.slot[k].Remaining(), 3.0), label + ": Read");
        checks += 7;
    }
    const float markSeconds = w.at("mark_record_seconds").get<float>();
    Check(Near(essb::status::kMarkRecordSeconds, markSeconds), "mark record seconds");
    for (const json& m : w.at("marks")) {
        const int e = m.at("element").get<int>();
        const std::uint32_t effect = m.at("effect").get<std::uint32_t>();
        const essb::Tag tag = essb::TagOf(effect);
        Check(tag.kind == TagKind::kMark && tag.index == e && essb::Settles(tag), "mark tag " + std::to_string(e));
        essb::StatusOp op = essb::MakeOp(Op::kApplyMark);
        op.element = e;
        op.seconds = 12.0f;
        op.magnitude = static_cast<float>(essb::n3::kMarkJumped);
        const essb::Lowered l = essb::Lower(op, 70.0f);
        Check(l.spell == m.at("spell").get<std::uint32_t>() && l.dispelEffect == effect && Near(l.effectiveness, 12.0 / markSeconds) &&
              Near(l.magnitude, essb::n3::kMarkJumped), "mark lower " + std::to_string(e));
        essb::Board b;
        essb::Read(b, essb::RawEffect{ effect, 4.0f, 2.0f, 8.0f });
        Check(b.mark[e].has && essb::MarkFlags(b.mark[e].magnitude) == essb::n3::kMarkExtended, "mark read flags");
        checks += 3;
    }
    for (const char* which : { "bleed_dot", "poison_dot" }) {
        const json& d = w.at(which);
        const bool bleed = std::string(which) == "bleed_dot";
        const std::uint32_t effect = d.at("effect").get<std::uint32_t>();
        const essb::Tag tag = essb::TagOf(effect);
        Check(tag.kind == (bleed ? TagKind::kBleedDot : TagKind::kPoisonDot), std::string(which) + " tag");
        const json& spells = d.at("spells");
        Check(static_cast<int>(spells.size()) == essb::status::kDotMaxSeconds, std::string(which) + " spell count");
        for (int s = 1; s <= essb::status::kDotMaxSeconds; ++s) {
            const essb::StatusOp op = essb::Amount(bleed ? Op::kBleedDot : Op::kPoisonDot, 7.5f, 0, static_cast<float>(s) - 0.3f);
            const essb::Lowered l = essb::Lower(op, 70.0f);
            Check(l.spell == spells.at(s - 1).get<std::uint32_t>() && l.dispelEffect == effect && Near(l.magnitude, 7.5) &&
                  Near(l.effectiveness, 1.0), std::string(which) + " whole seconds " + std::to_string(s));
            ++checks;
        }
        const essb::Lowered gone = essb::Lower(essb::Amount(bleed ? Op::kBleedDot : Op::kPoisonDot, 0.0f), 70.0f);
        Check(gone.spell == 0 && gone.dispelEffect == effect, std::string(which) + " magnitude 0 removes");
    }
    {
        essb::Board b;
        essb::Read(b, essb::RawEffect{ w.at("fear").get<std::uint32_t>(), 10.0f, 0.5f, 2.0f });
        essb::Read(b, essb::RawEffect{ w.at("frenzy").get<std::uint32_t>(), 10.0f, 0.5f, 3.0f });
        essb::Read(b, essb::RawEffect{ w.at("slow_effect").get<std::uint32_t>(), 25.0f, 0.5f, 6.0f });
        essb::Read(b, essb::RawEffect{ w.at("slow_effect").get<std::uint32_t>(), 50.0f, 0.5f, 3.0f });
        Check(b.fearing && b.frenzied && Near(b.maxSlowPct, 50.0), "fear / frenzy / slow read");
        Check(essb::Settles(essb::TagOf(w.at("fear").get<std::uint32_t>())) && essb::Settles(essb::TagOf(w.at("frenzy").get<std::uint32_t>())),
              "fear / frenzy settle (回魘)");
        checks += 2;
    }
    for (int e = 1; e <= 11; ++e) {
        const essb::Lowered l = essb::Lower(essb::Amount(Op::kDamage, 12.0f, e), 70.0f);
        Check(l.spell == w.at("react").at(e - 1).get<std::uint32_t>() && Near(l.magnitude, 12.0), "react spell " + std::to_string(e));
        ++checks;
    }
    Check(essb::Lower(essb::Amount(Op::kDamage, 5.0f, 0), 70.0f).spell == w.at("true_spell").get<std::uint32_t>(), "true damage spell");
    const json& soak = w.at("soak");
    const essb::Lowered slow = essb::Lower(essb::Amount(Op::kSlow, 80.0f, 0, 6.2f), 60.0f);
    Check(slow.spell == soak.at(5).get<std::uint32_t>() && Near(slow.magnitude, 60.0), "slow: whole seconds and the MCM cap");
    Check(essb::Lower(essb::Amount(Op::kSlow, 25.0f, 0, 3.0f), 0.0f).spell == 0, "slow cap 0 casts nothing");
    Check(essb::Lower(essb::Amount(Op::kHeal, 3.0f), 70.0f).spell == w.at("heal").get<std::uint32_t>(), "heal spell");
    Check(essb::Lower(essb::Amount(Op::kRestoreMagicka, 3.0f), 70.0f).spell == w.at("magicka").get<std::uint32_t>(), "magicka spell");
    Check(essb::Lower(essb::Amount(Op::kRestoreStamina, 3.0f), 70.0f).spell == w.at("stamina").get<std::uint32_t>(), "stamina spell");
    Check(essb::Lower(essb::Amount(Op::kBleedDrain, 3.0f), 70.0f).spell == w.at("bleed_tick").get<std::uint32_t>(), "放血 spell");
    checks += 7;
    Check(essb::TagOf(0x12345678u).kind == TagKind::kNone, "a foreign effect has no tag");
    return checks + 1;
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 3) {
            std::cerr << "usage: status_test <fix22-status-table.json> <fix22-wiring.json>\n";
            return 2;
        }
        const auto [scenarios, ops] = GroupS(Load(argv[1]));
        std::printf("NATIVE STATUS S ok: %d scenarios, %d expected ops matched exactly (boards compared after every row)\n", scenarios, ops);
        const int wiring = GroupW(Load(argv[2]));
        std::printf("NATIVE STATUS W ok: %d record checks (TagOf, Settles, Read, Lower vs build/fix22_records.py)\n", wiring);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "STATUS TEST FAILED: %s\n", e.what());
        return 1;
    }
}
