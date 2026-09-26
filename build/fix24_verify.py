"""Round 24 (N5: the reaction bodies, the fusion and the death handling in the DLL): offline checks of what this round
changed, each with injected faults.

  CONTRACT   the round-22 / 23 seam checks on today's sources (natives declared = registered with the same arity, every
             ModEvent the DLL can send registered to a handler reading no more than is sent) plus: the five round-24 events
             (ESSB_Push, ESSB_Ash, ESSB_Raise, ESSB_Sneak, ESSB_Domain) are sent and handled; the body-only events
             (Reactions.h BodyOnly) are refused by SendEvent and registered by no script; no death snapshot (ESSB_Death) is
             sent; the death sink handles only dead = false, never you, through DeathCounts, and hands a task the read
             snapshot; the burst is one native (ESSBNative.Burst) called from OnFormClosed.
  REMOVED    ruling R4: ESSBGuard.psc and ESSBReactions.psc are gone (and off the compile list and the quest VMAD); no script
             registers the Papyrus kill event or names a removed function / native; OnFormClosed / OnFormOpened scan nothing.
  RECORDS    read back from the written ESP: every round-24 kind (markers and windows: Script, No Magnitude, the record
             seconds, the right delivery; 血承: Peak Value Modifiers on the right actor value), every timed family (one
             spell a whole second, on the shared utility effect), 安全閥's PERK entry reads ESSB_N5_SafetyValve, the quest's
             player alias carries three scripts; settings.json state_schema_version 13.
  RESOLVE    every ESSB_N5_ status record and timed spell ManifestData.h names exists in the ESP under that editor id.
  GUARDS     every event sink and task behind SEH + C++ catch; every native through Guard (the round-22 check).
  FAULTS     reaction_test fails on a mutated table (a magnitude, a missing op, an extra board entry, the wrong member, a
             wiring FormID).
  ENDINGS    every file this round touched keeps its pre-round line endings (CRLF or LF).
  MUTANTS    the C++ source mutations of native/build.py on Reactions.h all failed (receipt), >= 5.
  HISTORY    build/fix24_history.py (Papyrus, digest-bound, silent edits caught) and build/fix24_native_history.py (DLL,
             tests, generator modules, verifiers; sha256-bound, silent edits caught); the round-23 seals read the pre-fix24
             snapshot only after these proofs.
"""
from pathlib import Path
import copy, json, re, struct, subprocess, sys, tempfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SRC = ROOT / 'src'
SNAPSHOT = ROOT / '.codex/pre-fix24-snapshot'
PLUGIN_CPP = ROOT / 'native/src/Plugin.cpp'
STATUS_H = ROOT / 'native/include/Status.h'
REACTIONS_H = ROOT / 'native/include/Reactions.h'

import fix22_verify as v22
import fix23_verify as v23

N5_EVENTS = ['ESSB_Push', 'ESSB_Ash', 'ESSB_Raise', 'ESSB_Sneak', 'ESSB_Domain']
REMOVED_FILES = ['ESSBGuard.psc', 'ESSBReactions.psc']
REMOVED_NAMES = ['ESSBReactions', 'ESSBGuard', 'OnKillEvent', 'SettleKill', 'SettleStaleKills', 'KillPending', 'HasDeathSnapshot',
                 'SettleSneakKill', 'ArmKillProc', 'SettleKillProc', 'KillElementFor', 'ApplyInherit', 'ApplyTrackedDamage',
                 'NoteDamageElement', 'LastDamageFor', 'OnESSBDeath', 'OnESSBFrozen', 'OnESSBJudgment', 'OnESSBSplash',
                 'OnESSBRise', 'OnESSBShatter', 'OnESSBLanding', 'OnESSBDischarge', 'OnESSBBlade', 'OnLanding', 'LethalAmbush',
                 'TryKillStreak', 'ShatterArea', 'DischargeAll', 'JudgeArea', 'SurgeOn', 'EndWind', 'ChainEnd', 'ForceOpenOn',
                 'SetGuardBurst', 'SetDoubleBurst', 'DoubleBurstLeft', 'GuardBurstLeft', 'BurstMarks', 'EndMark', 'DotRemaining',
                 'SetGuided', 'RegisterForActorKilled', 'OnActorKilled', 'InheritSpell', 'SpreadPoison']
