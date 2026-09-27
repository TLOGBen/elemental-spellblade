// ElementsSpellblade.dll - native on-hit handler for Skyrim SE 1.5.97 + SKSE 2.0.20.
//
// Hit handling runs in stages (Handle):
//   1. filter       ReadHitFacts + essb::Filter        which hits count (HitPipeline.h, pure)
//   2. read facts   ReadPlayer / ReadTarget / ReadBoard  engine reads only; EngineFacts.h maps them (pure)
//   3. plan         essb::PlanHit + essb::PlanStatusHit what to cast and how strong (HitMath.h, Status.h, pure)
//   4. apply        Apply + Execute                    CastSpellImmediate / Dispel(true), one override per spell
//   5. report       Report                             log line and, at debug level >= 2, an on-screen notice
// Round 20 (N2): the magnitude is computed here at hit time. Round 21 (v0.4 trees): 反擊, 寂滅, the soaked slow.
// Round 22 (N3): the target status layer and the fire / divine self ladders are engine effects this DLL applies:
//   * at hit time (the hit sink): marks open / refresh / cut, the element's status, the reactions' state part;
//   * when one of our "settles at the end" effects runs out (the effect-removed sink, read-only, work via AddTask);
//   * on a 100 ms timer thread that posts one main-thread task per tick (ladder decay, the white-hot fire source);
//   * for the Papyrus reaction bodies, through ESSBNative natives over the same effects.
// Round 23 (N4): your own resources are effects on you too (SelfLayer.h); a hit whose target is you goes through the
// same sink to Hurt.h (the facts before the damage in the sink, the damage itself in a follow-up task); the spell-cast
// sink runs 反咒 and 逼近; the timer decays 超載 and refunds 風's sprint; the resource pools and the sync bar are shown
// through TrueHUD's custom widget API when TrueHUD is there (TrueHud.h).
// Round 24 (N5): the reaction bodies, the fusion (融斷) and the death handling are the DLL's (Reactions.h). Every event
// that has bodies reads ONE crowd (the high process list, main thread, handles collected first; StatusEngine.h
// SelectCrowd), the body pass turns the plan's body events into casts on the crowd, and only what stays Papyrus (pushes,
// fear / frenzy, the raise, the ash, keep-sneak, domains, experience, sounds) goes out as ModEvents.
// Round 25 (N6): the timer does the per-second work Papyrus did (Timer.h: 維持費, 魔力歸零 2 秒, blood's upkeep, 長流 and
// 長河, the environment every 5 s, the storm's charge, the silence's drain), counting only the time the game runs; the
// domains are engine hazards the DLL places at the fused target's feet (Spawn Hazard) and finds again each second for
// what they do to you and to the enemies inside; the hotkeys come through an input event sink.
// Round 26: the probe log (MCM 除錯等級 4, Trace.h). Every observable a step of build/probes-all.md checks is one line
// "[ESSB][T][kind] #seq g=… r=… key=value…", buffered and written by the timer thread once a second; the step marker
// (ESSB_ProbeStep, numpad + / -, or `set ESSB_ProbeStep to N`) splits the log per station. Nothing it does changes play.
// The design state lives in those effects; `state` holds only handles, forms and faults. Faults latch the handler OFF
// until the game restarts.
#include "EngineFacts.h"
#include "HitPipeline.h"
#include "Hurt.h"
#include "Load.h"
#include "ManifestData.h"
#include "Reactions.h"
#include "Selection.h"
#include "Sinks.h"
#include "SelfLayer.h"
#include "Status.h"
#include "StatusEngine.h"
#include "Timer.h"
#include "Trace.h"
#include "TrueHud.h"

#include <Windows.h>
#include <bcrypt.h>
#include <intrin.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

namespace {

constexpr char kPlugin[] = "Elements Spellblade.esp";
constexpr char kSkyrim[] = "Skyrim.esm";
constexpr std::uint32_t kSkseVersion = 0x02000140;  // 2.0.20 packed
constexpr std::uint64_t kProcNoticeIntervalMs = 1000;
// 1.0 = the engine leaves the magnitude unchanged (0x140540360); 0.0 would clamp every proc to 1 point.
constexpr float kEffectiveness = 1.0f;
// 0 = no override: the engine keeps the record's magnitudes (0x140551980 writes the override only if non-zero).
constexpr float kNoMagnitudeOverride = 0.0f;
constexpr auto kTickInterval = std::chrono::milliseconds(100);

using FunctionID = RE::FUNCTION_DATA::FunctionID;
static_assert(static_cast<int>(RE::WEAPON_TYPE::kBow) == essb::kBow);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kStaff) == essb::kStaff);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kCrossbow) == essb::kCrossbow);
static_assert(std::size(essb::procRows) == 2 * essb::kElementCount);
static_assert(std::size(essb::kStatusRecords) == essb::kStatusKindCount);

// ---------------------------------------------------------------- the only mutable state

void Log(std::string_view line) noexcept;

// The form source Load.h resolves against (round 25 hotfix): the game's TESDataHandler. The resolution itself -- every
// record, every identity check, the status tables -- is Load.h's, so native/tests/load_test.cpp runs the same code on
// the written ESP and manifest.
struct GameForms {
    using Global = RE::TESGlobal;
    using Spell = RE::SpellItem;
    using Magic = RE::MagicItem;
    using Effect = RE::EffectSetting;
    using Keyword = RE::BGSKeyword;
    using Class = RE::TESClass;
    using Faction = RE::TESFaction;
    using Perk = RE::BGSPerk;
    using Hazard = RE::BGSHazard;
    using File = RE::TESFile;

    RE::TESDataHandler& data;

    template <class T>
    T* Lookup(std::uint32_t id, const char* file)
    {
        return data.LookupForm<T>(id, file);
    }
    std::string KindOf(std::uint32_t id, const char* file)
    {
        const RE::TESForm* form = data.LookupForm(id, file);
        return form ? std::string(RE::FormTypeToString(form->GetFormType())) : std::string();
    }
    std::optional<std::uint32_t> RuntimeId(std::uint32_t id, const char* file)
    {
        const RE::TESFile* mod = data.LookupModByName(file);
        if (!mod) {
            return std::nullopt;
        }
        return mod->IsLight() ? (0xFE000000u | (static_cast<std::uint32_t>(mod->GetSmallFileCompileIndex()) << 12) | (id & 0xFFFu))
                              : ((static_cast<std::uint32_t>(mod->GetCompileIndex()) << 24) | (id & 0xFFFFFFu));
    }
    const File* Mod(const char* file) { return data.LookupModByName(file); }
    std::optional<float> FirstSeconds(const Spell* spell)
    {
        if (!spell || spell->effects.empty() || !spell->effects[0]) {
            return std::nullopt;
        }
        return static_cast<float>(spell->effects[0]->effectItem.duration);
    }
    bool SpawnsHazard(const Effect* effect, const Hazard* hazard)
    {
        return effect->GetArchetype() == RE::EffectSetting::Archetype::kSpawnHazard && effect->data.associatedForm == hazard;
    }
    void Report(const std::string& line) { Log("[ESSB][load] FAILED " + line); }
};

// The status layer's records (round 22) and every other resolved record: Load.h's tables, over the game's types.
using StatusForms = essb::load::StatusForms<GameForms>;
using Forms = essb::load::Forms<GameForms>;
static_assert(std::string_view(essb::load::kPlugin) == kPlugin && std::string_view(essb::load::kSkyrim) == kSkyrim);

struct State {
    std::atomic_bool ready{};     // manifest resolved and sinks registered
    std::atomic_bool faulted{};   // latched until the game restarts
    std::atomic_bool inGame{};    // from PostLoadGame/NewGame until the next PreLoadGame
    std::atomic_bool echoDispelQueued{};     // a consumed echo marker waits for its main-thread dispel
    std::atomic_bool riposteDispelQueued{};  // a used 反擊 window waits for its main-thread dispel
    std::atomic_bool tickQueued{};           // one timer task at a time (a task never re-queues itself)
    std::atomic_bool stopTimer{};
    std::atomic<std::uint64_t> lastProcNotice{};
    essb::Cadence cadence{};         // round 25: the timer's clock (game-running time only; main thread); not design state
    // 審查修正: the game-running ms this session (never reset, never saved) -- Papyrus's windows read it through
    // ESSBNative.RunningSeconds so they stop with the game (paused, loading) like the DLL's own clock.
    std::atomic<std::uint64_t> runningMs{};
    bool stoppedLogged = false;      // probe N6-1: the stop was logged once (main thread)
    HANDLE log{ INVALID_HANDLE_VALUE };
    Forms forms{};
    std::optional<essb::trace::TraceRng> rng;  // damage rolls; seeded once per game process (round 26: with a tape)
    // Notices raised before the HUD exists (data load). Round 26c: Fault can raise one from any thread -- locked.
    std::mutex noticeLock;
    std::vector<std::string> deferredNotices;
    // Round 26c: your pools as the last task left them (WriteMirrors), so the hurt sink reads no effect list.
    std::atomic<float> mirrorGuard{};
    std::atomic<float> mirrorOverload{};
    std::atomic_bool mirrorAfterimage{};
    std::atomic_bool mirrorLinger{};
    // Round 26c (P5): how many engine-mutating bodies run now (a task; > 1 = two at once), and which.
    std::atomic<int> mutating{};
    std::atomic<const char*> mutatingName{};
    std::mutex overlapLock;
    std::vector<std::pair<const char*, const char*>> overlapsSeen;
    std::atomic_bool rngOutsideLogged{};
    std::atomic_bool traceReset{};   // round 26c: OnGameReady asks the tick task to reset the probe log's watchers
    // Probe X1 (round 26 rework): which thread each sink and task really runs on. kDataLoaded arrives on the game's
    // InitTESThread (SKSE Hooks_Data: the hook sits in ID 35554, called only by InitTESThread's ThreadProc), so it is no
    // reference. The references are: the input sink's thread (BSInputDeviceManager::PollInputDevices is called from
    // Main::Update itself = the WinMain loop, native-verification-3 s13), the game window's owner thread (created by
    // WinMain), and the thread of the latest SKSE task (SKSE runs its tasks after BSTaskPool::ProcessTaskQueue, which the
    // game calls both from Main::Update and from the "Post process" BSJobs job, so tasks need not be on one thread).
    // Every sink / task logs each NEW thread it sees (4 at most) against all of them.
    std::atomic<DWORD> inputThread{};
    std::atomic<DWORD> taskThread{};      // the latest SKSE task's
    std::atomic<DWORD> windowThread{};
    DWORD dataThread = 0;
    std::atomic_bool uiWitnessQueued{};   // round 26: one UI witness task at a time
    std::array<std::array<std::atomic<DWORD>, 4>, 20> threadSeen{};
    // Round 26b (X2): the call chains each sink / task was seen with (RtlCaptureStackBackTrace's hash), the executable's
    // and this DLL's address ranges, and the address of the Havok TLS index (REL::ID 528600), for the witness lines.
    std::array<std::array<std::atomic<ULONG>, 8>, 20> chainSeen{};
    std::uintptr_t exeBase = 0, exeEnd = 0, dllBase = 0, dllEnd = 0;
    std::uintptr_t havokTlsIndex = 0;
    // Round 23: the hits you took this frame, between the hit sink (before the damage) and the one task that reads the
    // damage (native-verification-2 s15). Plumbing between two calls of the same frame, not design state.
    std::mutex hurtLock;
    std::vector<std::pair<RE::ActorHandle, essb::HurtFacts>> hurts;
    std::atomic_bool hurtQueued{};
    // Probe N4-2 (debug level 3 only): the last actor you hit and its casters' last logged state (main thread).
    RE::ActorHandle probeTarget{};
    std::array<int, 2> probeCaster{ -1, -1 };
    // Round 26 (the probe log, Trace.h): the buffer, the real clock's origin, the running event's label and what the
    // watchers saw last. Logging only -- nothing here is read by a rule.
    essb::trace::Buffer trace;
    std::mutex flushLock;
    std::uint64_t realStart = 0;
    std::atomic<std::uint64_t> lastFlush{};
    std::vector<std::pair<std::uint32_t, std::string>> globalNames; // manifest "globals": local id -> editor ID
    std::vector<float> globalSeen;                                   // [i] of forms.globals; empty = dump them again
    std::vector<std::uint32_t> perksSeen;
    bool perksRead = false;
    std::uint64_t lastPerkScan = 0;
    std::vector<std::uint32_t> domainsSeen;
    float stepSeen = -1.0f;                                          // ESSB_ProbeStep as last seen (-1: not yet)
    bool secondRead = false;
    std::array<float, 3> secondSeen{};                               // your health / magicka / stamina at the last second
    bool traceWasOn = false;
};

State state;

// Round 26c (P4): per-thread state. The removal event of our own Dispel(true) arrives on the dispelling thread inside the
// call (native-verification-3 s6), so the self-dispel flag is the thread's; so are the running event's label for the
// probe log, "inside a hit task" (a hit event our own casts raise is dropped) and "inside a task" (P3 / P5).
thread_local bool t_selfDispel = false;
thread_local bool t_inHitTask = false;
thread_local bool t_inTask = false;
thread_local const char* t_traceCtx = "-";
constexpr essb::Config kConfig = essb::MakeConfig();

// ---------------------------------------------------------------- log and on-screen notices

// Round 26: the probe log is on (ESSB_DebugLevel >= 4).
bool TraceOn() noexcept
{
    return state.forms.debug && essb::trace::On(state.forms.debug->value);
}

// Writes what the probe log's buffer holds (one WriteFile; under its own lock so two flushes never swap order).
void FlushTrace() noexcept
{
    try {
        std::lock_guard lock(state.flushLock);
        std::uint64_t dropped = 0;
        std::string text = state.trace.Take(dropped);
        if (dropped > 0) {
            char line[128];
            std::snprintf(line, sizeof(line), "[ESSB][T][trace] dropped=%llu lines (the buffer was full)\n", static_cast<unsigned long long>(dropped));
            text += line;
        }
        state.lastFlush = GetTickCount64();
        if (!text.empty() && state.log != INVALID_HANDLE_VALUE) {
            DWORD written = 0;
            WriteFile(state.log, text.data(), static_cast<DWORD>(text.size()), &written, nullptr);
        }
    } catch (...) {
    }
}

// Writes the buffer once the DLL unloads (a normal exit); the timer thread writes it every second before that.
struct TraceAtExit {
    ~TraceAtExit() { FlushTrace(); }
} traceAtExit;

std::uint64_t RealMs() noexcept
{
    return GetTickCount64() - state.realStart;
}

// One probe-log line into the buffer; returns its sequence number (0 = not written).
std::uint64_t Emit(const essb::trace::Line& line) noexcept
{
    try {
        bool now = false;
        const std::uint64_t seq = state.trace.Add(line, state.runningMs.load(), RealMs(), now);
        if (now) {
            FlushTrace();
        }
        return seq;
    } catch (...) {
        return 0;
    }
}

// The running event's label on every op line (main thread; nests).
struct TraceCtx {
    const char* prev;
    explicit TraceCtx(const char* ctx) noexcept : prev(t_traceCtx) { t_traceCtx = ctx; }
    ~TraceCtx() { t_traceCtx = prev; }
    TraceCtx(const TraceCtx&) = delete;
    TraceCtx& operator=(const TraceCtx&) = delete;
};

// One WriteFile per line on an append handle: there is no lock a fault could leave held. Round 26: while the probe log is
// on, every line goes through its buffer instead, so the file keeps one order.
void Log(std::string_view line) noexcept
{
    if (state.log == INVALID_HANDLE_VALUE) {
        return;
    }
    if (TraceOn()) {
        try {
            bool now = false;
            state.trace.Raw(line, now);
            if (now) {
                FlushTrace();
            }
            return;
        } catch (...) {
        }
    }
    char buffer[640];
    const std::size_t length = (std::min)(line.size(), sizeof(buffer) - 1);
    std::memcpy(buffer, line.data(), length);
    buffer[length] = '\n';
    DWORD written = 0;
    WriteFile(state.log, buffer, static_cast<DWORD>(length + 1), &written, nullptr);
}

template <class... Args>
void Logf(const char* format, Args... args) noexcept
{
    char line[512];
    std::snprintf(line, sizeof(line), format, args...);
    Log(line);
}

