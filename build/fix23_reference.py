"""Round 23 (slice N4) reference model of your own resources and the hits you take, written from 元素魔戰士規劃-v0.4.md.

The native tests compare native/include/SelfLayer.h and Hurt.h (and the N4 parts of Status.h) against this model on
generated scenarios (build/fix23-self-table.json). It is written from the design text, independently of the C++:
plain Python, v0.4's own wording in the comments; build/fix23_fixture.py additionally pins hand-computed anchors.

  NODE_NAMES      the nodes the N4 layer reads, by v0.4 name; their slots come from the identity table (never from here)
  SUSTAIN_LEGEND  each element's 持續傳奇主線 (化身 treats it as fully invested for 10 s), checked by label
  scenarios       see scenario_specs(); evaluate() runs one

Sources in v0.4: 1.1 (blood power cost), 2.1 (lightning N and crit), 2.3 (your resources), 2.4 (sync), 2.6 (wind's
multi-trigger, the guide's sync jump), 5.1-5.13 (nodes). Decisions the design leaves open are the ledger's
(.codex/impl-fix-round23.html).
"""
from __future__ import annotations

NODE_NAMES = {
    # 5.2 common
    'kCommonSyncThreshold': ('common', '同調門檻'),
    'kCommonFocus': ('common', '專一'),
    'kCommonExtreme': ('common', '極致'),
    'kCommonFeedback': ('common', '回饋'),
    'kCommonAvatar': ('common', '化身'),
    'kCommonPreempt': ('common', '先制'),
    'kCommonOpenSync': ('common', '開印時'),
    'kCommonTrio': ('common', '三重奏'),
    'kCommonConcert': ('common', '協奏'),
    # 5.3 fire
    'kFireScorch': ('fire', '灼身'),
    'kFireBathe': ('fire', '浴火'),
    # 5.4 frost
    'kFrostIceMail': ('frost', '冰鎧'),
    'kFrostColdRetort': ('frost', '寒反'),
    'kFrostIceHeart': ('frost', '冰心'),
    # 5.5 lightning
    'kLightningChargeCap': ('lightning', '電荷上限'),
    'kLightningStorm': ('lightning', '雷暴'),
    'kLightningReverse': ('lightning', '逆電'),
    'kLightningQuick': ('lightning', '疾電'),
    'kLightningGod': ('lightning', '雷神'),
    'kLightningOpenCharge': ('lightning', '開印電荷'),
    'kLightningStrongShock': ('lightning', '強感電'),
    'kLightningThunderclap': ('lightning', '雷鳴'),
    'kLightningThunder': ('lightning', '雷霆'),
    'kLightningStatic': ('lightning', '靜電'),
    'kLightningOverloadEnd': ('lightning', '過載終焉'),
    'kLightningResidual': ('lightning', '蓄餘'),
    'kLightningAfterShock': ('lightning', '餘電'),
    'kLightningAdvent': ('lightning', '雷臨強化'),
    # 5.6 earth
    'kEarthBedrock': ('earth', '磐石'),
    'kEarthThick': ('earth', '厚土'),
    'kEarthRetaliate': ('earth', '反震'),
    'kEarthQuakeKnock': ('earth', '地動'),
    'kEarthMountain': ('earth', '山岳'),
    'kEarthOpenRock': ('earth', '開印岩甲'),
    'kEarthRockSkin': ('earth', '岩膚'),
    'kEarthFirm': ('earth', '固土'),
    'kEarthCharge': ('earth', '蓄能'),
    'kEarthAdvent': ('earth', '地臨強化'),
    # 5.7 wind
    'kWindFrenzy': ('wind', '亂舞'),
    'kWindAfterimage': ('wind', '殘影'),
    'kWindThousand': ('wind', '千刃'),
    'kWindOpenGauge': ('wind', '開印風勢'),
    'kWindGaleMark': ('wind', '疾風痕'),
    'kWindFirst': ('wind', '先風'),
    'kWindMulti': ('wind', '多段觸發'),
    'kWindFollow': ('wind', '順勢'),
    'kWindGale': ('wind', '疾風'),
    # 5.8 blood
    'kBloodBlade': ('blood', '血刃'),
    'kBloodVein': ('blood', '血脈'),
    # 5.9 divine
    'kDivineSanctuary': ('divine', '庇護'),
    'kDivineOath': ('divine', '誓約'),
    'kDivineHeaven': ('divine', '天誅'),
    # 5.10 poison
    'kPoisonSkin': ('poison', '毒皮'),
    # 5.11 water
    'kWaterShield': ('water', '水盾'),
    'kWaterCleanse': ('water', '洗淨'),
    'kWaterTideBody': ('water', '潮身'),
    'kWaterPurify': ('water', '淨化'),
    'kWaterStill': ('water', '止水'),
    # 5.12 darkness
    'kDarkGrudge': ('darkness', '怨縛'),
    # 5.13 astral
    'kAstralAfterglow': ('astral', '餘輝'),
    'kAstralEternal': ('astral', '永夜'),
    'kAstralDome': ('astral', '天穹'),
    'kAstralGate': ('astral', '星門'),
    'kAstralRemnant': ('astral', '星殘'),
    'kAstralFalling': ('astral', '墜星'),
    # 5.1 no form
    'kNoFormCloseIn': ('noform', '逼近'),
    'kNoFormOverloadCap': ('noform', '超載上限'),
    'kNoFormAccumulate': ('noform', '蓄流'),
    'kNoFormShieldCost': ('noform', '法盾效率'),
    'kNoFormTransmute': ('noform', '化勁'),
    'kNoFormShieldShare': ('noform', '法盾分擔'),
    'kNoFormUnyield': ('noform', '不屈'),
    'kNoFormLinger': ('noform', '餘魔'),
    'kNoFormEndless': ('noform', '不竭'),
    'kNoFormBreak': ('noform', '破式'),
    'kNoFormInterrupt': ('noform', '斷咒'),
    'kNoFormCounter': ('noform', '反咒'),
    'kNoFormCloakBreak': ('noform', '破護'),
    'kNoFormSpellReturn': ('noform', '咒返'),
}

# 化身 (5.2 持續傳奇主線): "自動觸發當前元素的持續傳奇效果" -- each element tree's sustain legend main line.
SUSTAIN_LEGEND = {'fire': '業火', 'frost': '絕對零度', 'lightning': '天雷', 'earth': '地動', 'wind': '千刃', 'blood': '血海',
                  'divine': '天啟', 'poison': '瘟疫', 'water': '長河', 'darkness': '深淵', 'astral': '永夜'}


# ================================================================ the scenario model
# World23 extends the round-22 model (build/fix22_reference.World: the N3 rules, written from v0.4 on its own) with v0.4's
# N4 rules: your resources (2.3 你身上的資源), sync (2.4), the ends' self parts, the hits you take. The C++ is never
# consulted. Random draws: mode 'mid' (the round-22 rule: a chance p succeeds when p >= 0.5, a real draw is the
# midpoint), 'yes' (every chance succeeds, a real draw is the low end), 'no' (no chance succeeds, a real draw is the high
# end) -- self_test.cpp scripts its RNG the same way.

import fix22_reference as _n3
from fix22_reference import (FIRE, FROST, LIGHTNING, EARTH, WIND, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL, TREE, CUT,
                             BURST, EXPIRE, Slot, json_key)

EVENT_ARGS = dict(_n3.EVENT_ARGS, End=8, Discharge=4, Blade=2, Knock=1, SyncUp=1, Cleanse=1, Lethal=0)
FOREVER = 86400.0
STAGES = (5, 15, 30)


