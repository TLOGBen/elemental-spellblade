from pathlib import Path
import re
# Reuse only the file-preserving helpers, never rerun the transformation.
s=Path('build/implement_fix9.py').read_text(encoding='utf8');exec(s[:s.index('# Backups')])
p='build_v03.py';s=read(p)
s=s.replace("ID_QUEST = 0x000800\nID_MCM_QUEST = 0x00515B", "sys.path.insert(0, str(WORK / 'build'))\nimport state_schema\nSTATE_SCHEMA_VERSION = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))['state_schema_version']\nSCHEMA_QUEST_IDS = state_schema.quest_ids(STATE_SCHEMA_VERSION)\nSCHEMA_STUBS = state_schema.stub_ids(STATE_SCHEMA_VERSION)\nID_QUEST = SCHEMA_QUEST_IDS['ESSB_MainQuest']\nID_MCM_QUEST = SCHEMA_QUEST_IDS['ESSB_MCMQuest']")
s=s.replace("    # Independent runtime-only MCM quest.","    # Retired forms have no scripts, start flag, or aliases. Never recycle these IDs.\n    for stub_edid, stub_id in SCHEMA_STUBS.items():\n        add('QUST', stub_id, stub_edid, [\n            ('FULL', Z('ESSB retired state schema')),\n            ('DNAM', struct.pack('<HBBII', 0, 0, 255, 0, 0)), ('NEXT', b''),\n        ])\n\n    # Independent runtime-only MCM quest.")
s=s.replace("('VMAD', vmad('ESSBSilence', {}))", "('VMAD', vmad('ESSBSilence', {'Controller': (1, own(ID_QUEST))}))")
s=s.replace("    for name, value in funcs:","    lines += ['Quest Function ControllerQuest() Global',\n              f'\\tReturn Game.GetFormFromFile(0x{ID_QUEST:06X}, \\\"Elements Spellblade.esp\\\") as Quest',\n              'EndFunction', '',\n              'Bool Function Operational() Global', '\\tQuest quest = ControllerQuest()',\n              '\\tIf !quest', '\\t\\tReturn False', '\\tEndIf',\n              '\\tESSBController ctl = quest.GetAlias(0) as ESSBController',\n              '\\tReturn ctl && ctl.IsOperational()', 'EndFunction', '']\n    for name, value in funcs:")
s=s.replace('def main():\n    write_state_helpers()', 'def main():\n    state_schema.preflight()\n    write_state_helpers()')
s=s.replace("    validate_fix3(check, written, fx_bindings)","    state_schema.verify(check, written['records'], sys.modules[__name__])\n    validate_fix3(check, written, fx_bindings)")
s=s.replace("current.get(e) == v for e, v in baseline.items()", "state_schema.stable_identity(e, current.get(e), v) for e, v in baseline.items()")
s=s.replace("manifest.get(e) == old for e, old in baseline.items()", "state_schema.stable_identity(e, manifest.get(e), old) for e, old in baseline.items()")
s=s.replace("written['records'].get(e) == old for e, old in fix2_records.items()", "state_schema.stable_identity(e, written['records'].get(e), old) for e, old in fix2_records.items()")
s=s.replace("if edid not in written['records'] or written['records'][edid]['id'] != old['id']", "if not state_schema.stable_identity(edid, written['records'].get(edid), old)")
s=s.replace('if e not in baseline}', 'if e not in baseline and e not in SCHEMA_STUBS}')
s=s.replace('if e not in baseline and e not in ID_BALANCE_GLOB', 'if e not in baseline and e not in SCHEMA_STUBS and e not in ID_BALANCE_GLOB')
s=s.replace("f'existing={len(baseline)} unchanged", "f'existing non-quest identities unchanged (schema checked); baseline={len(baseline)}")
s=s.replace("existing={len(baseline)} unchanged;", "existing non-quest IDs unchanged; baseline={len(baseline)};")
write(p,s)
# Legacy checkers keep all mechanical checks and delegate only the two explicit quest exceptions.
for file in ['fix6_verify.py','fix7_verify.py','fix8_verify.py']:
 p='build/'+file;s=read(p)
 s=s.replace("manifest.get(k)==v for k,v in baseline.items()", "b.state_schema.stable_identity(k,manifest.get(k),v) for k,v in baseline.items()")
 s=s.replace("written['records'].get(k)==v for k,v in baseline.items()", "b.state_schema.stable_identity(k,written['records'].get(k),v) for k,v in baseline.items()")
 s=s.replace("manifest.get(k) == v for k, v in before.items()", "b.state_schema.stable_identity(k,manifest.get(k),v) for k, v in before.items()")
 s=s.replace('if k not in baseline', 'if k not in baseline and k not in b.SCHEMA_STUBS')
 s=s.replace('if k not in before}', 'if k not in before and k not in b.SCHEMA_STUBS}')
 s=s.replace('existing={len(baseline)} unchanged', 'existing non-quest IDs unchanged; baseline={len(baseline)}')
 s=s.replace('existing={len(before)} unchanged', 'existing non-quest IDs unchanged; baseline={len(before)}')
 if file=='fix8_verify.py':
  s=s.replace("assert new_paths <= {'.codex/impl-fix-round8.html'}, new_paths", "assert new_paths <= {'.codex/impl-fix-round8.html', '.codex/impl-fix-round9.html', 'state-schema.lock.json'} | {p.relative_to(ROOT).as_posix() for p in (ROOT/'.codex/pre-fix9-snapshot').rglob('*') if p.is_file()} | {'.codex/fix-round9-briefing.md', '.codex/smoke2-essb-excerpt.log'}, new_paths")
 write(p,s)
# Silence also has a saved generation reference; old pre-FIX9 effects lack it and simply expire.
p='src/ESSBSilence.psc';s=read(p);s=s.replace('Actor Holder','Quest Property Controller Auto\n\nActor Holder',1);s=s.replace('If !ESSBState.Operational()', 'If !Controller || Controller != ESSBState.ControllerQuest() || !ESSBState.Operational()');s=s.replace('\tUnregisterForUpdate()','\t; The engine removes registrations after native AME teardown.');write(p,s)
# Remove native calls from a finished AME, and make FormRules startup binding gate unambiguous.
p='src/ESSBFormRules.psc';s=read(p);s=s.replace('\tIf Controller\n\t\tCtl = Controller.GetAlias(0) as ESSBController\n\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf\n\tEndIf','\tIf !Controller\n\t\tReturn\n\tEndIf\n\tCtl = Controller.GetAlias(0) as ESSBController\n\tIf !Ctl || !Ctl.IsOperational()\n\t\tReturn\n\tEndIf',1)
s=s.replace('\tMagickaEmptySince = -1.0\n\tUnregisterForUpdate()\n\tUnregisterForModEvent("ESSB_FormChanged")','\tMagickaEmptySince = -1.0\n\t; The engine removes registrations after native AME teardown.',1);write(p,s)
print('schema build wiring complete')
