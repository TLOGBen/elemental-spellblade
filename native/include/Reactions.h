#pragma once
// Round 24 (slice N5): the reaction bodies, the fusion (融斷), the death handling and every range scan they need, in the
// DLL (ruling R4: the damage and status parts of ESSBReactions / ESSBElem* / ESSBNodes / ESSBNoForm move here; pushes,
// fear / frenzy AI, reanimation AI, the ash's disintegration, keep-sneak, domains (N6) and 神佑 stay Papyrus through
// ModEvents). Pure like Status.h: no engine, no allocation, no global state. The engine reads ONE crowd per event --
// the event's own actor (member 0) and the eligible hostiles around it and around you, collected first, then read
// (native-verification-3 s11; ruling R3/R6) -- and every body here plans on those boards; ops carry `at` (the member)
// and the executor selects that actor before casting.
//
//   RunBodies     the body pass: walks a plan the state planners (Status.h, SelfLayer.h, Hurt.h) produced and turns
//                 every body event (open, end, frozen, hallucination groups, 聖裁, 濺血, 越線, 碎冰, 落地, 放電, 風刃,
//                 過熱) and every crowd op (共鳴層 count, 碎岩's ring, 冰心) into casts on the crowd; new events a body
//                 pushes (chain ends, forced opens) are walked too, in order, at most kMaxBodies of them
//   PlanBurst     融斷 (2.5, 5.1 冷寂, 5.2): every mark within 15 m (收束 20 m, +0.3 m a point) ends with reason burst ×
//                 K_sync × the burst main lines; 寂, 萬寂, 斷界, 回流, 雙斷, 安全閥, 地斷, 颶風, 墜星's burst half
//   PlanDeath     the death sink (2.6, 5.x): 化灰 (聖灰, 淨灰, 淨土), 亡者歸來 (殘魂, 冥召, 死靈主, 狂宴), the poison's death
//                 spread (蔓延), 連鎖冰封, 火葬, 亡魂, 亡衛, 飲血, 血承, 不死, 無魔, 連殺
//   PlanAdvent    opening a form: X臨 (every hostile within 2 m + 0.2 m a point opens), the 臨強化 branches, 臨界, 雙斷
//   PlanEcho      a star hit's echo (回聲, 星鏈) on the other resonance targets
// Every number is v0.4's (the comment names the section); a reading the text leaves open is a ledger decision
// (.codex/impl-fix-round24.html).
#include "SelfLayer.h"

#include <array>
#include <cstdint>

namespace essb {

namespace n5 {
inline constexpr float kMetre = 70.0f;               // 2.9: 1 m = 70 units
inline constexpr float kNear = 1050.0f;              // 2.9 "附近": 15 m, 5 targets, nearest first
inline constexpr int kNearLimit = 5;
inline constexpr float kArea = 210.0f;               // 2.9 範圍終焉 (碎冰、地震、裁決、焚天…): 3 m
inline constexpr float kWideQuake = 350.0f;          // 廣震 5 m
inline constexpr float kVortex = 350.0f;             // 風渦 5 m
inline constexpr float kSixMetres = 420.0f;          // 濃毒、疫染 6 m
inline constexpr float kTransfer = 210.0f;           // 淬毒：3 公尺內一名敵人傳 1 劑
inline constexpr float kDrag = 105.0f;               // 牽引：目標身後 1.5 公尺內（最多 2 人）
inline constexpr int kDragLimit = 2;
inline constexpr float kLegion = 280.0f;             // 群魔 4 m
inline constexpr float kSmite = 280.0f;              // 破邪斬 4 m
inline constexpr float kBurst = 1050.0f;             // 融斷 15 m
inline constexpr float kGather = 1400.0f;            // 收束 20 m
inline constexpr float kBurstPerPoint = 21.0f;       // 融斷範圍 +0.3 m a point
inline constexpr float kAdventBase = 2.0f;           // 臨：2 m + 0.2 m a point
inline constexpr float kAdventPerPoint = 0.2f;
inline constexpr float kRangeBase = 1.0f;            // 血海 / 天啟：1 m + 0.2 m a point
inline constexpr int kCrowdMax = 24;                 // eligible actors a scan reads besides member 0 (nearest first)
inline constexpr int kMaxBodies = 160;               // body events one pass walks at most
inline constexpr int kUnlimited = kCrowdMax;         // "不限": every eligible one the scan read
// open bodies (2.6, 5.x)
inline constexpr float kFireOpen = 0.5f;             // 點燃：B_max ×0.5
inline constexpr float kEmberStamina = 15.0f;        // 餘熱
inline constexpr float kPreBurn = 0.5f;              // 先燃 ×0.5
inline constexpr float kFrostOpenSeconds = 3.0f;     // 霜結：減速 25%（ESSB_FrostOpenSlowPct）3 秒
inline constexpr float kShockOpenDrain = 1.0f;       // 感電：目標魔力 -B_max ×1.0
inline constexpr float kWeaken = 10.0f;              // 感電削弱：魔抗 -10%（印記的 8 秒）
inline constexpr float kWeakenSeconds = 8.0f;
inline constexpr float kFlash = 15.0f;               // 雷閃：移速 +15% 2 秒
inline constexpr float kFlashSeconds = 2.0f;
inline constexpr float kFissureArmor = 30.0f;        // 裂痕：護甲 -30（主線 +2／點）、耐力 -10，你回 10 耐力；8 秒
inline constexpr float kFissureArmorPerPoint = 2.0f;
inline constexpr float kFissureStamina = 10.0f;
inline constexpr float kFissureSeconds = 8.0f;
inline constexpr float kKnock = 3.0f;                // 跌倒推力（ESSBController.Knockdown）
inline constexpr float kBaseSeconds = 3.0f;          // 地基：耐力不回復 3 秒
inline constexpr float kStill = 100.0f;              // 耐力凝滯 100%
inline constexpr float kFirstQuake = 0.5f;           // 先震 ×0.5，不含跌倒
inline constexpr float kPull = 1.5f;                 // 風痕：拉近 1.5 m（開啟熟練主線 +0.1 m／點，最多 3 m）
inline constexpr float kPullPerPoint = 0.1f;
inline constexpr float kPullMax = 3.0f;
inline constexpr float kLeap = 10.0f;                // 輕躍：移速 +10% 3 秒
inline constexpr float kLeapSeconds = 3.0f;
inline constexpr float kGust = 10.0f;                // 氣流：回 10 耐力
inline constexpr float kOpenLeech = 50.0f;           // 血痕的「依血位吸血」與深血痕的吸血：50 × 吸血比例（v0.4 沒寫量，round 21 KEPT）
inline constexpr float kOpenHeal = 0.5f;             // 開印回血：B_max ×0.5，低血位（<30%）×2
inline constexpr float kBloodCurse = 50.0f;          // 血咒：生命回復 -50% 5 秒
inline constexpr float kBloodCurseSeconds = 5.0f;
inline constexpr float kSacrifice = 0.5f;            // 血祭之始 ×0.5 血潮
inline constexpr float kDivineOpenHeal = 0.5f;       // 聖印：你回血 B_max ×0.5（開啟新手主線 +5%／點）
inline constexpr float kDivineOpenPerPoint = 0.05f;
inline constexpr float kPoisonSplash = 2.0f;         // 毒濺：附近 1 人 2 劑
inline constexpr float kThick = 2.0f;                // 濃毒：複製 2 劑
inline constexpr float kFilm = 50.0f;                // 毒膜：毒抗 +50% 5 秒
inline constexpr float kFilmSeconds = 5.0f;
inline constexpr float kRot = 10.0f;                 // 腐蝕開印：毒抗 -10%（印記的 8 秒）
inline constexpr float kRotSeconds = 8.0f;
inline constexpr float kPoisonBlood = 0.5f;          // 毒血：你回血 B_max ×0.5
inline constexpr float kWaterOpenPerPoint = 0.003f;  // 開印時回復生命與耐力各最大值 0.3%／點
inline constexpr float kDarkOpenDrain = 1.0f;        // 詛咒開印：吸魔 B_max ×1.0
inline constexpr int kStainCurse = 2;                // 暗染：附近 1 人詛咒（開印的 2 層）
inline constexpr float kGuardMR = 10.0f;             // 護持：命中得 10% 魔抗 3 秒
inline constexpr float kGuardSeconds = 3.0f;
inline constexpr float kWither = 15.0f;              // 萎靡：中毒 ≥5 劑時攻擊 -15%（3 秒）
inline constexpr float kWitherSeconds = 3.0f;
inline constexpr float kErode = 20.0f;               // 侵蝕：滿劑時毒抗 -20%（6 秒）
inline constexpr float kErodeSeconds = 6.0f;
inline constexpr float kErosionPerLayer = 2.0f;      // 詛咒每層抗性侵蝕 -2%（主線 +0.2%／點），詛咒的 8 秒
inline constexpr float kErosionPerPoint = 0.2f;
inline constexpr float kErosionSeconds = 8.0f;
inline constexpr float kQuakeStrike = 1.5f;          // 震擊：1.5× 地震爆傷、削 50 耐力
inline constexpr float kQuakeStrikeStamina = 50.0f;
// end bodies
inline constexpr float kFrostEnd = 1.0f;             // 碎冰（未冰封）：B_max ×1.0
inline constexpr float kPerCharge = 0.3f;            // 放電：電荷 × 30% B_max（每格 +1%／點）
inline constexpr float kDischargeDrain = 0.5f;       // 削減目標魔力＝放電傷害的 50%
inline constexpr int kJump = 2;                      // 跳到附近 2 人各 40%（電弧 3 人 55%，連鎖 5 人）
inline constexpr float kJumpShare = 0.4f;
inline constexpr int kArcJump = 3;
inline constexpr float kArcShare = 0.55f;
inline constexpr int kChainJump = 5;
inline constexpr float kQuake = 1.5f;                // 地震 ×1.5（崩裂 ×2.0）
inline constexpr float kCollapse = 2.0f;
inline constexpr float kQuakeStamina = 2.0f;         // 削減耐力 B_max ×2（主線 +3%／點，不吃節點倍率）
inline constexpr float kQuakeStaminaPerPoint = 0.03f;
inline constexpr float kQuakeSlow = 30.0f;           // 其餘減速 30% 3 秒
inline constexpr float kQuakeSlowSeconds = 3.0f;
inline constexpr float kDust = 20.0f;                // 塵暴：攻擊 -20% 3 秒
inline constexpr float kDustSeconds = 3.0f;
inline constexpr float kBlade = 1.0f;                // 風刃 B_max ×1.0（風刃傷害 +2%／點）
inline constexpr float kBladePerPoint = 0.02f;
inline constexpr float kBladeUnbalanced = 1.3f;      // 失衡中受風刃傷害 +30%
inline constexpr int kBladeNear = 2;                 // 吹飛：附近 2 人（亂流 5 人）；迴旋 2 人
inline constexpr int kTurbulence = 5;
inline constexpr float kChaseStamina = 3.0f;         // 追風：回耐力 3
inline constexpr float kBlow = 3.0f;                 // 吹飛 3 m
inline constexpr float kLift = 1.0f;                 // 吹上天 / 空中追擊：推高 1 m
inline constexpr float kLanding = 0.5f;              // 落地 B_max ×0.5（主線 +5%／點；上天 ×1.0）
inline constexpr float kLandingPerPoint = 0.05f;
inline constexpr float kSkyLanding = 0.5f;
inline constexpr float kVortexPull = 2.0f;           // 風渦：拉向目標 2 m
inline constexpr float kSated = 1.5f;                // 飽飲：流血部分 ×1.5
inline constexpr float kPactCost = 0.10f;            // 血契：高血位（≥70%）損 10% 生命，血潮 ×2
inline constexpr float kPactMult = 2.0f;
inline constexpr float kSurgeHealth = 0.10f;         // 血潮：當前生命 10%（首領 3%；放血終焉 ×2）
inline constexpr float kSurgeHealthVip = 0.03f;
inline constexpr float kSurgeHeal = 2.0f;            // 治療你＝結算 × 吸血比例 × 2（主線 +0.1／點）
inline constexpr float kSurgeHealPerPoint = 0.1f;
inline constexpr float kBloodSever = 0.5f;           // 血斷：融斷治療 50%
inline constexpr float kJudge = 2.0f;                // 裁決 ×2.0（重裁 ×3.0），治療你 B_max ×1.0
inline constexpr float kHeavyJudge = 3.0f;
inline constexpr float kJudgeHeal = 1.0f;
inline constexpr float kRadiance = 0.2f;             // 光耀：亡靈魔族 5 秒內受聖傷 +20%
inline constexpr float kRadianceSeconds = 5.0f;
inline constexpr float kSmiteShare = 0.5f;           // 破邪斬：聖裁傷害的 50%
inline constexpr float kHolyBlast = 0.5f;            // 聖裁 III：3 公尺 B_max ×0.5 聖光爆
inline constexpr float kBreakArmor = 60.0f;          // 聖裁 II／III 破防：護甲 -60、魔抗 -10%，5 秒
inline constexpr float kBreakMR = 10.0f;
inline constexpr float kBreakSeconds = 5.0f;
inline constexpr float kShred = 0.1f;                // 碎甲：自有減防 10%（碎甲加深 20%），5 秒
inline constexpr float kDeepShred = 0.2f;
inline constexpr float kShredSeconds = 5.0f;
inline constexpr float kFrozenSlow = 50.0f;          // 冰封：減速 50%（絕對零度：同調三段再 -2%／點，上限 70%）
inline constexpr float kZeroPerPoint = 2.0f;
inline constexpr float kDeepChill = 20.0f;           // 深寒：冰封中攻擊 -20%、耐力不回復
inline constexpr int kFrostBurst = 2;                // 霜爆：3 公尺內凍結 ≥1 的敵人凍結 +2
inline constexpr float kFall = 2.0f;                 // 星落 ×2.0（隕星 ×3.0）
inline constexpr float kMeteor = 3.0f;
inline constexpr float kStarSever = 0.6f;            // 星斷：融斷改為真實傷害 ×0.6
inline constexpr float kChainEnd = 0.5f;             // 連鎖終焉 ×0.5
inline constexpr float kNoHeal = 100.0f;             // 死咒：無法治療（生命回復 -100%）3 秒，不治 6 秒
inline constexpr float kNoHealSeconds = 3.0f;
inline constexpr float kNoHealLong = 6.0f;
inline constexpr float kRotEnd = 20.0f;              // 腐蝕終焉：魔抗 -20% 8 秒
inline constexpr float kRotEndSeconds = 8.0f;
inline constexpr float kGuide = 1.5f;                // 大潮：導引 ×1.5（強引 ×2.0）
// death (2.6, 2.7, 5.x)
inline constexpr float kDeathShare = 0.5f;           // 中毒死亡擴散：S = max(R, 死者最大生命 × 30%) × 50%（蔓延 75%）
inline constexpr float kCreep = 0.75f;
inline constexpr float kDeathFloor = 0.3f;
inline constexpr float kDeathSpreadSeconds = 12.0f;  // 接收者 m' = min(m + S/12, 上限)、d' = max(d - t, 12)
inline constexpr int kChainFreeze = 3;               // 連鎖冰封：凍結 +3、減速 30% 3 秒
inline constexpr float kCremation = 0.5f;            // 火葬 ×0.5
inline constexpr float kSoulFear = 2.0f;             // 亡魂：恐懼 2 秒
inline constexpr float kWardBlast = 1.0f;            // 亡衛：3 公尺 B_max ×1.0 暗傷、詛咒 +2
inline constexpr int kWardCurse = 2;
inline constexpr float kDrink = 0.2f;                // 飲血：回血 20%，10 秒嗜血
inline constexpr float kThirstSeconds = 10.0f;
inline constexpr float kInheritResist = 0.5f;        // 血承：火冰雷毒魔抗各 50%、護甲 20%、最大生命 10%，15 秒
inline constexpr float kInheritArmor = 0.2f;
inline constexpr float kInheritHealth = 0.1f;
inline constexpr float kUndyingCooldown = 30.0f;     // 不死：每 30 秒一次
inline constexpr float kAshMagicka = 2.0f;           // 聖灰：魔力 B_max ×2
inline constexpr float kPureAsh = 1.0f;              // 淨灰：附近亡靈 B_max ×1.0 聖傷
inline constexpr float kRemnant = 0.25f;             // 殘魂：詛咒 1～2 層 25% 復生
inline constexpr float kServantAttack = 0.1f;        // 詛咒 5 層以上每層僕從攻擊 +10%
inline constexpr float kStreak = 5.0f;               // 連殺：5 秒
// burst (2.5, 5.1, 5.2)
inline constexpr std::array<float, 4> kSync{ 1.0f, 1.5f, 2.0f, 3.0f };   // K_sync by stage
inline constexpr int kHushCap = 5;                   // 寂：上限 5（寂上限 +1／每 5 點 → 8），10 秒
inline constexpr float kHushBurn = 0.05f;            // 每層燒目標最大魔力 5%（主線 +0.5%／點）
inline constexpr float kHushBurnPerPoint = 0.005f;
inline constexpr int kAllHush = 3;                   // 萬寂：寂 ≥3 層
inline constexpr float kAllHushTrue = 0.5f;          //       每清一種 B_max ×0.5 真實傷害
inline constexpr float kSever = 10.0f;               // 斷界：被結清元素的弱化 10%（決策：抗性削減）3 秒
inline constexpr float kSeverSeconds = 3.0f;
inline constexpr float kBackflow = 0.5f;             // 回流：每個印記 B_max ×0.5 魔力（可灌進超載）
inline constexpr float kDoubleBurst = 3.0f;          // 雙斷 3 秒
inline constexpr float kSafety = 2.0f;               // 安全閥 2 秒
inline constexpr float kEarthSever = 0.3f;           // 地斷：耐力低於 30%
inline constexpr float kFallingStar = 0.5f;          // 墜星：每層 ×0.5 闇星一擊
// astral (5.13)
inline constexpr float kEcho = 0.25f;                // 回聲 25%（主線 +1%／點，不吃節點倍率；夜晚 ×1.5）
inline constexpr float kEchoPerPoint = 0.01f;
inline constexpr float kEchoNight = 1.5f;
inline constexpr float kEclipse = 0.5f;              // 星蝕：闇星一擊的 50%
inline constexpr float kGatherBonus = 1.3f;          // 聚星：15 m 內共鳴目標 ≥3，這次引爆 +30%
inline constexpr int kGatherCount = 3;
// advent (5.x)
inline constexpr float kColdAdvent = 30.0f;          // 冰臨強化：減速 30% 3 秒
inline constexpr float kColdAdventSeconds = 3.0f;
inline constexpr float kEarthAdventStamina = 0.5f;   // 地臨強化：範圍內敵人耐力 -50%
inline constexpr float kBloodAdventCost = 0.15f;     // 血臨強化：付最大生命 15%（留 1 點），並濺血一次
inline constexpr float kPoisonAdvent = 3.0f;         // 毒臨強化：中毒 3 劑
inline constexpr float kDarkAdventFear = 2.0f;       // 暗臨強化：恐懼 2 秒
inline constexpr int kAstralAdvent = 2;              // 星臨強化：星痕 2 層
inline constexpr float kThreshold = 30.0f;           // 臨界：附近敵人減速 30% 2 秒
inline constexpr float kThresholdSeconds = 2.0f;
}  // namespace n5

// ================================================================ the crowd

inline constexpr int kCrowdSlots = n5::kCrowdMax + 1;
inline constexpr int kAroundYou = -1;   // Around(): centred on you

// One actor the engine read for this event. Member 0 is the event's own actor (the hit / ended / dying / pushed one;
// `has` false when there is none, e.g. a burst); the others are eligible actors (v0.4 2.9: hostile, of a hostile
// faction, or engaged by you in the last 30 s; never you, a teammate, a commanded actor or the dead) and, flagged
// `ally`, your teammates (聖光 heals them; nothing hostile ever selects them).
struct Member {
    bool has = false;
    bool ally = false;
    Board board{};
    Body body{};
    std::array<float, 3> pos{};
    int level = 1;
    bool dragon = false;          // never knocked, raised or turned to ash
    bool essential = false;       // 2.9 必要角色: essential, or filling a quest-object alias -- never knocked down, raised or
                                  // turned to ash (a unique / protected named enemy can be; review fix 2)
    bool spellUser = false;       // 5.1 "施法者": a spell in either hand, an armour spell or a cloak (HitMath TargetFacts)
    float armor = 0.0f;           // DamageResist (碎甲 10% of it)
    std::array<float, 5> resist{};   // fire, frost, shock, poison, magic (血承, 劇毒)
    float magicka = 0.0f;
    float magickaMax = 0.0f;
};

struct Crowd {
    std::array<Member, kCrowdSlots> m{};
    int count = 1;                // member 0 always exists (maybe empty)
    std::array<float, 3> you{};   // your position
};

constexpr float Distance(const std::array<float, 3>& a, const std::array<float, 3>& b) noexcept
{
    const float dx = a[0] - b[0];
    const float dy = a[1] - b[1];
    const float dz = a[2] - b[2];
    const float sq = dx * dx + dy * dy + dz * dz;
    if (sq <= 0.0f) {
        return 0.0f;
    }
    float r = sq > 1.0f ? sq : 1.0f;   // Newton's square root (constexpr; a few steps suffice for game units)
    for (int i = 0; i < 24; ++i) {
        r = 0.5f * (r + sq / r);
    }
    return r;
}

struct Picked {
    std::array<std::uint8_t, kCrowdSlots> k{};
    int n = 0;
};

// The hostile members within `radius` of `centre` (a member, or kAroundYou), `centre` itself excluded, nearest first,
// at most `limit`, that pass `keep`.
template <class Keep>
constexpr Picked Around(const Crowd& c, int centre, float radius, int limit, Keep&& keep)
{
    const std::array<float, 3>& at = centre == kAroundYou ? c.you : c.m[centre].pos;
    std::array<float, kCrowdSlots> d{};
    Picked p;
    for (int k = 0; k < c.count; ++k) {
        const Member& x = c.m[k];
        if (k == centre || !x.has || x.ally || !keep(x)) {
            continue;
        }
        const float dist = Distance(at, x.pos);
        if (dist > radius) {
            continue;
        }
        // insertion sort by distance (k order breaks ties, so the result is deterministic)
        int i = p.n;
        while (i > 0 && d[i - 1] > dist) {
            d[i] = d[i - 1];
            p.k[i] = p.k[i - 1];
            --i;
        }
        d[i] = dist;
        p.k[i] = static_cast<std::uint8_t>(k);
        ++p.n;
    }
    if (p.n > limit) {
        p.n = limit;
    }
    return p;
}

constexpr Picked Around(const Crowd& c, int centre, float radius, int limit)
{
    return Around(c, centre, radius, limit, [](const Member&) { return true; });
}

// ================================================================ what the body pass reads besides the crowd

struct BodyInputs {
    const StatusInputs* in = nullptr;  // tuning, config, you (PlayerFacts, Self), the N4 switch, the form element
    bool hitSneak = false;             // the hit behind these events was a sneak attack (奇襲)
    float stamina = 0.0f;              // your stamina and its max (不死, 無魔)
    float staminaMax = 0.0f;
    float magicka = 0.0f;              // your magicka and its max (回流, 無魔, 深淵回響, 水臨強化)
    float magickaMax = 0.0f;
};

// ================================================================ the timed utilities and other small op builders

constexpr StatusOp TimedOp(int kind, float magnitude, float seconds) noexcept
{
    StatusOp op = MakeOp(Op::kTimed, kTimedOnPlayer[kind] ? Who::kPlayer : Who::kTarget);
    op.element = kind;
    op.magnitude = magnitude;
    op.seconds = seconds;
    return op;
}

// A Papyrus push (ruling R4): kind 1 blow back, 2 pull toward you, 3 pull toward crowd member `centre` - 1 (風渦; 0 = none),
// 4 lift up. Plugin.cpp turns the member into its FormID when it sends the event (a float cannot carry a FormID).
constexpr StatusOp PushOp(int kind, float metres, float landing, int centre, bool slowIfImmune) noexcept
{
    return MakeEvent(Event::kPush, static_cast<float>(kind), metres, landing, static_cast<float>(centre), slowIfImmune ? 1.0f : 0.0f);
}

// ================================================================ the bodies

template <NodeReader Nodes, RandomSource Rng>
class Bodies
{
public:
    Bodies(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, const Nodes& nodes, Rng& rng) :
        plan_(plan), c_(crowd), self_(self), bin_(bin), nodes_(nodes), rng_(rng)
    {}

