// Round 27: the engine glue that no longer needs the engine (native/include/Runtime.h, Registry.h) -- run offline.
//   scope     one engine-mutating body at a time: nesting counts once, two threads at once are reported, an SEH exit's
//             reset puts the count back (E9)
//   session   the epoch and inGame through data load, the main menu, a new game, a load, a failed load, the main menu
//             again (E3): a task queued in an older session never acts; the new-game path starts a session like a load
//   log       the log never fails the plugin (G12): the main file, a PID-suffixed one, none -- a throwing opener included;
//             Query fills the plugin info before it opens the log, and a failed log does not change its answer
//   seh       only an access violation inside this DLL is swallowed (E2)
//   gate      the hotkeys' input gate from the UI counters and the input menus (E6)
//   event     the ModEvent's text is never cut (E12), a name is cut at a character's edge (Trace.h Utf8Fit)
//   registry  a task's snapshot answers the removal sink (expired / dispelled / death, the crystals), the death sink's board
//             and the read-only natives; the removal erases its row; two threads publishing and reading at once (E1)
//   hurt      a hit waits for its frame's end; "after" and our own health changes per hit (E4, G7); PlanHurt's loss leaves
//             out our own payments
#include "Registry.h"
#include "Runtime.h"
#include "Trace.h"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

using essb::StatusKind;
namespace rt = essb::rt;
namespace reg = essb::reg;

int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
}

bool Near(double a, double b, double tol = 1e-4)
{
    return std::abs(a - b) <= tol * std::max(1.0, std::abs(b));
}

struct NoNodes {
    int Rank(const essb::NodeId&) const { return 0; }
    bool Has(const essb::BranchId&) const { return false; }
};

struct MidRng {
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return lo + (hi - lo) * 0.5f; }
    bool Chance(float) { return false; }
};

// ---------------------------------------------------------------- scope

void ScopeChecks()
{
    rt::ScopeCounters c;
    int overlaps = 0;
    const auto report = [&](const char*, const char*) { ++overlaps; };
    {
        bool inTask = false;
        rt::Scope outer("a", inTask, c, report);
        Check(inTask && c.mutating == 1, "scope: one body open");
        {
            rt::Scope nested("b", inTask, c, report);
            Check(c.mutating == 1, "scope: a nested body on the same thread counts once");
        }
        Check(inTask && c.mutating == 1, "scope: the nested scope leaves the outer open");
    }
    Check(c.mutating == 0 && overlaps == 0, "scope: closed, no overlap");
    // two threads inside at once: reported
    std::atomic<int> stage{ 0 };
    std::thread other([&]() {
        bool inTask = false;
        rt::Scope s("other", inTask, c, report);
        stage = 1;
        while (stage.load() != 2) {
            std::this_thread::yield();
        }
    });
    while (stage.load() != 1) {
        std::this_thread::yield();
    }
    {
        bool inTask = false;
        rt::Scope mine("mine", inTask, c, report);
        Check(overlaps == 1 && c.mutating == 2, "scope: two threads at once are one overlap");
    }
    stage = 2;
    other.join();
    Check(c.mutating == 0, "scope: both closed");
    // E9: an SEH exit skips the destructor; the reset puts the count and the flag back, the destructor then does nothing
    bool inTask = false;
    {
        rt::Scope s("faulted", inTask, c, report);
        rt::ResetScope(inTask, c);
        Check(!inTask && c.mutating == 0, "scope: the reset after a fault");
    }
    Check(c.mutating == 0, "scope: no double decrement after a reset");
    rt::ResetScope(inTask, c);
    Check(c.mutating == 0, "scope: a reset outside a task changes nothing");
}

// ---------------------------------------------------------------- session (E3)

void SessionChecks()
{
    rt::Session s;
    auto t = rt::OnMessage(s, rt::Msg::kDataLoaded);
    Check(t.loadManifest && !s.inGame, "session: data load resolves, no game yet");
    const rt::Ticket boot = rt::Take(s);
    t = rt::OnMessage(s, rt::Msg::kMainMenu);   // the main menu at start
    Check(!s.inGame && !rt::Valid(s, boot), "session: nothing acts at the main menu");
    // the new-game path (the round-27 report): kNewGame with no PreLoadGame before it
    const rt::Ticket beforeNew = rt::Take(s);
    t = rt::OnMessage(s, rt::Msg::kNewGame);
    Check(t.gameReady && t.clearRegistry, "session: a new game starts a session (game ready, the old snapshots go)");
    const rt::Ticket ready = rt::Take(s);   // OnGameReady queues its task before the game runs
    Check(!rt::Valid(s, ready) && rt::SameSession(s, ready), "session: the game-ready task is of the new session");
    rt::GameReady(s);
    Check(s.inGame && rt::Valid(s, ready) && !rt::Valid(s, beforeNew), "session: the new game runs; a task queued before it does nothing");
    const rt::Ticket playing = rt::Take(s);
    Check(rt::Valid(s, playing), "session: a task of the running game acts");
    // a load
    t = rt::OnMessage(s, rt::Msg::kPreLoadGame);
    Check(!s.inGame && t.flush && t.publish && t.clearRegistry && !rt::Valid(s, playing), "session: a load ends the session");
    t = rt::OnMessage(s, rt::Msg::kPostLoadGameFailed);
    Check(!t.gameReady && !s.inGame, "session: a failed load starts nothing");
    t = rt::OnMessage(s, rt::Msg::kPreLoadGame);
    t = rt::OnMessage(s, rt::Msg::kPostLoadGame);
    Check(t.gameReady, "session: a load that worked starts one");
    rt::GameReady(s);
    const rt::Ticket loaded = rt::Take(s);
    Check(rt::Valid(s, loaded) && !rt::Valid(s, playing), "session: the old game's tasks stay dead after the load");
    t = rt::OnMessage(s, rt::Msg::kSaveGame);
    Check(t.flush && s.inGame && rt::Valid(s, loaded), "session: a save changes nothing but the flush");
    t = rt::OnMessage(s, rt::Msg::kMainMenu);   // quit to the main menu
    Check(!s.inGame && !rt::Valid(s, loaded), "session: the main menu ends the session");
    t = rt::OnMessage(s, rt::Msg::kNewGame);
    rt::GameReady(s);
    Check(s.inGame && !rt::Valid(s, loaded), "session: a second new game from the menu");
}

