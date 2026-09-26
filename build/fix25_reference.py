"""Round 25 (slice N6) reference model: the DLL's per-second work, the domains' DLL halves and the hotkey decisions,
written from 元素魔戰士規劃-v0.4.md on its own (native/include/Timer.h is never consulted). Where v0.4 gives no number,
the model uses the one the Papyrus it replaces used (named in the comment); the round-22 model (build/fix22_reference.py)
supplies the poison dose arithmetic of 2.7 (擴散一劑) and D_react's categorical terms, as it does for rounds 23 and 24.
native/tests/timer_test.cpp runs every scenario below through the DLL's functions and requires the same results.

NODE_NAMES   every node:: constant Timer.h reads that earlier rounds did not name -> (tree, v0.4 name)
HAND         hand-computed anchors (the arithmetic written out in the comment), checked against the model's output
"""
import math

import fix22_reference as _n3

NODE_NAMES = {
    'kWaterFlowRate': ('water', '長流每秒回復'),        # 5.11 持續熟練主線：+0.2%／點
    'kWaterFlowSync': ('water', '同調每段長流回復'),    # 5.11 持續大師主線：同調每段 +0.05%／點
    'kWaterLongRiver': ('water', '長河'),              # 5.11 持續傳奇主線：同調三段 +0.05%／點、附近同伴
    'kCommonComposure': ('common', '定神'),            # 5.2：同調三段時免疫減速
    'kCommonSmoothSwitch': ('common', '順轉'),         # 5.2：開形態免魔力門檻
}

FIRE, FROST, LIGHTNING, EARTH, WIND, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL = range(1, 12)
TREE = _n3.TREE
DOMAIN_ELEMENTS = (FIRE, FROST, EARTH, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL)   # v0.4 section 5's nine domains
UPKEEP_BASE, UPKEEP_DARK, UPKEEP_RELIEF = 1.0, 2.0, 0.7   # 1.1（settings.json upkeep_*，fixture checks them）
METRE = 70.0


# ================================================================ the clock (N6-1)

def cadence(steps):
    """The timer counts game-running time only: a step while stopped (paused, a menu, loading) counts nothing; one step
    counts at most 250 ms; a second (and every 5 s the environment) is due when the running time reaches it; a missed
    second is dropped, never made up. The first step only starts the clock."""
    last, active, next_second, next_env = 0, 0, 1000, 0
    out = []
    for now, stopped in steps:
        beat = [0, 0, 0.0]
        if last == 0 or now < last:
            last = now
            out.append(beat)
            continue
        dt = min(now - last, 250)
        last = now
        if stopped:
            out.append(beat)
            continue
        active += dt
        beat[2] = dt / 1000.0
        if active >= next_second:
            beat[0] = 1
            next_second += 1000
            if next_second <= active:
                next_second = active + 1000
        if active >= next_env:
            beat[1] = 1
            next_env = active + 5000
        out.append(beat)
    return out


# ================================================================ the forms' second (1.1, 2.10, 5.11)

def upkeep(element, magicka_max, level, mult_upkeep):
    """1.1: 最大魔力 × 基礎% × (1 − 0.7 × 樹等級／100) × 維持費倍率；暗 2.0%、其餘 1.0%；血形態不扣魔力。"""
    if element == BLOOD or element == 0:
        return 0.0
    lv = min(100.0, max(1.0, level))
    pct = UPKEEP_DARK if element == DARKNESS else UPKEEP_BASE
    return max(0.0, magicka_max * pct / 100.0 * (1 - UPKEEP_RELIEF * lv / 100.0) * mult_upkeep)


def blood_upkeep_pct(fraction):
    """1.1 血位表「損血（維持每秒）」：100% 1.0%、70% 0.6%、30% 0.2%、10% 0，線性內插（10% 以下 0）。"""
    points = [(0.1, 0.0), (0.3, 0.2), (0.7, 0.6), (1.0, 1.0)]
    f = min(1.0, max(0.0, fraction))
    if f <= 0.1:
        return 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if f <= x1:
            return y0 + (f - x0) * (y1 - y0) / (x1 - x0)
    return 1.0


def flow_fraction(w):
    """5.11 長流：每秒生命與耐力 2.0% +0.2%／點（熟練）+0.05%／點 × 同調段（大師）+0.05%／點（長河，同調三段）。"""
    f = (w.flow_base + w.flow_per_rank * w.rank('water', '長流每秒回復')) / 100.0
    f += 0.0005 * w.rank('water', '同調每段長流回復') * w.sync
    if w.sync >= 3:
        f += 0.0005 * w.rank('water', '長河')
    return f


