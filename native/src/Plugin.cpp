// ElementsSpellblade.dll - native on-hit handler for Skyrim SE 1.5.97 + SKSE 2.0.20.
//
// Hit handling runs in stages (Handle):
//   1. filter       ReadHitFacts + essb::Filter        which hits count (HitPipeline.h, pure)
//   2. read facts   ReadPlayer / ReadTarget / ...      engine reads only; EngineFacts.h maps them (pure)
//   3. plan         essb::PlanHit                      what to cast and how strong (HitMath.h, pure)
//   4. apply        Apply                              CastSpellImmediate, one magnitude override per spell
//   5. report       Report                             log line and, at debug level >= 2, an on-screen notice
// Round 20 (slice N2): the magnitude is computed here at hit time (it used to be pre-written into the spell
// records by Papyrus); no-form hits (baseline true damage, siphon, dispel) are handled here too.
// All mutable state lives in `state`. Faults latch the handler OFF until the game restarts.
#include "EngineFacts.h"
#include "HitPipeline.h"
#include "ManifestData.h"
#include "Selection.h"

#include <Windows.h>
#include <bcrypt.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
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

using FunctionID = RE::FUNCTION_DATA::FunctionID;
static_assert(static_cast<int>(RE::WEAPON_TYPE::kBow) == essb::kBow);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kStaff) == essb::kStaff);
static_assert(static_cast<int>(RE::WEAPON_TYPE::kCrossbow) == essb::kCrossbow);
static_assert(std::size(essb::procRows) == 2 * essb::kElementCount);

// ---------------------------------------------------------------- the only mutable state

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
    RE::BGSKeyword* undead{};
    RE::BGSKeyword* daedra{};
    RE::BGSKeyword* armorSpell{};
    RE::BGSKeyword* cloak{};
    RE::TESClass* necroClass{};
    RE::TESFaction* necroFaction{};
    std::vector<RE::BGSPerk*> mainPerks;    // [localId - kMainPerkBase]
    std::vector<RE::BGSPerk*> branchPerks;  // [localId - kBranchPerkBase]
};

