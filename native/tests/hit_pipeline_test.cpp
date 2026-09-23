// Offline tests of the engine-free hit pipeline (HitPipeline.h + Selection.h + generated ManifestData.h).
// Each group states what it proves; case counts are printed and recorded in build/fix19-native-test.log.
//   A  production truth table: every Input BuildInput can emit -> spell, vs the old 74-segment ESP oracle
//   B  wiring: engine answers -> Input, with the exact CTDA queries issued (mocked engine)
//   C  filter: every hit-fact combination the engine can report -> verdict, vs a line-by-line
//      transliteration of the Papyrus OnWeaponHit gates (parity of DLL base and Papyrus bonus)
//   D  lightning band distribution through BuildInput with a mocked GetRandomPercent
#include "HitPipeline.h"
#include "ManifestData.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <iostream>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void Check(bool ok, const std::string& message)
{
    if (!ok) {
        throw std::runtime_error(message);
    }
}

// ---------------------------------------------------------------- A

int GroupA(const char* path)
{
    std::ifstream file(path);
    Check(bool(file), "truth table missing");
    std::string line;
    int rows = 0;
    std::set<std::uint32_t> reached;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        std::istringstream in(line);
        essb::Input x;
        int power = 0;
        int sneak = 0;
        std::uint32_t expected = 0;
        in >> x.element >> x.rightItem >> power >> sneak >> x.blood >> x.lightning >> expected;
        Check(!in.fail(), "bad truth-table row: " + line);
        x.power = power != 0;
        x.sneak = sneak != 0;
        const std::uint32_t actual = essb::spell(essb::select(x));
        Check(actual == expected, "A mismatch: " + line + " got " + std::to_string(actual));
        if (actual) {
            reached.insert(actual);
        }
        ++rows;
    }
    // 11 elements x 3 right-hand kinds x power x sneak, blood x5 bands (4 + none), lightning x5 bands.
    Check(rows == 9 * 12 + 60 + 60, "truth table does not cover the production input space");
    Check(reached.size() == std::size(essb::rows), "a manifest spell is unreachable from production inputs");
    return rows;
}

// ---------------------------------------------------------------- B

struct Engine {
    int rightItem = 0;           // what CTDA 597 (right hand) reports: 7, 12 or other
    bool power = false;
    bool sneak = false;
    float health = 1.0f;         // CTDA 640 value
    std::array<int, 4> draws{};  // successive GetRandomPercent results
    int drawn = 0;
    std::vector<essb::Query> log;

    bool operator()(const essb::Query& q)
    {
        log.push_back(q);
        switch (q.fn) {
        case essb::Fn::kGetEquippedItemType:
            Check(q.param == essb::kRightHand && q.op == essb::Op::kEqual, "597 must ask the right hand with ==");
            return float(rightItem) == q.value;
        case essb::Fn::kIsPowerAttacking:
            Check(q.value == 1.0f && q.op == essb::Op::kEqual, "673 must be == 1");
            return power;
        case essb::Fn::kIsSneaking:
            Check(q.value == 1.0f && q.op == essb::Op::kEqual, "286 must be == 1");
            return sneak;
        case essb::Fn::kGetActorValuePercent:
            Check(q.param == essb::kHealth && q.op == essb::Op::kGreaterOrEqual, "640 must be Health >=");
            return health >= q.value;
        case essb::Fn::kGetRandomPercent:
            Check(q.op == essb::Op::kLess, "77 must be <");
            Check(drawn < 4, "more than four random draws");
            return float(draws[drawn++]) < q.value;
        }
        throw std::runtime_error("unexpected CTDA function");
    }
};

