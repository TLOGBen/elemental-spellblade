#pragma once
// Round 25 hotfix: the data-load resolution of the DLL (was Plugin.cpp ResolveGlobals .. ResolveDomains), written against
// an abstract form source so the native tests run the SAME code on the written ESP and manifest
// (native/tests/load_test.cpp, run by build/fix25_verify.py on build/fix25-load-forms.json).
//
// Why: 0.25.0 faulted in the game at data load ("manifest identity mismatch: tagged effect resolved"). TaggedEffects()
// names the 護血 pool (round 23) and 寂 (round 24), but ResolveStatus registered neither in the status effect table;
// every offline test only checked that an id was ON the list, never that the loader registered it, because the loader
// itself could not run offline. Now it can: Plugin.cpp keeps only the adapter (GameForms) and calls LoadForms.
//
// Every failed check is reported with what failed: the FormID (local and at the plugin's runtime index), the EditorID
// the manifest gives it, the record type the DLL expects and which check. The load goes on after a failure where that is
// safe, so ONE run lists every problem; LoadForms then throws (Plugin.cpp: the latched fault, native hit OFF).
//
// D (the form source) provides:
//   types        Global, Spell, Magic (a base of Spell), Effect, Keyword, Class, Faction, Perk, Hazard, File
//   Lookup<T>    (local FormID, file name) -> T*, nullptr when missing or of another type (TESDataHandler::LookupForm)
//   KindOf       (local FormID, file name) -> the record type there ("MGEF"), "" when there is none
//   RuntimeId    (local FormID, file name) -> the FormID at the file's load-order index, std::nullopt when not loaded
//   Mod          file name -> const File*, nullptr when not loaded
//   FirstSeconds the duration of a spell's first effect, std::nullopt when it has none
//   SpawnsHazard whether an effect is a Spawn Hazard effect whose associated form is that hazard
//   Report       one failure line (Plugin.cpp: the log; load_test: stdout)
#include "EngineFacts.h"
#include "ManifestData.h"
#include "Selection.h"
#include "Status.h"
#include "StatusEngine.h"
#include "Timer.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

