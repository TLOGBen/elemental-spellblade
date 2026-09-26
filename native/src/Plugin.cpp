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
// The design state lives in those effects; `state` holds only handles, forms and faults. Faults latch the handler OFF
// until the game restarts.
#include "EngineFacts.h"
#include "HitPipeline.h"
#include "ManifestData.h"
#include "Selection.h"
#include "Status.h"
#include "StatusEngine.h"

#include <Windows.h>
#include <bcrypt.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
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

// The status layer's records, resolved (round 22). What each one stands for is Status.h's (TagOf, Lower); here only
// the local FormID <-> form pointer tables, sorted for lookup.
struct StatusForms {
    std::vector<std::pair<const RE::EffectSetting*, std::uint32_t>> effectIds;  // sorted by pointer
    std::vector<std::pair<std::uint32_t, RE::EffectSetting*>> effects;          // sorted by local id
    std::vector<std::pair<std::uint32_t, RE::SpellItem*>> spells;               // sorted by local id
    std::vector<std::pair<const RE::MagicItem*, std::uint32_t>> spellIds;        // sorted by pointer
};

struct Forms {
    RE::TESGlobal* enabled{};
    RE::TESGlobal* formActive{};
    RE::TESGlobal* element{};
    RE::TESGlobal* debug{};
    RE::TESGlobal* nativeHit{};
    RE::TESGlobal* wanted{};
    std::vector<std::pair<std::uint32_t, RE::TESGlobal*>> globals;  // every GLOB the tuning reads, by local id
    std::array<RE::SpellItem*, 2 * (essb::kElementCount + 1)> procs{};  // [element * 2 + power]
    std::vector<std::pair<std::uint32_t, RE::SpellItem*>> spells;     // cast spells, by local id
    RE::EffectSetting* bloodMark{};
    RE::EffectSetting* silence{};
    RE::EffectSetting* bloodGuard{};
    RE::EffectSetting* echoPending{};
    RE::EffectSetting* twinWindow{};
    RE::EffectSetting* riposteWindow{};
    RE::EffectSetting* hush{};
    RE::EffectSetting* hushSpent{};
    RE::BGSKeyword* undead{};
    RE::BGSKeyword* daedra{};
    RE::BGSKeyword* armorSpell{};
    RE::BGSKeyword* cloak{};
    RE::TESClass* necroClass{};
    RE::TESFaction* necroFaction{};
    std::vector<RE::BGSPerk*> mainPerks;    // [localId - kMainPerkBase]
    std::vector<RE::BGSPerk*> branchPerks;  // [localId - kBranchPerkBase]
    StatusForms status{};
    const RE::TESFile* file{};  // our plugin (the wash never strips our own effects)
};

struct State {
    std::atomic_bool ready{};     // manifest resolved and sinks registered
    std::atomic_bool faulted{};   // latched until the game restarts
    std::atomic_bool inGame{};    // from PostLoadGame/NewGame until the next PreLoadGame
    std::atomic_bool handling{};  // re-entrancy guard of the hit sink (also guards `rng`)
    std::atomic_bool echoDispelQueued{};     // a consumed echo marker waits for its main-thread dispel
    std::atomic_bool riposteDispelQueued{};  // a used 反擊 window waits for its main-thread dispel
    std::atomic_bool tickQueued{};           // one timer task at a time (a task never re-queues itself)
    std::atomic_bool stopTimer{};
    // True while this DLL dispels one of its own effects: the engine sends the removal event from inside Dispel(true)
    // (native-verification-3 s6), and those removals are ours to handle, not expiries. Main thread only.
    bool selfDispel = false;
    std::atomic<std::uint64_t> lastProcNotice{};
    std::uint64_t lastSecondMs = 0;  // cadence of the per-second timer work (main thread); not design state
    HANDLE log{ INVALID_HANDLE_VALUE };
    Forms forms{};
    std::optional<essb::SplitMix64> rng;  // damage rolls; seeded once per game process
    // Notices raised before the HUD exists (data load). Only touched from SKSE messages (main thread).
    std::vector<std::string> deferredNotices;
    DWORD mainThread = 0;
    std::array<std::atomic_bool, 5> threadLogged{};  // probe X1: each sink logs its thread once
};

State state;
constexpr essb::Config kConfig = essb::MakeConfig();

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

// Probe X1 (native-verification-3 s16): the first event of each sink logs whether it arrived on the main thread.
enum class Probe
{
    kHit,
    kRemove,
    kDeath,
    kTick,
    kNative,
};

void LogThreadOnce(Probe which, const char* name) noexcept
{
    auto& flag = state.threadLogged[static_cast<int>(which)];
    if (!flag.exchange(true)) {
        const DWORD thread = GetCurrentThreadId();
        Logf("[ESSB][X1] %s thread=%lu main=%lu %s", name, thread, state.mainThread, thread == state.mainThread ? "same" : "DIFFERENT");
    }
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
    state.handling = false;
    state.selfDispel = false;
    if (!first) {
        return;
    }
    Logf("[ESSB][fault] %s; native hit OFF until the game restarts", reason);
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

// ---------------------------------------------------------------- stages 4 and 5: casts

RE::SpellItem* SpellOf(const essb::CastStep& step)
{
    if (step.cast == essb::Cast::kProc) {
        return state.forms.procs[step.element * 2 + (step.power ? 1 : 0)];
    }
    const std::uint32_t id = essb::SpellFor(step);
    for (const auto& [localId, spell] : state.forms.spells) {
        if (localId == id) {
            return spell;
        }
    }
    return nullptr;
}

RE::MagicCaster& CasterOf(RE::PlayerCharacter& player)
{
    auto* caster = player.GetMagicCaster(RE::MagicSystem::CastingSource::kInstant);
    if (!caster) {
        throw std::runtime_error("player instant caster unavailable");
    }
    return *caster;
}

void Apply(RE::PlayerCharacter& player, RE::Actor& target, const essb::Plan& plan)
{
    auto& caster = CasterOf(player);
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
        std::vector<RE::ActiveEffect*> found;
        ForEachRunningEffect(*player, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
            if (&base == wanted) {
                found.push_back(&effect);
            }
        });
        for (RE::ActiveEffect* effect : found) {
            effect->Dispel(true);
        }
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
    "ESSB_Shatter", "ESSB_Landing", "ESSB_Rise" };
static_assert(std::size(kEventNames) == static_cast<int>(essb::Event::kCount));

