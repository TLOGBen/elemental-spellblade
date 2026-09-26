// Round 23 (N4) offline tests of your own resources and the hits you take (SelfLayer.h, Hurt.h and the N4 parts of
// Status.h).
//   S  scenarios: every row of build/fix23-self-table.json -- your board and the target's (the attacker's for a hurt)
//      before, the owned nodes, a list of steps (element hits with the self part, forced opens, no-form hits, ends, form
//      leave / enter, the per-second decay, resonance, hurts, enemy casts) -- run through the planners here; the boards
//      afterwards and every non-status op must equal what build/fix23_reference.py (written from the v0.4 text) computed.
//      Random draws follow the row's mode: 'mid' (a chance p succeeds when p >= 0.5, a real draw is the midpoint),
//      'yes' (every chance succeeds, a real draw is its low end), 'no' (none succeeds, the high end)
//   W  wiring: build/fix23-wiring.json (the generator's identities) -> the mirror globals, the new ops' Lower (which spell
//      is cast / dispelled), the 護血 pool's tag and read, the AV kinds
//   X  direct checks: 化身's node wrapper, 多段觸發's count, the blood power cost curve, the pools' share rules
// Injected faults (build/fix23_verify.py) mutate the table and require this binary to fail.
#include "Hurt.h"

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

// The row's draw mode (the reference model draws the same way).
struct ScriptRng {
    int mode = 0;   // 0 mid, 1 yes, 2 no
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return mode == 1 ? lo : mode == 2 ? hi : lo + (hi - lo) * 0.5f; }
    bool Chance(float probability) { return mode == 1 ? true : mode == 2 ? false : probability >= 0.5f; }
};

std::string SuffixOf(int kind)
{
    const std::string_view id = essb::kStatusRecords[kind].editorId;
    constexpr std::string_view n3 = "ESSB_N3_";
    constexpr std::string_view n4 = "ESSB_N4_";
    Check(id.starts_with(n3) || id.starts_with(n4), "status record without the ESSB_N3_ / ESSB_N4_ prefix");
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
    "Discharge", "Blade", "Knock", "SyncUp", "Cleanse", "Lethal" };
