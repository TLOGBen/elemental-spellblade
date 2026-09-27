"""Round 26 (the probe log): offline checks of what this round changed, each with injected faults.

  JUDGE      build/probe-judge.py judges all 102 step IDs, each at exactly one station, every rule present; the stations
             of build/probes-all.md (its "### 站 N：ID、ID" headers) are the judge's STATIONS, in order, and every station
             has an 操作 line and a log 判定 line.
  SAMPLES    the judge on the native sample (native/tests/trace_test.cpp: the real planners in a fake world write
             build/fix26-trace-sample.log; its stations 9001..9006 renumbered to the sheet's): B-07, B-35, B-33, A-15, A-05,
             A-09 PASS; one mutation of each fails it. Hand-written samples (build here, every line checked against the
             shared formats of build/fix26_format.py) for SETUP-1, A-01, A-06, A-10, A-11, A-12, B-08, B-13, C-01, D-01,
             D-24, E-01: PASS as written, FAIL with the one fault each carries.
  TRACE      the probe log in the sources: Probe::kHurtTask is the hurt task's own flag (the round-25 bug: it shared
             kHurt with the hit sink's line); every X1 sink / task probe is there; the level is 4 (Trace.h kLevel) and
             every Papyrus call of ESSBNative.Trace sits behind a level-4 check (CachedDebugLevel >= 4 / Level() >= 4 or
             the gated Probe / LogEvent / LogThrottled / ESSBLog.Log); the timer thread flushes once a second; the step
             keys run only with the level on; ESSBNative.Trace is declared and registered through Guard (read-only); the
             MCM debug enum has 4：探針 log; DLL version 0.26.0 everywhere.
  RECORDS    ESSB_ProbeStep is a GLOB at 0x005C00 in the written ESP and in the manifest's globals (Load.h resolves it:
             build/fix25_verify LOAD runs the loader on this ESP).
  MUTANTS    the Trace.h / StatusEngine.h probe-log mutants of native/build.py all failed trace_test (receipt), >= 4.
  HISTORY    build/fix26_history.py (Papyrus) and build/fix26_native_history.py (DLL, tests, generators, verifiers, the
             judge); the round-25 seals read the pre-fix26 snapshot only after these proofs.
  ENDINGS    every file this round touched keeps its pre-round line endings and byte-order mark.
"""
from pathlib import Path
import importlib.util, json, re, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SNAPSHOT = ROOT / '.codex/pre-fix26-snapshot'
SRC = ROOT / 'src'
PLUGIN_CPP = ROOT / 'native/src/Plugin.cpp'
SHEET = ROOT / 'build/probes-all.md'
SAMPLE = ROOT / 'build/fix26-trace-sample.log'
SAMPLE_STATIONS = {9001: 'B-07', 9002: 'B-35', 9003: 'B-33', 9004: 'A-15', 9005: 'A-05', 9006: 'A-09'}

import fix26_format as fmt