    const Tuning& T() const { return *bin_.in->tuning; }
    const Config& C() const { return *bin_.in->config; }
    float BMax(int element) const { return C().damage[element][1]; }
    bool Has(const BranchId& id) const { return nodes_.Has(id); }
    int Rank(const NodeId& id) const { return nodes_.Rank(id); }
    float Pct(int rank, float perPoint) const { return essb::Pct(T(), rank, perPoint); }
    float Sec(float seconds) const { return Scaled(T(), seconds); }

    // The inputs of the state rules for member k (its body replaces the event target's).
    StatusInputs InFor(int k) const
    {
        StatusInputs in = *bin_.in;
        in.body = c_.m[k].body;
        return in;
    }

    // Run a state rule (Status.h / SelfLayer.h) on member k: every target op it pushes is stamped with `at` = k.
    template <class Fn>
    void On(int k, Fn&& fn)
    {
        const std::uint8_t outer = plan_.at;
        plan_.at = static_cast<std::uint8_t>(k);
        const StatusInputs in = InFor(k);
        fn(c_.m[k].board, in);
        plan_.at = outer;
    }

    void Push(int k, StatusOp op)
    {
        if (op.who == Who::kTarget || op.op == Op::kEvent) {
            op.at = static_cast<std::uint8_t>(k);
        }
        plan_.Push(op);
    }

    // D_react (2.7) of `element` × K on member k: B_max × K × G × M_mod (the categorical terms) × the target's
    // vulnerabilities (嗜血、御風、空中追擊、星鎖、星域; 火域 for fire). M_ext and Res are the engine's.
    float React(int element, float k, int at) const
    {
        const Board& b = c_.m[at].board;
        float amount = BMax(element) * k * ReactionScale(element, T(), bin_.in->player, nodes_) *
                       ReactionVulnerability(b, self_, T(), nodes_);
        if (element == kFire && b.Has(StatusKind::kDomainFire)) {
            amount *= n3::kDomain;
        }
        if (element == kDivine && b.Has(StatusKind::kRadiance) && c_.m[at].body.undeadOrDaedra) {
            amount *= 1.0f + n5::kRadiance;   // 光耀
        }
        return amount;
    }

    void Damage(int k, int element, float amount)
    {
        if (amount > 0.0f) {
            Push(k, Amount(Op::kDamage, amount, element));
        }
    }

    void Heal(float amount) { plan_.Push(Amount(Op::kHeal, amount * T().multRecovery)); }
    void Magicka(float amount) { plan_.Push(Amount(Op::kRestoreMagicka, amount * T().multRecovery)); }
    void Stamina(float amount) { plan_.Push(Amount(Op::kRestoreStamina, amount * T().multRecovery)); }
    void Slow(int k, float pct, float seconds) { Push(k, Amount(Op::kSlow, pct, 0, Sec(seconds))); }
    void Timed(int k, int kind, float magnitude, float seconds)
    {
        if (kind == timed::kArmorDebuff) {
            magnitude *= T().multDrain;   // the Papyrus drains (碎甲、裂痕) took ESSB_MultDrain
        }
        Push(k, TimedOp(kind, magnitude, Sec(seconds)));
    }
    void DrainMagicka(int k, float amount) { Push(k, Amount(Op::kDrainMagicka, amount * T().multDrain)); }
    void DrainStamina(int k, float amount) { Push(k, Amount(Op::kDrainStamina, amount * T().multDrain)); }
    void Event(int k, StatusOp op) { Push(k, op); }

    // 5.8 吸血 at the current blood zone (the open's "依血位吸血", 深血痕, the surge's heal).
    float Leech() const { return LeechRatio(bin_.in->player, nodes_); }

    // ---------------------------------------------------------------- open (2.6 開印 + the open branches)