class World25(_n3.World):
    """The round-22 world (tuning, nodes, boards, ops) plus the per-second facts."""

    def __init__(self, damage, spec):
        t = spec.get('tuning', {})
        super().__init__(damage, ranks=spec.get('ranks'), branches=spec.get('branches'), sync=t.get('sync', 0),
                         mult_duration=t.get('duration', 1.0), mult_cooldown=t.get('cooldown', 1.0), base=t.get('base', 1.0),
                         recovery=t.get('recovery', 1.0), mult_dot=t.get('dot', 1.0), night=t.get('night', False),
                         interior=t.get('interior', False), slow_cap=t.get('slow_cap', 70.0), level=spec.get('levels', {}),
                         body=spec.get('body'))
        self.mult_upkeep = t.get('upkeep', 1.0)
        self.flow_base = t.get('flow_base', 2.0)
        self.flow_per_rank = t.get('flow_per_rank', 0.2)
        for kind, (mag, elapsed, duration) in spec.get('me', {}).items():
            self.me.kinds[kind] = _n3.Slot(mag, elapsed, duration)
        for kind, (mag, elapsed, duration) in spec.get('target', {}).items():
            self.target.kinds[kind] = _n3.Slot(mag, elapsed, duration)
        if 'poison' in spec:
            m, elapsed, duration = spec['poison']
            self.target.poison = _n3.Slot(m, elapsed, duration)

    def charge_cap(self):
        return 6 + self.rank('lightning', '電荷上限') // 3 + self.cap_bonus()

    def set_me(self, kind, magnitude, seconds):
        self.op('apply', kind, -1, magnitude, seconds)
        self.put(self.me, kind, magnitude, seconds)

    def clear_me(self, kind):
        if self.me.has(kind):
            self.op('remove', kind, -1)
            self.drop(self.me, kind)


def form_second(w, f, allies):
    """One second of the form you are in (1.1 維持費 and 魔力歸零, 5.11 長流 / 長河, 2.10 雷雨)."""
    out = dict(spent=0.0, bled=0.0, flow=0.0, closing=0, charged=0)
    form = f['form']
    if not 1 <= form <= 11:
        w.clear_me('ManaEmpty')
        return out
    if form == BLOOD:
        # 血形態不扣魔力、不受魔力歸零關閉；依血位扣生命（代價路徑，留 1 點由引擎端做）。
        w.clear_me('ManaEmpty')
        # 審查修正：血位與扣血量用同一個上限（永久生命，其他血位規則的分母）。
        fraction = f['health'] / f['health_permanent'] if f['health_permanent'] > 0 else 1.0
        out['bled'] = f['health_permanent'] * blood_upkeep_pct(fraction) / 100.0 * w.mult_upkeep
        if out['bled'] > 0:
            w.op('pay', -1, out['bled'])
    else:
        fee = upkeep(form, f['magicka_max'], w.level.get(TREE[form], 1), w.mult_upkeep)
        out['spent'] = min(max(fee, 0.0), max(0.0, f['magicka']))
        if out['spent'] > 0:
            w.op('spend', -1, out['spent'])
        if f['magicka'] - out['spent'] <= 0:
            # 魔力歸零持續 2 秒自動關閉：第一秒記下（你身上的標記），第三個歸零的秒（標記已 2 秒）關閉。
            if not w.me.has('ManaEmpty'):
                w.set_me('ManaEmpty', 1.0, 3600.0)
            elif w.me.kinds['ManaEmpty'].elapsed >= 1.5:
                w.clear_me('ManaEmpty')
                w.op('event', -1, 'Close')
                out['closing'] = 1
        else:
            w.clear_me('ManaEmpty')
        if form == WATER:
            out['flow'] = flow_fraction(w)
            if f['health_max'] * out['flow'] > 0:
                w.op('heal', -1, f['health_max'] * out['flow'] * w.recovery)
            if f['stamina_max'] * out['flow'] > 0:
                w.op('stamina', -1, f['stamina_max'] * out['flow'] * w.recovery)
            if fee > 0:
                w.op('magicka', -1, fee * 0.8)   # 長流另回維持費的 80%（不吃成長、不吃回復倍率）
            if w.sync >= 3 and w.rank('water', '長河') > 0:
                for at, hmax, smax in allies[:5]:
                    w.op('healTarget', at, hmax * out['flow'] * w.recovery)
                    w.op('staminaTarget', at, smax * out['flow'] * w.recovery)
    if form == LIGHTNING and f.get('thunder') and not w.me.has('StormCooldown'):
        # 2.10 雷雨：雷形態每 3 秒自動 +1 電荷（冷卻倍率）；電荷上限 6（+1／每 3 點），10 秒。
        charges = min(w.me.layers('Charge') + 1, w.charge_cap())
        w.set_me('Charge', float(charges), w.scaled(10.0))
        w.set_me('StormCooldown', 1.0, w.cooldown(3.0))
        out['charged'] = 1
    return out


# ================================================================ the environment (2.10)

def weather_class(flags):
    for bit, cls in ((1, 0), (2, 1), (4, 2), (8, 3)):
        if flags & bit:
            return cls
    return -1


