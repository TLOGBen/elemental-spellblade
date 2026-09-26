"""Round 22 (N3, the status layer): offline checks of what this round changed, each with injected faults.

  CONTRACT   the DLL <-> Papyrus seam: every ESSBNative declaration is registered by the DLL with the same number of
             arguments and every registered native is declared; every ModEvent the DLL sends (kEventNames and
             ESSB_Death) is registered in ESSBController.Setup to an Event with the ModEvent signature, and each
             handler reads no more values than the DLL puts in strArg; every status code the natives document is
             one ReadCode answers.
  REMOVED    the status container, the registry, the swap, the pending state and the difference patch are gone from
             every script (ruling R4); no ESSBStatus / ESSBMark sources; no script calls a removed controller function.
  RECORDS    read back from the written ESP: every status kind's MGEF / SPEL (flags: No Magnitude so effectiveness
             sets the duration; the stub script exactly on the kinds that settle, the marks, fear and frenzy); the
             retired container effect carries no script; 聖佑's tier spells carry the weapon (AttackDamageMult) and
             armour effects; the DoT spells last 1..45 s; 冰甲's chill has the two exclusive gauge effects; 狂刃.
  WASH       the R5 predicate in Plugin.cpp's Executor::Wash names every condition the ruling lists.
  GUARDS     every event sink and every task the DLL posts runs behind an SEH frame and a C++ catch; every native
             body goes through Guard (C++ catch + SehInvoke).
  FAULTS     the native status test fails on a mutated table (a magnitude, a missing op, an extra board entry, a
             wiring FormID, a wrong duration) -- the test can see what it claims to check.
  ENDINGS    every script keeps its pre-round line endings (CRLF or LF).
  UI         commander ruling: with the master switch off the MCM actions (status button, tree menu, respec, restore
             defaults) still run -- executed on the real ESSBController / ESSBState / ESSBMCM through the Papyrus
             harness; the tree menu, the settings power and the controller's UI entry points gate on IsReadyUI.
  REVIEW     the review fixes: the master switch gates every status path (Plugin.cpp Enabled(), Papyrus IsOperational);
             no miasma cloak record; the 幻影 PERK entry (attacker has 幻影, GetRandomPercent < 30) and 御風's entry
             without the sync gate in the ESP; the C++ mutation tests of native/build.py all failed (receipt); the
             native / generator seal build/fix22_native_history.py holds.
  HISTORY    build/fix22_history.py: today's scripts differ from the pre-fix22 snapshot only by the declared
             changes (digest-bound), and silent edits inside declared / untouched functions are caught.
"""
from pathlib import Path
import copy, json, re, struct, subprocess, sys, tempfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SRC = ROOT / 'src'
SNAPSHOT = ROOT / '.codex/pre-fix22-snapshot'
PLUGIN_CPP = ROOT / 'native/src/Plugin.cpp'
STATUS_H = ROOT / 'native/include/Status.h'
ENGINE_H = ROOT / 'native/include/StatusEngine.h'


def code_only(text):
    """Papyrus without comments and {...} doc blocks (a ';' inside a string is kept)."""
    import fix21_identity
    text = fix21_identity.strip_docs(text.replace('\r\n', '\n'))
    out = []
    for line in text.splitlines():
        masked = re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: '"' + ' ' * (len(m[0]) - 2) + '"', line)
        cut = masked.find(';')
        out.append(line if cut < 0 else line[:cut])
    return '\n'.join(out)


def scripts():
    return {p.name: p.read_text(encoding='utf-8-sig') for p in sorted(SRC.glob('*.psc'))}


# ---------------------------------------------------------------- CONTRACT

def natives_declared(sources):
    out = {}
    for m in re.finditer(r'(?m)^\s*(?:\w+(?:\[\])?\s+)?Function\s+(\w+)\(([^)]*)\)\s+Global\s+Native\b', code_only(sources['ESSBNative.psc'])):
        args = [a for a in m[2].split(',') if a.strip()]
        out[m[1]] = len(args)
    return out


def natives_registered(cpp):
    out = {}
    for name, fn in re.findall(r'vm->RegisterFunction\("(\w+)", kClass, (\w+)\)', cpp):
        sig = re.search(r'\n[^\n]*\b' + fn + r'\(RE::StaticFunctionTag\*([^)]*)\)', cpp)
        assert sig, fn
        args = [a for a in sig[1].split(',') if a.strip()]
        out[name] = len(args)
    return out


