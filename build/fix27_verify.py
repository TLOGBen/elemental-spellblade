"""Round 27 / 27b (DLL 0.27.1): offline checks of what this round changed, each with injected faults.

  VISUALS    build/fix27_visuals.check on the written ESP (G13, G14; 27b): the form ring -- four constant self effects per
             element with a Skyrim.esm ring art, one per ESSB_SyncStage 0..3 under ESSB_WeaponGlow (形態光圈), no shader or
             enchantment (the round-27 weapon glow retired and unused), the
             mark keeps its edge light and lost the art / sound, the open flashes carry art and sound, the status shadings,
             the four domain hazard models, No Absorb/Reflect (0x200000) on every DLL spell and Ignore Resistance (0x100000)
             on the one-effect markers; the Papyrus half (no IsDead skip in OnESSBEnd / OnESSBOpen, ESSB_Fx placed). One
             fault each on copies of the records / scripts must fail it.
  SOURCES    E2: every __except goes through SehFilter; E3: AddTask only in QueueTask (plus the notification and the
             main-thread witness, which touch no game state); E1: the OVERLAP-READ witness, the removal sink erases the
             registry row; G12: SKSEPlugin_Query goes through Runtime.h Query (the log cannot fail it) and OpenLog is
             noexcept; G8: the switch in SwitchWork (the burst on every close, also magicka empty -- the user's decision
             2026-09-27), OnFormOpened calls no FormEnter, KeepSync declared and registered; G15: a step key bound to a form
             is the hotkey only, CycleDebugLevel reaches 4. One fault each must fail.
  VERSION    0.27.1 in CMakeLists, ManifestData.h, fix19_native, the packaged manifest and build/probe-judge.py VERSION.
  JUDGE      SETUP-1 fails on [ESSB][OVERLAP-READ], on [ESSB][crash] and on an older version (the round-26 hand sample).
  MUTANTS    the receipt: every runtime / anchor mutant failed its test, and the contract's mutations are there (G1, G6,
             G7, E1, E3, the burst's overflow, G15).
  HISTORY    build/fix27_history.py (Papyrus) and build/fix27_native_history.py, each with its silent edits caught.
  ENDINGS    every file this round touched keeps its pre-round line endings and byte-order mark.
"""
from pathlib import Path
import dataclasses, importlib.util, json, re, struct, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SNAPSHOT = ROOT / '.codex/pre-fix27-snapshot'
SRC = ROOT / 'src'
VERSION = '0.27.1'

import fix27_visuals as vis


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fn_text(text, head):
    at = text.find(head)
    if at < 0:
        return None
    end = text.find('\n}\n', at)
    return text[at:end + 3] if end > 0 else None


# ---------------------------------------------------------------- VISUALS

def _replace(records, edid, key, change):
    """A copy of `records` with one subrecord of one record changed (change(bytes) -> bytes, or None to drop it)."""
    out = []
    done = False
    for r in records:
        if r.edid == edid and not done:
            ss = []
            for k, v in r.ss:
                if k == key and not done:
                    done = True
                    v = change(v)
                    if v is None:
                        continue
                ss.append((k, v))
            r = dataclasses.replace(r, ss=ss)
        out.append(r)
    assert done, (edid, key)
    return out


def _put(offset, value):
    def change(v):
        data = bytearray(v)
        struct.pack_into('<I', data, offset, value)
        return bytes(data)
    return change


