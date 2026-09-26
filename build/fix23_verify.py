"""Round 23 (N4, your resources and the hits you take): offline checks of what this round changed, each with injected
faults.

  CONTRACT   the round-22 seam checks run on today's sources (every ESSBNative declaration registered with the same
             arity, every ModEvent the DLL sends registered to a handler that reads no more than is sent -- the six new
             N4 events and the ninth ESSB_Death value included); the player codes 40-58 ESSBNative.psc documents are
             ones ReadCode answers.
  REMOVED    ruling R6: ESSBGuard has no OnHitEx and registers no hit event (it unregisters the old one); no Papyrus
             self counter is left (SelfCharge, SelfRockArmor, SelfWind, Resolve, IceShield, the burst / switch charge,
             ExtremeCount, the trio / concert state, the counter-spell animation path); no script writes a mirror global
             the DLL owns (ESSB_Charge, ESSB_Resolve, ESSB_IceShield, ESSB_RockArmor, ESSB_Wind, ESSB_SyncStage, ESSB_Sync)
             outside the fresh-schema reset; no script calls a removed function.
  RECORDS    read back from the written ESP: every round-23 kind's MGEF / SPEL (counters: Script, No Magnitude, the record
             seconds; AV kinds: Peak Value Modifier on the right actor value); the mirror ESSB_Bracing; 聖佑's tier spells
             carry magic resist 10 / 20 / 35 (R7); ESSB_P_BaseRules carries the pool entries (法盾, 水幕, 護血 on both
             halves with the destructive-spell OR on the spell half), 聖佑's physical reduction and 冰盾's per-layer
             reduction; 殘影 / 破護 read the DLL's effects, not the Papyrus windows.
  RESOLVE    every spell / effect the DLL casts or reads (ManifestData.h spell:: / effect:: / the status records / the
             mirrors) exists in the ESP under the expected editor id.
  GUARDS     every event sink (the hurt, cast and menu sinks included) and every task behind SEH + C++ catch; every
             native through Guard.
  FAULTS     the native self test fails on a mutated table (a magnitude, a missing op, an extra board entry, a wrong
             duration, a wiring FormID).
  ENDINGS    every file this round touched keeps its pre-round line endings (CRLF or LF).
  MUTANTS    the C++ source mutations of native/build.py on SelfLayer.h / Hurt.h all failed (receipt), >= 5.
  HISTORY    build/fix23_history.py (Papyrus, digest-bound, silent edits caught) and build/fix23_native_history.py (DLL,
             tests, generator modules, sha256-bound, silent edits caught); the round-22 seals now read the pre-fix23
             snapshot only after these proofs.
"""
from pathlib import Path
import copy, json, re, struct, subprocess, sys, tempfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
SRC = ROOT / 'src'
SNAPSHOT = ROOT / '.codex/pre-fix23-snapshot'
PLUGIN_CPP = ROOT / 'native/src/Plugin.cpp'
STATUS_H = ROOT / 'native/include/Status.h'

import fix22_verify as v22

N4_EVENTS = ['ESSB_Discharge', 'ESSB_Blade', 'ESSB_Knock', 'ESSB_SyncUp', 'ESSB_Cleanse', 'ESSB_Lethal']
REMOVED_NAMES = ['SelfCharge', 'SelfRockArmor', 'SelfWind', 'ChargeDecayAt', 'SelfLastHit', 'BurstCharge', 'SwitchCharge',
                 'ExtremeCount', 'SwitchEndPending', 'PendingDischarge', 'ThunderLeft', 'WindFollowLeft', 'RockArmorShown',
                 'CachedSync', 'TakeAttacker', 'OnHitEx', 'RefreshNodeBits', 'ConsumeRockArmor', 'ConsumeIceShield',
                 'SyncRockArmor', 'OnEarthRetaliate', 'OnPoisonSkin', 'CheckWindGauge', 'StormChance', 'OverloadMult',
                 'TrioMult', 'ConcertMult', 'PushTrio', 'TakeSwitchEnd', 'TakeGrandConcert', 'EndCharge', 'ConsumeEndCharge',
                 'OpenSyncBonus', 'SyncThresholdScale', 'ComputeSyncStage', 'OnInterruptCast', 'OnCounterSpell',
                 'StartCounter', 'StopCounter', 'CounterEligible', 'RememberCast', 'RecentCast', 'AddOpenSelf', 'GuideSync',
                 'TakeInterrupt', 'TakeIceHeart', 'TakeRetaliate', 'TakeCleanse', 'SetRiposte', 'SetCloakGuard',
                 'SetGuardWind', 'SetThunder', 'SetWindFollow', 'SetPendingDischarge', 'HasExtreme', 'AfterOpen']
