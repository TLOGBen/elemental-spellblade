"""Round 25 (N6: the per-second timers, the hotkey input sink and the domains in the DLL): offline checks of what this
round changed, each with injected faults.

  CONTRACT   the round-22..24 seam checks on today's sources (build/fix24_verify.check_contract: natives declared =
             registered, every ModEvent the DLL sends registered, body-only events never registered) plus: ESSB_Switch and
             ESSB_Close are sent by the DLL (RequestSwitch, Timer.h PlanFormSecond) and handled by ESSBController
             (OnESSBSwitch -> SwitchForm, OnESSBClose -> CloseForm); ESSBNative.RequestSwitch is declared, registered and
             queued; ExtendFuse / WashBuffs are gone; OnESSBDomain only plays the opening effect; the domain event casts the
             element's spawn spell (StatusEngine.h RunOp, DomainSpawnSpell) without a magnitude override.
  TIMER      ruling R3: the timer thread posts ONE task a tick (tickQueued) and the task never queues itself; the clock
             (essb::Step) stops while the game is paused or loading (GameStopped); the per-second work runs from the
             clock's beat; the input sink is registered on BSInputDeviceManager, never consumes (kContinue) and gates on
             Timer.h InputOpen.
  REMOVED    ESSBFormRules / ESSBInput / ESSBSilence are gone (src, SCRIPTS, VMAD); no script names the Papyrus domains,
             the environment check, the storm clock, 長流, the key polling or the domain mirrors; no Papyrus per-second loop
             is left for work v0.4 assigns to the DLL (no RegisterForSingleUpdate in an effect script, no RegisterForKey).
  RECORDS    read back from the written ESP: every round-25 kind (Script, No Magnitude, the record seconds, the delivery),
             every domain (HAZD: invisible model, 3 m in feet, Inherit Duration + Drop to Ground, limit 0, interval 0.3, its
             hazard spell; the hazard spell's effects; the Spawn Hazard MGEF: archetype 40, associated item = the HAZD, no
             death dispel, not hostile; one spawn spell a whole second 1..24), ESSB_FormRulesEffect / ESSB_SilenceEffect
             without VMAD, the quest alias with two scripts and none of the removed properties, schema 14.
  RESOLVE    every ESSB_N6_ status record and every domain FormID ManifestData.h names is that record in the ESP.
  NODES      no node is -N6, 待決 or PARTIAL any more (build/plan-coverage.json); 神聖領域 and 毒霧 are DONE.
  GUARDS     every event sink and task behind SEH + C++ catch, every native through Guard (build/fix22_verify).
  FAULTS     timer_test fails on a mutated table (an upkeep 1% stronger, the close event dropped, 潮池's wash limit, a hotkey
             slot, a clock beat, a spawn spell FormID, a round-25 kind's record seconds).
  ENDINGS    every file this round touched keeps its pre-round line endings and byte-order mark.
  MUTANTS    the C++ source mutations of native/build.py on Timer.h all failed (receipt), >= 5.
  HISTORY    build/fix25_history.py (Papyrus) and build/fix25_native_history.py (DLL, tests, generators, verifiers); the
             round-24 seals read the pre-fix25 snapshot only after these proofs.
"""
from pathlib import Path
import copy, json, re, struct, subprocess, sys, tempfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SRC = ROOT / 'src'
SNAPSHOT = ROOT / '.codex/pre-fix25-snapshot'
PLUGIN_CPP = ROOT / 'native/src/Plugin.cpp'
STATUS_H = ROOT / 'native/include/Status.h'
ENGINE_H = ROOT / 'native/include/StatusEngine.h'
TIMER_H = ROOT / 'native/include/Timer.h'
REACTIONS_H = ROOT / 'native/include/Reactions.h'

import fix22_verify as v22
import fix24_verify as v24