namespace essb::load {

inline constexpr char kPlugin[] = "Elements Spellblade.esp";
inline constexpr char kSkyrim[] = "Skyrim.esm";

// The status layer's records, resolved (round 22). What each one stands for is Status.h's (TagOf, Lower); here only
// the local FormID <-> form pointer tables, sorted for lookup.
template <class D>
struct StatusForms {
    std::vector<std::pair<const typename D::Effect*, std::uint32_t>> effectIds;  // sorted by pointer
    std::vector<std::pair<std::uint32_t, typename D::Effect*>> effects;          // sorted by local id
    std::vector<std::pair<std::uint32_t, typename D::Spell*>> spells;            // sorted by local id
    std::vector<std::pair<const typename D::Magic*, std::uint32_t>> spellIds;    // sorted by pointer
};

template <class D>
struct Forms {
    using Global = typename D::Global;
    using Spell = typename D::Spell;
    using Effect = typename D::Effect;
    using Keyword = typename D::Keyword;
    Global* enabled{};
    Global* formActive{};
    Global* element{};
    Global* debug{};
    Global* nativeHit{};
    Global* wanted{};
    std::vector<std::pair<std::uint32_t, Global*>> globals;  // every GLOB the tuning reads, by local id
    std::array<Spell*, 2 * (kElementCount + 1)> procs{};  // [element * 2 + power]
    std::vector<std::pair<std::uint32_t, Spell*>> spells;  // cast spells, by local id
    Effect* bloodMark{};
    Effect* silence{};
    Effect* bloodGuard{};
    Effect* echoPending{};
    Effect* twinWindow{};
    Effect* riposteWindow{};
    Effect* hush{};
    Effect* hushSpent{};
    Effect* manaBreak{};           // round 23: 反咒 (the caster carries your 滅法印)
    std::array<Keyword*, 3> destructive{};   // MagicDamageFire / Frost / Shock: the pools' spell half
    // Round 23: the mirrors of your resources the PERK conditions and Papyrus read (the DLL is their only writer).
    Global* mirrorSync{};
    Global* mirrorStage{};
    Global* mirrorCharge{};
    Global* mirrorResolve{};
    Global* mirrorIceShield{};
    Global* mirrorRock{};
    Global* mirrorWind{};
    Global* mirrorBracing{};
    Keyword* undead{};
    Keyword* daedra{};
    Keyword* armorSpell{};
    Keyword* cloak{};
    Keyword* dragon{};        // round 24: ActorTypeDragon (never knocked, raised or turned to ash)
    Effect* engaged{};    // round 24: 2.9 你主動攻擊過的目標 (ESSB_EngagedEffect, 30 s)
    Effect* reanimate{};  // round 24: your raised servant (ESSB_ReanimateEffect; 亡衛)
    // Round 25 (N6): the domains (build/fix25_records.py): [element] -> the HAZD and its Spawn Hazard effect (null: none).
    std::array<typename D::Hazard*, kElementCount + 1> domainHazards{};
    std::array<Effect*, kElementCount + 1> domainSpawn{};
    // Round 25: the globals the timer and the hotkeys write or read (the DLL is the only writer of the first four).
    Global* envWet{};
    Global* envStormy{};   // 暴風雪 (the hit path's 凍結累積 ×2)
    Global* envThunder{};  // 審查修正: 雷雨 (the storm charge)
    Global* envNight{};
    Global* freeOpen{};             // ESSB_FreeOpen: 免門檻 (Papyrus sets it after a burst; opening uses it up)
    Global* hotkeysEnabled{};
    Global* formNotify{};
    std::array<Global*, kElementCount> hotkeys{};
    typename D::Class* necroClass{};
    typename D::Faction* necroFaction{};
    std::vector<typename D::Perk*> mainPerks;    // [localId - kMainPerkBase]
    std::vector<typename D::Perk*> branchPerks;  // [localId - kBranchPerkBase]
    StatusForms<D> status{};
    const typename D::File* file{};  // our plugin (the wash never strips our own effects)
};

// What one load resolved (logged in one line at data load).
struct Summary {
    int globals = 0;        // GLOB, by the manifest (the named ones are among them)
    int procSpells = 0;
    int castSpells = 0;     // the hit path's (manifest "spells")
    int effects = 0;        // the named MGEFs of ResolveEffects
    int vanilla = 0;        // Skyrim.esm keywords / class / faction
    int mainPerks = 0;
    int branchPerks = 0;    // present branch slots (a missing slot is allowed)
    int statusEffects = 0;  // the status effect table (TagOf's effects)
    int statusSpells = 0;   // the status spell table (Lower's spells, CastSpells)
    int hazards = 0;
    int spawnEffects = 0;
    std::uint32_t pluginIndex = 0;  // the plugin's runtime FormID prefix (0x05000000 for load-order index 5)
    std::vector<std::string> failures;
};

template <class T, class D>
constexpr const char* SigOf()
{
    if constexpr (std::is_same_v<T, typename D::Global>) {
        return "GLOB";
    } else if constexpr (std::is_same_v<T, typename D::Spell>) {
        return "SPEL";
    } else if constexpr (std::is_same_v<T, typename D::Effect>) {
        return "MGEF";
    } else if constexpr (std::is_same_v<T, typename D::Keyword>) {
        return "KYWD";
    } else if constexpr (std::is_same_v<T, typename D::Class>) {
        return "CLAS";
    } else if constexpr (std::is_same_v<T, typename D::Faction>) {
        return "FACT";
    } else if constexpr (std::is_same_v<T, typename D::Perk>) {
        return "PERK";
    } else {
        static_assert(std::is_same_v<T, typename D::Hazard>, "a record type the loader does not know");
        return "HAZD";
    }
}

inline std::string Hex(std::uint32_t value, int digits)
{
    char text[16];
    std::snprintf(text, sizeof(text), "0x%0*X", digits, value);
    return text;
}

inline std::uint32_t LocalId(const nlohmann::json& row)
{
    return row.at("local_id").get<std::uint32_t>();
}

// The failure list and the words that name a record in it.
template <class D>
class Diag
{
public:
    Diag(D& data, const nlohmann::json& manifest, Summary& summary) : data_(data), summary_(summary)
    {
        // manifest "records": local id (6 hex digits) -> [EditorID, record type] of every record the plugin has
        // (build/fix19_native.py manifest); only used to name what failed.
        if (const auto it = manifest.find("records"); it != manifest.end()) {
            for (const auto& [key, row] : it->items()) {
                names_.emplace(static_cast<std::uint32_t>(std::stoul(key, nullptr, 16)), row.at(0).get<std::string>());
            }
        }
        if (const auto it = manifest.find("vanilla"); it != manifest.end()) {
            for (const auto& [name, row] : it->items()) {
                vanilla_.emplace(row.at("form_id").get<std::uint32_t>(), name);
            }
        }
    }

    // "0x005303 (runtime 0x05005303) ESSB_BloodGuardEffect in Elements Spellblade.esp"
    std::string Name(std::uint32_t local, const char* file) const
    {
        std::string out = Hex(local, 6);
        const std::optional<std::uint32_t> runtime = data_.RuntimeId(local, file);
        out += runtime ? " (runtime " + Hex(*runtime, 8) + ")" : std::string(" (runtime ?: ") + file + " is not loaded)";
        const bool ours = std::string(file) == kPlugin;
        const auto& table = ours ? names_ : vanilla_;
        const auto it = table.find(local);
        out += it != table.end() ? " " + it->second : std::string(" (no EditorID in the manifest)");
        return out + " in " + file;
    }