MIRRORS = ['GCharge', 'GResolve', 'GIceShield', 'GRockArmor', 'GWind', 'GSyncStage', 'Sync']


def code_only(text):
    return v22.code_only(text)


def scripts():
    return {p.name: p.read_text(encoding='utf-8-sig') for p in sorted(SRC.glob('*.psc'))}


# ---------------------------------------------------------------- CONTRACT

def check_contract(sources, cpp, status_h):
    # The events round 23 sends are built in SelfLayer.h / Hurt.h too (the round-22 check only scanned Status.h).
    headers = status_h + ''.join((ROOT / 'native/include' / h).read_text(encoding='utf-8') for h in ('SelfLayer.h', 'Hurt.h'))
    errors, counts = v22.check_contract(sources, cpp, headers)
    sent = v22.events_sent(cpp, headers)
    for name in N4_EVENTS:
        if name not in sent:
            errors.append(f'{name}: the DLL does not send it')
    if sent.get('ESSB_Death') != 9:
        errors.append(f'ESSB_Death carries {sent.get("ESSB_Death")} values, not 9 (the last-hit-sneak marker)')
    doc = re.search(r'Player\s+codes.*?FormEnter', sources['ESSBNative.psc'], re.S)
    if not doc:
        errors.append('ESSBNative.psc does not document the player codes 40-58')
        return errors, counts
    documented = {int(c) for c in re.findall(r'(?<![\d.])(\d{2}) ', doc[0]) if 40 <= int(c) <= 58}
    answered = {int(c) for c in re.findall(r'\bcase (\d+): return', cpp)}
    for c in sorted(set(range(40, 59)) - documented):
        errors.append(f'player code {c} is not documented in ESSBNative.psc')
    for c in sorted(documented - answered):
        errors.append(f'player code {c} is documented but ReadCode does not answer it')
    counts['player_codes'] = len(documented & answered)
    return errors, counts


# ---------------------------------------------------------------- REMOVED

def check_removed(sources):
    errors = []
    guard = code_only(sources['ESSBGuard.psc'])
    if re.search(r'\bEvent OnHitEx\b', guard) or 'RegisterForHitEventEx' in guard:
        errors.append('ESSBGuard still handles or registers the Papyrus hit event (R6)')
    if 'UnregisterForAllHitEventsEx' not in guard:
        errors.append('ESSBGuard does not unregister the old saves\' hit event')
    for script, text in sources.items():
        code = code_only(text)
        for name in REMOVED_NAMES:
            if re.search(r'\b' + name + r'\b', code):
                errors.append(f'{script}: still names {name}')
        # A mirror the DLL owns is written only by the fresh-schema reset (ReconcileLoadedForm).
        for fn in re.finditer(r'(?ms)^(?:\w+(?:\[\])?\s+)?(?:Function|Event) (\w+)\(.*?^End(?:Function|Event)', code):
            if fn[1] == 'ReconcileLoadedForm':
                continue
            for g in MIRRORS:
                if re.search(r'\b' + g + r'\.SetValue(?:Int)?\(', fn[0]) or re.search(r'SetGlobal\(\s*' + g + r'\s*,', fn[0]):
                    errors.append(f'{script}.{fn[1]} writes {g} (a mirror the DLL owns)')
    return errors


# ---------------------------------------------------------------- RECORDS / RESOLVE

