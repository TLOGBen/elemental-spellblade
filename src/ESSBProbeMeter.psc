Scriptname ESSBProbeMeter extends ActiveMagicEffect

Perk Property ProbeAB Auto
Perk Property ProbeHit Auto
Perk Property ProbeMultiply Auto
Perk Property CrossA Auto
Perk Property CrossB Auto
Perk Property CrossA2 Auto
Perk Property CrossB2 Auto
Perk Property TieA Auto
Perk Property TieB Auto
Perk Property TieA2 Auto
Perk Property TieB2 Auto
GlobalVariable Property TieVariant Auto
GlobalVariable Property TieResult1 Auto
GlobalVariable Property TieResult2 Auto
GlobalVariable Property TieResult3 Auto
GlobalVariable Property TieResult4 Auto
GlobalVariable Property Gate Auto
GlobalVariable Property Session Auto
Spell Property ReferenceSpell Auto
Actor Victim
Actor Player
Weapon TestWeapon
Float Token
Float BeforeHealth
Float SampleHealth
Float LastActivity
Float CalibrationK
String InvalidReasons
String HitSources
Float ReportA
Float ReportB
Float ReportC
Int CountA
Int CountB
Int CountC
Int CountReference
Int Hits
Int WeaponHits
Int ExtraHits
Int Trial
Int Mode
Int Phase
Bool Bad
Bool Calibrated
Bool ReferencePending

Bool Function Near(Float actual, Float expected)
	Return actual >= expected - 0.15 && actual <= expected + 0.15
EndFunction

; These actual Papyrus bodies are executed by the offline harness.
String Function Verdict(Int probe, Float damage, Int a, Int b, Int c, Bool invalid)
	If invalid
		Return "unexpected, report: invalid or contaminated measurement"
	EndIf
	If probe == 1
		If a == 1 && b == 1 && c == 0 && Near(damage, 12.0)
			Return "both segments fired (5+7): lightning_roll_mode = additive"
		ElseIf a == 1 && b == 0 && c == 0 && Near(damage, 5.0)
			Return "only the first segment fired (5): lightning_roll_mode = chain"
		ElseIf a == 0 && b == 1 && c == 0 && Near(damage, 7.0)
			Return "single winner = last processed / lowest priority (7): lightning_roll_mode = exclusive"
		EndIf
	ElseIf probe >= 5 && probe <= 8
		Int winner = TieWinner(damage, a, b, c, False)
		Return "equal-priority variant=" + (probe - 4) + " winner=" + winner + " (1=A5,2=B7,3=both,0=unexpected); compare all four variants before deciding property"
	ElseIf probe == 3 || probe == 4
		Return CrossVerdict(probe, damage, a, b, c)
	ElseIf probe == 2 && a == 0 && b == 0 && c == 1
		If Near(damage, 20.0)
			Return "0x1D doubled the entry-point spell (20): tier_multiplier_mode = entry"
		ElseIf Near(damage, 10.0)
			Return "entry-point spell unchanged (10): tier_multiplier_mode = spell_variant"
		EndIf
	EndIf
	Return "unexpected, report: observed damage or segment counts do not match"
EndFunction

String Function CrossVerdict(Int variant, Float damage, Int a, Int b, Int c)
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

Int Function CurrentMode()
	Int cross = CrossMode()
	Int tie = TieMode()
	If tie != 0
		If tie > 0 && cross == 0 && !Player.HasPerk(ProbeAB) && !Player.HasPerk(ProbeHit) && !Player.HasPerk(ProbeMultiply)
			Return tie
		EndIf
		Return 0
	EndIf
	If cross != 0
		If cross > 0 && !Player.HasPerk(ProbeAB) && !Player.HasPerk(ProbeHit) && !Player.HasPerk(ProbeMultiply)
			Return cross
		EndIf
		Return 0
	EndIf
	If Player.HasPerk(ProbeAB) && !Player.HasPerk(ProbeHit) && !Player.HasPerk(ProbeMultiply)
		Return 1
	ElseIf !Player.HasPerk(ProbeAB) && Player.HasPerk(ProbeHit) && Player.HasPerk(ProbeMultiply)
		Return 2
	EndIf
	Return 0