def check_visuals(b, records, ctl):
    errors = vis.check(records, b) + vis.check_papyrus(ctl)
    if errors:
        return errors, []
    import fix27_records as hit27
    import fix22_records as hit22
    import fix25_records as hit25
    no_absorb, _ = hit27.dll_spell_flags(b)
    by_local = {int(r.key.split('|')[1], 16): r for r in records if r.key.startswith(b.PLUGIN.casefold())}
    some_dll_spell = by_local[sorted(no_absorb)[0]].edid
    freeze = hit22.edid_effect(next(s for k, s, *_ in hit22.KINDS if k == 'kFreeze'))

    def clear_flag(v):
        data = bytearray(v)
        struct.pack_into('<I', data, 4, struct.unpack_from('<I', data, 4)[0] & ~hit27.NO_ABSORB)
        return bytes(data)

    def old_ctda(v):   # the round-18 bug: a condition reading Skyrim.esm:005000 (no own())
        data = bytearray(v)
        struct.pack_into('<I', data, 12, 0x005000)
        return bytes(data)

    def stage_one(v):   # a ring's stage condition moved to another stage (two rings at once)
        data = bytearray(v)
        struct.pack_into('<f', data, 4, 1.0)
        return bytes(data)

    def retired_efid(v):   # the form ability back on a retired weapon-glow effect
        return struct.pack('<I', b.own(0x5280))

    def no_persist(v):
        data = bytearray(v)
        struct.pack_into('<I', data, 0, struct.unpack_from('<I', data, 0)[0] & ~0x1000)
        return bytes(data)

    faults = [
        ('a ring without its art', vis.check(_replace(records, 'ESSB_FormRingEffect_Fire_2', 'DATA', _put(96, 0)), b)),
        ('a ring touching the weapon (an enchant shader)', vis.check(_replace(records, 'ESSB_FormRingEffect_Frost_0', 'DATA', _put(36, 0x01005300)), b)),
        ('a ring as Enhance Weapon', vis.check(_replace(records, 'ESSB_FormRingEffect_Astral_3', 'DATA', _put(64, 39)), b)),
        ('a ring condition on Skyrim.esm:005000', vis.check(_replace(records, 'ESSB_FormAbility_Water', 'CTDA', old_ctda), b)),
        ('two rings on one stage', vis.check(_replace(records, 'ESSB_FormAbility_Earth', 'CTDA', stage_one), b)),
        ('the form ability on a retired glow effect', vis.check(_replace(records, 'ESSB_FormAbility_Blood', 'EFID', retired_efid), b)),
        ('the mark with the open art again', vis.check(_replace(records, 'ESSB_MarkEffect_Blood', 'DATA', _put(96, 0x01003000)), b)),
        ('the mark without its edge light', vis.check(_replace(records, 'ESSB_MarkEffect_Earth', 'DATA', _put(32, 0)), b)),
        ('an open flash without art', vis.check(_replace(records, 'ESSB_MarkFlashEffect_Wind', 'DATA', _put(96, 0)), b)),
        ('an open flash without sound', vis.check(_replace(records, 'ESSB_MarkFlashEffect_Poison', 'SNDD', lambda v: None), b)),
        ('凍結 without persist', vis.check(_replace(records, freeze, 'DATA', no_persist), b)),
        ('the fire domain invisible again', vis.check(_replace(records, hit25.hazard_edid(1), 'MODL', lambda v: hit25.HAZARD_MODEL.encode('ascii') + b'\0'), b)),
        ('a DLL spell reflectable', vis.check(_replace(records, some_dll_spell, 'SPIT', clear_flag), b)),
        ('OnESSBEnd skipping the dead again', vis.check_papyrus(re.sub(r'(?m)^(Event OnESSBEnd\(.*\n)', r'\1\tIf akTarget.IsDead()\n\tEndIf\n', ctl, 1))),
        ('ESSB_Fx not registered', vis.check_papyrus(ctl.replace('RegisterForModEvent("ESSB_Fx", "OnESSBFx")', '', 1))),
    ]
    missed = [label for label, errs in faults if not errs]
    return [f'visual fault not caught: {m}' for m in missed], [label for label, _ in faults]


# ---------------------------------------------------------------- SOURCES

def check_sources(cpp, sources, sinks_h):
    errors = []
    code = '\n'.join(line for line in cpp.splitlines() if not line.lstrip().startswith('//'))
    bare = [m.start() for m in re.finditer(r'__except\s*\((?!SehFilter\(GetExceptionInformation\(\), )', code)]
    if bare:
        errors.append(f'E2: {len(bare)} __except without SehFilter')
    tasks = [m.start() for m in re.finditer(r'->AddTask\(', code)]
    allowed = [fn_text(code, 'bool QueueTask(Fn fn, bool sessionOnly = false) noexcept'), fn_text(code, 'void Show(std::string text) noexcept')]
    witness = code.count('tasks->AddTask([]() { MainThreadGuarded(); });')
    inside = sum(1 for body in allowed if body and '->AddTask(' in body)
    if len(tasks) != inside + witness or inside != 2:
        errors.append(f'E3: {len(tasks)} AddTask calls, {inside + witness} allowed (QueueTask, Show, the main-thread witness)')
    if '[ESSB][OVERLAP-READ]' not in cpp:
        errors.append('E1: no OVERLAP-READ witness')
    if 'state.registry.EraseUid(' not in cpp:
        errors.append('E1: the removal sink does not erase the registry row')
    query = fn_text(cpp, 'extern "C" __declspec(dllexport) bool SKSEPlugin_Query(')
    if not query or 'essb::rt::Query(' not in query:
        errors.append('G12: SKSEPlugin_Query does not go through Runtime.h Query')
    if 'void OpenLog() noexcept' not in cpp:
        errors.append('G12: OpenLog can throw')
    switch = fn_text(cpp, '\nvoid SwitchWork(')
    if not switch or 'BurstWork(from);' not in switch:
        errors.append('G8: the close in SwitchWork does not burst')
    magicka = fn_text(cpp, 'void CloseByMagicka(RE::PlayerCharacter& player)\n{')
    if not magicka or 'SwitchWork(player, essb::SwitchKind::kClose, from, 0, 1);' not in magicka:
        errors.append('G5 (the user\'s decision): magicka empty does not close through the burst of SwitchWork')
    if 'vm->RegisterFunction("KeepSync", kClass, PapyrusKeepSync);' not in cpp or \
            'Function KeepSync(Int aiCount) Global Native' not in sources['ESSBNative.psc']:
        errors.append('G8: KeepSync not declared and registered')
    ctl = sources['ESSBController.psc']
    opened = re.search(r'(?ms)^Function OnFormOpened\(.*?^EndFunction', ctl)
    if not opened or re.search(r'(?m)^[^;\n]*ESSBNative\.FormEnter\(', opened[0]):
        errors.append('G8: OnFormOpened still calls FormEnter (the DLL task does)')
    if 'const bool hotkey = f.enabled && f.hotkeys && HotkeyElement(KeyCodeOf(p.device, p.id), true, f.keys) != 0;' not in sinks_h \
            or 'if (!hotkey && f.active && f.trace' not in sinks_h:
        errors.append('G15: a step key bound to a form is still a step')
    if '(DebugLevel.GetValueInt() + 1) % 5' not in sources['ESSBSettingsEffect.psc']:
        errors.append('G15: CycleDebugLevel does not reach 4')
    return errors