    void Open(int k, int element, float mult, int cutFrom, bool fromHit)
    {
        (void)cutFrom;
        Member& m = c_.m[k];
        switch (element) {
        case kFire:
            Damage(k, kFire, React(kFire, n5::kFireOpen * mult, k));   // 點燃：B_max ×0.5
            if (Has(node::kFireEmberHeat)) {
                Stamina(n5::kEmberStamina);   // 餘熱
            }
            if (Has(node::kFireFlareUp)) {
                // 焰起強化：開印額外對範圍內敵人一次火附傷（決策：一次火的附傷——隨機 B、火附傷的 M_mod、你的熱度）。
                const Picked p = Around(c_, k, n5::kNear, n5::kNearLimit);
                for (int i = 0; i < p.n; ++i) {
                    Damage(p.k[i], kFire, FireProc(p.k[i]));
                }
            }
            if (Has(node::kFirePreBurn) && T().syncStage >= 3) {
                // 先燃：同調三段時開印立即一次 ×0.5 爆燃（不消耗目標狀態），照你的熱度。
                Detonate(k, n5::kPreBurn, HeatTier(self_), 0.0f, 1.0f, false);
            }
            break;
        case kFrost: {
            Slow(k, T().frostOpenSlowPct * mult, n5::kFrostOpenSeconds);   // 霜結：減速 25% 3 秒
            if (Has(node::kFrostColdTide)) {
                const Picked p = Around(c_, k, n5::kNear, 1);   // 寒潮：附近 1 人凍結 +2
                for (int i = 0; i < p.n; ++i) {
                    On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::AddFreeze(plan_, b, 2.0f, false, in, nodes_, rng_); });
                }
            }
            break;
        }
        case kLightning:
            DrainMagicka(k, BMax(kLightning) * n5::kShockOpenDrain * mult);   // 感電：目標魔力 -B_max ×1.0
            if (Has(node::kLightningConduct)) {
                SpreadMark(k, kLightning);   // 傳導
            }
            if (Has(node::kLightningChargeOpen)) {
                Magicka(BMax(kLightning));   // 充能開印：開印時回復 B_max 魔力
            }
            if (Has(node::kLightningWeaken)) {
                Timed(k, timed::kMagicResistDebuff, n5::kWeaken, n5::kWeakenSeconds);   // 感電削弱
            }
            if (Has(node::kLightningFlash)) {
                Timed(0, timed::kHaste, n5::kFlash, n5::kFlashSeconds);   // 雷閃
            }
            if (Has(node::kLightningFirst) && T().syncStage >= 3) {
                // 先雷：同調三段時開印立即放電一次，不消耗電荷（暴擊照一般放電擲）。
                const int charges = self_.Layers(StatusKind::kCharge);
                DischargeAll(k, charges, 1.0f, 1.0f, CritRoll(charges, false));
            }
            break;
        case kEarth: {
            const float armor = n5::kFissureArmor + n5::kFissureArmorPerPoint * static_cast<float>(Rank(node::kEarthFissureArmor));
            Timed(k, timed::kArmorDebuff, armor * mult, n5::kFissureSeconds);   // 裂痕：護甲 -30（主線 +2／點）
            DrainStamina(k, n5::kFissureStamina * mult);                        //       耐力 -10
            Stamina(n5::kFissureStamina * mult);                                //       你回 10 耐力
            if (Has(node::kEarthWave)) {
                const Picked p = Around(c_, k, n5::kNear, 1);   // 震波：附近 1 人也裂痕
                for (int i = 0; i < p.n; ++i) {
                    On(p.k[i], [&](Board& b, const StatusInputs& in) {
                        Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kFissure, 1.0f, Scaled(*in.tuning, n3::kFissure));
                    });
                    Timed(p.k[i], timed::kArmorDebuff, armor, n5::kFissureSeconds);
                }
            }
            if (Has(node::kEarthDeepFissure) && m.body.staminaMax > 0.0f && m.body.stamina / m.body.staminaMax < n3::kDeepFissure) {
                Event(k, MakeEvent(Event::kKnock, n5::kKnock));   // 深裂痕的推力（倒地在 DLL 開印時已掛）
            }
            if (Has(node::kEarthBase)) {
                Timed(k, timed::kStaminaRateDebuff, n5::kStill, n5::kBaseSeconds);   // 地基
            }
            if (Has(node::kEarthFirstQuake) && T().syncStage >= 3) {
                Quake(k, n5::kFirstQuake, false);   // 先震：×0.5 地震，不含跌倒
            }
            break;
        }
        case kWind: {
            const bool ambush = Has(node::kWindAmbush) && bin_.hitSneak && fromHit;   // 奇襲
            if (!ambush) {
                const float metres = std::min(n5::kPullMax, n5::kPull + n5::kPullPerPoint * static_cast<float>(Rank(node::kWindPullRange)));
                Event(k, PushOp(2, metres * mult, 0.0f, 0, false));   // 風痕：拉近你 1.5 m（推力在 Papyrus）
                if (Has(node::kWindDrag)) {
                    // 牽引：目標身後（比目標離你遠）1.5 m 內的其他敵人也一起拉近並失衡，最多 2 人。
                    const float behind = Distance(c_.you, m.pos);
                    const Picked p = Around(c_, k, n5::kDrag, n5::kCrowdMax,
                        [&](const Member& x) { return Distance(c_.you, x.pos) > behind; });
                    for (int i = 0; i < p.n && i < n5::kDragLimit; ++i) {
                        Event(p.k[i], PushOp(2, metres * mult, 0.0f, 0, false));
                        On(p.k[i], [&](Board& b, const StatusInputs& in) {
                            Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kUnbalance, 1.0f, Scaled(*in.tuning, n3::kUnbalance));
                        });
                    }
                }
            }
            if (Has(node::kWindRaid)) {
                SpreadMark(k, kWind, [&](int j) {   // 風襲：附近 1 人也風痕（失衡）
                    On(j, [&](Board& b, const StatusInputs& in) {
                        Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kUnbalance, 1.0f, Scaled(*in.tuning, n3::kUnbalance));
                    });
                });
            }
            if (Has(node::kWindLeap)) {
                Timed(0, timed::kHaste, n5::kLeap, n5::kLeapSeconds);   // 輕躍
            }
            if (Has(node::kWindGust)) {
                Stamina(n5::kGust);   // 氣流
            }
            if (ambush) {
                // 奇襲：一刀開印兼吹飛——立即結算一次風終焉的本體（不往外連鎖），失衡照吹飛吹掉。
                On(k, [&](Board& b, const StatusInputs&) { Writer{ plan_, b, Who::kTarget }.Clear(StatusKind::kUnbalance); });
                WindEnd(k, 1.0f, EndReason::kCut);
            }
            break;
        }
        case kBlood: {
            HealLeech(n5::kOpenLeech * Leech() * mult);   // 血痕：依血位吸血
            if (Has(node::kBloodSpatter)) {
                const Picked p = Around(c_, k, n5::kNear, 1);   // 血濺：附近 1 人流血 1 層
                for (int i = 0; i < p.n; ++i) {
                    On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::AddBleed(plan_, b, 1, in, nodes_); });
                }
            }
            if (Has(node::kBloodOpenHeal)) {
                const bool low = bin_.in->self.Fraction() < n3::kZoneLow;
                Heal(BMax(kBlood) * n5::kOpenHeal * (low ? 2.0f : 1.0f));   // 開印回血：B_max ×0.5，低血位 ×2
            }
            if (Has(node::kBloodCurse)) {
                Timed(k, timed::kHealRateDebuff, n5::kBloodCurse, n5::kBloodCurseSeconds);   // 血咒
            }
            if (Has(node::kBloodDeepMark)) {
                const int zone = BloodZone(bin_.in->self);   // 深血痕的吸血：中血區一次、低血區兩次
                const int times = zone == 3 ? 2 : zone == 2 ? 1 : 0;
                for (int i = 0; i < times; ++i) {
                    HealLeech(n5::kOpenLeech * Leech());
                }
            }
            if (Has(node::kBloodSacrifice) && T().syncStage >= 3) {
                SurgeOn(k, n5::kSacrifice, true);   // 血祭之始：×0.5 血潮
            }
            break;
        }
        case kDivine: {
            Heal(BMax(kDivine) * (n5::kDivineOpenHeal * mult + n5::kDivineOpenPerPoint * static_cast<float>(Rank(node::kDivineOpenHeal))));
            if (Has(node::kDivineGlow)) {
                SpreadMark(k, kDivine);   // 聖輝
            }
            if (Has(node::kDivineLight)) {
                // 聖光：開印時附近同伴回血 B_max（決策：你身邊 15 m 內的同伴）。
                for (int j = 1; j < c_.count; ++j) {
                    if (c_.m[j].has && c_.m[j].ally && Distance(c_.you, c_.m[j].pos) <= n5::kNear) {
                        Push(j, Amount(Op::kHealTarget, BMax(kDivine) * T().multRecovery));
                    }
                }
            }
            break;
        }
        case kPoison: {
            // 淬毒：立即向 3 公尺內一名敵人傳 1 劑（2.7 擴散一劑）。
            const Picked p = Around(c_, k, n5::kTransfer, 1);
            const int doses = RoundStochastic(mult, rng_);
            for (int i = 0; i < p.n && doses > 0; ++i) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::SpreadDoses(plan_, b, static_cast<float>(doses), in, nodes_); });
            }
            if (Has(node::kPoisonSplash)) {
                const Picked q = Around(c_, k, n5::kNear, 1);   // 毒濺：附近 1 人 2 劑（擴散一劑的規則）
                const int splash = RoundStochastic(n5::kPoisonSplash * mult, rng_);
                for (int i = 0; i < q.n; ++i) {
                    On(q.k[i], [&](Board& b, const StatusInputs& in) { rule::SpreadDoses(plan_, b, static_cast<float>(splash), in, nodes_); });
                }
            }
            if (Has(node::kPoisonThick)) {
                // 濃毒：6 公尺內已有中毒的敵人，從劑數最高的那一個複製 2 劑到新目標（不從對方扣）。
                const Picked q = Around(c_, k, n5::kSixMetres, n5::kCrowdMax, [](const Member& x) { return x.board.poisonDot.has; });
                if (q.n > 0) {
                    On(k, [&](Board& b, const StatusInputs& in) { rule::SpreadDoses(plan_, b, n5::kThick, in, nodes_); });
                }
            }
            if (Has(node::kPoisonFilm)) {
                Timed(0, timed::kPoisonResistBuff, n5::kFilm, n5::kFilmSeconds);   // 毒膜
            }
            if (Has(node::kPoisonRot)) {
                Timed(k, timed::kPoisonResistDebuff, n5::kRot, n5::kRotSeconds);   // 腐蝕開印
            }
            if (Has(node::kPoisonBlood)) {
                Heal(BMax(kPoison) * n5::kPoisonBlood);   // 毒血
            }
            break;
        }
        case kWater: {
            const int rank = Rank(node::kWaterOpenHeal);
            if (rank > 0) {
                const float share = n5::kWaterOpenPerPoint * static_cast<float>(rank);   // 開印時回復生命與耐力各 0.3%／點
                Heal(bin_.in->self.healthMax * share);
                Stamina(bin_.staminaMax * share);
            }
            if (Has(node::kWaterSpread)) {
                SpreadMark(k, 0, [&](int j) {   // 廣佈：浸濕擴散到附近 1 人（浸濕的減速與時長）
                    On(j, [&](Board& b, const StatusInputs& in) {
                        Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kSoak, 1.0f, rule::SoakSeconds(*in.tuning, nodes_));
                    });
                    Push(j, Amount(Op::kSlow, SoakSlowPct(T()), 0, rule::SoakSeconds(T(), nodes_)));
                }, [](const Member& x) { return !x.board.Has(StatusKind::kSoak); });
            }
            if (Has(node::kWaterSpring)) {
                Stamina(T().waterOpenStamina);   // 湧泉：回復耐力 80
            }
            if (Has(node::kWaterOpenWash) && !m.board.Has(StatusKind::kWashCooldown)) {
                // 開印沖刷：驅散目標一個有時限的增益，每目標每 10 秒一次（淨潮照算）。
                On(k, [&](Board& b, const StatusInputs& in) {
                    Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kWashCooldown, 1.0f, CooldownOf(*in.tuning, n3::kWashCooldown));
                });
                StatusOp wash = Amount(Op::kWash, Has(node::kWaterPurgeTide) ? 2.0f * BMax(kWater) : 0.0f);
                wash.element = 1;   // one buff
                Push(k, wash);
            }
            break;
        }
        case kDarkness: {
            const float drain = BMax(kDarkness) * n5::kDarkOpenDrain * mult;   // 詛咒：吸魔 B_max ×1.0
            DrainMagicka(k, drain);
            Magicka(drain);
            if (Has(node::kDarkStain)) {
                SpreadMark(k, kDarkness, [&](int j) {   // 暗染：附近 1 人也詛咒
                    On(j, [&](Board& b, const StatusInputs& in) { rule::AddCurse(plan_, b, n5::kStainCurse, in, nodes_); });
                });
            }
            break;
        }
        case kAstral: {
            if (Has(node::kAstralBright)) {
                // 明星：15 公尺內已有其他共鳴目標時，新目標與最近的那一個星痕各 +1（在星散之前判定）。
                const Picked p = Around(c_, k, n5::kNear, 1, [](const Member& x) { return x.board.Has(StatusKind::kStar); });
                if (p.n > 0) {
                    On(k, [&](Board& b, const StatusInputs& in) { rule::AddStars(plan_, b, 1, in, nodes_); });
                    On(p.k[0], [&](Board& b, const StatusInputs& in) { rule::AddStars(plan_, b, 1, in, nodes_); });
                }
            }
            if (Has(node::kAstralScatter) && !(bin_.in->n4 && self_.Has(StatusKind::kCosmos))) {
                SpreadMark(k, kAstral, [&](int j) {   // 星散：附近 1 人也星痕（也進入共鳴）
                    On(j, [&](Board& b, const StatusInputs& in) { rule::AddStars(plan_, b, 1, in, nodes_); });
                });
            }
            break;
        }
        default:
            break;
        }
    }

    // ---------------------------------------------------------------- end (2.6 終焉 + the closing branches)

    void End(int k, int element, EndReason reason, float mult, int flags, float v1, float v2, float v3, int charge)
    {
        const bool chain = (flags & 1) != 0;
        const bool afterSwitch = (flags & 2) != 0;
        // 融斷 (commander ruling, v0.4 2.7 D_burst): a fused mark deals B_max × K_sync × G × M_mod (the burst main lines in
        // M_mod) -- no K_react; the element's own end move (爆燃, 碎冰 ×1.0, 放電, 地震, 風刃, 血潮, 裁決, 星落) is not
        // dealt. The end's non-damage part (the state part in Status.h: consumption, catalysis ×4 with 毒斷, guidance,
        // the death-curse fuse and its no-heal, the star detonation; 2.5's lift) and every branch still apply.
        // 2.7: the closing lines (common 終焉／終焉再／同調三段時終焉 × the tree's 終焉 main) and, for a burst, the tree's
        // 融斷 main lines (and 雷斷); a chain end takes none of them (like the Papyrus body did).
        float body = mult;
        if (!chain) {
            body *= EndNodeMult(element, T(), nodes_);
            if (reason == EndReason::kBurst) {
                body *= BurstNodeMult(element);
                if (element == kLightning && Has(node::kLightningBurstBonus)) {
                    body *= 1.0f + n5::kPerCharge * static_cast<float>(charge);   // 雷斷：附加全部電荷的放電加成
                }
            }
        }
        const bool fused = reason == EndReason::kBurst && !chain;
        if (fused) {
            FusionHit(k, element, body);
        }
        switch (element) {
        case kFire:
            if (!fused) {
                Detonate(k, body, static_cast<int>(v1 + 0.5f), v2, v3, true);
            }
            if (!chain && Has(node::kFireSkyfire)) {
                // 焚天：範圍內所有帶火印記的目標一起爆燃（各自吃自己身上的狀態）——各一次連鎖終焉。
                const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit, [](const Member& x) { return x.board.mark[kFire].has; });
                for (int i = 0; i < p.n; ++i) {
                    ChainEndOn(p.k[i], kFire, body);
                }
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kFireDomain)) {
                Event(k, MakeEvent(Event::kDomain, kFire, 5.0f, n5::kArea));   // 火域（領域 N6，Papyrus）
            }
            break;
        case kFrost:
            if (v1 < 0.5f) {
                if (!fused) {
                    Damage(k, kFrost, React(kFrost, n5::kFrostEnd * body * Signature(kFrost), k));   // 未冰封：B_max ×1.0
                }
            } else if (!chain && Has(node::kFrostGlacier) && !Has(node::kFrostAvalanche)) {
                ShatterArea(k);   // 冰河：冰終焉時目標若冰封，範圍內冰封目標一起碎冰（冰崩在碎冰事件裡已做）
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kFrostPlain)) {
                Event(k, MakeEvent(Event::kDomain, kFrost, 5.0f, n5::kArea));   // 冰原
            }
            break;
        case kLightning:
            if (charge > 0) {
                if (!fused) {
                    DischargeAll(k, charge, body, v1, EndCrit(charge, v2, v3 >= 0.5f));
                }
                if (!chain && Has(node::kLightningStrike)) {
                    // 雷殛：雷終焉對範圍內所有感電目標各一次全額放電。
                    const Picked p = Around(c_, k, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.mark[kLightning].has; });
                    for (int i = 0; i < p.n; ++i) {
                        Discharge(p.k[i], charge, body, 1.0f, CritRoll(charge, false), true);
                    }
                }
            }
            break;
        case kEarth: {
            if (!fused) {
                float quake = body;
                if (!chain && self_.Has(StatusKind::kChargedQuake)) {
                    quake *= 1.0f + self_[StatusKind::kChargedQuake].magnitude;   // 蓄能：下一次地震 +5%／點，用掉
                    Writer{ plan_, self_, Who::kPlayer }.Clear(StatusKind::kChargedQuake);
                }
                Quake(k, quake, true);
            }
            if (!chain && Has(node::kEarthLandslide)) {
                // 山崩：土終焉對範圍內所有帶裂痕的目標各一次地震。
                const Picked p = Around(c_, k, QuakeRadius(), n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kFissure); });
                for (int i = 0; i < p.n; ++i) {
                    Quake(p.k[i], body, false);
                }
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kEarthRiftZone)) {
                Event(k, MakeEvent(Event::kDomain, kEarth, 5.0f, n5::kArea));   // 地裂
            }
            break;
        }
        case kWind:
            if (fused) {
                Event(k, PushOp(4, n5::kLift, LandingStored(), 0, true));   // 2.5 融斷：吹上天
            } else {
                WindEnd(k, body, reason);
            }
            if (!chain && Has(node::kWindVortex)) {
                // 風渦：終焉時 5 公尺內敵人被拉向目標聚攏（推力在 Papyrus）。
                const Picked p = Around(c_, k, n5::kVortex, n5::kNearLimit);
                for (int i = 0; i < p.n; ++i) {
                    Event(p.k[i], PushOp(3, n5::kVortexPull, 0.0f, k + 1, false));
                }
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kWindSever)) {
                Blade(k, 1.0f);   // 風斷：風印記融斷時每個目標各兩段風刃
                Blade(k, 1.0f);
            }
            break;
        case kBlood:
            if (!fused) {
                Surge(k, v1, body, reason, chain);
            }
            if (!chain && !fused && Has(node::kBloodFlood)) {   // 血漫 follows a 血潮, which a fusion does not deal
                // 血漫：血潮結算時附近流血目標一起血潮。
                const Picked p = Around(c_, k, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kBleed); });
                for (int i = 0; i < p.n; ++i) {
                    SurgeOn(p.k[i], body, true);
                }
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kBloodPool)) {
                Event(k, MakeEvent(Event::kDomain, kBlood, 5.0f, n5::kArea));   // 血池
            }
            break;
        case kDivine:
            if (!fused) {
                JudgeArea(k, body, static_cast<int>(v1 + 0.5f));
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kDivineSever)) {
                Heal(BMax(kDivine));   // 聖斷：聖印記融斷每個目標治療你 B_max ×1.0
            }
            if (!chain) {
                if (reason == EndReason::kBurst && Has(node::kDivineHolyDomain)) {
                    Event(k, MakeEvent(Event::kDomain, kDivine, 8.0f, n5::kArea));   // 神聖領域：8 秒聖域
                } else if (Has(node::kDivineSanctum)) {
                    Event(k, MakeEvent(Event::kDomain, kDivine, 5.0f, n5::kArea));   // 聖域：5 秒
                }
            }
            break;
        case kPoison: {
            const Member& m = c_.m[k];
            if (!chain && Has(node::kPoisonVirulent) && m.board.poisonDot.has && m.resist[3] > 0.0f) {
                // 劇毒：催毒期間目標毒抗視為 0——一個等於它當前毒抗的削減，持續到中毒剩下的秒數。
                Push(k, TimedOp(timed::kPoisonResistDebuff, m.resist[3], m.board.poisonDot.Remaining()));
            }
            if (!chain && Has(node::kPoisonRotEnd)) {
                Timed(k, timed::kMagicResistDebuff, n5::kRotEnd, n5::kRotEndSeconds);   // 腐蝕終焉
            }
            if (!chain && Has(node::kPoisonInfect) && m.board.poisonDot.has) {
                // 疫染：把目標的中毒（同強度同剩餘）複製到 6 公尺內敵人（取較強、較久的）。
                const Slot copy = m.board.poisonDot;
                const float factor = rule::PoisonFactor(m.board);
                const Picked p = Around(c_, k, n5::kSixMetres, n5::kNearLimit);
                for (int i = 0; i < p.n; ++i) {
                    On(p.k[i], [&](Board& b, const StatusInputs& in) {
                        rule::Poison next{ std::max(copy.magnitude, b.poisonDot.magnitude), std::max(copy.Remaining(), b.poisonDot.Remaining()) };
                        if (factor > 1.0f && !b.Has(StatusKind::kCatalyzed)) {
                            Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kCatalyzed, factor, next.remaining);
                        }
                        rule::SetPoison(plan_, b, next, in, nodes_);
                    });
                }
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kPoisonFog)) {
                Event(k, MakeEvent(Event::kDomain, kPoison, 5.0f, n5::kArea));   // 毒霧（劑數併入：10.4 待決）
            }
            break;
        }
        case kWater:
            if (reason == EndReason::kCut && !chain && Has(node::kWaterFlood)) {
                // 大潮：水終焉時範圍內所有浸濕目標都給接管元素導引。
                const float guide = (Has(node::kWaterStrongGuide) ? n3::kStrongGuide : n5::kGuide) * Signature(kWater) * body;
                const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kSoak); });
                for (int i = 0; i < p.n; ++i) {
                    On(p.k[i], [&](Board& b, const StatusInputs& in) {
                        Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kGuided, guide, Scaled(*in.tuning, 30.0f));
                    });
                }
            }
            if (!chain && Has(node::kWaterScour)) {
                plan_.Push(MakeEvent(Event::kCleanse, 1));   // 洗滌：清除你所有負面效果（本體在 Papyrus，同洗淨）
                StatusOp wash = Amount(Op::kWash, Has(node::kWaterPurgeTide) ? 2.0f * BMax(kWater) : 0.0f);
                wash.element = 1;   // 並驅散目標一個有時限的增益
                Push(k, wash);
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kWaterTidePool)) {
                Event(k, MakeEvent(Event::kDomain, kWater, 5.0f, n5::kArea));   // 潮池
            }
            break;
        case kDarkness:
            Timed(k, timed::kHealRateDebuff, n5::kNoHeal, Has(node::kDarkNoHeal) ? n5::kNoHealLong : n5::kNoHealSeconds);   // 死咒期間無法治療
            if (!chain && Has(node::kDarkAbyssEcho)) {
                Magicka(bin_.magickaMax);   // 深淵回響：回滿你的魔力
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kDarkDeathZone)) {
                Event(k, MakeEvent(Event::kDomain, kDarkness, 5.0f, n5::kArea));   // 死域
            }
            break;
        case kAstral: {
            if (!fused) {
                const float amount = BMax(kAstral) * (Has(node::kAstralMeteor) ? n5::kMeteor : n5::kFall) * body * Signature(kAstral);
                Damage(k, kAstral, React(kAstral, amount / BMax(kAstral), k));
            }
            // 星落：15 公尺內所有共鳴目標（含本人，本人已由狀態部分引爆）的星痕立即引爆，最多 5 人。
            const Picked p = Around(c_, k, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kStar); });
            for (int i = 0; i < p.n; ++i) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::DetonateStars(plan_, b, self_, in, nodes_, 1.0f); });
            }
            if (reason == EndReason::kBurst && !chain && Has(node::kAstralZone)) {
                Event(k, MakeEvent(Event::kDomain, kAstral, 5.0f, n5::kArea));   // 星域
            }
            break;
        }
        default:
            break;
        }
        if (chain) {
            return;
        }
        if (Has(node::kCommonFeed)) {
            Magicka(BMax(element));   // 反哺：每次終焉回復你 B_max 魔力
        }
        // 連鎖終焉：附近帶同一印記的目標也終焉 ×0.5；大協奏：切換後首次終焉讓範圍內帶舊印記的敵人各終焉一次。
        const bool chainEnd = Has(node::kCommonChainEnd);
        const bool grand = Has(node::kCommonGrand) && afterSwitch;
        if (chainEnd || grand) {
            const Picked p = Around(c_, k, n5::kNear, n5::kNearLimit, [&](const Member& x) { return x.board.mark[element].has; });
            for (int i = 0; i < p.n; ++i) {
                ChainEndOn(p.k[i], element, body * (grand ? 1.0f : n5::kChainEnd));
            }
        }
    }

    // ---------------------------------------------------------------- the other body events

    // 冰封開始：冰封期間的強減速 50%（絕對零度：同調三段時 -2%／點，上限 70%），深寒；霜爆。
    void Frozen(int k, float seconds)
    {
        float slow = n5::kFrozenSlow;
        if (T().syncStage >= 3) {
            slow += n5::kZeroPerPoint * static_cast<float>(Rank(node::kFrostZero));
        }
        Push(k, Amount(Op::kSlow, slow, 0, seconds));
        if (Has(node::kFrostDeepChill)) {
            Push(k, TimedOp(timed::kMeleeDebuff, n5::kDeepChill, seconds));
            Push(k, TimedOp(timed::kStaminaRateDebuff, n5::kStill, seconds));
        }
        if (Has(node::kFrostBurst)) {
            const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit, [](const Member& x) { return x.board.Layers(StatusKind::kFreeze) >= 1; });
            for (int i = 0; i < p.n; ++i) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) {
                    rule::AddFreeze(plan_, b, static_cast<float>(n5::kFrostBurst), false, in, nodes_, rng_);
                });
            }
        }
    }

    // 幻覺的範圍那一半：夢魘（恐懼時 3 m 內其他敵人詛咒 +1）、群魔（同調三段瘋狂時 4 m 內詛咒 ≥3 的一起瘋狂 3 秒）。
    void Hallucinate(int k, int kind)
    {
        if (kind == 1 && Has(node::kDarkNightmare)) {
            const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit);
            for (int i = 0; i < p.n; ++i) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::AddCurse(plan_, b, 1, in, nodes_); });
            }
        }
        if (kind == 2 && Has(node::kDarkLegion) && T().syncStage >= 3) {
            const Picked p = Around(c_, k, n5::kLegion, n5::kNearLimit, [](const Member& x) {
                return x.board.Layers(StatusKind::kCurse) >= 3 && !x.board.Has(StatusKind::kFrenzyCooldown);
            });
            for (int i = 0; i < p.n; ++i) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) {
                    Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kFrenzyCooldown, 1.0f, CooldownOf(*in.tuning, n3::kFrenzyCooldown));
                });
                // arg 2 = 1: a group frenzy (Papyrus skips a target it cannot charm, no 幻視 for it)
                Event(p.k[i], MakeEvent(Event::kHallucinate, 2, Sec(n3::kFrenzy), 1));
            }
        }
    }

    // 聖裁 II／III 的破防（護甲 -60、魔抗 -10%，5 秒）；III 的 3 m 聖光爆；破邪斬（III：主目標傷害 50% 濺到 4 m 內）。
    void Judgment(int k, int tier, float damage)
    {
        Timed(k, timed::kArmorDebuff, n5::kBreakArmor, n5::kBreakSeconds);
        Timed(k, timed::kMagicResistDebuff, n5::kBreakMR, n5::kBreakSeconds);
        if (tier < 3) {
            return;
        }
        const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            float blast = React(kDivine, n5::kHolyBlast, p.k[i]);
            if (c_.m[p.k[i]].body.undeadOrDaedra) {
                blast *= n3::kPrey;
            }
            Damage(p.k[i], kDivine, blast);
        }
        if (Has(node::kDivineSmite) && damage > 0.0f) {
            const Picked q = Around(c_, k, n5::kSmite, n5::kNearLimit);
            // the main hit's damage was computed with the main target's multipliers; the splash takes 50% of the
            // plain part and each receiver's own vulnerability, ×3 on the undead
            const float plain = damage / std::max(0.001f, ReactionVulnerability(c_.m[k].board, self_, T(), nodes_) *
                                                            (c_.m[k].body.undeadOrDaedra ? n3::kPrey : 1.0f));
            for (int i = 0; i < q.n; ++i) {
                float splash = plain * n5::kSmiteShare * ReactionVulnerability(c_.m[q.k[i]].board, self_, T(), nodes_);
                if (c_.m[q.k[i]].body.undeadOrDaedra) {
                    splash *= n3::kPrey;
                }
                Damage(q.k[i], kDivine, splash);
            }
        }
    }

    // 濺血：15 公尺內所有流血目標（最多 5）一次 ×0.5 血潮，不清除血痕（以你為中心）。
    void Splash()
    {
        const Picked p = Around(c_, kAroundYou, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kBleed); });
        for (int i = 0; i < p.n; ++i) {
            SurgeOn(p.k[i], 0.5f, false);
        }
    }

    // 往上越線的血約：15 公尺內所有流血目標血痕 +2 層。
    void Rise()
    {
        if (!Has(node::kBloodPact)) {
            return;
        }
        const Picked p = Around(c_, kAroundYou, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kBleed); });
        for (int i = 0; i < p.n; ++i) {
            On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::AddBleed(plan_, b, 2, in, nodes_); });
        }
    }

    // 碎冰之後：碎甲 10%（碎甲加深 20%）5 秒；冰崩：碎冰範圍化為 3 公尺。
    void Shattered(int k, int source)
    {
        const float shred = Has(node::kFrostArmorBreak) ? n5::kDeepShred : n5::kShred;
        if (c_.m[k].armor > 0.0f) {
            Timed(k, timed::kArmorDebuff, c_.m[k].armor * shred, n5::kShredSeconds);
        }
        if (Has(node::kFrostAvalanche) && source != 3) {
            ShatterArea(k);
        }
    }

    void Landing(int k, float stored)
    {
        Damage(k, kWind, stored * ReactionScale(kWind, T(), bin_.in->player, nodes_) * ReactionVulnerability(c_.m[k].board, self_, T(), nodes_));
    }

    // 過熱：15 公尺內所有帶火印記的目標自動爆燃（各一次連鎖終焉，以你為中心）。
    void Overheat()
    {
        const Picked p = Around(c_, kAroundYou, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.mark[kFire].has; });
        for (int i = 0; i < p.n; ++i) {
            On(p.k[i], [&](Board& b, const StatusInputs& in) {
                Writer{ plan_, b, Who::kTarget }.Unmark(kFire);
                if (!b.Has(StatusKind::kEndCooldown)) {
                    PlanEndBody(plan_, kFire, EndReason::kExpire, 1.0f, false, b, self_, in, nodes_, rng_, true);   // a chain end
                }
            });
        }
    }

    // ---------------------------------------------------------------- shared pieces

    // The fusion hit of one mark: B_max × K (K_sync × the common / 冷寂 / X印記的融斷 lines × the end lines, the guide; 雷斷
    // adds the charges) × G × M_mod's categorical terms × the target's vulnerabilities. 水斷 turns it into a heal and a
    // stamina restore of B_max × K × G, 星斷 into true damage ×0.6 (G of the astral tree), 血斷 heals 50% of it.
    void FusionHit(int k, int element, float mult)
    {
        if (element == kWater && Has(node::kWaterSever)) {
            const float amount = BMax(kWater) * mult * TreeG(T(), TreeOf(kWater));
            Heal(amount);
            Stamina(amount);
            return;
        }
        if (element == kAstral && Has(node::kAstralSever)) {
            Push(k, Amount(Op::kDamage, BMax(kAstral) * mult * n5::kStarSever * TreeG(T(), TreeOf(kAstral)) * T().baseDamageMult, 0));
            return;
        }
        const float amount = React(element, mult, k);
        Damage(k, element, amount);
        if (element == kBlood && Has(node::kBloodSever)) {
            HealLeech(amount * n5::kBloodSever);   // 血斷：融斷治療 50%
        }
    }

    float Signature(int element) const
    {
        return 1.0f + Pct(Rank(node::kSignature[element]), 0.03f);   // 關閉傳奇主線：該元素終焉招式 +3%／點
    }

    float BurstNodeMult(int element) const
    {
        return 1.0f + Pct(Rank(node::kBurstMain[element]), 0.02f) + Pct(Rank(node::kBurstAgain[element]), 0.02f);
    }

    float QuakeRadius() const { return Has(node::kEarthWide) ? n5::kWideQuake : n5::kArea; }

    float CritRoll(int charges, bool) { return rng_.Real(0.0f, 1.0f) < LightningCritChance(charges) + (self_.Has(StatusKind::kQuickShock) ? n4::kQuickShock : 0.0f) ? 1.5f : 1.0f; }

    void HealLeech(float amount)
    {
        if (amount > 0.0f) {
            plan_.Push(Amount(Op::kHeal, amount * T().multRecovery));
        }
    }

    // One fire proc on member k (焰起強化): random B, R 1, G, the fire proc's M_mod (with the statuses' terms), heat.
    float FireProc(int k)
    {
        const Member& m = c_.m[k];
        const ProcTerm term = ProcTerms(kFire, false, T(), m.board, self_, m.body, nodes_);
        StatusTerms terms;
        terms.add[kFire] = term.add;
        terms.mult[kFire] = term.mult;
        Attack a;
        a.element = kFire;
        TargetFacts facts;
        facts.undeadOrDaedra = m.body.undeadOrDaedra;
        return RollProc(kFire, a, C(), T(), bin_.in->player, facts, nodes_, rng_, terms).magnitude;
    }

    // 爆燃 (2.6): B_max × 熱度倍率 × (1 + 消耗加成) × 熾焰 × mult × 爆燃 +3%／點. `mark` puts the 火葬 marker (the amount)
    // on the target BEFORE the damage, so a kill by this detonation is known to the death sink in the same frame.
    void Detonate(int k, float mult, int heat, float bonus, float blaze, bool mark)
    {
        const float amount = React(kFire, n3::kHeatBurst[std::clamp(heat, 0, 4)] * (1.0f + bonus) * blaze * mult * Signature(kFire), k);
        if (mark && Has(node::kFireCremation)) {
            On(k, [&](Board& b, const StatusInputs&) { Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kCremation, amount, 1.0f); });
        }
        Damage(k, kFire, amount);
    }

    // 放電 (2.6, 5.5): charges × 30% B_max (每格 +1%／點) × R × crit × mult × 放電 +3%／點; drain 50% of it (with G);
    // jumps to 2 nearest within 15 m ×40% (電弧 3 人 55%, 連鎖 5 人). `crit` is the multiplier already decided
    // (1 / 1.5 / 2.5). 天雷 (sync 3): every shocked target within 2 m + 0.2 m a point of you instead of the jumps.
    void Discharge(int k, int charges, float mult, float power, float crit, bool jumps)
    {
        if (charges <= 0) {
            return;
        }
        const float per = n5::kPerCharge * (1.0f + Pct(Rank(node::kLightningPerCharge), 0.01f));
        const float raw = BMax(kLightning) * per * static_cast<float>(charges) * mult * Signature(kLightning) * power * crit;
        HitDischarge(k, raw, 1.0f);
        if (!jumps) {
            return;
        }
        int count = n5::kJump;
        float share = n5::kJumpShare;
        if (Has(node::kLightningArc)) {
            count = n5::kArcJump;
            share = n5::kArcShare;
        }
        if (Has(node::kLightningChain)) {
            count = n5::kChainJump;
        }
        const Picked p = Around(c_, k, n5::kNear, count);
        for (int i = 0; i < p.n; ++i) {
            HitDischarge(p.k[i], raw, share);
        }
    }

    void HitDischarge(int k, float raw, float share)
    {
        const float amount = raw * share;
        Damage(k, kLightning, amount * ReactionScale(kLightning, T(), bin_.in->player, nodes_) *
                                  ReactionVulnerability(c_.m[k].board, self_, T(), nodes_));
        DrainMagicka(k, amount * n5::kDischargeDrain * TreeG(T(), TreeOf(kLightning)));
    }

    // The end's crit (value2 the draw, value3 a cutting power hit): ×2.5 on a cutting power hit that crits (a full-charge
    // one always does), ×1.5 otherwise; 疾電 adds 15% to the chance.
    float EndCrit(int charges, float draw, bool cutPower) const
    {
        bool crit = draw < LightningCritChance(charges) + (self_.Has(StatusKind::kQuickShock) ? n4::kQuickShock : 0.0f);
        if (cutPower && charges >= res::ChargeCap(nodes_)) {
            crit = true;
        }
        return crit ? (cutPower ? n4::kPowerCrit : 1.5f) : 1.0f;
    }

    // A discharge on member k with its crit multiplier already decided; 天雷 (sync 3) turns the jumps into every shocked
    // target within 2 m + 0.2 m a point of you (each a full discharge with its own crit roll).
    void DischargeAll(int k, int charges, float mult, float power, float critMult)
    {
        const int sky = Rank(node::kLightningSky);
        if (sky > 0 && T().syncStage >= 3) {
            // 天雷：同調三段時放電改為對範圍內所有感電目標（2 m + 0.2 m／點，以你為中心），不再跳躍。
            Discharge(k, charges, mult, power, critMult, false);
            const float radius = (n5::kAdventBase + n5::kAdventPerPoint * static_cast<float>(sky)) * n5::kMetre;
            const Picked p = Around(c_, kAroundYou, radius, n5::kNearLimit, [&](const Member& x) { return x.board.mark[kLightning].has; });
            for (int i = 0; i < p.n; ++i) {
                if (p.k[i] != k) {
                    Discharge(p.k[i], charges, mult, 1.0f, CritRoll(charges, false), false);
                }
            }
            return;
        }
        Discharge(k, charges, mult, power, critMult, true);
    }

    // 地震 (2.6, 5.6): 3 m (廣震 5 m) B_max ×1.5 (崩裂 ×2.0) earth damage and stamina B_max ×2 (+3%／點, with G); a
    // target the cut floors falls (ragdoll push in Papyrus, downed in the DLL), the rest are slowed 30% 3 s; 塵暴 -20%
    // attack 3 s.
    void Quake(int k, float mult, bool knock)
    {
        const float k1 = (Has(node::kEarthCollapse) ? n5::kCollapse : n5::kQuake) * mult * Signature(kEarth);
        const float stamina = BMax(kEarth) * n5::kQuakeStamina * (1.0f + n5::kQuakeStaminaPerPoint * static_cast<float>(Rank(node::kEarthQuakeStamina))) *
                              TreeG(T(), TreeOf(kEarth)) * mult;
        const bool dust = Has(node::kEarthDust);
        auto one = [&](int j) {
            Damage(j, kEarth, React(kEarth, k1, j));
            const bool floored = c_.m[j].body.stamina <= stamina * T().multDrain;
            DrainStamina(j, stamina);
            if (knock && floored && !c_.m[j].essential && !c_.m[j].dragon) {
                Event(j, MakeEvent(Event::kKnock, n5::kKnock));   // 倒地 is put by Papyrus Knockdown when the push lands
            } else {
                Slow(j, n5::kQuakeSlow, n5::kQuakeSlowSeconds);
            }
            if (dust) {
                Timed(j, timed::kMeleeDebuff, n5::kDust, n5::kDustSeconds);
            }
        };
        one(k);
        const Picked p = Around(c_, k, QuakeRadius(), n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            one(p.k[i]);
        }
    }

    // 風刃: B_max(風) ×1.0 × 風刃傷害 +2%／點 × mult on member k (+30% unbalanced); 迴旋: also 2 others within 15 m; 追風:
    // stamina +3 and unbalance; 空中追擊: an airborne target is pushed 1 m higher (Papyrus).
    void Blade(int k, float mult)
    {
        const float amount = BMax(kWind) * n5::kBlade * mult * (1.0f + Pct(Rank(node::kWindBladeDamage), n5::kBladePerPoint));
        BladeOne(k, amount);
        if (Has(node::kWindWhirl)) {
            const Picked p = Around(c_, k, n5::kNear, n5::kBladeNear);
            for (int i = 0; i < p.n; ++i) {
                BladeOne(p.k[i], amount);
            }
        }
    }

    void BladeOne(int k, float amount)
    {
        Member& m = c_.m[k];
        const float unbalanced = m.board.Has(StatusKind::kUnbalance) ? n5::kBladeUnbalanced : 1.0f;
        Damage(k, kWind, amount * unbalanced * ReactionScale(kWind, T(), bin_.in->player, nodes_) * ReactionVulnerability(m.board, self_, T(), nodes_));
        if (Has(node::kWindChase)) {
            Stamina(n5::kChaseStamina);
            On(k, [&](Board& b, const StatusInputs& in) {
                Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kUnbalance, 1.0f, Scaled(*in.tuning, n3::kUnbalance));
            });
        }
        if (Has(node::kWindAirChase) && m.board.Has(StatusKind::kAirborne)) {
            Event(k, PushOp(4, n5::kLift, LandingStored(), 0, false));
        }
    }

    float LandingStored() const
    {
        float k = n5::kLanding + Pct(Rank(node::kWindLanding), n5::kLandingPerPoint);
        if (Has(node::kWindSky)) {
            k += n5::kSkyLanding;   // 上天：落地 B_max ×1.0
        }
        return BMax(kWind) * k;   // G and the vulnerabilities at landing (Landing)
    }

    // 吹飛 (2.6): a blade on the target and on 2 others within 15 m (亂流 5); the target is blown back 3 m (上天: lifted, a
    // burst always lifts -- 2.5 吹上天); a target that cannot be pushed is slowed 30% 3 s (Papyrus).
    void WindEnd(int k, float mult, EndReason reason)
    {
        Blade(k, mult);
        const bool lift = reason == EndReason::kBurst || Has(node::kWindSky);
        Event(k, lift ? PushOp(4, n5::kLift, LandingStored(), 0, true) : PushOp(1, n5::kBlow, 0.0f, 0, true));
        const Picked p = Around(c_, k, n5::kNear, Has(node::kWindTurbulence) ? n5::kTurbulence : n5::kBladeNear);
        for (int i = 0; i < p.n; ++i) {
            Blade(p.k[i], mult);
        }
    }

    // 血潮 (2.6, 5.8): the bleed remaining (strength × seconds; the DoT already carries G and ESSB_MultDot) × the blood
    // hit curve, + the target's current health 10% (首領 3%; 放血終焉 ×2; ×ESSB_BaseDamageMult, no G -- like 碎冰 and
    // 聖裁 III), × 血潮 +3%／點; 飽飲 ×1.5 on the bleed part; 血契 at ≥70% health pays 10% and doubles; heal = that ×
    // the leech ratio × 2 (+0.1／點); 血斷 heals 50% on a burst; 血海 (sync 3): the bleeding within 1 m + 0.2 m a point
    // surge too.
    void Surge(int k, float remaining, float mult, EndReason reason, bool chain)
    {
        Member& m = c_.m[k];
        float surge = mult;
        if (Has(node::kBloodContract) && bin_.in->self.Fraction() >= n3::kZoneHigh) {
            plan_.Push(Amount(Op::kPayHealth, bin_.in->self.healthMax * n5::kPactCost));
            surge *= n5::kPactMult;
        }
        const float bleed = remaining * (Has(node::kBloodSated) ? n5::kSated : 1.0f) *
                            Interpolate(BloodCurveFraction(bin_.in->player, nodes_), kBloodHitCurve);
        float percent = m.body.vip ? n5::kSurgeHealthVip : n5::kSurgeHealth;
        if (Has(node::kBloodEndBleed)) {
            percent *= 2.0f;
        }
        const float health = m.body.health * percent * T().baseDamageMult;
        const float amount = (bleed + health) * surge * Signature(kBlood) * ReactionVulnerability(m.board, self_, T(), nodes_);
        Damage(k, kBlood, amount);
        HealLeech(amount * Leech() * (n5::kSurgeHeal + n5::kSurgeHealPerPoint * static_cast<float>(Rank(node::kBloodSurgeHeal))));
        (void)reason;
        const int sea = Rank(node::kBloodSea);
        if (sea > 0 && T().syncStage >= 3 && !chain) {
            const float radius = (n5::kRangeBase + n5::kAdventPerPoint * static_cast<float>(sea)) * n5::kMetre;
            const Picked p = Around(c_, k, radius, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kBleed); });
            for (int i = 0; i < p.n; ++i) {
                SurgeOn(p.k[i], mult, true);
            }
        }
    }

    // A surge on another bleeding target (血海, 血漫, 血祭之始, 濺血): its own bleed remaining; `clear` takes the bleed off.
    void SurgeOn(int k, float mult, bool clear)
    {
        Member& m = c_.m[k];
        const float remaining = m.board.bleedDot.magnitude * m.board.bleedDot.Remaining();
        if (clear) {
            On(k, [&](Board& b, const StatusInputs&) {
                if (b.bleedDot.has) {
                    plan_.Push(Amount(Op::kBleedDot, 0.0f, 0, 0.0f));
                    b.bleedDot = Slot{};
                }
                Writer{ plan_, b, Who::kTarget }.Clear(StatusKind::kBleed);
            });
        }
        Surge(k, remaining, mult, EndReason::kExpire, true);
    }

    // 裁決 (2.6, 5.9): B_max ×2.0 (重裁 ×3.0) × 裁決 +3%／點 × (1 + 聖印 20% [+ 聖痕 10%]) × (1 + 聖佑階的聖傷加成) × mult,
    // ×3 on the undead (聖痕: a divine-marked target counts), heals you B_max; 懲戒 +20% a layer, used up (天誅: the bonus
    // part also on 3 m others); 天啟 (sync 3: 1 m + 0.2 m a point) / 廣裁 (3 m) spread it; 光耀: the undead within 3 m
    // take +20% holy for 5 s.
    void JudgeArea(int k, float mult, int holy)
    {
        const int punish = self_.Layers(StatusKind::kPunish);
        if (punish > 0) {
            Writer{ plan_, self_, Who::kPlayer }.Clear(StatusKind::kPunish);
        }
        const float bonus = n3::kPunishPerLayer * static_cast<float>(punish);
        Judge(k, mult * (1.0f + bonus), holy);
        if (punish > 0 && Has(node::kDivineHeaven)) {
            const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit);
            for (int i = 0; i < p.n; ++i) {
                Judge(p.k[i], mult * bonus, holy, false);   // the punishment's bonus part only
            }
        }
        const int apocalypse = Rank(node::kDivineApocalypse);
        const bool wide = Has(node::kDivineWideJudge);
        float radius = 0.0f;
        if (apocalypse > 0 && T().syncStage >= 3) {
            radius = std::max((n5::kRangeBase + n5::kAdventPerPoint * static_cast<float>(apocalypse)) * n5::kMetre, wide ? n5::kArea : 0.0f);
        } else if (wide) {
            radius = n5::kArea;
        }
        if (radius > 0.0f) {
            const Picked p = Around(c_, k, radius, n5::kNearLimit);
            for (int i = 0; i < p.n; ++i) {
                Judge(p.k[i], mult * (1.0f + bonus), holy);
            }
        }
        if (Has(node::kDivineRadiance)) {
            auto mark = [&](int j) {
                On(j, [&](Board& b, const StatusInputs& in) {
                    Writer{ plan_, b, Who::kTarget }.Set(StatusKind::kRadiance, 1.0f, Scaled(*in.tuning, n5::kRadianceSeconds));
                });
            };
            if (c_.m[k].body.undeadOrDaedra) {
                mark(k);
            }
            const Picked p = Around(c_, k, n5::kArea, n5::kCrowdMax, [](const Member& x) { return x.body.undeadOrDaedra; });
            for (int i = 0; i < p.n; ++i) {
                mark(p.k[i]);
            }
        }
    }

    void Judge(int k, float mult, int holy, bool heal = true)
    {
        const Member& m = c_.m[k];
        float vulnerability = 1.0f;
        if (m.board.mark[kDivine].has) {
            vulnerability += n3::kHolyMark;
            if (Has(node::kDivineStigma) && !m.body.undeadOrDaedra) {
                vulnerability += n3::kStigma;
            }
        }
        const float tier = n3::kHolyProc[std::clamp(holy, 0, 3)] + Pct(Rank(node::kDivineHolyBonus), 0.01f) * static_cast<float>(holy);
        float amount = React(kDivine, (Has(node::kDivineHeavyJudge) ? n5::kHeavyJudge : n5::kJudge) * mult * Signature(kDivine) *
                                          vulnerability * (1.0f + tier), k);
        const bool prey = m.body.undeadOrDaedra || (Has(node::kDivineStigma) && m.board.mark[kDivine].has);
        if (prey) {
            amount *= n3::kPrey;
        }
        Damage(k, kDivine, amount);
        if (heal) {
            Heal(BMax(kDivine) * n5::kJudgeHeal);
        }
    }

    // 冰崩／冰河：範圍內所有冰封目標碎冰（各吃自己的冰晶）；碎冰事件標來源 3，不再往外擴。
    void ShatterArea(int k)
    {
        const Picked p = Around(c_, k, n5::kArea, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kFrozen); });
        for (int i = 0; i < p.n; ++i) {
            On(p.k[i], [&](Board& b, const StatusInputs& in) { rule::Shatter(plan_, b, in, nodes_, 3); });
        }
    }

    // A chain end on member j (連鎖終焉、大協奏、焚天、過熱): the mark goes; outside its 1 s end cooldown the end runs with
    // chain = 1 (no node multipliers, no further chains).
    void ChainEndOn(int j, int element, float mult)
    {
        On(j, [&](Board& b, const StatusInputs& in) {
            if (!b.mark[element].has) {
                return;
            }
            Writer{ plan_, b, Who::kTarget }.Unmark(element);
            if (!b.Has(StatusKind::kEndCooldown)) {
                PlanEndBody(plan_, element, EndReason::kExpire, mult, false, b, self_, in, nodes_, rng_, true);
            }
        });
    }

    // "開印時附近 1 人也 X": the nearest one within 15 m that can take the mark without a cut (no other mark, or 雙印
    // with room) and does not carry it yet (decision: the mark alone, no open, never cutting another mark); `extra` puts
    // the element's status on it too.
    template <class Extra, class Keep>
    void SpreadMark(int k, int element, Extra&& extra, Keep&& keep)
    {
        const bool dual = Has(node::kCommonDualMark);
        const Picked p = Around(c_, k, n5::kNear, 1, [&](const Member& x) {
            if (!keep(x)) {
                return false;
            }
            if (element == 0) {
                return true;
            }
            const int others = x.board.MarkCount() - (x.board.mark[element].has ? 1 : 0);
            return !x.board.mark[element].has && (others == 0 || (dual && others < 2));
        });
        for (int i = 0; i < p.n; ++i) {
            if (element != 0) {
                On(p.k[i], [&](Board& b, const StatusInputs& in) {
                    Writer{ plan_, b, Who::kTarget }.Mark(element, rule::MarkSeconds(element, *in.tuning, nodes_, false));
                });
            }
            extra(p.k[i]);
        }
    }

    template <class Extra>
    void SpreadMark(int k, int element, Extra&& extra)
    {
        SpreadMark(k, element, extra, [](const Member&) { return true; });
    }

    void SpreadMark(int k, int element)
    {
        SpreadMark(k, element, [](int) {}, [](const Member&) { return true; });
    }

    StatusPlan& plan_;
    Crowd& c_;
    Board& self_;
    const BodyInputs& bin_;
    const Nodes& nodes_;
    Rng& rng_;
};