def check_records(b):
    import fix23_records as rec
    import fix22_records as rec22
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
                errors.append(f'{suffix}: a counter must be Script with No Magnitude (archetype {archetype})')
        else:
            if archetype != 34 or struct.unpack_from('<i', effect.d['DATA'], 68)[0] != av:
                errors.append(f'{suffix}: AV kind must be a Peak Value Modifier on actor value {av}')
        if struct.unpack_from('<I', spell.d['EFIT'], 8)[0] != int(seconds):
            errors.append(f'{suffix}: spell lasts {struct.unpack_from("<I", spell.d["EFIT"], 8)[0]} s, not {int(seconds)}')
        if struct.unpack_from('<I', spell.d['SPIT'], 20)[0] != (0 if on_player else 1):
            errors.append(f'{suffix}: delivery must be {"self" if on_player else "contact"}')
    if 'ESSB_Bracing' not in by:
        errors.append('ESSB_Bracing mirror missing')
    magic = by.get('ESSB_N4_HolyMagicEffect')
    if not magic or struct.unpack_from('<i', magic.d['DATA'], 68)[0] != 44:
        errors.append('聖佑 magic resist effect missing or not MagicResist (44)')
    for tier in (1, 2, 3):
        spell = by[rec22.edid_spell(f'Holy{tier}')]
        efids = [struct.unpack('<I', v)[0] & 0xFFFFFF for tag, v in spell.ss if tag == 'EFID']
        values = [struct.unpack_from('<f', v)[0] for tag, v in spell.ss if tag == 'EFIT']
        pairs = dict(zip(efids, values))
        if abs(pairs.get(rec.holy_magic_effect_id(), -1) - rec.HOLY_MR[tier - 1]) > 1e-6:
            errors.append(f'聖佑 {tier}: magic resist {pairs.get(rec.holy_magic_effect_id())} not {rec.HOLY_MR[tier - 1]}')
    base = by['ESSB_P_BaseRules']
    ss = base.ss
    entries = sum(1 for tag, _ in ss if tag == 'PRKE')
    ctdas = [v for tag, v in ss if tag == 'CTDA']
    own = b.own

    def has_param(fid):
        return any(struct.unpack_from('<i', c, 12)[0] == fid for c in ctdas)
    for label, fid in (('法盾／超載', own(rec.effect_id('kOverload'))), ('護血', own(b.hit20.GUARD_EFFECT)),
                       ('聖佑 I', own(rec22.effect_id('kHoly1'))), ('聖佑 III', own(rec22.effect_id('kHoly3'))),
                       ('冰盾 mirror', own(b.mech(4))), ('magicka AV', 25)):
        if not has_param(fid):
            errors.append(f'ESSB_P_BaseRules has no condition on {label}')
    fire_kw = b.ref('Skyrim.esm', b.FID_KW_DAMAGE_FIRE)
    if not any(struct.unpack_from('<i', c, 12)[0] == fire_kw and c[0] & 1 for c in ctdas):
        errors.append('the pool spell half lacks the OR-ed destructive keyword condition')
    if entries < 3 * 2 + 3 + 8:
        errors.append(f'ESSB_P_BaseRules has only {entries} entries')
    for branch, fid, label in (('ESSB_P_wind_0_3_B1', own(rec.effect_id('kAfterimage')), '殘影'),
                               ('ESSB_P_noform_1_3_B1', own(rec.effect_id('kCloakGuard')), '破護')):
        r = by.get(branch)
        if not r or not any(struct.unpack_from('<i', v, 12)[0] == fid for tag, v in r.ss if tag == 'CTDA'):
            errors.append(f'{label}: the PERK entry does not read the DLL effect')
    return errors, len(rec.KINDS), by


def check_resolve(by):
    """Every FormID ManifestData.h names for a DLL cast or read (spell::, effect::, glob::, the status records) is in the ESP
    under the editor id the header comment gives."""
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    by_local = {}
    for edid, r in by.items():
        try:
            by_local[int(r.key.split('|')[1], 16)] = edid
        except (ValueError, IndexError):
            pass
    errors, count = [], 0
    for fid, edid in re.findall(r'inline constexpr std::uint32_t k\w+ = (0x[0-9a-fA-F]+);\s*//\s*(ESSB_\w+)', header):
        count += 1
        if by_local.get(int(fid, 16)) != edid:
            errors.append(f'{edid} ({fid}): the ESP holds {by_local.get(int(fid, 16))}')
    for effect, spell, _s, _p, _st, edid in re.findall(
            r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), ([\d.]+)f, (true|false), (true|false), "(ESSB_N[34]_\w+)"\}', header):
        count += 2
        if by_local.get(int(spell, 16)) != edid or by_local.get(int(effect, 16)) != edid + 'Effect':
            errors.append(f'status record {edid}: spell / effect ids do not match the ESP')
    return errors, count


# ---------------------------------------------------------------- FAULTS