// ---------------------------------------------------------------- the log and Query (G12)

void LogChecks()
{
    int tries = 0;
    Check(rt::OpenLogWith([&](bool) { ++tries; return true; }) == rt::LogPick::kMain && tries == 1, "log: the main file");
    tries = 0;
    Check(rt::OpenLogWith([&](bool pid) { ++tries; return pid; }) == rt::LogPick::kPid && tries == 2, "log: the main file held -> the PID file");
    Check(rt::OpenLogWith([](bool pid) -> bool {
        if (!pid) {
            throw std::runtime_error("locked");
        }
        return true;
    }) == rt::LogPick::kPid, "log: a throwing open -> the PID file");
    Check(rt::OpenLogWith([](bool) -> bool { throw std::runtime_error("no directory"); }) == rt::LogPick::kNone, "log: none at all");

    // Query: the info before the log; the log decides nothing
    std::vector<std::string> order;
    bool answer = rt::Query([&]() { order.push_back("fill"); return true; }, [&]() { order.push_back("log"); throw std::runtime_error("locked"); },
        [&]() { order.push_back("check"); return true; });
    Check(answer && order == std::vector<std::string>{ "fill", "log", "check" }, "query: fill, log (failing), check -- still accepted");
    order.clear();
    answer = rt::Query([&]() { order.push_back("fill"); return false; }, [&]() { order.push_back("log"); }, [&]() { order.push_back("check"); return true; });
    Check(!answer && order == std::vector<std::string>{ "fill" }, "query: no info -> refused before anything else");
    answer = rt::Query([]() { return true; }, []() {}, []() -> bool { throw std::runtime_error("x"); });
    Check(!answer, "query: a throwing check refuses, never escapes");
    answer = rt::Query([]() { return true; }, []() {}, []() { return false; });
    Check(!answer, "query: the runtime check decides");
}

// ---------------------------------------------------------------- SEH (E2)

void SehChecks()
{
    const std::uintptr_t base = 0x180000000, end = 0x180140000;
    Check(rt::SehVerdict(rt::kAccessViolation, base + 0x59E46, base, end) == rt::Seh::kHandle, "seh: our access violation is ours");
    Check(rt::SehVerdict(rt::kAccessViolation, 0x140C15F75, base, end) == rt::Seh::kPass, "seh: the engine's access violation passes");
    Check(rt::SehVerdict(rt::kStackOverflow, base + 0x10, base, end) == rt::Seh::kPass, "seh: a stack overflow passes");
    Check(rt::SehVerdict(rt::kCppException, base + 0x10, base, end) == rt::Seh::kPass, "seh: a C++ exception passes (to its catch)");
    Check(rt::SehVerdict(rt::kAccessViolation, base + 0x10, 0, 0) == rt::Seh::kPass, "seh: before the DLL's range is known, nothing is swallowed");
    Check(rt::SehVerdict(rt::kAccessViolation, end, base, end) == rt::Seh::kPass, "seh: the range's end is outside");
}

// ---------------------------------------------------------------- the input gate (E6)

void GateChecks()
{
    rt::UiFacts u;
    Check(essb::InputOpen(rt::GateFrom(u)), "gate: gameplay takes the key");
    for (int k = 0; k < 7; ++k) {
        rt::UiFacts x;
        (k == 0 ? x.paused : k == 1 ? x.modal : k == 2 ? x.itemMenu : k == 3 ? x.applicationMenu : k == 4 ? x.console : k == 5 ? x.inputMenu : x.textEntry) = true;
        Check(!essb::InputOpen(rt::GateFrom(x)), "gate: blocked by fact " + std::to_string(k));
    }
    rt::UiFacts loading;
    loading.loading = true;
    Check(!essb::InputOpen(rt::GateFrom(loading)) && rt::GateFrom(loading).loading, "gate: the loading menu");
    rt::UiFacts noGame;
    noGame.inGame = false;
    Check(rt::GateFrom(noGame).loading, "gate: no game running counts as loading");
    std::set<std::string_view> names(rt::kInputMenus.begin(), rt::kInputMenus.end());
    Check(names.size() == rt::kInputMenus.size() && names.contains("Dialogue Menu") && names.contains("Favorites Menu"),
        "gate: the input menus (the dialogue and favourites menus take keys without pausing)");
}