def environment(f):
    """v0.4 2.10（審查修正）：下雨、下雪或站在水中 → 浸濕；暴風雪＝下雪且風大（風速 ≥ 128／255）→ stormy（凍結累積 ×2）；
    雷雨＝下雨且有雷電（雷電頻率不是 255＝沒有）→ thunder（雷形態電荷）；室內、地城沒有天氣；夜晚 20:00–6:00。"""
    outdoors = not f['interior']
    weather = f['weather'] in (2, 3) and outdoors
    return dict(wet=int(weather or f['swimming'] or f['underwater']),
                stormy=int(outdoors and f['weather'] == 3 and f['wind'] >= 128),
                thunder=int(outdoors and f['weather'] == 2 and f['lightning'] != 255),
                night=int(f['hour'] >= 20.0 or f['hour'] < 6.0))


# ================================================================ the domains (R4)

def inside(sites, at):
    """你（或一名敵人）站在一個還活著的領域裡：距離領域中心 3 公尺以內。"""
    return sorted({e for e, x, y, z in sites if math.dist((x, y, z), at) <= 3 * METRE})


def domain_self(w, elements):
    out = dict(fuse=0, immune=0, cleanse=0)
    if FIRE in elements:
        # 火域：你在其中熱度升階免等待；進入火域時白熱引信一次性 +5 秒（上一秒不在火域才算進入）。
        if not w.me.has('FireDomainPlayer') and w.me.has('Heat3'):
            fuse = w.me.kinds['Heat3']
            w.set_me('Heat3', fuse.magnitude, fuse.remaining() + 5.0)
            out['fuse'] = 1
        w.set_me('FireDomainPlayer', 1.0, 2.0)
    if FROST in elements:
        w.set_me('FrostDomainPlayer', 1.0, 2.0)   # 冰原：你在其中免疫減速
        out['immune'] = 1
    if BLOOD in elements:
        w.op('heal', -1, 20.0 * w.recovery)       # 血池：你在其中每秒回血（Papyrus 的 20）
    if DIVINE in elements:
        w.op('heal', -1, 25.0 * w.recovery)       # 聖域：你持續回復（Papyrus 的生命 25、魔力 20）
        w.op('magicka', -1, 20.0 * w.recovery)
    if WATER in elements:
        w.op('heal', -1, 15.0 * w.recovery)       # 潮池：你在其中回血回耐力（各 15）並每秒洗淨一次
        w.op('stamina', -1, 15.0 * w.recovery)
        w.op('event', -1, 'Cleanse', 0.0)
        out['cleanse'] = 1
    return out


def domain_enemy(w, elements, refund):
    """一名敵人在活著的領域裡的這一秒（hazard 已掛上標記、地裂的耐力不回復與死域的無法治療）。"""
    if FROST in elements:
        w.op('slow', 0, min(50.0, max(0.0, min(w.slow_cap, 70.0))), 2.0)   # 冰原：減速 50%（受減速上限）
    if EARTH in elements and w.body['stamina'] <= 0:
        w.op('event', 0, 'Knock', 2.0)                                      # 地裂：耐力歸 0 跌倒
    if POISON in elements:
        w.spread_doses(1.0)                                                 # 毒霧（R5）：每秒擴散一劑併進牠的中毒
    if WATER in elements:
        w.op('wash', 0, 1.0, refund)                                        # 潮池：每秒被沖刷一個增益
    if DARKNESS in elements:
        amount = w.bmax(DARKNESS) * 0.5 * w.react_scale(DARKNESS) * w.vulnerability() * w.mult_dot   # 死域：B_max ×0.5
        if amount > 0:
            w.op('damage', 0, DARKNESS, amount)


def spawn_seconds(element, seconds, mult_duration):
    """The whole seconds of the spell that places a domain (the HAZD lasts as long): seconds × 持續時間倍率, 1..24."""
    if element not in DOMAIN_ELEMENTS or seconds <= 0:
        return 0
    return min(24, max(1, int(seconds * mult_duration + 0.5)))


# ================================================================ slows on you

def is_slow(v):
    """一個「減速」：有持續時間、有害、作用在移速（SpeedMult）的數值／峰值／雙數值修正。"""
    modifier = v['archetype'] in (0, 5, 34)
    speed = v['primary'] == 30 or (v['archetype'] == 5 and v['secondary'] == 30)
    return int(modifier and speed and v['detrimental'] and v['duration'] > 0)


def slow_immune(w):
    """冰原（你在其中）、定神、御風（同調三段）免疫減速。"""
    return int(w.me.has('FrostDomainPlayer') or (w.sync >= 3 and (w.has('common', '定神') or w.has('wind', '御風'))))


# ================================================================ hotkeys (R6)

def key_code(device, ident):
    if device == 0:
        return ident if ident < 256 else -1
    if device == 1:
        return 256 + ident if ident < 10 else -1
    if device == 2:
        order = [0x0001, 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040, 0x0080, 0x0100, 0x0200, 0x1000, 0x2000, 0x4000, 0x8000]
        if ident in order:
            return 266 + order.index(ident)
        return {0x9: 280, 0xA: 281}.get(ident, -1)
    return -1