struct State {
    std::atomic_bool ready{};     // manifest resolved and hit sink registered
    std::atomic_bool faulted{};   // latched until the game restarts
    std::atomic_bool inGame{};    // from PostLoadGame/NewGame until the next PreLoadGame
    std::atomic_bool handling{};  // re-entrancy guard of the hit sink (also guards `rng`)
    std::atomic_bool echoDispelQueued{};  // a consumed echo marker waits for its main-thread dispel
    std::atomic<std::uint64_t> lastProcNotice{};
    HANDLE log{ INVALID_HANDLE_VALUE };
    Forms forms{};
    std::optional<essb::SplitMix64> rng;  // damage rolls; seeded once per game process
    // Notices raised before the HUD exists (data load). Only touched from SKSE messages (main thread).
    std::vector<std::string> deferredNotices;
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
    ForEachRunningEffect(target, [&](RE::ActiveEffect&, RE::EffectSetting& effect) {
        raw.bloodMark = raw.bloodMark || &effect == f.bloodMark;
        raw.silenced = raw.silenced || &effect == f.silence;
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

// ---------------------------------------------------------------- stages 4 and 5

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

void Apply(RE::PlayerCharacter& player, RE::Actor& target, const essb::Plan& plan)
{
    auto* caster = player.GetMagicCaster(RE::MagicSystem::CastingSource::kInstant);
    if (!caster) {
        throw std::runtime_error("player instant caster unavailable");
    }
    for (int i = 0; i < plan.count; ++i) {
        const essb::CastStep& step = plan.steps[i];
        RE::SpellItem* spell = SpellOf(step);
        if (!spell) {
            throw std::runtime_error("plan asks for a spell the manifest does not have");
        }
        const float magnitude = essb::UsesOverride(step.cast) ? step.magnitude : kNoMagnitudeOverride;
        RE::TESObjectREFR* on = essb::CastsOnPlayer(step.cast) ? static_cast<RE::TESObjectREFR*>(&player) : &target;
        // Every hit re-applies, like entry 51 did (no same-spell gate; see native-verification.md).
        caster->CastSpellImmediate(spell, false, on, kEffectiveness, false, magnitude, &player);
    }
}

// Main-thread body of the echo dispel. The effects are collected first and dispelled after the walk, so the
// active-effect list is never changed while it is being iterated.
void DispelEchoCpp() noexcept
{
    try {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player || !state.forms.echoPending) {
            return;
        }
        std::vector<RE::ActiveEffect*> found;
        ForEachRunningEffect(*player, [&](RE::ActiveEffect& effect, RE::EffectSetting& base) {
            if (&base == state.forms.echoPending) {
                found.push_back(&effect);
            }
        });
        for (RE::ActiveEffect* effect : found) {
            effect->Dispel(true);
        }
    } catch (const std::exception& e) {
        Fault(e.what());
    } catch (...) {
        Fault("unknown C++ exception in echo dispel task");
    }
}

// SEH-only wrapper (no C++ objects here), the same two layers as the hit sink.
void DispelEchoGuarded() noexcept
{
    __try {
        DispelEchoCpp();
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        Fault("access violation in echo dispel task");
    }
    state.echoDispelQueued = false;
}

// The echo marker is removed on the main thread; until then ReadPlayer ignores it (no double echo).
void QueueEchoDispel()
{
    const auto* tasks = SKSE::GetTaskInterface();
    if (!tasks || state.echoDispelQueued.exchange(true)) {
        return;
    }
    tasks->AddTask([]() { DispelEchoGuarded(); });
}

std::string_view ProcName(int element, bool power)
{
    const essb::ProcRow* row = essb::FindProc(element, power);
    return row ? row->name : std::string_view("?");
}

void Report(const essb::Plan& plan, const essb::Attack& attack, int weaponType, const RE::Actor& target)
{
    if (state.forms.debug->value < 2.0f) {
        return;
    }
    Logf("[ESSB][hit][L2] %08X element=%d weapon=%d power=%d sneak=%d magnitude=%.2f crit=%d siphon=%.2f burned=%.2f casts=%d",
        target.GetFormID(), plan.element, weaponType, int(attack.power), int(attack.sneakAttack), plan.magnitude,
        int(plan.crit), plan.siphon, plan.burned, plan.count);
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

    const essb::HitFacts hit = ReadHitFacts(ev, *player, target);
    const essb::Verdict verdict = essb::Filter(hit);
    if (verdict.reason != essb::Reject::kAccepted) {
        if (state.forms.debug->value >= 3.0f) {
            Logf("[ESSB][hit-reject][L3] reason=%s weapon=%d", RejectName(verdict.reason), verdict.weaponType);
        }
        return;
    }

    const bool formActive = hit.formActive == 1.0f;
    const essb::Attack attack = essb::MakeAttack(verdict.element, ReadAttack(ev, *player, verdict.weaponType));
    const essb::Tuning tuning = essb::ReadTuning(Global);
    const essb::PlayerFacts playerFacts = ReadPlayer(*player);
    const essb::TargetFacts targetFacts = essb::MakeTarget(ReadTarget(*target));
    const auto hasPerk = [player](std::uint32_t localId) {
        return PlayerHasPerk(*player, localId);
    };
    const essb::PerkNodes nodes(hasPerk, formActive);

    const essb::Plan plan = essb::PlanHit(attack, kConfig, tuning, playerFacts, targetFacts, nodes, *state.rng);
    Apply(*player, *target, plan);
    if (plan.consumeEcho) {
        QueueEchoDispel();
    }
    Report(plan, attack, verdict.weaponType, *target);
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
    // Every spell a plan can ask for must be resolved.
    for (int cast = 0; cast <= static_cast<int>(essb::Cast::kBloodGuard); ++cast) {
        essb::CastStep step{ static_cast<essb::Cast>(cast) };
        const int variants = step.cast == essb::Cast::kSilence ? essb::kSilenceSpellCount : 1;
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

    LARGE_INTEGER counter{};
    QueryPerformanceCounter(&counter);
    state.rng.emplace(static_cast<std::uint64_t>(counter.QuadPart) ^ (GetTickCount64() << 21));

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
    if (state.forms.wanted->value != 1.0f) {
        Notify("元素魔戰士 DLL：命中附傷已在 MCM 關閉");
        return;
    }
    if (state.forms.debug->value >= 1.0f) {
        Notify(std::string("元素魔戰士 DLL ") + essb::nativeVersion + "：命中附傷運作中（命中時算強度）");
    }
}

void OnGameReady()
{
    state.inGame = true;
    state.echoDispelQueued = false;
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
        info->version = 20;
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