EndFunction

Bool Function Clean()
	; Zero resistance/regen guards remain mandatory; k only calibrates shared spell scaling.
	Return CurrentMode() == Mode && Player.GetActorValue("AttackDamageMult") == 0.0 && Victim.GetActorValue("FireResist") == 0.0 && Victim.GetActorValue("MagicResist") == 0.0 && Victim.GetActorValue("AbsorbChance") == 0.0 && Victim.GetActorValue("HealRate") == 0.0 && Victim.GetActorValue("HealRateMult") == 0.0 && Player.GetEquippedWeapon() == TestWeapon && !TestWeapon.GetEnchantment() && !Victim.IsDead() && Victim.GetActorValue("Health") > 100.0
EndFunction

Function Invalidate(String reason)
	Bad = True
	InvalidReasons = InvalidReasons + reason + "; "
	Debug.Trace("[ESSB-PROBE] INVALID " + reason)
EndFunction

String Function EnvironmentReason()
	If CurrentMode() != Mode
		Return "probe perks changed during measurement"
	ElseIf !TestWeapon
		Return "no test weapon equipped; equip the unenchanted iron dagger"
	ElseIf Player.GetEquippedWeapon() != TestWeapon
		Return "equipped weapon changed"
	ElseIf TestWeapon.GetEnchantment()
		Return "test weapon is enchanted"
	ElseIf Player.GetActorValue("AttackDamageMult") != 0.0
		Return "non-zero AttackDamageMult=" + Player.GetActorValue("AttackDamageMult")
	ElseIf Victim.GetActorValue("FireResist") != 0.0
		Return "non-zero FireResist=" + Victim.GetActorValue("FireResist")
	ElseIf Victim.GetActorValue("MagicResist") != 0.0
		Return "non-zero MagicResist=" + Victim.GetActorValue("MagicResist")
	ElseIf Victim.GetActorValue("AbsorbChance") != 0.0
		Return "non-zero AbsorbChance=" + Victim.GetActorValue("AbsorbChance")
	ElseIf Victim.GetActorValue("HealRate") != 0.0
		Return "non-zero HealRate=" + Victim.GetActorValue("HealRate")
	ElseIf Victim.GetActorValue("HealRateMult") != 0.0
		Return "non-zero HealRateMult=" + Victim.GetActorValue("HealRateMult")
	ElseIf Victim.IsDead()
		Return "target is dead"
	ElseIf Victim.GetActorValue("Health") <= 100.0
		Return "target health too low=" + Victim.GetActorValue("Health") + "; need >100"
	EndIf
	Return ""
EndFunction

Bool Function SaneCalibration(Float k)
	; Reference must lose 2..20 HP: avoid tiny denominators and extreme amplification.
	Return k >= 0.2 && k <= 2.0
EndFunction

Function LogEnvironment()
	Debug.Trace("[ESSB-PROBE] ENV target=" + Victim + " fire_resist=" + Victim.GetActorValue("FireResist") + " magic_resist=" + Victim.GetActorValue("MagicResist") + " absorb=" + Victim.GetActorValue("AbsorbChance") + " heal_rate=" + Victim.GetActorValue("HealRate") + " heal_mult=" + Victim.GetActorValue("HealRateMult") + " attack_damage_mult=" + Player.GetActorValue("AttackDamageMult"))
EndFunction

; Runtime FormIDs include the actual load-order byte (also for signed Int IDs).
String Function HexForm(Form item)
	Int value = item.GetFormID()
	Int shift = 28
	String result = ""
	While shift >= 0
		result += StringUtil.GetNthChar("0123456789ABCDEF", Math.LogicalAnd(Math.RightShift(value, shift), 15))
		shift -= 4
	EndWhile
	Return result
EndFunction