def hotkey(code, enabled, keys):
    if not enabled or code <= 0:
        return 0
    for i, k in enumerate(keys):
        if k == code:
            return i + 1
    return 0


def gate_open(g):
    return int(not (g['paused'] or g['menu'] or g['console'] or g['text'] or g['loading']))


def plan_switch(f, wanted):
    """1.1：開形態需要魔力高於上限 10%（血形態、順轉、免門檻例外）；同一形態再按一次＝關閉；切換不需要魔力。"""
    if not f['enabled'] or f['dead'] or not 1 <= wanted <= 11:
        return ['Ignore', 0, 0]
    if f['active'] and f['current'] == wanted:
        return ['Close', 0, 0]
    if not f['active']:
        if wanted != BLOOD and not f['free_pass'] and not f['free_open'] and f['magicka'] < f['magicka_max'] * 0.1:
            return ['Refuse', 0, 0]
        return ['Open', wanted, 1]
    return ['Switch', wanted, 0]


# ================================================================ scenarios

def _form(name, facts, **spec):
    base = dict(form=0, magicka=100.0, magicka_max=100.0, health=100.0, health_max=100.0, health_permanent=100.0, stamina=100.0,
                stamina_max=100.0, thunder=False)
    base.update(facts)
    return dict(group='form', name=name, facts=base, allies=spec.pop('allies', []), **spec)