REMOVED_NATIVES = ['BurstMarks', 'SetGuided', 'DotRemaining', 'ForceOpen', 'EndMark', 'Shatter', 'Detonate', 'MarkedNear']
# review fix 1: the natives that scan or cast only queue their work (QueueNative -> AddTask) and return
# round 25 (N6): ExtendFuse and WashBuffs lost their only callers (the Papyrus domains) and are gone; build/fix25_verify.py
# checks that, and that RequestSwitch is queued too.
QUEUED_NATIVES = ['Burst', 'FormEnter', 'FormLeave', 'SetSync', 'AddStatus', 'SetStatus', 'ClearStatus', 'SetWindow', 'ApplyMark',
                  'CastProc', 'DumpTargets']


def code_only(text):
    return v22.code_only(text)


def scripts():
    return {p.name: p.read_text(encoding='utf-8-sig') for p in sorted(SRC.glob('*.psc'))}


# ---------------------------------------------------------------- CONTRACT

def body_only(reactions):
    fn = re.search(r'constexpr bool BodyOnly\(Event e\) noexcept\s*\{(.*?)\n\}', reactions, re.S)
    return set(re.findall(r'Event::(k\w+)', fn[1])) if fn else set()


def event_names(cpp, status_h):
    names = re.findall(r'"(ESSB_\w+)"', re.search(r'kEventNames\[\] = \{([^}]*)\}', cpp)[1])
    enum = re.search(r'enum class Event : std::uint8_t\s*\{(.*?)\n\};', status_h, re.S)[1]
    kinds = [m for m in re.findall(r'^\s*(k\w+),', enum, re.M) if m != 'kCount']
    return dict(zip(kinds, names))