// ---------------------------------------------------------------- the ModEvent text and names (E12)

bool ValidUtf8(std::string_view s)
{
    std::size_t i = 0;
    while (i < s.size()) {
        const auto u = static_cast<unsigned char>(s[i]);
        const std::size_t n = u < 0x80 ? 1 : (u & 0xE0) == 0xC0 ? 2 : (u & 0xF0) == 0xE0 ? 3 : (u & 0xF8) == 0xF0 ? 4 : 0;
        if (n == 0 || i + n > s.size()) {
            return false;
        }
        for (std::size_t k = 1; k < n; ++k) {
            if ((static_cast<unsigned char>(s[i + k]) & 0xC0) != 0x80) {
                return false;
            }
        }
        i += n;
    }
    return true;
}

void TextChecks()
{
    std::array<float, 8> big;
    big.fill(3.0e38f);
    big[7] = -3.0e38f;
    const std::string text = rt::EventText(big, false, 0);
    Check(std::count(text.begin(), text.end(), '|') == 7 && text.size() > 256, "event: eight huge numbers, none cut (" + std::to_string(text.size()) + " chars)");
    Check(text.substr(text.rfind('|') + 1).rfind("-3", 0) == 0 && text.ends_with(".00000"), "event: the last number is whole");
    std::array<float, 8> push{ 1.5f, 2.25f, 3.0f, 1.0f, 0.5f, 0, 0, 0 };
    Check(rt::EventText(push, true, -16777216) == "1.50000|2.25000|3.00000|-16777216|0.50000", "event: the push's centre as a signed FormID");

    // a CJK name longer than the name buffer: cut at a character's edge
    std::string name;
    for (int i = 0; i < 30; ++i) {
        name += "瘟疫狼";   // 3 bytes each
    }
    essb::trace::ActorFacts a;
    a.has = true;
    a.name = name;
    essb::trace::Line line("op");
    line.Actor("on", a);
    Check(ValidUtf8(line.Body()), "name: the cut name is whole characters");
    Check(essb::trace::Utf8Fit(name, 64) == 63 && essb::trace::Utf8Fit(name, 63) == 63 && essb::trace::Utf8Fit(name, 62) == 60,
        "name: Utf8Fit stops before a split character");
    Check(essb::trace::Utf8Fit("abc", 10) == 3, "name: a short name is kept");
    // a long line cut at kMaxLine ends on a character's edge
    essb::trace::Line longLine("pap");
    for (int i = 0; i < 400; ++i) {
        longLine.F("%s", "寂");
    }
    Check(longLine.Cut() && ValidUtf8(longLine.Body()) && longLine.Body().size() <= essb::trace::kMaxLine, "line: a cut line keeps whole characters");
}

// ---------------------------------------------------------------- the registry (E1)

essb::engine::EffectView Row(std::uint32_t uid, std::uint32_t effect, float magnitude, float elapsed, float duration)
{
    essb::engine::EffectView v;
    v.uid = uid;
    v.effect = effect;
    v.magnitude = magnitude;
    v.elapsed = elapsed;
    v.duration = duration;
    v.ours = true;
    return v;
}