def events_sent(cpp, status_h):
    names = re.search(r'kEventNames\[\] = \{([^}]*)\}', cpp)[1]
    sent = re.findall(r'"(ESSB_\w+)"', names)
    enum = re.search(r'enum class Event : std::uint8_t\s*\{(.*?)\n\};', status_h, re.S)[1]
    kinds = [m for m in re.findall(r'^\s*(k\w+),', enum, re.M) if m != 'kCount']
    assert len(kinds) == len(sent), (kinds, sent)
    # Round 24 (N5): the events the DLL's own body pass consumes (Reactions.h BodyOnly) never reach Papyrus (SendEvent
    # refuses them); every other one is still a contract. The bodies' own ModEvents are built in Reactions.h.
    reactions = ROOT / 'native/include/Reactions.h'
    body_only = set()
    if reactions.is_file():
        rtext = reactions.read_text(encoding='utf-8')
        status_h += rtext
        fn = re.search(r'constexpr bool BodyOnly\(Event e\) noexcept\s*\{(.*?)\n\}', rtext, re.S)
        body_only = set(re.findall(r'Event::(k\w+)', fn[1])) if fn else set()
    # the values each event carries: the MakeEvent calls of Status.h / Plugin.cpp (max argument count per kind)
    count = {}
    for m in re.finditer(r'MakeEvent\(\s*(?:essb::)?Event::(k\w+)((?:,[^;]*?)?)\)\s*\)?;', status_h + cpp):
        args = m[2].count(',')
        count[m[1]] = max(count.get(m[1], 0), args)
    values = {sent[i]: count.get(k, 0) for i, k in enumerate(kinds) if k not in body_only}
    death = re.search(r'std::array<float, (\d+)> value', cpp)
    if death:   # round 24: the death snapshot event is gone (the death sink runs the death handling in the DLL)
        values['ESSB_Death'] = int(death[1])
    return values


def check_contract(sources, cpp, status_h):
    errors = []
    declared, registered = natives_declared(sources), natives_registered(cpp)
    for name in sorted(set(declared) | set(registered)):
        if name not in registered:
            errors.append(f'ESSBNative.{name} is declared but the DLL does not register it')
        elif name not in declared:
            errors.append(f'the DLL registers ESSBNative.{name} but ESSBNative.psc does not declare it')
        elif declared[name] != registered[name]:
            errors.append(f'ESSBNative.{name}: {declared[name]} Papyrus arguments, {registered[name]} in the DLL')
    ctl = code_only(sources['ESSBController.psc'])
    setup = re.search(r'(?ms)^Function Setup\(\).*?^EndFunction', ctl)[0]
    handlers = dict(re.findall(r'RegisterForModEvent\("(ESSB_\w+)", "(\w+)"\)', setup))
    for event, values in events_sent(cpp, status_h).items():
        handler = handlers.get(event)
        if not handler:
            errors.append(f'{event} is sent by the DLL but not registered in ESSBController.Setup')
            continue
        body = re.search(r'(?ms)^Event ' + handler + r'\((String \w+, String \w+, Float \w+, Form \w+)\)(.*?)^EndEvent', ctl)
        if not body:
            errors.append(f'{event}: no Event {handler}(String, String, Float, Form) in ESSBController')
            continue
        read = [int(i) for i in re.findall(r'EventArg\(\s*args\s*,\s*(\d+)\s*\)', body[2])]
        if read and max(read) >= values:
            errors.append(f'{event}: {handler} reads value {max(read)} but the DLL sends {values}')
    doc = re.search(r'Status codes.*?End reasons', sources['ESSBNative.psc'], re.S)[0]
    doc = '\n'.join(line for line in doc.splitlines() if 'AddStatus only' not in line)   # 25: an add-only code
    documented = {int(c) for c in re.findall(r'(?<![\d.])(\d{1,2}) ', doc) if 1 <= int(c) <= 29}
    answered = {int(c) for c in re.findall(r'\bcase (\d+): return', cpp)}
    for c in sorted(documented - answered):
        errors.append(f'status code {c} is documented in ESSBNative.psc but ReadCode does not answer it')
    return errors, dict(natives=len(registered), events=len(handlers), codes=len(answered))


# ---------------------------------------------------------------- REMOVED

REMOVED_NAMES = ['ESSBStatus', 'ESSBMark', 'RegStatus', 'RegActor', 'RegElem', 'RegMark', 'FindSlot', 'AcquireSlot',
                 'EnsureStatus', 'SwapHosts', 'CancelSwap', 'PendingStacks', 'BackupInts', 'FlushPendingState',
                 'ApplyProc', 'ApplyBonusProc', 'DifferenceMult', 'DifferencePossible', 'NativeProcUnit', 'NativeNodeSum',
                 'HitBonusSpells', 'StatusHostSpell', 'MarkSpells', 'OnStatusStart', 'OnMarkStart', 'TakePendingBleed',
                 'SetNextOpenMult', 'SetWetLock', 'CaptureDeath', 'StackCap', 'HitStacks', 'SetMolten', 'SelfOverheat']