REMOVED_FILES = ['ESSBFormRules.psc', 'ESSBInput.psc', 'ESSBSilence.psc']
REMOVED_NAMES = ['StartDomain', 'InDomain', 'TickDomain', 'DomainActive', 'PlayerInDomain', 'ScanDomainTargets', 'DomainFlag',
                 'InsideDomainSlot', 'ClearDomainResidents', 'ObserveDomainResidents', 'RememberDomainResident', 'DomainTargetTicks',
                 'EnvCheck', 'FlowPercent', 'WaterFormTick', 'PayBloodCost', 'BloodDrainPerSecond', 'ESSBInput', 'ESSBFormRules',
                 'ESSBSilence', 'InputLayer', 'StormCharge', 'LastEnvCheck', 'PlayerInFireDomain', 'DomainLeft', 'DomainResident',
                 'TargetDamageMult', 'ApplyStrip', 'ApplyDamage', 'ApplyDamageRaw', 'ApplyDotDamage', 'ReactDamage', 'GetDamageMult',
                 'SelfSlowImmune', 'WindSlowImmune', 'ToggleForm', 'RegisterForKey', 'OnKeyDown', 'GameHour', 'FormRulesAbility',
                 'GDomainFire', 'GDomainFrost', 'GDomainEarth', 'GDomainBlood', 'GDomainDivine', 'GDomainPoison', 'GDomainWater',
                 'GDomainDark', 'GDomainAstral', 'ExtendFuse', 'WashBuffs', 'AddStackTo', 'GetBloodHitMult',
                 'GCombo', 'ComboHits', 'ComboTime']   # round-25 review: the dead 連段
# round-25 review: Papyrus's second windows count the DLL's game-running clock, never real time.
WINDOW_FUNCTIONS = ['TickTimers', 'TimersActive', 'SecondsLeft', 'SetEmber', 'SetQuench', 'SetShockRecent', 'SetGuardSwitch',
                    'SetGuardIce', 'SetSyncKeep']
REMOVED_NATIVES = ['ExtendFuse', 'WashBuffs']
N6_EVENTS = {'ESSB_Switch': 'OnESSBSwitch', 'ESSB_Close': 'OnESSBClose'}


def code_only(text):
    return v22.code_only(text)


def scripts():
    return {p.name: p.read_text(encoding='utf-8-sig') for p in sorted(SRC.glob('*.psc'))}


def fn_body(text, name):
    m = re.search(r'\n' + re.escape(name) + r'\([^)]*\)[^{;]*\{(.*?)\n\}', text, re.S)
    return m[1] if m else None


# ---------------------------------------------------------------- CONTRACT / TIMER

def check_contract(sources, cpp, status_h, reactions, engine_h, timer_h):
    errors, counts = v24.check_contract(sources, cpp, status_h, reactions)
    names = v24.event_names(cpp, status_h)
    ctl = code_only(sources['ESSBController.psc'])
    for event, handler in N6_EVENTS.items():
        if event not in names.values():
            errors.append(f'{event}: not in the DLL\'s kEventNames')
        if f'RegisterForModEvent("{event}", "{handler}")' not in ctl:
            errors.append(f'{event}: ESSBController does not register {handler}')
    switch = re.search(r'(?ms)^Event OnESSBSwitch\(.*?^EndEvent', ctl)
    if not switch or 'SwitchForm(' not in switch[0]:
        errors.append('OnESSBSwitch does not change the form through SwitchForm')
    close = re.search(r'(?ms)^Event OnESSBClose\(.*?^EndEvent', ctl)
    if not close or 'CloseForm()' not in close[0]:
        errors.append('OnESSBClose does not close the form')
    domain = re.search(r'(?ms)^Event OnESSBDomain\(.*?^EndEvent', ctl)
    if not domain or 'PlaceFx(' not in domain[0] or re.search(r'StartDomain|Domain(Left|X|Elem)', domain[0]):
        errors.append('OnESSBDomain does more than the opening effect (the domain is the DLL\'s hazard)')
    request = fn_body(cpp, 'void RequestSwitch')
    if not request or 'essb::PlanSwitch(' not in request or 'essb::Event::kSwitch' not in request:
        errors.append('RequestSwitch does not decide through Timer.h PlanSwitch and send ESSB_Switch')
    if 'MakeEvent(Event::kClose)' not in timer_h:
        errors.append('Timer.h PlanFormSecond does not send ESSB_Close')
    native = code_only(sources['ESSBNative.psc'])
    if not re.search(r'(?m)^Function RequestSwitch\(Int aiElement\) Global Native', native):
        errors.append('ESSBNative.psc does not declare RequestSwitch(Int aiElement)')
    req = re.search(r'\n[^\n]*\bPapyrusRequestSwitch\(RE::StaticFunctionTag\*[^)]*\)\s*\{(.*?)\n\}', cpp, re.S)
    if not req or 'QueueNative("RequestSwitch"' not in req[1]:
        errors.append('ESSBNative.RequestSwitch does not queue its work on the main thread')
    for name in REMOVED_NATIVES:
        if re.search(r'\bFunction ' + name + r'\(', native) or f'RegisterFunction("{name}"' in cpp:
            errors.append(f'the {name} native is still declared or registered')
    run_op = re.search(r'void RunOp\(E& engine, const StatusOp& op, const Tuning& tuning\)\s*\{(.*?)\n\}', engine_h, re.S)
    if not run_op or 'DomainSpawnSpell(' not in run_op[1] or 'engine.Cast(Who::kTarget, spawn, 0.0f, 1.0f)' not in run_op[1]:
        errors.append('RunOp does not cast the domain\'s spawn spell (no magnitude override) for ESSB_Domain')
    if not run_op or 'engine.DrainMagickaAll(on)' not in run_op[1]:
        errors.append('RunOp does not drain the magicka when it silences')
    counts['n6_events'] = len(N6_EVENTS)
    return errors, counts