    // What is at that FormID, for a record that did not resolve as the expected type.
    std::string Found(std::uint32_t local, const char* file) const
    {
        const std::string kind = data_.KindOf(local, file);
        return kind.empty() ? std::string("no such record") : "the record there is a " + kind;
    }

    void Fail(std::string line)
    {
        data_.Report(line);
        summary_.failures.push_back(std::move(line));
    }

    // An aggregate check (no single record to name).
    bool Check(bool same, const std::string& what)
    {
        if (!same) {
            Fail("manifest identity mismatch: " + what);
        }
        return same;
    }

    // A check about one record: "<what>: <name> expected <SIG>, <detail>".
    bool CheckId(bool same, const char* what, std::uint32_t local, const char* file, const char* sig, const std::string& detail)
    {
        if (!same) {
            Fail(std::string("manifest identity mismatch: ") + what + ": " + Name(local, file) + " expected " + sig + ", " + detail);
        }
        return same;
    }

    // The manifest names another FormID than the DLL was compiled with.
    bool Same(std::uint32_t manifest, std::uint32_t compiled, const char* what, const char* file, const char* sig)
    {
        return CheckId(manifest == compiled, what, compiled, file, sig,
            "the manifest names " + Hex(manifest, 6) + " (the DLL and the manifest are from different builds)");
    }

    template <class T>
    T* Resolve(std::uint32_t id, const char* file, const char* what)
    {
        auto* form = data_.template Lookup<T>(id, file);
        if (!form) {
            Fail(std::string("record missing: ") + what + ": " + Name(id, file) + " expected " + SigOf<T, D>() + ", " + Found(id, file));
        }
        return form;
    }