def check_removed(sources):
    errors = []
    for name in ('ESSBStatus.psc', 'ESSBMark.psc'):
        if name in sources:
            errors.append(f'{name} still exists')
    for script, text in sources.items():
        code = code_only(text)
        for name in REMOVED_NAMES:
            if re.search(r'\b' + name + r'\b', code):
                errors.append(f'{script}: still names {name}')
    return errors


# ---------------------------------------------------------------- RECORDS

def check_records(b):
    import fix22_records as rec
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    by = {r.edid: r for r in records}
    errors = []

    def flags(r):
        return struct.unpack_from('<I', r.d['DATA'])[0]

    def vmad_script(r):
        return r.d['VMAD'][8:8 + struct.unpack_from('<H', r.d['VMAD'], 6)[0]].decode('utf-8') if 'VMAD' in r.d else None

    for kind, suffix, label, on_player, seconds, stub, _text in rec.KINDS:
        effect, spell = by.get(rec.edid_effect(suffix)), by.get(rec.edid_spell(suffix))
        if not effect or not spell:
            errors.append(f'{suffix}: record missing')
            continue
        if not flags(effect) & 0x400:
            errors.append(f'{suffix}: MGEF without No Magnitude (effectiveness would scale the magnitude, not the time)')
        if flags(effect) & 0x200:
            errors.append(f'{suffix}: MGEF has No Duration')
        if (vmad_script(effect) == rec.STUB_SCRIPT) != stub:
            errors.append(f'{suffix}: stub script {"missing" if stub else "present"}')
        efit = spell.d['EFIT']
        if struct.unpack_from('<I', efit, 8)[0] != int(seconds):
            errors.append(f'{suffix}: spell lasts {struct.unpack_from("<I", efit, 8)[0]} s, not {int(seconds)}')
    for name in ['ESSB_MarkEffect_' + n for n in b.ELEMENTS] + ['ESSB_FearEffect', 'ESSB_FrenzyEffect']:
        if vmad_script(by[name]) != rec.STUB_SCRIPT:
            errors.append(f'{name}: no stub script (its end must reach the DLL)')
    if 'VMAD' in by['ESSB_StatusHostEffect'].d:
        errors.append('the retired status container still carries a script')
    weapon, armor = by['ESSB_N3_HolyWeaponEffect'], by['ESSB_N3_HolyArmorEffect']
    if struct.unpack_from('<i', weapon.d['DATA'], 68)[0] != 154 or struct.unpack_from('<i', armor.d['DATA'], 68)[0] != 39:
        errors.append('聖佑: the weapon effect must be AttackDamageMult (154), the armour DamageResist (39)')
    for tier, (w, a) in enumerate(zip(rec.HOLY_WEAPON, rec.HOLY_ARMOR), 1):
        spell = by[rec.edid_spell(f'Holy{tier}')]
        values = [struct.unpack_from('<f', v)[0] for tag, v in spell.ss if tag == 'EFIT']
        if abs(values[1] - w) > 1e-6 or (a > 0 and abs(values[2] - a) > 1e-6):
            errors.append(f'聖佑 {tier}: tier spell carries {values}')
    for key, suffix, *_ in rec.DOT_KINDS:
        for s in range(1, rec.DOT_MAX_SECONDS + 1):
            spell = by[rec.dot_edid(suffix, s)]
            if struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != s:
                errors.append(f'{suffix} {s}: wrong duration')
    for chill, gauge_pct in (('ESSB_IceArmorChill', rec.ICE_CHILL_GAUGE_PCT), ('ESSB_IceArmorChillWide', rec.ICE_CHILL_GAUGE_WIDE_PCT)):
        spell = by[chill]
        efids = [struct.unpack('<I', v)[0] & 0xFFFFFF for tag, v in spell.ss if tag == 'EFID']
        ctdas = [v for tag, v in spell.ss if tag == 'CTDA']
        gauge = rec.effect_id('kFreeze')
        if len(efids) != 2 or len(ctdas) != 2 or efids[1] != rec.ice_chill_gauge_effect_id():
            errors.append(f'{chill}: needs the plain and the gauge chill effect')
        elif not all(struct.unpack_from('<I', c, 12)[0] & 0xFFFFFF == gauge for c in ctdas):
            errors.append(f'{chill}: the conditions must read the DLL freeze effect')
        elif struct.unpack_from('<f', [v for tag, v in spell.ss if tag == 'EFIT'][1])[0] != gauge_pct:
            errors.append(f'{chill}: gauge slow is not {gauge_pct}%')
    blade = by['ESSB_N3_FrenzyBladeEffect']
    if struct.unpack_from('<i', blade.d['DATA'], 68)[0] != 154:
        errors.append('狂刃: not AttackDamageMult')
    vision, vision_spell = by.get('ESSB_N3_VisionEffect'), by.get('ESSB_N3_Vision')
    if not vision or struct.unpack_from('<i', vision.d['DATA'], 68)[0] != 154 or not flags(vision) & 0x4:
        errors.append('幻視: the effect must be a detrimental AttackDamageMult (154) modifier')
    elif struct.unpack('<fII', vision_spell.d['EFIT'])[:3:2] != (struct.unpack('<f', struct.pack('<f', 0.2))[0], 3):
        errors.append('幻視: the spell must be -0.2 attack damage multiplier for 3 s (v0.4 line 1380)')
    if any('Miasma' in name for name in by):
        errors.append('a 瘴氣 cloak record is still written (ruling (b)+(d): the DLL gives the doses per second)')
    # 幻影 (ruling (c)): one PERK entry, incoming damage x0 with the attacker tab reading the DLL's 幻影 effect and
    # GetRandomPercent < 30; 御風: the entry reading the unbalance effect carries no sync-stage condition.
    phantom, unbalance = b.own(rec.effect_id('kPhantom')), b.own(rec.effect_id('kUnbalance'))
    sync = b.own(b.mech(0))
    found_phantom = found_wind = 0
    for r in records:
        if r.sig != 'PERK':
            continue
        entry, tab = None, None
        for tag, v in r.ss + [('PRKE', b'\xff\xff\xff')]:
            if tag == 'PRKE':
                if entry and entry['ep'] == 0x24 and (1, 214, phantom) in entry['c'] and (1, 77, 30.0, 0x80) in entry['r']:
                    found_phantom += 1 if entry['v'] == 0.0 else 0
                if entry and entry['ep'] == 0x23 and (2, 214, unbalance) in entry['c']:
                    found_wind += 1
                    if (0, 74, sync) in entry['c'] or (2, 74, sync) in entry['c']:
                        errors.append('御風: the unbalance entry still needs sync stage 3 (v0.4 5.7: only the slow immunity does)')
                entry, tab = dict(ep=None, c=set(), r=set(), v=None), None
            elif tag == 'DATA' and entry is not None and entry['ep'] is None and len(v) == 3:
                entry['ep'] = v[0]
            elif tag == 'PRKC' and entry is not None:
                tab = v[0]
            elif tag == 'CTDA' and entry is not None:
                op, value, func, param = v[0], struct.unpack_from('<f', v, 4)[0], struct.unpack_from('<H', v, 8)[0], struct.unpack_from('<I', v, 12)[0]
                entry['c'].add((tab, func, param))
                entry['r'].add((tab, func, round(value, 3), op))
            elif tag == 'EPFD' and entry is not None and len(v) == 4:
                entry['v'] = struct.unpack('<f', v)[0]
    if found_phantom != 1:
        errors.append(f'幻影: {found_phantom} PERK entries of incoming damage x0 on (attacker has 幻影, GetRandomPercent < 30), not 1')
    if found_wind != 1:
        errors.append(f'御風: {found_wind} weapon-damage entries on the unbalance effect, not 1')
    return errors, len(rec.KINDS)


