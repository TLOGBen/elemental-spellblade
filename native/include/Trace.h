#pragma once
// Round 26: the probe log (MCM 除錯等級 4「探針 log」). The user runs build/probes-all.md in one sitting and only acts; the
// commander judges every step from the log. So at level 4 every observable a step checks is one line of
// ElementsSpellblade.log, precise and greppable:
//
//   [ESSB][T][<kind>] #<seq> g=<game-running ms> r=<real ms> <key=value ...>
//
// kind: proc, hit-reject, op, op-done, remove, apply, hurt, cast, death, burst, settle, native, scan, scan-c, second, env,
// domain, domain-in, domain-new, domain-gone, domain-you, switch, key, mcm, node, pap, tick, interrupt, casting, wash, rng,
// trace. The step marker is its own line: [ESSB][STEP] <station> #<seq> g=… r=… via=key|console.
//
// Pure: no engine. Plugin.cpp fills ActorFacts from the engine and hands the lines to one Buffer; the timer thread writes
// the buffer to the file once a second (and at a fault / a load / the DLL's unload), so a hit never waits on the disk.
// With the level below 4 nothing here runs: every call site checks the level first (one float compare).
// native/tests/trace_test.cpp runs the formatters, the buffer and the recording random source on the real planners.
#include "Hurt.h"
#include "Status.h"
#include "Timer.h"

#include <algorithm>
#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <string>
#include <string_view>

