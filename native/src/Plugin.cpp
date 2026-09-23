// ElementsSpellblade.dll - native on-hit element proc for Skyrim SE 1.5.97 + SKSE 2.0.20.
//
// Hit handling runs in five stages (Handle):
//   1. read facts   ReadFacts        engine reads only
//      filter       essb::Filter     pure, HitPipeline.h
//   2. read state   essb::BuildInput pure; the engine answers the CTDA queries through Ask()
//   3. select       essb::select     pure, Selection.h
//   4. apply        Apply            CastSpellImmediate on the player's instant caster
//   5. report       Report           log line and, at debug level >= 2, an on-screen notice
// All mutable state lives in `state`. Faults latch the handler OFF until the game restarts.
#include "HitPipeline.h"
#include "ManifestData.h"

#include <Windows.h>
#include <bcrypt.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

constexpr char kPlugin[] = "Elements Spellblade.esp";
constexpr std::uint32_t kSkseVersion = 0x02000140;  // 2.0.20 packed
constexpr std::uint64_t kProcNoticeIntervalMs = 1000;
// 1.0 = the engine leaves magnitude unchanged (0x140540360); 0.0 would clamp every proc to 1 point.
constexpr float kEffectiveness = 1.0f;
constexpr float kNoMagnitudeOverride = 0.0f;

using FunctionID = RE::FUNCTION_DATA::FunctionID;
static_assert(static_cast<std::uint16_t>(essb::Fn::kGetRandomPercent) == static_cast<std::uint16_t>(FunctionID::kGetRandomPercent));
static_assert(static_cast<std::uint16_t>(essb::Fn::kIsSneaking) == static_cast<std::uint16_t>(FunctionID::kIsSneaking));
static_assert(static_cast<std::uint16_t>(essb::Fn::kGetEquippedItemType) == static_cast<std::uint16_t>(FunctionID::kGetEquippedItemType));
static_assert(static_cast<std::uint16_t>(essb::Fn::kGetActorValuePercent) == static_cast<std::uint16_t>(FunctionID::kGetActorValuePercent));
static_assert(static_cast<std::uint16_t>(essb::Fn::kIsPowerAttacking) == static_cast<std::uint16_t>(FunctionID::kIsPowerAttacking));
static_assert(static_cast<int>(RE::WEAPON_TYPE::kBow) == essb::kBow);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kStaff) == essb::kStaff);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kCrossbow) == essb::kCrossbow);

// ---------------------------------------------------------------- the only mutable state

struct Globals {
    RE::TESGlobal* enabled{};
    RE::TESGlobal* formActive{};
    RE::TESGlobal* element{};
    RE::TESGlobal* debug{};
    RE::TESGlobal* nativeHit{};
    RE::TESGlobal* wanted{};
};

struct State {
    std::atomic_bool ready{};     // manifest resolved and hit sink registered
    std::atomic_bool faulted{};   // latched until the game restarts
    std::atomic_bool inGame{};    // from PostLoadGame/NewGame until the next PreLoadGame
    std::atomic_bool handling{};  // re-entrancy guard of the hit sink
    std::atomic<std::uint64_t> lastProcNotice{};
    HANDLE log{ INVALID_HANDLE_VALUE };
    Globals globals{};
    std::array<RE::SpellItem*, essb::kKeyCount> spells{};
    // Notices raised before the HUD exists (data load). Only touched from SKSE messages (main thread).
    std::vector<std::string> deferredNotices;
};

State state;

// ---------------------------------------------------------------- log and on-screen notices

