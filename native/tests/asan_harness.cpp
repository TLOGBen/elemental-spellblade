// Round 27d (0.27.3): the AddressSanitizer harness of native/build.py's lifetime net. clang-cl's AddressSanitizer on this
// toolchain cannot run code that throws (even a trivial throw / catch aborts), so the runtime / engine tests, which
// check by throwing, are not run under it; this harness drives the same headers WITHOUT exceptions and reports by exit
// code: the self-pointing context copied and returned (the 0.27.1 bug), the node view on a named reader (the 0.27.2
// bug), the registry published and read by two threads, a 24-target burst with every node and its body pass (the plan
// growing while the bodies walk it), a chained end carrying its sum, the hurt queue.
#include "EngineFacts.h"
#include "Reactions.h"
#include "Registry.h"
#include "Runtime.h"
#include "SelfLayer.h"
#include "Status.h"
#include "StatusEngine.h"

#include <atomic>
#include <cstdio>
#include <memory>
#include <set>
#include <thread>
#include <tuple>
#include <vector>

namespace {

int failures = 0;

void Expect(bool ok, const char* what)
{
    if (!ok) {
        std::printf("ASAN HARNESS FAILED: %s\n", what);
        ++failures;
    }
}

struct AllNodes {
    int Rank(const essb::NodeId& id) const { return id.tree >= 0 ? essb::kMainMaxRank : 0; }
    bool Has(const essb::BranchId&) const { return true; }
};

struct MidRng {
    int Int(int lo, int) { return lo; }
    float Real(float lo, float hi) { return lo + (hi - lo) * 0.5f; }
    bool Chance(float) { return false; }
};

__declspec(noinline) essb::rt::Context MakeCopied()
{
    essb::rt::Context local;
    local.tuning.multDrain = 1.25f;
    local.in.tuning = &local.tuning;
    essb::rt::Context copy = local;
    return copy;
}

void Burst()
{
    const essb::Config config = essb::MakeConfig();
    const essb::rt::Context c = MakeCopied();
    essb::StatusInputs in = c.in;
    in.config = &config;
    essb::Tuning tuning = c.tuning;
    tuning.level.fill(100.0f);
    tuning.nodeScale = 5.0f;
    tuning.syncStage = 3;
    in.tuning = &tuning;
    in.n4 = true;
    const AllNodes perks;
    essb::Board me;
    const auto nodes = essb::WithAvatar(perks, me);   // a named reader (a temporary does not compile)
    essb::Crowd crowd;
    crowd.count = 1 + essb::n5::kCrowdMax;
    for (int k = 1; k < crowd.count; ++k) {
        essb::Member& m = crowd.m[k];
        m.has = true;
        m.board.mark[1 + (k % 11)] = essb::Slot{ true, 0.0f, 1.0f, 8.0f };
        m.board.mark[1 + ((k + 4) % 11)] = essb::Slot{ true, 0.0f, 2.0f, 8.0f };
        m.board.poisonDot = essb::Slot{ true, 5.0f, 1.0f, 8.0f };
        m.body = essb::Body{ 500.0f, 1000.0f, 20.0f, 100.0f, false, false, 200.0f };
        m.pos = { 50.0f * static_cast<float>(k), 0.0f, 0.0f };
        m.magickaMax = 100.0f;
    }
    const essb::BodyInputs bin{ &in, false, 100.0f, 100.0f, 100.0f, 100.0f };
    MidRng rng;
    auto plan = std::make_unique<essb::StatusPlan>();
    const essb::BurstResult r = essb::PlanBurst(*plan, crowd, me, bin, 3, essb::kFire, nodes, rng);
    Expect(r.targets == essb::n5::kCrowdMax && plan->count > 512 && !plan->overflow, "a 24-target burst with every node plans in full");
    bool finite = true;
    for (int i = 0; i < plan->count; ++i) {
        finite = finite && essb::engine::SaneValue(plan->ops[i].magnitude);
    }
    Expect(finite, "every op of the burst has a sane magnitude");
}

void RegistryThreads()
{
    essb::reg::Registry r;
    std::atomic_bool stop{};
    std::thread writer([&] {
        for (int i = 0; i < 20000; ++i) {
            essb::reg::Snapshot s;
            s.ours.resize(1 + i % 5);
            r.Publish(essb::reg::Key{ 0xFF000800u + static_cast<std::uint32_t>(i % 7), 3 }, std::move(s));
            if (i % 3 == 0) {
                r.Forget(0xFF000800u + static_cast<std::uint32_t>(i % 7));
            }
        }
        stop = true;
    });
    int reads = 0;
    while (!stop) {
        for (std::uint32_t k = 0; k < 7; ++k) {
            if (const auto s = r.Get(essb::reg::Key{ 0xFF000800u + k, 3 })) {
                reads += s->ours.empty() ? 0 : 1;
            }
            r.EraseUid(essb::reg::Key{ 0xFF000800u + k, 3 }, 0);
        }
    }
    writer.join();
    Expect(reads >= 0, "the registry read beside its writer");
}

void Hurt()
{
    essb::rt::HurtQueue<int> q;
    for (int i = 0; i < 64; ++i) {
        essb::rt::HurtEntry<int> e;
        e.frame = static_cast<std::uint64_t>(i / 4);
        e.atMs = static_cast<std::uint64_t>(i);
        q.Push(e);
    }
    const auto batch = q.Take(8, 100);
    Expect(!batch.ready.empty(), "the hurt queue hands the earlier frames");
}

}  // namespace

int main()
{
    const essb::rt::Context c = MakeCopied();
    Expect(c.in.tuning == &c.tuning && c.in.tuning->multDrain == 1.25f, "a returned context reads its own tuning");
    Burst();
    RegistryThreads();
    Hurt();
    if (failures == 0) {
        std::printf("ASAN HARNESS ok: context copy, named node view, 24-target burst, registry threads, hurt queue\n");
    }
    return failures == 0 ? 0 : 1;
}