void SendEvent(const essb::StatusOp& op, RE::Actor* target)
{
    auto* source = SKSE::GetModCallbackEventSource();
    if (!source) {
        throw std::runtime_error("ModEvent source unavailable");
    }
    // Fixed-point: Papyrus' String -> Float cast does not read exponents.
    char text[256];
    std::snprintf(text, sizeof(text), "%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f", op.arg[0], op.arg[1], op.arg[2], op.arg[3],
        op.arg[4], op.arg[5], op.arg[6], op.arg[7]);
    SKSE::ModCallbackEvent ev{ kEventNames[static_cast<int>(op.event)], text, op.arg[0], target };
    source->SendEvent(&ev);
}

// The write half of the engine adapter StatusEngine.h runs on: Dispel(true), CastSpellImmediate from the player's
// instant caster, the cost path, the ModEvent, the self-dispel flag the removal sink reads.
class RealEngine final : public EffectLists
{
public:
    RealEngine(RE::PlayerCharacter& player, RE::Actor* target) : EffectLists(player, target), playerCharacter_(player), caster_(CasterOf(player)) {}

    void Dispel(essb::Who, Handle effect) { effect->Dispel(true); }
    bool SelfDispel() const noexcept { return state.selfDispel; }
    void SetSelfDispel(bool on) noexcept { state.selfDispel = on; }

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
        caster_.CastSpellImmediate(SpellById(spell), false, &On(who), effectiveness, false, magnitude, &playerCharacter_);
    }

    bool Dead(essb::Who who) { return On(who).IsDead(); }

    void PayHealth(float amount)
    {
        auto* values = playerCharacter_.AsActorValueOwner();
        const float pay = (std::min)(amount, values->GetActorValue(RE::ActorValue::kHealth) - 1.0f);
        if (pay > 0.0f) {
            values->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kHealth, -pay);
        }
    }

    void Send(const essb::StatusOp& op) { SendEvent(op, target_); }

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
    }

private:
    RE::PlayerCharacter& playerCharacter_;
    RE::MagicCaster& caster_;
};

class Executor
{
public:
    Executor(RE::PlayerCharacter& player, RE::Actor* target, const essb::Tuning& tuning) : engine_(player, target), tuning_(tuning) {}

    void Run(const essb::StatusPlan& plan)
    {
        if (plan.overflow) {
            throw std::runtime_error("status plan overflow");
        }
        essb::engine::RunPlan(engine_, plan, tuning_);
    }

