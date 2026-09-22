from pathlib import Path
W=Path(__file__).resolve().parents[1]
def edit(path,fn):
 p=W/path;raw=p.read_bytes();s=raw.decode('utf-8');crlf=b'\r\n' in raw;s=s.replace('\r\n','\n');new=fn(s);p.write_bytes(new.replace('\n','\r\n').encode('utf-8') if crlf else new.encode('utf-8'))
perks=[('TieA',0x860),('TieB',0x861),('TieA2',0x863),('TieB2',0x862)]
globs=[('TieVariant',0x870)]+[(f'TieResult{i}',0x870+i) for i in range(1,5)]
props=''.join(f'Perk Property {n} Auto\n' for n,_ in perks)+''.join(f'GlobalVariable Property {n} Auto\n' for n,_ in globs)
def setup(s):
 s=s.replace('Spell Property ThirdPower Auto','Spell Property FourthPower Auto\nInt TieNext\n'+props+'Spell Property ThirdPower Auto')
 s=s.replace('player.AddSpell(ThirdPower, False)','player.AddSpell(ThirdPower, False)\n\tplayer.AddSpell(FourthPower, False)')
 s=s.replace('「第三題」、「清理」','「第三題」、「第四題」、「清理」')
 s=s.replace('player.RemovePerk(CrossB2)','player.RemovePerk(CrossB2)\n'+''.join(f'\tplayer.RemovePerk({n})\n' for n,_ in perks).rstrip())
 s=s.replace('CrossSecond = False\n\t\tplayer.RemoveSpell','CrossSecond = False\n\t\tTieNext = 0\n\t\tResetTie()\n\t\tplayer.RemoveSpell(FourthPower)\n\t\tplayer.RemoveSpell')
 s=s.replace('第三題能力已移除','第三、四題能力已移除')
 s=s.replace('mode == 1 || mode == 2 || mode == 4','mode == 1 || mode == 2 || mode == 4 || mode == 5')
 s=s.replace('\t\t\tElse\n\t\t\t\tIf !CrossSecond','\t\t\tElseIf mode == 5\n\t\t\t\tSetupTie(player)\n\t\t\tElse\n\t\t\t\tIf !CrossSecond')
 s=s.replace('If mode == 4\n\t\t\t\tLogSetup','If mode == 5\n\t\t\t\tLogSetup("PROBE=4 variant=" + (TieNext + 1) + " priority=0/0; v1 A-low/first; v2 A-high/first; v3 A-low/last; v4 A-high/last; fresh_meter=" + attached, Bandit, player)\n\t\t\tElseIf mode == 4\n\t\t\t\tLogSetup')
 s=s.replace('If mode == 4\n\t\t\t\t\tCrossSecond','If mode == 5\n\t\t\t\t\tTieNext += 1\n\t\t\t\t\tIf TieNext >= 4\n\t\t\t\t\t\tTieNext = 0\n\t\t\t\t\tEndIf\n\t\t\t\t\tmode = 4\n\t\t\t\tElseIf mode == 4\n\t\t\t\t\tCrossSecond')
 s+='\nFunction ResetTie()\n\tIf TieVariant\n\t\tTieVariant.SetValue(0.0)\n'+''.join(f'\t\tTieResult{i}.SetValue(0.0)\n' for i in range(1,5))+'\tEndIf\nEndFunction\n\nFunction SetupTie(Actor player)\n\tIf TieNext == 0\n\t\tResetTie()\n\tEndIf\n\tTieVariant.SetValue(TieNext + 1)\n\tPerk a = TieA\n\tPerk b = TieB\n\tIf TieNext == 1 || TieNext == 3\n\t\ta = TieA2\n\t\tb = TieB2\n\tEndIf\n\tIf TieNext < 2\n\t\tplayer.AddPerk(a)\n\t\tplayer.AddPerk(b)\n\tElse\n\t\tplayer.AddPerk(b)\n\t\tplayer.AddPerk(a)\n\tEndIf\nEndFunction\n'
 return s