void RegistryChecks()
{
    using essb::engine::Removal;
    const auto mark = essb::status::kMarkEffect[essb::kFire];
    const auto frozen = essb::kStatusRecords[static_cast<int>(StatusKind::kFrozen)].effect;
    const auto crystal = essb::kStatusRecords[static_cast<int>(StatusKind::kCrystal)].effect;
    reg::Registry r;
    reg::Snapshot s;
    s.atMs = 10000;
    s.ours = { Row(1, mark, 2.0f, 1.0f, 8.0f), Row(2, frozen, 1.0f, 2.5f, 3.0f), Row(3, crystal, 4.0f, 2.5f, 3.0f) };
    s.fromOurFile = 3;
    r.Publish(0xFF001234, s);
    Check(r.Has(0xFF001234) && r.Size() == 1, "registry: published");
    // the freeze ends by time half a second later (the timer's clock at 10500): expired, with the 4 crystals of that moment
    auto got = r.Get(0xFF001234);
    auto x = reg::RemovedFrom(*got, 2, false, 10500, true);
    Check(x.reason == Removal::kExpired && x.crystals == 4 && x.tag.kind == essb::TagKind::kStatus, "registry: the freeze expired, 4 crystals");
    // the same effect leaving at 10100 (0.4 s early) is a dispel; 10200 (within the slack) counts as the expiry
    Check(reg::RemovedFrom(*got, 2, false, 10100, true).reason == Removal::kDispelled, "registry: early = dispelled");
    Check(reg::RemovedFrom(*got, 2, false, 10200, true).reason == Removal::kExpired, "registry: within the slack = expired");
    Check(reg::RemovedFrom(*got, 2, true, 10500, true).reason == Removal::kDeath, "registry: dead = death");
    Check(reg::RemovedFrom(*got, 99, false, 10500, true).reason == Removal::kIgnore, "registry: an unknown effect is not ours");
    Check(reg::RemovedFrom(*got, 3, false, 10500, true).reason == Removal::kIgnore, "registry: crystals do not settle");
    Check(reg::RemovedFrom(*got, 3, false, 10500, false).reason == Removal::kExpired, "registry: the probe log describes any of ours");
    // the board now: the clocks advanced; the freeze is gone after its duration (+ the slack)
    essb::Board b = reg::BoardOf(*got, 10400);
    Check(b.mark[essb::kFire].has && Near(b.mark[essb::kFire].elapsed, 1.4f) && b.Has(StatusKind::kFrozen), "registry: board at 10.4 s");
    b = reg::BoardOf(*got, 11000);
    Check(b.mark[essb::kFire].has && !b.Has(StatusKind::kFrozen) && !b.Has(StatusKind::kCrystal), "registry: the freeze has run out by 11 s");
    // the removal erases its row; a snapshot of nothing forgets the actor
    r.EraseUid(0xFF001234, 2);
    got = r.Get(0xFF001234);
    Check(got && got->ours.size() == 2 && reg::RemovedFrom(*got, 2, false, 10500, true).reason == Removal::kIgnore, "registry: the removed row is gone");
    r.Publish(0xFF001234, reg::Snapshot{});
    Check(!r.Has(0xFF001234), "registry: an actor with nothing of ours is forgotten");
    reg::Snapshot servant;
    servant.servant = true;
    r.Publish(7, servant);
    Check(r.Has(7) && r.Get(7)->servant, "registry: a servant marker keeps the actor");
    r.Clear();
    Check(r.Size() == 0, "registry: a new session clears it");
    // the snapshot as an engine for StatusEngine.h's templates
    const reg::SnapshotView view(s, 0.5f);
    const essb::Board viaEngine = essb::engine::ReadBoard(view, essb::Who::kTarget);
    Check(viaEngine.Has(StatusKind::kFrozen) && Near(viaEngine[StatusKind::kFrozen].elapsed, 3.0f), "registry: the view advances the clocks");

    // two threads: a task publishing, a sink reading and erasing, at once
    reg::Registry shared;
    std::atomic_bool stop{ false };
    std::atomic<int> reads{ 0 };
    std::thread writer([&]() {
        for (std::uint32_t i = 0; i < 20000; ++i) {
            reg::Snapshot w;
            w.atMs = i;
            w.ours = { Row(i, mark, 1.0f, 0.0f, 8.0f), Row(i + 1, frozen, 1.0f, 0.0f, 3.0f) };
            shared.Publish(i % 16, std::move(w));
        }
        stop = true;
    });
    std::thread reader([&]() {
        while (!stop.load()) {
            for (std::uint32_t a = 0; a < 16; ++a) {
                if (auto g = shared.Get(a)) {
                    const essb::Board bb = reg::BoardOf(*g, g->atMs);
                    if (bb.MarkCount() > 1) {
                        throw std::runtime_error("registry: a torn snapshot");
                    }
                    shared.EraseUid(a, g->ours.empty() ? 0 : g->ours.front().uid);
                    ++reads;
                }
            }
        }
    });
    writer.join();
    reader.join();
    Check(reads.load() > 0, "registry: read while written (" + std::to_string(reads.load()) + " reads, no torn snapshot)");
}

// ---------------------------------------------------------------- the hurt queue (E4, G7)