    // Ruling R5 (StatusEngine.h Washes); 淨潮 refunds `refund` health and magicka per removed buff. Returns the count.
    int Wash(int limit, float refund)
    {
        const int removed = essb::engine::Wash(engine_, essb::Who::kTarget, limit,
            [&](const essb::engine::EffectView& v, bool washed) { engine_.LogWash(v, washed); });
        const float amount = refund * static_cast<float>(removed) * tuning_.multRecovery;
        if (removed > 0 && amount > 0.0f) {
            engine_.Cast(essb::Who::kPlayer, essb::spell::kHeal, amount, kEffectiveness);
            engine_.Cast(essb::Who::kPlayer, essb::spell::kRestoreMagicka, amount, kEffectiveness);
        }
        return removed;
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
    return c;
}

bool FormIsActive() noexcept
{
    return state.forms.formActive->value == 1.0f;
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

void Handle(const RE::TESHitEvent& ev)
{
    if (!Active()) {
        return;
    }
    auto* player = RE::PlayerCharacter::GetSingleton();
    if (!player || ev.cause.get() != player) {
        return;  // every other actor's hit leaves here, before any further engine read
    }
    LogThreadOnce(Probe::kHit, "TESHitEvent");
    auto* target = ev.target ? ev.target->As<RE::Actor>() : nullptr;

    const essb::HitFacts hit = ReadHitFacts(ev, *player, target);
    const essb::Verdict verdict = essb::Filter(hit);
    if (verdict.reason != essb::Reject::kAccepted) {
        if (state.forms.debug->value >= 3.0f) {
            Logf("[ESSB][hit-reject][L3] reason=%s weapon=%d", RejectName(verdict.reason), verdict.weaponType);
        }
        return;
    }

    const bool formActive = hit.formActive == 1.0f;
    essb::Attack attack = essb::MakeAttack(verdict.element, ReadAttack(ev, *player, verdict.weaponType));
    const auto nodes = MakeNodes(*player, formActive);
    const essb::TargetFacts targetFacts = TargetFactsOf(*target);
    essb::Board targetBoard = ReadBoard(*target);
    essb::Board selfBoard = ReadBoard(*player);
    // v0.4 2.1: every hit on a downed target counts as a power attack (without the power attack's costs).
    if (targetBoard.Has(essb::StatusKind::kDowned)) {
        attack.power = true;
    }
    const bool iceArmor = formActive && attack.element == essb::kFrost && nodes.Has(essb::node::kFrostIceArmor);
    Context c = MakeContext(*player, iceArmor);
    c.in.body = ReadBody(*target, *player, targetFacts);

    essb::StatusTerms terms = TermsFor(attack.power, c.tuning, targetBoard, selfBoard, c.in.body, nodes);
    bool consumeStreak = false;
    if (attack.element == essb::kWind) {
        terms.windSneak = essb::WindSneakExtra(attack.sneakAttack, selfBoard, nodes, consumeStreak);
    }
    // 聖痕 (5.9): a target carrying the divine mark is judged undead / daedra for the hit's ×1.5 (review fix 4); the
    // body facts above keep the real answer for ProcTerms' +10% on the living.
    const essb::Plan plan = essb::PlanHit(attack, kConfig, c.tuning, c.player, essb::JudgedTarget(targetFacts, targetBoard, nodes), nodes,
        *state.rng, terms);
    Apply(*player, *target, plan);
    if (plan.consumeEcho) {
        QueueMarkerDispel(Marker::kEcho);
    }
    if (plan.consumeRiposte) {
        QueueMarkerDispel(Marker::kRiposte);
    }

    essb::HitStatus status;
    if (essb::IsElement(attack.element)) {
        // 雙生: a left-hand hit inside the twin window marks with the previous form's element (Papyrus did the same).
        int markElement = attack.element;
        if (attack.leftHand && c.player.twinWindow && essb::IsElement(c.tuning.twinElement)) {
            markElement = c.tuning.twinElement;
        }
        essb::StatusPlan statusPlan;
        status = essb::PlanStatusHit(statusPlan, markElement, attack.power, targetBoard, selfBoard, c.in, nodes, *state.rng);
        if (consumeStreak) {
            essb::Writer{ statusPlan, selfBoard, essb::Who::kPlayer }.Clear(essb::StatusKind::kKillStreak);   // 連殺 used up
        }
        Executor(*player, target, c.tuning).Run(statusPlan);
    }
    Report(plan, attack, verdict.weaponType, *target, status);
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

class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
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

HitSink hitSink;

// ---------------------------------------------------------------- round 22: when a status runs out

// What an expiry settles (only effects with a stub script send the event; build/fix22_records.py KINDS).
// What the removal sink read (StatusEngine.h OnRemoved: the tag, the magnitude as it left, the crystals of the same
// frame) and whom it was on; the settle task plans from it.
struct Expiry {
    RE::ActorHandle actor{};
    essb::engine::Removed removed{};
};

// 跳印 (5.2): the nearest living hostile within `radius` of `from` that carries no mark of ours (main thread only).
RE::Actor* NearestUnmarked(RE::Actor& from, RE::PlayerCharacter& player, float radius)
{
    auto* lists = RE::ProcessLists::GetSingleton();
    if (!lists) {
        return nullptr;
    }
    const RE::NiPoint3 at = from.GetPosition();
    RE::Actor* best = nullptr;
    float bestDistance = radius;
    for (auto& handle : lists->highActorHandles) {
        auto ptr = handle.get();
        RE::Actor* actor = ptr.get();
        if (!actor || actor == &from || actor->IsDead() || !actor->Is3DLoaded() || actor->IsPlayerTeammate() ||
            actor->IsCommandedActor() || !actor->IsHostileToActor(&player)) {
            continue;
        }
        const float d = actor->GetPosition().GetDistance(at);
        if (d > bestDistance) {
            continue;
        }
        const essb::Board board = ReadBoard(*actor);
        bool marked = false;
        for (int e = essb::kFire; e <= essb::kAstral && !marked; ++e) {
            marked = board.mark[e].has;
        }
        if (!marked) {
            best = actor;
            bestDistance = d;
        }
    }
    return best;
}

void SettleCpp(const Expiry& expiry) noexcept
{
    try {
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
        essb::StatusPlan plan;
        const essb::engine::Settled settled =
            essb::engine::PlanSettle(plan, expiry.removed, targetBoard, selfBoard, c.in, nodes, *state.rng);
        // 跳印：過期終焉照常結算，然後印記跳到 6 公尺內最近一個沒有印記的敵人（剩 4 秒、不開印、只跳一次）。
        if (settled.jump && target) {
            if (RE::Actor* next = NearestUnmarked(*target, *player, essb::n3::kJumpRadius)) {
                essb::Board nextBoard = ReadBoard(*next);
                essb::StatusPlan jump;
                essb::Writer{ jump, nextBoard, essb::Who::kTarget }.FlaggedMark(expiry.removed.tag.index,
                    essb::Scaled(c.tuning, essb::n3::kJumpSeconds), essb::n3::kMarkJumped);
                Executor(*player, next, c.tuning).Run(jump);
            }
        }
        Executor(*player, target, c.tuning).Run(plan);
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

// The effect-removed event arrives inside Finish(), before the effect leaves the list (native-verification-3 s2), and
// often from the actor's own effect update loop: read only here, act in a main-thread task.
void OnRemoveCpp(const RE::TESActiveEffectApplyRemoveEvent& ev) noexcept
{
    try {
        if (ev.isApplied || state.selfDispel || !Enabled() || !ev.target) {
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

// ---------------------------------------------------------------- round 22: death snapshot for the Papyrus kill hooks

// TESDeathEvent dead=false is sent inside KillImpl while the corpse still carries every effect (native-verification-3
// s10). The v0.4 death handling is N5; until then the Papyrus kill hooks (連鎖冰封, 飲血, 血承, ...) read this snapshot
// instead of the deleted registry: ESSB_Death, sender = the dying actor,
// strArg = marks bitmask | freeze | bleed layers | poison doses | curse | frozen | nether | killed by the player.
// Sent when the corpse carries a status of ours or the player is the killer (then it is also the Papyrus kill hook).
struct DeathSnapshot {
    RE::ActorHandle actor{};
    std::array<float, 8> value{};
};

void SendDeathCpp(const DeathSnapshot& snapshot) noexcept
{
    try {
        auto actorPtr = snapshot.actor.get();
        if (!actorPtr) {
            return;
        }
        essb::StatusOp op{};
        op.op = essb::Op::kEvent;
        auto* source = SKSE::GetModCallbackEventSource();
        if (!source) {
            return;
        }
        char text[256];
        const auto& v = snapshot.value;
        std::snprintf(text, sizeof(text), "%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f", v[0], v[1], v[2], v[3], v[4], v[5], v[6],
            v[7]);
        SKSE::ModCallbackEvent ev{ "ESSB_Death", text, v[0], actorPtr.get() };
        source->SendEvent(&ev);
    } catch (...) {
        Fault("unknown C++ exception in the death task");
    }
}

void SendDeathGuarded(const DeathSnapshot& snapshot) noexcept
{
    __try {
        SendDeathCpp(snapshot);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in the death task");
    }
}

void OnDeathCpp(const RE::TESDeathEvent& ev) noexcept
{
    try {
        if (ev.dead || !Enabled() || !ev.actorDying) {   // master switch (review fix 3)
            return;
        }
        auto* actor = ev.actorDying->As<RE::Actor>();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!actor || actor == player) {
            return;
        }
        LogThreadOnce(Probe::kDeath, "TESDeathEvent");
        const essb::Board board = ReadBoard(*actor);
        int marks = 0;
        for (int e = essb::kFire; e <= essb::kAstral; ++e) {
            marks |= board.mark[e].has ? (1 << e) : 0;
        }
        using K = essb::StatusKind;
        const float perDose = player ? essb::PerDose(kConfig, essb::ReadTuning(Global), MakeNodes(*player, FormIsActive())) : 0.0f;
        DeathSnapshot snapshot{ actor->GetHandle(),
            { static_cast<float>(marks), static_cast<float>(board.Layers(K::kFreeze)), static_cast<float>(board.Layers(K::kBleed)),
                static_cast<float>(essb::Doses(board, perDose)), static_cast<float>(board.Layers(K::kCurse)),
                board.Has(K::kFrozen) ? 1.0f : 0.0f, board.Has(K::kNether) ? 1.0f : 0.0f,
                ev.actorKiller.get() == player ? 1.0f : 0.0f } };
        if (marks == 0 && snapshot.value[1] + snapshot.value[2] + snapshot.value[3] + snapshot.value[4] <= 0.0f &&
            snapshot.value[7] < 0.5f) {
            return;
        }
        if (const auto* tasks = SKSE::GetTaskInterface()) {
            tasks->AddTask([snapshot]() { SendDeathGuarded(snapshot); });
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
        const auto hostiles = HostilesNear(player, source.radius);
        for (const auto& handle : hostiles) {
            auto actorPtr = handle.get();
            RE::Actor* enemy = actorPtr.get();
            if (!enemy || enemy->IsDead()) {
                continue;
            }
            essb::Board enemyBoard = ReadBoard(*enemy);
            essb::StatusPlan burn;
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
            if (!selfBoard.Has(K::kFireBath)) {
                if (!hostiles.empty() && selfBoard.Has(K::kHeat3)) {
                    essb::Writer{ self, selfBoard, essb::Who::kPlayer }.Set(K::kFireBath, static_cast<float>(hostiles.size()),
                        selfBoard[K::kHeat3].Remaining());
                }
            } else {
                self.Push(essb::Amount(essb::Op::kHeal, kConfig.damage[essb::kFire][1] * essb::n3::kFireBathHeal *
                                                             selfBoard[K::kFireBath].magnitude * c.tuning.multRecovery));
            }
        }
    }
    if (selfBoard.Has(K::kMoltenBody)) {
        self.Push(essb::Amount(essb::Op::kRestoreStamina, essb::n3::kMoltenStamina * c.tuning.multRecovery));
    }
}

// Per second, on every hostile within 50 m (round 22, until N5 owns the per-second points): 放血 (2.3: each bleed layer
// takes 0.3% of the target's CURRENT health, bosses 0.1%, +0.01% per point of 流血每層傷害, no G(L), no resist) and 瘟疫
// (5.10, 待決 in v0.4 10.4: at sync 3, a poisoned target has 5% per point to pass one dose to an enemy within 3 m; the
// v0.3 rule, now with the dose merged into that enemy's poison). Both lived in the deleted status container.
template <class Nodes>
void TargetSecond(RE::PlayerCharacter& player, const essb::Board& selfBoard, Context& c, const Nodes& nodes)
{
    using K = essb::StatusKind;
    const float drainRate = essb::n3::kBleedDrain + essb::n3::kBleedDrainPerPoint * static_cast<float>(nodes.Rank(essb::node::kBloodLayerDamage));
    const auto hostiles = HostilesNear(player, 3500.0f);
    // Gives `doses` to `to` through 2.7 擴散一劑 (the same rule as 淬毒's transfer and 濃毒): read, grow, re-apply.
    auto spread = [&](RE::Actor& to, float doses) {
        essb::Board toBoard = ReadBoard(to);
        Context tc = c;
        tc.in.body = ReadBody(to, player, TargetFactsOf(to));
        essb::StatusPlan plan;
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
        const int layers = board.Layers(K::kBleed);
        if (layers > 0 && board.bleedDot.has) {
            const bool vip = TargetFactsOf(*enemy).vip;
            const float rate = vip ? drainRate * (essb::n3::kBleedDrainVip / essb::n3::kBleedDrain) : drainRate;
            const float health = enemy->AsActorValueOwner()->GetActorValue(RE::ActorValue::kHealth);
            essb::StatusPlan drain;
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
        const bool plagueNow = plague > 0.0f && state.rng->Chance(plague);
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
                spread(*candidate, miasma);
            }
            if (d <= best) {
                best = d;
                nearest = candidate;
            }
        }
        if (plagueNow && nearest) {
            spread(*nearest, 1.0f);
        }
    }
    (void)selfBoard;
}

void TickCpp() noexcept
{
    try {
        // The master switch (ESSB_Enabled) stops the per-second work too, not only hits (round 22: the old ghost
        // statuses ignored it).
        if (!Enabled()) {
            return;
        }
        auto* ui = RE::UI::GetSingleton();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player || (ui && ui->GameIsPaused())) {
            return;
        }
        LogThreadOnce(Probe::kTick, "timer task");
        const auto nodes = MakeNodes(*player, FormIsActive());
        Context c = MakeContext(*player, false);
        essb::Board selfBoard = ReadBoard(*player);
        essb::StatusPlan plan;
        essb::PlanDecay(plan, selfBoard, c.in, nodes);
        const std::uint64_t now = GetTickCount64();
        if (now - state.lastSecondMs >= 1000) {
            state.lastSecondMs = now;
            FireSecond(*player, selfBoard, c, nodes, plan);
            TargetSecond(*player, selfBoard, c, nodes);
        }
        Executor(*player, nullptr, c.tuning).Run(plan);
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
void TimerLoop() noexcept
{
    while (!state.stopTimer) {
        std::this_thread::sleep_for(kTickInterval);
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

// ---------------------------------------------------------------- data load

std::uint32_t LocalId(const nlohmann::json& row)
{
    return row.at("local_id").get<std::uint32_t>();
}

template <class T>
T* Resolve(RE::TESDataHandler& data, std::uint32_t id, const char* file, const char* what)
{
    auto* form = data.LookupForm<T>(id, file);
    if (!form) {
        throw std::runtime_error(std::string(what) + " missing from its plugin");
    }
    return form;
}

void CheckIdentity(bool same, const char* what)
{
    if (!same) {
        throw std::runtime_error(std::string("manifest identity mismatch: ") + what);
    }
}

void ResolveGlobals(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    auto& f = state.forms;
    const auto& globals = manifest.at("globals");
    auto one = [&](const char* name, std::uint32_t id) {
        CheckIdentity(globals.at(name).get<std::uint32_t>() == id, name);
        return Resolve<RE::TESGlobal>(data, id, kPlugin, name);
    };
    f.enabled = one("ESSB_Enabled", essb::glob::kEnabled);
    f.formActive = one("ESSB_FormActive", essb::glob::kFormActive);
    f.element = one("ESSB_CurrentElement", essb::glob::kCurrentElement);
    f.debug = one("ESSB_DebugLevel", essb::glob::kDebugLevel);
    f.nativeHit = one("ESSB_NativeHit", essb::glob::kNativeHit);
    f.wanted = one("ESSB_NativeWanted", essb::glob::kNativeWanted);
    // The tuning globals: the manifest lists them by editor ID; every id ReadTuning asks for must be among them.
    f.globals.clear();
    for (const auto& [name, id] : globals.items()) {
        const auto localId = id.get<std::uint32_t>();
        f.globals.emplace_back(localId, Resolve<RE::TESGlobal>(data, localId, kPlugin, "tuning global"));
    }
    auto known = [&](std::uint32_t id) {
        return std::any_of(f.globals.begin(), f.globals.end(), [id](const auto& g) { return g.first == id; });
    };
    bool complete = true;
    essb::ReadTuning([&](std::uint32_t id) {
        complete = complete && known(id);
        return 0.0f;
    });
    CheckIdentity(complete, "tuning globals");
}

void ResolveSpells(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    auto& f = state.forms;
    f.procs.fill(nullptr);
    std::size_t procs = 0;
    for (const auto& row : manifest.at("proc_spells")) {
        const int element = row.at("element").get<int>();
        const int power = row.at("power").get<int>();
        const essb::ProcRow* compiled = essb::FindProc(element, power != 0);
        CheckIdentity(compiled && compiled->id == LocalId(row) && !f.procs[element * 2 + power], "proc spell");
        f.procs[element * 2 + power] = Resolve<RE::SpellItem>(data, LocalId(row), kPlugin, "proc spell");
        ++procs;
    }
    CheckIdentity(procs == std::size(essb::procRows), "proc spell count");
    f.spells.clear();
    for (const auto& [name, row] : manifest.at("spells").items()) {
        f.spells.emplace_back(LocalId(row), Resolve<RE::SpellItem>(data, LocalId(row), kPlugin, "cast spell"));
    }
    // Every spell a plan can ask for must be resolved (one per whole second for silence and the soaked slow).
    for (int cast = 0; cast <= static_cast<int>(essb::Cast::kBloodGuard); ++cast) {
        essb::CastStep step{ static_cast<essb::Cast>(cast) };
        const int variants = essb::DurationVariants(step.cast);
        for (int v = 1; v <= variants; ++v) {
            step.seconds = v;
            step.element = essb::kFire;
            CheckIdentity(SpellOf(step) != nullptr, "cast spell coverage");
        }
    }
}

void ResolveEffects(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    auto& f = state.forms;
    const auto& effects = manifest.at("effects");
    auto one = [&](const char* name, std::uint32_t id) {
        CheckIdentity(LocalId(effects.at(name)) == id, name);
        return Resolve<RE::EffectSetting>(data, id, kPlugin, name);
    };
    f.bloodMark = one("kBloodMark", essb::effect::kBloodMark);
    f.silence = one("kSilence", essb::effect::kSilence);
    f.bloodGuard = one("kBloodGuard", essb::effect::kBloodGuard);
    f.echoPending = one("kEchoPending", essb::effect::kEchoPending);
    f.twinWindow = one("kTwinWindow", essb::effect::kTwinWindow);
    f.riposteWindow = one("kRiposteWindow", essb::effect::kRiposteWindow);
    f.hush = one("kHush", essb::effect::kHush);
    f.hushSpent = one("kHushSpent", essb::effect::kHushSpent);

    const auto& vanilla = manifest.at("vanilla");
    auto id = [&](const char* name, std::uint32_t compiled) {
        CheckIdentity(vanilla.at(name).at("form_id").get<std::uint32_t>() == compiled, name);
        return compiled;
    };
    f.undead = Resolve<RE::BGSKeyword>(data, id("kUndeadKeyword", essb::vanilla::kUndeadKeyword), kSkyrim, "ActorTypeUndead");
    f.daedra = Resolve<RE::BGSKeyword>(data, id("kDaedraKeyword", essb::vanilla::kDaedraKeyword), kSkyrim, "ActorTypeDaedra");
    f.armorSpell = Resolve<RE::BGSKeyword>(data, id("kArmorSpellKeyword", essb::vanilla::kArmorSpellKeyword), kSkyrim, "MagicArmorSpell");
    f.cloak = Resolve<RE::BGSKeyword>(data, id("kCloakKeyword", essb::vanilla::kCloakKeyword), kSkyrim, "MagicCloak");
    f.necroClass = Resolve<RE::TESClass>(data, id("kNecroClass", essb::vanilla::kNecroClass), kSkyrim, "necromancer class");
    f.necroFaction = Resolve<RE::TESFaction>(data, id("kNecroFaction", essb::vanilla::kNecroFaction), kSkyrim, "necromancer faction");
}

// The record duration of a spell's first effect: effectiveness = wanted / this (ledger D1), so it must be the number
// Status.h was compiled with.
float RecordSeconds(const RE::SpellItem* spell)
{
    if (!spell || spell->effects.empty() || !spell->effects[0]) {
        throw std::runtime_error("status spell without an effect");
    }
    return static_cast<float>(spell->effects[0]->effectItem.duration);
}

// Round 22: every status-layer record by local FormID, checked against the manifest and the compiled table.
void ResolveStatus(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    auto& s = state.forms.status;
    s = StatusForms{};
    const auto& status = manifest.at("status");
    auto effect = [&](std::uint32_t id, const char* what) {
        auto* form = Resolve<RE::EffectSetting>(data, id, kPlugin, what);
        CheckIdentity(essb::TagOf(id).kind != essb::TagKind::kNone, what);
        s.effects.emplace_back(id, form);
        s.effectIds.emplace_back(form, id);
    };
    auto spell = [&](std::uint32_t id, const char* what, float seconds) {
        auto* form = Resolve<RE::SpellItem>(data, id, kPlugin, what);
        if (seconds > 0.0f) {
            CheckIdentity(RecordSeconds(form) == seconds, what);
        }
        s.spells.emplace_back(id, form);
    };
    const auto& kinds = status.at("kinds");
    CheckIdentity(kinds.size() == static_cast<std::size_t>(essb::kStatusKindCount), "status kind count");
    for (int k = 0; k < essb::kStatusKindCount; ++k) {
        const auto& row = kinds.at(k);
        const auto& compiled = essb::kStatusRecords[k];
        CheckIdentity(row.at("effect").get<std::uint32_t>() == compiled.effect && row.at("spell").get<std::uint32_t>() == compiled.spell &&
                          row.at("editor_id").get<std::string>() == compiled.editorId,
            "status record");
        effect(compiled.effect, "status effect");
        spell(compiled.spell, "status spell", compiled.seconds);
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        const auto& mark = status.at("marks").at(e - 1);
        CheckIdentity(mark.at("effect").get<std::uint32_t>() == essb::status::kMarkEffect[e] &&
                          mark.at("spell").get<std::uint32_t>() == essb::status::kMarkSpell[e],
            "mark record");
        effect(essb::status::kMarkEffect[e], "mark effect");
        spell(essb::status::kMarkSpell[e], "mark spell", essb::status::kMarkRecordSeconds);
        CheckIdentity(status.at("react").at(e - 1).at("spell").get<std::uint32_t>() == essb::status::kReactSpell[e], "reaction spell");
        spell(essb::status::kReactSpell[e], "reaction spell", 0.0f);
    }
    const auto& dots = status.at("dots");
    CheckIdentity(dots.at("bleed").at("effect").get<std::uint32_t>() == essb::status::kBleedDotEffect &&
                      dots.at("poison").at("effect").get<std::uint32_t>() == essb::status::kPoisonDotEffect,
        "DoT effects");
    effect(essb::status::kBleedDotEffect, "bleed DoT");
    effect(essb::status::kPoisonDotEffect, "poison DoT");
    for (int i = 0; i < essb::status::kDotMaxSeconds; ++i) {
        CheckIdentity(dots.at("bleed").at("spells").at(i).get<std::uint32_t>() == essb::status::kBleedDot[i] &&
                          dots.at("poison").at("spells").at(i).get<std::uint32_t>() == essb::status::kPoisonDot[i],
            "DoT spells");
        spell(essb::status::kBleedDot[i], "bleed DoT spell", static_cast<float>(i + 1));
        spell(essb::status::kPoisonDot[i], "poison DoT spell", static_cast<float>(i + 1));
    }
    CheckIdentity(status.at("fear").at("effect").get<std::uint32_t>() == essb::status::kFearEffect &&
                      status.at("frenzy").at("effect").get<std::uint32_t>() == essb::status::kFrenzyEffect &&
                      status.at("slow").at("effect").get<std::uint32_t>() == essb::status::kSlowEffect,
        "fear / frenzy / slow effects");
    effect(essb::status::kFearEffect, "fear effect");
    effect(essb::status::kFrenzyEffect, "frenzy effect");
    effect(essb::status::kSlowEffect, "slow effect");
    // The other spells Status.h Lower can name. The list is StatusEngine.h CastSpells() -- the native tests lower every
    // op and require each spell it names to be on that list (review: ESSB_Util_BleedTick was missing here, so the first
    // 放血 tick would have faulted the DLL).
    const auto have = [](const auto& table, std::uint32_t id) {
        return std::any_of(table.begin(), table.end(), [id](const auto& row) { return row.first == id; });
    };
    for (const std::uint32_t id : essb::engine::CastSpells()) {
        if (!have(s.spells, id)) {
            spell(id, "cast spell", 0.0f);
        }
    }
    for (const std::uint32_t id : essb::engine::TaggedEffects()) {
        CheckIdentity(have(s.effects, id), "tagged effect resolved");
    }
    std::sort(s.effectIds.begin(), s.effectIds.end());
    std::sort(s.effects.begin(), s.effects.end());
    std::sort(s.spells.begin(), s.spells.end());
    s.spells.erase(std::unique(s.spells.begin(), s.spells.end()), s.spells.end());
    for (const auto& [id, form] : s.spells) {
        s.spellIds.emplace_back(static_cast<const RE::MagicItem*>(form), id);
    }
    std::sort(s.spellIds.begin(), s.spellIds.end());
    const auto same = [](const auto& a, const auto& b) { return a.first == b.first; };
    CheckIdentity(std::adjacent_find(s.effectIds.begin(), s.effectIds.end(), same) == s.effectIds.end(), "status effects are distinct forms");
    CheckIdentity(std::adjacent_find(s.spells.begin(), s.spells.end(), same) == s.spells.end(), "status spells are distinct ids");
    state.forms.file = data.LookupModByName(kPlugin);
    CheckIdentity(state.forms.file != nullptr, "plugin file");
}

// Every rank of every main line and every branch slot; missing branch slots stay null (HasPerk false).
void ResolvePerks(RE::TESDataHandler& data, const nlohmann::json& manifest)
{
    const auto& perks = manifest.at("perks");
    CheckIdentity(perks.at("main_base").get<std::uint32_t>() == essb::kMainPerkBase &&
                      perks.at("branch_base").get<std::uint32_t>() == essb::kBranchPerkBase &&
                      perks.at("main_max_rank").get<int>() == essb::kMainMaxRank &&
                      perks.at("branch_slots").get<int>() == essb::kBranchSlots,
        "perk layout");
    auto& f = state.forms;
    f.mainPerks.assign(static_cast<std::size_t>(essb::kNodeCount * essb::kMainMaxRank), nullptr);
    f.branchPerks.assign(static_cast<std::size_t>(essb::kNodeCount * essb::kBranchSlots), nullptr);
    for (std::size_t i = 0; i < f.mainPerks.size(); ++i) {
        f.mainPerks[i] = Resolve<RE::BGSPerk>(data, essb::kMainPerkBase + static_cast<std::uint32_t>(i), kPlugin, "main-line perk");
    }
    for (std::size_t i = 0; i < f.branchPerks.size(); ++i) {
        f.branchPerks[i] = data.LookupForm<RE::BGSPerk>(essb::kBranchPerkBase + static_cast<std::uint32_t>(i), kPlugin);
    }
}

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
    const bool matches = manifest.at("schema") == 2 && manifest.at("plugin") == kPlugin &&
                         manifest.at("native_version") == essb::nativeVersion && manifest.at("runtime") == "1.5.97.0";
    if (!matches) {
        throw std::runtime_error("manifest version does not match this DLL");
    }
    ResolveGlobals(*data, manifest);
    ResolveSpells(*data, manifest);
    ResolveEffects(*data, manifest);
    ResolvePerks(*data, manifest);
    ResolveStatus(*data, manifest);

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
    state.mainThread = GetCurrentThreadId();
    Logf("[ESSB][X1] kDataLoaded thread=%lu", state.mainThread);
    std::thread(TimerLoop).detach();
    state.ready = true;
    PublishStatus();
    Log("[ESSB][load] manifest resolved; hit, effect-removed and death sinks registered; timer running");
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

void OnGameReady()
{
    state.inGame = true;
    state.echoDispelQueued = false;
    state.riposteDispelQueued = false;
    state.selfDispel = false;
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
// Windows (SetWindow): 30 嗜血 (player)   31 連殺 (player)   32 火域 / 33 冰原 / 34 星域 (target)   35 身在火域 (player)

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

// One native call on `actor`: read the boards, run `plan` (a Status.h rule), execute.
template <class Rule>
void RunRule(RE::Actor* actor, Rule&& rule)
{
    auto* player = RE::PlayerCharacter::GetSingleton();
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
    essb::StatusPlan plan;
    rule(plan, targetBoard, selfBoard, c, nodes);
    Executor(*player, target, c.tuning).Run(plan);
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
            essb::rule::AddFreeze(plan, target, static_cast<float>(delta(K::kFreeze)), false, c.in, nodes, *state.rng);
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

void PapyrusAddStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code, std::int32_t amount)
{
    Guard("AddStatus", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) { AddOrSet(plan, target, self, c, nodes, code, amount, false); });
        return true;
    }, false);
}

void PapyrusSetStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code, std::int32_t value)
{
    Guard("SetStatus", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) { AddOrSet(plan, target, self, c, nodes, code, value, true); });
        return true;
    }, false);
}

void PapyrusClearStatus(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t code)
{
    using K = essb::StatusKind;
    static constexpr std::pair<int, K> kCodes[] = { { 3, K::kFissure }, { 4, K::kUnbalance }, { 8, K::kSoak }, { 9, K::kPressure },
        { 10, K::kCurse }, { 11, K::kStar }, { 12, K::kCrystal }, { 13, K::kDowned }, { 15, K::kStarLock }, { 16, K::kCatalyzed },
        { 17, K::kDeathCurse }, { 18, K::kNether }, { 19, K::kFrozen } };
    Guard("ClearStatus", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto&, const auto&) {
            const essb::Writer tw{ plan, target, essb::Who::kTarget };
            if (code == 23) {
                essb::Writer{ plan, self, essb::Who::kPlayer }.Clear(K::kPunish);   // 懲戒 used by 裁決 (on the player)
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
                for (const auto& [c, kind] : kCodes) {
                    if (c == code) {
                        tw.Clear(kind);
                    }
                }
            }
        });
        return true;
    }, false);
}

void PapyrusSetWindow(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t window, float seconds, float magnitude)
{
    using K = essb::StatusKind;
    Guard("SetWindow", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto&) {
            const float s = essb::Scaled(c.tuning, seconds);
            switch (window) {
            case 30: essb::Writer{ plan, self, essb::Who::kPlayer }.Set(K::kBloodthirst, 1.0f, s); break;
            case 31: essb::Writer{ plan, self, essb::Who::kPlayer }.Set(K::kKillStreak, 1.0f, seconds); break;
            case 32: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kDomainFire, 1.0f, seconds); break;
            case 33: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kDomainFrost, 1.0f, seconds); break;
            case 34: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kDomainAstral, 1.0f, seconds); break;
            case 35: essb::Writer{ plan, self, essb::Who::kPlayer }.Set(K::kFireDomainPlayer, 1.0f, seconds); break;
            case 36: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kAirborne, magnitude, s); break;
            case 37: essb::Writer{ plan, target, essb::Who::kTarget }.Set(K::kFrenzyCooldown, 1.0f, essb::CooldownOf(c.tuning, seconds)); break;
            default: break;
            }
        });
        return true;
    }, false);
}

