// Round 25 (N6) offline tests of the DLL's per-second work, the domains' DLL halves and the hotkey decisions (Timer.h,
// the round-25 parts of Status.h / StatusEngine.h).
//   T  scenarios: every row of build/fix25-timer-table.json -- the clock (steps with the game running or stopped), a
//      form's second (維持費, 魔力歸零, 血形態, 長流 / 長河, 雷雨), the environment, the weather classes, who stands in which
//      domain, what the domains do to you and to an enemy, the domain spell's seconds, the slow test and the immunity, the
//      key codes, the hotkey slots, the input gate, the switch decision -- run through the DLL's functions; ops (with the
//      member they act on; -1 = you), outputs and boards must equal what build/fix25_reference.py (from the v0.4 text)
//      computed
//   W  wiring: build/fix25-wiring.json (the generator's identities) -> the round-25 kinds, the domains' HAZD / Spawn
//      Hazard / spawn spells in ManifestData.h, CastSpells, Lower of the ally stamina, the globals the timer reads
//      (ReadTimerTuning through a fake global table), the hotkey and mirror globals, the upkeep settings
//   X  fake engine: a fake timer (100 ms steps, a 30 s pause, a load that resets the clock) through Step; fake input
//      events (key down / held, keyboard / mouse / gamepad, the console and a menu open) through the sink's decisions;
//      fake hazard casts: RunPlan of a fusion's ESSB_Domain event casts the element's spawn spell (no magnitude override)
//      on the member before the ModEvent, nothing for an element without a domain, the silence drains the magicka, 潮池
//      washes one buff of three
// Injected faults (build/fix25_verify.py) mutate the table and require this binary to fail.
#include "StatusEngine.h"
#include "Timer.h"

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
using essb::Who;

int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
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

    bool Has(const essb::BranchId& id) const { return branches.contains({ id.tree, id.route, id.tier, id.index }); }
};

MapNodes NodesOf(const json& row)
{
    MapNodes n;
    for (const auto& r : row.value("ranks", json::array())) {
        n.ranks[{ r.at(0).get<int>(), r.at(1).get<int>(), r.at(2).get<int>() }] = r.at(3).get<int>();
    }
    for (const auto& b : row.value("branches", json::array())) {
        n.branches.insert({ b.at(0).get<int>(), b.at(1).get<int>(), b.at(2).get<int>(), b.at(3).get<int>() });
    }
    return n;
}

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
    "Discharge", "Blade", "Knock", "SyncUp", "Cleanse", "Lethal", "Push", "Ash", "Raise", "Sneak", "Domain", "Overheat", "Switch",
    "Close" };
const int kEventArgs[] = { 4, 8, 1, 3, 2, 1, 1, 1, 0, 4, 2, 1, 1, 1, 0, 5, 0, 5, 1, 3, 0, 2, 0 };
static_assert(std::size(kEventNames) == static_cast<int>(essb::Event::kCount));
static_assert(std::size(kEventArgs) == static_cast<int>(essb::Event::kCount));

const char* kTreeIds[] = { "fire", "frost", "lightning", "earth", "wind", "blood", "divine", "poison", "water", "darkness", "astral",
    "noform", "common" };

// ---------------------------------------------------------------- rows

constexpr int kNoAt = -2;

struct Row {
    std::string name;
    int at = 0;
    std::vector<double> values;
};

std::optional<Row> RowOf(const essb::StatusOp& op, const essb::Tuning& t)
{
    using essb::Op;
    const int at = op.who == Who::kPlayer ? -1 : op.at;
    switch (op.op) {
    case Op::kSpendMagicka: return Row{ "spend", -1, { op.magnitude } };
    case Op::kPayHealth: return Row{ "pay", -1, { op.magnitude } };
    case Op::kHeal: return Row{ "heal", -1, { op.magnitude } };
    case Op::kRestoreMagicka: return Row{ "magicka", -1, { op.magnitude } };
    case Op::kRestoreStamina: return Row{ "stamina", -1, { op.magnitude } };
    case Op::kHealTarget: return Row{ "healTarget", op.at, { op.magnitude } };
    case Op::kStaminaTarget: return Row{ "staminaTarget", op.at, { op.magnitude } };
    case Op::kApply: return Row{ "apply:" + SuffixOf(static_cast<int>(op.kind)), at, { op.magnitude, op.seconds } };
    case Op::kRemove: return Row{ "remove:" + SuffixOf(static_cast<int>(op.kind)), at, {} };
    case Op::kSlow: return Row{ "slow", at, { essb::Lower(op, t.slowCapPct).magnitude, op.seconds } };
    case Op::kWash: return Row{ "wash", at, { static_cast<double>(op.element), op.magnitude } };
    case Op::kDamage: return Row{ "damage", at, { static_cast<double>(op.element), op.magnitude } };
    case Op::kPoisonDot: return Row{ "poisonDot", kNoAt, { op.magnitude, op.seconds } };
    case Op::kEvent: {
        const int e = static_cast<int>(op.event);
        Row row{ std::string("event:") + kEventNames[e], at, {} };
        for (int i = 0; i < kEventArgs[e]; ++i) {
            row.values.push_back(op.arg[i]);
        }
        return row;
    }
    default:
        return Row{ "unexpected op " + std::to_string(static_cast<int>(op.op)), at, {} };
    }
}

