#pragma once
// Round 25 (slice N6): the DLL's per-second work, the DLL halves of the domains (領域) and the hotkey decisions. Pure:
// no engine, no global state. Plugin.cpp reads the engine (actor values, effect lists, the hazards near you, the input
// event, the menus) into the facts below, calls these and executes the StatusPlan they return (native/tests/timer_test.cpp
// runs the same functions on the scenarios of build/fix25_reference.py, written from the v0.4 text).
//
//   Step           the timer's clock: the 100 ms timer thread posts one task per tick (native-verification-3 s12); the
//                  task counts only the time the game is running (not paused, no menu, not loading: probe N6-1) and says
//                  when a second (and every 5 s the environment) is due -- it never catches up missed seconds
//   PlanFormSecond 1.1 維持費 (each form, magicka; blood pays health), 魔力歸零 2 秒關閉, 5.11 長流 (health, stamina and
//                  80% of the water upkeep in magicka) and 長河 (allies), 2.10 雷雨 (+1 charge every 3 s)
//   Environment    2.10: rain / snow outdoors or swimming (wet), 暴風雪 = snow with high wind (stormy), 雷雨 = rain
//                  with thunder / lightning (thunder), 20:00-6:00 (night)
//   Domains        who stands in which live domain (the hazards the engine owns, R4), what it does to you each second
//                  (火域 fuse +5 s on entry and heat without waiting, 冰原 slow immunity, 血池 / 聖域 / 潮池 回復, 潮池 洗淨)
//                  and to an enemy inside (冰原 slow, 毒霧 +1 dose merged into its poison (R5), 潮池 one buff washed,
//                  死域 dark damage, 地裂 knock at 0 stamina); Status.h DomainSpawnSpell names the spell that places
//                  one (StatusEngine.h RunOp casts it for the ESSB_Domain event of a fusion)
//   Slows          which of your effects are a slow (定神／御風 at sync 3 and 冰原 make you immune)
//   Hotkeys        the key code of an input event, whether input reaches gameplay (not in the console, a text box or a
//                  menu: probe N6-2), which form a key switches to, and PlanSwitch (v0.4 1.1: opening needs 10% magicka --
//                  blood none, 順轉 and 免門檻 waive it; the same element closes; a switch needs nothing)
//
// Every number is v0.4's (or the one the Papyrus it replaces used, where v0.4 gives none -- named in the comment).
#include "Reactions.h"
#include "SelfLayer.h"
#include "Status.h"

#include <algorithm>
#include <array>
#include <cstdint>