def source_faults(cpp, sources, sinks_h):
    caught = []

    def expect(label, errors):
        if not errors:
            raise AssertionError(('fix27 source fault not caught', label))
        caught.append(label)

    class Text(str):
        def replace(self, old, new, count=-1):   # every fault must really change the text
            assert old in self, ('fix27 fault text not found', old[:80])
            return str.replace(self, old, new, count)

    cpp, sinks_h = Text(cpp), Text(sinks_h)
    expect('a bare __except', check_sources(cpp.replace('} __except (SehFilter(GetExceptionInformation(), "access violation in the hit task")) {',
                                                        '} __except (EXCEPTION_EXECUTE_HANDLER) {', 1), sources, sinks_h))
    expect('an AddTask outside QueueTask', check_sources(cpp.replace('        if (!QueueTask([](bool live) { TickGuarded(live); })) {',
        '        if (!(SKSE::GetTaskInterface()->AddTask([]() { TickGuarded(true); }), true)) {', 1), sources, sinks_h))
    expect('no OVERLAP-READ', check_sources(cpp.replace('[ESSB][OVERLAP-READ]', '[ESSB][READ]'), sources, sinks_h))
    expect('Query opening the log itself', check_sources(cpp.replace('    return essb::rt::Query(\n', '    OpenLog();\n    return Query_(\n', 1),
                                                         sources, sinks_h))
    expect('magicka closing without the burst', check_sources(cpp.replace('SwitchWork(player, essb::SwitchKind::kClose, from, 0, 1);',
                                                                           'SwitchWork(player, essb::SwitchKind::kIgnore, from, 0, 1);', 1), sources, sinks_h))
    s = dict(sources)
    s['ESSBSettingsEffect.psc'] = Text(s['ESSBSettingsEffect.psc']).replace('% 5', '% 4', 1)
    expect('CycleDebugLevel stopping at 3', check_sources(cpp, s, sinks_h))
    expect('the step key over the hotkey', check_sources(cpp, sources, sinks_h.replace('if (!hotkey && f.active && f.trace', 'if (f.active && f.trace', 1)))
    return caught


# ---------------------------------------------------------------- VERSION / JUDGE / MUTANTS

def check_versions(b, j):
    errors = []
    cmake = (ROOT / 'native/CMakeLists.txt').read_text(encoding='utf-8')
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    import fix19_native as n
    if f'VERSION {VERSION}' not in cmake or f'nativeVersion[] = "{VERSION}"' not in header or n.NATIVE_VERSION != VERSION:
        errors.append(f'the DLL version is not {VERSION} in CMakeLists / ManifestData.h / fix19_native')
    manifest = json.loads((b.OUT / 'SKSE/Plugins/ElementsSpellblade/manifest.json').read_text(encoding='utf-8'))
    if manifest.get('native_version') != VERSION:
        errors.append(f'the packaged manifest is not {VERSION}')
    if j.VERSION != VERSION:
        errors.append(f'build/probe-judge.py judges {j.VERSION}, not {VERSION}')
    return errors


