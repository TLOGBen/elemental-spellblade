#pragma once
// Round 23 (N4, commander ruling R5; v0.4 10.3 last row, 2.4): your three resource pools (超載、護血、蓄勁) and the sync
// bar, drawn through TrueHUD's custom widget API (LoadCustomWidgets -> RegisterNewWidgetType -> AddWidget). First
// version: colour-only bars that borrow TrueHUD's own `ResourceBar` symbol from TrueHUD_Widgets.swf (no swf of ours, no
// text labels); TrueHUD's special resource bar is never touched (Valhalla Combat owns it, build/truehud-verification.md).
//
// These are NOT TrueHUD's header: they are our own declarations of the part of its plugin interface we call, written
// from its published interface and checked against the installed TrueHUD.dll 1.1.10's PDB (llvm-pdbutil, round 23
// ledger): the IVTrueHUD1 slots in order (LoadCustomWidgets at vtable offset 96, RegisterNewWidgetType 104, AddWidget
// 112, RemoveWidget 120) and WidgetBase's layout (_view 8, _object 16, _widgetID 40, _lock 48, _taskQueue 128,
// _widgetState 168, _depth 172, sizeof 176; virtuals ~, Update, Initialize, Dispose, SetWidgetState). The static_asserts
// below pin the layout for the compiler we build with. TrueHUD stays an optional runtime dependency: no TrueHUD.dll, or
// no RequestPluginAPI export, and nothing is drawn (silently).
//
// Threads: the values are written by the DLL's main-thread timer task (Publish) and read by TrueHUD's UI thread
// (PoolBar::Update) through atomics; the API calls themselves only queue HUD tasks inside TrueHUD.
#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>

#include <Windows.h>
#include <winver.h>   // GetFileVersionInfo (round 23 review: the version gate)

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <queue>
#include <string_view>
#include <vector>

namespace essb::hud {

enum class ApiResult : std::uint8_t
{
    kOk,
    kNotOwner,
    kMustKeep,
    kAlreadyGiven,
    kAlreadyTaken,
    kWidgetFailedToLoad,
    kBadThread,
};

enum class RemovalMode : std::uint8_t
{
    kImmediate,
    kNormal,
    kDelayed,
};

// TrueHUD owns the widget object it gets from AddWidget and calls these virtuals on its UI thread.
class WidgetBase
{
public:
    enum WidgetState : std::uint8_t
    {
        kActive = 0,
        kPendingHide = 1,
        kHidden = 2,
        kDelayedRemoval = 3,
        kPendingRemoval = 4,
        kRemoved = 5,
    };

    WidgetBase() = default;
    virtual ~WidgetBase() = default;
    virtual void Update(float a_deltaTime) = 0;
    virtual void Initialize() = 0;
    virtual void Dispose() = 0;
    virtual void SetWidgetState(WidgetState a_state) { widgetState = a_state; }