    D& data() { return data_; }

private:
    D& data_;
    Summary& summary_;
    std::unordered_map<std::uint32_t, std::string> names_;
    std::unordered_map<std::uint32_t, std::string> vanilla_;
};

// A manifest value in a failure line (json::dump is not used: its template trips /W4 C4459 next to Plugin.cpp's `state`).
inline std::string Text(const nlohmann::json& value)
{
    if (value.is_string()) {
        return value.get<std::string>();
    }
    if (value.is_number_integer()) {
        return std::to_string(value.get<long long>());
    }
    return std::string("(a JSON ") + value.type_name() + ")";
}

inline void CheckVersion(const nlohmann::json& manifest)
{
    const bool matches = manifest.at("schema") == 2 && manifest.at("plugin") == kPlugin &&
                         manifest.at("native_version") == nativeVersion && manifest.at("runtime") == "1.5.97.0";
    if (!matches) {
        throw std::runtime_error("manifest version does not match this DLL: manifest schema " + Text(manifest.at("schema")) +
                                 ", plugin " + Text(manifest.at("plugin")) + ", native_version " +
                                 Text(manifest.at("native_version")) + ", runtime " + Text(manifest.at("runtime")) +
                                 "; this DLL is " + nativeVersion + " for " + kPlugin + " on 1.5.97.0");
    }
}

// The spell a plan step casts, from the resolved tables (nullptr: not resolved).
template <class D>
typename D::Spell* SpellOf(const Forms<D>& f, const CastStep& step)
{
    if (step.cast == Cast::kProc) {
        return f.procs[step.element * 2 + (step.power ? 1 : 0)];
    }
    const std::uint32_t id = SpellFor(step);
    for (const auto& [localId, spell] : f.spells) {
        if (localId == id) {
            return spell;
        }
    }
    return nullptr;
}

template <class D>
void ResolveGlobals(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& f, Summary& sum)
{
    using Global = typename D::Global;
    const auto& globals = manifest.at("globals");
    auto one = [&](const char* name, std::uint32_t id) {
        d.Same(globals.at(name).get<std::uint32_t>(), id, name, kPlugin, "GLOB");
        return d.template Resolve<Global>(id, kPlugin, name);
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
        if (auto* form = d.template Resolve<Global>(localId, kPlugin, "tuning global")) {
            f.globals.emplace_back(localId, form);
        }
    }
    sum.globals = static_cast<int>(f.globals.size());
    auto known = [&](std::uint32_t id) {
        return std::any_of(f.globals.begin(), f.globals.end(), [id](const auto& g) { return g.first == id; });
    };
    ReadTuning([&](std::uint32_t id) {
        d.CheckId(known(id), "tuning globals", id, kPlugin, "GLOB", "ReadTuning reads it but it did not resolve from the manifest's globals");
        return 0.0f;
    });
    // Round 23: the mirrors the DLL writes (v0.4 2.3), by the manifest's editor IDs.
    f.mirrorSync = one("ESSB_Sync", essb::glob::kSync);
    f.mirrorStage = one("ESSB_SyncStage", essb::glob::kSyncStage);
    f.mirrorCharge = one("ESSB_Charge", essb::glob::kCharge);
    f.mirrorResolve = one("ESSB_Resolve", essb::glob::kResolve);
    f.mirrorIceShield = one("ESSB_IceShield", essb::glob::kIceShield);
    f.mirrorRock = one("ESSB_RockArmor", essb::glob::kRockArmor);
    f.mirrorWind = one("ESSB_Wind", essb::glob::kWind);
    f.mirrorBracing = one("ESSB_Bracing", essb::glob::kBracing);
    // Round 25 (N6): the environment (the DLL writes it; 審查修正: ESSB_EnvThunder), 免門檻, the hotkeys and the tuning the
    // timer reads.
    f.envWet = one("ESSB_EnvWet", essb::glob::kEnvWet);
    f.envStormy = one("ESSB_EnvStormy", essb::glob::kEnvStormy);
    f.envThunder = one("ESSB_EnvThunder", essb::glob::kEnvThunder);
    f.envNight = one("ESSB_EnvNight", essb::glob::kEnvNight);
    f.freeOpen = one("ESSB_FreeOpen", essb::glob::kFreeOpen);
    f.hotkeysEnabled = one("ESSB_HotkeysEnabled", essb::glob::kHotkeysEnabled);
    f.formNotify = one("ESSB_FormNotify", essb::glob::kFormNotify);
    static constexpr const char* kHotkeyNames[kElementCount] = { "ESSB_Hotkey_Fire", "ESSB_Hotkey_Frost", "ESSB_Hotkey_Lightning",
        "ESSB_Hotkey_Earth", "ESSB_Hotkey_Wind", "ESSB_Hotkey_Blood", "ESSB_Hotkey_Divine", "ESSB_Hotkey_Poison", "ESSB_Hotkey_Water",
        "ESSB_Hotkey_Darkness", "ESSB_Hotkey_Astral" };
    for (int i = 0; i < kElementCount; ++i) {
        f.hotkeys[i] = one(kHotkeyNames[i], essb::glob::kHotkey[i]);
    }
    ReadTimerTuning([&](std::uint32_t id) {
        d.CheckId(known(id), "timer tuning globals", id, kPlugin, "GLOB", "ReadTimerTuning reads it but it did not resolve from the manifest's globals");
        return 0.0f;
    });
}

// Round 25 (N6): the domains' HAZDs and Spawn Hazard effects by element, checked against the manifest (the spawn spells
// resolve with the other cast spells: StatusEngine.h CastSpells).
template <class D>
void ResolveDomains(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& f, Summary& sum)
{
    using Effect = typename D::Effect;
    f.domainHazards.fill(nullptr);
    f.domainSpawn.fill(nullptr);
    int count = 0;
    for (const auto& row : manifest.at("status").at("domains")) {
        const int e = row.at("element").get<int>();
        if (!d.Check(IsElement(e), "domain record: element " + std::to_string(e) + " is not an element")) {
            continue;
        }
        d.Same(row.at("hazard").get<std::uint32_t>(), essb::status::kDomainHazard[e], "domain record (hazard)", kPlugin, "HAZD");
        d.Same(row.at("spawn_effect").get<std::uint32_t>(), essb::status::kDomainSpawnEffect[e], "domain record (spawn effect)", kPlugin, "MGEF");
        const auto& spawn = row.at("spawn");
        if (d.Check(spawn.size() == static_cast<std::size_t>(kDomainMaxSeconds),
                "domain spawn spells: element " + std::to_string(e) + " lists " + std::to_string(spawn.size()) + ", the DLL has " +
                    std::to_string(kDomainMaxSeconds))) {
            for (int s = 0; s < kDomainMaxSeconds; ++s) {
                d.Same(spawn.at(s).get<std::uint32_t>(), essb::status::kDomainSpawn[e][s], "domain spawn spell", kPlugin, "SPEL");
            }
        }
        f.domainHazards[e] = d.template Resolve<typename D::Hazard>(essb::status::kDomainHazard[e], kPlugin, "domain hazard");
        f.domainSpawn[e] = d.template Resolve<Effect>(essb::status::kDomainSpawnEffect[e], kPlugin, "domain spawn effect");
        sum.hazards += f.domainHazards[e] ? 1 : 0;
        sum.spawnEffects += f.domainSpawn[e] ? 1 : 0;
        if (f.domainHazards[e] && f.domainSpawn[e]) {
            d.CheckId(d.data().SpawnsHazard(f.domainSpawn[e], f.domainHazards[e]), "domain spawn effect places its hazard",
                essb::status::kDomainSpawnEffect[e], kPlugin, "MGEF",
                "it is not a Spawn Hazard effect whose associated item is " + d.Name(essb::status::kDomainHazard[e], kPlugin));
        }
        ++count;
    }
    int compiled = 0;
    for (int e = kFire; e <= kAstral; ++e) {
        compiled += essb::status::kDomainHazard[e] ? 1 : 0;
    }
    d.Check(count == compiled, "domain count: the manifest lists " + std::to_string(count) + ", the DLL has " + std::to_string(compiled));
}

template <class D>
void ResolveSpells(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& f, Summary& sum)
{
    using Spell = typename D::Spell;
    f.procs.fill(nullptr);
    std::size_t procs = 0;
    for (const auto& row : manifest.at("proc_spells")) {
        const int element = row.at("element").get<int>();
        const int power = row.at("power").get<int>();
        const ProcRow* compiled = FindProc(element, power != 0);
        const bool slot = element >= 0 && element <= kElementCount && (power == 0 || power == 1);
        const bool known = slot && compiled && compiled->id == LocalId(row) && !f.procs[element * 2 + power];
        d.CheckId(known, "proc spell", LocalId(row), kPlugin, "SPEL",
            "the DLL has " + (compiled ? Hex(compiled->id, 6) : std::string("no proc spell")) + " for element " + std::to_string(element) +
                " power " + std::to_string(power) + " (or that slot is listed twice)");
        if (known) {
            f.procs[element * 2 + power] = d.template Resolve<Spell>(LocalId(row), kPlugin, "proc spell");
            sum.procSpells += f.procs[element * 2 + power] ? 1 : 0;
        }
        ++procs;
    }
    d.Check(procs == std::size(procRows),
        "proc spell count: the manifest lists " + std::to_string(procs) + ", the DLL has " + std::to_string(std::size(procRows)));
    f.spells.clear();
    for (const auto& [name, row] : manifest.at("spells").items()) {
        if (auto* form = d.template Resolve<Spell>(LocalId(row), kPlugin, "cast spell")) {
            f.spells.emplace_back(LocalId(row), form);
        }
    }
    sum.castSpells = static_cast<int>(f.spells.size());
    // Every spell a plan can ask for must be resolved (one per whole second for silence and the soaked slow).
    for (int cast = 0; cast <= static_cast<int>(Cast::kBloodGuard); ++cast) {
        CastStep step{ static_cast<Cast>(cast) };
        const int variants = DurationVariants(step.cast);
        for (int v = 1; v <= variants; ++v) {
            step.seconds = v;
            step.element = kFire;
            d.CheckId(SpellOf(f, step) != nullptr, "cast spell coverage", step.cast == Cast::kProc ? 0u : SpellFor(step), kPlugin, "SPEL",
                "the hit path casts it (Cast " + std::to_string(cast) + ", " + std::to_string(v) + " s) but it is not resolved");
        }
    }
}

template <class D>
void ResolveEffects(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& f, Summary& sum)
{
    using Effect = typename D::Effect;
    using Keyword = typename D::Keyword;
    const auto& effects = manifest.at("effects");
    auto one = [&](const char* name, std::uint32_t id) {
        d.Same(LocalId(effects.at(name)), id, name, kPlugin, "MGEF");
        auto* form = d.template Resolve<Effect>(id, kPlugin, name);
        sum.effects += form ? 1 : 0;
        return form;
    };
    f.bloodMark = one("kBloodMark", essb::effect::kBloodMark);
    f.silence = one("kSilence", essb::effect::kSilence);
    f.bloodGuard = one("kBloodGuard", essb::effect::kBloodGuard);
    f.echoPending = one("kEchoPending", essb::effect::kEchoPending);
    f.twinWindow = one("kTwinWindow", essb::effect::kTwinWindow);
    f.riposteWindow = one("kRiposteWindow", essb::effect::kRiposteWindow);
    f.hush = one("kHush", essb::effect::kHush);
    f.hushSpent = one("kHushSpent", essb::effect::kHushSpent);
    f.manaBreak = one("kManaBreak", essb::effect::kManaBreak);
    f.engaged = one("kEngaged", essb::effect::kEngaged);
    f.reanimate = one("kReanimate", essb::effect::kReanimate);

    const auto& vanilla = manifest.at("vanilla");
    auto id = [&](const char* name, std::uint32_t compiled, const char* sig) {
        d.Same(vanilla.at(name).at("form_id").get<std::uint32_t>(), compiled, name, kSkyrim, sig);
        return compiled;
    };
    auto vanillaForm = [&](auto* form) {
        sum.vanilla += form ? 1 : 0;
        return form;
    };
    f.undead = vanillaForm(d.template Resolve<Keyword>(id("kUndeadKeyword", essb::vanilla::kUndeadKeyword, "KYWD"), kSkyrim, "ActorTypeUndead"));
    f.daedra = vanillaForm(d.template Resolve<Keyword>(id("kDaedraKeyword", essb::vanilla::kDaedraKeyword, "KYWD"), kSkyrim, "ActorTypeDaedra"));
    f.armorSpell = vanillaForm(d.template Resolve<Keyword>(id("kArmorSpellKeyword", essb::vanilla::kArmorSpellKeyword, "KYWD"), kSkyrim, "MagicArmorSpell"));
    f.cloak = vanillaForm(d.template Resolve<Keyword>(id("kCloakKeyword", essb::vanilla::kCloakKeyword, "KYWD"), kSkyrim, "MagicCloak"));
    f.dragon = vanillaForm(d.template Resolve<Keyword>(id("kDragonKeyword", essb::vanilla::kDragonKeyword, "KYWD"), kSkyrim, "ActorTypeDragon"));
    f.necroClass = vanillaForm(d.template Resolve<typename D::Class>(id("kNecroClass", essb::vanilla::kNecroClass, "CLAS"), kSkyrim, "necromancer class"));
    f.necroFaction = vanillaForm(d.template Resolve<typename D::Faction>(id("kNecroFaction", essb::vanilla::kNecroFaction, "FACT"), kSkyrim, "necromancer faction"));
    f.destructive = { vanillaForm(d.template Resolve<Keyword>(id("kDamageFireKeyword", essb::vanilla::kDamageFireKeyword, "KYWD"), kSkyrim, "MagicDamageFire")),
        vanillaForm(d.template Resolve<Keyword>(id("kDamageFrostKeyword", essb::vanilla::kDamageFrostKeyword, "KYWD"), kSkyrim, "MagicDamageFrost")),
        vanillaForm(d.template Resolve<Keyword>(id("kDamageShockKeyword", essb::vanilla::kDamageShockKeyword, "KYWD"), kSkyrim, "MagicDamageShock")) };
}

// Round 22: every status-layer record by local FormID, checked against the manifest and the compiled table.
template <class D>
void ResolveStatus(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& forms, Summary& sum)
{
    using Effect = typename D::Effect;
    using Spell = typename D::Spell;
    auto& s = forms.status;
    s = StatusForms<D>{};
    const auto& status = manifest.at("status");
    auto effect = [&](std::uint32_t id, const char* what) {
        auto* form = d.template Resolve<Effect>(id, kPlugin, what);
        d.CheckId(TagOf(id).kind != TagKind::kNone, what, id, kPlugin, "MGEF", "Status.h TagOf does not know it");
        if (form) {
            s.effects.emplace_back(id, form);
            s.effectIds.emplace_back(form, id);
        }
    };
    // The record duration of a spell's first effect: effectiveness = wanted / this (ledger D1), so it must be the number
    // Status.h was compiled with.
    auto spell = [&](std::uint32_t id, const char* what, float seconds) {
        auto* form = d.template Resolve<Spell>(id, kPlugin, what);
        if (!form) {
            return;
        }
        if (seconds > 0.0f) {
            const std::optional<float> record = d.data().FirstSeconds(form);
            d.CheckId(record && *record == seconds, what, id, kPlugin, "SPEL",
                (record ? "its first effect lasts " + std::to_string(*record) + " s" : std::string("it has no effect")) +
                    ", the DLL was compiled with " + std::to_string(seconds) + " s");
        }
        s.spells.emplace_back(id, form);
    };
    const auto& kinds = status.at("kinds");
    d.Check(kinds.size() == static_cast<std::size_t>(kStatusKindCount),
        "status kind count: the manifest lists " + std::to_string(kinds.size()) + ", the DLL has " + std::to_string(kStatusKindCount));
    for (int k = 0; k < kStatusKindCount && k < static_cast<int>(kinds.size()); ++k) {
        const auto& row = kinds.at(k);
        const auto& compiled = kStatusRecords[k];
        d.Same(row.at("effect").get<std::uint32_t>(), compiled.effect, "status record (effect)", kPlugin, "MGEF");
        d.Same(row.at("spell").get<std::uint32_t>(), compiled.spell, "status record (spell)", kPlugin, "SPEL");
        d.CheckId(row.at("editor_id").get<std::string>() == compiled.editorId, "status record (EditorID)", compiled.spell, kPlugin, "SPEL",
            "the manifest calls it " + row.at("editor_id").get<std::string>() + ", the DLL " + std::string(compiled.editorId));
        effect(compiled.effect, "status effect");
        spell(compiled.spell, "status spell", compiled.seconds);
    }
    for (int e = kFire; e <= kAstral; ++e) {
        const auto& mark = status.at("marks").at(e - 1);
        d.Same(mark.at("effect").get<std::uint32_t>(), essb::status::kMarkEffect[e], "mark record (effect)", kPlugin, "MGEF");
        d.Same(mark.at("spell").get<std::uint32_t>(), essb::status::kMarkSpell[e], "mark record (spell)", kPlugin, "SPEL");
        effect(essb::status::kMarkEffect[e], "mark effect");
        spell(essb::status::kMarkSpell[e], "mark spell", essb::status::kMarkRecordSeconds);
        d.Same(status.at("react").at(e - 1).at("spell").get<std::uint32_t>(), essb::status::kReactSpell[e], "reaction spell", kPlugin, "SPEL");
        spell(essb::status::kReactSpell[e], "reaction spell", 0.0f);
    }
    const auto& dots = status.at("dots");
    d.Same(dots.at("bleed").at("effect").get<std::uint32_t>(), essb::status::kBleedDotEffect, "DoT effects (bleed)", kPlugin, "MGEF");
    d.Same(dots.at("poison").at("effect").get<std::uint32_t>(), essb::status::kPoisonDotEffect, "DoT effects (poison)", kPlugin, "MGEF");
    effect(essb::status::kBleedDotEffect, "bleed DoT");
    effect(essb::status::kPoisonDotEffect, "poison DoT");
    for (int i = 0; i < essb::status::kDotMaxSeconds; ++i) {
        d.Same(dots.at("bleed").at("spells").at(i).get<std::uint32_t>(), essb::status::kBleedDot[i], "DoT spells (bleed)", kPlugin, "SPEL");
        d.Same(dots.at("poison").at("spells").at(i).get<std::uint32_t>(), essb::status::kPoisonDot[i], "DoT spells (poison)", kPlugin, "SPEL");
        spell(essb::status::kBleedDot[i], "bleed DoT spell", static_cast<float>(i + 1));
        spell(essb::status::kPoisonDot[i], "poison DoT spell", static_cast<float>(i + 1));
    }
    d.Same(status.at("fear").at("effect").get<std::uint32_t>(), essb::status::kFearEffect, "fear effect", kPlugin, "MGEF");
    d.Same(status.at("frenzy").at("effect").get<std::uint32_t>(), essb::status::kFrenzyEffect, "frenzy effect", kPlugin, "MGEF");
    d.Same(status.at("slow").at("effect").get<std::uint32_t>(), essb::status::kSlowEffect, "slow effect", kPlugin, "MGEF");
    effect(essb::status::kFearEffect, "fear effect");
    effect(essb::status::kFrenzyEffect, "frenzy effect");
    effect(essb::status::kSlowEffect, "slow effect");
    // Round 25 hotfix: the 護血 pool (TagKind::kGuardPool, round 23) and 寂 (TagKind::kHush, round 24) are TagOf's
    // effects too -- the board reads them and the dispels find them through this table. 0.25.0 resolved them into Forms
    // only (ResolveEffects), so the TaggedEffects check below faulted the DLL at data load.
    effect(essb::effect::kBloodGuard, "blood guard pool");
    effect(essb::effect::kHush, "hush");
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
        const bool resolves = d.data().template Lookup<Effect>(id, kPlugin) != nullptr;
        d.CheckId(have(s.effects, id), "tagged effect resolved", id, kPlugin, "MGEF",
            resolves ? "the record resolves, but ResolveStatus never put it in the status effect table (TagOf knows it)"
                     : "not resolved (" + d.Found(id, kPlugin) + ")");
    }
    std::sort(s.effectIds.begin(), s.effectIds.end());
    std::sort(s.effects.begin(), s.effects.end());
    std::sort(s.spells.begin(), s.spells.end());
    s.spells.erase(std::unique(s.spells.begin(), s.spells.end()), s.spells.end());
    for (const auto& [id, form] : s.spells) {
        s.spellIds.emplace_back(static_cast<const typename D::Magic*>(form), id);
    }
    std::sort(s.spellIds.begin(), s.spellIds.end());
    for (std::size_t i = 1; i < s.effectIds.size(); ++i) {
        d.CheckId(s.effectIds[i - 1].first != s.effectIds[i].first, "status effects are distinct forms", s.effectIds[i].second, kPlugin,
            "MGEF", "it is the same form as " + d.Name(s.effectIds[i - 1].second, kPlugin));
    }
    for (std::size_t i = 1; i < s.spells.size(); ++i) {
        d.CheckId(s.spells[i - 1].first != s.spells[i].first, "status spells are distinct ids", s.spells[i].first, kPlugin, "SPEL",
            "two different forms answer it");
    }
    sum.statusEffects = static_cast<int>(s.effects.size());
    sum.statusSpells = static_cast<int>(s.spells.size());
    forms.file = d.data().Mod(kPlugin);
    d.Check(forms.file != nullptr, std::string("plugin file: ") + kPlugin + " is not loaded");
}