// The mark of `element` without the open reaction (傳導、聖輝、暗染、星散、風襲: "開印時附近 1 人也 X").
void PapyrusApplyMark(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t element)
{
    Guard("ApplyMark", [&]() -> bool {
        if (!essb::IsElement(element)) {
            return false;
        }
        RunRule(actor, [&](auto& plan, auto& target, auto&, auto& c, const auto& nodes) {
            essb::Writer{ plan, target, essb::Who::kTarget }.Mark(element, essb::rule::MarkSeconds(element, c.tuning, nodes, false));
        });
        return true;
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

// 融斷 (2.5): every mark (and 疊印's residual) on actors within `radius` of the player ends with reason "burst" and
// multiplier `mult`; the state part runs here, the bodies get their end events. Returns the targets settled. The v0.4
// burst scan is N5; it moved here now because the registry it used is gone (ruling R4).
std::int32_t PapyrusBurstMarks(RE::StaticFunctionTag*, float radius, float mult)
{
    return Guard("BurstMarks", [&]() -> std::int32_t {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* lists = RE::ProcessLists::GetSingleton();
        if (!player || !lists) {
            return 0;
        }
        std::vector<RE::ActorHandle> marked;
        const RE::NiPoint3 centre = player->GetPosition();
        for (auto& handle : lists->highActorHandles) {
            auto ptr = handle.get();
            RE::Actor* actor = ptr.get();
            if (actor && !actor->IsDead() && actor->GetPosition().GetDistance(centre) <= radius) {
                const essb::Board b = ReadBoard(*actor);
                if (MarksOf(b) != 0 || b.Has(essb::StatusKind::kResidual)) {
                    marked.push_back(handle);
                }
            }
        }
        std::int32_t settled = 0;
        for (auto& handle : marked) {
            auto ptr = handle.get();
            RunRule(ptr.get(), [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
                // One end-cooldown check for the whole burst of this target (like Papyrus EndBothMarks did): inside
                // it the marks just go; outside it every mark (and the residual) settles.
                const bool allowed = !target.Has(essb::StatusKind::kEndCooldown);
                const essb::Writer tw{ plan, target, essb::Who::kTarget };
                for (int e = essb::kFire; e <= essb::kAstral; ++e) {
                    if (!target.mark[e].has) {
                        continue;
                    }
                    tw.Unmark(e);
                    if (allowed) {
                        essb::PlanEndBody(plan, e, essb::EndReason::kBurst, mult, false, target, self, c.in, nodes, *state.rng);
                    }
                }
                if (target.Has(essb::StatusKind::kResidual)) {
                    const int residual = target.Layers(essb::StatusKind::kResidual);
                    tw.Clear(essb::StatusKind::kResidual);
                    if (allowed && essb::IsElement(residual)) {
                        essb::PlanEndBody(plan, residual, essb::EndReason::kBurst, mult, false, target, self, c.in, nodes, *state.rng);
                    }
                }
            });
            ++settled;
        }
        return settled;
    }, 0);
}

// Leaving a form (Papyrus OnFormSwitched / CloseForm): 洩壓 and the self ladders (Status.h OnFormLeave).
void PapyrusFormLeave(RE::StaticFunctionTag*, std::int32_t element, bool burst)
{
    Guard("FormLeave", [&]() -> bool {
        RunRule(RE::PlayerCharacter::GetSingleton(), [&](auto& plan, auto&, auto& self, auto& c, const auto& nodes) {
            essb::OnFormLeave(plan, element, burst, self, c.in, nodes);
        });
        return true;
    }, false);
}

// 火域 (5.3): entering it adds 5 s to the white-hot fuse once (Papyrus calls this on entry).
void PapyrusExtendFuse(RE::StaticFunctionTag*, float seconds)
{
    Guard("ExtendFuse", [&]() -> bool {
        RunRule(RE::PlayerCharacter::GetSingleton(), [&](auto& plan, auto&, auto& self, auto&, const auto&) {
            if (self.Has(essb::StatusKind::kHeat3)) {
                const essb::Slot fuse = self[essb::StatusKind::kHeat3];
                essb::Writer{ plan, self, essb::Who::kPlayer }.Set(essb::StatusKind::kHeat3, fuse.magnitude, fuse.Remaining() + seconds);
            }
        });
        return true;
    }, false);
}

// 大潮 (5.11): the next end on this target is ×mult (the takeover of the guide).
void PapyrusSetGuided(RE::StaticFunctionTag*, RE::Actor* actor, float mult)
{
    Guard("SetGuided", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto&, auto& c, const auto&) {
            essb::Writer{ plan, target, essb::Who::kTarget }.Set(essb::StatusKind::kGuided, mult, essb::Scaled(c.tuning, 30.0f));
        });
        return true;
    }, false);
}