def meter(s):
 s=s.replace('GlobalVariable Property Gate Auto',props+'GlobalVariable Property Gate Auto')
 s=s.replace('ElseIf probe == 3 || probe == 4','ElseIf probe >= 5 && probe <= 8\n\t\tInt winner = TieWinner(damage, a, b, c, False)\n\t\tReturn "equal-priority variant=" + (probe - 4) + " winner=" + winner + " (1=A5,2=B7,3=both,0=unexpected); compare all four variants before deciding property"\n\tElseIf probe == 3 || probe == 4')
 s=s.replace('Int cross = CrossMode()','Int cross = CrossMode()\n\tInt tie = TieMode()\n\tIf tie != 0\n\t\tIf tie > 0 && cross == 0 && !Player.HasPerk(ProbeAB) && !Player.HasPerk(ProbeHit) && !Player.HasPerk(ProbeMultiply)\n\t\t\tReturn tie\n\t\tEndIf\n\t\tReturn 0\n\tEndIf')
 s=s.replace('; 3=third question', '; 5..8=fourth question variants 1..4 priority zero (see SETUP); 3=third question')
 s=s.replace('String answer = Verdict(Mode, damage / CalibrationK, CountA, CountB, CountC, Bad)','String answer = Verdict(Mode, damage / CalibrationK, CountA, CountB, CountC, Bad)\n\t\t\tIf Mode >= 5 && Mode <= 8\n\t\t\t\tRememberTie(TieWinner(damage / CalibrationK, CountA, CountB, CountC, Bad))\n\t\t\tEndIf')
 s+='''
Int Function TieMode()
	If TieA && TieB && TieA2 && TieB2 && TieVariant
		Int v = TieVariant.GetValue() as Int
		Bool pair1 = Player.HasPerk(TieA) && Player.HasPerk(TieB) && !Player.HasPerk(TieA2) && !Player.HasPerk(TieB2)
		Bool pair2 = !Player.HasPerk(TieA) && !Player.HasPerk(TieB) && Player.HasPerk(TieA2) && Player.HasPerk(TieB2)
		If (pair1 && (v == 1 || v == 3)) || (pair2 && (v == 2 || v == 4))
			Return v + 4
		ElseIf Player.HasPerk(TieA) || Player.HasPerk(TieB) || Player.HasPerk(TieA2) || Player.HasPerk(TieB2)
			Return -1
		EndIf
	EndIf
	Return 0
EndFunction

Int Function TieWinner(Float damage, Int a, Int b, Int c, Bool invalid)
	If invalid || c != 0
		Return 0
	ElseIf a == 1 && b == 0 && Near(damage, 5.0)
		Return 1
	ElseIf a == 0 && b == 1 && Near(damage, 7.0)
		Return 2
	ElseIf a == 1 && b == 1 && Near(damage, 12.0)
		Return 3
	EndIf
	Return 0
EndFunction

String Function TieDecision(Int r1, Int r2, Int r3, Int r4)
	If r1 == 0 || r2 == 0 || r3 == 0 || r4 == 0
		Return "equal_priority_decider = unknown; need four valid variants"
	ElseIf r1 == 1 && r2 == 2 && r3 == 1 && r4 == 2
		Return "equal_priority_decider = lower FormID (supported by four variants; record order held A then B)"
	ElseIf r1 == 2 && r2 == 1 && r3 == 2 && r4 == 1
		Return "equal_priority_decider = higher FormID (supported by four variants; record order held A then B)"
	ElseIf r1 == 1 && r2 == 1 && r3 == 2 && r4 == 2
		Return "equal_priority_decider = added to player first (supported by four variants)"
	ElseIf r1 == 2 && r2 == 2 && r3 == 1 && r4 == 1
		Return "equal_priority_decider = added to player last (supported by four variants)"
	ElseIf r1 == 3 && r2 == 3 && r3 == 3 && r4 == 3
		Return "equal_priority_decider = none; additive in tested equal-priority pairs"
	ElseIf r1 == r2 && r2 == r3 && r3 == r4
		Return "equal_priority_decider = unresolved spell identity / physical PERK record order; fixed A or B"
	EndIf
	Return "equal_priority_decider = unknown; inconsistent pattern, repeat on fresh save"
EndFunction

Function RememberTie(Int winner)
	If Mode == 5
		TieResult1.SetValue(winner)
	ElseIf Mode == 6
		TieResult2.SetValue(winner)
	ElseIf Mode == 7
		TieResult3.SetValue(winner)
	ElseIf Mode == 8
		TieResult4.SetValue(winner)
	EndIf
	Int r1 = TieResult1.GetValue() as Int
	Int r2 = TieResult2.GetValue() as Int
	Int r3 = TieResult3.GetValue() as Int
	Int r4 = TieResult4.GetValue() as Int
	Debug.Trace("[ESSB-PROBE] VERDICT TIE results=" + r1 + "," + r2 + "," + r3 + "," + r4 + "; " + TieDecision(r1, r2, r3, r4))
EndFunction
'''
 return s
