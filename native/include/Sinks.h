#pragma once
// Round 26b (the commander's threading ruling): what the death sink and the input sink may do in the event itself. Both
// events arrive on a BSJobs worker (the death sink from the engine's own kill path, the input sink in the "Poll controls"
// job, which runs beside "Post process"), so each sink only reads what belongs to the event and queues the rest with SKSE
// AddTask, which runs right after the engine's own task queue in "Post process" -- the engine's serialization point.
//
//   DeathSink  reads the corpse only (our reanimate marker on it, how many of our effects, its own board and facts through
//              the world's ReadCorpse); the killer and the player are compared by identity, never read. The killer's
//              frenzy, the player's facts, the crowd and every write happen in the death task.
//   PlanInput  maps the key presses of one input event to switch / step actions; pure. The sink runs no switch itself
//              (RequestSwitch and the step marker run in a task: a hotkey may be one frame late).
// Pure: native/tests/trace_test.cpp runs both on a fake world that records every actor read and every write.
#include "StatusEngine.h"
#include "Timer.h"

#include <array>
#include <cstdint>
#include <vector>

namespace essb::sink {

struct DeathSeen {
    bool dyingIsYou = false;
    bool killerYou = false;
    bool servant = false;
    int ours = 0;            // our effects still on the corpse (only when `countOurs`)
    bool snapshot = false;   // a death the DLL handles (DeathCounts): the task plans it from the corpse read here
};

// `corpse`: the dying actor (read); `killer`, `you`: identities only. The world's reads: Servant(corpse),
// CountOurs(corpse), ReadCorpse(corpse) -> Board (the corpse's board, the world keeps the full snapshot).
template <class World, class Ref>
DeathSeen DeathSink(World& world, Ref corpse, const void* killer, const void* you, bool dead, bool countOurs)
{
    DeathSeen s;
    s.dyingIsYou = static_cast<const void*>(corpse) == you;
    s.killerYou = killer != nullptr && killer == you;
    if (s.dyingIsYou) {
        return s;
    }
    s.servant = world.Servant(corpse);
    if (countOurs) {
        s.ours = world.CountOurs(corpse);
    }
    if (dead) {
        return s;   // the dead = true event: effects may be gone (native-verification-3 s10); only logged
    }
    const engine::DeathEvent e{ dead, s.dyingIsYou, s.killerYou, s.servant };
    s.snapshot = engine::DeathCounts(e, world.ReadCorpse(corpse));
    return s;
}

// Round 26c (the heap audit): in this load order TESHitEvent arrives on the window thread (Precision / TDM resolve hits
// from a Main::Update hook) while every SKSE task runs on a Post-process worker -- so the hit sink does no engine work at
// all: it reads the event and the hit-time facts, filters, and queues the hit; planning, casts, dispels and actor-value
// writes run in the hit task. A hit event that arrives while a hit task runs on the same thread (our own casts) is
// dropped, as the old re-entrancy guard did.
enum class HitRoute : std::uint8_t
{
    kIgnore,   // neither yours nor on you
    kNested,   // raised by our own hit task on this thread: dropped
    kHurt,     // on you: snapshot for the hurt task
    kYours,    // yours: filter here, then the hit task
};

constexpr HitRoute RouteHit(bool causeIsYou, bool targetIsYou, bool insideHitTask) noexcept
{
    if (insideHitTask) {
        return HitRoute::kNested;
    }
    if (causeIsYou) {
        return HitRoute::kYours;
    }
    return targetIsYou ? HitRoute::kHurt : HitRoute::kIgnore;
}

// One button of an input event, as the sink read it from the event itself.
struct Press {
    Device device = Device::kOther;
    std::uint32_t id = 0;
    bool down = false;
};

enum class ActionKind : std::uint8_t
{
    kSwitch,   // RequestSwitch(element, "hotkey") in a task
    kStep,     // the probe log's step marker (+1 / -1) in a task
};

struct Action {
    ActionKind kind = ActionKind::kSwitch;
    int element = 0;     // kSwitch
    int delta = 0;       // kStep
    int code = 0;        // the key code (the log)
    bool accepted = false;   // the gate was open (a blocked hotkey is an action with accepted = false, only logged)
};

struct InputFacts {
    bool active = false;        // the DLL is ready and in game (Active())
    bool enabled = false;       // the master switch (Enabled())
    bool hotkeys = false;       // ESSB_HotkeysEnabled
    bool trace = false;         // the probe log level
    std::array<int, kElementCount> keys{};
    int stepNext = 0;           // DIK codes of the step keys
    int stepBack = 0;
    InputGate gate{};           // snapshotted in the sink (GateNow)
};

// Pure: what one input event asks for. Blocked hotkeys come back with accepted = false (the sink logs them); blocked
// step keys are dropped.
inline std::vector<Action> PlanInput(const std::vector<Press>& presses, const InputFacts& f)
{
    std::vector<Action> out;
    const bool open = InputOpen(f.gate);
    for (const Press& p : presses) {
        if (!p.down) {
            continue;
        }
        if (f.active && f.trace && p.device == Device::kKeyboard && open &&
            (static_cast<int>(p.id) == f.stepNext || static_cast<int>(p.id) == f.stepBack)) {
            out.push_back(Action{ ActionKind::kStep, 0, static_cast<int>(p.id) == f.stepNext ? 1 : -1, static_cast<int>(p.id), true });
            continue;
        }
        if (!f.enabled || !f.hotkeys) {
            continue;
        }
        const int code = KeyCodeOf(p.device, p.id);
        const int element = HotkeyElement(code, true, f.keys);
        if (element == 0) {
            continue;
        }
        out.push_back(Action{ ActionKind::kSwitch, element, 0, code, open });
    }
    return out;
}

}  // namespace essb::sink