// A wash of at most `limit` buffs (開印沖刷、洗滌、潮池 go through here so 淨潮 counts them). Returns the count.
std::int32_t PapyrusWashBuffs(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t limit)
{
    return Guard("WashBuffs", [&]() -> std::int32_t {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player || !actor || actor->IsDead() || actor == player) {
            return 0;
        }
        const auto nodes = MakeNodes(*player, FormIsActive());
        const essb::Tuning tuning = essb::ReadTuning(Global);
        const float refund = nodes.Has(essb::node::kWaterPurgeTide) ? 2.0f * kConfig.damage[essb::kWater][1] : 0.0f;
        return Executor(*player, actor, tuning).Wash(limit, refund);
    }, 0);
}

// Remaining damage of a DoT (strength × seconds left): 2.7 R = m × (d − t).
float PapyrusDotRemaining(RE::StaticFunctionTag*, RE::Actor* actor, bool poison)
{
    return Guard("DotRemaining", [&]() -> float {
        if (!actor) {
            return 0.0f;
        }
        const essb::Board b = ReadBoard(*actor);
        const essb::Slot& dot = poison ? b.poisonDot : b.bleedDot;
        return dot.magnitude * dot.Remaining();
    }, 0.0f, true);
}

// The death curse fuse is set by the dark end in the DLL; Papyrus keeps only its no-heal half.
// Actors with any mark of `element` (0 = any) within `radius` of `center`, nearest first, at most `limit`.
std::vector<RE::Actor*> PapyrusMarkedNear(RE::StaticFunctionTag*, RE::TESObjectREFR* center, float radius, std::int32_t limit, std::int32_t element)
{
    return Guard("MarkedNear", [&]() -> std::vector<RE::Actor*> {
        std::vector<std::pair<float, RE::Actor*>> found;
        auto* lists = RE::ProcessLists::GetSingleton();
        if (!center || !lists) {
            return {};
        }
        const RE::NiPoint3 at = center->GetPosition();
        for (auto& handle : lists->highActorHandles) {
            auto ptr = handle.get();
            RE::Actor* actor = ptr.get();
            if (!actor || actor->IsDead() || actor == center) {
                continue;
            }
            const float d = actor->GetPosition().GetDistance(at);
            if (d > radius) {
                continue;
            }
            const std::int32_t marks = MarksOf(ReadBoard(*actor));
            if (element == 0 ? marks != 0 : (marks & (1 << element)) != 0) {
                found.emplace_back(d, actor);
            }
        }
        std::sort(found.begin(), found.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        std::vector<RE::Actor*> out;
        for (const auto& [d, actor] : found) {
            if (static_cast<std::int32_t>(out.size()) >= limit) {
                break;
            }
            out.push_back(actor);
        }
        return out;
    }, std::vector<RE::Actor*>{}, true);
}

// A forced open without a hit (Papyrus 臨 and 雙斷: "對範圍內敵人各開印一次"): the mark with its cut and open.
void PapyrusForceOpen(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t element)
{
    Guard("ForceOpen", [&]() -> bool {
        if (!essb::IsElement(element) || actor == RE::PlayerCharacter::GetSingleton()) {
            return false;
        }
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
            essb::PlanStatusHit(plan, element, false, target, self, c.in, nodes, *state.rng, false);
        });
        return true;
    }, false);
}

