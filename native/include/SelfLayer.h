#pragma once
// Round 23 (slice N4): your own resources as engine effects the DLL reads and re-applies (v0.4 2.3 "你身上的資源", 2.4,
// 5.1-5.13). Pure, like Status.h: the planners here read two boards (the target's and yours) and push StatusOps; the
// engine side (StatusEngine.h RunPlan, Plugin.cpp) executes them. Nothing here remembers anything between calls.
//
//   BloodPowerTerms  before the hit: 血形態重擊扣血 (1.1), 回湧 (no cost, ×1.5) and 血刃 (half the paid health joins
//                    the blood proc) -- they change the proc, so they are decided before HitMath rolls it
//   PlanSelfHit      one accepted element hit: 同調 +1 and the stages, 電荷 (and 雷's N via StatusTerms), the in-form full
//                    power discharge, 雷暴, 雷神, 雷霆, 法術麻痺, 岩甲 and 碎岩, 蓄勁 / 蓄能, 地動, 風勢 and the blades, 千刃,
//                    順勢, 冰盾, 回湧's bleed, 洗淨, the dark star's strike and 餘輝, 極致, 化身, the open gains (先制, 開印時,
//                    血脈, 星門, 餘電, 誓約, 強感電, 雷鳴, 先風), 多段觸發's repeat count, 連殺's last-hit-sneak marker
//   PlanSelfOpen     a forced open without a hit (臨, 雙斷): the open gains only
//   PlanSelfNoForm   a no-form hit: 戰意 (滅法沉默 +1, 破式 uses it), 超載's pool, 斷咒, 雷霆
//   PlanSelfLeave    leaving a form: your resources clear (過載終焉 keeps the charges, 星殘 the resonance for 15 s, 墜星
//                    turns the 闇宙 into the cut settlement), the switch charge snapshot, 協奏's pending end, 護血
//   PlanSelfEnter    opening a form: the 專一 clock, 雷臨強化 (+5 charges), 地臨強化 (岩甲 full)
//   PlanSelfSecond   the DLL timer, once a second: 超載 decays after its wait
//   OnResonance      a star detonation's resonance targets (the engine counted them)
#include "Status.h"

namespace essb {

// 化身 (5.2 持續傳奇主線): for 10 s the form's 持續傳奇主線 reads as fully invested (decision 7: the passive-number ones
// "視同已取得"; the chance ones -- 地動、千刃、瘟疫 -- then fire at their best rate). Wraps the planners' node reader.
template <NodeReader Inner>
struct AvatarNodes {
    const Inner& inner;
    int element = 0;   // the form element the window was opened in (0 = no window)

