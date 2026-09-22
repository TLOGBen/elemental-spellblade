from implement_fix16 import *
c='src/ESSBController.psc'
replace(c,'Int[] DomainElem','Actor[] DomainResident\nFloat[] DomainResidentAt\nInt[] DomainElem')
replace(c,'\tIf !DomainElem','\tIf !DomainResident\n\t\tDomainResident = new Actor[18]\n\tEndIf\n\tIf !DomainResidentAt\n\t\tDomainResidentAt = new Float[18]\n\tEndIf\n\tIf !DomainResident || !DomainResidentAt\n\t\tBreakState()\n\t\tReturn\n\tEndIf\n\tIf !DomainElem',2) if False else None
# Only the outer allocation site (inner failure check is intentionally untouched).
replace(c,'\tIf !DomainElem\n\t\tDomainElem = new Int[3]', '\tIf !DomainResident\n\t\tDomainResident = new Actor[18]\n\tEndIf\n\tIf !DomainResidentAt\n\t\tDomainResidentAt = new Float[18]\n\tEndIf\n\tIf !DomainResident || !DomainResidentAt\n\t\tBreakState()\n\t\tReturn\n\tEndIf\n\tIf !DomainElem\n\t\tDomainElem = new Int[3]')
replace(c,'\tDomainR[slot] = afRadius','\tDomainR[slot] = afRadius\n\tClearDomainResidents(slot)\n\tObserveDomainResidents(slot, ScanDomainTargets(PO3_SKSEFunctions.GetActorsByProcessingLevel(0), slot), ThePlayer(), DomainTickAt[slot])')
replace(c,'\t\t\tInt ticks = (stop - DomainTickAt[slot]) as Int\n\t\t\tDomainTickAt[slot] = DomainTickAt[slot] + ticks\n\t\t\tInt element = DomainElem[slot]', '\t\t\tActor[] nearby = ScanDomainTargets(pool, slot)\n\t\t\tObserveDomainResidents(slot, nearby, player, Utility.GetCurrentRealTime())\n\t\t\tInt ticks = DomainTargetTicks(player, slot, stop)\n\t\t\tDomainTickAt[slot] = stop\n\t\t\tInt element = DomainElem[slot]')
replace(c,'\t\t\tActor[] nearby = ScanDomainTargets(pool, slot)\n\t\t\tInt index = 0','\t\t\tInt index = 0')
replace(c,'\t\t\t\tActor victim = nearby[index]\n\t\t\t\tIf victim && ticks > 0','\t\t\t\tActor victim = nearby[index]\n\t\t\t\tticks = DomainTargetTicks(victim, slot, stop)\n\t\t\t\tIf victim && ticks > 0')
replace(c,'\t\t\t\tDomainElem[slot] = 0','\t\t\t\tDomainElem[slot] = 0\n\t\t\t\tClearDomainResidents(slot)')
replace(c,'\t\tDomainLeft[timerIndex] = 0.0','\t\tDomainLeft[timerIndex] = 0.0\n\t\tClearDomainResidents(timerIndex)')
write(c,read(c)+'''
; Six residents/domain: the existing nearest-five selection plus the player.
; First observed inside is a conservative entry time; no retroactive award to newcomers.
Function ClearDomainResidents(Int aiSlot)
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		DomainResident[i] = None
		DomainResidentAt[i] = 0.0
		i += 1
	EndWhile
EndFunction

Function ObserveDomainResidents(Int aiSlot, Actor[] akNearby, Actor akPlayer, Float afNow)
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		Actor resident = DomainResident[i]
		Bool present = resident && resident == akPlayer && InsideDomainSlot(akPlayer, aiSlot)
		Int n = 0
		While resident && !present && n < akNearby.Length
			present = akNearby[n] == resident
			n += 1
		EndWhile
		If !present
			DomainResident[i] = None
			DomainResidentAt[i] = 0.0
		EndIf
		i += 1
	EndWhile
	If InsideDomainSlot(akPlayer, aiSlot)
		RememberDomainResident(akPlayer, aiSlot, afNow)
	EndIf
	i = 0
	While i < akNearby.Length
		RememberDomainResident(akNearby[i], aiSlot, afNow)
		i += 1
	EndWhile
EndFunction

Function RememberDomainResident(Actor akTarget, Int aiSlot, Float afNow)
	If !akTarget
		Return
	EndIf
	Int i = aiSlot * 6
	Int empty = -1
	While i < aiSlot * 6 + 6
		If DomainResident[i] == akTarget
			Return
		ElseIf !DomainResident[i]
			empty = i
		EndIf
		i += 1
	EndWhile
	If empty >= 0
		DomainResident[empty] = akTarget
		DomainResidentAt[empty] = afNow
	EndIf
EndFunction

Int Function DomainTargetTicks(Actor akTarget, Int aiSlot, Float afStop)
	If !akTarget
		Return 0
	EndIf
	Int i = aiSlot * 6
	While i < aiSlot * 6 + 6
		If DomainResident[i] == akTarget
			Int ticks = (afStop - DomainResidentAt[i]) as Int
			If ticks > 0
				DomainResidentAt[i] = DomainResidentAt[i] + ticks
				Return ticks
			EndIf
			Return 0
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction
''')
ledger('A4 領域每目標結算','已保存三領域各六個居民的首次觀測／已結算時間；新進者不追領舊帳，離開後重入重算')
replace(c,'Bool hitCasting = ESSBNoForm.IsCasting(akTarget) || RecentCast(akTarget)','Bool hitCasting = ESSBNodes.Br(Self, 11, 1, 1, 0) && (ESSBNoForm.IsCasting(akTarget) || RecentCast(akTarget))')
replace(c,'If CachedSync >= CachedT3 && !DivineArmed && !DivineSaveUsed','If CachedSync >= CachedT3 && !DivineArmed && !DivineSaveUsed && ESSBNodes.Br(Self, 6, 0, 4, 0)')
replace('src/ESSBStatus.psc','RingClock > 0 && !Settling && Holder && !Holder.IsDead()','RingClock > 0 && !Settling && Utility.GetCurrentRealTime() - RingClock >= 1.0 && Holder && !Holder.IsDead()',4)
ledger('A5 命中成本','已加斷咒／神佑所有權短路；GetStack 等先查未滿一秒，再做 IsDead；待實測')
# Reuse the existing two form reads in the hit dispatcher; do not add hot-path natives.
replace(c,'Bool[] HitSneak','Int[] HitForm\nBool[] HitSneak')
replace(c,'\tIf !HitSneak\n\t\tHitSneak = new Bool[8]','\tIf !HitForm\n\t\tHitForm = new Int[8]\n\t\tIf !HitForm\n\t\t\tBreakState()\n\t\t\tReturn\n\t\tEndIf\n\tEndIf\n\tIf !HitSneak\n\t\tHitSneak = new Bool[8]')
replace(c,'\tHitActor[fact] = targetActor','\tInt hitElement = 0\n\tIf FormActive.GetValueInt() == 1\n\t\thitElement = CurrentElement.GetValueInt()\n\tEndIf\n\tHitForm[fact] = hitElement\n\tHitActor[fact] = targetActor')
replace(c,'If sneak && FormActive.GetValueInt() == 1 && CurrentElement.GetValueInt() == 5','If sneak && hitElement == 5')
replace(c,'\tIf FormActive.GetValueInt() != 1\n\t\t; 規劃 4','\tIf hitElement == 0\n\t\t; 規劃 4')
replace(c,'\tInt element = CurrentElement.GetValueInt()\n\tIf element < 1','\tInt element = hitElement\n\tIf element < 1')
replace(c,'\tIf aiElement == 0\n\t\tReturn\n\tEndIf\n\tInt i = 0\n\tWhile i < 8\n\t\tIf HitActor[i] == akVictim && !HitKillDone[i]','\tInt i = 0\n\tWhile i < 8\n\t\tIf HitActor[i] == akVictim && !HitKillDone[i] && HitSneak[i] && HitForm[i] == 5')
replace(c,'ESSBElem2.TryKillStreak(Self, aiElement, HitSneak[i])','ESSBElem2.TryKillStreak(Self, HitForm[i], HitSneak[i])')
# The done latch is claimed only by qualifying facts: an earlier non-sneak hit cannot consume it.
replace('src/ESSBElem2.psc','; FIX14: wind streak consumes the same frozen death attribution.','; FIX16 deviation: wind-form branch consumes recorded hit-time form, not killing element.')
s=read('src/ESSBElem2.psc');start=s.index('Function TryKillStreak(');end=s.index('EndFunction',start);s=s[:start]+s[start:end].replace('aiKillingElement','aiHitForm')+s[end:];write('src/ESSBElem2.psc',s)
ledger('B1.2 連殺命中形態','已改讀命中記錄 HitForm，純物理潛行致死可結算；非潛行舊命中不先消耗完成旗標')
replace('settings.json','"state_schema_version": 5','"state_schema_version": 6')
