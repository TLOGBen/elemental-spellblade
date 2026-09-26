"""Round 22 (slice N3) reference model of the status layer, written from 元素魔戰士規劃-v0.4.md.

The native tests compare native/include/Status.h against this model on generated scenarios (build/fix22-status-table.json).
It is written from the design text, independently of the C++: plain Python, v0.4's own wording in the comments.

  NODE_NAMES   the nodes the status layer reads, by v0.4 name; their slots come from the identity table (never from here)
  scenarios    a deterministic set of pre-hit boards / nodes / attacks and what v0.4 says must happen

Sources in v0.4: 2.2 (marks), 2.3 (statuses and the self resources), 2.6 (open / end), 2.7 (DoT and poison formulas,
the white-hot source), 5.2-5.13 (nodes). Decisions the design leaves open are the ledger's (.codex/impl-fix-round22.html).
"""
from __future__ import annotations

# ---------------------------------------------------------------- the nodes the status layer reads

NODE_NAMES = {
    # 5.2 common
    'kCommonMarkDuration': ('common', '印記持續'),
    'kCommonDualMark': ('common', '雙印'),
    'kCommonResidual': ('common', '疊印'),
    'kCommonCapBonus': ('common', '每種元素狀態上限'),
    'kCommonOmni': ('common', '萬象'),
    'kCommonJump': ('common', '跳印'),
    'kCommonEnd': ('common', '終焉'),
    'kCommonEndAgain': ('common', '終焉再'),
    'kCommonSyncEnd': ('common', '同調三段時終焉'),
    # 5.3 fire
    'kFireSourceN': ('fire', '火源倍率 N'),
    'kFireMeltdown': ('fire', '熔斷'),
    'kFireKindling': ('fire', '添薪'),
    'kFireBrand': ('fire', '烙印'),
    'kFireMoltenCore': ('fire', '熔心'),
    'kFireMoltenBody': ('fire', '熔身'),
    'kFireBath': ('fire', '火浴'),
    'kFireInferno': ('fire', '業火'),
    'kFireForge': ('fire', '熔爐'),
    'kFireOpenQuick': ('fire', '開印後 5 秒內熱度升階免等待'),
    'kFireIgnite': ('fire', '引火'),
    'kFireFlareOpen': ('fire', '烈火點燃'),
    'kFireBlazeStart': ('fire', '烈火之始'),
    'kFireTinder': ('fire', '火種'),
    'kFireFierce': ('fire', '猛爆'),
    'kFireResidualPressure': ('fire', '餘壓'),
    'kFireBlaze': ('fire', '熾焰'),
    'kFireConsume': ('fire', '爆燃的消耗加成'),
    'kFireEmber': ('fire', '餘燼'),
    # 5.4 frost
    'kFrostAccumulate': ('frost', '每次命中凍結累積'),
    'kFrostErode': ('frost', '寒蝕'),
    'kFrostSkin': ('frost', '霜膚'),
    'kFrostFrozenProc': ('frost', '冰封目標受冰附傷'),
    'kFrostPermafrost': ('frost', '永凍'),
    'kFrostFrostbite': ('frost', '凍傷'),
    'kFrostOpenFreeze': ('frost', '開印凍結'),
    'kFrostDeepRime': ('frost', '深霜結'),
    'kFrostIceArmor': ('frost', '冰甲'),
    'kFrostLock': ('frost', '霜鎖'),
    'kFrostAbsolute': ('frost', '絕霜'),
    'kFrostSharp': ('frost', '銳碎'),
    'kFrostLinger': ('frost', '寒留'),
    'kFrostCoffin': ('frost', '冰棺'),
    # 5.6 earth
    'kEarthDeepFissure': ('earth', '深裂痕'),
    'kEarthRift': ('earth', '裂地'),
    # 5.7 wind
    'kWindRideWind': ('wind', '御風'),
    'kWindDarkWind': ('wind', '暗風'),
    'kWindKillStreak': ('wind', '連殺'),
    'kWindAirChase': ('wind', '空中追擊'),
    # 5.8 blood
    'kBloodLayerDamage': ('blood', '流血每層傷害'),
    'kBloodDeepWound': ('blood', '深創'),
    'kBloodStanch': ('blood', '止血'),
    'kBloodOpenLayers': ('blood', '開印流血'),
    'kBloodDeepMark': ('blood', '深血痕'),
    'kBloodLead': ('blood', '血引'),
    # 5.9 divine
    'kDivineHolyBonus': ('divine', '聖佑各階武器傷害與聖傷加成'),
    'kDivineRetribution': ('divine', '神罰'),
    'kDivineJudgeDamage': ('divine', '聖裁傷害'),
    'kDivineStigma': ('divine', '聖痕'),
    'kDivineDawn': ('divine', '聖啟'),
    'kDivineMercy': ('divine', '慈光'),
    'kDivineLead': ('divine', '聖引'),
    'kDivineHolyDomain': ('divine', '神聖領域'),
    # 5.10 poison
    'kPoisonDoseDamage': ('poison', '每劑傷害'),
    'kPoisonThreshold': ('poison', '傳染門檻'),
    'kPoisonOpenDoses': ('poison', '開印劑數'),
    'kPoisonToxicStart': ('poison', '劇毒之始'),
    'kPoisonFester': ('poison', '潰爛'),
    'kPoisonPlague': ('poison', '瘟疫'),
    'kPoisonMiasmaRate': ('poison', '瘴氣每秒傳遞劑量'),
    'kPoisonLinger': ('poison', '延毒'),
    # 5.11 water
    'kWaterPressure': ('water', '水壓'),
    'kWaterPressureDamage': ('water', '水壓每層水附傷'),
    'kWaterDeepSoak': ('water', '深濕'),
    'kWaterOceanStart': ('water', '汪洋之始'),
    'kWaterStrongGuide': ('water', '強引'),
    'kWaterOcean': ('water', '汪洋'),
    'kWaterPurgeTide': ('water', '淨潮'),
    'kWaterEbb': ('water', '退潮'),
    # 5.12 darkness
    'kDarkFearCurse': ('darkness', '懼咒'),
    'kDarkIllusionTime': ('darkness', '幻覺持續'),
    'kDarkFrenzyCurse': ('darkness', '狂咒'),
    'kDarkAbyss': ('darkness', '深淵'),
    'kDarkOpenCurse': ('darkness', '開印詛咒'),
    'kDarkConfusion': ('darkness', '迷亂'),
    'kDarkNether': ('darkness', '冥印'),
    'kDarkLinger': ('darkness', '咒延'),
    'kDarkDevour': ('darkness', '噬咒'),
    'kDarkCurseLost': ('darkness', '死咒的「已損失生命」係數'),
    'kDarkGlutton': ('darkness', '饕餮'),
    'kDarkEcho': ('darkness', '回魘'),
    'kDarkPhantom': ('darkness', '幻影'),
    # 5.13 astral
    'kAstralCap': ('astral', '星痕層數上限'),
    'kAstralWeakness': ('astral', '星痕弱點'),
    'kAstralDelay': ('astral', '星痕延遲'),
    'kAstralLock': ('astral', '星鎖'),
    'kAstralRadiance': ('astral', '星耀'),
}

# The element skeleton lines read per element: [element] -> main-line label in that element's tree ('' = none).
# `{x}` is the element's short name. Wind's opening adept slot is its pull distance, not a proc line.
SKELETON = {
    'kOpenProc': (1, 1, '開印後 5 秒內{x}附傷', {'wind'}),
    'kMarkDuration': (1, 2, '{x}印記持續', set()),
    'kOpenEffect': (1, 4, '開印效果', set()),
    'kTakeover': (2, 2, '終焉後 5 秒內接管元素附傷', {'fire', 'earth', 'wind', 'blood', 'darkness'}),
    'kEndMain': (2, 0, '終焉', set()),
}
# 關閉傳奇主線 (2, 4): the element's own end move.
SIGNATURE = {'fire': '爆燃', 'frost': '碎冰', 'lightning': '放電', 'earth': '地震', 'wind': '落地傷害', 'blood': '血潮',
             'divine': '裁決', 'poison': '催毒期間中毒傷害', 'water': '導引', 'darkness': '死咒', 'astral': '星落'}


# ================================================================ the scenario model
# One World = the pre-hit boards (target, you), the nodes you own, the tuning, and the ops the rules produce. Every
# rule below is v0.4's wording turned into arithmetic; the C++ is never consulted. Random draws are deterministic for
# the table: a chance p succeeds when p >= 0.5 (so 3.2 layers round to 3, 3.6 to 4), a real draw is the midpoint.

FIRE, FROST, LIGHTNING, EARTH, WIND, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL = range(1, 12)
TREE = [None, 'fire', 'frost', 'lightning', 'earth', 'wind', 'blood', 'divine', 'poison', 'water', 'darkness', 'astral']
SHORT = [None, '火', '冰', '雷', '土', '風', '血', '聖', '毒', '水', '暗', '星']
EVENT_ARGS = {'Open': 4, 'End': 7, 'Frozen': 1, 'Hallucinate': 2, 'Judgment': 1, 'Splash': 1, 'Shatter': 1,
              'Landing': 1, 'Rise': 0}
CUT, BURST, EXPIRE = 0, 1, 2
MARK_JUMPED, MARK_EXTENDED = 2, 4


class Slot:
    def __init__(self, magnitude=0.0, elapsed=0.0, duration=0.0):
        self.magnitude, self.elapsed, self.duration = float(magnitude), float(elapsed), float(duration)

    def remaining(self):
        return max(0.0, self.duration - self.elapsed)

    def layers(self):
        return int(self.magnitude + 0.5)