Row RowOf(const json& e)
{
    Row row;
    row.name = e.at(0).get<std::string>();
    std::size_t i = 1;
    if (row.name == "apply" || row.name == "remove") {
        row.name += ":" + e.at(1).get<std::string>();
        row.at = e.at(2).get<int>();
        i = 3;
    } else if (row.name == "event") {
        row.at = e.at(1).get<int>();
        row.name += ":" + e.at(2).get<std::string>();
        i = 3;
    } else if (row.name == "poisonDot") {
        row.at = kNoAt;
    } else {
        row.at = e.at(1).get<int>();
        i = 2;
    }
    for (; i < e.size(); ++i) {
        row.values.push_back(e.at(i).get<double>());
    }
    return row;
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

int CompareOps(const std::string& where, const essb::StatusPlan& plan, const essb::Tuning& t, const json& expected)
{
    std::vector<Row> have;
    for (int i = 0; i < plan.count; ++i) {
        if (const auto r = RowOf(plan.ops[i], t)) {
            have.push_back(*r);
        }
    }
    std::string list;
    for (const auto& r : have) {
        list += "\n    " + Text(r);
    }
    Check(have.size() == expected.size(), where + ": " + std::to_string(have.size()) + " ops, expected " + std::to_string(expected.size()) + list);
    for (std::size_t i = 0; i < have.size(); ++i) {
        const Row want = RowOf(expected.at(i));
        Check(Same(have[i], want), where + ": op " + std::to_string(i) + " is " + Text(have[i]) + ", expected " + Text(want));
    }
    return static_cast<int>(have.size());
}

void CompareBoard(const std::string& where, const essb::Board& b, const json& expected)
{
    std::map<std::string, std::pair<double, double>> have;
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        if (b.slot[k].has) {
            have[SuffixOf(k)] = { b.slot[k].magnitude, b.slot[k].Remaining() };
        }
    }
    for (const auto& [name, v] : expected.items()) {
        const auto it = have.find(name);
        Check(it != have.end(), where + ": expected " + name + " on you");
        Check(Near(it->second.first, v.at(0).get<double>()) && Near(it->second.second, v.at(1).get<double>()),
            where + ": " + name + " is " + std::to_string(it->second.first) + " / " + std::to_string(it->second.second));
    }
    for (const auto& [name, v] : have) {
        Check(expected.contains(name), where + ": unexpected " + name + " on you");
    }
}

void Seed(essb::Board& board, const json& statuses)
{
    for (const auto& [kind, v] : statuses.items()) {
        board[KindOf(kind)] = essb::Slot{ true, v.at(0).get<float>(), v.at(1).get<float>(), v.at(2).get<float>() };
    }
}

essb::Tuning TuningOf(const json& row)
{
    essb::Tuning t;
    const json tu = row.value("tuning", json::object());
    t.syncStage = tu.value("sync", 0);
    t.multDuration = tu.value("duration", 1.0f);
    t.multCooldown = tu.value("cooldown", 1.0f);
    t.baseDamageMult = tu.value("base", 1.0f);
    t.multRecovery = tu.value("recovery", 1.0f);
    t.multDot = tu.value("dot", 1.0f);
    t.envNight = tu.value("night", false);
    t.slowCapPct = tu.value("slow_cap", 70.0f);
    t.level.fill(1.0f);
    for (const auto& [tree, level] : row.value("levels", json::object()).items()) {
        const auto it = std::find(std::begin(kTreeIds), std::end(kTreeIds), tree);
        Check(it != std::end(kTreeIds), "unknown tree " + tree);
        t.level[static_cast<int>(it - std::begin(kTreeIds))] = level.get<float>();
    }
    return t;
}

