// Round 25 hotfix: the DLL's data-load resolution (Load.h, the code Plugin.cpp LoadManifest runs) on the written ESP and
// manifest, offline. 0.25.0 faulted in the game at data load ("tagged effect resolved") because no test ran the loader:
// the tests checked that an id was on TaggedEffects() / CastSpells(), never that the loader registered it.
//   L  load: essb::load::LoadForms over a fake TESDataHandler built from build/fix25-load-forms.json (build/fix25_verify.py
//      reads it back from the ESP it just wrote and from Skyrim.esm: every record's local FormID and type, each SPEL's
//      first-effect duration, each MGEF's archetype and associated item) and the packaged manifest.json -- every
//      identity check, every record lookup by type, the record durations, the domains' Spawn Hazard effects, the tagged
//      effects and the cast spells, exactly as in the game
//   R  runtime: what the DLL looks up after the load finds its record the way Plugin.cpp does (sorted tables): every
//      TaggedEffects() id by id and by form (EffectById / EffectIdOf), every CastSpells() id (SpellById / SpellIdOf), every
//      hit-path cast (SpellOf)
// Injected faults (build/fix25_verify.py) mutate the ESP facts / the manifest and require this binary to fail; the
// native/build.py mutants of Load.h (the 0.25.0 registration among them) must fail it too.
#include "Load.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using json = nlohmann::json;

int checks = 0;

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
    ++checks;
}

json Load(const char* path)
{
    std::ifstream in(path);
    Check(in.good(), std::string("cannot open ") + path);
    json data;
    in >> data;
    return data;
}

// One record of the fake data handler. The C++ type is the record type (LookupForm<T> answers only its own type).
struct Form {
    virtual ~Form() = default;
    std::string file;
    std::uint32_t id = 0;
    std::string sig;
    std::optional<float> seconds;    // SPEL: its first effect's duration
    std::uint32_t archetype = 0;     // MGEF: DATA archetype
    std::uint32_t associated = 0;    // MGEF: DATA associated item (raw, the ESP's master index in the top byte)
};
struct Global : Form {};
struct Magic : Form {};
struct Spell : Magic {};
struct Effect : Form {};
struct Keyword : Form {};
struct Class : Form {};
struct Faction : Form {};
struct Perk : Form {};
struct Hazard : Form {};
struct File {
    std::string name;
};

std::unique_ptr<Form> Make(const std::string& sig)
{
    if (sig == "GLOB") return std::make_unique<Global>();
    if (sig == "SPEL") return std::make_unique<Spell>();
    if (sig == "MGEF") return std::make_unique<Effect>();
    if (sig == "KYWD") return std::make_unique<Keyword>();
    if (sig == "CLAS") return std::make_unique<Class>();
    if (sig == "FACT") return std::make_unique<Faction>();
    if (sig == "PERK") return std::make_unique<Perk>();
    if (sig == "HAZD") return std::make_unique<Hazard>();
    return std::make_unique<Form>();
}

// The fake TESDataHandler: the files in load order (index = the runtime FormID prefix), their records by local id.
class FakeData
{
public:
    using Global = ::Global;
    using Spell = ::Spell;
    using Magic = ::Magic;
    using Effect = ::Effect;
    using Keyword = ::Keyword;
    using Class = ::Class;
    using Faction = ::Faction;
    using Perk = ::Perk;
    using Hazard = ::Hazard;
    using File = ::File;

    explicit FakeData(const json& facts)
    {
        // load order: the plugin's masters, then the plugin (the ESP's own numbering of FormIDs)
        for (const auto& name : facts.at("masters")) {
            order_.push_back(name.get<std::string>());
        }
        order_.push_back(facts.at("plugin").get<std::string>());
        for (const auto& name : order_) {
            files_.emplace(name, File{ name });
        }
        for (const auto& [file, rows] : facts.at("records").items()) {
            for (const auto& row : rows) {
                auto form = Make(row.at("sig").get<std::string>());
                form->file = file;
                form->id = row.at("id").get<std::uint32_t>();
                form->sig = row.at("sig").get<std::string>();
                if (row.contains("seconds") && !row.at("seconds").is_null()) {
                    form->seconds = row.at("seconds").get<float>();
                }
                form->archetype = row.value("archetype", 0u);
                form->associated = row.value("associated", 0u);
                const auto key = std::make_pair(file, form->id);
                Check(forms_.emplace(key, std::move(form)).second, "two records at one FormID in the facts");
            }
        }
    }