void OpenLog()
{
    if (state.log != INVALID_HANDLE_VALUE) {
        return;
    }
    const auto directory = SKSE::log::log_directory();
    if (!directory) {
        throw std::runtime_error("SKSE log directory unavailable");
    }
    std::filesystem::create_directories(*directory);
    const auto path = *directory / L"ElementsSpellblade.log";
    state.realStart = GetTickCount64();
    state.log = CreateFileW(path.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (state.log == INVALID_HANDLE_VALUE) {
        throw std::runtime_error("Cannot open ElementsSpellblade.log");
    }
    Logf("[ESSB][load] ElementsSpellblade %s; SE 1.5.97 + SKSE 2.0.20 only; no entry-51 fallback", essb::nativeVersion);
}

// Probe X1 (native-verification-3 s16): the first event of each sink logs whether it arrived on the main thread.
enum class Probe
{
    kHit,
    kRemove,
    kDeath,
    kTick,
    kNative,
    kHurt,
    kCast,
    kNativeTask,   // round 24 review fix 1: the queued native work
    kInput,        // round 25 (N6): the hotkey input sink (probe N6-2)
    kHurtTask,     // round 26: the hurt task has its own flag (it shared kHurt with the hit sink's line, so only one was written)
    kSettleTask,   // round 26: the expiry settle task
    kDeathTask,    // round 26: the death task
    kCastTask,     // round 26: the spell-cast task (反咒, 逼近)
    kUiTask,       // round 26 (threading witness): an SKSE UI task (AddUITask, drained in UI::ProcessMessages)
    kInputFrame,   // round 26 (threading witness): the input sink on every call (PollInputDevices sends every frame)
    kInputTask,    // round 26b: a hotkey / step action the input sink queued
    kHitTask,      // round 26c: the hit task (the hit sink only snapshots)
    kCount,
};
static_assert(static_cast<std::size_t>(Probe::kCount) <= 20);

const char* Compare(DWORD thread, DWORD reference) noexcept
{
    return reference == 0 ? "unknown" : thread == reference ? "same" : "DIFFERENT";
}

// Round 26 rework: every sink / task logs each new thread it runs on (at most 4 per probe), with the raw ids and whether
// the thread is the input sink's (the main loop's), the latest SKSE task's and the game window's -- one in-game run
// settles where each of them runs. A few atomic reads per event; no lock.
const char* Compare(DWORD thread, DWORD reference) noexcept;

// Round 26b (X2): the Havok TLS word of this thread (the job system's bit mask at TLS[*ID 528600] + 0x688), read-only.
bool ReadHavokTls(std::uintptr_t indexAddress, std::uint32_t& out) noexcept
{
    __try {
        const std::uint32_t index = *reinterpret_cast<const std::uint32_t*>(indexAddress);
        auto** tls = reinterpret_cast<std::uint8_t**>(__readgsqword(0x58));
        out = *reinterpret_cast<const std::uint32_t*>(tls[index] + 0x688);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

constexpr bool IsTaskProbe(Probe p) noexcept
{
    return p == Probe::kTick || p == Probe::kNativeTask || p == Probe::kHurtTask || p == Probe::kSettleTask || p == Probe::kDeathTask ||
           p == Probe::kCastTask || p == Probe::kUiTask || p == Probe::kInputTask || p == Probe::kHitTask;
}

// Round 26b (X2): the first time each distinct call chain reaches a sink or a task, its return addresses (12 frames above
// the sink / task) as SkyrimSE.exe+0x… (ESSB+0x… for this DLL), the chain keys they contain (Trace.h kChainKeys), the
// window-thread comparison and, in a task, the Havok TLS word. Never inlined: the frames it skips are its own and
// LogThreadOnce's.
__declspec(noinline) void LogChainOnce(Probe which, const char* name) noexcept
{
    void* frames[12]{};
    ULONG hash = 0;
    const USHORT n = RtlCaptureStackBackTrace(2, 12, frames, &hash);
    hash |= 1u;
    auto& seen = state.chainSeen[static_cast<int>(which)];
    bool fresh = false;
    for (auto& slot : seen) {
        ULONG known = slot.load();
        if (known == hash) {
            return;
        }
        if (known == 0) {
            fresh = slot.compare_exchange_strong(known, hash);
            if (!fresh && known == hash) {
                return;
            }
            if (fresh) {
                break;
            }
        }
    }
    if (!fresh) {
        return;   // eight chains seen already
    }
    char text[900];
    int at = 0;
    char keys[160] = "-";
    int keyAt = 0;
    for (USHORT i = 0; i < n && at < 820; ++i) {
        const auto address = reinterpret_cast<std::uintptr_t>(frames[i]);
        if (address >= state.exeBase && address < state.exeEnd) {
            const auto offset = address - state.exeBase;
            at += std::snprintf(text + at, sizeof(text) - at, "%sSkyrimSE.exe+0x%llX", i ? "," : "", static_cast<unsigned long long>(offset));
            for (const auto& key : essb::trace::kChainKeys) {
                if (key.offset == offset && keyAt < 140) {
                    keyAt += std::snprintf(keys + keyAt, sizeof(keys) - keyAt, "%s%s", keyAt ? "," : "", key.name);
                }
            }
        } else if (address >= state.dllBase && address < state.dllEnd) {
            at += std::snprintf(text + at, sizeof(text) - at, "%sESSB+0x%llX", i ? "," : "", static_cast<unsigned long long>(address - state.dllBase));
        } else {
            at += std::snprintf(text + at, sizeof(text) - at, "%s0x%llX", i ? "," : "", static_cast<unsigned long long>(address));
        }
    }
    text[(std::min)(at, static_cast<int>(sizeof(text)) - 1)] = '\0';
    char havok[16] = "-";
    std::uint32_t word = 0;
    if (IsTaskProbe(which) && state.havokTlsIndex && ReadHavokTls(state.havokTlsIndex, word)) {
        std::snprintf(havok, sizeof(havok), "0x%08X", word);
    }
    const DWORD thread = GetCurrentThreadId();
    const DWORD window = state.windowThread.load();
    auto* ui = RE::UI::GetSingleton();
    Logf("[ESSB][X2] %s thread=%lu window=%lu %s paused=%d havok=%s keys=%s frames=%s", name, thread, window, Compare(thread, window),
        ui && ui->GameIsPaused() ? 1 : 0, havok, keys, text);
}

__declspec(noinline) void LogThreadOnce(Probe which, const char* name) noexcept
{
    LogChainOnce(which, name);   // round 26b (X2)
    const DWORD thread = GetCurrentThreadId();
    auto& seen = state.threadSeen[static_cast<int>(which)];
    for (std::size_t k = 0; k < seen.size(); ++k) {
        DWORD known = seen[k].load();
        if (known == thread) {
            return;
        }
        if (known == 0) {
            if (!seen[k].compare_exchange_strong(known, thread)) {
                return;   // another thread took this slot at the same moment; the next event logs again
            }
            const DWORD input = state.inputThread.load();
            const DWORD task = state.taskThread.load();
            const DWORD window = state.windowThread.load();
            auto* ui = RE::UI::GetSingleton();
            Logf("[ESSB][X1] %s thread=%lu n=%d input=%lu %s task=%lu %s window=%lu %s dataLoaded=%lu paused=%d", name, thread,
                static_cast<int>(k) + 1, input, Compare(thread, input), task, Compare(thread, task), window, Compare(thread, window),
                state.dataThread, ui && ui->GameIsPaused() ? 1 : 0);
            return;
        }
    }
}

// Every SKSE task notes its thread (the X1 lines compare the sinks against the latest one).
void NoteTaskThread() noexcept
{
    state.taskThread = GetCurrentThreadId();
}

// The first SKSE task (queued at kDataLoaded): the game window's owner thread (a witness of the WinMain thread) and the
// first task's thread.
void MainThreadCpp() noexcept
{
    try {
        const DWORD thread = GetCurrentThreadId();
        DWORD window = 0;
        if (auto* main = RE::Main::GetSingleton(); main && main->wnd) {
            window = GetWindowThreadProcessId(reinterpret_cast<HWND>(main->wnd), nullptr);
        }
        state.windowThread = window;
        NoteTaskThread();
        Logf("[ESSB][X1] first SKSE task thread=%lu window=%lu %s input=%lu %s dataLoaded=%lu (InitTESThread)", thread, window,
            Compare(thread, window), state.inputThread.load(), Compare(thread, state.inputThread.load()), state.dataThread);
    } catch (...) {
    }
}

void MainThreadGuarded() noexcept
{
    __try {
        MainThreadCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

// Round 26c (P5): every engine-mutating body (every SKSE task) runs inside one scope. The count of scopes open right now
// must never pass 1 (SKSE runs its tasks one after another); if it does, "[ESSB][OVERLAP] <name> thread= with=<other>"
// is logged once per pair. Two atomics per task: kept in release.
void Overlap(const char* name, const char* other) noexcept
{
    try {
        std::lock_guard lock(state.overlapLock);
        for (const auto& [a, b] : state.overlapsSeen) {
            if (a == name && b == other) {
                return;
            }
        }
        state.overlapsSeen.emplace_back(name, other);
    } catch (...) {
    }
    Logf("[ESSB][OVERLAP] %s thread=%lu with=%s", name, GetCurrentThreadId(), other ? other : "?");
}

struct TaskScope {
    const char* name;
    bool outer;
    explicit TaskScope(const char* n) noexcept : name(n), outer(t_inTask)
    {
        if (outer) {
            return;   // a nested scope on the same thread (a task body calling another body)
        }
        t_inTask = true;
        const char* other = state.mutatingName.exchange(n);
        if (state.mutating.fetch_add(1) + 1 > 1) {
            Overlap(n, other);
        }
    }
    ~TaskScope()
    {
        if (outer || !t_inTask) {
            return;
        }
        t_inTask = false;
        if (state.mutating.fetch_sub(1) <= 0) {
            state.mutating = 0;
        }
    }
    TaskScope(const TaskScope&) = delete;
    TaskScope& operator=(const TaskScope&) = delete;
};

// A hit task's scope: a TESHitEvent our own casts raise on this thread is dropped by the sink (the old re-entrancy guard).
struct InHitTask {
    bool prev;
    InHitTask() noexcept : prev(t_inHitTask) { t_inHitTask = true; }
    ~InHitTask() { t_inHitTask = prev; }
    InHitTask(const InHitTask&) = delete;
    InHitTask& operator=(const InHitTask&) = delete;
};

// Round 26c (P3): the damage rolls are drawn only inside tasks (one context, one after another); a draw anywhere else is
// logged once (it would race with the tasks).
essb::trace::TraceRng& Rng() noexcept
{
    if (!t_inTask && !state.rngOutsideLogged.exchange(true)) {
        Logf("[ESSB][RNG] a draw outside a task thread=%lu", GetCurrentThreadId());
    }
    return Rng();
}

// Debug.Notification equivalent: RE::DebugNotification (CommonLib-NG Misc.h), run on the main thread
// through the SKSE task interface so it is safe from any caller.
void Show(std::string text) noexcept
{
    try {
        const auto* tasks = SKSE::GetTaskInterface();
        if (!tasks) {
            return;
        }
        tasks->AddTask([text = std::move(text)]() {
            RE::DebugNotification(text.c_str());
        });
    } catch (...) {
    }
}

void Notify(std::string text) noexcept
{
    try {
        Log("[ESSB][notice] " + text);
        if (state.inGame) {
            Show(std::move(text));
        } else {
            std::lock_guard lock(state.noticeLock);   // round 26c: Fault may raise a notice from any thread
            state.deferredNotices.push_back(std::move(text));
        }
    } catch (...) {
    }
}

bool ProcNoticeDue() noexcept
{
    const std::uint64_t now = GetTickCount64();
    std::uint64_t last = state.lastProcNotice.load();
    if (now - last < kProcNoticeIntervalMs) {
        return false;
    }
    return state.lastProcNotice.compare_exchange_strong(last, now);
}

// ---------------------------------------------------------------- status and faults

// SEH-only helper: no C++ objects here, so __try is allowed.
void WriteNativeHit(float value) noexcept
{
    __try {
        if (state.forms.nativeHit) {
            state.forms.nativeHit->value = value;
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

bool Active() noexcept
{
    if (!state.ready || state.faulted || !state.inGame || !state.forms.wanted) {
        return false;
    }
    return state.forms.wanted->value == 1.0f;
}

// The mod's master switch (ESSB_Enabled) on top of Active(): every status-layer path -- the per-second task, the expiry
// settlement, the death snapshot and every ESSBNative function -- does nothing while it is off (review fix 3). The hit
// path checks the same global through HitPipeline's Filter.
bool Enabled() noexcept
{
    return Active() && state.forms.enabled && state.forms.enabled->value == 1.0f;
}

// ESSB_NativeHit is what Papyrus reads (MCM status, the not-running notice); recomputed on every state change.
void PublishStatus() noexcept
{
    WriteNativeHit(Active() ? 1.0f : 0.0f);
}

void Fault(const char* reason) noexcept
{
    state.ready = false;
    const bool first = !state.faulted.exchange(true);
    WriteNativeHit(0.0f);
    t_selfDispel = false;
    if (t_inTask) {   // round 26c: a fault inside a task body (an SEH exit skips its scope's destructor)
        t_inTask = false;
        if (state.mutating.fetch_sub(1) <= 0) {
            state.mutating = 0;
        }
    }
    if (!first) {
        return;
    }
    Logf("[ESSB][fault] %s; native hit OFF until the game restarts", reason);
    FlushTrace();   // round 26: a fault is written at once
    try {
        Notify(std::string("元素魔戰士 DLL 故障：") + reason + "。命中附傷已停用，重開遊戲前不會恢復");
    } catch (...) {
    }
}

// ---------------------------------------------------------------- stage 1: which hits count

// Papyrus GetEquippedItemType(hand) == 0 (empty hand or a hand-to-hand weapon), evaluated with the same
// engine condition function the Papyrus gate uses. Stack-only TESConditionItem, no heap.
bool HandIsEmpty(RE::PlayerCharacter& player, bool left)
{
    RE::TESConditionItem item;
    item.data.functionData.function = FunctionID::kGetEquippedItemType;
    item.data.functionData.params[0] = reinterpret_cast<void*>(static_cast<std::uintptr_t>(left ? 0 : 1));
    item.data.comparisonValue.f = 0.0f;
    item.data.flags.opCode = RE::CONDITION_ITEM_DATA::OpCode::kEqualTo;
    RE::ConditionCheckParams args(&player, &player);
    return item.IsTrue(args);
}

essb::HandFacts ReadHand(RE::PlayerCharacter& player, bool left)
{
    essb::HandFacts hand;
    auto* object = player.GetEquippedObject(left);
    auto* weapon = object ? object->As<RE::TESObjectWEAP>() : nullptr;
    hand.weaponType = weapon ? static_cast<int>(weapon->GetWeaponType()) : essb::kNoWeapon;
    hand.nothing = HandIsEmpty(player, left);
    return hand;
}

void ReadSource(const RE::TESHitEvent& ev, essb::HitFacts& facts)
{
    facts.projectile = ev.projectile != 0;
    if (!ev.source) {
        facts.source = essb::SourceKind::kNone;
        return;
    }
    auto* form = RE::TESForm::LookupByID(ev.source);
    auto* weapon = form ? form->As<RE::TESObjectWEAP>() : nullptr;
    if (weapon) {
        facts.source = essb::SourceKind::kWeapon;
        facts.sourceWeaponType = static_cast<int>(weapon->GetWeaponType());
    } else if (form && form->Is(RE::FormType::Ammo)) {
        facts.source = essb::SourceKind::kAmmo;
    } else if (form && form->Is(RE::FormType::Projectile) && ev.source == ev.projectile) {
        facts.source = essb::SourceKind::kSameProjectile;
    } else {
        facts.source = essb::SourceKind::kOther;
    }
}

essb::HitFacts ReadHitFacts(const RE::TESHitEvent& ev, RE::PlayerCharacter& player, RE::Actor* target)
{
    essb::HitFacts facts;
    facts.causeIsPlayer = true;  // Handle only reads facts for the player's own hits
    facts.targetIsActor = target != nullptr;
    facts.targetIsPlayer = target == &player;
    if (target && !facts.targetIsPlayer) {
        facts.targetDead = target->IsDead();
        facts.teammate = target->IsPlayerTeammate();
        facts.commanded = target->IsCommandedActor();
    }
    using Flag = RE::TESHitEvent::Flag;
    facts.bash = ev.flags.any(Flag::kBashAttack);
    facts.blocked = ev.flags.any(Flag::kHitBlocked);
    ReadSource(ev, facts);
    facts.right = ReadHand(player, false);
    facts.left = ReadHand(player, true);
    facts.enabled = state.forms.enabled->value;
    facts.formActive = state.forms.formActive->value;
    facts.element = state.forms.element->value;
    return facts;
}

// ---------------------------------------------------------------- stage 2: engine reads

float Global(std::uint32_t localId)
{
    for (const auto& [id, global] : state.forms.globals) {
        if (id == localId) {
            return global->value;
        }
    }
    throw std::runtime_error("tuning global not in the manifest");
}

bool PlayerHasPerk(RE::PlayerCharacter& player, std::uint32_t localId)
{
    RE::BGSPerk* perk = nullptr;
    const auto& main = state.forms.mainPerks;
    const auto& branch = state.forms.branchPerks;
    if (localId >= essb::kMainPerkBase && localId - essb::kMainPerkBase < main.size()) {
        perk = main[localId - essb::kMainPerkBase];
    } else if (localId >= essb::kBranchPerkBase && localId - essb::kBranchPerkBase < branch.size()) {
        perk = branch[localId - essb::kBranchPerkBase];
    }
    return perk && player.HasPerk(perk);
}

// The player's nodes as the planners read them (one cache per call).
auto MakeNodes(RE::PlayerCharacter& player, bool formActive)
{
    const auto hasPerk = [&player](std::uint32_t localId) {
        return PlayerHasPerk(player, localId);
    };
    return essb::PerkNodes<decltype(hasPerk)>(hasPerk, formActive);
}

std::uint32_t WeaponId(RE::TESForm* form)
{
    return form && form->As<RE::TESObjectWEAP>() ? form->GetFormID() : 0;
}

essb::RawAttack ReadAttack(const RE::TESHitEvent& ev, RE::PlayerCharacter& player, int weaponType)
{
    using Flag = RE::TESHitEvent::Flag;
    essb::RawAttack raw;
    raw.powerFlag = ev.flags.any(Flag::kPowerAttack);
    raw.sneakFlag = ev.flags.any(Flag::kSneakAttack);
    raw.ranged = essb::IsRangedType(weaponType);
    raw.sourceWeapon = ev.source ? WeaponId(RE::TESForm::LookupByID(ev.source)) : 0;
    raw.leftWeapon = WeaponId(player.GetEquippedObject(true));
    raw.rightWeapon = WeaponId(player.GetEquippedObject(false));
    return raw;
}

// Active effects that are running (not waiting on conditions, not being dispelled).
template <class Visit>
void ForEachRunningEffect(RE::Actor& actor, Visit&& visit)
{
    auto* list = actor.AsMagicTarget()->GetActiveEffectList();
    if (!list) {
        return;
    }
    for (RE::ActiveEffect* effect : *list) {
        if (!effect || effect->flags.any(RE::ActiveEffect::Flag::kInactive, RE::ActiveEffect::Flag::kDispelled)) {
            continue;
        }
        if (auto* base = effect->GetBaseObject()) {
            visit(*effect, *base);
        }
    }
}

float MaxOf(RE::Actor& actor, RE::ActorValue av)
{
    return actor.AsActorValueOwner()->GetPermanentActorValue(av) +
           actor.GetActorValueModifier(RE::ACTOR_VALUE_MODIFIER::kTemporary, av);
}

std::uint32_t EffectIdOf(const RE::EffectSetting* base) noexcept;   // below (round 22's status table)

// Round 26: one actor as the probe log shows it (name, FormID, health / magicka / stamina current / max, dead).
essb::trace::ActorFacts FactsOf(RE::Actor* actor) noexcept
{
    essb::trace::ActorFacts f;
    if (!actor) {
        return f;
    }
    f.has = true;
    const char* name = actor->GetName();
    f.name = name ? std::string_view(name) : std::string_view();
    f.formId = actor->GetFormID();
    auto* v = actor->AsActorValueOwner();
    f.h = v->GetActorValue(RE::ActorValue::kHealth);
    f.hMax = MaxOf(*actor, RE::ActorValue::kHealth);
    f.m = v->GetActorValue(RE::ActorValue::kMagicka);
    f.mMax = MaxOf(*actor, RE::ActorValue::kMagicka);
    f.s = v->GetActorValue(RE::ActorValue::kStamina);
    f.sMax = MaxOf(*actor, RE::ActorValue::kStamina);
    f.dead = actor->IsDead();
    return f;
}

essb::PlayerFacts ReadPlayer(RE::PlayerCharacter& player)
{
    essb::PlayerFacts p;
    auto* values = player.AsActorValueOwner();
    p.health = values->GetActorValue(RE::ActorValue::kHealth);
    p.healthPermanent = values->GetPermanentActorValue(RE::ActorValue::kHealth);
    p.healthMax = MaxOf(player, RE::ActorValue::kHealth);
    p.magicka = values->GetActorValue(RE::ActorValue::kMagicka);
    p.magickaMax = MaxOf(player, RE::ActorValue::kMagicka);
    const auto* cell = player.GetParentCell();
    p.interior = cell && cell->IsInteriorCell();
    const auto& f = state.forms;
    ForEachRunningEffect(player, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
        if (&base == f.bloodGuard) {
            p.bloodGuard = (std::max)(p.bloodGuard, effect.magnitude);
        } else if (&base == f.echoPending) {
            p.echoPending = !state.echoDispelQueued;
        } else if (&base == f.twinWindow) {
            p.twinWindow = true;
        } else if (&base == f.riposteWindow) {
            p.riposteWindow = !state.riposteDispelQueued;
        } else if (EffectIdOf(&base) == essb::kStatusRecords[static_cast<int>(essb::StatusKind::kBloodthirst)].effect) {
            p.bloodthirst = true;   // round 24: 飲血's 嗜血 (吸血 +10%)
        }
    });
    return p;
}

essb::RawTarget ReadTarget(RE::Actor& target)
{
    const auto& f = state.forms;
    essb::RawTarget raw;
    raw.undeadKeyword = f.undead && target.HasKeyword(f.undead);
    raw.daedraKeyword = f.daedra && target.HasKeyword(f.daedra);
    const auto* base = target.GetActorBase();
    raw.necromancerClass = base && f.necroClass && base->npcClass == f.necroClass;
    raw.necromancerFaction = f.necroFaction && target.IsInFaction(f.necroFaction);
    const auto* process = target.GetActorRuntimeData().currentProcess;
    if (process && process->middleHigh) {
        raw.commandedActors = static_cast<int>(process->middleHigh->commandedActors.size());
    }
    ForEachRunningEffect(target, [&](RE::ActiveEffect& active, RE::EffectSetting& effect) {
        raw.bloodMark = raw.bloodMark || &effect == f.bloodMark;
        raw.silenced = raw.silenced || &effect == f.silence;
        if (&effect == f.hush) {
            raw.hushMagnitude = (std::max)(raw.hushMagnitude, active.magnitude);
        }
        raw.hushSpent = raw.hushSpent || &effect == f.hushSpent;
        raw.armorSpellEffect = raw.armorSpellEffect || (f.armorSpell && effect.HasKeyword(f.armorSpell));
        raw.cloakEffect = raw.cloakEffect || (f.cloak && effect.HasKeyword(f.cloak));
    });
    auto* left = target.GetEquippedObject(true);
    auto* right = target.GetEquippedObject(false);
    raw.spellInLeftHand = left && left->As<RE::SpellItem>();
    raw.spellInRightHand = right && right->As<RE::SpellItem>();
    raw.essential = target.IsEssential();
    raw.baseEssential = base && base->IsEssential();
    raw.baseProtected = base && base->IsProtected();
    raw.baseUnique = base && base->IsUnique();
    raw.magicka = target.AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka);
    raw.magickaMax = MaxOf(target, RE::ActorValue::kMagicka);
    return raw;
}

// ---------------------------------------------------------------- round 22: status reads

template <class Id, class Ptr>
Ptr Lookup(const std::vector<std::pair<Id, Ptr>>& table, Id key) noexcept
{
    const auto it = std::lower_bound(table.begin(), table.end(), key, [](const auto& row, Id k) { return row.first < k; });
    return it != table.end() && it->first == key ? it->second : Ptr{};
}

// Local FormID of one of our status-layer effect records, or 0 for anything else.
std::uint32_t EffectIdOf(const RE::EffectSetting* base) noexcept
{
    return Lookup(state.forms.status.effectIds, base);
}

RE::EffectSetting* EffectById(std::uint32_t id)
{
    auto* effect = Lookup(state.forms.status.effects, id);
    if (!effect) {
        throw std::runtime_error("status effect not resolved");
    }
    return effect;
}

RE::SpellItem* SpellById(std::uint32_t id)
{
    auto* spell = Lookup(state.forms.status.spells, id);
    if (!spell) {
        throw std::runtime_error("status spell not resolved");
    }
    return spell;
}

std::uint32_t SpellIdOf(const RE::MagicItem* spell) noexcept
{
    return spell ? Lookup(state.forms.status.spellIds, spell) : 0;
}

// StatusEngine.h's wash numbers are CommonLib's enums (ruling R5).
static_assert(essb::engine::kSpellTypeSpell == static_cast<int>(RE::MagicSystem::SpellType::kSpell));
static_assert(essb::engine::kSpellTypeScroll == static_cast<int>(RE::MagicSystem::SpellType::kScroll));
static_assert(essb::engine::kSpellTypeStaff == static_cast<int>(RE::MagicSystem::SpellType::kStaffEnchantment));
static_assert(essb::engine::kSourceLeft == static_cast<int>(RE::MagicSystem::CastingSource::kLeftHand));
static_assert(essb::engine::kSourceRight == static_cast<int>(RE::MagicSystem::CastingSource::kRightHand));

// One running effect as StatusEngine.h sees it (review fix 6: the engine side runs against this view, so the tests can
// feed a fake list).
essb::engine::EffectView ViewOf(RE::ActiveEffect& effect, RE::EffectSetting& base)
{
    using AR = RE::EffectSetting::Archetype;
    essb::engine::EffectView v;
    v.uid = effect.usUniqueID;
    v.effect = EffectIdOf(&base);
    v.spell = SpellIdOf(effect.spell);
    v.magnitude = effect.magnitude;
    v.elapsed = effect.elapsedSeconds;
    v.duration = effect.duration;
    v.hasSpell = effect.spell != nullptr;
    v.spellType = effect.spell ? static_cast<int>(effect.spell->GetSpellType()) : -1;
    v.castingSource = static_cast<int>(effect.castingSource);
    v.hostile = base.IsHostile();
    v.detrimental = base.IsDetrimental();
    v.ours = effect.spell && effect.spell->GetFile(0) == state.forms.file;
    const AR archetype = base.GetArchetype();
    v.company = archetype == AR::kSummonCreature || archetype == AR::kBoundWeapon || archetype == AR::kReanimate ||
                archetype == AR::kCommandSummoned;
    return v;
}

// The effect lists of the player and (optionally) one target: the read half of the engine adapter.
class EffectLists
{
public:
    using Handle = RE::ActiveEffect*;

    EffectLists(RE::Actor& player, RE::Actor* target) : player_(player), target_(target) {}

    RE::Actor* ActorOf(essb::Who who) const noexcept { return who == essb::Who::kPlayer ? &player_ : target_; }

    template <class Fn>
    void ForEach(essb::Who who, Fn&& fn)
    {
        if (RE::Actor* actor = ActorOf(who)) {
            ForEachRunningEffect(*actor, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) { fn(ViewOf(effect, base), &effect); });
        }
    }

    // Every effect on the list, the finishing ones included (the effect-removed event arrives before its effect
    // leaves the list, possibly already flagged; native-verification-3 s2).
    template <class Fn>
    void ForEachIncludingEnding(essb::Who who, Fn&& fn)
    {
        RE::Actor* actor = ActorOf(who);
        auto* list = actor ? actor->AsMagicTarget()->GetActiveEffectList() : nullptr;
        if (!list) {
            return;
        }
        for (RE::ActiveEffect* effect : *list) {
            if (effect) {
                if (auto* base = effect->GetBaseObject()) {
                    fn(ViewOf(*effect, *base), effect);
                }
            }
        }
    }

protected:
    RE::Actor& player_;
    RE::Actor* target_;
};

// Everything of ours on the actor, as essb::Board (Status.h Read through StatusEngine.h). Read-only.
essb::Board ReadBoard(RE::Actor& actor)
{
    EffectLists lists(actor, nullptr);
    return essb::engine::ReadBoard(lists, essb::Who::kPlayer);
}

// Round 26b: the body of an actor without the player (the death sink reads the corpse only; the task adds the distance).
essb::Body ReadBodyOnly(RE::Actor& target, const essb::TargetFacts& facts)
{
    essb::Body body;
    auto* values = target.AsActorValueOwner();
    body.health = values->GetActorValue(RE::ActorValue::kHealth);
    body.healthMax = MaxOf(target, RE::ActorValue::kHealth);
    body.stamina = values->GetActorValue(RE::ActorValue::kStamina);
    body.staminaMax = MaxOf(target, RE::ActorValue::kStamina);
    body.vip = facts.vip;
    body.undeadOrDaedra = facts.undeadOrDaedra;
    return body;
}

essb::Body ReadBody(RE::Actor& target, RE::PlayerCharacter& player, const essb::TargetFacts& facts)
{
    essb::Body body;
    auto* values = target.AsActorValueOwner();
    body.health = values->GetActorValue(RE::ActorValue::kHealth);
    body.healthMax = MaxOf(target, RE::ActorValue::kHealth);
    body.stamina = values->GetActorValue(RE::ActorValue::kStamina);
    body.staminaMax = MaxOf(target, RE::ActorValue::kStamina);
    body.vip = facts.vip;
    body.undeadOrDaedra = facts.undeadOrDaedra;
    body.distanceToPlayer = target.GetPosition().GetDistance(player.GetPosition());
    return body;
}

essb::Self ReadSelf(RE::PlayerCharacter& player)
{
    essb::Self self;
    auto* values = player.AsActorValueOwner();
    self.health = values->GetActorValue(RE::ActorValue::kHealth);
    self.healthPermanent = values->GetPermanentActorValue(RE::ActorValue::kHealth);
    self.healthMax = MaxOf(player, RE::ActorValue::kHealth);
    return self;
}

essb::TargetFacts TargetFactsOf(RE::Actor& target)
{
    return essb::MakeTarget(ReadTarget(target));
}

// ---------------------------------------------------------------- round 23: casting state, mirrors

// native-verification-3 s8: casting = a caster with a spell in state 1-4 (request, charge, ready, release), or 6 with a
// concentration spell. Read-only, at hit time.
bool IsCasting(RE::Actor& actor)
{
    for (RE::ActorMagicCaster* caster : actor.GetActorRuntimeData().magicCasters) {
        if (!caster || !caster->currentSpell) {
            continue;
        }
        const auto s = static_cast<int>(caster->state.get());
        if ((s >= 1 && s <= 4) || (s == 6 && caster->currentSpell->GetCastingType() == RE::MagicSystem::CastingType::kConcentration)) {
            return true;
        }
    }
    return false;
}

void SetMirror(RE::TESGlobal* global, float value) noexcept
{
    if (global && global->value != value) {
        global->value = value;
    }
}

// v0.4 2.3: the thresholds PERK conditions read are mirrored into GLOBs by the DLL (the only writer); TrueHUD's bars read
// the pools. Called after every plan that can change your resources, and on every timer tick (an effect that ran out).
template <class Nodes>
void WriteMirrors(RE::PlayerCharacter& player, const essb::Board& me, const Nodes& nodes)
{
    using K = essb::StatusKind;
    const auto& f = state.forms;
    const int sync = me.Layers(K::kSync);
    const essb::res::SyncThresholds th = essb::res::Thresholds(essb::ReadTuning(Global), me, nodes);
    SetMirror(f.mirrorSync, static_cast<float>(sync));
    SetMirror(f.mirrorStage, static_cast<float>(essb::res::StageOf(sync, th)));
    SetMirror(f.mirrorCharge, static_cast<float>(me.Layers(K::kCharge)));
    SetMirror(f.mirrorResolve, static_cast<float>(me.Layers(K::kResolve)));
    SetMirror(f.mirrorIceShield, static_cast<float>(me.Layers(K::kIceShield)));
    SetMirror(f.mirrorRock, static_cast<float>(me.Layers(K::kRockArmor)));
    SetMirror(f.mirrorWind, static_cast<float>(me.Layers(K::kWindGauge)));
    SetMirror(f.mirrorBracing, static_cast<float>(me.Layers(K::kBracing)));
    // TrueHUD (R5): 超載 / max magicka cap, 護血 / 20% max health, 蓄勁 / 10, 同調 / the stage-3 threshold (form only).
    const float magickaMax = MaxOf(player, RE::ActorValue::kMagicka);
    const float healthMax = MaxOf(player, RE::ActorValue::kHealth);
    // Round 26c: the pools the hurt sink needs at hit time, so it reads no effect list (the sink runs beside the tasks).
    state.mirrorGuard = me.guardPool.has ? me.guardPool.magnitude : 0.0f;
    state.mirrorOverload = me.Has(K::kOverload) ? me[K::kOverload].magnitude : 0.0f;
    state.mirrorAfterimage = me.Has(K::kAfterimage);
    state.mirrorLinger = me.Has(K::kLingerShield);
    essb::hud::Publish(0, me.Has(K::kOverload) ? me[K::kOverload].magnitude : 0.0f, essb::res::OverloadCap(magickaMax, nodes));
    essb::hud::Publish(1, me.guardPool.has ? me.guardPool.magnitude : 0.0f, essb::kBloodGuardCapOfMaxHealth * healthMax);
    essb::hud::Publish(2, static_cast<float>(me.Layers(K::kStoredForce)), static_cast<float>(essb::n4::kForceCap));
    const bool form = state.forms.formActive->value == 1.0f;
    essb::hud::Publish(3, form ? static_cast<float>(sync) : 0.0f, static_cast<float>(th.at[2]));
}

// ---------------------------------------------------------------- stages 4 and 5: casts

RE::SpellItem* SpellOf(const essb::CastStep& step)
{
    return essb::load::SpellOf(state.forms, step);
}

RE::MagicCaster& CasterOf(RE::PlayerCharacter& player)
{
    auto* caster = player.GetMagicCaster(RE::MagicSystem::CastingSource::kInstant);
    if (!caster) {
        throw std::runtime_error("player instant caster unavailable");
    }
    return *caster;
}

// Round 26b (L3, the crash A/B): one line for every kill, push, knock and hazard this DLL causes.
void LogCaused(const char* kind, const RE::TESObjectREFR* ref, const char* via) noexcept
{
    if (state.forms.debug && state.forms.debug->value >= 3.0f) {
        Logf("[ESSB][AB][L3] kind=%s ref=%08X tick=%llu via=%s thread=%lu", kind, ref ? ref->GetFormID() : 0u,
            static_cast<unsigned long long>(GetTickCount64()), via, GetCurrentThreadId());
    }
}

bool CausedLogging() noexcept
{
    return state.forms.debug && state.forms.debug->value >= 3.0f;
}

void Apply(RE::PlayerCharacter& player, RE::Actor& target, const essb::Plan& plan)
{
    auto& caster = CasterOf(player);
    const bool watch = CausedLogging() && !target.IsDead();   // round 26b
    for (int i = 0; i < plan.count; ++i) {
        const essb::CastStep& step = plan.steps[i];
        RE::SpellItem* spell = SpellOf(step);
        if (!spell) {
            throw std::runtime_error("plan asks for a spell the manifest does not have");
        }
        const float magnitude = essb::UsesOverride(step.cast) ? step.magnitude : kNoMagnitudeOverride;
        RE::TESObjectREFR* on = essb::CastsOnPlayer(step.cast) ? static_cast<RE::TESObjectREFR*>(&player) : &target;
        // Every hit re-applies, like entry 51 did (no same-spell gate; see native-verification.md).
        caster.CastSpellImmediate(spell, false, on, kEffectiveness, false, magnitude, &player);
    }
    if (watch && target.IsDead()) {
        LogCaused("kill", &target, "proc");
    }
}

// The two single-use markers the DLL consumes on the player: 餘響待發 (echo) and the 反擊 window.
enum class Marker
{
    kEcho,
    kRiposte,
};

RE::EffectSetting* MarkerEffect(Marker marker) noexcept
{
    return marker == Marker::kEcho ? state.forms.echoPending : state.forms.riposteWindow;
}

std::atomic_bool& MarkerQueued(Marker marker) noexcept
{
    return marker == Marker::kEcho ? state.echoDispelQueued : state.riposteDispelQueued;
}

// Round 26c (P2): dispels the running effects `match` picks. Each is collected by its unique id and base effect, and
// re-found in the live list right before its Dispel (an earlier dispel may have changed the list), never by a pointer
// kept across dispels. Returns how many were dispelled.
template <class Match>
int DispelLive(RE::Actor& actor, Match&& match)
{
    std::vector<std::pair<std::uint16_t, const RE::EffectSetting*>> found;
    ForEachRunningEffect(actor, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
        if (match(effect, base)) {
            found.emplace_back(effect.usUniqueID, &base);
        }
    });
    int dispelled = 0;
    for (const auto& [uid, base] : found) {
        RE::ActiveEffect* live = nullptr;
        ForEachRunningEffect(actor, [&](RE::ActiveEffect& effect, RE::EffectSetting& b) {
            if (!live && effect.usUniqueID == uid && &b == base) {
                live = &effect;
            }
        });
        if (live) {
            live->Dispel(true);
            ++dispelled;
        }
    }
    return dispelled;
}

// Main-thread body of a marker dispel. The effects are collected first and dispelled after the walk, so the
// active-effect list is never changed while it is being iterated.
void DispelMarkerCpp(Marker marker) noexcept
{
    try {
        auto* player = RE::PlayerCharacter::GetSingleton();
        RE::EffectSetting* wanted = MarkerEffect(marker);
        if (!player || !wanted) {
            return;
        }
        TaskScope scope("marker dispel");   // round 26c
        DispelLive(*player, [&](RE::ActiveEffect&, RE::EffectSetting& base) { return &base == wanted; });   // round 26c (P2)
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in marker dispel task");
    }
}

// SEH-only wrapper (no C++ objects here), the same two layers as the hit sink.
void DispelMarkerGuarded(Marker marker) noexcept
{
    __try {
        DispelMarkerCpp(marker);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in marker dispel task");
    }
    MarkerQueued(marker) = false;
}

// A used marker is removed on the main thread; until then ReadPlayer ignores it (it is never used twice).
void QueueMarkerDispel(Marker marker)
{
    const auto* tasks = SKSE::GetTaskInterface();
    if (!tasks || MarkerQueued(marker).exchange(true)) {
        return;
    }
    tasks->AddTask([marker]() { DispelMarkerGuarded(marker); });
}

// ---------------------------------------------------------------- round 22: executing status plans

// A ModEvent for the Papyrus reaction bodies: sender = the target, numArg = the first value, strArg = every value joined
// with '|' (ESSBController parses them with StringUtil.Split).
constexpr const char* kEventNames[] = { "ESSB_Open", "ESSB_End", "ESSB_Frozen", "ESSB_Hallucinate", "ESSB_Judgment", "ESSB_Splash",
    "ESSB_Shatter", "ESSB_Landing", "ESSB_Rise", "ESSB_Discharge", "ESSB_Blade", "ESSB_Knock", "ESSB_SyncUp", "ESSB_Cleanse",
    "ESSB_Lethal", "ESSB_Push", "ESSB_Ash", "ESSB_Raise", "ESSB_Sneak", "ESSB_Domain", "ESSB_Overheat", "ESSB_Switch", "ESSB_Close" };
static_assert(std::size(kEventNames) == static_cast<int>(essb::Event::kCount));

void SendEvent(const essb::StatusOp& op, RE::Actor* target, RE::Actor* centre = nullptr)
{
    auto* source = SKSE::GetModCallbackEventSource();
    if (!source) {
        throw std::runtime_error("ModEvent source unavailable");
    }
    if (essb::BodyOnly(op.event)) {
        return;   // round 24: the bodies are the DLL's (Reactions.h); Papyrus has no handler for these any more
    }
    // Fixed-point: Papyrus' String -> Float cast does not read exponents.
    char text[256];
    if (op.event == essb::Event::kPush) {
        // The pull-to centre (風渦) is a crowd member; Papyrus gets its FormID as a signed 32-bit integer (`as Int`, then
        // Game.GetForm); 0 = none.
        const std::int32_t id = centre ? static_cast<std::int32_t>(centre->GetFormID()) : 0;
        std::snprintf(text, sizeof(text), "%.5f|%.5f|%.5f|%d|%.5f", op.arg[0], op.arg[1], op.arg[2], id, op.arg[4]);
    } else {
        std::snprintf(text, sizeof(text), "%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f", op.arg[0], op.arg[1], op.arg[2], op.arg[3],
            op.arg[4], op.arg[5], op.arg[6], op.arg[7]);
    }
    SKSE::ModCallbackEvent ev{ kEventNames[static_cast<int>(op.event)], text, op.arg[0], target };
    source->SendEvent(&ev);
}

// Round 23 (N4): the engine-side ops (StatusEngine.h RunOp). Defined below.
void QueueInterrupt(RE::ActorHandle actor);                         // InterruptCast(false) in a task (s9)
void CrowdOpOutsideBodies(const char* what) noexcept;               // round 24: the crowd ops belong to the body pass

// Round 25 (N6): the silence's drain (v0.4 5.1 沉默中無法施法、不回魔): the actor's current magicka to 0, the same
// actor-value path as Papyrus DamageActorValue (the effect's MagickaRateMult -100 keeps it from coming back).
void DrainAllMagicka(RE::Actor& actor)
{
    auto* values = actor.AsActorValueOwner();
    const float current = values->GetActorValue(RE::ActorValue::kMagicka);
    if (current > 0.0f) {
        values->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kMagicka, -current);
    }
}

// The write half of the engine adapter StatusEngine.h runs on: Dispel(true), CastSpellImmediate from the player's
// instant caster, the cost path, the ModEvent, the self-dispel flag the removal sink reads.
class RealEngine final : public EffectLists
{
public:
    RealEngine(RE::PlayerCharacter& player, RE::Actor* target, const std::vector<RE::Actor*>* crowd = nullptr) :
        EffectLists(player, target), playerCharacter_(player), caster_(CasterOf(player)), primary_(target), crowd_(crowd)
    {}

    // Round 24 (N5): the crowd member the next op acts on (StatusOp::at; 0 = the plan's own target).
    void Select(std::uint8_t at)
    {
        if (at == 0) {
            target_ = primary_;
        } else if (crowd_ && at < crowd_->size()) {
            target_ = (*crowd_)[at];
        } else {
            throw std::runtime_error("status op on a crowd member the plan did not read");
        }
    }

    void Dispel(essb::Who, Handle effect) { effect->Dispel(true); }
    bool SelfDispel() const noexcept { return t_selfDispel; }
    void SetSelfDispel(bool on) noexcept { t_selfDispel = on; }

    RE::Actor& On(essb::Who who)
    {
        RE::Actor* actor = ActorOf(who);
        if (!actor) {
            throw std::runtime_error("status op on a missing target");
        }
        return *actor;
    }

    void Cast(essb::Who who, std::uint32_t spell, float magnitude, float effectiveness)
    {
        RE::Actor& on = On(who);
        const bool watch = CausedLogging() && !on.IsDead();   // round 26b (L3 A/B)
        caster_.CastSpellImmediate(SpellById(spell), false, &on, effectiveness, false, magnitude, &playerCharacter_);
        if (CausedLogging()) {
            for (const auto& row : essb::status::kDomainSpawn) {
                if (std::find(std::begin(row), std::end(row), spell) != std::end(row) && spell != 0) {
                    LogCaused("hazard", &on, t_traceCtx);
                    break;
                }
            }
            if (watch && on.IsDead()) {
                LogCaused("kill", &on, t_traceCtx);
            }
        }
    }

    bool Dead(essb::Who who) { return On(who).IsDead(); }

    // Round 25 (N6): a silence takes the magicka to 0 at once (was ESSBSilence.OnEffectStart).
    void DrainMagickaAll(essb::Who who)
    {
        if (RE::Actor* actor = ActorOf(who)) {
            DrainAllMagicka(*actor);
        }
    }

    void PayHealth(float amount)
    {
        auto* values = playerCharacter_.AsActorValueOwner();
        const float pay = (std::min)(amount, values->GetActorValue(RE::ActorValue::kHealth) - 1.0f);
        if (pay > 0.0f) {
            values->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kHealth, -pay);
        }
    }

    void Send(const essb::StatusOp& op)
    {
        RE::Actor* centre = nullptr;
        if (op.event == essb::Event::kPush && op.arg[3] >= 0.5f) {
            const std::size_t member = static_cast<std::size_t>(op.arg[3] + 0.5f) - 1;
            centre = member == 0 ? primary_ : (crowd_ && member < crowd_->size() ? (*crowd_)[member] : nullptr);
        }
        SendEvent(op, target_, centre);
        if (op.event == essb::Event::kPush || op.event == essb::Event::kKnock) {
            LogCaused(op.event == essb::Event::kPush ? "push" : "knock", target_, t_traceCtx);   // round 26b (L3 A/B)
        }
    }

    // Round 23 review: the part of a hit the pools could not take. The same actor-value path as the console's
    // `damageav health` / Papyrus DamageActorValue, with no clamp: at 0 the engine's death handling runs (inference;
    // probe card step "guard death").
    void HurtHealth(float amount)
    {
        if (amount > 0.0f) {
            const bool watch = CausedLogging() && !playerCharacter_.IsDead();
            playerCharacter_.AsActorValueOwner()->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kHealth, -amount);
            if (watch && playerCharacter_.IsDead()) {
                LogCaused("kill", &playerCharacter_, t_traceCtx);   // round 26b (L3 A/B)
            }
        }
    }

    // Round 23 (N4): the engine-side ops of the self layer and the hurt path.
    void PayStamina(float amount)
    {
        auto* values = playerCharacter_.AsActorValueOwner();
        const float pay = (std::min)(amount, values->GetActorValue(RE::ActorValue::kStamina));
        if (pay > 0.0f) {
            values->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kStamina, -pay);
        }
    }
    // Round 24: the crowd ops are the body pass's (Reactions.h RunBodies consumes them); reaching the engine means a
    // plan ran without its bodies -- logged, nothing scanned here (ruling R6: one scan per event).
    void Resonance() { CrowdOpOutsideBodies("resonance"); }
    void Interrupt(essb::Who who)
    {
        if (RE::Actor* actor = ActorOf(who)) {
            QueueInterrupt(actor->GetHandle());
        }
    }
    void CrushArea(const essb::StatusOp&) { CrowdOpOutsideBodies("crush area"); }
    void FreezeNearby() { CrowdOpOutsideBodies("freeze nearby"); }

    // Round 26 (the probe log): StatusEngine.h RunOp calls these for every op while the level is 4.
    bool Tracing() const noexcept { return TraceOn(); }

    std::uint64_t TraceOp(const essb::StatusOp& op, const essb::Lowered& l, essb::Who on)
    {
        RE::Actor* actor = ActorOf(on);
        // the instance this op replaces or removes, before the dispel: its magnitude (layers) and what was left of it
        int count = 0;
        float was = 0.0f;
        float left = 0.0f;
        if (actor && (l.dispelSpell || l.dispelEffect)) {
            ForEach(on, [&](const essb::engine::EffectView& v, Handle) {
                if ((l.dispelSpell && v.spell == l.dispelSpell) || (l.dispelEffect && v.effect == l.dispelEffect)) {
                    if (count++ == 0) {
                        was = v.magnitude;
                        left = (std::max)(0.0f, v.duration - v.elapsed);
                    }
                }
            });
        }
        essb::trace::Line line("op");
        essb::trace::OpLine(line, t_traceCtx, op, FactsOf(actor), l, count, was, left);
        return Emit(line);
    }

    void TraceDone(std::uint64_t seq, essb::Who on)
    {
        essb::trace::Line line("op-done");
        essb::trace::OpDoneLine(line, seq, FactsOf(ActorOf(on)));
        Emit(line);
    }

    void LogReapply(const essb::StatusOp& op, int dispelled)
    {
        if (state.forms.debug->value >= 3.0f) {  // probe N3-2: one re-apply, how many old instances went first (expect 1)
            Logf("[ESSB][N3-2][L3] dot=%s magnitude=%.2f seconds=%.1f dispelled=%d", op.op == essb::Op::kBleedDot ? "bleed" : "poison",
                op.magnitude, op.seconds, dispelled);
        }
    }

    void LogWash(const essb::engine::EffectView& v, bool washed)
    {
        if (state.forms.debug->value >= 3.0f) {  // probe N3-3: every effect the wash looked at, and the verdict
            Logf("[ESSB][N3-3][L3] effect=%08X type=%d castingSource=%d duration=%.1f hostile=%d ours=%d -> %s", v.effect,
                v.spellType, v.castingSource, v.duration, v.hostile ? 1 : 0, v.ours ? 1 : 0, washed ? "washed" : "kept");
        }
        if (TraceOn()) {   // round 26
            essb::trace::Line line("wash");
            line.Actor("on", FactsOf(target_));
            line.F(" effect=%08X type=%d castingSource=%d duration=%.1f elapsed=%.1f hostile=%d ours=%d company=%d verdict=%s", v.effect,
                v.spellType, v.castingSource, v.duration, v.elapsed, v.hostile ? 1 : 0, v.ours ? 1 : 0, v.company ? 1 : 0, washed ? "washed" : "kept");
            Emit(line);
        }
    }

private:
    RE::PlayerCharacter& playerCharacter_;
    RE::MagicCaster& caster_;
    RE::Actor* primary_;
    const std::vector<RE::Actor*>* crowd_;
};