essb::TimerTuning TimerTuningOf(const json& row)
{
    essb::TimerTuning tt;
    const json tu = row.value("tuning", json::object());
    tt.multUpkeep = tu.value("upkeep", 1.0f);
    tt.flowBasePct = tu.value("flow_base", 2.0f);
    tt.flowPerRankPct = tu.value("flow_per_rank", 0.2f);
    return tt;
}

// ---------------------------------------------------------------- group T

int RunScenario(const json& row, const essb::Config& config)
{
    const std::string name = row.at("name").get<std::string>();
    const std::string group = row.at("group").get<std::string>();
    const json& expect = row.at("expect");
    if (group == "cadence") {
        essb::Cadence c;
        const auto& steps = row.at("steps");
        const auto& beats = expect.at("beats");
        Check(steps.size() == beats.size(), name + ": beat count");
        for (std::size_t i = 0; i < steps.size(); ++i) {
            const essb::Beat b = essb::Step(c, steps[i].at(0).get<std::uint64_t>(), steps[i].at(1).get<bool>());
            Check((b.second ? 1 : 0) == beats[i].at(0).get<int>() && (b.env ? 1 : 0) == beats[i].at(1).get<int>() &&
                      Near(b.seconds, beats[i].at(2).get<double>()),
                name + ": step " + std::to_string(i) + " second=" + std::to_string(b.second) + " env=" + std::to_string(b.env) +
                    " seconds=" + std::to_string(b.seconds));
        }
        return static_cast<int>(steps.size());
    }
    if (group == "env") {
        const json& f = row.at("facts");
        essb::EnvFacts facts;
        facts.weather = f.at("weather").get<int>();
        facts.lightning = static_cast<std::uint8_t>(f.at("lightning").get<int>());
        facts.wind = static_cast<std::uint8_t>(f.at("wind").get<int>());
        facts.interior = f.at("interior").get<bool>();
        facts.swimming = f.at("swimming").get<bool>();
        facts.underwater = f.at("underwater").get<bool>();
        facts.hour = f.at("hour").get<float>();
        const essb::EnvFlags e = essb::Environment(facts);
        Check((e.wet ? 1 : 0) == expect.at("wet").get<int>() && (e.stormy ? 1 : 0) == expect.at("stormy").get<int>() &&
                  (e.thunder ? 1 : 0) == expect.at("thunder").get<int>() && (e.night ? 1 : 0) == expect.at("night").get<int>(),
            name);
        return 1;
    }
    if (group == "weather") {
        Check(essb::WeatherClass(static_cast<std::uint8_t>(row.at("flags").get<int>())) == expect.at("cls").get<int>(), name);
        return 1;
    }
    if (group == "inside") {
        std::array<essb::DomainSite, 8> sites{};
        int n = 0;
        for (const auto& s : row.at("sites")) {
            sites[n++] = essb::DomainSite{ s.at(0).get<int>(), { s.at(1).get<float>(), s.at(2).get<float>(), s.at(3).get<float>() } };
        }
        const auto& at = row.at("at");
        const essb::DomainSet in = essb::InsideOf(sites, n, { at.at(0).get<float>(), at.at(1).get<float>(), at.at(2).get<float>() });
        std::vector<int> have;
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            if (in[e]) {
                have.push_back(e);
            }
        }
        Check(have == expect.at("elements").get<std::vector<int>>(), name);
        return 1;
    }
    if (group == "spawn") {
        return 0;   // checked against the wiring in W (the spell ids come from the generator)
    }
    if (group == "slow") {
        const json& v = row.at("view");
        essb::SlowView view{ v.at("archetype").get<int>(), v.at("primary").get<int>(), v.at("secondary").get<int>(), v.at("detrimental").get<bool>(),
            v.at("duration").get<float>() };
        Check((essb::IsSlow(view) ? 1 : 0) == expect.at("slow").get<int>(), name);
        return 1;
    }
    if (group == "keycode") {
        Check(essb::KeyCodeOf(static_cast<essb::Device>(row.at("device").get<int>()), row.at("id").get<std::uint32_t>()) == expect.at("code").get<int>(),
            name);
        return 1;
    }
    if (group == "hotkey") {
        std::array<int, essb::kElementCount> keys{};
        for (int i = 0; i < essb::kElementCount; ++i) {
            keys[i] = row.at("keys").at(i).get<int>();
        }
        Check(essb::HotkeyElement(row.at("code").get<int>(), row.at("enabled").get<bool>(), keys) == expect.at("element").get<int>(), name);
        return 1;
    }
    if (group == "gate") {
        const json& g = row.at("gate");
        essb::InputGate gate{ g.at("paused").get<bool>(), g.at("menu").get<bool>(), g.at("console").get<bool>(), g.at("text").get<bool>(),
            g.at("loading").get<bool>() };
        Check((essb::InputOpen(gate) ? 1 : 0) == expect.at("open").get<int>(), name);
        return 1;
    }
    if (group == "switch") {
        const json& f = row.at("facts");
        essb::SwitchFacts facts;
        facts.enabled = f.at("enabled").get<bool>();
        facts.dead = f.at("dead").get<bool>();
        facts.active = f.at("active").get<bool>();
        facts.current = f.at("current").get<int>();
        facts.magicka = f.at("magicka").get<float>();
        facts.magickaMax = f.at("magicka_max").get<float>();
        facts.freePass = f.at("free_pass").get<bool>();
        facts.freeOpen = f.at("free_open").get<bool>();
        const essb::SwitchPlan p = essb::PlanSwitch(facts, row.at("wanted").get<int>());
        static const char* kinds[] = { "Ignore", "Refuse", "Open", "Switch", "Close" };
        const json& want = expect.at("plan");
        Check(kinds[static_cast<int>(p.kind)] == want.at(0).get<std::string>() && p.element == want.at(1).get<int>() &&
                  (p.consumeFree ? 1 : 0) == want.at(2).get<int>(),
            name + ": " + kinds[static_cast<int>(p.kind)] + " " + std::to_string(p.element));
        return 1;
    }
    // the planners over boards
    const MapNodes nodes = NodesOf(row);
    const essb::Tuning t = TuningOf(row);
    essb::StatusInputs in;
    in.config = &config;
    in.tuning = &t;
    in.n4 = true;
    in.player.interior = row.value("tuning", json::object()).value("interior", false);
    const json body = row.value("body", json::object());
    in.body.stamina = body.value("stamina", 100.0f);
    in.body.staminaMax = body.value("stamina_max", 100.0f);
    essb::Board me;
    Seed(me, row.value("me", json::object()));
    essb::Board target;
    Seed(target, row.value("target", json::object()));
    if (row.contains("poison")) {
        const auto& p = row.at("poison");
        target.poisonDot = essb::Slot{ true, p.at(0).get<float>(), p.at(1).get<float>(), p.at(2).get<float>() };
    }
    auto plan = std::make_unique<essb::StatusPlan>();
    int count = 0;
    if (group == "immune") {
        Check((essb::SlowImmune(me, t, nodes) ? 1 : 0) == expect.at("immune").get<int>(), name);
        return 1;
    }
    if (group == "form") {
        const json& f = row.at("facts");
        essb::SecondFacts facts;
        facts.form = f.at("form").get<int>();
        facts.magicka = f.at("magicka").get<float>();
        facts.magickaMax = f.at("magicka_max").get<float>();
        facts.health = f.at("health").get<float>();
        facts.healthMax = f.at("health_max").get<float>();
        facts.healthPermanent = f.at("health_permanent").get<float>();
        facts.stamina = f.at("stamina").get<float>();
        facts.staminaMax = f.at("stamina_max").get<float>();
        facts.thunder = f.at("thunder").get<bool>();
        std::array<essb::Ally, 5> allies{};
        int n = 0;
        for (const auto& a : row.at("allies")) {
            allies[n++] = essb::Ally{ a.at(0).get<int>(), a.at(1).get<float>(), a.at(2).get<float>() };
        }
        const essb::FormSecond out = essb::PlanFormSecond(*plan, me, facts, in, TimerTuningOf(row), nodes, allies, n);
        const json& o = expect.at("out");
        Check(Near(out.spent, o.at("spent").get<double>()) && Near(out.bled, o.at("bled").get<double>()) &&
                  Near(out.flow, o.at("flow").get<double>()) && (out.closing ? 1 : 0) == o.at("closing").get<int>() &&
                  (out.charged ? 1 : 0) == o.at("charged").get<int>(),
            name + ": outputs spent=" + std::to_string(out.spent) + " bled=" + std::to_string(out.bled) + " flow=" + std::to_string(out.flow));
    } else if (group == "domainSelf") {
        essb::DomainSet inside{};
        for (const auto& e : row.at("inside")) {
            inside[e.get<int>()] = true;
        }
        const essb::DomainSelf out = essb::PlanDomainSelf(*plan, me, inside, in, nodes);
        const json& o = expect.at("out");
        Check((out.fuseExtended ? 1 : 0) == o.at("fuse").get<int>() && (out.slowImmune ? 1 : 0) == o.at("immune").get<int>() &&
                  out.cleanse == o.at("cleanse").get<int>(),
            name + ": outputs");
    } else if (group == "domainEnemy") {
        essb::DomainSet inside{};
        for (const auto& e : row.at("inside")) {
            inside[e.get<int>()] = true;
        }
        const float refund = row.value("refund", false) ? 2.0f * config.damage[essb::kWater][1] : 0.0f;
        essb::PlanDomainEnemy(*plan, target, inside, in, me, nodes, refund);
        if (!expect.at("poison").is_null()) {
            Check(target.poisonDot.has && Near(target.poisonDot.magnitude, expect.at("poison").at(0).get<double>()) &&
                      Near(target.poisonDot.Remaining(), expect.at("poison").at(1).get<double>()),
                name + ": the poison afterwards");
        }
    } else {
        throw std::runtime_error("unknown group " + group);
    }
    Check(!plan->overflow, name + ": plan overflow");
    count += CompareOps(name, *plan, t, expect.at("ops"));
    CompareBoard(name, me, expect.at("me"));
    return count + 1;
}