// ================================================================ the body pass

// The events the body pass owns (never sent to Papyrus; Plugin.cpp refuses them).
constexpr bool BodyOnly(Event e) noexcept
{
    return e == Event::kFrozen || e == Event::kJudgment || e == Event::kSplash || e == Event::kRise || e == Event::kShatter ||
           e == Event::kLanding || e == Event::kDischarge || e == Event::kBlade || e == Event::kOverheat;
}

// Walks plan.ops[from..] (the list grows as bodies push) and runs each body once. Returns the body events handled;
// plan.overflow is set if more than kMaxBodies were waiting (the rest are left as no-ops).
template <NodeReader Nodes, RandomSource Rng>
int RunBodies(StatusPlan& plan, int from, Crowd& crowd, Board& self, const BodyInputs& bin, const Nodes& nodes, Rng& rng)
{
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    int handled = 0;
    for (int i = from; i < plan.count; ++i) {
        const StatusOp op = plan.ops[i];
        const int k = op.at;
        if (k >= crowd.count) {
            continue;
        }
        const bool present = crowd.m[k].has;
        auto consume = [&]() { plan.ops[i].op = Op::kNoop; };
        switch (op.op) {
        case Op::kEvent:
            if (handled >= n5::kMaxBodies) {
                if (BodyOnly(op.event)) {
                    consume();   // bounded: the bodies beyond kMaxBodies are dropped (the Papyrus events still go)
                }
                continue;
            }
            switch (op.event) {
            case Event::kOpen:
                if (present) {
                    b.Open(k, static_cast<int>(op.arg[0] + 0.5f), op.arg[1], static_cast<int>(op.arg[2] + 0.5f), op.arg[3] > 0.5f);
                }
                ++handled;
                break;   // the event stays: Papyrus gives the open's experience
            case Event::kEnd:
                if (present) {
                    b.End(k, static_cast<int>(op.arg[0] + 0.5f), static_cast<EndReason>(static_cast<int>(op.arg[1] + 0.5f)), op.arg[2],
                        static_cast<int>(op.arg[3] + 0.5f), op.arg[4], op.arg[5], op.arg[6], static_cast<int>(op.arg[7] + 0.5f));
                }
                ++handled;
                break;   // the event stays: Papyrus gives the end's experience and places the end's explosion
            case Event::kFrozen:
                if (present) {
                    b.Frozen(k, op.arg[0]);
                }
                consume();
                ++handled;
                break;
            case Event::kHallucinate:
                if (present && op.arg[2] < 0.5f) {
                    b.Hallucinate(k, static_cast<int>(op.arg[0] + 0.5f));
                }
                ++handled;
                break;   // the event stays: Papyrus casts the fear / frenzy (or 幻視)
            case Event::kJudgment:
                if (present) {
                    b.Judgment(k, static_cast<int>(op.arg[0] + 0.5f), op.arg[1]);
                }
                consume();
                ++handled;
                break;
            case Event::kSplash:
                b.Splash();
                consume();
                ++handled;
                break;
            case Event::kRise:
                b.Rise();
                consume();
                ++handled;
                break;
            case Event::kShatter:
                if (present) {
                    b.Shattered(k, static_cast<int>(op.arg[0] + 0.5f));
                }
                consume();
                ++handled;
                break;
            case Event::kLanding:
                if (present) {
                    b.Landing(k, op.arg[0]);
                }
                consume();
                ++handled;
                break;
            case Event::kDischarge:
                if (present) {
                    // arg3 = the crit multiplier the DLL decided (滿格重擊 ×2.5; 雷暴／雷神／雷霆／餘電 rolled)
                    b.DischargeAll(k, static_cast<int>(op.arg[0] + 0.5f), op.arg[1], op.arg[2], op.arg[3] > 0.0f ? op.arg[3] : 1.0f);
                }
                consume();
                ++handled;
                break;
            case Event::kBlade:
                if (present) {
                    for (int n = static_cast<int>(op.arg[0] + 0.5f); n > 0; --n) {
                        b.Blade(k, op.arg[1]);
                    }
                }
                consume();
                ++handled;
                break;
            case Event::kOverheat:
                b.Overheat();
                consume();
                ++handled;
                break;
            default:
                break;
            }
            break;
        case Op::kResonance: {
            // 共鳴層 (2.3, 5.13): the detonator and the other resonance targets within 15 m of it (at most 8).
            int count = 1;
            if (present) {
                count += Around(crowd, k, n4::kResonanceRadius, n4::kResonanceCount,
                    [](const Member& x) { return x.board.Has(StatusKind::kStar); }).n;
            }
            OnResonance(plan, self, count, *bin.in, nodes);
            consume();
            break;
        }
        case Op::kDamage:
            if (op.element == kAstral && op.arg[0] == tag::kStarBurst && present && nodes.Has(node::kAstralGather)) {
                // 聚星：引爆當下 15 公尺內共鳴目標 ≥3（含引爆者），這次引爆 +30%。
                const int others = Around(crowd, k, n4::kResonanceRadius, n5::kCrowdMax,
                    [](const Member& x) { return x.board.Has(StatusKind::kStar); }).n;
                if (1 + others >= n5::kGatherCount) {
                    plan.ops[i].magnitude *= n5::kGatherBonus;
                }
            }
            if (op.element == kAstral && op.arg[0] == tag::kDarkStrike && present && nodes.Has(node::kAstralEclipse)) {
                // 星蝕：闇星中每一擊的傷害，另以 50% 回聲到所有其他共鳴目標（最多 5）。
                const Picked p = Around(crowd, k, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kStar); });
                for (int j = 0; j < p.n; ++j) {
                    b.Damage(p.k[j], kAstral, op.magnitude * n5::kEclipse);
                }
            }
            break;
        case Op::kCrushArea:
            if (present) {
                // 碎岩 (5.6): up to 5 more within 3 m take the earth damage and the stamina cut; a floored one falls.
                const Picked p = Around(crowd, k, n4::kCrushRadius, n4::kCrushTargets);
                for (int j = 0; j < p.n; ++j) {
                    const int t = p.k[j];
                    const bool floored = crowd.m[t].body.stamina <= op.seconds;
                    b.Damage(t, kEarth, op.magnitude * ReactionVulnerability(crowd.m[t].board, self, *bin.in->tuning, nodes));
                    b.Push(t, Amount(Op::kDrainStamina, op.seconds));
                    if (floored && !crowd.m[t].essential && !crowd.m[t].dragon) {
                        b.Event(t, MakeEvent(Event::kKnock, n4::kKnockForce));
                    }
                }
            }
            consume();
            break;
        case Op::kFreezeNearby: {
            // 冰心 (5.4): every hostile within 15 m of you whose freeze gauge is at least 1 freezes now.
            const Picked p = Around(crowd, kAroundYou, n4::kIceHeartRadius, n5::kNearLimit,
                [](const Member& x) { return x.board.Layers(StatusKind::kFreeze) >= 1 && !x.board.Has(StatusKind::kFrozen); });
            for (int j = 0; j < p.n; ++j) {
                b.On(p.k[j], [&](Board& bb, const StatusInputs& in) {
                    rule::Freeze(plan, bb, rule::FrozenSeconds(*in.tuning, nodes), 1.0f, nodes);
                });
            }
            consume();
            break;
        }
        default:
            break;
        }
    }
    return handled;
}

