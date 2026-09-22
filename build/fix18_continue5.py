from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='src/ESSBController.psc';s=read(p);old=body(s,'ValidateBindings');new=old.replace('\tReturn True\nEndFunction','''\tInt checkProc = 0
\tWhile checkProc < ProcVariants.Length
\t\tIf !ProcVariants[checkProc] || ProcElements[checkProc] < 1 || ProcElements[checkProc] > 11 || ProcRatios[checkProc] <= 0.0
\t\t\tReturn False
\t\tEndIf
\t\tcheckProc += 1
\tEndWhile
\tcheckProc = 0
\tWhile checkProc < HitBonusSpells.Length
\t\tIf !HitBonusSpells[checkProc]
\t\t\tReturn False
\t\tEndIf
\t\tcheckProc += 1
\tEndWhile
\tReturn True
EndFunction''');s=s.replace(old,new);s=s.replace('; 血位（規劃 1.1）：100% ×1.3、70% ×1.1、30% ×0.8、10% ×0.6，線性內插。','; Phase 1 blood damage uses the approved four HP bands; leech retains its original curve.');write(p,s)
p='src/ESSBInput.psc';s=read(p).replace('Function Setup()\n\tIf !Ctl', 'Function Setup()\n\tReady = False\n\tIf !Ctl');s=s.replace('\tUnregisterForAllKeys()','''\tIf !Enabled || !CurrentElement || !FormActive || !HotkeysEnabled || !FormNotify || !FreeOpen || !Hotkeys
\t\tCtl.BreakState()
\t\tReturn
\tEndIf
\tIf Hotkeys.Length != 11
\t\tCtl.BreakState()
\t\tReturn
\tEndIf
\tInt checkKey = 0
\tWhile checkKey < Hotkeys.Length
\t\tIf !Hotkeys[checkKey]
\t\t\tCtl.BreakState()
\t\t\tReturn
\t\tEndIf
\t\tcheckKey += 1
\tEndWhile
\tUnregisterForAllKeys()''');write(p,s)
p='build/fix18_verify.py';s=read(p).replace('expected=r18.entries(b)',"expected=r18.entries(b,json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['lightning_roll_mode'])");s=s.replace('report=dict(player=player_sequences()',"import fix18_extra_checks as extra\n    report=dict(input=extra.input_checks(ROOT),target_combinations=extra.targets(sys.modules[__name__]),blood=extra.blood(sys.modules[__name__]),player=player_sequences()")
# run_path does not register the dynamic module, use explicit API carrying these globals.
s=s.replace('extra.targets(sys.modules[__name__])','extra.targets(NS(**globals()))').replace('extra.blood(sys.modules[__name__])','extra.blood(NS(**globals()))')
s=s.replace("print('FIX18 ok: six player sequences;", "print('FIX18 ok: 15 input gates; 88 target combinations; 88 blood cases; six player sequences;")
write(p,s)
p='build_v03.py';s=read(p).replace("runpy.run_path(str(WORK / 'build/fix18_verify.py'))['run']()", "runpy.run_path(str(WORK / 'build/fix18_verify.py'))['run']()\n    runpy.run_path(str(WORK / 'build/fix18_probes.py'))['run'](sys.modules[__name__])");write(p,s)