def scenario_specs():
    out = []
    # ---- the clock
    steps = [(1000 + 100 * i, False) for i in range(25)]
    out.append(dict(group='cadence', name='clock: 100 ms steps, seconds at 1 s and 2 s of running time', steps=steps))
    steps = [(1000, False)] + [(1000 + 100 * i, False) for i in range(1, 5)] + [(1500 + 100 * i, True) for i in range(1, 300)] + \
            [(31400 + 100 * i, False) for i in range(1, 12)]
    out.append(dict(group='cadence', name='clock: a 30 s pause counts nothing (N6-1)', steps=steps))
    out.append(dict(group='cadence', name='clock: a 5 s stall counts 250 ms, the missed seconds are dropped',
                    steps=[(1000, False), (1100, False), (6100, False), (6200, False)] + [(6200 + 100 * i, False) for i in range(1, 12)]))
    out.append(dict(group='cadence', name='clock: the environment every 5 s of running time',
                    steps=[(1000 + 250 * i, False) for i in range(50)]))
    # ---- the forms' second
    out.append(_form('upkeep: fire, tree 1, 200 magicka', dict(form=FIRE, magicka=150.0, magicka_max=200.0)))
    out.append(_form('upkeep: darkness, tree 100, slider x2', dict(form=DARKNESS, magicka=80.0, magicka_max=300.0),
                     levels={'darkness': 100}, tuning=dict(upkeep=2.0)))
    out.append(_form('upkeep: tree level 0 reads as 1, 150 reads as 100', dict(form=FROST, magicka=90.0, magicka_max=100.0),
                     levels={'frost': 0}))
    out.append(_form('upkeep: tree 150 (clamped to 100)', dict(form=FROST, magicka=90.0, magicka_max=100.0), levels={'frost': 150}))
    out.append(_form('upkeep: slider 0 is free', dict(form=EARTH, magicka=90.0, magicka_max=100.0), tuning=dict(upkeep=0.0)))
    out.append(_form('upkeep: no more than you have; empty -> the 2 s clock starts',
                     dict(form=ASTRAL, magicka=0.5, magicka_max=200.0)))
    out.append(_form('upkeep: empty 1 s -> nothing yet', dict(form=ASTRAL, magicka=0.0, magicka_max=200.0),
                     me={'ManaEmpty': [1.0, 1.0, 3600.0]}))
    out.append(_form('upkeep: empty 2 s -> the form closes', dict(form=ASTRAL, magicka=0.0, magicka_max=200.0),
                     me={'ManaEmpty': [1.0, 2.0, 3600.0]}))
    out.append(_form('upkeep: magicka back -> the clock is cleared', dict(form=ASTRAL, magicka=50.0, magicka_max=200.0),
                     me={'ManaEmpty': [1.0, 1.0, 3600.0]}))
    out.append(_form('no form: the clock is cleared, nothing paid', dict(form=0), me={'ManaEmpty': [1.0, 1.0, 3600.0]}))
    out.append(_form('blood: 70% health pays 0.6% of max (no magicka, no close)',
                     dict(form=BLOOD, magicka=0.0, health=70.0, health_max=120.0, health_permanent=100.0),
                     me={'ManaEmpty': [1.0, 2.0, 3600.0]}))
    out.append(_form('blood: full health 1.0%, slider x1.5', dict(form=BLOOD, health=200.0, health_max=200.0, health_permanent=200.0),
                     tuning=dict(upkeep=1.5)))
    out.append(_form('blood: 50% health 0.4%', dict(form=BLOOD, health=50.0, health_max=100.0, health_permanent=100.0)))
    out.append(_form('blood: 10% health pays nothing', dict(form=BLOOD, health=10.0, health_max=100.0, health_permanent=100.0)))
    out.append(_form('blood: 5% health pays nothing', dict(form=BLOOD, health=5.0, health_max=100.0, health_permanent=100.0)))
    out.append(_form('water: 長流 base, tree 1', dict(form=WATER, magicka=100.0, magicka_max=200.0, health_max=300.0, stamina_max=150.0)))
    out.append(_form('water: 長流 +5 熟練, stage 3, 大師 4, 長河 2, recovery x2, two allies',
                     dict(form=WATER, magicka=100.0, magicka_max=250.0, health_max=300.0, stamina_max=200.0),
                     levels={'water': 40}, tuning=dict(sync=3, recovery=2.0),
                     ranks={('water', '長流每秒回復'): 5, ('water', '同調每段長流回復'): 4, ('water', '長河'): 2},
                     allies=[[1, 180.0, 90.0], [2, 400.0, 250.0]]))
    out.append(_form('water: 長河 at stage 2 gives the allies nothing', dict(form=WATER, magicka=100.0, magicka_max=200.0),
                     tuning=dict(sync=2), ranks={('water', '長河'): 3}, allies=[[1, 180.0, 90.0]]))
    out.append(_form('water: empty after the fee -> the clock starts, the 80% still comes back',
                     dict(form=WATER, magicka=1.0, magicka_max=200.0)))
    out.append(_form('storm: lightning in a storm, charge 2 -> 3, cooldown 3 s x1.5',
                     dict(form=LIGHTNING, thunder=True), me={'Charge': [2.0, 1.0, 10.0]}, tuning=dict(cooldown=1.5)))
    out.append(_form('storm: at the cap the charge stays 6', dict(form=LIGHTNING, thunder=True), me={'Charge': [6.0, 1.0, 10.0]}))
    out.append(_form('storm: the 3 s clock still runs -> no charge', dict(form=LIGHTNING, thunder=True),
                     me={'Charge': [2.0, 1.0, 10.0], 'StormCooldown': [1.0, 1.0, 3.0]}))
    out.append(_form('storm: no storm, no charge', dict(form=LIGHTNING, thunder=False), me={'Charge': [2.0, 1.0, 10.0]}))
    out.append(_form('storm: a storm in the fire form gives no charge', dict(form=FIRE, thunder=True)))
    # ---- the environment
    # (lightning, wind) are Skyrim.esm WTHR DATA values: SkyrimOvercastRain 255/25, SkyrimStormRain 246/50,
    # SkyrimOvercastSnow 255/76, SkyrimStormSnow 203/178, SkyrimClear 255/25.
    for name, weather, lightning, wind, interior, swim, under, hour in [
            ('rain outdoors at noon', 2, 255, 25, False, False, False, 12.0),
            ('snow outdoors at 21:00', 3, 255, 76, False, False, False, 21.0),
            ('rain indoors', 2, 255, 25, True, False, False, 12.0),
            ('swimming indoors at 05:59', 0, 255, 25, True, True, False, 5.99),
            ('under water, clear sky, 06:00', 0, 255, 25, False, False, True, 6.0),
            ('cloudy, 20:00', 1, 255, 38, False, False, False, 20.0),
            ('no weather at all, 19:59', -1, 255, 0, False, False, False, 19.99),
            ('thunderstorm (SkyrimStormRain) outdoors', 2, 246, 50, False, False, False, 12.0),
            ('thunderstorm indoors', 2, 246, 50, True, False, False, 12.0),
            ('blizzard (SkyrimStormSnow): lightning frequency but snow, no thunder', 3, 203, 178, False, False, False, 12.0),
            ('snow at wind 127: not a blizzard', 3, 255, 127, False, False, False, 12.0),
            ('snow at wind 128: a blizzard', 3, 255, 128, False, False, False, 12.0),
            ('blizzard indoors', 3, 203, 178, True, False, False, 12.0),
            ('rain at lightning 254: thunder', 2, 254, 0, False, False, False, 12.0),
            ('clear at lightning 0 (DefaultWeather): no thunder without rain', 0, 0, 0, False, False, False, 12.0)]:
        out.append(dict(group='env', name='env: ' + name,
                        facts=dict(weather=weather, lightning=lightning, wind=wind, interior=interior, swimming=swim,
                                   underwater=under, hour=hour)))
    for flags in (0x00, 0x01, 0x02, 0x04, 0x08, 0x06, 0x0C, 0x10):
        out.append(dict(group='weather', name=f'weather flags {flags:#04x}', flags=flags))
    # ---- the domains
    sites = [[FIRE, 0.0, 0.0, 0.0], [FROST, 500.0, 0.0, 0.0], [FIRE, 150.0, 0.0, 0.0], [LIGHTNING, 0.0, 0.0, 0.0], [WATER, 0.0, 209.0, 0.0]]
    for at in ([0.0, 0.0, 0.0], [210.0, 0.0, 0.0], [360.0, 0.0, 0.0], [500.0, 210.5, 0.0], [0.0, 100.0, 0.0]):
        out.append(dict(group='inside', name=f'inside at {at}', sites=sites, at=at))
    out.append(dict(group='domainSelf', name='you in 火域, white-hot, just walked in: fuse +5 s', inside=[FIRE],
                    me={'Heat3': [3.0, 2.0, 8.0]}))
    out.append(dict(group='domainSelf', name='you still in 火域: no second +5 s', inside=[FIRE],
                    me={'Heat3': [3.0, 3.0, 13.0], 'FireDomainPlayer': [1.0, 1.0, 2.0]}))
    out.append(dict(group='domainSelf', name='火域 while not white-hot: the window only', inside=[FIRE]))
    out.append(dict(group='domainSelf', name='冰原 + 血池 + 聖域 + 潮池 at recovery x1.5', inside=[FROST, BLOOD, DIVINE, WATER],
                    tuning=dict(recovery=1.5)))
    out.append(dict(group='domainSelf', name='no domain: nothing', inside=[]))
    out.append(dict(group='domainEnemy', name='enemy in 冰原 with the slow cap at 30', inside=[FROST], tuning=dict(slow_cap=30.0)))
    out.append(dict(group='domainEnemy', name='enemy in 冰原 (cap 70)', inside=[FROST]))
    out.append(dict(group='domainEnemy', name='enemy in 地裂 at 0 stamina', inside=[EARTH], body=dict(stamina=0.0)))
    out.append(dict(group='domainEnemy', name='enemy in 地裂 with stamina left', inside=[EARTH], body=dict(stamina=30.0)))
    out.append(dict(group='domainEnemy', name='enemy in 毒霧 with 2 doses, 5 s left', inside=[POISON], poison='doses:2:5'))
    out.append(dict(group='domainEnemy', name='enemy in 毒霧 without poison: opens at 1 dose, 12 s', inside=[POISON]))
    out.append(dict(group='domainEnemy', name='enemy in 毒霧 at the 10-dose cap, 14 s left', inside=[POISON], poison='doses:10:14'))
    out.append(dict(group='domainEnemy', name='enemy in 潮池, 淨潮 owned', inside=[WATER], refund=True, branches=[('water', '淨潮')]))
    out.append(dict(group='domainEnemy', name='enemy in 死域 at night outdoors, star-locked, dot x1.5', inside=[DARKNESS],
                    tuning=dict(night=True, dot=1.5), target={'StarLock': [1.0, 0.0, 3.0]}))
    out.append(dict(group='domainEnemy', name='enemy in 死域 by day, dark tree 40', inside=[DARKNESS], levels={'darkness': 40}))
    out.append(dict(group='domainEnemy', name='enemy in all nine', inside=list(DOMAIN_ELEMENTS), body=dict(stamina=0.0),
                    poison='doses:3:9'))
    for element, seconds, mult in ((FIRE, 5.0, 1.0), (DIVINE, 8.0, 3.0), (ASTRAL, 5.0, 0.25), (FROST, 5.0, 2.3), (LIGHTNING, 5.0, 1.0),
                                   (WIND, 5.0, 1.0), (EARTH, 0.0, 1.0), (POISON, 5.0, 10.0)):
        out.append(dict(group='spawn', name=f'spawn element {element} {seconds} s x{mult}', element=element, seconds=seconds, mult=mult))
    # ---- slows
    for name, v in [('a timed frost slow (peak value, SpeedMult, detrimental)', dict(archetype=34, primary=30, secondary=-1, detrimental=True, duration=3.0)),
                    ('a dual value modifier slowing through its second value', dict(archetype=5, primary=24, secondary=30, detrimental=True, duration=1.0)),
                    ('your wind speed ability (not detrimental)', dict(archetype=34, primary=30, secondary=-1, detrimental=False, duration=5.0)),
                    ('a constant slow (an ability, duration 0)', dict(archetype=0, primary=30, secondary=-1, detrimental=True, duration=0.0)),
                    ('frost damage on health only', dict(archetype=0, primary=24, secondary=-1, detrimental=True, duration=1.0)),
                    ('a script effect', dict(archetype=1, primary=30, secondary=-1, detrimental=True, duration=5.0))]:
        out.append(dict(group='slow', name='slow: ' + name, view=v))
    for name, spec in [('in 冰原', dict(me={'FrostDomainPlayer': [1.0, 0.5, 2.0]})),
                       ('定神 at stage 3', dict(branches=[('common', '定神')], tuning=dict(sync=3))),
                       ('定神 at stage 2', dict(branches=[('common', '定神')], tuning=dict(sync=2))),
                       ('御風 at stage 3', dict(branches=[('wind', '御風')], tuning=dict(sync=3))),
                       ('nothing', dict())]:
        out.append(dict(group='immune', name='immune: ' + name, **spec))
    # ---- hotkeys
    for device, ident in ((0, 79), (0, 300), (1, 1), (1, 12), (2, 0x1000), (2, 0x0001), (2, 0x8000), (2, 0x9), (2, 0xA), (2, 0x0400), (3, 5)):
        out.append(dict(group='keycode', name=f'key device {device} id {ident:#x}', device=device, id=ident))
    keys = [79, 80, 81, 75, 76, 77, 71, 72, 73, 82, 83]
    for code, enabled, k in ((79, True, keys), (83, True, keys), (84, True, keys), (79, False, keys), (0, True, [0] * 11),
                             (276, True, [276] + keys[1:]), (80, True, [80, 80] + keys[2:])):
        out.append(dict(group='hotkey', name=f'hotkey {code} enabled={enabled}', code=code, enabled=enabled, keys=k))
    for name, g in [('in game', {}), ('paused', dict(paused=True)), ('a menu', dict(menu=True)), ('the console', dict(console=True)),
                    ('a text box', dict(text=True)), ('loading', dict(loading=True))]:
        gate = dict(paused=False, menu=False, console=False, text=False, loading=False)
        gate.update(g)
        out.append(dict(group='gate', name='gate: ' + name, gate=gate))
    base = dict(enabled=True, dead=False, active=False, current=0, magicka=50.0, magicka_max=100.0, free_pass=False, free_open=False)
    for name, change, wanted in [('open fire with 50% magicka', {}, FIRE),
                                 ('open fire with 9% magicka: refused', dict(magicka=9.0), FIRE),
                                 ('open fire with exactly 10%', dict(magicka=10.0), FIRE),
                                 ('open blood with 0 magicka (blood needs none)', dict(magicka=0.0), BLOOD),
                                 ('open with 0 magicka and 順轉', dict(magicka=0.0, free_pass=True), WATER),
                                 ('open with 0 magicka and 免門檻', dict(magicka=0.0, free_open=True), ASTRAL),
                                 ('the same form again closes it', dict(active=True, current=FROST), FROST),
                                 ('switch with 0 magicka (a switch needs none)', dict(active=True, current=FIRE, magicka=0.0), DARKNESS),
                                 ('dead: nothing', dict(dead=True), FIRE),
                                 ('switched off: nothing', dict(enabled=False), FIRE),
                                 ('not a form: nothing', {}, 12)]:
        f = dict(base)
        f.update(change)
        out.append(dict(group='switch', name='switch: ' + name, facts=f, wanted=wanted))
    return out


