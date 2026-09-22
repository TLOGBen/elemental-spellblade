from pathlib import Path
import json, re,hashlib
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='build/fix18_records.py';s=read(p).replace('function=6,epft=3','function=10,epft=5');write(p,s)
s=read('build_v03.py')
s=s.replace("'ESSBSettingsEffect', 'ESSBState', 'ESSBMCM']","'ESSBSettingsEffect', 'ESSBState', 'ESSBMCM', 'ESSBInput']")
s=s.replace('FUNC_HAS_MAGIC_EFFECT_KEYWORD = 693','FUNC_HAS_MAGIC_EFFECT_KEYWORD = 699')
s=s.replace('def entry(entry_point, value, conditions, tabs=3, function=EPF_MULT):','def entry(entry_point, value, conditions, tabs=3, function=EPF_MULT, epft=1):')
s=s.replace("('EPFT', bytes([1])), ('EPFD', F(value))","('EPFT', bytes([epft])), ('EPFD', F(value) if epft == 1 else I(value))")
# module import uses existing build sys.path setup
pos=s.index('def build_esp(plan):')
s=s[:pos]+'import fix18_records as hit18\n\n\n'+s[pos:]
s=s.replace('    # -------------------------------------------------------------- KYWD','    hit18.add_records(sys.modules[__name__], add, settings)\n\n    # -------------------------------------------------------------- KYWD',1)
s=s.replace('    # -------------------------------------------------------------- 形態能力','    hit18.weapon_glows(sys.modules[__name__], add, fx_records, fxe)\n\n    # -------------------------------------------------------------- 形態能力',1)
s=s.replace("hit_shader=fxe('aura', ix), enchant_shader=fxe('aura', ix)","hit_shader=0, enchant_shader=0")
a=s.index('        glow = []');z=s.index("        add('SPEL', ID_FORM_ABILITY_SPELL",a)
s=s[:a]+'''        glow = []
        for stage in range(3):
            glow += [('EFID', I(own(hit18.WEAPON_EFFECT + ix * 3 + stage))),
                     ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
                     ('CTDA', gv_ge(sync_stage_global, stage + 1 if stage else 0))]
            if stage < 2:
                glow.append(('CTDA', ctda(0x80, stage + 2, 74, sync_stage_global)))
'''+s[z:]
# Existing hit forms keep IDs; bloodrage uses quiet second damage effect under player HP condition.
s=s.replace("            effect = hit_power_ids.get(power, ID_HIT_EFFECT + ix)","""            if name == 'Blood':
                magnitude *= 1.25
            effect = hit_power_ids.get(power, ID_HIT_EFFECT + ix)""")
s=s.replace("                 if name == 'Lightning' else []))","""                 if name == 'Lightning' else []) + (
                 [('EFID', I(own(hit18.BONUS_EFFECT + ix))), ('EFIT', struct.pack('<fII', magnitude * 0.15, 0, 0)),
                  ('CTDA', ctda(CTDA_GE, 0.3, 640, 24, run_on=2, reference=ref('Skyrim.esm', 0x14))),
                  ('CTDA', ctda(0xA0, 0.7, 640, 24, run_on=2, reference=ref('Skyrim.esm', 0x14))),
                  ('CTDA', ctda(CTDA_EQ, 1, 448, own(ID_BRANCH_PERK + (5*15+3)*4+1), run_on=2, reference=ref('Skyrim.esm', 0x14)))]
                 if name == 'Blood' else []) +
                 [('EFID', I(own(ID_ENGAGED_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 30))])

    hit18.append_variants(sys.modules[__name__], rr, add, settings)""")