void HurtChecks()
{
    rt::HurtQueue<int> q;
    auto entry = [](int who, float before, std::uint64_t frame, std::uint64_t at, double ledger) {
        rt::HurtEntry<int> e;
        e.attacker = who;
        e.facts.healthBefore = before;
        e.frame = frame;
        e.atMs = at;
        e.ledger = ledger;
        return e;
    };
    // frame 5: two hits; frame 6: one
    q.Push(entry(1, 100.0f, 5, 1000, 0.0));
    q.Push(entry(2, 90.0f, 5, 1001, -10.0));   // our blood cost of 10 came between the two (not the enemy's)
    q.Push(entry(3, 70.0f, 6, 1016, -10.0));
    // the task runs in frame 5 (the damage of frame 5 may not be applied yet): nothing is taken
    auto b = q.Take(5, 1010);
    Check(b.ready.empty() && b.more, "hurt: a hit waits for its frame's end");
    // frame 6: the two hits of frame 5; the third (frame 6) waits and gives the second its "after"
    b = q.Take(6, 1020);
    Check(b.ready.size() == 2 && b.more && b.nextBefore && *b.nextBefore == 70.0f, "hurt: the earlier frame's hits, in order");
    rt::AssignAfter(b, 50.0f, -25.0);
    Check(b.ready[0].attacker == 1 && b.ready[0].facts.healthAfter == 90.0f && Near(b.ready[0].facts.ownDelta, -10.0),
        "hurt: the first hit's after = the second's before; our own -10 in between");
    Check(b.ready[1].facts.healthAfter == 70.0f && Near(b.ready[1].facts.ownDelta, 0.0), "hurt: the second's after = the waiting hit's before");
    // later: the third, with 15 of our own payments since its sink
    b = q.Take(7, 1030);
    rt::AssignAfter(b, 40.0f, -25.0);
    Check(b.ready.size() == 1 && !b.more && b.ready[0].facts.healthAfter == 40.0f && Near(b.ready[0].facts.ownDelta, -15.0),
        "hurt: the last hit's after = your health now, our own -15 left out");
    // a frame counter that stopped: the hit is taken after kHurtMaxWaitMs
    q.Push(entry(4, 40.0f, 9, 2000, 0.0));
    Check(q.Take(9, 2000 + rt::kHurtMaxWaitMs - 1).ready.empty(), "hurt: waits while the frame runs");
    Check(q.Take(9, 2000 + rt::kHurtMaxWaitMs).ready.size() == 1, "hurt: taken after the longest wait");
    q.Push(entry(5, 40.0f, 9, 2000, 0.0));
    q.Clear();
    Check(!q.Pending(), "hurt: a new session clears the waiting hits");

    // the ledger
    rt::HealthLedger ledger;
    ledger.Add(-10.0f);
    ledger.Add(4.5f);
    Check(Near(ledger.Now(), -5.5), "hurt: the ledger sums our own changes");

    // PlanHurt (Hurt.h): a spell hit without a form -- 化法為力 gives back 30% of the loss as magicka. The enemy did 20; our
    // own blood cost took 10 more between the sink and the task: the loss is 20, not 30 (G7).
    essb::Config c;
    essb::Tuning t;
    essb::StatusInputs in;
    in.config = &c;
    in.tuning = &t;
    in.formElement = 0;
    in.player.health = 70.0f;
    in.self = essb::Self{ 70.0f, 100.0f, 100.0f };
    essb::HurtFacts f;
    f.spell = true;
    f.healthBefore = 100.0f;
    f.healthAfter = 70.0f;
    f.ownDelta = -10.0f;
    f.magickaMax = 100.0f;
    essb::Board attacker, me;
    MidRng rng;
    auto plan = std::make_unique<essb::StatusPlan>();
    essb::PlanHurt(*plan, f, attacker, me, in, NoNodes{}, rng);
    float restored = -1.0f;
    for (int i = 0; i < plan->count; ++i) {
        if (plan->ops[i].op == essb::Op::kRestoreMagicka) {
            restored = plan->ops[i].magnitude;
        }
    }
    Check(Near(restored, 6.0), "hurt: 化法為力 on the enemy's 20 only (got " + std::to_string(restored) + ", 9 = our own cost counted)");
    // our own heal of 5 between: the enemy did 35 (100 -> 70 with +5 of ours)
    f.ownDelta = 5.0f;
    plan = std::make_unique<essb::StatusPlan>();
    essb::PlanHurt(*plan, f, attacker, me, in, NoNodes{}, rng);
    restored = -1.0f;
    for (int i = 0; i < plan->count; ++i) {
        if (plan->ops[i].op == essb::Op::kRestoreMagicka) {
            restored = plan->ops[i].magnitude;
        }
    }
    Check(Near(restored, 10.5), "hurt: our own heal does not hide the enemy's damage");
}

// ---------------------------------------------------------------- the killing blow's corpse (G6)

// A fake engine for StatusEngine.h RunPlan: counts what lands on the target (the corpse) and on you.
struct CorpseEngine {
    using Handle = int;
    struct Row {
        essb::Who who;
        essb::engine::EffectView v;
        bool alive = true;
    };
    std::vector<Row> rows;
    bool corpse = true;
    int castsOnTarget = 0, castsOnYou = 0, dispelsOnTarget = 0, events = 0;
    void Select(std::uint8_t) {}
    template <class Fn>
    void ForEach(essb::Who who, Fn&& fn)
    {
        for (int i = 0; i < static_cast<int>(rows.size()); ++i) {
            if (rows[i].who == who && rows[i].alive) {
                fn(rows[i].v, i);
            }
        }
    }
    void Dispel(essb::Who who, Handle h)
    {
        rows[h].alive = false;
        dispelsOnTarget += who == essb::Who::kTarget ? 1 : 0;
    }
    bool SelfDispel() const { return false; }
    void SetSelfDispel(bool) {}
    void Cast(essb::Who who, std::uint32_t, float, float) { (who == essb::Who::kTarget ? castsOnTarget : castsOnYou) += 1; }
    bool Dead(essb::Who who) { return corpse && who == essb::Who::kTarget; }
    bool IsCorpse(essb::Who who) const { return corpse && who == essb::Who::kTarget; }
    void DrainMagickaAll(essb::Who) {}
    void PayHealth(float) {}
    void Send(const essb::StatusOp&) { ++events; }
    void HurtHealth(float) {}
    void PayStamina(float) {}
    void Resonance() {}
    void Interrupt(essb::Who) {}
    void CrushArea(const essb::StatusOp&) {}
    void FreezeNearby() {}
    void LogReapply(const essb::StatusOp&, int) {}
    void LogWash(const essb::engine::EffectView&, bool) {}
};