namespace essb::trace {

inline constexpr float kLevel = 4.0f;                 // ESSB_DebugLevel at which the probe log is on
inline constexpr std::size_t kMaxLine = 480;          // bytes of one line's body; a longer body is cut and ends in "~"
inline constexpr std::size_t kFlushBytes = 1u << 20;  // a buffer this full asks to be written at once
inline constexpr std::size_t kMaxBuffer = 16u << 20;  // past this (the disk stalled) lines are dropped and counted
inline constexpr int kTape = 24;                      // random draws one tape keeps (the rest are counted)
inline constexpr int kStepKeyNext = 78;               // DIK numpad +: the next probe station
inline constexpr int kStepKeyBack = 74;               // DIK numpad -: the previous probe station (marks it again)

// Round 26b (X2): the return addresses (SkyrimSE.exe offsets) that name the context a sink or a task runs in (the
// commander's disassembly): the BSJobs "Post process" job and its task queue, the paused path of Main::Update, the hit
// task (ID 36016) and the hit frame handler, the UI job and the main-thread ProcessMessages, the "Poll controls" job and
// the paused input poll, the VM update job and the paused VM update. build/probe-judge.py reads the same table.
struct ChainKey {
    std::uintptr_t offset;
    const char* name;
};
inline constexpr ChainKey kChainKeys[] = { { 0x640E67, "post-process" }, { 0x5B36AD, "paused-tasks" }, { 0x5C770C, "hit-task" },
    { 0x7211EF, "hit-frame" }, { 0x63FCC9, "ui-job" }, { 0x5B35BF, "main-ui" }, { 0x5B3F48, "poll-controls" },
    { 0x5B33B5, "paused-input" }, { 0x640623, "vm-job" }, { 0x5B3381, "paused-vm" } };

constexpr bool On(float level) noexcept
{
    return level >= kLevel;
}

// ---------------------------------------------------------------- names

inline constexpr const char* kElement[12] = { "none", "fire", "frost", "shock", "earth", "wind", "blood", "divine", "poison",
    "water", "dark", "astral" };

constexpr const char* ElementName(int element) noexcept
{
    return element >= 0 && element < 12 ? kElement[element] : "?";
}

constexpr const char* OpName(Op op) noexcept
{
    constexpr const char* names[] = { "Apply", "Remove", "Mark", "Unmark", "BleedDot", "PoisonDot", "RemoveDots", "Slow", "Damage",
        "Heal", "RestoreMagicka", "RestoreStamina", "PayHealth", "Wash", "Event", "BleedDrain", "Resonance", "Interrupt",
        "SpendMagicka", "PayStamina", "DrainStamina", "Riposte", "DispelMarkOn", "GuardPool", "CrushArea", "FreezeNearby",
        "HurtHealth", "DrainMagicka", "HealTarget", "Silence", "Hush", "Timed", "Noop", "StaminaTarget" };
    static_assert(std::size(names) == static_cast<int>(Op::kStaminaTarget) + 1);
    const int i = static_cast<int>(op);
    return i >= 0 && i < static_cast<int>(std::size(names)) ? names[i] : "?";
}

constexpr const char* EventName(Event e) noexcept
{
    constexpr const char* names[] = { "Open", "End", "Frozen", "Hallucinate", "Judgment", "Splash", "Shatter", "Landing", "Rise",
        "Discharge", "Blade", "Knock", "SyncUp", "Cleanse", "Lethal", "Push", "Ash", "Raise", "Sneak", "Domain", "Overheat",
        "Switch", "Close" };
    static_assert(std::size(names) == static_cast<int>(Event::kCount));
    const int i = static_cast<int>(e);
    return i >= 0 && i < static_cast<int>(std::size(names)) ? names[i] : "-";
}

// A status kind by its record (ESSB_N3_Freeze -> N3_Freeze), the name the probe sheet greps for.
constexpr std::string_view KindName(StatusKind kind) noexcept
{
    const int i = static_cast<int>(kind);
    if (i < 0 || i >= kStatusKindCount) {
        return "-";
    }
    std::string_view id = kStatusRecords[i].editorId;
    return id.starts_with("ESSB_") ? id.substr(5) : id;
}

constexpr const char* EndReasonName(int reason) noexcept
{
    return reason == 0 ? "cut" : reason == 1 ? "burst" : reason == 2 ? "expire" : "?";
}

// HitMath.h Cast (the steps of a hit's plan: the proc and the no-form drains).
constexpr const char* CastName(Cast cast) noexcept
{
    constexpr const char* names[] = { "Proc", "DrainMagicka", "DrainStamina", "TrueDamage", "SoakSlow", "DispelMark", "Silence",
        "HushSpent", "Heal", "RestoreMagicka", "RestoreStamina", "SpendMagicka", "BloodGuard" };
    static_assert(std::size(names) == static_cast<int>(Cast::kBloodGuard) + 1);
    const int i = static_cast<int>(cast);
    return i >= 0 && i < static_cast<int>(std::size(names)) ? names[i] : "?";
}

// A tagged effect (StatusEngine.h / Status.h TagOf) by name: N3_Frozen, Mark_fire, BleedDot, PoisonDot, Fear, Frenzy,
// Slow, GuardPool, Hush.
inline std::string TagName(const Tag& tag)
{
    switch (tag.kind) {
    case TagKind::kStatus: return std::string(KindName(static_cast<StatusKind>(tag.index)));
    case TagKind::kMark: return std::string("Mark_") + ElementName(tag.index);
    case TagKind::kBleedDot: return "BleedDot";
    case TagKind::kPoisonDot: return "PoisonDot";
    case TagKind::kFear: return "Fear";
    case TagKind::kFrenzy: return "Frenzy";
    case TagKind::kSlow: return "Slow";
    case TagKind::kGuardPool: return "GuardPool";
    case TagKind::kHush: return "Hush";
    default: return "-";
    }
}

// The cooldown statuses (every kind whose record is a …Cooldown) on a board: "RetortCooldown:2.1,CrossCooldown:0.4" or "-".
inline std::string Cooldowns(const Board& board)
{
    std::string out;
    char one[64];
    for (int k = 0; k < kStatusKindCount; ++k) {
        const std::string_view id = kStatusRecords[k].editorId;
        if (!board.slot[k].has || id.find("Cooldown") == std::string_view::npos) {
            continue;
        }
        const std::string_view name = KindName(static_cast<StatusKind>(k));
        const int n = std::snprintf(one, sizeof(one), "%s%.*s:%.1f", out.empty() ? "" : ",", static_cast<int>(name.size()), name.data(),
            board.slot[k].Remaining());
        out.append(one, static_cast<std::size_t>(std::max(0, std::min(n, static_cast<int>(sizeof(one)) - 1))));
    }
    return out.empty() ? std::string("-") : out;
}

// ---------------------------------------------------------------- one line

// The engine facts of one actor at the moment of the line: name(0xFormID)[h=cur/max m=cur/max s=cur/max].
struct ActorFacts {
    bool has = false;
    std::string_view name{};
    std::uint32_t formId = 0;
    float h = 0.0f, hMax = 0.0f, m = 0.0f, mMax = 0.0f, s = 0.0f, sMax = 0.0f;
    bool dead = false;
};

// One line's body, built in place (no allocation); anything past kMaxLine is cut and the line ends in "~".
class Line
{
public:
    explicit Line(const char* kind) noexcept : kind_(kind) { buf_[0] = '\0'; }

