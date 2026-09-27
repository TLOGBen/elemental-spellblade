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
#include "Sinks.h"
#include "StatusEngine.h"
#include "Trace.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
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

// ---------------------------------------------------------------- round 26b: the sinks read only their own event

struct FakeActor {
    int id = 0;
    essb::Board board;
    bool servant = false;
    int ours = 0;
};

// Every read the death sink makes, by actor; the world has no way to write anything.
struct SinkWorld {
    std::vector<int> reads;
    bool Servant(const FakeActor* a) { reads.push_back(a->id); return a->servant; }
    int CountOurs(const FakeActor* a) { reads.push_back(a->id); return a->ours; }
    const essb::Board& ReadCorpse(const FakeActor* a) { reads.push_back(a->id); return a->board; }
};

void SinkChecks()
{
    FakeActor corpse{ 1 };
    FakeActor killer{ 2 };
    FakeActor you{ 3 };
    corpse.board.mark[essb::kFire] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
    corpse.ours = 2;
    // dead = false, killed by you: the corpse is read, the killer and you only compared
    SinkWorld w;
    essb::sink::DeathSeen s = essb::sink::DeathSink(w, &corpse, &you, &you, false, true);
    Check(s.killerYou && s.snapshot && s.ours == 2 && !s.dyingIsYou, "death sink: your kill of a marked corpse is planned");
    Check(!w.reads.empty() && std::all_of(w.reads.begin(), w.reads.end(), [](int id) { return id == 1; }),
        "death sink: only the corpse is read (never the killer, never you)");
    // killed by someone else: still only the corpse
    SinkWorld w2;
    s = essb::sink::DeathSink(w2, &corpse, &killer, &you, false, false);
    Check(!s.killerYou && s.snapshot && std::all_of(w2.reads.begin(), w2.reads.end(), [](int id) { return id == 1; }),
        "death sink: another killer is never read");
    // the dead = true event: counted for the log, never planned
    SinkWorld w3;
    s = essb::sink::DeathSink(w3, &corpse, &killer, &you, true, true);
    Check(!s.snapshot && s.ours == 2, "death sink: dead = true is only logged");
    // your own death: nothing is read
    SinkWorld w4;
    s = essb::sink::DeathSink(w4, &you, &killer, &you, false, true);
    Check(s.dyingIsYou && w4.reads.empty(), "death sink: your own death reads nothing");
    // a clean corpse killed by someone else: nothing to plan
    FakeActor clean{ 4 };
    SinkWorld w5;
    Check(!essb::sink::DeathSink(w5, &clean, &killer, &you, false, false).snapshot, "death sink: nothing of ours, not your kill");

    // PlanInput: pure; blocked hotkeys come back not accepted, step keys only with the probe log and an open gate
    essb::sink::InputFacts f;
    f.active = f.enabled = f.hotkeys = true;
    f.keys = { 79, 80, 81, 75, 76, 77, 71, 72, 73, 82, 83 };
    f.stepNext = tr::kStepKeyNext;
    f.stepBack = tr::kStepKeyBack;
    const std::vector<essb::sink::Press> presses{ { essb::Device::kKeyboard, 79, true }, { essb::Device::kKeyboard, 80, false },
        { essb::Device::kKeyboard, static_cast<std::uint32_t>(tr::kStepKeyNext), true }, { essb::Device::kKeyboard, 30, true } };
    auto a = essb::sink::PlanInput(presses, f);
    Check(a.size() == 1 && a[0].kind == essb::sink::ActionKind::kSwitch && a[0].element == essb::kFire && a[0].accepted,
        "input: a pressed hotkey becomes one accepted switch (the released key, the unbound key and the step key without the log do nothing)");
    f.trace = true;
    a = essb::sink::PlanInput(presses, f);
    Check(a.size() == 2 && a[1].kind == essb::sink::ActionKind::kStep && a[1].delta == 1, "input: the step key with the probe log");
    f.gate.console = true;
    a = essb::sink::PlanInput(presses, f);
    Check(a.size() == 1 && !a[0].accepted, "input: a closed gate blocks the hotkey (logged, not run) and drops the step key");
    f.gate.console = false;
    f.enabled = false;
    a = essb::sink::PlanInput(presses, f);
    Check(a.size() == 1 && a[0].kind == essb::sink::ActionKind::kStep, "input: the master switch off keeps the step key only");
    // the X2 chain keys: unique offsets, the ones the commander named
    std::set<std::uintptr_t> offsets;
    for (const auto& k : tr::kChainKeys) {
        offsets.insert(k.offset);
    }
    Check(offsets.size() == std::size(tr::kChainKeys) && offsets.contains(0x640E67) && offsets.contains(0x5B36AD), "X2: chain keys");
}