class Executor
{
public:
    Executor(RE::PlayerCharacter& player, RE::Actor* target, const essb::Tuning& tuning, const std::vector<RE::Actor*>* crowd = nullptr) :
        engine_(player, target, crowd), tuning_(tuning)
    {}

    void Run(const essb::StatusPlan& plan)
    {
        if (plan.overflow) {
            throw std::runtime_error("status plan overflow");
        }
        essb::engine::RunPlan(engine_, plan, tuning_);
    }

private:
    RealEngine engine_;
    const essb::Tuning& tuning_;
};

// What a planner needs besides the boards, for the player and (optionally) a target.
struct Context {
    essb::Tuning tuning{};
    essb::PlayerFacts player{};
    essb::StatusInputs in{};
};

Context MakeContext(RE::PlayerCharacter& player, bool iceArmor)
{
    Context c;
    c.tuning = essb::ReadTuning(Global);
    c.player = ReadPlayer(player);
    c.in.config = &kConfig;
    c.in.tuning = &c.tuning;
    c.in.player = c.player;
    c.in.self = ReadSelf(player);
    c.in.iceArmor = iceArmor;
    // Round 23: the N4 layer is live in the game (the round-22 scenario tables run without it).
    c.in.n4 = true;
    c.in.formElement = state.forms.formActive->value == 1.0f ? static_cast<int>(state.forms.element->value) : 0;
    return c;
}

bool FormIsActive() noexcept
{
    return state.forms.formActive->value == 1.0f;
}

// ---------------------------------------------------------------- round 24: the crowd (one scan per event)

std::array<float, 3> PosOf(const RE::Actor& actor)
{
    const RE::NiPoint3 p = actor.GetPosition();
    return { p.x, p.y, p.z };
}

std::array<float, 3> PosOfRef(const RE::TESObjectREFR& ref)
{
    const RE::NiPoint3 p = ref.GetPosition();
    return { p.x, p.y, p.z };
}

bool HasOurEffect(RE::Actor& actor, const RE::EffectSetting* wanted)
{
    bool found = false;
    if (wanted) {
        ForEachRunningEffect(actor, [&](RE::ActiveEffect&, RE::EffectSetting& base) { found = found || &base == wanted; });
    }
    return found;
}

// Probe N5-1: how many of our effects an actor still runs (the death sink logs it for both death events).
int CountOurEffects(RE::Actor& actor)
{
    int count = 0;
    ForEachRunningEffect(actor, [&](RE::ActiveEffect&, RE::EffectSetting& base) {
        const auto* file = base.GetFile(0);
        if (file && file->GetFilename() == kPlugin) {
            ++count;
        }
    });
    return count;
}

// Round 26c (P6): the alias list's read lock is taken and released in this SEH-only frame (__finally), so an access
// violation inside the walk, caught by a task's __except further up, still releases the engine lock (a BSReadLockGuard's
// destructor would be skipped by the SEH unwind under /EHsc).
bool QuestObjectAlias(const RE::ExtraAliasInstanceArray* aliases) noexcept
{
    auto& lock = const_cast<RE::BSReadWriteLock&>(aliases->lock);
    lock.LockForRead();
    bool found = false;
    __try {
        for (std::uint32_t i = 0; i < aliases->aliases.size() && !found; ++i) {
            const auto* data = aliases->aliases[i];
            found = data && data->alias && data->alias->IsQuestObject();
        }
    } __finally {
        lock.UnlockForRead();
    }
    return found;
}

// 2.9 必要角色 (review fix 2): essential (the reference or its base), or filling a quest-object alias. A unique or
// protected named enemy is not exempt from being knocked down, raised or turned to ash.
bool EssentialOf(RE::Actor& actor)
{
    if (actor.IsEssential()) {
        return true;
    }
    const auto* base = actor.GetActorBase();
    if (base && base->IsEssential()) {
        return true;
    }
    if (const auto* aliases = actor.extraList.GetByType<RE::ExtraAliasInstanceArray>()) {
        return QuestObjectAlias(aliases);
    }
    return false;
}

// Everything a body reads about one actor (Reactions.h Member).
// Round 26b: everything a body reads about one actor except its distance to you (the death sink's corpse read).
void ReadMemberSelf(essb::Member& m, RE::Actor& actor, bool ally)
{
    const essb::TargetFacts facts = TargetFactsOf(actor);
    m = essb::Member{};
    m.has = true;
    m.ally = ally;
    m.board = ReadBoard(actor);
    m.body = ReadBodyOnly(actor, facts);
    m.pos = PosOf(actor);
    m.level = actor.GetLevel();
    m.dragon = state.forms.dragon && actor.HasKeyword(state.forms.dragon);
    m.essential = EssentialOf(actor);
    m.spellUser = facts.spellUser;
    auto* v = actor.AsActorValueOwner();
    m.armor = v->GetActorValue(RE::ActorValue::kDamageResist);
    m.resist = { v->GetActorValue(RE::ActorValue::kResistFire), v->GetActorValue(RE::ActorValue::kResistFrost),
        v->GetActorValue(RE::ActorValue::kResistShock), v->GetActorValue(RE::ActorValue::kPoisonResist),
        v->GetActorValue(RE::ActorValue::kResistMagic) };
    m.magicka = v->GetActorValue(RE::ActorValue::kMagicka);
    m.magickaMax = MaxOf(actor, RE::ActorValue::kMagicka);
}

void ReadMember(essb::Member& m, RE::Actor& actor, RE::PlayerCharacter& player, bool ally)
{
    const essb::TargetFacts facts = TargetFactsOf(actor);
    m = essb::Member{};
    m.has = true;
    m.ally = ally;
    m.board = ReadBoard(actor);
    m.body = ReadBody(actor, player, facts);
    m.pos = PosOf(actor);
    m.level = actor.GetLevel();
    m.dragon = state.forms.dragon && actor.HasKeyword(state.forms.dragon);
    m.essential = EssentialOf(actor);
    m.spellUser = facts.spellUser;
    auto* v = actor.AsActorValueOwner();
    m.armor = v->GetActorValue(RE::ActorValue::kDamageResist);
    m.resist = { v->GetActorValue(RE::ActorValue::kResistFire), v->GetActorValue(RE::ActorValue::kResistFrost),
        v->GetActorValue(RE::ActorValue::kResistShock), v->GetActorValue(RE::ActorValue::kPoisonResist),
        v->GetActorValue(RE::ActorValue::kResistMagic) };
    m.magicka = v->GetActorValue(RE::ActorValue::kMagicka);
    m.magickaMax = MaxOf(actor, RE::ActorValue::kMagicka);
}

// One event's crowd: member 0 = `primary` (its board may come from the planner, which has not been executed yet), the
// others read from the high process list ONCE (main thread; the handles are collected first, then each actor is read;
// native-verification-3 s11). The pointers keep the actors alive while the plan runs.
struct CrowdRead {
    std::unique_ptr<essb::Crowd> crowd = std::make_unique<essb::Crowd>();
    std::vector<RE::NiPointer<RE::Actor>> keep;
    std::vector<RE::Actor*> actors;   // [member]; [0] = the primary (null when none)
    bool built = false;
};

void BuildCrowd(CrowdRead& out, RE::PlayerCharacter& player, RE::Actor* primary, const essb::Board* primaryBoard, float aroundPrimary,
    float aroundYou)
{
    out.built = true;
    essb::Crowd& c = *out.crowd;
    c = essb::Crowd{};
    c.you = PosOf(player);
    out.keep.clear();
    out.actors.assign(1, primary);
    if (primary) {
        ReadMember(c.m[0], *primary, player, false);
        if (primaryBoard) {
            c.m[0].board = *primaryBoard;
        }
    }
    auto* lists = RE::ProcessLists::GetSingleton();
    if (!lists) {
        return;
    }
    std::vector<RE::NiPointer<RE::Actor>> seen;
    std::vector<essb::engine::ActorView> views;
    for (auto& handle : lists->highActorHandles) {
        auto ptr = handle.get();
        RE::Actor* actor = ptr.get();
        if (!actor) {
            continue;
        }
        essb::engine::ActorView v;
        v.you = actor == &player;
        v.dead = actor->IsDead();
        v.loaded = actor->Is3DLoaded();
        v.teammate = actor->IsPlayerTeammate();
        v.commanded = actor->IsCommandedActor();
        v.hostile = !v.you && !v.dead && actor->IsHostileToActor(&player);
        v.pos = PosOf(*actor);
        views.push_back(v);
        seen.push_back(ptr);
    }
    // the engaged marker is read only for the non-hostile ones near enough to matter (it walks their effect list)
    const std::array<float, 3> centre = primary ? PosOf(*primary) : c.you;
    int skip = -1;
    for (std::size_t i = 0; i < views.size(); ++i) {
        if (seen[i].get() == primary) {
            skip = static_cast<int>(i);
        } else if (!views[i].hostile && !views[i].teammate && !views[i].dead &&
                   (essb::Distance(views[i].pos, centre) <= aroundPrimary || essb::Distance(views[i].pos, c.you) <= aroundYou)) {
            views[i].engaged = HasOurEffect(*seen[i], state.forms.engaged);
        }
    }
    // Round 26: the probe log hears the verdict on every actor of the list (SelectCrowd is SelectCrowdWhy without it).
    const bool tracing = TraceOn();
    std::vector<essb::engine::Pick> why;
    if (tracing) {
        why.assign(views.size(), essb::engine::Pick::kFar);
    }
    const auto picks = essb::engine::SelectCrowdWhy(views, skip, centre, aroundPrimary, c.you, aroundYou, essb::n5::kCrowdMax,
        [&](int i, essb::engine::Pick verdict) {
            if (tracing) {
                why[static_cast<std::size_t>(i)] = verdict;
            }
        });
    std::vector<int> member(tracing ? views.size() : 0, 0);
    for (const auto& pick : picks) {
        if (c.count >= essb::kCrowdSlots) {
            break;
        }
        RE::Actor* actor = seen[pick.index].get();
        ReadMember(c.m[c.count], *actor, player, pick.ally);
        out.keep.push_back(seen[pick.index]);
        out.actors.push_back(actor);
        if (tracing) {
            member[static_cast<std::size_t>(pick.index)] = c.count;
        }
        ++c.count;
    }
    if (tracing) {
        essb::trace::Line head("scan");
        head.F(" ctx=%s", t_traceCtx);
        head.Actor("centre", FactsOf(primary));
        head.F(" aroundCentre=%.0f aroundYou=%.0f high=%d picked=%d", aroundPrimary, aroundYou, static_cast<int>(views.size()), c.count - 1);
        Emit(head);
        const float bound = 2.0f * (std::max)(aroundPrimary, aroundYou) + 700.0f;
        int beyond = 0;
        for (std::size_t i = 0; i < views.size(); ++i) {
            const float dYou = essb::Distance(views[i].pos, c.you);
            const float dCentre = essb::Distance(views[i].pos, centre);
            if (why[i] == essb::engine::Pick::kFar && (std::min)(dYou, dCentre) > bound) {
                ++beyond;
                continue;
            }
            essb::trace::Line row("scan-c");
            row.Actor("who", FactsOf(seen[i].get()));
            row.F(" d_you=%.0f d_centre=%.0f hostile=%d teammate=%d engaged=%d verdict=%s member=%d", dYou, dCentre, views[i].hostile ? 1 : 0,
                views[i].teammate ? 1 : 0, views[i].engaged ? 1 : 0, essb::engine::kPickNames[static_cast<int>(why[i])], member[i]);
            Emit(row);
        }
        if (beyond > 0) {
            essb::trace::Line row("scan-c");
            row.F(" beyond=%d verdict=far", beyond);
            Emit(row);
        }
    }
    if (state.forms.debug->value >= 3.0f) {   // probe N5-2: one scan per event; who it picked, how far from you
        Logf("[ESSB][N5-2][L3] scan high=%d picked=%d centre=%08X", static_cast<int>(views.size()), c.count - 1,
            primary ? primary->GetFormID() : 0u);
        for (int k = 1; k < c.count; ++k) {
            RE::Actor* a = out.actors[k];
            Logf("[ESSB][N5-2][L3]   %d %08X %s d=%.0f ally=%d", k, a->GetFormID(), a->GetName(), essb::Distance(c.you, c.m[k].pos),
                c.m[k].ally ? 1 : 0);
        }
    }
}

// Does the plan (from `from`) have anything the body pass needs a crowd for?
bool NeedsCrowd(const essb::StatusPlan& plan, int from)
{
    using essb::Op;
    for (int i = from; i < plan.count; ++i) {
        const essb::StatusOp& op = plan.ops[i];
        if ((op.op == Op::kEvent && (essb::BodyOnly(op.event) || op.event == essb::Event::kOpen || op.event == essb::Event::kEnd ||
                                        op.event == essb::Event::kHallucinate)) ||
            op.op == Op::kResonance || op.op == Op::kCrushArea || op.op == Op::kFreezeNearby ||
            (op.op == Op::kDamage && op.arg[0] > 0.0f)) {
            return true;
        }
    }
    return false;
}

essb::BodyInputs BodyInputsOf(RE::PlayerCharacter& player, const Context& c, bool sneak)
{
    essb::BodyInputs bin;
    bin.in = &c.in;
    bin.hitSneak = sneak;
    auto* v = player.AsActorValueOwner();
    bin.stamina = v->GetActorValue(RE::ActorValue::kStamina);
    bin.staminaMax = MaxOf(player, RE::ActorValue::kStamina);
    bin.magicka = v->GetActorValue(RE::ActorValue::kMagicka);
    bin.magickaMax = MaxOf(player, RE::ActorValue::kMagicka);
    return bin;
}

// The crowd radii of an event centred on a target: 15 m around it (the "附近" bodies) and 15 m around you (濺血, 血約,
// 天雷, 冰心, 過熱, 聖光).
constexpr float kAroundEvent = 1050.0f;

// Runs the body pass on plan.ops[from..] if it has bodies (building the crowd on first need), then executes the plan.
// `targetBoard` is the planner's board of the primary (kept in step with member 0 both ways).
template <class Nodes>
void RunWithBodies(RE::PlayerCharacter& player, RE::Actor* primary, essb::Board* targetBoard, essb::StatusPlan& plan, int from,
    essb::Board& self, Context& c, const Nodes& nodes, CrowdRead& crowd, bool sneak = false)
{
    if (NeedsCrowd(plan, from)) {
        if (!crowd.built) {
            BuildCrowd(crowd, player, primary, targetBoard, kAroundEvent, kAroundEvent);
        } else if (targetBoard && primary) {
            crowd.crowd->m[0].board = *targetBoard;
        }
        if (primary) {
            c.in.body = crowd.crowd->m[0].body;
        }
        const essb::BodyInputs bin = BodyInputsOf(player, c, sneak);
        essb::RunBodies(plan, from, *crowd.crowd, self, bin, nodes, Rng());
        if (targetBoard && primary) {
            *targetBoard = crowd.crowd->m[0].board;
        }
    }
    Executor(player, primary, c.tuning, crowd.built ? &crowd.actors : nullptr).Run(plan);
}

int FormElement() noexcept
{
    return FormIsActive() ? static_cast<int>(state.forms.element->value) : 0;
}

// ---------------------------------------------------------------- report

std::string_view ProcName(int element, bool power)
{
    const essb::ProcRow* row = essb::FindProc(element, power);
    return row ? row->name : std::string_view("?");
}

void Report(const essb::Plan& plan, const essb::Attack& attack, int weaponType, const RE::Actor& target, const essb::HitStatus& status)
{
    if (state.forms.debug->value < 2.0f) {
        return;
    }
    Logf("[ESSB][hit][L2] %08X element=%d weapon=%d power=%d sneak=%d magnitude=%.2f crit=%d siphon=%.2f burned=%.2f casts=%d opened=%d cut=%d",
        target.GetFormID(), plan.element, weaponType, int(attack.power), int(attack.sneakAttack), plan.magnitude,
        int(plan.crit), plan.siphon, plan.burned, plan.count, int(status.opened), status.cutFrom);
    if (!ProcNoticeDue()) {
        return;
    }
    char amount[96];
    std::string text;
    if (essb::IsElement(plan.element)) {
        const std::string_view name = ProcName(plan.element, attack.power);
        std::snprintf(amount, sizeof(amount), " 強度 %.1f", plan.magnitude);
        text = "元素附傷：";
        text += essb::elementNames[plan.element];
        text += " ";
        text.append(name.data(), name.size());
        text += amount;
        if (plan.crit) {
            text += " 暴擊";
        }
    } else {
        std::snprintf(amount, sizeof(amount), "真傷 %.1f（吸魔 %.1f、燒魔 %.1f）", plan.magnitude, plan.siphon, plan.burned);
        text = plan.dispel ? "無元素滅法：" : "無元素：";
        text += amount;
    }
    Notify(std::move(text));
}

// Round 26: one proc as the probe log shows it (the target before the proc lands, the plan's casts, the draws it took).
void TraceProc(const char* src, const essb::Plan& plan, const essb::Attack& attack, int weaponType, RE::Actor* target, int charges, float critBonus)
{
    essb::trace::Line line("proc");
    const std::string_view spell = essb::IsElement(plan.element) ? ProcName(plan.element, attack.power) : std::string_view("-");
    const std::string rolls = Rng().Tape();
    essb::trace::ProcLine(line, src, FactsOf(target), FactsOf(RE::PlayerCharacter::GetSingleton()), plan, attack, weaponType, spell, charges,
        critBonus, rolls);
    Emit(line);
    Rng().Record(true);   // the rest of the event's draws go to its "rng" line
}

// The draws an event took after its proc (chances, the bodies' rolls), one line; recording stops.
void TraceDraws(const char* ctx)
{
    if (Rng().Count() > 0) {
        essb::trace::Line line("rng");
        line.F(" ctx=%s draws=%s", ctx, Rng().Tape().c_str());
        Emit(line);
    }
    Rng().Record(false);
}

constexpr const char* RejectName(essb::Reject reason) noexcept
{
    constexpr const char* names[] = { "accepted", "not-player", "disabled", "bash-or-blocked", "bad-target", "ally",
        "unsupported-weapon", "melee-with-projectile", "dead-target", "bad-element" };
    return names[static_cast<int>(reason)];
}

// ---------------------------------------------------------------- the hit handler

// The status terms of every element for this hit (the form's proc, 雙生's left hand, 餘響's echo).
template <class Nodes>
essb::StatusTerms TermsFor(bool power, const essb::Tuning& tuning, const essb::Board& target, const essb::Board& self,
    const essb::Body& body, const Nodes& nodes)
{
    essb::StatusTerms terms;
    for (int element = essb::kFire; element <= essb::kAstral; ++element) {
        const essb::ProcTerm term = essb::ProcTerms(element, power, tuning, target, self, body, nodes);
        terms.add[element] = term.add;
        terms.mult[element] = term.mult;
    }
    return terms;
}

void HandleHurt(const RE::TESHitEvent& ev, RE::PlayerCharacter& player);

// 極致 (5.2): one more full proc of the form's element on the target, with this hit's flags and the statuses now.
template <class Nodes>
void ExtraProc(RE::PlayerCharacter& player, RE::Actor& target, const essb::Attack& hit, Context& c, const essb::TargetFacts& facts,
    const essb::StatusTerms& terms, const Nodes& nodes)
{
    essb::Attack attack = hit;
    attack.leftHand = false;
    essb::Plan plan;
    const essb::Proc proc = essb::RollProc(attack.element, attack, kConfig, c.tuning, c.player, facts, nodes, Rng(), terms);
    plan.Add({ essb::Cast::kProc, proc.magnitude, attack.element, attack.power });
    if (TraceOn()) {   // round 26 (the plan's element / magnitude / crit fields are only read by the log)
        plan.element = attack.element;
        plan.magnitude = proc.magnitude;
        plan.crit = proc.crit;
        TraceProc("extra", plan, attack, -1, &target, terms.charges, terms.critBonus);
    }
    Apply(player, target, plan);
}

// Round 26c (P1): what the hit sink read at hit time; the hit task plans and applies from it one frame later.
struct HitSeen {
    RE::ActorHandle target{};
    essb::HitFacts facts{};
    essb::Verdict verdict{};
    essb::RawAttack raw{};
};