def check_timer(cpp):
    errors = []
    loop = fn_body(cpp, 'void TimerLoop')
    if not loop or 'state.tickQueued.exchange(true)' not in loop or loop.count('AddTask(') != 1:
        errors.append('TimerLoop does not post exactly one task a tick behind tickQueued (R3)')
    tick = fn_body(cpp, 'void TickCpp')
    guarded = fn_body(cpp, 'void TickGuarded')
    if not tick or 'AddTask(' in tick or (guarded and 'AddTask(' in guarded):
        errors.append('the timer task queues work itself (R3: never self-rescheduling)')
    if not tick or 'essb::Step(state.cadence' not in tick or 'GameStopped(ui)' not in tick or 'if (beat.second)' not in tick:
        errors.append('the timer task does not pace its per-second work on the game-running clock (N6-1)')
    stopped = fn_body(cpp, 'bool GameStopped')
    if not stopped or 'GameIsPaused()' not in stopped or 'LoadingMenu' not in stopped or 'state.inGame' not in stopped:
        errors.append('GameStopped does not cover pause, loading and the load gap')
    for needle, why in (('FormSecondWork(', 'the upkeep / 長流 / storm second'), ('EnvironmentCheck(', 'the environment'),
                        ('SilenceSecond(', 'the silence drain'), ('ScanDomains(', 'the domains'), ('PlanDomainSelf(', 'your domains'),
                        ('SlowImmunity(', 'the slow immunity')):
        if not tick or needle not in tick:
            errors.append(f'the timer task does not run {why}')
    if 'input->AddEventSink(&inputSink)' not in cpp:
        errors.append('the input sink is not registered on BSInputDeviceManager')
    sink = re.search(r'class InputSink final.*?\n\};', cpp, re.S)
    if not sink or 'return RE::BSEventNotifyControl::kContinue;' not in sink[0] or 'kStop' in sink[0]:
        errors.append('the input sink may consume input (it must always continue)')
    inp = fn_body(cpp, 'void InputCpp')
    if not inp or 'essb::InputOpen(' not in inp or 'IsDown()' not in inp or 'catch (...)' not in inp:
        errors.append('the input sink does not gate on InputOpen / key down, or has no C++ catch')
    # round-25 review: the 60 m domain scan only with a domain node; Papyrus's windows read the running clock.
    if 'essb::HasDomainNode(nodes) ? ScanDomains(' not in cpp:
        errors.append('the domain scan runs without the domain-node gate (Timer.h HasDomainNode)')
    if 'state.runningMs.fetch_add(' not in cpp or 'RegisterFunction("RunningSeconds", kClass, PapyrusRunningSeconds, true)' not in cpp:
        errors.append("ESSBNative.RunningSeconds is not the timer's running clock (an atomic, callable from tasklets)")
    return errors


# ---------------------------------------------------------------- REMOVED