# ---------------------------------------------------------------- WASH / GUARDS

# Ruling R5 lives in StatusEngine.h Washes (tested on fake effects by native/tests/engine_test.cpp); Plugin.cpp's ViewOf
# supplies the facts, and static_asserts there pin the spell-type / casting-source numbers to CommonLib's enums.
WASH_TERMS = ['kSpellTypeSpell', 'kSpellTypeScroll', 'kSpellTypeStaff', 'kSourceLeft', 'kSourceRight',
              'v.duration > 0.0f', 'v.elapsed < v.duration', '!v.hostile', '!v.detrimental', '!v.ours', '!v.company',
              'v.hasSpell']
VIEW_TERMS = ['base.IsHostile()', 'base.IsDetrimental()', 'state.forms.file', 'AR::kSummonCreature', 'AR::kBoundWeapon',
              'AR::kReanimate', 'AR::kCommandSummoned', 'effect.castingSource', 'GetSpellType()',
              'essb::engine::kSpellTypeScroll == static_cast<int>(RE::MagicSystem::SpellType::kScroll)',
              'essb::engine::kSpellTypeStaff == static_cast<int>(RE::MagicSystem::SpellType::kStaffEnchantment)',
              'essb::engine::kSourceRight == static_cast<int>(RE::MagicSystem::CastingSource::kRightHand)']