namespace essb {

namespace n6 {
inline constexpr std::uint64_t kSecondMs = 1000;
inline constexpr std::uint64_t kEnvMs = 5000;         // 2.10：環境偵測每 5 秒一次
inline constexpr std::uint64_t kStepCapMs = 250;      // one timer step counts at most this (a stall is not game time)
inline constexpr float kMagickaGate = 0.1f;           // 1.1 開形態需要魔力高於上限的 10%
inline constexpr float kManaEmptyClose = 2.0f;        // 1.1 魔力歸零持續 2 秒自動關閉形態
inline constexpr float kManaEmptySlack = 0.5f;        // counted in timer seconds: the 3rd empty second (elapsed ~2.0 >= 1.5)
inline constexpr float kManaEmptyClock = 3600.0f;     // the marker only has to outlive the wait
inline constexpr float kFlowMagickaShare = 0.8f;      // 5.11 長流另回「水形態魔力維持費的 80%」
inline constexpr float kFlowSyncPerPoint = 0.0005f;   // 5.11 大師主線：同調每段長流回復 +0.05%／點
inline constexpr float kFlowRiverPerPoint = 0.0005f;  // 5.11 傳奇主線：長河，同調三段時再 +0.05%／點
inline constexpr float kRiverRadius = 420.0f;         // 長河「附近同伴」：6 公尺（Papyrus ScanAllies(420)）
inline constexpr int kRiverAllies = 5;
inline constexpr float kStormCharge = 3.0f;           // 2.10 雷雨：雷形態每 3 秒自動 +1 電荷
inline constexpr float kNightFrom = 20.0f;            // 2.10 夜晚 20:00–6:00
inline constexpr float kNightTo = 6.0f;
// 審查修正 (v0.4 2.10: 雷雨 and 暴風雪 are not "any rain or snow"). From Skyrim.esm's WTHR DATA: thunderLightningFrequency
// is 255 on every weather without lightning and 246 on SkyrimStormRain*; windSpeed is 178 on SkyrimStormSnow, 76 on
// SkyrimOvercastSnow, 102 on SkuldafnCloudy (snow), 0 on BlackreachWeather.
inline constexpr std::uint8_t kNoLightning = 255;     // thunderLightningFrequency: this weather has no lightning
inline constexpr std::uint8_t kBlizzardWind = 128;    // windSpeed (0-255 = 0-1): a snow weather at half wind or more
inline constexpr float kDomainRadius = 210.0f;        // 2.9：融斷後留下的領域 3 公尺
inline constexpr float kDomainScan = 4200.0f;         // the domains the DLL looks for: within 60 m of you
inline constexpr float kWindow = 2.0f;                // the windows the per-second work refreshes (you in 火域 / 冰原)
inline constexpr float kPlainSlow = 50.0f;            // 冰原：內部敵人減速 50%
inline constexpr float kPlainSlowSeconds = 2.0f;
inline constexpr float kPoolHeal = 20.0f;             // 血池：你在其中每秒回血（v0.4 沒寫量；round 21 審查修正的 20）
inline constexpr float kSanctumHeal = 25.0f;          // 聖域：你持續回復（同上：生命 25、魔力 20）
inline constexpr float kSanctumMagicka = 20.0f;
inline constexpr float kTideHeal = 15.0f;             // 潮池：你在其中回血回耐力（同上：各 15）並每秒洗淨一次
inline constexpr float kTideStamina = 15.0f;
inline constexpr float kDeathZone = 0.5f;             // 死域：每秒受 B_max ×0.5 暗傷（D_react, 2.7; ×ESSB_MultDot）
inline constexpr float kRiftKnock = 2.0f;             // 地裂：耐力歸 0 跌倒（推力 2.0，同地動：推不倒的不改減速）
inline constexpr float kPurgeTideRefund = 2.0f;       // 淨潮：每個被沖刷的增益回 B_max(水) ×2（PapyrusWashBuffs 同）
}  // namespace n6

// ================================================================ the clock

// The timer task's clock (plumbing, not design state: it lives in the DLL's state only to pace the task).
struct Cadence {
    std::uint64_t last = 0;                 // the previous step (GetTickCount64 ms); 0 = none yet
    std::uint64_t active = 0;               // game-running ms counted so far
    std::uint64_t nextSecond = n6::kSecondMs;
    std::uint64_t nextEnv = 0;              // the environment at the first running step
};

struct Beat {
    bool second = false;   // the per-second work is due
    bool env = false;      // the 5 s environment check is due
    float seconds = 0.0f;  // game-running seconds since the previous step (the sprint refund)
};

// One timer step at `now`. `stopped`: paused, a menu, loading -- nothing is counted and nothing is due. A stall longer
// than kStepCapMs counts as kStepCapMs; a second that was missed is dropped, never made up.
constexpr Beat Step(Cadence& c, std::uint64_t now, bool stopped) noexcept
{
    Beat b;
    if (c.last == 0 || now < c.last) {
        c.last = now;
        return b;
    }
    const std::uint64_t dt = std::min(now - c.last, n6::kStepCapMs);
    c.last = now;
    if (stopped) {
        return b;
    }
    c.active += dt;
    b.seconds = static_cast<float>(dt) / 1000.0f;
    if (c.active >= c.nextSecond) {
        b.second = true;
        c.nextSecond += n6::kSecondMs;
        if (c.nextSecond <= c.active) {
            c.nextSecond = c.active + n6::kSecondMs;
        }
    }
    if (c.active >= c.nextEnv) {
        b.env = true;
        c.nextEnv = c.active + n6::kEnvMs;
    }
    return b;
}

// ================================================================ the forms' second (1.1, 2.10, 5.11)

// The globals the per-second work reads besides Tuning (ESSB_MultUpkeep, the two 長流 balance GLOBs).
struct TimerTuning {
    float multUpkeep = 1.0f;       // ESSB_MultUpkeep (MCM 維持費 0-3)
    float flowBasePct = 2.0f;      // ESSB_WaterFlowBasePct: 長流 2.0%／秒
    float flowPerRankPct = 0.2f;   // ESSB_WaterFlowPerRankPct: 熟練主線 +0.2%／點
};

template <class Global>
constexpr TimerTuning ReadTimerTuning(Global&& global)
{
    TimerTuning t;
    t.multUpkeep = global(glob::kMultUpkeep);
    t.flowBasePct = global(glob::kWaterFlowBasePct);
    t.flowPerRankPct = global(glob::kWaterFlowPerRankPct);
    return t;
}

// 1.1 維持費: max magicka × base% × (1 − 0.7 × tree level / 100) × the MCM slider; darkness 2.0%, the rest 1.0%
// (settings.json upkeep_*); the tree level is clamped to 1..100 (Papyrus ESSBFormRules.MagickaUpkeep).
constexpr float MagickaUpkeep(int element, float magickaMax, const Tuning& t, const TimerTuning& tt) noexcept
{
    if (!IsElement(element) || element == kBlood) {
        return 0.0f;
    }
    const float level = std::clamp(t.level[TreeOf(element)], 1.0f, 100.0f);
    const float pct = element == kDarkness ? kUpkeepDarkPct : kUpkeepBasePct;
    return std::max(0.0f, magickaMax * pct * 0.01f * (1.0f - kUpkeepLevelRelief * level / 100.0f) * tt.multUpkeep);
}

// 1.1 血位表「損血（維持每秒）」: 100% 1.0%, 70% 0.6%, 30% 0.2%, 10% and below 0, linear between (a fraction of max
// health per second).
constexpr float BloodUpkeepFraction(float healthFraction) noexcept
{
    const float f = std::clamp(healthFraction, 0.0f, 1.0f);
    float pct = 0.0f;
    if (f >= 0.7f) {
        pct = 0.6f + (f - 0.7f) * (0.4f / 0.3f);
    } else if (f >= 0.3f) {
        pct = 0.2f + (f - 0.3f) * (0.4f / 0.4f);
    } else if (f >= 0.1f) {
        pct = (f - 0.1f) * (0.2f / 0.2f);
    }
    return pct / 100.0f;
}

// 5.11 長流: health and stamina a second = (2.0% + 0.2%／點 熟練) + 0.05%／點 大師 × sync stage (+ 0.05%／點 長河 at stage
// 3), as a fraction of the max. Not node-scaled (build/fix6-classification: 回復類不吃節點倍率).
template <NodeReader Nodes>
constexpr float FlowFraction(const Tuning& t, const TimerTuning& tt, const Nodes& nodes)
{
    float f = (tt.flowBasePct + tt.flowPerRankPct * static_cast<float>(nodes.Rank(node::kWaterFlowRate))) * 0.01f;
    f += n6::kFlowSyncPerPoint * static_cast<float>(nodes.Rank(node::kWaterFlowSync)) * static_cast<float>(t.syncStage);
    if (t.syncStage >= 3) {
        f += n6::kFlowRiverPerPoint * static_cast<float>(nodes.Rank(node::kWaterLongRiver));
    }
    return f;
}

// What the second reads about you.
struct SecondFacts {
    int form = 0;                // the form's element, 0 = none
    float magicka = 0.0f;
    float magickaMax = 0.0f;     // GetActorValueMax
    float health = 0.0f;
    float healthMax = 0.0f;      // GetActorValueMax
    float healthPermanent = 0.0f;
    float stamina = 0.0f;
    float staminaMax = 0.0f;
    bool thunder = false;        // ESSB_EnvThunder (2.10 雷雨), as the last environment check wrote it
};

// An ally 長河 reaches (op member `at`, 1..).
struct Ally {
    int at = 0;
    float healthMax = 0.0f;
    float staminaMax = 0.0f;
};

struct FormSecond {
    float spent = 0.0f;      // magicka paid (never more than you had)
    float bled = 0.0f;       // blood form: health paid on the cost path (the engine keeps 1)
    float flow = 0.0f;       // 長流's fraction this second (0 outside the water form)
    bool closing = false;    // 魔力歸零 2 秒: the form closes (ESSB_Close -> Papyrus CloseForm)
    bool charged = false;    // 雷雨 gave a charge
};

template <NodeReader Nodes, std::size_t N>
constexpr FormSecond PlanFormSecond(StatusPlan& plan, Board& me, const SecondFacts& f, const StatusInputs& in, const TimerTuning& tt,
    const Nodes& nodes, const std::array<Ally, N>& allies, int allyCount)
{
    using K = StatusKind;
    FormSecond out;
    const Tuning& t = *in.tuning;
    const Writer pw{ plan, me, Who::kPlayer };
    if (!IsElement(f.form)) {
        pw.Clear(K::kManaEmpty);
        return out;
    }
    if (f.form == kBlood) {
        // 血形態不扣魔力、不受魔力歸零關閉，改依血位扣生命（1.1；代價路徑，永遠留 1 點）。
        pw.Clear(K::kManaEmpty);
        // 審查修正: the ratio and the amount read the same maximum (the permanent health, the 血位 of every other
        // blood rule: GetActorValuePercentage's denominator).
        const float fraction = f.healthPermanent > 0.0f ? f.health / f.healthPermanent : 1.0f;
        out.bled = f.healthPermanent * BloodUpkeepFraction(fraction) * tt.multUpkeep;
        if (out.bled > 0.0f) {
            plan.Push(Amount(Op::kPayHealth, out.bled));
        }
    } else {
        const float fee = MagickaUpkeep(f.form, f.magickaMax, t, tt);
        out.spent = std::clamp(fee, 0.0f, std::max(0.0f, f.magicka));
        if (out.spent > 0.0f) {
            plan.Push(Amount(Op::kSpendMagicka, out.spent));
        }
        if (f.magicka - out.spent <= 0.0f) {
            if (!me.Has(K::kManaEmpty)) {
                pw.Set(K::kManaEmpty, 1.0f, n6::kManaEmptyClock);
            } else if (me[K::kManaEmpty].elapsed >= n6::kManaEmptyClose - n6::kManaEmptySlack) {
                pw.Clear(K::kManaEmpty);
                StatusOp close = MakeEvent(Event::kClose);
                close.who = Who::kPlayer;
                plan.Push(close);
                out.closing = true;
            }
        } else {
            pw.Clear(K::kManaEmpty);
        }
        if (f.form == kWater) {
            // 5.11 長流：生命、耐力（×回復倍率），魔力回「這筆維持費」的 80%（不吃成長、不吃回復倍率、不給同伴）。
            out.flow = FlowFraction(t, tt, nodes);
            if (f.healthMax * out.flow > 0.0f) {
                plan.Push(Amount(Op::kHeal, f.healthMax * out.flow * t.multRecovery));
            }
            if (f.staminaMax * out.flow > 0.0f) {
                plan.Push(Amount(Op::kRestoreStamina, f.staminaMax * out.flow * t.multRecovery));
            }
            if (fee > 0.0f) {
                plan.Push(Amount(Op::kRestoreMagicka, fee * n6::kFlowMagickaShare));
            }
            // 長河：同調三段時長流同時作用於附近同伴（生命與耐力）。
            if (t.syncStage >= 3 && nodes.Rank(node::kWaterLongRiver) > 0) {
                for (int i = 0; i < allyCount && i < static_cast<int>(N) && i < n6::kRiverAllies; ++i) {
                    StatusOp heal = Amount(Op::kHealTarget, allies[i].healthMax * out.flow * t.multRecovery);
                    heal.at = static_cast<std::uint8_t>(allies[i].at);
                    plan.Push(heal);
                    StatusOp stamina = Amount(Op::kStaminaTarget, allies[i].staminaMax * out.flow * t.multRecovery);
                    stamina.at = static_cast<std::uint8_t>(allies[i].at);
                    plan.Push(stamina);
                }
            }
        }
    }
    // 2.10 雷雨：雷形態每 3 秒（×冷卻倍率）自動 +1 電荷；電荷是 DLL 的效果（round 23）。
    if (f.form == kLightning && f.thunder && !me.Has(K::kStormCooldown)) {
        res::SetCharges(plan, me, me.Layers(K::kCharge) + 1, in, nodes);
        pw.Set(K::kStormCooldown, 1.0f, CooldownOf(t, n6::kStormCharge));
        out.charged = true;
    }
    return out;
}

// ================================================================ the environment (2.10)

// Papyrus Weather.GetClassification: the first of pleasant 0, cloudy 1, rainy 2, snow 3 in the weather's flags; -1 none.
constexpr int WeatherClass(std::uint8_t flags) noexcept
{
    if (flags & 0x01) {
        return 0;
    }
    if (flags & 0x02) {
        return 1;
    }
    if (flags & 0x04) {
        return 2;
    }
    if (flags & 0x08) {
        return 3;
    }
    return -1;
}

struct EnvFacts {
    int weather = -1;          // WeatherClass of the current weather (-1: none)
    std::uint8_t lightning = n6::kNoLightning;   // the weather's thunderLightningFrequency (255: none)
    std::uint8_t wind = 0;                       // the weather's windSpeed (0-255)
    bool interior = false;     // 室內、地城沒有環境加成
    bool swimming = false;
    bool underwater = false;
    float hour = 12.0f;        // the game hour
};

struct EnvFlags {
    bool wet = false;      // ESSB_EnvWet: 下雨、下雪或站在水中
    bool stormy = false;   // ESSB_EnvStormy: 暴風雪（下雪且風大）-- the hit path's 凍結累積 ×2 (round 22)
    bool thunder = false;  // ESSB_EnvThunder: 雷雨（下雨且有雷電）-- 雷形態每 3 秒 +1 電荷
    bool night = false;    // ESSB_EnvNight: 20:00–6:00
};

constexpr EnvFlags Environment(const EnvFacts& f) noexcept
{
    EnvFlags e;
    const bool outdoors = !f.interior;
    const bool weather = (f.weather == 2 || f.weather == 3) && outdoors;
    e.wet = weather || f.swimming || f.underwater;
    e.stormy = outdoors && f.weather == 3 && f.wind >= n6::kBlizzardWind;
    e.thunder = outdoors && f.weather == 2 && f.lightning != n6::kNoLightning;
    e.night = f.hour >= n6::kNightFrom || f.hour < n6::kNightTo;
    return e;
}

// ================================================================ the domains (R4)

// One live domain: a hazard of ours the engine still holds (owner = you), its element and where it lies.
struct DomainSite {
    int element = 0;
    std::array<float, 3> pos{};
};

using DomainSet = std::array<bool, kElementCount + 1>;   // [element]: inside a live domain of that element

template <std::size_t N>
constexpr DomainSet InsideOf(const std::array<DomainSite, N>& sites, int count, const std::array<float, 3>& at) noexcept
{
    DomainSet in{};
    for (int i = 0; i < count && i < static_cast<int>(N); ++i) {
        if (IsElement(sites[i].element) && Distance(sites[i].pos, at) <= n6::kDomainRadius) {
            in[sites[i].element] = true;
        }
    }
    return in;
}

struct DomainSelf {
    bool fuseExtended = false;   // 火域: you walked in white-hot (+5 s once)
    bool slowImmune = false;     // 冰原
    int cleanse = 0;             // 潮池: one cleanse this second
};

// What the live domains you stand in do to you this second. One per element however many overlap.
template <NodeReader Nodes>
constexpr DomainSelf PlanDomainSelf(StatusPlan& plan, Board& me, const DomainSet& in, const StatusInputs& inputs, const Nodes& nodes)
{
    using K = StatusKind;
    DomainSelf out;
    const Tuning& t = *inputs.tuning;
    const Writer pw{ plan, me, Who::kPlayer };
    if (in[kFire]) {
        // 火域：你在其中熱度升階免等待（DLL 的熱度讀這個視窗）；進入時白熱引信一次性 +5 秒（進入＝上一秒不在火域）。
        if (!me.Has(K::kFireDomainPlayer) && me.Has(K::kHeat3)) {
            const Slot fuse = me[K::kHeat3];
            pw.Set(K::kHeat3, fuse.magnitude, fuse.Remaining() + n3::kFireDomainExtend);
            out.fuseExtended = true;
        }
        pw.Set(K::kFireDomainPlayer, 1.0f, n6::kWindow);
    }
    if (in[kFrost]) {
        pw.Set(K::kFrostDomainPlayer, 1.0f, n6::kWindow);   // 冰原：你在其中免疫減速（每 tick 驅散你身上的減速）
        out.slowImmune = true;
    }
    if (in[kBlood]) {
        plan.Push(Amount(Op::kHeal, n6::kPoolHeal * t.multRecovery));
    }
    if (in[kDivine]) {
        plan.Push(Amount(Op::kHeal, n6::kSanctumHeal * t.multRecovery));
        plan.Push(Amount(Op::kRestoreMagicka, n6::kSanctumMagicka * t.multRecovery));
    }
    if (in[kWater]) {
        plan.Push(Amount(Op::kHeal, n6::kTideHeal * t.multRecovery));
        plan.Push(Amount(Op::kRestoreStamina, n6::kTideStamina * t.multRecovery));
        StatusOp cleanse = MakeEvent(Event::kCleanse, 0.0f);   // 洗淨一次（Papyrus ApplyCleanse：洗淨本體，round 23 決策 11）
        cleanse.who = Who::kPlayer;
        plan.Push(cleanse);
        out.cleanse = 1;
    }
    (void)nodes;
    return out;
}

// What a live domain does to an enemy inside it this second (the hazard already put the marker and, for 地裂 / 死域, the
// engine effects on it). `in.body` is that enemy's; `refund` is 淨潮's heal per washed buff (0 without the node).
template <NodeReader Nodes>
constexpr void PlanDomainEnemy(StatusPlan& plan, Board& target, const DomainSet& inside, const StatusInputs& in, const Board& me,
    const Nodes& nodes, float refund)
{
    const Tuning& t = *in.tuning;
    if (inside[kFrost]) {
        plan.Push(Amount(Op::kSlow, n6::kPlainSlow, 0, n6::kPlainSlowSeconds));   // 冰原：減速 50%（受 MCM 減速上限）
    }
    if (inside[kEarth] && in.body.stamina <= 0.0f) {
        plan.Push(MakeEvent(Event::kKnock, n6::kRiftKnock));   // 地裂：耐力歸 0 跌倒（每目標 8 秒一次由 Papyrus 推力管）
    }
    if (inside[kPoison]) {
        rule::SpreadDoses(plan, target, 1.0f, in, nodes);   // 毒霧（R5）：每秒「擴散一劑」併進牠自己的中毒
    }
    if (inside[kWater]) {
        StatusOp wash = Amount(Op::kWash, refund);   // 潮池：每秒被沖刷一個增益（不吃退潮的 10 秒冷卻）
        wash.element = 1;
        plan.Push(wash);
    }
    if (inside[kDarkness]) {
        const float amount = in.config->damage[kDarkness][1] * n6::kDeathZone * ReactionScale(kDarkness, t, in.player, nodes) *
                             ReactionVulnerability(target, me, t, nodes) * t.multDot;
        if (amount > 0.0f) {
            plan.Push(Amount(Op::kDamage, amount, kDarkness));   // 死域：每秒 B_max ×0.5 暗傷
        }
    }
}

// 審查修正: the domains the DLL looks for each second only when you hold a node that leaves one (read each second from
// your perks; nothing is cached) -- without one no hazard of yours can exist, so the 60 m cell walk is skipped.
inline constexpr std::array<BranchId, 10> kDomainNodes{ node::kFireDomain, node::kFrostPlain, node::kEarthRiftZone,
    node::kBloodPool, node::kDivineSanctum, node::kDivineHolyDomain, node::kPoisonFog, node::kWaterTidePool,
    node::kDarkDeathZone, node::kAstralZone };

template <NodeReader Nodes>
constexpr bool HasDomainNode(const Nodes& nodes)
{
    for (const BranchId& id : kDomainNodes) {
        if (nodes.Has(id)) {
            return true;
        }
    }
    return false;
}

// ================================================================ slows on you

// 冰原「你在其中免疫減速」, 5.2 定神 and 5.7 御風 (同調三段時免疫減速).
template <NodeReader Nodes>
constexpr bool SlowImmune(const Board& me, const Tuning& t, const Nodes& nodes)
{
    return me.Has(StatusKind::kFrostDomainPlayer) ||
           (t.syncStage >= 3 && (nodes.Has(node::kCommonComposure) || nodes.Has(node::kWindRideWind)));
}

// One of your running effects as the slow test reads it.
struct SlowView {
    int archetype = -1;          // RE::EffectSetting::Archetype
    int primaryAV = -1;
    int secondaryAV = -1;
    bool detrimental = false;
    float duration = 0.0f;       // 0 = a constant effect (an ability): never touched
};

inline constexpr int kArchetypeValueModifier = 0;
inline constexpr int kArchetypeDualValueModifier = 5;
inline constexpr int kArchetypePeakValueModifier = 34;
inline constexpr int kActorValueSpeedMult = 30;

// A timed, detrimental value / peak value / dual value modifier on SpeedMult.
constexpr bool IsSlow(const SlowView& v) noexcept
{
    const bool modifier = v.archetype == kArchetypeValueModifier || v.archetype == kArchetypePeakValueModifier ||
                          v.archetype == kArchetypeDualValueModifier;
    const bool speed = v.primaryAV == kActorValueSpeedMult || (v.archetype == kArchetypeDualValueModifier && v.secondaryAV == kActorValueSpeedMult);
    return modifier && speed && v.detrimental && v.duration > 0.0f;
}

// ================================================================ hotkeys (R6)

enum class Device : std::uint8_t
{
    kKeyboard = 0,
    kMouse = 1,
    kGamepad = 2,
    kOther = 3,
};

// The key code Papyrus RegisterForKey / MCM Helper keymaps use for an input event: keyboard = DirectInput scan code,
// mouse = 256 + button, gamepad = 266.. (SKSE InputMap: the XInput mask of the button; the triggers are 280 / 281).
constexpr int KeyCodeOf(Device device, std::uint32_t id) noexcept
{
    switch (device) {
    case Device::kKeyboard:
        return id < 256 ? static_cast<int>(id) : -1;
    case Device::kMouse:
        return id < 10 ? 256 + static_cast<int>(id) : -1;
    case Device::kGamepad: {
        constexpr std::uint32_t masks[] = { 0x0001, 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040, 0x0080, 0x0100, 0x0200,
            0x1000, 0x2000, 0x4000, 0x8000 };
        for (int i = 0; i < static_cast<int>(std::size(masks)); ++i) {
            if (id == masks[i]) {
                return 266 + i;
            }
        }
        if (id == 0x0009) {
            return 280;   // left trigger
        }
        if (id == 0x000A) {
            return 281;   // right trigger
        }
        return -1;
    }
    default:
        return -1;
    }
}

// Whether a key reaches gameplay (Papyrus ESSBInput: !Utility.IsInMenuMode() && !UI.IsTextInputEnabled()).
struct InputGate {
    bool paused = false;      // UI::GameIsPaused
    bool menu = false;        // a menu that pauses, uses the cursor or the menu input context, or is modal, is open
    bool console = false;
    bool textEntry = false;   // ControlMap::textEntryCount > 0
    bool loading = false;
};

constexpr bool InputOpen(const InputGate& g) noexcept
{
    return !g.paused && !g.menu && !g.console && !g.textEntry && !g.loading;
}

// The form a key press switches to (1..11; the first bound slot wins), 0 = none.
constexpr int HotkeyElement(int code, bool enabled, const std::array<int, kElementCount>& keys) noexcept
{
    if (!enabled || code <= 0) {
        return 0;
    }
    for (int i = 0; i < kElementCount; ++i) {
        if (keys[i] == code) {
            return i + 1;
        }
    }
    return 0;
}

struct SwitchFacts {
    bool enabled = true;      // ESSB_Enabled
    bool dead = false;
    bool active = false;      // ESSB_FormActive
    int current = 0;          // ESSB_CurrentElement
    float magicka = 0.0f;
    float magickaMax = 0.0f;
    bool freePass = false;    // 5.2 順轉：開形態免魔力門檻
    bool freeOpen = false;    // 5.1 免門檻：融斷後下一次開形態不需魔力（ESSB_FreeOpen）
};

enum class SwitchKind : std::uint8_t
{
    kIgnore,   // nothing (switched off, dead, not a form)
    kRefuse,   // 魔力不足，無法開啟形態
    kOpen,
    kSwitch,
    kClose,    // the same element again = close (Z)
};

struct SwitchPlan {
    SwitchKind kind = SwitchKind::kIgnore;
    int element = 0;          // what ESSB_CurrentElement becomes (0 closed)
    bool consumeFree = false; // opening from no form uses up 免門檻 (ESSB_FreeOpen -> 0)
};

constexpr SwitchPlan PlanSwitch(const SwitchFacts& f, int wanted) noexcept
{
    SwitchPlan p;
    if (!f.enabled || f.dead || !IsElement(wanted)) {
        return p;
    }
    if (f.active && f.current == wanted) {
        p.kind = SwitchKind::kClose;
        return p;
    }
    if (!f.active) {
        if (wanted != kBlood && !f.freePass && !f.freeOpen && f.magicka < f.magickaMax * n6::kMagickaGate) {
            p.kind = SwitchKind::kRefuse;
            return p;
        }
        p.kind = SwitchKind::kOpen;
        p.element = wanted;
        p.consumeFree = true;
        return p;
    }
    p.kind = SwitchKind::kSwitch;
    p.element = wanted;
    return p;
}

// The one-line notice (v0.4 1.1「形態：冰霜」; the ESSBInput wording kept).
inline constexpr const char* kFormLabels[kElementCount + 1] = { "", "火焰", "冰霜", "雷電", "大地", "風", "鮮血", "神聖", "毒素", "水",
    "黑暗", "星界" };

}  // namespace essb
