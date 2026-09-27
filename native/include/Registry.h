#pragma once
// Round 27 (E1): our own effects on each actor, as the tasks last read them. The effect lists are walked only inside our
// SKSE tasks (one after another); the sinks and the read-only natives that ran beside them (the effect-removed sink, the
// death sink, GetStatus / GetStatusFloat / MarksOn) read this registry instead, so no thread walks a list a task is
// changing. The review's scenario: a kill dispatched on the window thread while the timer task re-applies a bleed (Dispel
// + Cast) on a worker -- the death sink walked freed nodes.
//
//   Snapshot      one actor's effects of ours (EffectView, the same rows ReadBoard reads), the game-running ms of the
//                 read, and the few foreign facts a sink needs (a cloak / an armour spell, the raise's servant marker)
//   Registry      FormID -> Snapshot under one small mutex, never held across an engine call; Publish (a task), Get (a
//                 copy), EraseUid (the removal sink: the effect that just left), Clear (a new session, E3)
//   SnapshotView  the snapshot as an engine for StatusEngine.h's templates (ReadBoard, DescribeRemoved), each effect's
//                 elapsed advanced by the time since the read
//   RemovedFrom   the removal sink's answer (OnRemoved's reasons) from the snapshot
//
// Pure: no engine. native/tests/runtime_test.cpp runs it with two threads publishing and reading.
#include "Locks.h"
#include "StatusEngine.h"

#include <cstdint>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <utility>
#include <vector>

namespace essb::reg {

// An effect whose estimated elapsed time is within this of its duration when it leaves counts as expired (the snapshot's
// clock is the timer's game-running milliseconds, 100 ms steps; a foreign dispel in the last 0.35 s settles like an
// expiry -- the only difference from the list read it replaces).
inline constexpr float kExpirySlack = 0.35f;

struct Snapshot {
    std::vector<engine::EffectView> ours;   // our effects (TagOf / our spells / our file)
    std::uint64_t atMs = 0;                 // game-running ms when the task read the list
    bool armorSpell = false;                // an armour spell's effect (ReadTarget's armorSpellEffect)
    bool cloak = false;                     // a cloak (ReadTarget's cloakEffect)
    bool servant = false;                   // our reanimate marker (亡衛's servant)
    bool bloodMark = false;                 // ReadTarget's other list facts (the death sink reads them from here)
    bool silenced = false;
    bool hushSpent = false;
    float hushMagnitude = 0.0f;
    int fromOurFile = 0;                    // effects whose record is ours (probe N5-1's count)
};

// The snapshot as StatusEngine.h's engine: rows in list order, elapsed advanced by `advance` seconds.
class SnapshotView
{
public:
    using Handle = std::size_t;

    SnapshotView(const Snapshot& s, float advance) noexcept : s_(s), advance_(advance) {}

    template <class Fn>
    void ForEach(Who, Fn&& fn) const
    {
        for (std::size_t i = 0; i < s_.ours.size(); ++i) {
            engine::EffectView v = s_.ours[i];
            v.elapsed += advance_;
            fn(v, i);
        }
    }
    template <class Fn>
    void ForEachIncludingEnding(Who who, Fn&& fn) const
    {
        ForEach(who, std::forward<Fn>(fn));
    }

private:
    const Snapshot& s_;
    float advance_;
};

inline float SecondsSince(const Snapshot& s, std::uint64_t nowMs) noexcept
{
    return nowMs > s.atMs ? static_cast<float>(static_cast<double>(nowMs - s.atMs) / 1000.0) : 0.0f;
}

// The board of a snapshot now (the effects' clocks advanced to `nowMs`; one that ran past its duration is left out -- it
// is gone, the removal sink just has not erased it yet).
inline Board BoardOf(const Snapshot& s, std::uint64_t nowMs)
{
    Board board;
    const float advance = SecondsSince(s, nowMs);
    for (const engine::EffectView& row : s.ours) {
        if (!row.effect) {
            continue;
        }
        const float elapsed = row.elapsed + advance;
        if (row.duration > 0.0f && elapsed > row.duration + kExpirySlack) {
            continue;
        }
        Read(board, RawEffect{ row.effect, row.magnitude, elapsed, row.duration });
    }
    return board;
}

// The effect-removed event from the snapshot: which of ours ended and why (as engine::OnRemoved tells them apart), with the
// crystals of the same moment. `settling` = only the kinds that settle (the sink); false = any of ours (the probe log).
inline engine::Removed RemovedFrom(const Snapshot& s, std::uint32_t uid, bool dead, std::uint64_t nowMs, bool settling)
{
    engine::Removed out;
    const engine::EffectView* row = nullptr;
    for (const engine::EffectView& v : s.ours) {
        if (v.uid == uid) {
            row = &v;
            break;
        }
    }
    if (!row) {
        return out;   // kIgnore: not ours, or never read by a task
    }
    out.tag = TagOf(row->effect);
    out.magnitude = row->magnitude;
    out.elapsed = row->elapsed + SecondsSince(s, nowMs);
    out.duration = row->duration;
    if (out.tag.kind == TagKind::kNone || (settling && !Settles(out.tag))) {
        out.reason = engine::Removal::kIgnore;
        return out;
    }
    Board seen;   // the board as the task read it (the crystals leave with the freeze, in the same frame)
    for (const engine::EffectView& v : s.ours) {
        if (v.effect) {
            Read(seen, RawEffect{ v.effect, v.magnitude, v.elapsed, v.duration });
        }
    }
    out.crystals = seen.Layers(StatusKind::kCrystal);
    const bool expired = out.duration > 0.0f && out.elapsed >= out.duration - kExpirySlack;
    out.reason = dead ? engine::Removal::kDeath : expired ? engine::Removal::kExpired : engine::Removal::kDispelled;
    if (out.reason == engine::Removal::kExpired && out.elapsed < out.duration) {
        out.elapsed = out.duration;   // settled as the engine's own expiry
    }
    return out;
}

// Round 27 (G9): the marks our tasks took off an actor in the last second (an end, a cut, a burst unmarks before its
// damage). A death in that second counts the actor as carrying them (v0.4 2.6: 帶印記死亡即化灰, 亡者歸来, 裁決 化灰), so a
// kill by the end's own damage is still a marked death. Written by a task's dispel, read by the death sink.
inline constexpr std::uint64_t kSettledWindowMs = 1000;

class SettledMarks
{
public:
    void Note(std::uint32_t actor, int element, std::uint64_t nowMs)
    {
        std::lock_guard lock(lock_);
        Prune(nowMs);
        rows_.push_back(Row{ actor, element, nowMs });
    }

