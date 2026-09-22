"""One-time scoped edits; preserve each existing file's newline convention."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def edit(name, change):
    path = ROOT/name
    raw = path.read_bytes()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf8').replace('\r\n', '\n')
    path.write_bytes(change(text).replace('\n', nl).encode('utf8'))

def setup(s):
    s = s.replace('Spell Property SecondPower Auto', 'Spell Property SecondPower Auto\nSpell Property ThirdPower Auto')
    s = s.replace('Perk Property ProbeMultiply Auto', 'Perk Property ProbeMultiply Auto\nPerk Property CrossA Auto\nPerk Property CrossB Auto\nPerk Property CrossA2 Auto\nPerk Property CrossB2 Auto\nBool CrossSecond')
    s = s.replace('player.AddSpell(SecondPower, False)', 'player.AddSpell(SecondPower, False)\n\tplayer.AddSpell(ThirdPower, False)')
    s = s.replace('「第二題」、「清理」', '「第二題」、「第三題」、「清理」')
    s = s.replace('player.RemovePerk(ProbeMultiply)', 'player.RemovePerk(ProbeMultiply)\n\tplayer.RemovePerk(CrossA)\n\tplayer.RemovePerk(CrossB)\n\tplayer.RemovePerk(CrossA2)\n\tplayer.RemovePerk(CrossB2)')
    start = s.index('\tBandit.EnableAI(False)')
    end = s.index('\nEndFunction', start)
    s = s[:start] + '''	Float angle = player.GetAngleZ()
	Bandit.MoveTo(player, Math.Sin(angle) * 128.0, Math.Cos(angle) * 128.0, 0.0)
	Bandit.Enable()
	Int loaded = 0
	While !Bandit.Is3DLoaded() && loaded < 40
		Utility.Wait(0.25)
		loaded += 1
	EndWhile
	If !Bandit.Is3DLoaded() || Bandit.IsDead() || Bandit.IsDisabled()
		Return False
	EndIf
	; Keep animation/AI processing alive: disabling AI before 3D broke melee hits.
	Bandit.EnableAI(True)
	Bandit.SetRestrained(True)
	Bandit.SetDontMove(True)
	Bandit.SetGhost(False)
	Bandit.SetActorValue("Aggression", 0.0)
	Bandit.StopCombat()
	Bandit.StopCombatAlarm()
	Bandit.SetAngle(0.0, 0.0, angle + 180.0)
	Utility.Wait(2.0)
	Bandit.UnequipAll()
	Bandit.RemoveAllItems()
	Return SettleBandit()
EndFunction

Function NetValue(String name, Float wanted)
	; Add only the CURRENT residual. Repeated calls cannot accumulate -33 offsets.
	Float residual = wanted - Bandit.GetActorValue(name)
	If residual != 0.0
		Bandit.ModActorValue(name, residual)
	EndIf
EndFunction

Bool Function SetupReady()
	Return Bandit && Bandit != Game.GetPlayer() && Bandit.Is3DLoaded() && !Bandit.IsDead() && !Bandit.IsDisabled() && !Bandit.IsDeleted() && Bandit.GetActorValue("Health") == 10000.0 && Bandit.GetActorValueMax("Health") == 10000.0 && Bandit.GetActorValue("FireResist") == 0.0 && Bandit.GetActorValue("MagicResist") == 0.0 && Bandit.GetActorValue("AbsorbChance") == 0.0 && Bandit.GetActorValue("HealRate") == 0.0 && Bandit.GetActorValue("HealRateMult") == 0.0
EndFunction

Bool Function SettleBandit()
	Int stable = 0
	Int attempts = 0
	While stable < 6 && attempts < 30
		If !Bandit.Is3DLoaded() || Bandit.IsDead() || Bandit.IsDisabled() || Bandit.IsDeleted()
			Return False
		EndIf
		Bool wasReady = SetupReady()
		NetValue("FireResist", 0.0)
		NetValue("MagicResist", 0.0)
		NetValue("AbsorbChance", 0.0)
		NetValue("HealRate", 0.0)
		NetValue("HealRateMult", 0.0)
		Float healthResidual = 10000.0 - Bandit.GetActorValueMax("Health")
		If healthResidual != 0.0
			Bandit.ModActorValue("Health", healthResidual)
		EndIf
		Bandit.RestoreActorValue("Health", 10000.0)
		Utility.Wait(0.5)
		If wasReady && SetupReady()
			stable += 1
		Else
			stable = 0
		EndIf
		attempts += 1
	EndWhile
	Debug.Trace("[ESSB-PROBE] SETTLE stable_samples=" + stable + " attempts=" + attempts + " health=" + Bandit.GetActorValue("Health") + " max_health=" + Bandit.GetActorValueMax("Health") + " fire_resist=" + Bandit.GetActorValue("FireResist") + "; AI enabled; restrained/dont-move; non-ghost")
	Return stable >= 6 && SetupReady()''' + s[end:]
    s = s.replace(' + " AttackDamageMult="', ' + " CrossA=" + player.HasPerk(CrossA) + " CrossB=" + player.HasPerk(CrossB) + " CrossA2=" + player.HasPerk(CrossA2) + " CrossB2=" + player.HasPerk(CrossB2) + " cross_variant2=" + CrossSecond + " AttackDamageMult="')
    s = s.replace('\t\tActor removed = Bandit', '\t\tCrossSecond = False\n\t\tplayer.RemoveSpell(ThirdPower)\n\t\tActor removed = Bandit')
    s = s.replace('攻擊倍率已還原。可離開測試檔。', '攻擊倍率已還原，第三題能力已移除；讀檔會補發。可離開測試檔。')
    s = s.replace('ElseIf mode == 1 || mode == 2', 'ElseIf mode == 1 || mode == 2 || mode == 4')
    s = s.replace('\t\t\tElse\n\t\t\t\tplayer.AddPerk(ProbeHit)', '\t\t\tElseIf mode == 2\n\t\t\t\tplayer.AddPerk(ProbeHit)')
    s = s.replace('\t\t\t\tplayer.AddPerk(ProbeMultiply)\n\t\t\tEndIf', '''				player.AddPerk(ProbeMultiply)
			Else
				If !CrossSecond
					player.AddPerk(CrossA)
					player.AddPerk(CrossB)
				Else
					player.AddPerk(CrossA2)
					player.AddPerk(CrossB2)
				EndIf
			EndIf
			; Last gate immediately before attaching; no latent repair during measurement.
			If !SetupReady()
				RemovePerks(player)
				LogSetup("FAILED final AV/3D check; rerun preparation", Bandit, player)
				Debug.Notification("目標尚未穩定，未掛載量測器；請重新準備。")
				Busy = False
				Return
			EndIf''')
    s = s.replace('\t\t\tIf attached\n', '\t\t\tIf attached\n\t\t\t\tIf mode == 4\n\t\t\t\t\tCrossSecond = !CrossSecond\n\t\t\t\t\tmode = 3\n\t\t\t\tEndIf\n')
    s = s.replace('FAILED spawn; cast cleanup then prepare again', 'FAILED spawn/3D/settle; cast cleanup then prepare again')
    return s

def meter(s):
    s = s.replace('Perk Property ProbeMultiply Auto', 'Perk Property ProbeMultiply Auto\nPerk Property CrossA Auto\nPerk Property CrossB Auto\nPerk Property CrossA2 Auto\nPerk Property CrossB2 Auto')
    s = s.replace('Int Hits\n', 'Int Hits\nInt WeaponHits\nInt ExtraHits\n')
    s = s.replace('\t\tEndIf\n\tElseIf probe == 2', '\t\tElseIf a == 0 && b == 1 && c == 0 && Near(damage, 7.0)\n\t\t\tReturn "single winner = last processed / lowest priority (7): lightning_roll_mode = exclusive"\n\t\tEndIf\n\tElseIf probe == 3 || probe == 4\n\t\tReturn CrossVerdict(probe, damage, a, b, c)\n\tElseIf probe == 2', 1)
    at = s.index('Int Function CurrentMode()')
    s = s[:at] + '''String Function CrossVerdict(Int variant, Float damage, Int a, Int b, Int c)
	If c == 0 && a == 1 && b == 1 && Near(damage, 12.0)
		Return "cross-perk additive: coexistence OK (12); tested pair only; cross_perk_mode = additive"
	ElseIf c == 0 && a == 1 && b == 0 && Near(damage, 5.0)
		If variant == 3
			Return "cross-perk single winner A (5): lower FormID; entry priority 200; added first; perk rank 1 (entry rank 0); compare variant 2; cross_perk_mode = exclusive"
		EndIf
		Return "cross-perk single winner A (5): lower FormID; entry priority 199; added first; perk rank 1 (entry rank 0); compare variant 1; cross_perk_mode = exclusive"
	ElseIf c == 0 && a == 0 && b == 1 && Near(damage, 7.0)
		If variant == 3
			Return "cross-perk single winner B (7): higher FormID; entry priority 199; added last; perk rank 1 (entry rank 0); compare variant 2; cross_perk_mode = exclusive"
		EndIf
		Return "cross-perk single winner B (7): higher FormID; entry priority 200; added last; perk rank 1 (entry rank 0); compare variant 1; cross_perk_mode = exclusive"
	EndIf
	Return "unexpected, report: cross-perk damage or segment counts do not match"
EndFunction

Int Function CrossMode()
	If CrossA && CrossB && CrossA2 && CrossB2
		If Player.HasPerk(CrossA) && Player.HasPerk(CrossB) && !Player.HasPerk(CrossA2) && !Player.HasPerk(CrossB2)
			Return 3
		ElseIf !Player.HasPerk(CrossA) && !Player.HasPerk(CrossB) && Player.HasPerk(CrossA2) && Player.HasPerk(CrossB2)
			Return 4
		ElseIf Player.HasPerk(CrossA) || Player.HasPerk(CrossB) || Player.HasPerk(CrossA2) || Player.HasPerk(CrossB2)
			Return -1
		EndIf
	EndIf
	Return 0
EndFunction

''' + s[at:]
    s = s.replace('Int Function CurrentMode()\n', '''Int Function CurrentMode()
	Int cross = CrossMode()
	If cross != 0
		If cross > 0 && !Player.HasPerk(ProbeAB) && !Player.HasPerk(ProbeHit) && !Player.HasPerk(ProbeMultiply)
			Return cross
		EndIf
		Return 0
	EndIf
''')
    s = s.replace('remove/add the meter spell")', 'remove/add the meter spell; probe 3 requires exactly CrossA+CrossB OR CrossA2+CrossB2 and none of the original three; use setup powers to repair")')
    s = s.replace('\tMode = CurrentMode()','\tMode = CurrentMode()\n\tDebug.Trace("[ESSB-PROBE] MODE=" + Mode + "; 3=third question variant 1 (A200/B199), 4=third question variant 2 (A199/B200); equal perk ranks; A lower FormID/add first; B higher FormID/add last")')
    s = s.replace(' || akSource != TestWeapon', '')
    s = s.replace('\tIf Hits > 1\n\t\tBad = True\n\tEndIf', '''	If akSource == TestWeapon
		WeaponHits += 1
	ElseIf ForeignNonWeapon(akSource)
		ExtraHits += 1
	Else
		Invalidate("ineligible extra source=" + akSource + "; None, weapon, spell or projectile sources cannot be ignored")
	EndIf''')
    at = s.index('Event OnHit(')
    s = s[:at] + '''Bool Function ForeignNonWeapon(Form source)
	; Conservative: reject ALL spells, weapons and projectile forms, including ours.
	If !source
		Return False
	EndIf
	Int kind = source.GetType()
	Return kind != 41 && kind != 22 && kind != 50
EndFunction

Bool Function IgnoreControlExtras(Float damage)
	; Never relax reference/probe attribution, even if normalized damage looks right.
	Return !Bad && !Calibrated && !ReferencePending && WeaponHits == 1 && ExtraHits > 0 && Hits == WeaponHits + ExtraHits && damage == 0.0 && CountA + CountB + CountC == 0
EndFunction

''' + s[at:]
    s = s.replace('\t\tIf Hits > expectedHits', '''		If IgnoreControlExtras(damage)
			Debug.Trace("[ESSB-PROBE] IGNORED control extra events=" + ExtraHits + " total=" + Hits + " weapon_hits=" + WeaponHits + " sources=" + HitSources + "; exactly one test weapon hit; foreign non-weapon/non-spell/non-projectile sources; stable physical delta exactly 0; no probe segments; reference/probe rules unchanged")
		ElseIf Hits > expectedHits''')
    s = s.replace('\t\tLogEnvironment()\n\t\tDebug.Trace("[ESSB-PROBE] MEASURE', '\t\tIf expectedHits == 1 && WeaponHits != 1\n\t\t\tInvalidate("test weapon hit count=" + WeaponHits + " expected=1 sources=" + HitSources)\n\t\tEndIf\n\t\tLogEnvironment()\n\t\tDebug.Trace("[ESSB-PROBE] MEASURE')
    s = s.replace('Hits = 0\n', 'Hits = 0\n\t\tWeaponHits = 0\n\t\tExtraHits = 0\n')
    return s

if __name__ == '__main__':
    edit('src/ESSBProbeSetup.psc', setup)
    edit('src/ESSBProbeMeter.psc', meter)
