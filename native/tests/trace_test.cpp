// Round 26: the probe log (native/include/Trace.h) -- the lines the commander judges build/probes-all.md from.
//   format    every line kind the sheet greps has the fixed prefix "[ESSB][T][kind] #seq g=… r=…" and its keys, read back
//             with the patterns of build/fix26-trace-format.json (the same patterns build/probe-judge.py parses with)
//   buffer    the sequence is the file order, a long body is cut at kMaxLine and ends in "~", a newline in a name cannot
//             split a line, a full buffer drops and counts
//   rng       TraceRng draws exactly what SplitMix64 draws (recording or not: the probe log never changes a roll) and
//             its tape reads back the draws
//   engine    a fake world (effects that are cast, dispelled and run out) under the real StatusEngine.h RunPlan: every op
//             is traced once, op-done follows exactly the value-changing ops, nothing is traced with the level off, the
//             "was" part reads the instance the op replaces; DescribeRemoved tells expiry / dispel / death apart for every
//             effect of ours; SelectCrowdWhy gives every actor of a list its verdict and the same picks as SelectCrowd
//   sample    the real planners (PlanHit, PlanStatusHit, PlanHurt, PlanSwitch, Environment, PlanFormSecond) in the fake world
//             write build/fix26-trace-sample.log: one station per scenario (markers 9001..), the input of probe-judge's
//             offline test (build/fix26_verify.py renumbers the stations to the sheet's)
#include "EngineFacts.h"
#include "Selection.h"
#include "StatusEngine.h"
#include "Trace.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using essb::StatusKind;
using essb::Who;
using essb::engine::EffectView;
namespace tr = essb::trace;

int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
}

bool Near(double a, double b, double tol = 2e-3)
{
    return std::abs(a - b) <= tol * std::max(1.0, std::abs(b));
}

std::vector<std::string> Lines(const std::string& text)
{
    std::vector<std::string> out;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        out.push_back(line);
    }
    return out;
}

// build/fix26-trace-format.json: kind -> regex (ECMAScript) of the whole line; probe-judge.py uses the same file.
std::map<std::string, std::regex> formats;

void LoadFormats(const char* path)
{
    std::ifstream in(path);
    Check(static_cast<bool>(in), std::string("format file missing: ") + path);
    nlohmann::json j;
    in >> j;
    for (const auto& [kind, pattern] : j.at("kinds").items()) {
        formats.emplace(kind, std::regex(pattern.get<std::string>()));
    }
    Check(formats.size() >= 20, "format: at least the 20 kinds the sheet reads");
}

// Every T line parses with its kind's pattern; the step marker with "step". Returns the kinds seen.
std::set<std::string> CheckFormat(const std::string& text)
{
    static const std::regex head(R"(^\[ESSB\]\[T\]\[([a-z-]+)\] #(\d+) g=(\d+) r=(\d+)( .*)?$)");
    static const std::regex step(R"(^\[ESSB\]\[STEP\] (\d+) #(\d+) g=(\d+) r=(\d+) via=([a-z-]+)$)");
    std::set<std::string> kinds;
    unsigned long long last = 0;
    for (const auto& line : Lines(text)) {
        std::smatch m;
        unsigned long long seq = 0;
        std::string kind;
        if (std::regex_match(line, m, step)) {
            kind = "step";
            seq = std::stoull(m[2]);
        } else if (std::regex_match(line, m, head)) {
            kind = m[1];
            seq = std::stoull(m[2]);
        } else {
            Check(false, "format: a line of the probe log has no T prefix: " + line);
        }
        Check(seq == last + 1, "format: the sequence is the file order: " + line);
        last = seq;
        const auto it = formats.find(kind);
        Check(it != formats.end(), "format: kind " + kind + " has no pattern in build/fix26-trace-format.json");
        Check(std::regex_match(line, it->second), "format: the " + kind + " pattern does not read: " + line);
        kinds.insert(kind);
    }
    return kinds;
}

// ---------------------------------------------------------------- the fake world

tr::ActorFacts Facts(const char* name, std::uint32_t id, float h, float hMax, float m = 100.0f, float mMax = 100.0f)
{
    tr::ActorFacts f;
    f.has = true;
    f.name = name;
    f.formId = id;
    f.h = h;
    f.hMax = hMax;
    f.m = m;
    f.mMax = mMax;
    f.s = 100.0f;
    f.sMax = 100.0f;
    return f;
}