// ---------------------------------------------------------------- group W

int Wiring(const json& w, const json& table)
{
    int n = 0;
    for (const auto& k : w.at("kinds")) {
        const StatusKind kind = KindOf(k.at("suffix").get<std::string>());
        const auto& r = essb::kStatusRecords[static_cast<int>(kind)];
        Check(r.effect == k.at("effect").get<std::uint32_t>() && r.spell == k.at("spell").get<std::uint32_t>() &&
                  Near(r.seconds, k.at("seconds").get<double>()) && r.onPlayer == k.at("on_player").get<bool>() && !r.stub,
            "W: kind " + k.at("suffix").get<std::string>());
        ++n;
    }
    Check(w.at("domain_max").get<int>() == essb::kDomainMaxSeconds, "W: kDomainMaxSeconds");
    std::set<int> withDomain;
    const auto cast = essb::engine::CastSpells();
    for (const auto& d : w.at("domains")) {
        const int e = d.at("element").get<int>();
        withDomain.insert(e);
        Check(essb::status::kDomainHazard[e] == d.at("hazard").get<std::uint32_t>() &&
                  essb::status::kDomainSpawnEffect[e] == d.at("spawn_effect").get<std::uint32_t>(),
            "W: domain records of element " + std::to_string(e));
        for (int s = 0; s < essb::kDomainMaxSeconds; ++s) {
            const std::uint32_t id = d.at("spawn").at(s).get<std::uint32_t>();
            Check(essb::status::kDomainSpawn[e][s] == id, "W: spawn spell " + std::to_string(e) + "/" + std::to_string(s + 1));
            Check(std::find(cast.begin(), cast.end(), id) != cast.end(), "W: the spawn spell is resolved at load (CastSpells)");
            n += 2;
        }
        // the hazard spell carries the marker the hit path reads (火域／冰原／星域) or this round's
        const std::uint32_t marker = d.at("effects").at(0).at(0).get<std::uint32_t>();
        Check(essb::TagOf(marker).kind == essb::TagKind::kStatus, "W: the hazard spell's first effect is a status marker");
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        if (!withDomain.contains(e)) {
            Check(essb::status::kDomainHazard[e] == 0 && essb::status::kDomainSpawn[e][0] == 0, "W: no domain for element " + std::to_string(e));
            essb::Tuning t;
            Check(essb::DomainSpawnSpell(e, 5.0f, t) == 0, "W: DomainSpawnSpell of an element without a domain");
        }
    }
    // the spawn scenarios: the whole seconds the model says, the spell the generator made for them
    for (const auto& row : table.at("scenarios")) {
        if (row.at("group") != "spawn") {
            continue;
        }
        essb::Tuning t;
        t.multDuration = row.at("mult").get<float>();
        const int element = row.at("element").get<int>();
        const int seconds = row.at("expect").at("seconds").get<int>();
        std::uint32_t want = 0;
        for (const auto& d : w.at("domains")) {
            if (d.at("element").get<int>() == element && seconds > 0) {
                want = d.at("spawn").at(seconds - 1).get<std::uint32_t>();
            }
        }
        Check(essb::DomainSpawnSpell(element, row.at("seconds").get<float>(), t) == want, "W: " + row.at("name").get<std::string>());
        ++n;
    }
    essb::StatusOp op = essb::Amount(essb::Op::kStaminaTarget, 12.0f);
    const essb::Lowered l = essb::Lower(op, 70.0f);
    Check(l.spell == w.at("stamina_target").get<std::uint32_t>() && !l.onPlayer && Near(l.magnitude, 12.0), "W: Lower(kStaminaTarget)");
    Check(std::find(cast.begin(), cast.end(), essb::spell::kStaminaTarget) != cast.end(), "W: the ally stamina spell is resolved");
    const json& g = w.at("globals");
    std::map<std::uint32_t, float> table2{ { g.at("multUpkeep").get<std::uint32_t>(), 1.75f }, { g.at("flowBase").get<std::uint32_t>(), 2.5f },
        { g.at("flowPerRank").get<std::uint32_t>(), 0.3f } };
    const essb::TimerTuning tt = essb::ReadTimerTuning([&](std::uint32_t id) {
        const auto it = table2.find(id);
        Check(it != table2.end(), "W: ReadTimerTuning reads an unknown global");
        return it->second;
    });
    Check(Near(tt.multUpkeep, 1.75) && Near(tt.flowBasePct, 2.5) && Near(tt.flowPerRankPct, 0.3), "W: ReadTimerTuning fields");
    Check(essb::glob::kEnvThunder == g.at("thunder").get<std::uint32_t>() && essb::glob::kFreeOpen == g.at("freeOpen").get<std::uint32_t>() &&
              essb::glob::kHotkeysEnabled == g.at("hotkeysEnabled").get<std::uint32_t>() &&
              essb::glob::kFormNotify == g.at("formNotify").get<std::uint32_t>(),
        "W: the 雷雨 / hotkey globals");
    for (int i = 0; i < essb::kElementCount; ++i) {
        Check(essb::glob::kHotkey[i] == g.at("hotkeys").at(i).get<std::uint32_t>(), "W: hotkey global " + std::to_string(i));
    }
    const auto& up = w.at("upkeep");
    Check(Near(essb::kUpkeepBasePct, up.at(0).get<double>()) && Near(essb::kUpkeepDarkPct, up.at(1).get<double>()) &&
              Near(essb::kUpkeepLevelRelief, up.at(2).get<double>()),
        "W: the upkeep settings");
    return n + 8;
}

