"""Round 27h / 28 (DLL 0.28.0): offline checks of what the whole-project review and the Papyrus-layer review changed, each
rule with an injected fault that must fail it.

  SWITCH     1-4: OnESSBSwitch waits on nothing (no ticket, no Utility.Wait) and swaps no ability; SwitchWork adds / removes
             the form abilities and keeps the burst's sync (Runtime.h OnBurstKeep / OnOpenKeep).
  READY      Papyrus review 2: Setup aligns the form abilities and writes ESSB_PapyrusReady at its end; RequestSwitch holds a
             switch until it reads 1; the DLL writes 0 at kPreLoadGame / kNewGame.
  TREES      Papyrus review 1 / 3 / 4: RefreshTree walks no node; no Papyrus Reconcile / TakeSnapshot; OnCustomSkillIncrease
             adds with GlobalVariable.Mod; the StatsMenu close is the DLL's (ReconcileBranchesWork).
  OPERATIONAL Papyrus review 10: IsOperational needs ESSB_NativeHit == 1.
  CASTS      Papyrus review 7: no SetNthEffectMagnitude / SetNthEffectDuration outside the reanimate (its own lock).
  SCANS      Papyrus review 6 / review 1-5 / 1-6: PoisonFormTick scans nothing; the hit sink reads no inventory; the domains
             are the recorded ones (no cell walk, no walk of every actor).
  FAULTS     1-2: every C++ catch of ours is a session fault; RunningSeconds never faults; a load clears a session fault.
  HAZARDS    Papyrus review 5: every hazard effect is conditioned (not you, not a teammate, hostile).
  BUDGET     the native calls a handler makes, bounded offline (build/papyrus_budget.py): OnCustomSkillIncrease <= 50 and the
             others in BUDGETS; the 0.27.6 RefreshTree body must break it.

Round 28b (DLL 0.28.1):
  READY      F2: ClearPapyrusReady() in each of the three places by location -- the kPreLoadGame case, the kNewGame case
             before its OnGameReady(), the kPostLoadGame success branch before its OnGameReady() (the saved global).
  GAMEREADY  F3 / F5 / F7: GameReadyCpp clears the domain ledger, 印潮's arming and 水臨強化's cooldown.
  FAULTCLOSE F4: FaultCloseCpp dispels the 護血 pool and the pending echo (the old Papyrus CloseForm did).
  CASTWITH   F1: no magnitude-bearing MGEF reaches an effectiveness-based duration: CastWithWork casts Runtime.h
             PlanCastWith's call; the executor's Cast refuses an effectiveness on a spell with a magnitude; every Papyrus
             CastWith site resolves to spells that are No Magnitude, cast with 0 seconds, or a family of whole-second
             copies (build/fix28_records.py CASTWITH) whose copies are their base with only the duration changed and which
             the DLL table (ManifestData.h status::kCastWith) lists.
  SURGE      F5: 印潮 fires on the first hit after a switch that opened its mark (not on a cut); only a switch arms it.
  ADVENT     F7: FormEnterWork gives PlanAdvent 水臨強化's cooldown, starts it when it fired, logs the cooling at L4.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import papyrus_budget as pb  # noqa: E402

SRC = ROOT / 'src'
BUDGETS = {
    ('ESSBTrees', 'OnCustomSkillIncrease'): 50,
    ('ESSBTrees', 'RefreshTree'): 10,
    ('ESSBTrees', 'OnMenuClose'): 10,
    ('ESSBController', 'OnESSBOpen'): 40,
    ('ESSBController', 'OnESSBEnd'): 40,
    ('ESSBElem3', 'PoisonFormTick'): 40,
}
# SetNthEffect* left in place (review 7 named the casts): the reanimate (its own ReanimateBusy lock around the record) and
# the abilities (their magnitude is written before AddSpell -- an ability is added, not cast; the refresh runs one at a time).
CASTS_ALLOWED = ('ReanimateSpell', 'WarmBloodAbility', 'InductionAbility', 'WindSpeedAbility')
# The 0.27.6 RefreshTree (the per-node cache rebuild) -- a fault that must break the budget.
OLD_REFRESH = '''Function RefreshTree(Int aiTree)
	Actor player = ThePlayer()
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		CacheRank[pos] = GetMainRank(aiTree, route, tier)
		Int n = 0
		While n < BRANCH_SLOTS
			Perk branch = GetBranch(aiTree, route, tier, n)
			If branch && player.HasPerk(branch)
				n += 0
			EndIf
			n += 1
		EndWhile
		pos += 1
	EndWhile
	LevelCache[aiTree] = TreeLevel(aiTree)
EndFunction
'''


def fn(text, name):
    m = re.search(r'(?ms)^[ \t]*(?:\w+(?:\[\])?[ \t]+)?(?:Function|Event)[ \t]+' + re.escape(name) + r'\s*\(.*?^[ \t]*End(?:Function|Event)\b', text)
    return m.group(0) if m else ''


def cpp_fn(cpp, head):
    i = cpp.find(head)
    if i < 0:
        return ''
    j = cpp.find('\n}\n', i)
    return cpp[i:j + 2] if j > 0 else cpp[i:]


def code_only(text):
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith((';', '//')))


def case_block(message, label):
    """The text of `case SKSE::MessagingInterface::<label>:` up to its break."""
    i = message.find(f'case SKSE::MessagingInterface::{label}:')
    if i < 0:
        return ''
    j = message.find('break;', i)
    return message[i:j] if j > 0 else ''


def check_ready_sites(message):
    """Round 28b (F2): the three resets of ESSB_PapyrusReady by location (was: a count of two)."""
    errors = []
    pre = code_only(case_block(message, 'kPreLoadGame'))
    new = code_only(case_block(message, 'kNewGame'))
    post = code_only(case_block(message, 'kPostLoadGame'))
    success = post[post.find('if (message->data != nullptr) {'):post.find('} else {')] if 'if (message->data != nullptr) {' in post else ''
    if 'ClearPapyrusReady();' not in pre or 'ClearSessionFault();' not in pre:
        errors.append('READY / FAULTS: kPreLoadGame does not reset ESSB_PapyrusReady and the session fault')
    if not (0 <= new.find('ClearPapyrusReady();') < new.find('OnGameReady();')) or 'ClearSessionFault();' not in new:
        errors.append('READY / FAULTS: kNewGame does not reset ESSB_PapyrusReady (before OnGameReady) and the session fault')
    if not (0 <= success.find('ClearPapyrusReady();') < success.find('OnGameReady();')):
        errors.append('READY: the kPostLoadGame success branch does not clear ESSB_PapyrusReady before OnGameReady '
                      '(the save restores the 1 kPreLoadGame cleared)')
    return errors


def check_28b(cpp):
    """Round 28b: F3, F4, F5, F7 wiring in Plugin.cpp and CastWithWork / Cast (F1)."""
    errors = []
    ready = code_only(cpp_fn(cpp, 'void GameReadyCpp() noexcept'))
    for text, what in (('state.domains.Clear();', 'F3: the domain ledger'), ('state.surgeArmed = false;', 'F5: 印潮\'s arming'),
                       ('state.waterAdvent = essb::AdventCooldown{};', 'F7: 水臨強化\'s cooldown')):
        if text not in ready:
            errors.append(f'GAMEREADY: GameReadyCpp does not reset {what}')
    close = code_only(cpp_fn(cpp, 'void FaultCloseCpp() noexcept'))
    if 'DispelLive(' not in close or '&base == f.bloodGuard' not in close or '&base == f.echoPending' not in close:
        errors.append('FAULTCLOSE: a fault\'s close leaves the 護血 pool / the pending echo')
    work = code_only(cpp_fn(cpp, 'void CastWithWork('))
    if 'essb::rt::PlanCastWith(facts)' not in work or re.search(r'seconds\s*/\s*(?:facts\.)?record', work) \
            or 'CastSpellImmediate(cast, false, on, call.effectiveness, false, call.magnitude, player);' not in work \
            or work.count('CastSpellImmediate(') != 1:
        errors.append('CASTWITH: CastWithWork does not cast Runtime.h PlanCastWith\'s call (seconds as an effectiveness again)')
    if 'facts.noMagnitude = AllNoMagnitude(*spell);' not in work:
        errors.append('CASTWITH: CastWithWork does not tell the planner whether the spell has a magnitude')
    if not re.search(r'if \(effectiveness != 1\.0f && !AllNoMagnitude\(\*item\)\) \{\s*(?:\n\s*)*LogOnce\([^;]*\);\s*effectiveness = 1\.0f;',
                     code_only(cpp_fn(cpp, '    void Cast(essb::Who who, std::uint32_t spell, float magnitude, float effectiveness)'))):
        errors.append('CASTWITH: the executor\'s Cast lets an effectiveness reach a spell with a magnitude')
    handle = code_only(cpp_fn(cpp, 'void Handle(const HitSeen& seen, RE::PlayerCharacter& playerRef, RE::Actor& targetRef, bool corpse)'))
    if 'const bool firstAfterSwitch = std::exchange(state.surgeArmed, false);' not in handle \
            or 'const bool surge = firstAfterSwitch && status.opened && nodes.Has(essb::node::kCommonSurge);' not in handle \
            or 'essb::PlanSurge(statusPlan, cw, selfBoard, bin, markElement, nodes, Rng());' not in handle:
        errors.append('SURGE: 印潮 is not the first hit after a switch that opened its mark')
    switch = code_only(cpp_fn(cpp, '\nvoid SwitchWork('))
    if 'state.surgeArmed = kind == essb::SwitchKind::kSwitch && essb::IsElement(from);' not in switch \
            or switch.count('state.surgeArmed = false;') != 1:
        errors.append('SURGE: SwitchWork does not arm 印潮 on a switch only (a close disarms it)')
    enter = code_only(cpp_fn(cpp, '\nvoid FormEnterWork(int element)\n{'))
    if 'bin.waterAdventReady = state.waterAdvent.Ready(now);' not in enter or 'state.waterAdvent.Fired(now);' not in enter \
            or '[ESSB][advent][L4] water-plus cooldown left=' not in enter or 'const std::uint64_t now = state.runningMs.load();' not in enter:
        errors.append('ADVENT: FormEnterWork does not run 水臨強化\'s 10 s running-clock cooldown (and its L4 line)')
    return errors


# Round 28b (F1): every Papyrus ESSBNative.CastWith site, by (function, spell argument): what the spell can be.
#   list      those EDIDs;  'util'  UtilSpells[i] for every ApplyUtil call with a literal duration > 0;
#   'zero'    the site passes a literal 0.0 seconds;  'windows'  the nine guard windows (ESSBState.GuardWindowSpell);
#   'markers' ApplySelfMarker's callers (none today: a caller must be listed here first).
CASTWITH_SITES = {
    ('ApplyUtil', 'utilSpell'): 'util',
    ('ApplySelfMarker', 'akMarker'): 'markers',
    ('ApplyFear', 'FearSpell'): ['ESSB_FearSpell'],
    ('ApplyFrenzy', 'FrenzySpell'): ['ESSB_FrenzySpell'],
    ('ApplyFrenzy', 'FrenzyBladeSpell'): ['ESSB_N3_FrenzyBlade'],
    ('ApplyAsh', 'AshSpell'): 'zero',
    ('ApplyGuardWindow', 'window'): 'windows',
}
GUARD_WINDOW_FIRST, GUARD_WINDOWS = 0x005171, 9   # ESSBState.GuardWindowSpell: 0x005171 + 2 i


def castwith_calls(sources):
    """(script, function, spell argument, seconds argument) of every ESSBNative.CastWith call."""
    out = []
    for name, text in sources.items():
        if name == 'ESSBNative.psc':
            continue
        current = None
        for line in code_only(text).splitlines():
            m = re.match(r'^\s*(?:\w+(?:\[\])?\s+)?(?:Function|Event)\s+(\w+)', line)
            if m:
                current = m.group(1)
            call = re.search(r'ESSBNative\.CastWith\(\s*([^,]+),\s*([^,]+),\s*(.+),\s*([^,()]+(?:\([^()]*\))?[^,()]*)\)', line)
            if call:
                out.append((name, current, call.group(1).strip(), call.group(4).strip()))
    return out


def check_castwith(b, records, sources, header):
    """Round 28b (F1): the ESP half of 'no magnitude-bearing MGEF reaches an effectiveness-based duration'."""
    import fix28_records as hit28
    errors = []
    by_edid = {r.edid: r for r in records}
    by_id = {int(r.key.split('|')[1], 16) & 0xFFFFFF: r for r in records if r.key.split('|')[0].casefold() == b.PLUGIN.casefold()}
    effect_flags = {}
    for r in records:
        if r.sig == 'MGEF' and 'DATA' in r.d:
            effect_flags[int(r.key.split('|')[1], 16) & 0xFFFFFF] = struct.unpack_from('<I', r.d['DATA'])[0]

    def efids(spell):
        return [struct.unpack('<I', v)[0] & 0xFFFFFF for k, v in spell.ss if k == 'EFID']

    def magnitude_bearing(spell):
        return any(not effect_flags.get(e, 0) & 0x400 for e in efids(spell))

    families = {hit28.castwith_base_id(b, name): name for name, *_ in hit28.CASTWITH}
    table = {int(base, 16): int(first, 16) for base, first in
             re.findall(r'\{(0x[0-9a-f]+), (0x[0-9a-f]+)\},  // \w+: ESSB_N7_CastWith', header)}
    for base, name in families.items():
        spell = by_id.get(base)
        if not spell or spell.sig != 'SPEL':
            errors.append(f'CASTWITH: family {name}: no base spell {base:06X}')
            continue
        if not magnitude_bearing(spell):
            errors.append(f'CASTWITH: family {name}: {spell.edid} has no magnitude (a No Magnitude spell needs no copies)')
        if table.get(base) != hit28.castwith_id(name, 1):
            errors.append(f'CASTWITH: family {name}: the DLL table (ManifestData.h status::kCastWith) does not list it')
        for seconds in range(1, hit28.CASTWITH_MAX_SECONDS + 1):
            copy = by_edid.get(hit28.castwith_edid(name, seconds))
            if not copy or int(copy.key.split('|')[1], 16) & 0xFFFFFF != hit28.castwith_id(name, seconds):
                errors.append(f'CASTWITH: {hit28.castwith_edid(name, seconds)} missing')
                continue
            want = [(k, v) for k, v in spell.ss if k != 'EDID']
            got = [(k, v) for k, v in copy.ss if k != 'EDID']
            efit = copy.d.get('EFIT', b'')
            base_efit = spell.d.get('EFIT', b'')
            if len(efit) != 12 or struct.unpack('<fII', efit)[2] != seconds or efit[:8] != base_efit[:8]:
                errors.append(f'CASTWITH: {copy.edid} does not last {seconds} s with its base\'s magnitude')
            if [(k, v) for k, v in want if k != 'EFIT'] != [(k, v) for k, v in got if k != 'EFIT']:
                errors.append(f'CASTWITH: {copy.edid} differs from {spell.edid} beyond its duration')
    if len(table) != len(families):
        errors.append('CASTWITH: the DLL table lists a family the records do not')
    # the Papyrus sites
    ctl = sources.get('ESSBController.psc', '')
    for script, function, arg, seconds in castwith_calls(sources):
        spec = CASTWITH_SITES.get((function, arg))
        if spec is None:
            errors.append(f'CASTWITH: {script} {function}: ESSBNative.CastWith({arg}, ...) is not listed in CASTWITH_SITES')
            continue
        if spec == 'zero':
            if not re.fullmatch(r'0(?:\.0*)?', seconds):
                errors.append(f'CASTWITH: {function} must cast {arg} with 0 seconds (it has a magnitude)')
            continue
        if spec == 'markers':
            callers = [m for m in re.finditer(r'\bApplySelfMarker\(', code_only(ctl)) if not code_only(ctl)[max(0, m.start() - 9):m.start()].endswith('Function ')]
            if callers:
                errors.append('CASTWITH: ApplySelfMarker has callers: list the markers they pass in CASTWITH_SITES')
            continue
        if spec == 'util':
            spells = set()
            for text in sources.values():
                for idx, dur in re.findall(r'\bApplyUtil\(\s*(\d+)\s*,[^,\n]*,\s*(\d+)\s*[,)]', code_only(text)):
                    if int(dur) > 0:
                        spells.add(b.util_spell_id(int(idx)))
                        if int(idx) in (4, 6, 27):
                            errors.append(f'CASTWITH: ApplyUtil({idx}, ..., {dur}) may cast UtilTargetSpells with seconds (no copies)')
            spells = [by_id.get(i) for i in sorted(spells)]
        elif spec == 'windows':
            spells = [by_id.get(GUARD_WINDOW_FIRST + 2 * i) for i in range(GUARD_WINDOWS)]
        else:
            spells = [by_edid.get(e) for e in spec]
        for spell in spells:
            if spell is None or spell.sig != 'SPEL':
                errors.append(f'CASTWITH: {function}: a spell of the site is missing from the ESP')
                continue
            base = int(spell.key.split('|')[1], 16) & 0xFFFFFF
            if magnitude_bearing(spell) and (base not in families or base not in table):
                errors.append(f'CASTWITH: {function} casts {spell.edid} (an effect with a magnitude) for its seconds without '
                              f'whole-second copies (the effectiveness would scale its magnitude)')
    return errors


def castwith_faults(b, records, sources, header):
    import fix28_records as hit28
    caught = []

    class R:
        def __init__(self, r, ss):
            self.sig, self.key, self.ss = r.sig, r.key, ss

        @property
        def d(self):
            return dict(self.ss)

        @property
        def edid(self):
            return self.d.get('EDID', b'').rstrip(b'\0').decode('utf-8', 'replace')

    def expect(label, recs=records, srcs=sources, head=header):
        if not check_castwith(b, recs, srcs, head):
            raise AssertionError(('fix28 CastWith fault not caught', label))
        caught.append(label)

    victim = hit28.castwith_edid('Fear', 4)
    bad = []
    for r in records:
        if r.edid == victim:
            bad.append(R(r, [(k, struct.pack('<fII', 10.0, 0, 2) if k == 'EFIT' else v) for k, v in r.ss]))
        else:
            bad.append(r)
    expect('a copy lasting its base\'s record time', recs=bad)
    first = hit28.castwith_id('FrenzyBlade', 1)
    expect('a family missing from the DLL table', head=header.replace(f'{hex(first)}}},  // FrenzyBlade', '0x0},  // FrenzyBlade'))
    s = dict(sources)
    s['ESSBElem.psc'] = s['ESSBElem.psc'].replace('akCtl.ApplyUtil(13, rank as Float, 6, akTarget)',
                                                  'akCtl.ApplyUtil(13, rank as Float, 6, akTarget)\n\takCtl.ApplyUtil(10, 5.0, 4, akTarget)', 1)
    assert s['ESSBElem.psc'] != sources['ESSBElem.psc']
    expect('an ApplyUtil with seconds on a magnitude spell without copies', srcs=s)
    s = dict(sources)
    s['ESSBController.psc'] = s['ESSBController.psc'].replace('ESSBNative.CastWith(AshSpell, akTarget, akTarget.GetActorValueMax("Health") + 100.0, 0.0)',
                                                              'ESSBNative.CastWith(AshSpell, akTarget, akTarget.GetActorValueMax("Health") + 100.0, 3.0)', 1)
    assert s['ESSBController.psc'] != sources['ESSBController.psc']
    expect('化灰 cast for seconds', srcs=s)
    return caught


def check_sources(cpp, sources):
    errors = []
    ctl, trees = sources['ESSBController.psc'], sources['ESSBTrees.psc']
    switch = code_only(fn(ctl, 'OnESSBSwitch'))
    if not switch or 'Utility.Wait' in switch or '0x005DC0' in switch or '.Mod(' in switch:
        errors.append('SWITCH: OnESSBSwitch still waits on the ticket')
    for name in ('OnESSBSwitch', 'FormOpenedFx', 'FormClosedFx'):
        if re.search(r'AddSpell\(FormAbilities|RemoveSpell\(FormAbilities', code_only(fn(ctl, name))):
            errors.append(f'SWITCH: {name} swaps a form ability (the switch task does)')
    work = cpp_fn(cpp, '\nvoid SwitchWork(')
    if 'SetFormAbility(player, to);' not in work or 'SetFormAbility(player, 0);' not in work or 'essb::rt::OnBurstKeep(' not in work \
            or 'essb::rt::OnOpenKeep(' not in work:
        errors.append('SWITCH: SwitchWork does not swap the abilities / keep the burst sync')
    setup = code_only(fn(ctl, 'Setup'))
    if 'papyrusReady.SetValue(1.0)' not in setup or setup.find('papyrusReady.SetValue(1.0)') < setup.find('RegisterForModEvent("ESSB_Switch"') \
            or 'RemoveSpell(FormAbilities[ability])' not in setup:
        errors.append('READY: Setup does not align the abilities and publish ESSB_PapyrusReady at its end')
    request = cpp_fn(cpp, '\nvoid RequestSwitch(int element, const char* via)\n{')
    if 'if (!PapyrusReady()) {' not in request or 'state.pendingSwitch = element;' not in request:
        errors.append('READY: RequestSwitch does not hold a switch until Papyrus is ready')
    message = cpp_fn(cpp, 'void MessageCpp(SKSE::MessagingInterface::Message* message) noexcept')
    errors += check_ready_sites(message)
    errors += check_28b(cpp)
    refresh = code_only(fn(trees, 'RefreshTree'))
    if 'While' in refresh or 'HasPerk' in refresh or 'GetMainRank' in refresh:
        errors.append('TREES: RefreshTree walks the nodes again')
    for gone in ('Reconcile', 'ReconcileGained', 'TakeSnapshot', 'SettleBranch'):
        if fn(trees, gone):
            errors.append(f'TREES: ESSBTrees.{gone} is back (the reconcile is the DLL\'s)')
    increase = code_only(fn(trees, 'OnCustomSkillIncrease'))
    if 'points.Mod(1.0)' not in increase or 'SetValueInt(' in increase:
        errors.append('TREES: OnCustomSkillIncrease writes the points read-modify-write')
    if 'QueueTask([](bool live) { ReconcileGuarded(live); });' not in cpp:
        errors.append('TREES: the StatsMenu close does not queue the DLL reconcile')
    operational = code_only(fn(ctl, 'IsOperational'))
    if 'NativeHit.GetValueInt() == 1' not in operational:
        errors.append('OPERATIONAL: IsOperational does not need the DLL running')
    for name, text in sources.items():
        for number, line in enumerate(code_only(text).splitlines(), 1):
            if re.search(r'SetNthEffect(?:Magnitude|Duration)\(', line) and not any(ok in line for ok in CASTS_ALLOWED):
                errors.append(f'CASTS: {name}: a shared spell record changed before a cast: {line.strip()}')
    if 'ScanTargets(' in code_only(fn(sources['ESSBElem3.psc'], 'PoisonFormTick')):
        errors.append('SCANS: PoisonFormTick scans every actor again')
    sink = re.sub(r'//[^\n]*', '', cpp_fn(cpp, 'void HitSinkCpp(const RE::TESHitEvent& ev) noexcept'))
    facts = re.sub(r'//[^\n]*', '', cpp_fn(cpp, 'essb::HitFacts ReadHitFacts('))
    if re.search(r'GetEquippedObject|ReadHand\(|HandIsEmpty', sink + facts):
        errors.append('SCANS: the hit sink reads your inventory')
    domains = cpp_fn(cpp, 'DomainScan ScanDomains(RE::PlayerCharacter& player, float radius)')
    if 'ForEachReferenceInRange' in domains or 'highActorHandles' in domains:
        errors.append('SCANS: the domains are found by a scan again')
    catches = re.findall(r'catch \(const std::exception& e\) \{\n\s*(\w+)\(e\.what\(\)\);', cpp)
    if not catches or any(c != 'SessionFault' for c in catches):
        errors.append('FAULTS: a C++ exception of ours is not a session fault')
    seconds = cpp_fn(cpp, 'float PapyrusRunningSeconds(RE::StaticFunctionTag*)')
    if re.search(r'\bFault\(', seconds):
        errors.append('FAULTS: RunningSeconds can fault the DLL')
    return errors


def source_faults(cpp, sources):
    caught = []

    def expect(label, cpp_text, srcs):
        if not check_sources(cpp_text, srcs):
            raise AssertionError(('fix28 source fault not caught', label))
        caught.append(label)

    def with_src(name, old, new):
        s = dict(sources)
        assert old in s[name], ('fix28 fault text not found', name, old[:60])
        s[name] = s[name].replace(old, new, 1)
        return s

    def cpp_with(old, new):
        assert old in cpp, ('fix28 fault text not found', old[:60])
        return cpp.replace(old, new, 1)

    expect('the switch waiting again', cpp, with_src('ESSBController.psc', '\tEcho(asArgs)\n\tIf !IsOperational()\n\t\tIf CachedDebugLevel >= 2\n\t\t\tLogEvent(2, "drop", "ESSB_Switch',
                                                     '\tEcho(asArgs)\n\tUtility.Wait(0.01)\n\tIf !IsOperational()\n\t\tIf CachedDebugLevel >= 2\n\t\t\tLogEvent(2, "drop", "ESSB_Switch')
           if '\r\n' not in sources['ESSBController.psc'] else
           with_src('ESSBController.psc', '\tEcho(asArgs)\r\n\tIf !IsOperational()\r\n\t\tIf CachedDebugLevel >= 2\r\n\t\t\tLogEvent(2, "drop", "ESSB_Switch',
                    '\tEcho(asArgs)\r\n\tUtility.Wait(0.01)\r\n\tIf !IsOperational()\r\n\t\tIf CachedDebugLevel >= 2\r\n\t\t\tLogEvent(2, "drop", "ESSB_Switch'))
    expect('the switch task not swapping the ability', cpp_with('    SetFormAbility(player, to);\n', ''), sources)
    expect('a switch not held for Papyrus', cpp_with('    if (!PapyrusReady()) {\n        state.pendingSwitch = element;', '    if (false) {\n        state.pendingSwitch = element;'), sources)
    expect('Setup not publishing readiness', cpp, with_src('ESSBController.psc', 'papyrusReady.SetValue(1.0)', 'papyrusReady.SetValue(0.0)'))
    expect('RefreshTree walking the nodes', cpp, with_src('ESSBTrees.psc', '\tLevelCache[aiTree] = TreeLevel(aiTree)', '\tWhile aiTree < 0\n\tEndWhile\n\tLevelCache[aiTree] = TreeLevel(aiTree)'))
    expect('the points read-modify-write again', cpp, with_src('ESSBTrees.psc', 'after = points.Mod(1.0) as Int', 'after = points.GetValueInt() + 1\n\t\tpoints.SetValueInt(after)'))
    expect('IsOperational without the DLL', cpp, with_src('ESSBController.psc', ' && NativeHit && NativeHit.GetValueInt() == 1\nEndFunction'.replace('\n', '\r\n' if '\r\n' in sources['ESSBController.psc'] else '\n'),
                                                        '\nEndFunction'.replace('\n', '\r\n' if '\r\n' in sources['ESSBController.psc'] else '\n')))
    expect('a shared spell record changed', cpp, with_src('ESSBController.psc', 'ESSBNative.CastWith(FearSpell, akTarget,', 'FearSpell.SetNthEffectDuration(0, seconds)\n\tESSBNative.CastWith(FearSpell, akTarget,'))
    expect('PoisonFormTick scanning', cpp, with_src('ESSBElem3.psc', 'Float heal = 6.0 * ESSBNative.PoisonedNearby()', 'Actor[] nearby = akCtl.ScanTargets(player, 1050.0, 5, player)\n\tFloat heal = 0.0'))
    expect('the hit sink reading the hands', cpp_with('    (void)player;\n    facts.enabled = state.forms.enabled->value;',
                                                      '    facts.right = ReadHand(player, false);\n    facts.enabled = state.forms.enabled->value;'), sources)
    expect('the domains by a cell walk', cpp_with('    DomainScan scan;\n    const std::uint64_t now = state.world.Ms();',
                                                  '    DomainScan scan;\n    RE::TES::GetSingleton()->ForEachReferenceInRange(&player, radius, nullptr);\n    const std::uint64_t now = state.world.Ms();'), sources)
    expect('a C++ exception as a hard fault', cpp_with('        SessionFault(e.what());', '        Fault(e.what());'), sources)
    # Round 28b
    expect('F2: the load keeps the saved ESSB_PapyrusReady', cpp_with('                ClearPapyrusReady();\n                OnGameReady();',
                                                                      '                OnGameReady();'), sources)
    expect('F2: a new game clears readiness after OnGameReady', cpp_with(
        '            ClearPapyrusReady();   // round 27h (Papyrus review 2)\n            OnGameReady();',
        '            OnGameReady();\n            ClearPapyrusReady();   // round 27h (Papyrus review 2)'), sources)
    expect('F3: the domains kept over a load', cpp_with('        state.domains.Clear();', ''), sources)
    expect('F4: the fault close keeps the pool', cpp_with('(f.bloodGuard && &base == f.bloodGuard) || ', ''), sources)
    expect('F5: 印潮 on a cut again', cpp_with('const bool surge = firstAfterSwitch && status.opened',
                                               'const bool surge = status.cutFrom != 0 && status.opened'), sources)
    expect('F5: an open arms 印潮', cpp_with('state.surgeArmed = kind == essb::SwitchKind::kSwitch && essb::IsElement(from);',
                                             'state.surgeArmed = true;'), sources)
    expect('F7: 水臨強化 without its cooldown', cpp_with('bin.waterAdventReady = state.waterAdvent.Ready(now);',
                                                      'bin.waterAdventReady = true;'), sources)
    expect('F1: CastWith scaling by the seconds again', cpp_with('call.effectiveness, false, call.magnitude, player);',
                                                               'seconds / facts.recordSeconds, false, call.magnitude, player);'), sources)
    expect('F1: the executor lets an effectiveness through', cpp_with('            effectiveness = 1.0f;\n        }\n        const bool watch',
                                                                    '        }\n        const bool watch'), sources)
    expect('RunningSeconds faulting', cpp_with('            LogOnce("[ESSB][skip] ESSBNative.RunningSeconds: the read failed (answered 0; the DLL keeps running)");\n        }',
                                               '            Fault("x");\n        }'), sources)
    return caught


def check_hazards(b, records):
    """Every effect of every hazard spell carries the three conditions (Papyrus review 5)."""
    import fix25_records as hit25
    import fix21_records as hit21
    errors = []
    want = hit25.hazard_conditions(b)
    by_edid = {r.edid: r for r in records}
    for element in hit25.DOMAIN_ELEMENTS:
        spell = by_edid.get(hit25.hazard_spell_edid(element))
        if not spell:
            errors.append(f'HAZARDS: no {hit25.hazard_spell_edid(element)}')
            continue
        items, current = [], None
        for key, value in spell.ss:
            if key == 'EFID':
                current = []
                items.append(current)
            elif key == 'CTDA' and current is not None:
                current.append(value)
        if not items or any(item != want for item in items):
            errors.append(f'HAZARDS: {spell.edid}: an effect without the three conditions (not you, not a teammate, hostile)')
    assert hit21.HOSTILE_CTDA in want
    return errors


def hazard_faults(b, records):
    import fix25_records as hit25

    class R:
        def __init__(self, r, ss):
            self.edid, self.ss = r.edid, ss

    target = hit25.hazard_spell_edid(hit25.DOMAIN_ELEMENTS[0])
    bad = []
    for r in records:
        if r.edid == target:
            ss, dropped = [], False
            for key, value in r.ss:
                if key == 'CTDA' and not dropped:
                    dropped = True
                    continue
                ss.append((key, value))
            bad.append(R(r, ss))
        else:
            bad.append(r)
    if not check_hazards(b, bad):
        raise AssertionError('a hazard effect without its conditions was not caught')
    return ['a hazard effect without its conditions']


def check_budget(sources):
    errors, rows = [], {}
    budget = pb.load(sources)
    for (script, name), limit in BUDGETS.items():
        cost = budget.function(script, name)
        rows[f'{script}.{name}'] = cost
        if cost > limit:
            errors.append(f'BUDGET: {script}.{name} makes up to {cost} native calls (the budget is {limit})')
    return errors, rows


def budget_fault(sources):
    s = dict(sources)
    text = s['ESSBTrees.psc']
    s['ESSBTrees.psc'] = text.replace(fn(text, 'RefreshTree'), OLD_REFRESH.replace('\n', '\r\n') if '\r\n' in text else OLD_REFRESH, 1)
    errors, rows = check_budget(s)
    if not errors:
        raise AssertionError('the 0.27.6 RefreshTree did not break the budget')
    return rows


def run(b):
    cpp = (ROOT / 'native/src/Plugin.cpp').read_text(encoding='utf-8')
    sources = {p.name: p.read_text(encoding='utf-8-sig') for p in SRC.glob('*.psc')}
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    header = (ROOT / 'native/include/ManifestData.h').read_text(encoding='utf-8')
    errors = check_sources(cpp, sources) + check_hazards(b, records) + check_castwith(b, records, sources, header)
    budget_errors, budget_rows = check_budget(sources)
    errors += budget_errors
    assert not errors, '\n  '.join(['FIX28 failed:'] + errors)
    caught = source_faults(cpp, sources) + hazard_faults(b, records) + castwith_faults(b, records, sources, header)
    old = budget_fault(sources)
    report = dict(source_faults=caught, budgets=budget_rows, old_refresh_budget=old, limits={f'{s}.{n}': v for (s, n), v in BUDGETS.items()})
    (ROOT / 'build/fix28-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX28 ok: switch in the DLL task (no ticket wait, abilities and the kept sync there), Papyrus readiness, the trees '
          f'(no node walk, the DLL reconcile, Mod), IsOperational, no shared-record casts, no scans in the sink / domains / 百毒不侵, '
          f'session faults, {len(__import__("fix25_records").DOMAIN_ELEMENTS)} hazard spells conditioned; '
          f'28b: readiness cleared at all three load points, the load resets, the fault close\'s pool, CastWith '
          f'({len(__import__("fix28_records").CASTWITH)} magnitude families of whole-second copies, every site checked), 印潮, '
          f'水臨強化\'s cooldown; budgets '
          + ', '.join(f'{k} {v}' for k, v in budget_rows.items())
          + f' (the 0.27.6 RefreshTree: OnCustomSkillIncrease {old["ESSBTrees.OnCustomSkillIncrease"]}); {len(caught)}/{len(caught)} faults caught')


if __name__ == '__main__':
    import runpy
    run(runpy.run_path(str(ROOT / 'build_v03.py'), run_name='fix28'))