    const char* Kind() const noexcept { return kind_; }
    std::string_view Body() const noexcept { return { buf_, n_ }; }
    bool Cut() const noexcept { return cut_; }

    Line& F(const char* format, ...) noexcept
    {
        if (n_ >= kMaxLine) {
            cut_ = true;
            return *this;
        }
        va_list args;
        va_start(args, format);
        const int wrote = std::vsnprintf(buf_ + n_, kMaxLine + 1 - n_, format, args);
        va_end(args);
        if (wrote < 0) {
            return *this;
        }
        if (n_ + static_cast<std::size_t>(wrote) > kMaxLine) {
            n_ = kMaxLine;
            cut_ = true;
        } else {
            n_ += static_cast<std::size_t>(wrote);
        }
        return *this;
    }

    // " key=Name(0x0001A2B3)[h=… m=… s=…]" (a name's spaces stay; brackets and control characters become '_').
    Line& Actor(const char* key, const ActorFacts& a) noexcept
    {
        if (!a.has) {
            return F(" %s=-", key);
        }
        char name[64];
        std::size_t k = 0;
        for (const char c : a.name) {
            if (k + 1 >= sizeof(name)) {
                break;
            }
            const auto u = static_cast<unsigned char>(c);
            name[k++] = (u < 0x20 || c == '(' || c == ')' || c == '[' || c == ']' || c == '=') ? '_' : c;
        }
        if (k == 0) {
            name[k++] = '?';
        }
        name[k] = '\0';
        return F(" %s=%s(0x%08X)[h=%.1f/%.1f m=%.1f/%.1f s=%.1f/%.1f%s]", key, name, a.formId, a.h, a.hMax, a.m, a.mMax, a.s, a.sMax,
            a.dead ? " dead" : "");
    }

private:
    const char* kind_;
    char buf_[kMaxLine + 1];
    std::size_t n_ = 0;
    bool cut_ = false;
};

// " op=Apply who=target at=0 kind=N3_Freeze el=none mag=3.00 sec=6.00" (+ " ev=End args=a|b|…" for an event or a body
// the body pass consumed). Every op line has the same keys, so one pattern reads them all.
inline void DescribeOp(Line& line, const StatusOp& op) noexcept
{
    const std::string_view kind = op.kind == StatusKind::kCount ? std::string_view("-") : KindName(op.kind);
    line.F(" op=%s who=%s at=%d kind=%.*s el=%s mag=%.2f sec=%.2f", OpName(op.op), op.who == Who::kPlayer ? "you" : "target",
        static_cast<int>(op.at), static_cast<int>(kind.size()), kind.data(), ElementName(op.element), op.magnitude, op.seconds);
    if (op.event != Event::kCount && (op.op == Op::kEvent || op.op == Op::kNoop)) {
        line.F(" ev=%s args=%g|%g|%g|%g|%g|%g|%g|%g", EventName(op.event), op.arg[0], op.arg[1], op.arg[2], op.arg[3], op.arg[4],
            op.arg[5], op.arg[6], op.arg[7]);
        if (op.event == Event::kEnd) {
            line.F(" reason=%s", EndReasonName(static_cast<int>(op.arg[1] + 0.5f)));
        }
    }
}

// " steps=Proc:11.23,DrainMagicka:10.50,Silence:0.00/2s" -- the casts of a hit's plan (HitMath.h Plan).
inline void DescribeHitPlan(Line& line, const Plan& plan) noexcept
{
    line.F(" steps=");
    if (plan.count == 0) {
        line.F("-");
    }
    for (int i = 0; i < plan.count; ++i) {
        const CastStep& s = plan.steps[i];
        line.F("%s%s:%.2f", i ? "," : "", CastName(s.cast), s.magnitude);
        if (s.seconds > 0) {
            line.F("/%ds", s.seconds);
        }
    }
}

// The step marker: "[ESSB][STEP] 17 #… g=… r=… via=key".
inline int StepPrefix(char* out, std::size_t cap, int station, std::uint64_t seq, std::uint64_t game, std::uint64_t real, const char* via) noexcept
{
    return std::snprintf(out, cap, "[ESSB][STEP] %d #%llu g=%llu r=%llu via=%s", station, static_cast<unsigned long long>(seq),
        static_cast<unsigned long long>(game), static_cast<unsigned long long>(real), via);
}

// ---------------------------------------------------------------- the line kinds the probe sheet reads most
// (Plugin.cpp fills them from the engine; native/tests/trace_test.cpp from its fake world -- one format for both.)

// op: one StatusOp as the executor runs it -- the event's label, the op, the actor it acts on, the instance it replaces
// or removes (`count` instances found before the dispel; the first one's magnitude and time left) and what is cast.
inline void OpLine(Line& line, const char* ctx, const StatusOp& op, const ActorFacts& on, const Lowered& l, int count, float was,
    float left) noexcept
{
    line.F(" ctx=%s", ctx);
    DescribeOp(line, op);
    line.Actor("on", on);
    if (l.dispelSpell || l.dispelEffect) {
        if (count > 0) {
            line.F(" was=%.2f left=%.2f n=%d", was, left, count);
        } else {
            line.F(" was=-");
        }
    }
    if (l.spell) {
        line.F(" cast=0x%06X cast_mag=%.2f eff=%.4f", l.spell, l.magnitude, l.effectiveness);
    }
}

// op-done: the actor right after an op that changes a value (StatusEngine.h ChangesValue); ref = the op line's number.
inline void OpDoneLine(Line& line, std::uint64_t ref, const ActorFacts& on) noexcept
{
    line.F(" ref=#%llu", static_cast<unsigned long long>(ref));
    line.Actor("on", on);
}

// proc: one element proc or no-form hit, the target before it lands, the plan's casts and the draws it took.
inline void ProcLine(Line& line, const char* src, const ActorFacts& target, const ActorFacts& you, const Plan& plan, const Attack& attack,
    int weaponType, std::string_view spell, int charges, float critBonus, std::string_view rolls) noexcept
{
    line.F(" src=%s", src);
    line.Actor("tgt", target);
    line.Actor("you", you);
    line.F(" el=%s spell=%.*s weapon=%d power=%d sneak=%d leftHand=%d mag=%.2f crit=%d", ElementName(plan.element),
        static_cast<int>(spell.size()), spell.data(), weaponType, attack.power ? 1 : 0, attack.sneakAttack ? 1 : 0, attack.leftHand ? 1 : 0,
        plan.magnitude, plan.crit ? 1 : 0);
    if (plan.element == kLightning) {
        line.F(" N=%d charges=%d critChance=%.3f", LightningRolls(charges), charges, LightningCritChance(charges) + critBonus);
    } else {
        line.F(" charges=%d", charges);
    }
    line.F(" siphon=%.2f burned=%.2f dispel=%d overloadAfter=%.2f overloaded=%d silenced=%d echo=%d riposte=%d", plan.siphon, plan.burned,
        plan.dispel ? 1 : 0, plan.overloadAfter, plan.overloaded ? 1 : 0, plan.silenced ? 1 : 0, plan.consumeEcho ? 1 : 0,
        plan.consumeRiposte ? 1 : 0);
    DescribeHitPlan(line, plan);
    line.F(" rolls=%.*s", static_cast<int>(rolls.size()), rolls.data());
}

// hit-end: the target and you once everything the hit did has run (the proc, the statuses, the bodies, the repeats).
inline void HitEndLine(Line& line, const ActorFacts& target, const ActorFacts& you, int ops) noexcept
{
    line.Actor("tgt", target);
    line.Actor("you", you);
    line.F(" ops=%d", ops);
}

// remove: one effect of ours leaving an actor, and why.
inline void RemoveLine(Line& line, const ActorFacts& on, const Tag& tag, float magnitude, float elapsed, float duration, const char* reason)
{
    const std::string name = TagName(tag);
    line.Actor("on", on);
    line.F(" tag=%s mag=%.2f elapsed=%.2f duration=%.2f left=%.2f reason=%s", name.c_str(), magnitude, elapsed, duration,
        std::max(0.0f, duration - elapsed), reason);
}

// hurt: a hit you took -- the facts the sink and the task read, the cooldowns before the plan.
inline void HurtLine(Line& line, const ActorFacts& attacker, const ActorFacts& you, const HurtFacts& f, int form, int ops,
    std::string_view cdYou, std::string_view cdAttacker) noexcept
{
    line.Actor("att", attacker);
    line.Actor("you", you);
    line.F(" before=%.2f after=%.2f lost=%.2f melee=%d spell=%d destructive=%d blocked=%d cloak=%d afterimage=%d linger=%d "
           "guardBefore=%.2f guardLeft=%.2f overloadBefore=%.2f magickaBefore=%.2f magickaNow=%.2f dot=%.2f form=%d ops=%d",
        f.healthBefore, f.healthAfter, std::max(0.0f, f.healthBefore - f.healthAfter), f.melee ? 1 : 0, f.spell ? 1 : 0, f.destructive ? 1 : 0,
        f.blocked ? 1 : 0, f.cloakTick ? 1 : 0, f.afterimage ? 1 : 0, f.linger ? 1 : 0, f.guardBefore, f.guardLeft, f.overloadBefore,
        f.magickaBefore, f.magicka, f.dotDamage, form, ops);
    line.F(" cd_you=%.*s cd_att=%.*s", static_cast<int>(cdYou.size()), cdYou.data(), static_cast<int>(cdAttacker.size()), cdAttacker.data());
}

// second: once a game-running second while a form is open (or the second did something).
inline void SecondLine(Line& line, int form, const FormSecond& fs, bool read, float dH, float dM, float dS, const ActorFacts& you) noexcept
{
    line.F(" form=%s spent=%.2f bled=%.2f flow=%.4f close=%d storm=%d", ElementName(form), fs.spent, fs.bled, fs.flow, fs.closing ? 1 : 0,
        fs.charged ? 1 : 0);
    if (read) {
        line.F(" dH=%+.2f dM=%+.2f dS=%+.2f", dH, dM, dS);
    } else {
        line.F(" dH=- dM=- dS=-");
    }
    line.Actor("you", you);
}

// env: every environment check (every 5 game-running seconds).
inline void EnvLine(Line& line, const EnvFlags& e, const EnvFacts& f, bool changed) noexcept
{
    line.F(" wet=%d stormy=%d thunder=%d night=%d changed=%d classification=%d lightning=%d wind=%d hour=%.2f interior=%d swimming=%d underwater=%d",
        e.wet ? 1 : 0, e.stormy ? 1 : 0, e.thunder ? 1 : 0, e.night ? 1 : 0, changed ? 1 : 0, f.weather, static_cast<int>(f.lightning),
        static_cast<int>(f.wind), f.hour, f.interior ? 1 : 0, f.swimming ? 1 : 0, f.underwater ? 1 : 0);
}

// switch: a hotkey or the Z power asked for a form.
inline void SwitchLine(Line& line, const char* via, int wanted, const SwitchPlan& p, const SwitchFacts& f, const ActorFacts& you) noexcept
{
    constexpr const char* kinds[] = { "ignore", "refuse", "open", "switch", "close" };
    line.F(" via=%s wanted=%s kind=%s element=%s active=%d current=%s dead=%d enabled=%d freePass=%d freeOpen=%d gate=%.2f", via,
        ElementName(wanted), kinds[static_cast<int>(p.kind)], ElementName(p.element), f.active ? 1 : 0, ElementName(f.current), f.dead ? 1 : 0,
        f.enabled ? 1 : 0, f.freePass ? 1 : 0, f.freeOpen ? 1 : 0, f.magickaMax * n6::kMagickaGate);
    line.Actor("you", you);
}

// key: a bound hotkey pressed -- whether gameplay took it and why not.
inline void KeyLine(Line& line, int code, int element, const InputGate& g, unsigned long thread) noexcept
{
    line.F(" code=%d element=%s verdict=%s paused=%d menu=%d console=%d text=%d loading=%d thread=%lu", code, ElementName(element),
        InputOpen(g) ? "accepted" : "blocked", g.paused ? 1 : 0, g.menu ? 1 : 0, g.console ? 1 : 0, g.textEntry ? 1 : 0, g.loading ? 1 : 0, thread);
}

// ---------------------------------------------------------------- the buffer

// Every line of the probe log (and, while it is on, every other line of the DLL, so the file keeps one order) goes here;
// the sequence number is given under the lock, so the file's order is the numbers' order. Thread-safe.
class Buffer
{
public:
    // Appends "[ESSB][T][kind] #seq g= r= body"; returns the line's sequence number. `flushNow` says the buffer is due.
    std::uint64_t Add(const Line& line, std::uint64_t game, std::uint64_t real, bool& flushNow)
    {
        std::lock_guard lock(mutex_);
        const std::uint64_t seq = ++seq_;
        if (text_.size() >= kMaxBuffer) {
            ++dropped_;
            flushNow = true;
            return seq;
        }
        char head[96];
        const int n = std::snprintf(head, sizeof(head), "[ESSB][T][%s] #%llu g=%llu r=%llu", line.Kind(), static_cast<unsigned long long>(seq),
            static_cast<unsigned long long>(game), static_cast<unsigned long long>(real));
        text_.append(head, static_cast<std::size_t>(std::max(0, std::min(n, static_cast<int>(sizeof(head)) - 1))));
        Clean(line.Body());
        if (line.Cut()) {
            text_ += '~';
        }
        text_ += '\n';
        flushNow = text_.size() >= kFlushBytes;
        return seq;
    }