def check_contract(sources, cpp, status_h, reactions):
    errors, counts = v23.check_contract(sources, cpp, status_h)
    sent = v22.events_sent(cpp, status_h + ''.join((ROOT / 'native/include' / h).read_text(encoding='utf-8')
                                                   for h in ('SelfLayer.h', 'Hurt.h')))
    for name in N5_EVENTS:
        if name not in sent:
            errors.append(f'{name}: the DLL does not send it')
        elif not re.search(r'MakeEvent\(\s*(?:essb::)?Event::k' + name[5:] + r'\b', reactions):
            errors.append(f'{name}: no body in Reactions.h builds it')
    names = event_names(cpp, status_h)
    ctl = code_only(sources['ESSBController.psc'])
    registered = set(re.findall(r'RegisterForModEvent\("(ESSB_\w+)"', ctl))
    only = body_only(reactions)
    if len(only) < 9:
        errors.append(f'Reactions.h BodyOnly names {len(only)} events, not the 9 bodies')
    for kind in sorted(only):
        if names.get(kind) in registered:
            errors.append(f'{names.get(kind)} is a body-only event but ESSBController still registers it')
    send = re.search(r'void SendEvent\(.*?\n\}', cpp, re.S)
    if not send or 'essb::BodyOnly(op.event)' not in send[0]:
        errors.append('SendEvent does not refuse the body-only events')
    if '"ESSB_Death"' in cpp or re.search(r'std::array<float, \d+> value', cpp):
        errors.append('the DLL still builds the ESSB_Death snapshot')
    death = re.search(r'void OnDeathCpp\(const RE::TESDeathEvent& ev\) noexcept\s*\{(.*?)\n\}', cpp, re.S)
    if not death:
        errors.append('no death sink (OnDeathCpp)')
    else:
        body = death[1]
        for needle, why in (('if (e.dead || e.dyingIsYou) {', 'handles only dead = false and never your own death'),
                            ('essb::engine::DeathCounts(e,', 'goes through DeathCounts'),
                            ('AddTask(', 'hands the plan to a task (no scan in the sink)'),
                            ('ReadMember(snapshot.corpse', 'reads the corpse in the sink, while its effects are there')):
            if needle not in body:
                errors.append(f'the death sink no longer {why}')
        if 'ProcessLists' in body or 'BuildCrowd' in body:
            errors.append('the death sink scans the process list itself (R3: scans run in the task)')
    closed = re.search(r'(?ms)^Function OnFormClosed\(Int aiIndex\).*?^EndFunction', ctl)
    if not closed or 'ESSBNative.Burst(aiIndex)' not in closed[0]:
        errors.append('OnFormClosed does not burst through ESSBNative.Burst(aiIndex)')
    for fn in ('OnFormClosed', 'OnFormOpened'):
        block = re.search(r'(?ms)^Function ' + fn + r'\(Int aiIndex\).*?^EndFunction', ctl)
        if block and re.search(r'\bScanTargets\(|\bForceOpenOn\(|\bMarkedNear\(', block[0]):
            errors.append(f'{fn} still scans or opens on its own (R4: the DLL does)')
    for name in QUEUED_NATIVES:
        fn = re.search(r'\n[^\n]*\bPapyrus' + name + r'\(RE::StaticFunctionTag\*[^)]*\)\s*\{(.*?)\n\}', cpp, re.S)
        if not fn or 'QueueNative("' + name + '"' not in fn[1]:
            errors.append(f'ESSBNative.{name} scans or casts outside a queued task (review fix 1)')
    queue = re.search(r'bool QueueNative\(.*?\n\}', cpp, re.S)
    if not queue or 'AddTask(' not in queue[0]:
        errors.append('QueueNative does not hand the work to SKSE AddTask')
    counts['queued_natives'] = len(QUEUED_NATIVES)
    counts['n5_events'] = len(N5_EVENTS)
    counts['body_only'] = len(only)
    return errors, counts


# ---------------------------------------------------------------- REMOVED

def check_removed(sources, b):
    errors = []
    for name in REMOVED_FILES:
        if (SRC / name).exists():
            errors.append(f'src/{name} still exists (R4)')
        if name[:-4] in b.SCRIPTS:
            errors.append(f'{name[:-4]} is still on build_v03.SCRIPTS')
    for script, text in sources.items():
        code = code_only(text)
        for name in REMOVED_NAMES:
            if re.search(r'\b' + name + r'\b', code):
                errors.append(f'{script}: still names {name}')
    native = code_only(sources['ESSBNative.psc'])
    for name in REMOVED_NATIVES:
        if re.search(r'\bFunction ' + name + r'\(', native):
            errors.append(f'ESSBNative.psc still declares {name}')
    if not re.search(r'(?m)^Function Burst\(Int aiElement\) Global Native', native):
        errors.append('ESSBNative.psc does not declare Burst(Int aiElement) (no return value: the burst is queued)')
    return errors


# ---------------------------------------------------------------- RECORDS / RESOLVE

