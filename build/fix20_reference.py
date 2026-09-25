"""Round 20 (N2) reference model of the hit-time magnitude, written from 元素魔戰士規劃-v0.4.md.

This is the oracle the native tests compare the DLL planner against (build/fix20-magnitude-table.json)
and the Papyrus difference patch's mirror is checked against (build/fix20_verify.py). It is written
independently of native/include/HitMath.h: plain Python, the design's own wording in the comments, and
the decisions recorded in .codex/impl-fix-round20.html (D1-D21).

Sources in v0.4: 1.1 (blood curves), 2.1 (B ranges, lightning best-of-N, crit, drain 50%), 2.7 (D_hit),
2.8 (no-form baseline true damage), 2.10 (environment), 3 (percentage main lines x NodeScale), 5.1 (siphon,
small dispel, dispel, silence, nodes), 5.2 (common tree), 5.3-5.13 (element skeleton, blood, divine, earth,
wind, water nodes).
"""
from dataclasses import dataclass, field

ELEMENTS = ['Fire', 'Frost', 'Lightning', 'Earth', 'Wind', 'Blood', 'Divine', 'Poison', 'Water', 'Darkness', 'Astral']
FIRE, FROST, LIGHTNING, EARTH, WIND, BLOOD, DIVINE, POISON, WATER, DARKNESS, ASTRAL = range(1, 12)
NOFORM_TREE, COMMON_TREE = 11, 12

# Node slots the N2 formulas read: (tree, route, tier) for main lines, (tree, route, tier, index) for branches.
# fix19_native.NODE_TABLE checks each slot against the ESP's node table (name / main-line text).
NODES = {
    'kEarthStaminaCut': (3, 0, 2),
    'kEarthDrainStrength': (3, 0, 2, 0),
    'kWindTailwind': (4, 0, 1, 1),
    'kBloodOverflow': (5, 0, 1, 1),
    'kBloodLeechRatio': (5, 0, 2),
    'kBloodReverse': (5, 0, 2, 0),
    'kBloodRage': (5, 0, 3, 1),
    'kDivineExorcism': (6, 0, 0, 1),
    'kWaterClearStream': (8, 0, 0, 0),
    'kWaterSoakSlow': (8, 1, 0),
    'kCommonStage2': (12, 0, 1),
    'kCommonStage3Power': (12, 0, 3),
    'kCommonAll1': (12, 1, 0),
    'kCommonAll2': (12, 1, 3),
    'kCommonEcho': (12, 2, 0, 0),
    'kCommonEchoRatio': (12, 2, 2),
    'kNoFormSeize': (11, 1, 0, 0),
    'kNoFormSilence': (11, 1, 2),
    'kNoFormDepletion': (11, 1, 2, 0),
    'kNoFormStillness': (11, 1, 2, 1),
    'kNoFormBurnCasters': (11, 1, 3),
    'kNoFormLowMagicka': (11, 1, 4),
    'kNoFormDevour': (11, 1, 4, 1),
}


def adept(element):
    """5.x sustain adept main line 'X proc +1%/point'; water's slot is a recovery line."""
    return None if element == WATER else (element - 1, 0, 1)


def master(element):
    """5.x sustain master main line '+1%/point per sync stage'; not for water."""
    return None if element == WATER else (element - 1, 0, 3)


@dataclass
class State:
    """One hit's inputs. ranks / branches are sparse: missing slot = 0 / not owned."""
    element: int = FIRE            # 0 = no form
    power: bool = False
    sneak: bool = False            # sneak-attack flag
    left: bool = False
    ranks: dict = field(default_factory=dict)
    branches: set = field(default_factory=set)
    level: dict = field(default_factory=dict)   # tree -> ESSB_Lvl value (missing = 1)
    stage: int = 0
    base_damage_mult: float = 1.0
    node_scale: float = 3.0
    mult_drain: float = 1.0
    mult_recovery: float = 1.0
    mult_duration: float = 1.0
    slow_cap: float = 70.0
    wet_slow: float = 15.0
    water_clear: float = 30.0
    seize_pct: float = 10.0
    wet: bool = False
    night: bool = False
    interior: bool = False
    prev: int = 0
    twin: int = 0
    echo_pending: bool = False
    twin_window: bool = False
    hp: float = 100.0
    hp_perm: float = 100.0
    hp_max: float = 100.0
    mp: float = 100.0
    mp_max: float = 100.0
    guard: float = 0.0
    undead: bool = False
    necro: bool = False
    blood_mark: bool = False
    silenced: bool = False
    spell_user: bool = False
    vip: bool = False
    t_mp: float = 0.0
    t_mp_max: float = 0.0