    RE::GPtr<RE::GFxMovieView> view;
    RE::GFxValue object;
    std::uint32_t widgetID = 0;
    mutable std::recursive_mutex lock;
    std::queue<std::function<void()>> tasks;   // TrueHUD's ProcessDelegates drains it; we never queue anything
    WidgetState widgetState = kHidden;
    float depth = 0.0f;
};

static_assert(sizeof(WidgetBase) == 176, "WidgetBase layout differs from TrueHUD 1.1.10 (PDB)");
static_assert(offsetof(WidgetBase, view) == 8 && offsetof(WidgetBase, object) == 16 && offsetof(WidgetBase, widgetID) == 40 &&
                  offsetof(WidgetBase, lock) == 48 && offsetof(WidgetBase, tasks) == 128 && offsetof(WidgetBase, widgetState) == 168 &&
                  offsetof(WidgetBase, depth) == 172,
    "WidgetBase field offsets differ from TrueHUD 1.1.10 (PDB)");

// TrueHUD's plugin interface, version 1 (the singleton RequestPluginAPI returns answers every version with the same
// object, so version 1 is the one every TrueHUD that has the export understands). Slots in the DLL's order.
class Api
{
public:
    [[nodiscard]] virtual unsigned long GetTrueHUDThreadId() const noexcept = 0;
    [[nodiscard]] virtual ApiResult RequestTargetControl(SKSE::PluginHandle a_plugin) noexcept = 0;
    [[nodiscard]] virtual ApiResult RequestSpecialResourceBarsControl(SKSE::PluginHandle a_plugin) noexcept = 0;   // never called
    virtual ApiResult SetTarget(SKSE::PluginHandle a_plugin, RE::ActorHandle a_actor) noexcept = 0;
    virtual ApiResult SetSoftTarget(SKSE::PluginHandle a_plugin, RE::ActorHandle a_actor) noexcept = 0;
    virtual void AddActorInfoBar(RE::ActorHandle a_actor) noexcept = 0;
    virtual void RemoveActorInfoBar(RE::ActorHandle a_actor, RemovalMode a_mode) noexcept = 0;
    virtual void AddBoss(RE::ActorHandle a_actor) noexcept = 0;
    virtual void RemoveBoss(RE::ActorHandle a_actor, RemovalMode a_mode) noexcept = 0;
    virtual void FlashActorValue(RE::ActorHandle a_actor, RE::ActorValue a_value, bool a_long) noexcept = 0;
    virtual ApiResult FlashActorSpecialBar(SKSE::PluginHandle a_plugin, RE::ActorHandle a_actor, bool a_long) noexcept = 0;
    virtual ApiResult RegisterSpecialResourceFunctions(SKSE::PluginHandle a_plugin, std::function<float(RE::Actor*)>&& a_current,
        std::function<float(RE::Actor*)>&& a_max, bool a_specialMode, bool a_forPlayer) noexcept = 0;   // never called
    virtual void LoadCustomWidgets(SKSE::PluginHandle a_plugin, std::string_view a_path, std::function<void(ApiResult)>&& a_done) noexcept = 0;
    virtual void RegisterNewWidgetType(SKSE::PluginHandle a_plugin, std::uint32_t a_type) noexcept = 0;
    virtual void AddWidget(SKSE::PluginHandle a_plugin, std::uint32_t a_type, std::uint32_t a_id, std::string_view a_symbol,
        std::shared_ptr<WidgetBase> a_widget) noexcept = 0;
    virtual void RemoveWidget(SKSE::PluginHandle a_plugin, std::uint32_t a_type, std::uint32_t a_id, RemovalMode a_mode) noexcept = 0;
};

// ---------------------------------------------------------------- the bars

inline constexpr std::uint32_t kWidgetType = 0x45535342;   // 'ESSB'
inline constexpr int kBarCount = 4;
inline constexpr std::array<std::uint32_t, kBarCount> kColors{ 0x8A2BE2, 0x8B0000, 0xC8A040, 0x88CCFF };   // 超載、護血、蓄勁、同調
inline constexpr std::string_view kSwf = "TrueHUD_Widgets.swf";
inline constexpr std::string_view kSymbol = "ResourceBar";

// What the timer task publishes (current, full) per bar; 0 full hides the bar.
struct Values {
    std::array<std::atomic<float>, kBarCount> current{};
    std::array<std::atomic<float>, kBarCount> full{};
};

inline Values& Shared() noexcept
{
    static Values values;
    return values;
}

inline void Publish(int bar, float current, float full) noexcept
{
    Shared().current[bar].store(current, std::memory_order_relaxed);
    Shared().full[bar].store(full, std::memory_order_relaxed);
}

class PoolBar final : public WidgetBase
{
public:
    explicit PoolBar(int a_bar) : bar_(a_bar) {}

    // TrueHUD calls these on its UI thread: a C++ catch inside, an SEH frame outside (the round-22 crash guards), so a
    // failure here can only leave a bar undrawn.
    void Initialize() override { Seh(&PoolBar::InitCpp, this); }
    void Update(float) override { Seh(&PoolBar::RefreshCpp, this); }
    void Dispose() override {}

private:
    static void Seh(void (*fn)(PoolBar*) noexcept, PoolBar* self) noexcept
    {
        __try {
            fn(self);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
        }
    }

    static void InitCpp(PoolBar* self) noexcept
    {
        try {
            self->Init();
        } catch (...) {
        }
    }

    static void RefreshCpp(PoolBar* self) noexcept
    {
        try {
            self->Refresh();
        } catch (...) {
        }
    }

    void Init()
    {
        if (!object.IsDisplayObject()) {
            return;
        }
        // TrueHUD_Bar.init(showPhantom, phantomDuration, direction, standalone, shadow, shapeMask, flash, penaltyBar)
        const std::array<RE::GFxValue, 8> init{ RE::GFxValue(false), RE::GFxValue(0.0), RE::GFxValue(0.0), RE::GFxValue(true),
            RE::GFxValue(false), RE::GFxValue(false), RE::GFxValue(false), RE::GFxValue(false) };
        object.Invoke("init", init);
        const double colour = static_cast<double>(kColors[bar_]);
        const std::array<RE::GFxValue, 5> colours{ RE::GFxValue(colour), RE::GFxValue(colour), RE::GFxValue(0.0), RE::GFxValue(colour),
            RE::GFxValue(16777215.0) };
        object.Invoke("setColor", colours);
        const std::array<RE::GFxValue, 1> width{ RE::GFxValue(150.0) };
        object.Invoke("setWidth", width);
        double stageW = 1280.0;
        double stageH = 720.0;
        if (view) {
            const RE::GRectF rect = view->GetVisibleFrameRect();
            stageW = rect.right - rect.left;
            stageH = rect.bottom - rect.top;
        }
        // Right of centre, above the bottom edge: clear of the (Untarnished UI) combined player widget at the left.
        object.SetMember("_x", RE::GFxValue(stageW * 0.62));
        object.SetMember("_y", RE::GFxValue(stageH * (0.93 - 0.022 * static_cast<double>(bar_))));
        object.SetMember("_visible", RE::GFxValue(false));
        shown_ = false;
        percent_ = -1.0;
    }