// Every rank of every main line and every branch slot; missing branch slots stay null (HasPerk false).
template <class D>
void ResolvePerks(Diag<D>& d, const nlohmann::json& manifest, Forms<D>& f, Summary& sum)
{
    const auto& perks = manifest.at("perks");
    d.Check(perks.at("main_base").get<std::uint32_t>() == kMainPerkBase && perks.at("branch_base").get<std::uint32_t>() == kBranchPerkBase &&
                perks.at("main_max_rank").get<int>() == kMainMaxRank && perks.at("branch_slots").get<int>() == kBranchSlots,
        "perk layout: the manifest has main " + Text(perks.at("main_base")) + " x" + Text(perks.at("main_max_rank")) + ", branch " +
            Text(perks.at("branch_base")) + " x" + Text(perks.at("branch_slots")) + "; the DLL main " + Hex(kMainPerkBase, 6) + " x" + std::to_string(kMainMaxRank) +
            ", branch " + Hex(kBranchPerkBase, 6) + " x" + std::to_string(kBranchSlots));
    f.mainPerks.assign(static_cast<std::size_t>(kNodeCount * kMainMaxRank), nullptr);
    f.branchPerks.assign(static_cast<std::size_t>(kNodeCount * kBranchSlots), nullptr);
    for (std::size_t i = 0; i < f.mainPerks.size(); ++i) {
        f.mainPerks[i] = d.template Resolve<typename D::Perk>(kMainPerkBase + static_cast<std::uint32_t>(i), kPlugin, "main-line perk");
    }
    for (std::size_t i = 0; i < f.branchPerks.size(); ++i) {
        f.branchPerks[i] = d.data().template Lookup<typename D::Perk>(kBranchPerkBase + static_cast<std::uint32_t>(i), kPlugin);
    }
    const auto present = [](const auto& table) {
        return static_cast<int>(std::count_if(table.begin(), table.end(), [](const auto* perk) { return perk != nullptr; }));
    };
    sum.mainPerks = present(f.mainPerks);
    sum.branchPerks = present(f.branchPerks);
}