    // The step marker, numbered in the same sequence.
    std::uint64_t Step(int station, std::uint64_t game, std::uint64_t real, const char* via, bool& flushNow)
    {
        std::lock_guard lock(mutex_);
        const std::uint64_t seq = ++seq_;
        char line[160];
        const int n = StepPrefix(line, sizeof(line), station, seq, game, real, via);
        text_.append(line, static_cast<std::size_t>(std::max(0, std::min(n, static_cast<int>(sizeof(line)) - 1))));
        text_ += '\n';
        flushNow = text_.size() >= kFlushBytes;
        return seq;
    }

    // Any other line of the DLL while the probe log is on (kept in order with the numbered ones, not numbered itself).
    void Raw(std::string_view line, bool& flushNow)
    {
        std::lock_guard lock(mutex_);
        if (text_.size() >= kMaxBuffer) {
            ++dropped_;
            flushNow = true;
            return;
        }
        Clean(line.substr(0, std::min<std::size_t>(line.size(), kMaxLine + 160)));
        text_ += '\n';
        flushNow = text_.size() >= kFlushBytes;
    }

    // What is waiting (the caller writes it); the buffer starts again empty. `dropped` = lines lost since the last take.
    std::string Take(std::uint64_t& dropped)
    {
        std::lock_guard lock(mutex_);
        std::string out;
        out.swap(text_);
        dropped = dropped_;
        dropped_ = 0;
        return out;
    }