int GroupB()
{
    const int items[] = { essb::kItemBow, essb::kItemCrossbow, 0, 1 };
    // Health boundaries only matter for blood and RNG patterns only for lightning; the other elements
    // get two extreme values of each to show they are not read at all.
    const std::vector<float> bloodHealths = { 1.0f, 0.85f, 0.84999f, 0.5f, 0.49999f, 0.2f, 0.19999f, 0.0f, -0.01f };
    const std::vector<float> otherHealths = { 1.0f, -0.01f };
    std::vector<int> allPatterns;
    for (int pattern = 0; pattern < 16; ++pattern) {
        allPatterns.push_back(pattern);
    }
    const std::vector<int> extremePatterns = { 0, 15 };
    int cases = 0;
    for (int element = 1; element <= 11; ++element) {
        const auto& healths = element == 6 ? bloodHealths : otherHealths;
        const auto& patterns = element == 3 ? allPatterns : extremePatterns;
        for (int item : items) {
            for (int flags = 0; flags < 4; ++flags) {
                for (float health : healths) {
                    for (int pattern : patterns) {
                        Engine engine;
                        engine.rightItem = item;
                        engine.power = (flags & 1) != 0;
                        engine.sneak = (flags & 2) != 0;
                        engine.health = health;
                        for (int i = 0; i < 4; ++i) {
                            engine.draws[i] = (pattern >> i) & 1 ? 0 : 99;  // 0 passes every chance, 99 none
                        }
                        const essb::Input x = essb::BuildInput(element, engine);

                        const int expectedItem = item == essb::kItemBow || item == essb::kItemCrossbow ? item : 0;
                        int expectedBlood = -1;
                        if (element == 6) {
                            expectedBlood = health >= 0.85f ? 0 : health >= 0.5f ? 1 : health >= 0.2f ? 2 : health >= 0.0f ? 3 : -1;
                        }
                        int expectedLightning = 0;
                        int expectedDraws = 0;
                        if (element == 3) {
                            expectedLightning = 1;
                            expectedDraws = 4;
                            for (int i = 0; i < 4; ++i) {
                                if ((pattern >> i) & 1) {
                                    expectedLightning = 5 - i;
                                    expectedDraws = i + 1;
                                    break;
                                }
                            }
                        }
                        Check(x.element == element && x.rightItem == expectedItem, "B weapon wiring");
                        Check(x.power == engine.power && x.sneak == engine.sneak, "B power/sneak wiring");
                        Check(x.blood == expectedBlood, "B blood band wiring");
                        Check(x.lightning == expectedLightning, "B lightning wiring");
                        Check(engine.drawn == expectedDraws, "B RNG must be drawn lazily and only for lightning");
                        const auto healthQueries = std::count_if(engine.log.begin(), engine.log.end(), [](const essb::Query& q) {
                            return q.fn == essb::Fn::kGetActorValuePercent;
                        });
                        Check((healthQueries > 0) == (element == 6), "B health must be read only for blood");
                        ++cases;
                    }
                }
            }
        }
    }
    return cases;
}

// ---------------------------------------------------------------- C

// Transliteration of ESSBController.ResolveHitWeaponType + the OnWeaponHit gates, kept deliberately
// close to the Papyrus text (not to HitPipeline.h) so the two implementations are independent.
int PapyrusResolve(const essb::HitFacts& f)
{
    const bool isWeapon = f.source == essb::SourceKind::kWeapon;
    if (isWeapon) {
        return f.sourceWeaponType;  // Return weaponSource.GetWeaponType()
    }
    const bool hasSource = f.source != essb::SourceKind::kNone;
    const bool ammo = f.source == essb::SourceKind::kAmmo;
    const bool sameProjectile = f.source == essb::SourceKind::kSameProjectile;
    if (hasSource && !ammo && !sameProjectile) {
        return -1;
    }
    const int equipped = f.right.weaponType;  // GetEquippedWeapon(False)
    const int offhand = f.left.weaponType;    // GetEquippedWeapon(True)
    if (f.projectile) {
        if (equipped != -1 && (equipped == 7 || equipped == 9)) {
            return equipped;
        }
        if (offhand != -1 && (offhand == 7 || offhand == 9)) {
            return offhand;
        }
    } else if (!hasSource && f.left.nothing && f.right.nothing) {  // GetEquippedItemType(0) == 0 && (1) == 0
        return 0;
    }
    return -1;
}