DAMAGE = None  # filled by load(settings)
NOFORM_BASE = 5.0


def load(settings):
    global DAMAGE, NOFORM_BASE
    DAMAGE = {i + 1: tuple(settings['element_damage'][name]) for i, name in enumerate(ELEMENTS)}
    NOFORM_BASE = settings['noform_base_true']


def rank(s, slot):
    if slot is None:
        return 0
    return s.ranks.get(slot, 0)


def has(s, slot):
    return slot in s.branches


def g_of(s, tree):
    """2.7: G(L) = 1 + 0.05 L, L = tree level (at least 1)."""
    return 1 + 0.05 * max(1, s.level.get(tree, 1))


def pct(s, points, base):
    """3: a percentage damage main line counts base x NodeScale per point."""
    return points * base * s.node_scale


def lerp(x, table):
    """1.1: linear between 100 / 70 / 30 / 10 %, flat beyond the ends."""
    xs = [p for p, _ in table]
    if x >= xs[0]:
        return table[0][1]
    if x <= xs[-1]:
        return table[-1][1]
    for (x1, y1), (x0, y0) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    raise AssertionError(x)


HIT_CURVE = [(1.0, 1.3), (0.7, 1.1), (0.3, 0.8), (0.1, 0.6)]
LEECH_CURVE = [(1.0, 0.05), (0.7, 0.15), (0.3, 0.35), (0.1, 0.50)]


def health_fraction(s):
    return s.hp / s.hp_perm if s.hp_perm > 0 else 1.0


def curve_fraction(s):
    x = min(1.0, max(0.0, health_fraction(s)))
    return 1 - x if has(s, NODES['kBloodReverse']) else x   # 5.8 逆流


def rage(s):
    return has(s, NODES['kBloodRage']) and 0.3 <= health_fraction(s) <= 0.7   # 5.8 血怒


def node_sum(s, element):
    """1 + the node percentages of M_mod (v0.4 3: percentage main lines count base x NodeScale per point)."""
    total = 1.0
    total += pct(s, rank(s, adept(element)), 0.01)
    total += pct(s, rank(s, master(element)), 0.01) * s.stage
    total += pct(s, rank(s, NODES['kCommonAll1']), 0.01) + pct(s, rank(s, NODES['kCommonAll2']), 0.01)
    if s.stage >= 2:
        total += pct(s, rank(s, NODES['kCommonStage2']), 0.01)
    if s.stage >= 3 and s.power:
        total += pct(s, rank(s, NODES['kCommonStage3Power']), 0.02)
    return total


def factor(s, element):
    """The categorical multipliers of M_mod (each x1 when it does not apply)."""
    factor = 1.0
    if element == BLOOD:
        factor *= lerp(curve_fraction(s), HIT_CURVE) * (1.15 if rage(s) else 1.0)
    if not s.interior:                       # 2.10: no environment bonus indoors
        if element == DARKNESS and s.night:
            factor *= 1.2
        if element == DIVINE and not s.night:
            factor *= 1.2
    if element == DIVINE and s.undead:       # 5.9: x1.5 against undead and daedra
        factor *= 1.5
    if element == DIVINE and s.necro and has(s, NODES['kDivineExorcism']):   # 驅魔 +50%
        factor *= 1.5
    if element == WIND and s.sneak:          # 1.1: wind sneak attack x3
        factor *= 3.0
    return factor


def modifier(s, element):
    """M_mod: 1 + node percentages (added), times the categorical multipliers (2.7 'all bonuses summed, applied once')."""
    return node_sum(s, element) * factor(s, element)


