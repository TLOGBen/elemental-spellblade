#pragma once
// Round 27: the parts of Plugin.cpp's plumbing that do not need the engine, so native/tests/runtime_test.cpp runs them.
//
//   Scope / ResetScope  one engine-mutating body at a time (round 26c P5): the count of open scopes, the overlap report,
//                       the reset an SEH exit needs (E9: an __except skips the scope's destructor)
//   Session             the game session (E3): an epoch bumped on PreLoadGame / NewGame / the main menu, `inGame`, and the
//                       transitions MessageCpp and the menu sink make; a Ticket taken when a task is queued is valid only
//                       in the same epoch while a game runs (a task queued before a load or the main menu does nothing)
//   HurtQueue           the hits you took (E4 + G7): each with the frame it arrived in and your own health ledger at that
//                       moment; the hurt task takes only the hits of earlier frames (the engine has applied their damage by
//                       then) and subtracts what our own costs and heals did to your health in between
//   OpenLogWith, Query  the log never fails the plugin (G12): the main file, else a PID-suffixed one, else none; Query fills
//                       the plugin info before anything else
//   SehVerdict          which structured exceptions a guard may swallow (E2): an access violation inside this DLL only;
//                       anything else (the engine's, a stack overflow) is logged and passed on
//   GateFrom            the hotkeys' input gate from the UI's counters and the input-taking menus by name (E6: no walk of
//                       UI::menuStack off its thread)
//   EventText           the ModEvent's '|'-joined numbers, never truncated (E12)
//   (T) DispelCollected  DispelLive's rule (round 26c P2): collect by (unique id, base), re-find each right before its dispel
//   (T) GuardRun         every ESSBNative body: the master switch (read-only natives answer while it is off), the SEH frame,
//                        C++ exceptions -- each ends in the fallback and one fault
//   (T) PlanTick         the timer task's order: the clock always first, the bars off when switched off, nothing while
//                        stopped, the environment before the second
//   (T) ReadEngaged      the crowd read's rule: the engaged marker (an effect-list walk) only for a non-hostile, living,
//                        non-follower actor near enough to matter
#include "Hurt.h"
#include "Locks.h"
#include "Timer.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