// ---------------------------------------------------------------- group X: fake engine

struct FakeEngine {
    using Handle = int;
    std::vector<essb::engine::EffectView> list[2];
    std::vector<bool> alive[2];
    std::vector<std::string> log;
    bool self = false;
    std::uint8_t current = 0;
    static int Index(Who who) { return who == Who::kPlayer ? 1 : 0; }
    template <class Fn>
    void ForEach(Who who, Fn&& fn)
    {
        for (int i = 0; i < static_cast<int>(list[Index(who)].size()); ++i) {
            if (alive[Index(who)][i]) {
                fn(list[Index(who)][i], i);
            }
        }
    }
    template <class Fn>
    void ForEachIncludingEnding(Who who, Fn&& fn) { ForEach(who, fn); }
    void Dispel(Who who, Handle h) { alive[Index(who)][h] = false; log.push_back("dispel " + std::to_string(h)); }
    bool SelfDispel() const { return self; }
    void SetSelfDispel(bool on) { self = on; }
    void Cast(Who who, std::uint32_t spell, float magnitude, float effectiveness)
    {
        char buf[128];
        std::snprintf(buf, sizeof(buf), "cast %u on %s#%d mag %.3f eff %.3f", spell, who == Who::kPlayer ? "you" : "member",
            static_cast<int>(current), magnitude, effectiveness);
        log.push_back(buf);
    }
    bool Dead(Who) { return false; }
    void PayHealth(float) { log.push_back("pay"); }
    void Send(const essb::StatusOp& op) { log.push_back(std::string("event ") + kEventNames[static_cast<int>(op.event)]); }
    void LogWash(const essb::engine::EffectView&, bool) {}
    void LogReapply(const essb::StatusOp&, int) {}
    void PayStamina(float) {}
    void HurtHealth(float) {}
    void Resonance() {}
    void Interrupt(Who) {}
    void CrushArea(const essb::StatusOp&) {}
    void FreezeNearby() {}
    void DrainMagickaAll(Who who) { log.push_back(std::string("drain magicka ") + (who == Who::kPlayer ? "you" : "member")); }
    void Select(std::uint8_t at) { current = at; }
    void Add(Who who, essb::engine::EffectView v)
    {
        list[Index(who)].push_back(v);
        alive[Index(who)].push_back(true);
    }
};