// One WriteFile per line on an append handle: there is no lock a fault could leave held.
void Log(std::string_view line) noexcept
{
    if (state.log == INVALID_HANDLE_VALUE) {
        return;
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
    state.log = CreateFileW(path.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (state.log == INVALID_HANDLE_VALUE) {
        throw std::runtime_error("Cannot open ElementsSpellblade.log");
    }
    Logf("[ESSB][load] ElementsSpellblade %s; SE 1.5.97 + SKSE 2.0.20 only; no entry-51 fallback", essb::nativeVersion);
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
        if (state.globals.nativeHit) {
            state.globals.nativeHit->value = value;
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

bool Active() noexcept
{
    if (!state.ready || state.faulted || !state.inGame || !state.globals.wanted) {
        return false;
    }
    return state.globals.wanted->value == 1.0f;
}

// ESSB_NativeHit is what Papyrus reads (ApplyProc guard, MCM status); recomputed on every state change.
void PublishStatus() noexcept
{
    WriteNativeHit(Active() ? 1.0f : 0.0f);
}

void Fault(const char* reason) noexcept
{
    state.ready = false;
    const bool first = !state.faulted.exchange(true);
    WriteNativeHit(0.0f);
    state.handling = false;
    if (!first) {
        return;
    }
    Logf("[ESSB][fault] %s; native hit OFF until the game restarts", reason);
    try {
        Notify(std::string("元素魔戰士 DLL 故障：") + reason + "。命中附傷已停用，重開遊戲前不會恢復");
    } catch (...) {
    }
}

// ---------------------------------------------------------------- stage 1: engine reads

RE::CONDITION_ITEM_DATA::OpCode ToOpCode(essb::Op op) noexcept
{
    switch (op) {
    case essb::Op::kGreaterOrEqual:
        return RE::CONDITION_ITEM_DATA::OpCode::kGreaterThanOrEqualTo;
    case essb::Op::kLess:
        return RE::CONDITION_ITEM_DATA::OpCode::kLessThan;
    default:
        return RE::CONDITION_ITEM_DATA::OpCode::kEqualTo;
    }
}

// Evaluates one CTDA condition with the same engine predicate the old ESP used (engine RNG included).
// Stack-only TESConditionItem: no TESCondition ownership, no heap allocation.
bool Ask(RE::Actor* subject, const essb::Query& query)
{
    RE::TESConditionItem item;
    item.data.functionData.function = static_cast<FunctionID>(query.fn);
    item.data.functionData.params[0] = reinterpret_cast<void*>(static_cast<std::uintptr_t>(query.param));
    item.data.comparisonValue.f = query.value;
    item.data.flags.opCode = ToOpCode(query.op);
    RE::ConditionCheckParams args(subject, subject);
    return item.IsTrue(args);
}

essb::HandFacts ReadHand(RE::PlayerCharacter& player, bool left)
{
    essb::HandFacts hand;
    auto* object = player.GetEquippedObject(left);
    auto* weapon = object ? object->As<RE::TESObjectWEAP>() : nullptr;
    hand.weaponType = weapon ? static_cast<int>(weapon->GetWeaponType()) : essb::kNoWeapon;
    const std::uint32_t side = left ? essb::kLeftHand : essb::kRightHand;
    // Same predicate as Papyrus GetEquippedItemType(hand) == 0 (empty hand or hand-to-hand weapon).
    hand.nothing = Ask(&player, essb::Query{ essb::Fn::kGetEquippedItemType, 0.0f, essb::Op::kEqual, side });
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

essb::HitFacts ReadFacts(const RE::TESHitEvent& ev, RE::PlayerCharacter& player, RE::Actor* target)
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
    facts.enabled = state.globals.enabled->value;
    facts.formActive = state.globals.formActive->value;
    facts.element = state.globals.element->value;
    return facts;
}

// ---------------------------------------------------------------- stages 4 and 5

void Apply(RE::PlayerCharacter& player, RE::SpellItem& spell, RE::Actor& target)
{
    auto* caster = player.GetMagicCaster(RE::MagicSystem::CastingSource::kInstant);
    if (!caster) {
        throw std::runtime_error("player instant caster unavailable");
    }
    // Every hit re-applies, like entry 51 did (no same-spell gate; see native-verification.md).
    caster->CastSpellImmediate(&spell, false, &target, kEffectiveness, false, kNoMagnitudeOverride, &player);
}

void Report(const essb::Key& key, const essb::Input& input, int weaponType, const RE::Actor& target, const RE::SpellItem& spell)
{
    if (state.globals.debug->value < 2.0f) {
        return;
    }
    const auto* row = essb::row(key);
    const std::string_view name = row ? row->name : std::string_view("?");
    Logf("[ESSB][hit][L2] %08X element=%d weapon=%d power=%d sneak=%d blood=%d lightning=%d spell=%08X %.*s",
        target.GetFormID(), key.element, weaponType, key.power, int(input.sneak), key.blood, key.lightning,
        spell.GetFormID(), static_cast<int>(name.size()), name.data());
    if (!ProcNoticeDue()) {
        return;
    }
    std::string text = "元素附傷：";
    text += essb::elementNames[key.element];
    text += " ";
    text += name;
    Notify(std::move(text));
}

constexpr const char* RejectName(essb::Reject reason) noexcept
{
    constexpr const char* names[] = { "accepted", "not-player", "disabled", "bash-or-blocked", "bad-target", "ally",
        "unsupported-weapon", "melee-with-projectile", "dead-target", "form-inactive", "bad-element" };
    return names[static_cast<int>(reason)];
}

// ---------------------------------------------------------------- the handler

void Handle(const RE::TESHitEvent& ev)
{
    if (!Active()) {
        return;
    }
    auto* player = RE::PlayerCharacter::GetSingleton();
    if (!player || ev.cause.get() != player) {
        return;  // every other actor's hit leaves here, before any further engine read
    }
    auto* target = ev.target ? ev.target->As<RE::Actor>() : nullptr;

    const essb::HitFacts facts = ReadFacts(ev, *player, target);
    const essb::Verdict verdict = essb::Filter(facts);
    if (verdict.reason != essb::Reject::kAccepted) {
        if (state.globals.debug->value >= 3.0f) {
            Logf("[ESSB][hit-reject][L3] reason=%s weapon=%d", RejectName(verdict.reason), verdict.weaponType);
        }
        return;
    }

    const int element = static_cast<int>(facts.element);
    const essb::Input input = essb::BuildInput(element, [player](const essb::Query& query) {
        return Ask(player, query);
    });

    const essb::Key key = essb::select(input);
    if (!key.element) {
        return;  // blood with no health band (health below 0%)
    }
    RE::SpellItem* spell = state.spells[key.index()];
    if (!spell) {
        throw std::runtime_error("selection has no manifest spell");
    }

    Apply(*player, *spell, *target);
    Report(key, input, verdict.weaponType, *target, *spell);
}

void HandleCpp(const RE::TESHitEvent* ev) noexcept
{
    try {
        if (ev) {
            Handle(*ev);
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in hit handler");
    }
}

class Sink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESHitEvent* ev, RE::BSTEventSource<RE::TESHitEvent>*) override
    {
        if (state.faulted || state.handling.exchange(true)) {
            return RE::BSEventNotifyControl::kContinue;
        }
        __try {
            HandleCpp(ev);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            Fault("access violation in hit handler");
        }
        state.handling = false;
        return RE::BSEventNotifyControl::kContinue;
    }
};

Sink sink;

// ---------------------------------------------------------------- data load

RE::TESGlobal* ResolveGlobal(RE::TESDataHandler& data, const nlohmann::json& manifest, const char* name, std::uint32_t id)
{
    if (manifest.at("globals").at(name) != id) {
        throw std::runtime_error("manifest global identity mismatch");
    }
    auto* global = data.LookupForm<RE::TESGlobal>(id, kPlugin);
    if (!global) {
        throw std::runtime_error("manifest global missing from the ESP");
    }
    return global;
}

void ResolveSpells(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    state.spells.fill(nullptr);
    std::size_t selectable = 0;
    for (const auto& row : manifest.at("spells")) {
        const auto id = row.at("local_id").get<std::uint32_t>();
        auto* spell = data.LookupForm<RE::SpellItem>(id, kPlugin);
        if (!spell) {
            throw std::runtime_error("proc spell missing from the ESP");
        }
        if (!row.at("selectable").get<bool>()) {
            continue;
        }
        const auto values = row.at("key").get<std::array<int, 5>>();
        const essb::Key key{ values[0], values[1], values[2], values[3], values[4] };
        const bool inRange = key.element >= 1 && key.element <= 11 && key.index() >= 0 && key.index() < essb::kKeyCount;
        if (!inRange || essb::spell(key) != id || state.spells[key.index()]) {
            throw std::runtime_error("manifest selection identity or duplicate mismatch");
        }
        state.spells[key.index()] = spell;
        ++selectable;
    }
    if (selectable != std::size(essb::rows)) {
        throw std::runtime_error("manifest selection table incomplete");
    }
}

void LoadManifest()
{
    auto* data = RE::TESDataHandler::GetSingleton();
    if (!data) {
        throw std::runtime_error("TESDataHandler unavailable");
    }
    state.globals.nativeHit = data->LookupForm<RE::TESGlobal>(essb::ESSB_NativeHit, kPlugin);
    WriteNativeHit(0.0f);

    std::ifstream file("Data/SKSE/Plugins/ElementsSpellblade/manifest.json");
    if (!file) {
        throw std::runtime_error("manifest.json missing");
    }
    nlohmann::json manifest;
    file >> manifest;
    const bool matches = manifest.at("schema") == 1 && manifest.at("plugin") == kPlugin &&
                         manifest.at("native_version") == essb::nativeVersion && manifest.at("runtime") == "1.5.97.0";
    if (!matches) {
        throw std::runtime_error("manifest version does not match this DLL");
    }

    state.globals.enabled = ResolveGlobal(*data, manifest, "ESSB_Enabled", essb::ESSB_Enabled);
    state.globals.formActive = ResolveGlobal(*data, manifest, "ESSB_FormActive", essb::ESSB_FormActive);
    state.globals.element = ResolveGlobal(*data, manifest, "ESSB_CurrentElement", essb::ESSB_CurrentElement);
    state.globals.debug = ResolveGlobal(*data, manifest, "ESSB_DebugLevel", essb::ESSB_DebugLevel);
    state.globals.nativeHit = ResolveGlobal(*data, manifest, "ESSB_NativeHit", essb::ESSB_NativeHit);
    state.globals.wanted = ResolveGlobal(*data, manifest, "ESSB_NativeWanted", essb::ESSB_NativeWanted);
    ResolveSpells(*data, manifest);

    auto* source = RE::ScriptEventSourceHolder::GetSingleton();
    if (!source) {
        throw std::runtime_error("hit event source unavailable");
    }
    source->AddEventSink<RE::TESHitEvent>(&sink);
    state.ready = true;
    PublishStatus();
    Log("[ESSB][load] manifest resolved; hit sink registered; waiting for a game load (MCM preference applies)");
}

// Once per game load / new game, after the HUD exists.
void AnnounceStatus()
{
    if (!state.ready || state.faulted) {
        return;  // faults were already announced (deferred or immediate)
    }
    if (state.globals.wanted->value != 1.0f) {
        Notify("元素魔戰士 DLL：命中附傷已在 MCM 關閉");
        return;
    }
    if (state.globals.debug->value >= 1.0f) {
        Notify(std::string("元素魔戰士 DLL ") + essb::nativeVersion + "：命中附傷運作中");
    }
}

void OnGameReady()
{
    state.inGame = true;
    PublishStatus();
    for (auto& text : state.deferredNotices) {
        Show(text);
    }
    state.deferredNotices.clear();
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

// ---------------------------------------------------------------- Papyrus (MCM only)

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
    if (!state.globals.wanted) {
        return;
    }
    state.globals.wanted->value = on ? 1.0f : 0.0f;
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

bool RegisterPapyrus(RE::BSScript::IVirtualMachine* vm)
{
    try {
        if (!vm) {
            return false;
        }
        vm->RegisterFunction("SetNativeHit", "ESSBNative", PapyrusSetNativeHit);
        vm->RegisterFunction("IsNativeHitActive", "ESSBNative", PapyrusIsNativeHitActive);
        vm->RegisterFunction("NativeVersion", "ESSBNative", PapyrusNativeVersion);
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
        info->version = 19;
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