    constexpr int Rank(const NodeId& id) const
    {
        if (IsElement(element)) {
            const NodeId& legend = node::kSustainLegend[element];
            if (legend.tree == id.tree && legend.route == id.route && legend.tier == id.tier) {
                return kMainMaxRank;
            }
        }
        return inner.Rank(id);
    }
    constexpr bool Has(const BranchId& id) const { return inner.Has(id); }
};

template <NodeReader Inner>
constexpr AvatarNodes<Inner> WithAvatar(const Inner& nodes, const Board& me) noexcept
{
    return AvatarNodes<Inner>{ nodes, me.Has(StatusKind::kAvatar) ? me.Layers(StatusKind::kAvatar) : 0 };
}

// What the hit handler knows besides the two boards.
struct SelfHit {
    int element = 0;             // the element of this hit's effects (雙生's left hand: the twin element)
    int formElement = 0;         // the form's element
    bool power = false;          // R 1.5 (a downed target counts)
    bool sneak = false;          // kSneakAttack (undetected)
    bool crit = false;           // the lightning proc crit (雷鳴)
    bool targetCasting = false;  // the target is casting (native-verification-3 s8), read by the engine at hit time
    float bloodCost = 0.0f;      // health this blood power hit pays (BloodPowerTerms), 0 = none
    bool surgeUp = false;        // 回湧 was used by this hit (BloodPowerTerms)
};

struct SelfResult {
    bool extraProc = false;      // 極致: one more full proc of the form's element on this target
    int repeats = 0;             // 多段觸發: repeat this hit's effects this many more times (damage ×0.5)
};

namespace res {

// v0.4 1.1: the blood power hit's cost, linear over 100% / 70% / 30% / 10% health (8% / 5% / 2% / 0 of max health).
constexpr float BloodPowerCostFraction(float healthFraction) noexcept
{
    return Interpolate(Clamp01(healthFraction), n4::kBloodPowerCost);
}

// 回湧 (5.8): a power hit in the 8 s after an upward crossing pays nothing, hits ×1.5 and adds 2 bleed layers.
constexpr bool SurgeUpReady(const Board& me) noexcept
{
    return me.Has(StatusKind::kSurgeUp);
}

}  // namespace res

// Before the hit: a blood power hit pays health (1.1, never below 1); 回湧 waives it and makes the hit ×1.5; 血刃 puts half
// of what was paid into this hit's blood proc (flat, after the multipliers). Returns the cost to pay.
template <NodeReader Nodes>
constexpr float BloodPowerTerms(int element, bool power, bool realPower, const Self& self, const Board& me, const Nodes& nodes,
    StatusTerms& terms, bool& surgeUp)
{
    surgeUp = false;
    if (element != kBlood || !power) {
        return 0.0f;
    }
    if (res::SurgeUpReady(me)) {
        surgeUp = true;
        terms.mult[kBlood] *= n4::kSurgeUpMult;
        return 0.0f;
    }
    if (!realPower) {
        return 0.0f;   // v0.4 2.1: a downed target's hit counts as a power attack, without the power attack's costs
    }
    const float cost = std::min(self.healthMax * res::BloodPowerCostFraction(self.Fraction()), std::max(0.0f, self.health - 1.0f));
    if (cost > 0.0f && nodes.Has(node::kBloodBlade)) {
        terms.flat[kBlood] += cost * n4::kBloodBlade;
    }
    return cost;
}

namespace res {

// The open gains of `element` for you (2.3 開印 +2 etc., 5.x): charges, 岩甲, 風勢, 同調, 共鳴層; returns the blades the
// open sends (疾風痕 filling the gauge, 先風). `hitPower` / `hitCrit` are false for a forced open.
template <NodeReader Nodes, RandomSource Rng>
constexpr int OpenGains(StatusPlan& plan, int element, bool hitPower, bool hitCrit, Board& target, Board& me, const StatusInputs& in,
    const Nodes& nodes, Rng& rng)
{
    const Tuning& t = *in.tuning;
    const Writer pw{ plan, me, Who::kPlayer };
    int blades = 0;
    switch (element) {
    case kLightning: {
        int gain = n4::kChargeOpen + nodes.Rank(node::kLightningOpenCharge) / 5;   // 開印電荷 +1／每 5 點
        if (hitCrit && nodes.Has(node::kLightningThunderclap)) {
            gain += n4::kThunderclap;   // 雷鳴
        }
        int charges = me.Layers(StatusKind::kCharge) + gain;
        if (hitPower && nodes.Has(node::kLightningStrongShock) && !me.Has(StatusKind::kStrongShockCooldown)) {
            charges = ChargeCap(nodes);   // 強感電：開印那一擊是重擊，電荷直接補滿（這一擊不放電）
            pw.Set(StatusKind::kStrongShockCooldown, 1.0f, CooldownOf(t, n4::kStrongShockCooldown));
        }
        SetCharges(plan, me, charges, in, nodes);
        break;
    }
    case kEarth: {
        const int gain = (nodes.Has(node::kEarthRockSkin) ? n4::kRockSkin : n4::kRockOpen) + nodes.Rank(node::kEarthOpenRock) / 5;
        SetRock(plan, me, me.Layers(StatusKind::kRockArmor) + gain, in, nodes);
        break;
    }
    case kWind: {
        const int threshold = WindThreshold(nodes);
        int gauge = nodes.Has(node::kWindGaleMark) ? threshold
                                                   : me.Layers(StatusKind::kWindGauge) + n4::kWindOpen + nodes.Rank(node::kWindOpenGauge) / 5;
        if (gauge >= threshold) {
            ++blades;   // 風勢到門檻：送出風刃後歸零（疾風痕：開印直接滿）
            gauge = 0;
        }
        SetWind(plan, me, gauge, in, nodes);
        if (t.syncStage >= 3 && nodes.Has(node::kWindFirst)) {
            ++blades;   // 先風：同調三段時開印附帶一段風刃
        }
        break;
    }
    case kDivine:
        if (nodes.Has(node::kDivineOath)) {
            Writer{ plan, target, Who::kTarget }.Set(StatusKind::kOath, 1.0f, Scaled(t, n4::kOath));   // 誓約：這個目標 8 秒內打你
        }
        break;
    case kAstral:
        if (!me.Has(StatusKind::kCosmos) && nodes.Has(node::kAstralGate)) {
            AddResonance(plan, me, n4::kStarGate, in, nodes);   // 星門：開印 +1 共鳴層（闇星中無效）
        }
        break;
    default:
        break;
    }
    // 同調 (5.2): 先制 +2, 開啟專精主線 +1／每 5 點; 血脈 (5.8) +2 on a blood open.
    int sync = nodes.Rank(node::kCommonOpenSync) / 5 + (nodes.Has(node::kCommonPreempt) ? n4::kPreempt : 0);
    if (element == kBlood && nodes.Has(node::kBloodVein)) {
        sync += n4::kBloodVein;
    }
    AddSync(plan, me, sync, in, nodes);
    // 餘電 (5.5): the takeover element's next open carries a ×0.5 discharge of the charges the lightning end had.
    if (me.Has(StatusKind::kPendingDischarge)) {
        const int charges = me.Layers(StatusKind::kPendingDischarge);
        const float crit = rng.Chance(LightningCritChance(charges) + (me.Has(StatusKind::kQuickShock) ? n4::kQuickShock : 0.0f)) ? 1.5f : 1.0f;
        plan.Push(Discharge(charges, 0.5f, 1.0f, crit));
        pw.Clear(StatusKind::kPendingDischarge);
    }
    return blades;
}

constexpr float CritFor(int charges, const Board& me, float roll, bool power) noexcept
{
    const float chance = LightningCritChance(charges) + (me.Has(StatusKind::kQuickShock) ? n4::kQuickShock : 0.0f);
    return roll < chance ? CritMultiplier(power) : 1.0f;
}

}  // namespace res

// 風的多段觸發 (2.6, 5.7): a hit that cut a wind mark repeats its effects N times in all (基礎 2, 關閉專精主線 +1／每 5 點,
// at most 5); returns the extra repetitions.
template <NodeReader Nodes>
constexpr int MultiTriggerRepeats(const HitStatus& st, const Nodes& nodes)
{
    if (st.cutFrom != kWind) {
        return 0;
    }
    return std::min(n4::kMultiMax, n4::kMultiBase + nodes.Rank(node::kWindMulti) / 5) - 1;
}

// One accepted element hit (after PlanHit and PlanStatusHit, on the boards they left). `repeat` = a 多段觸發 repetition:
// the resource +1s and the dark-star strike happen again, the one-off parts (sync, 極致, 化身, the open) do not.
template <NodeReader Nodes, RandomSource Rng>
constexpr SelfResult PlanSelfHit(StatusPlan& plan, const SelfHit& hit, const HitStatus& st, Board& target, Board& me,
    const StatusInputs& in, const Nodes& nodes, Rng& rng, bool repeat = false)
{
    const Tuning& t = *in.tuning;
    const Config& c = *in.config;
    const Writer pw{ plan, me, Who::kPlayer };
    const Writer tw{ plan, target, Who::kTarget };
    SelfResult out;
    int blades = 0;
    const bool opened = st.opened && !repeat;

    if (!repeat) {
        res::AddSync(plan, me, 1, in, nodes);   // 2.4 每有效命中 +1、到門檻換段
    }
    switch (hit.element) {
    case kLightning: {
        const int cap = res::ChargeCap(nodes);
        const int before = me.Layers(StatusKind::kCharge);
        const bool full = before >= cap;
        int charges = before;
        bool discharged = false;
        if (hit.power && full) {
            // 形態內滿格重擊放電 (2.1, 5.5): 必定暴擊 ×2.5、吃重擊倍率、清空電荷；雷印記不結束、不算終焉。
            plan.Push(res::Discharge(before, 1.0f, n4::kPower, n4::kPowerCrit));
            charges = 0;
            discharged = true;
        } else if (!hit.power && full && nodes.Has(node::kLightningStorm) && rng.Chance(n4::kStorm)) {
            // 雷暴：電荷滿時普攻 30% 放電（清空電荷，不必定暴擊）。
            plan.Push(res::Discharge(before, 1.0f, 1.0f, res::CritFor(before, me, rng.Real(0.0f, 1.0f), false)));
            charges = 0;
            discharged = true;
        }
        if (opened) {
            if (discharged) {
                res::SetCharges(plan, me, 0, in, nodes);
            }
            res::OpenGains(plan, kLightning, hit.power, hit.crit, target, me, in, nodes, rng);
            charges = me.Layers(StatusKind::kCharge);
        } else if (!discharged) {
            charges = std::min(cap, charges + 1);   // a discharging hit leaves the charges empty
        }
        if (!discharged && charges >= cap && before < cap && t.syncStage >= 3 && nodes.Has(node::kLightningGod)) {
            // 雷神：同調三段時電荷一到滿層，立即對被命中的目標自動放電並回復魔力（B_max × 電荷數，round 21 KEPT 值）。
            plan.Push(res::Discharge(charges, 1.0f, 1.0f, res::CritFor(charges, me, rng.Real(0.0f, 1.0f), false)));
            plan.Push(Amount(Op::kRestoreMagicka, c.damage[kLightning][1] * static_cast<float>(charges) * n4::kGodMagicka * t.multRecovery));
            charges = 0;
            discharged = true;
        }
        if (charges != me.Layers(StatusKind::kCharge) || !opened) {
            res::SetCharges(plan, me, charges, in, nodes);   // a hit refreshes the 10 s even at the cap
        }
        if (discharged && nodes.Has(node::kLightningQuick)) {
            pw.Set(StatusKind::kQuickShock, 1.0f, Scaled(t, n4::kQuickShockSeconds));   // 疾電
        }
        if (full && hit.targetCasting && rng.Chance(n4::kParalysis)) {
            plan.Push(MakeOp(Op::kInterrupt));   // 滿格：法術麻痺（30% 中斷詠唱）
        }
        break;
    }
    case kEarth: {
        const int cap = res::RockCap(nodes);
        const int rock = me.Layers(StatusKind::kRockArmor);
        const bool formHit = hit.formElement == kEarth;
        float quakeBonus = me.Has(StatusKind::kChargedQuake) ? me[StatusKind::kChargedQuake].magnitude : 0.0f;
        if (hit.power && rock >= cap && formHit && !repeat) {
            // 碎岩 (5.6): 滿層重擊把岩甲全部砸出：目標與 3 公尺內（最多 5 人）各受 B_max ×0.3 × 層數土傷與 ×0.5 × 層數削耐；
            // 命中的目標必定跌倒，範圍內被削到 0 的也跌倒（每目標 8 秒一次，推力在 Papyrus）。蓄能的加成用在這裡。
            const float scale = ReactionScale(kEarth, t, in.player, nodes) * (1.0f + quakeBonus);
            const float damage = static_cast<float>(rock) * c.damage[kEarth][1] * n4::kCrushDamage * scale *
                                 ReactionVulnerability(target, me, t, nodes);
            const float stamina = static_cast<float>(rock) * c.damage[kEarth][1] * n4::kCrushStamina * TreeG(t, TreeOf(kEarth)) * t.multDrain;
            plan.Push(Amount(Op::kDamage, damage, kEarth));
            plan.Push(Amount(Op::kDrainStamina, stamina));
            plan.Push(MakeEvent(Event::kKnock, n4::kKnockForce));
            StatusOp ring = MakeOp(Op::kCrushArea);
            ring.magnitude = static_cast<float>(rock) * c.damage[kEarth][1] * n4::kCrushDamage * scale;
            ring.seconds = stamina;
            plan.Push(ring);
            res::SetRock(plan, me, 0, in, nodes);
            if (quakeBonus > 0.0f) {
                pw.Clear(StatusKind::kChargedQuake);
                quakeBonus = 0.0f;
            }
        } else if (opened) {
            res::OpenGains(plan, kEarth, hit.power, hit.crit, target, me, in, nodes, rng);
        } else {
            res::SetRock(plan, me, std::min(cap, rock + 1), in, nodes);
        }
        if (hit.power && formHit && !repeat) {
            // 蓄勁 (5.6)：重擊命中 +3，上限 10；蓄能：這一擊把現有的蓄勁全部換成下一次地震／碎岩 +5%／點（v0.4「消耗全部」，
            // 蓄勁 ≥1 就換；審查修正，指揮官裁定）。
            int force = me.Layers(StatusKind::kStoredForce);
            if (force >= 1 && nodes.Has(node::kEarthCharge)) {
                pw.Set(StatusKind::kChargedQuake, quakeBonus + static_cast<float>(force) * n4::kQuakeChargePerPoint, 3600.0f);
                force = 0;
            }
            res::SetCount(plan, me, StatusKind::kStoredForce, std::min(n4::kForceCap, force + n4::kForcePower), n4::kForever);
        }
        if (hit.power && t.syncStage >= 3 && in.body.staminaMax > 0.0f && in.body.stamina / in.body.staminaMax < n4::kQuakeKnockStamina &&
            nodes.Rank(node::kEarthQuakeKnock) > 0 &&
            rng.Chance(n4::kQuakeKnockPerPoint * static_cast<float>(nodes.Rank(node::kEarthQuakeKnock)))) {
            plan.Push(MakeEvent(Event::kKnock, 2.0f));   // 地動：同調三段重擊、耐力低於 30%、機率 5%／點（推力在 Papyrus）
        }
        break;
    }
    case kWind: {
        const int threshold = res::WindThreshold(nodes);
        if (opened) {
            blades += res::OpenGains(plan, kWind, hit.power, hit.crit, target, me, in, nodes, rng);
        }
        if (hit.sneak) {
            res::SetWind(plan, me, threshold, in, nodes);   // 1.1：潛行攻擊時風勢直接滿
        } else if (!opened) {
            res::SetWind(plan, me, me.Layers(StatusKind::kWindGauge) + 1, in, nodes);
        }
        if (me.Layers(StatusKind::kWindGauge) >= threshold) {
            res::SetWind(plan, me, 0, in, nodes);   // 到門檻送出風刃後歸零
            res::Blades(plan, 1, hit.sneak && nodes.Has(node::kWindDarkWind) ? n4::kDarkWindBlade : 1.0f);   // 暗風：潛行送出的風刃 ×2
        }
        const int thousand = nodes.Rank(node::kWindThousand);
        if (t.syncStage >= 3 && thousand > 0 && rng.Chance(n4::kThousandPerPoint * static_cast<float>(thousand))) {
            ++blades;   // 千刃
        }
        break;
    }
    case kFrost:
        res::SetIceShield(plan, me, me.Layers(StatusKind::kIceShield) + 1, in, nodes);   // 冰盾：冰形態命中 +1，刷新 8 秒
        break;
    case kBlood:
        if (hit.surgeUp && !repeat) {
            pw.Clear(StatusKind::kSurgeUp);
            rule::AddBleed(plan, target, n4::kSurgeUpBleed, in, nodes);   // 回湧：那個目標血痕 +2
        } else if (hit.bloodCost > 0.0f && !repeat) {
            plan.Push(Amount(Op::kPayHealth, hit.bloodCost));   // 1.1：血形態重擊扣血（留 1 點）
        }
        break;
    case kWater:
        if (opened) {
            res::OpenGains(plan, kWater, hit.power, hit.crit, target, me, in, nodes, rng);
        }
        if (!repeat && nodes.Has(node::kWaterCleanse) && !me.Has(StatusKind::kCleanseCooldown)) {
            // 洗淨 (5.11): an element hit clears one of your negative effects (淨化: all of them), every 3 s; the dispel is
            // ESSBController.ApplyCleanse (ESSB_Cleanse).
            plan.Push(MakeEvent(Event::kCleanse, nodes.Has(node::kWaterPurify) ? 1 : 0));
            pw.Set(StatusKind::kCleanseCooldown, 1.0f, CooldownOf(t, n4::kCleanseCooldown));
        }
        break;
    case kAstral:
        if (me.Has(StatusKind::kCosmos)) {
            // 闇星：每一次武器命中消耗 1 層闇宙，對該目標打出一次滿層引爆；用完回到一般形態（餘輝：得 3 層共鳴層）。
            StatusOp strike = Amount(Op::kDamage, res::DarkStrike(hit.power, target, me, in, nodes), kAstral);
            strike.arg[0] = tag::kDarkStrike;   // round 24: 星蝕 echoes it in the body pass
            plan.Push(strike);
            const int left = me.Layers(StatusKind::kCosmos) - 1;
            if (left > 0) {
                pw.Set(StatusKind::kCosmos, static_cast<float>(left), Scaled(t, n4::kCosmos));
            } else {
                pw.Clear(StatusKind::kCosmos);
                if (nodes.Has(node::kAstralAfterglow)) {
                    pw.Set(StatusKind::kResonance, static_cast<float>(n4::kAfterglow), Scaled(t, n4::kResonance));
                }
            }
        } else if (opened) {
            res::OpenGains(plan, kAstral, hit.power, hit.crit, target, me, in, nodes, rng);
        }
        break;
    default:
        if (opened) {
            res::OpenGains(plan, hit.element, hit.power, hit.crit, target, me, in, nodes, rng);
        }
        break;
    }
    if (opened && (hit.element == kFrost || hit.element == kBlood)) {
        res::OpenGains(plan, hit.element, hit.power, hit.crit, target, me, in, nodes, rng);
    }
    if (repeat) {
        res::Blades(plan, blades, 1.0f);
        return out;
    }
    // ---- every element hit
    if (me.Has(StatusKind::kWindFollow)) {
        ++blades;   // 順勢：風終焉後 5 秒內接管元素的命中皆附帶一段風刃
    }
    res::Blades(plan, blades, 1.0f);
    if (me.Has(StatusKind::kThunder)) {
        const int charges = me.Layers(StatusKind::kThunder);   // 雷霆：融斷當下的電荷，每次命中放電 ×0.3
        plan.Push(res::Discharge(charges, n4::kThunderMult, 1.0f, res::CritFor(charges, me, rng.Real(0.0f, 1.0f), false)));
    }
    if (t.syncStage >= 3 && nodes.Has(node::kCommonExtreme)) {
        const int count = me.Layers(StatusKind::kExtreme) + 1;   // 極致：同調三段每 10 次命中額外一次全額附傷
        if (count >= n4::kExtremeHits) {
            out.extraProc = true;
            pw.Clear(StatusKind::kExtreme);
        } else {
            pw.Set(StatusKind::kExtreme, static_cast<float>(count), n4::kForever);
        }
    }
    const int avatar = nodes.Rank(node::kCommonAvatar);
    if (t.syncStage >= 3 && avatar > 0 && !me.Has(StatusKind::kAvatarCooldown) && !me.Has(StatusKind::kAvatar)) {
        // 化身：同調三段時冷卻完成後的下一次命中——10 秒內當前元素的持續傳奇主線視同點滿（決策 7）。
        pw.Set(StatusKind::kAvatar, static_cast<float>(hit.formElement), Scaled(t, n4::kAvatar));
        pw.Set(StatusKind::kAvatarCooldown, 1.0f,
            CooldownOf(t, std::max(1.0f, n4::kAvatarCooldown - n4::kAvatarPerPoint * static_cast<float>(avatar))));
    }
    if (hit.sneak) {
        tw.Set(StatusKind::kLastHitSneak, static_cast<float>(hit.formElement), 1.0f);   // 連殺：死亡時讀這個標記
    }
    out.repeats = MultiTriggerRepeats(st, nodes);
    return out;
}

// A forced open (Papyrus 臨, 雙斷): the open gains only (no hit, so no crit, no power, no sync +1).
template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanSelfOpen(StatusPlan& plan, int element, Board& target, Board& me, const StatusInputs& in, const Nodes& nodes, Rng& rng)
{
    res::Blades(plan, res::OpenGains(plan, element, false, false, target, me, in, nodes, rng), 1.0f);
}

// A no-form hit (5.1): 戰意 (a no-form hit refreshes its 10 s; 滅法 silencing +1; 破式 uses all), the 超載 pool the plan
// left, 斷咒 (a casting target is interrupted, every 5 s, +1 戰意), 雷霆, the last-hit-sneak marker.
template <NodeReader Nodes>
constexpr void PlanSelfNoForm(StatusPlan& plan, const Plan& hitPlan, const SelfHit& hit, Board& target, Board& me,
    const StatusInputs& in, const Nodes& nodes, float roll)
{
    const Tuning& t = *in.tuning;
    const Writer pw{ plan, me, Who::kPlayer };
    int resolve = me.Layers(StatusKind::kResolve);
    if (hitPlan.breakUsed) {
        resolve = 0;
    }
    if (hitPlan.silenced) {
        ++resolve;   // 滅法讓目標沉默 +1
    }
    if (hit.targetCasting && nodes.Has(node::kNoFormInterrupt) && !me.Has(StatusKind::kInterruptCooldown)) {
        plan.Push(MakeOp(Op::kInterrupt));   // 斷咒
        pw.Set(StatusKind::kInterruptCooldown, 1.0f, CooldownOf(t, n4::kInterruptCooldown));
        ++resolve;
    }
    res::SetCount(plan, me, StatusKind::kResolve, std::min(n4::kResolveCap, resolve), Scaled(t, n4::kResolve));
    if (hitPlan.overloadAfter >= 0.0f) {
        const float before = me.Has(StatusKind::kOverload) ? me[StatusKind::kOverload].magnitude : 0.0f;
        res::SetOverload(plan, me, hitPlan.overloadAfter, hitPlan.overloadAfter > before, in, nodes);
    }
    if (me.Has(StatusKind::kThunder)) {
        const int charges = me.Layers(StatusKind::kThunder);
        plan.Push(res::Discharge(charges, n4::kThunderMult, 1.0f, res::CritFor(charges, me, roll, false)));
    }
    if (hit.sneak) {
        Writer{ plan, target, Who::kTarget }.Set(StatusKind::kLastHitSneak, 12.0f, 1.0f);   // 12 = no form
    }
}

// Leaving a form (switch or Z). v0.4 2.3: what sits on you clears, except where a node says otherwise.
template <NodeReader Nodes>
constexpr void PlanSelfLeave(StatusPlan& plan, int element, bool burst, Board& me, const StatusInputs& in, const Nodes& nodes)
{
    const Writer pw{ plan, me, Who::kPlayer };
    const int charges = me.Layers(StatusKind::kCharge);
    if (element == kLightning && !burst && charges > 0) {
        pw.Set(StatusKind::kSwitchCharge, static_cast<float>(charges), 60.0f);   // the cut end discharges these
    }
    if (!nodes.Has(node::kLightningOverloadEnd)) {
        res::SetCharges(plan, me, 0, in, nodes);   // 過載終焉：電荷跨形態攜帶（10 秒未命中仍歸零）
    }
    res::SetRock(plan, me, 0, in, nodes);
    res::SetWind(plan, me, 0, in, nodes);
    res::SetIceShield(plan, me, 0, in, nodes);
    pw.Clear(StatusKind::kStoredForce);
    pw.Clear(StatusKind::kChargedQuake);
    pw.Clear(StatusKind::kExtreme);
    pw.Clear(StatusKind::kFormHeld);
    pw.Clear(StatusKind::kSurgeUp);
    if (element == kAstral) {
        const int cosmos = me.Layers(StatusKind::kCosmos);
        if (!burst && cosmos > 0 && nodes.Has(node::kAstralFalling)) {
            pw.Set(StatusKind::kFallingStar, static_cast<float>(cosmos), 30.0f);   // 墜星：留到被切那一擊
        }
        pw.Clear(StatusKind::kCosmos);
        if (nodes.Has(node::kAstralRemnant) && me.Has(StatusKind::kResonance)) {
            pw.Set(StatusKind::kResonance, me[StatusKind::kResonance].magnitude, Scaled(*in.tuning, n4::kStarRemnant));   // 星殘
        } else {
            pw.Clear(StatusKind::kResonance);
        }
    } else {
        pw.Clear(StatusKind::kCosmos);
    }
    if (!burst) {
        pw.Set(StatusKind::kConcert, 1.0f, 3600.0f);   // 協奏／大協奏：切換後首次終焉
    }
    if (me.guardPool.has) {
        plan.Push(Amount(Op::kBloodGuardPool, 0.0f));   // 護血：離開形態清空
        me.guardPool = Slot{};
    }
}

// Opening a form: the 專一 clock starts; 雷臨強化 +5 charges; 地臨強化 岩甲 full (its stamina ring is the Papyrus scan).
template <NodeReader Nodes>
constexpr void PlanSelfEnter(StatusPlan& plan, int element, Board& me, const StatusInputs& in, const Nodes& nodes)
{
    Writer{ plan, me, Who::kPlayer }.Set(StatusKind::kFormHeld, static_cast<float>(element), n4::kForever);
    if (element == kLightning && nodes.Has(node::kLightningAdvent)) {
        res::SetCharges(plan, me, me.Layers(StatusKind::kCharge) + n4::kAdventCharges, in, nodes);
    }
    if (element == kEarth && nodes.Has(node::kEarthAdvent)) {
        res::SetRock(plan, me, res::RockCap(nodes), in, nodes);
    }
}

// Once a second: 超載 decays by 5% of max magicka (不竭 -0.2%／點, floor 2%) once its wait (3 s, 蓄流 6 s) ran out.
template <NodeReader Nodes>
constexpr void PlanSelfSecond(StatusPlan& plan, Board& me, float magickaMax, const StatusInputs& in, const Nodes& nodes)
{
    if (!me.Has(StatusKind::kOverload) || me.Has(StatusKind::kOverloadWait)) {
        return;
    }
    const float rate = std::max(n4::kEndlessFloor, n4::kOverloadDecay - n4::kEndlessPerPoint * static_cast<float>(nodes.Rank(node::kNoFormEndless)));
    res::SetOverload(plan, me, me[StatusKind::kOverload].magnitude - rate * magickaMax, false, in, nodes);
}

// A detonation's resonance targets (the engine counted the resonant hostiles within 15 m, the detonator included).
template <NodeReader Nodes>
constexpr void OnResonance(StatusPlan& plan, Board& me, int count, const StatusInputs& in, const Nodes& nodes)
{
    res::AddResonance(plan, me, std::clamp(count, 1, n4::kResonanceCount), in, nodes);
}

}  // namespace essb