def judge_module():
    spec = importlib.util.spec_from_file_location('probe_judge', ROOT / 'build/probe-judge.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- JUDGE / SHEET

def check_judge(j, sheet_text):
    errors = []
    ids = [i for n, group, _ in j.STATIONS for i in group]
    if sorted(ids) != sorted(j.ALL_IDS) or len(ids) != len(set(ids)):
        errors.append(f'stations do not cover the 102 IDs exactly once: {sorted(set(j.ALL_IDS) ^ set(ids))}')
    missing = [i for i in j.ALL_IDS if i not in j.RULES]
    if missing:
        errors.append(f'no rule for {missing}')
    numbers = [n for n, _, _ in j.STATIONS]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append('station numbers are not 1..N in order')
    heads = re.findall(r'^### 站 (\d+)：([^（\r\n]+)', sheet_text, re.M)
    sheet = [(int(n), [x.strip() for x in re.split(r'[＋、]', body) if x.strip()]) for n, body in heads]
    judged = [(n, list(group)) for n, group, _ in j.STATIONS]
    if sheet != judged:
        diff = [(a, b) for a, b in zip(sheet, judged) if a != b][:3]
        errors.append(f'probes-all.md stations differ from probe-judge.STATIONS ({len(sheet)} vs {len(judged)}): {diff}')
    blocks = re.split(r'^### 站 \d+：', sheet_text, flags=re.M)[1:]
    for n, block in zip([n for n, _ in sheet], blocks):
        if '**操作**' not in block:
            errors.append(f'station {n}: no 操作')
        if '**log 判定**' not in block:
            errors.append(f'station {n}: no log 判定')
    for need in ('4：探針 log', r'C:\Users\powde\OneDrive\Documents\My Games\Skyrim Special Edition\SKSE\ElementsSpellblade.log',
                 '數字鍵區 `+`', 'set ESSB_ProbeStep to N', '複製'):
        if need not in sheet_text:
            errors.append(f'the sheet does not say {need!r}')
    return errors, dict(stations=len(judged), steps=len(ids))


# ---------------------------------------------------------------- SAMPLES

class Log:
    """A hand-written log in the probe log's formats (every T line is checked against build/fix26_format.py)."""

    def __init__(self):
        self.lines = []
        self.seq = 0
        self.g = 1000

    def step(self, n):
        self.seq += 1
        self.lines.append(f'[ESSB][STEP] {n} #{self.seq} g={self.g} r={self.g} via=key')

    def t(self, kind, body):
        self.seq += 1
        self.lines.append(f'[ESSB][T][{kind}] #{self.seq} g={self.g} r={self.g}{body}')

    def raw(self, text):
        self.lines.append(text)

    def wait(self, ms):
        self.g += ms

    def text(self):
        return '\n'.join(self.lines) + '\n'


def A(name, fid, h=1000.0, hm=1000.0, m=300.0, mm=300.0, s=200.0, sm=200.0, dead=False):
    return f'{name}(0x{fid:08X})[h={h:.1f}/{hm:.1f} m={m:.1f}/{mm:.1f} s={s:.1f}/{sm:.1f}{" dead" if dead else ""}]'


YOU = 0x14
BANDIT = 0xFF000D8A


def op(ctx, name, who='target', kind='-', el='none', mag=0.0, sec=0.0, on=None, extra=''):
    return (f' ctx={ctx} op={name} who={who} at=0 kind={kind} el={el} mag={mag:.2f} sec={sec:.2f}{extra} on='
            + (on or A('Bandit', BANDIT, 5000, 5000, 100, 100, 100, 100)))


def s_setup(fault):
    L = Log()
    L.raw('[ESSB][load] ElementsSpellblade 0.26.0; SE 1.5.97 + SKSE 2.0.20 only; no entry-51 fallback')
    L.step(1)
    L.t('pap', ' kind=mcm-button who=- button=ShowNativeStatus version=0.26.0 active=True')
    probes = ['Papyrus native', 'queued native task', 'TESHitEvent', 'TESHitEvent (you are the target)', 'hurt task',
              'TESActiveEffectApplyRemoveEvent', 'TESDeathEvent', 'timer task', 'TESSpellCastEvent', 'input sink']
    for p in probes:
        if fault and p == 'hurt task':
            continue
        L.raw(f'[ESSB][X1] {p} thread=15464 n=1 input=18188 DIFFERENT task=15464 same window=18188 DIFFERENT dataLoaded=2744 paused=0')
    return L


def s_a01(fault):
    L = Log()
    L.step(2)
    for old, new in ((3, 5), (5, 1), (1, 3)) if not fault else ((3, 3), (3, 0.25), (0.25, 3)):
        L.t('mcm', f' global=ESSB_NodeScale old={old:.3f} new={new:.3f}')
        L.wait(500)
    return L


def s_a06(fault):
    L = Log()
    L.step(7)
    for flags in ((0, 1, 1, 0, 0), (1, 1, 0, 0, 0), (0, 1, 0, 1, 0), (1, 1, 0, 0, 0)):
        L.t('key', f' code=79 element=fire verdict=blocked paused={flags[0]} menu={flags[1]} console={flags[2]} text={flags[3]} '
                   f'loading={flags[4]} thread=18188')
        if fault:
            L.t('switch', ' via=hotkey wanted=fire kind=open element=fire active=0 current=none dead=0 enabled=1 freePass=0 freeOpen=0 '
                          'gate=30.00 you=' + A('Prisoner', YOU))
            fault = False
        L.wait(2000)
    return L


def s_a10(fault):
    L = Log()
    L.step(11)
    L.t('second', ' form=fire spent=2.98 bled=0.00 flow=0.0000 close=0 storm=0 dH=+0.00 dM=-2.98 dS=+0.00 you=' + A('Prisoner', YOU, m=250))
    L.wait(300)
    L.t('tick', ' state=stopped active=40000 paused=1 loading=0')
    L.g += 0
    stopped_r = L.g
    L.lines.append(f'[ESSB][T][tick] #{L.seq + 1} g={L.g} r={stopped_r + 30000} state=running active={40000 if not fault else 70000}')
    L.seq += 1
    L.wait(700)
    L.t('second', ' form=fire spent=2.98 bled=0.00 flow=0.0000 close=0 storm=0 dH=+0.00 dM=-2.98 dS=+0.00 you=' + A('Prisoner', YOU, m=247.02))
    return L


def s_a11(fault):
    L = Log()
    L.step(12)
    L.t('second', ' form=fire spent=0.00 bled=0.00 flow=0.0000 close=0 storm=0 dH=+0.00 dM=-300.00 dS=+0.00 you=' + A('Prisoner', YOU, m=0))
    L.wait(500 if fault else 2000)
    L.t('second', ' form=fire spent=0.00 bled=0.00 flow=0.0000 close=1 storm=0 dH=+0.00 dM=+0.00 dS=+0.00 you=' + A('Prisoner', YOU, m=0))
    L.wait(100)
    L.t('pap', ' kind=form-close who=' + A('Prisoner', YOU, m=0) + ' reason=magicka-empty element=1')
    return L


def s_a12(fault):
    L = Log()
    L.step(13)
    for h, bled in ((1000.0, 10.0), (990.0, 9.87), (700.0, 6.0 if not fault else 5.0), (694.0, 5.94), (100.0, 0.0), (100.0, 0.0)):
        L.t('second', f' form=blood spent=0.00 bled={bled:.2f} flow=0.0000 close=0 storm=0 dH=-{bled:.2f} dM=+0.00 dS=+0.00 you='
                      + A('Prisoner', YOU, h=h - bled))
        L.wait(1000)
    return L


def s_b08(fault):
    L = Log()
    L.step(26)
    you = lambda h: A('Prisoner', YOU, h=h)
    L.t('op', op('hit', 'Apply', 'you', 'N3_Heat1', mag=1, sec=3600, on=you(1000), extra=''))
    L.wait(3000)
    L.t('op', op('hit', 'Remove', 'you', 'N3_Heat1', on=you(1000)))
    L.t('op', op('hit', 'Apply', 'you', 'N3_Heat2', mag=1, sec=3600, on=you(1000)))
    L.wait(3000)
    if not fault:
        L.t('op', op('hit', 'Remove', 'you', 'N3_Heat2', on=you(1000)))
    L.t('op', op('hit', 'Apply', 'you', 'N3_Heat3', mag=0, sec=8, on=you(1000)))
    for s in range(8):
        L.wait(1000)
        L.t('fire-source', ' tier=3 radius=210 perEnemy=6.30 cost=5.00 hostiles=1 bath=0')
        L.t('op', op('fire-source', 'Damage', el='fire', mag=6.30))
        L.t('op', op('tick', 'PayHealth', 'you', mag=5.0, on=you(1000 - 5 * s)))
    L.wait(200)
    L.t('settle', ' on=' + you(960) + ' tag=N3_Heat3 mag=0.00 elapsed=8.00 duration=8.00 crystals=0')
    L.t('op', op('settle', 'Noop', 'target', on=you(960)).replace(' on=', ' ev=Overheat args=0|0|0|0|0|0|0|0 on='))
    L.t('op', op('settle', 'PayHealth', 'you', mag=100.0, on=you(960)))
    L.t('op', op('settle', 'Remove', 'you', 'N3_Heat3', on=you(860)))
    L.wait(4000)
    L.t('second', ' form=fire spent=2.98 bled=0.00 flow=0.0000 close=0 storm=0 dH=+0.00 dM=-2.98 dS=+0.00 you=' + you(860))
    return L


def s_b13(fault):
    L = Log()
    L.step(30)
    you = A('Prisoner', YOU)
    charges = [2, 3, 4, 5, 6] if not fault else [2, 4, 5, 6]
    before = 0
    for c in charges:
        n = before + 1
        L.t('proc', f' src=hit tgt={A("Bandit", BANDIT, 5000, 5000, 100, 100, 100, 100)} you={you} el=shock spell=ESSB_Hit_Lightning_Normal '
                    f'weapon=1 power=0 sneak=0 leftHand=0 mag=21.00 crit=0 N={n} charges={before} critChance={0.05 + 0.02 * before:.3f} '
                    f'siphon=0.00 burned=0.00 dispel=0 overloadAfter=-1.00 overloaded=0 silenced=0 echo=0 riposte=0 steps=Proc:21.00 '
                    f'rolls=I(1,25)=20')
        L.t('op', op('hit', 'Apply', 'you', 'N4_Charge', mag=c, sec=10, on=you))
        before = c
        L.wait(1200)
    L.t('proc', f' src=hit tgt={A("Bandit", BANDIT, 4900, 5000, 100, 100, 100, 100)} you={you} el=shock spell=ESSB_Hit_Lightning_Power '
                f'weapon=1 power=1 sneak=0 leftHand=0 mag=30.00 crit=0 N=7 charges=6 critChance=0.170 siphon=0.00 burned=0.00 '
                f'dispel=0 overloadAfter=-1.00 overloaded=0 silenced=0 echo=0 riposte=0 steps=Proc:30.00 rolls=I(1,25)=19')
    L.t('op', op('hit', 'Noop', on=A('Bandit', BANDIT, 4900, 5000)).replace(' on=', ' ev=Discharge args=6|1|1.5|2.5|0|0|0|0 on='))
    L.t('op', op('hit', 'Damage', el='shock', mag=177.0))
    L.t('op', op('hit', 'Remove', 'you', 'N4_Charge', on=you))
    L.t('hit-end', f' tgt={A("Bandit", BANDIT, 4693, 5000, 100, 100, 100, 100)} you={you} ops=9')
    return L


def s_c01(fault):
    L = Log()
    L.step(55)
    att = A('Bandit', BANDIT, 5000, 5000, 100, 100, 100, 100)
    L.t('hurt', f' att={att} you={A("Prisoner", YOU, 965)} before=1000.00 after=965.00 lost=35.00 melee=1 spell=0 destructive=0 blocked=0 '
                'cloak=0 afterimage=0 linger=0 guardBefore=0.00 guardLeft=-1.00 overloadBefore=0.00 magickaBefore=300.00 magickaNow=300.00 '
                'dot=0.00 form=0 ops=1 cd_you=- cd_att=-')
    L.t('op', op('hurt', 'SpendMagicka', 'you', mag=35.0 if fault else 15.0, on=A('Prisoner', YOU, 965)))
    L.wait(3000)
    L.t('hurt', f' att={att} you={A("Prisoner", YOU, 900)} before=965.00 after=930.00 lost=35.00 melee=1 spell=0 destructive=0 blocked=0 '
                'cloak=0 afterimage=0 linger=0 guardBefore=0.00 guardLeft=-1.00 overloadBefore=0.00 magickaBefore=3.00 magickaNow=3.00 '
                'dot=0.00 form=0 ops=2 cd_you=- cd_att=-')
    L.t('op', op('hurt', 'SpendMagicka', 'you', mag=3.0, on=A('Prisoner', YOU, 930)))
    L.t('op', op('hurt', 'HurtHealth', 'you', mag=12.0, on=A('Prisoner', YOU, 930)))
    return L


def s_d01(fault):
    L = Log()
    L.step(64)
    ally = A('Lydia', 0x000A2C94, 800, 800, 100, 100, 100, 100)
    for i, (el, mag) in enumerate((('fire', 12.6), ('frost', 10.5), ('shock', 26.25), ('earth', 10.5))):
        npc = A(f'Bandit{i}', 0xFF000E00 + i, 3000, 3000, 100, 100, 100, 100)
        L.t('burst-start', f' element={el} stage=0 sync=1 radius=1050 you={A("Prisoner", YOU)}')
        L.t('scan', f' ctx=burst centre=- aroundCentre=0 aroundYou=2100 high=6 picked=2')
        L.t('scan-c', f' who={npc} d_you=150 d_centre=150 hostile=1 teammate=0 engaged=1 verdict=picked member=1')
        L.t('scan-c', f' who={ally} d_you=200 d_centre=200 hostile=0 teammate=1 engaged=0 verdict=ally member=2')
        L.t('op', op('burst', 'Damage', el=el, mag=mag, on=npc))
        if fault and i == 0:
            L.t('op', op('burst', 'Damage', el=el, mag=mag, on=ally))
        L.t('burst', f' element={el} stage=0 targets=1 marks=1 crowd=3 ops=6')
        L.wait(3000)
    return L


def s_d24(fault):
    L = Log()
    L.step(88)
    L.t('mcm', ' global=ESSB_Enabled old=1.000 new=0.000')
    L.wait(5000)
    if fault:
        L.t('op', op('tick', 'PayHealth', 'you', mag=5.0, on=A('Prisoner', YOU)))
    L.t('pap', ' kind=dump-status who=' + A('Prisoner', YOU) + ' element=0 active=0 sync=0 stage=0')
    L.wait(5000)
    L.t('mcm', ' global=ESSB_Enabled old=0.000 new=1.000')
    L.wait(1000)
    L.t('proc', f' src=hit tgt={A("Bandit", BANDIT, 5000, 5000, 100, 100, 100, 100)} you={A("Prisoner", YOU)} el=fire '
                'spell=ESSB_Hit_Fire_Normal weapon=1 power=0 sneak=0 leftHand=0 mag=11.00 crit=0 charges=0 siphon=0.00 burned=0.00 dispel=0 '
                'overloadAfter=-1.00 overloaded=0 silenced=0 echo=0 riposte=0 steps=Proc:11.00 rolls=R(10,12)=10.4762')
    return L


def s_e01(fault):
    L = Log()
    L.step(89)
    npc = A('Bandit', BANDIT, 5000, 5000, 100, 100, 100, 100)
    for reason, elapsed in (('expired', 2.0), ('dispel', 0.6), ('death', 0.5)):
        if fault and reason == 'death':
            continue
        L.t('remove', f' on={npc} tag=N3_StarFuse mag=20.00 elapsed={elapsed:.2f} duration=2.00 left={max(0, 2 - elapsed):.2f} reason={reason}')
        L.wait(4000)
    return L


HAND = {'SETUP-1': s_setup, 'A-01': s_a01, 'A-06': s_a06, 'A-10': s_a10, 'A-11': s_a11, 'A-12': s_a12, 'B-08': s_b08, 'B-13': s_b13,
        'C-01': s_c01, 'D-01': s_d01, 'D-24': s_d24, 'E-01': s_e01}

# One mutation of the native sample per step (the renumbered text): (step, old, new, count) -- each must turn PASS into FAIL.
NATIVE_FAULTS = {
    'B-07': (lambda t: re.sub(r'(el=fire spell=ESSB_Hit_Fire_Normal .*? mag=)[\d.]+(.*?rolls=R\(10,12\)=)[\d.]+', r'\g<1>13.55\g<2>12.9000', t, count=1)),
    'B-35': (lambda t: t.replace('kind=N3_Bleed el=none mag=8.00', 'kind=N3_Bleed el=none mag=9.00', 1)),
    'B-33': (lambda t: t.replace('tag=Mark_fire mag=0.00 elapsed=8.00 duration=8.00 left=0.00 reason=expired',
                                 'tag=Mark_fire mag=0.00 elapsed=8.00 duration=8.00 left=0.00 reason=dispel', 1)),
    'A-15': (lambda t: re.sub(r'wet=1 stormy=1 thunder=0', 'wet=1 stormy=0 thunder=0', t)),
    'A-05': (lambda t: t.replace('wanted=fire kind=refuse', 'wanted=fire kind=open', 1)),
    'A-09': (lambda t: t.replace('form=fire spent=2.98', 'form=fire spent=4.50')),
}


def renumbered_sample(j):
    text = SAMPLE.read_text(encoding='utf-8')
    station = {n: j.STATIONS[[i for i, (m, ids, _) in enumerate(j.STATIONS) if s in ids][0]][0] for n, s in SAMPLE_STATIONS.items()}
    return re.sub(r'^\[ESSB\]\[STEP\] (\d+) ', lambda m: f'[ESSB][STEP] {station[int(m.group(1))]} ', text, flags=re.M)


def verdict_of(j, text, step):
    lines = [j.parse_line(n, x) for n, x in enumerate(text.splitlines(), 1) if '[ESSB]' in x]
    out, bad_format, _ = j.judge(lines, step)
    return out[step][1], bad_format


def check_samples(j):
    errors, rows = [], []
    if not SAMPLE.exists():
        return ['build/fix26-trace-sample.log missing (native/build.py writes it through trace_test)'], rows
    native = renumbered_sample(j)
    for n, step in SAMPLE_STATIONS.items():
        v, bad = verdict_of(j, native, step)
        if bad:
            errors.append(f'native sample: {len(bad)} lines do not match the formats (first: {bad[0].text[:120]})')
        if v.status != 'PASS':
            errors.append(f'native sample {step}: {v.status} {v.reason}')
        fv, _ = verdict_of(j, NATIVE_FAULTS[step](native), step)
        if fv.status != 'FAIL':
            errors.append(f'native sample {step} with its fault: {fv.status} (should be FAIL) {fv.reason}')
        rows.append((step, 'native', v.status, fv.status))
    for step, build in HAND.items():
        good, bad = build(False).text(), build(True).text()
        v, fmt_bad = verdict_of(j, good, step)
        if fmt_bad:
            errors.append(f'hand sample {step}: a line does not match its format: {fmt_bad[0].text[:160]}')
        if v.status != 'PASS':
            errors.append(f'hand sample {step}: {v.status} {v.reason}')
        fv, _ = verdict_of(j, bad, step)
        if fv.status != 'FAIL':
            errors.append(f'hand sample {step} with its fault: {fv.status} (should be FAIL) {fv.reason}')
        rows.append((step, 'hand', v.status, fv.status))
    return errors, rows


# ---------------------------------------------------------------- TRACE (static)

X1_NAMES = ['"TESHitEvent"', '"TESHitEvent (you are the target)"', '"hurt task"', '"TESSpellCastEvent"', '"TESActiveEffectApplyRemoveEvent"',
            '"TESDeathEvent"', '"timer task"', '"input sink"', '"Papyrus native"', '"queued native task"', '"settle task"', '"death task"',
            '"spell-cast task"']


def psc_functions(text):
    import fix21_history as h21
    return h21.functions(text)


def check_trace(cpp, sources, trace_h, config_text):
    errors = []
    if 'LogThreadOnce(Probe::kHurtTask, "hurt task")' not in cpp or 'LogThreadOnce(Probe::kHurt, "hurt task")' in cpp:
        errors.append('the hurt task does not log X1 with its own flag Probe::kHurtTask')
    for name in X1_NAMES:
        if f', {name});' not in cpp:
            errors.append(f'X1 probe {name} missing')
    if 'inline constexpr float kLevel = 4.0f;' not in trace_h:
        errors.append('Trace.h kLevel is not 4')
    loop = cpp[cpp.index('void TimerLoop() noexcept'):cpp.index('// ---------------------------------------------------------------- round 25 (N6): hotkeys')]
    if 'GetTickCount64() - state.lastFlush.load() >= 1000' not in loop or 'FlushTrace();' not in loop:
        errors.append('the timer thread does not flush the probe log once a second')
    if 'if (Active() && TraceOn()) {\n            ProbeKeys(first);' not in cpp:
        errors.append('the step keys are not gated on the probe log level')
    if 'vm->RegisterFunction("Trace", kClass, PapyrusTrace);' not in cpp or '}, false, true);' not in cpp[cpp.index('void PapyrusTrace'):]:
        errors.append('ESSBNative.Trace is not registered through Guard (read-only)')
    if 'Function Trace(String asKind, Actor akActor, String asText) Global Native' not in sources.get('ESSBNative.psc', ''):
        errors.append('ESSBNative.psc does not declare Trace')
    # every Papyrus call of ESSBNative.Trace (and of the Probe wrapper) behind a level-4 check in front of it
    for script, text in sources.items():
        for fn, body in psc_functions(text).items():
            body = body.replace('\r\n', '\n')
            for m in re.finditer(r'(ESSBNative\.Trace|(?<![\w.])Probe|akCtl\.Probe)\(', body):
                if body[:m.start()].endswith('Function '):
                    continue   # the Probe wrapper's own definition
                window = body[max(0, m.start() - 240):m.start()]
                if not re.search(r'(CachedDebugLevel >= 4|Level\(\) >= 4|current >= 4)', window):
                    errors.append(f'{script} {fn}: a probe-log call without a level-4 check in front of it')
    if "'4：探針 log'" not in config_text:
        errors.append('the MCM debug enum has no 4：探針 log')
    return errors


def check_versions(b):
    errors = []
    cmake = (ROOT / 'native/CMakeLists.txt').read_text(encoding='utf-8')
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    import fix19_native as n
    if 'VERSION 0.26.0' not in cmake or 'nativeVersion[] = "0.26.0"' not in header or n.NATIVE_VERSION != '0.26.0':
        errors.append('the DLL version is not 0.26.0 in CMakeLists / ManifestData.h / fix19_native')
    manifest = json.loads((b.OUT / 'SKSE/Plugins/ElementsSpellblade/manifest.json').read_text(encoding='utf-8'))
    if manifest.get('native_version') != '0.26.0':
        errors.append('the packaged manifest is not 0.26.0')
    if manifest.get('globals', {}).get('ESSB_ProbeStep') != 0x5C00:
        errors.append('ESSB_ProbeStep is not in the manifest globals at 0x005C00')
    return errors


def check_records(b):
    errors = []
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    hits = [r for r in records if r.sig == 'GLOB' and int(r.key.split('|')[1], 16) == 0x5C00]
    if len(hits) != 1:
        errors.append('the written ESP has no GLOB 0x005C00')
    else:
        edid = hits[0].d.get('EDID', b'')
        edid = edid if isinstance(edid, bytes) else str(edid).encode('utf-8')
        if b'ESSB_ProbeStep' not in edid:
            errors.append(f'GLOB 0x005C00 is not ESSB_ProbeStep ({edid!r})')
    formids = json.loads((ROOT / 'build/v03-formids.json').read_text(encoding='utf-8'))['records']
    row = formids.get('ESSB_ProbeStep')
    if not row or row['id'] != '005C00' or row['type'] != 'GLOB':
        errors.append('ESSB_ProbeStep is not the GLOB 0x005C00 in build/v03-formids.json')
    return errors, len(hits)


def check_mutants():
    receipt = json.loads((ROOT / 'native/out/build-receipt.json').read_text(encoding='utf-8'))
    mutants = receipt.get('mutants') or []
    trace = [m for m in mutants if m['test'] == 'trace']
    assert len(trace) >= 4 and all(m['exit'] not in (0, None) for m in trace), ('round-26 trace mutants', trace)
    return trace


# ---------------------------------------------------------------- ENDINGS

TOUCHED = ['build_v03.py', 'native/CMakeLists.txt', 'native/build.py', 'native/include/StatusEngine.h', 'native/include/Load.h',
           'native/src/Plugin.cpp', 'build/fix19_native.py', 'build/probes-all.md', 'build/native-verification.md', '實作紀錄.md',
           'build/fix25_history.py', 'build/fix25_history_gen.py', 'build/fix25_history_template.py', 'build/fix25_native_history.py',
           'build/fix25_native_history_gen.py', 'build/fix25_native_history_template.py']


def check_endings():
    errors = []
    pairs = [(p, SNAPSHOT / 'src' / p.name) for p in sorted(SRC.glob('*.psc'))]
    pairs += [(ROOT / rel, SNAPSHOT / rel) for rel in TOUCHED]
    for now_path, before in pairs:
        if not before.exists() or not now_path.exists():
            continue
        was, now = before.read_bytes(), now_path.read_bytes()
        was_crlf = b'\r\n' in was and was.count(b'\r\n') == was.count(b'\n')
        now_crlf = b'\r\n' in now and now.count(b'\r\n') == now.count(b'\n')
        name = now_path.relative_to(ROOT).as_posix()
        if was_crlf != now_crlf or (not was_crlf and b'\r\n' in now):
            errors.append(f'{name}: line endings changed')
        if was.startswith(b'\xef\xbb\xbf') != now.startswith(b'\xef\xbb\xbf'):
            errors.append(f'{name}: the byte-order mark changed')
    return errors


# ---------------------------------------------------------------- injected faults of this verifier

def self_test(j, cpp, sources, trace_h, config_text, sheet_text):
    caught = []

    def expect(label, errors):
        if not errors:
            raise AssertionError(('fix26 fault not caught', label))
        caught.append(label)

    expect('the hurt task back on kHurt', check_trace(cpp.replace('LogThreadOnce(Probe::kHurtTask, "hurt task")',
                                                                  'LogThreadOnce(Probe::kHurt, "hurt task")', 1), sources, trace_h, config_text))
    expect('the timer thread not flushing', check_trace(cpp.replace('            FlushTrace();   // round 26: the probe log reaches the file once a second (paused or not)',
                                                                    '            (void)0;', 1), sources, trace_h, config_text))
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('\tIf CachedDebugLevel >= 4\n\t\tProbe("knock"', '\tIf True\n\t\tProbe("knock"', 1)
    expect('an ungated Papyrus probe', check_trace(cpp, s, trace_h, config_text))
    expect('the step keys without the level', check_trace(cpp.replace('if (Active() && TraceOn()) {\n            ProbeKeys(first);',
                                                                     'if (Active()) {\n            ProbeKeys(first);', 1), sources, trace_h, config_text))
    expect('a station moved in the sheet', check_judge(j, sheet_text.replace('### 站 25：B-07', '### 站 25：B-08', 1))[0])
    expect('a station without log 判定', check_judge(j, sheet_text.replace('**log 判定**', '**判定**', 1))[0])
    return caught


def run(b):
    j = judge_module()
    sheet_text = SHEET.read_text(encoding='utf-8')
    cpp = PLUGIN_CPP.read_text(encoding='utf-8')
    trace_h = (ROOT / 'native/include/Trace.h').read_text(encoding='utf-8')
    config_text = (ROOT / 'build_v03.py').read_text(encoding='utf-8')
    sources = {p.name: p.read_text(encoding='utf-8-sig') for p in SRC.glob('*.psc')}
    errors, judge_counts = check_judge(j, sheet_text)
    sample_errors, sample_rows = check_samples(j)
    errors += sample_errors + check_trace(cpp, sources, trace_h, config_text) + check_versions(b) + check_endings()
    record_errors, _ = check_records(b)
    errors += record_errors
    assert not errors, '\n  '.join(['FIX26 failed:'] + errors)
    caught = self_test(j, cpp, sources, trace_h, config_text, sheet_text)
    trace_mutants = check_mutants()
    import fix26_history
    history = fix26_history.self_check()
    import fix26_native_history
    native_history = fix26_native_history.self_check()
    report = dict(judge=judge_counts, samples=sample_rows, source_faults=caught, trace_mutants=[m['name'] for m in trace_mutants],
                  history=history, native_history=native_history)
    (ROOT / 'build/fix26-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    native = [r for r in sample_rows if r[1] == 'native']
    hand = [r for r in sample_rows if r[1] == 'hand']
    print(f'FIX26 ok: probe-judge judges all {judge_counts["steps"]} steps at {judge_counts["stations"]} stations = build/probes-all.md; '
          f'native sample (real planners) {len(native)} steps PASS and FAIL with one fault each ({", ".join(r[0] for r in native)}); '
          f'hand samples {len(hand)} steps PASS / FAIL ({", ".join(r[0] for r in hand)}); hurt task on its own X1 flag, 13 X1 probes, '
          f'level 4, 1 s flush, gated step keys and Papyrus probes, ESSBNative.Trace guarded; ESSB_ProbeStep GLOB 0x005C00; 0.26.0; '
          f'line endings kept; {len(caught)}/{len(caught)} source faults caught; {len(trace_mutants)} trace mutants failed; '
          f'history: {history["changed"]} changed / {history["added"]} added functions, {len(history["silent_edits_caught"])} silent '
          f'edits caught; native seal {native_history["changed"]} changed / {native_history["added"]} added / '
          f'{native_history["unchanged"]} unchanged, {len(native_history["silent_edits_caught"])} silent edits caught')


if __name__ == '__main__':
    import build_v03
    run(build_v03)
