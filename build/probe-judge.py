"""Round 26: judge build/probes-all.md from ElementsSpellblade.log (MCM 除錯等級 4「探針 log」).

    python -B build/probe-judge.py <ElementsSpellblade.log> [--json out.json] [--step B-07] [--quiet]

The user only acts; this reads the log. The log is split at the step markers "[ESSB][STEP] <station> ..." (numpad + /
numpad -, or `set ESSB_ProbeStep to N`); every station of build/probes-all.md lists the step IDs it covers (STATIONS below;
build/fix26_verify.py checks the two agree). A station marked more than once is judged on its LAST segment (a redo).

Each step prints one verdict with the evidence lines (their #sequence numbers):
  PASS      the log shows what the sheet expects
  FAIL      the log shows something else (the reason names the numbers)
  EYES      the log part is judged (see the reason) but a part only the screen shows remains -- the user answers it
  RECORD    a step that only records behaviour (no pass / fail in the sheet): the evidence is listed
  NO-DATA   the station is missing, or it has none of the lines the step needs

The line formats are build/fix26_format.py's (the same patterns native/tests/trace_test.cpp checks the DLL's writers
against). The expected numbers are the sheet's; where v0.4 gives a formula the reference models are used
(build/fix25_reference.py for the upkeep and the blood cost).
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import fix26_format as fmt  # noqa: E402

# ================================================================ the stations (probes-all.md, in the order they are run)
# (station, step IDs, short title). fix26_verify checks every one of the 102 step IDs is judged exactly once and that the
# sheet's station headers list the same IDs.
STATIONS = [
    (1, ['SETUP-1'], 'DLL 版本與執行緒（X1）'),
    (2, ['A-01'], '節點倍率滑桿範圍'),
    (3, ['A-02'], '13 棵樹的代表節點'),
    (4, ['A-03'], '退役節點'),
    (5, ['A-04'], '新 NPC 沒有殘留狀態'),
    (6, ['A-05'], '熱鍵與 Z 的開關、魔力門檻'),
    (7, ['A-06', 'E-10'], '選單裡按熱鍵'),
    (8, ['A-07'], '按住熱鍵、手把熱鍵'),
    (9, ['A-08'], '死亡／倒地／騎馬時按熱鍵（記錄）'),
    (10, ['A-09'], '維持費'),
    (11, ['A-10', 'E-09'], '暫停時計時器停住'),
    (12, ['A-11'], '魔力歸零 2 秒關形態'),
    (13, ['A-12'], '血形態扣血'),
    (14, ['A-13'], '水形態長流'),
    (15, ['A-14'], '等待／睡覺／快速旅行／對話'),
    (16, ['A-15'], '天氣與雷雨'),
    (17, ['A-16'], '雨中浸濕減速'),
    (18, ['A-18'], '浸濕時長四捨五入與 30 秒上限'),
    (19, ['B-01'], '無元素：吸魔、燒魔、滅法'),
    (20, ['B-02'], '無元素重擊不打到自己'),
    (21, ['B-03'], '吸魔量 +1 點'),
    (22, ['B-04'], '滅法倍率 +1 點'),
    (23, ['B-05'], '燒魔倍數'),
    (24, ['B-06', 'E-04'], '反咒與斷咒'),
    (25, ['B-07'], '火焰附傷強度'),
    (26, ['B-08'], '熱度階梯、白熱、過熱'),
    (27, ['B-10'], '冰封後重擊碎冰'),
    (28, ['B-11'], '冰甲與霜膚的寒氣'),
    (29, ['B-12'], '冰盾'),
    (30, ['B-13'], '電荷、雷的 N 與暴擊、滿格重擊放電'),
    (31, ['B-14', 'E-05'], '法術麻痺（滿格打斷詠唱）'),
    (32, ['B-15'], '反擊'),
    (33, ['B-16'], '岩甲、蓄勁、碎岩'),
    (34, ['B-17'], '地臨強化'),
    (35, ['B-18'], '疾風潛行 ×3'),
    (36, ['B-19'], '風勢與風刃'),
    (37, ['B-20'], '被切的印記多觸發'),
    (38, ['B-21'], '鮮血吸血'),
    (39, ['B-22'], '護血池'),
    (40, ['B-23'], '同調與升段'),
    (41, ['B-35', 'E-02'], '血痕層數'),
    (42, ['B-24'], '神聖日夜'),
    (43, ['B-25'], '神聖對亡靈、聖痕'),
    (44, ['B-26'], '聖佑階梯'),
    (45, ['B-27'], '聖佑減傷'),
    (46, ['B-28'], '中毒劑數'),
    (47, ['B-29'], '水臨強化'),
    (48, ['B-30', 'E-03'], '水壓沖刷'),
    (49, ['B-31'], '恐懼、瘋狂、幻視'),
    (50, ['B-36'], '幻影'),
    (51, ['B-32'], '星痕引爆'),
    (52, ['B-33'], '印記上身與過期'),
    (53, ['B-34'], '終焉後接管'),
    (54, ['B-37'], '關形態＝融斷'),
    (55, ['C-01', 'E-06'], '法盾'),
    (56, ['C-02'], '水幕'),
    (57, ['C-03'], '護血致死'),
    (58, ['C-04'], '化法為力→超載'),
    (59, ['C-05'], '十一項受擊反應與冷卻'),
    (60, ['C-06'], '灼身'),
    (61, ['C-07'], '持續傷不分擔'),
    (62, ['C-08'], 'TrueHUD 資源條'),
    (63, ['C-09'], '切換與 Z 清資源'),
    (64, ['D-01'], '融斷：火冰雷土'),
    (65, ['D-02'], '融斷：風血聖毒水暗星'),
    (66, ['D-03'], '冰封融斷'),
    (67, ['D-04'], '三段同調的聖、星'),
    (68, ['D-05'], '融斷距離'),
    (69, ['D-06'], '寂與萬寂'),
    (70, ['D-07'], '範圍不碰隨從路人'),
    (71, ['D-08'], '聖灰'),
    (72, ['D-09'], '亡者歸來'),
    (73, ['D-10'], '中毒死亡擴散'),
    (74, ['D-11'], '連鎖冰封、火葬、亡魂'),
    (75, ['D-12'], '不死、飲血、血承'),
    (76, ['D-13'], '焰起強化'),
    (77, ['D-14'], '印潮、雙斷、臨界'),
    (78, ['D-15', 'E-07'], '同時死亡與死亡事件'),
    (79, ['D-16'], '連殺、無魔'),
    (80, ['B-09'], '火浴'),
    (81, ['D-17', 'A-17'], '火域、冰原、減速上限'),
    (82, ['D-18'], '血池、聖域、神聖領域、潮池'),
    (83, ['D-19'], '聖域減敵人傷害'),
    (84, ['D-20', 'E-11'], '地裂、毒霧、死域、星域'),
    (85, ['D-21', 'E-12'], '領域不碰隨從、5 個同時'),
    (86, ['D-22'], '死域裡存讀檔'),
    (87, ['D-23'], '瘴氣'),
    (88, ['D-24'], '總開關'),
    (89, ['E-01'], '星痕引信的三種移除'),
    (90, ['E-08'], '雪漫城門口的掃描'),
    (91, ['E-13'], 'FPS'),
    (92, ['F-01'], '故障演練'),          # round 27h (review: verification)
    (93, ['F-02'], 'HDT-SMP 壓力站'),    # round 27h (the 0.27.5 freeze: an A/B around HDT-SMP)
]

ALL_IDS = (['SETUP-1'] + [f'A-{i:02d}' for i in range(1, 19)] + [f'B-{i:02d}' for i in range(1, 38)] +
           [f'C-{i:02d}' for i in range(1, 10)] + [f'D-{i:02d}' for i in range(1, 25)] + [f'E-{i:02d}' for i in range(1, 14)] +
           ['F-01', 'F-02'])   # round 27h
assert len(ALL_IDS) == 104

PLAYER_ID = 0x14
GAMEPAD_BASE = 266   # SKSE key codes: keyboard 0-255, mouse 256-265, gamepad from 266

# ================================================================ parsing

_ACTOR = re.compile(r' (\w+)=(?:-(?= |$)|([^()\[\]=]*)\((0x[0-9A-F]{8})\)\[h=(\S+?)/(\S+?) m=(\S+?)/(\S+?) s=(\S+?)/(\S+?)( dead)?\])')
_STEP = re.compile(fmt.STEP)
_KINDS = {k: re.compile(p) for k, p in fmt.table()['kinds'].items() if k != 'step'}
_HEAD = re.compile(r'^\[ESSB\]\[T\]\[([a-z-]+)\] #(\d+) g=(\d+) r=(\d+)(.*)$')


def num(text):
    try:
        v = float(text)
        return v
    except (TypeError, ValueError):
        return None


class Actor:
    __slots__ = ('name', 'id', 'h', 'hmax', 'm', 'mmax', 's', 'smax', 'dead')

    def __init__(self, m):
        self.name = (m.group(2) or '').strip()
        self.id = int(m.group(3), 16)
        self.h, self.hmax, self.m, self.mmax, self.s, self.smax = (num(m.group(i)) for i in range(4, 10))
        self.dead = bool(m.group(10))

    def __repr__(self):
        return f'{self.name}(0x{self.id:08X})'


class Line:
    """One line of the log: a T line (kind, seq, g, r, fields, actors), a step marker, or any other ESSB line (raw)."""
    __slots__ = ('n', 'text', 'kind', 'seq', 'g', 'r', 'f', 'a', 'ok', 'dm')

    def __init__(self, n, text):
        self.n = n
        self.text = text
        self.kind = 'raw'
        self.seq = self.g = self.r = None
        self.f = {}
        self.a = {}
        self.ok = True
        self.dm = 1.0   # ESSB_BaseDamageMult in force at this line (read_log sets it)

    def __getitem__(self, key):
        return self.f.get(key)

    def v(self, key, default=None):
        x = self.f.get(key)
        y = num(x)
        return default if y is None else y

    def d(self, key, default=None):
        """A damage number of this line at 傷害倍率 1.0: the logged value divided by the ESSB_BaseDamageMult in force
        (round 27g: the build default is 0.8 and a save keeps its own; the sheet's numbers are the 1.0 ones)."""
        y = self.v(key)
        return default if y is None else y / self.dm

    def short(self):
        return self.text if len(self.text) <= 260 else self.text[:257] + '...'


def parse_line(n, text):
    line = Line(n, text)
    m = _STEP.match(text)
    if m:
        line.kind = 'step'
        line.f = {'station': m.group(1), 'via': m.group(5)}
        line.seq, line.g, line.r = int(m.group(2)), int(m.group(3)), int(m.group(4))
        return line
    m = _HEAD.match(text)
    if not m:
        return line
    line.kind = m.group(1)
    line.seq, line.g, line.r = int(m.group(2)), int(m.group(3)), int(m.group(4))
    pattern = _KINDS.get(line.kind)
    line.ok = bool(pattern and pattern.match(text))
    body = m.group(5)
    for am in _ACTOR.finditer(body):
        if am.group(3):
            line.a[am.group(1)] = Actor(am)
        else:
            line.a[am.group(1)] = None
    rest = _ACTOR.sub(' ', body)
    for token in rest.split():
        if '=' in token:
            k, _, v = token.partition('=')
            if k and k not in line.f:
                line.f[k] = v
    return line


DAMAGE_MULT_GLOBAL = 'ESSB_BaseDamageMult'


def read_log(path):
    raw = Path(path).read_bytes().decode('utf-8', errors='replace')
    lines = []
    for n, text in enumerate(raw.splitlines(), 1):
        if '[ESSB]' in text:
            lines.append(parse_line(n, text.rstrip()))
    mark_damage_mult(lines)
    return lines


def mark_damage_mult(lines):
    """Round 27g: every line carries the 傷害倍率 in force -- the session's mcm-state value, then each [mcm] change of
    it. Before the first mcm-state (no debug level 4 at load) it is unknown and taken as 1.0; DAMAGE_MULTS lists the
    values seen so the report can say which one the numbers were divided by."""
    current = 1.0
    for x in lines:
        if x.kind == 'mcm-state' and x.f.get(DAMAGE_MULT_GLOBAL) is not None:
            current = x.v(DAMAGE_MULT_GLOBAL, current)
        elif x.kind == 'mcm' and x.f.get('global') == DAMAGE_MULT_GLOBAL:
            current = x.v('new', current)
        if current <= 0:
            current = 1.0
        x.dm = current
        DAMAGE_MULTS.add(round(current, 3))


DAMAGE_MULTS = set()


def clock_drift(lines, limit_ms=1000):
    """Round 27h (review 1-1): death / settle / hit-late lines carry the world clock (the effects' elapsed) and the running
    clock (upkeep, the timer). Between two such lines both should advance alike; a gap over a second means the DLL
    compared an effect's time against the wrong clock somewhere (0.27.6: marks judged expired at a death). The pairs."""
    out, last = [], None
    for x in lines:
        w, r = x.v('world'), x.v('running')
        if w is None or r is None:
            continue
        if last is not None:
            dw, dr = w - last.v('world'), r - last.v('running')
            if abs(dw - dr) > limit_ms:
                out.append((last, x, dw, dr))
        last = x
    return out


class Seg(list):
    """The lines of one station (or the whole log)."""

    def of(self, kind, **where):
        out = []
        for x in self:
            if x.kind != kind:
                continue
            if all((x.f.get(k) == str(v)) if not callable(v) else v(x) for k, v in where.items()):
                out.append(x)
        return out

    def ops(self, op=None, kind=None, who=None, ctx=None, ev=None, el=None):
        out = []
        for x in self:
            if x.kind != 'op':
                continue
            if op and x['op'] != op:
                continue
            if kind and x['kind'] != kind:
                continue
            if who and x['who'] != who:
                continue
            if ctx and x['ctx'] != ctx:
                continue
            if ev and x['ev'] != ev:
                continue
            if el and x['el'] != el:
                continue
            out.append(x)
        return out

    def procs(self, **where):
        return self.of('proc', **where)

    def done_after(self, op_line):
        """The op-done line of an op (same actor, after the op)."""
        for x in self:
            if x.kind == 'op-done' and x['ref'] == f'#{op_line.seq}':
                return x
        return None


def split(lines):
    """station -> the lines of its LAST marking (to the next marker), plus how many times it was marked."""
    segs, marks = {}, defaultdict(int)
    current = None
    for x in lines:
        if x.kind == 'step':
            current = int(x.f['station'])
            marks[current] += 1
            segs[current] = Seg([x])
            continue
        if current is not None:
            segs[current].append(x)
    return segs, marks


# ================================================================ verdicts

class Verdict:
    def __init__(self, status, reason, evidence=()):
        self.status = status
        self.reason = reason
        self.evidence = [e for e in evidence if e is not None][:12]

    def json(self):
        return {'status': self.status, 'reason': self.reason, 'evidence': [f'#{e.seq} L{e.n}: {e.short()}' for e in self.evidence]}


def PASS(reason, *ev):
    return Verdict('PASS', reason, ev)


def FAIL(reason, *ev):
    return Verdict('FAIL', reason, ev)


def EYES(reason, *ev):
    return Verdict('EYES', reason, ev)


def RECORD(reason, *ev):
    return Verdict('RECORD', reason, ev)


def NODATA(reason, *ev):
    return Verdict('NO-DATA', reason, ev)


def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def rel(a, b, frac):
    return a is not None and b is not None and abs(a - b) <= frac * max(abs(b), 1e-6)


def fmt_nums(xs, n=2):
    return ', '.join(f'{x:.{n}f}' for x in xs)


def rolls_of(proc):
    """The proc's rolls: R(lo,hi)=v and I(lo,hi)=v draws."""
    text = proc.text.split(' rolls=', 1)[-1]
    out = []
    for m in re.finditer(r'([RIC])\(([^)]*)\)=(\S+)', text):
        out.append((m.group(1), [num(x) for x in m.group(2).split(',')], num(m.group(3))))
    return out


def steps_of(proc):
    """The hit plan's casts: {name: [magnitudes]} and seconds."""
    out = defaultdict(list)
    text = proc['steps'] or ''
    for part in text.split(','):
        m = re.match(r'(\w+):([-\d.]+)(?:/(\d+)s)?', part)
        if m:
            out[m.group(1)].append((float(m.group(2)), int(m.group(3)) if m.group(3) else 0))
    return out


def node_added(seg, perk):
    """The node watcher's line for a perk (local id hex, 6 digits) gained in this segment (or earlier: the whole log)."""
    for x in seg:
        if x.kind == 'node' and x['change'] == '+' and x['id'] == perk.upper():
            return x
    return None


def last_before(seg, line, kind, pred=lambda x: True):
    best = None
    for x in seg:
        if x.seq is not None and line.seq is not None and x.seq >= line.seq:
            break
        if x.kind == kind and pred(x):
            best = x
    return best


# ================================================================ the steps
# Every rule gets (seg, ctx): seg = its station's last segment (Seg), ctx = Ctx (the whole log and every station).

class Ctx:
    def __init__(self, lines):
        self.all = Seg(lines)
        self.segs, self.marks = split(lines)

    def station_of(self, step):
        for n, ids, _ in STATIONS:
            if step in ids:
                return n
        return None

    def seg(self, step):
        n = self.station_of(step)
        return self.segs.get(n, Seg())


RULES = {}


def rule(*ids):
    def wrap(fn):
        for i in ids:
            RULES[i] = fn
        return fn
    return wrap


def chain(seq, preds):
    """The lines of `seq` that match `preds` in this order (a subsequence), or None."""
    out = []
    k = 0
    for x in seq:
        if k < len(preds) and preds[k](x):
            out.append(x)
            k += 1
    return out if k == len(preds) else None


def by_target(procs):
    first = {}
    for p in procs:
        t = p.a.get('tgt')
        if t and t.id not in first:
            first[t.id] = p
    return first


# ---------------------------------------------------------------- SETUP

# Round 27c (0.27.2): since G8 (round 27) the hotkey switch, the close and the fusion run in the input task, so station 1's
# actions queue no ESSBNative task any more -- the input task is required instead ("queued native task" still counts
# when it appears; the menu's respec and the MCM close do queue one).
X1_PROBES = ['Papyrus native', 'input task', 'TESHitEvent', 'TESHitEvent (you are the target)', 'hurt task',
             'TESActiveEffectApplyRemoveEvent', 'TESDeathEvent', 'timer task', 'TESSpellCastEvent', 'input sink']
_X1 = re.compile(r'^\[ESSB\]\[X1\] (.+?) thread=(\d+) n=(\d+) input=(\d+) (\w+) task=(\d+) (\w+) window=(\d+) (\w+) dataLoaded=(\d+) paused=(\d)')


_X2 = re.compile(r'^\[ESSB\]\[X2\] (.+?) thread=(\d+) window=(\d+) (\w+) paused=(\d) havok=(\S+) keys=(\S+) frames=(\S*)$')
# The chain keys (native/include/Trace.h kChainKeys; build/fix26_verify.py checks the two agree).
CHAIN_KEYS = {0x640E67: 'post-process', 0x5B36AD: 'paused-tasks', 0x5C770C: 'hit-task', 0x7211EF: 'hit-frame', 0x63FCC9: 'ui-job',
              0x5B35BF: 'main-ui', 0x5B3F48: 'poll-controls', 0x5B33B5: 'paused-input', 0x640623: 'vm-job', 0x5B3381: 'paused-vm'}
X2_TASKS = {'timer task', 'queued native task', 'hurt task', 'settle task', 'death task', 'spell-cast task', 'input task', 'hit task'}
X2_HIT = {'TESHitEvent', 'TESHitEvent (you are the target)'}
# during gameplay: the context each probe must show (the commander's ruling, round 26b); a name not listed is only recorded
# Round 26c: the hit sinks no longer do engine work, so their context is only recorded (in this load order Precision / TDM
# send TESHitEvent on the window thread); every task -- the hit task included -- must be in Post process.
X2_WANT = {**{n: {'post-process'} for n in X2_TASKS},
           'input sink': {'poll-controls'}, 'input sink (every frame)': {'poll-controls'}, 'SKSE UI task': {'ui-job', 'main-ui'},
           'Papyrus native': {'vm-job'}}


def x2_verdicts(log):
    """(bad, eyes, rows) over every [ESSB][X2] line."""
    bad, eyes, rows = [], [], []
    for x in log:
        if x.kind != 'raw':
            continue
        m = _X2.match(x.text)
        if not m:
            continue
        name, paused, window_same, keys = m.group(1), m.group(5) == '1', m.group(4) == 'same', set(m.group(7).split(',')) - {'-'}
        rows.append((x, name, paused, keys))
        if paused:
            if not window_same and not any(k.startswith('paused') for k in keys):
                bad.append((x, f'{name}: 暫停時不在視窗執行緒、也沒有 paused 路徑'))
            continue
        want = X2_WANT.get(name)
        if want is None or keys & want:
            continue
        if keys:
            bad.append((x, f'{name}: 遊戲中是 {",".join(sorted(keys))}（應 {"／".join(sorted(want))}）'))
        else:
            eyes.append((x, f'{name}: 12 層內沒有認得的呼叫鏈'))
    return bad, eyes, rows


# The DLL version this sheet judges (round 28b: 0.28.1). build/fix26_verify.py and build/fix27_verify.py build their samples with it.
VERSION = '0.28.1'


@rule('SETUP-1')
def r_setup(seg, ctx):
    log = ctx.all
    version = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][load] ElementsSpellblade ')]
    button = [x for x in log.of('pap') if x['kind'] == 'mcm-button' and 'ShowNativeStatus' in x.text]
    if not version:
        return NODATA('log 裡沒有 [ESSB][load] ElementsSpellblade 版本行（不是這一版的 log？）')
    if f'ElementsSpellblade {VERSION}' not in version[0].text:
        return FAIL(f'DLL 版本不是 {VERSION}', version[0])
    # round 27 (E1): an effect list walked outside a task is a FAIL of its own (the removal / death sinks read the registry)
    overlap_read = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][OVERLAP-READ]')]
    if overlap_read:
        return FAIL('出現 [ESSB][OVERLAP-READ]：有人在 task 外走了效果清單（round 27 E1 規定永遠不能出現）', *overlap_read[:4])
    overlap = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][OVERLAP]')]
    if overlap:
        return FAIL('出現 [ESSB][OVERLAP]：兩個改引擎的工作同時在跑（round 26c 規定永遠不能出現）', *overlap[:4])
    # round 27 (E2): an exception the DLL did not swallow (not its own access violation) is logged before the game sees it
    # round 27c (0.27.2): an op with a non-finite or absurd value was dropped by the executor's guard
    badmag = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][BADMAG]')]
    if badmag:
        return FAIL('出現 [ESSB][BADMAG]：有操作的數值不是有限數或大得離譜（已丟掉沒套用，但算錯了）', *badmag[:4])
    crash = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][crash]')]
    if crash:
        return FAIL('出現 [ESSB][crash]：DLL 裡發生了不是自己存取違規的例外（已交還遊戲）', *crash[:2])
    rng = [x for x in log if x.kind == 'raw' and x.text.startswith('[ESSB][RNG]')]
    if rng:
        return FAIL('擲骰出現在 task 以外', *rng[:2])
    seen = defaultdict(list)
    for x in log:
        if x.kind == 'raw':
            m = _X1.match(x.text)
            if m:
                seen[m.group(1)].append((x, m))
    missing = [p for p in X1_PROBES if p not in seen]
    bad, eyes, rows = x2_verdicts(log)
    chains = '；'.join(f'{n}{"（暫停）" if p else ""}: {",".join(sorted(k)) or "?"}' for x, n, p, k in rows[:24])
    evidence = [version[0]] + ([button[-1]] if button else []) + [x for p in X1_PROBES for x, _ in seen.get(p, [])[:1]]
    if missing:
        return FAIL('X1 缺：' + '、'.join(missing), *evidence)
    x2_names = {n for x, n, p, k in rows}
    if 'hit task' not in x2_names or 'timer task' not in x2_names:
        return FAIL('X2 缺命中 task 或計時器 task 的呼叫鏈', *evidence)
    if bad:
        return FAIL('X2：' + '；'.join(r for x, r in bad[:4]), *[x for x, r in bad[:6]])
    ok_button = bool(button) and f'version={VERSION}' in button[-1].text and 'active=True' in button[-1].text
    if eyes or not ok_button:
        why = ('；'.join(r for x, r in eyes[:4]) + '；') if eyes else ''
        return EYES(why + (f'MCM 版本按鈕沒寫進 log 或不是 {VERSION}／True，請看畫面；' if not ok_button else '') + '呼叫鏈：' + chains,
                    *(evidence + [x for x, r in eyes[:3]]))
    return PASS(f'版本 {VERSION}；X1 十種都在；沒有 OVERLAP、OVERLAP-READ、crash、BADMAG；X2：遊戲中所有 task（含命中 task）在 Post process、輸入／UI／VM 在各自的 job、暫停時在視窗執行緒（命中 sink 只記錄）。'
                '呼叫鏈：' + chains, *(evidence + [x for x, n, p, k in rows[:4]]))