// ================================================================ the element hit's own branch bodies

// After an accepted element hit (on the boards the hit left): 震擊 (5.6: a power hit on a fissured target -- one ×1.5
// quake blast on it, stamina -50, the fissure used), 護持 (5.9: +10% magic resist 3 s), 萎靡 (5.10: ≥5 doses -- attack
// -15% 3 s), 侵蝕 (5.10: 10 doses -- poison resist -20% 6 s), 詛咒的抗性侵蝕 (5.12: every layer -2% (+0.2%／點) × 萬象 on
// the four element resists and magic resist, the curse's 8 s). `silence` is the no-form hit's silence (封印: the same
// silence on every hostile within 3 m).
template <NodeReader Nodes, RandomSource Rng>
void PlanHitBodies(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, int element, bool power, int silence,
    const Nodes& nodes, Rng& rng)
{
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    if (!crowd.m[0].has) {
        return;
    }
    const Board& target = crowd.m[0].board;
    const Tuning& t = *bin.in->tuning;
    switch (element) {
    case kEarth:
        if (power && nodes.Has(node::kEarthQuakeStrike) && target.Has(StatusKind::kFissure)) {
            b.Damage(0, kEarth, b.React(kEarth, n5::kQuakeStrike, 0));
            b.DrainStamina(0, n5::kQuakeStrikeStamina);
            b.On(0, [&](Board& bb, const StatusInputs&) { Writer{ plan, bb, Who::kTarget }.Clear(StatusKind::kFissure); });
        }
        break;
    case kDivine:
        if (nodes.Has(node::kDivineGuard)) {
            b.Timed(0, timed::kMagicResistBuff, n5::kGuardMR, n5::kGuardSeconds);
        }
        break;
    case kPoison: {
        const int doses = Doses(target, PerDose(*bin.in->config, t, nodes));
        if (doses >= n3::kMiasmaDoses && nodes.Has(node::kPoisonWither)) {
            b.Timed(0, timed::kMeleeDebuff, n5::kWither, n5::kWitherSeconds);
        }
        if (doses >= n3::kDoseCap && nodes.Has(node::kPoisonErode)) {
            b.Timed(0, timed::kPoisonResistDebuff, n5::kErode, n5::kErodeSeconds);
        }
        break;
    }
    case kDarkness: {
        const int curse = target.Layers(StatusKind::kCurse);
        if (curse > 0) {
            const float amount = static_cast<float>(curse) *
                                 (n5::kErosionPerLayer + n5::kErosionPerPoint * static_cast<float>(nodes.Rank(node::kDarkErosion))) * Omni(nodes);
            for (const int kind : { timed::kFireResistDebuff, timed::kFrostResistDebuff, timed::kShockResistDebuff, timed::kMagicResistDebuff,
                     timed::kPoisonResistDebuff }) {
                b.Timed(0, kind, amount, n5::kErosionSeconds);
            }
        }
        break;
    }
    default:
        break;
    }
    if (silence > 0 && nodes.Has(node::kNoFormSeal)) {
        const Picked p = Around(crowd, 0, n5::kArea, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            StatusOp op = Amount(Op::kSilence, 0.0f, 0, static_cast<float>(silence));
            b.Push(p.k[i], op);
        }
    }
}