# binding props before mechanical globals
marker='    for ix, (name, _default) in enumerate(MECH_GLOBALS):\n        # 屬性名'
pos=s.index(marker)
s=s[:pos]+'''    proc_rows = hit18.variants(sys.modules[__name__])
    props.update({
        'HitProcPerk': (1, own(hit18.HIT_PERK)),
        'GDivineArmed': (1, own(hit18.DIVINE_ARMED)),
        'FormNotify': (1, own(hit18.NOTIFY)), 'FormSound': (1, own(hit18.SOUND)),
        'Guard': (1, (own(ID_QUEST), 0)), 'InputLayer': (1, (own(ID_QUEST), 0)),
        'ProcVariants': (11, [own(v['id']) for v in proc_rows]),
        'ProcElements': (13, [v['e'] for v in proc_rows]),
        'ProcRatios': (14, [v['ratio'] for v in proc_rows]),
        'ProcPowers': (13, [v['p'] for v in proc_rows]),
        'ProcSneaks': (13, [v['s'] for v in proc_rows]),
        'ProcBloodBands': (13, [v['band'] for v in proc_rows]),
        'HitBonusSpells': (11, [own(hit18.BONUS_SPELL+i) for i in range(11)]),
    })
'''+s[pos:]
pos=s.index('    quest_vmad = ')
s=s[:pos]+'''    guard_props.update({
        'Enabled': (1, own(ID_GLOB['ESSB_Enabled'])),
        'FormActive': (1, own(ID_GLOB['ESSB_FormActive'])),
        'DivineArmed': (1, own(hit18.DIVINE_ARMED)),
        **{name: (1, own(manifest['ESSB_'+name]['id'] and int(manifest['ESSB_'+name]['id'],16)))
           for name in ['RockArmor','IceShield','WaterMirror','GuardWind']},
    })
    input_props = {'Ctl': (1, (own(ID_QUEST), 0)),
        **{name: (1, own(ID_GLOB['ESSB_'+name])) for name in ['Enabled','CurrentElement','FormActive']},
        'HotkeysEnabled': (1, own(hit18.KEY_ENABLE)), 'FormNotify': (1, own(hit18.NOTIFY)),
        'FreeOpen': (1, own(int(manifest['ESSB_FreeOpen']['id'],16))),
        'Hotkeys': (11, [own(hit18.HOTKEYS+i) for i in range(11)])}
'''+s[pos:]
s=s.replace("struct.pack('<3H', 5, 2, 3)\n                  + script('ESSBController'","struct.pack('<3H', 5, 2, 4)\n                  + script('ESSBController'")
s=s.replace("+ script('ESSBGuard', guard_props))","+ script('ESSBGuard', guard_props)\n                  + script('ESSBInput', input_props))")
# count is computed from rr? inspect later
s=s.replace('    # -------------------------------------------------------------- 組檔','    entry_count += len(hit18.entries(sys.modules[__name__], settings["lightning_roll_mode"]))\n\n    # -------------------------------------------------------------- 組檔',1)
# MCM
s=s.replace("    config = {'modName':", """    hotkeys = [control('ESSB_HotkeysEnabled', '直接切換熱鍵', 'toggle', defaultValue=1),
               control('ESSB_FormNotify', '切換文字提示', 'toggle', defaultValue=1),
               control('ESSB_FormSound', '切換音效', 'toggle', defaultValue=1)]
    hotkeys += [control('ESSB_Hotkey_'+n, label, 'keymap', defaultValue=hit18.KEY_CODES[i])
                for i,(n,label) in enumerate(zip(ELEMENTS,ZH))]
    config = {'modName':""")
s=s.replace("'content': trees}]}","'content': trees},\n                        {'pageDisplayName': '熱鍵', 'cursorFillMode': 'topToBottom', 'content': hotkeys}]}")
# Validator updates only for explicitly replaced representations, existing identity/layout guards retained.
s=s.replace("and e not in GUARD_WINDOW_EDIDS}","and e not in GUARD_WINDOW_EDIDS and not 0x5200 <= int(v['id'],16) < 0x5300}")
s=s.replace("assert set(added) == FIX5_NEW_EDIDS | GUARD_WINDOW_EDIDS |", "assert set(added) == {e for e,v in manifest.items() if 0x5200 <= int(v['id'],16) < 0x5300} | FIX5_NEW_EDIDS | GUARD_WINDOW_EDIDS |")
s=s.replace("['一般', '平衡', '技能樹']","['一般', '平衡', '技能樹', '熱鍵']")
s=s.replace("assert glob_edids == expected_globals and len(glob_edids) == 38","expected_globals |= {'ESSB_Hotkey_'+n for n in ELEMENTS} | {'ESSB_HotkeysEnabled','ESSB_FormNotify','ESSB_FormSound'}\n    assert glob_edids == expected_globals and len(glob_edids) == 52")
s=s.replace("            shader = by_id[shader_id]","            if role == 'aura':\n                assert shader_id == 0 and struct.unpack_from('<I', effect.d['DATA'], 36)[0] == 0\n                continue\n            shader = by_id[shader_id]",1)
s=s.replace("    runpy.run_path(str(WORK / 'build/fix16_verify.py'))['run']()","    runpy.run_path(str(WORK / 'build/fix16_verify.py'))['run']()\n    runpy.run_path(str(WORK / 'build/fix18_verify.py'))['run']()")
write('build_v03.py',s)
sett=read('settings.json').replace('"state_schema_version": 6','"state_schema_version": 7')
data=json.loads(sett);data.update(lightning_roll_mode='chain',form_notify=True,form_sound=True,hotkeys_enabled=True);write('settings.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# Quiet bloodrage effect index 1 follows the same cached base.
c=read('src/ESSBController.psc');c=c.replace('ProcWritten[i] = value','ProcWritten[i] = value\n\t\t\tIf e == 6\n\t\t\t\tProcVariants[i].SetNthEffectMagnitude(1, value * 0.15)\n\t\t\tEndIf')
write('src/ESSBController.psc',c)