def proc(s, element, draws):
    """One D_hit. draws is the list of scripted random outcomes, consumed in order:
    ('real', lo, hi, u) for B of non-lightning, ('int', 1, 25, value) for lightning, ('chance', p, bool) for the crit."""
    if element == LIGHTNING:
        kind, lo, hi, value = draws.pop(0)
        assert (kind, lo, hi) == ('int',) + DAMAGE[LIGHTNING]
        b = value                            # D1: integer face of 1..25, best of N = 1 (charges are N4)
    else:
        kind, lo, hi, u = draws.pop(0)
        assert (kind, lo, hi) == ('real',) + DAMAGE[element]
        b = lo + (hi - lo) * u
    r = 1.5 if s.power else 1.0
    d = b * r * g_of(s, element - 1) * s.base_damage_mult * modifier(s, element)
    crit = False
    if element == LIGHTNING:
        kind, p, crit = draws.pop(0)
        assert kind == 'chance' and abs(p - 0.05) < 1e-9   # D3: 5% + 2% x charges(0)
        if crit:
            d *= 2.5 if s.power else 1.5     # D2: C = 1.5, 2.5 on a power attack
    return d, crit


def mean_unit(s, element):
    """The DLL's mean proc divided by (1 + node percentages), crit excluded: mean B x R x G x BDM x factors."""
    lo, hi = DAMAGE[element]
    b = (lo + hi) / 2                        # integer 1..25 and continuous ranges share the midpoint mean
    return b * (1.5 if s.power else 1.0) * g_of(s, element - 1) * s.base_damage_mult * factor(s, element)


def expected_mean_proc(s, element):
    """Mean of the DLL's element proc without the crit (what the Papyrus difference patch subtracts)."""
    return mean_unit(s, element) * node_sum(s, element)


def plan_element(s, draws):
    casts = []
    e = s.element
    d, crit = proc(s, e, draws)
    casts.append(('kProc', d, e, s.power, 0))
    if e == LIGHTNING:
        casts.append(('kDrainMagicka', d * 0.5 * s.mult_drain, 0, False, 0))   # 2.1: drain 50% of the damage
    if e == BLOOD and s.blood_mark:           # D4: blood mark = bleeding in N2
        ratio = lerp(curve_fraction(s), LEECH_CURVE) + 0.01 * rank(s, NODES['kBloodLeechRatio']) + (0.15 if rage(s) else 0)
        heal = d * ratio * s.mult_recovery    # D7: leech = proc x ratio
        missing = max(0.0, s.hp_max - s.hp)
        healed = min(heal, missing)
        if healed > 0:
            casts.append(('kHeal', healed, 0, False, 0))
        spill = heal - healed
        pool = min(s.guard, 0.2 * s.hp_max)   # clamped on read: max health may have dropped since it filled
        if spill > 0 and has(s, NODES['kBloodOverflow']):   # 5.8 血溢 -> 護血, cap 20% max health
            pool = min(pool + spill, 0.2 * s.hp_max)
        if pool > 0 and pool != s.guard:       # a full pool is not recast
            casts.append(('kBloodGuard', pool, 0, False, 0))
    if s.wet:                                 # 2.10: soaked slow for everyone in rain / snow / water
        slow = min(s.wet_slow + rank(s, NODES['kWaterSoakSlow']), max(0.0, min(s.slow_cap, 70.0)))
        casts.append(('kSoakSlow', slow, 0, False, 0))
    if e == EARTH:                            # D6: 3.0 x points x G(earth), half back with 汲力
        cut = 3.0 * rank(s, NODES['kEarthStaminaCut']) * g_of(s, EARTH - 1)
        if cut > 0:
            casts.append(('kDrainStamina', cut * s.mult_drain, 0, False, 0))
            if has(s, NODES['kEarthDrainStrength']):
                casts.append(('kRestoreStamina', cut * 0.5 * s.mult_recovery, 0, False, 0))
    if e == WIND and has(s, NODES['kWindTailwind']):
        casts.append(('kRestoreStamina', 25.0 * g_of(s, WIND - 1) * s.mult_recovery, 0, False, 0))
    if e == WATER and has(s, NODES['kWaterClearStream']):
        casts.append(('kRestoreStamina', s.water_clear * s.mult_recovery, 0, False, 0))
    if s.left and s.twin_window and 1 <= s.twin <= 11 and s.twin != e:   # 5.2 雙生
        dt, _ = proc(s, s.twin, draws)
        casts.append(('kProc', dt, s.twin, s.power, 0))
        if s.twin == LIGHTNING:
            casts.append(('kDrainMagicka', dt * 0.5 * s.mult_drain, 0, False, 0))
    consume = False
    if s.echo_pending and 1 <= s.prev <= 11 and s.prev != e:   # 5.2 餘響
        consume = True
        ratio = (0.5 if has(s, NODES['kCommonEcho']) else 0.0) + pct(s, rank(s, NODES['kCommonEchoRatio']), 0.03)
        if ratio > 0:
            dp, _ = proc(s, s.prev, draws)
            casts.append(('kProc', dp * ratio, s.prev, s.power, 0))
    return dict(casts=casts, consume_echo=consume, crit=crit, magnitude=d)