def check_records(b):
    import fix24_records as rec
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    by = {r.edid: r for r in records}
    errors = []

    def flags(r):
        return struct.unpack_from('<I', r.d['DATA'])[0]
    for kind, suffix, label, on_player, seconds, hidden, text, av in rec.KINDS:
        effect, spell = by.get(rec.edid_effect(suffix)), by.get(rec.edid_spell(suffix))
        if not effect or not spell:
            errors.append(f'{suffix}: record missing')
            continue
        archetype = struct.unpack_from('<I', effect.d['DATA'], 64)[0]
        if av is None:
            if archetype != 1 or not flags(effect) & 0x400:
                errors.append(f'{suffix}: a marker / window must be Script with No Magnitude (archetype {archetype})')
        elif archetype != 34 or struct.unpack_from('<i', effect.d['DATA'], 68)[0] != av:
            errors.append(f'{suffix}: 血承 must be a Peak Value Modifier on actor value {av}')
        if struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != int(seconds):
            errors.append(f'{suffix}: spell lasts {struct.unpack_from("<I", spell.d["EFIT"], 8)[0]} s, not {int(seconds)}')
        if struct.unpack_from('<I', spell.d['SPIT'], 20)[0] != (0 if on_player else 1):
            errors.append(f'{suffix}: delivery must be {"self" if on_player else "contact"}')
    timed = 0
    for util, name in rec.TIMED:
        effect_key = b.own(b.util_effect_id(util))
        for s in range(1, rec.TIMED_MAX_SECONDS + 1):
            spell = by.get(rec.timed_edid(name, s))
            if not spell:
                errors.append(f'{rec.timed_edid(name, s)} missing')
                continue
            efid = struct.unpack('<I', spell.d['EFID'])[0]
            if efid != effect_key or struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != s:
                errors.append(f'{rec.timed_edid(name, s)}: not the shared utility effect for {s} s')
            if struct.unpack_from('<I', spell.d['SPIT'], 20)[0] != (0 if util in rec.SELF_UTILS else 1):
                errors.append(f'{rec.timed_edid(name, s)}: wrong delivery')
            timed += 1
    reanimate = by.get('ESSB_ReanimateSpell')
    attack = by.get(rec.SERVANT_ATTACK_EDID)
    efids = [struct.unpack('<I', v)[0] for tag, v in reanimate.ss if tag == 'EFID'] if reanimate else []
    if not attack or len(efids) != 2 or efids[1] != b.own(rec.SERVANT_ATTACK_EFFECT):
        errors.append('ESSB_ReanimateSpell does not carry the servant attack effect as its second effect (review fix 3)')
    elif (struct.unpack_from('<I', attack.d['DATA'], 64)[0] != 34 or struct.unpack_from('<i', attack.d['DATA'], 68)[0] != 154
          or not struct.unpack_from('<I', attack.d['DATA'])[0] & rec.NO_DEATH_DISPEL):
        errors.append('the servant attack effect is not a no-death-dispel Peak Value Modifier on AttackDamageMult')
    valve = by.get('ESSB_P_common_2_3_B2')
    fid = b.own(rec.effect_id('kSafetyValve'))
    if not valve or not any(struct.unpack_from('<i', v, 12)[0] == fid for tag, v in valve.ss if tag == 'CTDA'):
        errors.append('安全閥: the PERK entry does not read ESSB_N5_SafetyValve')
    quest = next((r for r in records if r.sig == 'QUST' and r.edid == 'ESSB_MainQuest'), None)
    if not quest or b'ESSBGuard' in quest.d.get('VMAD', b'') or b'ESSBController' not in quest.d.get('VMAD', b''):
        errors.append('the main quest VMAD still carries ESSBGuard (or lost ESSBController)')
    # round 25 (N6) bumped the schema again (R1); round 24's bump is checked on the settings round 24 shipped
    settings = json.loads((ROOT / '.codex/pre-fix25-snapshot/settings.json').read_text(encoding='utf-8'))
    if settings.get('state_schema_version') != 13:
        errors.append(f'state_schema_version is {settings.get("state_schema_version")}, not 13 (R1: one bump this round)')
    return errors, len(rec.KINDS), timed, by