class World23(_n3.World):
    def __init__(self, damage, *, rng='mid', form=0, magicka_max=100.0, repeat=False, sync_t=(5, 15, 30), **options):
        super().__init__(damage, **options)
        self.rng, self.form, self.magicka_max, self.repeat = rng, form, magicka_max, repeat
        self.sync_t = tuple(sync_t)                                              # ESSB_SyncT1..3（與 Papyrus 永續同一份）

    # ---------------------------------------------------------------- draws
    def chance(self, p):
        return True if self.rng == 'yes' else False if self.rng == 'no' else p >= 0.5

    def real(self, lo, hi):
        return lo if self.rng == 'yes' else hi if self.rng == 'no' else lo + (hi - lo) * 0.5

    def crit_mult(self, charges, power=False):
        """2.1: 5% + 2% a charge (+15% 疾電's 3 s); ×1.5, a power hit ×2.5."""
        chance = 0.05 + 0.02 * charges + (0.15 if self.me.has('QuickShock') else 0.0)
        return (2.5 if power else 1.5) if self.real(0.0, 1.0) < chance else 1.0

    # ---------------------------------------------------------------- 2.4 sync
    def thresholds(self):
        scale = max(0.4, 1 - 0.02 * self.rank('common', '同調門檻'))                     # 同調門檻 -2%／點
        held = self.me.kinds.get('FormHeld')
        if self.has('common', '專一') and held and held.elapsed >= 60.0:                 # 專一：60 秒後再 ×0.5
            scale *= 0.5
        stages = [max(1, s) for s in self.sync_t]
        if scale >= 1:
            return stages
        t1, t2, t3 = (int(s * scale) for s in stages)
        t1 = max(1, t1)
        t2 = max(t1 + 1, t2)
        t3 = max(t2 + 1, t3)
        return [t1, t2, t3]

    def stage_of(self, count):
        t1, t2, t3 = self.thresholds()
        return 3 if count >= t3 else 2 if count >= t2 else 1 if count >= t1 else 0

    def set_sync(self, count, announce=True):
        me = self.me
        before = self.stage_of(me.layers('Sync'))
        if count <= 0:
            self.drop(me, 'Sync')
            return
        self.put(me, 'Sync', count, FOREVER)
        after = self.stage_of(count)
        if after > before and announce:
            self.event('SyncUp', after)
            if self.has('common', '回饋') and 1 <= self.form <= 11:                       # 回饋：B_max ×2 生命與魔力
                amount = self.bmax(self.form) * 2.0 * self.recovery
                self.op('heal', amount)
                self.op('magicka', amount)

    def add_sync(self, n):
        if n > 0:
            self.set_sync(self.me.layers('Sync') + n)

    # ---------------------------------------------------------------- your resources (2.3)
    def count(self, kind, n, seconds):
        if n <= 0:
            self.drop(self.me, kind)
        else:
            self.put(self.me, kind, n, seconds)

    def charge_cap(self):
        return 6 + self.rank('lightning', '電荷上限') // 3 + self.cap_bonus()

    def rock_cap(self):
        return (10 if self.has('earth', '厚土') else 5) + self.cap_bonus()

    def wind_gate(self):
        return 3 if self.has('wind', '亂舞') else 4

    def ice_cap(self):
        return 8 if self.has('frost', '冰鎧') else 5

    def set_charges(self, n):
        self.count('Charge', min(n, self.charge_cap()), self.scaled(10.0))

    def set_rock(self, n):
        n = max(0, min(n, self.rock_cap()))
        self.count('RockArmor', n, FOREVER)
        armor = n * (40.0 if self.has('earth', '磐石') else 25.0)
        if n <= 0:
            self.drop(self.me, 'RockArmorAV')
        elif not self.me.has('RockArmorAV') or self.me.mag('RockArmorAV') != armor:
            self.put(self.me, 'RockArmorAV', armor, FOREVER)

    def set_wind(self, n):
        self.count('WindGauge', min(n, self.wind_gate()), self.scaled(5.0))

    def set_ice(self, n):
        n = max(0, min(n, self.ice_cap()))
        self.count('IceShield', n, self.scaled(8.0))
        if n <= 0:
            self.drop(self.me, 'IceShieldArmorAV')
            self.drop(self.me, 'IceShieldMagicAV')
        else:
            self.put(self.me, 'IceShieldArmorAV', n * 20.0, 8.0)                      # 護甲 +20／層
            self.put(self.me, 'IceShieldMagicAV', n * 4.0, 8.0)                       # 魔抗 +4%／層

    def add_resolve(self, n):
        self.count('Resolve', min(5, self.me.layers('Resolve') + n), self.scaled(10.0))

    def overload_cap(self):
        return self.magicka_max * (0.5 + 0.02 * self.rank('noform', '超載上限'))

    def set_overload(self, pool, infused):
        me = self.me
        if pool <= 0.01:
            self.drop(me, 'Overload')
            self.drop(me, 'OverloadWait')
            return
        self.put(me, 'Overload', pool, FOREVER)
        if infused:
            self.put(me, 'OverloadWait', 1, 6.0 if self.has('noform', '蓄流') else 3.0)

    def resonance_gate(self):
        return 7 if self.has('astral', '天穹') and self.sync >= 3 else 10

    def add_resonance(self, n):
        me = self.me
        if n <= 0 or me.has('Cosmos'):
            return
        total = me.layers('Resonance') + n
        if total >= self.resonance_gate():                                               # 自動升闇星：1：1 轉為闇宙（上限 15）
            self.drop(me, 'Resonance')
            self.put(me, 'Cosmos', min(total, 15), self.scaled(10.0))
            return
        self.put(me, 'Resonance', total, self.scaled(20.0))

    def dark_strike(self, power):
        cap = self.star_cap()
        amount = cap * self.bmax(ASTRAL) * self.react_scale(ASTRAL) * self.omni() * \
            (1 + self.pct(self.rank('astral', '永夜'), 0.03))
        if power and self.has('astral', '星痕弱點'):
            amount *= 1 + 0.08 * cap * self.omni()
        return amount * self.vulnerability()

    def discharge(self, charges, mult, power, crit):
        self.event('Discharge', charges, mult, power, crit)

    def blades(self, n, mult=1.0):
        if n > 0:
            self.event('Blade', n, mult)

    # ---------------------------------------------------------------- the N3 hooks N4 changes
    def add_stars(self, layers):
        if self.me.has('Cosmos'):                                                        # 闇星中不給星痕
            return
        super().add_stars(layers)

    def detonate_stars(self, mult):
        had = self.target.layers('Star')
        super().detonate_stars(mult)
        if had > 0 and not self.me.has('Cosmos'):
            self.op('resonance')                                                         # 引爆：共鳴層（引擎計數）

    def raise_holy(self, steps):
        if self.repeat:
            tier = self.holy_tier()
            self.set_holy(min(3, tier + steps))                                          # 多段觸發：聖佑升 N 階
            return
        super().raise_holy(steps)

    def hit(self, element, power, hit_work=True):
        me = self.me
        before = (me.layers('BloodZone'), me.has('CrossCooldown'))
        super().hit(element, power, hit_work)
        zone = me.layers('BloodZone')
        if element == BLOOD and before[0] and zone < before[0] and not before[1]:
            self.put(me, 'SurgeUp', 1, self.scaled(8.0))                                 # 回湧：往上越線

    def end_extra(self, element, charge):
        me = self.me
        mult, flags = 1.0, 0
        if me.has('Concert'):                                                            # 切換後首次終焉
            flags |= 2
            if self.has('common', '協奏'):
                mult *= 1.5
            self.drop(me, 'Concert')
        if self.has('common', '三重奏') and 1 <= element <= 11:
            kinds = 1 + sum(1 for e in range(1, 12) if e != element and me.has(f'Trio{e}'))
            if kinds >= 3:
                mult *= 3.0
                for e in range(1, 12):
                    self.drop(me, f'Trio{e}')
                self.put(me, 'SyncKeepAll', 1, 60.0)
            else:
                self.put(me, f'Trio{element}', 1, 10.0)
        if self.has('lightning', '過載終焉') and charge >= 8:
            mult *= 2.0
        return mult, flags

    def end_body(self, element, reason, mult, power=False, chain=False):
        """v0.4 2.6 with the N4 parts: the charge the lightning end discharges, 協奏／三重奏／過載終焉, the self parts."""
        me = self.me
        cut = reason == CUT
        charge = me.layers('SwitchCharge') if cut and me.has('SwitchCharge') else me.layers('Charge')
        flags = 1 if chain else 0
        extra = 1.0
        if not chain:
            # the extras multiply after the guide (the round-22 model multiplies the guide inside end_body)
            extra, bits = self.end_extra(element, charge)
            flags |= bits
        before = len(self.ops)
        super().end_body(element, reason, mult * extra, power, chain)
        # rewrite the End event: flags and the charge (the base model writes chain as 0/1 and no charge)
        for i in range(len(self.ops) - 1, before - 1, -1):
            row = self.ops[i]
            if row[0] == 'event' and row[1] == 'End':
                if element == LIGHTNING:
                    row[7] = self.real(0.0, 1.0)   # the body's crit draw, in this RNG mode
                self.ops[i] = row[:5] + [float(flags)] + row[6:9] + [float(charge)]
                break
        self.end_self(element, reason, charge, power, chain)

    def end_self(self, element, reason, charge, power, chain):
        me = self.me
        cut = reason == CUT
        if element == LIGHTNING:
            if not self.has('lightning', '蓄餘'):
                self.drop(me, 'SwitchCharge')
                self.set_charges(0)
            if cut and not chain and charge > 0 and self.has('lightning', '餘電'):
                self.put(me, 'PendingDischarge', charge, 30.0)
            if reason == BURST and not chain and self.has('lightning', '雷霆'):
                self.put(me, 'Thunder', charge, self.scaled(5.0))
            if charge > 0 and self.has('lightning', '疾電'):
                self.put(me, 'QuickShock', 1, self.scaled(3.0))
        elif element == EARTH:
            if self.has('earth', '固土'):
                self.set_rock(self.rock_cap())
        elif element == WIND:
            if cut and not chain and self.has('wind', '順勢'):
                self.put(me, 'WindFollow', 1, self.scaled(5.0))
        elif element == WATER:
            if cut and not chain:
                now = me.layers('Sync')
                nxt = next((at for at in self.thresholds() if now < at), now)
                self.set_sync(nxt)                                                       # 導引：同調跳到下一段門檻
        elif element == ASTRAL:
            if cut and me.has('FallingStar'):
                self.op('damage', ASTRAL, me.layers('FallingStar') * 0.5 * self.dark_strike(power))
                self.drop(me, 'FallingStar')

    # ---------------------------------------------------------------- open gains (2.3 開印 +2 …)
    def open_gains(self, element, power, crit):
        me, t = self.me, self.target
        blades = 0
        if element == LIGHTNING:
            gain = 2 + self.rank('lightning', '開印電荷') // 5
            if crit and self.has('lightning', '雷鳴'):
                gain += 2
            n = me.layers('Charge') + gain
            if power and self.has('lightning', '強感電') and not me.has('StrongShockCooldown'):
                n = self.charge_cap()
                self.put(me, 'StrongShockCooldown', 1, self.cooldown(15.0))
            self.set_charges(n)
        elif element == EARTH:
            self.set_rock(me.layers('RockArmor') + (4 if self.has('earth', '岩膚') else 2) + self.rank('earth', '開印岩甲') // 5)
        elif element == WIND:
            gate = self.wind_gate()
            gauge = gate if self.has('wind', '疾風痕') else me.layers('WindGauge') + 2 + self.rank('wind', '開印風勢') // 5
            if gauge >= gate:
                blades += 1
                gauge = 0
            self.set_wind(gauge)
            if self.sync >= 3 and self.has('wind', '先風'):
                blades += 1
        elif element == DIVINE:
            if self.has('divine', '誓約'):
                self.put(t, 'Oath', 1, self.scaled(8.0))
        elif element == ASTRAL:
            if not me.has('Cosmos') and self.has('astral', '星門'):
                self.add_resonance(1)
        sync = self.rank('common', '開印時') // 5 + (2 if self.has('common', '先制') else 0)
        if element == BLOOD and self.has('blood', '血脈'):
            sync += 2
        self.add_sync(sync)
        if me.has('PendingDischarge'):                                                   # 餘電 ×0.5
            n = me.layers('PendingDischarge')
            self.discharge(n, 0.5, 1.0, self.crit_mult(n))
            self.drop(me, 'PendingDischarge')
        return blades

    # ---------------------------------------------------------------- one element hit (the self part)
    def self_hit(self, element, form, power, sneak, crit, opened, cut_from, casting, blood_cost=0.0, surge_up=False,
                 repeat=False, body_stamina=None):
        me, t = self.me, self.target
        opened = opened and not repeat
        blades = 0
        extra = False
        if not repeat:
            self.add_sync(1)
        if element == LIGHTNING:
            cap = self.charge_cap()
            before = me.layers('Charge')
            full = before >= cap
            n, fired = before, False
            if power and full:
                self.discharge(before, 1.0, 1.5, 2.5)                                    # 滿格重擊放電：必暴 ×2.5
                n, fired = 0, True
            elif not power and full and self.has('lightning', '雷暴') and self.chance(0.3):
                self.discharge(before, 1.0, 1.0, self.crit_mult(before))
                n, fired = 0, True
            if opened:
                if fired:
                    self.set_charges(0)
                self.open_gains(LIGHTNING, power, crit)
                n = me.layers('Charge')
            elif not fired:
                n = min(cap, n + 1)                                                      # a discharging hit leaves 0
            if not fired and n >= cap > before and self.sync >= 3 and self.has('lightning', '雷神'):
                self.discharge(n, 1.0, 1.0, self.crit_mult(n))
                self.op('magicka', self.bmax(LIGHTNING) * n * 0.5 * self.recovery)     # 雷神回魔 ×0.5（可調，指揮官裁定）
                n, fired = 0, True
            if n != me.layers('Charge') or not opened:
                self.set_charges(n)
            if fired and self.has('lightning', '疾電'):
                self.put(me, 'QuickShock', 1, self.scaled(3.0))
            if full and casting and self.chance(0.3):
                self.op('interrupt')                                                     # 滿格：法術麻痺
        elif element == EARTH:
            cap, rock = self.rock_cap(), me.layers('RockArmor')
            bonus = me.mag('ChargedQuake') if me.has('ChargedQuake') else 0.0
            if power and rock >= cap and form == EARTH and not repeat:
                scale = self.react_scale(EARTH) * (1 + bonus)
                self.op('damage', EARTH, rock * self.bmax(EARTH) * 0.3 * scale * self.vulnerability())
                stamina = rock * self.bmax(EARTH) * 0.5 * self.g(EARTH) * 1.0
                self.op('drainStamina', stamina)
                self.event('Knock', 3.0)
                self.op('crush', rock * self.bmax(EARTH) * 0.3 * scale, stamina)
                self.set_rock(0)
                if bonus > 0:
                    self.drop(me, 'ChargedQuake')
                    bonus = 0.0
            elif opened:
                self.open_gains(EARTH, power, crit)
            else:
                self.set_rock(min(cap, rock + 1))
            if power and form == EARTH and not repeat:
                force = me.layers('StoredForce')
                if force >= 1 and self.has('earth', '蓄能'):
                    self.put(me, 'ChargedQuake', bonus + force * 0.05, 3600.0)
                    force = 0
                self.count('StoredForce', min(10, force + 3), FOREVER)
            stam = self.body['stamina'] if body_stamina is None else body_stamina
            points = self.rank('earth', '地動')
            if power and self.sync >= 3 and stam / self.body['stamina_max'] < 0.3 and points > 0 and self.chance(0.05 * points):
                self.event('Knock', 2.0)
        elif element == WIND:
            gate = self.wind_gate()
            if opened:
                blades += self.open_gains(WIND, power, crit)
            if sneak:
                self.set_wind(gate)
            elif not opened:
                self.set_wind(me.layers('WindGauge') + 1)
            if me.layers('WindGauge') >= gate:
                self.set_wind(0)
                self.blades(1, 2.0 if sneak and self.has('wind', '暗風') else 1.0)
            points = self.rank('wind', '千刃')
            if self.sync >= 3 and points > 0 and self.chance(0.05 * points):
                blades += 1
        elif element == FROST:
            self.set_ice(me.layers('IceShield') + 1)
        elif element == BLOOD:
            if surge_up and not repeat:
                self.drop(me, 'SurgeUp')
                self.add_bleed(2)
            elif blood_cost > 0 and not repeat:
                self.op('pay', blood_cost)
        elif element == WATER:
            if opened:
                self.open_gains(WATER, power, crit)
            if not repeat and self.has('water', '洗淨') and not me.has('CleanseCooldown'):
                self.event('Cleanse', 1 if self.has('water', '淨化') else 0)             # 洗淨：每 3 秒一次（淨化：全部）
                self.put(me, 'CleanseCooldown', 1, self.cooldown(3.0))
        elif element == ASTRAL:
            if me.has('Cosmos'):
                self.op('damage', ASTRAL, self.dark_strike(power))
                left = me.layers('Cosmos') - 1
                if left > 0:
                    self.put(me, 'Cosmos', left, self.scaled(10.0))
                else:
                    self.drop(me, 'Cosmos')
                    if self.has('astral', '餘輝'):
                        self.put(me, 'Resonance', 3, self.scaled(20.0))
            elif opened:
                self.open_gains(ASTRAL, power, crit)
        elif opened:
            self.open_gains(element, power, crit)
        if opened and element in (FROST, BLOOD):
            self.open_gains(element, power, crit)
        if repeat:
            self.blades(blades)
            return extra, 0
        if me.has('WindFollow'):
            blades += 1
        self.blades(blades)
        if me.has('Thunder'):
            n = me.layers('Thunder')
            self.discharge(n, 0.3, 1.0, self.crit_mult(n))
        if self.sync >= 3 and self.has('common', '極致'):
            c = me.layers('Extreme') + 1
            if c >= 10:
                extra = True
                self.drop(me, 'Extreme')
            else:
                self.put(me, 'Extreme', c, FOREVER)
        points = self.rank('common', '化身')
        if self.sync >= 3 and points > 0 and not me.has('AvatarCooldown') and not me.has('Avatar'):
            self.put(me, 'Avatar', form, self.scaled(10.0))
            self.put(me, 'AvatarCooldown', 1, self.cooldown(max(1.0, 30.0 - points)))
        if sneak:
            self.put(t, 'LastHitSneak', form, 1.0)
        repeats = 0
        if cut_from == WIND:
            repeats = min(5, 2 + self.rank('wind', '多段觸發') // 5) - 1
        return extra, repeats

    def self_open(self, element):
        self.blades(self.open_gains(element, False, False))

    # ---------------------------------------------------------------- no form (5.1)
    def self_noform(self, silenced, broke, overload_after, casting, sneak):
        me = self.me
        resolve = me.layers('Resolve')
        if broke:
            resolve = 0
        if silenced:
            resolve += 1
        if casting and self.has('noform', '斷咒') and not me.has('InterruptCooldown'):
            self.op('interrupt')
            self.put(me, 'InterruptCooldown', 1, self.cooldown(5.0))
            resolve += 1
        self.count('Resolve', min(5, resolve), self.scaled(10.0))
        if overload_after >= 0:
            before = me.mag('Overload') if me.has('Overload') else 0.0
            self.set_overload(overload_after, overload_after > before)
        if me.has('Thunder'):
            n = me.layers('Thunder')
            self.discharge(n, 0.3, 1.0, self.crit_mult(n))
        if sneak:
            self.put(self.target, 'LastHitSneak', 12, 1.0)

    # ---------------------------------------------------------------- leave / enter / second
    def self_leave(self, element, burst):
        me = self.me
        charges = me.layers('Charge')
        if element == LIGHTNING and not burst and charges > 0:
            self.put(me, 'SwitchCharge', charges, 60.0)
        if not self.has('lightning', '過載終焉'):
            self.set_charges(0)
        self.set_rock(0)
        self.set_wind(0)
        self.set_ice(0)
        for kind in ('StoredForce', 'ChargedQuake', 'Extreme', 'FormHeld', 'SurgeUp'):
            self.drop(me, kind)
        if element == ASTRAL:
            cosmos = me.layers('Cosmos')
            if not burst and cosmos > 0 and self.has('astral', '墜星'):
                self.put(me, 'FallingStar', cosmos, 30.0)
            self.drop(me, 'Cosmos')
            if self.has('astral', '星殘') and me.has('Resonance'):
                self.put(me, 'Resonance', me.mag('Resonance'), self.scaled(15.0))
            else:
                self.drop(me, 'Resonance')
        else:
            self.drop(me, 'Cosmos')
        if not burst:
            self.put(me, 'Concert', 1, 3600.0)
        if me.guard is not None:
            self.op('guardPool', 0.0)
            me.guard = None

    def self_enter(self, element):
        me = self.me
        self.put(me, 'FormHeld', element, FOREVER)
        if element == LIGHTNING and self.has('lightning', '雷臨強化'):
            self.set_charges(me.layers('Charge') + 5)
        if element == EARTH and self.has('earth', '地臨強化'):
            self.set_rock(self.rock_cap())

    def self_second(self):
        me = self.me
        if not me.has('Overload') or me.has('OverloadWait'):
            return
        rate = max(0.02, 0.05 - 0.002 * self.rank('noform', '不竭'))
        self.set_overload(me.mag('Overload') - rate * self.magicka_max, False)

    # ---------------------------------------------------------------- before a blood power hit (1.1, 5.8)
    def blood_terms(self, power, real_power):
        """Returns (cost, mult on the blood proc, flat add, 回湧 used)."""
        if not power:
            return 0.0, 1.0, 0.0, False
        if self.me.has('SurgeUp'):
            return 0.0, 1.5, 0.0, True
        if not real_power:
            return 0.0, 1.0, 0.0, False
        f = max(0.0, min(1.0, self.hp / self.hp_max))
        points = [(1.0, 0.08), (0.7, 0.05), (0.3, 0.02), (0.1, 0.0)]
        if f >= 1.0:
            share = 0.08
        elif f <= 0.1:
            share = 0.0
        else:
            share = next(lo_v + (f - lo_f) / (hi_f - lo_f) * (hi_v - lo_v)
                         for (hi_f, hi_v), (lo_f, lo_v) in zip(points, points[1:]) if f >= lo_f)
        cost = min(self.hp_max * share, max(0.0, self.hp - 1.0))
        flat = cost * 0.5 if cost > 0 and self.has('blood', '血刃') else 0.0
        return cost, 1.0, flat, False

    # ---------------------------------------------------------------- a hit you take (Hurt.h)
    def hurt(self, f):
        me, foe = self.me, self.target
        form = self.form
        lost = max(0.0, f['before'] - f['after'])
        if f.get('afterimage'):
            self.drop(me, 'Afterimage')
        share = cost = 0.0
        kind = None
        if not f.get('spell') or f.get('destructive'):
            if form == 0:
                if f.get('magicka_before', 0) > 0 or f.get('overload_before', 0) > 0:
                    over = f.get('overload_before', 0) > 0
                    share = (0.45 if over else 0.30) + 0.01 * self.rank('noform', '法盾分擔')
                    cost = (0.75 if over else 1.0) * (1 - 0.02 * self.rank('noform', '法盾效率'))
                    kind = 'shield'
                elif f.get('linger'):
                    share, cost, kind = 0.3, 1.0 * (1 - 0.02 * self.rank('noform', '法盾效率')), 'linger'
            elif form == WATER and f.get('magicka_before', 0) > 0:
                shield_veil = self.has('water', '水盾')
                share = 0.3 if shield_veil else 0.2
                if self.sync >= 3 and self.has('water', '止水'):
                    share += 0.15
                cost = 1.0 if shield_veil else 1.5
                kind = 'veil'
            elif form == BLOOD and f.get('guard_before', 0) > 0:
                share, cost, kind = 0.5, 1.0, 'guard'                  # 護血 50%（指揮官裁定）
        blocked = lost * share / (1 - share) if 0 < share < 1 and lost > 0 else 0.0
        magicka = max(0.0, f['magicka'])
        pool = me.mag('Overload') if me.has('Overload') else 0.0
        extra = 0.0                                                              # 分擔池付不出來的部分＝真的傷害（可致死）

        def hurt_you(amount):
            nonlocal extra
            if amount > 0:
                self.op('hurtHealth', amount)
                extra += amount
        if 0 < share < 1 and f.get('dot_damage', 0) > 0:                         # 持續傷不分擔：PERK 切掉的那份還回去
            hurt_you(f['dot_damage'] * share / (1 - share))
        if blocked > 0:
            owed = blocked * cost
            if kind == 'shield':
                take = min(pool, owed)
                if take > 0:
                    pool -= take
                    owed -= take
                    self.set_overload(pool, False)
            if kind in ('shield', 'veil'):
                paid = min(owed, magicka)
                if paid > 0:
                    self.op('spendMagicka', paid)
                if owed > paid and cost > 0:
                    hurt_you((owed - paid) / cost)                               # 魔力不夠：付不出的部分打到生命
                emptied = magicka > 0 and paid >= magicka
                magicka -= paid
                if emptied and kind == 'shield' and pool <= 0 and self.has('noform', '餘魔') and not me.has('LingerCooldown'):
                    self.put(me, 'LingerShield', 1, 2.0)
                    self.put(me, 'LingerCooldown', 1, self.cooldown(30.0))
                if emptied and kind == 'veil' and self.has('water', '潮身') and not me.has('TideBodyCooldown'):
                    self.event('Cleanse', 1 if self.has('water', '淨化') else 0)
                    back = f['magicka_max'] * 0.2 * self.recovery
                    self.op('magicka', back)
                    magicka += back
                    self.put(me, 'TideBodyCooldown', 1, self.cooldown(30.0))
            elif kind == 'linger':
                self.op('payStamina', min(owed, max(0.0, f['stamina'])))
            elif kind == 'guard':
                guard = f['guard_left'] if f.get('guard_left', -1.0) >= 0 else f['guard_before']   # a same-frame second hit
                left = guard - blocked
                self.op('guardPool', max(0.0, left))
                if left < 0:
                    hurt_you(-left)                                              # 池不夠的部分是真的傷害，不留 1 點
        if form == 0 and f.get('spell') and lost + blocked > 0:
            ratio = 0.6 if self.has('noform', '化勁') else 0.3
            if me.has('CloseIn'):
                ratio *= 2
            back = (lost + blocked) * ratio * self.recovery
            fits = min(back, max(0.0, f['magicka_max'] - magicka))
            if fits > 0:
                self.op('magicka', fits)
            cap = f['magicka_max'] * (0.5 + 0.02 * self.rank('noform', '超載上限'))
            if back > fits and pool < cap:
                self.set_overload(min(cap, pool + back - fits), True)
        attacker = f.get('attacker', False)
        melee = f.get('melee', False)
        retort = attacker and not foe.has('RetortCooldown')
        retorted = False
        if form == EARTH and me.has('RockArmor'):
            rock = me.layers('RockArmor')
            if attacker and melee and rock >= self.rock_cap() and self.has('earth', '反震') and not me.has('RetaliateCooldown'):
                self.op('damage', EARTH, self.bmax(EARTH) * 2.0 * self.react_scale(EARTH) * self.vulnerability())
                self.event('Knock', 3.0)
                self.put(me, 'RetaliateCooldown', 1, self.cooldown(10.0))
                self.set_rock(0)
            elif not (self.has('earth', '山岳') and self.sync >= 3):
                self.set_rock(rock - 1)
        if retort and melee and form == FIRE and self.has('fire', '灼身'):
            others = len([e for e in foe.marks if e != FIRE])
            if others == 0 or (others < 2 and self.has('common', '雙印')):
                foe.marks[FIRE] = Slot(0, 0, self.mark_seconds(FIRE))
            self.op('damage', FIRE, self.bmax(FIRE) * 1.0 * self.react_scale(FIRE) * self.vulnerability())
            retorted = True
        if retort and form == FROST and self.has('frost', '寒反'):
            self.op('slow', 30.0, self.scaled(3.0))
            self.add_freeze(1.0)
            retorted = True
        if retort and melee and form == LIGHTNING and self.has('lightning', '靜電'):
            others = len([e for e in foe.marks if e != LIGHTNING])
            if others == 0 or (others < 2 and self.has('common', '雙印')):
                foe.marks[LIGHTNING] = Slot(0, 0, self.mark_seconds(LIGHTNING))
            retorted = True
        if retort and melee and form == POISON and self.has('poison', '毒皮'):
            self.add_doses(2.0)
            retorted = True
        if retorted:
            self.put(foe, 'RetortCooldown', 1, self.cooldown(3.0))
        if attacker and form == DARKNESS and self.has('darkness', '怨縛') and foe.has('Curse') and not foe.has('GrudgeCooldown'):
            self.add_curse(1)
            self.put(foe, 'GrudgeCooldown', 1, self.cooldown(2.0))
        if attacker and f.get('spell') and form == 0 and self.has('noform', '咒返') and not me.has('SpellReturnCooldown'):
            self.op('dispelMark')
            self.put(me, 'SpellReturnCooldown', 1, self.cooldown(5.0))
        if f.get('blocked') and form == 0 and self.has('noform', '反擊'):
            self.op('riposte')
        if f.get('cloak') and form == 0 and self.has('noform', '破護'):
            self.put(me, 'CloakGuard', 1, 2.0)
        if form == 0 and self.has('noform', '不屈') and not me.has('UnyieldCooldown'):
            self.add_resolve(1)
            self.put(me, 'UnyieldCooldown', 1, self.cooldown(3.0))
        if form == LIGHTNING and self.has('lightning', '逆電') and not me.has('ReverseCooldown'):
            self.set_charges(me.layers('Charge') + 1)
            self.put(me, 'ReverseCooldown', 1, self.cooldown(2.0))
        if attacker and form == FIRE and self.sync >= 3 and self.has('fire', '浴火') and FIRE in foe.marks:
            self.raise_heat(1)
        if self.holy_tier() >= 2 and not me.has('PunishCooldown'):
            gain = 2 if attacker and foe.has('Oath') else 1
            cap = 8 if self.has('divine', '天誅') else 5
            self.put(me, 'Punish', min(cap, me.layers('Punish') + gain), self.scaled(8.0))
            self.put(me, 'PunishCooldown', 1, 0.5)
        if f.get('blocked') and form == EARTH:
            force = me.layers('StoredForce')
            if force >= 1 and self.has('earth', '蓄能'):                        # 蓄能：v0.4「消耗全部」，≥1 就換
                self.put(me, 'Bracing', force, 3.0)
                force = 0
            self.count('StoredForce', min(10, force + 2), FOREVER)
        if melee and not f.get('afterimage') and form == WIND and self.has('wind', '殘影') and \
                me.layers('WindGauge') >= self.wind_gate() and self.chance(0.3):
            self.set_wind(0)
            self.put(me, 'Afterimage', 1, 2.0)
        fraction = max(0.0, f['after'] - extra) / self.hp_max
        if self.heat_tier() >= 3 and fraction < 0.1:
            self.form_leave(FIRE, False)                                                 # 自動洩壓
        if form == BLOOD:
            zone = 1 if fraction > 0.7 else 2 if fraction >= 0.3 else 3
            marked = me.layers('BloodZone')
            if marked != zone:
                self.put(me, 'BloodZone', zone, 86400.0)
                if marked and not me.has('CrossCooldown'):
                    self.put(me, 'CrossCooldown', 1, self.cooldown(10.0))
                    if zone > marked:
                        self.event('Splash', 0.0)
                    else:
                        self.event('Rise')
                        self.put(me, 'SurgeUp', 1, self.scaled(8.0))
        if form == FROST and fraction < 0.3 and self.has('frost', '冰心') and not me.has('IceHeartCooldown'):
            self.op('freezeNearby')
            self.put(me, 'IceHeartCooldown', 1, self.cooldown(30.0))
        if form == DIVINE and fraction < 0.3 and self.has('divine', '庇護') and not me.has('SanctuaryCooldown'):
            self.set_holy(3)
            self.put(me, 'SanctuaryCooldown', 1, self.cooldown(30.0))
        if f['after'] - extra <= 0:
            self.event('Lethal')

    def spell_cast(self, near, marked, cost, true_mult):
        me = self.me
        if self.form != 0:
            return
        if near and self.has('noform', '逼近') and not me.has('CloseInCooldown'):
            self.put(me, 'CloseIn', 1, self.scaled(2.0))
            self.put(me, 'CloseInSpeed', 30.0, 2.0)
            self.put(me, 'CloseInCooldown', 1, self.cooldown(6.0))
        if marked and cost > 0 and self.has('noform', '反咒'):
            ratio = 1 + 0.02 * max(1, self.level.get('noform', 1))
            damage = cost * ratio * true_mult * self.base
            self.op('damage', 0, damage)
            if self.has('noform', '噬命'):
                self.op('heal', damage * 0.5 * self.recovery)
            self.add_resolve(1)

    def summary(self):
        def board(b):
            out = {k: [round(s.magnitude, 5), round(s.remaining(), 5)] for k, s in b.kinds.items()}
            out.update({f'Mark{e}': [round(s.magnitude, 5), round(s.remaining(), 5)] for e, s in b.marks.items()})
            if b.bleed:
                out['BleedDot'] = [round(b.bleed.magnitude, 5), round(b.bleed.remaining(), 5)]
            if b.poison:
                out['PoisonDot'] = [round(b.poison.magnitude, 5), round(b.poison.remaining(), 5)]
            if getattr(b, 'guard', None) is not None:
                out['GuardPool'] = [round(b.guard, 5), 0.0]
            return out
        ops = []
        for row in self.ops:
            if row[0] == 'event':
                ops.append(['event', row[1]] + [round(x, 5) for x in row[2:2 + EVENT_ARGS[row[1]]]])
            else:
                ops.append([row[0]] + [round(x, 5) if isinstance(x, float) else x for x in row[1:]])
        return dict(target=board(self.target), me=board(self.me), ops=sorted(ops, key=lambda r: json_key(r)))


# ================================================================ steps and scenarios
# Steps (self_test.cpp runs the same list through the C++):
#   ['hit', element, power, {sneak, crit, casting, real, repeat}]  one accepted element hit: (a blood power hit's cost
#        terms first: row 'blood' cost mult flat) the N3 status hit, then the self part; row 'result' extra repeats;
#        repeat: run the 多段觸發 repetitions as the DLL does
#   ['open', element]                        a forced open's gains (臨, 雙斷)
#   ['nohit', {silenced, broke, overload_after, casting, sneak}]  a no-form hit's self part
#   ['leave', element, burst] / ['enter', element] / ['second'] / ['resonance', count] / ['sync', count, announce]
#   ['end', element, reason, mult]           an end (the N3 body with the N4 parts)
#   ['hurt', {facts}]                        a hit you take (the facts the sink and the task read)
#   ['cast', near, marked, cost, true_mult]  an enemy spell cast (逼近, 反咒)
#   ['age', seconds]

def run_steps(w, steps):
    t = w.target
    for step in steps:
        op = step[0]
        if op == 'hit':
            element, power = step[1], step[2]
            o = step[3] if len(step) > 3 else {}
            cost, surge = 0.0, False
            if element == BLOOD and power:
                cost, mult, flat, surge = w.blood_terms(power, o.get('real', power))
                w.op('blood', cost, mult, flat)
            before = set(t.marks)
            at = len(w.ops)
            w.hit(element, power)
            opened = any(r[0] == 'event' and r[1] == 'Open' and r[2] == element for r in w.ops[at:])
            cut_from = next((e for e in sorted(before) if e not in t.marks and e != element), 0)
            extra, repeats = w.self_hit(element, w.form, power, o.get('sneak', False), o.get('crit', False), opened, cut_from,
                                        o.get('casting', False), cost, surge)
            w.op('result', 1.0 if extra else 0.0, float(repeats))
            if o.get('repeat'):
                w.repeat = True
                for _ in range(repeats):
                    w.hit(element, power)
                    w.self_hit(element, w.form, power, o.get('sneak', False), o.get('crit', False), False, 0,
                               o.get('casting', False), cost, surge, repeat=True)
                w.repeat = False
        elif op == 'open':
            w.self_open(step[1])
        elif op == 'nohit':
            o = step[1]
            w.self_noform(o.get('silenced', False), o.get('broke', False), o.get('overload_after', -1.0),
                          o.get('casting', False), o.get('sneak', False))
        elif op == 'leave':
            w.form_leave(step[1], step[2])
            w.self_leave(step[1], step[2])
        elif op == 'enter':
            w.self_enter(step[1])
        elif op == 'second':
            w.self_second()
        elif op == 'resonance':
            w.add_resonance(max(1, min(step[1], 8)))
        elif op == 'sync':
            w.set_sync(step[1], step[2])
        elif op == 'end':
            w.end(step[1], step[2], step[3])
        elif op == 'hurt':
            f = dict(step[1])
            w.hp = f['after']
            w.hurt(f)
        elif op == 'cast':
            w.spell_cast(step[1], step[2], step[3], step[4])
        elif op == 'age':
            w.age(step[1])
        else:
            raise ValueError(step)


def _n(tree, *names):
    return {(tree, n) for n in names}


def _facts(**kw):
    """A hurt: health 100 -> after, magicka, max magicka 100, stamina 100, unless given."""
    f = dict(attacker=True, melee=True, spell=False, destructive=False, blocked=False, cloak=False, afterimage=False,
             linger=False, before=100.0, magicka_before=0.0, overload_before=0.0, guard_before=0.0, after=90.0,
             magicka=0.0, magicka_max=100.0, stamina=100.0)
    f.update(kw)
    return f


def scenario_specs():
    S = []
    add = S.append
    T, M = 'target', 'me'
    F = FOREVER
    # ---- 2.4 sync
    add(('sync: 4 + a hit = stage 1, ESSB_SyncUp, 回饋 heals B_max x2', dict(form=FIRE, branches=_n('common', '回饋')),
         [(M, 'Sync', 4, 1, F)], [], [('hit', FIRE, False)]))
    add(('sync: 同調門檻 10 points lower the thresholds to 4 / 12 / 24', dict(form=FIRE, ranks={('common', '同調門檻'): 10}),
         [(M, 'Sync', 3, 1, F)], [], [('hit', FIRE, False)]))
    add(('sync: 專一 after 60 s halves the thresholds again', dict(form=FIRE, branches=_n('common', '專一')),
         [(M, 'Sync', 6, 1, F), (M, 'FormHeld', FIRE, 61, F)], [], [('hit', FIRE, False)]))
    add(('sync: 先制 and 開啟專精主線 add on the open', dict(form=FROST, branches=_n('common', '先制'), ranks={('common', '開印時'): 10}),
         [], [], [('hit', FROST, False)]))
    add(('sync: 血脈 +2 on a blood open', dict(form=BLOOD, branches=_n('blood', '血脈'), hp=100.0), [], [], [('hit', BLOOD, False)]))
    add(('sync: ESSB_SyncT1..3 at 3 / 8 / 12 move the stages', dict(form=FIRE, sync_t=(3, 8, 12)), [(M, 'Sync', 2, 1, F)], [],
         [('hit', FIRE, False)]))
    add(('sync: a switch keeps a count quietly', dict(form=FIRE, branches=_n('common', '回饋')), [(M, 'Sync', 2, 1, F)], [],
         [('sync', 16, False)]))
    add(('sync: Papyrus sets 0: the count goes', dict(form=FIRE), [(M, 'Sync', 12, 1, F)], [], [('sync', 0, True)]))
    add(('water cut: 導引 jumps the sync to the next threshold', dict(form=FIRE), [(M, 'Sync', 7, 1, F)], [(WATER, 0, 1, 10)],
         [('hit', FIRE, False)]))
    # ---- 雷 (2.1, 2.3, 5.5)
    add(('lightning open: +2 charges, 開印電荷 10 points +2', dict(form=LIGHTNING, ranks={('lightning', '開印電荷'): 10}), [], [],
         [('hit', LIGHTNING, False)]))
    add(('lightning refresh: +1 charge, cap 6', dict(form=LIGHTNING), [(M, 'Charge', 6, 3, 10)], [(LIGHTNING, 0, 1, 8)],
         [('hit', LIGHTNING, False)]))
    add(('lightning: 電荷上限 9 points and 萬象 raise the cap', dict(form=LIGHTNING, ranks={('lightning', '電荷上限'): 9,
         ('common', '每種元素狀態上限'): 10}), [(M, 'Charge', 10, 3, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, False)]))
    add(('lightning: a full power hit discharges (crit x2.5), the mark stays', dict(form=LIGHTNING), [(M, 'Charge', 6, 3, 10)],
         [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, True)]))
    add(('lightning: 雷暴 30% on a full normal hit (chance succeeds)', dict(form=LIGHTNING, rng='yes', branches=_n('lightning', '雷暴')),
         [(M, 'Charge', 6, 3, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, False)]))
    add(('lightning: 雷暴 fails (chance fails)', dict(form=LIGHTNING, rng='no', branches=_n('lightning', '雷暴')),
         [(M, 'Charge', 6, 3, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, False)]))
    add(('lightning: 雷神 at sync 3 discharges when the charges fill, magicka back, 疾電', dict(form=LIGHTNING, sync=3,
         branches=_n('lightning', '雷神', '疾電')), [(M, 'Charge', 5, 3, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, False)]))
    add(('lightning: full charges paralyse a casting target (30%, succeeds)', dict(form=LIGHTNING, rng='yes'),
         [(M, 'Charge', 6, 3, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', LIGHTNING, False, dict(casting=True))]))
    add(('lightning: not full, no paralysis', dict(form=LIGHTNING, rng='yes'), [(M, 'Charge', 4, 3, 10)], [(LIGHTNING, 0, 1, 8)],
         [('hit', LIGHTNING, False, dict(casting=True))]))
    add(('lightning: 強感電 fills on a power open, 15 s cooldown', dict(form=LIGHTNING, branches=_n('lightning', '強感電')), [], [],
         [('hit', LIGHTNING, True)]))
    add(('lightning: 雷鳴 +2 on a crit open', dict(form=LIGHTNING, branches=_n('lightning', '雷鳴')), [], [],
         [('hit', LIGHTNING, False, dict(crit=True))]))
    add(('lightning end: charges consumed, 餘電 pending on a cut, 疾電', dict(form=FIRE, branches=_n('lightning', '餘電', '疾電')),
         [(M, 'Charge', 4, 1, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('lightning end: 蓄餘 keeps the charges', dict(form=FIRE, branches=_n('lightning', '蓄餘')), [(M, 'Charge', 4, 1, 10)],
         [(LIGHTNING, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('餘電: the next open carries a x0.5 discharge', dict(form=FIRE), [(M, 'PendingDischarge', 4, 1, 30)], [], [('hit', FIRE, False)]))
    add(('lightning burst: 雷霆 5 s, every hit discharges x0.3', dict(form=LIGHTNING, branches=_n('lightning', '雷霆')),
         [(M, 'Charge', 5, 1, 10)], [(LIGHTNING, 0, 1, 8)], [('end', LIGHTNING, BURST, 1.0), ('hit', FIRE, False)]))
    add(('lightning leave: a switch snapshots the charges for the cut end', dict(form=LIGHTNING), [(M, 'Charge', 5, 1, 10)],
         [(LIGHTNING, 0, 1, 8)], [('leave', LIGHTNING, False), ('hit', FIRE, False)]))
    add(('過載終焉: the charges cross forms; an end with 8+ is x2', dict(form=LIGHTNING, branches=_n('lightning', '過載終焉'),
         ranks={('lightning', '電荷上限'): 6}), [(M, 'Charge', 8, 1, 10)], [(FIRE, 0, 1, 8)],
         [('leave', LIGHTNING, True), ('hit', FROST, False)]))
    add(('雷臨強化: +5 charges when the form opens', dict(form=LIGHTNING, branches=_n('lightning', '雷臨強化')), [], [],
         [('enter', LIGHTNING)]))
    add(('lightning hurt: 逆電 +1 charge, 2 s', dict(form=LIGHTNING, branches=_n('lightning', '逆電')), [(M, 'Charge', 2, 1, 10)], [],
         [('hurt', _facts())]))
    add(('lightning hurt: 靜電 marks the melee attacker', dict(form=LIGHTNING, branches=_n('lightning', '靜電')), [], [],
         [('hurt', _facts())]))
    # ---- 土 (2.3, 5.6)
    add(('earth open: 岩甲 +2 (25 armour a layer)', dict(form=EARTH), [], [], [('hit', EARTH, False)]))
    add(('earth open: 岩膚 +4, 開印岩甲 5 points +1, 磐石 40 a layer', dict(form=EARTH, branches=_n('earth', '岩膚', '磐石'),
         ranks={('earth', '開印岩甲'): 5}), [], [], [('hit', EARTH, False)]))
    add(('earth refresh +1, 厚土 cap 10', dict(form=EARTH, branches=_n('earth', '厚土')), [(M, 'RockArmor', 7, 1, F),
         (M, 'RockArmorAV', 175, 1, F)], [(EARTH, 0, 1, 8)], [('hit', EARTH, False)]))
    add(('碎岩: a full power hit smashes the armour out, 蓄勁 +3', dict(form=EARTH), [(M, 'RockArmor', 5, 1, F),
         (M, 'RockArmorAV', 125, 1, F)], [(EARTH, 0, 1, 8)], [('hit', EARTH, True)]))
    add(('蓄能: 蓄勁 full on a power hit becomes the next quake bonus', dict(form=EARTH, branches=_n('earth', '蓄能')),
         [(M, 'StoredForce', 10, 1, F), (M, 'RockArmor', 2, 1, F), (M, 'RockArmorAV', 50, 1, F)], [(EARTH, 0, 1, 8)],
         [('hit', EARTH, True)]))
    add(('蓄能: any 蓄勁 converts on a power hit (3 points -> +15% quake)', dict(form=EARTH, branches=_n('earth', '蓄能')),
         [(M, 'StoredForce', 3, 1, F), (M, 'RockArmor', 2, 1, F), (M, 'RockArmorAV', 50, 1, F)], [(EARTH, 0, 1, 8)],
         [('hit', EARTH, True)]))
    add(('蓄能: a block converts 4 points into 4% bracing', dict(form=EARTH, branches=_n('earth', '蓄能')),
         [(M, 'StoredForce', 4, 1, F)], [], [('hurt', _facts(blocked=True, after=98.0))]))
    add(('碎岩 with the stored quake bonus', dict(form=EARTH), [(M, 'RockArmor', 5, 1, F), (M, 'RockArmorAV', 125, 1, F),
         (M, 'ChargedQuake', 0.5, 1, 3600)], [(EARTH, 0, 1, 8)], [('hit', EARTH, True)]))
    add(('地動: sync 3, target stamina under 30%, 5%/pt (succeeds)', dict(form=EARTH, sync=3, rng='yes',
         ranks={('earth', '地動'): 4}, body=dict(stamina=20.0)), [(M, 'RockArmor', 1, 1, F), (M, 'RockArmorAV', 25, 1, F)],
         [(EARTH, 0, 1, 8)], [('hit', EARTH, True)]))
    add(('earth hurt: 岩甲 -1', dict(form=EARTH), [(M, 'RockArmor', 3, 1, F), (M, 'RockArmorAV', 75, 1, F)], [], [('hurt', _facts())]))
    add(('earth hurt: 山岳 at sync 3 keeps it', dict(form=EARTH, sync=3, branches=_n('earth', '山岳')),
         [(M, 'RockArmor', 3, 1, F), (M, 'RockArmorAV', 75, 1, F)], [], [('hurt', _facts())]))
    add(('反震: full armour, melee, B_max x2 back and a knock, armour gone', dict(form=EARTH, branches=_n('earth', '反震')),
         [(M, 'RockArmor', 5, 1, F), (M, 'RockArmorAV', 125, 1, F)], [], [('hurt', _facts())]))
    add(('蓄勁: a block +2; 蓄能 turns a full one into bracing', dict(form=EARTH, branches=_n('earth', '蓄能')),
         [(M, 'StoredForce', 10, 1, F)], [], [('hurt', _facts(blocked=True, after=98.0))]))
    add(('固土: the earth end fills the armour', dict(form=FIRE, branches=_n('earth', '固土')), [], [(EARTH, 0, 1, 8)],
         [('hit', FIRE, False)]))
    add(('地臨強化: armour full when the form opens', dict(form=EARTH, branches=_n('earth', '地臨強化')), [], [], [('enter', EARTH)]))
    # ---- 風 (2.3, 2.6, 5.7)
    add(('wind open: gauge +2', dict(form=WIND), [], [], [('hit', WIND, False)]))
    add(('wind: the gauge reaches 4, one blade, back to 0', dict(form=WIND), [(M, 'WindGauge', 3, 1, 5)], [(WIND, 0, 1, 8)],
         [('hit', WIND, False)]))
    add(('wind sneak: gauge full, 暗風 blade x2', dict(form=WIND, branches=_n('wind', '暗風')), [(M, 'WindGauge', 1, 1, 5)],
         [(WIND, 0, 1, 8)], [('hit', WIND, False, dict(sneak=True))]))
    add(('wind open: 疾風痕 fills it (a blade), 先風 at sync 3, 亂舞 threshold 3', dict(form=WIND, sync=3,
         branches=_n('wind', '疾風痕', '先風', '亂舞')), [], [], [('hit', WIND, False)]))
    add(('千刃 at sync 3 (succeeds)', dict(form=WIND, sync=3, rng='yes', ranks={('wind', '千刃'): 4}), [(M, 'WindGauge', 1, 1, 5)],
         [(WIND, 0, 1, 8)], [('hit', WIND, False)]))
    add(('多段觸發: cutting a wind mark repeats the hit (2 + 5 points = 3 in all)', dict(form=FIRE, ranks={('wind', '多段觸發'): 5}),
         [], [(WIND, 0, 1, 8)], [('hit', FIRE, False, dict(repeat=True))]))
    add(('多段觸發: 聖佑 rises one tier each repetition', dict(form=DIVINE), [], [(WIND, 0, 1, 8)],
         [('hit', DIVINE, False, dict(repeat=True))]))
    add(('順勢: after the wind cut end every hit sends a blade', dict(form=FIRE, branches=_n('wind', '順勢')), [], [(WIND, 0, 1, 8)],
         [('hit', FIRE, False), ('age', 1.0), ('hit', FIRE, False)]))
    add(('殘影: a full gauge, melee, 30% (succeeds)', dict(form=WIND, rng='yes', branches=_n('wind', '殘影')),
         [(M, 'WindGauge', 4, 1, 5)], [], [('hurt', _facts())]))
    add(('殘影 absorbed the next hit: the window closes', dict(form=WIND, branches=_n('wind', '殘影')),
         [(M, 'Afterimage', 1, 0.5, 2), (M, 'WindGauge', 4, 1, 5)], [], [('hurt', _facts(afterimage=True, after=100.0))]))
    # ---- 冰 (5.4)
    add(('冰盾: a frost hit +1 layer (armour 20, resist 4%)', dict(form=FROST), [(M, 'IceShield', 2, 3, 8)], [(FROST, 0, 1, 8)],
         [('hit', FROST, False)]))
    add(('冰鎧: cap 8', dict(form=FROST, branches=_n('frost', '冰鎧')), [(M, 'IceShield', 8, 3, 8)], [(FROST, 0, 1, 8)],
         [('hit', FROST, False)]))
    add(('寒反: any attacker slowed 30% 3 s and freeze +1, 3 s per attacker', dict(form=FROST, branches=_n('frost', '寒反')),
         [], [], [('hurt', _facts(melee=False)), ('hurt', _facts(melee=False, before=90.0, after=80.0))]))
    add(('冰心: under 30% health, freeze the nearby, 30 s', dict(form=FROST, branches=_n('frost', '冰心')), [], [],
         [('hurt', _facts(before=40.0, after=25.0))]))
    # ---- 火 (5.3)
    add(('灼身: the melee attacker takes B_max x1 fire and your fire mark', dict(form=FIRE, branches=_n('fire', '灼身')), [], [],
         [('hurt', _facts())]))
    add(('灼身: a ranged attacker is not burnt', dict(form=FIRE, branches=_n('fire', '灼身')), [], [], [('hurt', _facts(melee=False))]))
    add(('浴火: sync 3, the fire-marked attacker pushes the heat', dict(form=FIRE, sync=3, branches=_n('fire', '浴火')),
         [(M, 'Heat1', 1, 3, 3600), (M, 'HeatDecay', 1, 1, 6)], [(FIRE, 0, 1, 8)], [('hurt', _facts())]))
    add(('自動洩壓: heat III and health under 10%', dict(form=FIRE), [(M, 'Heat3', 0, 1, 8)], [], [('hurt', _facts(before=20.0, after=8.0))]))
    # ---- 血 (1.1, 5.8)
    add(('blood power hit at full health pays 8%, 血刃 adds half', dict(form=BLOOD, branches=_n('blood', '血刃'), hp=100.0),
         [(M, 'BloodZone', 1, 1, F)], [(BLOOD, 0, 1, 8)], [('hit', BLOOD, True)]))
    add(('blood power hit at 50% pays 3.5%', dict(form=BLOOD, hp=50.0), [(M, 'BloodZone', 2, 1, F)], [(BLOOD, 0, 1, 8)],
         [('hit', BLOOD, True)]))
    add(('blood: a downed target counts as power without the cost', dict(form=BLOOD, hp=100.0), [(M, 'BloodZone', 1, 1, F)],
         [(BLOOD, 0, 1, 8)], [('hit', BLOOD, True, dict(real=False))]))
    add(('回湧: no cost, x1.5, +2 bleed', dict(form=BLOOD, hp=60.0), [(M, 'BloodZone', 2, 1, F), (M, 'SurgeUp', 1, 1, 8)],
         [(BLOOD, 0, 1, 8)], [('hit', BLOOD, True)]))
    add(('越線 on a hurt: down a zone splashes', dict(form=BLOOD, hp=80.0), [(M, 'BloodZone', 1, 1, F)], [],
         [('hurt', _facts(before=80.0, after=60.0))]))
    add(('護血: the pool takes 50% of a small hit and holds', dict(form=BLOOD, hp=100.0),
         [(M, 'BloodZone', 1, 1, F)], [], [('hurt', _facts(guard_before=5.0, after=99.0))]))
    add(('護血: the pool holds', dict(form=BLOOD, hp=100.0), [(M, 'BloodZone', 1, 1, F)], [],
         [('hurt', _facts(guard_before=50.0, after=99.0))]))
    add(('護血: a huge hit through a tiny pool kills (no keep-1)', dict(form=BLOOD, hp=100.0),
         [(M, 'BloodZone', 1, 1, F)], [], [('hurt', _facts(guard_before=5.0, after=20.0))]))
    add(('護血: the pool partially holds, the rest is real damage', dict(form=BLOOD, hp=100.0),
         [(M, 'BloodZone', 1, 1, F)], [], [('hurt', _facts(guard_before=6.0, after=90.0))]))
    add(('護血: the second hit of a frame pays from what the first left', dict(form=BLOOD, hp=100.0),
         [(M, 'BloodZone', 1, 1, F)], [], [('hurt', _facts(guard_before=5.0, guard_left=2.0, after=99.5))]))
    add(('護血: a switch empties the pool', dict(form=BLOOD), [(M, 'GuardPool', 12, 0, 0)], [], [('leave', BLOOD, False)]))
    # ---- 聖 (5.9)
    add(('懲戒: 聖佑 II, hit +1', dict(form=DIVINE), [(M, 'Holy2', 0, 3, 3600)], [], [('hurt', _facts())]))
    add(('懲戒: 誓約 attacker +2, 天誅 cap 8', dict(form=DIVINE, branches=_n('divine', '天誅')),
         [(M, 'Holy3', 0, 3, 3600), (M, 'Punish', 7, 1, 8), (T, 'Oath', 1, 1, 8)], [], [('hurt', _facts())]))
    add(('懲戒: 0.5 s between layers', dict(form=DIVINE), [(M, 'Holy2', 0, 3, 3600), (M, 'Punish', 2, 1, 8),
         (M, 'PunishCooldown', 1, 0.2, 0.5)], [], [('hurt', _facts())]))
    add(('誓約: the divine open marks the target 8 s', dict(form=DIVINE, branches=_n('divine', '誓約')), [], [], [('hit', DIVINE, False)]))
    add(('庇護: under 30% 聖佑 III, 30 s', dict(form=DIVINE, branches=_n('divine', '庇護')), [(M, 'Holy1', 1, 3, 3600)], [],
         [('hurt', _facts(before=35.0, after=20.0))]))
    # ---- 毒 / 暗 (5.10, 5.12)
    add(('毒皮: the melee attacker +2 doses', dict(form=POISON, branches=_n('poison', '毒皮')), [], [], [('hurt', _facts())]))
    add(('怨縛: a cursed attacker +1 curse, 2 s', dict(form=DARKNESS, branches=_n('darkness', '怨縛')), [(T, 'Curse', 2, 1, 10)], [],
         [('hurt', _facts())]))
    # ---- 水 (5.11)
    add(('水幕: 20% by magicka at 1.5 a point', dict(form=WATER), [], [], [('hurt', _facts(magicka_before=30.0, after=84.0, magicka=30.0))]))
    add(('水幕: magicka runs out, the rest is damage', dict(form=WATER), [], [],
         [('hurt', _facts(magicka_before=3.0, after=84.0, magicka=3.0))]))
    add(('水盾 + 止水 at sync 3: 45% at 1.0', dict(form=WATER, sync=3, branches=_n('water', '水盾', '止水')), [], [],
         [('hurt', _facts(magicka_before=60.0, after=89.0, magicka=60.0))]))
    add(('潮身: the veil empties magicka: cleanse, 20% back, 30 s', dict(form=WATER, branches=_n('water', '潮身', '淨化')), [], [],
         [('hurt', _facts(magicka_before=3.0, after=84.0, magicka=3.0))]))
    add(('水幕 does not take a non-destructive spell', dict(form=WATER), [], [],
         [('hurt', _facts(spell=True, melee=False, magicka_before=30.0, after=84.0, magicka=30.0))]))
    add(('洗淨: a water hit clears one negative effect, 3 s', dict(form=WATER, branches=_n('water', '洗淨')), [], [(WATER, 0, 1, 10)],
         [('hit', WATER, False), ('hit', WATER, False)]))
    add(('淨化: the cleanse clears all', dict(form=WATER, branches=_n('water', '洗淨', '淨化')), [], [], [('hit', WATER, False)]))
    # ---- 星 (2.3, 5.13)
    add(('star detonation: resonance, the gate turns it into 闇宙', dict(form=ASTRAL), [(M, 'Resonance', 8, 1, 20)], [],
         [('resonance', 3)]))
    add(('resonance under the gate', dict(form=ASTRAL), [(M, 'Resonance', 2, 1, 20)], [], [('resonance', 3)]))
    add(('天穹: gate 7 at sync 3', dict(form=ASTRAL, sync=3, branches=_n('astral', '天穹')), [(M, 'Resonance', 5, 1, 20)], [],
         [('resonance', 2)]))
    add(('闇星: a hit strikes a full detonation, 闇宙 -1', dict(form=ASTRAL, ranks={('astral', '永夜'): 2}), [(M, 'Cosmos', 3, 1, 10)],
         [], [('hit', ASTRAL, False)]))
    add(('闇星: the last 闇宙, 餘輝 3 resonance', dict(form=ASTRAL, branches=_n('astral', '餘輝')), [(M, 'Cosmos', 1, 1, 10)],
         [(ASTRAL, 0, 1, 8)], [('hit', ASTRAL, False)]))
    add(('星門: the open +1 resonance', dict(form=ASTRAL, branches=_n('astral', '星門')), [], [], [('hit', ASTRAL, False)]))
    add(('the end detonation counts resonance outside the dark star', dict(form=FIRE), [(T, 'Star', 2, 1, 30)],
         [(ASTRAL, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('墜星: a switch keeps the 闇宙, the cut settles it', dict(form=ASTRAL, branches=_n('astral', '墜星', '星殘')),
         [(M, 'Cosmos', 4, 1, 10), (M, 'Resonance', 3, 1, 20)], [(ASTRAL, 0, 1, 8)],
         [('leave', ASTRAL, False), ('hit', FIRE, False)]))
    # ---- 5.2 common: 極致, 化身, 協奏, 三重奏
    add(('極致: the 10th hit at sync 3 is an extra proc', dict(form=FIRE, sync=3, branches=_n('common', '極致')),
         [(M, 'Extreme', 9, 1, F)], [(FIRE, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('化身: sync 3, 10 s window, cooldown 30 - 5', dict(form=FIRE, sync=3, ranks={('common', '化身'): 5}), [], [(FIRE, 0, 1, 8)],
         [('hit', FIRE, False)]))
    add(('協奏: the first end after a switch x1.5 (flag 2)', dict(form=FIRE, branches=_n('common', '協奏')), [(M, 'Concert', 1, 1, 3600)],
         [(FROST, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('三重奏: the third element end in 10 s x3, keep-all', dict(form=FIRE, branches=_n('common', '三重奏')),
         [(M, 'Trio1', 1, 2, 10), (M, 'Trio2', 1, 4, 10)], [(LIGHTNING, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('三重奏: a second element only marks it', dict(form=FIRE, branches=_n('common', '三重奏')), [(M, 'Trio1', 1, 2, 10)],
         [(FROST, 0, 1, 8)], [('hit', FIRE, False)]))
    add(('leave: your resources clear; the switch leaves 協奏 pending', dict(form=EARTH),
         [(M, 'RockArmor', 3, 1, F), (M, 'RockArmorAV', 75, 1, F), (M, 'StoredForce', 4, 1, F), (M, 'Extreme', 3, 1, F),
          (M, 'FormHeld', EARTH, 20, F), (M, 'Sync', 9, 1, F)], [], [('leave', EARTH, False)]))
    add(('連殺 marker: a sneak hit leaves the form element 1 s', dict(form=WIND), [], [], [('hit', WIND, False, dict(sneak=True))]))
    # ---- 5.1 no form
    add(('no form: silencing +1 戰意, 斷咒 interrupts a caster +1', dict(form=0, branches=_n('noform', '斷咒')),
         [(M, 'Resolve', 2, 1, 10)], [], [('nohit', dict(silenced=True, casting=True))]))
    add(('no form: 破式 used the 戰意', dict(form=0), [(M, 'Resolve', 5, 1, 10)], [], [('nohit', dict(broke=True))]))
    add(('no form: the overload pool the siphon left, 3 s wait (蓄流 6)', dict(form=0, branches=_n('noform', '蓄流')),
         [(M, 'Overload', 10, 1, F)], [], [('nohit', dict(overload_after=25.0))]))
    add(('no form: a sneak hit leaves marker 12', dict(form=0), [], [], [('nohit', dict(sneak=True))]))
    add(('超載 decays 5% a second after the wait; 不竭 5 points 4%', dict(form=0, magicka_max=200.0, ranks={('noform', '不竭'): 5}),
         [(M, 'Overload', 30, 5, F)], [], [('second',)]))
    add(('超載 waits', dict(form=0), [(M, 'Overload', 30, 5, F), (M, 'OverloadWait', 1, 1, 3)], [], [('second',)]))
    add(('法盾: 30% by magicka at 1.0', dict(form=0), [], [], [('hurt', _facts(magicka_before=50.0, after=79.0, magicka=50.0))]))
    add(('法盾: magicka runs out, the rest is damage', dict(form=0), [], [],
         [('hurt', _facts(magicka_before=5.0, after=79.0, magicka=5.0))]))
    add(('法盾 does not share a DoT: the cut part of a burning spell is dealt back', dict(form=0), [], [],
         [('hurt', _facts(spell=True, melee=False, destructive=True, magicka_before=50.0, after=90.0, magicka=50.0,
                          dot_damage=30.0))]))
    add(('法盾 with overload: 45%, 0.75, the pool pays first; 法盾分擔 / 法盾效率', dict(form=0, ranks={('noform', '法盾分擔'): 5,
         ('noform', '法盾效率'): 10}), [(M, 'Overload', 4, 1, F)],
         [], [('hurt', _facts(magicka_before=50.0, overload_before=4.0, after=80.0, magicka=50.0))]))
    add(('餘魔: the shield empties magicka: 2 s of stamina sharing', dict(form=0, branches=_n('noform', '餘魔')), [], [],
         [('hurt', _facts(magicka_before=2.0, after=79.0, magicka=2.0)),
          ('hurt', _facts(linger=True, before=79.0, after=65.0, magicka=0.0))]))
    add(('化法為力: 30% of a spell back as magicka, the rest into the overload', dict(form=0), [], [],
         [('hurt', _facts(spell=True, melee=False, after=80.0, magicka=97.0))]))
    add(('化法為力 with 化勁 during 逼近: x2, capped pool', dict(form=0, branches=_n('noform', '化勁')), [(M, 'CloseIn', 1, 0.5, 2),
         (M, 'Overload', 45, 1, F)], [], [('hurt', _facts(spell=True, melee=False, destructive=True, magicka_before=100.0,
                                                         after=80.0, magicka=100.0))]))
    add(('咒返: a spell hit puts 滅法印 on the caster, 5 s', dict(form=0, branches=_n('noform', '咒返')), [], [],
         [('hurt', _facts(spell=True, melee=False, after=95.0))]))
    add(('反擊: a block opens the riposte window', dict(form=0, branches=_n('noform', '反擊')), [], [],
         [('hurt', _facts(blocked=True, after=99.0))]))
    add(('破護: a cloak tick is refused 2 s', dict(form=0, branches=_n('noform', '破護')), [], [],
         [('hurt', _facts(spell=True, melee=False, cloak=True, after=99.0))]))
    add(('不屈: a hit +1 戰意, 3 s', dict(form=0, branches=_n('noform', '不屈')), [(M, 'Resolve', 1, 4, 10)], [],
         [('hurt', _facts()), ('hurt', _facts(before=90.0, after=80.0))]))
    add(('逼近: a hostile cast within 15 m: 2 s +30% speed, 6 s', dict(form=0, branches=_n('noform', '逼近')), [], [],
         [('cast', True, False, 0.0, 1.0)]))
    add(('反咒: the marked caster takes its cost x(1 + 2%/level) true damage, 噬命 half back', dict(form=0,
         branches=_n('noform', '反咒', '噬命')), [], [], [('cast', False, True, 40.0, 1.0)]))
    add(('反咒 does nothing in a form', dict(form=FIRE, branches=_n('noform', '反咒')), [], [], [('cast', True, True, 40.0, 1.0)]))
    add(('lethal: ESSB_Lethal for 神佑', dict(form=0), [], [], [('hurt', _facts(before=5.0, after=0.0))]))
    return S


def build_world(damage, options):
    opts = dict(options)
    ranks = opts.pop('ranks', {})
    branches = opts.pop('branches', set())
    return World23(damage, ranks=ranks, branches=branches, **opts)


def seed(w, statuses, marks, flags):
    guard = [s for s in statuses if s[1] == 'GuardPool']
    _n3.seed(w, [s for s in statuses if s[1] != 'GuardPool'], marks, flags)
    for who, kind, magnitude, elapsed, duration in guard:
        w.me.guard = float(magnitude)


def evaluate(damage, spec):
    name, options, statuses, marks, steps = spec
    options = dict(options)
    flags = options.pop('target_flags', {})
    w = build_world(damage, options)
    w.me.guard = None
    seed(w, statuses, marks, flags)
    run_steps(w, steps)
    return w.summary()