    std::uint64_t Sequence() const
    {
        std::lock_guard lock(mutex_);
        return seq_;
    }

private:
    void Clean(std::string_view body)
    {
        for (const char c : body) {
            text_ += (c == '\n' || c == '\r') ? ' ' : c;
        }
    }

    mutable std::mutex mutex_;
    std::string text_;
    std::uint64_t seq_ = 0;
    std::uint64_t dropped_ = 0;
};

// ---------------------------------------------------------------- the random draws

// SplitMix64 with a tape: exactly the same draws (the same generator, called the same way), and while recording each draw
// is kept -- "R(10,12)=11.234 C(0.07)=0 I(1,25)=17" -- so a proc's rolls, lightning's N rolls and every chance a plan
// took (the interrupt, 殘影, 幻影, the plague) are in the log. Recording off: one bool test per draw.
class TraceRng
{
public:
    explicit constexpr TraceRng(std::uint64_t seed) noexcept : rng_(seed) {}

    int Int(int lo, int hi) noexcept
    {
        const int v = rng_.Int(lo, hi);
        Note('I', static_cast<float>(lo), static_cast<float>(hi), static_cast<float>(v));
        return v;
    }
    float Real(float lo, float hi) noexcept
    {
        const float v = rng_.Real(lo, hi);
        Note('R', lo, hi, v);
        return v;
    }
    bool Chance(float probability) noexcept
    {
        const bool v = rng_.Chance(probability);
        Note('C', probability, 0.0f, v ? 1.0f : 0.0f);
        return v;
    }