class Board:
    def __init__(self):
        self.kinds = {}      # suffix -> Slot
        self.marks = {}      # element -> Slot
        self.bleed = None    # Slot (magnitude = damage per second)
        self.poison = None
        self.frenzied = False
        self.max_slow = 0.0

    def has(self, kind):
        return kind in self.kinds

    def layers(self, kind):
        return self.kinds[kind].layers() if kind in self.kinds else 0

    def mag(self, kind):
        return self.kinds[kind].magnitude if kind in self.kinds else 0.0


class World:
    def __init__(self, damage, *, ranks=None, branches=None, sync=0, mult_duration=1.0, mult_cooldown=1.0,
                 node_scale=3.0, base=1.0, recovery=1.0, mult_dot=1.0, poison_k=0.2116, bleed_k=0.1143, wet=False,
                 stormy=False, night=False, interior=False, slow_cap=70.0, wet_slow=15.0, level=None,
                 hp=100.0, hp_max=100.0, body=None, ice_armor=False):
        self.B = damage                                   # element -> (B_min, B_max)
        self.ranks = dict(ranks or {})                    # (tree, v0.4 name) -> points
        self.branches = set(branches or ())               # (tree, v0.4 name)
        self.sync, self.mult_duration, self.mult_cooldown = sync, mult_duration, mult_cooldown
        self.node_scale, self.base, self.recovery, self.mult_dot = node_scale, base, recovery, mult_dot
        self.poison_k, self.bleed_k = poison_k, bleed_k
        self.wet, self.stormy, self.night, self.interior = wet, stormy, night, interior
        self.slow_cap, self.wet_slow = slow_cap, wet_slow
        self.level = dict(level or {})                   # tree id -> ESSB_Lvl
        self.hp, self.hp_max = hp, hp_max                # you (health and max health; permanent = max here)
        self.body = dict(health=100.0, health_max=100.0, stamina=100.0, stamina_max=100.0, vip=False, undead=False,
                         distance=0.0)
        self.body.update(body or {})
        self.ice_armor = ice_armor
        self.target, self.me = Board(), Board()
        self.ops = []

    # ---------------------------------------------------------------- small helpers
    def rank(self, tree, name):
        return self.ranks.get((tree, name), 0)

    def has(self, tree, name):
        return (tree, name) in self.branches

    def pct(self, points, base):
        return points * base * self.node_scale          # 3: percentage lines count base x NodeScale per point

    def scaled(self, seconds):
        return seconds * self.mult_duration              # the MCM duration multiplier

    def cooldown(self, seconds):
        return seconds * self.mult_cooldown

    def chance(self, p):
        return p >= 0.5

    def stochastic(self, value):
        whole = int(value)
        rest = value - whole
        return whole + (1 if rest > 0 and self.chance(rest) else 0)

    def g(self, element):
        return 1 + 0.05 * max(1, self.level.get(TREE[element], 1))   # 2.7 G(L)

    def bmax(self, element):
        return self.B[element][1]

    def react_scale(self, element):
        """2.7 D_react's categorical part the status layer uses: G(L) x damage multiplier x day / night."""
        scale = self.g(element) * self.base
        if not self.interior and ((element == DARKNESS and self.night) or (element == DIVINE and not self.night)):
            scale *= 1.2
        return scale

    def vulnerability(self):
        t, me = self.target, self.me
        m = 1.2 if me.has('Bloodthirst') else 1.0
        if self.has('wind', '御風') and t.has('Unbalance'):   # v0.4 5.7: only the slow immunity needs sync 3
            m *= 1.3
        if self.has('wind', '空中追擊') and t.has('Airborne'):
            m *= 1.5
        if t.has('StarLock'):
            m *= 1.1
        if t.has('DomainAstral'):
            m *= 1.2
        return m

    def cap_bonus(self):
        return min(3, self.rank('common', '每種元素狀態上限') // 5)

    def omni(self):
        return 1.25 if self.has('common', '萬象') else 1.0

    # ---------------------------------------------------------------- writes
    def put(self, board, kind, magnitude, seconds):
        board.kinds[kind] = Slot(magnitude, 0.0, seconds)

    def drop(self, board, kind):
        board.kinds.pop(kind, None)

    def op(self, *row):
        self.ops.append(list(row))

    def event(self, name, *args):
        self.op('event', name, *[float(a) for a in args])

    # ---------------------------------------------------------------- durations
    def mark_seconds(self, element, linger=False):
        seconds = 10.0 if element == WATER else 8.0                                     # 2.2
        seconds += 0.2 * self.rank('common', '印記持續')                                  # 5.2
        seconds += 0.2 * self.rank(TREE[element], f'{SHORT[element]}印記持續')             # 5.x 開啟專精主線
        return self.scaled(seconds + (4.0 if linger else 0.0))                           # 寒留 +4

    def soak_seconds(self):
        return self.scaled(10.0 + 0.3 * self.rank('water', '浸濕持續'))

    def frozen_seconds(self):
        return self.scaled(3.0 + (2.0 if self.has('frost', '永凍') else 0.0))

    def fuse_seconds(self):
        return self.scaled(12.0 if self.has('fire', '添薪') else 8.0)

    # ---------------------------------------------------------------- frost (2.3, 2.6, 5.4)
    def freeze(self, seconds, shatter_mult):
        t = self.target
        self.put(t, 'Frozen', shatter_mult, seconds)
        self.put(t, 'Freeze', 5, seconds)
        if t.has('Crystal'):
            self.put(t, 'Crystal', t.mag('Crystal'), seconds + 1.0)   # 冰晶 outlive 冰封 by 1 s (review fix 2)
        self.event('Frozen', seconds)

    def add_freeze(self, amount, erode_power=False):
        t = self.target
        if t.has('Frozen'):
            return
        if self.stormy:
            amount *= 2          # 暴風雪累積 ×2
        if t.has('DomainFrost'):
            amount *= 2          # 冰原：凍結累積 ×2
        after = min(5, t.layers('Freeze') + self.stochastic(amount))
        if after <= 0:
            return
        if after >= 5:
            self.freeze(self.frozen_seconds(), 1.0)
            return
        seconds = self.scaled(6.0) + (self.scaled(2.0) if erode_power else 0.0)
        self.put(t, 'Freeze', after, seconds)
        if t.has('Crystal'):
            self.put(t, 'Crystal', t.mag('Crystal'), seconds)
        self.op('slow', min(25.0, max(0.0, min(self.slow_cap, 70.0))), seconds)   # 凍結量表 ≥1：減速 25%

    def shatter(self, source, mult=1.0):
        t, b = self.target, self.body
        sharp = self.has('frost', '銳碎')
        pct = (0.12 if sharp else 0.10) if b['vip'] else (0.25 if sharp else 0.20)
        pct *= 1 + self.pct(self.rank('frost', '碎冰'), 0.03)                          # 碎冰 +3%／點，乘在 20% 上
        pct += t.layers('Crystal') * (0.025 if b['vip'] else 0.05)
        again = t.mag('Frozen') if t.has('Frozen') else 1.0
        self.op('damage', 0, b['health_max'] * pct * again * mult * self.base)
        for k in ('Frozen', 'Crystal', 'Freeze'):
            self.drop(t, k)
        self.event('Shatter', source)
        if self.has('frost', '冰棺') and again >= 1.0:
            self.freeze(self.scaled(2.0), 0.5)                                            # 冰棺：再冰封 2 秒，第二次 ×0.5

    # ---------------------------------------------------------------- blood
    def per_bleed_layer(self):
        per = self.bmax(BLOOD) * self.bleed_k * self.mult_dot * self.g(BLOOD) * self.base
        per *= (1 + self.pct(self.rank('blood', '流血每層傷害'), 0.02)) * self.omni()
        if self.has('blood', '止血') and self.hp / self.hp_max < 0.3:
            per *= 1.5
        return per

    def add_bleed(self, layers):
        t = self.target
        cap = (12 if self.has('blood', '深創') else 8) + self.cap_bonus()
        after = min(cap, t.layers('Bleed') + layers)
        if after <= 0:
            return
        seconds = self.scaled(10.0)
        self.put(t, 'Bleed', after, seconds)
        per_second = after * self.per_bleed_layer()
        self.op('bleedDot', per_second, seconds)
        t.bleed = Slot(per_second, 0, seconds)

    # ---------------------------------------------------------------- poison (2.7)
    def per_dose(self):
        return (self.bmax(POISON) * self.poison_k * self.mult_dot * self.g(POISON) * self.base *
                (1 + self.pct(self.rank('poison', '每劑傷害'), 0.02)) * self.omni())

    def factor(self):
        """The catalysis multiplier the poison carries (the 催毒 marker's magnitude), 1 when not catalysed."""
        t = self.target
        return t.mag('Catalyzed') if t.has('Catalyzed') and t.mag('Catalyzed') > 0 else 1.0

    def base_doses(self, board=None):
        b = board or self.target
        per = self.per_dose()
        if not b.poison or per <= 0:
            return 0.0
        f = b.kinds['Catalyzed'].magnitude if 'Catalyzed' in b.kinds and b.kinds['Catalyzed'].magnitude > 0 else 1.0
        return b.poison.magnitude / f / per

    def set_poison(self, magnitude, remaining):
        t = self.target
        self.op('poisonDot', magnitude, remaining)
        t.poison = Slot(magnitude, 0, remaining)
        if t.has('Catalyzed'):
            self.put(t, 'Catalyzed', t.mag('Catalyzed'), remaining)

    def add_doses(self, doses):
        """2.7: counted in base doses (a catalysed poison keeps its multiplier; review fix 1)."""
        if doses <= 0:
            return
        t = self.target
        m = t.poison.magnitude if t.poison else 0.0
        rest = t.poison.remaining() if t.poison else 0.0
        per, f = self.per_dose(), self.factor()
        new_m = min(m / f + doses * per, 10 * per) * f
        new_rest = self.scaled(12.0) if m <= 0 else min(rest + self.scaled(3.0), self.scaled(15.0))
        self.set_poison(new_m, new_rest)

    def spread_doses(self, doses):
        """2.7 擴散一劑: m' = m + doses (same base-dose cap), d' = max(d - t, 12)."""
        if doses <= 0:
            return
        t = self.target
        m = t.poison.magnitude if t.poison else 0.0
        rest = t.poison.remaining() if t.poison else 0.0
        per, f = self.per_dose(), self.factor()
        self.set_poison(min(m / f + doses * per, 10 * per) * f, max(rest, self.scaled(12.0)))

    def miasma_doses(self):
        """瘴氣: doses a second this target gives each enemy within 3 m (0 below the threshold)."""
        t = self.target
        if not t.poison:
            return 0.0
        threshold = 1 if self.has('poison', '傳染門檻') else 5
        if self.base_doses() + 0.001 < threshold:
            return 0.0
        rate = 1.0 if t.has('Catalyzed') else 0.5
        return rate + self.pct(self.rank('poison', '瘴氣每秒傳遞劑量'), 0.05)

    def plague_chance(self):
        return 0.05 * self.rank('poison', '瘟疫') if self.target.poison and self.sync >= 3 else 0.0

    # ---------------------------------------------------------------- water
    def set_pressure(self, layers):
        t = self.target
        cap = 5 + self.cap_bonus()
        before = t.layers('Pressure')
        after = min(cap, layers)
        if after <= 0:
            return
        self.put(t, 'Pressure', after, self.scaled(8.0))
        if after >= cap and before < cap:
            self.op('wash', 2 * self.bmax(WATER) if self.has('water', '淨潮') else 0.0)   # 滿格沖刷（裁定 R5）

    # ---------------------------------------------------------------- darkness
    def curse_cap(self):
        cap = 5
        if self.sync >= 3:
            cap += min(5, self.rank('darkness', '深淵') // 3)
        return cap + self.cap_bonus()

    def add_curse(self, layers):
        t = self.target
        before = t.layers('Curse')
        after = min(self.curse_cap(), before + layers)
        if after <= 0 or layers <= 0:
            return
        self.put(t, 'Curse', after, self.scaled(8.0))
        fear_at = 2 if self.has('darkness', '懼咒') else 3
        frenzy_at = 4 if self.has('darkness', '狂咒') else 5
        longer = 0.1 * self.rank('darkness', '幻覺持續')
        if before < frenzy_at <= after and not t.has('FrenzyCooldown'):
            self.put(t, 'FrenzyCooldown', 1, self.cooldown(20.0))
            self.event('Hallucinate', 2, self.scaled(3.0 + longer))
        elif before < fear_at <= after and not t.has('FearCooldown'):
            self.put(t, 'FearCooldown', 1, self.cooldown(12.0))
            self.event('Hallucinate', 1, self.scaled(2.0 + longer))

    # ---------------------------------------------------------------- astral
    def star_cap(self):
        return 3 + self.rank('astral', '星痕層數上限') // 5 + self.cap_bonus()

    def add_stars(self, layers):
        t = self.target
        after = min(self.star_cap(), t.layers('Star') + layers)
        if after <= 0:
            return
        self.put(t, 'Star', after, self.scaled(30.0))
        delay = max(0.5, 2.0 - 0.1 * self.rank('astral', '星痕延遲'))
        self.put(t, 'StarFuse', 1, self.scaled(delay))

    def detonate_stars(self, mult):
        t = self.target
        layers = t.layers('Star')
        vulnerability = self.vulnerability()
        self.drop(t, 'StarFuse')
        self.drop(t, 'Star')
        if layers > 0:
            self.op('damage', ASTRAL, layers * self.bmax(ASTRAL) * self.react_scale(ASTRAL) * self.omni() * mult * vulnerability)

    # ---------------------------------------------------------------- the ladders on you
    def heat_tier(self):
        me = self.me
        if me.has('Heat4'):
            return 4
        if me.has('Heat3') or me.has('MoltenBody'):
            return 3
        return 2 if me.has('Heat2') else 1 if me.has('Heat1') else 0

    def set_heat(self, tier, fuse=0.0):
        me = self.me
        for k in range(1, 5):
            if k != tier:
                self.drop(me, f'Heat{k}')
        if tier <= 0:
            self.drop(me, 'HeatDecay')
            return
        if tier == 3:
            self.put(me, 'Heat3', 0, fuse if fuse > 0 else self.fuse_seconds())
            self.drop(me, 'HeatDecay')
        elif tier == 4:
            self.put(me, 'Heat4', 0, self.scaled(6.0))
            self.drop(me, 'HeatDecay')
        else:
            self.put(me, f'Heat{tier}', 1, 3600.0)
            self.put(me, 'HeatDecay', 1, self.scaled(6.0))

    def raise_heat(self, steps):
        me = self.me
        if me.has('MoltenBody'):
            return
        tier = self.heat_tier()
        if tier >= 3:
            return
        kind = f'Heat{max(1, tier)}'
        mature = tier == 0 or me.kinds[kind].elapsed >= 2.0
        open_ = me.kinds.get('OpenBoost')
        if open_ and open_.layers() == FIRE and self.rank('fire', '開印後 5 秒內熱度升階免等待') > 0 and open_.remaining() > 0:
            mature = True
        if me.has('FireDomainPlayer'):
            mature = True
        if not mature:
            if tier > 0:
                self.put(me, 'HeatDecay', 1, self.scaled(6.0))
            return
        self.set_heat(min(3, tier + steps))

    def holy_tier(self):
        me = self.me
        return 3 if me.has('Holy3') else 2 if me.has('Holy2') else 1 if me.has('Holy1') else 0

    def set_holy(self, tier):
        me = self.me
        for k in range(1, 4):
            if k != tier:
                self.drop(me, f'Holy{k}')
        if tier <= 0:
            self.drop(me, 'HolyDecay')
            return
        if not me.has(f'Holy{tier}'):
            self.put(me, f'Holy{tier}', 0, 3600.0)
        self.put(me, 'HolyDecay', 1, self.scaled(8.0))

    def raise_holy(self, steps):
        tier = self.holy_tier()
        mature = tier == 0 or self.me.kinds[f'Holy{tier}'].elapsed >= 2.0
        self.set_holy(min(3, tier + steps) if mature else tier)

    def blood_zone(self):
        f = self.hp / self.hp_max
        return 1 if f > 0.7 else 2 if f >= 0.3 else 3

    # ---------------------------------------------------------------- open (2.6, the state part)
    def open_state(self, element, mult, cut_from):
        t, me = self.target, self.me
        window = 5.0 + (0.5 * (self.rank('fire', '開印後 5 秒內熱度升階免等待') // 5) if element == FIRE else 0.0)
        self.put(me, 'OpenBoost', element, self.scaled(window))
        if element == FIRE:
            tier = self.heat_tier()
            if tier == 3 and me.has('Heat3') and self.has('fire', '烈火點燃'):
                fuse = me.kinds['Heat3']
                extra = min(2.0, 4.0 - fuse.magnitude)
                if extra > 0:
                    self.put(me, 'Heat3', fuse.magnitude + extra, fuse.remaining() + extra)
            elif self.has('fire', '烈火之始') and self.body['health'] / self.body['health_max'] > 0.8 and tier < 3:
                self.set_heat(3)
            else:
                self.raise_heat(2 if self.has('fire', '引火') else 1)
        elif element == FROST:
            if self.has('frost', '深霜結') and not t.has('Frozen'):
                self.put(t, 'Crystal', min(3, t.layers('Crystal') + 1), self.scaled(6.0))
            if self.has('frost', '絕霜') and self.sync >= 3:
                if not t.has('Frozen'):
                    self.freeze(self.frozen_seconds(), 1.0)
            else:
                self.add_freeze((3 + self.rank('frost', '開印凍結') // 3) * mult)
            if self.has('frost', '霜鎖'):
                if t.max_slow >= min(self.slow_cap, 70.0):
                    self.add_freeze(1.0)
                else:
                    self.op('slow', 30.0, self.scaled(3.0))
        elif element == EARTH:
            self.put(t, 'Fissure', 1, self.scaled(8.0))
            b = self.body
            if self.has('earth', '深裂痕') and b['stamina'] / b['stamina_max'] < 0.5:
                self.down()
        elif element == WIND:
            self.put(t, 'Unbalance', 1, self.scaled(3.0))
        elif element == BLOOD:
            layers = 2 + self.rank('blood', '開印流血') // 5
            if self.has('blood', '深血痕'):
                zone = self.blood_zone()
                layers += 2 if zone == 1 else 1 if zone == 2 else 0
            self.add_bleed(self.stochastic(layers * mult))
        elif element == DIVINE:
            self.raise_holy(1)
            if self.has('divine', '聖啟') and self.sync >= 3 and self.holy_tier() < 2:
                self.set_holy(2)
            if self.has('divine', '慈光'):
                self.put(me, 'Punish', min(5, me.layers('Punish') + 2), self.scaled(8.0))
        elif element == POISON:
            doses = 3 + self.rank('poison', '開印劑數') // 3
            if self.has('poison', '劇毒之始') and self.sync >= 3:
                doses *= 2
            self.add_doses(self.stochastic(doses * mult))
        elif element == WATER:
            lock = self.has('water', '汪洋之始') and self.sync >= 3
            self.put(t, 'Soak', 2 if lock else 1, 3600.0 if lock else self.soak_seconds())
            self.op('slow', min(self.wet_slow, max(0.0, min(self.slow_cap, 70.0))) * mult, self.soak_seconds())
            if self.has('water', '深濕') and self.has('water', '水壓') and self.wet:
                self.set_pressure(5 + self.cap_bonus())
        elif element == DARKNESS:
            self.add_curse(self.stochastic((2 + self.rank('darkness', '開印詛咒') // 5) * mult))
            if self.has('darkness', '幻影'):
                self.put(t, 'Phantom', 1, self.scaled(3.0))   # 5.12 幻影 (ruling (c)): the PERK rolls per hit
        elif element == ASTRAL:
            self.add_stars(1)
            if self.has('astral', '星鎖'):
                self.put(t, 'StarLock', 1, self.scaled(3.0))
            if self.has('astral', '星耀') and self.sync >= 3:
                self.detonate_stars(2.0)
        if cut_from == BLOOD and self.has('blood', '血引'):
            self.add_bleed(2)
        if cut_from == DIVINE and self.has('divine', '聖引'):
            self.op('heal', self.bmax(DIVINE) * self.recovery)

    def down(self):
        rift = self.has('earth', '裂地') and self.target.has('Fissure')
        self.put(self.target, 'Downed', 1, self.scaled(5.0 if rift else 3.0))

    # ---------------------------------------------------------------- end (2.6, the state part)
    def end_node_mult(self, element):
        common = 1 + self.pct(self.rank('common', '終焉'), 0.01) + self.pct(self.rank('common', '終焉再'), 0.01)
        if self.sync >= 3:
            common += self.pct(self.rank('common', '同調三段時終焉'), 0.01)
        return common * (1 + self.pct(self.rank(TREE[element], '終焉'), 0.02))

    def end_body(self, element, reason, mult, power=False, chain=False):
        t, me = self.target, self.me
        self.put(t, 'EndCooldown', 1, self.cooldown(1.0))
        cut = reason == CUT
        if t.has('Guided'):
            mult *= t.mag('Guided')
            self.drop(t, 'Guided')
        settle = mult if chain else mult * self.end_node_mult(element)
        value = [0.0, 0.0, 0.0]
        if element == FIRE:
            heat = max(self.heat_tier(), me.layers('VentedHeat'))
            self.drop(me, 'VentedHeat')
            keep = self.has('fire', '猛爆')
            bonus, consumed = 0.0, 0
            for kind, cap in (('Freeze', 5), ('Curse', self.curse_cap()), ('Pressure', 5 + self.cap_bonus())):
                if t.layers(kind) > 0:
                    bonus += min(0.75, 0.25 * 3 * t.layers(kind) / cap)
                    consumed += 1
                    if not keep:
                        self.drop(t, kind)
            for kind in ('Fissure', 'Soak', 'Unbalance'):
                if t.has(kind):
                    bonus += 0.25
                    consumed += 1
                    if not keep:
                        self.drop(t, kind)
            if not keep and t.has('Frozen'):
                self.drop(t, 'Frozen')
                self.drop(t, 'Crystal')
            dots = (t.bleed.magnitude * t.bleed.remaining() if t.bleed else 0) + \
                   (t.poison.magnitude * t.poison.remaining() if t.poison else 0)
            if dots > 0:
                domain = 1.2 if t.has('DomainFire') else 1.0
                self.op('damage', FIRE, dots * 0.5 * settle * domain)
                consumed += (1 if t.bleed else 0) + (1 if t.poison else 0)
                if not keep:
                    self.op('removeDots')
                    self.drop(t, 'Bleed')
                    self.drop(t, 'Catalyzed')
                    t.bleed = t.poison = None
            if t.has('Star'):
                consumed += 1
                self.detonate_stars(1.0)
            bonus += self.pct(self.rank('fire', '爆燃的消耗加成'), 0.01) * consumed
            value = [heat, bonus, 1.5 if heat >= 3 and self.has('fire', '熾焰') else 1.0]
        elif element == FROST:
            # 冰封融斷 (5.4, round 24 commander ruling): a fusion shatters a frozen target only with the branch
            if t.has('Frozen') and (reason != BURST or self.has('frost', '冰封融斷')):
                self.shatter(2, settle)
                value[0] = 1.0
        elif element == LIGHTNING:
            hit_cut = cut and power
            value = [1.5 if hit_cut else 1.0, 0.5, 1.0 if hit_cut else 0.0]
        elif element == WIND:
            self.drop(t, 'Unbalance')
        elif element == BLOOD:
            value[0] = t.bleed.magnitude * t.bleed.remaining() if t.bleed else 0.0
            if t.bleed:
                self.op('bleedDot', 0.0, 0.0)
                t.bleed = None
            self.drop(t, 'Bleed')
        elif element == DIVINE:
            value[0] = self.holy_tier()
        elif element == POISON:
            if t.poison:
                factor = 3.0 if self.has('poison', '潰爛') else 2.0
                if reason == BURST and self.has('poison', '毒斷'):
                    factor = 4.0                                    # 5.10 毒斷（round 24）：融斷的催毒 ×4
                factor *= 1 + self.pct(self.rank('poison', '催毒期間中毒傷害'), 0.03)
                remaining = t.poison.remaining() + (self.scaled(4.0) if self.has('poison', '延毒') else 0.0)
                self.put(t, 'Catalyzed', self.factor() * factor * settle, remaining)
                self.set_poison(t.poison.magnitude * factor * settle, remaining)
        elif element == WATER:
            if cut:
                guide = (2.0 if self.has('water', '強引') else 1.5) * (1 + self.pct(self.rank('water', '導引'), 0.03))
                self.put(t, 'Guided', guide * mult, self.scaled(30.0))
            if t.has('Soak') and t.mag('Soak') > 1.5:
                self.put(t, 'Soak', 1, self.soak_seconds())
            if self.has('water', '汪洋'):
                self.put(t, 'Soak', 1, self.scaled(30.0))
            if self.has('water', '退潮') and reason != EXPIRE and not t.has('WashCooldown'):
                self.put(t, 'WashCooldown', 1, self.cooldown(10.0))
                self.op('wash', 2 * self.bmax(WATER) if self.has('water', '淨潮') else 0.0)
        elif element == DARKNESS:
            fuse = settle * (1 + self.pct(self.rank('darkness', '死咒'), 0.03))
            self.put(t, 'DeathCurse', fuse, self.scaled(3.0))
            if cut and self.has('darkness', '冥印'):
                self.put(t, 'Nether', 1, self.scaled(8.0))
        elif element == ASTRAL:
            if t.has('Star'):
                self.detonate_stars(1.0)
        takeover = ('終焉後 5 秒內接管元素附傷' if element in (FROST, LIGHTNING, DIVINE, POISON, WATER, ASTRAL) else None)
        if cut and not chain and takeover:
            boost = self.pct(self.rank(TREE[element], takeover), 0.01)
            if boost > 0:
                self.put(me, 'EndBoost', boost, self.scaled(5.0))
        if cut and not chain and self.has('common', '疊印') and not t.has('Residual'):
            self.put(t, 'Residual', element, self.scaled(4.0))
        self.event('End', element, reason, mult, 1 if chain else 0, *value)

    def end(self, element, reason, mult, power=False):
        self.target.marks.pop(element, None)
        if not self.target.has('EndCooldown'):
            self.end_body(element, reason, mult, power)

    # ---------------------------------------------------------------- one hit (2.2, 2.3)
    def hit(self, element, power, hit_work=True):
        t, me = self.target, self.me
        refresh = element in t.marks
        linger = False
        open_mult = 1 + self.pct(self.rank(TREE[element], '開印效果'), 0.03)
        cut_from = 0
        if not refresh:
            others = len(t.marks)
            dual = self.has('common', '雙印')
            if others > 0 and not (dual and others < 2):
                old = max((e for e in t.marks if e != element), key=lambda e: t.marks[e].elapsed)
                self.end(old, CUT, 1.0, power)
                cut_from = old
                linger = old == FROST and self.has('frost', '寒留')
                if old == FIRE and self.has('fire', '餘燼'):
                    open_mult *= 1.5
                if old == WATER and t.has('Soak') and t.mag('Soak') > 1.5:
                    self.put(t, 'Soak', 1, self.soak_seconds())
        t.marks[element] = Slot(0, 0, self.mark_seconds(element, linger))
        if not refresh and not t.has('OpenCooldown'):
            self.put(t, 'OpenCooldown', 1, self.cooldown(1.0))
            self.open_state(element, open_mult, cut_from)
            self.event('Open', element, open_mult, cut_from, 1 if hit_work else 0)
        if not hit_work:
            return
        if refresh:
            if element == FIRE:
                self.raise_heat(2 if power and self.has('fire', '烙印') else 1)
            elif element == FROST:
                if t.has('Frozen'):
                    if power:
                        self.shatter(1)
                    elif t.layers('Crystal') < 3:
                        self.put(t, 'Crystal', t.layers('Crystal') + 1, t.kinds['Frozen'].remaining() + 1.0)
                else:
                    amount = (3.0 if self.has('frost', '寒蝕') else 2.0) if power else 1.0
                    amount *= 1 + 0.05 * self.rank('frost', '每次命中凍結累積')
                    self.add_freeze(amount, power and self.has('frost', '寒蝕'))
            elif element == BLOOD:
                self.add_bleed(1)
            elif element == POISON:
                self.add_doses(2 if power else 1)
            elif element == WATER:
                if t.has('Soak'):
                    locked = t.mag('Soak') > 1.5
                    self.put(t, 'Soak', 2 if locked else 1, 3600.0 if locked else self.soak_seconds())
            elif element == DARKNESS:
                self.add_curse(1 + (2 if t.frenzied and self.has('darkness', '迷亂') else 0))
            elif element == ASTRAL:
                self.add_stars(1)
        if element == FROST and self.ice_armor and not t.has('Frozen'):
            radius = 350.0 if self.has('frost', '霜膚') else 210.0
            if self.body['distance'] <= radius:
                self.add_freeze(1.0)
        if element == WATER and self.has('water', '水壓') and (t.has('Soak') or self.wet):
            self.set_pressure(t.layers('Pressure') + 1)
        if element == DIVINE:
            if refresh:
                self.raise_holy(1)
            holy = self.holy_tier()
            heal = [0.0, 0.0, 0.25, 0.5][holy]
            if heal > 0:
                self.op('heal', self.bmax(DIVINE) * heal * self.recovery)
            needed = 2 if self.has('divine', '神罰') else 3
            count = t.layers('Judge') + 1
            if count >= needed:
                self.drop(t, 'Judge')
                b = self.body
                if holy >= 3:
                    damage = b['health_max'] * (0.02 if b['vip'] else 0.04) * self.base
                else:
                    damage = self.bmax(DIVINE) * 1.0 * self.react_scale(DIVINE)
                damage *= 1 + [0.0, 0.10, 0.20, 0.35][holy] + self.pct(self.rank('divine', '聖佑各階武器傷害與聖傷加成'), 0.01) * holy
                damage *= 1 + self.pct(self.rank('divine', '聖裁傷害'), 0.02)
                if b['undead'] or (self.has('divine', '聖痕') and DIVINE in t.marks):
                    damage *= 3
                damage *= self.vulnerability()
                punish = me.layers('Punish')
                if punish > 0:
                    damage *= 1 + 0.2 * punish
                    self.drop(me, 'Punish')
                self.op('damage', DIVINE, damage)
                if holy >= 2:
                    self.event('Judgment', holy)
            else:
                self.put(t, 'Judge', count, self.scaled(4.0))
        if element == BLOOD:
            zone = self.blood_zone()
            marked = me.layers('BloodZone')
            if marked != zone:
                self.put(me, 'BloodZone', zone, 86400.0)
                if marked and zone > marked and not me.has('CrossCooldown'):
                    self.put(me, 'CrossCooldown', 1, self.cooldown(10.0))
                    self.event('Splash', t.bleed.magnitude * t.bleed.remaining() if t.bleed else 0.0)
                elif marked and zone < marked and not me.has('CrossCooldown'):
                    self.put(me, 'CrossCooldown', 1, self.cooldown(10.0))
                    self.event('Rise')

    # ---------------------------------------------------------------- when things run out
    def mark_expired(self, element, flags):
        t = self.target
        if (element == DARKNESS and self.has('darkness', '咒延') and not flags & MARK_EXTENDED and
                t.layers('Curse') >= 3):
            t.marks[element] = Slot(flags | MARK_EXTENDED, 0, self.scaled(4.0))   # 咒延：續 4 秒（每目標一次）
            return False
        t.marks.pop(element, None)
        if not t.has('EndCooldown'):
            self.end_body(element, EXPIRE, 1.0)
        return True

    def frozen_end(self, carried=0):
        t = self.target
        self.drop(t, 'Frozen')
        crystals = max(t.layers('Crystal'), carried)   # the removal sink's same-frame read (review fix 2)
        if crystals > 0 and self.has('frost', '凍傷'):
            self.op('damage', FROST, crystals * self.bmax(FROST) * 0.5 * self.g(FROST) * self.base * self.vulnerability())
        self.drop(t, 'Crystal')
        if self.has('frost', '永凍'):
            self.put(t, 'Freeze', 2, self.scaled(6.0))
        else:
            self.drop(t, 'Freeze')

    def star_fuse_end(self):
        self.drop(self.target, 'StarFuse')
        self.detonate_stars(1.0)

    def death_curse_end(self, fuse):
        t, b = self.target, self.body
        self.drop(t, 'DeathCurse')
        fuse *= self.vulnerability()
        ratio = 0.15 + self.pct(self.rank('darkness', '死咒的「已損失生命」係數'), 0.005)
        if self.has('darkness', '噬咒'):
            ratio += 0.03 * t.layers('Curse')
            self.drop(t, 'Curse')
        lost = max(0.0, b['health_max'] - b['health'])
        self.op('damage', DARKNESS, (self.bmax(DARKNESS) * 2.0 * self.react_scale(DARKNESS) + lost * ratio) * fuse)
        if self.has('darkness', '饕餮'):
            self.op('heal', self.bmax(DARKNESS) * self.recovery)
            self.op('magicka', self.bmax(DARKNESS) * self.recovery)

    def hallucination_end(self):
        if self.has('darkness', '回魘'):
            self.add_curse(2)

    def fuse_end(self, tier):
        me = self.me
        self.drop(me, f'Heat{tier}')
        if tier == 3 and self.has('fire', '熔爐'):
            self.set_heat(4)
            return
        self.drop(me, 'FireBath')
        if self.has('fire', '熔身'):
            self.set_heat(0)
            self.put(me, 'MoltenBody', 1, self.scaled(10.0))
            return
        self.op('pay', self.hp_max * 0.10)
        self.set_heat(1 if self.has('fire', '熔心') else 0)

    def form_leave(self, element, burst):
        me = self.me
        if element == FIRE and not (burst and self.has('fire', '熔斷')):
            tier = self.heat_tier()
            if tier >= 3:
                self.put(me, 'VentedHeat', tier, self.scaled(30.0))
                self.drop(me, 'MoltenBody')
                self.drop(me, 'FireBath')
                if self.has('fire', '餘壓'):
                    self.set_heat(2)
                    self.put(me, 'SourceLinger', 1, self.scaled(2.0))
                else:
                    self.set_heat(1 if self.has('fire', '熔心') else 0)
            else:
                self.set_heat(0)
        if element == DIVINE:
            if not (burst and self.holy_tier() == 3 and self.has('divine', '神聖領域')):
                self.set_holy(0)
            self.drop(me, 'Punish')

    def decay(self):
        me = self.me
        heat = self.heat_tier()
        if heat in (1, 2) and not me.has('HeatDecay') and not self.has('fire', '火種'):
            self.set_heat(heat - 1)
        holy = self.holy_tier()
        if holy > 0 and not me.has('HolyDecay'):
            self.set_holy(holy - 1)

    def age(self, seconds):
        for board in (self.target, self.me):
            for name in list(board.kinds):
                s = board.kinds[name]
                s.elapsed += seconds
                if s.elapsed >= s.duration:
                    del board.kinds[name]
            for e in list(board.marks):
                s = board.marks[e]
                s.elapsed += seconds
                if s.elapsed >= s.duration:
                    del board.marks[e]
            for attr in ('bleed', 'poison'):
                s = getattr(board, attr)
                if s:
                    s.elapsed += seconds
                    if s.elapsed >= s.duration:
                        setattr(board, attr, None)

    # ---------------------------------------------------------------- the table row
    def summary(self):
        def board(b):
            out = {k: [round(s.magnitude, 5), round(s.remaining(), 5)] for k, s in b.kinds.items()}
            out.update({f'Mark{e}': [round(s.magnitude, 5), round(s.remaining(), 5)] for e, s in b.marks.items()})
            if b.bleed:
                out['BleedDot'] = [round(b.bleed.magnitude, 5), round(b.bleed.remaining(), 5)]
            if b.poison:
                out['PoisonDot'] = [round(b.poison.magnitude, 5), round(b.poison.remaining(), 5)]
            return out
        ops = []
        for row in self.ops:
            if row[0] == 'event':
                ops.append(['event', row[1]] + [round(x, 5) for x in row[2:2 + EVENT_ARGS[row[1]]]])
            else:
                ops.append([row[0]] + [round(x, 5) if isinstance(x, float) else x for x in row[1:]])
        return dict(target=board(self.target), me=board(self.me), ops=sorted(ops, key=lambda r: json_key(r)))


def json_key(row):
    return [str(x) if isinstance(x, str) else f'{x:020.6f}' for x in row]


def proc_terms(w, element, power):
    """2.7 T and the node-like additions the statuses give this element's proc (read before the hit changes them)."""
    t, me = w.target, w.me
    add, mult = 0.0, 1.0
    open_ = me.kinds.get('OpenBoost')
    if open_ and open_.layers() == element and open_.remaining() > 0 and element != WIND:
        add += w.pct(w.rank(TREE[element], f'開印後 5 秒內{SHORT[element]}附傷'), 0.01)
    if me.has('EndBoost'):
        add += me.mag('EndBoost')
    if me.has('Bloodthirst'):
        mult *= 1.2
    if element == FIRE:
        mult *= 1 + [0.0, 0.15, 0.35, 0.60, 0.90][w.heat_tier()]
        if me.has('MoltenBody'):
            add += 1.0
        if t.has('DomainFire'):
            mult *= 1.2
    elif element == FROST:
        if t.has('Frozen'):
            add += w.pct(w.rank('frost', '冰封目標受冰附傷'), 0.02)
    elif element == DIVINE:
        holy = w.holy_tier()
        add += [0.0, 0.10, 0.20, 0.35][holy] + w.pct(w.rank('divine', '聖佑各階武器傷害與聖傷加成'), 0.01) * holy
        if DIVINE in t.marks:
            mult *= 1 + 0.2 + (0.1 if w.has('divine', '聖痕') and not w.body['undead'] else 0.0)
    elif element == WATER:
        if w.has('water', '水壓') and t.has('Pressure'):
            per = 0.10 + w.pct(w.rank('water', '水壓每層水附傷'), 0.01)
            mult *= 1 + t.layers('Pressure') * per * w.omni()
    elif element == ASTRAL:
        if power and w.has('astral', '星痕弱點'):
            mult *= 1 + 0.08 * t.layers('Star') * w.omni()
    if w.has('wind', '御風') and t.has('Unbalance'):   # v0.4 5.7: no sync gate on the +30%
        mult *= 1.3
    if w.has('wind', '空中追擊') and t.has('Airborne'):
        mult *= 1.5
    if t.has('StarLock'):
        mult *= 1.1
    if t.has('DomainAstral'):
        mult *= 1.2
    return add, mult


def run_steps(w, steps):
    for step in steps:
        op = step[0]
        if op == 'hit':
            w.hit(step[1], step[2])
        elif op == 'force':
            w.hit(step[1], False, hit_work=False)
        elif op == 'end':
            w.end(step[1], step[2], step[3])
        elif op == 'expireMark':
            w.mark_expired(step[1], step[2])
        elif op == 'frozenEnd':
            w.frozen_end(step[1] if len(step) > 1 else 0)
        elif op == 'spread':
            w.spread_doses(step[1])
        elif op == 'miasma':
            w.op('miasmaDoses', w.miasma_doses())
        elif op == 'plague':
            w.op('plagueChance', w.plague_chance())
        elif op == 'starFuseEnd':
            w.star_fuse_end()
        elif op == 'deathCurseEnd':
            w.death_curse_end(step[1])
        elif op == 'hallucinationEnd':
            w.hallucination_end()
        elif op == 'fuseEnd':
            w.fuse_end(step[1])
        elif op == 'leave':
            w.form_leave(step[1], step[2])
        elif op == 'decay':
            w.decay()
        elif op == 'age':
            w.age(step[1])
        elif op == 'terms':
            add, mult = proc_terms(w, step[1], step[2])
            w.op('terms', step[1], add, mult)
        else:
            raise ValueError(step)


# ---------------------------------------------------------------- scenarios
# Each: (name, world options, pre-hit statuses [(who, kind, magnitude, elapsed, duration)], marks [(element, flags,
# elapsed, duration)], steps). Nodes are named by (tree, v0.4 name); ranks as {name: points}, branches as a set.

def _n(tree, *names):
    return {(tree, n) for n in names}


def scenario_specs():
    S = []
    add = S.append
    T, M = 'target', 'me'
    # ---- 2.2 marks: open, refresh, cut, 雙印, cooldowns, durations
    add(('fire open, fresh target', {}, [], [], [('hit', FIRE, False)]))
    add(('water open: soak 10 s, 15% slow, 10 s mark', {}, [], [], [('hit', WATER, False)]))
    add(('mark durations: 印記持續 + 火印記持續, ×1.5 duration', dict(ranks={('common', '印記持續'): 10, ('fire', '火印記持續'): 5},
         mult_duration=1.5), [], [], [('hit', FIRE, False)]))
    add(('refresh inside the open cooldown does not re-open', {}, [(T, 'OpenCooldown', 1, 0.2, 1.0)], [(FIRE, 0, 1.0, 8.0)],
         [('hit', FIRE, False)]))
    add(('cut: frost cuts fire (fire end, frost open +3)', {}, [], [(FIRE, 0, 2.0, 8.0)], [('hit', FROST, False)]))
    add(('雙印: second element stays, third cuts the older', dict(branches=_n('common', '雙印')), [],
         [(FIRE, 0, 3.0, 8.0)], [('hit', FROST, False), ('age', 0.5), ('hit', WIND, False)]))
    add(('end cooldown: the second end on the target does nothing', {}, [(T, 'EndCooldown', 1, 0.5, 1.0)],
         [(FIRE, 0, 2.0, 8.0)], [('hit', WIND, False)]))
    add(('open effect +9%/pt and 餘燼 ×1.5 on the open after a fire end', dict(ranks={('frost', '開印效果'): 4},
         branches=_n('fire', '餘燼')), [], [(FIRE, 0, 1.0, 8.0)], [('hit', FROST, False)]))
    add(('寒留: frost end, the takeover mark +4 s', dict(branches=_n('frost', '寒留')), [], [(FROST, 0, 1.0, 8.0)],
         [('hit', EARTH, False)]))
    add(('疊印 + takeover line on a cut', dict(branches=_n('common', '疊印'), ranks={('frost', '終焉後 5 秒內接管元素附傷'): 6}),
         [], [(FROST, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('force open (臨): mark and open, no hit work', {}, [], [], [('force', DARKNESS)]))
    # ---- fire ladder (5.3)
    add(('fire refresh: 微熱 matured -> 灼熱', {}, [(M, 'Heat1', 1, 2.5, 3600), (M, 'HeatDecay', 1, 1.0, 6.0)],
         [(FIRE, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('fire refresh: 微熱 not matured, decay reset', {}, [(M, 'Heat1', 1, 1.0, 3600), (M, 'HeatDecay', 1, 4.0, 6.0)],
         [(FIRE, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('烙印 power hit: two tiers -> 白熱 (添薪 12 s)', dict(branches=_n('fire', '烙印', '添薪')),
         [(M, 'Heat1', 1, 3.0, 3600), (M, 'HeatDecay', 1, 1.0, 6.0)], [(FIRE, 0, 1.0, 8.0)], [('hit', FIRE, True)]))
    add(('引火 open: two tiers', dict(branches=_n('fire', '引火')), [], [], [('hit', FIRE, False)]))
    add(('烈火之始: target above 80% -> 白熱', dict(branches=_n('fire', '烈火之始'), body=dict(health=90)), [], [],
         [('hit', FIRE, False)]))
    add(('烈火點燃: 白熱 open +2 s, capped at +4', dict(branches=_n('fire', '烈火點燃')), [(M, 'Heat3', 3.0, 2.0, 11.0)],
         [(FROST, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('開印後 5 秒內熱度升階免等待', dict(ranks={('fire', '開印後 5 秒內熱度升階免等待'): 10}),
         [(M, 'Heat1', 1, 0.5, 3600), (M, 'HeatDecay', 1, 0.5, 6.0), (M, 'OpenBoost', FIRE, 1.0, 6.0)],
         [(FIRE, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('火域: no wait for the next tier', {}, [(M, 'Heat2', 1, 0.2, 3600), (M, 'HeatDecay', 1, 0.2, 6.0),
         (M, 'FireDomainPlayer', 1, 0.0, 2.0)], [(FIRE, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    add(('overheat: fuse end pays 10%, 熔心 keeps 微熱', dict(branches=_n('fire', '熔心'), hp_max=300), [], [],
         [('fuseEnd', 3)]))
    add(('熔身: fuse end -> 10 s 熔身, heat 0', dict(branches=_n('fire', '熔身')), [(M, 'Heat3', 0, 8.0, 8.0)], [],
         [('fuseEnd', 3)]))
    add(('熔爐: 白熱 fuse end -> 熔燒 6 s', dict(branches=_n('fire', '熔爐')), [(M, 'Heat3', 0, 8.0, 8.0)], [],
         [('fuseEnd', 3)]))
    add(('form leave at 白熱: vent (爆燃照熱度), 餘壓 keeps 灼熱 + source 2 s', dict(branches=_n('fire', '餘壓')),
         [(M, 'Heat3', 0, 3.0, 8.0)], [], [('leave', FIRE, False)]))
    add(('熔斷: burst keeps the heat', dict(branches=_n('fire', '熔斷')), [(M, 'Heat2', 1, 3.0, 3600),
         (M, 'HeatDecay', 1, 1.0, 6.0)], [], [('leave', FIRE, True)]))
    add(('decay: 灼熱 without its timer -> 微熱; 火種 keeps it', {}, [(M, 'Heat2', 1, 9.0, 3600)], [], [('decay',)]))
    add(('火種: no decay', dict(branches=_n('fire', '火種')), [(M, 'Heat2', 1, 9.0, 3600)], [], [('decay',)]))
    add(('fire end: consumption bonus, DoT conversion, stars, 熾焰 at 白熱', dict(branches=_n('fire', '熾焰'),
         ranks={('fire', '爆燃的消耗加成'): 5, ('fire', '終焉'): 3, ('common', '終焉'): 2}),
         [(T, 'Freeze', 3, 1.0, 6.0), (T, 'Curse', 2, 1.0, 8.0), (T, 'Soak', 1, 1.0, 10.0), (T, 'Star', 2, 1.0, 30.0),
          (T, 'StarFuse', 1, 1.0, 2.0), (M, 'Heat3', 0, 1.0, 8.0)],
         [(FIRE, 0, 1.0, 8.0)], [('hit', WIND, False)]))
    # ---- frost (5.4)
    add(('frost hits: +1, power +2, 寒蝕 +3 and 8 s', dict(branches=_n('frost', '寒蝕')), [], [(FROST, 0, 1.0, 8.0)],
         [('hit', FROST, False), ('hit', FROST, True)]))
    add(('暴風雪 ×2 and 每次命中凍結累積', dict(stormy=True, ranks={('frost', '每次命中凍結累積'): 10}),
         [], [(FROST, 0, 1.0, 8.0)], [('hit', FROST, False)]))
    add(('gauge 5 freezes (永凍 +2 s); normal hit stores a crystal', dict(branches=_n('frost', '永凍')),
         [(T, 'Freeze', 4, 1.0, 6.0)], [(FROST, 0, 1.0, 8.0)], [('hit', FROST, False), ('hit', FROST, False)]))
    add(('shatter: power hit on frozen, 2 crystals, 碎冰 +3%/pt, 冰棺', dict(branches=_n('frost', '冰棺'),
         ranks={('frost', '碎冰'): 5}, body=dict(health_max=400)),
         [(T, 'Frozen', 1.0, 1.0, 3.0), (T, 'Freeze', 5, 1.0, 3.0), (T, 'Crystal', 2, 1.0, 3.0)], [(FROST, 0, 1.0, 8.0)],
         [('hit', FROST, True)]))
    add(('銳碎 on a boss', dict(branches=_n('frost', '銳碎'), body=dict(health_max=1000, vip=True)),
         [(T, 'Frozen', 1.0, 1.0, 3.0), (T, 'Freeze', 5, 1.0, 3.0)], [(FROST, 0, 1.0, 8.0)], [('hit', FROST, True)]))
    add(('frost end while frozen: shatter × end node multipliers', dict(ranks={('frost', '終焉'): 5, ('common', '終焉再'): 4},
         body=dict(health_max=200)), [(T, 'Frozen', 1.0, 1.0, 3.0), (T, 'Freeze', 5, 1.0, 3.0)],
         [(FROST, 0, 1.0, 8.0)], [('hit', BLOOD, False)]))
    add(('frozen ends: 凍傷 crystals, 永凍 keeps half', dict(branches=_n('frost', '凍傷', '永凍')),
         [(T, 'Frozen', 1.0, 3.0, 3.0), (T, 'Freeze', 5, 3.0, 3.0), (T, 'Crystal', 3, 3.0, 3.0)], [], [('frozenEnd',)]))
    add(('凍傷 with the crystals already gone: the removal sink carried 3 (review fix 2)', dict(branches=_n('frost', '凍傷')),
         [(T, 'Frozen', 1.0, 3.0, 3.0), (T, 'Freeze', 5, 3.0, 3.0)], [], [('frozenEnd', 3)]))
    add(('freezing keeps the stored crystals 1 s past the frozen end', dict(branches=_n('frost', '深霜結')),
         [(T, 'Freeze', 4, 1.0, 6.0), (T, 'Crystal', 2, 1.0, 6.0)], [(FROST, 0, 1.0, 8.0)], [('hit', FROST, False)]))
    add(('深霜結 + 絕霜 open at sync 3', dict(branches=_n('frost', '深霜結', '絕霜'), sync=3), [], [], [('hit', FROST, False)]))
    add(('霜鎖: already at the slow cap -> freeze +1', dict(branches=_n('frost', '霜鎖'), target_flags=dict(max_slow=70)), [], [],
         [('hit', FROST, False)]))
    add(('冰甲 in range: hit freeze +1 (霜膚 5 m)', dict(branches=_n('frost', '冰甲', '霜膚'), ice_armor=True,
         body=dict(distance=300)), [], [(FROST, 0, 1.0, 8.0)], [('hit', FROST, False)]))
    # ---- earth / wind
    add(('earth open: fissure; 深裂痕 low stamina -> downed; 裂地 5 s', dict(branches=_n('earth', '深裂痕', '裂地'),
         body=dict(stamina=30)), [], [], [('hit', EARTH, False)]))
    add(('wind open: unbalance; wind end blows it away', {}, [], [], [('hit', WIND, False), ('age', 1.2),
         ('hit', FIRE, False)]))
    # ---- blood (5.8)
    add(('blood open 2 layers + 開印流血 + 深血痕 high zone', dict(ranks={('blood', '開印流血'): 5},
         branches=_n('blood', '深血痕'), level={'blood': 20}), [], [], [('hit', BLOOD, False)]))
    add(('blood refresh +1, cap 8 (深創 12), 流血每層傷害', dict(ranks={('blood', '流血每層傷害'): 5}),
         [(T, 'Bleed', 8, 1.0, 10.0)], [(BLOOD, 0, 1.0, 8.0)], [('hit', BLOOD, False)]))
    add(('blood end: remaining settles, bleed removed', {}, [(T, 'Bleed', 4, 2.0, 10.0)], [(BLOOD, 0, 1.0, 8.0)],
         [('hit', DIVINE, False)]))
    add(('越線 down -> 濺血; up -> rise', dict(hp=50), [(M, 'BloodZone', 1, 1.0, 86400)], [(BLOOD, 0, 1.0, 8.0)],
         [('hit', BLOOD, False)]))
    add(('越線 up -> rise, cooldown', dict(hp=90), [(M, 'BloodZone', 2, 1.0, 86400)], [(BLOOD, 0, 1.0, 8.0)],
         [('hit', BLOOD, False)]))
    add(('血引: the open after a blood end bleeds 2', dict(branches=_n('blood', '血引')), [(T, 'Bleed', 3, 1.0, 10.0)],
         [(BLOOD, 0, 1.0, 8.0)], [('hit', POISON, False)]))
    # ---- divine (5.9)
    add(('divine open: 聖佑 I; hits raise when matured; II heal', {}, [], [], [('hit', DIVINE, False), ('age', 2.5),
         ('hit', DIVINE, False)]))
    add(('聖裁 on the third hit at 聖佑 II with 懲戒 3', dict(ranks={('divine', '聖裁傷害'): 5}),
         [(M, 'Holy2', 0, 1.0, 3600), (M, 'HolyDecay', 1, 1.0, 8.0), (M, 'Punish', 3, 1.0, 8.0), (T, 'Judge', 2, 1.0, 4.0)],
         [(DIVINE, 0, 1.0, 8.0)], [('hit', DIVINE, False)]))
    add(('聖裁 III: max health 4%, 神罰 on the second hit, undead ×3', dict(branches=_n('divine', '神罰'),
         body=dict(health_max=500, undead=True)), [(M, 'Holy3', 0, 3.0, 3600), (M, 'HolyDecay', 1, 1.0, 8.0),
         (T, 'Judge', 1, 1.0, 4.0)], [(DIVINE, 0, 1.0, 8.0)], [('hit', DIVINE, False)]))
    add(('聖啟 + 慈光 open', dict(branches=_n('divine', '聖啟', '慈光'), sync=3), [], [], [('hit', DIVINE, False)]))
    add(('聖佑 decay and form leave clears 懲戒; 神聖領域 keeps III on a burst', dict(branches=_n('divine', '神聖領域')),
         [(M, 'Holy3', 0, 5.0, 3600), (M, 'Punish', 2, 1.0, 8.0)], [], [('leave', DIVINE, True), ('decay',)]))
    # ---- poison (5.10)
    add(('poison open 3 doses 12 s; hit +1, power +2; time +3 capped 15', dict(level={'poison': 10}), [], [],
         [('hit', POISON, False), ('age', 1.0), ('hit', POISON, False), ('hit', POISON, True)]))
    add(('傳染門檻: the open doses reach the 1-dose miasma threshold', dict(branches=_n('poison', '傳染門檻')), [], [],
         [('hit', POISON, False), ('miasma',)]))
    add(('poison end: catalysis ×2 (潰爛 ×3), 延毒 +4 s, 催毒期間中毒傷害', dict(branches=_n('poison', '潰爛', '延毒'),
         ranks={('poison', '催毒期間中毒傷害'): 5}), [], [(POISON, 0, 1.0, 8.0)],
         [('hit', POISON, False), ('hit', ASTRAL, False)]))
    # Review fix 1 / ruling (b)+(d) / fix 5: hand-computed expectations in build/fix22_fixture.py HAND (not from this model).
    # per dose at tree level 1: B_max 9 x 0.2116 x G 1.05 = 1.99962; 4 doses = 7.99848.
    add(('catalyse then re-open: open +3 doses keeps ×2', {}, [(T, 'PoisonDot', 7.99848, 2.0, 12.0)], [],
         [('end', POISON, EXPIRE, 1.0), ('hit', POISON, False)]))
    add(('catalyse then re-open, two power hits: base-dose cap 10 keeps ×2', {}, [(T, 'PoisonDot', 7.99848, 2.0, 12.0)], [],
         [('end', POISON, EXPIRE, 1.0), ('hit', POISON, False), ('hit', POISON, True), ('hit', POISON, True)]))
    add(('spread one dose: d\' = max(d - t, 12)', {}, [(T, 'PoisonDot', 7.99848, 10.0, 12.0)], [], [('spread', 1.0)]))
    add(('spread 0.5 dose into a catalysed poison', {}, [(T, 'PoisonDot', 15.99696, 1.0, 14.0), (T, 'Catalyzed', 2.0, 1.0, 14.0)],
         [], [('spread', 0.5)]))
    add(('miasma: 5 doses give 0.5 a second, 4 give none', {}, [(T, 'PoisonDot', 9.9981, 1.0, 12.0)], [], [('miasma',)]))
    add(('miasma below the threshold', {}, [(T, 'PoisonDot', 7.99848, 1.0, 12.0)], [], [('miasma',)]))
    add(('miasma catalysed + 瘴氣每秒傳遞劑量 10 points', dict(ranks={('poison', '瘴氣每秒傳遞劑量'): 10}),
         [(T, 'PoisonDot', 19.9962, 1.0, 12.0), (T, 'Catalyzed', 2.0, 1.0, 11.0)], [], [('miasma',)]))
    add(('plague: 5%/pt at sync 3', dict(ranks={('poison', '瘟疫'): 4}, sync=3), [(T, 'PoisonDot', 1.99962, 1.0, 12.0)], [],
         [('plague',)]))
    add(('幻影: the dark open puts 幻影 on the target for 3 s', dict(branches=_n('darkness', '幻影')), [], [],
         [('hit', DARKNESS, False)]))
    add(('terms: 御風 without sync stage 3', dict(branches=_n('wind', '御風')), [(T, 'Unbalance', 1, 1, 3)], [],
         [('terms', EARTH, False)]))
    # ---- water (5.11)
    add(('水壓: soaked hits +1, cap washes once (淨潮)', dict(branches=_n('water', '水壓', '淨潮')),
         [(T, 'Soak', 1, 1.0, 10.0), (T, 'Pressure', 4, 1.0, 8.0)], [(WATER, 0, 1.0, 10.0)],
         [('hit', WATER, False), ('hit', WATER, False)]))
    add(('water end cut: guide 1.5 (強引 2.0, 導引 +3%/pt), 汪洋 soak 30 s, 退潮 wash',
         dict(branches=_n('water', '強引', '汪洋', '退潮'), ranks={('water', '導引'): 5}),
         [(T, 'Soak', 1, 1.0, 10.0)], [(WATER, 0, 1.0, 10.0)], [('hit', FIRE, False)]))
    add(('guided: the next end ×guide', {}, [(T, 'Guided', 1.5, 1.0, 30.0)], [(DARKNESS, 0, 1.0, 8.0)],
         [('hit', FIRE, False)]))
    add(('汪洋之始 at sync 3: soak locked until cut', dict(branches=_n('water', '汪洋之始'), sync=3), [], [],
         [('hit', WATER, False), ('age', 12), ('hit', WATER, False)]))
    add(('深濕: raining, pressure full at once', dict(branches=_n('water', '深濕', '水壓'), wet=True), [], [],
         [('hit', WATER, False)]))
    # ---- darkness (5.12)
    add(('curse: open 2, hit 3 -> fear; 5 -> frenzy; cooldowns', {}, [], [],
         [('hit', DARKNESS, False), ('hit', DARKNESS, False), ('hit', DARKNESS, False), ('hit', DARKNESS, False)]))
    add(('懼咒 2 / 狂咒 4 / 幻覺持續', dict(branches=_n('darkness', '懼咒', '狂咒'), ranks={('darkness', '幻覺持續'): 10}),
         [], [], [('hit', DARKNESS, False), ('hit', DARKNESS, False), ('hit', DARKNESS, False)]))
    add(('迷亂: frenzied target +2 more', dict(branches=_n('darkness', '迷亂'), target_flags=dict(frenzied=True)),
         [(T, 'Curse', 1, 1.0, 8.0)],
         [(DARKNESS, 0, 1.0, 8.0)], [('hit', DARKNESS, False)]))
    add(('dark end cut: death curse fuse (死咒 +3%/pt), 冥印', dict(branches=_n('darkness', '冥印'),
         ranks={('darkness', '死咒'): 5}), [], [(DARKNESS, 0, 1.0, 8.0)], [('hit', WATER, False)]))
    add(('death curse ends: B_max ×2 + lost 15%+, 噬咒, 饕餮', dict(branches=_n('darkness', '噬咒', '饕餮'),
         ranks={('darkness', '死咒的「已損失生命」係數'): 5}, body=dict(health=40, health_max=200), night=True),
         [(T, 'Curse', 4, 1.0, 8.0), (T, 'DeathCurse', 1.2, 3.0, 3.0)], [], [('deathCurseEnd', 1.2)]))
    add(('回魘: fear ends, curse +2', dict(branches=_n('darkness', '回魘')), [(T, 'Curse', 2, 1.0, 8.0)], [],
         [('hallucinationEnd',)]))
    add(('咒延: curse >= 3 keeps the mark 4 s once, then it ends', dict(branches=_n('darkness', '咒延')),
         [(T, 'Curse', 3, 1.0, 8.0)], [], [('expireMark', DARKNESS, 0), ('expireMark', DARKNESS, MARK_EXTENDED)]))
    # ---- astral (5.13)
    add(('astral open: star 1 + fuse 2 s; hit +1; 星痕延遲; cap', dict(ranks={('astral', '星痕延遲'): 10}), [], [],
         [('hit', ASTRAL, False), ('hit', ASTRAL, False)]))
    add(('star fuse ends: all layers detonate', dict(branches=_n('common', '萬象')), [(T, 'Star', 3, 1.0, 30.0)], [],
         [('starFuseEnd',)]))
    add(('星鎖 + 星耀 at sync 3', dict(branches=_n('astral', '星鎖', '星耀'), sync=3), [], [], [('hit', ASTRAL, False)]))
    add(('astral end: own stars detonate', {}, [(T, 'Star', 2, 1.0, 30.0), (T, 'StarFuse', 1, 1.0, 2.0)],
         [(ASTRAL, 0, 1.0, 8.0)], [('hit', FIRE, False)]))
    # ---- expiry (2.6)
    add(('mark expires: expiry end ×1, no takeover', dict(ranks={('frost', '終焉後 5 秒內接管元素附傷'): 5}), [], [],
         [('expireMark', FROST, 0)]))
    add(('lightning end cut by a power hit: R 1.5, crit draw', {}, [], [(LIGHTNING, 0, 1.0, 8.0)], [('hit', FIRE, True)]))
    # ---- ProcTerms: the target-side multipliers (replaces the difference patch)
    add(('terms: heat, 熔身, domain', {}, [(M, 'Heat2', 1, 1, 3600), (T, 'DomainFire', 1, 0, 2)], [],
         [('terms', FIRE, False)]))
    add(('terms: open window + end boost + bloodthirst', dict(ranks={('frost', '開印後 5 秒內冰附傷'): 5}),
         [(M, 'OpenBoost', FROST, 1.0, 5.0), (M, 'EndBoost', 0.12, 1.0, 5.0), (M, 'Bloodthirst', 1, 1, 10)], [],
         [('terms', FROST, False)]))
    add(('terms: frozen target', dict(ranks={('frost', '冰封目標受冰附傷'): 6}), [(T, 'Frozen', 1, 1, 3)], [],
         [('terms', FROST, False)]))
    add(('terms: 聖佑 II, holy mark, 聖痕', dict(branches=_n('divine', '聖痕'), ranks={('divine', '聖佑各階武器傷害與聖傷加成'): 5}),
         [(M, 'Holy2', 0, 1, 3600)], [(DIVINE, 0, 1.0, 8.0)], [('terms', DIVINE, False)]))
    add(('terms: pressure 3 with 萬象', dict(branches=_n('water', '水壓') | _n('common', '萬象'),
         ranks={('water', '水壓每層水附傷'): 4}), [(T, 'Pressure', 3, 1, 8)], [], [('terms', WATER, False)]))
    add(('terms: star weakness on a power hit, star lock, 星域', dict(branches=_n('astral', '星痕弱點')),
         [(T, 'Star', 2, 1, 30), (T, 'StarLock', 1, 1, 3), (T, 'DomainAstral', 1, 0, 2)], [], [('terms', ASTRAL, True)]))
    add(('terms: 御風 at sync 3 and 空中追擊', dict(branches=_n('wind', '御風', '空中追擊'), sync=3),
         [(T, 'Unbalance', 1, 1, 3), (T, 'Airborne', 30, 0.5, 2)], [], [('terms', EARTH, False)]))
    return S


def build_world(damage, options):
    opts = dict(options)
    ranks = opts.pop('ranks', {})
    branches = opts.pop('branches', set())
    return World(damage, ranks=ranks, branches=branches, **opts)


def seed(w, statuses, marks, flags):
    for who, kind, magnitude, elapsed, duration in statuses:
        board = w.target if who == 'target' else w.me
        if kind in ('PoisonDot', 'BleedDot'):   # the two DoT slots
            setattr(board, 'poison' if kind == 'PoisonDot' else 'bleed', Slot(magnitude, elapsed, duration))
            continue
        board.kinds[kind] = Slot(magnitude, elapsed, duration)
    for element, mark_flags, elapsed, duration in marks:
        w.target.marks[element] = Slot(mark_flags, elapsed, duration)
    w.target.max_slow = float(flags.get('max_slow', 0.0))   # strongest of our slows already on it
    w.target.frenzied = bool(flags.get('frenzied', False))  # our frenzy is running on it


def evaluate(damage, spec):
    name, options, statuses, marks, steps = spec
    options = dict(options)
    flags = options.pop('target_flags', {})
    w = build_world(damage, options)
    seed(w, statuses, marks, flags)
    run_steps(w, steps)
    return w.summary()