def _board_rows(board):
    return {k: [s.magnitude, s.remaining()] for k, s in sorted(board.kinds.items())}


def evaluate(damage, spec):
    g = spec['group']
    if g == 'cadence':
        return dict(beats=cadence(spec['steps']))
    if g == 'env':
        return environment(spec['facts'])
    if g == 'weather':
        return dict(cls=weather_class(spec['flags']))
    if g == 'inside':
        return dict(elements=inside(spec['sites'], spec['at']))
    if g == 'spawn':
        return dict(seconds=spawn_seconds(spec['element'], spec['seconds'], spec['mult']))
    if g == 'slow':
        return dict(slow=is_slow(spec['view']))
    if g == 'keycode':
        return dict(code=key_code(spec['device'], spec['id']))
    if g == 'hotkey':
        return dict(element=hotkey(spec['code'], spec['enabled'], spec['keys']))
    if g == 'gate':
        return dict(open=gate_open(spec['gate']))
    if g == 'switch':
        return dict(plan=plan_switch(spec['facts'], spec['wanted']))
    w = World25(damage, dict(spec, ranks=dict(spec.get('ranks', {})), branches=set(spec.get('branches', ())),
                             me=spec.get('me', {}), target=spec.get('target', {}), **_poison(damage, spec)))
    if g == 'immune':
        return dict(immune=slow_immune(w))
    if g == 'form':
        out = form_second(w, spec['facts'], spec.get('allies', []))
    elif g == 'domainSelf':
        out = domain_self(w, set(spec['inside']))
    elif g == 'domainEnemy':
        refund = 2.0 * w.bmax(WATER) if spec.get('refund') else 0.0
        domain_enemy(w, set(spec['inside']), refund)
        out = {}
    else:
        raise ValueError(g)
    return dict(ops=w.ops, out=out, me=_board_rows(w.me),
                poison=[w.target.poison.magnitude, w.target.poison.remaining()] if w.target.poison else None)


