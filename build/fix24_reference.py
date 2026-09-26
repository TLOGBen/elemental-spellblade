"""Round 24 (slice N5) reference model: the reaction bodies, the fusion (融斷), the death handling and the range scans,
written from 元素魔戰士規劃-v0.4.md on its own (the C++ in native/include/Reactions.h is never consulted). It extends the
round-23 model (build/fix23_reference.py, which extends round 22's): a World24 holds a CROWD -- member 0 (the hit / ended /
dying actor, or nobody for a burst) and the other actors with their boards, bodies and positions -- and every op it
produces names the member it acts on. native/tests/reaction_test.cpp runs the same scenarios through the DLL's planners
and requires the same boards and the same ops, member by member.

NODE_NAMES   every node:: constant Reactions.h reads that earlier rounds did not name -> (tree, v0.4 name)
SKELETON     per-element main lines the burst reads ([element] -> slot), by v0.4 label pattern
LABELED      per-element lines whose label differs by tree (X臨: 地臨 for earth)
"""
import math

NODE_NAMES = {
    # 5.1 noform (冷寂 and the two no-form N5 branches)
    'kNoFormBurst': ('noform', '融斷'),
    'kNoFormHushBurn': ('noform', '寂每層燒魔'),
    'kNoFormGather': ('noform', '收束'),
    'kNoFormBurstRadius': ('noform', '融斷範圍'),
    'kNoFormHushCap': ('noform', '寂上限'),
    'kNoFormSever': ('noform', '斷界'),
    'kNoFormBackflow': ('noform', '回流'),
    'kNoFormBurstAgain': ('noform', '融斷再'),
    'kNoFormDoubleBurst': ('noform', '雙斷'),
    'kNoFormAllHush': ('noform', '萬寂'),
    'kNoFormNoMana': ('noform', '無魔'),
    'kNoFormSeal': ('noform', '封印'),
    # 5.2 common
    'kCommonBurst': ('common', '融斷'),
    'kCommonBurstAgain': ('common', '融斷再'),
    'kCommonChainEnd': ('common', '連鎖終焉'),
    'kCommonFeed': ('common', '反哺'),
    'kCommonGrand': ('common', '大協奏'),
    'kCommonSafety': ('common', '安全閥'),
    'kCommonSurge': ('common', '印潮'),
    'kCommonThreshold': ('common', '臨界'),
    # 5.3 fire
    'kFireCremation': ('fire', '火葬'),
    'kFireDomain': ('fire', '火域'),
    'kFireEmberHeat': ('fire', '餘熱'),
    'kFireFlareUp': ('fire', '焰起強化'),
    'kFirePreBurn': ('fire', '先燃'),
    'kFireSkyfire': ('fire', '焚天'),
    # 5.4 frost
    'kFrostAdventPlus': ('frost', '冰臨強化'),
    'kFrostArmorBreak': ('frost', '碎甲加深'),
    'kFrostAvalanche': ('frost', '冰崩'),
    'kFrostBurst': ('frost', '霜爆'),
    'kFrostChainFreeze': ('frost', '連鎖冰封'),
    'kFrostColdTide': ('frost', '寒潮'),
    'kFrostDeepChill': ('frost', '深寒'),
    'kFrostGlacier': ('frost', '冰河'),
    'kFrostPlain': ('frost', '冰原'),
    'kFrostZero': ('frost', '絕對零度'),
    # 5.5 lightning
    'kLightningArc': ('lightning', '電弧'),
    'kLightningBurstBonus': ('lightning', '雷斷'),
    'kLightningChain': ('lightning', '連鎖'),
    'kLightningChargeOpen': ('lightning', '充能開印'),
    'kLightningConduct': ('lightning', '傳導'),
    'kLightningFirst': ('lightning', '先雷'),
    'kLightningFlash': ('lightning', '雷閃'),
    'kLightningPerCharge': ('lightning', '放電每格電荷傷害'),
    'kLightningSky': ('lightning', '天雷'),
    'kLightningStrike': ('lightning', '雷殛'),
    'kLightningWeaken': ('lightning', '感電削弱'),
    # 5.6 earth
    'kEarthBase': ('earth', '地基'),
    'kEarthCollapse': ('earth', '崩裂'),
    'kEarthDust': ('earth', '塵暴'),
    'kEarthFirstQuake': ('earth', '先震'),
    'kEarthFissureArmor': ('earth', '裂痕護甲削減'),
    'kEarthLandslide': ('earth', '山崩'),
    'kEarthQuakeStamina': ('earth', '地震耐力削減'),
    'kEarthRiftZone': ('earth', '地裂'),
    'kEarthSever': ('earth', '地斷'),
    'kEarthWave': ('earth', '震波'),
    'kEarthWide': ('earth', '廣震'),
    'kEarthQuakeStrike': ('earth', '震擊'),
    # 5.7 wind
    'kWindAmbush': ('wind', '奇襲'),
    'kWindBladeDamage': ('wind', '風刃傷害'),
    'kWindChase': ('wind', '追風'),
    'kWindDrag': ('wind', '牽引'),
    'kWindGust': ('wind', '氣流'),
    'kWindHurricane': ('wind', '颶風'),
    'kWindLanding': ('wind', '落地傷害'),
    'kWindLeap': ('wind', '輕躍'),
    'kWindPullRange': ('wind', '開印拉近距離'),
    'kWindRaid': ('wind', '風襲'),
    'kWindSever': ('wind', '風斷'),
    'kWindSky': ('wind', '上天'),
    'kWindTurbulence': ('wind', '亂流'),
    'kWindVortex': ('wind', '風渦'),
    'kWindWhirl': ('wind', '迴旋'),
    # 5.8 blood
    'kBloodAdventPlus': ('blood', '血臨強化'),
    'kBloodContract': ('blood', '血契'),
    'kBloodCurse': ('blood', '血咒'),
    'kBloodDrink': ('blood', '飲血'),
    'kBloodEndBleed': ('blood', '放血終焉'),
    'kBloodFlood': ('blood', '血漫'),
    'kBloodInherit': ('blood', '血承'),
    'kBloodOpenHeal': ('blood', '開印回血'),
    'kBloodPact': ('blood', '血約'),
    'kBloodPool': ('blood', '血池'),
    'kBloodSacrifice': ('blood', '血祭之始'),
    'kBloodSated': ('blood', '飽飲'),
    'kBloodSea': ('blood', '血海'),
    'kBloodSever': ('blood', '血斷'),
    'kBloodSpatter': ('blood', '血濺'),
    'kBloodSurgeHeal': ('blood', '血潮治療倍率 ×2'),
    'kBloodUndying': ('blood', '不死'),
    # 5.9 divine
    'kDivineApocalypse': ('divine', '天啟'),
    'kDivineAsh': ('divine', '聖灰'),
    'kDivineGlow': ('divine', '聖輝'),
    'kDivineHeavyJudge': ('divine', '重裁'),
    'kDivineLight': ('divine', '聖光'),
    'kDivineOpenHeal': ('divine', '開印回血'),
    'kDivinePureAsh': ('divine', '淨灰'),
    'kDivinePureLand': ('divine', '淨土'),
    'kDivineRadiance': ('divine', '光耀'),
    'kDivineSanctum': ('divine', '聖域'),
    'kDivineSever': ('divine', '聖斷'),
    'kDivineSmite': ('divine', '破邪斬'),
    'kDivineWideJudge': ('divine', '廣裁'),
    'kDivineGuard': ('divine', '護持'),
    # 5.10 poison
    'kPoisonAdventPlus': ('poison', '毒臨強化'),
    'kPoisonBlood': ('poison', '毒血'),
    'kPoisonCreep': ('poison', '蔓延'),
    'kPoisonFilm': ('poison', '毒膜'),
    'kPoisonFog': ('poison', '毒霧'),
    'kPoisonInfect': ('poison', '疫染'),
    'kPoisonRot': ('poison', '腐蝕開印'),
    'kPoisonRotEnd': ('poison', '腐蝕終焉'),
    'kPoisonSplash': ('poison', '毒濺'),
    'kPoisonThick': ('poison', '濃毒'),
    'kPoisonVirulent': ('poison', '劇毒'),
    'kPoisonWither': ('poison', '萎靡'),
    'kPoisonErode': ('poison', '侵蝕'),
    'kPoisonSever': ('poison', '毒斷'),
    'kFrostBurstShatter': ('frost', '冰封融斷'),
    # 5.11 water
    'kWaterAdventPlus': ('water', '水臨強化'),
    'kWaterFlood': ('water', '大潮'),
    'kWaterOpenHeal': ('water', '開印時回復生命與耐力各最大值 0.3%／點'),
    'kWaterOpenWash': ('water', '開印沖刷'),
    'kWaterScour': ('water', '洗滌'),
    'kWaterSever': ('water', '水斷'),
    'kWaterSpread': ('water', '廣佈'),
    'kWaterSpring': ('water', '湧泉'),
    'kWaterTidePool': ('water', '潮池'),
    # 5.12 darkness
    'kDarkAbyssEcho': ('darkness', '深淵回響'),
    'kDarkAdventPlus': ('darkness', '暗臨強化'),
    'kDarkDeathZone': ('darkness', '死域'),
    'kDarkFeast': ('darkness', '狂宴'),
    'kDarkGuard': ('darkness', '亡衛'),
    'kDarkLegion': ('darkness', '群魔'),
    'kDarkLord': ('darkness', '死靈主'),
    'kDarkNightmare': ('darkness', '夢魘'),
    'kDarkNoHeal': ('darkness', '不治'),
    'kDarkRemnant': ('darkness', '殘魂'),
    'kDarkSoul': ('darkness', '亡魂'),
    'kDarkStain': ('darkness', '暗染'),
    'kDarkSummon': ('darkness', '冥召'),
    'kDarkErosion': ('darkness', '詛咒每層抗性侵蝕'),
    # 5.13 astral
    'kAstralAdventPlus': ('astral', '星臨強化'),
    'kAstralBright': ('astral', '明星'),
    'kAstralChain': ('astral', '星鏈'),
    'kAstralEcho': ('astral', '回聲比例'),
    'kAstralEclipse': ('astral', '星蝕'),
    'kAstralGather': ('astral', '聚星'),
    'kAstralMeteor': ('astral', '隕星'),
    'kAstralScatter': ('astral', '星散'),
    'kAstralSever': ('astral', '星斷'),
    'kAstralZone': ('astral', '星域'),
}

# (route, tier, label pattern, trees without that line) -- checked against every tree like round 22's SKELETON.
SKELETON = {
    'kBurstMain': (2, 1, '{x}印記的融斷', set()),
    'kBurstAgain': (2, 3, '{x}印記的融斷再', set()),
}
# (route, tier, {tree: label}) -- the 開啟大師主線 "X臨" (earth: 地臨).
LABELED = {
    'kAdvent': (1, 3, {'fire': '火臨', 'frost': '冰臨', 'lightning': '雷臨', 'earth': '地臨', 'wind': '風臨', 'blood': '血臨',
                       'divine': '聖臨', 'poison': '毒臨', 'water': '水臨', 'darkness': '暗臨', 'astral': '星臨'}),
}



# ================================================================ the scenario model
# World24 extends the round-23 model (build/fix23_reference.World23: the N3 status rules and the N4 self rules, both
# written from v0.4 on their own) with a crowd. `select(k)` makes member k the round-22 model's "target" (its board and
# body), so every status rule the bodies reuse (凍結累積、擴散一劑、詛咒、流血、星痕、碎冰、終焉的狀態部分…) acts on that
# member; every op remembers the member it acts on (-1 = you). The body pass then walks the ops in order the way v0.4
# describes each body: the open / end bodies (2.6), the node bodies (5.x), the range rules (2.9). Random draws follow the
# round-23 modes ('mid', 'yes', 'no').

import fix22_reference as _n3
import fix23_reference as _n4
from fix22_reference import (FIRE, FROST, LIGHTNING, EARTH, WIND, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL, TREE, SHORT,
                             CUT, BURST, EXPIRE, Slot, Board, SIGNATURE)

EVENT_ARGS = dict(Open=4, End=8, Frozen=1, Hallucinate=3, Judgment=2, Splash=1, Shatter=1, Landing=1, Rise=0, Discharge=4,
                  Blade=2, Knock=1, SyncUp=1, Cleanse=1, Lethal=0, Push=5, Ash=0, Raise=5, Sneak=1, Domain=3, Overheat=0)
BODY_ONLY = {'Frozen', 'Judgment', 'Splash', 'Rise', 'Shatter', 'Landing', 'Discharge', 'Blade', 'Overheat'}
SELF_OPS = {'heal', 'magicka', 'stamina', 'pay', 'spendMagicka', 'payStamina', 'guardPool', 'hurtHealth', 'resonance',
            'freezeNearby'}
SELF_EVENTS = {'SyncUp', 'Cleanse', 'Lethal', 'Sneak', 'Splash', 'Rise', 'Overheat'}
TIMED_SELF = {'magicResistBuff', 'haste', 'poisonResistBuff'}
DROPPED = {'noop', 'bleedDrain', 'result', 'blood'}   # not compared (status writes are compared as boards)

METRE = 70.0                  # 2.9: 1 公尺 = 70 單位
NEAR, NEAR_LIMIT = 15 * METRE, 5          # 「附近」：15 公尺、最近的 5 人
AREA = 3 * METRE              # 範圍終焉 3 公尺
CROWD_MAX = 24                # 一次掃描讀的合格敵人上限（「不限」＝全部讀到的）
HEAT_BURST = [1.0, 1.6, 2.4, 3.2, 4.0]
HOLY_PROC = [0.0, 0.10, 0.20, 0.35]
TIER_CAP = [6, 13, 21, 30, 60, 999]
TIER_SECONDS = [120.0, 120.0, 120.0, 180.0, 180.0, 86313600.0]
SYNC_K = [1.0, 1.5, 2.0, 3.0]
HIT_CURVE = [(1.0, 1.3), (0.7, 1.1), (0.3, 0.8), (0.1, 0.6)]
LEECH_CURVE = [(1.0, 0.05), (0.7, 0.15), (0.3, 0.35), (0.1, 0.50)]
INHERIT = ['InheritFire', 'InheritFrost', 'InheritShock', 'InheritPoison', 'InheritMagic']


def interpolate(x, points):
    if x >= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x >= x1:
            return y1 + (x - x1) / (x0 - x1) * (y0 - y1)
    return points[-1][1]


def distance(a, b):
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b)))


class Member:
    def __init__(self, spec):
        self.has = spec.get('has', True)
        self.ally = spec.get('ally', False)
        self.pos = tuple(float(x) for x in spec['pos'])
        self.level = spec.get('level', 10)
        self.dragon = spec.get('dragon', False)
        self.essential = spec.get('essential', False)   # 2.9 必要角色: never knocked down, raised or turned to ash
        self.spell_user = spec.get('spell_user', False)
        self.armor = float(spec.get('armor', 0.0))
        self.resist = [float(x) for x in spec.get('resist', [0, 0, 0, 0, 0])]
        self.magicka_max = float(spec.get('magicka_max', 0.0))
        body = spec.get('body', {})
        self.body = dict(health=float(body.get('health', 100.0)), health_max=float(body.get('health_max', 100.0)),
                         stamina=float(body.get('stamina', 100.0)), stamina_max=float(body.get('stamina_max', 100.0)),
                         vip=body.get('vip', False), undead=body.get('undead', False), distance=0.0)
        self.board = Board()
        self.board.hush = None
        seed_board(self.board, spec.get('board', {}))
        self.board.frenzied = spec.get('frenzied', False)
        self.board.max_slow = float(spec.get('max_slow', 0.0))


def seed_board(board, statuses):
    for kind, (magnitude, elapsed, duration) in statuses.items():
        slot = Slot(magnitude, elapsed, duration)
        if kind == 'PoisonDot':
            board.poison = slot
        elif kind == 'BleedDot':
            board.bleed = slot
        elif kind == 'Hush':
            board.hush = slot
        elif kind.startswith('Mark'):
            board.marks[int(kind[4:])] = slot
        else:
            board.kinds[kind] = slot