    // The elements settled on `actor` within the window (a bit per element).
    std::uint32_t Recent(std::uint32_t actor, std::uint64_t nowMs) const
    {
        std::lock_guard lock(lock_);
        std::uint32_t mask = 0;
        for (const Row& r : rows_) {
            if (r.actor == actor && nowMs >= r.atMs && nowMs - r.atMs <= kSettledWindowMs && r.element > 0 && r.element < 32) {
                mask |= 1u << r.element;
            }
        }
        return mask;
    }

    void Clear()
    {
        std::lock_guard lock(lock_);
        rows_.clear();
    }

private:
    struct Row {
        std::uint32_t actor = 0;
        int element = 0;
        std::uint64_t atMs = 0;
    };
    void Prune(std::uint64_t nowMs)
    {
        std::erase_if(rows_, [nowMs](const Row& r) { return nowMs < r.atMs || nowMs - r.atMs > kSettledWindowMs; });
    }
    mutable lk::Mutex lock_;
    std::vector<Row> rows_;
};

// Round 27b (review B N9): an expiry end settles its mark too -- the mark that just ran out (its element, 0 for anything
// else) is noted before the end's damage, so a kill by the expiry end still counts as a marked death.
inline int ExpiredMarkOf(const engine::Removed& r) noexcept
{
    return r.tag.kind == TagKind::kMark && r.reason == engine::Removal::kExpired && IsElement(r.tag.index) ? r.tag.index : 0;
}

// A corpse's board with the marks settled on it in the last second (G9): those count as carried.
inline void WithSettled(Board& board, std::uint32_t mask) noexcept
{
    for (int e = kFire; e <= kAstral; ++e) {
        if ((mask & (1u << e)) && !board.mark[e].has) {
            board.mark[e] = Slot{ true, 0.0f, 0.0f, 1.0f };
        }
    }
}

// Round 27b (review A N2): an actor is its FormID AND its reference handle (index + reuse bits). A FormID of a created
// reference (FF......) is given again after the old one is deleted; its handle's reuse bits differ, so a snapshot of the
// dead one never answers for the new one.
struct Key {
    std::uint32_t form = 0;
    std::uint32_t handle = 0;
    Key() = default;
    Key(std::uint32_t f, std::uint32_t h = 0) noexcept : form(f), handle(h) {}   // NOLINT: a bare FormID is handle 0 (tests)
};

class Registry
{
public:
    // A task's fresh read of one actor (an empty one forgets it).
    void Publish(Key actor, Snapshot s)
    {
        std::lock_guard lock(lock_);
        if (s.ours.empty() && !s.servant) {
            map_.erase(actor.form);
        } else {
            map_[actor.form] = Entry{ actor.handle, std::move(s) };
        }
    }

    std::optional<Snapshot> Get(Key actor) const
    {
        std::lock_guard lock(lock_);
        const auto it = map_.find(actor.form);
        if (it == map_.end() || it->second.handle != actor.handle) {
            return std::nullopt;
        }
        return it->second.snapshot;
    }

    bool Has(Key actor) const
    {
        std::lock_guard lock(lock_);
        const auto it = map_.find(actor.form);
        return it != map_.end() && it->second.handle == actor.handle;
    }

    // The removal sink: the effect that just left is erased (the snapshot stays true without a task in between).
    void EraseUid(Key actor, std::uint32_t uid)
    {
        std::lock_guard lock(lock_);
        const auto it = map_.find(actor.form);
        if (it == map_.end() || it->second.handle != actor.handle) {
            return;
        }
        auto& rows = it->second.snapshot.ours;
        for (std::size_t i = 0; i < rows.size(); ++i) {
            if (rows[i].uid == uid) {
                rows.erase(rows.begin() + static_cast<std::ptrdiff_t>(i));
                break;
            }
        }
    }

    // Every death and every unload (TESObjectLoadedEvent, loaded = false): whatever the handle.
    void Forget(std::uint32_t actor)
    {
        std::lock_guard lock(lock_);
        map_.erase(actor);
    }

    void Clear()
    {
        std::lock_guard lock(lock_);
        map_.clear();
    }

    std::size_t Size() const
    {
        std::lock_guard lock(lock_);
        return map_.size();
    }

private:
    struct Entry {
        std::uint32_t handle = 0;
        Snapshot snapshot;
    };
    mutable lk::Mutex lock_;
    std::unordered_map<std::uint32_t, Entry> map_;
};

}  // namespace essb::reg