void CorpseChecks()
{
    essb::Config c;
    essb::Tuning t;
    essb::StatusInputs in;
    in.config = &c;
    in.tuning = &t;
    in.n4 = true;
    in.formElement = essb::kFrost;
    for (const bool corpse : { true, false }) {
        essb::Board target;
        target.mark[essb::kFire] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
        essb::Board me;
        MidRng rng;
        auto plan = std::make_unique<essb::StatusPlan>();
        // a frost hit cuts the fire mark: the fire end, the frost mark, your sync
        const essb::HitStatus st = essb::PlanStatusHit(*plan, essb::kFrost, false, target, me, in, NoNodes{}, rng);
        essb::SelfHit hit;
        hit.element = essb::kFrost;
        hit.formElement = essb::kFrost;
        essb::PlanSelfHit(*plan, hit, st, target, me, in, NoNodes{}, rng);
        Check(st.cutFrom == essb::kFire, "corpse: the hit cuts the fire mark");
        CorpseEngine e;
        e.corpse = corpse;
        essb::engine::EffectView fire;
        fire.uid = 1;
        fire.effect = essb::status::kMarkEffect[essb::kFire];
        fire.magnitude = 0.0f;
        fire.elapsed = 2.0f;
        fire.duration = 8.0f;
        e.rows.push_back({ essb::Who::kTarget, fire });
        essb::engine::RunPlan(e, *plan, t);
        if (corpse) {
            Check(e.castsOnTarget == 0 && e.dispelsOnTarget == 0, "corpse: nothing is cast on or dispelled from the corpse (" +
                std::to_string(e.castsOnTarget) + " casts, " + std::to_string(e.dispelsOnTarget) + " dispels)");
            Check(e.events >= 1, "corpse: the cut end still settles (its event reaches the bodies / Papyrus)");
            Check(e.castsOnYou >= 1, "corpse: your resources still accrue (the sync)");
        } else {
            Check(e.castsOnTarget >= 1 && e.dispelsOnTarget >= 1, "alive: the frost mark is cast and the fire mark dispelled");
        }
    }
}

// ---------------------------------------------------------------- the marks just settled (G9)

void SettledChecks()
{
    essb::reg::SettledMarks s;
    s.Note(0xFF000001, essb::kDivine, 5000);
    s.Note(0xFF000002, essb::kDarkness, 5100);
    Check(s.Recent(0xFF000001, 5900) == (1u << essb::kDivine), "settled: the divine mark counts within the second");
    Check(s.Recent(0xFF000001, 6001) == 0u, "settled: not after it");
    essb::Board corpse;
    essb::reg::WithSettled(corpse, s.Recent(0xFF000002, 5600));
    Check(corpse.mark[essb::kDarkness].has && corpse.MarkCount() == 1, "settled: the corpse carries the dark mark the end took");
    Check(essb::engine::DeathCounts(essb::engine::DeathEvent{}, corpse), "settled: the death counts as a marked death");
    s.Clear();
    Check(s.Recent(0xFF000002, 5600) == 0u, "settled: a new session clears them");
}

// ---------------------------------------------------------------- (T) Plugin.cpp's rules without the engine

struct FakeEffect {
    std::uint16_t uid = 0;
    int base = 0;
    bool dispelled = false;
};

// ---------------------------------------------------------------- round 27b: review A