namespace essb::rt {

// ---------------------------------------------------------------- task scopes (round 26c P5, round 27 E9)

struct ScopeCounters {
    std::atomic<int> mutating{};
    std::atomic<const char*> name{};
};

// `inTask` is the calling thread's flag (Plugin.cpp: thread_local). A nested scope on the same thread counts once.
template <class OnOverlap>
class Scope
{
public:
    Scope(const char* name, bool& inTask, ScopeCounters& c, OnOverlap onOverlap) noexcept : inTask_(inTask), c_(c), outer_(inTask)
    {
        if (outer_) {
            return;
        }
        inTask_ = true;
        const char* other = c_.name.exchange(name);
        if (c_.mutating.fetch_add(1) + 1 > 1) {
            onOverlap(name, other);
        }
    }
    ~Scope()
    {
        if (outer_ || !inTask_) {
            return;   // nested, or already reset (a fault inside the body)
        }
        inTask_ = false;
        if (c_.mutating.fetch_sub(1) <= 0) {
            c_.mutating = 0;
        }
    }
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;

private:
    bool& inTask_;
    ScopeCounters& c_;
    bool outer_;
};

// An SEH exit (or a fault) inside a body: the scope's destructor will not run, so the thread's flag and the count go back.
inline void ResetScope(bool& inTask, ScopeCounters& c) noexcept
{
    if (!inTask) {
        return;
    }
    inTask = false;
    if (c.mutating.fetch_sub(1) <= 0) {
        c.mutating = 0;
    }
}

// ---------------------------------------------------------------- the game session (E3)

enum class Msg : std::uint8_t
{
    kDataLoaded,
    kPreLoadGame,
    kPostLoadGame,        // the load succeeded
    kPostLoadGameFailed,  // SKSE's success flag was false: no game runs
    kNewGame,
    kSaveGame,
    kMainMenu,            // the main menu opened (quit to it, or the start)
};

struct Session {
    std::atomic<std::uint32_t> epoch{ 1 };
    std::atomic_bool inGame{};
};

// What MessageCpp does for one message besides the session's own fields.
struct Transition {
    bool loadManifest = false;   // resolve the forms, register the sinks
    bool gameReady = false;      // OnGameReady: the deferred notices, the load's resets (a task), the status
    bool flush = false;          // write the probe log now
    bool publish = false;        // ESSB_NativeHit again
    bool clearRegistry = false;  // the old session's snapshots and hits go (Registry.h, HurtQueue)
};

inline Transition OnMessage(Session& s, Msg m) noexcept
{
    Transition t;
    switch (m) {
    case Msg::kDataLoaded:
        t.loadManifest = true;
        break;
    case Msg::kPreLoadGame:
    case Msg::kMainMenu:
        s.inGame = false;
        s.epoch.fetch_add(1);
        t.flush = true;
        t.publish = true;
        t.clearRegistry = true;
        break;
    case Msg::kNewGame:
        // a new game from the main menu (no PreLoadGame before it): a new session all the same
        s.epoch.fetch_add(1);
        t.clearRegistry = true;
        t.gameReady = true;
        break;
    case Msg::kPostLoadGame:
        t.gameReady = true;
        break;
    case Msg::kPostLoadGameFailed:
        break;
    case Msg::kSaveGame:
        t.flush = true;
        break;
    }
    return t;
}

// OnGameReady's last step: the game runs from here.
inline void GameReady(Session& s) noexcept
{
    s.inGame = true;
}

struct Ticket {
    std::uint32_t epoch = 0;
};

inline Ticket Take(const Session& s) noexcept
{
    return Ticket{ s.epoch.load() };
}

// A queued task may act only in the session it was queued in, while a game runs.
inline bool Valid(const Session& s, const Ticket& t) noexcept
{
    return s.inGame.load() && s.epoch.load() == t.epoch;
}

// The game-ready task itself runs before `inGame` may be seen by its thread: the epoch alone.
inline bool SameSession(const Session& s, const Ticket& t) noexcept
{
    return s.epoch.load() == t.epoch;
}

// ---------------------------------------------------------------- your own health changes (G7)

// Σ of every change our own tasks made to your health (a payment -, a heal +, the part of a hit a pool passed on -). Only
// the tasks write it (one at a time); the hit sink reads it.
class HealthLedger
{
public:
    void Add(float delta) noexcept
    {
        double was = total_.load();
        while (!total_.compare_exchange_weak(was, was + static_cast<double>(delta))) {
        }
    }
    double Now() const noexcept { return total_.load(); }
    void Reset() noexcept { total_ = 0.0; }

private:
    std::atomic<double> total_{};
};

// ---------------------------------------------------------------- the hits you took (E4 + G7)

// A hit is taken when its frame is over (the input sink counts frames: BSInputDeviceManager polls once a frame), or when
// it has waited this long (a frame counter that stops -- a menu with no polling -- never keeps a hit forever).
inline constexpr std::uint64_t kHurtMaxWaitMs = 150;

template <class Who>
struct HurtEntry {
    Who attacker{};
    HurtFacts facts{};
    std::uint64_t frame = 0;
    std::uint64_t atMs = 0;
    double ledger = 0.0;   // HealthLedger::Now() at the sink
};

template <class Who>
struct HurtBatch {
    std::vector<HurtEntry<Who>> ready;
    bool more = false;                    // hits of this frame stay for the next task
    std::optional<float> nextBefore;      // the first remaining hit's health before (the last ready one's "after")
    std::optional<double> nextLedger;
};

template <class Who>
class HurtQueue
{
public:
    void Push(HurtEntry<Who> e)
    {
        std::lock_guard lock(lock_);
        q_.push_back(std::move(e));
    }

    bool Pending() const
    {
        std::lock_guard lock(lock_);
        return !q_.empty();
    }