def check_removed(sources, b):
    errors = []
    import fix21_history as h21
    controller = h21.functions(sources.get('ESSBController.psc', ''))
    for fn in WINDOW_FUNCTIONS:
        body = code_only(controller.get(fn, ''))
        if not body or 'GetCurrentRealTime' in body or 'Now()' not in body:
            errors.append(f'ESSBController.{fn}: a second window still counts real time (paused time) or is gone')
    if 'ESSBNative.RunningSeconds()' not in code_only(controller.get('Now', '')):
        errors.append('ESSBController.Now does not read the DLL game-running clock (ESSBNative.RunningSeconds)')
    for name in REMOVED_FILES:
        if (SRC / name).exists():
            errors.append(f'src/{name} still exists')
        if name[:-4] in b.SCRIPTS:
            errors.append(f'{name[:-4]} is still on build_v03.SCRIPTS')
    for script, text in sources.items():
        code = code_only(text)
        for name in REMOVED_NAMES:
            if re.search(r'\b' + name + r'\b', code):
                errors.append(f'{script}: still names {name}')
        if re.search(r'SetWindow\([^,]+,\s*3[2-5]\s*,', code):
            errors.append(f'{script}: sets one of the removed domain windows 32-35')
    # Shipped scripts only: ESSBProbeMeter is the round-18 damage-probe harness (its own probe package, not on
    # build_v03.SCRIPTS, no gameplay), and its 0.25 s / 1 s updates pace a measurement, not work v0.4 gives the DLL.
    effect_scripts = [n for n, t in sources.items() if n[:-4] in b.SCRIPTS
                      and re.search(r'(?m)^Scriptname \w+ extends ActiveMagicEffect', t)]
    for name in effect_scripts:
        if 'RegisterForSingleUpdate' in code_only(sources[name]):
            errors.append(f'{name}: an effect script still runs a Papyrus per-second loop')
    return errors


# ---------------------------------------------------------------- RECORDS / RESOLVE