def run_self_test(table, wiring):
    exe = ROOT / 'native/out/Release/self_test.exe'
    with tempfile.TemporaryDirectory() as tmp:
        t, w = Path(tmp) / 't.json', Path(tmp) / 'w.json'
        t.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')
        w.write_text(json.dumps(wiring, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([str(exe), str(t), str(w)], capture_output=True, text=True, encoding='utf-8', errors='replace').returncode


def check_faults():
    table = json.loads((ROOT / 'build/fix23-self-table.json').read_text(encoding='utf-8'))
    wiring = json.loads((ROOT / 'build/fix23-wiring.json').read_text(encoding='utf-8'))
    assert run_self_test(table, wiring) == 0, 'the unmutated tables must pass'
    faults = []

    def fault(label, mutate_table=None, mutate_wiring=None):
        t, w = copy.deepcopy(table), copy.deepcopy(wiring)
        if mutate_table:
            mutate_table(t)
        if mutate_wiring:
            mutate_wiring(w)
        assert run_self_test(t, w) != 0, f'injected fault not caught: {label}'
        faults.append(label)

    def scenario(t, prefix):
        return next(s for s in t['scenarios'] if s['name'].startswith(prefix))

    def spend_off(t):
        op = next(o for o in scenario(t, '法盾: 30%')['expect']['ops'] if o[0] == 'spendMagicka')
        op[1] *= 1.01
    fault('法盾 spends 1% more', spend_off)

    def drop_discharge(t):
        s = scenario(t, 'lightning: a full power hit')
        s['expect']['ops'] = [o for o in s['expect']['ops'] if o[:2] != ['event', 'Discharge']]
    fault('the full power discharge missing', drop_discharge)

    def extra_rock(t):
        scenario(t, 'earth open: 岩甲 +2')['expect']['me']['StoredForce'] = [3.0, 86400.0]
    fault('an extra resource on you', extra_rock)

    def ice_longer(t):
        scenario(t, '冰盾: a frost hit')['expect']['me']['IceShield'][1] += 1.0
    fault('冰盾 lasting 1 s longer', ice_longer)

    def punish_cap(t):
        scenario(t, '懲戒: 誓約 attacker')['expect']['me']['Punish'][0] = 9.0
    fault('懲戒 past 天誅\'s cap', punish_cap)

    def wiring_id(w):
        w['kinds'][2]['effect'] += 1
    fault('a wiring FormID off by one', mutate_wiring=wiring_id)

    def mirror_id(w):
        w['mirrors']['ESSB_Charge'] += 1
    fault('a mirror global off by one', mutate_wiring=mirror_id)
    return faults


# ---------------------------------------------------------------- ENDINGS / MUTANTS / GUARDS

TOUCHED = ['build_v03.py', 'plan_coverage.py', 'settings.json', 'native/CMakeLists.txt', 'native/build.py',
           'native/include/HitMath.h', 'native/include/Status.h', 'native/include/StatusEngine.h', 'native/src/Plugin.cpp',
           'native/tests/engine_test.cpp', 'native/tests/hit_pipeline_test.cpp', 'native/tests/status_test.cpp',
           'build/fix19_native.py', 'build/fix22_fixture.py', 'build/fix22_records.py']


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
    return errors


def check_mutants():
    receipt = json.loads((ROOT / 'native/out/build-receipt.json').read_text(encoding='utf-8'))
    mutants = receipt.get('mutants') or []
    assert all(m['exit'] != 0 for m in mutants), 'a native mutant survived'
    n4 = [m for m in mutants if m['header'] in ('SelfLayer.h', 'Hurt.h')]
    assert len(n4) >= 5, ('fewer than 5 round-23 C++ mutants', len(n4))
    return mutants, n4


def run(b):
    sources = scripts()
    cpp = PLUGIN_CPP.read_text(encoding='utf-8')
    status_h = STATUS_H.read_text(encoding='utf-8')
    errors, counts = check_contract(sources, cpp, status_h)
    errors += check_removed(sources)
    record_errors, kinds, by = check_records(b)
    resolve_errors, resolved = check_resolve(by)
    errors += record_errors + resolve_errors + v22.check_guards(cpp) + check_endings()
    assert not errors, '\n  '.join(['FIX23 failed:'] + errors)
    faults = check_faults()
    import fix23_history
    history = fix23_history.self_check()
    import fix23_native_history
    native_history = fix23_native_history.self_check()
    mutants, n4 = check_mutants()
    report = dict(contract=counts, kinds=kinds, resolved=resolved, native_faults=faults, history=history,
                  native_history=native_history, native_mutants=[m['name'] for m in mutants])
    (ROOT / 'build/fix23-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX23 ok: {counts["natives"]} natives declared = registered; {counts["events"]} ModEvents registered (6 new N4 + '
          f'ESSB_Death with 9 values); {counts["player_codes"]} player codes documented and answered; OnHitEx and the '
          f'Papyrus self counters gone, no Papyrus write to a DLL mirror; {kinds} round-23 kinds read back, 聖佑 magic '
          f'resist 10/20/35, pool / 聖佑 / 冰盾 PERK entries, 殘影 / 破護 read the DLL effects; {resolved} DLL FormIDs '
          f'resolve to the expected ESP records; sinks / tasks / natives guarded; line endings kept; '
          f'{len(faults)}/{len(faults)} self-test faults caught; history: {history["changed"]} changed / '
          f'{history["removed"]} removed / {history["added"]} added functions declared, '
          f'{len(history["silent_edits_caught"])} silent edits caught; native seal: {native_history["changed"]} changed / '
          f'{native_history["added"]} added / {native_history["unchanged"]} unchanged, '
          f'{len(native_history["silent_edits_caught"])} silent edits caught; {len(n4)} round-23 C++ mutants failed '
          f'({len(mutants)} in all)')