    void Record(bool on) noexcept
    {
        recording_ = on;
        count_ = 0;
        more_ = 0;
    }
    bool Recording() const noexcept { return recording_; }
    int Count() const noexcept { return count_ + more_; }

    // The draws since Record(true), as text (at most kTape; "+N more").
    std::string Tape() const
    {
        std::string out;
        char one[64];
        for (int i = 0; i < count_; ++i) {
            const Draw& d = tape_[i];
            int n = 0;
            if (d.kind == 'C') {
                n = std::snprintf(one, sizeof(one), "%sC(%.4g)=%d", i ? " " : "", d.a, d.v > 0.5f ? 1 : 0);
            } else if (d.kind == 'I') {
                n = std::snprintf(one, sizeof(one), "%sI(%d,%d)=%d", i ? " " : "", static_cast<int>(d.a), static_cast<int>(d.b), static_cast<int>(d.v));
            } else {
                n = std::snprintf(one, sizeof(one), "%sR(%.4g,%.4g)=%.4f", i ? " " : "", d.a, d.b, d.v);
            }
            out.append(one, static_cast<std::size_t>(std::max(0, std::min(n, static_cast<int>(sizeof(one)) - 1))));
        }
        if (more_ > 0) {
            std::snprintf(one, sizeof(one), " +%d more", more_);
            out += one;
        }
        return out.empty() ? std::string("-") : out;
    }

private:
    struct Draw {
        char kind = 0;
        float a = 0.0f, b = 0.0f, v = 0.0f;
    };

    void Note(char kind, float a, float b, float v) noexcept
    {
        if (!recording_) {
            return;
        }
        if (count_ < kTape) {
            tape_[count_++] = Draw{ kind, a, b, v };
        } else {
            ++more_;
        }
    }

    SplitMix64 rng_;
    bool recording_ = false;
    int count_ = 0;
    int more_ = 0;
    std::array<Draw, kTape> tape_{};
};

}  // namespace essb::trace