struct World {
    using Handle = int;
    struct Eff {
        EffectView v;
        bool alive = true;
    };
    std::vector<Eff> list[2];   // [0] target, [1] you
    tr::ActorFacts actor[2]{ Facts("Bandit", 0xFF000D8A, 5000.0f, 5000.0f), Facts("Prisoner", 0x00000014, 1000.0f, 1000.0f, 300.0f, 300.0f) };
    bool self = false;
    bool dead = false;
    std::uint32_t uid = 100;
    tr::Buffer& buffer;
    std::uint64_t game = 0;
    std::uint64_t real = 0;
    const char* ctx = "hit";
    bool tracing = true;
    int traced = 0;
    int done = 0;
    std::vector<essb::Op> doneOps;
    essb::Op current{};

    explicit World(tr::Buffer& b) : buffer(b) {}

    static int Index(Who who) { return who == Who::kPlayer ? 1 : 0; }

    std::uint64_t Emit(const tr::Line& line)
    {
        bool now = false;
        return buffer.Add(line, game, real, now);
    }

    template <class Fn>
    void ForEach(Who who, Fn&& fn)
    {
        auto& l = list[Index(who)];
        for (int i = 0; i < static_cast<int>(l.size()); ++i) {
            if (l[i].alive) {
                fn(l[i].v, i);
            }
        }
    }
    template <class Fn>
    void ForEachIncludingEnding(Who who, Fn&& fn)
    {
        ForEach(who, fn);
    }

    void Removed(Who who, Eff& e, const char* reason)
    {
        tr::Line line("remove");
        tr::RemoveLine(line, actor[Index(who)], essb::TagOf(e.v.effect), e.v.magnitude, e.v.elapsed, e.v.duration, reason);
        Emit(line);
    }

    void Dispel(Who who, Handle h)
    {
        auto& e = list[Index(who)][h];
        e.alive = false;
        if (!self) {
            Removed(who, e, "dispel");
        }
    }
    bool SelfDispel() const { return self; }
    void SetSelfDispel(bool on) { self = on; }

    // The spell -> (effect, the record's seconds) the fake engine applies; a react spell deals its magnitude.
    void Cast(Who who, std::uint32_t spell, float magnitude, float effectiveness)
    {
        std::uint32_t effect = 0;
        float seconds = 0.0f;
        for (int k = 0; k < essb::kStatusKindCount; ++k) {
            if (essb::kStatusRecords[k].spell == spell) {
                effect = essb::kStatusRecords[k].effect;
                seconds = essb::kStatusRecords[k].seconds * effectiveness;
            }
        }
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            if (essb::status::kMarkSpell[e] == spell) {
                effect = essb::status::kMarkEffect[e];
                seconds = essb::status::kMarkRecordSeconds * effectiveness;
            }
            if (essb::status::kReactSpell[e] == spell) {
                actor[Index(who)].h -= magnitude;
                return;
            }
        }
        for (int i = 0; i < essb::status::kDotMaxSeconds; ++i) {
            if (essb::status::kBleedDot[i] == spell) {
                effect = essb::status::kBleedDotEffect;
                seconds = static_cast<float>(i + 1);
            }
            if (essb::status::kPoisonDot[i] == spell) {
                effect = essb::status::kPoisonDotEffect;
                seconds = static_cast<float>(i + 1);
            }
        }
        if (spell == essb::spell::kHeal) {
            actor[Index(who)].h = std::min(actor[Index(who)].hMax, actor[Index(who)].h + magnitude);
            return;
        }
        if (!effect) {
            return;   // a utility cast the fake does not model
        }
        EffectView v;
        v.uid = ++uid;
        v.effect = effect;
        v.spell = spell;
        v.magnitude = magnitude;
        v.duration = seconds;
        v.hasSpell = true;
        v.ours = true;
        list[Index(who)].push_back(Eff{ v });
    }
    bool Dead(Who) { return dead; }
    void PayHealth(float amount) { actor[1].h = std::max(1.0f, actor[1].h - amount); }
    void Send(const essb::StatusOp&) {}
    void LogWash(const EffectView&, bool) {}
    void LogReapply(const essb::StatusOp&, int) {}
    void PayStamina(float amount) { actor[1].s = std::max(0.0f, actor[1].s - amount); }
    void HurtHealth(float amount) { actor[1].h -= amount; }
    void Resonance() {}
    void Interrupt(Who) {}
    void CrushArea(const essb::StatusOp&) {}
    void FreezeNearby() {}
    void DrainMagickaAll(Who who) { actor[Index(who)].m = 0.0f; }
    void Select(std::uint8_t) {}

    // round 26: the probe log's hooks, as Plugin.cpp's RealEngine has them
    bool Tracing() const { return tracing; }
    std::uint64_t TraceOp(const essb::StatusOp& op, const essb::Lowered& l, Who on)
    {
        ++traced;
        current = op.op;
        int count = 0;
        float was = 0.0f;
        float left = 0.0f;
        if (l.dispelSpell || l.dispelEffect) {
            ForEach(on, [&](const EffectView& v, Handle) {
                if ((l.dispelSpell && v.spell == l.dispelSpell) || (l.dispelEffect && v.effect == l.dispelEffect)) {
                    if (count++ == 0) {
                        was = v.magnitude;
                        left = std::max(0.0f, v.duration - v.elapsed);
                    }
                }
            });
        }
        tr::Line line("op");
        tr::OpLine(line, ctx, op, actor[Index(on)], l, count, was, left);
        return Emit(line);
    }
    void TraceDone(std::uint64_t ref, Who on)
    {
        ++done;
        doneOps.push_back(current);
        tr::Line line("op-done");
        tr::OpDoneLine(line, ref, actor[Index(on)]);
        Emit(line);
    }

    // Game time passes: every effect ages; one that reaches its duration leaves (reason expired).
    void Elapse(float seconds)
    {
        game += static_cast<std::uint64_t>(seconds * 1000.0f);
        real += static_cast<std::uint64_t>(seconds * 1000.0f);
        for (int w = 0; w < 2; ++w) {
            for (auto& e : list[w]) {
                if (!e.alive) {
                    continue;
                }
                e.v.elapsed += seconds;
                if (e.v.duration > 0.0f && e.v.elapsed >= e.v.duration) {
                    e.alive = false;
                    Removed(w == 1 ? Who::kPlayer : Who::kTarget, e, "expired");
                }
            }
        }
    }
};