// The hit task's body: everything a hit does, from the snapshot. `player` and `target` are live (checked by the caller).
void Handle(const HitSeen& seen, RE::PlayerCharacter& playerRef, RE::Actor& targetRef)
{
    RE::PlayerCharacter* player = &playerRef;
    RE::Actor* target = &targetRef;
    TraceCtx traceCtx("hit");   // round 26
    const essb::HitFacts& hit = seen.facts;
    const essb::Verdict& verdict = seen.verdict;
    if (state.forms.debug->value >= 3.0f) {
        state.probeTarget = target->GetHandle();   // probe N4-2 follows the last actor you hit
    }

    using K = essb::StatusKind;
    const bool formActive = hit.formActive == 1.0f;
    essb::Attack attack = essb::MakeAttack(verdict.element, seen.raw);
    const bool realPower = attack.power;
    const auto perks = MakeNodes(*player, formActive);
    const essb::TargetFacts targetFacts = TargetFactsOf(*target);
    essb::Board targetBoard = ReadBoard(*target);
    essb::Board selfBoard = ReadBoard(*player);
    const auto nodes = essb::WithAvatar(perks, selfBoard);   // 化身: the form's legend main line reads full for 10 s
    // v0.4 2.1: every hit on a downed target counts as a power attack (without the power attack's costs).
    if (targetBoard.Has(K::kDowned)) {
        attack.power = true;
    }
    const bool iceArmor = formActive && attack.element == essb::kFrost && nodes.Has(essb::node::kFrostIceArmor);
    Context c = MakeContext(*player, iceArmor);
    c.in.body = ReadBody(*target, *player, targetFacts);
    // Round 23 (N4): your resources feed the hit -- the charges (雷's N and crit, 疾電), the overload pool (滅法 spends it
    // first, ×1.5), 破式 at full resolve, and a blood power hit's cost / 回湧 / 血刃.
    c.player.overload = selfBoard.Has(K::kOverload) ? selfBoard[K::kOverload].magnitude : 0.0f;
    c.player.overloadCap = essb::res::OverloadCap(c.player.magickaMax, nodes);

    essb::StatusTerms terms = TermsFor(attack.power, c.tuning, targetBoard, selfBoard, c.in.body, nodes);
    terms.charges = selfBoard.Layers(K::kCharge);
    terms.critBonus = selfBoard.Has(K::kQuickShock) ? essb::n4::kQuickShock : 0.0f;
    terms.breakForm = attack.element == essb::kNoElement && attack.power && nodes.Has(essb::node::kNoFormBreak) &&
                      selfBoard.Layers(K::kResolve) >= essb::n4::kResolveCap;
    bool consumeStreak = false;
    if (attack.element == essb::kWind) {
        terms.windSneak = essb::WindSneakExtra(attack.sneakAttack, selfBoard, nodes, consumeStreak);
    }
    // 雙生: a left-hand hit inside the twin window marks with the previous form's element (Papyrus did the same).
    int markElement = attack.element;
    if (attack.leftHand && c.player.twinWindow && essb::IsElement(c.tuning.twinElement)) {
        markElement = c.tuning.twinElement;
    }
    essb::SelfHit self;
    self.element = markElement;
    self.formElement = c.in.formElement;
    self.power = attack.power;
    self.sneak = attack.sneakAttack;
    self.bloodCost = essb::BloodPowerTerms(attack.element, attack.power, realPower, c.in.self, selfBoard, nodes, terms, self.surgeUp);
    self.targetCasting = IsCasting(*target);
    // 聖痕 (5.9): a target carrying the divine mark is judged undead / daedra for the hit's ×1.5 (review fix 4); the
    // body facts above keep the real answer for ProcTerms' +10% on the living.
    const essb::TargetFacts judged = essb::JudgedTarget(targetFacts, targetBoard, nodes);
    const bool tracing = TraceOn();   // round 26: the proc's rolls, then every other draw of this hit
    if (tracing) {
        Rng().Record(true);
    }
    const essb::Plan plan = essb::PlanHit(attack, kConfig, c.tuning, c.player, judged, nodes, Rng(), terms);
    if (tracing) {
        TraceProc("hit", plan, attack, verdict.weaponType, target, terms.charges, terms.critBonus);
    }
    Apply(*player, *target, plan);
    if (plan.consumeEcho) {
        QueueMarkerDispel(Marker::kEcho);
    }
    if (plan.consumeRiposte) {
        QueueMarkerDispel(Marker::kRiposte);
    }
    self.crit = plan.crit;

    essb::HitStatus status;
    auto statusPlanPtr = std::make_unique<essb::StatusPlan>();   // 28 KB: on the heap, not on the engine's stack
    essb::StatusPlan& statusPlan = *statusPlanPtr;
    CrowdRead crowd;   // round 24: read once, only if a body needs it
    if (essb::IsElement(attack.element)) {
        // 回聲 (5.13): a star hit on a target that already carried star marks, outside the dark star.
        const bool echo = markElement == essb::kAstral && targetBoard.Has(K::kStar) && !selfBoard.Has(K::kCosmos);
        const bool avatarBefore = selfBoard.Has(K::kAvatar);
        status = essb::PlanStatusHit(statusPlan, markElement, attack.power, targetBoard, selfBoard, c.in, nodes, Rng());
        if (consumeStreak) {
            essb::Writer{ statusPlan, selfBoard, essb::Who::kPlayer }.Clear(K::kKillStreak);   // 連殺 used up
        }
        const essb::SelfResult result = essb::PlanSelfHit(statusPlan, self, status, targetBoard, selfBoard, c.in, nodes, Rng());
        // Round 24 (N5): the hit's own branch bodies (震擊, 護持, 萎靡, 侵蝕, the curse's erosion) on member 0, then the
        // crowd bodies: every open / end / frozen ... event this hit produced, 回聲, 印潮, 化身's active legend.
        const bool surge = status.cutFrom != 0 && status.opened && nodes.Has(essb::node::kCommonSurge);
        const bool avatar = !avatarBefore && selfBoard.Has(K::kAvatar);
        if (NeedsCrowd(statusPlan, 0) || echo || surge || avatar) {
            const essb::Board planned = targetBoard;
            BuildCrowd(crowd, *player, target, &planned, kAroundEvent, kAroundEvent);
        } else {
            crowd.actors.assign(1, target);   // member 0 alone: no scan
            ReadMember(crowd.crowd->m[0], *target, *player, false);
            crowd.crowd->m[0].board = targetBoard;
            crowd.crowd->you = PosOf(*player);
        }
        c.in.body = crowd.crowd->m[0].body;
        {
            const essb::BodyInputs bin = BodyInputsOf(*player, c, attack.sneakAttack);
            essb::Crowd& cw = *crowd.crowd;
            essb::PlanHitBodies(statusPlan, cw, selfBoard, bin, markElement, attack.power, 0, nodes, Rng());
            if (echo) {
                essb::PlanEcho(statusPlan, cw, 0, plan.magnitude, c.in, nodes);
            }
            if (surge) {
                essb::PlanSurge(statusPlan, cw, selfBoard, bin, markElement, status.cutFrom, nodes, Rng());   // 印潮
            }
            if (avatar) {
                const essb::AvatarNodes<std::remove_cvref_t<decltype(perks)>> full{ perks, c.in.formElement };
                essb::PlanAvatarBurst(statusPlan, cw, selfBoard, bin, c.in.formElement, full, Rng());   // 化身
            }
            essb::RunBodies(statusPlan, 0, cw, selfBoard, bin, nodes, Rng());
            targetBoard = cw.m[0].board;
        }
        Executor(*player, target, c.tuning, &crowd.actors).Run(statusPlan);
        // 風的多段觸發 (2.6): the takeover element's hit effects repeat; damage-type procs ×0.5 each, rolled again.
        for (int i = 0; i < result.repeats && !target->IsDead(); ++i) {
            essb::StatusTerms again = terms;
            for (float& m : again.mult) {
                m *= essb::n4::kMultiRepeat;
            }
            again.flat = {};
            essb::PlayerFacts once = c.player;
            once.echoPending = false;
            once.twinWindow = false;
            once.riposteWindow = false;
            TraceCtx repeatCtx("repeat");   // round 26
            const essb::Plan repeatHit = essb::PlanHit(attack, kConfig, c.tuning, once, judged, nodes, Rng(), again);
            if (tracing) {
                TraceProc("repeat", repeatHit, attack, verdict.weaponType, target, again.charges, again.critBonus);
            }
            Apply(*player, *target, repeatHit);
            essb::StatusInputs repeatIn = c.in;
            repeatIn.repeat = true;
            auto repeatPtr = std::make_unique<essb::StatusPlan>();
            essb::StatusPlan& repeatPlan = *repeatPtr;
            const essb::HitStatus repeated = essb::PlanStatusHit(repeatPlan, markElement, attack.power, targetBoard, selfBoard, repeatIn,
                nodes, Rng());
            essb::PlanSelfHit(repeatPlan, self, repeated, targetBoard, selfBoard, repeatIn, nodes, Rng(), true);
            RunWithBodies(*player, target, &targetBoard, repeatPlan, 0, selfBoard, c, nodes, crowd);
        }
        if (result.extraProc && !target->IsDead()) {
            ExtraProc(*player, *target, attack, c, judged, terms, nodes);
        }
    } else {
        essb::PlanSelfNoForm(statusPlan, plan, self, targetBoard, selfBoard, c.in, nodes, Rng().Real(0.0f, 1.0f));
        // 封印 (5.1, round 24): the dispel's silence reaches every hostile within 3 m of the target.
        int silence = 0;
        for (int i = 0; i < plan.count; ++i) {
            if (plan.steps[i].cast == essb::Cast::kSilence) {
                silence = plan.steps[i].seconds;
            }
        }
        if (silence > 0 && nodes.Has(essb::node::kNoFormSeal)) {
            const essb::Board planned = targetBoard;
            BuildCrowd(crowd, *player, target, &planned, kAroundEvent, kAroundEvent);
            const essb::BodyInputs bin = BodyInputsOf(*player, c, attack.sneakAttack);
            essb::PlanHitBodies(statusPlan, *crowd.crowd, selfBoard, bin, 0, attack.power, silence, nodes, Rng());
        }
        RunWithBodies(*player, target, &targetBoard, statusPlan, 0, selfBoard, c, nodes, crowd);
    }
    WriteMirrors(*player, selfBoard, nodes);
    if (tracing) {
        TraceDraws("hit");
        essb::trace::Line end("hit-end");   // round 26: the target and you after everything the hit did
        essb::trace::HitEndLine(end, FactsOf(target), FactsOf(player), statusPlan.count);
        Emit(end);
    }
    Report(plan, attack, verdict.weaponType, *target, status);
}