def check_resolve(by):
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    by_local = {}
    for edid, r in by.items():
        try:
            by_local[int(r.key.split('|')[1], 16)] = edid
        except (ValueError, IndexError):
            pass
    errors, count = [], 0
    for effect, spell, _s, _p, _st, edid in re.findall(
            r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), ([\d.]+)f, (true|false), (true|false), "(ESSB_N5_\w+)"\}', header):
        count += 2
        if by_local.get(int(spell, 16)) != edid or by_local.get(int(effect, 16)) != edid + 'Effect':
            errors.append(f'status record {edid}: spell / effect ids do not match the ESP')
    timed = re.search(r'kTimed\[\d+\]\[\d+\] = \{(.*?)\};', header, re.S)
    if not timed:
        errors.append('ManifestData.h has no kTimed table')
    else:
        for fid in re.findall(r'0x[0-9a-fA-F]+', timed[1]):
            count += 1
            if not by_local.get(int(fid, 16), '').startswith('ESSB_N5_Timed'):
                errors.append(f'timed spell {fid} is not an ESSB_N5_Timed* record in the ESP')
    return errors, count


# ---------------------------------------------------------------- FAULTS

def run_reaction_test(table, wiring):
    exe = ROOT / 'native/out/Release/reaction_test.exe'
    with tempfile.TemporaryDirectory() as tmp:
        t, w = Path(tmp) / 't.json', Path(tmp) / 'w.json'
        t.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')
        w.write_text(json.dumps(wiring, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([str(exe), str(t), str(w)], capture_output=True, text=True, encoding='utf-8', errors='replace').returncode


def check_faults():
    table = json.loads((ROOT / 'build/fix24-body-table.json').read_text(encoding='utf-8'))
    wiring = json.loads((ROOT / 'build/fix24-wiring.json').read_text(encoding='utf-8'))
    assert run_reaction_test(table, wiring) == 0, 'the unmutated tables must pass'
    faults = []

    def fault(label, mutate_table=None, mutate_wiring=None):
        t, w = copy.deepcopy(table), copy.deepcopy(wiring)
        if mutate_table:
            mutate_table(t)
        if mutate_wiring:
            mutate_wiring(w)
        assert run_reaction_test(t, w) != 0, f'injected fault not caught: {label}'
        faults.append(label)

    def scenario(t, prefix):
        return next(s for s in t['scenarios'] if s['name'].startswith(prefix))

    def burst_off(t):
        op = next(o for o in scenario(t, 'burst: stage 2')['expect']['ops'] if o[0] == 'damage')
        op[-1] *= 1.01
    fault('a burst 1% stronger', burst_off)

    def drop_raise(t):
        s = scenario(t, 'death: 亡者歸來 — level 20')
        s['expect']['ops'] = [o for o in s['expect']['ops'] if o[:3] != ['event', 0, 'Raise']]
    fault('亡者歸來 missing', drop_raise)

    def extra_poison(t):
        scenario(t, 'death: the poison spreads')['expect']['members'][9]['PoisonDot'] = [1.25, 12.0]   # the follower
    fault('the poison death spread reaching the follower', extra_poison)

    def wrong_member(t):
        op = next(o for o in scenario(t, 'frost open: 霜結')['expect']['ops'] if o[0] == 'slow' and o[1] == 1)
        op[1] = 2
    fault('寒潮 on the wrong member', wrong_member)

    def undying_heal(t):
        op = next(o for o in scenario(t, 'death: 飲血')['expect']['ops'] if o[0] == 'heal' and abs(o[2] - 11.0) < 1e-6)
        op[2] = 10.0
    fault('不死 heals to the line, not one over it', undying_heal)

    def wiring_id(w):
        w['timed'][0]['spells'][4] += 1
    fault('a timed spell FormID off by one', mutate_wiring=wiring_id)
    return faults


# ---------------------------------------------------------------- ENDINGS / MUTANTS

TOUCHED = ['build_v03.py', 'plan_coverage.py', 'settings.json', 'native/CMakeLists.txt', 'native/build.py',
           'native/include/HitMath.h', 'native/include/Status.h', 'native/include/StatusEngine.h', 'native/include/SelfLayer.h',
           'native/include/EngineFacts.h', 'native/src/Plugin.cpp', 'native/tests/engine_test.cpp', 'native/tests/status_test.cpp',
           'native/tests/self_test.cpp', 'build/fix19_native.py', 'build/fix22_fixture.py', 'build/fix22_reference.py',
           'build/fix6_verify.py', 'build/fix11_verify.py', 'build/fix16_verify.py', 'build/fix21_identity.py',
           'build/fix22_verify.py', 'build/fix23_verify.py', 'build/fix23_history.py', 'build/fix23_history_template.py',
           'build/fix23_native_history.py', 'build/fix23_native_history_template.py']


def check_endings():
    errors = []
    pairs = [(p, SNAPSHOT / 'src' / p.name) for p in sorted(SRC.glob('*.psc'))]
    pairs += [(ROOT / rel, SNAPSHOT / rel) for rel in TOUCHED]
    for now_path, before in pairs:
        if not before.exists():
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
    n5 = [m for m in mutants if m['header'] == 'Reactions.h']
    assert len(n5) >= 5, ('fewer than 5 round-24 C++ mutants', len(n5))
    return mutants, n5


# ---------------------------------------------------------------- self test of the source checks

def self_test(sources, cpp, status_h, reactions, b):
    caught = []

    def expect(label, errors, needle):
        assert any(needle in e for e in errors), (label, 'fault not caught', errors[:3])
        caught.append(label)

    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('RegisterForModEvent("ESSB_Knock", "OnESSBKnock")',
                                                              'RegisterForModEvent("ESSB_Knock", "OnESSBKnock")\r\n\tRegisterForModEvent("ESSB_Frozen", "OnESSBKnock")', 1)
    expect('a body-only event registered in Papyrus', check_contract(s, cpp, status_h, reactions)[0], 'is a body-only event')
    expect('SendEvent lets the bodies through', check_contract(sources, cpp.replace('if (essb::BodyOnly(op.event)) {', 'if (false) {', 1),
                                                                status_h, reactions)[0], 'does not refuse')
    expect('a native casting on the VM thread', check_contract(sources, cpp.replace('return QueueNative("Burst", [element]() {',
                                                                                'return [element]() {', 1), status_h, reactions)[0],
           'outside a queued task')
    expect('the death sink handles dead = true', check_contract(sources, cpp.replace('if (e.dead || e.dyingIsYou) {', 'if (e.dyingIsYou) {', 1),
                                                                   status_h, reactions)[0], 'handles only dead = false')
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('ESSBNative.Burst(aiIndex)', 'ESSBNative.Burst(0)', 1)
    expect('the burst without the closing element', check_contract(s, cpp, status_h, reactions)[0], 'ESSBNative.Burst(aiIndex)')
    s = dict(sources)
    s['ESSBElem.psc'] += '\nFunction Probe24(ESSBController akCtl, Actor akTarget) Global\n\takCtl.OnKillEvent(akTarget)\nEndFunction\n'
    expect('a call into the deleted kill hook', check_removed(s, b), 'still names OnKillEvent')
    s = dict(sources)
    s['ESSBNative.psc'] += '\nFunction Detonate(Actor akActor) Global Native\n'
    expect('a removed native declared again', check_removed(s, b), 'still declares Detonate')
    return caught


# ---------------------------------------------------------------- BEHAVIOUR (today's scripts, review fix 4)

def check_behaviour():
    """Functions this round changed that the older verifiers exercised on the round-23 scripts, run on today's."""
    import math
    import fix6_verify as v6
    settings = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))
    ctl = v6.Ctl(settings)
    reg = v6.make_scripts(SRC, ctl)
    c = reg['ESSBController']
    # Round 25 (N6): GetDamageMult and ReactDamage went with the Papyrus domains (死域's damage is the DLL's D_react);
    # they run on the scripts round 24 shipped (build/fix25_history.py ties them to today's).
    import fix25_history
    old = v6.make_scripts(fix25_history.legacy_source(), ctl)['ESSBController']
    checks = 0
    ctl.EnvNight = v6.Glob(0)
    assert math.isclose(old.GetDamageMult(1), 1.0), 'GetDamageMult: no Papyrus 嗜血 ×1.2 any more (the DLL reads it)'
    assert math.isclose(old.GetDamageMult(7), 1.2) and math.isclose(old.GetDamageMult(10), 1.0), 'day: divine ×1.2'
    ctl.EnvNight = v6.Glob(1)
    assert math.isclose(old.GetDamageMult(10), 1.2) and math.isclose(old.GetDamageMult(7), 1.0), 'night: darkness ×1.2'
    fire = settings['element_damage']['Fire'][1]
    assert c.BaseMax(1) == fire and c.BaseMax(0) == 0.0 and c.BaseMax(12) == 0.0, 'BaseMax'
    assert math.isclose(old.ReactDamage(10, 0.5), settings['element_damage']['Darkness'][1] * 0.5 * 1.2), 'ReactDamage at night'
    checks += 4
    ctl.UtilSpells = [v6.Spell()]
    ctl.UtilTargetSpells = []
    for value in (15, 70, 999):
        c.ApplyUtil(0, value, 3, v6.Actor())
        assert ctl.UtilSpells[0].mag == min(value, 70), 'ApplyUtil: the slow cap'
        checks += 1
    return checks