def check_records(b):
    import fix25_records as rec
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    by = {r.edid: r for r in records}
    key = {r.edid: int(r.key.split('|')[1], 16) for r in records}
    errors = []

    def flags(r):
        return struct.unpack_from('<I', r.d['DATA'])[0]
    for kind, suffix, label, on_player, seconds, text in rec.KINDS:
        effect, spell = by.get(rec.edid_effect(suffix)), by.get(rec.edid_spell(suffix))
        if not effect or not spell:
            errors.append(f'{suffix}: record missing')
            continue
        if struct.unpack_from('<I', effect.d['DATA'], 64)[0] != 1 or not flags(effect) & 0x400:
            errors.append(f'{suffix}: must be Script with No Magnitude')
        if struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != int(seconds):
            errors.append(f'{suffix}: spell lasts {struct.unpack_from("<I", spell.d["EFIT"], 8)[0]} s, not {int(seconds)}')
        if struct.unpack_from('<I', spell.d['SPIT'], 20)[0] != (0 if on_player else 1):
            errors.append(f'{suffix}: delivery must be {"self" if on_player else "contact"}')
    spawns = 0
    for e in rec.DOMAIN_ELEMENTS:
        hazard, hspell, seffect = by.get(rec.hazard_edid(e)), by.get(rec.hazard_spell_edid(e)), by.get(rec.spawn_effect_edid(e))
        if not hazard or not hspell or not seffect:
            errors.append(f'domain {e}: HAZD / hazard spell / spawn effect missing')
            continue
        limit, radius, life, isr, interval, hflags, spell, light, ipds, sound = struct.unpack('<IffffIIIII', hazard.d['DATA'][:40])
        if (limit, hflags) != (rec.HAZARD_LIMIT, rec.HAZARD_FLAGS) or abs(radius - rec.DOMAIN_RADIUS_FEET) > 1e-3 or \
                abs(interval - rec.HAZARD_TARGET_INTERVAL) > 1e-6 or spell != b.own(rec.hazard_spell_id(e)):
            errors.append(f'{rec.hazard_edid(e)}: DATA is not 3 m / Inherit Duration + Drop to Ground / limit 0 / 0.3 s / its spell')
        if hazard.d.get('MODL', b'').rstrip(b'\0').decode('ascii', 'replace') != rec.HAZARD_MODEL:
            errors.append(f'{rec.hazard_edid(e)}: model is not the invisible vanilla hazard model')
        efids = [struct.unpack('<I', v)[0] for tag, v in hspell.ss if tag == 'EFID']
        want = [b.own(x[0]) for x in rec.hazard_effects(b, e)]
        if efids != want:
            errors.append(f'{rec.hazard_spell_edid(e)}: effects {[hex(x) for x in efids]} != {[hex(x) for x in want]}')
        data = seffect.d['DATA']
        if struct.unpack_from('<I', data, 64)[0] != 40 or struct.unpack_from('<I', data, 8)[0] != b.own(rec.hazard_id(e)):
            errors.append(f'{rec.spawn_effect_edid(e)}: not a Spawn Hazard effect placing its HAZD')
        if not flags(seffect) & rec.NO_DEATH_DISPEL or flags(seffect) & 0x5:
            errors.append(f'{rec.spawn_effect_edid(e)}: must be no-death-dispel and neither hostile nor detrimental')
        for s in range(1, rec.DOMAIN_MAX_SECONDS + 1):
            spell = by.get(rec.spawn_edid(e, s))
            if not spell or struct.unpack('<I', spell.d['EFID'])[0] != b.own(rec.spawn_effect_id(e)) or \
                    struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != s or struct.unpack_from('<f', spell.d['EFIT'], 0)[0] != 0.0:
                errors.append(f'{rec.spawn_edid(e, s)}: not the {s} s spawn spell with magnitude 0')
            spawns += 1
    for edid in ('ESSB_FormRulesEffect', 'ESSB_SilenceEffect'):
        if 'VMAD' in by[edid].d:
            errors.append(f'{edid} still carries a script')
    quest = by.get('ESSB_MainQuest')
    vmad = quest.d.get('VMAD', b'') if quest else b''
    for needle in (b'ESSBInput', b'InputLayer', b'GameHour', b'FormRulesAbility', b'GDomainDivine', b'GDomainFire', b'ReactSpells'):
        if needle in vmad:
            errors.append(f'the main quest VMAD still carries {needle.decode()}')
    if b'ESSBController' not in vmad or b'ESSBTrees' not in vmad:
        errors.append('the main quest VMAD lost ESSBController or ESSBTrees')
    settings = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))
    if settings.get('state_schema_version') != 14:
        errors.append(f'state_schema_version is {settings.get("state_schema_version")}, not 14 (R1: one bump this round)')
    # round-25 review (commander's ruling): 聖域「其中敵人傷害 -20%」is the divine hazard spell's own two harmful effects
    # on the enemies inside (AttackDamageMult -0.2, DestructionPowerModifier -20, 2 s like the marker); no PERK reads the
    # old ESSB_DomainDivine mirror any more.
    mirror = b.own(b.ID_MECH2_GLOB + [n for n, _ in b.MECH2_GLOBALS].index('ESSB_DomainDivine'))
    for r in records:
        if r.sig == 'PERK' and any(tag == 'CTDA' and struct.unpack_from('<I', v, 12)[0] == mirror for tag, v in r.ss):
            errors.append(f'{r.edid}: a PERK still reads ESSB_DomainDivine (聖域 is the hazard\'s effects now)')
    hspell = by.get(rec.hazard_spell_edid(7))
    efits = [(struct.unpack('<I', v)[0]) for tag, v in hspell.ss if tag == 'EFID'] if hspell else []
    mags = [struct.unpack('<fII', v) for tag, v in hspell.ss if tag == 'EFIT'] if hspell else []
    for wkey, suffix, label, av, magnitude in rec.DIVINE_WEAKEN:
        effect = by.get(rec.weaken_edid(wkey))
        if not effect:
            errors.append(f'{rec.weaken_edid(wkey)} missing')
            continue
        data = effect.d['DATA']
        if struct.unpack_from('<I', data, 64)[0] != 34 or struct.unpack_from('<i', data, 68)[0] != av or \
                flags(effect) & 0x5 != 0x5:
            errors.append(f'{rec.weaken_edid(wkey)}: not a hostile, detrimental Peak Value Modifier on AV {av}')
        own = b.own(rec.weaken_id(wkey))
        if own not in efits or abs(mags[efits.index(own)][0] - magnitude) > 1e-5 or mags[efits.index(own)][2] != rec.MARKER_SECONDS:
            errors.append(f'{rec.hazard_spell_edid(7)}: {label} is not on it at {magnitude} for {rec.MARKER_SECONDS} s')
    if not by.get(rec.THUNDER_GLOBAL):
        errors.append('ESSB_EnvThunder (雷雨) GLOB missing')
    return errors, len(rec.KINDS), spawns, by, key