int FakeEngineChecks()
{
    int n = 0;
    // 審查修正: the domain scan runs only with a domain node -- none, an unrelated node, then each of the ten alone.
    {
        MapNodes none;
        Check(!essb::HasDomainNode(none), "X: no node, no domain scan");
        MapNodes other;
        other.branches.insert({ essb::node::kCommonComposure.tree, essb::node::kCommonComposure.route, essb::node::kCommonComposure.tier,
            essb::node::kCommonComposure.index });
        Check(!essb::HasDomainNode(other), "X: 定神 is no domain node");
        for (const essb::BranchId& id : essb::kDomainNodes) {
            MapNodes one;
            one.branches.insert({ id.tree, id.route, id.tier, id.index });
            Check(essb::HasDomainNode(one), "X: a domain node starts the scan");
        }
        Check(essb::kDomainNodes.size() == 10, "X: ten domain nodes (聖域 and 神聖領域 both place 聖域)");
        n += 3;
    }
    essb::Tuning t;
    t.multDuration = 1.0f;
    // A fusion's domain event on member 3 (火域, 5 s): the spawn spell for 5 s, magnitude 0 (no override), before the event.
    {
        FakeEngine f;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::StatusOp op = essb::MakeEvent(essb::Event::kDomain, static_cast<float>(essb::kFire), 5.0f, 210.0f);
        op.at = 3;
        plan->Push(op);
        essb::engine::RunPlan(f, *plan, t);
        char want[128];
        std::snprintf(want, sizeof(want), "cast %u on member#3 mag 0.000 eff 1.000", essb::status::kDomainSpawn[essb::kFire][4]);
        Check(f.log.size() == 2 && f.log[0] == want && f.log[1] == "event Domain", "X: the domain is cast at the member's feet, then the event");
        ++n;
    }
    // 神聖領域 8 s at the duration slider 2.5 -> the 20 s spell; lightning (no domain) -> only the event.
    {
        FakeEngine f;
        auto plan = std::make_unique<essb::StatusPlan>();
        t.multDuration = 2.5f;
        plan->Push(essb::MakeEvent(essb::Event::kDomain, static_cast<float>(essb::kDivine), 8.0f, 210.0f));
        plan->Push(essb::MakeEvent(essb::Event::kDomain, static_cast<float>(essb::kLightning), 5.0f, 210.0f));
        essb::engine::RunPlan(f, *plan, t);
        char want[128];
        std::snprintf(want, sizeof(want), "cast %u on member#0 mag 0.000 eff 1.000", essb::status::kDomainSpawn[essb::kDivine][19]);
        Check(f.log.size() == 3 && f.log[0] == want && f.log[1] == "event Domain" && f.log[2] == "event Domain",
            "X: 8 s x2.5 = the 20 s spell; no spell for lightning");
        t.multDuration = 1.0f;
        ++n;
    }
    // The silence drains the magicka at once.
    {
        FakeEngine f;
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::StatusOp op = essb::MakeOp(essb::Op::kSilence);
        op.seconds = 2.0f;
        plan->Push(op);
        essb::engine::RunPlan(f, *plan, t);
        Check(f.log.size() == 2 && f.log[1] == "drain magicka member", "X: silence -> the cast, then the magicka to 0");
        ++n;
    }
    // 潮池: one buff of three washed a second (the wash's limit rides on `element`).
    {
        FakeEngine f;
        for (int i = 0; i < 3; ++i) {
            essb::engine::EffectView v;
            v.uid = 100 + i;
            v.hasSpell = true;
            v.spellType = essb::engine::kSpellTypeSpell;
            v.castingSource = essb::engine::kSourceRight;
            v.duration = 60.0f;
            v.elapsed = 1.0f;
            f.Add(Who::kTarget, v);
        }
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::StatusOp wash = essb::Amount(essb::Op::kWash, 0.0f);
        wash.element = 1;
        plan->Push(wash);
        essb::engine::RunPlan(f, *plan, t);
        const int left = static_cast<int>(std::count(f.alive[0].begin(), f.alive[0].end(), true));
        Check(left == 2, "X: 潮池 washes exactly one buff, " + std::to_string(3 - left) + " went");
        auto all = std::make_unique<essb::StatusPlan>();
        all->Push(essb::Amount(essb::Op::kWash, 0.0f));
        essb::engine::RunPlan(f, *all, t);
        Check(std::count(f.alive[0].begin(), f.alive[0].end(), true) == 0, "X: a wash without a limit takes the rest");
        n += 2;
    }
    // A fake timer: 100 ms steps; 1 s of play, a 30 s pause, a load (the clock starts again), 2 s of play.
    {
        essb::Cadence c;
        int seconds = 0;
        int envs = 0;
        std::uint64_t now = 5000;
        auto run = [&](int steps, bool stopped) {
            for (int i = 0; i < steps; ++i) {
                now += 100;
                const essb::Beat b = essb::Step(c, now, stopped);
                seconds += b.second ? 1 : 0;
                envs += b.env ? 1 : 0;
            }
        };
        run(11, false);
        Check(seconds == 1 && envs == 1, "X: 1 s of play -> one second, the environment at the start");
        run(300, true);
        Check(seconds == 1 && envs == 1 && c.active == 1000, "X: a 30 s pause counts nothing");
        c = essb::Cadence{};   // a load (Plugin.cpp OnGameReady)
        run(21, false);
        Check(seconds == 3 && envs == 2, "X: after a load: the clock restarts (2 s, the environment at once)");
        n += 3;
    }
    // Fake input events: (device, id, value, held, gate) -> the form the sink would switch to (0 none).
    {
        struct Press {
            essb::Device device;
            std::uint32_t id;
            float value;
            float held;
            bool console;
            bool menu;
            int want;
        };
        const std::array<int, essb::kElementCount> keys{ 79, 80, 81, 75, 76, 77, 71, 72, 73, 82, 276 };
        const Press presses[] = {
            { essb::Device::kKeyboard, 79, 1.0f, 0.0f, false, false, essb::kFire },        // numpad 1 down
            { essb::Device::kKeyboard, 79, 1.0f, 0.4f, false, false, 0 },                  // held: not a new press
            { essb::Device::kKeyboard, 79, 0.0f, 0.4f, false, false, 0 },                  // released
            { essb::Device::kKeyboard, 80, 1.0f, 0.0f, true, false, 0 },                   // the console is open
            { essb::Device::kKeyboard, 80, 1.0f, 0.0f, false, true, 0 },                   // a menu is open
            { essb::Device::kGamepad, 0x1000, 1.0f, 0.0f, false, false, essb::kAstral },   // A (276)
            { essb::Device::kMouse, 1, 1.0f, 0.0f, false, false, 0 },                      // right mouse: not bound
        };
        for (const Press& p : presses) {
            const bool down = p.value > 0.0f && p.held == 0.0f;   // RE::ButtonEvent::IsDown
            int element = 0;
            if (down) {
                const int candidate = essb::HotkeyElement(essb::KeyCodeOf(p.device, p.id), true, keys);
                essb::InputGate gate;
                gate.console = p.console;
                gate.menu = p.menu;
                element = candidate != 0 && essb::InputOpen(gate) ? candidate : 0;
            }
            Check(element == p.want, "X: input event " + std::to_string(p.id) + " -> " + std::to_string(element));
            ++n;
        }
    }
    return n;
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 3) {
            std::cerr << "usage: timer_test <timer-table.json> <wiring.json>\n";
            return 2;
        }
        const json table = Load(argv[1]);
        const json wiring = Load(argv[2]);
        essb::Config config;
        const auto& damage = table.at("damage");
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            config.damage[e] = { damage.at(e - 1).at(0).get<float>(), damage.at(e - 1).at(1).get<float>() };
        }
        int scenarios = 0;
        int items = 0;
        for (const auto& row : table.at("scenarios")) {
            items += RunScenario(row, config);
            ++scenarios;
        }
        std::cout << "NATIVE TIMER T ok: " << scenarios << " scenarios, " << items << " expected items matched (the clock, the forms' second, "
                  << "the environment, the domains, the slows, the hotkeys)\n";
        const int wired = Wiring(wiring, table);
        std::cout << "NATIVE TIMER W ok: " << wired << " wiring checks (round-25 kinds, the domains' HAZD / Spawn Hazard / spawn spells, "
                  << "CastSpells, the ally stamina, the timer's globals, the hotkeys, the upkeep settings)\n";
        const int fake = FakeEngineChecks();
        std::cout << "NATIVE TIMER X ok: " << fake << " fake-engine checks (fusion domain casts, silence drain, 潮池 wash limit, "
                  << "a fake timer with a pause and a load, fake input events, the domain scan's node gate)\n";
        std::cout << "checks=" << checks << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "NATIVE TIMER FAILED: " << e.what() << "\n";
        return 1;
    }
}