def run(b):
    sources = scripts()
    cpp = PLUGIN_CPP.read_text(encoding='utf-8')
    status_h = STATUS_H.read_text(encoding='utf-8')
    reactions = REACTIONS_H.read_text(encoding='utf-8')
    errors, counts = check_contract(sources, cpp, status_h, reactions)
    errors += check_removed(sources, b)
    record_errors, kinds, timed, by = check_records(b)
    resolve_errors, resolved = check_resolve(by)
    errors += record_errors + resolve_errors + v22.check_guards(cpp) + check_endings()
    assert not errors, '\n  '.join(['FIX24 failed:'] + errors)
    behaviour = check_behaviour()
    caught = self_test(sources, cpp, status_h, reactions, b)
    faults = check_faults()
    import fix24_history
    history = fix24_history.self_check()
    import fix24_native_history
    native_history = fix24_native_history.self_check()
    mutants, n5 = check_mutants()
    report = dict(behaviour=behaviour, contract=counts, kinds=kinds, timed_spells=timed, resolved=resolved, source_faults=caught, native_faults=faults,
                  history=history, native_history=native_history, native_mutants=[m['name'] for m in mutants])
    (ROOT / 'build/fix24-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX24 ok: {counts["natives"]} natives declared = registered; {counts["n5_events"]} round-24 ModEvents sent and '
          f'handled, {counts["body_only"]} body-only events never reach Papyrus, no ESSB_Death snapshot, the death sink '
          f'(dead = false, never you, DeathCounts, task) and the one-native burst in place; ESSBGuard / ESSBReactions and '
          f'every removed body, hook and native gone; {kinds} round-24 kinds and {timed} timed spells read back, 安全閥 '
          f'reads the DLL effect, 3 alias scripts, schema 13; {resolved} DLL FormIDs resolve; sinks / tasks / natives '
          f'guarded; {counts["queued_natives"]} scanning / casting natives queued on the main thread; {behaviour} behaviour '
          f'checks on today\'s scripts; line endings kept; {len(caught)}/{len(caught)} source faults and {len(faults)}/{len(faults)} '
          f'reaction-test faults caught; history: {history["changed"]} changed / {history["removed"]} removed / '
          f'{history["added"]} added functions and {history["files"]} whole scripts declared, '
          f'{len(history["silent_edits_caught"])} silent edits caught; native seal: {native_history["changed"]} changed / '
          f'{native_history["added"]} added / {native_history["unchanged"]} unchanged, '
          f'{len(native_history["silent_edits_caught"])} silent edits caught; {len(n5)} round-24 C++ mutants failed '
          f'({len(mutants)} in all)')