void Review27bChecks()
{
    namespace rt = essb::rt;
    // N2: a FormID given again to a new reference (another handle's reuse bits) never reads the old snapshot
    reg::Registry r;
    reg::Snapshot s;
    s.ours = { Row(1, essb::status::kMarkEffect[essb::kFire], 2.0f, 1.0f, 8.0f) };
    r.Publish(reg::Key{ 0xFF000800, 0x00100007 }, s);
    Check(r.Has(reg::Key{ 0xFF000800, 0x00100007 }) && r.Get(reg::Key{ 0xFF000800, 0x00100007 }), "registry: the same reference reads its snapshot");
    Check(!r.Has(reg::Key{ 0xFF000800, 0x00500007 }) && !r.Get(reg::Key{ 0xFF000800, 0x00500007 }),
        "registry: a new reference with the same FormID (other reuse bits) reads nothing");
    r.EraseUid(reg::Key{ 0xFF000800, 0x00500007 }, 1);
    Check(r.Get(reg::Key{ 0xFF000800, 0x00100007 })->ours.size() == 1, "registry: the new reference's removal does not touch the old row");
    r.Forget(0xFF000800);
    Check(r.Size() == 0, "registry: a death / an unload forgets the FormID whatever the handle");

    // N3: the world clock -- paused frames (0) and stalls add nothing
    rt::WorldClock clock;
    clock.Frame(0.016f);
    clock.Frame(0.0f);
    clock.Frame(5.0f);
    clock.Frame(0.5f);
    Check(clock.Ms() == 516, "world clock: 16 ms + 500 ms, a paused frame and a 5 s stall add nothing (" + std::to_string(clock.Ms()) + ")");

    // N4 / N5: the SEH filter with a lock held, and a stack overflow
    const std::uintptr_t base = 0x180000000, end = 0x180140000;
    Check(rt::SehVerdict(rt::kAccessViolation, base + 0x10, base, end, 1) == rt::Seh::kPass, "seh: our access violation with a lock held passes");
    Check(rt::SehQuiet(rt::kStackOverflow) && !rt::SehQuiet(rt::kAccessViolation), "seh: a stack overflow is passed on doing nothing");
    {
        essb::lk::Mutex m;
        Check(essb::lk::Held() == 0, "locks: none held");
        {
            std::lock_guard lock(m);
            Check(essb::lk::Held() == 1, "locks: a lock of ours counts itself");
        }
        std::unique_lock later(m, std::try_to_lock);
        Check(later.owns_lock() && essb::lk::Held() == 1, "locks: try_lock counts too");
    }
    Check(essb::lk::Held() == 0, "locks: released, none held");
    essb::lk::EnterEngineLock();
    Check(rt::SehVerdict(rt::kAccessViolation, base + 0x10, base, end, essb::lk::Held()) == rt::Seh::kPass, "seh: inside an engine lock scope, passed on");
    essb::lk::LeaveEngineLock();

    // N6: the game-ready task queued before inGame turns on runs in its session
    rt::Session session;
    rt::OnMessage(session, rt::Msg::kPostLoadGame);
    const rt::Ticket ready = rt::Take(session);
    Check(!rt::Valid(session, ready) && rt::SameSession(session, ready), "session: the game-ready task runs before inGame (the epoch decides)");

    // N8: the main menu ends the session, faulted or not
    Check(rt::MenuEndsSession(true, true, true) && !rt::MenuEndsSession(false, true, true) && !rt::MenuEndsSession(true, false, true) &&
            !rt::MenuEndsSession(true, true, false),
        "menu: opening the main menu in a game ends the session");

    // N7: in corpse mode only the cut end's event names the corpse
    Check(essb::engine::CorpseSends(essb::Event::kEnd), "corpse: the cut end's event is sent");
    for (const essb::Event e : { essb::Event::kOpen, essb::Event::kAsh, essb::Event::kRaise, essb::Event::kSneak, essb::Event::kPush,
             essb::Event::kKnock, essb::Event::kHallucinate, essb::Event::kDomain, essb::Event::kJudgment }) {
        Check(!essb::engine::CorpseSends(e), "corpse: the death task's (or nothing's) event " + std::to_string(static_cast<int>(e)) + " is not sent");
    }

    // B-N7: 連殺's sneak record -- a non-sneak hit clears the target's row
    {
        std::vector<std::tuple<std::uint32_t, int, std::uint64_t>> rows;
        rt::NoteSneakHit(rows, 7, true, 6, 1000);
        Check(rows.size() == 1, "sneak: a sneak hit leaves its row");
        rt::NoteSneakHit(rows, 7, false, 6, 1200);
        Check(rows.empty(), "sneak: a later non-sneak hit on the same target clears it");
        rt::NoteSneakHit(rows, 8, true, 1, 1300);
        rt::NoteSneakHit(rows, 9, true, 1, 9000);
        Check(rows.size() == 1 && std::get<0>(rows[0]) == 9, "sneak: rows older than 5 s go");
    }

    // B-N9: an expiry end's mark is noted as settled (a kill by it is a marked death)
    {
        essb::engine::Removed gone;
        gone.tag = essb::Tag{ essb::TagKind::kMark, essb::kDarkness };
        gone.reason = essb::engine::Removal::kExpired;
        Check(reg::ExpiredMarkOf(gone) == essb::kDarkness, "settled: the dark mark that ran out is noted");
        gone.reason = essb::engine::Removal::kDispelled;
        Check(reg::ExpiredMarkOf(gone) == 0, "settled: a dispelled mark is the dispel's (noted there)");
        gone.reason = essb::engine::Removal::kExpired;
        gone.tag = essb::Tag{ essb::TagKind::kStatus, 3 };
        Check(reg::ExpiredMarkOf(gone) == 0, "settled: a status is not a mark");
    }

    // N10: only what a cast of that magnitude can do is ours
    Check(Near(rt::OwnDelta(100.0f, 80.0f, 5.0f), -5.0f), "own health: a 5-point cost while a 15-point hit lands counts 5");
    Check(Near(rt::OwnDelta(100.0f, 130.0f, 20.0f), 20.0f), "own health: a heal of 20 counts at most 20");
    Check(Near(rt::OwnDelta(100.0f, 90.0f, 0.0f), 0.0f), "own health: a cast with no magnitude counts nothing");
    Check(Near(rt::OwnDelta(100.0f, 97.0f, 5.0f), -3.0f), "own health: the change itself when within the bound");
}