// ================================================================ echo (5.13 回聲, 星鏈)

// A star hit on a target that carried star marks before the hit (outside the dark star): the other resonance targets
// within 15 m (5, nearest) take this hit's star proc × 25% (+1%／點, not node-scaled; night ×1.5) as star damage; no
// stars, no re-timing, no open. 星鏈: each of them +1 star (not re-timed), once every 2 s per target.
template <NodeReader Nodes>
void PlanEcho(StatusPlan& plan, Crowd& crowd, int k, float procDamage, const StatusInputs& in, const Nodes& nodes)
{
    const Tuning& t = *in.tuning;
    float ratio = n5::kEcho + n5::kEchoPerPoint * static_cast<float>(nodes.Rank(node::kAstralEcho));
    if (t.envNight && !in.player.interior) {
        ratio *= n5::kEchoNight;
    }
    const Picked p = Around(crowd, k, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.board.Has(StatusKind::kStar); });
    for (int i = 0; i < p.n; ++i) {
        const int j = p.k[i];
        StatusOp hit = Amount(Op::kDamage, procDamage * ratio, kAstral);
        hit.at = static_cast<std::uint8_t>(j);
        plan.Push(hit);
        Board& b = crowd.m[j].board;
        if (nodes.Has(node::kAstralChain) && !b.Has(StatusKind::kStarChainCooldown)) {
            const Writer w{ plan, b, Who::kTarget, static_cast<std::uint8_t>(j) };
            const int layers = std::min(StarCap(nodes), b.Layers(StatusKind::kStar) + 1);
            w.Set(StatusKind::kStar, static_cast<float>(layers), b[StatusKind::kStar].Remaining());   // not re-timed: the fuse stays
            w.Set(StatusKind::kStarChainCooldown, 1.0f, CooldownOf(t, 2.0f));
        }
    }
}

// ================================================================ 融斷 (2.5)

// Magicka to you, whatever goes over the max into 超載 (5.1: 回流, 無魔 "可以灌進超載").
template <NodeReader Nodes>
constexpr void GiveMagicka(StatusPlan& plan, Board& self, float amount, const BodyInputs& bin, const Nodes& nodes)
{
    const float room = std::max(0.0f, bin.magickaMax - bin.magicka);
    const float into = std::min(amount, room);
    if (into > 0.0f) {
        plan.Push(Amount(Op::kRestoreMagicka, into));
    }
    const float over = amount - into;
    if (over > 0.0f) {
        const float pool = self.Has(StatusKind::kOverload) ? self[StatusKind::kOverload].magnitude : 0.0f;
        res::SetOverload(plan, self, std::min(pool + over, res::OverloadCap(bin.magickaMax, nodes)), true, *bin.in, nodes);
    }
}


struct BurstResult {
    int targets = 0;   // members settled
    int marks = 0;     // marks settled (回流)
};

template <NodeReader Nodes>
constexpr float BurstRadius(const Nodes& nodes)
{
    return (nodes.Has(node::kNoFormGather) ? n5::kGather : n5::kBurst) + n5::kBurstPerPoint * static_cast<float>(nodes.Rank(node::kNoFormBurstRadius));
}