def check_judge(j):
    v26 = _module('fix26_verify_for27', ROOT / 'build/fix26_verify.py')
    good = v26.s_setup(False).text()
    errors, rows = [], []
    v, _ = v26.verdict_of(j, good, 'SETUP-1')
    if v.status != 'PASS':
        errors.append(f'SETUP-1 sample: {v.status} {v.reason}')
    for label, bad in (('an OVERLAP-READ', good + '[ESSB][OVERLAP-READ] ctx=TESDeathEvent thread=18188 (an effect list walked outside a task)\n'),
                       ('a crash passed on', good + '[ESSB][crash] hit task: exception 0xC0000005 at 0x7FF600001000 (SkyrimSE.exe) -- not this DLL\'s access violation; passed on to the game\n'),
                       ('an older DLL', good.replace(f'ElementsSpellblade {VERSION};', 'ElementsSpellblade 0.26.3;', 1))):
        assert bad != good, label
        fv, _ = v26.verdict_of(j, bad, 'SETUP-1')
        if fv.status != 'FAIL':
            errors.append(f'SETUP-1 with {label}: {fv.status} (should be FAIL)')
        rows.append(label)
    return errors, rows


def check_mutants():
    receipt = json.loads((ROOT / 'native/out/build-receipt.json').read_text(encoding='utf-8'))
    mutants = receipt.get('mutants') or []
    ours = [m for m in mutants if m['test'] in ('runtime', 'anchor')] + [m for m in mutants if m['name'].startswith('G15:')]
    errors = [f'mutant survived: {m["name"]}' for m in ours if m['exit'] in (0, None)]
    for tag in ('G1:', 'G6:', 'G7:', 'E1:', 'E3:', 'G15:', 'B-small: the burst', 'T:', 'A-N2:', 'B-N1:', 'B-N2:'):
        if not any(m['name'].startswith(tag) for m in ours):
            errors.append(f'no {tag} mutant in the receipt')
    return errors, ours


# ---------------------------------------------------------------- ENDINGS

TOUCHED = ['build_v03.py', 'native/CMakeLists.txt', 'native/build.py', 'native/src/Plugin.cpp', 'build/fix19_native.py',
           'build/probes-all.md', 'build/probe-judge.py', 'build/native-verification.md', '實作紀錄.md',
           'build/fix18_records.py', 'build/fix22_records.py', 'build/fix25_records.py', 'build/fix24_verify.py', 'build/fix25_verify.py',
           'build/fix26_verify.py', 'build/fix26_format.py'] + \
          [f'native/include/{h}' for h in ('Hurt.h', 'Reactions.h', 'SelfLayer.h', 'Sinks.h', 'Status.h', 'StatusEngine.h', 'Trace.h', 'TrueHud.h')]


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


def run(b):
    j = _module('probe_judge_for27', ROOT / 'build/probe-judge.py')
    cpp = (ROOT / 'native/src/Plugin.cpp').read_text(encoding='utf-8')
    sinks_h = (ROOT / 'native/include/Sinks.h').read_text(encoding='utf-8')
    sources = {p.name: p.read_text(encoding='utf-8-sig') for p in SRC.glob('*.psc')}
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    errors, visual_faults = check_visuals(b, records, sources['ESSBController.psc'])
    errors += check_sources(cpp, sources, sinks_h) + check_versions(b, j) + check_endings()
    judge_errors, judge_rows = check_judge(j)
    mutant_errors, mutants = check_mutants()
    errors += judge_errors + mutant_errors
    assert not errors, '\n  '.join(['FIX27 failed:'] + errors)
    caught = source_faults(cpp, sources, sinks_h)
    import fix27_history
    history = fix27_history.self_check()
    import fix27_native_history
    native_history = fix27_native_history.self_check()
    report = dict(visual_faults=visual_faults, source_faults=caught, judge=judge_rows, mutants=[m['name'] for m in mutants],
                  history=history, native_history=native_history, inventory=[list(row) for row in vis.INVENTORY])
    (ROOT / 'build/fix27-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX27 ok: visuals on the written ESP (the form ring: 4 vanilla-art effects per element, one per SyncStage, gated by 形態光圈, nothing on the weapon; '
          f'mark edge light without art, open flashes, {len(__import__("fix22_records").STATUS_SHADERS)} status shadings, '
          f'{len(__import__("fix25_records").HAZARD_MODELS)} domain models, SPIT 0x200000 on the DLL spells and every spell delivered to others, 0x100000 on the markers, Papyrus end / open / ESSB_Fx); '
          f'{len(visual_faults)}/{len(visual_faults)} visual faults caught; sources E1 E2 E3 G5 G8 G12 G15 with {len(caught)}/{len(caught)} faults caught; '
          f'{VERSION} everywhere; SETUP-1 fails on {", ".join(judge_rows)}; {len(mutants)} round-27 mutants failed; '
          f'history: {history["changed"]} changed / {history["added"]} added functions, {len(history["silent_edits_caught"])} silent edits caught; '
          f'native seal {native_history.get("changed", "?")} changed / {native_history.get("added", "?")} added, '
          f'{len(native_history["silent_edits_caught"])} silent edits caught; line endings kept')