struct NoNodes {
    int Rank(const essb::NodeId&) const { return 0; }
    bool Has(const essb::BranchId&) const { return false; }
};

// ---------------------------------------------------------------- unit checks

void BufferChecks()
{
    tr::Buffer b;
    bool now = false;
    tr::Line a("op");
    a.F(" x=%d", 1);
    Check(b.Add(a, 5, 7, now) == 1 && !now, "buffer: first line is #1");
    tr::Line longLine("pap");
    for (int i = 0; i < 100; ++i) {
        longLine.F(" field%d=%d", i, i);
    }
    Check(longLine.Cut() && longLine.Body().size() == tr::kMaxLine, "buffer: a long body stops at kMaxLine");
    Check(b.Add(longLine, 6, 8, now) == 2, "buffer: second line is #2");
    tr::Line named("op");
    tr::ActorFacts f = Facts("Bad\nName(x)=y", 0x10, 1.0f, 2.0f);
    named.Actor("on", f);
    b.Add(named, 7, 9, now);
    b.Raw("[ESSB][X1] raw line", now);
    Check(b.Step(17, 8, 10, "key", now) == 4, "buffer: the step marker is numbered in the same sequence");
    std::uint64_t dropped = 99;
    const std::string text = b.Take(dropped);
    const auto lines = Lines(text);
    Check(dropped == 0 && lines.size() == 5, "buffer: 5 lines, none dropped");
    Check(lines[0] == "[ESSB][T][op] #1 g=5 r=7 x=1", "buffer: the prefix (" + lines[0] + ")");
    Check(lines[1].back() == '~' && lines[1].size() == std::string("[ESSB][T][pap] #2 g=6 r=8").size() + tr::kMaxLine + 1,
        "buffer: a cut line ends in ~");
    Check(lines[2].find("on=Bad_Name_x__y(0x00000010)[h=1.0/2.0") != std::string::npos, "buffer: a name cannot break the line (" + lines[2] + ")");
    Check(lines[3] == "[ESSB][X1] raw line", "buffer: a raw line keeps its text and order");
    Check(lines[4] == "[ESSB][STEP] 17 #4 g=8 r=10 via=key", "buffer: the step marker (" + lines[4] + ")");
    Check(b.Take(dropped).empty(), "buffer: taken once");
}