const int kEventArgs[] = { 4, 8, 1, 2, 1, 1, 1, 1, 0, 4, 2, 1, 1, 1, 0 };   // End: arg 7 = the charges (N4)
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
    case Op::kResonance: return Row{ "resonance", {} };
    case Op::kInterrupt: return Row{ "interrupt", {} };
    case Op::kSpendMagicka: return Row{ "spendMagicka", { op.magnitude } };
    case Op::kPayStamina: return Row{ "payStamina", { op.magnitude } };
    case Op::kHurtHealth: return Row{ "hurtHealth", { op.magnitude } };
    case Op::kDrainStamina: return Row{ "drainStamina", { op.magnitude } };
    case Op::kRiposte: return Row{ "riposte", {} };
    case Op::kDispelMarkOn: return Row{ "dispelMark", {} };
    case Op::kBloodGuardPool: return Row{ "guardPool", { op.magnitude } };
    case Op::kCrushArea: return Row{ "crush", { op.magnitude, op.seconds } };
    case Op::kFreezeNearby: return Row{ "freezeNearby", {} };
    case Op::kEvent: {
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
    if (b.guardPool.has) {
        out["GuardPool"] = { b.guardPool.magnitude, 0.0 };
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
        } else if (kind == "GuardPool") {
            board.guardPool = slot;
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
    t.syncT = { tu.value("syncT1", 5), tu.value("syncT2", 15), tu.value("syncT3", 30) };
    t.level.fill(1.0f);
    for (const auto& lv : row.at("levels")) {
        t.level[lv.at(0).get<int>()] = lv.at(1).get<float>();
    }
}

essb::HurtFacts HurtOf(const json& f)
{
    essb::HurtFacts h;
    h.attacker = f.value("attacker", false);
    h.melee = f.value("melee", false);
    h.spell = f.value("spell", false);
    h.destructive = f.value("destructive", false);
    h.blocked = f.value("blocked", false);
    h.cloakTick = f.value("cloak", false);
    h.afterimage = f.value("afterimage", false);
    h.linger = f.value("linger", false);
    h.healthBefore = f.value("before", 100.0f);
    h.magickaBefore = f.value("magicka_before", 0.0f);
    h.overloadBefore = f.value("overload_before", 0.0f);
    h.guardBefore = f.value("guard_before", 0.0f);
    h.guardLeft = f.value("guard_left", -1.0f);
    h.healthAfter = f.value("after", 100.0f);
    h.dotDamage = f.value("dot_damage", 0.0f);
    h.magicka = f.value("magicka", 0.0f);
    h.magickaMax = f.value("magicka_max", 100.0f);
    h.stamina = f.value("stamina", 100.0f);
    return h;
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
        in.n4 = true;
        in.formElement = facts.value("form", 0);
        const float hpMax = facts.value("hp_max", 100.0f);
        float hp = facts.value("hp", 100.0f);
        const float magickaMax = facts.value("magicka_max", 100.0f);
        in.player.healthPermanent = hpMax;
        in.player.healthMax = hpMax;
        in.body.health = body.value("health", 100.0f);
        in.body.healthMax = body.value("health_max", 100.0f);
        in.body.stamina = body.value("stamina", 100.0f);
        in.body.staminaMax = body.value("stamina_max", 100.0f);
        in.body.vip = body.value("vip", false);
        in.body.undeadOrDaedra = body.value("undead", false);
        ScriptRng rng;
        const std::string mode = facts.value("rng", std::string("mid"));
        rng.mode = mode == "yes" ? 1 : mode == "no" ? 2 : 0;
        essb::Board target;
        essb::Board self;
        Seed(target, self, row);
        std::vector<Row> ops;
        for (const json& step : row.at("steps")) {
            in.player.health = hp;
            in.self = essb::Self{ hp, hpMax, hpMax };
            const std::string op = step.at(0).get<std::string>();
            essb::StatusPlan plan;
            if (op == "hit") {
                const int element = step.at(1).get<int>();
                const bool power = step.at(2).get<bool>();
                const json o = step.size() > 3 ? step.at(3) : json::object();
                essb::SelfHit hit;
                hit.element = element;
                hit.formElement = in.formElement;
                hit.power = power;
                hit.sneak = o.value("sneak", false);
                hit.crit = o.value("crit", false);
                hit.targetCasting = o.value("casting", false);
                if (element == essb::kBlood && power) {
                    essb::StatusTerms terms;
                    hit.bloodCost = essb::BloodPowerTerms(element, power, o.value("real", power), in.self, self, nodes, terms, hit.surgeUp);
                    ops.push_back(Row{ "blood", { hit.bloodCost, terms.mult[essb::kBlood], terms.flat[essb::kBlood] } });
                }
                const essb::HitStatus st = essb::PlanStatusHit(plan, element, power, target, self, in, nodes, rng);
                const essb::SelfResult result = essb::PlanSelfHit(plan, hit, st, target, self, in, nodes, rng);
                ops.push_back(Row{ "result", { result.extraProc ? 1.0 : 0.0, static_cast<double>(result.repeats) } });
                if (o.value("repeat", false)) {
                    essb::StatusInputs again = in;
                    again.repeat = true;
                    for (int i = 0; i < result.repeats; ++i) {
                        const essb::HitStatus r = essb::PlanStatusHit(plan, element, power, target, self, again, nodes, rng);
                        essb::PlanSelfHit(plan, hit, r, target, self, again, nodes, rng, true);
                    }
                }
            } else if (op == "open") {
                essb::PlanSelfOpen(plan, step.at(1).get<int>(), target, self, in, nodes, rng);
            } else if (op == "nohit") {
                const json& o = step.at(1);
                essb::Plan hitPlan;
                hitPlan.silenced = o.value("silenced", false);
                hitPlan.breakUsed = o.value("broke", false);
                hitPlan.overloadAfter = o.value("overload_after", -1.0f);
                essb::SelfHit hit;
                hit.targetCasting = o.value("casting", false);
                hit.sneak = o.value("sneak", false);
                essb::PlanSelfNoForm(plan, hitPlan, hit, target, self, in, nodes, rng.Real(0.0f, 1.0f));
            } else if (op == "leave") {
                essb::OnFormLeave(plan, step.at(1).get<int>(), step.at(2).get<bool>(), self, in, nodes);
                essb::PlanSelfLeave(plan, step.at(1).get<int>(), step.at(2).get<bool>(), self, in, nodes);
            } else if (op == "enter") {
                essb::PlanSelfEnter(plan, step.at(1).get<int>(), self, in, nodes);
            } else if (op == "second") {
                essb::PlanSelfSecond(plan, self, magickaMax, in, nodes);
            } else if (op == "resonance") {
                essb::OnResonance(plan, self, step.at(1).get<int>(), in, nodes);
            } else if (op == "sync") {
                essb::res::SetSync(plan, self, std::max(0, step.at(1).get<int>()), in, nodes, step.at(2).get<bool>());
            } else if (op == "end") {
                essb::PlanEnd(plan, step.at(1).get<int>(), static_cast<essb::EndReason>(step.at(2).get<int>()),
                    step.at(3).get<float>(), false, target, self, in, nodes, rng);
            } else if (op == "hurt") {
                const essb::HurtFacts f = HurtOf(step.at(1));
                hp = f.healthAfter;
                in.player.health = hp;
                in.self = essb::Self{ hp, hpMax, hpMax };
                essb::PlanHurt(plan, f, target, self, in, nodes, rng);
            } else if (op == "cast") {
                essb::CastFacts f;
                f.hostileNear = step.at(1).get<bool>();
                f.marked = step.at(2).get<bool>();
                f.cost = step.at(3).get<float>();
                f.trueMult = step.at(4).get<float>();
                essb::PlanSpellCast(plan, f, self, in, nodes);
            } else if (op == "age") {
                Age(target, step.at(1).get<float>());
                Age(self, step.at(1).get<float>());
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
    int checks = 0;
    // The mirror globals the DLL writes (ESSB_Sync etc., read by PERK conditions) are the generator's records.
    const json& m = w.at("mirrors");
    Check(m.at("ESSB_Sync").get<std::uint32_t>() == essb::glob::kSync, "mirror ESSB_Sync");
    Check(m.at("ESSB_SyncStage").get<std::uint32_t>() == essb::glob::kSyncStage, "mirror ESSB_SyncStage");
    Check(m.at("ESSB_Charge").get<std::uint32_t>() == essb::glob::kCharge, "mirror ESSB_Charge");
    Check(m.at("ESSB_Resolve").get<std::uint32_t>() == essb::glob::kResolve, "mirror ESSB_Resolve");
    Check(m.at("ESSB_IceShield").get<std::uint32_t>() == essb::glob::kIceShield, "mirror ESSB_IceShield");
    Check(m.at("ESSB_RockArmor").get<std::uint32_t>() == essb::glob::kRockArmor, "mirror ESSB_RockArmor");
    Check(m.at("ESSB_Wind").get<std::uint32_t>() == essb::glob::kWind, "mirror ESSB_Wind");
    Check(m.at("ESSB_Bracing").get<std::uint32_t>() == essb::glob::kBracing, "mirror ESSB_Bracing");
    checks += 8;
    // The new ops' casts.
    auto lower = [](Op op, float magnitude) { return essb::Lower(essb::Amount(op, magnitude), 70.0f); };
    essb::Lowered l = lower(Op::kSpendMagicka, 9.0f);
    Check(l.spell == w.at("spend_magicka").get<std::uint32_t>() && Near(l.magnitude, 9.0), "spend magicka spell");
    Check(lower(Op::kSpendMagicka, 0.0f).spell == 0, "spend magicka 0 casts nothing");
    l = lower(Op::kDrainStamina, 26.25f);
    Check(l.spell == w.at("drain_stamina").get<std::uint32_t>() && Near(l.magnitude, 26.25), "drain stamina spell");
    l = essb::Lower(essb::MakeOp(Op::kRiposte, essb::Who::kPlayer), 70.0f);
    Check(l.spell == w.at("riposte").get<std::uint32_t>() && l.dispelSpell == l.spell, "riposte: dispel then cast");
    l = essb::Lower(essb::MakeOp(Op::kDispelMarkOn), 70.0f);
    Check(l.spell == w.at("dispel_mark").get<std::uint32_t>(), "咒返 casts the 滅法印 spell");
    l = lower(Op::kBloodGuardPool, 12.0f);
    Check(l.spell == w.at("guard_spell").get<std::uint32_t>() && l.dispelEffect == w.at("guard_effect").get<std::uint32_t>() &&
          Near(l.magnitude, 12.0), "護血 pool: dispel the old, cast the new");
    l = lower(Op::kBloodGuardPool, 0.0f);
    Check(l.spell == 0 && l.dispelEffect == w.at("guard_effect").get<std::uint32_t>(), "護血 pool 0: dispel only");
    for (const Op engine : { Op::kPayStamina, Op::kHurtHealth, Op::kResonance, Op::kInterrupt, Op::kCrushArea, Op::kFreezeNearby }) {
        const essb::Lowered e = lower(engine, 3.0f);
        Check(e.spell == 0 && e.dispelSpell == 0 && e.dispelEffect == 0, "an engine op casts nothing");
        ++checks;
    }
    checks += 7;
    // The 護血 pool is read from its effect.
    {
        const std::uint32_t guard = w.at("guard_effect").get<std::uint32_t>();
        Check(essb::TagOf(guard).kind == essb::TagKind::kGuardPool, "護血 effect tag");
        essb::Board b;
        essb::Read(b, essb::RawEffect{ guard, 17.0f, 1.0f, 86400.0f });
        Check(b.guardPool.has && Near(b.guardPool.magnitude, 17.0), "護血 pool read");
        checks += 2;
    }
    // The N4 kinds: the generator's rows, AV kinds carry a real magnitude and keep their record time.
    int n4 = 0;
    for (const json& k : w.at("kinds")) {
        const StatusKind kind = KindOf(k.at("suffix").get<std::string>());
        const essb::StatusRecord& r = essb::kStatusRecords[static_cast<int>(kind)];
        Check(r.effect == k.at("effect").get<std::uint32_t>() && r.spell == k.at("spell").get<std::uint32_t>() &&
              r.onPlayer == k.at("on_player").get<bool>() && Near(r.seconds, k.at("seconds").get<double>()),
              k.at("suffix").get<std::string>() + ": record");
        ++n4;
    }
    Check(n4 > 0, "no N4 kinds in the wiring");
    return checks + n4;
}

// ---------------------------------------------------------------- group X

int GroupX()
{
    int checks = 0;
    // 化身: the current form's sustain legend main line reads full, nothing else changes.
    MapNodes plain;
    essb::Board me;
    me[StatusKind::kAvatar] = essb::Slot{ true, static_cast<float>(essb::kEarth), 1.0f, 10.0f };
    const auto avatar = essb::WithAvatar(plain, me);
    Check(avatar.Rank(essb::node::kSustainLegend[essb::kEarth]) == essb::kMainMaxRank, "化身 reads the legend line full");
    Check(avatar.Rank(essb::node::kSustainLegend[essb::kWind]) == 0, "化身 only the form's element");
    essb::Board none;
    Check(essb::WithAvatar(plain, none).Rank(essb::node::kSustainLegend[essb::kEarth]) == 0, "no window, no change");
    checks += 3;
    // 多段觸發: 2 in all, +1 a 5 points, at most 5.
    essb::HitStatus cut;
    cut.cutFrom = essb::kWind;
    MapNodes multi;
    Check(essb::MultiTriggerRepeats(cut, multi) == 1, "多段觸發 base 2 = 1 repeat");
    multi.ranks[{ essb::node::kWindMulti.tree, essb::node::kWindMulti.route, essb::node::kWindMulti.tier }] = 25;
    Check(essb::MultiTriggerRepeats(cut, multi) == 4, "多段觸發 caps at 5");
    cut.cutFrom = essb::kFire;
    Check(essb::MultiTriggerRepeats(cut, multi) == 0, "only a wind cut repeats");
    checks += 3;
    // 1.1: the blood power cost at the curve's points.
    Check(Near(essb::res::BloodPowerCostFraction(1.0f), 0.08) && Near(essb::res::BloodPowerCostFraction(0.7f), 0.05) &&
          Near(essb::res::BloodPowerCostFraction(0.5f), 0.035) && Near(essb::res::BloodPowerCostFraction(0.3f), 0.02) &&
          Near(essb::res::BloodPowerCostFraction(0.1f), 0.0) && Near(essb::res::BloodPowerCostFraction(0.05f), 0.0),
          "blood power cost curve");
    ++checks;
    // The pools' share: a non-destructive spell is not shared; the physical half always is.
    essb::Config c;
    essb::Tuning t;
    essb::StatusInputs in;
    in.config = &c;
    in.tuning = &t;
    in.formElement = essb::kWater;
    essb::HurtFacts f;
    f.spell = true;
    f.magickaBefore = 50.0f;
    Check(essb::hurt::ShareOf(f, me, in, plain).share == 0.0f, "水幕 skips a non-destructive spell");
    f.destructive = true;
    Check(Near(essb::hurt::ShareOf(f, me, in, plain).share, 0.2), "水幕 takes a destructive spell");
    in.formElement = 0;
    f.magickaBefore = 0.0f;
    Check(essb::hurt::ShareOf(f, me, in, plain).share == 0.0f, "法盾 needs magicka or overload");
    checks += 3;
    return checks;
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 3) {
            std::cerr << "usage: self_test <fix23-self-table.json> <fix23-wiring.json>\n";
            return 2;
        }
        const auto [scenarios, ops] = GroupS(Load(argv[1]));
        std::printf("NATIVE SELF S ok: %d scenarios, %d expected ops matched exactly (boards compared after every row)\n", scenarios, ops);
        const int wiring = GroupW(Load(argv[2]));
        std::printf("NATIVE SELF W ok: %d wiring checks (mirrors, new ops' Lower, the 護血 pool, the N4 records)\n", wiring);
        const int direct = GroupX();
        std::printf("NATIVE SELF X ok: %d direct checks (化身, 多段觸發, blood cost curve, pool shares)\n", direct);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "SELF TEST FAILED: %s\n", e.what());
        return 1;
    }
}