def check_wash(cpp, engine_h=None):
    engine_h = ENGINE_H.read_text(encoding='utf-8') if engine_h is None else engine_h
    body = re.search(r'constexpr bool Washes\(const EffectView& v\) noexcept\s*\{(.*?)\n\}', engine_h, re.S)
    view = re.search(r'EffectView ViewOf\(RE::ActiveEffect& effect, RE::EffectSetting& base\)\s*\{(.*?)\n\}', cpp, re.S)
    if not body or not view:
        return ['StatusEngine.h Washes or Plugin.cpp ViewOf not found']
    return ([f'Wash: the R5 predicate lacks {term}' for term in WASH_TERMS if term not in body[1]] +
            [f'Wash: ViewOf / the enum pins lack {term}' for term in VIEW_TERMS if term not in view[1] and term not in cpp])


def check_guards(cpp):
    errors = []
    for m in re.finditer(r'BSEventNotifyControl ProcessEvent\((.*?)\n    \}', cpp, re.S):
        if '__try' not in m[0] or '__except' not in m[0]:
            errors.append('an event sink without an SEH frame')
    for fn in re.findall(r'AddTask\(\[[^\]]*\]\(\) \{ (\w+)\(', cpp):
        body = re.search(r'\n\w[^\n]*\b' + fn + r'\([^)]*\) noexcept\s*\{(.*?)\n\}', cpp, re.S)
        if not body or '__try' not in body[1]:
            errors.append(f'task {fn} runs without an SEH frame')
        inner = re.search(r'__try \{\s*(\w+)\(', body[1]) if body else None
        cpp_body = re.search(r'\n\w[^\n]*\b' + inner[1] + r'\([^)]*\) noexcept\s*\{(.*?)\n\}', cpp, re.S) if inner else None
        if not cpp_body or 'catch (...)' not in cpp_body[1]:
            errors.append(f'task {fn}: its body has no C++ catch')
    for name, fn in re.findall(r'vm->RegisterFunction\("(\w+)", kClass, (\w+)\)', cpp):
        body = re.search(r'\n[^\n]*\b' + fn + r'\(RE::StaticFunctionTag\*[^)]*\)\s*\{(.*?)\n\}', cpp, re.S)
        if not body or not re.search(r'\b(Guard\(|IsActiveGuarded\(|SetWantedGuarded\(|return essb::nativeVersion)', body[1]):
            errors.append(f'ESSBNative.{name} runs outside Guard')
    guard = re.search(r'auto Guard\(.*?\n\}', cpp, re.S)
    if not guard or 'SehInvoke(' not in guard[0] or 'catch (...)' not in guard[0]:
        errors.append('Guard lacks the SEH frame or the C++ catch')
    return errors


# ---------------------------------------------------------------- REVIEW: the master switch

SWITCH_SITES = ['void SettleCpp', 'void OnRemoveCpp', 'void OnDeathCpp', 'void TickCpp', 'auto Guard(']


def check_switch(cpp, sources):
    errors = []
    if not re.search(r'bool Enabled\(\) noexcept\s*\{[^}]*state\.forms\.enabled->value == 1\.0f', cpp):
        errors.append('Plugin.cpp Enabled() does not read ESSB_Enabled')
    for site in SWITCH_SITES:
        at = cpp.find(site)
        body = cpp[at:at + 900] if at >= 0 else ''
        if 'Enabled()' not in body:
            errors.append(f'{site}: no master switch (Enabled()) at its start')
    op = re.search(r'Bool Function IsOperational\(\)(.*?)EndFunction', code_only(sources['ESSBController.psc']), re.S)
    if not op or 'Enabled.GetValueInt() == 1' not in op[1]:
        errors.append('ESSBController.IsOperational does not require the master switch')
    return errors


# ---------------------------------------------------------------- UI: MCM actions with the master switch off

UI_FUNCTIONS = {'ESSBController.psc': ['CloseForm', 'DumpStatus', 'OnMenuClose', 'RefreshRuntimeValues', 'RefreshTrees',
                                       'RefreshAbilities', 'RefreshRecovery', 'IsReadyUI'],
                'ESSBTrees.psc': ['OpenTree', 'BeginSettings', 'FinishSettings', 'Respec', 'RespecAll', 'RespecTree'],
                'ESSBSettingsEffect.psc': None, 'ESSBMCM.psc': None}