def plan_noform(s):
    """5.1 / 2.8. No random draws."""
    casts = []
    g = g_of(s, NOFORM_TREE)
    r = 1.5 if s.power else 1.0
    true_mult = 1.0
    if s.silenced and has(s, NODES['kNoFormStillness']):                  # 靜寂 x1.5
        true_mult *= 1.5
    if s.t_mp_max > 0 and s.t_mp < 0.25 * s.t_mp_max:                     # legend main line, pre-hit magicka (D13)
        true_mult *= 1 + pct(s, rank(s, NODES['kNoFormLowMagicka']), 0.03)
    total = 0.0
    baseline = NOFORM_BASE * g * s.base_damage_mult * r                  # 2.8: 5 x G x MCM mult, power x1.5
    casts.append(('kTrueDamage', baseline, 0, False, 0))
    total += baseline
    siphon = 10 * g * r                                                  # 吸魔 10 x G (power x1.5)
    if has(s, NODES['kNoFormSeize']):
        siphon = max(siphon, s.t_mp_max * s.seize_pct / 100)            # 奪魔
    siphon = min(siphon * s.mult_drain, max(0.0, s.t_mp))
    t_mp = max(0.0, s.t_mp)
    mp = max(0.0, s.mp)
    if siphon > 0:
        gain = siphon * s.mult_recovery
        casts.append(('kDrainMagicka', siphon, 0, False, 0))
        casts.append(('kRestoreMagicka', gain, 0, False, 0))
        t_mp -= siphon
        mp = min(s.mp_max, mp + gain)
    bonus = 1 + 0.05 * rank(s, NODES['kNoFormBurnCasters']) if s.spell_user else 1.0
    burned = 0.0
    dispel = False
    if mp > 0 and not s.power:                                           # 小滅法 (D12: your magicka after the siphon)
        burn = min(5 * g * bonus * s.mult_drain, t_mp)
        if burn > 0:
            dmg = burn * 1.0 * true_mult
            casts.append(('kDrainMagicka', burn, 0, False, 0))
            casts.append(('kTrueDamage', dmg, 0, False, 0))
            total += dmg
            burned = burn
    elif mp > 0 and s.power:                                             # 滅法
        x = min(0.15 * s.mp_max, mp)
        y = 0.0
        if t_mp <= 0 and has(s, NODES['kNoFormDepletion']):              # 枯竭: 2X of your own
            spend = min(2 * x, mp)
        else:
            spend = x
            y = min(t_mp, x * 1.0 * bonus * s.mult_drain)
        dmg = (spend + y) * 1.0 * true_mult
        casts.append(('kSpendMagicka', spend, 0, False, 0))
        if y > 0:
            casts.append(('kDrainMagicka', y, 0, False, 0))
        casts.append(('kTrueDamage', dmg, 0, False, 0))
        casts.append(('kDispelMark', 0.0, 0, False, 0))
        if t_mp - y <= 0:                                                # burned to 0: silence
            wanted = min(1 + 0.2 * rank(s, NODES['kNoFormSilence']), 4)
            sec = int(wanted + 0.5)
            if s.vip:
                sec = max(1, sec // 2)
            sec = min(8, max(1, int(sec * s.mult_duration + 0.5)))
            casts.append(('kSilence', 0.0, 0, False, sec))
        total += dmg
        burned = y
        dispel = True
    if has(s, NODES['kNoFormDevour']):                                   # 噬命: half the true damage heals you
        casts.append(('kHeal', total * 0.5 * s.mult_recovery, 0, False, 0))
    return dict(casts=casts, consume_echo=False, crit=False, magnitude=total, siphon=siphon, burned=burned, dispel=dispel)


def plan(s, draws):
    draws = list(draws)
    out = plan_element(s, draws) if 1 <= s.element <= 11 else plan_noform(s)
    assert not draws, ('unused draws', draws)
    return out