void PluginRuleChecks()
{
    namespace rt = essb::rt;
    // DispelCollected: two effects of base 7 are picked; dispelling the first removes a third effect from the list (a
    // cloak's payload), which moves the second -- it must still be found by (uid, base), never by a kept position.
    const int bases[2] = { 7, 9 };
    std::vector<FakeEffect> list{ { 1, 0 }, { 2, 1 }, { 3, 0 } };
    std::vector<std::uint16_t> order;
    auto walk = [&](auto&& visit) {
        for (auto& e : list) {
            visit(e.uid, static_cast<const void*>(&bases[e.base]), &e);
        }
    };
    const int n = rt::DispelCollected(walk, [&](FakeEffect* e, const void*) { return e->base == 0; },
        [&](FakeEffect* e) {
            order.push_back(e->uid);
            const std::uint16_t uid = e->uid;
            list.erase(std::remove_if(list.begin(), list.end(), [&](const FakeEffect& x) { return x.uid == uid || (uid == 1 && x.uid == 2); }),
                list.end());
        });
    Check(n == 2 && order == std::vector<std::uint16_t>{ 1, 3 } && list.empty(), "dispel: both picked effects re-found after the list changed");
    // two instances of one base: only the picked one (uid 6) goes, not the first of that base
    std::vector<FakeEffect> twins{ { 5, 0 }, { 6, 0 } };
    std::vector<std::uint16_t> hit;
    rt::DispelCollected(
        [&](auto&& visit) {
            for (auto& e : twins) {
                visit(e.uid, static_cast<const void*>(&bases[e.base]), &e);
            }
        },
        [](FakeEffect* e, const void*) { return e->uid == 6; }, [&](FakeEffect* e) { hit.push_back(e->uid); });
    Check(hit == std::vector<std::uint16_t>{ 6 }, "dispel: the picked instance by its unique id, not the first of its base");
    std::vector<FakeEffect> gone{ { 4, 0 } };
    int calls = 0;
    const int none = rt::DispelCollected(
        [&](auto&& visit) {
            for (auto& e : gone) {
                visit(e.uid, static_cast<const void*>(&bases[e.base]), &e);
            }
            if (calls++ == 0) {
                gone.clear();   // it ran out between the collect and the dispel
            }
        },
        [](FakeEffect*, const void*) { return true; }, [](FakeEffect*) { throw std::runtime_error("dispelled a gone effect"); });
    Check(none == 0, "dispel: an effect gone before its dispel is skipped");

    // GuardRun: the master switch, the read-only natives, the SEH frame, C++ exceptions -- each to the fallback, one fault.
    Check(!rt::GuardOpen(false, true, false) && rt::GuardOpen(true, true, false) && !rt::GuardOpen(true, false, true),
        "guard: switched off, only the read-only natives answer (while active)");
    std::vector<rt::GuardFault> faults;
    auto fault = [&](rt::GuardFault kind, const char*) { faults.push_back(kind); };
    auto seh = [](auto& run) { run(); return true; };
    volatile bool raise = true;   // a throw the compiler cannot see through (C4702 in the guard's instantiation otherwise)
    Check(rt::GuardRun([] { return true; }, [] { return 5; }, -1, seh, fault) == 5 && faults.empty(), "guard: the body's answer");
    Check(rt::GuardRun([] { return false; }, [&]() -> int { if (raise) throw std::runtime_error("ran"); return 5; }, -1, seh, fault) == -1 && faults.empty(),
        "guard: closed, the body never runs");
    Check(rt::GuardRun([] { return true; }, [&]() -> int { if (raise) throw std::runtime_error("boom"); return 5; }, -1, seh, fault) == -1 &&
            faults == std::vector<rt::GuardFault>{ rt::GuardFault::kException },
        "guard: a C++ exception -> the fallback and one fault");
    faults.clear();
    Check(rt::GuardRun([] { return true; }, [] { return 5; }, -1, [](auto&) { return false; }, fault) == -1 &&
            faults == std::vector<rt::GuardFault>{ rt::GuardFault::kSeh },
        "guard: the SEH frame caught one -> the fallback and one fault");
    faults.clear();
    Check(rt::GuardRun([&]() -> bool { if (raise) throw 3; return true; }, [] { return 5; }, -1, seh, fault) == -1 && faults == std::vector<rt::GuardFault>{ rt::GuardFault::kUnknown },
        "guard: the switch read itself failing -> the fallback");

    // PlanTick: the clock always; switched off the bars go and nothing else; stopped nothing; env and second only when due.
    essb::Beat due;
    due.second = due.env = true;
    const auto off = rt::PlanTick(false, true, false, due);
    Check(off.clock && off.hudOff && !off.run && !off.env && !off.second, "tick: switched off, the clock and the bars only");
    const auto stopped = rt::PlanTick(true, true, true, due);
    Check(stopped.clock && !stopped.hudOff && !stopped.run && !stopped.second, "tick: stopped, nothing but the clock");
    const auto on = rt::PlanTick(true, true, false, due);
    Check(on.run && on.env && on.second, "tick: running and due, the environment and the second");
    Check(!rt::PlanTick(true, true, false, essb::Beat{}).second && !rt::PlanTick(true, false, false, due).run, "tick: not due / no player");

    // ReadEngaged: only the living, non-hostile, non-follower actors near enough have their effect list walked.
    Check(rt::ReadEngaged(false, false, false, 3.0f, 99.0f, 4.0f, 4.0f), "crowd: a near bystander is read");
    Check(!rt::ReadEngaged(true, false, false, 1.0f, 1.0f, 4.0f, 4.0f) && !rt::ReadEngaged(false, true, false, 1.0f, 1.0f, 4.0f, 4.0f) &&
            !rt::ReadEngaged(false, false, true, 1.0f, 1.0f, 4.0f, 4.0f) && !rt::ReadEngaged(false, false, false, 9.0f, 9.0f, 4.0f, 4.0f),
        "crowd: hostile, follower, dead or far -- no list walk");
}

}  // namespace

int main()
{
    try {
        ScopeChecks();
        SessionChecks();
        LogChecks();
        SehChecks();
        GateChecks();
        TextChecks();
        RegistryChecks();
        HurtChecks();
        CorpseChecks();
        SettledChecks();
        PluginRuleChecks();
        Review27bChecks();
        std::printf("NATIVE RUNTIME ok: %d checks (task scopes, the session and new game, the log and Query, SEH, the input gate, "
                    "event text and UTF-8, the effect registry with two threads, the hurt queue and our own health, the corpse mode, the settled marks, "
                    "the dispel re-find, the native guard, the tick order, the crowd read)\n",
            checks);
        return 0;
    } catch (const std::exception& e) {
        std::printf("NATIVE RUNTIME FAILED: %s\n", e.what());
        return 1;
    }
}