    // The hits of frames before `frame` (and any that waited kHurtMaxWaitMs), in arrival order; stops at the first one
    // that must wait, so the order is kept.
    HurtBatch<Who> Take(std::uint64_t frame, std::uint64_t nowMs)
    {
        HurtBatch<Who> out;
        std::lock_guard lock(lock_);
        std::size_t n = 0;
        while (n < q_.size() && (q_[n].frame < frame || nowMs - q_[n].atMs >= kHurtMaxWaitMs)) {
            ++n;
        }
        out.ready.assign(std::make_move_iterator(q_.begin()), std::make_move_iterator(q_.begin() + static_cast<std::ptrdiff_t>(n)));
        q_.erase(q_.begin(), q_.begin() + static_cast<std::ptrdiff_t>(n));
        out.more = !q_.empty();
        if (out.more) {
            out.nextBefore = q_.front().facts.healthBefore;
            out.nextLedger = q_.front().ledger;
        }
        return out;
    }

    void Clear()
    {
        std::lock_guard lock(lock_);
        q_.clear();
    }

private:
    mutable lk::Mutex lock_;
    std::vector<HurtEntry<Who>> q_;
};

// Each ready hit's health after it (the next hit's "before", the last one's the first waiting hit's or your health now)
// and what our own changes did in between (the ledger's difference): Hurt.h's lost = before - after + ownDelta.
template <class Who>
void AssignAfter(HurtBatch<Who>& b, float healthNow, double ledgerNow) noexcept
{
    for (std::size_t i = 0; i < b.ready.size(); ++i) {
        HurtFacts& f = b.ready[i].facts;
        const bool last = i + 1 == b.ready.size();
        const float after = !last ? b.ready[i + 1].facts.healthBefore : b.nextBefore ? *b.nextBefore : healthNow;
        const double ledgerAfter = !last ? b.ready[i + 1].ledger : b.nextLedger ? *b.nextLedger : ledgerNow;
        f.healthAfter = after;
        f.ownDelta = static_cast<float>(ledgerAfter - b.ready[i].ledger);
    }
}

// ---------------------------------------------------------------- the log and SKSEPlugin_Query (G12)

enum class LogPick : std::uint8_t
{
    kMain,   // ElementsSpellblade.log
    kPid,    // ElementsSpellblade-<pid>.log (the main one is held by a game process that has not exited yet)
    kNone,   // no log at all; the plugin runs the same
};

// `open(pidSuffix)` tries one file and returns whether it opened; it may throw (caught here).
template <class Open>
LogPick OpenLogWith(Open&& open) noexcept
{
    for (const bool pid : { false, true }) {
        try {
            if (open(pid)) {
                return pid ? LogPick::kPid : LogPick::kMain;
            }
        } catch (...) {
        }
    }
    return LogPick::kNone;
}

// SKSEPlugin_Query: the info first (SKSE reports a plugin whose Query failed as "(00000000 <NULL> 00000000) incompatible"),
// then the log (never decides anything), then the runtime check.
template <class Fill, class OpenLog, class Check>
bool Query(Fill&& fill, OpenLog&& openLog, Check&& check) noexcept
{
    try {
        if (!fill()) {
            return false;
        }
    } catch (...) {
        return false;
    }
    try {
        openLog();
    } catch (...) {
    }
    try {
        return check();
    } catch (...) {
        return false;
    }
}

// ---------------------------------------------------------------- structured exceptions (E2)

inline constexpr std::uint32_t kAccessViolation = 0xC0000005u;
inline constexpr std::uint32_t kStackOverflow = 0xC00000FDu;
inline constexpr std::uint32_t kCppException = 0xE06D7363u;

enum class Seh : std::uint8_t
{
    kHandle,   // ours to swallow: an access violation at an address inside this DLL
    kPass,     // log, flush, EXCEPTION_CONTINUE_SEARCH (the game's own crash handling sees it)
};

// Round 27b (review A N4): never while this thread holds a lock of ours or an engine lock scope we entered (`locksHeld`,
// Locks.h): the swallowed exception would leave the lock held and the next task would hang on it.
constexpr Seh SehVerdict(std::uint32_t code, std::uintptr_t at, std::uintptr_t base, std::uintptr_t end, int locksHeld = 0) noexcept
{
    return code == kAccessViolation && locksHeld == 0 && base != 0 && at >= base && at < end ? Seh::kHandle : Seh::kPass;
}

// Round 27b (review A N5): a stack overflow is passed on at once, the filter doing nothing (no log, no flush: there is no
// stack left for them).
constexpr bool SehQuiet(std::uint32_t code) noexcept
{
    return code == kStackOverflow;
}

// ---------------------------------------------------------------- the hotkeys' input gate (E6)

// Menus that take the keyboard without pausing the game (a pausing one is UI::numPausesGame; an item menu, an application
// menu and a modal one have their own counters). By name: UI::IsMenuOpen finds the menu in the registered map and reads its
// on-stack flag -- no walk of UI::menuStack, which the UI thread changes.
inline constexpr std::array<std::string_view, 12> kInputMenus = { "Console", "Dialogue Menu", "Favorites Menu", "Crafting Menu", "BarterMenu",
    "GiftMenu", "Training Menu", "Lockpicking Menu", "Book Menu", "ContainerMenu", "MessageBoxMenu", "CustomMenu" };

struct UiFacts {
    bool inGame = true;
    bool paused = false;          // UI::GameIsPaused (numPausesGame > 0)
    bool modal = false;           // UI::IsModalMenuOpen
    bool itemMenu = false;        // UI::IsItemMenuOpen
    bool applicationMenu = false; // UI::IsApplicationMenuOpen
    bool console = false;         // IsMenuOpen("Console")
    bool loading = false;         // IsMenuOpen("Loading Menu")
    bool inputMenu = false;       // any of kInputMenus open
    bool textEntry = false;       // ControlMap::textEntryCount > 0
};

constexpr InputGate GateFrom(const UiFacts& u) noexcept
{
    InputGate g;
    g.loading = !u.inGame || u.loading;
    g.paused = u.paused;
    g.console = u.console;
    g.menu = u.modal || u.itemMenu || u.applicationMenu || u.inputMenu;
    g.textEntry = u.textEntry;
    return g;
}

// ---------------------------------------------------------------- the ModEvent's numbers (E12)

// "%.5f|%.5f|…" of the 8 numbers (the push: 3, the centre's FormID, 1), fixed-point (Papyrus' String -> Float cast reads no
// exponent). Grown until it fits: a float's %.5f is up to 47 characters.
inline std::string EventText(const std::array<float, 8>& a, bool push, std::int32_t centre)
{
    std::string out(512, '\0');
    for (;;) {
        const int n = push ? std::snprintf(out.data(), out.size(), "%.5f|%.5f|%.5f|%d|%.5f", a[0], a[1], a[2], centre, a[4])
                           : std::snprintf(out.data(), out.size(), "%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f", a[0], a[1], a[2], a[3], a[4],
                                 a[5], a[6], a[7]);
        if (n < 0) {
            return std::string();
        }
        if (static_cast<std::size_t>(n) < out.size()) {
            out.resize(static_cast<std::size_t>(n));
            return out;
        }
        out.assign(static_cast<std::size_t>(n) + 1, '\0');
    }
}

// ---------------------------------------------------------------- (27e) branches bought in a skill menu (0.27.4)

// One route's branches as bits (tier × 4 + index): the StatsMenu snapshot and the mask after it (a branch costs 5 points
// and the Custom Skills Framework takes 1; ESSBTrees takes the other 4 for each bit gained).
constexpr std::uint32_t BranchBit(int tier, int index) noexcept
{
    return (tier >= 0 && tier < 5 && index >= 0 && index < 4) ? (1u << (tier * 4 + index)) : 0u;
}

constexpr std::uint32_t Gained(std::uint32_t before, std::uint32_t now) noexcept
{
    return now & ~before;
}

// ---------------------------------------------------------------- (27e) the lethal event's pace (0.27.4)

// A hit that leaves you at or below 0 without dying (god mode, an essential player, 神佑's deferred kill) sends ESSB_Lethal
// at most once a second: every further hit in that second would only queue the same Papyrus event again.
inline constexpr std::uint64_t kLethalEveryMs = 1000;

constexpr bool LethalDue(std::uint64_t lastMs, std::uint64_t nowMs) noexcept
{
    return lastMs == 0 || nowMs < lastMs || nowMs - lastMs >= kLethalEveryMs;
}

// ---------------------------------------------------------------- (27d) the form ring's watch (0.27.3)

// One of our effects by its local FormID: a form ring (ESSB_FormRingEffect_<X>_<stage>) or not.
struct Ring {
    bool ring = false;
    int element = 0;   // 1..11
    int stage = 0;     // 0..stages-1
};

constexpr Ring RingOf(std::uint32_t local, std::uint32_t first, int stages) noexcept
{
    if (stages <= 0 || local < first || local >= first + static_cast<std::uint32_t>(11 * stages)) {
        return Ring{};
    }
    const int offset = static_cast<int>(local - first);
    return Ring{ true, 1 + offset / stages, offset % stages };
}

// ---------------------------------------------------------------- (27c) the planner's context (0.27.2)

// What a planner needs besides the boards (Plugin.cpp MakeContext fills it). `in.tuning` points at this object's own
// `tuning`. MakeContext returns it by value; in 0.27.1 MSVC copied it (NRVO is not guaranteed) and the copy's pointer still
// named MakeContext's dead local -- a burst or an expiry settle, whose crowd scan then reused that stack, read garbage
// tunings (ESSB_MultDrain ~4e22, a cooldown of ~0 s: effectiveness 0, a fire damage of inf). Every copy and assignment
// now points at its own tuning. The offline tests never copied such a struct (they build StatusInputs in place).
struct Context {
    Tuning tuning{};
    PlayerFacts player{};
    StatusInputs in{};