    void Refresh()
    {
        if (!object.IsDisplayObject()) {
            return;
        }
        const float full = Shared().full[bar_].load(std::memory_order_relaxed);
        const float current = Shared().current[bar_].load(std::memory_order_relaxed);
        const bool show = full > 0.0f && current > 0.0f;   // 空池隱藏
        if (show != shown_) {
            object.SetMember("_visible", RE::GFxValue(show));
            shown_ = show;
        }
        if (!show) {
            return;
        }
        const double percent = std::clamp(static_cast<double>(current / full), 0.0, 1.0);
        if (percent != percent_) {
            const std::array<RE::GFxValue, 2> args{ RE::GFxValue(percent), RE::GFxValue(false) };
            object.Invoke("updatePercent", args);
            percent_ = percent;
        }
    }

    int bar_;
    bool shown_ = false;
    double percent_ = -1.0;
};

// The API and the add state. All on the main thread except `loaded` (TrueHUD's callback).
struct Link {
    Api* api = nullptr;
    SKSE::PluginHandle plugin = SKSE::kInvalidPluginHandle;
    std::atomic_bool loaded{};     // LoadCustomWidgets said OK
    std::atomic_bool requested{};  // a load is on its way
    bool added = false;            // the bars were added since the last load
    int waitTicks = 0;             // AddWidget waits a tick after the load (the loadClip is asynchronous)
    int pendingTicks = 0;          // timer ticks since the load was requested (review: TrueHUD may never call back)
};

// The oldest TrueHUD whose interface the declarations above were checked against (the installed 1.1.10's PDB).
inline constexpr std::uint64_t kMinVersion = (1ull << 48) | (1ull << 32) | (10ull << 16);
inline constexpr int kLoadTimeoutTicks = 100;   // 10 s of the 100 ms timer: a load with no answer is given up and retried

// TrueHUD.dll's file version (VS_FIXEDFILEINFO: major.minor.patch.build packed high to low), 0 when it cannot be read.
inline std::uint64_t FileVersion(HMODULE module) noexcept
{
    wchar_t path[MAX_PATH]{};
    if (!GetModuleFileNameW(module, path, MAX_PATH)) {
        return 0;
    }
    DWORD ignored = 0;
    const DWORD size = GetFileVersionInfoSizeW(path, &ignored);
    if (size == 0) {
        return 0;
    }
    std::vector<std::byte> data(size);
    if (!GetFileVersionInfoW(path, 0, size, data.data())) {
        return 0;
    }
    VS_FIXEDFILEINFO* info = nullptr;
    UINT length = 0;
    if (!VerQueryValueW(data.data(), L"\\", reinterpret_cast<void**>(&info), &length) || !info || length < sizeof(VS_FIXEDFILEINFO)) {
        return 0;
    }
    return (static_cast<std::uint64_t>(info->dwFileVersionMS) << 32) | info->dwFileVersionLS;
}

inline Link& Hud() noexcept
{
    static Link link;
    return link;
}

// At SKSE kPostLoad / kDataLoaded: find TrueHUD. Nothing (and no error) when it is absent or too old.
inline bool Find() noexcept
{
    try {
        HMODULE module = GetModuleHandleW(L"TrueHUD.dll");
        if (!module) {
            return false;
        }
        if (FileVersion(module) < kMinVersion) {
            return false;   // older than the TrueHUD these declarations were checked against: no widgets (silently)
        }
        using Request = void* (*)(std::uint8_t);
        const auto request = reinterpret_cast<Request>(GetProcAddress(module, "RequestPluginAPI"));
        if (!request) {
            return false;
        }
        Hud().api = static_cast<Api*>(request(0));   // InterfaceVersion::V1
        Hud().plugin = SKSE::GetPluginHandle();
        return Hud().api != nullptr;
    } catch (...) {
        Hud().api = nullptr;
        return false;
    }
}

// A new load: at game load and whenever TrueHUD's menu opens (its OnClose removed every custom widget).
inline void Reload() noexcept
{
    Link& h = Hud();
    if (!h.api || h.requested.exchange(true)) {
        return;
    }
    h.loaded = false;
    h.added = false;
    h.waitTicks = 0;
    h.pendingTicks = 0;
    h.api->LoadCustomWidgets(h.plugin, kSwf, [](ApiResult result) {
        Hud().loaded = result == ApiResult::kOk;
        Hud().requested = false;
    });
}

// Once per timer tick (main thread): add the bars one tick after the load finished.
inline void Tick() noexcept
{
    Link& h = Hud();
    if (!h.api || h.added) {
        return;
    }
    if (!h.loaded) {
        // TrueHUD never answered the load (review): give up this request after the timeout and ask again.
        if (h.requested && ++h.pendingTicks >= kLoadTimeoutTicks) {
            h.requested = false;
            Reload();
        }
        return;
    }
    if (++h.waitTicks < 2) {
        return;
    }
    h.api->RegisterNewWidgetType(h.plugin, kWidgetType);
    for (int bar = 0; bar < kBarCount; ++bar) {
        h.api->AddWidget(h.plugin, kWidgetType, static_cast<std::uint32_t>(bar), kSymbol, std::make_shared<PoolBar>(bar));
    }
    h.added = true;
}

}  // namespace essb::hud