void RngChecks()
{
    essb::SplitMix64 plain(12345);
    tr::TraceRng traced(12345);
    traced.Record(true);
    for (int i = 0; i < 200; ++i) {
        if (i == 100) {
            traced.Record(false);   // recording off: still the same draws
        }
        Check(plain.Int(1, 25) == traced.Int(1, 25), "rng: Int draws equal");
        Check(plain.Real(10.0f, 12.0f) == traced.Real(10.0f, 12.0f), "rng: Real draws equal");
        Check(plain.Chance(0.3f) == traced.Chance(0.3f), "rng: Chance draws equal");
    }
    tr::TraceRng tape(7);
    tape.Record(true);
    const int i = tape.Int(1, 25);
    const float r = tape.Real(10.0f, 12.0f);
    const bool c = tape.Chance(0.07f);
    char want[160];
    std::snprintf(want, sizeof(want), "I(1,25)=%d R(10,12)=%.4f C(0.07)=%d", i, r, c ? 1 : 0);
    Check(tape.Tape() == want, "rng: the tape reads back the draws (" + tape.Tape() + ")");
    for (int k = 0; k < 40; ++k) {
        tape.Chance(0.5f);
    }
    Check(tape.Count() == 43 && tape.Tape().ends_with("+19 more"), "rng: at most kTape draws kept, the rest counted");
}

void EngineChecks(tr::Buffer& buffer)
{
    // Every op is traced once; op-done follows exactly the value-changing ops; nothing with the level off.
    World w(buffer);
    essb::StatusPlan plan;
    essb::Board target;
    essb::Board you;
    essb::Writer{ plan, target, Who::kTarget }.Set(StatusKind::kCurse, 3.0f, 8.0f);
    essb::Writer{ plan, target, Who::kTarget }.Mark(essb::kFire, 8.0f);
    plan.Push(essb::Amount(essb::Op::kDamage, 40.0f, essb::kFire));
    plan.Push(essb::Amount(essb::Op::kPayHealth, 12.0f));
    plan.Push(essb::MakeEvent(essb::Event::kEnd, static_cast<float>(essb::kFire), 1.0f, 1.0f));
    essb::Tuning t;
    essb::engine::RunPlan(w, plan, t);
    Check(w.traced == plan.count, "engine: every op traced once");
    Check(w.done == 2 && w.doneOps[0] == essb::Op::kDamage && w.doneOps[1] == essb::Op::kPayHealth, "engine: op-done after damage and pay only");
    // A re-apply reads the instance it replaces.
    essb::StatusPlan again;
    essb::Writer{ again, target, Who::kTarget }.Set(StatusKind::kCurse, 4.0f, 8.0f);
    w.Elapse(2.0f);
    essb::engine::RunPlan(w, again, t);
    std::uint64_t dropped = 0;
    const auto lines = Lines(buffer.Take(dropped));
    bool sawWas = false;
    bool sawEnd = false;
    for (const auto& l : lines) {
        sawWas = sawWas || (l.find("kind=N3_Curse") != std::string::npos && l.find("mag=4.00") != std::string::npos &&
                               l.find("was=3.00 left=6.00 n=1") != std::string::npos);
        sawEnd = sawEnd || (l.find("ev=End") != std::string::npos && l.find("reason=burst") != std::string::npos);
    }
    Check(sawWas, "engine: the re-apply names what it replaced (3 layers, 6 s left)");
    Check(sawEnd, "engine: an end event names its reason");
    World off(buffer);
    off.tracing = false;
    essb::engine::RunPlan(off, plan, t);
    Check(off.traced == 0 && off.done == 0, "engine: level off, nothing traced");

    // DescribeRemoved: every effect of ours, expiry / dispel / death; a foreign one ignored.
    World r(buffer);
    r.Cast(Who::kTarget, essb::kStatusRecords[static_cast<int>(StatusKind::kFissure)].spell, 1.0f, 1.0f);
    const std::uint32_t id = r.list[0].back().v.uid;
    r.list[0].back().v.elapsed = 8.0f;
    Check(essb::engine::DescribeRemoved(r, Who::kTarget, id, false).reason == essb::engine::Removal::kExpired,
        "removed: a status that does not settle is still described (expired)");
    r.list[0].back().v.elapsed = 1.0f;
    Check(essb::engine::DescribeRemoved(r, Who::kTarget, id, false).reason == essb::engine::Removal::kDispelled, "removed: early = dispel");
    Check(essb::engine::DescribeRemoved(r, Who::kTarget, id, true).reason == essb::engine::Removal::kDeath, "removed: dead = death");
    EffectView foreign;
    foreign.uid = 555;
    r.list[0].push_back(World::Eff{ foreign });
    Check(essb::engine::DescribeRemoved(r, Who::kTarget, 555, false).reason == essb::engine::Removal::kIgnore, "removed: foreign ignored");
    buffer.Take(dropped);
}