// Everything the DLL resolves at data load, in the order LoadManifest ran it in 0.25.0. Every failure is reported
// (D::Report) as it is found; if there was any, LoadForms throws with the first one and the count (Plugin.cpp turns that
// into the latched fault; load_test into a failed build).
template <class D>
Summary LoadForms(D& data, const nlohmann::json& manifest, Forms<D>& f)
{
    CheckVersion(manifest);
    Summary sum;
    Diag<D> d(data, manifest, sum);
    const std::optional<std::uint32_t> base = data.RuntimeId(0, kPlugin);
    sum.pluginIndex = base ? *base : 0;
    ResolveGlobals(d, manifest, f, sum);
    ResolveSpells(d, manifest, f, sum);
    ResolveEffects(d, manifest, f, sum);
    ResolvePerks(d, manifest, f, sum);
    ResolveStatus(d, manifest, f, sum);
    ResolveDomains(d, manifest, f, sum);   // round 25 (N6)
    if (!sum.failures.empty()) {
        const std::size_t more = sum.failures.size() - 1;
        throw std::runtime_error(sum.failures.front() +
                                 (more ? " (and " + std::to_string(more) + " more load failure(s), each logged above)" : std::string()));
    }
    return sum;
}

// The one summary line Plugin.cpp logs at data load.
inline std::string Describe(const Summary& s)
{
    return "plugin at " + Hex(s.pluginIndex, 8) + ": " + std::to_string(s.globals) + " globals, " + std::to_string(s.procSpells) +
           " proc spells, " + std::to_string(s.castSpells) + " hit-path spells, " + std::to_string(s.effects) + " named effects, " +
           std::to_string(s.statusEffects) + " status effects (TagOf), " + std::to_string(s.statusSpells) + " status spells, " +
           std::to_string(s.hazards) + " domain hazards + " + std::to_string(s.spawnEffects) + " spawn effects, " +
           std::to_string(s.mainPerks) + " main-line perks, " + std::to_string(s.branchPerks) + " branch perks, " +
           std::to_string(s.vanilla) + " Skyrim.esm forms";
}

}  // namespace essb::load
