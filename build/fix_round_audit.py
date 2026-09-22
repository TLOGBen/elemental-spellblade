"""Final scope, artifact and source-contract audit (offline, campaign-root writes only)."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tes import read_plugin

baseline = json.loads((ROOT / 'build/fix-round-baseline.json').read_text(encoding='utf8'))
manifest = json.loads((ROOT / 'build/v03-formids.json').read_text(encoding='utf8'))
compiler = json.loads((ROOT / 'build/v03-compile-results.json').read_text(encoding='utf8'))
records, meta = read_plugin(ROOT / 'package/Elements Spellblade/Elements Spellblade.esp')
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


check('masters exactly Skyrim.esm', meta['masters'] == ['Skyrim.esm'])
check('not ESL flagged', not meta['flags'] & 0x200)
check('record_count equals manifest', len(records) == manifest['record_count'])
check('zero duplicate FormIDs', len({r.key for r in records}) == len(records))
old_records, new_records = baseline['manifest']['records'], manifest['records']
check('all 3870 existing EDIDs retain their FormIDs', all(
    edid in new_records and old['id'] == new_records[edid]['id']
    for edid, old in old_records.items()))
check('ESSB_DebugLevel remains 000811', new_records['ESSB_DebugLevel']['id'] == '000811')
check('PERK EDID scheme unchanged',
      {k for k, v in old_records.items() if v['type'] == 'PERK'} ==
      {k for k, v in new_records.items() if v['type'] == 'PERK'})
check('all 17 scripts compile', len(compiler['results']) == 17 and
      all(r['exit_code'] == 0 for r in compiler['results']))
warnings = [dict(script=r['script'], line=line)
            for r in compiler['results'] for line in (r['stdout'] + '\n' + r['stderr']).splitlines()
            if re.search(r'\bwarning\b', line, re.I) and not re.search(r'\b0 warnings?\b', line, re.I)]
csf = json.loads((ROOT / 'build/csf-validate.json').read_text(encoding='utf8'))
check('CSF 13/13 valid', csf['totals']['files'] == csf['totals']['valid'] == 13)
coverage = json.loads((ROOT / 'build/plan-coverage.json').read_text(encoding='utf8'))
check('plan coverage zero unmapped / PENDING', coverage['totals']['unmapped'] == 0 and
      not any(k.startswith('PENDING') and v for k, v in coverage['totals']['by_status'].items()))
delivery = json.loads((ROOT / 'build/fix-round-delivery.json').read_text(encoding='utf8'))
check('all 120 spell and effect delivery pairs validated', delivery['valid'] and len(delivery['spells']) == 120)
protected = ['元素魔戰士規劃-v0.3.md', 'fx_extract.py',
             'review-2026-09-17.md', 'review-astra-A.md', 'review-astra-B.md']
check('plan / review / fx_extract hashes unchanged', all(
    hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == baseline['files'][name]['sha256']
    for name in protected))
log = (ROOT / '實作紀錄.md').read_bytes()
old_log = baseline['files']['實作紀錄.md']['text']
check('implementation log retains its entire original text',
      log.decode('utf-8-sig').replace('\r\n', '\n').startswith(old_log))


def function(text, name):
    return re.search(rf'(?m)^(?:\w+(?:\[\])? )?Function {name}\(.*?^EndFunction', text, re.S)[0]


changed = []
for name, old in baseline['files'].items():
    path = ROOT / name
    text = path.read_text(encoding='utf-8-sig')
    if hashlib.sha256(path.read_bytes()).hexdigest() != old['sha256']:
        changed.append(name)
    if path.suffix == '.psc':
        check(f'{name}: strict UTF-8, no replacement characters', '\ufffd' not in text)
        old_names = set(re.findall(r'\bFunction (\w+)\(', old['text'], re.I))
        new_names = set(re.findall(r'\bFunction (\w+)\(', text, re.I))
        check(f'{name}: every existing public function name retained', old_names <= new_names)
        sizes = [int(n) for n in re.findall(r'new \w+\[(\d+)\]', text)]
        check(f'{name}: arrays at most 128', all(n <= 128 for n in sizes))
        executable = '\n'.join(line.split(';')[0] for line in text.splitlines()
                               if not line.startswith('{'))
        if path.stem in {r['script'] for r in compiler['results']}:
            check(f'{name}: no forbidden wait / recurring update / cast calls', not re.search(
                r'\bUtility\.Wait\s*\(|\bRegisterForUpdate\s*\(|\.Cast\s*\(', executable, re.I))
        else:
            check(f'{name}: historical source not shipped and unchanged', text == old['text'])

ctl = (ROOT / 'src/ESSBController.psc').read_text(encoding='utf8')
old_ctl = baseline['files']['src\\ESSBController.psc']['text'] if 'src\\ESSBController.psc' in baseline['files'] else baseline['files']['src/ESSBController.psc']['text']
for name in ['CanRagdoll', 'TakePush', 'PlaceFx', 'PlayFormSound', 'StartDomain', 'PushSyncStage']:
    check(f'controller {name} preserved exactly', function(ctl, name) == function(old_ctl, name))
generator = (ROOT / 'build_v03.py').read_text(encoding='utf8')
old_generator = baseline['files']['build_v03.py']['text']
for name in ['write_fx_bindings', 'fx_vanilla_helpers']:
    pattern = rf'(?m)^def {name}\(.*?(?=^def |\Z)'
    old = re.search(pattern, old_generator, re.S)
    if old:
        check(f'generator {name} FX logic preserved', old[0] == re.search(pattern, generator, re.S)[0])
reactions = (ROOT / 'src/ESSBReactions.psc').read_text(encoding='utf8')
status = (ROOT / 'src/ESSBStatus.psc').read_text(encoding='utf8')
noform = (ROOT / 'src/ESSBNoForm.psc').read_text(encoding='utf8')
trees = (ROOT / 'src/ESSBTrees.psc').read_text(encoding='utf8')
check('P1-6 direct-hit true damage explicitly suppresses XP', all(
    '11, False)' in line for name in ['OnMartialHit', 'OnManaBreak']
    for line in function(noform, name).splitlines() if '.ApplyTrueDamage(' in line))
check('A11 tick and remaining bleed share one formula',
      'ESSBElem2.BleedPerLayer(Ctl)' in function(status, 'Tick') and
      'ESSBElem2.BleedPerLayer(akCtl)' in function(reactions, 'EndBlood'))
check('B6 decay publishes resource mirrors', all(
    f'{mutation}\n\t\tPushSelf()' in function(ctl, 'Tick')
    for mutation in ['SelfWind = 0', 'SelfCharge -= 1']))
check('B10 perpetual has no expiry', 'PerpetualKeep = t1' in function(ctl, 'OnFormClosed') and
      'PerpetualKeep' not in function(ctl, 'TickTimers') and
      'PerpetualKeep = 0' in function(ctl, 'SwitchForm'))
check('B11 purchase and both respec entries refresh abilities', all(
    'Controller.RefreshAbilities()' in function(trees, name)
    for name in ['Reconcile', 'RespecTree', 'RespecAll']))
check('A5 water handoff carries final end multiplier',
      'GuideMult(akCtl) * afMult' in function(reactions, 'EndWater'))
check('advisory execution adds only the missing x2',
      'afAmount * 2.0' in function((ROOT / 'src/ESSBElem3.psc').read_text(encoding='utf8'), 'AfterDeathCurse'))
result = {'checks_passed': len(checks), 'checks': checks, 'warnings': warnings,
          'changed_baseline_files': changed,
          'new_records': {k: v for k, v in new_records.items() if k not in old_records},
          'record_count': len(records), 'existing_records_stable': len(old_records),
          'delivery_contact': len(delivery['contact']), 'delivery_self': len(delivery['self']),
          'coverage': coverage['totals'], 'csf': csf['totals']}
(ROOT / 'build/fix-round-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({k: result[k] for k in ['checks_passed', 'warnings', 'changed_baseline_files',
                                      'record_count', 'existing_records_stable']}, ensure_ascii=False, indent=2))