def _poison(damage, spec):
    """'doses:n:seconds' -> the poison DoT slot with n base doses (the per-dose strength of a tree-1 world)."""
    text = spec.get('poison')
    if not text:
        return {}
    _tag, n, seconds = text.split(':')
    probe = World25.__new__(World25)
    _n3.World.__init__(probe, damage, level=spec.get('levels', {}))
    return {'poison': [float(n) * probe.per_dose(), 0.0, float(seconds)]}


def fixture_row(damage, spec):
    """The table row: the inputs as the C++ test reads them (poison expanded) and what the model says."""
    row = {k: v for k, v in spec.items() if k not in ('ranks', 'branches', 'poison')}
    row.update(_poison(damage, spec))
    return row


# ================================================================ hand anchors
# Each: scenario name -> what the arithmetic says (ops rows / outputs), written out here by hand.
HAND = {
    # 200 × 1.0% × (1 − 0.7 × 1/100) = 2 × 0.993 = 1.986
    'upkeep: fire, tree 1, 200 magicka': dict(ops=[['spend', -1, 1.986]]),
    # 300 × 2.0% × (1 − 0.7 × 100/100) × 2 = 6 × 0.3 × 2 = 3.6
    'upkeep: darkness, tree 100, slider x2': dict(ops=[['spend', -1, 3.6]]),
    # level 150 → 100: 100 × 1% × 0.3 = 0.3
    'upkeep: tree 150 (clamped to 100)': dict(ops=[['spend', -1, 0.3]]),
    # fee 200 × 1% × 0.993 = 1.986 > 0.5 → spend 0.5, empty → the clock (1, 3600 s)
    'upkeep: no more than you have; empty -> the 2 s clock starts': dict(ops=[['spend', -1, 0.5], ['apply', 'ManaEmpty', -1, 1.0, 3600.0]]),
    'upkeep: empty 2 s -> the form closes': dict(ops=[['remove', 'ManaEmpty', -1], ['event', -1, 'Close']]),
    # 70 / 100 → 0.6% of the same maximum 100 = 0.6 (審查修正: not of the current maximum 120)
    'blood: 70% health pays 0.6% of max (no magicka, no close)': dict(ops=[['remove', 'ManaEmpty', -1], ['pay', -1, 0.6]]),
    # 200 × 1.0% × 1.5 = 3.0
    'blood: full health 1.0%, slider x1.5': dict(ops=[['pay', -1, 3.0]]),
    # 50%: 0.2 + (0.5 − 0.3) × 1 = 0.4% of 100 = 0.4
    'blood: 50% health 0.4%': dict(ops=[['pay', -1, 0.4]]),
    # fee 250 × 1% × (1 − 0.28) = 1.8; 長流 (2 + 0.2 × 5)% + 0.0005 × 4 × 3 + 0.0005 × 2 = 0.03 + 0.006 + 0.001 = 0.037
    # heal 300 × 0.037 × 2 = 22.2, stamina 200 × 0.037 × 2 = 14.8, magicka 1.8 × 0.8 = 1.44; ally 1: 180 × 0.037 × 2 = 13.32
    'water: 長流 +5 熟練, stage 3, 大師 4, 長河 2, recovery x2, two allies':
        dict(ops=[['spend', -1, 1.8], ['heal', -1, 22.2], ['stamina', -1, 14.8], ['magicka', -1, 1.44], ['healTarget', 1, 13.32],
                  ['staminaTarget', 1, 6.66], ['healTarget', 2, 29.6], ['staminaTarget', 2, 18.5]]),
    # charge 2 → 3 for 10 s; the storm clock 3 × 1.5 = 4.5 s
    'storm: lightning in a storm, charge 2 -> 3, cooldown 3 s x1.5':
        dict(ops=[['apply', 'Charge', -1, 3.0, 10.0], ['apply', 'StormCooldown', -1, 1.0, 4.5]]),
    # fuse 8 − 2 = 6 left, + 5 = 11
    'you in 火域, white-hot, just walked in: fuse +5 s':
        dict(ops=[['apply', 'Heat3', -1, 3.0, 11.0], ['apply', 'FireDomainPlayer', -1, 1.0, 2.0]]),
    # 20 × 1.5, 25 × 1.5, 20 × 1.5, 15 × 1.5
    '冰原 + 血池 + 聖域 + 潮池 at recovery x1.5':
        dict(ops=[['apply', 'FrostDomainPlayer', -1, 1.0, 2.0], ['heal', -1, 30.0], ['heal', -1, 37.5], ['magicka', -1, 30.0],
                  ['heal', -1, 22.5], ['stamina', -1, 22.5], ['event', -1, 'Cleanse', 0.0]]),
    'enemy in 冰原 with the slow cap at 30': dict(ops=[['slow', 0, 30.0, 2.0]]),
    'enemy in 地裂 at 0 stamina': dict(ops=[['event', 0, 'Knock', 2.0]]),
}


def check_hand(name, expect):
    want = HAND.get(name)
    if want is None:
        return 0
    near = lambda a, b: abs(a - b) <= 2e-4 * max(1.0, abs(b))
    same = lambda r, w: len(r) == len(w) and all((a == b) if isinstance(b, str) or isinstance(a, str) else near(a, b) for a, b in zip(r, w))
    for row in want['ops']:
        assert any(same(r, row) for r in expect['ops']), ('HAND', name, row, expect['ops'])
    return 1
