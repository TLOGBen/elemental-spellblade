#pragma once
// Round 23 (slice N4): a hit whose target is you (v0.4 "受擊" rows). Pure: PlanHurt reads what the hurt sink recorded
// before the damage (the facts, your health and magicka then) and what the follow-up task read after it (your health
// now), plus your board and the attacker's, and pushes StatusOps (Status.h) on you (Who::kPlayer) and the attacker
// (Who::kTarget).
//
// The pools (v0.4 5.1 法盾、5.8 護血、5.11 水幕): a PERK entry cut this hit by the share s BEFORE the engine took health
// (build_v03 base_rule_entries), so the damage that reached your health is h = before − after and what the pool
// blocked is h × s ÷ (1 − s) (native-verification-2 s15: the event comes before the damage, so the sink records
// `before` and a task reads `after`). v0.4 accepts this as an estimate.
//
// Order in one hit: 殘影's absorbed hit; the pools; 化法為力; the branches on the attacker (反震 / 岩甲 −1, 灼身, 寒反,
// 靜電, 毒皮, 怨縛, 咒返); your own (反擊, 破護, 不屈, 逆電, 浴火, 懲戒, 蓄勁 / 蓄能, 殘影's roll); the post-hit thresholds
// (自動洩壓, 越線, 冰心, 庇護); ESSB_Lethal when you are at or below 0.
#include "SelfLayer.h"