Function LogPerkRefusal(String reason)
	String ab = HexForm(ProbeAB)
	String hit = HexForm(ProbeHit)
	String multiply = HexForm(ProbeMultiply)
	Debug.Trace("[ESSB-PROBE] REFUSED " + reason + "; player currently has: ESSB_ProbeAB " + ab + "=" + Player.HasPerk(ProbeAB) + ", ESSB_ProbeMagnitudeHit " + hit + "=" + Player.HasPerk(ProbeHit) + ", ESSB_ProbeMultiply " + multiply + "=" + Player.HasPerk(ProbeMultiply) + " (True=has perk, False=does not have perk); probe 1 needs ONLY " + ab + "; probe 2 needs BOTH " + hit + " and " + multiply + " WITHOUT " + ab + "; use player.removeperk on all three IDs, then player.addperk for the chosen combination; click the bandit first and remove/add the meter spell; probe 3 requires exactly CrossA+CrossB OR CrossA2+CrossB2 and none of the original three; use setup powers to repair")
EndFunction

Event OnEffectStart(Actor akTarget, Actor akCaster)
	Debug.Trace("[ESSB-PROBE] START meter")
	Player = Game.GetPlayer()
	Victim = akTarget
	Mode = CurrentMode()
	Debug.Trace("[ESSB-PROBE] MODE=" + Mode + "; 5..8=fourth question variants 1..4 priority zero (see SETUP); 3=third question variant 1 (A200/B199), 4=third question variant 2 (A199/B200); equal perk ranks; A lower FormID/add first; B higher FormID/add last")
	If Mode == 0 || Victim == Player
		If Mode == 0 && Victim == Player
			LogPerkRefusal("wrong probe perk combination and the console target was the player; remove the meter spell from the player")
		ElseIf Victim == Player
			Debug.Trace("[ESSB-PROBE] REFUSED the console target was the player; remove the meter spell from the player, click the bandit first, then add the meter spell to the bandit")
		Else
			LogPerkRefusal("wrong probe perk combination")
		EndIf
		Dispel()
		Return
	EndIf
	Gate.SetValue(0.0)
	Token = Session.GetValue() + 1.0
	Session.SetValue(Token)
	TestWeapon = Player.GetEquippedWeapon()
	LogEnvironment()
	If !TestWeapon || !Clean()
		Debug.Trace("[ESSB-PROBE] VERDICT unexpected, report: setup failed: " + EnvironmentReason() + "; fix ENV and remove/add meter")
		Dispel()
		Return
	EndIf
	RegisterForModEvent("ESSBProbeSegment18b", "OnSegment")
	BeforeHealth = Victim.GetActorValue("Health")
	LastActivity = Utility.GetCurrentRealTime()
	Debug.Trace("[ESSB-PROBE] READY CONTROL session=" + Token + " target=" + Victim + " health=" + BeforeHealth + "; hit ONCE; native probe gate is OFF")
	RegisterForSingleUpdate(0.25)
EndEvent

Event OnSegment(Form target, Int segment, Float reported)
	If target != Victim || Token != Session.GetValue()
		If target != Victim
			Debug.Trace("[ESSB-PROBE] IGNORED segment from a different target; remove the meter spell from other targets and test only the selected bandit")
		Else
			Debug.Trace("[ESSB-PROBE] IGNORED segment for an older meter session; remove extra meters and remove/add the meter on one bandit, then wait for READY CONTROL")
		EndIf
		Return
	EndIf
	If Phase == 2
		Invalidate("segment arrived during stability check: segment=" + segment)
	EndIf
	If segment == 1
		CountA += 1
		ReportA = reported
	ElseIf segment == 2
		CountB += 1
		ReportB = reported
	ElseIf segment == 3
		CountC += 1
		ReportC = reported
	ElseIf segment == 4 && ReferencePending
		CountReference += 1
	Else
		Invalidate("unexpected segment=" + segment + " reference_pending=" + ReferencePending)
	EndIf
	LastActivity = Utility.GetCurrentRealTime()
EndEvent

Bool Function ForeignNonWeapon(Form source)
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