# ---------------------------------------------------------------- A

@rule('A-01')
def r_a01(seg, ctx):
    rows = [x for x in seg.of('mcm') if x['global'] == 'ESSB_NodeScale']
    if not rows:
        return NODATA('這一站沒有 ESSB_NodeScale 的變動（請把滑桿拉到最右、最左、再放回 3）')
    values = [x.v('new') for x in rows]
    hi, lo, last = max(values), min(values), values[-1]
    if hi > 5.0001 or lo < 0.9999:
        return FAIL(f'滑桿超出 1～5：最大 {hi}、最小 {lo}', *rows)
    if not (near(hi, 5.0, 1e-3) and near(lo, 1.0, 1e-3)):
        return FAIL(f'沒拉到兩端：最大 {hi}、最小 {lo}（範圍應是 1～5）', *rows)
    if not near(last, 3.0, 1e-3):
        return FAIL(f'最後沒放回 3（{last}）', *rows)
    return PASS('節點倍率滑桿最大 5、最小 1，已放回 3', *rows)


@rule('A-02')
def r_a02(seg, ctx):
    return EYES('技能樹畫面只能看：13 個代表節點都在、都是 v0.4 名稱（「洩壓」不在火焰樹上）')


@rule('A-03')
def r_a03(seg, ctx):
    x = node_added(seg, '002029') or node_added(ctx.all, '002029')
    if not x:
        return NODATA('沒看到 player.addperk XX002029 的節點行')
    if '退役' not in x.text:
        return FAIL('加上的 002029 名稱不是「洩壓（已退役）」', x)
    return EYES('log：002029＝「' + x.text.split('name=', 1)[-1] + '」已加上；火焰樹上看不到它、help 顯示已退役，要看畫面', x)


@rule('A-04')
def r_a04(seg, ctx):
    rows = [x for x in seg.of('pap') if x['kind'] == 'dump-nearest']
    if not rows:
        return NODATA('沒有「印出目標狀態」的 dump-nearest 行')
    x = rows[-1]
    if 'none=1' in x.text:
        return FAIL('30 公尺內沒有可打的目標（dump-nearest none=1）', x)
    codes = {k: x.f[k] for k in x.f if re.fullmatch(r's\d+', k)}
    nonzero = {k: v for k, v in codes.items() if v != '0'}
    if x['marks'] != '0' or nonzero:
        return FAIL(f'新 NPC 有殘留：marks={x["marks"]} ' + ' '.join(f'{k}={v}' for k, v in nonzero.items()), x)
    return PASS(f'{x.a.get("who")} 印記 0、s2～s19 全 0', x)


@rule('A-05')
def r_a05(seg, ctx):
    sw = seg.of('switch')
    want = [('hotkey', 'frost', 'open'), ('hotkey', 'frost', 'close'), ('hotkey', 'fire', 'refuse'), ('hotkey', 'blood', 'open'),
            ('hotkey', 'blood', 'close'), ('power', 'fire', 'refuse'), ('power', 'fire', 'open'), ('power', 'fire', 'close')]
    preds = [lambda x, w=w: (x['via'], x['wanted'], x['kind']) == w for w in want]
    if not sw:
        return NODATA('這一站沒有 switch 行')
    got = chain(sw, preds)
    if not got:
        seen = [(x['via'], x['wanted'], x['kind']) for x in sw]
        return FAIL('切換順序不對，實際：' + '；'.join('/'.join(s) for s in seen), *sw)
    for x in got:
        if x['kind'] == 'refuse':
            you = x.a.get('you')
            if you and you.m is not None and you.m >= x.v('gate', 0):
                return FAIL(f'魔力 {you.m} 不低於門檻 {x["gate"]} 卻被拒絕', x)
    return PASS('冰霜開→關、火焰魔力不足拒絕、鮮血照開→關、Z 魔力不足拒絕→補滿開→再按關，順序都對', *got)


@rule('A-06')
def r_a06(seg, ctx):
    keys = seg.of('key')
    blocked = [x for x in keys if x['verdict'] == 'blocked']
    if not keys:
        return NODATA('這一站沒有 key 行')
    flags = {k: any(x[k] == '1' for x in blocked) for k in ('console', 'menu', 'text', 'paused')}
    hot = [x for x in seg.of('switch') if x['via'] == 'hotkey']
    bad = [x for x in hot if last_before(seg, x, 'key') in blocked]
    if bad:
        return FAIL('選單裡按的熱鍵切換了形態', *bad)
    missing = [k for k in ('console', 'menu', 'text') if not flags[k]]
    if missing:
        return FAIL('少了這幾種被擋的情況：' + '、'.join(missing) + f'（blocked 共 {len(blocked)} 次）', *blocked)
    return PASS(f'主控台、背包／Esc（menu）、MCM 文字欄都被擋（blocked {len(blocked)} 次），沒有切換', *blocked)


@rule('E-10')
def r_e10(seg, ctx):
    keys = seg.of('key')
    ok = [x for x in keys if x['verdict'] == 'accepted']
    inputs = [x for x in ctx.all if x.kind == 'raw' and x.text.startswith('[ESSB][X1] input sink thread=')]
    if not ok:
        return NODATA('這一站沒有在遊戲畫面按下的熱鍵（accepted）')
    thread = inputs[0].text.split('thread=', 1)[1].split()[0] if inputs else None
    after = [x for x in seg.of('switch') if x['via'] == 'hotkey' and x.seq > ok[0].seq]
    if not after:
        return FAIL('accepted 之後沒有 switch via=hotkey', ok[0])
    if thread and any(x['thread'] != thread for x in ok):
        return FAIL(f'熱鍵的執行緒跟輸入 sink（{thread}）不同', *ok)
    blocked = [x for x in keys if x['verdict'] == 'blocked']
    bad = [x for x in blocked if not any(x[k] == '1' for k in ('paused', 'menu', 'console', 'text', 'loading'))]
    if bad:
        return FAIL('blocked 但五個旗標都是 0', *bad)
    return PASS(f'遊戲畫面 accepted（thread={ok[0]["thread"]}，與輸入 sink 相同）接著 switch via=hotkey；選單裡的都有擋下的理由',
                ok[0], after[0], *(inputs[:1]))


@rule('A-07')
def r_a07(seg, ctx):
    keys = seg.of('key')
    rebind = [x for x in seg.of('mcm') if x['global'] == 'ESSB_Hotkey_Fire']
    first_rebind = rebind[0].seq if rebind else 1 << 62
    kb_switch = [x for x in seg.of('switch') if x['via'] == 'hotkey' and x.seq < first_rebind]
    kb_keys = [x for x in keys if x['verdict'] == 'accepted' and x.seq < first_rebind]
    if not kb_keys:
        return NODATA('沒有按住數字鍵區 1 的 key 行')
    if len(kb_switch) != 1:
        return FAIL(f'按住三秒切換了 {len(kb_switch)} 次（應 1 次）', *kb_switch)
    if not rebind:
        return PASS('按住只切換一次；手把熱鍵未測（沒有改綁的 mcm 行）', kb_keys[0], kb_switch[0])
    pad = int(rebind[0].v('new', 0))
    pad_keys = [x for x in keys if x['code'] == str(pad) and x['verdict'] == 'accepted']
    pad_switch = [x for x in seg.of('switch') if x['via'] == 'hotkey' and x.seq > first_rebind]
    if pad < GAMEPAD_BASE:
        return EYES(f'改綁的代碼 {pad} 不是手把鍵；按住只切換一次（log 部分 OK）', rebind[0])
    if not pad_keys or not pad_switch:
        return FAIL(f'手把鍵 {pad} 沒有 accepted／沒有切換', rebind[0], *pad_keys)
    return PASS(f'按住只切換一次；手把鍵 {pad} 按一次切換一次', kb_switch[0], rebind[0], pad_keys[0], pad_switch[0])


@rule('A-08')
def r_a08(seg, ctx):
    rows = [x for x in seg if x.kind in ('key', 'switch')]
    if not rows:
        return NODATA('這一站沒有 key／switch 行')
    text = '；'.join(f'{x.kind}:{x["verdict"] or x["kind"]} dead={x["dead"] or "-"}' for x in rows[:12])
    return RECORD('只記錄（v0.4 沒寫死亡／倒地／騎馬該怎麼擋）：' + text, *rows)


def upkeep_ok(lines, element):
    import fix25_reference as ref
    got = [x for x in lines if x['form'] == element and x.v('spent') is not None and x.v('spent') > 0]
    if len(got) < 3:
        return None, got
    you = got[-1].a.get('you')
    expect = ref.upkeep(ref.DARKNESS if element == 'dark' else ref.FIRE, you.mmax, 1.0, 1.0)
    spent = statistics.median(x.v('spent') for x in got)
    return (rel(spent, expect, 0.2), spent, expect), got


@rule('A-09')
def r_a09(seg, ctx):
    sec = seg.of('second')
    res = []
    ev = []
    for element in ('fire', 'dark'):
        ok, got = upkeep_ok(sec, element)
        if ok is None:
            return NODATA(f'{element} 形態的 second 行不到 3 行')
        res.append((element, ok))
        ev += got[:2]
    bad = [f'{e}: 中位數 {s:.2f}／預期 {x:.2f}' for e, (ok, s, x) in res if not ok]
    text = '；'.join(f'{e} 每秒 {s:.2f}（預期 {x:.2f}）' for e, (ok, s, x) in res)
    regen = [x for x in sec if x['form'] in ('fire', 'dark') and x.v('dM') is not None and x.v('spent')]
    drift = [x for x in regen if x.v('dM') > -0.5 * x.v('spent')]
    note = '' if not drift else f'；注意：{len(drift)} 秒的 dM 比維持費少一半以上（自然回魔沒關？）'
    return (FAIL if bad else PASS)(text + ('；超過 20%：' + '、'.join(bad) if bad else '') + note, *ev)


def pauses(seg):
    """(stopped line, running line) pairs of the timer clock."""
    out = []
    stop = None
    for x in seg.of('tick'):
        if x['state'] == 'stopped':
            stop = x
        elif x['state'] == 'running' and stop is not None:
            out.append((stop, x))
            stop = None
    return out


@rule('A-10')
def r_a10(seg, ctx):
    pairs = pauses(seg)
    if not pairs:
        return NODATA('沒有 tick stopped／running（Esc 沒停住計時器？）')
    long = [(a, b) for a, b in pairs if b.r - a.r >= 20000]
    if not long:
        return FAIL('沒有停 20 秒以上的暫停', *[p for pair in pairs for p in pair])
    a, b = long[0]
    gained = int(b['active']) - int(a['active'])
    before = last_before(seg, a, 'second')
    after = next((x for x in seg.of('second') if x.seq > b.seq), None)
    lost = None
    if before and after and before.a.get('you') and after.a.get('you'):
        lost = before.a['you'].m - after.a['you'].m
    if gained > 1000:
        return FAIL(f'暫停 {(b.r - a.r) / 1000:.0f} 秒，遊戲時鐘卻走了 {gained} ms', a, b)
    if lost is not None and before.v('spent') is not None and lost > 2.0 * max(before.v('spent'), 1.0) + 1.0:
        return FAIL(f'暫停前後魔力少了 {lost:.1f}（超過兩秒份）', before, a, b, after)
    return PASS(f'暫停 {(b.r - a.r) / 1000:.0f} 秒，遊戲時鐘只走 {gained} ms；魔力前後差 '
                + ('-' if lost is None else f'{lost:.1f}'), a, b, before, after)


@rule('E-09')
def r_e09(seg, ctx):
    pairs = pauses(seg)
    if len(pairs) < 2:
        return NODATA(f'停住／恢復只有 {len(pairs)} 組（Esc、背包、Alt+Tab、存讀檔各一次）')
    bad = [(a, b) for a, b in pairs if int(b['active']) - int(a['active']) >= 1000]
    loads = [x for x in seg.of('trace') if 'game-ready' in x.text]
    after = [x for x in seg.of('second') if loads and x.seq > loads[-1].seq]
    if bad:
        return FAIL('有一次停住時 active 走了一秒以上', *[p for pair in bad for p in pair])
    if loads and not after:
        return FAIL('讀檔後沒有 second 行（計時器沒接上）', loads[-1])
    return PASS(f'{len(pairs)} 次停住都沒算進遊戲時鐘' + ('；讀檔後 second 照常' if loads else '；（這一站沒讀檔）'),
                *[p for pair in pairs[:3] for p in pair], *(after[:1]))


@rule('A-11')
def r_a11(seg, ctx):
    sec = seg.of('second')
    zero = next((x for x in sec if x.a.get('you') and x.a['you'].m <= 0.5 and x['form'] != 'none'), None)
    close = next((x for x in sec if x['close'] == '1'), None)
    pap = next((x for x in seg.of('pap') if x['kind'] == 'form-close' and 'magicka-empty' in x.text), None)
    if not zero:
        return NODATA('沒有魔力 0 的 second 行')
    if not close:
        return FAIL('魔力歸零後沒有 close=1', zero)
    dt = (close.g - zero.g) / 1000.0
    if not 1.0 <= dt <= 4.0:
        return FAIL(f'魔力歸零到關閉 {dt:.1f} 秒（應約 2～3 秒）', zero, close)
    if not pap:
        return FAIL('DLL 送了 close=1，Papyrus 沒有 form-close（魔力耗盡）', zero, close)
    return PASS(f'魔力歸零 {dt:.1f} 秒後關閉，Papyrus form-close reason=magicka-empty', zero, close, pap)


@rule('A-12')
def r_a12(seg, ctx):
    import fix25_reference as ref
    rows = [x for x in seg.of('second') if x['form'] == 'blood']
    if len(rows) < 3:
        return NODATA('血形態的 second 行不到 3 行')
    bad, seen = [], defaultdict(list)
    for x in rows:
        you = x.a.get('you')
        bled = x.v('bled', 0.0)
        before = you.h + bled
        f = before / you.hmax if you.hmax else 1.0
        expect = you.hmax * ref.blood_upkeep_pct(f) / 100.0
        band = 'full' if f >= 0.95 else '70%' if 0.62 <= f <= 0.72 else '10%' if f <= 0.12 else 'other'
        seen[band].append(bled)
        if not near(bled, expect, max(0.15 * expect, 0.3)):
            bad.append(x)
        if x.v('spent', 0.0) > 0.01:
            bad.append(x)
    text = '；'.join(f'{k}: {fmt_nums(v[:4])}' for k, v in seen.items())
    missing = [b for b in ('full', '70%', '10%') if not seen.get(b)]
    if bad:
        return FAIL('扣血跟 v0.4 血位表（1.1）對不上或扣了魔力：' + text, *bad[:6])
    if missing:
        return NODATA('每個血位都對，但缺這幾段：' + '、'.join(missing) + '（' + text + '）', *rows[:3])
    return PASS('血形態每秒扣血照血位表（滿血 1.0%、70% 0.6%、10% 不扣），魔力不扣：' + text, *rows[:4])