def check_vision(sources):
    body = re.search(r'(?ms)^Event OnESSBHallucinate\(.*?^EndEvent', code_only(sources['ESSBController.psc']))
    if not body or 'VisionSpell' not in body[0] or re.search(r'ApplyUtil\(\s*17', body[0]):
        return ['幻視: OnESSBHallucinate must cast VisionSpell (x0.8), not the flat MeleeDamage util 17']
    return []


def check_ui(sources, mcm_text=None):
    """Runs the MCM actions with ESSB_Enabled = 0; returns errors (empty = they all reached their targets)."""
    from types import SimpleNamespace as NS
    from papyrus_harness import Script
    import tempfile
    errors = []

    class Glob:
        def __init__(self, v):
            self.v = v

        def GetValueInt(self):
            return int(self.v)

        def GetValue(self):
            return float(self.v)

    ctl_vm = Script(SRC / 'ESSBController.psc', dict())
    ctl_vm.overrides.update(IsCurrentController=lambda: True)
    ctl_vm.fields.update(Ready=True, StateBroken=False, Enabled=Glob(0))
    if ctl_vm.IsOperational() or not ctl_vm.IsReadyUI():
        errors.append('switch off: IsOperational must be False and IsReadyUI True')
    ctl_vm.fields['Enabled'] = Glob(1)
    if not (ctl_vm.IsOperational() and ctl_vm.IsReadyUI()):
        errors.append('switch on: IsOperational and IsReadyUI must both be True')
    ctl_vm.fields['Enabled'] = Glob(0)

    events = []
    target = NS(IsReadyUI=ctl_vm.IsReadyUI, IsOperational=ctl_vm.IsOperational,
                RefreshRuntimeValues=lambda: events.append('refresh'), RefreshTrees=lambda: None,
                RefreshAbilities=lambda: None, RefreshRecovery=lambda: None,
                CloseForm=lambda: events.append('close'), DumpStatus=lambda: events.append('dump'),
                CurrentTree=lambda: 0, TreeName=lambda i: 'fire', RespecReady=lambda i: True,
                Respec=lambda i: events.append('respec'), RespecAll=lambda: events.append('respec-all'))
    quest = NS(GetAlias=lambda i: target)
    state = Script(SRC / 'ESSBState.psc', dict(Game=NS(GetFormFromFile=lambda fid, plugin: None)))
    state.overrides.update(ControllerQuest=lambda: quest, RestoreTunableDefaults=lambda: events.append('defaults'))
    if state.Operational() or not state.ReadyUI():
        errors.append('ESSBState: Operational must be False and ReadyUI True with the switch off')
    path = SRC / 'ESSBMCM.psc'
    if mcm_text is not None:
        tmp = Path(tempfile.mkdtemp()) / 'ESSBMCM.psc'
        tmp.write_text(mcm_text, encoding='utf-8')
        path = tmp
    mcm = Script(path, dict(ESSBState=state, ShowMessage=lambda *a: True, ForcePageReset=lambda: None,
                            Debug=NS(Notification=lambda s: None),
                            Game=NS(GetPlayer=lambda: NS(IsInCombat=lambda: False, EndDeferredKill=lambda: None))))
    mcm.fields['Controller'] = quest
    for action, want in (('DumpRegistry', ['dump']), ('RestoreDefaults', ['defaults', 'refresh']),
                         ('RespecCurrent', ['close', 'respec']), ('RespecAll', ['respec-all'])):
        events.clear()
        getattr(mcm, action)()
        if events[:len(want)] != want:
            errors.append(f'MCM {action} with the switch off did {events}, not {want}')
    for script, names in UI_FUNCTIONS.items():
        code = code_only(sources[script])
        bodies = [code] if names is None else [m[0] for n in names for m in
                                               [re.search(r'(?ms)^(?:\w+\s+)?(?:Function|Event) ' + n + r'\(.*?^End(?:Function|Event)', code)] if m]
        for body in bodies:
            if re.search(r'\bIsOperational\(|ESSBState\.Operational\(', body):
                errors.append(f'{script}: a UI path still gates on the master switch (IsOperational)')
                break
    return errors


def check_mutants():
    receipt = json.loads((ROOT / 'native/out/build-receipt.json').read_text(encoding='utf-8'))
    mutants = receipt.get('mutants') or []
    by = {h: sum(1 for m in mutants if m['header'] == h and m['exit'] != 0) for h in ('Status.h', 'StatusEngine.h')}
    assert all(m['exit'] != 0 for m in mutants), 'a native mutant survived'
    assert by['Status.h'] >= 3 and by['StatusEngine.h'] >= 3, ('too few native mutants', by)
    return mutants