// K_sync × the common closing 融斷 lines (+1%／點, 再 +2%／點) × the no-form 冷寂 lines (+2%／點, 再 +3%／點).
template <NodeReader Nodes>
constexpr float BurstMult(int stage, const Tuning& t, const Nodes& nodes)
{
    const float common = 1.0f + Pct(t, nodes.Rank(node::kCommonBurst), 0.01f) + Pct(t, nodes.Rank(node::kCommonBurstAgain), 0.02f);
    const float quiet = 1.0f + Pct(t, nodes.Rank(node::kNoFormBurst), 0.02f) + Pct(t, nodes.Rank(node::kNoFormBurstAgain), 0.03f);
    return n5::kSync[std::clamp(stage, 0, 3)] * common * quiet;
}

// The state part of the burst on every member within the radius of you, then the bodies. `formElement` is the form
// being closed.
template <NodeReader Nodes, RandomSource Rng>
BurstResult PlanBurst(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, int stage, int formElement, const Nodes& nodes,
    Rng& rng)
{
    const StatusInputs& base = *bin.in;
    const Tuning& t = *base.tuning;
    const Config& c = *base.config;
    BurstResult out;
    const float radius = BurstRadius(nodes);
    const float mult = BurstMult(stage, t, nodes);
    const int start = plan.count;
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    const int hushCap = n5::kHushCap + std::min(3, nodes.Rank(node::kNoFormHushCap) / 5);
    const float burn = n5::kHushBurn + n5::kHushBurnPerPoint * static_cast<float>(nodes.Rank(node::kNoFormHushBurn));
    std::array<bool, 12> settledElement{};
    float backflow = 0.0f;
    bool earthSettled = false;
    // Read before the marks go: 墜星 shares among the star-marked, 颶風 lifts the ones the wind end does not.
    const Picked stars = Around(crowd, kAroundYou, radius, n5::kCrowdMax, [](const Member& x) { return x.board.mark[kAstral].has; });
    std::array<bool, kCrowdSlots> windMarked{};
    for (int k = 0; k < crowd.count; ++k) {
        windMarked[k] = crowd.m[k].board.mark[kWind].has;
    }
    const Picked p = Around(crowd, kAroundYou, radius, n5::kCrowdMax,
        [](const Member& x) { return x.board.MarkCount() > 0 || x.board.Has(StatusKind::kResidual); });
    for (int i = 0; i < p.n; ++i) {
        const int k = p.k[i];
        int settled = 0;
        b.On(k, [&](Board& target, const StatusInputs& in) {
            // One end-cooldown check for the whole burst of this target: inside it the marks just go.
            const bool allowed = !target.Has(StatusKind::kEndCooldown);
            const Writer tw{ plan, target, Who::kTarget };
            auto settle = [&](int e) {
                if (allowed) {
                    // The end's state part as for any end (×1: K_sync and the burst lines go to the fusion hit only); its
                    // event carries K (× the guide the state part took off) for the body pass.
                    const int from = plan.count;
                    PlanEndBody(plan, e, EndReason::kBurst, 1.0f, false, target, self, in, nodes, rng);
                    for (int i = from; i < plan.count; ++i) {
                        if (plan.ops[i].op == Op::kEvent && plan.ops[i].event == Event::kEnd && static_cast<int>(plan.ops[i].arg[0] + 0.5f) == e) {
                            plan.ops[i].arg[2] *= mult;
                        }
                    }
                    ++settled;
                    settledElement[e] = true;
                    backflow += c.damage[e][1] * n5::kBackflow;
                    earthSettled = earthSettled || e == kEarth;
                }
            };
            for (int e = kFire; e <= kAstral; ++e) {
                if (target.mark[e].has) {
                    tw.Unmark(e);
                    settle(e);
                }
            }
            if (target.Has(StatusKind::kResidual)) {
                const int residual = target.Layers(StatusKind::kResidual);
                tw.Clear(StatusKind::kResidual);
                if (IsElement(residual)) {
                    settle(residual);
                }
            }
        });
        ++out.targets;
        out.marks += settled;
        if (settled > 0) {
            // 冷寂 (5.1): +1 寂 per element settled (cap 5, 寂上限 +1 every 5 points → 8), 10 s; each new layer burns 5%
            // (+0.5%／點) of its max magicka now.
            Member& m = crowd.m[k];
            const int before = m.board.hush.Layers();
            int layers = std::min(hushCap, before + settled);
            const int gained = layers - before;
            if (gained > 0 && m.magickaMax > 0.0f) {
                b.DrainMagicka(k, m.magickaMax * burn * static_cast<float>(gained));
            }
            if (nodes.Has(node::kNoFormAllHush) && layers >= n5::kAllHush) {
                // 萬寂：寂 ≥3 層的目標身上其他元素狀態全部清除，每清一種寂 +1，並轉為「該元素 B_max ×0.5」真實傷害。
                int cleared = 0;
                b.On(k, [&](Board& target, const StatusInputs&) {
                    const Writer w{ plan, target, Who::kTarget };
                    auto take = [&](bool has, int element, auto&& clear) {
                        if (!has) {
                            return;
                        }
                        clear();
                        ++cleared;
                        StatusOp hit = Amount(Op::kDamage, c.damage[element][1] * n5::kAllHushTrue * TreeG(t, kNoFormTree) *
                                                               t.baseDamageMult, 0);
                        plan.Push(hit);
                    };
                    take(target.Has(StatusKind::kFreeze) || target.Has(StatusKind::kFrozen) || target.Has(StatusKind::kCrystal), kFrost, [&]() {
                        w.Clear(StatusKind::kFreeze);
                        w.Clear(StatusKind::kFrozen);
                        w.Clear(StatusKind::kCrystal);
                    });
                    take(target.Has(StatusKind::kCurse), kDarkness, [&]() { w.Clear(StatusKind::kCurse); });
                    take(target.Has(StatusKind::kBleed) || target.bleedDot.has, kBlood, [&]() {
                        w.Clear(StatusKind::kBleed);
                        if (target.bleedDot.has) {
                            plan.Push(Amount(Op::kBleedDot, 0.0f, 0, 0.0f));
                            target.bleedDot = Slot{};
                        }
                    });
                    take(target.poisonDot.has, kPoison, [&]() {
                        plan.Push(Amount(Op::kPoisonDot, 0.0f, 0, 0.0f));
                        target.poisonDot = Slot{};
                        w.Clear(StatusKind::kCatalyzed);
                    });
                    take(target.Has(StatusKind::kPressure) || target.Has(StatusKind::kSoak), kWater, [&]() {
                        w.Clear(StatusKind::kPressure);
                        w.Clear(StatusKind::kSoak);
                    });
                    take(target.Has(StatusKind::kStar), kAstral, [&]() {
                        w.Clear(StatusKind::kStar);
                        w.Clear(StatusKind::kStarFuse);
                    });
                    take(target.Has(StatusKind::kFissure) || target.Has(StatusKind::kDowned), kEarth, [&]() {
                        w.Clear(StatusKind::kFissure);
                        w.Clear(StatusKind::kDowned);
                    });
                    take(target.Has(StatusKind::kUnbalance), kWind, [&]() { w.Clear(StatusKind::kUnbalance); });
                });
                layers = std::min(hushCap, layers + cleared);
            }
            b.On(k, [&](Board& target, const StatusInputs&) {
                StatusOp hush = Amount(Op::kHush, static_cast<float>(layers));
                plan.Push(hush);
                target.hush = Slot{ true, static_cast<float>(layers), 0.0f, 10.0f };
            });
        }
    }
    // 墜星 (5.13): at a burst in the dark star, the 闇宙 left are shared evenly among the star-marked targets in range,
    // each layer a ×0.5 dark-star strike.
    const int cosmos = self.Layers(StatusKind::kCosmos);
    if (cosmos > 0 && nodes.Has(node::kAstralFalling)) {
        for (int i = 0; i < stars.n; ++i) {
            const int k = stars.k[i];
            const StatusInputs in = b.InFor(k);
            const float share = static_cast<float>(cosmos) / static_cast<float>(stars.n);
            b.Damage(k, kAstral, share * n5::kFallingStar * res::DarkStrike(false, crowd.m[k].board, self, in, nodes));
        }
    }
    // 斷界 (5.1): every enemy in range takes the weakening of every element this burst settled, 3 s (decision: the
    // matching resist -10%: fire / frost / shock / poison resist, magic resist for the others).
    if (nodes.Has(node::kNoFormSever)) {
        const Picked all = Around(crowd, kAroundYou, radius, n5::kCrowdMax);
        for (int i = 0; i < all.n; ++i) {
            std::array<bool, kTimedKinds> done{};
            for (int e = kFire; e <= kAstral; ++e) {
                if (!settledElement[e]) {
                    continue;
                }
                const int kind = e == kFire ? timed::kFireResistDebuff : e == kFrost ? timed::kFrostResistDebuff :
                                 e == kLightning ? timed::kShockResistDebuff : e == kPoison ? timed::kPoisonResistDebuff :
                                                                              timed::kMagicResistDebuff;
                if (!done[kind]) {
                    done[kind] = true;
                    b.Timed(all.k[i], kind, n5::kSever, n5::kSeverSeconds);
                }
            }
        }
    }
    // 地斷 (5.6): an earth burst knocks down every enemy in range whose stamina is below 30% (and downs it).
    if (earthSettled && nodes.Has(node::kEarthSever)) {
        const Picked low = Around(crowd, kAroundYou, radius, n5::kCrowdMax, [](const Member& x) {
            return x.body.staminaMax > 0.0f && x.body.stamina / x.body.staminaMax < n5::kEarthSever && !x.essential && !x.dragon;
        });
        for (int i = 0; i < low.n; ++i) {
            b.Event(low.k[i], MakeEvent(Event::kKnock, n5::kKnock));   // Papyrus Knockdown puts 倒地 when it lands
        }
    }
    // 颶風 (5.7): the burst's lift reaches every enemy in range, not only the wind-marked.
    if (nodes.Has(node::kWindHurricane)) {
        const Picked all = Around(crowd, kAroundYou, radius, n5::kNearLimit);
        for (int i = 0; i < all.n; ++i) {
            if (!windMarked[all.k[i]]) {
                b.Event(all.k[i], PushOp(4, n5::kLift, b.LandingStored(), 0, true));
            }
        }
    }
    const Writer pw{ plan, self, Who::kPlayer };
    // 回流 (5.1): B_max ×0.5 of each settled mark's element as magicka, the overflow into 超載.
    if (nodes.Has(node::kNoFormBackflow) && backflow > 0.0f) {
        GiveMagicka(plan, self, backflow * t.multRecovery, bin, nodes);
    }
    if (nodes.Has(node::kNoFormDoubleBurst)) {
        pw.Set(StatusKind::kDoubleBurst, 1.0f, Scaled(t, n5::kDoubleBurst));   // 雙斷
    }
    if (nodes.Has(node::kCommonSafety)) {
        pw.Set(StatusKind::kSafetyValve, 1.0f, Scaled(t, n5::kSafety));   // 安全閥：融斷時你受傷 -50% 2 秒
    }
    RunBodies(plan, start, crowd, self, bin, nodes, rng);
    (void)formElement;
    return out;
}

// ================================================================ death (2.6, 2.7, 5.x)

// What the death sink knows besides the corpse's board (crowd member 0) and yours.
struct DeathFacts {
    bool killerYou = false;       // the killer is you (your weapon, your spells and reactions)
    bool killerFrenzied = false;  // the killer is an NPC under your frenzy (狂宴)
    bool servant = false;         // the corpse is your raised servant (our reanimate effect: 亡衛)
    int curseCap = 5;             // your curse cap now (滿層 doubles the servant's time)
};

struct Raise {
    bool raise = false;
    int tier = 0;
    int levelCap = 0;
    float seconds = 0.0f;
    float attack = 0.0f;
    bool permanent = false;
};

// 亡者歸來 (2.6, 5.12): tier by level (≤6 / 13 / 21 / 30 / 60), 5+ curse layers tier +1 (max 5) and +10% attack a layer,
// the full cap doubles the time; 殘魂 25% at 1-2 layers, 冥召 always (tier +1), 死靈主 (sync 3) no threshold, any level,
// permanent (六階).
constexpr std::array<int, 6> kTierCap{ 6, 13, 21, 30, 60, 999 };
constexpr std::array<float, 6> kTierSeconds{ 120.0f, 120.0f, 120.0f, 180.0f, 180.0f, 86313600.0f };

template <NodeReader Nodes, RandomSource Rng>
Raise JudgeRaise(const Member& corpse, const DeathFacts& f, const Tuning& t, const Nodes& nodes, Rng& rng)
{
    Raise out;
    const Board& b = corpse.board;
    const bool curseKill = b.Has(StatusKind::kCurseKill);
    const bool summon = curseKill && nodes.Has(node::kDarkSummon);                 // 冥召
    const bool lord = nodes.Has(node::kDarkLord) && t.syncStage >= 3;             // 死靈主
    const bool marked = b.mark[kDarkness].has || b.Has(StatusKind::kNether) || (f.killerFrenzied && nodes.Has(node::kDarkFeast));
    if ((!marked && !summon) || corpse.essential || corpse.dragon || f.servant) {
        return out;
    }
    const int curse = b.Layers(StatusKind::kCurse);
    bool ok = curse >= 3 || summon || lord;
    if (!ok && curse >= 1 && nodes.Has(node::kDarkRemnant)) {
        ok = rng.Chance(n5::kRemnant);   // 殘魂
    }
    if (!ok) {
        return out;
    }
    int tier = corpse.level <= 6 ? 1 : corpse.level <= 13 ? 2 : corpse.level <= 21 ? 3 : corpse.level <= 30 ? 4 : corpse.level <= 60 ? 5 : 6;
    if (tier == 6 && !lord) {
        return out;   // 60 級以上只有死靈主能復生
    }
    if (tier <= 5) {
        if (curse >= 5) {
            tier = std::min(5, tier + 1);
            out.attack = n5::kServantAttack * static_cast<float>(curse);
        }
        if (summon) {
            tier = std::min(5, tier + 1);
        }
    }
    out.raise = true;
    out.permanent = lord;
    out.tier = lord ? 6 : tier;
    out.levelCap = kTierCap[out.tier - 1];
    out.seconds = lord ? kTierSeconds[5] : kTierSeconds[tier - 1] * (curse >= f.curseCap ? 2.0f : 1.0f);
    return out;
}

