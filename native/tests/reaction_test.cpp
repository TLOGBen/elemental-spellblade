// Round 24 (N5) offline tests of the reaction bodies, the fusion (融斷), the death handling and the range scans
// (Reactions.h).
//   R  scenarios: every row of build/fix24-body-table.json -- a crowd (member 0 and the others: boards, bodies, positions,
//      flags), your board, the owned nodes and a list of steps (body events pushed as the state planners push them, the
//      crowd ops, a burst, a death, an advent, an echo, the hit's branch bodies, 印潮, 化身) -- run through the planners
//      here; every member's board afterwards and every non-status op (with the member it acts on; -1 = you) must equal
//      what build/fix24_reference.py (written from the v0.4 text) computed. Random draws follow the row's mode like
//      self_test ('mid', 'yes', 'no').
//   W  wiring: build/fix24-wiring.json (the generator's identities) -> the round-24 kinds, the timed families and their
//      Lower (which spell, which side), 寂, the ally heal, the silences, the drain, the crowd's forms, the two tunables
//   X  direct checks: Distance, Around (nearest first, the limit, the centre, allies and the empty never picked), the
//      `at` stamping of StatusPlan::Push, BodyOnly, the burst radius / multiplier, the raise table
// Injected faults (build/fix24_verify.py) mutate the table and require this binary to fail.
#include "Reactions.h"
#include "StatusEngine.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
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

struct ScriptRng {
    int mode = 0;   // 0 mid, 1 yes, 2 no
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return mode == 1 ? lo : mode == 2 ? hi : lo + (hi - lo) * 0.5f; }
    bool Chance(float probability) { return mode == 1 ? true : mode == 2 ? false : probability >= 0.5f; }
};