# ---------------------------------------------------------------- FAULTS

def run_status_test(table, wiring):
    exe = ROOT / 'native/out/Release/status_test.exe'
    with tempfile.TemporaryDirectory() as tmp:
        t, w = Path(tmp) / 't.json', Path(tmp) / 'w.json'
        t.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')
        w.write_text(json.dumps(wiring, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([str(exe), str(t), str(w)], capture_output=True, text=True, encoding='utf-8', errors='replace').returncode


def check_faults():
    table = json.loads((ROOT / 'build/fix22-status-table.json').read_text(encoding='utf-8'))
    wiring = json.loads((ROOT / 'build/fix22-wiring.json').read_text(encoding='utf-8'))
    assert run_status_test(table, wiring) == 0, 'the unmutated tables must pass'

    def first(pred):
        return next(s for s in table['scenarios'] if pred(s))

    faults = []

    def fault(label, mutate_table=None, mutate_wiring=None):
        t, w = copy.deepcopy(table), copy.deepcopy(wiring)
        if mutate_table:
            mutate_table(t)
        if mutate_wiring:
            mutate_wiring(w)
        assert run_status_test(t, w) != 0, f'injected fault not caught: {label}'
        faults.append(label)

    def damage_plus_one_percent(t):
        s = next(s for s in t['scenarios'] if any(o[0] == 'damage' for o in s['expect']['ops']))
        op = next(o for o in s['expect']['ops'] if o[0] == 'damage')
        op[2] *= 1.01
    fault('a damage 1% off', damage_plus_one_percent)

    def drop_event(t):
        s = next(s for s in t['scenarios'] if any(o[0] == 'event' for o in s['expect']['ops']))
        s['expect']['ops'] = [o for o in s['expect']['ops'] if o[0] != 'event'][:len(s['expect']['ops']) - 1]
    fault('an expected ModEvent missing', drop_event)

    def extra_status(t):
        t['scenarios'][0]['expect']['target']['Fissure'] = [1.0, 8.0]
    fault('an extra status on the board', extra_status)

    def wrong_duration(t):
        s = next(s for s in t['scenarios'] if 'Bleed' in s['expect']['target'])
        s['expect']['target']['Bleed'][1] += 1.0
    fault('a status lasting 1 s longer', wrong_duration)

    def wrong_heat(t):
        s = next(s for s in t['scenarios'] if s['name'].startswith('fire refresh: 微熱 matured'))
        s['expect']['me']['Heat1'] = s['expect']['me'].pop('Heat2')
    fault('the ladder on the wrong tier', wrong_heat)

    def wiring_id(w):
        w['kinds'][3]['spell'] += 1
    fault('a wiring FormID off by one', mutate_wiring=wiring_id)

    def wiring_stub(w):
        w['kinds'][1]['stub'] = not w['kinds'][1]['stub']
    fault('a stub flag flipped', mutate_wiring=wiring_stub)
    return faults


# ---------------------------------------------------------------- ENDINGS

def check_endings():
    errors = []
    for p in sorted(SRC.glob('*.psc')):
        before = SNAPSHOT / 'src' / p.name
        if not before.exists():
            continue
        was, now = before.read_bytes(), p.read_bytes()
        was_crlf, now_crlf = was.count(b'\r\n') == was.count(b'\n'), now.count(b'\r\n') == now.count(b'\n')
        now_lf = b'\r\n' not in now
        if was_crlf and not now_crlf:
            errors.append(f'{p.name}: was CRLF, now {"LF" if now_lf else "mixed"}')
        elif not was_crlf and not now_lf:
            errors.append(f'{p.name}: was LF, now has CRLF')
    return errors


# ---------------------------------------------------------------- self test of the source checks

def self_test(sources, cpp, status_h):
    caught = []

    def expect(label, errors, needle):
        assert any(needle in e for e in errors), (label, 'fault not caught', errors[:3])
        caught.append(label)

    s = dict(sources)
    s['ESSBNative.psc'] += '\nFunction Ghost(Actor akActor) Global Native\n'
    expect('a native nobody registers', check_contract(s, cpp, status_h)[0], 'does not register it')
    s = dict(sources)
    # round 24: the Shatter / Rise / Detonate anchors went with the Papyrus bodies; the same faults on natives and events left
    s['ESSBNative.psc'] = s['ESSBNative.psc'].replace('Function ApplyMark(Actor akActor, Int aiElement) Global Native',
                                                        'Function ApplyMark(Actor akActor, Int aiElement, Int aiExtra) Global Native')
    expect('a native with a different argument count', check_contract(s, cpp, status_h)[0], 'Papyrus arguments')
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('RegisterForModEvent("ESSB_Knock", "OnESSBKnock")', '')
    expect('a ModEvent nobody listens to', check_contract(s, cpp, status_h)[0], 'ESSB_Knock is sent')
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('EventArg(args, 4) > 0.5', 'EventArg(args, 9) > 0.5', 1)
    expect('a handler reading past the values sent', check_contract(s, cpp, status_h)[0], 'reads value 9')
    s = dict(sources)
    s['ESSBElem.psc'] += '\nFunction Probe22(ESSBController akCtl, Actor akTarget) Global\n\takCtl.ApplyProc(akTarget, 1, False, False, False)\nEndFunction\n'
    expect('a call into the deleted difference patch', check_removed(s), 'still names ApplyProc')
    expect('an event sink without SEH', check_guards(cpp.replace('__try {\n            OnDeathCpp(*ev);', '{\n            OnDeathCpp(*ev);', 1)),
           'without an SEH frame')
    expect('a native outside Guard', check_guards(re.sub(r'(void PapyrusApplyMark\(RE::StaticFunctionTag\*, RE::Actor\* actor, std::int32_t element\)\s*\{)\s*Guard\("ApplyMark", ',
                                                         r'\1 NoGuard("ApplyMark", ', cpp)), 'outside Guard')
    expect('a wash without the hostile test', check_wash(cpp, ENGINE_H.read_text(encoding='utf-8').replace('!v.hostile', 'true')),
           '!v.hostile')
    expect('a status task without the master switch', check_switch(cpp.replace('if (!Enabled()) {   // master switch (review fix 3)',
                                                                              'if (!Active()) {', 1), sources), 'master switch')
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('&& Enabled.GetValueInt() == 1\r\nEndFunction', '\r\nEndFunction')
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('&& Enabled.GetValueInt() == 1\nEndFunction', '\nEndFunction')
    expect('IsOperational without the master switch', check_switch(cpp, s), 'IsOperational')
    expect('an MCM action behind the master switch', check_ui(sources, sources['ESSBMCM.psc'].replace(
        'ESSBState.ReadyUI()', 'ESSBState.Operational()')), 'with the switch off')
    s = dict(sources)
    s['ESSBTrees.psc'] = s['ESSBTrees.psc'].replace('Controller.IsReadyUI()', 'Controller.IsOperational()', 1)
    expect('the tree menu behind the master switch', check_ui(s), 'ESSBTrees.psc')
    return caught


def run(b):
    sources = scripts()
    cpp = PLUGIN_CPP.read_text(encoding='utf-8')
    status_h = STATUS_H.read_text(encoding='utf-8')
    errors, counts = check_contract(sources, cpp, status_h)
    errors += check_removed(sources)
    record_errors, kinds = check_records(b)
    errors += record_errors + check_wash(cpp) + check_guards(cpp) + check_endings() + check_switch(cpp, sources) + check_ui(sources) + check_vision(sources)
    assert not errors, '\n  '.join(['FIX22 failed:'] + errors)
    caught = self_test(sources, cpp, status_h)
    faults = check_faults()
    import fix22_history
    history = fix22_history.self_check()
    import fix22_native_history
    native_history = fix22_native_history.self_check()
    mutants = check_mutants()
    report = dict(contract=counts, status_kinds=kinds, source_faults=caught, native_faults=faults, history=history,
                  native_history=native_history, native_mutants=[m['name'] for m in mutants])
    (ROOT / 'build/fix22-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX22 ok: {counts["natives"]} natives declared = registered (same arity); {counts["events"]} ModEvents sent = '
          f'registered, handlers read within what is sent; {counts["codes"]} status codes answered; status container, '
          f'registry and difference patch gone; {kinds} status kinds read back (No Magnitude, stub exactly where the end '
          f'settles); R5 wash predicate complete; every sink / task / native guarded (SEH + C++); line endings kept; '
          f'{len(caught)}/{len(caught)} source faults and {len(faults)}/{len(faults)} native-test faults caught; history: '
          f'{history["changed"]} changed / {history["removed"]} removed / {history["added"]} added functions declared, '
          f'{len(history["silent_edits_caught"])} silent edits caught; native seal: {native_history["changed"]} changed / '
          f'{native_history["added"]} added / {native_history["unchanged"]} unchanged files, '
          f'{len(native_history["silent_edits_caught"])} silent edits caught; {len(mutants)}/{len(mutants)} C++ mutants failed '
          f'the native tests; master switch on every status path; MCM actions run with the switch off')
    return report