void HitTaskCpp(const HitSeen& seen) noexcept
{
    try {
        TaskScope scope("hit task");   // round 26c (P5)
        if (!Active()) {
            return;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto held = seen.target.get();
        RE::Actor* target = held.get();
        if (!player || !target) {
            return;
        }
        InHitTask inHit;   // a hit event our own casts raise here is dropped (the old re-entrancy guard)
        LogThreadOnce(Probe::kHitTask, "hit task");
        NoteTaskThread();
        if (target->IsDead()) {
            // Round 26c: the hit's own damage killed the target before this task (one frame after the hit): no proc on a
            // corpse. Logged so the probe sheet can tell it from a missing proc.
            if (state.forms.debug->value >= 3.0f) {
                Logf("[ESSB][hit-late][L3] %08X dead before the hit task (no proc)", target->GetFormID());
            }
            if (TraceOn()) {
                essb::trace::Line line("hit-late");
                line.Actor("tgt", FactsOf(target));
                line.F(" reason=dead");
                Emit(line);
            }
            return;
        }
        Handle(seen, *player, *target);
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the hit task");
    }
}

void HitTaskGuarded(const HitSeen& seen) noexcept
{
    __try {
        HitTaskCpp(seen);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the hit task");
    }
}

// Round 26c (P1): the hit sink does no engine work. It reads the event, the hand and the hit-time facts (flags, the
// equipped weapons, the globals, the target's dead / teammate flags), filters, and queues the hit task. The route
// (yours / on you / nested in our own hit task / neither) is Sinks.h RouteHit.
void HitSinkCpp(const RE::TESHitEvent& ev) noexcept
{
    try {
        if (!Active()) {
            return;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) {
            return;
        }
        auto* target = ev.target ? ev.target->As<RE::Actor>() : nullptr;
        switch (essb::sink::RouteHit(ev.cause.get() == player, target == player, t_inHitTask)) {
        case essb::sink::HitRoute::kIgnore:
        case essb::sink::HitRoute::kNested:
            return;
        case essb::sink::HitRoute::kHurt:
            HandleHurt(ev, *player);   // round 23: a hit whose target is you (Hurt.h); a snapshot, the hurt task does the work
            return;
        case essb::sink::HitRoute::kYours:
            break;
        }
        LogThreadOnce(Probe::kHit, "TESHitEvent");
        HitSeen seen;
        seen.facts = ReadHitFacts(ev, *player, target);
        seen.verdict = essb::Filter(seen.facts);
        if (seen.verdict.reason != essb::Reject::kAccepted) {
            if (state.forms.debug->value >= 3.0f) {
                Logf("[ESSB][hit-reject][L3] reason=%s weapon=%d", RejectName(seen.verdict.reason), seen.verdict.weaponType);
            }
            if (TraceOn()) {   // round 26
                essb::trace::Line line("hit-reject");
                line.Actor("tgt", FactsOf(target));
                line.F(" reason=%s weapon=%d", RejectName(seen.verdict.reason), seen.verdict.weaponType);
                Emit(line);
            }
            return;
        }
        seen.raw = ReadAttack(ev, *player, seen.verdict.weaponType);
        seen.target = target->GetHandle();
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([seen]() { HitTaskGuarded(seen); });
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the hit sink");
    }
}

class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESHitEvent* ev, RE::BSTEventSource<RE::TESHitEvent>*) override
    {
        if (!ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            HitSinkCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in the hit sink");
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

HitSink hitSink;

// ---------------------------------------------------------------- round 23: hits you take (Hurt.h)

// A magic item whose effects carry one of the destruction damage keywords (the spell half of the pools' PERK entries
// is bound to the same keywords, build_v03 base_rule_entries).
bool Destructive(RE::MagicItem& item)
{
    for (RE::Effect* effect : item.effects) {
        if (!effect || !effect->baseEffect) {
            continue;
        }
        for (RE::BGSKeyword* keyword : state.forms.destructive) {
            if (keyword && effect->baseEffect->HasKeyword(keyword)) {
                return true;
            }
        }
    }
    return false;
}

// The task after the damage: every hit you took this frame, in order; the damage of hit i is its "before" minus the next
// hit's "before" (the last one: minus your health now).
float DotDamageOf(RE::PlayerCharacter& player, RE::FormID spell);   // below (round 23 review)

void HurtCpp() noexcept
{
    try {
        TaskScope scope("hurt task");   // round 26c (P5)
        std::vector<std::pair<RE::ActorHandle, essb::HurtFacts>> hits;
        {
            std::lock_guard lock(state.hurtLock);
            hits.swap(state.hurts);
        }
        state.hurtQueued = false;
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!Enabled() || !player || hits.empty()) {   // master switch (review fix 3)
            return;
        }
        LogThreadOnce(Probe::kHurtTask, "hurt task");   // round 26: its own flag (it shared kHurt with the sink's line)
        NoteTaskThread();
        TraceCtx traceCtx("hurt");
        const bool tracing = TraceOn();
        auto* values = player->AsActorValueOwner();
        const float healthNow = values->GetActorValue(RE::ActorValue::kHealth);
        for (std::size_t i = 0; i < hits.size(); ++i) {
            essb::HurtFacts f = hits[i].second;
            f.healthAfter = i + 1 < hits.size() ? hits[i + 1].second.healthBefore : healthNow;
            auto attackerPtr = hits[i].first.get();
            RE::Actor* attacker = attackerPtr.get();
            if (attacker && attacker->IsDead()) {
                attacker = nullptr;
            }
            f.attacker = f.attacker && attacker != nullptr;
            if (f.cloakTick) {   // round 26c: the sink marked a cloak candidate; the check reads the attacker here
                bool cloak = false;
                if (attacker && state.forms.cloak) {
                    ForEachRunningEffect(*attacker, [&](RE::ActiveEffect&, RE::EffectSetting& effect) {
                        cloak = cloak || effect.HasKeyword(state.forms.cloak);
                    });
                }
                f.cloakTick = cloak;
            }
            f.dotDamage = f.sourceSpell ? DotDamageOf(*player, f.sourceSpell) : 0.0f;
            f.magicka = values->GetActorValue(RE::ActorValue::kMagicka);
            f.magickaMax = MaxOf(*player, RE::ActorValue::kMagicka);
            f.stamina = values->GetActorValue(RE::ActorValue::kStamina);
            const auto perks = MakeNodes(*player, FormIsActive());
            essb::Board me = ReadBoard(*player);
            if (i > 0 && f.guardBefore > 0.0f) {
                f.guardLeft = me.guardPool.has ? me.guardPool.magnitude : 0.0f;   // what the earlier hit of this frame left
            }
            const auto nodes = essb::WithAvatar(perks, me);
            essb::Board foe = f.attacker ? ReadBoard(*attacker) : essb::Board{};
            Context c = MakeContext(*player, false);
            c.in.self.health = f.healthAfter;   // the thresholds (自動洩壓, 越線, 冰心, 庇護) read your health after this hit
            if (f.attacker) {
                c.in.body = ReadBody(*attacker, *player, TargetFactsOf(*attacker));
            }
            auto planPtr = std::make_unique<essb::StatusPlan>();
            essb::StatusPlan& plan = *planPtr;
            std::string cdYou;
            std::string cdAttacker;
            if (tracing) {   // round 26: the cooldowns as the hit found them (before the plan sets new ones)
                cdYou = essb::trace::Cooldowns(me);
                cdAttacker = essb::trace::Cooldowns(foe);
                Rng().Record(true);
            }
            essb::PlanHurt(plan, f, foe, me, c.in, nodes, Rng());
            if (tracing) {
                essb::trace::Line line("hurt");
                essb::trace::HurtLine(line, FactsOf(f.attacker ? attacker : nullptr), FactsOf(player), f, c.in.formElement, plan.count, cdYou,
                    cdAttacker);
                Emit(line);
            }
            CrowdRead crowd;   // round 24: 冰心's scan, a retort's bodies (灼身、寒反…) run in the body pass
            RunWithBodies(*player, f.attacker ? attacker : nullptr, f.attacker ? &foe : nullptr, plan, 0, me, c, nodes, crowd);
            if (tracing) {
                TraceDraws("hurt");
            }
            WriteMirrors(*player, me, nodes);
            if (state.forms.debug->value >= 3.0f) {   // probe P8 / N4: the damage the task measured
                Logf("[ESSB][hurt][L3] before=%.2f after=%.2f lost=%.2f melee=%d spell=%d blocked=%d guard=%.2f magicka=%.2f dot=%.2f ops=%d",
                    f.healthBefore, f.healthAfter, (std::max)(0.0f, f.healthBefore - f.healthAfter), f.melee ? 1 : 0, f.spell ? 1 : 0,
                    f.blocked ? 1 : 0, f.guardBefore, f.magickaBefore, f.dotDamage, plan.count);
            }
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the hurt task");
    }
}

void HurtGuarded() noexcept
{
    __try {
        HurtCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the hurt task");
    }
}

// Round 23 review: the damage-over-time part of the spell that just hit you -- its running health-damage effects with a
// duration, Σ magnitude (after the PERK cut) × remaining seconds. Main thread (the hurt task).
float DotDamageOf(RE::PlayerCharacter& player, RE::FormID spell)
{
    float total = 0.0f;
    ForEachRunningEffect(player, [&](RE::ActiveEffect& ae, RE::EffectSetting& effect) {
        if (!ae.spell || ae.spell->GetFormID() != spell || ae.duration <= 0.0f || !effect.IsDetrimental()) {
            return;
        }
        const auto archetype = effect.GetArchetype();
        const bool modifier = archetype == RE::EffectSetting::Archetype::kValueModifier ||
                              archetype == RE::EffectSetting::Archetype::kDualValueModifier;
        if (modifier && effect.data.primaryAV == RE::ActorValue::kHealth) {
            total += (std::max)(0.0f, ae.magnitude) * (std::max)(0.0f, ae.duration - ae.elapsedSeconds);
        }
    });
    return total;
}

// In the hit sink (read only): the facts of a hit whose target is you, and your health / magicka / pools BEFORE the
// damage (native-verification-2 s15: TESHitEvent comes first on the melee, projectile and spell paths).
void HandleHurt(const RE::TESHitEvent& ev, RE::PlayerCharacter& player)
{
    if (!Enabled()) {   // master switch
        return;
    }
    LogThreadOnce(Probe::kHurt, "TESHitEvent (you are the target)");
    RE::TESObjectREFR* cause = ev.cause.get();
    auto* attacker = cause ? cause->As<RE::Actor>() : nullptr;
    if (attacker == &player) {
        return;
    }
    using Flag = RE::TESHitEvent::Flag;
    essb::HurtFacts f;
    // Only a hostile actor is "an attacker" (灼身, 寒反, 咒返... never land on a follower's stray swing).
    f.attacker = attacker && !attacker->IsDead() && attacker->IsHostileToActor(&player);
    auto* source = ev.source ? RE::TESForm::LookupByID(ev.source) : nullptr;
    auto* magic = source ? source->As<RE::MagicItem>() : nullptr;
    const bool projectile = ev.projectile != 0;
    f.spell = magic != nullptr;
    f.sourceSpell = magic ? magic->GetFormID() : 0;
    f.melee = !f.spell && !projectile;
    f.blocked = ev.flags.any(Flag::kHitBlocked);
    f.destructive = magic && Destructive(*magic);
    // Round 26c (P1): the sink reads no effect list (the tasks change them on another thread). The cloak check (a spell
    // hit with no projectile from an attacker wearing a cloak) is marked here and made in the hurt task; your pools come
    // from what the last task left (WriteMirrors: at most one 100 ms timer tick old).
    f.cloakTick = f.spell && !projectile && attacker && state.forms.cloak;
    auto* values = player.AsActorValueOwner();
    f.healthBefore = values->GetActorValue(RE::ActorValue::kHealth);
    f.magickaBefore = values->GetActorValue(RE::ActorValue::kMagicka);
    f.overloadBefore = state.mirrorOverload.load();
    f.guardBefore = state.mirrorGuard.load();
    f.afterimage = state.mirrorAfterimage.load();
    f.linger = state.mirrorLinger.load();
    {
        std::lock_guard lock(state.hurtLock);
        state.hurts.emplace_back(attacker ? attacker->GetHandle() : RE::ActorHandle{}, f);
    }
    const auto* tasks = SKSE::GetTaskInterface();
    if (tasks && !state.hurtQueued.exchange(true)) {
        tasks->AddTask([]() { HurtGuarded(); });
    }
}

// ---------------------------------------------------------------- round 23: an enemy casts (反咒, 逼近)

struct CastSeen {
    RE::ActorHandle caster{};
    RE::FormID spell = 0;
};

void CastCpp(const CastSeen& seen) noexcept;

void CastGuarded(const CastSeen& seen) noexcept
{
    __try {
        CastCpp(seen);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the spell-cast task");
    }
}

// TESSpellCastEvent comes after the cast has spent its magicka (native-verification-2 s6): read the caster and the spell,
// act in a task.
void OnCastCpp(const RE::TESSpellCastEvent& ev) noexcept
{
    try {
        if (!Enabled() || !ev.object || state.forms.formActive->value == 1.0f) {   // 大師與滅法：只在未開形態時
            return;
        }
        auto* caster = ev.object->As<RE::Actor>();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!caster || !player || caster == player) {
            return;
        }
        LogThreadOnce(Probe::kCast, "TESSpellCastEvent");
        const CastSeen seen{ caster->GetHandle(), ev.spell };
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([seen]() { CastGuarded(seen); });
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the spell-cast sink");
    }
}

class CastSink final : public RE::BSTEventSink<RE::TESSpellCastEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESSpellCastEvent* ev, RE::BSTEventSource<RE::TESSpellCastEvent>*) override
    {
        if (!ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            OnCastCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in the spell-cast sink");
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

CastSink castSink;

// Round 26c (T3): the bars' lifecycle calls at debug level 3, with the calling thread and TrueHUD's own.
void HudLog(const char* what, int bar) noexcept
{
    if (state.forms.debug && state.forms.debug->value >= 3.0f) {
        Logf("[ESSB][hud][L3] %s bar=%d thread=%lu truehud=%lu", what, bar, GetCurrentThreadId(), essb::hud::TrueHudThread());
    }
}

// Round 26c: TrueHUD's reload as a guarded task (the bars' state is the tasks').
void HudReloadCpp() noexcept
{
    try {
        TaskScope scope("hud reload");
        essb::hud::Reload();
    } catch (...) {
    }
}

void HudReloadGuarded() noexcept
{
    __try {
        HudReloadCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the hud reload task");
    }
}

// TrueHUD's menu (re)opening: its OnClose removed every custom widget, so the bars are loaded and added again.
void OnMenuCpp(const RE::MenuOpenCloseEvent& ev) noexcept
{
    try {
        if (TraceOn()) {   // round 26: every menu opening / closing (the pauses the sheet's steps make)
            auto* ui = RE::UI::GetSingleton();
            essb::trace::Line line("menu");
            line.F(" name=%s opening=%d paused=%d", ev.menuName.c_str(), ev.opening ? 1 : 0, ui && ui->GameIsPaused() ? 1 : 0);
            Emit(line);
        }
        if (ev.opening && ev.menuName == "TrueHUD") {
            if (const auto* tasks = SKSE::GetTaskInterface()) {
                tasks->AddTask([]() { HudReloadGuarded(); });
            }
        }
    } catch (...) {
    }
}

class MenuSink final : public RE::BSTEventSink<RE::MenuOpenCloseEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::MenuOpenCloseEvent* ev, RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override
    {
        if (!ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            OnMenuCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

MenuSink menuSink;

// ---------------------------------------------------------------- round 22: when a status runs out

// What an expiry settles (only effects with a stub script send the event; build/fix22_records.py KINDS).
// What the removal sink read (StatusEngine.h OnRemoved: the tag, the magnitude as it left, the crystals of the same
// frame) and whom it was on; the settle task plans from it.
struct Expiry {
    RE::ActorHandle actor{};
    essb::engine::Removed removed{};
};

void SettleCpp(const Expiry& expiry) noexcept
{
    try {
        TaskScope scope("settle task");   // round 26c (P5)
        if (!Enabled()) {   // master switch (review fix 3)
            return;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto actorPtr = expiry.actor.get();
        RE::Actor* actor = actorPtr.get();
        if (!player || !actor || actor->IsDead()) {
            return;
        }
        const auto nodes = MakeNodes(*player, FormIsActive());
        Context c = MakeContext(*player, false);
        const bool onPlayer = actor == player;
        RE::Actor* target = onPlayer ? nullptr : actor;
        essb::Board selfBoard = ReadBoard(*player);
        essb::Board targetBoard = target ? ReadBoard(*target) : essb::Board{};
        if (target) {
            c.in.body = ReadBody(*target, *player, TargetFactsOf(*target));
        }
        auto planPtr = std::make_unique<essb::StatusPlan>();
        essb::StatusPlan& plan = *planPtr;
        TraceCtx traceCtx("settle");   // round 26
        LogThreadOnce(Probe::kSettleTask, "settle task");
        NoteTaskThread();
        const bool tracing = TraceOn();
        if (tracing) {
            essb::trace::Line line("settle");
            line.Actor("on", FactsOf(actor));
            line.F(" tag=%s mag=%.2f elapsed=%.2f duration=%.2f crystals=%d", essb::trace::TagName(expiry.removed.tag).c_str(),
                expiry.removed.magnitude, expiry.removed.elapsed, expiry.removed.duration, expiry.removed.crystals);
            Emit(line);
            Rng().Record(true);
        }
        const essb::engine::Settled settled =
            essb::engine::PlanSettle(plan, expiry.removed, targetBoard, selfBoard, c.in, nodes, Rng());
        CrowdRead crowd;
        // 跳印：過期終焉照常結算，然後印記跳到 6 公尺內最近一個沒有印記的敵人（剩 4 秒、不開印、只跳一次）——
        // round 24: from the same crowd the end's bodies read (one scan per event).
        if (settled.jump && target) {
            const essb::Board planned = targetBoard;
            BuildCrowd(crowd, *player, target, &planned, kAroundEvent, kAroundEvent);
            const essb::Picked next = essb::Around(*crowd.crowd, 0, essb::n3::kJumpRadius, 1,
                [](const essb::Member& x) { return x.board.MarkCount() == 0; });
            if (next.n > 0) {
                const std::uint8_t at = next.k[0];
                essb::Writer{ plan, crowd.crowd->m[at].board, essb::Who::kTarget, at }.FlaggedMark(expiry.removed.tag.index,
                    essb::Scaled(c.tuning, essb::n3::kJumpSeconds), essb::n3::kMarkJumped);
            }
        }
        RunWithBodies(*player, target, target ? &targetBoard : nullptr, plan, 0, selfBoard, c, nodes, crowd);
        if (tracing) {
            TraceDraws("settle");
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in expiry task");
    }
}

void SettleGuarded(const Expiry& expiry) noexcept
{
    __try {
        SettleCpp(expiry);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in expiry task");
    }
}

// Round 26 (the probe log): every effect of ours that leaves an actor (reason expired / dispel / death, what was left of
// it), and every effect of ours the engine puts on one that the DLL did not cast (a hazard's marker, a Papyrus spell).
// Read-only, like the sink. The DLL's own dispels (a re-apply, a clear) are its op lines, not these.
bool CastByDll(const RE::MagicItem* spell) noexcept
{
    if (!spell) {
        return false;
    }
    if (SpellIdOf(spell) != 0) {
        return true;
    }
    for (const RE::SpellItem* proc : state.forms.procs) {
        if (proc == spell) {
            return true;
        }
    }
    return std::any_of(state.forms.spells.begin(), state.forms.spells.end(), [spell](const auto& row) { return row.second == spell; });
}

// An effect the engine put on an actor: the list is walked in a task, not inside the apply event (the event may come
// from inside the engine's own list update). Logging only: a failed read is logged, it never faults the DLL.
struct AppliedSeen {
    RE::ActorHandle actor{};
    std::uint16_t uid = 0;
};

void TraceAppliedCpp(const AppliedSeen& seen) noexcept
{
    try {
        TaskScope scope("apply trace task");   // round 26c (P5)
        auto held = seen.actor.get();
        RE::Actor* actor = held.get();
        if (!actor || !TraceOn()) {
            return;
        }
        auto* list = actor->AsMagicTarget()->GetActiveEffectList();
        if (!list) {
            return;
        }
        for (RE::ActiveEffect* effect : *list) {
            if (!effect || effect->usUniqueID != seen.uid) {
                continue;
            }
            RE::EffectSetting* base = effect->GetBaseObject();
            if (!base || base->GetFile(0) != state.forms.file || CastByDll(effect->spell)) {
                return;
            }
            auto casterPtr = effect->caster.get();
            auto* player = RE::PlayerCharacter::GetSingleton();
            essb::trace::Line line("apply");
            line.Actor("on", FactsOf(actor));
            line.F(" effect=0x%06X tag=%s spell=0x%06X mag=%.2f duration=%.2f", base->GetFormID() & 0xFFFFFFu,
                essb::trace::TagName(essb::TagOf(base->GetFormID() & 0xFFFFFFu)).c_str(), effect->spell ? (effect->spell->GetFormID() & 0xFFFFFFu) : 0u,
                effect->magnitude, effect->duration);
            line.Actor("caster", FactsOf(casterPtr.get()));
            if (player) {
                line.F(" d=%.0f", actor->GetPosition().GetDistance(player->GetPosition()));
            }
            Emit(line);
            return;
        }
    } catch (...) {
    }
}

void TraceAppliedGuarded(const AppliedSeen& seen) noexcept
{
    __try {
        TraceAppliedCpp(seen);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Log("[ESSB][T][trace] an applied effect could not be read (logging only; nothing else changes)");
    }
}

void TraceEffectEvent(const RE::TESActiveEffectApplyRemoveEvent& ev) noexcept
{
    try {
        auto* actor = ev.target ? ev.target->As<RE::Actor>() : nullptr;
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!actor || !player) {
            return;
        }
        if (!ev.isApplied) {
            // The same read the removal sink already makes (OnRemoved): the event arrives before the effect leaves the list.
            EffectLists lists(*player, actor);
            const essb::engine::Removed r = essb::engine::DescribeRemoved(lists, essb::Who::kTarget, ev.activeEffectUniqueID, actor->IsDead());
            if (r.reason == essb::engine::Removal::kIgnore) {
                return;
            }
            static constexpr const char* kReasons[] = { "ignore", "expired", "dispel", "death" };
            essb::trace::Line line("remove");
            essb::trace::RemoveLine(line, FactsOf(actor), r.tag, r.magnitude, r.elapsed, r.duration, kReasons[static_cast<int>(r.reason)]);
            Emit(line);
            return;
        }
        const AppliedSeen seen{ actor->GetHandle(), ev.activeEffectUniqueID };
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([seen]() { TraceAppliedGuarded(seen); });
        }
    } catch (...) {
    }
}

// The effect-removed event arrives inside Finish(), before the effect leaves the list (native-verification-3 s2), and
// often from the actor's own effect update loop: read only here, act in a main-thread task.
void OnRemoveCpp(const RE::TESActiveEffectApplyRemoveEvent& ev) noexcept
{
    try {
        if (!t_selfDispel && ev.target && TraceOn()) {
            TraceEffectEvent(ev);   // round 26
        }
        if (ev.isApplied || t_selfDispel || !Enabled() || !ev.target) {
            return;
        }
        auto* actor = ev.target->As<RE::Actor>();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!actor || !player) {
            return;
        }
        EffectLists lists(*player, actor);
        const bool dead = actor->IsDead();
        const essb::engine::Removed removed = essb::engine::OnRemoved(lists, essb::Who::kTarget, ev.activeEffectUniqueID, dead);
        if (removed.reason == essb::engine::Removal::kIgnore) {
            return;
        }
        LogThreadOnce(Probe::kRemove, "TESActiveEffectApplyRemoveEvent");
        if (state.forms.debug->value >= 3.0f) {  // probe N3-1: the three removal reasons, told apart
            static constexpr const char* kReasons[] = { "ignore", "expired", "dispel", "death" };
            Logf("[ESSB][N3-1][L3] tag=%d/%d found=1 elapsed=%.2f duration=%.2f magnitude=%.2f dead=%d crystals=%d -> %s",
                static_cast<int>(removed.tag.kind), removed.tag.index, removed.elapsed, removed.duration, removed.magnitude,
                dead ? 1 : 0, removed.crystals, kReasons[static_cast<int>(removed.reason)]);
        }
        if (removed.reason != essb::engine::Removal::kExpired) {
            return;
        }
        const Expiry expiry{ actor->GetHandle(), removed };
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([expiry]() { SettleGuarded(expiry); });
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the effect-removed sink");
    }
}

class RemoveSink final : public RE::BSTEventSink<RE::TESActiveEffectApplyRemoveEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESActiveEffectApplyRemoveEvent* ev,
        RE::BSTEventSource<RE::TESActiveEffectApplyRemoveEvent>*) override
    {
        if (!ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            OnRemoveCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in the effect-removed sink");
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

RemoveSink removeSink;

// ---------------------------------------------------------------- round 24: death (v0.4 2.6, 2.7, 5.x)

// TESDeathEvent dead = false is sent inside KillImpl while the corpse still carries every effect (native-verification-3
// s10): the sink reads the corpse (its board, its facts) and the killer, and the task plans from that snapshot -- the
// corpse's effects are dispelled on its next effect update, so they are not read again. dead = true (sent later, the
// effects may be gone) is not used. ESSB_Death and the Papyrus kill hooks are gone (ruling R4).
struct DeathSnapshot {
    RE::ActorHandle actor{};
    essb::Member corpse{};
    essb::DeathFacts facts{};
    // Round 26b: the killer as the event gave it (a reference, never read in the sink); the task resolves it.
    RE::NiPointer<RE::TESObjectREFR> killer{};
    bool dead = false;
    bool handled = false;            // DeathCounts: plan it (else the task only logs)
    essb::sink::DeathSeen seen{};
};

void DeathCpp(const DeathSnapshot& snapshot) noexcept
{
    try {
        TaskScope scope("death task");   // round 26c (P5)
        if (!Enabled()) {
            return;
        }
        TraceCtx traceCtx("death");   // round 26
        LogThreadOnce(Probe::kDeathTask, "death task");
        NoteTaskThread();
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto actorPtr = snapshot.actor.get();
        RE::Actor* corpse = actorPtr.get();
        if (!player || !corpse) {
            return;
        }
        // Round 26b: everything about the killer and the player is read here, in the task (the sink read the corpse only).
        RE::Actor* killer = snapshot.killer ? snapshot.killer->As<RE::Actor>() : nullptr;
        if (state.forms.debug->value >= 3.0f) {   // probe N5-1: both death events, the killer, our effects still on it
            Logf("[ESSB][N5-1][L3] %08X dead=%d killer=%08X you=%d ours=%d", corpse->GetFormID(), snapshot.dead ? 1 : 0,
                killer ? killer->GetFormID() : 0u, snapshot.seen.killerYou ? 1 : 0, snapshot.seen.ours);
        }
        if (TraceOn()) {   // round 26: both death events
            essb::trace::Line line("death-event");
            line.Actor("corpse", FactsOf(corpse));
            line.Actor("killer", FactsOf(killer));
            line.F(" dead=%d killerYou=%d servant=%d ours=%d", snapshot.dead ? 1 : 0, snapshot.seen.killerYou ? 1 : 0,
                snapshot.seen.servant ? 1 : 0, snapshot.seen.ours);
            Emit(line);
        }
        if (!snapshot.handled) {
            return;
        }
        essb::DeathFacts deathFacts = snapshot.facts;
        // 狂宴 (5.12; v0.4 10.3 P4): the killer is an NPC under your frenzy (our frenzy effect on it), not you.
        deathFacts.killerFrenzied = killer && killer != player && !killer->IsDead() &&
                                    HasOurEffect(*killer, Lookup(state.forms.status.effects, essb::status::kFrenzyEffect));
        const auto perks = MakeNodes(*player, FormIsActive());
        Context c = MakeContext(*player, false);
        essb::Board selfBoard = ReadBoard(*player);
        const auto nodes = essb::WithAvatar(perks, selfBoard);
        CrowdRead crowd;
        BuildCrowd(crowd, *player, corpse, &snapshot.corpse.board, kAroundEvent, kAroundEvent);
        essb::Member& m0 = crowd.crowd->m[0];
        const essb::Board board = snapshot.corpse.board;
        m0 = snapshot.corpse;   // the facts read in the sink (the position is the corpse's now)
        m0.board = board;
        m0.pos = PosOf(*corpse);
        m0.body.distanceToPlayer = corpse->GetPosition().GetDistance(player->GetPosition());   // round 26b: read here
        c.in.body = m0.body;
        const essb::BodyInputs bin = BodyInputsOf(*player, c, false);
        auto planPtr = std::make_unique<essb::StatusPlan>();
        essb::StatusPlan& plan = *planPtr;
        essb::DeathFacts facts = deathFacts;
        facts.curseCap = essb::CurseCap(c.tuning, nodes);
        const bool tracing = TraceOn();   // round 26
        if (tracing) {
            Rng().Record(true);
        }
        essb::PlanDeath(plan, *crowd.crowd, selfBoard, bin, facts, nodes, Rng());
        if (tracing) {
            essb::trace::Line line("death");
            line.Actor("corpse", FactsOf(corpse));
            line.Actor("killer", FactsOf(killer));
            line.F(" killerYou=%d frenzied=%d servant=%d marks=%d curse=%d poison=%d bleed=%d frozen=%d hush=%d essential=%d level=%d curseCap=%d crowd=%d ops=%d",
                facts.killerYou ? 1 : 0, facts.killerFrenzied ? 1 : 0, facts.servant ? 1 : 0, board.MarkCount(),
                board.Layers(essb::StatusKind::kCurse), board.poisonDot.has ? 1 : 0, board.bleedDot.has ? 1 : 0,
                board.Has(essb::StatusKind::kFrozen) ? 1 : 0, board.hush.has ? 1 : 0, m0.essential ? 1 : 0, m0.level, facts.curseCap,
                crowd.crowd->count, plan.count);
            Emit(line);
        }
        Executor(*player, corpse, c.tuning, &crowd.actors).Run(plan);
        if (tracing) {
            TraceDraws("death");
        }
        WriteMirrors(*player, selfBoard, nodes);
        if (state.forms.debug->value >= 1.0f) {   // probe N5-1: the corpse, the killer, what was on it
            Logf("[ESSB][death][L1] %08X killerYou=%d frenzied=%d servant=%d marks=%d curse=%d poison=%d frozen=%d crowd=%d ops=%d",
                corpse->GetFormID(), facts.killerYou ? 1 : 0, facts.killerFrenzied ? 1 : 0, facts.servant ? 1 : 0, board.MarkCount(),
                board.Layers(essb::StatusKind::kCurse), board.poisonDot.has ? 1 : 0, board.Has(essb::StatusKind::kFrozen) ? 1 : 0,
                crowd.crowd->count, plan.count);
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the death task");
    }
}

void DeathGuarded(const DeathSnapshot& snapshot) noexcept
{
    __try {
        DeathCpp(snapshot);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the death task");
    }
}

// Round 26b: the corpse's reads for essb::sink::DeathSink (the corpse only; the snapshot keeps the full member).
struct CorpseWorld {
    essb::Member* member;
    bool Servant(RE::Actor* corpse) { return HasOurEffect(*corpse, state.forms.reanimate); }
    int CountOurs(RE::Actor* corpse) { return CountOurEffects(*corpse); }
    const essb::Board& ReadCorpse(RE::Actor* corpse)
    {
        ReadMemberSelf(*member, *corpse, false);   // read-only, in the sink: the effects are all still there
        return member->board;
    }
};

// Round 26b (the commander's threading ruling): the sink reads the corpse only -- the killer and the player are compared
// by identity (Sinks.h DeathSink); the killer's frenzy, the player, the crowd, the logs and every write run in the task.
void OnDeathCpp(const RE::TESDeathEvent& ev) noexcept
{
    try {
        if (!Enabled() || !ev.actorDying) {   // master switch (review fix 3)
            return;
        }
        auto* actor = ev.actorDying->As<RE::Actor>();
        const void* player = RE::PlayerCharacter::GetSingleton();
        if (!actor || !player) {
            return;
        }
        LogThreadOnce(Probe::kDeath, "TESDeathEvent");
        DeathSnapshot snapshot;
        CorpseWorld world{ &snapshot.corpse };
        const bool logging = state.forms.debug->value >= 3.0f || TraceOn();
        snapshot.seen = essb::sink::DeathSink(world, actor, static_cast<const void*>(ev.actorKiller.get()), player, ev.dead, logging);
        if (snapshot.seen.dyingIsYou) {
            return;
        }
        snapshot.handled = snapshot.seen.snapshot;
        if (!snapshot.handled && !logging) {
            return;
        }
        snapshot.actor = actor->GetHandle();
        snapshot.killer = ev.actorKiller;
        snapshot.dead = ev.dead;
        snapshot.facts.killerYou = snapshot.seen.killerYou;
        snapshot.facts.servant = snapshot.seen.servant;
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([snapshot]() { DeathGuarded(snapshot); });
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the death sink");
    }
}

class DeathSink final : public RE::BSTEventSink<RE::TESDeathEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESDeathEvent* ev, RE::BSTEventSource<RE::TESDeathEvent>*) override
    {
        if (!ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            OnDeathCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in the death sink");
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

DeathSink deathSink;

// ---------------------------------------------------------------- round 22: the timer (ladder decay, fire source)

// Hostile, living, loaded actors within `radius` of the player, from the high process list (native-verification-3 s11:
// main thread only, handles collected first). Teammates and commanded actors never count.
std::vector<RE::ActorHandle> HostilesNear(RE::PlayerCharacter& player, float radius)
{
    std::vector<RE::ActorHandle> found;
    auto* lists = RE::ProcessLists::GetSingleton();
    if (!lists) {
        return found;
    }
    const RE::NiPoint3 centre = player.GetPosition();
    for (auto& handle : lists->highActorHandles) {
        auto actorPtr = handle.get();
        RE::Actor* actor = actorPtr.get();
        if (!actor || actor->IsDead() || !actor->Is3DLoaded() || actor->IsPlayerTeammate() || actor->IsCommandedActor()) {
            continue;
        }
        if (!actor->IsHostileToActor(&player)) {
            continue;
        }
        if (actor->GetPosition().GetDistance(centre) <= radius) {
            found.push_back(handle);
        }
    }
    return found;
}

// One second of white-hot (v0.4 5.3): burn every hostile within 3 m (熔燒 4.5 m) and give it the fire mark (no open),
// pay the 0.5% cost, auto-vent below 10% health, 火浴 and 熔身 per second.
template <class Nodes>
void FireSecond(RE::PlayerCharacter& player, essb::Board& selfBoard, Context& c, const Nodes& nodes, essb::StatusPlan& self)
{
    using K = essb::StatusKind;
    const int tier = essb::HeatTier(selfBoard);
    if (tier >= 3 && c.in.self.Fraction() < essb::n3::kAutoVent) {
        essb::OnFormLeave(self, essb::kFire, false, selfBoard, c.in, nodes);   // 自動洩壓（永遠先於過熱判定）
        return;
    }
    const essb::FireSource source = essb::PlanFireSource(selfBoard, c.in, nodes);
    if (source.active) {
        TraceCtx traceCtx("fire-source");   // round 26
        const auto hostiles = HostilesNear(player, source.radius);
        if (TraceOn()) {
            essb::trace::Line line("fire-source");
            line.F(" tier=%d radius=%.0f perEnemy=%.2f cost=%.2f hostiles=%d bath=%d", tier, source.radius, source.perEnemy, source.cost,
                static_cast<int>(hostiles.size()), nodes.Has(essb::node::kFireBath) ? 1 : 0);
            Emit(line);
        }
        for (const auto& handle : hostiles) {
            auto actorPtr = handle.get();
            RE::Actor* enemy = actorPtr.get();
            if (!enemy || enemy->IsDead()) {
                continue;
            }
            essb::Board enemyBoard = ReadBoard(*enemy);
            auto burnPtr = std::make_unique<essb::StatusPlan>();   // round 24: 28 KB, on the heap
            essb::StatusPlan& burn = *burnPtr;
            const float domain = enemyBoard.Has(essb::StatusKind::kDomainFire) ? essb::n3::kDomain : 1.0f;   // 火域：受火傷 +20%
            burn.Push(essb::Amount(essb::Op::kDamage, source.perEnemy * essb::ReactionVulnerability(enemyBoard, selfBoard, c.tuning, nodes) * domain, essb::kFire));
            // 火源掛的火印記不觸發開印，只讓目標成為爆燃與過熱的對象；它不切別的印記（沒有雙印位置就不掛）。
            const int others = enemyBoard.MarkCount() - (enemyBoard.mark[essb::kFire].has ? 1 : 0);
            if (others == 0 || (others < 2 && nodes.Has(essb::node::kCommonDualMark))) {
                essb::Writer{ burn, enemyBoard, essb::Who::kTarget }.Mark(essb::kFire, essb::rule::MarkSeconds(essb::kFire, c.tuning, nodes, false));
            }
            Executor(player, enemy, c.tuning).Run(burn);
        }
        if (source.cost > 0.0f && tier >= 3) {
            self.Push(essb::Amount(essb::Op::kPayHealth, source.cost));
        }
        // 火浴：白熱點燃當下依燒到的人數固定回血量，之後每秒 B_max ×0.1 × 該人數（人數不隨後續增減變動）。
        if (tier >= 3 && nodes.Has(essb::node::kFireBath)) {
            essb::PlanFireBath(self, selfBoard, static_cast<int>(hostiles.size()), kConfig.damage[essb::kFire][1], c.tuning);   // round 24: tested (reaction_test X)
        }
    }
    if (selfBoard.Has(K::kMoltenBody)) {
        self.Push(essb::Amount(essb::Op::kRestoreStamina, essb::n3::kMoltenStamina * c.tuning.multRecovery));
    }
}

// ---------------------------------------------------------------- round 25 (N6): the domains the engine holds

// The live domains (v0.4 2.9: 3 m, 5 s / 8 s; ruling R4: engine hazards, no limit of 3) within `radius` of you: each
// hazard of ours whose owner is you, found two ways (both read-only, main thread) -- the references of the loaded cells
// near you, and the Spawn Hazard effect on the actors of the high process list (its hazard handle; the effect lasts as
// long as the hazard, build/fix25_records.py). Counted once each. Probe N6-3 logs both counts.
struct DomainScan {
    std::vector<essb::DomainSite> sites;
    std::vector<const RE::TESObjectREFR*> seen;
    int fromCells = 0;
    int fromEffects = 0;
};

int DomainElementOf(const RE::BGSHazard* base) noexcept
{
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        if (base && state.forms.domainHazards[e] == base) {
            return e;
        }
    }
    return 0;
}

bool AddDomain(DomainScan& scan, RE::TESObjectREFR* ref, RE::PlayerCharacter& player, float radius)
{
    if (!ref || ref->GetFormType() != RE::FormType::PlacedHazard || ref->IsDisabled() || ref->IsDeleted()) {
        return false;
    }
    if (std::find(scan.seen.begin(), scan.seen.end(), ref) != scan.seen.end()) {
        return false;
    }
    auto* hazard = static_cast<RE::Hazard*>(ref);
    const auto& data = hazard->GetHazardRuntimeData();
    const int element = DomainElementOf(data.hazard);
    if (element == 0) {
        return false;
    }
    auto owner = data.ownerActor.get();
    if (owner.get() != &player || (data.lifetime > 0.0f && data.age >= data.lifetime)) {
        return false;
    }
    if (ref->GetPosition().GetDistance(player.GetPosition()) > radius) {
        return false;
    }
    scan.seen.push_back(ref);
    scan.sites.push_back(essb::DomainSite{ element, PosOfRef(*ref) });
    if (TraceOn()) {   // round 26
        essb::trace::Line line("domain");
        line.F(" el=%s ref=0x%08X age=%.1f lifetime=%.1f radius=%.2f magnitude=%.2f owner=you d=%.0f", essb::trace::ElementName(element),
            ref->GetFormID(), data.age, data.lifetime, data.radius, data.magnitude, ref->GetPosition().GetDistance(player.GetPosition()));
        Emit(line);
    }
    if (state.forms.debug->value >= 3.0f) {   // probe N6-3: every live domain the second found
        Logf("[ESSB][N6-3][L3] domain element=%d ref=%08X age=%.1f lifetime=%.1f radius=%.2f magnitude=%.2f owner=you d=%.0f", element,
            ref->GetFormID(), data.age, data.lifetime, data.radius, data.magnitude, ref->GetPosition().GetDistance(player.GetPosition()));
    }
    return true;
}

DomainScan ScanDomains(RE::PlayerCharacter& player, float radius)
{
    DomainScan scan;
    if (auto* tes = RE::TES::GetSingleton()) {
        tes->ForEachReferenceInRange(&player, radius, [&](RE::TESObjectREFR* ref) {
            if (ref && ref->GetFormType() == RE::FormType::PlacedHazard && AddDomain(scan, ref, player, radius)) {
                ++scan.fromCells;
            }
            return RE::BSContainer::ForEachResult::kContinue;
        });
    }
    if (auto* lists = RE::ProcessLists::GetSingleton()) {
        std::vector<RE::NiPointer<RE::TESObjectREFR>> hazards;
        for (auto& handle : lists->highActorHandles) {
            auto actorPtr = handle.get();
            RE::Actor* actor = actorPtr.get();
            if (!actor) {
                continue;
            }
            ForEachRunningEffect(*actor, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
                for (int e = essb::kFire; e <= essb::kAstral; ++e) {
                    if (state.forms.domainSpawn[e] == &base && base.GetArchetype() == RE::EffectSetting::Archetype::kSpawnHazard) {
                        if (auto ref = static_cast<RE::SpawnHazardEffect&>(effect).hazard.get()) {
                            hazards.push_back(ref);
                        }
                    }
                }
            });
        }
        for (auto& ref : hazards) {
            if (AddDomain(scan, ref.get(), player, radius)) {
                ++scan.fromEffects;
            }
        }
    }
    if (state.forms.debug->value >= 3.0f && !scan.sites.empty()) {
        Logf("[ESSB][N6-3][L3] domains=%d cells=%d effects=%d", static_cast<int>(scan.sites.size()), scan.fromCells, scan.fromEffects);
    }
    return scan;
}

essb::DomainSet InsideAt(const DomainScan& scan, const RE::NiPoint3& at)
{
    essb::DomainSet in{};
    for (const auto& site : scan.sites) {
        const RE::NiPoint3 p{ site.pos[0], site.pos[1], site.pos[2] };
        if (essb::IsElement(site.element) && p.GetDistance(at) <= essb::n6::kDomainRadius) {
            in[site.element] = true;
        }
    }
    return in;
}

// Per second, on every hostile within 50 m (round 22): 放血 (2.3: each bleed layer takes 0.3% of the target's CURRENT
// health, bosses 0.1%, +0.01% per point of 流血每層傷害, no G(L), no resist) and 瘟疫 / 瘴氣 (the doses merged into each
// neighbour's one poison); round 25 (N6): what a live domain does to it (Timer.h PlanDomainEnemy: 冰原 slow, 地裂 knock,
// 毒霧 +1 dose (R5), 潮池 one buff washed, 死域 dark damage).
template <class Nodes>
void TargetSecond(RE::PlayerCharacter& player, const essb::Board& selfBoard, Context& c, const Nodes& nodes, const DomainScan& domains)
{
    using K = essb::StatusKind;
    const float drainRate = essb::n3::kBleedDrain + essb::n3::kBleedDrainPerPoint * static_cast<float>(nodes.Rank(essb::node::kBloodLayerDamage));
    const auto hostiles = HostilesNear(player, 3500.0f);
    const float refund = nodes.Has(essb::node::kWaterPurgeTide) ? essb::n6::kPurgeTideRefund * kConfig.damage[essb::kWater][1] : 0.0f;
    // Gives `doses` to `to` through 2.7 擴散一劑 (the same rule as 淬毒's transfer and 濃毒): read, grow, re-apply.
    auto spread = [&](RE::Actor& to, float doses) {
        TraceCtx traceCtx("spread");   // round 26
        essb::Board toBoard = ReadBoard(to);
        Context tc = c;
        tc.in.body = ReadBody(to, player, TargetFactsOf(to));
        auto planPtr = std::make_unique<essb::StatusPlan>();   // round 24: 28 KB, on the heap
        essb::StatusPlan& plan = *planPtr;
        essb::rule::SpreadDoses(plan, toBoard, doses, tc.in, nodes);
        Executor(player, &to, c.tuning).Run(plan);
    };
    for (const auto& handle : hostiles) {
        auto actorPtr = handle.get();
        RE::Actor* enemy = actorPtr.get();
        if (!enemy || enemy->IsDead()) {
            continue;
        }
        essb::Board board = ReadBoard(*enemy);
        if (!domains.sites.empty()) {
            const essb::DomainSet inside = InsideAt(domains, enemy->GetPosition());
            if (std::any_of(inside.begin(), inside.end(), [](bool b) { return b; })) {
                TraceCtx traceCtx("domain-enemy");   // round 26
                if (TraceOn()) {
                    essb::trace::Line line("domain-enemy");
                    line.Actor("who", FactsOf(enemy));
                    line.F(" inside=");
                    bool first = true;
                    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
                        if (inside[e]) {
                            line.F("%s%s", first ? "" : ",", essb::trace::ElementName(e));
                            first = false;
                        }
                    }
                    Emit(line);
                }
                Context tc = c;
                tc.in.body = ReadBody(*enemy, player, TargetFactsOf(*enemy));
                auto planPtr = std::make_unique<essb::StatusPlan>();
                essb::StatusPlan& plan = *planPtr;
                essb::PlanDomainEnemy(plan, board, inside, tc.in, selfBoard, nodes, refund);
                Executor(player, enemy, c.tuning).Run(plan);
                board = ReadBoard(*enemy);   // the dose / the wash changed it
            }
        }
        const int layers = board.Layers(K::kBleed);
        if (layers > 0 && board.bleedDot.has) {
            const bool vip = TargetFactsOf(*enemy).vip;
            const float rate = vip ? drainRate * (essb::n3::kBleedDrainVip / essb::n3::kBleedDrain) : drainRate;
            const float health = enemy->AsActorValueOwner()->GetActorValue(RE::ActorValue::kHealth);
            auto drainPtr = std::make_unique<essb::StatusPlan>();   // round 24: 28 KB, on the heap
            essb::StatusPlan& drain = *drainPtr;
            TraceCtx traceCtx("bleed-drain");   // round 26
            drain.Push(essb::Amount(essb::Op::kBleedDrain, static_cast<float>(layers) * rate * health * c.tuning.multDot));
            Executor(player, enemy, c.tuning).Run(drain);
        }
        if (!board.poisonDot.has) {
            continue;
        }
        // 瘴氣 and 瘟疫 (commander ruling (b)+(d)): the DLL gives the doses itself, merged into each neighbour's one
        // poison -- no NPC-cast cloak (it hit the NPC's allies, took the kill credit and had a fixed strength).
        const float miasma = essb::rule::MiasmaDoses(board, c.in, nodes);
        const float plague = essb::rule::PlagueChance(board, c.tuning, nodes);
        const bool plagueNow = plague > 0.0f && Rng().Chance(plague);
        if (miasma <= 0.0f && !plagueNow) {
            continue;
        }
        const RE::NiPoint3 at = enemy->GetPosition();
        RE::Actor* nearest = nullptr;
        float best = essb::n3::kPlagueRadius;
        for (const auto& other : hostiles) {
            auto otherPtr = other.get();
            RE::Actor* candidate = otherPtr.get();
            if (!candidate || candidate == enemy || candidate->IsDead()) {
                continue;
            }
            const float d = candidate->GetPosition().GetDistance(at);
            if (miasma > 0.0f && d <= essb::n3::kMiasmaRadius) {
                if (TraceOn()) {   // round 26
                    essb::trace::Line line("spread");
                    line.F(" kind=miasma doses=%.3f d=%.0f", miasma, d);
                    line.Actor("from", FactsOf(enemy));
                    line.Actor("to", FactsOf(candidate));
                    Emit(line);
                }
                spread(*candidate, miasma);
            }
            if (d <= best) {
                best = d;
                nearest = candidate;
            }
        }
        if (plagueNow && nearest) {
            if (TraceOn()) {   // round 26
                essb::trace::Line line("spread");
                line.F(" kind=plague doses=1 chance=%.3f d=%.0f", plague, best);
                line.Actor("from", FactsOf(enemy));
                line.Actor("to", FactsOf(nearest));
                Emit(line);
            }
            spread(*nearest, 1.0f);
        }
    }
}

// Round 25 (N6): the silence takes the magicka to 0 every second while it lasts (it was ESSBSilence's OnUpdate; v0.4
// 5.1 沉默中無法施法、不回魔): anyone within 50 m carrying our silence effect.
void SilenceSecond(RE::PlayerCharacter& player)
{
    auto* lists = RE::ProcessLists::GetSingleton();
    if (!lists || !state.forms.silence) {
        return;
    }
    std::vector<RE::NiPointer<RE::Actor>> silenced;
    for (auto& handle : lists->highActorHandles) {
        auto ptr = handle.get();
        RE::Actor* actor = ptr.get();
        if (actor && !actor->IsDead() && actor->GetPosition().GetDistance(player.GetPosition()) <= 3500.0f &&
            HasOurEffect(*actor, state.forms.silence)) {
            silenced.push_back(ptr);
        }
    }
    for (auto& ptr : silenced) {
        DrainAllMagicka(*ptr);
        if (TraceOn()) {   // round 26
            essb::trace::Line line("silence");
            line.Actor("on", FactsOf(ptr.get()));
            Emit(line);
        }
    }
}

// Round 25 (N6): the allies 長河 reaches (v0.4 5.11「附近同伴」: teammates and your summons within 6 m, 5 at most, nearest
// first), as op members 1.. of `out` (out[0] stays null: the second's own ops are on you).
std::vector<essb::Ally> AlliesNear(RE::PlayerCharacter& player, std::vector<RE::Actor*>& out, std::vector<RE::NiPointer<RE::Actor>>& keep)
{
    std::vector<std::pair<float, RE::NiPointer<RE::Actor>>> found;
    if (auto* lists = RE::ProcessLists::GetSingleton()) {
        for (auto& handle : lists->highActorHandles) {
            auto ptr = handle.get();
            RE::Actor* actor = ptr.get();
            if (!actor || actor == &player || actor->IsDead() || !actor->Is3DLoaded() || !(actor->IsPlayerTeammate() || actor->IsCommandedActor())) {
                continue;
            }
            const float d = actor->GetPosition().GetDistance(player.GetPosition());
            if (d <= essb::n6::kRiverRadius) {
                found.push_back({ d, ptr });
            }
        }
    }
    std::sort(found.begin(), found.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    std::vector<essb::Ally> allies;
    out.assign(1, nullptr);
    for (auto& [d, ptr] : found) {
        if (static_cast<int>(allies.size()) >= essb::n6::kRiverAllies) {
            break;
        }
        RE::Actor* actor = ptr.get();
        allies.push_back(essb::Ally{ static_cast<int>(out.size()), MaxOf(*actor, RE::ActorValue::kHealth), MaxOf(*actor, RE::ActorValue::kStamina) });
        out.push_back(actor);
        keep.push_back(ptr);
    }
    return allies;
}

// Round 25 (N6): 1.1 維持費 / 魔力歸零 2 秒 / 血形態扣血, 5.11 長流 and 長河, 2.10 雷雨 -- Timer.h PlanFormSecond.
template <class Nodes>
essb::FormSecond FormSecondWork(RE::PlayerCharacter& player, essb::Board& selfBoard, Context& c, const Nodes& nodes, essb::StatusPlan& plan)
{
    essb::SecondFacts f;
    f.form = c.in.formElement;
    auto* v = player.AsActorValueOwner();
    f.magicka = v->GetActorValue(RE::ActorValue::kMagicka);
    f.magickaMax = MaxOf(player, RE::ActorValue::kMagicka);
    f.health = v->GetActorValue(RE::ActorValue::kHealth);
    f.healthMax = MaxOf(player, RE::ActorValue::kHealth);
    f.healthPermanent = v->GetPermanentActorValue(RE::ActorValue::kHealth);
    f.stamina = v->GetActorValue(RE::ActorValue::kStamina);
    f.staminaMax = MaxOf(player, RE::ActorValue::kStamina);
    f.thunder = state.forms.envThunder && state.forms.envThunder->value == 1.0f;   // 審查修正: 雷雨, not any rain or snow
    const essb::TimerTuning tt = essb::ReadTimerTuning(Global);
    std::vector<RE::Actor*> members;
    std::vector<RE::NiPointer<RE::Actor>> keep;
    std::array<essb::Ally, essb::n6::kRiverAllies> allies{};
    int allyCount = 0;
    if (f.form == essb::kWater && c.tuning.syncStage >= 3 && nodes.Rank(essb::node::kWaterLongRiver) > 0) {
        const auto reached = AlliesNear(player, members, keep);
        for (const auto& a : reached) {
            allies[allyCount++] = a;
        }
    }
    auto ownPtr = std::make_unique<essb::StatusPlan>();
    essb::StatusPlan& own = *ownPtr;
    TraceCtx traceCtx("form-second");   // round 26
    const essb::FormSecond out = essb::PlanFormSecond(own, selfBoard, f, c.in, tt, nodes, allies, allyCount);
    if (allyCount > 0) {
        Executor(player, nullptr, c.tuning, &members).Run(own);   // 長河's ops name their ally
    } else {
        for (int i = 0; i < own.count; ++i) {
            plan.Push(own.ops[i]);   // the rest joins the second's plan on you
        }
    }
    if (state.forms.debug->value >= 2.0f && (out.spent > 0.0f || out.bled > 0.0f || out.flow > 0.0f || out.closing || out.charged)) {
        Logf("[ESSB][second][L2] form=%d spent=%.2f bled=%.2f flow=%.4f allies=%d close=%d storm=%d", f.form, out.spent, out.bled, out.flow,
            allyCount, out.closing ? 1 : 0, out.charged ? 1 : 0);
    }
    return out;
}

// Round 25 (N6): the environment every 5 s (v0.4 2.10, was ESSBController.EnvCheck): the weather's classification, an
// interior cell, swimming / under water, the game hour -> ESSB_EnvWet / EnvStormy / EnvThunder / EnvNight (the DLL is
// their writer). 審查修正: 暴風雪 = snow with the weather's wind speed at half or more, 雷雨 = rain with a lightning
// frequency (255 = none), from the weather record's DATA.
void EnvironmentCheck(RE::PlayerCharacter& player)
{
    essb::EnvFacts facts;
    if (auto* sky = RE::Sky::GetSingleton(); sky && sky->currentWeather) {
        const auto& data = sky->currentWeather->data;
        facts.weather = essb::WeatherClass(static_cast<std::uint8_t>(data.flags.underlying()));
        facts.lightning = static_cast<std::uint8_t>(data.thunderLightningFrequency);
        facts.wind = data.windSpeed;
    }
    const auto* cell = player.GetParentCell();
    facts.interior = cell && cell->IsInteriorCell();
    const auto* actorState = player.AsActorState();
    facts.swimming = actorState && actorState->IsSwimming();
    // PO3 IsRefUnderwater's test (the reference's position more than 87.5% under the water level).
    const RE::TESObjectREFR& ref = player;
    facts.underwater = ref.IsPointSubmergedMoreThan(player.GetPosition(), player.GetParentCell(), 0.875f);
    if (auto* calendar = RE::Calendar::GetSingleton()) {
        facts.hour = calendar->GetHour();
    }
    const essb::EnvFlags e = essb::Environment(facts);
    const auto& f = state.forms;
    const bool changed = (f.envWet && f.envWet->value != (e.wet ? 1.0f : 0.0f)) || (f.envStormy && f.envStormy->value != (e.stormy ? 1.0f : 0.0f)) ||
                         (f.envThunder && f.envThunder->value != (e.thunder ? 1.0f : 0.0f)) ||
                         (f.envNight && f.envNight->value != (e.night ? 1.0f : 0.0f));
    SetMirror(f.envWet, e.wet ? 1.0f : 0.0f);
    SetMirror(f.envStormy, e.stormy ? 1.0f : 0.0f);
    SetMirror(f.envThunder, e.thunder ? 1.0f : 0.0f);
    SetMirror(f.envNight, e.night ? 1.0f : 0.0f);
    if (TraceOn()) {   // round 26: every check (every 5 s), changed or not
        essb::trace::Line line("env");
        essb::trace::EnvLine(line, e, facts, changed);
        if (auto* sky = RE::Sky::GetSingleton(); sky && sky->currentWeather) {
            line.F(" weather=0x%08X", sky->currentWeather->GetFormID());
        }
        Emit(line);
    }
    if (changed && f.debug->value >= 1.0f) {   // v0.4 6.1: 環境加成切換
        Logf("[ESSB][env][L1] wet=%d stormy=%d thunder=%d night=%d classification=%d lightning=%d wind=%d hour=%.2f interior=%d swimming=%d "
             "underwater=%d",
            e.wet ? 1 : 0, e.stormy ? 1 : 0, e.thunder ? 1 : 0, e.night ? 1 : 0, facts.weather, static_cast<int>(facts.lightning),
            static_cast<int>(facts.wind), facts.hour, facts.interior ? 1 : 0, facts.swimming ? 1 : 0, facts.underwater ? 1 : 0);
    }
}

// Round 25 (N6): 冰原「你在其中免疫減速」, 定神, 御風 -- every tick, while immune, your slows are dispelled (Timer.h IsSlow:
// a timed, detrimental modifier on SpeedMult). Collected first, dispelled after the walk.
template <class Nodes>
void SlowImmunity(RE::PlayerCharacter& player, const essb::Board& me, const essb::Tuning& t, const Nodes& nodes)
{
    if (!essb::SlowImmune(me, t, nodes)) {
        return;
    }
    // round 26c (P2): collected by id, re-found before each dispel
    const int dispelled = DispelLive(player, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
        essb::SlowView v;
        v.archetype = static_cast<int>(base.GetArchetype());
        v.primaryAV = static_cast<int>(base.data.primaryAV);
        v.secondaryAV = static_cast<int>(base.data.secondaryAV);
        v.detrimental = base.IsDetrimental();
        v.duration = effect.duration;
        return essb::IsSlow(v);
    });
    if (dispelled > 0 && state.forms.debug->value >= 2.0f) {
        Logf("[ESSB][slow][L2] immune: %d slow(s) dispelled", dispelled);
    }
    if (dispelled > 0 && TraceOn()) {   // round 26
        essb::trace::Line line("slow-immune");
        line.F(" dispelled=%d", dispelled);
        Emit(line);
    }
}

// 1.1 風形態 / 5.7 疾風: while you sprint in the wind form, stamina comes back at 20% of the sprint drain (疾風 50%), the
// drain being the engine's own formula (native-verification-2 s14: fSprintStaminaDrainMult × (fSprintStaminaWeightBase +
// fSprintStaminaWeightMult × equipped weight) a second). Refunded, not reduced: 0 stamina still stops the sprint.
float GameSetting(const char* name, float fallback)
{
    auto* settings = RE::GameSettingCollection::GetSingleton();
    auto* setting = settings ? settings->GetSetting(name) : nullptr;
    return setting ? setting->GetFloat() : fallback;
}

// Round 25: `seconds` is the game-running time of this timer step (Timer.h Step), so a pause refunds nothing.
template <class Nodes>
void WindSprint(RE::PlayerCharacter& player, const Context& c, const Nodes& nodes, float seconds)
{
    if (seconds <= 0.0f || c.in.formElement != essb::kWind) {
        return;
    }
    const auto* actorState = player.AsActorState();
    if (!actorState || !actorState->IsSprinting()) {
        return;
    }
    seconds = (std::min)(seconds, 0.5f);
    const float drain = GameSetting("fSprintStaminaDrainMult", 7.0f) *
                        (GameSetting("fSprintStaminaWeightBase", 1.0f) + GameSetting("fSprintStaminaWeightMult", 0.02f) * player.GetEquippedWeight());
    const float share = nodes.Has(essb::node::kWindGale) ? 0.5f : 0.2f;
    const float back = share * drain * seconds * c.tuning.multRecovery;
    if (back > 0.0f) {
        player.AsActorValueOwner()->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kStamina, back);
    }
}

// Probe N4-2 (native-verification-3 s18; debug level 3): the last actor you hit, its two casters' state / castingTimer /
// currentSpell, one line whenever a caster's state changes (the timer runs every 100 ms), and whether IsCasting (the
// 法術麻痺 / 斷咒 test) calls that casting.
void ProbeCasting()
{
    if (state.forms.debug->value < 3.0f) {
        return;
    }
    auto ptr = state.probeTarget.get();
    RE::Actor* actor = ptr.get();
    if (!actor || actor->IsDead()) {
        return;
    }
    const auto& casters = actor->GetActorRuntimeData().magicCasters;
    for (int i = 0; i < 2; ++i) {
        const RE::ActorMagicCaster* caster = casters[i];
        const int s = caster ? static_cast<int>(caster->state.get()) : -1;
        if (s == state.probeCaster[i]) {
            continue;
        }
        state.probeCaster[i] = s;
        Logf("[ESSB][N4-2][L3] target=%08X caster=%d state=%d castingTimer=%.2f spell=%08X casting=%d magicka=%.1f",
            actor->GetFormID(), i, s, caster ? caster->castingTimer : 0.0f,
            caster && caster->currentSpell ? caster->currentSpell->GetFormID() : 0u, IsCasting(*actor) ? 1 : 0,
            actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka));
        if (TraceOn()) {   // round 26
            essb::trace::Line line("casting");
            line.Actor("who", FactsOf(actor));
            line.F(" caster=%d state=%d castingTimer=%.2f spell=0x%08X casting=%d", i, s, caster ? caster->castingTimer : 0.0f,
                caster && caster->currentSpell ? caster->currentSpell->GetFormID() : 0u, IsCasting(*actor) ? 1 : 0);
            Emit(line);
        }
    }
}

// ---------------------------------------------------------------- round 26: the probe log's watchers (logging only)

void MarkStep(int station, const char* via) noexcept
{
    try {
        bool now = false;
        state.trace.Step(station, state.runningMs.load(), RealMs(), via, now);
        if (now) {
            FlushTrace();
        }
        const std::string text = "探針站 " + std::to_string(station);
        RE::DebugNotification(text.c_str());
    } catch (...) {
    }
}

// numpad + / numpad -: the next / the previous probe station (ESSB_ProbeStep; the console's `set ESSB_ProbeStep to N`
// jumps). Main thread (the input sink).
void StepKey(int delta)
{
    auto* g = state.forms.probeStep;
    if (!g) {
        return;
    }
    const int now = (std::max)(0, static_cast<int>(g->value + 0.5f));
    const int next = (std::max)(1, now + delta);
    g->value = static_cast<float>(next);
    state.stepSeen = g->value;
    MarkStep(next, delta > 0 ? "key" : "key-back");
}

std::string_view GlobalName(std::uint32_t id)
{
    for (const auto& [gid, name] : state.globalNames) {
        if (gid == id) {
            return name;
        }
    }
    return "?";
}

// Every global the DLL reads (the MCM's sliders and toggles among them, and the console's `set`): a line per change; all
// of them once when the probe log turns on or a game loads.
void WatchGlobals()
{
    const auto& g = state.forms.globals;
    const bool dump = state.globalSeen.size() != g.size();
    if (dump) {
        state.globalSeen.assign(g.size(), 0.0f);
    }
    essb::trace::Line all("mcm-state");
    int inLine = 0;
    for (std::size_t i = 0; i < g.size(); ++i) {
        if (!g[i].second) {
            continue;
        }
        const float v = g[i].second->value;
        const std::string_view name = GlobalName(g[i].first);
        if (dump) {
            all.F(" %.*s=%.3f", static_cast<int>(name.size()), name.data(), v);
            if (++inLine == 12) {
                Emit(all);
                all = essb::trace::Line("mcm-state");
                inLine = 0;
            }
        } else if (v != state.globalSeen[i]) {
            essb::trace::Line line("mcm");
            line.F(" global=%.*s old=%.3f new=%.3f", static_cast<int>(name.size()), name.data(), state.globalSeen[i], v);
            Emit(line);
        }
        state.globalSeen[i] = v;
    }
    if (dump && inLine > 0) {
        Emit(all);
    }
}

// The perks the DLL reads (main-line ranks and branch slots, by local FormID -- the id `player.addperk XX……` names):
// once a real second, a line per perk gained or lost; the whole set when the probe log turns on or a game loads.
void WatchPerks(RE::PlayerCharacter& player)
{
    std::vector<std::uint32_t> owned;
    const auto& main = state.forms.mainPerks;
    const auto& branch = state.forms.branchPerks;
    for (std::size_t i = 0; i < main.size(); ++i) {
        if (main[i] && player.HasPerk(main[i])) {
            owned.push_back(essb::kMainPerkBase + static_cast<std::uint32_t>(i));
        }
    }
    for (std::size_t i = 0; i < branch.size(); ++i) {
        if (branch[i] && player.HasPerk(branch[i])) {
            owned.push_back(essb::kBranchPerkBase + static_cast<std::uint32_t>(i));
        }
    }
    std::sort(owned.begin(), owned.end());
    auto perkOf = [&](std::uint32_t id) -> RE::BGSPerk* {
        return id >= essb::kMainPerkBase && id - essb::kMainPerkBase < main.size() ? main[id - essb::kMainPerkBase]
                                                                                   : branch[id - essb::kBranchPerkBase];
    };
    if (!state.perksRead) {
        state.perksRead = true;
        essb::trace::Line line("node-state");
        line.F(" count=%d ids=", static_cast<int>(owned.size()));
        for (std::size_t i = 0; i < owned.size(); ++i) {
            line.F("%s%06X", i ? "," : "", owned[i]);
        }
        Emit(line);
    } else {
        for (const std::uint32_t id : owned) {
            if (!std::binary_search(state.perksSeen.begin(), state.perksSeen.end(), id)) {
                RE::BGSPerk* perk = perkOf(id);
                essb::trace::Line line("node");
                line.F(" change=+ id=%06X name=%s", id, perk && perk->GetName() ? perk->GetName() : "?");
                Emit(line);
            }
        }
        for (const std::uint32_t id : state.perksSeen) {
            if (!std::binary_search(owned.begin(), owned.end(), id)) {
                RE::BGSPerk* perk = perkOf(id);
                essb::trace::Line line("node");
                line.F(" change=- id=%06X name=%s", id, perk && perk->GetName() ? perk->GetName() : "?");
                Emit(line);
            }
        }
    }
    state.perksSeen = std::move(owned);   // sorted above
}

// Every timer tick, before the master switch (its own change is logged too): the level turning on or off, the globals,
// the step marker set from the console, and once a real second the perks.
void ProbeWatch(RE::PlayerCharacter& player)
{
    const bool on = TraceOn();
    if (!on) {
        if (state.traceWasOn) {
            state.traceWasOn = false;
            FlushTrace();
        }
        return;
    }
    if (!state.traceWasOn) {
        state.traceWasOn = true;
        state.globalSeen.clear();
        state.perksRead = false;
        state.stepSeen = -1.0f;
        state.secondRead = false;
        essb::trace::Line line("trace");
        line.F(" on level=%.0f dll=%s buffer=1s maxLine=%d", state.forms.debug->value, essb::nativeVersion, static_cast<int>(essb::trace::kMaxLine));
        Emit(line);
    }
    WatchGlobals();
    if (auto* step = state.forms.probeStep) {
        if (state.stepSeen < 0.0f) {
            state.stepSeen = step->value;   // what the save (or the last session) left: not a new station
        } else if (step->value != state.stepSeen) {
            state.stepSeen = step->value;
            MarkStep(static_cast<int>(step->value + 0.5f), "console");
        }
    }
    const std::uint64_t now = GetTickCount64();
    if (now - state.lastPerkScan >= 1000) {
        state.lastPerkScan = now;
        WatchPerks(player);
    }
}

// The live domains this second: the ones that appeared and went, who stands in each (every actor near, not only the
// hostiles the rules act on), and whether you do.
void TraceDomains(RE::PlayerCharacter& player, const DomainScan& scan, const essb::DomainSet& you)
{
    std::vector<std::uint32_t> ids;
    for (std::size_t i = 0; i < scan.seen.size(); ++i) {
        ids.push_back(scan.seen[i]->GetFormID());
    }
    std::sort(ids.begin(), ids.end());
    for (std::size_t i = 0; i < scan.seen.size(); ++i) {
        const std::uint32_t id = scan.seen[i]->GetFormID();
        if (!std::binary_search(state.domainsSeen.begin(), state.domainsSeen.end(), id)) {
            essb::trace::Line line("domain-new");
            line.F(" ref=0x%08X el=%s", id, essb::trace::ElementName(scan.sites[i].element));
            Emit(line);
        }
    }
    for (const std::uint32_t id : state.domainsSeen) {
        if (!std::binary_search(ids.begin(), ids.end(), id)) {
            essb::trace::Line line("domain-gone");
            line.F(" ref=0x%08X", id);
            Emit(line);
        }
    }
    state.domainsSeen = ids;
    if (auto* lists = RE::ProcessLists::GetSingleton(); lists && !scan.sites.empty()) {
        for (auto& handle : lists->highActorHandles) {
            auto ptr = handle.get();
            RE::Actor* actor = ptr.get();
            if (!actor || actor == &player) {
                continue;
            }
            for (std::size_t i = 0; i < scan.sites.size(); ++i) {
                const RE::NiPoint3 at{ scan.sites[i].pos[0], scan.sites[i].pos[1], scan.sites[i].pos[2] };
                const float d = actor->GetPosition().GetDistance(at);
                if (d <= essb::n6::kDomainRadius) {
                    essb::trace::Line line("domain-in");
                    line.F(" ref=0x%08X el=%s d=%.0f", scan.seen[i]->GetFormID(), essb::trace::ElementName(scan.sites[i].element), d);
                    line.Actor("who", FactsOf(actor));
                    line.F(" hostile=%d teammate=%d commanded=%d", actor->IsHostileToActor(&player) ? 1 : 0, actor->IsPlayerTeammate() ? 1 : 0,
                        actor->IsCommandedActor() ? 1 : 0);
                    Emit(line);
                }
            }
        }
    }
    if (std::any_of(you.begin(), you.end(), [](bool b) { return b; })) {
        essb::trace::Line line("domain-you");
        line.F(" inside=");
        bool first = true;
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            if (you[e]) {
                line.F("%s%s", first ? "" : ",", essb::trace::ElementName(e));
                first = false;
            }
        }
        line.Actor("you", FactsOf(&player));
        Emit(line);
    }
}