Event OnHit(ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked)
	If Token != Session.GetValue()
		Debug.Trace("[ESSB-PROBE] IGNORED hit for an older meter session; remove extra meters and remove/add the meter on one bandit, then wait for READY CONTROL")
		Return
	EndIf
	Hits += 1
	HitSources = HitSources + "[" + Hits + ":" + akSource + "]"
	If akAggressor != Player || akProjectile || abPowerAttack || abSneakAttack || abBashAttack || abHitBlocked || Phase == 2
		Invalidate("invalid hit: aggressor=" + akAggressor + " source=" + akSource + " expected_weapon=" + TestWeapon + " projectile=" + akProjectile + " power=" + abPowerAttack + " sneak=" + abSneakAttack + " bash=" + abBashAttack + " blocked=" + abHitBlocked + " phase=" + Phase)
	EndIf
	If akSource == TestWeapon
		WeaponHits += 1
	ElseIf ForeignNonWeapon(akSource)
		ExtraHits += 1
	Else
		Invalidate("ineligible extra source=" + akSource + "; None, weapon, spell or projectile sources cannot be ignored")
	EndIf
	LastActivity = Utility.GetCurrentRealTime()
	Phase = 1
	Debug.Trace("[ESSB-PROBE] HIT session=" + Token + " trial=" + Trial + " hits=" + Hits + " source=" + akSource + " invalid=" + Bad)
EndEvent