void CrowdChecks()
{
    using essb::engine::ActorView;
    using essb::engine::Pick;
    std::vector<ActorView> list(9);
    list[0].you = true;
    list[1].hostile = true;
    list[1].pos = { 100.0f, 0.0f, 0.0f };   // the primary
    list[2].hostile = true;
    list[2].pos = { 200.0f, 0.0f, 0.0f };
    list[3].dead = true;
    list[4].teammate = true;
    list[4].pos = { 50.0f, 0.0f, 0.0f };
    list[5].pos = { 60.0f, 0.0f, 0.0f };    // a neutral you did not attack
    list[6].hostile = true;
    list[6].pos = { 9000.0f, 0.0f, 0.0f };  // too far
    list[7].commanded = true;
    list[8].hostile = true;
    list[8].pos = { 300.0f, 0.0f, 0.0f };   // over the limit of 1
    std::vector<Pick> why(list.size(), Pick::kFar);
    const std::array<float, 3> you{};
    const std::array<float, 3> centre{ 100.0f, 0.0f, 0.0f };
    const auto picked = essb::engine::SelectCrowdWhy(list, 1, centre, 1050.0f, you, 1050.0f, 1, [&](int i, Pick p) { why[i] = p; });
    const auto plain = essb::engine::SelectCrowd(list, 1, centre, 1050.0f, you, 1050.0f, 1);
    Check(picked.size() == plain.size() && std::equal(picked.begin(), picked.end(), plain.begin(),
                                                     [](const auto& a, const auto& b) { return a.index == b.index && a.ally == b.ally; }),
        "crowd: the verdicts never change the picks");
    const std::vector<Pick> want{ Pick::kYou, Pick::kPrimary, Pick::kPicked, Pick::kDead, Pick::kAlly, Pick::kNeutral, Pick::kFar,
        Pick::kCommanded, Pick::kOverLimit };
    Check(why == want, "crowd: every actor has its verdict (you, primary, picked, dead, ally, neutral, far, commanded, over the limit)");
    Check(std::string(essb::engine::kPickNames[static_cast<int>(Pick::kAllyOverLimit)]) == "ally-over-limit" &&
              std::size(essb::engine::kPickNames) == static_cast<std::size_t>(Pick::kAllyOverLimit) + 1,
        "crowd: every verdict has a name");
}

void NameChecks()
{
    Check(tr::KindName(StatusKind::kFreeze) == "N3_Freeze", "names: status kinds by record");
    Check(tr::TagName(essb::TagOf(essb::status::kMarkEffect[essb::kFire])) == "Mark_fire", "names: marks by element");
    Check(std::string(tr::OpName(essb::Op::kStaminaTarget)) == "StaminaTarget" && std::string(tr::EventName(essb::Event::kClose)) == "Close",
        "names: the last op and event");
    essb::Board b;
    b[StatusKind::kRetortCooldown] = essb::Slot{ true, 1.0f, 1.0f, 3.0f };
    Check(tr::Cooldowns(b) == "N4_RetortCooldown:2.0" || tr::Cooldowns(b).find("RetortCooldown:2.0") != std::string::npos,
        "names: cooldowns with the time left (" + tr::Cooldowns(b) + ")");
    Check(tr::Cooldowns(essb::Board{}) == "-", "names: no cooldown = -");
}

// ---------------------------------------------------------------- the offline sample for build/probe-judge.py