// Once a game-running second: the form's upkeep / blood cost / 長流 and how your health, magicka and stamina moved since
// the last second (dH dM dS: everything together -- the upkeep, regeneration, hits). While a form is open, or when the
// second did anything.
void TraceSecond(RE::PlayerCharacter& player, const essb::FormSecond& fs, int form)
{
    auto* v = player.AsActorValueOwner();
    const std::array<float, 3> now{ v->GetActorValue(RE::ActorValue::kHealth), v->GetActorValue(RE::ActorValue::kMagicka),
        v->GetActorValue(RE::ActorValue::kStamina) };
    const bool read = state.secondRead;
    const std::array<float, 3> was = state.secondSeen;
    state.secondSeen = now;
    state.secondRead = true;
    if (form == 0 && fs.spent <= 0.0f && fs.bled <= 0.0f && fs.flow <= 0.0f && !fs.closing && !fs.charged) {
        return;
    }
    essb::trace::Line line("second");
    essb::trace::SecondLine(line, form, fs, read, now[0] - was[0], now[1] - was[1], now[2] - was[2], FactsOf(&player));
    Emit(line);
}

// Round 25 (N6, probe N6-1): the game does not run -- paused (Esc, the inventory, the console, Alt+Tab with the game
// paused), loading, or between a load's start and its end. The timer counts none of that.
bool GameStopped(RE::UI* ui)
{
    if (!state.inGame) {
        return true;
    }
    return ui && (ui->GameIsPaused() || ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME));
}

void TickCpp() noexcept
{
    try {
        TaskScope scope("timer task");   // round 26c (P5)
        // Round 26: the probe log's watchers run before the master switch (turning it off is logged too).
        if (auto* watched = RE::PlayerCharacter::GetSingleton(); watched && Active()) {
            ProbeWatch(*watched);
        }
        // The master switch (ESSB_Enabled) stops the per-second work too, not only hits (round 22: the old ghost
        // statuses ignored it).
        if (!Enabled()) {
            return;
        }
        auto* ui = RE::UI::GetSingleton();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) {
            return;
        }
        TraceCtx traceCtx("tick");   // round 26
        const bool stopped = GameStopped(ui);
        const essb::Beat beat = essb::Step(state.cadence, GetTickCount64(), stopped);
        state.runningMs.fetch_add(static_cast<std::uint64_t>(std::llround(beat.seconds * 1000.0f)));   // 0 while stopped
        if (stopped) {
            if (state.forms.debug->value >= 3.0f && !state.stoppedLogged) {   // probe N6-1: the clock stops
                state.stoppedLogged = true;
                Logf("[ESSB][N6-1][L3] stopped active=%llu ms", static_cast<unsigned long long>(state.cadence.active));
                if (TraceOn()) {   // round 26
                    essb::trace::Line line("tick");
                    line.F(" state=stopped active=%llu paused=%d loading=%d", static_cast<unsigned long long>(state.cadence.active),
                        ui && ui->GameIsPaused() ? 1 : 0, ui && ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME) ? 1 : 0);
                    Emit(line);
                }
            }
            return;
        }
        if (state.stoppedLogged) {
            state.stoppedLogged = false;
            if (state.forms.debug->value >= 3.0f) {
                Logf("[ESSB][N6-1][L3] running again active=%llu ms", static_cast<unsigned long long>(state.cadence.active));
            }
            if (TraceOn()) {   // round 26
                essb::trace::Line line("tick");
                line.F(" state=running active=%llu", static_cast<unsigned long long>(state.cadence.active));
                Emit(line);
            }
        }
        LogThreadOnce(Probe::kTick, "timer task");
        NoteTaskThread();   // round 26: the X1 lines compare the sinks with the latest task's thread
        if (beat.env) {
            EnvironmentCheck(*player);   // round 25: before the second, so the storm's charge reads this check
        }
        const auto perks = MakeNodes(*player, FormIsActive());
        Context c = MakeContext(*player, false);
        essb::Board selfBoard = ReadBoard(*player);
        const auto nodes = essb::WithAvatar(perks, selfBoard);   // round 23: 化身 (業火、瘟疫 read here)
        auto planPtr = std::make_unique<essb::StatusPlan>();   // round 24: 28 KB, on the heap
        essb::StatusPlan& plan = *planPtr;
        essb::PlanDecay(plan, selfBoard, c.in, nodes);
        essb::FormSecond second{};   // round 26: the probe log's second line reads it
        if (beat.second) {
            // 審查修正: no domain node, no hazard of yours -- skip the 60 m cell walk (read each second, nothing cached).
            const DomainScan domains = essb::HasDomainNode(nodes) ? ScanDomains(*player, essb::n6::kDomainScan) : DomainScan{};
            FireSecond(*player, selfBoard, c, nodes, plan);
            TargetSecond(*player, selfBoard, c, nodes, domains);
            SilenceSecond(*player);
            essb::PlanSelfSecond(plan, selfBoard, c.player.magickaMax, c.in, nodes);   // round 23: 超載 decays
            second = FormSecondWork(*player, selfBoard, c, nodes, plan);                // round 25: 維持費, 長流, 雷雨
            const essb::DomainSet inside = InsideAt(domains, player->GetPosition());
            if (TraceOn()) {
                TraceDomains(*player, domains, inside);   // round 26
            }
            const essb::DomainSelf self = essb::PlanDomainSelf(plan, selfBoard, inside, c.in, nodes);
            if (state.forms.debug->value >= 2.0f && (self.fuseExtended || std::any_of(inside.begin(), inside.end(), [](bool b) { return b; }))) {
                Logf("[ESSB][domain][L2] you in: fire=%d frost=%d blood=%d divine=%d water=%d fuse+5=%d", inside[essb::kFire] ? 1 : 0,
                    inside[essb::kFrost] ? 1 : 0, inside[essb::kBlood] ? 1 : 0, inside[essb::kDivine] ? 1 : 0, inside[essb::kWater] ? 1 : 0,
                    self.fuseExtended ? 1 : 0);
            }
        }
        SlowImmunity(*player, selfBoard, c.tuning, nodes);   // round 25: 冰原 / 定神 / 御風, every tick
        WindSprint(*player, c, nodes, beat.seconds);
        ProbeCasting();
        Executor(*player, nullptr, c.tuning).Run(plan);
        if (beat.second && TraceOn()) {
            TraceSecond(*player, second, c.in.formElement);   // round 26
        }
        WriteMirrors(*player, selfBoard, nodes);   // an effect that ran out takes its mirror to 0
        essb::hud::Tick(!state.forms.trueHudBars || state.forms.trueHudBars->value == 1.0f);   // round 26c (T2): the MCM switch
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the timer task");
    }
}

void TickGuarded() noexcept
{
    __try {
        TickCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the timer task");
    }
    state.tickQueued = false;
}

// Background timer: wakes every 100 ms and posts ONE main-thread task, never a second while the first is pending
// (native-verification-3 s12: a task that re-queues itself would spin forever inside the same frame).
// Round 26 (threading witness, logging only): once a second one SKSE UI task notes the thread UI::ProcessMessages runs
// on, so the X1 lines show whether AddUITask would be a main-thread drain point. It does nothing else.
void UiWitnessGuarded() noexcept
{
    __try {
        LogThreadOnce(Probe::kUiTask, "SKSE UI task");
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
    state.uiWitnessQueued = false;
}

void TimerLoop() noexcept
{
    while (!state.stopTimer) {
        std::this_thread::sleep_for(kTickInterval);
        if (GetTickCount64() - state.lastFlush.load() >= 1000) {
            FlushTrace();   // round 26: the probe log reaches the file once a second (paused or not)
            if (state.ready && !state.faulted && state.inGame && !state.uiWitnessQueued.exchange(true)) {
                try {
                    if (const auto* tasks = SKSE::GetTaskInterface()) {
                        tasks->AddUITask([]() { UiWitnessGuarded(); });
                    } else {
                        state.uiWitnessQueued = false;
                    }
                } catch (...) {
                    state.uiWitnessQueued = false;
                }
            }
        }
        if (state.faulted || !state.ready || !state.inGame) {
            continue;
        }
        const auto* tasks = SKSE::GetTaskInterface();
        if (!tasks || state.tickQueued.exchange(true)) {
            continue;
        }
        try {
            tasks->AddTask([]() { TickGuarded(); });
        } catch (...) {
            state.tickQueued = false;
        }
    }
}

// Round 26c (P7): the timer thread is stopped (and waited for, briefly) before the statics it reads are destroyed. At
// process exit the thread is already gone and the wait returns at once; it never blocks the loader for long.
std::thread timerThread;

struct TimerStopper {
    ~TimerStopper()
    {
        state.stopTimer = true;
        if (timerThread.joinable()) {
            WaitForSingleObject(static_cast<HANDLE>(timerThread.native_handle()), 1000);
            timerThread.detach();
        }
    }
} timerStopper;

// ---------------------------------------------------------------- round 25 (N6): hotkeys (ruling R6)

// The switch both routes share (v0.4 1.1: 熱鍵與 Z 路線呼叫同一個切換函式): the hotkey sink and ESSBNative.RequestSwitch
// (the form powers). Main thread. Timer.h PlanSwitch decides; the DLL writes ESSB_CurrentElement / ESSB_FormActive first
// (the next hit already uses the new element), shows the one-line notice, then ESSB_Switch tells Papyrus to change the
// form (abilities, sync keep, the burst on a close: v0.4 1.1 形態開關 Papyrus).
void RequestSwitch(int element, const char* via)
{
    auto* player = RE::PlayerCharacter::GetSingleton();
    auto& f = state.forms;
    if (!player) {
        return;
    }
    essb::SwitchFacts facts;
    facts.enabled = f.enabled && f.enabled->value == 1.0f;
    facts.dead = player->IsDead();
    facts.active = f.formActive->value == 1.0f;
    facts.current = static_cast<int>(f.element->value);
    facts.magicka = player->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka);
    facts.magickaMax = MaxOf(*player, RE::ActorValue::kMagicka);
    facts.freePass = MakeNodes(*player, facts.active).Has(essb::node::kCommonSmoothSwitch);
    facts.freeOpen = f.freeOpen && f.freeOpen->value > 0.0f;
    const essb::SwitchPlan p = essb::PlanSwitch(facts, element);
    if (TraceOn()) {   // round 26
        essb::trace::Line line("switch");
        essb::trace::SwitchLine(line, via, element, p, facts, FactsOf(player));
        Emit(line);
    }
    if (f.debug->value >= 1.0f) {
        Logf("[ESSB][switch][L1] via=%s wanted=%d kind=%d element=%d active=%d current=%d", via, element, static_cast<int>(p.kind), p.element,
            facts.active ? 1 : 0, facts.current);
    }
    switch (p.kind) {
    case essb::SwitchKind::kIgnore:
        return;
    case essb::SwitchKind::kRefuse:
        RE::DebugNotification("魔力不足，無法開啟形態");
        return;
    case essb::SwitchKind::kClose:
        f.formActive->value = 0.0f;
        f.element->value = 0.0f;
        break;
    case essb::SwitchKind::kOpen:
    case essb::SwitchKind::kSwitch:
        f.element->value = static_cast<float>(p.element);
        f.formActive->value = 1.0f;
        break;
    }
    if (p.consumeFree && f.freeOpen) {
        f.freeOpen->value = 0.0f;
    }
    if (f.formNotify && f.formNotify->value == 1.0f) {
        const std::string text = p.kind == essb::SwitchKind::kClose ? std::string("元素魔戰士：關閉形態")
                                                                     : std::string("元素魔戰士：") + essb::kFormLabels[p.element];
        RE::DebugNotification(text.c_str());
    }
    SendEvent(essb::MakeEvent(essb::Event::kSwitch, static_cast<float>(element), p.kind == essb::SwitchKind::kOpen ? 1.0f : 0.0f), player);
}

