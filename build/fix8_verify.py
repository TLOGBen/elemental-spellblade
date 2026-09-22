"""Round 8: execute actual Papyrus bodies offline and independently read final records."""
from pathlib import Path
from types import SimpleNamespace as NS
import json, math, re, runpy, hashlib, struct
ROOT = Path(__file__).resolve().parents[1]

def text(name):
    return (ROOT / name).read_text(encoding='utf-8-sig')

def body(name, fn):
    return re.search(r'(?m)^[^\n;]*\b(?:Function|Event) ' + fn + r'\(.*?^End(?:Function|Event)', text(name), re.S | re.M)[0]

def strip_fix12_logging(source):
    # FIX16 owns the corpse-settlement branch; retain exact comparison of living behavior.
    source = source.replace('If target.IsDead()\n\t\t\t\tCaptureDeath(index)\n\t\t\t\tClearSlot(index)\n\t\t\tElseIf player', 'If player')
    source = re.sub(r"\((\w+Left) > 0 && \1 > Utility.GetCurrentRealTime\(\)\)", r"\1 > 0", source)
    source = re.sub(r'(?m)^\s*CachedSync = [^\n]+\n', '', source)
    lines=source.splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i]
        if re.match(r'\s*If (?:\w+\.)?CachedDebugLevel >=',line):
            depth=1;i+=1
            while depth:
                if lines[i].strip().startswith('If '):depth+=1
                if lines[i].strip()=='EndIf':depth-=1
                i+=1
            continue
        if re.search(r'(?:ESSBLog.Log|LogEvent|LogThrottled)\(',line):
            while line.rstrip().endswith(chr(92)):
                i+=1;line=lines[i]
            i+=1;continue
        out.append(line);i+=1
    return '\n'.join(out)