bool PapyrusAccepts(const essb::HitFacts& f)
{
    if (!f.causeIsPlayer || f.enabled != 1.0f) {
        return false;
    }
    if (f.bash || f.blocked) {  // Math.LogicalAnd(aiHitFlagMask, 1097731) != 0
        return false;
    }
    if (!f.targetIsActor || f.targetIsPlayer || f.teammate || f.commanded) {
        return false;
    }
    const int weaponType = PapyrusResolve(f);
    if (weaponType < 0 || weaponType > 9 || weaponType == 8) {
        return false;
    }
    const bool ranged = weaponType == 7 || weaponType == 9;
    if (!ranged && f.projectile) {
        return false;
    }
    if (f.targetDead) {
        return false;
    }
    if (f.formActive != 1.0f) {  // !hitActive: no-form XP only, no element proc
        return false;
    }
    const int element = int(f.element);  // CurrentElement.GetValueInt()
    return element >= 1 && element <= 11;
}

// Hand states the engine can report: empty, a non-weapon (spell/shield/torch), a hand-to-hand
// weapon, or a weapon of type 1..9.
std::vector<essb::HandFacts> Hands()
{
    std::vector<essb::HandFacts> hands = { { essb::kNoWeapon, true }, { essb::kNoWeapon, false }, { 0, true } };
    for (int type = 1; type <= 9; ++type) {
        hands.push_back({ type, false });
    }
    return hands;
}

int GroupC()
{
    struct SourceState {
        essb::SourceKind kind;
        int weaponType;
    };
    std::vector<SourceState> sources = { { essb::SourceKind::kNone, -1 }, { essb::SourceKind::kAmmo, -1 },
        { essb::SourceKind::kSameProjectile, -1 }, { essb::SourceKind::kOther, -1 } };
    for (int type = 0; type <= 9; ++type) {
        sources.push_back({ essb::SourceKind::kWeapon, type });
    }
    const auto hands = Hands();
    int cases = 0;
    // C1: weapon resolution over every reportable source/projectile/hand combination.
    for (const auto& source : sources) {
        for (int projectile = 0; projectile < 2; ++projectile) {
            for (const auto& right : hands) {
                for (const auto& left : hands) {
                    essb::HitFacts f;
                    f.causeIsPlayer = true;
                    f.targetIsActor = true;
                    f.enabled = 1.0f;
                    f.formActive = 1.0f;
                    f.element = 1.0f;
                    f.source = source.kind;
                    f.sourceWeaponType = source.weaponType;
                    f.projectile = projectile != 0;
                    f.right = right;
                    f.left = left;
                    Check(essb::ResolveWeaponType(f) == PapyrusResolve(f), "C1 weapon resolution differs from Papyrus");
                    const bool accepted = essb::Filter(f).reason == essb::Reject::kAccepted;
                    Check(accepted == PapyrusAccepts(f), "C1 filter differs from Papyrus");
                    ++cases;
                }
            }
        }
    }
    // C2: every other gate, each boolean fact and each global value, on melee, ranged and fist baselines.
    // The GLOBs are only ever written with SetValueInt / MCM toggles, so only integer values can occur.
    const float globals[] = { 0.0f, 1.0f, 2.0f, -1.0f, 3.0f, 11.0f, 12.0f };
    for (int baseline = 0; baseline < 3; ++baseline) {
        for (int gate = 0; gate < 8; ++gate) {
            for (int on = 0; on < 2; ++on) {
                for (float value : globals) {
                    essb::HitFacts f;
                    f.causeIsPlayer = true;
                    f.targetIsActor = true;
                    f.enabled = 1.0f;
                    f.formActive = 1.0f;
                    f.element = 3.0f;
                    if (baseline == 0) {
                        f.source = essb::SourceKind::kWeapon;
                        f.sourceWeaponType = 1;
                    } else if (baseline == 1) {
                        f.source = essb::SourceKind::kWeapon;
                        f.sourceWeaponType = 7;
                        f.projectile = true;
                    }
                    const bool flag = on != 0;
                    switch (gate) {
                    case 0: f.causeIsPlayer = flag; break;
                    case 1: f.targetIsActor = flag; break;
                    case 2: f.targetIsPlayer = flag; break;
                    case 3: f.targetDead = flag; break;
                    case 4: f.teammate = flag; f.commanded = !flag; break;
                    case 5: f.bash = flag; f.blocked = !flag; break;
                    case 6: f.enabled = value; f.formActive = flag ? 1.0f : value; break;
                    case 7: f.element = value; break;
                    }
                    const bool accepted = essb::Filter(f).reason == essb::Reject::kAccepted;
                    Check(accepted == PapyrusAccepts(f), "C2 gate differs from Papyrus");
                    ++cases;
                }
            }
        }
    }
    return cases;
}