// ---------------------------------------------------------------- round 26c

// P3: the tape never writes past its end -- sequentially (100 draws for 24 slots) and with four threads drawing at once
// while a fifth restarts the recording (a data race by design here: the test is that it stays inside the object).
struct Fenced {
    tr::TraceRng rng{ 99 };
    std::array<std::uint64_t, 8> canary{ 0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL,
        0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL, 0xC0FFEE0DDBA11ULL };
    bool Intact() const
    {
        return std::all_of(canary.begin(), canary.end(), [](std::uint64_t c) { return c == 0xC0FFEE0DDBA11ULL; });
    }
};

void TapeBoundsChecks()
{
    auto fenced = std::make_unique<Fenced>();
    fenced->rng.Record(true);
    for (int i = 0; i < 100; ++i) {
        fenced->rng.Chance(0.5f);
    }
    Check(fenced->Intact() && fenced->rng.Count() == 100, "tape: 100 draws, 24 kept, nothing written past the tape");
    auto shared = std::make_unique<Fenced>();
    shared->rng.Record(true);
    std::atomic_bool stop{ false };
    std::vector<std::thread> workers;
    for (int w = 0; w < 4; ++w) {
        workers.emplace_back([&]() {
            for (int i = 0; i < 200000; ++i) {
                shared->rng.Real(0.0f, 1.0f);
            }
        });
    }
    std::thread restarter([&]() {
        while (!stop.load()) {
            shared->rng.Record(true);
        }
    });
    for (auto& w : workers) {
        w.join();
    }
    stop = true;
    restarter.join();
    Check(shared->Intact(), "tape: four threads drawing while a fifth restarts the recording never write past the tape");
    Check(!shared->rng.Tape().empty(), "tape: still readable after the stress");
}

// P2: a fake whose Dispel erases the effect from the list (so a kept handle -- an index -- would point at another
// effect afterwards): DispelWhere must re-find each by identity.
struct ShiftingWorld {
    using Handle = int;
    std::vector<EffectView> list;
    bool self = false;
    template <class Fn>
    void ForEach(Who, Fn&& fn)
    {
        for (int i = 0; i < static_cast<int>(list.size()); ++i) {
            fn(list[static_cast<std::size_t>(i)], i);
        }
    }
    void Dispel(Who, Handle h) { list.erase(list.begin() + h); }
    bool SelfDispel() const { return self; }
    void SetSelfDispel(bool on) { self = on; }
};

void DispelByIdChecks()
{
    ShiftingWorld w;
    auto view = [](std::uint32_t uid, std::uint32_t effect) {
        EffectView v;
        v.uid = uid;
        v.effect = effect;
        v.spell = effect + 1;
        return v;
    };
    w.list = { view(1, 10), view(2, 10), view(3, 20), view(4, 10) };
    const int n = essb::engine::DispelWhere(w, Who::kTarget, [](const EffectView& v) { return v.effect == 10; });
    Check(n == 3 && w.list.size() == 1 && w.list[0].uid == 3, "dispel: each match re-found by id before its Dispel (the list shifts)");
    ShiftingWorld gone;
    gone.list = { view(1, 10) };
    int calls = 0;
    const int m = essb::engine::DispelWhere(gone, Who::kTarget, [&](const EffectView& v) {
        if (++calls == 1) {
            return v.effect == 10;
        }
        return false;
    });
    Check(m == 1 && gone.list.empty() && !gone.self, "dispel: the self-dispel flag is restored");
}