    template <class T>
    T* Lookup(std::uint32_t id, const char* file)
    {
        const auto it = forms_.find({ file, id & 0xFFFFFFu });
        return it != forms_.end() ? dynamic_cast<T*>(it->second.get()) : nullptr;
    }
    std::string KindOf(std::uint32_t id, const char* file)
    {
        const auto it = forms_.find({ file, id & 0xFFFFFFu });
        return it != forms_.end() ? it->second->sig : std::string();
    }
    std::optional<std::uint32_t> RuntimeId(std::uint32_t id, const char* file)
    {
        const auto it = std::find(order_.begin(), order_.end(), std::string(file));
        if (it == order_.end()) {
            return std::nullopt;
        }
        return (static_cast<std::uint32_t>(it - order_.begin()) << 24) | (id & 0xFFFFFFu);
    }
    const File* Mod(const char* file)
    {
        const auto it = files_.find(file);
        return it != files_.end() ? &it->second : nullptr;
    }
    std::optional<float> FirstSeconds(const Spell* spell) { return spell->seconds; }
    // The engine's check: archetype 40 (Spawn Hazard) and the associated form IS that hazard (raw id -> the master it
    // names -> the form there).
    bool SpawnsHazard(const Effect* effect, const Hazard* hazard)
    {
        const std::uint32_t index = effect->associated >> 24;
        if (effect->archetype != 40 || index >= order_.size()) {
            return false;
        }
        return Lookup<Hazard>(effect->associated, order_[index].c_str()) == hazard;
    }
    void Report(const std::string& line)
    {
        std::printf("[ESSB][load] FAILED %s\n", line.c_str());
        ++failures;
    }

    int failures = 0;

private:
    std::vector<std::string> order_;
    std::map<std::string, File> files_;
    std::map<std::pair<std::string, std::uint32_t>, std::unique_ptr<Form>> forms_;
};

template <class Id, class Ptr>
Ptr Find(const std::vector<std::pair<Id, Ptr>>& table, Id key)
{
    Check(std::is_sorted(table.begin(), table.end()), "a lookup table is not sorted");
    const auto it = std::lower_bound(table.begin(), table.end(), key, [](const auto& row, Id k) { return row.first < k; });
    return it != table.end() && it->first == key ? it->second : Ptr{};
}

// R: the runtime lookups of Plugin.cpp (EffectById, EffectIdOf, SpellById, SpellIdOf, SpellOf) on the resolved tables.
void Runtime(const essb::load::Forms<FakeData>& f)
{
    const auto& s = f.status;
    for (const std::uint32_t id : essb::engine::TaggedEffects()) {
        const Effect* form = Find(s.effects, id);
        Check(form != nullptr, "EffectById: tagged effect " + essb::load::Hex(id, 6) + " not in the status effect table");
        Check(Find(s.effectIds, form) == id, "EffectIdOf: tagged effect " + essb::load::Hex(id, 6) + " does not map back to its id");
        Check(essb::TagOf(id).kind != essb::TagKind::kNone, "a tagged effect TagOf does not know");
    }
    for (const std::uint32_t id : essb::engine::CastSpells()) {
        const Spell* form = Find(s.spells, id);
        Check(form != nullptr, "SpellById: cast spell " + essb::load::Hex(id, 6) + " not in the status spell table");
        Check(Find(s.spellIds, static_cast<const Magic*>(form)) == id, "SpellIdOf: " + essb::load::Hex(id, 6) + " does not map back");
    }
    for (int cast = 0; cast <= static_cast<int>(essb::Cast::kBloodGuard); ++cast) {
        essb::CastStep step{ static_cast<essb::Cast>(cast) };
        for (int v = 1; v <= essb::DurationVariants(step.cast); ++v) {
            step.seconds = v;
            step.element = essb::kFire;
            Check(essb::load::SpellOf(f, step) != nullptr, "SpellOf: a hit-path cast without its spell");
        }
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {   // the proc spells: every element, normal and power
        for (const bool power : { false, true }) {
            essb::CastStep step{ essb::Cast::kProc };
            step.element = e;
            step.power = power;
            Check(essb::load::SpellOf(f, step) != nullptr, "SpellOf: element " + std::to_string(e) + " has no proc spell");
        }
    }
    for (int e = essb::kFire; e <= essb::kAstral; ++e) {
        Check((f.domainHazards[e] != nullptr) == (essb::status::kDomainHazard[e] != 0) &&
                  (f.domainSpawn[e] != nullptr) == (essb::status::kDomainSpawnEffect[e] != 0),
            "a domain without its hazard / spawn effect");
    }
    Check(f.bloodGuard == Find(s.effects, essb::effect::kBloodGuard) && f.hush == Find(s.effects, essb::effect::kHush),
        "the 護血 pool / 寂 resolve to one form in both tables");
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::cerr << "usage: load_test <manifest.json> <fix25-load-forms.json>\n";
        return 2;
    }
    try {
        const json manifest = Load(argv[1]);
        FakeData data(Load(argv[2]));
        essb::load::Forms<FakeData> forms;
        essb::load::Summary summary;
        try {
            summary = essb::load::LoadForms(data, manifest, forms);
        } catch (const std::exception& e) {
            std::printf("[ESSB][fault] %s; native hit OFF until the game restarts\n", e.what());
            std::printf("NATIVE LOAD FAILED: %d load failure(s)\n", data.failures);
            return 1;
        }
        Check(data.failures == 0 && summary.failures.empty(), "failures reported without a throw");
        Runtime(forms);
        std::printf("[ESSB][load] resolved %s\n", essb::load::Describe(summary).c_str());
        std::printf("NATIVE LOAD L ok: the DLL's data-load resolution (Load.h) passes on the written ESP and manifest; "
                    "R ok: %d runtime lookups (tagged effects, cast spells, hit-path casts, domains)\n",
            checks);
        return 0;
    } catch (const std::exception& e) {
        std::printf("NATIVE LOAD FAILED: %s\n", e.what());
        return 1;
    }
}