edit('src/ESSBProbeSetup.psc',setup);edit('src/ESSBProbeMeter.psc',meter)
extra=repr(perks+globs)[1:-1]
edit('build/fix18e_records.py',lambda s:s.replace("(4, 0x847", "(5, 0x880, 0x881, 'ESSB_ProbeFourthPower', '探針：第四題'),\n          (4, 0x847").replace("('CrossB2', 0x853)]", "('CrossB2', 0x853), ('FourthPower', 0x880), "+extra+"]"))
def recipe(s):
 s=s.replace("('CrossB2',0x853)]","('CrossB2',0x853),"+extra+"]")
 s=s.replace("(0x833,'ESSB_ProbeSession')]","(0x833,'ESSB_ProbeSession'),"+repr([(fid,n) for n,fid in globs])[1:-1]+"]")
 s=s.replace("('CTDA',b.ctda(0,1,448,b.own(0x852),run_on=2,reference=0x14))", "('CTDA',b.ctda(1,1,448,b.own(0x852),run_on=2,reference=0x14)),('CTDA',b.ctda(1,1,448,b.own(0x860),run_on=2,reference=0x14)),('CTDA',b.ctda(0,1,448,b.own(0x863),run_on=2,reference=0x14))")
 s=s.replace("(0x853,'ESSB_ProbeCrossB2',0x811,200)]", "(0x853,'ESSB_ProbeCrossB2',0x811,200),(0x860,'ESSB_ProbeTieA',0x810,0),(0x861,'ESSB_ProbeTieB',0x811,0),(0x863,'ESSB_ProbeTieA2',0x810,0),(0x862,'ESSB_ProbeTieB2',0x811,0)]")
 s=s.replace('0x854','0x882').replace('len(rr)==29','len(rr)==40').replace('grants four lesser','grants five lesser').replace('29 records','40 records')
 s=s.replace("    print('PROBES ok:","    runpy.run_path(str(b.WORK/'build/fix18g_verify.py'))['run'](b)\n    print('PROBES ok:")
 return s
edit('build/fix18_probes.py',recipe)
# Existing checks are retained, only their expected expanded record/property sets change.
for file in ['build/fix18b_verify.py','build/fix18f_verify.py']:
 edit(file,lambda s:s.replace('len(records)==29','len(records)==40').replace('len({r.key for r in records})==29','len({r.key for r in records})==40').replace('records=29','records=40').replace("('CrossB2',0x853)]}","('CrossB2',0x853),"+extra+"]}" ) if file.endswith('fix18b_verify.py') else s.replace('len(records)==29','len(records)==40').replace('records=29','records=40'))