template <NodeReader Nodes, RandomSource Rng>
void PlanDeath(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, const DeathFacts& f, const Nodes& nodes, Rng& rng)
{
    const StatusInputs& base = *bin.in;
    const Tuning& t = *base.tuning;
    const Config& c = *base.config;
    const int start = plan.count;
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    Member& corpse = crowd.m[0];
    const Board& cb = corpse.board;
    const Writer pw{ plan, self, Who::kPlayer };
    const bool bleeding = cb.Has(StatusKind::kBleed) || cb.bleedDot.has;

    // 化灰 (2.6, 5.9): the divine mark (or 淨土: sync 3, your kill in the divine form) -- ash first, no raise.
    const bool pureLand = nodes.Has(node::kDivinePureLand) && t.syncStage >= 3 && f.killerYou && base.formElement == kDivine;
    const bool ash = (cb.mark[kDivine].has || pureLand) && !corpse.essential && !corpse.dragon && !f.servant;
    if (ash) {
        plan.Push(MakeEvent(Event::kAsh));
        if (nodes.Has(node::kDivineAsh)) {
            b.Magicka(c.damage[kDivine][1] * n5::kAshMagicka);   // 聖灰
        }
        if (nodes.Has(node::kDivinePureAsh) && corpse.body.undeadOrDaedra && cb.mark[kDivine].has) {
            const Picked p = Around(crowd, 0, n5::kNear, n5::kNearLimit, [](const Member& x) { return x.body.undeadOrDaedra; });
            for (int i = 0; i < p.n; ++i) {
                b.Damage(p.k[i], kDivine, b.React(kDivine, n5::kPureAsh, p.k[i]));   // 淨灰
            }
        }
    } else {
        const Raise r = JudgeRaise(corpse, f, t, nodes, rng);
        if (r.raise) {
            plan.Push(MakeEvent(Event::kRaise, r.tier, r.levelCap, r.seconds, r.attack, r.permanent ? 1 : 0));
        }
    }
    // 中毒死亡擴散 (2.7, 5.10): S = max(R, max health × 30%) × 50% (蔓延 75%) to every eligible enemy within 15 m (no 5
    // cap): m' = min(m + S/12, 10 doses), d' = max(d - t, 12); S/12 above the cap lengthens the time to S / cap instead.
    if (cb.poisonDot.has) {
        const float remaining = cb.poisonDot.magnitude * cb.poisonDot.Remaining();
        const float share = std::max(remaining, corpse.body.healthMax * n5::kDeathFloor) *
                            (nodes.Has(node::kPoisonCreep) ? n5::kCreep : n5::kDeathShare);
        const float perSecond = share / n5::kDeathSpreadSeconds;
        const Picked p = Around(crowd, 0, n5::kNear, n5::kUnlimited);
        for (int i = 0; i < p.n; ++i) {
            b.On(p.k[i], [&](Board& target, const StatusInputs& in) {
                const float factor = rule::PoisonFactor(target);
                const float cap = static_cast<float>(n3::kDoseCap) * PerDose(c, t, nodes) * factor;
                rule::Poison next;
                const float now = target.poisonDot.Remaining();
                if (perSecond > cap) {
                    next.magnitude = cap;
                    next.remaining = std::max(now, share / cap);
                } else {
                    next.magnitude = std::min(target.poisonDot.magnitude + perSecond, cap);
                    next.remaining = std::max(now, Scaled(t, n5::kDeathSpreadSeconds));
                }
                rule::SetPoison(plan, target, next, in, nodes);
            });
        }
    }
    // 連鎖冰封 (5.4): a frozen corpse -- the enemies nearby freeze +3 and slow 30% 3 s.
    if (cb.Has(StatusKind::kFrozen) && nodes.Has(node::kFrostChainFreeze)) {
        const Picked p = Around(crowd, 0, n5::kNear, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            b.On(p.k[i], [&](Board& target, const StatusInputs& in) {
                rule::AddFreeze(plan, target, static_cast<float>(n5::kChainFreeze), false, in, nodes, rng);
            });
            b.Slow(p.k[i], n5::kQuakeSlow, n5::kQuakeSlowSeconds);
        }
    }
    // 火葬 (5.3): a detonation killed it -- once more ×0.5 on the enemies nearby.
    if (cb.Has(StatusKind::kCremation) && nodes.Has(node::kFireCremation)) {
        const Picked p = Around(crowd, 0, n5::kNear, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            b.Damage(p.k[i], kFire, cb[StatusKind::kCremation].magnitude * n5::kCremation);
        }
    }
    // 亡魂 (5.12): the death curse killed it -- the enemies nearby fear 2 s (Papyrus casts).
    if (cb.Has(StatusKind::kCurseKill) && nodes.Has(node::kDarkSoul)) {
        const Picked p = Around(crowd, 0, n5::kNear, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            b.Event(p.k[i], MakeEvent(Event::kHallucinate, 1, Scaled(t, n5::kSoulFear), 1));
        }
    }
    // 亡衛 (5.12): at sync 3 your servant's death blasts 3 m: B_max ×1.0 darkness, curse +2.
    if (f.servant && nodes.Has(node::kDarkGuard) && t.syncStage >= 3) {
        const Picked p = Around(crowd, 0, n5::kArea, n5::kNearLimit);
        for (int i = 0; i < p.n; ++i) {
            b.Damage(p.k[i], kDarkness, b.React(kDarkness, n5::kWardBlast, p.k[i]));
            b.On(p.k[i], [&](Board& target, const StatusInputs& in) { rule::AddCurse(plan, target, n5::kWardCurse, in, nodes); });
        }
    }
    if (f.killerYou && bleeding) {
        // 飲血 (5.8): heal 20% of max health and 10 s of 嗜血.
        if (nodes.Has(node::kBloodDrink)) {
            plan.Push(Amount(Op::kHeal, base.self.healthMax * n5::kDrink * t.multRecovery));
            pw.Set(StatusKind::kBloodthirst, 1.0f, Scaled(t, n5::kThirstSeconds));
        }
        // 血承 (5.8, 2.7): its fire / frost / shock / poison / magic resist ×50%, armour ×20%, max health ×10% for 15 s;
        // only the latest one (the old instances go first).
        if (nodes.Has(node::kBloodInherit)) {
            constexpr std::array<StatusKind, 5> kinds{ StatusKind::kInheritFire, StatusKind::kInheritFrost, StatusKind::kInheritShock,
                StatusKind::kInheritPoison, StatusKind::kInheritMagic };
            for (int i = 0; i < 5; ++i) {
                const float v = corpse.resist[i] * n5::kInheritResist;
                if (v > 0.0f) {
                    pw.Set(kinds[i], v, 15.0f);
                } else {
                    pw.Clear(kinds[i]);
                }
            }
            const float armor = corpse.armor * n5::kInheritArmor * t.multRecovery;
            if (armor > 0.0f) {
                pw.Set(StatusKind::kInheritArmor, armor, 15.0f);
            }
            pw.Set(StatusKind::kInheritHealth, corpse.body.healthMax * n5::kInheritHealth * t.multRecovery, 15.0f);
        }
    }
    // 不死 (5.8): at sync 3 a bleeding target dies -- stamina full, health to just over the nearest line above (30% / 70%),
    // one 回湧 without the crossing cooldown (血約 with it); every 30 s.
    if (bleeding && nodes.Has(node::kBloodUndying) && t.syncStage >= 3 && !self.Has(StatusKind::kUndyingCooldown)) {
        pw.Set(StatusKind::kUndyingCooldown, 1.0f, CooldownOf(t, n5::kUndyingCooldown));
        plan.Push(Amount(Op::kRestoreStamina, std::max(0.0f, bin.staminaMax - bin.stamina)));
        const float fraction = base.self.Fraction();
        const float line = fraction < n3::kZoneLow ? n3::kZoneLow : fraction < n3::kZoneHigh ? n3::kZoneHigh : 0.0f;
        if (line > 0.0f) {
            const float wanted = line * base.self.healthPermanent + 1.0f;
            if (wanted > base.self.health) {
                plan.Push(Amount(Op::kHeal, wanted - base.self.health));
            }
            const int zone = line == n3::kZoneLow ? 2 : 1;
            pw.Set(StatusKind::kBloodZone, static_cast<float>(zone), 86400.0f);
        }
        pw.Set(StatusKind::kSurgeUp, 1.0f, Scaled(t, n4::kSurgeUp));
        plan.Push(MakeEvent(Event::kRise));
    }
    // 無魔 (5.1): you killed a caster -- stamina and magicka full (a full bar's worth; what goes over into 超載).
    if (f.killerYou && corpse.spellUser && nodes.Has(node::kNoFormNoMana)) {
        plan.Push(Amount(Op::kRestoreStamina, std::max(0.0f, bin.staminaMax - bin.stamina)));
        GiveMagicka(plan, self, bin.magickaMax, bin, nodes);
    }
    // 連殺 (5.7): a wind-marked target your sneak attack killed -- 5 s of keeping sneak (Papyrus) and the next sneak attack
    // ×2 (the DLL's window).
    if (f.killerYou && nodes.Has(node::kWindKillStreak) && cb.mark[kWind].has && cb.Has(StatusKind::kLastHitSneak) &&
        cb.Layers(StatusKind::kLastHitSneak) == kWind) {
        plan.Push(MakeEvent(Event::kSneak, Scaled(t, n5::kStreak)));
        pw.Set(StatusKind::kKillStreak, 1.0f, Scaled(t, n5::kStreak));
    }
    RunBodies(plan, start, crowd, self, bin, nodes, rng);
}

// ================================================================ opening a form (the 臨)

// X臨 (5.x 開啟大師主線): every hostile within 2 m + 0.2 m a point of you opens the form's mark (a forced open: the mark,
// its cut, its open); the 臨強化 branches act on the same range even without the main line (2 m); 臨界 slows the
// hostiles nearby 30% 2 s; 雙斷 (a burst in the last 3 s) opens on every hostile within the burst range.
template <NodeReader Nodes, RandomSource Rng>
void PlanAdvent(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, int element, const Nodes& nodes, Rng& rng)
{
    const StatusInputs& base = *bin.in;
    const Tuning& t = *base.tuning;
    const int start = plan.count;
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    auto open = [&](int k) {
        b.On(k, [&](Board& target, const StatusInputs& in) {
            const HitStatus opened = PlanStatusHit(plan, element, false, target, self, in, nodes, rng, false);
            if (opened.opened) {
                PlanSelfOpen(plan, element, target, self, in, nodes, rng);
            }
        });
    };
    const int rank = IsNode(node::kAdvent[element]) ? nodes.Rank(node::kAdvent[element]) : 0;
    const float radius = (n5::kAdventBase + n5::kAdventPerPoint * static_cast<float>(rank)) * n5::kMetre;
    const Picked ring = Around(crowd, kAroundYou, radius, n5::kUnlimited);
    for (int i = 0; i < ring.n; ++i) {
        const int k = ring.k[i];
        if (rank > 0) {
            open(k);
        }
        switch (element) {
        case kFrost:
            if (rank > 0 && nodes.Has(node::kFrostAdventPlus)) {
                b.Slow(k, n5::kColdAdvent, n5::kColdAdventSeconds);   // 冰臨強化
            }
            break;
        case kEarth:
            if (nodes.Has(node::kEarthAdvent)) {
                plan.Push([&] {   // 地臨強化：範圍內敵人耐力 -50%（最大耐力的一半，不吃削減倍率）
                    StatusOp op = Amount(Op::kDrainStamina, crowd.m[k].body.staminaMax * n5::kEarthAdventStamina);
                    op.at = static_cast<std::uint8_t>(k);
                    return op;
                }());
            }
            break;
        case kPoison:
            if (nodes.Has(node::kPoisonAdventPlus)) {
                b.On(k, [&](Board& target, const StatusInputs& in) { rule::SpreadDoses(plan, target, n5::kPoisonAdvent, in, nodes); });
            }
            break;
        case kWater:
            if (nodes.Has(node::kWaterAdventPlus)) {
                b.On(k, [&](Board& target, const StatusInputs& in) {
                    Writer{ plan, target, Who::kTarget }.Set(StatusKind::kSoak, 1.0f, rule::SoakSeconds(*in.tuning, nodes));
                });
                b.Push(k, Amount(Op::kSlow, SoakSlowPct(t), 0, rule::SoakSeconds(t, nodes)));
            }
            break;
        case kDarkness:
            if (nodes.Has(node::kDarkAdventPlus)) {
                b.Event(k, MakeEvent(Event::kHallucinate, 1, Scaled(t, n5::kDarkAdventFear), 1));
            }
            break;
        case kAstral:
            if (nodes.Has(node::kAstralAdventPlus)) {
                b.On(k, [&](Board& target, const StatusInputs& in) { rule::AddStars(plan, target, n5::kAstralAdvent, in, nodes); });
            }
            break;
        default:
            break;
        }
    }
    if (element == kWater && nodes.Has(node::kWaterAdventPlus)) {
        plan.Push(MakeEvent(Event::kCleanse, 1));   // 水臨強化：你清除全部負面效果（本體在 Papyrus）
        plan.Push(Amount(Op::kRestoreMagicka, std::max(0.0f, bin.magickaMax - bin.magicka)));   // 並回滿魔力
    }
    if (element == kBlood && nodes.Has(node::kBloodAdventPlus)) {
        plan.Push(Amount(Op::kPayHealth, base.self.healthMax * n5::kBloodAdventCost));   // 血臨強化：付 15%（留 1 點）
        plan.Push(MakeEvent(Event::kSplash));                                              // 並濺血一次（不受越線冷卻）
    }
    if (nodes.Has(node::kCommonThreshold)) {
        const Picked p = Around(crowd, kAroundYou, n5::kNear, n5::kNearLimit);   // 臨界
        for (int i = 0; i < p.n; ++i) {
            b.Slow(p.k[i], n5::kThreshold, n5::kThresholdSeconds);
        }
    }
    if (self.Has(StatusKind::kDoubleBurst)) {
        Writer{ plan, self, Who::kPlayer }.Clear(StatusKind::kDoubleBurst);   // 雙斷：融斷後 3 秒內再開形態
        const Picked p = Around(crowd, kAroundYou, BurstRadius(nodes), n5::kUnlimited);
        for (int i = 0; i < p.n; ++i) {
            if (!(rank > 0 && Distance(crowd.you, crowd.m[p.k[i]].pos) <= radius)) {
                open(p.k[i]);
            }
        }
    }
    RunBodies(plan, start, crowd, self, bin, nodes, rng);
}

// ================================================================ 印潮 (5.2)

// The switch hit's open (the hit cut `oldElement`): up to 2 other targets within 15 m carrying the same old mark each
// get the new element's open (a forced open: cut, open).
template <NodeReader Nodes, RandomSource Rng>
void PlanSurge(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, int element, int oldElement, const Nodes& nodes, Rng& rng)
{
    if (!nodes.Has(node::kCommonSurge) || !IsElement(oldElement)) {
        return;
    }
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    const Picked p = Around(crowd, 0, n5::kNear, 2, [&](const Member& x) { return x.board.mark[oldElement].has; });
    for (int i = 0; i < p.n; ++i) {
        b.On(p.k[i], [&](Board& target, const StatusInputs& in) {
            const HitStatus opened = PlanStatusHit(plan, element, false, target, self, in, nodes, rng, false);
            if (opened.opened) {
                PlanSelfOpen(plan, element, target, self, in, nodes, rng);
            }
        });
    }
}

// ================================================================ 火浴 (5.3, commander ruling C3: redone in the DLL)

// Every second of the fire source (Plugin.cpp FireSecond): at 白熱 the first second fixes the count of hostiles the source
// burns (火浴 = that count, lasting what 白熱 has left); every later second heals you B_max(火) × 0.1 × that count (the
// count never follows later changes). `burning` is the hostiles the source reached this second.
constexpr void PlanFireBath(StatusPlan& plan, Board& self, int burning, float fireBMax, const Tuning& t)
{
    const Writer pw{ plan, self, Who::kPlayer };
    if (!self.Has(StatusKind::kFireBath)) {
        if (burning > 0 && self.Has(StatusKind::kHeat3)) {
            pw.Set(StatusKind::kFireBath, static_cast<float>(burning), self[StatusKind::kHeat3].Remaining());
        }
        return;
    }
    plan.Push(Amount(Op::kHeal, fireBMax * n3::kFireBathHeal * self[StatusKind::kFireBath].magnitude * t.multRecovery));
}

// ================================================================ 化身 (5.2): the active legend effects fire once

// Decision: the reaction-range legends (天雷 / 血海 / 天啟) are "主動": at the 化身 hit they act once on the target at
// full rank -- a 天雷 discharge of your charges, a 血海 surge, a 天啟 judgment; the rest stay the 10-second window.
template <NodeReader Nodes, RandomSource Rng>
void PlanAvatarBurst(StatusPlan& plan, Crowd& crowd, Board& self, const BodyInputs& bin, int element, const Nodes& nodes, Rng& rng)
{
    Bodies<Nodes, Rng> b(plan, crowd, self, bin, nodes, rng);
    if (!crowd.m[0].has) {
        return;
    }
    switch (element) {
    case kLightning: {
        const int charges = self.Layers(StatusKind::kCharge);
        b.DischargeAll(0, charges, 1.0f, 1.0f, b.CritRoll(charges, false));
        break;
    }
    case kBlood:
        b.SurgeOn(0, 1.0f, true);
        break;
    case kDivine:
        b.JudgeArea(0, 1.0f, HolyTier(self));
        break;
    default:
        break;
    }
}

}  // namespace essb