def run():
    import sys
    sys.path.insert(0, str(ROOT))
    import build_v03 as b
    h = runpy.run_path(str(ROOT / 'build/fix6_verify.py'))
    Ctl, Actor, Glob, Script, make = [h[n] for n in ('Ctl', 'Actor', 'Glob', 'Script', 'make_scripts')]
    cfg = json.loads(text('settings.json'))
    records, meta = b.read_plugin(b.OUT / b.PLUGIN)
    rec = {r.edid: r for r in records}
    manifest = json.loads(text('build/v03-formids.json'))['records']
    before = json.loads(text('.codex/pre-fix8-snapshot/v03-formids.json'))['records']
    assert all(b.state_schema.stable_identity(k,manifest.get(k),v) for k, v in before.items())
    added = {k: v for k, v in manifest.items() if k not in before and k not in b.SCHEMA_STUBS and k not in b.GUARD_WINDOW_EDIDS and k not in b.hit18.new_edids(b)}
    assert set(added) == {'ESSB_MultUpkeep'}
    assert added['ESSB_MultUpkeep']['id'] == '00516D'
    assert int(added['ESSB_MultUpkeep']['id'], 16) > max(int(v['id'], 16) for v in before.values())
    glob = rec['ESSB_MultUpkeep']
    assert glob.sig == 'GLOB' and glob.d['FNAM'] == b'f'
    assert math.isclose(struct.unpack('<f', glob.d['FLTV'])[0], cfg['mult_upkeep'])
    assert meta['masters'] == ['Skyrim.esm'] and manifest['ESSB_DebugLevel']['id'] == '000811'
    quest = rec['ESSB_MainQuest'].d['VMAD']
    assert quest.count(b.vstr('MultUpkeep') + bytes([1, 1]) + b.obj(b.own(0x00516D))) == 1
    assert quest.count(b.vstr('NoformBaseTrue') + bytes([4, 1]) + struct.pack('<f', cfg['noform_base_true'])) == 1
    assert rec['ESSB_FormRulesEffect'].d['VMAD'] == b.vmad('ESSBFormRules', {
        'UpkeepBasePct': (4, cfg['upkeep_base_pct']), 'UpkeepDarkPct': (4, cfg['upkeep_dark_pct']),
        'UpkeepLevelRelief': (4, cfg['upkeep_level_relief']),
        'FormActive': (1, b.own(b.ID_GLOB['ESSB_FormActive'])),
        'CurrentElement': (1, b.own(b.ID_GLOB['ESSB_CurrentElement'])), 'Controller': (1, b.own(b.ID_QUEST))})

    # Exact inherited eligibility and opening/closing mechanics remain byte-for-byte unchanged.
    ctlfile = 'src/ESSBController.psc'
    for fn in ('OnFormClosed', 'BloodDrainPerSecond', 'BloodCostScale', 'PayBloodCost', 'BloodPowerCost'):
        assert strip_fix12_logging(body(ctlfile, fn).replace('If !IsCurrentController() || StateBroken', 'If StateBroken').replace('\n\tIf !IsOperational()\n\t\tReturn\n\tEndIf', '', 1).replace('\n\tIf StateBroken\n\t\tReturn\n\tEndIf', '', 1)) == strip_fix12_logging(body('build/fix8-before/' + ctlfile, fn)), fn
    # Round 18 relocates ToggleForm/CloseForm input publication; behavioral gates in fix18_verify.input_cases.
    assert 'InputLayer.RequestSwitch(aiIndex)' in body(ctlfile, 'ToggleForm')
    assert 'OnFormClosed(previous)' in body(ctlfile, 'CloseForm')
    oldhit = body('build/fix8-before/' + ctlfile, 'OnWeaponHit')
    # FIX11 owns eligibility regressions; all downstream round-8 mechanics stay exact.
    hit_tail = body(ctlfile, 'OnWeaponHit').split('\tLastHitPower = power', 1)[1]
    hit_tail = re.sub(r'\n\t\tLogRejectedHit\("invalid-element"[^\n]*', '', hit_tail)
    # FIX11 executes weapon eligibility and full proc/mark/XP; FIX12 adds slot passing and callsite logging gates.
    for token in ('PayBloodCost(BloodPowerCost())', 'ESSBElem2.WindBlade', 'ESSBElem.Discharge', 'WindFollowLeft > 0'):
        assert token in hit_tail and token in oldhit
    noform = body(ctlfile, 'OnNoFormHit')
    oldnoform = body('build/fix8-before/' + ctlfile, 'OnNoFormHit')
    assert 'ApplyNoFormBaseline(akTarget, abPower, riposte)' in noform
    assert 'ComboHits += 1' in noform and 'ESSBNoForm.EmberRatio(Self)' in noform
    assert noform.count('ApplyNoFormBaseline(') == 1
    for name in ('ESSBNoForm.OnMartialHit', 'ESSBNoForm.OnManaBreak'):
        assert noform.count(name + '(') == 1
    baseline = body(ctlfile, 'ApplyNoFormBaseline')
    assert 'GLevel(' not in baseline and 'BaseDamageMult.GetValue()' not in baseline
    truebody = body(ctlfile, 'ApplyTrueDamage')
    assert truebody.count('GLevel(') == 1 and truebody.count('BaseDamageMult.GetValue()') == 1
    assert 'If aiTree == 11 && !abBaseline' in truebody
    damage_cases = []
    for level in (1, 25, 50, 75, 100):
        for mult in (0.25, 1, 1.7, 3):
            for power in (False, True):
                ctl = Ctl(cfg); ctl.level = level; ctl.BaseDamageMult.x = mult; ctl.NoformBaseTrue = cfg['noform_base_true']
                ctl.rank_default = 15  # Low target magicka would otherwise activate TrueMult.
                xp = []; ctl.Trees.OnValidHitXP = lambda e: xp.append(e)
                g_calls = []; ctl.GLevel = lambda tree, lv=level: g_calls.append(tree) or (1 + .05 * lv)
                reg = make(ROOT / 'src', ctl); target = Actor(100); target.mag = 1
                reg['ESSBController'].ApplyNoFormBaseline(target, power)
                expected = cfg['noform_base_true'] * (1 + .05 * level) * mult * (1.5 if power else 1)
                assert math.isclose(target.true[-1], expected) and not xp and g_calls == [11]
                # Existing node damage must still receive TrueMult (backward-compatible default).
                target.true.clear(); reg['ESSBController'].ApplyTrueDamage(5, target, 11, False)
                assert math.isclose(target.true[-1], 5 * (1 + .05 * level) * mult * (1 + .03 * 15 * cfg['node_percent_scale']))
                damage_cases.append(dict(level=level,base_mult=mult,power=power,baseline=expected,extra_xp=len(xp)))
    ctl.NoformBaseTrue = 0; target.true.clear(); reg['ESSBController'].ApplyNoFormBaseline(target, False)
    assert not target.true

    ctl.rank_default = 0; ctl.NoformBaseTrue = cfg['noform_base_true']; target.true.clear()
    reg['ESSBController'].ApplyNoFormBaseline(target, False)
    assert math.isclose(target.true[-1], cfg['noform_base_true'] * 6 * 3) and not xp

    # All 11 trees: NodeScale affects only the new approved coefficients.
    node_cases = 0
    for scale in (0.25, 1, 1.7, 3):
        for rank in (0, 1, 15):
            ctl = Ctl(cfg); ctl.NodeScale.x = scale; ctl.rank_default = rank; reg = make(ROOT / 'src', ctl)
            for element in range(1, 12):
                assert math.isclose(reg['ESSBElem'].OpenMult(ctl, element), 1 + .03 * rank * scale)
                node_cases += 1
            assert math.isclose(reg['ESSBElem2'].BleedTickMult(ctl), 1 + .02 * rank * scale)
            for vip in (False, True):
                assert math.isclose(reg['ESSBElem2'].BleedDrainPercent(ctl, vip), (.003 + .0001 * rank) / (3 if vip else 1))
            assert math.isclose(reg['ESSBElem2'].QuakeStamina(ctl), 4 * (1 + .03 * rank) * 6)
            ctl.ranks = {(11, 0, 1): 0, (11, 0, 2): 0}; ctl.GetResolve = lambda: 5
            captured = []; ctl.ApplyTrueDamage = lambda amount, *args: captured.append(amount)
            reg['ESSBNoForm'].OnMartialHit(ctl, Actor(), NS(GetBaseDamage=lambda: 20), True)
            assert captured == ([] if rank == 0 else [20 * .03 * rank * scale]) or (rank > 0 and math.isclose(captured[0], 20 * .03 * rank * scale))

    # Real FormRules body; adapt syntax only, route its persistent variable to State.
    class Holder(Actor):
        def DamageActorValue(self, kind, amount):
            assert kind == 'Magicka' and 0 < amount <= self.mag; self.mag -= amount
    ctl = Ctl(cfg); ctl.MultUpkeep = Glob(1); holder = Holder(300)
    active = Glob(1); element = Glob(1); state = NS(MagickaEmptySince=-1.0)
    env = NS(Ctl=ctl,Holder=holder,FormActive=active,CurrentElement=element,
             UpkeepBasePct=cfg['upkeep_base_pct'],UpkeepDarkPct=cfg['upkeep_dark_pct'],UpkeepLevelRelief=cfg['upkeep_level_relief'])
    reg = {}; script = Script(ROOT/'src/ESSBFormRules.psc', reg, env)
    script.source = re.sub(r'(?m)^Event ', 'Function ', script.source).replace('EndEvent', 'EndFunction')
    script.source = script.source.replace(' as ESSBController', '')
    script.source = script.source.replace('MagickaEmptySince', 'State.MagickaEmptySince')
    ctl.IsOperational = lambda: True
    env.Controller = object(); env.ESSBState = NS(ControllerQuest=lambda: env.Controller)
    env.State = state; clock = NS(now=10.0); scheduled = []; closed = []; notices = []; blood = []
    env.Utility = NS(GetCurrentRealTime=lambda: clock.now)
    env.Debug = NS(Notification=lambda s: notices.append(s))
    env.RegisterForSingleUpdate = lambda n: scheduled.append(n)
    env.UnregisterForUpdate = lambda: scheduled.clear()
    ctl.BloodDrainPerSecond = lambda: .006
    ctl.PayBloodCost = lambda v: blood.append(v)
    def close():
        closed.append(clock.now); active.x = 0; element.x = 0
    ctl.CloseForm = close
    upkeep = []
    for level in (1, 25, 50, 75, 100):
        ctl.Trees.TreeLevel = lambda tree, lv=level: lv
        for scale in (0, .5, 1, 1.7, 3):
            ctl.MultUpkeep.x = scale
            for e in range(1, 12):
                cost = script.MagickaUpkeep(e)
                pct = cfg['upkeep_dark_pct'] if e == 10 else cfg['upkeep_base_pct']
                assert math.isclose(cost, 300 * pct / 100 * (1 - cfg['upkeep_level_relief'] * level / 100) * scale, abs_tol=1e-10)
                if scale == 1 and e in (1, 10): upkeep.append(dict(level=level,dark=e==10,per_second=cost))
    seen = []; ctl.Trees.TreeLevel = lambda tree: seen.append(tree) or 25
    for e in range(1,12): script.MagickaUpkeep(e)
    assert seen == list(range(11))
    ctl.MultUpkeep.x = 1; active.x = 1; element.x = 1; holder.mag = 1
    script.OnUpdate(); assert state.MagickaEmptySince == 10 and not closed
    clock.now = 11; script.OnUpdate(); assert not closed
    clock.now = 12; scheduled.clear(); script.OnUpdate()
    assert closed == [12] and len(notices) == 1 and not scheduled
    script.OnUpdate(); assert len(notices) == len(closed) == 1
    # Recovery cancels previous grace. A new depletion must receive a fresh full grace.
    active.x = 1; element.x = 10; holder.mag = 0; clock.now = 20; script.OnUpdate()
    holder.mag = 100; clock.now = 21; script.OnUpdate(); assert state.MagickaEmptySince == -1
    holder.mag = 0; clock.now = 22; script.OnUpdate(); assert len(closed) == 1
    clock.now = 23; script.OnUpdate(); assert len(closed) == 1
    clock.now = 24; script.OnUpdate(); assert closed == [12,24] and len(notices) == 2
    # Switching while empty does not restart the grace; manual close does clear it.
    active.x = 1; element.x = 1; holder.mag = 0; clock.now = 30; script.OnUpdate()
    element.x = 2; script.OnESSBFormChanged('', 'open', 2, None); assert state.MagickaEmptySince == 30
    active.x = 0; script.OnESSBFormChanged('', 'close', 0, None); assert state.MagickaEmptySince == -1 and not scheduled
    # Free upkeep means no mana or health maintenance; multiplier scales blood exactly once.
    for scale in (0, .5, 1, 1.7, 3):
        active.x = 1; element.x = 6; holder.mag = 300; ctl.MultUpkeep.x = scale; state.MagickaEmptySince = -1
        script.OnUpdate(); assert math.isclose(blood[-1], .006 * scale)
        assert holder.mag == 300  # blood form pays health only (user decision 2026-09-18): no magicka upkeep
    form = text('src/ESSBFormRules.psc')
    assert 'Utility.Wait' not in form and 'RegisterForUpdate(' not in form
    assert form.count('RegisterForSingleUpdate(') == text('build/fix8-before/src/ESSBFormRules.psc').count('RegisterForSingleUpdate(') + 2  # load ready event and temporary-not-ready retry
    assert 'DamageActorValue("Health"' not in form
    assert 'MultDrain' not in form and 'MultRecovery' not in form and 'MultDuration' not in form

    rows = json.loads(text('build/fix6-classification.json'))
    assert len(rows) == 195 and not any(r['status']=='DECISION' for r in rows)
    approved = [r for r in rows if r['reason'].startswith('fix8')]
    assert len(approved) == 14 and sum(r['status']=='SCALED' for r in approved)==13
    bloodrow = next(r for r in approved if r['tree']=='blood' and r['route']==0)
    assert bloodrow['old'].split('，',1)[1] == bloodrow['new'].split('，',1)[1]
    labels={'SCALED':f'×{cfg["node_percent_scale"]:g}','UNCHANGED':'不改','SPECIFIC':'第2／2b項指定'}
    lines=['# 195 主線完整分類（fix round 8 決策已結清）','','| 樹 | 路線 | 階 | 分類／原因 | 原文 | 顯示文字 | 程式位置 |','|---|---|---|---|---|---|---|']
    for r in rows:
        site='；'.join(x[0] for x in r.get('code_sites',[])) or r['site']
        values=[r['tree'],r['route_name'],r['tier_name'],labels[r['status']]+'：'+r['reason'],r['old'],r['new'],site]
        lines.append('| '+' | '.join(v.replace('|','／') for v in values)+' |')
    path=ROOT/'build/fix6-classification.md'; raw=path.read_bytes(); nl='\r\n' if b'\r\n' in raw else '\n'
    path.write_bytes((nl.join(lines)+nl).encode('utf-8'))
    coverage=json.loads(text('build/plan-coverage.json'))
    addition=[r for r in coverage['rows'] if r['section']=='fix8 addition']
    assert len(addition)==1 and addition[0]['kind']=='mechanism' and addition[0]['edid']=='-'
    assert coverage['totals']['unmapped']==0 and coverage['totals']['nodes']==495

    # Immutable files and original encodings; only exact authorized source paths may differ.
    hashes=json.loads(text('build/fix8-scope-before.json')); changed=[]
    # The ongoing campaign ledger changed after round 8, before this hotfix.
    protected=json.loads(text('build/fix9-protected-hashes.json'))
    hashes['.strategic-advance/essb-standalone-build/run-ledger.jsonl']=protected['.strategic-advance/essb-standalone-build/run-ledger.jsonl']
    for name,digest in hashes.items():
        if name.startswith('.strategic-advance/'): continue  # commander's campaign ledger is append-only by design
        data=(ROOT/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:
            assert name in ('build_v03.py','settings.json','plan_coverage.py','實作紀錄.md') or (name.startswith('src/') and name.endswith('.psc')),name
            changed.append(name)
    for p in (ROOT/'build/fix8-before').rglob('*'):
        if not p.is_file(): continue
        name=p.relative_to(ROOT/'build/fix8-before'); q=ROOT/name
        old=p.read_bytes(); new=q.read_bytes()
        if str(name)=='實作紀錄.md':
            # Round18 already normalized this older mixed-newline ledger.
            # Freeze the actual pre-18b bytes, and retain the round8 text prefix.
            current_baseline=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
            assert current_baseline.replace(b'\r\n',b'\n').startswith(old.replace(b'\r\n',b'\n'))
            assert new.startswith(current_baseline)
            old=current_baseline
        assert old.startswith(b'\xef\xbb\xbf')==new.startswith(b'\xef\xbb\xbf'),str(name)
        if old.count(b'\n'):
            assert (old.count(b'\r\n')==old.count(b'\n'))==(new.count(b'\r\n')==new.count(b'\n')),str(name)
        if str(name)=='實作紀錄.md':assert new.startswith(old)
    # Round 18 supplied specifications predate this run; allow their presence, freeze their content.
    round18_specs = {'design-latency-2026-09-20.md': 'e3866f99eebb67844f3f440ee37798e3e0bcb224df4e4f8a143ead11f502ec44', '元素魔戰士規劃-v0.3_alter.md': 'ba97abd041c6b842e89efac04550f469b79977d4455b711be695e8264bf91832'}
    for name, digest in round18_specs.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    new_paths = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.relative_to(ROOT).parts[0] not in ('build','package','.codex','.strategic-advance','__pycache__')} - set(hashes)
    assert new_paths <= set(protected) | set(round18_specs) | {'src/ESSBInput.psc', 'src/ESSBProbeMeter.psc', 'src/ESSBProbeSegment.psc', 'src/ESSBProbeSetup.psc', 'src/ESSBProbePower.psc'} | {'.codex/impl-fix-round8.html', '.codex/impl-fix-round9.html', 'state-schema.lock.json', 'review-2026-09-18.md', 'review-fable-2026-09-19.md', 'review-fable-2026-09-19-r15.md'} | {p.relative_to(ROOT).as_posix() for p in (ROOT/'.codex/pre-fix9-snapshot').rglob('*') if p.is_file()} | {'.codex/fix-round9-briefing.md', '.codex/smoke2-essb-excerpt.log'}, new_paths
    report=dict(existing_unchanged=len(before),appended=added,masters=meta['masters'],upkeep_300=upkeep,
                damage_cases=damage_cases,node_cases=node_cases,decisions_resolved=14,
                grace_scenarios=['depletion at t10 -> close at t12 once','recovery cancels; new depletion t22 -> close t24','empty switch retains grace','manual close clears grace','blood/free upkeep'],
                G_once=True,base_mult_once=True,upkeep_mult_once=True,node_scale_once=True,extra_xp=0,
                changed_source_files=changed,runtime_tested=False)
    (ROOT/'build/fix8-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'FIX8 ok: existing non-quest IDs unchanged; baseline={len(before)}; appended GLOB=0x00516D; 11 upkeep forms; 2s grace; {len(damage_cases)} baseline cases; 14 decisions; G/sliders once; encodings/scope checked')
    return report

if __name__=='__main__':run()