class World24(_n4.World23):
    def __init__(self, damage, crowd, *, stamina=100.0, stamina_max=100.0, magicka=100.0, sneak=False, bloodthirst=False,
                 **options):
        super().__init__(damage, **options)
        self.me.hush = None
        self.ats, self.src, self.tags = [], [], {}
        self.you = tuple(float(x) for x in crowd['you'])
        self.members = [Member(m) for m in crowd['members']]
        for m in self.members:
            m.body['distance'] = distance(self.you, m.pos)
        self.stamina, self.stamina_max, self.magicka = stamina, stamina_max, magicka
        self.sneak, self.bloodthirst_fact = sneak, bloodthirst
        self.at = 0
        self.select(0)

    # ---------------------------------------------------------------- the crowd
    def select(self, k):
        self.at = k
        self.target, self.body = self.members[k].board, self.members[k].body

    def on(self, k, fn):
        outer = self.at
        self.select(k)
        fn()
        self.select(outer)

    def around(self, centre, radius, limit, keep=None):
        """2.9: the eligible members within `radius` of `centre` (a member, or -1 = you), nearest first, at most `limit`."""
        at = self.you if centre == -1 else self.members[centre].pos
        found = []
        for k, m in enumerate(self.members):
            if k == centre or not m.has or m.ally or (keep and not keep(m)):
                continue
            d = distance(at, m.pos)
            if d <= radius:
                found.append((d, k))
        found.sort(key=lambda x: x[0])
        return [k for _, k in found[:limit]]

    # ---------------------------------------------------------------- ops
    def op(self, *row):
        name = row[0]
        if name == 'event':
            at = -1 if row[1] in SELF_EVENTS else self.at
        elif name == 'timed':
            at = -1 if row[1] in TIMED_SELF else self.at
        else:
            at = -1 if name in SELF_OPS else self.at
        self.ops.append(list(row))
        self.ats.append(at)
        self.src.append(self.at)

    def op_at(self, k, *row):
        outer = self.at
        self.at = k
        self.op(*row)
        self.at = outer

    def event_at(self, k, name, *args):
        self.op_at(k, 'event', name, *[float(a) for a in args])

    def detonate_stars(self, mult):
        before = len(self.ops)
        super().detonate_stars(mult)
        for i in range(before, len(self.ops)):
            if self.ops[i][0] == 'damage' and self.ops[i][1] == ASTRAL:
                self.tags[i] = 'star'        # the star detonation (聚星 reads it)

    # ---------------------------------------------------------------- the terms a body uses
    def fraction(self):
        return self.hp / self.hp_max

    def curve_fraction(self):
        f = min(1.0, max(0.0, self.fraction()))
        return 1.0 - f if self.has('blood', '逆流') else f

    def rage(self):
        return self.has('blood', '血怒') and 0.3 <= self.fraction() <= 0.7

    def rscale(self, element):
        """2.7 D_react's categorical terms: G(L) × the damage multiplier × blood's curve and 血怒 × day / night."""
        scale = self.g(element) * self.base
        if element == BLOOD:
            scale *= interpolate(self.curve_fraction(), HIT_CURVE) * (1.15 if self.rage() else 1.0)
        if not self.interior and ((element == DARKNESS and self.night) or (element == DIVINE and not self.night)):
            scale *= 1.2
        return scale

    def vuln(self, k):
        outer = self.at
        self.select(k)
        v = self.vulnerability()
        self.select(outer)
        return v

    def react(self, element, mult, k):
        m = self.members[k]
        amount = self.bmax(element) * mult * self.rscale(element) * self.vuln(k)
        if element == FIRE and m.board.has('DomainFire'):
            amount *= 1.2                                     # 火域：火傷 +20%
        if element == DIVINE and m.board.has('Radiance') and m.body['undead']:
            amount *= 1.2                                     # 光耀：亡靈魔族受聖傷 +20%
        return amount

    def leech(self):
        """5.8 吸血比例 at your blood zone (+ the expert line, 血怒, 飲血's 嗜血 +10%)."""
        ratio = interpolate(self.curve_fraction(), LEECH_CURVE) + 0.01 * self.rank('blood', '吸血比例各血位')
        if self.rage():
            ratio += 0.15
        if self.bloodthirst_fact:
            ratio += 0.10
        return ratio

    def sig(self, element):
        tree = TREE[element]
        return 1 + self.pct(self.rank(tree, SIGNATURE[tree]), 0.03)

    def burst_node_mult(self, element):
        tree, x = TREE[element], SHORT[element]
        return 1 + self.pct(self.rank(tree, f'{x}印記的融斷'), 0.02) + self.pct(self.rank(tree, f'{x}印記的融斷再'), 0.02)

    def g_noform(self):
        return 1 + 0.05 * max(1, self.level.get('noform', 1))

    def damage(self, k, element, amount):
        if amount > 0:
            self.op_at(k, 'damage', element, amount)

    def heal(self, amount):
        self.op('heal', amount * self.recovery)

    def heal_leech(self, amount):
        if amount > 0:
            self.op('heal', amount * self.recovery)

    def magicka_op(self, amount):
        self.op('magicka', amount * self.recovery)

    def stamina_op(self, amount):
        self.op('stamina', amount * self.recovery)

    def slow(self, k, pct, seconds):
        self.op_at(k, 'slow', pct, self.scaled(seconds))

    def timed(self, k, name, magnitude, seconds):
        if name == 'armorDebuff':
            magnitude *= self.drain                            # the drains took ESSB_MultDrain
        self.op_at(k, 'timed', name, magnitude, self.scaled(seconds))

    def timed_raw(self, k, name, magnitude, seconds):
        self.op_at(k, 'timed', name, magnitude, seconds)

    def drain_magicka(self, k, amount):
        self.op_at(k, 'drainMagicka', amount * self.drain)

    def drain_stamina(self, k, amount):
        self.op_at(k, 'drainStamina', amount * self.drain)

    def push(self, k, kind, metres, landing, centre, slow_if_immune):
        self.event_at(k, 'Push', kind, metres, landing, float(int(centre)), 1 if slow_if_immune else 0)

    def soak_slow(self):
        return min(self.wet_slow, max(0.0, min(self.slow_cap, 70.0)))

    def crit_roll(self, charges):
        chance = 0.05 + 0.02 * charges + (0.15 if self.me.has('QuickShock') else 0.0)
        return 1.5 if self.real(0.0, 1.0) < chance else 1.0

    def quake_radius(self):
        return 5 * METRE if self.has('earth', '廣震') else AREA

    def landing_stored(self):
        k = 0.5 + self.pct(self.rank('wind', '落地傷害'), 0.05) + (0.5 if self.has('wind', '上天') else 0.0)
        return self.bmax(WIND) * k

    # ---------------------------------------------------------------- 2.6 開印 bodies and the open branches
    def open_body(self, k, element, mult, cut_from, from_hit):
        m = self.members[k]
        if element == FIRE:
            self.damage(k, FIRE, self.react(FIRE, 0.5 * mult, k))                          # 點燃 B_max ×0.5
            if self.has('fire', '餘熱'):
                self.stamina_op(15.0)
            if self.has('fire', '焰起強化'):
                raise NotImplementedError('焰起強化 (a fire proc) is not modelled here; see the probe card')
            if self.has('fire', '先燃') and self.sync >= 3:
                self.detonate(k, 0.5, self.heat_tier(), 0.0, 1.0, False)                   # 先燃 ×0.5，不消耗
        elif element == FROST:
            self.slow(k, self.frost_open_slow * mult, 3.0)                                 # 霜結 25% 3 秒
            if self.has('frost', '寒潮'):
                for j in self.around(k, NEAR, 1):
                    self.on(j, lambda: self.add_freeze(2.0))
        elif element == LIGHTNING:
            self.drain_magicka(k, self.bmax(LIGHTNING) * 1.0 * mult)                       # 感電：魔力 -B_max
            if self.has('lightning', '傳導'):
                self.spread_mark(k, LIGHTNING)
            if self.has('lightning', '充能開印'):
                self.magicka_op(self.bmax(LIGHTNING))
            if self.has('lightning', '感電削弱'):
                self.timed(k, 'magicResistDebuff', 10.0, 8.0)
            if self.has('lightning', '雷閃'):
                self.timed(0, 'haste', 15.0, 2.0)
            if self.has('lightning', '先雷') and self.sync >= 3:
                n = self.me.layers('Charge')
                self.discharge_all(k, n, 1.0, 1.0, self.crit_roll(n))
        elif element == EARTH:
            armor = 30.0 + 2.0 * self.rank('earth', '裂痕護甲削減')
            self.timed(k, 'armorDebuff', armor * mult, 8.0)                                # 裂痕：護甲 -30
            self.drain_stamina(k, 10.0 * mult)                                             #       耐力 -10
            self.stamina_op(10.0 * mult)                                                   #       你回 10
            if self.has('earth', '震波'):
                for j in self.around(k, NEAR, 1):
                    self.on(j, lambda: self.put(self.target, 'Fissure', 1, self.scaled(8.0)))
                    self.timed(j, 'armorDebuff', armor, 8.0)
            if self.has('earth', '深裂痕') and m.body['stamina'] / m.body['stamina_max'] < 0.5:
                self.event_at(k, 'Knock', 3.0)
            if self.has('earth', '地基'):
                self.timed(k, 'staminaRateDebuff', 100.0, 3.0)
            if self.has('earth', '先震') and self.sync >= 3:
                self.quake(k, 0.5, False)
        elif element == WIND:
            ambush = self.has('wind', '奇襲') and self.sneak and from_hit
            if not ambush:
                metres = min(3.0, 1.5 + 0.1 * self.rank('wind', '開印拉近距離'))
                self.push(k, 2, metres * mult, 0.0, 0, False)                             # 風痕：拉近 1.5 m
                if self.has('wind', '牽引'):
                    behind = distance(self.you, m.pos)
                    for j in self.around(k, 1.5 * METRE, CROWD_MAX, lambda x: distance(self.you, x.pos) > behind)[:2]:
                        self.push(j, 2, metres * mult, 0.0, 0, False)
                        self.on(j, lambda: self.put(self.target, 'Unbalance', 1, self.scaled(3.0)))
            if self.has('wind', '風襲'):
                self.spread_mark(k, WIND, lambda j: self.on(j, lambda: self.put(self.target, 'Unbalance', 1, self.scaled(3.0))))
            if self.has('wind', '輕躍'):
                self.timed(0, 'haste', 10.0, 3.0)
            if self.has('wind', '氣流'):
                self.stamina_op(10.0)
            if ambush:
                self.on(k, lambda: self.drop(self.target, 'Unbalance'))
                self.wind_end(k, 1.0, CUT)                                                 # 奇襲：開印兼吹飛
        elif element == BLOOD:
            self.heal_leech(50.0 * self.leech() * mult)                                    # 依血位吸血
            if self.has('blood', '血濺'):
                for j in self.around(k, NEAR, 1):
                    self.on(j, lambda: self.add_bleed(1))
            if self.has('blood', '開印回血'):
                self.heal(self.bmax(BLOOD) * 0.5 * (2.0 if self.fraction() < 0.3 else 1.0))
            if self.has('blood', '血咒'):
                self.timed(k, 'healRateDebuff', 50.0, 5.0)
            if self.has('blood', '深血痕'):
                zone = self.blood_zone()
                for _ in range(2 if zone == 3 else 1 if zone == 2 else 0):
                    self.heal_leech(50.0 * self.leech())
            if self.has('blood', '血祭之始') and self.sync >= 3:
                self.surge_on(k, 0.5, True)
        elif element == DIVINE:
            self.heal(self.bmax(DIVINE) * (0.5 * mult + 0.05 * self.rank('divine', '開印回血')))
            if self.has('divine', '聖輝'):
                self.spread_mark(k, DIVINE)
            if self.has('divine', '聖光'):
                for j, x in enumerate(self.members):
                    if j >= 1 and x.has and x.ally and distance(self.you, x.pos) <= NEAR:
                        self.op_at(j, 'healTarget', self.bmax(DIVINE) * self.recovery)
        elif element == POISON:
            doses = self.stochastic(mult)
            for j in self.around(k, 3 * METRE, 1):
                if doses > 0:
                    self.on(j, lambda: self.spread_doses(doses))                             # 淬毒：3 公尺內一人 1 劑
            if self.has('poison', '毒濺'):
                splash = self.stochastic(2.0 * mult)
                for j in self.around(k, NEAR, 1):
                    self.on(j, lambda: self.spread_doses(splash))
            if self.has('poison', '濃毒'):
                if self.around(k, 6 * METRE, CROWD_MAX, lambda x: x.board.poison is not None):
                    self.on(k, lambda: self.spread_doses(2.0))
            if self.has('poison', '毒膜'):
                self.timed(0, 'poisonResistBuff', 50.0, 5.0)
            if self.has('poison', '腐蝕開印'):
                self.timed(k, 'poisonResistDebuff', 10.0, 8.0)
            if self.has('poison', '毒血'):
                self.heal(self.bmax(POISON) * 0.5)
        elif element == WATER:
            rank = self.rank('water', '開印時回復生命與耐力各最大值 0.3%／點')
            if rank > 0:
                self.heal(self.hp_max * 0.003 * rank)
                self.stamina_op(self.stamina_max * 0.003 * rank)
            if self.has('water', '廣佈'):
                def soak(j):
                    self.on(j, lambda: self.put(self.target, 'Soak', 1, self.soak_seconds()))
                    self.op_at(j, 'slow', self.soak_slow(), self.soak_seconds())
                self.spread_mark(k, 0, soak, lambda x: not x.board.has('Soak'))
            if self.has('water', '湧泉'):
                self.stamina_op(self.water_open_stamina)
            if self.has('water', '開印沖刷') and not m.board.has('WashCooldown'):
                self.on(k, lambda: self.put(self.target, 'WashCooldown', 1, self.cooldown(10.0)))
                self.op_at(k, 'wash', 2 * self.bmax(WATER) if self.has('water', '淨潮') else 0.0, 1.0)
        elif element == DARKNESS:
            drain = self.bmax(DARKNESS) * 1.0 * mult
            self.drain_magicka(k, drain)
            self.magicka_op(drain)
            if self.has('darkness', '暗染'):
                self.spread_mark(k, DARKNESS, lambda j: self.on(j, lambda: self.add_curse(2)))
        elif element == ASTRAL:
            if self.has('astral', '明星'):
                near = self.around(k, NEAR, 1, lambda x: x.board.has('Star'))
                if near:
                    self.on(k, lambda: self.add_stars(1))
                    self.on(near[0], lambda: self.add_stars(1))
            if self.has('astral', '星散') and not self.me.has('Cosmos'):
                self.spread_mark(k, ASTRAL, lambda j: self.on(j, lambda: self.add_stars(1)))

    def spread_mark(self, k, element, extra=None, keep=None):
        """「開印時附近 1 人也 X」：15 公尺內最近、能不切印就帶上這個印記的一人（只給印記，不開印）."""
        dual = self.has('common', '雙印')

        def ok(x):
            if keep and not keep(x):
                return False
            if element == 0:
                return True
            others = len(x.board.marks) - (1 if element in x.board.marks else 0)
            return element not in x.board.marks and (others == 0 or (dual and others < 2))
        for j in self.around(k, NEAR, 1, ok):
            if element:
                self.on(j, lambda: self.target.marks.__setitem__(element, Slot(0, 0, self.mark_seconds(element))))
            if extra:
                extra(j)

    # ---------------------------------------------------------------- 2.6 終焉 bodies and the closing branches
    def end_event_body(self, k, element, reason, mult, flags, v1, v2, v3, charge):
        chain, after_switch = bool(flags & 1), bool(flags & 2)
        burst = reason == BURST
        body = mult
        if not chain:
            body *= self.end_node_mult(element)
            if burst:
                body *= self.burst_node_mult(element)
                if element == LIGHTNING and self.has('lightning', '雷斷'):
                    body *= 1 + 0.3 * charge                                               # 雷斷：全部電荷的放電加成
        m = self.members[k]
        # 融斷 (v0.4 2.7 D_burst, commander ruling): each fused mark deals B_max × K_sync × G × M_mod, no K_react; the end
        # move itself is not dealt; the end's non-damage part and every branch still apply
        fused = burst and not chain
        if fused:
            self.fusion_hit(k, element, body)
        if element == FIRE:
            if not fused:
                self.detonate(k, body, int(v1 + 0.5), v2, v3, True)
            if not chain and self.has('fire', '焚天'):
                for j in self.around(k, AREA, NEAR_LIMIT, lambda x: FIRE in x.board.marks):
                    self.chain_end_on(j, FIRE, body)
            if burst and not chain and self.has('fire', '火域'):
                self.event_at(k, 'Domain', FIRE, 5.0, AREA)
        elif element == FROST:
            if v1 < 0.5:
                if not fused:
                    self.damage(k, FROST, self.react(FROST, 1.0 * body * self.sig(FROST), k))   # 碎冰（未冰封）×1.0
            elif not chain and self.has('frost', '冰河') and not self.has('frost', '冰崩'):
                self.shatter_area(k)
            if burst and not chain and self.has('frost', '冰原'):
                self.event_at(k, 'Domain', FROST, 5.0, AREA)
        elif element == LIGHTNING:
            if charge > 0:
                if not fused:
                    self.discharge_all(k, charge, body, v1, self.end_crit(charge, v2, v3 >= 0.5))
                if not chain and self.has('lightning', '雷殛'):
                    for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: LIGHTNING in x.board.marks):
                        self.discharge(j, charge, body, 1.0, self.crit_roll(charge), True)
        elif element == EARTH:
            if not fused:
                quake = body
                if not chain and self.me.has('ChargedQuake'):
                    quake *= 1 + self.me.mag('ChargedQuake')
                    self.drop(self.me, 'ChargedQuake')
                self.quake(k, quake, True)
            if not chain and self.has('earth', '山崩'):
                for j in self.around(k, self.quake_radius(), NEAR_LIMIT, lambda x: x.board.has('Fissure')):
                    self.quake(j, body, False)
            if burst and not chain and self.has('earth', '地裂'):
                self.event_at(k, 'Domain', EARTH, 5.0, AREA)
        elif element == WIND:
            if fused:
                self.push(k, 4, 1.0, self.landing_stored(), 0, True)                  # 2.5 融斷：吹上天
            else:
                self.wind_end(k, body, reason)
            if not chain and self.has('wind', '風渦'):
                for j in self.around(k, 5 * METRE, NEAR_LIMIT):
                    self.push(j, 3, 2.0, 0.0, k + 1, False)                          # 拉向成員 k（Plugin 換成 FormID）
            if burst and not chain and self.has('wind', '風斷'):
                self.blade(k, 1.0)
                self.blade(k, 1.0)
        elif element == BLOOD:
            if not fused:
                self.surge(k, v1, body, reason, chain)
            if not chain and not fused and self.has('blood', '血漫'):
                for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: x.board.has('Bleed')):
                    self.surge_on(j, body, True)
            if burst and not chain and self.has('blood', '血池'):
                self.event_at(k, 'Domain', BLOOD, 5.0, AREA)
        elif element == DIVINE:
            if not fused:
                self.judge_area(k, body, int(v1 + 0.5))
            if burst and not chain and self.has('divine', '聖斷'):
                self.heal(self.bmax(DIVINE))
            if not chain:
                if burst and self.has('divine', '神聖領域'):
                    self.event_at(k, 'Domain', DIVINE, 8.0, AREA)
                elif self.has('divine', '聖域'):
                    self.event_at(k, 'Domain', DIVINE, 5.0, AREA)
        elif element == POISON:
            b = m.board
            if not chain and self.has('poison', '劇毒') and b.poison and m.resist[3] > 0:
                self.timed_raw(k, 'poisonResistDebuff', m.resist[3], b.poison.remaining())   # 毒抗視為 0
            if not chain and self.has('poison', '腐蝕終焉'):
                self.timed(k, 'magicResistDebuff', 20.0, 8.0)
            if not chain and self.has('poison', '疫染') and b.poison:
                copy_m, copy_r = b.poison.magnitude, b.poison.remaining()
                factor = b.mag('Catalyzed') if b.has('Catalyzed') and b.mag('Catalyzed') > 0 else 1.0
                for j in self.around(k, 6 * METRE, NEAR_LIMIT):
                    def infect():
                        t = self.target
                        nm = max(copy_m, t.poison.magnitude if t.poison else 0.0)
                        nr = max(copy_r, t.poison.remaining() if t.poison else 0.0)
                        if factor > 1 and not t.has('Catalyzed'):
                            self.put(t, 'Catalyzed', factor, nr)
                        self.set_poison(nm, nr)
                    self.on(j, infect)
            if burst and not chain and self.has('poison', '毒霧'):
                self.event_at(k, 'Domain', POISON, 5.0, AREA)
        elif element == WATER:
            if reason == CUT and not chain and self.has('water', '大潮'):
                guide = (2.0 if self.has('water', '強引') else 1.5) * self.sig(WATER) * body
                for j in self.around(k, AREA, NEAR_LIMIT, lambda x: x.board.has('Soak')):
                    self.on(j, lambda: self.put(self.target, 'Guided', guide, self.scaled(30.0)))
            if not chain and self.has('water', '洗滌'):
                self.op('event', 'Cleanse', 1.0)
                self.op_at(k, 'wash', 2 * self.bmax(WATER) if self.has('water', '淨潮') else 0.0, 1.0)
            if burst and not chain and self.has('water', '潮池'):
                self.event_at(k, 'Domain', WATER, 5.0, AREA)
        elif element == DARKNESS:
            self.timed(k, 'healRateDebuff', 100.0, 6.0 if self.has('darkness', '不治') else 3.0)
            if not chain and self.has('darkness', '深淵回響'):
                self.magicka_op(self.magicka_max)
            if burst and not chain and self.has('darkness', '死域'):
                self.event_at(k, 'Domain', DARKNESS, 5.0, AREA)
        elif element == ASTRAL:
            if not fused:
                amount = self.bmax(ASTRAL) * (3.0 if self.has('astral', '隕星') else 2.0) * body * self.sig(ASTRAL)
                self.damage(k, ASTRAL, self.react(ASTRAL, amount / self.bmax(ASTRAL), k))
            for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: x.board.has('Star')):
                self.on(j, lambda: self.detonate_stars(1.0))                            # 星落：共鳴目標一起引爆
            if burst and not chain and self.has('astral', '星域'):
                self.event_at(k, 'Domain', ASTRAL, 5.0, AREA)
        if chain:
            return
        if self.has('common', '反哺'):
            self.magicka_op(self.bmax(element))
        grand = self.has('common', '大協奏') and after_switch
        if self.has('common', '連鎖終焉') or grand:
            for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: element in x.board.marks):
                self.chain_end_on(j, element, body * (1.0 if grand else 0.5))

    def fusion_hit(self, k, element, mult):
        """v0.4 2.7 D_burst: B_max × K × G × M_mod (the categorical terms, the target's vulnerabilities); 水斷 heals and
        restores B_max × K × G instead, 星斷 is true damage ×0.6 (G of the astral tree), 血斷 heals 50% of it."""
        if element == WATER and self.has('water', '水斷'):
            amount = self.bmax(WATER) * mult * self.g(WATER)
            self.heal(amount)
            self.stamina_op(amount)
            return
        if element == ASTRAL and self.has('astral', '星斷'):
            self.op_at(k, 'damage', 0, self.bmax(ASTRAL) * mult * 0.6 * self.g(ASTRAL) * self.base)
            return
        amount = self.react(element, mult, k)
        self.damage(k, element, amount)
        if element == BLOOD and self.has('blood', '血斷'):
            self.heal_leech(amount * 0.5)

    def chain_end_on(self, j, element, mult):
        def run():
            t = self.target
            if element not in t.marks:
                return
            del t.marks[element]
            if not t.has('EndCooldown'):
                self.end_body(element, EXPIRE, mult, False, chain=True)
        self.on(j, run)

    # ---------------------------------------------------------------- the pieces the bodies share
    def detonate(self, k, mult, heat, bonus, blaze, mark):
        """爆燃: B_max × 熱度倍率 × (1 + 消耗加成) × 熾焰 × mult × 爆燃 +3%／點; 火葬's marker before the damage."""
        amount = self.react(FIRE, HEAT_BURST[max(0, min(4, heat))] * (1 + bonus) * blaze * mult * self.sig(FIRE), k)
        if mark and self.has('fire', '火葬'):
            self.on(k, lambda: self.put(self.target, 'Cremation', amount, 1.0))
        self.damage(k, FIRE, amount)

    def discharge(self, k, charges, mult, power, crit, jumps):
        """放電: 電荷 × 30% B_max (+1%／點) × R × 暴擊 × mult; 削魔 50%; 跳附近 2 人 40%（電弧 3 人 55%、連鎖 5 人）."""
        if charges <= 0:
            return
        per = 0.3 * (1 + self.pct(self.rank('lightning', '放電每格電荷傷害'), 0.01))
        raw = self.bmax(LIGHTNING) * per * charges * mult * self.sig(LIGHTNING) * power * crit
        self.hit_discharge(k, raw, 1.0)
        if not jumps:
            return
        count, share = 2, 0.4
        if self.has('lightning', '電弧'):
            count, share = 3, 0.55
        if self.has('lightning', '連鎖'):
            count = 5
        for j in self.around(k, NEAR, count):
            self.hit_discharge(j, raw, share)

    def hit_discharge(self, k, raw, share):
        amount = raw * share
        self.damage(k, LIGHTNING, amount * self.rscale(LIGHTNING) * self.vuln(k))
        self.drain_magicka(k, amount * 0.5 * self.g(LIGHTNING))

    def end_crit(self, charges, draw, cut_power):
        crit = draw < 0.05 + 0.02 * charges + (0.15 if self.me.has('QuickShock') else 0.0)
        if cut_power and charges >= self.charge_cap():
            crit = True
        return (2.5 if cut_power else 1.5) if crit else 1.0

    def discharge_all(self, k, charges, mult, power, crit):
        sky = self.rank('lightning', '天雷')
        if sky > 0 and self.sync >= 3:
            # 天雷：放電改為對範圍內（2 m + 0.2 m／點，以你為中心）所有感電目標，不再跳躍
            self.discharge(k, charges, mult, power, crit, False)
            for j in self.around(-1, (2 + 0.2 * sky) * METRE, NEAR_LIMIT, lambda x: LIGHTNING in x.board.marks):
                if j != k:
                    self.discharge(j, charges, mult, 1.0, self.crit_roll(charges), False)
            return
        self.discharge(k, charges, mult, power, crit, True)

    def quake(self, k, mult, knock):
        """地震: 3 m（廣震 5 m）B_max ×1.5（崩裂 ×2.0）、削耐力 B_max ×2（+3%／點，含 G）；削到底的跌倒，其餘減速 30% 3 秒."""
        k1 = (2.0 if self.has('earth', '崩裂') else 1.5) * mult * self.sig(EARTH)
        stamina = self.bmax(EARTH) * 2.0 * (1 + 0.03 * self.rank('earth', '地震耐力削減')) * self.g(EARTH) * mult
        dust = self.has('earth', '塵暴')

        def one(j):
            x = self.members[j]
            self.damage(j, EARTH, self.react(EARTH, k1, j))
            floored = x.body['stamina'] <= stamina * self.drain
            self.drain_stamina(j, stamina)
            if knock and floored and not x.essential and not x.dragon:
                self.event_at(j, 'Knock', 3.0)
            else:
                self.slow(j, 30.0, 3.0)
            if dust:
                self.timed(j, 'meleeDebuff', 20.0, 3.0)
        one(k)
        for j in self.around(k, self.quake_radius(), NEAR_LIMIT):
            one(j)

    def blade(self, k, mult):
        amount = self.bmax(WIND) * 1.0 * mult * (1 + self.pct(self.rank('wind', '風刃傷害'), 0.02))
        self.blade_one(k, amount)
        if self.has('wind', '迴旋'):
            for j in self.around(k, NEAR, 2):
                self.blade_one(j, amount)

    def blade_one(self, k, amount):
        b = self.members[k].board
        unbalanced = 1.3 if b.has('Unbalance') else 1.0
        self.damage(k, WIND, amount * unbalanced * self.rscale(WIND) * self.vuln(k))
        if self.has('wind', '追風'):
            self.stamina_op(3.0)
            self.on(k, lambda: self.put(self.target, 'Unbalance', 1, self.scaled(3.0)))
        if self.has('wind', '空中追擊') and b.has('Airborne'):
            self.push(k, 4, 1.0, self.landing_stored(), 0, False)

    def wind_end(self, k, mult, reason):
        self.blade(k, mult)
        if reason == BURST or self.has('wind', '上天'):
            self.push(k, 4, 1.0, self.landing_stored(), 0, True)                         # 吹上天
        else:
            self.push(k, 1, 3.0, 0.0, 0, True)                                             # 吹飛 3 m
        for j in self.around(k, NEAR, 5 if self.has('wind', '亂流') else 2):
            self.blade(j, mult)

    def surge(self, k, remaining, mult, reason, chain):
        """血潮: (流血剩餘 × 血位曲線 + 當前生命 10%〔首領 3%〕) × 血潮 +3%／點；治療＝× 吸血 × 2（+0.1／點）."""
        m = self.members[k]
        surge = mult
        if self.has('blood', '血契') and self.fraction() >= 0.7:
            self.op('pay', self.hp_max * 0.10)
            surge *= 2.0
        bleed = remaining * (1.5 if self.has('blood', '飽飲') else 1.0) * interpolate(self.curve_fraction(), HIT_CURVE)
        pct = 0.03 if m.body['vip'] else 0.10
        if self.has('blood', '放血終焉'):
            pct *= 2
        health = m.body['health'] * pct * self.base
        amount = (bleed + health) * surge * self.sig(BLOOD) * self.vuln(k)
        self.damage(k, BLOOD, amount)
        self.heal_leech(amount * self.leech() * (2.0 + 0.1 * self.rank('blood', '血潮治療倍率 ×2')))
        sea = self.rank('blood', '血海')
        if sea > 0 and self.sync >= 3 and not chain:
            for j in self.around(k, (1 + 0.2 * sea) * METRE, NEAR_LIMIT, lambda x: x.board.has('Bleed')):
                self.surge_on(j, mult, True)

    def surge_on(self, k, mult, clear):
        b = self.members[k].board
        remaining = b.bleed.magnitude * b.bleed.remaining() if b.bleed else 0.0
        if clear:
            def run():
                t = self.target
                if t.bleed:
                    self.op('bleedDot', 0.0, 0.0)
                    t.bleed = None
                self.drop(t, 'Bleed')
            self.on(k, run)
        self.surge(k, remaining, mult, EXPIRE, True)

    def judge_area(self, k, mult, holy):
        punish = self.me.layers('Punish')
        if punish > 0:
            self.drop(self.me, 'Punish')
        bonus = 0.2 * punish                                                               # 懲戒 +20%／層
        self.judge(k, mult * (1 + bonus), holy)
        if punish > 0 and self.has('divine', '天誅'):
            for j in self.around(k, AREA, NEAR_LIMIT):
                self.judge(j, mult * bonus, holy, heal=False)
        apocalypse = self.rank('divine', '天啟')
        wide = self.has('divine', '廣裁')
        radius = 0.0
        if apocalypse > 0 and self.sync >= 3:
            radius = max((1 + 0.2 * apocalypse) * METRE, AREA if wide else 0.0)
        elif wide:
            radius = AREA
        if radius > 0:
            for j in self.around(k, radius, NEAR_LIMIT):
                self.judge(j, mult * (1 + bonus), holy)
        if self.has('divine', '光耀'):
            def mark(j):
                self.on(j, lambda: self.put(self.target, 'Radiance', 1, self.scaled(5.0)))
            if self.members[k].body['undead']:
                mark(k)
            for j in self.around(k, AREA, CROWD_MAX, lambda x: x.body['undead']):
                mark(j)

    def judge(self, k, mult, holy, heal=True):
        """裁決 B_max ×2.0（重裁 ×3.0）× (1 + 聖印 20% [+ 聖痕 10%]) × (1 + 聖佑階) × 亡靈 ×3；治療你 B_max."""
        m = self.members[k]
        marked = DIVINE in m.board.marks
        vulnerability = 1.0
        if marked:
            vulnerability += 0.2
            if self.has('divine', '聖痕') and not m.body['undead']:
                vulnerability += 0.1
        tier = HOLY_PROC[max(0, min(3, holy))] + self.pct(self.rank('divine', '聖佑各階武器傷害與聖傷加成'), 0.01) * holy
        amount = self.react(DIVINE, (3.0 if self.has('divine', '重裁') else 2.0) * mult * self.sig(DIVINE) * vulnerability *
                            (1 + tier), k)
        if m.body['undead'] or (self.has('divine', '聖痕') and marked):
            amount *= 3
        self.damage(k, DIVINE, amount)
        if heal:
            self.heal(self.bmax(DIVINE) * 1.0)

    def shatter_area(self, k):
        for j in self.around(k, AREA, NEAR_LIMIT, lambda x: x.board.has('Frozen')):
            self.on(j, lambda: self.shatter(3))

    # ---------------------------------------------------------------- the other body events
    def frozen_body(self, k, seconds):
        slow = 50.0 + (2.0 * self.rank('frost', '絕對零度') if self.sync >= 3 else 0.0)
        self.op_at(k, 'slow', slow, seconds)
        if self.has('frost', '深寒'):
            self.timed_raw(k, 'meleeDebuff', 20.0, seconds)
            self.timed_raw(k, 'staminaRateDebuff', 100.0, seconds)
        if self.has('frost', '霜爆'):
            for j in self.around(k, AREA, NEAR_LIMIT, lambda x: x.board.layers('Freeze') >= 1):
                self.on(j, lambda: self.add_freeze(2.0))

    def hallucinate_body(self, k, kind):
        if kind == 1 and self.has('darkness', '夢魘'):
            for j in self.around(k, AREA, NEAR_LIMIT):
                self.on(j, lambda: self.add_curse(1))
        if kind == 2 and self.has('darkness', '群魔') and self.sync >= 3:
            for j in self.around(k, 4 * METRE, NEAR_LIMIT,
                                 lambda x: x.board.layers('Curse') >= 3 and not x.board.has('FrenzyCooldown')):
                self.on(j, lambda: self.put(self.target, 'FrenzyCooldown', 1, self.cooldown(20.0)))
                self.event_at(j, 'Hallucinate', 2, self.scaled(3.0), 1)

    def judgment_body(self, k, tier, damage):
        self.timed(k, 'armorDebuff', 60.0, 5.0)                                            # 破防：護甲 -60
        self.timed(k, 'magicResistDebuff', 10.0, 5.0)                                      #       魔抗 -10%
        if tier < 3:
            return
        for j in self.around(k, AREA, NEAR_LIMIT):
            blast = self.react(DIVINE, 0.5, j) * (3.0 if self.members[j].body['undead'] else 1.0)
            self.damage(j, DIVINE, blast)                                                  # 聖光爆 B_max ×0.5
        if self.has('divine', '破邪斬') and damage > 0:
            main = self.members[k]
            plain = damage / max(0.001, self.vuln(k) * (3.0 if main.body['undead'] else 1.0))
            for j in self.around(k, 4 * METRE, NEAR_LIMIT):
                splash = plain * 0.5 * self.vuln(j) * (3.0 if self.members[j].body['undead'] else 1.0)
                self.damage(j, DIVINE, splash)

    def splash_body(self):
        for j in self.around(-1, NEAR, NEAR_LIMIT, lambda x: x.board.has('Bleed')):
            self.surge_on(j, 0.5, False)                                                   # 濺血 ×0.5，不清血痕

    def rise_body(self):
        if not self.has('blood', '血約'):
            return
        for j in self.around(-1, NEAR, NEAR_LIMIT, lambda x: x.board.has('Bleed')):
            self.on(j, lambda: self.add_bleed(2))

    def shattered_body(self, k, source):
        m = self.members[k]
        if m.armor > 0:
            self.timed(k, 'armorDebuff', m.armor * (0.2 if self.has('frost', '碎甲加深') else 0.1), 5.0)
        if self.has('frost', '冰崩') and source != 3:
            self.shatter_area(k)

    def landing_body(self, k, stored):
        self.damage(k, WIND, stored * self.rscale(WIND) * self.vuln(k))

    def overheat_body(self):
        for j in self.around(-1, NEAR, NEAR_LIMIT, lambda x: FIRE in x.board.marks):
            self.chain_end_on(j, FIRE, 1.0)

    # ---------------------------------------------------------------- the body pass
    def consume(self, i):
        self.ops[i] = ['noop']

    def run_bodies(self, start):
        i = start
        while i < len(self.ops):
            row, k = self.ops[i], self.src[i]
            present = 0 <= k < len(self.members) and self.members[k].has
            name = row[0]
            if name == 'event':
                ev = row[1]
                a = [float(x) for x in row[2:]] + [0.0] * 8
                if ev == 'Open':
                    if present:
                        self.open_body(k, int(a[0] + 0.5), a[1], int(a[2] + 0.5), a[3] > 0.5)
                elif ev == 'End':
                    if present:
                        self.end_event_body(k, int(a[0] + 0.5), int(a[1] + 0.5), a[2], int(a[3] + 0.5), a[4], a[5], a[6],
                                            int(a[7] + 0.5))
                elif ev == 'Hallucinate':
                    if present and a[2] < 0.5:
                        self.hallucinate_body(k, int(a[0] + 0.5))
                elif ev in BODY_ONLY:
                    if ev == 'Frozen' and present:
                        self.frozen_body(k, a[0])
                    elif ev == 'Judgment' and present:
                        self.judgment_body(k, int(a[0] + 0.5), a[1])
                    elif ev == 'Splash':
                        self.splash_body()
                    elif ev == 'Rise':
                        self.rise_body()
                    elif ev == 'Shatter' and present:
                        self.shattered_body(k, int(a[0] + 0.5))
                    elif ev == 'Landing' and present:
                        self.landing_body(k, a[0])
                    elif ev == 'Discharge' and present:
                        self.discharge_all(k, int(a[0] + 0.5), a[1], a[2], a[3] if a[3] > 0 else 1.0)
                    elif ev == 'Blade' and present:
                        for _ in range(int(a[0] + 0.5)):
                            self.blade(k, a[1])
                    elif ev == 'Overheat':
                        self.overheat_body()
                    self.consume(i)
            elif name == 'resonance':
                # 共鳴層 (2.3): the detonator and the resonance targets within 15 m of it (at most 8 counted)
                count = 1 + (len(self.around(k, NEAR, 8, lambda x: x.board.has('Star'))) if present else 0)
                self.add_resonance(max(1, min(count, 8)))
                self.consume(i)
            elif name == 'damage' and self.tags.get(i) == 'star' and present and self.has('astral', '聚星'):
                if 1 + len(self.around(k, NEAR, CROWD_MAX, lambda x: x.board.has('Star'))) >= 3:
                    row[2] *= 1.3                                                           # 聚星 +30%
            elif name == 'damage' and self.tags.get(i) == 'dark' and present and self.has('astral', '星蝕'):
                for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: x.board.has('Star')):
                    self.damage(j, ASTRAL, row[2] * 0.5)                                    # 星蝕 50%
            elif name == 'crush':
                if present:
                    magnitude, stamina = row[1], row[2]
                    for j in self.around(k, AREA, 5):
                        x = self.members[j]
                        floored = x.body['stamina'] <= stamina
                        self.damage(j, EARTH, magnitude * self.vuln(j))
                        self.op_at(j, 'drainStamina', stamina)
                        if floored and not x.essential and not x.dragon:
                            self.event_at(j, 'Knock', 3.0)
                self.consume(i)
            elif name == 'freezeNearby':
                for j in self.around(-1, NEAR, NEAR_LIMIT, lambda x: x.board.layers('Freeze') >= 1 and not x.board.has('Frozen')):
                    self.on(j, lambda: self.freeze(self.frozen_seconds(), 1.0))              # 冰心
                self.consume(i)
            i += 1

    # ---------------------------------------------------------------- the hit's branch bodies, echo
    def hit_bodies(self, element, power, silence):
        m = self.members[0]
        if not m.has:
            return
        b = m.board
        if element == EARTH:
            if power and self.has('earth', '震擊') and b.has('Fissure'):
                self.damage(0, EARTH, self.react(EARTH, 1.5, 0))
                self.drain_stamina(0, 50.0)
                self.on(0, lambda: self.drop(self.target, 'Fissure'))
        elif element == DIVINE:
            if self.has('divine', '護持'):
                self.timed(0, 'magicResistBuff', 10.0, 3.0)
        elif element == POISON:
            outer = self.at
            self.select(0)
            per, f = self.per_dose(), self.factor()
            self.select(outer)
            doses = int(b.poison.magnitude / f / per + 0.001) if b.poison and per > 0 else 0
            if doses >= 5 and self.has('poison', '萎靡'):
                self.timed(0, 'meleeDebuff', 15.0, 3.0)
            if doses >= 10 and self.has('poison', '侵蝕'):
                self.timed(0, 'poisonResistDebuff', 20.0, 6.0)
        elif element == DARKNESS:
            curse = b.layers('Curse')
            if curse > 0:
                amount = curse * (2.0 + 0.2 * self.rank('darkness', '詛咒每層抗性侵蝕')) * self.omni()
                for kind in ('fireResistDebuff', 'frostResistDebuff', 'shockResistDebuff', 'magicResistDebuff',
                             'poisonResistDebuff'):
                    self.timed(0, kind, amount, 8.0)
        if silence > 0 and self.has('noform', '封印'):
            for j in self.around(0, AREA, NEAR_LIMIT):
                self.op_at(j, 'silence', float(silence))

    def echo(self, k, proc):
        ratio = 0.25 + 0.01 * self.rank('astral', '回聲比例')
        if self.night and not self.interior:
            ratio *= 1.5
        for j in self.around(k, NEAR, NEAR_LIMIT, lambda x: x.board.has('Star')):
            self.op_at(j, 'damage', ASTRAL, proc * ratio)
            b = self.members[j].board
            if self.has('astral', '星鏈') and not b.has('StarChainCooldown'):
                self.select(j)
                layers = min(self.star_cap(), b.layers('Star') + 1)
                self.select(0)
                b.kinds['Star'] = Slot(layers, 0, b.kinds['Star'].remaining())               # 不重算引信
                self.put(b, 'StarChainCooldown', 1, self.cooldown(2.0))

    # ---------------------------------------------------------------- 融斷 (2.5, 5.1, 5.2)
    def give_magicka(self, amount):
        into = min(amount, max(0.0, self.magicka_max - self.magicka))
        if into > 0:
            self.op('magicka', into)
        over = amount - into
        if over > 0:
            pool = self.me.mag('Overload') if self.me.has('Overload') else 0.0
            self.set_overload(min(pool + over, self.overload_cap()), True)

    def burst_radius(self):
        return (20 * METRE if self.has('noform', '收束') else NEAR) + 0.3 * METRE * self.rank('noform', '融斷範圍')

    def burst_mult(self, stage):
        common = 1 + self.pct(self.rank('common', '融斷'), 0.01) + self.pct(self.rank('common', '融斷再'), 0.02)
        quiet = 1 + self.pct(self.rank('noform', '融斷'), 0.02) + self.pct(self.rank('noform', '融斷再'), 0.03)
        return SYNC_K[max(0, min(3, stage))] * common * quiet

    def burst(self, stage, form):
        start = len(self.ops)
        radius, mult = self.burst_radius(), self.burst_mult(stage)
        hush_cap = 5 + min(3, self.rank('noform', '寂上限') // 5)
        burn = 0.05 + 0.005 * self.rank('noform', '寂每層燒魔')
        settled_elements, backflow, earth = set(), [0.0], [False]
        stars = self.around(-1, radius, CROWD_MAX, lambda x: ASTRAL in x.board.marks)
        wind_marked = {k for k, m in enumerate(self.members) if WIND in m.board.marks}
        for k in self.around(-1, radius, CROWD_MAX, lambda x: x.board.marks or x.board.has('Residual')):
            m = self.members[k]
            settled = [0]

            def state():
                t = self.target
                allowed = not t.has('EndCooldown')

                def settle(e):
                    if allowed:
                        before = len(self.ops)
                        self.end_body(e, BURST, 1.0)                                 # the state part ×1
                        for row in self.ops[before:]:
                            if row[0] == 'event' and row[1] == 'End' and int(row[2] + 0.5) == e:
                                row[4] *= mult                                         # K for the fusion hit
                        settled[0] += 1
                        settled_elements.add(e)
                        backflow[0] += self.bmax(e) * 0.5
                        earth[0] = earth[0] or e == EARTH
                for e in range(FIRE, ASTRAL + 1):
                    if e in t.marks:
                        del t.marks[e]
                        settle(e)
                if t.has('Residual'):
                    residual = t.layers('Residual')
                    self.drop(t, 'Residual')
                    if 1 <= residual <= 11:
                        settle(residual)
            self.on(k, state)
            if settled[0] == 0:
                continue
            before = m.board.hush.layers() if m.board.hush else 0
            layers = min(hush_cap, before + settled[0])
            gained = layers - before
            if gained > 0 and m.magicka_max > 0:
                self.drain_magicka(k, m.magicka_max * burn * gained)                        # 寂：每層燒最大魔力 5%
            if self.has('noform', '萬寂') and layers >= 3:
                cleared = [0]

                def all_hush():
                    t = self.target

                    def take(present, element, clear):
                        if not present:
                            return
                        clear()
                        cleared[0] += 1
                        self.op('damage', 0, self.bmax(element) * 0.5 * self.g_noform() * self.base)

                    def frost():
                        for kind in ('Freeze', 'Frozen', 'Crystal'):
                            self.drop(t, kind)

                    def blood():
                        self.drop(t, 'Bleed')
                        if t.bleed:
                            self.op('bleedDot', 0.0, 0.0)
                            t.bleed = None

                    def poison():
                        self.op('poisonDot', 0.0, 0.0)
                        t.poison = None
                        self.drop(t, 'Catalyzed')
                    take(t.has('Freeze') or t.has('Frozen') or t.has('Crystal'), FROST, frost)
                    take(t.has('Curse'), DARKNESS, lambda: self.drop(t, 'Curse'))
                    take(t.has('Bleed') or t.bleed is not None, BLOOD, blood)
                    take(t.poison is not None, POISON, poison)
                    take(t.has('Pressure') or t.has('Soak'), WATER, lambda: (self.drop(t, 'Pressure'), self.drop(t, 'Soak')))
                    take(t.has('Star'), ASTRAL, lambda: (self.drop(t, 'Star'), self.drop(t, 'StarFuse')))
                    take(t.has('Fissure') or t.has('Downed'), EARTH, lambda: (self.drop(t, 'Fissure'), self.drop(t, 'Downed')))
                    take(t.has('Unbalance'), WIND, lambda: self.drop(t, 'Unbalance'))
                self.on(k, all_hush)
                layers = min(hush_cap, layers + cleared[0])
            self.op_at(k, 'hush', float(layers))
            m.board.hush = Slot(layers, 0, 10.0)
        cosmos = self.me.layers('Cosmos')
        if cosmos > 0 and self.has('astral', '墜星'):
            for k in stars:
                outer = self.at
                self.select(k)
                strike = self.dark_strike(False)
                self.select(outer)
                self.damage(k, ASTRAL, cosmos / len(stars) * 0.5 * strike)                  # 墜星：闇宙均分，每層 ×0.5
        if self.has('noform', '斷界'):
            for k in self.around(-1, radius, CROWD_MAX):
                done = set()
                for e in sorted(settled_elements):
                    kind = {FIRE: 'fireResistDebuff', FROST: 'frostResistDebuff', LIGHTNING: 'shockResistDebuff',
                            POISON: 'poisonResistDebuff'}.get(e, 'magicResistDebuff')
                    if kind not in done:
                        done.add(kind)
                        self.timed(k, kind, 10.0, 3.0)
        if earth[0] and self.has('earth', '地斷'):
            for k in self.around(-1, radius, CROWD_MAX, lambda x: x.body['stamina_max'] > 0 and
                                 x.body['stamina'] / x.body['stamina_max'] < 0.3 and not x.essential and not x.dragon):
                self.event_at(k, 'Knock', 3.0)
        if self.has('wind', '颶風'):
            for k in self.around(-1, radius, NEAR_LIMIT):
                if k not in wind_marked:
                    self.push(k, 4, 1.0, self.landing_stored(), 0, True)
        if self.has('noform', '回流') and backflow[0] > 0:
            self.give_magicka(backflow[0] * self.recovery)
        if self.has('noform', '雙斷'):
            self.put(self.me, 'DoubleBurst', 1, self.scaled(3.0))
        if self.has('common', '安全閥'):
            self.put(self.me, 'SafetyValve', 1, self.scaled(2.0))
        self.run_bodies(start)

    # ---------------------------------------------------------------- death (2.6, 2.7, 5.x)
    def judge_raise(self, facts):
        m = self.members[0]
        b = m.board
        summon = b.has('CurseKill') and self.has('darkness', '冥召')
        lord = self.has('darkness', '死靈主') and self.sync >= 3
        marked = DARKNESS in b.marks or b.has('Nether') or (facts.get('killer_frenzied') and self.has('darkness', '狂宴'))
        if (not marked and not summon) or m.essential or m.dragon or facts.get('servant'):
            return None
        curse = b.layers('Curse')
        ok = curse >= 3 or summon or lord
        if not ok and curse >= 1 and self.has('darkness', '殘魂'):
            ok = self.chance(0.25)
        if not ok:
            return None
        lv = m.level
        tier = 1 if lv <= 6 else 2 if lv <= 13 else 3 if lv <= 21 else 4 if lv <= 30 else 5 if lv <= 60 else 6
        if tier == 6 and not lord:
            return None
        attack = 0.0
        if tier <= 5:
            if curse >= 5:
                tier = min(5, tier + 1)
                attack = 0.1 * curse
            if summon:
                tier = min(5, tier + 1)
        final = 6 if lord else tier
        seconds = TIER_SECONDS[5] if lord else TIER_SECONDS[tier - 1] * (2.0 if curse >= facts.get('curse_cap', 5) else 1.0)
        return final, TIER_CAP[final - 1], seconds, attack, 1 if lord else 0

    def death(self, facts):
        start = len(self.ops)
        self.select(0)
        corpse = self.members[0]
        cb = corpse.board
        you = facts.get('killer_you', False)
        bleeding = cb.has('Bleed') or cb.bleed is not None
        pure_land = self.has('divine', '淨土') and self.sync >= 3 and you and self.form == DIVINE
        if (DIVINE in cb.marks or pure_land) and not corpse.essential and not corpse.dragon and not facts.get('servant'):
            self.op('event', 'Ash')                                                        # 化灰
            if self.has('divine', '聖灰'):
                self.magicka_op(self.bmax(DIVINE) * 2.0)
            if self.has('divine', '淨灰') and corpse.body['undead'] and DIVINE in cb.marks:
                for j in self.around(0, NEAR, NEAR_LIMIT, lambda x: x.body['undead']):
                    self.damage(j, DIVINE, self.react(DIVINE, 1.0, j))
        else:
            r = self.judge_raise(facts)
            if r:
                self.op('event', 'Raise', *[float(x) for x in r])                          # 亡者歸來
        if cb.poison:
            # 2.7 中毒死亡擴散：S = max(R, 最大生命 × 30%) × 50%（蔓延 75%），15 公尺內不限人數
            share = max(cb.poison.magnitude * cb.poison.remaining(), corpse.body['health_max'] * 0.3) * \
                (0.75 if self.has('poison', '蔓延') else 0.5)
            per_second = share / 12.0
            for j in self.around(0, NEAR, CROWD_MAX):
                def spread():
                    t = self.target
                    cap = 10 * self.per_dose() * self.factor()
                    now = t.poison.remaining() if t.poison else 0.0
                    if per_second > cap:
                        self.set_poison(cap, max(now, share / cap))
                    else:
                        self.set_poison(min((t.poison.magnitude if t.poison else 0.0) + per_second, cap),
                                        max(now, self.scaled(12.0)))
                self.on(j, spread)
        if cb.has('Frozen') and self.has('frost', '連鎖冰封'):
            for j in self.around(0, NEAR, NEAR_LIMIT):
                self.on(j, lambda: self.add_freeze(3.0))
                self.slow(j, 30.0, 3.0)
        if cb.has('Cremation') and self.has('fire', '火葬'):
            for j in self.around(0, NEAR, NEAR_LIMIT):
                self.damage(j, FIRE, cb.mag('Cremation') * 0.5)
        if cb.has('CurseKill') and self.has('darkness', '亡魂'):
            for j in self.around(0, NEAR, NEAR_LIMIT):
                self.event_at(j, 'Hallucinate', 1, self.scaled(2.0), 1)
        if facts.get('servant') and self.has('darkness', '亡衛') and self.sync >= 3:
            for j in self.around(0, AREA, NEAR_LIMIT):
                self.damage(j, DARKNESS, self.react(DARKNESS, 1.0, j))
                self.on(j, lambda: self.add_curse(2))
        me = self.me
        if you and bleeding:
            if self.has('blood', '飲血'):
                self.op('heal', self.hp_max * 0.2 * self.recovery)
                self.put(me, 'Bloodthirst', 1, self.scaled(10.0))
            if self.has('blood', '血承'):
                for i, kind in enumerate(INHERIT):
                    v = corpse.resist[i] * 0.5
                    if v > 0:
                        self.put(me, kind, v, 15.0)
                    else:
                        self.drop(me, kind)
                armor = corpse.armor * 0.2 * self.recovery
                if armor > 0:
                    self.put(me, 'InheritArmor', armor, 15.0)
                self.put(me, 'InheritHealth', corpse.body['health_max'] * 0.1 * self.recovery, 15.0)
        if bleeding and self.has('blood', '不死') and self.sync >= 3 and not me.has('UndyingCooldown'):
            self.put(me, 'UndyingCooldown', 1, self.cooldown(30.0))
            self.op('stamina', max(0.0, self.stamina_max - self.stamina))
            f = self.fraction()
            line = 0.3 if f < 0.3 else 0.7 if f < 0.7 else 0.0
            if line > 0:
                wanted = line * self.hp_max + 1.0
                if wanted > self.hp:
                    self.op('heal', wanted - self.hp)
                self.put(me, 'BloodZone', 2 if line == 0.3 else 1, 86400.0)
            self.put(me, 'SurgeUp', 1, self.scaled(8.0))
            self.op('event', 'Rise')
        if you and corpse.spell_user and self.has('noform', '無魔'):
            self.op('stamina', max(0.0, self.stamina_max - self.stamina))
            self.give_magicka(self.magicka_max)
        if (you and self.has('wind', '連殺') and WIND in cb.marks and cb.has('LastHitSneak') and
                cb.layers('LastHitSneak') == WIND):
            self.op('event', 'Sneak', self.scaled(5.0))
            self.put(me, 'KillStreak', 1, self.scaled(5.0))
        self.run_bodies(start)

    # ---------------------------------------------------------------- X臨, 印潮, 化身
    def open_forced(self, k, element):
        def run():
            before = len(self.ops)
            self.hit(element, False, hit_work=False)
            if any(r[0] == 'event' and r[1] == 'Open' and r[2] == element for r in self.ops[before:]):
                self.self_open(element)
        self.on(k, run)

    def advent(self, element):
        start = len(self.ops)
        tree = TREE[element]
        label = _LABELED_ADVENT[tree]
        rank = self.rank(tree, label)
        radius = (2 + 0.2 * rank) * METRE
        for k in self.around(-1, radius, CROWD_MAX):
            if rank > 0:
                self.open_forced(k, element)
            if element == FROST and rank > 0 and self.has('frost', '冰臨強化'):
                self.slow(k, 30.0, 3.0)
            elif element == EARTH and self.has('earth', '地臨強化'):
                self.op_at(k, 'drainStamina', self.members[k].body['stamina_max'] * 0.5)
            elif element == POISON and self.has('poison', '毒臨強化'):
                self.on(k, lambda: self.spread_doses(3.0))
            elif element == WATER and self.has('water', '水臨強化'):
                self.on(k, lambda: self.put(self.target, 'Soak', 1, self.soak_seconds()))
                self.op_at(k, 'slow', self.soak_slow(), self.soak_seconds())
            elif element == DARKNESS and self.has('darkness', '暗臨強化'):
                self.event_at(k, 'Hallucinate', 1, self.scaled(2.0), 1)
            elif element == ASTRAL and self.has('astral', '星臨強化'):
                self.on(k, lambda: self.add_stars(2))
        if element == WATER and self.has('water', '水臨強化'):
            self.op('event', 'Cleanse', 1.0)
            self.op('magicka', max(0.0, self.magicka_max - self.magicka))
        if element == BLOOD and self.has('blood', '血臨強化'):
            self.op('pay', self.hp_max * 0.15)
            self.op('event', 'Splash')
        if self.has('common', '臨界'):
            for k in self.around(-1, NEAR, NEAR_LIMIT):
                self.slow(k, 30.0, 2.0)
        if self.me.has('DoubleBurst'):
            self.drop(self.me, 'DoubleBurst')
            for k in self.around(-1, self.burst_radius(), CROWD_MAX):
                if not (rank > 0 and distance(self.you, self.members[k].pos) <= radius):
                    self.open_forced(k, element)
        self.run_bodies(start)

    def surge_open(self, element, old):
        if not self.has('common', '印潮') or not 1 <= old <= 11:
            return
        for k in self.around(0, NEAR, 2, lambda x: old in x.board.marks):
            self.open_forced(k, element)

    def avatar(self, element):
        if not self.members[0].has:
            return
        if element == LIGHTNING:
            n = self.me.layers('Charge')
            self.discharge_all(0, n, 1.0, 1.0, self.crit_roll(n))
        elif element == BLOOD:
            self.surge_on(0, 1.0, True)
        elif element == DIVINE:
            self.judge_area(0, 1.0, self.holy_tier())

    # ---------------------------------------------------------------- the table row
    def summary24(self):
        def board(b):
            out = {k: [round(s.magnitude, 5), round(s.remaining(), 5)] for k, s in b.kinds.items()}
            out.update({f'Mark{e}': [round(s.magnitude, 5), round(s.remaining(), 5)] for e, s in b.marks.items()})
            if b.bleed:
                out['BleedDot'] = [round(b.bleed.magnitude, 5), round(b.bleed.remaining(), 5)]
            if b.poison:
                out['PoisonDot'] = [round(b.poison.magnitude, 5), round(b.poison.remaining(), 5)]
            if getattr(b, 'hush', None):
                out['Hush'] = [round(b.hush.magnitude, 5), round(b.hush.remaining(), 5)]
            return out
        ops = []
        for row, at in zip(self.ops, self.ats):
            name = row[0]
            if name in DROPPED:
                continue
            if name == 'event':
                args = [float(x) for x in row[2:]] + [0.0] * 8
                ops.append(['event', at, row[1]] + [round(x, 5) for x in args[:EVENT_ARGS[row[1]]]])
            elif name == 'timed':
                ops.append(['timed', at, row[1]] + [round(float(x), 5) for x in row[2:]])
            else:
                values = [round(float(x), 5) for x in row[1:]]
                if name == 'wash' and len(values) == 1:
                    values.append(0.0)                                                    # the status layer's wash: all buffs
                ops.append([name, at] + values)
        return dict(members=[board(m.board) for m in self.members], me=board(self.me),
                    ops=sorted(ops, key=lambda r: [str(x) for x in r]))


_LABELED_ADVENT = LABELED['kAdvent'][2]


def run_steps(w, steps):
    for step in steps:
        kind = step[0]
        if kind == 'event':
            start = len(w.ops)
            w.event_at(step[1], step[2], *step[3:])
            w.run_bodies(start)
        elif kind == 'op':
            start = len(w.ops)
            at, what = step[1], step[2]
            if what == 'resonance':
                w.op_at(at, 'resonance')
            elif what == 'crush':
                w.op_at(at, 'crush', float(step[3]), float(step[4]))
            elif what == 'freezeNearby':
                w.op_at(at, 'freezeNearby')
            elif what in ('starBurst', 'darkStrike'):
                w.op_at(at, 'damage', ASTRAL, float(step[3]))
                w.tags[len(w.ops) - 1] = 'star' if what == 'starBurst' else 'dark'
            else:
                raise ValueError(step)
            w.run_bodies(start)
        elif kind == 'burst':
            w.burst(step[1], step[2])
        elif kind == 'death':
            w.death(step[1])
        elif kind == 'advent':
            w.advent(step[1])
        elif kind == 'echo':
            w.echo(step[1], step[2])
        elif kind == 'hitBodies':
            start = len(w.ops)
            w.hit_bodies(step[1], step[2], step[3])
            w.run_bodies(start)
        elif kind == 'surge':
            start = len(w.ops)
            w.surge_open(step[1], step[2])
            w.run_bodies(start)
        elif kind == 'avatar':
            start = len(w.ops)
            w.avatar(step[1])
            w.run_bodies(start)
        else:
            raise ValueError(step)


def build_world(damage, spec):
    t, f = spec.get('tuning', {}), spec.get('facts', {})
    levels = {TREE_IDS[i]: lv for i, lv in spec.get('levels', [])}
    w = World24(damage, spec['crowd'], stamina=f.get('stamina', 100.0), stamina_max=f.get('stamina_max', 100.0),
                magicka=f.get('magicka', 100.0), sneak=f.get('sneak', False), bloodthirst=f.get('bloodthirst', False),
                rng=f.get('rng', 'mid'), form=f.get('form', 0), magicka_max=f.get('magicka_max', 100.0),
                ranks=spec.get('ranks', {}), branches=spec.get('branches', set()), sync=t.get('syncStage', 0),
                mult_duration=t.get('multDuration', 1.0), mult_cooldown=t.get('multCooldown', 1.0),
                node_scale=t.get('nodeScale', 3.0), base=t.get('baseDamageMult', 1.0), recovery=t.get('multRecovery', 1.0),
                mult_dot=t.get('multDot', 1.0), night=t.get('envNight', False), interior=f.get('interior', False),
                slow_cap=t.get('slowCapPct', 70.0), wet_slow=t.get('wetSlowPct', 15.0), level=levels,
                hp=f.get('hp', 100.0), hp_max=f.get('hp_max', 100.0))
    w.drain = t.get('multDrain', 1.0)
    w.frost_open_slow = t.get('frostOpenSlowPct', 25.0)
    w.water_open_stamina = t.get('waterOpenStamina', 80.0)
    seed_board(w.me, spec.get('me', {}))
    return w


TREE_IDS = ['fire', 'frost', 'lightning', 'earth', 'wind', 'blood', 'divine', 'poison', 'water', 'darkness', 'astral', 'noform',
            'common']


def evaluate(damage, spec):
    w = build_world(damage, spec)
    run_steps(w, spec['steps'])
    return w.summary24()


# ================================================================ the scenarios
# You stand at the origin; positions are game units (70 = 1 m). Member 0 is the event's actor. Allies, empty slots and
# actors beyond a range are placed on purpose: no body may ever pick them (2.9).

def _m(x, y=0.0, **kw):
    d = dict(pos=[float(x), float(y), 0.0])
    d.update(kw)
    return d


def _c(*members):
    return dict(you=[0.0, 0.0, 0.0], members=list(members))


def _b(tree, *names):
    return {(tree, n) for n in names}


def _r(tree, **ranks):
    return {(tree, n): v for n, v in ranks.items()}


def _mark(e, seconds=8.0, flags=0):
    return {f'Mark{e}': [flags, 0.0, seconds]}


def _k(**kinds):
    return {k: list(v) for k, v in kinds.items()}


def _end(at, element, reason, mult=1.0, flags=0, v1=0.0, v2=0.0, v3=0.0, charge=0):
    return ['event', at, 'End', element, reason, mult, flags, v1, v2, v3, charge]


def _open(at, element, mult=1.0, cut_from=0, from_hit=1):
    return ['event', at, 'Open', element, mult, cut_from, from_hit]


def _spec(name, crowd, steps, *, branches=(), ranks=None, tuning=None, facts=None, me=None, levels=()):
    return dict(name=name, crowd=crowd, steps=steps, branches=set(branches), ranks=dict(ranks or {}), tuning=dict(tuning or {}),
                facts=dict(facts or {}), me=dict(me or {}), levels=[list(x) for x in levels])


ALLY = dict(ally=True)
GONE = dict(has=False)


def scenario_specs():
    S = []
    add = S.append
    # ---------------------------------------------------------------- open bodies (2.6 開印 + the open branches)
    add(_spec('fire open: 點燃 ×0.5, 餘熱, 先燃 at sync 3 on your 灼熱',
              _c(_m(100), _m(300)), [_open(0, FIRE)], branches=_b('fire', '餘熱', '先燃'), tuning=dict(syncStage=3),
              me=_k(Heat2=(1, 0, 3600), HeatDecay=(1, 0, 6))))
    add(_spec('frost open: 霜結 25% 3 s; 寒潮 the nearest other +2 (the ally, the empty and the far never)',
              _c(_m(100), _m(400), _m(900), _m(200, **ALLY), _m(150, **GONE), _m(2000)), [_open(0, FROST)],
              branches=_b('frost', '寒潮')))
    add(_spec('lightning open: 感電 drain, 傳導 onto the unmarked, 充能開印, 感電削弱, 雷閃',
              _c(_m(100), _m(300), _m(200, board=_mark(FIRE))), [_open(0, LIGHTNING)],
              branches=_b('lightning', '傳導', '充能開印', '感電削弱', '雷閃')))
    add(_spec('lightning open with 雙印: 傳導 may join a single other mark',
              _c(_m(100), _m(200, board=_mark(FIRE)), _m(300)), [_open(0, LIGHTNING)],
              branches=_b('lightning', '傳導') | _b('common', '雙印')))
    add(_spec('earth open: 裂痕 (裂痕護甲削減 5), 震波, 地基, 深裂痕 knocks a tired target',
              _c(_m(100, body=dict(stamina=40)), _m(500)), [_open(0, EARTH)],
              branches=_b('earth', '震波', '地基', '深裂痕'), ranks=_r('earth', 裂痕護甲削減=5), tuning=dict(multDrain=1.5)))
    add(_spec('wind open: 風痕 pull (開印拉近距離 5), 牽引 the two behind, 風襲, 輕躍, 氣流',
              _c(_m(300), _m(350), _m(320, 60), _m(250), _m(360)), [_open(0, WIND)],
              branches=_b('wind', '牽引', '風襲', '輕躍', '氣流'), ranks=_r('wind', 開印拉近距離=5)))
    add(_spec('wind open 奇襲: a sneak hit opens and blows at once (the unbalance goes first)',
              _c(_m(100, board=_k(Unbalance=(1, 0, 3))), _m(500), _m(700)), [_open(0, WIND)],
              branches=_b('wind', '奇襲'), facts=dict(sneak=True)))
    add(_spec('blood open at 50% health: 依血位吸血, 血濺, 開印回血, 血咒, 深血痕',
              _c(_m(100), _m(400)), [_open(0, BLOOD)], branches=_b('blood', '血濺', '開印回血', '血咒', '深血痕'),
              facts=dict(hp=50.0)))
    add(_spec('blood open: 血祭之始 at sync 3 surges the target ×0.5', _c(_m(100, board=_k(Bleed=(2, 0, 10), BleedDot=(3, 0, 10)))),
              [_open(0, BLOOD)], branches=_b('blood', '血祭之始'), tuning=dict(syncStage=3)))
    add(_spec('divine open: 開印回血 5 points, 聖輝, 聖光 heals the allies within 15 m',
              _c(_m(100), _m(400), _m(500, **ALLY), _m(1200, **ALLY)), [_open(0, DIVINE)],
              branches=_b('divine', '聖輝', '聖光'), ranks=_r('divine', 開印回血=5)))
    add(_spec('poison open: 淬毒 within 3 m, 毒濺, 濃毒, 毒膜, 腐蝕開印, 毒血',
              _c(_m(100), _m(250), _m(100, 300, board=_k(PoisonDot=(4, 0, 10)))), [_open(0, POISON)],
              branches=_b('poison', '毒濺', '濃毒', '毒膜', '腐蝕開印', '毒血')))
    add(_spec('water open: 開印回復 5 points, 廣佈 to the nearest unsoaked, 湧泉, 開印沖刷 with 淨潮',
              _c(_m(100), _m(500), _m(200, board=_k(Soak=(1, 0, 10)))), [_open(0, WATER)],
              branches=_b('water', '廣佈', '湧泉', '開印沖刷', '淨潮'),
              ranks=_r('water', **{'開印時回復生命與耐力各最大值 0.3%／點': 5})))
    add(_spec('darkness open: 詛咒 drains magicka to you, 暗染 curses the nearest other',
              _c(_m(100), _m(400)), [_open(0, DARKNESS)], branches=_b('darkness', '暗染')))
    add(_spec('astral open: 明星 (+1 each) and 星散',
              _c(_m(100), _m(300, board=_k(Star=(1, 0, 30), StarFuse=(1, 0, 2))), _m(500)), [_open(0, ASTRAL)],
              branches=_b('astral', '明星', '星散')))
    # ---------------------------------------------------------------- end bodies (2.6 終焉 + the closing branches)
    add(_spec('fire end: 爆燃 at 灼熱 with a 25% consume bonus; 焚天 chains a 3 m fire mark; 火葬 marks both',
              _c(_m(100), _m(250, board=_mark(FIRE)), _m(100, 250, board=_mark(FIRE))),
              [_end(0, FIRE, EXPIRE, v1=2, v2=0.25, v3=1.0)], branches=_b('fire', '焚天', '火葬')))
    add(_spec('frost end unfrozen: 碎冰 ×1.0 with 碎冰 5 points and 終焉 lines',
              _c(_m(100)), [_end(0, FROST, CUT)], ranks=_r('frost', 碎冰=5, 終焉=2) | _r('common', 終焉=3)))
    add(_spec('frost end frozen: 冰河 shatters the frozen within 3 m (碎甲 on its armour)',
              _c(_m(100), _m(250, armor=50.0, board=_k(Frozen=(1, 0, 3), Freeze=(5, 0, 3))), _m(700, board=_k(Frozen=(1, 0, 3)))),
              [_end(0, FROST, EXPIRE, v1=1.0)], branches=_b('frost', '冰河')))
    add(_spec('lightning end: 4 charges ×1.5 on a cutting power hit, 2 jumps ×40%, 雷殛 on the shocked',
              _c(_m(100), _m(300), _m(400, board=_mark(LIGHTNING)), _m(500), _m(600, **ALLY)),
              [_end(0, LIGHTNING, CUT, v1=1.5, v2=0.9, v3=1.0, charge=4)], branches=_b('lightning', '雷殛')))
    add(_spec('lightning end: a full charge cutting power hit always crits ×2.5; 電弧 3 ×55%',
              _c(_m(100), _m(300), _m(400), _m(500)),
              [_end(0, LIGHTNING, CUT, v1=1.5, v2=0.9, v3=1.0, charge=6)], branches=_b('lightning', '電弧')))
    add(_spec('Discharge event: 連鎖 5 targets, the crit multiplier the DLL decided',
              _c(_m(100), _m(200), _m(300), _m(400), _m(500), _m(600), _m(700)),
              [['event', 0, 'Discharge', 3, 0.5, 1.0, 1.5]], branches=_b('lightning', '連鎖')))
    add(_spec('lightning end 天雷 at sync 3: every shocked target within 2 m + 0.2 m/pt of you, no jumps',
              _c(_m(100, board=_mark(LIGHTNING)), _m(150, board=_mark(LIGHTNING)), _m(200), _m(300, board=_mark(LIGHTNING))),
              [_end(0, LIGHTNING, EXPIRE, v1=1.0, v2=0.9, charge=3)], ranks=_r('lightning', 天雷=5), tuning=dict(syncStage=3),
              facts=dict(rng='no')))
    add(_spec('earth end: 地震 崩裂 ×2, 廣震 5 m, 塵暴, 山崩 on the fissured; a floored target falls',
              _c(_m(100, body=dict(stamina=15)), _m(400), _m(100, 150, board=_k(Fissure=(1, 0, 8))), _m(1000, board=_k(Fissure=(1, 0, 8)))),
              [_end(0, EARTH, EXPIRE)], branches=_b('earth', '崩裂', '廣震', '塵暴', '山崩'), ranks=_r('earth', 地震耐力削減=4),
              me=_k(ChargedQuake=(0.15, 0, 10))))
    add(_spec('wind end: 吹飛, 風渦, 亂流, 追風, 迴旋',
              _c(_m(100), _m(200), _m(300), _m(400), _m(1600)), [_end(0, WIND, EXPIRE)],
              branches=_b('wind', '風渦', '亂流', '追風', '迴旋')))
    add(_spec('wind end 上天: lifted instead, 空中追擊 on the airborne (landing stored)',
              _c(_m(100, board=_k(Airborne=(1, 0, 2))), _m(300)), [_end(0, WIND, CUT)], branches=_b('wind', '上天', '空中追擊'),
              ranks=_r('wind', 風刃傷害=5)))
    add(_spec('blood end: 血潮 with 血契 at full health, 飽飲, 放血終焉; 血漫 surges a bleeding neighbour',
              _c(_m(100), _m(300, board=_k(Bleed=(2, 0, 10), BleedDot=(2, 5, 10)))), [_end(0, BLOOD, EXPIRE, v1=20.0)],
              branches=_b('blood', '血契', '飽飲', '放血終焉', '血漫')))
    add(_spec('blood end at 60% health: the curve and the leech; 血海 at sync 3; a boss takes 3%',
              _c(_m(100, body=dict(vip=True, health=500)), _m(150, board=_k(Bleed=(1, 0, 10), BleedDot=(1, 0, 10)))),
              [_end(0, BLOOD, CUT, v1=10.0)], ranks=_r('blood', 血海=5, **{'血潮治療倍率 ×2': 5}), tuning=dict(syncStage=3),
              facts=dict(hp=60.0)))
    add(_spec('divine end: 裁決 at holy 2 with 懲戒 3, 天誅, 廣裁, 光耀 on the undead',
              _c(_m(100, board=_mark(DIVINE)), _m(250, body=dict(undead=True)), _m(100, 150)), [_end(0, DIVINE, CUT, v1=2)],
              branches=_b('divine', '天誅', '廣裁', '光耀', '聖痕', '聖域'), me=_k(Punish=(3, 0, 8))))
    add(_spec('divine end 天啟 at sync 3 and 重裁 at night',
              _c(_m(100, body=dict(undead=True)), _m(200)), [_end(0, DIVINE, EXPIRE, v1=3)], branches=_b('divine', '重裁'),
              ranks=_r('divine', 天啟=5), tuning=dict(syncStage=3, envNight=True)))
    add(_spec('poison end: 劇毒, 腐蝕終焉, 疫染 to 6 m (keeping the stronger / longer)',
              _c(_m(100, resist=[0, 0, 0, 30, 0], board=_k(PoisonDot=(8, 0, 14), Catalyzed=(2, 0, 14))), _m(300),
                 _m(400, board=_k(PoisonDot=(10, 0, 3))), _m(900)),
              [_end(0, POISON, CUT)], branches=_b('poison', '劇毒', '腐蝕終焉', '疫染')))
    add(_spec('water end cut: 大潮 guides the soaked within 3 m; 洗滌',
              _c(_m(100), _m(200, board=_k(Soak=(1, 0, 10))), _m(700, board=_k(Soak=(1, 0, 10)))), [_end(0, WATER, CUT)],
              branches=_b('water', '大潮', '洗滌', '強引')))
    add(_spec('darkness end: 不治 6 s, 深淵回響 fills your magicka', _c(_m(100)), [_end(0, DARKNESS, CUT)],
              branches=_b('darkness', '不治', '深淵回響'), facts=dict(magicka=20.0, magicka_max=150.0)))
    add(_spec('astral end: 星落 ×2 (隕星 ×3) and every resonance target within 15 m detonates; 聚星',
              _c(_m(100), _m(300, board=_k(Star=(2, 0, 30))), _m(400, board=_k(Star=(1, 0, 30))), _m(2000, board=_k(Star=(3, 0, 30)))),
              [_end(0, ASTRAL, EXPIRE)], branches=_b('astral', '隕星', '聚星')))
    add(_spec('連鎖終焉 ×0.5 on the fire-marked nearby, 反哺',
              _c(_m(100), _m(300, board=_mark(FIRE)), _m(500, board=_mark(FIRE) | _k(EndCooldown=(1, 0, 1)))),
              [_end(0, FIRE, CUT, v1=1, v2=0.0, v3=1.0)], branches=_b('common', '連鎖終焉', '反哺')))
    add(_spec('大協奏: the first end after a switch ends every old-marked target at ×1',
              _c(_m(100), _m(300, board=_mark(FROST))), [_end(0, FROST, CUT, flags=2)], branches=_b('common', '大協奏')))
    # ---------------------------------------------------------------- the other body events
    add(_spec('Frozen: 絕對零度 5 points at sync 3, 深寒, 霜爆 on the freezing within 3 m',
              _c(_m(100), _m(250, board=_k(Freeze=(2, 0, 6))), _m(300)), [['event', 0, 'Frozen', 3.0]],
              branches=_b('frost', '深寒', '霜爆'), ranks=_r('frost', 絕對零度=5), tuning=dict(syncStage=3)))
    add(_spec('Hallucinate: 夢魘 curses 3 m (a fear there chains); a group event does nothing more',
              _c(_m(100), _m(200, board=_k(Curse=(2, 0, 8))), _m(700)),
              [['event', 0, 'Hallucinate', 1, 2.0, 0], ['event', 2, 'Hallucinate', 1, 2.0, 1]], branches=_b('darkness', '夢魘')))
    add(_spec('Hallucinate: 群魔 at sync 3 frenzies the cursed ≥3 within 4 m',
              _c(_m(100), _m(250, board=_k(Curse=(3, 0, 8))), _m(300, board=_k(Curse=(4, 0, 8), FrenzyCooldown=(1, 0, 20))),
                 _m(150, board=_k(Curse=(1, 0, 8)))),
              [['event', 0, 'Hallucinate', 2, 3.0, 0]], branches=_b('darkness', '群魔'), tuning=dict(syncStage=3)))
    add(_spec('Judgment III: 破防, the 3 m blast (undead ×3), 破邪斬 50% within 4 m',
              _c(_m(100, board=_k(StarLock=(1, 0, 3))), _m(250, body=dict(undead=True)), _m(360), _m(600)),
              [['event', 0, 'Judgment', 3, 44.0]], branches=_b('divine', '破邪斬')))
    add(_spec('Judgment II: 破防 only', _c(_m(100), _m(200)), [['event', 0, 'Judgment', 2, 10.0]], tuning=dict(multDrain=2.0)))
    add(_spec('Splash: every bleeding within 15 m of you surges ×0.5 without clearing; Rise with 血約',
              _c(_m(100, board=_k(Bleed=(2, 0, 10), BleedDot=(2, 0, 10))), _m(900, board=_k(Bleed=(1, 0, 10))), _m(1200, board=_k(Bleed=(1, 0, 10))),
                 _m(300)),
              [['event', 0, 'Splash', 20.0], ['event', 0, 'Rise']], branches=_b('blood', '血約')))
    add(_spec('Shatter: 碎甲加深 20%, 冰崩 shatters the frozen within 3 m (they do not spread again)',
              _c(_m(100, armor=80.0), _m(250, armor=40.0, board=_k(Frozen=(1, 0, 3), Freeze=(5, 0, 3))),
                 _m(400, board=_k(Frozen=(1, 0, 3), Freeze=(5, 0, 3)))),
              [['event', 0, 'Shatter', 1]], branches=_b('frost', '碎甲加深', '冰崩')))
    add(_spec('Landing and Blade events (空中追擊 lifts the airborne once more; 御風 on the unbalanced)',
              _c(_m(100, board=_k(Airborne=(1, 0, 2), Unbalance=(1, 0, 3))), _m(300)),
              [['event', 0, 'Landing', 6.0], ['event', 0, 'Blade', 2, 0.5]], branches=_b('wind', '空中追擊', '御風')))
    add(_spec('Overheat: every fire-marked within 15 m of you detonates as a chain end',
              _c(_m(100, board=_mark(FIRE)), _m(800, board=_mark(FIRE)), _m(1200, board=_mark(FIRE)), _m(300)),
              [['event', 0, 'Overheat']], me=_k(Heat1=(1, 0, 3600))))
    add(_spec('resonance: the detonator and the star-marked within 15 m count; 聚星 +30%; 星蝕 50% to the others',
              _c(_m(100), _m(300, board=_k(Star=(1, 0, 30))), _m(400, board=_k(Star=(2, 0, 30))), _m(1500, board=_k(Star=(1, 0, 30)))),
              [['op', 0, 'resonance'], ['op', 0, 'starBurst', 20.0], ['op', 0, 'darkStrike', 30.0]],
              branches=_b('astral', '聚星', '星蝕'), me=_k(Resonance=(4, 0, 20))))
    add(_spec('碎岩 ring: 5 within 3 m, a floored one falls (not an essential one); 冰心 freezes the freezing within 15 m',
              _c(_m(100), _m(200, body=dict(stamina=10)), _m(250, essential=True, body=dict(stamina=5)), _m(260), _m(270), _m(280),
                 _m(290), _m(600, board=_k(Freeze=(1, 0, 6))), _m(700, board=_k(Frozen=(1, 0, 3), Freeze=(5, 0, 3)))),
              [['op', 0, 'crush', 12.0, 20.0], ['op', 0, 'freezeNearby']]))
    # ---------------------------------------------------------------- 融斷
    add(_spec('burst: stage 2 ×2, the common / no-form lines, 寂 burns magicka; the ally, the empty and the far untouched',
              _c(_m(0, **GONE), _m(300, magicka_max=200.0, board=_mark(FIRE)), _m(500, magicka_max=100.0, board=_mark(FROST) | _mark(LIGHTNING)),
                 _m(700, board=_k(Residual=(DARKNESS, 0, 4))), _m(400, **ALLY, board=_mark(FIRE)), _m(2000, board=_mark(FIRE))),
              [['burst', 2, 0]], ranks=_r('common', 融斷=2, 融斷再=1) | _r('noform', 融斷=2, 寂每層燒魔=4),
              me=_k(Charge=(3, 0, 10))))
    add(_spec('burst: 萬寂 clears the other statuses, 斷界, 回流 over the max into 超載, 雙斷, 安全閥, 寂 cap',
              _c(_m(0, **GONE), _m(300, magicka_max=100.0, board=_mark(FROST) | _mark(POISON) | _k(Curse=(2, 0, 8), Soak=(1, 0, 10),
                                                                                                    PoisonDot=(3, 0, 10), Hush=(1, 0, 10)))),
              [['burst', 1, 0]], branches=_b('noform', '萬寂', '斷界', '回流', '雙斷') | _b('common', '安全閥', '雙印'),
              ranks=_r('noform', 寂上限=5), facts=dict(magicka=95.0, magicka_max=100.0)))
    add(_spec('burst: 地斷 knocks the tired, 颶風 lifts the unmarked, 風斷 two blades, 墜星 shares 闇宙',
              _c(_m(0, **GONE), _m(300, board=_mark(EARTH)), _m(400, body=dict(stamina=20), board=_mark(WIND)),
                 _m(500, board=_mark(ASTRAL) | _k(Star=(1, 0, 30))), _m(600, body=dict(stamina=10))),
              [['burst', 3, 0]], branches=_b('earth', '地斷') | _b('wind', '颶風', '風斷') | _b('astral', '墜星'),
              me=_k(Cosmos=(6, 0, 10))))
    add(_spec('burst: a target inside its end cooldown only loses the marks (no 寂)',
              _c(_m(0, **GONE), _m(300, board=_mark(FIRE) | _k(EndCooldown=(1, 0, 1))), _m(400, board=_mark(DARKNESS))),
              [['burst', 0, 0]]))
    add(_spec('burst: 星斷 true ×0.6, 水斷 heals and restores, 聖斷, 血斷, the domains (火域)',
              _c(_m(0, **GONE), _m(300, board=_mark(ASTRAL)), _m(400, board=_mark(WATER)), _m(500, board=_mark(DIVINE)),
                 _m(600, board=_mark(BLOOD) | _k(Bleed=(2, 0, 10), BleedDot=(2, 0, 10))), _m(700, board=_mark(FIRE))),
              [['burst', 1, 0]], branches=_b('astral', '星斷') | _b('water', '水斷') | _b('divine', '聖斷') | _b('blood', '血斷') |
              _b('fire', '火域'), ranks=_r('fire', 火印記的融斷=5, 火印記的融斷再=5)))
    add(_spec('burst 雷斷: all charges added to the lightning burst', _c(_m(0, **GONE), _m(300, board=_mark(LIGHTNING))),
              [['burst', 1, 0]], branches=_b('lightning', '雷斷'), me=_k(Charge=(5, 0, 10)), tuning=dict(syncStage=1)))
    add(_spec('fusion stage 3 on a frozen target without 冰封融斷: the fusion hit only, it stays frozen',
              _c(_m(0, **GONE), _m(300, board=_mark(FROST) | _k(Frozen=(1, 0, 3), Freeze=(5, 0, 3)))), [['burst', 3, 0]]))
    add(_spec('fusion stage 3 on a frozen target with 冰封融斷: the fusion hit and a 碎冰 (not ×K_sync)',
              _c(_m(0, **GONE), _m(300, board=_mark(FROST) | _k(Frozen=(1, 0, 3), Freeze=(5, 0, 3)))), [['burst', 3, 0]],
              branches=_b('frost', '冰封融斷')))
    add(_spec('fusion stage 3 on a frozen boss with 冰封融斷: 碎冰 10% of its max health',
              _c(_m(0, **GONE), _m(300, body=dict(vip=True, health=1000, health_max=1000), board=_mark(FROST) | _k(Frozen=(1, 0, 3), Freeze=(5, 0, 3)))),
              [['burst', 3, 0]], branches=_b('frost', '冰封融斷')))
    add(_spec('fusion stage 3 of a divine and an astral mark: B_max × 3 × G (day ×1.2), no 裁決 ×2 / 星落 ×2, the stars still detonate',
              _c(_m(0, **GONE), _m(300, board=_mark(DIVINE)), _m(400, board=_mark(ASTRAL) | _k(Star=(2, 0, 30)))), [['burst', 3, 0]]))
    add(_spec("burst 毒斷: the burst's catalysis ×4 (not ×2)", _c(_m(0, **GONE), _m(300, board=_mark(POISON) | _k(PoisonDot=(3, 0, 10)))),
              [['burst', 0, 0]], branches=_b('poison', '毒斷')))
    add(_spec('burst 收束 20 m (+0.3 m/pt) reaches further', _c(_m(0, **GONE), _m(1450, board=_mark(FIRE)), _m(1700, board=_mark(FIRE))),
              [['burst', 0, 0]], branches=_b('noform', '收束'), ranks=_r('noform', 融斷範圍=2)))
    # ---------------------------------------------------------------- death
    add(_spec('death: the divine mark turns it to ash; 聖灰, 淨灰 on the undead nearby',
              _c(_m(100, body=dict(undead=True), board=_mark(DIVINE) | _mark(DARKNESS) | _k(Curse=(5, 0, 8))),
                 _m(300, body=dict(undead=True)), _m(400), _m(500, **ALLY, body=dict(undead=True))),
              [['death', dict(killer_you=True)]], branches=_b('divine', '聖灰', '淨灰')))
    add(_spec('death: 亡者歸來 — level 20, curse 5 of 5: tier 4, +50% attack, double time',
              _c(_m(100, level=20, board=_mark(DARKNESS) | _k(Curse=(5, 0, 8)))), [['death', dict(killer_you=True, curse_cap=5)]]))
    add(_spec('death: 亡者歸來 — level 5, curse 3 of 8: tier 1', _c(_m(100, level=5, board=_mark(DARKNESS) | _k(Curse=(3, 0, 8)))),
              [['death', dict(curse_cap=8)]]))
    add(_spec('death: 殘魂 raises at 1 curse (the 25% succeeds)', _c(_m(100, level=40, board=_mark(DARKNESS) | _k(Curse=(1, 0, 8)))),
              [['death', dict(killer_you=True)]], branches=_b('darkness', '殘魂'), facts=dict(rng='yes')))
    add(_spec('death: 殘魂 fails its 25% in the mid mode; a dragon and a boss never rise',
              _c(_m(100, level=40, board=_mark(DARKNESS) | _k(Curse=(1, 0, 8)))), [['death', dict(killer_you=True)]],
              branches=_b('darkness', '殘魂')))
    add(_spec('death: 冥召 — the death curse killed it: tier +1 without a mark', _c(_m(100, level=8, board=_k(CurseKill=(1, 0, 1)))),
              [['death', dict(killer_you=True)]], branches=_b('darkness', '冥召')))
    add(_spec('death: 死靈主 at sync 3 — any level, permanent', _c(_m(100, level=80, board=_mark(DARKNESS))),
              [['death', dict(killer_you=True)]], branches=_b('darkness', '死靈主'), tuning=dict(syncStage=3)))
    add(_spec('death: an essential NPC with 5 curse does not rise', _c(_m(100, level=10, essential=True, board=_mark(DARKNESS) | _k(Curse=(5, 0, 8)))),
              [['death', dict(killer_you=True)]]))
    add(_spec('death: a named (unique, not essential) enemy rises (2.9: only essential ones are exempt)',
              _c(_m(100, level=10, body=dict(vip=True), board=_mark(DARKNESS) | _k(Curse=(3, 0, 8)))), [['death', dict(killer_you=True)]]))
    add(_spec('death: a named (unique) enemy turns to ash; an essential one does not',
              _c(_m(100, body=dict(vip=True), board=_mark(DIVINE))), [['death', dict(killer_you=True)]], branches=_b('divine', '聖灰')))
    add(_spec('death: an essential enemy with the divine mark is not turned to ash',
              _c(_m(100, essential=True, board=_mark(DIVINE))), [['death', dict(killer_you=True)]], branches=_b('divine', '聖灰')))
    add(_spec('death: 狂宴 — killed by your frenzied NPC counts as marked',
              _c(_m(100, level=10, board=_k(Curse=(3, 0, 8)))), [['death', dict(killer_frenzied=True)]], branches=_b('darkness', '狂宴')))
    add(_spec('death: the poison spreads S = max(R, 30% max health) × 50% to everyone within 15 m (no cap on count)',
              _c(_m(100, body=dict(health_max=100.0), board=_k(PoisonDot=(2, 0, 5))), _m(200), _m(300, board=_k(PoisonDot=(3, 0, 20))),
                 _m(400), _m(500), _m(600), _m(700), _m(800), _m(2000), _m(350, **ALLY)),
              [['death', dict()]]))
    add(_spec('death: 蔓延 75%, a huge share caps the strength and lengthens the time',
              _c(_m(100, body=dict(health_max=2000.0), board=_k(PoisonDot=(10, 0, 10))), _m(200)), [['death', dict()]],
              branches=_b('poison', '蔓延')))
    add(_spec('death: 連鎖冰封, 火葬, 亡魂, 亡衛 at sync 3',
              _c(_m(100, board=_k(Frozen=(1, 0, 3), Freeze=(5, 0, 3), Cremation=(20, 0, 1), CurseKill=(1, 0, 1))), _m(200), _m(300),
                 _m(1500)),
              [['death', dict(servant=True)]], branches=_b('frost', '連鎖冰封') | _b('fire', '火葬') | _b('darkness', '亡魂', '亡衛'),
              tuning=dict(syncStage=3)))
    add(_spec('death: 飲血, 血承 (resists, armour, max health), 不死 at 20% health, 無魔 over the max, 連殺',
              _c(_m(100, spell_user=True, armor=50.0, resist=[40, 0, 20, 10, 30], body=dict(health_max=300.0),
                    board=_mark(WIND) | _k(Bleed=(2, 0, 10), LastHitSneak=(WIND, 0, 1))), _m(400, board=_k(Bleed=(1, 0, 10)))),
              [['death', dict(killer_you=True)]],
              branches=_b('blood', '飲血', '血承', '不死', '血約') | _b('noform', '無魔') | _b('wind', '連殺'), tuning=dict(syncStage=3),
              facts=dict(hp=20.0, stamina=30.0, magicka=80.0), me=_k(InheritFrost=(12, 0, 15))))
    add(_spec('death: 不死 once in 30 s; at 50% health the line is 70%', _c(_m(100, board=_k(Bleed=(1, 0, 10)))), [['death', dict()]],
              branches=_b('blood', '不死'), tuning=dict(syncStage=3), facts=dict(hp=50.0)))
    add(_spec('death: 不死 in its cooldown does nothing', _c(_m(100, board=_k(Bleed=(1, 0, 10)))), [['death', dict()]],
              branches=_b('blood', '不死'), tuning=dict(syncStage=3), facts=dict(hp=50.0), me=_k(UndyingCooldown=(1, 0, 30))))
    add(_spec('death: 淨土 at sync 3 — your kill in the divine form turns to ash', _c(_m(100, board=_mark(DARKNESS) | _k(Curse=(5, 0, 8)))),
              [['death', dict(killer_you=True)]], branches=_b('divine', '淨土'), tuning=dict(syncStage=3), facts=dict(form=DIVINE)))
    # ---------------------------------------------------------------- X臨 (opening a form)
    add(_spec('advent: 火臨 5 points opens every hostile within 3 m of you; 臨界; the far only slowed',
              _c(_m(0, **GONE), _m(100), _m(200, board=_mark(FROST)), _m(400), _m(1300)), [['advent', FIRE]],
              ranks=_r('fire', 火臨=5), branches=_b('common', '臨界')))
    add(_spec('advent 雙斷: a burst in the last 3 s opens on every hostile within the burst range',
              _c(_m(0, **GONE), _m(100), _m(600), _m(1300)), [['advent', WIND]], ranks=_r('wind', 風臨=2),
              me=_k(DoubleBurst=(1, 0, 3))))
    add(_spec('advent: 冰臨 with 冰臨強化', _c(_m(0, **GONE), _m(100), _m(300)), [['advent', FROST]], ranks=_r('frost', 冰臨=1),
              branches=_b('frost', '冰臨強化')))
    add(_spec('advent: 地臨強化 without the main line (2 m)', _c(_m(0, **GONE), _m(100, body=dict(stamina_max=180)), _m(200)),
              [['advent', EARTH]], branches=_b('earth', '地臨強化')))
    add(_spec('advent: 毒臨強化 3 doses, 暗臨強化 fear', _c(_m(0, **GONE), _m(100), _m(200)),
              [['advent', POISON], ['advent', DARKNESS]], branches=_b('poison', '毒臨強化') | _b('darkness', '暗臨強化')))
    add(_spec('advent: 水臨強化 soaks, cleanses you and fills your magicka', _c(_m(0, **GONE), _m(100)), [['advent', WATER]],
              branches=_b('water', '水臨強化'), facts=dict(magicka=30.0)))
    add(_spec('advent: 星臨強化 2 stars; 血臨強化 pays 15% and splashes',
              _c(_m(0, **GONE), _m(100, board=_k(Bleed=(1, 0, 10), BleedDot=(1, 0, 10)))), [['advent', ASTRAL], ['advent', BLOOD]],
              branches=_b('astral', '星臨強化') | _b('blood', '血臨強化')))
    # ---------------------------------------------------------------- echo, the hit's bodies, 印潮, 化身
    add(_spec('echo: 25% (+1%/pt) of the star proc to the other resonance targets, night ×1.5; 星鏈 once per 2 s',
              _c(_m(100, board=_k(Star=(1, 0, 30))), _m(300, board=_k(Star=(1, 0, 20))), _m(400, board=_k(Star=(2, 0, 20),
                                                                                                           StarChainCooldown=(1, 0, 2))),
                 _m(500)),
              [['echo', 0, 12.0]], branches=_b('astral', '星鏈'), ranks=_r('astral', 回聲比例=5), tuning=dict(envNight=True)))
    add(_spec('hit bodies: 震擊 on a fissured target with a power hit', _c(_m(100, board=_k(Fissure=(1, 0, 8)))),
              [['hitBodies', EARTH, True, 0]], branches=_b('earth', '震擊')))
    add(_spec('hit bodies: 護持', _c(_m(100)), [['hitBodies', DIVINE, False, 0]], branches=_b('divine', '護持')))
    add(_spec('hit bodies: 萎靡 at 5 doses, 侵蝕 at 10', _c(_m(100, board=_k(PoisonDot=(20, 0, 12)))), [['hitBodies', POISON, False, 0]],
              branches=_b('poison', '萎靡', '侵蝕')))
    add(_spec('hit bodies: the curse erodes every resist 2%/layer (+0.2%/pt) × 萬象', _c(_m(100, board=_k(Curse=(4, 0, 8)))),
              [['hitBodies', DARKNESS, False, 0]], ranks=_r('darkness', 詛咒每層抗性侵蝕=5), branches=_b('common', '萬象')))
    add(_spec('hit bodies: 封印 silences every hostile within 3 m of the target', _c(_m(100), _m(250), _m(500), _m(200, **ALLY)),
              [['hitBodies', 0, False, 4]], branches=_b('noform', '封印')))
    add(_spec('印潮: the switch hit opens the new element on 2 others carrying the old mark',
              _c(_m(100), _m(200, board=_mark(FIRE)), _m(300, board=_mark(FIRE)), _m(400, board=_mark(FIRE)), _m(250)),
              [['surge', WATER, FIRE]], branches=_b('common', '印潮')))
    add(_spec('化身 lightning: 天雷 discharge of your charges', _c(_m(100, board=_mark(LIGHTNING)), _m(150, board=_mark(LIGHTNING))),
              [['avatar', LIGHTNING]], ranks=_r('lightning', 天雷=10), tuning=dict(syncStage=3), me=_k(Charge=(5, 0, 10))))
    add(_spec('化身 blood and divine: a surge, a judgment at your holy tier',
              _c(_m(100, board=_k(Bleed=(2, 0, 10), BleedDot=(2, 0, 10)))), [['avatar', BLOOD], ['avatar', DIVINE]],
              me=_k(Holy3=(0, 0, 3600))))
    return S


# ---------------------------------------------------------------- hand anchors (computed by hand from v0.4, not by the model)
# B_max: fire 12, frost 10, lightning 25, earth 10, wind 9, blood 10, divine 10, poison 9, water 7, darkness 10, astral 10.
# G(L) at level 1 = 1.05; NodeScale 3 (a "+x%/pt" line gives 3x per point); day: divine ×1.2.
HAND = {
    # 點燃 12 × 0.5 × 1.05 = 6.3; 餘熱 15; 先燃 12 × 灼熱 2.4 × 0.5 × 1.05 = 15.12
    'fire open: 點燃 ×0.5, 餘熱, 先燃 at sync 3 on your 灼熱': dict(ops=[
        ['damage', 0, FIRE, 6.3], ['stamina', -1, 15.0], ['damage', 0, FIRE, 15.12]]),
    # 霜結 25% 3 s; 寒潮: member 1 (400, nearest non-ally) freezes 2 layers (6 s) and slows 25%
    'frost open: 霜結 25% 3 s; 寒潮 the nearest other +2 (the ally, the empty and the far never)': dict(
        ops=[['slow', 0, 25.0, 3.0], ['slow', 1, 25.0, 6.0]], absent=[['slow', 3], ['slow', 4], ['slow', 5]],
        boards={(1, 'Freeze'): [2.0, 6.0]}),
    # 感電 25; 充能開印 25; 雷閃 +15% 2 s on you; 傳導 puts the lightning mark (8 s) on member 1, never member 2 (fire mark)
    'lightning open: 感電 drain, 傳導 onto the unmarked, 充能開印, 感電削弱, 雷閃': dict(
        ops=[['drainMagicka', 0, 25.0], ['magicka', -1, 25.0], ['timed', -1, 'haste', 15.0, 2.0],
             ['timed', 0, 'magicResistDebuff', 10.0, 8.0]], boards={(1, 'Mark3'): [0.0, 8.0]}),
    # 裂痕 armour 30 + 2×5 = 40, × MultDrain 1.5 = 60; stamina 10 × 1.5 = 15; you +10; 地基 100% 3 s; 深裂痕 knock
    'earth open: 裂痕 (裂痕護甲削減 5), 震波, 地基, 深裂痕 knocks a tired target': dict(
        ops=[['timed', 0, 'armorDebuff', 60.0, 8.0], ['drainStamina', 0, 15.0], ['stamina', -1, 10.0],
             ['timed', 1, 'armorDebuff', 60.0, 8.0], ['timed', 0, 'staminaRateDebuff', 100.0, 3.0], ['event', 0, 'Knock', 3.0]],
        boards={(1, 'Fissure'): [1.0, 8.0]}),
    # 爆燃 12 × 2.4 × 1.25 × 1.05 = 37.8 (火葬 marker 37.8 for 1 s); the chained 3 m mark: 12 × 1.0 × 1.05 = 12.6
    'fire end: 爆燃 at 灼熱 with a 25% consume bonus; 焚天 chains a 3 m fire mark; 火葬 marks both': dict(
        ops=[['damage', 0, FIRE, 37.8], ['damage', 1, FIRE, 12.6]], absent=[['damage', 2]],
        boards={(0, 'Cremation'): [37.8, 1.0], (1, 'Cremation'): [12.6, 1.0]}),
    # 碎冰 10 × 1.0 × (1 + 5×3%×3 = 1.45) × end lines (1 + 3×1%×3)(1 + 2×2%×3) = 1.09 × 1.12 × 1.05 G = 18.58668
    'frost end unfrozen: 碎冰 ×1.0 with 碎冰 5 points and 終焉 lines': dict(ops=[['damage', 0, FROST, 18.58668]]),
    # 放電 25 × 0.3 × 4 × 1.5 = 45 → ×1.05 = 47.25, drain 45 × 0.5 × 1.05 = 23.625; jumps 45 × 0.4 = 18 → 18.9 / 9.45
    'lightning end: 4 charges ×1.5 on a cutting power hit, 2 jumps ×40%, 雷殛 on the shocked': dict(
        ops=[['damage', 0, LIGHTNING, 47.25], ['drainMagicka', 0, 23.625], ['damage', 1, LIGHTNING, 18.9],
             ['drainMagicka', 1, 9.45]], absent=[['damage', 4]]),
    # full charge (6) cutting power hit: ×2.5 always; raw 25 × 0.3 × 6 × 1.5 × 2.5 = 168.75 → ×1.05 = 177.1875
    'lightning end: a full charge cutting power hit always crits ×2.5; 電弧 3 ×55%': dict(
        ops=[['damage', 0, LIGHTNING, 177.1875], ['damage', 3, LIGHTNING, 168.75 * 0.55 * 1.05]]),
    # 血潮: bleed 20 × 飽飲 1.5 × curve 1.3 = 39, + health 100 × 20% = 20 → 59 × 血契 2 = 118; heal 118 × 5% × 2 = 11.8; pay 10
    'blood end: 血潮 with 血契 at full health, 飽飲, 放血終焉; 血漫 surges a bleeding neighbour': dict(
        ops=[['damage', 0, BLOOD, 118.0], ['heal', -1, 11.8], ['pay', -1, 10.0], ['bleedDot', 1, 0.0, 0.0]]),
    # 裁決 10 × 2 × 1.6 (懲戒 3) × 1.2 (聖印) × 1.1 (聖痕) × 1.2 (holy 2) × 3 (聖痕 prey) × 1.05 G × 1.2 day
    'divine end: 裁決 at holy 2 with 懲戒 3, 天誅, 廣裁, 光耀 on the undead': dict(
        ops=[['damage', 0, DIVINE, 10 * 2 * 1.6 * 1.3 * 1.2 * 3 * 1.05 * 1.2], ['heal', -1, 10.0],
             ['event', 0, 'Domain', DIVINE, 5.0, 210.0]], boards={(1, 'Radiance'): [1.0, 5.0]}),
    # 劇毒: poison resist 30 as a debuff for the poison's 14 s; 腐蝕終焉 magic resist -20% 8 s
    'poison end: 劇毒, 腐蝕終焉, 疫染 to 6 m (keeping the stronger / longer)': dict(
        ops=[['timed', 0, 'poisonResistDebuff', 30.0, 14.0], ['timed', 0, 'magicResistDebuff', 20.0, 8.0]],
        boards={(1, 'PoisonDot'): [8.0, 14.0], (1, 'Catalyzed'): [2.0, 14.0], (2, 'PoisonDot'): [10.0, 14.0]}),
    # 冰封 50% + 5 × 2% = 60% for 3 s; 深寒 attack -20%, stamina regen -100% for 3 s
    'Frozen: 絕對零度 5 points at sync 3, 深寒, 霜爆 on the freezing within 3 m': dict(
        ops=[['slow', 0, 60.0, 3.0], ['timed', 0, 'meleeDebuff', 20.0, 3.0], ['timed', 0, 'staminaRateDebuff', 100.0, 3.0]],
        boards={(1, 'Freeze'): [4.0, 6.0]}),
    # 破防 60 / 10% 5 s; blast 10 × 0.5 × 1.05 × 1.2 = 6.3, the undead ×3 = 18.9; 破邪斬 44 / 1.1 (星鎖) × 0.5 = 20
    'Judgment III: 破防, the 3 m blast (undead ×3), 破邪斬 50% within 4 m': dict(
        ops=[['timed', 0, 'armorDebuff', 60.0, 5.0], ['timed', 0, 'magicResistDebuff', 10.0, 5.0], ['damage', 1, DIVINE, 18.9],
             ['damage', 1, DIVINE, 60.0], ['damage', 2, DIVINE, 20.0]], absent=[['damage', 3]]),
    # burst stage 2: K 2 × common (1 + 2×1%×3 + 1×2%×3 = 1.12) × no-form (1 + 2×2%×3 = 1.12) = 2.5088;
    # fire at no heat: 12 × 1 × 2.5088 × 1.05 = 31.6109; 寂 burns 200 × (5% + 4 × 0.5%) = 14 (one layer)
    'burst: stage 2 ×2, the common / no-form lines, 寂 burns magicka; the ally, the empty and the far untouched': dict(
        ops=[['damage', 1, FIRE, 31.61088], ['drainMagicka', 1, 14.0], ['drainMagicka', 2, 14.0], ['hush', 1, 1.0], ['hush', 2, 2.0]],
        absent=[['damage', 4], ['damage', 5]], boards={(1, 'Hush'): [1.0, 10.0], (2, 'Hush'): [2.0, 10.0]}),
    # 萬寂: 寂 1 + 2 settled = 3 (cap 5 + 寂上限 5/5 = 6) -> clears the curse, the poison, the soak: each B_max × 0.5 × G 1.05
    # true (暗 5.25, 毒 4.725, 水 3.675), 寂 3 + 3 = 6; the burn counts the 2 new layers only: 100 × 5% × 2 = 10.
    # 回流 (10 + 9) × 0.5 = 9.5 magicka: 5 fits (95 of 100), 4.5 into 超載; 斷界 frost / poison resist -10% 3 s; 雙斷 3 s, 安全閥 2 s
    'burst: 萬寂 clears the other statuses, 斷界, 回流 over the max into 超載, 雙斷, 安全閥, 寂 cap': dict(
        ops=[['damage', 1, 0, 5.25], ['damage', 1, 0, 4.725], ['damage', 1, 0, 3.675], ['hush', 1, 6.0], ['drainMagicka', 1, 10.0],
             ['magicka', -1, 5.0], ['timed', 1, 'frostResistDebuff', 10.0, 3.0], ['timed', 1, 'poisonResistDebuff', 10.0, 3.0]],
        boards={(1, 'Hush'): [6.0, 10.0], (-1, 'Overload'): [4.5, 86400.0], (-1, 'DoubleBurst'): [1.0, 3.0],
                (-1, 'SafetyValve'): [1.0, 2.0]}),
    # 聚星: the detonator + 2 star-marked within 15 m = 3 -> 20 × 1.3 = 26; 星蝕 30 × 0.5 = 15 on each of the two (the one
    # 20 m from the detonator is out); 共鳴層 4 + 3 = 7 (20 s)
    'resonance: the detonator and the star-marked within 15 m count; 聚星 +30%; 星蝕 50% to the others': dict(
        ops=[['damage', 0, ASTRAL, 26.0], ['damage', 1, ASTRAL, 15.0], ['damage', 2, ASTRAL, 15.0]], absent=[['damage', 3]],
        boards={(-1, 'Resonance'): [7.0, 20.0]}),
    # 碎岩: 5 nearest within 3 m of the target (the 6th is left out), 12 earth and 20 stamina each; the tired one falls, the boss
    # does not; 冰心: the freezing one within 15 m of you freezes (3 s), the frozen one is left alone
    '碎岩 ring: 5 within 3 m, a floored one falls (not an essential one); 冰心 freezes the freezing within 15 m': dict(
        ops=[['damage', 1, EARTH, 12.0], ['drainStamina', 1, 20.0], ['event', 1, 'Knock', 3.0], ['damage', 5, EARTH, 12.0]],
        absent=[['event', 2, 'Knock'], ['damage', 6]], boards={(7, 'Frozen'): [1.0, 3.0]}),
    # 地臨強化 without 地臨: 2 m of you; stamina -50% of 180 = 90, no MultDrain; the one at 2.9 m untouched
    'advent: 地臨強化 without the main line (2 m)': dict(ops=[['drainStamina', 1, 90.0]], absent=[['drainStamina', 2]]),
    # 天雷 5 at sync 3: 2 + 1 = 3 m of you; 3 charges: 25 × 0.3 × 3 = 22.5 × 1.05 = 23.625 on each shocked target in it,
    # drain 22.5 × 0.5 × 1.05 = 11.8125; no jumps (member 2, unmarked, and member 3, 4.3 m, take nothing)
    'lightning end 天雷 at sync 3: every shocked target within 2 m + 0.2 m/pt of you, no jumps': dict(
        ops=[['damage', 0, LIGHTNING, 23.625], ['damage', 1, LIGHTNING, 23.625], ['drainMagicka', 1, 11.8125]],
        absent=[['damage', 2], ['damage', 3]]),
    # 融斷 on a frozen target (v0.4 2.7 D_burst; 5.4 冰封融斷): stage 3 K = 3 -> frost 10 × 3 × 1.05 = 31.5; without the
    # branch no 碎冰 (still frozen), with it a normal 碎冰 20% of 100 = 20 true (not × K_sync), a boss 10% of 1000 = 100
    'fusion stage 3 on a frozen target without 冰封融斷: the fusion hit only, it stays frozen': dict(
        ops=[['damage', 1, FROST, 31.5]], absent=[['damage', 1, 0]], boards={(1, 'Frozen'): [1.0, 3.0], (1, 'Hush'): [1.0, 10.0]}),
    'fusion stage 3 on a frozen target with 冰封融斷: the fusion hit and a 碎冰 (not ×K_sync)': dict(
        ops=[['damage', 1, FROST, 31.5], ['damage', 1, 0, 20.0]]),
    'fusion stage 3 on a frozen boss with 冰封融斷: 碎冰 10% of its max health': dict(
        ops=[['damage', 1, FROST, 31.5], ['damage', 1, 0, 100.0]]),
    # divine 10 × 3 × 1.05 × 1.2 (day) = 37.8, no heal of 裁決; astral 10 × 3 × 1.05 = 31.5, and the 2 stars detonate
    # through the end's state part: 2 × 10 × 1.05 = 21 (not × K_sync); one resonance layer (20 s)
    'fusion stage 3 of a divine and an astral mark: B_max × 3 × G (day ×1.2), no 裁決 ×2 / 星落 ×2, the stars still detonate': dict(
        ops=[['damage', 1, DIVINE, 37.8], ['damage', 2, ASTRAL, 31.5], ['damage', 2, ASTRAL, 21.0]], absent=[['heal', -1]],
        boards={(-1, 'Resonance'): [1.0, 20.0]}),
    # a named (unique) enemy is not exempt (2.9 必要角色 only): level 10 -> tier 2 (cap 13, 120 s)
    'death: a named (unique, not essential) enemy rises (2.9: only essential ones are exempt)': dict(
        ops=[['event', 0, 'Raise', 2.0, 13.0, 120.0, 0.0, 0.0]]),
    'death: an essential NPC with 5 curse does not rise': dict(absent=[['event', 0, 'Raise']]),
    'death: a named (unique) enemy turns to ash; an essential one does not': dict(ops=[['event', 0, 'Ash'], ['magicka', -1, 20.0]]),
    'death: an essential enemy with the divine mark is not turned to ash': dict(absent=[['event', 0, 'Ash']]),
    # 毒斷: poison 3/s × 4 × K_sync 1 = 12 for the 10 s left; the marker ×4
    "burst 毒斷: the burst's catalysis ×4 (not ×2)": dict(boards={(1, 'PoisonDot'): [12.0, 10.0], (1, 'Catalyzed'): [4.0, 10.0]}),
    # tier 3 (level 20) + 1 (curse 5) = 4: cap 30, 180 s × 2 (full cap), attack +50%
    'death: 亡者歸來 — level 20, curse 5 of 5: tier 4, +50% attack, double time': dict(
        ops=[['event', 0, 'Raise', 4.0, 30.0, 360.0, 0.5, 0.0]]),
    # R = 2 × 5 = 10 < 30 (30% of 100) → S = 15, 1.25 a second for 12 s; per dose 9 × 0.2116 × 1.05 = 1.99962
    'death: the poison spreads S = max(R, 30% max health) × 50% to everyone within 15 m (no cap on count)': dict(
        boards={(1, 'PoisonDot'): [1.25, 12.0], (2, 'PoisonDot'): [4.25, 20.0], (7, 'PoisonDot'): [1.25, 12.0]}),
    # 不死 at 20%: stamina 100 - 30 = 70; health to 30% + 1 = 31 → heal 11; 飲血 heal 20% of 100 = 20
    'death: 飲血, 血承 (resists, armour, max health), 不死 at 20% health, 無魔 over the max, 連殺': dict(
        ops=[['heal', -1, 20.0], ['heal', -1, 11.0], ['stamina', -1, 70.0], ['event', -1, 'Sneak', 5.0], ['magicka', -1, 20.0]],
        boards={(-1, 'InheritFire'): [20.0, 15.0], (-1, 'InheritArmor'): [10.0, 15.0], (-1, 'InheritHealth'): [30.0, 15.0]}),
    # 回聲 (25% + 5 × 1%) × 1.5 night = 45% of 12 = 5.4
    'echo: 25% (+1%/pt) of the star proc to the other resonance targets, night ×1.5; 星鏈 once per 2 s': dict(
        ops=[['damage', 1, ASTRAL, 5.4], ['damage', 2, ASTRAL, 5.4]], boards={(1, 'Star'): [2.0, 20.0]}),
    # 侵蝕 4 × (2 + 5 × 0.2) × 1.25 = 15
    'hit bodies: the curse erodes every resist 2%/layer (+0.2%/pt) × 萬象': dict(
        ops=[['timed', 0, 'fireResistDebuff', 15.0, 8.0], ['timed', 0, 'poisonResistDebuff', 15.0, 8.0]]),
}