// The real planners in the fake world, one station per scenario (markers 9001..; build/fix26_verify.py renumbers them to
// the sheet's stations): the formatters are the DLL's, the numbers are the planners'.
std::string Sample()
{
    tr::Buffer b;
    World w(b);
    tr::TraceRng rng(20260927);
    const essb::Config config = essb::MakeConfig();
    essb::Tuning t;
    t.level.fill(1.0f);
    NoNodes nodes;
    essb::StatusInputs in;
    in.config = &config;
    in.tuning = &t;
    in.n4 = true;
    bool now = false;
    auto mark = [&](int station) { b.Step(station, w.game, w.real, "key", now); };
    auto tick = [&](float seconds) {
        for (float s = 0.0f; s < seconds - 1e-4f; s += 0.5f) {
            w.Elapse(0.5f);
        }
    };
    auto proc = [&](int element, bool power) {
        essb::Attack a;
        a.element = element;
        a.power = power;
        rng.Record(true);
        essb::PlayerFacts player;
        const essb::Plan plan = essb::PlanHit(a, config, t, player, essb::TargetFacts{}, nodes, rng);
        tr::Line line("proc");
        const essb::ProcRow* row = essb::FindProc(element, power);
        tr::ProcLine(line, "hit", w.actor[0], w.actor[1], plan, a, 1, row ? row->name : std::string_view("-"), 0, 0.0f, rng.Tape());
        w.Emit(line);
        rng.Record(false);
        return plan;
    };
    auto statusHit = [&](int element, bool power) {
        essb::Board target = essb::engine::ReadBoard(w, Who::kTarget);
        essb::Board self = essb::engine::ReadBoard(w, Who::kPlayer);
        auto plan = std::make_unique<essb::StatusPlan>();
        essb::PlanStatusHit(*plan, element, power, target, self, in, nodes, rng);
        essb::engine::RunPlan(w, *plan, t);
    };
    auto formSecond = [&](int form, float magicka, bool thunder) {
        essb::SecondFacts sf;
        sf.form = form;
        sf.magicka = magicka;
        sf.magickaMax = 300.0f;
        sf.health = 1000.0f;
        sf.healthMax = 1000.0f;
        sf.healthPermanent = 1000.0f;
        sf.stamina = 200.0f;
        sf.staminaMax = 200.0f;
        sf.thunder = thunder;
        essb::Board me = essb::engine::ReadBoard(w, Who::kPlayer);
        auto plan = std::make_unique<essb::StatusPlan>();
        const std::array<essb::Ally, essb::n6::kRiverAllies> allies{};
        const essb::FormSecond fs = essb::PlanFormSecond(*plan, me, sf, in, essb::TimerTuning{}, nodes, allies, 0);
        w.ctx = "form-second";
        essb::engine::RunPlan(w, *plan, t);
        w.ctx = "hit";
        return fs;
    };

    // 9001 = B-07: 5 normal and 3 power fire procs, 7 s apart (no heat: only the proc is planned)
    mark(9001);
    for (int i = 0; i < 8; ++i) {
        proc(essb::kFire, i >= 5);
        tick(7.0f);
    }

    // 9002 = B-35: blood hits on a fresh target until the bleed stops growing, then 12 s without a hit
    mark(9002);
    w.list[0].clear();
    for (int i = 0; i < 9; ++i) {
        proc(essb::kBlood, false);
        statusHit(essb::kBlood, false);
        tick(1.5f);
    }
    tick(12.0f);

    // 9003 = B-33: one hit of fire, wind, water and astral on a clean target each, 15 s apart
    mark(9003);
    for (const int element : { essb::kFire, essb::kWind, essb::kWater, essb::kAstral }) {
        w.list[0].clear();
        proc(element, false);
        statusHit(element, false);
        tick(15.0f);
    }

    // 9004 = A-15: the weather sequence (Timer.h Environment), a check every 5 s; the lightning form's seconds
    // (PlanFormSecond) give their storm charges
    mark(9004);
    struct Weather {
        std::uint32_t id;
        int cls;
        std::uint8_t lightning;
        std::uint8_t wind;
        bool interior;
    };
    const Weather weathers[] = { { 0x000C8220u, 2, 40, 60, false }, { 0x000C8220u, 2, 40, 60, true },
        { 0x0000081Au, 0, essb::n6::kNoLightning, 30, false }, { 0x000C821Fu, 2, essb::n6::kNoLightning, 60, false },
        { 0x000C8220u, 2, 40, 60, false }, { 0x0004D7FBu, 3, essb::n6::kNoLightning, 40, false },
        { 0x000C8221u, 3, essb::n6::kNoLightning, 200, false }, { 0x0000081Au, 0, essb::n6::kNoLightning, 30, false } };
    essb::EnvFlags last{};
    for (const Weather& x : weathers) {
        essb::EnvFacts f;
        f.weather = x.cls;
        f.lightning = x.lightning;
        f.wind = x.wind;
        f.interior = x.interior;
        for (int check = 0; check < 2; ++check) {
            const essb::EnvFlags e = essb::Environment(f);
            const bool changed = e.wet != last.wet || e.stormy != last.stormy || e.thunder != last.thunder || e.night != last.night;
            last = e;
            tr::Line line("env");
            tr::EnvLine(line, e, f, changed);
            line.F(" weather=0x%08X", x.id);
            w.Emit(line);
            for (int s = 0; s < 5; ++s) {
                const essb::FormSecond fs = formSecond(essb::kLightning, 300.0f, e.thunder);
                tr::Line second("second");
                tr::SecondLine(second, essb::kLightning, fs, true, 0.0f, -fs.spent, 0.0f, w.actor[1]);
                w.Emit(second);
                tick(1.0f);
            }
        }
    }

    // 9005 = A-05: the switch sequence (Timer.h PlanSwitch): hotkey frost open / close, fire refused at 20 magicka, blood
    // opens and closes; the Z power refused, opened after the restore, closed
    mark(9005);
    struct Press {
        const char* via;
        int wanted;
        float magicka;
    };
    const Press presses[] = { { "hotkey", essb::kFrost, 300.0f }, { "hotkey", essb::kFrost, 300.0f }, { "hotkey", essb::kFire, 20.0f },
        { "hotkey", essb::kBlood, 20.0f }, { "hotkey", essb::kBlood, 20.0f }, { "power", essb::kFire, 20.0f },
        { "power", essb::kFire, 300.0f }, { "power", essb::kFire, 300.0f } };
    essb::SwitchFacts sw;
    for (const Press& x : presses) {
        sw.magicka = x.magicka;
        sw.magickaMax = 300.0f;
        const essb::SwitchPlan plan = essb::PlanSwitch(sw, x.wanted);
        tr::ActorFacts you = w.actor[1];
        you.m = x.magicka;
        tr::Line line("switch");
        tr::SwitchLine(line, x.via, x.wanted, plan, sw, you);
        w.Emit(line);
        if (plan.kind == essb::SwitchKind::kClose) {
            sw.active = false;
            sw.current = 0;
        } else if (plan.kind == essb::SwitchKind::kOpen || plan.kind == essb::SwitchKind::kSwitch) {
            sw.active = true;
            sw.current = plan.element;
        }
        tick(1.0f);
    }

    // 9006 = A-09: 10 s of the fire form and 10 s of the dark form (Timer.h PlanFormSecond), regeneration off
    mark(9006);
    for (const int form : { essb::kFire, essb::kDarkness }) {
        float magicka = 300.0f;
        for (int s = 0; s < 10; ++s) {
            const essb::FormSecond fs = formSecond(form, magicka, false);
            magicka -= fs.spent;
            tr::ActorFacts you = w.actor[1];
            you.m = magicka;
            tr::Line second("second");
            tr::SecondLine(second, form, fs, true, 0.0f, -fs.spent, 0.0f, you);
            w.Emit(second);
            tick(1.0f);
        }
    }
    std::uint64_t dropped = 0;
    return b.Take(dropped);
}