// A chain end from a Papyrus body (連鎖終焉、焚天、冰河、山崩、雷殛…: the ranged ones are N5 scans the bodies still
// do): the state part here, then the end event with chain = 1 (no node multipliers, no further chains).
void PapyrusEndMark(RE::StaticFunctionTag*, RE::Actor* actor, std::int32_t element, std::int32_t reason, float mult)
{
    Guard("EndMark", [&]() -> bool {
        if (!essb::IsElement(element) || reason < 0 || reason > 2) {
            return false;
        }
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
            if (!target.mark[element].has) {
                return;
            }
            essb::Writer{ plan, target, essb::Who::kTarget }.Unmark(element);
            if (!target.Has(essb::StatusKind::kEndCooldown)) {
                essb::PlanEndBody(plan, element, static_cast<essb::EndReason>(reason), mult, false, target, self, c.in, nodes, *state.rng, true);
            }
        });
        return true;
    }, false);
}

// One extra full proc of the current form's element on `actor` with the DLL's formula and the target's statuses now
// (5.2 極致, N4 counter; the count stays in Papyrus until N4).
void PapyrusCastProc(RE::StaticFunctionTag*, RE::Actor* actor, bool power)
{
    Guard("CastProc", [&]() -> bool {
        auto* player = RE::PlayerCharacter::GetSingleton();
        const int element = FormElement();
        if (!player || !actor || actor == player || actor->IsDead() || !essb::IsElement(element)) {
            return false;
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
        const essb::Proc proc = essb::RollProc(element, attack, kConfig, c.tuning, c.player, facts, nodes, *state.rng, terms);
        plan.Add({ essb::Cast::kProc, proc.magnitude, element, attack.power });
        Apply(*player, *actor, plan);
        return true;
    }, false);
}

// 冰崩 / 冰河 (5.4): a frozen target nearby shatters on its own crystals (the range scan is the Papyrus body's, N5).
void PapyrusShatter(RE::StaticFunctionTag*, RE::Actor* actor)
{
    Guard("Shatter", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto&, auto& c, const auto& nodes) {
            if (target.Has(essb::StatusKind::kFrozen)) {
                essb::rule::Shatter(plan, target, c.in, nodes, 2);
            }
        });
        return true;
    }, false);
}