namespace essb {

struct HurtFacts {
    bool attacker = false;       // an actor other than you caused it
    bool melee = false;          // not a spell and no projectile (the rule ESSBGuard.OnHitEx used)
    bool spell = false;          // the source is a spell, scroll or staff enchantment (化法為力, 咒返)
    bool destructive = false;    // that spell carries MagicDamageFire / Frost / Shock (the PERK's spell half cut it)
    bool blocked = false;        // kHitBlocked
    bool cloakTick = false;      // a spell hit, no projectile, the attacker carries a MagicCloak effect (破護)
    bool afterimage = false;     // your 殘影 window was up when this hit arrived (the PERK made it 0)
    bool linger = false;         // your 餘魔 window was up when this hit arrived
    float healthBefore = 0.0f;   // the sink (before the damage)
    float magickaBefore = 0.0f;
    float overloadBefore = 0.0f;
    float guardBefore = 0.0f;    // your 護血 pool at the sink (the PERK cut this hit while it was up)
    float guardLeft = -1.0f;     // the pool a same-frame earlier hit left (the task's current read); < 0: guardBefore
    float healthAfter = 0.0f;    // the task (after the damage)
    float dotDamage = 0.0f;      // the task: Σ magnitude × remaining seconds of this spell's damage-over-time effects on
                                 // you (after the PERK cut; round 23 review: DoTs are not shared)
    std::uint32_t sourceSpell = 0;   // engine plumbing: the spell that hit (the task finds its DoTs by it)
    float magicka = 0.0f;        // the task
    float magickaMax = 0.0f;
    float stamina = 0.0f;
};

namespace hurt {

// The share a pool's PERK entry took off this hit (0 = none), and what each blocked point costs.
struct Share {
    float share = 0.0f;
    float cost = 0.0f;
    bool shield = false;    // 法盾 (the overload is spent first)
    bool veil = false;      // 水幕
    bool guard = false;     // 護血
    bool linger = false;    // 餘魔's stamina window
};

template <NodeReader Nodes>
constexpr Share ShareOf(const HurtFacts& f, const Board& me, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    Share s;
    const bool shared = !f.spell || f.destructive;   // the physical entry always applies; the spell half is keyword-bound
    if (!shared) {
        return s;
    }
    if (in.formElement == 0) {
        if (f.magickaBefore > 0.0f || f.overloadBefore > 0.0f) {
            const bool over = f.overloadBefore > 0.0f;
            s.share = (over ? n4::kShieldShareOverload : n4::kShieldShare) +
                      n4::kShieldSharePerPoint * static_cast<float>(nodes.Rank(node::kNoFormShieldShare));
            s.cost = (over ? n4::kShieldCostOverload : n4::kShieldCost) *
                     (1.0f - n4::kShieldCostPerPoint * static_cast<float>(nodes.Rank(node::kNoFormShieldCost)));
            s.shield = true;
        } else if (f.linger) {
            s.share = n4::kLingerShare;
            s.cost = n4::kShieldCost * (1.0f - n4::kShieldCostPerPoint * static_cast<float>(nodes.Rank(node::kNoFormShieldCost)));
            s.linger = true;
        }
    } else if (in.formElement == kWater && f.magickaBefore > 0.0f) {
        const bool shieldVeil = nodes.Has(node::kWaterShield);
        s.share = shieldVeil ? n4::kShieldVeil : n4::kVeilShare;
        if (t.syncStage >= 3 && nodes.Has(node::kWaterStill)) {
            s.share += n4::kStillWater;   // 止水：同調三段時分擔比例再 +15%
        }
        s.cost = shieldVeil ? n4::kShieldVeilCost : n4::kVeilCost;
        s.veil = true;
    } else if (in.formElement == kBlood && f.guardBefore > 0.0f) {
        s.share = n4::kGuardShare;
        s.cost = 1.0f;
        s.guard = true;
    }
    (void)me;
    return s;
}

}  // namespace hurt

template <NodeReader Nodes, RandomSource Rng>
constexpr void PlanHurt(StatusPlan& plan, const HurtFacts& f, Board& attacker, Board& me, const StatusInputs& in, const Nodes& nodes,
    Rng& rng)
{
    const Tuning& t = *in.tuning;
    const Config& c = *in.config;
    const Writer pw{ plan, me, Who::kPlayer };
    const Writer aw{ plan, attacker, Who::kTarget };
    const int form = in.formElement;
    const float lost = std::max(0.0f, f.healthBefore - f.healthAfter);

    // ---- 殘影's window took this hit (the PERK made it 0): it closes now (v0.4 5.7「讓下一次攻擊無效」).
    if (f.afterimage) {
        pw.Clear(StatusKind::kAfterimage);
    }

    // ---- the pools
    const hurt::Share share = hurt::ShareOf(f, me, in, nodes);
    float blocked = 0.0f;
    if (share.share > 0.0f && share.share < 1.0f && lost > 0.0f) {
        blocked = lost * share.share / (1.0f - share.share);
    }
    float magicka = std::max(0.0f, f.magicka);
    float pool = me.Has(StatusKind::kOverload) ? me[StatusKind::kOverload].magnitude : 0.0f;
    // Round 23 review (commander rulings): what a pool could not pay is real damage to you, with no keep-1 clamp -- it
    // can kill, and ESSB_Lethal then fires as for any lethal hit.
    float extra = 0.0f;
    auto hurtYou = [&](float amount) {
        if (amount > 0.0f) {
            plan.Push(Amount(Op::kHurtHealth, amount));
            extra += amount;
        }
    };
    // DoTs are not shared: the PERK conditions cannot see an effect's duration (no such condition function), so the part
    // its spell half cut from this spell's damage-over-time effects is dealt back at once, and nothing is charged for it.
    if (share.share > 0.0f && share.share < 1.0f && f.dotDamage > 0.0f) {
        hurtYou(f.dotDamage * share.share / (1.0f - share.share));
    }
    if (blocked > 0.0f) {
        float owed = blocked * share.cost;
        if (share.shield) {
            const float fromPool = std::min(pool, owed);   // 法盾：先花超載
            if (fromPool > 0.0f) {
                pool -= fromPool;
                owed -= fromPool;
                res::SetOverload(plan, me, pool, false, in, nodes);
            }
        }
        if (share.shield || share.veil) {
            const float paid = std::min(owed, magicka);
            if (paid > 0.0f) {
                plan.Push(Amount(Op::kSpendMagicka, paid));
            }
            if (owed > paid && share.cost > 0.0f) {
                hurtYou((owed - paid) / share.cost);   // the magicka ran out: the rest of what the shield took is damage
            }
            const bool emptied = magicka > 0.0f && paid >= magicka;
            magicka -= paid;
            if (emptied && share.shield && pool <= 0.0f && nodes.Has(node::kNoFormLinger) && !me.Has(StatusKind::kLingerCooldown)) {
                // 餘魔：法盾把魔力扣到 0 的那一刻不中斷，再以 30% 分擔 2 秒（改扣耐力），每 30 秒一次。
                pw.Set(StatusKind::kLingerShield, 1.0f, n4::kLinger);
                pw.Set(StatusKind::kLingerCooldown, 1.0f, CooldownOf(t, n4::kLingerCooldown));
            }
            if (emptied && share.veil && nodes.Has(node::kWaterTideBody) && !me.Has(StatusKind::kTideBodyCooldown)) {
                // 潮身：水幕把魔力扣到 0 的那一刻，立即洗淨一次（不佔洗淨冷卻）並回復最大魔力 20%，每 30 秒一次。
                plan.Push(MakeEvent(Event::kCleanse, nodes.Has(node::kWaterPurify) ? 1 : 0));
                const float back = f.magickaMax * n4::kTideBody * t.multRecovery;
                plan.Push(Amount(Op::kRestoreMagicka, back));
                magicka += back;
                pw.Set(StatusKind::kTideBodyCooldown, 1.0f, CooldownOf(t, n4::kTideBodyCooldown));
            }
        } else if (share.linger) {
            plan.Push(Amount(Op::kPayStamina, std::min(owed, std::max(0.0f, f.stamina))));
        } else if (share.guard) {
            // 護血：受到傷害時優先扣，歸零後才傷及生命（the part the pool could not hold is real damage now, it can kill）.
            // Two hits in one frame both met the pool at the sink; the second pays from what the first left
            // (round 22 carry-over: the same-frame double hit).
            const float guard = f.guardLeft >= 0.0f ? f.guardLeft : f.guardBefore;
            const float left = guard - blocked;
            plan.Push(Amount(Op::kBloodGuardPool, std::max(0.0f, left)));
            if (left < 0.0f) {
                hurtYou(-left);
            }
        }
    }

    // ---- 化法為力 (5.1): a spell's damage (what reached you plus what the shield took) gives back 30% as magicka (化勁
    // 60%, 逼近's 2 s ×2); what does not fit goes into the overload pool.
    if (form == 0 && f.spell && lost + blocked > 0.0f) {
        float ratio = nodes.Has(node::kNoFormTransmute) ? n4::kTransmuteStrong : n4::kTransmute;
        if (me.Has(StatusKind::kCloseIn)) {
            ratio *= 2.0f;
        }
        const float back = (lost + blocked) * ratio * t.multRecovery;
        const float fits = std::min(back, std::max(0.0f, f.magickaMax - magicka));
        if (fits > 0.0f) {
            plan.Push(Amount(Op::kRestoreMagicka, fits));
        }
        const float cap = res::OverloadCap(f.magickaMax, nodes);
        if (back > fits && pool < cap) {
            res::SetOverload(plan, me, std::min(cap, pool + back - fits), true, in, nodes);
        }
    }

    // ---- on the attacker
    const bool retort = f.attacker && !attacker.Has(StatusKind::kRetortCooldown);
    bool retorted = false;
    if (form == kEarth && me.Has(StatusKind::kRockArmor)) {
        const int rock = me.Layers(StatusKind::kRockArmor);
        if (f.attacker && f.melee && rock >= res::RockCap(nodes) && nodes.Has(node::kEarthRetaliate) &&
            !me.Has(StatusKind::kRetaliateCooldown)) {
            // 反震：岩甲滿層被近戰命中，反震一次土傷並使攻擊者跌倒，每 10 秒一次，清空岩甲。
            plan.Push(Amount(Op::kDamage, c.damage[kEarth][1] * n4::kRetaliate * ReactionScale(kEarth, t, in.player, nodes) *
                                              ReactionVulnerability(attacker, me, t, nodes), kEarth));
            plan.Push(MakeEvent(Event::kKnock, n4::kKnockForce));
            pw.Set(StatusKind::kRetaliateCooldown, 1.0f, CooldownOf(t, n4::kRetaliateCooldown));
            res::SetRock(plan, me, 0, in, nodes);
        } else if (!(nodes.Has(node::kEarthMountain) && t.syncStage >= 3)) {
            res::SetRock(plan, me, rock - 1, in, nodes);   // 岩甲被打 −1（山岳：同調三段時免除）
        }
    }
    if (retort && f.melee && form == kFire && nodes.Has(node::kFireScorch)) {
        // 灼身：被近戰命中時攻擊者掛你的火印記（不開印、不切別的印記）並受一次 B_max ×1.0 火傷。
        const int others = attacker.MarkCount() - (attacker.mark[kFire].has ? 1 : 0);
        if (others == 0 || (others < 2 && nodes.Has(node::kCommonDualMark))) {
            aw.Mark(kFire, rule::MarkSeconds(kFire, t, nodes, false));
        }
        plan.Push(Amount(Op::kDamage, c.damage[kFire][1] * n4::kScorch * ReactionScale(kFire, t, in.player, nodes) *
                                          ReactionVulnerability(attacker, me, t, nodes), kFire));
        retorted = true;
    }
    if (retort && form == kFrost && nodes.Has(node::kFrostColdRetort)) {
        // 寒反：攻擊你的敵人被減速 30% 3 秒，且凍結 +1（v0.4 沒限近戰）。
        plan.Push(Amount(Op::kSlow, n4::kColdRetortSlow, 0, Scaled(t, n4::kColdRetort)));
        rule::AddFreeze(plan, attacker, 1.0f, false, in, nodes, rng);
        retorted = true;
    }
    if (retort && f.melee && form == kLightning && nodes.Has(node::kLightningStatic)) {
        const int others = attacker.MarkCount() - (attacker.mark[kLightning].has ? 1 : 0);
        if (others == 0 || (others < 2 && nodes.Has(node::kCommonDualMark))) {
            aw.Mark(kLightning, rule::MarkSeconds(kLightning, t, nodes, false));   // 靜電：攻擊者感電
        }
        retorted = true;
    }
    if (retort && f.melee && form == kPoison && nodes.Has(node::kPoisonSkin)) {
        rule::AddDoses(plan, attacker, n4::kPoisonSkin, in, nodes);   // 毒皮：攻擊者中毒 +2 劑
        retorted = true;
    }
    if (retorted) {
        aw.Set(StatusKind::kRetortCooldown, 1.0f, CooldownOf(t, n4::kRetortCooldown));
    }
    if (f.attacker && form == kDarkness && nodes.Has(node::kDarkGrudge) && attacker.Has(StatusKind::kCurse) &&
        !attacker.Has(StatusKind::kGrudgeCooldown)) {
        rule::AddCurse(plan, attacker, 1, in, nodes);   // 怨縛：詛咒目標打你時它的詛咒 +1，每目標 2 秒一次
        aw.Set(StatusKind::kGrudgeCooldown, 1.0f, CooldownOf(t, n4::kGrudgeCooldown));
    }
    if (f.attacker && f.spell && form == 0 && nodes.Has(node::kNoFormSpellReturn) && !me.Has(StatusKind::kSpellReturnCooldown)) {
        plan.Push(MakeOp(Op::kDispelMarkOn));   // 咒返：對施法者施加滅法印，每 5 秒一次
        pw.Set(StatusKind::kSpellReturnCooldown, 1.0f, CooldownOf(t, n4::kSpellReturnCooldown));
    }

    // ---- on you
    if (f.blocked && form == 0 && nodes.Has(node::kNoFormRiposte)) {
        plan.Push(MakeOp(Op::kRiposte, Who::kPlayer));   // 反擊：格擋成功後 3 秒內下一次命中吸魔 ×2
    }
    if (f.cloakTick && form == 0 && nodes.Has(node::kNoFormCloakBreak)) {
        pw.Set(StatusKind::kCloakGuard, 1.0f, 2.0f);   // 破護：不受元素披風反傷（第一跳仍會吃到），逐跳刷新
    }
    if (form == 0 && nodes.Has(node::kNoFormUnyield) && !me.Has(StatusKind::kUnyieldCooldown)) {
        res::AddResolve(plan, me, 1, in, nodes);   // 不屈：被命中時戰意 +1（每 3 秒一次），重設歸零計時
        pw.Set(StatusKind::kUnyieldCooldown, 1.0f, CooldownOf(t, n4::kUnyieldCooldown));
    }
    if (form == kLightning && nodes.Has(node::kLightningReverse) && !me.Has(StatusKind::kReverseCooldown)) {
        res::SetCharges(plan, me, me.Layers(StatusKind::kCharge) + 1, in, nodes);   // 逆電：被命中時電荷 +1（每 2 秒一次）
        pw.Set(StatusKind::kReverseCooldown, 1.0f, CooldownOf(t, 2.0f));
    }
    if (f.attacker && form == kFire && t.syncStage >= 3 && nodes.Has(node::kFireBathe) && attacker.mark[kFire].has) {
        rule::RaiseHeat(plan, me, 1, in, nodes);   // 浴火：同調三段時被帶火印記的目標命中，熱度推進一次（照成熟時間）
    }
    if (HolyTier(me) >= 2 && !me.Has(StatusKind::kPunishCooldown)) {
        // 懲戒：聖佑 II 以上每被命中 +1（每 0.5 秒最多一層；誓約的目標打你 +2），上限 5（天誅 8），8 秒，被打刷新。
        const int gain = f.attacker && attacker.Has(StatusKind::kOath) ? n4::kOathPunish : n4::kPunishHit;
        const int layers = std::min(res::PunishCap(nodes), me.Layers(StatusKind::kPunish) + gain);
        pw.Set(StatusKind::kPunish, static_cast<float>(layers), Scaled(t, n3::kPunish));
        pw.Set(StatusKind::kPunishCooldown, 1.0f, n4::kPunishInterval);
    }
    if (f.blocked && form == kEarth) {
        // 蓄勁：格擋來襲攻擊 +2（上限 10）；蓄能：格擋把現有的蓄勁全部換成每點物理減傷 +1%，3 秒（v0.4「消耗全部」）。
        int force = me.Layers(StatusKind::kStoredForce);
        if (force >= 1 && nodes.Has(node::kEarthCharge)) {   // 蓄能：蓄勁 ≥1 就全部換（審查修正）
            pw.Set(StatusKind::kBracing, static_cast<float>(force), n4::kBracing);
            force = 0;
        }
        res::SetCount(plan, me, StatusKind::kStoredForce, std::min(n4::kForceCap, force + n4::kForceBlock), n4::kForever);
    }
    if (f.melee && !f.afterimage && form == kWind && nodes.Has(node::kWindAfterimage) &&
        me.Layers(StatusKind::kWindGauge) >= res::WindThreshold(nodes) && rng.Chance(n4::kAfterimage)) {
        // 殘影：風勢滿時被近戰命中，30% 機率讓下一次攻擊無效（消耗風勢）。
        res::SetWind(plan, me, 0, in, nodes);
        pw.Set(StatusKind::kAfterimage, 1.0f, n4::kAfterimageSeconds);
    }

    // ---- thresholds on your health after the hit
    Self after = in.self;
    after.health = std::max(0.0f, after.health - extra);   // the thresholds see the damage the pools could not take
    const float fraction = after.Fraction();
    if (HeatTier(me) >= 3 && fraction < n3::kAutoVent) {
        OnFormLeave(plan, kFire, false, me, in, nodes);   // 自動洩壓：生命 <10%（受擊的當下，洩壓永遠先於過熱判定）
    }
    if (form == kBlood) {
        // 越線（5.8）：受擊也比對血區（往下＝濺血；往上＝回湧）。
        const int zone = BloodZone(after);
        const int marked = me.Layers(StatusKind::kBloodZone);
        if (marked != zone) {
            pw.Set(StatusKind::kBloodZone, static_cast<float>(zone), 86400.0f);
            if (marked != 0 && !me.Has(StatusKind::kCrossCooldown)) {
                pw.Set(StatusKind::kCrossCooldown, 1.0f, CooldownOf(t, n3::kCross));
                if (zone > marked) {
                    plan.Push(MakeEvent(Event::kSplash, 0.0f));
                } else {
                    plan.Push(MakeEvent(Event::kRise));
                    pw.Set(StatusKind::kSurgeUp, 1.0f, Scaled(t, n4::kSurgeUp));
                }
            }
        }
    }
    if (form == kFrost && fraction < n4::kIceHeartHealth && nodes.Has(node::kFrostIceHeart) && !me.Has(StatusKind::kIceHeartCooldown)) {
        plan.Push(MakeOp(Op::kFreezeNearby));   // 冰心：生命低於 30% 時冰封附近所有凍結量表 ≥1 的敵人，每 30 秒一次
        pw.Set(StatusKind::kIceHeartCooldown, 1.0f, CooldownOf(t, n4::kIceHeartCooldown));
    }
    if (form == kDivine && fraction < n4::kSanctuaryHealth && nodes.Has(node::kDivineSanctuary) && !me.Has(StatusKind::kSanctuaryCooldown)) {
        rule::SetHoly(plan, me, 3, in, nodes);   // 庇護：生命低於 30% 時聖佑直接 III 並刷新，每 30 秒一次
        pw.Set(StatusKind::kSanctuaryCooldown, 1.0f, CooldownOf(t, n4::kSanctuaryCooldown));
    }
    if (f.healthAfter - extra <= 0.0f) {
        StatusOp lethal = MakeEvent(Event::kLethal);
        lethal.who = Who::kPlayer;
        plan.Push(lethal);   // 神佑的延遲死亡（Papyrus）
    }
}

// 逼近 (5.1): an enemy within 15 m cast a spell -- 2 s of +30% speed and double 化法為力, every 6 s. 反咒 (5.1): a caster
// carrying your 滅法印 takes true damage = that cast's magicka cost × (100% + 2% per no-form level), and 戰意 +1.
struct CastFacts {
    bool hostileNear = false;    // the caster is hostile and within 15 m
    bool marked = false;         // the caster carries your 滅法印 (ESSB_ManaBreakEffect)
    float cost = 0.0f;           // MagicItem::CalculateMagickaCost(caster) (× the dual-cast multiplier)
    float trueMult = 1.0f;       // HitMath TrueDamageMultiplier on the caster (靜寂, 目標魔力低於 25%)
};

template <NodeReader Nodes>
constexpr void PlanSpellCast(StatusPlan& plan, const CastFacts& f, Board& me, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    const Writer pw{ plan, me, Who::kPlayer };
    if (in.formElement != 0) {
        return;   // 大師與滅法路線只在未開形態時生效
    }
    if (f.hostileNear && nodes.Has(node::kNoFormCloseIn) && !me.Has(StatusKind::kCloseInCooldown)) {
        pw.Set(StatusKind::kCloseIn, 1.0f, Scaled(t, n4::kCloseIn));
        pw.Set(StatusKind::kCloseInSpeed, n4::kCloseInSpeed, n4::kCloseIn);
        pw.Set(StatusKind::kCloseInCooldown, 1.0f, CooldownOf(t, n4::kCloseInCooldown));
    }
    if (f.marked && f.cost > 0.0f && nodes.Has(node::kNoFormCounter)) {
        const float ratio = 1.0f + n4::kCounterPerLevel * std::max(1.0f, t.level[kNoFormTree]);
        // 真實傷害（v0.4 5.1 自帶等級縮放「100 級為 300%」，所以不再乘 G(L)；決策 8）；噬命：真傷的 50% 轉為生命。
        const float damage = f.cost * ratio * f.trueMult * t.baseDamageMult;
        plan.Push(Amount(Op::kDamage, damage, 0));
        if (nodes.Has(node::kNoFormDevour)) {
            plan.Push(Amount(Op::kHeal, damage * 0.5f * t.multRecovery));
        }
        res::AddResolve(plan, me, 1, in, nodes);
    }
}

}  // namespace essb