// P1: the hit sink's route -- a hit raised inside our own hit task is dropped; yours goes to the hit task, on you to the
// hurt task, the rest nowhere. The sink itself calls nothing that changes the engine (build/fix26_verify.py checks its
// body); this is the pure part.
void RouteChecks()
{
    using essb::sink::HitRoute;
    Check(essb::sink::RouteHit(true, false, false) == HitRoute::kYours, "route: your hit -> the hit task");
    Check(essb::sink::RouteHit(false, true, false) == HitRoute::kHurt, "route: a hit on you -> the hurt task");
    Check(essb::sink::RouteHit(false, false, false) == HitRoute::kIgnore, "route: others' hits are ignored");
    Check(essb::sink::RouteHit(true, false, true) == HitRoute::kNested && essb::sink::RouteHit(false, true, true) == HitRoute::kNested,
        "route: a hit our own hit task raised is dropped (the old re-entrancy guard)");
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

// Round 26d (0.26.3): Plugin.cpp's Rng() returns through TaskRng. 0.26.2's body called itself and spun forever at the
// first draw (the in-game freeze after closing a form with a burst). Each call here runs under a 3 s watchdog: a hang ends
// the test with a failure instead of hanging ctest.
void TaskRngChecks()
{
    auto watched = [](const char* what, auto body) {
        auto job = std::async(std::launch::async, body);
        if (job.wait_for(std::chrono::seconds(3)) != std::future_status::ready) {
            std::cout << "NATIVE TRACE FAILED: task rng: " << what << " never returned (a self-call spins: the 0.26.2 freeze)\n";
            std::cout.flush();
            std::_Exit(3);
        }
        return job.get();
    };
    std::optional<tr::TraceRng> rng;
    rng.emplace(99);
    std::atomic_bool reported{ false };
    int outside = 0;
    tr::TraceRng* inTask = watched("a draw inside a task", [&] { return &tr::TaskRng(rng, true, reported, [&] { ++outside; }); });
    Check(inTask == &*rng && outside == 0 && !reported, "task rng: inside a task, the seeded source and no report");
    tr::TaskRng(rng, true, reported, [&] { ++outside; }).Record(true);   // the burst's first call (burst-start)
    const int roll = watched("a roll inside a task", [&] { return tr::TaskRng(rng, true, reported, [&] { ++outside; }).Int(1, 25); });
    Check(roll >= 1 && roll <= 25 && rng->Count() == 1, "task rng: the draw lands on the tape");
    watched("a draw outside a task", [&] { return &tr::TaskRng(rng, false, reported, [&] { ++outside; }); });
    watched("a second draw outside a task", [&] { return &tr::TaskRng(rng, false, reported, [&] { ++outside; }); });
    Check(outside == 1 && reported, "task rng: a draw outside a task is reported once");
    std::optional<tr::TraceRng> unseeded;
    tr::TraceRng* seeded = watched("an unseeded source", [&] { return &tr::TaskRng(unseeded, true, reported, [] {}); });
    Check(unseeded.has_value() && seeded == &*unseeded, "task rng: an unseeded source is seeded, never read empty");
}

int main(int argc, char** argv)
{
    try {
        if (argc < 2) {
            throw std::runtime_error("usage: trace_test <build/fix26-trace-format.json> [sample.log]");
        }
        LoadFormats(argv[1]);
        BufferChecks();
        RngChecks();
        TaskRngChecks();
        tr::Buffer buffer;
        EngineChecks(buffer);
        CrowdChecks();
        NameChecks();
        SinkChecks();
        TapeBoundsChecks();
        DispelByIdChecks();
        RouteChecks();
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