// 星落 (2.6): the other resonance targets' stars detonate at once (the scan is N5, in Papyrus until then).
void PapyrusDetonate(RE::StaticFunctionTag*, RE::Actor* actor)
{
    Guard("Detonate", [&]() -> bool {
        RunRule(actor, [&](auto& plan, auto& target, auto& self, auto& c, const auto& nodes) {
            if (target.Has(essb::StatusKind::kStar)) {
                essb::rule::DetonateStars(plan, target, self, c.in, nodes, 1.0f);
            }
        });
        return true;
    }, false);
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
        vm->RegisterFunction("BurstMarks", kClass, PapyrusBurstMarks);
        vm->RegisterFunction("FormLeave", kClass, PapyrusFormLeave);
        vm->RegisterFunction("ExtendFuse", kClass, PapyrusExtendFuse);
        vm->RegisterFunction("SetGuided", kClass, PapyrusSetGuided);
        vm->RegisterFunction("WashBuffs", kClass, PapyrusWashBuffs);
        vm->RegisterFunction("DotRemaining", kClass, PapyrusDotRemaining);
        vm->RegisterFunction("MarkedNear", kClass, PapyrusMarkedNear);
        vm->RegisterFunction("ForceOpen", kClass, PapyrusForceOpen);
        vm->RegisterFunction("EndMark", kClass, PapyrusEndMark);
        vm->RegisterFunction("CastProc", kClass, PapyrusCastProc);
        vm->RegisterFunction("Shatter", kClass, PapyrusShatter);
        vm->RegisterFunction("Detonate", kClass, PapyrusDetonate);
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
        info->version = 22;
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