// Probe N6-2: whether input reaches gameplay now (Timer.h InputOpen). A menu that pauses, uses the cursor or the menu
// input context, or is modal blocks it (Papyrus Utility.IsInMenuMode); so do the console and a text box.
essb::InputGate GateNow()
{
    essb::InputGate g;
    g.loading = !state.inGame;
    auto* ui = RE::UI::GetSingleton();
    if (ui) {
        g.paused = ui->GameIsPaused();
        g.console = ui->IsMenuOpen(RE::Console::MENU_NAME);
        g.loading = g.loading || ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME);
        using Flag = RE::UI_MENU_FLAGS;
        for (const auto& menu : ui->menuStack) {
            if (menu && menu->menuFlags.any(Flag::kPausesGame, Flag::kUsesCursor, Flag::kUsesMenuContext, Flag::kModal)) {
                g.menu = true;
                break;
            }
        }
    }
    if (auto* controls = RE::ControlMap::GetSingleton()) {
        g.textEntry = controls->textEntryCount > 0;
    }
    return g;
}

essb::Device DeviceOf(RE::INPUT_DEVICE device) noexcept
{
    switch (device) {
    case RE::INPUT_DEVICE::kKeyboard: return essb::Device::kKeyboard;
    case RE::INPUT_DEVICE::kMouse: return essb::Device::kMouse;
    case RE::INPUT_DEVICE::kGamepad: return essb::Device::kGamepad;
    default: return essb::Device::kOther;
    }
}

// Round 26: the step marker's keys (numpad + / -), while the probe log is on and the game takes input. Before the master
// switch: the probe sheet marks its steps with the switch off too.
// Round 26b: one action of the input sink, run in a task (the sink itself switches nothing; a hotkey may be one frame late).
void InputActionCpp(const essb::sink::Action& a) noexcept
{
    try {
        TaskScope scope("input task");   // round 26c (P5)
        LogThreadOnce(Probe::kInputTask, "input task");
        NoteTaskThread();
        if (a.kind == essb::sink::ActionKind::kStep) {
            if (Active() && TraceOn()) {
                StepKey(a.delta);
            }
            return;
        }
        if (!Enabled()) {
            return;
        }
        RequestSwitch(a.element, "hotkey");
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the input task");
    }
}

void InputActionGuarded(const essb::sink::Action& a) noexcept
{
    __try {
        InputActionCpp(a);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the input task");
    }
}

// Round 26b (the commander's threading ruling): the sink reads the event's buttons and the globals, snapshots the input
// gate once, lets Sinks.h PlanInput map keys to actions, logs, and queues each accepted action with AddTask.
void InputCpp(RE::InputEvent* first) noexcept
{
    try {
        if (!first) {
            return;
        }
        auto& f = state.forms;
        essb::sink::InputFacts facts;
        facts.active = Active();
        if (!facts.active) {
            return;
        }
        facts.trace = TraceOn();
        facts.enabled = Enabled();
        facts.hotkeys = f.hotkeysEnabled && f.hotkeysEnabled->value == 1.0f;
        if (!facts.trace && !(facts.enabled && facts.hotkeys)) {
            return;
        }
        std::vector<essb::sink::Press> presses;
        for (RE::InputEvent* e = first; e; e = e->next) {
            if (e->GetEventType() != RE::INPUT_EVENT_TYPE::kButton) {
                continue;
            }
            const auto* button = e->AsButtonEvent();
            if (button && button->IsDown()) {
                presses.push_back(essb::sink::Press{ DeviceOf(e->GetDevice()), button->GetIDCode(), true });
            }
        }
        if (presses.empty()) {
            return;
        }
        for (int i = 0; i < essb::kElementCount; ++i) {
            facts.keys[i] = f.hotkeys[i] ? static_cast<int>(f.hotkeys[i]->value) : 0;
        }
        facts.stepNext = essb::trace::kStepKeyNext;
        facts.stepBack = essb::trace::kStepKeyBack;
        facts.gate = GateNow();   // one snapshot for the whole event
        const auto actions = essb::sink::PlanInput(presses, facts);
        const essb::InputGate& gate = facts.gate;
        const bool open = essb::InputOpen(gate);   // PlanInput decided on the same snapshot; nothing runs past a closed gate
        for (const essb::sink::Action& a : actions) {
            if (a.kind == essb::sink::ActionKind::kSwitch) {
                LogThreadOnce(Probe::kInput, "input sink");
                if (TraceOn()) {   // round 26
                    essb::trace::Line line("key");
                    essb::trace::KeyLine(line, a.code, a.element, gate, GetCurrentThreadId());
                    Emit(line);
                }
                if (f.debug->value >= 3.0f) {   // probe N6-2
                    if (!a.accepted) {
                        Logf("[ESSB][N6-2][L3] key=%d element=%d blocked paused=%d menu=%d console=%d text=%d loading=%d", a.code, a.element,
                            gate.paused ? 1 : 0, gate.menu ? 1 : 0, gate.console ? 1 : 0, gate.textEntry ? 1 : 0, gate.loading ? 1 : 0);
                    } else {
                        Logf("[ESSB][N6-2][L3] key=%d element=%d accepted thread=%lu", a.code, a.element, GetCurrentThreadId());
                    }
                }
            }
            if (!a.accepted || !open) {
                continue;
            }
            if (const auto* tasks = SKSE::GetTaskInterface()) {
                tasks->AddTask([a]() { InputActionGuarded(a); });
            }
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the input sink");
    }
}

// The input sink (native-verification-3 s13: BSInputDeviceManager sends on the main thread, before the frame's SKSE
// tasks). Never consumes: every event goes on to the game and other sinks.
class InputSink final : public RE::BSTEventSink<RE::InputEvent*>
{
public:
    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent* const* ev, RE::BSTEventSource<RE::InputEvent*>*) override
    {
        // Round 26 (X1): the input sink runs in Main::Update (PollInputDevices), the main loop's thread; its first event of
        // any kind names it (an atomic compare, before anything else).
        LogThreadOnce(Probe::kInputFrame, "input sink (every frame)");   // round 26 threading witness: every thread it runs on
        if (DWORD none = 0; state.inputThread.load() == 0 && state.inputThread.compare_exchange_strong(none, GetCurrentThreadId())) {
            Logf("[ESSB][X1] input sink thread=%lu (Main::Update -> BSInputDeviceManager::PollInputDevices: the main loop) window=%lu %s "
                 "dataLoaded=%lu",
                GetCurrentThreadId(), state.windowThread.load(), Compare(GetCurrentThreadId(), state.windowThread.load()), state.dataThread);
        }
        if (!ev || !*ev || state.faulted) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            InputCpp(*ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in the input sink");
        }
        return RE::BSEventNotifyControl::kContinue;
    }
};

InputSink inputSink;

// ---------------------------------------------------------------- data load

void LoadManifest()
{
    auto* data = RE::TESDataHandler::GetSingleton();
    if (!data) {
        throw std::runtime_error("TESDataHandler unavailable");
    }
    state.forms.nativeHit = data->LookupForm<RE::TESGlobal>(essb::glob::kNativeHit, kPlugin);
    WriteNativeHit(0.0f);

    std::ifstream file("Data/SKSE/Plugins/ElementsSpellblade/manifest.json");
    if (!file) {
        throw std::runtime_error("manifest.json missing");
    }
    nlohmann::json manifest;
    file >> manifest;
    // Round 25 hotfix: the whole resolution is Load.h's (load_test runs it on the written ESP). Every failure is logged
    // as "[ESSB][load] FAILED ..." with the FormID, EditorID, expected type and check; the first one is the fault.
    GameForms game{ *data };
    const essb::load::Summary resolved = essb::load::LoadForms(game, manifest, state.forms);
    Log("[ESSB][load] resolved " + essb::load::Describe(resolved));
    // Round 26: the probe log names the globals it watches by their editor IDs (the manifest's "globals").
    state.globalNames.clear();
    for (const auto& [name, id] : manifest.at("globals").items()) {
        state.globalNames.emplace_back(id.get<std::uint32_t>(), name);
    }

    LARGE_INTEGER counter{};
    QueryPerformanceCounter(&counter);
    state.rng.emplace(static_cast<std::uint64_t>(counter.QuadPart) ^ (GetTickCount64() << 21));

    auto* source = RE::ScriptEventSourceHolder::GetSingleton();
    if (!source) {
        throw std::runtime_error("event sources unavailable");
    }
    source->AddEventSink<RE::TESHitEvent>(&hitSink);
    source->AddEventSink<RE::TESActiveEffectApplyRemoveEvent>(&removeSink);
    source->AddEventSink<RE::TESDeathEvent>(&deathSink);
    source->AddEventSink<RE::TESSpellCastEvent>(&castSink);   // round 23: 反咒, 逼近
    if (auto* ui = RE::UI::GetSingleton()) {
        ui->AddEventSink<RE::MenuOpenCloseEvent>(&menuSink);   // round 23: TrueHUD's menu clears custom widgets on close
    }
    auto* input = RE::BSInputDeviceManager::GetSingleton();
    if (!input) {
        throw std::runtime_error("input device manager unavailable");
    }
    input->AddEventSink(&inputSink);   // round 25 (N6): the hotkeys (ESSBInput is gone)
    essb::hud::SetLog(&HudLog);   // round 26c (T3)
    if (essb::hud::Find()) {
        Log("[ESSB][load] TrueHUD found: the pool and sync bars use its custom widget API");
    } else {
        Log("[ESSB][load] TrueHUD not found (or no RequestPluginAPI): no pool bars, nothing else changes");
    }
    // Round 26 fix: kDataLoaded is sent from the game's InitTESThread, not the main loop; the X1 reference is the first
    // SKSE task's thread (queued here, it runs in Main::Update at the main menu).
    state.dataThread = GetCurrentThreadId();
    // Round 26b (X2): the address ranges the witness lines name frames by, and the Havok TLS index (REL::ID 528600).
    auto moduleRange = [](HMODULE module, std::uintptr_t& base, std::uintptr_t& end) {
        base = reinterpret_cast<std::uintptr_t>(module);
        const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(module);
        const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);
        end = base + nt->OptionalHeader.SizeOfImage;
    };
    moduleRange(GetModuleHandleW(nullptr), state.exeBase, state.exeEnd);
    HMODULE self = nullptr;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            reinterpret_cast<LPCWSTR>(&LogChainOnce), &self) && self) {
        moduleRange(self, state.dllBase, state.dllEnd);
    }
    state.havokTlsIndex = REL::ID(528600).address();
    Logf("[ESSB][X1] kDataLoaded thread=%lu (InitTESThread: SKSE sends kDataLoaded from the data-load thread, not the main loop)",
        state.dataThread);
    if (const auto* tasks = SKSE::GetTaskInterface()) {
        tasks->AddTask([]() { MainThreadGuarded(); });
    }
    timerThread = std::thread(TimerLoop);   // round 26c (P7): kept, stopped before `state` is destroyed
    state.ready = true;
    PublishStatus();
    Log("[ESSB][load] manifest resolved; hit (yours and on you), effect-removed, death and spell-cast sinks registered; timer running; "
        "round 24: the reaction bodies, the burst and the death handling are native; round 25: the per-second work, the domains "
        "and the hotkeys are native");
}

// Once per game load / new game, after the HUD exists.
void AnnounceStatus()
{
    if (!state.ready || state.faulted) {
        return;  // faults were already announced (deferred or immediate)
    }
    if (state.forms.wanted->value != 1.0f) {
        Notify("元素魔戰士 DLL：命中附傷已在 MCM 關閉");
        return;
    }
    if (state.forms.debug->value >= 1.0f) {
        Notify(std::string("元素魔戰士 DLL ") + essb::nativeVersion + "：命中附傷與狀態層運作中");
    }
}

// Round 26c (P4): the load's resets of task-owned state run as a task (FIFO: before the first timer tick of this game).
void GameReadyCpp() noexcept
{
    try {
        TaskScope scope("game ready");
        state.cadence = essb::Cadence{};   // round 25: the timer's clock starts again after a load (nothing carried over)
        // Round 26: after a load the probe log shows the globals and the perks again, and the step marker starts from the save.
        state.globalSeen.clear();
        state.perksRead = false;
        state.domainsSeen.clear();
        state.secondRead = false;
        state.stepSeen = -1.0f;
        essb::hud::Reload();   // round 23: (re)load the bars' swf after a load / new game (round 26c: from a task)
    } catch (...) {
    }
}

void GameReadyGuarded() noexcept
{
    __try {
        GameReadyCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the game-ready task");
    }
}

void OnGameReady()
{
    if (const auto* tasks = SKSE::GetTaskInterface()) {
        tasks->AddTask([]() { GameReadyGuarded(); });   // round 26c: queued before inGame turns on (the timer waits for it)
    }
    if (TraceOn()) {
        essb::trace::Line line("trace");
        line.F(" game-ready running=%llu", static_cast<unsigned long long>(state.runningMs.load()));
        Emit(line);
    }
    FlushTrace();
    state.inGame = true;
    state.echoDispelQueued = false;
    state.riposteDispelQueued = false;
    t_selfDispel = false;
    state.hurtQueued = false;
    {
        std::lock_guard lock(state.hurtLock);
        state.hurts.clear();
    }
    PublishStatus();
    std::vector<std::string> notices;
    {
        std::lock_guard lock(state.noticeLock);   // round 26c
        notices.swap(state.deferredNotices);
    }
    for (auto& text : notices) {
        Show(text);
    }
    AnnounceStatus();
}

void MessageCpp(SKSE::MessagingInterface::Message* message) noexcept
{
    try {
        if (!message) {
            return;
        }
        switch (message->type) {
        case SKSE::MessagingInterface::kDataLoaded:
            if (!state.faulted) {
                LoadManifest();
            }
            break;
        case SKSE::MessagingInterface::kPreLoadGame:
            state.inGame = false;
            PublishStatus();
            if (TraceOn()) {   // round 26
                essb::trace::Line line("trace");
                line.F(" loading running=%llu", static_cast<unsigned long long>(state.runningMs.load()));
                Emit(line);
            }
            FlushTrace();
            break;
        case SKSE::MessagingInterface::kSaveGame:
            if (TraceOn()) {   // round 26
                essb::trace::Line line("trace");
                line.F(" saved running=%llu", static_cast<unsigned long long>(state.runningMs.load()));
                Emit(line);
            }
            FlushTrace();
            break;
        case SKSE::MessagingInterface::kPostLoadGame:
            // SKSE passes the success flag as the pointer value itself, not as bool*.
            if (message->data != nullptr) {
                OnGameReady();
            }
            break;
        case SKSE::MessagingInterface::kNewGame:
            OnGameReady();
            break;
        default:
            break;
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown exception while loading");
    }
}

void Message(SKSE::MessagingInterface::Message* message)
{
    __try {
        MessageCpp(message);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation while loading");
    }
}

// ---------------------------------------------------------------- Papyrus: MCM

bool IsActiveGuarded() noexcept
{
    __try {
        return Active();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in IsNativeHitActive");
        return false;
    }
}

void SetWantedCpp(bool on) noexcept
{
    if (!state.forms.wanted) {
        return;
    }
    state.forms.wanted->value = on ? 1.0f : 0.0f;
    PublishStatus();
    if (!on) {
        Notify("元素魔戰士 DLL：命中附傷已在 MCM 關閉");
    } else if (Active()) {
        Notify("元素魔戰士 DLL：命中附傷已開啟");
    } else {
        Notify("元素魔戰士 DLL：已要求開啟，但 DLL 故障或未就緒，命中附傷仍停用");
    }
}

void SetWantedGuarded(bool on) noexcept
{
    __try {
        SetWantedCpp(on);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in SetNativeHit");
    }
}

bool PapyrusIsNativeHitActive(RE::StaticFunctionTag*)
{
    return IsActiveGuarded();
}

std::string PapyrusNativeVersion(RE::StaticFunctionTag*)
{
    return essb::nativeVersion;
}

void PapyrusSetNativeHit(RE::StaticFunctionTag*, bool on)
{
    SetWantedGuarded(on);
}

// ---------------------------------------------------------------- Papyrus: the status layer for the reaction bodies
//
// ESSBNative.psc lists these. Status codes (the old aiKind numbering, v0.4 meanings):
//   1 fire mark   2 freeze gauge (5 = frozen)   3 fissure   4 unbalance   5 bleed layers   6 divine mark (聖印)
//   7 poison doses   8 soak   9 pressure   10 curse   11 star layers   12 ice crystals   13 downed   14 airborne
//   15 star lock   16 catalysed   17 death-curse fuse   18 nether   19 frozen
// On the player: 20 heat tier (0..4)   21 聖佑 tier (0..3)   22 熔身
// Windows (SetWindow): 30 嗜血 (player)   31 連殺 (player)   36 浮空 (target)   37 瘋狂冷卻 (target)
// (round 25: 32-35, the Papyrus domains' windows, are gone -- the hazards put the markers on, Timer.h keeps yours)

enum class NativeCall
{
    kRead,
    kAdd,
    kSet,
    kClear,
};

// SEH frame for a native's body (no objects with destructors in this function, so __try is allowed): an access
// violation inside the engine calls becomes a fault instead of a crash. C++ exceptions (0xE06D7363) pass on to the
// caller's catch so their message is kept.
template <class F>
bool SehInvoke(F& f) noexcept
{
    __try {
        f();
        return true;
    } __except (GetExceptionCode() == 0xE06D7363 ? EXCEPTION_CONTINUE_SEARCH : EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

// Every ESSBNative function body runs here: C++ catch and the SEH frame above (round 22 crash guards).
template <class Body>
auto Guard(const char* what, Body&& body, decltype(body()) fallback, bool readOnly = false) noexcept -> decltype(body())
{
    try {
        // Master switch (review fix 3): natives that change anything stop; the read-only ones (GetStatus, MarksOn, ...)
        // keep answering so the MCM status button works with the switch off (commander ruling).
        if (readOnly ? !Active() : !Enabled()) {   // master switch (review fix 3)
            return fallback;
        }
        LogThreadOnce(Probe::kNative, "Papyrus native");
        std::optional<decltype(body())> out;
        auto run = [&]() { out.emplace(body()); };
        if (!SehInvoke(run)) {
            Fault((std::string("access violation in ESSBNative.") + what).c_str());
            return fallback;
        }
        return std::move(*out);
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault(what);
    }
    return fallback;
}

// Round 24 review fix 1: a native that scans or casts only queues its work (SKSE AddTask, thread-safe) and returns; the
// work runs on the main thread whatever thread the VM called the native from (nv3 s10: the process lists and the effect
// lists are main-thread only), in call order (the task queue is FIFO, so Burst -> FormLeave -> SetSync keep their order).
struct NativeJob {
    const char* what;
    std::function<void()> run;
};

void NativeJobCpp(NativeJob* job) noexcept
{
    try {
        TaskScope scope("queued native task");   // round 26c (P5)
        if (Enabled()) {   // master switch (review fix 3): the switch may have been turned off since the call
            LogThreadOnce(Probe::kNativeTask, "queued native task");
            NoteTaskThread();
            job->run();
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault(job->what);
    }
}

void NativeJobGuarded(NativeJob* job) noexcept
{
    __try {
        NativeJobCpp(job);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in a queued ESSBNative task");
    }
    delete job;
}

bool QueueNative(const char* what, std::function<void()> run)
{
    auto* tasks = SKSE::GetTaskInterface();
    if (!tasks) {
        return false;
    }
    auto* job = new NativeJob{ what, std::move(run) };
    tasks->AddTask([job]() { NativeJobGuarded(job); });
    return true;
}

RE::ActorHandle HandleOf(RE::Actor* actor)
{
    return actor ? actor->GetHandle() : RE::ActorHandle{};
}

// One native call on `actor`: read the boards, run `plan` (a Status.h rule), execute.
template <class Rule>
void RunRule(RE::Actor* actor, Rule&& rule)
{
    auto* player = RE::PlayerCharacter::GetSingleton();
    if (!player || !actor || actor->IsDead()) {
        return;
    }
    const auto perks = MakeNodes(*player, FormIsActive());
    Context c = MakeContext(*player, false);
    const bool onPlayer = actor == player;
    RE::Actor* target = onPlayer ? nullptr : actor;
    essb::Board selfBoard = ReadBoard(*player);
    const auto nodes = essb::WithAvatar(perks, selfBoard);   // round 23: 化身
    essb::Board targetBoard = target ? ReadBoard(*target) : essb::Board{};
    if (target) {
        c.in.body = ReadBody(*target, *player, TargetFactsOf(*target));
    }
    auto planPtr = std::make_unique<essb::StatusPlan>();
    essb::StatusPlan& plan = *planPtr;
    rule(plan, targetBoard, selfBoard, c, nodes);
    CrowdRead crowd;   // round 24: a native that froze / cursed / detonated brings its bodies
    RunWithBodies(*player, target, target ? &targetBoard : nullptr, plan, 0, selfBoard, c, nodes, crowd);
    WriteMirrors(*player, selfBoard, nodes);   // round 23: a native may have changed your resources
}

// ---------------------------------------------------------------- round 26: the natives in the probe log

// One ESSBNative call as the queued task runs it (the rule's ops follow with ctx=native:<fn>).
void TraceNative(const char* fn, RE::Actor* actor, int a, int b, float x = 0.0f)
{
    if (!TraceOn()) {
        return;
    }
    essb::trace::Line line("native");
    line.F(" fn=%s", fn);
    line.Actor("who", FactsOf(actor));
    line.F(" a=%d b=%d x=%.2f form=%s", a, b, x, essb::trace::ElementName(FormElement()));
    Emit(line);
}

// ---------------------------------------------------------------- round 23: the engine-side ops (SelfLayer.h / Hurt.h)

// Round 24 (N5): 共鳴層's count, 碎岩's ring and 冰心 are the body pass's (Reactions.h RunBodies) on the event's crowd.
void CrowdOpOutsideBodies(const char* what) noexcept
{
    if (state.forms.debug && state.forms.debug->value >= 1.0f) {
        Logf("[ESSB][bodies][L1] a %s op reached the engine without its body pass (skipped)", what);
    }
}

void InterruptCpp(const RE::ActorHandle& handle) noexcept
{
    try {
        TaskScope scope("interrupt task");   // round 26c (P5)
        auto ptr = handle.get();
        RE::Actor* actor = ptr.get();
        if (actor && !actor->IsDead() && actor->Is3DLoaded()) {
            actor->InterruptCast(false);   // native-verification-3 s9: the same engine path as Papyrus InterruptCast
            if (state.forms.debug->value >= 3.0f) {   // probe N4-2: the hands drop, the magicka stays
                Logf("[ESSB][N4-2][L3] interrupt target=%08X magicka=%.1f", actor->GetFormID(),
                    actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka));
            }
            if (TraceOn()) {   // round 26
                essb::trace::Line line("interrupt");
                line.Actor("who", FactsOf(actor));
                Emit(line);
            }
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the interrupt task");
    }
}

void InterruptGuarded(const RE::ActorHandle& handle) noexcept
{
    __try {
        InterruptCpp(handle);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the interrupt task");
    }
}

void QueueInterrupt(RE::ActorHandle actor)
{
    if (const auto* tasks = SKSE::GetTaskInterface()) {
        tasks->AddTask([actor]() { InterruptGuarded(actor); });
    }
}

// 反咒 and 逼近 (5.1), in the task after TESSpellCastEvent.
void CastCpp(const CastSeen& seen) noexcept
{
    try {
        TaskScope scope("spell-cast task");   // round 26c (P5)
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto casterPtr = seen.caster.get();
        RE::Actor* caster = casterPtr.get();
        if (!Enabled() || !player || !caster || caster->IsDead()) {
            return;
        }
        essb::CastFacts f;
        f.hostileNear = caster->IsHostileToActor(player) && caster->GetPosition().GetDistance(player->GetPosition()) <= essb::n4::kCloseInRadius;
        ForEachRunningEffect(*caster, [&](RE::ActiveEffect&, RE::EffectSetting& effect) {
            f.marked = f.marked || &effect == state.forms.manaBreak;
        });
        auto* spell = RE::TESForm::LookupByID<RE::MagicItem>(seen.spell);
        if (f.marked && spell) {
            // v0.4 5.1: the magicka that cast cost, recomputed (MagicItem::CalculateMagickaCost); a dual cast × the game's
            // dual-cast cost multiplier (native-verification-2 s6).
            f.cost = spell->CalculateMagickaCost(caster);
            for (RE::ActorMagicCaster* hand : caster->GetActorRuntimeData().magicCasters) {
                if (hand && hand->currentSpell == spell && hand->GetIsDualCasting()) {
                    f.cost *= GameSetting("fMagicDualCastingCostMult", 2.8f);
                    break;
                }
            }
        }
        if (!f.hostileNear && !(f.marked && f.cost > 0.0f)) {
            return;
        }
        TraceCtx traceCtx("enemy-cast");   // round 26
        LogThreadOnce(Probe::kCastTask, "spell-cast task");
        NoteTaskThread();
        if (TraceOn()) {
            essb::trace::Line line("cast");
            line.Actor("caster", FactsOf(caster));
            line.F(" spell=0x%08X marked=%d cost=%.2f near=%d form=%d", seen.spell, f.marked ? 1 : 0, f.cost, f.hostileNear ? 1 : 0, FormElement());
            Emit(line);
        }
        RunRule(caster, [&](auto& plan, auto&, auto& self, auto& c, const auto& nodes) {
            f.trueMult = essb::TrueDamageMultiplier(TargetFactsOf(*caster), c.tuning, nodes);
            essb::PlanSpellCast(plan, f, self, c.in, nodes);
        });
        if (state.forms.debug->value >= 3.0f) {   // probe N4-1: the cost the DLL computed for a marked caster
            Logf("[ESSB][N4-1][L3] caster=%08X spell=%08X marked=%d cost=%.2f near=%d", caster->GetFormID(), seen.spell, f.marked ? 1 : 0,
                f.cost, f.hostileNear ? 1 : 0);
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in the spell-cast task");
    }
}

float ReadCode(RE::Actor& actor, int code)
{
    using K = essb::StatusKind;
    const essb::Board b = ReadBoard(actor);
    auto* player = RE::PlayerCharacter::GetSingleton();
    switch (code) {
    case 1: return b.mark[essb::kFire].has ? 1.0f : 0.0f;
    case 2: return static_cast<float>(b.Has(K::kFrozen) ? essb::n3::kFreezeCap : b.Layers(K::kFreeze));
    case 3: return b.Has(K::kFissure) ? 1.0f : 0.0f;
    case 4: return b.Has(K::kUnbalance) ? 1.0f : 0.0f;
    case 5: return static_cast<float>(b.Layers(K::kBleed));
    case 6: return b.mark[essb::kDivine].has ? 1.0f : 0.0f;
    case 7: return player ? static_cast<float>(essb::Doses(b, essb::PerDose(kConfig, essb::ReadTuning(Global), MakeNodes(*player, FormIsActive())))) : 0.0f;
    case 8: return b.Has(K::kSoak) ? 1.0f : 0.0f;
    case 9: return static_cast<float>(b.Layers(K::kPressure));
    case 10: return static_cast<float>(b.Layers(K::kCurse));
    case 11: return static_cast<float>(b.Layers(K::kStar));
    case 12: return static_cast<float>(b.Layers(K::kCrystal));
    case 13: return b.Has(K::kDowned) ? 1.0f : 0.0f;
    case 14: return b[K::kAirborne].Remaining();
    case 15: return b.Has(K::kStarLock) ? 1.0f : 0.0f;
    case 16: return b.Has(K::kCatalyzed) ? 1.0f : 0.0f;
    case 17: return b.Has(K::kDeathCurse) ? 1.0f : 0.0f;
    case 18: return b.Has(K::kNether) ? 1.0f : 0.0f;
    case 19: return b.Has(K::kFrozen) ? 1.0f : 0.0f;
    case 20: return static_cast<float>(essb::HeatTier(b));
    case 21: return static_cast<float>(essb::HolyTier(b));
    case 22: return b.Has(K::kMoltenBody) ? 1.0f : 0.0f;
    case 23: return static_cast<float>(b.Layers(K::kPunish));
    case 24: return b.Has(K::kFrenzyCooldown) ? 1.0f : 0.0f;
    // Round 23 (N4): your resources (on the player) and the kill-streak marker (on a target).
    case 40: return static_cast<float>(b.Layers(K::kSync));
    case 41: return player ? static_cast<float>(essb::res::StageOf(b.Layers(K::kSync), essb::res::Thresholds(essb::ReadTuning(Global), b, MakeNodes(*player, FormIsActive())))) : 0.0f;
    case 42: return static_cast<float>(b.Layers(K::kCharge));
    case 43: return static_cast<float>(b.Layers(K::kRockArmor));
    case 44: return static_cast<float>(b.Layers(K::kWindGauge));
    case 45: return static_cast<float>(b.Layers(K::kResolve));
    case 46: return static_cast<float>(b.Layers(K::kIceShield));
    case 47: return static_cast<float>(b.Layers(K::kResonance));
    case 48: return static_cast<float>(b.Layers(K::kCosmos));
    case 49: return b.Has(K::kOverload) ? b[K::kOverload].magnitude : 0.0f;
    case 50: return static_cast<float>(b.Layers(K::kStoredForce));
    case 51: return b.Has(K::kSyncKeepAll) ? 1.0f : 0.0f;
    case 52: return b.Has(K::kQuickShock) ? 1.0f : 0.0f;
    case 53: return b.Has(K::kChargedQuake) ? b[K::kChargedQuake].magnitude : 0.0f;
    case 54: return b.Has(K::kLastHitSneak) ? b[K::kLastHitSneak].magnitude : 0.0f;
    case 55: return player ? static_cast<float>(essb::res::ChargeCap(MakeNodes(*player, FormIsActive()))) : 0.0f;
    case 56: return player ? static_cast<float>(essb::res::WindThreshold(MakeNodes(*player, FormIsActive()))) : 0.0f;
    case 57: return player ? static_cast<float>(essb::res::RockCap(MakeNodes(*player, FormIsActive()))) : 0.0f;
    case 58: return b.guardPool.has ? b.guardPool.magnitude : 0.0f;
    default: return 0.0f;
    }
}

std::int32_t PapyrusGetStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code)
{
    return Guard("GetStatus", [&]() -> std::int32_t { return actor ? static_cast<std::int32_t>(ReadCode(*actor, code) + 0.001f) : 0; }, 0, true);
}

float PapyrusGetStatusFloat(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code)
{
    return Guard("GetStatusFloat", [&]() -> float { return actor ? ReadCode(*actor, code) : 0.0f; }, 0.0f, true);
}

// Adds (or with `set` sets) layers of a target status through the same rules as a hit (caps, the freeze at 5, the
// wash at full pressure, the illusion ladder).
template <class Nodes>
void AddOrSet(essb::StatusPlan& plan, essb::Board& target, essb::Board& self, Context& c, const Nodes& nodes, int code, int amount, bool set)
{
    using K = essb::StatusKind;
    const essb::Writer tw{ plan, target, essb::Who::kTarget };
    const essb::Tuning& t = c.tuning;
    auto delta = [&](K kind) { return set ? amount - target.Layers(kind) : amount; };
    switch (code) {
    case 2:
        if (set && amount <= 0) {
            tw.Clear(K::kFreeze);
            tw.Clear(K::kFrozen);
        } else if (set && amount >= essb::n3::kFreezeCap) {
            if (!target.Has(K::kFrozen)) {
                essb::rule::Freeze(plan, target, essb::rule::FrozenSeconds(t, nodes), 1.0f, nodes);
            }
        } else {
            essb::rule::AddFreeze(plan, target, static_cast<float>(delta(K::kFreeze)), false, c.in, nodes, Rng());
        }
        break;
    case 3: tw.Set(K::kFissure, 1.0f, essb::Scaled(t, essb::n3::kFissure)); break;
    case 4: tw.Set(K::kUnbalance, 1.0f, essb::Scaled(t, essb::n3::kUnbalance)); break;
    case 5: essb::rule::AddBleed(plan, target, delta(K::kBleed), c.in, nodes); break;
    case 7: essb::rule::AddDoses(plan, target, static_cast<float>(amount), c.in, nodes); break;
    // 25: 擴散劑數（淬毒的傳劑、濃毒）— 2.7 擴散一劑 d' = max(d - t, 12)（審查修正 5）。
    case 25: essb::rule::SpreadDoses(plan, target, static_cast<float>(amount), c.in, nodes); break;
    case 8: tw.Set(K::kSoak, 1.0f, essb::rule::SoakSeconds(t, nodes)); break;
    case 9: essb::rule::SetPressure(plan, target, set ? amount : target.Layers(K::kPressure) + amount, c.in, nodes); break;
    case 10: essb::rule::AddCurse(plan, target, delta(K::kCurse), c.in, nodes); break;
    case 11: essb::rule::AddStars(plan, target, delta(K::kStar), c.in, nodes); break;
    case 12: tw.Set(K::kCrystal, static_cast<float>(std::clamp(set ? amount : target.Layers(K::kCrystal) + amount, 0, essb::n3::kCrystalCap)),
                 target.Has(K::kFrozen) ? target[K::kFrozen].Remaining() + essb::n3::kCrystalMargin : essb::Scaled(t, essb::n3::kFreezeGauge));
        break;
    case 13: essb::rule::Down(plan, target, c.in, nodes); break;
    case 15: tw.Set(K::kStarLock, 1.0f, essb::Scaled(t, essb::n3::kStarLock)); break;
    case 18: tw.Set(K::kNether, 1.0f, essb::Scaled(t, 8.0f)); break;
    default: break;
    }
    (void)self;
}

// Round 23 (N4): your resources through ESSBNative's player codes (40-58, see ESSBNative.psc), for the Papyrus paths that
// still add or set one: the storm weather's +1 charge (v0.4 2.10: a Papyrus timer calls the DLL), a lethal wind sneak
// attack's full gauge, the sync a switch keeps (承接、連斷、永續、三重奏), clearing on request.
template <class Nodes>
void SelfCode(essb::StatusPlan& plan, essb::Board& self, Context& c, const Nodes& nodes, int code, int amount, bool set)
{
    using K = essb::StatusKind;
    const auto value = [&](K kind) { return set ? amount : self.Layers(kind) + amount; };
    switch (code) {
    case 40: essb::res::SetSync(plan, self, value(K::kSync), c.in, nodes); break;
    case 42: essb::res::SetCharges(plan, self, value(K::kCharge), c.in, nodes); break;
    case 43: essb::res::SetRock(plan, self, value(K::kRockArmor), c.in, nodes); break;
    case 44: essb::res::SetWind(plan, self, value(K::kWindGauge), c.in, nodes); break;
    case 45:
        essb::res::SetCount(plan, self, K::kResolve, (std::min)(essb::n4::kResolveCap, value(K::kResolve)), essb::Scaled(c.tuning, essb::n4::kResolve));
        break;
    case 46: essb::res::SetIceShield(plan, self, value(K::kIceShield), c.in, nodes); break;
    case 47:
        if (set) {
            essb::res::SetCount(plan, self, K::kResonance, amount, essb::Scaled(c.tuning, essb::n4::kResonance));
        } else {
            essb::res::AddResonance(plan, self, amount, c.in, nodes);
        }
        break;
    case 48:
        essb::res::SetCount(plan, self, K::kCosmos, (std::min)(essb::n4::kCosmosCap, value(K::kCosmos)), essb::Scaled(c.tuning, essb::n4::kCosmos));
        break;
    case 50: essb::res::SetCount(plan, self, K::kStoredForce, (std::min)(essb::n4::kForceCap, value(K::kStoredForce)), essb::n4::kForever); break;
    case 51: essb::res::SetCount(plan, self, K::kSyncKeepAll, (std::min)(1, value(K::kSyncKeepAll)), 60.0f); break;
    case 53:
        if (set && amount <= 0) {
            essb::Writer{ plan, self, essb::Who::kPlayer }.Clear(K::kChargedQuake);   // 蓄能's quake bonus used by the earth end
        }
        break;
    default: break;
    }
}

void PapyrusAddStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code, std::int32_t amount)
{
    Guard("AddStatus", [&]() -> bool {
        return QueueNative("AddStatus", [handle = HandleOf(actor), code, amount]() {
            const auto held = handle.get();
            RE::Actor* actor = held.get();
            TraceCtx traceCtx("native:AddStatus");   // round 26
            TraceNative("AddStatus", actor, code, amount);
            RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
                if (actor == RE::PlayerCharacter::GetSingleton()) {
                    SelfCode(plan, self, c, nodes, code, amount, false);   // round 23: your resources
                } else {
                    AddOrSet(plan, target, self, c, nodes, code, amount, false);
                }
            });
        });
    }, false);
}

void PapyrusSetStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code, std::int32_t value)
{
    Guard("SetStatus", [&]() -> bool {
        return QueueNative("SetStatus", [handle = HandleOf(actor), code, value]() {
            const auto held = handle.get();
            RE::Actor* actor = held.get();
            TraceCtx traceCtx("native:SetStatus");   // round 26
            TraceNative("SetStatus", actor, code, value);
            RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
                if (actor == RE::PlayerCharacter::GetSingleton()) {
                    SelfCode(plan, self, c, nodes, code, value, true);
                } else {
                    AddOrSet(plan, target, self, c, nodes, code, value, true);
                }
            });
        });
    }, false);
}

void PapyrusClearStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code)
{
    using K = essb::StatusKind;
    static constexpr std::pair<int, K> kCodes[] = { { 3, K::kFissure }, { 4, K::kUnbalance }, { 8, K::kSoak }, { 9, K::kPressure },
        { 10, K::kCurse }, { 11, K::kStar }, { 12, K::kCrystal }, { 13, K::kDowned }, { 15, K::kStarLock }, { 16, K::kCatalyzed },
        { 17, K::kDeathCurse }, { 18, K::kNether }, { 19, K::kFrozen } };
    Guard("ClearStatus", [&]() -> bool {
        return QueueNative("ClearStatus", [handle = HandleOf(actor), code]() {
            const auto held = handle.get();
            RE::Actor* actor = held.get();
            TraceCtx traceCtx("native:ClearStatus");   // round 26
            TraceNative("ClearStatus", actor, code, 0);
            RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
                const essb::Writer tw{ plan, target, essb::Who::kTarget };
                if (code == 23) {
                    essb::Writer{ plan, self, essb::Who::kPlayer }.Clear(K::kPunish);   // 懲戒 used by 裁決 (on the player)
                } else if (code >= 40) {
                    SelfCode(plan, self, c, nodes, code, 0, true);   // round 23: your resources to 0
                } else if (code == 2) {
                    tw.Clear(K::kFreeze);
                    tw.Clear(K::kFrozen);
                    tw.Clear(K::kCrystal);
                } else if (code == 5) {
                    tw.Clear(K::kBleed);
                    plan.Push(essb::Amount(essb::Op::kBleedDot, 0.0f));
                } else if (code == 7) {
                    plan.Push(essb::Amount(essb::Op::kPoisonDot, 0.0f));
                    tw.Clear(K::kCatalyzed);
                } else if (code == 11) {
                    tw.Clear(K::kStar);
                    tw.Clear(K::kStarFuse);
                } else {
                    for (const auto& [listed, kind] : kCodes) {
                        if (listed == code) {
                            tw.Clear(kind);
                        }
                    }
                }
            });
        });
    }, false);
}

void PapyrusSetWindow(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t window, float seconds, float magnitude)
{
    using K = essb::StatusKind;
    Guard("SetWindow", [&]() -> bool {
        return QueueNative("SetWindow", [handle = HandleOf(actor), window, seconds, magnitude]() {
            const auto held = handle.get();
            RE::Actor* actor = held.get();
            TraceCtx traceCtx("native:SetWindow");   // round 26
            TraceNative("SetWindow", actor, window, static_cast<int>(seconds + 0.5f), magnitude);
            RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto&) {
                const float s = essb::Scaled(c.tuning, seconds);
                switch (window) {
                case 30: essb::Writer{ plan, self, essb::Who::kPlayer }.Set(K::kBloodthirst, 1.0f, s); break;
                case 31: essb::Writer{ plan, self, essb::Who::kPlayer }.Set(K::kKillStreak, 1.0f, seconds); break;
                case 36: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kAirborne, magnitude, s); break;
                case 37: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kFrenzyCooldown, 1.0f, essb::CooldownOf(c.tuning, seconds)); break;
                default: break;
                }
            });
        });
    }, false);
}

// The mark of `element` without the open reaction (傳導、聖輝、暗染、星散、風襲: "開印時附近 1 人也 X").
void PapyrusApplyMark(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t element)
{
    Guard("ApplyMark", [&]() -> bool {
        if (!essb::IsElement(element)) {
            return false;
        }
        return QueueNative("ApplyMark", [handle = HandleOf(actor), element]() {
            const auto held = handle.get();
            TraceCtx traceCtx("native:ApplyMark");   // round 26
            TraceNative("ApplyMark", held.get(), element, 0);
            RunRule(held.get(), [&](auto& plan, auto& target, auto&, auto& c, const auto& nodes) {
                essb::Writer{ plan, target, essb::Who::kTarget }.Mark(element, essb::rule::MarkSeconds(element, c.tuning, nodes, false));
            });
        });
    }, false);
}

std::int32_t MarksOf(const essb::Board& b)
{
    std::int32_t mask = 0;
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        mask |= b.mark[e].has ? (1 << e) : 0;
    }
    return mask;
}

std::int32_t PapyrusMarksOn(RE::StaticFunctionTag*, RE::Actor* actor)
{
    return Guard("MarksOn", [&]() -> std::int32_t { return actor ? MarksOf(ReadBoard(*actor)) : 0; }, 0, true);
}

// 融斷 (2.5, round 24): Papyrus CloseForm calls this before FormLeave. The DLL reads the crowd once (you and 15 m past the
// burst radius), settles every mark in range (B_max × K_sync × G × M_mod, v0.4 2.7 D_burst; the end's non-damage part
// per 2.6) and runs the bodies (冷寂's 寂, 萬寂, 斷界, 回流, 雙斷, 安全閥, 地斷, 颶風, 墜星's burst half). Queued (review fix 1).
void PapyrusBurst(RE::StaticFunctionTag*, std::int32_t element)
{
    Guard("Burst", [&]() -> bool {
        return QueueNative("Burst", [element]() {   // review fix 1: the scan and the casts run in a task
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!player) {
                return;
            }
            const auto perks = MakeNodes(*player, FormIsActive());
            Context c = MakeContext(*player, false);
            essb::Board selfBoard = ReadBoard(*player);
            const auto nodes = essb::WithAvatar(perks, selfBoard);
            const int stage = essb::res::StageOf(selfBoard.Layers(essb::StatusKind::kSync), essb::res::Thresholds(c.tuning, selfBoard, nodes));
            TraceCtx traceCtx("burst");   // round 26
            const bool tracing = TraceOn();
            if (tracing) {
                essb::trace::Line line("burst-start");
                line.F(" element=%s stage=%d sync=%d radius=%.0f", essb::trace::ElementName(element), stage,
                    selfBoard.Layers(essb::StatusKind::kSync), essb::BurstRadius(nodes));
                line.Actor("you", FactsOf(player));
                Emit(line);
                Rng().Record(true);
            }
            CrowdRead crowd;
            BuildCrowd(crowd, *player, nullptr, nullptr, 0.0f, essb::BurstRadius(nodes) + kAroundEvent);
            const essb::BodyInputs bin = BodyInputsOf(*player, c, false);
            auto planPtr = std::make_unique<essb::StatusPlan>();
            essb::StatusPlan& plan = *planPtr;
            const essb::BurstResult r = essb::PlanBurst(plan, *crowd.crowd, selfBoard, bin, stage, element, nodes, Rng());
            Executor(*player, nullptr, c.tuning, &crowd.actors).Run(plan);
            WriteMirrors(*player, selfBoard, nodes);
            if (state.forms.debug->value >= 1.0f) {   // v0.4 6.1: 融斷（目標數、同調段）; probe N5-2 reads the crowd size
                Logf("[ESSB][burst][L1] element=%d stage=%d targets=%d marks=%d crowd=%d ops=%d", element, stage, r.targets, r.marks,
                    crowd.crowd->count, plan.count);
            }
            if (tracing) {   // round 26
                essb::trace::Line line("burst");
                line.F(" element=%s stage=%d targets=%d marks=%d crowd=%d ops=%d", essb::trace::ElementName(element), stage, r.targets,
                    r.marks, crowd.crowd->count, plan.count);
                Emit(line);
                TraceDraws("burst");
            }
        });
    }, false);
}

// Leaving a form (Papyrus OnFormSwitched / CloseForm): 洩壓 and the self ladders (Status.h OnFormLeave).
void PapyrusFormLeave(RE::StaticFunctionTag*, std::int32_t element, bool burst)
{
    Guard("FormLeave", [&]() -> bool {
        return QueueNative("FormLeave", [element, burst]() {
        TraceCtx traceCtx("leave");   // round 26
        TraceNative("FormLeave", RE::PlayerCharacter::GetSingleton(), element, burst ? 1 : 0);
        RunRule(RE::PlayerCharacter::GetSingleton(), [&](auto& plan, auto&, auto& self, auto& c, const auto& nodes) {
            essb::OnFormLeave(plan, element, burst, self, c.in, nodes);
            essb::PlanSelfLeave(plan, element, burst, self, c.in, nodes);   // round 23: your resources (SelfLayer.h)
        });
        });
    }, false);
}

// Round 23 (N4): opening a form (Papyrus OnFormOpened): the 專一 clock, 雷臨強化, 地臨強化 (SelfLayer.h PlanSelfEnter);
// round 24 (N5): the advents (Reactions.h PlanAdvent).
void PapyrusFormEnter(RE::StaticFunctionTag*, std::int32_t element)
{
    Guard("FormEnter", [&]() -> bool {
        if (!essb::IsElement(element)) {
            return false;
        }
        return QueueNative("FormEnter", [element]() {   // review fix 1: the scan and the casts run in a task
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!player) {
                return;
            }
            const auto perks = MakeNodes(*player, true);
            Context c = MakeContext(*player, false);
            essb::Board selfBoard = ReadBoard(*player);
            const auto nodes = essb::WithAvatar(perks, selfBoard);
            auto planPtr = std::make_unique<essb::StatusPlan>();
            essb::StatusPlan& plan = *planPtr;
            TraceCtx traceCtx("enter");   // round 26
            TraceNative("FormEnter", player, element, 0);
            essb::PlanSelfEnter(plan, element, selfBoard, c.in, nodes);
            // Round 24 (N5): X臨, the 臨強化 branches, 臨界, 雙斷 -- one crowd around you (the burst range covers 雙斷).
            CrowdRead crowd;
            BuildCrowd(crowd, *player, nullptr, nullptr, 0.0f, essb::BurstRadius(nodes) + kAroundEvent);
            const essb::BodyInputs bin = BodyInputsOf(*player, c, false);
            essb::PlanAdvent(plan, *crowd.crowd, selfBoard, bin, element, nodes, Rng());
            Executor(*player, nullptr, c.tuning, &crowd.actors).Run(plan);
            WriteMirrors(*player, selfBoard, nodes);
        });
    }, false);
}

// Round 23 (N4): the sync count a switch or a burst leaves (Papyrus decides the keep: 承接、連斷、永續、三重奏).
void PapyrusSetSync(RE::StaticFunctionTag*, std::int32_t count)
{
    Guard("SetSync", [&]() -> bool {
        return QueueNative("SetSync", [count]() {
        TraceCtx traceCtx("native:SetSync");   // round 26
        TraceNative("SetSync", RE::PlayerCharacter::GetSingleton(), count, 0);
        RunRule(RE::PlayerCharacter::GetSingleton(), [&](auto& plan, auto&, auto& self, auto& c, const auto& nodes) {
            essb::res::SetSync(plan, self, (std::max)(0, count), c.in, nodes, false);
        });
        });
    }, false);
}

// Round 25 (N6, ruling R6): the Z form powers (ESSBFormPowerEffect) switch through the same DLL function as the hotkeys
// (RequestSwitch: the magicka gate, the globals, the notice, ESSB_Switch). Queued: it runs on the main thread. The old
// ExtendFuse native is gone with its only caller (Papyrus TickDomain): 火域's fuse is Timer.h PlanDomainSelf's.
void PapyrusRequestSwitch(RE::StaticFunctionTag*, std::int32_t element)
{
    Guard("RequestSwitch", [&]() -> bool {
        if (!essb::IsElement(element)) {
            return false;
        }
        return QueueNative("RequestSwitch", [element]() { RequestSwitch(element, "power"); });
    }, false);
}

// 審查修正 (round 25 review): Papyrus's second windows (ESSBController TickTimers: 引燃、淬火、守勢…) count game-running
// seconds, not real time, so they stop while the game is paused or loading. A read of one atomic: callable from the
// VM's tasklets (no main-thread wait), no game object touched. Not through Guard: it must answer with the master switch
// off too (a window that never ends would be worse), and its tasklet thread is not the X1 probe's native thread.
float PapyrusRunningSeconds(RE::StaticFunctionTag*)
{
    float out = 0.0f;
    try {
        auto read = [&]() { out = static_cast<float>(static_cast<double>(state.runningMs.load()) / 1000.0); };
        if (!SehInvoke(read)) {
            Fault("access violation in ESSBNative.RunningSeconds");
        }
    } catch (...) {
        Fault("C++ exception in ESSBNative.RunningSeconds");
    }
    return out;
}

// The MCM status button (Papyrus DumpStatus): every marked actor within `radius` of you, with its status codes, to the log.
void PapyrusDumpTargets(RE::StaticFunctionTag*, float radius)
{
    Guard("DumpTargets", [&]() -> bool {
        return QueueNative("DumpTargets", [radius]() {   // review fix 1: the process-list scan runs in a task
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* lists = RE::ProcessLists::GetSingleton();
            if (!player || !lists) {
                return;
            }
            int count = 0;
            for (auto& handle : lists->highActorHandles) {
                auto held = handle.get();
                RE::Actor* actor = held.get();
                if (!actor || actor == player || actor->IsDead()) {
                    continue;
                }
                const float d = actor->GetPosition().GetDistance(player->GetPosition());
                const std::int32_t marks = MarksOf(ReadBoard(*actor));
                if (d > radius || marks == 0) {
                    continue;
                }
                ++count;
                std::string line;
                for (int code = 2; code <= 19; ++code) {
                    const int value = static_cast<int>(ReadCode(*actor, code) + 0.001f);
                    if (value != 0) {
                        line += " s" + std::to_string(code) + "=" + std::to_string(value);
                    }
                }
                Logf("[ESSB][dump][L0] target=%08X marks=%d dist=%.0f%s", actor->GetFormID(), marks, d, line.c_str());
            }
            Logf("[ESSB][dump][L0] status end marked=%d", count);
        });
    }, false);
}

// One extra full proc of the current form's element on `actor` with the DLL's formula and the target's statuses now
// (5.2 極致, N4 counter; the count stays in Papyrus until N4).
void PapyrusCastProc(RE::StaticFunctionTag*, RE::Actor* actor, bool power)
{
    Guard("CastProc", [&]() -> bool {
        return QueueNative("CastProc", [handle = HandleOf(actor), power]() {   // review fix 1: queued
        const auto held = handle.get();
        RE::Actor* actor = held.get();
        auto* player = RE::PlayerCharacter::GetSingleton();
        const int element = FormElement();
        if (!player || !actor || actor == player || actor->IsDead() || !essb::IsElement(element)) {
            return;
        }
        const auto nodes = MakeNodes(*player, true);
        Context c = MakeContext(*player, false);
        const essb::TargetFacts facts = TargetFactsOf(*actor);
        const essb::Board targetBoard = ReadBoard(*actor);
        const essb::Board selfBoard = ReadBoard(*player);
        c.in.body = ReadBody(*actor, *player, facts);
        essb::Attack attack;
        attack.element = element;
        attack.power = power || targetBoard.Has(essb::StatusKind::kDowned);
        const essb::StatusTerms terms = TermsFor(attack.power, c.tuning, targetBoard, selfBoard, c.in.body, nodes);
        essb::Plan plan;
        const bool tracing = TraceOn();   // round 26
        if (tracing) {
            Rng().Record(true);
        }
        const essb::Proc proc = essb::RollProc(element, attack, kConfig, c.tuning, c.player, facts, nodes, Rng(), terms);
        plan.Add({ essb::Cast::kProc, proc.magnitude, element, attack.power });
        if (tracing) {   // the plan's element / magnitude / crit fields are only read by the log
            plan.element = element;
            plan.magnitude = proc.magnitude;
            plan.crit = proc.crit;
            TraceProc("cast", plan, attack, -1, actor, terms.charges, terms.critBonus);
            Rng().Record(false);
        }
        Apply(*player, *actor, plan);
        });
    }, false);
}

// Round 26: the Papyrus half of the probe log (ESSBController.Probe and the MCM's buttons): one line
// "[ESSB][T][pap] kind=… who=name(0xFormID)[h m s] text", numbered in the DLL's sequence. A normal native (main thread,
// so the actor values are read safely); read-only; only while the level is 4 (Papyrus checks it before calling).
void PapyrusTrace(RE::StaticFunctionTag*, RE::BSFixedString kind, RE::Actor* actor, RE::BSFixedString text)
{
    Guard("Trace", [&]() -> bool {
        if (!TraceOn()) {
            return false;
        }
        essb::trace::Line line("pap");
        line.F(" kind=%s", kind.c_str() ? kind.c_str() : "?");
        line.Actor("who", FactsOf(actor));
        line.F(" %s", text.c_str() ? text.c_str() : "");
        Emit(line);
        return true;
    }, false, true);
}

bool RegisterPapyrus(RE::BSScript::IVirtualMachine* vm)
{
    try {
        if (!vm) {
            return false;
        }
        constexpr const char* kClass = "ESSBNative";
        vm->RegisterFunction("SetNativeHit", kClass, PapyrusSetNativeHit);
        vm->RegisterFunction("IsNativeHitActive", kClass, PapyrusIsNativeHitActive);
        vm->RegisterFunction("NativeVersion", kClass, PapyrusNativeVersion);
        vm->RegisterFunction("GetStatus", kClass, PapyrusGetStatus);
        vm->RegisterFunction("GetStatusFloat", kClass, PapyrusGetStatusFloat);
        vm->RegisterFunction("AddStatus", kClass, PapyrusAddStatus);
        vm->RegisterFunction("SetStatus", kClass, PapyrusSetStatus);
        vm->RegisterFunction("ClearStatus", kClass, PapyrusClearStatus);
        vm->RegisterFunction("SetWindow", kClass, PapyrusSetWindow);
        vm->RegisterFunction("ApplyMark", kClass, PapyrusApplyMark);
        vm->RegisterFunction("MarksOn", kClass, PapyrusMarksOn);
        vm->RegisterFunction("Burst", kClass, PapyrusBurst);
        vm->RegisterFunction("FormLeave", kClass, PapyrusFormLeave);
        vm->RegisterFunction("RequestSwitch", kClass, PapyrusRequestSwitch);
        vm->RegisterFunction("RunningSeconds", kClass, PapyrusRunningSeconds, true);   // 審查修正: an atomic read only
        vm->RegisterFunction("DumpTargets", kClass, PapyrusDumpTargets);
        vm->RegisterFunction("CastProc", kClass, PapyrusCastProc);
        vm->RegisterFunction("FormEnter", kClass, PapyrusFormEnter);
        vm->RegisterFunction("SetSync", kClass, PapyrusSetSync);
        vm->RegisterFunction("Trace", kClass, PapyrusTrace);   // round 26: the probe log's Papyrus lines
        return true;
    } catch (...) {
        Fault("Papyrus registration failed");
        return false;
    }
}

// ---------------------------------------------------------------- startup checks (before any engine call)

struct AlgorithmHandle {
    BCRYPT_ALG_HANDLE handle{};
    ~AlgorithmHandle()
    {
        if (handle) {
            BCryptCloseAlgorithmProvider(handle, 0);
        }
    }
};

struct HashHandle {
    BCRYPT_HASH_HANDLE handle{};
    ~HashHandle()
    {
        if (handle) {
            BCryptDestroyHash(handle);
        }
    }
};

// Lower-case hex SHA-256 of a file, or "" when it cannot be read.
std::string Sha256File(const char* path)
{
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        return {};
    }
    AlgorithmHandle algorithm;
    if (BCryptOpenAlgorithmProvider(&algorithm.handle, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) {
        return {};
    }
    HashHandle hash;
    if (BCryptCreateHash(algorithm.handle, &hash.handle, nullptr, 0, nullptr, 0, 0) < 0) {
        return {};
    }
    std::vector<char> buffer(1 << 16);
    while (in) {
        in.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const auto count = in.gcount();
        if (count <= 0) {
            continue;
        }
        if (BCryptHashData(hash.handle, reinterpret_cast<PUCHAR>(buffer.data()), static_cast<ULONG>(count), 0) < 0) {
            return {};
        }
    }
    if (!in.eof()) {
        return {};
    }
    unsigned char digest[32];
    if (BCryptFinishHash(hash.handle, digest, sizeof(digest), 0) < 0) {
        return {};
    }
    std::string text;
    char pair[3];
    for (const unsigned char byte : digest) {
        std::snprintf(pair, sizeof(pair), "%02x", byte);
        text += pair;
    }
    return text;
}

// Refusals here happen before SKSE::Init: the DLL must not call game code it cannot locate, so it
// cannot show a notice. ESSBController.Setup shows the generic "DLL not running" notice instead.
bool CheckRuntime(const SKSE::QueryInterface* skse)
{
    if (!skse || skse->IsEditor()) {
        Log("[ESSB][refuse] not the game runtime; native hit OFF");
        return false;
    }
    if (skse->RuntimeVersion() != REL::Version(1, 5, 97, 0) || skse->SKSEVersion() != kSkseVersion) {
        Log("[ESSB][refuse] requires Skyrim 1.5.97 + SKSE 2.0.20; native hit OFF");
        return false;
    }
    const std::string hash = Sha256File("Data/SKSE/Plugins/version-1-5-97-0.bin");
    if (hash.empty()) {
        Log("[ESSB][refuse] Address Library version-1-5-97-0.bin missing or unreadable; native hit OFF");
        return false;
    }
    if (hash != essb::addressHash) {
        Log("[ESSB][refuse] Address Library is not the verified file (SHA-256 differs); native hit OFF");
        return false;
    }
    return true;
}

}  // namespace

extern "C" __declspec(dllexport) bool SKSEPlugin_Query(const SKSE::QueryInterface* skse, SKSE::PluginInfo* info)
{
    try {
        OpenLog();
        if (!info) {
            return false;
        }
        info->infoVersion = SKSE::PluginInfo::kVersion;
        info->name = "ElementsSpellblade";
        info->version = 24;
        return CheckRuntime(skse);
    } catch (...) {
        Log("[ESSB][refuse] Query failed; native hit OFF");
        return false;
    }
}

extern "C" __declspec(dllexport) bool SKSEPlugin_Load(const SKSE::LoadInterface* skse)
{
    try {
        OpenLog();
        if (!CheckRuntime(skse)) {
            return false;
        }
        SKSE::Init(skse);
        const auto* papyrus = SKSE::GetPapyrusInterface();
        const auto* messages = SKSE::GetMessagingInterface();
        if (!papyrus || !messages) {
            Fault("SKSE interfaces unavailable");
            return false;
        }
        if (!papyrus->Register(RegisterPapyrus) || !messages->RegisterListener(Message)) {
            Fault("SKSE interface registration failed");
            return false;
        }
        Log("[ESSB][load] SKSE interfaces registered; waiting for data");
        return true;
    } catch (...) {
        Fault("Load failed");
        return false;
    }
}