@rule('A-13')
def r_a13(seg, ctx):
    rows = [x for x in seg.of('second') if x['form'] == 'water' and x.v('dH') is not None]
    if len(rows) < 3:
        return NODATA('水形態的 second 行不到 3 行')
    you = rows[-1].a['you']
    hurt = [x for x in rows if x.a['you'].h < x.a['you'].hmax - 1]
    h_ok = [x for x in hurt if rel(x.v('dH'), you.hmax * 0.02, 0.25)]
    s_ok = [x for x in rows if x.a['you'].s < x.a['you'].smax - 1 and rel(x.v('dS'), you.smax * 0.02, 0.25)]
    m_bad = [x for x in rows if x.v('spent', 0) > 0 and not (-0.5 * x.v('spent') <= x.v('dM') <= 0.05)]
    river = seg.ops(op='HealTarget', ctx='form-second')
    if not hurt:
        return NODATA('生命一直是滿的（先 damageav health 500）', *rows[:2])
    notes = f'生命每秒 +{statistics.median(x.v("dH") for x in hurt):.1f}（預期 {you.hmax * 0.02:.1f}）'
    if len(h_ok) < max(1, len(hurt) // 2) or m_bad:
        return FAIL(notes + f'；魔力淨變化不在「-50%×維持費～0」的有 {len(m_bad)} 秒', *(m_bad[:4] or hurt[:4]))
    extra = f'；長河：同伴每秒回血 {len(river)} 次' if river else '；長河未測（沒有 HealTarget ctx=form-second）'
    return PASS(notes + f'；耐力回 {len(s_ok)} 秒符合 2%；魔力淨少約兩成維持費（長流回 80%）' + extra, *rows[:3], *(river[:1]))


@rule('A-14')
def r_a14(seg, ctx):
    menus = seg.of('menu')
    pairs = pauses(seg)
    if not pairs:
        return NODATA('沒有 tick stopped／running（等待、睡覺、快速旅行都會停住計時器）')
    rows = [(a, b, int(b['active']) - int(a['active'])) for a, b in pairs]
    dialog_open = [x for x in menus if 'Dialogue' in (x['name'] or '') and x['opening'] == '1']
    dialog_close = [x for x in menus if 'Dialogue' in (x['name'] or '') and x['opening'] == '0']
    bad = [(a, b) for a, b, g in rows if g > 1500]
    during = []
    if dialog_open and dialog_close:
        during = [x for x in seg.of('second') if dialog_open[0].seq < x.seq < dialog_close[-1].seq and x.v('spent', 0) > 0]
    if bad:
        return FAIL('有一次停住時遊戲時鐘走了 1.5 秒以上', *[p for pair in bad for p in pair])
    note = f'；對話中照扣 {len(during)} 秒' if dialog_open else '；（沒有對話選單的 menu 行）'
    return PASS(f'{len(pairs)} 次停住（等待／睡覺／快速旅行）遊戲時鐘都沒走' + note, *[p for a, b, g in rows[:3] for p in (a, b)], *during[:1])


WEATHER = {0x000C8220: 'storm-rain', 0x0000081A: 'clear', 0x000C821F: 'rain', 0x0004D7FB: 'snow', 0x000C8221: 'blizzard'}
WEATHER_FLAGS = {'storm-rain': ('1', '0', '1'), 'clear': ('0', '0', '0'), 'rain': ('1', '0', '0'), 'snow': ('1', '0', '0'),
                 'blizzard': ('1', '1', '0')}


@rule('A-15')
def r_a15(seg, ctx):
    env = seg.of('env')
    if not env:
        return NODATA('這一站沒有 env 行')
    bad, seen = [], defaultdict(list)
    for x in env:
        w = WEATHER.get(int(x['weather'], 16)) if x['weather'] else None
        if x['interior'] == '1':
            seen['interior'].append(x)
            if (x['wet'], x['stormy'], x['thunder']) != ('0', '0', '0') and x['swimming'] != '1':
                bad.append(x)
            continue
        if not w:
            continue
        seen[w].append(x)
        if (x['wet'], x['stormy'], x['thunder']) != WEATHER_FLAGS[w]:
            bad.append(x)
    storm_charges = [x for x in seg.of('second') if x['storm'] == '1']
    wrong_charge = []
    for x in storm_charges:
        e = last_before(seg, x, 'env')
        if e is None or e['thunder'] != '1':
            wrong_charge.append(x)
    missing = [w for w in ('storm-rain', 'interior', 'clear', 'rain', 'snow', 'blizzard') if not seen.get(w)]
    if bad or wrong_charge:
        return FAIL('天氣旗標不對或不是雷雨時加了電荷', *(bad[:6] + wrong_charge[:3]))
    if not storm_charges:
        return FAIL('雷雨時沒有加電荷（second storm=1）', *(seen.get('storm-rain', [])[:2]))
    gaps = [(b.g - a.g) / 1000 for a, b in zip(storm_charges, storm_charges[1:]) if b.g - a.g < 10000]
    note = f'；電荷間隔 {fmt_nums(gaps[:4], 1)} 秒' if gaps else ''
    if missing:
        return NODATA('已看到的都對，缺：' + '、'.join(missing) + note, *env[:4])
    return PASS('雷雨 wet=1 thunder=1、室內全 0、晴天 0、一般雨 wet 不加電荷、一般雪 stormy=0、暴風雪 stormy=1' + note,
                *[seen[w][0] for w in seen][:6], storm_charges[0])


def soak_hits(seg):
    out = []
    for p in seg.procs():
        steps = steps_of(p)
        if 'SoakSlow' in steps:
            out.append((p, steps['SoakSlow'][0]))
    return out


def slow_expiry(seg, after_line):
    for x in seg.of('remove'):
        if x['tag'] == 'Slow' and x.seq > after_line.seq and x['reason'] == 'expired':
            return x, (x.g - after_line.g) / 1000.0
    return None, None


@rule('A-16')
def r_a16(seg, ctx):
    hits = soak_hits(seg)
    if not hits:
        return NODATA('雨中那一刀沒有 SoakSlow（下雨了嗎？env wet=1？）')
    p, (pct, secs) = hits[0]
    if not near(pct, 15.0, 0.01) or secs != 10:
        return FAIL(f'浸濕減速 {pct}% {secs} 秒（應 15% 10 秒）', p)
    x, dt = slow_expiry(seg, p)
    if x is None:
        return EYES('浸濕 15% 10 秒已上（speedmult 85）；log 沒看到它過期的 remove，請看 11 秒後 speedmult 是否 100', p)
    if not 9.0 <= dt <= 11.5:
        return FAIL(f'浸濕減速 {dt:.1f} 秒後才過期（應約 10 秒）', p, x)
    return PASS(f'雨中那一刀上浸濕減速 15%（speedmult 85）10 秒，{dt:.1f} 秒後過期', p, x)


@rule('A-18')
def r_a18(seg, ctx):
    hits = soak_hits(seg)
    if len(hits) < 2:
        return NODATA(f'只看到 {len(hits)} 刀帶浸濕（① 與 ② 各一刀）')
    (p1, (pct1, s1)), (p2, (pct2, s2)) = hits[0], hits[-1]
    dur = [x for x in seg.of('mcm') if x['global'] == 'ESSB_MultDuration']
    if s1 != 10:
        return FAIL(f'① 浸濕 {s1} 秒（10.3 應四捨五入成 10）', p1)
    if s2 != 30:
        return FAIL(f'② 浸濕 {s2} 秒（15 秒 ×3 應夾在 30）', p2, *dur)
    x1, d1 = slow_expiry(seg, p1)
    x2, d2 = slow_expiry(seg, p2)
    notes = f'① {s1} 秒' + (f'（{d1:.1f} 秒後過期）' if d1 else '') + f'；② {s2} 秒' + (f'（{d2:.1f} 秒後過期）' if d2 else '')
    if (d1 and not 9 <= d1 <= 11.5) or (d2 and not 29 <= d2 <= 31.5):
        return FAIL('過期時間不對：' + notes, p1, x1, p2, x2)
    return PASS(notes, p1, x1, p2, x2, *dur[:1])


# ---------------------------------------------------------------- B

def base_roll(proc):
    """The proc's base B: the element's R(lo,hi) draw, or lightning's best I(1,25) of N."""
    rs = rolls_of(proc)
    if proc['el'] == 'shock':
        ints = [v for k, a, v in rs if k == 'I']
        return max(ints) if ints else None
    reals = [v for k, a, v in rs if k == 'R']
    return reals[0] if reals else None


def ratio(proc, g=1.05):
    b = base_roll(proc)
    return None if not b else proc.d('mag') / (b * g)


def noform(seg, **w):
    return [p for p in seg.procs() if p['el'] == 'none' and all(p[k] == v for k, v in w.items())]


@rule('B-01')
def r_b01(seg, ctx):
    normal = noform(seg, power='0')
    power = noform(seg, power='1')
    ends = seg.of('hit-end')
    if not normal or len(power) < 2:
        return NODATA(f'普攻 {len(normal)} 刀、重擊 {len(power)} 刀（需 1 普攻 + 2 重擊）')
    p1 = normal[0]
    over = p1['overloaded'] == '1'
    want = 13.13 if over else 10.5
    if not near(p1.d('mag'), want, 0.08) or not near(p1.v('siphon'), 10.5, 0.08) or not near(p1.v('burned'), 5.25, 0.08):
        return FAIL(f'① 真傷 {p1["mag"]}（應 {want}）吸魔 {p1["siphon"]}（10.5）燒魔 {p1["burned"]}（5.25）', p1)
    e1 = next((x for x in ends if x.seq > p1.seq), None)
    t0, t1 = p1.a.get('tgt'), e1.a.get('tgt') if e1 else None
    if t0 and t1 and not near(t0.m - t1.m, 15.75, 0.6):
        return FAIL(f'① NPC 魔力 {t0.m} → {t1.m}（應少 15.75）', p1, e1)
    p2 = power[0]
    if p2['dispel'] != '1' or not near(p2.v('siphon'), 15.75, 0.15):
        return FAIL(f'② 重擊 dispel={p2["dispel"]} 吸魔 {p2["siphon"]}（應 15.75）', p2)
    p3 = next((p for p in power[1:] if p.a.get('tgt') and p.a['tgt'].m <= 6), None)
    if not p3:
        return NODATA('③ 沒有「NPC 魔力 5」的那一刀重擊', p1, p2)
    e3 = next((x for x in ends if x.seq > p3.seq), None)
    silence = [x for x in seg.of('silence') if x.seq > p3.seq]
    resolve = [x for x in seg.ops(kind='N4_Resolve', op='Apply') if x.seq > p3.seq]
    you0 = p3.a.get('you')
    you1 = e3.a.get('you') if e3 else None
    if not e3 or e3.a['tgt'].m > 0.5:
        return FAIL('③ 重擊後 NPC 魔力不是 0', p3, e3)
    if silence and any(x.a['on'].m > 0.5 for x in silence[:3]):
        return FAIL('③ 沉默中 NPC 回魔了', *silence[:3])
    if not resolve:
        return FAIL('③ 沒有戰意 +1（N4_Resolve）', p3)
    if you0 and you1 and near(you0.m, you0.mmax, 1.0) and not near(you1.m, you0.mmax * 0.85 + 5, 3.0):
        return FAIL(f'③ 你的魔力 {you1.m:.1f}（應約 M×85%+5＝{you0.mmax * 0.85 + 5:.1f}）', p3, e3)
    return PASS(f'① 真傷 {p1["mag"]}、吸魔 10.5、燒魔 5.25；② 滅法吸魔 {p2["siphon"]}；③ NPC 魔力歸 0、沉默中不回、戰意 +1、'
                f'你的魔力 {you1.m if you1 else "?"}', p1, e1, p2, p3, e3, *(silence[:1] + resolve[:1]))


@rule('B-02')
def r_b02(seg, ctx):
    power = noform(seg, power='1')
    if len(power) < 3:
        return NODATA(f'重擊只有 {len(power)} 刀')
    bad = []
    for p in power[:3]:
        spend = steps_of(p).get('SpendMagicka')
        you = p.a.get('you')
        if not spend or not you or not rel(spend[0][0], you.mmax * 0.15, 0.05):
            bad.append(p)
    hurt = [x for x in seg.of('hurt') if x.a.get('att') is None]
    if bad:
        return FAIL('重擊沒有扣最大魔力 15%', *bad)
    return EYES(f'log：三刀各扣最大魔力 15%；無攻擊者的受擊行 {len(hurt)} 行。自己有沒有硬直／音效／血花／特效只能看畫面', *power[:3])


@rule('B-03')
def r_b03(seg, ctx):
    node = node_added(seg, '0049AB')
    p = next((p for p in noform(seg, power='0') if not node or p.seq > node.seq), None)
    if not p:
        return NODATA('加了 0049AB 之後沒有普攻')
    if not 10.9 <= p.v('siphon') <= 11.1:
        return FAIL(f'吸魔 {p["siphon"]}（應 11.0）', node, p)
    return PASS(f'吸魔 {p["siphon"]}（原 10.5）', node, p)


@rule('B-04')
def r_b04(seg, ctx):
    node = node_added(seg, '0049F6')
    ps = [p for p in noform(seg, power='0') if not node or p.seq > node.seq]
    p = next((p for p in ps if p['overloaded'] == '0'), None)
    if not p:
        return NODATA('加了 0049F6 之後沒有「沒觸發超載」的普攻' + ('（都是魔力滿的超載）' if ps else ''), *ps[:1])
    if not 10.55 <= p.d('mag') <= 10.66:
        return FAIL(f'真傷 {p["mag"]}（應 10.6）', node, p)
    return PASS(f'真傷 {p["mag"]}（5.25 + 5.25 × 1.02）', node, p)


@rule('B-05')
def r_b05(seg, ctx):
    node = node_added(seg, '004A05')
    ps = noform(seg, power='1')
    before = [p for p in ps if not node or p.seq < node.seq]
    after = [p for p in ps if node and p.seq > node.seq]
    if not before or not after:
        return NODATA(f'加點前 {len(before)} 刀、加點後 {len(after)} 刀重擊')
    a, b = before[0], after[0]
    ra = a.v('burned') / a.a['you'].mmax
    rb = b.v('burned') / b.a['you'].mmax
    if not near(ra, 0.15, 0.004) or not near(rb, 0.1605, 0.004):
        return FAIL(f'燒魔 ÷ 最大魔力：加點前 {ra:.4f}（0.15）加點後 {rb:.4f}（0.1605）', a, node, b)
    return PASS(f'燒魔 ÷ 最大魔力：{ra:.4f} → {rb:.4f}（×1.07）', a, node, b)


@rule('B-06')
def r_b06(seg, ctx):
    casts = [x for x in seg.of('cast') if x['marked'] == '1' and x.v('cost', 0) > 0]
    counter = [x for x in seg.ops(op='Damage', ctx='enemy-cast') if x['el'] == 'none']
    interrupts = seg.ops(op='Interrupt', ctx='hit')
    cooldowns = seg.ops(kind='N4_InterruptCooldown', op='Apply')
    resolve = seg.ops(kind='N4_Resolve', op='Apply')
    if not casts:
        return NODATA('沒有被掛破魔印的法師施法（cast marked=1）')
    c = casts[0]
    d = next((x for x in counter if x.seq > c.seq), None)
    if not d:
        return FAIL('法師施法後沒有反咒真傷', c)
    caster = c.a.get('caster')
    if d.a.get('on') and caster and d.a['on'].id != caster.id:
        return FAIL('反咒的真傷打到的不是施法者', c, d)
    if not rel(d.d('mag'), c.v('cost') * 1.02, 0.06):
        return FAIL(f'反咒真傷 {d["mag"]}，法術消耗 {c["cost"]}（應約 ×1.02）', c, d)
    if not any(x.seq > c.seq and x['ctx'] == 'enemy-cast' for x in resolve):
        return FAIL('反咒沒有戰意 +1', c, d)
    if not interrupts:
        return EYES(f'反咒 OK（消耗 {c["cost"]}、真傷 {d["mag"]}、戰意 +1）；log 沒有斷咒的打斷（法師詠唱時打到了嗎？）', c, d)
    first = interrupts[0]
    cd = next((x for x in cooldowns if x.seq > first.seq - 50), None)
    again = [x for x in interrupts[1:] if (x.g - first.g) < 5000]
    if again:
        return FAIL('斷咒 5 秒內又打斷了一次', first, *again)
    return PASS(f'反咒：消耗 {c["cost"]} → 施法者真傷 {d["mag"]}、戰意 +1；斷咒：打斷一次並掛 5 秒冷卻，冷卻內沒再打斷', c, d, first, cd)


@rule('E-04')
def r_e04(seg, ctx):
    casts = [x for x in seg.of('cast') if x['marked'] == '1']
    if not casts:
        return NODATA('沒有 cast marked=1')
    rows = []
    bad = []
    for c in casts:
        caster = c.a.get('caster')
        before = last_before(seg, c, 'casting', lambda x: x.a.get('who') and caster and x.a['who'].id == caster.id)
        if before and caster:
            spent = before.a['who'].m - caster.m
            rows.append(f'消耗 {c["cost"]} ／ 實際少 {spent:.1f}')
            if abs(spent - c.v('cost')) > 1.0 and spent > 0:
                bad.append(c)
    same_spell = defaultdict(list)
    for c in casts:
        same_spell[c['spell']].append(c)
    burst = [v for v in same_spell.values() if len(v) >= 3 and (v[-1].g - v[0].g) < 3500]
    if bad:
        return FAIL('cost 跟法師實際少掉的魔力差超過 1：' + '；'.join(rows), *bad)
    if burst:
        return FAIL('同一個法術幾秒內多行 cast（專注法術每秒一行？）', *burst[0])
    return PASS('每次施法一行，cost 跟實際魔力差 < 1：' + ('；'.join(rows) if rows else '（沒有施法前的 casting 行可比，只驗了一次一行）'), *casts[:3])


@rule('B-07')
def r_b07(seg, ctx):
    normal = [p for p in seg.procs(el='fire', power='0') if p['src'] == 'hit']
    power = [p for p in seg.procs(el='fire', power='1') if p['src'] == 'hit']
    if len(normal) < 5 or len(power) < 3:
        return NODATA(f'普攻 {len(normal)} 刀、重擊 {len(power)} 刀（需 5 + 3）')
    clean_n = [p for p in normal if near(ratio(p), 1.0, 0.005)]
    clean_p = [p for p in power if near(ratio(p), 1.5, 0.008)]
    heated = len(normal) + len(power) - len(clean_n) - len(clean_p)
    bad_n = [p for p in clean_n if not 10.49 <= p.d('mag') <= 12.61]
    bad_p = [p for p in clean_p if not 15.7 <= p.d('mag') <= 18.91]
    distinct = len({p['mag'] for p in clean_n})
    if bad_n or bad_p:
        return FAIL('強度超出範圍（普通 10.5～12.6、重擊 15.7～18.9）', *(bad_n + bad_p))
    if len(clean_n) < 3 or len(clean_p) < 1:
        return NODATA(f'沒有熱度的刀太少（普通 {len(clean_n)}、重擊 {len(clean_p)}；{heated} 刀帶熱度加成）', *normal[:3])
    if distinct < 3:
        return FAIL(f'普通攻擊只有 {distinct} 種強度', *clean_n)
    return PASS(f'普通 {fmt_nums([p.v("mag") for p in clean_n])}（{distinct} 種）；重擊 {fmt_nums([p.v("mag") for p in clean_p])}'
                + (f'；另 {heated} 刀帶熱度加成未計' if heated else ''), *(clean_n[:3] + clean_p[:2]))


def heat_track(seg):
    """Your heat tier over the station from the ops on you (Apply N3_HeatK / Remove)."""
    out = []
    for x in seg.ops(who='you'):
        k = x['kind'] or ''
        m = re.fullmatch(r'N3_Heat(\d)', k)
        if m:
            out.append((x, int(m.group(1)), x['op']))
    return out


@rule('B-08')
def r_b08(seg, ctx):
    track = heat_track(seg)
    applies = [(x, k) for x, k, op in track if op == 'Apply']
    order = [k for x, k in applies]
    if not applies:
        return NODATA('這一站沒有熱度的 op')
    got = chain(applies, [lambda a: a[1] == 1, lambda a: a[1] == 2, lambda a: a[1] == 3])
    if not got:
        return FAIL('熱度沒有依序 1→2→3：' + '→'.join(map(str, order)), *[x for x, k in applies])
    white = got[2][0]
    # 同時兩個熱度：每次 Apply 前，其他階都被 Remove
    live = set()
    for x, k, op in track:
        if op == 'Remove':
            live.discard(k)
        else:
            live.add(k)
            if len(live) > 1:
                return FAIL(f'同時有兩個熱度 {sorted(live)}', x)
    burns = [x for x in seg.ops(op='Damage', ctx='fire-source') if x.seq > white.seq]
    pays = [x for x in seg.ops(op='PayHealth') if x.seq > white.seq]
    settle = next((x for x in seg.of('settle') if x['tag'] == 'N3_Heat3' and x.seq > white.seq), None)
    if not burns:
        return FAIL('白熱時 NPC 沒有每秒掉血（沒有 ctx=fire-source 的傷害）', white)
    if not settle:
        return NODATA('白熱引信沒結束（沒有 settle tag=N3_Heat3；等滿 9 秒）', white, burns[0])
    overheat = [x for x in pays if x.seq > settle.seq]
    you0 = white.a.get('on')
    later = next((x for x in seg if x.seq and x.seq > settle.seq + 3 and x.a.get('you')), None)
    lost = (you0.h - later.a['you'].h) / you0.hmax if you0 and later else None
    if not overheat or not rel(overheat[0].v('mag'), you0.hmax * 0.10, 0.05):
        return FAIL('引信結束沒有付 10% 生命（過熱）', settle, *(overheat[:1]))
    if lost is not None and not 0.10 <= lost <= 0.18:
        return FAIL(f'你的生命只少了 {lost * 100:.1f}%（應約 14%：白熱每秒 0.5% × 8 + 過熱 10%）', white, settle, later)
    return PASS(f'熱度 1→2→3（一次只有一階）；白熱中 NPC 每秒吃火傷 {len(burns)} 次；引信結束付 10%；你共少 '
                + ('?' if lost is None else f'{lost * 100:.1f}%'), *[g[0] for g in got], burns[0], settle, overheat[0])


@rule('B-10')
def r_b10(seg, ctx):
    frozen = seg.ops(kind='N3_Frozen', op='Apply')
    if not frozen:
        return NODATA('沒有冰封（N3_Frozen）')
    f = frozen[0]
    hit = next((p for p in seg.procs(el='frost', power='1') if p.seq > f.seq), None)
    if not hit:
        return NODATA('冰封後沒有重擊', f)
    shatter = [x for x in seg.ops(ev='Shatter') if x.seq > hit.seq]
    dmg = [x for x in seg.ops(op='Damage', el='frost') if x.seq > hit.seq]
    end = next((x for x in seg.of('hit-end') if x.seq > hit.seq), None)
    tgt = hit.a.get('tgt')
    drop = tgt.h - end.a['tgt'].h if end and tgt else None
    removed = [x for x in seg.ops(kind='N3_Frozen', op='Remove') if x.seq > hit.seq]
    if not shatter:
        return FAIL('冰封中重擊沒有碎冰（ev=Shatter）', f, hit)
    if drop is None or drop < 0.16 * tgt.hmax:
        return FAIL(f'只少 {drop}（應 ≥ 最大生命 16%＝{0.16 * tgt.hmax:.0f}）', hit, end, *dmg[:2])
    if not removed:
        return FAIL('碎冰後冰封沒退', hit, shatter[0])
    return PASS(f'碎冰：生命少 {drop:.0f}（最大 {tgt.hmax:.0f} 的 {drop / tgt.hmax * 100:.0f}%），冰封退掉', f, hit, shatter[0], end, removed[0])


def spell_name(ctx, local):
    names = getattr(ctx, 'names', None)
    if names is None:
        names = {}
        path = HERE / 'v03-formids.json'
        if path.exists():
            for edid, row in json.loads(path.read_text(encoding='utf-8'))['records'].items():
                names[int(row['id'], 16)] = edid
        ctx.names = names
    return names.get(local, f'0x{local:06X}')


@rule('B-11')
def r_b11(seg, ctx):
    rows = []
    for x in seg.of('apply'):
        name = spell_name(ctx, int(x['spell'], 16)) if x['spell'] else ''
        if name.startswith('ESSB_IceArmorChill'):
            rows.append((x, name))
    if not rows:
        return NODATA('沒有冰甲寒氣上身的 apply 行（冰甲節點、冰霜形態、站 NPC 旁？）')
    narrow = [x for x, n in rows if n == 'ESSB_IceArmorChill']
    wide = [x for x, n in rows if n == 'ESSB_IceArmorChillWide']
    bad = [x for x in narrow if not near(x.v('mag'), 20, 0.01)] + [x for x in wide if not near(x.v('mag'), 30, 0.01)]
    if bad:
        return FAIL('寒氣減速不是 20%／30%', *bad)
    if not narrow or not wide:
        return NODATA(f'冰甲 {len(narrow)} 次、霜膚 {len(wide)} 次', *[x for x, n in rows[:3]])
    return EYES('log：冰甲寒氣減速 20%、霜膚 30% 都上身；「6 公尺外 100」與「關冰霜後不再減速」要看 speedmult', narrow[0], wide[0])


@rule('B-12')
def r_b12(seg, ctx):
    armor = seg.ops(kind='N4_IceShieldArmorAV', op='Apply')
    magic = seg.ops(kind='N4_IceShieldMagicAV', op='Apply')
    count = seg.ops(kind='N4_IceShield', op='Apply')
    if not count:
        return NODATA('沒有冰盾的 op')
    three = next((x for x in count if near(x.v('mag'), 3, 0.01)), None)
    if not three:
        return FAIL('冰盾沒到 3 層：' + fmt_nums([x.v('mag') for x in count], 0), *count)
    a = next((x for x in armor if x.seq > three.seq - 3 and near(x.v('mag'), 60, 0.01)), None)
    m = next((x for x in magic if x.seq > three.seq - 3 and near(x.v('mag'), 12, 0.01)), None)
    if not a or not m:
        return FAIL('3 層時護甲 +60／魔抗 +12 沒上', three, *(armor[-1:] + magic[-1:]))
    gone = [x for x in seg.of('remove') if x['tag'] == 'N4_IceShield' and x['reason'] == 'expired']
    note = f'；停手後 {((gone[0].g - three.g) / 1000):.1f} 秒過期' if gone else '；（沒看到過期）'
    return PASS('冰盾 3 層、護甲 +60、魔抗 +12' + note, three, a, m, *(gone[:1]))


@rule('B-13')
def r_b13(seg, ctx):
    procs = seg.procs(el='shock')
    charges = seg.ops(kind='N4_Charge', op='Apply')
    if len(procs) < 5:
        return NODATA(f'雷電只有 {len(procs)} 刀')
    mags = [int(round(x.v('mag'))) for x in charges]
    got = chain(mags, [lambda v: v == 2, lambda v: v == 3, lambda v: v == 4, lambda v: v == 5, lambda v: v == 6])
    if not got:
        return FAIL('電荷不是 2→3→4→5→6：' + '→'.join(map(str, mags)), *charges)
    bad_n = [p for p in procs if p['power'] == '0' and p.v('N') != p.v('charges') + 1]
    over = [p for p in procs if p['crit'] == '0' and p['power'] == '0' and p.d('mag') > 26.3]
    if bad_n or over:
        return FAIL('N ≠ 電荷 +1，或沒暴擊的強度超過 26.3', *(bad_n + over))
    pw = next((p for p in procs if p['power'] == '1' and p.v('charges') >= 6), None)
    if not pw:
        return NODATA('沒有滿格的重擊', *procs[:3])
    dis = next((x for x in seg.ops(ev='Discharge') if x.seq > pw.seq), None)
    cleared = next((x for x in seg.ops(kind='N4_Charge', op='Remove') if x.seq > pw.seq), None)
    end = next((x for x in seg.of('hit-end') if x.seq > pw.seq), None)
    if not dis or not cleared:
        return FAIL('滿格重擊沒放電或電荷沒清空', pw, dis, cleared)
    extra = ((pw.a['tgt'].h - end.a['tgt'].h) / pw.dm - pw.d('mag')) if end else None   # 27g: at 傷害倍率 1.0
    if extra is not None and extra < 150:
        return FAIL(f'放電只多扣 {extra:.0f}（應約 177）', pw, dis, end)
    crit = [p for p in procs if p['crit'] == '1']
    return PASS(f'電荷 2→6、N＝電荷+1、沒暴擊 ≤ 26.3（暴擊 {len(crit)} 刀）；滿格重擊放電多扣 '
                + ('?' if extra is None else f'{extra:.0f}') + '、電荷清空', *(charges[:2] + [pw, dis, cleared, end]))


@rule('B-14')
def r_b14(seg, ctx):
    tries = []
    for p in seg.procs(el='shock', power='0'):
        if p.v('charges', 0) >= 6:
            draws = next((x for x in seg.of('rng') if x.seq > p.seq and x['ctx'] == 'hit'), None)
            tries.append((p, draws))
    hits = seg.ops(op='Interrupt', ctx='hit')
    if len(tries) < 5:
        return NODATA(f'滿格普攻只有 {len(tries)} 刀（做 10 次）')
    rolled = [(p, d) for p, d in tries if d and 'C(0.3)' in d.text]
    n = len(rolled)
    k = len(hits)
    if n and k == 0 and n >= 10:
        return FAIL(f'{n} 次詠唱中滿格普攻都沒打斷', *[p for p, d in rolled[:3]])
    if n and k >= n and n >= 5:
        return FAIL(f'{n} 次每次都打斷', *hits[:3])
    if n == 0:
        return NODATA(f'{len(tries)} 刀滿格普攻都不是在對方詠唱時（沒有 30% 的擲骰）', *[p for p, d in tries[:3]])
    return PASS(f'詠唱中滿格普攻 {n} 次，打斷 {k} 次（約三成）', *([p for p, d in rolled[:2]] + hits[:2]))


@rule('E-05')
def r_e05(seg, ctx):
    rows = seg.of('casting')
    inter = seg.of('interrupt')
    if not rows:
        return NODATA('沒有 casting 行（先砍法師一刀，它才會被追蹤）')
    states = [x['state'] for x in rows]
    seen = set(states)
    if not ({'1', '2', '3'} & seen) or not ({'4', '5', '6'} & seen):
        return FAIL('詠唱狀態序列不完整：' + '→'.join(states[:20]), *rows[:6])
    if inter:
        i = inter[0]
        after = next((x for x in rows if x.seq > i.seq), None)
        if after and after['state'] not in ('0', '9'):
            return FAIL(f'中斷後的狀態是 {after["state"]}（應 0 或 9）', i, after)
        return PASS('詠唱序列 ' + '→'.join(states[:12]) + '；中斷後回 0／9', rows[0], i, after)
    return PASS('詠唱序列 ' + '→'.join(states[:12]) + '（這一站沒有中斷）', *rows[:4])


@rule('B-15')
def r_b15(seg, ctx):
    block = next((x for x in seg.of('hurt') if x['blocked'] == '1'), None)
    if not block:
        return NODATA('沒有格擋成功的受擊行（hurt blocked=1）')
    win = next((x for x in seg.ops(op='Riposte') if x.seq > block.seq), None)
    ps = [p for p in noform(seg, power='0') if p.seq > block.seq]
    if not win:
        return FAIL('格擋後沒有反擊視窗（op=Riposte）', block)
    if len(ps) < 2:
        return NODATA(f'格擋後只有 {len(ps)} 刀普攻', block, win)
    a, b = ps[0], ps[1]
    if not (a['riposte'] == '1' and 21.5 <= a.v('siphon') <= 22.6):
        return FAIL(f'格擋後第一刀吸魔 {a["siphon"]}（應約 22，×2）riposte={a["riposte"]}', block, win, a)
    if b['riposte'] == '1' or b.v('siphon') > 12.0:
        return FAIL(f'第二刀還是翻倍（吸魔 {b["siphon"]}）', a, b)
    return PASS(f'格擋後第一刀吸魔 {a["siphon"]}（×2），第二刀 {b["siphon"]}', block, win, a, b)


@rule('B-16')
def r_b16(seg, ctx):
    rock = seg.ops(kind='N4_RockArmor')
    av = seg.ops(kind='N4_RockArmorAV', op='Apply')
    force = seg.ops(kind='N4_StoredForce', op='Apply')
    if not rock:
        return NODATA('沒有岩甲的 op')
    first = next((x for x in rock if x['op'] == 'Apply'), None)
    if not first or not near(first.v('mag'), 2, 0.01):
        return FAIL('① 開印後岩甲不是 2 層', *rock[:3])
    a50 = next((x for x in av if near(x.v('mag'), 50, 0.01)), None)
    if not a50:
        return FAIL('① 岩甲 2 層時護甲不是 +50', first, *av[:2])
    hurt = [x for x in seg.of('hurt') if x['blocked'] == '0' and x.seq > first.seq]
    one = next((x for x in rock if x['op'] == 'Apply' and near(x.v('mag'), 1, 0.01) and hurt and x.seq > hurt[0].seq), None)
    blocked = next((x for x in seg.of('hurt') if x['blocked'] == '1'), None)
    f2 = next((x for x in force if blocked and x.seq > blocked.seq and near(x.v('mag'), 2, 0.01)), None)
    if not one:
        return FAIL('② 被打後岩甲沒有 −1', *(hurt[:1] + rock[:4]))
    if not blocked or not f2:
        return FAIL('③ 格擋後沒有「蓄勁 2」', blocked, *force[:2])
    # ④ 碎岩: a power earth hit at full rock -- its plan knocks the target (ev=Knock) and clears the rock; the ring itself
    # (CrushArea) is consumed by the body pass, so the knock is what the log shows
    crush = next((p for p in seg.procs(el='earth', power='1') if p.seq > (f2.seq if f2 else 0)), None)
    knock = next((x for x in seg.ops(ev='Knock', ctx='hit') if crush and x.seq > crush.seq), None)
    f5 = next((x for x in force if crush and x.seq > crush.seq and near(x.v('mag'), 5, 0.01)), None)
    gone = next((x for x in rock if crush and x['op'] == 'Remove' and x.seq > crush.seq), None)
    if not crush:
        return NODATA('④ 沒有滿層重擊', first, one, f2)
    if not (knock and gone and f5):
        return FAIL('④ 碎岩後：倒地、岩甲清空、蓄勁 5 缺一', crush, knock, gone, f5)
    return PASS('① 岩甲 2 層、護甲 +50；② 被打 −1；③ 格擋蓄勁 2；④ 碎岩：土傷＋倒地、岩甲清空、蓄勁 5', first, a50, one, f2, crush, knock, f5)


@rule('B-17')
def r_b17(seg, ctx):
    node = node_added(seg, '0020D0') or node_added(ctx.all, '0020D0')
    drains = seg.ops(op='DrainStamina', ctx='enter')
    scan = [x for x in seg.of('scan-c') if x.a.get('who')]
    if not drains:
        return NODATA('開大地形態時沒有削耐（ctx=enter 的 DrainStamina）', node)
    d = drains[0]
    on = d.a.get('on')
    if on and not rel(d.v('mag'), on.smax * 0.5, 0.12):
        return FAIL(f'削耐 {d["mag"]}，NPC 最大耐力 {on.smax}（應約一半）', d)
    far = [x for x in scan if x.v('d_you', 0) > 280 and any(o.a.get('on') and o.a['on'].id == x.a['who'].id for o in drains)]
    if far:
        return FAIL('4 公尺外的 NPC 也被削耐', *far)
    return PASS(f'開大地形態時 2 公尺內 NPC 被削耐 {d["mag"]}（最大耐力 {on.smax if on else "?"} 的一半）', node, d)


@rule('B-18')
def r_b18(seg, ctx):
    ps = seg.procs(el='wind')
    sneak = [p for p in ps if p['sneak'] == '1']
    open_ = [p for p in ps if p['sneak'] == '0']
    if not sneak or len(open_) < 2:
        return NODATA(f'潛行 {len(sneak)} 刀、被看見 {len(open_)} 刀')
    s = sneak[0]
    if not 25.1 <= s.d('mag') <= 28.5:
        return FAIL(f'潛行未被發現那刀 {s["mag"]}（應 25.2～28.4，×3）', s)
    bad = [p for p in open_ if p.d('mag') > 9.6]
    if bad:
        return FAIL('被看見的刀也 ×3', *bad)
    return PASS(f'潛行 {s["mag"]}（×3）；被看見 {fmt_nums([p.v("mag") for p in open_])}', s, *open_[:2])


@rule('B-19')
def r_b19(seg, ctx):
    gauge = seg.ops(kind='N4_WindGauge')
    blades = seg.ops(ev='Blade')
    if not gauge:
        return NODATA('沒有風勢的 op')
    mags = [int(round(x.v('mag'))) for x in gauge if x['op'] == 'Apply']
    if not chain(mags, [lambda v: v == 2, lambda v: v == 3]):
        return FAIL('風勢不是 2→3：' + '→'.join(map(str, mags)), *gauge)
    three = next(x for x in gauge if x['op'] == 'Apply' and near(x.v('mag'), 3, 0.01))
    b1 = next((b for b in blades if b.seq > three.seq), None)
    if not b1:
        return FAIL('第三刀沒有風刃', three)
    args = b1['args'].split('|') if b1['args'] else []
    if args and float(args[0]) != 1:
        return FAIL(f'一次送出 {args[0]} 段風刃', b1)
    sneak = next((p for p in seg.procs(el='wind', sneak='1') if p.seq > b1.seq), None)
    b2 = next((b for b in blades if sneak and b.seq > sneak.seq), None)
    if not sneak:
        return NODATA('③ 沒有偷襲那一刀', three, b1)
    if not b2 or (b2.seq - sneak.seq) > 60:
        return FAIL('③ 偷襲沒有立刻送出風刃', sneak)
    return PASS('風勢 2→3，第三刀一段風刃並歸零；偷襲立刻一段風刃', three, b1, sneak, b2)


@rule('B-20')
def r_b20(seg, ctx):
    dumps = [x for x in seg.of('pap') if x['kind'] == 'dump-nearest']
    freeze = seg.ops(kind='N3_Freeze', op='Apply')
    if len(dumps) < 2:
        vals = fmt_nums([x.v('mag') for x in freeze], 0)
        return NODATA(f'「印出目標狀態」只有 {len(dumps)} 次（凍結 op：{vals}）', *freeze[:2])
    s = [x['s2'] for x in dumps]
    if s[0] != '4' or s[1] != '3':
        return FAIL(f's2 依序 {s[:2]}（應 4、3）', *dumps[:2], *freeze[:2])
    return PASS('切掉風印記那刀 s2=4；切掉火印記那刀 s2=3', *dumps[:2], *freeze[:2])


@rule('B-21')
def r_b21(seg, ctx):
    ps = [p for p in seg.procs(el='blood', power='0') if p['src'] == 'hit']
    if len(ps) < 2:
        return NODATA(f'鮮血普攻只有 {len(ps)} 刀')
    p = ps[1]
    heal = steps_of(p).get('Heal')
    if not 7.9 <= p.d('mag') <= 10.1:
        return FAIL(f'第二刀強度 {p["mag"]}（應 8～10）', p)
    if not heal or not rel(heal[0][0], p.v('mag') * 0.25, 0.08):
        return FAIL('第二刀吸血不是強度的 25%：' + (str(heal[0][0]) if heal else '沒有 Heal'), p)
    end = next((x for x in seg.of('hit-end') if x.seq > p.seq), None)
    d = end.a['you'].h - p.a['you'].h if end else None
    return PASS(f'第二刀強度 {p["mag"]}、吸血 {heal[0][0]:.2f}（25%）；那一刀前後你的生命 '
                + ('?' if d is None else f'{d:+.2f}'), p, end)


@rule('B-22')
def r_b22(seg, ctx):
    pools = []
    for p in seg.procs(el='blood'):
        g = steps_of(p).get('BloodGuard')
        if g:
            pools.append((p, g[0][0]))
    if len(pools) < 3:
        return NODATA(f'只有 {len(pools)} 刀灌進護血池')
    values = [v for p, v in pools]
    deltas = [b - a for a, b in zip(values, values[1:])]
    you = pools[-1][0].a['you']
    if any(v > you.hmax * 0.2 + 0.5 for v in values):
        return FAIL(f'護血池超過最大生命 20%：{fmt_nums(values)}', *[p for p, v in pools])
    grow = [d for d in deltas if d > 0]
    if len(grow) < 2:
        return FAIL('護血池沒隨刀數增加：' + fmt_nums(values), *[p for p, v in pools])
    return PASS('護血池 ' + fmt_nums(values) + '（每刀 +' + fmt_nums(grow) + '），不超過最大生命 20%', *[p for p, v in pools[:4]])


@rule('B-23')
def r_b23(seg, ctx):
    sync = [x for x in seg.ops(kind='N4_Sync', op='Apply')]
    ups = seg.ops(ev='SyncUp')
    if len(sync) < 30:
        return NODATA(f'同調只看到 {len(sync)} 次 +1')
    mags = [int(round(x.v('mag'))) for x in sync]
    if mags[:30] != list(range(1, 31)):
        return FAIL('同調不是每刀 +1：' + ','.join(map(str, mags[:32])), *sync[:3])
    at = []
    for u in ups:
        before = last_before(seg, u, 'op', lambda x: x['kind'] == 'N4_Sync' and x['op'] == 'Apply')
        at.append(int(round(before.v('mag'))) if before else None)
    if at != [5, 15, 30]:
        return FAIL(f'升段在第 {at} 刀（應 5、15、30 各一次）', *ups)
    return EYES('log：同調每刀 +1，第 5、15、30 刀各升一段（各一次）；升段音效與三段光暈只能看畫面', *ups)


@rule('B-35')
def r_b35(seg, ctx):
    ops = seg.ops(kind='N3_Bleed')
    if not ops:
        return NODATA('沒有血痕的 op')
    mags = [int(round(x.v('mag'))) for x in ops if x['op'] == 'Apply']
    if not mags or mags[0] != 2 or (len(mags) > 1 and mags[1] != 3):
        return FAIL('血痕 ①② 不是 2、3：' + ','.join(map(str, mags)), *ops[:3])
    if max(mags) != 8:
        return FAIL(f'血痕上限 {max(mags)}（應 8）', *ops[-2:])
    last = [x for x in ops if x['op'] == 'Apply'][-1]
    gone = next((x for x in seg.of('remove') if x['tag'] == 'N3_Bleed' and x.seq > last.seq), None)
    dumps = [x for x in seg.of('pap') if x['kind'] == 'dump-nearest']
    if not gone:
        return NODATA('停手後沒看到血痕過期', last)
    dt = (gone.g - last.g) / 1000.0
    if gone['reason'] != 'expired' or not 9.0 <= dt <= 11.5:
        return FAIL(f'血痕 {dt:.1f} 秒後 {gone["reason"]}（應 10 秒過期）', last, gone)
    return PASS(f'血痕 2、3、…、上限 8；停手 {dt:.1f} 秒後過期歸 0', ops[0], last, gone, *dumps[-1:])


@rule('E-02')
def r_e02(seg, ctx):
    rows = seg.ops(op='BleedDot') + ctx.seg('B-28').ops(op='PoisonDot')
    if not rows:
        return NODATA('沒有 BleedDot／PoisonDot 的 op（鮮血站與毒素站）')
    bad = [x for x in rows if x.v('n', 0) > 1]
    if bad:
        return FAIL('一次重套趕走了兩個以上的舊 DoT', *bad)
    first = [x for x in rows if x['was'] == '-']
    return PASS(f'{len(rows)} 次重套：第一次沒有舊的（was=-）{len(first)} 次，之後每次只趕走 1 個（n=1）', *rows[:4])


def first_hits(seg, el):
    """The procs of `el` on a target that had none of your hits in this station yet."""
    seen = set()
    out = []
    for p in seg.procs(el=el):
        t = p.a.get('tgt')
        if not t or t.id in seen:
            continue
        seen.add(t.id)
        out.append(p)
    return out


@rule('B-24')
def r_b24(seg, ctx):
    rows = []
    for p in seg.procs(el='divine', power='0'):
        env = last_before(seg, p, 'env')
        holy = last_before(seg, p, 'op', lambda x: (x['kind'] or '').startswith('N3_Holy') and x['who'] == 'you')
        fresh = holy is None or holy['op'] == 'Remove'
        mark = last_before(seg, p, 'op', lambda x: x['op'] in ('Mark', 'Unmark') and x['el'] == 'divine' and x.a.get('on') and p.a.get('tgt') and x.a['on'].id == p.a['tgt'].id)
        if fresh and (mark is None or mark['op'] == 'Unmark' or (p.g - mark.g) > 20000):
            rows.append((p, env['night'] if env else None))
    day = [p for p, n in rows if n == '0']
    night = [p for p, n in rows if n == '1']
    if not day or not night:
        return NODATA(f'乾淨的第一刀：中午 {len(day)}、晚上 {len(night)}（各 3 次）')
    bad = [p for p in day if p.d('mag') < 10.08 - 0.01] + [p for p in night if p.d('mag') > 10.5 + 0.01]
    if bad:
        return FAIL('中午低於 10.08 或晚上高於 10.5', *bad)
    return PASS(f'中午 {fmt_nums([p.v("mag") for p in day])}；晚上 {fmt_nums([p.v("mag") for p in night])}', *(day[:2] + night[:2]))


@rule('B-25')
def r_b25(seg, ctx):
    node = node_added(seg, '002188')
    firsts = [p for p in first_hits(seg, 'divine') if not node or p.seq < node.seq]
    undead = [p for p in firsts if 15.0 <= p.d('mag') <= 19.0]
    after = [p for p in seg.procs(el='divine') if node and p.seq > node.seq]
    second = []
    per = defaultdict(list)
    for p in after:
        per[p.a['tgt'].id].append(p)
    for v in per.values():
        if len(v) >= 2:
            second.append(v[1])
    if not undead:
        return NODATA('沒有屍鬼的第一刀（應 15.1～18.9）', *firsts[:3])
    if not second:
        return NODATA('加聖痕後沒有同一名強盜的第二刀', node, undead[0])
    s = second[0]
    if not 21.4 <= s.d('mag') <= 27.3:
        return FAIL(f'有聖痕的第二刀 {s["mag"]}（應 21.6～27.0）', node, s)
    return PASS(f'屍鬼第一刀 {undead[0]["mag"]}（×1.5）；聖痕後強盜第二刀 {s["mag"]}', undead[0], node, s)


@rule('B-26')
def r_b26(seg, ctx):
    track = []
    for x in seg.ops(who='you'):
        m = re.fullmatch(r'N3_Holy(\d)', x['kind'] or '')
        if m:
            track.append((x, int(m.group(1)), x['op']))
    applies = [(x, k) for x, k, op in track if op == 'Apply']
    if not applies:
        return NODATA('沒有聖佑的 op')
    if not chain(applies, [lambda a: a[1] == 1, lambda a: a[1] == 2, lambda a: a[1] == 3]):
        return FAIL('聖佑不是 I→II→III：' + '→'.join(str(k) for x, k in applies), *[x for x, k in applies])
    live = set()
    for x, k, op in track:
        if op == 'Remove':
            live.discard(k)
        else:
            live.add(k)
            if len(live) > 1:
                return FAIL(f'同時有兩階聖佑 {sorted(live)}', x)
    return EYES('log：聖佑 I→II→III、一次只有一階；attackdamagemult／damageresist 的數值由記錄帶（build 驗過），要看 getav 請看畫面',
                *[x for x, k in applies[:3]])


@rule('B-27')
def r_b27(seg, ctx):
    hurt = seg.of('hurt')
    wind_melee = [x.v('lost') for x in hurt if x['form'] == '5' and x['melee'] == '1' and x.v('lost', 0) > 0]
    div_melee = [x.v('lost') for x in hurt if x['form'] == '7' and x['melee'] == '1' and x.v('lost', 0) > 0]
    wind_spell = [x.v('lost') for x in hurt if x['form'] == '5' and x['spell'] == '1' and x.v('lost', 0) > 0]
    div_spell = [x.v('lost') for x in hurt if x['form'] == '7' and x['spell'] == '1' and x.v('lost', 0) > 0]
    if len(wind_melee) < 2 or len(div_melee) < 2:
        return NODATA(f'疾風近戰 {len(wind_melee)} 下、神聖近戰 {len(div_melee)} 下')
    a, b = statistics.mean(wind_melee), statistics.mean(div_melee)
    r = b / a
    note = f'近戰 B/A＝{r:.3f}'
    if wind_spell and div_spell:
        note += f'；火球 {div_spell[0]:.1f}／{wind_spell[0]:.1f}＝{div_spell[0] / wind_spell[0]:.3f}（應約 0.9）'
    if not 0.88 <= r <= 0.99:
        return FAIL(note + '（應約 0.95）', *hurt[:6])
    return EYES(note + '（約 0.95）；magicresist +10 要看 getav', *hurt[:6])


@rule('B-28')
def r_b28(seg, ctx):
    dumps = [x for x in seg.of('pap') if x['kind'] == 'dump-nearest']
    s7 = [x['s7'] for x in dumps]
    want = ['3', '4', '6', '10', '0']
    if len(dumps) < 5:
        return NODATA(f'「印出目標狀態」只有 {len(dumps)} 次：s7={s7}')
    if not chain(s7, [lambda v, w=w: v == w for w in want]):
        return FAIL(f's7 依序 {s7}（應 3、4、6、停在 10、0）', *dumps)
    return PASS('s7：3、4、6、10、0', *dumps[:5])


@rule('B-29')
def r_b29(seg, ctx):
    """Round 28 (D3, the user's decision): 水臨強化 restores 25% of max magicka (× the recovery slider, 1 in this sheet) and
    cleanses, only with a hostile within the advent's range -- the first open (no enemy near) gives nothing."""
    node = node_added(seg, '0021FC') or node_added(ctx.all, '0021FC')
    ops = seg.ops(op='RestoreMagicka', ctx='enter')
    enters = [x for x in seg.of('native') if x['fn'] == 'FormEnter'] or seg.of('switch')
    if not ops:
        return NODATA('開水形態時沒有回魔（旁邊有敵人時才回；ctx=enter 的 RestoreMagicka）', node)
    you = ops[0].a.get('on')
    bad = [x for x in ops if you and not near(x.v('mag'), you.mmax * 0.25, 1.0)]
    if bad:
        return FAIL(f'水臨強化回魔 {fmt_nums([x.v("mag") for x in ops])}（應最大魔力 {you.mmax:.0f} 的 25%＝{you.mmax * 0.25:.1f}）', *bad[:3])
    if len(ops) >= len(enters) and len(enters) >= 2:
        return FAIL(f'開了 {len(enters)} 次水形態、每次都回魔（旁邊沒敵人的那次不該回）', *ops[:3])
    # Round 28b (F7, the user's ruling 2026-09-28): 10 s cooldown on the running clock -- ③ inside it gives nothing and
    # logs "[ESSB][advent][L4] water-plus cooldown left=<s>"; ④ after it gives 25% again.
    close = [(a, b) for a, b in zip(ops, ops[1:]) if b.r - a.r < 10000]
    if close:
        a, b = close[0]
        return FAIL(f'10 秒內回魔兩次（相隔 {(b.r - a.r) / 1000:.1f} 秒；水臨強化有 10 秒冷卻）', a, b)
    cooling = raw_with(seg, '[ESSB][advent][L4] water-plus cooldown left=')
    lefts = [float(x.text.rsplit('left=', 1)[1].split()[0]) for x in cooling]
    if cooling and any(not 0.0 < s <= 10.0 for s in lefts):
        return FAIL(f'冷卻中的剩餘秒數 {fmt_nums(lefts)}（應在 0～10 秒）', *cooling[:2])
    if len(ops) < 2 or not cooling:
        return NODATA(f'水臨強化回魔 {len(ops)} 次、冷卻中的 L4 行 {len(cooling)} 行（③ 要在 10 秒內再切到水、④ 要等 10 秒後再切）', node, *ops[:2])
    return PASS(f'水臨強化回最大魔力 25%（{fmt_nums([x.v("mag") for x in ops])}），只在旁邊有敵人時；10 秒內再切到水沒有回魔'
                f'（冷卻剩 {fmt_nums(lefts)} 秒），之後再切又回', node, *(ops[:2] + cooling[:1]))


def wash_ok(x):
    return (x['type'] in ('0', '12', '13') and x['castingSource'] in ('0', '1') and x['hostile'] == '0' and x['ours'] == '0'
            and x['company'] == '0' and x.v('duration', 0) > 0 and x.v('elapsed', 0) < x.v('duration', 0))


@rule('B-30')
def r_b30(seg, ctx):
    wash = seg.ops(op='Wash')
    rows = seg.of('wash')
    if not wash:
        return NODATA('第 5 刀沒有沖刷（op=Wash）')
    washed = [x for x in rows if x['verdict'] == 'washed']
    if not washed:
        return FAIL('沖刷時沒有任何效果被沖掉（護甲術在嗎？）', wash[0], *rows[:4])
    wrong = [x for x in washed if not wash_ok(x)]
    you = [x for x in rows if x.a.get('on') and x.a['on'].id == PLAYER_ID]
    if wrong or you:
        return FAIL('沖掉了不該沖的，或沖到你自己', *(wrong + you))
    return EYES(f'log：沖掉 {len(washed)} 個手施增益（castingSource 0／1）、其餘保留；護甲術的外觀消失、你的藥水還在，看畫面',
                wash[0], *washed[:3])


@rule('E-03')
def r_e03(seg, ctx):
    rows = seg.of('wash')
    if not rows:
        return NODATA('沒有 wash 行')
    bad = [x for x in rows if x['verdict'] == 'washed' and not wash_ok(x)]
    console = [x for x in rows if x['castingSource'] == '3']
    if bad:
        return FAIL('不該沖的被 washed', *bad)
    note = f'；主控台施放的 castingSource=3、都 kept（{len(console)} 個）' if console else '；（沒看到 castingSource=3 的主控台增益）'
    return PASS(f'{len(rows)} 個效果：只有手施、有時長、非敵意、非我們的被沖' + note, *rows[:5])


@rule('B-31')
def r_b31(seg, ctx):
    curse = [int(round(x.v('mag'))) for x in seg.ops(kind='N3_Curse', op='Apply')]
    hall = seg.ops(ev='Hallucinate')
    pap = [x for x in seg.of('pap') if x['kind'] in ('hallucinate', 'fear', 'frenzy')]
    kinds = [x['args'].split('|')[0] if x['args'] else '?' for x in hall]
    vision = [x for x in pap if x['kind'] == 'hallucinate' and 'charm=False' in x.text]
    if not hall:
        return NODATA('沒有幻覺事件（詛咒 3 層／5 層）')
    if '1' not in kinds or '2' not in kinds:
        return FAIL(f'幻覺種類 {kinds}（應有恐懼 1 與瘋狂 2；詛咒 {curse}）', *hall)
    if not vision:
        return EYES('log：詛咒 3 層恐懼、5 層瘋狂；沒看到屍鬼的幻視（charm=False）行；逃跑／互打看畫面', *(hall[:2] + pap[:2]))
    return EYES('log：詛咒 3 層恐懼、5 層瘋狂、屍鬼控不到改幻視；逃跑、互打、屍鬼不逃看畫面', *(hall[:2] + vision[:1] + pap[:2]))


@rule('B-36')
def r_b36(seg, ctx):
    opens = seg.ops(kind='N3_Phantom', op='Apply')
    hurt = [x for x in seg.of('hurt') if x['melee'] == '1']
    if not opens or len(hurt) < 6:
        return NODATA(f'幻影 {len(opens)} 次、被打 {len(hurt)} 下')
    windows = [(o.g, o.g + 3000) for o in opens]
    inside = [x for x in hurt if any(a <= x.g <= b for a, b in windows)]
    outside = [x for x in hurt if x not in inside]
    miss_in = [x for x in inside if x.v('lost', 1) < 0.5]
    miss_out = [x for x in outside if x.v('lost', 1) < 0.5 and x['blocked'] == '0']
    n, k = len(inside), len(miss_in)
    note = f'3 秒內 {n} 擊落空 {k}；3 秒外 {len(outside)} 擊落空 {len(miss_out)}'
    if miss_out:
        return FAIL(note + '（3 秒外也落空）', *miss_out[:3])
    if n >= 4 and (k == 0 or k == n):
        return FAIL(note + '（應零星約三成）', *inside[:4])
    if n < 4:
        return NODATA(note + '（3 秒內的擊太少）', *inside)
    return PASS(note, *(opens[:1] + miss_in[:2] + inside[:2]))


@rule('B-32')
def r_b32(seg, ctx):
    star = seg.ops(kind='N3_Star', op='Apply')
    settle = next((x for x in seg.of('settle') if x['tag'] == 'N3_StarFuse'), None)
    if not star:
        return NODATA('沒有星痕的 op')
    two = next((x for x in star if near(x.v('mag'), 2, 0.01)), None)
    if not two:
        return FAIL('星痕沒到 2 層', *star)
    if not settle:
        return FAIL('停手後沒有引爆（settle N3_StarFuse）', two)
    dmg = next((x for x in seg.ops(op='Damage', el='astral') if x.seq > settle.seq), None)
    gone = next((x for x in seg.ops(kind='N3_Star', op='Remove') if x.seq > settle.seq), None)
    dt = (settle.g - two.g) / 1000.0
    if not dmg or not 15 <= dmg.d('mag') <= 22.5:
        return FAIL('引爆傷害不是約 21（2×10×1.05）', settle, dmg)
    if not gone:
        return FAIL('引爆後星痕還在', settle, dmg)
    return PASS(f'停手 {dt:.1f} 秒引爆，星傷 {dmg["mag"]}（抗性前），星痕清掉', two, settle, dmg, gone)


@rule('B-33')
def r_b33(seg, ctx):
    rows = []
    bad = []
    for el, lo, hi in (('fire', 7.0, 9.5), ('wind', 7.0, 9.5), ('water', 9.0, 11.5), ('astral', 7.0, 9.5)):
        mark = next((x for x in seg.ops(op='Mark', el=el)), None)
        if not mark:
            rows.append(f'{el}: 沒開印')
            bad.append(None)
            continue
        gone = next((x for x in seg.of('remove') if x['tag'] == f'Mark_{el}' and x.seq > mark.seq), None)
        if not gone:
            rows.append(f'{el}: 沒過期')
            bad.append(mark)
            continue
        dt = (gone.g - mark.g) / 1000.0
        rows.append(f'{el}: {dt:.1f} 秒 {gone["reason"]}')
        if gone['reason'] != 'expired' or not lo <= dt <= hi:
            bad.append(gone)
    if any(b is None for b in bad) and len([b for b in bad if b is None]) == 4:
        return NODATA('四個元素都沒開印')
    if bad:
        return FAIL('；'.join(rows), *[b for b in bad if b])
    return PASS('印記上身並過期：' + '；'.join(rows), *seg.ops(op='Mark')[:4])


@rule('B-34')
def r_b34(seg, ctx):
    ends = [x for x in seg.ops(ev='End') if x['reason'] == 'cut']
    frost_end = next((x for x in ends if x['args'] and x['args'].split('|')[0] == '2'), None)
    fire_end = next((x for x in ends if x['args'] and x['args'].split('|')[0] == '1'), None)
    water = seg.procs(el='water', power='0')
    if not frost_end or not fire_end:
        return NODATA(f'冰被切 {bool(frost_end)}、火被切 {bool(fire_end)}')
    after_frost = [p for p in water if frost_end.seq < p.seq and p.g - frost_end.g <= 5000]
    after_fire = [p for p in water if fire_end.seq < p.seq and p.g - fire_end.g <= 5000]
    if not after_frost or not after_fire:
        return NODATA(f'切掉之後 5 秒內的水普攻：冰 {len(after_frost)} 刀、火 {len(after_fire)} 刀')
    hi_frost = [p for p in after_frost if p.d('mag') > 7.36]
    hi_fire = [p for p in after_fire if p.d('mag') > 7.41]
    if hi_fire:
        return FAIL('火被切之後的水附傷超過 7.4', *hi_fire)
    if not hi_frost:
        return FAIL('冰被切之後 5 秒內的水附傷都沒超過 7.35', *after_frost)
    return PASS(f'冰終焉後水附傷 {fmt_nums([p.v("mag") for p in after_frost])}（有超過 7.35）；火被切後 '
                f'{fmt_nums([p.v("mag") for p in after_fire])}（不超過 7.35）', frost_end, *after_frost[:2], fire_end, *after_fire[:2])


@rule('B-37')
def r_b37(seg, ctx):
    burst = seg.of('burst')
    dmg = seg.ops(op='Damage', ctx='burst')
    if not burst:
        return NODATA('沒有融斷（burst）')
    fire = [x for x in dmg if x['el'] == 'fire']
    if not fire:
        return FAIL('融斷沒有火傷', burst[0])
    if not 12.3 <= fire[0].d('mag') <= 12.9:
        return FAIL(f'融斷火傷 {fire[0]["mag"]}（同調 0 段應 12.6；×2 以上＝錯）', burst[0], fire[0])
    unmark = [x for x in seg.ops(op='Unmark') if x.seq > burst[0].seq - 100]
    dumps = [x for x in seg.of('pap') if x['kind'] == 'dump-nearest' and x.seq > fire[0].seq]
    if dumps and dumps[-1]['marks'] != '0':
        return FAIL('關形態之後還有印記', dumps[-1])
    return PASS(f'融斷火傷 {fire[0]["mag"]}（12×1×1.05）' + ('，之後印記 0' if dumps else ''), burst[0], fire[0], *(unmark[:1] + dumps[-1:]))


# ---------------------------------------------------------------- C

def hurt_ops(seg, hurt):
    """The ops the hurt task ran for this hit (ctx=hurt, until the next hurt line)."""
    out = []
    started = False
    for x in seg:
        if x is hurt:
            started = True
            continue
        if not started:
            continue
        if x.kind == 'hurt':
            break
        if x.kind == 'op' and x['ctx'] == 'hurt':
            out.append(x)
    return out


def op_mag(ops, op):
    return sum(x.v('mag', 0) for x in ops if x['op'] == op)


@rule('C-01')
def r_c01(seg, ctx):
    rows = [x for x in seg.of('hurt') if x['form'] == '0' and x['melee'] == '1' and x.v('lost', 0) > 0]
    if len(rows) < 2:
        return NODATA(f'沒開形態時被砍只有 {len(rows)} 下')
    first = None
    for x in rows:
        ops = hurt_ops(seg, x)
        spend = op_mag(ops, 'SpendMagicka')
        if x.v('magickaBefore', 0) > 50 and spend > 0:
            first = (x, spend)
            break
    if not first:
        return FAIL('魔力夠時被砍，沒有扣魔力（法盾沒擋？）', *rows[:3])
    x, spend = first
    expect = x.v('lost') * 0.3 / 0.7
    if not rel(spend, expect, 0.15):
        return FAIL(f'掉血 {x["lost"]}，法盾扣魔 {spend:.2f}（應約 {expect:.2f}＝h×0.3÷0.7）', x, *hurt_ops(seg, x))
    low = next((y for y in rows if y.v('magickaBefore', 99) <= 5), None)
    if not low:
        return NODATA(f'第一下 OK（扣魔 {spend:.2f}／預期 {expect:.2f}）；沒有「魔力只剩 3」的那一下', x)
    unpaid = op_mag(hurt_ops(seg, low), 'HurtHealth')
    if unpaid <= 0:
        return FAIL('魔力不夠的那一下沒有把付不出的部分扣到生命（HurtHealth）', low, *hurt_ops(seg, low))
    return PASS(f'法盾：掉血 {x["lost"]}、扣魔 {spend:.2f}（h×0.3÷0.7＝{expect:.2f}）；魔力不夠時付不出的 {unpaid:.2f} 照扣生命', x, low)


@rule('E-06')
def r_e06(seg, ctx):
    rows = [x for s in ('C-01', 'C-02', 'C-03') for x in ctx.seg(s).of('hurt')]
    if not rows:
        return NODATA('C-01～C-03 的站沒有 hurt 行')
    dup = [(a, b) for a, b in zip(rows, rows[1:]) if a['before'] == b['before'] and a['after'] == b['after'] and abs(b.g - a.g) <= 50]
    if dup:
        return FAIL('同一下出現兩行 hurt', *dup[0])
    return PASS(f'{len(rows)} 下各一行 hurt（before／after／lost 都在）', *rows[:4])


@rule('C-02')
def r_c02(seg, ctx):
    rows = [x for x in seg.of('hurt') if x['form'] == '9' and x['melee'] == '1' and x.v('lost', 0) > 0]
    if not rows:
        return NODATA('水形態被砍的 hurt 行沒有')
    x = rows[0]
    spend = op_mag(hurt_ops(seg, x), 'SpendMagicka')
    expect = x.v('lost') * 0.2 / 0.8 * 1.5
    if not rel(spend, expect, 0.15):
        return FAIL(f'掉血 {x["lost"]}，水幕扣魔 {spend:.2f}（應約 {expect:.2f}＝h×0.2÷0.8×1.5）', x)
    return PASS(f'水幕：掉血 {x["lost"]}、扣魔 {spend:.2f}（預期 {expect:.2f}）', x)


@rule('C-03')
def r_c03(seg, ctx):
    rows = [x for x in seg.of('hurt') if x.v('guardBefore', 0) >= 10]
    if not rows:
        return NODATA('沒有護血池 ≥ 10 時被打的 hurt 行')
    x = rows[0]
    ops = hurt_ops(seg, x)
    pool = [o for o in ops if o['op'] == 'GuardPool']
    unpaid = op_mag(ops, 'HurtHealth')
    died = [d for d in seg.of('death-event') if d.a.get('corpse') and d.a['corpse'].id == PLAYER_ID]
    saved = [p for p in seg.of('pap') if p['kind'] == 'divine' and 'saved=1' in p.text]
    after = next((o for o in seg.of('op-done') if o.seq > x.seq and o.a.get('on') and o.a['on'].id == PLAYER_ID), None)
    if not pool:
        return FAIL('護血池沒扣', x, *ops)
    if unpaid <= 0:
        return FAIL('池不夠的部分沒有扣生命（HurtHealth）', x, *ops)
    if after and near(after.a['on'].h, 1.0, 0.01) and not died and not saved:
        return FAIL('卡在 1 點生命', x, after)
    how = '死亡' if died else '神佑救起' if saved else f'生命剩 {after.a["on"].h:.1f}' if after else '?'
    return PASS(f'池 {x["guardBefore"]} 扣光、其餘 {unpaid:.1f} 照扣生命 → {how}', x, *(pool[:1] + died[:1] + saved[:1]))


@rule('C-04')
def r_c04(seg, ctx):
    node = node_added(seg, '00229D') or node_added(ctx.all, '00229D')
    ov = seg.ops(kind='N4_Overload', op='Apply')
    hurt = next((x for x in seg.of('hurt') if x['spell'] == '1'), None)
    if not hurt:
        return NODATA('沒有被法術打的 hurt 行', node)
    first = next((o for o in ov if o.seq > hurt.seq and o['ctx'] == 'hurt'), None)
    if not first:
        return FAIL('被法術打之後沒有超載', node, hurt)
    original = hurt.v('lost') / 0.7
    if not rel(first.v('mag'), original * 0.3, 0.25):
        return FAIL(f'超載 {first["mag"]}（應約原本傷害 {original:.1f} × 0.3＝{original * 0.3:.1f}）', hurt, first)
    decay = [o for o in ov if o.seq > first.seq and o['ctx'] == 'tick']
    if not decay:
        return NODATA('超載沒看到衰減（等 5 秒以上）', hurt, first)
    wait = (decay[0].g - first.g) / 1000.0
    if wait < 2.5:
        return FAIL(f'超載 {wait:.1f} 秒就開始衰減（應先等 3 秒）', first, decay[0])
    return PASS(f'超載 {first["mag"]}（原本傷害 ×0.3），{wait:.1f} 秒後開始每秒衰減', node, hurt, first, *decay[:2])


REACTIONS = {
    'N4_RetaliateCooldown': '反震', 'N4_ReverseCooldown': '逆電', 'N4_GrudgeCooldown': '怨縛', 'N4_SpellReturnCooldown': '咒返',
    'N4_UnyieldCooldown': '不屈', 'N4_IceHeartCooldown': '冰心', 'N4_SanctuaryCooldown': '庇護', 'N4_RetortCooldown': '灼身／寒反／靜電／毒皮',
    'N4_Afterimage': '殘影', 'N3_Punish': '懲戒',
}


@rule('C-05')
def r_c05(seg, ctx):
    ops = [x for x in seg.ops(op='Apply') if x['ctx'] == 'hurt' and x['kind'] in REACTIONS]
    if not ops:
        return NODATA('沒有受擊反應的 op')
    seen = defaultdict(list)
    bad = []
    for x in ops:
        on = x.a.get('on')
        key = (x['kind'], on.id if on else 0)
        if x['kind'] not in ('N3_Punish', 'N4_Afterimage'):
            for prev in seen[key]:
                if x.g < prev.g + prev.v('sec', 0) * 1000 - 150:
                    bad.append((prev, x))
        seen[key].append(x)
    # same hit twice: two applies of one cooldown between two hurt lines
    for h in seg.of('hurt'):
        kinds = [o['kind'] for o in hurt_ops(seg, h) if o['op'] == 'Apply' and o['kind'] in REACTIONS and o['kind'] != 'N3_Punish']
        if len(kinds) != len(set(kinds)):
            bad.append((h, h))
    punish = [int(round(x.v('mag'))) for x in ops if x['kind'] == 'N3_Punish']
    names = sorted({REACTIONS[k] for k, _ in seen})
    if bad:
        return FAIL('冷卻內又觸發或同一下兩次：' + '、'.join(REACTIONS[a['kind']] for a, b in bad if a.kind == 'op'), *[y for p in bad[:3] for y in p])
    missing = [n for n in ('反震', '殘影', '逆電', '灼身／寒反／靜電／毒皮', '怨縛', '咒返', '不屈', '冰心', '庇護', '懲戒') if n not in names]
    note = '觀察到：' + '、'.join(names) + (f'；懲戒層數 {punish}' if punish else '') + ('；未測：' + '、'.join(missing) if missing else '')
    return PASS(note + '；冷卻內都沒有再觸發、同一下沒有兩次', *ops[:6])


@rule('C-06')
def r_c06(seg, ctx):
    node = node_added(seg, '00200C') or node_added(ctx.all, '00200C')
    rows = [x for x in seg.of('hurt') if x['melee'] == '1' and x.a.get('att')]
    if not rows:
        return NODATA('沒有被近戰砍的 hurt 行', node)
    first = None
    for x in rows:
        ops = hurt_ops(seg, x)
        marks = [o for o in ops if o['op'] == 'Mark' and o['el'] == 'fire']
        dmg = [o for o in ops if o['op'] == 'Damage' and o['el'] == 'fire']
        if marks and dmg:
            first = (x, marks[0], dmg[0])
            break
    if not first:
        return FAIL('被砍時攻擊者沒有掛你的火印記＋火傷', node, *rows[:2])
    x, m, d = first
    again = [y for y in rows if y.seq > x.seq and y.g - x.g < 3000 and any(o['op'] in ('Mark', 'Damage') for o in hurt_ops(seg, y))]
    if again:
        return FAIL('3 秒內第二下又觸發', x, *again)
    if not 11.0 <= d.d('mag') <= 13.5:
        return FAIL(f'灼身火傷 {d["mag"]}（應 B_max × 1.0 左右）', x, d)
    return PASS(f'灼身：攻擊者掛你的火印記、火傷 {d["mag"]}；3 秒內第二下沒反應', node, x, m, d)


@rule('C-07')
def r_c07(seg, ctx):
    rows = [x for x in seg.of('hurt') if x['spell'] == '1' and x.v('dot', 0) > 0]
    if not rows:
        return NODATA('沒有帶持續傷的法術打你（找不到原版法術就標未測）')
    x = rows[0]
    add = op_mag(hurt_ops(seg, x), 'HurtHealth')
    expect = x.v('dot') * 0.3 / 0.7
    if not rel(add, expect, 0.3):
        return FAIL(f'dot={x["dot"]}，補扣 {add:.2f}（應約 {expect:.2f}）', x)
    return PASS(f'dot={x["dot"]}，命中當下補扣 {add:.2f}（dot×0.3÷0.7）', x)


@rule('C-08')
def r_c08(seg, ctx):
    found = [x for x in ctx.all if x.kind == 'raw' and x.text.startswith('[ESSB][load] TrueHUD')]
    ov = seg.ops(kind='N4_Overload', op='Apply')
    return EYES(('log：' + found[0].text.split('] ', 1)[-1] if found else 'log 沒有 TrueHUD 行')
                + f'；超載 {len(ov)} 次。資源條的顏色、位置、停用後不出錯要看畫面', *(found[:1] + ov[:1]))


@rule('C-09')
def r_c09(seg, ctx):
    switch = next((x for x in seg.of('switch') if x['kind'] == 'switch' and x['wanted'] == 'fire'), None)
    if not switch:
        return NODATA('沒有從雷電切到火焰的 switch')
    before = last_before(seg, switch, 'op', lambda x: x['kind'] == 'N4_Charge' and x['op'] == 'Apply')
    cleared = next((x for x in seg.ops(kind='N4_Charge', op='Remove') if x.seq > switch.seq), None)
    end = next((x for x in seg.ops(ev='End') if x.seq > switch.seq and x['reason'] == 'cut' and (x['args'] or '').startswith('3|')), None)
    dis = next((x for x in seg.ops(ev='Discharge') if end and x.seq > end.seq), None)
    close = next((x for x in seg.of('switch') if x['kind'] == 'close' and x.seq > switch.seq), None)
    if not cleared:
        return FAIL('切換後電荷還在（沒點過載終焉）', before, switch)
    if not end or not dis:
        return FAIL('火焰切掉雷印記沒有放電', switch, end)
    charges = dis['args'].split('|')[0] if dis['args'] else '?'
    if close:
        after = [x for x in seg.ops(op='Remove') if x.seq > close.seq and x['kind'] in ('N4_Sync', 'N4_RockArmor', 'N4_WindGauge', 'N4_IceShield', 'N4_StoredForce')]
        sync = [x for x in seg.ops(kind='N4_Sync') if x.seq > close.seq]
        if not sync:
            return FAIL('按 Z 後同調沒歸零', close)
        return PASS(f'切換清電荷；雷終焉用 {charges} 格放電；Z 後同調與資源清掉（{len(after)} 個 Remove）', before, switch, cleared, end, dis, close)
    return PASS(f'切換清電荷；雷終焉用 {charges} 格放電（這一站沒按 Z）', before, switch, cleared, end, dis)


# ---------------------------------------------------------------- D

def scan_groups(seg):
    """[(scan head, [scan-c rows])] in order."""
    out = []
    for x in seg:
        if x.kind == 'scan':
            out.append((x, []))
        elif x.kind == 'scan-c' and out:
            out[-1][1].append(x)
    return out


def untouchable(seg):
    """Actor ids a range effect must never hit: allies and neutrals of this station's scans."""
    ids = set()
    for head, rows in scan_groups(seg):
        for r in rows:
            who = r.a.get('who')
            if who and r['verdict'] in ('ally', 'neutral', 'ally-far', 'ally-over-limit'):
                ids.add(who.id)
    return ids


HARM = ('Damage', 'Mark', 'PoisonDot', 'BleedDot', 'Slow', 'DrainStamina', 'DrainMagicka', 'Silence', 'Hush', 'Timed', 'Apply')


def harmed(seg, ids):
    out = []
    for x in seg.ops():
        on = x.a.get('on')
        if on and on.id in ids and x['who'] == 'target' and x['op'] in HARM and x['ctx'] not in ('form-second',):
            out.append(x)
    return out


BMAX = {'fire': 12, 'frost': 10, 'shock': 25, 'earth': 10, 'wind': 9, 'blood': 10, 'divine': 10, 'poison': 9, 'water': 7, 'dark': 10, 'astral': 10}


def burst_damage(seg, el):
    return [x for x in seg.ops(op='Damage', ctx='burst') if x['el'] == el]


@rule('D-01')
def r_d01(seg, ctx):
    rows = []
    bad = []
    for el in ('fire', 'frost', 'shock', 'earth'):
        d = burst_damage(seg, el)
        if not d:
            rows.append(f'{el}: 沒有')
            continue
        want = BMAX[el] * 1.05
        rows.append(f'{el}: {d[0]["mag"]}（{want:.2f}）')
        if not rel(d[0].d('mag'), want, 0.03):
            bad.append(d[0])
    hurt_allies = harmed(seg, untouchable(seg))
    down = [x for x in seg.ops(kind='N3_Downed', op='Apply') if x['ctx'] == 'burst']
    if all('沒有' in r for r in rows):
        return NODATA('沒有融斷傷害')
    if bad or hurt_allies or down:
        return FAIL('；'.join(rows) + ('；打到隨從／路人' if hurt_allies else '') + ('；土融斷讓人跌倒' if down else ''), *(bad + hurt_allies + down)[:6])
    return PASS('融斷 B_max×1.05：' + '；'.join(rows) + '；隨從路人沒事、土不跌倒', *[burst_damage(seg, e)[0] for e in ('fire', 'frost', 'shock', 'earth') if burst_damage(seg, e)])


@rule('D-02')
def r_d02(seg, ctx):
    rows, bad, ev = [], [], []
    for el in ('wind', 'blood', 'divine', 'poison', 'water', 'dark', 'astral'):
        d = burst_damage(seg, el)
        if not d:
            rows.append(f'{el}: 沒有')
            continue
        x = d[0]
        ev.append(x)
        want = BMAX[el] * 1.05
        lo, hi = want * 0.97, want * (1.35 if el == 'blood' else 1.25 if el == 'divine' else 1.03)
        rows.append(f'{el}: {x["mag"]}')
        if not lo <= x.d('mag') <= hi:
            bad.append(x)
    heal = [x for x in seg.ops(op='Heal', ctx='burst')]
    guided = [x for x in seg.ops(kind='N3_Guided', op='Apply') if x['ctx'] == 'burst']
    hush = [x for x in seg.ops(op='Hush', ctx='burst')]
    push = seg.ops(ev='Push', ctx='burst')
    curse = [x for x in seg.ops(kind='N3_DeathCurse', op='Apply') if x['ctx'] == 'burst']
    cat = [x for x in seg.ops(kind='N3_Catalyzed', op='Apply') if x['ctx'] == 'burst']
    if all('沒有' in r for r in rows):
        return NODATA('沒有融斷傷害')
    notes = '；'.join(rows) + f'；推 {len(push)}、死咒 {len(curse)}、催毒 {len(cat)}、寂 {len(hush)}'
    if bad or heal or guided or not hush:
        why = ('；聖融斷有回血' if heal else '') + ('；水融斷掛了導引' if guided else '') + ('；沒有寂' if not hush else '')
        return FAIL(notes + why, *(bad + heal + guided)[:6])
    return EYES(notes + '；風被吹上天、目標身上的寂（畫面看不到）照 log', *(ev[:4] + push[:1] + hush[:1]))


@rule('D-03')
def r_d03(seg, ctx):
    d = burst_damage(seg, 'frost')
    node = node_added(seg, '002069') or node_added(ctx.all, '002069')
    if not d:
        return NODATA('沒有冰融斷')
    first = d[0]
    if not rel(first.d('mag'), 31.5, 0.03):
        return FAIL(f'三段冰融斷 {first["mag"]}（應 31.5＝10×3×1.05）', first)
    before = [x for x in seg.ops(ev='Shatter', ctx='burst') if not node or x.seq < node.seq]
    if before:
        return FAIL('沒有冰封融斷也碎冰', first, *before)
    shatter = [x for x in seg.ops(ev='Shatter', ctx='burst') if node and x.seq > node.seq]
    if not shatter:
        return NODATA('第一段 OK；加了冰封融斷後沒有碎冰', first, node)
    rows = []
    for s in shatter:
        dmg = next((x for x in seg.ops(op='Damage', ctx='burst', el='frost') if x.seq > s.seq), None)
        on = s.a.get('on')
        if dmg and on:
            rows.append((s, dmg, dmg.d('mag') / on.hmax))
    if not rows:
        return NODATA('碎冰後沒有傷害 op', *shatter)
    fracs = [f for s, dmg, f in rows]
    if not any(near(f, 0.20, 0.02) for f in fracs):
        return FAIL(f'碎冰比例 {fmt_nums(fracs, 3)}（一般 0.20、首領 0.10，不乘 3）', *[r[1] for r in rows])
    return PASS(f'沒有節點只打 31.5、仍冰封；冰封融斷碎冰 {fmt_nums(fracs, 3)} 的最大生命', first, node, *[r[1] for r in rows])


@rule('D-04')
def r_d04(seg, ctx):
    div = burst_damage(seg, 'divine')
    ast = burst_damage(seg, 'astral')
    if not div or not ast:
        return NODATA(f'聖融斷 {len(div)}、星融斷 {len(ast)}')
    d = div[0]
    if not rel(d.d('mag'), 37.8, 0.03):
        return FAIL(f'三段聖融斷 {d["mag"]}（應 37.8，不是 75.6）', d)
    extra = [x for x in ast if x is not ast[0]]
    if not rel(ast[0].d('mag'), 31.5, 0.03):
        return FAIL(f'三段星融斷 {ast[0]["mag"]}（應 31.5）', ast[0])
    if extra and not any(15 <= x.d('mag') <= 22.5 for x in extra):
        return FAIL('星痕引爆不是約 21（乘了 3？）', *extra)
    return PASS(f'聖 {d["mag"]}、星 {ast[0]["mag"]}' + (f' ＋ 引爆 {extra[0]["mag"]}' if extra else ''), d, ast[0], *extra[:1])


@rule('D-05')
def r_d05(seg, ctx):
    groups = [(h, rows) for h, rows in scan_groups(seg) if h['ctx'] == 'burst']
    if not groups:
        return NODATA('沒有融斷的掃描行')
    out = []
    for h, rows in groups:
        far = [r for r in rows if r.a.get('who') and 1050 <= r.v('d_you', 0) <= 1300]
        for r in far:
            out.append((h, r))
    if len(out) < 3:
        return NODATA(f'16～17 公尺的 NPC 只出現在 {len(out)} 次融斷掃描（三次：無節點、收束、冷寂 5 點）', *[h for h, rows in groups[:3]])
    verdicts = [r['verdict'] for h, r in out]
    if verdicts[0] == 'picked':
        return FAIL('17 公尺、沒有收束也被融斷', out[0][1])
    if verdicts[1] != 'picked' or verdicts[2] != 'picked':
        return FAIL(f'收束／冷寂時沒被融斷：{verdicts}', *[r for h, r in out[:3]])
    return PASS(f'17 公尺：無節點 {verdicts[0]}、收束 picked；16 公尺冷寂 5 點 picked（半徑 {out[2][0]["aroundYou"]}）', *[r for h, r in out[:3]])


@rule('D-06')
def r_d06(seg, ctx):
    drains = seg.ops(op='DrainMagicka', ctx='burst')
    if not drains:
        return NODATA('融斷沒有燒魔（寂每層燒魔）')
    d = drains[0]
    on = d.a.get('on')
    want = on.mmax * 0.15 if on else None
    if not rel(d.v('mag'), want, 0.08):
        return FAIL(f'寂 2 層燒魔 {d["mag"]}（應最大魔力 15%＝{want:.1f}）', d)
    trues = [x for x in seg.ops(op='Damage', ctx='burst') if x['el'] == 'none']
    cleaned = [x for x in seg.ops(ctx='burst') if (x['op'] == 'PoisonDot' and x.v('mag', 1) == 0) or (x['op'] == 'Remove' and x['kind'] == 'N3_Curse')]
    if not trues or not cleaned:
        return EYES(f'① 燒魔 {d["mag"]}（15%）OK；② 萬寂的清除（中毒、詛咒各受一次真傷）沒在 log 找到', d)
    return PASS(f'① 燒魔 {d["mag"]}（15%）；② 萬寂清 {len(cleaned)} 種、真傷 {fmt_nums([x.v("mag") for x in trues])}', d, *(cleaned[:2] + trues[:2]))


@rule('D-07')
def r_d07(seg, ctx):
    ids = untouchable(seg)
    if not ids:
        return NODATA('掃描裡沒有隨從或路人（他們要站在 NPC 2 公尺內）')
    bad = harmed(seg, ids)
    if bad:
        return FAIL('放電／雷殛／中毒擴散打到隨從或路人', *bad)
    effects = seg.ops(ev='Discharge') + seg.ops(op='PoisonDot', ctx='death')
    return PASS(f'隨從與路人（{len(ids)} 名）沒被任何範圍效果打到', *effects[:4])


@rule('D-08')
def r_d08(seg, ctx):
    deaths = seg.of('death')
    if not deaths:
        return NODATA('沒有死亡')
    rows, bad = [], []
    for dl in deaths:
        corpse = dl.a.get('corpse')
        ash = [x for x in seg.ops(ev='Ash', ctx='death') if x.seq > dl.seq and x.a.get('on') and corpse and x.a['on'].id == corpse.id]
        mana = [x for x in seg.ops(op='RestoreMagicka', ctx='death') if x.seq > dl.seq]
        rows.append(f'{corpse} essential={dl["essential"]} 化灰={bool(ash)}')
        if dl['essential'] == '1' and ash:
            bad.append(dl)
        if dl['essential'] == '0' and (not ash or not mana or not near(mana[0].v('mag'), 20, 0.5)):
            bad.append(dl)
    pap = [x for x in seg.of('pap') if x['kind'] == 'ash']
    if bad:
        return FAIL('；'.join(rows), *bad)
    return EYES('；'.join(rows) + '；化灰外觀與 essential 倒下不死看畫面', *(deaths[:3] + pap[:2]))


@rule('D-09')
def r_d09(seg, ctx):
    raises = seg.ops(ev='Raise', ctx='death')
    if not raises:
        return NODATA('沒有亡者歸來事件')
    rows = []
    bad = []
    for r in raises:
        a = [float(v) for v in r['args'].split('|')]
        dl = last_before(seg, r, 'death')
        level = int(dl['level']) if dl else None
        want = 240 if level is not None and level <= 13 else 360
        rows.append(f'等級 {level} 秒數 {a[2]:.0f}（{want}）攻擊 +{a[3]:.1f}')
        if not near(a[2], want, 1) or not near(a[3], 0.5, 0.01):
            bad.append(r)
    pap = [x for x in seg.of('pap') if x['kind'] in ('raise', 'raised')]
    if bad:
        return FAIL('；'.join(rows), *bad)
    return EYES('；'.join(rows) + '；站起來、第二次復生、結束後回 1.0 看畫面', *(raises[:2] + pap[:2]))


@rule('D-10')
def r_d10(seg, ctx):
    node = node_added(seg, '0021B0')
    dots = seg.ops(op='PoisonDot', ctx='death')
    if not dots:
        return NODATA('死亡時沒有中毒擴散')
    before = [x for x in dots if not node or x.seq < node.seq]
    after = [x for x in dots if node and x.seq > node.seq]
    bad = [x for x in before if not (rel(x.d('mag'), 20, 0.2) and 19 <= x.v('sec') <= 25)]
    bad += [x for x in after if not (rel(x.d('mag'), 20, 0.2) and 30 <= x.v('sec') <= 38)]
    far = []
    for h, rows in scan_groups(seg):
        for r in rows:
            if r.v('d_centre', 0) > 1050 and r['verdict'] == 'picked':
                far.append(r)
    if bad or far:
        return FAIL('擴散的強度／秒數不對，或 15 公尺外的也中', *(bad + far)[:6])
    return PASS(f'15 公尺內各中毒（每秒 {fmt_nums([x.v("mag") for x in before[:2]])}、{fmt_nums([x.v("sec") for x in before[:2]], 0)} 秒）'
                + (f'；蔓延後 {fmt_nums([x.v("sec") for x in after[:2]], 0)} 秒' if after else '；（蔓延未測）'), *(before[:2] + after[:2]))


@rule('D-11')
def r_d11(seg, ctx):
    frozen = [x for x in seg.ops(kind='N3_Freeze', op='Apply') if x['ctx'] == 'death']
    fire = [x for x in seg.ops(op='Damage', ctx='death') if x['el'] == 'fire']
    fear = [x for x in seg.ops(ev='Hallucinate', ctx='death')]
    rows = f'連鎖冰封 {len(frozen)}、火葬 {len(fire)}、亡魂 {len(fear)}'
    if not (frozen and fire and fear):
        return FAIL(rows + '（少一項）', *(frozen[:1] + fire[:1] + fear[:1])) if (frozen or fire or fear) else NODATA(rows)
    return PASS(rows, frozen[0], fire[0], fear[0])


@rule('D-12')
def r_d12(seg, ctx):
    und = [x for x in seg.ops(kind='N5_UndyingCooldown', op='Apply') if x['ctx'] == 'death']
    deaths = seg.of('death')
    if not deaths:
        return NODATA('沒有死亡')
    if not und:
        return FAIL('不死沒觸發', *deaths[:2])
    if len(und) > 1 and (und[1].g - und[0].g) < 30000:
        return FAIL('30 秒內不死觸發兩次', *und)
    after = next((x for x in seg if x.seq and x.seq > und[0].seq and x.kind == 'second'), None)
    h = after.a['you'].h if after else None
    thirst = seg.ops(kind='N3_Bloodthirst', op='Apply')
    if h is not None and not 440 <= h <= 520:
        return FAIL(f'不死＋飲血後生命 {h:.0f}（應約 501）', und[0], after)
    return PASS(f'不死一次（30 秒內第二次沒觸發）、之後生命 {h if h is None else round(h)}、嗜血 {len(thirst)}', und[0], after, *thirst[:1])


@rule('D-13')
def r_d13(seg, ctx):
    node = node_added(seg, '00201C') or node_added(ctx.all, '00201C')
    hits = [x for x in seg.ops(op='Damage', ctx='hit') if x['el'] == 'fire' and x['at'] != '0']
    if not hits:
        return NODATA('開火印時旁邊的人沒吃火傷', node)
    ids = {x.a['on'].id for x in hits if x.a.get('on')}
    bad = [x for x in hits if not 10.4 <= x.d('mag') <= 12.7]
    if len(ids) != 5 or bad:
        return FAIL(f'吃到火附傷的有 {len(ids)} 人（應最近 5 人），強度 {fmt_nums([x.v("mag") for x in hits])}', *hits)
    return PASS(f'最近 5 人各吃一次火附傷 {fmt_nums([x.v("mag") for x in hits])}', node, *hits[:5])


@rule('D-14')
def r_d14(seg, ctx):
    # Round 28b (F5, the user's ruling 2026-09-28): 印潮 -- the first hit after switching to water opened its mark on an
    # unmarked NPC; the 2 nearest OTHER unmarked NPCs within 15 m get the water mark too (ctx=hit, at != 0); the two carrying
    # a fire mark keep it (no water on them, no fire mark removed: D1). 雙斷 opens on the targets the burst cleared.
    tide = [x for x in seg.ops(op='Mark', el='water') if x['ctx'] == 'hit' and x['at'] != '0']
    fire = {x.a['on'].id for x in seg.ops(op='Mark', el='fire') if x.a.get('on')}
    cut = [x for x in seg.ops(op='Unmark', el='fire') if x['ctx'] == 'hit' and x['at'] != '0']
    double = [x for x in seg.ops(op='Mark', el='frost') if x['ctx'] == 'enter']
    crit = [x for x in seg.ops(op='Slow') if x['ctx'] == 'enter' and near(x.v('mag'), 30, 0.01)]
    allies = harmed(seg, untouchable(seg))
    tide_ids = {x.a['on'].id for x in tide if x.a.get('on')}
    rows = f'印潮 {len(tide_ids)} 人、雙斷 {len(double)} 人、臨界 {len(crit)} 人'
    if allies:
        return FAIL(rows + '；碰到隨從', *allies)
    if tide_ids & fire or cut:
        return FAIL(rows + '（印潮只掛在身上沒有印記的人：帶火印記的被掛了水印或被切掉）', *(tide[:2] + cut[:2]))
    if len(tide_ids) > 2:
        return FAIL(rows + '（印潮最多 2 人）', *tide[:3])
    if not tide_ids:
        return FAIL(rows + '（切到水後第一擊開印，旁邊沒印記的人應被掛上水印記）') if double or crit else NODATA(rows)
    if not double or not crit or len(crit) > 5:
        return FAIL(rows + '（臨界最多 5 人）', *(double[:1] + crit[:1])) if (double or crit) else NODATA(rows)
    return PASS(rows + '（印潮只掛沒有印記的人、最多 2 人）', *(tide[:2] + double[:1] + crit[:1]))


@rule('D-15')
def r_d15(seg, ctx):
    deaths = seg.of('death')
    if len(deaths) < 5:
        return NODATA(f'只有 {len(deaths)} 名死者')
    ids = [x.a['corpse'].id for x in deaths if x.a.get('corpse')]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    if dup:
        return FAIL('同一名死者有兩行 [death]', *[x for x in deaths if x.a['corpse'].id in dup])
    return EYES(f'{len(deaths)} 名死者各一行 [death]；畫面卡不卡要看', *deaths[:5])


@rule('E-07')
def r_e07(seg, ctx):
    ev = seg.of('death-event')
    if not ev:
        return NODATA('沒有 death-event')
    zero = [x for x in ev if x['dead'] == '0']
    bad = [x for x in zero if x.v('ours', 0) == 0 and x['killerYou'] == '1' and x.a.get('corpse') and x.a['corpse'].id != PLAYER_ID]
    deaths = seg.of('death')
    ids = [x.a['corpse'].id for x in deaths if x.a.get('corpse')]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    if dup:
        return FAIL('同一死者兩行 [death]', *deaths)
    if bad:
        return FAIL('dead=0 那行 ours=0（效果已經不在）', *bad)
    kinds = ', '.join(f'{x.a.get("corpse")} dead={x["dead"]} ours={x["ours"]} killer={x.a.get("killer")}' for x in ev[:6])
    return PASS('死亡事件：' + kinds, *ev[:6])


@rule('D-16')
def r_d16(seg, ctx):
    sneak = seg.ops(ev='Sneak', ctx='death')
    streak = seg.ops(kind='N3_KillStreak', op='Apply')
    used = seg.ops(kind='N3_KillStreak', op='Remove')
    restore = [x for x in seg.ops(ctx='death') if x['op'] in ('RestoreMagicka', 'RestoreStamina')]
    over = [x for x in seg.ops(kind='N4_Overload', op='Apply') if x['ctx'] == 'death']
    rows = f'連殺 Sneak {len(sneak)}、視窗 {len(streak)}、用掉 {len(used)}；無魔回復 {len(restore)}、超載 {len(over)}'
    if not sneak or not streak:
        return FAIL(rows, *(sneak + streak)[:3]) if (restore or over) else NODATA(rows)
    after = [p for p in seg.procs(el='wind', sneak='1') if p.seq > streak[0].seq]
    if after and not used:
        return FAIL(rows + '；下一次潛行沒有用掉 ×2', streak[0], after[0])
    if not restore:
        return EYES(rows + '；無魔未測；5 秒不被發現看畫面', *(sneak[:1] + streak[:1] + used[:1]))
    return EYES(rows + '；5 秒不被發現看畫面', *(sneak[:1] + streak[:1] + used[:1] + restore[:2] + over[:1]))


@rule('B-09')
def r_b09(seg, ctx):
    node = node_added(seg, '00200D') or node_added(ctx.all, '00200D')
    src = [x for x in seg.of('fire-source') if x['bath'] == '1']
    heals = [x for x in seg.ops(op='Heal') if x['ctx'] == 'tick']
    if not src:
        return NODATA('沒有白熱的火源行（bath=1）', node)
    n = int(src[0]['hostiles'])
    want = 12 * 0.1 * n
    if not heals:
        return FAIL(f'白熱第一秒燒到 {n} 人，之後沒有回血', src[0])
    bad = [x for x in heals if not near(x.v('mag'), want, 0.06)]
    away = [x for x in heals if last_before(seg, x, 'fire-source') and last_before(seg, x, 'fire-source')['hostiles'] == '0']
    if bad:
        return FAIL(f'回血 {fmt_nums([x.v("mag") for x in heals[:5]])}（應固定 {want:.2f}＝12×0.1×{n}）', src[0], *bad[:3])
    note = f'；走開後照回 {len(away)} 秒' if away else '；（沒看到走開後的秒）'
    return PASS(f'白熱第一秒 {n} 人 → 每秒回 {want:.2f}，共 {len(heals)} 秒' + note, node, src[0], *heals[:2], *away[:1])


def domain_life(seg, el):
    new = [x for x in seg.of('domain-new') if x['el'] == el]
    out = []
    for n in new:
        gone = next((x for x in seg.of('domain-gone') if x['ref'] == n['ref'] and x.seq > n.seq), None)
        out.append((n, gone, (gone.g - n.g) / 1000.0 if gone else None))
    return out


@rule('D-17')
def r_d17(seg, ctx):
    fire = domain_life(seg, 'fire')
    frost = domain_life(seg, 'frost')
    if not fire or not frost:
        return NODATA(f'火域 {len(fire)} 個、冰原 {len(frost)} 個')
    you = seg.of('domain-you')
    ext = [x for x in seg.ops(kind='N3_Heat3', op='Apply') if x['ctx'] == 'tick']
    entries = 0
    inside_prev = False
    last_g = None
    for x in seg:
        if x.kind == 'second':
            inside = any(y for y in you if y.g == x.g and 'fire' in (y['inside'] or ''))
            if inside and not inside_prev:
                entries += 1
            inside_prev = inside
    immune = [x for x in seg.ops(kind='N6_FrostDomainPlayer', op='Apply')]
    slows = [x for x in seg.ops(op='Slow', ctx='domain-enemy')]
    bad = []
    if len(ext) > max(entries, 1):
        bad.append(f'火域白熱引信加了 {len(ext)} 次（進入 {entries} 次）')
    if not immune:
        bad.append('你在冰原裡沒有免疫減速')
    if not slows or any(not near(x.v('mag'), 50, 0.01) for x in slows):
        bad.append('冰原裡的敵人沒有減速 50%')
    life = [t for n, g, t in fire + frost if t]
    if bad:
        return FAIL('；'.join(bad), *(ext[:2] + immune[:1] + slows[:2]))
    return PASS(f'火域引信 +5 秒 {len(ext)} 次（進入 {entries} 次）；冰原裡你免疫減速、敵人減速 50%；領域壽命 {fmt_nums(life, 1)} 秒',
                fire[0][0], *(ext[:1] + immune[:1] + slows[:1]))


@rule('A-17')
def r_a17(seg, ctx):
    cap = [x for x in seg.of('mcm') if x['global'] == 'ESSB_SlowCapPct']
    if not cap:
        return NODATA('沒有 set ESSB_SlowCapPct 的 mcm 行')
    thirty = next((x for x in cap if near(x.v('new'), 30, 0.01)), None)
    back = next((x for x in cap if thirty and x.seq > thirty.seq and near(x.v('new'), 70, 0.01)), None)
    slows = [x for x in seg.ops(op='Slow') if thirty and x.seq > thirty.seq and (not back or x.seq < back.seq)]
    if not slows:
        return NODATA('上限 30 時沒有減速的 op', thirty)
    over = [x for x in slows if x.v('cast_mag', 0) > 30.001]
    if over:
        return FAIL('上限 30 時減速超過 30%', *over)
    return PASS(f'上限 30 時減速都 ≤ 30（{fmt_nums([x.v("cast_mag") for x in slows[:4]])}）' + ('；已改回 70' if back else ''), thirty, *slows[:2], back)


@rule('D-18')
def r_d18(seg, ctx):
    rows, bad, ev = [], [], []
    for el, wants in (('blood', {'Heal': 20}), ('divine', {'Heal': 25, 'RestoreMagicka': 20}), ('water', {'Heal': 15, 'RestoreStamina': 15})):
        inside = [y for y in seg.of('domain-you') if el in (y['inside'] or '').split(',')]
        if not inside:
            rows.append(f'{el}: 沒站進去')
            continue
        gs = {y.g for y in inside}
        for op, want in wants.items():
            got = [x for x in seg.ops(op=op, ctx='tick') if x.g in gs]
            ok = [x for x in got if near(x.v('mag'), want, 0.6)]
            rows.append(f'{el} {op} {len(ok)}/{len(inside)} 秒')
            ev += ok[:1]
            if not ok:
                bad.append(inside[0])
    lives = {el: [t for n, g, t in domain_life(seg, el) if t] for el in ('blood', 'divine', 'water')}
    cleanse = seg.ops(ev='Cleanse')
    if all('沒站進去' in r for r in rows):
        return NODATA('沒站進任何領域')
    note = '；'.join(rows) + '；壽命 ' + '、'.join(f'{k} {fmt_nums(v, 1)}' for k, v in lives.items() if v) + f'；潮池洗淨 {len(cleanse)}'
    if bad:
        return FAIL(note, *bad)
    div = lives.get('divine') or []
    if div and not any(near(t, 5, 1.2) for t in div) and not any(near(t, 8, 1.2) for t in div):
        return FAIL(note + '（聖域應 5 秒、神聖領域 8 秒）', *seg.of('domain-new')[:2])
    return PASS(note, *ev[:4])


@rule('D-19')
def r_d19(seg, ctx):
    hurt = [x for x in seg.of('hurt') if x['melee'] == '1' and x.v('lost', 0) > 0 and x.a.get('att')]
    inside_ids = defaultdict(set)
    for y in seg.of('domain-in'):
        if y['el'] == 'divine' and y.a.get('who'):
            inside_ids[y.g // 1000].add(y.a['who'].id)
    inside, outside = [], []
    for h in hurt:
        sec = h.g // 1000
        ids = inside_ids.get(sec, set()) | inside_ids.get(sec - 1, set())
        (inside if h.a['att'].id in ids else outside).append(h.v('lost'))
    if len(inside) < 3 or len(outside) < 3:
        return NODATA(f'聖域內 {len(inside)} 下、外 {len(outside)} 下')
    r = statistics.mean(inside) / statistics.mean(outside)
    weak = [x for x in seg.of('apply') if 'Divine' in spell_name(ctx, int(x['spell'], 16))]
    if not 0.7 <= r <= 0.9:
        return FAIL(f'裡面／外面＝{r:.3f}（應約 0.8）', *hurt[:6])
    return EYES(f'近戰裡面／外面＝{r:.3f}（約 0.8）；減弱效果上身 {len(weak)} 次；火球的比例只記錄、getav 看畫面', *(hurt[:4] + weak[:2]))


@rule('D-20')
def r_d20(seg, ctx):
    earth = [x for x in seg.of('apply') if (x['tag'] or '') == 'N6_DomainEarth']
    knock = seg.ops(ev='Knock', ctx='domain-enemy')
    poison = seg.ops(op='PoisonDot', ctx='domain-enemy')
    dark = [x for x in seg.ops(op='Damage', ctx='domain-enemy') if x['el'] == 'dark']
    astral = [x for x in seg.of('apply') if (x['tag'] or '') == 'N3_DomainAstral']
    rows = f'地裂標記 {len(earth)}、跌倒 {len(knock)}、毒霧加劑 {len(poison)}、死域暗傷 {len(dark)}、星域標記 {len(astral)}'
    bad = [x for x in dark if not (4.9 <= x.d('mag') <= 6.7)]
    per = defaultdict(list)
    for k in knock:
        per[k.a['on'].id if k.a.get('on') else 0].append(k.g)
    fast = [ts for ts in per.values() if any(b - a < 8000 for a, b in zip(ts, ts[1:]))]
    if not (earth or knock or poison or dark or astral):
        return NODATA(rows)
    if bad or fast:
        return FAIL(rows + ('；死域每秒不是 5.25（夜 6.3）' if bad else '') + ('；同一目標 8 秒內跌兩次' if fast else ''), *(bad[:3] + knock[:2]))
    return PASS(rows, *(earth[:1] + knock[:1] + poison[:1] + dark[:1] + astral[:1]))


@rule('E-11')
def r_e11(seg, ctx):
    doms = [x for x in seg.of('domain') if x['el'] == 'dark']
    if not doms:
        return NODATA('沒有死域的 domain 行')
    ins = [x for x in seg.of('domain-in') if x['el'] == 'dark']
    friendly = defaultdict(list)
    for y in ins:
        if y['hostile'] == '0' and y.a.get('who'):
            friendly[y.a['who'].id].append(y.a['who'].h)
    lost = {k: v[0] - min(v) for k, v in friendly.items() if v}
    bad = [k for k, d in lost.items() if d > 0.5]
    per_sec = defaultdict(set)
    for d in doms:
        per_sec[d.g // 1000].add(d['ref'])
    most = max(len(v) for v in per_sec.values())
    if bad:
        return FAIL('死域裡的路人／隨從掉血', *[y for y in ins if y.a.get('who') and y.a['who'].id in bad][:4])
    return PASS(f'死域每秒一行（最多同時 {most} 個）；非敵對 {len(friendly)} 名沒掉血；lifetime={doms[0]["lifetime"]} radius={doms[0]["radius"]}',
                doms[0], *ins[:3])


@rule('D-21')
def r_d21(seg, ctx):
    ins = seg.of('domain-in')
    friendly = defaultdict(list)
    for y in ins:
        if y['hostile'] == '0' and y.a.get('who'):
            friendly[y.a['who'].id].append(y)
    fire = [x for x in seg.of('domain') if x['el'] == 'fire']
    per_sec = defaultdict(set)
    for d in fire:
        per_sec[d.g // 1000].add(d['ref'])
    most = max((len(v) for v in per_sec.values()), default=0)
    harmed_f = [y for rows in friendly.values() for y in rows[1:] if y.a['who'].h < rows[0].a['who'].h - 0.5]
    slowed = [x for x in seg.ops(op='Slow') if x.a.get('on') and x.a['on'].id in friendly]
    if not friendly and not fire:
        return NODATA('沒有 domain-in／火域行')
    if harmed_f or slowed:
        return FAIL('隨從／路人在領域裡掉血或被減速', *(harmed_f + slowed)[:4])
    if most < 5:
        return FAIL(f'火域最多同時 {most} 個（應 5 個）', *fire[:5])
    return PASS(f'隨從路人 {len(friendly)} 名在領域裡沒掉血沒減速；火域同時 {most} 個', *(fire[:5] + list(friendly.values())[0][:1] if friendly else fire[:5]))


@rule('E-12')
def r_e12(seg, ctx):
    fire = [x for x in seg.of('domain') if x['el'] == 'fire']
    ready = [x for x in seg.of('trace') if 'game-ready' in x.text]
    if not fire:
        return NODATA('沒有火域的 domain 行')
    per_sec = defaultdict(set)
    for d in fire:
        per_sec[d.g // 1000 if not ready or d.seq < ready[-1].seq else ('after', d.g // 1000)].add(d['ref'])
    before = max((len(v) for k, v in per_sec.items() if not isinstance(k, tuple)), default=0)
    after = max((len(v) for k, v in per_sec.items() if isinstance(k, tuple)), default=0)
    if before < 5:
        return FAIL(f'讀檔前 domains 最多 {before} 個（應 5）', *fire[:5])
    if after > 5:
        return FAIL(f'讀檔後 domains {after} 個（同一個 hazard 算了兩次）', *fire[-5:])
    return PASS(f'讀檔前 5 個；讀檔後最多 {after} 個' + ('' if ready else '（這一站沒讀檔）'), *(fire[:2] + ready[-1:]))


@rule('D-22')
def r_d22(seg, ctx):
    ready = [x for x in seg.of('trace') if 'game-ready' in x.text]
    if not ready:
        return NODATA('這一站沒有讀檔（trace game-ready）')
    after = [x for x in seg if x.seq and x.seq > ready[-1].seq and x.kind in ('second', 'domain', 'proc', 'switch')]
    fault = [x for x in ctx.all if x.kind == 'raw' and '[ESSB][fault]' in x.text]
    if fault:
        return FAIL('DLL 故障', *fault)
    if not after:
        return FAIL('讀檔後 DLL 沒有動靜（沒有 second／domain 行）', ready[-1])
    return PASS(f'讀檔後照常（{len(after)} 行活動），沒有故障', ready[-1], *after[:2])


@rule('D-23')
def r_d23(seg, ctx):
    rows = seg.of('spread')
    miasma = [x for x in rows if x['kind'] == 'miasma']
    if not miasma:
        return NODATA('沒有瘴氣擴散（A 要 5 劑以上、旁邊 3 公尺內有敵人）')
    you = [x for x in rows if x.a.get('to') and x.a['to'].id == PLAYER_ID]
    you_ops = [x for x in seg.ops(ctx='spread') if x['who'] == 'you']
    bad = [x for x in miasma if not (0.49 <= x.v('doses') <= 1.6)]
    far = [x for x in miasma if x.v('d', 0) > 215]
    if you or you_ops or bad or far:
        return FAIL('瘴氣傳到你身上、劑量不對或超過 3 公尺', *(you + you_ops + bad + far)[:4])
    plague = [x for x in rows if x['kind'] == 'plague']
    return PASS(f'瘴氣每秒 {fmt_nums([x.v("doses") for x in miasma[:3]])} 劑、都在 3 公尺內的敵人；瘟疫 {len(plague)} 次', *miasma[:3], *plague[:1])


@rule('D-24')
def r_d24(seg, ctx):
    rows = [x for x in seg.of('mcm') if x['global'] == 'ESSB_Enabled']
    off = next((x for x in rows if near(x.v('new'), 0, 0.01)), None)
    on = next((x for x in rows if off and x.seq > off.seq and near(x.v('new'), 1, 0.01)), None)
    if not off:
        return NODATA('沒有總開關關掉的 mcm 行')
    end = on.seq if on else 1 << 62
    during = [x for x in seg if x.seq and off.seq < x.seq < end]
    forbidden = [x for x in during if x.kind in ('op', 'proc', 'hurt', 'death', 'settle', 'second', 'switch', 'burst')]
    buttons = [x for x in during if x.kind == 'pap' and x['kind'] in ('mcm-button', 'dump-status', 'dump-nearest')]
    if forbidden:
        return FAIL(f'總開關關著時 DLL 還在動（{len(forbidden)} 行）', *forbidden[:5])
    if not buttons:
        return EYES('關著時 DLL 完全沒動；MCM 按鈕沒寫進 log，請看畫面有沒有反應', off, on)
    after = [x for x in seg.procs() if on and x.seq > on.seq]
    return PASS(f'關著時沒有任何命中／狀態／每秒／受擊／死亡行；MCM 按鈕照常（{len(buttons)} 行）' + ('；打開後照常' if after else ''),
                off, *buttons[:2], on, *after[:1])


# ---------------------------------------------------------------- E

@rule('E-01')
def r_e01(seg, ctx):
    rows = [x for x in seg.of('remove') if x['tag'] == 'N3_StarFuse']
    reasons = {x['reason'] for x in rows}
    if not rows:
        return NODATA('沒有星痕引信的 remove 行')
    missing = [r for r in ('expired', 'dispel', 'death') if r not in reasons]
    if missing:
        return FAIL('少了這幾種移除：' + '、'.join(missing), *rows)
    bad = [x for x in rows if (x['reason'] == 'expired' and x.v('elapsed') < x.v('duration') - 0.05) or
           (x['reason'] == 'dispel' and x.v('elapsed') >= x.v('duration'))]
    if bad:
        return FAIL('elapsed／duration 跟理由對不上', *bad)
    return PASS('(a) 到期 expired、(b) dispelallspells → dispel、(c) kill → death', *rows[:4])


@rule('E-08')
def r_e08(seg, ctx):
    groups = scan_groups(seg)
    if len(groups) < 2:
        return NODATA(f'只有 {len(groups)} 次掃描')
    bad = []
    for h, rows in groups:
        for r in rows:
            who = r.a.get('who')
            if r['verdict'] == 'picked' and (r['hostile'] == '0' and r['engaged'] == '0'):
                bad.append(r)
            if r['verdict'] in ('picked', 'ally') and who and who.id == PLAYER_ID:
                bad.append(r)
    if bad:
        return FAIL('名單裡有路人／你', *bad[:4])
    neutral = sum(1 for h, rows in groups for r in rows if r['verdict'] == 'neutral')
    return PASS(f'{len(groups)} 次掃描，名單只有敵人（與 ally）；路人／守衛 {neutral} 次被排除（neutral）', *[h for h, rows in groups[:3]])


@rule('E-13')
def r_e13(seg, ctx):
    doms = seg.of('domain')
    return EYES(f'FPS 只能看畫面（這一站 domain 行 {len(doms)} 行；拿掉領域節點後應沒有 domain 行）', *doms[:1])


# ---------------------------------------------------------------- F (round 27h)

def raw_with(seg, *parts):
    return [x for x in seg if x.kind == 'raw' and all(p in x.text for p in parts)]


@rule('F-01')
def r_f01(seg, ctx):
    """The fault drill: a bad magnitude is dropped without a fault; a forced C++ exception is a SESSION fault that closes the
    form; a reload clears it."""
    badmag = raw_with(seg, '[ESSB][BADMAG]')
    fault = raw_with(seg, '[ESSB][fault]', 'for this game session')
    hard = raw_with(seg, '[ESSB][fault]', 'until the game restarts')
    closed = raw_with(seg, '[ESSB][fault]', 'the form is closed')
    cleared = raw_with(seg, '[ESSB][fault]', 'the session fault is cleared')
    if not badmag and not fault:
        return NODATA('沒有 BADMAG 也沒有 fault 行（主控台 cgf "ESSBNative.ForceFault" 2，再 1）')
    if hard:
        return FAIL('演練的 C++ 例外被當成要重開遊戲的故障（應只停這次遊戲）', *hard[:2])
    if not badmag:
        return FAIL('沒有 [ESSB][BADMAG]（ForceFault 2 應走丟棄壞數值的路）', *fault[:1])
    if fault and fault[0].n < badmag[0].n:
        return FAIL('BADMAG 之前就故障了', fault[0], badmag[0])
    if not fault:
        return NODATA('BADMAG 丟掉了、沒有故障（對）；還沒做 ForceFault 1', *badmag[:1])
    if not closed or closed[0].n < fault[0].n:
        return FAIL('故障後形態沒有關（沒有 the form is closed）', fault[0])
    if not cleared or cleared[0].n < fault[0].n:
        return EYES('故障、關形態都對；讀檔後沒看到 the session fault is cleared（讀檔了嗎？）', badmag[0], fault[0], closed[0])
    return PASS('壞數值丟掉不故障；C++ 例外＝這次遊戲的故障、形態關閉；讀檔後恢復', badmag[0], fault[0], closed[0], cleared[0])


@rule('F-02')
def r_f02(seg, ctx):
    """HDT-SMP stress: white heat 30 s ×3, 20 switches, the ring on / off, SMP gear. The log half: the body fire's applies and
    removals, the switches, the ring switch, the per-second events / natives; the freeze itself only the screen shows."""
    body = raw_with(seg, '[ESSB][bodyfx]')
    applied = [x for x in body if ' apply ' in x.text]
    removed = [x for x in body if ' remove ' in x.text]
    switches = [x for x in seg.of('switch') if x['kind'] in ('open', 'switch', 'close')]
    ring = [x for x in seg.of('mcm') if x['global'] == 'ESSB_WeaponGlow']
    rates = seg.of('rate')
    peak_events = max((x.v('events', 0) for x in rates), default=0)
    peak_natives = max((x.v('natives', 0) for x in rates), default=0)
    text = (f'身上火焰 套用 {len(applied)} 次、移除 {len(removed)} 次；切換 {len(switches)} 次；光圈開關 {len(ring)} 次；'
            f'每秒事件最多 {peak_events:.0f}、原生呼叫最多 {peak_natives:.0f}')
    if len(applied) < 3 or len(switches) < 20:
        return NODATA('不夠：' + text + '（白熱 3 次、切換 20 次）', *(applied[:1] + switches[:1]))
    return EYES(text + '；有沒有凍結只能看畫面（有的話請附 HDT-SMP 版本，另用 MCM「白熱全身特效」關掉再做一次）',
                *(applied[:2] + switches[:2] + ring[:1]))


def rate_summary(lines):
    """Round 27h: the per-second ModEvents sent and natives Papyrus called (the probe log's rate lines)."""
    rates = [x for x in lines if x.kind == 'rate']
    if not rates:
        return None
    ev = [x.v('events', 0) for x in rates]
    nat = [x.v('natives', 0) for x in rates]
    lag = [x.v('lagMaxMs', 0) for x in rates]
    return (f'每秒 ModEvent 平均 {statistics.mean(ev):.1f}、最多 {max(ev):.0f}；Papyrus 原生呼叫平均 {statistics.mean(nat):.1f}、'
            f'最多 {max(nat):.0f}；Papyrus 處理延遲最長 {max(lag):.0f} ms（{len(rates)} 秒）')


PAPYRUS_WARNINGS = (
    ('Suspended stack count is over our warning threshold', 'Papyrus 的暫停堆疊超過警告門檻'),
    ('Unbound native function', '沒綁上的原生函式'),
)


def papyrus_scan(path):
    """Round 27h (Papyrus review): the Papyrus log's warnings that point at a slow or broken script half: the suspended-stack
    threshold (with our scripts on the stacks) and unbound natives of ESSBNative."""
    try:
        text = Path(path).read_bytes().decode('utf-8', errors='replace')
    except OSError:
        return None
    rows = []
    for needle, label in PAPYRUS_WARNINGS:
        hits = [line for line in text.splitlines() if needle in line]
        ours = [line for line in hits if 'essb' in line.lower()] if needle.startswith('Unbound') else hits
        rows.append((label, len(ours)))
    essb_stack = sum(1 for line in text.splitlines() if 'essb' in line.lower() and 'stack' in line.lower())
    return rows, essb_stack


# ================================================================ run

def judge(lines, only=None):
    ctx = Ctx(lines)
    out = {}
    for n, ids, title in STATIONS:
        for i in ids:
            if only and i != only:
                continue
            seg = ctx.segs.get(n, Seg())
            if not seg and i != 'SETUP-1':
                out[i] = (n, Verdict('NO-DATA', f'站 {n}（{title}）沒有標記（數字鍵區 + 或 set ESSB_ProbeStep to {n}）'))
                continue
            try:
                out[i] = (n, RULES[i](seg, ctx))
            except Exception as e:   # a malformed log must not stop the other steps
                out[i] = (n, Verdict('FAIL', f'判讀時出錯：{type(e).__name__}: {e}'))
    bad_format = [x for x in lines if x.kind not in ('raw', 'step') and not x.ok]
    return out, bad_format, ctx


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    path = argv[1]
    only = argv[argv.index('--step') + 1] if '--step' in argv else None
    lines = read_log(path)
    out, bad_format, ctx = judge(lines, only)
    for a, b, dw, dr in clock_drift(lines)[:5]:
        print(f'警告：#{a.seq} → #{b.seq} 世界時鐘走了 {dw / 1000:.1f} 秒、執行時鐘走了 {dr / 1000:.1f} 秒（差超過 1 秒）')
    if (summary := rate_summary(lines)):
        print(summary)
    papyrus = argv[argv.index('--papyrus') + 1] if '--papyrus' in argv else str(Path(path).resolve().parents[1] / 'Logs/Script/Papyrus.0.log')
    if (scan := papyrus_scan(papyrus)):
        rows, stacks = scan
        print('Papyrus.0.log：' + '、'.join(f'{label} {n} 次' for label, n in rows) + f'；提到 ESSB 的堆疊行 {stacks} 行')
    print('傷害倍率（ESSB_BaseDamageMult）：' + '、'.join(f'{m:g}' for m in sorted(DAMAGE_MULTS))
          + '；傷害數字先除以當下的倍率，再跟表上（倍率 1.0）的數字比')
    counts = defaultdict(int)
    for i in ALL_IDS:
        if i not in out:
            continue
        n, v = out[i]
        counts[v.status] += 1
        if '--quiet' in argv and v.status == 'PASS':
            continue
        print(f'{i:8} 站{n:3} {v.status:8} {v.reason}')
        for e in v.evidence[:6]:
            print(f'           #{e.seq} L{e.n}: {e.short()}')
    if bad_format:
        print(f'格式不符的行 {len(bad_format)} 行（前 3 行）：')
        for x in bad_format[:3]:
            print('   L' + str(x.n) + ': ' + x.short())
    print('合計：' + '、'.join(f'{k} {v}' for k, v in sorted(counts.items())) + f'；站 {len(ctx.segs)} 個有標記')
    if '--json' in argv:
        target = Path(argv[argv.index('--json') + 1])
        target.write_text(json.dumps({i: dict(station=n, **v.json()) for i, (n, v) in out.items()}, ensure_ascii=False, indent=1),
                          encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