Event OnUpdate()
	If Token != Session.GetValue()
		Debug.Trace("[ESSB-PROBE] REFUSED an update for an older meter session; remove extra meters and remove/add the meter on one bandit, then wait for READY CONTROL")
		Dispel()
		Return
	EndIf
	If CurrentMode() != Mode
		Gate.SetValue(0.0)
		LogPerkRefusal("probe perks changed during measurement")
		Dispel()
		Return
	EndIf
	If !Clean()
		Invalidate(EnvironmentReason())
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If Phase == 0 && (Bad || Victim.GetActorValue("Health") != BeforeHealth || CountA + CountB + CountC > 0) && now - LastActivity > 3.0
		If Victim.GetActorValue("Health") != BeforeHealth
			Invalidate("health changed before a hit: before=" + BeforeHealth + " current=" + Victim.GetActorValue("Health"))
		EndIf
		If CountA + CountB + CountC > 0
			Invalidate("probe segments arrived before a hit: A=" + CountA + " B=" + CountB + " C=" + CountC)
		EndIf
		Bad = True
		Phase = 1
	EndIf
	If Phase == 1 && now - LastActivity > 3.0
		SampleHealth = Victim.GetActorValue("Health")
		Phase = 2
		Debug.Trace("[ESSB-PROBE] WAIT checking whether the target health has stopped changing; do not hit, keep the game running and wait for READY")
		RegisterForSingleUpdate(1.0)
		Return
	ElseIf Phase == 2
		Float afterHealth = Victim.GetActorValue("Health")
		Float damage = BeforeHealth - afterHealth
		If afterHealth != SampleHealth
			Invalidate("unstable health: sample=" + SampleHealth + " after=" + afterHealth)
		EndIf
		Int expectedHits = 1
		If ReferencePending
			expectedHits = 0
		EndIf
		If IgnoreControlExtras(damage)
			Debug.Trace("[ESSB-PROBE] IGNORED control extra events=" + ExtraHits + " total=" + Hits + " weapon_hits=" + WeaponHits + " sources=" + HitSources + "; exactly one test weapon hit; foreign non-weapon/non-spell/non-projectile sources; stable physical delta exactly 0; no probe segments; reference/probe rules unchanged")
		ElseIf Hits > expectedHits
			Invalidate("extra hit events: count=" + Hits + " expected=" + expectedHits + " sources=" + HitSources)
		ElseIf Hits < expectedHits
			Invalidate("missing hit events: count=" + Hits + " expected=" + expectedHits + " sources=" + HitSources)
		EndIf
		If expectedHits == 1 && WeaponHits != 1
			Invalidate("test weapon hit count=" + WeaponHits + " expected=1 sources=" + HitSources)
		EndIf
		LogEnvironment()
		Debug.Trace("[ESSB-PROBE] MEASURE session=" + Token + " trial=" + Trial + " probe=" + Mode + " before=" + BeforeHealth + " after=" + afterHealth + " health_delta=" + damage + " A_count=" + CountA + " B_count=" + CountB + " C_count=" + CountC + " A_reported=" + ReportA + " B_reported=" + ReportB + " C_reported=" + ReportC + " hits=" + Hits + " weapon_hits=" + WeaponHits + " extra_candidates=" + ExtraHits + " sources=" + HitSources + " reference_count=" + CountReference + " invalid=" + Bad)
		If ReferencePending
			ReferencePending = False
			CalibrationK = damage / 10.0
			If !SaneCalibration(CalibrationK)
				Invalidate("reference k out of band [0.2,2.0]: k=" + CalibrationK + " health_delta=" + damage)
			EndIf
			If CountReference != 1 || CountA + CountB + CountC != 0
				Invalidate("reference segment counts: reference=" + CountReference + " expected=1 A=" + CountA + " B=" + CountB + " C=" + CountC + " expected_probe_total=0")
			EndIf
			If !Bad
				Calibrated = True
				Gate.SetValue(1.0)
				Debug.Trace("[ESSB-PROBE] CALIBRATE k=" + CalibrationK + " reference_delta=" + damage + " nominal=10 band=[0.2,2.0]")
				Debug.Trace("[ESSB-PROBE] VERDICT REFERENCE stable native fire accepted; physical=0; attribution enabled")
			Else
				Bad = True
				Debug.Trace("[ESSB-PROBE] VERDICT unexpected, report: REFERENCE invalid: " + InvalidReasons + "do not interpret subsequent hits")
			EndIf
		ElseIf !Calibrated
			If !Bad && damage == 0.0 && CountA + CountB + CountC == 0
				Debug.Trace("[ESSB-PROBE] VERDICT CONTROL physical-only hit = 0; testing native fire reference; DO NOT HIT")
				ReferencePending = True
				BeforeHealth = afterHealth
				Hits = 0
				WeaponHits = 0
				ExtraHits = 0
				HitSources = ""
				InvalidReasons = ""
				Phase = 1
				LastActivity = now
				Player.DoCombatSpellApply(ReferenceSpell, Victim)
				RegisterForSingleUpdate(0.25)
				Return
			Else
				If damage != 0.0
					Invalidate("non-zero physical control delta=" + damage + " expected=0")
				EndIf
				If CountA + CountB + CountC != 0
					Invalidate("control segment counts: A=" + CountA + " B=" + CountB + " C=" + CountC + " expected_total=0")
				EndIf
				Bad = True
				Debug.Trace("[ESSB-PROBE] VERDICT unexpected, report: CONTROL invalid: " + InvalidReasons + "do not interpret subsequent hits")
			EndIf
		Else
			String answer = Verdict(Mode, damage / CalibrationK, CountA, CountB, CountC, Bad)
			If Mode >= 5 && Mode <= 8
				RememberTie(TieWinner(damage / CalibrationK, CountA, CountB, CountC, Bad))
			EndIf
			Debug.Trace("[ESSB-PROBE] VERDICT " + answer + " [basis=health_delta/k; k=" + CalibrationK + " normalized_delta=" + (damage / CalibrationK) + "; reported_magnitude is diagnostic only] reasons=" + InvalidReasons)
		EndIf
		If Bad
			Gate.SetValue(0.0)
			Debug.Trace("[ESSB-PROBE] STOP remove/add meter after fixing setup; no switch decided")
			Dispel()
			Return
		EndIf
		Trial += 1
		Hits = 0
		WeaponHits = 0
		ExtraHits = 0
		HitSources = ""
		InvalidReasons = ""
		CountA = 0
		CountB = 0
		CountC = 0
		ReportA = 0.0
		ReportB = 0.0
		ReportC = 0.0
		BeforeHealth = afterHealth
		Phase = 0
		Debug.Trace("[ESSB-PROBE] READY PROBE session=" + Token + " trial=" + Trial + "; hit ONCE, then wait for next READY")
	EndIf
	RegisterForSingleUpdate(0.25)
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	If Token == Session.GetValue()
		Gate.SetValue(0.0)
	EndIf
	; The native effect may already be gone here. Do not call native methods on Self.
EndEvent

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