std::string SuffixOf(int kind)
{
    const std::string_view id = essb::kStatusRecords[kind].editorId;
    for (const std::string_view prefix :
        { std::string_view("ESSB_N3_"), std::string_view("ESSB_N4_"), std::string_view("ESSB_N5_"), std::string_view("ESSB_N6_") }) {
        if (id.starts_with(prefix)) {
            return std::string(id.substr(prefix.size()));
        }
    }
    throw std::runtime_error("status record without the ESSB_N3_ .. N6_ prefix");
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
const int kEventArgs[] = { 4, 8, 1, 3, 2, 1, 1, 1, 0, 4, 2, 1, 1, 1, 0, 5, 0, 5, 1, 3, 0, 2, 0 };
static_assert(std::size(kEventNames) == static_cast<int>(essb::Event::kCount));
static_assert(std::size(kEventArgs) == static_cast<int>(essb::Event::kCount));

const char* kTimedNames[] = { "armorDebuff", "magicResistBuff", "haste", "fireResistDebuff", "frostResistDebuff", "shockResistDebuff",
    "magicResistDebuff", "meleeDebuff", "healRateDebuff", "staminaRateDebuff", "poisonResistBuff", "poisonResistDebuff" };
static_assert(std::size(kTimedNames) == essb::kTimedKinds);

// ---------------------------------------------------------------- group R

struct Row {
    std::string name;
    int at = 0;
    std::vector<double> values;
};

bool SelfOp(const essb::StatusOp& op)
{
    using essb::Op;
    return op.who == essb::Who::kPlayer || op.op == Op::kHeal || op.op == Op::kRestoreMagicka || op.op == Op::kRestoreStamina ||
           op.op == Op::kPayHealth || op.op == Op::kSpendMagicka || op.op == Op::kPayStamina || op.op == Op::kBloodGuardPool ||
           op.op == Op::kHurtHealth || op.op == Op::kResonance || op.op == Op::kFreezeNearby ||
           (op.op == Op::kEvent && (op.event == essb::Event::kSyncUp || op.event == essb::Event::kCleanse ||
                                       op.event == essb::Event::kLethal || op.event == essb::Event::kSneak ||
                                       op.event == essb::Event::kSplash || op.event == essb::Event::kRise ||
                                       op.event == essb::Event::kOverheat));
}

std::optional<Row> RowOf(const essb::StatusOp& op)
{
    using essb::Op;
    const int at = SelfOp(op) ? -1 : op.at;
    switch (op.op) {
    case Op::kDamage: return Row{ "damage", at, { static_cast<double>(op.element), op.magnitude } };
    case Op::kHeal: return Row{ "heal", at, { op.magnitude } };
    case Op::kRestoreMagicka: return Row{ "magicka", at, { op.magnitude } };
    case Op::kRestoreStamina: return Row{ "stamina", at, { op.magnitude } };
    case Op::kPayHealth: return Row{ "pay", at, { op.magnitude } };
    case Op::kWash: return Row{ "wash", at, { op.magnitude, static_cast<double>(op.element) } };
    case Op::kSlow: return Row{ "slow", at, { op.magnitude, op.seconds } };
    case Op::kBleedDot: return Row{ "bleedDot", at, { op.magnitude, op.seconds } };
    case Op::kPoisonDot: return Row{ "poisonDot", at, { op.magnitude, op.seconds } };
    case Op::kRemoveDots: return Row{ "removeDots", at, {} };
    case Op::kDrainStamina: return Row{ "drainStamina", at, { op.magnitude } };
    case Op::kDrainMagicka: return Row{ "drainMagicka", at, { op.magnitude } };
    case Op::kHealTarget: return Row{ "healTarget", at, { op.magnitude } };
    case Op::kSilence: return Row{ "silence", at, { op.seconds } };
    case Op::kHush: return Row{ "hush", at, { op.magnitude } };
    case Op::kTimed: return Row{ std::string("timed:") + kTimedNames[op.element], at, { op.magnitude, op.seconds } };
    case Op::kResonance: return Row{ "resonance", at, {} };
    case Op::kCrushArea: return Row{ "crush", at, { op.magnitude, op.seconds } };
    case Op::kFreezeNearby: return Row{ "freezeNearby", at, {} };
    case Op::kEvent: {
        const int e = static_cast<int>(op.event);
        Row row{ std::string("event:") + kEventNames[e], at, {} };
        for (int i = 0; i < kEventArgs[e]; ++i) {
            row.values.push_back(op.arg[i]);
        }
        return row;
    }
    default:
        return std::nullopt;   // status writes: the boards afterwards are compared instead; kNoop: consumed
    }
}

Row RowOf(const json& expected)
{
    Row row;
    row.name = expected.at(0).get<std::string>();
    row.at = expected.at(1).get<int>();
    std::size_t i = 2;
    if (row.name == "event" || row.name == "timed") {
        row.name += ":" + expected.at(2).get<std::string>();
        i = 3;
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
    if (b.guardPool.has) {
        out["GuardPool"] = { b.guardPool.magnitude, 0.0 };
    }
    if (b.hush.has) {
        out["Hush"] = { b.hush.magnitude, b.hush.Remaining() };
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
    if (a.name != b.name || a.at != b.at || a.values.size() != b.values.size()) {
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
    std::string s = r.name + " @" + std::to_string(r.at);
    for (double v : r.values) {
        char buf[48];
        std::snprintf(buf, sizeof(buf), " %.5f", v);
        s += buf;
    }
    return s;
}

void SeedBoard(essb::Board& board, const json& statuses)
{
    for (const auto& [kind, v] : statuses.items()) {
        const essb::Slot slot{ true, v.at(0).get<float>(), v.at(1).get<float>(), v.at(2).get<float>() };
        if (kind == "PoisonDot") {
            board.poisonDot = slot;
        } else if (kind == "BleedDot") {
            board.bleedDot = slot;
        } else if (kind == "GuardPool") {
            board.guardPool = slot;
        } else if (kind == "Hush") {
            board.hush = slot;
        } else if (kind.starts_with("Mark")) {
            board.mark[std::stoi(kind.substr(4))] = slot;
        } else {
            board[KindOf(kind)] = slot;
        }
    }
}

std::array<float, 3> Pos(const json& p)
{
    return { p.at(0).get<float>(), p.at(1).get<float>(), p.at(2).get<float>() };
}

void SeedCrowd(essb::Crowd& crowd, const json& c)
{
    crowd.you = Pos(c.at("you"));
    const json& members = c.at("members");
    Check(members.size() >= 1 && members.size() <= static_cast<std::size_t>(essb::kCrowdSlots), "crowd size");
    crowd.count = static_cast<int>(members.size());
    for (std::size_t k = 0; k < members.size(); ++k) {
        const json& m = members.at(k);
        essb::Member& x = crowd.m[k];
        x = essb::Member{};
        x.has = m.value("has", true);
        x.ally = m.value("ally", false);
        x.pos = Pos(m.at("pos"));
        x.level = m.value("level", 10);
        x.dragon = m.value("dragon", false);
        x.essential = m.value("essential", false);
        x.spellUser = m.value("spell_user", false);
        x.armor = m.value("armor", 0.0f);
        if (m.contains("resist")) {
            for (int i = 0; i < 5; ++i) {
                x.resist[i] = m.at("resist").at(i).get<float>();
            }
        }
        x.magicka = m.value("magicka", 0.0f);
        x.magickaMax = m.value("magicka_max", 0.0f);
        const json body = m.value("body", json::object());
        x.body.health = body.value("health", 100.0f);
        x.body.healthMax = body.value("health_max", 100.0f);
        x.body.stamina = body.value("stamina", 100.0f);
        x.body.staminaMax = body.value("stamina_max", 100.0f);
        x.body.vip = body.value("vip", false);
        x.body.undeadOrDaedra = body.value("undead", false);
        x.body.distanceToPlayer = essb::Distance(crowd.you, x.pos);
        SeedBoard(x.board, m.value("board", json::object()));
        x.board.frenzied = m.value("frenzied", false);
        x.board.maxSlowPct = m.value("max_slow", 0.0f);
    }
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
    t.multDrain = tu.value("multDrain", 1.0f);
    t.multDot = tu.value("multDot", 1.0f);
    t.envNight = tu.value("envNight", false);
    t.slowCapPct = tu.value("slowCapPct", 70.0f);
    t.frostOpenSlowPct = tu.value("frostOpenSlowPct", 25.0f);
    t.waterOpenStamina = tu.value("waterOpenStamina", 80.0f);
    t.wetSlowPct = tu.value("wetSlowPct", 15.0f);
    t.level.fill(1.0f);
    for (const auto& lv : row.at("levels")) {
        t.level[lv.at(0).get<int>()] = lv.at(1).get<float>();
    }
}

essb::Event EventOf(const std::string& name)
{
    for (int e = 0; e < static_cast<int>(essb::Event::kCount); ++e) {
        if (name == kEventNames[e]) {
            return static_cast<essb::Event>(e);
        }
    }
    throw std::runtime_error("unknown event " + name);
}

std::pair<int, int> GroupR(const json& table)
{
    essb::Config c;
    for (int e = 1; e <= 11; ++e) {
        c.damage[e] = { table.at("damage").at(e - 1).at(0).get<float>(), table.at("damage").at(e - 1).at(1).get<float>() };
    }
    int scenarios = 0;
    int compared = 0;
    auto crowd = std::make_unique<essb::Crowd>();
    auto plan = std::make_unique<essb::StatusPlan>();
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
        essb::StatusInputs in;
        in.config = &c;
        in.tuning = &t;
        in.n4 = true;
        in.formElement = facts.value("form", 0);
        const float hpMax = facts.value("hp_max", 100.0f);
        const float hp = facts.value("hp", 100.0f);
        in.player.health = hp;
        in.player.healthPermanent = hpMax;
        in.player.healthMax = hpMax;
        in.player.magicka = facts.value("magicka", 100.0f);
        in.player.magickaMax = facts.value("magicka_max", 100.0f);
        in.player.interior = facts.value("interior", false);
        in.player.bloodthirst = facts.value("bloodthirst", false);
        in.self = essb::Self{ hp, hpMax, hpMax };
        essb::BodyInputs bin;
        bin.in = &in;
        bin.hitSneak = facts.value("sneak", false);
        bin.stamina = facts.value("stamina", 100.0f);
        bin.staminaMax = facts.value("stamina_max", 100.0f);
        bin.magicka = in.player.magicka;
        bin.magickaMax = in.player.magickaMax;
        ScriptRng rng;
        const std::string mode = facts.value("rng", std::string("mid"));
        rng.mode = mode == "yes" ? 1 : mode == "no" ? 2 : 0;
        *crowd = essb::Crowd{};
        SeedCrowd(*crowd, row.at("crowd"));
        in.body = crowd->m[0].body;
        essb::Board self;
        SeedBoard(self, row.at("me"));
        *plan = essb::StatusPlan{};
        for (const json& step : row.at("steps")) {
            const std::string op = step.at(0).get<std::string>();
            const int from = plan->count;
            if (op == "event") {
                essb::StatusOp e = essb::MakeOp(essb::Op::kEvent);
                e.event = EventOf(step.at(2).get<std::string>());
                for (std::size_t i = 3; i < step.size(); ++i) {
                    e.arg[i - 3] = step.at(i).get<float>();
                }
                e.at = static_cast<std::uint8_t>(step.at(1).get<int>());
                plan->Push(e);
                essb::RunBodies(*plan, from, *crowd, self, bin, nodes, rng);
            } else if (op == "op") {
                const std::string kind = step.at(2).get<std::string>();
                essb::StatusOp o{};
                if (kind == "resonance") {
                    o = essb::MakeOp(essb::Op::kResonance, essb::Who::kPlayer);
                } else if (kind == "crush") {
                    o = essb::MakeOp(essb::Op::kCrushArea);
                    o.magnitude = step.at(3).get<float>();
                    o.seconds = step.at(4).get<float>();
                } else if (kind == "freezeNearby") {
                    o = essb::MakeOp(essb::Op::kFreezeNearby, essb::Who::kPlayer);
                } else if (kind == "starBurst" || kind == "darkStrike") {
                    o = essb::Amount(essb::Op::kDamage, step.at(3).get<float>(), essb::kAstral);
                    o.arg[0] = kind == "starBurst" ? essb::tag::kStarBurst : essb::tag::kDarkStrike;
                } else {
                    throw std::runtime_error(name + ": unknown op " + kind);
                }
                o.at = static_cast<std::uint8_t>(step.at(1).get<int>());
                plan->Push(o);
                essb::RunBodies(*plan, from, *crowd, self, bin, nodes, rng);
            } else if (op == "burst") {
                essb::PlanBurst(*plan, *crowd, self, bin, step.at(1).get<int>(), step.at(2).get<int>(), nodes, rng);
            } else if (op == "death") {
                const json& f = step.at(1);
                essb::DeathFacts d;
                d.killerYou = f.value("killer_you", false);
                d.killerFrenzied = f.value("killer_frenzied", false);
                d.servant = f.value("servant", false);
                d.curseCap = f.value("curse_cap", 5);
                essb::PlanDeath(*plan, *crowd, self, bin, d, nodes, rng);
            } else if (op == "advent") {
                essb::PlanAdvent(*plan, *crowd, self, bin, step.at(1).get<int>(), nodes, rng);
            } else if (op == "echo") {
                essb::PlanEcho(*plan, *crowd, step.at(1).get<int>(), step.at(2).get<float>(), in, nodes);
            } else if (op == "hitBodies") {
                essb::PlanHitBodies(*plan, *crowd, self, bin, step.at(1).get<int>(), step.at(2).get<bool>(), step.at(3).get<int>(), nodes, rng);
                essb::RunBodies(*plan, from, *crowd, self, bin, nodes, rng);
            } else if (op == "surge") {
                essb::PlanSurge(*plan, *crowd, self, bin, step.at(1).get<int>(), step.at(2).get<int>(), nodes, rng);
                essb::RunBodies(*plan, from, *crowd, self, bin, nodes, rng);
            } else if (op == "avatar") {
                essb::PlanAvatarBurst(*plan, *crowd, self, bin, step.at(1).get<int>(), nodes, rng);
                essb::RunBodies(*plan, from, *crowd, self, bin, nodes, rng);
            } else {
                throw std::runtime_error(name + ": unknown step " + op);
            }
            Check(!plan->overflow, name + ": plan overflow");
        }
        std::vector<Row> ops;
        for (int i = 0; i < plan->count; ++i) {
            if (auto r = RowOf(plan->ops[i])) {
                ops.push_back(*r);
            }
        }
        const json& expect = row.at("expect");
        const json& members = expect.at("members");
        Check(static_cast<int>(members.size()) == crowd->count, name + ": member count");
        for (int k = 0; k < crowd->count; ++k) {
            CompareBoard(name + " (member " + std::to_string(k) + ")", crowd->m[k].board, members.at(k));
        }
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
    int checks = 0;
    for (const json& k : w.at("kinds")) {
        const StatusKind kind = KindOf(k.at("suffix").get<std::string>());
        const essb::StatusRecord& r = essb::kStatusRecords[static_cast<int>(kind)];
        Check(r.effect == k.at("effect").get<std::uint32_t>() && r.spell == k.at("spell").get<std::uint32_t>() &&
              r.onPlayer == k.at("on_player").get<bool>() && Near(r.seconds, k.at("seconds").get<double>()),
              k.at("suffix").get<std::string>() + ": record");
        // an AV kind (血承) keeps its record time: the override is its value
        const essb::Lowered l = essb::Lower([&] {
            essb::StatusOp op = essb::MakeOp(Op::kApply, r.onPlayer ? essb::Who::kPlayer : essb::Who::kTarget);
            op.kind = kind;
            op.magnitude = 3.0f;
            op.seconds = r.seconds;
            return op;
        }(), 70.0f);
        Check(l.spell == r.spell && l.dispelSpell == r.spell && Near(l.effectiveness, 1.0) && l.onPlayer == r.onPlayer,
              k.at("suffix").get<std::string>() + ": dispel then cast at the record time");
        checks += 2;
    }
    Check(w.at("timed_max").get<int>() == essb::kTimedMaxSeconds, "timed max seconds");
    int family = 0;
    for (const json& f : w.at("timed")) {
        const auto& spells = f.at("spells");
        for (int s = 1; s <= essb::kTimedMaxSeconds; ++s) {
            Check(essb::status::kTimed[family][s - 1] == spells.at(s - 1).get<std::uint32_t>(), f.at("name").get<std::string>() + ": id");
            const essb::Lowered l = essb::Lower(essb::TimedOp(family, 12.0f, static_cast<float>(s)), 70.0f);
            Check(l.spell == spells.at(s - 1).get<std::uint32_t>() && Near(l.magnitude, 12.0) && l.onPlayer == f.at("self").get<bool>(),
                  f.at("name").get<std::string>() + ": Lower of " + std::to_string(s) + " s");
            ++checks;
        }
        Check(essb::kTimedOnPlayer[family] == f.at("self").get<bool>(), "timed side");
        const essb::Lowered longer = essb::Lower(essb::TimedOp(family, 1.0f, 99.0f), 70.0f);
        Check(longer.spell == spells.at(essb::kTimedMaxSeconds - 1).get<std::uint32_t>(), "a longer body clamps to the longest spell");
        Check(essb::Lower(essb::TimedOp(family, 0.0f, 3.0f), 70.0f).spell == 0, "a 0 magnitude casts nothing");
        checks += 3;
        ++family;
    }
    Check(family == essb::kTimedKinds, "timed family count");
    essb::Lowered l = essb::Lower(essb::Amount(Op::kHush, 3.0f), 70.0f);
    Check(l.spell == w.at("hush").get<std::uint32_t>() && l.dispelSpell == l.spell && Near(l.magnitude, 3.0), "寂: dispel the old, cast the layers");
    l = essb::Lower(essb::Amount(Op::kHush, 0.0f), 70.0f);
    Check(l.spell == 0 && l.dispelSpell == w.at("hush").get<std::uint32_t>(), "寂 0: dispel only");
    Check(essb::TagOf(w.at("hush_effect").get<std::uint32_t>()).kind == essb::TagKind::kHush, "寂 effect tag");
    {
        essb::Board b;
        essb::Read(b, essb::RawEffect{ w.at("hush_effect").get<std::uint32_t>(), 4.0f, 1.0f, 10.0f });
        Check(b.hush.has && b.hush.Layers() == 4, "寂 read");
    }
    l = essb::Lower(essb::Amount(Op::kHealTarget, 10.0f), 70.0f);
    Check(l.spell == w.at("heal_target").get<std::uint32_t>() && !l.onPlayer, "聖光 heals the ally (a target cast)");
    l = essb::Lower(essb::Amount(Op::kDrainMagicka, 7.0f), 70.0f);
    Check(l.spell == w.at("drain_magicka").get<std::uint32_t>() && Near(l.magnitude, 7.0), "drain magicka");
    for (int s = 1; s <= essb::kSilenceSpellCount; ++s) {
        l = essb::Lower(essb::Amount(Op::kSilence, 0.0f, 0, static_cast<float>(s)), 70.0f);
        Check(l.spell == w.at("silence").at(s - 1).get<std::uint32_t>() && l.magnitude == 0.0f, "封印 silence " + std::to_string(s));
        ++checks;
    }
    Check(essb::Lower(essb::MakeOp(Op::kNoop), 70.0f).spell == 0, "a consumed body casts nothing");
    Check(w.at("engaged").get<std::uint32_t>() == essb::effect::kEngaged, "engaged effect (2.9 你主動攻擊過的目標)");
    Check(w.at("reanimate").get<std::uint32_t>() == essb::effect::kReanimate, "reanimate effect (亡衛)");
    Check(w.at("tuning").at("frostOpenSlowPct").get<std::uint32_t>() == essb::glob::kFrostOpenSlowPct, "tuning ESSB_FrostOpenSlowPct");
    Check(w.at("tuning").at("waterOpenStamina").get<std::uint32_t>() == essb::glob::kWaterOpenStamina, "tuning ESSB_WaterOpenStamina");
    // every spell a body can cast is on the list the DLL resolves at load
    const auto cast = essb::engine::CastSpells();
    auto listed = [&](std::uint32_t id) { return std::find(cast.begin(), cast.end(), id) != cast.end(); };
    Check(listed(w.at("hush").get<std::uint32_t>()) && listed(w.at("heal_target").get<std::uint32_t>()) &&
          listed(w.at("drain_magicka").get<std::uint32_t>()), "the bodies' spells are resolved at load");
    for (const json& f : w.at("timed")) {
        for (const json& id : f.at("spells")) {
            Check(listed(id.get<std::uint32_t>()), "a timed spell is resolved at load");
        }
    }
    for (const json& id : w.at("silence")) {
        Check(listed(id.get<std::uint32_t>()), "a silence is resolved at load");
    }
    const auto tagged = essb::engine::TaggedEffects();
    Check(std::find(tagged.begin(), tagged.end(), w.at("hush_effect").get<std::uint32_t>()) != tagged.end(), "寂 is a tagged effect");
    return checks + 16;
}

// ---------------------------------------------------------------- group X

int GroupX()
{
    int checks = 0;
    Check(Near(essb::Distance({ 0, 0, 0 }, { 3, 4, 0 }), 5.0) && Near(essb::Distance({ 1, 1, 1 }, { 1, 1, 1 }), 0.0) &&
          Near(essb::Distance({ 0, 0, 0 }, { 700, 0, 2400 }), 2500.0), "Distance");
    ++checks;
    auto crowd = std::make_unique<essb::Crowd>();
    crowd->count = 6;
    crowd->you = { 0, 0, 0 };
    const float xs[6] = { 0, 300, 100, 1000, 200, 50 };
    for (int k = 0; k < 6; ++k) {
        crowd->m[k].has = true;
        crowd->m[k].pos = { xs[k], 0, 0 };
    }
    crowd->m[4].ally = true;   // an ally is never picked
    crowd->m[5].has = false;   // an empty slot is never picked
    const essb::Picked p = essb::Around(*crowd, 0, 1050.0f, 5);
    Check(p.n == 3 && p.k[0] == 2 && p.k[1] == 1 && p.k[2] == 3, "Around: nearest first, not the centre, no ally, no empty");
    const essb::Picked q = essb::Around(*crowd, 0, 1050.0f, 2);
    Check(q.n == 2 && q.k[0] == 2 && q.k[1] == 1, "Around: the limit");
    const essb::Picked r = essb::Around(*crowd, 0, 250.0f, 5);
    Check(r.n == 1 && r.k[0] == 2, "Around: the radius");
    const essb::Picked s = essb::Around(*crowd, essb::kAroundYou, 150.0f, 5);
    Check(s.n == 2 && s.k[0] == 0 && s.k[1] == 2, "Around you: member 0 counts");
    checks += 4;
    auto plan = std::make_unique<essb::StatusPlan>();
    plan->at = 3;
    plan->Push(essb::Amount(essb::Op::kDamage, 1.0f, essb::kFire));
    essb::StatusOp own = essb::Amount(essb::Op::kDamage, 1.0f, essb::kFire);
    own.at = 2;
    plan->Push(own);
    Check(plan->ops[0].at == 3 && plan->ops[1].at == 2, "StatusPlan::Push stamps `at` unless the op has one");
    ++checks;
    Check(essb::BodyOnly(essb::Event::kDischarge) && essb::BodyOnly(essb::Event::kOverheat) && !essb::BodyOnly(essb::Event::kEnd) &&
          !essb::BodyOnly(essb::Event::kPush) && !essb::BodyOnly(essb::Event::kHallucinate), "BodyOnly");
    ++checks;
    MapNodes none;
    Check(Near(essb::BurstRadius(none), 1050.0), "融斷 15 m");
    MapNodes gather;
    gather.branches.insert({ essb::node::kNoFormGather.tree, essb::node::kNoFormGather.route, essb::node::kNoFormGather.tier,
        essb::node::kNoFormGather.index });
    gather.ranks[{ essb::node::kNoFormBurstRadius.tree, essb::node::kNoFormBurstRadius.route, essb::node::kNoFormBurstRadius.tier }] = 10;
    Check(Near(essb::BurstRadius(gather), 1400.0 + 210.0), "收束 20 m + 0.3 m × 10");
    essb::Tuning t;
    Check(Near(essb::BurstMult(0, t, none), 1.0) && Near(essb::BurstMult(1, t, none), 1.5) && Near(essb::BurstMult(2, t, none), 2.0) &&
          Near(essb::BurstMult(3, t, none), 3.0), "K_sync 1 / 1.5 / 2 / 3");
    checks += 3;
    // 火浴 (C3 redo, v0.4 5.3): 白熱 fixes the count at the first second (3 burning, lasting 白熱's 6.5 s left); every later
    // second heals B_max(火) 12 × 0.1 × 3 = 3.6 (× MultRecovery 1.5 = 5.4), whatever the count does later.
    {
        essb::Tuning rt;
        rt.multRecovery = 1.5f;
        essb::Board me;
        me[StatusKind::kHeat3] = essb::Slot{ true, 0.0f, 1.5f, 8.0f };
        auto bath = std::make_unique<essb::StatusPlan>();
        essb::PlanFireBath(*bath, me, 3, 12.0f, rt);
        Check(me.Has(StatusKind::kFireBath) && Near(me[StatusKind::kFireBath].magnitude, 3.0) && Near(me[StatusKind::kFireBath].Remaining(), 6.5) &&
              bath->count == 1 && bath->ops[0].op == essb::Op::kApply, "火浴: the first second fixes the count for 白熱's rest");
        *bath = essb::StatusPlan{};
        essb::PlanFireBath(*bath, me, 7, 12.0f, rt);
        Check(bath->count == 1 && bath->ops[0].op == essb::Op::kHeal && Near(bath->ops[0].magnitude, 5.4), "火浴: 12 × 0.1 × 3 × 1.5 a second");
        essb::Board cold;
        *bath = essb::StatusPlan{};
        essb::PlanFireBath(*bath, cold, 3, 12.0f, rt);
        Check(bath->count == 0 && !cold.Has(StatusKind::kFireBath), "火浴: nothing below 白熱");
        checks += 3;
    }
    return checks;
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 3) {
            std::cerr << "usage: reaction_test <fix24-body-table.json> <fix24-wiring.json>\n";
            return 2;
        }
        const auto [scenarios, ops] = GroupR(Load(argv[1]));
        std::printf("NATIVE BODY R ok: %d scenarios, %d expected ops matched exactly (every member's board compared)\n", scenarios, ops);
        const int wiring = GroupW(Load(argv[2]));
        std::printf("NATIVE BODY W ok: %d wiring checks (round-24 kinds, timed families, 寂, ally heal, silences, crowd forms)\n", wiring);
        const int direct = GroupX();
        std::printf("NATIVE BODY X ok: %d direct checks (Distance, Around, at stamping, BodyOnly, burst radius and K_sync, 火浴)\n", direct);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "BODY TEST FAILED: %s\n", e.what());
        return 1;
    }
}