void SampleChecks(const std::string& text)
{
    const auto kinds = CheckFormat(text);
    for (const char* k : { "proc", "op", "remove", "env", "second", "switch", "step" }) {
        Check(kinds.contains(k), std::string("sample: the ") + k + " lines are in the sample");
    }
    int stations = 0;
    for (const auto& line : Lines(text)) {
        stations += line.starts_with("[ESSB][STEP] ") ? 1 : 0;
    }
    Check(stations == 6, "sample: six stations (9001..9006)");
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 2) {
            throw std::runtime_error("usage: trace_test <build/fix26-trace-format.json> [sample.log]");
        }
        LoadFormats(argv[1]);
        BufferChecks();
        RngChecks();
        tr::Buffer buffer;
        EngineChecks(buffer);
        CrowdChecks();
        NameChecks();
        const std::string sample = Sample();
        SampleChecks(sample);
        if (argc >= 3) {
            std::ofstream out(argv[2], std::ios::binary);
            out << sample;
            Check(static_cast<bool>(out), std::string("sample: written to ") + argv[2]);
        }
        std::cout << "NATIVE TRACE ok: " << checks << " checks (format, buffer, rng, engine hooks, removals, crowd verdicts, names; "
                  << Lines(sample).size() << " sample lines from the real planners)\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "NATIVE TRACE FAILED: " << e.what() << "\n";
        return 1;
    }
}