// ---------------------------------------------------------------- D

// Integer model (the engine's GetRandomPercent returns 0..99) and a continuous model, each 1,000,000 hits.
int GroupD()
{
    constexpr int trials = 1000000;
    std::mt19937 rng(190020);
    std::uniform_int_distribution<int> integer(0, 99);
    std::array<int, 6> hits{};
    for (int i = 0; i < trials; ++i) {
        auto ask = [&](const essb::Query& q) {
            if (q.fn == essb::Fn::kGetRandomPercent) {
                return float(integer(rng)) < q.value;
            }
            return false;
        };
        ++hits[essb::select(essb::BuildInput(3, ask)).lightning];
    }
    double remaining = 1.0;
    for (int band = 5; band >= 1; --band) {
        const double chance = band == 1 ? 1.0 : std::ceil(100.0 / band) / 100.0;
        const double expected = remaining * chance;
        remaining *= 1.0 - chance;
        const double measured = double(hits[band]) / trials;
        Check(std::abs(measured - expected) < 0.002, "D integer-model distribution");
        std::printf("R%d integer_expected=%.4f measured=%.4f\n", band, expected, measured);
    }
    std::uniform_real_distribution<float> real(0.0f, 100.0f);
    hits.fill(0);
    for (int i = 0; i < trials; ++i) {
        auto ask = [&](const essb::Query& q) {
            if (q.fn == essb::Fn::kGetRandomPercent) {
                return real(rng) < q.value;
            }
            return false;
        };
        ++hits[essb::select(essb::BuildInput(3, ask)).lightning];
    }
    for (int band = 1; band <= 5; ++band) {
        Check(std::abs(double(hits[band]) / trials - 0.2) < 0.002, "D continuous-model distribution");
    }
    return 2 * trials;
}

// Manifest identity at compile time: every generated row is a distinct, in-range key.
constexpr bool RowsAreDistinctKeys()
{
    for (std::size_t i = 0; i < std::size(essb::rows); ++i) {
        const auto& key = essb::rows[i].key;
        if (key.index() < 0 || key.index() >= essb::kKeyCount || essb::spell(key) != essb::rows[i].id) {
            return false;
        }
        for (std::size_t j = i + 1; j < std::size(essb::rows); ++j) {
            if (essb::rows[j].key == key) {
                return false;
            }
        }
    }
    return true;
}
static_assert(RowsAreDistinctKeys());

}  // namespace

int main(int argc, char** argv)
{
    try {
        Check(argc == 2, "usage: hit_pipeline_test <build/fix19-truth.csv>");
        const int a = GroupA(argv[1]);
        const int b = GroupB();
        const int c = GroupC();
        const int d = GroupD();
        std::printf("NATIVE TRUTH TABLE ok: A %d production inputs == old 74-segment ESP oracle; all %zu manifest spells reachable\n",
            a, std::size(essb::rows));
        std::printf("NATIVE WIRING ok: B %d mocked engine states -> Input with exact CTDA queries; RNG lazy, health only for blood\n", b);
        std::printf("NATIVE FILTER ok: C %d hit-fact combinations == Papyrus OnWeaponHit gates\n", c);
        std::printf("NATIVE LIGHTNING ok: D %d BuildInput draws (integer + continuous RNG models)\n", d);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "FAILED: %s\n", e.what());
        return 1;
    }
}