    Context() = default;
    Context(const Context& other) : tuning(other.tuning), player(other.player), in(other.in) { in.tuning = &tuning; }
    Context& operator=(const Context& other)
    {
        tuning = other.tuning;
        player = other.player;
        in = other.in;
        in.tuning = &tuning;
        return *this;
    }
};

// ---------------------------------------------------------------- (27b) the registry's clock (review A N3)

// The game-world clock the effects' own elapsed time follows (the engine's world-time frame delta: 0 while paused, slowed by
// Slow Time): the input sink adds each frame's delta. A delta outside (0, 1] s is a stall or a bad read and adds nothing.
class WorldClock
{
public:
    void Frame(float seconds) noexcept
    {
        if (seconds > 0.0f && seconds <= 1.0f) {
            us_.fetch_add(static_cast<std::uint64_t>(static_cast<double>(seconds) * 1000000.0 + 0.5));
        }
    }
    std::uint64_t Ms() const noexcept { return us_.load() / 1000; }

private:
    std::atomic<std::uint64_t> us_{};
};

// ---------------------------------------------------------------- (27b) our own health change, exactly (review A N10)

// A cast of ours on you changed your health by after - before; only the part a spell of that magnitude can cause counts
// (|delta| <= bound): another hit landing in the same moment is not ours. bound 0 (no magnitude): nothing counts.
constexpr float OwnDelta(float before, float after, float bound) noexcept
{
    const float d = after - before;
    const float b = bound > 0.0f ? bound : 0.0f;
    return d > b ? b : d < -b ? -b : d;
}

// ---------------------------------------------------------------- (27b) 連殺's sneak record (review B N7)

// The hit sink's row for `target`: every accepted hit replaces it; a non-sneak hit leaves none (a later non-sneak kill
// never reads an older sneak hit); rows older than 5 s go.
template <class Rows>
void NoteSneakHit(Rows& rows, std::uint32_t target, bool sneak, int formElement, std::uint64_t now)
{
    std::erase_if(rows, [&](const auto& row) { return std::get<0>(row) == target || now - std::get<2>(row) > 5000; });
    if (sneak) {
        rows.emplace_back(target, formElement, now);
    }
}

// ---------------------------------------------------------------- (27b) the menu sink's session end (review A N8)

// The main menu ends the session whether the DLL faulted or not (a faulted DLL's old tasks must still stop).
constexpr bool MenuEndsSession(bool opening, bool mainMenu, bool inGame) noexcept
{
    return opening && mainMenu && inGame;
}

// ---------------------------------------------------------------- (T) the collect-then-dispel rule (round 26c P2)

// `walk(visit)` calls visit(uid, base, handle) for every running effect of one actor; `match(handle, base)` picks;
// `dispel(handle)` dispels one. Each picked effect is re-found by (uid, base) in a fresh walk right before its dispel -- an
// earlier dispel may have changed the list, so no handle is kept across dispels. Returns how many were dispelled.
template <class Walk, class Match, class Dispel>
int DispelCollected(Walk&& walk, Match&& match, Dispel&& dispel)
{
    std::vector<std::pair<std::uint16_t, const void*>> found;
    walk([&](std::uint16_t uid, const void* base, auto handle) {
        if (match(handle, base)) {
            found.emplace_back(uid, base);
        }
    });
    int dispelled = 0;
    for (const auto& [uid, base] : found) {
        bool done = false;
        walk([&](std::uint16_t u, const void* b, auto handle) {
            if (!done && u == uid && b == base) {
                done = true;
                dispel(handle);
            }
        });
        dispelled += done ? 1 : 0;
    }
    return dispelled;
}

// ---------------------------------------------------------------- (T) the native guard (round 22, round 27 E2)

enum class GuardFault : std::uint8_t
{
    kSeh,         // an access violation inside the body (the SEH frame swallowed it)
    kException,   // a C++ exception (its message)
    kUnknown,     // anything else thrown
};

// A native's body may run: the ones that change something stop with the master switch; the read-only ones (GetStatus,
// MarksOn, ...) keep answering while the DLL is active, so the MCM status button works with the switch off.
constexpr bool GuardOpen(bool readOnly, bool active, bool enabled) noexcept
{
    return readOnly ? active : enabled;
}

// `open()` decides (read inside the try); `seh(run)` runs `run` inside the caller's SEH frame and says whether it returned;
// `fault(kind, message)` records one fault. The fallback answers every failure.
template <class Open, class Body, class Seh, class Fault>
auto GuardRun(Open&& open, Body&& body, decltype(body()) fallback, Seh&& seh, Fault&& fault) noexcept -> decltype(body())
{
    try {
        if (!open()) {
            return fallback;
        }
        std::optional<decltype(body())> out;
        auto run = [&]() { out.emplace(body()); };
        if (!seh(run) || !out) {
            fault(GuardFault::kSeh, nullptr);
            return fallback;
        }
        return std::move(*out);
    } catch (const std::exception& e) {
        fault(GuardFault::kException, e.what());
    } catch (...) {
        fault(GuardFault::kUnknown, nullptr);
    }
    return fallback;
}

// ---------------------------------------------------------------- (T) the timer task's order (round 25, round 27 E5 / E13)

struct TickPlan {
    bool clock = true;     // the game-running clock advances (always: Papyrus's windows end even switched off or faulted)
    bool hudOff = false;   // switched off: the TrueHUD bars go (E13)
    bool run = false;      // the per-tick work (decay, the executor, the mirrors)
    bool env = false;      // the 5 s environment check, before the second (the storm's charge reads it)
    bool second = false;   // the per-second work (維持費, 長流, domains, the magicka close)
};

constexpr TickPlan PlanTick(bool enabled, bool player, bool stopped, const Beat& beat) noexcept
{
    TickPlan p;
    p.hudOff = !enabled;
    p.run = enabled && player && !stopped;
    p.env = p.run && beat.env;
    p.second = p.run && beat.second;
    return p;
}

// ---------------------------------------------------------------- (T) the crowd read (round 22, round 26)

// The engaged marker is read (a walk of that actor's effect list) only for a living, non-hostile, non-follower actor
// within `aroundPrimary` of the centre or `aroundYou` of you; everyone else is decided without it.
constexpr bool ReadEngaged(bool hostile, bool teammate, bool dead, float toCentre, float toYou, float aroundPrimary, float aroundYou) noexcept
{
    return !hostile && !teammate && !dead && (toCentre <= aroundPrimary || toYou <= aroundYou);
}

}  // namespace essb::rt