def check_resolve(by, key):
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    by_local = {v: k for k, v in key.items()}
    errors, count = [], 0
    for effect, spell, _s, _p, _st, edid in re.findall(
            r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), ([\d.]+)f, (true|false), (true|false), "(ESSB_N6_\w+)"\}', header):
        count += 2
        if by_local.get(int(spell, 16)) != edid or by_local.get(int(effect, 16)) != edid + 'Effect':
            errors.append(f'status record {edid}: spell / effect ids do not match the ESP')
    for table, prefix in (('kDomainHazard', 'ESSB_N6_Hazard_'), ('kDomainSpawnEffect', 'ESSB_N6_DomainEffect_')):
        m = re.search(table + r'\[12\] = \{(.*?)\};', header)
        ids = [int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', m[1])] if m else []
        if len(ids) != 9:
            errors.append(f'{table}: {len(ids)} domains, not 9')
        for fid in ids:
            count += 1
            if not by_local.get(fid, '').startswith(prefix):
                errors.append(f'{table}: {fid:#x} is not an {prefix}* record')
    m = re.search(r'kDomainSpawn\[12\]\[\d+\] = \{(.*?)\n\};', header, re.S)
    for fid in re.findall(r'0x[0-9a-fA-F]+', m[1] if m else ''):
        count += 1
        if not by_local.get(int(fid, 16), '').startswith('ESSB_N6_Domain_'):
            errors.append(f'spawn spell {fid} is not an ESSB_N6_Domain_* record')
    return errors, count


# ---------------------------------------------------------------- NODES

def check_nodes():
    data = json.loads((ROOT / 'build/plan-coverage.json').read_text(encoding='utf-8'))
    errors = []
    for row in data['rows']:
        status = row['status']
        if status.endswith('-N6') or '待決' in status or status.startswith('PARTIAL') or status.startswith('LATER') or status.startswith('KEPT'):
            errors.append(f'{row["tree"]} {row["name"] if row["kind"] == "node" else row["text"]}: status {status}')
    by = {(r['tree'], r['name']): r for r in data['rows'] if r['kind'] == 'node'}
    for key in (('divine', '神聖領域'), ('poison', '毒霧')):
        if by.get(key, {}).get('status') != 'DONE':
            errors.append(f'{key}: not DONE')
    return errors, len(data['rows'])


# ---------------------------------------------------------------- FAULTS

def run_timer_test(table, wiring):
    exe = ROOT / 'native/out/Release/timer_test.exe'
    with tempfile.TemporaryDirectory() as tmp:
        t, w = Path(tmp) / 't.json', Path(tmp) / 'w.json'
        t.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')
        w.write_text(json.dumps(wiring, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([str(exe), str(t), str(w)], capture_output=True, text=True, encoding='utf-8', errors='replace').returncode


def check_faults():
    table = json.loads((ROOT / 'build/fix25-timer-table.json').read_text(encoding='utf-8'))
    wiring = json.loads((ROOT / 'build/fix25-wiring.json').read_text(encoding='utf-8'))
    assert run_timer_test(table, wiring) == 0, 'the unmutated tables must pass'
    faults = []

    def fault(label, mutate_table=None, mutate_wiring=None):
        t, w = copy.deepcopy(table), copy.deepcopy(wiring)
        if mutate_table:
            mutate_table(t)
        if mutate_wiring:
            mutate_wiring(w)
        assert run_timer_test(t, w) != 0, f'injected fault not caught: {label}'
        faults.append(label)

    def scenario(t, prefix):
        return next(s for s in t['scenarios'] if s['name'].startswith(prefix))

    def upkeep(t):
        scenario(t, 'upkeep: fire, tree 1')['expect']['ops'][0][2] *= 1.01
    fault('an upkeep 1% stronger', upkeep)

    def no_close(t):
        s = scenario(t, 'upkeep: empty 2 s')
        s['expect']['ops'] = [o for o in s['expect']['ops'] if o[0] != 'event']
    fault('魔力歸零 without closing the form', no_close)

    def wash_all(t):
        s = scenario(t, 'enemy in 潮池')
        s['expect']['ops'][0][2] = 0.0
    fault('潮池 washing every buff', wash_all)

    def slot(t):
        scenario(t, 'hotkey 83 enabled=True')['expect']['element'] = 10
    fault('a hotkey switching to the wrong form', slot)

    def beat(t):
        scenario(t, 'clock: a 30 s pause')['expect']['beats'][20][0] = 1
    fault('a second counted during a pause', beat)

    def spawn(w):
        w['domains'][0]['spawn'][4] += 1
    fault('a spawn spell FormID off by one', mutate_wiring=spawn)

    def kind(w):
        w['kinds'][0]['seconds'] = 3.0
    fault('a marker lasting 3 s (not 2)', mutate_wiring=kind)
    return faults


# ---------------------------------------------------------------- ENDINGS / MUTANTS

TOUCHED = ['build_v03.py', 'plan_coverage.py', 'settings.json', 'native/CMakeLists.txt', 'native/build.py',
           'native/include/Status.h', 'native/include/StatusEngine.h', 'native/src/Plugin.cpp', 'native/tests/engine_test.cpp',
           'native/tests/status_test.cpp', 'native/tests/self_test.cpp', 'native/tests/reaction_test.cpp', 'build/fix19_native.py',
           'build/fix22_fixture.py', 'build/fix6_verify.py', 'build/fix21_identity.py', 'build/fix24_verify.py',
           'build/fix24_history.py', 'build/fix24_history_template.py', 'build/fix24_native_history.py',
           'build/fix24_native_history_template.py', '實作紀錄.md', 'build/native-verification.md']


def check_endings():
    errors = []
    pairs = [(p, SNAPSHOT / 'src' / p.name) for p in sorted(SRC.glob('*.psc'))]
    pairs += [(ROOT / rel, SNAPSHOT / rel) for rel in TOUCHED]
    for now_path, before in pairs:
        if not before.exists() or not now_path.exists():
            continue
        was, now = before.read_bytes(), now_path.read_bytes()
        was_crlf = was.count(b'\r\n') == was.count(b'\n') and b'\r\n' in was
        now_crlf = now.count(b'\r\n') == now.count(b'\n') and b'\r\n' in now
        now_lf = b'\r\n' not in now
        name = now_path.relative_to(ROOT).as_posix()
        if was_crlf and not now_crlf:
            errors.append(f'{name}: was CRLF, now {"LF" if now_lf else "mixed"}')
        elif not was_crlf and not now_lf:
            errors.append(f'{name}: was LF, now has CRLF')
        if was.startswith(b'\xef\xbb\xbf') != now.startswith(b'\xef\xbb\xbf'):
            errors.append(f'{name}: the byte-order mark changed')
    return errors


def check_mutants():
    receipt = json.loads((ROOT / 'native/out/build-receipt.json').read_text(encoding='utf-8'))
    mutants = receipt.get('mutants') or []
    assert all(m['exit'] != 0 for m in mutants), 'a native mutant survived'
    n6 = [m for m in mutants if m['test'] == 'timer']
    assert len(n6) >= 5 and sum(1 for m in n6 if m['header'] == 'Timer.h') >= 5, ('fewer than 5 round-25 C++ mutants', len(n6))
    return mutants, n6


# ---------------------------------------------------------------- self test of the source checks

def self_test(sources, cpp, status_h, reactions, engine_h, timer_h, b):
    caught = []

    def expect(label, errors, needle):
        assert any(needle in e for e in errors), (label, 'fault not caught', errors[:3])
        caught.append(label)

    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('RegisterForModEvent("ESSB_Close", "OnESSBClose")', '', 1)
    expect('ESSB_Close no longer handled', check_contract(s, cpp, status_h, reactions, engine_h, timer_h)[0], 'does not register OnESSBClose')
    expect('the domain spawn overriding the magnitude',
           check_contract(sources, cpp, status_h, reactions, engine_h.replace('engine.Cast(Who::kTarget, spawn, 0.0f, 1.0f)',
                                                                             'engine.Cast(Who::kTarget, spawn, 5.0f, 1.0f)', 1), timer_h)[0],
           'spawn spell')
    expect('a timer task that queues itself',
           check_timer(cpp.replace('        LogThreadOnce(Probe::kTick, "timer task");',
                                   '        LogThreadOnce(Probe::kTick, "timer task");\n        SKSE::GetTaskInterface()->AddTask([]() { TickGuarded(); });', 1)),
           'queues work itself')
    expect('the clock running through a pause',
           check_timer(cpp.replace('return ui && (ui->GameIsPaused() || ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME));',
                                   'return ui && ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME);', 1)), 'GameStopped')
    expect('an input sink that eats the key',
           check_timer(cpp.replace('            Fault("access violation in the input sink");\n        }\n        return RE::BSEventNotifyControl::kContinue;',
                                   '            Fault("access violation in the input sink");\n        }\n        return RE::BSEventNotifyControl::kStop;', 1)),
           'may consume input')
    s = dict(sources)
    s['ESSBElem3.psc'] += '\nFunction Probe25(ESSBController akCtl) Global\n\takCtl.StartDomain(1, None, 5)\nEndFunction\n'
    expect('a call into the deleted Papyrus domains', check_removed(s, b), 'still names StartDomain')
    s = dict(sources)
    s['ESSBCounter.psc'] += '\nEvent OnUpdate()\n\tRegisterForSingleUpdate(1.0)\nEndEvent\n'
    expect('a per-second loop in an effect script', check_removed(s, b), 'per-second loop')
    s = dict(sources)   # round-25 review: a window back on real time (it would run through a pause)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('Float remaining = afDeadline - Now()',
                                                              'Float remaining = afDeadline - Utility.GetCurrentRealTime()', 1)
    expect('a second window on real time', check_removed(s, b), 'counts real time')
    return caught


def run(b):
    sources = scripts()
    cpp = PLUGIN_CPP.read_text(encoding='utf-8')
    status_h = STATUS_H.read_text(encoding='utf-8')
    reactions = REACTIONS_H.read_text(encoding='utf-8')
    engine_h = ENGINE_H.read_text(encoding='utf-8')
    timer_h = TIMER_H.read_text(encoding='utf-8')
    errors, counts = check_contract(sources, cpp, status_h, reactions, engine_h, timer_h)
    errors += check_timer(cpp) + check_removed(sources, b)
    record_errors, kinds, spawns, by, key = check_records(b)
    resolve_errors, resolved = check_resolve(by, key)
    node_errors, rows = check_nodes()
    errors += record_errors + resolve_errors + node_errors + v22.check_guards(cpp) + check_endings()
    assert not errors, '\n  '.join(['FIX25 failed:'] + errors)
    caught = self_test(sources, cpp, status_h, reactions, engine_h, timer_h, b)
    faults = check_faults()
    import fix25_history
    history = fix25_history.self_check()
    import fix25_native_history
    native_history = fix25_native_history.self_check()
    mutants, n6 = check_mutants()
    report = dict(contract=counts, kinds=kinds, spawn_spells=spawns, resolved=resolved, plan_rows=rows, source_faults=caught,
                  native_faults=faults, history=history, native_history=native_history, native_mutants=[m['name'] for m in n6])
    (ROOT / 'build/fix25-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX25 ok: {counts["natives"]} natives declared = registered (RequestSwitch queued; ExtendFuse / WashBuffs gone); '
          f'{counts["n6_events"]} round-25 ModEvents sent and handled (ESSB_Switch -> SwitchForm, ESSB_Close -> CloseForm); '
          f'the domain event casts its spawn spell without an override; the timer posts one task a tick, never itself, and '
          f'counts only running game time; the input sink never consumes and gates on the console / text / menus; '
          f'ESSBFormRules / ESSBInput / ESSBSilence and every Papyrus domain / environment / 長流 / key-polling name gone, no '
          f'effect-script update loop left; {kinds} round-25 kinds, 9 domains and {spawns} spawn spells read back, schema 14; '
          f'{resolved} DLL FormIDs resolve; {rows} plan rows with no -N6 / 待決 / PARTIAL left; sinks / tasks / natives guarded; '
          f'line endings kept; {len(caught)}/{len(caught)} source faults and {len(faults)}/{len(faults)} timer-test faults caught; '
          f'history: {history["changed"]} changed / {history["removed"]} removed / {history["added"]} added functions and '
          f'{history["files"]} whole scripts declared, {len(history["silent_edits_caught"])} silent edits caught; native seal: '
          f'{native_history["changed"]} changed / {native_history["added"]} added / {native_history["unchanged"]} unchanged, '
          f'{len(native_history["silent_edits_caught"])} silent edits caught; {len(n6)} round-25 C++ mutants failed ({len(mutants)} in all)')
